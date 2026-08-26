# 52 — Batch 7.2R Real Qwen TTS Resume Validation

执行日期：2026-08-26（Asia/Shanghai）

性质：**Batch 7.2R continuation；不是重新执行 Batch 7.2；不是 Batch 7.3**

结论：**READY_FOR_USER_AUDIO_REVIEW**。当前 Mac 已通过 runtime、服务、Provider neutrality 与离线回归门禁；正式 MCP → Plugin → Bailian Qwen → 本地物理探测 → Drama Service → MinIO 链路生成并持久化两段真实 Audio。技术验证通过后已立即停止，没有进入 timeline、AV mux、表演质量批准或 Batch 7.3。

```text
BATCH_7_2R = READY_FOR_USER_AUDIO_REVIEW
REAL_QWEN_TTS = PASS
QWEN_REAL_TTS_CALLS = 2
REAL_AUDIO_CREATED = YES
AUDIO_TECHNICAL_VALIDATION = PASS
USER_AUDIO_REVIEW = PENDING
BATCH_7_3 = NOT_STARTED
```

## 1. 本次目标

本次从 50/52 号报告记录的既有停止点恢复 Batch 7.2R。没有重新设计 Speech abstraction、resolver、OpenAI adapter、Bailian adapter、retry policy 或 Media contract；只完成 fresh-host reconciliation、直接 blocker 修复、必要回归与真实 two-speaker TTS E2E。

停止边界为：

```text
真实 Audio 已生成
→ 物理格式、时长、hash 与正式 Media round-trip 验证通过
→ 交给用户听审
→ STOP
```

## 2. Context Recovery

本次以当前 repository 与 artifacts 为事实来源，重点读取：

- 47 号 Batch 7.0 architecture/gap audit；
- 48 号 Batch 7.1 Audio foundation/fresh-host reconciliation；
- 49 号 Batch 7.2 credential-gated E2E；
- 50 号 Batch 7.2R provider-neutral implementation；
- 51 号 environment audit；
- 本报告上一版的 fresh-host BLOCKED 记录；
- `BailianQwenSpeechProvider`、`OpenAiSpeechProvider`、`resolve_speech_provider`；
- `SpeechBackedProductionProvider`、structured request、fingerprint、Media import；
- focused speech/retry/ambiguous-timeout tests；
- `run_batch7_2r_preflight.py` 与既有两 speaker fixture；
- `artifacts/batch7-2/` 的 request/evidence/summary；
- `drama-mcp-service` Settings、adapter、protocol tests；
- `drama-service` Media/HTTP 配置与当前未提交改动。

开始前状态：

```text
drama-plugin = CLEAN
drama-mcp-service = CLEAN
drama-service = 9 EXISTING USER MODIFICATIONS
```

`drama-service` 的 Media Java 文件、tests、operation doc 与 `application.yml` 改动在本次开始前已存在；本次未编辑、回滚或覆盖这些文件。

## 3. New Mac Preflight

### Repository / toolchain

```text
WORKSPACE = /Users/zy/historical-plugin
DRAMA_PLUGIN = PRESENT
DRAMA_MCP_SERVICE = PRESENT
DRAMA_SERVICE = PRESENT

PYTHON = 3.13.15
JAVA = 17.0.20.1
MAVEN = 3.9.16_INTELLIJ_BUNDLED
FFMPEG = 9.0.1
FFPROBE = 9.0.1
```

### Services

```text
DRAMA_SERVICE_AUTHENTICATED_PING = PASS
DRAMA_MCP_HEALTH = PASS
DRAMA_MCP_INITIALIZE = PASS
MCP_TOOL_COUNT = 45
PLUGIN_LOAD = PASS
MYSQL_TCP = PASS
MINIO_HEALTH = PASS
MCP_TO_JAVA_READ = PASS
```

连通性检查使用当前 runtime configuration 中的实际地址，不把它们无脑替换为 localhost。检查未输出 DB、Storage、Bearer 或 Provider secret。

独立验证 MCP 使用 `127.0.0.1:18765`，避免替换用户已有 8765 进程；真实 Audio 完成后该验证实例已停止。

## 4. MCP / Plugin Path Issue

### 结果

```text
PATH_ISSUE = REPRODUCED_AND_FIXED
```

### Root cause

`Settings.from_environment()` 对相对 `DRAMA_PLUGIN_ROOT` / `DRAMA_PLUGIN_CONFIG` 直接调用 `Path.resolve()`；解析基准因此是进程 CWD。相同配置：

```env
DRAMA_PLUGIN_ROOT=../drama-plugin/plugin
```

从 `drama-mcp-service/` 启动时存在，从 `drama-mcp-service/src/` 启动时解析到不存在的路径。这证明错误不是 `plugin.yaml` 内容非法，而是相对路径语义不稳定。

### Minimal fix

修改 `drama-mcp-service/src/drama_mcp_service/settings.py`：

