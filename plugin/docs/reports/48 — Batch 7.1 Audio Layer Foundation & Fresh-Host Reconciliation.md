# 48 — Batch 7.1 Audio Layer Foundation & Fresh-Host Reconciliation

执行日期：2026-08-24（Asia/Shanghai）

性质：AUDIO LAYER FOUNDATION + FRESH-HOST RECONCILIATION

结论：**BATCH_7_1 = PASS；BATCH_7_2_READY = YES（仅表示 7.2 prerequisites 已验证；本批未进入 7.2）**

## 1. 执行摘要

本批在新 macOS Host 上完成了 Audio v1 的内容约定、结构化 Speech request、Provider seam、确定性 fingerprint/sourceRef、Media contract 加固、单一 `audio-production` Skill、Host probe/mux helper、assembly manifest、Fake Provider 与 synthetic WAV 测试。

没有执行真实 TTS、图像、视频或 Audio AI 生成；没有调用 Comfy Cloud；没有调用付费 Provider；没有消费 credits；没有进入 Batch 7.2。

首次执行时 Java/Maven 与 `ffmpeg`/`ffprobe` 不可用；用户随后准备了 Java 17、IntelliJ IDEA 内置 Maven 与 ffmpeg/ffprobe，本批在同一 fresh-host reconciliation 上恢复执行。当前 Host 已完成 Java tests、ffprobe physical probe、synthetic AV mux，以及经现有 MySQL/MinIO 配置的 synthetic Audio Media round-trip。因此本报告没有把 Batch 7.0 的旧 Artifact、Media、MinIO Object 或 runtime PASS 冒充当前结果。

## 2. Fresh-host reconciliation

### CURRENT_HOST_VERIFIED

- workspace 中存在 `drama-plugin`、`drama-service`、`drama-mcp-service` 三个独立 Git 仓库；
- 开始时 `drama-plugin` 与 `drama-mcp-service` clean；
- `drama-service/server/src/main/resources/application.yml` 开始时已有用户修改，本批未编辑、回滚、覆盖或提交该文件；
- workspace 开始时没有可复用的旧 Batch 6/7 runtime Artifact；本批只新建 `artifacts/batch7-1/`；
- 新 Artifact Root 只包含 synthetic fixtures、evidence JSON、hash、capability state 与 validation summary。

### HISTORICAL_EVIDENCE

Batch 7.0 报告是可信 architecture input，但其旧 Artifact Root：

```text
/Users/yizhao/PyProject/historical_plugin/artifacts/batch6-0re2e
```

以及报告中的旧 `mediaId`、旧 MinIO Object、旧 Shot Video、checkpoint、ledger 全部标记为：

```text
HISTORICAL_EVIDENCE_ONLY
```

本批没有读取、寻找、恢复或重建这些对象，也没有把旧 runtime PASS 用作当前验证。

### CURRENT_HOST_VERIFIED（恢复执行后）

```text
JAVA_RUNTIME = OPENJDK_17.0.20.1_TEMURIN
MAVEN = 3.9.16_INTELLIJ_BUNDLED
DRAMA_SERVICE_8080 = STARTED_FOR_VALIDATION_THEN_GRACEFULLY_STOPPED
MYSQL = REACHABLE_THROUGH_EXISTING_APPLICATION_CONFIG
MINIO_9000 = LISTENING
FFMPEG = 9.0.1
FFPROBE = 9.0.1
```

## 3. Audio v1 content convention

新增 `plugin/docs/audio-layer-content-convention.md` 并冻结：

