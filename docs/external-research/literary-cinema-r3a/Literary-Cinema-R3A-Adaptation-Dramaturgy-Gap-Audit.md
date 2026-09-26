# Literary Cinema R3A — Adaptation & Dramaturgy Gap Audit

> 审计日期：2026-09-26。源码基线：`bb83843074ae685a5fdd53ed94b1a27bd863a014`。范围：NON_RUNTIME / NO SCREENPLAY REWRITE / NO MEDIA GENERATION。本文的未来设计建议不是已实施能力，也不是剧本批准。

首要缺口不是更多影视术语。已有改编许可、电影表达、场景策略变化规则，但它们与当前 screenplay 的具体信息时机之间缺乏足够细的、可验证的因果交接。R2 优先解决“读懂与能演”，没有证明“信息在这一刻出现是被戏逼出来的”。

## 1. Source Fidelity：当前在保护什么

[creative_source contracts](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/creative_source.py:62)把原文、事实、解释、改编分开。Preservation 包含 must_keep、核心人物关系/事件、character arc、theme conflict、narrative identity；不是简单锁每一个字。文字精确锁属于 SourceArtifact 引文和已批准 SpokenContent 两个不同层级。

| 审计候选 | 当前等价承载 | 当前验证 | 缺口 |
|---|---|---|---|
| SOURCE_CRITICAL | Preservation / must_keep / core_* / narrative_identity；source pins | 来源有效；REMOVE 不得移除 protected；阶段 review hash | 对 KEEP/EXTERNALIZE/REORDER 等操作是否破坏关键因果、人物逻辑，主要依赖专业审阅，不是完整语义证明 |
| ADAPTATION_FLEXIBLE | permitted_changes + decision operation/reason/narrative_effect/expression | operation 许可、source IDs、destination 映射 | 许可粒度与实际改动差异、责任人、保留项证明缺少统一逐项闭环 |
| 原作顺序 | LiteraryAnalysis.event_order | 原作事件集合与分析完整性 | 这是来源分析顺序，不是电影播放顺序锁 |
| 版本台词 | Script/SpokenContent + R2 exact-text witness | hash、speaker、target、intent 一致 | 一句“正确”台词的出现时机仍可能错 |

这些候选不是本轮新增 enum。不能把“非 must_keep”直接当任意可改；仍须 permitted_changes 和授权的 owner/review。

**没有发现源码强制按小说顺序拍的证据。** Operation 明确含 REORDER；validate_literary 没有把电影 destination 顺序与原作 event_order 做相等约束。实际 [literary-package](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/literary-package.json)的 D02 将自杀意图的呈现延至 S03，D15 重组传讲与再遇关系；不能将本片问题归因为系统冻结了全部小说顺序。

当前忠实主要保护人物/关系、核心因果、思想冲突、人物变化、主观叙述边界、关键象征与结局方向；原文引文在来源层精确保留。潜在错误是作者为保持事实而保守地沿用叙述推进，不是已有代码禁令；需要创作证据，不能凭成片想象归罪源码。

## 2. Adaptation Thesis：复用而非另建 Canon

已有组件的职责不同：

- PhilosophicalCore：原著问题、价值冲突、选择/后果/歧义；不等于本次电影选择。
- AdaptationContract：哪些改变获准及叙事效果；可以承载版本取舍。
- CinemaExpression：该取舍怎样可拍；不负责完整 Scene 过程。
- Story / Dramatic Bible：主轴、人物关系与体验路线。
- Director Vision / cinematicIntent：观众体验和表达重点，消费上述选择；不能另选一个相反故事。

本片 [dramatic-bible.json](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/dramatic-bible.json)已经选择“从无所谓的自封，到不先解释而跟随具体请求”，叙事开口排除母亲最终病况、完整文明史；episodeArchitecture 指明 S13 峰值、S06/S14 呼吸空间、S15/S16 余波。这已经接近具体的版本 thesis，不只是主题摘要。

**缺的不是必然的新 Thesis 顶层合同。** 缺的是把“用哪一关系/冲突/体验承载原作”的既有版本选择，绑定至 adaptation decisions、Scene 过程、信息时机及评价证据。R3B 应先复用 Story/working Bible 的版本选择和 AdaptationContract 的 source/decision 追踪；如不能可靠回放，才做最小 facet，不能再建 WorkMeaning 或第二 Canon。

## 3. Narrative Compression / Expansion 权限

| 操作 | 当前表达能力 | 合法 owner | 薄弱处 |
|---|---|---|---|
| COMPRESS / MERGE / REORDER | 有明确 Operation；MERGE 多来源检查 | literary-adaptation 批准改编边界，Story/Scene 在范围内执行 | 操作后关键因果是否保留仍需审阅 |
| EXPAND | 无同名 enum；一 source→多 decisions/destinations、ADD/EXTERNALIZE 可表达部分 | 涉新增源外事件先 adaptation；范围内场景展开由 Scene | 无需因缺一个词就宣布没有能力；展开与发明新关键事实须区分 |
| SPLIT | mappings 可一决策多 destination | Story/Scene 执行，影响改编选择则上返 | 拆分后的信息依赖/保护义务需保持 |
| DELAY_REVEAL / ADVANCE_SETUP | 无独立操作名；decision narrative_effect、Scene/knowledge working sets 可描述 | Story 跨场；Scene 场内；超许可回 adaptation | WHAT/WHEN 有片段表达，缺 HOW MUCH/after which response 的闭环 |
| 心理→行为；解释→冲突；总结→Scene | EXTERNALIZE + CinemaExpression channels | cinema 提表达方案；Scene 写具体过程；DPD/Performance 解释/实现 | 容易把可拍动作当已经完成“冲突” |

