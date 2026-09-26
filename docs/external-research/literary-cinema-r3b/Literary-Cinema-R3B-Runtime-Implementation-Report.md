# Literary Cinema R3B — Runtime Implementation Report

日期：2026-09-26。基线 HEAD：`bb83843074ae685a5fdd53ed94b1a27bd863a014`。

本轮已将源场景的有序载体、作用—回应关系、信息释放审阅和 exact-turn identity 接入正式 `FormalSourceWitness → full_performance_coverage_gate → complete_production_book`。缺少新交接或证据时，正式 Book 不能通过。没有重写剧本、生成媒体或调用收费服务。测试通过只证明结构、绑定与责任闭环，不证明电影改编或表演艺术效果。

## Baseline

设计输入重新读取了 R3A 六份报告：[Authority Map](../literary-cinema-r3a/Literary-Cinema-R3A-Current-Authority-Map.md)、[External Forensics](../literary-cinema-r3a/Literary-Cinema-R3A-External-Capability-Forensics.md)、[Adaptation Gap](../literary-cinema-r3a/Literary-Cinema-R3A-Adaptation-Dramaturgy-Gap-Audit.md)、[Performance Gap](../literary-cinema-r3a/Literary-Cinema-R3A-Directorial-Performance-Gap-Audit.md)、[S02 Trace](../literary-cinema-r3a/Literary-Cinema-R3A-S02-Dramaturgy-Trace.md)、[Reconciliation](../literary-cinema-r3a/Literary-Cinema-R3A-Conflict-Authority-Reconciliation.md)。实际代码审计包括 creative_source、incubation/scene working sets、screenplay_playability、DPD、DirectorPerformanceIntent、formal performance Host、coverage、preproduction，以及 Dialogue/Blocking/Action/Editorial/Director 的合同与 owner 规则。

修改前 pytest：**2730 passed**。修改前 mypy：**40 errors / 13 files / 201 source files**。原有 R3A 报告目录与 `.DS_Store` 是开始时已有的未跟踪文件，本轮没有清理它们。没有应用外部 Skill 或新建顶级 Skill。

## Changed Runtime Files

以下路径均相对于仓库根目录。

| 文件 | 实际变更及消费者 |
|---|---|
| `plugin/src/drama_plugin/contracts/scene_dramaturgy.py`（新增） | 源载体定位、interaction/info 注释、DPD 回应解释、分轴 review、密度证据。不是第二套 Scene/Beat 实体 |
| `plugin/src/drama_plugin/scene_dramaturgy.py`（新增） | 当前源哈希、顺序、因果、知识窗口、review 与确定性 receipt 校验 |
| `plugin/src/drama_plugin/contracts/dpd.py` | 现有 BeatDPD 嵌套 response_interpretations；空值保持旧序列化 |
| `plugin/src/drama_plugin/contracts/screenplay_playability.py` | Beat witness 增加源 action/reaction carrier refs |
| `plugin/src/drama_plugin/screenplay_playability.py` | ordered carrier 校验、exact-turn 校验/指纹、mapper dramaturgy receipt 与 readyForDirection |
| `plugin/src/drama_plugin/contracts/performance_direction.py` | Director 当前 dramaturgy/turn 指纹及 projection turn 指纹 |
| `plugin/src/drama_plugin/performance_direction.py` | 源 turn → DPD → Director → VISUAL/VOICE 的联合身份检查 |
| `plugin/src/drama_plugin/hosts/formal_performance.py` | 从可信源枚举每个关键 interaction/silence，逐行匹配源 turn/实际 listener response，要求所有 Scene reviews |
| `plugin/src/drama_plugin/performance_coverage.py` | 新 receipt 决定 readiness；按 finding 路由 repair owner；STANDARD 共享表达与密度证据 |
| `plugin/src/drama_plugin/preproduction.py` | 正式 Book 消费以上 gates；全量 DPD scope、当前 Director/projection、review/self-review 指纹约束 |
| `plugin/src/drama_plugin/contracts/creative_source.py` | StageReview 增加 preservation_checks，未改变 AdaptationDecision owner |
| `plugin/src/drama_plugin/creative_source.py` | 新改编编译要求保护事实 receipt；历史完整性 replay 与新批准分离 |
| `plugin/src/drama_plugin/professional.py` | 既有 scene-development 的 Scene Beat Bible 允许 typed dramaturgy facet；Director 不获得该字段 |

