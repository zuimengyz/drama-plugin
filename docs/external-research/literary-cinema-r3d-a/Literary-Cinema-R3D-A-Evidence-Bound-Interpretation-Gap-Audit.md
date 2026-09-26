# Literary Cinema R3D-A — Evidence-Bound Interpretation Gap Audit

> 2026-09-26 · NON_RUNTIME / ARCHITECTURE DESIGN INPUT · SELF_AUDIT。本文所有新增解释、义务与结构均为审计建议，未获用户采纳、未写入创作源或 Runtime。R3 candidate 保持 NOT_ADOPTED / R3C_BLOCKED_BY_RUNTIME。证据定位、版本及原文锚点见 [Evidence Index](Evidence-Index.md)。

## 五层表示及证据规则（设计，不实施）

| 层 | 本轮定义 | 例子 | 可做什么 / 不可做什么 |
|---|---|---|---|
| SOURCE FACT | 指定原文明确事件或叙述者明确陈述，保留 POV | A005 望星后决定今夜自杀，且不知原因 | 可核对 offsets；不证明自述为客观宇宙真相 |
| SOURCE OBSERVATION | 对一个或多个事实的可复核模式，不附象征结论 | A005、A018–019 关联两次星的出现 | 单独 evidence record；不自动晋升 motif |
| INTERPRETIVE HYPOTHESIS | 对观察意义的可质疑命题 | 星把被拒绝的现实带入梦旅 | 有 scope/support/counter/alternatives；不直接驱动生产 |
| WORKING INTERPRETATION | 比较后暂选、仍保留异议的电影方向 | 重返关系而非证明世界已修复 | 可供设计讨论；不伪装用户采纳 |
| APPROVED INTERPRETIVE SPINE | 当前改编版本获准使用的一组链接 | 已批准 item 引用 I_EXIT、D02、D14、D16 | APPROVED_FOR_THIS_ADAPTATION；不是 OBJECTIVELY_TRUE_MEANING |

不把五层塞入一个 `meaning` 字段，也不把五层全加进当前 Origin enum。Origin 继续标 SOURCE_FACT / INTERPRETATION / ADAPTATION_INVENTION；五层 epistemic role 与 adoption 状态分开表达。上游 observation/hypothesis evidence 由 literary-source-analysis 审阅；电影选用由 adaptation/Director 按各自权限提出，用户批准高杠杆取舍。Film Board 是同一记录的视图，不再储存第二套意义。

每个重要 hypothesis 的最小证据记录：稳定 local id、revision、命题、scope、观察引用、来源 package/anchor pins；每条 support 的 type（DIRECT_TEXT / RECURRENCE / STRUCTURAL_PARALLEL / CHARACTER_BEHAVIOR / DIALOGUE / ENDING_ECHO）、实际支持哪部分、强弱与限制；反证及搜索范围、替代解释、confidence理由、采用/保留/拒绝状态、审核人与批准引用。Source fact 自带叙述层与可核对定位，不能只存一句摘要。

同段中的两句、同源的翻译与摘要不算三个独立来源。多锚点也不是多数投票；一个关键反证可限制十个弱联想。“未找到反证”须记录检查了哪里，不等于证明没有反证。多个强解释可共存为 MULTI_VALENT；证据不足为 OPEN；含强冲突为 CONTESTED。分歧项保留各自 id，不融合成无从驳斥的散文。

## 当前真实断点

