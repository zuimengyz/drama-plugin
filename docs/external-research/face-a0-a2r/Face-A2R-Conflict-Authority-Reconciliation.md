# Face A2R — Conflict & Authority Reconciliation

审计日期：2026-09-25（Asia/Shanghai）。本轮仅 Face A0–A2R；所有候选均未安装、未实施、未作平台媒体验证。

## Authority Ladder

1. Platform Contract / explicit runtime configuration。
2. Work Canon / source / approved Character facts。
3. Validated Specialized External Knowledge。
4. Platform-validated Specialized Local Knowledge。
5. Experimental external/local rule。
6. Generic aesthetics / prompt heuristic。

本轮 A/B/C 处 EXTERNAL_CANDIDATE，D 为 REFERENCE_ONLY；均不能凭开源身份上升到 Level 3。审美偏好不能覆盖 Level 2。既有契约与批准事实因 authority 胜出，不等于本地所有艺术规则已获媒体验证。

## FACE_CONFLICT_MATRIX

Winner 决定当前权威；Future Action 是未来讨论时的取舍，本轮未修改任何 loser。scope 不同先拆开，不能伪装 same-scope external winner。

| Conflict | 能力 | 冲突外部规则 | 本地权威/约束 | Winner | Future Action |
|---|---|---|---|---|---|
| FC01 | F43, F48 | 理想比例/无瑕/雕塑化面部默认 | 批准身份与禁止自动美化 | Level 1/2 本地边界 | REJECT；不把外部审美值纳入身份或 QC；无本地 loser |
| FC02 | F44 | 职业/性格/类型推面部 | 来源与批准设计，casting 禁 physiognomy | Level 2 人物事实 | REJECT AESTHETIC_OR_STEREOTYPE_HEURISTIC；外部默认不得导入 |
| FC03 | F45, F16, F20, F29 | 半哑光/鼻红/眼纹/固定高光通用注入 | 年龄/皮肤/剧情状态及 Lighting 各自批准 | Level 1/2 平台与人物状态 | REJECT 自动注入；ADAPT 分区观察，未知保持未知 |
| FC04 | F41, F22, F26 | 肖像编辑锁 pose/gaze/expression | C15 当前镜头拥有表演 | Scope-specific local authority | 编辑基底有批准 preserve 时 KEEP_LOCAL；镜头迁移不得照搬保留清单 |
| FC05 | F42, F39 | scene reference 默认授权表情光照相机 | Reference 不转移 owner | C15 / 当前专业原件 | REJECT 自动继承；ADAPT leakage 观察 |
| FC06 | F46 | 冷脸不笑/偏移视线是真实感必需 | Performance / Blocking 当前原件 | Level 2 approved performance | REJECT 默认表演；不把固定表情纳入身份 |
| FC07 | F49 | 外部 prompt 模板写最终 provider prompt | 现有 compiler/serializer 独占各自正式路径 | Level 1 平台 | REFERENCE_ONLY；不复制 prompt bundle/附加第二写入者 |
| FC08 | F40 | QC fail 即修图/迭代调用 | Review 处置、预算与授权独立 | Level 1 平台 | ADAPT 局部修复建议；外部自动执行分支不采用 |
| FC09 | F28, F27 | 固定差异组数/两轮上限 | 本地角色需求与差异证明 | 本地角色任务与证据门 | REFERENCE_ONLY 数字阈值；ADAPT 比较思想，不替换 casting |
| FC10 | F47 | 手机/噪点/随拍等于真人 | Work medium 与已批准视觉风格 | Level 1/2 平台与作品 | REFERENCE_ONLY 风格；不重审 cinematography、不默改镜头 |
| FC11 | F23, F24, F13 | 从强阴影或遮帽区补确定结构 | 只接受可见证据/批准创作 | Level 2 已批准事实 | ADAPT 不确定性；推测不可自动成为事实 |
| FC12 | F52, F53 | 论文/自述产量/四图一致证明通用能力 | same task/medium/credible evidence 才能赢 | 证据门槛 | REJECT 模型机理推论；REFERENCE_ONLY 效果声称 |
| FC13 | F22, F18 | C anchor 含姿态服装及任意可变 medium | 身份/服装/当前状态/Work pin 独立 | Level 1/2 + C15 | KEEP_LOCAL；只保留合法稳定项，不能通过换场顺带改 medium |
| FC14 | F50, F51 | 安装外部 runtime / route / video | 本轮研究限定 | 用户范围 + Level 1 | OUT_OF_SCOPE；不导入执行/反馈失效规则 |
| FC15 | F54, F44 | A 结构解耦新文档与 auto_bss 旧默认并存 | 本地事实优先 | 批准人物事实 | ADAPT 解耦；REJECT 推型；不接受整包内部优先级作为平台规则 |
| FC16 | F01, F03, F06, F27 | 误把外部几何视为本地从未具有 | 旧 FaceDesign + 当前 casting 已有几何 | 本地事实与审计完整性 | 保留已有能力；仅调查 formal asset/IR/QC 的连接缺口，无 REPLACE_LOCAL |

