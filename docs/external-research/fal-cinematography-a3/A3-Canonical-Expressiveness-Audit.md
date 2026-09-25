# A3 — Canonical Expressiveness Audit

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED。本文件是 A3 提案，不改变当前 Skill、Python、route 或生产权。仅 16 个 A2R ADAPT capability；所有 Video assimilation 排除。

## 输入与当前版本

本轮先重读当前 HEAD `8f805217f9b7b692a10f3ec0a5363a938f91b192` 与工作树，再读 A0、A1、A2、A2R。实际路径是相邻 [fal-cinematography-a0-a2r](../fal-cinematography-a0-a2r/README.md)，不是假设报告直接位于 external-research 根目录。HEAD 未变；之前未跟踪的 A0–A2R 报告保留。所有输入与 tracked 文件 hashes 见 [input-freeze](evidence/input-freeze.json)。不访问新外部 Skill，不重新排名 provider，不扩充审计范围。

## CANONICAL_EXPRESSIVENESS_MATRIX

Expressible Now 只问“语义能否在当前正确 owner 的字段内表达”，不把 `dict[str, Any]` 可装任意 JSON 当成已有语义验证/自动投影。PARTIAL 精确列出未闭合部分。每项只列主要 Gap Type，C04/C28 等交叉 criteria 见合同 B。

| Capability | Current Owner | Existing Field/Contract | Expressible Now | Gap Type | Proposed Design |
|---|---|---|---|---|---|
| C02 景别与可读内容 | cinematography | `Camera Bible.values.shot_scale_philosophy / spatial_readability` | YES | KNOWLEDGE_ONLY | 先定义需要读到的身体、环境和关系，再选景别；补知识而非景别枚举。 |
| C03 相机角度、高度、视点 | cinematography | `values.camera_point_of_view / camera_height / perspective` | YES | SEMANTIC_CLARIFICATION | 视点关系、高度和光轴俯仰分别决定；不以角度自动推断人物强弱。 |
| C04 相机距离与透视一致性 | cinematography（设计）; spatial-continuity-qa（观察） | `values.camera_distance / perspective / lens_intention; Review.checks / findings` | YES | QC_CRITERIA_EXTENSION | 增加跨字段一致性 criteria，不做虚假的 mm 物理模拟。 |
| C05 构图选项和主体层级 | cinematography | `values.subject_hierarchy / spatial_readability / perspective` | YES | SEMANTIC_CLARIFICATION | subject_hierarchy 承载构图选择；空间可读性承载前后层关系，不新增 composition 顶层键。 |
| C06 焦段语言 | cinematography | `values.lens_intention / camera_distance / perspective` | YES | KNOWLEDGE_ONLY | 以空间伸缩/分离意图和相机距离定义镜头感；mm 可选且必须有理由。 |
| C07 景深与静态焦平面 | cinematography | `values.lens_intention / spatial_readability` | YES | SEMANTIC_CLARIFICATION | lens_intention 区分可读焦平面与允许柔化层；不含 rack focus。 |
| C09 动机光与光型 | lighting-design | `values.source / motivation / direction / intensity_relationship / contrast / falloff / visibility_priorities / practical_lights` | YES | SEMANTIC_CLARIFICATION | source 说明可见/隐含来源，direction 区分方位与软硬；材质反应归光照意图而非新增材质。 |
| C10 色彩与 mood grade | color-design; color-grading | `values.scene_palettes / sequence_palettes / character_environment_color_relation; grade_intention / exposure_continuity / skin_preservation` | YES | SEMANTIC_CLARIFICATION | 色彩意图与事后匹配分开；复用 preserve/secondary_details 传递批准静态目标。 |
| C11 胶片/光学质感选项 | global-visual-style（work边界）; cinematography/color-grading（各自实现） | `GlobalVisualStyle 封闭枚举; Camera.lens_intention; Grade.grade_intention` | PARTIAL | FIELD_EXTENSION | D1：GlobalVisualStyle 可空 imaging_character，限定批准的摄影类型、capture character 与可选 texture 边界；不增加 IR 字段。 |
| C13 具象描述代替空泛赞词 | 各原专业 owner；cinematography协调镜头描述缺口 | `CreativeRecord.values 的原部门字段; AssetDecision.text/reason` | YES | KNOWLEDGE_ONLY | generic 反馈退回原 owner 补具体可见决定；不在 compiler 添加事实或简单删词。 |
| C15 角色 anchor 与变量分离 | specialized-asset-design; reference-strategy; blocking/action/DPD（当前状态） | `AssetDecision; Reference Plan.reference_roles; FrameSpec.references / reference_members / actors; IR.subjects / blocking / action` | PARTIAL | SOURCE_MAPPING_EXTENSION | D2：FrameSpec.professional_sources 可空 pins；来源映射验证参考责任进入 IR.preserve，不能依靠被 IR 覆盖的 legacy 文本。 |
| C17 角色漂移质量检查 | visual-continuity-qa / production review | `Review.checks / findings; QA.values.findings / evidence_refs / owner_routes` | YES | QC_CRITERIA_EXTENSION | 增加 identity/costume 可观测 criteria；不增加 disposition 或自动 retry。 |
| C28 写实：材质接触与透视 | specialized-asset-design/prop-design; blocking/action; cinematography; lighting-design; QA（各自子职责） | `AssetDecision; Prop.material; Blocking.physical_relations; Action.contact_constraints; Camera.perspective; Lighting.*; Review.*` | YES | SEMANTIC_CLARIFICATION | 分为 material/contact/action/light/perspective/observation 六子责任；补对应 QC criteria。 |
| C30 摄影 genre 与 capture era 分离 | global-visual-style; source/world 原 owner不变 | `GlobalVisualStyle 封闭字段; IR.world.era 是故事年代` | PARTIAL | FIELD_EXTENSION | 复用同一 D1；拍摄类型/capture character 与 world.era 隔离，不推默认摄影年代。 |
| C35 一次改一个变量 | shot-production 的实验设计（不取得常规生产控制权） | `既有不可变请求/attempt/review/输出hash；无生产单变量字段` | YES | SEMANTIC_CLARIFICATION | A5 非 Runtime 实验 manifest 固定 inputs，只变一个可解释决策族；不加生产次数限制。 |
| C36 光线/色彩/镜头联合 QC | visual-continuity-qa / spatial-continuity-qa / production review | `QA.values.checks / findings / evidence_refs / owner_routes; Review.*` | YES | QC_CRITERIA_EXTENSION | 同一媒体的联合审查按维度记录；一份 finding 对应唯一修复 owner。 |

