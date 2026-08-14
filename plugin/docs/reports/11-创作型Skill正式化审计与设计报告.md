# 11-创作型 Skill 正式化审计与设计报告

执行日期：2026-08-14（Asia/Shanghai）  
审计仓库：`drama-plugin`  
审计性质：只读专项审计与目标设计；除本报告外不修改 Skill、代码、Tool Contract、MCP Service、Java Service、数据库、Media 或 Generation。

## 1. 执行摘要

### 1.1 核心结论

当前 Drama Plugin 的创作型 Skill **不是纯粹的 Tool Wrapper**，但也尚未达到 Professional Creative Skill。更准确的定位是：

> **具备少量领域创作提示的、较成熟的 Tool/持久化使用手册。**

现有 Skill 已经正确解决了平台中立、Tool 选择、长期记忆边界、create/save 语义、上下游职责隔离等架构问题，也已写入一些重要的领域要素：

- Work：theme、viewpoint、relationships、central conflict、timeline、structure；
- Script：main/secondary lines、character arcs、pacing、escalation、climax；
- Episode：goal、opening hook、conflict progression、information gain、character change、ending hook；
- Scene：entry state、objective、conflict、action、turn、exit state；
- Shot：framing、camera、composition、blocking、action、movement、duration、continuity。

这些不是零基础，必须保留。但五个核心 Skill 都没有显式、可执行的：

```text
Context sufficiency check
→ Plan
→ Draft/Execute
→ Domain Review
→ Revise or Re-plan
→ Review again
→ Persist Gate
```

`skill.yaml` 每个 Skill 只有两条 completion conditions；`SKILL.md` 仅 12–14 行，主要篇幅用于 get/list/search/create/save、Stable Envelope、Domain Content 与 Context Tool 语义。仓库中不存在面向创作质量的 Plan、Review、Revise、Fail Gate 指令，也没有真实创作质量回归测试。

### 1.2 正式判断

- 当前 Work / Script / Episode / Scene / Shot 均为 **EARLY**，不是 PRODUCTION-READY。
- 最大问题不是 Tool 不够，而是 **专业创作方法论、质量标准和持久化前质量闭环不足**。
- 当前开放 `content` Contract 足以保存正式创作成果；Java 也能持久化这些 JSON 事实。当前没有证据要求修改 Tool 或 Java Contract。
- 应当在每个对应 Skill 内定义该领域独有的 planning、execution、review、revision 和 persist gate；不应建立通用 Review Engine、Workflow Runtime 或 Java Plan/Review 实体。
- 在 ComfyUI MCP 对接之前，**建议先完成 Creative Skill 加固**。否则只会把不稳定的文字创作结果更高成本地物化为图片和视频。

## 2. 审计范围

### 2.1 已完整检查的 Skill Core

当前共 8 个 Skill，均检查了 `SKILL.md`、`skill.yaml` 与 `agents/openai.yaml`：

```text
skills/historical-research
skills/work-creation
skills/script-adaptation
skills/episode-development
skills/scene-development
skills/shot-design
skills/asset-resolution
skills/shot-production
```

当前所有 Skill 目录都没有 `references/`。

### 2.2 已检查的实现与契约

- Skill 加载与校验：`src/drama_plugin/skills/registry.py`、`validation.py`；
- Skill manifest model：`src/drama_plugin/contracts/manifest.py`；
- Tool catalog 与 schema：`src/drama_plugin/tools/catalog.py`、`registry.py`、`schemas.py`；
- Work→Shot Contract：`src/drama_plugin/contracts/creation.py`；
- Context：`contracts/context.py`、`context/local.py`、`context/builder.py`；
- Research Contract：`contracts/research.py`；
- Provider Protocol、Mock 与 HTTP binding；
- Plugin composition root 与 manifest；
- MCP 动态投影：`drama-mcp-service/src/drama_mcp_service/adapter.py`；
- Java Work / Script / Episode / Scene / Shot DTO 与 ToolApi 实现；
- 当前 Plugin、Skill、Tool、Context、Memory Contract 和 MCP 测试。

### 2.3 已检查的文档

- `README.md`、`docs/architecture.md`；
- Batch 05 Agent 驱动业务模型重构报告；
- Batch 06 长期记忆 Tool 接口补齐报告；
- Batch 07 通用 Skill 加固报告；
- Batch 08 Skill 持久化语义加固报告；
- Batch 09 长期记忆 Contract / MySQL 冻结报告；
- 早期协议、MCP PoC 与架构审计中和 Skill/Agent/Tool 边界相关的章节。

### 2.4 审计边界

本审计不以“测试是否通过”替代创作能力评估，也没有运行会创建 Work、Script、Episode、Scene、Shot、Asset 或 Media 的真实 E2E。现有工作区中的其他改动不属于本审计，未被修改或回退。

## 3. 当前 Skill 总体架构

当前架构方向正确：

```text
Harness / Agent Host
  ├─ Agent Loop
  ├─ Skill selection
  ├─ Tool dispatch
  └─ Run Context lifecycle
          ↓
Platform-neutral Skill Core
  ├─ SKILL.md
  └─ skill.yaml
          ↓
Stable Logical Tools
          ↓
MCP / HTTP Adapter
          ↓
Java / MySQL or other Providers
```

证据：

- `plugin.py` 明确是 composition root，注释声明 Host 是 decision-maker 和 Agent Loop owner；
- `SkillRegistry` 只加载 `skill.yaml` 与 `SKILL.md`，不执行步骤；
- `SkillToolReferenceValidator` 只验证 Tool code 存在和 domain 一致；
- MCP `PluginToolAdapter` 动态投影 Plugin Tool Registry，不包含 Work/Scene/Shot 专用编排；
- `agents/openai.yaml` 只有 display metadata 和 default prompt，没有核心方法论；
- 测试禁止 Skill Core 依赖 Codex、MCP、Java、ComfyUI 或其他具体运行时。

