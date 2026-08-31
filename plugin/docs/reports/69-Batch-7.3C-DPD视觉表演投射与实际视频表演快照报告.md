# 69 — Batch 7.3C DPD 视觉表演投射与实际视频表演快照报告

批次：Batch 7.3C — DPD Visual Projection & Realized Video Performance  
日期：2026-08-30  
最终结论：`BATCH_7_3C_ENGINEERING = PASS`  
用户艺术验收：`USER_VISUAL_PERFORMANCE_REVIEW = PENDING`  
停止边界：`STOP BEFORE Batch 7.3D Final Dubbing`

## 1. 执行摘要

本批已完成一条真实、可审计的生产闭环：

```text
DPDSnapshot
  -> VisualPerformanceBrief
  -> provider-neutral Video Generation Request
  -> real Comfy Cloud MP4
  -> durable Video Media
  -> controlled frame observation
  -> RealizedPerformanceSnapshot
```

复用既有潼关 Work、Scene、Shot、Character/Scene 资产与旧视频，不重新设计 Work/Script/Scene，也未重新生成 Character 或 Scene。Comfy Cloud 主生成 1 次、retry 0、候选 1；生成结果为 11.041667 秒无声 H.264 MP4，正式 Media 为 `media_ac9d14c5cdc74c43ba44562752cf9489`，内容哈希为 `066b281d01ba8f330c66c463c8c6ff0f238cc2f56af7c0dffbbaf812e62f677f`。经 Drama Service Resolve 回读，bytes、大小与哈希完全一致。

实际视频没有被 DPD 改写。Observation 记录了主体稳定坐姿、面向对手、后段低头再恢复等事实；嘴部因侧脸和胡须遮挡无法可靠判断，明确记录为 `UNKNOWN`。DPD 与实际视频的差异被标记为非阻断 `DEVIATED` Diagnostic。Fish Audio、Qwen TTS、OpenAI TTS 调用均为 0。

## 2. 本批范围

本批只建设两项能力：

1. `DPD + Shot/Scene/Character visual context -> VisualPerformanceBrief`；
2. `Generated Video -> accepted observation -> RealizedPerformanceSnapshot`。

不在范围内：最终配音、TTS、视频条件化 Audio Projection、Lip Sync、viseme、SFX、ambience、music、mix、AV mux、完整 Episode 生产。

## 3. Architecture Freeze

以下生产区域保持冻结：DPD Core、SceneDPD、BeatDPD、LineDPD、DPDSnapshot、AudioPerformanceBrief、Audio Projection、CreativeVoiceProfile、Voice lifecycle 与 Fish Audio。7.3C 未修改这些合同的语义或实现；共享 `contracts/__init__.py` 仅增加两个视觉合同导出。

冻结因果链为：

```text
DPD = INTENDED PERFORMANCE AUTHORITY
VisualPerformanceBrief = intended visible performance
Video Media = generated pixels over time
RealizedPerformanceSnapshot = accepted actual visible facts
```

任何 DPD-vs-Video 偏差均不得拒绝 Video、阻止 Media、阻止 Snapshot 或偷偷改写实际事实。

## 4. 开始前 Visual AS-IS 审计

编码前读取并审计了 65、66、67、68 报告，DPD/Scene/Shot/Asset/Media 合同，Shot Design、Shot Production、Asset Resolution 技能，现有 Comfy Cloud 集成，Batch 5.x/6.x 真实视频报告与当前 Work/Script/Episode/Scene/Shot。

十项审计结论如下：