1. `Scene.content.spokenContent[].text` 是唯一授权 Dialogue；Audio 不得改写、增删或把 pronunciation/provider syntax 写回正文。
2. `Work.content.voiceProfiles[]` 由 Work-scoped `speakerKey` 拥有，actor 与 narrator 同等支持。
3. `creativeProfile` 是长期稳定声音身份；`providerMappings[]` 是可替换实现；更换 Provider 不得修改 creative profile。
4. `Work.content.pronunciationGuidance[]` provider-agnostic；pinyin、SSML、phoneme 或词典语法只存在于 adapter boundary。
5. `SPEECH_CLIP` 是 Work-owned、`shotId=null`、`assetId=null` 的一个 spoken item 对应一个 reusable Audio Media。
6. `SHOT_DIALOGUE_MIX` 是 derivative；`FINAL_AV` 是新的 VIDEO Media identity；silent source Video immutable。
7. `Shot.content.spokenContentBindings[]` 继续是唯一 visual coverage semantic；Audio 没有新增平行 coverage enum。

## 4. Structured Speech request 与 Provider abstraction

新增 provider-neutral contracts：

- `CreativeVoiceProfile`
- `ProviderVoiceMapping`
- `VoiceProfile`
- `PronunciationGuidance`
- `TargetTimingPolicy`
- `SpeechGenerationRequest`
- `SpeechGenerationResult`
- `SpeechProvider` protocol

`SpeechGenerationRequest` 明确包含 exact text、spokenContentId、speakerKey、creative voice profile、selected approved provider mapping、pronunciation guidance、performance intent、material render parameters 与 timing policy。

没有新增 `production.generate_speech` Tool。现有 Tool code 仍为：

```text
production.generate_audio
```

但 Tool 输入已改为 typed `SpeechGenerationRequest`。`StructuredSpeechProductionAdapter` 将 exact text 和完整 structured request 一起交给现有 `ProductionProvider.generate_audio` seam；exact text 不再只存在于自由 prompt。`MockSpeechProvider` 与现有 `MockProductionProvider` 只在离线测试中验证 request/response 和 adapter handoff，没有真实 Provider invocation。

Skill Core 不含 vendor、具体 server、transport 或 provider-specific pronunciation syntax。未来 HTTP-backed 或 MCP-backed TTS 只需实现 seam/adapter，不改变 Skill。

## 5. Fingerprint、freshness 与 retry

实现 canonical JSON：UTF-8、Unicode preserved、sorted keys、compact separators、reject non-finite numbers；实现 SHA-256：

```text
AUDIO_INPUT_FINGERPRINT = SHA-256(canonical JSON)
```

material 至少包含：

```text
schemaVersion
workId
sceneId
spokenContentId
textHash
speakerKey
performanceIntentHash
voiceProfileFingerprint
providerMappingFingerprint
pronunciationFingerprint
provider
model
materialRenderParameters
targetTimingPolicy
```

测试确认 text、speaker、performance、creative voice、provider mapping、pronunciation、render parameters、timing policy 任一 material change 都 stale；display label、operator note、timestamp、guidance note、run label 等 non-material metadata 不 stale。

sourceRef 冻结：

```text
PASS current reusable result = audio-input:<fingerprint>
FAILED/PENDING/DEBUG candidate = audio-attempt:<fingerprint>:<attempt-id>
```

FAILED attempt 不占 canonical key，不阻塞 retry；继续沿用既有唯一 `Media.sourceRef`，没有新增 idempotency table。

## 6. Media contract hardening

### Drama Plugin

`Media` 稳定暴露：

```text
durationMs
mimeType
fileSize
contentHash
```

`media.import_media` 增加可选 `source_ref` 与 positive `duration_ms`；`media.list_media` 增加 `work_id/purpose/source_ref` filters；HTTP 与 Mock provider mapping 已同步。

### Drama Service

在既有 `MediaEntity.durationMs` / `drama_media.duration_ms` 上接通：

- import metadata → `durationMs`；
- `MediaDtos.Result` → duration/MIME/size/hash；
- deterministic import `source_ref` 与 duplicate retry；
- AUDIO 必须 `audio/*`；
- `FINAL_AV` 必须 `mediaType=VIDEO` 且 `video/*`；
- list type/work/purpose/sourceRef filters。

