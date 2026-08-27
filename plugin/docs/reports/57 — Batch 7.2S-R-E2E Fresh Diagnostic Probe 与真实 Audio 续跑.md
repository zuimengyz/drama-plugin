# 57 — Batch 7.2S-R-E2E Fresh Diagnostic Probe 与真实 Audio 续跑

日期：2026-08-27  
结论：`BATCH_7_2S_R_E2E = READY_FOR_USER_AUDIO_REVIEW`

## 1. Previous State

56 号报告状态为 `BLOCKED`。历史 rejected operation 的 diagnostics 已不可恢复，本轮不再追查或复用其 identity：

```text
HISTORICAL_REJECTION_RECOVERY_ATTEMPTED = NO_MORE
HISTORICAL_REJECTED_REQUEST_RETRIED = NO
```

本轮使用新的 operation、attempt 和 request fingerprints 做受控复现。

## 2. Runtime Repair

外部 `~/.config/historical-plugin/runtime.env` 第 20 行是明确的 assignment 格式问题：`=` 后多了一个空格，使单个未引用值被 shell 解释成命令。变量名为 `DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN`；未读取、打印或改变其值语义。

修复前先建立外部备份：

```text
~/.config/historical-plugin/runtime.env.bak-batch-7.2s-r-e2e-20260827
```

最小修复仅移除该空格。bash 与 zsh 正式 source 均返回 0，输出均为 0 bytes。外部配置及备份未复制进 repository。

## 3. Diagnostic Strategy

```text
MAX_DIAGNOSTIC_REAL_REQUESTS = 2
ACTUAL_DIAGNOSTIC_PROBES = 1
DIAGNOSTIC_PROBE_2 = NOT_USED_ROOT_CAUSE_IDENTIFIED
```

Probe 1 完整保留 persisted Dialogue、Character Understanding、Voice Profile、Scene State、Performance Intent、Neil 和 `qwen3-tts-instruct-flash`，只创建新的 diagnostic operation identity。

## 4. Probe 1

请求元数据：

```text
Dialogue = spoken-s1-wangsili-proposal
model = qwen3-tts-instruct-flash
voice = Neil
text = 20 chars / 60 UTF-8 bytes
instruction = 2504 chars / 3080 UTF-8 bytes
payload keys = input, model
input keys = instructions, language_type, optimize_instructions, text, voice
compiled instruction hash = 3b16934d698fed336c32ede60e6ab421f5f29dfc4cec7055840d5d92f90cff29
fresh operation fingerprint = 393aa347320d45f91808be3e4c83e6acdab14d611017a73239b2457072e2bb64
```

Provider 的明确结果：

```text
HTTP = 400
code = InvalidParameter
safe message = <400> InternalError.Algo.InvalidParameter: TTS instruction exceeds maximum allowed length. actual=2504, max=2048
Request ID = 11a9a18b-4268-93bb-b2d5-4fa0f19bdcb2
normalized reason = INVALID_REQUEST
AMBIGUOUS = NO
```

## 5. Root Cause

```text
ROOT_CAUSE = PROVIDER_INSTRUCTION_EXCEEDS_2048_CHARACTER_LIMIT
```

该结论来自本轮新的 observable Provider response，不依赖历史 4xx。model、voice、auth 和 quota 不是该请求的拒绝原因。

## 6. Fix

只修改 Bailian Qwen provider instruction compiler：

- 从 rich provider-neutral semantics 中选择当前发声真正需要的字段；
- 去除 `evidenceRefs`、confidence、UNKNOWN、unknownFields、完整历史上下文和重复 metadata；
- 保留 exact-text invariant、材质控制与已审核发音；
- 增加 2048 字符本地 guard，超限时在 HTTP 前返回 `LOCAL_INSTRUCTION_LENGTH_GUARD / INVALID_REQUEST`。

未修改 Character Understanding、Voice Profile、Scene State、Performance Intent schema 或 Skill Core。

## 7. Instruction Compilation

| Speaker | Before | After | Limit |
| --- | ---: | ---: | ---: |
| 王思礼 | 2504 chars / 3080 bytes | 1027 chars / 1503 bytes | 2048 chars |
| 哥舒翰 | 同一旧展开策略 | 1237 chars / 1755 bytes | 2048 chars |

压缩后仍保留三层：

```text
BASE CHARACTER VOICE
CURRENT SCENE STATE
CURRENT LINE PERFORMANCE
```

同一角色的两个候选 instruction hash 完全相同，只有 concrete Provider voice 不同。

## 8. Local Media Import Continuation

修复后的第一个 Neil 请求已由 Provider 成功生成 3.92 秒 WAV，但进程级 TTS 输出目录与 `DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS` 不一致，导致后续本地 Media 安全根检查返回 `INVALID_ARGUMENT`。

物理文件已存在且 ffprobe PASS，因此未重复调用 Provider。MCP 以修正后的进程级 allowed root 重启，并将同一个 WAV 接续导入为新的 `PENDING` Media；随后 get/list/resolve/download/hash 均 PASS。此处没有修改业务代码，也没有增加 audition 请求数。

## 9. Skill E2E

```text
SKILL_ACTUALLY_INVOKED = YES
SHARED_WORK / SCRIPT / EPISODE / SCENE / SHOT = PASS
DUPLICATE_WORK_CREATED = NO
DOMAIN_WRITES = 0
CHARACTER_MODEL_CHANGES = NONE
SEMANTIC_INVARIANTS = PASS
```

