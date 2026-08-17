# Batch 5.6：真实视频生成验证执行报告

执行日期：2026-08-17  
执行范围：Scene `5-2 一桌家书`；Shot `5-2-04`、`5-2-05`  
最终结论：`BATCH_5_6 = FAIL`

## 1. Executive Summary

本批由正式 `shot-production` Skill 驱动，完成了视频工作流发现、两条 Shot 的源 Media 解析、运动语义编译、视频输入契约收口以及 Shot `5-2-04` 的一次真实 Seedance 生成。用户已明确授权上传两张正式 Shot 图片，并授权两个 4 秒、720p、无音频视频合计约 182 Comfy Cloud credits。

实际执行中，Shot `5-2-04` 的正式云端 job 已成功完成，且生成只提交一次；后续状态轮询和输出获取始终复用同一 job，没有因超时重新生成。当前 Windows Host 随后无法与 Provider 输出所在对象存储完成 TLS 下载：刷新同一 completed job 的输出地址后，PowerShell、Python TLS 客户端和应用内浏览器均得到连接关闭/意外 EOF。有限重试耗尽后，未获得本地 MP4 字节，因此不能真实打开视频进行动态内容 Review，也不能进入 Media Import。

鉴于 Review PASS 是视频持久化的硬门禁，Shot `5-2-04` 未持久化；Shot `5-2-05` 在确认同一下载链路不可用后 fail-closed，未执行第二次付费 submit。预计实际消耗约 91 credits，而不是已授权上限约 182 credits。

本批不把 `job completed` 冒充动态内容 Review PASS，不把网络下载失败记为视觉质量失败，也不为获得两个结果而重复收费提交。因此本批诚实判定为 FAIL，且不进入音频、视频编辑或其他 Scene。

## 2. Skill Activation 与执行边界

实际使用：

- `shot-production`：读取 Shot/Scene/既有 Media，选择视频输入模式，编译运动语义、相机意图、Review 门禁、重试与持久化顺序。
- `skill-creator`：对既有 Skill Core 的视频输入与动态 Review 规则做最小、单一位置的补充和验证。
- `plugin-creator`：校验并重新安装本地插件，使当前 Host 实际加载本批更新后的 Skill，而非仅修改源码副本。
- `browser:control-in-app-browser`：仅在常规下载客户端均失败后，对同一 completed job 的输出地址执行最后一次受控下载验证；没有触发新 generation。

没有使用图像生成 Skill；没有重新生成 5.5 图片；没有生成音频；没有启动视频编辑；没有新建视频引擎或长期下载框架。

## 3. Existing Media Reuse

### Shot 5-2-04

- Shot ID：`shot_a9dc0ba7dfdc4e7ea2d1d479403c6274`
- Source Media ID：`media_bd382552bfc94719b6e2b2dffa00583c`
- 当前 Host `media.get_media`：PASS
- 当前 Host `media.resolve_media`：PASS
- SHA-256：`e63bf11cfcb83322629783c00cb55f90e4cb39a7bee677088a071d327a711061`
- 字节数：1,539,172
- 用途：Single Image → Video 的唯一输入图片

### Shot 5-2-05

- Shot ID：`shot_5559407312e04d9988591a11d3bcbf7f`
- Source Media ID：`media_1dc175f213cc474598efbed9bc909f30`
- 当前 Host `media.get_media`：PASS
- 当前 Host `media.resolve_media`：PASS
- SHA-256：`55ca23e337564712a9bb0e52f433a3dc4c7e3587854690eff1e961db9a4a219b`
- 字节数：1,578,715
- 用途：计划作为 Single Image → Video 的唯一输入图片；已上传，但因 fail-closed 未 submit generation

两张图片均直接复用 Batch 5.5 的 Review PASS 正式 Media。未修改图片、未重新抽图、未跨 Shot 拼接首尾帧。

## 4. Video Workflow Discovery

通过 Comfy Cloud 正式模板发现与 schema 读取，确认以下能力：