```text
DB_SCHEMA_CHANGE = NO
NEW_DATABASE_TABLE = NO
NEW_AUDIO_CRUD_TOOL = NO
NEW_AUDIO_IDEMPOTENCY_TABLE = NO
```

Java unit/integration tests 已用 Java 17 与 IntelliJ IDEA 内置 Maven 执行：

```text
JAVA_MEDIA_TESTS = PASS
TESTS = 33
FAILURES = 0
ERRORS = 0
SKIPPED = 0
```

## 7. Authoritative actual duration

冻结：

```text
Scene.spokenContent.estimatedDurationMs != Media.durationMs
Provider duration = INFORMATIONAL_ONLY
Media.durationMs = HOST_PROBED_PHYSICAL_DURATION
```

Java 只接收/校验/持久化 positive `durationMs`，不运行 `ffprobe`。Host helper 使用当前 Host 的 `ffprobe 9.0.1` 探测两个 WAV；measured duration 均与 expected duration 相等。Python standard-library `wave` 仍作为 WAV fallback/交叉检查，不是本轮 evidence 的主 probe。

## 8. Synthetic Audio evidence

全部为 `SYNTHETIC_TEST`，不是 Dialogue Audio，不是 AI generation：

| fixture | 类型 | fileSize | SHA-256 | expected | measured | probe |
|---|---:|---:|---|---:|---:|---|
| `test-1s.wav` | deterministic 440 Hz waveform | 32,044 | `78112ce72576feab43cdb556c28d1df4fd1e32fc23936cf5d4d896a0d5b03b63` | 1,000ms | 1,000ms | `ffprobe 9.0.1` |
| `test-2s.wav` | deterministic silence | 64,044 | `20eaebffe1816e0ffa6f7f854f5ef4ea80d5349faaf0ce1fec1b713e7fde58fa` | 2,000ms | 2,000ms | `ffprobe 9.0.1` |

生成脚本重复运行后两个 SHA-256 未变化。

Evidence：

- `artifacts/batch7-1/evidence/synthetic-audio-fixtures.json`
- `artifacts/batch7-1/evidence/audio-fingerprint.json`
- `artifacts/batch7-1/evidence/host-capabilities.json`
- `artifacts/batch7-1/evidence/java-media-tests.json`
- `artifacts/batch7-1/evidence/synthetic-audio-media-roundtrip.json`
- `artifacts/batch7-1/evidence/synthetic-av-mux.json`
- `artifacts/batch7-1/validation-summary.json`

## 9. Host ffprobe / ffmpeg boundary

新增最小 Host helper，能够在 capability 存在时：

- probe duration 与 video/audio streams；
- capture implementation/version；
- mux immutable source Video + Audio 到新 output；
- capture deterministic settings；
- probe output streams/duration；
- hash inputs/output；
- confirm source Video hash unchanged。

当前 Host capability 与实际 synthetic mux：

```text
FFPROBE_CAPABILITY = PASS
FFMPEG_MUX_CAPABILITY = PASS
OUTPUT_STREAMS = H264_VIDEO_PLUS_AAC_AUDIO
OUTPUT_DURATION_MS = 2000
SOURCE_VIDEO_IMMUTABLE = TRUE
```

没有执行 brew install，没有静默 skip。实际生成 2 秒 synthetic black H.264 source Video，并把 2 秒 silent WAV mux 为新的 H.264 + AAC MP4；source hash 在 mux 前后均为 `cc348970913906cbce46af356372d4bf6506eef2ccfc3684c0058698061a28b7`，output hash 为 `ee9f358db28bc3097e4714aceec5cf0cfb02b0c3ebe6b6128f57465dfb0f70fc`。source path 未被覆盖。

## 10. Audio-production Skill

新增单一 `plugin/skills/audio-production/SKILL.md`，没有拆分 voice casting/TTS/review/mix/mux 微 Skill。流程覆盖：