这些边界应继续保持，不应因增加 Plan/Review 就重新引入 Workflow Engine。

## 4. 当前 Skill 的真实定位

### 4.1 Tool Wrapper、Workflow 还是 Professional Skill？

| 维度 | 当前状态 | 判断 |
|---|---|---|
| Tool 选择 | get/list/search/create/save 语义清晰 | STRONG |
| 持久化语义 | create 首次写入、save 仅修订、full replacement | STRONG |
| 平台中立 | Core 与 Host/MCP/Java/ComfyUI 解耦 | STRONG |
| Context 声明 | required/optional 已声明，Context Tool 条件调用 | PARTIAL |
| 专业 Planning | 只有结果要素列表，没有规划方法 | PARTIAL |
| Draft Execution | 有方向性要求，没有完整创作步骤和产物深度 | PARTIAL |
| Domain Review | 只有两条 completion conditions，没有自审过程与缺陷分类 | PARTIAL / WEAK |
| Revision loop | save 语义存在，但没有 Review FAIL→Revise→Review | MISSING |
| Persist Gate | 要求“complete initial formal state”，但没有可验证的质量通过条件 | PARTIAL |
| 质量评测 | 当前测试只验证合同/字符串/平台边界 | MISSING |

因此，当前 Skill 的中心重力仍是 Tool 使用与持久化正确性，而不是可重复的专业创作方法。

### 4.2 具体证据

五个核心 `SKILL.md` 均没有显式出现 Plan、Review、Draft、Quality Gate 或 Review FAIL 处理。文件中的 revise/revision 主要指 `save_xxx` 对既有实体的持久化修订，不是 Agent Run 内部的草稿修订循环。

`tests/test_skills.py` 当前主要验证：

- 8 个 Skill 能加载；
- Core 平台中立且不互相调用；
- 所有 Tool code 在说明中出现；
- create/save 字符串语义正确；
- Adapter 只含界面 metadata。

它没有验证 Agent 是否先 Plan、是否拒绝低质量 Draft、是否按领域 rubric Review、是否 Revision 后再 Persist。

`tests/test_memory_contracts.py` 和 `integration/run_drama_service_e2e.py` 为验证 Contract，合法地使用极简 `content`，例如只有 `theme`、`format`、`arc`、`character` 或 `framing`。这证明 Tool 链可运行，但也证明持久层不会替 Agent 判断“内容是否足以成为作品”。

## 5. 当前创作链审计

```text
Historical Research Context
→ Work
→ Script
→ Episode
→ Scene
→ Shot
→ Asset / Media / Production
```

父子关系、Tool 和 Context 链已经存在；缺口主要是每一级的“转换方法”和“质量守门”：

| 转换 | 当前已有 | 当前缺失 |
|---|---|---|
| Research→Work | 研究与创作分离、事实/推断/虚构区分 | 从史料中提炼命题、人物欲望、对抗、代价和完整故事设计的方法 |
| Work→Script | 主线、支线、人物弧、节奏、高潮 | 如何把文学设计转为可演结构、分集策略、信息揭示与全剧节拍 |
| Script→Episode | Hook、推进、信息增量、人物变化 | 单集必要性、状态变化、内部转折、集间节奏和失败判据 |
| Episode→Scene | 目标、冲突、行动、转折、出入状态 | 场景策略、障碍/战术、潜台词、节拍、场景删除测试和可演文本标准 |
| Scene→Shot | 景别、构图、站位、运动、连续性 | 叙事覆盖策略、轴线/视线/方向、镜头节奏、资产一致性和生成可执行性评审 |

上游质量不足会逐级固化。Production Tool 再强，也不能补回 Work 命题、人物弧、Scene 冲突或 Shot 叙事目的。

## 6. Work Skill 审计

审计对象：`skills/work-creation/SKILL.md` 与 `skill.yaml`。

### 6.1 已有能力

- 明确 Work 不是历史资料记录，应形成 coherent literary work；
- 已要求 theme、viewpoint、relationships、central conflict、timeline、overall structure；
- 已区分事实、疑点和虚构；
- 已正确区分 ID→get、自然语言→search、结构枚举→list、新建→create、既有修订→save；
- `skill.yaml` 要求 `researchContext` 与 `creativeIntent`，方向正确；
- completion conditions 要求文学一致性及历史/虚构边界明确。

### 6.2 关键缺口

当前内容仍可能退化成：

```text
作品名：神龙政变
描述：张柬之发动政变，武则天退位，李显复位。
```

原因不是 Tool Contract 太窄，而是 Skill 没有要求在 create 前完成以下认知闭环：

- premise 与 logline；
- 主人公、外在目标、内在需求、核心误区；
- 对抗力量及其合理目标；
- 失败代价和不可逆后果；
- 主题问题及结局如何回答主题；
- 主要人物关系与关系变化；
- 核心史实、不可改变事实、争议事实和可虚构空间；
- 起点、触发事件、主要转折、中段变化、危机、高潮、结局；
- 主角和关键人物弧线；
- 类型、叙事基调、目标受众、短剧体量和结构约束。

当前只有“建立 theme/conflict/timeline/structure”的一句指令，没有告诉 Agent 如何比较候选方案、如何选择主人公、如何把历史事件变成角色驱动故事，也没有 Work Review rubric。

### 6.3 判断

Work Skill 已超越 TEST wrapper，但只能保证“字段方向大致正确”，不能稳定阻止事件摘要被当作作品。成熟度：**EARLY**。

## 7. Script Skill 审计

审计对象：`skills/script-adaptation/SKILL.md` 与 `skill.yaml`。

### 7.1 已有能力

- 明确 preserve the Work's dramatic truth；
- 要求主线、必要支线、人物弧、节奏、升级、高潮和短剧结构；
- 强调 observable action 优于 explanatory prose；
- 正确使用 Work/Script get、父级 list、create/save；
- 不自动创建 Episode，职责边界正确。

### 7.2 关键缺口

