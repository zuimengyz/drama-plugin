# Batch 5.1 — Reference-driven Multi-Shot Visual Production E2E 执行报告（Runtime Provider 阻断）

> 执行日期：2026-08-17  
> 报告编号：24（既有 23 号报告未覆盖）  
> 执行范围：正式对象存储轻量确认、已安装 Skill/Host adapter 读取、Drama/Visual runtime preflight。  
> 未执行：Reference 生成、Asset/Media 新建、Shot 生成、Provider 上传、付费任务、Media 回写、源码或数据库修改。

## 1. 执行摘要

本轮在 Batch 5.1R 已恢复 Stable Media `media_f1048149fd0f485c822481f91ea6a894` 后重新进入 Batch 5.1。正式 MinIO `192.168.1.86:9000` 健康；紧邻本轮的恢复验收已经通过 Java `media.get_media`、`media.resolve_media`、正式 signed URL 下载和 SHA-256/byte equality，因此对象存储基线成立。

执行时按已安装的 `asset-resolution` 与 `shot-production` Skill 做 runtime preflight。当前 Host 的视觉生产相关 MCP 中只有 `drama-tools`，没有注册 `comfy-cloud`；本会话也没有暴露 `visual.template.discover`、`visual.input.upload`、`visual.image.generate`、`visual.job.wait`、`visual.output.fetch` 所需的 Provider tools。

`shot-production` 明确要求 Provider 缺失时返回 `VISUAL_PROVIDER_UNAVAILABLE` 并停止，禁止安装、配置、模拟 Provider，也禁止把 Drama 的旧 `production.generate_image` 误判为当前视觉 Provider。因此本轮没有创建 Character/Scene Master Reference，没有启动任何付费生成，没有创建 Asset/Media，也没有进入三 Shot 生产。

```text
FORMAL_OBJECT_STORAGE = PASS
VISUAL_PROVIDER_UNAVAILABLE
RUNTIME_VISUAL_PROVIDER_PREFLIGHT = FAIL
BATCH_5_1 = BLOCKED
```

## 2. 正式对象存储

轻量确认：

```text
formal endpoint = 192.168.1.86:9000
MinIO health HTTP = 200
baseline stable media get = PASS
baseline stable media resolve = PASS
baseline formal download HTTP = 200
baseline MIME = image/png
baseline size = 1,859,767 bytes
baseline SHA-256 = d665fdf7016cfa3231b251067682f1733e4b71979be886f2fb454d90929b6539
baseline byte equality = PASS

FORMAL_OBJECT_STORAGE = PASS
```

本轮未创建新的 storage smoke Media；已有正式对象与紧邻本轮的 Batch 5.1R 验收足以证明 Java/Media resolve/正式 bucket 链路，不为 preflight 阻断扩大业务写入。

## 3. 试验对象

继承目标：

```text
workId = work_4cf81e8862234727b082cf2115ec699b
scriptId = script_5f16ca3b7a3b4b2e80b2f2711e37b2ce
episodeId = episode_3a900d6a26b246889970af5b7f5a1475
sceneId = scene_399ace55923e47be8092eb808d7d284c
baseline shotId = shot_11b46c83ee77483fb01c6903cfa198c3
baseline mediaId = media_f1048149fd0f485c822481f91ea6a894
```

Visual Provider preflight 在正式生产上下文读取和三 Shot 最终选择前即失败。为遵守“Provider 不可用时停止”和“不创建假的 Shot”，本轮未声明三个目标 Shot：

```text
SHOT_COUNT = 0
```

## 4. Standard Reference

### Character

计划业务身份为“李陵 Character Master Reference”，允许 bootstrap 的稳定来源 Media 已恢复且可 resolve。但 Provider 不可用，未执行生成、Review 或持久化。

```text
CHARACTER_MASTER_REFERENCE = BLOCKED
character assetId = NOT_CREATED
character mediaId = NOT_CREATED
```

### Scene

计划业务身份为“苏武穹庐 Scene Master Reference”。Provider 不可用，未执行生成、Review 或持久化。

```text
SCENE_MASTER_REFERENCE = BLOCKED
scene assetId = NOT_CREATED
scene mediaId = NOT_CREATED
REFERENCE_ASSET_PERSISTENCE = BLOCKED
```

## 5. Drama Media → Visual Provider

Drama 侧 stable Media 已存在并可从正式存储 resolve；但 Host 没有提供 Provider 的上传、生成、等待和输出取回能力，链路停在 handoff preflight：

```text
stable Drama Media = READY
media resolve = READY
visual provider handoff = UNAVAILABLE
DRAMA_MEDIA_TO_VISUAL_PROVIDER = BLOCKED
```

