# 50 — Batch 7.2R Provider-Neutral Real TTS E2E

执行日期：2026-08-25（Asia/Shanghai）

性质：PROVIDER-NEUTRAL TTS ADAPTER + CREDENTIAL-GATED REAL E2E

结论：**离线实现与回归为 PASS；整批为 BLOCKED。阻塞项：`DASHSCOPE_API_KEY_AVAILABLE=NO` 且 `REAL_TTS_E2E_ENABLED=NO`。**

```text
BATCH_7_2R = BLOCKED
OFFLINE_PROVIDER_IMPLEMENTATION = PASS
REAL_QWEN_TTS = BLOCKED_BY_CREDENTIAL_AND_EXPLICIT_GATE
QWEN_REAL_TTS_CALLS = 0
OPENAI_REAL_TTS_CALLS = 0
```

没有用 Mock、旧 Audio 或 synthetic tone 冒充真实 Qwen Speech；没有创建伪造的 Audio timeline 或 AV preview；没有进入 Batch 7.3。

## 1. Current host 与执行边界

```text
JAVA = 17.0.20.1_TEMURIN
MAVEN = 3.9.16_INTELLIJ_BUNDLED
FFMPEG = 9.0.1
FFPROBE = 9.0.1
DASHSCOPE_API_KEY = UNSET
REAL_TTS_E2E = UNSET
```

Credential 审计只判断变量是否存在，从未输出、保存或写入 credential 值。用户已有 `drama-service/server/src/main/resources/application.yml` 及三个仓库全部既有未提交改动均保持不变；7.2R 没有修改 Java、Harness、Media schema 或 Skill。

## 2. Provider-neutral architecture

冻结后的结构：

```text
SpeechGenerationRequest
        ↓
resolve_speech_provider(mode, config, output_directory)
        ├── openai
        │     → OpenAiSpeechProvider
        └── bailian_qwen
              → BailianQwenSpeechProvider
```

`OpenAiSpeechProvider` 保留，既有 `/v1/audio/speech` 行为继续通过离线回归。resolver 只选择显式配置的 adapter，不做 Provider fallback、模型 fallback 或 dependency-injection framework。

配置边界：

```text
DRAMA_PLUGIN_PROVIDER_SPEECH_MODE=openai|bailian_qwen
OPENAI_API_KEY=<secret>
DASHSCOPE_API_KEY=<secret>
DRAMA_PLUGIN_SERVICE_SPEECH_OPENAI_BASE_URL=<url>
DRAMA_PLUGIN_SERVICE_SPEECH_BAILIAN_BASE_URL=<url>
DRAMA_PLUGIN_SERVICE_SPEECH_OUTPUT_DIRECTORY=<absolute review directory>
REAL_TTS_E2E=true
```

实现位置：

- `plugin/src/drama_plugin/providers/speech/openai.py`
- `plugin/src/drama_plugin/providers/speech/bailian_qwen.py`
- `plugin/src/drama_plugin/providers/speech/resolver.py`
- `plugin/src/drama_plugin/providers/speech/production.py`

切换只影响 provider adapter、provider configuration、provider mapping 与 fingerprint/result。Dialogue、creative profile、`audio-production` Skill、Java Media model 与 Media schema 不受影响。

## 3. Bailian Qwen HTTP adapter

本批冻结的真实配置目标：

```text
ACTIVE_PROVIDER = bailian_qwen
QWEN_MODEL = qwen3-tts-instruct-flash
TRANSPORT = non-realtime HTTP
VOICE_MODE = system voices
VOICE_A = Cherry
VOICE_B = Ethan
VOICE_CLONING = NO
VOICE_DESIGN = NO
REALTIME_WEBSOCKET = NO
```

