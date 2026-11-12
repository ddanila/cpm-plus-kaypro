#!/usr/bin/env python3
"""Execute V3 monitor from reset, with externally supplied serial/key events. MIT."""
import binascii,ctypes as C,json,sys
from pathlib import Path
from check_drivers import symbols
from diagnostics import frame
ROOT=Path(__file__).resolve().parents[1]
class Board:
 def __init__(self):
  self.l=C.CDLL(str(ROOT/'build'/('board-test.dylib' if sys.platform=='darwin' else 'board-test.so')))
  self.l.board_new.restype=C.c_void_p
  for n,c in {'board_free':0,'board_tick':1,'board_peek':1,'board_poke':2,'board_cell':2,'board_receive':2,'board_receive_status':3,'board_modem':2,'board_wr':2,'board_baud':1}.items():getattr(self.l,n).argtypes=[C.c_void_p]+[C.c_uint]*c
  self.l.board_rom.argtypes=[C.c_void_p,C.c_void_p,C.c_uint];self.l.board_tx.argtypes=[C.c_void_p,C.c_void_p]
  self.m=self.l.board_new();rom=(ROOT/'build/boot.rom').read_bytes();assert not self.l.board_rom(self.m,rom,len(rom));self.tick(2000000)
 def tick(self,n=1000):self.l.board_tick(self.m,n)
 def peek(self,a):return self.l.board_peek(self.m,a)
 def word(self,a):return self.peek(a)+256*self.peek(a+1)
 def key(self,c):assert not self.l.board_receive(self.m,1,ord(c));self.tick(2000000)
 def tx(self):
  b=C.create_string_buffer(32768);n=self.l.board_tx(self.m,b);return b.raw[:n]
 def send(self,data):
  for b in data:
   assert not self.l.board_receive(self.m,0,b);self.tick(3000)
  self.tick(100000)
 def screen(self):return '\n'.join(''.join(chr(self.l.board_cell(self.m,r,c)&127) for c in range(80)).rstrip() for r in range(24))
 def close(self):self.l.board_free(self.m)
