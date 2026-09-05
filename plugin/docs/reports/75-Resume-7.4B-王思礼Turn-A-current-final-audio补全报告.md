# Resume 7.4B 前置补全 — 王思礼 Turn A 当前正式配音报告

## 1. 执行摘要

本任务结果为 **PASS**。Turn A 的 canonical SpokenContent、Current Voice 及 Cloud master hash、独立 production DPD、speaker-specific Realized Performance、Base/Video-conditioned Audio Projection 全部通过。用户明确授权外发后，Fish Audio 完成唯一一次主生成，结果经 Drama Service 持久化到 Cloud MinIO，并通过回读哈希、物理信号和 ASR 校验。

新 Turn A Media 为 `media_76a8fb24233246189d030babc7ceffd4`，自然时长4571ms，technicalReviewStatus=PASS、reviewStatus=PENDING。它可作为下一次 7.4B 的实际时长证据；这不代表艺术验收。本任务没有重跑正式 7.4B reconciliation。

## 2. 7.4B 当前阻断

此前 7.4B 已证明 Turn A current Final Audio=MISSING、Turn B current Final Audio=PRESENT/4107ms，因此 Full Dialogue Coverage=INCOMPLETE、Full Realized Feasibility=EVIDENCE_LIMITED。

先前自动审批审查曾在进程启动前阻止向 Fish Audio 发送对白及 Voice master；用户随后明确批准该外发及 Cloud MinIO 持久化。授权后的执行成功，旧阻断现已 RESOLVED。历史拒绝及解决状态见 [external-blocker.json](../../../../artifacts/resume-7-4b-turn-a/evidence/external-blocker.json)。

## 3. Turn A Canonical Identity

重新从当前 Domain 读取 Work v5、Scene 和 Shot，而非报告反抄。

| 字段 | 当前值 |
|---|---|
| sequence | 1 |
| spokenContentId | `spoken-s1-wangsili-proposal` |
| speakerKey | `speaker:wangsili` |
| coverage | `ON_SCREEN_SPEAKER` |
| exact text | `请给我三十骑，取杨国忠首级，为大帅除患。` |
| estimatedDurationMs | 5000 |

Shot binding、Scene SpokenContent、speaker 三者一致，Gate A=PASS。当前只读层级及候选审计见 [current-gates.json](../../../../artifacts/resume-7-4b-turn-a/evidence/current-gates.json)。

## 4. Historical Audio Rejection

重新枚举得到7条 Turn-A 历史候选。包括约3968ms、技术 PASS 的 `media_dde17eef66804697a1b9be9d6f881cd0`，但它缺少当前 production DPD、Video、Turn-A RP 与 final projection lineage。旧 Media 未删除、覆盖、改写或伪装成 current；HISTORICAL_AUDIO_REUSE=FORBIDDEN/PASS。

## 5. Current Voice

当前 Work binding 唯一解析为 `voice_06ac45335157432e8322a9b32e8d9804`。Voice status=ACTIVE、version=2，唯一 ACTIVE Fish `s2-pro` mapping 已存在。本任务没有 Voice Design、Voice replacement、rebind 或第二艺术候选；Voice Design calls=0、Create Model calls=0。Gate B=PASS。

## 6. Voice Storage Verification

Voice master declared hash 为 `716e09b7ceb8cb7fd1770c57aa4bd6214f437ce3e07ad16b36ba73ccdc267efb`。已按 `get_voice → resolve_voice → Drama Service → Cloud MinIO → download` 回读；下载文件 SHA-256 与 declared hash 一致，文件大小360492 bytes。TURN_A_VOICE_HASH=PASS。

## 7. Production DPD Audit

搜索结果只有正式 Turn-B DPD `2d826a…` 和 7.4A 为 timing fixture 建立的 Turn-A 临时 DPD `3e3833…`。前者 speaker/line 不匹配，后者明确没有 production authority。当前 Domain 没有可直接复用的 Turn-A production DPDSnapshot，因此依照 `dramatic-performance-direction` Skill，从本次重新读取的 current Work actor hierarchy/P2、Scene、Shot 与 canonical line 独立构建。

Source fingerprint 由 current Work version、两位角色的 hierarchy、P2、Scene、Shot 与 canonical SpokenContent canonicalize 得到；没有复制整份 Character profile、Voice 参数、镜头动作或供应商控制。

## 8. Production DPD Result

新 production DPD fingerprint 为 `af9827cf6564228b4c0a9fd8ed6a1ab2cc1813b5ec36ced9015087014ea413e5`，见 [turn-a-production-dpd.json](../../../../artifacts/resume-7-4b-turn-a/evidence/turn-a-production-dpd.json)。

