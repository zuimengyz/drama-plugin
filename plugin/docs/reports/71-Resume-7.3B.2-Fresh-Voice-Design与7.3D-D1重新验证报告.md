# 71 — Resume 7.3B.2 Fresh Voice Design 与 7.3D D1 重新验证报告

## 1. 执行摘要

Phase A 使用冻结的 CreativeVoiceProfile / CreativeVoiceCastingProfile 和新的 `CHARACTER_DIALOGUE` Preview，向 Fish Voice Design 提交一次请求并返回三条候选。三条均通过 WAV、解码、时长、ASR 完整性、重复/增漏字、clipping/corruption 技术检查；系统保留低置信声学代理排序，没有自动批准任何候选。随后用户明确批准 N0，Phase B 从原 recovery 精确恢复 N0，创建独立新 Voice、完成一次 Fish materialization、原子替换 Work binding，并只重跑一次 D1。

```text
PHASE_A = PASS
PHASE_B_ENGINEERING = PASS
USER_NEW_D1_ARTISTIC_REVIEW = PENDING
```

Phase A 付费与变更计数：

```text
Voice Design primary submissions = 1
Voice Design candidates = 3
safe retry = 0
Voice import = 0
Create Model = 0
Work Voice binding changes = 0
production TTS = 0
D1 rerun = 0
B0 = 0
Comfy = 0
```

第一次本地启动尝试在 Python import 前失败；第二次预检在未启动的 Drama Service 上以 `get_work HTTP 502` 失败。两者都发生在 Fish provider 调用之前，均不计提交。恢复既有 Drama Service 后，Storage Preflight 和唯一一次 Voice Design 成功；未盲目重提。

## 2. 用户旁白偏置确认

用户已经明确判定当前长期 Voice 存在旁白 / 解说倾向，当前 D1 虽技术正确但仍明显呆板，Video Conditioning 的艺术增益有限。因此满足 68 号任务的 Conditional Fresh Voice Design 前置条件：

```text
CURRENT_VOICE_ARTISTIC_ACCEPTANCE = FAIL
CURRENT_VOICE_NARRATOR_BIAS = CONFIRMED_BY_USER
FRESH_VOICE_DESIGN = YES
```

Fresh Voice Design 的目的不是否定 7.3A、7.3C 或 7.3D 架构，而是隔离并修复稳定 Voice Identity 这一主要变量。

## 3. 为什么启动 Fresh Voice Design

旧 Preview `此事若行，我便是反臣。不可。` 只有约 3–4 秒，形式正式、判断性强、句尾高 finality，天然容易把稳定声线推向宣告、旁白或播音。它继续是正式 D1 的 canonical SpokenContent，但不再承担 Voice Identity Preview 职责。

新的 Preview 测试的是“历史剧情人物能否与另一个人自然交流”的稳定声线，而不是当前拒绝场景、当前 DPD 或当前视频表演。

## 4. Frozen Architecture

以下均未修改或重跑：

- DPD 与 `dpdFingerprint = 2d826a70c27da23aded5eda30082931b5c122115dd932ce104b3fb590ec90e1b`；
- Video `media_ac9d14c5cdc74c43ba44562752cf9489` 及其 SHA-256；
- RealizedPerformanceSnapshot 与 `a2d3d311576d75a305e6453089176ac89b0d8cfd9c3acd2a141ee24a13cefd12`；
- canonical SpokenContent `spoken-s1-geshuhan-refusal` 及正式文本；
- 7.3D Audio Projection / Video Conditioning；
- Voice Domain、recovery、Media 与 Cloud storage 架构；
- Java production contracts。

Storage Preflight 沿既有所有权路径执行：

```text
Plugin provider → Drama Service → Cloud object → download → SHA-256
```

旧 Voice master、旧 D1、固定 Video 三份 durable object 的下载哈希分别与 Domain 中冻结哈希一致，结果 `PASS`。Plugin 没有直连 MinIO。

## 5. Old Voice Baseline

```text
voiceId = voice_3b83cfdee0fd4d1a9b4728b0ef1714d7
version = 2
master SHA-256 = 62c41957aeeeaf27b5da897731863a138b76b3f213ab2dbb3fcb780224cf3787
status = preserved
```

调用前后 Work version 都是 4，`speaker:geshuhan` 仍绑定旧 Voice。Domain 查询确认没有任何带本次 design fingerprint 的新 Voice，旧 Voice 仍存在且内容未改变。

旧 D1 同样保持：

```text
mediaId = media_9b8b1bb59996489c89af39f451be698f
SHA-256 = 27bb959353d81ff340db6911fe190097192f647be21fc2da1cddf3f9d65c8793
duration = 3457 ms
```