本片同一共同生活源单元展开到 S05–S07，S10 的规则/资源冲突重组也证明平台不只有逐页摘要能力。改编的自由有 owner；未解决的是使用与审阅质量，不能授予 Director 或 Prompt 补写权。

## 4. Scene / Beat Dramaturgy

[Scene skill](/Users/zy/historical-plugin/drama-plugin/plugin/skills/scene-development/SKILL.md)和 [scene-craft-proof](/Users/zy/historical-plugin/drama-plugin/plugin/skills/cinematic-screenplay-incubation/references/scene-craft-proof.md)已要求当前欲求、阻力、失败后的策略变化、转折后果；[literary-craft](/Users/zy/historical-plugin/drama-plugin/plugin/skills/cinematic-screenplay-incubation/references/literary-craft.md)已把对白定义为对听者行动。

当前问题分四层：

1. **规则已存在，但执行未充分兑现。** S02 第一对白虽是请求，却在男人的参与/拒绝过程充分发展前携带完整核心信息。
2. **Granularity 不同。** screenplay.json 的 B02 是整场；R2 S02-appeal 又把两次请求与较晚反应放进同一 actor beat。字段有 objective 不等于存在来回作用的交易链。
3. **R2 Gate 验证载体，不验证过程。** [validate_beat_playability](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/screenplay_playability.py:31)检查动作出现于正文、actor/target；不校验其先后、刺激来源、对方状态如何导致策略变化。
4. **不能靠补字段自动修戏。** 未来结构只能要求可追踪的依据；人类/专业审阅仍须判断反应是否可信、过程是否需要、能否删除而不影响后续。悬置、短回应、梦中非因果段落允许有明确意图，不统一套八步公式。

## 5. DRAMATIC_INFORMATION_RELEASE_AUDIT

系统并非只有 WHAT：Bible receipts 已有 speaker、information ID、beforeBeat、channel，checker 检查角色在做决定前是否得到信息；DirectorScenePlan 有 audience_knowledge；Editorial 有 VisualInformationBeat 与 CutMotivation。

但三者解决不同问题：**角色是否可能知道**、**观众总体知道什么**、**镜头何时给视觉信息**，不能直接证明“一条信息为何在这一次对方阻力之后出现”。

| 维度 | 当前 | 本片断点 | owner |
|---|---|---|---|
| WHAT | 源事实、对白、知识 ledger | 核心事实可读 | Source/Scene/Dialogue |
| WHEN | beforeBeat 与场景宏观 audience knowledge | B02 粒度不足，首句内部信息释放未被检查 | Scene；跨场 Story |
| HOW MUCH | prose/作者判断 | 母亲出事、需要帮助、跟随、急迫集中于首句 | Scene 决定释放量，Dialogue 写原文 |
| THROUGH WHOSE ACTION | LineDPD dramatic_action / target | 请求标签存在，阻力前后的不同策略未完整区分 | Scene 过程→DPD解释 |
| AFTER WHAT RESISTANCE | transition trigger/interaction timing 可表达 | 没有把初次身体停住与真正进入女孩处境区分为审阅条件 | Scene / DPD；Director判表达清晰度 |

“先生……我妈妈出事了。跟我来，快！”是可理解的请求；就本次希望让观众经历“女孩闯入他的世界”的目标看，它是 **DRAMATICALLY_PREMATURE** 候选诊断：完整信息先完成交代，随后才展开男人真正听见、女孩误判与挫败。不是断言真实紧急求助者不得立刻讲事实，也不是证明必须先加某句台词。

EXPOSITION DELIVERY 诊断：主要作用是让观众立即掌握四项剧情信息。
DRAMATIC DISCOVERY 诊断：信息如何改变对方行为/希望/误判，并因阻力改变策略。当前后半场已有这种机制；前段缺少其对信息顺序的约束。不能只润色对白。

## 6. Rhythm：当前拥有多层，连接仍薄

Story/episodeArchitecture 拥有 build、climax、release；Scene 拥有等待、失败、再次尝试、反应的因果节奏；DPD 有 transition/continuity；Director 有 performance_rhythm；[EditorialRhythmPlan](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/dramatic_editorial.py:176)有信息、reaction/cut/hold。

因此“只有 rhythm_speed 或时长”不成立。缺口是这些层级如何继承同一个未解决欲求/代价，而不是各自填写节奏词。剪得快不等于信息成熟，停顿长也不自动深刻。等待谁回应、未得到什么、为何下一策略改变，应回 Scene/DPD；Editorial 实现该等待，不代写因果。