| 编号 | 证据 | 断点与影响 |
|---|---|---|
| G01 | contracts/creative_source.py SourceUnit + validate_literary | 只核 supports 指向事实，未要求支持类型、反证、范围；字段合法不等于命题成立 |
| G02 | PhilosophicalCore.ambiguity | 有总体歧义，但不说明它限制哪个 hypothesis、哪些部门不应选边 |
| G03 | StageReview、当前包 reviews | 自审 APPROVED 与用户采用不同；无紧凑 Film Board 的精确采纳对象 |
| G04 | source_map、director.source_intent、trace_intent | 来源/父链 freshness 已有；解释→部门 obligation→专业 output 的端到端保留凭证不足 |
| G05 | R3 D02/X02；Director S02 primaryFocus | 引用了 E_STAR 不等于传达星与今夜决定；局部女孩戏成功可掩盖此前精神节点 |
| G06 | U_REL_GIRL；characterArc alive / C_FRIENDS ordinary | “未完义务”混进 SOURCE_FACT 陈述；扶门、重访等电影成分混在 INTERPRETATION state prose | 

G06 不是本轮修改请求。U_REL_GIRL 中求助、拒绝、后来找到有直接证据，但“未完义务”是解释。C_FRIENDS ordinary 自述“电影将两次听众合成”应追 D15；C_MAN alive 的“出门”与邻人扶门应追 D14；sealed 的楼梯停听须追 D01。当前 enum 和 validator 能防错误类型引用，却不能读出这种句内混层。这是作品理解需要证据治理的实证，不是新大 Skill 的理由。

## Interpretive Confidence

分别记录三条轴，不能相互换算：

- source fact confidence：VERIFIED_TEXT / ANCHOR_MISMATCH / UNRESOLVED_VERSION；只断言指定文本确有此陈述。对自述可靠性另列 qualification。
- interpretation confidence：HIGH（关键直接关系或独立结构回声支撑、已查主要反证）、MEDIUM（有限推论且有竞争解释）、LOW（单处联想/缺行为后果）、CONTESTED（强证据互相限制）。不是概率，不从模型语气生成。
- department applicability：REQUIRED / CONTEXT_ONLY / NOT_APPLICABLE / UNRESOLVED，逐 scope/consumer 由专业审阅确定。HIGH 文学关联也可能对 Costume 为 NOT_APPLICABLE。

HIGH 必须含证据理由与削弱条件；用户选择 LOW 的创作联想也不能将 confidence 自动升 HIGH。若超出源支持，则标改编发明并按既有改编边界处理，绝不变 SOURCE_FACT。原文明确不知道的原因，即使专家与用户都喜欢某假说也须保留未知。

## USER_INTERPRETIVE_HYPOTHESIS / USER_HYPOTHESIS_TRACE

用户原命题作为 PRIMARY_USER_INTERPRETIVE_HYPOTHESIS：不断阅读、思考、认识世界→愈知自身与世界荒谬、虚无、无能为力→联系失去意义→自杀。以下判断均限指定版本，不对其他译本或作者心理作结论。

| 成分 / verdict | Direct support | Indirect support | Counter-evidence / uncertainty | scope / confidence |
|---|---|---|---|---|
| 学习加深“我荒唐”的自知：SUPPORTED | A003 / C_MAN、U_PRIDE：学校/大学、学得越多越确信自身荒唐 | A030、A037 的知识与生活张力 | 不能把自我荒唐扩大为客观“世界荒谬”结论 | 人物前史；HIGH |
| 不断思考最终推导虚无：PARTIALLY_SUPPORTED，线性因果 OVERSTATED | A003 一切无关的确信；A007 白天阅读 | 学习与羞耻、骄傲相邻叙述 | A003 明说几乎不再思考、没有解决任何问题；转折部分突然且原因不知 | 入场历史；MEDIUM，完整因果 OPEN |
| 世界/他人对他失去意义：SUPPORTED（自述立场） | A003 几乎不注意人、碰撞别人；A007 噪声忘却 | A004 冷淡判词 | A009 同情、痛与羞耻仍在；A027 自称从未停止爱旧地球 | 入场 belief，不是其全部情感事实；HIGH |
| 无能为力为自杀核心原因：OPEN / OVERSTATED 若当定论 | 开篇无明确直接陈述 | A003 未解问题、A005 两月延宕可容此读法 | 冷漠、骄傲、羞耻更直接；A038 的无力属梦后段，不能倒投前史 | 前史动机；LOW–MEDIUM，不排他 |
| 退出世界→重新参与：SUPPORTED 作为主轴假说 | A005/A009 拟消失却仍有责任感觉；A039选择活；A041找到女孩 | A028–033 接纳、A038自罚失效、A040传讲 | A027“从未停止爱”；A036参与也能造成伤害；A040确信仍绝对 | 全片关系轴；HIGH但非唯一主题 |

