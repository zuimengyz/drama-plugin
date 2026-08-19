# Batch 6.0R-E2E-R2 Credit Telemetry Unblock & Production Resume 执行报告

执行时间：2026-08-19（Asia/Shanghai）

## 1. 执行摘要

本轮沿用报告 41、R1 checkpoint、既有 credit ledger 和 production checkpoint；R1 未重跑、8 个 stable reference 未重新恢复或生成。用户确认的 1995 credits 被作为本轮唯一预算基线，余额 telemetry 缺失不再阻断执行。

R2 从 `Scene 1 / Shot 1-01 / IMAGE_CREDIT_PREFLIGHT` 原地继续，完成 Shot 1-01 与 Shot 1-02 的图片、视频、正式 Media、MinIO resolve 和 SHA-256 闭环。Shot 1-02 的“哥舒翰｜潼关主帅”首次出场角标通过非生成型后处理完成，未为角标重新生成视频。

进入 Shot 1-03 预检时发现冻结 Reference Plan 的真实缺口：该镜头是哥舒翰与王思礼的双人镜头，王思礼是明确可见且承担提议动作的人物，但批准的 8 个 stable reference 中没有王思礼；既有旧王思礼 Asset 已在冻结 plan 中明确标记为属于 known-defective Work、不可复用。依据 Shot Production 的 `MISSING_STABLE_REFERENCE` 硬门，本轮在提交下一付费 Job 前停止。

## 2. 冻结状态复用

```text
R1 reused = YES
R1 rerun = NO
R1_MEDIA_RECOVERY = PREVIOUSLY PASS
Stable Reference Media = 8/8 reused
Reference regeneration = 0
Duplicate stable Media = 0
```

未重新创建 Work、Script、Episode、Scene、Shot、Asset 或既有 Media；未修改 R1 recovery contract、R1 tests 或 R1 checkpoint。

## 3. Credit Telemetry Unblock

```text
USER_CONFIRMED_STARTING_CREDITS = 1995
BALANCE_TELEMETRY_AVAILABLE = NO
R2_INITIAL_BUDGET = 1995
R2_MAX_CREDIT_SPEND = 1995
CREDIT_ACCOUNTING_MODE = ESTIMATED
```

每个 Job 均在 submit 前调用 `estimate_credits`：Nano Banana 2 图片为 18 credits/image，Kling V3 5 秒 1080p 视频为 177 credits。Provider 未返回 actual consumption，billing delta 亦不可用，因此只按官方 estimate 记账，未把估算冒充 actual。

## 4. Provider 与输入策略

仅使用：

```text
MCP = comfy-cloud-2
AUTH = X-API-Key
OAuth = NOT USED
```

冻结的 `api_google_nano_banana2_text_to_image` 无 reference 输入能力。Shot 1-01/1-02 均要求稳定身份输入，因此按视觉 Provider 规则做最小能力等价替换为同系列官方 `api_google_nano_banana2_image_edit`；没有改变模型家族、剧情、Shot 或 Reference Plan。视频继续使用冻结的 `api_kling_v3_video`、single-image、5 秒、1080p、无音频、multi-shot disabled。

## 5. Credit Ledger Summary

| Seq | Shot | Type | Job | Estimate | Result |
|---:|---|---|---|---:|---|
| 1 | 1-01 | IMAGE | `86782b40-ce19-4b55-b837-938e296a6c4e` | 18 | Visual review fail，保留 raw |
| 2 | 1-01 | IMAGE revision | `d0680eca-3a83-442c-9594-c83e3431f173` | 18 | Durable PASS |
| 3 | 1-01 | VIDEO | `78ad8db0-e33b-4ed4-8f8d-d163aa204e18` | 177 | Visual review fail，保留 raw |
| 4 | 1-01 | VIDEO revision | `cda7b86f-4d6b-4aa0-bea5-75fcf0a5e0af` | 177 | Durable PASS |
| 5 | 1-02 | IMAGE | `35504470-22bf-4889-9b10-f9773bfb0216` | 18 | Visual review fail，保留 raw |
| 6 | 1-02 | IMAGE revision | `6c0a8a3a-fc2a-4cd3-be7d-837399dd4bfa` | 18 | Durable PASS |
| 7 | 1-02 | VIDEO | `9f8ba1a6-3394-4caf-b7b6-84d07e36db3c` | 177 | Durable PASS |

