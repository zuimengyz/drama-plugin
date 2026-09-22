# F01-TS01-R — Vidu + Seedance Video Provider Projection Reconciliation

核验日期：2026-09-22。范围：仓库中的正式 Comfy MCP 视频 Projection；不提交收费生成。

## 1. Executive Result

**PARTIAL（运行启用状态）；本轮 Projection 实现和请求形成验收 PASS。**

- Vidu Q3 Pro / Turbo 的文生、单首帧图生共四种组合，已通过真实 MCP 模板/schema 驱动的 inspect → compile → semantic projection → seal → verify_execution。
- Seedance 2.5 文生、首尾帧、单参考图三条既有路线已用当前 MCP 重新确认，并补齐关键 schema 漂移防护。没有将旧 ByteDance 名称作为支持依据。
- **当前外部 `drama-plugin.env` 明确设置 `DRAMA_VIDEO_MODEL_SEEDANCE_2_5_ENABLED=false`。** Flux 3、MiniMax H3 同样禁用；Vidu Pro/Turbo 为 true。未修改这些开关。Seedance 请求链在隔离测试中成立，但不能在当前配置下通过正式生产资格门禁。
- 全量测试 **2497 passed**；本轮专项 **72 passed**；两个修改的 Python 源文件类型检查通过。
- **收费生成调用 0**；没有真实上传、服务写入、预算预约或媒体生成。真实 MCP 调用仅为发现、schema 读取和免费估价。预约测试在离线内存状态中使用明确标识的模拟报价和绑定。

完整证据目录：[video-reconciliation](../../tests/fixtures/video-reconciliation/)。文件 SHA-256 与来源说明：[capture-manifest.json](../../tests/fixtures/video-reconciliation/capture-manifest.json)。

## 2. Root Cause

`hosts.comfy_video.NODES` 原来仅注册 Flux3 I2V、两个 MiniMax H3 节点、三个 ByteDance2 节点。图检查器只允许单个已知生成节点及 LoadImage / SaveVideo / MarkdownNote，故真实 `Vidu3ImageToVideoNode` 在编译前被正确地按“尚未理解的付费节点”拒绝。缺口在节点语义注册，而非 MCP transport。

此外，`cinematic_projection.project` 用“Flux 使用 prompt，否则使用 model.prompt”的二分方式选择字段；音频也用相同推断。只增加白名单会把 Vidu 的 `prompt`、`model.audio` 投影错误。

现有 capability 已绑定 graph/schema hash 和证据时效，但主要按提供的 node schema 验证取值；缺少对已审阅关键结构的独立比对。新增精确结构契约可阻止“把 duration.max 改大后重新计算 capability fingerprint”一类漂移。

## 3. Vidu

事实来源：本次 `search_templates`、`get_template`、`get_template_schema`、`get_node` 返回，原始解析 JSON 均已保存。`search_models(q=vidu)` 返回空，不能据此否定模板和节点目录中的真实存在；此接口的 partner catalog 与完整 node/template catalog 不等价。

| 项目 | Q3 图生 | Q3 文生 |
|---|---|---|
| Template | `api_vidu_q3_image_to_video` | `api_vidu_q3_text_to_video` |
| Node | `Vidu3ImageToVideoNode` | `Vidu3TextToVideoNode` |
| 生成节点 ID | 14 | 9 |
| vendor model | `viduq3-pro` / `viduq3-turbo` | 同左 |
| 独立 plugin model key | `vidu-q3-pro` / `vidu-q3-turbo` | 同左 |
| Prompt | `prompt`，最多 2000 字符 | 同左 |
| Duration | `model.duration`，INT，1–16 | 同左 |
| Resolution | `720p` / `1080p` / `2K` | `720p` / `1080p` |
| Audio | `model.audio`，BOOLEAN，可开关 | 同左 |
| 图片 | `image`，一张必需首帧 | 无图片 |
| reference / last frame | 本节点不支持 | 本节点不支持 |
| Aspect | 无独立字段；本适配要求输入尺寸与意图比例相符 | `model.aspect_ratio`：16:9、9:16、3:4、4:3、1:1 |
| Seed | INT，0–2147483647 | 同左 |

2000 字符限制由当前 node schema 的 tooltip 明确给出，而非机器字段 `max_length`；因此在精确节点语义注册中显式保留。绝不截断 prompt。文生模板的示例 prompt 被 schema 接口标记为 `values_truncated`；完整图已保存，编译时由冻结意图生成完整 prompt 覆盖该示例，不回传截断示例。

