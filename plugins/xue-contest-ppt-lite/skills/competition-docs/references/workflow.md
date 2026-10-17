# 流程与恢复

## 任务文件
任务目录内保留 `state.json`、`requirements.json`、`sources.json`、`claims.json`、`decisions.json`、`issues.json`、`qa.json` 和 `work/`；`outputs/` 仅存请求交付物。可按阶段创建这些 JSON，不必在启动时制造空文件。状态脚本只负责持久化和依赖失效，不会替代理解材料、调用模型或生成文档。

- requirements：id、原始要求、source_locator、mandatory、target_artifacts、acceptance、status。
- sources：id、kind、title、locator、version/commit、content_hash、retrieved_at、access_scope。Zotero 保存 library_id、item_key、attachment_key；代码保存相对路径和行号。
- claims：id、text、type、source_ids、source_locator、scope、confidence、used_by。type 区分 verified、source_reported、assumption、planned、missing。
- decisions：问题、选择、适用范围、用户原话或消息依据；缺少证据不能记成已批准。
- issues：节点、时间、错误、尝试次数、替代方案、损失、影响要求、状态；最终集中汇总。不要保存令牌、凭据或原始环境变量。

## 状态脚本
用绝对技能目录调用，下面命令以任务目录为当前目录示意；不使用插件目录保存运行状态。

```bash
python3 <技能目录>/scripts/workflow.py init . --formats docx,pdf,pptx
python3 <技能目录>/scripts/workflow.py show .
python3 <技能目录>/scripts/workflow.py add . source:paper --deps requirements
python3 <技能目录>/scripts/workflow.py set . source:paper done --watch work/paper.txt --artifact work/extracted.json
python3 <技能目录>/scripts/workflow.py set . sources done --watch sources.json
python3 <技能目录>/scripts/workflow.py refresh .
python3 <技能目录>/scripts/workflow.py report .
```

`set` 的状态是 pending/running/done/waiting/failed/skipped/stale。失败、等待和跳过必须有 `--reason`；done 的 watch/artifact 必须存在，artifact 至少一个。路径可相对任务目录；源材料可在目录外，但只读并记录哈希。生成产物必须在任务目录内。

默认图：requirements → sources → research → plan → content；content → docx/pdf/design；design → pptx；选定交付物 → qa → report。DOCX+PDF 同时需要时，PDF 默认依赖 DOCX；后续替代路线不得伪装二者同源。

若要局部重做，在真正展开内容前用 `add section:architecture --deps plan,sources`、`add slide:3 --deps section:architecture,design` 等添加更细节点。用 `link <子节点> --deps <父节点列表>` 增加依赖，不能有环。例如将 content 依赖所有 section，pptx 依赖所有 slide，才能让局部修改可追踪。只有验证过对应输入未变的节点可复用。

`--watch` 跟踪源文件、决策文件、JSON 台账、选用模板及工具版本锁；`--artifact` 跟踪输出。每次完成节点都保存全部应监视路径；重新 set done 会替换该节点的路径清单。改输入前运行 refresh，节点 hash 变化使自身和下游 stale。人为改变 claim/章节映射也必须显式使相应节点 stale，不靠哈希猜语义影响。

受阻节点标 skipped 后，可用 `--allow-partial` 完成下游草稿；不会变成 ready。等待确认的任务标 waiting，禁止用 allow-partial 消耗其未确认结果。report 独立于其他节点始终可生成。

## 质量记录
qa.json 至少如下，各项的 evidence 写真实检查记录或本地路径：

```json
{
  "checks": {
    "requirements": {"status": "passed", "evidence": "work/requirements-review.md"},
    "evidence": {"status": "passed", "evidence": "work/claims-review.md"},
    "consistency": {"status": "passed", "evidence": "work/consistency-review.md"},
    "structure": {"status": "passed", "evidence": "work/file-check.md"},
    "visual": {"status": "passed", "evidence": "work/visual-review.md"}
  }
}
```

qa done 时必须 `--watch qa.json`；证据文件也必须作为 `--artifact` 传入；该记录和所有检查文件会被哈希跟踪。脚本只核验记录存在、状态有效，不证明人工判断正确。visual-review 按交付物枚举所有页/幻灯片、渲染命令和实际图片检查结果；没有完整视觉检查则 status=unverified，并将 qa 标 failed 或 skipped。

## 恢复原则
恢复先 refresh，再看 decisions/issues，沿既有工具路线继续。先前 done 的节点如依赖陈旧即 stale。不要清除失败历史、覆盖用户原件，或把上轮 QA 复制为新文件的 QA。最终报告明确工作目录，便于后续聊天继续；没有读取状态就不声称“已恢复”。