- 定义稳定的 MCP `PROJECT_ROOT`；
- 绝对路径保持原语义；
- 相对 Plugin root/config 固定相对于 MCP project root 解析；
- sibling default 仍由 repository layout 推导，不硬编码用户名或机器路径。

### Regression

新增 CWD 变化测试。修复后从 `src/` 启动也解析到真实 sibling Plugin/config：

```text
PLUGIN_ROOT_EXISTS = TRUE
PLUGIN_CONFIG_EXISTS = TRUE
SETTINGS_TESTS = 3 PASS
```

## 5. Runtime Environment

用户 runtime 已迁移到 repository 外部：

```text
RUNTIME_ENV = ~/.config/historical-plugin/runtime.env
DIRECTORY_MODE = 0700
FILE_MODE = 0600
```

`scripts/load-env.sh` 已做最小修改以支持：

```bash
source scripts/load-env.sh <explicit-env-file>
```

bash/zsh 显式文件、带空格路径、正确引用的带空格值及 export 测试均 PASS。临时 migration copy 与先前 MCP-local `.env` 已移除，不再作为平行 Runtime Source。

脱敏状态：

```text
REAL_TTS_E2E = ENABLED
DRAMA_PLUGIN_PROVIDER_SPEECH_MODE = BAILIAN_QWEN
DASHSCOPE_API_KEY = PRESENT
DRAMA_PLUGIN_SERVICE_SPEECH_BAILIAN_BASE_URL = PRESENT_HTTPS
DRAMA_PLUGIN_SERVICE_SPEECH_OUTPUT_DIRECTORY = artifacts/batch7-2/review
DRAMA_PLUGIN_SERVICE_SPEECH_MAX_TRANSIENT_RETRIES = VALID_0_TO_2
```

没有把 runtime env、API key、Bearer token、签名 URL 或 Storage secret 写入 repository、artifact 或报告。

## 6. Provider Neutrality

实际 Plugin initialization：

```text
SpeechProvider = BailianQwenSpeechProvider
ProductionProvider = SpeechBackedProductionProvider
MediaProvider = HttpMediaProvider
FALLBACK = NO
```

架构边界保持：

- Skill Core 不含 OpenAI/Qwen/Bailian/DashScope vendor terms；
- MCP Tool 仍为 provider-neutral `production.generate_audio`；
- Java Work/Script/Episode/Scene/Shot/Media domain 不含 Qwen-specific logic；
- `resolve_speech_provider` 精确选择一个 adapter，不 fallback；
- OpenAI `/v1/audio/speech` adapter 保留并通过 offline regression；
- OpenAI 真实调用为 0；
- Qwen model/voice 只存在于 provider mapping 与 adapter boundary。

```text
PROVIDER_NEUTRALITY = PASS
OPENAI_REGRESSION = PASS
OPENAI_REAL_TTS_CALLS = 0
```

## 7. Real Qwen TTS E2E

正式链路：

```text
MCP Client
→ drama-mcp-service production.generate_audio
→ Drama Plugin structured Speech request
→ SpeechBackedProductionProvider
→ BailianQwenSpeechProvider
→ DashScope/Qwen non-realtime HTTP
→ immediate original Audio download
→ ffprobe
→ HttpMediaProvider.import_media
→ Drama Service
→ MySQL + MinIO
→ MCP media.resolve_media
→ download/hash verification
```

使用既有 Batch 7.2R fixture：

| item | speakerKey | voice | model | result |
|---|---|---|---|---|
| speaker A | `speaker:validation-a` | Cherry | `qwen3-tts-instruct-flash` | PASS |
| speaker B | `speaker:validation-b` | Ethan | `qwen3-tts-instruct-flash` | PASS |

Retry/cost accounting：

```text
GENERATION_ITEMS = 2
PRIMARY_GENERATION_LIMIT = 2
PRIMARY_GENERATION_ATTEMPTS = 2
PROVIDER_CALLS = 2
SAFE_TRANSIENT_RETRIES = 0
AMBIGUOUS_ATTEMPTS = 0
DOWNLOAD_CALLS = 2
```

没有外层 retry loop；safe retry 只由既有 Provider policy 控制。没有发生 ambiguous timeout，没有 fallback、model fallback 或 mock substitution。

为准确保存真实 retry evidence，`SpeechBackedProductionProvider` 仅补充持久化 provider-neutral 的 `providerCallCount`、`providerRetryCount`、`providerDownloadCallCount`、voice/audio IDs；没有保存 credential、Authorization、response URL 或 response body。

## 8. Audio Evidence

### Speaker A / Cherry

```text
artifact = artifacts/batch7-2/review/speech-1067d82ef6c5804105713dfb72d21a33e86a82946e8055643674ef66ae47aeb9-a91779e7059a4bf18fb80f28213c9064.wav
mediaId = media_a752827f6c7e4c3a843e2d1c34db8c35
fileSize = 138284
durationMs = 2880
codec = pcm_s16le
sampleRate = 24000
channels = 1
mimeType = audio/x-wav
sha256 = bab54789682c9e5d6217bbed885e05530d5b0554e1ed09b384f2eab10a099b14
reviewStatus = PENDING
```