## 源码核验结论

- `professional.py::_SPECS` 实际 Camera 字段只有 camera_point_of_view、shot_scale_philosophy、perspective、lens_intention、camera_height、camera_distance、camera_movement、spatial_readability、subject_hierarchy 和 scene_ref。**没有现成的 camera_angle、composition_intent、depth_of_field 顶层字段**。本设计不照抄用户示例字段；用现有字段下的明确语义结构承载。
- `contracts/professional.py::CreativeRecord.values` 为 dict[str,Any]，但 `professional.validate_bible` 严格限制顶层 key、nested provider controls、owner 和 scope。可增语义文档/可选 profile 校验，不能通过自由嵌套偷渡其他 owner。
- `contracts/visual_prompt.py::Camera` 仅 framing、shot_size、readable_details、perspective、depth_cues；Lighting 仅 time_of_day、light_sources、contrast、realism。已有 Fact 含 priority/scope/source，足够承载 still 视觉决定；本轮不提出新 Camera/Lighting/Color IR 类型。
- `contracts/specialized_asset.py::GlobalVisualStyle` 为封闭 enum 组合，没有 capture character 或 optical texture 可变字段。塞进 material_philosophy/readability 或 Director.face/camera 将越权；D1 是必要最小扩展。
- `frame_request.compile_frame` 先在 legacy 文本写“reference 不继承 pose”，但 prompt_ir 分支用 compile_ir 的文本替换整个 prompt。正式 IR 路径仍校验参考 hash/slots/actor IDs，却没有强制把 reference_roles 及 must-not-carry 义务带入 IR。D2 与 source mapping 验证解决这个准确缺口，不能宣称已完整实现。
- `professional.compile_prompt_projection` 返回 `executable=false` 的部门原件投影，并非自动从全部专业字段生成 VisualPromptIR；未来映射必须做显式 source consumption，不能把现行系统描述成已闭环。
- `Fact.source` 当前仅校验非空字符串，不自动打开所有原件核对作者/值。CreativeRecord.source_refs 也主要做 freshness；Host 不会自动读取所有 knowledge metadata。未来 source resolver 必须显式传入/解析 retained refs；一段非空 source 字符串不能证明 provenance。
- `image_serializer.select_image_rows` 对 edit 过滤 camera/light 大部分字段；定向相机/光照 edit 必须由已有 edit_delta 表达，保持项用 preserve。不能仅将新 camera 字段塞入 IR 就声称 edit 生效。

