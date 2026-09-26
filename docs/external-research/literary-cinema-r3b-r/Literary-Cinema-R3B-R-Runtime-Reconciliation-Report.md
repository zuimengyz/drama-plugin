# Literary Cinema R3B-R — Runtime Reconciliation Report

2026-09-26 · RUNTIME BUGFIX / RECONCILIATION · SELF_AUDIT。

**FP01 / FP02 已修复；同一 R3 候选的两个语义阻断已解除。** 三场 source dramaturgy、六轴审阅与 mapper 通过，15/15 exact-turn 通过。没有修改、adopt 或批准剧本。S03 新审阅收据使旧 Director pin 失效；本轮保留并报告 `STALE_DIRECTOR_DRAMATURGY`，不重写 Director candidate 或 projection。

## Baseline

实际起点 HEAD：`df625f9d01cc62c3f1ffed2774e88166ab37bae5`。工作树仅已有未跟踪的 R3D-A 报告目录及 `.DS_Store`，无既存 Runtime diff。重新读取 R3C Creative / Directorial Performance / Anti-Gate-Drift 报告、R3D-A Final Findings，并核对当前源码而非沿用报告行号。

检查范围包括 `screenplay_playability.py`、`scene_dramaturgy.py`、`performance_direction.py`、`hosts/formal_performance.py`、`performance_coverage.py`、`preproduction.py`，以及 DPD、playability、dramaturgy、Director 的现有合同和 R3B / screenplay 测试。实际责任点是前两个文件，其余调用链无需修改。

[baseline-integrity.json](baseline-integrity.json) 在修改前冻结 1,062 个既有文件。原始 R3C `08-run-gates.py` 会回写 Director candidate，因此没有执行这个写入入口。本轮新增只读入口 [r3b_r_recheck.py](../../../plugin/tests/r3b_r_recheck.py)，对同一外部候选分别加载基线两个模块和修改后 Runtime。原始 [candidate-before.json](candidate-before.json) 复现两个阻断；[candidate-after.json](candidate-after.json) 保留所有实际返回值和负例结果。

## FP01 Root Cause

原判断仅凭 `_VOCATIVES.fullmatch(text)` 拒绝所有可理解称呼式文本，没有区分呼叫本身和未说出的求助请求。S02-L7-new 的 exact text / speaker / target / DPD 均正确，仍被拒绝。

当前 source 的 intent、LineDPD.dramatic_action、literalMeaning 都是 `叫住新出现的求助对象`。source target 为 `另一行人`，Scene.characters 包含此对象。相同 Beat 的源定位包含 `action:368:379` 与 `spoken:S02-L7-new`，后者 cause_ref 指向前者，双方 actor / target 与该 turn 相同。

## FP01 Fix

复用当前 exact-turn、Scene hash、DPD composition、speaker、target、intent 和源载体验证。在原称呼歧义分支增加窄范围 contextual-call 判断：

- approved source intent 与 LineDPD action 已精确一致；action 必须是精确匹配的 calling vocabulary，literalMeaning 也必须与该 action 一致。
- 使用 `get_attention`、`call_to_target`、`call_after_target`、`interrupt_target`、`identify_addressee`，并保留现有中文行动值 `叫住新出现的求助对象` 的精确兼容。没有对子串、objective 或对白做 NLP 分类；含追加请求的复合行动不会匹配。
- 文本是单一连续呼叫形式；必须为 CONTINUOUS，不能把旧碎裂称呼借此合法化。
- 目标明确、不是说话人且在当前 Scene.characters；同一 Beat 必须覆盖该 turn 及其源中已声明的前置 encounter action，且 actor / target、cause_ref、源顺序与源 hash 均一致。

现有 action 是自由文本，当前代码没有可直接消费的 speech-act enum。采用六个精确行动值足以处理本轮边界；未增加 schema、intent enum 或创作实体。中文兼容值是对既有 approved action 的窄判定，不是对白文本白名单，不依赖 S02、女孩、先生等 id 或身份。未知措辞仍保守拒绝称呼例外，不进行语义猜测。

