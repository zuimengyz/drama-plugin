# Prompt A2R — Conflict & Authority Reconciliation

2026-09-26 · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED · STOP AT A2R

本轮完成研究裁决：**READY_FOR_PROMPT_A3 = YES**，仅表示 A3 设计输入已足够明确，不是 A3/A4 执行或媒体验证授权。本轮未设计最终 schema、未修改任何 Runtime/serializer/adapter，未生成媒体。

输入：[A0 source freeze](Prompt-A0-External-Source-Freeze.md)、[A1 capability forensics](Prompt-A1-Capability-Forensics.md)、[A2 local mapping and policy audit](Prompt-A2-Local-Capability-Mapping.md)。证据与结论严格分开：源码/离线编译可验证的机制，不等于图像/视频效果已验证。

## Authority Ladder 与 scope

沿用用户指定次序：

1. Platform Contract / explicit runtime configuration。
2. Work Canon / approved source facts。
3. Validated specialized external knowledge。
4. Platform-validated specialized local knowledge。
5. Experimental external/local rule。
6. Generic heuristic / filler / style prompt。

高层 platform 限制可拒绝不支持的请求，不可借此重写低层 Canon 的故事事实。第 3/4 层也不能因知识更专业而越过第 2 层改变角色。A4 当前知识仍为 LOCAL_EXPERIMENTAL，外部模型写法也没有本地媒体验证；不能冒充第 3/4 层。先确定 scope/owner，再比较同 scope 权威；reference、当前表演、资产稳定身份不是同一种权限。

## PROMPT_CONFLICT_MATRIX

以下均已有 winner 与未来动作；“resolved”指研究层职责裁决完成，不代表候选代码已实现或视觉效果问题已修复。

| ID | Conflict / trigger | Winner / authority | Loser / boundary | Future action | Resolution |
|---|---|---|---|---|---|
| C01 | prompt optimizer 自行解释作品或补动作 | approved Work/Scene/Director + 原专业 owner，层 2 | P01/P02/P04 只优化表达 | 缺可见载体退原 owner；distiller 不新增事实 | RESOLVED |
| C02 | provider family 写法覆盖戏剧意图 | Canon 层 2；platform 只决定能否执行 | P08 的表达偏好为层 5/6 | policy 不可重写事件/人物/镜头；不可行回 route/规划 | RESOLVED |
| C03 | 为长度丢 Meaning-critical | 原 owner 批准义务 + hard-limit fail-closed | P16 算法/通用长度目标 | 保留/等价表达仍超限则拒绝；不得盲截断 | RESOLVED |
| C04 | “20/30–40 词”压过本地限制和必需信息 | actual capability + 语义义务，层 1/2 | B3/B4 社区偏好 | 固定词数 REFERENCE_ONLY；不推广到 Vidu/Seedance | RESOLVED |
| C05 | I2V motion-only 删除必要身份/接触/信物 | approved reference duties + 必需 current/temporal facts | P10 的无条件解释 | 先证明 reference 承载，保留必要 anchor/constraint | RESOLVED |
| C06 | reference 肖像姿势/灯光覆盖本镜头 | Blocking/Performance/Lighting 当前原件 | 身份 reference 未获 current-state 权力 | 保持 carry/exclude；区分整帧 source 与 portrait | RESOLVED |
| C07 | video prompt 重设计 still 人物/场景 | 同一批准 Asset/Scene/current state | 视频 family policy、模型漂移或新描述 | shared source pin；仅合法时间变化可变，不新造静态身份 | RESOLVED |
| C08 | shared IR 被误解为 shared final policy | 各 task/mode 的合法执行语义 | 单一通用文本模板 | 共享语义、分投影；仍由 core 单一最终编译入口按 scope dispatch | RESOLVED |
| C09 | family adapter 成为第二 prompt writer | core compiler/serializer ownership | transport adapter 的 enhancer/润色 | family policy 在 core projection 内选择；adapter 只 schema/transport | RESOLVED |
| C10 | 字符级/embedding 去重合并不同 actor/time | source-bound scoped obligation | 不带主体/时态的近似相似度 | 不确定等价不合并；起终态、不同角色保留独立覆盖 | RESOLVED |
| C11 | 同一身份被多 owner 重述，重复越多越“保真” | 稳定 Asset 事实 + Reference duty 各自唯一 owner | 多份同义身份副本 | canonical obligation 合并表达，保留多来源 trace，不合并异职能 | RESOLVED |
| C12 | 所有 cinematic/quality 字样硬删 | runtime medium 和 approved visual requirement | 通用 filler blacklist | 保留媒介/参数；纯赞美无用途才移除；需实测语言增益 | RESOLVED |
| C13 | eval framework 或 grader 定义艺术目标 | Work/Director 批准需求；QA 观察职责 | P21 的错误用法 | grader 校准并报告 UNKNOWN；不据总分改 Canon | RESOLVED |
| C14 | 外部工具/路径引用替代模型实际可见事实 | platform 实际输入能力 + Canon | Sentry agent 文件读取模式机械套用 | Host 可解析 pin；provider 接受事实与合法媒体，不能只给本地路径 | RESOLVED |
| C15 | 直接导入 LLMLingua/fal runtime | 现有 platform 边界，用户禁止 | P16/P23 Runtime 接管 | REJECT；仅借预算/强制保留/实验流程概念 | RESOLVED |
| C16 | 为新 Meaning schema 建第二份 Canon | 既有 source/intent/scene/shot owners | 新 Prompt owner 复制主题/场景目的 | A3 先评估复用与 linking；有明确不可表达证据才提最小增量 | RESOLVED |
| C17 | EDIT selector 与 CRITICAL/required 覆盖冲突 | 本用途 required obligation；不静默损失 | “存在于 IR 即已消费”的假定 | 保留现有 A4 显式拒绝；A3 研究 selector→emitted/reference coverage，不能偷改本轮 policy | RESOLVED |
| C18 | reason 删除连带丢约束；reason 全发污染模型 | 原 owner 区分 rationale 与 executable decision | 粗暴全删或全发 | 控制信息留内部，有效约束独立成批准事实后投影 | RESOLVED |
| C19 | 旧 A3 报告缺口覆盖当前 A4 事实 | 当前 HEAD + actual consumer evidence | 旧基线“mapper 尚不存在” | 报告按版本叙述；保留旧报告原件，不改写历史 | RESOLVED |
| C20 | 同时改专业知识与 prompt policy 后归因 prompt | 固定源与预登记实验对照 | 混合干预结果 | Prompt A5 固定 Face/Cinematography 决定，不能复用其知识实验作 policy 胜出证据 | RESOLVED |

