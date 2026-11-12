#!/usr/bin/env python3
"""Boot/reattach a Kaypro KP2 ROM using the production Juku disk host. MIT."""
import argparse
import binascii
import hashlib
import fcntl
import json
import math
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import stat
import subprocess
import sys
import termios
import time
import tty
from terminal import Screen, Keys
from serial_format import configure

ROOT=Path(__file__).resolve().parents[1]
BAUD=19200
MIN_PAYLOAD=0x36
MAX_PAYLOAD=0x35ff

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def exact(fd,n,deadline):
    data=bytearray()
    while len(data)<n:
        if not select.select([fd],[],[],max(0,deadline-time.monotonic()))[0]:
            raise TimeoutError('serial receive timeout')
        try: part=os.read(fd,n-len(data))
        except BlockingIOError: continue
        if not part: raise ConnectionError('serial disconnected')
        data.extend(part)
    return bytes(data)

def write_all(fd,data,deadline):
    view=memoryview(data)
    while view:
        if not select.select([],[fd],[],max(0,deadline-time.monotonic()))[1]:
            raise TimeoutError('serial transmit timeout')
        try: n=os.write(fd,view)
        except BlockingIOError: continue
        if not n: raise ConnectionError('serial write made no progress')
        view=view[n:]

class Port:
    def __init__(self,path,baud=19200,parity="O",stop_bits=1):
        self.fd=os.open(path,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
        try:
            if not stat.S_ISCHR(os.fstat(self.fd).st_mode): raise ValueError('serial port must be a character device')
            name=os.ttyname(self.fd)
            self.simulated=name.startswith(('/dev/pts/','/dev/ttys','/dev/pty'))
            if not self.simulated and hasattr(termios,'TIOCEXCL'):
                fcntl.ioctl(self.fd,termios.TIOCEXCL)
            self.original=termios.tcgetattr(self.fd)
            self.settings=configure(self.fd,baud,parity,stop_bits,self.simulated)
        except BaseException:
            os.close(self.fd);raise
    def close(self):
        if not self.simulated and hasattr(termios,'TIOCNXCL'):
            fcntl.ioctl(self.fd,termios.TIOCNXCL)
        os.close(self.fd)


def transfer(fd,payload,session,deadline,identity,corrupt=False):
    if not MIN_PAYLOAD<=len(payload)<=MAX_PAYLOAD:raise ValueError('payload length outside 0036..35FF')
    if identity!=b'KP2':raise ValueError(f'expected KP2 ROM, received {identity!r}')
    packet=len(payload).to_bytes(2,'little')+payload+(binascii.crc_hqx(payload,65535)^int(corrupt)).to_bytes(2,'big')
    if session:
        # Packet file is intended bytes, not proof of bytes transmitted.
        Path(session,'bootstrap-packet.bin').write_bytes(b'K'+packet)
        Path(session,'bootstrap-rx.bin').write_bytes(identity)
    write_all(fd,packet,deadline)
    answer=exact(fd,1,deadline)
    if session:
        with Path(session,'bootstrap-rx.bin').open('ab') as f:f.write(answer)
    if answer!=b'\x06':raise ValueError(f'ROM rejected upload: {answer.hex()}; reset and retry')


def upload(fd,payload,session,timeout=30,corrupt=False):
    """One exchange; shared by the real launcher and fault-injection tests."""
    if not MIN_PAYLOAD<=len(payload)<=MAX_PAYLOAD:raise ValueError('invalid payload size')
    deadline=time.monotonic()+timeout
    write_all(fd,b'K',deadline)
    transfer(fd,payload,session,deadline,exact(fd,3,deadline),corrupt)


def bootstrap(fd,payload,session,timeout):
    if not MIN_PAYLOAD<=len(payload)<=MAX_PAYLOAD:raise ValueError('invalid payload size')
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        write_all(fd,b'K',deadline)
        try:identity=exact(fd,3,min(deadline,time.monotonic()+2))
        except TimeoutError:continue
        transfer(fd,payload,session,deadline,identity)
        return
    raise TimeoutError('KP2 ROM did not respond before deadline')


def validate(image,platform):
    if Path(image).stat().st_size!=819200: raise ValueError('expected native800 disk image')
    data=Path(platform).read_bytes()
    if not MIN_PAYLOAD<=len(data)<=MAX_PAYLOAD: raise ValueError('invalid platform size')
    # CPM3.SYS carries the platform's compile-time system CRC. Check the image
    # independently rather than trusting matching filenames.
    from media import inspect
    files=inspect(Path(image).read_bytes())
    if (0,'CPM3.SYS') not in files or (0,'CCP.COM') not in files:raise ValueError('missing CP/M system files')
    manifest=Path(platform).parent/'manifest.json'
    if not manifest.exists():raise ValueError('missing platform manifest; rebuild or use release artifacts')
    if manifest.exists():
        m=json.loads(manifest.read_text())
        for key,p in [('platform.cim',platform),('kaypro.img',image)]:
            if m['sha256'][key]!=digest(p):raise ValueError(f'manifest mismatch: {key}')
    return data


def validate_host(host,baud=19200,parity="O",stop_bits=1):
    # --help exits during option parsing, before serial or media access. Put it
    # LAST so old binaries must parse the options that V3 requires first.
    command=[str(Path(host).resolve()),'--machine','kaypro2',
             '--disk-baud',str(baud),'--serial-parity',parity,
             '--serial-stop-bits',str(stop_bits),'--help']
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=5)
    except subprocess.TimeoutExpired as e:
        raise ValueError('host preflight timed out; no upload attempted') from e
    if result.returncode:
        detail=(result.stderr or result.stdout).splitlines()
        raise ValueError('incompatible host executable; rebuild the pinned host before booting: '+
                         (detail[0] if detail else f'exit {result.returncode}'))


