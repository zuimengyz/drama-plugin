# 68 — Batch 7.3B.2 Voice Identity、Voice Design、Casting 与 Materialization 审计报告

日期：2026-08-29  
范围：Voice Identity / Voice Design / Casting / Materialization / DEBUG Media containment  
结论：**工程整改 PASS；完整批次 PARTIAL（中性 G1M 出站未获授权）**

## 1. 执行摘要

本批先以零 Fish 调用重建 61、63、65、66、67 号谱系，再审计
`Character Understanding → CreativeVoiceCastingProfile → Fish Voice Design → AI
Casting → Voice master → Create Model → TTS`。根因不是 DPD：最早可由代码确认的旁白偏置风险位于
**Voice Design compiler**。旧 compiler 把成熟、低中音、深共鸣、坚定、审慎、清晰、克制等正确单项压成一条 instruction，
却没有声明这是“历史短剧中人与人互动的角色对白”；其 preview 又是高度正式、裁决式的
“此事若行，我便是反臣。不可。”。二者组合会把 Provider 推向旁白/播音语义空间。

同时确认了更严重的 lifecycle 缺口：63 号 Branch C 把 Technical QC 后的低置信 DSP Top-1
直接当成 master，随后自动 Voice import、Create Model、Work bind 和 production TTS。AI ranking
事实上越权承担了 Artistic Approval。本批已把显式用户批准门放到 AI ranking 与 master freeze 之间，
并复用 `voice-design-recovery-v1` 支持按 candidate hash 恢复。

G0/G1 已整理并回验。精确中性 G1M 原计划复用 ACTIVE Fish mapping，以相同 preview text、
`speed=1.0 / volume=0.0 / no DPD / no marker` 做一次 TTS；出站安全审查认为这会把私有 production
Voice mapping 用于外部 Fish TTS/ASR，当前授权不足，调用在执行前被拒绝。本批没有绕过，也没有把旧 directed
TTS 冒充中性结果。因此 `MATERIALIZATION_ISOLATION=LIMITED`，按任务标准总批次为 PARTIAL。

## 2. 用户旁白感反馈

用户听感是当前大量 Fish Voice 偏旁白、解说、播音或有声书，而不是可信的人物对白。自动指标不能替代这一艺术判断。
本报告只确认 lineage、prompt 风险、生命周期边界、物理/声学证据及可听审文件；最终角色感仍为
`USER_VOICE_ARTISTIC_REVIEW=PENDING`。

## 3. 本批范围

已执行：

- 61/63 master lineage reconciliation；
- Voice Freeze、Creative Casting、Voice Design prompt、preview text、AI Casting 审计；
- 最小 `CHARACTER_DIALOGUE / NARRATION` 稳定 use-case；
- 新 Voice human artistic approval gate 与 exact-candidate resume；
- Create Model master/hash/fingerprint 复核；
- `[curious]` semantic-collapse side audit；
- 67 号 7 条 DEBUG Media 默认发现隔离；
- streaming WAV actual PCM duration regression；
- G0/G1/既有同文 directed TTS 听审包、测试与报告。

未执行：Fresh Voice Design、生产 Voice replacement、Voice retirement、新 Provider、7.3C、Visual、Lip Sync、AV mux。

## 4. Architecture Freeze

65 的 DPD Core、66 的 DPD → Audio Projection、`AudioPerformanceBrief`、Scene/Beat/Line DPD 均未修改。
本批新增的 `voiceUseCase` 只表达稳定用途，不携带当前 Scene 的 emotion、tactic、pause、dramatic action。

```text
DPD_CORE = FROZEN
AUDIO_PROJECTION = FROZEN
DPD_CODE_CHANGES_BY_7_3B_2 = NONE
VISUAL_7_3C = NOT_STARTED
LIP_SYNC = NOT_STARTED
```

## 5. Historical Voice Lineage

### 61 号哥舒翰

