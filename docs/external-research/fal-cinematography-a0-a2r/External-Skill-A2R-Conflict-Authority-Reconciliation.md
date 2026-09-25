# External Skill A2R — Conflict & Authority Reconciliation

**READY_FOR_A3 = YES（仅限下述最小 Canonical Contract Design；本轮 STOP，未执行 A3/A4）。**

本轮已经知道哪些是值得研究的摄影知识、哪些是 fal execution、哪些与本地职责冲突，以及每项的明确归属。外部专业知识总体为 EXTERNAL_CANDIDATE，不能宣称已“经过实产验证并正式吸收”。41 项能力逐项处置；25 条裁决全部 `RESOLVED_FOR_A2R`。没有未裁决的 same-scope authority conflict。

## 裁决原则与证据责任

1. Level 1：显式环境、单一 IR、route/MCP、source map、Storage、生产门等平台合同最高；外部不能覆盖。
2. Level 2：原著/历史/批准视觉媒介、角色/剧情/表演/构图事实不能被通用摄影配方重新发明。
3. Level 3：若同 capability、modality、provider/transport、medium、task、stage 有可信外部验证，且本地弱验证，默认 EXTERNAL WINS，并移除 loser 的执行权。**本轮没有满足这一门槛的条目**；不把开源标签和 examples 伪装为 Level 3。
4. Level 4：仅真实同范围实产特化证据可建立本地专业优先。本轮未建立该证据；127 项离线测试不用于宣称本地摄影效果优越。
5. Level 5：双方效果证据弱时，弱外部规则不得升级为强制全局权威。保留当前显式执行合同；吸收知识只能作为原 owner 的候选方法。未知优劣不等于权限归属未裁决。

`same_scope=false` 的规则各自留在原精确范围，结论必须是 `COEXIST_IN_SEPARATE_SCOPE`。`same_scope=true` 表示在输入创作/平台决策边界上确实竞争，执行工具的差异不会豁免越权。F21 是导入时可能把可选词汇强制化的风险，明确不伪造原文要求。

## CONFLICT_MATRIX

