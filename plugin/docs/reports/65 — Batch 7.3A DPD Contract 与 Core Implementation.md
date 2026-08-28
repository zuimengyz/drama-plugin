# 65 — Batch 7.3A DPD Contract 与 Core Implementation

日期：2026-08-28（Asia/Shanghai）  
批次：Batch 7.3A — Dramatic Performance Direction Contract & Core Implementation  
结论：`BATCH_7_3A = PASS`

## 1. 执行摘要

本批先重读 62 号 DPD 架构审计并追踪当前 Scene/Dialogue/Audio/Shot Skill、typed Audio contracts、fingerprint、Role Dubbing adapter 与 tests，随后实现独立、可重放、Provider/Modality/Host-neutral 的 DPD Core。

交付包括 `SceneDPD → BeatDPD → LineDPD → EffectiveDPD → DPDSnapshot`、显式继承/覆盖/reset/list/reference 规则、canonical SHA-256 fingerprint、严格版本与 extra-field 校验、三上下文同一句对白 fixture、独立 `dramatic-performance-direction` Skill 和兼容文档。

本批未实现 Audio/Visual Projection，未修改 Provider payload，未调用 TTS/Image/Video，未新增 Tool、Java Contract、服务、数据库或持久化流程。

## 2. 本批次范围

已完成：

- DPD Core typed contract、composer、validation、snapshot、fingerprint；
- Scene/Beat/Line 三层语义与 deterministic merge；
- independent DPD Skill Core；
- 7.2S `SceneState` / `performanceIntent` 兼容边界说明；
- deterministic fixture、contract/neutrality/regression tests；
- plugin 与 MCP 全量回归。

明确未开始：

- Batch 7.3B Audio Projection；
- Visual/Animation/Motion/Facial/Camera projection；
- real TTS、Image、Video、Lip Sync；
- DPD persistence lifecycle、Java/DB/API/MCP CRUD。

## 3. 开始前架构审计

真实 AS-IS：

```text
Scene.content.spokenContent[].performanceIntent (concise string)
                         ≠
SpeechGenerationRequest.performanceIntent (open dict)
                         +
SceneState (typed, but overlaps target/objective/activation/subtext)
                         ↓
Audio adapters / Role Dubbing

Shot Design / Production
  └─ separate untyped visible action/performance language
```

审计结论：当前没有 typed DPD。Audio 层承担了过多当下表演导演语义；Visual 能表达表演，但没有与 Audio 共用的 authoritative snapshot。`compile_speech_request()` 仍把 Scene 的 `performanceIntent` 原样复制进 open dict，旧 Dialogue convention 又将其定义为 string，证明它不能直接升格为 Core contract。

DPD 的正确位置是独立 Skill Core / Agent-side deterministic intermediate representation。它不是 Runtime、Provider Adapter、业务 Entity 或 transport contract。

## 4. 发现的旧结构与重复结构

| 结构 | 真实现状 | 7.3A 决策 |
|---|---|---|
| `CharacterUnderstanding` | typed、evidence-scoped、稳定人物理解 | KEEP；只作上游 context，不复制进 DPD |
| `CreativeVoiceProfile` / Casting | 稳定声音身份与 Provider materialization | KEEP；DPD 不读取 Casting |
| `SceneState` 客观状态 | emotion/cause/urgency/stress/physical/presentation | KEEP |
| `SceneState` activation/expressiveness/target/objective/subtext/restraint | 与 DPD 重叠 | COMPATIBILITY；未来迁移后 deprecated |
| Dialogue string `performanceIntent` | concise、provider-neutral but untyped | COMPATIBILITY；不扩张 |
| Audio rich `performanceIntent` dict | baseline + scene delta；包含 cross-modal 与 Audio controls | SPLIT recommendation；7.3A 不破坏现链 |
| legacy `delivery` / top-level `pace` / `pauseAfterMs` | 模糊或 Audio-only | future deprecation recommendation |
| Shot action/performance continuity | 可见表演语义但未 typed 对齐 | 保留；未来消费同一 DPD fingerprint |

## 5. DPD 最终职责定义

DPD 回答：当前角色为什么行动、对谁行动、受什么阻碍、采用什么策略、处于什么权力/关系位置、内部激活与外部控制如何组合，以及期望形成什么可观察戏剧结果。

DPD 不回答：声音速度/音高/音量/呼吸/发音/精确停顿，身体姿态/视线/手势/走位，镜头/构图，Provider prompt/model/parameter，或 Runtime/HTTP/storage 配置。

## 6. Scene / Beat / Line Contract

`SceneDPD` 拥有：source fingerprint、dramatic purpose、conflict condition、power structure、public/private context，以及仅在物质上必要的 climate/urgency/information/social constraints。

