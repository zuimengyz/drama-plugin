# Batch 6.D0 — Dialogue Layer Architecture & Gap Audit 报告

执行日期：2026-08-19（Asia/Shanghai）

性质：ARCHITECTURE AUDIT + GAP AUDIT + DESIGN

结论：**PASS_WITH_GAPS_FOUND**

实施状态：**未进入 D1**

## 1. 执行摘要

当前系统已经能持久化 Work → Script → Episode → Scene → Shot，并能继续到 Asset、Media、Image、Video；但它尚没有可由 Audio、字幕、lip-sync 和时长规划直接消费的正式 Dialogue Layer。

主要结论如下：

- Script 保存的是全剧适配合同、主线、信息揭示、Episode/Scene 结构需求和节奏策略，不是完整文学剧本；当前样本没有具体台词、旁白、角色说话风格或声音人格。
- Scene Skill 的规范目标是“可表演的动作与对白”，但 6.0R-E2E 的实际 Scene 只持久化了剧情目的、动作/节拍和 `dialogueSubtextIntent`，没有任何正式对白行。
- Shot 保存的是镜头叙事状态、动作、构图、机位、连续性和字符串型时长估算；个别 `requiredTransition` 含“提出、拒绝、下令”等口语行为摘要，但没有 speaker、spoken text 或 Scene Dialogue 引用，属于 **AD_HOC**，不是正式 spoken-content。
- 当前 Dialogue 没有真正的“产生点”；预期应在 Scene Development 产生，却在 Scene 持久化前被压缩为功能描述。Shot 只能再次概述剧情，Visual Production 不会、也不应代写台词。
- 旧 Dify 已实践过正确的核心依赖：`sourceSceneScript` 是台词来源，Shot 只绑定/少量压缩，Audio 只能消费不得擅自改写；但旧方案把对白、旁白、环境声、拟音、音乐、混音、时间轴和 lip-sync 混在大 Audio/AV JSON，并依赖固定节点图，不适合直接迁回。
- 推荐最小方案是：**Scene `content.spokenContent[]` 保存 Dialogue/Narration 正文作为 Source of Truth；Shot `content.spokenContentRefs[]` 仅绑定其消费项；不新增 Dialogue Entity、数据库表或 Tool。**
- 采用 Scene 内稳定 item ID，并使用 Work 范围的稳定 `speakerKey` + `displayName`；已有角色 Asset 可作可选绑定，但不能让 Dialogue 依赖视觉 Asset 先存在。
- 每个 spoken item 必须有可追溯的历史关系、戏剧意图、简洁表演意图与预计时长；“史料原话”必须额外具有可核对的来源定位和原文证据，不允许仅凭模型判断。
- 对需要 spoken content 的 Scene，应先完成 Dialogue 与 duration feasibility，再做 Shot Planning 和付费 Visual Production；纯环境、战斗动作、沉默反应等镜头不强制对白。

最终判定：

```text
DIALOGUE_LAYER_REQUIRED = YES
CURRENT_DIALOGUE_SUPPORT = PARTIAL
PRIMARY_DIALOGUE_GAP = Scene 未持久化正式 spoken text，Shot 无稳定绑定，provenance/duration 不可消费
RECOMMENDED_SOURCE_OF_TRUTH = Scene.content.spokenContent[]
INDEPENDENT_DIALOGUE_ENTITY_REQUIRED = NO
NEW_DATABASE_TABLE_REQUIRED = NO
NEW_TOOL_REQUIRED = NO
NEW_SKILL_REQUIRED = NO（D1 先加固 Scene/Shot/Review；独立 Skill 仅在规模证明后 DEFER）
SHOT_DIALOGUE_BINDING_REQUIRED = YES（仅对实际承载 spoken content 的 Shot）
HISTORICAL_PROVENANCE_REQUIRED = YES
DURATION_ESTIMATION_REQUIRED_BEFORE_VISUAL = CONDITIONAL（存在 spoken content 时为 YES）
EXISTING_COMPLETED_VISUALS_REUSABLE = YES
BATCH_6_D1_RECOMMENDED = YES
```

## 2. 审计范围、方法与证据边界

审计了：

- Plugin Domain Contract、Tool Catalog、Provider、HTTP 映射、MCP generic adapter、MySQL contract DDL；
- Work、Script、Episode、Scene、Shot、Asset、Media 相关 Skills 与 Review/Planning 规则；
- Batch 6.0R-E2E 的正式创建输入、持久化回读结果 artifact、27-Shot transition matrix、生产计划、reference manifest、R2 checkpoint、credit ledger 和已完成媒体；
- `/Users/yizhao/IdeaProjects/AI_historical/src/main/resources/dify_dsl` 下全部 6 个 DSL 文件；
- 旧 Java/Dify 时代的 `HistoricalSceneShot`、`ShotAudioPlanV3`、`ShotAvPlanV3`、Compiler 与 Mapper，仅作为 reference。

证据限制：本地当前 Plugin 仓库只冻结了 Java ToolApi 映射和 MySQL schema，没有当前七类长期记忆 Java Controller/Service/Repository 源码；`plugin/docs/reports/09-...` 也明确当时“未实现 Java”。正式 MCP 端口在本次审计时未运行，未为审计修改配置或启动生产服务。因此当前长期记忆内容以创建 6.0R-E2E 的正式 MCP 回归脚本、其持久化 list 回读断言、`text-regression-result.json` 以及后续生产 checkpoint 交叉验证。旧 `AI_historical` Java 类不得误当成新长期记忆实现。