```text
Gather
→ Resolve Voice
→ Compile Exact Speech Request
→ Provider Capability Preflight
→ Idempotency Check
→ Generate (only when separately authorized)
→ Text / Voice / Pronunciation Review
→ Probe Actual Duration
→ Import SPEECH_CLIP
→ Duration Reconciliation
→ Build av-assembly-v1
→ Optional SHOT_DIALOGUE_MIX
→ AV Mux
→ Import FINAL_AV
→ Resolve / Hash / Review
```

本批按 foundation/dry-run boundary 在真实 Generate 前停止。Skill quick validation：`PASS`。

## 11. AV assembly / FINAL_AV

`AvAssemblyManifest(schemaVersion=av-assembly-v1)` 支持：

- `sourceVideoMediaId`
- `audioMixMediaId`
- `speechClipMediaIds`
- ordered `timeline[]`
- `spokenContentId/audioMediaId/startMs/sourceInMs/sourceOutMs`

unit test 验证同一个 `audioMediaId` 可被多个 timeline slice/Shot placement 复用。`FinalAvFingerprintInput` 包含 manifest、source Video hash、Audio hashes、mux implementation/version/settings；canonical final fingerprint deterministic。

`FINAL_AV` 可表示为新的 `Media(mediaType=VIDEO,purpose=FINAL_AV)`。source Video immutability 是 contract/helper hard gate；当前 Host 已完成 synthetic mux 与 stream/duration/hash 验证，但没有把该 fixture 冒充真实剧集 FINAL_AV。

## 12. Optional current-host Media round-trip

用现有 application 配置启动 `drama-service`，创建唯一 `SYNTHETIC_TEST` Work，将 `test-1s.wav` 以 `AUDIO/SPEECH_CLIP`、positive `durationMs=1000` 与 canonical `audio-input:<fingerprint>` sourceRef 导入 Media。随后完成 get、type/work/purpose/sourceRef 四条件 list、resolve、签名下载与三方 hash 对比；服务在验证后优雅关闭。

```text
SYNTHETIC_AUDIO_MEDIA_ROUNDTRIP = PASS
LOCAL_SHA256 = STORED_CONTENT_HASH = DOWNLOADED_SHA256
MIME_TYPE = audio/wav
DURATION_MS = 1000
```

本次创建的是新的 Work/Media/Object；没有读取、寻找、复用或恢复 Batch 7.0 历史 mediaId/object。evidence 不记录鉴权令牌、签名 URL、bucket 或 object key。

## 13. Test matrix

### CURRENT_HOST_VERIFIED / SYNTHETIC_TEST

| 检查 | 结果 |
|---|---|
| Plugin unit/integration | `118 passed` |
| Plugin mypy strict | `Success: no issues found in 38 source files` |
| Python compileall | PASS |
| `audio-production` quick validation | PASS |
| drama-mcp-service local suite | `23 passed, 1 skipped` |
| skipped MCP test | live OpenAI E2E；无 API key；本批禁止真实调用 |
| actor voice profile | PASS |
| narrator voice profile | PASS |
| creative profile / provider mapping separation | PASS |
| exact Dialogue request / no mutation | PASS |
| pronunciation separated from Dialogue | PASS |
| deterministic textHash/fingerprint | PASS |
| all material stale cases | PASS |
| non-material metadata freshness | PASS |
| canonical PASS / failed attempt retry refs | PASS |
| Fake Provider structured request/response | PASS |
| AUDIO/FINAL_AV MIME helper | PASS |
| missing/invalid/positive duration contract | PASS in Plugin and Java |
| Host-side WAV measured duration | PASS |
| Java Media tests | `33 passed, 0 failed, 0 errors, 0 skipped` |
| synthetic WAV → Java/MinIO/resolve/hash | PASS |
| ffprobe stream/duration probe | PASS |
| ffmpeg synthetic mux | PASS |
| cross-Shot clip reuse model | PASS |
| source-path immutability guard | PASS |
| FINAL_AV fingerprint/representation | PASS |
| no Audio CRUD Tool/table | PASS by code/schema audit |
| no paid/real Provider invocation | PASS |

