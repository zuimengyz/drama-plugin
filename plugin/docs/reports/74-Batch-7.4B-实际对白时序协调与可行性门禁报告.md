# Batch 7.4B — 实际对白时序协调与可行性门禁报告

## 1. 执行摘要

Batch 7.4B Phase A 恢复执行结果为 **PASS**。Turn A current Final Audio 已在独立前置任务补齐，本次重新读取当前 Domain 并完成正式 Full Realized Reconciliation：Turn A=4571ms、Turn B=4107ms、完整对白覆盖=COMPLETE、最低需求=10478ms、实际视频=11042ms、物理可行性=FEASIBLE、余量=564ms。

系统先判定 feasibility，再生成 proposal：A 500–5071ms、受保护 reaction 5071–5871ms、B 5871–9978ms、post 1064ms。Artistic Compatibility=UNKNOWN，User Timing Review=REQUIRED。Proposal 不是 accepted timing，也没有进入 AVSync、Mux 或 Final Shot rebuild；现有72 Final Shot 仍只有 Turn B，对白覆盖仍为 INCOMPLETE。

## 2. 本批范围

完成 Source Plan 重验、完整 Shot coverage、每条 Audio 当前 lineage、全实际时长预算、艺术约束、原因诊断、proposal、72/73 fixture、回归、文档和报告。恢复执行只通过现有 Service 读取当前 Domain；没有写 Domain。

本次 7.4B Provider Calls：Fish=0、Comfy=0、Voice Design=0、Create Model=0、Audio Generation=0、Video Generation=0、Final AV Mux=0。Turn A Audio 的一次 Fish 生产属于已完成的独立 prerequisite，不计入本次 reconciliation。

## 3. 7.4A 输入

Source plan fingerprint：`dfe0dc594602c215597d462e5e670814e783fddbfc1255e5ee1b2eedb8776083`。

| 项目 | 冻结计划 |
|---|---:|
| Shot duration | 10500ms |
| Pre hold | 0–500ms |
| Turn A | 500–5500ms；5000ms |
| DELIBERATE_REACTION | 5500–6300ms；800ms |
| Turn B | 6300–9500ms；3200ms |
| Planned post hold | 1000ms |
| Minimum post hold | 500ms |

现有 `validate_dialogue_timing_plan` 已使用当前 Scene/Shot、SpokenContent 顺序与身份、planning DPD、intent context 和 policy 重放验证。原计划未覆盖或改写。

## 4. Architecture Freeze

DPD Core、DialogueTimingPlan/Policy、VisualPerformanceBrief、Audio/Video projection contracts、Voice、SpokenContent、AVSyncPlan 与7.3E assembly 保持冻结。22个冻结源码/计划文件的 SHA-256 复核全部一致，见 [freeze-verification.json](../../../../artifacts/batch7-4b/evidence/freeze-verification.json)。

恢复后只修正 7.4B helper 对 planning lineage 与 audio-production lineage 的混同，并更新 runner、fixture、tests 和 docs。核心 `DialogueTimingReconciliation` Contract 未新增字段；DB、MCP、Service、Java 与 Domain 均无改动。

## 5. Shot Dialogue Coverage Audit

当前 Scene=`scene_3ad95aa042e647d9a9be05a51dd8a009`，Shot=`shot_83db7eb53b2f49d3a58428d4659e584e`，Work=`work_9cc5d11969a64f93bce4a544f349c793`，version=5。

| Sequence | spokenContentId | Speaker | Coverage | Planned |
|---|---|---|---|---:|
| 1 | `spoken-s1-wangsili-proposal` | `speaker:wangsili` | ON_SCREEN_SPEAKER | 5000ms |
| 2 | `spoken-s1-geshuhan-refusal` | `speaker:geshuhan` | ON_SCREEN_SPEAKER | 3200ms |

当前 Work 共枚举35条 AUDIO（含 DEBUG），保留与当前 Scene/Shot 有关的18条候选进入 selector。完整 turn 顺序来自 Shot binding，正文身份来自 Scene canonical SpokenContent。当前只读快照见 [current-domain.json](../../../../artifacts/batch7-4b/evidence/current-domain.json)。

## 6. Actual Audio Coverage

