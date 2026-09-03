# 72 — Batch 7.3E 视听同步、声场构建与最终镜头合成报告

> **Resume 状态更新（2026-09-02）**：用户已批准 `dialogueStartMs = 5200`。第 27 节记录完成后的生产结果，并取代第 1–26 节中初始 PARTIAL/REVIEW_REQUIRED 状态；初始内容保留作为审计历史。

## 1. 执行摘要

本批完成 Storage Preflight、当前生产输入恢复、AV/声场能力审计、`AVSyncPlan` 与 `AcousticMixPlan` 最小 Contract、fingerprint/staleness 规则、负向测试和用户 Review Package。

当前固定 Video 与 Fresh Voice Design 后的新 D1 均从 Drama Service resolve/download 成功，下载 SHA-256 与 Media `contentHash` 完全一致；不存在对象缺失，无需 storage reconciliation。

本批没有生成 Final Shot。阻断原因是 Production 缺少可信 Dialogue Timing Authority：当前 Shot 有两名说话者的两句对白，而本批 D1 是第二句；Shot/Production 没有 approved `dialogueStartMs`，7.3C 的 `mouthActivity` 与 `speechWindow` 均为 `UNKNOWN`。依据冻结规则，不能把 D1 猜放到 0ms 或其他时间。结果为：

```text
DIALOGUE_PLACEMENT = REVIEW_REQUIRED
LIP_SYNC = NOT_APPLIED_FOR_LOW_VISIBILITY
MIX = BLOCKED
FINAL_AV_MUX = BLOCKED
BATCH_7_3E = PARTIAL
```

Fish TTS、Comfy Live、新 Audio Provider 调用均为 0；Video、D1、Voice、DPD、SpokenContent 均未修改或覆盖。

## 2. 当前 Frozen Inputs

| Input | 当前事实 |
|---|---|
| Work | `work_9cc5d11969a64f93bce4a544f349c793`, version 5 |
| Scene | `scene_3ad95aa042e647d9a9be05a51dd8a009` |
| Shot | `shot_83db7eb53b2f49d3a58428d4659e584e` |
| Voice | `voice_c59996a23d9046eb8df51cccfb4a0649` |
| Voice master hash | `59fb527e80eb7a3564caeaed8da68b62226922fd77902967e8e7996842fbd7ad` |
| Video | `media_ac9d14c5cdc74c43ba44562752cf9489` |
| Video hash | `066b281d01ba8f330c66c463c8c6ff0f238cc2f56af7c0dffbbaf812e62f677f` |
| D1 | `media_6f4d16d785b84b52b3062e0666a826b5` |
| D1 hash | `4db91e1299cb3083db55290e5e23ef8595e012e5a7b3fe185ba80a44121e7a9c` |
| DPD fingerprint | `2d826a70c27da23aded5eda30082931b5c122115dd932ce104b3fb590ec90e1b` |
| RealizedPerformance fingerprint | `a2d3d311576d75a305e6453089176ac89b0d8cfd9c3acd2a141ee24a13cefd12` |
| SpokenContent | `spoken-s1-geshuhan-refusal` / `此事若行，我便是反臣。不可。` |

当前 Work binding 指向新 Voice，当前 D1 的 Voice/master、DPD、RealizedPerformance、Video、SpokenContent lineage 均指向上述最新输入。旧 Voice 与旧 D1 均保留，本批未做状态或 bytes 变更。

## 3. Storage Preflight

正式 owner path 为：

```text
Plugin / MCP -> Drama Service -> Cloud MinIO
```

Video 与 D1 均执行 `get_media -> resolve_media -> download -> SHA-256`：

| Media | metadata | resolve | download | hash |
|---|---:|---:|---:|---:|
| Video | PASS | PASS | PASS | `066b...677f` = declared hash |
| D1 | PASS | PASS | PASS | `4db9...7a9c` = declared hash |

