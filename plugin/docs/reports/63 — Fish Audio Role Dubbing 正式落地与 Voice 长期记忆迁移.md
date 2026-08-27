# 63 — Fish Audio Role Dubbing 正式落地与 Voice 长期记忆迁移

日期：2026-08-27（Asia/Shanghai）  
执行类型：Production Landing / Domain Migration / Real E2E  
停止边界：`USER_AUDIO_REVIEW = PENDING`

## 1. Executive Summary

本批已把角色声音从一次性 Speech Provider 参数提升为第一类长期资源 `Voice`，并完成真实共享剧情中两位角色的 Fish Audio Role Dubbing。两条正式 Audio 均通过 Fish ASR 可懂度技术质检、Drama Service / MySQL / 持久 MinIO 写入、resolve 下载和 SHA-256 回验；重启 Drama Service 与 MCP 后，Work 绑定、Voice master、Fish mapping 与 Media 全部保持稳定。

本批没有进入 DPD 实现、lip-sync 或 Final AV。技术门已通过，但声音的艺术质量没有被 Codex 自动批准，当前等待用户试听。

## 2. Context Recovery

复用既有真实共享 Narrative Context，没有创建 duplicate Work：

- Work：`work_9cc5d11969a64f93bce4a544f349c793`
- Script：`script_a404a8277fef45eda8ef3aaf478307cc`
- Episode：`episode_c33021fe53ba4af08cd8b98113184dd2`
- Scene：`scene_3ad95aa042e647d9a9be05a51dd8a009`
- Shot：`shot_83db7eb53b2f49d3a58428d4659e584e`
- Dialogue：`spoken-s1-wangsili-proposal`、`spoken-s1-geshuhan-refusal`

62 号 DPD 审计已完成并被读取。本批遵守其结论：`Voice/Casting` 是稳定角色声音，`SceneState + PerformanceIntent` 是当前兼容输入；未来 DPD/RoleDubbingPerformanceBrief 只替换表演输入，不改变 Voice、Fish mapping、Role Dubbing lifecycle 或 Media。

## 3. Git / Runtime Baseline

开始时分别检查了 `drama-plugin`、`drama-mcp-service`、`drama-service`。Plugin 中已有用户修改及未跟踪的 61/62 号报告、creative casting 修复和 Fish runner 修改，全部保留并在其上集成；MCP 和 Service 开始时 clean。没有 reset、clean 或覆盖历史报告/evidence。

真实库 schema 变更前 Voice 表不存在；应用 schema 后、第一次正式提交前确认 `voice_count = 0`，目标 Work 的两个 `speakerKey` 均无 `voiceId`。

## 4. Previous Qwen Architecture

旧实现以 `production.generate_audio`、Speech Provider resolver、Bailian/Qwen/OpenAI adapter、候选 casting 与多批 Qwen runner 为中心。声音身份主要停留在请求/Media provenance 中，没有独立 Voice 生命周期、master reference 所有权、provider mapping 恢复或 Work speaker binding。

## 5. Target Fish Architecture

正式链路为：

```text
Character Understanding → Creative Voice Casting → speakerKey
→ Work Voice Binding / Voice lookup
→ Fish Voice Design（仅缺 Voice）→ AI Casting → Voice master
→ Fish Create Model（仅缺 mapping）→ Fish s2-pro TTS
→ Fish ASR → Intelligibility QC → Media(AUDIO)
```

Fish 仅存在于 Drama Plugin external provider boundary；Skill、MCP、Java Voice Domain 与 Media Domain 保持 provider-neutral。

## 6. Voice Domain Design

新增 provider-neutral `Voice` contract：稳定 ID、name、source type、ACTIVE/RETIRED lifecycle、对象存储身份、duration/hash、`voice-v1` content、version 与时间戳。Voice 不属于单 Scene/Shot/Media；同一个 Voice 可跨 Dialogue 和未来 Scene 复用。

## 7. drama_voice Schema

