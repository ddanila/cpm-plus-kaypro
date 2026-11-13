#!/usr/bin/env python3
"""Cross-check selected WD1793 outcomes against independent MAME implementation."""
import argparse,json,subprocess
from pathlib import Path
from floppy_media import build
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--mame',default='mame');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False);romdir=a.out/'roms/kayproii';romdir.mkdir(parents=True)
for name,data in [('81-232.u47',(ROOT/'build/boot.rom').read_bytes()),('81-146.u43',bytes(2048)),('kaypro_ii-ins8048.bin',bytes(1024))]:(romdir/name).write_bytes(data)
disk=a.out/'fixture.kay';disk.write_bytes(build({'HELLO.TXT':b'Synthetic MAME fixture\r\n\x1a'}))
r=subprocess.run([a.mame,'kayproii','-bios','232','-rompath',str(romdir.parent.resolve()),'-flop1',str(disk.resolve()),'-cfg_directory',str((a.out/'cfg').resolve()),'-video','none','-sound','none','-nothrottle','-skip_gameinfo','-autoboot_delay','0','-autoboot_script',str(ROOT/'tools/check_mame_floppy.lua'),'-seconds_to_run','8'],capture_output=True,text=True,timeout=45)
(a.out/'mame.log').write_text(r.stdout+r.stderr)
rows=[line.split('KAYPRO_FDC ',1)[1] for line in r.stdout.splitlines() if 'KAYPRO_FDC ' in line]
assert len(rows)==1,r.stdout+r.stderr
result=json.loads(rows[0]);result['hardware_executed']=False;result['scope']='independent lost-data deadline and missing-sector status; synthetic media'
(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
assert r.returncode==0 and result['pass'],result
print(json.dumps(result,indent=2))