1. **现有 Visual Prompt / Shot Prompt contract**：此前没有 typed Visual Performance 或 Shot Prompt 合同。Shot 的 action、framing、composition、cameraBehavior 保存在开放 `Shot.content`；视频工具表面为 `prompt + single image` 或 `start/end frame`。
2. **实际属于 DPD 的字段**：objective、interaction target、dramatic action、tactic、authority、relationship、internal activation、external control、subtext、observable intent 与 performance boundaries。
3. **属于 Visual Projection 的字段**：当下 body/head/gaze/facial tension/gesture/orientation/pre-speech/visible control 的可观察方向。
4. **属于 Camera / Cinematography 的字段**：shot type、framing、scale、composition、lens/angle（若存在）、camera behavior/movement；继续归 Shot Design 所有。
5. **Comfy adapter 是否混入戏剧推理**：Host-side Comfy MCP 本身不判断人物动机，但既往 Agent 直接把 action、identity、camera、performance 混为一条 prompt，没有 typed 边界。7.3C 在 adapter 之前建立了边界。
6. **现有视频 generation request 是否 provider-neutral**：Drama `production.generate_video` 的表面模式是 provider-neutral，且固定单图或首尾帧；但开放 parameters 有污染风险。本批核心请求指纹只使用中性输入，Comfy workflow/node/model/job 信息不进入核心合同。
7. **已有 review / analysis 结构**：可复用 `visualContentReview`、连续性报告与 Media 校验习惯；此前没有结构化 realized performance snapshot。
8. **如何取得并分析真实 MP4**：Comfy job 完成后 `get_output` 下载本地 MP4；ffprobe 校验流；基础内容 Review；`media.import_media` 持久化；`media.resolve_media` 回读哈希；随后按 1 fps 全景与 2 fps 主体脸部受控抽样形成 accepted observation。
9. **stable Media fingerprint**：Media 已有稳定 id、sourceRef、mimeType、fileSize、contentHash；此前缺少 visual projection、video request、realized performance 三段规范指纹。
10. **可复用潼关资产**：Work `work_9cc5d11969a64f93bce4a544f349c793`；Scene `scene_3ad95aa042e647d9a9be05a51dd8a009`；Shot 1-03 `shot_83db7eb53b2f49d3a58428d4659e584e`；哥舒翰、王思礼、潼关稳定 Asset/Media；旧无声 Shot Video `media_63787886dc85413c90207e17d68df520`。

旧 Video 物理对象在当前存储中缺失，但 Comfy 原 Job 仍可恢复完全相同 bytes；本批按原 SHA-256 恢复该稳定 Media，并从 200 ms 提取一张通过 Review 的首帧，导入为 `media_3e48554b57e64b4caabf98e50b4bebab`。未改变旧 Media identity。

## 5. DPD / Visual Projection 边界

DPD 回答“角色为什么这样演、对谁、采取什么戏剧行动、权威与控制关系是什么”。Visual Projection 不重做这些判断，只回答“上述已定戏剧行为如何变为视频模型可见的动作”。

本 Fixture 的 DPD 为：哥舒翰对王思礼作受控拒绝，`HIGH internal activation + HIGH external control`。投射结果不是“大表情”，而是稳定坐姿、低动作幅度、克制头动、持续视线压力、可见面部张力与有限手势。

## 6. Character / Scene / Performance 边界

Character 稳定外观来自 `MASTER_CHARACTER_CARD`、Character Asset、face/costume reference 及其稳定 Media。Scene 稳定外观来自 `MASTER_SCENE_CARD`、`SCENE_REFERENCE` 及其稳定 Media。`VisualPerformanceBrief` 只保存两者的 material identity fingerprint，不拥有脸、年龄、发型、服装、盔甲、建筑或历史场景设计。

真实 provider 输入采用一张既有正式视频派生的稳定双人首帧；它已经固化哥舒翰、王思礼、军案、地图与环境身份。实际引用数 1，未超过既有上限 3，也未动态堆叠多张参考。

## 7. Camera / Performance 边界

`VisualPerformanceBrief` 禁止 framing、shot scale、lens、angle、composition 与 camera movement。它只拥有人物当下如何动、看和控制可见表演。

Shot 1-03 原有 `TWO_SHOT`、composition 与 cameraBehavior 继续由 Shot Design 提供。`compile_video_motion_prompt()` 是 materialization 边界：它将独立的 action、performance brief 与 camera design 合并为 provider prompt，但不会把 Camera ontology 写回 Brief。

