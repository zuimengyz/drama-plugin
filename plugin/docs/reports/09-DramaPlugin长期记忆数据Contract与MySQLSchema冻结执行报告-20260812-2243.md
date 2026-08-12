# Drama Plugin 长期记忆数据 Contract 与 MySQL Schema 冻结执行报告

执行时间：2026-08-12 22:43（Asia/Shanghai）  
工程根目录：`D:\home\AI\historical_plugin\drama-plugin\plugin`  
结论：**PASS**

## 1. 执行摘要

本批次已冻结 Work、Script、Episode、Scene、Shot、Asset、Media 七类长期记忆的 create/save 输入 Contract，并统一为“Stable Envelope + `content` JSON Object”。14 个 create/save Tool 的 catalog、Provider Protocol、Mock Provider、HTTP Provider 与测试已同步。Tool code 未增删改名，Plugin 实际加载仍为 42 个 Tool。

已加固 `work-creation`、`script-adaptation`、`episode-development`、`scene-development`、`shot-design`、`asset-resolution` 六个 Skill；`historical-research` 与 `shot-production` 未修改。已新增 MySQL 8.0+ 七表 DDL 与 Java ToolApi 映射说明。未实现 Java、MCP Server、数据库访问、对象存储 Adapter、Workflow、Binding、Plan 或 Compile。

修改前基线为 32 项测试中 31 passed / 1 failed；唯一失败是 Windows 默认 GBK 解码 UTF-8 README。测试现已显式使用 UTF-8。最终为 38 passed / 0 failed，mypy 0 errors。

## 2. 修改前 Contract 审计

以下内容来自修改前实际 `src/drama_plugin/tools/catalog.py` 与运行时 ToolRegistry，不来自 README 推测。

| Domain | 修改前 create input | 修改前 save input | 主要差异 |
| --- | --- | --- | --- |
| Work | required: `title`; optional: `description`, `content` | required: `work: Work` | `content` 非必需；save 接收整 DTO |
| Script | required: `work_id`, `title`; optional: `content` | required: `script: Script` | `content` 非必需；save 包含父级 DTO |
| Episode | required: `script_id`, `number`, `title`; optional: `content` | required: `episode: Episode` | `number` 未采用 `episode_no`；save 可携带父级 |
| Scene | required: `episode_id`, `number`, `heading`; optional: `content` | required: `scene: Scene` | 顶层字段与目标 `order/title/location` 不一致 |
| Shot | required: `scene_id`, `number`, `description`; optional: `duration_seconds`, `content` | required: `shot: Shot` | 镜号是整数；创作字段摊在 Envelope；save 可携带父级 |
| Asset | required: `asset_type`, `name`; optional: `description`, `reference_media_ids` | required: `asset: Asset` | 无 scope、无 `content`；save 可修改 type |
| Media | required: `media_type`, `mime_type`, `storage_key`; optional: `metadata` | required: `media: Media` | 暴露存储字段；无 scope、`source_ref`、`content` |

差异归类如下：

- 保留：稳定名称/标题、结构父级、排序/编号、Asset 类型与引用媒体、Media 类型。
- 新增：所有 create/save 的必需 `content: object`；Asset scope；Media scope、purpose 与不透明 `source_ref`。
- 删除：save 的整实体参数；Shot 的顶层 description/duration；Media 的 Tool 可见 mime/storage/metadata。
- 迁入 `content`：Episode/Scene/Shot/Asset/Media 的可演进正式领域事实。
- 保持顶层：父级、稳定 ID、标题/名称、顺序/编号、高频过滤字段、Asset scope/type、Media scope/type/purpose/source reference。

## 3. 最终 Contract 总表

所有输入字段统一使用 `snake_case`；同一 request 不接受 camelCase 同义字段，且 `additionalProperties=false`。

