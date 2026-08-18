# Batch 6.0R — Historical Story Architecture & Narrative Continuity Hardening 执行报告

## 1. Final Result

```text
BATCH_6_0R = PASS

TECHNICAL_SKILL_HARDENING = PASS
CREATIVE_REGRESSION = PASS
FULL_NARRATIVE_REVIEW = PASS

SKILL_AUDIT = PASS
HISTORICAL_SCOPE_FIRST = PASS
HISTORICAL_SPINE_REQUIRED = PASS
NARRATIVE_AUTHORITY_REQUIRED = PASS

FACT_ATTRIBUTION_VALIDATION = PASS
PROTAGONIST_SCOPE_ALIGNMENT = PASS
UNSUPPORTED_CAUSAL_PROMOTION_BLOCKED = PASS
DRAMATIZATION_DELETION_TEST = PASS

PREMATURE_SHOT_QUOTA_REMOVED = PASS
STRUCTURE_FROM_STORY_COVERAGE = PASS

SCENE_STATE_CONTINUITY = PASS
SHOT_STATE_CONTINUITY = PASS
SAME_SHORT_COMMAND_REGRESSION = PASS

COMFY_CLOUD_CALLED = NO
PROVIDER_CREDITS_SPENT = NO

JAVA_DOMAIN_MODEL_CHANGED = NO
NEW_FRAMEWORK_ADDED = NO
EVENT_SPECIFIC_HARDCODING = NO
```

唯一业务输入严格为：

```text
创作一部关于安史之乱前期潼关之战的历史短剧。
```

执行通过正式 `MCP → Plugin → Java → MySQL` Contract 停止于 Shot Planning。未调用 Asset、Media、Production 或 Comfy Cloud。

## 2. Batch 6.0 Root Cause

| 维度 | Batch 6.0 表面结果 | 实际问题 |
|---|---|---|
| Visual Continuity | 人物、服装、道具、时代视觉一致 | 只能证明画面元素稳定，不能证明故事完整。 |
| Narrative Continuity | 旧报告以单一 Cross-Scene PASS 收口 | 从军议直接跳到大战，整军、出关、行军、抵达、部署等状态缺失。 |
| Historical Causality | 结果未改写 | 守险判断、诱敌识别和败局行动被下沉给 Supporting Actor，实际“为什么发生”已漂移。 |
| Protagonist / Scope | 选择王思礼作为“非帝王视角” | Scope 仍声称讲完整潼关之战，却让 SECONDARY actor 承担主决策与主战场因果。 |
| Premature Structure Quota | 单集、2 Scenes、4 Shots 技术可生产 | 配额先于历史骨架，导致只保留“好拍”的军议和败阵片段。 |

根因不是 Java Contract 或视觉 Provider，而是 Work 的传统原创剧本模板把主动主角、internalNeed、关系弧和个人高潮当成先验硬要求；下游 Review 又未独立检查 Historical Beat Coverage 和 Causal Narrative Continuity。

## 3. Old Work Audit

旧 Work 通过正式 `work.get_work` 只读，未修改：

```text
workId = work_084411597e604d80ab704b299e73b254
title = 《潼关烟阵》
```

具体缺陷：

