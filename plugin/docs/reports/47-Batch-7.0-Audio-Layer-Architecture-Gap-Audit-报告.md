# 47 — Batch 7.0 Audio Layer Architecture & Gap Audit 报告

执行日期：2026-08-20（Asia/Shanghai）

性质：ARCHITECTURE AUDIT + GAP AUDIT + MINIMAL DESIGN

结论：**PASS**

## 1. 执行摘要

Batch 7.0 只进行了静态代码、正式只读 Tool Contract、现有 Media、Skill、Provider capability、旧 Dify DSL 与本地 AV utility 审计；没有实施 Audio Production。

当前系统已具备 Dialogue 真源、Work-scoped `speakerKey`、Shot coverage、静音视频和通用 Media/Object Storage 基础，但 **尚不具备已验证的 Audio Production**。主要缺口不是“没有 `AUDIO` 枚举”，而是没有稳定的 Work voice identity、真实 TTS adapter、pronunciation layer、text fidelity gate、可读取的实际音频时长、跨 Shot speech clip ownership、可持久化的 AV assembly provenance 与 freshness/idempotency 约定。

推荐最小架构为：

```text
Scene.content.spokenContent[]                    authoritative language
       ↓ spokenContentId + speakerKey
Work.content.voiceProfiles[]                     stable creative voice identity
       ↓ provider mapping resolved by Host/adapter
Media(AUDIO, purpose=SPEECH_CLIP, shotId=null)   one clip per spoken item
       ↓ reusable across Shot coverage
Host Audio/AV assembly manifest                  timing, pause, mix, source refs
       ↓
Media(AUDIO, purpose=SHOT_DIALOGUE_MIX)           optional durable v1 mix
       + immutable silent Video Media
       ↓ deterministic mux
Media(VIDEO, purpose=FINAL_AV)                    new durable output
```

不推荐新增 Audio Entity、Audio 数据库表或 Audio CRUD Tool。现有 `Media` 足以承载 speech clip、mix 和 final AV；7.1 应只补足现有 Media Contract 的 `durationMs`、确定性 `sourceRef`/fingerprint 幂等入口和必要过滤能力，并新增一个精简 `audio-production` Skill。Provider generation Tool 与 Domain persistence Tool 必须继续分离。

## 2. 当前验证基线

已读取：

- Batch 6.D0、6.D1、6.D2、6.0R-E2E 最新报告；
- `dialogue-layer-content-convention.md`；
- 当前 `drama-service`、`drama-plugin`、`drama-mcp-service`；
- 当前非 Git Artifact Root 下的 dialogue backfill、visual regression、checkpoint、ledger 和静音视频；
- Shot 1-03 当前正式 Work/Scene/Shot/Media readback。

当前已验证链路：

```text
Historical Context
→ Work speaker identity
→ Scene.content.spokenContent[]
→ Shot.content.spokenContentBindings[]
→ Shot.content.plannedDurationMs
→ Dialogue-aware Image
→ Silent Video
→ Media / MinIO / Resolve / Hash
```

状态保持：

```text
DIALOGUE_LAYER_VISUAL_CONSUMER_READY = YES
AUDIO_LAYER_VALIDATED = NO
```

## 3. 工程与 Artifact 边界

```text
CURRENT_LONG_TERM_MEMORY_SERVICE = current workspace drama-service
CURRENT_PLUGIN = current workspace drama-plugin
CURRENT_MCP = current workspace drama-mcp-service

ARTIFACT_ROOT = /Users/yizhao/PyProject/historical_plugin/artifacts/batch6-0re2e
ARTIFACTS_GIT_MANAGED = NO

OLD_DIFY_DSL = /Users/yizhao/IdeaProjects/AI_historical/src/main/resources/dify_dsl
OLD_DIFY_DSL_ROLE = REFERENCE ONLY
AI_HISTORICAL_RUNTIME_DEPENDENCY = NO
```

未使用旧 `plugin/docs/reports/artifacts/...` 作为 runtime root；未执行 `git add/restore` 处理 artifacts。当前三个源码仓库原本已有用户修改，本批未归属、回滚或覆盖这些修改。

## 4. 当前 Audio 相关代码 / Contract

当前真实能力分层如下：

| 位置 | 当前事实 | 结论 |
|---|---|---|
| `drama-service` | `MediaType {IMAGE, VIDEO, AUDIO}` | AUDIO 类型真实存在 |
| `drama-service` | `MediaEntity.durationMs` 与 DB `duration_ms` 已存在 | 字段存在但当前 import 不写、Result 不暴露 |
| `drama-plugin` | `MediaType.AUDIO` | Plugin contract 支持类型 |
| `drama-plugin` | `ProductionProvider.generate_audio(prompt, refs, parameters)` | 只有泛化 seam，无 speech-safe structured contract |
| Tool Catalog | `production.generate_audio` 已暴露 | Contract 存在，不等于真实 TTS 实现 |
| 当前 MCP tools/list | 确认 `production.generate_audio`、Media import/resolve 等存在 | MCP 可发现 |
| 当前 runtime provider mode | production=`mock` | 当前 Tool 调用不会进入真实 TTS Provider |
| Mock provider | 返回伪 `MediaType.AUDIO` 元数据 | 只用于测试，不能证明 Audio Production |
| Skill | `shot-production` 提到显式 Audio 请求 | 方法学边界存在，但没有 voice resolution/timeline/review/mux 完整流程 |

因此：

```text
CURRENT_AUDIO_SUPPORT = PARTIAL
CURRENT_REAL_TTS_ADAPTER = NO
CURRENT_AUDIO_TOOL_IMPLEMENTATION = CONTRACT_ONLY_PLUS_MOCK
```

## 5. 当前 Media Audio 能力

当前 Media 稳定 envelope：

