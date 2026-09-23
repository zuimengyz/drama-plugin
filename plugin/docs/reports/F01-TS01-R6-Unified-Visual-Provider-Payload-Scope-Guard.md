# F01-TS01-R6 — Unified Visual Provider Payload Scope Guard

## 1. Root Cause

首帧 `environment` 拼入完整资产 compilation，人物 identity/costume 也拼接所有 decisions，导致 Director constraints、未来连续性与当前可见事实混合。视频编译按整个结构输出，部分 provenance、表演解释及声音策略也随之进入 prompt。旧图像 authority 消费判断又要求完整 receipt prompt，强化了这种耦合。

## 2. Covered Task Types

统一 task 合同覆盖 `IMAGE`、`FIRST_FRAME`、`KEY_FRAME`、`VIDEO`。已接入资产角色/服装/场景图像 projection、正式首帧及参考图编辑编译、MCP 视频编译、HTTP 视频 prompt 编译和正式 authority/submission 校验。视频既有文生、单图、首尾帧及参考路线继续使用原 adapter。

## 3. Old Flow

完整上游结构/资产全文 → 字符串拼接 → Provider；缺少任务范围与执行字段的独立检查。即使某段只用于 authority，也可能因全文消费要求进入模型。

## 4. New Flow

完整内部 context/原始 receipt → task-specific 字段选择与 source path → 当前任务可执行块 → 去重 → `VISUAL_PROVIDER_SCOPE_REVIEW` → 原 Prompt Budget / Provider request formation → 原封存与提交门禁。

`scope_context` 保存原始材料，`execution[task]` 明确选择可执行字段及原文来源。编译产生 source hash/map、context fingerprint 和 prompt fingerprint；不会把 context 序列化到 Provider prompt。相同表达只输出一次，人物 subject 绑定保留。现有 typed compiler 复用同一最终文本检查。

完整资产 receipt 仍按原权威 store 重放。图像消费改为验证派生的当前视觉内容，旧全文 payload 明确拒绝。视频资产提示改用稳定脸部、当前衣物结构、建筑等字段；原 continuity 全文留在内部，当前 clip 的连续性由 frozen intent 提供。

## 5. Scope Rules by Task Type

| Task | 执行内容 | 内部保留/拒绝 |
| --- | --- | --- |
| IMAGE | identity、服装道具、当前环境/姿态、构图、光材质媒介、视觉连续性、必要参考/可见文字 | 声音、剧情目的、观众解释、未来事件、审批/预算/权威全文 |
| FIRST_FRAME / KEY_FRAME | 单一瞬间可画出的同类视觉字段 | action chain、beats、ending state、声音与后续场景 |
| VIDEO | 当前 clip 动作、表演、镜头运动、起止状态、节奏与连续性；启用原生音频时的对白/声音 | 全场文学说明、内部解释、future scene、音乐规划、来源/审批数据 |

视频中的 native audio policy 仍决定参数，不当作 prompt 文本。静音路线不输出 source sound 内容。原 source map 的内部字段改标为 `UPSTREAM_LOCK`，未覆盖上游原文。

错误包括 `VISUAL_PROVIDER_PAYLOAD_SCOPE_VIOLATION`、`VISUAL_PROVIDER_PAYLOAD_DUPLICATED_BLOCK`、`VISUAL_PROVIDER_PAYLOAD_CONTAINS_AUTHORITY_CONTEXT`。规则检查任务字段、来源路径、控制面标签、未来场景标记和重复块；没有暴力/伤害等敏感词删除或替换逻辑。

## 6. Files Changed

- 新增 `src/drama_plugin/visual/payload_scope.py`：统一编译与 review。
- `visual/frame_request.py`、`visual/video_prompt.py`：任务 context、首帧和 HTTP 边界。
- `hosts/cinematic_projection.py`、`hosts/comfy_video.py`：视频字段收窄、预算前 review。
- `specialized_asset.py`、`hosts/specialized_asset.py`、`hosts/route_production.py`：资产派生、完整权威验证和正式提交连接。
- 新增 `tests/test_payload_scope.py`；更新两处原先要求全文/固定旧长度的 authority 测试。
- workspace `artifacts/f01-ts01-r6/`：只读复现脚本、内部 compiled frame、Provider prompt、视频诊断及结果。

## 7. Tests

**304 passed**：scope、prompt budget、authority、资产、Vidu/Seedance reconciliation、HTTP provider、首帧、参考图、cinematic、route duration、cost 等相关回归。最终将缺失参考诊断移出 prompt 后，针对性复核 **89 passed**。新增 scope 测试 **10 passed**；8 个修改源文件 mypy 通过，`git diff --check` 通过。

覆盖图像只保留视觉字段、首帧拒绝未来动作、视频保留当前动作/音频能力约束、authority 隔离、来源不能改标签绕过、重复表达去重、预算仍可阻断。测试明确保留必要“伤口”视觉描述，证明不是敏感词清洗。旧“整个 receipt 必须等于 Provider prompt”的测试改为内部 receipt 完整、外部派生内容合法。

## 8. Real Regressions

使用保存的真实 S02 数据，仅 request formation / validation：

- **Flux S02-K02 首帧**：原污染 spec 被 scope gate 阻断。使用同一原始 spec、资产、光线原文的当前视觉字段重新编译，**request formation PASS、authority PASS**；最终 **1064 字符**，模型仍为 **Flux.2 [pro]**。人物身份/衣物/空间与 subject 对应保留；不包含 Director constraints、sound、future S05 或资产全文。
- **Vidu S02-K02**：scope **PASS**、authority **PASS**、budget **PASS**；最终 **1591 / 2000 字符**。保留当前抓肘、转身、请求对白及当前 clip 连续性；完整冻结意图没有改写。缺失参考的诊断仅保留在内部 manifest/错误中。
- 原始 compiled frame、资产、frozen intent、正式 Work 的 SHA-256 前后一致；无模型切换、自动重试或新增收费任务。

复现命令（workspace 根目录）：

```sh
drama-mcp-service/.venv/bin/python artifacts/f01-ts01-r6/replay-scope.py
```

## 9. Remaining Blocker

保存的视频样本仍缺必需参考素材绑定，继续 `REQUIRED_REFERENCE_UNFULFILLED`；本轮未刷新成本或授予提交资格。首帧通过的是本地请求形成与验证，不代表 Provider moderation 或图像质量已经通过。

这是结构化任务边界与最小规则检查，不是自然语言 AI 审稿器。含混的旧混合字段需要从原始任务字段重新编译，不能把整个文档重新标成 visual 来代替 source selection。未改 Director、剧本、人物设计、模型预算/时长/成本合同。修复与回归后停止。
