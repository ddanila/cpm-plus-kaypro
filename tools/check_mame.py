#!/usr/bin/env python3
"""Independent ROM startup check; synthetic unused display/keyboard fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--mame', default='mame')
p.add_argument('--out', type=Path, default=ROOT / 'local/mame-check')
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=False)
romdir = a.out / 'roms/kayproii'
romdir.mkdir(parents=True)
rom = (ROOT / 'build/boot.rom').read_bytes()
assert len(rom) == 4096
(romdir / '81-232.u47').write_bytes(rom)
(romdir / '81-146.u43').write_bytes(bytes(2048))
(romdir / 'kaypro_ii-ins8048.bin').write_bytes(bytes(1024))
r = subprocess.run([a.mame, 'kayproii', '-bios', '232', '-rompath', str(romdir.parent.resolve()),
    '-video', 'none', '-sound', 'none', '-nothrottle', '-skip_gameinfo',
    '-autoboot_delay', '0', '-autoboot_script', str(ROOT / 'tools/check_mame.lua'),
    '-seconds_to_run', '5'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=45)
(a.out / 'startup.log').write_text(r.stdout)
lines = [line.split('KAYPRO_STARTUP ', 1)[1] for line in r.stdout.splitlines() if 'KAYPRO_STARTUP ' in line]
assert len(lines) == 1, r.stdout
result = json.loads(lines[0])
result['rom_sha256'] = hashlib.sha256(rom).hexdigest()
result['mame_version'] = subprocess.check_output([a.mame, '-help'], text=True).splitlines()[0]
result['hardware_executed'] = False
result['scope'] = 'ROM reset, relocation, RAM bank switch, serial RX wait; synthetic character and keyboard ROMs'
(a.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
assert r.returncode == 0 and result['pass'], r.stdout
print(json.dumps(result, indent=2))
