# 12-创作型 Skill 生命周期基线加固执行报告

执行日期：2026-08-14（Asia/Shanghai）  
执行批次：Creative Skill 加固 Batch 1  
执行仓库：`drama-plugin`

## 1. 执行摘要

本批已为 `work-creation`、`script-adaptation`、`episode-development`、`scene-development`、`shot-design` 五个核心创作 Skill 建立统一、轻量、平台无关的 Creative Lifecycle：

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

统一的是 Agent 工作纪律；五个 Skill 的 Context、Plan 内容和 Critical Review Checks 仍然分别面向 Work、Script、Episode、Scene、Shot。每个 Skill 明确：Context 不足时先通过已有 get/list/search/context 能力补齐；无法补齐则报告阻塞；Plan 和工作笔记不进入长期 Domain Content；完整 Draft 必须先 Review；Review FAIL 禁止持久化；修订后必须再次 Review；只有 Review PASS 才能 create/save。

本批没有增加 references、Tool、MCP 逻辑、Java Contract、ContextBuilder、Harness、Workflow 或状态机。五个 `SKILL.md` 均为 44 行，符合 Batch 1“生命周期优先、领域深度后置”的精简目标。

验证结果：Drama Plugin 65 tests passed；Skill tests 14 passed；mypy 34 个源码文件无问题；8 个 Skill 格式校验全部通过；Drama MCP Service 13 tests passed；Tool Registry 仍为 44 个，合同快照 SHA-256 未变化。

## 2. 执行依据

本批完整复核并以 `docs/reports/11-创作型Skill正式化审计与设计报告.md` 为设计依据。该报告确认：

```text
PLAN_CAPABILITY = PARTIAL
EXECUTE_CAPABILITY = PARTIAL
REVIEW_CAPABILITY = PARTIAL
REVISE_CAPABILITY = MISSING
PERSIST_GATE = PARTIAL

TOOL_CONTRACT_CHANGE_REQUIRED = NO
JAVA_CONTRACT_CHANGE_REQUIRED = NO
```

执行前重新读取了当前五个 `SKILL.md`、五个 `skill.yaml`、`tests/test_skills.py`、Skill/Tool registry、Context 边界、MCP 动态适配与 Java 长期记忆边界。当前目录映射与审计报告一致，没有发生 Skill 重命名或迁移。

本批同时遵循 `skill-creator` 的精简与渐进披露原则：主 Skill 只保留工作方式、关键规则、Tool 策略和质量 Gate；未在 Batch 1 添加完整编剧理论或 `references/`。

## 3. 修改前状态

修改前五个 Skill 已具备：

- 平台无关 Skill Core；
- get/list/search/create/save 的正确选择；
- Stable Envelope + Domain Content；
- create 是首次正式写入，save 是已有实体的完整修订；
- 若干领域要素与两条 completion conditions。

修改前的共同缺口：

- 没有显式 Understand Goal；
- Context Tool 仅被描述为“需要时使用”，没有充分/可补齐/不可补齐三类行为；
- 没有独立 Plan 与完整 Draft 阶段；
- 没有 Review PASS/FAIL 语义；
- 没有 Review FAIL→Revise/Re-plan→Review Again；
- “complete initial formal state” 未绑定可检查的 Persist Gate；
- Plan、Review notes 与正式 Domain Content 的边界不够明确。

`tests/test_skills.py` 修改前只验证加载、平台中立、Tool 引用、create/save 语义和 Host Adapter metadata，没有 Creative Lifecycle 防回归。

## 4. 本批修改范围

### MODIFIED

```text
skills/work-creation/SKILL.md
skills/work-creation/skill.yaml
skills/script-adaptation/SKILL.md
skills/script-adaptation/skill.yaml
skills/episode-development/SKILL.md
skills/episode-development/skill.yaml
skills/scene-development/SKILL.md
skills/scene-development/skill.yaml
skills/shot-design/SKILL.md
skills/shot-design/skill.yaml
tests/test_skills.py
```

### ADDED

