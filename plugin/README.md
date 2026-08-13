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

父关系直接由 `Script.work_id`、`Episode.script_id`、`Scene.episode_id`、`Shot.scene_id` 表达，不存在 relation 或 binding domain。Tool 输入统一使用 `snake_case`。

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

七类长期记忆的 create/save 输入统一采用 **Stable Envelope + Domain Content**：父级、身份、排序和高频检索字段保留在 Tool 顶层，Skill 确认的完整正式领域事实放入 `content` JSON Object。`content` 不是字符串化 JSON、推理草稿或 Provider 原始响应。`save_xxx` 提交修订后的完整正式状态，不支持 Patch、field mask 或 operation list；普通 save 不改变稳定父级、Asset scope/type 或 Media 物理引用。

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

`list_episodes` 可按 `episode_no`、`title` 过滤；`list_scenes` 可按 `order`、`location`、`character` 过滤；`list_shots` 可按字符串 `shot_no`、`shot_type`、`character` 过滤。Search 只声明自然语言发现语义，不绑定 SQL、全文索引、向量库或 RAG 技术。

恢复长期创作记忆时，Agent 可按已掌握的信息组合 Tool，例如：`work.search_works("神龙")` → `script.list_scripts(work_id)` → `episode.list_episodes(script_id, episode_no=3)` → `scene.search_scenes(query, episode_id)` → `shot.list_shots(scene_id)` 或 `shot.search_shots(query, scene_id)`。这是一种可选恢复策略，不是硬编码 Workflow。

Script、Episode 通常通过父级 ID 与 list 发现，因此第一版不提供 `search_scripts`、`search_episodes`。Media 优先通过 `media_id`、Asset 的 `reference_media_ids`、Shot/Agent Context 获取，因此不提供 `search_media`。

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

Agent 只传 prompt、`asset_id`、`media_id` 和必要参数。Adapter 内部解析存储引用、处理上传、Provider 调用并登记 Media；workflow JSON、node id、filename、bucket、URL 和 Provider response 不得进入 Skill Core。

## Asset 与 Media

`media.import_media` 将 `file://` 或受控 `https://` 来源经 Plugin 流式上传到
Java 管理的对象存储；`media.resolve_media` 将长期 `mediaId` 解析为临时可消费
URL。使用本地文件前必须配置 `DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS`（多个根按
操作系统 path separator 分隔）；real path 或 symlink 最终落在根目录外会被拒绝。
媒体 binary 不进入 MCP JSON，Plugin 也不直接访问 Object Storage。

Asset 的 Stable Envelope 包含 `asset_id`、所属 Work/可选细粒度 scope、`asset_type`、名称、说明与 `reference_media_ids`，不同 Asset 类型的正式事实保存在 `content`。已知 `asset_id` 时使用 `get_asset`；未知 ID 时使用 `search_assets`。是否值得登记、是否复用以及 `FOUND/NOT_FOUND` 都由 Agent 按 `asset-resolution` 推理，服务只存最终事实。

Media 的 Tool 可见 Stable Envelope 包含 `media_id`、scope、`media_type`、purpose 与不透明 `source_ref`，正式语义保存在 `content`。Skill 不解释 `source_ref` 的格式，也看不到 bucket、object key、路径等存储内部字段。真实媒体字节由 Local/MinIO/S3-compatible Object Storage 保存，不进入 MySQL。

## 长期记忆实现边界

```text
Skill
  -> 决定何时调用 Tool，并定义 Domain Content
Tool Contract
  -> 定义 Stable Envelope + content 的稳定提交结构
Java Tool Interface
  -> 一个 Tool 对应一个接口方法，按 Domain 聚合
Repository
  -> 保存普通结构字段 + JSON content
MySQL
  -> 保存七类长期记忆
Object Storage
  -> 保存媒体字节
```

Tool catalog 是精确机器 Schema 的唯一真源。未来 Java DTO 映射见 [`docs/java-tool-api-mapping.md`](docs/java-tool-api-mapping.md)，MySQL 8.0+ 冻结 DDL 见 [`docs/schema/drama-memory-mysql.sql`](docs/schema/drama-memory-mysql.sql)。数据库 Entity、Repository Model 或物理列名不得反向决定 Skill Schema。

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

### 连接 Drama Service

`memory`（Work/Script/Episode/Scene/Shot）、`asset` 和 `media` 是三个独立 Provider。真实 Java 联调时三者均切换为 `http`，使用同一个服务地址和同一个服务端 Secret；Research/Production 保持 `mock`，Context 保持 `local`。34 项相对 URL 由 Host 配置提供，示例见 [`config/drama-service-http.example.yaml`](config/drama-service-http.example.yaml)。

```bash
export DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN='<same-as-DRAMA_TOOL_SECRET>'
export DRAMA_PLUGIN_SERVICE_ASSET_API_TOKEN="$DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN"
export DRAMA_PLUGIN_SERVICE_MEDIA_API_TOKEN="$DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN"
```

HTTP Provider 发送且只发送 `Authorization: Bearer <API_TOKEN>`。HTTP mode 缺少 base URL 或 token 会直接产生配置错误，不会回退到 Mock。真实跨进程 E2E 的启动步骤和显式运行命令见 Drama Service 的 Batch 02 报告与本仓库 `integration/run_drama_service_e2e.py`。

## 边界

- Java Drama Service 是长期创作事实库，不是 Workflow Engine、Generation Engine 或任务调度器。
- MCP 是协议与能力边界，不拥有 Agent 决策。
- Generation Adapter 隔离 ComfyUI/Provider 物理细节。
- Python runtime 仅用于 Contract、Mock 与开发期验证，不是 Host 的生产调用路径。

更详细的依赖方向见 [`docs/architecture.md`](docs/architecture.md)。
