# Prompt A2 — Local Capability Mapping

2026-09-26 · HEAD `789ed88d895bee045f24cf4432971da8220e5310` · NON_RUNTIME

结论：上游意义、可拍摄转译和来源映射都已部分结构化；缺少的是跨创作类型、镜头用途、输入模式的统一“不可丢失语义义务→可见事实→最终表达”闭环。不能宣称 Meaning 或中间翻译能力从零缺失。STILL/VIDEO 已有分流，但还不是统一治理、分模式验证的完整 policy 体系。

## 本地证据目录

下列路径相对仓库，行号与完整 symbols/hash 见 [local-source-index.json](evidence/local-source-index.json)。这是一份当前代码审计，不是从旧报告推测 Runtime。

| ID | Current evidence | 关键定位 |
|---|---|---|
| L01 | [creative_source contracts](../../../plugin/src/drama_plugin/contracts/creative_source.py) | PhilosophicalCore 74；Preservation 86；CinemaExpression 129；ScreenplayInput 225 |
| L02 | [creative_source compiler](../../../plugin/src/drama_plugin/creative_source.py) | compile_source 224；literary sourceMap→cinema/characterArc 244–271 |
| L03 | [professional registry](../../../plugin/src/drama_plugin/professional.py) / [contracts](../../../plugin/src/drama_plugin/contracts/professional.py) | registry 23–73；CreativeRecord；ShotAssembly.dramatic_purpose 134 |
| L04 | [Director](../../../plugin/src/drama_plugin/director.py) | trace_intent 208；source_intent 235；不重新解析源作品 |
| L05 | [cinematic contracts](../../../plugin/src/drama_plugin/contracts/cinematic.py) / [review](../../../plugin/src/drama_plugin/visual/cinematic.py) | ObservableAction、PerformanceBeat、narrative_intent；review_direction 104 |
| L06 | [embodiment contract](../../../plugin/src/drama_plugin/contracts/character_embodiment.py) / [Skill](../../../plugin/skills/character-embodiment/SKILL.md) | EmbodimentRule source→interpretation→observable_evidence；contrast reasoning-only |
| L07 | [specialized assets](../../../plugin/src/drama_plugin/specialized_asset.py) / [Skill](../../../plugin/skills/specialized-asset-design/SKILL.md) | compile_asset 135；provider_projection 189；design text/reason/source_refs |
| L08 | [still mapping](../../../plugin/src/drama_plugin/visual/still_knowledge.py) | MappingRow；_leaf；make_receipt；project_ir 282；replay 415 |
| L09 | [route Host](../../../plugin/src/drama_plugin/hosts/route_production.py) | validate_still_professional_sources 324；prepare_still_projection 360；两个提交门重读来源 |
| L10 | [VisualPromptIR](../../../plugin/src/drama_plugin/contracts/visual_prompt.py) | Fact 16；Blocking 64；Action 71；Temporal 109；VisualPromptIR 126 |
| L11 | [compile_ir](../../../plugin/src/drama_plugin/visual/prompt_ir.py) | 编译 12；selectors 93–102；budget 116–130；submission gate 138 |
| L12 | [image serializer](../../../plugin/src/drama_plugin/visual/image_serializer.py) | select_image_rows 9；render_image 27 |
| L13 | [frame_request](../../../plugin/src/drama_plugin/visual/frame_request.py) / [image_route](../../../plugin/src/drama_plugin/visual/image_route.py) | IR 编译/覆盖旧 prose 303–326；route 从空 prompt 构造 API graph |
| L14 | [video_prompt](../../../plugin/src/drama_plugin/visual/video_prompt.py) | compile_video_prompt 6；compile_request_ir 37；asset semantics 注入 continuity |
| L15 | [Vidu serializer](../../../plugin/src/drama_plugin/visual/vidu_serializer.py) | select_rows 6；render 25 |
| L16 | [cinematic projection](../../../plugin/src/drama_plugin/hosts/cinematic_projection.py) | INTERNAL_FIELDS 14；narrativeIntent upstream lock 99；IR 验证/替换 195–233 |
| L17 | [video adapter base](../../../plugin/src/drama_plugin/providers/video/base.py) / [adapters](../../../plugin/src/drama_plugin/providers/video/adapters.py) | prompt_text 为 core compiler 的兼容别名；adapter 做 payload transport |
| L18 | [budget](../../../plugin/src/drama_plugin/hosts/prompt_budget.py) / [payload scope](../../../plugin/src/drama_plugin/visual/payload_scope.py) | 字符硬限/结构标签压缩；scope gate、exact-block 去重、asset_payload |
| L19 | [film grammar](../../../plugin/src/drama_plugin/contracts/film_grammar.py) / [editorial authority](../../../plugin/src/drama_plugin/contracts/editorial_authority.py) | intent handoff、must_preserve、受保护 editorial intent loss；不等于 prompt atom |
| L20 | [A4 joint report](../still-liveaction-a4/Still-LiveAction-A4-Implementation-Report.md) | opt-in STILL/LIVE_ACTION；知识 LOCAL_EXPERIMENTAL；不改变 serializer |

