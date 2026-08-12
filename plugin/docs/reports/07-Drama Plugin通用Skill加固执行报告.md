# 07 - Drama Plugin 通用 Skill 加固执行报告

## 1. 执行摘要

本批次以最小侵入方式完成 8 个现有 Skill 的通用化加固：

- `SKILL.md` 继续承担平台无关业务方法论，并明确每个 Logical Tool Contract 的适用条件；
- `skill.yaml` 继续承担平台无关机器契约，核心 Tool 归入 `preferred`，辅助 Tool 保留在 `allowed`；
- `agents/openai.yaml` 收敛为可选的 OpenAI/Codex 界面 Adapter，不再携带本地 MCP URL；
- 复用现有 `SkillRegistry`、`ToolRegistry` 与 `SkillToolReferenceValidator`，没有新增运行时、DSL、框架或第三方依赖。

8 个 Skill 均已完成加固。Skill Core 不依赖 Codex、MCP、Java、FastAPI、ComfyUI、具体 Provider 或未来 Harness。当前未解决项仅涉及本批范围外的 Host MCP 配置路径与开发环境 editable install 路径，不影响通用 Skill Contract 本身。

## 2. 修改前问题

### GEN-001：SKILL.md 缺少完整 Logical Tool 名称

- 文件：8 个 `skills/*/SKILL.md`。
- 问题：多数文件已有 get/list/search/create/save 的判断思路，但常用 “read”“list”“search” 等自然语言代替稳定 Tool code；部分辅助 Tool 完全只存在于 `skill.yaml`。
- 风险：只读取 `SKILL.md` 的原生 Host 无法可靠知道应请求哪项逻辑能力。
- 处理：已修改。逐个写明 Tool code 及适用条件，但未写成固定调用顺序。

### GEN-002：preferred / allowed 的核心性表达偏弱

- 文件：除 historical-research 外的 7 个 `skill.yaml`。
- 问题：部分核心 list/search Tool 位于 `allowed`，与该 Skill 的主要发现、读取、创建和保存职责不完全一致。
- 风险：未来通用 SkillLoader 难以区分核心能力与辅助能力。
- 处理：已修改。核心 Domain Tool 归入 `preferred`；历史核验、Context、参考 Media 等辅助能力保留在 `allowed`。两组无重复。

### GEN-003：OpenAI Adapter 含本地 PoC MCP 接线

- 文件：`skills/shot-production/agents/openai.yaml`。
- 问题：包含 `127.0.0.1:8765`、streamable HTTP transport 与 MCP dependency。
- 风险：把单机 PoC 地址固化进 Skill 级 Host Adapter，且会让 Adapter 看起来像通用 Core 的必要组成。
- 处理：已删除 dependency block，只保留 `interface`。未修改 MCP Server、根级 Host 配置或 Marketplace。

### GEN-004：缺少通用三层边界的自动防回归

- 文件：`tests/test_skills.py`。
- 问题：已有 Codex/MCP 基础禁词与 Skill 加载测试，但未覆盖全部要求词、SKILL.md 明示 Logical Tool、preferred/allowed 重复、OpenAI Adapter 顶层职责。
- 风险：后续修改可能重新把 Host 配置或隐式 Tool 引用带回 Core。
- 处理：已用三个极小静态测试补齐；没有实现 Markdown 语义解析器。

### GEN-005：现有校验器是否需要扩展

- 文件：`src/drama_plugin/skills/validation.py`。
- 审计结果：现有 `SkillToolReferenceValidator` 已校验每个 preferred/allowed Tool 存在，并校验 code domain 与注册 Tool domain 一致。
- 处理：无需修改，避免重复抽象。

## 3. 8 个 Skill 加固结果

### historical-research

- SKILL.md：明确 `research.search_sources/events/people/locations` 的分类使用条件，以及何时使用 `research.verify_claim`；强调优先使用已有证据。
- skill.yaml：无需修改，原 preferred/allowed 边界准确。
- openai.yaml：无需修改，原文件仅含界面 metadata。
- Tool Contract：只依赖 research Tool，不承担 Work/Script 等持久实体 CRUD。

### work-creation

- SKILL.md：明确已知 ID 用 `work.get_work`，自然语言身份用 `work.search_works`，结构枚举用 `work.list_works`，新建与更新分别使用 create/save。
- skill.yaml：将 `work.search_works` 调整为 preferred。
- openai.yaml：无需修改。
- Tool Contract：Work 发现、读取、创建、保存；历史核验与 Context 仅为条件性辅助。

### script-adaptation

