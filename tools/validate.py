#!/usr/bin/env python3
"""Structural validation of built packages; does not claim real service QA."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
R=Path(__file__).resolve().parents[1]

def check(root):
 m=json.loads((root/'.agents/plugins/marketplace.json').read_text())
 results=[]
 for item in m['plugins']:
  rp=item['source']['path']; assert rp.startswith('./') and '..' not in Path(rp).parts
  plugin=root/rp;manifest=json.loads((plugin/'.codex-plugin/plugin.json').read_text())
  assert item['name']==manifest['name'] and manifest['skills']=='./skills/'
  for key in ['skills','mcpServers']:
   if key in manifest:
    v=manifest[key];assert v.startswith('./') and '..' not in Path(v).parts and (plugin/v).exists()
  sk=plugin/'skills/competition-docs';text=(sk/'SKILL.md').read_text();assert len(text.splitlines())<100
  for file in [sk/'SKILL.md',*sorted((sk/'references').glob('*.md'))]:
   for link in re.findall(r'\]\(([^)]+)\)',file.read_text()):
    if '://' in link or link.startswith('#'):continue
    assert (file.parent/link.split('#')[0]).is_file(),(file,link)
  lock=json.loads((plugin/'bundle-lock.json').read_text())
  for p,h in lock['files'].items():assert hashlib.sha256((plugin/p).read_bytes()).hexdigest()==h,p
  for p in plugin.rglob('*'):
   assert not p.is_symlink(),p
   assert p.name not in {'.env','.config.local.toml','.DS_Store'},p
   assert '.git' not in p.parts and '__pycache__' not in p.parts,p
  subprocess.run([sys.executable,str(sk/'scripts/preflight.py'),'--formats','docx,pdf,pptx','--inputs','paper,local,github'],check=True,stdout=subprocess.DEVNULL)
  if 'mcpServers' in manifest:
   subprocess.run([sys.executable,str(plugin/'skills/ppt-master/scripts/attribution_guard.py')],check=True)
   assert 'exa' in json.loads((plugin/'.mcp.json').read_text())['mcpServers']
  results.append({'plugin':manifest['name'],'structural_validation':'passed','core_lines':len(text.splitlines()),'locked_files':len(lock['files'])})
 return results
if __name__=='__main__':
 print(json.dumps([v for variant in ['lite','bundled'] for v in check(R/'work'/('XUE-大赛PPT'+('-轻量版' if variant=='lite' else '')))],ensure_ascii=False,indent=2))
