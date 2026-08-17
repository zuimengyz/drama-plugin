# Batch 5.2 — Reference-driven Multi-Shot Visual Production E2E

## 1. Executive Summary

本报告仅执行 Batch 5.2 的 Provider preflight 与 Drama 侧只读预检。Comfy 侧仅调用一次无消费的 `get_server_info`，未调用 upload/generation/job/output 工具；未重新登录、配置、安装或模拟 Provider，未提交生成任务，未创建或修改任何 Drama domain data，也未创建 batch5-2 Provider outputs。

Drama 侧真实读取、稳定 Asset/Media 一致性检查、Media resolve、受控临时下载与 SHA-256 验证均完成。视觉 Provider preflight 被精确阻断：外层已调用 `comfy-cloud/get_server_info`，返回 OAuth refresh token rejected，`invalid_grant: refresh token reuse detected`，并要求 OAuth authorization。按 shot-production contract，停止于 Provider preflight。

因此本批未生成 Shot、未执行 Visual Review / Identity Annotation / Cross-Shot Review、未导入或持久化 Shot Media。

## 2. Stable Reference Preflight

| Reference | Asset | Asset type / identity | Stable Media | MIME | Expected SHA-256 | Resolved/download SHA-256 | Result |
|---|---|---|---|---|---|---|---|
| Character | `asset_df44cfb7db1646f2a7b7eae2463a032e` | `MASTER_CHARACTER_CARD` / 李陵 | `media_fe9dae51b9a74c8ea4819784eca27154` | `image/png` | `742bd90ef8d5da24be3c1037b386079fe3d8d6cb6869b5b5d5a81c9b41bfa51d` | `742bd90ef8d5da24be3c1037b386079fe3d8d6cb6869b5b5d5a81c9b41bfa51d` | PASS |
| Scene | `asset_c13dbef904f04c63bc48de0a8505be66` | `MASTER_SCENE_CARD` / 苏武穹庐 | `media_ec444a5cf36040bcb96b2b12b8a6ea6e` | `image/png` | `5e0eddccf35284a98ba79087abed64ceb539614aab308138fa151f45f0b8eb71` | `5e0eddccf35284a98ba79087abed64ceb539614aab308138fa151f45f0b8eb71` | PASS |

两项均通过 `media.resolve_media` 获取实际字节，下载到受控临时文件后验证为非空、常规 PNG、1024×1024、RGBA；未在报告中记录临时 URL。Media metadata 中的既有 `visualContentReview=PASS` 与 `annotationValidation=PASS` 仅作为稳定 Reference 事实读取，未重新执行 Batch 5.1RR.1。

## 3. Production Context

真实读取并核对：

- Work: `work_4cf81e8862234727b082cf2115ec699b` — `E2E_B04《北海无雁：苏武十九年》`
- Script: `script_5f16ca3b7a3b4b2e80b2f2711e37b2ce` — `E2E_B04《北海无雁》八集短剧剧本`
- Episode: `episode_3a900d6a26b246889970af5b7f5a1475` — 第 5 集《故人来劝》
- Scene: `scene_399ace55923e47be8092eb808d7d284c` — `E2E_B04 5-2 一桌家书`；地点为苏武穹庐内、入夜、火弱风急

三个 Shot 均确认属于该 Scene：

| Shot | Stable ID | Title / shotType | Distinct real context |
|---|---|---|---|
| A | `shot_a9dc0ba7dfdc4e7ea2d1d479403c6274` | 5-2-04 / 只暖手不饮 / 双人过肩组接 | 苏武端碗停在唇下，只暖手不饮；李陵前倾；固定机位内拉焦 |
| B | `shot_5559407312e04d9988591a11d3bcbf7f` | 5-2-05 / 扶节 / 物件特写上摇双人近景 | 汉节残余旄毛、李陵扶节、苏武放下碗；物件特写上摇至双人近景 |
| C | `shot_11b46c83ee77483fb01c6903cfa198c3` | 5-2-06 / 反问 / 李陵正面近景 | 李陵手停在汉节上，面对苏武画外反问；固定 80mm 近景、无王印 |

共同稳定约束为李陵身份、深色胡服与皮毛、苏武穹庐、入夜、弱火、冷暗基调；三 Shot 的景别、动作、构图和叙事功能不同。

## 4. Reference Handoff and Provider Preflight

