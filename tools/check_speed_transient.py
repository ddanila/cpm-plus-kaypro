#!/usr/bin/env python3
"""MIT. Stub-BDOS test of timeout/recovery logic, not x1 electrical behavior."""
import sys,ctypes as C,json,subprocess,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from check_monitor import Board
parser=argparse.ArgumentParser(description='Check RAM speed transient recovery; no physical serial access')
parser.add_argument('--out',type=Path,default=ROOT/'build/speed-transient')
p=parser.parse_args().out;p.mkdir(parents=True,exist_ok=True)
subprocess.run(['z80asm','-o',str(p/'SPEED.COM'),str(ROOT/'tools/hardware/serial-speed.asm')],check=True)
program=(p/'SPEED.COM').read_bytes();cases=[]
for mode in ('echo','error','timeout','no-ack'):
 b=Board();l=b.l;l.board_load.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint];l.board_call_stack.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint];l.board_pc.argtypes=[C.c_void_p]
 def load(a,d):l.board_load(b.m,a,d,len(d))
 try:
  load(0,b'\x76');load(5,b'\xc9');load(0x100,program);load(0x81,b' 0F 45\r');l.board_call_stack(b.m,0x100,0,0x7ff0)
  sent=bytearray()
  for _ in range(2000):
   b.tick(10000);sent.extend(b.tx())
   if len(sent)>=512:break
  assert bytes(sent[:512])==bytes(range(256))*2,(mode,len(sent))
  payload=bytes((i*73+19)&255 for i in range(4096))
  if mode in ('echo','error'):
   for i,v in enumerate(payload):
    assert not l.board_receive_status(b.m,0,v,0x10 if mode=='error' and i==0 else 0)
    b.tick(2000)
   for _ in range(2000):
    b.tick(10000);sent.extend(b.tx())
    if b'KEND' in sent[4608:]:break
   assert bytes(sent[512:4608])==payload
  else:
   for _ in range(5000):
    b.tick(10000);sent.extend(b.tx())
    if b'KEND' in sent[512:]:break
  offset=4608 if mode in ('echo','error') else 512
  for _ in range(20):b.tick(10000);sent.extend(b.tx())
  assert sent[offset:offset+4]==b'KEND',(mode,sent[-20:])
  count=int.from_bytes(sent[offset+4:offset+6],'little');errors=sent[offset+6]
  assert count==(4096 if mode in ('echo','error') else 0)
  assert errors==(0x10 if mode=='error' else 0)
  assert l.board_wr(b.m,0,4)==0x45
  if mode!='no-ack':assert not l.board_receive(b.m,0,ord('!'))
  for _ in range(20000):
   b.tick(10000)
   if l.board_pc(b.m)<=1:break
  assert l.board_pc(b.m)<=1,(mode,l.board_pc(b.m))
  cases.append(mode);print('PASS',mode,flush=True)
 finally:b.close()
(p/'emulator.json').write_text(json.dumps({'complete':True,'cases':cases,'scope':'RAM-loaded transient with stub BDOS/warm boot; no bit-level x1 or electrical qualification'},indent=2)+'\n')