`bind_capability(..., variant='viduq3-pro'|'viduq3-turbo')` 必须显式传入型号；生成的 `model_key`、Candidate.model、Candidate.variant、请求 `model` 在编译与封存时保持独立。两个型号的 request fingerprint 不同。

还发现 `Vidu3StartEndToVideoNode`：字段为 `first_frame` + `end_frame`，720p/1080p、1–16 秒、可选声音。**当前 Vidu 模板搜索未返回对应 Q3 首尾帧模板**；只保留其 schema 证据，未制造模板、未注册未验证路线。不能把该节点能力写成 Q3 I2V 节点的能力。

## 4. Seedance

`search_models` 实际返回 `byteplus/seedance-2.0-t2v`，tiers 包括 Seedance 2.0、2.0 Fast、2.0 Mini、2.5。该 catalog slug 不是 plugin identity，不能据 slug 将所有型号合并。模板和 node 的 model 分支才用于验证具体请求。

本次读取的三个 **Seedance 2.5 node schema 与现有 `tests/fixtures/seedance/node-schemas.json` 完全相同**，故保留原有 Projection，仅增加结构校验与当前模板回归。

| Route | Template | 核心 Node | 正式支持范围 |
|---|---|---|---|
| T2V | `api_seedance2_5_t2v` | `ByteDance2TextToVideoNode` | 无图、明确比例、原生声音开关 |
| FLF | `api_seedance2_5_flf2v` | `ByteDance2FirstLastFrameNode` | `first_frame` / `last_frame`；当前模板连接两张图 |
| R2V | `api_seedance2_5_r2v` | `ByteDance2ReferenceNodeV2` | 一张 `model.reference_images.image_1`；固定 `model.task_type=reference` |

共同字段：`model='Seedance 2.5'`；`model.prompt`；`model.duration` INT 4–30；`model.resolution` 为 480p、720p、1080p、4k；`model.generate_audio` BOOLEAN；`model.output_format` 当前 options **仅 mp4**；seed 0–2147483647；watermark BOOLEAN。当前 node schema 没有给出 prompt 数字长度上限，未借用 HTTP Seedance 或 Vidu 的上限。

T2V/R2V 的 `model.ratio` 枚举为 16:9、4:3、1:1、3:4、9:16、21:9、adaptive；正式请求必须与 intent 的明确比例一致。2.5 FLF 无 ratio 字段：同一 node 的 ratio 条件只适用于 2.0 系列，故 2.5 通过首尾帧尺寸验证比例。asset_id 替代输入仍拒绝。

R2V schema 还暴露多图、视频、音频、asset 列表，以及 auto_downscale / auto_upscale；模板描述称 20 图/6 视频/6 音频，而 get_node 的 auto-grow slot 列表为 30/10/10。**这不是单参考图正式适配支持全部多模态的证据。** 当前保持一张图，两个 scaling 布尔参数必须完整冻结；edit / extend / auto 模式继续阻断。

本轮选择 2.5，因为它具备项目已有且经当前 schema 确认的三条正式链。2.0/Fast/Mini、旧 1.0/1.5 的 schema/目录发现不等于正式支持；本轮不按名称扩展，也不把 HTTP `seedance-2-standard` 等模型配置映射为 MCP 2.0 identity。

**运行状态：DISABLED。** 模拟启用下的契约测试不构成修改外部配置或生产授权。专项测试验证 false 开关时连 dry-run seal 也拒绝资格准入。

## 5. Video Provider Support Matrix

盘点边界：完整翻页获得 **105 个 paid API、输出 VIDEO 的 node，21 个 family**；另保存 `tag=Video` 的 135 个模板及 Vidu/Seedance/Flux/MiniMax 专项发现。首次 limit=100 的 node 结果 dropped=47，已用 limit=20、offset=0/20/40/60/80/100 补全。OSS 的大型子图仅作模板发现，不宣称全量 node 核验。

**SUPPORTED 指表内限定路线；PARTIAL 指家族/节点只有部分型号或输入组合；UNSUPPORTED 指没有正式 Comfy 适配；DISABLED 指外部配置明确禁用；NOT_VERIFIED 指该项没有取得完整证据。** HTTP adapter 不计入此矩阵的 Comfy 支持。