### Speaker B / Ethan

```text
artifact = artifacts/batch7-2/review/speech-d824bb399c3a54f3942409c0d024c77f53309b390a8b20c5a89fc0f7e7b65149-af6ca3399ef0419a89417b92c94e0ec4.wav
mediaId = media_e0d60f8221b7468ebae22f388693a1b1
fileSize = 99884
durationMs = 2080
codec = pcm_s16le
sampleRate = 24000
channels = 1
mimeType = audio/x-wav
sha256 = 5c45b8a68e34e16150abbb5923053af3188b2840e7497f26ac05679ad9cc3865
reviewStatus = PENDING
```

两项均验证：

```text
provider original bytes > 0
local review SHA-256
= provider response SHA-256
= Java stored contentHash
= MinIO resolved download SHA-256

ffprobe duration > 0
Media.durationMs = ffprobe duration
audio stream present
exactTextInputVerified = true
```

主 evidence：

- `artifacts/batch7-2/evidence/real-qwen-tts-e2e-7.2r.json`
- `artifacts/batch7-2/evidence/resume-preflight-7.2r.json`
- `artifacts/batch7-2/evidence/test-results-7.2r.json`
- `artifacts/batch7-2/validation-summary-7.2r.json`

Artifact secret-pattern scan：PASS。

## 9. Tests

实际执行：

```text
sh scripts/test-load-env.sh
→ PASS (bash + zsh)

python -m pytest -q tests/test_real_speech_provider.py
→ 21 passed

python -m pytest -q
→ 139 passed

python -m mypy src/drama_plugin
→ PASS, 43 source files

python -m compileall -q src/drama_plugin integration/...
→ PASS

drama-mcp-service/.venv/bin/python -m pytest -ra
→ 14 passed

drama-mcp-service/.venv/bin/python -m mypy src/drama_mcp_service
→ PASS, 4 source files

IntelliJ bundled Maven 3.9.16: mvn test
→ 33 passed, 0 failure, 0 error, 0 skip
```

Focused tests覆盖 resolver、OpenAI preserved、Qwen selected、exact Dialogue、two voices、provider-specific fingerprint、ephemeral URL、safe 429 retry、ambiguous read timeout no retry、Media canonical/attempt semantics 与 Skill vendor-neutral audit。

## 10. Git Diff

### Batch 7.2R 最小必要修改

`drama-plugin`：

- 复用 preflight fixture builder；
- 新增 credential-gated、MCP-only 的 real E2E runner；
- Media content 持久化非敏感 provider call/retry evidence；
- ffprobe evidence 增加 sample rate/channels；
- 对应 focused test；
- 更新本报告。

`drama-mcp-service`：

- 修复 Plugin 相对路径依赖 CWD；
- 增加路径 regression；
- 移除 MCP 测试对旧 44 tool count 的硬编码，继续验证动态无损投影与 45-tool 当前 contract。

workspace scripts/artifacts：

- `load-env.sh` 支持 explicit env-file；
- 新增最小 bash/zsh loader test；
- 更新既有 `artifacts/batch7-2/` evidence/summary/review，不建立平行目录。

### 明确未修改

```text
Skill Core vendor boundary = UNCHANGED
Tool code / domain contract = UNCHANGED
OpenAI provider behavior = UNCHANGED
Java source by this resume = UNCHANGED
DB schema = UNCHANGED
Batch 7.3 = NOT_STARTED
```

`drama-service` 当前 9 个未提交文件均为任务开始前的用户既有改动，本次只运行 tests 与真实服务调用，没有把它们计入本次 diff。

## 11. Final Status

```text
BATCH_7_2R = READY_FOR_USER_AUDIO_REVIEW

MCP_HEALTH = PASS
PLUGIN_LOAD = PASS
DRAMA_SERVICE_HEALTH = PASS
MYSQL = PASS
MINIO = PASS

SPEECH_PROVIDER = bailian_qwen
PROVIDER_NEUTRALITY = PASS
OPENAI_REGRESSION = PASS
OPENAI_REAL_TTS_CALLS = 0

REAL_TTS_E2E = PASS
REAL_QWEN_TTS = PASS
QWEN_REAL_TTS_CALLS = 2
QWEN_REAL_TTS_RETRIES = 0
AMBIGUOUS_ATTEMPTS = 0

REAL_AUDIO_CREATED = YES
AUDIO_TECHNICAL_VALIDATION = PASS
REAL_AUDIO_MEDIA_ROUNDTRIP = PASS
HASH_EQUALITY = PASS

USER_AUDIO_REVIEW = PENDING
AUDIO_APPROVED = NOT_SET

AUDIO_TIMELINE = NOT_STARTED
AV_MUX = NOT_STARTED
FINAL_AV = NOT_STARTED
BATCH_7_3 = NOT_STARTED
```

**STOP：真实 Audio 已产生并完成技术验证；等待用户听审。**