## 8. VisualPerformanceBrief Contract

新增最小 provider-neutral `visual-performance-brief-v1`：

- lineage：dpdFingerprint、sceneId、shotId、shotFingerprint；
- stable identity lineage：characterVisualIdentityFingerprint、sceneVisualIdentityFingerprint；
- visible performance：bodyActivity、headBehavior、gazeBehavior、facialTension、gesturePolicy、interactionOrientation、preSpeechBehavior、visibleControl；
- performanceBoundaries；
- canonical fingerprint。

合同拒绝 unsupported version、空 direction、Shot/Scene/Speaker/Character mismatch、unknown/provider field 与 Camera field。未建立 Emotion ontology、FACS、Gesture DSL 或 Body Language taxonomy。

## 9. DPD -> Visual Mapping

组合映射优先于单字段映射：

| DPD 组合 | Visual Projection |
|---|---|
| HIGH activation + HIGH control | low-amplitude body、stable posture、restrained head、focused gaze、visible facial tension、restrained gesture |
| HIGH activation + LOW control | larger-amplitude body、quicker/uneven head recovery、broader gesture、visible expression change |
| MEDIUM activation + HIGH control | low-to-medium activity、small responsive head adjustment、contained facial variation |

同一 DPD、Shot 与 visual identity 产生相同 Brief 和 fingerprint；material DPD 变化产生不同 Brief/fingerprint。离线 fixture 已覆盖 HIGH/HIGH 与 HIGH/LOW 对照，并确认 DPD 输入没有被修改。

## 10. Comfy Capability Mapping

| 能力 | 状态 | 处理 |
|---|---|---|
| 固定单图 I2V | SUPPORTED | `SINGLE_IMAGE`，引用数 1 |
| 11 秒、720p、无音频 | SUPPORTED | duration=11，generateAudio=false |
| 人物/场景身份延续 | APPROXIMATED | 由稳定首帧与 preservation boundary 约束 |
| controlled gaze | APPROXIMATED | 自然语言 performance prompt |
| low-amplitude gesture | APPROXIMATED | 自然语言 performance prompt |
| facial tension | APPROXIMATED | 自然语言 performance prompt |
| 精确动作时间窗 | UNSUPPORTED | 不静默宣称；由生成后 Observation 记录实际结果 |
| 精确 speech/mouth window | UNSUPPORTED | 本批不使用 Audio driving；只观察，无法可靠看出时为 UNKNOWN |

Comfy adapter 只 materialize Brief + Shot camera/action + stable frame，不重新判断目标、潜台词、关系或历史设定。

## 11. Reference Asset Reuse

复用：既有 Work/Script/Episode/Scene/Shot、哥舒翰 Character Master、王思礼 Character Master、潼关 Scene Master 与 Batch 6.0R-E2E 旧无声视频。未生成新的 Character/Scene master，未修改 Work、Script、Episode、Scene 或 Shot Design。

旧视频恢复哈希为 `5027499b630045813e09ac082c90f9251a95e292bcb4d9767e7d7b0a5a0a065a`；派生 START_FRAME Media 为 `media_3e48554b57e64b4caabf98e50b4bebab`，哈希 `9f110af425cb7fe120d4c9c6b37a93d7363f5b09807667afb8cad85b1346da38`。

## 12. Visual Fingerprint / Lineage

```text
DPD fingerprint
  2d826a70...
    -> Visual Projection fingerprint
       abea5007...
         -> Video Request fingerprint
            74c0b047...
              -> Video content hash
                 066b281d...
                   -> Realized Performance fingerprint
                      a2d3d311...
```

所有指纹使用 canonical SHA-256。排除 timestamp、UUID、Host、Comfy task/workflow/node/model、temporary/signed URL、provider response 与 secret。Video request 指纹包含 Brief fingerprint、Shot、固定输入模式、源 Media 内容哈希、camera design fingerprint、compiled motion prompt、目标时长与 `audioPolicy=NONE`。

