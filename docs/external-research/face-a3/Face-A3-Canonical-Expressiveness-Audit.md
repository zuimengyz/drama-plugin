# Face A3 — Canonical Expressiveness Audit

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED

基线：2026-09-25，HEAD `3b286cca94ad3a1683060d4df2a986a6f789236f`。全部建议尚未实施；知识成熟度至多 LOCAL_EXPERIMENTAL，媒体效果 NOT_PLATFORM_VALIDATED。

## 读取依据与结论

必读原件：[A0](../face-a0-a2r/Face-A0-External-Source-Freeze.md)、[A1](../face-a0-a2r/Face-A1-Capability-Forensics.md)、[A2](../face-a0-a2r/Face-A2-Local-Capability-Mapping.md)、[A2R](../face-a0-a2r/Face-A2R-Conflict-Authority-Reconciliation.md)、[capabilities](../face-a0-a2r/evidence/capabilities.json)、[source-index](../face-a0-a2r/evidence/source-index.json)。摄影承接 [C15/C17/C28 与 D2](../fal-cinematography-a3/A3-Professional-Knowledge-Contract.md) 和 [source mapping](../fal-cinematography-a3/A3-Source-IR-Consumer-Mapping.md)。冻结见 evidence/input-freeze.json。前轮 HEAD 到当前 HEAD 仅增加 58 个审计文档；不能拿旧 HEAD 当本轮生产状态。

**结论：现有容器可表达批准的人物差异；缺少统一语义分工、按用途覆盖、来源消费与细项观察。Face 专用 schema 新增为零。** 这不是宣称当前契约已足够：新 opt-in authoring profile、显式来源/职责 metadata 与 mapper 校验才使粗文本可核查。它们是未来 A4 工作。

当前 CharacterAsset 的 face 等 11 类 AssetDecision 都是 text/reason/source_refs；至少一条决定不保证 face/age 存在。旧 FaceDesign 有 shape/bone_structure/brow/cheekbone/jaw/eye_character/skin_character，但 character-art 已转发，不恢复作者。Casting 有 VisualDiscriminant/FaceArchetype.geometry，可选区间不能变成强制测量或正式身份第二份。

LIVE_ACTION 已含真实演员比例、皮肤、毛发及自然不对称语言；GlobalVisualStyle 已有 IDENTITY_WITHOUT_BEAUTIFICATION 与 PRESERVE_AUTHORED_IDENTITY。其文本 gate 不能证明像素。准确缺口是 **MEDIUM_PRESENT_BUT_FACE_REALISM_UNDERSPECIFIED**，不是 medium 只有一个空标签。

## FACE_A3_ALLOWLIST

以下 ID/名称直接连接真实 A2R ADAPT 行与 capabilities.json，不按任务示例推导。KEEP_LOCAL F17/F19/F21/F22/F26/F41 仅继承；其余 REFERENCE_ONLY/REJECT/OUT_OF_SCOPE 不创建规则。尤其 F17 不对称不是本轮新增 criterion，F20 不授权年龄估计器。

- F01 — 整体脸形与长宽关系
- F02 — 纵向比例与前后突出程度分离
- F03 — 眉骨起伏与眼窝深度分离
- F04 — 颧位、颧宽、前突与面颊软组织分离
- F05 — 面中纵长与鼻基底／面中凸凹区分
- F06 — 下颌相对颧宽及转折
- F07 — 下巴长度形状与前后投射／侧貌
- F08 — 眼形、间距、眼睑作为身份差异
- F09 — 自然眉形与眉眼间距
- F10 — 鼻梁、鼻尖与鼻翼／宽度
- F11 — 唇形、嘴宽与上下唇比例
- F12 — 耳廓身份保持
- F13 — 发际线身份与局部重建限制
- F14 — 头发密度、质地与可信毛发
- F15 — 肤色家族与漂白防护
- F16 — 皮肤区域纹理与可见尺度
- F18 — 痣、雀斑、疤等辨识标记
- F20 — 年龄与眼口区纹理、体积及毛发成熟度核对
- F23 — 身份参考可见性与质量适用性
- F24 — 可见、推测、不可确认的面部参考证据
- F25 — 多角度身份参考及脸部与全身证明分开
- F27 — 多人对比检查结构区别而非只换装饰
- F29 — 皮肤物理状态与光照响应分开
- F30 — geometry drift 按区域观察
- F31 — age drift 观察
- F32 — beautification drift 观察
- F33 — 皮肤塑料／蜡／绘制感观察
- F34 — 眼部与牙齿完整性观察
- F35 — 耳部完整性观察
- F36 — 下颌／下巴漂移观察
- F37 — 发际线漂移及头发边界观察
- F38 — 稳定标记漂移观察
- F39 — reference leakage 观察
- F40 — 局部修复、回原锚点、保留其它已批准事实
- F54 — 结构、妆容与气质解耦，未知不补全

## FACE_CANONICAL_EXPRESSIVENESS_MATRIX

