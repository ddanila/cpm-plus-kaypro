"""CRC-protected RAM runtime transition, independent of the installed ROM. MIT."""
import binascii
import json
import time
import fcntl
import os
import secrets
from pathlib import Path

PROFILES={'compat':(19200,'O'), 'fast':(19800,'N')}

def prepare(payload, manifest, parity, buffering):
    if manifest.get('runtime_link')!=1:raise ValueError('platform lacks runtime negotiation')
    data=bytearray(payload);offsets=manifest['runtime_offsets']
    offset=offsets['runtime_config']
    if data[offset:offset+2]!=b'\0D':raise ValueError('invalid runtime patch location')
    data[offset:offset+2]=bytes([1,0x44 if parity=='N' else 0x45])
    data[offsets['console_buffering']]=int(buffering)
    return bytes(data)

def receive(fd, phase, timeout=8):
    from serial_boot import exact
    end=time.monotonic()+timeout;data=bytearray()
    while time.monotonic()<end:
        data.extend(exact(fd,1,end))
        if len(data)>=6:
            frame=bytes(data[-6:])
            if frame[:3]==b'RT'+phase and binascii.crc_hqx(frame[:4],65535)==int.from_bytes(frame[4:],'big'):
                return frame
    raise TimeoutError('runtime handshake timed out')

def transition(port, baud, parity, adapter=None):
    from serial_boot import write_all
    from serial_format import configure
    old=port.settings.copy()
    def apply(rate,par):
        port.settings=configure(port.fd,rate,par,1,port.simulated)
        if adapter:port.settings['usb']=adapter.set(rate,parity={'N':0,'O':1,'E':2}[par])
    try:
        ready=receive(port.fd,b'R')
        write_all(port.fd,ready,time.monotonic()+2)
        time.sleep(.05)
        apply(baud,parity)
        probe=receive(port.fd,b'F')
        expected=0x44 if parity=='N' else 0x45
        if probe[3]!=expected:raise ValueError('target runtime framing differs')
        write_all(port.fd,probe,time.monotonic()+2)
        receive(port.fd,b'D')
        write_all(port.fd,b'G',time.monotonic()+2)
        return dict(selected='runtime',settings=port.settings)
    except (TimeoutError,ValueError,OSError) as error:
        apply(old['baud'],old['parity'])
        rollback=receive(port.fd,b'B',20)
        write_all(port.fd,rollback,time.monotonic()+2)
        return dict(selected='fallback',settings=port.settings,error=str(error))

from shared_host import load
load()
from jh_recovery import next_generation
