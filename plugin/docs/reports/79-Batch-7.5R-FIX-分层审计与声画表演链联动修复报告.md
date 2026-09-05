# Batch 7.5R-FIX — 分层审计与声画表演链联动修复

## Layer Audit Matrix

本报告是 **AUDIT → MARK → FIX → CASCADE → E2E** 的实际执行结果。实施前矩阵先于代码保存于 `artifacts/batch7-5r-fix/evidence/layer-audit-initial.json`，完整记录 Evidence、Owner、Impact radius、Downstream stale、Required fix。表中 Final 是工程职责完成状态，旁列艺术状态独立，不能互相覆盖。

|Layer|Initial|Observed problem / Owner|实际 Fix|Final 工程|艺术状态|
|---|---|---|---|---|---|
|L1 Voice Identity / Casting|NEEDS_FIX|候选1被用户选择不等于新 Take 艺术通过；旧声音/旧 Take 用户 FAIL 必须按 hash 生效|复用候选1，零 Design；freshness/cache 排除用户拒绝的音频；明确 final-for-target 与 USER accepted 的区别|PASS|NEEDS_REVIEW|
|L2 Audio Acting / Fish|NEEDS_FIX|丰富 Brief 退化为单前缀；conditioner 用统一收束覆盖句内行动与开放句尾|新增紧凑 phraseDeliverySpans；目标、关系、行动推进进入真实 Fish rendered text；conditioner 保留 authored Brief|PASS|QUESTIONABLE；旁白感 UNKNOWN|
|L3 Execution Timing|NEEDS_FIX|视觉仍用 5000/3200ms 计划，后端对账却用实际音频|纯 helper 从实际完整 A/B 时长派生执行窗口，保护 reaction/minimum holds，Plan 不回写|PASS|最终节奏待用户|
|L4 Visual Performance Projection|NEEDS_FIX|只 hash 丰富字段、实际 prompt 丢失方向/交接/边界|relative phases 真正使用 actual-derived execution；逐轮传递 speaker/listener、gaze、gesture、transition purpose、boundaries|PASS|QUESTIONABLE|
|L5 Video / RP|NEEDS_FIX|旧视频用户 FAIL；RP 无明确 speaker scope|一次新 I2V；新 Shot/A/B RP；nullable observedSpeakerKey；当前画面重新观察|PASS|QUESTIONABLE|
|L6 Reconciliation / Lip Sync|NEEDS_FIX|只有物理 fit；旧 Audio source 与新 target 混淆；未实现嘴型|独立 target-fit 与完整 speaker RP；participation-constrained 对账；真实 Sync3 坐标选脸，两个操作；新嘴部/身份/非说话者观察|PASS|嘴型质量 QUESTIONABLE，待听看|
|L7 Final AV|NEEDS_FIX|无完整 A/B 带嘴型新 Final，不能继承旧单句血统|两条原始 Audio 完整合成；新的嘴型 Video、FINAL_AV、typed manifest、完整 source/projection/timing/RP/lip lineage；Cloud hash 验证|PASS|PENDING_USER_REVIEW|

**最终完整 Review Video**：[06-final-av.mp4](/Users/zy/historical-plugin/artifacts/batch7-5r-fix/review/06-final-av.mp4)。新 Final Media `media_061eb4b9d236437eb088bf95d927c30f`。V1 Pipeline = READY_FOR_USER_REVIEW；这不是 USER_ARTISTIC_PASS。

## 授权、历史事实与证据边界

最新用户附件 `pasted-text.txt` 正式任务为 7.5R-FIX：第14–49行明确替代逐层 STOP，并授权真实 Provider E2E；第1176–1201行给出 A TTS 1、Comfy 1+最多1纠偏及必要 Lip Sync 预算。因此本批没有沿用上一份 **7.5R AUDIT ONLY** 的零调用限制。第一次自动审批误按旧限制拒绝 TTS；只读核实最新附件原文后重新提交获准，没有绕过拒绝。后续没有中间用户批准伪造。

以下历史用户结论继续生效：旧7.5 VIDEO_DIALOGUE_COORDINATION=FAIL；旧7.5 Turn A AUDIO_ARTISTIC_REVIEW=FAIL；NARRATOR_BIAS=STILL_PRESENT；旧 Lip Sync 未实现。新素材与这些旧 hash 分开记录，机器 QUESTIONABLE 不覆盖旧 USER FAIL。