本批只新增本报告。没有修改代码、Contract、Skill、数据库或作品数据；没有调用 Comfy、TTS 或任何生成 Provider。

## 3. 当前代码与长期记忆真实模型

### 3.1 Stable Envelope + open content

`contracts/creation.py` 的 Work/Script/Episode/Scene/Shot 都只有稳定 Envelope 与开放 `content: dict`。Asset、Media 同样使用开放 content。Tool catalog 的 create/save 只校验 `content` 是 object，不校验其内部 Dialogue 结构。

| Domain | Stable envelope | 当前可演进内容 | Dialogue 专属机器字段 |
|---|---|---|---|
| Work | id/title/description | `content` | 无 |
| Script | id/workId/title | `content` | 无 |
| Episode | id/scriptId/episodeNo/title | `content` | 无 |
| Scene | id/episodeId/order/title/location | `content` | 无 |
| Shot | id/sceneId/shotNo/title/shotType | `content` | 无 |
| Asset | id/scope/type/name/referenceMediaIds | `content` | 无；Asset 是视觉稳定身份 |
| Media | id/workId/assetId/shotId/type/purpose/sourceRef | `content` | 只有 `AUDIO` 媒体类型，不是 Dialogue Source |

MySQL contract 恰好七表，`drama_scene.content`、`drama_shot.content` 为 JSON；只有 `drama_media.duration_ms` 是实际媒体时长。没有 Dialogue 表，也没有必要因本审计新增第八表。

### 3.2 Controller / Service / Persistence / MCP 边界

- Tool catalog 是机器输入 schema 真源；`scene.create/save` 和 `shot.create/save` 已能完整替换开放 content。
- HTTP Provider 把相同 snake_case envelope/content 传至 `/api/tool/...`。
- MCP adapter 对 Plugin registry 做通用投影，不含 Dialogue 特殊 dispatch。
- Java 预期只负责 identity、schema/persistence、version 和稳定父子关系；当前本地材料不能证明它对 content 内字段有更细验证。
- 因此 D1 可利用既有 content 扩展语义，无需先扩 Tool、MCP 或数据库。

### 3.3 当前 provenance 能力

- Research contract 能表达 claim、excerpt、source、confidence、tags，但 Historical Research Skill 默认把它保留在 Agent Run Context，不持久化 Research Entity。
- Work 样本持久化 `researchSources[]`、`historicalSpine[].evidenceClass/evidenceRef` 和 `dramatizedButCompatible[]`。
- Scene/Shot 只保留 `requiredSpineBeatIds`；可追到历史 beat，但无法证明某句台词是不是史料原话。

## 4. Script Dialogue 能力

Script Skill 允许规划 `dialogue strategy`，并要求整体可通过动作、行为、对白和视觉信息呈现；同时明确禁止“详细 Scene 对白/action”。这意味着 Script 的职责是对白策略与全剧可听性，不是台词正文 Source of Truth。

6.0R-E2E Script 实际保存：

- adaptationContract、mainLine、informationReveal；
- episodeArchitecture、sceneRequirements；
- pacing 与结构 Review。

实际不存在：

- 具体 dialogue lines / narration；
- speaker 引用；
- 角色语言风格或跨 Scene voice bible；
- 表演 delivery；
- 台词 provenance；
- spoken duration。

判定：**结构化适配大纲，而非完整文学剧本。** 当前标题虽称“历史短剧剧本”，内容仍不是可直接拍摄/配音的文学剧本。

## 5. Scene Dialogue 能力

Scene Skill 的设计目标明确包括：完整候选 Scene 要有“playable action and dialogue”；Review 检查 Dialogue/subtext；持久化规则却只列出 action、turn 等通用 facts，没有规定正式台词结构。

6.0R-E2E 每个 Scene 实际保存：

- `characters`（字符串名字）；
- objective/opposition/stakes；
- `tacticsAndBeats`（由 Shot 动作摘要组成）；
- `dialogueSubtextIntent`（统一为“争取、拒绝、催迫或服从，不讲授历史”）；
- input/transition/output 与 review。

不存在 `dialogue/dialogueLines/speaker/line/narration/performance` 等正文。故 Scene 当前是**高质量可视化剧情/动作摘要**，尚未达到“可拍摄文学场景”。Skill 意图与真实持久化结果存在 gap。

## 6. Shot Dialogue 能力

Shot 当前主要表达：叙事目的、Narrative Input/Transition/Output、subject/action/blocking、framing、angle、camera、composition、visual entry/exit、continuity、first appearance、generation feasibility 和 `rhythmDurationEstimate`。

`requiredTransition` 中有“王思礼提出……哥舒翰拒绝”“唐玄宗令使者催……”“火拔归仁以贼至为由迫……”等自然语言，但它们是剧情动作摘要：

- 不知道逐字说什么；
- 不知道一个描述中有几句、顺序和说话边界；
- 不知道是否是画外音、诏书、口头命令或字幕；
- 没有 stable speaker；
- 没有 provenance、performance、duration；
- 不能被 TTS 或字幕直接消费。

判定：

```text
SHOT_SPOKEN_CONTENT_STATUS = AD_HOC
```

