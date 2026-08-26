# Batch 7.2S-R — 通用角色理解与戏剧配音加固

日期：2026-08-26  
结论：`BATCH_7_2S_R = AMBIGUOUS`

## 1. Previous Review

Batch 7.2S 已证明 Skill、领域上下文、语义规划、Speech Provider 和 Media Transport 的链路成立，但用户正式听审结论为：

```text
7.2S ENGINEERING = PASS
7.2S USER REVIEW = REJECTED
VOICE_CASTING_MATCH = FAIL
SCENE_PERFORMANCE_MATCH = FAIL
```

问题已经从 Transport / Semantic Propagation 收敛到 Character Understanding、Casting 与 Performance Quality。只替换一个 preset voice 不能解决人物理解过薄、稳定声线与当前表演混合等问题。

## 2. Character Model Changes

本批在正式 Speech Request 前加入轻量 transient `CharacterUnderstanding`，不增加数据库表。它由证据支持的字段组成，并允许显式 `UNKNOWN`：

- 身份与生命阶段；
- 经历结构；
- 决策方式；
- 情绪调节；
- 人际互动；
- 权力与责任；
- 表达习惯；
- 身体基线；
- 公开/私下呈现；
- 组织、责任与边界约束。

每个已填维度包含 `value / confidence / evidenceRefs`。`UNKNOWN` 必须使用 `LOW` confidence。新的长期 Voice Profile 增加 `vocalWeight`、`resonanceDepth`、`articulationFirmness`、`commandPresence`、`controlledPower`、`sentenceFinality` 等 provider-neutral 维度；旧字段仍以默认 `UNKNOWN` 保持兼容。

实现仍是小型 typed object + Skill rules，没有 Character Psychology Framework、数据库迁移、Voice DB、embedding 或新 Domain Entity。

## 3. Neutrality Audit

```text
NO CHARACTER-SPECIFIC RULE = PASS
NO VALUE-LADEN CHARACTER SHORTCUT = PASS
NO PROVIDER-SPECIFIC SKILL RULE = PASS
```

- Production Skill 和 casting resolver 不含测试角色姓名判断；
- Skill 不含 Provider、model 或 concrete voice 名；
- 新增规则没有把“英雄/反派、贤明/昏庸、勇敢/懦弱、高尚/卑劣”作为声音捷径；
- Adapter 的候选评分只读取 Voice Profile；把 speaker identity 换成合成名称后，候选 ID、分数和理由完全一致；
- Java Domain 未增加任何 Provider 感知字段或 Tool。

真实测试结果可以出现人物姓名，但没有 production rule 依赖人物 identity。

## 4. Stable vs Scene State

正式顺序变为：

```text
Historical / Narrative Evidence
  -> Character Understanding (stable + uncertainty)
  -> Character Voice Profile (stable)
  -> Voice Candidate Ranking
  -> Scene State (temporary)
  -> Performance Intent (baseline + sceneDelta)
  -> Speech Request
```

`SceneState` 单独承载当前 emotion、cause、internal activation、external expressiveness、urgency、stress、interaction target、objective、subtext、restraint、physical condition 与 presentation mode。病中负担、当前疲惫、低声、高压、紧迫等不会永久写入角色声音。

## 5. Character Understanding Evidence

Skill Host 实际加载已持久化的 Work、Script、Episode、Scene、Shot，没有 fixture bypass：

| Domain | ID |
|---|---|
| Work | `work_9cc5d11969a64f93bce4a544f349c793` |
| Script | `script_a404a8277fef45eda8ef3aaf478307cc` |
| Episode | `episode_c33021fe53ba4af08cd8b98113184dd2` |
| Scene | `scene_3ad95aa042e647d9a9be05a51dd8a009` |
| Shot | `shot_83db7eb53b2f49d3a58428d4659e584e` |

### 王思礼（本次真实测试数据）

- Identity / Role：受主帅节制的部将；可执行小规模行动，最终批准权不在本人；
- Experience：持久层支持军务、前线行动与率领先头部队经历；
- Decision：面对当前威胁迅速提出资源与目标明确的高后果行动；
- Interaction：直接提出兵力、目标和效用，同时用请求句承认批准权；
- Responsibility：行动受主帅批准权与军令关系约束；
- Communication：一句内完成请求、目标和理由，密度高、说明短；
- Physical / emotional baseline：无足够持久证据，保持 `UNKNOWN`；
- lifeStage、perceivedAgeRange、长期情绪表达方式等均未凭姓名或身份补全。

### 哥舒翰（本次真实测试数据）

- Identity / Role：守关军统军主帅，对关防、军令和部将行动承担最终裁决责任；
- Experience：持久层支持关防、军务判断、大军指挥及会战经历；
- Decision：重视军报、地形与后果，优先维护持续关防，拒绝不可逆政治位置变化；
- Interaction：以行动后果和明确拒绝关闭高风险方案；
- Responsibility：当前决定同时影响身份、军令边界与守关体系；
- Communication：短句、高密度、明确句末关闭；
- Physical baseline：长期身体声学影响证据不足，保持 `UNKNOWN`；本 Scene 的 illness burden 只进入临时状态；
- lifeStage、perceivedAgeRange、长期 emotional containment 等没有从历史名声或年龄印象猜测。

