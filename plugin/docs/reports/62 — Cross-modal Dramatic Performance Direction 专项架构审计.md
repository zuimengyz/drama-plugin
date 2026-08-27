# 62 — Cross-modal Dramatic Performance Direction 专项架构审计

日期：2026-08-27（Asia/Shanghai）  
审计类型：Architecture / Skill / Contract Responsibility Audit  
结论：`CROSS_MODAL_DPD_AUDIT = COMPLETE`

## 1. Executive Summary

本批只审计 repository 中的 Skill、typed contracts、Provider adapters、tests、历史 Audio / Visual evidence 与 59/61 号报告；没有修改任何生产业务代码，没有创建 DPD Skill/Tool/Domain，没有调用 Fish、Qwen、Comfy、Video 或 Lip Sync。

核心结论：

1. **需要独立的 `dramatic-performance-direction` Skill。** 当前 Scene 只持久化一条简短、非 typed 的 line `performanceIntent`；Audio 又在运行时重新构造 rich baseline-plus-delta；Visual 只从 Shot/action 编译行为。没有一个共同、可重现的表演决策上游。
2. **位置选 Option C，但不建两个导演对象。** Scene Review PASS 后生成一份 hierarchical `DramaticPerformanceDirection`，其 Scene/Beat/Line core 供 Shot Design 使用；Shot 和 transient Timing Plan 完成后，由 Audio/Visual 业务边界生成 projection brief。Projection 不重新解释人物或改写 DPD core。
3. **当前 `PerformanceIntent` 应“拆分并迁移”，不是原样扩张。** Cross-modal objective/target/subtext/activation/control/boundary 迁入 DPD；pace/volume/breath/sentence closure 进 Audio Projection；当前 emotion/stress/physical condition 保留在 SceneState；模糊 legacy `delivery/pace/pauseAfterMs` 废弃。
4. **DPD 不重做 Character Understanding，不读 Creative Voice Casting。** Character Understanding 提供稳定、中性、有证据的人物边界；Creative Voice Casting 决定长期声音。DPD 只决定当前 Scene 的表演。Audio Projection 再合并 DPD + approved Voice Profile/Casting + Timing。
5. **DPD core 必须保持小。** 共享语义只需 acting objective、interaction target、authority position、internal activation、external control、可选 subtext/pause function 和 performance boundaries。呼吸、收句、音量属 Audio；gaze、posture、gesture、facial tension、mouth visibility 属 Visual。
6. **持久化推荐 compact Scene snapshot，不是新 Domain。** 仅 transient 不能保证 Windows/macOS 换 Host 后使用同一导演方案。建议将一份 compact、versioned snapshot 放在现有 `Scene.content` open JSON；Shot-specific briefs 保持 transient，生成后只在 Media provenance 记录 fingerprint/version。
7. **不需新 MCP Tool、Java Domain 或 DB migration。** DPD 是 Skill planning，可用现有 Work/Scene/Shot read/save Tool 和 open content。`drama-mcp-service` 不应承载 director logic。
8. **不增加默认人工 `PERFORMANCE_DIRECTION_REVIEW`。** 保留 Scene/Shot Review 和 Audio/Visual 结果 Review。Voice Casting Review 与 DPD 完全分离。
9. **下一批只做 Contract/Foundation，不做真实 Single-Scene E2E。** 最小范围是新 Skill、typed transient contract、现有 PerformanceIntent reconciliation、mock Audio/Visual projections 与 offline tests。

## 2. Audit Scope

已审计：

- `scene-development`、`shot-design`、`shot-production`、`audio-production` 的 `SKILL.md`、`skill.yaml` 及必读 references；
- `contracts/audio.py`、`contracts/creation.py`、`contracts/media.py`；
- `audio/foundation.py`、Qwen/OpenAI/Fish speech adapters 与 Fish 验证 runner；
- `production.generate_image/video/audio` Tool catalog 与 Provider protocols；
- Dialogue/Audio content conventions；
- 7.2S-R Character Understanding、SceneState、PerformanceIntent、Speech Request evidence；
- Batch 5.5 / 6.0 Visual E2E evidence；
- 53、54、59、61 号报告；
- `drama-mcp-service` 的通用投影边界与 `drama-service` 的 open JSON persistence。

本批不评估 Provider 实时质量，不修正代码，不生成任何媒体。

## 3. Current AS-IS Performance Flow

### 3.1 真实现状图

```text
Work / Script / Episode
          ↓
scene-development
  ├─ Scene objective / opposition / stakes / action / turn
  └─ spokenContent[]
       exact text + intent + concise string performanceIntent
          ↓
shot-design
  ├─ subject / action / blocking / camera / performance continuity
  ├─ plannedDurationMs
  └─ spokenContentBindings[] (id + coverageIntent only)
          ↓
  ┌──────────┴──────────┐
  ↓                     ↓
shot-production       audio-production
  ↓                     ├─ CharacterUnderstanding
ad-hoc visual prompt       ├─ VoiceProfile / Casting
  ├─ action              ├─ SceneState
  ├─ pose/gaze/expression └─ rich line PerformanceIntent
  └─ motion/forbidden          ↓
  ↓                     SpeechGenerationRequest
generate_image/video          ↓
  ↓                     Qwen/OpenAI: rich prompt
Visual Provider             Fish validation: speed + volume only
```

### 3.2 生命周期追踪

