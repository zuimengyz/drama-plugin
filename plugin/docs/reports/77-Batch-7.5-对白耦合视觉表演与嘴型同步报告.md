# Batch 7.5 — Dialogue-Coupled Visual Performance & Lip Sync

正式编号：第 7.5 期——对话耦合视觉表演与唇形同步。
中文批次：第7.5批——对白耦合视觉表演与口型同步。统一报告，后续 D/E 继续在本报告补充。

## 当前结果与审核入口

**Phase C = REVIEW_REQUIRED；STOP BEFORE LIP SYNC。**

已按用户选择候选1恢复 Phase A，完成新 Voice、新 A Audio、对白感知视觉简报、新 Video、三个新 RP、重新 reconciliation 和完整对白本地预览。

[观看完整对白审核预览](/Users/zy/historical-plugin/artifacts/batch7-5/review/05-dialogue-aware-preview.mp4)

**VISUAL_DIALOGUE_COMPATIBILITY=QUESTIONABLE**。前半段王思礼口部/头部变化较多，哥舒翰主要保持朝向；后半段哥舒翰出现更明显回应动作，王思礼以稳定朝向为主。但是哥舒翰明显的口部、下颌和身体回应约在7750ms以后，晚于本次5198ms音频提案起点。画面并非无关动作，仍不足以判定交接自然；这是本次必须听看审核的疑点。

**ENGINEERING 验证与 USER ARTISTIC ACCEPTANCE 分开。** Phase B/C 工程链路完成；整批 `BATCH_7_5_ENGINEERING=NOT_COMPLETE`，因为 D/E 尚未执行。`USER_ARTISTIC_REVIEW=PENDING`。不能据此宣布历史短剧表演质量 PASS。

## 7.4C 结论及旧素材边界

`BATCH_7_4C_PHASE_A_ENGINEERING=PASS` 保留为技术事实，但 `USER_AV_REVIEW=FAIL`、`TIMING_ACCEPTANCE=BLOCKED`、`VISUAL_DIALOGUE_COORDINATION=FAIL`、`TURN_A_CHARACTER_DIALOGUE_QUALITY=FAIL`、`LIP_SYNC=NOT_IMPLEMENTED`。

7.4C Phase B 已取消，未向 AVSync 写入旧5871ms提案。旧 `04-complete-dialogue-preview.mp4` 只作失败审核证据，未 promote、import 或用作 timing authority。

旧视频 `media_ac9d14c5cdc74c43ba44562752cf9489`，hash `066b281d01ba8f330c66c463c8c6ff0f238cc2f56af7c0dffbbaf812e62f677f` 保留，报告层诊断 **STALE_FOR_DIALOGUE_PERFORMANCE**。它字节有效，但其7.3C单行 DPD VisualPerformanceBrief/Video Request 没有消费完整 DialogueTimingPlan 和 speaker-turn 结构。未修改通用媒体生命周期、删除或覆盖旧视频。

7.4C 把两段音频放进正确时间位置，证明的是合成可行；旧视频没有按完整交流行动制作，因此技术 PASS 不等于对白表演协调。当前没有证据要求修改 Script 或 canonical Dialogue。

## Phase A — 差异审核、用户选声与正式配音

### 声音根因与人工权威

用户先明确反馈“Master 本身也明显偏旁白／播音”。所以 `VOICE_MASTER_NARRATOR_BIAS=PRESENT`，`TURN_A_NARRATOR_BIAS=PRESENT`，`TURN_A_ROOT_CAUSE=VOICE_IDENTITY`。没有将此误当成仅 Audio Projection 问题，也没有直接重试旧声音。

第一次执行只调用一次 Fish Voice Design，n=2，voiceUseCase=CHARACTER_DIALOGUE。试听是王思礼当面请求授权，接冻结哥舒翰回应；不是历史说明、演说或旁白。用户随后明确“选择候选1”，见 `user-voice-choice.json`。

