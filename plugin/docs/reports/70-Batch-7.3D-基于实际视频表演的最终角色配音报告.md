# 70 — Batch 7.3D：基于实际视频表演的最终角色配音报告

日期：2026-08-31。批次：Video-Conditioned Final Dubbing。

## 1. 执行摘要

**BATCH_7_3D = PARTIAL。** 最小视频条件投射、fingerprint/失效机制、Fish adapter opt-in 接入与离线回归已完成；未生成真实 B0/D1，不能宣称 Live 或整批 Engineering PASS。

具体阻断是 `STORAGE_MIGRATION_RECONCILIATION_REQUIRED`：当前 service-owned env 重复定义 `DRAMA_MEDIA_STORAGE_ENDPOINT`，两项分别为 NON_LOCAL、LOCAL，现有 ownership 校验失败。既有服务仍可返回 Video/Voice 原对象且下载 hash 正确，但不足以证明正在使用迁移后的云存储。不是 Fish outage，也不是“云对象已丢失”的结论。

已告知用户保留唯一云端 endpoint、通过现有启动路径重启 Drama Service，再重新预检。本批没有修改 env、重启服务、直接访问 MinIO、重建 Voice 或重新生成 Video。所有真实 TTS 调用为 0。

## 2. 本批范围

实现：既有 DPD/Base Audio Projection + canonical SpokenContent + frozen Voice + accepted RealizedPerformanceSnapshot → final AudioPerformanceBrief → 现有 Fish Role Dubbing 编译/持久化路径。

完成的 Review 为结构化准备包；WAV 不存在，不造占位文件。没有 Lip Sync、SFX、ambience、music、reverb、mix、AV mux 或后续 Episode production。

## 3. 7.3C Fixture

| 对象 | 复用身份 |
| --- | --- |
| Work | `work_9cc5d11969a64f93bce4a544f349c793`，《关门以东》 |
| Script | `script_a404a8277fef45eda8ef3aaf478307cc` |
| Episode | `episode_c33021fe53ba4af08cd8b98113184dd2` |
| Scene | `scene_3ad95aa042e647d9a9be05a51dd8a009`，关门未开 |
| Shot | `shot_83db7eb53b2f49d3a58428d4659e584e`，1-03 三十骑之议，TWO_SHOT |
| Video | `media_ac9d14c5cdc74c43ba44562752cf9489` |
| 主体 | `speaker:geshuhan`，画面右侧人物；沿用 7.3C 的主体关联，不根据姓名推断外观或声音 |
| SpokenContent | `spoken-s1-geshuhan-refusal` |
| 原文 | `此事若行，我便是反臣。不可。` |
| Voice | `voice_3b83cfdee0fd4d1a9b4728b0ef1714d7`，ACTIVE，version 2 |

视频 H.264、1280×704、24fps，约 11.041667 秒，无声音。Shot 原计划时长和 SpokenContent estimatedDuration 不是实际 speech window。没有改成 close-up 或重做 Shot。

## 4. Architecture Freeze

DPD Core/SceneDPD/BeatDPD/LineDPD/DPDSnapshot、既有 AudioPerformanceBrief/Base Audio Projection、CreativeVoiceProfile、Voice 生命周期与绑定均未因本批修改。7.3C Visual Projection、真实视频和 accepted Snapshot 不变。

新增的是一个组合型 final projection wrapper 和局部 helper。已有 Role Dubbing 仅增加 final request 校验、编译 opt-in 与 lineage；未增加 Voice 设计策略。Java production/数据库/CRUD/MCP 新工具均为 0。工作区原有 7.3B–7.3C 未提交修改保留，没有 reset/checkout/commit。

## 5. 开始前 Audio/Video AS-IS Audit

已先读取 65–69 报告、DPD 与 Audio/Video/Voice/Media contracts、Audio Production skill 及其 references、Fish compiler、Role Dubbing、Media restore、现有 integration、env ownership/启动脚本，再开始编码。

审计结论：

