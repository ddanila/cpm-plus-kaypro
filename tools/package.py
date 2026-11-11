#!/usr/bin/env python3
"""Package only artifacts that match completed macOS and Linux qualification."""
import argparse,hashlib,io,json,tarfile
from pathlib import Path
from qualify import source_hashes
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--macos',type=Path,required=True);p.add_argument('--linux',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 reports=[json.loads((d/'qualification.json').read_text()) for d in (a.macos,a.linux)]
 manifest=json.loads((ROOT/'build/manifest.json').read_text())
 for r in reports:
  assert r['complete'] and not r['hardware_executed']
  assert r['source_sha256']==source_hashes() and r['manifest']==manifest
 assert reports[0]['platform'].startswith('macOS') and reports[1]['platform'].startswith('Linux')
 files=[ROOT/f for f in ['README.md','LICENSE','NOTICE.md','build/boot.rom','build/platform.cim','build/manifest.json','out/kaypro.img','third_party/cpm3/LICENSE.md','third_party/JUKU-LICENSE','third_party/juku-common/LICENSE']]
 files+=list((ROOT/'docs').glob('*.md'))+[ROOT/'docs/dependencies.json']
 files+=[ROOT/'tools'/f for f in ['serial_boot.py','terminal.py','diagnostics.py','serial_format.py','media.py','dependencies.py']]
 entries={str(f.relative_to(ROOT)):f.read_bytes() for f in files}
 for label,d in [('macos',a.macos),('linux',a.linux)]:
  for name in ['qualification.json','boot-result.json','driver-result.json','launcher-result.json','monitor-result.json','alternate/result.json','writable/result.json','read-only/result.json']:
   entries[f'qualification/{label}/{name}']=(d/name).read_bytes()
 if (a.macos/'mame/result.json').exists():entries['qualification/mame.json']=(a.macos/'mame/result.json').read_bytes()
 hashes=''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in sorted(entries.items()))
 entries['SHA256SUMS']=hashes.encode()
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with tarfile.open(a.output,'w:gz') as tar:
  for name,data in sorted(entries.items()):
   info=tarfile.TarInfo('kaypro-kp2-hardware-candidate/'+name);info.size=len(data);info.mode=0o644;info.mtime=0
   tar.addfile(info,io.BytesIO(data))
 print(a.output)
if __name__=='__main__':main()
