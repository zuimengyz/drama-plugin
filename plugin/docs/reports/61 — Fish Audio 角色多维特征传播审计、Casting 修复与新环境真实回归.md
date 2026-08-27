# Fish Audio 角色多维特征传播审计、Casting 修复与新环境真实回归

日期：2026-08-27  
结论：`FISH_CHARACTER_DIMENSION_REPAIR = READY_FOR_USER_AUDIO_REVIEW`

## 1. Goal

本批在同一任务内完成 Character Dimension Propagation Audit、根因定位、最小通用修复、离线回归、Fresh Fish Voice Design、两阶段 Casting、Create Model、Baseline/Directed TTS 与 ASR QC。没有进入长期 Voice、Media import、Qwen replacement 或 Lip Sync。

核心回答：此前多维 Character Understanding 确实执行，但只被 `PARTIAL` 地转化为 Fish 可用的基础声音设计。主要断点位于 Stable Voice Profile 之后：缺少明确区分史实与艺术决策的 Creative Voice Casting 层；Fish prompt 和自动 Casting 因此只消费少数已知行为维度。

## 2. New Mac Environment Boundary

```text
NEW_MAC_ENV = PASS
RUNTIME_ENV = PRESENT
FISH_AUDIO_API_KEY = PRESENT
OLD_LOCAL_AUDIO_FILES_REQUIRED = NO
OLD_TEMPORARY_REFERENCE_ID_REQUIRED = NO
```

当前 Host 不使用上一环境的 candidate、Master、Baseline 或 Directed WAV。所有输入音频均由本批新的两次 Fish Voice Design 产生。

## 3. Previous Fish Validation

60 号报告已证明 Fish API、Voice Design、Create Model、same-reference Baseline/Directed 与 ASR 可跑，但当时 prompt 只使用 articulation、phrase attack、pace、command presence、controlled power、sentence finality 和 language。`vocalAge/vocalWeight/resonanceDepth/timbreBrightness/texture` 因 `UNKNOWN` 被排除，AI Casting 也固定不比较这些维度。

## 4. AS-IS Character-to-Fish Data Flow

```text
共享 Work/Script/Episode/Scene/Shot
  → CharacterUnderstanding（真实执行，多维）
  → Stable Voice Profile（只保留证据可直接支持的声音后果）
  → build_voice_casting_brief（已知值 + 小型固定 phrase map）
  → Fish Voice Design
  → Technical QC + 少量声学代理评分
```

审计答案：

| 问题 | 结论 |
|---|---|
| Q1 多维 Character Understanding 是否执行 | YES |
| Q2 产生了哪些维度 | 身份/职责、经历、决策、互动、责任、沟通、约束；physical/lifeStage 等允许 UNKNOWN |
| Q3 哪些进入 Stable Voice Profile | articulation、phrase attack、pace、command presence、controlled power、sentence finality、language/register 等 |
| Q4 哪些进入 Creative Casting | 修复前无该层；修复后加入明确标注的 vocal age/weight/register/resonance/brightness/texture/roughness/breathiness 等 |
| Q5 哪些进入 Fish instruction | 修复前仅少数稳定行为维度；修复后 compact acoustic brief 使用上述高价值基础音色维度 |
| Q6 哪些进入 AI Casting | 修复前 clarity/pace/ending/controlled-power；修复后 Technical QC 通过后再比较音龄复合印象、重量、共鸣、明暗、质地、粗糙度、气声等低置信声学代理 |

## 5. Dimension Propagation Matrix

完整机器可读矩阵：`artifacts/role-dubbing-bakeoff/fish-dimension-repair/evidence/dimension-propagation-matrix.json`。

### 王思礼

