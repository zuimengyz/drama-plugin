# Screenplay R2 — Implementation Report

Runtime、既有 Skills、前三场候选及回归 fixture 已修改。**READY_FOR_SCREENPLAY_R2_CREATIVE_REVIEW**；未采纳到正式 Work／Scene，没有批准新生产，没有执行 Still／Seedance A5。

基线与终检 HEAD：`287493c6bb1099eb6d70f4cfe1a5bc1b9bbb43cd`。工作树保留未提交变更；已有 `docs/external-research/.DS_Store` 未触碰。此前 A3/A4 Seedance 工作已在 HEAD 中，本轮不改变它。

## Deliverables

- [16 场／64 个检查点的可演性审计](Screenplay-R2-Playability-Audit.md)
- [Performance Intent / Dialogue Intent 契约与权威](Screenplay-R2-Performance-Intent-Contract.md)
- [S01–S03 OLD → NEW 及完整差异](Screenplay-R2-S01-S03-Rewrite.md)
- [完整 R2 可读候选](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/screenplay-r2/04-screenplay-r2.md)
- [结构化 performance sidecar](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/screenplay-r2/performance-sidecar.json)

候选正文只重写 S01–S03，并修改版本标题；S04–S16 原样复制。R1 两份源档保留原有指纹，不破坏已引用原件。10 个 actor Beat、12 条逐字对白与当前源动作绑定。没有新 Actor／Director／Canon；sidecar 用本地角色称谓，不能冒充正式 Speaker 或已审批 Scene。

## Changed Runtime Files

| File（相对仓库） | 实际变化 |
|---|---|
| plugin/src/drama_plugin/contracts/screenplay_playability.py | 新增 BeatPlayability / LinePlayability 最小 source/carrier/review witness；动作复用 ObservableAction |
| plugin/src/drama_plugin/contracts/dpd.py | 既有 BeatDPD / LineDPD 加可选嵌套 witness；缺省序列化省略，保持旧哈希 |
| plugin/src/drama_plugin/screenplay_playability.py | 实际 screenplay → performance mapping、源哈希／载体／任务／逐字对白／fragment Gate |
| plugin/src/drama_plugin/hosts/formal_performance.py | 既有正式 Performance Book 审阅入口强制 playability 与对白覆盖检查 |
| plugin/src/drama_plugin/performance_direction.py | CinematicShotSpec handoff 对 R2 绑定额外核对源对白 exact hash 与 target |
| plugin/tests/test_screenplay_playability.py | 35 项正反例与真实正式 Gate／Cinematic handoff 回归 |
| plugin/tests/formal_performance_helpers.py | 为现有正式离线 fixture 明确补作者给定的 target/tactic/delivery/carrier；无生产自动默认 |
| plugin/tests/fixtures/screenplay_r2/ | 保留 R1、R2 和源绑定 sidecar，测试可独立复跑 |

Runtime 变更不止文档。共享架构通过现有正式 Gate 接入，没有新 provider、route、MCP endpoint、Service 或 Storage。没有改动 `prompt_generators/`、`providers/`、`tools/`；git diff 对这些路径为空。

## Contract Changes

复用 SceneDPD 的 purpose，BeatDPD 的 actor/objective/target/tactic/obstacle/transition_trigger，LineDPD 的 intent/continuity/change，现有 DPD subtext。补 current-beat 状态、可见／可听动作载体、反应、审阅证据；没有平行的心理权威。状态 scope 固定 CURRENT_BEAT，结构不允许 identity、Camera、Lighting 或替换 Dialogue 字段。导演全局表达与仲裁未变。

Dialogue 的 text、speakerKey、intent、performanceIntent 仍位于 spokenContent；新正式审阅要求明确 target。Line witness 只保存 exact text hash、literal meaning、speakability review、fragment purpose。汉字、标点、停顿符号都是 exact text 的一部分，不做 normalize／同音替换／拼接。

## Skill Changes

修改现有 12 个 Skill，均指向 `plugin/docs/screenplay-playability.md`：
work-creation、cinematic-screenplay-incubation、script-adaptation、scene-development、character-dramaturgy、dialogue-design、director、dramatic-performance-direction、character-embodiment、blocking、action-choreography、cinematic-direction。

分别明确上游意义、剧本可演载体、对白可说性、当前状态和稳定身份、空间／力学权限、Director 保留权与 generator 非创作边界。修正 DPD 旧的 “Keep the existing DPD schema unchanged.” 为允许本轮最小 witness 增量，保留 DPD 作为唯一表演心理投影。未新装 Skill；共享规范不是第二个 Skill。现有 dialogue content convention 增补新正式审阅所需 target 和证据。

## Mapping Changes

`map_screenplay_performance` 的输入是同一当前 Scene 和作者提供的既有 DPD 层。关键任务不全即 UNRESOLVED；不做默认动作，不由情绪推演目标。可见行为和反应必须在 screenplayAction 中有原文载体；说话本身作为动作时只允许取同一演员的 canonical spokenContent。输出复用已有 BeatDPD / DPDSnapshot 与源对白深拷贝。

