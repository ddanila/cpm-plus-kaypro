#!/usr/bin/env python3
"""Derive the loader contract from GENCPM, never a fixed BIOS size."""
from pathlib import Path
import binascii,json,hashlib
root=Path(__file__).resolve().parents[1]
s=(root/'build/cpm3.sys').read_bytes()
length=s[1]*256; top=s[0]*256; entry=int.from_bytes(s[4:6],'little')
assert top==0xc000 and s[2:4]==b'\0\0' and len(s)==length+256
assert 0x8000 < top-length < entry < top and len(s)<=16384
memory=b''.join(s[i:i+128] for i in range(len(s)-128,255,-128))
crc=binascii.crc_hqx(memory,65535)
values=dict(system_crc=crc,system_start=top-length,system_entry=entry,system_length=length,system_records=len(s)//128,system_blocks=(len(s)+2047)//2048)
assert values['system_blocks']<8
(root/'build/system.inc').write_text(''.join(f'{k} equ {v}\n' for k,v in values.items()))
(root/'build/system-map.json').write_text(json.dumps(dict(**values,system_top=top,platform_start=0xc000,platform_limit=0xf600,stack_top=0xf700,bootstrap_start=0x8000,sys_sha256=hashlib.sha256(s).hexdigest()),indent=2)+'\n')