**UNRESOLVED_SAME_SCOPE_AUTHORITY_CONFLICTS = 0**。尚未验证的模型效果是 evidence gap，不是未决权威冲突。没有为了得出零冲突而授予 optimizer、grader、adapter 新创作权。

## 唯一未来能力方向

**Semantic-Preserving Prompt Distillation**：以批准戏剧义务为目标，以可见事实为中介，以模型适用语言为输出。Compression 可以是其中的一个受控操作；单独最小化字符不构成能力目标。

专业层已经做 Meaning→可观察行为的局部翻译，尤其 CinemaTranslation、CharacterEmbodiment 和 Performance。未来缺口是把它们与 Scene/Shot 目的、current state、reference coverage、IR 选择、实际 emitted spans 连成可审阅链。保真不要求主题原文出现在 prompt；要求承载主题的批准可见关系没有丢掉。

必要责任边界：

- Work/Scene/Director 确定 WHY 和不可丢失的戏剧义务。
- Blocking/Action/Performance/Camera/Lighting/Asset 等原 owner 确定 WHAT IS OBSERVABLE / HOW；新动作需要其批准。
- Shot/coverage 绑定用途、时点、片段与必要可读性。
- reference owner 确认哪些义务由哪一输入承载，不能以“有图”代替证据。
- distillation/projection 只选取、去真重复、等价表述、检查覆盖和预算；不创造主题、动作或美术。
- core serializer 对一个 task/mode/family 生成唯一可重放最终结果；adapter 不后改。
- QA 以批准义务和真实媒体观察判断，而不是奖励短 prompt。

不在此建立最终 schema、字段 enum、storage API、注册新 Skill 或实施文件清单；以上仅是 A3 应解决的问题与 ownership 裁决。

## PROMPT_A5_EVALUATION_AUDIT

固定 fixture 必须有；否则换 prompt 与换作品/摄影决定混在一起。借鉴 A1 的 P06/P19–22 测试组织法，保留本地 Review/QA 的证据和授权边界。不要把 Promptfoo 的文本答案评分直接当视觉事实检测。