## 6. Stable Creative Voice Profile

继续复用已有冻结证据，没有根据当前 Scene、DPD 或用户偏好重新发明人物人格。稳定要求包括：late-middle-adult vocal age、medium-heavy weight、natural low-middle register、deep unforced resonance、slightly dark brightness、dry light age texture、low-medium roughness、low breathiness、firm articulation、deliberate phrase attack、moderate-deliberate baseline pace、责任重量与不依赖响度的 controlled power。

声龄仍按 texture、resonance、breath support、articulation 和 phrase shape 的组合表达，禁止简单“压低音高 = 年长”。当前疾病、愤怒、拒绝、威胁等场景状态不进入稳定 Voice Identity。

## 7. New CHARACTER_DIALOGUE Preview

```text
先坐下。方才外面是什么情形，你慢慢说。
别只说结论，我要听你亲眼看见的。
若还有什么没讲清楚，现在一并告诉我。
```

用途严格为 `VOICE_IDENTITY_PREVIEW_ONLY`。它没有写入 Script、Scene Dialogue 或 SpokenContent，也没有读取当前 DPD、Video 或 Realized Performance。文本不含角色实名，`voiceUseCase = CHARACTER_DIALOGUE`，生成时长目标约 10–15 秒。

## 8. Voice Design Instruction

实际 compiler 输出强调：原创、lived-in 的历史剧情人物基础声线，用于人与人直接互动；自然、克制、可长期复用；明确排除 documentary、audiobook、broadcast、announcer、presenter narration；同时禁止从“去旁白”滑向夸张舞台腔、持续压嗓或当前场景情绪。

完整请求见 [`voice-design-request.json`](../../../../artifacts/batch7-3b-2-fresh/review/voice-design-request.json)。

```text
designRequestFingerprint = 87ad528aef4cc7922f7e7d09346ee6525ef32abe4fab10b3483a90b2b09b9752
reviewArtifactId = voice-design-review:87ad528aef4cc7922f7e7d09346ee6525ef32abe4fab10b3483a90b2b09b9752
candidateCount = 3
```

## 9. Candidates

| 候选 | Review 文件 | SHA-256 | 时长 | 技术状态 | MASTER_DURATION_RISK |
|---|---|---|---:|---|---|
| N0 | `N0-candidate.wav` | `59fb527e80eb7a3564caeaed8da68b62226922fd77902967e8e7996842fbd7ad` | 13.328 s | PASS | NO |
| N1 | `N1-candidate.wav` | `7da345dbc22bbfb783b4157bc039b224beae69f2abcdc81ef5a2be94884170e9` | 14.211 s | PASS | NO |
| N2 | `N2-candidate.wav` | `a1446d926850d93398eb817eb081160724a7f62840fb197bb2c8010b82a58dd1` | 12.539 s | PASS | NO |

三条 review 文件与 `voice-design-recovery-v1` 中原始候选逐字节 hash 一致，没有重编码或归一化。

## 10. Technical QC

三条候选均为 WAV PCM signed 16-bit little-endian、44.1 kHz、mono，可由 ffprobe 解码。Fish ASR 对三条均得到 `CER = 0.0`，且 `missing = []`、`extra = []`、`repetition = []`；signal 检查均为 `obviousClipping = false`，没有发现 corruption。三条均超过约 10 秒，不触发 master duration risk。

技术 QC 只说明候选完整、可用、可审计，不说明艺术上已经解决旁白感。

## 11. AI Ranking

```text
AI_RECOMMENDED = N0
confidence = LOW_ACOUSTIC_PROXY
AI_RECOMMENDED != USER_APPROVED
```

排序为 N0、N1、N2。N0 的综合稳定声线声学代理匹配最高；N1 在年龄/亮度代理上较好但重量和深共鸣代理更轻；N2 的重量/深共鸣代理最强但受控力量代理最低。所有维度都只是低置信信号统计，未建立 narratorScore、actorScore 或任何伪定量“艺术正确率”。

## 12. Human Approval Gate

系统按设计返回 `VOICE_ARTISTIC_REVIEW_REQUIRED`。批准前的只读 gate audit 结果：

```text
fresh design imported Voice IDs = []
Production Voice Changed = NO
old Voice present = YES
Voice import calls = 0
Create Model calls = 0
production TTS calls = 0
D1 calls = 0
```

只有用户明确回复 `APPROVE N0`、`APPROVE N1` 或 `APPROVE N2`，Phase B 才能从现有 recovery 精确恢复对应 index/hash。AI 不能代替用户批准。

