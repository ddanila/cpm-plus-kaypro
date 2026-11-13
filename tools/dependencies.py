#!/usr/bin/env python3
"""Fetch isolated, pinned dependency checkouts. Existing dirty trees are rejected."""
import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'build/deps');p.add_argument('--host-only',action='store_true');a=p.parse_args()
 pins=json.loads((ROOT/'docs/dependencies.json').read_text())
 for name in (['8080-cosim'] if a.host_only else ['dac-emulation','8080-cosim']):
  path=(a.out/name).resolve()
  def git(*args):return subprocess.check_output(['git','-C',str(path),*args],text=True).strip()
  if not path.exists():
   path.mkdir(parents=True);git('init');git('remote','add','origin',f'https://github.com/ddanila/{name}.git')
  if git('status','--porcelain'):raise ValueError(f'dirty dependency checkout: {path}')
  git('config','remote.origin.promisor','true')
  git('config','remote.origin.partialclonefilter','blob:none')
  git('sparse-checkout','init','--cone')
  paths=['common','machines/kaypro2','machines/juku','tests','third_party/cpu/chips'] if name=='dac-emulation' else ['host','sync','tests/fixtures/jukuhost']
  git('sparse-checkout','set',*paths)
  git('fetch','--filter=blob:none','--depth','1','origin',pins[name]);git('checkout','--detach',pins[name])
  assert git('rev-parse','HEAD')==pins[name]
  print(path)
if __name__=='__main__':main()