回读链路为 7.2S/Fish、Fresh Voice Design、7.3A DPD、7.3B/B.1/B.2 Audio/Voice、7.3C Visual/RP、7.3D Video-conditioned Audio、7.3E AV、7.4A/B/C、7.5、7.5R 报告及当前源码。上一份统一审计78继续保留，本报告记录协调实施及真实结果，不重新发明架构。

|证据源|本批用途|
|---|---|
|当前 `src/drama_plugin`、contracts、两个 production SKILL|实际契约、渲染、staleness、组装路径|
|`docs/reports/53…`、65、66、67、68/71、69、70、72、74–78 对应 Batch 报告|为什么存在 Voice/DPD/projection/RP/timing 职责；历史失败与设计边界|
|`artifacts/batch7-4a/evidence/dialogue-timing-plan.json`|原始 PLANNED，不修改|
|`artifacts/resume-7-4b-turn-a/evidence/turn-a-production-dpd.json`|A 正式 production DPD，与 planning DPD 区别保留|
|`artifacts/batch7-5/evidence/*`|旧 Voice/Audio/Video/RP/reconciliation 与失败回归|
|`artifacts/batch7-5r-fix/evidence/current-context.json`、`final-fixture-replay.json`|当前 durable facts 与冻结范围校验|
|本批 `turn-a-projection.json`、`execution-timing.json`、`video-request.json`、`production-observations.json`、`target-performance-fit.json`|输入真正进入执行链的证据|
|本批 `sync3-capability.json`、`lip-executed-workflows.json`、`lip-submission.json`、`lip-observation.json`|实际坐标参数、执行图、付费 operation 与结果 QC|
|`cascade-trace.json`、`final-lineage.json`、`final-cloud-hash.json`|全链 fingerprint 和最终云端事实|

无真实听觉判断能力。因此不以 ASR、波形、RMS、频谱推断角色感或旁白感；新声音的最终听感仍由用户裁定。ASR 本批仅证明正文清晰度，不能证明表演。

## 本次真实 Cascade Trace

```text
用户已选择的 candidate1 Voice 不变
→ 排除旧7.5 A艺术FAIL hash
→ 修 Audio projection / Fish phrase rendering
→ 一次新 A TTS（3898 → 4270ms）；B仍4107ms
→ 旧 actual-execution material stale
→ 重算 actual-derived visual execution（Plan仍5000/3200）
→ 新 Visual Brief / Video Request fingerprint
→ 一次新 11042ms Video
→ 旧 RP / target-fit / reconciliation stale
→ 新 Shot RP + A RP + B RP
→ Full physical fit + visible participation fit
→ 新 A500–4770 / B5570–9677 proposal
→ explicit production anchor（USER approval仍PENDING）
→ no-lip preview
→ Sync3 selected left face + A audio；selected right face + B audio
→ 新 mouth-only derivative Video + 新 post-lip Shot/A/B RP
→ 原始 A/B Audio + frozen windows + AcousticMixPlan
→ 新 FINAL_AV attempt + Cloud MinIO download hash
→ STOP USER REVIEW
```

|节点|实际结果|
|---|---|
|Voice A|`voice_e8731619bea0467db69b197cef1299a1`，master hash `265c94c6c3b019a25fae34ad715ad8f1a33198d71c156397d61ed49cc695ef28`；未改|
|A Audio|`media_9685c608eef54e5bb698d79221d4eb91` / 4270ms / `755be137f268744afcf4ca638c85b1688851e9d207a64a646bb902cb4aec674c`|
|B Audio|`media_6f4d16d785b84b52b3062e0666a826b5` / 4107ms / `4db91e1299cb3083db55290e5e23ef8595e012e5a7b3fe185ba80a44121e7a9c`；未改|
|Execution fingerprint|`3537d6e11ae7f06177c934572d603118757233e5d1aefaeebf0463bf0933dc2b`|
|Visual Brief fingerprint|`364339c5d43a50017689bf161c1fd6a8ba04ee8ad6f5850ea093c47dbfc21ae6`|
|Video Request fingerprint|`7a0b51dd9a85c2609d0ec59fc8fe8a17335bfe5b445407ad0fab8d56385c9425`|
|Video Media / hash|`media_5086fb709d4749869361beca68db1d05` / `f8eb8fa65db0dee0cac8dd5020cc73aae9da8f16d8b494288190f061e184aeb1`|
|Reconciliation fingerprint|`035971be6c7f015bd3964009807603a2581dd890ebaef8e468b1fb5c8a5e75b8`|
|Lip derivative Media / hash|`media_d40c4d20f470480d8c8f1725b5e60fbd` / `8584891a1cfd088688ebfac6e7745abca4273160c4ba1b44be21b54d9c6e5730`|
|Lip provenance fingerprint|`d7bea4ff3228cbd21be92cbd4c8f7199a5b14e4867ce29c6a75d205509a7f4fc`|
|Final Media / hash|`media_061eb4b9d236437eb088bf95d927c30f` / `db1803a9611a9beac8d8fecc513975ea9adf101faaff1c9ef8866f2a52088928`|

