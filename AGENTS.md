# Competition Docs

先读 DECISIONS.md。源码总控位于 plugins/competition-docs-core/；tools/build.py 生成两版和压缩包，禁止直接修生成目录。保持上游 vendor 原始内容与许可证，不改 ppt-master 完整性关卡。

运行 `python3 -m unittest discover -s tests -v` 验证状态失效与质量门；再运行 tools/validate.py，最后用宿主官方 quick_validate.py 验证总控技能。测试仅使用隔离临时目录，不连接用户 Zotero/Canva，不运行用户项目。

安装测试仅可使用隔离 CODEX_HOME。真实用户配置/账户连接不是构建包必需步骤。不得自动启用两版，或将凭据、本机偏好、缓存、运行时、源码包和个人材料纳入交付。
