# 56 — Batch 7.2S-R-E2E Provider 拒绝诊断与真实候选续跑

日期：2026-08-27  
结论：`BATCH_7_2S_R_E2E = BLOCKED`

## 1. Previous Blocker

55 号报告中的首个 fresh candidate 已到达真实 Provider，并被 4xx 明确拒绝：

```text
Dialogue = spoken-s1-wangsili-proposal
Model = qwen3-tts-instruct-flash
Voice = Neil
REQUEST_REACHED_PROVIDER = YES
CLASSIFICATION = PROVIDER_REJECTED
AMBIGUOUS = NO
```

该 operation 保持 `HISTORICAL_REJECTED / DO_NOT_BLIND_RETRY`。本次没有复用其 operation identity、request fingerprint 或 attempt identity。

## 2. Zero-Call Rejection Root Cause Diagnosis

旧实现只把 `httpx.Response.status_code` 放入 `SpeechProviderError`；response body 中可能存在的 code、message、request ID 没有解析，也没有进入 MCP evidence。历史进程已结束，workspace、artifact 和日志搜索均只剩 4xx 分类，无法恢复被丢弃的数据。

```text
HTTP status = 4XX_EXACT_VALUE_NOT_RETAINED
provider error code = NOT_RETAINED
safe provider error message = NOT_RETAINED
provider request ID = NOT_RETAINED
normalized reason category = UNKNOWN_REJECTION
ROOT_CAUSE = PROVIDER_REJECTION_REASON_UNKNOWN
```

