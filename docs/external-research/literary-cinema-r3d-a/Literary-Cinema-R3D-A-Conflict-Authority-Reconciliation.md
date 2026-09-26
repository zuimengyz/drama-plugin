# Literary Cinema R3D-A — Conflict / Authority Reconciliation

> 2026-09-26 · NON_RUNTIME / ARCHITECTURE DESIGN INPUT · SELF_AUDIT。本文所有新增解释、义务与结构均为审计建议，未获用户采纳、未写入创作源或 Runtime。R3 candidate 保持 NOT_ADOPTED / R3C_BLOCKED_BY_RUNTIME。证据定位、版本及原文锚点见 [Evidence Index](Evidence-Index.md)。

## Authority 裁决

下表为本轮设计裁决。`UNRESOLVED_SAME_SCOPE_AUTHORITY_CONFLICTS=0` 仅表示下列职权已有明确归属，不表示开放文学问题已解决、原件已修复或Runtime已实现。

| 冲突 | 裁决：谁拥有哪个值 | 谁消费 / 出现冲突回哪里 |
|---|---|---|
| PhilosophicalCore vs Interpretive Spine | Philosophy保有原作问题/价值/歧义解释；spine引用并选择其对本版的用途 | 不复制问题成Theme2；源意义争议回source-analysis/philosophy |
| Adaptation Thesis vs Spine | Adaptation拥有保留与强调什么、允许哪些改动；spine是这些选择在全片中的一致应用链接 | 改变取舍先回adaptation；Director只组织应用 |
| Story vs Interpretation | Story拥有事件结构与跨场因果；interpretation证据不重写事件 | 解释要求新结局则上返Story/Adaptation并获相应批准 |
| Character Dramaturgy vs Existential State | 同一owner；state是阶段层面的belief/relationship/behavior内容 | 不另建state作者；缺源回Character |
| DPD vs Character State | Character给阶段/稳定约束；DPD给Scene/Beat/Line任务、策略、subtext、回应解释 | DPD不能改全片核心；当前Beat不反写package |
| Director vs Interpretation | Director选观众经验、优先级、协调；上游负责证据命题，用户采纳方向 | source_intent仍是只读投影，禁止Director代做文学分析 |
| Motif meaning vs Camera | source-analysis拥有文本模式与假说；adaptation选择电影功能；Director保护呈现重点 | Camera只写可感知关系的HOW；无权定义STAR意义 |
| Motif visual / sound realization | Camera/Lighting/Color/Specialized Asset/Performance各自视觉域；Sound声场，Music配乐，Diegetic Vocal源内唱 | Shot覆盖、Editorial时间组织；无万能Motif owner |
| World fact vs World relation | Source/World事实；Character拥有角色关系立场；Director拥有观众主客观关系 | 环境资产不能把心理写成城市客观真相 |
| Lighting vs mood interpretation | Lighting拥有动机光/可见性；情绪意义来自当前批准意图 | 冲突回Director/Character，不以光重写世界 |
| Sound vs thematic interpretation | Sound拥有声源、距离、听觉注意；不判哲学 | 安静可能物理/主观/无配乐，各自核源 |
| Prompt vs interpretation | Prompt只等义投影批准可见/可听义务 | 抽象缺口回专业owner，不让模型补文学 |
| Costume/Face vs State | Specialized Asset拥有具体外观服装；Look临时状态；Embodiment条件化习惯 | 禁虚无→破衣/驼背/黑眼圈，缺据保持未知 |
| Medium vs meaning | movie runtime pin决定LIVE_ACTION/CG；不解释作品 | 解释位于媒介上游，媒介可反馈实现限制，不改变意义 |
| Approval receipt vs content | receipt仅证明批准对象、版本、scope、来源；Board只展示 | 不允许receipt另写意义或隐含剧情批准 |

## 现有重复风险的处理

Dramatic Bible的question/start/end，CharacterArc的sealed→learning，Director Vision的cinematic_interpretation已分别存在。未来不是把三份prose合并成第四份Canon，而是让同一个intent item引用各自原件，并声明应用范围与专业待答问题。相同命题若有两处完整副本，选择owner原件，其余保留只读投影和指针；不得在本轮静默清理旧文件。

源包自身有句内混层（U_REL_GIRL的“未完义务”、部分arc state带电影发明），应由原source/Character/Adaptation owner在未来授权修订中处理。不能让新的spine通过复制脏标记而宣称已完成证据治理，也不能因旧字段粗糙就让Camera越权。

## MINIMAL_R3D_RUNTIME_SURFACE（仅未来输入）

| 最小面 | 复用位置 | 需要的小增量与验收条件 | 不需要的扩张 |
|---|---|---|---|
| Evidence model | contracts/creative_source.py 的分析/审阅相邻facet；creative_source.py | 可分辨observation/hypothesis，支持与反证指向当前anchor；scope/置信依据/竞争关系可重放 | 新Canon、文学批评Agent、完整概率系统 |
| Film selection/linking artifact | 既有 Cinematic Intent item与Director artifact store；DirectorWorkspace.intent_refs | 选用上游命题、版本、范围、未决政策、用户receipt引用；可从item解析至源 | 新顶级Skill、新业务表、第二Director |
| Approval / stale | 既有SourcePin、approval evidence、current fingerprints | 拒绝旧版本或scope不符；撤销批准也失效；历史读取不等于新生产可用 | 给旧包自动补人类批准 |
| Professional handoff | CapabilityRequest、CreativeRecord.source_refs、professional source maps | 义务id→接收owner→当前专业output/ref→审阅结果；缺必要项明确返回 | 每部门重复存全文解释；全图互相依赖 |
| End-to-end review | 既有intent preservation、department integration/Book评审位置 | 若启用本解释facet，消费链缺失/冲突/stale则不可宣称当前准备完成；语义判断留review | 用字符串命中证明艺术成功 |

先在现有数据容器与审阅流程上证明可承载，再冻结极小typed facet；本报告的候选名不是已实施schema。character state已有字段，world relation已有关系/intent域；初期不需要额外CharacterState或WorldRelation顶级合同。motif occurrence ledger引用原件中的出现，不复制Scene事实。

不修改FP01/FP02，不在这里设计其算法；R3B-R仍是前置独立任务。R3D将来需以R3B-R完成后新HEAD重新核对，本轮读到的是当前df625f9。

## 未来验收用例（不是已执行测试）

1. H-S1/H-S2及其反证可共同采纳，OPEN机制不阻止有界方向批准；缺源则拒绝。
2. 删A005反证、把街星与另一地球合并、把S16新对白标SOURCE_FACT：专业证据审阅失败，各回源owner。
3. 同id新hypothesis版本/新source版本/撤销用户批准，旧Camera/Editorial消费receipt不能通过。
4. 更改星解释不应自动创作服装；但实际消费了旧item的完整Book不能继续宣称current。
5. 三部门共同删除社会生活的反例返回DEPARTMENT_INTERPRETATION_DRIFT，而源有依据的夜暗/黎明前寂静不误报。
6. Prompt收到文学prose应返回专业转译，不生成替代动作；保留approved observable事实的投影可通过结构检查。
7. existing legacy artifact仍可原样回放；未有interpretive approval的旧版不得被追授新能力。

## Host role

Host协调证据、管理假说版本、发现冲突、携带真实批准、检查跨部门一致性。专业owner判断内容，用户选电影方向。Host不推断不可证伪的作者意图，不以模型自信覆盖反证，不直接代写部门方案。