```text
docs/reports/12-创作型Skill生命周期基线加固执行报告.md
```

没有新增 fixture 或 references。`agents/openai.yaml` 未修改。

## 5. Work Lifecycle 修改

`work-creation` 现在要求先区分新建与修订，明确创作意图、范围、受众/格式/基调/史实约束，并拒绝把标题或事件名当作充分创作意图。

Context 阶段沿用真实 Tool 语义：已知 ID 用 `work.get_work`，自然语言身份用 `work.search_works`，结构枚举才用 `work.list_works`；证据不足时形成 focused research question 并停止 Plan/Persist。

Work Plan 基线要求记录目标、继承史实、不可违反约束、戏剧结构或状态变化、Draft 关键内容与待解决问题。Draft 不得是几行事件摘要、占位或测试内容。Review 基于现有 theme、viewpoint、relationships、central conflict、timeline、structure 以及历史/虚构边界。结构或创作目的失败时 re-plan；Review PASS 后才能写入正式 Work。

## 6. Script Lifecycle 修改

`script-adaptation` 现在先明确目标 Work、新建/修订状态、改编范围、格式/长度/受众/连续性约束。Context 使用 `work.get_work`、`script.get_script`、`script.list_scripts` 与条件性 `context.build_context`，没有新增不存在的 `script.search_scripts`。

Script Plan 基线要求声明改编目标、必须继承的 Work 事实和人物真相、不可违反约束、视听结构与推进，以及 Draft 所需主线/支线/人物弧/节奏/升级/高潮。Draft 必须可供 Script Review 和 Episode 开发，不能是剧情梗概片段。Review 检查对 Work 的忠实、主支线、人物弧、节奏、升级、高潮、短剧结构和 screenable action。

局部文字、节奏或小型连续性缺陷 local revise；主线、人物弧、总体结构、高潮或 Work fidelity 失败时 re-plan。

## 7. Episode Lifecycle 修改

`episode-development` 现在明确 Episode 不是 Script 的机械切片。开始前需明确 parent Script、集号、戏剧范围和连续性约束；通过 `script.get_script`、`episode.get_episode`、`episode.list_episodes` 获取父级、既有对象与必要邻集。

Episode Plan 基线要求声明 dramatic goal、继承的 Script/人物状态、不可违反约束、entry-to-exit change，以及 hook、conflict progression、information gain、character change、ending hook。Draft 不得是几行 synopsis 或测试字段。

Review 以现有 dramatic job、opening hook、escalating conflict、information gain、character change、ending hook 和邻集连续性为 Critical Checks，并新增 entry/exit meaningful change。dramatic job、推进或状态变化失败时 re-plan。

## 8. Scene Lifecycle 修改

`scene-development` 现在先明确 parent Episode、戏剧时刻、目标结果、地点/时间/人物/连续性约束。Context 阶段按 ID→get、父级范围→list、自然语言身份→search 获取 Scene，条件性使用 location research 和 claim verification。

Scene Plan 基线要求声明 purpose、继承的 Episode/人物事实、不可违反约束、entry-to-exit state change，以及 place/time/participants/objective/conflict/action/turn/dialogue/exit state。Draft 必须是可演行动与对白，不能是“人物+地点”、静态对话摘要或占位。

Review 检查 dramatic purpose、objective、conflict、playable action、turn、entry/exit state，并要求通过信息、关系、决定、危险或目标变化形成真实状态变化。目的、冲突、turn 或 Episode function 失败时 re-plan。

## 9. Shot Lifecycle 修改

`shot-design` 现在先明确新建 coverage 或修订、parent Scene、覆盖范围、视觉结果、时长/连续性/参考约束，并禁止把一句话或一句对白机械等同于一个 Shot。

Context 阶段使用 `scene.get_scene`、`shot.get_shot/list_shots/search_shots`，仅在已选稳定参考确实影响连续性时使用 `asset.get_asset` 或 `media.get_media`。Shot 消费已批准历史 Context，不机械重复 Research。