- Reference/Image → Video 模板：支持单图输入。
- First/Last Frame → Video 模板：支持同一 Shot 的首帧与尾帧输入。
- 本批实际选择：官方 Reference/Image → Video 模板。
- 模型：Seedance 2.0 Mini。
- 分辨率：720p。
- 时长：4 秒。
- 音频：关闭。
- 画幅：自适应源图。

模板 schema 发现期间出现一次瞬时 HTTP 传输失败；按 Visual Provider Retry Policy 对同一只读操作重试一次后 PASS，未增加 generation count。

## 5. Video Input Contract

### Single Image 模式

正式契约冻结为：

- 必须且只能提供 1 个 `reference_media_id`。
- 不得同时提供 `start_media_id` / `end_media_id`。
- 0 张、2 张及以上、混合输入均在 Provider submit 前拒绝。
- 输入 Media 必须属于当前 Shot 已选定的正式源 Media。

本批 Shot `5-2-04` 与 `5-2-05` 均满足该契约。

### Start-End Frame 模式

正式契约冻结为：

- 必须同时且各自仅有一个 start/end Media。
- 不得混入 arbitrary reference list。
- 只允许同一 Shot 的合法帧对；禁止拿两个不同 Shot 的成片图片伪造首尾帧。

数据库与 Media 目的审计未发现这两个 Shot 已存在合格的同 Shot `START_FRAME` + `END_FRAME` 对。因此本批不为覆盖率造假，真实 Start-End E2E 记为 `NOT_RUN_NO_EXISTING_FRAME_PAIR`。

## 6. Motion Planning

### Shot 5-2-04

Skill 从既有 Shot 语义编译出紧凑运动约束：

- 苏武双手轻微收紧、只借碗暖手。
- 碗保持明显低于嘴部，不碰唇、不饮用。
- 表演仅包含克制目光、自然呼吸和轻微衣料运动。
- 李陵前景肩背仅有微弱呼吸。
- 火盆火焰轻微闪动；穹庐结构稳定。
- 相机保持静止，仅允许难以察觉的电影感漂移。
- 禁止走动、大幅手势、身份/服装变化、道具变化、场景形变及文字畸变。

该 prompt 在 Provider 长度限制内，保持 Static Camera Intent、角色稳定事实和 `只暖手不饮` 的 Required/Forbidden 语义。

### Shot 5-2-05

Skill 计划保持扶节与双人关系的微运动：

- 汉节位置与人物关系保持稳定。
- 碗已处于上一 Shot 之后的落桌/非饮用状态，不回跳至嘴边。
- 仅允许呼吸、目光、衣料和环境火光的细微运动。
- 相机与构图保持克制，不引入身份、服装、道具或场景变形。

由于 Shot `5-2-04` 输出下载链路已耗尽重试，Shot `5-2-05` prompt 未提交到付费 generation。

## 7. Shot 5-2-04 Real Generation

- Provider：Comfy Cloud
- Workflow：官方 Reference/Image → Video
- Model：Seedance 2.0 Mini
- 输入：1 张当前 Shot 正式图片
- 参数：4 秒、720p、无音频
- Provider Job ID：`fb42f0e2-7b38-4adb-a474-86315efb68e8`
- Generation submit：1 次
- Generation count：1
- Targeted revise：0

执行时序：

1. 用户确认约 91 credits 的单条消费门禁。
2. 同一输入与 prompt 执行一次正式 submit，取得 job ID。
3. `wait_for_job` 多次返回仍在运行/轮询超时，继续查询同一 job ID。
4. 同一 job 最终状态为 completed。
5. `get_output` 从同一 completed job 取得 MP4 输出信息。
6. 下载阶段因当前 Host TLS 连接被关闭而失败。
7. 对同一 completed job 再次 `get_output`，刷新输出地址；没有重新 submit。
8. 在受控的初始 + 2 次技术重试后仍为连接关闭/SSL unexpected EOF，判定输出下载不可用。

