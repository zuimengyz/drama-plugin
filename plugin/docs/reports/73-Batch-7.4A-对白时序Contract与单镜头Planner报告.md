# 73 — Batch 7.4A：对白时序 Contract 与单镜头 Planner 报告

日期：2026-09-03。正式编号：**Batch 7.4A — Dialogue Timing Contract & Single-Shot Planner**。

## 1. 执行摘要

**BATCH_7_4A = PASS；USER_TIMING_REVIEW = PENDING。** 完成 provider-neutral
`DialogueTimingPlan` / `DialogueTurnTiming`、单 Shot 确定性 Planner、极小内部 policy、
Shot Design skill 路由、四类合成 fixture 与第五个当前真实 Domain 回归 fixture。

真实 Shot 的推荐计划为：开头 500ms；王思礼 500–5500ms；反应 800ms；
哥舒翰 6300–9500ms；结尾 1000ms。使用的是 Domain 的 **10500ms planned duration**，
不是 actual Video 的 11042ms。

第二句推荐起点为 **6300ms**，比旧 USER_REVIEW 5200ms 晚 **1100ms**。
实际 D1 4107ms 大于该句 3200ms 的估算窗口，故
**ACTUAL_D1_FITS_PLANNED_WINDOW = NO**。这是估算与实际执行差异的有效诊断，
不把自动计划当作艺术验收，也不据此反向调整本次计划。

所有真实音视频 Provider、Voice Design、Create Model、新 Audio、Video generation、
Final AV mux 与领域写操作均为 0。完成后停在 7.4B 之前。

## 2. 72 号问题回顾

72/7.3E 已完成固定 Video + D1 + USER_REVIEW placement → durable Final Shot，
工程链路 PASS；用户随后认为 5200ms 的艺术 placement 不合适。
根因是 `DIALOGUE_TIMING_PLANNING_GAP = IDENTIFIED`：原有对白 identity、speaker、
估算与 DPD，尚不能表达每句起止及句间人物反应。

本批没有修补某个既有毫秒值。5200 仅在计划落盘后的 evaluation sidecar 中比较；
没有进入 Planner、policy、intent 或规划 fixture。

## 3. 本批范围

实现单 Shot 中完整 ordered SpokenContent 的计划时序与时长诊断。新增代码没有网络、
文件或媒体 I/O。集成 runner 只读本地 JSON，先输出 plan，后加载独立 evaluation。

没有 Scene/Episode timeline、跨 Shot 对白切片、重叠时间线、TTS 合成、Video 生成、
嘴型处理、AVSyncPlan 更新或 Final Shot 重建。真实环境仅访问现有 Domain GET API。

## 4. Architecture Freeze

以下既有源码和语义未改：DPD Core / Scene-Beat-Line、VisualPerformanceBrief、
RealizedPerformance、AudioPerformanceBrief、VideoConditionedAudio、Voice、SpokenContent、
AVSyncPlan、AcousticMixPlan、7.3E Final Assembly。

`contracts/__init__.py` 只导出两个新增 contract；Shot Design skill 加入 timing-only 路由。
没有修改旧绑定 schema、Scene/Shot contract、plugin manifest、Java、DB 或 MCP。
未安装或重新安装本机插件；本批交付为仓库实现与测试。

## 5. Timing AS-IS Audit

先审计 72（含 Resume）、69/7.3C、70/7.3D，creation/audio/dpd/av_sync contracts、
现有 duration/fingerprint helpers、Dialogue convention、Shot Design/Planning、
Shot Production、Audio Production、DPD skills。编码前审计记录保存于工作区
`artifacts/batch7-4a/evidence/as-is-audit.md`。