1. `evidenceBoundary.sourceSupported` 只写“潼关守军主张据险坚守”，但 `protagonist.agency` 收窄为王思礼“提出守险判断”。史料明确记载守险奏议由哥舒翰提出，郭子仪、李光弼另行上言；这是 `UNSUPPORTED_CAUSAL_PROMOTION`。
2. `protagonist.agency` 又赋予王思礼“辨识诱敌征兆、在崩阵中组织可执行的撤退”。史料支持其率精兵居前，不支持其承担全军识破诱敌或决定撤退的主因果。
3. `internalNeed` 把人物塑造成“从服从命令到见证与补救”的心理成长；`relationshipArcs` 又虚构其与哥舒翰、军令之间的信任变化。这些字段反过来要求剧情证明一个无直接证据的现代人物弧。
4. `stakes.personal` 和 `stakes.relational` 为王思礼追加失关责任及信任撕裂，进一步把事件中心从主帅、朝廷命令和伏击因果移到 Supporting Actor。
5. `storyArchitecture.escalation` 写“王思礼的劝阻无法改变皇命”，错误把史载哥舒翰的守险奏议收窄给王思礼。
6. `storyArchitecture.climax` 写王思礼“打开退路、传回失关警报”，以虚构个人行动替代大军崩溃、残部入关、崔乾祐攻克潼关的历史高潮。
7. `creativeBrief.format` 预设“单集、后续按2个真实场景展开”；`shortFormSuitability` 预设“四个核心视觉镜头”。结构预算先于完整 Historical Spine。
8. 2 Scene / 4 Shot 只覆盖“关内接令”和“战场败阵”，删除了出关、行军、灵宝地形、交兵诱敌、伏击机制、八千余人入关、潼关被克、哥舒翰收卒与被执等必要 Beat/Transition。

## 4. Changed Skill Rules

最小修改集中在现有 Markdown Skill Core、`skill.yaml`、`agents/openai.yaml` 和现有测试，没有增加实体、表或编排框架。

- Historical Research：要求保留 source-supported actor granularity、因果角色、顺序和 Scope。
- Work：强制 `Research → Scope → Spine → Actor Hierarchy → Narrative Authority → Protagonist → Architecture → Structure Estimate`。
- Protagonist：完整主战场/主决策 Scope 只能从 PRIMARY authority 选择；Supporting Actor 要做主角必须缩小 Scope。
- Actor Attribution：集体、机构、职位或未具名群体不得无证据收窄为具体人物。
- Traditional Arcs：`internalNeed`、私人关系弧与 Personal Stakes 降为可选、解释性、非因果材料。
- Theme：只能由 Historical Spine 已有事件产生。
- Architecture：每个主要节点必须列出 `spineBeatIds`。
- Dramatization：重要 `DRAMATIZED_BUT_COMPATIBLE` 情节必须通过删除测试。
- Structure：改为 Coverage First；episodes/scenes/shots 只是可调整估算。
- Episode / Scene / Shot：增加 Narrative Input State、Required Transition、Narrative Output State。
- Continuity：视觉、服装、道具、动作、Scene State、历史 Beat、因果叙事与 Full Story Arc 分开判定。

## 5. Historical Story Pipeline

```text
Research
→ Historical Scope
→ Historical Spine
→ Historical Actor Hierarchy
→ Narrative Authority
→ Protagonist
→ Story Architecture
→ Structure Estimate
```

研究采用可追溯史籍文本，重点依据《资治通鉴》卷218记载的守险奏议、连续催战、出关、灵宝西原地形、诱敌伏击、烟火后袭、败退、失关及被执因果，并以《旧唐书》本纪/列传交叉限定结果和人物身份：

