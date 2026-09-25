# A3 — Source / IR / Consumer Mapping

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED。本文件是 A3 提案，不改变当前 Skill、Python、route 或生产权。仅 16 个 A2R ADAPT capability；所有 Video assimilation 排除。

## 单一消费链

```text
approved canon / Director intent / movie medium
  → existing professional originals (one decision, one owner)
  → scoped source selection + deterministic mapping receipt
  → existing VisualPromptIR facts
  → compile_ir → current shared image_serializer (one writer)
  → frame adapter exact prompt transfer + execution parameters
  → existing qualified Host / review / Media lifecycle
```

其中 source selection/receipt 是未来 A4 的确定性投影职责，不是专业创作或新 prompt writer。当前 compile_prompt_projection 只有非执行原件投影；下表是明确的目标消费设计，不冒充已落地。

## SOURCE_IR_CONSUMER_MATRIX

下表 Canonical 字段位于正确 owner 原件；绝不直接把 external_source 的文本当 Fact.text。静态只用 CURRENT；reasons、knowledge provenance、QC、实验 metadata 不发送 provider。

| Capability / source decision | Owner → canonical field | VisualPromptIR destination | Serializer consumer | Adapter boundary |
|---|---|---|---|---|
| C02 景别与可读内容 | cinematography → `Camera Bible.values.shot_scale_philosophy / spatial_readability` | `camera.shot_size; camera.readable_details` | CAMERA | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C03 相机角度、高度、视点 | cinematography → `values.camera_point_of_view / camera_height / perspective` | `camera.perspective（来源组合映射）` | CAMERA | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C04 相机距离与透视一致性 | cinematography（设计）; spatial-continuity-qa（观察） → `values.camera_distance / perspective / lens_intention; Review.checks / findings` | `camera.perspective; camera.depth_cues; QC不进IR` | CAMERA / Review | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C05 构图选项和主体层级 | cinematography → `values.subject_hierarchy / spatial_readability / perspective` | `camera.framing; camera.readable_details; camera.depth_cues` | CAMERA | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C06 焦段语言 | cinematography → `values.lens_intention / camera_distance / perspective` | `camera.depth_cues; camera.perspective` | CAMERA | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C07 景深与静态焦平面 | cinematography → `values.lens_intention / spatial_readability` | `camera.depth_cues; camera.readable_details` | CAMERA | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C09 动机光与光型 | lighting-design → `values.source / motivation / direction / intensity_relationship / contrast / falloff / visibility_priorities / practical_lights` | `lighting.light_sources / contrast / realism / time_of_day` | LIGHTING | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C10 色彩与 mood grade | color-design; color-grading → `values.scene_palettes / sequence_palettes / character_environment_color_relation; grade_intention / exposure_continuity / skin_preservation` | `preserve[]（必要目标）; secondary_details[]（明确可省略目标）` | TARGET LOOK / Review | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C11 胶片/光学质感选项 | global-visual-style（work边界）; cinematography/color-grading（各自实现） → `GlobalVisualStyle 封闭枚举; Camera.lens_intention; Grade.grade_intention` | `preserve[] 或 secondary_details[]；具体光学意图仍 camera.depth_cues` | TARGET LOOK / CAMERA | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C13 具象描述代替空泛赞词 | 各原专业 owner；cinematography协调镜头描述缺口 → `CreativeRecord.values 的原部门字段; AssetDecision.text/reason` | `随原决定映射；reason/criteria不发provider` | 各所属section | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C15 角色 anchor 与变量分离 | specialized-asset-design; reference-strategy; blocking/action/DPD（当前状态） → `AssetDecision; Reference Plan.reference_roles; FrameSpec.references / reference_members / actors; IR.subjects / blocking / action` | `subjects[]; blocking; action; preserve[]（reference duty）` | SUBJECTS / CURRENT BLOCKING / TARGET LOOK; edit PRESERVE | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C17 角色漂移质量检查 | visual-continuity-qa / production review → `Review.checks / findings; QA.values.findings / evidence_refs / owner_routes` | `NO_PROVIDER_PROJECTION` | Review only | 无 provider consumer |
| C28 写实：材质接触与透视 | specialized-asset-design/prop-design; blocking/action; cinematography; lighting-design; QA（各自子职责） → `AssetDecision; Prop.material; Blocking.physical_relations; Action.contact_constraints; Camera.perspective; Lighting.*; Review.*` | `environment/subjects; blocking.contact; camera.perspective; lighting.realism；观察不入IR` | 分配现有section / Review | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C30 摄影 genre 与 capture era 分离 | global-visual-style; source/world 原 owner不变 → `GlobalVisualStyle 封闭字段; IR.world.era 是故事年代` | `world.era 不变；imaging intent→preserve[]/secondary_details[]` | TARGET WORLD vs TARGET LOOK | 仅接收单一已编译 prompt；size/seed/quality/images 等仍由当前 adapter 独占 |
| C35 一次改一个变量 | shot-production 的实验设计（不取得常规生产控制权） → `既有不可变请求/attempt/review/输出hash；无生产单变量字段` | `NO_PROVIDER_PROJECTION` | Experiment evidence only | 无 provider consumer |
| C36 光线/色彩/镜头联合 QC | visual-continuity-qa / spatial-continuity-qa / production review → `QA.values.checks / findings / evidence_refs / owner_routes; Review.*` | `NO_PROVIDER_PROJECTION` | Review only | 无 provider consumer |