**S02-L7-new 的 PASS 仅表示它作为 contextual call/get-attention action 可成立，不表示完整求助已在这句话表达。** 妈妈出事、请跟随等信息仍由其它源 turn 承载，本修复不会为当前句添加任何信息 release。

## FP01 Positive / Negative Cases

[test_r3b_r_dialogue_vocative.py](../../../plugin/tests/test_r3b_r_dialogue_vocative.py) 覆盖：明确 action / target / encounter 的“先生！”、“喂！”、“妈妈！”、“约翰！”；示例词没有被追加到生产词法规则。

负例包括 medical-help、persuade-follow、包含 get_attention 的复合请求、旧“妈妈……先生，妈妈……”、缺目标、多候选但未绑定、目标不在场、DPD 错目标、encounter 错目标、无 encounter / source facet、相同文字交换 turn，以及 literalMeaning 偷带完整求助。全部仍拒绝。完整句式不因 action=get_attention 被一概当成称呼式空句。

## FP02 Root Cause

原审阅将所有 `important + ACTION + target` 统一要求出现在 interpersonal interactions 中，而 source interaction 验证又明确要求两个不同 actor。S03-L1 的 `target=自己` 因而无法在不虚构听者的情况下满足 Gate。

## FP02 Fix

只在现有 important ACTION 缺 interaction 的分支内判断明确身份：actor==target，或既有反身标签 `自己` / canonical `SELF`。若字符名恰好就是 SELF / 自己，则优先按真实角色身份处理，不将它当别名。AUDIENCE、VOICE_OVER、DIRECT_ADDRESS 均不属于该范围。

自我定向不能裸豁免：同一当前 DPD Beat 必须包含该 action，并绑定后面的同一 actor / self target 的 AFTERMATH、REACTION 或非环境 SILENCE，且有 objective / tactic。后续载体必须严格晚于 action；若 source 指定 cause_ref，不能与该 action 冲突。当前 ACTION_RESPONSE_CHAIN 的 PASS 审阅必须明确用 evidence_refs 同时覆盖 action 与 continuation。缺任一条件产生 `SELF_DIRECTED_CONTINUATION_REQUIRED`。

本轮复用已有 source-owned carrier、DPD action→reaction witness 及 current review，没有为自语创建 interpersonal edge，也没有从自然语言 reason 自动识别“无需回应”特批。没有自己的后续见证时仍返回审阅；未增加新的 waiver contract。

S03-L1 原 DPD 已定位到 `action:207:221`：“身体向桌前靠了一点，又停住。” 原 current review 覆盖此载体与台词，足以检查 self continuation。袖、手、咳嗽、门把和未开门均维持原 source / DPD 关系。

## FP02 Positive / Negative Cases

[test_r3b_r_self_directed_action.py](../../../plugin/tests/test_r3b_r_self_directed_action.py) 检查 自己 / SELF / actor==target；“走。”后自己起身离开、“别回头。”后继续前行，以及原 S03-L1。

负例包括相同文字改向另一个人物、缺 DPD、把当前 utterance 自己当后续行为、无任务、审阅缺所需证据/有 concern、后续行为有其它 cause、SELF→OTHER 后旧审阅、audience/voice-over/direct-address，以及伪环境 response。`source_dramaturgy` 的 interpersonal listener / response-role 检查完全未改；缺第二人的真实回应仍为 `IMPORTANT_ACTION_RESPONSE_MISSING`。

S03 `causalCoverage` 仍为空，因为它记录 interpersonal edges；不是将 self continuation 漏当回应，也没有把两次咳嗽算成 listener response。原 source、DPD 与 review 仍可定位自己的 continuation。环境载体不能给伪造的 interaction 或 self witness 填空。

## Changed Runtime Files

仅修改：

1. [screenplay_playability.py](../../../plugin/src/drama_plugin/screenplay_playability.py)：contextual call 范围判断。
2. [scene_dramaturgy.py](../../../plugin/src/drama_plugin/scene_dramaturgy.py)：self-directed continuation 的审阅范围判断。