## CURRENT_PROMPT_AUTHORITY_MAP

“影响最终 prompt”区分经专业决定间接影响、确定性映射、实际语言输出。Host 运行这些边界并不能机械证明它理解了文学内涵。

| Layer | What it knows | What it owns | What it emits | Does it affect final prompt? |
|---|---|---|---|---|
| Work / Story / adaptation | 主题、冲突、来源边界、关系与事件 | Canon 与适配决定 | Work.content、Story Bible、AdaptationContract | 间接；不应整篇发送，L01–03 |
| literary cinema translation | 决定如何成为可拍摄表达 | shootable intention，非摄影执行 | CinemaExpression、nonverbal alternative、来源映射 | 经 screenplay/专业决定；没有直达每个 Fact 的强制链，L01–02 |
| Script / Episode | 因果推进、节奏、场次功能 | 改编结构与 episode progression | open content + screenplayInput | 间接；由 scene/专业 owner 消费 |
| Scene development | scene_purpose、conflict、beats、reversal | 场景因果与状态变化 | Scene Beat Bible、正式 Scene | 间接；A4 可映射 world/time 叶，非主题直写，L03/L08 |
| Director | 全片解释、重点、WHY、分层 intent | 意图与冲突仲裁 | Director Vision、intent refs/requests | 经专业决定；narrativeIntent 在 L16 为 UPSTREAM_LOCK |
| Character dramaturgy / external driver | 身份、目标、矛盾、关系、arc stage | 谁是此人 | Character Bible / pinned package | 资产与表演的上游，不能从相貌反推意义 |
| Character embodiment | 意义的身体行为证据 | source-bound observable inference | rules/theses/conditions | 给 Asset/Performance；有局部中间层，L06 |
| Casting | 候选角色适配与可表演范围 | proof/selection，不是正式身份 | plans/proof requirements | 独立候选编译分支；不与 shot serializer 混为同 scope |
| Specialized Asset | 稳定脸、年龄、发、身体、服装、环境 | concrete asset text | AssetDecision + reason + source refs | A4 exact leaf→IR；legacy asset projection 另有 scoped branch，L07–08 |
| Scene environment / layout | 地形、建筑、道具与位置关系 | 场景资产归 Specialized Asset；Layout 归位置 owner | SceneAsset / Layout Bible | environment/blocking，旧 environment-art 等是只读兼容视图 |
| Blocking / Action / Performance | 姿态、视线、接触、动作因果、变化 | 各自 HOW | 当前状态叶、action beats、expression | still 当前截面，video 时间展开，L03/L05/L08 |
| Cinematography | 观察对象、视点、距离、透视、焦平面、可读性 | Camera decisions | Camera Bible intent/reason/criteria | camera.*；当前 still profile 禁运镜/拉焦，L08 |
| Lighting | 光源、动机、方向、软硬、反差 | 照明可见事实 | Lighting Bible | lighting.*，理由不发模型 |
| Color / Grade / GlobalStyle | 色彩发展、材质肤色保护、成像边界 | 独立色彩/后期目标；Work style | Color/Grade intent、D1 imaging_character | required→preserve；optional→secondary，D1 仅受支持路径 |
| Reference Strategy | 媒体承载何种事实、排除何种状态 | carry/exclude/coverage duties | SourcePin + media slot/hash + preservation_text | preserve；图像输入独立绑定；portrait 不自动承载 pose/light，L08 |
| Shot / Clip / cinematic-direction | 为什么拍、覆盖目的、起止态、拍摄可行性 | 薄组装、clip 边界和兼容投影 | ShotAssembly、CinematicShotSpec | 原件→执行意图；不允许 provider 重写镜头，L03/L05/L19 |
| still mapper / Host | 叶、owner、scope、approval、版本 | 确定性映射和重放 | receipt + VisualPromptIR | COPY/JOIN/SELECT；不创建新动作或修辞，L08–09 |
| VisualPromptIR compiler | 当前事实、任务、scope、priority | 筛选/预算/编译记录 | retained/omitted、prompt/hash | YES；它不是意义解释器，L10–11 |
| static / Vidu renderer | 被选中的事实与任务模式 | 当前 scope 最终语言组织 | provider prose | YES；static/edit/Vidu 已分流，L12/L15 |
| generic video projection | typed IR 或旧 frozen spec | core 的视频语言投影 | generic labeled rows 或 legacy prose | YES；formal IR 覆盖旧 prose，L14/L16 |
| Provider Adapter | payload schema、输入、参数、限制 | transport/capability | 请求，不拥有 Canon | 接收核心编译结果；不能再润色，L17 |
| QC / review | required fact 与实际证据/用途偏差 | 观察、UNKNOWN、repair owner | Review/QA sidecar | 间接回 owner；不是第二创作或自动 retry，L08/L20 |