1. `AudioPerformanceBrief` 已包含 pace/rhythm/intensity/pause/articulation/ending/control，足以组合；不需要新音频维度体系。
2. 7.3B adapter 的稳定生产默认控制为 speed/volume；7.3B.1 已有可单独 fingerprint 的 rendered text，不应把 dramatic action 自动映射成 emotion label。
3. `SpeechGenerationRequest`、`audio_input_fingerprint`、Role Dubbing `sourceRef` 和 `Media.content` 可承载新依赖，不需要新表。
4. 稳定 Voice 是 Work speaker binding → Voice master → Fish mapping，不是某条 Dialogue Audio Media。当前 mapping 已存在；审计只读检查可达，没有 materialization。
5. Scene canonical SpokenContent 是台词唯一来源；Shot 通过 spokenContentBindings 关联，不从旧音频反抄台词。
6. 7.3C Snapshot 已描述真实画面，但 mouthActivity UNKNOWN，不能为本批提供可靠的开口/结束时间。
7. 可复用 Service `get/resolve/download/import`；已有 `media.restore_media_object` 可以恢复同 ID 对象；Voice 没有同等 restore API。
8. 既有 Audio reviewStatus、technicalReviewStatus、ASR intelligibility QC、WAV probe 和 freshness helper 可复用。
9. 旧 baseline 不能只凭相同 speaker 或相同文本判定；必须匹配完整 base request/material lineage。
10. 本批请求取代前一批 7.3C 的 STOP 范围；只继续 7.3D，不重新执行视频生产。

7.3C review 当时只保存 DPD summary；本批从同一任务原始 7.3C 工具输出恢复完整 DPDSnapshot 到 evidence，再用 `compose_dpd` 校验 effective data 和原 fingerprint 一致。不是重新创作 DPD。

## 6. Cloud MinIO Migration Preflight

`mcp-host.env` ownership PASS；`drama-plugin.env` PASS；`drama-service.env` FAIL：duplicate keys: `DRAMA_MEDIA_STORAGE_ENDPOINT`。Endpoint assignment count=2，class=[NON_LOCAL, LOCAL]。

integration 仅检查 assignment keys 与 endpoint class，不导出或使用 storage credential；不 source service env 到 Host。生产 Plugin 不获得 MinIO endpoint/credential。存储配置应由 Drama Service 启动路径加载。本批没有证明云端实际运行态，故 CLOUD_MINIO_STORAGE_RESOLVE 不能 PASS。

在 gate 修复前，真实生成保持禁止；“已有对象下载成功”不能覆盖配置错误。没有盲目尝试另一个 storage endpoint。

## 7. Video Media Resolve / Hash

通过 Drama MCP 获取现有 Media，并由 `media.resolve_media` 返回 Drama Service owner URL；下载 HTTP 200，5,489,983 bytes，hash PASS：

`066b281d01ba8f330c66c463c8c6ff0f238cc2f56af7c0dffbbaf812e62f677f`

stable Media ID、Shot ownership、RP video hash 一致。未保存临时 URL，未调用 Comfy。固定视频位于工作区 `artifacts/batch7-3c/review/shot-video.mp4`。

## 8. Voice Resolve / Hash

通过 `voice.get_voice` / `voice.resolve_voice` / Service download，HTTP 200，299,052 bytes，3,390ms。Resolve hash 与 metadata、下载 bytes 一致：

`62c41957aeeeaf27b5da897731863a138b76b3f213ab2dbb3fcb780224cf3787`

沿用已冻结 creative profile 文件 `artifacts/batch7-2/evidence/voice-profile-7.2s-r.json`。没有对 UNKNOWN 音色维度补推断，没有从 current facial tension 设计新嗓音。设计、CreateModel、重新绑定都为 0。

## 9. DPD / Video / Voice / SpokenContent Authority

| Authority | 拥有 | 不拥有 |
| --- | --- | --- |
| DPD | objective、action、tactic、relationship、subtext、内部意图 | 视频实际动作事实 |
| accepted RP | 实际可见动作、状态、可靠性及时间窗口 | 心理、剧情、音色 |
| frozen Voice | 稳定声音身份与 master material | 当前一场戏的心理/画面状态 |
| canonical SpokenContent | 原文、说话者、台词 identity | Provider 改词空间 |
| Final projection | 在上述边界内组织声音执行 | 修正坏视频、重新创作 DPD |

最终声音的视觉执行跟随 actual accepted Video；若视频艺术上错，修 Video/Visual 节点并重新 observation，而不是让声音替旧意图纠正画面。