开放 content 在技术上“可以装”Dialogue，但当前没有正式约定，不能因此判为 FORMAL。

## 7. 当前 Skill 能力

| Skill | 当前责任 | Dialogue 现状 |
|---|---|---|
| Work Creation | 历史骨架与文学基础 | 明确不写 Scene dialogue |
| Script Adaptation | 全剧可视听结构、dialogue strategy | 允许对白作为表达手段，但禁止详细 Scene 台词 |
| Episode Development | 单集戏剧任务和状态变化 | 禁止详细 Scene dialogue/action |
| Scene Development | 可表演 Scene、动作、对白、潜台词 | 应是正文产生点，但没有最小持久化形状与 hard gate |
| Shot Design | dialogue/reaction coverage、rhythm/duration | 规则假定 Scene 已有对白，却无引用/绑定要求 |
| Shot Production | image/video/audio 物理媒体 | 可调用 `generate_audio`，但无正式 Dialogue 输入；容易被迫重写 |
| Review | 各 Skill 内嵌 Review | 检查对白戏剧功能，不检查 exact text、speaker identity、quote provenance 或 speech duration |

不存在独立通用 Review Skill；本项目采用各领域 Skill 自审。D1 应延续此结构，避免新建大量 Plan/Write/Review/Revise Skills。

## 8. 当前 Production 数据流

真实链路是：

```text
Work historical spine/evidence refs
  ↓  Script Adaptation：结构与 dialogue strategy
Script mainLine / sceneRequirements
  ↓  Episode Development：单集状态链
Episode dramatic job
  ↓  Scene Development：本应写 playable dialogue
Scene tactics/action + dialogueSubtextIntent（没有正文）
  ↓  Shot Design：再次概述 speech act
Shot requiredTransition / visual plan / 5–9 sec 字符串估算
  ↓  Shot Production
Image prompt → silent 5-second video (generate_audio=false)
```

生产 artifacts 进一步证明：pre-spend plan 对 19 个目标视频统一覆盖 `durationSeconds=5`、`generate_audio=false`；完成的 1-01/1-02 视频实际时长分别约 5.041667/5.083333 秒。

## 9. Dialogue 信息产生、传递与丢失点

| 阶段 | 产生 | 保存 | 传递 | 丢失/风险 |
|---|---|---|---|---|
| Research/Work | 史实事件、人物行为、evidenceRef | Work content | beat IDs | 无逐字引语证据链 |
| Script | dialogue strategy、可听信息 | Script content | Scene requirements | 不写具体台词是合理边界 |
| Episode | 场景任务 | Episode content | Scene job | 不写具体台词是合理边界 |
| Scene | **规范上应产生具体对白** | 实际只存 dialogue function | 动作摘要传到 Shot | **PRIMARY LOSS POINT** |
| Shot | 可决定覆盖哪句话 | 实际无 refs，只重复 speech act | 视觉 prompt | ownership/原文/时长全部丢失 |
| Visual Production | 不应创作台词 | silent Media | 可留给后期 | 固定 5 秒后可能塞不下对白 |
| Future Audio | 应消费正式 Dialogue | 尚无输入 | — | 当前必须重新理解/改写剧情，设计失败 |

## 10. 当前 6.0R-E2E Dialogue Gap Matrix

说明：`D`=Dialogue required，`N`=Narration required；`C`=conditional。当前所有行的 formal dialogue source、exact spoken text、provenance、spoken duration 均不存在。Speaker “可推导”不等于已有稳定引用。

