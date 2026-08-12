# Drama Plugin

Drama Plugin 是精简、平台无关的历史短剧 Skill Package。它提供创作方法论、稳定 Tool Contract、最小领域模型与可替换 Provider；不实现 Agent Loop、固定 Workflow、数据库、Java 服务、MCP Server 或 ComfyUI。

## 核心关系

```text
Agent Host
  ├─ Agent：读取 Context、选择 Skill、调用 Tool、判断 Result 与下一步
  ├─ Skill：历史短剧创作方法论、业务规则、最小 Context 和完成标准
  └─ Tool：无业务决策的可执行动作
       └─ MCP / HTTP：能力协议与长期事实访问接口
            ├─ Java Drama Service：Persistent Memory / System of Record
            └─ Generation Adapter：ComfyUI 或其他 Provider 的物理适配层
```

**Agent 串联 Skill；Skill 不组成固定 Workflow。** Agent 可以读取或修改上游对象、跳过不需要的阶段，并根据当前 Result 自主选择下一 Tool 或 Skill。

## 业务模型

历史研究结果默认留在 Agent Research Context，不成为 Java 长期 Domain。Agent 可以据此创作 Work：

```text
Historical Research Context
  -> Work
     -> Script
        -> Episode
           -> Scene
              -> Shot
```

箭头表达父子关系，不是状态机。长期事实只包含：

- `Work`：基于历史研究创作的文学作品；
- `Script`：Work 的影视化改编；
- `Episode`、`Scene`、`Shot`：逐级创作对象；
- `Asset`：跨 Scene、Shot 或 Agent Run 值得复用的稳定视觉记忆；
- `Media`：真实图片、视频、音频文件的稳定长期引用句柄。

父关系直接由 `Script.workId`、`Episode.scriptId`、`Scene.episodeId`、`Shot.sceneId` 表达，不存在 relation 或 binding domain。

## Skill Core

```text
skills/
├── historical-research
├── work-creation
├── script-adaptation
├── episode-development
├── scene-development
├── shot-design
├── asset-resolution
└── shot-production
```

`SKILL.md` 与 `skill.yaml` 是平台无关 Core，只依赖稳定 Tool code。`agents/openai.yaml` 是 OpenAI/Codex Host Adapter；业务规则不放在那里。

## Tool Contract

长期记忆动作保持五类稳定语义：

- `get_xxx`：已知稳定 ID 时读取唯一完整对象，不承担搜索；
- `list_xxx`：已知父级或结构范围时列举对象，可带轻量结构过滤，不等同全文搜索；
- `search_xxx`：稳定 ID 丢失、仅有名称或自然语言描述时发现候选；
- `create_xxx`：在当前 Skill 已形成足够完整的初始正式状态后，一次性创建新的长期事实并获得稳定 ID；
- `save_xxx`：基于稳定 ID 明确修订已有长期事实。它不是首次持久化，也不是 create 后的默认步骤；没有具体修订时不调用。

实际长期记忆 Tool 为：

```text
work.create_work / get_work / save_work / list_works / search_works
script.create_script / get_script / save_script / list_scripts
episode.create_episode / get_episode / save_episode / list_episodes
scene.create_scene / get_scene / save_scene / list_scenes / search_scenes
shot.create_shot / get_shot / save_shot / list_shots / search_shots
asset.create_asset / get_asset / save_asset / list_assets / search_assets
media.create_media / get_media / save_media / list_media
```

`list_episodes` 可按 `episodeNo`、`title` 过滤；`list_scenes` 可按 `order`、`location`、`character` 过滤；`list_shots` 可按 `shotNo`、`shotType`、`character` 过滤。Search 只声明自然语言发现语义，不绑定 SQL、全文索引、向量库或 RAG 技术。

恢复长期创作记忆时，Agent 可按已掌握的信息组合 Tool，例如：`work.search_works("神龙")` → `script.list_scripts(workId)` → `episode.list_episodes(scriptId, episodeNo=3)` → `scene.search_scenes(query, episodeId)` → `shot.list_shots(sceneId)` 或 `shot.search_shots(query, sceneId)`。这是一种可选恢复策略，不是硬编码 Workflow。

Script、Episode 通常通过父级 ID 与 list 发现，因此第一版不提供 `search_scripts`、`search_episodes`。Media 优先通过 `mediaId`、Asset 的 `referenceMediaIds`、Shot/Agent Context 获取，因此不提供 `search_media`。

历史研究是当前 Run 的外部能力，不是 Java CRUD Domain：

```text
research.search_sources / search_events / search_people / search_locations / verify_claim
```

生产 Tool 使用业务语义：

```text
production.generate_image
production.generate_video
production.generate_audio
```

Agent 只传 prompt、`assetId`、`mediaId` 和必要参数。Adapter 内部解析存储引用、处理上传、Provider 调用并登记 Media；workflow JSON、node id、filename、bucket、URL 和 Provider response 不得进入 Skill Core。

## Asset 与 Media

Asset 是 `assetId + type + name + description + referenceMediaIds`。已知 `assetId` 时使用 `get_asset`；未知 ID 时使用 `search_assets`，候选已包含名称、类型、说明与媒体引用等轻量判断信息。是否值得登记、是否复用以及 `FOUND/NOT_FOUND` 都由 Agent 按 `asset-resolution` 推理，服务只存最终事实。

Media 是 `mediaId + type + mimeType + storageKey + metadata`。`storageKey` 是 Adapter/服务使用的非公开稳定引用；Agent 原则上只携带 `mediaId` 及其当前语义，不依赖物理文件位置。

## Context

`DramaRunContext` 区分两类状态：

- Persistent Memory：当前任务需要的最小 Work/Script/Episode/Scene/Shot/Asset/Media 对象链；
- Run Context：selectedAssetIds、generatedMediaIds、Research Context 与临时创作状态。

Context 归 Host 管理。Plugin 的 `context.build_context` 和 `context.refresh_context` 只构建/刷新最小 payload，不维护无限膨胀的全局 Context。

## Provider 与配置

`memory`、`asset`、`research`、`production`、`media` 支持 `mock|http`；`context` 支持 `local|http`。HTTP operation path 全由配置提供，Contract 不依赖 Java Controller、FastAPI route 或 MCP 实现类。

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -ra
.venv/bin/python -m mypy src/drama_plugin
.venv/bin/python examples/build_shot_context.py
```

环境变量示例：

```text
DRAMA_PLUGIN_PROVIDER_MEMORY_MODE
DRAMA_PLUGIN_SERVICE_MEMORY_BASE_URL
DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN
```

环境值覆盖 YAML。不要提交 token。

## 边界

- Java Drama Service 是长期创作事实库，不是 Workflow Engine、Generation Engine 或任务调度器。
- MCP 是协议与能力边界，不拥有 Agent 决策。
- Generation Adapter 隔离 ComfyUI/Provider 物理细节。
- Python runtime 仅用于 Contract、Mock 与开发期验证，不是 Host 的生产调用路径。

更详细的依赖方向见 [`docs/architecture.md`](docs/architecture.md)。