补充偏差：Provider 首次返回的下载命令自身包含 `--retry 3`，实际执行造成一次初始尝试加三次内部重试，超过项目对单一 operation 的正式 `MAX_TECHNICAL_RETRIES = 2`。识别后没有再次使用该命令；刷新地址后的独立下载操作严格采用初始 + 2 次 retry。该偏差如实计入本批 actual retry validation FAIL，但没有造成重复 generation 或额外 credits。

### Dynamic Content Review

结果：`NOT_RUN_OUTPUT_UNAVAILABLE`

虽然 Provider job completed，但本机没有取得可打开的 MP4 字节，因此无法检查：

- 人物身份与服装是否稳定；
- 碗是否始终不碰嘴、不发生饮用；
- 人体、手、面部、道具与穹庐是否结构稳定；
- 运动是否自然、相机是否保持静止；
- 是否存在闪变、漂移、场景 morphing 或其他动态伪影。

按 Skill 门禁，`job completed` 不能代替 Visual Content Review PASS。因此未执行 targeted revise，也未进入 Media Import。

## 8. Shot 5-2-05 Execution

- Source resolution：PASS
- Provider input upload：PASS
- Motion planning：PASS
- Generation submit：NOT_RUN
- Generation count：0
- Technical retry count：0
- Targeted revise：0
- 预计 credits 消耗：0

停止理由：Shot `5-2-04` 已证明当前 Host 不能取得 completed job 的视频字节。继续提交 Shot `5-2-05` 会再消耗约 91 credits，但仍无法执行真实 Review 与 Media Persistence，不满足本批端到端目标。Skill 因此 fail-closed；这不是 Shot B 的视觉质量 FAIL，也不是 Provider generation FAIL。

## 9. Technical Retry 与 Idempotency

本批遵循以下边界：

- 模板/schema 只读发现瞬时失败：重试同一 operation。
- 已有 job ID 后，状态轮询始终查询同一 job。
- completed job 的 output fetch/download 失败：刷新并下载同一 job 的同一生成结果。
- 不因 polling timeout、get_output 或 download failure 重新 submit generation。
- Technical retry 不增加 generation count。
- Visual Review FAIL 才可能触发 targeted revise；本批未取得输出字节，不能伪造 Review FAIL，也不能触发 revise。

实际证据：Shot `5-2-04` 的 job ID 全程不变，generation count 始终为 1。

## 10. Cross-Shot Dynamic Review

结果：`NOT_RUN`

前置条件要求两个 Shot 均完成 Per-Shot Dynamic Content Review PASS。本批没有任何一条视频能从 Provider 输出存储下载到当前 Host，因此不满足 Cross-Shot Review 门禁。没有以两张静态源图替代视频动态一致性审查。

## 11. Media Persistence

### Shot 5-2-04

- `media.import_media`：NOT_RUN
- `media.get_media`：NOT_RUN（无新 Video Media ID）
- `media.resolve_media`：NOT_RUN
- SHA-256 equality：NOT_RUN

### Shot 5-2-05

- `media.import_media`：NOT_RUN
- `media.get_media`：NOT_RUN
- `media.resolve_media`：NOT_RUN
- SHA-256 equality：NOT_RUN

原因不是当前 Local MinIO 不可写，而是 Provider 输出 MP4 未能下载，且 Visual Content Review 未 PASS。按冻结顺序 `Provider Output → Dynamic Review PASS → Media Import`，没有创建未经审查的视频 Media 元数据或对象。

## 12. Minimal Source Changes

为防止 Host 错传视频输入并把动态 Review 降级为 job-status 检查，本批只做最小 Skill/Tool Contract 收口：

- `plugin/src/drama_plugin/tools/catalog.py`
  - `visual.video.generate` 在 Provider 调用前验证 Single Image 与 Start-End 两种互斥输入形态。
  - 拒绝空输入、双 reference、首尾不完整及混合输入。
  - 约束 compact prompt 上限。
- `plugin/skills/shot-production/references/visual-provider.md`
  - 增加视频输入、同 Shot 首尾帧、动态 Review、生成/revise/retry 分离规则。
- `plugin/tests/test_tools.py`
  - 覆盖合法单图、合法首尾帧、空/双图/不完整/混合输入及过长 prompt。
