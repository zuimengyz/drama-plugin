# 58 — Batch 7.2S-R-E2E Qwen3-TTS 至 Qwen-Audio 3.0 TTS Plus 角色配音迁移

日期：2026-08-27  
结论：`BATCH_7_2S_R_E2E_QWEN_AUDIO_MIGRATION = READY_FOR_USER_AUDIO_REVIEW`

## A. Migration Audit

迁移前后路径：

```text
Qwen3-TTS Instruct + preset voice
→ Qwen-Audio 3.0 TTS Plus + Voice Design + instruction control
```

| 项目 | Qwen3 legacy path | Qwen-Audio production path |
| --- | --- | --- |
| model family | `QWEN3_TTS` | `QWEN_AUDIO_TTS` |
| model | `qwen3-tts-instruct-flash` | `qwen-audio-3.0-tts-plus` |
| endpoint | `services/aigc/multimodal-generation/generation` | `services/audio/tts/SpeechSynthesizer` |
| voice | preset ranking 产生 Neil / Maia / Eldric Sage / Moon | `voice-enrollment/create_voice` 产生 custom `voice_id` |
| performance field | `input.instructions` | `input.instruction` |
| legacy fields | `optimize_instructions`, `language_type` | 不发送这些字段 |
| base voice | Qwen3 instruction + preset | Stable Voice Profile → compact `VoiceDesignSpec` → `voice_prompt` |
| scene performance | rich Qwen3 instruction | SceneState + PerformanceIntent → compact instruction |
| response | multimodal audio URL → download | SpeechSynthesizer audio URL/id → download |
| diagnostics | HTTP/code/message/request ID/reason | 复用相同安全 diagnostics |
| retry | ambiguous 不重提；明确 transient 有界重试 | 同一原则；非幂等 create_voice 结果不确定时不重提 |
| fingerprint | request/input/provider operation fingerprints | 保留并增加 voice design fingerprint |
| Media | ffprobe → import → get/list/resolve/download/hash | 完全复用，无架构修改 |

审计结论：

- `BATCH72R_QWEN_MODEL` 由 E2E/runtime 层读取，最终进入 `ProviderVoiceMapping.model`；Provider boundary 再做 model-family dispatch。
- 旧实现若只替换 model 字符串，会把 Qwen3 payload 发到错误契约；因此本次不是字符串替换。
- preset ranking 位于 Bailian provider candidate mapping，继续保留给 Qwen3 fallback，不再作为 Plus production casting 主路径。
- Audio 下载、错误解析、retry、fingerprint、ffprobe 与 Media round-trip 可直接复用。

官方契约依据：

