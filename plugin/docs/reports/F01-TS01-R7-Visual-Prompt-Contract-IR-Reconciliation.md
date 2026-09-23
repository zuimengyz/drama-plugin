# F01-TS01-R7 — Visual Prompt Contract / Prompt IR Reconciliation

## 1. Root Cause

Scope Guard 只判断可投影范围；旧编译没有定义完整性、优先级和任务语义。年龄、时代、动作状态与磨损细节平铺。编辑指令可能被 scope context 的投影替代，正向描述也无法清楚表达源图中必须纠正的错误。

## 2. Prompt Contract Design

新增 `VisualPromptIR → compile_ir → executable prompt + compilation receipt`。IR 缺少必填信息、优先级过低、任务/输入不匹配或音频不受支持时，明确报错。编译记录包含 IR、来源指纹、保留/省略字段、最终 prompt 指纹与现有预算校验结果。

FrameSpec、VideoRequest、正式 cinematic projection 接入 `prompt_ir`。`begin_submission` 必须验证 IR 编译记录与实际 payload 一致；HTTP create_task 在解析媒体地址、调用 Provider 前再次要求 IR。未迁移请求返回 `VISUAL_PROMPT_IR_REQUIRED_BEFORE_SUBMISSION`。

旧编译路径保留历史重放/诊断用途，不能凭旧文本进入新收费提交。未启用 IR 时不新增 VideoRequest 序列化字段，避免无意改变历史请求指纹。现有预算、路线与 Asset Authority 校验继续执行。

## 3. Prompt IR Schema

正式 schema 位于 `contracts/visual_prompt.py`，Pydantic 拒绝未知字段。

- `task`：类型、Provider family、medium、主体类别、输入模式、clip ID。
- `world`：era、location、historical_context、environment_rules，全部必填。
- `subjects`：id、role、apparent_age、face、hair、可选 beard、body_proportions、costume、visible_condition。
- `blocking` / `action`：位置、朝向、接触、当前关系、动作、表情；有角色时必填。
- `environment` / `camera` / `lighting`：建筑、拓扑、时期物件；构图、景别、可读信息、透视；时段、光源、反差、质感。
- `continuity` / `preserve`：当前任务必须维持的信息。
- `edit_delta`：区域、source_issue、operation、target_correction。
- `video_temporal`：start、progression、performance、camera motion、end、可选 audio。
- `negative_constraints`：原约束和显式等价 positive_target。
- `secondary_details`：明确可省略的次级细节。

描述字段使用 `Fact(text, priority, scope, source)`；原文、未来能力与依据留在内部 IR。source 只用于审计，不发送给 Provider。来源指纹绑定原输入；不通过默认值猜测缺失的年龄、时代或动作。

## 4. Rules by Task Type

| 任务 | 必须具备的区别 |
| --- | --- |
| Text-to-image | 无源图；角色图必须包含主体和当前状态；纯场景图可不含角色 |
| Image/reference edit | 明确源图/参考输入，必须有 edit delta 和 preserve |
| First/key frame | 仅当前可见状态；non_current 能力/未来信息留在内部 |
| Video | 必须绑定 clip ID 和 temporal 字段；支持 text、single_image、first_last、reference；blocking/action 明确标记为 clip start 状态，避免锁死后续动作 |

音频只有 Provider 路线启用时才允许投影，必需音频不支持时阻断。现有 cinematic 对接还核对来源、首尾状态、canonical actions、原文对白和资产执行语义。

## 5. Priority Rules

CRITICAL：时代/地域、视觉年龄、核心身份、站位/接触、当前动作、edit delta、preserve、必要连续性及 clip 时序。

IMPORTANT：服装、可见状况、环境、摄影与光线；这些必填内容同样不能通过预算压缩删除。

SECONDARY：仅明确可选的细节可在超预算时逐项省略，记录字段路径和原因。完整描述保留在 IR；不截字符串、不删除硬约束。仍超限时沿用 `PROVIDER_PROMPT_BUDGET_EXCEEDED`。Comfy 使用原 capability limit；HTTP 使用现有 adapter capability。

