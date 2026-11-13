#!/usr/bin/env python3
"""Run actual Z80 floppy routines against timed FDC; never touches real hardware."""
import ctypes as C,json,sys
from pathlib import Path
from check_drivers import symbols
ROOT=Path(__file__).resolve().parents[1]
def main():
 lib=C.CDLL(str(ROOT/'build'/('board-test.dylib' if sys.platform=='darwin' else 'board-test.so')))
 lib.board_new.restype=C.c_void_p
 for name,count in [('board_free',0),('board_call_floppy',2),('board_poke',2),('board_peek',1),('board_eject',1),('board_fault',2),('board_bank',0),('board_fdc',1),('board_key_stream',1),('board_error',1)]:
  getattr(lib,name).argtypes=[C.c_void_p]+[C.c_uint]*count
 lib.board_load.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint]
 lib.board_mount.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_uint]
 m=lib.board_new();sy=symbols(ROOT/'build/platform.lst');data=(ROOT/'build/platform.cim').read_bytes();lib.board_load(m,0xc000,data,len(data))
 def call(n,c=0):
  rc=lib.board_call_floppy(m,sy[n],c);assert rc>=0,('timeout',n);return rc
 def put(n,v):lib.board_poke(m,sy[n],v)
 def word(n,v):put(n,v&255);lib.board_poke(m,sy[n]+1,v>>8)
 def dma():return bytes(lib.board_peek(m,0x5000+i) for i in range(128))
 images=[C.create_string_buffer(bytes((i*31+(i>>9)+d*71)&255 for i in range(204800)),204800) for d in range(2)]
 cases=[]
 try:
  call('local_init');call('keyboard_init');call('floppy_home');word('dma',0x5000)
  for d,img in enumerate(images):assert lib.board_mount(m,d,img,204800,1)==0
  for d in (0,1,0):
   put('drive',d+2)
   for t,r in [(0,1),(1,2),(1,3),(1,4),(1,5),(39,40)]:
    word('track',t);word('record',r)
    rc=call('read');assert rc==0,('read',d,t,r,rc,lib.board_fdc(m,0))
    off=t*5120+(r-1)*128;assert dma()==images[d].raw[off:off+128],('data',d,t,r)
  cases.append('C/D selection, record offsets, track boundaries, seek/restore')
  call('floppy_home');call('keyboard_init');put('drive',2);word('track',39);word('record',1)
  lib.board_key_stream(m,24);assert call('read')==0
  assert lib.board_peek(m,sy['keycount'])==24 and lib.board_error(m,1)==0
  cases.append('300-baud keyboard stream survives spin-up, seek and sector transfer')
  put('drive',2);word('track',2);word('record',3)
  before=images[0].raw;assert call('write')!=0;assert images[0].raw==before
  cases.append('physical writes disabled by default')
  put('floppy_write_mask',1);payload=bytes(range(128));lib.board_load(m,0x5000,payload,128)
  rc=call('write');assert rc==0,('write status',rc,lib.board_fdc(m,0),lib.board_fdc(m,4))
  off=2*5120+2*128
  assert images[0].raw==before[:off]+payload+before[off+128:]
  assert call('read')==0 and dma()==payload
  cases.append('write-through read/modify/write preserves every neighboring byte')
  put('drive',3);assert call('write')!=0
  cases.append('C permission does not authorize D writes')
  assert lib.board_mount(m,0,images[0],204800,0)==0
  put('drive',2);assert call('write')!=0
  cases.append('physical write protection enforced')
  lib.board_fault(m,0,8);assert call('read')!=0;lib.board_fault(m,0,0)
  assert call('read')==0
  cases.append('CRC fault exhausts bounded retries and next read recovers')
  lib.board_eject(m,0);assert call('read')!=0
  cases.append('missing media returns error without hanging')
  word('track',40);assert call('read')!=0
  word('track',0);word('record',41);assert call('read')!=0
  cases.append('invalid cylinder/record rejected')
  assert not (lib.board_bank(m)&128)
  report=dict(hardware_executed=False,cases=cases,complete=True)
  print(json.dumps(report,indent=2))
  (ROOT/'build/floppy-driver-test.json').write_text(json.dumps(report,indent=2)+'\n')
 finally:lib.board_free(m)
if __name__=='__main__':main()
