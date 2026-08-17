# Batch 5.1RR.1 — Reference Identity Annotation & Persistence 执行报告

执行日期：2026-08-17（Asia/Shanghai）  
Work ID：`work_4cf81e8862234727b082cf2115ec699b`

## 1. Executive Summary

- 未重新生成 Provider 图片，未提交新的 Provider job；复用并保留两个既有 Provider artifact。
- Provider 原始视觉内容 Review 的最终语义为 PASS；缺失身份标签属于后处理要求，不属于 Provider 视觉质量失败。
- 两张正式 Reference 均完成确定性本地身份标注，并实际打开检查通过。
- 两张 Reference 均完成 Drama Media 导入、正式 MinIO resolve 回读和 SHA256 字节一致性校验。
- 两个稳定 Asset 均完成持久化并绑定本批新 Reference Media：李陵 `MASTER_CHARACTER_CARD`、苏武穹庐 `MASTER_SCENE_CARD`。
- 未修改 bootstrap Media `media_f1048149fd0f485c822481f91ea6a894`。
- 未启动 Shot；Shot generation remains 0。

## 2. Provider Original Integrity

| 对象 | Provider path | size | dimensions / MIME | SHA-256 | integrity |
|---|---|---:|---|---|---|
| Character | `docs/reports/artifacts/batch5-1rr/character-master-liling-provider.png` | 1,412,218 bytes | 1024×1024, `image/png` | `41ec29c7d6ae18c3503e50041c1784dc5ec74fd3770c5407e8cd22517a3135df` | PASS |
| Scene | `docs/reports/artifacts/batch5-1rr/scene-master-qionglu-provider.png` | 1,801,679 bytes | 1024×1024, `image/png` | `e20301d471c46fb2e51f17c73727803c22ed5517658b47f3e2675a4844d35e90` | PASS |

两个 Provider 原图均存在、为可读 regular file、可解码；原文件未修改、未覆盖、未删除。

## 3. Visual Review Semantic Correction

本批正式冻结以下语义：

```text
CHARACTER_VISUAL_CONTENT_REVIEW = PASS
SCENE_VISUAL_CONTENT_REVIEW = PASS
CHARACTER_IDENTITY_ANNOTATION = NOT_YET_PERFORMED（本批完成）
SCENE_IDENTITY_ANNOTATION = NOT_YET_PERFORMED（本批完成）
```

身份标注是 `Visual Content Review` 之后的 deterministic local post-process；`identity annotation != provider visual quality`。28 号历史报告未覆盖、未修改，仅由本报告修正后续流程语义。

## 4. Identity Annotation

两张 Reference 均使用确定性 Pillow + 系统字体 `Heiti TC Light`，字体实际路径为 `/System/Library/Fonts/STHeiti Light.ttc`。统一规则如下：左上角、margin 24 px、字号 34 px、padding 12×10 px、黑色 alpha 176 半透明底板；除标注面板外像素保持不变。

| 对象 | label text | corner | validation |
|---|---|---|---|
| Character | `人物：李陵` | top-left | PASS：中文可见、无乱码、未遮挡面部/关键服装、主体未发生其他改变 |
| Scene | `场景：苏武穹庐` | top-left | PASS：中文可见、无乱码、未遮挡主要空间结构、主体未发生其他改变 |

两张图片均已实际打开检查，Annotation Validation = PASS。

## 5. Reference Artifacts

Provenance：`Provider original → deterministic annotation → platform Reference`。

| 对象 | provider SHA-256 | reference path | reference SHA-256 | MIME / dimensions | decode |
|---|---|---|---|---|---|
| Character | `41ec29c7d6ae18c3503e50041c1784dc5ec74fd3770c5407e8cd22517a3135df` | `docs/reports/artifacts/batch5-1rr/character-master-liling-reference.png` | `742bd90ef8d5da24be3c1037b386079fe3d8d6cb6869b5b5d5a81c9b41bfa51d` | `image/png`, 1024×1024, 1,355,658 bytes | PASS |
| Scene | `e20301d471c46fb2e51f17c73727803c22ed5517658b47f3e2675a4844d35e90` | `docs/reports/artifacts/batch5-1rr/scene-master-qionglu-reference.png` | `5e0eddccf35284a98ba79087abed64ceb539614aab308138fa151f45f0b8eb71` | `image/png`, 1024×1024, 1,713,523 bytes | PASS |

## 6. Media Persistence

导入只使用两张 `*-reference.png`，未导入 Provider 原图；purpose 均为 `REFERENCE`。artifact 目录在服务配置的 allowed root 内，导入成功。