## External Winner Rule 应用结果

只有同能力、同模态、同任务、同媒介且有可信外部证据，并且本地欠验证，才允许 EXTERNAL WINS。本轮没有满足全部条件的项目。B 的单照片精修展示不能打败原创人物设计/跨镜头身份契约；A/C 缺可复核实验，D 只有职责文字。不能为了吸收外部材料虚构替换赢家。

`LOCAL_RULES_EXPECTED_TO_BE_REPLACED = []`。

因此没有 REMOVE / DEPRECATE_AND_DISABLE / MOVE_TO_HISTORY 的本地目标。已有 character-art 只读兼容地位维持，不是本轮作出的废弃动作。未来 Face A3 如发现精确同范围胜负，需重新举证并明确唯一 loser；本轮的 ADAPT 不授予双重权威。

## Final Decision Table（唯一且穷尽）

| Decision | Count | Capability IDs |
|---|---|---|
| ADOPT | 0 | — |
| ADAPT | 35 | F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11, F12, F13, F14, F15, F16, F18, F20, F23, F24, F25, F27, F29, F30, F31, F32, F33, F34, F35, F36, F37, F38, F39, F40, F54 |
| REPLACE_LOCAL | 0 | — |
| KEEP_LOCAL | 6 | F17, F19, F21, F22, F26, F41 |
| REFERENCE_ONLY | 4 | F28, F47, F49, F53 |
| REJECT | 7 | F42, F43, F44, F45, F46, F48, F52 |
| OUT_OF_SCOPE | 2 | F50, F51 |

完整逐项决定与证据位于 [A2 matrix](Face-A2-Local-Capability-Mapping.md) 和 [capabilities.json](evidence/capabilities.json)。没有隐含 ADOPT。KEEP_LOCAL 表示保留既有职责/规则，非复制外部；ADAPT 只表示进入设计研究候选。

## FACE_CAPABILITIES_RECOMMENDED_FOR_A3

F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11, F12, F13, F14, F15, F16, F18, F20, F23, F24, F25, F27, F29, F30, F31, F32, F33, F34, F35, F36, F37, F38, F39, F40, F54

按最小职责分组：

- 批准面部结构与辨识差异的表达：F01–F12、F27、F54。复用既有 Specialized Asset 和 Casting，查明现有表达是否足够，不预设新 skill 或 schema。
- 表面、毛发、标记与年龄的身份/状态边界：F13–F16、F18、F20、F29。年龄方法证据不完整，禁止自动生成标准年龄脸。
- 身份参考的可见性、推测与多角度证据职责：F23–F25、F39。继承 C15，不创建新事实 authority。
- 逐维 observation 与局部修复范围：F30–F40 中被标为 ADAPT 的项目。继续现有 Review / visual-continuity-qa / Production Review，不设重试系统。

这些是未来要解决的问题和候选知识，**不是 Facial Identity Structure 的字段设计、JSON schema、实施计划或 Face A3 交付**。A 的无许可证状态、派生来源和弱效果证据随候选保留；未来若采用须独立表达、保持 attribution 与验证限制，不直接拷贝代码/模板。

## EXTERNAL_AESTHETIC_RULES_FORBIDDEN_FROM_RUNTIME

| IDs | 明确禁止的默认 |
|---|---|
| F43 | 把黄金比、三庭五眼和理想角度作为通用真人合格线 |
| F44 | 将军/总裁/反派/护士/阶层/族群/性格自动推出颌、眼、鼻、肤色 |
| F45 | 给所有角色注入成年半哑光、鼻红、眼纹及指定高光 |
| F46 | 真人必须不笑/冷脸/偏移视线 |
| F48 | 完美皮肤/雕塑化精致脸覆盖批准身份 |
| F28/F47（REFERENCE_ONLY） | 结构组数阈值或 iPhone/噪点/歪构图自动成为 Runtime gate |

F49 的 provider 词语是 REFERENCE_ONLY；F52 的“某词必触发假脸”及论文越界归因为 REJECT。既有 CG branch 的合法美术用途未被宣判错误，但不能迁移进固定 LIVE_ACTION Work。没有实际媒体回放，不能指认这些规则已经导致用户那次试拍的 CG 感。

## Required Final Findings

### Q1 — 是否缺少 explicit facial geometry identity contract？

