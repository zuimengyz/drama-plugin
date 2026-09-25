# Prompt A3/A4 — Model Generator / Seedance Implementation Report

2026-09-26 · source HEAD `789ed88d895bee045f24cf4432971da8220e5310` · Runtime implementation · STOP AT A4

## Outcome / Generator Architecture

Seedance 2.0 standard / fast / mini 的实际 HTTP production 编译链已经是：

`approved VisualPromptIR → Seedance2PromptGenerator → coverage receipt / hard-limit gate → Seedance adapter exact transfer`。

route selection 结果不变。已批准切换模型时按 selected provider/model 派发，不能误用 ContinuityPack.primary_model。没有收费或真实媒体生成，没有安装用户提供的 Skill，也没有执行 A5。其它模型仅有明确的 RESERVED 插槽，原有生产逻辑不在本轮伪装为新 generator。

现有 Fact、VisualPromptIR、Temporal、VideoReference、ContinuityPack、CinematicShotSpec 和审批机制保留。共享 PromptAtom 是这些原件的投影与回执，不是 WorkMeaning2/第二 Canon。只有 source-approved facts 进入生成器；缺动作、表演、身份绑定、音频 source 或冲突 camera 返回 UNRESOLVED / 错误，不能自动补完。

原件与用户补传 Skill 的 SHA256 见 [source-freeze.json](evidence/source-freeze.json)。官方身份是用户提供的来源声明；模型效果最高仅 LOCAL_EXPERIMENTAL。原件里的“AI 导演”和操作指令作为被审阅材料，没有取得本地 Director 权限。

## Changed Runtime Files

以下清单包含新文件；`git diff --stat` 不显示未跟踪新增文件。逐文件 hash 见 [changed-files.json](evidence/changed-files.json)。

- `plugin/docs/model-prompt-generators.md`
- `plugin/src/drama_plugin/contracts/video.py`
- `plugin/src/drama_plugin/hosts/http_video.py`
- `plugin/src/drama_plugin/prompt_generators/__init__.py`
- `plugin/src/drama_plugin/prompt_generators/base.py`
- `plugin/src/drama_plugin/prompt_generators/contracts.py`
- `plugin/src/drama_plugin/prompt_generators/flux/README.md`
- `plugin/src/drama_plugin/prompt_generators/gpt_image_2/README.md`
- `plugin/src/drama_plugin/prompt_generators/kling/README.md`
- `plugin/src/drama_plugin/prompt_generators/minimax/README.md`
- `plugin/src/drama_plugin/prompt_generators/registry.py`
- `plugin/src/drama_plugin/prompt_generators/seedance_2/__init__.py`
- `plugin/src/drama_plugin/prompt_generators/seedance_2/canonical.py`
- `plugin/src/drama_plugin/prompt_generators/seedance_2/generator.py`
- `plugin/src/drama_plugin/prompt_generators/seedance_2/policy.json`
- `plugin/src/drama_plugin/prompt_generators/seedance_2/policy.py`
- `plugin/src/drama_plugin/prompt_generators/seedance_2_5/README.md`
- `plugin/src/drama_plugin/prompt_generators/vidu/README.md`
- `plugin/src/drama_plugin/prompt_generators/wan/README.md`
- `plugin/src/drama_plugin/providers/video/adapters.py`
- `plugin/src/drama_plugin/providers/video/base.py`
- `plugin/src/drama_plugin/visual/prompt_ir.py`
- `plugin/src/drama_plugin/visual/video_prompt.py`
- `plugin/tests/test_architecture_authority.py`
- `plugin/tests/test_authority_provider_separation.py`
- `plugin/tests/test_seedance_prompt_generator.py`

主要修改：`contracts/video.py` 增加可缺省且缺省不序列化的 reference binding、projection annotation；`visual/prompt_ir.py` 复用现有事实收集并派发 Seedance；`visual/video_prompt.py` 校验真实请求、reference、能力和来源；HTTP Host 对 frozen cinematic source 验证原文覆盖；adapter/base 仅传递实际 route 身份并 exact-transfer，没有任何附加 prompt 文案。无 MCP、Service、Storage、Director 或 provider registry 数据变更。

调用约定与 source gate 详见 [model-prompt-generators.md](../../../plugin/docs/model-prompt-generators.md)。

## Seedance Official Skill Assimilation Matrix

