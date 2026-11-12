#!/usr/bin/env python3
"""Boot actual Z80 firmware through a timed PTY; reuse the production N4 host."""
import sys
import argparse, binascii, hashlib, json, os, pty, select, shutil, subprocess, time, tty, termios
from pathlib import Path
from media import inspect
from serial_boot import upload
from terminal import Screen
from check_drivers import symbols
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--host',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--read-only',action='store_true');p.add_argument('--corrupt-read',action='store_true');p.add_argument('--alternate',action='store_true',help='select 9600 8E2 using the ROM keyboard');p.add_argument('--optimized',action='store_true');p.add_argument('--auto',action='store_true');p.add_argument('--read-ahead',type=int,default=4);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    wire,device=pty.openpty();terminal,console=pty.openpty();keyboard_r,keyboard_w=os.pipe()
    for fd in (wire,device,terminal,console):tty.setraw(fd)
    image=ROOT/'out/kaypro.img';disk=a.out/'disk.img';shutil.copyfile(image,disk)
    log=(a.out/'emulator.log').open('wb');hostlog=(a.out/'host-process.log').open('wb')
    emu=subprocess.Popen([str(ROOT/'build/kaypro-probe'),str(ROOT/'build/boot.rom'),str(wire),str(a.out/'ram.bin'),str(keyboard_r)],pass_fds=(wire,keyboard_r),stderr=log,env=dict(os.environ,KAYPRO_BOOT_SYNC=str(symbols(ROOT/'build/boot-stage.lst')['sync']),KAYPRO_KEYSERVICE=str(symbols(ROOT/'build/platform.lst')['keyservice'])))
    host=None;output=bytearray();cases=[]
    result=dict(complete=False,hardware_executed=False,framing='9600 8E2' if a.alternate else '19200 8O1',rom_sha256=digest(ROOT/'build/boot.rom'),platform_sha256=digest(ROOT/'build/platform.cim'),image_sha256=digest(image),host_sha256=digest(a.host),emulator_sha256=digest(ROOT/'build/kaypro-probe'),cases=cases)
    def exact(n,timeout=5):
        data=bytearray();end=time.monotonic()+timeout
        while len(data)<n:
            if not select.select([device],[],[],max(0,end-time.monotonic()))[0]:raise TimeoutError(('serial',bytes(data)))
            data.extend(os.read(device,n-len(data)))
        return bytes(data)
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
    def start_host(mode='attach'):
        return subprocess.Popen([sys.executable,str(ROOT/'tools/serial_boot.py'),'auto' if a.auto else mode,
            '--host',str(a.host),'--serial',os.ttyname(device),'--session',str(a.out/'session'),
            '--console-pty',os.ttyname(console)]+(['--baud','9600','--parity','E','--stop-bits','2'] if a.alternate else [])+(['--runtime-profile','fast','--buffer-console','--read-ahead',str(a.read_ahead)] if a.optimized else [])+(['--read-only'] if a.read_only else [])+(['--test-corrupt-read-reply-once'] if a.corrupt_read and mode=='boot' else []),stdout=hostlog,stderr=hostlog)
    try:
        def monitor_ready(mode,selector,wr4):
            marker=f'monitor-ready mode={mode} selector={selector} wr4={wr4:02x}'
            end=time.monotonic()+60
            while marker not in (a.out/'emulator.log').read_text():
                if emu.poll() is not None or time.monotonic()>=end:
                    raise TimeoutError(f'ROM did not reach {marker}')
                time.sleep(.02)
        monitor_ready(0,15,0x45)
        if a.alternate:
            for key,mode,selector,wr4 in [
                    ('S',1,15,0x45),('1',1,5,0x45),('1',1,6,0x45),
                    ('1',1,7,0x45),('1',1,10,0x45),('1',1,12,0x45),
                    ('1',1,14,0x45),('2',1,14,0x47),('3',1,14,0x4f),
                    ('\x1b',0,14,0x4f)]:
                os.write(keyboard_w,key.encode());monitor_ready(mode,selector,wr4)
            passed('ROM keyboard selects 9600 8E2')
        payload=(ROOT/'build/platform.cim').read_bytes()
        try:upload(device,payload,None,corrupt=True)
        except ValueError as e:assert 'rejected' in str(e)
        else:raise AssertionError('corrupt upload accepted')
        passed('corrupt bootstrap rejected')
        host=start_host('boot')
        disk=a.out/'session/disk.img'
        passed('production launcher started')
        expect(b'A>');passed('CP/M Plus cold boot')
        assert b'Kaypro 2' in command('TYPE HELLO.TXT')
        command('DIR')
        assert b'SCREEN PASS' in command('SCREEN')
        at=len(output);os.write(keyboard_w,b'TYPE HELLO.TXT\r')
        assert b'Kaypro 2' in expect(b'A>',at);passed('local keyboard command via SIO B')
        if a.read_only:
            before=digest(disk)
            assert b'ERROR:' in command('PIP COPY.TXT=HELLO.TXT')
            assert digest(disk)==before;passed('read-only write rejected without disk change')
        else:
            command('PIP BINCOPY.BIN=PATTERN.BIN')
            files=inspect(disk.read_bytes())
            assert files[(0,'BINCOPY.BIN')].data==files[(0,'PATTERN.BIN')].data
            passed('multi-record binary copy independently verified')
            at=len(output);os.write(terminal,b'KEYS\r');expect(b'KEYS START',at)
            os.write(keyboard_w,bytes(65+(i&15) for i in range(32)))
            assert b'KEYS PASS' in expect(b'A>',at);passed('local keyboard during BIOS disk writes')
            command('PIP COPY.TXT=HELLO.TXT')
            files=inspect(disk.read_bytes());assert files[(0,'COPY.TXT')].data==files[(0,'HELLO.TXT')].data
            passed('independent disk readback')
            command('RENAME RENAMED.TXT=COPY.TXT')
            assert (0,'RENAMED.TXT') in inspect(disk.read_bytes());passed('rename persisted')
            at=len(output);os.write(terminal,b'\x03');expect(b'A>',at);passed('warm boot')
            host.terminate();host.wait(timeout=10);host=None
            host=start_host();time.sleep(.5)
            assert b'Kaypro 2' in command('TYPE RENAMED.TXT');passed('host restart without guest reset')
        if a.auto:
            # Power cycle the modeled target only; the production host stays up.
            # No side channel tells the host which state/settings to expect.
            at=len(output)
            emu.terminate();emu.wait(timeout=10)
            emu=subprocess.Popen([str(ROOT/'build/kaypro-probe'),str(ROOT/'build/boot.rom'),str(wire),str(a.out/'ram.bin'),str(keyboard_r)],pass_fds=(wire,keyboard_r),stderr=log,env=dict(os.environ,KAYPRO_RESET_TRIAL="1",KAYPRO_BOOT_SYNC=str(symbols(ROOT/'build/boot-stage.lst')['sync']),KAYPRO_KEYSERVICE=str(symbols(ROOT/'build/platform.lst')['keyservice'])))
            expect(b'A>',at,120);passed('automatic ROM reset recovery with unchanged host')
            assert b'Kaypro 2' in command('TYPE HELLO.TXT')
            if not a.read_only:
                assert inspect((a.out/'session/disk.img').read_bytes())[(0,'RENAMED.TXT')].data.startswith(b'CP/M')
                passed('session writes survive automatic reboot')
        assert digest(image)==result['image_sha256'];passed('source image unchanged')
        result['complete']=True
    finally:
        if host:host.terminate();host.wait(timeout=10)
        emu.terminate();emu.wait(timeout=10)
        log.close();hostlog.close()
        result['emulator_exit']=emu.returncode
        try:
            if emu.returncode:result['complete']=False
            if result['complete']:
                logtext=(a.out/'emulator.log').read_text()
                assert ('baud=9600 wr4=4f' if a.alternate else 'baud=19800 wr4=44' if a.optimized else 'baud=19800 wr4=45') in logtext
                passed('selected serial configuration retained by CP/M')
                model=Screen();model.feed(output)
                ram=(a.out/'ram.bin').read_bytes()
                sy=symbols(ROOT/'build/platform.lst')
                cells=bytearray((a.out/'ram.bin.screen.bin').read_bytes())
                row,col=ram[sy['vrow']],ram[sy['vcol']]
                cells[row*80+col]^=128
                assert bytes(cells)==b''.join(model.cells),'CRT/host screen mismatch'
                passed('CRT and host screen equivalence')
                import re
                match=re.search(r'keyboard received=(\d+) dropped=(\d+) max_service_gap=(\d+)',(a.out/'emulator.log').read_text())
                assert match and int(match[2])==0
                assert (a.auto and int(match[3])==0) or 0<int(match[3])<83334,match[0]
                result['keyboard_max_service_gap_cycles']=int(match[3])
                passed('keyboard service gap below one 300-baud character')
                if a.corrupt_read:
                    logs=''.join(f.read_text() for f in (a.out/'session').glob('host-*.log'))
                    assert 'test-fault=read-crc injected=1' in logs and 'duplicate-valid-reply=1' in logs
                    passed('corrupt disk reply retried successfully')
        except BaseException:
            result['complete']=False
            raise
        finally:
            (a.out/'console.bin').write_bytes(output)
            (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
            for fd in (wire,device,terminal,console,keyboard_r,keyboard_w):os.close(fd)
    if not result['complete']:raise RuntimeError('qualification incomplete')
if __name__=='__main__':main()