- SKILL.md：明确 Work 精确读取、Script 精确读取/父级列举、新建与更新的 Tool 选择。
- skill.yaml：将 `script.list_scripts` 调整为 preferred。
- openai.yaml：无需修改。
- Tool Contract：不搜索不存在的 `search_scripts`，不创建 Episode。

### episode-development

- SKILL.md：明确通过 `script.get_script` 获取父级；已知 Episode ID 用 get，已知 Script 范围用 list；create/save 语义分离。
- skill.yaml：将 `episode.list_episodes` 调整为 preferred。
- openai.yaml：无需修改。
- Tool Contract：不增加 `search_episodes`，不自动拆 Scene。

### scene-development

- SKILL.md：明确 Scene 的 get/list/search/create/save 条件，并限制历史地点搜索与 claim 核验的使用时机。
- skill.yaml：将 `scene.list_scenes`、`scene.search_scenes` 调整为 preferred。
- openai.yaml：无需修改。
- Tool Contract：只开发当前 Scene，不生成 Shot 或解析 Asset。

### shot-design

- SKILL.md：明确 `shot.get_shot`、`shot.list_shots`、`shot.search_shots`、create/save 的判断；Asset/Media 仅用于连续性参考。
- skill.yaml：将 Shot list/search 调整为 preferred。
- openai.yaml：无需修改。
- Tool Contract：不调用生产 Tool，不自动生成媒体。

### asset-resolution

- SKILL.md：明确已知 Asset ID 用 get，结构范围用 list，自然语言身份用 search；只有无合适候选时才生成参考图并 create；已有 Asset 更新用 save。
- skill.yaml：Asset 五类核心动作统一为 preferred；生产、Media、Context 保持辅助；`media.create_media` 加入 `refresh_after`。
- openai.yaml：无需修改。
- Tool Contract：FOUND/NOT_FOUND 与复用判断仍属于 Agent；没有 Binding、Plan 或 Compile。

### shot-production

- SKILL.md：明确 Shot/Scene/Asset/Media 的条件读取，以及按请求选择 image/video/audio；不存在强制媒体生成序列。
- skill.yaml：三种 generation Tool 与必要稳定引用读取列为 preferred；移除 Core 中的 Provider 字样。
- openai.yaml：删除本地 MCP dependency，只保留 interface metadata。
- Tool Contract：只生产已批准 Shot 所需 Media，不重新承担 Shot Design。

## 4. Tool Contract 对照表

| Skill | Preferred Tools | Allowed Tools | 关键调用判断 |
|---|---|---|---|
| historical-research | research.search_sources, research.verify_claim | research.search_events/people/locations | 有证据先使用；按缺口类别搜索；重要主张才核验 |
| work-creation | work.get/search/create/save | work.list, research.verify_claim, context.build/refresh | ID→get；自然语言→search；新实体→create；已有更新→save |
| script-adaptation | work.get, script.get/list/create/save | research.verify_claim, context.build/refresh | scriptId→get；workId 范围→list；不增加模糊 search |
| episode-development | script.get, episode.get/list/create/save | research.verify_claim, context.build/refresh | episodeId→get；scriptId 范围→list；不自动创建 Scene |
| scene-development | episode.get, scene.get/list/search/create/save | research.search_locations, research.verify_claim, context.build/refresh | ID→get；父级→list；自然语言→search；候选确认后再 create |
| shot-design | scene.get, shot.get/list/search/create/save | asset.get, media.get, context.build/refresh | ID→get；sceneId→list；描述→search；不生成媒体 |
| asset-resolution | asset.get/list/search/create/save | production.generate_image, media.create/get, context.build/refresh | 已知 ID→get；类型范围→list；描述→search；无候选才 create |
| shot-production | shot.get, scene.get, asset.get, media.get, production.generate_image/video/audio | media.list, context.build/refresh | 仅按请求选择生成类型；无固定 image→video 序列 |

`context.build_context` 只在所需上下文未提供时使用；`context.refresh_context` 只在状态变化导致当前上下文过期时使用。它们不是每个 Skill 的强制首尾步骤。

## 5. 通用化边界验证

- `SKILL.md` 是否平台无关：**是**。仅含业务方法论、Logical Tool code、判断与停止条件。
- `skill.yaml` 是否平台无关：**是**。仅含业务 Context、Tool Contract 和 Completion Conditions。
- `agents/openai.yaml` 是否仅作为 Host Adapter：**是**。8 个文件都只含 `interface`。
- Skill Core 是否依赖 MCP：**否**。
- Skill Core 是否依赖 Codex：**否**。
- Skill Core 是否依赖 Java：**否**。
- Skill Core 是否依赖具体 Provider：**否**。
- Skill Core 是否依赖 FastAPI、ComfyUI 或 Agents SDK：**否**。

