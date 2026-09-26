# Unified Video Provider Contract — P1

本 Contract 扩展现有 `visual.video_selection → ProductionRoute → productionStage`，没有另建选择器、审批链或剧情状态机。图片继续使用现有 Comfy Cloud MCP。HTTP 与 MCP 的差别止于 Host 执行层。

Seedance 标准版已在本项目原有 Registry（提交 `292d855`）注册为独立键
`seedance-2-standard`，API model 为 `doubao-seedance-2-0-260128`。本次明确其显示名称为
`Seedance 2.0`，与 `Seedance 2.0 Fast` / `Seedance 2.0 Mini` 一同枚举；保留现有三个
独立键、API ID、启用开关和共用 SeedanceProvider，不新建 alias 或猜测新的官方 ID。
这里沿用项目已有接入定义，mock 不证明账号具有该模型权限，也不宣称本轮做过官方在线验证。

## 代码与职责

| 层 | 入口 | 职责 |
|---|---|---|
| 创作 | Director / CinematicShotSpec | 已批准事实、动作、声音、风格；不含厂商请求 |
| 路线 | `visual/video_selection.py` | 硬约束、连续性、质量、成本及既有偏好策略 |
| Contract | `contracts/video.py` | `VideoRequest`、`ContinuityPack`、`ProviderTask` |
| Registry | `providers/video/registry.json` | 官方模型 ID、模式、组合限制、文档、transport |
| HTTP Adapter | `providers/video/adapters.py` | Seedance / MiniMax / Vidu / Wan / Kling |
| MCP Adapter | `providers/video/comfy.py` | 封装既有 MCP 绑定与一次提交；旧调用路径仍保留 |
| Host | `hosts/http_video.py` | bind、submit、poll、下载、导入、读回、账本 |
| 长期存储 | 既有 `complete_retained_media` / MediaProvider | Drama Service import/read/resolve、MinIO、稳定 Media ID |

上层 ExecutionRoute 使用既有大写枚举 `HTTP` / `MCP`；Registry 使用 `http` / `mcp`。其他 Host 可调用 Python Contract 和注入 Provider，不需要 Codex API。

## 请求与结果

Python 属性为 snake_case，JSON 为 camelCase。请求包含 prompt、negativePrompt、inputMode、firstFrame、lastFrame、referenceImages/Videos/Audios、duration、resolution、aspectRatio、nativeAudio、seed、character/scene/styleReferences、providerHints、continuity、switchEvidence。

Reference 是稳定 Media ID、version、contentHash、kind、semantics、reviewRef 以及必要的尺寸/时长。禁止用临时 URL 作为参考身份。身份、服饰、道具、环境、风格、动作、摄影机和连续性语义都能分别标记。Host 读取 Media 校验 Work、hash、类型，执行时才 resolve URL。厂商不支持必需字段/组合时拒绝请求，不静默删除。

统一生命周期：

```python
create_task(request, client_request_id=attempt_id) -> ProviderTask
get_task(task: ProviderTask) -> ProviderTask
cancel_task(task: ProviderTask) -> ProviderTask | None
fetch_result(task: ProviderTask) -> ProviderTask
estimate_cost(request) -> CostEstimate | None
```

使用包含 provider/model/task ID 的 task handle，防止混淆不同厂商的任务。`VideoGenerationResult` 是同一归一化 Contract。字段包括 provider、model、providerTaskId、clientRequestId、requestFingerprint、status、createdAt/startedAt/completedAt、duration/resolution/fps、outputUrl/outputMediaId、usage、estimatedCost/actualCost/currency、errorCode/errorMessage/retryable。厂商未提供的时间、帧率或费用保持 null，不推测。

`ProviderTask.durable()` 排除 outputUrl；正式 Work、receipt journal、CLI 输出均只使用 durable 形式。临时 URL 只存在于内存中的下载步骤。取消为可选能力；P1 对官方接口返回 None，避免把同时可删除已完成结果的 DELETE 误作安全取消。

## Continuity Pack 与切换

唯一权威是 `Work.content.continuityPacks[segmentId]`。Pack 保存源版本/指纹、角色脸部/体型/年龄/发型/服装/甲胄/武器/道具、地点/时段/天气/光线、独立 CG 或写实 RouteStyleContract、色彩/镜头语言、必需参考、上一批准镜头/尾帧、Primary Provider/Model、identityCritical。

Pack 是专业原稿与既有稳定资产的投影，不把 Provider 输出升级为人物定义。绑定和提交前必须与 Work 中的 Pack 完全相等。每个请求引用其中的同一 Reference 对象；不可改变 hash、语义、版本或 reviewRef。参考素材不够时阻断该模型，不压缩必要的一致性要求。

切换须具备 shot boundary 与 capability-gap evidence。官方 Primary 的缺口必须由其 Registry 校验实际重现；旧 Comfy Primary 使用已检查 MCP schema 的外部证据。关键人物段默认锁定，禁止仅因价格切换。切换至少需要视觉锚点；已有上一批准尾帧必须作为首帧或参考传递。首尾帧与参考模式互斥的模型不得假装同时支持；可选完整参考模式，否则淘汰。edit/extend 是显式例外，仍需完整连续性证据。

Prompt Adapter 仅将原 prompt、negative constraints、Canonical Pack 和逐类 reference roles 作确定性结构投影；不调用模型重写剧情，不拥有第二套角色、服装或风格。修改 Pack/请求必须重新规划和封存路线；已付费旧任务仍按原快照恢复，避免创作修改导致任务丢失。

## 准入与选择