- `plugin/tests/test_skills.py`
  - 校验 Skill Core 视频契约存在。
- `plugin/.codex-plugin/plugin.json`
  - 仅更新开发 cachebuster，并完成插件 validate/install，使运行 Host 加载本次修改。

离线测试：`48 passed`。Plugin validate：PASS。Skill quick validate：PASS。

未修改 Java、Drama MCP、数据库结构或业务数据契约；未新增运行时服务、视频引擎、重试框架、下载代理、MinIO 同步或 replica 系统。

## 13. Scope Control

- Image regeneration：NOT RUN
- Audio generation：NOT RUN
- Video editing：NOT RUN
- Other Scene/Episode production：NOT RUN
- Start-End fake pairing：NOT RUN
- Unlimited retry：NOT RUN
- Duplicate paid generation submit：NOT RUN
- New video engine/framework：NOT RUN

## 14. Blocker and Resume Boundary

唯一实际阻断为：当前 Windows Host 无法通过 TLS 下载 Provider 已完成的 GCS 输出对象；错误表现为连接关闭或 SSL unexpected EOF。Comfy Cloud MCP、OAuth、模板发现、图片上传、generation submit、job status 与 get_output 均可用。

恢复条件是当前 Host 网络/TLS 链路能够读取 Provider 输出对象，或 Provider 提供同一 completed job 的可访问输出通道。恢复后应优先复用现有 Shot `5-2-04` job 获取输出，不得重新生成；只有完成真实动态 Review 与 Media Persistence 后，才评估是否提交 Shot `5-2-05`。

## 15. Unified Acceptance Fields

```text
VIDEO_WORKFLOW_DISCOVERY = PASS
SOURCE_MEDIA_RESOLUTION = PASS

SHOT_01_VIDEO_PLANNING = PASS
SHOT_01_VIDEO_GENERATION = PASS
SHOT_01_VIDEO_CONTENT_REVIEW = NOT_RUN_OUTPUT_UNAVAILABLE
SHOT_01_VIDEO_TARGETED_REVISE = NOT_RUN
SHOT_01_VIDEO_MEDIA_IMPORT = NOT_RUN
SHOT_01_VIDEO_GENERATION_COUNT = 1
SHOT_01_VIDEO_TECHNICAL_RETRY_COUNT = 5

SHOT_02_VIDEO_PLANNING = PASS
SHOT_02_VIDEO_GENERATION = NOT_RUN_FAIL_CLOSED
SHOT_02_VIDEO_CONTENT_REVIEW = NOT_RUN
SHOT_02_VIDEO_TARGETED_REVISE = NOT_RUN
SHOT_02_VIDEO_MEDIA_IMPORT = NOT_RUN
SHOT_02_VIDEO_GENERATION_COUNT = 0
SHOT_02_VIDEO_TECHNICAL_RETRY_COUNT = 0

SINGLE_IMAGE_VIDEO_CONTRACT = PASS
SINGLE_IMAGE_VIDEO_REAL_E2E = FAIL_OUTPUT_DOWNLOAD_UNAVAILABLE
START_END_VIDEO_CONTRACT = PASS
START_END_VIDEO_REAL_E2E = NOT_RUN_NO_EXISTING_FRAME_PAIR

VIDEO_TECHNICAL_RETRY_CONTRACT = PASS
VIDEO_TECHNICAL_RETRY_VALIDATION = FAIL
VIDEO_GENERATION_IDEMPOTENCY = PASS
VIDEO_REVISE_SEPARATE_FROM_TECHNICAL_RETRY = PASS

CROSS_SHOT_DYNAMIC_REVIEW = NOT_RUN
CHARACTER_IDENTITY_DYNAMIC_CONSISTENCY = NOT_RUN
COSTUME_DYNAMIC_CONSISTENCY = NOT_RUN
SCENE_DYNAMIC_CONSISTENCY = NOT_RUN
LIGHTING_DYNAMIC_CONTINUITY = NOT_RUN
PROP_STATE_DYNAMIC_CONTINUITY = NOT_RUN
CAMERA_INTENT_COMPLIANCE = NOT_RUN

SHOT_01_VIDEO_MEDIA_PERSISTENCE = NOT_RUN
SHOT_02_VIDEO_MEDIA_PERSISTENCE = NOT_RUN
CURRENT_HOST_NEW_VIDEO_BYTE_EQUALITY = NOT_RUN

AUTHORIZED_CREDIT_BUDGET_APPROX = 182
ACTUAL_PROVIDER_GENERATION_COUNT = 1
ESTIMATED_ACTUAL_CREDITS_SPENT = 91

IMAGE_GENERATION = NOT_RUN
AUDIO_GENERATION = NOT_RUN
VIDEO_EDITING = NOT_RUN

DRAMA_PLUGIN_CHANGED = YES
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO

NEW_VIDEO_ENGINE = NO
NEW_RETRY_FRAMEWORK = NO
MINIO_SYNC_SYSTEM_INTRODUCED = NO

BATCH_5_6 = FAIL
NEXT_BATCH_READY = NO
```