| 必答审计问题 | 当前事实与处理 |
| --- | --- |
| 1. 多个 SpokenContent 怎样记录？ | Shot.content.spokenContentBindings[]，每项只有 spokenContentId + coverageIntent。 |
| 2. 顺序是否明确？ | 数组已有稳定顺序，但旧文档未声明播放顺序。本批在新 timing 消费层固定数组顺序，输出 1-based sequence；不改旧 contract。 |
| 3. speaker binding？ | binding → parent Scene canonical item.speakerKey；真实 Work historicalActorHierarchy 已核实两者均存在。绝不从姓名猜。 |
| 4. 已有 estimatedDurationMs？ | 有，正整数；当前两句为 5000 / 3200。 |
| 5. estimate 的 authority？ | Scene authoring 的语言/字词率启发式与表演意图调整；只是规划估算，不是最终 TTS 实测。 |
| 6. Shot planned duration？ | 当前 plannedDurationMs=10500。旧 rhythmDurationEstimate 文字为 5–9 seconds，存在不一致；本批使用正式整数、不改原 Shot。 |
| 7. 已有 reaction/pause/action？ | Scene tacticsAndBeats、turn、requiredTransition；Shot subjectActionBlocking、visual entry/exit 与 narrative state。没有统一的数值 reaction window。 |
| 8. DPD 哪些字段相关？ | dramaticAction、objective、tactic、relationship/authority、activation/control、continuity/change、transitionTrigger 及相邻 turn 的整体关系。 |
| 9. timing 混在哪里？ | Spoken estimate、Shot planned/prose duration、Audio TargetTimingPolicy、Audio brief rhythm/pause、RP observed windows、AVSyncPlan accepted placement、AvTimelineItem actual slices；各自 authority 保留。 |
| 10. 可复用 helper？ | canonical_json / sha256_canonical、compose_dpd / fingerprint_dpd。没有独立 speech estimator，也没有可直接复用且保证排除 post-production 的 Shot/Spoken planning fingerprint helper。 |

本机 Service/MCP 初始未运行。为当前 Domain 核对，临时通过既有脚本启动已构建的
Drama Service JAR，沿用正式配置 `sql.init.mode=never`；未编译 Java、未初始化数据库。
只读 get_scene/get_shot/get_work 成功，Scene/Shot 完整 JSON 与历史 snapshot 相同，
Work 为 version 5。完成后关闭本次启动的服务。MCP 测试通过离线适配器执行，无需启动 MCP。

当前 72 Final Shot 在计划生成后另行只读 get_media 核实：

```text
MediaId = media_a78d6ab7e9e94d06912c76658d28d378
purpose = FINAL_AV
contentHash = ca306f27b9e7da9ee03e5fa340cc06234b63b91119639a1fa242eae73aff0cbc
finalShotFingerprint = 15f65974fd72a6c471a8c1b16d5d5b00df511d85f9b12b62dcc330503cd4cc0e
AVSyncPlan fingerprint = 3a159f37e397270aeb8bc7b4164984ace1d912700ae809192d69ac5068dfe271
```

这些 metadata 只进 audit evidence，未传给 Planner；未 resolve/download 或读取音视频 bytes。

## 6. Dialogue Timing 职责

只负责“什么时候发生”：开头建立、每句计划起止、轮次交接的反应、结尾 hold、
Shot 预算是否足够。canonical text 与 speaker 不由 Planner 创作。
它不会决定角色动机、声音身份、具体声音表演、镜头语言或实际视频演成什么。

## 7. Planned vs Accepted Timing

```text
DialogueTimingPlan = PLANNED TIMING
Video production -> actual Video -> future reconciliation
-> Accepted timing -> AVSyncPlan -> Final AV
```

本批只实现第一层。PLANNED 不是 accepted actual timing，更不是 observed mouth timing。
即使时长预算通过，也不授权最终 mux。状态仅 PLANNED / CONFLICT；缺失或无效输入
返回明确错误，不构建新 workflow state machine。

## 8. DPD / Timing 边界

DPD 保留 objective/action/tactic、关系/权威、内部激活/外部控制等戏剧语义；
不添加 pauseMs、reactionMs、dialogueStartMs。

采用用户允许的两阶段 Agent 路径：Shot Design Agent 综合当前及上一 turn 的 DPD，
形成带理由的短 vocabulary 意图；numeric Planner 验证意图绑定的完整 context fingerprint，
再确定性物化毫秒。没有根据 HIGH 或 emotion 的简单数值公式。

这不声称能确定性理解任意自然语言。确定性保证覆盖**已固定的 DPD + 已审阅意图 + policy**；
语义判断由 Agent 负责并可审计。DPD/context 改变必须重新审阅，不能只替换旧 intent 的 hash。

## 9. Lip Sync / Timing 边界

Timing 规划整句何时说；Lip Sync 是整句期间的 phoneme/viseme 与嘴型关系。
本批没有 phoneme alignment、viseme、mouth retarget、Wav2Lip、Sync 3 或 audio-driven generation。
`LIP_SYNC = OUT_OF_SCOPE`。

## 10. AVSyncPlan / DialogueTimingPlan 边界