| 字段 | 当前真实状态 | Audio 设计含义 |
|---|---|---|
| `id` | required | stable Media identity |
| `workId` | required | speech clip 可归属 Work |
| `assetId` | optional | speech 不应依赖视觉 Asset，通常 null |
| `shotId` | optional | speech clip 可 null；Shot mix/final AV 可绑定 Shot |
| `sceneId` | 不存在于 envelope | 可暂存于 open `content`；若规模证明查询不足再评估 envelope |
| `mediaType` | IMAGE/VIDEO/AUDIO | 可表示 Audio |
| `purpose` | optional free string | 可区分 SPEECH_CLIP、SHOT_DIALOGUE_MIX、FINAL_AV |
| `sourceRef` | required unique | create 可幂等；import 当前自动随机，形成缺口 |
| `content` | required open object | 可表达 spoken item link、fingerprint、provider metadata、assembly manifest |
| `durationMs` | DB/entity 已有 | import/result 未接通 |
| MIME / size / hash | entity/storage 已有 | get/list Result 不暴露；resolve 仅暴露 MIME/size |

明确回答：

```text
Can current Media represent speech audio? = YES, structurally
Can it represent one spoken item used across multiple Shots? = YES, with shotId=null and sceneId/spokenContentId in content
Can it represent final AV separately from silent source video? = YES, as a new VIDEO Media with a distinct purpose and source links in content
Can sourceRef/purpose/content express provenance without new entity? = YES
Does current Media import support audio MIME? = YES structurally; it accepts generic MIME, but AUDIO-specific MIME validation/E2E is unverified
Does current resolve/storage support audio objects? = GENERICALLY YES by code; AUDIO object round-trip remains unverified
```

关键限制：当前 `media.list_media` 只按 type 过滤，Java 端上限 100；没有 work/purpose/sourceRef 过滤。当前 imported Media 的 `sourceRef` 被强制生成为随机 `storage:UUID`，不利于在付费生成前做 fingerprint 幂等查询。

## 6. Current Audio Production Flow

真实当前 flow 为：

```text
production.generate_audio Tool
→ current runtime MockProductionProvider
→ mock Media metadata only
```

当前没有：

- 已接入 Drama Plugin 的真实 TTS provider；
- speech-specific exact-text input contract；
- voice profile / provider voice mapping；
- pronunciation adapter；
- post-generation duration probe；
- text fidelity review；
- Audio Media import round-trip test；
- Audio timeline 或 AV mux formal flow。

所以不能把 Tool 名称或 Mock 成功当作生产能力。

## 7. Dialogue → Audio Gap

Dialogue 已提供 `spokenContentId/kind/speakerKey/text/performanceIntent/provenance/estimatedDurationMs`，Shot 已提供 coverage 和 planned duration。缺失的 consumer responsibilities 为：

1. `speakerKey → creative voice profile`；
2. creative profile → provider/model/voice mapping；
3. exact text → pronunciation-safe provider input；
4. material render parameters；
5. one spoken item → one reusable speech clip；
6. actual duration 与 review；
7. cross-Shot timing/clip slicing；
8. speech mix 与 immutable source video 的 AV assembly；
9. idempotency、freshness 与 stale detection。

Dialogue Layer 不承担以上职责，也不得被 Audio Layer反向修改。

## 8. Voice Identity / Voice Profile

Voice Profile 必须是 provider-agnostic 的业务长期记忆，至少表达：

- age presentation；
- timbre tendency；
- temperament / authority；
- baseline pace；
- power / restraint；
- language/register；
- consistency notes。

Ownership 比较：

| 方案 | 一致性 | Narrator | 重复/复杂度 | 结论 |
|---|---|---|---|---|
| Work actor hierarchy 内嵌 | actor 跨 Scene 稳定 | narrator 不自然 | 轻，但污染历史 actor 结构 | ADAPTABLE，不首选 |
| Work-level voice registry keyed by speakerKey | 跨 Scene/Episode 稳定 | 原生支持 `narrator:*` | 轻量 open content | **推荐** |
| Scene spoken item 内嵌 | 每句可见 | 可支持 | 高重复、声音漂移 | DROP |
| runtime 临时选择 | 无持久一致性 | 可支持 | 重启后漂移 | 仅试验可用，非正式方案 |
| 独立 Voice Entity | 强生命周期 | 支持 | 新表/CRUD/Tool 过早 | DEFER |

推荐：

```text
RECOMMENDED_VOICE_PROFILE_OWNERSHIP = Work.content.voiceProfiles[] keyed by speakerKey
```

Visual Asset 与 Voice Profile 完全解耦；同一人物 Reference Image 不参与声音身份判定。

## 9. Provider Voice Mapping

Creative Voice Profile 与 Provider Mapping 必须分层：

```text
voiceProfile.creativeProfile
  ≠
voiceProfile.providerMappings[]
```

Provider mapping 记录 `provider/model/voiceId/material parameters/mapping fingerprint/status`。更换 Provider 时保留 `speakerKey`、Dialogue text 和 creative profile，只切换 mapping。每次生成的 Audio Media 必须冻结实际使用的 mapping fingerprint 和 provider metadata，以便重现与 stale detection。

Provider 参数不得写回 `Scene.spokenContent`。

## 10. Pronunciation

历史人名、地名和官职构成真实 gap，例如哥舒翰、火拔归仁、崔乾祐、潼关、陕洛。推荐 Work-level provider-agnostic pronunciation registry：

```text
Work.content.pronunciationGuidance[]
  term
  language
  reviewedReading
  optional speakerScope
```

Adapter 将 `reviewedReading` 转成 provider 支持的 phoneme/pinyin/SSML/dictionary。正式 `spokenContent.text` 始终保持原样；不得插拼音、奇怪符号或为 TTS 改写正文。

