# Literary Cinema R3B — Gate Evidence

日期：2026-09-26；基线 HEAD `bb83843074ae685a5fdd53ed94b1a27bd863a014`。本报告记录离线确定性结构测试和明确标记的诊断 fixture。所有艺术判断都是 source-bound 自审证据，没有独立观众、演员或媒体质量实证。

## Test Status

| 检查 | 修改前 | 修改后 | 结论 |
|---|---|---|---|
| 新增 `test_literary_cinema_r3b.py` | 无 | 52 tests passed，包含参数化反例 | PASS |
| Focused regression | — | 371 passed in 5.98s | PASS |
| Full regression | 2730 passed in 120.96s | 2782 passed in 119.19s | PASS；增加 52 |
| mypy strict 全库 | 40 errors / 13 files / 201 source files | 同一 40 条错误 / 13 files / 203 source files | 全库未通过；本轮新增错误 0 |
| git diff --check | — | exit 0 | PASS |
| 当前创作源 hash | 修改前冻结 22 文件 | 22/22 相同 | PASS |
| Provider/Prompt/Skill 等受保护文件 hash | 修改前冻结 264 文件 | 264/264 相同 | PASS |

执行目录：`/Users/zy/historical-plugin/drama-plugin/plugin`；解释器：`/Users/zy/historical-plugin/drama-mcp-service/.venv/bin/python`。

```text
python -m pytest -q
python -m pytest -q tests/test_literary_cinema_r3b.py tests/test_screenplay_playability.py tests/test_pre_r1_remediation.py tests/test_creative_source.py tests/test_full_performance_coverage.py tests/test_cross_modal_performance.py tests/test_dpd_core.py tests/test_seedance_prompt_generator.py tests/test_production_language.py
python -m mypy src/drama_plugin
git diff --check
```

可核对证据：[validation.json](validation.json)、[source-integrity.json](source-integrity.json)、[diagnostic-receipts.json](diagnostic-receipts.json)。完整 pytest 摘要与 mypy 基线/最终诊断保存在本目录 validation 文件夹。Mypy 的既有问题涉及 characters、visual、character_package、performance_casting 等文件，不隐藏为本轮 PASS。

第一轮全回归曾有 12 failed / 10 errors，均由新 preservation 要求暴露：10 项历史已批准资产校验需保留精确 replay，12 项合成语言测试需要新增保护事实证据。已修复并全量重跑；这些不是基线失败。

## Synthetic Good and Bad Cases

下表 actual 指对应测试已执行的返回状态或抛出拒绝；反例被拒绝时 result=PASS 表示 Gate 行为正确，不表示坏输入可用于生产。