## 7. S01–S16 全片非修改式采样

下表根据当前正文逐场读取；不以旁边说明弥补正文，不是成片效果判断。关注顺序/信息密度/推进/agency/状态变化/重复。

| Scene | 正文可见过程与状态变化 | 信息 / agency / 节奏诊断 |
|---|---|---|
| S01 | 谈论中撤退；被追问后不答；离开又停听，无人叫他 | 退出是行动，停听暴露尚有关系需求；不是普通转场空停顿。缺口是 sidecar 是否保留对未被挽留的回应作用 |
| S02 | 星→身体被拦→完整请求→迟来转脸/希望→收手推责→再抓→驱赶→女孩转向他人→进门 | 有后续反应与升级，不能说全场没戏；首轮信息释放早于充分试探/阻力过程 |
| S03 | 枪/袖口→手与自辩→邻门咳嗽→门把前未开→回坐面门入睡 | 过去接触与当前他人需求形成推进；不是四个无关象征。需区分动作触发与事后解释，不能只靠“愧疚”标签 |
| S04 | 梦中枪击、埋葬、滴水、旅途、思念旧地 | 悬置与主观体验，不能机械要求现实因果；压缩叙述风险应与梦的保护边界一起审，不强补宇宙解释 |
| S05 | 怀疑欢迎；抬枝未成→他人留位置→再试参与 | 已有失败/回应/再试；把一段共同生活展开为可参与的 Scene，不是男人只看 |
| S06 | 接果失败→孩子等待→再接；歌声相让；孩子靠近后手完成接触 | 明确释放与加入；与 S05 类似的学习结构，但任务从接纳延至触碰/共享，可有功能差异 |
| S07 | 他要救临终者→被温和阻止→不解众人接受→手终于放开 | 认知冲突与行为变化成立；不可为了升戏改成无死亡乐园或强制哭泣 |
| S08 | 男人参与游戏并藏果/说谎→另一人受排斥→他欲挽回/获关注→关系改变→宏观跳跃 | 男人是致事者，不仅反应者；局部过程与历史摘要接缝高风险。堕落的唯一机制本来不能被坐实 |
| S09 | 手的争夺→血→群体分裂；界线、动物与歌声变化 | 高压缩历史段，易成为事件列举；有不可逆后果，不能把未详述全部当缺陷 |
| S10 | 规则先保护孩子，随后排除；男人献水介入被人群推回 | 有独立选择与失败；制度功能/代价同时显现。信息不是纯口头解释，结局是否继承至后场需检验 |
| S11 | 邀请共享→女人护食/伤口拒绝→孩子未食离开 | 哲理对白依伤口和资源展开；仍有命题代言风险，需检验女人自身目标而非仅反驳男人 |
| S12 | 安全承诺→强制排斥→男人阻止→被定义为对立者并拖离 | 与 S10/S11 同属介入受阻，但代价从拒绝升到公开强制；若演为同样“一次受挫”，层级会丢失 |
| S13 | 助伤者未成→认罪求刑/求十字架→他人自己的损失/实际木材需要→无人接纳救赎方案 | 峰值是自罚方案也失效，agency 有但失去支配结局；不能压成又一场旁观反应 |
| S14 | 醒后推开枪、狂喜；想代人提水，实际按需要扶门 | 释放与行动尺度修正，有恢复但非全能；不能把喜悦一律压小 |
| S15 | 梦被质疑→承认记忆有限与自身污点→小行动延续关系 | 信息密度偏高，有自我说明风险；与 S01 对照为不再退出，不是原样重复谈论 |
| S16 | 女孩回避→承认此前拒绝→女孩试探他会否跟随→他等候再进 | 行为性收束而非母亲结果揭晓；保持未决事实，是开放结尾，不是缺失答案 |

总体已有 build（接纳）、turn/irreversibility（S08–09）、escalation（S10–12）、climax（S13）、release（S14）及检验/余波（S15–16）。最需后续审阅的是 S08–12 的压缩桥接和 S10–12 失败结构是否真正累积；不能宣称全片毫无层级。S05–07 的长呼吸也不能按固定速度删去。

## 8. 未来 Gate 需求（不实施、不冻结字段）

**Adaptation Freedom Gate**：每一实质变更说明改了什么、电影必要性、保留了哪些保护事实、何 owner 授权、改善什么戏剧功能；联系现有 decision/source mapping/review，而非第二 Canon。

**Dramaturgy Gate**：重要 Scene 能从正文证明 entry、欲求、阻力、作用与回应、策略/关系变化、exit；允许审阅说明为何某项不适用。先检查过程，再检查台词自然度。分辨“字段存在”“正文证据”“专业判断”。

**Information Gate**：重要信息的角色知情、观众可知、释放数量、触发动作、先前回应必须可以追踪；必要时标记其首次释放过早。不是所有信息都要延迟，不预设必须增加对白或场次。

详细未来评价轴和反例见 reconciliation。本轮不产生 R3 剧本。

