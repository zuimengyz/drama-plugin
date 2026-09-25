# A3 — A4 Minimal Implementation Plan

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED。本文件是 A3 提案，不改变当前 Skill、Python、route 或生产权。仅 16 个 A2R ADAPT capability；所有 Video assimilation 排除。

## 决定

**READY_FOR_A4 = YES，仅指以下最小、显式启用的实现范围已具备设计依据；本轮没有执行 A4。**

A4 可以使知识在原部门中被表达、引用、投影并检验；它不能将 LOCAL_EXPERIMENTAL 自动升级 PLATFORM_VALIDATED/PRODUCTION，后两者需要 A5 与原审批流程。当前 GPT Image 2 route、MCP、Service、Storage、Director boundary 保持不动。

## 逐文件预计影响

“需要修改”是未来 A4 清单，不是本轮 diff。新 module 是纯编译前映射职责，不注册为 Skill/专业 owner；若实现过程发现需要新执行入口或违反停止条件，应暂停而非扩建架构。

| File | Change class | Expected impact |
|---|---|---|
| `plugin/skills/cinematography/SKILL.md` | KNOWLEDGE/DOC | C02–C07/C13 字段语义、反例与来源要求；不写 provider 文本 |
| `plugin/skills/lighting-design/SKILL.md` | KNOWLEDGE/DOC | C09/C28 source visibility、软硬、材料交互与观察分离 |
| `plugin/skills/color-design/SKILL.md` | KNOWLEDGE/DOC | C10 palette 归属、必要/可省略静态目标 |
| `plugin/skills/color-grading/SKILL.md` | KNOWLEDGE/DOC | C10/C11 approved capture boundary 与实际 footage 匹配分离 |
| `plugin/skills/specialized-asset-design/SKILL.md` | KNOWLEDGE/DOC | C15 stable anchors/C28 material；D1 只读边界；不复制外部 anchor template |
| `plugin/skills/reference-strategy/SKILL.md` | KNOWLEDGE/DOC | C15 每图 carry/not-carry 与 current-state owner；无 cap/route 改动 |
| `plugin/skills/blocking/SKILL.md` | KNOWLEDGE/DOC | C15/C28 当前接触/姿势事实高于 reference pose；无新表演权限 |
| `plugin/skills/action-choreography/SKILL.md` | KNOWLEDGE/DOC | C28 静态接触截面与 Lighting/QA 的边界；不吸收视频运动 |
| `plugin/skills/shot-production/SKILL.md` | KNOWLEDGE/DOC | C17/C36 观察 criteria 与 C35 仅实验原则；reference 正式 IR 覆盖要求 |
| `plugin/skills/shot-production/references/production-rules.md` | QC KNOWLEDGE | 补 criteria applicability/evidence/repair-owner；不改 disposition |
| `plugin/docs/professional-departments.md` | DOC | 既有 values authoring profile、知识出处非创作事实、QA criteria 与应用范围 |
| `plugin/docs/core-creative-r1.md` | DOC | D1 可选 still imaging 边界、来源和旧指纹兼容 |
| `plugin/src/drama_plugin/professional.py` | D1 REGISTRY METADATA | 仅给现有 global-visual-style authority_scope 描述加入 imaging_character；不新增 owner、不扩 Camera/Lighting 字段或 DAG |
| `plugin/src/drama_plugin/contracts/specialized_asset.py` | D1 FIELD_EXTENSION | 只加可空 imaging_character 和两个小值类型；None 序列化精确省略，不改其它字段 |
| `plugin/src/drama_plugin/hosts/specialized_asset.py` | D1 VALIDATION | save_style 对 D1 source refs/Work/medium/scope 作受控验证；不推默认 style |
| `plugin/src/drama_plugin/specialized_asset.py` | D1 SOURCE MAPPING | 验证非空 D1、在 GLOBAL_STYLE sourceMap 记录字段；不把成像边界附加为 asset prompt；无 D1 分支输出字节不变 |
| `plugin/src/drama_plugin/visual/frame_request.py` | D2 FIELD_EXTENSION / REPLAY | FrameSpec.professional_sources 可空；非空纳入 source fingerprint，空字段从 legacy dump 省略；读取 mapping 输出而非 raw append |
| `plugin/src/drama_plugin/visual/still_knowledge.py` | NEW PURE MAPPING MODULE (PROPOSED) | 仅验证 A3 profile/source map、从原件选择事实构造既有 IR/mapping receipt；无网络、无 IO 权威、无 final prompt renderer |
| `plugin/src/drama_plugin/hosts/route_production.py` | SOURCE REPLAY HOOK | opt-in A3 mapping 的 reserve/begin-submission 读取 existing store current originals 并重验；现有授权/route/预算完全保留 |
| `plugin/tests/test_specialized_asset.py` | FUTURE OFFLINE TEST | D1 absent byte equivalence、wrong medium/source/stale、无资产事实越权 |
| `plugin/tests/test_route_image_inputs.py` | FUTURE OFFLINE TEST | D2 pins/hash/slot、reference duty 与 current state、map tamper、legacy compatibility |
| `plugin/tests/test_visual_prompt_ir.py` | FUTURE OFFLINE TEST | same source chain 到 retained/omitted、内部字段不出 prompt、edits 的 delta 可达 |
| `plugin/tests/test_still_knowledge.py` | NEW TEST ONLY (PROPOSED) | 16 allowlist、owner mapping、scope、missing source、no invented facts、reference leakage 声明覆盖、单一 writer |

