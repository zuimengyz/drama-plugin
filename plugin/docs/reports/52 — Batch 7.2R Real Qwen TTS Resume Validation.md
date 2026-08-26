# 52 — Batch 7.2R Real Qwen TTS Resume Validation

执行日期：2026-08-26（Asia/Shanghai）

性质：**Batch 7.2R continuation；不是 Batch 7.3**

结论：**BLOCKED**。Fresh-host 审计确认 DashScope credential 已声明且非空，但用户外部 env 中 `REAL_TTS_E2E` 未启用，`DRAMA_PLUGIN_PROVIDER_SPEECH_MODE` 也未解析为 `bailian_qwen`。根据 7.2R 显式门禁和 STOP 规则，本次没有发起 Qwen 或 OpenAI 真实 TTS 请求，没有用 Mock、旧 Audio 或 synthetic Audio 冒充真实结果。

```text
BATCH_7_2R = BLOCKED
PRIMARY_BLOCKER = BLOCKED_BY_REAL_TTS_E2E_GATE
SECONDARY_BLOCKER = ACTIVE_PROVIDER_NOT_BAILIAN_QWEN
QWEN_REAL_TTS_CALLS = 0
OPENAI_REAL_TTS_CALLS = 0
```

## 1. Evidence classification

```text
HISTORICAL_7_2R_OFFLINE_EVIDENCE = report 50
CURRENT_FRESH_HOST_VERIFIED = YES
REAL_QWEN_PROVIDER_RESULT = NOT_EXECUTED_GATE
REAL_AUDIO_MEDIA_RESULT = NOT_EXECUTED_GATE
SYNTHETIC_VIDEO_FIXTURE = NOT_CREATED
USER_AUDIO_REVIEW_PENDING = NOT_REACHED
```

50 号报告保留上一 Host 的历史证据，本报告不把其 PASS 项当作当前 Host 的运行结果。当前源码仍保留 `OpenAiSpeechProvider`、`BailianQwenSpeechProvider`、显式 resolver、structured request、exact-text compiler、provider-specific fingerprint、有限 safe retry、ambiguous-timeout 保护、临时 Audio URL 即时取回与 attempt/canonical Media 语义。

## 2. External env safety and gate

Env 文件的真实路径位于 `historical_plugin` workspace 顶层，不在 `drama-plugin`、`drama-mcp-service` 或 `drama-service` 任一 Git repository 内。本次没有复制、修改或输出其完整内容，没有输出 credential value。

安全审计结果：

```text
EXTERNAL_ENV_FILE_USED = YES_FOR_PREFLIGHT_ONLY
ENV_FILE_STORED_OUTSIDE_REPOSITORY = YES
DASHSCOPE_API_KEY_AVAILABLE = YES
REAL_TTS_E2E_ENABLED = NO
ACTIVE_PROVIDER = NOT_BAILIAN_QWEN
```

直接 shell `source` 该文件不能干净成功；其中至少一个值不符合 shell assignment 语法，会被 shell 解释为命令。为避免误执行或泄露，后续门禁审计使用了 `python-dotenv` 解析，仅输出 SET/UNSET、ENABLED/DISABLED 和 provider match 结果。因为本次没有进入真实 runtime，没有用非规定 loader 触发 Provider 请求。

## 3. Fresh-host toolchain and regression

```text
JAVA_RUNTIME = Temurin 17.0.19
MAVEN = 3.9.16
FFMPEG = 8.1.2
FFPROBE = 8.1.2
PYTHON_SYSTEM = 3.13.13
PLUGIN_TEST_PYTHON = 3.12.13

REAL_PROVIDER_FOCUSED_TESTS = 21 PASS
PLUGIN_TESTS = 139 PASS
PLUGIN_MYPY_STRICT = PASS_43_SOURCE_FILES
PLUGIN_COMPILEALL = PASS
DRAMA_MCP_SERVICE_TESTS = 13 PASS
DRAMA_MCP_SERVICE_MYPY = PASS_4_SOURCE_FILES
DRAMA_SERVICE_TESTS = 38 PASS, 0 FAILURE, 0 ERROR, 0 SKIP
```

Java regression 显式使用 Java 17；测试数以当前源码为准。Maven 测试的 persistence profile 是 H2 test profile，不冒充真实 MySQL E2E。

## 4. Runtime service preflight

不携带任何 credential 的连通性检查：

```text
CONFIGURED_MINIO_HEALTH = HTTP_200
CONFIGURED_MYSQL_TCP = REACHABLE
DRAMA_SERVICE_ENTRY = HTTP_502
DRAMA_MCP_HEALTH = UNREACHABLE
```

因此即使后续启用 TTS gate，真实 Media import/resolve/download round-trip 前仍需先恢复 Drama Service 与 MCP runtime。本次未自动启动或改配这些服务。

## 5. Real call and artifact result