## CURRENT_STILL_VIDEO_PROMPT_PIPELINE

### STILL 正式镜头链

1. 已批准专业 originals + exact SourcePin/leaf，保留各 owner。A4 是显式启用 profile；不能把它称作所有既有 Work 的全局默认。
2. `prepare_still_projection` 用 `make_receipt` 冻结映射，再 `project_ir`。操作只有 COPY_LEAF、JOIN_ORDERED_LEAVES、SELECT_SCOPED_ITEM；不是 LLM 摘要。每个现存 Fact 必须有映射；拒绝未绑定旁路文本。
3. `FrameSpec.professional_sources` 绑定 originals 与 receipt；Host 在 reserve/begin-submission 重读 current 原件/审批、验证 actor/reference/required coverage 并 replay。
4. `compile_frame` 通过默认 GPT Image 2 模板选择进入 `compile_ir`，检查 source fingerprint、task、输入模式、主体绑定；编译后的 prompt **替换**旧 FrameSpec 生成 prose，不拼接两份。
5. `compile_ir` 取 medium、world、subject、blocking/action、environment/camera/light、continuity/preserve、positive targets、edit_delta、secondary；`Fact.source` 留在记录。CURRENT 可用于 still；action.non_current 被排除。VIDEO Temporal 不能放进 static IR。
6. image serializer 初始帧按 TARGET WORLD / SUBJECTS / CURRENT BLOCKING / ENVIRONMENT / CAMERA / LIGHTING / TARGET LOOK 输出。priority/path 标签不在最终静帧文字中；字段内正文基本原样。medium 有固定的 cinematic still 短语，专业原文中的泛词不会自动改成具体动作。
7. edit selector 只保留 delta/preserve/world/blocking/action/positive targets、medium、architecture、lighting.realism，以及 subject role/face/costume。camera、其它 lighting、hair/body/visible_condition、continuity 等留 IR 并记录 EDIT_SOURCE_PRESERVED_NOT_REDESCRIBED。输出 MUST CHANGE→PRESERVE→TARGET RESULT，保留 source issue 与 correction，不能一律删除“旧问题”文字。
8. 编译先按任务选择，再在超限时只删明确 optional SECONDARY；不能容纳必需文字则拒绝。`compile_frame` 此处不传 `hard_limit`，故没有当前静帧统一长度上限的事实依据。
9. 同一 prompt 写入 API workflow；提交门重编译校验字节等价。源 template JSON 内存在展示用 cyberpunk 示例，但 `image_route` 从空 prompt 构建实际图、随后填入编译结果；不能把静态 demo 文本误报为当前请求污染。

专业字段去向：face/surface_state/marks 在 A4 以有序 JOIN 汇入 face；age/hair 独立；当前伤/汗/妆来自 Look；expression 来自 Performance；Blocking 与当前接触来自其 owner。Camera visible intent、Lighting intent 直接映入 Fact.text。色彩 required 和 D1 preservation 放 preserve，optional 才放 secondary。reason/criteria/evidence_state/rule provenance/coverage 留 receipt/QA；不是提示正文。

### 资产/选角分支不能遗漏

