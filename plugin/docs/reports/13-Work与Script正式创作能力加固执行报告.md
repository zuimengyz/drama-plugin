# 13-Work 与 Script 正式创作能力加固执行报告

执行日期：2026-08-14（Asia/Shanghai）
执行批次：Creative Skill 加固 Batch 2
执行仓库：`drama-plugin`

## 1. 执行摘要

本批已在 Batch 1 七阶段 Creative Lifecycle 不变的前提下，为 `work-creation` 和 `script-adaptation` 建立可执行的专业 Planning、完整 Draft、领域 Review、分级 Revision 与强化 Persist Gate。

Work 现在能够指导 Agent 把历史事件转化为角色驱动的正式 Story Foundation：先建立创作简报和史实边界，再比较关键候选、选择戏剧中心，设计主人公目标/内在需求、对抗、代价、人物与关系弧、premise/logline、主题问题、因果结构、高潮与结局，并拒绝历史摘要、时间线、人物列表等低质量替代品。

Script 现在先建立 Adaptation Contract，继承已批准 Work，再规划因果主线、必要支线、可观察人物弧、冲突升级、信息揭示、Episode Architecture、短剧节奏、screenability 与对白策略，并拒绝剧情梗概、事件列表、机械分集、不可演内心叙述及 Work drift。

为保持 Skill Core 精简，两个主 `SKILL.md` 仍各为 44 行；深度方法拆为四个直接引用、单层、短小的 references。新增两类题材的静态/人工质量评测 fixture：政治事件驱动的神龙政变，以及人物关系驱动的唐太宗—魏征君臣关系。生产 Skill 未硬编码测试题材。

最终验证：Skill tests 18 passed，Drama Plugin 69 passed，mypy 34 个源码文件通过，8 个 Skill 校验全部通过，Drama MCP Service 13 passed，Tool Registry 仍为 44，Tool Contract SHA-256 与 Batch 1 相同。

## 2. Batch 1 基线复核

执行前完整复核：

- `docs/reports/11-创作型Skill正式化审计与设计报告.md`；
- `docs/reports/12-创作型Skill生命周期基线加固执行报告.md`；
- Work/Script 当前 `SKILL.md`、`skill.yaml`；
- `tests/test_skills.py`；
- Tool catalog/registry、Context 与 Research 边界；
- MCP 动态投影与 Java 长期记忆边界。

当前仓库与报告结论一致。Batch 1 已建立的阶段、顺序和硬规则均保留：

```text
Understand Goal
→ Gather Context
→ Plan
→ Execute Draft
→ Review
→ Revise or Re-plan
→ Review Again
→ Persist
```

自动化测试继续验证：Context 不足时阻断、Plan/Draft/Review notes 不持久化、Review FAIL 禁止写入、修订后必须 Review Again、Review PASS 后才能 create/save。

## 3. 本批修改范围

### MODIFIED

```text
skills/work-creation/SKILL.md
skills/work-creation/skill.yaml
skills/script-adaptation/SKILL.md
skills/script-adaptation/skill.yaml
tests/test_skills.py
```

### ADDED

```text
skills/work-creation/references/planning.md
skills/work-creation/references/review.md
skills/script-adaptation/references/planning.md
skills/script-adaptation/references/review.md
tests/fixtures/creative-quality/work-script-evaluations.yaml
docs/reports/13-Work与Script正式创作能力加固执行报告.md
```

没有修改 `agents/openai.yaml`，也没有修改 Episode、Scene、Shot、Asset、Production 或 Historical Research Skill。

## 4. Work Skill 修改前问题

Batch 1 Work 已有生命周期、Context 规则和基础 Review，但专业内容仍以 theme、viewpoint、relationships、conflict、timeline、structure 等结果要素为主，缺少从历史材料形成这些结果的方法。

主要风险是 Agent 虽然会先 Plan 和 Review，仍可能把以下内容主观判为“完整”：

```text
事件摘要
年代顺序
人物简介
主题标签
一句 premise
```

缺少的不是 Work Tool，而是事件到故事的推导方法、方案选择、角色驱动因果、专业 Review rubric 与反摘要 Gate。

## 5. Work 专业 Planning 设计

