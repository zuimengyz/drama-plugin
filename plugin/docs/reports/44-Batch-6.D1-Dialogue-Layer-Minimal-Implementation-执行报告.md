# Batch 6.D1 — Dialogue Layer Minimal Implementation 执行报告

执行日期：2026-08-19（Asia/Shanghai）

性质：CONTRACT CONVENTION + SKILL IMPLEMENTATION + PERSISTENCE VERIFICATION + REGRESSION

结论：**PASS**

## 1. 执行摘要

本批以最小改动在现有 Work → Script → Episode → Scene → Shot 链路中冻结 Dialogue Layer：Scene `content.spokenContent[]` 是唯一正文真源；Shot `content.spokenContentBindings[]` 只表达 coverage；Work 既有人物层级提供稳定 `speakerKey`；历史引语、ID 稳定和数值时长均进入现有 Skill Review gate。

当前 `drama-service` 已透明保存开放 JSON content，隔离 H2 集成测试证明 Scene/Shot 嵌套内容经 create/save/get/list/search 完整 round-trip，并证明 save 为 full replacement。因此没有修改生产 Java、DTO、Entity、数据库、Plugin Domain Contract、Tool Catalog 或 MCP adapter。

## 2. D0 基线

D1 采用报告 43 的结论：Dialogue Layer 必需、当前支持部分存在、Scene 应拥有正文、Shot 需要引用、provenance 必需、含 spoken content 时视觉生产前必须检查时长；不新增 Dialogue Entity/Table/Tool/Skill。

D0 示例中的裸 `spokenContentRefs[]` 在 D1 被收紧为带 coverage 语义的 `spokenContentBindings[]`；Scene-local speaker registry 被 Work-scoped identity 取代。

## 3. 当前工程边界确认

- 当前长期记忆事实源：同一 workspace 的 `drama-service/`。
- Plugin：`drama-plugin/`，保留开放 content contract。
- MCP adapter：`drama-mcp-service/`，继续通用投影。
- 未把旧工程当作代码、构建、数据库或运行时依赖。

## 4. drama-service 实际长期记忆实现

实际审计 Controller、Service、DTO、Entity、Mapper/TypeHandler、schema 与测试后确认：

- Work/Script/Episode/Scene/Shot DTO 的 `content` 为 Jackson `JsonNode`；
- Entity 同样持有 `JsonNode`，经 `JsonNodeTypeHandler` 保存；
- `MemorySupport.requireObject` 只要求 content 是 JSON object，不过滤内部字段；
- create 直接保存完整 content，save 完整替换并增加 version；
- get/list/search 返回同一嵌套 JSON；
- `drama_scene.content` 与 `drama_shot.content` 均为 JSON 列。

结论：无强类型转换丢字段风险，生产 Java 无需修改。

## 5. AI_historical / Dify DSL 参考边界

本批没有扫描、构建、运行或修改旧 `AI_historical` Java，也没有复制旧 Domain、Compiler、数据库或固定 workflow。旧 Dify DSL 仅保留为 D0 已完成的历史业务参考，不进入当前代码、配置或 runtime dependency。

## 6. 最终 Dialogue content convention

新增平台中立约定 `plugin/docs/dialogue-layer-content-convention.md`：

```text
Work historicalActorHierarchy[].speakerKey
  ↓
Scene.content.spokenContent[]              ← sole reviewed source
  ↓ stable spokenContentId
Shot.content.spokenContentBindings[]       ← coverage only
Shot.content.plannedDurationMs
  ↓ DURATION_FEASIBILITY
Shot Production / Future Audio             ← consumers, never authors
```

不支持 `dialogues`、`dialogueLines`、`spokenLines`、`speech`、`spokenContentRefs` 等 alias。

## 7. Work-scoped speaker identity 方案

复用 `Work.content.historicalActorHierarchy`。可能发言的个人条目获得 Work 内唯一、稳定、非空的 `speakerKey`；既有 `actor` 仍承担显示名。相同人物跨 Scene 和修订复用同一 key，不新建 Scene registry 或 Character Entity。

视觉 `assetId` 仅为可选 enrichment。缺少视觉 Asset 不阻塞 Dialogue。旁白采用 `narrator:*`，通常为 `narrator:default`，不创建虚构视觉角色。

## 8. Scene spokenContent schema

每个 item 的冻结必需字段为：

