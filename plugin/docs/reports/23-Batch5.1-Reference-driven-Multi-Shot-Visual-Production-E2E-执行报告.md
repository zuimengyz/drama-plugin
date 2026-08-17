# Batch 5.1 — Reference-driven Multi-Shot Visual Production E2E 执行报告

> 执行日期：2026-08-16  
> 报告编号：23  
> 最终状态：`BLOCKED`  
> 停止阶段：正式对象存储前置门槛

## 1. 执行摘要

本批没有进入 Master Reference 生成或三个 Shot 的图片生产。按照任务的硬门槛，首先把 Java Service 从 Batch 5 遗留的临时 `127.0.0.1:9100` 存储切换到正式、持久的系统 MinIO `127.0.0.1:9000`，然后只读验证 Batch 5 稳定 Media：

```text
media_f1048149fd0f485c822481f91ea6a894
```

`media.resolve_media` 能生成正式 9000 的签名 URL，但对象连续两次即时下载均返回 HTTP 404，没有文件落地。该 Media 因而不能作为本批要求的 Drama Stable Media → Visual Provider reference 输入。

任务明确要求正式对象存储不可用时立即停止，且禁止继续使用临时 9100。因此本批没有：

- 调用 Comfy 生成；
- 选择或生产三个 Shot；
- 创建 Character/Scene Master Reference；
- 创建 Asset/Media；
- 修改数据库、Java、MCP、Drama Tool Contract 或 Skill；
- 启动新的临时对象存储。

```text
FORMAL_OBJECT_STORAGE = BLOCKED
BATCH_5_1 = BLOCKED
```

## 2. 继承基线

本批直接继承且没有重复执行：

```text
BATCH_5 = PASS
BATCH_5_0_1 = PASS
REFERENCE_TO_IMAGE_UP_TO_3 = PASS
VISUAL_CAPABILITY_CONTRACT = PASS
VISUAL_SKILL_ORCHESTRATION = PASS
```

实际 Host 加载的生产 Skill 为：

```text
drama-plugin version = 0.1.0+codex.20260815155920
shot-production
asset-resolution
```

## 3. 正式对象存储

### 3.1 正式服务事实

系统级正式 MinIO：

```text
service = minio.service
status = active (running)
endpoint = http://127.0.0.1:9000
data directory = /data/minio
health = HTTP 200
bucket = drama-media
```

这不是 Batch 5 使用的 `/tmp/drama-batch5-minio`，也不是临时 9100 进程。

### 3.2 Java 运行路径纠正

检查发现任务开始时占用 8080 的旧 Java 进程仍配置：

```text
DRAMA_MEDIA_STORAGE_ENDPOINT=http://127.0.0.1:9100
DRAMA_MEDIA_STORAGE_BUCKET=drama-media
```

该进程被正常停止。随后使用 `/etc/default/minio` 中的正式凭据，以运行时环境变量启动现有 Java 17 jar：

```text
DRAMA_MEDIA_STORAGE_ENDPOINT=http://127.0.0.1:9000
DRAMA_MEDIA_STORAGE_BUCKET=drama-media
```

凭据没有打印、写入仓库或进入报告。Java 在 8080 启动成功；Drama MCP 8765 保持原配置。

### 3.3 Stable Media 只读验收

对象：

```text
mediaId = media_f1048149fd0f485c822481f91ea6a894
workId = work_4cf81e8862234727b082cf2115ec699b
shotId = shot_11b46c83ee77483fb01c6903cfa198c3
purpose = SHOT_KEY_IMAGE
mediaType = IMAGE
declared size = 1,859,767 bytes
visualReview = PASS
```

第一次 resolve：

```text
endpoint = 127.0.0.1:9000
resolve = PASS
download = HTTP 404
```

为排除旧签名，立即重新 resolve 并下载：

```text
fresh signed URL = YES
endpoint = 127.0.0.1:9000
download = HTTP 404
local file = MISSING
```