全部6个 source/post-lip RP fingerprints 记录于 `cascade-trace.json`，均绑定其实际 Video hash，不复用旧 a2d3d3… / 7.5 RP。

## 四层 Timing 与 Audio / Video 生命周期

|层|Authority|本批值 / 规则|
|---|---|---|
|PLANNED|DialogueTimingPlan 创作意图|A5000/B3200，pre500，reaction800，原 Plan fingerprint `dfe0dc594602c215597d462e5e670814e783fddbfc1255e5ee1b2eedb8776083`，不回写|
|EXECUTION|`derive_visual_execution_timing` deterministic projection|actual A4270/B4107 + planned holds + target11000，A500–4770、B5570–9677、target post1323|
|REALIZED|物理 Audio/Video 和 RP|Video265帧/24fps=11041.667ms，Domain round=11042；真实 Audio whole-line duration；可见事实与不确定性|
|ACCEPTED|用户/Production authority 明确区分|本批按最新授权使用 `EXPLICIT_PRODUCTION_ANCHOR` 继续 review attempt；不是 USER_REVIEW；用户最终 timing/artistic acceptance PENDING|

本次 required minimum=10177ms，actual shot slack=865ms，实际 post hold=1365ms。未压 reaction、未减少 minimum post、无 overlap。旧5871和旧5198均未被继承。

Actual Audio 应影响 Visual Production，但通过派生 EXECUTION，不回写 PLANNED。Video Provider 只得到相对阶段与 speaker ownership，不声称毫秒级执行。Realized 不能改 DPD；Accepted 不能冒充 observed mouth onset。

A 新片是 DPD production Audio，经新 target-fit 后冻结为本次 `final-for-target` 输入，未伪造“基于新 Video 生成”的 provenance。B 的旧 video-conditioned source Video/RP 保持原样：source lineage technically valid，原 wrapper 对新 target 不是 VIDEO_CONDITIONED_CURRENT；通过新的 speaker-specific RP / target-fit 作独立复用判断。本次没有发现必须机械重 TTS 的证据，故 B、post-video TTS 均为0。target fit QUESTIONABLE 仅支持用户已授权的 review attempt，不能宣称艺术 accepted。

Video源称 `VISUAL PERFORMANCE SOURCE`；嘴型输出为独立 derivative；Final AV 是 `final-av-attempt:<fp>:batch7-5r-fix`，reviewStatus=PENDING。用户批准以后才可成为 accepted canonical result，本次没有修改 Work binding 或把中间素材写成用户已接受。

## 修复内容、职责和 Impact Radius

### P0 协调集合（同一批完成）

|Change|Owner / Exact responsibility|Touched|Stale cascade / Migration / Validation|
|---|---|---|---|
|P0-1 实际执行时间 authority|Timing projection，把完整 actual durations 与计划 holds 派生为唯一此轮视觉执行目标|`dialogue_timing.py`、Visual Brief/projector|duration变化→execution/brief/request；不回写Plan；缺失/负数/预算冲突/tamper tests|
|P0-2 Audio acting loss 与 lifecycle|Audio projection/adapter，将句内行动真正送入 Fish；preserve authored conditioning；用户FAIL压过cache|`contracts/audio_projection.py`、`audio/projection.py`、`video_conditioning.py`、`foundation.py`、Fish/role_dubbing adapters|projection变化→A音频→duration→visual/fit；旧无span序列化/hash兼容；lexical preservation、range、非法cue、conditioner测试|
|P0-3 对白视觉实际渲染|Visual projection，speaker/listener/relative phase/目标/视线/手势/交接目的/边界须进入真实prompt|`visual/performance.py`、`contracts/visual_performance.py`|execution/DPD/brief变化→request→Video→RP；保留legacy未传execution路径；ordering、mapping、rendering、fingerprint regression|
|P0-4 RP scope 与 target-fit reconciliation|Realized / reconciliation，全speaker事实、物理预算优先、可见参与范围其次；独立 source provenance 与 current target-fit|`dialogue_reconciliation.py`、其contract、RP nullable speaker field|Video/RP/Audio/review变化→fit/reconciliation stale；旧policy保留；新`PARTICIPATION_CONSTRAINED_V1`；wrong speaker/hash/userFAIL/conflict/unknown tests|
|P0-5 有界执行与冻结规则|existing shot/audio skills + resumable fixture runner|两个 SKILL、`run_batch7_5r_fix.py`|测试gate→必要A→execution→一Video→RP/fit；unknown submission先恢复；V0/V1共享最多2视频提交，第二次需失败证据；本次未使用纠偏|