```json
{
  "id": "stable-within-parent-scene",
  "kind": "DIALOGUE",
  "speakerKey": "speaker:adviser",
  "text": "Reviewed exact spoken text.",
  "intent": "Immediate dramatic action.",
  "mustKeep": true,
  "performanceIntent": "Provider-agnostic delivery intent.",
  "provenance": {"relation": "FUNCTIONAL"},
  "estimatedDurationMs": 1800
}
```

`kind` 仅为 `DIALOGUE` 或 `NARRATION`。SFX、ambience、foley、music、voiceId、Audio Media、subtitle timecode、lip-sync、mixing 和 actual duration 均不属于本层。`spokenContent: []` 合法。

## 9. Shot spokenContentBindings schema

Shot 仅保存：

```json
{
  "spokenContentBindings": [
    {"spokenContentId": "spoken-01", "coverageIntent": "REACTION"}
  ],
  "plannedDurationMs": 2600
}
```

binding 必须解析到父 Scene item；不能携带正文、voice、subtitle、Audio ID 或 timeline。一个 item 可绑定连续多个 Shot，但未来 Audio 仍只生成一次。

## 10. Coverage intent 定义

- `ON_SCREEN_SPEAKER`：说话者可见并正在表达；
- `REACTION`：同一 spoken item 继续时观察另一主体反应；
- `OFF_SCREEN`：Scene 内说话者在画外；
- `VOICE_OVER`：旁白或有意的非画内表达。

## 11. Historical provenance hard gate

冻结四类：`DIRECT_QUOTE`、`ADAPTED`、`DRAMATIZED`、`FUNCTIONAL`。

`DIRECT_QUOTE` 必须同时具有非空 `sourceRef`、精确 `locator`、`excerpt`，且 text 与 excerpt 在非语义空白/标点归一后匹配。一般 evidence ref、书名或 beat ID 不足；失败时 Review FAIL 或显式降级，绝不自动升级。

`ADAPTED` 要求必要 `sourceRefs` 与 `adaptationNote`；其他类别只保留建立边界所需的精简 reference/note，不复制完整 Research 文档。

## 12. spoken item ID stability 规则

同一逻辑 item 的 wording、performance、provenance detail 或 duration estimate 修订保留 ID。仅新增、删除、拆分、合并会创建或退休受影响 ID，所有未受影响 item 保持不变。Scene full-replacement save 前必须先 reconcile IDs。

## 13. Duration estimation 规则

`estimatedDurationMs` 是正整数粗估，由语言字/词速、可懂度、performance intent 和停顿校正产生；不是实际 Audio duration。本批未调用 TTS。

`plannedDurationMs` 是 Shot 正整数机器字段；文学化 rhythm 描述可保留，但不能驱动 gate。

## 14. Duration feasibility gate

独立 Shot 比较 distinct bound item estimates 总和与 `plannedDurationMs`。连续 coverage group 对重复绑定 item ID 去重，再与组内 planned duration 总和比较，并审查动作、反应与沉默是否仍有可演空间。

冲突返回 `DURATION_FEASIBILITY`，必须在物理视觉生产前由 Scene/Shot Review 解决；Provider 无权临场删改。

## 15. Scene Skill 修改

Scene Development 现在明确：读取 Work speaker/evidence context；先判断是否需要 spoken content；需要时写 exact text 和九个正式字段；允许 silent Scene；Review 检查 speaker、历史一致性、fact attribution、正文完整性、戏剧功能、quote evidence、数值时长与现代语言污染；修订保持 ID；只持久化规范字段。

Scene planning/review references 同步增加 voice、subtext、自然度、冗余、exposition、silence/action relationship 等 SHOULD 检查，没有新增独立 Dialogue Reviewer。

## 16. Shot Skill 修改

Shot Design 现在只从 Scene 正文选择 binding，禁止复制；冻结四种 coverage intent；每个 Shot 写正整数 `plannedDurationMs`；Review 校验 binding resolution/source integrity，并在生产前执行 group-aware `DURATION_FEASIBILITY`。

## 17. Shot Production 修改

Shot Production 在存在 binding 时读取 convention，解析 Scene source，要求 numeric planned duration 和通过时长 gate。视觉只消费与画面有关的 delivery/reaction/off-screen/voice-over 语义。未来显式 Audio 请求可消费 identity、text、performance、provenance、estimate 和 coverage，但不得创建、删除、改写、拆分、合并或替换 Scene item。

缺视觉 Asset 只阻塞必须显示该人物身份的媒体生产，不影响 Dialogue authoring、narration 或 speaker identity。

