#!/usr/bin/env python3
"""Host-side failure, partial-I/O and terminal tests; no physical port access."""
import binascii,json,os,pty,select,sys,tempfile,threading,time,tty
import subprocess
from unittest.mock import patch
import serial_boot
from pathlib import Path
from serial_boot import Port,bootstrap,upload,exact,write_all,validate
from terminal import Screen,Keys
from diagnostics import frame,query
from serial_format import configure
ROOT=Path(__file__).resolve().parents[1]
def main():
 cases=[]
 with tempfile.TemporaryDirectory() as td:
  out=Path(td)
  # PC003 regression: an old server rejected framing options only AFTER G
  # executed the guest, leaving the CP/M loader halted. Reject it before even
  # opening the port or creating a session, for boot and attach alike.
  for mode in ('boot','attach'):
   session=out/('stale-host-'+mode)
   argv=['serial_boot.py',mode,'--serial','/dev/unused',
         '--session',str(session),'--host',sys.executable,'--console-pty','/dev/unused']
   stale=subprocess.CompletedProcess([],2,'','jukuhost: unknown option: --serial-parity\n')
   with patch.object(sys,'argv',argv), patch.object(serial_boot.subprocess,'run',return_value=stale) as run, patch.object(serial_boot,'Port') as port:
    try:serial_boot.main()
    except ValueError as e:assert 'incompatible host' in str(e)
    else:raise AssertionError('stale host accepted')
    port.assert_not_called();assert not session.exists()
    options=run.call_args.args[0]
    assert options[-1]=='--help' and '--serial-parity' in options[:-1]
  cases.append('incompatible host rejected before serial access, session creation or execution')
  def exchange(identity=b'KP2',ack=b'\x06',delay=.05):
   master,slave=pty.openpty();tty.setraw(slave);port=Port(os.ttyname(slave));assert port.simulated
   errors=[];data=bytes(range(64))
   def fake():
    try:
     assert exact(master,1,time.monotonic()+2)==b'K'
     for b in identity:
      time.sleep(delay);write_all(master,bytes([b]),time.monotonic()+2)
     if identity!=b'KP2':return
     packet=exact(master,68,time.monotonic()+3)
     assert packet==len(data).to_bytes(2,'little')+data+binascii.crc_hqx(data,65535).to_bytes(2,'big')
     write_all(master,ack,time.monotonic()+2)
    except BaseException as e:errors.append(e)
   thread=threading.Thread(target=fake);thread.start()
   try:
    if identity==b'KP2' and ack==b'\x06':bootstrap(port.fd,data,out,3)
    else:
     try:bootstrap(port.fd,data,out,3)
     except ValueError:pass
     else:raise AssertionError('invalid response accepted')
    thread.join(4);assert not thread.is_alive() and not errors,errors
    assert not select.select([master],[],[],.05)[0],'bootstrap must not execute on its own'
   finally:port.close();os.close(master);os.close(slave)
  exchange();cases.append('fragmented identity and exact CRC packet, no implicit execution')
  exchange(b'KP1');cases.append('old ROM rejected')
  exchange(ack=b'\x15');cases.append('NAK rejected without execution')
  master,slave=pty.openpty();tty.setraw(slave)
  try:
   try:bootstrap(slave,bytes(64),out,.1)
   except TimeoutError:pass
   else:raise AssertionError('missing ROM accepted')
  finally:os.close(master);os.close(slave)
  cases.append('bounded absent-ROM timeout')
  # Exercise short writes against a nonblocking pipe while a slow reader drains.
  r,w=os.pipe();os.set_blocking(w,False);received=bytearray();data=bytes(range(256))*1024
  def drain():
   while len(received)<len(data):received.extend(os.read(r,257))
  t=threading.Thread(target=drain);t.start()
  try:write_all(w,data,time.monotonic()+10);t.join(10);assert bytes(received)==data
  finally:os.close(w);os.close(r)
  cases.append('partial writes preserve 256 KiB stream')
  master,slave=pty.openpty();tty.setraw(slave)
  try:
   for parity in 'NOE':
    for stop in (1,2):configure(slave,19800,parity,stop,simulated=True)
   nonce=b'1234';reply=frame('Q',nonce,bytes([14,0x4f,3,0,0]),response=True)
   def diagnostic_reply():
    exact(master,11,time.monotonic()+2)
    bad=reply[:-1]+bytes([reply[-1]^1])
    stale=frame('Q',b'5678',bytes([14,0x4f,3,0,0]),response=True)
    write_all(master,b'noise'+bad+stale+reply,time.monotonic()+2)
   t=threading.Thread(target=diagnostic_reply);t.start()
   info=query(slave,'Q',nonce);t.join(2)
   assert info['version']==[3,0,0] and info['parity']=='E' and info['stop_bits']==2
  finally:os.close(master);os.close(slave)
  cases.append('diagnostic parser rejects noise, bad CRC and stale nonce; configurable PTY framing')
  validate(ROOT/'out/kaypro.img',ROOT/'build/platform.cim')
  bad=out/'platform.cim';bad.write_bytes(bytes(64))
  try:validate(ROOT/'out/kaypro.img',bad)
  except ValueError:pass
  else:raise AssertionError('unmatched artifacts accepted')
  cases.append('matched-artifact manifest required')
 result=dict(complete=True,hardware_executed=False,cases=cases)
 (ROOT/'build/launcher-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