| 项 | 值 |
|---|---|
| candidate count | 3 |
| selected index | 2 |
| preview text | `此事若行，我便是反臣。不可。` |
| master SHA-256 | `f96b3f73eef8baa2142645b5280a02f9dad2febd58385c7d1c1ac82fa8325adb` |
| duration | 3158 ms |
| technical QC | PASS；candidate 1 因漏“此事若行”被排除 |
| creative fit | 低置信声学代理排序 |
| persistence | `LOCAL_ONLY`，无 Voice Entity、Work binding 或 durable provider mapping |

### 63 号哥舒翰

| 项 | 值 |
|---|---|
| Voice | `voice_3b83cfdee0fd4d1a9b4728b0ef1714d7` |
| candidate count | 3 |
| selected index | 0 |
| master SHA-256 | `62c41957aeeeaf27b5da897731863a138b76b3f213ab2dbb3fcb780224cf3787` |
| duration | 3390 ms |
| mapping | Fish / `s2-pro` / ACTIVE |
| mapping material fingerprint | `c11e011153aa95fa5f63c67dc384013cd79b1b2663de657d31ad9190735edc8a` |
| Work binding | PRESENT |
| Voice resolve | Drama Service URL；stored/resolved/download SHA 全相等 |

## 6. 61 vs 63 Master Reconciliation

```text
61_MASTER = f96b…5adb
63_MASTER = 62c4…3787
COMPARISON = DIFFERENT_MASTER
```

原因链：61 的 approved-by-automation master 只留在 Host artifact，没有进入 Voice 长期资源；63 启动时 Work 无
Voice binding，Branch C 只看 durable state，因此重新提交 Voice Design 并从新候选中选 index 0。不是 MinIO、下载、
转码或 Create Model 改写 master；两个原始 master bytes 本来就不同。

这是 **lifecycle gap**，不是合理的稳定 Voice reuse：已知历史 master 没有 durable migration/approval identity，且 Branch C
没有 human review gate。63 的 recovery 只能恢复同一次 Design 的下游失败，不能发现 61 的另一套 local-only lineage。

## 7. Voice Freeze Semantics

正式语义如下：

1. `Candidate != Voice Master`；`AI Top-1 != Voice Master`。
2. 只有匹配 design request fingerprint、candidate index/hash、review artifact id 的 `USER_APPROVED` candidate 才成为 master。
3. master SHA 一旦批准即冻结；Voice import、mapping materialization、恢复都从同一 hash 开始。
4. Work 已绑定 ACTIVE Voice 时必须复用；新的 Creative Casting 输入不能静默换声。
5. mapping 缺失时，从 Drama Service 下载同一 master、校验 stored/resolved/local hash 后 materialize。
6. master 丢失或 hash 不符时返回 `VOICE_REFERENCE_UNAVAILABLE`，不得 Voice Design。
7. stable creative profile 的 material change 需要显式 retire/unbind/redesign + 新一轮人工 review；当前 Tool 不自动失效或替换生产 Voice。

## 8. CreativeVoiceCastingProfile Audit

当前 stable source 到新 Fish instruction 的传播如下：

| 维度 | Source | Casting | 旧 Fish instruction | 新 Fish instruction |
|---|---|---|---|---|
| vocal age | creative decision + chronology basis | `LATE_MIDDLE_ADULT` | YES | YES |
| weight | creative decision | `MEDIUM_HEAVY` | YES | YES |
| register | creative decision | `LOW_MIDDLE` | YES | YES |
| resonance | creative decision | `DEEP` | YES | YES |
| brightness | creative decision | `SLIGHTLY_DARK` | YES | YES |
| texture | creative decision | `DRY_AGE_TEXTURED` | YES | YES |
| roughness | creative decision | `LOW_MEDIUM` | YES | YES |
| breathiness | creative decision | `LOW` | YES | YES |
| articulation | stable VoiceProfile | `FIRM` | YES | YES |
| phrase attack | stable VoiceProfile | `DELIBERATE_JUDGMENT` | NO | YES |
| baseline pace | stable VoiceProfile | `MODERATE_DELIBERATE` | YES | YES |
| baseline energy | stable VoiceProfile | `UNKNOWN` | omitted | omitted |
| breath support | stable VoiceProfile | `UNKNOWN` | omitted | omitted；breathiness phrase 仅要求 supported breath |
| command presence | stable VoiceProfile | `HIGH_ACTION_CONSEQUENCE` | NO | YES，明确不是 announcer projection |
| gravitas | stable VoiceProfile | `HIGH_RESPONSIBILITY_WEIGHT` | NO | YES，明确不是 ceremonial narration |
| controlled power | stable VoiceProfile | `HIGH_WITHOUT_LOUDNESS_REQUIREMENT` | YES | YES |
| sentence finality | stable VoiceProfile | `HIGH` | YES | YES |
| language | stable VoiceProfile | `zh-CN` | YES | YES |
| voice use case | stable Casting | 不存在 | NO | `CHARACTER_DIALOGUE` |

