# 15-真实 Creative E2E 与质量回归执行报告

## 1. 执行摘要

本批在不修改生产 Skill、Tool Contract、Drama MCP Service、Java Service、数据库结构、ContextBuilder、Harness、Asset、Media 或 Generation 的前提下，完成了一条真实历史短剧创作链：

```text
Agent Host
→ Drama MCP（44 tools）
→ Java Service
→ MySQL
→ stable-ID reload
```

测试题材为第三题材“苏武北海十九年”，新建并保留了 1 个 Work、1 个八集 Script、1 个代表 Episode、3 个连续 Scene、1 个 Scene 的 10 个完整 Shot。所有 16 个实体均通过稳定 ID 从 MCP 重新读取，父子关系完整，过程性 Plan / Draft reasoning / Review notes 未进入 Java Domain Content。

真实运行还发现并验证了修订闭环：独立第二轮 Shot Review 发现 5-2-04 与 5-2-05 的酒碗持有连续性冲突；Agent 局部修订 5-2-05，重新 Review 后用 `shot.save_shot` 更新已有正式对象，再次回读成功。

总体结论为 **PARTIAL**，不是因为创作或持久化失败，而是当前 Codex Host 注册的插件缓存仍是 `0.1.0+codex.20260812052808`，五个核心创作 Skill 的哈希与工作区 Batch 1～3 最新版本不同。工作区新版 Skill 已被本次 Agent 显式读取并遵循，但无法证明 Host 自动 Skill selection/load 使用的正是最新版。因此：

```text
INFRASTRUCTURE_E2E = PASS
AGENT_BEHAVIOR_E2E = PASS
CREATIVE_QUALITY_E2E = PASS
REAL_SKILL_LOAD = INSUFFICIENT_PROOF
BATCH_4_RESULT = PARTIAL
```

另发现 `shot.list_shots(scene_id)` 经 MCP 返回空数组，而 Java 同一接口及稳定 ID `get_shot` 可读到全部 10 条。该问题不影响本次最终回读与父子完整性，但必须在进入自动化 Asset Resolution / ComfyUI 编排前收口。

## 2. Batch 1～3 冻结基线

执行依据：

- `11-创作型Skill正式化审计与设计报告.md`；
- `12-创作型Skill生命周期基线加固执行报告.md`；
- `13-Work与Script正式创作能力加固执行报告.md`；
- `14-Episode、Scene与Shot正式创作能力加固执行报告.md`。

冻结内容包括统一 Creative Lifecycle、Work/Script 专业方法、Episode/Scene/Shot 专业方法及其 references。Batch 4 仅验证真实行为与质量，不把测试中发现的问题现场写回生产 Skill。

## 3. 本批测试范围

本批实际覆盖：

```text
Research evidence
→ Work
→ Script（8 集完整改编结构）
→ Episode 5
→ Scene 5-1 / 5-2 / 5-3
→ Scene 5-2 的 10 Shot 完整 coverage
→ stable-ID get reload
```

未进入 Asset、Media、ComfyUI、Image、Video、Audio 或 Production Provider。

真实用户级初始意图按自然语言表达为：

> 请以苏武被扣匈奴、北海十九年和李陵劝降为史实基础，创作一部聚焦个人命运、求生与忠诚代价的历史短剧；不要只写事件摘要，要能继续发展成可演剧集、场景和镜头。

测试内容没有写入生产 Prompt、Skill 或 fixture，也没有以题材硬编码替代 Skill 方法。

## 4. 生产 Skill 未修改证明

本批开始前与报告落盘前，`git diff -- skills` 均为空。五个核心 Skill 及全部 references、skill.yaml 均未修改。

工作区核心 `SKILL.md` SHA-256：

| Skill | SHA-256 |
|---|---|
| work-creation | `8d5612eaabe4f8ae9166a819a9c869300cd5622d3d1a7e01a02eb0729efcaa40` |
| script-adaptation | `a04173a7e7dc052674512518f654ee4625517670899dafdaffd6551e01e45372` |
| episode-development | `798360fce2425cd65cfdf711b90bc1e437dc7fc2c1e2e858d6b2e57e75a8410e` |
| scene-development | `d4482f99456f38db53d4c8a4342c9a19750cece604e8803cef67495c09fe8636` |
| shot-design | `08a79e0d9fc02a49971f7233a747f26c6bb40b9dd1846cbc263341b6f6139ce0` |