## 明确无需修改的文件/模块

| 文件/模块 | 保持理由 |
|---|---|
| `plugin/skills/director/SKILL.md`；Director Python/contracts | WHY/部门仲裁已经明确；不可变更以容纳摄影知识 |
| `plugin/src/drama_plugin/contracts/professional.py` | CreativeBible/Record 现有 envelope 与 values 足够；不新增权限字段 |
| `professional.py` 的 Camera/Lighting registry / can_create / DAG | 所需顶层字段已有；只允许上表 D1 的既有 GlobalStyle 字段元数据同步，不新增 realism/global-cinema owner或依赖 |
| `plugin/src/drama_plugin/contracts/visual_prompt.py` | 现有 Fact/source、camera/light/preserve 足够；不新增 lens、color、capture-era 顶层 IR |
| `plugin/src/drama_plugin/contracts/cinematic.py` / `hosts/cinematic_projection.py` | 本轮非 video；旧 CinematicShotSpec 仅作当前上下文，不能被当新增摄影合同入口 |
| `plugin/src/drama_plugin/visual/prompt_ir.py` / `image_serializer.py` | 当前唯一 writer 继续使用；不换顺序、不做 provider split、不改 negative/face-anchor 策略 |
| `plugin/src/drama_plugin/visual/image_route.py` / `gpt_image2_template.json` | route、model、transport、质量/数量/尺寸参数不因知识改变 |
| `plugin/src/drama_plugin/visual/production.py` | Review disposition、预算、UNKNOWN/幂等恢复不变；checks 已支持 criterion key |
| `plugin/src/drama_plugin/providers/**`；MCP/Service；Storage/DirectorArtifactStore | 使用现有接口保存普通 metadata 和读取原件，无新 Provider 或存储实体 |
| manifest / Skill registry / `.agents/skills` / installed cache | 不新增正式 Skill、不安装外部 runtime |
| legacy character-art/environment-art/costume 等兼容视图 | 不恢复为作者，不写第二份资产事实 |

## 两个 schema delta 的实施接受条件

D1 与 D2 是本次全部必需顶层字段扩展，不另增 knowledge_source、camera_angle、depth_of_field、new_review_disposition 等字段。没有 D1/D2 的 legacy snapshot 必须完整 byte-equivalent；仅“不报错”不够。不要通过全局 dump omit 改其它 None/empty 值。