| ID | Capability | External Rule | Local Rule | Scope | External Evidence | Local Evidence | Winner | Future Action |
|---|---|---|---|---|---|---|---|---|
| F01 | C12, C29 | 外部领域 Skill 直接持有最终 prompt；具体模型上的模板竞争另见 F16。 | 正式静态请求只有 IR→compiler→serializer 一套可重放 final prompt。 | still/provider-neutral/LIVE_ACTION/film still/compilation; same=true | 候选源码；见下方 pins；无同范围实产评测 | test_visual_prompt_ir.py；deterministic，不证明照片真实; test_image_serializer.py：顺序/遗漏/identity/预算；非 provider A/B | L11/L12 | REJECT 外部 final writer；模板仅 REFERENCE_ONLY。A3 若论证 provider-specific serializer，只允许同一 compiler dispatch 一个 policy。 |
| F02 | C09, C10, C13 | 外部 cinematography 同时定灯光、颜色、环境细节。 | 各专业 owner 写原件，Camera 不能补缺别的部门。 | still/provider-neutral/LIVE_ACTION/film still/design; same=true | 候选源码；见下方 pins；无同范围实产评测 | 声明＋registry 字段；没有本轮可归因实拍 A/B; 部门归属测试；艺术效果未证实; 部门归属测试；非 provider 性能证明; test_specialized_asset.py：旧 writer 拒绝、source replay、审批绑定 | L20 department partition | 拆 K 为 Camera/Lighting/Color/Asset 候选；不建立 all-in-one 摄影写手。 |
| F03 | C01, C15, C39 | 每次角色/摄影任务收集 style/medium，缺少 capture era 填 phone/mirrorless。 | Work movie medium 由配置 pin，approved GlobalStyle 决定渲染边界。 | still/provider-neutral/LIVE_ACTION/film still/design; same=true | 候选源码；见下方 pins；无同范围实产评测 | test_specialized_asset.py：env pin、跨 Work、medium override | L03 | REJECT 自动 medium/default 注入；任务类型仍保留于 IR.task。 |
| F04 | C22, C25 | 摄影指定 endpoint 回退；genmedia 根据 prompt smart route。 | 正式 frame 当前 GPT Image 2 Comfy，密封 route 后不允许改 backend/model。 | still/provider-neutral/LIVE_ACTION/film still/qualification; same=true | 候选源码；见下方 pins；无同范围实产评测 | test_hero_vidu_routes.py、test_route_image_inputs.py；未实时重新连 Provider; 源码边界；不在本轮调用运行服务 | L13/L15 | REJECT 外部 endpoint defaults/smart fallback；保留当期 route，不安装 genmedia。 |
| F05 | C24, C25 | 由 genmedia 安装、run、status、download 管执行。 | Host/MCP、预约、异步恢复与 Media persistence 各有合同。 | still/provider-neutral/LIVE_ACTION/film still/execution; same=true | 候选源码；见下方 pins；无同范围实产评测 | 源码边界；不在本轮调用运行服务; 源码和 selected tests；无新媒体语义 PASS; 源码与 shot-production durable completion；本轮未访问 Media | L15/L17/L18 | REJECT R；下载结果不得绕过 formal Media。 |
| F06 | C21 | fal edit 支持 16 references 与 mask 参数。 | 本地 Comfy frame 只接受已核准三 references；没有 mask edit 控制。 | still/Comfy/OpenAIGPTImageNodeV2/LIVE_ACTION/film still/payload; same=false | 候选源码；见下方 pins；无同范围实产评测 | test_hero_vidu_routes.py、test_route_image_inputs.py；未实时重新连 Provider; frame input、source mismatch、slot wiring tests | fal schema in fal scope; local adapter in Comfy scope | PROVIDER_SCOPE_ONLY；本地扩容不在本轮。纠正指南参数需现行 schema，不直接继承 mask_image_url/input_fidelity。 |
| F07 | C16 | realism recipe 的 reference edit 不重述面部。 | edit serializer 保留 role/face/costume，省略其它旧外观细节。 | still/Comfy GPT Image 2/LIVE_ACTION/identity-preserving image edit/serialization; same=false | 候选源码；见下方 pins；无同范围实产评测 | test_image_serializer.py：顺序/遗漏/identity/预算；非 provider A/B; frame input、source mismatch、slot wiring tests | L12 for current route; external recipe REFERENCE_ONLY | KEEP_LOCAL 当前执行；未来如有同路线控制对照，再裁决 face policy，禁止两个 prompt 同时发出。 |
| F08 | C31 | 泛写实规则要求添加毛孔、红眼、灰尘及二三个瑕疵。 | 已批准身份/外观/状态不能被 compiler 新增；可见缺陷按实际用途判定。 | still/provider-neutral/LIVE_ACTION/film still/design; same=true | 候选源码；见下方 pins；无同范围实产评测 | test_specialized_asset.py：旧 writer 拒绝、source replay、审批绑定; test_specialized_asset.py：env pin、跨 Work、medium override; 规范＋production.py；不把测试视为审美有效性 | Approved asset/style (L02/L03) | REJECT 强制清单；可选材质/光学观察经 owner 认可后归 C11/C28，不附加到 prompt。 |
| F09 | C32 | 将 dead-center、对称构图、正视视线、无动作视为 AI tells。 | 当前批准构图/视线/静止可有明确戏剧目的。 | still/provider-neutral/LIVE_ACTION/film still/design; same=true | 候选源码；见下方 pins；无同范围实产评测 | 声明＋registry 字段；没有本轮可归因实拍 A/B; 部门边界与连续性测试; 部门边界测试；不等于作品审美验证 | Approved Camera/Blocking/Director facts | REJECT universal gate；candid 场景选项仅留 REFERENCE_ONLY，不自动改 approved shot。 |
| F10 | C33 | documentary 子类型只用场景光、禁 fill。 | 电影动机光允许符合来源和可读性的补光。 | still/provider-neutral/LIVE_ACTION/film still/design; same=false | 候选源码；见下方 pins；无同范围实产评测 | 部门归属测试；艺术效果未证实 | L05 for film; reference-only documentary preference | REFERENCE_ONLY 类型建议；不得定义全局 no-fill 或强制 mixed-temperature。 |
| F11 | C34 | 写实生成 2–4 variants 选优、固定 seed。 | 正式 frame n=1；逐请求预约/观察；未知创建不能再提交。 | still/provider-neutral/LIVE_ACTION/film still/production; same=true | 候选源码；见下方 pins；无同范围实产评测 | test_hero_vidu_routes.py、test_route_image_inputs.py；未实时重新连 Provider; 源码和 selected tests；无新媒体语义 PASS | L13/L17 | REJECT 默认批量；未来任何不同 batch 策略须独立平台授权；当前保持 n=1。 |
| F12 | C17, C36 | 对漂移/手或 prop 干扰直接 reject or retry；generic 就加强细节。 | 观察→明确约束→用途严重度；轻微不妨碍用途的差异不能自动失败。 | still/provider-neutral/LIVE_ACTION/film still/observed review; same=true | 候选源码；见下方 pins；无同范围实产评测 | 源码和 selected tests；无新媒体语义 PASS; 规范＋production.py；不把测试视为审美有效性 | L17/L21 review contract | C17/C36 指标进入原 gate 候选；删除自动 rerun implication，保留 UNKNOWN 和 user adoption 分离。 |
| F13 | C14, C08 | video camera moves/rack focus；still 可表现 motion blur。 | still 只能 CURRENT 静态目标，禁止 temporal progression。 | still/provider-neutral/LIVE_ACTION/film still/design; same=false | 候选源码；见下方 pins；无同范围实产评测 | test_visual_prompt_ir.py；deterministic，不证明照片真实; frame input、source mismatch、slot wiring tests | L11 static scope; video owners outside round | KEEP_LOCAL 静态边界；C08 FUTURE_VIDEO_ROUND，不迁移 Seedance/Vidu 控制。 |
| F14 | C26, C27 | 优先 approved still→I2V；模型支持 multi-prompt 时允许多镜头。 | coverage 从戏剧出发、输入 duties 由 qualified route 产生；没有普遍 still-first。 | video/provider-neutral/LIVE_ACTION/film still/planning; same=true | 候选源码；见下方 pins；无同范围实产评测 | thin assembly 与 dependency tests; 本轮只定位；video 正式吸收排除; 规范＋production.py；不把测试视为审美有效性 | L09/L16/L21 | FUTURE_VIDEO_ROUND；不得新增镜头/提前生成全部 keyframes。 |
| F15 | C15, C20 | 把整体 anchor（含 posture/style）重复并继承 reference。 | 身份参考只绑定身份，当前姿势/视线/位置来自 Shot/Blocking。 | still/provider-neutral/LIVE_ACTION/film still/reference projection; same=true | 候选源码；见下方 pins；无同范围实产评测 | test_specialized_asset.py：旧 writer 拒绝、source replay、审批绑定; 部门边界与连续性测试; frame input、source mismatch、slot wiring tests | L02 stable identity; L08 current state; L14 slots | 保留 anchor/variable 思路；把各变量交还原 owner；禁止 reference pose 默认迁移。 |
| F16 | C12, C18, C29 | SCLCAM subject-first；GPT 五段 scene-first；realism 六段禁止重排。 | 一个静态 serializer 负责实际顺序，不按 load 次序决定。 | still/GPT Image 2 family/LIVE_ACTION/film still/serialization; same=true | 候选源码；见下方 pins；无同范围实产评测 | test_image_serializer.py：顺序/遗漏/identity/预算；非 provider A/B | L12 current; no external ordering winner | 三模板仅 reference；不将任一绝对顺序提升为 Canonical。未来验证胜者必须替换原 serializer policy，而非追加模板。 |
| F17 | C22, C25 | model-routing 要 endpoint-first；较新 genmedia 对默认质量要求 smart routing。 | 平台 route 显式密封，不运行 genmedia。 | still/provider-neutral/LIVE_ACTION/film still/routing; same=true | 候选源码；见下方 pins；无同范围实产评测 | test_hero_vidu_routes.py、test_route_image_inputs.py；未实时重新连 Provider; 源码边界；不在本轮调用运行服务 | L13/L15 | 两类外部路由均不得入本地 Runtime；若未来评估 genmedia 则单独核实版本和优先规则。 |
| F18 | C24 | 下载路径/request id 即可交付。 | Media 要 readback bytes/hash、ownership、stable business binding。 | still/provider-neutral/LIVE_ACTION/film still/delivery; same=true | 候选源码；见下方 pins；无同范围实产评测 | 源码与 shot-production durable completion；本轮未访问 Media | L18 | REJECT downloaded-path-as-completion；任何未来 provider 结果仍由现有 completion entry 落库。 |
| F19 | C35 | 每 turn 只改一项。 | 允许同一批准目标下最小可用修复并保留成本/策略；一组相关修复可同时必要。 | still/provider-neutral/LIVE_ACTION/film still/rework; same=true | 候选源码；见下方 pins；无同范围实产评测 | 规范＋production.py；不把测试视为审美有效性 | L21 for production; controlled-variable rule for experiment | 只采用实验设计的单变量原则；不添加用户交互次数/固定重试上限。 |
| F20 | C40 | 失败就用真实 reference photo/edit mode。 | 稳定 approved reference、身份权属、qualified route 及预算必须满足。 | still/provider-neutral/LIVE_ACTION/film still/rework; same=true | 候选源码；见下方 pins；无同范围实产评测 | test_specialized_asset.py：旧 writer 拒绝、source replay、审批绑定; frame input、source mismatch、slot wiring tests; 规范＋production.py；不把测试视为审美有效性 | L02/L14/L21 | KEEP_LOCAL；仅把诊断退回 reference-strategy/asset owner，未许可不执行切换。 |
| F21 | C06 | 焦段列表经常绑定固定题材/人物效果。 | 从距离、空间和观众需求确定 lens intention，避免无依据数值。 | still/provider-neutral/LIVE_ACTION/film still/design; same=true | 候选源码；见下方 pins；无同范围实产评测 | 声明＋registry 字段；没有本轮可归因实拍 A/B | L04 as owner; external vocabulary is optional knowledge | 允许词汇充实；REJECT 自动题材→焦段与精确控制承诺；不替换 Camera owner。 |
| F22 | C10 | 同一 cinematic prompt 混合 palette、exposure style 与 final grade。 | 色彩发展、灯光因果、最终匹配各有原件和阶段。 | still/provider-neutral/LIVE_ACTION/film still/design; same=true | 候选源码；见下方 pins；无同范围实产评测 | 部门归属测试；非 provider 性能证明; 声明；本轮无画面调色观察; 部门归属测试；艺术效果未证实 | L06/L07/L05 partition | 意图分配给已存在 owner；不让 adapter LUT/调色重写场景事实。 |
| F23 | C31, C30 | 写实指南给 phone/film/年代组合及身体细节近似普遍摄影真理。 | 批准 medium、风格、角色和时代事实逐作品约束；CG 不接受 live-action pores 默认。 | still/provider-neutral/CG/film still/design; same=false | 候选源码；见下方 pins；无同范围实产评测 | test_specialized_asset.py：env pin、跨 Work、medium override; test_specialized_asset.py：旧 writer 拒绝、source replay、审批绑定 | L03 medium separation | 所有 K/Q 标明 LIVE_ACTION/still/task，不能进入 CG 全局 policy。 |
| F24 | C12, C21 | 把 aspect、duration、模型控制拼进领域 Prompt。 | structured execution fields 属于 adapter；STATIC 不含视频 duration。 | still/provider-neutral/LIVE_ACTION/film still/payload; same=true | 候选源码；见下方 pins；无同范围实产评测 | test_visual_prompt_ir.py；deterministic，不证明照片真实; test_hero_vidu_routes.py、test_route_image_inputs.py；未实时重新连 Provider | L11/L13 | REJECT prompt-owned execution controls；payload 单一字段 authority，当前 runtime 不变。 |
| F25 | C41 | 外部 structured prompt 的 Constraints 可直接使用否定句；专用 negative 字段需要 schema 支持。 | 本地 IR 保留 negative constraint，正式非 edit 约束输出作者显式提供的 positive_target；edit 的 remove/replace/correct 原样保留。 | still/GPT Image 2 family/LIVE_ACTION/film still/serialization; same=true | 候选源码；见下方 pins；无同范围实产评测 | test_visual_prompt_ir.py；deterministic，不证明照片真实; test_image_serializer.py：顺序/遗漏/identity/预算；非 provider A/B | L11/L12 current policy | REJECT 将外部 negative 模板追加到现有 prompt；任何未来胜出策略仅由同一 serializer 切换并停用旧策略，原 constraint/source 仍在 IR。 |