## 16. Final Answer

Batch 5.6 已验证 `shot-production` 能从既有 Shot Media 自主选择合法的 Single Image 视频输入、编译受控运动、执行真实 Provider submit，并在 job polling/output 阶段保持同 job 幂等。它也正确坚持了“必须实际打开视频完成动态 Review 后才可持久化”的门禁。

但本批没有验证成功完整真实视频 E2E：第一条云端视频完成后无法下载至当前 Host，第二条为避免无意义的额外消费未提交。因此不能宣称两个视频生成完成，不能宣称动态 Review 或 Media Persistence PASS，最终为 `BATCH_5_6 = FAIL`。

## 17. Resume Execution — Windows GCS Download Recovery

恢复日期：2026-08-18  
恢复性质：同一 Batch 5.6 的网络阻断断点续跑；不是重新执行 Batch 5.6。

### 17.1 Inherited checkpoint

本次严格继承 Initial Batch 5.6 Attempt：

- Shot `5-2-04` Provider job `fb42f0e2-7b38-4adb-a474-86315efb68e8` 已 completed。
- Shot `5-2-04` generation count 为 1。
- 初次执行未取得 MP4，Dynamic Review 与 Media Import 未运行。
- Shot `5-2-05` 此前 fail-closed，未 submit generation。
- 初次下载命令包含 `--retry 3`，产生 `initial + 3 retries` 的历史偏差；该事实继续保留。

恢复期间没有重新 submit Shot `5-2-04`，没有重新生成 Batch 5.5 图片，也没有创建替代 job。

### 17.2 Existing Job Recovery

通过已授权的 Comfy Cloud MCP 对同一 completed job 调用 `get_output`。Live tool schema 要求使用 `prompt_id`，修正调用参数后成功取得新的 Signed Output URL。URL 在内存中解析，console、报告和日志均未输出完整 URL 或任何 `X-Goog-*` query 参数。

结果：

- Comfy Cloud MCP authentication：PASS（OAuth）。
- Comfy Cloud `get_output`：PASS。
- Existing job reused：YES。
- Duplicate generation submit：NO。
- Signed URL refresh：PASS。
- Output scheme：`https`。
- Actual output host：`storage.googleapis.com`。
- Output port：`443`。

### 17.3 Output Download Network Diagnosis

```text
ACTUAL_OUTPUT_HOST=storage.googleapis.com
DNS=PASS
TCP_443=FAIL
TLS=FAIL
HTTP=FAIL_NO_RESPONSE
SYSTEM_PROXY_ROUTE=FAIL
DIRECT_ROUTE=FAIL
SIGNED_URL_REFRESH=PASS
DOWNLOAD=FAIL
```

诊断说明：