- 没有 Script planning procedure：全剧驱动问题、结构段落、关键 beats、集数/时长、Episode 分配、信息揭示顺序、中段转折、高潮与收束；
- 没有明确继承 Work 的哪些不可丢失事实、人物弧和历史边界；
- “screenable” 只有结论，没有定义可演剧本最低形态；
- 没有防止剧情梗概冒充 Script；
- 没有检查人物动机连续、冲突是否持续升级、场景是否重复、是否存在信息性对白、历史事实是否漂移；
- 没有 Review FAIL 后局部修订还是整体 re-plan 的判断。

### 7.3 判断

当前 Script Skill 能提示模型写“影视化结构”，但无法稳定产出可演、可分集、可继续拆 Scene 的正式剧本。成熟度：**EARLY**。

## 8. Episode Skill 审计

审计对象：`skills/episode-development/SKILL.md` 与 `skill.yaml`。

### 8.1 已有能力

Episode 是当前五个 Skill 中领域要素表达较完整者之一：

- “one clear dramatic job”；
- opening hook；
- conflict progression；
- information gain；
- character change；
- ending hook；
- neighboring Episode continuity；
- 不自动拆 Scene。

这已明确 Episode 不是简单数据库切片。

### 8.2 关键缺口

- 没有要求回答“为什么这一集必须存在”；
- 没有显式 beginning story state、turning point、ending story state；
- 没有定义中心冲突如何经历升级而不是重复；
- 没有关系变化、危险变化、目标推进的独立检查；
- ending hook 未区分悬念、逆转、决定、危机或阶段性 resolution；
- 对邻集只写“when continuity requires it”，没有说明何时必须查看前后集；
- 没有短剧单集节奏、时长和信息密度评审；
- 没有 Review/Revise/Persist Gate。

### 8.3 判断

当前 Episode Skill 具备较好的骨架清单，但仍不足以形成稳定的单集戏剧设计。成熟度：**EARLY**。

## 9. Scene Skill 审计

审计对象：`skills/scene-development/SKILL.md` 与 `skill.yaml`。

### 9.1 已有能力

- 明确 Scene 必须有 concrete dramatic purpose；
- 已要求 place、time、characters、entry state、objective、conflict、dialogue、action、turn、exit state；
- `skill.yaml` 描述为 state-changing Scene；
- 能 list/search existing Scenes，具备避免重复和检查结构范围的工具基础；
- 不自动生成 Shot 或解析 Asset，边界正确。

### 9.2 关键缺口

- 没有 Character Objective 与对手 Objective 的对撞设计；
- 没有 obstacle、stakes、tactics、beats、subtext、reversal 等可演方法；
- 没有区分“谈论冲突”和“在场景中发生冲突”；
- 没有对白检查：人物声音、潜台词、信息灌输、重复说明；
- 没有 Scene necessity test。

应明确识别以下失败：

```text
Scene before = A
Scene after  = A

且没有新信息、关系变化、决策变化、危险变化或目标推进
→ Scene 无存在价值，Review FAIL
```

### 9.3 判断

当前 Scene Skill 已知道 Scene 应包含哪些元素，但没有教 Agent 如何制造和验证戏剧变化。成熟度：**EARLY**。

## 10. Shot Skill 审计

审计对象：`skills/shot-design/SKILL.md` 与 `skill.yaml`。

### 10.1 已有能力

- “用最少必要镜头覆盖 Scene dramatic turn”是正确且重要的原则；
- 已覆盖 framing、camera position、composition、blocking、action、expression、movement、dialogue coverage、duration、entry/exit state；
- 已要求 spatial、performance、prop、wardrobe、temporal continuity；
- completion 明确每个保留 Shot 必须有 dramatic function，并避免 redundant Shots；
- 允许读取 Asset/Media 作为连续性参考，但不自动生产媒体。

### 10.2 关键缺口

- 未明确每个 Shot 的 Narrative Purpose 与信息/情绪变化；
- 未系统区分 subject、action、blocking、shot size、angle、movement、composition；
- 未覆盖 screen direction、eyeline、180-degree axis、character position、action match；
- 未定义景别组合、镜头长短和切换节奏如何服务 Scene turn；
- 未要求检查 Scene/Character/Costume/Prop Asset 的稳定引用是否齐备；
- 未定义 Generation Feasibility：单镜头动作复杂度、角色数量、空间可控性、首尾帧条件、可被 Image/Video Provider 执行的描述；
- 未防止“一句话一个 Shot”或机械平均景别；
- 没有整组 coverage review 和跨 Shot continuity review。

### 10.3 判断

当前 Shot Skill 的术语覆盖在五者中最强，但仍是镜头要素列表，不是完整的影视语言规划与生产可执行性方法。成熟度：**EARLY**。

## 11. Context Gathering 审计

### 11.1 当前声明

| Skill | required | optional |
|---|---|---|
| work-creation | researchContext, creativeIntent | workId, temporaryState |
| script-adaptation | work | scriptId, researchContext, temporaryState |
| episode-development | script | episodeId, neighboringEpisodes, researchContext, temporaryState |
| scene-development | episode | sceneId, neighboringScenes, researchContext, temporaryState |
| shot-design | scene | shotId, neighboringShots, selectedAssetIds, researchContext, temporaryState |

这些声明符合最小 Context 原则。`LocalContextProvider` 对既有 Script/Episode/Scene/Shot 能加载 Work→当前对象的父链；邻居、Asset 与 Media 不会被无差别加载，也符合精简原则。

### 11.2 缺口

`SKILL.md` 没有把 manifest 中的 required/optional 变成“开始创作前的充分性检查”。目前普遍只说：如果 Context 未提供，可以 `context.build_context`。但没有回答：

- 哪些上下文缺失时必须停止创作；
- 哪些可以由 Agent 合理推断；
- 哪些必须通过 get/list/search 补齐；
- 什么时候需要邻接对象；
- 新对象尚无 ID 时不能以该对象 scope build context，应如何从父级构建；
- 什么时候应把临时 Plan/Review 保留在 Agent Run Context，而不是写入 Java。

