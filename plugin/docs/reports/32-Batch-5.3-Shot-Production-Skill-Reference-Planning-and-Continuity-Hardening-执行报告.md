# Batch 5.3 — Shot Production Skill: Reference Planning & Continuity Hardening

## 1. Executive Summary

本批将 Batch 5.2R 暴露出的真实生产经验沉淀进 `shot-production` Skill Core。修改集中在 Reference Planning、Sequence Continuity、Shot Delta Compilation、Per-Shot Review、Targeted Revise、Cross-Shot Review 以及 Identity Annotation 顺序。

实现保持精简：`SKILL.md` 只保留执行骨架，详细规则放入一个单层 reference；使用现有 pytest 体系增加一个离线 fixture 和对应断言。没有新增 Continuity/Planning/Prompt Framework、运行时服务、Tool、DTO、数据库结构或 Provider abstraction。

本批没有调用视觉 Provider，没有执行 OAuth，没有生成图片，也没有重新运行或修复 Batch 5.2R Shot A。Drama Plugin 业务源码、Drama MCP、Java、数据库、Provider Adapter 与 Host metadata 均未修改。

验证结果：Skill quick validation PASS；插件完整测试 `84 passed`。

## 2. Batch 5.2R Findings

本批只吸收以下已验证事实：

1. `Stable Asset → Stable Media → resolve → Provider input` 已真实成立，不再质疑 Reference handoff。
2. Shot 5-2-04 的“只暖手不饮”两次均被生成成饮碗语义，且 revise 后过肩构图漂移，说明文学语义和 `shotType` 必须编译为可见证据、禁止结果与构图约束。
3. Shot 5-2-05 首次错误为苏武仍持碗；明确要求“碗在桌上、双手空出”后 PASS，证明针对已确认错误的 Targeted Revise 有效。
4. Shot 5-2-06 首次 PASS，说明简单 Shot 不应进入预防性 revise 循环。
5. 两个双人 Shot 实际只使用李陵与 Scene Reference；若苏武清晰可见但没有 Character Master，Reference Plan 必须显式报告缺失，不能声称计划完整。

## 3. Before / After Skill Behavior

| Capability | Before | After |
|---|---|---|
| Reference Planning | 仅规定最多 3 个稳定 Media；无候选发现和缺失状态 | 从可见人物、Scene、focal prop、costume 等稳定实体发现候选；记录 selected/omitted/missing/rationale；固定上限 3 |
| Sequence Continuity | 缺失 | 同一连续 Scene 建立共享 Stable Facts，并区分 Locked、Allowed Delta、Shot-specific Delta |
| Shot Delta | 直接依赖业务 prompt；无正式编译规则 | 编译 Action、Composition、Static Camera Intent、Required Evidence、Forbidden Outcome |
| Per-Shot Review | 只检查文件、主体、Reference 影响和一般目标 | Shot Semantic Accuracy 成为硬门禁，并检查身份、年龄、发须、服装、Scene、Lighting、Prop、Composition、结构与历史合理性 |
| Revise | 最多一次，可改 prompt 或 reference selection | 仅在真实 FAIL 后进行一次 targeted revise；默认保持 Stable Facts 与 Reference Plan，不改已 PASS Shot |
| Cross-Shot Review | 缺失 | 仅比较 Per-Shot PASS 结果；检查 Locked Facts，允许合法 Delta；两个以上 Shot 需重生成时停止并返回 replan 状态 |
| Annotation | 未在 Core 中明确顺序 | 固定为 Visual Content Review PASS 后、Media import 前；Annotation 不等于 Provider quality |

## 4. Reference Planning Rules

Candidate 只来自具有稳定 Asset 身份和合适稳定 Media 的当前 Shot/Scene 视觉实体：

1. 清晰可见、需要身份连续的命名主要人物；
2. Shot 叙事焦点且外观需稳定的 unique prop；
3. 对空间连续性重要的 Scene/location；
4. 独立 active costume variant；
5. 其他次要稳定视觉对象。

固定规则：

```text
MAX_REFERENCE_COUNT = 3
```

- Candidate 不超过 3：使用所有适用稳定 Candidate。
- Candidate 超过 3：按主要人物 → focal prop → Scene → costume → secondary object，并结合 Shot focality 选择 3 个。
- 不建立数值评分系统，不扩大上限。
- 不为了用满 3 个而加入无关 Reference。
- 输出 selected references、omitted candidates、missing stable references、selection rationale、count 和 completeness。
- 关键可见人物缺稳定身份时返回 `MISSING_STABLE_REFERENCE` 并停止视觉执行；不静默忽略、不拿临时图片替代、不在 Shot production 内自动生成未审查 Master。