| Object / semantic | 谁创建 | 时机 | 位置 | 消费者 | 真正到 Provider boundary |
|---|---|---|---|---|---|
| concise `spokenContent[].performanceIntent` | `scene-development` | Scene draft/review | `Scene.content` open JSON；约定为 nonblank string | Shot 仅保留源语义；Audio 理论读取 | 无稳定保证 |
| `CharacterUnderstanding` | `audio-production` | speech preflight | typed transient；嵌入 `VoiceProfile`/request/evidence | Voice Profile / Casting | 不直接；压缩为 stable voice |
| `SceneState` | `audio-production` | 每句 speech 前 | typed transient；嵌入 request；参与 Audio fingerprint | Qwen/OpenAI Audio adapter | YES for Qwen/OpenAI；Fish 实验 NO |
| rich `PerformanceIntent` | `audio-production` Agent run | 每句 speech 前 | untyped `dict[str, Any]`；7.2S-R evidence/request | Qwen/OpenAI adapter | YES for Qwen/OpenAI；Fish 实验仅间接 speed/volume |
| Shot acting/action | `shot-design` | Shot planning | `Shot.content` open JSON | `shot-production` | 编译后 YES |
| Visual prompt / motion prompt | `shot-production` Host/Agent | media generation 前 | transient string；Media 可记 provenance | Visual Provider | YES，但没有 typed acting brief |

### 3.3 关键断点

```text
Scene concise string PerformanceIntent
        ≠
Audio rich dict PerformanceIntent
        ≠
Shot/Visual acting semantics
```

`compile_speech_request()` 会把 `spoken_content.performanceIntent` 原样复制给 `SpeechGenerationRequest.performance_intent: dict[str, Any]`，而 Dialogue convention 和 fixtures 把 Scene field 定义为 string。因此当前 rich request 实际依赖 Agent/fixture 在运行时另造 dict，不是一条由 canonical Scene 自然传播的 typed 链。

## 4. Current Skill Responsibility

- `scene-development`：拥有 Scene 的目标、对抗、行动、转折、canonical Dialogue，并要求每句有 concise playable performance intent；不设计 Shot。
- `shot-design`：拥有 coverage、blocking、camera、reaction、performance continuity、`plannedDurationMs` 与 spoken bindings；不得复制 Dialogue 或 audio timing。
- `shot-production`：把 Shot semantics 编译为 visual constraints/motion prompt，可表达 pose、gaze、expression、posture 和 forbidden outcomes；当前无 typed `VisualActingBrief`。
- `audio-production`：当前同时拥有 Character Understanding、Voice Profile、SceneState、rich line PerformanceIntent、request compilation、speech generation/review/mux；表演导演职责已过度集中在 Audio。

## 5. PerformanceIntent Audit

### 5.1 “当前真实字段”的边界

Repository 中没有 `PerformanceIntent` typed class，因此不存在机器可穷尽的正式字段集。可审计的实际集合是：

1. 7.2S-R 真实 evidence 中的 baseline-plus-delta 字段；
2. Provider compiler 显式识别的字段；
3. tests 中仍存的 legacy `delivery`、top-level `pace`、`pauseAfterMs`。

这一本身就是 contract gap：任意 key 都能进 fingerprint，但 Provider 可能完全忽略。

### 5.2 字段分类

| Current field | 当前含义 | 分类 | 审计结论 |
|---|---|---|---|
| `spokenContentId` | line identity | DERIVABLE | request 已有，不应在 intent 内重复 |
| `baseline.pace` | 稳定语速 | AUDIO_ONLY | 属 Voice Profile / Audio Projection |
| `baseline.energy` | 稳定声音能量 | AUDIO_ONLY | 属 Voice Profile；不是当前表演 core |
| `baseline.containment` | 稳定情绪控制 | UNCLEAR | 与 Voice Profile 和 SceneState 重叠，需 reconciliation |
| `baseline.articulation` | 发音坚定度 | AUDIO_ONLY | Audio Projection |
| `baseline.sentenceFinality` | 基线收句 | AUDIO_ONLY | Voice Profile / Audio Projection |
| `sceneDelta.currentEmotion` | 当前情绪 | SCENE_STATE | 不在 DPD 内复制 mood label |
| `sceneDelta.cause` | 情绪/压力原因 | SCENE_STATE / DERIVABLE | 从 Scene facts 和 SceneState 取得 |
| `sceneDelta.internalActivation` | 内部激活 | CROSS_MODAL | 迁入 DPD core，从 SceneState 变换而来 |
| `sceneDelta.externalExpressiveness` | 外显程度 | CROSS_MODAL | 收敛为 DPD `externalControl` |
| `sceneDelta.urgency` | 当前紧迫 | SCENE_STATE | DPD 应生成可执行行为，不复制标签 |
| `sceneDelta.stress` | 压力 | SCENE_STATE | 保留为 input state |
| `sceneDelta.restraint` | 克制 | CROSS_MODAL | 与 external expressiveness 合并为 `externalControl` |
| `sceneDelta.paceAdjustment` | 本句语速调整 | AUDIO_ONLY | Audio Projection |
| `sceneDelta.volumeAdjustment` | 本句音量调整 | AUDIO_ONLY | Audio Projection |
| `sceneDelta.pausePlan` | 精确口语停顿 | AUDIO_ONLY + CROSS_MODAL DERIVATION | DPD 只保留可选 `pauseFunction`；位置/时长下沉 Audio/Timing |
| `sceneDelta.emphasis` | 词句重音 | AUDIO_ONLY | Audio Projection；Visual 不直接共享 token emphasis |
| `sceneDelta.breathAdjustment` | 呼吸组织 | AUDIO_ONLY | Audio Projection |
| `sceneDelta.sentenceFinalityAdjustment` | 收句变化 | AUDIO_ONLY | Audio Projection |
| `interactionTarget` | 表演互动对象 | CROSS_MODAL | DPD core |
| `speakerObjective` | 当前行动目标 | CROSS_MODAL | DPD core；不得改 Dialogue |
| `subtext` | 可演潜台词 | CROSS_MODAL | DPD optional core |
| `listenerRelationship` | 当前关系/权力结构 | DERIVABLE | 从 Work hierarchy + Scene 派生 `authorityPosition` |
| `immediatePressure` | 当前压力 | SCENE_STATE / DERIVABLE | 不在 DPD 重复散文 |
| `performanceBoundary` | 禁止的表演读法 | CROSS_MODAL | 迁入 DPD，拆为共享与 modality-specific boundaries |
| `delivery` | legacy 单一发声描述 | UNCLEAR / OBSOLETE | 模糊且无法验证，废弃 |
| top-level `pace` | legacy 语速 | AUDIO_ONLY | 迁 Audio Projection，废弃重复形式 |
| `pauseAfterMs` | legacy 精确停顿 | AUDIO_ONLY | 属 Timing/Audio，不属 DPD |