Shot Plan 基线要求声明 coverage goal、继承的 Scene/视觉状态、不可违反约束、visual and entry-to-exit progression，以及每个 Shot 的 dramatic function、framing、composition、blocking/action、camera behavior、duration、continuity。Draft 必须形成完整 coverage，不能机械切句或只给占位镜头标签。

Review 检查每个 Shot 的叙事功能、镜头要素、最少必要 coverage 和空间/表演/道具/服装/动作/时间连续性。单个参数问题 local revise；coverage、camera strategy、Scene progression 或跨镜连续性失败时 re-plan。

## 10. Context Gathering 基线

五个 Skill 均建立三类统一行为：

```text
A. Context sufficient
   → continue to Plan

B. Context missing but retrievable
   → known ID: get
   → known parent scope: list
   → unknown natural-language identity: search（仅存在该 Tool 的 Domain）
   → missing parent chain: context.build_context
   → then reassess before Plan

C. Critical context unavailable or contradictory
   → state the blocker
   → do not Draft
   → do not Persist
```

每个 Skill 将该规则映射到自身真实 Tool，而不是复制不存在的对称接口。`context.refresh_context` 仍只在正式写入使现有 Context 过期后使用。

## 11. Plan 基线

五个 Plan 均至少包含：

1. 当前对象目标；
2. 必须继承的上游事实/状态；
3. 不得违反的约束；
4. 当前对象要完成的结构或状态变化；
5. Draft 必须包含的领域关键内容；
6. Draft 前必须解决的问题。

Plan 明确保留在 Agent Run Context 或 temporary working state。每个 Skill 都禁止通过自身 create/save Tool 持久化 Plan。本批没有新增 Plan Tool、Java 实体或数据库表。

## 12. Execute Draft 基线

每个 Skill 先依据 Plan 形成“complete candidate formal state”，再进入 Review。Draft 与长期对象明确区分：

- Work 不能是几行事件摘要；
- Script 不能是 plot-summary fragment；
- Episode 不能是机械切片或简短 synopsis；
- Scene 不能只是人物、地点或静态对话摘要；
- Shot 不能是机械切句或占位 camera label。

五个 Skill 均明确 `Do not persist a partial draft` 或等价规则。Draft reasoning 不属于最终 Domain Content。

## 13. Review 基线

五个 Skill 均新增独立 Review 阶段，并明确：

```text
all critical checks pass
→ Review PASS

any critical check fails
→ Review FAIL
```

Critical Checks 直接建立在各 Skill 现有领域规则和 completion conditions 上，没有引入 Batch 2/3 的大型专业 rubric。Review 在任何 write 之前执行，并检查 unresolved historical/continuity conflict。

## 14. Revise / Re-plan 基线

五个 Skill 统一区分：

```text
wording / completeness / isolated pacing or continuity defect
→ local revise

core purpose / structure / dramatic change / coverage / continuity strategy failure
→ re-plan current object
```

Review FAIL 时显式禁止持久化。本批只增加 Skill instruction，没有 ReviewEngine、RevisionEngine、状态机或运行时代码。

## 15. Review Again 规则

每个 Skill 都包含硬规则：

```text
Review FAIL
→ Revise or Re-plan
→ Review complete Draft again
→ Review PASS
→ Persist Gate
```

任何 fix 都不能直接进入 create/save。自动化测试验证每个 Skill 同时包含 FAIL 阻断、local revise、re-plan 和 `Review Again and PASS` 约束。

## 16. Persist Gate

五个 Skill 的统一 Gate 为：

```text
required context sufficient
AND internal plan complete
AND complete draft exists
AND all critical checks pass
AND no unresolved historical or continuity conflict
→ may persist
```

硬规则：`No Review PASS means no create or save.`

Plan、draft reasoning、review notes、revision notes 默认留在 Agent Run Context / temporary working state，不写入 Work/Script/Episode/Scene/Shot `content`。仅 Review PASS 的正式领域结果进入 Stable Envelope + Domain Content。

## 17. Research 决策基线

本批未修改 `historical-research` Skill 或 Research 实现。五个创作 Skill 均采用：

