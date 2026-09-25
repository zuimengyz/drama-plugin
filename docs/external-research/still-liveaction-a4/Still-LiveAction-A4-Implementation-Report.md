# Still Live-action A4 — Joint Implementation Report

日期：2026-09-25。基线 HEAD：`3b286cca94ad3a1683060d4df2a986a6f789236f`。本轮实际修改了 Runtime Python、既有 Skill、契约和测试；没有实施 A5、生成媒体或提交 git commit。此前未跟踪的 Face A3 与 `.DS_Store` 保留。

## 最终状态

```text
CINEMATOGRAPHY_A4_IMPLEMENTED = YES
FACE_A4_IMPLEMENTED = YES
REFERENCE_A4_IMPLEMENTED = YES
QC_A4_IMPLEMENTED = YES
READY_FOR_STILL_LIVEACTION_A5 = YES
```

这些状态限定于已批准 A3 的 **显式启用 STILL/LIVE_ACTION 路径**。不是宣称人脸或摄影效果已验证，不自动迁移旧 Work，也不授予 A5 生成预算。知识仍为 LOCAL_EXPERIMENTAL。真实人物 fixture、配对条件和媒体观察留给已经批准的两份 A5 设计。

已实现的主链：原 owner 的批准原件 → exact SourcePin/leaf → 确定性 mapping receipt → 既有 VisualPromptIR → 原 compile_ir/image_serializer → 原 adapter。新增源码中没有 provider 调用、prompt renderer、创作 agent 或 retry executor。

## Changed Runtime Files

路径相对 drama-plugin 仓库；完整改动清单见 [changed-files.json](evidence/changed-files.json)。共修改20个已有文件，新增4个源码/知识/文档/测试文件；其中7个 Python Runtime 文件发生新增或修改，绝非仅交付设计文档。

| File | Before responsibility | Change | After responsibility / why required |
|---|---|---|---|
| plugin/src/drama_plugin/contracts/specialized_asset.py | Work媒介/风格与资产契约 | D1 ImagingCharacterIntent、OpticalTextureIntent、可空imaging_character；仅省略新增空字段 | 仍是GlobalStyle边界；既有封闭枚举无法表示批准capture/optical选择 |
| plugin/src/drama_plugin/hosts/specialized_asset.py | typed资产与style保存/来源读取 | save_style校验D1来源/Work/medium/current；资产输入解析加载D1上游 | 仍沿既有Host存储，正式submit可解析新来源；无新存储架构 |
| plugin/src/drama_plugin/specialized_asset.py | 资产原件验证及sourceMap | 验证D1；GLOBAL_STYLE映射保留imagingCharacter；不支持该字段的旧provider projection明确拒绝 | 不把成像事实拼到资产prompt或默默忽略 |
| plugin/src/drama_plugin/professional.py | 专业registry与验证 | 仅existing global-visual-style增加imaging_character字段元数据 | 无新owner、DAG、能力或Director权限 |
| plugin/src/drama_plugin/visual/frame_request.py | FrameSpec与既有图像preflight | D2 professional_sources；空字段精确省略；非空检查正式IR/receipt locator/identity绑定 | 来源进入原fingerprint；旧请求原字节保持 |
| plugin/src/drama_plugin/visual/still_knowledge.py（新） | 原来无A3纯投影消费者 | 纯metadata模型、owner/leaf/scope验证、三种操作、IR投影、reference/coverage/replay、observation→Review | 一个共享确定性mapper；不创建事实或最终prompt |
| plugin/src/drama_plugin/visual/still_knowledge_catalog.json（新） | A3资料仅为NON_RUNTIME | 包装51项本地独立表达、外部commit/section、版本/hash/成熟度 | 可回放知识出处；不作为人物/场景事实源，不载入外部Skill |
| plugin/src/drama_plugin/hosts/route_production.py | 既有route/stage操作与支付前验证 | prepare_still_projection；reserve/begin-submission重开原件；普通QC sidecar转既有review payload | 路由、预算和状态机不变；真实current从读取的Work取，不信frame自报 |
| plugin/skills/cinematography/SKILL.md | Camera Bible作者 | 可读对象优先；视点/高度/光轴/距离分离；焦平面和lens意图 | 摄影做专业决定，mapper不补“cinematic polish” |
| plugin/skills/lighting-design/SKILL.md | Lighting作者 | 动机、方向/软硬、衰减、可读性；皮肤身份与反射分离 | 保留Lighting职责，无默认轮廓光/高光/瑕疵 |
| plugin/skills/color-design/SKILL.md | Color Script作者 | palette及肤色/材质保护，必要/可选目标分开 | required targets不得为短prompt随意省略 |
| plugin/skills/color-grading/SKILL.md | Grade作者 | capture边界、实际footage与设计目标区分 | 不以调色重写年龄、骨相或故事年代 |
| plugin/skills/specialized-asset-design/SKILL.md | 正式角色/服装/场景作者 | face/age/hair/baseline skin/marks语义；反刻板、未知和阶段界限 | 无Face新schema，资产仍唯一身份作者 |
| plugin/skills/performance-casting/SKILL.md | 候选测试与选角 | 结构差异证据、年龄线索限制；修正旧Character Art权威称谓为Specialized Asset兼容视图 | 不形成第二正式身份作者，不加差异数量阈值或美貌门槛 |
| plugin/skills/reference-strategy/SKILL.md | Reference Plan作者 | carry/exclude、可见性、canonical leaf引用、三图/实体绑定、coverage | 媒体不自动夺取表情/姿势/灯光权限 |
| plugin/skills/look-continuity/SKILL.md | 当前妆/伤/疲劳/毛发状态 | 明确baseline与current投影边界、阶段疤痕需资产重批 | 不把当前状态固化成身份，不注入统一瑕疵 |
| plugin/skills/blocking/SKILL.md | 站位、姿势、视线/接触关系 | 静帧当前关系与portrait职责分离 | reference pose不替代Blocking |
| plugin/skills/action-choreography/SKILL.md | 动作因果/力学 | 只投影当前body/contact截面 | 不吸收运镜、clip timing或Video能力 |
| plugin/skills/shot-production/SKILL.md | 既有生成/观察流程 | 接入共享mapper、source recheck、QC证据流程 | 无新prompt writer、自动retry或支付权 |
| plugin/skills/shot-production/references/production-rules.md | 既有用途审阅和reference规则 | 明确sequence lighting是独立连续性事实；细项观察和原Review处置 | 消除portrait继承light的歧义，保持MAJOR/MINOR/UNKNOWN语义 |