已完成的非视觉链路：

`Stable Asset → bound stable Media → media.resolve_media → actual local bytes → MIME/magic/hash verification`

每个 Shot 的计划 Reference set 为两张：Character Master + Scene Master；未增加第三张 Reference，未使用旧本地 artifact，未调用 Provider upload。

Provider preflight evidence：外层 `comfy-cloud/get_server_info` 的实际失败为：

`OAuth refresh token rejected; invalid_grant: refresh token reuse detected; OAuth authorization required.`

该错误位于视觉 Provider authorization/preflight 层。按照 `references/visual-provider.md` 与 shot-production skill，本次不继续执行 `visual.input.upload`、`visual.image.generate`、`visual.job.wait` 或 `visual.output.fetch`，也不尝试修复 Provider 状态。

## 5. Shot A / Shot B / Shot C

三个 Shot 的真实 Shot contract 均已读取。因 Provider authorization blocker，三者均未进入 Provider、job、output、file review、annotation 或 Media persistence。

| Field | Shot A | Shot B | Shot C |
|---|---|---|---|
| Planned reference count | 2 | 2 | 2 |
| Provider / tool / template / jobId | NOT_RUN | NOT_RUN | NOT_RUN |
| Generation count | 0 | 0 | 0 |
| Generation | NOT_RUN | NOT_RUN | NOT_RUN |
| Output fetch | NOT_RUN | NOT_RUN | NOT_RUN |
| File decode | NOT_RUN | NOT_RUN | NOT_RUN |
| Visual Content Review | NOT_RUN | NOT_RUN | NOT_RUN |
| Identity Annotation | NOT_RUN | NOT_RUN | NOT_RUN |
| Media import | NOT_RUN | NOT_RUN | NOT_RUN |
| Media resolve | NOT_RUN | NOT_RUN | NOT_RUN |
| Media byte equality | NOT_RUN | NOT_RUN | NOT_RUN |
| Final mediaId / artifact | NOT_RUN | NOT_RUN | NOT_RUN |

## 6. Visual Review and Cross-Shot Review

未下载任何 Shot Provider output，因此没有进行实际图片查看；不得将 Provider `completed` 或稳定 Reference 的既有 review 结果当作本批 Shot review 结果。

| Dimension | Shot A | Shot B | Shot C | Consistency |
|---|---|---|---|---|
| Character Identity | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| Age | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| Hair / Beard | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| Costume | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| Scene | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| Lighting | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

## 7. Media Contract Inspection

实际读取的 Media contract 包括 `media.get_media` 与 `media.resolve_media`；当前稳定 Media 返回 `id/workId/assetId/shotId/mediaType/purpose/sourceRef/content`，resolve 返回 `mediaId/mimeType/sizeBytes/url/expiresAt`。`media.import_media` 的实际工具契约要求 `source_uri/work_id/media_type`，并可接收 `asset_id/shot_id/purpose/content`；本次未调用。

实际读取的 Shot contract 包括 `shot.get_shot`；当前 Shot 返回 `id/sceneId/shotNo/title/shotType/content`，内容承载镜头语义。读取结果未提供正式生成 Media 绑定字段；因此本次没有为了建立不存在的绑定而保存或修改 Shot。

## 8. Revision Record

NONE. 没有 generation，也没有 revise。

## 9. Changed Files

- 新增本报告：`docs/reports/30-Batch-5.2-Reference-driven-Multi-Shot-Visual-Production-E2E-执行报告.md`
- 未创建 `docs/reports/artifacts/batch5-2/`
- 未创建 batch5-2 Provider outputs 或 annotated derivatives
- 未修改既有文件、Secrets、Skill、Plugin、MCP、Java、数据库或 Workflow

## 10. Source Changes

```text
DRAMA_PLUGIN_SOURCE_CHANGED = NO
HISTORICAL_SKILL_CHANGED = NO
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO
COMFY_WORKFLOW_CHANGED = NO
CODEX_CONFIG_CHANGED = NO
SECRET_EXPOSURE = NO
```

## 11. Unified Acceptance Fields