新增测试模块：`r3b_helpers.py`、`r3b_screenplay_diagnostics.py`、`test_literary_cinema_r3b.py`。更新 formal_performance_helpers、literary_fixture、test_pre_r1_remediation、test_screenplay_playability、test_production_language 的合成证据/调用参数。没有修改正式 screenplay 或既有 R2 fixture 的正文/sidecar。

## Generator Architecture / Authority Boundary

本轮不修改任何 Prompt Generator。实际链为：

```text
existing Scene.content + spokenContent + screenplayAction
  → approved dramaturgy annotation / current source locators
  → BeatDPD / LineDPD + source-bound expectation and interpretation
  → dramaturgy review receipt
  → current DirectorPerformanceIntent
  → exact VISUAL / VOICE projections
  → formal coverage → Production Book readiness
```

Scene 仍拥有已发生事实、场内顺序与信息释放。DPD 仍是 objective/tactic/subtext/回应解释唯一来源。Director 只引用它们并给观众体验、尺度、节奏重点。Performance/Voice/Blocking/Action 实现批准内容。新字段不赋予 Director objective，也不赋予 Performance 对白修改权。没有改变跨场 Story/Script 或 Editorial 的权力。

## Minimal Representation Decisions

| 已有表达 | 不足 | 最小增量 | owner / consumer / validation |
|---|---|---|---|
| SceneBeatBible.causality、Scene.content、正文 | prose 无法确定同一动作实例及它和对白的交错顺序 | 嵌套 SceneDramaturgy：原始字符区间/现有 line id、文本 hash、有序角色标记；不新建 beat id | Scene → mapper/Host；源 hash、区间、台词顺序、actor/target 检查 |
| BeatPlayability.source_excerpt / ordered_actions | 两个 substring 都存在仍可倒序 | action_carrier_refs / reaction_carrier_ref | DPD source witness → ordered validator；数量、顺序、原句与角色一致 |
| BeatDPD objective/tactic/subtext | 不区分希望的回应与实际回应 | response_interpretations 指向 Scene action/response，expected、interpretation、next beat/reason | DPD → receipt；引用必须为真实 interaction，下一 beat 必须承载源下一动作 |
| knowledge/Scene information prose | 不知道首释量、接收者与选择前所需知识 | information 注释分解信息语义部分、releases、窗口、prior knowledge | Scene → 分轴 review；部件与受众集合、触发、时间窗检查 |
| Director/projection 已有 DPD refs | 同场合法 refs 仍可能绑错覆盖行 | 联合 turn fingerprint + dramaturgy fingerprint | Director/realization → Book；源 id/speaker/target/text/DPD/current hashes 同时相等 |
| coverage STANDARD/EXPANDED | 无密度依据且重复表达 | 五项风险/重要性证据及受限 shared_ref | 专业 direction → coverage；source binding、风险要求 EXPANDED |
| AdaptationDecision / StageReview | 变更理由存在，但无逐个保护项证明 | 既有 StageReview.preservation_checks | Adaptation → compiler；保护项全集、源/目标引用、审批 hash 与状态 |

Scene Beat Bible 可持有 facet；采用现有 Scene 保存流程将同一批准注释置于 `Scene.content.dramaturgy`。本轮没有自动 adoption 或新 Storage。Bible authoring 校验仅验证类型，真正源一致性在 Scene handoff 验证，不能把写入 Bible 当作 formal PASS。

## Scene Dramaturgy Handoff / Expected and Actual Response / Strategy Change

`source_body_hash` 对去掉 dramaturgy facet 的既有 Scene 求 hash，避免自指；DPD 与 review 则绑定包括 facet 的完整当前 Scene。载体直接定位 `screenplayAction` 的 `[start:end]` 或 `spoken:<canonical turn id>`。实际文本必须匹配 SHA256；action 区间不得倒序或重叠，所有对白 id 必须按源数组的完整顺序出现。mapper 不从台词猜 objective、response 或 timing。