Plugin 没有读取 MinIO endpoint/credential，没有直接上传 MinIO，也没有将 signed URL 写入 evidence。`CLOUD_STORAGE_HASH = PASS`。

## 4. AV AS-IS Audit

审计结论：

1. 可信 speech timing：**不存在**。
2. 项目内已验证 lip-sync workflow：**不存在**；只有 provider catalog 中可发现的模板。
3. side-face + beard 适用性：provider 文档宣称模型对侧脸和遮挡有能力，但本项目、当前双人胡须 fixture 均未实际验证，不能认定 PASS。
4. 是否只改嘴部：现有目录模板属于生成式 full-shot processing，无法提供当前视频逐像素只改嘴部的生产保证。
5. identity preservation：当前 fixture 无已接受证据。
6. stable ambience/SFX：均不存在。
7. Scene acoustic context：只有 Scene/Shot/实际画面的事实，可确认室内木结构军议空间、近距离双人对话；无正式 acoustic metadata。
8. ffmpeg：可做 delay、gain、fade、已有音轨 mix、video stream copy mux 与 probe；不能推断 dialogueStart，也不能凭空创造可信环境事实。

## 5. Dialogue Timing Authority

本批严格采用：

```text
approved explicit anchor
> reliable observed mouth activity
> verified audio-driven alignment
> explicit user/review anchor
> never agent guess
```

当前逐项结果为 `false / UNKNOWN / unverified / absent`，因此 `timingAuthority = NONE`。Shot 绑定两句 ON_SCREEN_SPEAKER 对白，当前 D1 是哥舒翰的第二句，D1 时长 4107ms；`estimatedDurationMs` 只属于计划长度，不是实际起音锚点。

## 6. mouthActivity UNKNOWN Boundary

`UNKNOWN` 不等于 0ms、不等于从视频开头说、不等于可以按 D1 时长、总视频时长、头动或字数猜起音。

Contract 强制：当 `timingAuthority = NONE` 时，`dialogueStartMs` 与 `dialogueEndMs` 必须同时为 `null`，`alignmentConfidence` 必须为 `UNKNOWN`。任何伪造窗口均 validation fail。

## 7. AVSyncPlan

新增唯一同步 Core artifact：`AVSyncPlan`，字段只包含 frozen Video/D1 identity、Shot/Spoken/Speaker identity、timing authority、可空 placement、lip policy、confidence 与 fingerprint。它不包含 Comfy workflow/model/node，也不包含 DPD objective/subtext。

当前 fingerprint：

```text
48b183bdb460ac304b5c992668bdcb80f5a88d8c3368c8393dd9e92800b21d31
```

当前 placement 保持 `null/null`，这是可信事实，不是缺失实现。

## 8. Lip Sync Capability Audit

项目 saved workflows 以 `lip/talk/audio` 搜索均为 0。Comfy 官方目录存在 `api_sync_so_lip_sync_video`（Sync 3，Video + Audio），但没有项目运行历史或 current-fixture acceptance。