| Seedance official rule | Category | Local authority | Runtime disposition | Reason |
| --- | --- | --- | --- | --- |
| references — 引用语法（统一标准） | MODEL_POLICY_CANDIDATE | Reference Plan + validated inputs | ADOPT_AS_SEEDANCE_SYNTAX | Actual adapter input order determines per-kind tags; no asset IDs. |
| subjects — 引用语法（统一标准） | MODEL_POLICY_CANDIDATE | Character / Reference Plan | ADAPT | Stable canonical subject labels; binding only from reviewed reference duties. |
| task — 任务分类 | MODEL_POLICY_CANDIDATE | selected route / provider registry | KEEP_UPSTREAM | Typed route and provider capability decide mode; unsupported modes fail. |
| structure — Step 4：结构化重写输出 | MODEL_POLICY_CANDIDATE | approved clip beats | ADAPT | Space before ordered approved temporal facts; no new shots or mandatory tails. |
| camera — Step 3 / 一镜一运镜 | MODEL_POLICY_CANDIDATE | Cinematography | CONDITIONAL | Report declared conflicts to Camera; preserve explicitly approved compound motion. |
| time — 镜头顺序优先于绝对时间 | MODEL_POLICY_CANDIDATE | Temporal / Editorial | ADAPT | Order existing beats; preserve all authored durations/triggers verbatim. |
| emotion — 动作描述要求 | CANON_FACT | Performance / Action | KEEP_UPSTREAM | Observable carriers come from Performance/Action, never invented by translator. |
| quality — 画质包 | QUALITY_CANDIDATE | GlobalVisualStyle / Lighting / Color | DISABLED_PENDING_A5 | No unconditional adjectives; approved IR medium/light/color remain exact. |
| stability — 稳定包 | QUALITY_CANDIDATE | identity / contact / continuity owners | ADAPT | Only existing identity/contact/continuity obligations; scoped semantic dedup. |
| subtitle — 字幕兜底 | UNVALIDATED_DEFAULT | scoped Work constraint | DISABLED_PENDING_A5 | Only explicit scoped canonical constraints; no universal no-text tail. |
| watermark_logo — 水印 / Logo 兜底 | UNVALIDATED_DEFAULT | API parameter / scoped Work constraint | DISABLED_PENDING_A5 | Existing watermark API field stays structured; no generic logo prohibition. |
| twins — 双胞胎兜底 | UNVALIDATED_DEFAULT | Reference / A5 evidence | DISABLED_PENDING_A5 | No unconditional duplicate-person text; A5 must assess contextual value. |
| face — 人脸参考最佳实践 | MODEL_POLICY_CANDIDATE | Reference Strategy | KEEP_UPSTREAM | Reference owner chooses media; portrait cannot inherit pose/light. |
| audio — 音频通道 / 特殊字符规范 | MODEL_POLICY_CANDIDATE | Dialogue / Audio owners | CONDITIONAL | Exact approved audio leaf plus speaker/language metadata; no dialogue rewriting. |
| homophones — 中文发音兜底 | UNVALIDATED_DEFAULT | exact approved Dialogue | REJECT | Changing approved dialogue is forbidden; no pronunciation substitution. |
| completion — 3.2 非关键缺失 / 自动补全 | UNVALIDATED_DEFAULT | original professional owner | REJECT | Missing action, identity, camera, reference duty returns to professional owner. |
| director — 角色定位 | CANON_FACT | Director | REJECT | Generator is a translator, never a Director. |

## Rules Adopted

- `@图片N/@视频N/@音频N` 按真正 API inputs 的每种 media 出现顺序编号。
- 同 canonical actor 稳定 `<主体N>`；原始 ID / 来源 / policy 不进入 prompt。
- 音频括号形式只用于有 exact source / hash / speaker / language 的批准 IR 音频叶。

## Rules Adapted

- SPACE/TIME 作为内部组织：静态与引用在前，现有 temporal facts 在后，不输出空间层/时间层标题。
- Path A 是一段；多 approved action beats 用换行和事件次序，不创造新镜头，不强制三段模板或固定尾巴。
- 镜头顺序语言保留原时间和触发条件，绝对时长不删除。
- 稳定性仅由已有 identity/contact/continuity 义务表达。reference 减述必须有 reviewed leaf coverage。
- camera conflict 报回摄影；明确批准的 compound source 原样保留，不擅选一镜一运镜。

## Rules Rejected

拒绝导演角色接管、默认低缓小动作、推断环境/风格、情绪→发明动作、默认拆镜头、同音字改对白、复制整份模板、依据 Skill 擅改 reference 配置。source 原文不满足要求时返回原 owner，不发可执行 prompt。

## Rules Disabled Pending Validation

Quality、subtitle、watermark/Logo 文本包、twin 默认包全部 DISABLED_PENDING_A5。Stability 不作为固定包；只投影已有批准约束。API 原有 `watermark=False` 保持为结构参数。人物数量/重复人风险没有 A5 证据，不自动触发 twin 文案。没有随机高清/电影质感/柔光尾巴。