仓库原有未跟踪 `.DS_Store` 与 Java `application.yml` 本地修改均在本批开始前存在；本批没有触碰或回退。

## 5. 环境 Preflight

| 检查 | 结果 |
|---|---|
| Plugin manifest / 8 Skills | PASS |
| MCP process / endpoint | PASS，`127.0.0.1:8765/mcp` |
| MCP initialize | PASS，server=`drama-mcp-service` |
| Tool count | PASS，44 |
| Tool Contract hash | PASS，`824f09a38b954b36fe1f7ced616e5ce98d10b918171d838333caec97c6ac90ca` |
| Java auth ping | PASS，HTTP 200 |
| Java → MySQL | PASS |
| Work preflight search | PASS，真实 MCP 链返回空候选 |
| Research provider | MCP 配置为 mock；本批没有使用，改用 Host 的真实网络检索能力 |

Java 最初未运行。第一次按已打包 jar 默认配置启动时，Hikari 实际使用 `localhost:3306/drama_service` 并返回 500；只读 JDBC `SELECT 1` 已证明当前工作区配置的云 MySQL 可达。随后通过 Spring 启动参数加载工作区现有 `application.yml`：

```text
--spring.config.additional-location=file:.../application.yml
```

没有修改配置文件或 Java 代码。重新启动后，真实 `work.search_works` 通过 MCP 返回 `[]`，写入前预检关闭。

## 6. Skill Load 证明

当前 Host 已注册 Skill 路径为：

```text
/Users/yizhao/.codex/plugins/cache/drama-marketplace/drama-plugin/
0.1.0+codex.20260812052808/skills/*/SKILL.md
```

该缓存与工作区最新五个核心 Skill 哈希不一致：

| Skill | Host cache hash | Workspace hash | 一致 |
|---|---|---|---|
| Work | `286c0713…e5b4` | `8d5612ea…a40` | NO |
| Script | `b8b8fe76…3abb` | `a04173a7…372` | NO |
| Episode | `fe8ba67a…52e` | `798360fc…410e` | NO |
| Scene | `05c33348…5a2` | `d4482f99…636` | NO |
| Shot | `815d554a…ee1d` | `08a79e0d…ce0` | NO |

本次 Agent 已直接、完整读取工作区最新版 `SKILL.md` 与所需 references，并按其生命周期和 rubric 执行；实际行为与新版规则吻合。但 Host 的自动注册源仍指向旧缓存，故不能把自动 Skill load 声称为 PASS。

```text
SKILL_LOAD_PROOF = INSUFFICIENT
REAL_SKILL_LOAD = INSUFFICIENT_PROOF
```

## 7. MCP / Java 真实链路证明

所有 Domain create/save/get 均由真实 MCP client 通过 streamable HTTP 调用，没有 mock、fake、直接 Java Controller 写入或数据库写入。

链路证据：

- MCP 列出 44 个工具，核心 create/get/save 均存在；
- `work.search_works` 经 MCP → Java → MySQL 返回真实空结果；
- 16 个 create 成果均返回 Java 生成的稳定 ID；
- 5-2-05 通过 `shot.save_shot` 修订原 ID；
- 最终 16 个实体经 MCP `get` 全部重载；
- 只读数据库交叉检查代表 Scene 下 `drama_shot` 为 10 行；没有直接数据库写操作。

## 8. 测试题材选择

选择“苏武北海十九年”，原因：

- 不重复既有神龙政变等政治事件 fixture；
- 核心是个人命运、生存、友情、羞耻与忠诚，不依赖大战 spectacle；
- 史料存在明确固定事件，同时十九年日常有合理虚构空间，适合验证 evidence boundary；
- 李陵是可信镜像人物，可测试 Skill 是否能避免把历史人物写成单一口号。

## 9. Historical Research 结果与证据边界