| Model / Route | MCP 可发现 | Template 可获得 | Node Schema 可获得 | Plugin Projection | Graph Verification | 当前状态 |
|---|---|---|---|---|---|---|
| Vidu Q3 Pro I2V/T2V | 是（node/template；models 搜索空） | 是，完整 | 是 | SUPPORTED | PASS | SUPPORTED |
| Vidu Q3 Turbo I2V/T2V | 是，model 分支 | 是，完整 | 是 | SUPPORTED | PASS | SUPPORTED |
| Vidu Q3 首尾帧 | 是 | 搜索未发现对应模板 | 是 | UNSUPPORTED | BLOCK | UNSUPPORTED |
| Vidu Q1/Q2、多帧/延长 | 是 | 目录有；未逐一取完整图 | Q1 代表节点已读取，其余 NOT_VERIFIED | UNSUPPORTED | BLOCK | UNSUPPORTED |
| Seedance 2.5 T2V / FLF / 单图 R2V | 是 | 是，完整 | 是 | SUPPORTED（上述范围） | PASS | **DISABLED** |
| Seedance 2.5 多模态 / 编辑 / 延长 | 是 | 目录有 | 是，同一 R2V node | PARTIAL（仅单图 reference） | 扩展组合 BLOCK | DISABLED / PARTIAL |
| Seedance 2.0 / Fast / Mini | 是 | 目录有；2.0 T2V 摘要已取 | 是，同一 ByteDance2 分支 | UNSUPPORTED | variant BLOCK | UNSUPPORTED |
| Seedance 1.0 / 1.5 | 是 | 目录有 | 本轮完整 get_node NOT_VERIFIED | UNSUPPORTED | BLOCK | UNSUPPORTED |
| Flux 3 单首帧 I2V | 是 | 是，完整 | 是 | SUPPORTED（单图） | PASS | DISABLED |
| Flux 3 其余图/时间锚、T2V、延长/编辑/增强 | 是 | 部分目录有 | I2V 是，其余 NOT_VERIFIED | PARTIAL（家族） | 扩展组合 BLOCK | PARTIAL |
| MiniMax H3 首尾帧 / 单参考图 | 是 | 是，完整 | 是 | SUPPORTED（标准 H3） | PASS | DISABLED |
| MiniMax H3 Max / Turbo / T2V / 再生成 | 是 | 部分目录有 | H3 FLF/R2V 分支是 | PARTIAL（家族） | 未适配型号/节点 BLOCK | PARTIAL |
| Grok | 是 | 摘要已取 | `GrokVideoNode` 是，其余 NOT_VERIFIED | UNSUPPORTED | BLOCK | UNSUPPORTED |
| Kling | 是 | v3 摘要已取 | 旧 T2V 代表节点是，其余 NOT_VERIFIED | UNSUPPORTED | BLOCK | UNSUPPORTED |
| Wan / Wan2 / Wan3 / HappyHorse | 是 | Wan2.7 摘要已取 | Wan T2V 代表节点是，其余 NOT_VERIFIED | UNSUPPORTED | BLOCK | UNSUPPORTED |
| Runway | 是 | Gen4 摘要已取 | Gen4 是，其余 NOT_VERIFIED | UNSUPPORTED | BLOCK | UNSUPPORTED |
| PixVerse | 是 | T2V 摘要已取 | T2V 是，其余 NOT_VERIFIED | UNSUPPORTED | BLOCK | UNSUPPORTED |
| Luma | 是 | T2V 摘要已取 | T2V 是，其余 NOT_VERIFIED | UNSUPPORTED | BLOCK | UNSUPPORTED |
| HeyGen | 是 | Avatar 摘要已取 | TalkingPhoto 是，其余 NOT_VERIFIED | UNSUPPORTED | BLOCK | UNSUPPORTED |
| Gemini / LTXV API / Veo / Pruna | 是 | 本轮 NOT_VERIFIED | 每家一个代表节点已取 | UNSUPPORTED | BLOCK | UNSUPPORTED |
| Beeble / Bria / HitPaw / sync.so / Topaz / WaveSpeed | 是，含编辑/增强/口型 | 本轮 NOT_VERIFIED | 每家一个代表节点已取 | UNSUPPORTED | BLOCK | UNSUPPORTED |
| OSS LTX / Wan / Hunyuan Video / SVD / Kandinsky / HuMo 等 | 模板目录是 | 搜索结果已保存；完整图 NOT_VERIFIED | NOT_VERIFIED | UNSUPPORTED | 子图/未适配节点 BLOCK | UNSUPPORTED |