新增三个专项测试文件、两个测试/审计 helper，以及两份逐字复制的冻结候选 JSON。冻结副本位于 tests/fixtures/r3b_r；测试只修改内存中的副本，原 artifacts 文件不写入。没有 Contract、DPD / Director 架构、Provider / MCP / Service / Storage、Prompt Generator 或 Skill 修改。

## Authority Boundary

Scene 仍拥有已发生事实、载体身份和顺序；DPD 仍拥有人物任务与后续表演见证；专业 review 仍拥有艺术判断。Runtime 只验证这些当前声明是否满足适用条件，不补信息、不创作回应、不判断表演艺术质量。

SELF_AUDIT 不是独立评审或用户批准。旧 artifact 可重放，不自动取得新 formal readiness。exact source / speaker / target / spoken_content_id / DPD / Director / projection 的 hash 与身份校验未删除或放宽。

## R3C Candidate Recheck

使用外部同一份 screenplay、sidecar 和 Director candidate，未重新生成创作 artifact。

| Gate | Before | After |
|---|---|---|
| S01 source / dramaturgy / mapper | PASS / PASS / ready=true | 相同 |
| S02 source / dramaturgy / mapper | PASS / PASS / FP01 exception | PASS / PASS / ready=true |
| S03 source / dramaturgy / mapper | PASS / CONCERN FP02 / ready=false | PASS / PASS / ready=true |
| validate_exact_turn | 14/15 | 15/15 |
| validate_turn_direction，保留原记录 pins 的 replay | 14/15 | 15/15 |
| validate_turn_direction，当前重新计算的审阅收据 | 14/15 | 13/15；S03 两句 STALE_DIRECTOR_DRAMATURGY |
| validate_intent，当前重新计算的审阅收据 | 15/15 | 13/15；同上 |
| listener / silence 源内局部审阅 | 三场两轴均 PASS | 三场两轴均 PASS |

S03 concern 被正确移除，receipt fingerprint 自然变化；Director candidate 仍 pin 旧收据。因此新正式方向链必须重新绑定并审阅，不能用旧 current 映射掩饰。**本轮未更新这个候选，未伪称全链当前 readiness PASS。** 回归测试明确要求它继续报 stale。此项是旧收据的正常失效，不是 FP02 仍未解除。

没有 formal adoption、当前正式 Scene/Shot 全树或完整 Book inputs，因此没有冒充 `FormalSourceWitness`，没有运行/宣称正式 Book completion PASS。局部 listener / silence 校验来自真实 `review_scene_dramaturgy` 的源/DPD/六轴检查，不是 formal full-film coverage。

## R3C Recheck Matrix

| Item | Before R3B-R | After R3B-R | Expected | Result |
| ---- | ------------ | ----------- | -------- | ------ |
| S02-L7-new contextual vocative | AMBIGUOUS_DIALOGUE | PASS | 仅呼叫有效 | PASS |
| S03-L1 self-directed action | IMPORTANT_ACTION_RESPONSE_MISSING | 无该 concern；Scene PASS | 自己的后续见证有效 | PASS |
| old ambiguous dialogue | AMBIGUOUS_DIALOGUE | AMBIGUOUS_DIALOGUE | 继续失败 | PASS |
| missing target | UNRESOLVED actor/target | 同前 | 继续失败 | PASS |
| wrong target | DIALOGUE_TARGET_MISMATCH | 同前 | 继续失败 | PASS |
| interpersonal missing response | CONCERN / IMPORTANT_ACTION_RESPONSE_MISSING | 同前 | 继续失败 | PASS |
| fake environmental response | STIMULUS_IS_NOT_ACTUAL_RESPONSE | 同前 | 继续失败 | PASS |
| exact-turn binding | EXACT_DIALOGUE_TURN_MISMATCH | 同前 | 继续失败 | PASS |
| empty medical / follow request | AMBIGUOUS_DIALOGUE | AMBIGUOUS_DIALOGUE | 继续失败 | PASS |
| S03 原 Director pin 对新收据 | 旧收据匹配 | STALE_DIRECTOR_DRAMATURGY | 保持严格版本边界 | PASS |

## Regression Tests