| Domain | Create Envelope | Save Envelope | Content |
| --- | --- | --- | --- |
| Work | required `title`; optional `description` | required `work_id`, `title`; optional `description` | required JSON Object |
| Script | required `work_id`, `title` | required `script_id`, `title` | required JSON Object |
| Episode | required `script_id`, `episode_no`, `title` | required `episode_id`, `episode_no`, `title` | required JSON Object |
| Scene | required `episode_id`, `order`, `title`; optional `location` | required `scene_id`, `order`, `title`; optional `location` | required JSON Object |
| Shot | required `scene_id`, `shot_no`; optional `title`, `shot_type` | required `shot_id`, `shot_no`; optional `title`, `shot_type` | required JSON Object |
| Asset | required `work_id`, `asset_type`, `name`; optional scope IDs、`description`、`reference_media_ids` | required `asset_id`, `name`; optional `description`, `reference_media_ids` | required JSON Object |
| Media | required `work_id`, `media_type`, `source_ref`; optional `asset_id`, `shot_id`, `purpose` | required `media_id`; optional `purpose` | required JSON Object |

`reference_media_ids` 的 Schema default 为 `[]`。`save_xxx` 是完整正式状态替换，不是 JSON Patch、Merge Patch、field mask 或 operation list。

## 4. Work Contract

- `work.create_work`: required `title`, `content`; optional `description`。
- `work.save_work`: required `work_id`, `title`, `content`; optional `description`。
- ID、version、created/updated time 不由 Agent 创建。
- save 只针对稳定 `work_id` 的明确修订。

## 5. Script Contract

- `script.create_script`: required `work_id`, `title`, `content`。
- `script.save_script`: required `script_id`, `title`, `content`。
- `work_id` 只在 create 建立稳定父级；普通 save 无法迁移 Script。

## 6. Episode Contract

- `episode.create_episode`: required `script_id`, `episode_no`, `title`, `content`。
- `episode.save_episode`: required `episode_id`, `episode_no`, `title`, `content`。
- 原 `number` 已替换为结构化过滤一致的 `episode_no`；save 不接收 `script_id`。

## 7. Scene Contract

- `scene.create_scene`: required `episode_id`, `order`, `title`, `content`; optional `location`。
- `scene.save_scene`: required `scene_id`, `order`, `title`, `content`; optional `location`。
- 人物、时间、动作、对白、目标、转折等进入 `content`；save 不接收 `episode_id`。
- Tool 的 `order` 在数据库映射为 `scene_order`，避免 SQL 列名歧义。

## 8. Shot Contract

- `shot.create_shot`: required `scene_id`, `shot_no`, `content`; optional `title`, `shot_type`。
- `shot.save_shot`: required `shot_id`, `shot_no`, `content`; optional `title`, `shot_type`。
- `shot_no` 已统一为 string，并同步 `list_shots` 的同名过滤参数类型。
- 构图、机位、动作、表演、时长等进入 `content`；save 不接收 `scene_id`。

## 9. Asset Contract

- `asset.create_asset`: required `work_id`, `asset_type`, `name`, `content`; optional `episode_id`, `scene_id`, `shot_id`, `description`, `reference_media_ids`。
- `asset.save_asset`: required `asset_id`, `name`, `content`; optional `description`, `reference_media_ids`。
- save 不接收 scope IDs 或 `asset_type`，Mock save 也会保留原 scope/type。
- Asset Domain Contract 已同步 scope 与 `content`；AssetType 保留既有值并补充长期视觉资产类型。
- 未增加 scopeType、binding 或独立资产绑定系统。

## 10. Media Contract

- `media.create_media`: required `work_id`, `media_type`, `source_ref`, `content`; optional `asset_id`, `shot_id`, `purpose`。
- `media.save_media`: required `media_id`, `content`; optional `purpose`。
- `source_ref` 在 Skill 中明确为 Host/Adapter 可解析的不透明稳定引用。
- save 不接收 scope、media type 或 source reference；新物理媒体应创建新 Media。
- Tool 可见 Domain Contract 不再暴露 `storage_key`、bucket、object key、路径或 Provider raw response。

## 11. Skill 修改结果