`resolve` 只证明 Java 能签发 URL，不证明物理 object 存在。连续 404 证明当前正式 bucket 中缺少该稳定 Media 对应的 object。结合 Batch 5 使用临时 9100 的已知历史，最可能根因是既有数据库 Media 记录的物理对象没有进入正式 9000；本报告不把推断写成已完成迁移事实。

判定：

```text
JAVA_FORMAL_STORAGE_CONFIGURATION = PASS
FORMAL_MINIO_SERVICE = PASS
EXISTING_STABLE_MEDIA_OBJECT = FAIL
FORMAL_MEDIA_RESOLVE_DOWNLOAD = FAIL
FORMAL_OBJECT_STORAGE = BLOCKED
```

## 4. 试验对象

由于正式对象存储门槛失败，按要求立即停止，未进入三个 Shot 的读取与选择。

仅用于门槛验证的继承对象：

```text
workId = work_4cf81e8862234727b082cf2115ec699b
sceneId = scene_399ace55923e47be8092eb808d7d284c
baseline shotId = shot_11b46c83ee77483fb01c6903cfa198c3
baseline mediaId = media_f1048149fd0f485c822481f91ea6a894
```

```text
SHOT_COUNT = 0
```

## 5. Standard Reference

### Character

计划中的“李陵 Character Master Reference”没有生成。其允许的 bootstrap 来源 `media_f104...` 无法从正式对象存储下载，不能绕过 Drama stable Media 改用本地 Batch 5 artifact，也不能从临时 9100 取回。

```text
CHARACTER_MASTER_REFERENCE = BLOCKED
character assetId = NONE
character mediaId = NONE
```

### Scene

Character 前置已经阻断，因此没有继续生成“苏武穹庐 Scene Master Reference”。

```text
SCENE_MASTER_REFERENCE = BLOCKED
scene assetId = NONE
scene mediaId = NONE
```

## 6. Drama Media → Visual Provider

本批要求的核心新链路是：

```text
Drama stable Media
→ resolve
→ physical reference file
→ Visual Provider
```

当前只到达 `resolve`，物理下载返回 404。因此：

```text
DRAMA_MEDIA_TO_VISUAL_PROVIDER = FAIL
```

没有使用 Comfy session Cloud filename、本地 artifact 或临时图片伪造通过。

## 7. Plugin 自主编排

门槛验证 Prompt 只表达业务目标：“验证稳定 Media 能否从正式对象存储解析并下载”，没有手工指定 Visual Provider Tool 顺序。Host 自动选择最新 `shot-production`，并自行执行 Drama Media 读取/resolve、下载校验和失败停止。

这证明 Skill 的停止边界生效，但没有进入实际 Reference selection、Provider handoff、generation、review 和 import，不能把完整生产编排判为 PASS：

```text
PLUGIN_PREFLIGHT_STOP_BEHAVIOR = PASS
PLUGIN_DRIVEN_VISUAL_ORCHESTRATION = FAIL
```

## 8. 每 Shot 生产结果

正式存储门槛失败后没有产生任何 Provider job 或 artifact：

| Shot | Reference count | Generation count | Job | Artifact | Media |
| --- | ---: | ---: | --- | --- | --- |
| A | 0 | 0 | NONE | NONE | NONE |
| B | 0 | 0 | NONE | NONE | NONE |
| C | 0 | 0 | NONE | NONE | NONE |

## 9. Cross-Shot Visual Review

没有生成三个 Shot，以下维度均无法验收：

| Dimension | Shot A | Shot B | Shot C | Consistency |
| --- | --- | --- | --- | --- |
| Face | NOT_RUN | NOT_RUN | NOT_RUN | FAIL |
| Age | NOT_RUN | NOT_RUN | NOT_RUN | FAIL |
| Hair / Beard | NOT_RUN | NOT_RUN | NOT_RUN | FAIL |
| Costume | NOT_RUN | NOT_RUN | NOT_RUN | FAIL |
| Scene | NOT_RUN | NOT_RUN | NOT_RUN | FAIL |
| Lighting | NOT_RUN | NOT_RUN | NOT_RUN | FAIL |