| Scene / Shot | 当前叙事信息 | D | N | Speaker | 视觉时长兼容 | Gap / 复用判断 |
|---|---|---:|---:|---|---|---|
| S1 / 1-01 叛军止步 | 环境建立、守势有效 | NO | C | N/A | 5s 可用 | MISSING_NARRATION_DECISION；**SAFE_TO_REUSE** |
| S1 / 1-02 主帅阅图 | 主帅确认固守 | NO | NO | 哥舒翰可推导 | 5s 可用 | NO_DIALOGUE_GAP；**SAFE_TO_REUSE** |
| S1 / 1-03 三十骑之议 | 王思礼建议，哥舒翰拒绝 | YES | NO | 两人名字可推导，稳定 ref 缺 | 未生产；5–9s 很可能不足双人交锋 | MISSING_SPOKEN_TEXT/SPEAKER_REF/PROVENANCE/PERFORMANCE/DURATION |
| S1 / 1-04 灞上军籍 | 调军盖印、互疑 | NO | C | N/A | 未生产 | MISSING_NARRATION_DECISION；视觉可表达 |
| S2 / 2-01 羸兵之报 | 杨国忠提出速战判断 | YES | NO | 杨国忠 Asset 可后绑 | 固定 5s 未验证 | MISSING_SPOKEN_TEXT/PROVENANCE/DURATION |
| S2 / 2-02 御座决令 | 玄宗下令出关复陕洛 | YES | NO | 玄宗 Asset 可后绑 | 固定 5s 高风险 | MISSING_SPOKEN_TEXT/QUOTE_CLASSIFICATION/DURATION |
| S2 / 2-03 守险回奏 | 哥舒翰说明诱饵与固守 | YES | NO | 哥舒翰 Asset 可后绑 | 固定 5s 高风险 | MISSING_SPOKEN_TEXT/PROVENANCE/PERFORMANCE/DURATION |
| S2 / 2-04 项背相望 | 连续诏使压缩选择 | C | C | 中使未建稳定身份 | montage 可无对白 | AMBIGUOUS_SPOKEN_MODE；先决定诏语/旁白/纯视觉 |
| S2 / 2-05 开关之令 | 接令、开关 | C | NO | 哥舒翰可推导 | 动作可表达 | 可用短军令或沉默；需 Host 决定 |
| S3 / 3-01 大军离关 | 地理转移 | NO | C | N/A | 视觉优先 | MISSING_NARRATION_DECISION |
| S3 / 3-02 山河夹军 | 七十里隘道、无法展开 | NO | C | N/A | 视觉可表达但数字信息难 | 可旁白/图文，非必需 Dialogue |
| S3 / 3-03 疏阵藏锋 | 崔乾祐令精兵伏后 | C | NO | 崔乾祐 Asset 可后绑 | 短令可容纳 | MISSING_SPOKEN_MODE/TEXT/DURATION（若说） |
| S3 / 3-04 偃旗深入 | 催军推进、敌军佯退 | C | NO | 哥舒翰/王思礼可推导 | 动作密集 | 军令可用喊声或动作；需先定后拍 |
| S4 / 4-01—4-06 | 木石、毡车、火烟、误射、后袭、崩溃 | NO | C | 多为群体 | 5s 单镜动作规划可行 | Dialogue 无 gap；旁白为风格选择；battle cries 属 Audio/SFX 边界 |
| S5 / 5-01—5-04 | 溃散、壕沟、残部入关、关旗易手 | NO | C | 多为群体 | 5s 视觉节拍可行 | “八千”若必须精确传达需旁白/图文；否则无 Dialogue gap |
| S6 / 6-01 榜收散卒 | 揭榜收卒、复守无力 | C | C | 哥舒翰可推导 | 视觉信息较多 | 榜文、口头招募或旁白模式未定 |
| S6 / 6-02 百骑围驿 | 火拔归仁借“贼至”迫其上马 | YES | NO | 火拔归仁/哥舒翰 Asset 可后绑 | 固定 5s 高风险 | MISSING_SPOKEN_TEXT/PROVENANCE/PERFORMANCE/DURATION |
| S6 / 6-03 缚马东行 | 被缚、复守终止 | NO | NO | N/A | 视觉优先 | NO_DIALOGUE_GAP |
| S6 / 6-04 宫墙无火 | 平安火不续、召相议避乱 | C | C | 玄宗可推导 | 5s 只能传一个核心信息 | AMBIGUOUS_SPOKEN_MODE/SHOT_DURATION_CONFLICT |

### 10.1 Host-driven 十问抽样

| 样本 | 是否说话 | 谁说 | 具体文本 | 意图 | 必须保留 | 旁白 | 语气 | 秒数 | Shot 可承载 | Audio 可直消 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1-01 环境建立 | AVAILABLE: NO | N/A | N/A | AVAILABLE | N/A | AMBIGUOUS | N/A | MISSING | DERIVABLE | NO |
| 1-03 建议/拒绝 | AVAILABLE: YES | DERIVABLE | **MISSING** | AVAILABLE | AMBIGUOUS | AVAILABLE: NO | MISSING | MISSING | AMBIGUOUS | **NO** |
| 2-02 皇令 | AVAILABLE: YES | DERIVABLE | **MISSING** | AVAILABLE | DERIVABLE: core order | AVAILABLE: NO | MISSING | MISSING | AMBIGUOUS | **NO** |
| 4-03 战斗逆转 | DERIVABLE: no dialogue | N/A | N/A | AVAILABLE | N/A | AMBIGUOUS | N/A | MISSING | DERIVABLE | NO（缺 Audio plan，不缺 Dialogue） |
| 6-02 欺骗/逼迫 | AVAILABLE: YES | DERIVABLE | **MISSING** | AVAILABLE | DERIVABLE | AVAILABLE: NO | MISSING | MISSING | AMBIGUOUS | **NO** |
| 6-04 结尾 | AMBIGUOUS | DERIVABLE | MISSING | AVAILABLE | AMBIGUOUS | AMBIGUOUS | MISSING | MISSING | AMBIGUOUS | **NO** |

“Host 能临时创作”只会把 MISSING 变成一次性推断，不会形成经过 Review、可复用、可追溯的长期事实。

## 11. 旧 Dify DSL 扫描结果

共扫描 6 个 `.yml`；没有额外 `.yaml/.json`。重要结构如下：

| DSL / workflow | field / node | 语义 | upstream | downstream |
|---|---|---|---|---|
| 子工作流 A：单集文学剧本 | `episodeScript.scenes[].dialogues[]` | lineNo/character/line/emotion/subtext | scene plan + history | language calibration、character scripts、B |
| 子工作流 A | language calibration / `dialogueChangeLog` | 保持场景结构，仅润色台词时代语言 | episodeScript | calibrated episodeScript |
| 子工作流 B：单场分镜与表演 | `sourceSceneScript` | 当前场文学剧本，动作/台词/非语言动作主依据 | A | shot planner |
| 子工作流 B | `shotPlans[].dialogueLines[]` | character/line/sourceLineNo | sourceSceneScript | C / persistence |
| 子工作流 B | `performancePlan` | emotion、face、eye、body、microAction、speechRhythm、subtext | scene + character scripts | shot performance |
| 子工作流 B | `audioRef.dialogueSource/dialogue/narration/sfx/bgmMood` | Shot 级来源与音频提示 | dialogueLines + scene | C |
| 子工作流 C：单镜头视听 | normalize dialogue | dialogue → dialogueLines → audio.dialogue 的降级读取 | shot storyboard | shotAudioPlan |
| 子工作流 C | `shotAudioPlan` / subtitle / edit | 单镜头声音、字幕、剪辑时间线 | exact shot dialogue + duration | AV production |
| generationTarget v3 AUDIO | `dialogueItems/narrationItems/...` | 完整音频生产 plan | target context | Java compiler/provider |
| generationTarget v3 VIDEO_WITH_AUDIO | audioPlan + syncPlan + lipSyncItems | AV 同步、嘴型、时间轴 | Shot AV input | compiler/provider |