### 固定与唯一变量

每个 pair 固定真实批准 Work/Script/Scene/Shot、Character/arc stage、Asset、姿态/表情/动作/时序、Camera/Lighting/Color/Grade/D1、reference bytes/slot/duties、route/transport/model snapshot、输入模式、尺寸/时长/quality/seed（如可控）等参数、原知识版本。旧/新使用同一 canonical source freeze 和同一语义义务集合。

唯一变化是预登记 **prompt projection policy variant** 及其必然派生的 final text/hash/选取记录。若一个实验同时改变去重与预算策略，只能把收益归于该组合；优先单因素消融。Source facts 不变不等于 prompt fingerprint 不变。不得把摄影/Face A5 的“改变知识决定、固定 serializer”实验偷换为这次“固定知识、改变 policy”。

### Fixture 分类与失败对照

这些是未来选样要求，不是伪造已批准 IDs 或可直接生成的 suite。本轮合成 compiler fixture 只证明链路机制。

| Family | 必须覆盖的案例 | 专门 negative control |
|---|---|---|
| STILL initial | 单人身份、多人关系、关键接触/信物、低光可读性、复杂空间 | 更短但删除关键手/物；身份交换；把尚未接触改成接触 |
| STILL edit/reference | 精确 change/preserve、reference leakage、required selector 省略 | 修改服装同时改脸；把不可见误判为已保留；原 source issue 被当目标 |
| VIDEO T2V | 完整静态建立、动作因果、表演反应、运镜、终态 | 只有动作没有主体/环境；省略反应使意义反转 |
| VIDEO I2V | 固定首帧、必要静态 anchor、动作/持续、受保护接触 | 只写 motion 导致信物/手部关系丢失；无故换脸/场景 |
| VIDEO first-last / reference | 起终点相同但中间必须保持；不同参考职责 | 两端正确而中间松手/穿物；首尾镜头错配 |
| VIDEO supported audio | 精确对白/说话者、同步和获批静默 | 文本相同却错 speaker；不支持音频仍注入对白指令 |
| 跨语言/极短否定 | 中文/英文、左右、尚未、始终、直到、施受者 | 词覆盖高但 actor/action/target/时间反转 |

### 三层验证

1. **结构/来源层**：无网络重放，pins、owner、scope、current、required obligations、合法输入、retained/omitted、最终 payload/hash 等价。known-good 必过、deliberately wrong 必败；不能只查某个词存在。候选将受保护义务删掉，即使更短也立即 FAIL。
2. **文本语义层**：盲评 source obligation 与 actual prompt/有效 reference coverage 的对应，检查绑定、否定、顺序、范围和未授权增加；允许意义等价表达，不强迫旧完整句 substring 作为未来唯一判据。保留不确定与争议；embedding/LLM grader 可辅助，不能成为 owner。旧 Runtime 的 exact checks 在本轮完全不变。
3. **媒体层**：未来另行授权后，观察图片区域与完整视频时间段，按原需求记录证据。STILL 看当前关系/身份/可读性；VIDEO 看 trigger→action→reaction→end 和全程保持，不能只截首尾帧。没有实际输出则 NOT_OBSERVED，不标 PASS。

### 结果与决策

记录所有请求、policy/model/version、源和输入 hash、输出 hash、原始观察、技术失败、grader 错误、UNKNOWN、人工分歧和成本。对照顺序交错、评审盲化，冻结开发集与 holdout；模型不可控随机性如实报告，支持 seed 也不宣称完全确定。样本数量/预算未来预登记，本轮不编造显著性或固定生成数。

硬判失败：任一 Meaning-critical / required visual / temporal obligation 丢失或反转，任何未批准事实新增，任何身份/状态/对白绑定漂移。短、快、便宜、总体美观都不能抵消这些失败。其余指标分别报告 prompt 长度、真实语义重复、可见达成率、各维改善/回归/UNKNOWN、失败率，不以一个主观总分抹平不同镜头问题。

“更短但更空”通过事先冻结的 obligations 和刻意删关键细节的 negative controls 识别；不能将 oracle 改成当前候选刚好具备的属性。媒体质量不明可得 INCONCLUSIVE，不自动采纳。晋级仅限实测 family/model/mode/task/medium，不能从 Vidu I2V 的好结果推广到全部 VIDEO。

## Required Final Findings