| Dimension | Source | Character Understanding | Stable Voice Profile | Creative Casting | Fish Prompt | AI Casting |
|---|---|---|---|---|---|---|
| lifeStage | 生年/阶段事实缺失；军旅经历存在 | UNKNOWN | 未投影 | 史实仍 UNKNOWN | 不作为史实发送 | 不作为史实评分 |
| perceivedAgeRange / vocalAge | 长期军旅经历；精确年龄缺失 | UNKNOWN | UNKNOWN | `MATURE_ADULT`，明确为创意决定 | YES | YES / LOW |
| experience | Work hierarchy、P2/P5、《旧唐书》卷110 | domainExperience/leadershipExposure 已知 | 间接 | 作为音龄/重量艺术依据 | 通过声学决定压缩 | 通过目标维度 |
| commandResponsibility | hierarchy + Dialogue | MEDIUM | command presence 已知 | medium controlled power | YES | controlled power；command presence LOW_CONFIDENCE |
| communication | canonical Dialogue | density/directness/precision 已知 | firm/moderate/open request | 保留 | YES | YES |
| physicalState | 稳定证据缺失 | UNKNOWN | UNKNOWN | 不填 | NO | NO |
| vocalWeight | CREATIVE VOICE DECISION | N/A | UNKNOWN | MEDIUM | YES | YES / LOW |
| resonance | CREATIVE VOICE DECISION | N/A | UNKNOWN | BALANCED | YES | YES / LOW |
| brightness/texture | CREATIVE VOICE DECISION | N/A | UNKNOWN | NEUTRAL / CLEAN_SUBTLE_GRAIN | YES | YES / LOW |
| articulation | communication evidence | 已知 | FIRM | FIRM | YES | YES |
| controlledPower | responsibility/interaction + creative decision | 已知依据 | UNKNOWN | MEDIUM_CONTROLLED | YES | YES |

### 哥舒翰

| Dimension | Source | Character Understanding | Stable Voice Profile | Creative Casting | Fish Prompt | AI Casting |
|---|---|---|---|---|---|---|
| lifeStage | 《旧唐书》卷104 年四十遭父丧、三年后入河西；天宝六至十五载序列 | 修复前 UNKNOWN；本批恢复至少五十岁出头下限推断 | 不改长期 profile | late-middle-adult target；不声称精确岁数 | 作为创意声学简报 | YES / LOW |
| perceivedAgeRange / vocalAge | 同上，SUPPORTED INFERENCE | 修复前 UNKNOWN | UNKNOWN | `LATE_MIDDLE_ADULT` | YES | YES / composite / LOW |
| experience | Work protagonist/hierarchy + primary chronology | HIGH | gravitas/command consequence | weight/resonance 依据 | 压缩为声学决定 | 通过目标维度 |
| commandResponsibility | Work/Scene/Dialogue | HIGH | HIGH_ACTION_CONSEQUENCE | controlled power preserved | YES | controlled power；command presence LOW_CONFIDENCE |
| communication | canonical Dialogue | short/dense/final 已知 | firm/deliberate/high-finality | 保留 | YES | YES |
| physicalState | 当前 illness 仅属 Scene | stable baseline UNKNOWN | 不投影 | EXCLUDED | NO | NO |
| vocalWeight | CREATIVE VOICE DECISION | N/A | UNKNOWN | MEDIUM_HEAVY | YES | YES / LOW |
| resonance | CREATIVE VOICE DECISION | N/A | UNKNOWN | DEEP | YES | YES / LOW |
| brightness/texture | CREATIVE VOICE DECISION | N/A | UNKNOWN | SLIGHTLY_DARK / DRY_AGE_TEXTURED | YES | YES / LOW |
| articulation | communication evidence | 已知 | FIRM | FIRM | YES | YES |
| controlledPower | responsibility evidence | 已知依据 | HIGH_WITHOUT_LOUDNESS_REQUIREMENT | preserved | YES | YES |

## 6. Root Cause

根因分类：

```text
DOMAIN_EVIDENCE_MISSING                 = PARTIAL（王思礼精确年龄/生命阶段）
CHARACTER_ANALYSIS_EXTRACTION_GAP       = YES（哥舒翰 primary chronology 未进入 lifeStage）
VOICE_PROFILE_PROJECTION_GAP            = NO（Stable Profile 对无直接声学证据保持 UNKNOWN 是正确边界）
CREATIVE_CASTING_LAYER_MISSING          = YES（主因）
FISH_VOICE_DESIGN_COMPILATION_GAP       = YES（缺少创意值时无输入；既有 map 也没有音龄等值）
AI_CASTING_SCORING_GAP                  = YES（直接原因）
```

上一轮声音跳脱的直接原因主要是 **our casting input / propagation problem**，不是已经证明的 Fish model limitation。Fish 仍存在候选随机性与短句漏读风险；本轮哥舒翰 candidate 1 漏掉开头四字，已被 Stage 1 排除，但这不能解释上一轮基础角色音色目标缺失。

## 7. Character Analysis vs Creative Casting Boundary

《旧唐书》卷104 的人物序列支持哥舒翰在潼关之战时至少已进入五十岁出头；这是由 primary chronology 得出的有边界推断，不是精确生年断言。王思礼传只支持早年从军与长期军旅经历，生年仍 UNKNOWN。

以下保持明确区分：

```text
HISTORICAL / NARRATIVE FACT:
life-stage lower bound、经历、职责、互动、沟通、当前 illness 属 Scene

CREATIVE VOICE DECISION:
vocal age target、weight、register、resonance、brightness、texture、roughness、breathiness
```