验证命令及结果见 [validation-summary.json](validation-summary.json)。测试不调用媒体生成或付费 provider。

- 新专项 53 项（含 frozen candidate 集成）加 R3B、原 screenplay playability 87 项：**140 passed**，见 [focused-tests.txt](focused-tests.txt)。
- 全库 pytest：**2835 passed**，见 [full-pytest.txt](full-pytest.txt)。
- 变更 Runtime 与全部新增 Python 文件严格 mypy：**7 files，0 errors**，见 [mypy-focused.txt](mypy-focused.txt)。
- 全库 mypy 前后均为 40 errors / 13 files / 203 source files；逐条比较错误文本，本轮新增 **0**、移除 **0**。未修复无关历史问题。原始 [before](mypy-before.txt)、[after](mypy-after.txt)。
- `git diff --check` 与新增文本空白检查通过。

## Source Integrity

[integrity-verification.json](integrity-verification.json) 证明 1,062 个起点文件中仅上述两个 Runtime 文件改变，其余 1,060 个未变，意外变化 0。覆盖原 R3 目录、R3D-A 报告、plugin 源/测试/skills，以及 MCP / Service 已跟踪文件。Provider 与 Prompt 源包含在冻结范围中。

| Protected input | SHA256，前后相同 |
|---|---|
| R3 screenplay | `39a1f9fa35d1e1becbeac667b911dfb9ab2e0dbaef6fb10e8335044fc0aadb3f` |
| R3 sidecar | `90ceeda49fee4542c1cb08b482bc9deb23fc6d4945690fdaddd26c876356a1a6` |
| R3 Director candidate | `4f1033e73234c5ae5dddbbb630694502e24250f4f9e4d1798c2debe6c94187ef` |

screenplay hash 与 R3C Creative Review / 原冻结记录一致。新增测试中的两份候选 JSON 与外部原件逐字一致，不是重新创作的版本。

## Known Gaps

1. Calling vocabulary 有意保守：不是任意语言、任意专名或任意 action prose 的自动语义理解器。未知称呼与行动改写仍需专业判断；本轮没有扩大到 NLP / intent taxonomy。
2. Self continuation 必须有现有 DPD 与 review 证据；没有“仅 target=SELF 就 PASS”的 fallback，也没有新造 no-response waiver。
3. S03 旧 Director receipt pin 的重新绑定/审阅仍待后续授权阶段；本轮遵守候选冻结，没有隐藏 stale 或重写指纹。
4. R3C 仍 NOT_ADOPTED；艺术审阅、formal Book、独立评审和媒体观察未完成。测试证明规则边界，不证明文学或成片质量。

## Mandatory Status

```text
FP01_CONTEXTUAL_VOCATIVE_FIXED = YES
FP02_SELF_DIRECTED_ACTION_FIXED = YES

VOCATIVE_OVERPERMISSIVE_REGRESSION = NO
INTERPERSONAL_RESPONSE_GATE_WEAKENED = NO

R3C_SCREENPLAY_UNCHANGED = YES
R3C_SIDECAR_UNCHANGED = YES
R3C_DIRECTOR_CANDIDATE_UNCHANGED = YES

R3C_S02_RUNTIME_BLOCKER_RESOLVED = YES
R3C_S03_RUNTIME_BLOCKER_RESOLVED = YES

PROMPT_GENERATOR_CHANGED = NO
R3D_RUNTIME_STARTED = NO
PAID_GENERATION = 0

NEW_TOP_LEVEL_SKILLS = 0
NEW_CANONICAL_CREATIVE_ENTITIES = 0
READY_FOR_LITERARY_CINEMA_R3D = YES
```

READY 仅表示本轮指定的两个 Runtime blocker 已和负例边界完成核对。**不表示 R3C_CREATIVE_REVIEW_PASS、剧本 adopted、当前 Director 全链通过或 READY_FOR_SEEDANCE_A5。** R3D 之后仍须 R3C-R 使用批准的解释对 S01–S03 重新审阅/修订。

**STOP：本轮不启动 R3D、R3C-R、A5，不生成媒体。**
