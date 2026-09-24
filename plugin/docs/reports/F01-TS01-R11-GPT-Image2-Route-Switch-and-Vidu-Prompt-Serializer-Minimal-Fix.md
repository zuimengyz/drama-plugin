# F01-TS01-R11 — GPT Image 2 Route Switch + Vidu Prompt Serializer

## 1. Root Cause

正式帧编译依赖调用者传入旧 Flux template，没有默认 GPT Image 2 选择及防止旧模板继续提交的门禁。视频 IR 则逐字段展开静态外观、摄影和时序事实，K02 输出 3832 字符，超过 Vidu 当前 2000 字符能力上限。

## 2. Image Route Change

当前 Comfy MCP 已核实 `api_openai_gpt_image_2_t2i` 与 `OpenAIGPTImageNodeV2`。后者显示名虽含 2.5，实际 model 枚举仍明确提供 `gpt-image-2`；代码固定选择该值。

`compile_frame(spec)` 现在默认选择 GPT Image 2，并沿用现有 FrameSpec、Template、参考图校验与请求合同。请求明确指定 `Custom` 原尺寸、`high`、`opaque`、`n=1`，只使用生成与保存节点（有参考时附 LoadImage）。S02 保持 1280×720；不借本轮改画幅或预算。尺寸及 API 参数严格校验，无自动 fallback。

正式帧提交门禁同时检查 template model 与实际 API 节点/model；旧 Flux 帧仍可用于历史校验，但不能授权新正式帧提交，返回 `HERO_KEYFRAME_ROUTE_REQUIRES_GPT_IMAGE2`。未引入 Seedream。独立人物/场景资产生成路径未改；现有 FrameSpec 内没有另设 ordinary-support 选路分类，本次默认及门禁作用于正式帧合同。

新图像编译仅在派生 IR 副本中重绑 provider_family，完整创作事实和源 IR 不变。已保存正式 Work/ProductionRoute 未重写；已形成可核验的新请求，不沿用旧 Flux sealed request。节点 schema 标注 seed 后端尚未实现，故不承诺 GPT 的种子可复现性。

## 3. Vidu Serializer Change

仅 VIDEO + Vidu 使用 START STATE / IDENTITY / ACTION / PERFORMANCE / CAMERA / END STATE / AUDIO / SETTING-CONTINUITY 格式。完整时序事实、对白、表演、摄影、端点及必要资产语义原样保留，主体 ID 与角色明确绑定。

有参考图时，不重复展开头发/胡须/体型、静态场景装饰及 secondary 细节；这些保留在完整内部 IR。必要 continuity 与 authority 锚点仍进入文本，完全重复的独立事实只输出一次。纯文生视频不假设存在参考图，保留静态描述。其他视频 Provider 的渲染不变。

沿用现有 source fingerprint、authority、scope、音频能力及 Prompt Budget gate，不修改 IR schema。无硬截断；关键内容仍超限时返回 `PROVIDER_PROMPT_BUDGET_EXCEEDED`。今日 MCP `Vidu3ImageToVideoNode` 确认 prompt 最多 2000 字符，并支持 `model.audio`；只有路线支持且 IR 需要时才输出 AUDIO。

## 4. Files Changed

- `visual/image_route.py`：正式帧默认 GPT Image 2 选择。
- `visual/gpt_image2_template.json`：当前 Comfy 官方模板证据；示例 prompt 不进入派生请求。
- `visual/frame_request.py`：默认选路、GPT 节点及显式尺寸/单张请求校验。
- `visual/vidu_serializer.py`：紧凑 Vidu 任务投影。
- `visual/prompt_ir.py`：接入 Vidu serializer 与正式帧选路门禁。
- `tests/test_hero_vidu_routes.py`、`tests/test_visual_prompt_ir.py`：新增覆盖与更新正式帧测试入口。
- 本报告及 [离线回归证据](/Users/zy/historical-plugin/artifacts/f01-ts01-r11-routes/result.json)。

代码文件均位于 `plugin/src/drama_plugin/` 下。工作区已有的 production.py 变更保留，本轮未修改该文件；既有测试中的 rework 覆盖仅更新其选路入口。

## 5. Tests

覆盖首次生成、FIRST_FRAME、KEY_FRAME、REFERENCE_EDIT 默认 GPT Image 2；旧 Flux 新提交阻断；错误模型/尺寸/多张/额外付费节点拒绝；完整内部 IR 不变；Vidu start/action/performance/camera/end/audio/authority 保留；超限仍阻断；无音频能力拒绝音频要求。

相关测试 **242 passed**，包含 Prompt Budget、Scope、Authority、正式 Provider、ProductionRoute、duration、cost authority 及 failed-no-media recovery 回归；4 个修改/新增 Python 源文件 mypy 通过，git diff --check 通过。非 Vidu VIDEO 四种输入模式的旧完整编译指纹测试继续通过。

## 6. S02 Regression Result

使用保存的真实 S02 r12 首次生成、r13 参考首帧和 K02 video IR，只读回归：

| 检查 | 结果 |
| --- | --- |
| r12 / r13 新正式图像请求 | `gpt-image-2`，scope / authority / replay PASS |
| 原 Video IR 展开 prompt | **3832 characters**（非完整 IR JSON 文件字节数） |
| 新 Vidu prompt | **1771 characters** |
| 真实 hard limit / 来源 | **2000 / runtime_node_schema** |
| 原生对白、时序、端点、摄影、资产锚点 | 保留；现有校验 PASS |
| request formation / sealed contract | PASS |
| 完整 Video IR、输入文件哈希 | 未改变 |
| ProductionRoute / budget / retry 持久化状态 | 未修改 |
| 收费生成 / 预留 / Work 保存 | **0** |

[Vidu prompt](/Users/zy/historical-plugin/artifacts/f01-ts01-r11-routes/vidu-prompt.txt)、[Vidu sealed contract](/Users/zy/historical-plugin/artifacts/f01-ts01-r11-routes/vidu-sealed-contract.json)、[GPT 首次生成请求](/Users/zy/historical-plugin/artifacts/f01-ts01-r11-routes/K02-scoped-compiled-r12.json)、[GPT 参考首帧请求](/Users/zy/historical-plugin/artifacts/f01-ts01-r11-routes/K02-scoped-compiled-r13.json)、[Replay](/Users/zy/historical-plugin/artifacts/f01-ts01-r11-routes/replay.py)。

## 7. Remaining Blocker

两项代码/请求级修复已通过离线回归。尚未生成或采用 GPT Image 2 首帧，故视频回归使用已有参考图证明编译合同，不声称已完成 GPT 首帧→Vidu 的真实媒体链。后续执行须对新 GPT 请求重新报价、按现有预算及审阅合同办理；不得复用 Flux 报价或旧 sealed request。未自动生成图片或视频，至此停止。
