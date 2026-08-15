# Batch 5 — Drama Visual Production E2E（单 Shot 图片闭环）执行报告

> 执行日期：2026-08-15  
> 报告编号：21  
> 执行范围：一个真实 Shot、一张最终图片、0–3 固定 reference 策略、官方 Comfy Cloud 模板、Drama Media 导入与回读。  
> 未执行：整集批量、视频、Saved/Custom Workflow、动态 Workflow、Drama/Java/MCP/DB 源码或契约修改。

## 1. 执行摘要

本批基于 Batch 4 保留的真实“苏武北海十九年”数据，选择 Shot `5-2-06 / 反问` 完成了单 Shot 图片生产闭环：

```text
Work / Script / Episode / Scene / Shot stable-ID reads
→ existing Asset / Media discovery
→ 0 reference decision
→ official TEXT_TO_IMAGE template
→ Comfy Cloud real job
→ local download and visual review
→ Drama media.import_media
→ Java / MySQL / MinIO persistence
→ media.get_media / list_media / resolve_media
→ resolved file download and byte equality verification
```

真实结果：

- Shot 上下文完整，父级稳定 ID 可逐层回读；
- 现有 Asset 为 0，唯一既有 Media 是无业务关联的存储测试图，未伪造复用；
- `referenceCount = 0`，按冻结策略选择官方 `api_google_nano_banana2_text_to_image`；
- Comfy job `4c7e2b93-0beb-4e82-a736-fd1e3fbb9136` 完成；
- 输出通过最小视觉 Review，无修正重试；
- 导入得到稳定 Media `media_f1048149fd0f485c822481f91ea6a894`；
- Media 与 Shot 稳定关联，列表中恰好出现一次；
- `resolve_media` 回下载文件与原生成文件字节完全一致。

结论：

```text
SHOT_VISUAL_PRODUCTION_E2E = PASS
BATCH_5 = PASS
```

## 2. 继承基线与本批边界

直接继承并未重复执行 C1–C1.3 的基础验证：

```text
COMFY_CLOUD_MCP_BASELINE = PASS
TEXT_TO_IMAGE = PASS
REFERENCE_IMAGE_1 = PASS
OFFICIAL_REFERENCE_IMAGE_2 = PASS
OFFICIAL_REFERENCE_IMAGE_3 = PASS
REFERENCE_TO_IMAGE_UP_TO_3 = PASS
```

冻结模板选择策略：

```text
0 reference -> official TEXT_TO_IMAGE
1 reference -> official single-reference template
2 references -> image_qwen_image_edit_2511
3 references -> api_bfl_flux2_max_sofa_swap
```

本批没有返回 Mage 路线，没有搜索模板竞赛，没有创建 Saved Workflow、自定义 Workflow 或 graph。

## 3. 使用的 Drama Skill 与决策影响

本批使用当前 Host 已安装版本：

```text
drama-plugin cache = 0.1.0+codex.20260815040146
skills = shot-production, asset-resolution
```

`asset-resolution` 的实际影响：

- 先检索已有稳定 Asset/Media，再判断是否适合；
- 拒绝与当前 Shot 无关的存储测试 Media；
- 没有为了凑 reference 创建伪 Asset；
- 当前产物是 Shot 专属 still，不是已批准的跨 Shot 标准角色卡，因此未新建 Asset。

`shot-production` 的实际影响：

- 使用 Shot/Scene 稳定 ID 构建生产上下文；
- 将最终物理图片作为稳定 Media 导入；
- 保留返回的 `mediaId` 并明确业务角色；
- 在请求的媒体存在且角色清晰后停止，没有自动扩展到其他 Shot 或视频。

## 4. 运行环境恢复

任务开始时 `codex mcp list` 显示 `drama-tools` 已注册，但 `127.0.0.1:8765` 没有运行进程。按仓库既有方式恢复：

```text
Java 17 Drama Service -> 127.0.0.1:8080
Drama MCP Service      -> 127.0.0.1:8765/mcp
```

没有修改配置文件或源码。Java 与 MCP 均用运行时环境变量启动，MCP 使用当前 Plugin 工作区和既有 HTTP provider 配置。

对象存储诊断：

1. 首次 `media.import_media` 返回 `STORAGE_ERROR`，没有 mediaId；
2. MySQL、Java、MCP 均正常；本地 `9000` MinIO 健康，但只读 `headBucket` 对 Java 当前配置返回 HTTP 403；
3. 清除代理后仍为同一错误，排除代理；
4. 根因分类为现有 MinIO 与 Java 配置的运行时凭据不匹配；
5. 不触碰现有 `9000` 实例，在 `9100` 启动隔离临时 MinIO，创建既有 `drama-media` bucket，并通过 Java 运行时环境变量连接；
6. 同一文件随后导入、读取、解析成功。