完整结构见 `character-understanding-7.2s-r.json`。`SKILL_ACTUALLY_INVOKED=true`，付费前阶段 `paidProviderCalls=0`。

## 6. Voice Profiles

两份 profile 均为 provider-neutral，未知维度不补齐：

| Speaker | Stable Profile 摘要 |
|---|---|
| `speaker:wangsili` | `articulationFirmness=FIRM`；`phraseAttack=DIRECT_REQUEST`；`baselinePace=MODERATE`；`commandPresence=MEDIUM_EXECUTION_CAPABLE`；请求句保留最终决定开放；vocal age/weight/resonance/timbre 等 `UNKNOWN` |
| `speaker:geshuhan` | `articulationFirmness=FIRM`；`phraseAttack=DELIBERATE_JUDGMENT`；`baselinePace=MODERATE_DELIBERATE`；`commandPresence=HIGH_ACTION_CONSEQUENCE`；`controlledPower=HIGH_WITHOUT_LOUDNESS_REQUIREMENT`；`sentenceFinality=HIGH`；vocal age/resonance/timbre 等 `UNKNOWN` |

这里的 `commandPresence` 表示话语具有行动后果，不表示声音大；`controlledPower` 表示不提高音量仍保持力量；`sentenceFinality` 只影响决定、拒绝、命令或裁决的句末结束性。

## 7. Candidate Casting

Adapter 使用 profile semantic vector 做 Top 3 排名。年龄权重仅为普通维度的 0.35；gender presentation 只在有证据时过滤候选，本次缺乏持久层证据，因此没有从姓名推断。

| Speaker | Rank 1 | Rank 2 | Rank 3 | Binding |
|---|---:|---:|---:|---|
| `speaker:wangsili` | Ethan 90.000 | Cherry 87.500 | Maia 86.250 | `PENDING` |
| `speaker:geshuhan` | Eldric Sage 97.500 | Moon 90.000 | Neil 89.167 | `PENDING` |

第一项比较了 articulation、pace、command presence 与 sentence finality；第二项另比较 controlled power 与 gravitas。Top 1 仅是本轮试听授权候选，不是 Approved Voice Binding。

Skill 完全不知道上述 Provider voice 名；名称只在 Provider-side evidence 与本报告中出现。

## 8. Performance Intent

### `spoken-s1-wangsili-proposal`

- baseline：moderate pace、firm articulation，其他无证据项保持 unknown；
- Scene delta：high internal activation + low external expressiveness + high restraint；
- pace：略快但不抢；volume：降低但不弱；
- pause：`三十骑` 后极短停顿；
- objective：取得主帅批准；subtext：献策同时试探是否授权跨越政治边界；
- boundary：不喊叫、不公开煽动、不演成拥有最终批准权。

### `spoken-s1-geshuhan-refusal`

- baseline：moderate/deliberate pace、firm articulation、high sentence finality；
- Scene delta：high internal activation + low external expressiveness + very high restraint；
- pace：略慢且审慎，但不拖沓；volume：降低但不弱；
- pause：开口前短停，`反臣` 后收束，`不可` 独立；
- objective：终结方案并维持军令与身份边界；
- boundary：当前 illness 不得演成低判断力、低控制力或低权威。

## 9. Semantic Invariants

以下规则同时受到 Skill 文本、typed request、Provider instruction 和 tests 保护：

```text
restraint HIGH != energy LOW                  PASS
physical fatigue/illness != authority LOW    PASS
older age != pace SLOW                        PASS
authority HIGH != volume HIGH                 PASS
anger HIGH != shouting                        PASS
urgency HIGH != always fast speech            PASS
confidence LOW != always quiet voice          PASS
```

Provider instruction 明确分成“长期基础声音”“当前场景状态”“本句表演变化”，Adapter 只做 semantic translation，不评价角色好坏。

## 10. Real Generation / Audio Evidence

### 真实调用结果

Skill Host 通过正式 `production.generate_audio` Tool 对两条 Dialogue 各调用一次。两次均返回预修复版本的通用：

```text
PROVIDER_ERROR
```

结果均没有：

- `mediaId`；
- provider request id；
- local Audio file；
-可用于确认“请求未送达”的状态。

旧 MCP adapter 把以下不同情况都包装成同一个错误：

- Provider 明确 4xx 拒绝；
- 既有 safe transient retry 已耗尽；
- request 可能到达但 response 不确定。

因此事后无法证明付费请求未送达。Host 在收到第一个通用错误时还不能识别 ambiguous 类型，随后执行了第二个预定 item；最终将两项保守标记为 `AMBIGUOUS`。没有外层 retry，也没有 reroll。

