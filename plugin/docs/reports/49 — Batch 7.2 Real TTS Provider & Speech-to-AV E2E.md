# 49 — Batch 7.2 Real TTS Provider & Speech-to-AV E2E

执行日期：2026-08-24（Asia/Shanghai）

性质：REAL TTS PROVIDER WIRING + CREDENTIAL-GATED E2E

结论：**BATCH_7_2 = BLOCKED；BLOCKER = REAL_TTS_CREDENTIALS_AVAILABLE=NO**

## 1. 执行摘要

本批完成了一个真实 HTTP TTS Provider 的最小 adapter、配置接线、secret redaction、结构化 payload 编译、有限安全重试、ambiguous-timeout 停止策略、Media canonical 幂等门禁、PENDING attempt 持久化边界，以及 FINAL_AV canonical/attempt sourceRef 约定。

当前 workspace、三个仓库 `.env`、runtime environment 与既有 Provider configuration 中均没有可用真实 TTS credential。按照 Batch 7.2 hard gate，执行在任何真实 Provider submission、Work/Scene 创建或 Media/MinIO 写入之前停止。没有用 Mock 冒充真实结果，没有生成真实 Speech，也没有继续构造伪造的 Audio timeline 或 AV preview。

```text
REAL_TTS_GENERATION = 0
REAL_TTS_CALL_COUNT = 0
REAL_TTS_RETRY_COUNT = 0
BATCH_7_2 = BLOCKED_BY_REAL_TTS_CREDENTIALS
```

## 2. CURRENT_HOST_VERIFIED

```text
JAVA = 17.0.20.1_TEMURIN
MAVEN = 3.9.16_INTELLIJ_BUNDLED
FFMPEG = 9.0.1
FFPROBE = 9.0.1
MINIO_9000 = LISTENING
DRAMA_SERVICE_8080_AT_PRECHECK = NOT_LISTENING
MYSQL_LOCAL_3306 = NOT_LISTENING
```

`drama-service` 当前 suite 使用 H2 test profile 通过 33/33。7.2 没有改动任何 Java 文件、Media schema 或用户已有 `application.yml`。由于真实 TTS credential gate 已阻塞 generation，本批没有重新访问外部 MySQL application profile，也没有启动一个不可能完成 Speech E2E 的持久化流程。

三个仓库的既有未提交改动均被保留；没有清理、覆盖、回滚或提交用户修改。Batch 7.0 的旧 Media/Object/visual artifacts 继续是 `HISTORICAL_EVIDENCE_ONLY`，没有读取、恢复或复用。

## 3. Real Provider discovery 与 credential safety

安全审计范围：

- `drama-plugin/.env.example`
- `drama-service/.env.example`
- `drama-mcp-service/.env.example`
- 三仓库内实际 `.env` / `.env.*`
- 当前进程 environment 的 TTS/Speech/OpenAI/Azure/Fish/Qwen/DashScope 等变量名
- Plugin config 与现有 `ProductionProvider`/`SpeechProvider` implementations

结果：

```text
ACTUAL_ENV_FILES = 0
REAL_TTS_CREDENTIALS_AVAILABLE = NO
EXISTING_REAL_SPEECH_ADAPTER_BEFORE_7_2 = NO
COMFY_CLOUD_EXCLUDED = YES
```

审计只输出变量名是否存在，不输出值。Artifacts 不包含 API key、Authorization、完整签名 URL、bucket 或 object key；没有创建或提交 `.env`。`.env.example` 只新增 placeholder。

## 4. 单一 Provider implementation

本批只实现：

```text
SpeechGenerationRequest
→ OpenAiSpeechProvider
→ POST /v1/audio/speech
→ original physical Audio file
```

没有同时接入第二个 Vendor，没有新增 TTS MCP Server，没有新增 `production.generate_speech`，继续使用：

```text
production.generate_audio
```

官方 OpenAI API reference 说明 Speech endpoint 使用独立 `input`、`model` 与 `voice` 字段，并支持 `instructions`、`response_format` 与 `speed`。本 adapter 将 `request.exactText` 原样放入 `input`；performance/pronunciation 只从 typed structured fields 编译进 adapter-side instructions，不把 Dialogue 降级为 free-form prompt-only 模式：[OpenAI Create speech API](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create)。

实现位置：

- `plugin/src/drama_plugin/providers/speech/openai.py`
- `plugin/src/drama_plugin/providers/speech/production.py`

配置边界：

