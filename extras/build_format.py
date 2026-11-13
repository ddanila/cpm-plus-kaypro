#!/usr/bin/env python3
"""Build a formatter bound to the exact resident platform. MIT."""
import hashlib,json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from check_drivers import symbols
sy=symbols(ROOT/'build/platform.lst')
names=['floppy_prepare','floppy_settle','floppy_wait','floppy_abort','floppy_read_sector','floppy_buffer','floppy_write_mask','floppy_home','drive','track','record','dma','system_latch','console_flush']
text='; Generated resident bindings; rebuild with the resident platform.\n'
text+=''.join(f'rt_{n}: equ 0{sy[n]:04x}h\n' for n in names)
# Immutable driver code guard: compare its complete instruction range, excluding data.
payload=(ROOT/'build/platform.cim').read_bytes()
a,b=sy['floppy_home'],sy['floppy_write_mask']
text+=f'guard_address: equ 0{a:04x}h\nguard_length: equ {b-a}\n'
(ROOT/'build/format-bindings.inc').write_text(text)
(ROOT/'build/format-guard.bin').write_bytes(payload[a-0xc000:b-0xc000])
stream=bytearray([0x4e]*80)
for sector in range(10):
 stream+=bytes(12)+bytes([0xf5]*3)+bytes([0xfe,0,0,sector,2,0xf7])+bytes([0x4e]*22)
 stream+=bytes(12)+bytes([0xf5]*3)+bytes([0xfb])+bytes([0xe5]*512)+bytes([0xf7])+bytes([0x4e]*32)
assert len(stream)==6120 and stream.count(0xf7)==20
stream+=bytes([0x4e])*(8192-len(stream))
(ROOT/'build/format-track.bin').write_bytes(stream)
(ROOT/'build/format-pattern.bin').write_bytes(bytes((i*73+19)&255 for i in range(512)))
subprocess.run([str(ROOT/'build/bin/zmac'),'--zmac','-o','build/format.cim','-o','build/format.lst','src/format.asm'],cwd=ROOT,check=True)
(ROOT/'build/format.json').write_text(json.dumps({'platform_sha256':hashlib.sha256(payload).hexdigest(),'command':'FORMAT C ERASE','physical_geometry':'40 x 10 x 512, sector IDs 0..9','format_sha256':hashlib.sha256((ROOT/'build/format.cim').read_bytes()).hexdigest()},indent=2)+'\n')