阿里云官方非实时音色表明确列出 Neil 支持 `qwen3-tts-instruct-flash`，因此可以排除 `VOICE_MODEL_INCOMPATIBLE`，但不能据此在 `INVALID_REQUEST`、`AUTH_OR_PERMISSION`、`QUOTA_OR_ACCOUNT` 或其他 rejection 中任选一个。[Qwen-TTS 非实时音色表](https://help.aliyun.com/zh/model-studio/qwen-tts-voice-list)

离线重建的旧 request 具有 20 字符 exact Dialogue 和 2504 字符 instruction（3080 UTF-8 bytes）。官方说明 instruction 上限为 1600 Token，所以存在输入长度风险；由于旧 error code/message 不在，字符数不能证明旧请求一定超过 Provider tokenizer 的 Token 限制，也不能作为历史根因。[非实时语音合成说明](https://help.aliyun.com/zh/model-studio/non-realtime-tts-user-guide)

阿里云建议失败时保留 Request ID，并说明它可能出现在 header 或 body；旧 Adapter 恰好没有保存该字段。本次只为未来请求修复此链路，不通过新付费请求反查历史错误。[百炼错误码与 Request ID](https://help.aliyun.com/zh/model-studio/error-code)

## 3. Diagnostic Propagation

最小传播链现在为：

```text
Bailian HTTP response
→ BailianQwenSpeechProvider parses selected safe fields
→ SpeechProviderError stores provider-neutral diagnostics
→ PluginToolAdapter emits MCP PROVIDER_REJECTED
→ E2E runner records allowlisted diagnostics
```

MCP error 可包含：

```text
httpStatus
providerErrorCode
providerErrorMessage
providerRequestId
rejectionReason
```

原因分类保持精简：

```text
VOICE_MODEL_INCOMPATIBLE
INVALID_REQUEST
UNSUPPORTED_PARAMETER
AUTH_OR_PERMISSION
QUOTA_OR_ACCOUNT
CONTENT_REJECTED
UNKNOWN_REJECTION
```

只有 provider code/message/status 的明确证据触发具体分类；否则为 `UNKNOWN_REJECTION`。`AMBIGUOUS_RESULT`、`PROVIDER_REJECTED`、`TRANSIENT_RETRY_EXHAUSTED` 三种 paid-call safety 语义保持独立。

## 4. Secret Safety

Adapter 不保存 raw response、完整 headers 或任意 response dump，只选择 `code`、`message`、`request_id` 和指定 request-ID header。Provider boundary 与 MCP boundary 均执行防御性过滤：

```text
Authorization / Bearer = REDACTED
API key = REDACTED
access token = REDACTED
Cookie = REDACTED
credential = REDACTED
URL and signed query = REDACTED
message length = BOUNDED
identifier character set = ALLOWLISTED
```

测试确认 exception 原文、credential、signed URL 和 mock secret 不进入 MCP content 或 structured content。

## 5. Voice / Model Compatibility

兼容性表只位于 `BailianQwenSpeechProvider` 层，不进入 Skill 或 Character Model。当前四个 planned candidates：

| Speaker | Rank | Voice | Model | Compatibility |
| --- | ---: | --- | --- | --- |
| `speaker:wangsili` | 1 | Neil | `qwen3-tts-instruct-flash` | COMPATIBLE |
| `speaker:wangsili` | 2 | Maia | `qwen3-tts-instruct-flash` | COMPATIBLE |
| `speaker:geshuhan` | 1 | Eldric Sage | `qwen3-tts-instruct-flash` | COMPATIBLE |
| `speaker:geshuhan` | 2 | Moon | `qwen3-tts-instruct-flash` | COMPATIBLE |

兼容检查只使用 model、voice 和 Provider capability；没有人物姓名规则。明确 incompatible 会在 HTTP 前阻止，unknown 也 fail closed。

## 6. Minimal Fixes

本次只修改：

- `SpeechProviderError`：增加安全 diagnostics 和 rejection reason；
- `BailianQwenSpeechProvider`：解析 allowlisted error 字段、脱敏、分类，并执行小型 voice/model compatibility preflight；
- MCP adapter：传播安全字段，不传播 raw exception；
- E2E runner：记录 allowlisted diagnostics；只有明确 `VOICE_MODEL_INCOMPATIBLE` 才允许转向下一个预规划独立候选；
- `scripts/load-env.sh`：source 前验证每一条为单独 assignment，禁止 assignment 后附命令、command substitution 和未闭合引用。

没有修改 Character Understanding、Voice Profile、Scene State、Performance Intent、candidate ranking、Dialogue、Java 或 shared Domain data。

## 7. Runtime Loader

当前外部 runtime 第 20 行仍包含 assignment 后附命令。旧 loader 会先产生 shell command error，再因文件后续命令成功而返回 0。修复后 bash/zsh 均在 source 前返回非 0，不执行任何 env 行，也不输出变量值。

```text
bash valid assignment file = PASS
zsh valid assignment file = PASS
bash invalid file fail-closed = PASS
zsh invalid file fail-closed = PASS
external runtime current load = FAIL_NONZERO_AS_REQUIRED
external runtime modified = NO
partial export = NO
secret leakage = 0
```

诊断时仍可用 `python-dotenv` 向隔离子进程注入配置；它不改变正式 loader 的 fail-closed 结论。

## 8. Shared Context and Skill Plan

使用隔离 MCP 子进程再次执行五层正式 get，全部命中既有 IDs：

```text
SHARED_WORK = PASS
SHARED_SCRIPT = PASS
SHARED_EPISODE = PASS
SHARED_SCENE = PASS
SHARED_SHOT = PASS
DUPLICATE_WORK_CREATED = NO
DOMAIN_WRITES = 0
```

继续使用 55 号报告已经由 `audio-production` Skill 生成的 exact Dialogue、Character Understanding、Voice Profile、Scene State、Performance Intent 和当前 ranking。语义 validator 再次 PASS；Character Model diff 为 0。

## 9. Fresh Provider Calls

Resume Gate 要求旧拒绝原因已知、payload 已证明 valid、正式 runtime PASS。当前三项均未完全满足，所以没有创建新 generation identity，也没有提交 Maia 或其他候选。

```text
PREVIOUS_REJECTION_REASON_KNOWN = NO
PROVIDER_PAYLOAD = RISK_PRESENT_NOT_PROVEN_VALID
RUNTIME_LOADER = FAIL_CLOSED_INVALID_EXTERNAL_ENV
NEW_REAL_PROVIDER_CALLS = 0
HISTORICAL_REJECTED_REQUEST_RETRIED = NO
SAFE_RETRIES = 0
NEW_AMBIGUOUS_ITEMS = 0
```

## 10. Audio and Current Environment Media

```text
REAL_AUDIO_CREATED = NO
AUDIO_TECHNICAL_VALIDATION = NOT_RUN
FRESH_AUDIO_MEDIA_CREATED = NO
CURRENT_ENV_MEDIA_ROUNDTRIP = NOT_RUN
OLD_ENVIRONMENT_MEDIA = OUT_OF_SCOPE_NOT_VALIDATED
OLD_ENV_MEDIA_REQUIRED = NO
VOICE_CANDIDATES_READY = NO
USER_AUDIO_REVIEW = NOT_READY
VOICE_BINDING = PENDING
AUDIO_APPROVED = NOT_SET
```

## 11. Tests

```text
drama-plugin/plugin
  pytest -q                         154 passed
  mypy src/drama_plugin             PASS, 44 source files

drama-mcp-service
  pytest -q                         18 passed
  mypy src/drama_mcp_service        PASS, 4 source files

validate_batch7_2sr_semantics.py
  Character Understanding = 2
  Voice Profile = 2
  Candidate Ranking = 2
  identity rename invariant = PASS
  semantic invariants = PASS
  paid provider calls = 0

bash -n scripts/load-env.sh         PASS
zsh -n scripts/load-env.sh          PASS

E2E JSON parse                      22 files PASS
secret-pattern scan                 0 matches
```

Provider tests覆盖 rejection parsing、redaction、显式原因分类、兼容性 preflight、Bailian safe retry/ambiguous safety、OpenAI offline regression 和 Skill vendor neutrality。MCP tests覆盖 diagnostics 传播和三种 paid safety classification。

## 12. Git Safety

既有 `.DS_Store` 未跟踪文件，以及 `drama-mcp-service/integration/run_mcp_e2e.py`、`integration/verify_runtime_config.py` 的既有修改均保留。55 号报告和旧 evidence 未覆盖。外部 runtime 未修改或复制。

## 13. Final Status

```text
BATCH_7_2S_R_E2E = BLOCKED
BLOCKER = PROVIDER_REJECTION_REASON_UNKNOWN

PROVIDER_REJECTION_DIAGNOSTICS = PASS_FOR_FUTURE_CALLS
HISTORICAL_DIAGNOSTIC_RECOVERY = NOT_POSSIBLE
PREVIOUS_REJECTION_REASON = UNKNOWN_REJECTION
ERROR_REDACTION = PASS
VOICE_MODEL_COMPATIBILITY_PREFLIGHT = PASS
NEIL_CURRENT_MODEL_COMPATIBILITY = COMPATIBLE

RUNTIME_LOADER = FAIL_CLOSED_INVALID_EXTERNAL_ENV_LINE_20
SHARED_NARRATIVE_CONTEXT = PASS
DUPLICATE_WORK_CREATED = NO
DOMAIN_WRITES = 0

SKILL_ACTUALLY_INVOKED = YES
CHARACTER_MODEL_GENERIC = PASS
CHARACTER_MODEL_CHANGES = NONE
SEMANTIC_INVARIANTS = PASS

FRESH_E2E_REQUESTS = NO_ADDITIONAL_CALLS
HISTORICAL_REJECTED_REQUEST_RETRIED = NO
NEW_REAL_PROVIDER_CALLS = 0

REAL_AUDIO_CREATED = NO
AUDIO_TECHNICAL_VALIDATION = NOT_RUN
FRESH_AUDIO_MEDIA_CREATED = NO
CURRENT_ENV_MEDIA_ROUNDTRIP = NOT_RUN
VOICE_CANDIDATES_READY = NO
VOICE_BINDING = PENDING
USER_AUDIO_REVIEW = NOT_READY
AUDIO_APPROVED = NOT_SET

COMFYUI_CALLS = 0
BATCH_7_3 = NOT_STARTED
```