Effective direction 把发言者定义为有执行能力但无最终批准权的 subordinate officer；目标为 `speaker:geshuhan`，动作是请求明确授权，tactic 是以有限兵力和明确结果作私下进言，internal activation/external control 均为 HIGH。`compose_dpd`、typed round-trip 和 `fingerprint_dpd` 全部一致。

新 DPD 与临时 DPD fingerprint 不同；临时 fixture 只在新 DPD 完成后读取作负面对比，未进入 Base/Final request。NO_TEMPORARY_DPD_REUSE=PASS。

## 9. AudioProjection Authority Ambiguity Audit

付费调用前的真实 dry run 复现了 blocker：旧 `_authority_band` 同时扫描 `authorityPosition`、`relationshipStance`、`tactic`、`dramaticAction`。当前 speaker 的 `authorityPosition=subordinate`，而 relationship/tactic 合理提到对方是 superior/command decision，因而同时命中 SUBORDINATE 和 DOMINANT。

这不是 DPD 矛盾，而是 Projection 把 interaction target 身份误当成 speaker authority。REAL_PRODUCTION_BLOCKER=YES；Fish 在修复前未调用。

## 10. Narrow Fix

只修改 [projection.py](../../src/drama_plugin/audio/projection.py)：speaker authority 仅从 typed `effective.authority_position` 分类。Relationship、tactic、action 仍进入各自表演含义，但不再参与发言者权威分类。没有修改 DPD、AudioPerformanceBrief schema、映射词表、Provider、ontology 或其他 Audio 层。

新增正反回归：subordinate speaker 面对 superior commander 仍为 SUBORDINATE；dominant commander 面对 subordinate 仍为 DOMINANT。既有 authority fixture 和 Turn-B fingerprint 未回归。修复后 production dry run=PASS；旧 temporary DPD 也不再误报，但仍被明确禁止作为 production authority。AUTHORITY_AMBIGUITY=FIXED。

## 11. Turn-A Visual Identity

身份不是依据画面位置猜测。既有 7.3C 接受证据明确写明 `speaker:geshuhan` 从头到尾在 screen-right，身体/面部朝向 screen-left 的王思礼；当前 Shot 又只绑定王思礼与哥舒翰两个 ON_SCREEN_SPEAKER。因此同一不可变 Video 的 screen-left partner 可绑定 `speaker:wangsili`。

本次在该已建立的身份关系上观察 screen-left 人物，并记录先前观察文档哈希；`guessedFromPositionOnly=false`。

## 12. Turn-A Realized Performance Observation

沿用 CONTROLLED_FRAME_SAMPLING，从同一 Video `media_ac9d14c5cdc74c43ba44562752cf9489` 以2fps抽取22帧 screen-left crop。接触表见 [turn-a-contact-sheet.png](../../../../artifacts/resume-7-4b-turn-a/evidence/turn-a-contact-sheet.png)。Comfy calls=0、Video generation=0。

可见事实：人物持续在 screen-left，坐姿稳定并朝向 screen-right partner；开头视线朝对方，中段约3000–6500ms低头看图后恢复；右前臂/手约3500–6000ms向地图前移并指示/描划。上身中段略向桌面靠近。采样不能可靠建立 mouth onset，因此 mouthActivity=UNKNOWN；expressionChange 也保留 UNKNOWN。

## 13. RP Snapshot

Turn-A RP fingerprint 为 `2ca43baa5f4ab5ba8cab24e9da7090d2c6bc2b579b760bf0d50150a721985405`，见 [turn-a-realized-performance-snapshot.json](../../../../artifacts/resume-7-4b-turn-a/evidence/turn-a-realized-performance-snapshot.json)。

Snapshot 绑定 Video hash `066b281d01ba8f330c66c463c8c6ff0f238cc2f56af7c0dffbbaf812e62f677f`、Shot 和 `speaker:wangsili` 观察描述；typed round-trip 与 `fingerprint_realized_performance` 一致。DPD 未被改写成 RP，头/手动作没有被解释为 speech onset。Gate D=PASS。

## 14. Base Audio Projection

输入为新 production DPD、current canonical SpokenContent、现有 `voice-profile:speaker:wangsili:7.2s-r`、current stable Voice identity 和 `TargetTimingPolicy(policy=NATURAL)`。Base Audio Projection fingerprint 为 `c9d3ff77b0e2d232d0af73a3e0ea9b5be2b9c0c35f07d84ce6d438fe0c63018b`。