具体历史读音必须单独 Review；本报告不伪造读音结论。

## 11. Text Fidelity

Text Fidelity Gate 分层：

**MUST**

- Provider 输入来自当前 Review PASS 的 exact `spokenContent.text`；
- 生成前保存 canonical `textHash` 与 `spokenContentId`；
- Provider 不得收到“根据剧情写一段台词”类开放任务；
- 生成后由 Host/Reviewer按 exact text 听审或 transcript 对照；
- mismatch、删词、加词、错人、不可懂均 FAIL，不允许自动改 Dialogue。

**SHOULD**

- 保存 provider transcript（若有）；
- 独立 ASR transcript + 规范化比较；
- 对历史专名和 ASR 低置信片段强制人工复核。

**DEFER**

- phoneme-level forced alignment；
- 全自动无人工 text-fidelity adjudication。

Audio 只保存 `spokenContentId + textHash` 追溯历史 provenance；不复制 `sourceRef/locator/excerpt`。

## 12. Actual Duration

```text
Scene.spokenContent.estimatedDurationMs ≠ Audio actualDurationMs
```

推荐 `Media.durationMs` 成为物理 speech clip / mix 的 authoritative actual duration。当前 DB/Entity 已有该字段，但 import/result 未接通，是 7.1 最小 Java/Contract gap。Provider metadata 可保存 raw provider duration；最终以本地 probe 后的 Media duration 为准。

不得覆盖 Dialogue estimate。可在 Audio Media `content` 中保存：

```text
estimatedDurationMsAtGeneration
actualDurationMs
durationDeltaMs
```

其中 `actualDurationMs` 的唯一规范值仍应与 envelope `Media.durationMs` 一致。

## 13. Duration Reconciliation

7.0 不冻结无实测依据的百分比阈值。推荐状态机：

| 状态 | 判定 |
|---|---|
| PASS | actual clip 可在 video/coverage window 内保留可懂度、performance pause 与反应空间 |
| ADJUSTABLE | 只需在已审 voice/performance 边界内调整 pace/pause/voice rendering 或 AV placement 即可兼容 |
| VISUAL_REPLAN_REQUIRED | 合理 render 调整仍超窗，或调整将损害可懂度、语义、人物表演、coverage |

Audio 较短时优先使用自然停顿、呼吸、反应、room tone 或画面 hold。Audio 较长时依次尝试 provider 可控且可审的 pace/pause、合适 voice mapping、AV edit；仍不兼容才触发 visual replan。禁止删词、增词或让 Provider 改写。

7.2 记录 `plannedDurationMs`、silent video duration、candidate speech window、actual duration、可控范围和 review 结果后，再冻结 provider-specific tolerance。

## 14. Audio Clip Ownership

方案比较：

| 方案 | 单一真源 | 跨 Shot reuse | 生命周期/版本 | Java/Tool 影响 | 结论 |
|---|---|---|---|---|---|
| A. 强绑定某一 Shot | 弱 | 差，reaction 会复制 | 被 Shot edit 误伤 | 小 | DROP |
| B. 绑定 Scene spoken item 的新 envelope 字段 | 强 | 好 | 需 Media sceneId/schema 改动 | 中 | 可选但非最小 |
| C. Work Media + `content.sceneId/spokenContentId` | 强 | 好 | 由 fingerprint 管理 | 最小 | **推荐** |
| D. 独立 Audio Clip Entity | 强 | 好 | 最强 | 新表/Entity/CRUD | DEFER |

推荐 speech clip：`workId` 绑定 Work；`shotId=null`；`assetId=null`；`purpose=SPEECH_CLIP`；`content` 指向 `sceneId/spokenContentId/speakerKey`。因此一个 spoken item 即使由 ON_SCREEN 与 REACTION 两个 Shot 覆盖也只生成一次。

## 15. Cross-Shot Reuse

Shot binding 继续是唯一 coverage 语义：`ON_SCREEN_SPEAKER/REACTION/OFF_SCREEN/VOICE_OVER`。Audio 不创建平行 coverage enum。

跨 Shot 场景：

```text
spoken item X
→ one SPEECH_CLIP Media
→ Shot A assembly slice references X
→ Shot B assembly slice references same X
```

如果一句跨切点，assembly manifest 使用 `sourceInMs/sourceOutMs` 表达每个 Shot 的 clip slice；不重新 TTS、不复制正文、不创建第二 speech identity。

## 16. Audio Timeline Ownership

比较：

| 位置 | 优点 | 问题 | 结论 |
|---|---|---|---|
| Shot content 绝对 timeline | 取用简单 | 跨 Shot 复制、污染 Shot design | DROP |
| Scene content audio timeline | 跨 Shot 完整 | consumer output 混入 Dialogue/Scene full replacement | 不作为 v1 canonical |
| clip + separate assembly plan | source/mix 解耦、跨 Shot reuse | Host 需维护 manifest | **推荐** |
| Audio Media 自带全部 timing | clip 可自描述 | 一个 clip 无法拥有多个 Shot placements | 只保存 intrinsic duration，不保存所有 placements |

推荐 timeline 由 Audio/AV Host 在 Agent Run Context / batch artifact 中构建；提交 Final AV 时，将该 Shot 的 committed assembly slice 固化到 Final AV Media `content`。若生成 durable `SHOT_DIALOGUE_MIX`，其 Media `content` 同时保存 ordered clip placements。未来需要完整 Scene mix 时，可新增 `SCENE_DIALOGUE_MIX` purpose，而非新 Entity。

## 17. Speech Clip vs Final Mix

必须区分：

```text
SPEECH_CLIP = one reviewed spoken item rendering
SHOT_DIALOGUE_MIX = speech clips + reviewed pauses/basic silence placement
FINAL_AV = immutable silent video + selected Audio mix
```