### 必要 P1（同批接入）

|Change|Owner / Exact responsibility|实现与证据|
|---|---|---|
|P1-1 Active-speaker sync safety|adapter，验证 capability/face selection/audio/hash/window，不拥有timing|`providers/lip_sync.py` 两个小校验函数；`prepare_speaker_operation`、`validate_lip_derivative`；wrong-speaker-mouth、identity/beard失败、audio/duration变化负测|
|P1-2 Derivative lineage / post-lip QC|production evidence，source与lip derivative不同身份，新mouth/identity/非speaker观察|`finish_batch7_5r_fix.py`、lip provenance、post-lip RP；真实两次Sync3结果；265帧不变|
|P1-3 Complete A/B final assembly|现有 AV manifest / AcousticMixPlan，完整 original speech clips + frozen window|`MOUTH_ONLY_DERIVATIVE` policy，typed manifest/fingerprint，两个AVSync与AcousticMixPlan；FINAL_AV attempt + Cloud hash + fixture replay|

实现顺序严格为 P0-1/2 → P0-3 → P0-4/5 → 全回归 → Audio → Video → 新RP/fit → P1-1/2 → P1-3。不是修一个局部后把下游已知 stale 继续往前推进。

兼容方案：空 phrase spans、空 execution fingerprint 不进入旧 hash；旧 rendering/reconciliation policy 保留用于历史重放，当前 coordinated runner 明确选新路径。旧 artifact 只保留，不批量改写、不在通用 Media lifecycle 新增状态。

## Audio Acting 与 Voice 决策

旧 Voice Master 已被用户直接判为旁白/播音。7.5 的 candidate1 被用户选择，随后 new Turn A Take 再次被用户判旁白；这足以证明 Take FAIL，不能仅凭这次 Take 断言 candidate1 Master 身份也失败。本批隔离证据显示 Audio Projection 存在确定的信息损失，因此先修 owner=AUDIO_PROJECTION/FISH_RENDERING，Voice Identity 保留 NEEDS_REVIEW。Visual Interaction 可能放大旁白感，单独由新视频观察处理，不能让 Voice Design 承担全部原因。

正文完全保持“请给我三十骑，取杨国忠首级，为大帅除患。”。三个 canonical offsets 的逐短语行动：

|range（end exclusive）|原文|本次 acting progression|
|---|---|---|
|[0,6)|请给我三十骑|向眼前对方提出具体兵力请求，私下直接询求|
|[7,13)|取杨国忠首级|把拟议行动说具体，连接前句，不转为对观众宣讲|
|[14,19)|为大帅除患|把收益交给对方，句尾留给上级作决定|

这不是新增 phrase ontology：nested span 仅3字段，正文仍在 SpokenContent，逗号/句号未变。没有“more emotional”等模糊指令，没有音频拼段或加速。真实 Fish payload 的 header 和三个 inline cues 见 `turn-a-projection.json`；逐短语自由表达只能标 APPROXIMATED，provider 是否演到位是未知艺术结果。一次TTS通过现有 intelligibility/proper-name gate并无明显削波，**TURN_A_NARRATOR_BIAS=UNKNOWN**，不得写 IMPROVED。

## 新视频与参与观察

Comfy `api_bfl_flux3_i2v`，job `70eea227-b0a3-409e-887c-aeceeedad05f`，seed75051，单正式参考图，目标11秒、720p、generate_audio=false。实际1280×704、24fps、265帧。角色卡/脸/服饰未重做，Comfy reference数=1，prompt1873字符。