def host_command(host,serial,fd,disk,console,session,readonly=False,baud=19200,parity="O",stop_bits=1):
    stamp=str(time.time_ns())
    args=[str(Path(host).resolve()),'--machine','kaypro2','--resume-disk','--serial',serial,
          '--serial-fd',str(fd),'--volume',str(disk),'--console-pty',console,
          '--log',str(session/f'host-{stamp}.log'),'--capture',str(session/f'wire-{stamp}.bin')]
    args += ['--disk-baud',str(baud),'--serial-parity',parity,'--serial-stop-bits',str(stop_bits)]
    if not readonly:args.append('--writable')
    return args


def run_host(args,fd,session,console_master=None):
    with (session/f'process-{time.time_ns()}.log').open('wb') as log:
        child=subprocess.Popen(args,pass_fds=(fd,),stdout=log,stderr=log)
        saved=None;screen=Screen();keys=Keys();key_at=0
        try:
            if console_master is None: return child.wait()
            if not sys.stdin.isatty():raise ValueError('interactive console requires a terminal; use --console-pty for automation')
            saved=termios.tcgetattr(0);tty.setraw(0)
            os.write(1,b'\x1b[2J\x1b[H')
            while child.poll() is None:
                ready,_,_=select.select([0,console_master],[],[],.05)
                if console_master in ready:
                    data=os.read(console_master,8192)
                    if not data:break
                    with (session/'console.bin').open('ab') as f:f.write(data)
                    screen.feed(data);write_all(1,screen.ansi(),time.monotonic()+5)
                if 0 in ready:
                    data=os.read(0,256)
                    if not data or b'\x1d' in data:break
                    write_all(console_master,keys.feed(data),time.monotonic()+5);key_at=time.monotonic()
                if keys.pending and time.monotonic()-key_at>.1:
                    write_all(console_master,keys.flush(),time.monotonic()+5)
            if child.poll() is not None:return child.returncode
            return 0
        finally:
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.kill();child.wait()
            if saved is not None:termios.tcsetattr(0,termios.TCSANOW,saved)
            (session/'host-screen.txt').write_bytes(screen.text())