实际存在 Prompt 指定的 `sourceSceneScript`、`dialogueLines`、`dialogueSource`、`audioRef`、`shotAudioPlan`；没有发现一个名为 `dialogueSource` 的独立长期 Dialogue Entity。

## 12. 旧 DSL Dialogue / Audio 数据流

```text
Episode scene plan（无完整对白）
  ↓
episodeScript.scenes[].dialogues（文学正文）
  ↓ language calibration（保留结构、可追变更）
sourceSceneScript
  ↓
shotPlans[].dialogueLines + sourceLineNo
  ↓
audioRef / shotAudioPlan / subtitlePlan / editPlan
  ↓
AUDIO or VIDEO_WITH_AUDIO target plan
  ↓
Java compiler / provider
```

业务上正确的是“上游正文授权、下游引用消费”；架构上错误的是固定工作流、字段重复和把 Dialogue/Audio/Mix 一次性耦合。

## 13. KEEP / ADAPT / DROP / DEFER

| 分类 | 内容 | 理由 |
|---|---|---|
| KEEP | Scene 文学正文是具体台词权威来源 | 防止 Shot/Audio 重写剧情 |
| KEEP | 每行有 speaker、text、sequence、intent/performance | TTS、字幕、表演、时长均需 |
| KEEP | Shot 绑定源行，而非复制后成为新真源 | 避免多份正文漂移 |
| KEEP | Audio 不得新增/改写输入台词 | Provider 应 consume |
| ADAPT | `sourceLineNo` → stable spoken item ID | 行号会随修订漂移 |
| ADAPT | character 字符串 → work-scoped speakerKey + displayName；Asset 可选绑定 | 兼顾稳定身份和低耦合 |
| ADAPT | `dialogueSource=original/adapted/none` → 历史 provenance 分类 + evidence chain | “original”含义不清，易冒充史料原话 |
| ADAPT | emotion/speechRhythm/subtext → 简洁 performanceIntent | 保留生产价值，避免细碎字段 |
| ADAPT | duration 与 Shot 同步规则 → Scene 估时先行，Shot 绑定后做 feasibility | 防止先拍后塞 |
| DROP | 固定 A→B→C Node Graph | 违背 Host 自主推理 |
| DROP | 每层重复整句 dialogue/audioRef | 多 Source of Truth |
| DROP | 强制每 Scene 有对白、按台词拆 Shot | 与当前 Skill 原则冲突 |
| DROP | 大而全默认字段、空值占位 | 增加噪音和伪确定性 |
| DEFER | Voice ID、pitch/breath、空间声、dB、BGM、mixing、timeline | 属未来 Audio Layer |
| DEFER | lip-sync tolerance、mouth visibility、beat sync | 需实际音频/AV Provider |
| DEFER | 多语言/translation table | 当前无正式需求 |

## 14. Dialogue Layer 与 Audio Layer 边界

| Dialogue Layer | Future Audio Layer |
|---|---|
| Dialogue / Narration 类型 | TTS Provider、Voice ID、模型 |
| stable item ID、sequence | 生成 job、实际 Audio Media ID |
| speaker identity | 音色、pitch、breath、distance |
| 正式文本 | 实际音频、实际 duration |
| dramatic intent / must-keep | ambience、foley、SFX、music |
| 简洁 performance intent | mixing、ducking、空间声 |
| historical provenance | audio timeline、lip-sync、sync tolerance |
| estimated speech duration | waveform/字幕实际时间码 |

Dialogue 可以说明“克制而坚决、压低声音、留出停顿”；不应保存特定 voiceId、dB 或混音参数。

## 15. Historical Dialogue Provenance

最小语义需区分四类，而最终 enum 命名可在 D1 冻结：

1. 文献明确记载并可核对的原话；
2. 依据文献语义压缩/改写；
3. 依据历史事实进行兼容的戏剧化创作；
4. 纯功能性连接台词。

最小证据链：

```text
spoken item
  → provenance relation
  → evidenceRef/sourceRef
  → exact source locator
  → source excerpt（仅当声称“原话”时强制）
```

仅有 `requiredSpineBeatIds` 或“《资治通鉴》卷218，第123段”不足以把一句现代生成文本标为原话。Review 规则必须是：没有可核对 excerpt + locator，就只能标为改写/戏剧化/功能性，绝不能自动升级为 quote。

## 16. Speaker Identity / Asset Reference 分析