1. `storage.googleapis.com` 能正常解析，因此不是 DNS failure。
2. 当前 Host 的显式 direct TCP 443 连接未建立，TLS handshake 无法开始/完成。
3. 使用系统 HTTP/代理路径的有限 GET 未获得 HTTP response；显式 direct 路径也失败。
4. 没有收到 HTTP 403、`SignatureDoesNotMatch`、`ExpiredToken` 或 `Request has expired`，所以没有证据表明本次失败属于 Signed URL 过期或签名错误。
5. Comfy Cloud MCP 与同一 completed job 的 `get_output` 已成功，因此失败不在 generation 或 Comfy job 状态阶段。
6. 因 TCP/TLS/HTTP 均未抵达可判读的 GCS response，不能把故障归因于 GCS 服务端；证据指向当前 Windows Host 的外网路由、代理绕过或 TLS 路径。

因此记录：

```text
ROOT_CAUSE = LIKELY_WINDOWS_PROXY_OR_TLS_ROUTE
FAILURE_OWNER_EVIDENCE = CURRENT_HOST_NETWORK_PATH
GCS_SERVER_FAILURE_PROVEN = NO
COMFY_CLOUD_GENERATION_FAILURE = NO
```

### 17.4 Resume Retry Compliance

本次恢复没有使用 Provider 示例中的 `--retry 3`。完整下载 operation 严格执行：

```text
initial attempt
retry 1
retry 2
= 3 calls total
```

三次路径依次用于系统路径、显式 direct 路径、系统路径 bounded retry，均失败。Resume technical retry count 为 2；不增加 generation count。

初次执行的历史下载 technical retry count 为 5，本次增加 2，因此 Batch 累计记录为 7。累计数字包含已经如实披露的历史超额偏差；它不代表本次再次违反策略。

```text
INITIAL_DOWNLOAD_RETRY_DEVIATION = OBSERVED
RESUME_DOWNLOAD_TECHNICAL_RETRY_COUNT = 2
CURRENT_RETRY_POLICY_COMPLIANT = PASS
SHOT_01_VIDEO_TECHNICAL_RETRY_COUNT_CUMULATIVE = 7
```

### 17.5 Dynamic Review and Persistence Gate

恢复下载仍未取得 MP4 文件，因此以下内容继续保持 NOT_RUN：

- container/video stream/duration/width/height 检查；
- 5-2-04 动态过程 Review；
- Identity、Costume、Required/Forbidden Semantic、Motion、Camera、Scene Stability 审查；
- targeted revise；
- Video Media import/get/resolve/hash equality。

没有以 `job completed` 或 `get_output PASS` 冒充 Dynamic Content Review PASS，也没有创建未经 Review 的 Media 记录。

### 17.6 Shot 5-2-05 Stop Gate

本任务要求 Shot `5-2-04` 至少达到 Download、Dynamic Review、Media Import、Resolve、Integrity 全部 PASS 后，才允许提交 Shot `5-2-05`。该前置条件仍未满足，因此：

```text
SHOT_02_DUPLICATE_OR_NEW_SUBMIT = NO
SHOT_02_VIDEO_GENERATION = NOT_RUN_FAIL_CLOSED
SHOT_02_ADDITIONAL_CREDITS_SPENT = 0
```

原 Batch 授权额度没有被扩大，实际 Provider generation count 仍为 1，预计实际消耗仍约 91 credits。

### 17.7 Resume Source and Scope Changes

本次恢复没有修改 Plugin、Skill Core、Drama MCP、Java、数据库或持久化结构。为避免 Signed URL 出现在 console/log 中，仅在报告 artifacts 目录运行了一个临时、批次内恢复脚本；它不进入业务源码，并在收口时删除。

没有新增 download proxy、GCS adapter、video downloader service、retry framework、Media sync 或新 Video Engine。

### 17.8 Resume Acceptance Fields

以下字段是本次 Resume 后的最新、权威状态；第 15 节保留为 Initial Batch 5.6 Attempt 的历史快照。