### 11.3 建议的最小 Context 策略

| Skill | Plan 前最低上下文 |
|---|---|
| Work | 用户创作意图、体量/受众约束、已有 Work 候选、足够的历史证据与虚构边界 |
| Script | 完整 Work、研究边界、已有 Script 候选、目标集数/单集时长/媒介约束 |
| Episode | Work/Script 中与本集有关的主线和人物状态、集号、相邻 Episode 状态 |
| Scene | Episode 任务、前后 Scene 状态、人物当下目标/关系/已知信息、地点时间约束 |
| Shot | Scene turn、前后 Shot、人物/空间/道具/服装连续性、选定 Asset、生产限制 |

Context 不必一次加载全剧；应按缺口使用已有 get/list/search/context 工具。

## 12. Research / Historical Evidence 审计

### 12.1 已有正确设计

`historical-research` 是当前较清晰的 Skill：

- 先形成 focused question；
- 保留 source identity；
- 区分 documented fact、supported inference、dispute、dramatic invention；
- 优先使用已有证据；
- 只在存在缺口时 search；
- consequential claim 才 verify；
- 研究结果默认留在 Agent Run Context，不建立 Java Research CRUD Domain。

Work、Script、Episode、Scene 也都采用条件性 Research；Shot 不声明 Research Tool。这个方向符合“既不每步都研究，也不完全不研究”。

### 12.2 当前缺口

- Work 要求 researchContext，但当 evidence 不足时没有明确“停止 Draft，形成 research question，交还 Harness/Agent 选择 historical-research”的规则；
- Script/Episode/Scene 只写 uncertain claim 时 verify，没有定义哪些变化属于 consequential historical drift；
- 没有说明 Research Context 的事实如何转化为“不可改事实 / 争议区 / 合理虚构区”；
- 没有在各领域 Review 中检查历史漂移。

### 12.3 建议的介入点

```text
Is a consequential creative decision evidence-dependent?
  ├─ NO  → use supplied context; do not search again
  └─ YES
       ├─ adequate evidence exists → use it and preserve uncertainty label
       └─ evidence missing/contradictory → formulate focused question;
          Harness/Agent selects research capability before planning continues
```

- Work：研究频率最高，应先建立 evidence boundary；
- Script：只有结构改编触碰关键史实或人物动机证据时补充；
- Episode：关键事件顺序、人物在场、决定性因果不确定时核验；
- Scene：既有 Context 足够时不重复研究；地点/礼仪/关键行为影响可信度时才查；
- Shot：通常不重新做史料研究，只消费已批准的 Scene 与视觉参考。

这不要求 Skill 调用另一个 Skill；Skill 可以返回“证据不足及研究问题”，由 Harness/Agent Loop 选择下一 Skill。

## 13. Plan 能力缺口

当前五个 Skill 都有“应包含什么”的名词清单，但没有“如何形成它”的 planning method。Plan 应是 Agent Run 内部产物，不是 Java 实体。

统一 Plan 最低要求：

1. 明确当前实体的唯一任务；
2. 列出必须继承的上游事实与不可违反约束；
3. 明确开始状态与目标结束状态；
4. 设计至少一个核心冲突/变化机制；
5. 比较候选方案并说明取舍；
6. 定义完成后下游所需的信息；
7. 在 Draft 前发现事实或 Context 缺口。

不同 Skill 仍需自己的 Plan rubric，不能只写一个通用“Create X”。

当前判断：`PLAN_CAPABILITY = PARTIAL`。

## 14. Execute 能力缺口

现有 Skill 已给出部分领域方向，因此 Execute 不是完全缺失。但缺少：

- 由 Plan 到完整领域结果的映射；
- 上游事实的继承清单；
- 允许创造与禁止改变的边界；
- 产物应达到的深度、粒度和可供下游消费的最低形态；
- 防止摘要、字段堆砌、机械切片和模板化输出的反例规则。

建议 Execute 明确：先在 Run 内完成 Draft，不调用 create/save；Draft 是完整候选正式状态，而不是几行摘要或空壳。只有 Review 通过后才组装 Stable Envelope + Domain Content。

当前判断：`EXECUTE_CAPABILITY = PARTIAL`。

## 15. Review 能力缺口

不建议新增 generic-review-skill。各领域 Review 的核心问题不同，应保留在对应 Skill，只有生命周期措辞保持一致。

### 15.1 Work Review

- 是否是角色驱动的作品设计，而非历史事件摘要；
- premise/logline 是否清楚；
- 主人公目标、需求、对抗、代价是否成立；
- 主题是否通过冲突和结局表达；
- 起点、转折、高潮、结局是否构成因果链；
- 人物关系和弧线是否改变；
- 史实、争议和虚构边界是否清楚；
- 类型、基调、受众和短剧体量是否一致。

### 15.2 Script Review

- 是否忠于 Work 的 premise、theme、人物弧和历史边界；
- 主线是否贯穿，支线是否服务主线；
- 动机是否连续，冲突是否升级；
- 信息揭示顺序是否制造期待；
- 是否有重复剧情、无意义段落或大量说明性对白；
- Episode 划分和高潮位置是否符合短剧节奏；
- 是否可演，而非扩写梗概；
- 结局是否兑现 Work。

### 15.3 Episode Review

- 本集唯一 dramatic job 是否明确；
- 开场 hook 是否立即建立问题/危险/欲望；
- 中部是否产生升级与 turn，而非重复；
- 是否有新的信息、决定、关系或危险变化；
- exit state 是否与 entry state 不同；
- ending hook/resolution 是否真实来自本集进展；
- 与前后集是否连续；
- 删除本集是否会损害全剧。如果不会，应 FAIL。

### 15.4 Scene Review

