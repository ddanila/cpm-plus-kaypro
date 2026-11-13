#!/usr/bin/env python3
"""Execute formatter Z80 code against timed WD1793, no real hardware. MIT."""
import ctypes as C,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from check_drivers import symbols
lib=C.CDLL(str(ROOT/'build'/('board-test.dylib' if sys.platform=='darwin' else 'board-test.so')))
lib.board_new.restype=C.c_void_p
for name,count in [('board_free',0),('board_call_floppy',2),('board_poke',2),('board_peek',1),('board_eject',1),('board_fdc',1),('board_fault',2)]:
 getattr(lib,name).argtypes=[C.c_void_p]+[C.c_uint]*count
lib.board_load.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint]
lib.board_mount.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_uint]
m=lib.board_new();p=symbols(ROOT/'build/platform.lst');s=symbols(ROOT/'build/format.lst')
def load(a,data):lib.board_load(m,a,data,len(data))
def call(a):
 rc=lib.board_call_floppy(m,a,0);assert rc>=0,('timeout',hex(a));return rc
def put(n,v):lib.board_poke(m,s[n],v)
images=[C.create_string_buffer(bytes([0x71+d])*204800,204800) for d in range(2)]
checks=[]
try:
 load(0xc000,(ROOT/'build/platform.cim').read_bytes());load(0x100,(ROOT/'build/format.cim').read_bytes())
 call(p['local_init']);call(p['keyboard_init']);call(p['floppy_home']);load(0x66,b'\x12\x34')
 for d in range(2):assert lib.board_mount(m,d,images[d],204800,1)==0
 for d in range(2):
  put('physical_drive',d)
  for track in range(40):
   put('cylinder',track);rc=call(s['format_track'])
   assert rc==0,('format',d,track,rc,lib.board_fdc(m,0),lib.board_fdc(m,4))
   assert call(s['verify_track'])==0,('verify',d,track)
   assert lib.board_peek(m,0x66)==0x12 and lib.board_peek(m,0x67)==0x34, 'NMI vector not restored'
   assert images[d].raw[track*5120:(track+1)*5120]==bytes([0xe5])*5120
  if d==0:assert images[1].raw==bytes([0x72])*204800,'C format modified D'
 checks.append('actual Z80 format + read-back of all 400 sectors on each drive; C never modifies D')
 before=images[0].raw;put('physical_drive',0);put('cylinder',0)
 assert lib.board_mount(m,0,images[0],204800,0)==0
 assert call(s['format_track'])!=0 and images[0].raw==before
 checks.append('physical write protection rejects format without changing media')
 lib.board_eject(m,0);assert call(s['format_track'])!=0
 checks.append('absent disk returns bounded error')
 put('physical_drive',2);assert call(s['format_track'])!=0
 put('physical_drive',1);put('cylinder',40);assert call(s['format_track'])!=0
 checks.append('invalid drive and track rejected')

 # Full command entry: capture completion at warm boot, stub console transport only.
 load(0xc00c,b'\xc9');load(p['console_flush'],b'\xc9');load(0,b'\x76')
 for d in range(2):assert lib.board_mount(m,d,images[d],204800,1)==0
 for tail in [b'',b' C',b' A ERASE',b' C ERASEx',b' D LOCK']:
  before=[i.raw for i in images];load(0x80,bytes([len(tail)])+tail)
  assert call(s['start'])>=0
  assert [i.raw for i in images]==before
  assert lib.board_peek(m,p['floppy_write_mask'])==0
 checks.append('invalid/bare commands never write; LOCK disables writes')
 # Deliberately incompatible resident driver must reject even valid ERASE.
 old=lib.board_peek(m,p['floppy_home']);lib.board_poke(m,p['floppy_home'],old^1)
 load(0x80,b'\x08 C ERASE');before=[i.raw for i in images]
 # const is public ABI; stub it to avoid unconfigured host polling in this unit test.
 load(0xc006,b'\xc9');assert call(s['start'])>=0
 assert [i.raw for i in images]==before
 lib.board_poke(m,p['floppy_home'],old)
 checks.append('resident code mismatch rejects destructive command')
 # Execute all 40 tracks through the public command entry and success path.
 for d in range(2): images[d].raw=bytes([0x71+d])*204800
 load(0x80,b'\x08 C ERASE')
 rc=lib.board_call_floppy(m,s['start'],0)
 lib.board_tick.argtypes=[C.c_void_p,C.c_uint];lib.board_pc.argtypes=[C.c_void_p]
 for _ in range(60):
  if rc>=0 or lib.board_pc(m)==1:break
  lib.board_tick(m,2000000)
 else:raise AssertionError('full format command timed out')
 assert images[0].raw==bytes([0xe5])*204800, ('full command',rc,lib.board_pc(m),lib.board_peek(m,s['cylinder']),lib.board_peek(m,s['failure']),sum(v==0xe5 for v in images[0].raw))
 assert images[1].raw==bytes([0x72])*204800
 assert lib.board_peek(m,p['floppy_write_mask'])==1
 checks.append('full FORMAT C ERASE command formats only C and enables only C writes')
 load(0x80,b'\x08 C ERASE');lib.board_fault(m,0,8)
 assert call(s['start'])>=0
 assert lib.board_peek(m,p['floppy_write_mask'])==0
 assert call(s['verify_track'])!=0
 assert lib.board_peek(m,s['read_tries'])==0
 assert lib.board_peek(m,s['cylinder'])==0
 lib.board_fault(m,0,0)
 checks.append('controller fault stops format, disables writes; persistent read CRC exhausts three attempts')
 before=[i.raw for i in images];load(0x80,b'\x07 C TEST')
 assert call(s['start'])>=0
 expected=bytes((i*73+19)&255 for i in range(512))
 assert images[0].raw[:512]==expected and images[0].raw[512:]==before[0][512:]
 assert images[1].raw==before[1]
 assert bytes(lib.board_peek(m,s['readback']+i) for i in range(512))==expected
 assert lib.board_peek(m,p['floppy_write_mask'])==0
 checks.append('raw TEST command writes/reads exact 512-byte pattern on track zero only, then disables writes')
 result={'hardware_executed':False,'complete':True,'checks':checks}
 (ROOT/'build/format-test.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:lib.board_free(m)