- [阿里云 Voice Design API](https://help.aliyun.com/zh/model-studio/voice-design-api-references)
- [阿里云 Qwen-Audio / CosyVoice HTTP TTS API](https://help.aliyun.com/zh/model-studio/cosyvoice-tts-http-api)
- [阿里云 Voice Design 使用指南](https://help.aliyun.com/en/model-studio/voice-design-user-guide)
- [阿里云非实时语音合成指南](https://help.aliyun.com/en/model-studio/non-realtime-tts-user-guide)

## B. Frozen Character Analysis

冻结边界保持为：

```text
Historical / Narrative Context
→ Character Understanding
→ Stable Character Voice Profile
→ Scene State
→ Performance Intent
```

关键冻结源文件：

- `plugin/src/drama_plugin/contracts/audio.py`
- `plugin/integration/validate_batch7_2sr_semantics.py`
- 既有 `audio-production` Skill 及 audio-layer content convention

源文件 SHA-256：

```text
contracts/audio.py
  3e6e81b393eadab75b5121e56e99b85cb97c779a76b245aaae9845698d888ca4
validate_batch7_2sr_semantics.py
  223f3c56571a060959ed61f9b077ca7730053ab8178759a281de25a174c5b3ef
```

重新运行语义 validator 后，Character Understanding、Voice Profile、SceneState + PerformanceIntent、SpeechGenerationRequest 四份 canonical JSON hash 均与迁移前 evidence 完全相同。

```text
CHARACTER_MODEL_FROZEN = PASS
CHARACTER_MODEL_CHANGES = NONE
CHARACTER_ANALYSIS_SEMANTIC_DIFF = NONE
```

## C. Model-family Implementation

`BailianQwenSpeechProvider` 增加小型 family dispatch：

```text
qwen3-tts-*              → existing Qwen3 compiler/endpoint
qwen-audio-3.0-tts-*     → Qwen-Audio compiler/SpeechSynthesizer
```

没有复制 Provider，没有改变 MCP tool；正式生成仍调用 `production.generate_audio`。Provider-neutral Speech contract、Skill、Domain、Java 与 Media architecture 均未加入 DashScope/Qwen 专属概念。

## D. Voice Design

`VoiceDesignSpec` 是现有 Stable Voice Profile 的 deterministic provider projection。它只选择稳定基础音色信息，不读取 Character 名称、Scene State、Performance Intent、evidenceRefs、UNKNOWN 或完整历史上下文。

本轮契约：

```text
model = voice-enrollment
action = create_voice
target_model = qwen-audio-3.0-tts-plus
voice_prompt <= 500 chars
preview_text = 20 persisted Dialogue chars
prefix = ASCII alnum, 10 chars
status query = query_voice, exact target model, status OK
```

| Speaker / Rank | prompt chars | prompt SHA-256 | custom voice ID | create request ID | status request ID |
| --- | ---: | --- | --- | --- | --- |
| 王思礼 / 1 | 291 | `4b4002a37a986f01827e58f23f91ea6c6304fddc2fb2a8ea94bec68ca63706da` | `qwen-audio-3.0-tts-plus-vd-vd03771e52-e4e4e25bcdbe490b9b955b7de3056e50` | recovered from `44d4a9e5-28d1-9cab-8c6c-5f32f439fa67` | `f31617c8-e976-9750-8fb9-0ee2518496fd` |
| 王思礼 / 2 | 291 | same | `qwen-audio-3.0-tts-plus-vd-vd03771e52-38aec0577f9a495f9732fcb7b4510426` | `80176c03-788d-9322-b091-a86397b5ab9b` | `63d4709c-c8af-9a62-91da-a4c6efd8376c` |
| 哥舒翰 / 1 | 335 | `1ed2d231c8560d7b4c6076073a12e5e28e9cf6c2ccf529ee7f119d02988ed4a5` | `qwen-audio-3.0-tts-plus-vd-vd97e9ae73-c4ef2f218bf74c358c7c7bd02f8e56e4` | `21156b63-5882-9044-b667-623367f5babf` | `730ee0a3-897e-96a8-b9a4-b1fde0f515b2` |
| 哥舒翰 / 2 | 335 | same | `qwen-audio-3.0-tts-plus-vd-vd97e9ae73-72d9683242b34e3caa740c5263741a91` | `81c80a58-09de-9694-a825-bee6aeae3d45` | `4daed0e7-4f65-9e29-a587-b516153947ff` |

同一角色 A/B 使用同一 Character Understanding、Voice Profile、VoiceDesignSpec、voice_prompt、target model；唯一变化是独立生成的 custom voice ID。

Voice Design create 总数为 4：第一次 create 成功后，本地对可缺省 `target_model` 的响应解析过严；随后通过只读 `list_voice/query_voice` 唯一恢复该 voice，未重复 create。其 preview 在本地异常发生前未保存；其余 3 个 preview 已作为独立辅助试听文件保存。所有 4 个 voice 的最终 query 状态均为 `OK` 且 target model 完全匹配。

## E. Candidate Generation

```text
MAX_VOICE_DESIGN_CALLS = 4
ACTUAL_VOICE_DESIGN_CREATE_CALLS = 4
CUSTOM_VOICE_CREATED = YES (4)
TARGET_MODEL_MATCH = PASS
SYSTEM_PRESET_USED_FOR_FORMAL_AUDITION = NO
VOICE_BINDING = PENDING
```

生产代码不含测试角色姓名分支；姓名只出现在 E2E evidence 和试听文件名中。没有自动生成 Candidate 3，也没有自动评价候选审美质量。

## F. Performance Instruction

Qwen-Audio `input.instruction` 只投影既有 SceneState 与 PerformanceIntent，包含当前情绪、activation、expressiveness、restraint、urgency、pace/volume delta、pause、emphasis、sentence finality、临时身体状态以及直接影响本句的 objective/subtext。Stable Voice Profile 不在 instruction 中重复。

Provider 实测给出一个明确的 HTTP 400：

```text
code = InvalidParameter
safe message = Instruction length is limited: 128, current: 672
Request ID = 8fe543df-8bff-9f6e-b83e-2d0f837f030d
AMBIGUOUS = NO
AUDIO_CREATED = NO
```

因此在官方页面未列出具体字符上限的情况下，以 observable Provider contract 建立 128-char 本地 guard，并做优先级压缩：

| Speaker | instruction chars | UTF-8 bytes | SHA-256 |
| --- | ---: | ---: | --- |
| 王思礼 | 119 | 357 | `44f5039784f3b970395d8310c43d1ed511c1e0fea2dd2833fb8752b57b81f8fc` |
| 哥舒翰 | 112 | 336 | `6dfe787e919112735904a089a437a59e8b1c3b6cd36344032a4a5ed744fbd070` |

该 400 是无音频产出的迁移契约诊断；随后正式试听恰好 4 次，符合 `MAX_AUDITION_TTS_CALLS = 4`。

## G. Real Audio

所有正式请求均为 exact persisted Dialogue，`exactTextInputVerified = true`。同一角色 A/B 的 Dialogue、SceneState、PerformanceIntent、instruction 与 model 全部相同，只有 custom voice ID 不同。

| Speaker / Rank | Media ID | duration | codec | sample rate | channels | bytes | SHA-256 |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| 王思礼 / 1 | `media_f4778987eac844fea461fa51bd489405` | 12640 ms | `pcm_s16le` | 24000 | 1 | 606764 | `bdd0e182b763a8d4f077097fc4a7ad96c26b3063f53ac75fc0c83aca7c4b7bb2` |
| 王思礼 / 2 | `media_f61cd48a30ec4bb6b6adbedb6a60613c` | 12640 ms | `pcm_s16le` | 24000 | 1 | 606764 | `ffd3471f4e926cd328cb0932cd1dc7d7ec1e42c074227d521beb12bd5d0b88ac` |
| 哥舒翰 / 1 | `media_2908cc0a970c43198255311f6bcd346f` | 5120 ms | `pcm_s16le` | 24000 | 1 | 245804 | `98529d4f29a3a03373d95214e46876b5927a3e8dd6bb95a1ff5e048305cc042b` |
| 哥舒翰 / 2 | `media_9da68203407e438a99ae2915022e3989` | 5120 ms | `pcm_s16le` | 24000 | 1 | 245804 | `f2cc680c7cad61e55880829b2f203503c1ce3cfe2fb07c4b0d453fcd16acf7fb` |

四份音频均完成：

```text
Provider → local WAV → ffprobe → Media import
→ current environment Storage → get/list/resolve/download
→ local / Media / resolved SHA equality
```

```text
QWEN_AUDIO_REAL_TTS = PASS
REAL_AUDIO_CREATED = YES
AUDIO_TECHNICAL_VALIDATION = PASS
FRESH_AUDIO_MEDIA_CREATED = YES
CURRENT_ENV_MEDIA_ROUNDTRIP = PASS
```

## H. Runtime Migration

真实 E2E 成功后，外部 runtime 的唯一 assignment 变化为：

```text
before = qwen3-tts-instruct-flash
after  = qwen-audio-3.0-tts-plus
```

等价迁移前备份：

```text
~/.config/historical-plugin/runtime.env.bak-qwen-audio-20260827-3a617a69
```

移除 model assignment 后，runtime 与 backup 的内容 hash 相同。正式 `load-env.sh` 在 bash/zsh 下 source 均返回 0、输出 0 bytes；Provider model-family sanity 为 `QWEN_AUDIO_TTS`。外部 runtime 与 backup 未复制到 repository。

```text
RUNTIME_MODEL = qwen-audio-3.0-tts-plus
CONFIG_NAMING_TECH_DEBT = PRESENT
SECRET_VALUES_PRINTED = NO
```

## I. Tests

```text
drama-plugin/plugin
  pytest -q                                      161 passed
  pytest -q tests/test_real_speech_provider.py    43 passed
  mypy src                                        PASS, 44 source files
  py_compile integration runner                   PASS

drama-mcp-service
  pytest -q                                       18 passed
  mypy src                                        PASS, 4 source files

validate_batch7_2sr_semantics.py                  PASS
  Character Understanding canonical diff          NONE
  Voice Profile canonical diff                    NONE
  SceneState + PerformanceIntent canonical diff   NONE
  SpeechGenerationRequest canonical diff          NONE

runtime reload
  bash source                                     PASS, 0 output bytes
  zsh source                                      PASS, 0 output bytes
  Provider family sanity                          PASS
```

Provider regression 覆盖 model-family dispatch、Qwen3 backward compatibility、VoiceDesignSpec stable-only projection、500-char guard、preview/prefix guard、create/query contract、non-idempotent ambiguous safety、Plus singular instruction、Qwen3-only field exclusion、128-char instruction guard、diagnostics、redaction 与 SpeechSynthesizer endpoint。

## J. Final Status

```text
BATCH_7_2S_R_E2E_QWEN_AUDIO_MIGRATION = READY_FOR_USER_AUDIO_REVIEW

MIGRATION_AUDIT = PASS
CHARACTER_MODEL_FROZEN = PASS
CHARACTER_MODEL_CHANGES = NONE
CHARACTER_ANALYSIS_SEMANTIC_DIFF = NONE

QWEN3_LEGACY_PATH = PASS
QWEN_AUDIO_MODEL_FAMILY = PASS
QWEN_AUDIO_TTS_CONTRACT = PASS
VOICE_DESIGN_API = PASS
VOICE_DESIGN_SPEC = PASS
VOICE_DESIGN_PROMPT_LIMIT = PASS

CUSTOM_VOICE_CREATED = YES
TARGET_MODEL_MATCH = PASS
QWEN_AUDIO_REAL_TTS = PASS
EXACT_DIALOGUE = PASS

SKILL_ACTUALLY_INVOKED = YES
FIXTURE_BYPASS = NO
DUPLICATE_WORK_CREATED = NO
DOMAIN_WRITES = 0

REAL_AUDIO_CREATED = YES
AUDIO_TECHNICAL_VALIDATION = PASS
FRESH_AUDIO_MEDIA_CREATED = YES
CURRENT_ENV_MEDIA_ROUNDTRIP = PASS

VOICE_CANDIDATES_READY = YES
VOICE_BINDING = PENDING
USER_AUDIO_REVIEW = PENDING
AUDIO_APPROVED = NOT_SET

COMFYUI_CALLS = 0
IMAGE_GENERATION = NOT_STARTED
VIDEO_GENERATION = NOT_STARTED
BATCH_7_3 = NOT_STARTED
SECRET_LEAKAGE = 0
```

到此停止，等待用户试听；不自动选择候选，不建立 Voice Binding，不进入 Batch 7.3。