没有从姓名、忠奸、勇懦、当前 illness 或当前 Scene 情绪补人物特征。

## 9. Voice Use Case Audit

旧 contract 无法区分角色对白与旁白。本批只新增一个最小 enum：

```text
VoiceUseCase = CHARACTER_DIALOGUE | NARRATION
```

Role Dubbing 默认 `CHARACTER_DIALOGUE`，兼容旧请求。它只说明“互动、生活化、非纪录片/有声书/广播/播音员/主持人”，
不说明本幕愤怒、威胁、试探或 pause duration。因此它属于稳定 Casting，不属于 DPD。

## 10. Voice Design Prompt Audit

旧哥舒翰 instruction 末尾为：

```text
... strong controlled power without requiring loudness,
decisive high-finality sentence endings, Mandarin Chinese voice.
Keep the base voice natural, clear, and controlled.
```

新 compiler 在相同稳定维度前加入：

```text
an original lived-in character voice for interactive human-to-human dialogue
in a historical drama, conversational rather than documentary, audiobook,
broadcast, announcer, or presenter narration
```

并补齐 stable phrase attack、command presence 与 gravitas，结尾显式禁止加入 current-scene emotion。完整 instruction
仍小于 Fish 2000 字符限制，不含人物姓名、SceneState、DPD 或 Provider 以外业务状态。

## 11. Narrator Bias Audit

源码没有 `authoritative narrator / documentary delivery / studio narration` 等直接正向旁白词。问题是组合语义：

```text
deep + firm + deliberate + controlled + high finality + clear
```

单项均有 stable evidence，但缺少互动角色语境，再叠加正式 preview，构成确定的 narrator-bias risk。修复没有删除人物必要的重量、
责任或克制，也没有改成“more dramatic”；只是增加 stable dialogue use context，并使用反旁白边界避免舞台剧式过演。

```text
NARRATOR_BIAS_ORIGIN = VOICE_DESIGN_COMPILER
QUALIFIER = EARLIEST_CONFIRMED_SEMANTIC_BIAS_RISK
PROVIDER_OUTPUT_ARTISTIC_CONFIRMATION = PENDING_USER_REVIEW
```

## 12. Preview Text Audit

61 与 63 均使用 canonical Dialogue：`此事若行，我便是反臣。不可。`。谱系真实且可恢复，但它是总结式、正式、
高 finality 的裁决句，不足以单独测试自然人际互动的 Voice Identity，存在明显旁白/宣告偏置。当前 Fish Voice Design candidate
长度也随该短 preview 约 3–4 秒。

本批未伪造另一段“同文”，也未改变 canonical Dialogue。后续若 redesign，应先提供 provider-neutral、非人物实名、非当前 Scene
情绪、兼具自然互动与足够音素覆盖的 reviewed casting preview；这是剩余 P1，不属于 DPD。

## 13. AI Casting Boundary

旧 Stage 2 的 age/weight/resonance/texture 等分数来自 crest factor、zero crossing、low-pass energy、envelope variation 等
低置信代理。它可以排技术坏音并辅助排序，不能判断人物可信度、是否像旁白、是否有长期辨识度。

