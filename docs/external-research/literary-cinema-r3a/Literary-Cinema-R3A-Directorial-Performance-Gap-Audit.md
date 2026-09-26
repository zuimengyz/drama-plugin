# Literary Cinema R3A — Directorial Performance Gap Audit

> 审计日期：2026-09-26。源码基线：`bb83843074ae685a5fdd53ed94b1a27bd863a014`。范围：NON_RUNTIME / NO SCREENPLAY REWRITE / NO MEDIA GENERATION。本文的未来设计建议不是已实施能力，也不是剧本批准。

Director 已有真实表演指导合同与正式消费者，不能判定“只有 Vision，完全不会指导演员”。但当前 R2 候选的逐句 DPD 映射没有等价于当前版本的完整 Director 意图链；现有正式链的覆盖粒度、同场逐句绑定和密度也仍有需检验之处。

## 1. 真实消费链

[DPD 合同](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/dpd.py)以 Scene→Beat→Line 合成心理/关系方向；R2 的 [map_screenplay_performance](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/screenplay_playability.py:93)只投影已提供方向与 exact dialogue，不生成 Director 指导。

[DirectorPerformanceIntent](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/performance_direction.py:37)包含 performance_core、audience_experience、primary_focus、containment、expression ceiling、release、partner focus、rhythm、continuity 与禁止行为；[validate_projection](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/performance_direction.py:43)校验同一 DPD/意图和通道实现；[attach_cinematic_performance](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/performance_direction.py:145)将来源一致的结果接入镜头。Voice 消费同一心理来源，不能改台词。

[complete_production_book](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/preproduction.py:305)真正调用 formal source witness 和 full coverage，要求每场 Director intent、每个源 spoken key 的 VISUAL/VOICE projection。因此存在可执行审阅链；最终只到设计审阅/用户审阅状态，不自动授权媒体生成。

当前 [R2 sidecar](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/screenplay-r2/performance-sidecar.json)是设计候选，仅 S01–S03 的 DPD/playability；[Director screenplay](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/director-screenplay.json)绑定旧版本。不能将它们拼成新版本已通过的正式链，也不能将线上状态未知报成正式源完全没有覆盖。

## 2. Dialogue Direction 能力逐维审计

| 候选维度 | 当前承载 | 判断 / 缺口 |
|---|---|---|
| speaker / exact dialogue | SpokenContent、LineDPD、source hash | 强绑定已有；Performance 无改词权 |
| target | canonical line target、effective interaction_target | R2 强制一致；非抽象“对镜头”替代人物对象 |
| beat objective | BeatDPD direction.objective | 已是行动/关系语义，不应新增 Director objective |
| playable action | tactic / LineDPD dramatic_action；ObservableAction | 区分“让他停下”的言语策略与“拉手肘”的身体实现 |
| delivery | source performanceIntent、Voice direction/projection | 存在；不能把嗓音参数反推新心理 |
| subtext | effective DPD subtext | 单一心理来源；Director 不另写矛盾潜台词 |
| trigger / turn | Beat transition trigger、Line continuity/change | 可描述，缺跨角色反馈/失败后策略边的系统校验 |
| expected response | objective/target 与 interaction handoff/response timing 可间接表达 | “希望对方发生何改变”没有稳定完整的全链关系；不能把“目标非空”当证明 |
| listener reaction | partner DPD、interaction speaker/listener_action 等 | 正式位置已有；枚举一场一个 interaction 太粗，可能遗漏多个关键来回 |
| forbidden interpretation | Director do_not / forbidden behaviors、DPD控制、审阅证据 | 已有，需区别禁止表演误读与禁止源动作 |
| density | STANDARD / EXPANDED、关键 Beat dual briefs | 已有起点；没有与 salience/ambiguity/risk 的清晰选择依据 |

[interaction 校验](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/performance_coverage.py:78)要求 speaker/listener refs、双方 action、目标、注意力、handoff/partner cue、response_timing、next beat owner，故“系统完全没有 listener”不成立。问题在重要交互是否全部被枚举和接续。

## 3. 当前 R2 witness 为什么不足以证明会演戏

[R2 beat validator](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/screenplay_playability.py:31)检验动作是否在正文出现；reaction.actor 必须等于该 actor beat 的 actor，所以该字段自身不是对方反馈边。对方任务需要另一个 DPD 与 interaction 链，而不是往本人的 reaction 填别人动作。

当前 sidecar 中：

- S02-appeal 覆盖女孩两次请求，reaction 使用较晚的退缩；这不是逐次 stimulus→response→changed tactic 的完整序列。
- S02-deflect 的动作数组把“收回手”列在“抬起手停在肩旁”之前，正文次序相反。因为 validator 检查 source 子串而不检查时序，这种 witness 不能当执行顺序。
- S02-seek 的 reaction 是发现行人，正文中它是绕开跑去求助的先行条件。字段名称并未保证因果角色。
- 部分 continuity/change 文字是概括性连接，不能证明角色等待何种回应、如何读错、为什么改变策略。

这是现有资料的诊断，不是建议将数组直接改成新的表演稿。本轮没有改文件，也没有运行生成。

## 4. Dialogue Is Action / Expected Response / Failure Escalation

“找警察去。”有原文与合法对象；其戏剧行为不止传递机构信息，还在当前语境中推动结束接触/转移求助。这个解释应由源 Scene 与 DPD 支持，不能让 Prompt 从句子猜。

三层应分开：

1. Scene：女孩要获得帮助、男人如何应对、实际回应和后果是什么。
2. DPD：每个角色此刻试图改变谁、采用何策略、把何反馈视为失败/机会；保持源支持。
3. Director：让观众感到拒绝需要主动用力、希望如何被误读、哪一刻听者才进入对方处境；不替角色增加新目标。
4. Performance/Voice/Blocking：将已获准方向体现为听见、停住、继续、语气和空间行为。