Expressible YES/PARTIAL 指容器允许而语义/覆盖未约束；Consumption NO 指端到端未完成，不否认已有 face 文本输出。每行来源/QC详项见同名 JSON rows，与知识 draft 的逐条外部 commit/section 一一对应。所有非 QC 行共同附加 SOURCE_MAPPING_EXTENSION / CONSUMER_GAP；这些是同一共享问题，不要求35套编译器。

| Capability | Current Owner | Existing Field | Expressible Now | Consumption Complete | Gap Type | Proposed Design |
|---|---|---|---|---|---|---|
| F01 整体脸形与长宽关系 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 记录批准人物差异；不统一瓜子脸或理想比。 |
| F02 纵向比例与前后突出程度分离 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 比例是人物事实的描述轴，不是三等分达标线。 |
| F03 眉骨起伏与眼窝深度分离 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 眉毛、眼睑、阴影不能替代骨骼；未知不补。 |
| F04 颧位、颧宽、前突与面颊软组织分离 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 保留独立关系，拒绝高颧必瘦脸。 |
| F05 面中纵长与鼻基底／面中凸凹区分 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 只吸收关系描述；不吸收饱满才美的规范。 |
| F06 下颌相对颧宽及转折 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 方窄圆钝均可；无英雄下颌默认。 |
| F07 下巴长度形状与前后投射／侧貌 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 不能用尖等于前伸；不使用理想角度。 |
| F08 眼形、间距、眼睑作为身份差异 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 开合受当前表演影响；跨角度比较不得直接比像素宽。 |
| F09 自然眉形与眉眼间距 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 自然毛发生长与眉妆、眉间紧张分开。 |
| F10 鼻梁、鼻尖与鼻翼／宽度 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 拒绝统一高细鼻梁。 |
| F11 唇形、嘴宽与上下唇比例 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 不把笑容、描唇与当前张口写成稳定形态。 |
| F12 耳廓身份保持 | specialized-asset-design | CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 外部只支持保存/检查，不提供完整耳部设计或测量法。 |
| F13 发际线身份与局部重建限制 | specialized-asset-design | CharacterAsset.decisions.hair | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 遮帽区域重建是提案，不能声称还原了未知真实发际线。 |
| F14 头发密度、质地与可信毛发 | specialized-asset-design | CharacterAsset.decisions.hair | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 保留批准密度长度；不普遍加碎发、灰发或头屑。 |
| F15 肤色家族与漂白防护 | specialized-asset-design | CharacterAsset.decisions.surface_state | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 受光颜色不是基础肤色；不按族裔或角色身份自动填色。 |
| F16 皮肤区域纹理与可见尺度 | specialized-asset-design | CharacterAsset.decisions.surface_state | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 按年龄、肤况、妆、景别、光线判断可见度；不要求每张都见毛孔。 |
| F18 痣、雀斑、疤等辨识标记 | specialized-asset-design | CharacterAsset.decisions.physical_identity | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 来源和批准决定其是否长期/阶段性；不能为真实感随意添加。 |
| F20 年龄与眼口区纹理、体积及毛发成熟度核对 | specialized-asset-design | CharacterAsset.decisions.age_presentation / face / surface_state / hair | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 外部仅部分线索；没有跨年龄可靠映射、通用皱纹数量或年龄估计器。 |
| F23 身份参考可见性与质量适用性 | reference-strategy | Reference Plan.values.reference_images / requirements | YES / PARTIAL | NO | SOURCE_MAPPING_EXTENSION | 不清楚/遮挡即不可确认；不把参考图暗部推成结构事实。 |
| F24 可见、推测、不可确认的面部参考证据 | reference-strategy | Reference Plan.values.requirements / reference_roles | YES / PARTIAL | NO | SOURCE_MAPPING_EXTENSION | 光影可能伪装深眼窝/颧点，观察不等于已批准事实。 |
| F25 多角度身份参考及脸部与全身证明分开 | reference-strategy | Reference Plan.values.reference_images / requirements; Casting proofs | YES / PARTIAL | NO | SOURCE_MAPPING_EXTENSION | 多视图是待检查的证据，不是任意角度永不漂移保证；不生成。 |
| F27 多人对比检查结构区别而非只换装饰 | performance-casting（候选比较）；specialized-asset-design（正式身份） | VisualDiscriminant / FaceArchetype.geometry → CharacterAsset.decisions.face | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 吸收结构比较目的；不保证纯文字选项不同等于成像不同。 |
| F29 皮肤物理状态与光照响应分开 | specialized-asset-design | surface_state; Look.skin_condition; Lighting/Grade records | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 保留职责拆分；固定高光位置不是身份，不吸收 universal 半哑光。 |
| F30 geometry drift 按区域观察 | visual-continuity-qa | Review.checks / findings; QA.evidence_refs / owner_routes | YES / PARTIAL | NO | QC_CRITERIA_EXTENSION | 脸形、眼距、鼻唇与 approved anchor 比；透视表情差异先控制。 |
| F31 age drift 观察 | visual-continuity-qa | Review.checks / findings; QA.evidence_refs / owner_routes | YES / PARTIAL | NO | QC_CRITERIA_EXTENSION | 未来候选 QC-AGE-DRIFT；本轮不注册；不能从噪声或肤亮断言变年轻。 |
| F32 beautification drift 观察 | visual-continuity-qa | Review.checks / findings; QA.evidence_refs / owner_routes | YES / PARTIAL | NO | QC_CRITERIA_EXTENSION | 检查未授权瘦颌、大眼、改鼻、磨平年龄与辨识细节。 |
| F33 皮肤塑料／蜡／绘制感观察 | visual-continuity-qa | Review.checks / findings; QA.evidence_refs / owner_routes | YES / PARTIAL | NO | QC_CRITERIA_EXTENSION | 结合批准真人媒介、妆态、光照与局部证据，不以有没有瑕疵一刀切。 |
| F34 眼部与牙齿完整性观察 | visual-continuity-qa | Review.checks / findings; QA.evidence_refs / owner_routes | YES / PARTIAL | NO | QC_CRITERIA_EXTENSION | 形态、反射、重复结构/牙齿漂移；不让更亮更清等于更真实。 |
| F35 耳部完整性观察 | visual-continuity-qa | Review.checks / findings; QA.evidence_refs / owner_routes | YES / PARTIAL | NO | QC_CRITERIA_EXTENSION | 遮挡合理性、额外耳廓、边界失真；不可见用 UNKNOWN。 |
| F36 下颌／下巴漂移观察 | visual-continuity-qa | Review.checks / findings; QA.evidence_refs / owner_routes | YES / PARTIAL | NO | QC_CRITERIA_EXTENSION | 与人物身份和当前视角比；非方颌/尖颌达标。 |
| F37 发际线漂移及头发边界观察 | visual-continuity-qa | Review.checks / findings; QA.evidence_refs / owner_routes | YES / PARTIAL | NO | QC_CRITERIA_EXTENSION | 角色版本与当前整理/遮挡分开，不将新造发际线当已知。 |
| F38 稳定标记漂移观察 | visual-continuity-qa | Review.checks / findings; QA.evidence_refs / owner_routes | YES / PARTIAL | NO | QC_CRITERIA_EXTENSION | 位置侧别在可见条件下比较；看不清不判消失。 |
| F39 reference leakage 观察 | visual-continuity-qa | Review.checks / findings; QA.evidence_refs / owner_routes | YES / PARTIAL | NO | QC_CRITERIA_EXTENSION | C15 细化到脸形身份与 pose/gaze/expression/light/camera 来源；D 非验证方法。 |
| F40 局部修复、回原锚点、保留其它已批准事实 | shot-production / Production Review | Review.checks / findings; QA.evidence_refs / owner_routes | YES / PARTIAL | NO | QC_CRITERIA_EXTENSION | 吸收修复范围原则；禁止外部检查失败即自动调用。 |
| F54 结构、妆容与气质解耦，未知不补全 | specialized-asset-design | face / surface_state; Look / Performance records | YES / PARTIAL | NO | SEMANTIC_CLARIFICATION | 仅保存 source/approved design 事实；不将化妆视觉效果反写骨相。 |