- Scene purpose、主角 objective、对手/obstacle 和 stakes 是否具体；
- 冲突是否通过行动和策略发生；
- turn 是否改变信息、关系、决定、危险或目标；
- exit state 是否不同于 entry state；
- 对白是否有角色声音、潜台词，是否避免信息灌输；
- 动作是否可演且服务 Episode；
- 删除 Scene 是否不影响剧情。若不影响，应 FAIL。

### 15.5 Shot Review

- 每个 Shot 是否有叙事功能；
- 镜头组是否完整覆盖 Scene turn；
- 景别、角度、运动和时长是否形成节奏；
- 轴线、视线、屏幕方向、人物位置和动作是否连续；
- Asset/Costume/Prop 是否一致；
- 是否存在机械切分或冗余 coverage；
- 是否可被 Image/Video Provider 执行；
- 首尾状态是否足以衔接前后镜头。

当前两条 completion conditions 是 Review 的雏形，但不足以构成可执行自审。当前判断：`REVIEW_CAPABILITY = PARTIAL`。

## 16. Revise 能力缺口

当前 Skill 对 revise 的描述主要是：已有稳定实体发生具体修订时使用 `save_xxx`。这解决了持久化语义，却没有解决 Draft 内部修订。

建议使用三档判断，不建立状态机：

| 缺陷类型 | 动作 |
|---|---|
| 措辞、局部节奏、单个事实标签、镜头参数等局部问题 | Local revise |
| Scene 冲突、Episode dramatic job、Shot coverage strategy 不成立 | Re-plan 当前实体 |
| Work premise、Script 主线/人物弧等根本结构不成立 | Re-plan 或整体重写当前层，并标记受影响下游需重新审查 |

统一规则：

```text
Review PASS → Persist
Review FAIL → Revise or Re-plan → Review again
```

应设置合理停止条件：无法补齐关键 Context、历史证据冲突未解决或用户约束互斥时，报告缺口，不得为了“完成”而持久化低质量 Draft。

当前判断：`REVISE_CAPABILITY = MISSING`。

## 17. Persist Gate 审计

### 17.1 已有 Gate

五个核心 Skill 都写明：只有形成 “complete initial formal state” 后才 create；create 是首次正式写入；save 不是 create 后的例行动作。这是重要且正确的持久化基础。

### 17.2 为什么仍然不足

“complete” 没有和领域 Review PASS 绑定。Agent 可以把一个只有 `theme` 的 Work 或只有 `hook` 的 Episode 主观视为 complete，并立即 create。Tool、MCP 和 Java 都不会阻止：

- Tool catalog 只要求 `content` 是 object；
- Pydantic Contract 使用开放 `dict[str, Any]`；
- Java `requireObject()` 只检查 JsonNode 是 object；
- MCP Adapter 只验证 JSON Schema，不做创作质量判断。

这不是 Tool/Java 的 bug，而是 Skill Gate 尚未正式化。

### 17.3 目标 Gate

只有同时满足以下条件才可 create/save：

1. Required Context 已齐备或缺口已明确处理；
2. Domain Plan 已完成；
3. Draft 是完整候选正式状态；
4. 对应领域 Review 所有 critical checks 通过；
5. 历史边界和上游连续性无未解决冲突；
6. 当前提交是新实体的首次正式状态，或既有实体的明确完整修订；
7. Draft reasoning、Plan、Review notes 不进入长期 `content`。

当前判断：`PERSIST_GATE = PARTIAL`。

## 18. Skill / Harness / Tool / Java 职责边界

| 层 | 应负责 | 不应负责 |
|---|---|---|
| Harness / Agent Host | Agent Loop、Skill selection、Tool dispatch、Run Context 生命周期、继续/停止、把 Skill 结果交给下一轮判断 | 历史短剧领域 rubric、替 Skill 决定 Scene 是否有戏剧价值 |
| Skill | Context 充分性、Research 决策、专业 Plan、Draft 方法、领域 Review、Revision 原则、Persist Gate、Tool 使用策略 | 实现 Agent Runtime、固定跨 Skill workflow、数据库或 Provider 细节 |
| Tool / MCP | 提供稳定 get/list/search/create/save/research/media/generation 能力，校验机器 schema，返回结果 | 创作、质量评分、决定是否值得保存、自动串联 Skill |
| Java / MySQL | 长期保存正式 Work/Script/Episode/Scene/Shot/Asset/Media，维护身份、父级和持久化约束 | 保存每轮 Plan/Review scratchpad、编排 Agent Loop、替代文学/影视评审 |

Plan、Draft、Review、Revision 默认留在 Agent Run 内部；必要时可利用已有 `temporaryState`，但不要求新增 Tool 或 Java 表。

## 19. 当前 Tool Contract 是否足够

### 19.1 分领域判断

| Domain | 当前获取/写入能力 | 是否足够支撑 Skill 加固 | 结论 |
|---|---|---|---|
| Work | get/list/search/create/save | 能发现重复、读取、创建与完整修订；开放 content 可保存丰富设计 | 足够 |
| Script | Work get；Script get/list/create/save | 已知 Work 下结构发现足够，当前不需要 search_scripts | 足够 |
| Episode | Script get；Episode get/list/filter/create/save | 可读取父级和邻集 | 足够 |
| Scene | Episode get；Scene get/list/search/create/save | 可读取邻 Scene、查重和修订 | 足够 |
| Shot | Scene get；Shot get/list/search/create/save；Asset/Media get | 可设计 coverage、查重和读取稳定参考 | 足够 |
| Research | search sources/events/people/locations、verify claim | 能在 Run 内建立证据边界 | 足够 |
| Context | build/refresh，父链最小投影 | 足够支持现有对象；新对象从父级 scope 开始即可 | 足够 |

### 19.2 不建议新增的 Tool

当前不应新增：

```text
work_plan
script_plan
episode_review
scene_review
shot_revision
creative_workflow
review_status
```

这些首先是 Agent Run 内的方法与判断，不是长期业务能力。

### 19.3 何时才考虑极小 Tool 调整