### Intentionally not executed

| 检查 | 结果 |
|---|---|
| 真实 TTS / paid Provider | 不在 7.1 授权范围 |
| Comfy Cloud | 不在 7.1 授权范围 |
| 真实剧集 FINAL_AV | 7.1 仅验证 synthetic assembly boundary |

## 14. Batch 7.2 readiness answers

| 问题 | 回答 |
|---|---|
| Is structured `SpeechGenerationRequest` ready? | YES |
| Is Provider adapter seam ready? | YES |
| Can HTTP-backed TTS Provider be added without changing Skill? | YES |
| Can MCP-backed TTS Provider be added without changing Skill? | YES |
| Is voice identity durable? | YES, convention/contract ready in Work open content |
| Is pronunciation separated? | YES |
| Is fingerprint/idempotency ready? | YES |
| Can Audio Media persist actual duration? | YES; Java tests and current-host round-trip verified |
| Can synthetic Audio round-trip? | YES |
| Can Host perform deterministic AV mux? | YES; ffmpeg/ffprobe 9.0.1 verified |
| Is source Video immutable? | YES; actual synthetic mux hash verified |
| Is FINAL_AV representable? | YES |

因此当前 Host 已满足本报告定义的 7.2 execution prerequisites：

```text
BATCH_7_2_READY = YES
```

这不是自动进入 7.2 的授权。真实 TTS Provider 选择、调用、费用与单 Shot E2E 仍须在后续批次单独批准；本结论不依赖任何旧 Artifact 或旧 Media。

## 15. Final matrix

```text
BATCH_7_1 = PASS
FRESH_HOST_RECONCILIATION = PASS
AUDIO_CONTENT_CONVENTION = PASS
VOICE_PROFILE_CONVENTION = PASS
PRONUNCIATION_CONVENTION = PASS
STRUCTURED_SPEECH_REQUEST = PASS
PROVIDER_ABSTRACTION = PASS_FAKE_ONLY
AUDIO_INPUT_FINGERPRINT = PASS
SOURCE_REF_IDEMPOTENCY = PASS
MEDIA_DURATION_CONTRACT = PASS_CURRENT_HOST_VERIFIED
AUDIO_MEDIA_CONTRACT = PASS_CURRENT_HOST_VERIFIED
AUDIO_PRODUCTION_SKILL = PASS
FFPROBE_CAPABILITY = PASS
FFMPEG_MUX_CAPABILITY = PASS
SYNTHETIC_AUDIO_FIXTURE = PASS
SYNTHETIC_AUDIO_MEDIA_ROUNDTRIP = PASS
SOURCE_VIDEO_IMMUTABILITY = PASS_ACTUAL_SYNTHETIC_MUX
FINAL_AV_CONVENTION = PASS
REAL_TTS_GENERATION = 0
COMFY_CLOUD_USAGE = 0
PAID_PROVIDER_CALLS = 0
CREDIT_CONSUMPTION = 0
BATCH_7_2_READY = YES

DB_SCHEMA_CHANGE = NO
NEW_DATABASE_TABLE = NO
NEW_AUDIO_CRUD_TOOL = NO
IMAGE_GENERATION = 0
VIDEO_AI_GENERATION = 0
AUDIO_AI_GENERATION = 0
```

## 16. Deferred to 7.2 or later

```text
DEFERRED_TO_7_2 = REAL_TTS_PROVIDER_SELECTION_AND_SINGLE_SHOT_E2E
DEFERRED = TTS_MCP_INTEGRATION, PAID_HTTP_TTS, VOICE_CLONING,
           BGM, SFX, FOLEY, AMBIENCE, SPATIAL_AUDIO, DUCKING,
           PRECISE_LIP_SYNC, SUBTITLE_PRODUCTION, FORCED_ALIGNMENT,
           MASTERING, MULTI_SCENE_AUDIO_E2E
```

**STOP：未自动进入 Batch 7.2。**
