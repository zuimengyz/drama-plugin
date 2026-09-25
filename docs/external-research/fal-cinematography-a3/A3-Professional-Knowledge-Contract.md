# A3 — Professional Knowledge Contract

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED。本文件是 A3 提案，不改变当前 Skill、Python、route 或生产权。仅 16 个 A2R ADAPT capability；所有 Video assimilation 排除。

## 1. 决策形状与权威

No Professional Skill Owns Final Provider Prompt。

Director 保留 WHY、戏剧优先级与部门仲裁。下述 contract 是同一组现有专业原件的作者约定，不是新的总 Bible。每个具体 decision 的 owner 是其原件 created_by_capability；跨部门内容只能引用并请求修订，不能在本字段新写一份。

通用 authoring profile 使用当前 CreativeBible / CreativeRecord 外壳：`id / scope_refs / source_refs / status / values / limitations`。`provenance` 继续为 `NEW_PROFESSIONAL_ELABORATION`，不新增外部 enum、不伪造 approved。值可细分为 `intent`（一个可见选择）、`reason`（为何服务已批准意图）、`constraints`（不可改变的边界）、`criteria`（如何观察是否满足）。这些是现有 values 内的文档化成员，不是新增顶层 API 字段。原有字符串记录保持可读，不要求批量迁移。

同一选择只在一个字段存一次。其它字段用决定 ID 引用；不复制互相矛盾的陈述。`intent` 不是 provider prompt：不包含模板顺序、endpoint、transport、参数、模型推荐或生成指令；reason/criteria 不默认发送模型。复杂复合值只有通过未来显式 mapping 才能成为多个 Fact，禁止用 str(dict) 直接串入文本。

所有记录必须有 Work/Scene/Shot 适用范围、当前上游 pins、可见主体/目标、owner、DECIDED 或 UNRESOLVED；不适用时标理由，不制造空白意义上的 PASS。描述意图是设计证据，媒体观察是另一证据层。

## 2. Cinematography：C02–C07、C13

下表的最左列均为当前 Camera Bible 的真实 key。内部语义成员是 A3 文档 profile；不另创 camera owner。

| Canonical existing field | 决策内容（结构语义） | 必要边界/判定 |
|---|---|---|
| spatial_readability | 要读到的 subject IDs、身体范围、关键物/接触部位、环境地标；哪些平面必须清楚、哪些可被遮挡/柔化 | audience target 从 Director/Shot purpose 引用；“看见两个人”不等于“看见两人反应” |
| shot_scale_philosophy | 景别意图、选择理由、身体/环境覆盖范围，引用 readability decision | 景别是可读性结果；不按题材随机填 close/medium/wide |
| camera_point_of_view | 观察者与人物的关系、主客观可见权限、共享或隔离的空间认知 | 视点不是 actor gaze；不新增角色知道的信息 |
| camera_height | 相对地面/人物身体部位的高度；必要时已批准数值及依据 | 不推断光轴方向；低机位也可以水平拍摄 |
| perspective | 光轴俯仰、朝向、人物-背景视觉关系及深度层次意图 | 与 height、distance 分开；不得凭角度给人物重新赋予地位 |
| camera_distance | 相机到目标的近远关系、可行站位与 subject/background 间距依据 | 不改变 Layout；无依据不填米数；不可行则退回 Layout |
| lens_intention | 希望呈现的空间伸缩/层次分离、焦平面优先级、允许柔化对象；可选 exact_mm 与 owner 理由 | wide/normal/tele/macro 是词汇，不是 genre→mm 查表；mm 不等于生成器严格光学仿真 |
| subject_hierarchy | 主次注意力、负空间用途、前景责任、对称或非对称、画面平衡、引导结构 | 对称/居中/平视均可；不把构图偏好变成真实度通用 gate |

相同焦平面决定只存 `lens_intention`，`spatial_readability` 引用其必须满足的对象；不重复写“另一套景深”。静帧只描述当前焦平面，禁止增加焦点转移、运镜或 clip duration。body position/gaze 来自 Blocking，expression 来自已批准表演投影；Camera 只能选择如何看。