D1：新增 Work 成像边界后，先保留原件版本和批准来源；新版本不同 hash，旧审阅/支付权限不能借用。A4 不允许为所有既有 Work 迁移或填默认。启用 D1 的静态路径必须能准确消费它；不支持的 consumer fail closed。

D2：源 pins 入 FrameSpec，mapping receipt 保留全部被选 canonical leaf 和知识应用来源；只 source locator 非空仍不算成功。opt-in A3 source 验证在 reserve 与 begin-submission 都需运行；真实 current/approval 从已有 Host 读取，不能用 caller 自报指纹。对于 `scope_context`，不重用它偷偷存 provenance：它已是 scoped payload 上下文，另塞 receipt 会混淆职责。

新纯模块只输出既有 IR 及 metadata，不输出 final provider prompt。自然语言 `intent` 来自专业 owner 原件，选择/拼接可重放。Projection 没有权力解释历史、改变 pose 或补灯。若对 mapping 的修订改变编译结果，必须走现行新 hash/requalify，不能重写 frozen receipts。

为保留旧行为，A4 的新路径以存在已批准 A3 professional_sources/mapping 为显式选择，旧请求仍原流程；未来若要把 A3 设为全局生产默认，须另一次发布决定与 A5 证据，不能在本次兼容分支里偷偷默认启用。此处新旧分支按版本/请求 scope 唯一，不同时输出两套 prompt。

## 建议实现顺序与验收

1. 首先加入独立知识文档与同 scope 正反例；不改任何批准 Work。
2. 实现并验证 D1/D2 的 nullable compatibility；再实现纯 mapper/source resolver，先仅用离线原件 fixtures。
3. 接入现有 route Host 的两个 source recheck 点；必须证明 changed source、forged owner、不同 Work、reference slot drift 均不能进入新请求。
4. 同一字段决定只输出一次，source/dest 覆盖可重放，reason/provenance/QC 不出 prompt；edit changes 通过既有 delta、preserve 成功消费。
5. 回归现有专业/资产/IR/静态 serializer/reference/route 测试；新增测试只检验真实边界，不把文档关键词计数当艺术质量。任何 paid/network 调用都不属于离线验收。
6. 保留 old request/no-D1/no-D2 全字节快照；不改变其它 medium/provider/video 行为。完成后只报告实现/离线证据，A5 生产实验另行授权。

## 旧规则与 deprecation

`LOCAL_RULES_TO_DEPRECATE_NOW=[]`。C02–C07/C09 等是原 owner 的知识充实，语义 profile 替代模糊示例措辞，不形成旧准则+新准则双写；并没有证据支持删本地 face/negative/route 规则。旧审批与 receipt 永久保留作 replay。

若 A5 日后证明某具体本地 heuristic 必须被替换，届时逐 rule/version 指定 REMOVE/DEPRECATE_AND_DISABLE/MOVE_TO_HISTORY/REFERENCE_ONLY，停用其同 scope 运行权，再启用新版本。不得“两个 prompt 都留着看顺序”。本 A4 不预先替换 serializer policy，也不重启 A2R 被拒绝项。

## A4_READINESS_MATRIX

Runtime Change Needed 指未来 A4，非本轮已发生；所有行还需 A5，YES 不表示摄影效果已验证。