这一收口没有修改 Java Service、MCP Service、数据库结构或 Tool Contract。

## 5. 试点 Shot 选择

对 Scene `scene_399ace55923e47be8092eb808d7d284c` 的 10 个真实 Shot 进行只读筛选后，选择：

| Field | Value |
| --- | --- |
| shotId | `shot_11b46c83ee77483fb01c6903cfa198c3` |
| shotNo | `5-2-06` |
| title | `反问` |
| shotType | `李陵正面近景` |
| sceneId | `scene_399ace55923e47be8092eb808d7d284c` |

选择理由：

- 单一可见人物；
- 80mm 固定正面近景；
- 只有停手、避开视线两项微动作；
- 穹庐背景简单；
- 情绪目标清晰：被苏武反问刺中后的压抑、羞耻与自控；
- 原 Shot 已明确“单人微动作镜头，可稳定生成”；
- 不涉及多人调度、酒液连续性、火势转场、交叠手部或主动运镜。

```text
SHOT_SELECTED = PASS
```

## 6. Work → Shot 上下文构建

稳定父级链：

```text
workId    = work_4cf81e8862234727b082cf2115ec699b
scriptId  = script_5f16ca3b7a3b4b2e80b2f2711e37b2ce
episodeId = episode_3a900d6a26b246889970af5b7f5a1475
sceneId   = scene_399ace55923e47be8092eb808d7d284c
shotId    = shot_11b46c83ee77483fb01c6903cfa198c3
```

最小生产上下文：

- Work：苏武在北海饥寒、遗忘与李陵劝降中拒绝让苦难替自己决定身份；
- Script 主线：苏武从奉使、被扣到十九年后归汉，持续重新选择不降；
- Episode 目标：苏武追问家人与归期，李陵借劝降证明自己的生存选择仍可理解；
- Scene：苏武穹庐内，入夜、火弱、风急；旧友情暂时覆盖公开敌对，但劝降正转为李陵自身的控诉；
- Shot：苏武画外问“你的母亲呢？”，李陵扶汉节的手停止摩挲残旄，视线短暂向画右下避，随后静默四秒；
- 连续性：李陵仍扶汉节；必须无王印；视线方向保持朝画右的苏武位置。

本次目标图片用途：

```text
SHOT_KEY_IMAGE / shot still
```

```text
SHOT_CONTEXT_BUILT = PASS
```

## 7. Asset / Media 与 reference 选择

定向检索范围：

```text
CHARACTER = 李陵
COSTUME   = 李陵 / 胡服 / 皮毛 / 无王印
LOCATION  = 苏武穹庐内 / 入夜 / 火弱
PROP      = 汉节 / 残余旄毛
```

真实发现：

```text
existing Asset count = 0
suitable reference Media count = 0
```

唯一既有图片 Media：

```text
mediaId = media_2cd480788fb541e69319a7ff591028c8
purpose = MEDIA_STORAGE_E2E
scope workId = work_49610e15461546a09ff238cd1ad05404
shotId = null
content source = manual-test-file
```

拒绝理由：它属于另一 Work 的通用存储 E2E，没有角色、服装、场景、道具、Asset 或目标 Shot 关联，不能作为李陵参考图。

最终选择：

```text
reference count = 0
reference_1 = none
reference_2 = none
reference_3 = none
```

0 是冻结策略中的合法输入。输入侧没有 reference，故不存在要解析的 reference Media；本批通过最终产物的 `import → resolve → download` 完成真实 `media.resolve` E2E。

```text
REFERENCE_SELECTION = PASS
```

## 8. Comfy 模板选择

按 reference 数量直接选择：

```text
reference count = 0
template = api_google_nano_banana2_text_to_image
template role = official TEXT_TO_IMAGE
```

没有重新搜索模板，也没有把模板名写入 Drama 业务契约或持久化 Domain Content。

```text
COMFY_TEMPLATE_SELECTION = PASS
```

## 9. 正式 Prompt

```text
Historical drama shot still, Western Han era. Li Ling, a weathered middle-aged
East Asian man in a worn Xiongnu fur robe, sits inside Su Wu's simple felt yurt
at night. 80mm frontal close-up, single character centered, his hand visible at
the lower edge lightly holding a weathered Han envoy tally with sparse yak-tail
tufts. Just after an off-screen question about his mother, his fingers have
suddenly stopped moving and his gaze drops briefly toward frame right,
restrained pain, shame and self-control in his face. Weak dying firelight, cold
wind implied through the dark felt interior, low-key warm-and-cold cinematic
lighting, realistic skin and fabric, shallow depth of field, coherent historical
set, shot key image, no crown, no royal seal, no text, no modern objects.
```

Prompt 覆盖人物、服装、动作、情绪、场景、光线、镜头用途与连续性禁项。

## 10. Comfy Cloud 真实生成

