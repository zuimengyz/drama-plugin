# Face A3 — QC Contract

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED

基线：2026-09-25，HEAD `3b286cca94ad3a1683060d4df2a986a6f789236f`。全部建议尚未实施；知识成熟度至多 LOCAL_EXPERIMENTAL，媒体效果 NOT_PLATFORM_VALIDATED。

## 观察结构与用途

复用 visual-continuity-qa 与 Production Review。下列是现有 QC-IDENTITY / QC-REFERENCE-LEAKAGE / QC-MATERIAL 的细分观察 keys，不建立新 validator owner、不新增 Review enum、不把名称注册成 runtime能力。F12–F16/F18/F20/F27 的设计知识提供观察依据；F30–F39 提供新增诊断维度。F40 只约束修复范围。

每条 observation metadata 必须含 criterion_id/version、capability_ids、actor/arc_stage、输出 media_id/hash、reference media/hash、region（坐标采用原图归一化坐标并注明裁切变换）、approved requirement exact pin+pointer、use/visibility、comparison、具体观察、PASS/FAIL/UNKNOWN、用途影响、root_cause_hypothesis、confidence、一个 repair_owner、保留范围。confidence 标 LOW/MEDIUM/HIGH 并给依据；对根因的置信度不能替代可见证据。

NOT_APPLICABLE 只属于旁路 metadata 的适用性，不塞进 Review.checks 的 PASS/FAIL/UNKNOWN。适用但看不清用 UNKNOWN。无需观察项从本次checks排除并记理由；不得用PASS伪装未观察。完整 metadata 保留为现有普通证据artifact，由 QA.evidence_refs 引用；Review 只投影已有可接受字段。

| Criterion | ADAPT | 具体可观察项 | 比较/适用边界 | Existing category | 默认调查 owner（须按根因裁决） |
|---|---|---|---|---|---|
| QC-FACE-GEOMETRY | F30 | 脸形/眼距/鼻唇相对关系 | 批准 face + 身份参考；控制透视/表情 | IDENTITY | specialized-asset-design |
| QC-AGE-DRIFT | F31 | 眼口体积、年龄线索与批准阶段偏离 | age_presentation 与该人物具体线索；疲劳/妆/光先分开 | IDENTITY | specialized-asset-design |
| QC-BEAUTIFICATION-DRIFT | F32 | 未批准放眼、缩鼻、瘦颌、磨掉年龄或标记 | 批准差异；漂亮本身不构成证据 | IDENTITY | specialized-asset-design |
| QC-SKIN-RESPONSE | F33 | 区域表面过度同质、蜡状边界/高光与妆光不相容 | baseline + 当前肤况 + light/grade；至少多项具体证据支持CG感归纳 | COSMETIC | lighting-design |
| QC-EYES-TEETH | F34 | 异常重复/融合、形态或反射不连贯 | 可见区域、角度和张口状态；不能要求牙齿总露出 | ANATOMY | shot-production |
| QC-EAR-INTEGRITY | F35 | 额外耳廓、边缘连接或身份失真 | 有耳部可见证据；遮发不判耳缺失 | ANATOMY | shot-production |
| QC-JAW-CHIN | F36 | 颌转折/颏投射相对批准身份偏移 | 当前角度与face；不是尖/方下巴达标 | IDENTITY | specialized-asset-design |
| QC-HAIRLINE-EDGE | F37 | 发际线位置漂移、毛发边界/纹理不可信 | 批准hair与当前整理/遮挡；规整发际线本身合法 | CONTINUITY | look-continuity |
| QC-STABLE-MARKS | F38 | 已批准标记侧别、位置、形态漂移 | physical_identity 与阶段Look；看不清标UNKNOWN | IDENTITY | specialized-asset-design |
| QC-REFERENCE-LEAKAGE | F39 | 参考pose/gaze/expression/light/camera覆盖当前原件 | 逐职责对照Reference Plan及当前owner；不是所有相似都泄漏 | CONTINUITY | reference-strategy |

## 从观察到唯一修复路由

表内默认是调查起点，不是“脸错就重设计角色”。先查批准原件：原件自相矛盾/缺失交其 author；原件正确但 mapping错误交既有 compiler/production实现维护；文本/绑定正确而输出偏差交 shot-production作 provider调查。每条发现记录一个下一步责任 owner，后续证据允许新版本路由，不能并列多个owner却无人负责。

具体归因：年龄设计阶段错误→specialized-asset-design（必要时请求casting补证）；当前疲劳误投年龄→look-continuity；表情错误→dramatic-performance-direction；pose/gaze错误→blocking；reference绑定/duty错误→reference-strategy；塑料高光若光原件不当→lighting-design，grade改变肤色→color-grading；正确原件/投影仍美化漂移→shot-production/provider investigation。QA仅提出有证据的假设，不直接改鼻、加皱纹、改肤色或操作provider。

复合症状分多个可证发现，不能把一个结论同时发给所有部门。unknown根因由shot-production协调检查来源和投影，不能升级成Face Realism Repair新owner。修复建议依F40注明最小局部范围、原批准锚点、必须保留的其它角色/表情/pose/camera/light。新结果不自动取代原锚点，不自动retry，不改变预算或重试次数。

## AAA/CG 感的证据纪律

“像游戏角色”仅可作多个具体观察的总结，不作为单独FAIL gate。例：同一可见面颊/额头在已批准柔光下都出现与参考不符的完全重复纹理，且眼周体积被明显磨平，可分别记录F33表面反应及F31年龄线索；必须注明区域、参考、用途、根因假设与置信度。该例是假设演示，不是本轮观察到的媒体。

反例：干净皮肤、对称脸、漂亮演员、年轻无纹、规则发际线在批准身份/妆光下都可PASS。粗皮肤、毛孔、瑕疵也不能自动PASS。远景没有毛孔不适用皮肤微纹理gate；侧面/笑容改变像素眼距不证明geometry drift；单项亮斑不能证明provider使用3D。F17既有不对称保留可作为背景核对，但不变成本轮ADAPT新能力。

## 既有 Review 处置保持

先保持当前校验：checks含FAIL当且仅当至少一条MAJOR finding，否则CHECKS_AND_FINDINGS_DISAGREE。逐维媒体诊断可在metadata标偏差；MINOR偏差在Review中作为MINOR finding而非FAIL check，check表示该用途必要要求仍满足。MAJOR finding → FAIL（即使同时有UNKNOWN）；否则含UNKNOWN → PENDING_REVIEW；否则MINOR → PASS_WITH_NOTES；无finding且checks通过 → PASS。severity依本次用途是否破坏必要身份/表演/可读性，绝不按美貌。沿用REGENERATE/POSTPROCESS/ACCEPT，MINOR+REGENERATE仍无效。建议REGENERATE不等于执行授权。不得引入总真实感分数或自动winner。