模型开关是最前置门禁：`DRAMA_VIDEO_MODEL_<模型键大写、标点改下划线>_ENABLED`。例如 `DRAMA_VIDEO_MODEL_VIDU_Q3_TURBO_ENABLED=false`。实际 env 和完整 example 为所有14个模型键提供中文注释及 `true` 初值；MiniMax H3 的官方与旧 MCP 路线共享同一模型开关。显式值仅 `true`（不区分大小写）启用；false、空值及非法值禁用。旧部署省略变量时兼容默认 true。

Host `video_provider.py models` 返回每个模型的 enabled、配置键和状态。DISABLED 在 AUTO/PREFER/PIN、fallback、路线资格、封存校验与新提交时都不可绕过。已提交任务仍可查询、下载和长期保存。开关不是能力缺口，不能据此绕过 Primary/Continuity 锁模；需要授权调整路线。`enabled=true` 也不代替 API Key、真实能力和预算。

先检查输入模式、连续性、参考数量/时长/组合、输出时长、分辨率/比例、原生音频、seed 与 allowlist hints。再比较适配性、一致性证据、任务范围内质量、相同 Work/镜头类别/风格的 Cost Per Accepted Shot、单次完整成本。

Registry strengths 是待验证路由假设，不是艺术排名。Standard 不自动成为默认；Fast/Mini、Vidu 等参与比较。Kling 为 specialist。未取得受控样本时质量是 UNKNOWN，只能沿既有限次试验规则准入。混合 credits/CNY/USD 不直接排序，必须先提供同一计价单位的有效报价；不内置假汇率。

## Host 使用顺序

1. 将审阅后的 ContinuityPack 写入原 Work，并读回。构造统一 VideoRequest 和既有 Requirements；`inputs` 与实际参考 ID/hash、ReferenceDuty provider slot 一致。
2. 使用 `hosts.http_video.candidate` 建立候选，再经原 `choose` / `qualify_route` 比较。ProductionRoute 的 `requirements.video_requests` 必须为每个 target 保存完整请求。
3. 沿既有 `save_route` / `init-stage` / `seal_decision` / `add-frame` 保存批准路线与预算。HTTP transport sealer 注册在 Host；Core 不导入厂商 Host。
4. `VideoProviderHost.bind` 验证配置、Registry/adapter/schema 指纹和 Canonical Pack。这里 authenticated 表示凭据已配置且绑定了官方 endpoint，不表示已向厂商验证密钥或余额。
5. 经既有 `operate(..., 'reserve', ...)` 持久化带新鲜报价、余额、execution_binding 的一次 attempt。
6. `submit(work_id, attempt_id)` 先记录 UNKNOWN 提交占位，再创建一次。确认 task ID 后立即写不含 URL/密钥的 receipt journal，并写回原 Work。
7. `poll(work_id, attempt_id)` 仅恢复原任务。成功后下载、探测、计算 hash、import、readback、绑定 Media、再次 resolve。内容审核与用户采用仍沿原流程，不自动 PASS。

Host CLI 为 `skills/shot-production/scripts/video_provider.py`，支持 `status / bind / submit / poll / metrics`。除 status 外，提供 `--mcp-config --work-id --cache`；bind 增加 `--decision`，submit/poll 增加 `--attempt-id`。与现有 route preflight 使用同一 cache 和 Work 锁。SDK Host 必须维持同样的单写者边界；服务当前没有跨 Host CAS。

## 异常恢复与存储

GET 网络/502/503/504 与明确 429 最多三次有限重试。创建超时、连接重置、408/5xx 视为不确定，绝不重新 POST。Kling 支持 external ID 查询恢复；其余无已验证查重入口的未知任务保留 UNKNOWN，等待官方控制台确认。已经取得 ID 的任务只 poll 原 ID。Work 写回失败可从本地 receipt 恢复；journal 不是第二个权威状态机。

下载使用独立客户端，不向 CDN 发送 API Authorization。URL 过期时重新读取原 task 获取地址；仍不新建视频。导入沿现有本地文件媒体闭环，不在正式资产保存厂商 URL。技术检查覆盖字节完整性、时长、比例/尺寸、fps、音轨；不合格内容可留作审阅证据，但技术状态 FAIL。

## 费用、配置和验证边界

每个 attempt 保存 provider/model、时长/分辨率、预估/实际金额、单位、attempt ordinal、accepted、rejectedReason。费用估计必须有新鲜、请求绑定的来源；未提供费用 API 时使用原路线报价/预留记录，统一 task 的 estimatedCost 可为 null。actualCost 未返回时保持 null；Vidu credits 留在 usage，不冒充现金。Kling 只有 cash 且单币种账单才归并 actualCost。metrics 按 provider/model/currency 分组；账单缺失不当作免费。

旧字段 `*_credits` 为兼容保留；正式预算、报价、余额均校验 unit，人民币/美元 stage 使用 `budget_unit`。不同币种不允许在同一预算内混用。跨模型比较须由 Host 提供同单位、可追溯报价，不能将旧 Comfy credits 当成 CNY。

五家官方 Provider 各只有 API_KEY + BASE_URL 核心 env。缺钥匙或地址使该 Provider NOT_CONFIGURED，其他 Provider/图片/Plugin 可正常工作。官方 endpoint 白名单拒绝第三方聚合站。READY 只代表本地配置通过；Live 验证独立记录。

能力与 endpoint 以 Registry 中的官方文档为依据；账号权限、地区、实名认证、配额、价格及未执行过的真实请求都不能靠 mock 证明。P1 默认不生成收费测试；有配置且得到任务授权时，每家最多一次最低合理规格 smoke，完整验证 task→poll→download→Drama/MinIO→resolve。