Timing target=null、allowRateAdjustment=false；没有把5000ms estimate写成目标。Production authority=SUBORDINATE，Projection dry run=PASS。

## 15. Video-conditioned Projection

Base brief与 Turn-A RP 经现有 `condition_audio_on_video` 生成 Final Projection，fingerprint 为 `603816890057232601b1e68cddb38c9a853eac0c8cf69ffffe5887ebcef325c2`。Video identity/hash、Shot/Scene、speaker、canonical text、Voice material 与 RP fingerprint 全部通过既有门禁。

Projection 只决定“怎么说”，没有生成 start/end placement。Provider-neutral request 见 [turn-a-final-request.json](../../../../artifacts/resume-7-4b-turn-a/evidence/turn-a-final-request.json)，preflight 见 [preflight.json](../../../../artifacts/resume-7-4b-turn-a/evidence/preflight.json)。

## 16. Fish Live Generation

使用 current ACTIVE Fish `s2-pro` mapping。Audio input fingerprint 为 `4d22c04cf3133797b72d6db17439baa12a746da63b74dd1317c96010a6c27aa4`，Provider request fingerprint 为 `ad6bc40c8ad644c255b5f674d94bb5ebb08c022ba27638e655323898be891d65`。映射 speed=0.92、volume=-2.0，来自既有 Audio brief→Fish capability mapping，并非5000ms duration fit。

用户明确授权后执行唯一一次 Fish 主调用；safe transient retry=0。第一次执行已创建 durable Media，随后校验脚本因误把 `MediaResolveResult` 当作含 `content_hash` 的对象而中止；恢复时先以固定 `sourceRef` 对账已存在 Media，没有再次提交。最终 [submission.json](../../../../artifacts/resume-7-4b-turn-a/evidence/submission.json) 为 DURABLE，primaryCallCount=1、safeRetryCount=0。

## 17. Technical QC

| 指标 | 结果 |
|---|---|
| format / codec | WAV / PCM S16LE |
| decode/playable | PASS |
| sample rate / channels | 24000 Hz / mono |
| duration | 4571ms（ffprobe 4.571375s） |
| speechActiveDuration | 4294ms |
| leading / trailing silence | 126ms / 152ms |
| RMS / peak | -23.143 dBFS / -3.111 dBFS |
| obvious clipping | false |
| ASR CER | 0.0 |
| missing / extra / repetition | [] / [] / [] |
| proper noun findings | [] |

Fish 返回的是流式 WAV，RIFF/data 长度字段为开放式 sentinel；因此 Python `wave` 的声明帧数不是时长权威。实际时长按完整解码的109713帧计算，并由 ffprobe 独立确认。文件可完整解码，信号与 ASR 门禁均通过。证据见 [completion.json](../../../../artifacts/resume-7-4b-turn-a/evidence/completion.json) 和 [turn-a-ffprobe.json](../../../../artifacts/resume-7-4b-turn-a/evidence/turn-a-ffprobe.json)。TECHNICAL_QC=PASS。

## 18. Media Persistence

新 Media `media_76a8fb24233246189d030babc7ceffd4` 已经由现有 `FishRoleDubbingProvider` 通过 Drama Service 持久化，purpose=`ROLE_DUBBING_AUDIO`、performanceAuthority=`VIDEO_CONDITIONED_FINAL_AUDIO`、sourceRef=`role-dubbing:4d22c04cf3133797b72d6db17439baa12a746da63b74dd1317c96010a6c27aa4`。Media content hash 为 `0940ec4c83da547a20f547a2ca5b90752443d32d22d013e5cce8ff13c71865c7`。旧 Media 未覆盖或删除。MEDIA_PERSISTENCE=PASS。

## 19. Cloud MinIO Verification

执行 `get_media → resolve_media → Drama Service → Cloud MinIO → download → SHA-256`。回读 Media ID 与请求一致；Media declared hash、回读后的 current persisted hash、下载文件 local SHA-256 均为 `0940ec4c83da547a20f547a2ca5b90752443d32d22d013e5cce8ff13c71865c7`。下载文件见 [turn-a-video-conditioned-final.wav](../../../../artifacts/resume-7-4b-turn-a/review/turn-a-video-conditioned-final.wav)。CLOUD_DOWNLOAD_HASH=PASS。

## 20. Freshness / Lineage

新 Media 已验证以下 current lineage：Work/Scene/Shot、`spoken-s1-wangsili-proposal`、`speaker:wangsili`、exactTextHash、Voice ID/master hash、production DPD `af9827…`、Video ID/hash、Turn-A RP `2ca43…`、Base/Final Projection、Audio input、Provider request 与 provider mapping fingerprint。