Speech clip 支持重用、单句重生、pronunciation review。Mix 是 derivative，不是 Dialogue source。7.2 v1 可只包含 speech + silence/pause；room tone 可选。不得把 Dialogue、SFX、BGM、Foley 一次生成成不可追溯黑盒。

## 18. Final AV Media

最终 AV 仍为：

```text
Media(mediaType=VIDEO, purpose=FINAL_AV, shotId=<shot>)
```

`content` 至少记录：

- sourceVideoMediaId；
- audioMixMediaId 或 ordered speechClipMediaIds；
- assembly manifest / timeline；
- audioInputFingerprint(s)；
- finalAvFingerprint；
- mux implementation/version/settings；
- actual duration / stream review；
- Media hash/review status。

当前 free-form `purpose/content` 足以表达，无需新 FinalAV Entity。

## 19. Source Video Immutability

规则：

```text
SOURCE_VIDEO_MEDIA remains immutable
FINAL_AV_MEDIA = new Media
```

Shot 1-03 silent source：`media_63787886dc85413c90207e17d68df520`。未来不得覆盖其对象、修改为有声版本或复用同一 Media identity。Final AV 必须新文件、新 object、新 Media ID、新 hash。

## 20. AV Assembly / ffmpeg Boundary

当前 Host 上 `/opt/homebrew/bin/ffmpeg` 8.1.2 可用；当前三个工程没有正式 ffmpeg/mux Tool、Provider adapter 或 production implementation。历史上 Agent 能运行 ffmpeg 不等于 Platform Contract 已实现。

最小推荐：

- v1 将 mux 作为 **Host local utility**，由 `audio-production` Skill 规定 capability preflight、输入 Media resolve、不可覆盖、确定性参数、ffmpeg/ffprobe version capture、stream/duration/hash review；
- Java 只持久化 Media，不构建命令、不做 creative timing；
- 不新增 Domain Tool；
- 若未来 Agent SDK/Windows/remote Host 无 ffmpeg，再把同一 manifest 交给可替换的 AV assembly provider/tool。

这比在 Java 中硬编码 ffmpeg 更符合可移植性和职责边界。7.1 可提供小型跨平台 helper/recipe，但必须在 PATH capability 缺失时明确阻塞。

## 21. Audio Media Import / Resolve

当前 import/store/resolve 对字节和 MIME 是通用实现；S3/MinIO 不区分图片、视频或音频。7.1 最小加固：

1. import metadata 支持正整数 `duration_ms` 并写入现有 DB 字段；
2. Media Result/Plugin contract 暴露 `durationMs/mimeType/fileSize/contentHash`；
3. `media_type=AUDIO` 至少验证 `audio/*`，FINAL_AV 验证 `video/*`；
4. 增加 WAV/MP3 import → MinIO → resolve → hash 的真实测试；
5. 不创建新表。

当前代码证据支持“generic object 可存/取”；在完成真实 Audio round-trip 前，Audio-specific E2E 状态仍为 UNVERIFIED。

## 22. Idempotency / Fingerprint

推荐：

```text
AUDIO_INPUT_FINGERPRINT = SHA-256(canonical JSON of:
  schemaVersion,
  workId,
  sceneId,
  spokenContentId,
  textHash,
  speakerKey,
  performanceIntentHash,
  voiceProfileFingerprint,
  providerMappingFingerprint,
  pronunciationFingerprint,
  provider/model,
  materialRenderParameters,
  targetTimingPolicy
)
```

生成前必须按 fingerprint 查 existing PASS Media。当前 imported Media 的随机 `sourceRef` 与 list filter 不足是 gap。7.1 应让 `media.import_media` 接收可选确定性 `source_ref`，并让现有 `media.list_media` 支持 `work_id/purpose/source_ref` 过滤；沿用 DB 唯一索引和既有 Tool，而非新 CRUD Tool。建议 sourceRef 形如 `audio-input:<fingerprint>`，但具体前缀在 7.1 convention 冻结。

## 23. Dialogue Revision / Audio Staleness

spoken item wording 可在 ID 不变时修订，因此 `spokenContentId` 单独不足。

以下任一变化使旧 speech clip `STALE`：

- canonical text/textHash；
- speakerKey；
- performanceIntent；
- pronunciation guidance；
- material target timing/render policy。

历史 provenance detail 若不改变正文、speaker 或 performance，通常不要求重生；Audio 仍通过 `spokenContentId` 追溯最新 provenance。旧 Media 不删除、不覆盖，只是不再被 freshness gate 选为 current。

## 24. Voice Change / Audio Staleness

以下变化也使 Audio stale：

- creative voice profile fingerprint；
- provider/model/voiceId mapping fingerprint；
- material provider controls，例如 speed/style/stability/pitch/emotion；
- mapping status 从 approved 变为 retired。

非声音内容的 metadata 文案变化不应无意义重生。7.1 必须定义 material/non-material parameter whitelist。

## 25. Audio Review

**MUST v1**

- speakerKey 与 Work voice profile/mapping 正确；
- exact text fidelity；
- 本句出现的历史专名 pronunciation；
- performanceIntent（克制、压低、停顿、断然等）；
- intelligibility；
- clipping / severe noise absent；
- actual duration 和 pause quality；
- voice consistency fingerprint；
- Media/MIME/stream/hash。

**SHOULD SOON**

- ASR normalized comparison；
- loudness/peak/basic silence metrics；
- reference sample consistency review；
- provider transcript and confidence；
- cross-Scene voice comparison。

**DEFER**

- studio mastering；
- spatial mix；
- phoneme forced alignment；
- perceptual MOS automation。

## 26. Subtitle Compatibility