这些 `FAIL` 表示 PASS 标准未达到，不表示已观察到具体视觉漂移。

## 10. Media Persistence

本批没有新增 Media 或 Asset，因此：

```text
Shot A → NONE
Shot B → NONE
Shot C → NONE

SHOT_MEDIA_IMPORT = FAIL
SHOT_MEDIA_PERSISTENCE = FAIL
MEDIA_BYTE_EQUALITY = FAIL
REFERENCE_REUSE_READY = FAIL
```

## 11. 真实阻断与最小下一步

真实阻断不是 Comfy 模板、跨 Shot 漂移或 Plugin Provider 选择，而是：

```text
稳定 Media 数据库记录存在
→ Java 能对正式 9000 签名
→ 正式 bucket 中目标 object 不存在
→ HTTP 404
```

下一步必须先由独立的对象存储修复动作确认并完成以下之一：

1. 将既有稳定 Media 的物理 object 正确迁移到正式 `/data/minio`，保持稳定 Media 身份与 object key；或
2. 按平台批准的正式恢复方案修复该 Media 的物理对象一致性。

修复后需要先验证：

```text
media_f104... resolve
→ HTTP 200 download
→ non-empty PNG
→ expected size/hash
```

然后重新执行 Batch 5.1。不要重新启用临时 9100，也不要通过重复创建同一 Shot Media 掩盖缺失对象。

## 12. 变更与冻结证明

本批仅新增本报告。没有新增 artifact、Asset、Media、Provider job 或数据库记录。

执行前源码状态：

```text
drama-plugin = clean
drama-mcp-service = clean
drama-service = existing application.yml modification
```

本批未修改 `application.yml`；它属于进入本批前的既有修改。

```text
CUSTOM_WORKFLOW_CREATED = NO
SAVED_WORKFLOW_CREATED = NO
DYNAMIC_WORKFLOW_INTRODUCED = NO

DRAMA_PLUGIN_SOURCE_CHANGED = NO
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO
```

## 13. 统一验收结论

```text
FORMAL_OBJECT_STORAGE = BLOCKED

CHARACTER_MASTER_REFERENCE = BLOCKED
SCENE_MASTER_REFERENCE = BLOCKED
REFERENCE_ASSET_PERSISTENCE = FAIL

DRAMA_MEDIA_TO_VISUAL_PROVIDER = FAIL

RUNTIME_VISUAL_PROVIDER_PREFLIGHT = FAIL

SHOT_COUNT = 0
MULTI_SHOT_GENERATION = BLOCKED

SHOT_A_REFERENCE_COUNT = 0
SHOT_B_REFERENCE_COUNT = 0
SHOT_C_REFERENCE_COUNT = 0

SHOT_A_VISUAL_REVIEW = FAIL
SHOT_B_VISUAL_REVIEW = BLOCKED
SHOT_C_VISUAL_REVIEW = BLOCKED

CHARACTER_IDENTITY_CONSISTENCY = FAIL
AGE_CONSISTENCY = FAIL
HAIR_BEARD_CONSISTENCY = FAIL
COSTUME_CONSISTENCY = FAIL
SCENE_CONSISTENCY = FAIL
LIGHTING_CONTINUITY = FAIL

CROSS_SHOT_VISUAL_CONSISTENCY = FAIL

SHOT_MEDIA_IMPORT = FAIL
SHOT_MEDIA_PERSISTENCE = FAIL
MEDIA_BYTE_EQUALITY = FAIL
REFERENCE_REUSE_READY = FAIL

PLUGIN_DRIVEN_VISUAL_ORCHESTRATION = FAIL

CUSTOM_WORKFLOW_CREATED = NO
SAVED_WORKFLOW_CREATED = NO
DYNAMIC_WORKFLOW_INTRODUCED = NO

DRAMA_PLUGIN_SOURCE_CHANGED = NO
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO

BATCH_5_1 = BLOCKED
```