现有 Asset/Media/Shot/Scene Tool contract 能提供所需的稳定 envelope、content、reference media 与 Shot/Scene 内容。补齐缺失 Master 属于既有 asset-resolution 能力边界，不复制到 shot-production。

```text
TOOL_CONTRACT_GAP = NO
```

## 5. Sequence Continuity

共享 Sequence Context 只存在于 Agent Run Context，不新增持久化模型。

### Locked

- Character identity、age、face、hair、beard、general appearance
- base costume、color、material、major silhouette、active variant
- Scene identity、spatial structure、historical material、major fixed objects
- time of day、major light source、warm/cool relationship、exposure、atmosphere
- continuity-significant prop identity、ownership 与无剧情依据时的状态

### Allowed Delta

- 姿态、视线、表情、身体方向
- 自然衣褶
- 不同机位和景别导致的背景可见区域与信息量变化

### Shot-specific Delta

- 当前 Shot 明确要求的动作、构图、视线、camera intent 与 prop state transition

### Prop State Transition

Shot A 的“苏武手持碗”与 Shot B 的“碗已放在桌上、苏武双手空出”构成有剧情依据的合法状态变化，不是 continuity drift。Generated output 只作为 Review evidence，不能把偶然生成的帽子、道具或服装变化提升为 Domain Truth。

## 6. Shot Delta Compilation

稳定逻辑顺序：

```text
Stable Identity
+ Stable Environment
+ Current Action State
+ Composition Constraint
+ Representative Static Camera Intent
+ Required Visual Evidence
+ Forbidden Visual Outcome
+ Continuity Constraints
```

5-2-04 离线案例：

| Source semantics | Compiled constraint |
|---|---|
| 只暖手 | 双手包住碗壁；姿态明确借热度取暖 |
| 不饮 | 碗口低于下唇；碗与嘴之间有清晰可见距离 |
| Forbidden | 嘴唇接触碗沿、碗遮嘴、头部向碗做饮用动作、吞咽或喝水姿态 |
| 双人过肩 | 前景出现李陵肩部或局部背影；苏武为清晰主体；建立明确 camera relationship |
| Composition Forbidden | 不得退化为完全正面并排双人构图 |

Camera motion 在静态 key image 中转译为代表性构图：缓推取更紧的终点构图；上摇保留 focal object 与人物关系或选择运动终点；拉焦建立前后景与注意中心。不要求单图表现时间运动。

## 7. Test Results

| Test | Offline assertion | Result |
|---|---|---|
| 1 | 双人 Shot + Scene 识别李陵、苏武、穹庐，count = 3 | PASS |
| 2 | 苏武缺稳定 Character Master 时显式 `MISSING_STABLE_REFERENCE` | PASS |
| 3 | 4 Candidates 只选 3，并输出 omitted 与 rationale | PASS |
| 4 | “只暖手不饮”产生 Required Evidence 与 Forbidden Outcome | PASS |
| 5 | 双人过肩要求 shoulder/back foreground，并禁止正面并排 | PASS |
| 6 | 手持碗 → 放桌上被识别为合法 Prop State Transition | PASS |
| 7 | 缓推/上摇/拉焦编译为 static key-image intent | PASS |
| 8 | Cross-Shot Review 区分 Locked Facts 与 Allowed Delta | PASS |
| 9 | Identity Annotation 位于 Visual Content Review PASS 之后 | PASS |

额外回放断言：Shot C ReferenceCount = 2，未加入 padding reference，PASS。

执行证据：

```text
quick_validate.py = Skill is valid!
plugin/tests = 84 passed
git diff --check = PASS
```

## 8. Batch 5.2R Offline Replay

未调用 Provider，仅使用 31 号报告事实与离线 fixture。

### Shot A — 5-2-04

如果李陵、苏武、穹庐三项 stable reference 均存在：选择三项，count = 3。当前已知稳定资产只有李陵 Character Master 与穹庐 Scene Master；苏武缺失，因此计划为：

```text
selected = 李陵 Character Master, 苏武穹庐 Scene Master
missing = 苏武
status = MISSING_STABLE_REFERENCE
```

新 Shot Delta 明确包含暖手的正向证据、不饮的可测空间关系、饮用姿态禁止项，以及过肩构图的 foreground/camera relationship 和禁止退化结果。

### Shot B — 5-2-05

