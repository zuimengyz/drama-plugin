# Fish Audio Voice Design 角色配音真实验证

日期：2026-08-27  
批次：Batch 7.2S-R-E2E continuation  
结论：`FISH_ROLE_DUBBING_VALIDATION = READY_FOR_USER_AUDIO_REVIEW`

## 1. Previous Blocker

上一轮严格执行“不得调用 Voice Design”与“本地 reference 必须显式映射”的边界，因此在密钥已存在但没有角色 WAV 映射时停止：

```text
FISH_AUDIO_API_KEY = PRESENT
REFERENCE_MAPPING = BLOCKED
FISH_REAL_CALLS = 0
```

该停止没有猜选任意 WAV，也没有 fallback 到 Qwen、Bailian 或 OpenAI。

## 2. Constraint Correction

本次将 reference 改为可选，并保留上一轮 clone path：

```text
explicit local reference exists → Create Model
no local reference              → Fish Voice Design → AI Casting
                                → local Master Reference → Create Model
```

本轮实际路径为：

```text
REFERENCE_MAPPING_REQUIRED = NO
VOICE_SOURCE = FISH_VOICE_DESIGN
```

没有修改 Character Understanding、Stable Voice Profile、Scene State 或 Performance Intent。

## 3. Fish Voice Design Contract

2026-08-27 依据 Fish 官方资料核验：

- endpoint：`POST https://api.fish.audio/v1/voice-design`；
- body：JSON only；
- required header：`model: voice-design-1`；
- `instruction`：1–2000 字符；
- `reference_text`：可选，最多 150 字符；
- `n`：1–4；本轮实际为 3；
- response：`candidates[]`，包含 index、base64 WAV、sample rate、duration 与 preview text；
- endpoint 无状态，不自动创建持久模型。

资料：