| Turn | 状态 | Media | Actual | Review |
|---|---|---|---:|---|
| A | PRESENT | `media_76a8fb24233246189d030babc7ceffd4` | 4571ms | technical PASS / artistic PENDING |
| B | PRESENT | `media_6f4d16d785b84b52b3062e0666a826b5` | 4107ms | technical PASS / artistic PENDING |

Turn A hash=`0940ec4c83da547a20f547a2ca5b90752443d32d22d013e5cce8ff13c71865c7`；Turn B hash=`4db91e1299cb3083db55290e5e23ef8595e012e5a7b3fe185ba80a44121e7a9c`。两条 Audio 均通过 canonical identity、speaker、current Voice/master/mapping、production DPD、Video、speaker-specific RP、Base/Final Projection、sourceRef、technical/intelligibility gate。

历史同句或旧 Voice Audio 仍全部排除。PRESENT 只表示可用于实际时长证据；两条 `reviewStatus=PENDING` 均保留 `AUDIO_REVIEW_PENDING`，未提升为艺术接受或正式复用 authority。FULL_SHOT_REALIZED_DIALOGUE_COVERAGE=COMPLETE。

## 7. Planned vs Realized Duration

| 分量 | Planned | Realized | Delta |
|---|---:|---:|---:|
| Shot | 10500 | 11042 | +542ms |
| Turn A | 5000 | 4571 | -429ms |
| Turn B | 3200 | 4107 | +907ms |
| Speech total | 8200 | 8678 | +478ms |
| Reaction | 800 | 800 protected | 0ms |
| Post | 1000 | 1064 proposed | +64ms |

两个 actual duration 都是 `ACTUAL_AUDIO` authority。Turn B 的 +907ms drift 不能单独推导台词错误；Turn A 的 -429ms 与之合并后，净 speech drift 为 +478ms。

## 8. Physical Feasibility Gate

执行顺序固定为 coverage → 物理预算 → 必要戏剧空间 → 实际视觉兼容 → 诊断 → 可行时 proposal。

```text
500 pre
+ 4571 Turn A actual
+ 800 protected reaction
+ 4107 Turn B actual
+ 500 minimum post
= 10478ms required minimum

11042 - 10478 = 564ms slack
```

全部 turn actual evidence 完整，`FULL_REALIZED_FEASIBILITY=FEASIBLE`，`fullRealizedRequiredMinimumMs=10478`，overflow=0。

## 9. Hybrid Feasibility

完整实际证据已经存在，因此 `evidenceMode=REALIZED`、`HYBRID_FEASIBILITY=NOT_NEEDED`。原先 A estimate + B actual 得到的10907ms/135ms仅保留为历史恢复背景，不参与当前 artifact 或 proposal。

Missing-turn 离线 fixture 仍验证：缺任意实际 Audio 时，Full Realized 只能 EVIDENCE_LIMITED；Hybrid 结果不能冒充 Full PASS。

## 10. Artistic Feasibility

物理 FEASIBLE 不自动等于艺术可行。Accepted shot-observation RP 的 mouthActivity=UNKNOWN，无法提供可靠 speech onset；Turn-A speaker-specific RP 同样保留 mouthActivity=UNKNOWN。两条 Audio 的艺术 review 均为 PENDING。

因此 `ARTISTIC_COMPATIBILITY=UNKNOWN`、`ARTISTIC_TIMING_REVIEW_REQUIRED`。系统不宣布 proposal 比旧5200或计划6300更好，也不把头部、视线或手势窗口伪造成开口边界。

## 11. Flexible Slack

净 speech drift=478ms，先由 actual Video 相对 planned Shot 的542ms额外容量吸收：consumedVideoDelta=478ms。planned post surplus 未被消耗：consumedPostSlack=0ms。

结果 post hold 为 `1000 + 542 - 478 = 1064ms`，高于 policy minimum 500ms。版本化规则仍为 `VIDEO_DELTA_THEN_POST_SURPLUS_V1`，没有新增 timing policy。

## 12. Reaction Protection

800ms 来自当前 DELIBERATE_REACTION intent 与冻结 policy，并在 proposal 中完整保留为5071–5871ms。它不是通用影视标准，但当前视觉证据没有授权压缩或改写该语义结构。