C04 设计校验：给定当前空间与人物尺度，选取的景别、距离、视角和 lens feel 是否能同时满足 readability；无法判断则 UNRESOLVED，不用关键词启发式冒充物理计算。C04 媒体校验则检查实际可见透视，不从 mm 文本推 PASS。

C13 修订协议：报告具体看不清/关系不明/照明无因果的点→定位当前 source decision→由其 owner 补具体可见决定→生成新版本并使依赖过期。不得由 compiler 加灯具、肤质、动作或“电影感”修饰。filler 的语义诊断不等于禁用某个形容词；词存在不自动 FAIL。

独立表述的设计示例（不是 final prompt、不是 approved Work）：

```json
{
  "values": {
    "camera_height": {"intent": "机位与坐姿人物眼部大致等高", "reason": "保留双方对视关系"},
    "perspective": {"intent": "水平观察，桌缘与后墙提供稳定深度关系", "constraints": ["不移动桌子与门的位置"]},
    "spatial_readability": {"intent": "两人的眼部反应与桌上正在交接的手都需要辨认", "criteria": ["第二人的脸不被前景肩部完全挡住"]},
    "lens_intention": {"intent": "保留人物之间距离感，两个表演平面均可辨认", "constraints": ["不默认柔化第二人的脸"]}
  }
}
```

上例只是 partial values 展示，缺完整外壳、原件与批准，不能提交或生产。

## 3. Lighting：C09、C28 光照部分

| Existing Lighting field | 作者必须作出的决定 |
|---|---|
| source / practical_lights | 哪些真实或逻辑上存在的来源负责照明；来源可见/画外/间接，引用已存在 practical/环境；画外动机不等于凭空增加灯具 |
| motivation | 光与场景时间/空间/戏剧可读目标的因果关系；区分动机与美化偏好 |
| direction | 相对画面/人物的方向；软硬/阴影边缘选择及依据，分别表达 |
| intensity_relationship / contrast | 各来源与主体/背景的相对关系；需要保留哪些暗部信息，不默认补光 |
| falloff | 近远衰减和被遮挡区域如何变化；不得忽略环境几何 |
| visibility_priorities | 哪些脸/手/材料状态必须可见；涉及反射、遮蔽、接触处应符合来源的效果 |
| day_night_continuity | 当前时段及跨场景变化来源；不能保留互相矛盾的夜灯/晨光设定 |

hardness/softness 放在 direction 的结构语义中，无需独立 Python 字段。可见源本身归 Prop/Scene Asset；Lighting 只引用其 ID 并决定照明，不设计灯具或材质。warm/rim/volumetric/bloom 不能作为默认美化组；只有可追溯来源与用途理由才可选择。补光不是普遍禁止，也不是必备。

接触阴影的设计由 Lighting 针对 approved contact/location 提出可见结果；是否真的出现由 QA 看媒体，不在 AssetDecision 中写“接触阴影已正确”。存在柔和多源/遮蔽条件时，阴影不明显未必失败。

## 4. Color / Imaging：C10、C11、C30

Color Design 的 `scene_palettes / sequence_palettes / character_environment_color_relation` 决定场景颜色关系及发展。Grade 的 `grade_intention / exposure_continuity / tonal_range / skin_preservation` 只处理已批准方向下的匹配和保真；无媒体只能描述目标与待观察条件。

`world.era` 是故事/世界年代，由 source/world 决定。capture character 是观众所见成像方式，由批准 Global Visual Style 决定；它不是另一份历史年代。19 世纪故事可以采用经批准的现代电影成像，也可以不指定器材年代；两者都不能自动推出手机/古照相工艺、时间戳或现代场景物件。

### D1 — 唯一 Work 级成像扩展（设计草案）

当前 `GlobalVisualStyle` 没有可表达此边界的自由字段。提议新增可空 `imaging_character`，Python snake_case / serialized camelCase `imagingCharacter`。仍由 existing global-visual-style authority 提交，经原 Director 审核流程，不授予 Director 摄影实现权。

