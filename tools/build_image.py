#!/usr/bin/env python3
"""Fresh virtual disk using the Robotron filesystem geometry and media writer."""
from pathlib import Path
import hashlib, json, zipfile
from media import add, inspect
ROOT=Path(__file__).resolve().parents[1]
def main():
    for name, expected in json.loads((ROOT/'third_party/inputs.json').read_text()).items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('input hash mismatch: '+name)
    disk=bytes([0xe5])*819200
    block=2
    def put(name,data):
        nonlocal disk,block
        disk=add(disk,name,data,system=True,start_block=block)
        block=max(inspect(disk)[(0,name)].blocks,default=block-1)+1
    put('CPM3.SYS',(ROOT/'build/cpm3.sys').read_bytes())
    put('CCP.COM',(ROOT/'third_party/cpm3/ccp.com').read_bytes())
    with zipfile.ZipFile(ROOT/'third_party/cpm3/releases/cpm3bin_unix-20260607.zip') as z:
        for name in ('dir','type','pip','erase','rename','show','set','submit'):
            put(name.upper()+'.COM',z.read(name+'.com'))
    put('HELLO.TXT',b'CP/M Plus 3.1 on Kaypro 2\r\n\x1a')
    put('PATTERN.BIN',bytes((i*73+(i>>8))&255 for i in range(8192)))
    put('SCREEN.COM',(ROOT/'build/screen-test.cim').read_bytes())
    put('KEYS.COM',(ROOT/'build/keys-test.cim').read_bytes())
    put('TEST.SUB',b'DIR HELLO.TXT\r\nTYPE HELLO.TXT\r\n\x1a')
    (ROOT/'out').mkdir(exist_ok=True)
    (ROOT/'out/kaypro.img').write_bytes(disk)
if __name__=='__main__': main()