`CharacterPromptFact` 已有 id/domain/text/sources/derived_summary，说明 atom 思想不是全新。`compile_asset` 和 `compile_character_art`/casting compiler 存在独立任务分支；不能笼统宣称项目所有视觉文字只有一个文件写入。`compile_asset` 的内部 receipt.prompt 包含 Director constraints；真正 `provider_projection` 调用 `asset_payload`，只选资产字段与媒介文本，不发送该内部 prompt。D1 非空且 consumer 不支持则报错。此分支是不同 scope 的权威，不是允许 adapter 对正式镜头二次写作。

### VIDEO HTTP 链

`VideoRequest`（作者输入及 continuity/refs）→ `compile_request_ir` → shared `compile_ir` → provider branch renderer → adapter `prompt_text` → payload。

- `compile_request_ir` 要求正式 prompt_ir；拒绝 post-normalization；如有 authority_context，资产 executableSemantic 加到 continuity；provider registry 提供字符限制。验证 task/input mode/source fingerprint。
- Vidu 且 text 模式：保留所有静态行与 temporal。Vidu reference/single_image/first_last：省略 hair/beard/body/visible_condition、非 architecture 环境细节等，但继续保留 world、face/age/costume、camera/light、blocking/action、continuity、preserve。**当前实际不是 motion-only**。
- Vidu 输出 START STATE / IDENTITY / ACTION / PERFORMANCE / CAMERA / END STATE / AUDIO / SETTING-CONTINUITY。精确相同文本有全局 `used` 去重，但 subject 按身份保留，end state 特意显式输出；起态/终态相同可能是必要保持，不能当冗余统一删。
- 非 Vidu VIDEO（包括此编译器下的 Seedance）走 generic `VIDEO CLIP` 加 priority/path/text，保留完整 subject/environment 信息；没有同等输入模式筛选。标签是否有帮助尚未视觉验证；当前确有内部组织标签进入文本的事实。
- legacy `compile_video_prompt` 无 IR 时，会把 r.prompt、negative、Canonical continuity JSON 和 reference roles 合并；其中可能重述人物/场景。此函数保留兼容能力，不等于新付费请求可绕过 IR。HTTP create 与正式提交门要求 IR；必须分开“可回放 legacy”与“可新提交”。

### VIDEO cinematic / Comfy 核心投影链

专业原件→CinematicShotSpec/frozen_creative→`hosts.cinematic_projection.project`。旧 prose 会投射 visualBible、opening、performance、camera、lighting、continuity、ending 等，并把 narrativeIntent、source/reason 等留 upstream lock。存在 IR 时再编译并替换旧正文，核对 opening/end、canonical action、exact dialogue、资产 executableSemantic 和 required refs。旧 manifest 改名 legacy_source_manifest，实际 manifest 来自 retained。该分支有更多源文覆盖检查；不能把 HTTP 仅 source fingerprint 的保证泛化为每条事实语义都验证通过。

视频没有直接调用 STILL renderer 后重写的链。它消费共享 IR 类型/专业源及自己的 temporal 数据。重复风险来自 **重新投影静态事实与 continuity 内容**，不是必然从图片 prompt 复制。不同视频分支的保护强度与语言组织不同，应分别治理。

## 离线观察与证据强度

[offline_probe.py](evidence/offline_probe.py) 阻断 socket connect，仅调用既有编译器和合成 fixture；[完整输出](evidence/offline-probes.json) 保留输入 IR、retained、omitted、prompt/hash。长度是 Python 字符数，不是 token 或模型硬上限。没有传入真实 provider registry 限制的对照不得推导生产请求可提交。

| Case | Observed result | 能证明什么 / 不能证明什么 |
|---|---|---|
| FIRST_FRAME | 1155 chars，non_current 省略 | static 分区输出；不证明图像保真 |
| IMAGE_EDIT | 657 chars，16 omitted | delta/preserve selector 实际执行 |
| Vidu text | 1229 chars | text 模式携带完整上下文 |
| Vidu single_image / first_last / reference | 各 608 chars，8 omitted | 有 mode-aware 静态减述；不能推广其视觉收益 |
| Seedance 同四模式 | 各 2393 chars，1 omitted | generic 路径未按参考输入减少同一组静态字段；不是 Vidu 优于 Seedance 的模型结论 |
| optional budget | 1375→654 chars；required-only 相同 | 仅 optional secondary 为预算移除 |
| required overflow | 100 字符限额被拒绝 | 未截断必需文本；保留 fail-closed |
| semantic duplicate | 两种“保持脸部身份”表达都存在 | 只有 exact 去重，缺少 semantic dedup |
| abstract expression | `alienated and lonely` 通过 compile_ir | 基础 IR 不验证“可见性语义”；并非证实某正式作品已这样生成 |
| edit critical continuity | 新加 CRITICAL 戒指可见性被 selector 省略 | priority 不保证 selector 后保留；A4 required receipt replay 可阻止静默成功 |