调用链：

```text
run_template(confirm=true)
-> job_id 4c7e2b93-0beb-4e82-a736-fd1e3fbb9136
-> wait_for_job
-> completed
-> get_output
-> signed URL
-> local download
```

输出：

| Field | Value |
| --- | --- |
| Cloud filename | `bf1ec28e76f83307e1fa65a8913b5c9209cdb733f17147993d05159c02ca78e7.png` |
| 本地路径 | `plugin/docs/reports/artifacts/batch5/shot_11b46c83ee77483fb01c6903cfa198c3-visual-production.png` |
| 类型 | PNG, 8-bit RGBA, non-interlaced |
| 分辨率 | 1024×1024 |
| 大小 | 1,859,767 bytes |
| SHA-256 | `d665fdf7016cfa3231b251067682f1733e4b71979be886f2fb454d90929b6539` |
| Credits | 服务端未返回数值 |

服务端警告 node `24` 的 `batch_size=5` 在执行图生效但不能回写 UI workflow；`get_output` 只返回一个文件。本批只下载、Review、导入这一张最终图片，没有运行第二个生成 job。该默认批量行为是后续成本控制风险，但不改变本批“一 Shot / 一最终 Media”的结果。

```text
COMFY_IMAGE_GENERATION = PASS
```

## 11. 最小视觉 Review

检查结果：

| Check | Result |
| --- | --- |
| 非空有效图片 | PASS |
| 单一人物主体 | PASS |
| 胡服皮毛 | PASS |
| 穹庐夜景 / 弱火冷调 | PASS |
| 低头避视、压抑停顿 | PASS |
| 手持残旄汉节 | PASS |
| 无王印 | PASS |
| 无文字 / 无现代物 | PASS |
| 与 Shot 基本一致 | PASS |

已知轻微偏差：构图比严格 80mm 紧近景略宽，更接近带手部信息的中近景；但人物表演、关键道具与情绪均清楚，且满足首条闭环产物用途。

结论：第一次结果可用，没有执行允许的一次修正重试。

```text
VISUAL_REVIEW = PASS
```

## 12. Drama Media 导入

导入方式：

```text
media.import_media
source_uri = reviewed local file URI
workId = work_4cf81e8862234727b082cf2115ec699b
shotId = shot_11b46c83ee77483fb01c6903cfa198c3
mediaType = IMAGE
purpose = SHOT_KEY_IMAGE
assetId = null
```

Domain Content：

```json
{
  "shotNo": "5-2-06",
  "role": "shot key image",
  "subject": "李陵在穹庐内被苏武画外反问后停手垂目",
  "visualReview": "PASS",
  "referenceCount": 0
}
```

成功返回：

| Field | Value |
| --- | --- |
| mediaId | `media_f1048149fd0f485c822481f91ea6a894` |
| workId | `work_4cf81e8862234727b082cf2115ec699b` |
| shotId | `shot_11b46c83ee77483fb01c6903cfa198c3` |
| mediaType | `IMAGE` |
| purpose | `SHOT_KEY_IMAGE` |
| sourceRef | `storage:bfabf888-4e4f-4c75-851a-2e6089a3c3f9` |
| mimeType | `image/png`（resolve 返回） |
| fileSize | 1,859,767 bytes |
| contentHash | `d665fdf7016cfa3231b251067682f1733e4b71979be886f2fb454d90929b6539`（本地与回下载一致性校验） |

`sourceRef` 仅作为不透明稳定标识使用；报告未记录 object key、凭据或 signed URL。

```text
DRAMA_MEDIA_IMPORT = PASS
```

## 13. Media resolve 与回下载

导入后执行：

```text
media.get_media(media_f1048149fd0f485c822481f91ea6a894) = PASS
media.resolve_media(media_f1048149fd0f485c822481f91ea6a894) = PASS
resolved mimeType = image/png
resolved sizeBytes = 1,859,767
resolved expiry = 15 minutes
```

临时 URL 未写入报告。回下载文件：

```text
plugin/docs/reports/artifacts/batch5/
shot_11b46c83ee77483fb01c6903cfa198c3-resolved.png
```

一致性：

```text
original size  = 1,859,767
resolved size  = 1,859,767
original SHA-256 = d665fdf7016cfa3231b251067682f1733e4b71979be886f2fb454d90929b6539
resolved SHA-256 = d665fdf7016cfa3231b251067682f1733e4b71979be886f2fb454d90929b6539
cmp byte equality = PASS
```

```text
MEDIA_RESOLVE_E2E = PASS
```

## 14. Shot 级长期记忆闭环

持久化后复核：

```text
media.list_media(media_type=IMAGE)
-> target media presence count = 1
-> shotId = shot_11b46c83ee77483fb01c6903cfa198c3
-> purpose = SHOT_KEY_IMAGE
-> visualReview = PASS
```