新增 `references/planning.md`，在 Work `Plan` 阶段强制按需读取。方法按八步组织：

1. 建立类型、受众、体量、短剧形式、基调、时代和用户约束的 Creative Brief；
2. 建立 documented/supported、disputed/uncertain、dramatic invention space 三类证据边界；
3. 把历史事件转化为压力→目标/选择→对抗→后果→更高代价→不可逆决定→高潮；
4. 对主人公、视角、切入点、核心冲突与高潮做简短候选比较后选择；
5. 设计 agency、opposition 与 escalating stakes；
6. 形成 premise、logline 和 thematic question；
7. 设计 relationship arc 与灵活的因果故事结构；
8. 检查是否形成足以供 Script 直接继承的完整 Draft Contract。

非关键缺失允许保守假设并留在内部 Plan；关键约束冲突则阻断。Plan、候选与取舍仍是 Agent Run 内部状态，不创建 Plan 实体。

## 6. Historical Event → Story 方法

Work 方法现在明确区分：

```text
historical importance ≠ dramatic story
```

Agent 必须找到一个承受压力、主动追求目标并作出不可逆选择的戏剧中心。历史事实提供限制、条件和结果，不自动等于剧情。事件必须通过人物选择与后果建立因果，而不能只按日期连接。

主人公不必是最著名的人，但必须具备可持续的目标、压力、选择、主题关联和观众入口。允许单主人公、双主人公或有限群像，但核心戏剧中心必须清楚。

## 7. Work 人物/冲突/主题/结构设计

Work Planning 现要求：

- 人物弧包含 external goal、internal need/blind spot、压力、选择、后果、不可逆决定和最终状态；
- 对抗可以来自人物、群体、制度、期限、身份、历史力量、自我或竞争忠诚，但必须有合理目标、逻辑和行动能力；
- stakes 可覆盖个人、关系、政治、社会、历史和道德层，且逐步升级，不得靠篡改史实虚增；
- premise/logline 必须包含主人公、主动目标、对抗、代价和独特历史情境；
- theme 必须转化为由选择和结局检验的 dramatic question，而不是标签或说教；
- 关系必须具有 initial state、冲突来源、决定性变化和 final state；
- 结构不强制三幕式或商业模板，但必须有起点、触发、升级、重大变化、危机、高潮、结局及最终状态。

## 8. Work Historical Boundary

Work 在 Planning 与 Review 中均使用三类证据边界。禁止：

- 改变已确立的关键结局；
- 把不在场人物写入决定性事件；
- 反转有较强证据的关键因果；
- 把争议解释写成确定事实。

允许在不冲突前提下合理虚构对白、私人互动、情绪、动机、合并相遇和时间压缩。关键证据不足时形成 focused research question 并停止 Plan/Persist；不重复研究已充分支持的事实。

## 9. Work Review Rubric

新增 13 项全部为 Critical 的 Work Review：

```text
Story Identity
Protagonist
Motivation
Opposition
Stakes
Dramatic Causality
Character Arc
Relationship Arc
Theme
Structure
Historical Integrity
Short-form Suitability
Downstream Readiness
```

每项同时定义 PASS evidence 与 FAIL signal。任何一项未解决即 Review FAIL，不通过平均分掩盖关键缺陷。

## 10. Work Anti-patterns

Review 明确识别并拒绝：Historical Summary、Chronology Dump、Character List、Theme Label、Conflict Label、No Stakes、Passive Protagonist、Villain Flattening、Historical Drift、Over-Scripting。

这些规则直接进入 Work Persist Gate：事件摘要、主题标签、人物列表、时间线、一句 premise、被动主人公、无行动能力的对抗、无 stakes、无高潮/结局的候选均不得写入。

## 11. Work Revision / Persist Gate

局部措辞、清晰度、标签或轻微一致性问题使用 local revise。主人公 agency、premise、核心冲突、opposition、stakes、主题问题、因果结构、高潮、人物/关系弧、短剧体量或史实边界失败时 re-plan；多处结构互相失效时整体重写 Draft。

任何修订后都必须重新执行完整 rubric。只有达到 `formal story foundation` 且全部 Critical Check PASS 才能调用 `work.create_work` 或 `work.save_work`。