配套文件：`plugin/docs/still-professional-mapping.md`（新增，实际调用/profile说明）；`plugin/docs/professional-departments.md`、`plugin/docs/core-creative-r1.md`（现有文档接入）；`plugin/tests/test_still_knowledge.py`（新增32项离线用例）。没有新增顶级Runtime Skill。知识目录选择打包在Python包资源内，保证Host可加载；Skill通过文档链接引用同一目录，不另存第二份权威数据。

## Canonical Capabilities Implemented

| Group | 已批准范围 | Runtime落点与实际证据 |
|---|---|---|
| Cinematography | C02–C07、C09–C11、C13、C15、C17、C28、C30、C35、C36，共16项 | 既有skills语义；CAMERA/LIGHT owner-field映射；D1；色彩preserve/secondary；12个原设计QC维度。C35只约束实验设计，不新增生产次数规则 |
| Face Identity | 真实A2R的35项ADAPT，集合未扩充 | catalog精确allowlist；CharacterAsset既有text/reason/source_refs；face/skin/marks固定顺序JOIN，age/hair独立Fact；coverage仅引用批准叶；Casting差异指导及QC细分 |
| Reference Responsibility | C15、F23–25、F39及已有KEEP_LOCAL身份/状态边界 | selected媒体/版本/hash/slot/实体与actor绑定；carry种类与canonical资产匹配；must-not-carry；preservation_text必须投影；required覆盖不能标optional逃避消费 |
| Human Realism QC | 摄影12项与Face10项，REFERENCE-LEAKAGE共享，总计21个criterion key | Observation严格metadata，真实requirement来源验证，缺证据UNKNOWN，逐用途impact/hypothesis/confidence/单repair owner；投影既有Review/QA字段 |

Face allowlist和所有rule hashes由离线测试检查，未将KEEP_LOCAL、REFERENCE_ONLY或REJECT升级成新吸收能力。F17自然不对称、F19不减龄等既有原则继续继承；没有把毛孔、红眼圈、皱纹、灰尘等变成通用真人配方。

## Contract Delta 与消费边界