- [Fish Voice Design API](https://docs.fish.audio/api-reference/endpoint/openapi-v1/voice-design)
- [Fish Voice Design Guide](https://docs.fish.audio/features/voice-design)
- [Fish Create Model API](https://docs.fish.audio/api-reference/endpoint/model/create-model)
- [Fish TTS API](https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech)
- [Fish ASR API](https://docs.fish.audio/api-reference/endpoint/openapi-v1/speech-to-text)

请求模型明确固定为：

```text
VOICE_DESIGN_MODEL = voice-design-1
REQUESTED_TTS_MODEL = s2-pro
ACTUAL_REQUEST_MODEL = s2-pro
```

未使用第三方代理，也没有静默替换模型。

## 4. Frozen Character Inputs

只读恢复并复用了既有 evidence：

- `character-understanding-7.2s-r-e2e.json`；
- `voice-profile-7.2s-r-e2e.json`；
- `performance-intent-7.2s-r-e2e.json`；
- `generation-request-7.2s-r-e2e.json`。

正式 MCP 读取重新确认：

```text
SHARED_WORK = PASS
SHARED_SCRIPT = PASS
SHARED_EPISODE = PASS
SHARED_SCENE = PASS
SHARED_SHOT = PASS
CANONICAL_DIALOGUE = PASS
DUPLICATE_WORK_CREATED = NO
DOMAIN_WRITES = 0
CHARACTER_ANALYSIS_CHANGES = NONE
```

canonical Dialogue：

| 角色 | spokenContentId | exact text |
|---|---|---|
| 王思礼 | `spoken-s1-wangsili-proposal` | 请给我三十骑，取杨国忠首级，为大帅除患。 |
| 哥舒翰 | `spoken-s1-geshuhan-refusal` | 此事若行，我便是反臣。不可。 |

## 5. Voice Casting Brief

Voice Design 只读取冻结 `creativeProfile` 的现有稳定字段。`SceneState`、`PerformanceIntent`、listener、urgency、当前情绪、剧情背景和人物姓名均未进入基础声音 prompt。

### 王思礼

使用字段：

```text
articulationFirmness = FIRM
phraseAttack = DIRECT_REQUEST
baselinePace = MODERATE
commandPresence = MEDIUM_EXECUTION_CAPABLE
sentenceFinality = OPEN_FOR_SUPERIOR_DECISION
language = zh-CN
```

### 哥舒翰

使用字段：

```text
articulationFirmness = FIRM
phraseAttack = DELIBERATE_JUDGMENT
baselinePace = MODERATE_DELIBERATE
commandPresence = HIGH_ACTION_CONSEQUENCE
controlledPower = HIGH_WITHOUT_LOUDNESS_REQUIREMENT
sentenceFinality = HIGH
language = zh-CN
```

`vocalAge`、`vocalWeight`、`resonanceDepth`、`timbreBrightness`、`texture` 等 UNKNOWN/null 字段全部排除，没有补猜。Prompt 未包含英雄/反派、忠奸、勇懦等价值判断。

## 6. Voice Design Candidates

实际调用：

```text
VOICE_DESIGN_CALLS = 2
VOICE_DESIGN_CANDIDATES = 6
CANDIDATES_PER_CHARACTER = 3
VOICE_DESIGN_REROLL = 0
```

Provider 实际返回 candidate index 为 `0..2`，因此文件保留该原始 index。全部响应音频已保存，并转换出 PCM s16le、mono、24 kHz 的 review copy；Provider 原始采样率为 44.1 kHz。

| 角色 | index | durationMs | Fish ASR | CER | Candidate QC |
|---|---:|---:|---|---:|---|
| 王思礼 | 0 | 4319 | exact | 0 | PASS |
| 王思礼 | 1 | 4087 | exact | 0 | PASS |
| 王思礼 | 2 | 4087 | exact | 0 | PASS |
| 哥舒翰 | 0 | 3158 | exact after normalization | 0 | PASS |
| 哥舒翰 | 1 | 2972 | 漏“不可” | 0.1818 | **FAIL / excluded** |
| 哥舒翰 | 2 | 2972 | exact after normalization | 0 | PASS |

候选 1 的明确漏句没有被审美分数掩盖，也没有触发新一轮 Voice Design。

## 7. AI Casting

```text
CASTING_PROFILE_SOURCE = EXISTING_FROZEN_VOICE_PROFILE
AI_CASTING = PASS
```

自动 Casting 先排除 ASR 漏字/多字、专名错误、重复或明显 clipping 的候选，再仅在可测且 Voice Profile 已知的维度上比较：clarity、articulation、baseline pace、sentence ending 与（若已有目标）controlled power。UNKNOWN 的音龄、重量、共鸣、明暗和质地不计分；短 preview 无法可靠自动判定 command presence 与跨句 voice stability，明确保留给听审。

最终选择：

| 角色 | selected provider index | Master SHA-256 | 选择摘要 |
|---|---:|---|---|
| 王思礼 | 0 | `98dcfffc394a3af14118594152ccb94489f522a5e47b67ba152fd2148c992d2a` | ASR exact；节奏最接近既有 MODERATE 目标；技术 QC PASS |
| 哥舒翰 | 2 | `0e7a4d137a9bbce193063b181c0d222fca97adbc508d7a624f638e9883477113` | ASR exact；节奏、句尾与 controlled-power 声学代理在合格候选中最匹配 |

这是结构化评价摘要，不是最终审美结论。

## 8. Master Reference

选中候选按哈希不变复制为：

- `wangsili-master-reference.wav`；
- `geshuhan-master-reference.wav`。

状态：

```text
MASTER_REFERENCE_AUDIO = READY
MASTER_VOICE_PERSISTENCE = LOCAL_ONLY
VOICE_ENTITY = NOT_CREATED
VOICE_TABLE = NOT_CREATED
WORK_VOICE_BINDING = NOT_CREATED
```

## 9. Create Model

依据官方契约，以 multipart `POST /model`、`type=tts`、`train_mode=fast`、`visibility=private` 创建临时模型。

```text
FISH_CREATE_MODEL_CALLS = 2
FISH_CREATE_MODEL = PASS
TEMPORARY_REFERENCE_ID = CREATED_PER_CHARACTER
PROVIDER_VOICE_ID_PERSISTENCE = EXPERIMENT_ONLY
```

每个角色只创建一次；Baseline 与 Directed 复用相同 `reference_id`。

## 10. Baseline TTS

| 角色 | model | durationMs | chars/s | ASR CER | 专名 | 技术 QC |
|---|---|---:|---:|---:|---|---|
| 王思礼 | `s2-pro` | 4084 | 4.897 | 0 | `三十骑`、`杨国忠` PASS | PASS |
| 哥舒翰 | `s2-pro` | 2830 | 4.947 | 0 | `反臣` PASS | PASS |

Baseline 只传同一临时 `reference_id`、exact Dialogue 与中性默认表演参数。

## 11. Directed TTS

Directed 保持同一 `reference_id` 与同一 exact Dialogue。为不把 provider markup 混入 canonical text，本轮仅使用 Fish 官方 `prosody.speed/volume`：

- 王思礼：`speed=1.05`、`volume=-1.0`；
- 哥舒翰：`speed=0.92`、`volume=-1.0`。

| 角色 | durationMs | chars/s | ASR CER | 专名 | 技术 QC |
|---|---:|---:|---:|---|---|
| 王思礼 | 4084 | 4.897 | 0 | PASS | PASS |
| 哥舒翰 | 3248 | 4.310 | 0 | PASS | PASS |

没有复用 Qwen instruction compiler，也没有将完整 Character Understanding、政治背景或长 subtext 发给 Fish。

## 12. ASR / Intelligibility QC

```text
ASR_PROVIDER = FISH
SAME_VENDOR_AS_TTS = YES
FORMAL_TTS_ASR_CALLS = 4
CANDIDATE_QC_ASR_CALLS = 6
ASR_QC = COMPLETE
```

四条正式 TTS：

```text
CER = 0
missing characters = []
extra characters = []
repetitions = []
proper noun mismatches = []
INTELLIGIBILITY_QC = PASS
```

同厂 ASR 仅是自动 QC，不代替用户试听。

## 13. Duration Comparison

| 角色 | Baseline | Directed | Directed/Baseline | 可懂度回退 | 时长畸变 |
|---|---:|---:|---:|---|---|
| 王思礼 | 4084 ms | 4084 ms | 1.000 | NO | NO |
| 哥舒翰 | 2830 ms | 3248 ms | 1.148 | NO | NO |

没有使用 atempo、time stretch、pitch shift、EQ、compression、reverb 或 enhancement 掩盖模型输出。

## 14. Audio Evidence

核心 evidence：

```text
artifacts/role-dubbing-bakeoff/fish-validation/evidence/fish-role-dubbing-validation.json
```

实际调用数：

```text
Fish Voice Design = 2
Fish Create Model = 2
Fish TTS = 4
Fish ASR = 10  # 6 candidate QC + 4 formal output QC
FISH_REAL_CALLS = 18

QWEN_REAL_CALLS = 0
BAILIAN_REAL_CALLS = 0
OPENAI_REAL_CALLS = 0
```

Fish 响应没有返回 request/trace header，evidence 中 request ID 为 null；未伪造 ID。

## 15. Tests

| 验证 | 结果 |
|---|---|
| Fish 专项离线测试 | 11 passed |
| drama-plugin full pytest | 172 passed |
| drama-plugin strict mypy | PASS，45 source files |
| drama-mcp-service pytest | 18 passed |
| drama-mcp-service strict mypy | PASS，4 source files |
| Git diff check | PASS |
| API key 扫描 | 30 files，0 matches |

覆盖 Voice Design 序列化/解析、候选 base64 音频、UNKNOWN 排除、Casting identity/Scene invariance、漏短句候选排除、Create Model multipart、`s2-pro` header、same-reference exact-text、鉴权脱敏与 ambiguous timeout 不重投。

## 16. Git Diff

本批只在 `drama-plugin` 增加：

- 一个最小 Fish HTTP client；
- 一个显式 reference / Voice Design 双路径 validation runner；
- 两组离线测试；
- 本报告与 Stage A0 artifacts。

```text
DRAMA_MCP_SERVICE_CHANGES = NONE
DRAMA_SERVICE_CHANGES = NONE
JAVA_DOMAIN_CHANGES = NONE
DB_MIGRATION = NONE
QWEN_IMPLEMENTATION = PRESERVED
```

预存 `.DS_Store` 与 59 号未跟踪报告均未覆盖或删除。

## 17. User Review Files

### 王思礼

- Master Reference：`master-reference/wangsili-master-reference.wav`
- Baseline：`review/wangsili-baseline.wav`
- Directed：`review/wangsili-directed.wav`

### 哥舒翰

- Master Reference：`master-reference/geshuhan-master-reference.wav`
- Baseline：`review/geshuhan-baseline.wav`
- Directed：`review/geshuhan-directed.wav`

所有 Voice Design 候选保存在 `voice-design/`，供必要时回看。

人工听审项：Voice identity similarity、Age impression、Vocal weight、Clarity、Pronunciation、Naturalness、Performance、Restraint/control、Pace、Command presence、Character consistency、Baseline vs Directed difference、Production acceptable。

## 18. Final Status

```text
FISH_ROLE_DUBBING_VALIDATION = READY_FOR_USER_AUDIO_REVIEW

REFERENCE_MAPPING_REQUIRED = NO
VOICE_SOURCE = FISH_VOICE_DESIGN
FISH_API_KEY = PRESENT

VOICE_DESIGN_CALLS = 2
VOICE_DESIGN_CANDIDATES = 6
AI_CASTING = PASS

MASTER_REFERENCE_AUDIO = READY_LOCAL_ONLY
FISH_CREATE_MODEL = PASS
TEMPORARY_REFERENCE_ID = CREATED
VOICE_IDENTITY_CONTROL = PASS

FISH_BASELINE_TTS = PASS
FISH_DIRECTED_TTS = PASS
ASR_QC = COMPLETE
INTELLIGIBILITY_QC = PASS
PERFORMANCE_CONTROL_INTELLIGIBILITY_REGRESSION = NO
PERFORMANCE_CONTROL_DURATION_DISTORTION = NO

QWEN_REAL_CALLS = 0
BAILIAN_REAL_CALLS = 0
OPENAI_REAL_CALLS = 0

VOICE_ENTITY = NOT_CREATED
VOICE_TABLE = NOT_CREATED
WORK_VOICE_BINDING = NOT_CREATED
MEDIA_IMPORT = NOT_RUN
MINIO_WRITE = NOT_RUN
ROLE_DUBBING_TOOL = NOT_CREATED
LIP_SYNC = NOT_STARTED
QWEN_REPLACEMENT = NOT_STARTED

USER_AUDIO_REVIEW = PENDING
```

技术验证回答：无本地 reference 时可自动进入 Voice Design；候选可由冻结 Stable Voice Profile 与技术/声学 evidence 自动定声；选中 Master 可成功创建临时模型并在 Baseline/Directed 间稳定复用。声音是否真正符合角色、Directed 是否更有影视表演价值、Fish 是否应取代 Qwen，只能由本轮用户试听决定。