阿里云百炼官方 API reference 将 `text`、`voice`、`language_type`、`instructions` 与 `optimize_instructions` 定义为 Qwen-TTS 输入字段，并说明非实时结果提供有效期 24 小时的 Audio URL：[Qwen-TTS API](https://help.aliyun.com/zh/model-studio/qwen-tts-api)。官方模型表确认 `qwen3-tts-instruct-flash` 是支持 instruction 的非实时 HTTP system-voice 模型，且不属于声音复刻或声音设计：[语音合成模型](https://help.aliyun.com/zh/model-studio/tts-model)。官方非实时音色表确认 `Cherry` 与 `Ethan` 均支持该模型和普通话：[Qwen-TTS 音色列表](https://help.aliyun.com/zh/model-studio/qwen-tts-voice-list)。

允许的 operator-selected fallback 是显式把 mapping model 改为 `qwen3-tts-flash`。adapter 不会在 API 失败时自动切换模型，也不会切到 OpenAI。该显式 fallback 不支持 instructions，报告必须按实际 operator selection 记录能力降级。

## 4. Exact Dialogue、instruction 与 fingerprint

Qwen compiler 固定：

```text
canonical Dialogue text
== SpeechGenerationRequest.exactText
== payload.input.text
```

`performanceIntent`、`creativeProfile` 与 material render controls 只编译到独立 `payload.input.instructions`；instruction 不包含 exact Dialogue 文本，不写回 Work/Scene。`optimize_instructions=false` 被显式发送，避免 provider 侧语义重写破坏可重复性。

本批没有 authoritative provider-specific pronunciation API，因此：

```text
PRONUNCIATION_PROVIDER_CONTROL = NOT_AVAILABLE
PRONUNCIATION_REVIEW = HUMAN_REVIEW_BOUNDARY
```

离线 fixture fingerprints：

```text
AUDIO_INPUT_FINGERPRINT_A = 4e6d4aff5e7167731098ddbff8738c19dc0125197200664701ee31da00949950
AUDIO_INPUT_FINGERPRINT_B = c5114ad151285c3be6f833d407c9c313f2321c5f56d444c9dbb2c812bdd755be
```

测试还证明：同一 Dialogue、同一 speaker、同一 creative profile 在 OpenAI mapping 与 Qwen mapping 下得到不同 Audio fingerprint；旧 OpenAI canonical Speech Clip 不会被当作 Qwen reusable result。切换不会修改 canonical Dialogue 或 creative profile。

## 5. HTTP、retry 与 ephemeral URL safety

生成 submission 规则：

- connect error/connect timeout：仅在提交尚未确认时有限重试；
- explicit 429/5xx：最多 `maxTransientRetries<=2`；
- read/write/pool timeout：立即 `ProviderResultUnknown`，不自动重复付费 submission；
- 4xx、无效 JSON、缺少 Audio URL：映射为不含 response body/secret/签名 URL 的 `SpeechProviderError`；
- 不做 OpenAI fallback，不做无限 retry。

成功 response 的签名 URL 只用于一次即时 GET。adapter 下载原始字节后写入本地 review directory，计算 SHA-256，并只返回本地 `file://` URI。metadata 允许保存 provider request ID、audio ID、model、voice、字节数、hash 与调用计数；不保存 URL、query、Authorization 或 credential。

下载 GET 是非付费、可重复的 retrieval，因此网络失败可以有限重试；一旦 generation 成功而下载最终失败，不会重新提交 generation，错误会保留非敏感 provider request ID 供排查。

## 6. Media 与 human review boundary

既有 `SpeechBackedProductionProvider` 继续执行：

```text
local review file
→ ffprobe physical Audio
→ durationMs
→ Media import
→ audio-attempt:<fingerprint>:<attempt-id>
→ reviewStatus=PENDING
```

adapter 现在同时提供 `responseSha256`，安全地冻结为 Media `audioSha256`。真正的 E2E 仍必须验证：

```text
local hash = stored contentHash = resolve/download hash
```

HTTP 200 不会提升 canonical PASS。只有人工听审后才能使用：

```text
audio-input:<fingerprint>
reviewStatus=PASS
```

FINAL_AV 同样保持：

```text
PENDING = final-av-attempt:<finalAvFingerprint>:<attempt-id>
PASS    = final-av:<finalAvFingerprint>
```

`USER_AUDIO_REVIEW_REQUIRED=YES` 是架构边界；当前没有真实 Audio，因此听审尚未到达且 `artifacts/batch7-2/review/` 正确为空。

## 7. Real E2E gate result

生成前硬门禁结果：

```text
DASHSCOPE_API_KEY_AVAILABLE = NO
REAL_TTS_E2E_ENABLED = NO
PRIMARY_GENERATIONS_ALLOWED = 2
PRIMARY_GENERATIONS_EXECUTED = 0
QWEN_RETRIES_EXECUTED = 0
```

因此本轮在任何真实 Qwen submission、fixture Work/Scene 创建、Media/MinIO import 之前停止：

```text
REAL_SPEECH_A = NOT_EXECUTED_CREDENTIAL_GATE
REAL_SPEECH_B = NOT_EXECUTED_CREDENTIAL_GATE
ACTUAL_DURATION_A = NOT_AVAILABLE
ACTUAL_DURATION_B = NOT_AVAILABLE
REAL_AUDIO_MEDIA_ROUNDTRIP = NOT_EXECUTED_CREDENTIAL_GATE
HASH_EQUALITY = NOT_EXECUTED_CREDENTIAL_GATE
AUDIO_TIMELINE = NOT_EXECUTED_CREDENTIAL_GATE
AV_PREVIEW = NOT_EXECUTED_CREDENTIAL_GATE
SOURCE_VIDEO_IMMUTABLE = NOT_EXECUTED_CREDENTIAL_GATE
```

未生成 black video，因为它必须按两个真实 Audio 的 ffprobe duration 动态确定长度；没有使用视觉 AI。

## 8. Agents SDK LLM provider-neutral design（design only）

本批只读审计当前 Harness 依赖 `openai-agents 0.22.0` 的本地安装源码：默认 `OpenAIProvider` 使用 OpenAI Responses；SDK 同时提供 `OpenAIChatCompletionsModel`、可注入 `AsyncOpenAI(base_url=...)` 的 client、抽象 `ModelProvider` 以及 `set_tracing_disabled`。Harness 代码未修改。

冻结设计：

```text
HarnessModelProviderResolver
  ├── openai
  │     → OpenAI Responses model
  └── bailian_qwen
        → OpenAI-compatible Chat Completions model
```

优先复用 SDK 已有 OpenAI-compatible Chat Completions integration；只有兼容能力不足时才实现完整 custom `ModelProvider`。不能因为能返回文本就声明 full compatibility。独立 Harness Provider batch 必须验证 tool calling、streaming、structured output、usage accounting、handoffs、system/developer instructions、context limits、error mapping 与 model settings；没有 OpenAI credential 时还必须禁用 OpenAI tracing 或配置替代 exporter。

```text
AGENTS_SDK_DEFAULT_PROVIDER = OPENAI_RESPONSES
AGENTS_SDK_NON_OPENAI_SUPPORTED = DESIGN_PATH_REQUIRES_VALIDATION
AGENTS_SDK_LLM_PROVIDER_NEUTRAL_DESIGN = PASS
HARNESS_LLM_PROVIDER_IMPLEMENTATION = DEFERRED_TO_SEPARATE_BATCH
```

## 9. Tests

```text
REAL_PROVIDER_FOCUSED_TESTS = 21 PASS
PLUGIN_TESTS = 139 PASS
PLUGIN_MYPY_STRICT = PASS_43_SOURCE_FILES
PYTHON_COMPILEALL = PASS
DRAMA_SERVICE_TESTS = 33 PASS, 0 FAILURE, 0 ERROR, 0 SKIP
DRAMA_MCP_SERVICE = 23 PASS, 1 SKIP
```

MCP 唯一 skip 是既有 live OpenAI E2E，原因是 `OPENAI_API_KEY unavailable`；本批明确要求 `OPENAI_REAL_TTS_CALLS=0`。Unit tests 的 HTTP 全部使用 `httpx.MockTransport`。

覆盖 resolver、OpenAI preserved、Qwen selected、unknown mode、Qwen config、missing credential、secret redaction、exact text、separate instructions、two voices、provider-specific fingerprint、success/URL/download、non-Audio、HTTP error、safe retry、ambiguous timeout、Media attempt/canonical semantics、OpenAI offline regression 与 Skill vendor-neutral regression。

## 10. Artifacts

```text
artifacts/batch7-2/
  evidence/
    provider-preflight-7.2r.json
    provider-neutrality-audit-7.2r.json
    agents-sdk-llm-provider-design-7.2r.json
    test-results-7.2r.json
  requests/
    speaker-a-qwen.redacted.json
    speaker-b-qwen.redacted.json
  review/       # empty: credential/gate blocked before generation
  manifests/    # empty: no real Audio timeline
  validation-summary-7.2r.json
```

7.2 的旧 evidence/request files 保留为 historical evidence，没有覆盖或复用。

## 11. Final matrix

```text
BATCH_7_2R = BLOCKED

SPEECH_PROVIDER_NEUTRAL = YES

OPENAI_PROVIDER_PRESERVED = YES
BAILIAN_QWEN_PROVIDER = PASS_OFFLINE
ACTIVE_PROVIDER = bailian_qwen

PROVIDER_SWITCHING = PASS
SKILL_VENDOR_NEUTRAL = YES
JAVA_PROVIDER_NEUTRAL = YES

REAL_QWEN_TTS = BLOCKED
TWO_SPEAKER_GENERATION = FAIL_NOT_EXECUTED_CREDENTIAL_GATE
EXACT_TEXT_INPUT = PASS_OFFLINE
ACTUAL_DURATION_PROBED = FAIL_NOT_EXECUTED_CREDENTIAL_GATE
REAL_AUDIO_MEDIA_ROUNDTRIP = FAIL_NOT_EXECUTED_CREDENTIAL_GATE
AUDIO_TIMELINE = FAIL_NOT_EXECUTED_CREDENTIAL_GATE
AV_MUX = FAIL_NOT_EXECUTED_CREDENTIAL_GATE

USER_AUDIO_REVIEW_REQUIRED = YES

OPENAI_REAL_TTS_CALLS = 0
QWEN_REAL_TTS_CALLS = 0
COMFY_CLOUD_USAGE = 0
IMAGE_AI_GENERATION = 0
VIDEO_AI_GENERATION = 0

AGENTS_SDK_LLM_PROVIDER_NEUTRAL_DESIGN = PASS
HARNESS_LLM_PROVIDER_IMPLEMENTATION = DEFERRED_TO_SEPARATE_BATCH
```

Batch 7.2R 到此停止；未进入 7.3。
