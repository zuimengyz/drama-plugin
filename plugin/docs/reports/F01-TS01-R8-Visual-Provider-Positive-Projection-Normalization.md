# F01-TS01-R8 — Visual Provider Positive Projection Normalization

## Root Cause

Scope Guard 已排除控制面内容，但允许的 asset 字段仍包含负向表面约束与首帧不可见的动作能力。字段范围正确不等于最终视觉表达已完成正向化。

## Files Changed

- `visual/positive_projection.py`：小型、确定性的最终文本转换与审计记录。
- `visual/frame_request.py`：图像请求形成前应用转换，保持原始 scope context，更新最终文本指纹。
- `contracts/video.py`、`visual/video_selection.py`：可选内部 `prompt_normalization` 计划。
- `visual/video_prompt.py`、`hosts/cinematic_projection.py`：视频最终投影接入；正向表达增长时重新使用现有长度门禁。
- `tests/test_positive_projection.py`：11 项必要测试。

未改 Scope Guard、Provider adapters、retry、预算、创作资产或剧本。

## Normalization Contract

采用逐条语义核对的完整描述映射，绑定原始最终 prompt 指纹，记录 before / after / kind / reason / basis。没有计划时原样返回；不推断任意中文句子的等价性，不按词过滤，不做全局删除。输入变化必须重新核对计划，旧计划明确报错。

`POSITIVE_EQUIVALENT` 表达当前正向视觉目标；`CURRENT_VISIBLE_ONLY` 只允许静态图像用途，禁止用于删除视频中的跨帧动作。转换前后均运行现有 scope validation。转换计划与原文留在内部审计中，不注入 Provider executable prompt。

## Tests

相关 suite：274 passed。随后新增完整内部 asset / continuity 保留测试，最终 normalization 文件单独验证为 11 passed。覆盖正向描述、静态未来能力排除、内部原文保留、禁止控制面回流、保留未映射描述及实际伤口、旧指纹拒绝、视频动作保护与最终长度门禁。六个改动源文件 mypy 通过，git diff --check 通过。

## S02 First-Frame Regression

使用保存的 `K02-scoped-compiled-r6.json` 与第二次提交的 `K02-submitted-prompt-r7.txt`，先验证二者 prompt 完全一致，再离线重新编译。

六处完整描述转换：男主皮肤、女孩身量中的握持能力、女孩皮肤表面状态、湿鞋裂口的跨帧开合描述及附带皮肤约束、湿地反光、时期相符街道陈设。女孩克制神情采用本任务明确给出的正向表达。必要的“尚未抓住”当前动作约束原样保留。

原文 1064 characters，结果 1065 characters；不是压缩任务。人物身份、年龄、骨相、服装、构图、当前姿态、建筑及必要连续性保留。其余 30 行原样保留；除 prompt 外 Provider request 字段完全一致。内部 scope context 全量一致，五个来源文件 SHA-256 前后相同。

请求形成、asset authority、visual scope、compiled request 重放校验均 PASS。没有执行预留、模型切换或收费生成。

证据目录：`/Users/zy/historical-plugin/artifacts/f01-ts01-r8/`

- `before-prompt.txt` / `after-prompt.txt` / `prompt.diff`
- `normalization-plan.json` / `normalized-compiled.json`
- `result.json` / `replay-normalization.py`

重放：在 `/Users/zy/historical-plugin` 执行 `drama-mcp-service/.venv/bin/python artifacts/f01-ts01-r8/replay-normalization.py`。只生成离线证据，不提交任务。

## Stop Condition

本轮 normalization 完成并停止。Provider moderation outcome 为 `NOT_TESTED`，不声明审核通过。如果后续使用该 prompt 的真实提交仍被 moderated，记录 `PROVIDER_MODERATION_INCOMPATIBILITY`，交由后续 Model Selection / Provider Route 决策；不继续改词或反复试探。该处记录停止策略，不改变现有 retry 系统。