当前人物身份：Work actor hierarchy、Scene characters 都是名字字符串；新架构没有 Character Entity。视觉生产为哥舒翰、杨国忠、玄宗、崔乾祐、火拔归仁建立了 stable Asset ID，但王思礼仍缺稳定视觉 Asset，且旁白/不出镜人物不一定需要视觉 Asset。

候选比较：

| 方案 | 结论 |
|---|---|
| 只用 name | 否；同名、别名、跨语言和身份漂移风险 |
| 强制 assetId | 否；把 Dialogue 错误依赖于视觉资产生命周期 |
| 新 Character Entity | 否；当前需求不足以证明第八实体 |
| Work 范围 `speakerKey` + displayName，optional assetId | **推荐** |

`speakerKey` 是 content 内稳定业务 key，不是新表；Scene spoken item 引用它。若后续 Asset 存在，可在 Work character registry 或 item speakerRef 中附加 `assetId`，但 Audio/Dialogue 不应因缺视觉 Asset 阻塞。

## 17. Dialogue Ownership 方案比较

| 方案 | Source of Truth / 重复 | Shot/Audio/字幕 | 复杂度 | 结论 |
|---|---|---|---|---|
| A Script 正文 | 跨 Scene 大对象，局部修订/Shot 拆分困难 | 需反查 Scene | 低表数、高 Host 复杂度 | 不推荐 |
| B Scene 正文 | 与可表演 Scene 同生命周期；不重复 | Shot refs、Audio/字幕直接投影 | 最小 | **推荐** |
| C Shot 正文 | 镜头重组即复制/漂移；反应镜头难归属 | Audio 易取但 Scene 失真 | 高重复 | 不推荐 |
| D 独立 Entity | 身份/版本最强 | 查询方便 | 新表/Tool/关系过重 | 当前 NO |
| E Scene 正文 + Shot binding | Scene SoT，Shot 只引用 item ID | 最适合重切、字幕、Audio | 仅 content 约定 | **RECOMMENDED_MINIMAL_MODEL** |

## 18. “Scene Dialogue + Shot Binding”假设验证

```text
SCENE_DIALOGUE_PLUS_SHOT_BINDING = FIT
```

原因：Scene Skill 已是可表演对白的自然创建者；Shot Skill 已承担 dialogue/reaction coverage；开放 content 和既有 save Tool 足以持久化两者；Shot binding 能在不复制正文的情况下支持说话者镜头、反应镜头、画外音和跨镜头延续。

限制：binding 只在实际承载 spoken content 时存在，不能要求所有 Shot 都有 refs；一个 spoken item 可被多个 Shot 覆盖，但 Audio 只生成一次。

## 19. Duration / Shot Compatibility

当前存在明确结构风险：

- 所有 Shot 只存字符串 `rhythmDurationEstimate="5–9 seconds"`；
- 生产计划又统一硬覆盖为 5 秒；
- 已完成视频确为约 5 秒；
- 1-03 双人建议/拒绝、2-02 皇令、2-03 固守陈述、6-02 欺骗与逼迫都可能超过 5 秒；
- 当前没有逐句估时或 Shot spoken load 检查。

推荐依赖方向：

```text
Scene dramatic design
  → formal spokenContent（仅需要时）
  → rough duration estimate
  → Shot coverage + numeric planned duration
  → duration feasibility Review
  → paid Visual Production
  → TTS actual duration（未来）
  → Audio timing / subtitle timing
```

估时职责：D1 由 Host/Skill 使用语言相关的字数/字符数粗估并允许 LLM 校正；不调用 TTS。实际 TTS duration 属 Audio Layer，产生后可微调停顿/剪辑，但不得重写已审 Dialogue。估值应是数字毫秒或秒，不是自由文本。

## 20. Dialogue Review 最小要求

| 等级 | 检查 |
|---|---|
| MUST | speaker correctness；historical consistency；quote provenance；事实归属；Scene dramatic function；exact text 完整性；duration feasibility；无现代语言污染；Audio 不改写 |
| SHOULD | character voice consistency；speech naturalness；subtext/performance intent；信息冗余；exposition overload；与动作/沉默关系 |
| DEFER | 声纹/voice casting；TTS 发音效果；实际 lip-sync；混音响度；多语言译配 |

Review 必须区分“台词是史实内容”与“台词是文献原句”，后者门槛更高。

## 21. Skill Boundary

D1 最少不新增 Skill：

- Script Adaptation：继续只负责 dialogue strategy、角色整体语言原则（如有必要），不写逐场正文。
- Scene Development：Plan → Write → Review → Revise spokenContent，并持久化 Scene SoT。
- Shot Design：读取 Scene spokenContent，决定 coverage/binding、reaction、silence 和 numeric duration；不得改写正文。
- Shot Production：消费绑定后的正文与 performance intent；视觉 Provider 只获得视觉/lip visibility 所需信息，未来 Audio Provider 直接消费文本。

若未来出现跨 Scene 批量台词重写、独立对白编剧协作或大量版本管理，再评估独立 Dialogue Skill；当前为 DEFER。

## 22. Tool Contract Boundary

```text
NEW_TOOL_REQUIRED = NO
```

理由：Scene/Shot create/save 已持久化开放 object；get/list/search 已能按父层读取。新增 create/get/save/search/delete_dialogue 会复制生命周期并破坏精简原则。

D1 只需 Skill 语义、content convention 和测试；若未来出现“只读取数千条 Dialogue 而不加载 Scene”的真实性能/协作需求，再重新审计独立 Tool。