```text
consequential decision evidence-dependent?
  ├─ no  → use approved context; do not repeat research
  └─ yes
       ├─ evidence sufficient → continue
       └─ evidence insufficient → formulate focused research question;
          stop before Plan/Persist;
          Agent or Host chooses existing research capability
```

Work/Script/Episode 使用已有 `research.verify_claim`；Scene 继续条件性使用 `research.search_locations` 和 `research.verify_claim`；Shot 没有新增 Research Tool，也不机械逐镜研究。

## 18. create/save 语义检查

原语义完整保留：

- new object + Review PASS → `create_xxx`；
- existing object + concrete reviewed revision → `save_xxx`；
- create 是正常首次正式持久化并返回稳定 ID；
- save 是已有对象的完整正式状态替换；
- 禁止 create 后无具体修订的 routine save；
- 禁止用 create/save 存 Plan、partial Draft 或 Review notes；
- Tool catalog 仍是机器 Schema 唯一真源。

原 `test_create_is_first_write_and_save_is_revision_only` 在扩展后继续通过。

## 19. skill.yaml 修改说明

五个 `skill.yaml` 的 code、name、description、required/optional context、refresh_after、preferred/allowed tools 均未变化。

每个 completion conditions 从 2 条增至 3 条。新增项仅声明：Persistence 必须在 sufficient context、internal plan、complete draft、passing domain review 且无 unresolved historical/continuity conflict 后发生。完整 Review rubric 仍保留在 `SKILL.md`，没有塞入 declarative metadata。

## 20. 测试新增

在现有 `tests/test_skills.py` 中增加 5 个测试：

1. 五个 Skill 的七阶段 Markdown 章节存在且顺序一致；
2. 每个 Skill 的 Review body 包含自身领域 Critical Checks，且五者不相同；
3. Plan/Draft/FAIL/Revise/Re-plan/Review Again/Persist Gate 形成完整约束；
4. Plan、draft reasoning、review/revision notes 不进入 Domain Content；
5. Research evidence 不足会在 Plan/Persist 前阻断，skill.yaml 含 lifecycle gate。

测试通过解析三级 Markdown 标题验证结构，再组合验证多个关键规则；没有仅依赖某一个生命周期单词，也没有实现 Markdown framework 或新增依赖。

## 21. 自动化测试结果

| 检查 | 结果 |
|---|---|
| `pytest -ra tests/test_skills.py` | 14 passed |
| Drama Plugin full pytest | 65 passed |
| mypy | Success，34 source files |
| Skill quick validation | 8/8 PASS |
| Drama MCP Service pytest | 13 passed |
| Tool Registry count | 44，未变化 |
| Tool Contract SHA-256 | `824f09a38b954b36fe1f7ced616e5ce98d10b918171d838333caec97c6ac90ca`，前后相同 |
| `git diff --check` | PASS |

当前没有真实 Agent Harness 执行完整 Creative Loop，因此没有伪造 Creative Agent E2E。

## 22. 平台无关性检查

现有平台中立测试继续通过。五个 Skill Core 没有引入：

- Codex/OpenAI 专用生命周期机制；
- MCP Server 地址或实现；
- Java Controller、DTO 或数据库表；
- ComfyUI、workflow node 或 Provider 细节；
- Skill 间固定 chaining。

`agents/openai.yaml` 未修改，仍然只是 Host Adapter interface metadata。Lifecycle 全部位于平台无关 `SKILL.md`，`skill.yaml` 只保存 declarative metadata。

## 23. 未修改范围

本批未修改：

```text
Java Service / Java Domain / MySQL / MinIO
Drama MCP Service / MCP Tool projection
Tool catalog / Tool code / Tool schema / Tool count
Media / Production / Generation / ComfyUI
Research Skill / Research implementation
ContextBuilder / Context contracts
Harness Runtime / Agent Loop
Asset Resolution / Shot Production
agents/openai.yaml
```

执行前后源码目录内容哈希保持一致：