本次主要可见事实：左黑帽人物前段有持续嘴/下颌变化并面向右侧；右灰须人物同段保持面向左侧、手在桌面附近；中段左侧口部变化减弱，右侧随后有更多下颌、头和上身变化；后段左侧维持视线、减少嘴部活动；两人全程坐着，没有拍桌、起身、夸张挥手或转向无关目标。具体2fps全图与4fps中段见 contact sheets。

原生口部活动仍与音频窗口不精确一致，尤其右侧明显口部变化较晚；双人交接可读性只标 QUESTIONABLE。production participation envelopes A250–5500、B5500–10500 是从画面注意方向、姿态和交流活动作的范围解释，不是 speech-onset 观测值，也不是把嘴型窗口直接写成 startMs。不存在必须修 Script 的物理证据；没有看到明确无关行动冲突，故本批按授权继续 E2E。未消耗一次艺术视频纠偏额度。

Monolithic保留用于当前单Shot，原因是已有稳定身份、场景和单连续镜头；本次以actual执行窗口、target fit和失败门约束其漂移。没有宣称prompt能可靠精确调度。若用户仍拒绝视觉交流关系，则对应修 VISUAL_PROJECTION/VIDEO_REALIZATION；不能把完整I2V改成无证据多段无限重试。本批视频没有切成多个生成段，分段只用于同一源视频的嘴型操作。

## Lip Sync 实际路径与 QC

免费回读 saved workflows、catalog、template/node schema；不是发现一个目录名字就宣称可生产。实际 `SyncLipSyncNode` 支持 `model.speaker_selection=coordinates`，以 `model.speaker_frame/x/y` 选择一张脸；`sync_mode=silence` 明确表示短轨补齐，长轨不裁切。当前双人、侧脸、灰胡须的实际安全性用输出检验。

工具 upload_file 不支持MP4。已继续检查替代路径：`use_previous_output` 将本次云视频置为可复用输入；LoadVideo → GetVideoComponents → ImageFromBatch → CreateVideo(24fps) → selected-face Sync3。两个自组图均做 dry_run；随后一个 submit_batch 提交两项，不重做Video。

|operation|输入 source 帧|选脸|音频放置|job|
|---|---|---|---|---|
|A|[0,133)，133帧|frame0，x447/y190，左黑帽|原A PCM从sample12000开始；前后只补静音|`db156437-654d-4cad-8b35-20b3ed69d0ec`|
|B|[133,265)，132帧|frame0，x895/y190，右灰须|原B PCM从sample680开始；前后只补静音|`ce7b8649-1cb0-4931-a6b1-5c55d2ea9099`|

切点为5541.667ms，处于两句之间。原窗口 A500–4770、B5570–9677 不变；B的680个24kHz样本即28.333ms片段内偏移。包含每段静音hold使目标人物在其非讲话间隙也能收口，整句样本逐字节保留。原始Audio hash不变；provider返回的AAC音轨不用于Final，Final重新使用原始A/B。

输出A133帧、B132帧，均24fps，重合成265帧。左右脸分别改变，非目标者样本未出现连续说话口部模式。已检查 eyes、beard、skin、costume、background、camera、wrong-speaker mouth、拼接前后4帧。未见重大身份破坏或接点空间跳变。`lip-a-contact.png`、`lip-b-contact.png`、`lip-full-contact.png`、`lip-join-contact.png` 与 `source-join-contact.png` 为证据。

QC PASS 的范围是实际输出技术安全及这些样本未见重大问题，不是逐帧无瑕疵或逐音素听觉吻合认证。`lipSyncQuality=QUESTIONABLE`、`phonemeAccuracy=NOT_AUDITORILY_VERIFIED`、USER_FINAL_ARTISTIC_ACCEPTANCE=PENDING。新 post-lip Shot/A/B RP 已绑定 derivative hash；旧 source RP 未假装自动 current。无额外嘴型纠偏操作。

## Final AV、持久化与技术验证

使用 accepted/reconciled execution windows 中本批明确授权的 production anchor，**没有把它写成 USER_REVIEW**。每句 AVSyncPlan 为 MOUTH_ONLY_DERIVATIVE，Audio actual whole duration 与 window相等。AcousticMixPlan A/B：close conversational、gain0、无空间处理、AMBIENCE=NOT_AVAILABLE、SFX=NOT_AVAILABLE、MUSIC=NONE。