```text
GlobalVisualStyle.imaging_character: ImagingCharacterIntent | None = None
ImagingCharacterIntent:
  photographic_genre: Text | None
  capture_character: Text | None
  optical_texture: tuple[OpticalTextureIntent, ...] = ()
  reason: Text
  source_refs: tuple[SourcePin, ...]  # nonempty approved design basis
OpticalTextureIntent:
  effect: GRAIN | HALATION | BLOOM | SHUTTER_CHARACTER | OPTICAL_SOFTNESS
  intent: Text
  applicability: Text
  preservation_constraints: tuple[Text, ...]  # nonempty
```

此 draft 不是 Python 实现。至少 genre/capture/texture 一项实际有内容才允许非 null。D1 仅适用 LIVE_ACTION + STILL；当前 GlobalVisualStyle 无 modality 字段，因此子对象合同固定为 STILL，未来消费者不得读它给视频加效果；CG 下出现 D1 拒绝，不改变 CG 现状。scope 继承 Work，特定场景选用还须 Camera/Grade 的当前 scoped decision；Work 不放特定人脸、站位或具体灯具。

capture_character 独立描述影像特征，不必填写年月/品牌。五个 effect 是可选能力词汇，不自动展开：空 tuple=未请求效果。单张 still 的 shutter_character 只表达冻结/轻微可见模糊的成像结果，不含运动轨迹、rack focus、duration、FPS 或视频参数。保留边界明确禁止新增皮肤特征、伤痕、陈旧污渍、现代物件。

缺省 None 必须在未来序列化中**省略新增键**，保持旧 style bytes/fingerprint/replay，不用全局 exclude_none 改其它字段。非空产生新版本/指纹，审批不能继承；旧编译 consumer 遇到未支持非空 D1 应失败，不能静默丢失。style receipt 需记录新字段 provenance，但不能把其整段字典或 template 附在 asset prompt 后；静帧 source mapper 将选中意图交唯一 IR serializer。

## 5. REFERENCE_RESPONSIBILITY_CONTRACT：C15

| Reference carries WHAT | 不自动携带 WHAT | 当前 owner |
|---|---|---|
| 审批过的 face/body identity 与辨识特征 | reference 的站姿、视线、表情、动作 | Specialized Asset；当前 pose/gaze/position 归 Blocking，expression 归已批准表演方向 |
| 稳定 costume identity / 某批准版本 | 前一场破损/血污/湿度状态无限继承 | Specialized Asset + Look Continuity 当前状态 |
| 明确选定的场景地标/材料事实 | 原图相机角度、构图、光照、时段默认迁移 | SceneAsset/Prop 原件；Camera/Lighting 决定当前实现 |
| 已声明、已审核且当前需要的 reference duty | 一张美图顺带成为全能 identity/composition/style reference | Reference Strategy 规划责任，Host 绑定实际输入 |

同一图可承载多人物，但 `reference_members` 必须明确枚举，不能换脸/混服装。最小图片数量、三图 cap、edit_source 不混 stable references 的当前约束不变。REFERENCE_EDIT 场景基底的有意保留由具体批准 `preserve` 指定，不把身份参考的“不带构图”误作“所有编辑都必须改构图”。C15 不引入新 edit 模式或删 face-anchor 策略。

Frame Compiler 已实现：reference_lock/hash/upload receipt/slots、entity kind、actor identity/master binding、reference_members 与 Actor.position/pose/action/gaze；legacy 分支声明当前 Blocking 高于 reference pose。**未充分实现**：正式 prompt_ir 替换文本后，没有结构化强制保留上述 reference duty 说明，也未把全部专业原件 pin 存入 FrameSpec。