真实研究使用《汉书·李广苏建传》在线古籍文本。固定事实包括：天汉元年出使、虞常案牵连、自刺未死、卫律劝降、北海牧羝、李陵以家讯劝降、武帝死讯、常惠设计雁足说辞、十九年后苏武与九人归汉。来源：[《汉书》卷五十四](https://zh.wikisource.org/wiki/%E6%BC%A2%E6%9B%B8/%E5%8D%B7054)。

证据边界：

- 固定：上述事件顺序、人物基本立场、李陵不归、雁足为交涉说辞；
- 不确定：北海的精确现代坐标、十九年逐日生活；
- 可虚构：不改变结局的生存动作、物件、停顿、室内调度和时间压缩；
- 禁止：苏武实质投降后反悔、李陵参与雁足计或随归、把真实射雁当已证事实。

Research notes 没有写入 Java；只有经过创作转译的历史边界进入正式 Work/Script/Episode content。

## 10. Work Agent Trace

```text
UNDERSTAND：新建第三题材 Work，目标是正式 Story Foundation
GATHER：work.search_works → []；真实《汉书》研究
NEGATIVE CONTROL：标题 + 两句事件摘要 → Review FAIL → NO CREATE
PLAN：命题、主人公目标/需要、镜像关系、代价、八集转折、史实边界
EXECUTE：形成完整候选 Work
REVIEW：主题、视角、关系、冲突、时间线、结构、历史边界 PASS
PERSIST：work.create_work
RELOAD：work.get_work PASS
```

## 11. Work Final Artifact Review

Work 已从事件摘要升级为 Story Foundation：

- premise 与 logline 聚焦“无人见证时忠诚是什么”；
- 苏武具有外部目标、内部需要、恐惧与代价；
- 李陵构成可信 counter-theme，而非工具性反派；
- 关系、八集结构、高潮、结局、视觉 motif 和历史边界齐全；
- 结局同时承认公共荣耀与私人损失。

结论：`WORK_QUALITY = PASS`。

## 12. Script Agent Trace

```text
GATHER：context.build_context(WORK, SCRIPT_ADAPTATION)
PLAN：主线、三条副线、人物弧、信息顺序、八集任务、连续性、制作规模
EXECUTE：形成八集完整 Screen Adaptation
REVIEW：忠于 Work、动机连续、升级、转折、高潮、可视行动、短剧节奏、历史边界 PASS
PERSIST：script.create_script
RELOAD：script.get_script PASS
```

## 13. Script Final Artifact Review

Script 不再是剧情梗概：八集均有 opening hook、goal、beats、state change 与 ending hook；信息揭示有顺序，李陵/常惠/汉节副线跨集推进；screen principle、对白纪律、连续性与 production shape 已定义。

限制是除代表 Episode 外，尚未把全部八集展开为逐场对白锁稿；这不影响本次“完整系列改编结构”验收，但仍是未来全剧生产前工作。

结论：`SCRIPT_QUALITY = PASS`。

## 14. Episode Agent Trace

```text
GATHER：context.build_context(SCRIPT, EPISODE_DEVELOPMENT)
PLAN：选择第5集，定义不可替代 Dramatic Job 和三场 progression
EXECUTE：形成 entry/exit state、信息增量、人物变化与时间预算
REVIEW：hook、central conflict、progression、turn、relationship change、ending hook PASS
PERSIST：episode.create_episode
RELOAD：episode.get_episode PASS
```

## 15. Episode Final Artifact Review

第5集的不可替代任务是摧毁苏武“家人仍在等待”的外部支点，使忠诚转为自我选择。其完成后，苏武—李陵关系从旧友记忆变为“相知但不能同行”，并为第6集武帝死讯准备更深危机。

结论：`EPISODE_QUALITY = PASS`。

## 16. Scene Agent Trace

三场分别执行：

1. 5-1“雪中故人”：王印、酒肉、汉节共同制造重逢门槛；
2. 5-2“一桌家书”：四层信息揭示和价值冲突；
3. 5-3“两杯入雪”：关系分途并回到主动生存。

每场均经过 Purpose / Objective / Obstacle / Turn / Entry–Exit State Review 后才 create。

## 17. Scene Final Artifact Review

三场不是“人物坐着讨论主题”：横节护羊、汉节卡门、解下王印、空柴筐、只暖手不饮、火灭、重新系印、两杯入雪和修羊圈均改变策略或关系。相邻场连续：王印门外 → 室内无王印 → 天亮重新系印；火灭/暗中坐定 → 天亮离场。

结论：`SCENE_QUALITY = PASS`。

## 18. Shot Agent Trace

```text
GATHER：context.build_context(SCENE, SHOT_DESIGN)
PLAN：10 Shot coverage；固定左李陵/右苏武轴；跟踪酒碗、火势、汉节、王印
EXECUTE：每镜写 narrative purpose、blocking、framing、camera、rhythm、continuity、feasibility
REVIEW 1：完整覆盖、非机械切句、轴线和入出状态总体 PASS
CREATE：10 个 shot.create_shot
SECOND PASS：发现 5-2-04 → 5-2-05 酒碗持有冲突，FAIL
LOCAL REVISE：只改 5-2-05 blocking / composition / continuity
REVIEW AGAIN：PASS
SAVE：shot.save_shot（稳定 ID 不变）
RELOAD：10 个 shot.get_shot PASS
```

## 19. Shot Final Artifact Review

10 镜头覆盖完整 Scene：建立谈判空间、三次家讯反应、扶节越界、李陵反问与控诉、短句对撞、火灭动作、结尾价值转折。镜头不是一句台词一切；多处使用完整动作单镜、拉焦、静态长停顿和紧双人，且每镜有明确 Narrative Purpose。

结论：`SHOT_QUALITY = PASS`。

## 20. Coverage / Continuity / Feasibility

Coverage：10 镜约 257 秒，另留约 23 秒用于转场与呼吸，覆盖 4 分 40 秒中心 Scene。

Continuity：

- 轴线固定左李陵/右苏武；
- 酒碗：中线 → 苏武持碗 → 放下 → 回到李陵；
- 火势：弱火 → 更弱 → 红炭 → 熄灭；
- 汉节：横隔 → 被触碰 → 竖于苏武身侧；
- 王印始终留在 Scene 5-2 外。

Generation Feasibility：每镜都给出固定人物、动作复杂度、关键帧或口型建议；5-2-05 与低光双人长镜被明确标为高难，但有可执行的首尾帧和位置锁定方案。本批只验收设计，不声称 ComfyUI 生成 PASS。

## 21. Revision / Re-plan 统计

| 对象 | Plan | Draft | Review FAIL | Local Revise | Re-plan | Review Again | create | save |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Work | 1 | 2（含负向弱稿） | 1 | 0 | 1 | 1 | 1 | 0 |
| Script | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| Episode | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| Scene | 3 | 3 | 0 | 0 | 0 | 0 | 3 | 0 |
| Shot coverage | 1 | 10 | 1 | 1 | 0 | 1 | 10 | 1 |

Revision 收敛：Work 一次 Re-plan；Shot 一次局部修订；均在下一次 Review PASS 后停止，没有循环。

## 22. Persist Gate 验证

负向 Work 摘要在 Review FAIL 后没有 create。所有首次持久化均发生在 Context 足够、Plan 完成、Draft 完整、Critical Review PASS 且无未解决历史/连续性冲突之后。

5-2-05 第二轮发现问题后没有 create 新 Shot，也没有先 save 再审查；修订完成并 Review Again PASS 后才调用 `shot.save_shot`。

```text
NO REVIEW PASS → NO CREATE / SAVE
PERSIST_GATE = PASS
```

## 23. Plan / Review Notes 泄漏检查

最终通过 MCP 重载全部 16 个 Domain Object，并递归检查 `content` key。未出现：

```text
plan
draft
review
reviewNotes
revisionNotes
temporaryState
```

`episodeDesigns`、`scenePlan` 等是最终正式结构内容，不是 Agent 私有推理或 Review notes。

```text
DRAFT_LEAK_TO_JAVA = NO
REVIEW_NOTES_LEAK_TO_JAVA = NO
```

## 24. Java Reload 验证

16 个稳定 ID 均经 MCP `get` 重载并计算规范 JSON SHA-256。摘要：

| 类型 | 数量 | get 结果 |
|---|---:|---|
| Work | 1 | PASS |
| Script | 1 | PASS |
| Episode | 1 | PASS |
| Scene | 3 | PASS |
| Shot | 10 | PASS |

5-2-05 重载 SHA-256 为 `3d21da464991e8800a2dd83bfccd3741458b67e3616e35afdeaeb87cec2ea3b4`，包含修订后的酒碗 blocking。

## 25. Parent / Child Integrity

程序化稳定 ID 检查结果：

```text
entityCount = 16
parentIntegrity = true
processLeakFree = true
```

链路：

```text
work_4cf8…699b
└─ script_5f16…b2ce
   └─ episode_3a90…1475
      ├─ scene_bfc4…3ee8
      ├─ scene_399a…284c
      │  └─ 10 shots（5-2-01 ～ 5-2-10）
      └─ scene_ad41…df14
```

## 26. Upstream Issue 行为

Script、Episode、Scene 与 Shot 在规划时均检查父级事实与边界，没有发现需要修改已持久化父对象的结构性矛盾。因此没有为了制造测试而伪造上游问题，也没有触发上游 save。

```text
UPSTREAM_ISSUE_HANDLING = NOT_TRIGGERED
```

## 27. Context Refresh 行为

每个层级使用新的 `context.build_context` 从稳定父 ID 建立 Context。由于没有上游修订，没有触发 `context.refresh_context`。

```text
CONTEXT_REFRESH_AFTER_UPSTREAM_REVISION = NOT_TRIGGERED
```

## 28. Negative Control

负向 Work 候选仅含标题与“出使—牧羊—归汉”两句摘要。Work Review 因以下缺失判 FAIL：主人公内部需要、关系压力、核心冲突、失败代价、戏剧结构、历史/虚构边界。Agent 未调用 create，随后 Re-plan 并形成完整 Work，再 Review PASS。

```text
NEGATIVE_CONTROL = PASS
```

## 29. Existing Fixture Regression

Plugin 全量 72 tests 包含 `tests/fixtures/creative-quality/work-script-evaluations.yaml` 的既有 Work/Script 正反例回归；`tests/test_skills.py` 21 tests 覆盖五个 Creative Lifecycle 与 Batch 2/3 rubric 结构。既有 fixture 未修改。

## 30. Final Independent / Second-pass Review

本批没有第二个独立模型或外部审稿 Agent，因此：

```text
FINAL_REVIEW_INDEPENDENCE = SELF_REVIEW_ONLY
```

但执行了持久化后的独立第二轮读取审查，且实际发现、修正了 5-2-05 连续性问题。该结果证明第二轮不是形式性 PASS；其局限是仍可能存在同一模型盲点。

## 31. Agent Behavioral Compliance

观察到的行为：

- 先 search / get / build_context，再 Plan；
- Research 有证据需求时使用真实来源，不逐 Scene/Shot 重复研究；
- Draft 与持久化对象分离；
- 每一层先执行领域 Review；
- FAIL 后能够区分 Re-plan 与 Local Revise；
- Revise 后重新 Review；
- new 使用 create，existing concrete revision 使用 save；
- 不进行 create 后习惯性 save。

因此行为本身 PASS。但因 Host 自动 Skill load 证据不足，不能把全部行为因果归功于已安装缓存中的最新版 Skill。

## 32. Creative Quality Evaluation

| 层级 | 质量判断 | 依据 |
|---|---|---|
| Work | PASS | 命题、人物目标/需要、关系、代价、结构、边界完整 |
| Script | PASS | 8 集可分集 Screen Adaptation、弧线、节奏、连续性与制作形态清楚 |
| Episode | PASS | 有不可替代 Dramatic Job、hook、progression、state change |
| Scene | PASS | 目标/障碍/行动/turn/entry-exit state 均可见 |
| Shot | PASS | 完整 coverage、叙事目的、轴线、物件连续性、生成可行性 |

质量 PASS 指达到本批 rubric 的正式候选水平，不等于市场验证、历史学专家终审、演员排练锁稿或 Production Ready。

## 33. Tool 使用统计

| Tool / 能力 | 次数或结果 |
|---|---|
| MCP initialize/list_tools | 多次预检；44 tools |
| work.search_works | 1，空候选 |
| context.build_context | 4（Work→Script、Script→Episode、Episode→Scene、Scene→Shot） |
| create_work/script/episode | 各 1 |
| create_scene | 3 |
| create_shot | 10 成功；另有 1 次客户端中断后重复冲突，未新增数据 |
| save_shot | 1（真实局部修订） |
| stable-ID get | 最终 16 次全部 PASS |
| shot.list_shots | MCP 两次空返；Java 直接只读接口为 10 条 |
| shot.search_shots | 1 次空返，用于冲突诊断 |
| 数据库 | 只读 `SELECT 1`、schema/row 交叉检查；零写入 |

## 34. Review 收敛情况

Work 负向候选一次 FAIL 后通过 Re-plan 收敛；Shot 一次第二轮 FAIL 后通过 Local Revise 收敛。其他对象第一轮 Critical Review 即 PASS。

Rubric 没有造成无限循环，也没有要求所有对象都研究、重做或持久化 review 状态。第一次 Shot Review 漏掉酒碗问题，但第二轮 rubric 能定位并指导最小修订，说明主要风险是执行注意力而非 rubric 缺项。

## 35. Quality Risks

| 风险 | 分类 | 影响 |
|---|---|---|
| Host 注册旧 Skill 缓存 | Harness / installation | 无法证明自动选择加载最新版 Skill |
| MCP `shot.list_shots` 空返 | Runtime integration | 自动恢复完整 Shot 列表可能失败；get 不受影响 |
| 最终审稿为同一 Agent | Model compliance | 仍可能存在自审盲区 |
| Script 仅代表集逐场展开 | Scope | 全剧视觉生产前仍需其余 Episode/Scene 锁稿 |
| 北海日常大量依赖可撤销虚构 | Historical boundary | 后续美术/对白不得把推断升级成史实 |
| 5-2-05 双手/物件同框 | Generation feasibility | 需要 Asset 稳定性和关键帧约束 |

## 36. Tool/MCP/Java/Harness 修改必要性重新判断

| 层 | 是否需要改 | 判断 |
|---|---|---|
| Skill | NO | 本批未证明 rubric 缺项；行为与质量均可收敛 |
| Tool Contract | NO | 现有 create/get/save/context 足以完成完整链；无需 plan/review Tool |
| MCP Contract | NO | 44 tools 与 hash 冻结，合同本身足够 |
| Java Domain Contract | NO | 开放 content 能保存正式结果，父子 ID 足够 |
| Harness / plugin installation | YES | 必须刷新并证明 Host 加载工作区最新五个 Skill |
| Runtime list implementation/config | YES（收口项） | 需定位 MCP 运行时为何 `shot.list_shots` 与 Java 真实结果不一致；优先检查运行包/缓存，不先改合同 |

因此最终状态中的 `MCP_CHANGE_REQUIRED` 仍记 NO：现有 MCP 服务代码与 13 个回归测试未显示合同或 adapter 必改；更可能是正在运行的插件包/缓存版本不一致。若刷新运行包后问题仍复现，再单独立最小 bugfix 批次。

## 37. 自动化回归结果

| 检查 | 结果 |
|---|---|
| Drama Plugin full pytest | 72 passed |
| Skill tests | 21 passed |
| Tool reference validation | PASS（Plugin/Skill tests 覆盖） |
| mypy | Success，34 source files |
| Drama MCP Service pytest | 13 passed |
| Tool Registry count | 44 |
| Tool Contract SHA-256 | `824f09a38b954b36fe1f7ced616e5ce98d10b918171d838333caec97c6ac90ca` |
| `git diff --check` | 报告落盘后执行，见最终交付 |

首次调用 Plugin 内层 `.venv/bin/pytest` 不存在，改用仓库实际 `../.venv/bin/pytest` 后通过；首次 mypy 未携带源码路径，改用 `PYTHONPATH=src ... mypy src/drama_plugin` 后通过。这些是命令入口问题，不是产品回归。

## 38. 所有真实 Domain IDs

```text
WORK_ID = work_4cf81e8862234727b082cf2115ec699b
SCRIPT_ID = script_5f16ca3b7a3b4b2e80b2f2711e37b2ce
EPISODE_ID = episode_3a900d6a26b246889970af5b7f5a1475

SCENE_1_ID = scene_bfc45f01d55a4323bcba15eb12913ee8
SCENE_2_ID = scene_399ace55923e47be8092eb808d7d284c
SCENE_3_ID = scene_ad4148a70cd2435f999432f67112df14

SHOT_5_2_01_ID = shot_6562bc6e4c0f47818f407fd0c3a11a83
SHOT_5_2_02_ID = shot_bddf109241874afb85376a773eff0691
SHOT_5_2_03_ID = shot_e8433461bc644caa85914a8f9f0e739d
SHOT_5_2_04_ID = shot_a9dc0ba7dfdc4e7ea2d1d479403c6274
SHOT_5_2_05_ID = shot_5559407312e04d9988591a11d3bcbf7f
SHOT_5_2_06_ID = shot_11b46c83ee77483fb01c6903cfa198c3
SHOT_5_2_07_ID = shot_27ff438363f64a948a6a66184a140cf1
SHOT_5_2_08_ID = shot_278f97a987174dfeb973e53f3bbb5075
SHOT_5_2_09_ID = shot_e1ba8436b6b047a8b12a9eba0ec19822
SHOT_5_2_10_ID = shot_420f581d79ef4dc898359809900cb707
```

这些数据按要求保留，不自动清理。

## 39. 已知不足

- Host 自动 Skill load 不是最新版，因而缺少直接证明；
- MCP Shot list 读路径与 Java 结果不一致；
- 没有独立第二模型、历史学专家、导演、摄影指导或演员排练审稿；
- 只展开一个代表 Episode 和三场，不等于八集全部锁稿；
- 没有执行 Asset Resolution 或任何真实生成；
- 一次 E2E 不能证明跨题材、跨模型稳定性；
- 当前五个 Skill 不因本批质量 PASS 自动升级为 Production Ready。

## 40. 是否可以进入 ComfyUI MCP 阶段

就 **本次 5-2 Shot artifact 本身** 而言，已经具有叙事目的、完整 coverage、连续性和生成可行性，值得进入 Asset Resolution / 小规模视觉试产。

就 **平台阶段门槛** 而言，目前不建议立即进入正式 ComfyUI MCP 集成：先刷新 Host 插件缓存并取得新版 Skill 直接加载证明，再收口 MCP `shot.list_shots` 空返。两项都属于小而明确的运行集成前置，不要求改 Skill、Tool Contract 或 Java Domain。

```text
READY_FOR_COMFYUI_MCP = NO
```

## 41. 最终验收结论

```text
REAL_SKILL_LOAD = INSUFFICIENT_PROOF
REAL_MCP_CHAIN = PASS
REAL_JAVA_PERSISTENCE = PASS
REAL_RESEARCH_CONTEXT = PASS

REAL_WORK_E2E = PASS
REAL_SCRIPT_E2E = PASS
REAL_EPISODE_E2E = PASS
REAL_SCENE_E2E = PASS
REAL_SHOT_E2E = PASS

WORK_QUALITY = PASS
SCRIPT_QUALITY = PASS
EPISODE_QUALITY = PASS
SCENE_QUALITY = PASS
SHOT_QUALITY = PASS

PLAN_BEFORE_DRAFT = PASS
REVIEW_BEFORE_PERSIST = PASS
REVISION_LOOP = PASS
NEGATIVE_CONTROL = PASS

UPSTREAM_ISSUE_HANDLING = NOT_TRIGGERED
CONTEXT_REFRESH_AFTER_UPSTREAM_REVISION = NOT_TRIGGERED

PERSIST_GATE = PASS
DRAFT_LEAK_TO_JAVA = NO
REVIEW_NOTES_LEAK_TO_JAVA = NO

PARENT_CHILD_INTEGRITY = PASS
FINAL_RELOAD = PASS

RUBRIC_CONVERGENCE = PASS
RUBRIC_OVERSTRICT_RISK = NO
RUBRIC_TOO_WEAK_RISK = NO

TOOL_CONTRACT_CHANGE_REQUIRED = NO
MCP_CHANGE_REQUIRED = NO
JAVA_CHANGE_REQUIRED = NO
HARNESS_CHANGE_REQUIRED = YES
SKILL_CHANGE_REQUIRED = NO

WORK_SKILL_MATURITY = EARLY
SCRIPT_SKILL_MATURITY = EARLY
EPISODE_SKILL_MATURITY = EARLY
SCENE_SKILL_MATURITY = EARLY
SHOT_SKILL_MATURITY = EARLY

INFRASTRUCTURE_E2E = PASS
AGENT_BEHAVIOR_E2E = PASS
CREATIVE_QUALITY_E2E = PASS

BATCH_4_RESULT = PARTIAL

READY_FOR_COMFYUI_MCP = NO
```

### Q1：真实 Agent Loop 中是否发生 Plan / Execute / Review / Revise / Persist？

**发生。** Work 负向候选触发 Re-plan；5-2-05 触发局部 Revise、Review Again 和 save；其他对象均遵守 Plan → Draft → Review → create。但 Host 自动加载最新版 Skill 的证明不足，因此不能把这一行为完全归因于当前安装缓存。

### Q2：Work 是否从历史事件摘要升级为正式 Story Foundation？

**是。** 已具备命题、logline、人物目标/需要、镜像关系、冲突、代价、弧线、八集结构与历史边界。

### Q3：Script 是否从剧情梗概升级为可演、可分集的 Screen Adaptation？

**是。** 八集均有 hook、dramatic job、beats、state change 和 ending hook，并有跨集弧线、信息顺序、对白纪律、连续性与制作形态。全部八集逐场锁稿仍是后续工作。

### Q4：Episode 是否具有不可替代 Dramatic Job？

**是。** 第5集专门摧毁“家人在等”的外部支点，并把忠诚转换为自我选择；删掉该集，第6集信念危机与第8集诀别均失去基础。

### Q5：Scene 是否从谈论冲突升级为在冲突中行动并改变状态？

**是。** 王印、门槛、酒碗、空柴筐、火势、汉节和羊群都参与策略变化；每场前后信息、关系或目标状态不同。

### Q6：Shot 是否升级为 Coverage Strategy + Narrative Purpose + Continuity + Generation Feasibility？

**是。** 10 镜覆盖完整中心 Scene，固定轴线并跟踪关键物件，每镜均有叙事功能、入出连续性和生成约束；不是一句话一个镜头。

### Q7：Review FAIL 后能否收敛？

**能。** Work 一次 Re-plan、Shot 一次 Local Revise 后均在第二轮 Review PASS，未无限循环。

### Q8：全 Critical Rubric 过严、合适还是过弱？

**当前证据显示合适。** 它能挡住摘要式 Work，也能定位一个真实 Shot blocking 问题，同时没有迫使所有对象反复 Research 或重写。一次运行不足以排除跨题材过严/过弱风险。

### Q9：最大剩余问题在哪一层？

**Harness / plugin installation 层。** Host 注册旧缓存，导致最新版 Skill 自动加载证明不足；其次是运行时 Shot list 读路径。当前没有证据要求改 Skill、Tool Contract 或 Java Domain。

### Q10：当前 Shot 是否值得进入 Asset Resolution / ComfyUI MCP 视觉生产？

**就 artifact 质量而言 YES；就平台立即进入正式阶段而言 NO。** 先完成新版 Skill 缓存刷新与 `list_shots` 收口，然后可以用本次 10 Shot 作为第一组 Asset Resolution / 小规模 ComfyUI 试产输入。

本批最核心结论：Batch 1～3 的方法在一次真实创作中能够产出明显优于测试摘要的正式候选结果，并能驱动真实修订闭环；阻止 Batch 4 完全 PASS 的不是 Creative Skill 内容质量，而是 Host 没有直接加载工作区最新版 Skill 的可验证事实。