## 10. Video-Conditioned Audio Projection

新增 `contracts/video_conditioned_audio.py::VideoConditionedAudioProjection`，schema `video-conditioned-audio-v1`。9 个字段：schemaVersion、baseAudioProjectionFingerprint、realizedPerformanceFingerprint、videoMediaId、videoContentHash、shotId、voiceMaterialFingerprint、finalAudioPerformanceBrief、fingerprint。

其中 finalAudioPerformanceBrief 是原类型，不复制字段定义。wrapper 与 brief 指纹均校验；request 的 brief 必须和 wrapper 中的 brief 一致。未知版本、provider 注入、guessed speechStart、legacy PerformanceIntent 冲突均失败。

`audio/video_conditioning.py::condition_audio_on_video` 从校验后的 DPD/base/RP 生成新实例，不修改输入；拒绝未声明的 base rendering 参数，防止静默覆盖。

## 11. RealizedPerformance → Audio Mapping

真实 RP：坐姿稳定、低幅度身体动作、主要朝向左侧对象；后段低头看向桌面再回转；visibleActivation MEDIUM、facialTension HIGH、expressionChange PRESENT。

结合 DPD 高内部激活/高控制，final 请求产生“内部紧张但不抬高音量”；可见变化只支持相对句间转折和恢复对人表达；句尾继续承担 DPD 的 reject 行动。保留稳定 Voice baseline 与 native prosody。

离线 counterfactual 把可见激活改为 HIGH、头部动作改为较大且频繁转移视线，产生不同的相对 rhythm 和 final fingerprint，但 text/Voice/DPD 不变。没有 head-speed→speech-speed、gaze-down→sad/quiet 的机械映射。

## 12. mouthActivity UNKNOWN Safety

保持 `mouthActivity=UNKNOWN`、`speechWindow=UNKNOWN`。不填 mouth start/end、speech onset、强制定时 pause 或绝对 phrase plan。

RP 的 7500–10500ms 头动窗口不是 speech anchor；投射只使用“有可见变化”这一事实，不把该时间映射到某个字。UNKNOWN 不妨碍生成自然 dialogue，但妨碍宣称同步准确。

## 13. Duration / Lip Sync Boundary

只允许 NATURAL、targetDuration=null、allowRateAdjustment=false、constraints={}。不使用 videoDuration、estimatedDuration 或当前头动窗口强拉音频。默认自然音频短于完整双人镜头是允许的；本批不做时间对齐。

Fish speed/volume 来自同一个 Base Voice/Audio 映射，B0/D1 都为 speed 0.92、volume 0。7.3D 不改变它们以追动作。

## 14. Final Audio Fingerprint

使用现有 canonical SHA-256 framework，final fingerprint 覆盖 DPD/text/Voice/Timing 的嵌套 brief，以及 Video/RP/master lineage。字段排序不改变结果。无 timestamp、random UUID、host、signed URL、provider response 或秘密。

| 指纹 | 值 |
| --- | --- |
| DPD | `2d826a70c27da23aded5eda30082931b5c122115dd932ce104b3fb590ec90e1b` |
| Realized | `a2d3d311576d75a305e6453089176ac89b0d8cfd9c3acd2a141ee24a13cefd12` |
| SpokenContent（id/speaker/text） | `7c348a81ce2bc5ccd9e4148381815281d33ffc0663072dc27bb063b674740921` |
| Voice material | `1954d55741436b73dd63fe655a00abf451ec3c8fba0272d6a129e5decac0517d` |
| Base projection | `c422b79dbbbab73d05bac8bb23b33a2fbb4c5b0654d1a16b1951da1b5a8ea4de` |
| Final projection | `66feac9fe97938c6bd0243e7b10699115759e0c6b025d88ab4bc090b5318310f` |

完整 sourceRefs、text hash、离线编译的 Fish payload fingerprints 在 `artifacts/batch7-3d/evidence/run.json`。这里的 providerRequestFingerprint 是编译证据，不表示已经提交。

## 15. Video → Audio Invalidation

Video hash 改变 → 新 RP → 新 final projection → 新 audio-input fingerprint → 旧 Audio STALE。相同 Video bytes 下，合法修订 accepted canonical observation 也产生同样效果。