字幕正文直接投影 `spokenContent.text`，不依赖 ASR；字幕 timing 来自 committed Audio/AV assembly manifest。Audio transcript 只用于 fidelity verification，不成为字幕正文真源。

因此推荐模型支持：

```text
spokenContentId + exact text + actual start/end → subtitle cue
```

v1 不要求生成字幕。

## 27. Lip-sync Compatibility

未来 lip-sync 可由以下信息直接得到：

- `spokenContentId`；
- `speakerKey`；
- actual clip/timeline；
- Shot binding coverage；
- `ON_SCREEN_SPEAKER` 与口部可见性 review。

REACTION/OFF_SCREEN/VOICE_OVER 不应错误触发说话人口型。v1 只验证 speaker timing、voice identity、AV sync 和无明显角色错配；不要求 phoneme-level lip-sync。

## 28. SFX / Ambience / Music Boundary

分类：

| 能力 | v1 |
|---|---|
| Dialogue speech | MUST |
| basic pause/silence placement | MUST |
| optional room tone | OPTIONAL |
| loudness-safe simple mix | SHOULD |
| ambience | DEFER |
| Foley | DEFER |
| SFX | DEFER |
| BGM/music | DEFER |
| ducking/spatial audio | DEFER |

第一版不恢复旧 Dify 的全量 Audio JSON。

## 29. Current Provider Capability

只读 discovery 发现：

- Comfy templates：Chatterbox single/multi-speaker/multilingual voice cloning；
- Comfy nodes：Fish Audio TTS/voice selector/voice clone/STT；ElevenLabs TTS/dialogue/voice selector/STT；HeyGen TTS；Qwen3-TTS 等；
- ElevenLabs sound-generation 是 SFX，不等同 speech TTS；
- 当前 Drama runtime production provider 仍为 mock。

结论：外部 Provider 候选存在，但 Batch 7 不应绑定 Comfy。7.1/7.2 必须通过 provider-agnostic request + adapter mapping 使用；provider replacement 不改变 Dialogue 或 Work voice profile。

预算治理：每个 Provider 有各自计费单位和执行预算，Host 应设 per-provider spend gate，并汇总到通用 production run ledger。视觉遗留 733 Comfy credits 不是自动 Audio budget，本批消费 0。

## 30. Old Dify DSL Audio Findings

旧 DSL 实际存在：

- 上游 dialogue 作为授权正文，明确要求 Audio 不得改写；
- 每句 speaker/item identity；
- `shotAudioPlan/audioTimeline`；
- dialogue/narration/ambient/foley/sfx/music/pause；
- subtitle projection；
- `VIDEO_WITH_AUDIO` 的 `audioPlan/syncPlan/lipSyncItems`；
- time range 和 duration validation。

正确思想是“正文授权、逐句身份、下游 timing、字幕投影、AV sync”。错误之处是 Shot-local 重复正文、一次性大 schema、强制空字段、固定 Dify node graph、Audio/Mix/Subtitle/Lip-sync 全耦合，以及 provider-facing字段过度进入同一 JSON。

## 31. KEEP / ADAPT / DROP / DEFER

| 分类 | 内容 |
|---|---|
| KEEP | Dialogue exact text authoritative；Audio 不改写；逐句 speaker identity；actual duration feedback；timeline；subtitle projection；source video immutable |
| ADAPT | 旧 itemId → current spokenContentId；speakerId → speakerKey；Shot audio timeline → clip + assembly manifest；voicePerformanceIntent → creative profile + adapter controls；VIDEO_WITH_AUDIO → new Final AV Media |
| DROP | Shot-local copied Dialogue；固定 Dify graph；巨大 mandatory Audio JSON；Audio/Subtitle/Mix/Lip-sync 一次规划；把 Provider voiceId 写进 Dialogue；空字段占位 schema |
| DEFER | ambience、foley、SFX、music、ducking、spatial audio、full Scene mix、precise lip-sync、automated mastering、independent Audio/Voice Entity |

## 32. Architecture Options Comparison

| 维度 | Shot-owned Audio | Scene-owned Audio plan in Scene content | Spoken-item Media + assembly manifest | Independent Audio Entity |
|---|---|---|---|---|
| Source of Truth | 容易复制正文 | 可引用 Scene | 直接引用 Scene item | 可引用 Scene |
| Cross-Shot reuse | 差 | 好 | **好** | 好 |
| Voice consistency | Shot 级漂移风险 | 中 | Work registry 驱动 | 可强制 |
| Actual duration | Shot plan | Scene plan | **Media.durationMs** | Entity field |
| AV timing | Shot 内简单 | Scene 完整 | **独立 manifest，兼顾两者** | 完整 |
| Media linkage | 简单但复制 | 中 | **purpose/content/sourceRef** | 强 |
| Provider independence | 中 | 中 | **高** | 高 |
| Host complexity | 低起步、高返工 | 中 | 中且职责清楚 | 高 |
| Java impact | 低 | Scene convention | **Media contract 小改** | 新 Domain 大改 |
| Tool impact | 无 | 无 | **existing Media tools only** | 新 CRUD |
| Skill impact | 扩大 Shot skill | Scene skill 污染 | **one audio-production Skill** | 新 Skill + Domain |
| Subtitle/lip-sync | 跨 Shot弱 | 好 | **好** | 好 |
| 结论 | DROP | 不作为 canonical | **RECOMMENDED** | DEFER |

## 33. Recommended Minimal Audio Architecture

