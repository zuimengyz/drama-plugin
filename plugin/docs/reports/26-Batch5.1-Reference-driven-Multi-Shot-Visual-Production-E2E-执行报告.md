# Batch 5.1 — Reference-driven Multi-Shot Visual Production E2E 执行报告

> 执行日期：2026-08-17  
> 报告编号：26（不覆盖既有 23、24、25）  
> 最终状态：`BLOCKED`  
> 阻断阶段：Provider 输出文件获取与 Visual Review

## 1. 执行摘要

本轮重新执行已越过 25 号报告的假性 MinIO 阻断：正式 MinIO `192.168.1.86:9000` 健康检查返回 HTTP 200，既有 Drama stable Media 成功 resolve、下载并通过 SHA-256/字节数校验。

Plugin 按 `asset-resolution` 与 `shot-production` Skill 读取真实 Work/Script/Episode/Scene/Shot，选择同一 Scene 的三个真实连续 Shot 候选：`5-2-04`、`5-2-05`、`5-2-06`。已将既有 stable Drama Media resolve → 本地 bootstrap 文件 → Comfy Cloud input upload，证明了 reference handoff 的前半段。

当前 verified visual implementation 为 Comfy Cloud。Plugin 自主发现并提交了两个官方视觉任务：一个以 1 个 Drama reference 生成李陵 Character Master，一个以 0 个 reference 生成穹庐 Scene Master。两个 Provider job 最终均成功，但 Host 无法下载其实际输出字节：Comfy Cloud 短链重定向到 `storage.googleapis.com` 后出现 TLS/egress 连接失败；Drama `media.import_media` 对该 Provider URL 也失败。因无法实际查看输出，不能执行 Visual Review，也不能按 Skill 要求创建稳定 Asset/Media，更不能安全进入三个正式 Shot。

```text
FORMAL_OBJECT_STORAGE = PASS
RUNTIME_VISUAL_PROVIDER_PREFLIGHT = PASS
DRAMA_MEDIA_TO_VISUAL_PROVIDER = PASS（bootstrap reference 已完成 resolve/download/upload）
CHARACTER_MASTER_REFERENCE = BLOCKED
SCENE_MASTER_REFERENCE = BLOCKED
SHOT_COUNT = 0
BATCH_5_1 = BLOCKED
```

## 2. 正式对象存储

```text
formal endpoint = 192.168.1.86:9000
MinIO health = HTTP 200
baseline media = media_f1048149fd0f485c822481f91ea6a894
baseline resolve = PASS
baseline download = HTTP 200
baseline size = 1,859,767 bytes
baseline SHA-256 = d665fdf7016cfa3231b251067682f1733e4b71979be886f2fb454d90929b6539
byte equality against declared/reference baseline = PASS
```

未使用临时 MinIO、9100 或 `/tmp/drama-batch5-minio` 绕过正式对象存储。

## 3. 试验对象

```text
workId = work_4cf81e8862234727b082cf2115ec699b
scriptId = script_5f16ca3b7a3b4b2e80b2f2711e37b2ce
episodeId = episode_3a900d6a26b246889970af5b7f5a1475
sceneId = scene_399ace55923e47be8092eb808d7d284c
```

候选 Shot 均来自同一 Scene《一桌家书》：

| Shot | shotNo | title | shotType |
| --- | --- | --- | --- |
| A | `5-2-04` | 只暖手不饮 | 双人过肩组接 |
| B | `5-2-05` | 扶节 | 物件特写上摇双人近景 |
| C | `5-2-06` | 反问 | 李陵近景缓推 |

三者共享李陵、胡服、穹庐、入夜弱火连续性，并有景别/动作差异。由于 Standard Reference 未完成 Review，未进入正式三 Shot 生成，未创建假的 Shot。

## 4. Standard Reference

### Character — 李陵 Character Master

业务目标：保留中年李陵的脸型、长发、胡须、疲惫克制气质、深色胡服/皮毛基础造型，避免特定 Shot 动作和特殊道具。

