#!/usr/bin/env python3
"""V3 diagnostics; explicit discovery never uploads or executes a payload. MIT."""
import argparse,binascii,json,os,select,secrets,sys,termios,time
from pathlib import Path
from serial_format import configure

def frame(command,nonce,payload=b'',response=False):
    if len(nonce)!=4 or len(payload)>16:raise ValueError('invalid diagnostic frame')
    body=bytes([len(payload)])+command.encode('ascii')+nonce+payload
    return (b'~R3' if response else b'~D3')+body+binascii.crc_hqx(body,65535).to_bytes(2,'big')

def query(fd,command='Q',nonce=None,timeout=2):
    from serial_boot import write_all
    nonce=nonce or secrets.token_bytes(4)
    deadline=time.monotonic()+timeout
    write_all(fd,frame(command,nonce),deadline)
    data=bytearray()
    while time.monotonic()<deadline:
        if not select.select([fd],[],[],max(0,deadline-time.monotonic()))[0]:break
        part=os.read(fd,4096)
        if not part:continue
        data.extend(part)
        while True:
            at=data.find(b'~R3')
            if at<0:
                data[:]=data[-2:];break
            if at:del data[:at]
            if len(data)<4:break
            n=data[3]
            if n>16:del data[0];continue
            size=11+n
            if len(data)<size:break
            packet=bytes(data[:size]);del data[:size]
            body=packet[3:-2]
            if binascii.crc_hqx(body,65535)!=int.from_bytes(packet[-2:],'big'):continue
            if body[1]!=ord(command) or body[2:6]!=nonce or n!=5:continue
            selector,wr4,major,minor,patch=body[6:]
            if selector>15 or wr4>>6==0 or (wr4>>2)&3 not in (1,3):continue
            return dict(selector=selector,wr4=wr4,version=[major,minor,patch],
                parity=('N' if not wr4&1 else 'E' if wr4&2 else 'O'),
                stop_bits=2 if wr4&8 else 1,multiplier=[1,16,32,64][wr4>>6],nonce=nonce.hex())
    raise TimeoutError('no matching V3 diagnostic reply')

def scan(fd,simulated=False,event=lambda x:None,dwell=16):
    for baud in [19200,19800,9600]:
        for parity in ['O','N','E']:
            try:configure(fd,baud,parity,1,simulated)
            except (OSError,ValueError,RuntimeError) as e:
                event(dict(baud=baud,parity=parity,unsupported=str(e)));continue
            termios.tcflush(fd,termios.TCIFLUSH)
            event(dict(baud=baud,parity=parity,state='searching'))
            end=time.monotonic()+dwell
            while time.monotonic()<end:
                nonce=secrets.token_bytes(4)
                try:info=query(fd,'P',nonce,.25)
                except TimeoutError:continue
                confirmed=None
                for _ in range(3):
                    try:confirmed=query(fd,'C',nonce,1);break
                    except TimeoutError:pass
                if confirmed is None:continue
                if confirmed['parity']!=parity or confirmed['stop_bits']!=1:
                    continue
                confirmed.update(host_baud=baud,host_parity=parity,host_stop_bits=1)
                event(dict(state='locked',**confirmed));return confirmed
    raise TimeoutError('scan exhausted; return ROM to defaults or choose settings manually')

def main():
    from serial_boot import Port,write_all
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['probe','scan','rx-test','tx-test'])
    p.add_argument('--serial',required=True)
    p.add_argument('--session',type=Path,default=None)
    p.add_argument('--baud',type=int,default=19200)
    p.add_argument('--parity',choices=['N','O','E'],default='O')
    p.add_argument('--stop-bits',type=int,choices=[1,2],default=1)
    p.add_argument('--duration',type=float,default=10)
    a=p.parse_args()
    if not 0<a.duration<=300:p.error('duration must be within 0..300 seconds')
    out=a.session or Path('local')/('serial-'+a.mode+'-'+str(time.time_ns()))
    out.mkdir(parents=True,exist_ok=False)
    result=dict(mode=a.mode,port=a.serial,complete=False,events=[])
    def event(e):result['events'].append(e);print(json.dumps(e),flush=True)
    port=None
    try:
        port=Port(a.serial,a.baud,a.parity,a.stop_bits)
        result['settings']=port.settings
        if a.mode=='probe':
            # V1 ignores V. Do not send a framed nonce to a legacy boot parser.
            write_all(port.fd,b'V',time.monotonic()+2)
            version=bytearray();end=time.monotonic()+2
            while time.monotonic()<end and b'\n' not in version:
                if select.select([port.fd],[],[],.1)[0]:version.extend(os.read(port.fd,256))
            result['version_reply']=version.hex()
            if not version.startswith(b'KPV3.'):
                raise RuntimeError('V3 version response absent; V1 has no version query')
            result['rom']=query(port.fd)
        elif a.mode=='scan':
            print('Select A on the Kaypro. Search is bounded to about three minutes.',flush=True)
            result['rom']=scan(port.fd,port.simulated,event)
        elif a.mode=='tx-test':
            print('Select R on the Kaypro to inspect received data.',flush=True)
            payload=bytes([0x55,0xaa,0,0xff])+bytes(range(256))
            end=time.monotonic()+a.duration;count=0
            with (out/'tx.bin').open('wb') as f:
                while time.monotonic()<end:
                    # Pace to the requested format; bounded continuous pattern.
                    for b in payload:
                        if time.monotonic()>=end:break
                        write_all(port.fd,bytes([b]),time.monotonic()+2);f.write(bytes([b]));count+=1
                        time.sleep((9+(a.parity!='N')+a.stop_bits)/a.baud)
            result['sent_bytes']=count
        else:
            print('Select T on the Kaypro to transmit the test pattern.',flush=True)
            data=bytearray();end=time.monotonic()+a.duration
            while time.monotonic()<end:
                if select.select([port.fd],[],[],.1)[0]:data.extend(os.read(port.fd,4096))
            (out/'rx.bin').write_bytes(data);result['received_bytes']=len(data)
            pattern=bytes([0x55,0xaa,0,0xff])+bytes(range(256))
            at=data.find(pattern)
            result['complete_pattern_seen']=at>=0
            result['pattern_stream_matches']=at>=0 and all(b==pattern[i%260] for i,b in enumerate(data[at:]))
        result['complete']=True
        print(json.dumps(result,indent=2));return 0
    except (OSError,RuntimeError,TimeoutError,ValueError,KeyboardInterrupt) as e:
        if port and a.mode=='scan':
            try:query(port.fd,'X',timeout=.3)
            except (OSError,TimeoutError):pass
        result['error']=str(e) or 'cancelled';print(result['error'],file=sys.stderr);return 1
    finally:
        if port:port.close()
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