只有真实 Creative E2E 证明 Agent 无法通过现有 get/list/search/context 获得必要信息时，才进入 B 类。例如未来数据量很大导致邻接 Scene/Shot 获取成本不可接受，可讨论极小的结构过滤或 Context option；目前没有这种证据。

结论：`TOOL_CONTRACT_CHANGE_REQUIRED = NO`。

## 20. A / B / C 修改分类

### A 类：只需要修改 Skill（当前主要工作）

- 五个核心 Skill 的统一生命周期；
- 各自专业 planning method；
- Required Context 充分性检查；
- Research 介入与停止条件；
- Draft 完整度与反摘要规则；
- 领域 Review rubric；
- Review FAIL→Revise/Re-plan→Review；
- Persist Gate；
- `SKILL.md` 与 references 的渐进披露组织；
- 面向真实历史短剧任务的 Skill quality regression/evaluation fixtures。

### B 类：Skill + Tool Contract 极小调整

当前：**无已证实必需项**。

保留条件性观察项：真实长篇数据 E2E 若证明邻接对象或最小 Context 无法有效获取，再基于证据讨论，不提前增加接口。

### C 类：必须修改 Java Domain Contract

当前：**无**。

Work→Shot 的正式创作事实可进入现有 `content` JSON Object。只有未来出现明确的跨系统查询、强类型校验、报表或独立版本治理需求，且开放 content 确实无法满足时，才考虑稳定字段；不能因为 Agent 内部需要 Plan/Review 就增加 Java Domain。

## 21. SKILL.md / references 组织建议

### 21.1 当前问题

当前 `SKILL.md` 极短，优点是精简，缺点是核心方法论不够。未来也不应把全部编剧理论塞进单一 `SKILL.md`。

### 21.2 建议边界

```text
SKILL.md
= Purpose
+ Required Context / missing-context behavior
+ lifecycle
+ critical rules
+ domain persist gate
+ Tool strategy
+ references routing

references/
= deeper planning method
+ domain review rubric
+ examples / anti-patterns
+ historical or continuity guidance
```

遵循渐进披露：主文件保持可扫描，复杂领域知识按需要读取；同一规则不在主文件和 reference 重复。

### 21.3 不建议 generic-review-skill

Review 的生命周期表述可统一，但 Work/Script/Episode/Scene/Shot 的判断内容差异很大。拆出 generic-review-skill 会迫使 Agent在 Skill 间跳转，也会稀释领域标准。优先把 Review 保留在每个 Skill 内或其直接 references 中。

## 22. Creative Skill Lifecycle 目标设计

建议五个创作 Skill 统一采用以下轻量生命周期：

```text
1. UNDERSTAND GOAL
   Clarify the requested object, scope, audience, constraints, and whether it is new or existing.

2. GATHER CONTEXT
   Use supplied context first; get known IDs; list known scopes; search only when identity is unknown;
   determine whether historical evidence is needed.

3. PLAN
   Build a domain-specific internal plan and define the intended state change.

4. EXECUTE DRAFT
   Produce a complete candidate formal state without persisting it.

5. REVIEW
   Apply the domain rubric and historical/continuity checks.

6. REVISE OR RE-PLAN
   Fix local defects or re-plan structural failures; review again.

7. PERSIST
   Only after Review PASS: create a genuinely new object or save a complete revision of an existing ID.
```

这是一套 Skill 指令，不是运行时状态机。Harness 继续使用现有 Agent Loop；不需要 `PlanManager`、`ReviewEngine`、`CreativeWorkflowRuntime` 或 `WorkflowCoordinator`。

## 23. 各核心 Skill 最小设计骨架

以下是未来加固的设计骨架，不是完整 `SKILL.md`，本批不创建文件。

### 23.1 Work Skill

**Purpose**  
把创作意图和历史证据转化为角色驱动、可改编的历史短剧作品设计，而非事件摘要。

**Required Context**  
创作意图、受众/类型/体量约束、Research Context、已有 Work 候选；证据不足时形成 focused research question 并停止持久化。

**Plan**  
确定 premise/logline、主人公目标/需求、对抗、代价、主题、关系、史实边界、故事起点/转折/高潮/结局和人物弧。

**Execute**  
形成完整 Work Domain Content，保证历史事实与虚构边界可区分，保证下游 Script 能继承核心命题和人物弧。

**Review**  
执行“非事件摘要”、角色驱动、因果结构、主题兑现、人物变化、历史可信度、短剧定位检查。

**Revise**  
措辞局部修；人物目标/冲突不成立则 re-plan；premise 不成立则整体重写当前 Work Draft。

**Persist Gate**  
只有 Work Review critical checks 全部通过才 create/save；Plan、Review notes 不进入 content。

**Relevant Tools**  
`work.get_work`、`work.search_works`、`work.list_works`、`work.create_work`、`work.save_work`、条件性 `research.verify_claim`、`context.build_context/refresh_context`。研究发现由 Harness/Agent 选择现有 research capability。

### 23.2 Script Skill

**Purpose**  
把批准的 Work 转化为可演、可分集、节奏清晰的历史短剧 Script。

**Required Context**  
完整 Work、历史边界、已有 Script、集数/时长/媒介约束。

**Plan**  
规划主线/支线、全剧结构 beats、人物弧、冲突升级、信息揭示、中段转折、Episode 划分、高潮和结局。

**Execute**  
把文学叙述转成可观察行动和戏剧段落，保持 Work 的 premise、theme、人物弧和史实边界。

**Review**  
检查忠实度、动机连续、冲突升级、信息性对白、剧情重复、无意义段落、短剧节奏、历史漂移和结局兑现。

**Revise**  
局部节拍/对白问题局部修；Episode 架构或主线失败则 re-plan Script。

**Persist Gate**  
不是剧情摘要；全剧结构和人物弧可供 Episode Skill 消费；Review PASS 后才写入。