## Seedance Supported Modes

实际 registry 三个 Seedance 2.0 型号均支持 T2V、I2V、FIRST_LAST、MULTI_REFERENCE，provider hard limit 均为 5000 characters。沿用已有 native audio 能力。VIDEO_EDIT/VIDEO_EXTEND 未接入，明确拒绝；Seedance 2.5 Comfy 路线属于已有独立 legacy family，不冒充 2.0。

T2V 保留全部 required static facts。I2V 仅减去经过职责/源/hash核验的 face 等叶。首尾帧仍保留起态、终态、批准过程和跨过程接触/身份/服装保护，不能拿两个 endpoint 代替全程义务。

## Semantic Coverage Implementation

每个 required executable IR leaf 有且仅有一个 coverage receipt，含 span offset；reference coverage 另含 tag、content hash、version、duty。重复源义务可以共享同一语义 span，但各自仍有回执。当前使用 TEXT_COVERED / REFERENCE_COVERED；MEDIA_COVERED 是共享扩展类型，本轮没有虚构 video/audio 全义务替代能力。

reference coverage 保存在既有 Canon VideoReference 中，request 必须与 Canon 完全相等；Host 重新读取 ContinuityPack，媒体在提交前复核身份/hash。覆盖声称还必须匹配 IR path、Fact.source、完整 text hash、subject、参考种类和 duty allowlist。face/costume/scene 独立；不能用 portrait 覆盖 pose、light、contact、direction 或 temporal/end-state。未提供覆盖证明时保留文字；无效/重复覆盖声明报错。

approved dialogue 使用 exact leaf，无同音字替换，无总结/拼接/润色；cinematic source gate 额外核对原 Dialogue 的 speaker、text、interval 和数量。Host source gate 核验 approved timed beats、endpoint、visual/camera/light/stability 等 source sections 和 required references。缺少 source→IR 对应不会退回 generic。

## Semantic Dedup Implementation

比较 scope（含 CURRENT/CLIP）、owner、subject、target、完整 relation/action/state、temporal phase、negation 和 reference duty，并要求完整文字一致。自由文本的施受关系与否定保留在不可拆命题中，不假装拥有自然语言实体解析器；无法确认 KEEP。仅相似文字、相反抓取方向、未转身/已转身、左右、开场/终态、同一身份/两个主体均不得合并。每条 source locator 留在 atom；不同 source 的真正同义义务可共享 span。

## Budget / Distillation Behavior

先排除来源性非投影材料和既有非当前 scope，再做 scoped exact semantic dedup、移除通用路径/priority 标签并采用职责语法、仅在超硬限时删掉 explicitly optional SECONDARY。CRITICAL/IMPORTANT 不删除、不按字符裁切；required SUPPORTING 也不静默删。没有经过批准的短释义时保留原文；structural compression 后仍超 hard limit 返回 planning。不存在自动同义改写模型。Soft budget 为 UNVALIDATED，未定词数/字符经验目标。

## Legacy Reconciliation

| Existing path | Disposition |
| --- | --- |
| generic VIDEO rows → Seedance 2.0 HTTP | 新生产由 generator 取代；没有 fallback |
| no-IR Seedance prompt + canonical JSON | 新生产拒绝；不能凭 legacy prompt 提交 |
| `compile_ir(..., legacy_replay=True)` | 仅显式历史/offline对照；submission 重新编译并拒绝 generic receipt |
| HTTP frozen CinematicShotSpec → generic OfficialHTTP projection | Seedance 分支改为 canonical source verification + 同一个 generator；不形成第二 final prompt |
| provider prompt enhancement | Seedance 没有新增；adapter 仅 schema/model/slots/transport；exact transfer 测试 |
| Seedance 2.5 Comfy、Vidu、其它模型 serializer | 保留原路线；不是 Seedance 2.0 的 fallback |
| 两个旧 `compiledBy` 测试断言 | 更新为真实 IR schema、Seedance family 与 coverage；之前 A4 已记录其为基线错误 |

## Reserved Model Folders

`gpt_image_2`, `vidu`, `flux`, `minimax`, `wan`, `kling`, `seedance_2_5`。来自当前 image route / official video registry / legacy_model_keys 与实际 Comfy 注册。目录仅 README：RESERVED / NOT_IMPLEMENTED / NO_RUNTIME_DISPATCH。registry readiness=false，不提供 fake generator，不注册其它模型新 dispatcher。

## Tests

