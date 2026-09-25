# Face A3 — A5 Validation Contract

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED

基线：2026-09-25，HEAD `3b286cca94ad3a1683060d4df2a986a6f789236f`。全部建议尚未实施；知识成熟度至多 LOCAL_EXPERIMENTAL，媒体效果 NOT_PLATFORM_VALIDATED。

## 状态与入场条件

本轮0媒体生成，未选择虚构角色或伪造approved ids。未来只从真实已批准角色/arc_stage、剧情、casting、资产、Reference Plan和shot原件筛选fixture。先完成A4离线来源/消费测试、pin与预算授权，再冻结实验manifest。不存在所需年龄段/镜头就记NOT_AVAILABLE并限定结论，不为填表捏造演员或角色。

## Fixture registry（待从真实原件填入，不可直接执行）

| Slot | 所需真实批准对象 | 场景/证据目的 |
|---|---|---|
| YA | young adult approved character/arc_stage | close-up身份，不能默认加成人皱纹 |
| MA | middle-aged adult approved character/arc_stage | close-up年龄/体积/皮肤与身份 |
| OA | older adult approved character/arc_stage | close-up年龄保真，不靠普遍加皱纹 |
| TWO | 同场两名真实已批准角色 | 结构区别、身份不交换，不能只靠衣服/头饰 |
| CHANGE | 上述同一角色两个已批准shot | 不同light/expression下身份保持；不是把改变作为同pair变量 |

每slot填写实际work/script/scene/shot/character/arc_stage/casting intent/asset版本、source pins/approvals、选取理由、visible facet覆盖与限制。年龄分组来自获批角色意图，无自行生理年龄推断。一个人物可复用多个slot；不得用同一阶段冒充三年龄组。无法全部覆盖时不能声称跨年龄验证完成。

## OLD/NEW唯一处理变量

每pair固定 screenplay、character identity事实、casting intent、costume、scene、pose、expression、camera、lighting、reference bytes/order、provider、transport、model、serializer版本/政策、全部参数（含seed如支持）、输出尺寸/数量与评审用途。唯一变量是 Face Canonical Knowledge Decision 的显式版本/采用情况。两边运行同一A4后的mapper/serializer实现；不能用旧代码vs新代码混入编译差异。

NEW可把同一批准身份的描述分工/来源覆盖变明确，不能偷偷新增不同鼻子/年龄/肤色；若新增创作事实，则不再是本实验对照，必须另立角色设计研究。knowledge版本影响selected canonical decision与由此导出的hash/prompt是合法结果变量；这些不要求相同，但必须给差异manifest证明没有其它源变化。OLD也不能豁免必要source/approval检查；旧输入无法过基础合法性时停止该pair，不通过删gate伪造OLD。

CHANGE包含两个shot，各自OLD/NEW一对；shot之间照明/表情可不同，但每对内完全相同。跨shot共同reference集合若实际不可能保持，应限定为额外观察，不把它当纯因果配对。联合A4不等于联合A5变量：摄影知识/D1在Face每pair双边固定；摄影实验也固定Face。不得一次改变两套知识再声称Face获胜。

## 样本与评审

未来在任何输出可见前预登记每fixture的pair数/重复次数、可见性、预算、模型随机性、停止规则。seed不支持则明确NONDETERMINISTIC；同参数不能保证相同底噪。保留全部输出/失败/调用receipt，不挑最好的一张。预算不足只做探索性观察，不能写统计普遍结论。输出随机匿名A/B顺序；评审先看批准需求及参考，再逐维独立记录，揭盲后才对比。意见分歧保留，不取一个“真人总分”。

| Dimension | 依据与观测 | 报告方式 |
|---|---|---|
| identity stability | F30/36/38，批准face/marks | 每区域match/deviation/UNKNOWN +证据 |
| facial distinctiveness | F27，角色结构对比 | 排除服装/发型单独区别，逐关系说明 |
| age fidelity | F20/31，approved stage | 具体体积/眼口/毛发线索；无自动年龄评分 |
| live-action human plausibility | F33–35/37 +既有LIVE_ACTION | 分皮肤、眼牙、耳、毛发观察 |
| AAA/CG character feel | 上述具体结果的描述性归纳 | 无独立gate/总分；必须多项可见证据 |
| skin plausibility/identity | F15/16/29/33 | 区域/尺度/妆光条件；干净不扣分 |
| hair/hairline plausibility | F13/14/37 | 版本、位置、边缘、遮挡；不强加碎发 |
| feature geometry consistency | F01–12/F30/36 | 关系与投射，控制视角/表情 |
| beautification drift | F32 | 未批准的放眼瘦脸改鼻减龄磨平 |
| reference leakage | F39/C15 | 哪个参考职责越过哪份当前原件 |
| expression preservation | inherited current Performance/KEEP_LOCAL边界 | smile/皱眉不能为所谓真实被抹掉 |

每条AAA/CG观察必须附specific visible evidence、region、approved requirement、comparison、root-cause hypothesis、confidence，并指向QC合同的单一repair owner。漂亮、对称、光滑或无皱纹本身都不是失败；毛孔/瑕疵不是通行证。材料异常和几何漂移分开；根因不能从一张图推定模型训练/3D机制。

## 结果与停止

每维列OLD与NEW observed findings、回归/改善/无明确差异/不可观察，以及样本限制、review disposition、所有失败。禁止“9.2/10”或NEW总分胜出。来源/绑定/参数变化则该pair标INVALID，不纳入结论；失败后自动修图会改变试验条件，应停止并保留，修复另建获批实验。输出不能直接替换原identity master。

A5完成也只能按实测provider/model/用途/年龄和可见条件决定特定rule的PLATFORM_VALIDATED候选；没有单条证据的rule继续LOCAL_EXPERIMENTAL。PRODUCTION仍需原发布批准；不得35条一起升级。