## 精确 Conflict Records

完整结构亦保留于 [conflicts.json](evidence/conflicts.json)。每条列出六维 scope、源 commit/file/section、双方 validation、winner/reason/future action。

### F01

```json
{
  "conflict_id": "F01",
  "capability": [
    "C12",
    "C29"
  ],
  "conflict_type": "PROMPT_CONFLICT / OWNERSHIP_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "## Prompt build order",
        "line": 94,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L94"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "## Prompt build order",
        "line": 72,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L72"
      }
    ],
    "rule": "外部领域 Skill 直接持有最终 prompt；具体模型上的模板竞争另见 F16。",
    "scope": {
      "capability": "final prompt ownership",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "compilation"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/prompt_ir.py",
        "symbol_or_section": "def compile_ir",
        "line": 12,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/image_serializer.py",
        "symbol_or_section": "def render_image",
        "line": 27,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "正式静态请求只有 IR→compiler→serializer 一套可重放 final prompt。",
    "scope": {
      "capability": "final prompt ownership",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "compilation"
    },
    "validation": "test_visual_prompt_ir.py；deterministic，不证明照片真实; test_image_serializer.py：顺序/遗漏/identity/预算；非 provider A/B"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "KEEP_LOCAL",
  "winner": "L11/L12",
  "reason": "平台单一编译/校验合同不能被自由拼接的外部模板覆盖；没有证据要求替换本地顺序。",
  "future_action": "REJECT 外部 final writer；模板仅 REFERENCE_ONLY。A3 若论证 provider-specific serializer，只允许同一 compiler dispatch 一个 policy。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F02

```json
{
  "conflict_id": "F02",
  "capability": [
    "C09",
    "C10",
    "C13"
  ],
  "conflict_type": "AUTHORITY_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/references/lighting-lens-color.md",
        "section": "## Lighting setups",
        "line": 3,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L3"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/references/lighting-lens-color.md",
        "section": "## Color and grade",
        "line": 32,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L32"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "If a result looks generic",
        "line": 144,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L144"
      }
    ],
    "rule": "外部 cinematography 同时定灯光、颜色、环境细节。",
    "scope": {
      "capability": "professional decision ownership",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/skills/cinematography/SKILL.md",
        "symbol_or_section": "## Professional decisions",
        "line": 20,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/lighting-design/SKILL.md",
        "symbol_or_section": "## Professional decisions",
        "line": 20,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/color-design/SKILL.md",
        "symbol_or_section": "## Professional decisions",
        "line": 20,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/specialized_asset.py",
        "symbol_or_section": "FORWARDED_DEPARTMENTS",
        "line": 12,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "各专业 owner 写原件，Camera 不能补缺别的部门。",
    "scope": {
      "capability": "professional decision ownership",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "声明＋registry 字段；没有本轮可归因实拍 A/B; 部门归属测试；艺术效果未证实; 部门归属测试；非 provider 性能证明; test_specialized_asset.py：旧 writer 拒绝、source replay、审批绑定"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "ADAPT",
  "winner": "L20 department partition",
  "reason": "Level 1 约束的是职责；不排斥把更好知识交给相应 owner。",
  "future_action": "拆 K 为 Camera/Lighting/Color/Asset 候选；不建立 all-in-one 摄影写手。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F03

```json
{
  "conflict_id": "F03",
  "capability": [
    "C01",
    "C15",
    "C39"
  ],
  "conflict_type": "AUTHORITY_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "## Inputs to collect",
        "line": 22,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L22"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/character-design/references/anchor-system.md",
        "section": "## Anchor fields",
        "line": 6,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "If the brief does not name an era",
        "line": 232,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L232"
      }
    ],
    "rule": "每次角色/摄影任务收集 style/medium，缺少 capture era 填 phone/mirrorless。",
    "scope": {
      "capability": "visual medium/style selection",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/hosts/specialized_asset.py",
        "symbol_or_section": "def bind_movie",
        "line": 19,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "Work movie medium 由配置 pin，approved GlobalStyle 决定渲染边界。",
    "scope": {
      "capability": "visual medium/style selection",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "test_specialized_asset.py：env pin、跨 Work、medium override"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "KEEP_LOCAL",
  "winner": "L03",
  "reason": "外部 still/video/edit 是任务轴；不得混为 medium；隐式 default 不能覆盖明确配置/批准事实。",
  "future_action": "REJECT 自动 medium/default 注入；任务类型仍保留于 IR.task。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F04

```json
{
  "conflict_id": "F04",
  "capability": [
    "C22",
    "C25"
  ],
  "conflict_type": "PROVIDER_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "## Model routing",
        "line": 114,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L114"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/genmedia/SKILL.md",
        "section": "## Critical rules",
        "line": 19,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/genmedia/SKILL.md#L19"
      }
    ],
    "rule": "摄影指定 endpoint 回退；genmedia 根据 prompt smart route。",
    "scope": {
      "capability": "route ownership",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "qualification"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/image_route.py",
        "symbol_or_section": "def select_frame_template",
        "line": 11,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/execution.py",
        "symbol_or_section": "def require_execution",
        "line": 36,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "正式 frame 当前 GPT Image 2 Comfy，密封 route 后不允许改 backend/model。",
    "scope": {
      "capability": "route ownership",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "qualification"
    },
    "validation": "test_hero_vidu_routes.py、test_route_image_inputs.py；未实时重新连 Provider; 源码边界；不在本轮调用运行服务"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "KEEP_LOCAL",
  "winner": "L13/L15",
  "reason": "Level 1 route 是 explicit platform contract；外部质量排名无基准且不能授权新 transport。",
  "future_action": "REJECT 外部 endpoint defaults/smart fallback；保留当期 route，不安装 genmedia。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F05

```json
{
  "conflict_id": "F05",
  "capability": [
    "C24",
    "C25"
  ],
  "conflict_type": "ARCHITECTURE_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "## Genmedia workflow",
        "line": 37,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L37"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/genmedia/SKILL.md",
        "section": "## Critical rules",
        "line": 19,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/genmedia/SKILL.md#L19"
      }
    ],
    "rule": "由 genmedia 安装、run、status、download 管执行。",
    "scope": {
      "capability": "execution lifecycle",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "execution"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/execution.py",
        "symbol_or_section": "def require_execution",
        "line": 36,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/production.py",
        "symbol_or_section": "class Review",
        "line": 298,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/hosts/visual_delivery.py",
        "symbol_or_section": "async def complete_attempt",
        "line": 10,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "Host/MCP、预约、异步恢复与 Media persistence 各有合同。",
    "scope": {
      "capability": "execution lifecycle",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "execution"
    },
    "validation": "源码边界；不在本轮调用运行服务; 源码和 selected tests；无新媒体语义 PASS; 源码与 shot-production durable completion；本轮未访问 Media"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "REJECT",
  "winner": "L15/L17/L18",
  "reason": "替换运行栈为安装便利，不是专业能力边界改进。",
  "future_action": "REJECT R；下载结果不得绕过 formal Media。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F06

```json
{
  "conflict_id": "F06",
  "capability": [
    "C21"
  ],
  "conflict_type": "PROVIDER_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-prompting/references/gpt-image-2.md",
        "section": "## Common parameters",
        "line": 132,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L132"
      }
    ],
    "rule": "fal edit 支持 16 references 与 mask 参数。",
    "scope": {
      "capability": "reference capacity / edit controls",
      "modality": "still",
      "provider": "fal/openai/gpt-image-2/edit",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "payload"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/image_route.py",
        "symbol_or_section": "def select_frame_template",
        "line": 11,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/frame_request.py",
        "symbol_or_section": "def compile_frame",
        "line": 178,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "本地 Comfy frame 只接受已核准三 references；没有 mask edit 控制。",
    "scope": {
      "capability": "reference capacity / edit controls",
      "modality": "still",
      "provider": "Comfy/OpenAIGPTImageNodeV2",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "payload"
    },
    "validation": "test_hero_vidu_routes.py、test_route_image_inputs.py；未实时重新连 Provider; frame input、source mismatch、slot wiring tests"
  },
  "same_scope": false,
  "authority_level": "L1",
  "decision": "COEXIST_IN_SEPARATE_SCOPE",
  "winner": "fal schema in fal scope; local adapter in Comfy scope",
  "reason": "同模型名字不等于同 transport/schema；16 不能自动替换三张 gate。",
  "future_action": "PROVIDER_SCOPE_ONLY；本地扩容不在本轮。纠正指南参数需现行 schema，不直接继承 mask_image_url/input_fidelity。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F07

```json
{
  "conflict_id": "F07",
  "capability": [
    "C16"
  ],
  "conflict_type": "PROMPT_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "## Identity preservation",
        "line": 251,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L251"
      }
    ],
    "rule": "realism recipe 的 reference edit 不重述面部。",
    "scope": {
      "capability": "face text in reference edit",
      "modality": "still",
      "provider": "fal GPT Image 2 edit",
      "medium": "LIVE_ACTION",
      "task": "identity-preserving image edit",
      "production_stage": "serialization"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/image_serializer.py",
        "symbol_or_section": "def render_image",
        "line": 27,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/frame_request.py",
        "symbol_or_section": "def compile_frame",
        "line": 178,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "edit serializer 保留 role/face/costume，省略其它旧外观细节。",
    "scope": {
      "capability": "face text in reference edit",
      "modality": "still",
      "provider": "Comfy GPT Image 2",
      "medium": "LIVE_ACTION",
      "task": "identity-preserving image edit",
      "production_stage": "serialization"
    },
    "validation": "test_image_serializer.py：顺序/遗漏/identity/预算；非 provider A/B; frame input、source mismatch、slot wiring tests"
  },
  "same_scope": false,
  "authority_level": "L5",
  "decision": "COEXIST_IN_SEPARATE_SCOPE",
  "winner": "L12 for current route; external recipe REFERENCE_ONLY",
  "reason": "外部没有同 Comfy scope 因果证据。本地 tests 仅证明已选合同，不证明保留脸部词质量更好。",
  "future_action": "KEEP_LOCAL 当前执行；未来如有同路线控制对照，再裁决 face policy，禁止两个 prompt 同时发出。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F08

```json
{
  "conflict_id": "F08",
  "capability": [
    "C31"
  ],
  "conflict_type": "SEMANTIC_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "## Anti-AI-look checklist",
        "line": 234,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L234"
      }
    ],
    "rule": "泛写实规则要求添加毛孔、红眼、灰尘及二三个瑕疵。",
    "scope": {
      "capability": "surface identity and image artifacts",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/specialized_asset.py",
        "symbol_or_section": "FORWARDED_DEPARTMENTS",
        "line": 12,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/hosts/specialized_asset.py",
        "symbol_or_section": "def bind_movie",
        "line": 19,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/shot-production/SKILL.md",
        "symbol_or_section": "## Use-based content review",
        "line": 101,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "已批准身份/外观/状态不能被 compiler 新增；可见缺陷按实际用途判定。",
    "scope": {
      "capability": "surface identity and image artifacts",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "test_specialized_asset.py：旧 writer 拒绝、source replay、审批绑定; test_specialized_asset.py：env pin、跨 Work、medium override; 规范＋production.py；不把测试视为审美有效性"
  },
  "same_scope": true,
  "authority_level": "L2",
  "decision": "REJECT",
  "winner": "Approved asset/style (L02/L03)",
  "reason": "Level 2 事实优先；未验证候选不能修改批准皮肤/环境或把画面缺陷当必要条件。",
  "future_action": "REJECT 强制清单；可选材质/光学观察经 owner 认可后归 C11/C28，不附加到 prompt。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F09

```json
{
  "conflict_id": "F09",
  "capability": [
    "C32"
  ],
  "conflict_type": "SEMANTIC_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "## Anti-AI-look checklist",
        "line": 234,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L234"
      }
    ],
    "rule": "将 dead-center、对称构图、正视视线、无动作视为 AI tells。",
    "scope": {
      "capability": "composition / gaze / stillness",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/skills/cinematography/SKILL.md",
        "symbol_or_section": "## Professional decisions",
        "line": 20,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/blocking/SKILL.md",
        "symbol_or_section": "## Role and authority",
        "line": 8,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/director/SKILL.md",
        "symbol_or_section": "## Role and authority",
        "line": 16,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "当前批准构图/视线/静止可有明确戏剧目的。",
    "scope": {
      "capability": "composition / gaze / stillness",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "声明＋registry 字段；没有本轮可归因实拍 A/B; 部门边界与连续性测试; 部门边界测试；不等于作品审美验证"
  },
  "same_scope": true,
  "authority_level": "L2",
  "decision": "REJECT",
  "winner": "Approved Camera/Blocking/Director facts",
  "reason": "外部 checklist 自称任意 realistic prompt，但 documentary/candid 偏好不能成为电影普遍准则；不能覆盖明确创作。",
  "future_action": "REJECT universal gate；candid 场景选项仅留 REFERENCE_ONLY，不自动改 approved shot。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F10

```json
{
  "conflict_id": "F10",
  "capability": [
    "C33"
  ],
  "conflict_type": "SEMANTIC_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "### Documentary / photojournalism",
        "line": 118,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L118"
      }
    ],
    "rule": "documentary 子类型只用场景光、禁 fill。",
    "scope": {
      "capability": "motivated fill",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "documentary/photojournalism still",
      "production_stage": "design"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/skills/lighting-design/SKILL.md",
        "symbol_or_section": "## Professional decisions",
        "line": 20,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "电影动机光允许符合来源和可读性的补光。",
    "scope": {
      "capability": "motivated fill",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "部门归属测试；艺术效果未证实"
  },
  "same_scope": false,
  "authority_level": "L2",
  "decision": "COEXIST_IN_SEPARATE_SCOPE",
  "winner": "L05 for film; reference-only documentary preference",
  "reason": "任务不同。单主方向也不等于单一光源；cinema 原文 warm-interior 示例本身含灯/月光。",
  "future_action": "REFERENCE_ONLY 类型建议；不得定义全局 no-fill 或强制 mixed-temperature。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F11

```json
{
  "conflict_id": "F11",
  "capability": [
    "C34"
  ],
  "conflict_type": "LIFECYCLE_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "## Common parameters",
        "line": 325,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L325"
      }
    ],
    "rule": "写实生成 2–4 variants 选优、固定 seed。",
    "scope": {
      "capability": "candidate count and retries",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "production"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/image_route.py",
        "symbol_or_section": "def select_frame_template",
        "line": 11,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/production.py",
        "symbol_or_section": "class Review",
        "line": 298,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "正式 frame n=1；逐请求预约/观察；未知创建不能再提交。",
    "scope": {
      "capability": "candidate count and retries",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "production"
    },
    "validation": "test_hero_vidu_routes.py、test_route_image_inputs.py；未实时重新连 Provider; 源码和 selected tests；无新媒体语义 PASS"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "REJECT",
  "winner": "L13/L17",
  "reason": "预算/幂等性是平台合同，不由 seed 幸运论覆盖。",
  "future_action": "REJECT 默认批量；未来任何不同 batch 策略须独立平台授权；当前保持 n=1。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F12

```json
{
  "conflict_id": "F12",
  "capability": [
    "C17",
    "C36"
  ],
  "conflict_type": "QUALITY_GATE_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/character-design/SKILL.md",
        "section": "## Quality bar",
        "line": 140,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/SKILL.md#L140"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "## Quality bar",
        "line": 132,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L132"
      }
    ],
    "rule": "对漂移/手或 prop 干扰直接 reject or retry；generic 就加强细节。",
    "scope": {
      "capability": "still QC disposition",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "observed review"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/production.py",
        "symbol_or_section": "class Review",
        "line": 298,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/shot-production/SKILL.md",
        "symbol_or_section": "## Use-based content review",
        "line": 101,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "观察→明确约束→用途严重度；轻微不妨碍用途的差异不能自动失败。",
    "scope": {
      "capability": "still QC disposition",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "observed review"
    },
    "validation": "源码和 selected tests；无新媒体语义 PASS; 规范＋production.py；不把测试视为审美有效性"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "ADAPT",
  "winner": "L17/L21 review contract",
  "reason": "外部提供要观察什么，本地规定何时证据足够及如何定级；不宣称本地审美更强。",
  "future_action": "C17/C36 指标进入原 gate 候选；删除自动 rerun implication，保留 UNKNOWN 和 user adoption 分离。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F13

```json
{
  "conflict_id": "F13",
  "capability": [
    "C14",
    "C08"
  ],
  "conflict_type": "MODALITY_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "4. Camera motion",
        "line": 101,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L101"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/references/shot-language.md",
        "section": "## Camera movement",
        "line": 23,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/shot-language.md#L23"
      }
    ],
    "rule": "video camera moves/rack focus；still 可表现 motion blur。",
    "scope": {
      "capability": "camera motion",
      "modality": "video",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "video movement",
      "production_stage": "video temporal design"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/prompt_ir.py",
        "symbol_or_section": "def compile_ir",
        "line": 12,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/frame_request.py",
        "symbol_or_section": "def compile_frame",
        "line": 178,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "still 只能 CURRENT 静态目标，禁止 temporal progression。",
    "scope": {
      "capability": "camera motion",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "test_visual_prompt_ir.py；deterministic，不证明照片真实; frame input、source mismatch、slot wiring tests"
  },
  "same_scope": false,
  "authority_level": "L1",
  "decision": "COEXIST_IN_SEPARATE_SCOPE",
  "winner": "L11 static scope; video owners outside round",
  "reason": "motion blur 可以是已批准静态结果，但推拉/拉焦时间轴不是 still 指令。",
  "future_action": "KEEP_LOCAL 静态边界；C08 FUTURE_VIDEO_ROUND，不迁移 Seedance/Vidu 控制。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F14

```json
{
  "conflict_id": "F14",
  "capability": [
    "C26",
    "C27"
  ],
  "conflict_type": "LIFECYCLE_CONFLICT / OWNERSHIP_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/storytelling/references/workflows.md",
        "section": "## Character narrative",
        "line": 35,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/storytelling/references/workflows.md#L35"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "- Video prompt describes",
        "line": 140,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L140"
      }
    ],
    "rule": "优先 approved still→I2V；模型支持 multi-prompt 时允许多镜头。",
    "scope": {
      "capability": "video preparation and coverage",
      "modality": "video",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "planning"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/skills/shot-design/SKILL.md",
        "symbol_or_section": "## Role and authority",
        "line": 15,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/video-model-selection/SKILL.md",
        "symbol_or_section": "---",
        "line": 1,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/shot-production/SKILL.md",
        "symbol_or_section": "## Use-based content review",
        "line": 101,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "coverage 从戏剧出发、输入 duties 由 qualified route 产生；没有普遍 still-first。",
    "scope": {
      "capability": "video preparation and coverage",
      "modality": "video",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "planning"
    },
    "validation": "thin assembly 与 dependency tests; 本轮只定位；video 正式吸收排除; 规范＋production.py；不把测试视为审美有效性"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "KEEP_LOCAL",
  "winner": "L09/L16/L21",
  "reason": "Level 1 架构和 Level 2 叙事不受 provider 反向定义；本轮只裁决边界不设计视频吸收。",
  "future_action": "FUTURE_VIDEO_ROUND；不得新增镜头/提前生成全部 keyframes。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F15

```json
{
  "conflict_id": "F15",
  "capability": [
    "C15",
    "C20"
  ],
  "conflict_type": "AUTHORITY_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/character-design/references/anchor-system.md",
        "section": "## Anchor fields",
        "line": 6,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-prompting/references/gpt-image-2.md",
        "section": "### Mode 3",
        "line": 68,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L68"
      }
    ],
    "rule": "把整体 anchor（含 posture/style）重复并继承 reference。",
    "scope": {
      "capability": "identity versus current pose",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "reference projection"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/specialized_asset.py",
        "symbol_or_section": "FORWARDED_DEPARTMENTS",
        "line": 12,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/blocking/SKILL.md",
        "symbol_or_section": "## Role and authority",
        "line": 8,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/frame_request.py",
        "symbol_or_section": "def compile_frame",
        "line": 178,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "身份参考只绑定身份，当前姿势/视线/位置来自 Shot/Blocking。",
    "scope": {
      "capability": "identity versus current pose",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "reference projection"
    },
    "validation": "test_specialized_asset.py：旧 writer 拒绝、source replay、审批绑定; 部门边界与连续性测试; frame input、source mismatch、slot wiring tests"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "ADAPT",
  "winner": "L02 stable identity; L08 current state; L14 slots",
  "reason": "结构性责任必须拆开；同一 reference 不能夺取当前动作权威。",
  "future_action": "保留 anchor/variable 思路；把各变量交还原 owner；禁止 reference pose 默认迁移。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F16

```json
{
  "conflict_id": "F16",
  "capability": [
    "C12",
    "C18",
    "C29"
  ],
  "conflict_type": "EXTERNAL_INTERNAL_PROMPT_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "## Prompt build order",
        "line": 94,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L94"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-prompting/references/gpt-image-2.md",
        "section": "## Prompt structure",
        "line": 18,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L18"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "## Prompt build order",
        "line": 72,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L72"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "## Prompt build order",
        "line": 72,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L72"
      }
    ],
    "rule": "SCLCAM subject-first；GPT 五段 scene-first；realism 六段禁止重排。",
    "scope": {
      "capability": "prompt section order",
      "modality": "still",
      "provider": "GPT Image 2 family",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "serialization"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/image_serializer.py",
        "symbol_or_section": "def render_image",
        "line": 27,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "一个静态 serializer 负责实际顺序，不按 load 次序决定。",
    "scope": {
      "capability": "prompt section order",
      "modality": "still",
      "provider": "GPT Image 2 family",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "serialization"
    },
    "validation": "test_image_serializer.py：顺序/遗漏/identity/预算；非 provider A/B"
  },
  "same_scope": true,
  "authority_level": "L5",
  "decision": "REFERENCE_ONLY",
  "winner": "L12 current; no external ordering winner",
  "reason": "三种写法在 GPT realistic still 任务重合，外部没有相同输入/输出对照；不存在证据充分的 Level 3 winner。",
  "future_action": "三模板仅 reference；不将任一绝对顺序提升为 Canonical。未来验证胜者必须替换原 serializer policy，而非追加模板。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F17