随后重新 `shot.get_shot`：

```text
shotId = shot_11b46c83ee77483fb01c6903cfa198c3
sceneId = scene_399ace55923e47be8092eb808d7d284c
shotNo = 5-2-06
title = 反问
shotType = 李陵正面近景
```

Shot 未被修改。长期关联位于 Media Stable Envelope 的 `shotId`，符合既有契约。后续 Agent 可通过稳定 `mediaId` 读取/解析，并把它作为 Shot Media 或后续视觉参考；它不是“生成完就丢失”的临时文件。

本批没有创建 Asset：该图片是一个 Shot 专属静帧，不等同于经过审核的跨 Shot 标准李陵角色卡。避免为闭环制造错误的长期 Asset 身份。

```text
SHOT_MEMORY_PERSISTENCE = PASS
```

## 15. Artifact 清单

```text
plugin/docs/reports/artifacts/batch5/
├── shot_11b46c83ee77483fb01c6903cfa198c3-visual-production.png
└── shot_11b46c83ee77483fb01c6903cfa198c3-resolved.png
```

两个文件逐字节相等。未保存 OAuth token、对象存储凭据、Comfy signed URL 或 Drama resolve URL。

## 16. 源码与契约保护

执行后：

```text
comfy-cloud = enabled
drama-tools = enabled

drama-plugin tracked diff = empty
drama-mcp-service tracked diff = empty
drama-service tracked diff = empty
git diff --check = PASS
```

未修改：

- Drama Plugin Tool Contract / Skills / business logic；
- Drama MCP Service；
- Java Service / Domain / DTO；
- MySQL schema；
- Media / Asset Contract；
- Comfy Saved/Custom Workflow。

唯一仓库新增内容是 Batch 5 artifact 与本报告。

## 17. 阻断点、风险与已知不足

### 已关闭

- Drama Java/MCP 进程未运行：已按既有机制恢复；
- 当前 9000 MinIO 与 Java 配置凭据不匹配：已用隔离 9100 MinIO 完成本批真实 E2E；
- 导入前两次 `STORAGE_ERROR` 均未创建 mediaId；最终只存在一个成功 Media 记录。

### 剩余风险

- 本批对象数据写入隔离的临时 MinIO 运行目录 `/tmp/drama-batch5-minio`。契约、DB、S3 import/resolve 链已真实通过，但在多 Shot 扩产前必须把 Java 指向正式持久对象存储并验证凭据/bucket 运维配置；不能把 `/tmp` 作为生产长期存储。
- 现有 Work 尚无标准李陵角色卡、服装卡和穹庐场景卡，因此本批使用 0 reference。人物跨 Shot 一致性尚未验证。
- 官方 T2I 模板报告 `batch_size=5`，但只返回一个输出文件。扩产前应明确该模板可覆盖的批量参数或选择稳定单输出配置，避免不可见的额外费用；本批不修改 Workflow。
- Comfy Cloud 在多个独立 Host 会话间仍出现 OAuth refresh token reuse 日志；本次生成已完成，不影响现有 artifact，但扩产前宜使用单一长生命周期 Host 会话。
- 本批视觉 Review 为人工最小可用性判断，没有人物一致性评分、历史真实性 rubric 或自动 revise loop。

## 18. 下一步建议

Batch 5 已证明一条 Shot 图片可从 Drama 上下文出发，经 Comfy 生成后回到稳定 Media 长期记忆。

下一步建议按顺序：

1. 将 Java Media Storage 切换到正式持久 MinIO/S3 配置并复核现有 Media 的迁移/保留策略；
2. 为李陵、苏武及穹庐建立经过审核的标准 Asset/Reference Media，而不是复用测试图；
3. 扩到少量多 Shot 图片生产，验证角色与场景一致性；
4. 再进入 Start/End Frame 与视频人工 confirmation E2E；
5. 最后完善系统化视觉 Review。

不要返回 Mage Saved Workflow，也不要构建动态 Workflow framework。

## 19. 统一验收结论

```text
SHOT_SELECTED = PASS
SHOT_CONTEXT_BUILT = PASS
REFERENCE_SELECTION = PASS
MEDIA_RESOLVE_E2E = PASS
COMFY_TEMPLATE_SELECTION = PASS
COMFY_IMAGE_GENERATION = PASS
VISUAL_REVIEW = PASS
DRAMA_MEDIA_IMPORT = PASS
SHOT_MEMORY_PERSISTENCE = PASS

SHOT_VISUAL_PRODUCTION_E2E = PASS
BATCH_5 = PASS
```

最终回答：本批已完成一个真实 Shot 的单图片生产闭环。图片不再是本地孤立测试产物，而是以稳定 Media ID、Work/Shot scope、业务 purpose 和可重新解析的对象存储内容回到 Drama 长期记忆体系。