`BeatDPD` 拥有：current actor、obstacle、transition trigger 与 sparse direction delta。composition 后必须得到 target/objective/tactic/authority/relationship/activation/control。

`LineDPD` 只引用 canonical `spokenContentId` 与 speaker，不复制台词文本；它拥有 dramatic action、observable intent、continuity、change from previous 和真实 line override。

三个输入 scope 都使用 `schemaVersion=dpd-v1`；snapshot 使用 `dpd-snapshot-v1`，effective output 使用 `dpd-effective-v1`。

## 7. 继承与覆盖规则

```text
Scene base → Beat override → Line override
```

- missing：继承最近父层；
- missing / explicit `null`：均为继承；这保证默认 JSON round-trip 不会把序列化出的 null 误当覆盖；v1 不提供 scalar reset；
- list：`performanceBoundaries` replace-whole，不 append；missing 继承，空 list 清空；
- conflict：低层 deterministic 胜出，不进行 prompt merge；
- identity conflict：`sceneId` / `beatId` 不一致立即失败；
- empty direction object：立即失败；
- snapshot deep-copy 三层输入，调用者后续修改不能污染快照。

## 8. Character / DPD 边界

Character Profile/Understanding 描述相对稳定的人物身份、经历、决策、关系与调节方式。DPD 只保留 actor/speaker stable key，并决定当前 Scene/Beat/Line 的动作。年龄、官职、传记、长期人格、Voice Profile 与 Casting 不复制到 Line DPD。

历史身份/礼制/等级可作为上游 constraint 影响 authority、control、relationship 或 tactic；DPD 不重新检索史料，也不裁决史实。

## 9. Audio Projection 边界

DPD Core 可表达 objective、target、tactic、authority、relationship、activation、control、subtext、boundary 与 observable intent。

pace、rhythm、pause placement/duration、intensity mapping、breath、voice pressure、articulation、prosodic emphasis、pitch、volume、Voice ID 与 provider prompt 全部留给 7.3B Audio Projection。

7.3A 没有把 `DPDSnapshot` 接入 `SpeechGenerationRequest`，没有修改 Fish/Qwen/OpenAI adapter 行为，也没有真实 Audio E2E。

## 10. Visual Projection 边界

DPD 可以描述 “controlled intimidation”“conceal uncertainty”“test the opponent”，但 gaze、posture、facial tension、gesture、distance、blocking、head angle 与 camera/framing 均未进入 contract。Visual Projection 尚未开始。

## 11. Snapshot / Fingerprint 设计

`DPDSnapshot` 同时保存 Scene/Beat/Line validated source layers、flattened effective result 和 fingerprint。它使未来 Projection 消费确定输入而不是重新解释完整剧本。

Fingerprint 复用从 Audio foundation 上移到通用 contract base 的 canonical JSON + SHA-256 实现；Audio public import 保持兼容。material 输入只含 schema 与三层/effective contract，不含时间、随机 UUID、Host、Provider result 或 fingerprint 自身。

## 12. 实际修改文件

新增：

- `plugin/src/drama_plugin/contracts/dpd.py`
- `plugin/src/drama_plugin/dpd/__init__.py`
- `plugin/src/drama_plugin/dpd/core.py`
- `plugin/skills/dramatic-performance-direction/SKILL.md`
- `plugin/skills/dramatic-performance-direction/skill.yaml`
- `plugin/skills/dramatic-performance-direction/agents/openai.yaml`
- `plugin/docs/dpd-core-contract.md`
- `plugin/tests/fixtures/dpd-core-v1.yaml`
- `plugin/tests/test_dpd_core.py`
- 本报告

兼容更新：通用 fingerprint utility、contract exports、Skill registry expectations、Plugin skill count、两级 README、Dialogue/Audio convention 与 scene-aware Audio reference。

未修改：`drama-service`、`drama-mcp-service` 生产代码、Runtime env、Provider config、storage、DB schema、Audio/Visual Provider payload。

## 13. 删除 / Deprecated 内容

生产 contract 未做 destructive delete。现有 `SceneState` 与 `performanceIntent` 保持可运行。

仅记录未来 deprecated 建议：DPD 投影正式接管后，逐步移除 `SceneState` 中跨模态重复字段与 legacy `delivery` / top-level `pace` / `pauseAfterMs`；迁移不得与 7.3A 合并执行。

## 14. 测试结果

| 验证 | 结果 |
|---|---|
| DPD + Skill + Audio targeted regression | 71 passed |
| drama-plugin full pytest | 152 passed |
| drama-plugin strict mypy | PASS（47 source files） |
| Skill quick validation | PASS |
| drama-mcp-service full pytest | 24 passed |
| drama-mcp-service strict mypy | PASS（4 source files） |
| lint / formatter command | NOT PRESENT（项目未配置） |
| Java tests | NOT APPLICABLE（无 Java 变更/依赖） |
| real Provider calls | 0 |