```text
R2_ACCOUNTED_USAGE = 603
R2_BUDGET_REMAINING = 1392
R2_ACCOUNTED_USAGE <= 1995 = PASS
```

没有 submit timeout、丢失 Job identity、盲目 resubmit 或重复扣费风险。Comfy technical retry count 为 0；三个 revision 均由具体 Visual Review FAIL 触发，不计作网络重试。

## 6. Shot 1-01 生产结果

### Image

- Stable reference：`REF_TONGPASS` / `media_0bbcae64f15e4d82b1e8f34512ea5f9f`。
- 首图 FAIL：保留参考标签、关门不可见、敌军读作活动阵列。
- 唯一针对性修订 PASS：紧闭关门、山河关隘、稳定守军与停滞远营可读，无标签。
- 正式 Media：`media_4fa8538e316f43c39e974050805800ec`。
- SHA-256：`1bb2947fe0c21a363856cff6b497acc0908382f2ae88e8446558457f034d3aad`。

### Video

- 首段 FAIL：门前新增向关门移动的士兵，可能读为敌军推进。
- 唯一针对性修订 PASS：门前道路为空，关门全程关闭，远营停滞，仅雾、河水、旗帜轻微运动。
- Shot 1-01 不构成哥舒翰首次明确出场，无姓名角标。
- 正式 Media：`media_8c2a03f8e3fd431ca2598821eb4ddb09`。
- SHA-256：`2e487ce378b3bd201e13f024667e5cf8a9af3ef8e54c474a58634c448eb8e5c6`。

## 7. Shot 1-02 生产结果

### Image

- Stable reference：`REF_GESHUIHAN` / `media_2a0e7a10b8fc4dc5863731c02e5392ef`。
- 首图动作与身份正确，但保留 reference 标签，Visual Review FAIL。
- 唯一针对性修订 PASS：哥舒翰身份、甲胄、军图与按回木签动作清楚，无 reference 标签。
- 正式 Media：`media_20f0fe2fe0814eefb590db2519a392af`。
- SHA-256：`de759178ad92468ba5a462f8e74784469241195aac50bd9db279d7c14739ffd8`。

### Video 与首次出场角标

- Raw Provider video 动态审核 PASS；没有付费视频 revision。
- Raw 输出保存在 `production/scene-01/shot-1-02/raw-video.mp4`。
- 以透明 PNG + ffmpeg overlay 非生成型叠加“哥舒翰｜潼关主帅”，显示区间 0.25–2.5 秒；角标位于左上安全区，不遮挡面部、右手木签或军图。
- Final 输出保存在 `production/scene-01/shot-1-02/final-video.mp4`。
- 正式 Media：`media_b11d88f165bd4d8d9cb1bc164b92c6bc`。
- Final SHA-256：`f62bc69ec90e5c2a794d41a81fff6f0f7bee60ece23b9e59c741f83211db6831`。
- `FIRST_APPEARANCE_NAME_TAG = PASS`。

第一次 ffmpeg 中景编码因 30 秒执行窗口留下一个不可播放的 incomplete 文件，已保留为 `final-video-incomplete.mp4`；随后使用相同非生成型 overlay 和明确 5.041667 秒时长成功完成，不涉及 Comfy credits。

## 8. Media / MinIO / Hash Matrix

| Shot | Role | Media | MIME | Resolve | Local↔MinIO SHA | Result |
|---|---|---|---|---|---|---|
| 1-01 | START_FRAME | `media_4fa8538e316f43c39e974050805800ec` | image/png | PASS | MATCH | PASS |
| 1-01 | FINAL_VIDEO | `media_8c2a03f8e3fd431ca2598821eb4ddb09` | video/mp4 | PASS | MATCH | PASS |
| 1-02 | START_FRAME | `media_20f0fe2fe0814eefb590db2519a392af` | image/png | PASS | MATCH | PASS |
| 1-02 | FINAL_VIDEO | `media_b11d88f165bd4d8d9cb1bc164b92c6bc` | video/mp4 | PASS | MATCH | PASS |