## 12. Script Skill 修改前问题

Batch 1 Script 已要求继承 Work、形成可观察 action、规划主/支线、人物弧、节奏、升级和高潮，但仍缺少：

- 明确 Adaptation Contract；
- 主线的选择—后果因果方法；
- Work arc 到可观察行为的转换；
- 信息揭示策略；
- 具有戏剧任务的 Episode Architecture；
- screenability 与对白最低标准；
- 剧情梗概、机械分集与不可演叙述的专业拒绝条件。

## 13. Script Work Inheritance

Script Plan 首先记录必须继承的 Work：premise、protagonist、major arcs、central conflict、stakes、thematic question、historical boundary、major turns、ending、format、audience 与 tone。

Script 可重新设计 screen structure、episode allocation、information reveal、visual storytelling、dialogue strategy 和 pacing，但不得暗中替换主人公、premise、主题、史实边界或重大结局。若缺陷源于 Work，应标记 `upstream Work issue`，不得偷偷改出另一部作品，也不得自动调用其他 Skill。

## 14. Script 专业 Planning

新增 `references/planning.md`，在 Script `Plan` 阶段强制按需读取。Planning 按以下结构执行：

1. 建立 Adaptation Contract；
2. 形成全剧 causal main line；
3. 控制只服务主线/人物弧/主题/高潮的 secondary lines；
4. 把人物弧映射为可观察行动、决定、失败、关系与行为变化；
5. 规划 audience/character knowledge 与 information reveal；
6. 让 conflict escalation 增加代价、约束与不可逆性；
7. 按 dramatic job 和 state change 规划 Episode Architecture；
8. 调整短剧节奏；
9. 建立 screenability/dialogue 策略；
10. 形成足以交给 Episode Skill 的完整 Script Draft Contract。

## 15. Script 主线/支线/人物弧

每个主要结构段必须回答：当前追求、增强的阻力、主人公决定、新后果和改变后的 story state。主线拒绝把历史事件简单串联。

支线必须服务主线、人物弧、主题、高潮或核心关系之一；短剧中无关、重复、体量过大的支线应删除、合并或降级。

Work 层抽象人物弧必须转化为屏幕可见的行动、压力下决定、牺牲、失败、关系和行为变化，不能用“逐渐成长”等内心总结代替。

## 16. Script Conflict Escalation

冲突从 initial problem 经 complication、higher cost、narrowing options、irreversible decision、crisis 到 climax。每次升级至少改变 goal、danger、knowledge、loyalty、relationship 或 available choice 之一，避免每集重复同一种朝堂争论或政治讨论。

## 17. Script Information Reveal

Planning 跟踪观众和主要人物在关键时刻各自知道什么，并明确谁发现、如何发现、信息改变了哪个决定或关系。优先通过 action、conflict、discovery、behavior、environment、reaction 和 consequence 进入剧情，拒绝双方都知道却互相讲解的历史课对白。

## 18. Script Episode Architecture

Script 可以规划 Episode Architecture，但不创建 Episode Entity。每个拟议单元包含 sequence number、dramatic job、entry state、central conflict/turn/discovery、exit state 及因果 hook/resolution。

分集按戏剧任务和状态变化，不按页数、年份或事件数量平均切分。单集内部详细设计仍由 `episode-development` 后续负责。

## 19. Script Screenability / Dialogue

重要内容必须通过可观察或可听见的 action、behavior、dialogue、visual detail、environment、reaction 与 choice 表达。内心和抽象历史判断必须转化为表演可执行信息。

对白需要目标和互动，避免双方都知道的事实、历史教材式讲解、同质声音和脱离行动的台词；允许潜台词，不强制金句。Script 只给 screen progression 与代表性行为，不写完整 Scene 或 camera coverage。

## 20. Script Review Rubric

新增 16 项全部为 Critical 的 Script Review：Work Fidelity、Main Line、Character Motivation、Character Arc、Secondary Lines、Conflict Escalation、Causality、Information Reveal、Episode Architecture、Pacing、Screenability、Dialogue、Historical Integrity、Climax and Payoff、Ending Fidelity、Downstream Readiness。