Interaction 只引用源载体，不复制动作事实。response 必须在 action 之后，cause 必须回指该 action，listener 必须等于 action target。下一 action 必须在 response 之后并由该 response 触发，actor 保持为策略发起者。DPD expected_response 与 Scene actual response 分开；source edge 与 DPD expectation 必须一一匹配。缺 listener DPD/task、泛化 `respond`、下一策略无因果承载或解释时产生 concern。仅 tactic 字符串不同不会通过策略变更证明。

receipt 的 `causalCoverage` 保留 action、actual response、expected response、interpretation、previous/next tactic、transition reason、speaker/listener DPD refs。Review 按六个轴保留 scope、finding、reason、evidence refs、repair owner；source evidence 必须可定位，空泛 PASS/OK 理由拒绝。review subject 绑定当前 Scene 和全部 scoped DPD。SELF_AUDIT / PARTIALLY_ISOLATED_REVIEW / INDEPENDENT_REVIEW 独立记录；自审者不能自称独立读者。本轮实际证据都是显式技术 fixture 自审，不宣称 cold-read independent PASS。

## Information Release Implementation

信息 amount 由 Scene 批准的语义 parts 表示，不是 NLP 词数。每次 release 标明载体、parts、观众与角色接收者、前置 response。窗口 `not_before` 检出 DRAMATICALLY_PREMATURE；`needed_by` 按每个接收者的 prior knowledge + 当时已释放 parts 检出 DRAMATICALLY_LATE。两者都是局部诊断字符串，没有增加平台全局艺术 enum。

每个 marked information 必须有专门 review finding；信息修复 owner 固定 Scene。没有 blanket 禁止 exposition；具有上下文的直接紧急事实可以通过。S02 fixture 保持“先生……我妈妈出事了。跟我来，快！”原文，literal validation 可通过，但首次接触释放全部请求信息早于延迟聆听的诊断窗口，触发 Scene concern。该窗口来自 R3A 专业诊断，不是 runtime 自行从文本推断艺术结论。

## Exact Turn Binding / Director Version Binding

联合指纹包括完整当前 Scene（因而含其版本内容）、精确原始 turn 对象及 DPD fingerprint。`validate_exact_turn` 先验证 requested id 等于 DPD 的 spoken_content_id，再复用 exact text/hash、speaker、target、line intent 和 source validation。覆盖行必须绑定这个 DPD，而不只是同一 Scene 的任意 DPD。

Director 必须绑定 current Scene pin、当前 dramaturgy receipt、全部作用域 DPD fingerprints/beat ids、该 Scene 的完整 turn map。每条 VISUAL/VOICE projection 必须具有该 exact-turn fingerprint，并通过既有 Director、DPD 和 modality 校验。对白、target、Scene 或 DPD 变化均使旧链失效。Book 的 self_review hash 也包括新 reviews，不能更换证据后沿用原自审。

## Listener / Silence Coverage and Direction Density

Formal source 不再只为多人场景制造一条 generic interaction：每个 approved interaction 独立枚举，partner DPD 必须承载那个 response，不能以同一 listener 的另一次回应替代。重要 silence 单独定位，区分拒绝、等待、处理、打断、未完成句、无机会发言；environmental silence 不带 actor 心理。既有一般静默段 coverage 保留，但不把每个逗号变成新 beat。

STANDARD/EXPANDED 保持原名。dramatic salience、ambiguity、relationship turn、performance risk、misreading risk 为显式专业判断；任一标记风险必须 EXPANDED。每行保留依据和当前源 ref。`shared_ref` 只共享同一 Scene/source 的非递归表达字段，不能继承 objective_ref、target_ref、审批或版本身份。没有自动补动作、停顿秒数或微表情。

## Adaptation Freedom Receipt / Legacy Reconciliation

receipt 复用 AdaptationDecision.expression/reason/narrative_effect/source refs，authorizing owner 为原 literary-adaptation StageReview。保护项包含 must_keep、core relationships/events、character arc、theme conflict、narrative identity；每项必须 PRESERVED、指向已有 source units 与目的地、具有证据。新 ADAPTATION/COMMERCIAL_PRODUCTION 编译缺证据即拒绝；STUDY 不会伪造 PASS。