## 13. Offline Fixture

离线 fixture 复用 7.3A DPD case，并建立更适合视觉的 Shot binding。验证结果：

- HIGH/HIGH -> stable, low-amplitude, focused gaze, visible tension, restrained gesture；
- 外部控制改为 LOW -> body/head/gesture direction 与 fingerprint 均变化；
- 字段顺序改变 -> canonical fingerprint 不变；
- provider/camera/psychological field 注入 -> validation error；
- invalid timestamp、end < start、outside duration -> validation error；
- 同一 video hash + canonical observation -> same realized fingerprint；
- video bytes hash 改变 -> realized fingerprint 与 future audio lineage 均改变。

## 14. Real Comfy Cloud E2E

前置检查：Comfy Cloud auth 与 MCP 健康；模板 `api_bfl_flux3_i2v` 可用；Drama MCP/Service 健康；所需稳定首帧可 Resolve；当前存储 owner 路径可读写；音频关闭。

真实运行：

- primary generation count：1；
- retry count：0；
- candidate count：1；
- Provider job：仅保存在 provider-generation evidence，不进入核心合同；
- 估算 credits：256；
- 真实扣费数值：Provider 未返回可验证账单，本报告不推测；
- `Fish Audio / Qwen TTS / OpenAI TTS = 0`。

Job 完成状态经专属 Job ID 确认。没有用 queue count 冒充完成，也没有因等待超时重复提交。

## 15. Generated Video Artifact

- Review MP4：`artifacts/batch7-3c/review/shot-video.mp4`；
- duration：11.041667 s；
- dimensions：1280 x 704；
- frame rate：24 fps；
- codec：H.264；
- audio streams：0；
- size：5,489,983 bytes；
- SHA-256：`066b281d01ba8f330c66c463c8c6ff0f238cc2f56af7c0dffbbaf812e62f677f`。

## 16. Observation Method

`OBSERVATION_METHOD = CONTROLLED_FRAME_SAMPLING`。

先以 1 fps 观察全镜头的 screen presence、orientation、body/head/gaze 与 interaction distance，再以 2 fps 裁取主体脸部检查 gaze、facial tension、expression change 与 mouth visibility。没有逐帧全量分析、FACS、情绪分类、viseme 或 phoneme extraction。

Observation 是 review-accepted canonical result。侧脸与胡须遮挡导致 mouth onset/end 不可靠，因此写 `UNKNOWN`，不根据台词或 DPD 猜测 speech window。

## 17. RealizedPerformanceSnapshot

新增 `realized-performance-snapshot-v1`，仅记录可观察事实与最小时间窗。真实结果摘要：

- stable medium two-shot；
- 主体从 0 ms 起始终位于 screen-right；
- 坐姿稳定，面向 screen-left partner；
- 视线大部分时间指向对手，后段低向桌面，结尾前回向对手；
- 主要头动窗口约 `7500–10500 ms`；
- visibleActivation=MEDIUM；facialTension=HIGH；expressionChange=PRESENT；
- 没有可靠检测到主体独立手势；
- mouthActivity=UNKNOWN；不写虚假 mouth/speech window。

Snapshot fingerprint：`a2d3d311576d75a305e6453089176ac89b0d8cfd9c3acd2a141ee24a13cefd12`。

## 18. Intended vs Realized

总体 Diagnostic：`DEVIATED`，只作诊断、不阻断。

- body amplitude、stable posture、restrained head、facial tension、visible control：ALIGNED；
- gaze：大部分 aligned，但后段转向桌面，DEVIATED；
- pre-speech behavior：mouth onset 不可靠，UNKNOWN；
- actual Snapshot 保留后段低头事实，没有为了贴合 DPD 写成“全程稳定直视”。

详见 `artifacts/batch7-3c/review/intended-vs-realized.md`。