每项定义 PASS evidence 与 FAIL signal。任何 Material Work drift、缺失主线/人物弧/升级/高潮或不可演结果均为 Review FAIL。

## 21. Script Anti-patterns

Review 明确识别并拒绝：Plot Summary、Event List、Mechanical Episode Split、Exposition Dialogue、Passive Protagonist、Flat Escalation、Repeated Beats、Disconnected Subplots、Character Drift、Historical Drift、Unfilmable Interior Prose、Premature Scene Detail。

## 22. Script Revision / Persist Gate

局部 dialogue、单一 beat、有限 exposition、小范围顺序或连续性问题使用 local revise。主线、动机、人物弧转换、冲突升级、Episode Architecture、climax/payoff、ending fidelity、screenability 或 Work fidelity 失败时结构性 re-plan；广泛关联失败时整体重写。

只有达到 `screen-adaptable formal Script state` 且全部 Critical Check PASS 才允许 `script.create_script` 或 `script.save_script`。剧情概要、事件列表、几行分集说明、被动主线、缺人物弧/升级/高潮、机械分集、不可演 prose 或 Work drift 均不得持久化。

## 23. Work / Script / Episode 职责边界

| 层 | 本批明确职责 | 禁止侵入 |
|---|---|---|
| Work | Story Foundation、premise、protagonist、theme、conflict、stakes、人物/关系弧、史实边界、重大架构 | 详细 Episode、Scene 对白/动作、Shot/camera |
| Script | Screen Adaptation、主/支线、可见人物弧、信息揭示、Episode Architecture、节奏、可演策略 | 改写 Work Foundation、创建 Episode Entity、详细 Scene、Shot/camera |
| Episode | 后续负责单集详细 Dramatic Job 与内部设计 | 本批未修改 |
| Scene | 后续负责具体冲突、行动和对白 | 本批未修改 |
| Shot | 后续负责 camera、coverage 和视觉执行 | 本批未修改 |

## 24. SKILL.md / references 组织

本批遵循 `skill-creator` 的渐进披露原则：

```text
SKILL.md
= purpose + lifecycle + critical routing + persist/tool boundary

references/planning.md
= reusable professional planning method

references/review.md
= full domain rubric + anti-patterns + revision routing + gate
```

两个 `SKILL.md` 仍为 44 行；四个 reference 分别为 93、48、94、55 行，均由主文件直接链接，只有一层目录，没有 reference-to-reference 跳转和重复教材式内容。

`skill.yaml` 仍只保存 declarative completion metadata：Work 第一项强化为 formal story foundation，Script 两项强化为 Work inheritance、因果主线、信息揭示、Episode Architecture 与反 plot-summary；生命周期 Gate 仍是第三项。

## 25. 新增/修改测试

`tests/test_skills.py` 从 14 个测试增至 18 个，新增/强化：

1. references 只在 Work/Script 存在、各两份、文件短小且可发现；
2. planning reference 只从 Plan 阶段路由，review reference 只从 Review 阶段路由；
3. Work 专业方法以多组概念、因果链、候选比较、rubric 表格和 Persist Gate 组合验证；
4. Script 专业方法以继承、主/支线、人物弧、揭示、升级、分集、screenability、rubric 和边界组合验证；
5. references 与主 Skill 一同接受平台无关和禁止固定 Skill chaining 检查；
6. fixture 必须覆盖两种不同题材、足够评测维度、失败样例、Review-PASS Work 前提和人工执行清单；
7. 生产 Skill 不得包含 fixture 专用历史人物或事件。

测试不是只要求单个 `protagonist` 或 `climax` 字符串，而是验证结构、路由、成组方法、PASS/FAIL Gate 与跨层边界。

## 26. Creative Evaluation Fixtures

新增 `tests/fixtures/creative-quality/work-script-evaluations.yaml`：

- Case A：神龙政变，政治事件驱动，重点检查 event-to-story、主人公 agency、政治 opposition、stakes、因果 climax/ending、史实边界；
- Case B：唐太宗与魏征，君臣关系驱动，重点检查关系作为 story engine、人物目标差异、relationship arc、主题通过选择体现和可辩护虚构。

