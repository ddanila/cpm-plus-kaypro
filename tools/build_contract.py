#!/usr/bin/env python3
"""Fail the build on memory-map violations; emit a matched-artifact manifest."""
import hashlib,json,re
from pathlib import Path
from check_drivers import symbols
ROOT=Path(__file__).resolve().parents[1]
def main():
    sy=symbols(ROOT/'build/platform.lst')
    assert sy['platform_end']<=0xf600,'resident platform encroaches on stack clearance'
    rom=(ROOT/'build/boot.rom').read_bytes()
    platform=(ROOT/'build/platform.cim').read_bytes()
    assert len(rom)==4096
    version=re.findall(rb'Kaypro serial boot ROM v(\d+\.\d+\.\d+)\r\n',rom)
    assert len(version)==1,'ROM must contain exactly one firmware version banner'
    assert 0x36<=len(platform)<=0x35ff
    assert len(platform)==sy['platform_end']-0xc000
    assert len((ROOT/'build/boot-stage.cim').read_bytes())<=0x1000
    assert symbols(ROOT/'build/boot.lst')['stage_end']<=4096
    assert sy['loader']>=0xc03c and platform[0x33]==0xc3
    files={'boot.rom':ROOT/'build/boot.rom','platform.cim':ROOT/'build/platform.cim','kaypro.img':ROOT/'out/kaypro.img'}
    manifest=dict(serial_handoff=1,diagnostic_protocol='D3',rom_version=version[0].decode('ascii'),protocol='KP2',framing='19200 8O1',hardware_executed=False,
      sha256={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()},
      sizes={k:p.stat().st_size for k,p in files.items()},
      rom_used=symbols(ROOT/'build/boot.lst')['stage_end'],
      rom_free=4096-symbols(ROOT/'build/boot.lst')['stage_end'],
      memory=dict(platform_start=0xc000,platform_end=sy['platform_end'],platform_limit=0xf600,
                  stack_top=0xf700,system_start=0x9d00,system_top=0xc000,bootstrap_start=0x8000))
    (ROOT/'build/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