逐节点、逐型号枚举、实际取得的模板名、完整 schema 文件和状态见 [105-node support matrix](../../tests/fixtures/video-reconciliation/video-node-support-matrix.json)。空 template 列表示本轮未验证，不表示不存在。配置证据见 [runtime-model-flags.json](../../tests/fixtures/video-reconciliation/runtime-model-flags.json)，仅记录非敏感 enable 开关。

未来单节点 T2V / 单首帧 / 首尾帧且输出原生 VIDEO 的模型可以沿用现有 NODES 与 schema contract；多模态 reference、视频编辑、增强和 OSS 子图需要各自的 transport/图语义验证，不能用相同白名单直接放行。

## 6. Architecture Changes

1. 沿用 `NODES` 精确注册，仅加入两个 Q3 node；增加可选 variants / audio / aspect / prompt_limit 声明。
2. cinematic projection 从同一注册读取 prompt、duration 和 audio 字段，消除本次 Vidu 所触发的字段二分错误。
3. `comfy_video_contracts.json` 记录本次五个目标节点经审阅的结构投影：类型、必需性、条件分支、枚举、范围、列表 slot、API 身份和输出。bind 和 compile 都比较；漂移需要重新 reconciliation。
4. 条件字段根据实际父 selector 选择；auto-grow 的真实命名 slot 用于验证已连接图片。必需字段缺失、字符串类型错误、用常量替代媒体连线、重复 link ID 均拒绝。
5. 不扩展正式业务 contract，不替换 MCPRegistry，不增加 HTTP 路线，不改变未知节点/额外收费节点拒绝规则。

检查但无需修改：`providers.video.comfy` 仍调用 `invoke_reserved(... verify_request=verify_execution)`；`compile_video.py` 仍调用真实编译/封存器且输出 submissionAllowed=false；`route_preflight.py` 和 `visual_preflight.py` 仍使用同一 verifier。model-selection 的 model key / enable 门禁沿用现有 registry，现有 `vidu-q3-pro` / `vidu-q3-turbo` identity 已足够，无需新增混合配置。

## 7. Files Changed

| 文件（相对 plugin/） | 职责 |
|---|---|
| `src/drama_plugin/hosts/comfy_video.py` | 精确节点、型号、字段、当前 schema 与参数检查 |
| `src/drama_plugin/hosts/comfy_video_contracts.json` | 五个目标节点的审阅结构基线；不是 endpoint/availability 配置 |
| `src/drama_plugin/hosts/cinematic_projection.py` | 使用节点声明的真实字段投影 |
| `tests/test_video_reconciliation.py` | 72 项新专项测试，含现有 provider 实时 schema 回归 |
| `tests/test_expression_routes.py` | 将测试占位 `Seedance2` 改为真实 `ByteDance2TextToVideoNode` |
| `tests/replay_video_reconciliation.py` | 重放七条离线 sealed request；永不连接/预约/生成 |
| `tests/fixtures/video-reconciliation/*.json` | 66 个证据/矩阵文件及独立 capture manifest |
| 本报告 | 结论、能力矩阵、重放方法与运行限制 |

工作区输出：`/Users/zy/historical-plugin/artifacts/f01-ts01-r/offline-replay/`，每条路线包含 request.json 和 sealed-request.json。所有 seal 均为 dry-run，包含模拟素材/上传记录及 OFFLINE 证据，不能用于真实生产。

## 8. Tests

以下从 `/Users/zy/historical-plugin/drama-plugin` 执行：

```sh
../drama-mcp-service/.venv/bin/python -m pytest plugin/tests/test_video_reconciliation.py -q
# 72 passed in 1.35s

../drama-mcp-service/.venv/bin/python -m pytest plugin/tests -q
# 2497 passed in 73.56s

../drama-mcp-service/.venv/bin/python -m mypy plugin/src/drama_plugin/hosts/comfy_video.py plugin/src/drama_plugin/hosts/cinematic_projection.py --follow-imports=silent
# Success: no issues found in 2 source files

git diff --check
# 无错误
```

重放七条请求（隔离 shell，不加载项目生产 enable 策略；绝不修改外部配置）：

```sh
cd /Users/zy/historical-plugin/drama-plugin/plugin
../../drama-mcp-service/.venv/bin/python tests/replay_video_reconciliation.py --output /private/tmp/f01-ts01-r-replay
```