D2 提案：`FrameSpec.professional_sources: tuple[SourcePin, ...] = ()`（现有 FrameSpec 为 snake_case，不引入 camel alias）。仅保存专业原件与派生 mapping receipt 的 pins；全空旧分支保持 bytes，非空 pin 入原有 fingerprint。CURRENT body/gaze/pose 仍只来自 actors/approved Blocking/表演，不从参考像素推断。future mapper 将角色/职责作为 source-bound `IR.preserve[]`，唯一 serializer 输出；不附加第二段 raw prompt。缺 required role、主体/slot 不一致或缺当前 source 均停止这次请求，不能省略职责绕过 cap。

## 6. Realism without Realism Owner：C28

| 子责任 | 单一 owner | Canonical source | 观察修复边界 |
|---|---|---|---|
| 材料是什么、结构/磨损事实 | Specialized Asset；独立道具仍 Prop Design | SceneAsset.surface_material、CostumeAsset.material、CharacterAsset.surface_state、Prop.material | 不由照明或 QA 改材料 |
| 人与物在哪里、是否接触 | Blocking | physical_relations / handoffs；当前姿势和目标 | 不由 Camera 移动人物 |
| 支撑、握持、力与接触关系 | Action Choreography | body_mechanics / contact_constraints | 只设计静态可见接触截面，不扩大到视频动作计划 |
| 光照如何与接触/材料交互 | Lighting Design | source/direction/falloff/visibility_priorities | contact shadow 是条件性结果，不强制统一黑影 |
| 人物环境是否同一视角/尺度 | Cinematography（看法），Scene Layout（真实摆位） | perspective / camera_distance，引用已批准 topology | 不以所谓真实感改环境几何 |
| 画面是否满足上述约束 | QA / production review | observed evidence 与现有 Review | 判断 observation，发 repair request；不创造修复后的事实 |

材料 fact 与材料“看起来合理”的 observation 必须分别存放。QA 不能把看不清当“不存在”；更不能将未观察 PASS 回填资产。

## 7. STILL / LIVE_ACTION QC：C04、C17、C28、C36

criteria 是可观察问题，不是新的 disposition。只在真实输出 bytes/Media hash 和用途已知后执行媒体审查。设计检查叫 DESIGN_ONLY，不计媒体通过率。

| Criterion ID | 应观察的现象/比较依据 | existing Finding.category | Repair owner |
|---|---|---|---|
| QC-CAMERA | 景别、视角、背景比例/地标透视与批准空间是否一致 | CAMERA | Cinematography；若实际布局错退 Layout |
| QC-IDENTITY | 与批准身份对应的脸形、体态辨识特征是否严重偏离 | IDENTITY | Asset/Reference；执行错误由 production 修复 |
| QC-COSTUME | 锁定服装结构、身份标记、当前状态是否混人或漂移 | COSTUME | Specialized Asset/Look |
| QC-MATERIAL | 材料可见响应与批准的物质/结构是否相容 | SCENE / COSTUME / PROP_STRUCTURE，按对象 | 对应 Asset/Prop；仅光照错归 Lighting |
| QC-CONTACT | 手/脚/物体接触、遮挡、支撑的可见结果是否违背当前关系 | BLOCKING / ANATOMY / PROP_STATE，按实际错误 | Blocking/Action |
| QC-LIGHT-MOTIVATION | 可见亮区是否有合理场景来源或批准意图 | SCENE | Lighting |
| QC-LIGHT-DIRECTION | 主体、环境与阴影/高光方向是否冲突 | SCENE | Lighting |
| QC-COLOR | palette、肤色与材料身份是否仍符合本场/相邻批准关系 | CONTINUITY / COSMETIC，按实际影响 | Color/Grade |
| QC-READABILITY | 要读的反应、手/物、环境关系是否真的能读到 | CAMERA / CROP | Camera；不可任意改表演 |
| QC-CONTACT-SHADOW | 在当前来源/表面/可见度下，接触处阴影与支撑是否相容 | SCENE / PROP_STATE | Lighting；接触事实错归 Action |
| QC-INTEGRATION | 人物与环境的尺度、遮挡、接触、照明是否一致 | SCENE | 按可见根因发一个主 repair owner |
| QC-REFERENCE-LEAKAGE | 是否误继承了 reference 的 pose/gaze/expression/light/composition | BLOCKING / CAMERA / SCENE | 原当前状态 owner；执行侧修复由 production |