## 13. Review Package

目录：`/Users/zy/historical-plugin/artifacts/batch7-3b-2-fresh/review/`

- [`N0-candidate.wav`](../../../../artifacts/batch7-3b-2-fresh/review/N0-candidate.wav)
- [`N1-candidate.wav`](../../../../artifacts/batch7-3b-2-fresh/review/N1-candidate.wav)
- [`N2-candidate.wav`](../../../../artifacts/batch7-3b-2-fresh/review/N2-candidate.wav)
- [`candidate-comparison.md`](../../../../artifacts/batch7-3b-2-fresh/review/candidate-comparison.md)
- [`voice-design-request.json`](../../../../artifacts/batch7-3b-2-fresh/review/voice-design-request.json)

听审重点：旁白 / 解说感是否下降；是否像人物在与另一个人说话；年龄和人物重量是否自然；是否过度压低、故意装老或形成配音腔；是否滑向舞台式夸张；是否具有长期角色辨识度。

Phase A focused regression：Voice Design compiler、`CHARACTER_DIALOGUE` use case、三候选 payload、review gate 与 hash-mismatch fail-closed，共 `5 passed, 31 deselected`。Live ASR / signal QC 另行对三条真实候选全部通过。

## 14. Resume Requirement

Phase A 当时必须停止，并已实际等待用户明确批准：

```text
PHASE_A = PASS
PHASE_B = WAITING_USER_APPROVAL（历史 checkpoint，现已由 USER APPROVED N0 解除）
```

收到明确 `APPROVE Nx` 后，只能从 `voice-design-recovery-v1` 恢复 exact candidate，并同时验证：

```text
designRequestFingerprint
candidateIndex
candidateHash
reviewArtifactId
approvalSource = USER
```

任一不一致即 fail closed，不得重新 Design。通过后才允许创建新 Voice、冻结 approved master、对新 Master 执行一次 Fish materialization，并在全部 READY 后原子更新 Work binding；旧 Voice 与旧 D1 均不得删除。随后只重跑 D1：B0、Video、DPD、RealizedPerformance、SpokenContent 与 Audio Projection 逻辑保持不变，唯一主要变量为 Voice Identity。

关键边界答案：旧 Voice 可重设计是因为用户已确认 narrator bias；旧 Preview 不再用于设计是因为它过短、正式且高 finality；新 Preview 只测 Stable Character Dialogue Voice Identity，不进入正式剧本，也不由当前 DPD 驱动；Create Model 和 Work binding 只能在用户批准及新 mapping READY 后发生；旧 Voice/旧 D1 均不删除；Phase B 不重生 Video 或 B0；新 Voice 切换后旧 D1 应变为 stale，但继续作为 D1-OLD；只有用户最终认可正式 Voice 与 D1-New 的艺术门槛后，才可另行决定是否进入 7.3E。

## 15. User Approved Candidate

用户在 Phase A 硬停止后明确回复 `APPROVAL N0`，规范化为 `APPROVE N0`。批准证据：

```text
USER_APPROVED = N0
designRequestFingerprint = 87ad528aef4cc7922f7e7d09346ee6525ef32abe4fab10b3483a90b2b09b9752
candidateIndex = 0
candidateHash = 59fb527e80eb7a3564caeaed8da68b62226922fd77902967e8e7996842fbd7ad
reviewArtifactId = voice-design-review:87ad528aef4cc7922f7e7d09346ee6525ef32abe4fab10b3483a90b2b09b9752
approvalSource = USER
```

没有把 AI rank 解释为用户批准，也没有接受模糊的“自动推荐”。

## 16. Exact Candidate Recovery

从既有 `voice-design-recovery-v1` 读取 N0，逐项校验 schema、design fingerprint、reviewArtifactId、Preview 文本、candidate index 与 candidate hash。Recovery 文件、Phase A Review N0 与 approved master 的 SHA-256 全部为同一个值。Phase B 显式禁止 `design_voice`；实际 Voice Design calls = 0。

若任一标识不一致，脚本会 fail closed；没有 reroll 或重新 Design。

## 17. Voice Master Freeze

批准后的 master 保持 N0 原始 WAV bytes，没有重编码、归一化或艺术转换：

```text
NEW_MASTER_HASH = 59fb527e80eb7a3564caeaed8da68b62226922fd77902967e8e7996842fbd7ad
Drama Service download hash = same
approved candidate hash = same
```

Review 文件：[`new-voice-master.wav`](../../../../artifacts/batch7-3b-2-fresh-d1/review/new-voice-master.wav)。

## 18. New Voice Entity

创建了独立的新 Voice identity：

