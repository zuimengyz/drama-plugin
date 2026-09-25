# A3 — A5 Validation Contract

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED。本文件是 A3 提案，不改变当前 Skill、Python、route 或生产权。仅 16 个 A2R ADAPT capability；所有 Video assimilation 排除。

## 目标与授权边界

未来 A5 检验旧专业知识决策（OLD）与本次独立适配的局部决定（NEW）在 STILL / LIVE_ACTION 的逐维差异。本轮不生成媒体；这个实验设计不是支付预算或 production approval，也不要求立即开展 30 张生成。

测量单位是“同一批准镜头目标、同一输入与执行条件的一对 OLD/NEW 结果”，结论只覆盖测过的 scope。不能用一张好图证明全局更真实，也不能把 IR 单测或提示词长度当质量胜者。

## 固定条件与唯一干预

每对开始前冻结并哈希：screenplay/Scene/Shot 的剧情及原始目的、角色/身体身份、costume/状态、scene/material/topology、当前 pose/gaze/expression/action/contact、参考 Media 原始 bytes/hash/order/duties、Work medium/style boundary、provider、transport、model/node/template/version、尺寸/quality/n/seed 等所有实际执行参数。

同一对 OLD/NEW 唯一允许改变的是预登记的 professional knowledge decision subset 及由此派生的专业 revision/IR/prompt；其 source fingerprint 必然不同，不能因此冒充固定请求字节。保持 compiler/serializer policy version 完全相同，否则混入 prompt policy 因素。不得比较 fal OLD 与 Comfy NEW，不得同时升级 model 或节点版本，不改变当前 GPT Image 2 route。

OLD 也通过同一 A4 serializer/mapping 版本消费旧决定；先证明可重放且不被“新知识默认值”悄悄修改。NEW 从 LOCAL_EXPERIMENTAL 规则产生且经同范围设计审阅。reference 不得替换或重新上传成不同 bytes；需上传时验证相等。执行时若 route/model capability 已变化，本 pair INVALIDATE，不迁移模型继续冒充同一实验。

C35 控制变量：一对只改一个预登记 decision family。对焦平面与可读性等必要耦合选择，列出全部变更，并将结果仅归因于该组合；不能宣传其中某一条规则独立有效。常规生产多问题修复不受此限制。

## 五类样本框架

所有样本都来自真实批准目标，不为实验改变 screenplay 或捏造 Asset。下表给出框架与一次干预示例，正式 A5 需预登记实际 ID/版本后才能运行。

| Fixture class | OLD/NEW 允许的单一变化 | 主要观察 | 禁止混入的变化 |
|---|---|---|---|
| 单人近景 | C06/C07 的 lens spatial/focus 决策族，保持同一可见身份要求 | face identity、焦平面可读性、比例、光学感 | 改年龄/肤色/修容；添加毛孔或瑕疵清单 |
| 双人文戏 | C02/C05/C07 的双方可读关系决策族 | 两人脸/手与关系、主体层级、reference leakage | 改位置/视线/表情/台词；删去第二人 |
| 夜间外景 | C09 的来源方向/反差意图细化 | source motivation、方向、材质响应、人物环境一致 | 增加新 practical、下雨、烟雾或换时段 |
| 室内低照度 | C09/C28 的已有光源与接触处可读性决策族 | 关键动作可读、contact shadow 是否条件性合理、低光保真 | 自动加 rim/fill、重做布景、将黑暗全部抬亮 |
| 人物与复杂环境关系 | C03/C04/C05 的距离/透视/层次意图族 | 人物环境尺度、遮挡、地标、构图和空间可读 | 改 Layout/门窗位置、删复杂物体来降低难度 |

C15 的 reference-duty 区分与 C17/C36 的观察适用于全部样本；C13 可作为“具体化选择”的辅助方法，但不能把未申报的其它 professional decision 一并改变。C11/C30 的 capture/texture 是可选子实验：仅在事先批准的同一 Work style 边界允许两种实现时比较；如果 style 已锁死，保持完全相同并只验证正确传递，不能为凑实验擅改 approved style。

## 配对、顺序与随机性

建议探索阶段预登记五类各一个镜头、每类三个独立配对 block，即 15 对/30 输出的**预算估算候选**；不是自动 batch 或已授权数量。实际数量须在执行前按预算/用途确定并锁定，数量不足则报告描述性结果，禁止隐藏样本不足。

每个 pair 使用相同 seed（仅当当前 adapter 确实支持），不同 block 可用不同预登记 seed；同 seed 不能保证生成确定性。若 transport 不支持控制 seed，记录 STOCHASTIC_UNCONTROLLED，配对靠固定条件与交错顺序降低混杂，不能谎称 seed 相同。当前 accepted execution parameters 必须逐字段比对。