Core 禁词扫描覆盖 Codex、MCP Server、localhost、127.0.0.1、FastAPI、Spring Boot、Java Service、ComfyUI、OpenAI Agents SDK、MCPServerStreamableHttp，结果为 0。Skill 之间不存在 `$other-skill` 调用。

## 6. Codex 与未来 Harness 的加载模型

Codex/OpenAI Host 可以通过 Plugin manifest 发现 Skill，读取 `agents/openai.yaml` 的界面 metadata，并在 Skill 触发后读取同一份 `SKILL.md`。Host 将 Logical Tool code 映射到它拥有的 ToolSet；Skill 不感知传输方式。

未来 Drama Harness 可以完全忽略 `agents/openai.yaml`，使用现有 `SkillRegistry` 或等价 SkillLoader 读取 `skill.yaml` 与 `SKILL.md`，获得 required/optional Context、preferred/allowed Tool 和完成条件，再把 Logical Tool code 绑定到 Function Tool、MCP 或其他实现。Harness/Agent Loop 不进入 Skill Core。

## 7. 测试结果

- SkillRegistry：8 个 Skill 全部加载，数量与名称准确。
- Tool validation：42 个 Tool 注册；8 个 Skill 的 preferred/allowed 引用全部存在且 domain 一致。
- SKILL.md / skill.yaml 一致性：每个声明的 Logical Tool code 均在对应 SKILL.md 明示；preferred 与 allowed 无重复。
- OpenAI Adapter：8 个文件顶层均只有 `interface`，字段仅为 display_name、short_description、default_prompt。
- Skill 格式校验：8/8 通过 `quick_validate.py`。
- pytest：30 collected，30 passed，0 failed。
- mypy：33 个 source file，0 issue。
- 示例：以项目真实源码路径运行 `examples/build_shot_context.py`，成功加载 shot-production 并构建 SHOT Context。
- `git diff --check`：PASS。
- 人工检查：逐个核对 8 个 SKILL.md 的判断语义、skill.yaml 引用与职责边界，未发现固定 Workflow 或越权调用。

仓库重组后，现有 `.venv` 的 editable project location 仍指向外层仓库根，而当前 `pyproject.toml/src` 位于 `plugin/`。因此直接运行示例会找不到包；本批未修改环境，使用 `PYTHONPATH=src` 完成等价源码验证。pytest 自身已通过 pyproject 的 `pythonpath=["src"]` 正常执行。

## 8. 未修改范围

本批未修改：

- MCP Server 与 MCP 协议实现；
- Java Drama Service；
- HTTP Provider 实现与业务 API；
- ComfyUI 或其他 Generation Adapter；
- 数据库与搜索实现；
- Agent SDK Harness、Agent Loop 或 Runtime；
- Marketplace、本地插件缓存或 Git 集成；
- ToolRegistry、SkillRegistry、SkillToolReferenceValidator 的实现；
- Plugin manifest 与顶层 README。

## 9. 未解决问题与后续建议

1. 当前仓库外层存在 `.mcp.json`，而内层 `plugin/.codex-plugin/plugin.json` 使用 `./.mcp.json` 相对引用。该 Host 打包路径需要在专门的 Codex Host 集成批次确认；本批按边界未移动或修改 MCP 配置。
2. 开发环境 editable install 路径仍指向重组前外层根。后续仅需重新执行当前项目的 editable install，不需要改 Skill 架构。

除此之外，没有本批必须继续处理的问题。不要据此启动 Harness 或 MCP 开发。

## 10. 实际修改文件

- `skills/historical-research/SKILL.md`
- `skills/work-creation/SKILL.md`
- `skills/work-creation/skill.yaml`
- `skills/script-adaptation/SKILL.md`
- `skills/script-adaptation/skill.yaml`
- `skills/episode-development/SKILL.md`
- `skills/episode-development/skill.yaml`
- `skills/scene-development/SKILL.md`
- `skills/scene-development/skill.yaml`
- `skills/shot-design/SKILL.md`
- `skills/shot-design/skill.yaml`
- `skills/asset-resolution/SKILL.md`
- `skills/asset-resolution/skill.yaml`
- `skills/shot-production/SKILL.md`
- `skills/shot-production/skill.yaml`
- `skills/shot-production/agents/openai.yaml`
- `tests/test_skills.py`
- `docs/reports/07-Drama Plugin通用Skill加固执行报告.md`

最终结论：同一套 `SKILL.md + skill.yaml` 已可作为 Universal Skill Core 供 Codex 与未来 Drama Harness 复用；Host Adapter 和 Tool transport 均位于 Core 之外。