```text
VIDEO_WORKFLOW_DISCOVERY = PASS
SOURCE_MEDIA_RESOLUTION = PASS

OUTPUT_DOWNLOAD_NETWORK_DIAGNOSIS = FAIL
ACTUAL_OUTPUT_HOST = storage.googleapis.com
WINDOWS_OUTPUT_DOWNLOAD = FAIL

SHOT_01_VIDEO_PLANNING = PASS
SHOT_01_VIDEO_GENERATION = PASS
SHOT_01_EXISTING_JOB_REUSED = YES
SHOT_01_DUPLICATE_SUBMIT = NO
SHOT_01_VIDEO_CONTENT_REVIEW = NOT_RUN_OUTPUT_UNAVAILABLE
SHOT_01_VIDEO_MEDIA_IMPORT = NOT_RUN
SHOT_01_VIDEO_GENERATION_COUNT = 1
SHOT_01_VIDEO_TECHNICAL_RETRY_COUNT = 7
SHOT_01_RESUME_TECHNICAL_RETRY_COUNT = 2
SHOT_01_VIDEO_TARGETED_REVISE_COUNT = 0

SHOT_02_VIDEO_PLANNING = PASS
SHOT_02_VIDEO_GENERATION = NOT_RUN_FAIL_CLOSED
SHOT_02_VIDEO_CONTENT_REVIEW = NOT_RUN
SHOT_02_VIDEO_MEDIA_IMPORT = NOT_RUN
SHOT_02_VIDEO_GENERATION_COUNT = 0
SHOT_02_VIDEO_TECHNICAL_RETRY_COUNT = 0
SHOT_02_VIDEO_TARGETED_REVISE_COUNT = 0

SINGLE_IMAGE_VIDEO_CONTRACT = PASS
SINGLE_IMAGE_VIDEO_REAL_E2E = FAIL_OUTPUT_DOWNLOAD_UNAVAILABLE

START_END_VIDEO_CONTRACT = PASS
START_END_VIDEO_REAL_E2E = NOT_RUN_NO_EXISTING_FRAME_PAIR

VIDEO_GENERATION_IDEMPOTENCY = PASS
CURRENT_RETRY_POLICY_COMPLIANT = PASS
INITIAL_DOWNLOAD_RETRY_DEVIATION = OBSERVED

VIDEO_MEDIA_MINIO_PERSISTENCE = NOT_RUN
VIDEO_MEDIA_MYSQL_PERSISTENCE = NOT_RUN
VIDEO_MEDIA_RESOLVE = NOT_RUN
VIDEO_MEDIA_INTEGRITY = NOT_RUN

CROSS_SHOT_DYNAMIC_REVIEW = NOT_RUN
CHARACTER_IDENTITY_DYNAMIC_CONSISTENCY = NOT_RUN
COSTUME_DYNAMIC_CONSISTENCY = NOT_RUN
SCENE_DYNAMIC_CONSISTENCY = NOT_RUN
LIGHTING_DYNAMIC_CONTINUITY = NOT_RUN
PROP_STATE_DYNAMIC_CONTINUITY = NOT_RUN
CAMERA_INTENT_COMPLIANCE = NOT_RUN

AUTHORIZED_CREDIT_BUDGET_APPROX = 182
ACTUAL_PROVIDER_GENERATION_COUNT = 1
ESTIMATED_ACTUAL_CREDITS_SPENT = 91

IMAGE_GENERATION = NOT_RUN
AUDIO_GENERATION = NOT_RUN
VIDEO_EDITING = NOT_RUN

RESUME_CODE_CHANGED = NO
JAVA_CHANGED = NO
DRAMA_MCP_CHANGED = NO
DATABASE_CHANGED = NO
NEW_VIDEO_ENGINE = NO
NEW_RETRY_FRAMEWORK = NO

BATCH_5_6 = FAIL
NEXT_BATCH_READY = NO
```

### 17.9 Resume Conclusion

本次已证明断点恢复与幂等边界有效：Shot `5-2-04` 始终复用原 completed job，`get_output` 可刷新 Signed URL，且没有重复收费生成。但用户调整后的当前 Windows 网络仍无法建立到实际 Output Host 的可用 TCP/TLS/HTTP 下载路径，故 MP4、Dynamic Review 和 Media Persistence 仍无法完成。

根据明确停止边界，Batch 5.6 继续保持 `FAIL`；Shot `5-2-05` 未提交，`NEXT_BATCH_READY = NO`。