OLD/NEW 调用顺序交错并预登记；观察展示使用盲化 X/Y 和随机左右位置。技术失败/timeout/UNKNOWN 按现有 recovery 保留，不生成替代来挑优；若确认无任务可重试，则按同一技术策略同时适用两臂，保留成本和失败率。不得只选 NEW 最好的一张与 OLD 首张比较。failed/unknown 输出必须入 denominator 或明确列为未可观察，不能静默删样本。

## OBSERVATION_DIMENSIONS（逐维，不给主观总分 winner）

| Dimension | 证据需求 | 可报告的 pair 结论 |
|---|---|---|
| live-action plausibility | 正常展示尺寸下的人/物/环境整体观察，引用具体区域与 approved requirement | NEW better / comparable / worse / UNKNOWN，并写原因 |
| game/CG feel | 具体表面/轮廓/光照异常证据；标签本身不够 | 同上；不能仅因干净皮肤或对称构图判 CG |
| camera coherence | 视角、比例、景别、距离、焦平面关系 | 同上，对应 QC-CAMERA |
| composition | 注意力层级与批准意图、关键对象可读性 | 同上；不是个人构图喜好投票 |
| subject-environment relation | 地标/尺度/遮挡/接触/位置关系 | 同上 |
| lighting motivation | 来源、方向、阴影/高光与场景来源证据 | 同上 |
| material realism | 已批准材料结构与其受光响应 | 同上；不能要求每种材料有灰尘 |
| identity stability | exact approved identity 与可见结果比较 | 同上；看不清为 UNKNOWN |
| reference leakage | 原参考与当前要求不同的姿态/视线/表情/光线/构图是否被误带入 | 同上；有意批准的编辑保留不算泄漏 |
| prompt length | 记录字符数；token 仅在指定 tokenizer 可用时记录其版本，否则 UNKNOWN | 原始数值/变化；越短不自动越好 |
| prompt duplication | exact normalized clause 重复和 source atom 重复分别记录；语义重复须人工标注 span/source | 次数/具体 spans；必要身份复述不能粗暴算错 |
| generic cinematic filler | 标出无可执行视觉信息的片段及理由，同时检查是否丢了具体事实 | 数量/片段/用途；关键词 blacklist 不作裁决 |

每维明细含：pair/block/case、盲化 arm、output hash、normal-view setting、region/必要 crop、observation、evidence、requirement ref、use-based impact、severity（如适用）、confidence/UNKNOWN 原因、reviewer、disagreement、repair owner。原始观察和相对比较分栏；未来 summary 不得覆盖原 Review。

## 不用加权总分的决策规则

逐维汇报所有 pairs 的 better/comparable/worse/UNKNOWN 计数和原始证据链接，并保留技术失败。五个场景类别单独列，不把一个优秀近景抵消夜外景身份失败。

单项 rule 的晋级候选至少满足：预登记目标维度有可重复具体改善；不能牺牲批准身份、剧情/动作、媒介、关键可读性与 required reference；没有未裁决 MAJOR 回归；对无足够证据的维度如实 UNKNOWN。只有描述性样本时不宣称统计显著或通用优势；允许结论 MIXED / INCONCLUSIVE，并限制采用 scope。

“新知识有效”的审查不等于 user adoption：技术 contract pass、媒体用途 review、rule 平台验证、作品用户采纳、支付授权各自独立。new rule 的 PLATFORM_VALIDATED scope 必须注明实际 provider/transport/model/version/task/medium，不能自动升级 video/CG。正式启用 PRODUCTION 仍需既有发布/授权门。

## 实验记录草案（非 runtime）

```text
experiment_id / preregistration_version / approved_budget_ref (initially absent)
source_freeze: screenplay, character, costume, scene, state, references, medium/style hashes
execution_freeze: provider, transport, model, template, serializer, exact parameters
intervention: capability_ids from A3 allowlist; old/new decision refs; changed fields; rationale
pairs: class, block, order, same-seed evidence or stochastic limitation
attempts: request fingerprint, provider task correlation, costs, output hash, technical outcome
observations: per-dimension evidence and existing Review refs
analysis: per-dimension counts, unknowns, regressions, scope-qualified disposition
user_adoption: separate existing reference or NOT_REQUESTED
```

原有预算和 reservation gate 仍逐次生效；设计 manifest 没有执行能力、不能重置 attempts。**A5 尚未执行，0 图片、0 付费调用。**