本批定义：

```text
Stage 1 Technical QC → Stage 2 AI Creative Fit ranking
→ Stage 3 USER ARTISTIC APPROVAL
```

`AI_RECOMMENDED != APPROVED`。不新增 narratorScore 或声学伪科学判定。

## 14. Human Artistic Approval Gate

新 Branch C：

```text
No Voice
→ Voice Design (<=3)
→ physical/signal/ASR Technical QC
→ AI ranking
→ voice-design-recovery-v1 package
→ VOICE_ARTISTIC_REVIEW_REQUIRED
→ STOP
```

无 approval 时真实 unit gate 为：

```text
Voice imports = 0
Create Model calls = 0
Work binds = 0
production TTS calls = 0
```

resume approval contract 仅含 design fingerprint、candidate index/hash、review artifact id 与固定 `approvalSource=USER`。
invalid/mismatched approval fail closed。MCP 只公开 provider-neutral high-level code 和无 secret/hash-addressed review details。

## 15. Existing Master Listening Set

- G0：`artifacts/batch7-3b-2/review/01-historical-repair-master.wav`
- G1：`artifacts/batch7-3b-2/review/02-current-production-master.wav`
- 辅助既有同文 directed TTS：`artifacts/batch7-3b-2/review/04-existing-production-same-text-directed.wav`

G1 已通过 `voice.get_voice → voice.resolve_voice → Drama Service content` 下载回验；URL owner 为 Drama Service，
stored/resolved/download SHA 均为 `62c4…3787`。

## 16. Create Model Materialization Isolation

G1M 的严格条件为相同 preview text、当前 ACTIVE mapping、Fish `s2-pro`、speed 1.0、volume 0、无 DPD、无 marker、
无 punctuation manipulation。调用在向 Fish 发送 production Voice identity 前被安全审查拒绝，实际 Fish calls 为 0。

现有 63 TTS 虽同文同 mapping，但为 `speed=0.92 / volume=-1.0`，因此只作为有混杂因素的 auxiliary，不命名为 G1M。

```text
MATERIALIZATION_ISOLATION = LIMITED
G1M = NONE
CREATE_MODEL_IDENTITY_DEGRADATION = NOT_PROVEN
```

## 17. Acoustic Evidence

| 文件 | duration | crest dB | low-pass/signal | diff/signal | clipping |
|---|---:|---:|---:|---:|---|
| G0 | 3158 ms | 19.917 | 0.733 | 0.247 | false |
| G1 | 3390 ms | 18.178 | 0.812 | 0.116 | false |
| 63 同文 directed | 3596 ms | 17.959 | 0.814 | 0.170 | false |

G0/G1 在这些代理上不同，符合不同 master；G1 与 materialized directed TTS 的低频能量代理接近，但这不能证明角色感保留，
也不能判旁白。艺术结论仍等待用户。

## 18. Narrator Bias Root Cause

证据支持的最早层为 `VOICE_DESIGN_COMPILER`：use-case 缺失 + formal preview + formal/controlled 属性组合。63 又由
AI Top-1 自动批准，使 Provider 输出无人工拦截直接进入生产，放大了风险。Create Model/TTS 是否进一步削弱 identity 因无严格 G1M
仍未隔离，不能写成既成事实。

## 19. Conditional Fresh Voice Design

前提“用户确认当前 master 本身已旁白化”尚未完成，所以：

```text
FRESH_VOICE_DESIGN = NOT_NEEDED_BEFORE_USER_REVIEW
VOICE_DESIGN_PRIMARY_SUBMISSIONS = 0
FRESH_CANDIDATES = NONE
```

## 20. Fresh Candidate Results

未执行。没有 N0/N1/N2，没有候选进入 Voice、mapping、Work 或 Media。

## 21. Voice Recovery / Resume

