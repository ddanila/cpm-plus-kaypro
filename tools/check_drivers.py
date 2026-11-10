#!/usr/bin/env python3
"""Execute resident guest drivers; compare against an independent screen model."""
import ctypes as C
import json
from pathlib import Path
import re
import sys
from terminal import Screen,Keys
ROOT=Path(__file__).resolve().parents[1]
def symbols(file):
    return {m[1]:int(m[2],16) for line in Path(file).read_text().splitlines()
            if (m:=re.fullmatch(r'(\w+)\s+([0-9A-F]{4})\s+\d+',line))}
def main():
    lib=C.CDLL(str(ROOT/'build'/('board-test.dylib' if sys.platform=='darwin' else 'board-test.so')))
    lib.board_new.restype=C.c_void_p
    for name in ['board_free','board_peek','board_poke','board_cell','board_bank','board_receive','board_baud','board_error','board_cycles','board_call']:
        fn=getattr(lib,name)
        counts={'board_free':0,'board_bank':0,'board_cycles':0,'board_peek':1,'board_poke':2,'board_cell':2,'board_receive':2,'board_baud':1,'board_error':1,'board_call':2}
        fn.argtypes=[C.c_void_p]+[C.c_uint]*counts[name]
    lib.board_call_stack.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint]
    lib.board_load.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint]
    lib.board_cycles.restype=C.c_ulonglong
    m=lib.board_new();assert m
    sy=symbols(ROOT/'build/platform.lst')
    data=(ROOT/'build/platform.cim').read_bytes();lib.board_load(m,0xc000,data,len(data))
    def call(name,c=0):
        result=lib.board_call(m,sy[name],c)
        assert result>=0,name
        return result
    def peek(name):return lib.board_peek(m,sy[name])
    model=Screen();cases=[]
    try:
        # Bank state must be restored by video routines; all lower RAM is a canary.
        for a in range(0x4000):lib.board_poke(m,a,(a*37+13)&255)
        call('local_init');call('keyboard_init')
        assert lib.board_baud(m,1)==300
        sequences=[b'Hello Kaypro\r\n',b'\x1b=7oZ',b'\x1a',
          b'A'*80+b'B'*80+b'C'*80,b'\x1b=!%\x18',b'\x1b=!!\x17',
          b'\x1e\x0b\x08\x0cX\x09T',b'\x1b=7 \n',b'\x1b=!!\x1bEInserted',
          b'\x1b= !\x1bR',b'\x1bG`abc\x1bAabc',b'\x1b=\x00!',b'\x1b=!\xffX',
          b'\x00\x07',b'\x1bZ?',b'\x1a'+b'line\r\n'*28]
        for sequence in sequences:
            for c in sequence:
                call('localout',c);model.feed(bytes([c]))
                assert (peek('vrow'),peek('vcol'))==(model.row,model.col)
                for y in range(24):
                    for x in range(80):
                        actual=lib.board_cell(m,y,x)
                        if (y,x)==(model.row,model.col):actual^=128
                        assert actual==model.cells[y][x],(sequence,y,x,actual,model.cells[y][x])
                assert lib.board_bank(m)==0x40
        for a in range(0x4000):assert lib.board_peek(m,a)==(a*37+13)&255,hex(a)
        cases.append('terminal controls, screen/cursor oracle and bank isolation')
        # A transient may call the BIOS with its stack below 4000.
        assert lib.board_call_stack(m,sy['localout'],ord('S'),0x2000)>=0
        assert lib.board_bank(m)==0x40
        cases.append('low-RAM caller stack survives video bank switch')
        # Actual channel-B input; overflow is visible, never hidden by an enlarged FIFO.
        expected=bytes(range(128))
        for b in bytes(range(160)):
            assert lib.board_receive(m,1,b)==0
            call('keyservice')
        assert peek('keycount')==128 and peek('keydrops')==32
        assert bytes(call('keyboard_get') for _ in range(128))==expected
        cases.append('keyboard 128-byte queue and exact drop-newest overflow')
        for _ in range(3):
            for b in range(100):
                assert lib.board_receive(m,1,b)==0;call('keyservice');assert call('keyboard_get')==b
        cases.append('keyboard queue wrap and recovery')
        assert lib.board_receive(m,1,65)==0;call('keypause');call('keyservice')
        assert call('const')==0 and peek('keycount')==1
        assert call('conin')==65
        cases.append('warm-boot input hold')
        # Mainline pure rendering must leave both SIOs alone; bell may only TX B.
        keys=Keys();assert keys.feed(b'\x1b[')==b'' and keys.feed(b'A')==b'\x0b'
        assert keys.feed(b'\x1b')==b'' and keys.flush()==b'\x1b'
        cases.append('host arrow translation and standalone escape')
        out=dict(complete=True,scope='resident driver unit tests (RAM-loaded, not a boot)',cases=cases)
        (ROOT/'build/driver-result.json').write_text(json.dumps(out,indent=2)+'\n')
        (ROOT/'build/driver-map.json').write_text(json.dumps({k:sy[k] for k in ['vrow','vcol','keyservice','keycount','keydrops','keyqueue','platform_end']},indent=2)+'\n')
        print(json.dumps(out,indent=2))
    finally:lib.board_free(m)
if __name__=='__main__':main()