AVSyncPlan 引用固定 Video/D1 与被接受的 actual placement；DialogueTimingPlan
只引用创作输入与估算。没有新增 AVSync timingAuthority，也没有把计划直接转换成 mux manifest。
旧 72 USER_REVIEW placement 及 Final Shot 保持原样。

## 11. Duration Estimate Authority

复用既有 canonical estimates；不重新计算、不改字、不调整 TTS speed。
现有 Audio `NATURAL/FIT_WINDOW/FIXED_WINDOW` 是执行 policy，不能当作 speech estimator。

canonical convention 已要求每句有 estimatedDurationMs，本批不为缺失 estimate 创建一个
伪精确回退模型：缺失返回 `DURATION_ESTIMATE_REQUIRED`，要求上游提供可信 planning estimate；
非正整数（含 bool、浮点、字符串）返回 `INVALID_DURATION_ESTIMATE`。
因此没有新增 Speech Duration Model 或固定“每汉字 300ms”公式。

实际 4107ms 只进 evaluation；缺少 planned target 时保留 null 并报告 required duration，
不会读取 11042ms 视频时长来补目标，也不宣称“已适配一个未知目标”。

## 12. DialogueTimingPlan Contract

新增 `contracts/dialogue_timing.py`，schema=`dialogue-timing-plan-v1`。
主要字段：sceneId/shotId、shotFingerprint/sourceFingerprint、policyVersion/policyFingerprint、
可空 targetShotDurationMs、turns、pre/minimumPost/post holds、recommendedMinimumShotDurationMs、
plannedDurationMs、status、diagnostic、fingerprint。

严格检查 schema、字段白名单、整数、唯一/连续顺序、重复对白、负时间、end=start+duration、
重叠、reaction/pre/post 算术、预算状态、intent context 一致性与 canonical fingerprint。
CONFLICT 中超过 target 的窗口是完整需求诊断，不能冒充适配成功的 PLANNED 计划。

跨当前来源复用必须调用 `validate_dialogue_timing_plan()` 重放，拒绝错误 Scene/Shot
或自洽但过期的计划。仅 hash 自洽无法证明与当前输入的身份和来源一致。

## 13. DialogueTurnTiming

每 turn 保存 spokenContentId、speakerKey、sequence、plannedStart/Duration/EndMs、
transitionFromPrevious、transitionHoldMs、transitionReason，以及 canonical Spoken/DPD/intent-context
fingerprints。durationAuthority 固定 `SCENE_PLANNING_ESTIMATE`。

没有 exact text、audio/video identity、provider/model、observed timing。
第一项 transitionHoldMs=0，开头空间只计入 preDialogueHoldMs，避免重复预算。
REACTION coverage 仍表示该 canonical item 的完整声音覆盖，不新增重复沉默 turn。

## 14. Timing Policy

`dialogue_timing.py` 内部 `DialogueTimingPolicy`，版本 `dialogue-timing-policy-v1`。

| 项目 | 当前平台 policy |
| --- | ---: |
| 正常开头建立 | 500ms |
| 有明确意图的立即开头 | 0ms |
| 立即接话 / 最小 inter-turn separation | 100ms |
| SHORT_REACTION | 350ms |
| DELIBERATE_REACTION | 800ms |
| 最小 post hold | 500ms |

全部非零窗口为正整数且 reaction bands 严格递增，配置与版本均进 fingerprint。
**这些数值只是当前平台 planning policy，不是演员标准停顿、历史剧黄金比例或影视工业标准。**
没有 tolerance、magic-ms 分散映射、自动 speed 或 estimate inflation。

## 15. DPD → Timing Intent

内部 `TransitionIntent` 只有 contextFingerprint、transition、rationale；没有 schemaVersion、
存储 identity、ms、CRUD。可用类别：OPENING、IMMEDIATE_RESPONSE、SHORT_REACTION、
DELIBERATE_REACTION；OVERLAP 仅为明确拒绝哨兵，不增加时间线能力。

真实 fixture 的第一句原先没有独立保存的 DPDSnapshot。本批按 current Scene/Shot/SpokenContent
及既有 SceneDPD，为 proposal 建立**新增临时 DPD 输入**：请求主帅批准、具体进言策略、
部将/主帅授权关系、HIGH activation/control，以及守势决策转向政治建议的 continuity/change。
它不是伪称既有持久化 DPD，未回写任何 Domain。