## 19. Video -> Future Audio Invalidation

本批只冻结依赖，不实现 Audio：

```text
FutureFinalAudioProjectionFingerprint = hash(
  dpdFingerprint
  + voiceFingerprint
  + spokenContentFingerprint
  + realizedPerformanceFingerprint
)
```

Video V1 -> Snapshot A -> Audio A；Video bytes 或 accepted observation 改变后，Snapshot B 的 fingerprint 改变，Audio A 必须 `STALE / REGENERATE`。最终配音直接服从实际视频 Snapshot，即使 Video 偏离 DPD。

若戏本身错，修改 DPD；若 DPD 正确但 Video 演错，只修改 Visual Projection、video generation parameters 或 stable assets，重新生成 Video 与 Snapshot。不得同时手工修改 Audio Projection。

## 20. Media Persistence / Hash

正式 Video Media：`media_ac9d14c5cdc74c43ba44562752cf9489`。

Media 合同完整保留 stable id、work/shot binding、type/purpose、sourceRef、duration、mimeType、fileSize、contentHash 与 source lineage。实际 MP4 从 Drama Service 的 owner content route 回读，得到 5,489,983 bytes 与 SHA-256 `066b281d...f677f`，与本地下载和 Media metadata 完全一致。未持久化临时 Comfy URL、signed URL、token 或 secret。

详细 Snapshot 本批作为 deterministic intermediate artifact 保存在 review package，不新增 Java Entity、数据库表、CRUD 或搜索 MCP。

## 21. Tests

| 测试 | 结果 |
|---|---|
| DPD regression | PASS |
| Visual Projection unit/contract/fingerprint | PASS |
| Video request adapter/fixed-mode regression | PASS |
| Realized Snapshot / observation validation | PASS |
| Character/Scene identity separation | PASS |
| Camera/performance separation | PASS |
| reference input limit（实际 1 <= 3；既有 production tests） | PASS |
| Media import/restore/resolve/hash | PASS |
| Audio regression | PASS |
| Plugin full pytest | PASS — 181 passed |
| Plugin strict mypy | PASS — 52 source files |
| MCP pytest | PASS — 26 passed |
| MCP strict mypy | PASS — 4 source files |
| Java | NOT RUN — no Java production change |

## 22. Complexity Audit

生产核心只新增两个 Contract：`VisualPerformanceBrief`、`RealizedPerformanceSnapshot`；一个小型 projection/observation helper module 与一个本地 `VisualProjectionError`。没有新增 enum class（只使用最小 Literal）、数据库字段、Java、Service、MCP tool 或通用 lineage service。

未建立 BodyLanguageOntology、ExpressionOntology、Emotion classifier、GestureDSL、VideoPerformanceAST、FrameAnalysisFramework、VisionService 或 Generic Multimodal Workflow Engine。

## 23. Severity

- P0：0。没有用 DPD 伪造 Snapshot；Video 变化会改变 realized fingerprint；核心合同无 Comfy 字段。
- P1：0。时间窗均在 duration 内；引用数 1；Video 已耐久持久化；实际 gaze deviation 被如实保留。
- P2：1 个已知观察限制。主体为侧脸且有胡须，mouth activity 无法可靠判定，按合同记 `UNKNOWN`；这不是阻断或伪造。

## 24. User Visual Review Boundary

自动系统只确认可播放性、主体存在、基础身份连续、动作检测、Media 完整、Observation 与 fingerprint 正确。它不宣称这是“最好表演”或达到特定影视艺术水准。

`USER_VISUAL_PERFORMANCE_REVIEW = PENDING`。用户可直接查看 MP4、Brief、Snapshot 与 intended-vs-realized diagnostic。用户若认为后段低头太快或不合适，后续只修改 Visual Projection / Video generation 并重新 Observation，不触碰 Audio。

## 25. 未解决问题与必须回答的问题

### Q1 DPD 与 Visual Projection 的边界是什么？