Final lineage包括：SpokenContent A/B引用及请求正文、Voice身份与master哈希（Audio provenance）、production DPD、Plan、execution material、new VisualBrief、VideoRequest/hash、source RP、new reconciliation、explicit anchor、Audio A/B hashes、lip operation与云job、lip derivative、post-lip RP、完整2-clip manifest、AVSync/Mix、ffmpeg版本/settings及assembly fingerprint。

新Video、嘴型Video与Final均经 Plugin Media → Drama Service → Cloud MinIO，get/resolve/download核对SHA-256。sourceVideo第一次import响应超时后先按唯一sourceRef查询，恢复既有持久化结果，没有重复生成。Final首次本地调用错误地传字符串MediaType，修为正式枚举后复用既有lip结果完成导入；没有为本地bug重跑Provider。

|QC|结果|
|---|---|
|playable / video+audio stream|PASS；ffmpeg完整decode|
|Video frames/duration|265/24=11041.667ms；Domain round11042；未time stretch|
|A/B coverage|COMPLETE；A一次、B一次|
|placement|500–4770 / 5570–9677ms；严格对应当前reconciliation|
|whole PCM / no trim / no duplicate / no overlap|PASS；合成buffer slice逐字节相等；记录raw PCM hash|
|no clipping|PASS；原始混音及解码AAC峰值均低于int16上限|
|video stream copy at mux|PASS；源lip Video与Final视频packet hash相同|
|identity / wrong speaker / lip artifacts|抽帧技术QC PASS；艺术细节待用户|
|Cloud final download|PASS；`db1803a9611a9beac8d8fecc513975ea9adf101faaff1c9ef8866f2a52088928`|
|Frozen Domain / old Media preservation|PASS；`final-fixture-replay.json`|

## Tests、范围与复杂度

付费前：Plugin **397 passed**（包含7.3/7.4/7.5全部回归及新增协调测试），strict mypy **60 source files PASS**；MCP **26 passed**、strict mypy **4 files PASS**。`tests.json` 绑定 src hash `4c0db40993d7f4a65d4df3f9f36d7f073b61a09ea983f0cb78a44ffed66ac794`。付费后最终fixture replay再次证明当前src与此hash一致；没有隐含未测试src改动。

新增测试覆盖：actual→visual、phase order / active-listener、plan immutable、brief/rendered prompt regression、Video request fingerprint、Video/RP/Audio/review改变导致fit/reconciliation stale、physical fit不盖visible conflict、speaker RP mismatch、非法/越界span、exact lexical preservation、conditioner preserve、explicit face、wrong-speaker-mouth/identity/beard negative、Audio与duration不能被lip改变、共享纠偏预算。最终真实fixture replay额外校验typed FinalAvFingerprintInput/AVSync/AcousticMixPlan、A/B完整各一次、用户review未伪造、云hash与冻结Domain。

实际改动清单见 `change-radius.json`，按本轮开始前hash比较，未把之前工作区未提交改动冒算本批。Core独立contract新增 **0**；已有contract顶层可选字段 **3**（phraseDeliverySpans、executionTimingFingerprint、observedSpeakerKey）；一个nested span helper model的字段 **3**；纯Core helper **2**。另外2个小lip adapter校验函数、2个fixture执行脚本、既有policy新增枚举值，不是独立服务/实体/平台。

**未修改**：Work/Script/Scene/Shot/SpokenContent正文、DPD Core与正式DPD、Character identity/角色资产、Voice Master/Casting/Work binding、B Audio、Java、DB、MCP contract与tools。旧7.2 Final、旧7.3C Video、旧7.5 Video和7.4C preview保留。本批无 Scene/Episode扩展。

## Provider 成本与终止

|类别|本批实际|
|---|---|
|Fish Voice Design|0|
|Fish Create Model|0|
|Fish TTS|1（A）|
|Fish ASR QC|1；单列，不假装所有Fish请求只有TTS一个|
|B TTS / post-video corrective TTS|0 / 0|
|Comfy Video generation|1|
|Lip Sync|2（A/B selected-face）|
|Artistic visual corrective loop|0|
|Lip corrective|0|
|safe transient retries|未观察到Provider retry；最大配置≤2；Media导入恢复不计生成调用|