第二句完整复用 7.3D evidence 中已冻结 DPD，指纹保持
`2d826a70c27da23aded5eda30082931b5c122115dd932ce104b3fb590ec90e1b`。
前句请求批准且将决定交给主帅；后句 reject/stop proposal/controlled refusal，具有 dominant
commander 与 personally exposed 的关系，高激活且高控制，trigger 为听完建议，change
从 listening pressure 转为 definitive refusal。综合支持一次有界判断反应。
urgency 要及时关闭建议，排除长时间悬置；本次选择 DELIBERATE_REACTION 是可复核创作判断，
不宣称 DPD 逻辑上唯一导出 800ms。

## 16. Timing Intent → Milliseconds

`plan_dialogue_timing()` 重新生成 context 并核对每个 intent 的 fingerprint；缺少意图报
TIMING_INTENT_REQUIRED，旧意图报 STALE_TIMING_INTENT。数值只来自集中 policy：

```text
start[0] = preHold
end[i] = start[i] + estimate[i]
start[i+1] = end[i] + transitionHold[i+1]
minimum = lastEnd + minimumPostHold
```

没有 LLM 自由输出毫秒、random.uniform、temperature、调用实际媒体后倒推起点。

## 17. Pre / Reaction / Post Hold

默认留开头建立。立即开头需要显式 IMMEDIATE_RESPONSE 意图；句间立即接话仍保留
100ms separation，保证前一句完整结束。明确抢话到上一句尚未结束或同时说话，必须
声明 OVERLAP 并返回 `OVERLAPPING_DIALOGUE_NOT_SUPPORTED`，不能暗改为立即接话。

预算富余统一进入结尾 hold，不把对白拉到 Shot 尾端，也不悄悄改反应长度。
这是一项明确且保守的 policy；极长 Shot 可能形成较长结尾 hold，仍需用户艺术 Review。

## 18. Timing Conflict

Fixture D：target=3000ms，speech=3400ms，pre=500ms，reaction=800ms，post minimum=500ms，
minimum required=5200ms。返回 CONFLICT/TIMING_CONFLICT、recommended minimum=5200ms。

保留台词、顺序、原 duration estimates 与全部 reaction/post 需求；不会删词、改词、
极端拉速、删 reaction、制造 overlap、修改 Shot 或延长 Video。
由上游审阅后选择延长/拆 Shot、修订 Dialogue 或 Scene pacing。

## 19. Fingerprint / Staleness

复用 canonical sorted-key SHA-256。plan fingerprint 覆盖 schema、Shot planning projection、
ordered Spoken hashes、speaker、DPD、estimate、context/intent、policy version/material、
target 与输出。对象字段顺序无关，数组顺序有意义。

Shot planning projection 只含稳定 identity、绑定、目标和最小 narrative/action/entry/exit context。
不直接 hash 整个开放 Shot.content，避免夹带 current timestamp、random UUID、Host、
actual Video hash、Comfy job、Fish response、USER_REVIEW anchor 等依赖。
Camera/framing 不参与语义时序；变化不会无故改 plan。

text/order/speaker/DPD/estimate/target/policy 任一变化均令旧 plan stale；有的变化只改变
fingerprint、不改变毫秒也是正确结果。变更后必须重新审阅相关意图并重放校验。

当前 context fingerprint：
`52d00ccaf6ebfea446bb35ee392c56f0bfee6ad3f10399c5414f1d356bb39056`。

当前 plan fingerprint：
`dfe0dc594602c215597d462e5e670814e783fddbfc1255e5ee1b2eedb8776083`。

## 20. Offline Fixtures

| Fixture | 核验 |
| --- | --- |
| A 单人单句 | pre=500，1800ms speech，post 独立保留，输入不变。 |
| B 双人两句 | canonical order/speakers，speech=1800/1600，800ms 判断反应。 |
| C Immediate Response | action/objective/tactic/continuity 共同支持立即接话，100ms 小于 B 的 800ms，仍无 overlap。 |
| D Timing Conflict | 3000ms target vs 5200ms 完整需求，正确 CONFLICT，不压缩。 |
| E 72 真实回归 | current Scene/Shot/Spoken、既有拒绝 DPD + 明示临时 proposal DPD，纯离线 replay。 |

A–D 是测试文件中的可重放输入 factory；E 存为
`tests/fixtures/dialogue-timing-72.json`，provenance 明示全部来源与新增临时 DPD。
actual duration/old anchor 在单独 `dialogue-timing-72-evaluation.json`，不在规划 fixture 内。

## 21. 72 Real Fixture