72 项既有相关测试通过，见 [日志](evidence/local-tests.log)。A4 `test_edit_required_omission_is_explicit` 特别验证后一保护：有 required row 被省略必须报错。本轮不把合成可达路径报告成线上缺陷发生频率，也没有修复 Runtime。

## HOST_MEANING_AWARENESS / MEANING_TO_VISIBLE_ATOMS_AUDIT

| 层 | a/b/c/d 分类 | 判断 |
|---|---|---|
| Work Meaning | 文学 d；历史 c + 局部 d | PhilosophicalCore/Adaptation/SourceMap 正式存在；历史 Work/Story 多在 open content/CreativeBible。不是 a |
| Scene Meaning | c + 局部 d | scene_purpose/conflict/reversal 和意图层级存在，专业依赖确实消费；缺统一 final prompt obligation receipt |
| Shot Dramatic Function | d（局部结构），c（prompt coverage） | ShotAssembly.dramatic_purpose、Shot.purpose、CinematicShotSpec.narrative_intent、intent handoff 均存在；不保证每项 MUST 落到输出 |
| Meaning→observable | c + 局部 d | CinemaExpression、EmbodimentRule、Performance ObservableAction 已具备；缺跨这些来源的统一可见义务辨识/保留闭环 |
| prompt meaning preservation | c | Fact/source/priority + A4 receipt 是强基础；drop cost/semantic equivalence/meaning coverage 未统一 |

a=不存在；b=只在上游文本；c=参与决定但未全链系统化；d=已有稳定结构。不同粒度不能强行只选一个；上述明确给出作用域。阅读字段或验证 hash 只能证明来源/结构，不证明 Host 每次正确理解作品。

三个须区分的层：

1. **Meaning**：例如用户给出的“他对真实生命的呼救保持冷漠”。它属于 Work/Scene/Director 意图依据，不是脸型或全局气质默认。
2. **Visible atoms**：若上游已批准，女孩抓袖口、他的躯干仍朝离开方向、未转身、未建立视线连接；动作发生在哪一刻及持续多久必须由 Blocking/Action/Performance 决定。不能从“冷漠”由 distiller 新造这些动作。
3. **Prompt language**：同一当前接触/朝向可组织为 still 现态句；video 还要表达获批的变化或持续、trigger、end state。没有批准动作就退原 owner，不给模型一句 alienated 让它自创。

当前专业决定直接进入语言的位置：A4 COPY/JOIN 的 intent/text→Fact.text→renderer、非 A4 作者给出的 IR Fact、旧 cinematic 的 `prose(executable(...))`。这些位置有 source pin，却没有自动证明“这些可见事实足以承载原意义”。抽象标签 review 已在 L05 对仅含部分泛词的动作给 MAJOR；它不覆盖任意英语心理形容词、所有表达字段或图片 IR。

**A3 需要统一 canonical semantic handoff/coverage 的设计输入；不应现在预判新增三套顶级 WorkMeaning/SceneMeaning/ShotFunction schema。** 先复用上述正式原件与 handoff，补全关联和可检查义务。WHY 归 Work/Scene/Director；可观察 HOW 归现有专业 owner；Shot 绑定用途/覆盖；Distiller 只选择与表述批准义务。这就是需要补的中间衔接，而不是新“懂文学的 prompt optimizer”作者。

## STILL_VIDEO_PROMPT_POLICY_AUDIT

**应共享上游语义，分别设计最终投影。** 已有实现分流是正确基础；还要按输入模式细分，不能粗分为“图像长、视频短”两个模板。