没有使用本地 Batch 5 artifact、旧 Provider filename 或无 stable mediaId 的图片绕过该门禁。

## 6. Plugin 自主编排

本任务 Prompt 只描述业务目标，没有指示底层 Provider Tool 顺序。已安装 `shot-production` Skill 自主加载 visual-provider capability reference，并正确完成以下判断：

1. 视觉执行需要 Drama stable Asset/Media discovery、resolve 与 import；
2. 正式 reference 必须走 `Asset → Media → resolve → Provider`；
3. Host 必须提供 template discovery、input upload、image generation、job wait、output fetch；
4. 当前 Host 缺失外部 visual provider，应返回 `VISUAL_PROVIDER_UNAVAILABLE`；
5. 不得安装、模拟 Provider，或退回旧 `production.generate_image` 假装 READY。

这证明 Skill 的失败边界被正确执行，但未发生真实 Provider handoff 和 Media 回写，故不能把生产编排验收写成 PASS：

```text
PLUGIN_DRIVEN_VISUAL_ORCHESTRATION = BLOCKED
```

## 7. 每 Shot 生产结果

Provider preflight 阻断发生在任何付费执行前：

```text
SHOT_A_REFERENCE_COUNT = NOT_DECIDED
SHOT_B_REFERENCE_COUNT = NOT_DECIDED
SHOT_C_REFERENCE_COUNT = NOT_DECIDED

SHOT_A_GENERATION_COUNT = 0
SHOT_B_GENERATION_COUNT = 0
SHOT_C_GENERATION_COUNT = 0

SHOT_A_VISUAL_REVIEW = BLOCKED
SHOT_B_VISUAL_REVIEW = BLOCKED
SHOT_C_VISUAL_REVIEW = BLOCKED

MULTI_SHOT_GENERATION = BLOCKED
```

没有 Provider、Template、job identity、输出 artifact、最终 mediaId 或 revise 可记录。

## 8. Cross-Shot Visual Review

三张 Shot 图片均未生成，因此跨 Shot 一致性没有可比较样本。以下为阻断状态，不是视觉质量 FAIL：

| Dimension | Shot A | Shot B | Shot C | Consistency |
| --- | --- | --- | --- | --- |
| Face | 未生成 | 未生成 | 未生成 | BLOCKED |
| Age | 未生成 | 未生成 | 未生成 | BLOCKED |
| Hair / Beard | 未生成 | 未生成 | 未生成 | BLOCKED |
| Costume | 未生成 | 未生成 | 未生成 | BLOCKED |
| Scene | 未生成 | 未生成 | 未生成 | BLOCKED |
| Lighting | 未生成 | 未生成 | 未生成 | BLOCKED |

```text
CROSS_SHOT_VISUAL_CONSISTENCY = BLOCKED
```

## 9. Media Persistence

没有 Review PASS 的新图片，因此没有调用 Media import，也没有创建替代 Media：

```text
SHOT_MEDIA_IMPORT = BLOCKED
SHOT_MEDIA_PERSISTENCE = BLOCKED
MEDIA_BYTE_EQUALITY = BLOCKED
REFERENCE_REUSE_READY = BLOCKED
```

## 10. 真实问题

OpenAI/Codex Host adapter 的 `agents/openai.yaml` 已声明可选依赖：

```text
value = comfy-cloud
url = https://cloud.comfy.org/mcp
```

但本次真实 Host runtime 没有把该依赖实例化为可调用 MCP；`codex mcp list` 的视觉生产相关条目中只有 `drama-tools`、没有 `comfy-cloud`，当前 Agent tool runtime 也没有 visual provider tools。由此产生的真实问题是：

> Skill adapter 声明了外部能力依赖，但当前 Host 会话没有提供该依赖，Production E2E 无法开始。

本轮没有通过修改 Plugin、MCP、Java、Provider 配置或 Workflow 来掩盖该问题。下一次重跑的前置条件是：由 Host 在任务开始前提供并认证 adapter 声明的 visual provider；本批本身不执行安装或登录。

## 11. 统一验收结论

```text
FORMAL_OBJECT_STORAGE = PASS

CHARACTER_MASTER_REFERENCE = BLOCKED
SCENE_MASTER_REFERENCE = BLOCKED
REFERENCE_ASSET_PERSISTENCE = BLOCKED

DRAMA_MEDIA_TO_VISUAL_PROVIDER = BLOCKED

RUNTIME_VISUAL_PROVIDER_PREFLIGHT = FAIL

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

VISUAL_PROVIDER_UNAVAILABLE
BATCH_5_1 = BLOCKED
```