该脚本明确使用测试证据；若 shell 已加载 Seedance=false，则仍会按配置拒绝，不能用它规避生产门禁。

Positive：四种 Vidu 组合、三条 Seedance 2.5 路线、Flux3 单首帧和两个 MiniMax H3 路线的实际模板/schema，通过编译、投影和封存。七条目标路线还调用真实 reservation 实现，使用模拟 MCP binding / quote / balance 验证契约；无真实服务写入。

Negative：未知/额外收费节点、schema class/type/范围漂移、删除音频字段后重算 hash、错误 LAST_FRAME 控制、越界 duration/resolution、错误型号、错误音频策略、超长 prompt、首帧比例不符、文生冒用图生 2K、显式禁用模型、dry-run seal 进入正常执行。原有过期/图篡改/引用漂移/封存变化/预算/绑定门禁由全量回归覆盖。

免费 `estimate_credits(template_name=...)` 确认五个真实模板均可识别一个收费节点：Vidu 两模板默认估值 190 credits，Seedance 三模板默认估值约 352。原文已保存为 `estimate-*.json`。**这些只是模板默认参数估值，不是八秒测试请求、Turbo 分支或其他 overrides 的正式报价。** 工具明确注明 bundled pricing 可能滞后；没有把这些数字当作最终预约报价。正式生产仍要求与最终 request fingerprint 一致的新报价和余额证据。

## 9. Remaining Gaps

- Seedance 2.5 当前被外部配置禁用；不自动启用。适配本身已完成同等级离线验证。
- Q3 首尾帧 node 可发现，但当前搜索无对应模板，因此该路线未接入。Q3 已返回的 I2V/T2V 模板均已接入。
- Seedance 2.0/Fast/Mini、旧 1.x、多模态引用和编辑/延长不在本轮正式支持范围。2.5 single-reference 不能被描述为完整 R2V 能力覆盖。
- Seedance template 描述与 node 的列表槽位数量不一致；本轮不利用这些未核实上限。通用 capability 文案也存在 up-to-1080p 与 node 4k 枚举差异，本报告采用当前 node schema，并保留原始证据。
- Vidu 编译后的完整 prompt 超过 2000 字符、时长超过 16 秒时仍硬阻断。没有修改 S02/S05、缩短剧情或增加 clip 拆分；本轮测试使用独立八秒测试意图，不构成原片段已可提交的证据。
- 未做真实视频、画质/表演/音画艺术验收、真实 billing/Receipt/Stable Media 验证；它们超出本轮且需要另行授权的收费执行。
- 本轮修改位于源码仓库；未重装 Codex 缓存中的插件。已有冻结候选应重新发现并封存，因为 adapter 源码 fingerprint 已变化；不能沿用旧 request seal。

## 10. Production Readiness

**Can Vidu enter formal production chain? YES，限已验证的 Q3 Pro/Turbo T2V 与单首帧 I2V。** 当前 enable=true；源码链已证明 validated provider projection + verified graph + sealed request。真实项目仍须提供合格冻结意图、真实素材和上传凭据、当前 schema/graph、准确报价、可用 MCP binding 与预算；本报告不是收费授权。

**Can Seedance enter formal production chain? Projection contract YES；当前外部运行配置 NO（DISABLED）。** 2.5 三条范围内路线已完成同级契约验证；加载真实配置后，model-selection/seal 正确拒绝。需由配置所有者明确启用才能用于后续真实生产；本轮未改变该事实。

| Acceptance | 结果与依据 |
|---|---|
| AC-01 | PASS：真实 Q3 I2V node 通过 inspect，四种 Q3 组合编译/封存成功 |
| AC-02 | PASS：实时 schema 两个 model 值、独立 model key / request fingerprint |
| AC-03 | 适配 PASS；当前运行 DISABLED：Seedance 2.5 三路线离线全链通过 |
| AC-04 | PASS：当前 template/schema/node 证据，不从 ByteDance 名称推断 |
| AC-05 | PASS：未知、额外收费节点仍默认拒绝 |
| AC-06 | PASS：2497 全量回归，含实时 Flux/MiniMax 模板 |
| AC-07 | PASS：七条 dry-run sealed request；真实生成零调用 |
| AC-08 | PASS：21 家族汇总及 105-node 可重放矩阵 |
| AC-09 | PASS：支持子集、未支持、未核验和禁用分别标注 |
| AC-10 | PASS：MCP JSON、SHA-256 manifest、源码、自动化测试、离线重放产物 |
