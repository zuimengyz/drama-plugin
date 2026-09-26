# Literary Cinema R3A — Conflict & Authority Reconciliation

> 审计日期：2026-09-26。源码基线：`bb83843074ae685a5fdd53ed94b1a27bd863a014`。范围：NON_RUNTIME / NO SCREENPLAY REWRITE / NO MEDIA GENERATION。本文的未来设计建议不是已实施能力，也不是剧本批准。

裁决：优先修复现有 Scene Dramaturgy → DPD → Director Performance 的交接、信息释放审阅和逐句绑定。没有证据支持先新增大型 Adaptation / Actor Director Skill。本轮的 owner resolution 是架构设计输入，不表示已修复 runtime、已批准新剧本或已完成表演实证。

## 1. C1–C8 same-scope 裁决

| 冲突 | 当前证据 / 风险 | 唯一事实 owner 与交接裁决 | 不允许的修复 |
|---|---|---|---|
| C1 CinemaTranslation vs Screenplay | CinemaExpression 已有心理外化/choice-action-consequence；具体场景还需写作 | literary-adaptation 批准改变；cinema 给 source-bound 可拍表达方案；Screenplay/Scene 把获准方案写成事件过程。冲突先回对应 adaptation decision | cinema/Director各写一版实际事件，或 Performance 把心理词自行变新情节 |
| C2 Screenplay vs Director | Scene skill拥有过程，Director已有rhythm/coordination | 场内剧情 beat 次序由 Scene/Screenplay；Director解释呈现重点/节奏。重排导致因果、知识、台词依赖变化须回源审阅 | Director 用表演计划静默重排故事 |
| C3 Director vs Performance | 本地 DPD 是 objective/tactic/subtext 唯一心理来源；Performance facet身体化 | DPD解释源人物任务；Director规定观众体验/表演尺度与关系压力重点；Performance/Voice体现，Blocking/Action各管路径/力学 | Director 再造 actor objective，或多个 owner 同时编辑最终动作事实 |
| C4 Dialogue Intent vs Director | R2 要求 canonical line intent == LineDPD dramatic_action | Dialogue/Screenplay 拥有文字与源言语行动；DPD绑定/解释该行动；Director引用，不另写相反 intention | 为“演得更好”改对白意义，或误把 delivery 当文学修辞许可 |
| C5 Scene vs Editorial | Scene有信息/策略；Editorial有cut/hold/visual information | Story跨场、Scene场内决定剧情信息依赖和观众揭示意图；Editorial在这些约束内决定具体呈现/剪切时点。内容级提前/延后回上游 | 剪辑删听者反应使策略无因，或凭 cut 改知情先后 |
| C6 Adaptation vs Preservation | REORDER明确存在；protected/许可与review在上游 | Preservation是批准的限制；Adaptation可在许可内重组，冲突由其上游修订与批准解决；Story/Scene执行 | 把原著顺序绝对化；或以“电影自由”改掉关键人物逻辑 |
| C7 Character Embodiment vs Performance | Character包身体倾向与current-beat实现分离 | Embodiment稳定/阶段性倾向；DPD当前心理；Performance当前身体实现，动作路径/力学仍各归原主 | 用长期习惯自动补每场动作，或每场重写人物稳定身份 |
| C8 Prompt Generator | Seedance缺批准动作/载体会UNRESOLVED；当前戏剧链薄弱会下传 | Prompt只翻译经批准IR；发现缺义务回 owner。Scene/DPD负责解决演员为何/对谁/期待何回应 | Prompt补目标、失败、listener反应、台词或新镜头 |

依据：[authority map](/Users/zy/historical-plugin/drama-plugin/docs/external-research/literary-cinema-r3a/Literary-Cinema-R3A-Current-Authority-Map.md)、[Director](/Users/zy/historical-plugin/drama-plugin/plugin/skills/director/SKILL.md)、[DPD](/Users/zy/historical-plugin/drama-plugin/plugin/skills/dramatic-performance-direction/SKILL.md)、[Scene](/Users/zy/historical-plugin/drama-plugin/plugin/skills/scene-development/SKILL.md)、[Editorial](/Users/zy/historical-plugin/drama-plugin/plugin/skills/editorial-design/SKILL.md)。