```text
FORMAL_OBJECT_STORAGE = PASS

STABLE_CHARACTER_REFERENCE = PASS
STABLE_SCENE_REFERENCE = PASS

CHARACTER_REFERENCE_ASSET_ID = asset_df44cfb7db1646f2a7b7eae2463a032e
CHARACTER_REFERENCE_MEDIA_ID = media_fe9dae51b9a74c8ea4819784eca27154
SCENE_REFERENCE_ASSET_ID = asset_c13dbef904f04c63bc48de0a8505be66
SCENE_REFERENCE_MEDIA_ID = media_ec444a5cf36040bcb96b2b12b8a6ea6e

CHARACTER_REFERENCE_RESOLVE = PASS
SCENE_REFERENCE_RESOLVE = PASS
CHARACTER_REFERENCE_HASH_EQUALITY = PASS
SCENE_REFERENCE_HASH_EQUALITY = PASS
REFERENCE_REUSE_ACTUALLY_USED = NO

SHOT_COUNT = 0
SHOT_A_GENERATION = NOT_RUN
SHOT_B_GENERATION = NOT_RUN
SHOT_C_GENERATION = NOT_RUN
SHOT_A_REFERENCE_COUNT = 0
SHOT_B_REFERENCE_COUNT = 0
SHOT_C_REFERENCE_COUNT = 0
SHOT_A_GENERATION_COUNT = 0
SHOT_B_GENERATION_COUNT = 0
SHOT_C_GENERATION_COUNT = 0
SHOT_A_OUTPUT_FETCH = NOT_RUN
SHOT_B_OUTPUT_FETCH = NOT_RUN
SHOT_C_OUTPUT_FETCH = NOT_RUN
SHOT_A_FILE_DECODE = NOT_RUN
SHOT_B_FILE_DECODE = NOT_RUN
SHOT_C_FILE_DECODE = NOT_RUN
SHOT_A_VISUAL_CONTENT_REVIEW = NOT_RUN
SHOT_B_VISUAL_CONTENT_REVIEW = NOT_RUN
SHOT_C_VISUAL_CONTENT_REVIEW = NOT_RUN
SHOT_A_IDENTITY_ANNOTATION = NOT_RUN
SHOT_B_IDENTITY_ANNOTATION = NOT_RUN
SHOT_C_IDENTITY_ANNOTATION = NOT_RUN
CHARACTER_IDENTITY_CONSISTENCY = NOT_RUN
AGE_CONSISTENCY = NOT_RUN
HAIR_BEARD_CONSISTENCY = NOT_RUN
COSTUME_CONSISTENCY = NOT_RUN
SCENE_CONSISTENCY = NOT_RUN
LIGHTING_CONTINUITY = NOT_RUN
CROSS_SHOT_VISUAL_CONSISTENCY = NOT_RUN
SHOT_A_MEDIA_IMPORT = NOT_RUN
SHOT_B_MEDIA_IMPORT = NOT_RUN
SHOT_C_MEDIA_IMPORT = NOT_RUN
SHOT_A_MEDIA_RESOLVE = NOT_RUN
SHOT_B_MEDIA_RESOLVE = NOT_RUN
SHOT_C_MEDIA_RESOLVE = NOT_RUN
SHOT_A_MEDIA_BYTE_EQUALITY = NOT_RUN
SHOT_B_MEDIA_BYTE_EQUALITY = NOT_RUN
SHOT_C_MEDIA_BYTE_EQUALITY = NOT_RUN
SHOT_MEDIA_PERSISTENCE = FAIL

REFERENCE_REUSE_READY = YES
STANDARD_REFERENCE_REGENERATION = NO
NEW_CHARACTER_MASTER_CREATED = NO
NEW_SCENE_MASTER_CREATED = NO
CUSTOM_WORKFLOW_CREATED = NO
SAVED_WORKFLOW_CREATED = NO
DYNAMIC_WORKFLOW_INTRODUCED = NO
DRAMA_PLUGIN_SOURCE_CHANGED = NO
HISTORICAL_SKILL_CHANGED = NO
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO
COMFY_WORKFLOW_CHANGED = NO
CODEX_CONFIG_CHANGED = NO
SECRET_EXPOSURE = NO

BATCH_5_2 = BLOCKED
NEXT_BATCH_READY = NO
```

阻断边界：稳定 Drama Reference preflight 已 PASS；视觉 Provider authorization 未通过，故 Batch 5.2 不能进入生成与后续验收阶段。解除 OAuth authorization blocker 后，下一步应从 Provider preflight 重新开始，不重新生成两个 Stable Reference。