候选为李陵、苏武、汉节、Scene，共 4 个。全都稳定时按人物身份与 Shot focality 选择李陵 + 苏武 + 汉节，省略 Scene，并记录上限导致的理由。当前汉节无稳定 Reference 时不临时创建图片；只使用合法稳定 Candidate。当前苏武仍缺稳定 Character Master，因此 Reference Plan 不可静默标为完整。

Prop Delta 将“碗在桌上、苏武双手空出”视为上一 Shot 之后的合法状态转移，也是 Per-Shot semantic gate。

### Shot C — 5-2-06

候选与选择均为李陵 Character Master + 穹庐 Scene Master：

```text
ReferenceCount = 2
padding reference = NONE
```

正面近景和反问语义简单时，首次 Review PASS 即结束，不进行预防性 revise。

## 9. Changed Files

- `plugin/skills/shot-production/SKILL.md`
- `plugin/skills/shot-production/skill.yaml`
- `plugin/skills/shot-production/references/production-rules.md`
- `plugin/skills/shot-production/references/visual-provider.md`
- `plugin/tests/fixtures/shot-production-batch5-3.yaml`
- `plugin/tests/test_skills.py`
- `plugin/docs/reports/32-Batch-5.3-Shot-Production-Skill-Reference-Planning-and-Continuity-Hardening-执行报告.md`

`plugin/skills/shot-production/agents/openai.yaml` 未修改。

## 10. Scope Control

```text
Visual Provider called = NO
Provider generation = 0
OAuth work = NO

New Framework = NO
New runtime service = NO
New Tool = NO
New persistence schema = NO

Drama Plugin business source = UNCHANGED
Drama MCP = UNCHANGED
Java = UNCHANGED
Database = UNCHANGED
Provider Adapter = UNCHANGED
Codex config = UNCHANGED
```

## 11. Unified Acceptance Fields

```text
SHOT_PRODUCTION_SKILL_FOUND = PASS

REFERENCE_PLANNING_RULES = PASS
REFERENCE_MAX_COUNT_FIXED_3 = PASS
VISIBLE_CHARACTER_DISCOVERY = PASS
MISSING_STABLE_REFERENCE_HANDLING = PASS
REFERENCE_OVERFLOW_SELECTION = PASS

SEQUENCE_CONTINUITY_RULES = PASS
LOCKED_FACTS_DEFINED = PASS
ALLOWED_DELTA_DEFINED = PASS
SHOT_SPECIFIC_DELTA_DEFINED = PASS
PROP_STATE_TRANSITION_HANDLING = PASS

SHOT_DELTA_COMPILATION = PASS
NEGATIVE_SEMANTIC_VISUALIZATION = PASS
COMPOSITION_CONSTRAINT_COMPILATION = PASS
STATIC_CAMERA_INTENT_COMPILATION = PASS

PER_SHOT_REVIEW_RULES = PASS
SHOT_SEMANTIC_REVIEW = PASS
TARGETED_REVISE_RULES = PASS

CROSS_SHOT_REVIEW_RULES = PASS
CHARACTER_CONTINUITY_RULES = PASS
COSTUME_CONTINUITY_RULES = PASS
SCENE_CONTINUITY_RULES = PASS
LIGHTING_CONTINUITY_RULES = PASS
PROP_CONTINUITY_RULES = PASS

IDENTITY_ANNOTATION_ORDER = PASS

SHOT_A_OFFLINE_REFERENCE_PLAN = PASS
SHOT_A_OFFLINE_DELTA_COMPILATION = PASS
SHOT_B_REFERENCE_OVERFLOW_CASE = PASS
SHOT_C_NO_REFERENCE_PADDING = PASS

HOST_INDEPENDENT_SKILL_CORE = PASS
TOOL_CONTRACT_UNCHANGED = YES
NEW_FRAMEWORK_INTRODUCED = NO
NEW_RUNTIME_SERVICE_INTRODUCED = NO
NEW_DATABASE_STRUCTURE = NO

COMFY_CLOUD_CALLED = NO
PROVIDER_GENERATION_COUNT = 0
OAUTH_WORK_PERFORMED = NO

DRAMA_PLUGIN_BUSINESS_SOURCE_CHANGED = NO
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO
PROVIDER_ADAPTER_CHANGED = NO

SKILL_TESTS = PASS

BATCH_5_3 = PASS
NEXT_BATCH_READY = YES
```

完成边界：停止于 Skill Core、offline fixture/test 与报告；未生成 Shot A、未创建苏武 Character Master 或汉节 Reference，也未开始 Batch 5.4。
