#!/usr/bin/env python3
"""Exercise the LED diagnostic's actual selection code, without hardware. MIT."""
import ctypes as C,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from check_drivers import symbols
lib=C.CDLL(str(ROOT/'build'/('board-test.dylib' if sys.platform=='darwin' else 'board-test.so')))
lib.board_new.restype=C.c_void_p
for name,count in [('board_call_floppy',2),('board_poke',2),('board_bank',0),('board_free',0)]:
 getattr(lib,name).argtypes=[C.c_void_p]+[C.c_uint]*count
lib.board_load.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint]
m=lib.board_new();s=symbols(ROOT/'build/drvled.lst');p=symbols(ROOT/'build/platform.lst')
try:
 for addr,file in [(0xc000,'platform.cim'),(0x100,'drvled.cim')]:
  data=(ROOT/'build'/file).read_bytes();lib.board_load(m,addr,data,len(data))
 assert lib.board_call_floppy(m,p['local_init'],0)>=0
 for old in (0x10,0x50):
  lib.board_poke(m,p['system_latch'],old)
  for name,want in [('select_c',0x11),('select_none',0x50),('select_d',0x12),('select_none',0x50)]:
   assert lib.board_call_floppy(m,s[name],0)>=0
   assert lib.board_bank(m)==want,(name,lib.board_bank(m),want)
 print('C/D/off selection and preservation of printer strobe PASS')
finally:lib.board_free(m)