| 对象 | mediaId | sourceRef | MIME | size | contentHash（local/reference） | formal MinIO resolved SHA-256 | resolve / byte equality |
|---|---|---|---|---:|---|---|---|
| Character | `media_fe9dae51b9a74c8ea4819784eca27154` | `storage:47f22231-733b-49ed-b1eb-cc576de548f6` | `image/png` | 1,355,658 bytes | `742bd90ef8d5da24be3c1037b386079fe3d8d6cb6869b5b5d5a81c9b41bfa51d` | `742bd90ef8d5da24be3c1037b386079fe3d8d6cb6869b5b5d5a81c9b41bfa51d` | PASS / PASS |
| Scene | `media_ec444a5cf36040bcb96b2b12b8a6ea6e` | `storage:04c8059e-581b-49da-86c9-63b788d9ca44` | `image/png` | 1,713,523 bytes | `5e0eddccf35284a98ba79087abed64ceb539614aab308138fa151f45f0b8eb71` | `5e0eddccf35284a98ba79087abed64ceb539614aab308138fa151f45f0b8eb71` | PASS / PASS |

注：`sourceRef` 是不透明稳定标识；本报告不记录 signed URL、凭据或秘密。

## 7. Asset Persistence

执行了 search-before-create：按 Work、身份、正式 Asset 类型搜索，Character 与 Scene 均未发现同身份稳定 Asset，因此各创建一次；未调用例行 `save_asset`。

| 对象 | search | action | assetId | asset type | bound reference mediaId | final get/search |
|---|---|---|---|---|---|---|
| 李陵 | NOT_FOUND（PASS） | CREATE | `asset_df44cfb7db1646f2a7b7eae2463a032e` | `MASTER_CHARACTER_CARD` | `media_fe9dae51b9a74c8ea4819784eca27154` | PASS |
| 苏武穹庐 | NOT_FOUND（PASS） | CREATE | `asset_c13dbef904f04c63bc48de0a8505be66` | `MASTER_SCENE_CARD` | `media_ec444a5cf36040bcb96b2b12b8a6ea6e` | PASS |

持久化后再次执行 `asset.get`、精确 `asset.search`、`media.get`、`media.resolve`。返回的身份、Asset 类型、绑定 Media、PNG MIME、尺寸与 Reference SHA256 均正确。bootstrap Media 未绑定。

## 8. Changed Files

- Reference derivatives（本批新建的正式产物）：
  - `docs/reports/artifacts/batch5-1rr/character-master-liling-reference.png`
  - `docs/reports/artifacts/batch5-1rr/scene-master-qionglu-reference.png`
- 本报告：`docs/reports/29-Batch-5.1RR.1-Reference-Identity-Annotation-and-Persistence-执行报告.md`
- Provider originals：未修改。
- Deterministic annotation script（本批新建）：`docs/reports/artifacts/batch5-1rr/annotate_references.py`。

## 9. Source Changes

```text
Drama Plugin source       = NO
historical Skill          = NO
Drama MCP                 = NO
Java                      = NO
Database                  = NO
Comfy Workflow            = NO
Codex config              = NO
```

## 10. Unified Acceptance Fields

```text
PROVIDER_REGENERATION = NO
NEW_PROVIDER_JOB_SUBMITTED = NO

CHARACTER_PROVIDER_ORIGINAL_INTEGRITY = PASS
SCENE_PROVIDER_ORIGINAL_INTEGRITY = PASS

CHARACTER_VISUAL_CONTENT_REVIEW = PASS
SCENE_VISUAL_CONTENT_REVIEW = PASS

CHARACTER_IDENTITY_ANNOTATION = PASS
SCENE_IDENTITY_ANNOTATION = PASS

CHARACTER_REFERENCE_ARTIFACT = PASS
SCENE_REFERENCE_ARTIFACT = PASS

CHARACTER_REFERENCE_DECODE = PASS
SCENE_REFERENCE_DECODE = PASS

CHARACTER_MEDIA_IMPORT = PASS
SCENE_MEDIA_IMPORT = PASS

CHARACTER_MEDIA_RESOLVE = PASS
SCENE_MEDIA_RESOLVE = PASS

CHARACTER_MEDIA_BYTE_EQUALITY = PASS
SCENE_MEDIA_BYTE_EQUALITY = PASS

CHARACTER_ASSET_SEARCH = PASS
SCENE_ASSET_SEARCH = PASS

CHARACTER_REFERENCE_ASSET_PERSISTENCE = PASS
SCENE_REFERENCE_ASSET_PERSISTENCE = PASS

CHARACTER_REFERENCE_REUSE_READY = YES
SCENE_REFERENCE_REUSE_READY = YES
REFERENCE_REUSE_READY = YES

SHOT_GENERATION_STARTED = NO
SHOT_COUNT = 0

DRAMA_PLUGIN_SOURCE_CHANGED = NO
HISTORICAL_SKILL_CHANGED = NO
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO
COMFY_WORKFLOW_CHANGED = NO
CODEX_CONFIG_CHANGED = NO

PROVIDER_ORIGINALS_PRESERVED = YES
SECRET_EXPOSURE = NO

BATCH_5_1RR_1 = PASS
NEXT_BATCH_READY = YES
```

完成边界已到达：稳定 Reference Asset 已就绪；本批立即停止，不进入 Shot Production，不生成 `5-2-04`、`5-2-05` 或 `5-2-06`。