本次裁决后未留下“同一范围同一最终事实由两人各自决定”的建议：UNRESOLVED_SAME_SCOPE_AUTHORITY_CONFLICTS = 0。尚未实施的绑定/coverage/语义审阅缺口保留，不能用这个 0 掩盖工程工作。

## 2. Required Final Findings — QF1–QF10

**QF1 当前是否缺少 Literary-to-Cinematic Adaptation？**  
不是从零缺失。源锚点、Preservation、改编许可/决策、compression mapping、CinemaExpression、ScreenplayInput、Scene作者规范及知识时序已存在。缺的是把版本选择落实到场内行动—回应—策略变化及信息释放的细粒度证明；主要断在 Cinema/Story 的场景级映射到 Scene过程、再到R2 actor beat的衔接。艺术判断执行不足与Contract粒度不足并存。

**QF2 谁拥有 Adaptation Freedom？**  
现有 literary-adaptation 在批准 Preservation/许可内拥有变更边界；Story/Script/Scene 分层执行。改变保护事实须回上游批准，Director 不拥有单方面豁免。

**QF3 谁拥有 Scene / Beat Dramaturgy？**  
现有 scene-development / screenplay incubation 的 Scene author；跨场结构归 Story/Script。Beat是Scene过程单位，DPD解释角色当前任务，不另建独立剧情owner。

**QF4 谁拥有 Information Release Timing？**  
跨场由 Story/Script，场内由 Scene。Dialogue兑现获准信息为精确台词；Director确定观众体验和重点；Editorial在上游约束内实现切换/持留时点。若改变因果、知识获得或Scene过程，必须回上游。

**QF5 新 Adaptation Contract / Thesis 还是复用？**  
先复用已存在 AdaptationContract、Story/Dramatic Bible版本选择、cinematicIntent和source mappings。当前本片已有具体关系/体验路线，不能再建第二 Canon。R3B 仅在证明无法追踪变更/保留/戏剧功能时，增加最小facet或review要求；不在R3A冻结最终schema。

**QF6 当前 Director 有 Directorial Performance 吗？**  
有正式合同、校验及Book消费者，不只是 Vision。没有证据证明当前R2候选已接成当前版本全覆盖；也没有观众/演员实测。缺交接、精确turn绑定风险与密度/interaction粒度，不能用“有类名”冒称当前作品成功。

**QF7 每句 Director Direction 谁生产、存储、批准、消费？**  
Scene/Dialogue提供精确源turn；DPD owner生成其单源任务解释；Director生成/审阅引用该DPD的表演意图；Performance/Voice生成各自实现。候选继续使用版本化文件sidecar，正式阶段复用已有Director artifact store/Production Book引用，不引入新Storage/业务实体。专业审阅不替代screenplay adoption或用户生产批准；当前源枚举/指纹/逐句投影通过后供Performance、Voice、Blocking协同和cinematic assembly消费。缺目标回DPD/Scene，不从Prompt补。

**QF8 Listener Reaction / Silence 是否一等语义？**  
需要在现有结构内成为可独立追踪的任务/刺激/回应/后果，现有SILENCE/REACTION通道、partner DPD、silent/interaction coverage已经有基础。补粒度与因果角色，不另建Listener/Silence Canon，也不把每个标点句都强制升级为dramatic beat。

**QF9 Actor Objective / Playable Action 属哪层？**  
目标和基本行为事实源于Screenplay/Scene；DPD唯一解释objective/tactic/subtext；Director选择观众感受与表达尺度；Performance体现为可观察身体/反应，Voice体现说话，Blocking/Action提供空间/力学。若“playable action”指心理策略归DPD，指身体行为归已批准源和实现部门，必须区别用词。

**QF10 R3B 最小 Runtime surface？**  
见下一节。先补交接与检查，不修改Provider/MCP/Service/Storage，不授权新剧本或生成。

## 3. R3B 候选最小改动面（未实施）