S01 以否定争论、收杯取衣、停在楼梯听为当前任务；S02 girl 的请求与 man 的推辞／爆发分开，女孩退开后继续求助；S03 备枪、手的回声、门把、回桌不拿枪形成可执行的冲突。手部回声及不把低声推辞演成入场恐吓的约束在 sidecar 中，不变成旁白或固定模型提示词。

## Validation / Gate Changes

- 重要 Beat 必须显式知道 actor、objective、target、tactic、action、current state、turn、reaction；已知纯情绪标签不能替代任务或动作。
- Source scene hash、carrier 和 composed snapshot 必须一致；包括重新校验 model_copy 产生的嵌套 witness，不能用对象复制跳过 fragment 必填目的。
- 每条 source dialogue 在 mapping 恰好一次，缺失／重复不能通过；speaker、target、intent、delivery、subtext 均有绑定，文本必须逐字一致。
- 旧 S02 称谓碎片是 AMBIGUOUS_DIALOGUE；正常急促片段可通过。故意不可理解单列，必须有明确戏剧目的，不替代 S02 本轮的传达求助要求。
- 正式 Performance Book 读取当前 Canon 后校验所有绑定 DPD 和 spoken inventory，不把缺项交给 Prompt Generator。
- Cinematic handoff 即使 audio 与 spec 同时换成同一句新词，也会因为不符原 witness 拒绝。更换 target 同样失败。

## Tests

全部测试均为离线确定性 fixture / mock，无生成调用。

1. 完整 `python -m pytest -q plugin/tests`：**2725 passed in 139.28s**。
2. 随后针对对象复制绕过校验与下游文本／target 对应补强，再跑 `test_screenplay_playability.py`、`test_dpd_core.py`、`test_pre_r1_remediation.py`、`test_cross_modal_performance.py`：**143 passed in 1.39s**。其中新 R2 测试共 35 项。未把这次定向结果冒称为重跑全量的 2730 项结果。
3. 5 个修改／新增 Runtime 文件用 `mypy --config-file plugin/pyproject.toml --follow-imports=silent` 严格检查：**Success**。
4. 12 个修改 Skill 均运行 skill-creator 的 `quick_validate.py`：**12/12 valid**。该检查仅验证 Skill 格式，不证明艺术质量。
5. `git diff --check`：通过。旧 DPD 固定 fingerprint fixture 全部保持，说明缺省新字段没有破坏重放。
6. 对照文件验证：两份 R1 同原哈希；R2 S04–S16 字节相等；artifact 与 repo fixture 内容相等；12 条对白逐行等于 screenplay 原文。

复现命令（在仓库根目录，Python 使用项目虚拟环境）：

```sh
/Users/zy/historical-plugin/drama-mcp-service/.venv/bin/python -m pytest -q plugin/tests/test_screenplay_playability.py plugin/tests/test_dpd_core.py plugin/tests/test_pre_r1_remediation.py plugin/tests/test_cross_modal_performance.py
```

## Legacy Reconciliation

旧 dpd-v1 仍可读取／重放，未填 witness 不输出空字段、保留原 fingerprint。新正式审阅需要返回 owner 源绑定补齐，不自动迁移或伪造可演性。旧 R1 女孩对白作为拒绝 fixture 留存，不作为新候选生产对白。Screenplay candidate 与正式已采用 Canon 分离：未来人工采纳后重新绑定真实 IDs／SourcePins，不能直接改 status 宣称已采用。

## Known Gaps / Review Boundary

- 自动检查证明结构和源绑定，不证明自然语言的全部含义、表演效果或艺术成熟度。情绪词／称谓串只覆盖明确反例；自由文本中的隐性改意、Camera/Lighting 越权描述仍须作者／专业审阅。无生成实证。
- S04–S16 已审计但未改写／未补全正式 DPD；间接引语、演唱内容、故意语义断裂、梦的声音变化等仍有后续专业缺口。不能用前三场通过测试宣称整部电影已可生产。
- 当前新稿及 sidecar 都是待人工审阅候选，尚未写入正式 Work／Script／Scene，未更新人物仓库 source pins。没有改主线或引入第二 Canon。
- 本轮仅更新源码和本地创作候选，不发布／重新安装插件，不进入 Still / Seedance A5。

## Integrity / Final Status

R1 source SHA-256：`11d0f82f18f7defa31a9a4abe0de12e061cdc62183e3744c2b607dc1c19428e1`。

S04–S16 受保护字节 SHA-256：`5708e651b5a1557b9426f346526e5fd15ecdcd3480d63119713f0dafa02ca713`。

R2 candidate SHA-256：`dae155c1d27e6091d8277e773fa22e1ca20b549e6a3e936322256a246b425c08`。

```text
SCREENPLAY_PLAYABILITY_RUNTIME_IMPLEMENTED = YES
PERFORMANCE_INTENT_IMPLEMENTED = YES
DIALOGUE_INTENT_IMPLEMENTED = YES
AMBIGUOUS_DIALOGUE_GATE_IMPLEMENTED = YES
S01_S03_REWRITTEN = YES
S04_S16_UNCHANGED = YES
PROMPT_GENERATOR_REMAINS_NON_CREATIVE = YES
PAID_GENERATION = 0
READY_FOR_SCREENPLAY_R2_CREATIVE_REVIEW = YES
```

执行结束，等待人工创作审阅；未执行任何图片、视频或音频生成。
