#!/usr/bin/env python3
"""Offline capability inventory. No API calls, installs, or credential output."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

SERVICES={'exa': ['exa'], 'github': ['github'], 'canva': ['canva'],
          'documents-runtime': ['load_workspace_dependencies']}
SKILLS=['documents','pdf','zotero-cli','repomix-explorer','ppt-master','slides','html-to-pptx','exa-web-search','grill-me','write-a-skill']
ALIASES={'html-to-pptx':'html-to-editable-pptx'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--formats',default=''); p.add_argument('--inputs',default='')
    p.add_argument('--tools-json',type=Path); p.add_argument('--skill-root',action='append',default=[])
    a=p.parse_args()
    names=json.loads(a.tools_json.read_text()) if a.tools_json else []
    if not isinstance(names,list) or not all(isinstance(x,str) for x in names): p.error('tools-json must be a string array')
    local=Path(__file__).resolve().parents[2]
    roots=[local,Path.home()/'.codex/skills',Path.home()/'.agents/skills']+[Path(x).expanduser() for x in a.skill_root]
    skills={}
    for n in SKILLS:
        found=next((r/sub/'SKILL.md' for r in roots for sub in [n,ALIASES.get(n,n)] if (r/sub/'SKILL.md').is_file()),None)
        skills[n]=dict(status='found' if found else 'missing',path=str(found) if found else None)
    services={k:dict(status='tool-listed-unverified' if any(all(t in n.lower() for t in terms) for n in names) else 'unknown') for k,terms in SERVICES.items()}
    commands={k:shutil.which(k) for k in ['python3','node','npx','repomix','zotero-cli','pdftoppm','soffice']}
    modules={k:bool(importlib.util.find_spec(k)) for k in ['yaml','docx','reportlab','pypdf','PIL']}
    print(json.dumps(dict(formats=a.formats.split(','),inputs=a.inputs.split(','),skills=skills,services=services,commands=commands,modules=modules,
                         note='Presence is not connectivity. Call actual tools at use time; no service authentication was tested.'),ensure_ascii=False,indent=2))
if __name__=='__main__': main()
