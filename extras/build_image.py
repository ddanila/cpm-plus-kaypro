#!/usr/bin/env python3
"""Build raw sector image utility bound to resident driver. MIT."""
import sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from check_drivers import symbols
s=symbols(ROOT/'build/platform.lst')
names=['floppy_prepare','floppy_read_sector','floppy_buffer','floppy_write_mask','floppy_home','floppy_nmi_begin','floppy_write_loop','drive','track','record','dma','console_flush']
a,b=s['floppy_home'],s['floppy_write_mask']
(ROOT/'build/image-bindings.inc').write_text(''.join(f'rt_{n}: equ 0{s[n]:04x}h\n' for n in names)+f'guard_address: equ 0{a:04x}h\nguard_length: equ {b-a}\n')
(ROOT/'build/image-guard.bin').write_bytes((ROOT/'build/platform.cim').read_bytes()[a-0xc000:b-0xc000])
subprocess.run([str(ROOT/'build/bin/zmac'),'--zmac','-o','build/image.cim','-o','build/image.lst','src/image.asm'],cwd=ROOT,check=True)