所有已花费 credits 且通过审核的结果均已下载、本地持久化、正式导入、MinIO resolve 并下载回验；没有只停留在 Provider 的成功结果。

## 9. Historical / Continuity Review

```text
HISTORICAL_MAINLINE = PASS
PROTAGONIST = 哥舒翰
WANG_SILI_ROLE_BOUNDARY = PASS / not promoted
SHOT_1_01_SEMANTIC_CONTINUITY = PASS
SHOT_1_02_SEMANTIC_CONTINUITY = PASS
REFERENCE_IMAGE_IDENTITY = PASS
FIRST_APPEARANCE_NAME_TAG = PASS
```

未改写冻结剧情或历史主线。

## 10. Stop Reason 与恢复要求

```text
LAST_COMPLETED_NODE =
Episode 1 / Scene 1 / Shot 1-02 / VIDEO_MEDIA_VERIFY

NEXT_NODE =
Episode 1 / Scene 1 / Shot 1-03 / IMAGE_REFERENCE_RESOLUTION

STOP_REASON = MISSING_STABLE_REFERENCE_REF_WANGSILI
```

Shot 1-03 是明确的 `TWO_SHOT`，required transition 为王思礼提出“三十骑劫取杨国忠”、哥舒翰隔案拒绝。王思礼不能被匿名替身、无正式身份图片或旧缺陷 Work Asset 代替。

恢复前置：通过独立 `asset-resolution` 工作流建立并审核王思礼的 stable Asset+Media；这会扩展当前冻结的 8-reference plan，必须作为明确的 Reference Plan 修复处理。完成后仍从 Shot 1-03 的 reference resolution/credit preflight 继续，不得重跑 Shot 1-01、1-02。

## 11. 关键计数

```text
R1 reused = YES
R1 rerun = NO

USER_CONFIRMED_STARTING_CREDITS = 1995
BALANCE_TELEMETRY_AVAILABLE = NO
CREDIT_ACCOUNTING_MODE = ESTIMATED
R2_ACCOUNTED_USAGE = 603
R2_BUDGET_REMAINING = 1392

COMFY_JOB_COUNT = 7
NEW_IMAGE_GENERATION_COUNT = 4
NEW_VIDEO_GENERATION_COUNT = 3
COMPLETED_IMAGE_COUNT = 2
COMPLETED_VIDEO_COUNT = 2
COMPLETED_SHOT_COUNT = 2
NEW_MEDIA_COUNT = 4
COMFY_RETRY_COUNT = 0
AVOIDED_DUPLICATE_JOB_COUNT = 0
```

`NEW_*_GENERATION_COUNT` 包含内容审核失败后唯一允许的 targeted revision；`COMPLETED_*` 只统计 durable PASS 产物。

## 12. 代码与工作区

```text
CODE_CHANGED = NO
```

本轮未修改 Java、Drama Plugin、Drama MCP 或 Comfy adapter 代码。工作区中的 R1 recovery code 及 `application.yml` 既有 modified 状态均来自本任务开始前，本轮不归属这些变更。新增/更新仅限 R2 ledger、checkpoint、production artifacts 与本报告。

## 13. 最终判定

```text
R1 = PREVIOUSLY PASS / NOT RERUN
R2_PRODUCTION = PARTIAL
R2_RESUME_SAFETY = PASS
BATCH_6_0R_E2E = PARTIAL
PRIMARY_BLOCKER = MISSING_STABLE_REFERENCE_REF_WANGSILI
```

本次不是 `CREDIT_HARD_STOP`：剩余账面预算为 1392。停止原因是冻结 Reference Plan 缺少 Shot 1-03 必需人物的稳定身份输入；继续提交会违反既定资产一致性和 Shot Production 安全规则。