Primary sources：

- https://zh.wikisource.org/zh-hant/舊唐書/卷104
- https://zh.wikisource.org/zh-hant/舊唐書/卷110

## 8. Minimal Fix

新增 `CreativeCastingDimension` 与 transient `CreativeVoiceCastingProfile`，以及一个 identity-free 的 generic projection/compiler：

```text
Character Understanding
  → Stable Voice Profile
  → explicit CREATIVE_VOICE_DECISION
  → CreativeVoiceCastingProfile
  → compact Fish acoustic brief
```

Production compiler 不接收人物姓名，不读取 SceneState/PerformanceIntent。真实角色决定仅存在于 integration planning fixture 与 evidence，符合 fixture/evidence 允许边界。

候选评分增加低成本 DSP evidence：low-frequency ratio、first-difference brightness proxy、zero-crossing、envelope variation、crest/tail 等。`vocalAge` 是 weight/resonance/brightness/texture 的复合代理，绝不读取 pitch 单参数。

## 9. Generic / Value-neutral Audit

```text
CHARACTER_SPECIFIC_PRODUCTION_RULES = NONE
VALUE_NEUTRALITY = PASS
IDENTITY_INVARIANCE = PASS
OLDER_AGE_PITCH_SHORTCUT = NONE
STABLE_SCENE_SEPARATION = PASS
```

测试构造同一 profile、不同 synthetic speaker identity；完整 Fish instruction 完全一致。编译器没有 character name、hero/villain、忠奸、勇懦等输入。

## 10. Fish Voice Design Prompt Before vs After

王思礼 BEFORE 只含 firm articulation、direct request、moderate pace、medium command presence、Mandarin。AFTER 额外带入 mature adult vocal age、medium weight、middle register、balanced resonance、neutral brightness、clean subtle grain、low roughness/breathiness 与 medium controlled power。

哥舒翰 BEFORE 只含 firm/deliberate、pace、command consequence、controlled power、finality、Mandarin。AFTER 额外带入 late-middle-adult composite age impression、medium-heavy weight、natural low-middle register（不强压低音）、deep unforced resonance、slightly dark timbre、dry light age texture、low-medium roughness 与 supported low breathiness。

两个 instruction 均短于 Fish 2000 字符限制，没有 CharacterUnderstanding JSON dump，也没有 Scene 临时状态。

## 11. AI Casting Before vs After

BEFORE：技术 QC + clarity/articulation/pace/ending/controlled power；音龄/重量/共鸣/明暗/质地固定 `EXCLUDED_UNKNOWN`。

AFTER：

```text
Stage 1 Technical QC
  ASR/CER/missing/extra/repetition/proper nouns/clipping
  ↓ PASS only
Stage 2 Voice Fit
  vocal age composite/weight/resonance/brightness/texture/roughness/breathiness
  + articulation/pace/ending/controlled power
```

短 preview 的 Voice Fit 全部标 `LOW_ACOUSTIC_PROXY`；command presence 与 cross-line stability 不伪造高精度结论。

## 12. Fresh Voice Design Candidates

```text
VOICE_DESIGN_CALLS = 2
CANDIDATES = 6
REROLL = 0
```

| 角色 | index | durationMs | CER | Technical QC | Voice Fit score |
|---|---:|---:|---:|---|---:|
| 王思礼 | 0 | 3901 | 0 | PASS | 0.6705 |
| 王思礼 | 1 | 3901 | 0 | PASS | 0.6541 |
| 王思礼 | 2 | 4087 | 0 | PASS | **0.6789 / selected** |
| 哥舒翰 | 0 | 3158 | 0 | PASS | 0.7224 |
| 哥舒翰 | 1 | 3158 | 0.3636；漏“此事若行” | FAIL / excluded | 0 |
| 哥舒翰 | 2 | 3158 | 0 | PASS | **0.7311 / selected** |

## 13. Master References

| 角色 | selected index | Master SHA-256 |
|---|---:|---|
| 王思礼 | 2 | `2fed70d530610fd91ebfb71218498bab27944c74a5a2446391ca0418f84e9036` |
| 哥舒翰 | 2 | `f96b3f73eef8baa2142645b5280a02f9dad2febd58385c7d1c1ac82fa8325adb` |

两份 Master 仅存在当前 Host；没有长期 Voice Entity、Work binding 或 provider mapping persistence。

## 14. Baseline TTS