| Shared / divergent | STILL policy | VIDEO policy | Evidence / qualification |
|---|---|---|---|
| Work/Scene/Shot meaning | 同一批准意图，用当前可见载体表达 | 同一意图，用状态变化/持续表达 | L01–06；Meaning 留 trace，不原样塞主题词 |
| identity / assets | text image 需足够脸/体/衣事实；edit 按 source duty 保留 | T2V 仍需要；I2V 以有效 reference 承载+必要 anchor/约束 | L12/L15；外部 P09/P10 仅候选 |
| current state / relation | 姿态、表情、接触、距离、视线、空间层级核心 | 必须继承开态，明确变化与终态 | 静帧不能要求全过程；video 不能用 ending 污染 first frame |
| camera / light / materials | 当前构图、透视、焦平面、光照和材质关系 | 运镜/转焦/光变化是有时序义务；不变部分按 reference 覆盖判断 | still Camera 不拥有 video movement；不得照搬固定“motion only” |
| action/performance | 一个批准时点的截面 | 施受者、顺序、触发、持续/停顿、反应、终态 | L05/L10/L16 |
| reference | identity portrait 与整帧 source 的职责不同 | 首帧、首尾、参考多图、reference video 的时序能力不同 | P14 + 本地 carry/exclude；不可无条件推定都携带 pose/light |
| continuity/preserve | 编辑 delta 限定哪些不能改变 | 跨帧身份/接触/方向/对象状态及终点保持 | 不应一概删除 same-face，也不应重复四次 |
| sound/dialogue | 不发不可见音频指令；屏内文字另论 | 仅支持且获批 native audio 时投射精确对白/说话者 | L10/L11/L16 |

`shared semantic layer = approved source facts + scoped dramatic obligations + reference responsibilities + current state and lineage`。

`still-only prompt policy = current visible slice + initial/reference/edit selection + composition/readability + explicit delta/preserve`。

`video-only prompt policy = clip temporal realization + input-mode-aware static inheritance + motion/performance/camera change + timed continuity/endpoints/audio when supported`。

这些是 A2 决策边界，不是最终 schema。视频的 T2V 不可省略世界与身份；I2V 也不能只凭“有图”删不可见但必要的戒指/手部关系。引用图无法证明承载时，保留必要文字或返回 reference owner。STILL 可以为必要静态事实用更长文字；VIDEO 有足够 reference 时优先变化与保持，预算仍以实测家族和实际 capability 为准。

## PROMPT_ATOM_PRIORITY_BUDGET_AUDIT

值得建立可追溯的 canonical obligation/atom 概念，复用 Fact、CharacterPromptFact 与 receipt。这里调查候选属性用途，**不定义字段类型、schema 或 API**。

| Candidate attribute | 为什么值得 / 当前基础 |
|---|---|
| semantic_role | 分清身份、关系、状态、变化、保持，不能只凭字符串相同合并 |
| source / owner | 已有 pin/leaf/owner；要关联回决定与戏剧义务，不另复制 Canon |
| priority / drop_cost | 当前三档存在，但缺少“删它会丢哪个意义”的可追踪判断 |
| visible_effect | 让评审能检查接触/视线/位置，而不是抽象情绪词计数 |
| projectable_to_still / video | 取决于 scope、时间与输入模式；不能永久把身份归 still-only |
| provider_scope | 只限定语言策略适用家族/模式，不使事实成为 vendor 所有 |

最小单位应是不可拆的语义关系，例如 actor–action–target–time/negation，不能等同单词、句子或一个粗 `face` 字段。多个 atoms 可由一句承载，同一 atom 可有多个来源，仍须能追踪覆盖。

| Proposed priority interpretation | 超限处置 | 与当前的差别 |
|---|---|---|
| CRITICAL | Meaning-critical 或关键可见身份/因果/时间义务绝不能静默删；无法表达就拒绝或退原 owner | 现有 CRITICAL 对预算有效，但 selectors 可能先排除；须贯通 selection 到 emitted coverage |
| IMPORTANT | 支撑必要可读性/空间判断；只允许意义等价重表述 | 不因词多而降级；变化要可审查 |
| SUPPORTING | 帮助质量的材质/光学等，仅在适用且不竞争关键义务时保留 | 不自动低于故事，例如信物材质可能关键 |
| OPTIONAL | 明确可省的装饰；先去重，再按预算省略并留 reason | 接近现有 optional SECONDARY，不能把所有 secondary 自动归 optional |
| NON_PROJECTED | provenance/reason/QA 等控制信息不发模型 | 没有发文字不等于删掉其约束作用 |

Meaning-critical、Visual-critical、Quality-supporting、Decorative 是合理的**作用维度**，不宜互斥替代 priority。一个很小的物体可以同时是视觉与意义关键；一个大面积背景也可能只是装饰。drop_cost 由创作 owner 和用途决定，distiller 不能靠审美评分自行排序。