正式 MySQL 仅新增一个 `drama_voice` 表，列包括稳定身份、`storage_*`、MIME/size/duration/hash、JSON content、version 和 timestamps。Work/Script/Episode/Scene/Shot/Asset/Media schema 均未改变。

项目没有 migration framework，因此新增显式、非启动时 `DramaMemorySchemaCli apply`，使用 checked-in schema；真实云库执行结果为 `DRAMA_MEMORY_SCHEMA_APPLY=PASS`。没有启动时偷偷 CREATE TABLE，也没有把手工 mysql 命令当正式方案。

## 8. Voice Object Storage

复用现有 `MediaStorage`、S3-compatible client、bucket、hash、resolve 与 integrity 能力。Voice master 使用独立 key：`voices/<voiceId>/master.<ext>`，不写 `drama_media`。

E2E 发现 external runtime 仍指向旧 LAN endpoint，当前 Host 连接超时；同机已有正式持久 MinIO `/Users/zy/minio/data` 且 health 200。确认 bucket/credential 后，把 endpoint 迁移到该实例的 loopback 地址；没有启动临时 MinIO、没有新 bucket、没有绕开现有对象存储。

## 9. Voice Content / Provider Mapping

`Voice.content` 保存 provider-neutral creative casting profile、source provenance 与 `providerMappings[]`。mapping 包含 provider、model、opaque provider voice id、material fingerprint、status、createdAt；Java 没有 Fish column。

两个正式 Voice 均有且仅有一个 ACTIVE Fish / `s2-pro` mapping。报告和 evidence 只记录 provider identity 的 SHA-256，不泄露原值。

## 10. Voice Tool Contract

新增：

- `voice.import_voice`
- `voice.get_voice`
- `voice.search_voices`
- `voice.save_voice`（expected version CAS）
- `voice.resolve_voice`

HTTP provider 用 multipart 上传 master，resolve 返回临时 URL；URL 不进入长期 content/evidence。

## 11. Work Speaker → Voice Binding

新增 `work.bind_voice` service operation，由 Plugin 内部调用。绑定仅更新 open `Work.content.voiceProfiles[]` 中对应 `speakerKey` 的 `voiceId`，使用 Work `expected_version` 乐观锁；测试证明 unrelated Work content 不丢失、重复项拒绝、RETIRED Voice 拒绝。

真实 Work 重启后仍保持：

```text
speaker:wangsili → voice_06ac45335157432e8322a9b32e8d9804
speaker:geshuhan → voice_3b83cfdee0fd4d1a9b4728b0ef1714d7
```

## 12. RoleDubbingRequest / Result

`RoleDubbingRequest` 包装现有 typed `SpeechGenerationRequest` 与 `RoleDubbingQcPolicy`。请求保持 exact Dialogue、speakerKey、VoiceProfile、CreativeVoiceCastingProfile、SceneState、PerformanceIntent、pronunciation guidance 与 timing policy。

`RoleDubbingResult` 返回 durable Audio Media ID、Voice ID、duration、Intelligibility QC、lifecycle branch 及本次 Voice Design/Create Model 调用计数。

## 13. production.generate_role_dubbing

旧 `production.generate_audio` 已从活动 Tool catalog 移除，新增单一高层 Tool `production.generate_role_dubbing`。Tool 内部完成 Voice resolve/create、mapping materialization、TTS、ASR QC 和正式 Media persistence；Host 不需调用 Fish-specific Tool。

高层业务错误保持有界：`VOICE_CASTING_FAILED`、`INTELLIGIBILITY_QC_FAILED`、`VOICE_NOT_FOUND`、`VOICE_REFERENCE_UNAVAILABLE`、`VOICE_BINDING_INVALID`、`VOICE_MAPPING_AMBIGUOUS`，并继续复用 ambiguous/rejected/transient 安全语义。

## 14. Branch A — Existing Voice + Fish Mapping

Branch A 只读取 Work binding、Voice 和 ACTIVE Fish mapping。重启后两位角色再次调用均返回：

```text
lifecycleBranch = EXISTING_MAPPING
voiceDesignCalls = 0
createModelCalls = 0
```