```json
{
  "conflict_id": "F17",
  "capability": [
    "C22",
    "C25"
  ],
  "conflict_type": "EXTERNAL_INTERNAL_ROUTING_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "## Model routing",
        "line": 114,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L114"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/genmedia/SKILL.md",
        "section": "## Critical rules",
        "line": 19,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/genmedia/SKILL.md#L19"
      }
    ],
    "rule": "model-routing 要 endpoint-first；较新 genmedia 对默认质量要求 smart routing。",
    "scope": {
      "capability": "default endpoint choice",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "routing"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/image_route.py",
        "symbol_or_section": "def select_frame_template",
        "line": 11,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/execution.py",
        "symbol_or_section": "def require_execution",
        "line": 36,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "平台 route 显式密封，不运行 genmedia。",
    "scope": {
      "capability": "default endpoint choice",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "routing"
    },
    "validation": "test_hero_vidu_routes.py、test_route_image_inputs.py；未实时重新连 Provider; 源码边界；不在本轮调用运行服务"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "REJECT",
  "winner": "L13/L15",
  "reason": "外部可在 premium 特定任务解释为例外，但默认 brief 的 precedence 未在 cinema 中统一；无须为接入该矛盾更改平台。",
  "future_action": "两类外部路由均不得入本地 Runtime；若未来评估 genmedia 则单独核实版本和优先规则。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F18

```json
{
  "conflict_id": "F18",
  "capability": [
    "C24"
  ],
  "conflict_type": "LIFECYCLE_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "## Genmedia workflow",
        "line": 37,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L37"
      }
    ],
    "rule": "下载路径/request id 即可交付。",
    "scope": {
      "capability": "completion proof",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "delivery"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/hosts/visual_delivery.py",
        "symbol_or_section": "async def complete_attempt",
        "line": 10,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "Media 要 readback bytes/hash、ownership、stable business binding。",
    "scope": {
      "capability": "completion proof",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "delivery"
    },
    "validation": "源码与 shot-production durable completion；本轮未访问 Media"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "KEEP_LOCAL",
  "winner": "L18",
  "reason": "Level 1 Storage contract；路径只是执行证据，不是正式存储身份。",
  "future_action": "REJECT downloaded-path-as-completion；任何未来 provider 结果仍由现有 completion entry 落库。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F19

```json
{
  "conflict_id": "F19",
  "capability": [
    "C35"
  ],
  "conflict_type": "LIFECYCLE_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-prompting/references/gpt-image-2.md",
        "section": "**6. One revision",
        "line": 44,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L44"
      }
    ],
    "rule": "每 turn 只改一项。",
    "scope": {
      "capability": "repair granularity",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "rework"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/skills/shot-production/SKILL.md",
        "symbol_or_section": "## Use-based content review",
        "line": 101,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "允许同一批准目标下最小可用修复并保留成本/策略；一组相关修复可同时必要。",
    "scope": {
      "capability": "repair granularity",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "rework"
    },
    "validation": "规范＋production.py；不把测试视为审美有效性"
  },
  "same_scope": true,
  "authority_level": "L5",
  "decision": "ADAPT",
  "winner": "L21 for production; controlled-variable rule for experiment",
  "reason": "外部适合作对照实验原则，无证据证明“一 turn 一改”应压过已授权修复。",
  "future_action": "只采用实验设计的单变量原则；不添加用户交互次数/固定重试上限。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F20

```json
{
  "conflict_id": "F20",
  "capability": [
    "C40"
  ],
  "conflict_type": "LIFECYCLE_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "If a result still fails realism",
        "line": 323,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L323"
      }
    ],
    "rule": "失败就用真实 reference photo/edit mode。",
    "scope": {
      "capability": "reference fallback",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "rework"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/specialized_asset.py",
        "symbol_or_section": "FORWARDED_DEPARTMENTS",
        "line": 12,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/frame_request.py",
        "symbol_or_section": "def compile_frame",
        "line": 178,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/shot-production/SKILL.md",
        "symbol_or_section": "## Use-based content review",
        "line": 101,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "稳定 approved reference、身份权属、qualified route 及预算必须满足。",
    "scope": {
      "capability": "reference fallback",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "rework"
    },
    "validation": "test_specialized_asset.py：旧 writer 拒绝、source replay、审批绑定; frame input、source mismatch、slot wiring tests; 规范＋production.py；不把测试视为审美有效性"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "KEEP_LOCAL",
  "winner": "L02/L14/L21",
  "reason": "不能因 generic output 换掉已批准身份或绕过参考图 provenance。",
  "future_action": "KEEP_LOCAL；仅把诊断退回 reference-strategy/asset owner，未许可不执行切换。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F21

```json
{
  "conflict_id": "F21",
  "capability": [
    "C06"
  ],
  "conflict_type": "SEMANTIC_CONFLICT_CANDIDATE",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/references/lighting-lens-color.md",
        "section": "## Lens feel",
        "line": 16,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L16"
      }
    ],
    "rule": "焦段列表经常绑定固定题材/人物效果。",
    "scope": {
      "capability": "lens selection",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/skills/cinematography/SKILL.md",
        "symbol_or_section": "## Professional decisions",
        "line": 20,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "从距离、空间和观众需求确定 lens intention，避免无依据数值。",
    "scope": {
      "capability": "lens selection",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "声明＋registry 字段；没有本轮可归因实拍 A/B"
  },
  "same_scope": true,
  "authority_level": "L5",
  "decision": "ADAPT",
  "winner": "L04 as owner; external vocabulary is optional knowledge",
  "reason": "原文使用 feel，并未强制精确焦距，故不是与 local 相反的物理规则；潜在冲突来自照表自动选 mm 的导入方式。",
  "future_action": "允许词汇充实；REJECT 自动题材→焦段与精确控制承诺；不替换 Camera owner。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F22

```json
{
  "conflict_id": "F22",
  "capability": [
    "C10"
  ],
  "conflict_type": "OWNERSHIP_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/references/lighting-lens-color.md",
        "section": "## Color and grade",
        "line": 32,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L32"
      }
    ],
    "rule": "同一 cinematic prompt 混合 palette、exposure style 与 final grade。",
    "scope": {
      "capability": "color/grade decision ownership",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/skills/color-design/SKILL.md",
        "symbol_or_section": "## Professional decisions",
        "line": 20,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/color-grading/SKILL.md",
        "symbol_or_section": "## Professional decisions",
        "line": 20,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/skills/lighting-design/SKILL.md",
        "symbol_or_section": "## Professional decisions",
        "line": 20,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "色彩发展、灯光因果、最终匹配各有原件和阶段。",
    "scope": {
      "capability": "color/grade decision ownership",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "部门归属测试；非 provider 性能证明; 声明；本轮无画面调色观察; 部门归属测试；艺术效果未证实"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "ADAPT",
  "winner": "L06/L07/L05 partition",
  "reason": "职责冲突不意味着色彩建议无价值；缺原始画面不能冒充完成 grade。",
  "future_action": "意图分配给已存在 owner；不让 adapter LUT/调色重写场景事实。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F23

```json
{
  "conflict_id": "F23",
  "capability": [
    "C31",
    "C30"
  ],
  "conflict_type": "SEMANTIC_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "## Anti-AI-look checklist",
        "line": 234,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L234"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-recipes/references/realism.md",
        "section": "## Two orthogonal axes",
        "line": 83,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L83"
      }
    ],
    "rule": "写实指南给 phone/film/年代组合及身体细节近似普遍摄影真理。",
    "scope": {
      "capability": "realism/medium scope",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/hosts/specialized_asset.py",
        "symbol_or_section": "def bind_movie",
        "line": 19,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/specialized_asset.py",
        "symbol_or_section": "FORWARDED_DEPARTMENTS",
        "line": 12,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "批准 medium、风格、角色和时代事实逐作品约束；CG 不接受 live-action pores 默认。",
    "scope": {
      "capability": "realism/medium scope",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "CG",
      "task": "film still",
      "production_stage": "design"
    },
    "validation": "test_specialized_asset.py：env pin、跨 Work、medium override; test_specialized_asset.py：旧 writer 拒绝、source replay、审批绑定"
  },
  "same_scope": false,
  "authority_level": "L2",
  "decision": "COEXIST_IN_SEPARATE_SCOPE",
  "winner": "L03 medium separation",
  "reason": "跨 medium 不产生专业优先权；历史电影的故事年代和摄影工艺年代也不是一轴。",
  "future_action": "所有 K/Q 标明 LIVE_ACTION/still/task，不能进入 CG 全局 policy。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F24

```json
{
  "conflict_id": "F24",
  "capability": [
    "C12",
    "C21"
  ],
  "conflict_type": "PROVIDER_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/cinematography/SKILL.md",
        "section": "## Prompt build order",
        "line": 94,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L94"
      },
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-prompting/references/gpt-image-2.md",
        "section": "## Common parameters",
        "line": 132,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L132"
      }
    ],
    "rule": "把 aspect、duration、模型控制拼进领域 Prompt。",
    "scope": {
      "capability": "output control ownership",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "payload"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/prompt_ir.py",
        "symbol_or_section": "def compile_ir",
        "line": 12,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/image_route.py",
        "symbol_or_section": "def select_frame_template",
        "line": 11,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "structured execution fields 属于 adapter；STATIC 不含视频 duration。",
    "scope": {
      "capability": "output control ownership",
      "modality": "still",
      "provider": "provider-neutral",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "payload"
    },
    "validation": "test_visual_prompt_ir.py；deterministic，不证明照片真实; test_hero_vidu_routes.py、test_route_image_inputs.py；未实时重新连 Provider"
  },
  "same_scope": true,
  "authority_level": "L1",
  "decision": "KEEP_LOCAL",
  "winner": "L11/L13",
  "reason": "文本只能表达批准可见画幅意图，参数值需 adapter schema；重复定义容易产生不一致。",
  "future_action": "REJECT prompt-owned execution controls；payload 单一字段 authority，当前 runtime 不变。",
  "status": "RESOLVED_FOR_A2R"
}
```

### F25

```json
{
  "conflict_id": "F25",
  "capability": [
    "C41"
  ],
  "conflict_type": "PROMPT_CONFLICT",
  "external": {
    "source": [
      {
        "repository": "https://github.com/fal-ai-community/skills",
        "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
        "file": "skills/fal-prompting/references/gpt-image-2.md",
        "section": "## Prompt structure",
        "line": 18,
        "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L18"
      }
    ],
    "rule": "外部 structured prompt 的 Constraints 可直接使用否定句；专用 negative 字段需要 schema 支持。",
    "scope": {
      "capability": "constraint serialization",
      "modality": "still",
      "provider": "GPT Image 2 family",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "serialization"
    },
    "validation": "候选规则/文本示例；未发现该 scope 实产对照；参数适用性不等于质量验证"
  },
  "local": {
    "source": [
      {
        "file": "plugin/src/drama_plugin/visual/prompt_ir.py",
        "symbol_or_section": "def compile_ir",
        "line": 12,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      },
      {
        "file": "plugin/src/drama_plugin/visual/image_serializer.py",
        "symbol_or_section": "def render_image",
        "line": 27,
        "commit": "8f805217f9b7b692a10f3ec0a5363a938f91b192"
      }
    ],
    "rule": "本地 IR 保留 negative constraint，正式非 edit 约束输出作者显式提供的 positive_target；edit 的 remove/replace/correct 原样保留。",
    "scope": {
      "capability": "constraint serialization",
      "modality": "still",
      "provider": "GPT Image 2 family",
      "medium": "LIVE_ACTION",
      "task": "film still",
      "production_stage": "serialization"
    },
    "validation": "test_visual_prompt_ir.py；deterministic，不证明照片真实; test_image_serializer.py：顺序/遗漏/identity/预算；非 provider A/B"
  },
  "same_scope": true,
  "authority_level": "L5",
  "decision": "KEEP_LOCAL",
  "winner": "L11/L12 current policy",
  "reason": "局部文本策略没有外部 same-scope 实产优势证据；禁止 compiler 自行发明等价正向事实。此处只维持现行选择，不把 positive prompting 当作已验证普遍真理。",
  "future_action": "REJECT 将外部 negative 模板追加到现有 prompt；任何未来胜出策略仅由同一 serializer 切换并停用旧策略，原 constraint/source 仍在 IR。",
  "status": "RESOLVED_FOR_A2R"
}
```

## Prompt Ownership Audit

外部 cinematography、realism、fal-prompting 都直接写最终 prompt。迁入本地时不允许它们继续持有该权力：

| 信息 | 最终 authority | 允许的候选处理 |
|---|---|---|
| 视点、距离、lens feel、焦平面、构图 | Camera owner，经 Director/canon 约束 | ADAPT 专业选择与理由，不输出最终 provider string |
| 光源、方向、材质可见性 | Lighting / Specialized Asset，各自原件 | source-pinned intent，不凭写实模板新增物体或伤痕 |
| palette 与成像质感 | Color / GlobalStyle / Grade 对应阶段 | 可选约束，不直接改变媒介 |
| 物理真实、identity、可读性检查 | 已有 QA review，加有 scope 的 criteria | 实际媒体观察，UNKNOWN 与 FAIL 分开 |
| GPT Image 2 分节/措辞习惯 | Prompt Compiler 的 provider-scoped serializer | 仅可设计单一 policy 的边界，不让专业 Skill owns prompt |
| fal/Comfy 参数、slots、mask、尺寸、数量 | 当前 route 对应 Adapter | 仅用该 transport 可验证 schema；不能搬 16 图到三图适配器 |
| 最终 prompt→请求 | compiler receipt + adapter exact transfer | 无后置 enhancer 或另一条自由文本替代 |

本地静态 serializer 目前是共享的。**GPT Image 2 特有 projection 应由专门的 provider-scoped serializer policy 管理**，而通用摄影视觉决策归原专业 owner；transport adapter 只映射参数。A3 可以判断是否需分离 policy，不能借“需要 adapter”重做整个架构。不要把 fal `/edit` 参数混作 OpenAI 原生 API 或 Comfy node 参数。

## Final Decision Table（完整互斥列表）

这里 ADAPT 为设计候选，ADOPT 为可直接采用的已验证外部规则。MERGE/PROVIDER_SCOPE_ONLY 是 A2 枚举；最终列表将 provider-only 归 REFERENCE_ONLY，防止误解为已接入。所有 video-only 条目落 FUTURE_VIDEO_ROUND。

| Final decision | Capability IDs | 具体处理 |
|---|---|---|
| ADOPT | ∅ | 空：无能力达到经实产验证、可直接升级 authority 的门槛。 |
| ADAPT | C02, C03, C04, C05, C06, C07, C09, C10, C11, C13, C15, C17, C28, C30, C35, C36 | 进入最小 A3 知识/职责/验证要求设计；没有生产准入。 |
| REPLACE_LOCAL | ∅ | 空：没有得到证据支持的本地专业规则替换裁决。 |
| KEEP_LOCAL | C01, C14, C16, C19, C20, C23, C40, C41 | 明确保留目前 owner/合同；不是影像效果优越声明。 |
| REFERENCE_ONLY | C18, C21, C33, C37, C38 | 仅查阅；C21 留 fal provider scope；不调用/安装。 |
| REJECT | C12, C22, C24, C25, C29, C31, C32, C34, C39 | 拒绝整体进入 Runtime；不否定其中可拆出的其他独立 K 条目。 |
| FUTURE_VIDEO_ROUND | C08, C26, C27 | 只记录 future_assimilation_candidate；不设计 Seedance/Vidu 正式吸收。 |

### LOCAL_RULES_EXPECTED_TO_BE_REPLACED

`[]`。这不是保护旧代码：本轮外部没有同范围更强实产证据。没有依据把本地 face-anchor、section order、positive-target 或 camera restraint 规则判作应被外部替换。后续若获得外部优胜证据，必须给出具体 loser 的文件/symbol/version 与 `REMOVE / DEPRECATE_AND_DISABLE / MOVE_TO_HISTORY / REFERENCE_ONLY`，停用旧 runtime policy，重新冻结 compilation；旧输出可历史重放但不再授予新生产权。

本轮已拒绝的外部 authority 永不以“追加提示层”进入 Runtime。将来获胜者也只能占有一个已明确 scope 的位置，不得让 prompt order 决定 A 与 B 谁生效。

### EXTERNAL_RULES_NOT_ALLOWED_TO_ENTER_RUNTIME

- C12/C29：SCLCAM/六段强制顺序的独立 final-prompt authority；C18 五段模板原文只能 reference。
- C22/C25：endpoint 排名、自动 fallback、smart routing、installer/自动注册。
- C24：绕过当前 Host/MCP/预算/Storage 的 genmedia 执行与路径即完成。
- C21：fal-only 参数、16 图上限、未经 schema 证实的参数拼写不得进入 Comfy。
- C31/C32/C33/C39：强制瑕疵、反居中/正视/静止、电影全局禁 fill、默认 phone/年代；documentary scope 的例外只留参考。
- C34：无预算授权批量 variants；seed 保真/可复现的无证据承诺。
- C16/C40：不允许跨 transport 自动删 required face fact、换掉 approved reference 或自动切 edit。
- C08/C26/C27：本轮所有 video 正式行为；C37/C38 的文字排版/示例不整体吸收。
- 外部 prompt 字符串、安装脚本和 provider 默认值均未复制进现有 prompt 或 runtime。

## A3 最小范围与后续门槛（仅提出，未执行）

READY_FOR_A3=YES 的含义是“职责裁决足以开始小范围设计”，不等于 license 完整、外部效果已验证或生产已就绪。

最小 A3 只涵盖：

1. 用本报告 ADAPT 集合设计 STILL/LIVE_ACTION 的专业意图与 QC 适用范围，复用现有 Camera/Lighting/Color/Specialized Asset/Review owner；先检查现有字段能否表达，再决定是否必须增加极少数契约字段。
2. 设计一个来源与消费映射：source decision→IR Fact/source→唯一静态 serializer→对应 adapter 参数；不写实现，不建立平行 Skill、统一大 Bible 或新存储实体。
3. 给 GPT Image 2 当前路线的候选 serializer 写对照验证要求：同 source/medium/task/reference/transport、控制变量、实际 bytes 与 observable QC；区分 source-pin 单测和真实媒体效果。此处只说明未来测试需要什么，不进行付费生成。
4. 为任何未来替换写明确 loser 停用/历史保存条件。本轮 replacement 集为空，不能预先删本地规则。

复制或再分发外部原文前仍有 license notice/覆盖待澄清；正式升级到 VALIDATED_EXTERNAL 或声称摄影增强前仍需同 scope 真实验证。两个门槛限制后续 adoption/implementation，不是本轮未裁决的 authority 冲突。A3 不包含视频、Provider 切换、MCP/Service/Storage 重构、技能安装或真实生成。

## Stop Gate

- 0 runtime behavior changes：基线 tracked hashes 与最终核对，见 [完成核验](evidence/completion-check.json)。
- 0 paid generation：只执行 GitHub/公开文档读取、本地源码审计和禁网 pytest。
- 0 unresolved same-scope authority conflicts：全部 25 个记录已裁决；精确不同范围明确共存。
- 0 silent external-skill installation：只临时 clone；报告目录不被 skill discovery 扫描。
- 未修改 Canonical Contract、生产 Skill、Compiler、Adapter、Director、MCP、Service、Storage；未生成图片/视频。

**A0 → A1 → A2 → A2R 完成；STOP。**