### QF1 — 是否缺少 Work Meaning / Scene Meaning / Shot Dramatic Function Contract？

**不缺这三层的全部结构；缺跨层统一的 prompt 保真衔接。** 文学 PhilosophicalCore/Preservation/CinemaTranslation、Scene Beat Bible.scene_purpose、ShotAssembly.dramatic_purpose/CinematicShotSpec.narrative_intent、Director intent hierarchy 都已存在。A3 应优先复用，设计 canonical semantic handoff/coverage；没有证据要求三套新顶级 Canon 副本。

### QF2 — 是否缺少 Meaning → Visible Semantic Atoms 中间层？

**局部能力已有，统一系统层仍缺。** CinemaExpression、EmbodimentRule、ObservableAction 提供直接反证，不能说完全没有翻译。尚缺从意义义务到原 owner 可见事实、reference/IR/实际输出的完整关系及丢失检测。由原专业部门负责具体化，Director 管 WHY，Shot 管用途/覆盖；Prompt Distiller 不获得动作创作权。

### QF3 — STILL / VIDEO 是否必须分开设计？

**YES，边界在最终 task/input-mode/provider-family projection。** 上游 Canon、身份、场景事实、镜头目的、参考职责与来源共享。still 取当前可见截面与 edit delta/preserve；video 取时间变化/持续、表演/运镜/连续性；T2V 必须建立静态上下文，I2V 可在参考确实承载时减少复述。当前已有 static/Vidu 分流，不能声称要从零拆分。

### QF4 — 哪些信息永远不应进入 Final Prompt？

控制数据：source pins/hash、审批、预算/费用、凭据、知识 provenance、QC 分数/原因、失败日志、内部比较推理、未批准提案和非当前未来计划。整篇 Work/Scene 意义及裸主题词不能代替可见事实。它们保留在 source/reason/IR/QA 中并约束选择；批准的当前事实、edit source issue、可见文字与支持的对白是不同类别，不机械按关键词删除。

### QF5 — Atom / Priority / Budget / Semantic Dedup / Meaning-critical preservation 是否值得？

**YES，复用并补全现有 Fact、CharacterPromptFact、priority/budget 与 receipt。** 缺的是 scoped obligation、drop-cost 判断、意义等价去重和选择后覆盖，而不是缺任意“atom”容器。A2 已逐项分析候选属性，未定义最终 schema。坚持 one semantic obligation, one emitted phrasing per applicable scope，同时保护人物/时点差异与必要端点。

### QF6 — Compression 还是 Distillation？

**Semantic-Preserving Prompt Distillation。** 长度是满足保真条件后的效率指标。现有 source-bound whole-leaf 投影能证明来自哪里，不能证明意义完整；简单删词可能保住名词而反转动作关系或时间。外部压缩算法不适合直接接管视觉 Runtime。

### QF7 — 是否适合进入 Prompt A3？

```text
READY_FOR_PROMPT_A3 = YES
SCOPE = DESIGN_ONLY_READINESS
PROMPT_A3_EXECUTED = NO
UNRESOLVED_SAME_SCOPE_AUTHORITY_CONFLICTS = 0
STOP_AT = A2R
```

A3 的唯一清晰输入：复用既有意义来源；定义跨层语义义务与可见覆盖；维持原 owner；分 still initial/edit 与 video 各输入模式、再分家族表达；保持 core 单一最终 writer 与 adapter 无创作权；建立 required coverage、semantic dedup 和预算失败边界；把未来 policy-only A5 与知识 A5 分开。家族效果与 soft budget 未知留待验证，不阻止设计，也不允许当作已验证值实施。

## Stop Gate 与完成证据

四份正式报告 + 原始冻结、源码索引、合成离线编译、72 项既有测试结果、completion check。初始已有 `.DS_Store` 保留。

要求与结果：0 runtime behavior changes；0 paid generations；0 serializer modifications；0 adapter modifications；0 external skill installation；0 copied prompt bundle；0 unresolved same-scope authority conflict。外部源码 clone 只在研究隔离目录，不执行其技能和生成命令。新增 Python 仅为 docs 下 NON_RUNTIME 离线证据脚本，没有 import/register 到产品。

受保护 tracked files SHA-256 前后比较见 [completion-check.json](evidence/completion-check.json)。它验证没有原有源码或技能变更，不声称完成了全库回归或媒体效果评估。**本轮 STOP，不开始 Prompt A3。**