助手运行环境不支持音频听觉输入，根因判断依赖用户实际比较，未拿波形/ASR冒充艺术听感。新 Voice 选择已有 USER 权威；**新正式 Take 的旁白偏差是否显著降低仍待本次完整预览审核**，不提前宣称 FIXED。

### 选中候选的实现

| 项目 | 结果 |
|---|---|
| Selected candidate | 1（provider index 0） |
| Candidate hash / new master hash | `265c94c6c3b019a25fae34ad715ad8f1a33198d71c156397d61ed49cc695ef28` |
| New Voice | `voice_e8731619bea0467db69b197cef1299a1` |
| Old Voice preserved | `voice_06ac45335157432e8322a9b32e8d9804`，未修改 |
| Work binding | 仅王思礼改绑新 Voice，Work version=6 |
| Cloud master resolve/download/hash | PASS |
| 未选候选 | 保留本地证据；未 materialize/import/bind |

只对选中原始字节作 Voice import → Fish model materialization → Work bind。首次 import 在本地允许目录校验时被拒，尚未发送 HTTP；之后将同一哈希字节暂存于既有允许目录成功导入，没有新增候选或重复创建 Voice。所有不确定提交由 journal 阻止盲目重试。

### 正式 DPD 与 Audio Projection

Turn A 使用原正式 production DPD `af9827cf6564228b4c0a9fd8ed6a1ab2cc1813b5ec36ced9015087014ea413e5`。
它明确：王思礼向 `speaker:geshuhan` 请求授权，以有限兵力和明确结果私下进言；有执行能力但无最终批准权；HIGH internal activation + HIGH external control。Voice binding 更新不改变该行动或权力关系，Scene/Shot/SpokenContent 内容已重新核验保持不变。

新 Take 在现有 AudioPerformanceBrief 中表达 interactive character dialogue、近距离对人说话、controlled breath、responsive phrasing、非播音节奏和给听者留下决定的句尾。语速倾向回到 NEUTRAL，NATURAL duration，禁止按5000ms估计拉伸；没有“more emotional”等泛化控制。

Audio authority 为 **DPD_AUDIO_PROJECTION**。旧视频对完整对白表演已陈旧，因此不把旧 RP 或旧 video-conditioned finality 强行加给新音频。没有伪造未来视频的 RP。DPD、exact text、Voice 与 brief fingerprint 均进入真实请求。