```text
72_FIXTURE_TIMING_PLAN
Shot = shot_83db7eb53b2f49d3a58428d4659e584e
Scene = scene_3ad95aa042e647d9a9be05a51dd8a009
Target planned Shot duration = 10500ms
Minimum required = 10000ms
Plan total = 10500ms
Status = PLANNED
```

| 阶段 | 起止 / 时长 |
| --- | --- |
| Pre-dialogue hold | 0–500ms / 500ms |
| Turn A，spoken-s1-wangsili-proposal | 500–5500ms / 5000ms |
| DELIBERATE_REACTION | 5500–6300ms / 800ms |
| Turn B，spoken-s1-geshuhan-refusal | 6300–9500ms / 3200ms |
| Post-dialogue hold | 9500–10500ms / 1000ms |

完整计划与上下文在工作区 `artifacts/batch7-4a/evidence/` 的
`dialogue-timing-plan.json` 和 `planning-context.json`。planned target 与 actual Video
不同是明确边界，不把 542ms 差额偷偷补进本次预算。

## 22. 5200ms Comparison

```text
72 User Anchor = 5200ms
7.4A Planner Recommendation = 6300ms
differenceMs = 6300 - 5200 = +1100ms
USER_TIMING_REVIEW = PENDING
```

新值来自开头 500 + 前句估算 5000 + 判断反应 800。
未以 5200 校准 policy、截断前句或选择 reaction；未声称自动计划艺术上更好。
以后须在真实视频上进行 reconciliation 与用户 Review 才能确定 accepted timing。

## 23. Actual D1 Fit Evaluation

```text
planned second-line window = 3200ms
actual D1 = 4107ms
excess = 907ms
ACTUAL_D1_FITS_PLANNED_WINDOW = NO
```

这是整句 window fit 检查；即使结尾另有 hold，也不能把结尾空间默默扩成 speech window
并宣称 fit。Planner 输入/结果均未因 evaluation 改变。
集成测试分别使用原值与另一组 actual duration/anchor/video duration，验证输出 plan bytes 完全相同。

## 24. Tests

最终测试使用现有 `drama-mcp-service/.venv/bin/python`，因为 Plugin 自己的旧 venv
缺少 pydantic；没有改 dependencies 或安装新包。通过 PYTHONPATH/MYPYPATH 明确使用当前源码。

| Suite | 最终结果 |
| --- | ---: |
| Dialogue timing contract/planner/fingerprint/conflict/real fixture | 69 passed |
| Plugin full pytest，包含 DPD、Shot/Spoken、7.3E AVSync 等全部旧回归 | 290 passed |
| Plugin strict mypy | PASS，57 source files |
| Drama MCP regression | 26 passed |
| Drama MCP strict mypy | PASS，4 source files |
| Shot Design skill quick_validate | PASS |
| git diff --check | PASS |
| Java build/tests | NOT_REQUIRED，未修改 Java |

覆盖 unsupported schema、missing Shot/order/speaker、duplicate sequence/Spoken、非法 estimate、
negative timing、end<start、overlap、overflow status、错误 Scene/Shot identity、未知/provider fields、
DPD staleness/recomposition、intent context、budget 算术、确定性、key reorder、policy 失效及
evaluation 隔离。测试中的网络陷阱确认 Planner 无网络访问。

所有计数来自完整执行；日志保存在 `artifacts/batch7-4a/evidence/*pytest.txt` 与 `*mypy.txt`。
没有真实 Fish/Comfy、Voice Design/Create Model、Audio/Video generation 或 Final Mux。

## 25. Complexity Audit

| 项目 | 结果 |
| --- | --- |
| production artifact contracts | 2：DialogueTimingPlan、DialogueTurnTiming |
| 内部值类型 | 2：6 字段 policy、3 字段 intent；非业务 Entity、无 schema/API/CRUD |
| production 新模块 | 2，contract 114 行 + planner/helper 249 行，总 363 行 |
| helper | 3 个公开函数：context、plan、validate；1 个内部 nonblank 校验 |
| enum classes | 0；4 个可输出节奏类别，OVERLAP 仅拒绝哨兵 |
| policy constants | 一个极小 policy：版本 + 5 个数值窗口，没有分散 magic milliseconds |
| 抽象深度 | 沿用 ContractModel，单层输入/输出校验与线性 turn loop |
| 新文件 / 既有改动 | 8 个新文件（含 report/docs/runner/fixtures/test），改 2 个文件（exports、Shot Design） |
| 新 Service/DB/MCP/Java | 全部 0 |