```text
Work.content.historicalActorHierarchy[].speakerKey       [Java open content]
Work.content.voiceProfiles[]                              [Java open content]
Work.content.pronunciationGuidance[]                      [Java open content]
                 ↓
Scene.content.spokenContent[]                             [AUTHORITATIVE TEXT]
                 ↓ spokenContentId/textHash
Shot.content.spokenContentBindings[]                      [VISUAL COVERAGE]
                 ↓
Audio Host / audio-production Skill
  resolve voice profile + provider mapping
  compile exact text + pronunciation + render controls
                 ↓
Speech Provider Adapter                                   [replaceable Provider]
                 ↓
review + ffprobe actual duration
                 ↓
Media(AUDIO/SPEECH_CLIP, shotId=null)                     [Java + MinIO]
                 ↓ reusable clip refs
Audio/AV Assembly Manifest                                [Host]
                 ↓
Media(AUDIO/SHOT_DIALOGUE_MIX, shotId=<shot>)             [optional durable mix]
                 +
Media(VIDEO/FINAL silent source, immutable)
                 ↓ Host mux utility / future assembly provider
Media(VIDEO/FINAL_AV, new identity)                       [Java + MinIO]
```

职责：Host 做 reasoning、voice resolution、timeline/reconciliation/review；Skill 定义方法和 gates；Provider 只 render；Java 持久化 stable Work/Media；MinIO 保存物理对象。

## 34. Recommended Minimal Schema

### MUST HAVE — Work voice registry

```json
{
  "voiceProfiles": [
    {
      "speakerKey": "speaker:example",
      "profileId": "voice-profile-example",
      "creativeProfile": {
        "agePresentation": "",
        "timbre": "",
        "temperament": "",
        "baselinePace": "",
        "power": "",
        "restraint": "",
        "language": "zh-CN"
      },
      "providerMappings": [
        {
          "provider": "",
          "model": "",
          "voiceId": "",
          "mappingFingerprint": "",
          "status": "APPROVED"
        }
      ]
    }
  ]
}
```

### MUST HAVE — Speech clip Media content

```json
{
  "schemaVersion": "audio-v1",
  "sceneId": "scene-id",
  "spokenContentId": "spoken-id",
  "speakerKey": "speaker:key",
  "textHash": "sha256",
  "voiceProfileFingerprint": "sha256",
  "providerMappingFingerprint": "sha256",
  "pronunciationFingerprint": "sha256",
  "audioInputFingerprint": "sha256",
  "provider": {"name": "", "model": "", "jobId": ""},
  "actualDurationMs": "FROM_MEDIA_DURATION_MS",
  "reviewStatus": "PASS"
}
```

Envelope：`mediaType=AUDIO`、`purpose=SPEECH_CLIP`、`workId=<work>`、`shotId=null`、`assetId=null`。

### MUST HAVE — Assembly / Final AV content

```json
{
  "schemaVersion": "av-assembly-v1",
  "sourceVideoMediaId": "silent-video-media-id",
  "audioMixMediaId": "audio-mix-media-id",
  "speechClipMediaIds": ["clip-a", "clip-b"],
  "timeline": [
    {"spokenContentId": "spoken-id", "audioMediaId": "clip-id", "startMs": 0, "sourceInMs": 0, "sourceOutMs": "ACTUAL"}
  ],
  "finalAvFingerprint": "sha256",
  "reviewStatus": "PASS"
}
```

### OPTIONAL LATER

- multiple language variants；
- Scene dialogue mix；
- ambience/SFX/Foley/music tracks；
- loudness/spatial/ducking metadata；
- phoneme alignment；
- subtitle cue Media；
- provider-specific advanced parameters；
- independent Audio/Voice Entities。

## 35. Full Data Flow

```text
Work actor/narrator speakerKey                     Java persistence
  └─ Work voiceProfiles + pronunciation guidance  Java persistence
          ↓ Host resolves approved mapping
Scene spokenContent exact text                     Java authoritative content
          ↓ spokenContentId + canonical textHash
Shot spoken bindings / plannedDurationMs           Java visual coverage
          ↓
Audio production plan                              Host Run Context/artifact
          ↓ exact text + rendering controls only
Speech provider                                    Provider
          ↓ bytes + provider metadata
Text/voice/pronunciation/duration review            Host + Skill
          ↓
Speech Clip Media                                  Java Media + MinIO
          ↓
Assembly timeline / pause reconciliation           Host
          ↓
Dialogue Mix Media                                 Java Media + MinIO
          + immutable Silent Video Media
          ↓ deterministic mux
Final AV Media                                     Java Media + MinIO
          ↓ resolve/hash/review
Subtitle/lip-sync projections later                Consumers
```

## 36. Shot 1-03 Dry Simulation

真实输入：

```text
Shot = shot_83db7eb53b2f49d3a58428d4659e584e
plannedDurationMs = 10500
silent Video Media = media_63787886dc85413c90207e17d68df520
silent video actual duration = 11041.667ms
audio streams = 0
```

结构模拟：

```text
spoken-s1-wangsili-proposal
  → speaker:wangsili
  → Work voice profile: REQUIRED, NOT YET CREATED
  → provider voice mapping: UNKNOWN_UNTIL_7.1/7.2
  → hypothetical SPEECH_CLIP A
  → estimatedDurationMs=5000
  → actualDurationMs=UNKNOWN_UNTIL_TTS

spoken-s1-geshuhan-refusal
  → speaker:geshuhan
  → Work voice profile: REQUIRED, NOT YET CREATED
  → provider voice mapping: UNKNOWN_UNTIL_7.1/7.2
  → hypothetical SPEECH_CLIP B
  → estimatedDurationMs=3200
  → actualDurationMs=UNKNOWN_UNTIL_TTS

clip A + reviewed pause + clip B
  → candidate visual coverage windows from existing review: first beat / second beat
  → committed start/end = UNKNOWN_UNTIL_TTS_AND_TIMELINE_REVIEW
  → hypothetical SHOT_DIALOGUE_MIX

media_63787886dc85413c90207e17d68df520 (immutable silent source)
  + hypothetical dialogue mix
  → hypothetical new FINAL_AV Media
```