这些是现有实现的表达/消费缺口，不产生新 same-scope owner 冲突：所有决定继续回到已确定的 owner，source resolver 不做创作。未触发 A3 STOP 条件。

## Schema delta 上限

只提出两个可选字段（未实现）：

- D1：`GlobalVisualStyle.imaging_character`，限定 Work 级成像边界；C11/C30 共享同一扩展。
- D2：`FrameSpec.professional_sources`，正式静态意图依赖的 SourcePin 集合；不装 prompt、不装 provider 参数，不给来源自动批准。它让原件版本进入既有 FrameSpec fingerprint，并可在未来 reservation/submission 读取重验。

Camera/Lighting 的 `CreativeRecord.values` 仅增加文档化的结构语义，不扩顶层字段；VisualPromptIR、Review、CinematicShotSpec、Provider request schema、MCP、Service、Storage 不增字段。Provenance/实验/观察细表作为现有 artifact store 可容纳的 metadata，不引入数据库实体或新的持久化机制。

## 本轮源码定位

- [plugin/src/drama_plugin/professional.py:48](../../../plugin/src/drama_plugin/professional.py) — `('cinematography'`
- [plugin/src/drama_plugin/contracts/professional.py:38](../../../plugin/src/drama_plugin/contracts/professional.py) — `class CreativeRecord`
- [plugin/src/drama_plugin/contracts/visual_prompt.py:78](../../../plugin/src/drama_plugin/contracts/visual_prompt.py) — `class Camera`
- [plugin/src/drama_plugin/contracts/specialized_asset.py:18](../../../plugin/src/drama_plugin/contracts/specialized_asset.py) — `class GlobalVisualStyle`
- [plugin/src/drama_plugin/visual/frame_request.py:178](../../../plugin/src/drama_plugin/visual/frame_request.py) — `def compile_frame`
- [plugin/src/drama_plugin/visual/image_serializer.py:9](../../../plugin/src/drama_plugin/visual/image_serializer.py) — `def select_image_rows`
- [plugin/src/drama_plugin/visual/prompt_ir.py:12](../../../plugin/src/drama_plugin/visual/prompt_ir.py) — `def compile_ir`
- [plugin/src/drama_plugin/visual/production.py:298](../../../plugin/src/drama_plugin/visual/production.py) — `class Review`
- [plugin/src/drama_plugin/hosts/professional.py:100](../../../plugin/src/drama_plugin/hosts/professional.py) — `def submit`
- [plugin/src/drama_plugin/hosts/route_production.py:113](../../../plugin/src/drama_plugin/hosts/route_production.py) — `async def operate`
- [plugin/src/drama_plugin/specialized_asset.py:85](../../../plugin/src/drama_plugin/specialized_asset.py) — `def validate_assets`

两个字段的机器可读设计见 [contract-delta-draft.json](contract-delta-draft.json)，它不被任何 Runtime loader 消费。