```text
newVoiceId = voice_c59996a23d9046eb8df51cccfb4a0649
version = 2
masterHash = 59fb527e80eb7a3564caeaed8da68b62226922fd77902967e8e7996842fbd7ad
source = USER APPROVED N0 recovery
```

没有覆盖旧 Voice master，也没有复用旧 Voice 的 provider mapping。

## 19. Fish Materialization

仅对新 Voice/new approved master 执行一次 Fish Create Model，model 继续为 `s2-pro`；safe retry = 0。新 mapping 可由 Fish 查询解析，material fingerprint 为：

```text
58326fc10905772ec7055e66c3e058ce7e32a0407befd976eabf1ecf88543668
```

该 fingerprint 覆盖新 Voice ID、新 master hash、provider 与 model。Create Model primary calls = 1，没有切换模型或 TTS provider。

## 20. Work Binding Transition

Work 原绑定仍是旧 Voice、version 4 时才执行更新；新 Voice master 下载 hash 与 mapping material fingerprint 已全部验证 READY。随后通过 `expectedVersion=4` 的单次 Domain 操作原子更新：

```text
Work version: 4 → 5
speaker:geshuhan:
voice_3b83cfdee0fd4d1a9b4728b0ef1714d7
→ voice_c59996a23d9046eb8df51cccfb4a0649
```

不存在先解绑旧 Voice 再等待 materialization 的空窗。失败路径保持旧 binding。

## 21. Old Voice Preservation

绑定切换后重新读取旧 Voice，其 version、master hash、status 与完整 contract 均未变化：

```text
OLD_VOICE_PRESERVED = PASS
delete = 0
retire = 0
master mutation = 0
```

旧 Voice 继续提供历史审计与 rollback 能力。

## 22. 7.3D Frozen Inputs

D1-NEW 与 D1-OLD 的固定输入对账通过：

| 输入 | 固定值 |
|---|---|
| DPD | `2d826a70c27da23aded5eda30082931b5c122115dd932ce104b3fb590ec90e1b` |
| RP | `a2d3d311576d75a305e6453089176ac89b0d8cfd9c3acd2a141ee24a13cefd12` |
| Video | `media_ac9d14c5cdc74c43ba44562752cf9489` / `066b281d…f677f` |
| SpokenContent | `spoken-s1-geshuhan-refusal` |
| exact text | `此事若行，我便是反臣。不可。` |
| Fish | `s2-pro` |
| timing | `NATURAL`，无目标时长/强制 rate |
| compiler | `BRIEF_CUES_V1` |
| speed / volume | `0.92 / 0.0` |

Script/Episode/Scene/Shot hierarchy也重新对账。DPD、Video、RP、SpokenContent、Shot 与 Audio ontology 修改均为 0；唯一主要变量是 Voice Identity/material。

## 23. Old D1 Freshness

旧 D1 `media_9b8b1bb59996489c89af39f451be698f` 保留，但在当前 Work 上已 stale：

```text
OLD_D1_FRESH = NO
```

原因是 Work 当前 Voice 改变、新 master/material fingerprint 改变、audio-input fingerprint 改变。旧 Media 没有删除或覆盖，仍作为 D1-OLD 艺术对照。

相关 fingerprint 变化：

| 指纹 | D1-OLD | D1-NEW |
|---|---|---|
| Base Audio Projection | `c422b79d…a8ea4de` | `a39b9b83…e220ab2` |
| Final Audio Projection | `66feac9f…5318310f` | `0f73577c…4774a59` |
| Audio input | `9e4f07fa…266543f` | `0bbb6398…2cd67a4` |
| Fish request | `5a881d45…69c31aa` | `a3fd1774…2c63d99` |

## 24. New D1 Generation

只执行一次新 D1 Fish TTS，safe retry = 0，没有第二 take：

```text
newD1MediaId = media_6f4d16d785b84b52b3062e0666a826b5
SHA-256 = 4db91e1299cb3083db55290e5e23ef8595e012e5a7b3fe185ba80a44121e7a9c
duration = 4107 ms
B0 calls = 0
D1 calls = 1
Comfy calls = 0
Voice Design calls = 0
Create Model during D1 = 0
```

Role Dubbing 返回的 Voice ID 必须是新 Voice，且 lifecycle 不允许再次 materialize。

## 25. New D1 QC

真实技术 QC：

| 项目 | D1-NEW |
|---|---|
| format | WAV PCM s16le，24 kHz，mono |
| duration | 4107 ms |
| speech active | 3860 ms |
| leading / trailing silence | 124 / 123 ms |
| RMS / peak | -22.523 / -3.620 dBFS |
| decodePlayable | true |
| obviousClipping | false |
| ASR CER | 0 |
| missing / extra / repetition | 均无 |
| content hash | local = Media = Cloud download |