验证：

```text
REPEAT_GENERATION_REQUIRED = NO; exactly one clip per spoken item
DIALOGUE_IMMUTABLE = YES
TWO_SPEAKER_VOICE_LINKAGE = REPRESENTABLE
ACTUAL_DURATION = REPRESENTABLE via Media.durationMs after 7.1 contract exposure
FINAL_AV = REPRESENTABLE as new VIDEO/FINAL_AV Media
DRY_SIMULATION_FAKED_ACTUAL_RESULT = NO
```

## 37. Gap Matrix

| Capability | Current support | Audio v1? | Current location | Gap | Recommended owner | 7.1 action |
|---|---|---:|---|---|---|---|
| speaker identity | YES | MUST | Work actor hierarchy | none | Work/Java | reuse |
| voice profile | NO | MUST | — | no durable persona | Work content | add convention/tests |
| provider mapping | NO | MUST | generic parameters only | no stable mapping | Work + adapter | add layered mapping |
| TTS | MOCK/EXTERNAL CANDIDATES | MUST | production Tool / Comfy | no real adapter | Provider/Host | adapter contract/preflight |
| pronunciation | NO | MUST | — | historic term risk | Work + adapter | minimal guidance convention |
| text fidelity | NO | MUST | Dialogue exact text only | no post-Audio gate | Skill/Host | fingerprint/review tests |
| actual duration | DB ONLY | MUST | MediaEntity.durationMs | import/result disconnected | Media/Java | expose/write/test |
| speech clip Media | STRUCTURAL | MUST | Media AUDIO | no purpose/content convention | Media + Skill | freeze v1 convention |
| cross-shot reuse | Dialogue supports | MUST | Shot bindings | Audio ownership absent | Skill/Media | shotId=null clip rule |
| timeline | NO | MUST | — | no assembly manifest | Host/Skill | minimal manifest |
| silence/pause | semantic only | MUST | performanceIntent | no placement | Host/Skill | v1 placement rule |
| AV mux | LOCAL UTILITY ONLY | MUST | Host ffmpeg 8.1.2 | no formal method/gate | Host/Skill | helper/preflight/tests |
| final AV Media | STRUCTURAL | MUST | Media VIDEO | no purpose/source convention | Media/Skill | FINAL_AV convention |
| staleness | NO | MUST | — | ID alone insufficient | Host/Skill | fingerprints |
| Audio review | NO | MUST | — | no rubric | audio-production Skill | add rubric |
| subtitle compatibility | Dialogue ready | NO | spoken text | timing absent | future consumer | preserve manifest |
| lip-sync compatibility | PARTIAL | NO | binding/coverage | actual timing absent | future consumer | preserve timing/speaker |
| SFX | external candidate | NO | Comfy sound generation | out of v1 | future Audio | DEFER |
| ambience | NO | NO | — | out of v1 | future Audio | DEFER |
| music | external candidate | NO | Comfy templates/nodes | out of v1 | future Audio | DEFER |

## 38. Batch 7.1 Impact Scope

建议最小文件范围：

**Drama Plugin**

- 新增 `plugin/docs/audio-layer-content-convention.md`；
- 新增单一 `plugin/skills/audio-production/SKILL.md` 及最多一份 production/review reference；
- Media contract 增加可选 physical metadata；
- existing Tool catalog/import/list 参数小幅扩展；
- Audio schema/fingerprint/Skill semantic tests；
- 可选小型 deterministic mux helper + unit tests。

**Drama Service**

- `MediaDtos`、`MediaImportService`、`MediaToolApiImpl`、Controller 的既有 contract 小改；
- 写入/返回现有 `duration_ms/mime/hash/size`；
- import deterministic `source_ref` 与 list filters；
- Audio MIME、idempotency 与 round-trip tests；
- **不改 DB schema**。

**Drama MCP Service**

- 只因 Plugin schema 自动透传；更新 protocol/adapter tests；
- 不新增 media-specific wrapper。

**Skills**

- Scene/Shot/Work Skills 只做最小 boundary reference；
- Shot Production 保持视觉为主，显式委派 speech/timeline/mux 给新 Audio Skill；
- 不拆 voice-casting/TTS/review/mix/mux 多个微 Skill。

## 39. Batch 7.1 Minimal Implementation Plan

1. 冻结 `audio-layer-content-convention.md`：ownership、purposes、voice registry、pronunciation、fingerprints、timeline、immutable source video。
2. 新增一个 `audio-production` Skill：Gather → voice resolve → exact-text compile → provider preflight → generation → review → duration → Media import → timeline → mux → Final AV；本批实现方法，不调用付费任务。
3. 在 Work open content convention 中允许 `voiceProfiles[]` 和 `pronunciationGuidance[]`；不修改 Dialogue convention 正文职责。
4. 加固现有 Media import/result/list：duration、physical metadata、deterministic sourceRef、work/purpose/sourceRef filters。
5. 定义 `AUDIO_INPUT_FINGERPRINT` 与 `FINAL_AV_FINGERPRINT` canonicalization。
6. 定义 `SPEECH_CLIP/SHOT_DIALOGUE_MIX/FINAL_AV` purposes 和 required content。
7. 实现/测试 Host ffmpeg capability wrapper 或严格 recipe；无 ffmpeg 时明确 `AV_ASSEMBLY_CAPABILITY_MISSING`。
8. 实现 provider adapter seam / structured request tests，但不在 7.1 自动提交真实 TTS。
9. 测试矩阵覆盖：actor/narrator、两 speaker、跨 Shot reuse、text/performance/voice/pronunciation stale、duration missing/invalid、Audio MIME、idempotent import、source video immutable、Final AV fingerprint、no Dialogue mutation。

建议判定：