免费catalog/schema/dry-run/upload/output-reuse/poll不计付费生成数。调用账本在 `provider-counts.json` 与各submission journal。V0完成，未消耗V1；没有为了用完预算重复生成。

Convergence policy 已明确：先productionAudio→实际执行窗口→V0→新RP/targetfit；只有可定位的持续不适配证据才允许一次V1，unknown提交先恢复。不能机械“每个新Video再TTS”；若经证明需post-video修某句，先检查actual delta对slack/reaction/post hold/参与范围，必要时使用同一V1额度，之后冻结Audio，不允许V2无限回圈。本次无需纠偏。

## Review Package 与最终状态

|文件|用途|
|---|---|
|[01-turn-a-final.wav](/Users/zy/historical-plugin/artifacts/batch7-5r-fix/review/01-turn-a-final.wav)|当前A，旁白感UNKNOWN|
|[02-turn-b-final.wav](/Users/zy/historical-plugin/artifacts/batch7-5r-fix/review/02-turn-b-final.wav)|冻结B|
|[03-dialogue-performance-video.mp4](/Users/zy/historical-plugin/artifacts/batch7-5r-fix/review/03-dialogue-performance-video.mp4)|新无声表演源|
|[04-no-lip-preview.mp4](/Users/zy/historical-plugin/artifacts/batch7-5r-fix/review/04-no-lip-preview.mp4)|完整对白无嘴型预览|
|[05-lip-sync-preview.mp4](/Users/zy/historical-plugin/artifacts/batch7-5r-fix/review/05-lip-sync-preview.mp4)|嘴型审核|
|[06-final-av.mp4](/Users/zy/historical-plugin/artifacts/batch7-5r-fix/review/06-final-av.mp4)|最终完整Review，Cloud持久化|

```text
LAYERED_AUDIT = PASS
COORDINATED_P0_FIX = PASS
ACTUAL_AUDIO_VISUAL_EXECUTION_LINK = PASS
AUDIO_ACTION_PROPAGATION = PASS (provider rendition APPROXIMATED)
VISUAL_DIALOGUE_PROPAGATION = PASS
MULTI_SPEAKER_RP = PASS
RECONCILIATION = PASS
LIP_SYNC = PASS (technical execution + sampled safety)
FINAL_AV = PASS
CLOUD_PERSISTENCE = PASS
REGRESSION = PASS
TURN_A_NARRATOR_BIAS = UNKNOWN
AUDIO_CHARACTER_FIT = QUESTIONABLE
VISUAL_DIALOGUE_FIT = QUESTIONABLE
LIP_SYNC_QUALITY = QUESTIONABLE
OVERALL_ARTISTIC_RESULT = PENDING_USER_REVIEW
V1_PIPELINE = READY_FOR_USER_REVIEW
```

最终需要用户判断人物是否像在互相交流、声音是否仍旁白、交接与节奏是否自然、口型和胡须是否可接受。用户如果拒绝，按具体反馈与当前hash定位Voice/AudioProjection/VisualProjection/VideoRealization/Timing/Lip owner；技术PASS不能抵消艺术FAIL。本批已输出最终完整review package，停止，不继续自动修下一轮。

## V2 Backlog — Cinematic Screenplay Incubation（DEFERRED，未实施）

范围限定1–2页内：V1单Shot审核完成后，才讨论电影化剧本孵化。V2关注场景的戏剧行动、信息释放、潜台词、角色关系推进与可拍性，让Script/DPD在进入昂贵生产前达到可审核质量。

建议未来输入：canonical Work/Script、历史依据、人物关系、场景目标与冲突、已获用户反馈的V1声画样例。输出应为人工可审的场景/对白/行动方案与最小镜头候选，先审表达，再进入既有production链。不要以自动重生成当作剧本孵化。

候选验收维度：每句是否对具体人物实施行动；句间是否形成行动推进；信息是否由冲突和选择展现；是否存在可见反应；场景是否有进入/转折/结束状态。它们是创作审核维度，不是新DPD ontology，也不为当前两位角色硬编码规则。

继续推迟：Scene/Episode timeline、多Shot调度、Sound Design、Ambience/SFX/Music、Temporal Graph、Timeline DB、Performance Orchestrator、大型多模态平台、新Java服务或DB实体。没有当前单Shot证据要求这些架构。V2仅记录方向；本批不实施、不调用Provider、不自动创建下一任务。