观察明细作为 review evidence artifact，含 criterion_id、applicability/reason、source requirement refs、media hash/区域、原始观察、证据充分性、use impact、repair owner。这里的明细字段**不是新增 Review 字段**。

准确投影现行 Review：

- applicable 且证据足够满足 → `checks[id]=PASS`。
- applicable 但被遮挡/没有证据 → `UNKNOWN`，无虚构 MAJOR finding；现行 status 为 PENDING_REVIEW。
- 可证违反核心用途 → `FAIL` + 对应 MAJOR finding，evidence 写明观察、批准要求、用途影响；无 MAJOR 不得填 FAIL。
- 轻微差异不影响用途 → PASS + MINOR finding，remedy 仅 ACCEPT/POSTPROCESS；现行代码拒绝 MINOR+REGENERATE。
- 不适用 → 不写伪 PASS，evidence 记录理由；任务真实 required 项不能标不适用逃避。
- 既有 `_review_status` 在 MAJOR 存在时返回 FAIL，即使还有 UNKNOWN；其它未知仍在证据中保留，不能假称都已观察。

Review 的 MAJOR/MINOR、remedy、PASS_WITH_NOTES/FAIL/PENDING_REVIEW 逻辑与 user adoption 全部不改。remedy=REGENERATE 是建议，不授权调用；不得发现差异自动 retry。两位 reviewer 分歧保留各自记录并由既有 review 流程裁决，不平均成总分。

## 8. C35：仅受控实验原则

一次改变一个能解释的专业 decision family，必要的关联物理参数作为同一预登记干预，不能伪称多个独立因果。修改相关联的景别/距离/景深以保持空间可行可构成一个干预；必须列出全部变化。常规生产仍允许一次修正多项相互依赖问题；不增加 turn 限制、默认批量生成或试错预算。具体 A5 见报告 E。

## 9. Knowledge provenance 与成熟度

[knowledge-contract-draft.json](knowledge-contract-draft.json) 给出全部 16 条本地规则、external commit/section/link、local owner、独立改写类别和状态。外部 provenance 只是知识出处，不是作品事实或上游批准。

未来采用 `rule_id + rule_version + 内容 hash` 固定知识原件。CreativeRecord.source_refs 可引用 kind=DESIGN 的 metadata pin，既有 source/approval refs 仍分别保留；绝不能把 knowledge pin 加到 registry depends_on 的必需专业 DAG 中。AssetDecision.source_refs 当前只允许自身 dramaturgy/director/world，所以**不能把知识 pin 直接塞入该列表**：资产的知识应用关系存非 Runtime application mapping evidence，key 为 asset Bible pin + asset id + field + rule hash；资产批准规则不变。

状态分开记录：

| 状态 | 条件 | 不代表什么 |
|---|---|---|
| EXTERNAL_CANDIDATE | A0 的外部来源证据结论 | 不代表有效专业规则 |
| LOCAL_EXPERIMENTAL | 独立改写且 owner/scope/contract 清楚（本 A3） | 不代表已实装或通过 A/B |
| PLATFORM_VALIDATED | A4 结构/来源检查通过，且 A5 在明确 scope 有逐维证据、无未解决重大回归，经负责 review 接受 | 单测不够；不能外推其它 medium/provider |
| PRODUCTION | 前项满足，加本地发布/启用审批；实际每次执行仍过原授权/预算/来源门 | 不是永久付费授权或用户作品采纳 |

这不是自动单链：外部源状态可以永远是 EXTERNAL_CANDIDATE，而本地派生规则通过自己的验证。修改规则产生新 hash/version，过往实验证据不自动继承。`LOCAL_EXPERIMENTAL` 不提升任何当前 approved Work 的状态。

许可边界沿用 LICENSE_DECLARED_MIT_NOTICE_INCOMPLETE；只独立抽象、独立表述和引用，不复制外部模板或大段文字。没有新的 provider prompting winner。
