#!/usr/bin/env python3
"""Boot actual Z80 firmware through a timed PTY; reuse the production N4 host."""
import argparse, binascii, hashlib, json, os, pty, select, shutil, subprocess, time, tty, termios
from pathlib import Path
from media import inspect
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--host',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    wire,device=pty.openpty();terminal,console=pty.openpty()
    for fd in (wire,device,terminal,console):tty.setraw(fd)
    image=ROOT/'out/kaypro.img';disk=a.out/'disk.img';shutil.copyfile(image,disk)
    log=(a.out/'emulator.log').open('wb');hostlog=(a.out/'host-process.log').open('wb')
    emu=subprocess.Popen([str(ROOT/'build/kaypro-probe'),str(ROOT/'build/boot.rom'),str(wire),str(a.out/'ram.bin')],pass_fds=(wire,),stderr=log)
    host=None;output=bytearray();cases=[]
    result=dict(complete=False,hardware_executed=False,rom_sha256=digest(ROOT/'build/boot.rom'),platform_sha256=digest(ROOT/'build/platform.cim'),image_sha256=digest(image),host_sha256=digest(a.host),emulator_sha256=digest(ROOT/'build/kaypro-probe'),cases=cases)
    def exact(n,timeout=5):
        data=bytearray();end=time.monotonic()+timeout
        while len(data)<n:
            if not select.select([device],[],[],max(0,end-time.monotonic()))[0]:raise TimeoutError(('serial',bytes(data)))
            data.extend(os.read(device,n-len(data)))
        return bytes(data)
    def send_payload(data,corrupt=False):
        os.write(device,b'K');assert exact(3)==b'KP1'
        packet=len(data).to_bytes(2,'little')+data+(binascii.crc_hqx(data,65535)^int(corrupt)).to_bytes(2,'big')
        # PTY has finite capacity; small chunks also represent bounded host writes.
        for i in range(0,len(packet),128):os.write(device,packet[i:i+128])
        return exact(1,30)
    def passed(name):cases.append(name);print(name,'PASS',flush=True)
    def expect(marker,start=0,timeout=120):
        end=time.monotonic()+timeout
        while marker not in output[start:]:
            if emu.poll() is not None or (host and host.poll() is not None):raise RuntimeError('child exited')
            if time.monotonic()>=end:raise TimeoutError(bytes(output[-500:]))
            if select.select([terminal],[],[],.05)[0]:
                output.extend(os.read(terminal,8192))
                (a.out/'console.bin').write_bytes(output)
        return bytes(output[start:])
    def command(text):
        at=len(output);os.write(terminal,text.encode()+b'\r');data=expect(b'A>',at);passed(text);return data
    def start_host():
        return subprocess.Popen([str(a.host),'--machine','kaypro2','--resume-disk','--serial',os.ttyname(device),'--serial-fd',str(device),'--volume',str(disk),'--console-pty',os.ttyname(console),'--writable','--log',str(a.out/'host.log'),'--capture',str(a.out/f'wire-{len(cases)}.bin')],pass_fds=(device,),stdout=hostlog,stderr=hostlog)
    try:
        time.sleep(1)
        payload=(ROOT/'build/platform.cim').read_bytes()
        assert send_payload(payload,True)==b'\x15';passed('corrupt bootstrap rejected')
        assert send_payload(payload)==b'\x06';passed('checked serial upload')
        # Drain the 8N1 execution byte before the host adopts 8O1 framing.
        os.write(device,b'G');termios.tcdrain(device);host=start_host()
        expect(b'A>');passed('CP/M Plus cold boot')
        assert b'Kaypro 2' in command('TYPE HELLO.TXT')
        command('DIR')
        command('PIP COPY.TXT=HELLO.TXT')
        files=inspect(disk.read_bytes());assert files[(0,'COPY.TXT')].data==files[(0,'HELLO.TXT')].data
        passed('independent disk readback')
        command('RENAME RENAMED.TXT=COPY.TXT')
        assert (0,'RENAMED.TXT') in inspect(disk.read_bytes());passed('rename persisted')
        at=len(output);os.write(terminal,b'\x03');expect(b'A>',at);passed('warm boot')
        host.terminate();host.wait(timeout=10);host=None
        host=start_host();time.sleep(.5)
        assert b'Kaypro 2' in command('TYPE RENAMED.TXT');passed('host restart without guest reset')
        assert digest(image)==result['image_sha256'];passed('source image unchanged')
        result['complete']=True
    finally:
        if host:host.terminate();host.wait(timeout=10)
        emu.terminate();emu.wait(timeout=10)
        result['emulator_exit']=emu.returncode
        if emu.returncode:result['complete']=False
        (a.out/'console.bin').write_bytes(output)
        (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        log.close();hostlog.close()
        for fd in (wire,device,terminal,console):os.close(fd)
    if not result['complete']:raise RuntimeError('qualification incomplete')
if __name__=='__main__':main()