**Relevant Tools**  
`work.get_work`、`script.get_script`、`script.list_scripts`、`script.create_script`、`script.save_script`、条件性 `research.verify_claim`、Context Tools。

### 23.3 Episode Skill

**Purpose**  
把 Script 的一段推进设计成具有独立戏剧任务和明确状态变化的一集。

**Required Context**  
相关 Work/Script 事实、集号、前后 Episode 状态、人物当前状态和本集约束。

**Plan**  
定义 episode goal、opening hook、central conflict、progression、turning point、information/relationship change、exit state、ending hook/resolution。

**Execute**  
形成完整单集设计，使每一段都服务本集任务并推进全剧。

**Review**  
执行必要性、entry/exit state、冲突升级、信息增量、人物/关系变化、集间连续性和短剧节奏检查。

**Revise**  
Hook 或局部节拍可局部修；dramatic job 或状态变化不成立则 re-plan 本集。

**Persist Gate**  
删除本集会损害全剧，且本集完成明确状态变化；Review PASS 后才 create/save。

**Relevant Tools**  
`script.get_script`、`episode.get_episode`、`episode.list_episodes`、`episode.create_episode`、`episode.save_episode`、条件性 research/context tools。

### 23.4 Scene Skill

**Purpose**  
把 Episode 意图转化为可演、发生冲突且改变故事状态的 Scene。

**Required Context**  
Episode 任务、前后 Scene、人物目标/关系/已知信息、地点时间与历史约束。

**Plan**  
定义 purpose、entry state、POV/中心人物、objective、opposing force、stakes、tactics、beats、turn 和 exit state。

**Execute**  
通过动作、选择、障碍和有潜台词的对白让冲突发生，不以说明性对话替代戏剧行动。

**Review**  
检查 Scene necessity、before/after 差异、目标/障碍/冲突、turn、信息/关系/决定/危险变化、对白和可演性。

**Revise**  
对白/动作局部修；冲突或 turn 不成立则 re-plan Scene；无法产生状态变化则删除或与其他 Scene 合并。

**Persist Gate**  
Scene before 不等于 after，且推进 Episode；Review PASS 后才 create/save。

**Relevant Tools**  
`episode.get_episode`、`scene.get_scene`、`scene.list_scenes`、`scene.search_scenes`、`scene.create_scene`、`scene.save_scene`、条件性 location/claim research、Context Tools。

### 23.5 Shot Skill

**Purpose**  
用最少必要且连续、可生产的 Shot 覆盖 Scene 的叙事转折。

**Required Context**  
批准的 Scene、前后 Shot、人物/空间/道具/服装状态、选定 Asset/Media、目标生产形式与限制。

**Plan**  
先设计 coverage strategy 和节奏，再逐 Shot 定义 narrative purpose、subject、action、blocking、framing、size、angle、movement、composition、duration、entry/exit state。

**Execute**  
形成完整镜头组，保持轴线、视线、屏幕方向、人物位置、动作和资产连续性，并让描述可被 Image/Video Provider 执行。

**Review**  
检查叙事意义、coverage 完整性、冗余、景别节奏、连续性、资产一致性和 generation feasibility。

**Revise**  
参数问题局部修；coverage/轴线/节奏失败则 re-plan 镜头组；不具叙事价值的 Shot 删除。

**Persist Gate**  
每个 Shot 有明确功能，整组足以表达 Scene turn，连续且可生产；Review PASS 后才逐项 create/save。

**Relevant Tools**  
`scene.get_scene`、`shot.get_shot`、`shot.list_shots`、`shot.search_shots`、`shot.create_shot`、`shot.save_shot`、`asset.get_asset`、`media.get_media`、Context Tools。

## 24. 当前成熟度评估

成熟度定义：

- **TEST / DEMO**：主要证明 Tool 可调用；
- **EARLY**：已有领域要素与正确边界，但产出质量依赖模型临场发挥；
- **USABLE**：有可重复 lifecycle、domain rubric、persist gate 和真实任务回归；
- **PRODUCTION-READY**：在多类真实历史题材上稳定通过质量评测和人工验收。

| Skill | 当前等级 | 为什么 | 到下一等级需要什么 |
|---|---|---|---|
| Work | EARLY | 有 theme/conflict/timeline 等骨架和研究边界，但可退化为事件摘要 | premise/character-driven planning、Work review、revision loop、真实作品评测 |
| Script | EARLY | 有主线/人物弧/节奏术语和 screen action 原则 | 全剧结构/分集 planning、可演标准、Script review、真实剧本回归 |
| Episode | EARLY | 有 dramatic job/hook/progression/change | 状态变化模型、必要性检查、邻集 review、revision loop |
| Scene | EARLY | 有 objective/conflict/turn/entry-exit | obstacle/tactics/beats/subtext、Scene necessity、before/after gate |
| Shot | EARLY | 镜头术语和 continuity 基础较强 | coverage strategy、axis/direction、asset consistency、generation feasibility review |

五者均比纯 Tool Wrapper 更成熟，因此不定为 TEST/DEMO；但缺乏稳定质量闭环，不能定为 USABLE 或 PRODUCTION-READY。

## 25. 与正式生产级创作能力的差距

正式生产能力需要的不只是更多字段，而是可重复的判断：

1. **目标理解**：知道用户要创作什么、给谁看、篇幅和基调是什么；
2. **上下文充分**：知道哪些上游事实、邻接状态和历史证据必须先读；
3. **领域规划**：每一级知道如何从上一级推导本级结构；
4. **完整执行**：不以摘要、测试字段或机械切分冒充正式成果；
5. **自审标准**：每个领域有自己的 critical checks；
6. **修订闭环**：知道局部修、re-plan 和重写的区别；
7. **持久化纪律**：只有值得长期保存的结果才 create/save；
8. **质量回归**：用真实历史题材和盲评/人工 rubric 验证 Skill，而非只验证 Tool 调用成功。

当前最核心缺失是第 3–7 项，尤其是 **领域化 Plan + Review + Revise + Persist Gate**。