建议 working formulation：他以“一切无关”停止求解与参与，却不能取消同情、羞耻、骄傲与对旧世界的依恋；梦让这种关系矛盾经历接纳、破坏和求刑失败，醒后选择继续回应，同时仍可能自负、犯错。**这句话是审计建议，未批准，也不是替换 PhilosophicalCore。**

梦的关系：知识与生活冲突延伸到 A030/A037，但作品不是简单反阅读/反科学。结尾关系：A040同时承认错误与宣称真理；A041落实找到女孩。不能把它压成“顿悟以后完全正确”或“知道一切无解所以随便行善”。

## 版本、批准与 stale（未来行为）

1. 源版本变化：保留旧证据供回放，新 source pin 下逐条重验引用；旧批准不继承。
2. hypothesis/选用范围/负边界变化：新 revision；批准绑定精确被选 item 集、未决项处理、work/branch/scope 和证据版本。只改措辞也不能悄悄覆盖已签内容。
3. 用户否决“星=希望”：保留原文与旧假说，撤销当前采用状态，更新选择，标记冲突消费者待重审。模型 HIGH 不可挡用户版本选择。
4. 依赖图：analysis → philosophy/adaptation（涉及者）→ intent → implication links → 专业原件 → Shot/IR/Prompt/Book/adoption receipt。影像不删，旧批准变历史；新生产不得用 stale 决定。
5. 使用实际消费边。当前 package 级 hash 粒度会使同包编译输入整体失效，遵守既有 gate，不假装已支持逐命题免重编译。未来重审可按受影响 scope 缩小，但绝不能只改 hash 重新盖章。
6. Board 展示审批状态只是视图；receipt 证明谁批准哪个版本，不拥有内容。未审则 UNREVIEWED，源正确不等于用户同意。

## Over-Interpretation / Generic Symbolism / Theme Word guards

| 未来反例 fixture | 预期判定与修复 owner |
|---|---|
| A010已死兄长出现一次，就因 kind=MOTIF 强制全片回收 | 不成立：类别标签不证明跨场功能；source-analysis 限为梦逻辑例证 |
| 星=希望 | A005为强反证；不得作为无争议解释下发 |
| 黑色=死亡、红色=危险、雨=悲伤、门=选择 | 缺本作证据则 UNSUPPORTED/LOW；夜雨事实不授权象征 |
| 黑夜自动等于抑郁；虚无自动低头慢走 | 撤销自动映射；Character/DPD 保持具体状态与条件，不医学诊断 |
| 贫困自动破衣；自杀自动邋遢/黑眼圈 | 无具体 source/批准资产决定则不得写入；Specialized Asset 回上游 |
| 女孩=救世天使 | A009“救了我”是因果自述，不证明神学身份；保留她自身求助 |
| 梦=无死亡完美乌托邦答案 | A031死亡、A036–038分裂、A034叙述不确定反驳 |
| 每部门各写一份“爱/存在/救赎” | 缺同一 approved id 与专业义务链接，判 interpretation drift |
| 将整段哲学 prose 直接送 Prompt | 返回专业转译；禁止以 provider“聪明”补洞 |
| 只列支持不查 A027/A040 等反证 | 不能进入 HIGH/批准候选；补 scope 与反证审阅 |

这些是未来语义审阅用例与结构校验设计，不是本轮已通过的可执行测试，更不是用关键词 blacklist 自动判断艺术。