## 6. SceneState Audit

typed `SceneState` 当前字段为：

```text
currentEmotion / emotionCause
internalActivation / externalExpressiveness
urgency / stressLevel
interactionTarget / speakerObjective / subtext / restraint
physicalCondition / presentationMode
unknownFields / evidenceRefs
```

它与 rich PerformanceIntent 有 10 个语义级重复：emotion/cause/activation/expressiveness/urgency/stress/target/objective/subtext/restraint。因此当前边界并未清晰成立。

推荐边界：

```text
SceneState
= 当前客观/证据化条件
  emotion + cause + urgency + stress + physicalCondition + presentationMode

DPD
= 如何把这些条件演成行为
  actingObjective + interactionTarget + authorityPosition
  internalActivation + externalControl + subtext + boundaries
```

`internalActivation/externalExpressiveness/restraint/objective/subtext` 在下一批应明确单一权威位置，不再 SceneState 和 DPD 同时复制。为了兼容现有 `scene-state-v1`，迁移期可读旧字段，但 DPD snapshot 是下游表演决策的唯一权威。

## 7. Character Understanding Boundary

`CharacterUnderstanding` 回答：

> 这个人是谁，通常如何决策、调节情绪、与人互动、承担责任和交流。

DPD 回答：

> 在这一个 Scene/Beat/Line 中，这个人要通过什么可观察的表演行为取得什么结果。

结论：

- DPD 只读经证据审计的 compact Character Understanding summaries；
- DPD 不从姓名、历史评价、职位、年龄或一句台词重建人设；
- UNKNOWN 必须保留，不为了“导演完整”而填满；
- 当前 Character Understanding 方法在 Audio Skill 中，这是 TO-BE 的职责位置 gap：DPD 应消费已有 summary，不应依赖 Audio 生产先运行。

## 8. Creative Voice Casting Boundary

Creative Voice Casting 回答：

> 这个角色长期应该是什么声音。

DPD 回答：

> 这个角色当下如何完成表演行动。

决策：`DPD_READS_CREATIVE_VOICE_CASTING = NO`。

原因：

- Casting 的 vocal age/weight/resonance/texture 对 Visual 没有共享价值；
- 让 DPD 读 Casting 会将表演决策锁定到声学实现；
- 场次表演变化不得导致重新 Voice Casting；
- Role Dubbing Projection 是正确合并点：`DPD + Voice Profile/Casting + Timing → RoleDubbingPerformanceBrief`。

## 9. Cross-modal Performance Gap

Visual 路径并非“完全不能表演”：

- Shot Design 已要求 emotion/energy/attention/orientation/intention continuity；
- Shot Production 已可编译 pose、gaze、expression、posture、body direction、facial micro-expression；
- Batch 5.5 / 6.0 已证明 action/posture/prop/forbidden completion 可进入真实 Visual Prompt。

但缺失的是：

```text
one authoritative performance direction
        ↓                   ↓
same semantic fingerprint   same semantic fingerprint
        ↓                   ↓
Visual Acting Brief         Audio Performance Brief
```

当前 Video 没有读取 7.2S rich Audio PerformanceIntent 的 typed path、contract test 或 fingerprint evidence。Shot Production 规则只有“使用 visible performance intent”的文本要求，不能证明与 Audio 使用同一份导演方案。

```text
CROSS_MODAL_PERFORMANCE_PROPAGATION = MISSING
VISUAL_ACTING_CAPABILITY = PRESENT_UNTYPED
AUDIO_RICH_INTENT_CAPABILITY = PRESENT_PROVIDER_DEPENDENT
```

## 10. DPD Candidate Model

推荐一个 hierarchical typed planning object，而不是 Scene 对象 + Line 对象 + Shot 对象三套 ontology。

```text
DramaticPerformanceDirection
  schemaVersion
  sceneId
  sourceFingerprint
  styleRef?
  sceneDirection
    sceneObjectiveRef
    beatDirections[]
      beatRef
      authorityPosition?
      attentionFocus?
      internalActivation
      externalControl
      performanceBoundaries[]
  lineDirections[]
    spokenContentId
    actingObjective
    interactionTarget?
    authorityPosition?
    subtext?
    internalActivation
    externalControl
    pauseFunction?
    performanceBoundaries[]
  unknowns[]
  evidenceRefs[]
```

精简规则：

- `sceneObjectiveRef` 引用 Scene，不复制 Scene objective 散文；
- `lineDirections` 以 canonical `spokenContentId` 对齐，不拥有 Dialogue text；
- `performanceEnergy` 由 internal activation + external control + beat context 派生，不再建第三个重叠标尺；
- 不含 Fish/Comfy/model/tag/node/MCP/Java 字段；
- 不含相机、音量、呼吸、具体手势、嘴部暴露等 projection 细节。