## 26. ComfyUI MCP 前是否应优先加固 Creative Skill

结论：**应当优先加固。**

理由：

1. Production/ComfyUI 位于创作链下游，只能物化已批准的 Shot；
2. 当前 `shot-production` 明确不重新设计 Shot，这是正确边界，因此它不会补救上游故事问题；
3. 低质量 Work 会产生低质量 Script、Episode、Scene 和 Shot；视觉 Provider 越强，错误物化成本越高；
4. 当前 Tool/Java/Media 已足以承载 Creative Skill E2E，不需要等待新基础设施；
5. 先冻结“什么是批准的 Shot”，再接 ComfyUI，能为生成评测提供稳定输入。

可以并行做不依赖内容质量的 ComfyUI 技术预研，但不建议把正式 Generation 接入作为当前主线验收目标。

## 27. 建议后续实施批次

为保持精简，建议分为 4 个边界清晰的批次：

### Batch 11.1：Creative Lifecycle 基线

- 仅修改五个核心 Skill Core；
- 加入 Understand/Gather/Plan/Execute/Review/Revise/Persist；
- 明确 missing-context、Research decision 和 Review FAIL 行为；
- 不增加 Tool、Java、运行时或通用 Review Skill；
- 增加轻量静态防回归和 Skill 格式校验。

### Batch 11.2：Work + Script 正式化

- 先加固最上游两个 Skill；
- 增加必要的一层 `references/`；
- 用至少两类历史题材做 forward evaluation：事件型政治剧、人物关系型历史剧；
- 重点验证“非事件摘要”和“非剧情梗概”。

### Batch 11.3：Episode + Scene + Shot 正式化

- 加固单集任务、Scene 状态变化和 Shot 影视语言/生产可行性；
- 复用现有邻接 list/search、Asset/Media get；
- 不修改 Production Tool。

### Batch 11.4：真实 Creative E2E 与质量回归

- 从 Research Context 生成一个完整 Work→Script→Episode→Scene→Shot 样本；
- 在每层保存前记录 Review 结果于 Run 输出，不写入 Java；
- 使用领域 rubric + 人工抽检评估；
- 验证持久化对象完整、上下游一致、无低质量 Draft 泄漏；
- 通过后再进入 ComfyUI 正式对接。

不建议把 11.1–11.3 合成一次巨大改写；也不建议为批次实施创建 Workflow Engine。

## 28. 最终结论

### 28.1 对核心问题的回答

**Q1：为什么当前只能支持 PoC/E2E/Tool 验证，而不足以正式创作？**  
因为当前工程已经证明“能读取、创建、保存和恢复对象”，但没有证明 Agent 能稳定规划、执行、评审和修订这些对象。Skill 对 Tool 与持久化的说明远强于对创作过程和质量 Gate 的说明。

**Q2：最大问题是 Tool 不够还是缺少方法论？**  
主要是缺少专业创作方法论和质量闭环。现有 Tool 对当前加固足够；没有已证实的 Tool/Java 阻塞。

**Q3：How to plan Work/Script/Scene/Shot 是否应定义在对应 Skill？**  
是。规划标准属于领域专业知识，且各层完全不同；放在 Tool、MCP、Java 或 Host Adapter 都会破坏职责边界。

**Q4：是否采用 Plan→Execute→Review→Revise→Persist 统一生命周期？**  
是。统一的是生命周期和 Gate，不是把不同领域方法抽象成同一个 rubric，也不是实现状态机。

**Q5：Harness 与 Skill 分别负责什么？**  
Harness 负责 Loop、selection、dispatch、Context 生命周期和继续/停止；Skill 负责专业方法、上下文充分性、研究判断、领域 Plan/Review/Revision、Persist Gate 和 Tool 策略。

**Q6：提高质量是否优先修改 Skill 而不是 Java/MCP/Tool/数据库？**  
是。当前 `content` 可保存丰富结果，MCP 是动态投影，Java 只做长期记忆；修改基础设施不会自动增加创作判断。

**Q7：哪些必须改 Java/Tool，哪些纯 Skill 可解决？**  
当前发现全部核心质量问题均为 A 类 Skill only；B 类和 C 类没有已证实必需项。只有未来真实 E2E 暴露数据获取或稳定持久字段的客观阻塞时再评估。

**Q8：进入 ComfyUI MCP 前是否先加固 Creative Skill？**  
是，明确推荐。先确保 Shot 来源于合格 Work/Script/Episode/Scene，并定义可生产 Shot Gate，再扩大视觉生成投入。

### 28.2 最终验收判断

```text
CURRENT_WORK_SKILL_PRODUCTION_READY = NO
CURRENT_SCRIPT_SKILL_PRODUCTION_READY = NO
CURRENT_EPISODE_SKILL_PRODUCTION_READY = NO
CURRENT_SCENE_SKILL_PRODUCTION_READY = NO
CURRENT_SHOT_SKILL_PRODUCTION_READY = NO

PLAN_CAPABILITY = PARTIAL
EXECUTE_CAPABILITY = PARTIAL
REVIEW_CAPABILITY = PARTIAL
REVISE_CAPABILITY = MISSING
PERSIST_GATE = PARTIAL

CREATIVE_SKILL_LAYER_PRODUCTION_READY = NO

SKILL_ONLY_IMPROVEMENT_POSSIBLE = YES
TOOL_CONTRACT_CHANGE_REQUIRED = NO
JAVA_CONTRACT_CHANGE_REQUIRED = NO

CREATIVE_SKILL_HARDENING_BEFORE_COMFYUI = RECOMMENDED
```

### 28.3 一句话结论

> 当前 Drama Plugin 距离“能够正式创作一部历史短剧”最核心缺失的，不是再增加一个 create Tool，而是让每个创作 Skill 真正教会 Agent：如何在充分 Context 与历史边界内规划作品，形成完整 Draft，用该领域独有的标准审查和修正它，并且只在质量通过时把它保存为长期事实。