## 23. Java Long-Term Memory Boundary

Java 应保持：

- 保存 Scene/Shot content；
- 保证 full replacement、version 和父子 identity；
- 可选做最薄的结构/引用 validation（若正式 contract 决定提升为 typed content）；
- 不生成台词、不做历史判断、不估算语速、不做 Review。

基于当前开放 content 推荐 D1 不改 Java/表。若 D1 决定把内部 content schema 升为 Java 强类型 DTO，应先证明跨 Host 机器校验的收益；否则属于过度实现。

## 24. Future Audio Consumer 验证

推荐模型可直接投影：

```text
Scene spoken item
  {speakerRef, text, performanceIntent, provenance, estimatedDurationMs}
       + Shot spokenContentRefs / plannedDurationMs
  ↓
Future Audio planning（选择 voice、计算实际时长、生成）
  ↓
Media(type=AUDIO, shotId/purpose/content)
```

Audio 不需要重读 Work 再判断“这个人可能说什么”；只需要解析身份、选择声音和生成。字幕同样可按 Scene item sequence + Shot binding 投影；实际 start/end 在音频生成后确定。多语言只记录为 future consideration，不设计 translation table。

## 25. 推荐 Dialogue Architecture

1. Dialogue Layer 位于 Scene content 内，名称建议使用能同时覆盖 Dialogue/Narration 的 `spokenContent`。
2. Scene Development 由 Host 触发：当 Scene 的信息、冲突、命令、承诺、拒绝或叙述无法仅靠视觉清楚表达时创建；纯视觉足够时允许空数组。
3. Scene Skill 完成写作、历史 provenance、Review 和 estimated duration 后才持久化。
4. Shot Design 读取这些 item，只保存 stable refs 和 coverage intent；不复制正文。
5. Shot duration 必须容纳绑定 spoken load；必要时延长、拆 Shot、跨 Shot 覆盖或把非必要文本压缩回 Scene Review，不能到 Audio 阶段才发现。
6. Java 使用现有 Scene/Shot content 持久化；Tool/MCP 不变。
7. Future Audio/Subtitle 是 consumer；Asset 是可选身份增强，不是前置依赖。

明确不需要 Dialogue 的情况：纯环境建立、视觉上自明的动作/反应/沉默、战斗机制、无语言的地理转场，以及 Host 判断对白只会重复画面信息的 Shot。

## 26. Recommended Minimal Schema

以下是 content convention，不是本批实现，也不是新 Entity：

```json
{
  "scene.content": {
    "speakerRegistry": [
      {
        "speakerKey": "work-scoped-stable-key",
        "displayName": "角色显示名"
      }
    ],
    "spokenContent": [
      {
        "id": "scene-local-stable-item-id",
        "kind": "DIALOGUE_OR_NARRATION",
        "speakerKey": "work-scoped-stable-key",
        "text": "经过 Review 的正式文本",
        "intent": "这句话在当前 Scene 中完成什么行动",
        "mustKeep": true,
        "performanceIntent": "简洁、provider-agnostic 的表演方向",
        "provenance": {
          "relation": "QUOTE_OR_ADAPTATION_OR_DRAMATIZATION_OR_FUNCTIONAL",
          "evidenceRefs": ["existing evidence/source reference"]
        },
        "estimatedDurationMs": 2400
      }
    ]
  },
  "shot.content": {
    "spokenContentRefs": ["scene-local-stable-item-id"],
    "plannedDurationMs": 5000
  }
}
```

说明：

- 数组顺序即 sequence，核心 schema 不再重复 `sequence`；若未来需局部排序再增加。
- `speakerRegistry` 可迁到 Work content 以支持跨 Scene 一致性；D1 可选择最小落点，但 `speakerKey` 必须 work-scoped。`assetId` 是 OPTIONAL LATER。
- `sourceExcerpt/exactLocator` 是声称直接引语时的条件必需证据，可放在 provenance 内；非 quote 不强制复制原文。
- `mustKeep` 是短剧压缩/Shot 重排所需的最小保留信号。

OPTIONAL LATER：assetId、language/locale、实际 audioMediaId、actualDurationMs、subtitle timecodes、voiceId、lipSync、translation variants。它们不得进入 D1 核心。

## 27. 推荐完整数据流

```text
Historical Evidence / Research Context
  └─ Host reasoning + Historical Research Skill
       ↓ evidence refs / boundaries
Work.content historicalSpine                         [Java persistence]
       ↓
Script.content adaptation + dialogue strategy        [Script Skill + Java]
       ↓
Episode.content dramatic job                         [Episode Skill + Java]
       ↓
Scene.content action + spokenContent[]                [Scene Skill write/review + Java]
       ↓ estimatedDurationMs
Shot.content coverage + spokenContentRefs[]           [Shot Skill + Java]
       ↓ duration feasibility gate
Visual Production                                    [Provider consumes visual plan]
       ↓
Future Audio Production                              [Provider consumes Dialogue; no rewrite]
       ↓ actual duration / Audio Media
Subtitle projection / AV sync                        [future consumer]
```

Host 决定是否需要 Dialogue/Narration；Skill 负责创作方法与 Review；Java 只持久化；Provider 只消费。

## 28. D1 修改影响面

