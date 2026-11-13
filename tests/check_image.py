#!/usr/bin/env python3
"""Raw imager instruction-level WD1793 and strict IMD regression checks. MIT."""
import ctypes as C,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'extras')]
from check_drivers import symbols
from kaypro_imd import decode,encode
raw=bytes((i*73+i//512)&255 for i in range(204800))
assert decode(encode(raw))==raw
compressed=bytearray(b'IMD fixture\x1a')
for t in range(40):
 compressed+=bytes([5,t,0,10,2])+bytes(range(9,-1,-1))
 for sec in range(9,-1,-1):compressed+=bytes([2,(t*10+sec)&255])
assert decode(bytes(compressed))==b''.join(bytes([i&255])*512 for i in range(400))
bad_sector=bytearray(encode(raw));bad_sector[bad_sector.index(26)+1+15]=5
for bad in [bytes(bad_sector),encode(raw)[:-1],encode(raw)+encode(raw)[encode(raw).index(b'\x1a')+1:],encode(raw).replace(bytes([5,0,0,10,2]),bytes([5,0,1,10,2]),1)]:
 try:decode(bad)
 except ValueError:pass
 else:raise AssertionError('accepted malformed image')
lib=C.CDLL(str(ROOT/'build'/('board-test.dylib' if sys.platform=='darwin' else 'board-test.so')))
lib.board_new.restype=C.c_void_p
for n,c in [('board_free',0),('board_call_floppy',2),('board_poke',2),('board_peek',1),('board_eject',1),('board_fault',2),('board_tick',1),('board_pc',0)]:
 getattr(lib,n).argtypes=[C.c_void_p]+[C.c_uint]*c
lib.board_load.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint]
lib.board_mount.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_uint]
m=lib.board_new();p=symbols(ROOT/'build/platform.lst');s=symbols(ROOT/'build/image.lst')
def load(a,b):lib.board_load(m,a,b,len(b))
def peek(a,n):return bytes(lib.board_peek(m,a+i) for i in range(n))
def put(n,v):lib.board_poke(m,s[n],v)
def call(a):
 rc=lib.board_call_floppy(m,a,0)
 assert rc>=0,('timeout',hex(a))
 return rc
images=[C.create_string_buffer(bytes([0xe5])*204800,204800) for _ in range(2)]
checks=[]
try:
 load(0xc000,(ROOT/'build/platform.cim').read_bytes());load(0x100,(ROOT/'build/image.cim').read_bytes())
 call(p['local_init']);call(p['keyboard_init']);call(p['floppy_home']);load(0x66,b'\x12\x34')
 for d in range(2):assert lib.board_mount(m,d,images[d],204800,1)==0
 for t in range(40):
  put('cylinder',t);track=raw[t*5120:(t+1)*5120];load(s['buffer'],track)
  assert call(s['write_track'])==0,('write',t)
  assert images[0].raw[t*5120:(t+1)*5120]==track
  load(s['buffer'],bytes(5120));assert call(s['read_track_raw'])==0
  assert peek(s['buffer'],5120)==track
  assert peek(0x66,2)==b'\x12\x34'
 assert images[0].raw==raw and images[1].raw==bytes([0xe5])*204800
 checks.append('400 raw sector writes + immediate verification + separate full readback; D untouched; NMI vector restored')
 put('cylinder',40);assert call(s['write_track'])!=0
 put('cylinder',0);before=images[0].raw
 lib.board_mount(m,0,images[0],204800,0);assert call(s['write_track'])!=0 and images[0].raw==before
 lib.board_eject(m,0);assert call(s['write_track'])!=0
 lib.board_mount(m,0,images[0],204800,1);lib.board_fault(m,0,8)
 assert call(s['write_track'])!=0;lib.board_fault(m,0,0)
 checks.append('invalid cylinder, write-protected/absent media and CRC error rejected')
 # Run complete guest command with a deterministic BDOS filesystem fixture.
 load(0xc00c,b'\xc9');load(p['console_flush'],b'\xc9');load(0,b'\x76')
 load(5,b'\xc3\x00\x76');load(0x7600,(ROOT/'build/image-bdos.cim').read_bytes())
 def entry(tail):
  load(0x100,(ROOT/'build/image.cim').read_bytes())
  load(0x80,bytes([len(tail)])+tail)
  rc=lib.board_call_floppy(m,s['start'],0)
  for _ in range(160):
   if rc>=0 or lib.board_pc(m)==1:break
   lib.board_tick(m,2000000)
  else:raise AssertionError('full command timeout')
 for tail in [b'',b' D ERASE',b' C ERASEx',b' C READx']:
  before=images[0].raw;entry(tail);assert images[0].raw==before
 before=images[0].raw
 load(0x7f06,b'\x01');entry(b' C ERASE');assert images[0].raw==before and peek(s['failure'],1)==b'\x01'
 load(0x7f06,b'\x00');load(0x7f04,b'\x00');entry(b' C READ');assert peek(s['failure'],1)==b'\x01'
 old=peek(p['floppy_home'],1);load(p['floppy_home'],bytes([old[0]^1]))
 entry(b' C ERASE');assert images[0].raw==before
 load(p['floppy_home'],old)
 checks.append('resident mismatch and source size error rejected before writes; existing readback refused')
 load(0x7f02,b'\x00\x80');load(0x8000,raw[:5120]);load(0x7f04,b'\x00')
 entry(b' C ERASE')
 assert peek(s['failure'],1)==b'\0' and images[0].raw==raw[:5120]*40
 assert peek(p['floppy_write_mask'],1)==b'\0'
 checks.append('full C ERASE command including BDOS reads and resident selection restoration; invalid commands never write')
 load(0x7f02,b'\x00\x80');load(0x7f04,b'\x01')
 entry(b' C READ')
 assert peek(s['failure'],1)==b'\0' and peek(0x7f05,1)==b'\0'
 assert peek(p['floppy_write_mask'],1)==b'\0'
 checks.append('full C READ command including BDOS output-byte comparison and close')
 load(0x7f02,b'\x00\x80');load(0x7f04,b'\x00');lib.board_fault(m,0,8)
 entry(b' C ERASE')
 assert peek(s['failure'],1)==b'\x01' and peek(s['cylinder'],1)==b'\x00'
 assert peek(p['floppy_write_mask'],1)==b'\0'
 checks.append('full write command stops at first controller error and disables physical writes')
 result={'hardware_executed':False,'complete':True,'checks':checks}
 (ROOT/'build/image-test.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:lib.board_free(m)