| Skill | 结果 |
| --- | --- |
| `work-creation` | 明确 Work Envelope 与正式创作内容；save 为 full replacement |
| `script-adaptation` | 明确 create 父级与 save 稳定 ID；禁止 save 移动 Work |
| `episode-development` | 明确 episode number/title 顶层；Episode 内容进入 `content` |
| `scene-development` | 明确 episode/order/title/location 顶层；人物与场景正文进入 `content` |
| `shot-design` | 明确字符串 shot number/title/type 顶层；镜头创作事实进入 `content` |
| `asset-resolution` | 明确 Asset scope/type/ref media 与 Media opaque `source_ref` 边界 |
| `historical-research` | 未修改；不承担长期实体 create/save |
| `shot-production` | 未修改；生成结果已有稳定 Media 时不得重复登记的既有边界保持 |

六个修改 Skill 均声明：Tool catalog 是机器 Schema 唯一真源；Skill 不复制完整 JSON Schema；`content` 不得是 stringified JSON、scratchpad 或 raw response。

## 12. Tool Contract 修改清单

- Tool 总数：修改前 42，修改后 42。
- Tool code：0 新增、0 删除、0 重命名。
- Input Schema：仅冻结 14 个 create/save，并将 `list_shots.shot_no` 同步为 string。
- get/list/search 业务职责：未改变。
- Output Schema：为保持返回实体与长期对象一致，进行了必要同步：Episode `number -> episodeNo`；Scene `number/heading -> order/title/location`；Shot `number/description/durationSeconds -> shotNo/title/shotType/content`；Asset 增加 scope/content；Media 改为 scope/purpose/sourceRef/content。Work/Script 结构保持。
- Provider Protocol：所有 14 个方法改为展开的稳定参数，不再接收整实体 save DTO。
- Mock：create 接收完整首次状态；save 重建完整 mutable state 并保留稳定父级/scope/type/source reference。
- HTTP：14 个 request body 与 Tool 输入一致使用 snake_case；endpoint path 仍完全来自配置。
- `object_schema`：增加只适用于 optional 字段的 default 支持，用于 `reference_media_ids=[]`。

## 13. MySQL 表清单

新增 `docs/schema/drama-memory-mysql.sql`，目标 MySQL 8.0+ / InnoDB / utf8mb4，共且仅有七张表：

| Table | Stable columns | JSON |
| --- | --- | --- |
| `drama_work` | id/title/description | content |
| `drama_script` | id/work_id/title | content |
| `drama_episode` | id/script_id/episode_no/title | content |
| `drama_scene` | id/episode_id/scene_order/title/location | content |
| `drama_shot` | id/scene_id/shot_no/title/shot_type | content |
| `drama_asset` | id/scope IDs/asset_type/name/description | reference_media_ids/content |
| `drama_media` | id/scope/media_type/purpose/source_ref + storage internal metadata | content |

七表均有 `id VARCHAR(64)`、`content JSON NOT NULL`、version、created_at、updated_at。无 BLOB、无物理 Foreign Key、无 Generic Entity、Binding、Workflow 或 Generation 表。

逻辑关系：`drama_script.work_id -> drama_work.id`；`drama_episode.script_id -> drama_script.id`；`drama_scene.episode_id -> drama_episode.id`；`drama_shot.scene_id -> drama_scene.id`；`drama_asset` scope IDs 指向相应长期对象；`drama_media.asset_id -> drama_asset.id`；`drama_media.shot_id -> drama_shot.id`。

本机存在 MySQL Client 8.0.11，但未连接任何现有数据库，也未安装工具。DDL 通过自动化静态测试验证七表、公共字段、ID 类型、Asset scope/reference、无 BLOB/Foreign Key/额外表。

## 14. Tool → Java Interface Method Mapping

新增 `docs/java-tool-api-mapping.md`。映射原则为一个 Tool 对应一个 Java interface method，并按 Domain 聚合为 `WorkToolApi`、`ScriptToolApi`、`EpisodeToolApi`、`SceneToolApi`、`ShotToolApi`、`AssetToolApi`、`MediaToolApi`。例如：

