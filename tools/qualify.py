#!/usr/bin/env python3
"""Run the software gate and collect a self-contained qualification report."""
import argparse,hashlib,json,platform,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(*args,cwd=ROOT):subprocess.run([str(x) for x in args],cwd=cwd,check=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source_hashes():
    paths=[ROOT/'Makefile']+sorted((ROOT/'src').glob('*.asm'))+sorted((ROOT/'tools').glob('*.py'))+sorted((ROOT/'tools').glob('*.c'))+sorted((ROOT/'tools').glob('*.lua'))
    return {str(p.relative_to(ROOT)):digest(p) for p in paths}
def main():
 p=argparse.ArgumentParser();p.add_argument('--dac',type=Path,required=True);p.add_argument('--host-repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mame');a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 dac=a.dac.resolve();host=a.host_repo.resolve();result=dict(complete=False,hardware_executed=False,platform=platform.platform(),architecture=platform.machine(),python=sys.version,source_sha256=source_hashes())
 try:
  run('make','all','probe','board-test',f'DAC={dac}',f'PYTHON={sys.executable}')
  run('make','test-kaypro2',cwd=dac)
  run('bash','sync/jukuhost_linux_build.sh',cwd=host)
  run('bash','sync/jukuhost_runner_check.sh',cwd=host)
  run('bash','sync/jukuhost_core_check.sh',cwd=host)
  for name in ['boot','drivers','launcher']:
   run(sys.executable,f'tools/check_{name}.py')
  for file in ['boot-result.json','driver-result.json','launcher-result.json','manifest.json','driver-map.json']:
   shutil.copyfile(ROOT/'build'/file,out/file)
  run(sys.executable,'tools/check_runtime.py','--host',host/'build/jukuhost','--out',out/'writable')
  run(sys.executable,'tools/check_runtime.py','--host',host/'build/jukuhost','--out',out/'read-only','--read-only','--corrupt-read')
  if a.mame:run(sys.executable,'tools/check_mame.py','--mame',a.mame,'--out',out/'mame')
  result['manifest']=json.loads((out/'manifest.json').read_text())
  result['dependencies']=json.loads((ROOT/'docs/dependencies.json').read_text())
  for key,path in [('dac-emulation',dac),('8080-cosim',host)]:
   actual=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
   if actual!=result['dependencies'][key]:raise ValueError(f'{key} differs from pinned revision')
   if subprocess.check_output(['git','-C',str(path),'status','--porcelain'],text=True).strip():raise ValueError(f'{key} checkout is dirty')
  assert result['source_sha256']==source_hashes(),'sources changed during qualification'
  assert json.loads((ROOT/'build/manifest.json').read_text())==result['manifest']
  result['complete']=True
 finally:(out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