```text
bootstrap source = media_f1048149fd0f485c822481f91ea6a894
bootstrap purpose = SHOT_KEY_IMAGE（未改标、未改 purpose、未冒充 Character Master）
reference count = 1
provider = Comfy Cloud
official template = api_qwen3_image_edit
provider job = 4296e4df-4f34-4365-8cba-52071f437ed9
provider terminal status = completed
output fetch = URL returned, byte download blocked by storage.googleapis.com egress
visual review = NOT EXECUTABLE
assetId = NOT_CREATED
mediaId = NOT_CREATED
```

因此：

```text
CHARACTER_MASTER_REFERENCE = BLOCKED
```

### Scene — 穹庐 Scene Master

业务目标：无人穹庐内部、夜间、弱火、冷暗环境、毡墙/木骨/皮毛材质、可复用于不同景别和机位。

```text
reference count = 0
provider = Comfy Cloud
implementation = openai/images-generations via partner API
official template family = Comfy Cloud partner image generation
provider job = ed74b5cd-9e45-4f12-beec-714f40535947
provider terminal status = completed
output fetch = URL returned, byte download blocked by storage.googleapis.com egress
visual review = NOT EXECUTABLE
assetId = NOT_CREATED
mediaId = NOT_CREATED
```

因此：

```text
SCENE_MASTER_REFERENCE = BLOCKED
```

本轮未创建任何 Reference Asset/Media；没有进行 revise，因为 Review 尚未开始，且两项输出均未可见。

## 5. Drama Media → Visual Provider

已完成并记录的实际链路：

```text
media_f1048149fd0f485c822481f91ea6a894
  → media.resolve_media
  → formal MinIO HTTP 200 download
  → SHA-256 verified local bootstrap
  → Comfy Cloud upload_file
  → reference input accepted by official template
```

这不是本地 artifact 冒充 stable Media，也不是旧 Provider filename。由于后续 Provider output fetch 失败，完整的“Provider output → Review → Drama Media import”链路未成立。

## 6. Plugin 自主编排

业务 Prompt 没有指定具体 Provider Tool、模型或 template id。Plugin/Skill 自主完成了：

1. 读取真实 Drama 上下文并选出同 Scene 的连续 Shot；
2. 识别既有 bootstrap Media 为 SHOT_KEY_IMAGE，而不是 Character Master；
3. 选择 1-reference Character 生成和 0-reference Scene 生成；
4. 发现并使用当前 verified Comfy Cloud 官方实现；
5. 执行 Drama stable Media → resolve → upload 的 Provider handoff；
6. 等待两个 Provider job 到 terminal `completed`。

Provider 输出无法被 Host 获取为本地文件，导致 Review/import 停止。因此自主编排能力已实际触发，但完整 E2E 未完成：

```text
PLUGIN_DRIVEN_VISUAL_ORCHESTRATION = BLOCKED
```

## 7. 每 Shot 生产结果

Provider 输出获取阻断发生在 Reference Review 之后、Shot 正式生产之前：

| Shot | referenceCount | generationCount | Provider/template | job | artifact | review | final mediaId |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| A | NOT_DECIDED | 0 | NOT_STARTED | NONE | NONE | BLOCKED | NONE |
| B | NOT_DECIDED | 0 | NOT_STARTED | NONE | NONE | BLOCKED | NONE |
| C | NOT_DECIDED | 0 | NOT_STARTED | NONE | NONE | BLOCKED | NONE |

本轮没有产生正式 Shot 图片，没有 revise，没有视频，没有 saved/custom/dynamic workflow。

## 8. Cross-Shot Visual Review

没有三张正式 Shot 图片，无法进行跨 Shot 比较：

| Dimension | Shot A | Shot B | Shot C | Consistency |
| --- | --- | --- | --- | --- |
| Face | NOT_RUN | NOT_RUN | NOT_RUN | BLOCKED |
| Age | NOT_RUN | NOT_RUN | NOT_RUN | BLOCKED |
| Hair / Beard | NOT_RUN | NOT_RUN | NOT_RUN | BLOCKED |
| Costume | NOT_RUN | NOT_RUN | NOT_RUN | BLOCKED |
| Scene | NOT_RUN | NOT_RUN | NOT_RUN | BLOCKED |
| Lighting | NOT_RUN | NOT_RUN | NOT_RUN | BLOCKED |