失败升级的 owner 是 Scene 的事件/策略过程设计，DPD 解释角色的策略转移；不是 Dialogue 一味增加信息，也不是 Director 或 Performance 自动添加新抓拉、停顿或台词。

## 5. Listener 与 Silence：已存在，但应提高语义精度

[FormalSourceWitness.obligations](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/hosts/formal_performance.py:37)已经枚举 silent、characters、interactions 和 continuity。silent 按 screenplayAction 的标点句切分，保守避免漏动作；多人 Scene 只生成一个 interaction row。这能保证正文片段没有静默消失，却不等于识别“正在等待回答”“故意不答”“听后改变策略”的戏剧单元。

因此应让 listener/silence 成为**已有 Scene/DPD/coverage 内可独立追踪的戏剧语义**，无需新业务实体。不是每个静默句都必须成为一个 beat；没有 actor 的环境句也不应强编心理任务。

S01 无人叫他后的停听、S02 身体未转向与迟来的听见、S03 门把前未打开，各有不同功能。共同 emotion label 不能代替这些区别。未来审阅应问等待谁、期待什么、没有得到什么、由此发生什么；不规定头转角度或秒数。

## 6. Director / Performance / Screenplay 边界

本地真实职责比“Director 拥有所有 intention”更精细：[Director Skill](/Users/zy/historical-plugin/drama-plugin/plugin/skills/director/SKILL.md)明确 DPD 拥有 objective/obstacle/tactic/subtext；[DPD Skill](/Users/zy/historical-plugin/drama-plugin/plugin/skills/dramatic-performance-direction/SKILL.md)也禁止 Director 第二心理层。

- Screenplay/Scene：发生什么、说什么、基本行为与关系/欲求事实。
- DPD：来源支持的即时 actor objective、playable tactic、subtext、知识/关系解释的唯一有效版本。
- Director：观众体验、重点、压力/释放、节奏与部门协调；引用 DPD 解释，不另造一个目标。
- Performance：在独立 facet 写身体/反应实现；Blocking 拥有路径，Action 拥有力学，Voice 拥有声音体现。
- Character Embodiment：长期、阶段性身体倾向；不自动把心理意义转换为当前一次具体动作。

Director 可以要求重新审阅目标的表达，不能通过“更好演”把目标事实改掉。源冲突回 Scene/Script；不能用表演意图掩盖事件修改。

## 7. Clean Screenplay + 现有 sidecar

推荐延续现有 sidecar/既有 artifact store，不把 OBJECTIVE/SUBTEXT/EXPECTED RESPONSE 逐句插入可读正文。

| 方面 | 设计建议 |
|---|---|
| 人类可读性 | 正文保留行为与台词；指导可单独展开，不能靠附录把不成立的戏解释成成立 |
| Runtime | 源 Scene/SpokenContent ID→DPD ref→Director intent→具体 projection；缺覆盖可检测 |
| Mapping | 已批准源用 source pins；候选用文本版本/hash与局部 line locator，不伪造正式 ID |
| Versioning | 改词/目标/beat 后使依赖指纹失效；未变片段可复用但须证明 scope 和依赖未变 |
| Replay | 原文保持单源，sidecar存引用与解释/实现；不得复制一套可编辑台词 Canon |
| Approval | screenplay adoption 与方向设计审阅、用户生产批准分别处理 |
| Downstream | Performance/Voice 读同一 DPD 和 Director envelope，不能从正文自行补另一套心理 |

## 8. 每句覆盖与 Direction Density

现有 STANDARD/EXPANDED 应优先复用。所有正式 turn 都有 trace，但密度依据重要性/多义/关系转折/风险：

- 普通功能回应：可引用稳定 beat DPD/scene Director intent，只写本句必要差异。
- 有关系变化：显式标识本句作用、对象、期望/实际反馈与接续。
- 重大转折/高误读：补足触发、潜台词、禁止误读、listener任务、强度/释放及前后余波。

这些是审阅原则，不是新 LOW/MEDIUM/HIGH enum。当前 projection 合同固定要求较多视觉/声音字段；R3B 应检验“共享约束+局部差异”的表达是否可回放，不能降低每句覆盖来换简洁，也不应把基础回应扩成两页微表情。

## 9. 精确 turn 绑定的静态风险

正式 source witness 检查每个 DPDSnapshot 自身绑定合法台词，并检查源所有台词出现在 snapshots 中；direction 的 objective_ref 最后只检查同 Scene。[Book completion spoken 循环](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/preproduction.py:349)用该 ref 取 DPD 并验证 projection，却未在该循环显式断言其 spoken_content_id 等于当前 expected item 的 line ID。

这意味着**同场两句合法 DPD/projection 与 coverage 行之间的错配存在静态校验缺口**。本轮没有构造/运行端到端绕过案例，不报告已复现生产漏洞。R3B 应加精确 turn/speaker/target 的绑定反例，区分“所有台词都在某处”与“每行指导属于这句”。

## 10. 未来 Dialogue Direction Coverage Gate 需求

从当前批准 turn 枚举，不从手写缩短清单枚举。检查 exact dialogue、speaker、target、DPD、Director意图、版本一致和 projection 属于同一句；重要 listener/silence 可独立覆盖；密度有依据；全部通过后仍需专业可演性审阅。

源文本可读与台词歧义 Gate 应保留，但允许源支持的未完句、未回答与有功能的沉默，不逼每次第一句把信息讲全。不能把更完整 exposition 当唯一消歧方式。