| Case | Expected | Actual | Gate / repair owner | Result |
|---|---|---|---|---|
| action → expected → actual refusal → next tactic | trace 可重放且输入不变 | PASS；2 条 causalCoverage；expected 与 actual/interpretation 独立 | Scene 事实、DPD 解释 | PASS |
| 动作存在但删除 response edge | 不准用散落动作代替因果 | `DPD_INTERPRETATION_NOT_SOURCE_INTERACTION` | Scene | PASS |
| expected_response=`respond` | 不因非空就通过 | CONCERN / GENERIC_EXPECTED_RESPONSE | DPD | PASS |
| strategy change 无 transition reason / next beat | 需要实际回应到下一策略 | CONCERN / RESPONSE_TO_NEXT_TACTIC_REQUIRED | DPD | PASS |
| 两个 tactic 字符串不同却指回原 beat | 不等于真实策略升级 | CONCERN | DPD | PASS |
| source `raise hand. withdraw hand.`，witness 逆序 | ORDER MISMATCH | ordered carrier 校验拒绝；两者 substring 存在也不能通过 | Scene / DPD witness | PASS |
| 源 carrier 数组倒置 | source order mismatch | SOURCE_TEMPORAL_ORDER_MISMATCH | Scene | PASS |
| sees passerby 是跑向路人的 trigger，却放到 reaction slot / 反指后行动 | fail / unresolved | TRIGGER_REACTION_ORDER_MISMATCH 或 reaction-role 拒绝 | Scene / DPD witness | PASS |
| 首次接触便释放所有重要信息，后面才聆听 | literal 可 PASS，dramaturgy concern | DRAMATICALLY_PREMATURE | Scene | PASS |
| 选择发生前某角色尚未得到所需信息 | 对称 late concern | DRAMATICALLY_LATE；按受众分别计已知 parts | Scene | PASS |
| 充分上下文下直接说“火车十分钟后开。” | 不强迫先制造阻力 | PASS；允许 direct_statement_reason | Scene | PASS |
| A 提问 → B 拒绝回答 → A 改变行动 | non-response 不可因无对白遗漏 | 完整 trace PASS；删除 listener DPD 后 CONCERN | Scene / DPD | PASS |
| 环境安静 | 不自动发明角色心理 | 无 actor 的 ENVIRONMENT 可以通过；添加 actor psychology 拒绝 | Scene | PASS |
| 漏掉 listener refusal 或用同一 listener 的另一反应替代 | fail | LISTENER_RESPONSE_DPD_REQUIRED 或 interaction-source mismatch | DPD / formal Host | PASS |
| review hash 过期 / 证据引用不存在 | fail | stale/unbound review 拒绝 | 原 review owner | PASS |
| 同一 author/reviewer 自称 independent | fail | INDEPENDENT_REVIEW_REQUIRES_DISTINCT_READER | Review | PASS |

## Exact Turn / Director / Book Evidence

| Case | Expected | Actual | Gate owner | Result |
|---|---|---|---|---|
| 3 个合成正式 Scene，各 2 个关键 interaction | 必须枚举 6 个 interaction | 6 条精确源 obligations；遗漏一条不 ready | FormalSourceWitness | PASS |
| 同场合法 Line1→DPD2、Line2→DPD1 | 即使双方都被覆盖也拒绝 | EXACT_DIALOGUE_TURN_MISMATCH；实际 Book NOT_READY | Formal Host / Book | PASS |
| A:“是。”、B:“是。” | 相同文字不能互换 speaker | 原 turn swap 和伪改 line id 分别被 exact-id / speaker 校验拒绝 | Exact source binding | PASS |
| 同一句“走开。” target GIRL vs FRIEND | 不能仅靠 text 相同通过 | target/source 校验拒绝 | Exact source binding | PASS |
| coverage target_ref 指向另一 listener | fail | 目标身份不一致拒绝 | Formal Host | PASS |
| 改 dialogue / target / DPD / Scene | 旧 Director intent/projection stale | 各参数化测试拒绝 | Director binding | PASS |
| 伪改 intent turn map / projection turn hash | fail | current turn fingerprint mismatch | Director / Projection validator | PASS |
| Director 漏掉 listener DPD scope | fail | 实际 Book NOT_READY | Book | PASS |
| 缺 dramaturgy review | 不得 fallback legacy | FORMAL_DRAMATURGY_REVIEW_REQUIRED；Book NOT_READY | Formal Host / Book | PASS |
| 有非 PASS 信息 finding | 不得 coverage 总数掩盖 | Book NOT_READY，保留 repair owner finding | Book / Scene | PASS |
| 完整 source / DPD / Director / projections / score / self-review | 可以交用户审阅，但不授权生产 | DIRECTOR_PRODUCTION_BOOK_READY_FOR_USER_REVIEW；productionAuthorized=false | Book | PASS |
| 风险标记却 STANDARD | 应要求 EXPANDED | DIRECTION_DENSITY_REQUIRES_EXPANDED | Coverage | PASS |
| STANDARD 复用同场共享表达 | 不复制心理身份 | 表达继承，exact objective_ref 保持本 turn；不改输入 | Coverage | PASS |
| Director 新增 objective/subtext；Performance 新增 subtext/dialogueIntent | 越权拒绝 | typed extra fields 拒绝 | Existing contracts | PASS |
| 新改编保护项 CONCERN 或缺失 | fail closed | SOURCE_CRITICAL_PRESERVATION_UNRESOLVED / PRESERVATION_REVIEW_REQUIRED | literary-adaptation | PASS |
| 旧无 receipt 输出精确 replay | 仅允许旧完整性校验；新编译不能沿用 | verify PASS；公开 compile 拒绝；tampered compiled 拒绝 | creative_source | PASS |
| 上游 PASS 后投影 approved visible carrier | Prompt 仅翻译批准结果 | 原可见事实出现、actor objective 不被偷偷添加；输入不变 | Existing Seedance generator | PASS |
| Prompt 中只有 sad，无批准可见载体 | 不得自动补低头等动作 | UNRESOLVED:performance:OBSERVABLE_CARRIER_REQUIRED | 原 Performance owner | PASS |

