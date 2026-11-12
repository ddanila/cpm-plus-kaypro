#!/usr/bin/env python3
"""Build a RAM-only CP/M transient to replace the resident Kaypro platform. MIT.

Run RELOAD from CP/M, stop its disk host after 'RELOAD READY', then use the
runtime handshake before attaching the host. The installed ROM is untouched.
"""
import argparse
import json
from pathlib import Path
from serial_boot import validate
from runtime_link import prepare

def build(platform,image,parity='N',buffering=False):
    payload=prepare(validate(image,platform),json.loads(platform.with_name('manifest.json').read_text()),parity,buffering)
    # BDOS print, DI, private SP, ~2.7 second pause, copy, loader entry C033.
    code=bytearray.fromhex('11 00 00 0e 09 cd 05 00 f3 31 00 80 06 04 11 00 00 1b 7a b3 20 fb 10 f6 21 00 00 11 00 c0 01 00 00 ed b0 c3 33 c0')
    message=b'RELOAD READY\r\n$'
    code[1:3]=(0x100+len(code)).to_bytes(2,'little')
    code[25:27]=(0x100+len(code)+len(message)).to_bytes(2,'little')
    code[31:33]=len(payload).to_bytes(2,'little')
    if 0x100+len(code)+len(message)+len(payload)>=0x8000:raise ValueError('reload overlaps stack')
    return bytes(code)+message+payload

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--platform',type=Path,default=Path('build/platform.cim'));p.add_argument('--image',type=Path,default=Path('out/kaypro.img'));p.add_argument('--parity',choices=['N','O'],default='N');p.add_argument('--buffer-console',action='store_true');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.write_bytes(build(a.platform,a.image,a.parity,a.buffer_console))