def main():
    if len(sys.argv)>1 and sys.argv[1] in ('probe','scan','rx-test','tx-test'):
        from diagnostics import main as diagnostics_main
        return diagnostics_main()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['boot','attach'])
    p.add_argument('--serial',required=True)
    p.add_argument('--baud',type=int,default=19200)
    p.add_argument('--parity',choices=['N','O','E'],default='O')
    p.add_argument('--stop-bits',type=int,choices=[1,2],default=1)
    p.add_argument('--session',type=Path,required=True)
    p.add_argument('--host',type=Path,default=ROOT.parent/'8080-cosim/build/jukuhost')
    p.add_argument('--platform',type=Path,default=ROOT/'build/platform.cim')
    p.add_argument('--image',type=Path,default=ROOT/'out/kaypro.img')
    p.add_argument('--timeout',type=float,default=30)
    p.add_argument('--read-only',action='store_true')
    p.add_argument('--test-corrupt-read-reply-once',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--console-pty',help='raw Kaypro console endpoint for automation')
    a=p.parse_args()
    if not math.isfinite(a.timeout) or a.timeout<=0:p.error('timeout must be finite and positive')
    if not a.host.is_file() or not os.access(a.host,os.X_OK):p.error('host executable is missing')
    if not a.console_pty and not sys.stdin.isatty():p.error('use --console-pty when not interactive')
    validate_host(a.host,a.baud,a.parity,a.stop_bits)
    payload=validate(a.image,a.platform)
    session=a.session.resolve()
    identity=dict(protocol='KP2',baud=a.baud,framing=f'8{a.parity}{a.stop_bits}',platform_sha256=digest(a.platform),
                  source_sha256=digest(a.image),host_sha256=digest(a.host),read_only=a.read_only)
    if a.mode=='boot':
        session.mkdir(parents=True,exist_ok=False)
        shutil.copyfile(a.image,session/'disk.img')
        (session/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    else:
        stored=json.loads((session/'identity.json').read_text())
        if stored!=identity:raise ValueError('session identity differs; use original artifacts and options')
        if (session/'disk.img').stat().st_size!=819200:raise ValueError('invalid session disk')
    lock=(session/'session.lock').open('a+b')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:lock.close();raise ValueError('session already in use')
    try:port=Port(a.serial,a.baud,a.parity,a.stop_bits)
    except BaseException:lock.close();raise
    master=slave=None
    result=dict(complete=False,simulated_serial=port.simulated,physical_qualification=False,execution_requested=False)
    try:
        if a.console_pty:console=a.console_pty
        else:
            master,slave=pty.openpty();tty.setraw(slave);console=os.ttyname(slave)
        if a.mode=='boot':
            if (a.baud,a.parity,a.stop_bits)!=(19200,'O',1):
                from diagnostics import query
                write_all(port.fd,b'V',time.monotonic()+3)
                version=bytearray()
                deadline=time.monotonic()+3
                while len(version)<64 and not version.endswith(b'\n'):
                    version.extend(exact(port.fd,1,deadline))
                if not version.startswith(b'KPV3.'):
                    raise ValueError('nondefault boot requires V3 in Boot mode; press B after scanning')
                info=query(port.fd,'Q',timeout=3)
                if info['version'][0]!=3 or not json.loads((a.platform.parent/'manifest.json').read_text()).get('serial_handoff'):
                    raise ValueError('nondefault boot requires V3 and handoff-aware platform')
                if info['parity']!=a.parity or info['stop_bits']!=a.stop_bits:
                    raise ValueError('ROM framing differs from host options')
                (session/'rom-info.json').write_text(json.dumps(info,indent=2)+'\n')
                query(port.fd,'B',timeout=3)
            transfer_timeout=max(a.timeout,4*len(payload)*(9+(a.parity!='N')+a.stop_bits)/a.baud+2)
            bootstrap(port.fd,payload,session,transfer_timeout)
            # Same framing and descriptor: neither reset, flush nor reopen here.
            result['execution_requested']=True
            write_all(port.fd,b'G',time.monotonic()+a.timeout)
            termios.tcdrain(port.fd)
        command=host_command(a.host,a.serial,port.fd,session/'disk.img',console,session,a.read_only,a.baud,a.parity,a.stop_bits)
        if a.test_corrupt_read_reply_once:command.append('--test-corrupt-read-reply-once')
        result['host_exit']=run_host(command,port.fd,session,master)
        result['complete']=result['host_exit']==0
        return result['host_exit']
    finally:
        port.close();lock.close()
        if master is not None:os.close(master);os.close(slave)
        (session/f'launch-{time.time_ns()}.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    def interrupted(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted)
    try:sys.exit(main())
    except KeyboardInterrupt:print('Detached; use attach to resume the session.',file=sys.stderr);sys.exit(130)
    except (OSError,ValueError,TimeoutError,RuntimeError) as e:print(f'Kaypro: {e}',file=sys.stderr);sys.exit(1)