复用 `is_audio_fresh`，没有新增 lineage service。Role Dubbing 在查询旧缓存前检查当前 Video/Shot/Scene/canonical text/Work Voice binding/master hash。测试证明旧 Video request 不能因为已有 Audio 而绕过检查。

最新 accepted observation 仍是调用方的显式输入；没有新增数据库指针或 background stale sweep。调用方不能把旧 observation 当“最新”传入。旧 Media 不删除，不手工改写 Audio Projection 来补救视频。

## 16. Fish Compilation

同一现有 Fish/s2-pro adapter、固定 mapping、原生 speed/volume。显式 `BRIEF_CUES_V1` 才从 brief 的 control/intensity/rhythm/pause/ending 序列化一个有界声音执行 cue；不读取视频、Comfy 数据或剧情意图再推理。

canonical text 完全保留，rendered text 独立 fingerprint。cue 上限 500 字符，拒绝方括号/换行注入、手工 rendered text 冲突及越界文字。旧默认 native 路径不自动启用新 cue。

Fish 官方 S2 文档支持自然语言执行 cue，并非只能固定 emotion tags；adapter 本批仅有选择地编译声音执行描述，未建立 action→emotion 字典。见 [Fish S2 emotion/expression documentation](https://docs.fish.audio/developer-guide/core-features/emotions) 和 [TTS API reference](https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech)。

TEXT_RENDERABLE 不等于艺术可控保证。本批没有 live 听审证据，不能宣称新 cue 已产生优于 B0 的表演。

## 17. Baseline Audio

搜索现有 Work 的 AUDIO Media，发现同 exactTextHash 旧记录 `media_080486d8b87b45ef8a103f6f4aaa90d5`，但没有相同 DPD/Base Projection lineage，不能作为严格 B0。7.3B 的“你可知道后果？”更不是本条台词。

严格 B0 要求同 text、Voice/master、model/mapping、base projection、compiler/material request。当前严格 B0 = NONE；未生成 baseline。存储 gate 通过后若仍不存在，允许一次生成，不复用不相干样本冒充。

## 18. Video-conditioned Final Audio

D1 = BLOCKED；stable Final Audio Media = NONE。本批未执行 `--live`。预算证据：B0=0、D1=0、safe retries=0、候选=0、VoiceDesign=0、CreateModel=0、Comfy=0、其他 TTS=0。

提供 `integration/run_batch7_3d_fish_live.py`：默认 prepare；live 需要显式 plugin config、唯一云端配置及操作方确认 Service 已重启。沿用 MCP 读取与现有配置的 Plugin RoleDubbing 实现；提交前 journal，先按 sourceRef reconcile，模糊结果不自动重提。自动 transient retries 设为 0。

prepare 路径已对真实既有资产运行成功；真实 B0/D1 synthesis/persistence 分支尚未运行，不能以离线测试替代 Live PASS。

## 19. Technical QC

离线 adapter、ASR intelligibility gate、PCM clipping gate、WAV probe、durable Media lineage、下载 hash 验证测试 PASS。

真实 D1 的播放、duration、active speech duration、leading/trailing silence、RMS/peak、clipping、missing/extra/repetition/CER、proper noun QC = **NOT_RUN**，因为没有 D1。终端模板的 Technical QC 只能写未达标，不能写 PASS；不是已经生成音频质量失败。

live runner 复用已有 probe/QC，记录声学统计与 canonical transcript 检查，只有技术通过才把结果用于 review。自然停顿和嗓音审美仍交给用户。

## 20. Media Persistence

final 路径使用现有 `media.import_media`，purpose=`ROLE_DUBBING_AUDIO`，包含 Shot ID、sourceRef、正时长；Service 提供 stable ID、contentHash、mimeType、fileSize。

open content 增加 final/base/RP fingerprints、source Video ID/hash、Voice master/material hash、audioInputFingerprint、providerRequestFingerprint；与 B0 sourceRef 不同。离线持久化测试 PASS；本批实际新的 Audio 持久化与下载验证 BLOCKED。

## 21. Baseline vs Video-conditioned

Review 包位于工作区 `artifacts/batch7-3d/review/`：

- `final-audio-performance-brief.json`：完整 final wrapper 与嵌套原 brief。
- `video-conditioning-summary.json`：safe evidence、fingerprints、UNKNOWN/NATURAL 及实际调用数。
- `baseline-vs-video-conditioned.md`：结构化差异、既有 Video/RP/DPD 链接、baseline 排除理由与恢复条件。

`B0-baseline.wav` / `D1-video-conditioned.wav` 均未创建。结构化差异存在，不等于“已经听到差异”。对照应看 D1 是否贴实际画面，不混同稳定 Voice 音色是否喜欢。

## 22. Cloud Storage Evidence

`evidence/storage-configuration.json`：key ownership 和 endpoint 分类，未保存具体地址/secret。
`evidence/storage-resolve-hash.json`：Service owner、HTTP 200、稳定 ID、hash/size，实际 restoreSameIdentity=false。

缺失对象测试：metadata 存在+下载404 → RECONCILIATION_REQUIRED。受信本地 Video bytes 匹配预期 hash → 仅调用既有 `media.restore_media_object` → 重新下载验证，stable ID 不变；错误 hash/非 Service URL 均拒绝。Voice 无恢复 contract 时必须停止，不能重建。真实环境本次未发生对象404、未执行 restore。

## 23. Tests

| 验证 | 实际结果 |
| --- | --- |
| Plugin full pytest | 203 passed |
| 新 video-conditioning / storage tests | 22 项，包含在 full suite |
| DPD/Base Audio/Voice/RP regression | PASS，包含在 full suite |
| Fish adapter / Role Dubbing / Media persistence | PASS，离线 |
| Plugin strict mypy | 54 source files PASS |
| MCP pytest | 26 passed |
| MCP strict mypy | 4 source files PASS |
| Audio Production skill quick_validate | PASS |
| git diff --check | PASS |
| Java | 未修改 production，未运行，不需要 |
| Real Fish Final Audio | BLOCKED，非 Mock PASS |

负例包括 missing DPD/RP、Video hash/Shot/Scene/speaker/spoken/Voice mismatch、stale RP、非法版本/未知字段/provider 注入、猜测 timing、legacy authority 冲突。另覆盖字段排序、输入不变、Video/observation 变更失效、陈旧 Video/Voice 在 cache 前拒绝、base/D1 相同 compiler/不同执行 cue。

执行结果见 `artifacts/batch7-3d/evidence/tests.json`。部分初次运行发现测试断言误匹配 hash 子串，以及 integration 的当前 MCP stream tuple/字段名/fixture 文件路径兼容问题；已修正，最终 prepare/full tests 重跑通过，没有付费重试。

## 24. Complexity Audit

生产新抽象只有 `VideoConditionedAudioProjection`（9 字段）和一个 projection helper；SpeechGenerationRequest 新增 1 个可选组合字段。新增 enum=0、服务=0、DB/Java entity=0、MCP 工具=0、Video/Audio ontology=0。

生产新增文件2；另外测试2、integration1、contract doc1、报告1。已有 Fish 增加有界 cue helper，Role Dubbing 增加当前输入校验。集成脚本的 storage/budget 检查不是新服务；详细 Snapshot 不迁移数据库。

按 `skill-creator` 仅给既有 Audio Production skill 增加条件路由与 7.3D STOP，明确不运行原 skill 后续 Voice-design/mux 步骤。未安装/reinstall plugin，未改 cache。工作区总 diff 包含上一批已有变更，不能全部算本批复杂度。

## 25. Severity

- P0 检查：未发现本批把 DPD 意图伪造成观察、Video 更新仍命中旧 Audio、core 被 provider 信息污染。对应回归通过。
- P1 未解决：云存储当前运行态未证实，service env 重复 endpoint；阻断付费 TTS 和 Live PASS，不能归为 Fish 故障。
- P1 边界检查：无可信 mouth timing，因此未猜测；真实 Audio QC/持久化尚无证据，保留 BLOCKED/NOT_RUN。
- P2：既有 Base 高控制映射的句尾仍较粗（warning/compliance），本批按冻结要求未改 Base；D1 以 DPD reject 与实际表演组织句尾。cue 艺术效果待听审。

无未修复的已知本批生产代码 FAIL；这不等于已经通过真实艺术验证。

## 26. User Review Boundary

USER_AUDIO_VISUAL_PERFORMANCE_REVIEW = NOT_READY。B0/D1 尚不存在，不能要求用户做不存在的 A/B 选择。未来音频技术完成后才为 PENDING；不能自行认定 D1 更好或完成影视艺术验收。

### 必答 Q1–Q15

| 问题 | 回答 |
| --- | --- |
| Q1 为什么仍需 DPD？ | 它负责人物为什么说、行动/关系/潜台词，不让画面观察重新发明剧情。 |
| Q2 RP 负责什么？ | 实际可见表演事实及可靠性，约束最终声音执行。 |
| Q3 Video 与 DPD 不一致跟谁？ | 视觉执行跟 actual accepted Video，不用旧意图改写观察。 |
| Q4 Objective/Subtext 跟谁？ | DPD。 |
| Q5 Mouth UNKNOWN 能猜窗口吗？ | NO。 |
| Q6 Audio 必须等长 Video 吗？ | NO，自然 dialogue 时长。 |
| Q7 Lip Sync 在本批吗？ | NO。 |
| Q8 Video 改变旧 Audio？ | STALE / REGENERATE，不删除历史 Media。 |
| Q9 是否重新设计 Voice？ | NO，原绑定/master 固定。 |
| Q10 Plugin 直接访问云 MinIO？ | NO，只通过 Drama Service。 |
| Q11 云存储谁负责？ | Drama Service storage layer 与 service-owned 配置。 |
| Q12 迁移丢对象怎么办？ | 明确 reconciliation；受信同 hash Video 通过现有 Service restore 同 identity；Voice 无对应 API 时停止。 |
| Q13 Conditioning 有结构化差异吗？ | YES，rhythm/intensity/pause/ending/control 与 final fingerprint 有区别；不声称已听到。 |
| Q14 真实 Final Audio 成功了吗？ | NO，存储 gate 阻断，TTS=0。 |
| Q15 用户认为 D1 更贴画面吗？ | PENDING USER REVIEW；当前包 NOT_READY。 |

## 27. 未解决问题

需要操作方核对 service-owned 配置，保留唯一正确云端 endpoint 并重启 Service；本批不替用户选择/删除外部配置条目。再次验证两个稳定对象的 resolve/download/hash，不依靠旧进程下载成功作为迁云证明。

然后在显式 live 授权下运行 bounded B0/D1；当前用户的本批授权仍不得扩展为新 Voice、模型对比、艺术重抽、Video regeneration。任何模糊提交先读 journal 和 sourceRef reconcile。配置修复前不能把当前 PARTIAL 改写成 PASS。

## 28. 7.3E 前置条件

这里只记录：稳定 D1 Media、exact canonical text、frozen Video/Voice、accepted RP/final fingerprints、真实 duration/QC/hash 与用户 Review 边界。mouth UNKNOWN 仍须在后续合适阶段另行处理，不能拿当前头动窗口伪装 mouth/phoneme alignment。

本批不实现 AV Sync、viseme、mouth retarget、声音场景、reverb、mix 或 mux。即使恢复后获得 D1，也在 review/report 后 STOP。

## 29. 最终 PASS / PARTIAL / FAIL

VIDEO_CONDITIONED_AUDIO_PROJECTION、DPD_AUTHORITY、REALIZED_VIDEO_AUTHORITY、VOICE_IDENTITY_SEPARATION、SPOKEN_CONTENT_AUTHORITY、MOUTH_UNKNOWN_SAFETY、NO_FORCED_VIDEO_DURATION、FINAL_AUDIO_FINGERPRINT、VIDEO_AUDIO_INVALIDATION、FISH_ADAPTER_INTEGRATION（离线）、DPD/AUDIO/VOICE/RP REGRESSION、COMPLEXITY_AUDIT = PASS。

Video Resolve/Hash、Voice Resolve/Hash = PASS（当前 Service 路径）。Cloud MinIO Migration = RECONCILIATION_REQUIRED。REAL_VIDEO_CONDITIONED_FISH_AUDIO、FINAL_ROLE_DUBBING_MEDIA、FINAL_AUDIO_DOWNLOAD_HASH = BLOCKED。Live TECHNICAL_QC = NOT_RUN。

**BATCH_7_3D = PARTIAL；STOP BEFORE Batch 7.3E AV Sync & Acoustic Scene。**