```text
NEW_AUDIO_PRODUCTION_SKILL_REQUIRED = YES
PROVIDER_ADAPTER_REQUIRED = YES
JAVA_CHANGE_REQUIRED = YES, minimal existing Media contract hardening
NEW_DATABASE_TABLE_REQUIRED = NO
NEW_DOMAIN_TOOL_REQUIRED = NO
MEDIA_CONVENTION_REQUIRED = YES
```

## 40. Batch 7.2 Single-Shot E2E Plan

Shot 1-03 适合作为首个真实样本，因为它同时具备：两个已 Review speaker、两个 ON_SCREEN bindings、不同 performance intent、8,200ms spoken estimate、10,500ms planned window、11.041667s 已审静音视频、稳定 final Video Media 与完整 MinIO/hash 证据。它能一次验证 voice distinction、pause、duration reconciliation 和 AV assembly，不需要扩大到多 Scene。

建议流程：

1. 只读重读 Work/Scene/Shot/Video；
2. Review 两个 Work voice profiles/provider mappings/pronunciations；
3. 设置明确 per-provider Audio budget 和成功即停 gate；
4. 每个 spoken item 生成一次 speech clip；
5. text/voice/pronunciation/performance/actual-duration Review；
6. import 两个 SPEECH_CLIP Media，MinIO/resolve/hash；
7. 构建 basic pause/silence timeline 和 SHOT_DIALOGUE_MIX；
8. 对 immutable silent video 做新 AV mux；
9. import new FINAL_AV Media，验证 video+audio streams、duration、resolve/hash、fingerprints；
10. 成功一个 Shot 即停止。

v1 PASS 聚焦：Dialogue source、voice identity、text fidelity、pronunciation、actual duration、timeline、AV mux、Media/MinIO/Resolve/Hash。明确排除 precise lip-sync、subtitle、BGM、SFX、Foley、complex mix。

## 41. Risks / Deferred Items

- Provider 对中文古名的发音、停顿与速度控制差异大；需 7.2 实测后定阈值。
- 当前 Media content 可承载 `sceneId`，但缺少 envelope/query；规模超过 list/sourceRef 能力后再评估，不提前加列。
- Voice profiles 写入 Work 需遵守 full replacement safety，避免覆盖历史内容。
- Provider voiceId 可能下线；mapping status/fingerprint 必须可更新且不改变 creative profile。
- ASR 对专名可能误判，不能单独作为 fidelity 最终裁决。
- ffmpeg 在当前 macOS 可用，不代表所有 Host 可用；必须 capability preflight。
- 当前 production Tool generic prompt contract 过宽；7.1 需用 Skill/adapter structured request 约束，未来是否新增 `generate_speech` capability Tool 视真实 adapter 需要 DEFER，而非 Audio CRUD。
- 独立 Audio Entity、Voice Entity、Scene mix、language variants、precise lip-sync、subtitle production、full sound design 全部 DEFER。

## 42. Final Decision Matrix

```text
AUDIO_LAYER_REQUIRED = YES
CURRENT_AUDIO_SUPPORT = PARTIAL
PRIMARY_AUDIO_GAP = no durable voice profile/provider mapping and no real reviewed TTS-to-Media-to-AV flow

RECOMMENDED_AUDIO_SOURCE_MODEL = Scene canonical spokenContent + Work voice registry + spoken-item Speech Clip Media + separate AV assembly manifest

INDEPENDENT_AUDIO_ENTITY_REQUIRED = NO
NEW_DATABASE_TABLE_REQUIRED = NO
NEW_DOMAIN_TOOL_REQUIRED = NO
NEW_AUDIO_PRODUCTION_SKILL_REQUIRED = YES

VOICE_PROFILE_REQUIRED = YES
VOICE_PROFILE_OWNERSHIP = Work.content.voiceProfiles[] keyed by work-scoped speakerKey
PROVIDER_VOICE_MAPPING_REQUIRED = YES
PRONUNCIATION_LAYER_REQUIRED = YES

SPEECH_AUDIO_MEDIA_REQUIRED = YES
AUDIO_ACTUAL_DURATION_REQUIRED = YES
AUDIO_TIMELINE_REQUIRED = YES
FINAL_AV_MEDIA_REQUIRED = YES
SOURCE_VIDEO_IMMUTABLE = YES

AUDIO_INPUT_FINGERPRINT_REQUIRED = YES
FINAL_AV_FINGERPRINT_REQUIRED = YES
TEXT_FIDELITY_GATE_REQUIRED = YES

PRECISE_LIP_SYNC_REQUIRED_FOR_V1 = NO
SUBTITLE_REQUIRED_FOR_V1 = NO
BGM_SFX_REQUIRED_FOR_V1 = NO

BATCH_7_1_RECOMMENDED = YES
BATCH_7_2_RECOMMENDED = YES

CURRENT_LONG_TERM_MEMORY_SERVICE = current workspace drama-service
CURRENT_PLUGIN = current workspace drama-plugin
CURRENT_MCP = current workspace drama-mcp-service
OLD_DIFY_DSL = /Users/yizhao/IdeaProjects/AI_historical/src/main/resources/dify_dsl REFERENCE ONLY
AI_HISTORICAL_RUNTIME_DEPENDENCY = NO

CODE_CHANGED = NO
PRODUCTION_DATA_CHANGED = NO
PRODUCTION_CHECKPOINT_CHANGED = NO
CREDIT_LEDGER_CHANGED = NO

AUDIO_GENERATION = 0
VIDEO_GENERATION = 0
IMAGE_GENERATION = 0
TTS_GENERATION = 0
COMFY_PAID_GENERATION = 0
CREDIT_CONSUMPTION = 0

BATCH_7_0 = PASS
```

**STOP：未自动进入 Batch 7.1 或 Batch 7.2。**