DPD 拥有戏剧意图与 authority；Visual Projection 只把已定意图转为可见行为方向，不重新解释剧情。

### Q2 Visual Projection 与 Shot Camera Design 的边界是什么？

人物如何动、看、控制属于 Performance；framing、scale、lens、angle、composition、camera movement 属于 Shot Camera Design。

### Q3 Character/Scene stable visual identity 来自哪里？

来自 MASTER_CHARACTER_CARD、Character Assets、MASTER_SCENE_CARD、SCENE_REFERENCE 与稳定 Media，不来自 DPD 或 VisualPerformanceBrief。

### Q4 RealizedPerformanceSnapshot 是什么？

对已存在视频的 accepted、provider-neutral、可观察、可审计、可指纹化事实描述。

### Q5 它与 DPD 有什么区别？

DPD 是计划中的表演 authority；Snapshot 是实际 pixels 演出的事实，不拥有 objective/subtext/relationship/internal activation。

### Q6 视频偏离 DPD 时是否阻断？

`NO`。

### Q7 视频偏离时 Snapshot 写哪个？

写 `actual video`。

### Q8 以后最终配音以什么作为直接视觉事实？

`RealizedPerformanceSnapshot`。

### Q9 如果视频错误，应修改哪些节点？

戏剧意图错则修改 DPD；DPD 正确但实现错则修改 Visual Projection、video generation parameters 或 stable assets，然后重新生成 Video 与 Snapshot。

### Q10 Video 更新后旧 Audio 如何处理？

`STALE / REGENERATE`。

### Q11 Observation 是否重新解释人物目标/潜台词？

`NO`。

### Q12 Realized Snapshot 是否需要 Java/DB？

当前 `NO`。它是 deterministic intermediate artifact；复用现有 Media 与文件证据即可。

### Q13 Comfy-specific 信息是否进入 provider-neutral contract？

`NO`。仅存在 provider adapter / generation evidence。

### Q14 真实视频生成与 Observation 是否完整跑通？

`YES`。真实 Job、MP4、Media import/resolve/hash、controlled observation 与 Snapshot 全部 PASS。

### Q15 用户是否已完成 Visual Artistic Review？

`NO — PENDING`。

## 26. 7.3D 前置条件

只记录未来依赖，不实施：

```text
DPD
+ Voice Identity
+ SpokenContent
+ RealizedPerformanceSnapshot
-> Final Audio Projection
```

`Final Audio must follow actual generated video performance.` 若 Video 错误，应 regenerate video -> new snapshot -> old audio stale；Audio 不负责纠正 Video。

## 27. 最终 PASS / PARTIAL / FAIL

```text
DPD_VISUAL_BOUNDARY = PASS
VISUAL_PROJECTION_CONTRACT = PASS
DPD_TO_VISUAL_PROJECTION = PASS
CHARACTER_VISUAL_IDENTITY_SEPARATION = PASS
SCENE_VISUAL_IDENTITY_SEPARATION = PASS
CAMERA_PERFORMANCE_SEPARATION = PASS
PROVIDER_NEUTRALITY = PASS
VISUAL_PROJECTION_DETERMINISM = PASS
REAL_COMFY_VIDEO = PASS
VIDEO_MEDIA_PERSISTENCE = PASS
REALIZED_PERFORMANCE_OBSERVATION = PASS
REALIZED_PERFORMANCE_SNAPSHOT = PASS
REALIZED_PERFORMANCE_FINGERPRINT = PASS
VIDEO_AUDIO_INVALIDATION_CONTRACT = DEFINED
DPD_REGRESSION = PASS
AUDIO_REGRESSION = PASS
COMPLEXITY_AUDIT = PASS
USER_VISUAL_PERFORMANCE_REVIEW = PENDING
BATCH_7_3C_ENGINEERING = PASS
BATCH_7_3C = PASS
```

Boundary：`STOP BEFORE Batch 7.3D Final Dubbing`。