## 11. DPD Placement Options

| Option | 优点 | 关键缺陷 | 结论 |
|---|---|---|---|
| A: Scene → DPD → Shot | Shot 可根据表演选 coverage/reaction/framing | 未知 Shot/timing 约束，无法生成完整 visual brief | PARTIAL |
| B: Shot → DPD → Production | 知道镜头与时长 | Shot Design 自己缺导演上游；Audio 被 Shot 绑定 | REJECT |
| C: Scene/Beat core → Shot → projection | coverage 有表演依据，projection 又能看 Shot/Timing | 需防止两阶段生成两个互相矛盾的对象 | **RECOMMENDED** |

对 Option C 的约束：

```text
Stage 1 = creative direction core (authoritative)
Stage 2 = modality projection (non-authoritative derivative)
```

Stage 2 不得改 acting objective/subtext/authority/internal-external shape。如 Shot/Timing 无法执行 core，应返回明确 re-plan，不得悄悄改导演方案。

## 12. Independent Skill Decision

推荐 `NEW SKILL: dramatic-performance-direction`，理由：

- 它是 Audio 与 Visual 的共同上游，不应由任一 modality 拥有；
- Scene Skill 已拥有剧作事件、Dialogue 和 state transition，再加 actor direction 会职责膨胀；
- Shot Skill 必须消费表演方向才能选择 reaction/coverage，不能同时是唯一生成者；
- Audio Skill 拥有 DPD 会使 Visual 永久依赖 Audio workflow；
- 一个小型 Skill 比在四个旧 Skill 中维护隐式对齐 prompt 更精简。

新 Skill 仍必须是 `SKILL.md + skill.yaml` 的 platform-neutral core，不应生成新 MCP Tool。

## 13. DPD Field Audit

### 13.1 候选字段判定

| Candidate | 判定 | 位置/理由 |
|---|---|---|
| `speakerObjective` | REQUIRED | DPD core；表演行动的目标 |
| `interactionTarget` | REQUIRED_WHEN_APPLICABLE | DPD core；独白/旁白可空 |
| `dramaticFunction` | DERIVABLE | 由 Scene line `intent` + objective 派生，不重复 |
| `authorityPosition` | REQUIRED_WHEN_RELATIONAL | DPD core；可执行的当下权力位置 |
| `addressingMode` | DERIVABLE | 从 target + hierarchy + authority 派生 |
| `interactionAsymmetry` | DERIVABLE | 与 authorityPosition 重叠 |
| `internalActivation` | REQUIRED | DPD core |
| `externalControl` | REQUIRED | DPD core；取代 restraint + externalExpressiveness 重叠 |
| `performanceEnergy` | DERIVABLE | 由 activation/control/beat 派生，避免第三条轴 |
| `phraseAttack` | OPTIONAL | Audio Projection，仅台词需要时 |
| `rhetoricalDrive` | OPTIONAL | Audio Projection；不是每句必需 |
| `pauseFunction` | OPTIONAL | DPD core 只留“为何停”；时长/位置由 Timing/Audio |
| `emphasisStructure` | OPTIONAL | Audio Projection |
| `sentenceClosure` | OPTIONAL | Audio Projection |
| `breathSupport` | NOT_NEEDED_IN_CORE | stable Voice/Audio Projection |
| `spatialProjection` | NOT_NEEDED_IN_CORE | Audio Projection，由空间与 addressing 派生 |
| `physicalStillness` | OPTIONAL | Visual Projection |
| `posture` | OPTIONAL | Visual Projection |
| `gazeTarget` | OPTIONAL | Visual Projection，由 target/Shot blocking 派生 |
| `gazeStability` | TOO_DETAILED | 由 gaze target + external control 编译 |
| `gestureEconomy` | OPTIONAL | Visual Projection |
| `facialTension` | OPTIONAL | Visual Projection |
| `headMovement` | TOO_DETAILED | Provider/Shot-specific 编译 |
| `bodyOrientation` | OPTIONAL | Visual Projection，受 Shot blocking 约束 |

### 13.2 价值中立

DPD 只描述 action/control/relationship/observable behavior。`hero`、`villain`、忠奸、勇懦、伟大、平庸等不得是 field 值或 prompt shortcut。“权力感”应翻译为 target 明确、停顿功能、外显控制、动作经济和决策性收束等可执行语义。

## 14. Historical Drama Performance Style Guide

推荐两层，不是四选一：

```text
Skill reference
  = 通用 historical dramatic performance grammar
    (清晰、有支撑、停顿有功能、身份关系明确、动作有目的)

optional Work.content.performanceStyleGuide
  = 该作品特有的表演语言与偏离项
```

不推荐 Host config：它不能稳定跨机器传播，也不是运行配置。Script 可消费 Work setting，但不应复制一份独立 style 真源。

现有 `Work.content` 是 open JSON，Work Skill 已把 tone/type/audience/period 视为创作约束，因此 optional Work-level setting 无需 Java field 或 DB migration。

生产规则只写抽象方法，禁止“模仿某剧/某演员/某角色”。Style Guide 不能覆盖 Character Understanding，不能使所有角色都同样慢、重或威严。

## 15. Audio Projection

权威边界：

```text
audio-production / future Role Dubbing Workflow
  consumes:
    DramaticPerformanceDirection
    approved Voice Profile / Creative Voice Casting
    Timing Plan
  produces:
    RoleDubbingPerformanceBrief
  ↓
Provider adapter
  compiles Fish/Qwen/future-provider syntax
```

DPD Skill 不应生成 Fish-ready prompt；Fish adapter 不应重新解释角色目标或潜台词。