不得将 Provider job completed 等同于视觉质量通过。

## 9. Media Persistence

```text
standard reference Asset persistence = NOT_PERFORMED
standard reference Media persistence = NOT_PERFORMED
Shot A → NONE
Shot B → NONE
Shot C → NONE
SHOT_MEDIA_IMPORT = BLOCKED
SHOT_MEDIA_PERSISTENCE = BLOCKED
MEDIA_BYTE_EQUALITY = BLOCKED（正式 MinIO bootstrap 基线的 byte equality 已 PASS）
REFERENCE_REUSE_READY = BLOCKED
```

Artifacts：

- [bootstrap-liling-shot-key.png](artifacts/batch5-1/bootstrap-liling-shot-key.png) — 既有 stable bootstrap 的本地校验副本，不是新建 Master 或 Shot 输出。

本轮生成输出未写入 artifacts，因为实际字节获取失败；没有用任务状态或 provider filename 伪造图片文件。

## 10. 真实问题

1. 正式 MinIO 阻断已排除：`192.168.1.86:9000` 健康检查和既有 Media 字节下载均 PASS。
2. Comfy Cloud 两个 Provider job 均成功，但 `get_output` 的短链在宿主 shell 中重定向至 `storage.googleapis.com`，TLS/egress 连接失败。
3. 由于输出文件不可读，不能满足 Skill 的“fetch local output → Visual Review PASS → Media import”顺序；Drama `media.import_media` 对 Comfy 输出 URL 也返回 provider fetch failure。
4. 未修改 Drama plugin source、Drama MCP、Java、DB schema、contracts；未新增 workflow/router/provider framework。

最小下一步是恢复当前 Host 对 Comfy Cloud output storage 的可达性，或提供等价的当前 verified output-fetch capability；恢复后应从本轮两个已完成 job 重新 fetch 并先做真实 Reference Review，再按原上限继续，不应重新提交已完成的 Reference 任务。

## 11. 统一验收字段

```text
FORMAL_OBJECT_STORAGE = PASS

CHARACTER_MASTER_REFERENCE = BLOCKED
SCENE_MASTER_REFERENCE = BLOCKED
REFERENCE_ASSET_PERSISTENCE = BLOCKED

DRAMA_MEDIA_TO_VISUAL_PROVIDER = PASS

RUNTIME_VISUAL_PROVIDER_PREFLIGHT = PASS

SHOT_COUNT = 0
MULTI_SHOT_GENERATION = BLOCKED

SHOT_A_REFERENCE_COUNT = NOT_DECIDED
SHOT_B_REFERENCE_COUNT = NOT_DECIDED
SHOT_C_REFERENCE_COUNT = NOT_DECIDED

SHOT_A_VISUAL_REVIEW = BLOCKED
SHOT_B_VISUAL_REVIEW = BLOCKED
SHOT_C_VISUAL_REVIEW = BLOCKED

CHARACTER_IDENTITY_CONSISTENCY = BLOCKED
AGE_CONSISTENCY = BLOCKED
HAIR_BEARD_CONSISTENCY = BLOCKED
COSTUME_CONSISTENCY = BLOCKED
SCENE_CONSISTENCY = BLOCKED
LIGHTING_CONTINUITY = BLOCKED

CROSS_SHOT_VISUAL_CONSISTENCY = BLOCKED

SHOT_MEDIA_IMPORT = BLOCKED
SHOT_MEDIA_PERSISTENCE = BLOCKED
MEDIA_BYTE_EQUALITY = BLOCKED
REFERENCE_REUSE_READY = BLOCKED

PLUGIN_DRIVEN_VISUAL_ORCHESTRATION = BLOCKED

CUSTOM_WORKFLOW_CREATED = NO
SAVED_WORKFLOW_CREATED = NO
DYNAMIC_WORKFLOW_INTRODUCED = NO

DRAMA_PLUGIN_SOURCE_CHANGED = NO
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO

BATCH_5_1 = BLOCKED
```