| 面 | 判定 | 最小影响 |
|---|---|---|
| Java | NOT_REQUIRED | 保持开放 content；只做回归验证 |
| Plugin Contract | NOT_REQUIRED | Scene/Shot content 已是 object |
| Tool | NOT_REQUIRED | 复用 scene/shot get/create/save |
| MCP | NOT_REQUIRED | generic registry projection 已足够 |
| Scene Skill | REQUIRED | spokenContent 产生、provenance、Review、空对白合法 |
| Shot Skill | REQUIRED | refs、不得改写、numeric duration feasibility |
| Script Skill | MAYBE | 明确 strategy 与正文边界/voice principles |
| Shot Production Skill | REQUIRED | 消费 refs，视觉与未来音频职责分离 |
| Historical Research Skill | MAYBE | 明确 direct quote evidence gate |
| Tests | REQUIRED | schema convention、Skill text、E2E no-new-tool/no-new-table |
| Existing Work/Script | NOT_REQUIRED | 不改 |
| Existing Episode | NOT_REQUIRED | 不改 |
| Existing Scene/Shot | NOT_REQUIRED for D1 | D2 才 backfill |
| Production checkpoint/ledger/media | NOT_REQUIRED / FROZEN | resume node 不变 |

## 29. Batch 6.D1 Minimal Implementation Plan

1. 冻结最小 content convention：Scene `spokenContent[]`、work-scoped `speakerKey`、Shot refs、numeric planned duration、provenance 规则；明确 direct quote 的条件证据。
2. 加固 Scene Development planning/review/persist：允许无对白；需要时必须产生 exact text、speaker、intent、performance、provenance、estimate。
3. 加固 Shot Design：读取而不改写；只对承载项绑定；做 spoken-load vs planned duration gate；支持 reaction/voice-over/跨 Shot coverage。
4. 加固 Shot Production：视觉阶段不代写；未来 audio 路径只消费；禁止把环境声等塞回 Dialogue。
5. 补最小 tests/fixtures：有对白、无对白、旁白、直接引语无证据 FAIL、改写、双人长对白 5 秒冲突、同一句跨反应镜头、缺 Asset 仍可 Dialogue。
6. 运行静态 Contract/Tool 数量/SQL 七表回归，证明 0 new Tool、0 new table；停止，不 backfill、不生成媒体。

## 30. Batch 6.D2 当前作品 Backfill 计划

1. 冻结当前 checkpoint、credit ledger、Media 和 resume node；不覆盖已有视频。
2. Host 读取 Work/Script/Episode/6 Scenes/27 Shots，逐 Scene 判定 visual-only、Dialogue、Narration 或混合。
3. 只为确认存在 gap 的单元补 spokenContent；优先 1-03、2-01/02/03、6-02，其他 conditional 项逐一判断，不能给所有 Shot 自动塞台词。
4. 对每项完成历史 provenance 与 direct-quote gate；不正式写成史料原话，除非有原文证据。
5. Scene Dialogue Review PASS 后估时；Shot Design 绑定 refs 并检查 duration。
6. 已完成 1-01/1-02 保持不变；未完成 Shot 若受 duration 影响，仅更新 future plan，不修改 checkpoint 事实。
7. 输出 backfill matrix：no-gap、audio-only、visual revision candidates；再由后续批次决定是否恢复生产。

## 31. 风险与暂缓事项

- 开放 content 的可发现性依赖 Skill convention；D1 测试必须防止字段名漂移。
- Scene full replacement 修订时，spoken item ID 必须稳定，否则 Shot refs 会断。
- speakerKey 需要一个 work-scoped 生成/复用规则，但不应升级为 Character Entity。
- 同一台词跨多个 Shot 时，Audio item 只能生成一次；Shot refs 表示 coverage，不表示复制音频。
- 当前 5 秒生产策略对 spoken shots 风险高；在 D2 之前不应继续批量消耗 credits 生产这些镜头。
- direct quote 的 evidence excerpt 如何从外部 Research 持久化，是 D1 需冻结的条件结构；当前不新增 Research 表。
- 多语言、配音 casting、真实 TTS duration、字幕 timecode、mix/lip-sync 全部暂缓。
- 当前 Java 七表实现源码未包含在本地审计材料；D1 实施前应只读确认正式 Java 确实透明保存 content，若一致则仍不改 Java。

## 32. 最终结论

Dialogue Layer 是必需的，但不需要一个新 Domain。当前最小且符合 Host-driven、精简与跨平台原则的答案是：

```text
Scene owns reviewed spoken content.
Shot binds, covers, and times it without rewriting it.
Java persists existing Scene/Shot content.
Audio and subtitles consume it.
Historical quotes require explicit evidence.
Visual spend follows dialogue-duration feasibility when speech exists.
```

“Scene Dialogue + Shot Binding”假设验证为 **FIT**。独立 Dialogue Entity、数据库表、Tool 和 Skill 在当前需求下都不是必要条件。D1 应先通过现有 Scene/Shot Skill 与 content 建立正式、可追溯、可估时的最小层；D2 再对 6.0R-E2E 只补真实缺口。

本批约束结果：

```text
COMFY_PAID_GENERATION = 0
CREDIT_CONSUMPTION = 0
CODE_CHANGED = NO
PRODUCTION_DATA_CHANGED = NO
REPORT_ADDED = YES
PRODUCTION_CHECKPOINT_CHANGED = NO
RESUME_NODE_CHANGED = NO
```