```text
DRAMA_PLUGIN_PROVIDER_SPEECH_MODE=openai
DRAMA_PLUGIN_SERVICE_SPEECH_BASE_URL=<configured URL>
OPENAI_API_KEY=<secret>
DRAMA_PLUGIN_SERVICE_SPEECH_OUTPUT_DIRECTORY=<absolute review path>
DRAMA_PLUGIN_SERVICE_SPEECH_MAX_TRANSIENT_RETRIES=0..2
DRAMA_PLUGIN_REAL_TTS_E2E=true
```

`SecretStr`/repr redaction 与错误映射均禁止泄漏 credential 或 upstream response body。

## 5. Retry 与 ambiguous paid generation safety

实现规则：

- connect error/connect timeout：仅在 submission 未确认时有限重试；
- explicit 429 或 5xx：最多 `maxTransientRetries<=2`；
- read/write/pool timeout：立即 `ProviderResultUnknown`，不自动重新提交；
- 4xx：安全映射为不含 response body/secret 的 `SpeechProviderError`；
- 空文件、非 `audio/*`、requested format/MIME 不匹配：失败，不持久化为成功。

OpenAI Speech API reference 没有在本次核对页面中建立该 endpoint 的 documented idempotency key，因此 adapter 不伪造 Provider idempotency header。Drama-level pre-generation gate 仍先查 canonical `audio-input:<fingerprint>`；已有 `reviewStatus=PASS` 的 fresh Media 时真实 Provider call 为 0。

## 6. Structured request 与两 Speaker validation fixture plan

当前 credential gate 发生在数据库内容选择前，因此没有创建 Work/Scene。为了验证 adapter 编译与未来 E2E 输入，保存两个 redacted、非持久化 request plans：

```text
VALIDATION_FIXTURE = TRUE
NOT_PRODUCTION_DRAMA = TRUE
NOT_HISTORICAL_PROVENANCE = TRUE
```

| Item | speakerKey | exactText | provider mapping |
|---|---|---|---|
| A | `speaker:validation-a` | `军报已经送到，请将军决断。` | `openai / gpt-4o-mini-tts / marin` |
| B | `speaker:validation-b` | `军令未下，各部不得擅动。` | `openai / gpt-4o-mini-tts / cedar` |

两个 mapping 不同；这只证明 mapping/config 准备完成，不证明已经生成两个声音或两者听感不同。

```text
EXACT_TEXT_REQUEST = PASS_OFFLINE_PAYLOAD_EQUALITY
TWO_SPEAKER_MAPPINGS_PREPARED = YES
TWO_SPEAKER_GENERATION = BLOCKED
PRONUNCIATION_GUIDANCE_APPLIED = NO
PRONUNCIATION_REVIEW = N/A
```

没有 authoritative reviewed pronunciation guidance，因此不猜测或伪造发音。

## 7. Media、review 与 FINAL_AV gates

`SpeechBackedProductionProvider` 在真实调用前查询：

```text
mediaType=AUDIO
workId=<request.workId>
purpose=SPEECH_CLIP
sourceRef=audio-input:<audioInputFingerprint>
```

fresh PASS 命中时直接复用。新生成物在 physical ffprobe 成功后只以：

```text
audio-attempt:<fingerprint>:<attempt-id>
reviewStatus=PENDING
```

导入，不占 canonical PASS key。content 冻结 textHash、voiceProfileFingerprint、providerMappingFingerprint、pronunciationFingerprint、audioInputFingerprint、provider/model 与 actualDurationMs，但不保存 secret 或 Authorization。

Audio convention 现已补充：

```text
fully reviewed FINAL_AV = final-av:<finalAvFingerprint>
pending/failed preview = final-av-attempt:<finalAvFingerprint>:<attempt-id>
```

由于本批没有真实 Audio，以下步骤均正确停在 credential gate：

```text
SPEECH_CLIP_A = NOT_CREATED
SPEECH_CLIP_B = NOT_CREATED
REAL_AUDIO_MEDIA_ROUNDTRIP = NOT_EXECUTED_CREDENTIAL_GATE
AUDIO_TIMELINE = NOT_EXECUTED_CREDENTIAL_GATE
SYNTHETIC_VIDEO_FIXTURE = NOT_CREATED
AV_MUX = NOT_EXECUTED_CREDENTIAL_GATE
FINAL_AV_FINGERPRINT = NOT_COMPUTED
FINAL_AV_SOURCE_REF = PENDING
USER_AUDIO_REVIEW_REQUIRED = NOT_REACHED
```

`artifacts/batch7-2/review/` 与 `manifests/` 目录保持为空；没有用 synthetic 7.1 Audio 代替真实 TTS Audio。

## 8. Provider replacement proof

Architecture audit：