相同 fingerprint 命中既有 canonical Media，因此没有重复 TTS/ASR/Media。

## 15. Branch B — Existing Voice / Missing Mapping

Branch B resolve Voice master、校验 stored/resolved/local SHA、执行一次 Create Model、CAS 保存 mapping，再 TTS。没有为了测试删除真实 reference id 或重复花费；offline test 覆盖完整路径并通过：

```text
MISSING_PROVIDER_MAPPING_BRANCH = OFFLINE_PASS
```

## 16. Branch C — New Voice / AI Casting

Branch C 从无 Work binding、无 Voice 开始，要求 CreativeVoiceCastingProfile；一次 Voice Design 请求固定 `n=3`，每个候选做物理探测、signal gate 与 Fish ASR 技术 QC，合格候选再由 acoustic creative-fit proxy 排序。选中 master 后才 import Voice、Create Model、保存 mapping、绑定 Work、TTS、ASR、Media。

如果所有候选技术失败，不创建 Voice、不 Create Model、不 TTS。测试已覆盖。

## 17. Fish Voice Design

Fish Voice Design 编译只位于 Fish adapter/workflow。两个正式 Voice 的 durable provenance 均证明 `candidateCount=3`：王思礼选中 index 2，哥舒翰选中 index 0。

执行中发生一次必须披露的成本异常：第一次王思礼 Design 已成功返回候选，但旧 LAN storage endpoint 导致 Voice import 前回滚；修复明确根因后重新 Design，因此王思礼总 Design submission 为 2，哥舒翰为 1。第一次没有 Voice/Create Model/TTS/Media，结果不 ambiguous。

为防止再次发生，正式代码新增当前运行的 `voice-design-recovery-v1`：下游 import 失败时保留已知 selected master + manifest；再次执行先校验 hash 再续跑 import，`voiceDesignCalls=0`。新增回归测试证明不会重复 Design。

## 18. AI Casting

AI Casting 先执行不可协商的技术门，再对合格候选以 CreativeVoiceCastingProfile 的多维目标做自动评分。Voice content 保存 candidate count、selected index、master hash、technical QC 与 creative fit；没有人工 casting review gate，也没有硬编码真实角色姓名的生产规则。

## 19. Fish Create Model

每个最终 Voice 仅 materialize 一个 Fish model。Create Model 使用 Voice ID + master hash 形成唯一 title；非幂等结果不确定时不盲重提，先通过 Fish model list/title 恢复。mapping CAS 落入 Voice content，Work 不保存 reference id。

## 20. Fish TTS

只允许 Fish `s2-pro`。exact Dialogue 进入 typed text 字段；speed/volume 只在 Fish adapter boundary 由 provider-neutral performance 输入映射。不存在 Qwen/OpenAI fallback。

## 21. ASR / Intelligibility QC

Voice Design 候选与最终 TTS 输出均用 Fish ASR。最终 QC 计算 normalized transcript、CER、missing、extra、repetition 与 proper-noun gate；`sameVendorAsTts=true`。

真实结果：

| Speaker | Transcript gate | CER | missing/extra/repetition | Technical |
|---|---:|---:|---|---|
| `speaker:wangsili` | exact normalized match | 0.0 | empty / empty / empty | PASS |
| `speaker:geshuhan` | exact normalized match | 0.0 | empty / empty / empty | PASS |

ASR QC failure不是自动 reroll，且发生在 Media persistence 之前。

## 22. Audio Media Persistence

正式输出均为 `MediaType=AUDIO`、`purpose=ROLE_DUBBING_AUDIO`、canonical role-dubbing fingerprint sourceRef。content 保存 Voice ID、exact text hash、performance fingerprint、mapping fingerprint、Fish/s2-pro provenance、Intelligibility QC、`technicalReviewStatus=PASS` 与 `reviewStatus=PENDING`。

## 23. Provenance / Fingerprints