def main():
 cases=[];b=Board()
 try:
  assert not b.tx();assert b.peek(0x9002)==0
  assert b.l.board_wr(b.m,0,1)==0 and b.l.board_wr(b.m,1,4)==0x44
  assert 'Waiting for host' in b.screen() and 'Shadows' not in b.screen()
  b.key('?');assert b.peek(0x9002)==1 and 'Shadows' in b.screen()
  b.key('\x1b');assert 'Shadows' not in b.screen()
  cases.append('quiet boot screen, explicit diagnostics and escape restore')
  b.key('S');assert b.peek(0x9002)==1
  b.key('1');assert b.peek(0x9000)==5
  b.key('2');assert b.peek(0x9001)==0x47
  b.key('3');assert b.peek(0x9001)==0x4f
  b.key('4');assert b.peek(0x9001)==0x8f
  assert b.l.board_wr(b.m,0,4)==0x8f and b.l.board_wr(b.m,1,4)==0x44
  b.key('\x1b');assert b.peek(0x9002)==0 and b.peek(0x9001)==0x8f
  b.key('D');assert b.peek(0x9001)==0x45 and b.peek(0x9000)==15
  cases.append('keyboard settings, independent channel B, escape and defaults')
  b.key('K');b.key('z');assert '7A' in b.screen();b.key('\x1b')
  b.key('R');b.l.board_modem(b.m,0,0)
  assert not b.l.board_receive_status(b.m,0,0xa5,0x50);b.tick(300000)
  assert b.peek(0x9016)&0x50==0x50 and 'A5' in b.screen(),b.screen()
  b.key('\x1b');b.key('I');cases.append('receive hex, error observations and controllable modem status')
  b.key('L');assert b.peek(0x9002)==8
  # Start without the long key helper to avoid dropping the first TX.
  b.l.board_receive(b.m,1,ord('O'))
  sent=bytearray()
  for i in range(100000):
   b.tick();data=b.tx();sent.extend(data)
   for v in data:assert not b.l.board_receive(b.m,0,v)
   if b.peek(0x9002)==1:break
  assert bytes(sent)==bytes([0x55,0xaa,0,0xff])+bytes(range(256)),(len(sent),sent[:10])
  assert b.word(0x9014)==0 and b.word(0x9010)==260 and 'PASS' in b.screen(),b.screen()
  cases.append('full local loopback pattern and PASS result')
  b.key('\x1b');b.key('L');b.key('O');b.tick(1500000)
  assert b.word(0x9014)>0
  b.key('\x1b');assert b.peek(0x9002)==0
  cases.append('missing echo timeout and prompt keyboard cancellation')
  b.tx();b.key('A');assert b.peek(0x9002)==6
  nonce=b'1234';packet=frame('P',nonce)
  b.send(packet[:-1]+bytes([packet[-1]^1]));assert not b.tx()
  b.send(b'KVG');assert not b.tx()
  b.send(packet);r=b.tx();assert r.startswith(b'~R3'),r
  assert b.peek(0x9002)==7
  b.send(frame('C',b'5678'));assert not b.tx() and b.peek(0x9002)==7
  b.send(frame('C',nonce));assert b.tx().startswith(b'~R3') and b.peek(0x9002)==9
  b.send(frame('C',nonce));assert b.tx().startswith(b'~R3') and b.peek(0x9002)==9
  b.tick(6000000);assert b.peek(0x9002)==9
  b.send(frame('Q',nonce));reply=b.tx();assert reply.startswith(b'~R3')
  assert reply[11:14]==bytes([3,1,0]),reply
  b.send(frame('B',nonce));assert b.tx().startswith(b'~R3') and b.peek(0x9002)==0
  b.send(b'V');assert b.tx()==b'KPV3.1.0\r\n'
  cases.append('CRC nonce discovery, no boot interpretation, lock survives, explicit boot return')
  saved=b.word(0x9000)
  b.key('A');b.send(frame('P',nonce));assert b.tx().startswith(b'~R3')
  b.tick(8000000);b.send(frame('C',nonce));assert not b.tx() and b.peek(0x9002)==6
  b.key('\x1b');assert b.peek(0x9002)==0 and b.word(0x9000)==saved
  cases.append('expired discovery confirmation rejected; keyboard cancels scan')
  b.key('L');b.l.board_receive(b.m,1,ord('O'))
  for _ in range(100000):
   b.tick()
   for v in b.tx():assert not b.l.board_receive(b.m,0,v^1)
   if b.peek(0x9002)==1:break
  assert b.word(0x9014)==260 and 'FAIL' in b.screen()
  b.key('\x1b');b.key('D')
  cases.append('incorrect loopback echo detected for every test byte')
  # Select a nondefault configuration, then boot without returning to defaults.
  b.key('S')
  for key in '11111123':b.key(key)
  b.key('\x1b');assert b.peek(0x9000)==14 and b.peek(0x9001)==0x4f
  # Boot a self-loop payload, inspect exported contract independently.
  data=b'\x00'*0x33+b'\xc3\x33\xc0'
  b.send(b'K');assert b.tx()==b'KP2'
  b.send(len(data).to_bytes(2,'little')+data+binascii.crc_hqx(data,65535).to_bytes(2,'big'));assert b.tx()==b'\x06'
  b.send(b'G');h=bytes(b.peek(0x9cf0+i) for i in range(16))
  assert h[5:7]==bytes([14,0x4f])
  assert h[:5]==b'KP3C\x01' and binascii.crc_hqx(h[:14],65535)==int.from_bytes(h[14:],'big')
  cases.append('checked config handoff emitted only on execute')
 finally:b.close()
 result=dict(complete=True,hardware_executed=False,cases=cases)
 (ROOT/'build/monitor-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