`RoleDubbingPerformanceBrief` 可包含：

```text
spokenContentId
actingObjective / interactionTarget / authorityPosition
internalActivation / externalControl / subtext?
phraseAttack? / rhetoricalDrive? / pausePlan?
emphasisStructure? / sentenceClosure? / breathAdjustment?
targetTimingPolicy
performanceBoundaries[]
performanceDirectionFingerprint
```

当前 Provider 边界对比：

- Qwen Audio 已编译 emotion/activation/expressiveness/restraint/urgency/pace/volume/emphasis/finality/objective/subtext，但输入仍是 open dict；
- OpenAI 把完整 dict 序列化进 instructions，缺少能力选择与长度精简；
- Fish 本次 Directed 实验只真正发送 `prosody.speed` 和 `prosody.volume`，其 evidence 中的 richer brief 没有进 Provider payload。

## 16. Visual Projection

`VisualActingBrief` 应由 `shot-production` 产生，而不是 Shot Design 或 DPD Skill。

理由：

- DPD Skill 生成的是跨模态 creative core，不知最终镜头约束；
- Shot Design 使用 DPD 选 coverage/blocking/framing，但不生成 production prompt；
- Shot Production 已拥有 stable facts + Shot delta + provider capability 的编译位置，可将 DPD + Shot + Timing 压缩成 brief。

建议 brief：

```text
shotId / subject / activeSpeaker?
interactionTarget / authorityPosition
internalActivation / externalControl
gaze / posture / gesture / facial tension / body orientation
physicalStillness / allowed movement
required visible evidence / forbidden acting outcome
lipSync guidance when required
performanceDirectionFingerprint
```

当前 `production.generate_image/video` 只接收 string prompt + generic parameters，没有 typed VisualActingBrief 输入。能力上可表达上述行为，contract 上则缺少可验证 projection/fingerprint：

```text
VISUAL_PROMPT_CAN_EXPRESS_ACTING = YES
TYPED_VISUAL_ACTING_BRIEF = MISSING
```

## 17. Lip-sync-friendly Visual Acting

当 `lipSyncRequired=true`，Visual Projection 应自动增加：

```text
active speaker face visible
mouth unobstructed
stable identity
limited unnecessary head rotation
sufficient face size
avoid uncontrolled pre-existing mouth movement
```

这些是 **transient visual production guidance**，不是默认 Shot Domain content。原因：

- 它们由特定后期 workflow 能力而不是剧作/镜头语义产生；
- 同一 Shot 可生成无 Lip Sync 或不同 Lip Sync Provider 的版本；
- 持久化到 Shot 会让 camera/acting 被当前技术过早锁死。

如 lip-sync guidance 与已审 Shot 的反应镜头、遮挡或构图目标冲突，必须在付费生成前返回 Shot/Timing re-plan，不得悄悄改镜头含义。

Lip Sync workflow 只需 `activeSpeaker + speechWindow + faceTarget? + performanceDirectionFingerprint`用于 provenance/QC，不应重新解释 DPD 或更改表演。

## 18. Timing / Ordering

DPD Stage 1 不应知道物理 `speechWindow`或强制 `targetDurationMs`。它可读 Scene 的 `estimatedDurationMs` 作为语言经济性软约束，但不决定时间线。

无循环顺序：

```text
1. Approved Scene + canonical Dialogue + estimatedDurationMs
2. Character Understanding summaries
3. DPD core (Scene/Beat/Line; no Shot and no speechWindow)
4. Shot Design (consumes DPD; owns coverage + plannedDurationMs)
5. transient Timing Plan (speechWindow / activeSpeaker / lipSyncRequired)
6. Audio Projection + Visual Projection (do not mutate DPD core)
7. Role Dubbing + Raw Visual production
8. measured duration fit
9. Lip Sync
10. Audio Post / Final AV
```

不产生循环的原因：

- DPD 只决定表演意图，不解时间线；
- Shot Design 在 DPD 指导下决定 coverage 和计划时长；
- Timing 只将已审的 Scene/Shot 决定放入窗口；
- Projection 只转译，不改 core；
- 无法 fit 时返回显式 re-plan gate，不是隐式反向改写。

## 19. Persistence / Fingerprint

### 19.1 选项对比

| Option | 跨 Host | Audio/Video 重生成 | Review | stale detection | 结论 |
|---|---|---|---|---|---|
| Transient only | FAIL，LLM 再生成可漂移 | 无法保证同方案 | 难追溯 | 弱 | REJECT |
| Snapshot in open content | PASS | 可重用同一 core | 可对比 | 可 fingerprint | **RECOMMENDED** |
| New Domain Entity | PASS | PASS | PASS | PASS | 当前过重，DEFER |

### 19.2 推荐生命周期

- `Scene.content.performanceDirectionSnapshot`：一份 compact、versioned、hierarchical core；
- 不在每个 Shot 复制 DPD；
- Audio/Raw Video/Lip-synced/Final AV Media 记录 `performanceDirectionFingerprint` 和 `performanceDirectionVersion`；
- modality brief 可在对应 Media provenance 保留 compact snapshot/hash，不反写 Scene/Shot；
- Scene/Dialogue/Character summary/Style 的 material change 改变 source fingerprint，旧 DPD 变 stale。

建议 fingerprint：

```text
performanceDirectionFingerprint = SHA-256(canonical JSON of:
  schemaVersion
  sceneId
  sourceFingerprint
  styleFingerprint
  sceneDirection material values
  lineDirections material values)
```

display text、排序无关的 evidence refs、生成时间不应影响“同一导演方案”指纹。

## 20. Review Boundary

默认：

```text
DPD auto-generation + contract validation
  ↓
Shot Review / Duration Feasibility
  ↓
Audio Review + Visual Review
```