冲突 fixture 可以计算压缩反事实来解释原因，但该值不能进入 proposal。没有裁剪对白、加速 Audio、重叠发言或把 reaction 压到最低分隔值。

## 13. Timing Conflict

当前真实 fixture 无物理冲突。若 A=6200ms、B=4107ms、Video=11042ms，则 minimum=12107ms、overflow=1065ms，返回 CONFLICT，所有 proposed windows 为 null，User Review=NOT_READY。

若 A=5000ms、B=4107ms、Video=10500ms，则 minimum=10907ms、overflow=407ms；只有压缩 reaction 才能 fit 时，返回 ARTISTIC_COMPATIBILITY=CONFLICTING 和 `REACTION_COMPRESSION_REQUIRED_TO_FIT`，不会自动修复上游。

## 14. Candidate Cause Diagnostics

当前 evidence-based candidate causes：

| Cause | 依据 |
|---|---|
| DURATION_ESTIMATE_DRIFT | A 5000→4571、B 3200→4107，实际总语音比计划多478ms |
| TIMING_OBSERVABILITY | mouth UNKNOWN，缺少可靠 speech onset |

当前不输出 MISSING/STALE Audio、SHOT_DURATION、DIALOGUE_LENGTH、AUDIO_REALIZATION 或 SHOT_SEGMENTATION_REVIEW。候选原因是审查线索，不是修改决定。

## 15. DialogueTimingReconciliation Contract

核心 artifact 仍为 `DialogueTimingReconciliation`，turn detail 仍为 nested `ReconciledDialogueTurn`。实现见 [contract](../../src/drama_plugin/contracts/dialogue_reconciliation.py)、[helper](../../src/drama_plugin/dialogue_reconciliation.py)，说明见 [contract doc](../dialogue-reconciliation-contract.md)。

恢复中发现的窄 bug 是：旧 helper 强制 Actual Audio 的 DPD/RP fingerprint 等于 source plan 的 planning DPD 和单个 shot-observation RP。Turn A 合法生产链使用独立 production DPD `af9827…` 与 speaker-specific RP `2ca43…`，因此被错误拒绝。

修复后，Source Plan 仍用 planning DPD 重放验证；每条 actual Audio 则用显式 `audio_dpd_by_spoken_content` 与 `audio_realized_by_spoken_content` 独立 recompose/refingerprint，并校验同一 Scene/Shot/Video/turn。两组来源分别进入 current freshness evidence。Contract、schema、policy 与 artifact 字段均未变化。

## 16. RealizedPerformance Boundary

Accepted shot-observation RP fingerprint=`a2d3d311576d75a305e6453089176ac89b0d8cfd9c3acd2a141ee24a13cefd12`，observed speaker=`speaker:geshuhan`，head motion=7500–10500ms，mouthActivity=UNKNOWN。

Turn A Audio freshness另验证其 speaker-specific RP fingerprint=`2ca43baa5f4ab5ba8cab24e9da7090d2c6bc2b579b760bf0d50150a721985405`；它与同一 Video/Shot/hash一致，但不替代 accepted shot-observation RP 的艺术门禁。所有可见窗口只作为 evidence/constraint，不作为 speech anchors。

## 17. Timing Proposal

| 分量 | Proposal | Authority |
|---|---|---|
| Pre | 0–500ms | 冻结计划要求 |
| Turn A | 500–5071ms | ACTUAL_AUDIO 4571ms；艺术待审 |
| Reaction | 5071–5871ms | DELIBERATE_REACTION 800ms |
| Turn B | 5871–9978ms | ACTUAL_AUDIO 4107ms；艺术待审 |
| Post | 9978–11042ms | 1064ms ≥ minimum 500ms |

RecommendedPlacementStatus=PROPOSED。线性窗口只在完整 coverage、物理 fit 且无硬 visual conflict 后生成；USER_TIMING_REVIEW=REQUIRED。

## 18. 5200 / 6300 / Proposal Comparison

| 来源 | Turn B start | 状态 |
|---|---:|---|
| 旧 USER_REVIEW anchor | 5200ms | 用户已指出艺术不合适；仅历史比较 |
| 7.4A plan | 6300ms | planning authority |
| 7.4B proposal | 5871ms | actual A 结束后保留800ms reaction |

