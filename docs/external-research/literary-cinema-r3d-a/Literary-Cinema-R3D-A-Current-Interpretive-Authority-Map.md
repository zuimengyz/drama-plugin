# Literary Cinema R3D-A — Current Interpretive Authority Map

> 2026-09-26 · NON_RUNTIME / ARCHITECTURE DESIGN INPUT · SELF_AUDIT。本文所有新增解释、义务与结构均为审计建议，未获用户采纳、未写入创作源或 Runtime。R3 candidate 保持 NOT_ADOPTED / R3C_BLOCKED_BY_RUNTIME。证据定位、版本及原文锚点见 [Evidence Index](Evidence-Index.md)。

## 结论与当前基线

需要统一的、有证据且获准的电影解释主轴，但现有 Cinematic Intent 已有等价承载。**拒绝新顶级 Interpretive Spine Skill；拒绝第二主题 Canon。** 首选给既有 source analysis 审阅及 Cinematic Intent linking artifact 加小型证据/采纳/消费 facet。不是把同一主题抄进每个部门。

实际 Git 根是 `drama-plugin`，不是上层工作目录。当前 HEAD 为 `df625f9d01cc62c3f1ffed2774e88166ab37bae5`；MCP 为 `d49f17db12c8c0201c9ae98641890d61fe519762`；Java 为 `63494a5afed1db6b55d5e607aac7259bd9bc890a`。开始时 plugin 仅有既存未跟踪 `docs/external-research/.DS_Store`，其他两仓干净。见 baseline-integrity.json。此轮只增加本报告目录，不把旧报告 HEAD 当当前实现。

当前指定源为 PG40745-DREAM 英译指定版本，非另一个中文译本。A000–A041 的引用区间是该 SourceArtifact.text 的字符偏移，不是 HTML 字节偏移。全文的第一人称自述须保留叙述归属：“他说世界不存在”是文本事实，“世界确实不存在”不是。

## 当前解释与审批链

| 层 | 已有 owner / artifact | 谁审核、谁消费 | 本轮确认的边界 |
|---|---|---|---|
| Source Canon | designated SourceArtifact + SourceAnchor | literary-source-analysis；编译器核 hash/quote | 不可用 R3 或用户假说反写原文 |
| LiteraryAnalysis | SourceUnit SOURCE_FACT / INTERPRETATION、supports、event_order | source specialist StageReview；Philosophy/Adaptation | 支持指针可验证，支持强度和反证未结构化 |
| PhilosophicalCore | philosophical-core；问题、价值两极、选择、后果、ambiguity | specialist review；改编、编剧、Director source_intent | 已解释作品；不需要另造 Philosophy2 |
| Preservation / Adaptation | literary-adaptation；preserved、D01–D17、compression | StageReview + R3B preservation_checks；Cinema/Story | 选择保留/外化/压缩均是改编行为，不是新 Source Fact |
| CinemaExpression | literature-to-cinema；X01–X16 | specialist review；Screenplay/Scene/Director | 将选择转为可拍义务；没有摄影、灯光执行权 |
| Story / Dramatic Bible | story-architecture + incubation | 来源与创作审阅；Scene、Character | 已有“自封→回应”、S13峰值、S06/S14释放、S16收束 |
| CharacterArc | character-dramaturgy；九个主人公阶段及其他人物 | 人物专业审阅；DPD、Director、资产上游 | stable/arc-stage state 不等于逐 Beat 动作 |
| Director Vision / cinematicIntent | director；cinematic_interpretation、meaning/why/priority、scope/parentRef | Director设计审阅、独立的用户批准；部门请求 | 选择呈现重点，不能重做文学分析或替代心理任务 |
| Professional departments | 各自 Bible / typed original | 专业审阅、Director协调；Shot/IR | HOW 仍由各 owner 写；引用意义不转移作者权 |

当前源包 reviews 的 `APPROVED` 明说为同一作者自审，并非用户批准；R1 director-screenplay 为 `USER_APPROVAL_PENDING`，`userApproval=false`，workspace `adoptedHead=null`。R3 director-performance-candidate 仅三场且为 DESIGN_FIXTURE_ONLY。不能因字段叫 APPROVED 或 CANON pin，就声称用户已经认可了本轮解释。

## INTERPRETIVE_CAPABILITY_MAP

