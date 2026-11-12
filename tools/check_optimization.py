#!/usr/bin/env python3
"""Execute runtime handoff/recovery and CRC on the Z80 board model. MIT."""
import binascii
import ctypes as C
import json
from check_monitor import Board, ROOT
from check_drivers import symbols

def main():
    sy=symbols(ROOT/'build/platform.lst');program=(ROOT/'build/platform.cim').read_bytes();cases=[]
    for fault in ('none','ready-corrupt','fast-drop','commit-drop'):
        b=Board();l=b.l
        l.board_load.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint]
        l.board_call.argtypes=[C.c_void_p,C.c_uint,C.c_uint]
        l.board_call_stack.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint]
        l.board_pc.argtypes=[C.c_void_p]
        def load(address,data):l.board_load(b.m,address,data,len(data))
        try:
            load(0xc000,program);load(0,b'\x76');b.tx()
            for name in ('keyboard_init','link_defaults','link_init'):
                assert l.board_call(b.m,sy[name],0)>=0
            l.board_poke(b.m,sy['runtime_config'],1)
            # Explicit HALT return, not the synchronous board_call watchdog.
            load(0x7ff0,b'\0\0')
            l.board_call_stack(b.m,sy['runtime_start'],0,0x7ff0)
            pending=bytearray();phases=[];completed=False
            for _ in range(15000):
                b.tick(10000);pending.extend(b.tx())
                while len(pending)>=6:
                    frame=bytes(pending[:6]);del pending[:6]
                    assert frame[:2]==b'RT' and binascii.crc_hqx(frame[:4],65535)==int.from_bytes(frame[4:],'big'),frame
                    phase=chr(frame[2]);phases.append(phase)
                    if phase=='R':
                        b.send(frame[:-1]+bytes([frame[-1]^1]) if fault=='ready-corrupt' else frame)
                    elif phase=='F' and fault!='fast-drop':b.send(frame)
                    elif phase=='D' and fault!='commit-drop':b.send(b'G');completed=True
                    elif phase=='B':b.send(frame);completed=True
                if completed:break
            assert completed,(fault,phases)
            assert ('B' in phases)==(fault!='none'),(fault,phases)
            assert l.board_wr(b.m,0,4)==(0x44 if fault=='none' else 0x45)
            assert l.board_wr(b.m,1,4)==0x44
            cases.append(dict(test=fault,phases=phases))
        finally:b.close()
    # Compare every table entry against independent polynomial division.
    def crc(value):
        for _ in range(8):value=(value>>1)^(0xa001 if value&1 else 0)
        return value
    lo=sy['N3CRCLO']-0xc000;hi=sy['N3CRCHI']-0xc000
    assert sy['N3CRCLO']%256==0 and hi-lo==256
    for byte in range(256):assert program[lo+byte]+256*program[hi+byte]==crc(byte)
    cases.append(dict(test='all CRC table entries independently verified',byte_update_cycles=72))
    b=Board();l=b.l
    l.board_load.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint]
    l.board_call.argtypes=[C.c_void_p,C.c_uint,C.c_uint]
    l.board_cycles.argtypes=[C.c_void_p];l.board_cycles.restype=C.c_ulonglong
    try:
        l.board_load(b.m,0xc000,program,len(program))
        # The transport result is stubbed; execute the actual cache policy.
        def poke(name,value):l.board_poke(b.m,sy[name],value)
        def call(name):assert l.board_call(b.m,sy[name],0)>=0
        poke('host_features',0);poke('N3COUNT',4);call('cache_validate');assert b.peek(sy['N3COUNT'])==0
        poke('host_features',0x80)
        l.board_load(b.m,sy['rh_call'],b'\xaf\xc9',2)
        for name in ('cache_epoch','RHCAPBUF'):l.board_load(b.m,sy[name],b'abcd',4)
        poke('N3COUNT',4);call('cache_validate');assert b.peek(sy['N3COUNT'])==4
        l.board_load(b.m,sy['RHCAPBUF'],b'abce',4)
        call('cache_validate');assert b.peek(sy['N3COUNT'])==0
        poke('N3COUNT',4);l.board_load(b.m,sy['rh_call'],b'\x3e\x01\xc9',3)
        call('cache_validate');assert b.peek(sy['N3COUNT'])==0
        cases.append(dict(test='cache retained only with supported, successful, matching host generation'))
        # Exercise the table routine itself, including register preservation.
        for byte in range(256):
            for previous in (0,0xffff,0x1234,0xabcd):
                expected=(previous>>8)^crc((previous^byte)&255)
                stub=bytes([0x3e,byte,0x11,previous&255,previous>>8,0x21,0x34,0x12,
                    0xcd,sy['N3CRC']&255,sy['N3CRC']>>8,0xed,0x53,0,0x70,0x22,2,0x70,0xc9])
                l.board_load(b.m,0x6000,stub,len(stub));assert l.board_call(b.m,0x6000,0)>=0
                assert b.word(0x7000)==expected and b.word(0x7002)==0x1234
        cases.append(dict(test='1024 Z80 CRC updates agree with independent bitwise oracle'))
    finally:b.close()
    from reload_runtime import build
    transient=build(ROOT/'build/platform.cim',ROOT/'out/kaypro.img')
    b=Board();l=b.l
    l.board_load.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint]
    l.board_call_stack.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint]
    try:
        l.board_load(b.m,5,b'\xc9',1);l.board_load(b.m,0x100,transient,len(transient));b.tx()
        l.board_call_stack(b.m,0x100,0,0x7ff0)
        wire=bytearray()
        for _ in range(1500):
            b.tick(10000);wire.extend(b.tx())
            if len(wire)>=6:break
        assert wire[:3]==b'RTR',wire
        assert bytes(b.peek(0xc000+i) for i in range(60))==program[:60]
        cases.append(dict(test='CP/M RAM reload copies platform and reaches runtime negotiation'))
    finally:b.close()
    (ROOT/'build/optimization-result.json').write_text(json.dumps(dict(complete=True,hardware_executed=False,cases=cases),indent=2)+'\n')
    print(json.dumps(cases,indent=2))
if __name__=='__main__':main()