## S01 Diagnostic

Expected：楼梯处停留、无人叫住、继续离开可以形成意义链，不以缺对白判错。

Actual：**PASS**。保留原 5 个 spoken turns；等待/离开和环境无人回应由原文 carrier 定位。没有新增 dialogue、人物目的或第二 Canon。这里不是两人交谈 interaction，故 `causalCoverage` 不伪造双人 response，而以 silence/source cause/DPD witness 验证。

Gate owner：Scene 标记事实/静默因果，DPD 提供已有源人物任务；正式 adoption 不在本轮。

## S02 Diagnostic

Expected：原话不变；完整请求在延迟聆听/误判之前释放，应形成 Scene concern，而非改成 Dialogue wording/Prompt repair。

Actual：**CONCERN**，`DRAMATICALLY_PREMATURE`，repairOwner=`scene-development`。保留原 4 个对白 turn 及文字；4 条 source-bound interaction receipt。人工专业 finding 与机器窗口校验各留一条同概念 finding，二者证据不同，不是两个新事实。

Diagnostic 序列直接锚定原文：看星星 → 接触/半停 → 完整请求 → 拉动 → 延迟聆听/误判 → 重复请求 → 撤手/推拒 → 再抓 → 拒绝/后退 → 看到行人作为下一行动 trigger → 跑向行人 → 男人入门。没有生成替代对白或改变次序。本轮只让早释 concern 可检测和路由，保留待 R3C 的创作问题。

## S03 Diagnostic

Expected：袖口、手、咳嗽、门把、未开门可以保留压力悬置，不强迫角色发言、开门或采取帮助行动。

Actual：**PASS**。原 3 个对白 turn 与动作原文保持；stimulus/hesitation/withdrawal 使用源 witness，未消解未决压力。没有为了构造传统 opposition 新增人物互动。

Gate owner：Scene source chain / DPD；判断具体电影效果留给 R3C。

## Dream / Nontraditional Diagnostic

选择 S04 坟墓等待水滴的**有界原文片段**，不是全场重建。

Expected：主观未知/非传统因果在明确 suspension_reason 下允许，不制造现实对手、解释或心理动作。

Actual：**PASS**。water arrives / does not / arrives 的环境载体，entry==exit 的 subjective unknown 有源诊断理由，DPD 数量为 0；无需给环境赋予 actor objective。本结果只覆盖该片段。

## Boundaries and Outcome

所有 diagnostic 输入在内存中构造 sidecar，测试验证调用前后输入相等；当前 creative 根目录 22 个文件逐字节 hash 未变。R2 正文 SHA256：`dae155c1d27e6091d8277e773fa22e1ca20b549e6a3e936322256a246b425c08`。没有采用新稿、没有独立审阅者假声明、没有媒体实证、没有收费调用。

P0 工程门槛通过：exact turn/speaker/target、stale Director、明确源顺序、action/response、information concern→Scene、listener/silence 缺口检测均进入正式 Book。`READY_FOR_LITERARY_CINEMA_R3C = YES` 仅授权下一轮人工创作审阅的准备状态；本轮未开始 R3C，也不代表 Seedance A5 readiness。