新增 `test_seedance_prompt_generator.py` 57 项离线测试（含 CURRENT 不能扩为全程、原文开场时间不得误删）；涵盖四模式、三型号、reserved拒绝、immutability、coverage replay、reference duty/hash/actor校验、input顺序、稳定主体、首尾保护、各类语义反例、scoped dedup、budget、缺动作/抽象表演、camera冲突、精确 audio、默认包缺省、internal ID、无 generic fallback、实际 adapter exact transfer、selected route 派发、frozen cinematic Host source gate。

第一轮完整测试：2689 PASS（当时51项新测试）。最终断网全库 **2695 PASS**，最终定向 **139 PASS**，mypy **14 source files / 0 issues**。完整证据见 [final-full-tests.log](evidence/final-full-tests.log)、[mypy.log](evidence/mypy.log)。最终回归加载 [offline_guard.py](evidence/offline_guard.py)，禁止 Python 测试进程真实 INET socket；provider生命周期只用 MockTransport。模型质量没有因此升级。资产隔离测试原先使用 SimpleNamespace 伪 adapter，已改用真实 SeedanceProvider + MockTransport，保留原权限/污染断言，并增加 exact-transfer 和 no-IR 拒绝断言。

## Offline Prompt Before/After

四例为明确的合成离线 fixture，不是已批准作品或媒体验证。OLD 使用同一 raw IR 的原 generic VIDEO serializer，NEW 使用新 generator；参数/义务相同，只在 Canon reference 中声明允许覆盖的叶。

| Mode | chars before | chars after | obligations total | text-covered | reference-covered | omitted optional | uncovered required | semantic duplicate count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| text_to_video | 2016 | 922 | 37 | 37 | 0 | 0 | 0 | 0 |
| image_to_video | 2016 | 1003 | 37 | 36 | 1 | 0 | 0 | 0 |
| first_last_frame | 2016 | 1079 | 37 | 35 | 2 | 0 | 0 | 0 |
| reference | 2016 | 1124 | 37 | 34 | 3 | 0 | 0 | 0 |

完整旧/新文字、coverage spans 和 input slots 见 [offline-comparison.json](evidence/offline-comparison.json)，可由 [offline_comparison.py](evidence/offline_comparison.py) 确定性重放。多参考模式的职责限制会增加必要文字；“更短”不自动代表 PASS。例子没有人为制造重复以夸大长度收益；去重能力由独立反例/重复测试证明。

## Known Gaps

- 全部模型策略最高 LOCAL_EXPERIMENTAL；尚无真实 Seedance 图像/视频 A/B，不能宣称生成质量、身份准确度或节省收费调用已经验证。
- 自由 prose 没有通用语义解析/蕴含证明。完整命题和 conservative KEEP 防止编译阶段反转，但原作者错误标注或媒体 reviewer 错误判断仍要由专业审批与 A5 发现。
- 只有明确 review 的 image duty 叶能减述。视频运动/音色 reference 会表达职责，但本轮不借此删除动态、对白或语音义务。也不自动从 face ref 推断年龄/皮肤等未单独证明的事实。
- 新 source annotations 必须来自批准源；历史 reference 未带 coverage 时保留文本。human identity reference 没有 subject binding 会返回 Reference Strategy；不会猜编号或人物。
- Camera冲突/抽象情绪的文字诊断是窄诊断，加上显式冲突字段；不是任意自然语言的完整冲突检测器。
- 严格 cinematic source gate 要求 owner 在现有 IR 保留完整 source sections 与时序。不能自动迁移一份缺失映射的旧 IR；它会 fail closed。
- 无 subtitle/title专属新 projection，也无独立 pronunciation policy；无 edit/extend runtime。将来的短释义与支持性 prose 压缩需审批/验证，不在此轮编造。

## Mandatory Final Status

```text
MODEL_PROMPT_GENERATOR_ARCHITECTURE_IMPLEMENTED = YES
SEEDANCE2_PROMPT_GENERATOR_IMPLEMENTED = YES
SEEDANCE2_OFFICIAL_SKILL_ASSIMILATED = YES
SEEDANCE2_FORMAL_ROUTE_USES_GENERATOR = YES
SEMANTIC_COVERAGE_IMPLEMENTED = YES
SEMANTIC_DISTILLATION_IMPLEMENTED = YES
RESERVED_MODEL_FOLDERS_CREATED = YES
ADAPTER_REMAINS_NON_CREATIVE = YES
PAID_GENERATION = 0
READY_FOR_SEEDANCE_PROMPT_A5 = YES
```

READY 表示代码/离线门禁可进入下一轮受控验证，不是授权执行 A5。本轮 STOP。