## 18. Work / Script / Research 是否修改及原因

- Work Creation：**最小修改**。既有人物层级增加 `speakerKey` 规划、Review 与持久化约定。
- Historical Research：**最小修改**。补充 direct quote 的 sourceRef + exact locator + matching excerpt 证据责任。
- Script Adaptation：**未修改**。当前 Skill 已明确负责 dialogue strategy，并禁止详细 Scene dialogue/action，边界足够清晰。

## 19. Java 是否修改及原因

```text
JAVA_PRODUCTION_CHANGED = NO
JAVA_TEST_CHANGED = YES
```

透明 JSON round-trip 已通过，不需要生产 Java 修复。仅在既有 `MemoryIntegrationTest` 增加隔离 H2 用例，验证真实 Controller/Service/Mapper/DB 链路。

## 20. Plugin Contract 是否修改及原因

```text
PLUGIN_DOMAIN_CONTRACT_CHANGED = NO
```

Scene/Shot 的开放 `content: object` 已满足扩展，约束由 convention、Skill、Review 和 fixture 冻结。

## 21. Tool 是否修改

```text
NEW_DIALOGUE_TOOL = NO
DIALOGUE_TOOL_ADDED = NO
```

继续使用既有 Work/Scene/Shot create/get/save/list/search。D1 未修改 Tool Catalog。

## 22. MCP 是否修改

```text
MCP_CHANGED = NO
```

generic adapter 无需特殊 Dialogue dispatch；其全量 13 项测试通过。

## 23. Database 是否修改

```text
DATABASE_CHANGED = NO
NEW_DIALOGUE_TABLE = NO
```

没有 DDL 或 migration；核心领域继续使用既有 JSON content 列。

## 24. 测试矩阵

fixture 使用虚构通用 Adviser/Commander，不硬编码当前作品，共 22 cases：

| # | Case | 期望/结果 |
|---:|---|---|
| 1 | Silent Scene | PASS / PASS |
| 2 | Character Dialogue | PASS / PASS |
| 3 | Narration without Character Asset | PASS / PASS |
| 4 | Direct Quote with exact evidence | PASS / PASS |
| 5 | Direct Quote without exact evidence | FAIL / `DIRECT_QUOTE_EVIDENCE` |
| 6 | Adapted Dialogue | PASS / PASS |
| 7 | Dramatized Dialogue | PASS / PASS |
| 8 | Functional Dialogue | PASS / PASS |
| 9 | Wording revision ID stability | PASS / PASS |
| 10 | Structural split, unaffected IDs stable | PASS / PASS |
| 11 | Cross-scene speaker stability | PASS / PASS |
| 12 | Missing visual Asset | PASS / PASS |
| 13 | On-screen speaker binding | PASS / PASS |
| 14 | Reaction binding | PASS / PASS |
| 15 | Off-screen + voice-over | PASS / PASS |
| 16 | Standalone duration fits | PASS / PASS |
| 17 | Contiguous coverage deduplicates item | PASS / PASS |
| 18 | Duration conflict | FAIL / `DURATION_FEASIBILITY` |
| 19 | Provider mutation | FAIL / `SPOKEN_SOURCE_MUTATION` |
| 20 | Wrong Scene alias | FAIL / `NON_CANONICAL_DIALOGUE_FIELD` |
| 21 | Duplicate Scene source fields | FAIL / `NON_CANONICAL_DIALOGUE_FIELD` |
| 22 | Shot copied spoken body | FAIL / `SHOT_DIALOGUE_COPY` |

这些测试直接解析并验证 fixture 的字段集合、enum、identity resolution、quote matching、ID 集合、binding source integrity、group duration arithmetic 与 provider immutability，而非仅搜索说明文字。

## 25. drama-service round-trip 结果

隔离 H2 用例 `mem010DialogueContentRoundTripsWithoutTypedFiltering` 验证：

- Scene `spokenContent`（含嵌套 provenance 与未知嵌套字段）create/get/list/search 原样返回；
- Scene save 后正文、ID 与嵌套关系原样返回，且旧未知字段消失，证明 full replacement；
- Shot `spokenContentBindings` + `plannedDurationMs` create/get/list/search 原样返回；
- Shot save 改为 `REACTION` 后不含 copied text，旧 rhythm 字段被完整替换。

```text
DRAMA_SERVICE_CONTENT_ROUND_TRIP = PASS
```

## 26. Regression 结果