```text
PROVIDER_ABSTRACTION_PRESERVED = YES
SKILL_VENDOR_NEUTRAL = YES
JAVA_PROVIDER_NEUTRAL = YES
NEW_AUDIO_DOMAIN_TOOL = NO
TTS_MCP_REQUIRED = NO
JAVA_FILES_CHANGED_BY_7_2 = 0
MEDIA_SCHEMA_CHANGED_BY_7_2 = NO
```

未来替换 HTTP Provider 或改为 MCP-backed `SpeechProvider`，只需修改 provider adapter、provider configuration 与 provider mapping；Scene Dialogue、Work creative voice identity、`audio-production` Skill、Java Domain Model 与 Media schema 不需要变化。

`audio-production` Skill 的 7.2 最小更新只冻结 PENDING human-review boundary 和 FINAL_AV attempt/canonical 规则，不包含 `OpenAI` 或其他 Vendor 名称。

## 9. Tests

```text
REAL_PROVIDER_FOCUSED_TESTS = 11 PASS
PLUGIN_TESTS = 129 PASS
PLUGIN_MYPY_STRICT = PASS_41_SOURCE_FILES
PYTHON_COMPILEALL = PASS
AUDIO_PRODUCTION_SKILL_QUICK_VALIDATE = PASS
DRAMA_SERVICE_TESTS = 33 PASS, 0 FAILURE, 0 ERROR, 0 SKIP
DRAMA_MCP_SERVICE = 23 PASS, 1 SKIP
```

唯一 MCP skip 是 live OpenAI E2E，原因明确为 `OPENAI_API_KEY unavailable`；这与 credential discovery 一致。普通 unit suite 的 HTTP 全部使用 `httpx.MockTransport`，不会产生真实 API call。

覆盖点：config parsing、missing credential、secret redaction、structured request→payload、exactText unchanged、two mappings、HTTP success/error、429 retry、ambiguous timeout safety、Media idempotency、physical probe/import boundary、canonical/attempt refs、Skill vendor neutrality。

## 10. Artifacts

```text
artifacts/batch7-2/
  evidence/
    fresh-host-precheck.json
    host-capabilities.json
    provider-neutrality-audit.json
    provider-preflight.json
    test-results.json
  requests/
    speaker-a.redacted.json
    speaker-b.redacted.json
  review/       # empty: no credential, no real generation
  manifests/    # empty: no real Audio timeline
  validation-summary.json
```

## 11. Final decision matrix

```text
BATCH_7_2 = BLOCKED
BLOCKER = REAL_TTS_CREDENTIALS_AVAILABLE_NO

REAL_TTS_PROVIDER = BLOCKED
REAL_TTS_PROVIDER_TYPE = HTTP
REAL_TTS_CREDENTIALS_AVAILABLE = NO
REAL_TTS_CALL_COUNT = 0
REAL_TTS_RETRY_COUNT = 0
TTS_MCP_REQUIRED = NO

PROVIDER_ABSTRACTION_PRESERVED = YES
SKILL_VENDOR_NEUTRAL = YES
JAVA_PROVIDER_NEUTRAL = YES

TWO_SPEAKER_GENERATION = BLOCKED
EXACT_TEXT_FIDELITY_INPUT = PASS
PRONUNCIATION_REVIEW = N/A
VOICE_DISTINCTION_REVIEW = PENDING

REAL_AUDIO_PHYSICAL_VALIDATION = FAIL_NOT_EXECUTED_CREDENTIAL_GATE
REAL_AUDIO_MEDIA_ROUNDTRIP = FAIL_NOT_EXECUTED_CREDENTIAL_GATE
ACTUAL_DURATION_PROBED = FAIL_NOT_EXECUTED_CREDENTIAL_GATE

AUDIO_TIMELINE = FAIL_NOT_EXECUTED_CREDENTIAL_GATE
SYNTHETIC_VIDEO_FIXTURE = FAIL_NOT_EXECUTED_CREDENTIAL_GATE
AV_MUX = FAIL_NOT_EXECUTED_CREDENTIAL_GATE
SOURCE_VIDEO_IMMUTABLE = FAIL_NOT_EXECUTED_CREDENTIAL_GATE

FINAL_AV_FINGERPRINT = FAIL_NOT_EXECUTED_CREDENTIAL_GATE
FINAL_AV_CANONICAL_SOURCE_REF = PENDING

COMFY_CLOUD_USAGE = 0
COMFY_CLOUD_CREDIT_CONSUMPTION = 0
IMAGE_AI_GENERATION = 0
VIDEO_AI_GENERATION = 0
```

解除 blocker 需要在本机进程环境中提供一个已获授权、已有额度的 API key，并显式设置 `DRAMA_PLUGIN_REAL_TTS_E2E=true`。本批不会创建订阅、购买 credits 或代用户决定费用。

**STOP：未自动进入 Batch 7.3。**