不新增强制 `PERFORMANCE_DIRECTION_REVIEW`。原因是 DPD 是中间 planning artifact，当前尚无证据表明每个 Scene 都值得多一道人工审批。高成本/高风险场景可由 Host 策略选择性预览，但不建新审批 Domain。

分离规则：

- DPD review/revision 不得改 approved Voice Casting；
- Voice Casting review 不得重写 DPD；
- DPD 不拥有 Dialogue text，台词需改时返回 Script/Scene revise；
- Lip Sync 只消费 reviewed Audio + Raw Video + Timing/active speaker，不作 DPD review。

## 21. Tool / MCP Impact

```text
NEW_DPD_TOOL = NOT_NEEDED
DRAMA_MCP_SERVICE_CHANGE = NONE
```

DPD 是 Skill-local planning/reasoning：读取现有 Work/Scene/Shot context，用 typed transient contract 验证，需要 snapshot 时复用 `scene.save_scene`。没有远程能力、专有计算或必须由 MCP 提供的状态，因此 `production.generate_performance_direction` 会是无必要 Tool。

`drama-mcp-service` 继续只投影通用 Tool catalog。不得加 director logic、acting logic、Fish logic 或 video acting logic。

## 22. drama-service Impact

```text
NEW_JAVA_DOMAIN = NO
DB_MIGRATION = NONE
```

代码证据：

- Work/Script/Episode/Scene/Shot 的 Python contract 都使用 `content: dict[str, Any]`；
- Java DTO/entity 使用 `JsonNode content`；
- MySQL `drama_scene`、`drama_shot`、`drama_media` 已有 JSON content；
- `Media.content` 也是 open JSON，`sourceRef` 与 hash 机制已可承载 provenance/stale semantics。

因此 compact Scene snapshot 与 Media fingerprint 都可用现有能力表达。本审计不执行任何写入。

## 23. Media Provenance

| Media | `performanceDirectionFingerprint` | `performanceDirectionVersion` | 结论 |
|---|---|---|---|
| Dialogue Audio / Role Dubbing | NEEDED | NEEDED | 证明使用哪份表演方案；参与 stale detection |
| Raw Video | NEEDED | NEEDED | 与 Audio 验证 same direction |
| Lip-Synced Video | NEEDED_INHERITED | NEEDED | 不重新解读，继承 Audio/Video 输入指纹；不一致则拒绝 |
| Shot Dialogue Mix | NEEDED_INHERITED | NEEDED | 继承所用 clips 指纹 |
| Final AV | NEEDED_INHERITED | NEEDED | 支持全链 stale 追踪 |
| Character Master / Voice Reference | NOT_NEEDED | NOT_NEEDED | 属稳定身份/声音，不属 Scene 表演 |

## 24. AS-IS vs TO-BE

### 24.1 AS-IS

```text
Scene
  ├─ dramatic facts/action/turn
  └─ line performanceIntent: string
       ↓                         └─ weak/implicit inheritance
Shot Design                              ↓
  └─ coverage/action              Visual Prompt
       ↓
Visual Production

Scene + Work + Shot
       ↓
Audio Production independently creates
Character Understanding + SceneState + rich PerformanceIntent
       ↓
Qwen/OpenAI prompt OR Fish speed/volume
```

### 24.2 TO-BE Candidate

```text
Work / Script / Episode / Approved Scene
                 ↓
       Character Understanding summaries
                 ↓
 [NEW] Dramatic Performance Direction core
      Scene / Beat / Line, one fingerprint
                 ↓
             Shot Design
                 ↓
       transient Production Timing Plan
          ┌─────────┴─────────┐
          ↓                   ↓
 Visual Acting Brief     Role Dubbing Performance Brief
 (shot-production)       (audio-production/workflow)
          ↓                   ↓
      Raw Video          Dialogue Audio
          └─────────┬─────────┘
                    ↓
                 Timing Fit
                    ↓
                  Lip Sync
                    ↓
             Audio Post / Final AV
```

59 号 `TIMELINE_FIRST_HYBRID` 不被推翻；DPD 只是在 Shot/Timing 前补齐跨模态 creative direction。

## 25. PerformanceIntent Migration Matrix

| Current field/group | Migration | Target |
|---|---|---|
| Scene concise string `performanceIntent` | KEEP_TEMPORARILY → DEPRECATE | 迁移期作 seed/compatibility；DPD snapshot 成为权威 |
| `spokenContentId` inside intent | DEPRECATE | DPD line key / request top-level |
| `baseline.pace/energy/articulation/sentenceFinality` | AUDIO_PROJECTION | Voice Profile + RoleDubbingPerformanceBrief |
| `baseline.containment` | DEPRECATE_DUPLICATE | Voice Profile stable containment 或 DPD externalControl，二选一 |
| `currentEmotion/cause/urgency/stress` | KEEP | SceneState input，不复制到 DPD |
| `internalActivation` | MOVE_TO_DPD | cross-modal core |
| `externalExpressiveness/restraint` | MOVE_TO_DPD + RECONCILE | 合并为 `externalControl` |
| `paceAdjustment/volumeAdjustment` | AUDIO_PROJECTION | Role Dubbing brief / Provider compiler |
| `pausePlan` | SPLIT | DPD `pauseFunction?` + Audio/Timing exact plan |
| `emphasis/breathAdjustment/sentenceFinalityAdjustment` | AUDIO_PROJECTION | Role Dubbing brief |
| `interactionTarget/speakerObjective/subtext` | MOVE_TO_DPD | line direction core |
| `listenerRelationship` | DERIVE_IN_DPD | Work hierarchy + Scene → authorityPosition |
| `immediatePressure` | DEPRECATE_DUPLICATE | SceneState/Scene stakes |
| `performanceBoundary` | MOVE_TO_DPD + SPLIT | shared boundaries + Audio/Visual projection boundaries |
| legacy `delivery` | DEPRECATE | 模糊单标签 |
| legacy top-level `pace` | AUDIO_PROJECTION | 统一为 pace adjustment |
| legacy `pauseAfterMs` | DEPRECATE / TIMING | transient Timing/Audio plan |