### Retry safety 最小修复

MCP adapter 现在分别输出：

```text
AMBIGUOUS_RESULT
PROVIDER_REJECTED
TRANSIENT_RETRY_EXHAUSTED
```

新增 MCP 测试确认具体 exception 语义不会再次被 generic `PROVIDER_ERROR` 抹平。由于本次两条历史请求无法重新分类，修复后**没有**重提付费请求。

### 技术验证

```text
REAL_AUDIO_CREATED = NO
AUDIO_TECHNICAL_VALIDATION = NOT_RUN
MEDIA_ROUNDTRIP = NOT_RUN
MINIO_ROUNDTRIP = NOT_RUN
```

这不是 Audio PASS，也不能进入用户听审。MinIO live preflight 自身为 PASS，但没有本批新 Audio 对象可做 roundtrip。

## 11. Tests

实际执行：

```text
drama-plugin/plugin:
  pytest -q                         145 passed
  mypy src/drama_plugin             PASS, 44 source files

drama-mcp-service:
  pytest -q                         17 passed
  mypy src/drama_mcp_service        PASS, 4 source files

drama-service/server:
  IntelliJ Maven 3.9.16 mvn test    33 passed, 0 failures/errors/skips

plugin-creator validate_plugin.py   PASS
skill quick_validate.py             PASS
```

OpenAI real calls：`0`。OpenAI adapter 仅离线回归。ComfyUI calls：`0`。

Runtime preflight：MCP health PASS；Drama persisted context reads PASS；MySQL-backed reads PASS；MinIO live PASS；`REAL_TTS_E2E` enabled；speech mode matched；credential 仅记录 `PRESENT`。

## 12. Git Diff

开始时三个 repository 已有未提交修改，均被保留：

- `drama-plugin`：Batch 7.2R/7.2S 的 report、integration、speech/media/contracts/tests 修改；
- `drama-mcp-service`：Settings path fix 与 protocol/settings tests；
- `drama-service`：既有 Media import/roundtrip 相关 9 个文件；本批未改 Java；
- workspace root：不是 Git repository，已有 Batch artifacts 未删除或覆盖。

本批最小新增/修改：

- Audio Skill 的通用中性人物规则和 scene-aware reference；
- `CharacterUnderstanding`、`SceneState` 与扩展 Voice Profile typed objects；
- provider-neutral request/fingerprint 的 scene-state 传播；
- 小型 profile-vector voice candidate ranking；
- Bailian/OpenAI Adapter 的候选解析与 stable/scene instruction 分段；
- production Media 的 candidate ranking / pending binding evidence；
- Character neutrality、value-neutral vocabulary、identity rename、semantic invariant tests；
- MCP paid retry error classification 与测试；
- 7.2S-R evidence、validator 与本报告；
- Plugin cachebuster/reinstall 至 `0.1.0+codex.20260826153008`。

这些变更均直接服务 7.2S-R；没有数据库迁移、没有新的 vendor-specific Tool、没有图像/视频/AV 改动。

## 13. Final Status

```text
BATCH_7_2S_R = AMBIGUOUS

CHARACTER_MODEL_GENERIC = PASS
CHARACTER_SPECIFIC_RULES = NONE
VALUE_NEUTRAL_PROFILE = PASS

CHARACTER_UNDERSTANDING = PASS
STABLE_STATE_SEPARATION = PASS
VOICE_PROFILE = PASS
PERFORMANCE_INTENT = PASS

SEMANTIC_INVARIANTS = PASS
PROVIDER_NEUTRALITY = PASS

VOICE_CANDIDATES_GENERATED = RANKING_ONLY
VOICE_BINDING = PENDING

PRODUCTION_GENERATE_AUDIO_CALLS = 2
CONFIRMED_PROVIDER_CALLS = UNKNOWN
AMBIGUOUS_ITEMS = 2
REAL_AUDIO_CREATED = NO
AUDIO_TECHNICAL_VALIDATION = NOT_RUN
MEDIA_ROUNDTRIP = NOT_RUN

USER_AUDIO_REVIEW = NOT_READY
AUDIO_APPROVED = NOT_SET

COMFYUI_CALLS = 0
IMAGE_GENERATION = NOT_STARTED
VIDEO_GENERATION = NOT_STARTED
BATCH_7_3 = NOT_STARTED
```

验收问题：

```text
A. 同一 profile 改名后 Voice Profile / Casting 保持一致？ YES
B. 人物由中性多维描述，而非年龄+性别+标签？ YES
C. 可表达疲惫但集中、低声但有控制力、克制但高能量等组合？ YES
D. Skill 是否不知道 concrete voice 与 Provider 名？ YES
E. 最终声音是否合适？ 本批没有可安全确认的新 Audio，不能由 Codex 判断。
```

本批在 ambiguous paid request 边界停止，没有进入 Batch 7.3。