## 真实源码定位

- `plugin/src/drama_plugin/contracts/specialized_asset.py`：CharacterField、AssetDecision、CharacterAsset、GlobalVisualStyle。
- `plugin/src/drama_plugin/specialized_asset.py`：validate_assets、字段 sourceMap；source_refs 限于所属 Director/Dramaturgy/World，必须包含 Dramaturgy。
- `plugin/src/drama_plugin/contracts/production_design.py`：旧 FaceDesign；`contracts/casting_discriminants.py`、`contracts/performance_casting.py`：现有候选差异。
- `plugin/src/drama_plugin/professional.py`：Reference Plan keys 为 shot_ref/input_mode/reference_images/reference_roles/start_frame_ref/end_frame_ref/reference_video_ref/requirements/unresolved_capability；Look 使用 skin_condition/fatigue/dirt/blood/wounds/injury_progression/facial_wear 等。
- `plugin/src/drama_plugin/visual/frame_request.py`：三图上限、实体/媒体/上传名唯一、reference_members、hash锁、formal IR 覆盖。
- `plugin/src/drama_plugin/contracts/visual_prompt.py`、`visual/image_serializer.py`：Fact 与 static/edit 实际消费不同。
- `plugin/src/drama_plugin/visual/production.py`：Review 状态/严重性；`visual_medium.py`：真实媒介语言与有界文字检查。

以上均为当前能力证据，不把提案 professional_sources 或 still_knowledge.py 说成已存在。Gap enum 仅使用用户七项；没有 FIELD_EXTENSION 行不意味着 shared CINE_D2 已实现。