总结：

```text
CURRENT_PERFORMANCE_INTENT_DECISION = SPLIT_AND_MIGRATE
NOT = KEEP_AS_ONE_SUPER_OBJECT
```

## 26. Responsibility Matrix

### 26.1 AS-IS

| Responsibility | scene-development | shot-design | shot-production | audio-production | proposed DPD |
|---|---|---|---|---|---|
| Scene dramatic objective | OWNS | INHERITS | CONSUMES | CONSUMES | N/A |
| Character state | OWNS narrative facts | PRESERVES continuity | COMPILES visible state | DERIVES typed SceneState | N/A |
| Performance acting | concise line string | coverage + continuity | ad-hoc visual compile | rich line intent owner | N/A |
| Voice casting | NONE | NONE | legacy call only | OWNS | N/A |
| Audio performance | NONE | duration context only | may invoke legacy audio | OWNS | N/A |
| Visual acting | playable action only | OWNS blocking/expression continuity | OWNS prompt compilation | NONE | N/A |
| Camera coverage | NONE | OWNS | CONSUMES | context only | N/A |
| Timing | line estimate | planned duration | provider duration compile | target/actual/mux | N/A |
| Provider translation | NONE | NONE | Visual boundary | Audio adapters | N/A |

### 26.2 TO-BE

| Responsibility | scene-development | shot-design | shot-production | audio-production | proposed DPD |
|---|---|---|---|---|---|
| Scene dramatic objective | OWNS | INHERITS | CONSUMES | CONSUMES | REFERENCES |
| Character state | OWNS facts | PRESERVES | CONSUMES projection | CONSUMES | CONSUMES, DOES_NOT_REBUILD |
| Performance acting | supplies canonical intent/action | CONSUMES core | projects Visual | projects Audio | **OWNS CORE** |
| Voice casting | NONE | NONE | NONE | **OWNS/CONSUMES APPROVED** | NONE |
| Audio performance | NONE | timing/coverage context | NONE | **OWNS PROJECTION** | supplies core |
| Visual acting | scene action input | coverage/blocking | **OWNS PROJECTION** | NONE | supplies core |
| Camera coverage | NONE | **OWNS** | CONSUMES | context only | NONE |
| Timing | estimate | planned duration | consumes Timing Plan | consumes Timing Plan | no physical timing ownership |
| Provider translation | NONE | NONE | **Visual provider boundary** | **Audio provider boundary** | NONE |

## 27. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| 过度导演导致表演僵硬 | 模型机械执行过多细节 | minimal core；optional fields；不定义 50-field ontology |
| Audio/Video projection 不一致 | 两个角色表演 | 同一 fingerprint；projection contract tests；shared core immutable |
| Provider 无法执行复杂 acting | prompt 被忽略/失真 | capability-aware projection；过细字段下沉；失败即 review/re-plan |
| DPD prompt 过长 | 成本高、关键语义丢失 | typed compact core；provider boundary 有界压缩 |
| 角色表演同质化 | 角色差异被 style 覆盖 | Character Understanding summaries + explicit unknowns；Style 只是 grammar |
| 历史剧风格覆盖人物差异 | 人人慢/重/威严 | Work-level deviations；禁止 style-to-pace/authority shortcut |
| 动态表演破坏 Voice identity | 每 Scene 声线漂移 | DPD 不读/不改 Casting；Audio Projection 相对 stable Voice 调整 |
| Video acting 与 Lip Sync 冲突 | 嘴部遮挡/转头/预存嘴动 | transient lip-sync visual guidance；生成前 feasibility gate |
| DPD stale propagation | 新 Dialogue/Scene 使用旧方案 | source fingerprint + Media provenance + canonical stale check |
| 跨 Host 重生成不一致 | macOS/Windows 漂移 | compact Scene snapshot；不依赖上一次 Agent memory |
| Skill responsibility explosion | Scene/Shot/Audio 互相重写 | DPD 只拥有 core；projection 回到 modality owners |
| SceneState/DPD 字段重复 | 指纹与执行漂移 | P0 reconciliation；定义单一权威 |
| snapshot 污染 Scene | open content 被巨型证据填满 | 只存 compact material values/fingerprints；evidence 保持精简 |

## 28. P0 / P1 / Deferred

### P0 — DPD Contract/Foundation

1. 新建 platform-neutral `dramatic-performance-direction` Skill + `skill.yaml`；
2. 定义小型 typed transient `DramaticPerformanceDirection`；
3. 冻结 compact Scene snapshot/source fingerprint/direction fingerprint convention；
4. reconciliation 现有 Scene string PerformanceIntent、SceneState 与 Audio rich dict；
5. 定义 typed/mock `RoleDubbingPerformanceBrief` 与 `VisualActingBrief`；
6. 加 offline contract tests：同 core 产生同 fingerprint，Audio/Visual 共享必要语义，不泄漏 modality/provider 字段；
7. 更新旧 Skill 职责边界，但不调用 Provider。

### P1 — Projection Integration