每个 Case 同时给出自然 Work prompt、基于真实 Review-PASS Work 的 Script prompt、期望评测维度和两个明确失败样例。Fixture 还要求保存 Skill 版本、证据 Context、prompt、artifact 和 tool trace，并对 rubric 逐项给出 artifact evidence。

这些是静态和人工 forward evaluation 材料，不包含“正确作品答案”，也不代表真实 LLM 已通过。

## 27. Forward Evaluation（如执行）

本批没有执行真实 Work/Script forward evaluation。

原因：当前自动化环境能加载仓库 Skill Contract，但没有一个与本次工作区修改隔离、可证明实际加载新版 Skill 并完整运行 Agent Loop 的 Creative Harness。直接由当前修改者模拟输出会污染评测独立性，也不能证明真实 Host 行为。

因此如实记录：

```text
STATIC_CREATIVE_SKILL_CONTRACT = PASS
REAL_WORK_FORWARD_EVAL = NOT_RUN
REAL_SCRIPT_FORWARD_EVAL = NOT_RUN
```

后续真实评测应使用 fixture 自然 prompt、实际证据 Context 和 Review-PASS Work artifact，保留完整输出与 Tool trace，再由 rubric 人工检查。

## 28. 自动化回归结果

| 检查 | 结果 |
|---|---|
| `pytest -ra tests/test_skills.py` | 18 passed |
| Drama Plugin full pytest | 69 passed |
| mypy | Success，34 source files |
| Skill quick validation | 8/8 PASS |
| Drama MCP Service pytest | 13 passed |
| Tool Registry count | 44，未变化 |
| Tool Contract SHA-256 | `824f09a38b954b36fe1f7ced616e5ce98d10b918171d838333caec97c6ac90ca`，与 Batch 1 相同 |
| `git diff --check` | PASS |

首次回归中曾误用不存在的 Plugin 内层 `.venv`、未通过 Python 调用无执行位的校验脚本，并误用 Plugin venv 启动 MCP tests；改用仓库实际运行时后全部通过。这些是命令入口问题，不是代码或合同失败，也没有安装新依赖。

## 29. Tool/MCP/Java 未修改证明

本批 `git diff --name-only -- src` 在 Plugin 源码范围为空；MCP 仓库状态为空；Tool catalog/schema/registry、ContextBuilder、Research 实现、Provider 和 Harness 均未修改。

Tool Registry 数量保持 44，按排序后的完整 `describe()` JSON 计算 SHA-256 仍为：

```text
824f09a38b954b36fe1f7ced616e5ce98d10b918171d838333caec97c6ac90ca
```

Java 仓库已有的 `server/src/main/resources/application.yml` 本地修改在本批开始前即存在，本批未触碰或回退。没有数据库、MySQL、MinIO、Media、Generation 或 ComfyUI 修改。

## 30. 已知不足

- 尚未由真实新版 Skill 驱动 LLM 完成盲式 forward evaluation；
- 静态测试可证明方法和 Gate 存在，不能证明不同模型都会稳定执行；
- Work/Script 的开放 `content` 尚未通过一条完整真实创作链验证其实际组织效果；
- Episode、Scene、Shot 仍只有 Batch 1 生命周期深度，需 Batch 3 专业化；
- 本批没有完整对白教材、固定商业结构模板或平台算法，这是有意控制范围；
- Work/Script 仍不能标记为 PRODUCTION-READY。

## 31. Batch 3 前置条件

Batch 3 已具备以下前提：

- Work 能提供明确 Story Foundation 与历史边界；
- Script 能提供主线、可见人物弧、信息揭示、Episode Architecture 与 screenability 约束；
- 生命周期、Review Again 和 Persist Gate 有自动化保护；
- Tool/MCP/Java/Context/Research 合同稳定；
- 质量 fixture 已示范如何区分静态合同和真实创作评测。

Batch 3 应仅深化 Episode、Scene、Shot 的领域方法，不回头新增 Workflow Engine，也不顺手修改 Production/Generation。真实 Work/Script forward evaluation 可在具备隔离 Harness 时执行，并在 Batch 4 汇入完整 Creative E2E。

## 32. 最终验收结论

### Work 验收