| Capability | Canonical Owner | Current Contract Sufficient | Runtime Change Needed | Validation Needed | A4 Ready |
|---|---|---|---|---|---|
| C02 | cinematography | YES | 知识/语义文档；共享 source mapper 消费，不新增专门字段 | 覆盖两人同时可读/手部关键动作/环境地标；适用 A5逐维观察 | YES |
| C03 | cinematography | YES | 知识/语义文档；共享 source mapper 消费，不新增专门字段 | 高度与俯仰不混淆；低机位平视不被改成仰拍；适用 A5逐维观察 | YES |
| C04 | cinematography（设计）; spatial-continuity-qa（观察） | YES | 知识/语义文档；共享 source mapper 消费，不新增专门字段 | 距离-视角-景别矛盾证据；遮挡不足保留 UNKNOWN；适用 A5逐维观察 | YES |
| C05 | cinematography | YES | 知识/语义文档；共享 source mapper 消费，不新增专门字段 | 居中/对称正例；构图不改变 actor positions；适用 A5逐维观察 | YES |
| C06 | cinematography | YES | 知识/语义文档；共享 source mapper 消费，不新增专门字段 | 不由 genre 填固定 mm；无精密模拟承诺；适用 A5逐维观察 | YES |
| C07 | cinematography | YES | 知识/语义文档；共享 source mapper 消费，不新增专门字段 | 对话双方/关键手部需可读；未选择虚化则无默认；适用 A5逐维观察 | YES |
| C09 | lighting-design | YES | 知识/语义文档；共享 source mapper 消费，不新增专门字段 | 来源与时段/阴影一致；无无理由 rim/bloom/美化；适用 A5逐维观察 | YES |
| C10 | color-design; color-grading | YES | 知识/语义文档；共享 source mapper 消费，不新增专门字段 | 肤色材质身份不被重涂；无媒体时不声称已 grade；适用 A5逐维观察 | YES |
| C11 | global-visual-style（work边界）; cinematography/color-grading（各自实现） | PARTIAL | D1 + 共享 D2/source mapping；无 IR/route 扩展 | 缺省零效果；texture 不改皮肤/伤痕；旧序列化无 null 增量；适用 A5逐维观察 | YES |
| C13 | 各原专业 owner；cinematography协调镜头描述缺口 | YES | 知识/语义文档；共享 source mapper 消费，不新增专门字段 | 原始事实保留、无凭空物件；filler人工分辨而非硬黑名单；适用 A5逐维观察 | YES |
| C15 | specialized-asset-design; reference-strategy; blocking/action/DPD（当前状态） | PARTIAL | D2 + source/role replay；无新 reference capacity | formal IR 路径参考角色/slot语义可见；无 pose/gaze/expression/light 泄漏；适用 A5逐维观察 | YES |
| C17 | visual-continuity-qa / production review | YES | 仅 QC criteria/evidence 文档；不改 Review 状态 | approved anchor 比对；观察不清 UNKNOWN；minor 不 REGENERATE；适用 A5逐维观察 | YES |
| C28 | specialized-asset-design/prop-design; blocking/action; cinematography; lighting-design; QA（各自子职责） | YES | 知识/语义文档；共享 source mapper 消费，不新增专门字段 | 阴影条件适用性、接触清楚程度、材料随光一致；无 realism 超级 owner；适用 A5逐维观察 | YES |
| C30 | global-visual-style; source/world 原 owner不变 | PARTIAL | D1 + 共享 D2/source mapping；无 IR/route 扩展 | 19世纪故事不推出古摄影或手机；未批准留 null；适用 A5逐维观察 | YES |
| C35 | shot-production 的实验设计（不取得常规生产控制权） | YES | 无生产策略改动；仅实验 manifest | OLD/NEW 双边对等；预算另授权；多项相关修复在生产仍合法；适用 A5逐维观察 | YES |
| C36 | visual-continuity-qa / spatial-continuity-qa / production review | YES | 仅 QC criteria/evidence 文档；不改 Review 状态 | camera/light/color/readability 逐维；不合成 subjective winner；适用 A5逐维观察 | YES |

所有 16 项的来源/职责已唯一分配。未触发改变 Director、第二 writer、MCP/Service/Storage、换 Provider、fal 安装、新 Runtime Skill 或 Video 依赖等停止条件。实施时遇到新的无法唯一裁决冲突，必须停下记录，不能援引 READY_FOR_A4 擅自扩大范围。

**本轮 STOP：以上只是 A4 计划。**