```text
QWEN_MODEL_TARGET = qwen3-tts-instruct-flash
QWEN_VOICE_A_TARGET = Cherry
QWEN_VOICE_B_TARGET = Ethan
TRANSPORT_TARGET = NON_REALTIME_HTTP

QWEN_REAL_TTS_CALLS = 0
QWEN_REAL_TTS_RETRIES = 0
TWO_SPEAKER_GENERATION = FAIL_NOT_EXECUTED_GATE
EXACT_TEXT_INPUT = PASS_OFFLINE_CURRENT_HOST

REAL_AUDIO_A = FAIL_NOT_EXECUTED_GATE
REAL_AUDIO_B = FAIL_NOT_EXECUTED_GATE
ACTUAL_DURATION_A_MS = NOT_AVAILABLE
ACTUAL_DURATION_B_MS = NOT_AVAILABLE
REAL_AUDIO_MEDIA_ROUNDTRIP = FAIL_NOT_EXECUTED_GATE
HASH_EQUALITY_A = FAIL_NOT_EXECUTED_GATE
HASH_EQUALITY_B = FAIL_NOT_EXECUTED_GATE

USER_AUDIO_REVIEW_REQUIRED = YES_AFTER_REAL_GENERATION
AUDIO_TIMELINE = FAIL_NOT_EXECUTED_GATE
SYNTHETIC_VIDEO_FIXTURE = FAIL_NOT_CREATED_WITHOUT_REAL_AUDIO
AV_PREVIEW = FAIL_NOT_EXECUTED_GATE
SOURCE_VIDEO_IMMUTABLE = NOT_APPLICABLE_NO_VIDEO_CREATED
FINAL_AV_CANONICAL = PENDING
```

`artifacts/batch7-2/review/` 中没有新的 `speaker-a`、`speaker-b` 或 `speech-preview-final-av.mp4`；这是 gate 阻塞下的正确结果。

## 6. Final matrix

```text
BATCH_7_2R = BLOCKED

EXTERNAL_ENV_FILE_USED = YES_FOR_PREFLIGHT_ONLY
ENV_FILE_STORED_OUTSIDE_REPOSITORY = YES

DASHSCOPE_API_KEY_AVAILABLE = YES
REAL_TTS_E2E_ENABLED = NO

SPEECH_PROVIDER_NEUTRAL = YES
OPENAI_PROVIDER_PRESERVED = YES
ACTIVE_PROVIDER = NOT_BAILIAN_QWEN

QWEN_MODEL = qwen3-tts-instruct-flash (TARGET_NOT_EXECUTED)
QWEN_VOICE_A = Cherry (TARGET_NOT_EXECUTED)
QWEN_VOICE_B = Ethan (TARGET_NOT_EXECUTED)

QWEN_REAL_TTS_CALLS = 0
QWEN_REAL_TTS_RETRIES = 0

TWO_SPEAKER_GENERATION = FAIL_NOT_EXECUTED_GATE
EXACT_TEXT_INPUT = PASS_OFFLINE_CURRENT_HOST

REAL_AUDIO_A = FAIL_NOT_EXECUTED_GATE
REAL_AUDIO_B = FAIL_NOT_EXECUTED_GATE
ACTUAL_DURATION_A_MS = NOT_AVAILABLE
ACTUAL_DURATION_B_MS = NOT_AVAILABLE

REAL_AUDIO_MEDIA_ROUNDTRIP = FAIL_NOT_EXECUTED_GATE
HASH_EQUALITY_A = FAIL_NOT_EXECUTED_GATE
HASH_EQUALITY_B = FAIL_NOT_EXECUTED_GATE

USER_AUDIO_REVIEW_REQUIRED = YES_AFTER_REAL_GENERATION

AUDIO_TIMELINE = FAIL_NOT_EXECUTED_GATE
SYNTHETIC_VIDEO_FIXTURE = FAIL_NOT_CREATED
AV_PREVIEW = FAIL_NOT_EXECUTED_GATE
SOURCE_VIDEO_IMMUTABLE = NOT_APPLICABLE

FINAL_AV_CANONICAL = PENDING

OPENAI_REAL_TTS_CALLS = 0
COMFY_CLOUD_USAGE = 0
IMAGE_AI_GENERATION = 0
VIDEO_AI_GENERATION = 0
```

## 7. Resume requirements

继续同一 Batch 7.2R 前需要：

1. 在 repository 外的用户 env 中显式设置 `REAL_TTS_E2E=true`。
2. 设置 `DRAMA_PLUGIN_PROVIDER_SPEECH_MODE=bailian_qwen`。
3. 使 env 文件成为 shell-compatible assignment，或让 `scripts/load-env.sh` 支持显式 env-file 参数后用它安全加载。
4. 恢复 Drama Service 入口与 Drama MCP health；MinIO 和 MySQL 当前连通性已通过。

满足以上条件后，从真实 Qwen two-speaker generation 继续，仍遵守最多两次 primary generation、每项最多两次 safe transient retry、ambiguous result 不盲目重提，并在真实 Audio 生成后停在用户听审边界。