| 优先级 / surface | 最小设计问题 | 复用对象 / 不扩张范围 |
|---|---|---|
| P0 Scene working sets / source-bound handoff | 重要Scene行动→回应→策略/关系变化；重要信息出现相对过程的位置；区分源beat与actor beat | SceneBeatBible、incubation working sets/checker；先决定哪些须typed，避免新顶级skill |
| P0 screenplay_playability / DPD交接 | 载体出现不等于时序正确；reaction是前因还是后果；保留精确台词与源目标 | 现有Beat/Line witness、DPD refs；不让mapper创造行为 |
| P0 formal_performance / performance_coverage / preproduction | coverage行与确切turn/speaker/target一致；重要交互枚举不能仅每场一项 | 现有source witness和Book Gate；补错绑/漏反应反例 |
| P1 Director intent / Performance projection | 当前版本的源/DPD指纹交接；STANDARD/EXPANDED依据；共享约束+局部差异 | 现有DirectorPerformanceIntent、sidecar、artifact store；无第二心理合同 |
| P1 creative_source review / adaptation mapping | 变更理由、保护事实证明、授权owner、戏剧收益可回放 | 现有AdaptationDecision/StageReview，先审最小facet必要性，非重造Contract |
| P1 professional review & fixtures | 分轴审阅、正文冷读证据、已存在规则真正影响adoption | 现有review/findings；测试只验证可机检错误，不用字符串PASS代表艺术成功 |

R3B 首先应验证静态提出的同场turn错绑风险，再设计修改；R3A没有复现完整生产绕过。未来若要增加schema字段，需说明现有字段为什么无法表达，不能把本报告所有候选维度机械设为mandatory。

## 4. 三个未来 Gate 的需求裁决

- **Adaptation Freedom**：改动、电影必要性、保留事实、授权owner、戏剧功能必须可追踪；对应当前 source/decision/review。原著顺序不是自动保护项。
- **Dramaturgy**：重要Scene应证明入场状态、欲求/阻力、真实作用和回应、策略/关系变化、出场差异；非公式场景可有具体理由。正文证据与作者解释分离。
- **Dialogue Direction Coverage**：每个approved turn精确映射原文/speaker/target/DPD/Director意图/实现；覆盖密度可变，来源不可省略。listener/silence有影响后续的任务时不能漏掉。

不能只因metadata填满就过关。设计审阅也不能当媒体效果观察。

## 5. 未来 R3C 分轴评价设计

不合并成总分；每轴分别记观察、源锚点、PASS/CONCERN/UNRESOLVED及修复owner。未实施新enum或评分系统。

| 轴 | 核心观察问题 | 不足时返回 |
|---|---|---|
| Source fidelity | 人物逻辑、核心因果、思想/象征/结局及主观未知是否保留？ | Adaptation/Source owner |
| Cinematic adaptation | 重组织创造了电影体验，还是只把原文换成动作？ | Adaptation/Story |
| Scene dramatic process | 进入与退出之间经历了必要过程吗？ | Scene |
| Beat causality | 对方回应改变下一策略吗？是否需猜隐藏事件？ | Scene/DPD |
| Information release | 何时、多少、经谁、在何阻力后得知？是否过早/过迟？ | Scene/Story |
| Character agency | 各人物有自己的欲求和选择，还是主人公论证工具？ | Scene/Character |
| Dialogue action | 这句试图改变谁，期待何反应？ | Dialogue/DPD |
| Performance direction | 来源任务、导演重点与身体/声音体现一致吗？ | Director/Performance |
| Listener reaction | 听者有任务且反馈影响后续吗？ | DPD/Performance |
| Silence | 不答/等待/中断起何作用，还是填空？ | Scene/DPD |
| Rhythm | build/hold/turn/release/aftermath是否分层并累积？ | Story/Scene/Director/Editorial |
| Emotional escalation | 代价/关系变化带来压力，不是音量逐级加大吗？ | Scene/DPD/Director |
| Filmability | 空间、接触、先后、声音/身体可实现且不改语义吗？ | Blocking/Action/Performance/Shot |