预算应分 hard provider limit 与经验 soft budget；前者服从 current capability，后者需家族/模式/任务实测。图片与视频可不同，但不能拍脑袋给常数。当前字符预算与 C 的 token budget 单位不同。压缩优先顺序：移走内部信息→同 scope 真重复合并→意义等价表达→已批准 optional 省略→仍超限则拒绝/回规划。不能删 MUST 来满足长度。

## ANTI_FILLER_AND_DUPLICATE_MEANING_AUDIT

| Language / location | Classification | Future disposition | 判断依据 |
|---|---|---|---|
| `Live-action cinematic still`，L12 | weakly causal / medium-context | KEEP ONLY IF JUSTIFIED | live-action 有明确媒介职责；cinematic 的增益未测，不能整句硬删 |
| `cinematic CG`，visual_medium | causal（媒介语境），不是赞美 | KEEP ONLY IF JUSTIFIED | 删除 CG 可能改变 Work 媒介；不按词表清除 |
| beautiful / masterpiece / award-winning / best quality 作为无目标赞美 | generic filler / non-causal 候选 | DROP（仅无批准可见作用时） | B 的反例；本地 sampled active serializer 未见自动注入全部这些词，不伪造污染清单 |
| ultra-detailed / high quality 作为文本 | provider-specific uncertain | REFERENCE_ONLY，待分家族测试 | 可能影响分布，也可能挤占义务；与 API `model.quality=high` 不同，后者是有效参数 |
| dramatic / lonely / alienated / tragic / existential | weakly causal 或不可操作意义标签 | KEEP ONLY IF JUSTIFIED；抽象意义留 source，缺 visible carrier 退 owner | synthetic 抽象 expression 可通过；不能从代码搜索推断模型必失败 |
| 固定“真实感”/material credible/identity preserve | 依 owner/source 可 causal，跨 owner 重复时稀释 | KEEP ONLY IF JUSTIFIED | L07 内部 receipt 和最终 asset_payload 不相同，必须查真正 payload |
| `CRITICAL subject.man.face:` 等 generic VIDEO 标签 | 结构性提示，模型效用 uncertain | REFERENCE_ONLY 作为现状；A3 评估是否可换表达 | L11 非 Vidu 分支确实输出；不是 provenance source 泄漏 |
| 肖像参考身份语句+face事实+continuity+preserve | 部分必要、部分 semantic duplicate 风险 | 合并同义义务，保留来源与不同 duties | 单说“窄脸”和“保留窄脸”未必重复：描述与约束职责不同 |

当前 image `dict.fromkeys` 是 section/subject 内 exact text 去重；Vidu `used` 是较广 exact text；payload_scope 也只做 exact/whitespace。没有跨 owner 的意义等价/冲突解析。synthetic 两句身份保持均输出，证明缺口可达；没有证明所有生产 prompt 都冗余。

建议原则 **one semantic obligation, one emitted phrasing per applicable scope**。同一人物/时点/对象/职责才可合并；相同短语属于不同人物不得合并。起点与终点都需要保持接触、不同 reference carry/exclude、负向 source_issue 与正向 correction，不能因词相近合并。等价关系不明就保留或回 owner；冲突先裁决，再去重。canonical atoms 值得研究，但不是添加一个会偷偷重写 Canon 的 NLP deduper。

## FINAL_PROMPT_INFORMATION_BOUNDARY

必须进入的不是所有 IR 字段，而是**本用途不可由已验证输入承载、且对结果必要的可执行义务**：主体绑定、必须可见的身份/对象/关系、当前状态、构图/光照可读性、编辑 delta/保留约束；视频另外含动作/表演/运镜时序和连续性。reference 承载与文字承载可以分工，required obligation 的覆盖不能消失。

永不以控制数据身份进入 final prompt：审批标记、预算/费用、凭据、内部 hash、source locator、版权判断、知识来源/版本、评审分数、QC 原因、失败日志、原件整包、未批准提案、未来非当前场景计划、原始推理/比较试验材料。它们留 IR/source/reason/QA/provenance。注意不是禁掉同名自然词：屏幕里批准出现的文字、当前可见的损伤、edit 的 source issue、合规 native audio 对白可成为任务事实。理由中的有效约束必须由原 owner 单独批准成可执行事实，不能随理由一起扔掉。