## 15. Deterministic Fixture 结果

同一句 `你可知道后果？`、同一 `spokenContentId` 在三种关系中得到三个不同 effective DPD：

| Case | Action | Activation / Control | Fingerprint |
|---|---|---|---|
| superior → subordinate | `warn` | HIGH / HIGH | `25a6510f58f378486f4f6e82c7a7dbdf037c5976d00f326599c3776c296c5b4c` |
| peer → peer | `probe` | MEDIUM / HIGH | `ffa45d47713a661859d4990780351c777e383d4e7c46f12bb26c2e012a4c3743` |
| subordinate → superior | `caution` | HIGH / HIGH | `9b8a17e9efa8c454eeec38f8f61d39816ce36ee70eb50146ae5b75dcf9ae0524` |

测试同时证明：相同 input/reordered mapping fingerprint 相同；line action 改变 fingerprint；line override 不污染 Scene/Beat；unknown Provider/Audio/Visual field fail fast。

## 16. Complexity Audit

| 指标 | 结果 | 判定 |
|---|---:|---|
| 可继承 direction fields | 10 | 保留；覆盖核心行为且可显式 merge |
| enums | 1（LOW/MEDIUM/HIGH） | 最小 vocabulary |
| contract classes | 7 | 3 layers + sparse state + effective + snapshot + 1 enum |
| public helpers | 3 | compose effective / compose snapshot / fingerprint |
| DPD production files | 3 | contracts + core + public export |
| abstraction depth | contracts → composer | 2 层，无 service/repository/adapter |

`confidence`、独立 risk field、独立 information-position field、emotion taxonomy、pause function、projection fields、style ontology、migration framework 均因当前没有不可替代的 fixture 需求而未加入。`EffectiveDPD` 虽为 flattened 29-field replay view，但没有新增独立 ontology；其字段均来自三层已存在 material values，目的是让消费者不再二次推理。

## 17. 未解决问题

- DPD snapshot 是否写入现有 `Scene.content` 需要独立 lifecycle/review 决策；本批保持 transient，不新增 Java persistence。
- 7.2S Audio compatibility fields仍有语义重叠；在 7.3B 完成 typed Audio Projection 前不能安全删除。
- Shot Design/Visual Production 尚未消费 DPD fingerprint；属于后续 Visual Projection 批次。

## 18. 7.3B 前置条件

7.3B 应以本批同一 `DPDSnapshot` 为唯一 cross-modal performance authority，定义 typed Audio Projection，将 Voice Profile/Casting、objective/target/activation/control 与 timing 转换为 provider-neutral Audio brief，再由 adapter 转换成具体 Provider 语法。Projection 不得修改 DPD，也不得在不兼容时静默重解释。

本报告止于前置条件；`BATCH_7_3B = NOT_STARTED`。

## 19. 架构问题与最终状态

### Q1–Q10

1. DPD 属于独立 Skill Core / Agent-side deterministic intermediate representation。
2. DPD 不是业务实体。
3. 当前不需要 Java 持久化；现有 open content 可作为未来候选，但本批未接入。
4. 不需要 MCP CRUD Tools。
5. Scene 建背景，Beat 覆盖当前行动状态，Line 只覆盖本句；missing/null inherit、scalar reset 不支持、空 list reset、Line > Beat > Scene。
6. Character 保持稳定身份/理解；DPD 只存 stable key 与当前表演决定。
7. DPD 给出戏剧语义；Audio Projection 才给出声学/韵律/时间控制。
8. DPD 给出戏剧语义；Visual Projection 才给出身体/面部/空间/镜头实现。
9. 复用 `ContractModel` strict schema、canonical fingerprint、stable speaker/spoken IDs、Character/Scene inputs 的边界语义。
10. 建议未来 deprecated 重叠 SceneState fields、untyped cross-modal PerformanceIntent 与 legacy delivery/pace/pause keys；本批不删除。

```text
BATCH_7_3A = PASS
DPD_CORE_CONTRACT = PASS
SCENE_DPD = PASS
BEAT_DPD = PASS
LINE_DPD = PASS
DPD_INHERITANCE = PASS
DPD_VALIDATION = PASS
DPD_PROVIDER_NEUTRALITY = PASS
DPD_MODALITY_NEUTRALITY = PASS
CHARACTER_DPD_SEPARATION = PASS
AUDIO_BOUNDARY = PASS
VISUAL_BOUNDARY = PASS
DETERMINISTIC_FIXTURE = PASS
REGRESSION = PASS

BATCH_7_3B_AUDIO_PROJECTION = NOT_STARTED
REAL_TTS_CALLS = 0
REAL_IMAGE_VIDEO_CALLS = 0
LIP_SYNC = NOT_STARTED
```