## Field-level 映射规则

- Camera `shot_scale_philosophy.intent` → `camera.shot_size`；`spatial_readability.intent` → `camera.readable_details`。
- `subject_hierarchy` 中 owner 选择的构图陈述 → `camera.framing`。前景与纵深选择可拆到 depth_cues，但同一原件 atom 不得同时输出两次。
- `camera_point_of_view / camera_height / camera_distance / perspective` 的选中可见意图 → `camera.perspective`。若需要组合，mapping row 明确列全部源 leaf 和固定连接操作；不能压缩出新的语义。每个 Fact.source 指向这条可重放 mapping row，不是随意造一个 source 字符串。
- `lens_intention` 的 lens spatial effect、焦平面、允许柔化对象各自 → `camera.depth_cues[]`。`camera.readable_details` 不重复输出这些意图，只保留不同的可读对象义务。exact_mm 若未作者给出就不能生成；有则作为描述，不传入 provider 数值控制。
- Lighting source/motivation/direction/practicals → `lighting.light_sources`；相对强度/反差 → contrast；falloff/material interaction/contact-light target → realism；当前时段来自批准的场景/Lighting continuity → time_of_day。组合时记录每个 source leaf；照明不得写 SceneAsset 材料事实。
- Source world era 只到 `world.era`。D1 capture_character / texture 以及 Color palette 的已选择必要画面义务 → `preserve[]`（CRITICAL）；作者明确可省略的装饰性成像细节 → `secondary_details[]`（SECONDARY）。preserve 指保留批准视觉边界，不意味着初始 T2I 有一张待编辑原图。不得把所有 color/texture 无差别降为 secondary 让预算删掉。
- Source Asset face/body/costume → 对应 `subjects`；当前 pose/position/contact → Blocking 与 Action；当前 expression 只读批准表演方向。Reference Plan 选中 reference duty → `preserve[]`，明确 source image 只负责哪些实体属性。Reference order/slot 的数字来自实际 FrameSpec 顺序，专业 Skill 不编造 provider slot。
- 定向 edit 的改变进入现有 `edit_delta`，未改变义务进入 preserve；既有 select_image_rows 可能省略 camera/light。A4 必须测试目标改变可达，不为此次知识吸收修改 edit serializer 的选择算法。无法用当前 edit_delta 表达则停止该任务设计，而非偷偷添加模板。
- C17/C36/观察型 C04/C28 进入 Review evidence，不回写 IR；只有原 owner 接受后形成新的批准决定才可产生新 Fact。C35 完全不进入 provider。

## Source 与 provenance 两条链

**创作/执行来源链**：批准 department Bible / asset / style → exact SourcePin(key,kind,fingerprint) → record id + JSON pointer → scoped decision leaf → derived mapping row → Fact.source → compile_ir.retained/omitted → prompt fingerprint → request。

**知识来源链**：external commit/section → A3 rule id/version/hash → local independent wording / validation state → application mapping（指向上述 decision leaf）。知识不能作为角色/历史事实来源，不能替代 approval，也不直接进入 prompt。

### D2 与 mapping receipt 的最小设计