## PROMPT_EXTERNAL_TO_LOCAL_CAPABILITY_MATRIX

处置是研究决定，未执行导入。能力 ID 与 [A1 inventory](Prompt-A1-Capability-Forensics.md) 一一对应。

| External capability | Source | Local equivalent | Current owner | Relationship | Evidence | Proposed disposition |
|---|---|---|---|---|---|---|
| P01 contract-first | A1 | approved sources/intent handoff | Work/Director/Host | COMPLEMENTARY | L01–04/L19 | ADAPT |
| P02 causal context | A1/A2 | scoped payload + current facts | professional owners/compiler | COMPLEMENTARY | L08/L18 | ADAPT |
| P03 one owner | A2 | registry/source owner gates | professional registry | OVERLAP | L03/L08 | KEEP_LOCAL |
| P04 minimal preserving wording | A1 | whole-leaf copy + exact prose | compiler | COMPLEMENTARY | L08/L11 | ADAPT |
| P05 path-only context | A1/A4 | Host source resolver | Host | ARCHITECTURE_MISMATCH | L09；provider 无文件 reader | REFERENCE_ONLY |
| P06 paired/holdout eval | A3 | 摄影/Face A5 固定实验思想 | QA/research | COMPLEMENTARY | L20、两份 A5 合同 | ADAPT |
| P07 stopping rules | A3 | Production budget/review gates | Production | OVERLAP | L20/visual.production | KEEP_LOCAL |
| P08 family projection | B1 | compile_ir static/Vidu/generic dispatch | compiler | COMPLEMENTARY | L11–16 | ADAPT |
| P09 static/edit structure | B2 | image_serializer delta/preserve | image serializer | OVERLAP | L12 | KEEP_LOCAL |
| P10 I2V static reduction | B3/B4 | Vidu non-text selector | core video policy | COMPLEMENTARY | L15/probes | ADAPT |
| P11 temporal expression | B3/B4 | Temporal + CinematicShotSpec | Action/Performance/Camera/Clip | OVERLAP | L05/L10/L16 | KEEP_LOCAL |
| P12 fixed word count | B3/B4 | dynamic hard character limit | capability/compiler | PROVIDER_ONLY | L18，未测本地 family | REFERENCE_ONLY |
| P13 concrete anti-filler | B1–4 | authoring skills + abstract-action review | professional owners | COMPLEMENTARY | L05/L08 | ADAPT |
| P14 reference roles | B2 | approved carry/exclude/hash binding | Reference Strategy | OVERLAP | L08/L09 | KEEP_LOCAL |
| P15 exact visible text | B2 | scoped visible_text；exact video dialogue | Graphics/Dialogue/compiler | COMPLEMENTARY | L16/L18 | ADAPT |
| P16 importance compressor runtime | C1 | no token classifier; explicit priority | compiler | ARCHITECTURE_MISMATCH | L10/L11 | REJECT |
| P17 forced retention concept | C1/C2 | required receipt/critical budget | owner + compiler | COMPLEMENTARY | L08/L11/probes | ADAPT |
| P18 budget-aware concept | C1 | character hard limit + optional drop | compiler | COMPLEMENTARY | L18 | ADAPT |
| P19 regression suite | D1/D2 | offline tests；A5 prospective | QA/research | COMPLEMENTARY | 72 tests/L20 | ADAPT |
| P20 calibrated controls | D1/D2 | negative/stale-source tests | QA/research | COMPLEMENTARY | test_still_knowledge / IR | ADAPT |
| P21 grader defines art | D1–3 misapplication | owner requirements + observation | Work/Director/QA | CONFLICT | L08/L20；D3 只评图像描述 | REJECT |
| P22 failure accounting | D1/D2 | UNKNOWN/FAIL Review evidence | QA/Production | OVERLAP | L08/L20 | KEEP_LOCAL |
| P23 genmedia/fal runtime | B1 | existing routes/adapters | Platform | OUT_OF_SCOPE | L13/L17 | REJECT |

没有 REPLACE_LOCAL 处置，没有把任何来源整个 ADOPT。Missing formal meaning-coverage、drop-cost 与 semantic dedup 是本地派生缺口，不伪装成外部已有完整实现。全部同 scope 冲突 winner 见 [A2R](Prompt-A2R-Conflict-Authority-Reconciliation.md)。
