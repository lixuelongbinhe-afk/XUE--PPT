#!/usr/bin/env python3
"""Build two local Codex distributions. Copies only explicitly allowlisted vendors."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
import os

ROOT=Path(__file__).resolve().parents[1]
SELECTED_VARIANTS=['lite','bundled']
VENDORS={
 'ppt-master':Path.home()/'.codex/skills/ppt-master',
 'slides':Path.home()/'.codex/skills/slides',
 'html-to-pptx':Path.home()/'.codex/skills/html-to-editable-pptx',
 'exa-web-search':Path.home()/'.codex/plugins/cache/codex-exa/exa/0.2.0',
}
IGNORE={'.git','.DS_Store','__pycache__','node_modules','.venv','venv','.config.local.toml','lessons-learned.md','.env','plugins','assets/slides-demo.mp4'}

def jwrite(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe_copy(src,dst):
 for p in sorted(src.rglob('*')):
  rel=p.relative_to(src)
  if any(x in IGNORE for x in rel.parts) or str(rel) in IGNORE or p.suffix in {'.pyc','.pyo'}:continue
  if p.is_symlink():raise ValueError('vendor symlink not allowed: '+str(p))
  if p.is_file():
   q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)

def build(out):
 out.mkdir(parents=True,exist_ok=True)
 for key in VENDORS:
  override=os.environ.get('XUE_VENDOR_'+key.upper().replace('-','_'))
  if override: VENDORS[key]=Path(override).expanduser().resolve()
 for variant in SELECTED_VARIANTS:
  dist=ROOT/'work'/('XUE-大赛PPT'+('-轻量版' if variant=='lite' else ''))
  if dist.exists():shutil.rmtree(dist)
  dist.mkdir(parents=True)
  name='xue-contest-ppt'+('-lite' if variant=='lite' else '')
  plug=dist/'plugins'/name
  safe_copy(ROOT/'plugins/competition-docs-core',plug)
  interface=dict(displayName='XUE-大赛PPT',
   shortDescription='依据竞赛要求和论文或项目生成可追溯的竞赛材料',
   longDescription='按需编排技术报告、创新创业计划书、DOCX/PDF/PPTX，支持 Canva、Zotero、GitHub、Exa、断点恢复和质量检查。',
   developerName='Competition Docs contributors',category='Productivity',capabilities=['Read','Write'],
   defaultPrompt=['根据竞赛要求和我的论文或项目，按需生成参赛材料。'])
  manifest=dict(name=name,version='0.1.1',description='Evidence-based competition document orchestration for Codex.',
   author={'name':'Competition Docs contributors'},license='MIT',skills='./skills/',interface=interface)
  # Codex compatibility layout is intentional for the installed client; no invented dependency fields.
  jwrite(plug/'.codex-plugin/plugin.json',manifest)
  agent=plug/'skills/competition-docs/agents/openai.yaml';agent.parent.mkdir(parents=True)
  agent.write_text('interface:\n  display_name: "XUE-大赛PPT"\n  short_description: "按竞赛要求整合论文与项目，生成可核验、可恢复的参赛文档和答辩材料"\n  default_prompt: "使用 $competition-docs，根据竞赛要求与我的论文或项目按需生成参赛材料。"\n')
  deps={
   'schema':1,'variant':variant,'note':'Documentation inventory, not a host automatic-install manifest.',
   'services':[{'id':s,'required_when':cond,'bundled_config':variant=='bundled' and s=='exa','authentication':'user connection required'} for s,cond in [('exa','external research'),('canva','PPT design/templates'),('documents','DOCX'),('pdf','PDF input/output'),('github','GitHub repository input')]],
   'skills':[{'id':s,'delivery':'bundled' if variant=='bundled' and s in VENDORS else 'external'} for s in ['zotero-cli','repomix-explorer','ppt-master','slides','html-to-pptx','exa-web-search','grill-me','write-a-skill']],
   'executables':['python3','zotero-cli','repomix or npx','node for HTML/PPT tools'],
   'rendering':'Use resolved host bundled runtime first; verify actual renderer per output format.',
   'not_redistributed':'Documents, PDF, Canva, GitHub service plugins; credentials; Zotero executable; Repomix executable; model/OS runtimes.',
  }
  jwrite(plug/'dependencies.json',deps)
  license_text='''MIT License

Copyright (c) 2026 Competition Docs contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''
  (plug/'LICENSE').write_text(license_text)
  locks=[]
  if variant=='bundled':
   for key,src in VENDORS.items():
    if not (src/'LICENSE').is_file() or 'Permission is hereby granted' not in (src/'LICENSE').read_text():
     raise ValueError('missing verified redistributable license: '+key)
    target=plug/'skills'/key
    if key=='exa-web-search':
     safe_copy(src/'skills/exa-web-search',target)
     shutil.copy2(src/'LICENSE',target/'LICENSE');shutil.copy2(src/'NOTICE.md',target/'NOTICE.md')
    else:safe_copy(src,target)
    # Keep exact contents; remapped folder name only. Internal paths remain relative.
    locks.append(dict(name=key,license='MIT',files=sum(p.is_file() for p in target.rglob('*'))))
   exa=json.loads((VENDORS['exa-web-search']/'.mcp.json').read_text())
   jwrite(plug/'.mcp.json',exa)
   manifest['mcpServers']='./.mcp.json';jwrite(plug/'.codex-plugin/plugin.json',manifest)
   subprocess.run(['python3',str(plug/'skills/ppt-master/scripts/attribution_guard.py')],check=True)
  jwrite(plug/'bundle-lock.json',{'vendors':locks,'files':{str(p.relative_to(plug)):sha(p) for p in sorted(plug.rglob('*')) if p.is_file()}})
  (plug/'THIRD_PARTY_NOTICES.md').write_text('''# 第三方与服务边界

本插件自编排内容为 MIT；第三方原文件按各自 LICENSE 和 NOTICE 分发，不表示服务所有者为本插件背书。

整合版内置：PPT Master（Hugo He，MIT）、Slides（Robbert van Empel，MIT）、HTML to PPTX（Phil，MIT）、Exa 社区插件技能/配置（Codex Exa contributors，MIT）。其许可证位于各 skills 子目录。PPT Master 内含第三方图标、声音和 OOXML 数据，其目录内 THIRD_PARTY_NOTICES/NOTICE 和附加许可证一并保留，使用品牌图标时仍应核实品牌规则。

Documents/PDF/Canva/GitHub 不包含在包中，必须安装/连接原插件；本地 Zotero 与 Repomix 技能没有找到明确可再分发许可，仅列依赖。grill-me/write-a-skill 同样外置，总控中提供独立编写的必要交互和维护规则。字体、模型、浏览器、Office/LibreOffice、账户和用户数据不随包分发。

Exa 连接参数来自本机已安装的 MIT 社区插件；真正搜索仍需要可用服务和用户连接。轻量版不会注册 Exa MCP；整合版会提供 Exa MCP 配置，已有独立 Exa 连接时二选一避免重复。
''')
  market=dict(name='xue-competition-tools'+('-lite' if variant=='lite' else ''),interface={'displayName':'XUE 竞赛工具'},plugins=[dict(name=name,source={'source':'local','path':'./plugins/'+name},policy={'installation':'AVAILABLE','authentication':'ON_INSTALL'},category='Productivity')])
  jwrite(dist/'.agents/plugins/marketplace.json',market)
  shutil.copy2(ROOT/'DECISIONS.md',dist/'DECISIONS.md')
  (dist/'README.md').write_text(f'''# XUE-大赛PPT {variant} 0.1.1

这是 Codex 本地插件包，包含总控 Skill、依赖清单、恢复脚本和验收流程；不是独立网站，也不会自动安装所有依赖。两版共用核心流程，二选一启用。

## 安装

解压到固定位置，避免以后删除该目录。将下面 `<解压后目录>` 替换为含 `.agents/` 和 `plugins/` 的目录。使用已安装 Codex CLI：

```bash
codex plugin marketplace add "<解压后目录>"
codex plugin add {name}@xue-competition-tools{'-lite' if variant=='lite' else ''}
```

重新打开 Codex 后，在插件目录选择此来源并检查已安装状态；必要时刷新客户端，在新聊天启用插件。支持的客户端入口可能不同，CLI 以本机 `codex plugin --help` 为准。不要将轻量版和整合版同时启用。

无需 CLI 时，可将本包作为一个 Codex 项目打开，让客户端发现 `.agents/plugins/marketplace.json` 后从对应本地来源安装。不要把 `dependencies.json` 当成自动安装器。

## 依赖

轻量版依赖已安装技能；整合版额外内置 ppt-master、slides、html-to-pptx、Exa 技能及 MCP 配置，保留上游许可。两版均需按任务连接 Documents、PDF、Canva、GitHub；论文还需 Zotero CLI 与可用文献库，本地代码需要 Repomix。Exa 是外部研究的默认依赖；整合版的 MCP 配置不包含账户凭据。

只装任务涉及的依赖。详见 `plugins/{name}/dependencies.json` 和 `THIRD_PARTY_NOTICES.md`。本包不携带 Zotero/Repomix 可执行程序、渲染器或模型，不是离线环境。

## 使用

在启用插件的新聊天中输入：

> 使用 $competition-docs。根据这份竞赛要求、我的论文和项目，生成技术报告 DOCX/PDF 与 8 分钟答辩 PPTX。论文统一入 Zotero；项目默认只读，运行验证前先问我。

提供竞赛要求文件和论文/项目路径或 GitHub URL。输出未明确时会询问。技术/创业混合任务共享证据，PPT 先使用 Canva 参考或实际可导出的模板，再自动选择生成路线。

工作记录存用户任务目录；恢复时提供该目录即可。workflow.py 是状态/失效辅助器，不是自动生成文档的 CLI；实际工具由 Codex 按总控技能编排。

## 更新与卸载

修改插件源后更新版本并刷新 marketplace/重装，再开新聊天。卸载使用 `codex plugin remove --help` 确认本机语法，从插件目录关闭或卸载。删除此安装包不会删除任务成果，也不会撤销服务授权；账户连接由原服务管理。

## 验证范围

本版本已验证技能格式、打包路径、上游完整性关卡与状态脚本。构建验证结果见随交付提供的验收报告。连接真实账户、获取 Canva 模板、论文入库和全格式渲染属于安装后的端到端验收，未拿到实际参赛材料前不能声称完成。验收情景在技能 `references/scenarios.md`。

安装格式依据：https://developers.openai.com/plugins/build/plugins 。采用当前 Codex 支持的 `.codex-plugin/plugin.json` 兼容格式与 repo marketplace，源码不修改用户全局配置。
''')
  archive=out/(dist.name+'.zip')
  with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   for p in sorted(dist.rglob('*')):
    if p.is_file(): z.write(p,str(Path(dist.name)/p.relative_to(dist)))
  print(json.dumps({'variant':variant,'directory':str(dist),'zip':str(archive),'bytes':archive.stat().st_size},ensure_ascii=False))

def main():
 global SELECTED_VARIANTS
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--variant',choices=['lite','bundled','all'],default='all');a=p.parse_args();SELECTED_VARIANTS=['lite','bundled'] if a.variant=='all' else [a.variant];build(a.out.resolve())
if __name__=='__main__':main()