## 6. Image Edit Delta Rules

编辑输出以 `SOURCE DELTA + PRESERVE + TARGET` 组织，保留 `CORRECT / REPLACE / REMOVE`。来源错误不经过笼统正向化。可正向表达的普通 negative constraint 使用显式 positive_target，且不能降低原优先级。

IR 路径禁止叠加旧 `prompt_normalization`，避免最终字符串替换弱化纠错指令或使编译证据失效。不存在敏感词过滤器。

## 7. Files Changed

- 新增 `contracts/visual_prompt.py`、`visual/prompt_ir.py`。
- 接入 `visual/frame_request.py`、`visual/video_prompt.py`、`hosts/cinematic_projection.py`。
- 增加 IR 输入字段：`contracts/video.py`、`visual/video_selection.py`。
- 提交前门禁：`visual/production.py`、`providers/video/base.py`。
- 新增 `tests/test_visual_prompt_ir.py`；迁移 `test_official_video_providers.py`、`test_mcp_execution.py`、`test_authority_provider_separation.py` 中实际测试新提交的夹具。

没有修改 Director、剧本、S02 原始意图、Provider adapters、预算/路线/authority 合同或 retry 策略。

## 8. Tests

相关回归 267 passed；覆盖 IR、正向表达、scope、图像请求、视频投影、五类 HTTP adapter、正式 route/MCP、authority separation 和 prompt budget。随后对 HTTP capability budget 接入和 clip-start 标记补充定向验证：106 passed。八个相关源文件 mypy 通过，git diff --check 通过。

新增 IR 测试覆盖 A–F：文生图/角色图/场景图、edit delta、首帧 future capability 隔离、四种视频输入模式、优先级保留、negative 正向目标与 edit 操作并存。还覆盖缺字段、Provider 不匹配、源指纹变化、控制面回流、旧请求提交前阻断、无网络副作用及编译结果篡改。

## 9. Real Regressions

当前 S02-K02 r9 图像，Media `media_85aca252613b4cbc900dce72c38743e8`，实际 PNG hash 与 retention/review 一致。人工查看保存图像并使用现有 review：男人偏老、右侧蓝色 P 标志仍存在。

- `CRITICAL subject.C_MAN.apparent_age` 明确为 **38–42岁（约四十岁）**。
- source delta 明确 `CORRECT` 男人年龄呈现与原有深棕短发/短胡茬；`REPLACE` 右侧现代停车牌为相邻历史街屋立面。
- preserve 双人构图、站位、女孩接近动作、尚未接触状态、湿石路及原有角色设计。
- 新 prompt 2922 characters；文字增长来自显式字段与优先级，不以长度增长作为效果证明。
- scope、asset authority、编译重放均 PASS。七个真实来源文件前后 SHA-256 一致，内部原文保留。

证据：`/Users/zy/historical-plugin/artifacts/f01-ts01-r7-prompt-ir/` 中的 `prompt-ir.json`、`compiled.json`、`provider-prompt.txt`、`provider-payload-preview.json`、`result.json`、`source-context.json` 和 `replay.py`。

输出绑定当前 r9 已保留 Media，而不是旧 r8 编辑输入。仅完成 payload preview；没有伪造当前 r9 的 Provider upload receipt，没有新上传、预留、收费任务或正式媒体生成。现有视频投影和结构化视频提交由离线回归验证；本轮没有新增真实 clip 生成。

## 10. Remaining Gaps

IR 是明确的 authoring contract，不是自动理解任意文学原文的提取器，也不能自动证明所有正向改写的语义等价。旧任务需要从完整来源补齐 IR 才能新提交；缺少信息时阻断，不猜测。

当前 r9 payload preview 尚未做新的 Provider 源图上传与正式请求封存，这属于未来明确授权的执行阶段。未测试真实生成质量或 moderation，不声称已解决模型年龄偏差或所有现代元素残留。若后续干净请求仍被 moderated，按既定 `PROVIDER_MODERATION_INCOMPATIBILITY` 交给 Model Selection / Provider Route，停止改词试探。