先读可读正文，再看sidecar解释；条件允许时用不带作者意图的独立读者，否则明确SELF-AUDIT或部分隔离。文本审阅不能声称演员/观众实测。检查S01–S16，不能用S02修复遮盖中段结构。

## 6. Counterexample Tests — 未来设计，未运行

| 反例 | 应暴露的失败 / 预期裁决 |
|---|---|
| 语义正确但首句信息全部释放在阻力前 | literal Gate可通过；dramaturgy review标记过早，返回Scene，不要求改成特定新句 |
| 自然对白没有objective | 不能以口语顺畅PASS；要求source-bound DPD或返回Scene |
| 说话者一直行动，听者没有reaction/任务 | interaction覆盖不完整；不得自动加点头 |
| 每句有emotion label但无playable action | objective/tactic缺失；不能把更细emotion词当修复 |
| Scene有conflict字段却无人真正阻挡 | 对照正文无resistance→strategy证据；返回Scene |
| 忠于原著事件但沿用小说总结节奏拖沓 | 检查许可内展开/压缩和Scene收益；不宣布源顺序不可变 |
| 为节奏改掉source-critical人物逻辑 | Adaptation Freedom拒绝/上返授权；电影性不构成豁免 |
| Director指导越权新增关键动作 | source-bound检查失败；不能以performance解释避开源审阅 |
| Performance改正式对白 | exact-text/speaker/meaning检查失败；回Dialogue/Screenplay |
| Prompt被迫猜actor intention | explicit UNRESOLVED；禁fallback创作 |
| 同场两条合法DPD/projection交换coverage行 | 精确turn身份检查应失败；这是当前静态风险待R3B验证 |
| 所有源动作均出现，但数组反转前后/将触发当reaction | 子串命中不能PASS语义时序；要求可追踪关系 |
| listener有一个场景级方向，却漏关键拒绝后的等待 | 场级总数覆盖不能替代关键interaction覆盖 |
| 简单回应继承正确意图但没有长说明 | 应允许紧凑覆盖；不得要求固定百字/微表情 |
| 重要未回答/未完句因不完整被强补解释 | 有dramatic function则保留；不能把消歧变exposition默认 |
| 梦史原因未知，被“因果完整”规则补成唯一机制 | 违反源主观/未知保护；允许有意悬置 |
| S10–12均为受阻但代价递增 | 不能只凭重复句式判失败；检查关系/选择/不可逆性是否累积 |

## 7. 交付与停止边界

六份报告互相补充：authority map给当前事实；external forensics限定外部证据；两份gap audit给最小缺口；S02 trace定位具体过程；本报告裁决职责与下一轮设计范围。

没有修改Runtime、Skill、Contract或剧本，没有外部Skill安装，没有媒体生成/收费调用，没有开始R3B。最终文件完整性结果见 [audit-verification.json](/Users/zy/historical-plugin/drama-plugin/docs/external-research/literary-cinema-r3a/audit-verification.json)。

```text
SOURCE_FIDELITY_BOUNDARY_MAPPED = YES
ADAPTATION_FREEDOM_BOUNDARY_MAPPED = YES
ADAPTATION_THESIS_GAP_IDENTIFIED = YES
SCENE_DRAMATURGY_OWNER_RESOLVED = YES
BEAT_DRAMATURGY_OWNER_RESOLVED = YES
INFORMATION_RELEASE_OWNER_RESOLVED = YES
DIRECTORIAL_PERFORMANCE_OWNER_RESOLVED = YES
DIALOGUE_DIRECTION_COVERAGE_GAP_IDENTIFIED = YES
LISTENER_REACTION_AUDITED = YES
SILENCE_AS_BEAT_AUDITED = YES
UNRESOLVED_SAME_SCOPE_AUTHORITY_CONFLICTS = 0
RUNTIME_CHANGES = 0
SCREENPLAY_CHANGES = 0
PAID_GENERATION = 0
READY_FOR_LITERARY_CINEMA_R3B = YES
```

READY 表示已有足够架构设计输入，不表示R3B已获本轮执行授权；本轮到此停止。