- [《资治通鉴》卷218](https://zh.wikisource.org/zh-hant/資治通鑑/卷218)
- [《旧唐书》卷9](https://zh.wikisource.org/zh-hant/舊唐書/卷9)
- [《旧唐书》卷104](https://zh.wikisource.org/zh-hant/舊唐書/卷104)
- [《旧唐书》卷106](https://zh.wikisource.org/zh-hant/舊唐書/卷106)

正式 Research Provider 可靠性问题仍延后；本批未把无关 Provider 证据写入 Work。

## 6. New Work Result

```text
workId = work_cc24a19e38bc490a937a5957c2cb020b
scriptId = script_03f775178d11466aa294184ef968f896
episodeId = episode_8db9b95222a546fc87ddae1572a38230
```

### Historical Scope

天宝十五载潼关守势被朝廷强令转为出关决战，至灵宝西原惨败、潼关失守与主帅被执的完整军事因果及直接后果。

### Historical Spine

| Beat | Actor | Event | Causal Effect | Evidence |
|---|---|---|---|---|
| H1 | 潼关唐军与叛军 | 叛军数月不能越关，守势有效 | 固守具备军事依据 | DOCUMENTED |
| H2 | 唐玄宗/朝廷、杨国忠、哥舒翰、郭李 | 羸弱情报、守险奏议、连续催令、被迫出关 | 守势被命令打断 | DOCUMENTED |
| H3 | 双方军队 | 相遇灵宝西原，南山北河、狭道绵长 | 唐军纵深拥塞 | DOCUMENTED |
| H4 | 崔乾祐、哥舒翰、王思礼等 | 散弱示形、伏兵在后、唐军推进、偃旗佯退 | 伏击条件成熟 | DOCUMENTED |
| H5 | 崔乾祐所部与唐军 | 木石、火烟、误射、南山精骑后袭 | 首尾失应、全线崩溃 | DOCUMENTED |
| H6 | 唐军残部、哥舒翰、崔乾祐 | 大败、八千余人入关、潼关被克 | 长安门户失去 | DOCUMENTED |
| H7 | 哥舒翰、火拔归仁、叛军 | 关西驿收卒欲复守，主帅被挟持东行 | 立即复守可能消失 | DOCUMENTED |

### Historical Actor Hierarchy / Narrative Authority

| Actor | Authority | Scope 内作用 |
|---|---|---|
| 哥舒翰 | PRIMARY | 跨越守险奏议、执行出关、战场指挥、败后收卒和被执。 |
| 唐玄宗及朝廷决策 | PRIMARY | 连续皇命直接触发出关。 |
| 崔乾祐 | PRIMARY | 选择战场、诱敌伏击并攻克潼关。 |
| 杨国忠 | SECONDARY | 以政治猜疑推动催战，但不是最终命令主体。 |
| 王思礼等前军将领 | SECONDARY | 率前军参战；不承担守险奏议或全军识破伏击。 |
| 火拔归仁 | SECONDARY | 败后挟持哥舒翰，决定主帅个人结局。 |

### Protagonist

```text
protagonist = 哥舒翰
narrativeAuthority = PRIMARY
selectionBasis = H2 + H4 + H6 + H7 的真实历史作用
selectionBasis != 更容易影视化
```

### Story Architecture

| Node | Spine Mapping |
|---|---|
| Starting State | H1 |
| Disruption | H2 |
| Escalation | H2 |
| Reversal | H3 + H4 |
| Crisis | H5 |
| Climax | H6 |
| Ending | H7 |
| Final State | H6 + H7 |

### Structure Estimate

```text
episodes = 1
scenes = 6
shots = 23
reasoning = H1—H7 覆盖 → 必要状态过渡 → Scene 动作/信息密度 → 最少 Shot 覆盖
quota = NO
adjustable = YES
```

## 7. Old vs New Comparison

| 比较项 | Batch 6.0 Old | Batch 6.0R New |
|---|---|---|
| 主角选择 | 王思礼，因行动视点和戏剧便利升格 | 哥舒翰，由完整 Scope 下 PRIMARY authority 推导 |
| 历史因果 | 守险/识伏/撤退下沉给王思礼 | 皇命、哥舒翰奏议/执行、崔乾祐伏击各归其主 |
| 虚构 Agency | 个人劝阻、识破、救人撤退承担高潮 | 兼容动作可删，删除后 H1—H7 仍成立 |
| 人物弧 | internalNeed 与关系弧推动主线 | 不要求心理成长；只保留史实身份关系边界 |
| Historical Beat | 片段式覆盖 | H1—H7 全覆盖 |
| Scene | 2，直接从军议跳战场 | 6，保留出关/行军/抵达/部署/伏击/失关/被执 |
| Shot | 4 个视觉配额 | 23 个由动作与信息密度反推的最少覆盖 |
| 剧情完整性 | Beginning 与败阵片段存在，中间因果和结局不足 | Beginning → Development → Crisis → Climax → Ending 完整 |

## 8. Episode / Scene / Shot Tree

```text
Work  《潼关失守》Batch 6.0R
└── Script  《潼关失守》历史短剧剧本
    └── Episode 1  关失人执（H1—H7）
        ├── Scene 1  关图与叠诏（H1,H2）
        │   ├── 1-01 守势仍固
        │   ├── 1-02 羸兵军报
        │   ├── 1-03 守险奏议
        │   └── 1-04 中使项背
        ├── Scene 2  出关入狭原（H2,H3）
        │   ├── 2-01 抚膺出令
        │   ├── 2-02 大军出关
        │   └── 2-03 南山北河
        ├── Scene 3  散阵诱进（H3,H4）
        │   ├── 3-01 狭道列军
        │   ├── 3-02 散如列星
        │   ├── 3-03 催军推进
        │   └── 3-04 偃旗欲遁
        ├── Scene 4  烟焰合围（H5）
        │   ├── 4-01 木石骤下
        │   ├── 4-02 氈车前驱
        │   ├── 4-03 草车纵火
        │   ├── 4-04 烟中误射
        │   └── 4-05 精骑断后
        ├── Scene 5  八千入关（H6）
        │   ├── 5-01 两岸皆空
        │   ├── 5-02 河壕塞路
        │   ├── 5-03 八千余入
        │   └── 5-04 关门陷落
        └── Scene 6  关西驿被执（H7）
            ├── 6-01 榜收散卒
            ├── 6-02 百骑围驿
            └── 6-03 关失人执
```

## 9. Narrative Transition Matrix

| Shot | Previous Output State | Current Input State | Required Transition | Result |
|---|---|---|---|---|
| 1-01 | 潼关守势有效 | 同状态 | 观察确认叛军仍受阻 | PASS |
| 1-02 | 羸弱军报入关 | 同状态 | 呈递军报 | PASS |
| 1-03 | 出关命令进入军议 | 同状态 | 哥舒翰陈述守险并回奏 | PASS |
| 1-04 | 守险意见未获采纳 | 同状态 | 连续中使压至最终整军令 | PASS |
| 2-01 | 准备出关 | 同状态 | 哥舒翰签发出关军令 | PASS |
| 2-02 | 关门开启 | 同状态 | 前后军依次出关 | PASS |
| 2-03 | 主力离开守险位置 | 同状态 | 行军抵达南山北河狭道 | PASS |
| 3-01 | 狭道展开受限 | 同状态 | 展示山河夹逼 | PASS |
| 3-02 | 军列压成长纵列 | 同状态 | 观察散弱敌阵 | PASS |
| 3-03 | 见敌少且散弱 | 同状态 | 哥舒翰催军，王思礼等居前 | PASS |
| 3-04 | 前锋深入 | 同状态 | 敌军偃旗、唐军松弛 | PASS |
| 4-01 | 伏击条件成熟 | 同状态 | 木石截断前锋 | PASS |
| 4-02 | 前锋受阻 | 同状态 | 氈车尝试冲开 | PASS |
| 4-03 | 氈车进入前端 | 同状态 | 草车堵塞并纵火 | PASS |
| 4-04 | 烟焰遮眼 | 同状态 | 唐军烟中误射 | PASS |
| 4-05 | 箭尽阵乱 | 同状态 | 同罗精骑越山击后 | PASS |
| 5-01 | 全线开始崩溃 | 同状态 | 前败传后、两岸皆溃 | PASS |
| 5-02 | 败兵奔河谷与关门 | 同状态 | 溺河、坠壕、争关 | PASS |
| 5-03 | 少量残部近关 | 同状态 | 八千余人入关 | PASS |
| 5-04 | 原防线无法恢复 | 同状态 | 崔乾祐乘胜攻关 | PASS |
| 6-01 | 关失、哥舒翰至关西驿 | 同状态 | 张榜招收散卒 | PASS |
| 6-02 | 散卒聚集但不足 | 同状态 | 火拔归仁围驿挟持 | PASS |
| 6-03 | 主帅失去自由东行 | 同状态 | 关门与主帅共同进入终态 | PASS |

所有 Scene Boundary 均有可见/可叙述过渡；没有再从“军议厅接令”直接跳到“几十里外大战”。

## 10. Review Gates

### Work Gates

| Gate | Result |
|---|---|
| HISTORICAL_SPINE_COMPLETE | PASS |
| FACT_ATTRIBUTION_VALID | PASS |
| PROTAGONIST_SCOPE_ALIGNMENT | PASS |
| UNSUPPORTED_CAUSAL_PROMOTION_ABSENT | PASS |
| DRAMATIZATION_NON_CAUSAL | PASS |
| STORY_ARCHITECTURE_SPINE_ALIGNED | PASS |
| STRUCTURE_COVERS_SPINE | PASS |

### Full Narrative Gates

| Gate | Result |
|---|---|
| CHARACTER_VISUAL_CONTINUITY | PASS_AT_TEXT_PLAN_LEVEL |
| COSTUME_PERIOD_CONTINUITY | PASS_AT_TEXT_PLAN_LEVEL |
| PROP_STATE_CONTINUITY | PASS_AT_TEXT_PLAN_LEVEL |
| SHOT_ACTION_CONTINUITY | PASS |
| SCENE_STATE_CONTINUITY | PASS |
| CAUSAL_NARRATIVE_CONTINUITY | PASS |
| HISTORICAL_BEAT_COVERAGE | PASS |
| FULL_STORY_ARC | PASS |

Full Narrative Review 回答：

- 历史主线完整：是，H1—H7 全覆盖。
- 主战场主体保留：是，朝廷、哥舒翰、崔乾祐及军队作用未被替换。
- Supporting Actor 升格承担主因果：无。
- 重要 Historical Beat 消失：无。
- Scene 间重大状态跳跃：无。
- Shot 间无法解释的动作跳跃：无。
- 删除兼容戏剧化后主因果仍成立：是。
- Beginning → Development → Crisis → Climax → Ending：完整。

```text
FULL_NARRATIVE_REVIEW = PASS
```

## 11. Generic Tests

新增通用 fixture：`tests/fixtures/creative-quality/historical-narrative-hardening.yaml`。

| Case | Expected | Result |
|---|---|---|
| A — 集体“诸将建议固守”不得收窄给无证据人物 | UNSUPPORTED_CAUSAL_PROMOTION / FAIL | PASS |
| B — Scope 不变时 Supporting Actor 不得升级 | PROTAGONIST_SCOPE_ALIGNMENT / FAIL | PASS |
| C — 用户指定 peripheral actor 时可缩小 Scope，但不转移主因果 | PASS | PASS |
| D — 删除兼容戏剧化后 Spine 仍成立 | PASS | PASS |
| E — 小规模偏好不得删除 Required Beat | STRUCTURE_COVERS_SPINE / FAIL | PASS |

测试结果：

```text
Skill targeted tests: 39 passed
Plugin suite excluding Windows symlink privilege case: 91 passed, 1 deselected
Full plugin suite: 91 passed, 1 environment failure
```

唯一全量失败为既有 `test_local_file_security` 在当前 Windows 账户创建 symlink 时触发 `WinError 1314`。未修改、绕过或重新引入任何 Windows `file://` allowed-roots 逻辑。

## 12. Hardcoding Audit

执行：

```text
rg "潼关|安史之乱|哥舒翰|王思礼|崔乾祐|安禄山" plugin/skills plugin/src
```

结果：

```text
NO_EVENT_SPECIFIC_TERMS_IN_SKILL_CORE_OR_PRODUCTION_SOURCE
```

事件与人物只存在于本报告和允许的 Regression artifact；通用测试使用匿名军队、机构、PRIMARY/SECONDARY actor，不含本事件特判。

## 13. Changed Files

### Historical Research（3）

- `skills/historical-research/SKILL.md`：增加 actor granularity 与因果角色保真。
- `skills/historical-research/skill.yaml`：增加研究完成条件。
- `skills/historical-research/agents/openai.yaml`：默认提示覆盖 Scope、顺序与 attribution。

### Work Creation（5）

- `skills/work-creation/SKILL.md`：改为 Historical-first 生命周期、硬 Gate、删除测试与 coverage-first persistence。
- `skills/work-creation/references/planning.md`：重写为 Scope→Spine→Authority→Protagonist→Architecture→Estimate。
- `skills/work-creation/references/review.md`：新增二元历史 Gate 与 failure codes。
- `skills/work-creation/skill.yaml`：更新完成条件，取消传统人物弧硬要求。
- `skills/work-creation/agents/openai.yaml`：更新默认入口提示。

### Script Adaptation（5）

- `skills/script-adaptation/SKILL.md`：继承 Scope/Spine/Authority/Attribution 与 required beat coverage。
- `skills/script-adaptation/references/planning.md`：Episode architecture 改为 coverage-derived、可调整。
- `skills/script-adaptation/references/review.md`：增加 beat、attribution、dramatization gates。
- `skills/script-adaptation/skill.yaml`：更新完成条件。
- `skills/script-adaptation/agents/openai.yaml`：强调不得改变历史因果。

### Episode Development（5）

- `skills/episode-development/SKILL.md`：加入 assigned beats 与 Narrative Input/Transition/Output。
- `skills/episode-development/references/planning.md`：补 required transition 规划。
- `skills/episode-development/references/review.md`：补 coverage、attribution、transition rows。
- `skills/episode-development/skill.yaml`：更新完成条件。
- `skills/episode-development/agents/openai.yaml`：更新默认提示。

### Scene Development（5）

- `skills/scene-development/SKILL.md`：加入 Scene narrative-state contract 与 FAIL_NARRATIVE_TRANSITION。
- `skills/scene-development/references/planning.md`：要求 Scene Boundary 状态承接。
- `skills/scene-development/references/review.md`：拆分 Scene State / Causal Narrative Continuity。
- `skills/scene-development/skill.yaml`：更新完成条件。
- `skills/scene-development/agents/openai.yaml`：更新默认提示。

### Shot Design（5）

- `skills/shot-design/SKILL.md`：要求每 Shot 的三态字段并拆分八项 Gate。
- `skills/shot-design/references/planning.md`：叙事状态与视觉状态并列规划。
- `skills/shot-design/references/review.md`：增加 Historical Beat、Full Arc 与 narrative transition gate。
- `skills/shot-design/skill.yaml`：更新完成条件。
- `skills/shot-design/agents/openai.yaml`：更新默认提示。

### Tests / Regression / Report（4）

- `tests/test_skills.py`：新增通用 Gate、continuity 拆分和 hardcoding 审计测试。
- `tests/fixtures/creative-quality/historical-narrative-hardening.yaml`：新增 Case A—E 通用 fixture。
- `integration/run_batch6_0r_text_regression.py`：Windows 可运行的正式 MCP 文本回归；显式禁止视觉工具并停止在 Shot。
- `docs/reports/06-00R-historical-story-architecture-hardening.md`：本报告。

未修改任何 Java 文件、数据库 schema、Comfy Adapter、OAuth、Spend Gate、媒体导入或 Windows allowed-roots 代码。

## 14. Deferred Issues

以下问题均记录为 `DEFERRED_TO_BATCH_6_1`，本批未修改：

- Comfy OAuth refresh concurrency / `refresh token reuse detected`。
- OAuth Host UI 行为。
- Spend Gate 在未 confirm 探测下的入队风险。
- Research Provider reliability：曾返回与主题无关证据且误判 supported。
- Windows 非管理员账户的 symlink 测试权限（不等同于 `file://` allowed-roots 缺陷）。

## 15. Next Step

```text
FULL_NARRATIVE_REVIEW = PASS
NEXT_BATCH_6_1_READY = YES
```

本批到 Shot Planning 为止。下一步可以进入 Batch 6.1，但本报告未提前执行 Asset、Image、Video、Audio、Media、TTS、BGM、Lip Sync 或 Final Render。