technicalReviewStatus=PASS、reviewStatus=PENDING、TURN_A_FRESHNESS_EVIDENCE=PASS、TURN_A_REALIZED_AUDIO=PRESENT。该结果是 `PRESENT_FOR_TIMING_EVIDENCE`，不等于 `ARTISTICALLY_ACCEPTED`；正式复用门禁仍可要求后续人工 review PASS。

## 21. Planned vs Actual Duration

PLANNED_TURN_A_DURATION=5000ms；ACTUAL_TURN_A_DURATION=4571ms；DURATION_DELTA=-429ms。音频按 NATURAL delivery 生成，没有为了计划估算强制拉伸或压缩。

## 22. Next 7.4B Preview

只读诊断为 `500 + 4571 + 800 + 4107 + 500 = 10478ms`。相对11042ms Video，粗略 slack=564ms、overflow=0，因此 NEXT_7_4B_EXPECTED=PHYSICALLY_POSSIBLE。

该 sidecar 不替代正式 reconciliation 或 Timing Acceptance。本任务没有修改 DialogueTimingPlan、Video、AVSyncPlan 或 Final Shot；`full7_4bReconciliationRerun=NOT_STARTED`。Turn A 实际音频前置证据已 READY。

## 23. Tests

| 检查 | 结果 |
|---|---|
| Authority narrow regression + Audio Projection + 7.4A/7.4B focused | 147 passed |
| Plugin full pytest | 361 passed |
| Plugin strict mypy | PASS，59 source files |
| MCP pytest | 26 passed |
| MCP strict mypy | PASS，4 source files |
| DPD typed compose/fingerprint | PASS |
| RP typed build/fingerprint、Video hash | PASS |
| Canonical/Voice/Cloud master gates | PASS |
| Real Fish/Media/Cloud Audio | PASS，1 primary/0 retry |
| Current lineage/technical/ASR/hash | PASS |

日志位于 `artifacts/resume-7-4b-turn-a/evidence/*pytest.log` 与 `*mypy.log`。

## 24. Complexity Audit

New core contracts=0、DB=0、MCP=0、service=0、ontology=0。生产改动只有 `_authority_band` 的 authority source 收窄和一项双向参数化回归；DPD/RP/Audio/Voice/Video-conditioned contracts 未改。新增资料均为本次 evidence/review/report，不是业务实体或后台流程。

冻结快照列出 DPD/RP/Video conditioning、7.4A/7.4B 源码与原 artifacts 的当前 SHA-256，见 [frozen-file-hashes.json](../../../../artifacts/resume-7-4b-turn-a/evidence/frozen-file-hashes.json)。

## 25. 未解决问题

1. 艺术 review 仍为 PENDING；本任务仅完成可用于 timing evidence 的技术与 lineage 门禁。
2. Production DPD 与7.4A timing fixture DPD不同。下一次正式 reconciliation 需明确区分 planning DPD 与实际 Audio production DPD lineage；本任务不改 DialogueTimingPlan，也不提前重跑7.4B。
3. Fish 流式 WAV 使用开放式 RIFF/data size sentinel；当前 ffprobe、完整 PCM 解码和 Cloud 哈希均通过。若下游工具只信任 RIFF 声明长度，需要在独立媒体兼容任务中无损规范化容器头，不能覆盖本次 immutable Media。

## 26. Final PASS/PARTIAL/FAIL

| Gate | 结果 |
|---|---|
| TURN_A_CANONICAL_SPOKEN_CONTENT | PASS |
| TURN_A_CURRENT_VOICE | PASS |
| TURN_A_VOICE_HASH | PASS |
| TURN_A_PRODUCTION_DPD | PASS |
| NO_TEMPORARY_DPD_REUSE | PASS |
| TURN_A_REALIZED_PERFORMANCE | PASS |
| TURN_A_AUDIO_PROJECTION | PASS |
| AUTHORITY_AMBIGUITY | FIXED |
| VIDEO_CONDITIONED_FINAL_AUDIO | PASS |
| REAL_FISH_TTS | PASS |
| TECHNICAL_QC | PASS |
| MEDIA_PERSISTENCE | PASS |
| CLOUD_DOWNLOAD_HASH | PASS |
| TURN_A_FRESHNESS_EVIDENCE | PASS |
| TURN_A_REALIZED_AUDIO | PRESENT |
| REGRESSION | PASS |

**TURN_A_FINAL_AUDIO_COMPLETION=PASS**。STOP BEFORE 7.4B FULL REALIZED RECONCILIATION。
