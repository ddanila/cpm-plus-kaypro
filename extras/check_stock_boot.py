#!/usr/bin/env python3
"""Boot an IMD under independently hashed stock Kaypro II firmware in MAME. MIT."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--image',type=Path,required=True)
p.add_argument('--rom',type=Path,required=True)
p.add_argument('--chargen',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--mame',default='mame');a=p.parse_args()
rom=a.rom.read_bytes();char=a.chargen.read_bytes()
assert hashlib.sha1(rom).hexdigest()=='cd9f45cc3546bcaad7254b92c5d501c40e2ef0b2','not stock 81-232'
assert hashlib.sha1(char).hexdigest()=='5cb880083b94bd8220aac1f87d537db7cfeb9013','not stock 81-146'
a.out.mkdir(parents=True,exist_ok=False)
rdir=a.out/'roms/kayproii';rdir.mkdir(parents=True)
(rdir/'81-232.u47').write_bytes(rom);(rdir/'81-146.u43').write_bytes(char)
(rdir/'kaypro_ii-ins8048.bin').write_bytes(bytes(1024))
result=subprocess.run([a.mame,'kayproii','-bios','232','-rompath',str(rdir.parent.resolve()),
 '-flop1',str(a.image.resolve()),'-cfg_directory',str((a.out/'cfg').resolve()),
 '-video','none','-sound','none','-nothrottle','-skip_gameinfo','-autoboot_delay','0',
 '-autoboot_script',str(ROOT/'extras/check_stock_boot.lua'),'-seconds_to_run','30'],
 stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
(a.out/'boot.log').write_text(result.stdout)
ok=result.returncode==0 and all(s in result.stdout for s in ['STOCK_PC ','KAYPRO II','64k CP/M v 2.2','A>'])
report={'pass':ok,'hardware_executed':False,'image_sha256':hashlib.sha256(a.image.read_bytes()).hexdigest(),
 'boot_rom_sha256':hashlib.sha256(rom).hexdigest(),'chargen_sha256':hashlib.sha256(char).hexdigest(),
 'scope':'Stock 81-232 ROM boots disk to CP/M 2.2 A> prompt; synthetic unused keyboard MCU ROM; keyboard not tested',
 'mame_version':subprocess.check_output([a.mame,'-help'],text=True).splitlines()[0]}
(a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
assert ok,result.stdout