`TECHNICAL_QC = PASS`。同厂商 ASR 与信号统计不能替代用户对旁白感、人物化和表演自然度的听审。

## 26. Cloud MinIO Persistence

新 Voice master 和新 D1 都只通过既有所有权路径持久化与解析：

```text
Plugin provider → Drama Service → Cloud MinIO
```

新 Voice 通过 `voice.get/resolve/download`，新 D1 通过 `media.get/resolve/download`；下载 SHA-256 分别等于 approved master hash 与 Media.contentHash。没有 temporary URL 持久化，没有 Plugin direct MinIO access，也没有 source service env 到 Host。

```text
NEW_VOICE_PERSISTENCE = PASS
NEW_D1_MEDIA = PASS
NEW_D1_HASH = PASS
CLOUD_MINIO_PERSISTENCE = PASS
```

## 27. Old D1 vs New D1

听审包：`/Users/zy/historical-plugin/artifacts/batch7-3b-2-fresh-d1/review/`

- [`01-D1-old-voice.wav`](../../../../artifacts/batch7-3b-2-fresh-d1/review/01-D1-old-voice.wav)
- [`02-D1-new-voice.wav`](../../../../artifacts/batch7-3b-2-fresh-d1/review/02-D1-new-voice.wav)
- [`03-fixed-shot-video.mp4`](../../../../artifacts/batch7-3b-2-fresh-d1/review/03-fixed-shot-video.mp4)
- [`new-voice-master.wav`](../../../../artifacts/batch7-3b-2-fresh-d1/review/new-voice-master.wav)
- [`voice-old-vs-new.md`](../../../../artifacts/batch7-3b-2-fresh-d1/review/voice-old-vs-new.md)

D1-NEW 比 D1-OLD 长 650 ms；这只是一次真实生成的测量差异，不能单独证明艺术改善。用户应直接听两条，并结合固定视频判断旁白感、人物互动感、年龄/重量自然度、句内行动感，以及是否出现装老或舞台腔。

## 28. Regression

Phase B 完成后执行完整现有回归：

| 检查 | 结果 |
|---|---|
| Plugin full pytest | 203 passed |
| Plugin strict mypy | 54 source files，PASS |
| MCP pytest | 26 passed |
| MCP strict mypy | 4 source files，PASS |
| Voice / exact approval recovery / hash mismatch fail-closed | PASS，包含在 Plugin suite |
| DPD / Audio Projection / 7.3D video-conditioning | PASS，包含在 Plugin suite |
| Fish adapter / Role Dubbing / Media persistence | PASS，包含在 Plugin suite |
| Live master/D1 Cloud resolve + hash | PASS |
| Java | production contract 未改，不运行 |

额外 Live 断言覆盖：approved master hash、new mapping material fingerprint、原子 binding、旧 Voice preservation、旧 D1 stale、new final fingerprint、DPD/Video/RP/SpokenContent 不变、D1 durable lineage 与三方 hash。

## 29. User D1 Review Boundary

工程系统不能把技术 QC 或单次 Voice replacement 自动解释成：

```text
NARRATOR_BIAS_FIXED
```

当前状态：

```text
USER_NEW_D1_ARTISTIC_REVIEW = PENDING
```

用户需要听 D1-OLD vs D1-NEW，判断新 Voice 是否显著减少旁白/解说感、是否更像对画面中的另一个人说话、是否仍呆板、是否具有长期角色辨识度。即使改善，也不生成 Take 2/3；Performance Take Gate 属于后续独立小批次。

## 30. Final State

```text
APPROVED_CANDIDATE_RECOVERY = PASS
VOICE_MASTER_FREEZE = PASS
NEW_VOICE_PERSISTENCE = PASS
FISH_MATERIALIZATION = PASS
WORK_VOICE_BINDING = PASS
OLD_VOICE_PRESERVED = PASS
OLD_D1_STALE = PASS
NEW_D1_GENERATION = PASS
NEW_D1_MEDIA = PASS
NEW_D1_HASH = PASS
TECHNICAL_QC = PASS
PHASE_A = PASS
PHASE_B_ENGINEERING = PASS
USER_NEW_D1_ARTISTIC_REVIEW = PENDING
7.3E = NOT_STARTED
```

本任务在 D1-OLD vs D1-NEW 听审包处停止。未生成 B0、Video、额外 take、Lip Sync、Viseme、SFX、ambience、music、mix 或 AV mux。