Sync 官方资料称 Sync 3 能处理 profile、遮挡和 active speaker；同时其质量建议仍指出单一清晰人脸最有利，多人需要 speaker selection，胡须和细节是挑战。官方 sync-mode 还说明 `bounce/cut/silence` 只处理输入时长关系，并不为本镜头的第二句提供 Production dialogueStart。[Sync 3 文档](https://sync.so/docs/models/sync-3)、[Lip-sync 模型文档](https://sync.so/docs/models/lipsync)、[质量建议](https://sync.so/docs/compatibility-and-tips/improving-lip-sync-quality)、[Sync mode 指南](https://sync.so/docs/developer-guides/sync-mode)

因此“目录可用”不等于“当前 production verified”。

## 9. Lip Sync Decision

当前角色是明显侧脸，完整灰胡须遮挡嘴部；画面同时存在两人，且只提供第二位说话者 D1。强行跑全长 Video + D1 仍缺少这句在 Shot 内的 placement，且没有嘴部局部修改/全局 identity preservation 的已接受证据。

决定：

```text
LIP_SYNC = NOT_APPLIED_FOR_LOW_VISIBILITY
COMFY_CALLS = 0
```

不重绘 Video，不因 lip-sync 缺失修改 D1，也不以 provider 隐式默认替代 Core timing contract。

## 10. Lip Sync Live Result

未执行 Live Lip Retarget。`primary=0, retry=0, candidate=0`。这是 gate decision，不是 provider/network failure。

## 11. Acoustic Scene Context

Scene 标题为“关门未开”，location 为“潼关关楼与军府”；实际抽帧显示暗色木结构室内军议空间，人物隔桌近距离交谈。可支持 `dialoguePerspective = CLOSE_CONVERSATIONAL`，但不足以证明某一条具体 room tone、军帐外战场声、马声、金鼓或音乐。

## 12. Ambience / SFX Assets

现有 Work Media 未发现可复用且 scope/approval 可信的 ambience、room tone、foley、SFX 或 music。结论：

```text
AMBIENCE = NOT_AVAILABLE
SFX = NOT_AVAILABLE
MUSIC = NONE
NO_UNGROUNDED_AUDIO = PASS
```

没有下载素材、没有生成历史音效包、没有接入新 Audio Provider。

## 13. AcousticMixPlan

新增第二且最后一个 Core artifact：`AcousticMixPlan`。它只拥有 Work/Scene/Shot、D1 binding、dialogue perspective、ambience/SFX bindings、克制的 spatial treatment、相对 gain 与 music policy。

当前 bindings 为空，`spatialTreatment = NONE`，避免在没有最终 placement/review 的情况下擅自改变已批准干声。fingerprint：

```text
1a5fcf8eb6eef3f29b40f312a62e6584c46a91b733adaedef6fec245c90ae165
```

## 14. Dialogue Spatial Treatment

计划层已确认近距离对话 perspective；实际 DSP 未执行。原因是没有可信 ambience/IR，且 placement 尚未批准。没有大混响、echo、广播 LUFS preset 或极端 gain/rate adjustment。

## 15. Mix

`MIX = BLOCKED_BY_DIALOGUE_PLACEMENT`。D1 dry Media 原样保留；没有制造 `FinalFinalAudio` Entity，也没有持久化无用途的临时 mixdown。

## 16. Final AV Mux

`FINAL_AV_MUX = BLOCKED_BY_DIALOGUE_PLACEMENT`。ffmpeg/ffprobe 都是 9.0.1，Host 能力 READY，但技术能力不能替代 timing authority。本批没有偷偷 `startMs=0`，没有输出声画错位的伪 Final Shot。

## 17. Final Shot Media

```text
Final Shot MediaId = NONE
Final Shot contentHash = NONE
Final Shot fingerprint = NONE
```

原 Video 与 D1 durable Media 均保留且不 stale。待 placement 批准后，应生成新的 derivative `FINAL_AV`/现有等价 purpose Media，绝不覆盖源 Video/D1。

## 18. Fingerprint / Staleness

`final_shot_fingerprint()` 已定义并测试，至少组合 Video hash、D1 hash、AVSyncPlan fingerprint、AcousticMixPlan fingerprint、Ambience/SFX hashes 与 assembly schema version；未解决 placement 时函数直接 fail，不能形成“可组装 Final Shot” lineage。

Video、D1、Sync Plan、Mix Plan 或绑定声效 hashes 任一变化都会产生新 Final Shot fingerprint，旧 Final Shot 必须 `STALE / REBUILD`。Final Shot 的产生不会反向改变 Video/D1。

## 19. Cloud MinIO Persistence

源 Video/D1 persistence 与 download hash 均 PASS。由于 Final Mux 被正确阻断，没有 Final Shot bytes，因此没有调用 `media.import_media`，也没有伪造 Media metadata。待真实 Final MP4 存在后，必须继续走 `media.import_media -> Drama Service -> Cloud MinIO -> resolve/download/hash`。

## 20. Technical QC

源输入 QC：

- Video：H.264、1280×704、24fps、11.041667s、仅 video stream；PASS。
- D1：PCM s16le、24kHz、mono、4.107s；PASS。
- source review copies hashes 与 durable Media hashes 相同；PASS。
- Final Shot：未生成，`TECHNICAL_QC = NOT_RUN`。

## 21. Complexity Audit

新增 production contract classes 恰好 2 个：`AVSyncPlan`、`AcousticMixPlan`。新增 small helpers 3 个：两个 canonical builder 和一个 Final Shot fingerprint helper。

没有新增 `LipSyncService`、`AcousticService`、`MixService`、timeline engine、multimodal engine、Java Entity、DB table、CRUD 或 MCP Tool。Comfy-specific 信息只在 audit evidence/report，不进入 provider-neutral contract。

## 22. Tests

| Suite | 结果 |
|---|---:|
| AVSync/Acoustic focused | 18 passed |
| Plugin full pytest（含 DPD/Visual/RP/Voice/7.3D/Media regression） | 221 passed |
| Plugin strict mypy | 55 source files PASS |
| Drama MCP pytest | 26 passed |
| Drama MCP strict mypy | 4 source files PASS |
| Java | NOT_REQUIRED（无 Java production change） |

负向覆盖包括：mouth UNKNOWN/no authority、start<0、end<start、end>video、D1 duration mismatch、provider/psychological field injection、hash mismatch、lip policy/authority mismatch、声场资源跨 Work/Scene、未解决 placement 禁止 final fingerprint、上游变化 staleness。

## 23. User Review Package

```text
artifacts/batch7-3e/review/
  01-source-video.mp4
  02-D1-dry.wav
  av-sync-plan.json
  acoustic-mix-plan.json
  final-shot-summary.md
```

没有 `03-final-shot.mp4`，原因已在 summary 中明示。用户无需重新审 Voice；当前需要的是 Dialogue Placement Review。

## 24. 未解决问题

唯一生产阻断：当前第二句 D1 在 11042ms Shot 内的 approved `dialogueStartMs` 未知。需要用户或正式 Production Review 给出一个明确 anchor；随后派生：

```text
dialogueEndMs = dialogueStartMs + 4107
dialogueEndMs <= 11042
```

Ambience/SFX 仍无可信资产；即使 placement 后进行最小 Dialogue-only mux，也不得凭空添加历史声效。

## 25. 下一阶段前置条件

继续本 Shot 只需要 approved dialogue start anchor；无需重做 DPD、Video、Voice、SpokenContent 或 D1。anchor 进入 AVSyncPlan 后再进行：placement -> optional minimum-change lip decision -> mix -> mux -> durable Media -> download hash -> technical QC -> user review。

不得自动扩大到多 Shot、Scene 或 Episode production。

## 26. 最终 PASS/PARTIAL/FAIL

```text
CURRENT_VIDEO_RESOLVE = PASS
CURRENT_D1_RESOLVE = PASS
CLOUD_STORAGE_HASH = PASS
AV_SYNC_PLAN = PASS
MOUTH_UNKNOWN_SAFETY = PASS
DIALOGUE_PLACEMENT = REVIEW_REQUIRED
LIP_SYNC = NOT_APPLIED_FOR_LOW_VISIBILITY
ACOUSTIC_SCENE_PLAN = PASS
DIALOGUE_PERSPECTIVE = PASS
AMBIENCE = NOT_AVAILABLE
SFX = NOT_AVAILABLE
NO_UNGROUNDED_AUDIO = PASS
MIX = BLOCKED
FINAL_AV_MUX = BLOCKED
FINAL_SHOT_MEDIA = NONE
FINAL_SHOT_TECHNICAL_QC = NOT_RUN
TESTS = PASS
BATCH_7_3E = PARTIAL
```

关键问题逐条答案：7.3E 不重做 D1、不重做 Video；mouth UNKNOWN 不能猜；lip-sync 不强制且失败不重画 Shot；Acoustic Scene 不改变表演，不自动加战场声或音乐；目标仍是 durable Final Shot MP4；Video/D1 永久保留，任何上游变化令 Final Shot stale；Cloud MinIO 由 Drama Service 负责；最终艺术质量由用户判断。

## 27. Resume — User Reviewed Dialogue Placement

### 27.1 Approved anchor 与输入对账

用户明确批准：

```text
timingAuthority = USER_REVIEW
dialogueStartMs = 5200
```

Resume 从当前 Domain 重新取得 Work version 5、Scene、Shot、Work Voice binding、Voice master、canonical SpokenContent、RealizedPerformance、Video 与 D1，并与第 72 批 frozen evidence 对账。当前 live Video/D1 仍为：

| Input | MediaId | Cloud/Media/download SHA-256 | probe duration |
|---|---|---|---:|
| Video | `media_ac9d14c5cdc74c43ba44562752cf9489` | `066b281d01ba8f330c66c463c8c6ff0f238cc2f56af7c0dffbbaf812e62f677f` | 11042ms |
| D1 | `media_6f4d16d785b84b52b3062e0666a826b5` | `4db91e1299cb3083db55290e5e23ef8595e012e5a7b3fe185ba80a44121e7a9c` | 4107ms |

两者都经过 `get_media -> resolve_media -> Drama Service download -> SHA-256`，没有 object missing，也没有执行 reconciliation/上游再生成。

### 27.2 Updated AVSyncPlan

物理 D1 probe 为 4107ms，因此：

```text
dialogueEndMs = 5200 + 4107 = 9307
9307 <= 11042
```

`dialogueStartMs >= 0`、`end > start`、`end <= Video duration` 全部 PASS。用户 anchor 只决定整句 placement；没有派生 word/phoneme/viseme/mouth timing。

旧/new fingerprint：

```text
old AVSyncPlan:
48b183bdb460ac304b5c992668bdcb80f5a88d8c3368c8393dd9e92800b21d31

new AVSyncPlan:
3a159f37e397270aeb8bc7b4164984ace1d912700ae809192d69ac5068dfe271
```

`mouthActivity = UNKNOWN` 与空 mouth windows 原样保留。`LIP_SYNC = NOT_APPLIED_FOR_LOW_VISIBILITY`；没有调用 Comfy/Sync 3。

### 27.3 Minimal mix 与 Final AV Mux

AcousticMixPlan 继续使用：

```text
dialoguePerspective = CLOSE_CONVERSATIONAL
ambienceBindings = {}
sfxBindings = {}
musicPolicy = NONE
spatialTreatment = NONE
```

AcousticMixPlan fingerprint 保持：

```text
1a5fcf8eb6eef3f29b40f312a62e6584c46a91b733adaedef6fec245c90ae165
```

本地 placement 在 24kHz mono PCM 上插入 124800 frames（5200ms）精确静音；D1 原 PCM 98568 frames 只出现一次，位置为 frames `124800–223368`，对应 `5200–9307ms`；前后无意外音频，D1 waveform 未拉速、变调或改时长。

Final mux 使用 ffmpeg 9.0.1：Video `stream copy`，Audio 仅为 MP4 compatibility 编码 AAC，`+faststart`。原 Video bytes hash 未变化，源/成片 H.264 elementary stream hash 均为：

```text
69554fbb33e5d2ea1635acbfbda4c421ccc4242a92f5f2ec7acf32a555752366
```

Final Shot fingerprint：

```text
15f65974fd72a6c471a8c1b16d5d5b00df511d85f9b12b62dcc330503cd4cc0e
```

含 mux implementation/settings 的 Final AV fingerprint：

```text
0627e6e306a36bde275936c0bc2322c3b79b6a5101d2927b72e843abf76f3f4e
```

### 27.4 Durable Final Shot Media 与 Cloud MinIO

成片以新的 derivative Media identity 导入，源 Video/D1 均未覆盖：

```text
purpose = FINAL_AV
reviewStatus = PENDING
MediaId = media_a78d6ab7e9e94d06912c76658d28d378
contentHash = ca306f27b9e7da9ee03e5fa340cc06234b63b91119639a1fa242eae73aff0cbc
durationMs = 11042
mimeType = video/mp4
fileSize = 5528388
```

持久化后执行 `get_media -> resolve_media -> Drama Service download -> SHA-256`：

```text
local final hash
= Media.contentHash
= resolved download hash
= ca306f27b9e7da9ee03e5fa340cc06234b63b91119639a1fa242eae73aff0cbc
```

`CLOUD_MINIO = PASS`；evidence 未保存 signed URL 或 credential。Media 使用 pending attempt sourceRef，因为技术 QC 已完成但用户 Final Shot 艺术 Review 仍为 PENDING。

### 27.5 Technical QC

```text
playable = PASS
video stream = H.264 / 1280x704 / 24fps
audio stream = AAC / 24kHz / mono
duration = 11.041667s
dialogue placement = 5200–9307ms PASS
video stream preserved = PASS
source Video bytes unchanged = PASS
D1 bytes/waveform unchanged = PASS
unexpected audio before anchor = NO
unexpected duplicated dialogue = NO
audio truncation = NO
video truncation = NO
final peak = -3.9 dBFS
clipping = NO
```

第一次本地 QC 在任何 Media import 前发现“MP4 精确时长 11.041667s 与四舍五入 Domain 11042ms”的 8-sample 比较差异；修正为以物理视频精确时长派生 PCM frame count 后重新本地验证。远程 `media.import_media` 只调用 1 次，没有 ambiguous resubmit。

### 27.6 Tests、成本与 Review Package

```text
AVSync/Acoustic focused = 18 passed
Plugin full pytest = 221 passed
Plugin strict mypy = PASS (55 source files)
Drama MCP pytest = 26 passed
Drama MCP strict mypy = PASS (4 source files)

Fish TTS = 0
Voice Design = 0
Create Model = 0
D1 generation = 0
Comfy = 0
new Audio Provider = 0
```

Review Package 已完整更新：

```text
artifacts/batch7-3e/review/
  01-source-video.mp4
  02-D1-dry.wav
  03-final-shot.mp4
  av-sync-plan.json
  acoustic-mix-plan.json
  final-shot-summary.md
```

### 27.7 Resume 最终状态

```text
CURRENT_VIDEO_RESOLVE = PASS
CURRENT_D1_RESOLVE = PASS
TIMING_AUTHORITY = USER_REVIEW
DIALOGUE_PLACEMENT = PASS
MOUTH_UNKNOWN_SAFETY = PASS
LIP_SYNC = NOT_APPLIED_FOR_LOW_VISIBILITY
ACOUSTIC_SCENE_PLAN = PASS
AMBIENCE = NOT_AVAILABLE
SFX = NOT_AVAILABLE
NO_UNGROUNDED_AUDIO = PASS
MIX = PASS
FINAL_AV_MUX = PASS
FINAL_SHOT_MEDIA = PASS
FINAL_SHOT_DOWNLOAD_HASH = PASS
FINAL_SHOT_TECHNICAL_QC = PASS
TESTS = PASS
BATCH_7_3E_ENGINEERING = PASS
USER_FINAL_SHOT_REVIEW = PENDING
DIALOGUE_TIMING_PLANNING_GAP = IDENTIFIED
```

Resume 在当前 1 Shot 结束；不进入 Multi-Shot、Scene 或 Episode Production。