Fish adapter 已支持 `BRIEF_CUES_V1`：control/intensity/rhythm/pauseStrategy/sentenceEnding 编成自然语言方括号 cue，同时保留 prosody 参数，未退回只有 speed+volume。官方 S2 支持自然语言与行内表达提示，含 pause/emphasis 等，但并非精确时间执行保证。[Fish Models Overview](https://docs.fish.audio/developer-guide/models-pricing/models-overview)

本次继续使用既有单前缀 cue 控制面；没有新增 Fish 核心合同。更早文档的 `(break)`/`(long-break)` 不直接当作 S2 毫秒控制保证。[Fish Fine-grained Control](https://docs.fish.audio/developer-guide/core-features/fine-grained-control)

### 正式 A Audio

| 项目 | 结果 |
|---|---|
| spokenContentId | `spoken-s1-wangsili-proposal` |
| speaker | `speaker:wangsili` |
| exact text | 请给我三十骑，取杨国忠首级，为大帅除患。 |
| New Audio Media | `media_57635a0ecc6649c48e7126a28908e45a` |
| Audio hash | `3b3b04ba33b87c8656c95a49f654d44f07e523f6f5e03e73c6ab213038c9dbbe` |
| Actual duration | 3898ms |
| Planned duration | 原5000ms，未改写 |
| Technical / intelligibility | PASS；CER=0，missing/extra/repetition/properNounFindings=[] |
| Cloud download hash | PASS |
| Artistic review | PENDING |

[Turn A before](/Users/zy/historical-plugin/artifacts/batch7-5/review/01-turn-a-before.wav) · [Turn A after](/Users/zy/historical-plugin/artifacts/batch7-5/review/02-turn-a-after.wav)

哥舒翰 Turn B `media_6f4d16d785b84b52b3062e0666a826b5`，4107ms，hash `4db91e1299cb3083db55290e5e23ef8595e012e5a7b3fe185ba80a44121e7a9c`，保持 **FROZEN**。没有重配 B、改脚本或重做角色视觉资产。

## Phase B — Dialogue-coupled Visual Production

### 一次窄幅扩展

现有 VisualPerformanceBrief 只能表达一条 DPD 的身体、头、视线、面部与 pre-speech，没有完整有序轮次。新增可选 `dialogueTimingPlanFingerprint`、`dialogueSourceFingerprint`、`dialoguePerformancePhases`；phase 为 brief 内嵌值，不是独立核心合同、服务或存储对象。

每个 phase 只有 order、activeSpeaker、listener、dramaticAction、visiblePerformanceFocus、transitionPurpose、relativeTimingRange。没有复制 exact dialogue text。消费 ordered canonical SpokenContent 以验证 text/identity/fingerprint；独立保留 planning DPD 与 production DPD，后者来自正式 A/B。

旧 brief 没有该扩展时，fingerprint material 排除新增空字段，所以既有7.3指纹保持不变。新 video request fingerprint 包含耦合 brief 指纹，源图、镜头与相位材料变化会改变请求身份。新增回归验证乱序、错误 speaker/listener、缺失/陈旧来源及旧指纹兼容。

### 计划 → 相对视觉阶段

保持原7.4A计划 `dfe0dc594602c215597d462e5e670814e783fddbfc1255e5ee1b2eedb8776083`，没有把3898ms写回计划。

| 相位 | 原计划 | Provider 相对阶段 | Speaker / Listener |
|---|---:|---:|---|
| Opening | 0–500ms | 约0–5% | 建立双方朝向 |
| Turn A | 500–5500ms | 约5–52% | 王思礼主动；哥舒翰听取 |
| Transition | 5500–6300ms | 约52–60% | 王思礼停下；哥舒翰获得反应空间 |
| Turn B | 6300–9500ms | 约60–90% | 哥舒翰回应；王思礼听取 |
| Ending | 9500–10500ms | 约90–100% | 回应结束，保持新状态 |

Provider prompt 明确 LEFT 黑帽王思礼对 RIGHT 灰须哥舒翰说话，听者保持朝向，然后交接、回应与收住。限制大幅手势、怒吼、站起、拍桌。百分比只是生产意图，不要求毫秒精确，也不把头/嘴动作自动等同 speech anchor。

### 稳定身份与真实生成

继续复用正式人物卡：王思礼 `asset_0bfe891941184a66bd9e6f6aee0b622c` / `media_04f98e81cb5a4b9d80779283ab70bfb3`；哥舒翰 `asset_807f5ae3694746ccab81c828ab57e990` / `media_2a0e7a10b8fc4dc5863731c02e5392ef`。没有新建 STANDARD_FACE、服装或场景资产。

实际 Comfy 输入为同一正式源帧 `media_3e48554b57e64b4caabf98e50b4bebab`，hash `9f110af425cb7fe120d4c9c6b37a93d7363f5b09807667afb8cad85b1346da38`。它已承载双方身份、服装、军案/地图和场景，是已接受历史镜头的固定提取帧；原资产、源帧和上游 Media 血统已回读。输入图数=1，未超过固定上限。

| 项目 | 结果 |
|---|---|
| Comfy workflow | `api_bfl_flux3_i2v`，真实 Comfy Cloud |
| Job ID / terminal status | `978d1576-b652-4bb8-bfc1-4572a150c9da` / COMPLETED |
| Target | 11s / 720p / generate_audio=false |
| Visual brief fingerprint | `9e640709909959af8898fdf674c83e8c8cd83e8f0fc945ff72a3bd85474a756a` |
| New request fingerprint | `176d826670c2ec383cc1df41e89c3371739a45ecc76f436074e6c8f47ff0f627` |
| New Video Media | `media_859a7796181a433192e7984e31529e1a` |
| New Video SHA-256 | `99731a95b7d64c7a5448d5c24b8c7e66bd4a46a70cf896819a8c1e3af2176430` |
| Physical | H.264，1280×704，24fps，11042ms，无音轨 |
| Cloud Media get/resolve/download/SHA-256 | PASS |

新 Video 作为既有 purpose=SHOT_VIDEO 经 Plugin → Drama Service → Cloud MinIO 导入，visualContentReview=PASS 指采样结构/身份没有明显失败；userVisualDialogueReview=PENDING。没有覆盖旧 Video 或旧72 Final Shot，也没有将审核预览持久化为 production Media。

## Phase C — 新观察、兼容性、重新对账

### RealizedPerformance 重新观察

由本次新视频以4fps抽44帧，另有2fps全画幅接触表和左右脸部接触表。时间窗口为采样近似，不能建立音素级同步。只记录可见事实，不写“内疚、理解、愤怒”等心理推断。

| 视角 | 新 RP fingerprint |
|---|---|
| Shot-level | `0b62accf9403b21ab5e84aebbc145e3393b8c8946583066b1216c1b08c969a62` |
| Turn A speaker-specific | `0996921049d048f5e179e1d3dc71562650d8c10f19cde620eb0770f704bbebc0` |
| Turn B speaker-specific | `aa2fd3bbbba943c4e2e45e414eb88dcaa617303d0482a7ae6332b182ca121cb8` |

旧 `a2d3d3…` 与旧 A RP 均未用于新视频观察。B 音频本身历史制作来源的旧 RP 只保留在 immutable audio provenance 中，不冒充新视频 RP。

可见事实：双方全程坐于军案两侧，身份/胡须/甲胄/背景保持可识别。A 的早段口部形状和头部有较多变化；约4750–5250ms向下看后恢复对右方朝向。B 前段基本面向 A，后段约7500–8500ms下颌/头部和身体前移更明显，约7750–10000ms有较清楚口部形状变化。没有明显大幅挥手、拍桌、站起或切镜。胡须与侧面角度限制精确嘴型判断；未验证 wrong-speaker lip-sync safety。

[全画幅观察](/Users/zy/historical-plugin/artifacts/batch7-5/evidence/full-labelled.jpg) · [王思礼观察](/Users/zy/historical-plugin/artifacts/batch7-5/evidence/left-labelled.jpg) · [哥舒翰观察](/Users/zy/historical-plugin/artifacts/batch7-5/evidence/right-labelled.jpg)

### 白话视觉兼容性审核

| 检查 | 结果 |
|---|---|
| A phase 主要是王思礼主动交流 | SUPPORTED；早段口/头变化集中于左方 |
| A phase 哥舒翰主要 listener/reactor | SUPPORTED；持续面向左方、无无关动作 |
| Transition 可识别交接/反应 | QUESTIONABLE；A低头/恢复早于更明显的B回应 |
| B phase 主要哥舒翰回应 | QUESTIONABLE；较明显回应集中在该阶段较晚部分 |
| B phase 王思礼主要 listener/reactor | SUPPORTED；后半段更多稳定朝向 |
| 综合 | **QUESTIONABLE**，需要用户完整听看 |

没有证据把本次判为明确 CONFLICTING；也不能把它写成 SUPPORTED/PASS。若用户认为仍不成对话，应按反馈定位 VIDEO_REALIZATION 或相应 VISUAL_PROJECTION/Timing 节点，禁止直接靠 lip-sync 修补上游关系。

### reconciliation 的最小输入兼容修复

旧校验要求每条音频必须 video-conditioned 且绑定目标 Video，与本批“新A先产生、B保持冻结、再生成新Video”的授权顺序冲突。修改仅在 `_expected_audio_lineage`/`_audit_audio`：

- 接受有当前 exact text、DPD、Voice/master/mapping 与真实 Audio lineage 的 DPD_AUDIO_PROJECTION。
- 冻结 B 可显式给出真实 `audio_source_videos_by_spoken_content` 与原 production RP；逐项核对来源 Video hash、身份、Work/Shot 范围。
- 未显式提供源视频时保留原行为，仍要求与目标 Video 一致。
- 新目标 Video 与新 RP 依然必需；视频、RP、A音频或B来源变化会使旧 reconciliation 失效。

没有将 B 的 metadata 改写成新视频，也没有新造 Video-conditioned Audio。Feasibility-first / placement-second 算法、DialogueTimingPlan、Policy、保护反应时间和7.4A planner **未改**。

### 本次提案

| 部分 | 新提案 |
|---|---:|
| Pre | 0–500ms |
| A | 500–4398ms |
| Reaction | 4398–5198ms（800ms） |
| B | 5198–9305ms |
| Post | 9305–11042ms（1737ms） |

Full dialogue coverage=COMPLETE，Full realized feasibility=FEASIBLE；protected minimum=9805ms，slack=1237ms。新 reconciliation fingerprint：`c047741870189fd2496307dcfc9c08fe8d381fb0806a07c55a059131f8535b6e`。旧5871ms未继承。

Reconciliation 合同的 artisticCompatibility=UNKNOWN：聚合 RP 的 mouthActivity=UNKNOWN，而且尚未用户艺术验收。独立、逐阶段、基于观察的对白视觉诊断为 QUESTIONABLE，两者没有互相伪造 authority。相对表演阶段不能保证按计划兑现；本次5198ms的 B音频起点与约7750ms较明显可见回应之间的差异需要用户审核，不能由嘴型修补或自动改变reaction来掩盖。

### 完整对白预览与技术 QC

新 Video + current A + frozen B + 本次未接受 reconciliation → [05-dialogue-aware-preview.mp4](/Users/zy/historical-plugin/artifacts/batch7-5/review/05-dialogue-aware-preview.mp4)。同字节别名：`dialogue-aware-review-preview.mp4`。

本地先构建24000Hz mono PCM，A从sample12000至105552，B从124752至223320，中间19200 samples=800ms。A/B各一次，完整PCM按原样进入混合轨；未 speed、pitch、trim、time-stretch。视频stream copy，源/预览video packet hash相同。

MP4可完整解码，H.264视频 + AAC音频，11042ms；无overlap、truncation、duplicate audio、clipping；混合峰值约-3.620dBFS，AAC解码峰值约-3.655dBFS。无可信环境声资产，AMBIENCE=NOT_AVAILABLE、SFX=NOT_AVAILABLE、MUSIC=NONE。

预览仍无lip-sync、无accepted timing、无Final AV/Final Shot Media import。

## 测试、血统与复杂度

| 检查 | 结果 |
|---|---|
| Dialogue timing → phase projection / ordering / speaker-listener mapping | PASS |
| Canonical text/speaker、缺失与陈旧来源负例 | PASS |
| VisualPerformanceBrief旧指纹与Video Request新指纹 | PASS |
| Video change → RP/reconciliation stale | PASS |
| A Audio hash change → reconciliation stale | PASS |
| Frozen B source hash/Shot mismatch → reject | PASS |
| Dialogue visual diagnostics、wrong-speaker mouth负例 | PASS（诊断单元测试，非已做lip-sync） |
| Identity preservation evidence | 新视频采样证据 SUPPORT；用户艺术判断待审 |
| 新 Final Shot lineage | NOT_RUN；E未开始，已有source血统就绪 |
| 7.3/7.4 regression + Plugin full pytest | **379 passed** |
| Plugin strict mypy | PASS，59 source files |
| MCP regression / strict mypy | **26 passed** / PASS，4 source files |
| 新音频ASR/哈希、新视频云端哈希、完整预览采样QC | PASS |
| git diff --check | PASS |

新核心合同=0；仅一个现有 VisualPerformanceBrief 窄扩展，附带已有 reconciliation 的音频来源兼容。DB=0、Java production changes=0、MCP new tools=0、new services=0。无Performance Orchestrator、Engine、Timeline DB、ActorScheduler或平台层新增。

现有生产证据已串联：SpokenContent A/B、Voice A/B、production DPD A/B、原TimingPlan、新VisualBrief/Video Request、源帧/角色资产、新Video hash、新RP、新reconciliation、A/B hashes。Accepted timing、Lip Sync provenance、Final AV assembly fingerprint尚不存在，未造空文件或伪造血统。

本批累计 Fish **4次操作**：Voice Design=1（2候选）、Create Model=1（仅候选1）、TTS=1（A）、ASR QC=1；瞬态重试=0。Comfy Video primary=1，重试=0。B TTS=0，新Voice Design追加=0。

## 必答问题

| 问题 | 答案 |
|---|---|
| Q1 7.4C技术通过为何用户不接受？ | 只证明摆放/合成；视觉没有按完整轮次制作。 |
| Q2 旧视频消费完整DialogueTimingPlan？ | NO |
| Q3 旧视频适合完整对白最终视觉载体？ | NO |
| Q4 证据要求修改台词？ | NO |
| Q5 A叙述偏差哪层？ | VOICE_IDENTITY，用户确认Master失败；选声1已实施，新take听感仍待审。 |
| Q6 新视觉消费DPD+SpokenContent+Timing？ | YES |
| Q7 要求Comfy毫秒精确？ | NO |
| Q8 必须speaker/listener/reaction结构？ | YES |
| Q9 新视频沿用旧RP？ | NO |
| Q10 新视频需重新reconcile？ | YES，已重跑 |
| Q11 视觉协调前可lip-sync？ | NO |
| Q12 lip-sync能替代表演协调？ | NO |
| Q13 lip-sync可重新决定timing？ | NO |
| Q14 已证明哪层物理冲突？ | NONE；当前实际音频总时长可容纳，不等于艺术协调通过。 |
| Q15 谁判断最终艺术质量？ | USER / PRODUCTION REVIEW |

## Resume Phase D / E

当前强制停止于 Phase C。只有用户明确 **APPROVE 7.5 VISUAL-DIALOGUE PERFORMANCE** 或等价批准，才继续审计 saved workflow/Comfy catalog/Sync3或等价能力。双人、侧脸、胡须、speaker switching须有明确active face选择证据；不能把混合双人音频丢给不识别speaker的整片lip-sync。

Lip Sync只处理接受窗口内嘴部动作，不重新决定start/end/reaction、不修改音频。须检查non-speaker mouth safety、face/beard/identity与时间连续性。当前workflow不能安全执行则 BLOCKED，并明确最小修复方向。lip-sync review尚未发生。

E只有Visual coordination accepted、Timing accepted、Lip Sync accepted或明确waived后才能进入。最终输出必须为新derivative FINAL_AV，完整A/B覆盖，独立cloud hash与Final Shot lineage。当前Timing authority仍为UNACCEPTED_PROPOSAL，Final AV=NOT_STARTED。

## 审核包与待用户判断

统一目录：`/Users/zy/historical-plugin/artifacts/batch7-5/review`。已有01-before、02-after、03-old-video、04-new-video、05-complete-preview及选声历史文件；06/07不存在。旧72 Final Shot、旧7.4C preview、新source Video均保留。

请重点判断：两人是否在进行这场对话、speaker/listener关系、交接是否自然、5198ms接话与可见回应是否协调、王思礼是否仍有明显旁白感。若拒绝，只修反馈指向的VOICE/AUDIO_PROJECTION/VISUAL_PROJECTION/VIDEO_REALIZATION/TIMING节点。

主要证据：`user-voice-choice.json`、`voice-binding-transition.json`、`turn-a-result.json`、`visual-projection-inputs.json`、`visual-performance-brief.json`、`video-request.json`、`comfy-submission.json`、`new-video-media.json`、`video-cloud-hash.json`、`new-rp-*.json`、`visual-dialogue-compatibility.json`、`new-reconciliation-inputs.json`、`new-reconciliation.json`、`complete-preview-qc.json`、`frozen-files-verification.json`，均在 `/Users/zy/historical-plugin/artifacts/batch7-5/evidence`。

**Boundary: STOP BEFORE LIP SYNC。**