| 能力 | 已存在 | 真实不足 | linking 是否够 / 最小 facet |
|---|---|---|---|
| LiteraryAnalysis | 事实与解释分开；解释只可支持于 SOURCE_FACT | observation 与 hypothesis 混在 prose；无竞争组/反证/证据权重 | 来源不重造；审阅证据需小 facet |
| PhilosophicalCore | question/conflict/value/choice/consequence/ambiguity | 整包解释无分命题 confidence/范围 | 链接命题 ledger 即可；不增主题本体 |
| Preservation | mustKeep、关系事件、人物弧、叙述身份 | 被保留单元不等于意义已经被观众接收 | 接到 interpretation obligation；不重造清单 |
| Adaptation | reason/narrativeEffect/expression、操作和目标 | 版本 thesis 的采纳理由分散；R3 D02 星的呈现理由变薄 | 引既有决定和用户版本选择；不复制决定 |
| CinemaExpression | 各 destination、channels、非语言替代、明确性例外 | 一个整场 X02 不能证明每个关键节点被保留 | 意义义务→existing carrier/专业输出的链接 |
| Story | 全片问题/阶段/知识与因果 | 故事一致不等于解释传播一致 | 只链接同一上游 item，拒绝 StoryTheme2 |
| Character Dramaturgy | narrative/emotional/belief/behavioral/relationship states | 少 scope 化的存在状态证据；混合源/发明成分 | 先复用 state，需 evidence pointer 与 applicability |
| Director | source_intent、层级 intent、部门请求、版本 pin | 无已采纳 hypothesis set、反证披露与逐部门解释消费证明 | 扩现有 intent artifact，小 facet 足够 |
| Embodiment | package pointer/hash、条件化观察、稳定/阶段区分 | 上游状态未批准时不能自己补 | 链接人物阶段，无新增心理字段 |
| Camera | perception-first、subject_hierarchy、spatial_readability | 无解释采用版本→知觉义务的强制对应 | 消费 Director 转译，不研究小说 |
| Lighting | motivation/visibility_priorities、实际光源 | 注册依赖主要 environment-art/camera；无解释 receipt | 义务通过 source refs 到达；不另作 mood 解释 |
| Sound | source/listener perspective、远近、注意/物理沉默区分 | 注册静态依赖并不直接证明消费 Director 当前解释 | 精确请求/消费凭证，不必全图增依赖 |
| Editorial | holds、reaction、montage、scene transitions | 有时间权力，缺 motif 出现间的意义保留证明 | 复用现有 transition/intent refs |

证据：`contracts/creative_source.py` 的 SourceUnit / PhilosophicalCore / CharacterArcState / SourceMapEntry；`creative_source.py` 的 validate_literary / review_hashes / _compile_source；`director.py:208` trace_intent 与 `:235` source_intent；`professional.py:22` 起的 registry 及 `:206` validate_bible。具体可点击链接在 Evidence Index。

## 为什么现有能力仍不够

`source_intent` 只是把 philosophicalCore、adaptation、characterArc、cinema、themeExpressionOrder 投影到 Director；它没有比较解释，也不能证明某个请求选择了哪条解释。SourceMapEntry 有 owner/path/anchor/decision，却没有 hypothesis version、counter-evidence、approval scope、department applicability。

既有 cinematic-intent sidecar 已有 id、meaning、why、priority、source、avoid、scope、parentRef 以及整体覆盖检查。它是最接近目标的现成结构。缺口不是容器，而是其中解释的证据来历与采纳状态，以及最终专业记录对该解释的响应证据。专业 registry 的开放 values 与 source_refs 能引用内容，但任意 prose 有来源不等于它被允许成为全片解释。

更直接的证据是既有 `01-source-grounding-and-spine.md` 的C节已经明确名为“本片的解释与因果脊柱”，B节还区分了多项文本问题与解释。它不是空白能力；但这份R1 prose没有提供逐命题的竞争/反证/采用版本与R3部门消费凭证。因此不能把本轮任务误判成第一次为本片建立解释。

本片的“退出↔参与”并非本轮新发现：I_EXIT、I_END、PhilosophicalCore、Dramatic Bible 已各自表达。需串联它们并纠正证据混层；本轮不再宣称创立一套新的作品哲学。