正式路径仍为：user-level task → `audio-production` Skill → persisted context → Character Understanding → Voice Profile → Scene State → Performance Intent → fixed candidate ranking → Provider。

## 10. Candidate Audition

| Speaker | Rank | Voice | Media ID | Duration | Review |
| --- | ---: | --- | --- | ---: | --- |
| 王思礼 | 1 | Neil | `media_15a32ca00d494419861c979338fef75c` | 3920 ms | PENDING |
| 王思礼 | 2 | Maia | `media_283960a42ef647f0ae9e998b4ed6f8ab` | 3920 ms | PENDING |
| 哥舒翰 | 1 | Eldric Sage | `media_cbed4d3f7e7a4ca883322091753689d3` | 4960 ms | PENDING |
| 哥舒翰 | 2 | Moon | `media_8b4442503a3a4d99a063b335fc4fac00` | 3760 ms | PENDING |

```text
AUDITION_PROVIDER_CALLS = 4
SAFE_TRANSIENT_RETRIES = 0
AMBIGUOUS_ITEMS = 0
VOICE_BINDING = PENDING
USER_AUDIO_REVIEW = PENDING
AUDIO_APPROVED = NOT_SET
```

## 11. Audio Evidence

所有候选均为 24 kHz、单声道、`pcm_s16le` WAV，bytes 与 duration 均大于 0：

| Voice | Bytes | SHA-256 |
| --- | ---: | --- |
| Neil | 188204 | `0800df5914a6d49e28bc0ac50fb8e37a07be748d7c3858e31ea33d61ddbea3c6` |
| Maia | 188204 | `93d1b665a223743baaef6a5ede2ec9acb0505ef4eda70fd9bfaf9fe7fc8f83ee` |
| Eldric Sage | 238124 | `81f994aa5e46c4db321b1fbcd3cae60990d14dae221c2983939136db99e61366` |
| Moon | 180524 | `a9c8c949bd9017dbdfff5867c0be96fd2e3da7d9991024807493c258b32e9800` |

试听文件：

- `artifacts/batch7-2/review/wangsili-candidate-1-88f39cc9.wav`
- `artifacts/batch7-2/review/wangsili-candidate-2-6d81434b.wav`
- `artifacts/batch7-2/review/geshuhan-candidate-1-6d81434b.wav`
- `artifacts/batch7-2/review/geshuhan-candidate-2-6d81434b.wav`

## 12. Media Roundtrip

四条正式候选均完成：

```text
local review artifact
→ ffprobe
→ Media import
→ current environment Storage
→ Media get
→ Media list by attempt sourceRef
→ resolve
→ download
→ local / Media / resolved SHA equality
```

结果为 `PASS`。旧环境 Media 保持 `OUT_OF_SCOPE`。

## 13. Tests

```text
drama-plugin/plugin
  pytest -q                                      155 passed
  pytest -q tests/test_real_speech_provider.py    37 passed
  mypy src                                        PASS, 44 source files

drama-mcp-service
  pytest -q                                       18 passed
  pytest -q tests/test_adapter.py                  13 passed
  mypy src                                        PASS, 4 source files

validate_batch7_2sr_semantics.py
  Character Understanding = 2
  Voice Profile = 2
  Candidate Ranking = 2
  identity rename invariant = PASS
  semantic invariants = PASS

bash -n scripts/load-env.sh = PASS
zsh -n scripts/load-env.sh  = PASS
```

Provider regression 覆盖 diagnostics、redaction、serialization、instruction compiler、2048 guard、voice/model compatibility、ambiguous/transient safety 与 OpenAI offline path；MCP regression 覆盖安全 diagnostics 传播。

## 14. Secret and Git Safety

未记录 Authorization、API key、Bearer token、Cookie、signed URL 或 credential value。外部 runtime 与 backup 不在 repository。55/56 号报告及历史 evidence 未覆盖；既有用户修改与 `.DS_Store` 均保留。

## 15. Final Status

```text
BATCH_7_2S_R_E2E = READY_FOR_USER_AUDIO_REVIEW

HISTORICAL_REJECTION_RECOVERY_ATTEMPTED = NO_MORE
FRESH_DIAGNOSTIC_REQUESTS = YES
DIAGNOSTIC_PROBES_USED = 1_OF_2

RUNTIME_LOADER = PASS
PROVIDER_DIAGNOSTICS = PASS
PROVIDER_REQUEST_ID_CAPTURE = PASS
ROOT_CAUSE = PROVIDER_INSTRUCTION_EXCEEDS_2048_CHARACTER_LIMIT

CHARACTER_MODEL_CHANGES = NONE
SKILL_ACTUALLY_INVOKED = YES
SEMANTIC_INVARIANTS = PASS

REAL_PROVIDER_CALLS = 5
AUDITION_PROVIDER_CALLS = 4
AMBIGUOUS_ITEMS = 0

REAL_AUDIO_CREATED = YES
AUDIO_TECHNICAL_VALIDATION = PASS
FRESH_AUDIO_MEDIA_CREATED = YES
CURRENT_ENV_MEDIA_ROUNDTRIP = PASS

VOICE_CANDIDATES_READY = YES
VOICE_BINDING = PENDING
USER_AUDIO_REVIEW = PENDING
AUDIO_APPROVED = NOT_SET

COMFYUI_CALLS = 0
BATCH_7_3 = NOT_STARTED
```