持久 provenance 不保存 signed URL、credential 或原始 provider response。关键 identity 由 exact text hash、performance input fingerprint、Voice master hash、provider mapping fingerprint 与 canonical audio input fingerprint连接。重复完全相同输入返回同一 Media ID。

## 24. Persistence Restart Validation

正式创建后重启了 `drama-service` 与 `drama-mcp-service`，且最终再次重启 MCP 以加载 recovery-safe 代码。重启后逐项完成：get Work、get Voice、resolve Voice、get Media、resolve Media、下载和 SHA-256。

两组 Voice ID、Media ID、provider identity hash、master hash、audio hash均未变化；`VOICE_RESTART_PERSISTENCE = PASS`。

## 25. Voice Reuse Validation

共享 Scene 中每个 speaker 仅有一条 canonical Dialogue，因此未创建假 Dialogue。对原 Dialogue 做 canonical repeat 验证：Branch A 0/0，返回同一 Voice/Media，并完成 resolve/hash。按规格：

```text
CROSS_DIALOGUE_REUSE_E2E = DEFERRED_NO_SECOND_CANONICAL_DIALOGUE
SAME_DIALOGUE_CANONICAL_REUSE = PASS
```

## 26. Qwen / Bailian Removal

已删除活动 Qwen/Bailian/OpenAI Speech adapter、resolver/casting/production stack、真实 Qwen speech tests 与六个旧 Qwen preflight/E2E runner。历史 reports/evidence 保留。

活动 source/config/skills/MCP/Java static audit 中不再存在 `qwen3-tts`、`qwen-audio`、`BailianQwenSpeechProvider`、DashScope speech、`BATCH72R_QWEN_MODEL` 或 `production.generate_audio` 实现。Fish blocker 不会恢复 Qwen。

## 27. Runtime Migration

external runtime 修改前创建备份：

`/Users/zy/.config/historical-plugin/runtime.env.pre-role-dubbing-20260827-232502.bak`

移除已证明只属于废弃 Speech/Qwen path 的 assignments，新增 Voice HTTP、checked-in operation map、Fish base/model/output、Role Dubbing timeout 和当前 allowed root；正式 MinIO endpoint 修正到本机持久实例。迁移后 CORE 与 ROLE_DUBBING_FISH 全部 SET，obsolete assignment 列表为空。

`OPENAI_API_KEY`、`DASHSCOPE_API_KEY` 的跨项目归属不确定，因此按要求保留，不作为 Role Dubbing 依赖，并记录为 external runtime tech debt。

## 28. drama-plugin Diff

主要变更：Voice/audio contracts；Voice HTTP/Mock providers；Fish Role Dubbing workflow；intelligibility/signal/creative-fit；Fish model ambiguous recovery；Voice Design known-result recovery；配置/composition/tool catalog；provider-neutral Skill 与 audio convention；真实 E2E runner；Branch A/B/C、Voice HTTP、QC、failure safety 测试；删除旧 Speech/Qwen stack。

## 29. drama-mcp-service Impact

MCP 仍使用通用 registry projection，自动投影五个 `voice.*` Tool 与 `production.generate_role_dubbing`。仅增加少量 RoleDubbing high-level safe error mapping；没有 Fish endpoint/model/reference-id/call ordering业务代码。

## 30. drama-service Diff

新增一个 Voice Java package、Voice storage reuse、Work versioned binding、显式 schema CLI、HTTP operation map与测试；其余 Domain schema 未变。Voice import controller 只把 metadata parse error映射为 invalid argument，不再错误吞掉下游异常。

## 31. Tests

最终回归：

| Repository | Verification | Result |
|---|---|---|
| drama-plugin | full pytest | 134 passed |
| drama-plugin | strict mypy | 44 source files, PASS |
| drama-mcp-service | full pytest | 23 passed |
| drama-mcp-service | strict mypy | 4 source files, PASS |
| drama-service | Maven test | 49 tests, 0 failures/errors |
| drama-service | package | BUILD SUCCESS |
| real E2E | initial + restart/reuse | PASS |

## 32. Provider-neutrality Audit