```text
WORK_PROFESSIONAL_PLANNING = PASS
WORK_EVENT_TO_STORY_METHOD = PASS
WORK_PROTAGONIST_DESIGN = PASS
WORK_GOAL_NEED_OPPOSITION_STAKES = PASS
WORK_CHARACTER_ARC = PASS
WORK_RELATIONSHIP_ARC = PASS
WORK_PREMISE_LOGLINE = PASS
WORK_THEME_DRAMATIC_QUESTION = PASS
WORK_HISTORICAL_BOUNDARY = PASS
WORK_STORY_ARCHITECTURE = PASS
WORK_ANTI_SUMMARY_GATE = PASS
WORK_DOMAIN_REVIEW = PASS
WORK_REVISION_POLICY = PASS
WORK_PERSIST_GATE = PASS
```

### Script 验收

```text
SCRIPT_PROFESSIONAL_PLANNING = PASS
SCRIPT_WORK_INHERITANCE = PASS
SCRIPT_MAIN_LINE = PASS
SCRIPT_SECONDARY_LINES = PASS
SCRIPT_CHARACTER_ARC_TRANSLATION = PASS
SCRIPT_CONFLICT_ESCALATION = PASS
SCRIPT_INFORMATION_REVEAL = PASS
SCRIPT_EPISODE_ARCHITECTURE = PASS
SCRIPT_SHORT_DRAMA_PACING = PASS
SCRIPT_SCREENABILITY = PASS
SCRIPT_DIALOGUE_BASELINE = PASS
SCRIPT_ANTI_SUMMARY_GATE = PASS
SCRIPT_DOMAIN_REVIEW = PASS
SCRIPT_REVISION_POLICY = PASS
SCRIPT_PERSIST_GATE = PASS
```

### 架构验收

```text
CREATIVE_LIFECYCLE_UNCHANGED_OR_COMPATIBLE = PASS

TOOL_CONTRACT_MODIFIED = NO
MCP_SERVICE_MODIFIED = NO
JAVA_SERVICE_MODIFIED = NO
DATABASE_MODIFIED = NO

WORK_SCRIPT_SKILL_PLATFORM_NEUTRAL = PASS
PLAN_REVIEW_NOT_PERSISTED = PASS
NO_REVIEW_PASS_NO_PERSIST = PASS

GENERIC_WORKFLOW_ENGINE_ADDED = NO
GENERIC_REVIEW_SKILL_ADDED = NO
```

### Batch 2 最终状态

```text
WORK_PROFESSIONAL_METHOD = PASS
SCRIPT_PROFESSIONAL_METHOD = PASS

WORK_PLAN_DEPTH = PASS
WORK_REVIEW_DEPTH = PASS
WORK_ANTI_SUMMARY_GATE = PASS

SCRIPT_PLAN_DEPTH = PASS
SCRIPT_REVIEW_DEPTH = PASS
SCRIPT_ANTI_SUMMARY_GATE = PASS
SCRIPT_SCREENABILITY_GATE = PASS

WORK_SCRIPT_BOUNDARY = PASS
SCRIPT_EPISODE_BOUNDARY = PASS

CREATIVE_LIFECYCLE_REGRESSION = PASS

TOOL_CONTRACT_MODIFIED = NO
MCP_SERVICE_MODIFIED = NO
JAVA_SERVICE_MODIFIED = NO

REAL_WORK_FORWARD_EVAL = NOT_RUN
REAL_SCRIPT_FORWARD_EVAL = NOT_RUN

WORK_SKILL_MATURITY = EARLY
SCRIPT_SKILL_MATURITY = EARLY

BATCH_2_RESULT = PASS
READY_FOR_BATCH_3 = YES
```

成熟度仍记为 EARLY，不是因为方法仍缺失，而是因为：

```text
PROFESSIONAL_METHOD_ESTABLISHED
REAL_CREATIVE_E2E_PENDING
```

最终结论：**Batch 2 已把 Work/Script 从“知道应有 conflict、arc、climax”推进到“知道如何从历史证据规划这些要素、如何形成可供下游继承的完整成果、如何按领域标准拒绝摘要与不可演结果，并且只有 Review PASS 才值得持久化”。基础设施保持稳定，下一步可以进入 Episode/Scene/Shot 专业能力加固。**