```text
Tool implementation: e482e6cf41f5da7e6bbec08e03a4edaed118c300dcb4e776af60769ebb1c21a5
Context implementation: 9e2d1b2e799e43eb49ff4bbc13dd76b02145f09739e8bc8ff7d94afddae47548
MCP Service source: e7ef5ebe5622a929bf2e8685c50769bd7fa6d4e60b965d6adf5119e3d3892108
Java source: 57be5e02591cb8a1c2d6e2743ea5e639121a91fb19bf50baa331b3f545ba26bb
```

Java 仓库已有的 `server/src/main/resources/application.yml` 工作区配置改动，以及两个既有 `.DS_Store`，均未触碰。

## 24. 已知不足

本批只建立工作纪律，不代表五个 Skill 已达到生产级：

- Work premise、人物目标/需求、人物弧和完整历史虚构边界仍需 Batch 2 深化；
- Script 全剧结构、分集设计、信息揭示和可演文本标准仍需 Batch 2 深化；
- Episode 单集必要性与节奏、Scene tactics/subtext/necessity、Shot 轴线/视线/生成可行性仍需 Batch 3 深化；
- 当前 Review 只是 critical baseline，不是完整领域 rubric；
- 当前测试验证 Skill Contract，不等同于模型在真实任务上的创作质量；
- 未执行真实 Harness 的 Plan→Review→Revise 行为 E2E。

因此本批不把任何核心 Skill 标记为 production-ready。

## 25. Batch 2 前置条件

进入 Batch 2 前已经具备：

- 五个 Skill 使用同一生命周期语言和阶段顺序；
- Draft 与持久化对象分离；
- Review PASS/FAIL 与 Review Again 硬规则；
- Plan/Review notes 不进入长期记忆；
- create/save、Tool、MCP、Java 边界稳定；
- 结构化防回归测试可保护后续专业内容扩展。

Batch 2 应在不改变生命周期骨架的前提下，重点深化 Work + Script 的 planning 和 domain review；如内容增大，再按 Batch 11 建议增加一层 references，不应创建通用 Workflow 或 Review Skill。

## 26. 最终验收结论

```text
WORK_LIFECYCLE_BASELINE = PASS
SCRIPT_LIFECYCLE_BASELINE = PASS
EPISODE_LIFECYCLE_BASELINE = PASS
SCENE_LIFECYCLE_BASELINE = PASS
SHOT_LIFECYCLE_BASELINE = PASS

UNDERSTAND_GOAL = PASS
CONTEXT_GATHERING = PASS
PLAN_STAGE = PASS
EXECUTE_DRAFT_STAGE = PASS
REVIEW_STAGE = PASS
REVISE_STAGE = PASS
REVIEW_AGAIN_RULE = PASS
PERSIST_GATE = PASS

NO_REVIEW_PASS_NO_PERSIST = PASS
PLAN_NOT_PERSISTED_AS_DOMAIN_CONTENT = PASS
REVIEW_NOT_PERSISTED_AS_DOMAIN_CONTENT = PASS

SKILL_PLATFORM_NEUTRAL = PASS
TOOL_CONTRACT_UNCHANGED = PASS
MCP_CONTRACT_UNCHANGED = PASS
JAVA_CONTRACT_UNCHANGED = PASS

PLAN_CAPABILITY = BASELINE_ESTABLISHED
EXECUTE_CAPABILITY = BASELINE_ESTABLISHED
REVIEW_CAPABILITY = BASELINE_ESTABLISHED
REVISE_CAPABILITY = BASELINE_ESTABLISHED
PERSIST_GATE = BASELINE_ESTABLISHED

TOOL_CONTRACT_MODIFIED = NO
MCP_SERVICE_MODIFIED = NO
JAVA_SERVICE_MODIFIED = NO

CREATIVE_AGENT_REAL_E2E = NOT_RUN

BATCH_1_RESULT = PASS
READY_FOR_BATCH_2 = YES
```

最终定位：**Creative Agent 正确工作的生命周期和持久化纪律已经建立；正式历史短剧创作所需的领域专业深度仍由 Batch 2/3 继续加固。**