1. Shot Design 消费 DPD core 的 coverage/reaction/continuity；
2. Timing Plan 消费 Scene estimates + planned duration；
3. Audio Production/Role Dubbing 消费 Audio brief；
4. Shot Production 消费 Visual brief；
5. Audio/Raw Video Media 记录 fingerprint/version；
6. 先做 mock/synthetic single-Scene integration，再单独授权真实 Provider E2E。

### Deferred

- DPD database/entity/CRUD Tool；
- automatic acting scoring / LLM judge；
- pose tracking / gesture recognition / facial-action ontology；
- 复杂 style preset library；
- 自动人工审批系统；
- 精确手势/眼动/头动时间线；
- Provider capability knowledge 持久化到 DPD；
- 自动跨模态表演质量评分。

## 29. Next Minimal Implementation Batch

```text
NEXT_MINIMAL_IMPLEMENTATION_BATCH
= dramatic-performance-direction Skill
  + typed transient contract
  + current PerformanceIntent / SceneState reconciliation
  + compact snapshot/fingerprint convention
  + mock Audio/Visual projections
  + offline tests
```

下一批不应直接做真实 Single-Scene E2E。原因：

- 当前 Scene string 与 Audio dict 已有 contract mismatch，应先确定权威和迁移；
- Fish 当前只消费 speed/volume，直接真实生成无法区分 DPD 质量与 adapter 能力问题；
- Visual 只接 string prompt，需先有可测的 projection；
- 先用 mock 证明 same direction 到达两个边界，再付费验证 Provider，故障定位更清晰。

## 30. Final Recommendation

### Q1 — DPD 是否需要独立 Skill？

**YES。** 它是跨 Audio/Visual 的 creative planning responsibility，不应继续隐藏在 Audio Skill 或分散在 Scene/Shot prompts。

### Q2 — 位于 Scene 后、Shot 后还是 two-stage？

**Option C / two-stage use。** Scene 后生成一份 authoritative core；Shot/Timing 后生成 derivative projections，不创建第二份导演真源。

### Q3 — 当前 PerformanceIntent 如何处理？

**SPLIT_AND_MIGRATE。** Cross-modal 字段进 DPD，state 字段留 SceneState，audio controls 进 Audio Projection，legacy loose keys 废弃。

### Q4 — DPD 与 Character Understanding 的边界？

Character Understanding 是 stable person understanding；DPD 是 current dramatic acting decision。DPD 只消费 summary，不重做人设分析。

### Q5 — DPD 与 Creative Voice Casting 的边界？

DPD 不读、不改、不评审 Voice Casting。Audio Projection 才合并 DPD 与 approved stable voice。

### Q6 — Audio 和 Video 共享哪些最小语义？

```text
actingObjective
interactionTarget
authorityPosition
internalActivation
externalControl
subtext? / pauseFunction?
performanceBoundaries
```

`performanceEnergy` 可从 activation/control 派生，不强制存储。

### Q7 — Visual Acting Brief 如何进入 Shot Production？

Shot Production 用 `DPD core + approved Shot + Timing Plan` 产生 transient typed brief，再编译为当前 string visual/motion prompt；Media 记录 direction fingerprint。

### Q8 — Role Dubbing Brief 如何进 Fish / future Provider？

Audio Production/Role Dubbing Workflow 用 `DPD + Voice/Casting + Timing` 生成 provider-neutral brief；Fish/future adapter 在 Provider boundary 做能力选择和语法编译。

### Q9 — DPD 应 transient、snapshot 还是新 Domain？

**Snapshot in existing Scene open content。** 运行时使用 typed object，跨 Host 使用 compact snapshot，Media 保存 fingerprint/version；不建新 Domain。

### Q10 — 下一批最小实现是什么？

**Skill + typed contract + reconciliation + snapshot/fingerprint + mock projections + offline tests。** 暂不调 Fish，不调 Video Provider，不做 Lip Sync，不做真实 Scene E2E。

### Static Verification / Git Safety

| Verification | Result |
|---|---|
| drama-plugin full pytest | `174 passed in 1.52s` |
| drama-plugin strict mypy | `Success: no issues found in 46 source files` |
| drama-mcp-service pytest | `18 passed in 0.96s` |
| drama-mcp-service strict mypy | `Success: no issues found in 4 source files` |
| drama-service Maven tests | current concurrent snapshot: `49 tests, 0 failures/errors/skips` |
| 4 current Skill quick validations | all `Skill is valid!` |

`drama-plugin/.venv` 在当前 Host 不含 pytest/mypy，因此 Plugin 测试复用了已存在的 `drama-mcp-service/.venv` 并显式指定 `PYTHONPATH/MYPYPATH`；没有安装依赖。Java 测试使用当前 Host 已存在的 IntelliJ 内置 Maven。

Git 安全记录：

- 开始时 `drama-plugin` 已有 61 号 Fish 批次的未提交代码/测试/报告，本批不修改它们；
- 本批在 `drama-plugin` 唯一新增是本 62 号报告；
- `drama-mcp-service` 开始和结束均 clean；
- `drama-service` 开始时 clean，审计进行期间出现 Voice/Media Storage 相关并发未提交修改；本批未参与、修改、覆盖或回滚这些并发用户修改。表中 Maven 结果是结束前对当时工作树的重跑快照。

### Final Status

```text
CROSS_MODAL_DPD_AUDIT = COMPLETE

DPD_IMPLEMENTATION = NOT_STARTED

NEW_SKILL_CREATED = NO
NEW_TOOL_CREATED = NO
DB_MIGRATION = NONE

FISH_REAL_CALLS = 0
VIDEO_REAL_CALLS = 0
LIP_SYNC_CALLS = 0

PRODUCTION_CODE_CHANGES = NONE

NEXT_BATCH = PROPOSED_ONLY
```

到此停止。不根据本审计自动开始实现。