相对理想“两个 contracts + 一个 helper”，增加的只是必要的内部 policy/intent 校验值类型：
前者集中可审计数值，后者把 Agent 判断绑定到来源并拒绝自由毫秒/未知字段。
未引入 Timeline Engine、Scheduling Framework、Event Bus、Temporal Graph、DSL、AST、
orchestrator 或 intent 业务实体。无需独立 dialogue-timing-planning skill；扩展现有 Shot Design 即可。

## 26. 未解决问题

1. 数值 policy 与真实 fixture 的 semantic intent 仍需艺术 Review；工程 PASS 不代表美学更优。
2. 3200ms 估算不能容纳实际 D1 4107ms，未来需 reconciliation 或上游修订；本批未修改。
3. 当前模型由 Agent 审阅自由文本 DPD，不是通用自动语言分类器；若语义不足或互相矛盾，
   应报告缺输入，不能伪造确定性结论。
4. policy 把全部余量放到结尾；超长尾部是否合适需创作判断。无跨 Shot 调度、speech slicing 或 overlap。
5. 旧 Shot prose duration 与数字不一致已记录；本批遵守 freeze，不修旧 Domain。

这些是明确的范围/Review 边界，没有未修复的本批已知工程 FAIL。

## 27. 7.4B 前置条件

仅记录，未实施：

```text
current DialogueTimingPlan + source/intent/policy fingerprints
+ actual Video
+ RealizedPerformanceSnapshot
-> Dialogue Timing Reconciliation
-> AcceptedDialogueTiming
-> AVSyncPlan
-> Final Shot
```

需重新审阅实际演出、实际 speech duration、原有 UNKNOWN mouth facts 与用户时间偏好；
不能把本批 6300ms 直接写成 approved mux authority。

必答 Q1–Q15：

| 问题 | 回答 |
| --- | --- |
| Q1 解决什么？ | 单 Shot 的整句对白起止、轮次反应、开头/结尾 hold 和预算。 |
| Q2 与 DPD 区别？ | DPD 拥有戏剧行动/动机/关系；Timing 拥有计划发生时刻。 |
| Q3 与 Lip Sync 区别？ | 不做 phoneme/viseme/mouth，只规划整句窗口。 |
| Q4 与 AVSyncPlan 区别？ | 创作计划 vs 被接受的实际 AV placement。 |
| Q5 消费实际 Video？ | NO。 |
| Q6 消费最终 D1 duration？ | NO，只有计划输出后 evaluation。 |
| Q7 DPD 保存 pauseMs？ | NO。 |
| Q8 谁判断立即/短/长反应？ | DPD semantics + Shot Design Agent/Timing Planner 的临时意图阶段。 |
| Q9 谁转毫秒？ | deterministic timing policy。 |
| Q10 LLM 可自由输出毫秒？ | NO。 |
| Q11 时长不够？ | TIMING_CONFLICT，报告 minimum，由上游处理。 |
| Q12 可以删台词？ | NO。 |
| Q13 可以极端加速 TTS？ | NO。 |
| Q14 计划直接成为 mux authority？ | NO，未来需要 7.4B。 |
| Q15 5200 输入 Planner？ | NO，只用于输出后比较。 |

## 28. 最终 PASS / PARTIAL / FAIL

```text
DIALOGUE_TIMING_CONTRACT = PASS
SINGLE_SHOT_PLANNER = PASS
TURN_ORDER_AUTHORITY = PASS
DPD_TIMING_BOUNDARY = PASS
LIP_SYNC_BOUNDARY = PASS
AVSYNC_BOUNDARY = PASS
DETERMINISTIC_TIMING_POLICY = PASS
PRE_DIALOGUE_HOLD = PASS
INTER_TURN_REACTION = PASS
POST_DIALOGUE_HOLD = PASS
NO_DIALOGUE_OVERLAP_V1 = PASS
TIMING_CONFLICT = PASS
FINGERPRINT_DETERMINISM = PASS
NO_PROVIDER_DEPENDENCY = PASS
NO_DATABASE = PASS
NO_MCP_CRUD = PASS
REGRESSION = PASS
COMPLEXITY_AUDIT = PASS
72_FIXTURE = PASS
ACTUAL_D1_FITS_PLANNED_WINDOW = NO
USER_TIMING_REVIEW = PENDING
FINAL_AV_MUX_CALLS = 0
FISH_CALLS = 0
COMFY_CALLS = 0
BATCH_7_4A = PASS
STOP BEFORE Batch 7.4B Realized Timing Reconciliation
```