| 范围 | 命令 | 结果 |
|---|---|---|
| D1 semantic + Skill tests | `.venv/bin/python -m pytest -q plugin/tests/test_dialogue_layer.py plugin/tests/test_skills.py` | 41 passed |
| Plugin 全量 | `.venv/bin/python -m pytest -q plugin/tests` | 96 passed |
| Skill quick validation | `quick_validate.py` × 5 changed Skills | 5 valid |
| drama-service 全量 | `mvn -q test` | 38 tests, 0 failure/error |
| MCP 全量 | `.venv/bin/python -m pytest -q` | 13 passed |

既有 Tool Contract、MCP discovery、creation domains、Media recovery、Work/Script/Episode/Scene/Shot 回归均通过。

## 27. 修改文件列表

D1-owned files：

- `drama-plugin/plugin/docs/dialogue-layer-content-convention.md`
- Historical Research：`SKILL.md`
- Work Creation：`SKILL.md`、`references/planning.md`、`references/review.md`
- Scene Development：`SKILL.md`、`references/planning.md`、`references/review.md`
- Shot Design：`SKILL.md`、`references/planning.md`、`references/review.md`
- Shot Production：`SKILL.md`、`references/production-rules.md`
- `drama-plugin/plugin/tests/fixtures/creative-quality/dialogue-layer.yaml`
- `drama-plugin/plugin/tests/test_dialogue_layer.py`
- `drama-service/server/src/test/java/com/drama/MemoryIntegrationTest.java`（仅新增隔离测试）
- 本报告。

Workspace 在 D1 前已有 Media recovery/production 等未提交修改；本批保留且未归属、覆盖或回滚它们。

## 28. 未修改范围

未修改 Script/Episode Skill、生产 Java、DTO/Entity/Mapper、schema、Plugin contracts、Tool Catalog、MCP、Asset/Media system、Comfy adapter、正式 Work/Script/Episode/6 Scenes/27 Shots/Assets/Media、MinIO objects 或旧工程。

生产冻结文件校验保持：

```text
r2-production-checkpoint.json SHA-256 = b41d7834fb04c4c13355c7d81afe72a770590651093b0c28d75d1b62a9f683a7
r2-credit-ledger.json          SHA-256 = 98d3095b8da65b40160e271b30acd5ccddf85c16709cc91cc069a8723f4430d3
```

## 29. D2 readiness

D1 convention、Skill gate、fixture 和真实 persistence 均已就绪。未来 Audio 可直接取得 speaker identity、exact text、performance intent、provenance、estimated duration 和 Shot coverage，无需重写剧情。

本批没有 backfill 当前作品、没有恢复 6.0R、没有规划或调用任何生成。D2 只能由后续明确任务启动。

```text
BATCH_6_D2_READY = YES
```

## 30. 最终 PASS / FAIL

```text
DIALOGUE_LAYER_MINIMAL_IMPLEMENTATION = PASS

SCENE_SPOKEN_CONTENT = PASS
SHOT_SPOKEN_BINDING = PASS
WORK_SCOPED_SPEAKER_IDENTITY = PASS
SPEAKER_ASSET_DECOUPLING = PASS

DIRECT_QUOTE_EVIDENCE_GATE = PASS
SPOKEN_ITEM_ID_STABILITY = PASS

NUMERIC_DURATION_ESTIMATE = PASS
SHOT_DURATION_FEASIBILITY_GATE = PASS

SILENT_SCENE_SUPPORTED = PASS
NARRATION_SUPPORTED = PASS
REACTION_COVERAGE_SUPPORTED = PASS
OFFSCREEN_COVERAGE_SUPPORTED = PASS

DRAMA_SERVICE_CONTENT_ROUND_TRIP = PASS

NEW_DIALOGUE_ENTITY = NO
NEW_DIALOGUE_TABLE = NO
NEW_DIALOGUE_TOOL = NO
NEW_DIALOGUE_SKILL = NO

AI_HISTORICAL_RUNTIME_DEPENDENCY = NO
OLD_DIFY_RUNTIME_DEPENDENCY = NO

COMFY_PAID_GENERATION = 0
AUDIO_GENERATION = 0
CREDIT_CONSUMPTION = 0

PRODUCTION_DATA_CHANGED = NO
PRODUCTION_CHECKPOINT_CHANGED = NO

BATCH_6_D1 = PASS
BATCH_6_D2_READY = YES
```

**STOP：未进入 Batch 6.D2。**