| Delta | Implemented | 兼容性、fingerprint、consumer |
|---|---|---|
| Cinematography D1 | YES | 缺省None从camel/snake dump精确省略。非空需要具体choice、reason、非空source pins；Host验证同Work的已批准来源与LIVE_ACTION。新style改变hash；asset review仍绑定其style pin。只在共享still mapper消费；旧asset/video projection明确报IMAGING_CHARACTER_REQUIRES_STILL_PROFESSIONAL_CONSUMER |
| Shared CINE_D2 | YES | FrameSpec.professional_sources空tuple不序列化；非空改变source fingerprint。包括原件和receipt pin，不能携带prompt/params。reserve和begin-submission重读Work current、原件和exact审批，重放IR与请求 |
| Face专用canonical字段 | NO，按A3要求不新增 | 现有CharacterAsset决定键、Reference开放values、覆盖索引足够；没有FaceRealismAsset/FaceDesign复活 |
| VisualPromptIR / Review新类型或状态 | NO，A3明确复用 | 现有Fact/subject/preserve和Review容器；新metadata在普通sidecar中，不改IR/Review schema |
| 新serializer/provider policy | NO，批准范围不需要 | image_serializer、prompt_ir、image_route和adapter保持原文件hash；adapter只接收现有编译结果 |
| 自动全局启用、迁移旧角色 | NO，设计规定opt-in | 未选择professional_sources的请求保留旧路径；没有默认成像/皮肤/脸部值注入 |

receipt先冻结，再bind D2，再计算FrameSpec source fingerprint，最后绑定IR；receipt自身不含FrameSpec/IR hash，避免循环。行保留source pins/pointer/operation/target/selected text hash/rule_refs；Fact.source精确指receipt行。正式compile_ir的retained/omitted和prompt fingerprint继续贯通请求。知识source与创作source在代码中分离；读取外部知识JSON不能生成一个人物事实。

静帧profile必须映射所有Fact，拒绝base IR中未绑定的旁路文本。复杂dict不能进入prompt。已批准的参考保留声明可以进入preserve；reason/criteria/evidence/provenance不进入provider。定向edit继续使用既有edit_delta/preserve及selector；required却被省略的字段明确阻断，不能把IR存在误报成实际消费。没有为本轮改变edit重述策略。

## Legacy Reconciliation

主动检索了generic cinematic、beauty/beautification、pores/wrinkles/asymmetry、reference pose/light inheritance及重复作者语言。

| Old rule / location | New authority | Decision | Runtime action |
|---|---|---|---|
| performance-casting入口称Character Art为稳定外观作者 | specialized-asset-design，Character Art只读forwarding | REMOVE旧歧义称谓 / KEEP现有兼容视图 | 原位修正文案，不新增作者或改变casting代码 |
| production-rules把Lighting列在Stable Facts中易混portrait身份 | Lighting独立sequence continuity | SEMANTIC_CLARIFICATION | 原位改为sequence lighting continuity，明确不从portrait继承 |
| legacy FrameSpec参考姿势文字在formal IR分支被替换 | Reference Plan approved duty→IR.preserve | KEEP legacy replay；新profile禁止依赖legacy文字代替职责 | 新路径必验duty实际映射和消费，未追加第二段prompt |
| 已有IDENTITY_WITHOUT_BEAUTIFICATION、PRESERVE_AUTHORED_IDENTITY、role salience | 原Asset/Casting/medium owner | KEEP_LOCAL | 不以外部默认美型覆盖；不改旧approved assets |
| 既有LIVE_ACTION皮肤/毛发/自然不对称语言 | 既有medium owner | KEEP_LOCAL，限定原路径 | visual_medium.py完全未改；新mapper只投影批准事实，没有新增imperfection模板 |
| “cinematic”等现有媒介/用途词 | 既有serializer/owner | KEEP；不做硬关键词删除 | 空泛创作要求回原作者具象化，mapper不润色；serializer未改 |
| 外部黄金比例、职业→脸、固定鼻红/眼纹、强制冷脸、外部prompt模板 | A2R排除裁决 | REJECT / REFERENCE_ONLY保持 | 未导入/注册/执行，无并行新旧规则 |
| 既有retry、预算、Review disposition | 既有Production | KEEP | 新QC只产观察和建议；MINOR+REGENERATE仍拒绝，未增加自动调用 |

没有发现需按“外部winner”删除的本地可执行美型函数。`DEPRECATE_AND_DISABLE runtime functions = []`，`removed runtime functions = []`；不为完成表格虚构旧规则冲突。Video/CG合法既有分支未被本轮改写。

## Tests 与 Runtime Evidence

运行器为现有 `/Users/zy/historical-plugin/drama-mcp-service/.venv/bin/python`；仓库自己的`.venv`没有pytest，未安装新依赖。以下pytest命令从repo root执行；mypy从plugin目录执行。没有收费生成，所有新增数据都是临时、明确标记的合成离线fixture。