- Skill：无 Fish/vendor/model/endpoint/reference-id。
- Tool/Contract：Role Dubbing 与 Voice 语义为 provider-neutral；provider mapping 是开放数组。
- MCP：`FISH_SPECIFIC_MCP_CODE = NONE`。
- Java：`JAVA_PROVIDER_SPECIFIC_FIELDS = NONE`。
- Work/Scene/Shot：无 `fish*` 字段。
- Fish 仅出现在 Plugin provider boundary、允许的 Voice mapping/Media provenance 与 provider integration evidence。

## 33. Git Diff

三个仓库的变更均保持未提交，供用户 review。未删除历史 reports/evidence；61、62 号既有未跟踪报告被保留，本报告使用确认后的下一编号 63。Plugin diff 的大部分删除量来自旧 Qwen/Bailian/OpenAI Speech 实现和 runner；MCP 仅小范围 generic adapter/test；Service 主要为 Voice/Work/storage/schema。

## 34. Real E2E Evidence

证据文件：

- `artifacts/role-dubbing-production/evidence/initial.json`
- `artifacts/role-dubbing-production/evidence/reuse.json`

| Speaker | Voice | Media | Duration | Master SHA-256 | Audio SHA-256 |
|---|---|---|---:|---|---|
| 王思礼 | `voice_06ac...9804` | `media_dde1...1cd0` | 3968 ms | `716e09b7...67efb` | `94cda82e...6f37ee` |
| 哥舒翰 | `voice_3b83...14d7` | `media_0804...90d5` | 3596 ms | `62c41957...cf3787` | `20e77f33...24e2ed` |

两条均满足 local/generated or downloaded SHA = durable metadata hash = resolved storage download SHA。

## 35. User Review Files

- `artifacts/role-dubbing-production/review/王思礼-wangsili.wav`
- `artifacts/role-dubbing-production/review/哥舒翰-geshuhan.wav`

master 文件也保存在 `review/masters/` 供技术核对，但用户应优先试听上述两条最终 Dialogue Audio。当前只允许人工判断人物声音、戏剧表演、年龄感、音色区分、节奏与自然度；不得因 ASR PASS 自动宣布艺术质量 PASS。

## 36. Final Status

```text
FISH_ROLE_DUBBING_PRODUCTION = PASS

VOICE_FIRST_CLASS_RESOURCE = PASS
DRAMA_VOICE_TABLE = PASS

VOICE_STORAGE = PASS
VOICE_HASH_INTEGRITY = PASS
VOICE_RESTART_PERSISTENCE = PASS

WORK_SPEAKER_VOICE_BINDING = PASS

VOICE_PROVIDER_MAPPING = PASS
FISH_REFERENCE_ID_PERSISTENCE = PASS

PRODUCTION_GENERATE_ROLE_DUBBING = PASS

NEW_VOICE_BRANCH = PASS
EXISTING_VOICE_BRANCH = PASS
MISSING_PROVIDER_MAPPING_BRANCH = OFFLINE_PASS

FISH_VOICE_DESIGN = PASS
VOICE_DESIGN_INFRA_RETRY_ANOMALY = DISCLOSED_AND_REMEDIATED
AI_CASTING = PASS
FISH_CREATE_MODEL = PASS
FISH_TTS = PASS
FISH_ASR = PASS

INTELLIGIBILITY_QC = PASS

ROLE_DUBBING_AUDIO_MEDIA = PASS
MEDIA_STORAGE_ROUNDTRIP = PASS

QWEN_ROLE_DUBBING_REMOVED = YES
QWEN_FALLBACK = NONE
QWEN_REAL_CALLS = 0
BAILIAN_REAL_CALLS = 0

FISH_SPECIFIC_MCP_CODE = NONE
JAVA_PROVIDER_SPECIFIC_FIELDS = NONE

DPD_IMPLEMENTATION = NOT_STARTED
LIP_SYNC_IMPLEMENTATION = NOT_STARTED
FINAL_AV = NOT_STARTED

USER_AUDIO_REVIEW = PENDING
```