```text
work.create_work -> WorkToolApi.createWork()
work.save_work   -> WorkToolApi.saveWork()
scene.create_scene -> SceneToolApi.createScene()
asset.save_asset -> AssetToolApi.saveAsset()
media.create_media -> MediaToolApi.createMedia()
```

未创建 Java 源码。未来 Request DTO 以 Tool catalog 的 snake_case input Schema 为依据；Repository 将 Envelope 映射为普通列，将 `content` 映射为 JSON。

## 15. 测试结果

| 验证 | 结果 |
| --- | --- |
| 修改前 pytest | 31 passed / 1 failed（README 默认编码） |
| 最终 pytest | 38 passed / 0 failed / 0 skipped / 0 warnings，2.30s |
| mypy | Success，33 source files，0 errors |
| Skill quick_validate | 8/8 passed |
| plugin validate | passed |
| Plugin load | 8 Skills / 42 Tools |
| Demo | passed；加载 drama-plugin、shot-production、SHOT Context、Shot/Scene/Work/Assets |
| HTTP binding | 14 个 create/save snake_case body 测试通过，无网络 |
| SQL static validation | passed |
| `git diff --check` | passed；仅 Git 的 LF→CRLF 工作区提示，无 whitespace error |

Demo 关键输出：

```text
Loaded Plugin: drama-plugin 0.1.0
Loaded Skill: shot-production
Context Scope: SHOT
Shot: 狄仁杰抬眼特写
Scene: 狄府书房雨夜密谈
Work: 神都密诏
Selected Assets: asset-di, asset-study
```

## 16. 边界确认与最终逐项回答

边界确认：未实现 Java；未修改 MCP Server；未增删或重命名 Tool；未新增 Workflow、Binding、Plan、Compile、search 技术、数据库运行依赖或媒体二进制存储；未修改 `skill.yaml`、`agents/openai.yaml`、`.codex-plugin/plugin.json`、`plugin.yaml`。

1. 是否所有新长期事实仍通过一次 `create_xxx` 完成首次正式持久化？**是。**
2. 是否仍禁止 `create → routine save`？**是。** 六个相关 Skill 和测试继续约束。
3. 是否所有 create 都采用“Stable Envelope + content”？**是。** 七个 create 均已冻结。
4. `content` 是否统一为真实 JSON Object，而非 stringified JSON？**是。** 14 个 Schema 均为 `type=object`。
5. Stable Envelope 是否只保留结构/检索/身份字段？**是。** 可演进创作事实已进入 `content`。
6. Skill 是否知道 Envelope 与 content 的边界？**是。** 六个承担持久化职责的 Skill 已明确。
7. 精确机器 Schema 是否仍由 Tool Contract 作为唯一真源？**是。** Skill 不复制完整 Schema。
8. save 是否采用完整新正式状态，而非 Patch？**是。** 未引入任何 Patch DSL。
9. 普通 save 是否禁止修改稳定父级关系？**是。** Schema 排除且 Mock 行为保留稳定关系。
10. Tool 总数是否仍为 42？**是。** 运行时实测 42。
11. get/list/search 语义是否保持不变？**是。** 仅 `list_shots.shot_no` 类型随冻结编号改为 string。
12. 是否生成 7 张 MySQL 长期记忆主表？**是。** 且没有第八张表。
13. MySQL 是否以普通字段保存 Envelope、JSON 保存 content？**是。**
14. 是否没有新增 Generic Entity 模型？**是。** 七个 Domain 保持明确。
15. 是否没有重新引入 Binding / Plan / Compile / Workflow？**是。**
16. 当前 Contract 是否可直接作为后续 Java `ToolApi` 接口与 DTO 的实现依据？**是。** Request 字段、返回 Domain、表结构与方法映射已相互对齐；Java 仍需自行实现 ID、校验、version 与持久化行为。

最终冻结关系：

```text
Skill owns domain meaning.
Tool Contract owns stable data shape.
Java owns persistence behavior.
MySQL owns long-term memory.
Object Storage owns media bytes.
```