继续复用 `voice-design-recovery-v1`，现在保存 request fingerprint、use case、reference text/hash、candidate count、每个合格候选
index/hash/duration/Technical QC/AI fit/rank/file identity 与 review artifact id。未批准的重复请求返回同一 review package，
`voiceDesignCalls=0`。批准后冻结 exact candidate；若 Voice import 下游失败，下一次同 approval 从相同 master 续跑，不 redesign。

Create Model 对新 approved Voice 传入 provenance 中的 exact reference text；mapping material fingerprint 继续绑定
`voiceId + masterHash + provider + model`。

## 22. `[curious]` Semantic Collapse Side Audit

67 号 B2 的 `[curious]` 是 `run_batch7_3b_1_fish_control_audit.py` 手工实验 rendered text，不是
`dramaticAction=probe` 的 production mapping。active Fish adapter 没有读取 `dramatic_action`，也没有 `probe → curious` 硬编码；
无 rendered text 时 canonical text 原样进入 TTS。新增静态/行为测试防回归。

```text
probe != curious
SEMANTIC_COLLAPSE_RISK = CONTAINED
```

## 23. DEBUG 24h Media Containment

未删除 7 条 durable Media。`media.list_media` 现在默认在 Plugin provider boundary 排除
`content.reviewStatus=DEBUG`；只有显式 `include_debug=true` 才返回。

真实 MCP 验证：

| 查询 | 数量 | status |
|---|---:|---|
| purpose=FISH_CONTROL_AUDIT_DEBUG，默认 | 0 | 不可发现 |
| 同条件 + include_debug=true | 7 | 全部 DEBUG |

影响面：Shot/Asset 正常 selection 通过 `media.list_media` 因而不可见；Role Dubbing canonical reuse 既有精确 sourceRef，
同时仍经过默认过滤；Audio freshness 还要求 `reviewStatus=PASS`；timeline/AV 没有自动 broad selector。知道 stable mediaId 的显式
`media.get_media` 仍可用于审计，这是有意的可追溯性，不是 production discovery。

## 24. Streaming WAV Probe Regression

`probe_wav_duration_ms` 不再把 WAV header 的 declared frame count 当 authority。它读取实际 PCM bytes，按
`actualBytes / channels / sampleWidth / sampleRate` 计时。回归 fixture 把 data chunk size 改成 `0xFFFFFFFF`，实际 1 秒 PCM
仍得到 1000 ms。67 runner 的实际 sample count 路径继续保留。

```text
STREAMING_WAV_DURATION_REGRESSION = PASS
```

## 25. Tests

| Suite | 结果 |
|---|---|
| Voice Design / Creative Casting / AI Casting / lifecycle / recovery / mapping / Work binding / Role Dubbing | included in Plugin full suite，PASS |
| DPD regression / Audio Projection regression / Fish adapter / Media discovery / WAV probe | included in Plugin full suite，PASS |
| drama-plugin pytest | `166 passed` |
| drama-plugin mypy | `Success: no issues found in 49 source files` |
| drama-mcp-service pytest | `26 passed` |
| drama-mcp-service mypy | `Success: no issues found in 4 source files` |
| drama-service Maven | `53 tests, 0 failures, BUILD SUCCESS` |
| real Fish calls | 0 |

## 26. Complexity Audit

新增：1 个两值 enum、1 个小型 approval contract、RoleDubbingRequest 1 个 optional field、既有 recovery manifest 的扩展、
`include_debug` 1 个 opt-in 参数和少量 gate helper。没有新 Entity、DB table、service、repository、workflow engine、dataset、
embedding、narrator detector 或 DPD ontology。Java 无代码修改。

## 27. Severity / P0–P2