历史 `verify_screenplay_input` 可以完整重算并比对原有、无新增 receipt 的冻结输出，用于旧档案验证；它不会补 preservation approval。新公共 `compile_source` 不开放该 replay 开关。源或编译内容变更仍无法通过完整相等比较。旧档案的历史权利批准不是 R3B 新改编批准。

无 facet 的 legacy screenplay mapper 可以读取，但返回 `readyForDirection=False` 和 unresolved 交接；正式 Host / Book 无 fallback。旧 DPD/intent 可反序列化用于回放，缺新绑定不能用于新正式 Book。没有修改旧媒体、Provider、路由或 Prompt。

## Tests and Source Integrity

最终执行数据见 [Gate Evidence](Literary-Cinema-R3B-Gate-Evidence.md) 与 `validation.json`。新增测试包括实际 Book completion 正例及 swap/stale/concern/missing review/listener scope 反例，而非只测独立 helper。第一次全回归揭示历史 source replay 与一个旧合成语言 fixture 缺新 receipt；已分别修复兼容边界和补合成 fixture 证据，再执行全回归。没有把这些本轮失败称为 baseline failure。

`source-integrity.json` 记录修改前后 22 份创作源文件 hash 一致；264 份 Provider/Prompt/Skill 等受保护文件 hash 一致。R2 正文 SHA256：`dae155c1d27e6091d8277e773fa22e1ca20b549e6a3e936322256a246b425c08`。本轮没有调用生成 API。

## Known Gaps

1. Gate 不自动发现未被 Scene 标记的重要信息/交互，也不以词匹配证明作者的戏剧解释真实；需专业审阅。拒绝几个空泛理由只是防明显占位，不能替代语义评审。
2. 原 Scene 把动作 prose 和对白数组分开，二者交错位置由 source-owner annotation 承担；各自内部顺序可确定性校验，交错是否忠于完整正文仍需源审阅。没有引入 NLP guessing。
3. 当前载体区间要求顺序且不重叠；复杂同时动作需源 owner 选择合适的聚合载体或未来最小扩展。本轮没有重造通用时间图。
4. S01/S03 是原文静默/压力链诊断；S04 是坟墓等待的有界梦境片段，不是全梦境全面 dramaturgy 认证。S01/S03 不虚构两人 interaction 来填满 causalCoverage。
5. Preservation receipt 是有来源的专业证明，不是机器理解人物逻辑；历史已批准档案不因 replay 自动补获 R3B preservation 证据。
6. 本片真实 R2 sidecar 尚未作为新正式 Scene/DPD/Director 链 adoption。S02 保留 concern，必须在 R3C 由 Scene 修复/审阅，不可据本轮测试声称剧本成功或可付费生产。
7. 全库 mypy 存在修改前已复现的 40 条错误；本轮核对新增错误为零，详见验证文件。

## Status

```text
SCENE_DRAMATURGY_HANDOFF_IMPLEMENTED = YES
ACTION_RESPONSE_CAUSALITY_IMPLEMENTED = YES
EXPECTED_ACTUAL_RESPONSE_TRACE_IMPLEMENTED = YES
STRATEGY_CHANGE_TRACE_IMPLEMENTED = YES
INFORMATION_RELEASE_GATE_IMPLEMENTED = YES
EXACT_DIALOGUE_TURN_BINDING_IMPLEMENTED = YES
LISTENER_CAUSAL_COVERAGE_IMPLEMENTED = YES
SILENCE_CAUSAL_COVERAGE_IMPLEMENTED = YES
DIRECTOR_INTENT_VERSION_BINDING_IMPLEMENTED = YES
DIRECTION_DENSITY_POLICY_IMPLEMENTED = YES
ADAPTATION_FREEDOM_RECEIPT_IMPLEMENTED = YES
PROMPT_GENERATOR_UNCHANGED_AS_TRANSLATOR = YES
SCREENPLAY_BODY_CHANGED = NO
PAID_GENERATION = 0
READY_FOR_LITERARY_CINEMA_R3C = YES
```

R3C readiness 仅指可进行后续人工创作修复/审阅。本轮到此停止；没有开始 R3C 或 Seedance A5。
