#!/usr/bin/env python3
"""ROM-only negative transfer tests with independently paced SIO bytes. MIT."""
import binascii,ctypes as C,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 l=C.CDLL(str(ROOT/'build'/('board-test.dylib' if sys.platform=='darwin' else 'board-test.so')))
 l.board_new.restype=C.c_void_p
 for n,args in dict(board_free=[],board_rom=[C.c_void_p,C.c_uint],board_tick=[C.c_uint],board_tx=[C.c_void_p],board_pc=[],board_receive=[C.c_uint,C.c_uint],board_peek=[C.c_uint]).items():getattr(l,n).argtypes=[C.c_void_p]+args
 rom=(ROOT/'build/boot.rom').read_bytes();m=l.board_new();assert not l.board_rom(m,rom,len(rom))
 l.board_tick(m,300000);cases=[]
 def tick(n=200000):l.board_tick(m,n)
 def receive():
  b=C.create_string_buffer(32768);n=l.board_tx(m,b);return b.raw[:n]
 def send(data):
  for b in data:
   assert l.board_receive(m,0,b)==0
   tick(1433)
  tick()
 def sync():
  send(b'K');assert receive()==b'KP2'
 def packet(data,crc=None):return len(data).to_bytes(2,'little')+data+(binascii.crc_hqx(data,65535) if crc is None else crc).to_bytes(2,'big')
 def recover(name):
  assert receive()==b'\x15',name
  cases.append(name)
 try:
  for length in [0,1,0x35,0x3600,0xffff]:
   sync();send(length.to_bytes(2,'little'));recover(f'reject length {length:04x}')
  sync();send(b'\x36');tick(4000000);recover('truncated length timeout')
  sync();send(b'\x36\x00'+b'X'*5);tick(4000000);recover('truncated payload timeout')
  data=b'\x00'*0x33+b'\xc3\x33\xc0' # self-loop at the documented entry
  sync();send(packet(data,0));recover('CRC failure')
  sync();send(packet(data)[:-1]);tick(4000000);recover('truncated CRC timeout')
  sync();send(packet(data));assert receive()==b'\x06'
  send(b'!');recover('wrong execute command')
  sync();send(packet(data));assert receive()==b'\x06'
  tick(4000000);recover('execute timeout')
  send(b'\x00!XYZ');assert receive()==b''
  sync();send(packet(data));assert receive()==b'\x06'
  assert l.board_pc(m)>=0x8000 and l.board_pc(m)<0x8400
  send(b'G');assert 0xc033<=l.board_pc(m)<=0xc036
  assert receive()==b'';cases.append('garbage recovery and execution only after valid CRC and G')
  result=dict(complete=True,hardware_executed=False,cases=cases)
  (ROOT/'build/boot-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:l.board_free(m)
if __name__=='__main__':main()