| 角色 | durationMs | chars/s | CER | QC |
|---|---:|---:|---:|---|
| 王思礼 | 3898 | 5.131 | 0 | PASS |
| 哥舒翰 | 3062 | 4.572 | 0 | PASS |

## 15. Directed TTS

Directed 与 Baseline 使用同一个本批新 reference_id 和同一 exact Dialogue；只使用既有 Fish native prosody speed/volume，没有 Qwen 长 instruction。

| 角色 | durationMs | chars/s | CER | Directed/Baseline | QC |
|---|---:|---:|---:|---:|---|
| 王思礼 | 3573 | 5.598 | 0 | 0.917 | PASS |
| 哥舒翰 | 3503 | 3.997 | 0 | 1.144 | PASS |

无可懂度回退，无 >1.5 或 <0.67 的时长畸变。

## 16. Intelligibility QC

6 个 Voice Design candidate 与 4 条正式 TTS 全部执行 Fish ASR。正式输出：

```text
CER = 0
missing = []
extra = []
repetition = []
proper noun mismatches = []
```

同厂 ASR 只是自动门禁，不替代用户听审。

## 17. User Review Files

王思礼：

- `artifacts/role-dubbing-bakeoff/fish-dimension-repair/master-reference/wangsili-master-reference.wav`
- `artifacts/role-dubbing-bakeoff/fish-dimension-repair/review/wangsili-baseline.wav`
- `artifacts/role-dubbing-bakeoff/fish-dimension-repair/review/wangsili-directed.wav`

哥舒翰：

- `artifacts/role-dubbing-bakeoff/fish-dimension-repair/master-reference/geshuhan-master-reference.wav`
- `artifacts/role-dubbing-bakeoff/fish-dimension-repair/review/geshuhan-baseline.wav`
- `artifacts/role-dubbing-bakeoff/fish-dimension-repair/review/geshuhan-directed.wav`

## 18. Tests

| 验证 | 结果 |
|---|---|
| Fish/Audio 专项 | 34 passed |
| drama-plugin full pytest | 174 passed |
| drama-plugin strict mypy | PASS / 46 source files |
| drama-mcp-service pytest | 18 passed |
| drama-mcp-service strict mypy | PASS / 4 source files |
| Git diff check | PASS |

## 19. Git Diff

仅 `drama-plugin` 有代码/测试/报告修改：typed transient contract、generic creative projection/compiler、Fish validation runner 的 repaired brief + two-stage evaluator、identity/neutrality/unknown/technical-gate tests 与本报告。`drama-service`、`drama-mcp-service` 均无代码修改；本机只为只读恢复启动其现有进程。

```text
DRAMA_SERVICE_CHANGES = NONE
DRAMA_MCP_SERVICE_CHANGES = NONE
DB_MIGRATION = NONE
DOMAIN_WRITES = 0
QWEN_IMPLEMENTATION = PRESERVED
```

## 20. Final Status

```text
FISH_CHARACTER_DIMENSION_REPAIR = READY_FOR_USER_AUDIO_REVIEW

NEW_MAC_ENV = PASS
OLD_LOCAL_AUDIO_REQUIRED = NO
SHARED_NARRATIVE_CONTEXT = PASS
DUPLICATE_DOMAIN_DATA = NO

CHARACTER_DIMENSION_AUDIT = COMPLETE
DIMENSION_PROPAGATION_MATRIX = COMPLETE
CHARACTER_UNDERSTANDING = PRESERVED
MULTIDIMENSIONAL_ANALYSIS = ACTIVE

ROOT_CAUSE = IDENTIFIED
CREATIVE_VOICE_CASTING = PASS
FISH_VOICE_DESIGN_INPUT = PASS
AI_CASTING_DIMENSION_USE = PASS

CHARACTER_SPECIFIC_RULES = NONE
VALUE_NEUTRALITY = PASS

VOICE_DESIGN_CALLS = 2
FRESH_CANDIDATES = 6
MASTER_REFERENCES = READY_LOCAL_ONLY
FISH_CREATE_MODEL = PASS
BASELINE_TTS = PASS
DIRECTED_TTS = PASS
INTELLIGIBILITY_QC = COMPLETE

QWEN_REAL_CALLS = 0
VOICE_LONG_TERM_MEMORY = NOT_STARTED
MEDIA_IMPORT = NOT_RUN
LIP_SYNC = NOT_STARTED
USER_AUDIO_REVIEW = PENDING
```

本批技术结果只证明多维人物理解现在能被压缩为 Fish 可用、可审计的基础声音设计，并实际参与选声。角色是否真正合适，尤其哥舒翰的年龄感、重量、纹理与不靠喊叫的控制力，仍以用户听审为最终结论。