旧5200仅在 reconciliation 生成后用于 sidecar comparison，不进入 fingerprint。将历史 anchor 改为9000不会改变 artifact 字节。系统不判断三者的艺术优劣。

## 19. 72 Final Shot Dialogue Coverage

Final Shot=`media_a78d6ab7e9e94d06912c76658d28d378`，hash=`ca306f27b9e7da9ee03e5fa340cc06234b63b91119639a1fa242eae73aff0cbc`。当前 manifest 只有 Turn B：start=5200ms、source 0–4107ms；不含 Turn A。

`72_FINAL_SHOT_DIALOGUE_COVERAGE=INCOMPLETE`。这不推翻7.3E engineering PASS，只说明现有成片不是完整双人对白版本。本批未修改 AVSyncPlan 或重建 Final Shot。

## 20. Fingerprint / Staleness

当前 reconciliation fingerprint=`c1ec9267e8aafc1f8bbe27f48c04fe4fe476aaeff604a7a85924e8b675913917`。

Fingerprint material 覆盖 source plan、Video identity/hash/duration、accepted RP、每条 Audio 的 production DPD/RP、current Voice/master/mapping、Audio hash/duration/lineage、coverage、policy、budget 与 proposal。候选按 Media ID 排序并用 canonical JSON；无 timestamp、host、临时 URL、MinIO endpoint、Provider request body、Comfy task 或5200 anchor。

`validate_dialogue_reconciliation` 会对全部 current inputs 确定性重放。Plan、canonical binding/text、Video、accepted RP、per-turn production DPD/RP、Voice、Audio hash/duration/review 或相关候选集合变化都会使旧结果 stale。

## 21. Offline Fixtures

| Fixture | 条件 | 结果 |
|---|---|---|
| A Fully feasible | actual=5000/3200；video11042 | COMPLETE、FEASIBLE；minimum10000、slack1042 |
| B Drift feasible | actual=5000/4000 | FEASIBLE；video542+post258吸收 drift |
| C Physical conflict | actual=6200/4107 | CONFLICT；minimum12107、overflow1065；无 proposal |
| D Missing turn | 移除 A current final | EVIDENCE_LIMITED；Hybrid FEASIBLE；slack135 |
| E Compression risk | actual=5000/4107；video10500 | CONFLICTING；保护800ms reaction；无 proposal |

另覆盖当前真实 full fixture、planning/production DPD 与 RP 分离、production input stale、精确 post 边界、visibility conflict、mouth ABSENT、ambiguous/stale Audio、pending review、determinism 与 historical-anchor 隔离。

## 22. Current Real Fixture

可复跑入口：[evaluate_dialogue_reconciliation.py](../../integration/evaluate_dialogue_reconciliation.py)；输入：[dialogue-reconciliation-72.json](../../tests/fixtures/dialogue-reconciliation-72.json)，引用原7.4A planning fixture。

实际 Video=`media_ac9d14c5cdc74c43ba44562752cf9489`，H264 11.041667s；Turn A PCM 24kHz mono 4.571375s；Turn B PCM 24kHz mono 4.107s。三项本地文件 SHA-256 均与当前 Media hash 一致，见 [physical-input-verification.json](../../../../artifacts/batch7-4b/evidence/physical-input-verification.json)。

当前输出见 [dialogue-timing-reconciliation.json](../../../../artifacts/batch7-4b/evidence/dialogue-timing-reconciliation.json)、[evaluation.json](../../../../artifacts/batch7-4b/evidence/evaluation.json) 与 [coverage-audit.json](../../../../artifacts/batch7-4b/evidence/coverage-audit.json)。结果为 A PRESENT / B PRESENT / COMPLETE / FEASIBLE / Hybrid NOT_NEEDED / Artistic UNKNOWN / minimum10478 / slack564 / overflow0。

## 23. Tests

| Gate | 结果 |
|---|---|
| Dialogue reconciliation focused | 73 passed |
| Plugin full pytest | 365 passed |
| Plugin strict mypy | PASS，59 source files |
| MCP regression | 26 passed |
| MCP strict mypy | PASS，4 source files |
| 冻结文件 SHA-256 | 22/22 PASS |
| Current fixture replay/byte equality | PASS |