1. 未来沿用 DirectorArtifactStore 保存普通派生 JSON receipt，key 标记为 still-professional-map；不新增 storage API 或服务实体。receipt 自身只有映射权，无 canCreate/canModify 专业 authority。
2. receipt 包含 `schema_id / rule_catalog_digest / work-scene-shot scope / source_pins / rows / not_projected / mapping_version`。每行有稳定 mapping_id、capability_id、唯一 decision owner、全部 canonical input pointers、目标 IR path、选择/拼接操作、选择后 text hash、priority 和 scope。不存 final prompt，不执行自由 LLM 重写。
3. `FrameSpec.professional_sources` 同时携带原件 pins 和 mapping receipt pin；fact.source 使用 `receipt-key@fingerprint#rows/<mapping_id>`。解析时用现有 SourcePin 列表查找，不能把 locator 当 URL 下载。receipt 只含 sources 的 pins，不含 FrameSpec/IR hash，从而避免 FrameSpec→IR→receipt 循环哈希。
4. 先冻结 source originals/receipt → 将 pins 放入 FrameSpec → 按现有算法计算排除 prompt_ir 的 source_fingerprint → 构造 IR → compile。D2 改变既有 source_fingerprint，从而不能沿用旧授权；没有 D2 时省略字段，旧 byte replay 保持。
5. 未来 Host 在 scoped A4 路径 reserve 与 begin-submission 两处通过现有 artifact resolver 打开 receipt 和每个 original，对 current map、Work/Scene/Shot、owner、approval、decision value/hash 和 IR text 重验。规则 metadata 只能验证版本/允许 scope；不能装作 creative approval。
6. Canonical 组合是确定性操作：COPY_LEAF / JOIN_ORDERED_LEAVES / SELECT_SCOPED_ITEM。没有“自动补足”“润色”“按模型重新理解”。字典结构作为意图原件由明确的字段映射消费；reason/criteria/source metadata 记录到 not_projected。
7. 动态 source freshness、approved originals 的真实性由 Host 已有工作上下文提供，不信任 caller 自造 current map。现有 Fact/source hash 检查不自动提供这一能力，A4 必须补此受控读验。

存在多重适用决定时：先按明确的批准 scope/关系选择；没有唯一批准局部替代则报冲突，退回原 owner。没有“最后加载者获胜”、也不自动把两个决定相加。继承 Work style 的子决定不得扩大边界。mapping receipt 是一个反映来源的索引，不成为新专业真相。

知识原件可通过已存在 artifact store 的普通字典保存；加载 A3 repo metadata 不等于已经装入 store。A3 只写设计文件。本地 application mapping 可以另存 metadata pins；由于 AssetDecision source_refs 白名单，不能借 provenance 改变其上游权限。

## No Professional Skill Owns Final Provider Prompt

`compile_ir` 保有唯一 serialization dispatch，`image_serializer.render_image` 当前仍可承载 GPT Image 2：已有 task sections、edit delta、preservation、预算和 replay，不存在必须立即拆分的能力证据。

未来如果独立研究证明需要 GPT Image 2 policy，它应作为 `visual/` 内 compiler 的纯 serialization policy，由已核准 provider family/task 唯一选择。policy 输入仍是已验证 IR 和 selected rows；只能改措辞/排布，不改 approved facts、medium、priority、source、参考身份或参数。每次 compilation 只选择一个 policy；receipt 记录 policy id/version 并可重放。该 policy 的新增字段与实现**不属于本次 A4 最小清单**，不能夹带进行。

Adapter 继续独占 model/transport/size/seed/quality/input slots 和异步执行 schema。serializer 不重新管理参数；Adapter 不增强或重写 prompt。SCLCAM、GPT 五段、realism 六段均未选为 winner；这里只保留边界，不借设计 provider policy 吸收被排除的 capability。

## 失败与回流

| 条件 | 设计结果 | 修复 owner |
|---|---|---|
| knowledge rule 不是本轮 allowlist / medium 非 LIVE_ACTION / task 是 VIDEO | 不应用 A3 profile | 当前原流程；不得强行转换 scope |
| source stale、缺真实批准、错误 Work/Scene/角色 | 停止本次投影，保留诊断 | source 原 owner / 当前 Host resolver |
| mapping leaf 缺失或 text 无来源；重要义务被当可省略删除 | 不产生可执行新请求 | mapper/原专业 owner（依根因） |
| required reference duty 没进入 IR 或主体/slot 不匹配 | 停止新请求 | Reference Strategy / frame mapping |
| D1 非空但 consumer 不能消费；新 effect 会改 approved 身份 | 不默默忽略或改 asset | GlobalStyle / scoped Camera/Grade |
| QA 无实际媒体 | UNKNOWN/DESIGN_ONLY，不得 production PASS | review 取证 |

这些诊断是未来设计准则，本轮未新增 error code 或 gate 实现。
