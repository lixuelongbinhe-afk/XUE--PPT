# 依赖与工具路由

## 发现规则
先看当前宿主已加载技能和工具，按明确入口读取；不编造工具名。整合版技能位于本插件 `skills/` 下，轻量版由已安装依赖提供。工具调用必须使用当前真实 schema。下表是能力标识，不保证某个固定名称存在。

| 依赖 | 使用条件 | 实际用途 | 失败替代 |
|---|---|---|---|
| Exa MCP + exa-web-search | 外部信息缺口 | 搜索并抓取原文，优先一手来源 | 其他可用联网检索；没有则标未核实 |
| Documents 插件 | DOCX、Word 论文读取/转 PDF | 模板、编辑、render_docx 与逐页检查 | 可用文档工具生成草稿，记录质量损失 |
| PDF 插件 | PDF 材料和 PDF 交付 | 提取、表格/公式页面确认、渲染 | 可用解析/渲染器；未渲染不能视觉通过 |
| Canva 插件 | PPT | 风格参考、账户可访问设计、候选生成、可用模板导出 | 已提供本地模板或本地风格预览 |
| GitHub 官方 MCP | GitHub 仓库 | 固定 ref/commit 读取目录、源码、README | 用户已有本地副本 → Repomix；或可用只读仓库工具 |
| zotero-cli 技能与命令 | 论文 | 去重导入、元数据、全文、引用 | 入库失败可直接读取副本，记录 Zotero 流程未完成 |
| repomix-explorer + Repomix CLI | 本地项目 | 打包、检索、架构证据 | rg/read 定向探索，记录覆盖范围 |
| ppt-master | 原生模板或原生 PPTX 优先 | 编辑原生 PPTX或生成新 PPTX | slides → html-to-pptx；仍失败则保留中间稿 |
| slides | HTML 展示或适合 HTML 重建 | 单文件固定舞台 HTML | ppt-master |
| html-to-pptx | slides 需要 PPTX 交付 | convert.py、结构检查、视觉审查 | 可用 PPTX 工具重建；HTML/PDF 不算 PPTX 已完成 |
| grill-me | 关键歧义 | 一次一问，给推荐答案 | 内置相同交互规则 |
| write-a-skill | 用户要维护插件本身 | 技能结构、渐进披露、检查 | 内置维护说明；不在每次参赛任务中调用 |

第一版仅编排 Codex，不提供 Claude Code 适配。GitHub 指 GitHub 仓库；其他托管站不强套 GitHub MCP。

## 预检
`python3 <技能目录>/scripts/preflight.py --formats docx,pdf,pptx --inputs paper,local,github --tools-json work/tools.json`

tools.json 为当前真实可调用工具名组成的 JSON 数组；可省略，但此时 MCP 状态只能 unknown。不要把安装文件、配置 URL、命令存在或工具名存在当作授权/连通成功。初次实际调用成功才升级为可用。CLI 不输出凭据，也不调用打印敏感设置的命令；Zotero config 只在需要诊断时运行，输出过滤后再保存。

脚本默认查插件内技能和用户技能目录，其他插件技能使用 `--skill-root <实际包含技能子目录的目录>` 显式补入；不扫描整个磁盘。检查报告为自定义依赖台账，不是宿主会自动安装的依赖协议。

## 两版边界
轻量版所有上游工具外置；整合版只内置有明确许可的 ppt-master、slides、html-to-pptx、Exa 技能及 Exa MCP 接入配置。Documents、PDF、Canva、GitHub 为外部服务/插件；Zotero CLI 与 Repomix 命令和语言运行时不在压缩包中。缺少明确本地许可的技能保持外部依赖。整合版不等于离线版。

两个版本二选一启用，避免同名总控技能和 Exa 服务重复。若已经连接独立 Exa 插件，优先复用；不要新建第二条连接。外部服务账户、套餐、字体、模型和渲染器在使用时检测，不自动付费、下载大模型或安装用户字体。

首次使用不必配置所有依赖；仅提示当前任务缺项。失败的只读工具优先自动替代，不在每次运行中重复要求安装全套。