Plugin suite 覆盖 DPD、RP、Audio freshness、7.4A timing、7.4B reconciliation 与 AVSync/assembly regression。测试日志位于 `artifacts/batch7-4b/evidence/*pytest.log` 与 `*mypy.log`。

## 24. Complexity Audit

| 项目 | 数量/范围 |
|---|---|
| 核心 artifact | 1（未新增） |
| Nested model | 1（未新增） |
| Contract schema/字段变化 | 0 |
| Reconciliation helper | 353行；新增2个可选 per-turn production input mappings |
| 新 policy / ontology | 0 |
| Services/DB/MCP/Java | 0 |
| Domain writes | 0 |

没有 Timeline Solver、Constraint Framework、Temporal Graph、Scene/Episode Timeline 或 Accepted Timing Domain。结构仍只处理单 Shot 的线性多 turn reconciliation。

## 25. 未解决问题

1. 两条 Audio 的艺术 review 均为 PENDING；本批只确认 current lineage、技术通过与实际时长。
2. mouthActivity=UNKNOWN，系统不能证明真实开口位置或自动宣布 proposal 艺术可行。
3. 72 Final Shot 仍缺 Turn A，需在 timing 被用户/制作审核接受后的独立阶段重建。
4. Proposal 5871ms 尚未成为 production authority，不能直接驱动 Mux。

## 26. User Timing Review Boundary

Q1–Q15：

| 问题 | 回答 |
|---|---|
| 第一件事 | Feasibility；先审计完整 coverage |
| Placement 是第一步吗 | NO |
| Actual Audio 放不下等于台词错吗 | NO |
| 如何判断候选责任层 | Evidence-based candidate causes |
| 缺一个 Turn 可否 Full PASS | NO |
| 可否使用 Hybrid estimate | YES，但 Full 为 EVIDENCE_LIMITED |
| 可否使用 Video extra duration | YES |
| 可否重分配 post surplus | YES，minimum 受保护 |
| Reaction 可否随意压缩 | NO |
| 可否删台词 | NO |
| 可否极端加速 Audio | NO |
| 可否自动拆 Shot | NO；只可提示 review |
| 当前 RP 能否提供 speech onset | NO |
| Proposal 是否直接成为 mux authority | NO |
| 谁批准 Timing | USER / PRODUCTION REVIEW |

本次 proposal 只能提交审查。系统没有写 accepted 状态、AVSyncPlan 或 Media。

## 27. Future Resume

仅记录后续路径：用户明确批准 `APPROVE 7.4B TIMING` 后，重新验证 current evidence，再评估 Accepted Timing → AVSyncPlan → Final Shot rebuild。该后续工作本批未实施。

## 28. 最终 PASS/PARTIAL/FAIL

| 验收项 | 结果 |
|---|---|
| SOURCE_PLAN_VALIDATION | PASS |
| SHOT_DIALOGUE_COVERAGE_AUDIT | PASS |
| ACTUAL_AUDIO_FRESHNESS_AUDIT | PASS |
| PHYSICAL_FEASIBILITY_GATE | PASS；FULL REALIZED FEASIBLE |
| HYBRID_EVIDENCE_SEPARATION | PASS；NOT_NEEDED |
| ARTISTIC_FEASIBILITY_GATE | PASS；UNKNOWN，不越权接受 |
| DURATION_DRIFT_DIAGNOSTIC | PASS |
| UPSTREAM_CAUSE_DIAGNOSTIC | PASS |
| REALIZED_PERFORMANCE_BOUNDARY | PASS |
| MOUTH_UNKNOWN_SAFETY | PASS |
| SLACK_REALLOCATION | PASS |
| REACTION_PROTECTION | PASS |
| RECONCILIATION_CONTRACT | PASS |
| FINGERPRINT | PASS |
| STALE_INPUT_REJECTION | PASS |
| NO_PROVIDER_CALLS | PASS |
| NO_DOMAIN_WRITES | PASS |
| REGRESSION | PASS |
| COMPLEXITY_AUDIT | PASS |

**Batch 7.4B Phase A=PASS**。当前 Shot 的 full realized physical feasibility 为 FEASIBLE；艺术兼容性仍 UNKNOWN，用户 Timing Review 必须先于任何 accepted timing 或重建。

**STOP BEFORE TIMING ACCEPTANCE / AVSYNC / FINAL SHOT REBUILD**