**YES，限定为当前正式可写 CharacterAsset 的完整、稳定、可逐项核查的面部身份表达。** CharacterField.face 仍是单个 AssetDecision.text，相关必填覆盖没有被约束；IR.face 仍是单 Fact。必须同时说明：若问题是“整个 Plugin 有没有任何显式几何结构”，答案是 **NO，并非完全没有**——旧 FaceDesign 有 shape/bone_structure/brow/cheekbone/jaw 等，当前 casting 有 VisualDiscriminant 与可选 GeometricRegion。不能以缺口为由重复建 authority。证据：[L-asset](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/specialized_asset.py:44); [L-ir](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/visual_prompt.py:44); [L-facelegacy](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/production_design.py:73); [L-cast](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/casting_discriminants.py:80)

### Q2 — 当前 Character Asset 足以区分真人个体与 generic/idealized AI face？

**PARTIAL。** 可以写详细差异并追溯源；casting 有反美貌门槛与对比设计，medium 已要求真人结构/皮肤/毛发。但没有强制将各项身份差异从正式资产逐项传递、检查，也没有媒体验证证明这些语言稳定奏效。不能回答绝对 NO，也不能因 sourceMap 完整回答 YES。证据：[L-source](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/specialized_asset.py:145); [L-castpolicy](/Users/zy/historical-plugin/drama-plugin/plugin/skills/performance-casting/references/visual-discriminants.md:20); [L-medium](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/visual_medium.py:31); [L-test](/Users/zy/historical-plugin/drama-plugin/plugin/tests/test_specialized_asset.py:84)

### Q3 — 是否值得在 Face A3 研究 Facial Identity Structure？

**YES。** 最小职责只覆盖批准的颅面/五官关系、稳定皮肤与毛发身份、辨识标记，以及特定人生阶段的年龄呈现依据与不确定性。仍归 Specialized Asset，Casting 提供获批候选依据；不得拥有当前表演、伤污、妆、光线、相机或 provider prompt。本轮不决定字段、必填性、数值或实现。

### Q4 — C15 Reference Responsibility 是否需要扩展？

**YES，细化职责和证据，不改变原则。** 明确哪些可见脸形、比例、发际线、标记属于获批身份，哪些被遮挡/光照误导而不可确认；区分肖像身份参考、编辑目标和当前 shot。D2 仍未实施。证据：[L-a3ref](/Users/zy/historical-plugin/drama-plugin/docs/external-research/fal-cinematography-a3/A3-Professional-Knowledge-Contract.md:100); [L-a3d2](/Users/zy/historical-plugin/drama-plugin/docs/external-research/fal-cinematography-a3/A3-Professional-Knowledge-Contract.md:113); [A-visible](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L104); [D-duty](https://github.com/Shinning1010/realportrait-ai/blob/35728411922ddf83c612612bc4d2d1c6df8a94a0/skill/realportrait-ai/SKILL.md#L18)

### Q5 — QC-IDENTITY 是否过粗？

**YES，作为面部诊断清单过粗；现有 Review 容器不因此失效。** 候选维度为几何身份、年龄、美化、皮肤塑料感、眼/牙、耳、下颌下巴、发际线、稳定标记、reference leakage。每维必须有适用条件、批准比较依据、媒体可见证据、用途影响和现有 owner 路由；未知不臆判。复用 A3 C17、QC-IDENTITY；角色皮肤同时与 C28/QC-MATERIAL 的职责拆分对齐。证据：[L-a3qc](/Users/zy/historical-plugin/drama-plugin/docs/external-research/fal-cinematography-a3/A3-Professional-Knowledge-Contract.md:135); [L-review](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/visual/production.py:298); [L-status](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/visual/production.py:308)

### Q6 — 哪些外部规则会造成 beauty / stereotype / CG 风险？

F43/F48（美貌比例与完美精致）、F44（身份类型→面部）、F45（通用纹理/高光）、F46（冻结冷脸）均 **REJECT**。F28（差异数量阈值）、F47（手机/噪点真实性风格）、F49（provider 提示模板）为 **REFERENCE_ONLY**，不可默认 Runtime 执行。这里只判有依据的冲突和潜在偏移，不声称已实验证明因果。A 新版解耦和反模板知识可单独 ADAPT，不能因此放行整包旧默认。

## Stop Gate

`READY_FOR_FACE_A3 = YES`：候选、缺口与审计冲突已可追溯，足够开始下一轮设计讨论；不代表效果验证、许可证放行、schema 决定或生产授权。

Face A0 → A1 → A2 → A2R 已止于报告。没有执行 Face A3/A4；没有新增 facial identity fields、修改 reference/QC/prompt/provider、安装外部 skill 或生成人物图片。审计范围内冲突均已裁决，无并行 face authority。