| Severity | Finding | 状态 |
|---|---|---|
| P0 | AI Top-1 自动成为 ACTIVE Voice 并触发 materialize/bind/TTS | FIXED：human gate |
| P0 | approved candidate 无 exact hash recovery 导致重抽/身份漂移 | FIXED：fingerprinted recovery + user approval |
| P1 | Voice Design 缺少 CHARACTER_DIALOGUE/NARRATION | FIXED |
| P1 | 3–4 秒 master 低于 Fish clone best-practice 10 秒建议，存在 materialization 风险 | OPEN；需先听审/严格隔离 |
| P1 | formal preview text 放大 narrator bias | OPEN；下次 redesign 前 review |
| P1 | 7 条假 24h DEBUG Media 可被 broad list 发现 | FIXED：默认不可发现 |
| P1 | Create Model/TTS identity degradation | NOT PROVEN；G1M LIMITED |
| P2 | `probe → [curious]` semantic collapse | CONTAINED；仅实验路径 + regression |

Fish 官方证据与推断分开：Create Model API 支持一个或多个 voice files 和对应 texts；官方 Voice Cloning Best Practices 建议
至少 10 秒录音以获得 studio-quality 结果。当前 3.16/3.39 秒是**风险推断**，不是已证明的 degradation。

- [Fish Create Model API](https://docs.fish.audio/api-reference/endpoint/model/create-model)
- [Fish Voice Cloning Best Practices](https://docs.fish.audio/developer-guide/best-practices/voice-cloning)
- [Fish Text to Speech API](https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech)

## 28. 未解决问题

1. G1M 未获出站授权，无法严格区分 current master 与 Create Model/TTS 的艺术身份损失。
2. 用户尚未分别判断 G0/G1 哪个更像人物、哪个更像旁白。
3. current preview 过短且正式；是否 redesign 及是否采用 >=10 秒 approved master 需听审后决定。
4. 当前 production Voice 不自动替换；若用户选择新 Candidate，需后续显式 resume。

## 29. User Listening Review Package

### Master Identity

- G0 与 G1 哪一个更像真实剧情人物？
- 哪一个最像旁白/播音？
- 年龄、社会身份、长期辨识度是否成立？

### Existing materialized auxiliary

- `04-existing-production-same-text-directed.wav` 相比 G1 是否变平、变成标准 TTS？
- 音色重量、年龄感、人物感是否损失？
- 注意它不是中性 G1M，speed/volume 是混杂变量。

## 30. 后续 Resume Requirement

若要完成 G1M，用户需显式批准：使用 production Voice 的现有 Fish mapping，把
`此事若行，我便是反臣。不可。` 发送至 Fish `s2-pro` 做 1 次中性 TTS；是否再把结果发给 Fish ASR应单独明确。
若听审确认 G1 master 本身旁白化，才允许 1 次 Fresh Voice Design（最多 3 candidates、0 reroll），并必须停在新的 review gate；
用户批准前不得替换 production Voice。

## 31. 最终 PASS / PARTIAL / FAIL

```text
VOICE_LINEAGE_AUDIT = PASS
HISTORICAL_PRODUCTION_MASTER_RECONCILIATION = PASS
VOICE_FREEZE_SEMANTICS = DEFINED
VOICE_DESIGN_PROMPT_AUDIT = PASS
VOICE_USE_CASE_AUDIT = PASS
AI_CASTING_BOUNDARY = PASS
HUMAN_ARTISTIC_APPROVAL_GATE = PASS
MATERIALIZATION_ISOLATION = LIMITED
NARRATOR_BIAS_ROOT_CAUSE = NARROWED_WITH_EVIDENCE
NARRATOR_BIAS_ORIGIN = VOICE_DESIGN_COMPILER
DEBUG_MEDIA_CONTAINMENT = PASS
STREAMING_WAV_DURATION_REGRESSION = PASS
DPD_REGRESSION = PASS
AUDIO_PROJECTION_REGRESSION = PASS
VOICE_REGRESSION = PASS
FISH_REAL_CALLS = 0
PRODUCTION_VOICE_CHANGED = NO
USER_VOICE_ARTISTIC_REVIEW = PENDING
BATCH_7_3B_2_ENGINEERING = PASS
BATCH_7_3B_2 = PARTIAL
```

证据：`artifacts/batch7-3b-2/evidence/voice-identity-audit.json`。