| Command | Count / result | Evidence |
|---|---|---|
| `python -m pytest plugin/tests/test_still_knowledge.py -q` | **32 PASS** | [new tests](evidence/new-tests-final.log) |
| `python -m pytest plugin/tests/test_still_knowledge.py plugin/tests/test_specialized_asset.py plugin/tests/test_visual_prompt_ir.py plugin/tests/test_route_image_inputs.py plugin/tests/test_production_route.py -q` | **121 PASS** | [focused regression](evidence/focused-regression.log) |
| `python -m pytest plugin/tests -q` | **2636 PASS，2 FAIL**；两个为已存在Video断言问题 | [unfiltered regression](evidence/full-regression.log) |
| HEAD原始副本 `python -m pytest /tmp/still-a4-baseline-3b286cc/plugin/tests/test_architecture_authority.py -q` | **14 PASS，相同2 FAIL** | [baseline reproduction](evidence/baseline-architecture.log) |
| 最终重复全库（筛选未匹配，实际未排除测试；完整命令见[test-summary.json](evidence/test-summary.json)） | **2636 PASS，相同2 FAIL，0 deselected** | [final full regression](evidence/final-full-regression.log)；未改Video代码或旧测试来求绿 |
| `python -m mypy` 七个新增/修改Python文件 | **PASS，0 issues** | [mypy](evidence/mypy.log) |
| skill-creator `quick_validate.validate_skill` | **11个修改入口全部PASS** | [入口frontmatter/名称/脚手架检查](evidence/skill-validation.json)；不宣称艺术效果验证 |
| registry及受保护文件hash对比 | **PASS** | [architecture check](evidence/architecture-check.json) |
| `git diff --check` | **PASS** | 无空白错误；git stat/status另保留 |

两个基线失败均在`plugin/tests/test_architecture_authority.py`：`test_provider_prompt_is_exact_core_compilation`与`test_formal_http_compile_reserve_replays_receipt_without_media_or_auth_claim`，都为`KeyError: compiledBy`。通过`git archive HEAD`隔离副本复现，未修改该测试或Video编译器。它们使“全库完全绿色”这一说法不成立，但不是本轮引入的still Runtime阻断；本轮授权明确排除Video修复。

新增测试涵盖：高度/光轴/距离与镜头/焦平面传递、动机光、D1正式submit与拒绝静默遗漏、D2空值回放、年龄及肤况不自动变化、表情不成为身份、reference职责/slot/kind分离、缺来源/伪owner/错误Work或stage/metadata投影拒绝、receipt可重复、冻结后stale和IR篡改拒绝、两个支付前Host点实际调用resolver、缺媒体/缺reference证据UNKNOWN、MINOR不再生成、MAJOR单owner路由、QA无创作写入、当前默认GPT Image 2 adapter接收单serializer原文。

[offline-trace.json](evidence/offline-trace.json)保留一个真实执行了mapper/编译器/Host回放的**合成离线**来源行、retained/omitted、source/prompt fingerprints与adapter模型。它不是生成图片或已批准A5人物，provider_calls=0。

## Architectural Regression 与限制

- Registry仍为HISTORICAL **49**、LITERARY **47** 个部门，唯一元数据差异是既有GlobalStyle的D1字段。
- 顶级Runtime Skill仍为 **57**，新增 **0**；本轮修改11个既有Skill入口。
- 已核对52个受保护文件hash未变，包含Director、Provider相关、单serializer、image route、IR/Review原schema与存储实现；修改清单没有MCP/Service或Video/Seedance/Vidu代码。
- A3全部原件和之前审计保持不变；没有安装fal/genmedia、外部Skill或prompt bundle。
- 字段owner、批准状态、scope、hash、确定性消费可由代码验证；一段被人工错误标成STABLE_IDENTITY的自然语言是否真含表情，不由NLP猜测。语义审阅与实际媒体证据仍必需。当前实现也不声称自动判定“像CG”的像素分类器。
- A5仍需真实批准人物和镜头、冻结同provider/serializer/reference/参数的OLD/NEW配对，逐维记录效果，不能从32项代码测试升级为PLATFORM_VALIDATED。

## Mandatory Completion Check

实际运行并保留 [git diff --stat](evidence/git-diff-stat.txt)、[git status](evidence/git-status.txt)。注意`git diff --stat`不包含未跟踪新文件；[完整文件清单](evidence/changed-files.json)显式列出了新增mapper、catalog、测试与使用文档。最终校验摘要见 [completion-check.json](evidence/completion-check.json)。

本轮 **STOP AT A4**。0 paid generation，0 real image/video generation，0 provider route changes，0新顶级Skill，0第二final prompt writer。没有执行A5。
