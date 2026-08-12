# Drama Plugin Agent 驱动业务模型重构执行报告

执行日期：2026-08-12（Asia/Shanghai）  
执行范围：`historical_plugin/drama-plugin`；未修改独立 MCP Server、Java Drama Service 或 ComfyUI 服务。

## 1. 执行摘要

本批次完成正式业务模型重构。Plugin Core 已从 Project/Story、Asset Hierarchy、Generation Plan/Compile 驱动的旧模型，收敛为由 Agent 自主选择 Skill 与 Tool 的创作能力包。

- Skill 数量保持 8 个，没有制造碎片 Skill。
- 长期事实模型收敛为 `Work / Script / Episode / Scene / Shot / Asset / Media`。
- Tool Registry 由 33 个旧动作调整为 39 个新动作：29 个长期记忆 CRUD/搜索、3 个生产动作、5 个 Run Research 动作、2 个 Context 动作。
- 删除 `GenerationPlan`、`GenerationTarget`、`GenerationState`、`AssetBinding`、`AssetHierarchy`、`AssetLevel` 等核心类型与相关 Tool。
- `DramaModelContext` 改为最小 `DramaRunContext`，明确 Persistent Memory 与 Run Context 分离。
- Mock、HTTP、Context、配置、示例与测试同步完成。
- 验证：24 tests passed；mypy 33 个源码文件 0 issues；8 个 Skill quick validation PASS；Plugin validation PASS；Demo PASS。

## 2. 重构前业务模型

```text
Project -> Story -> Episode -> Scene -> Shot
```

旧核心同时包含 Character/Location/Prop 聚合、BASE/SCENE/SHOT AssetLevel、Scene/Shot AssetBinding、AssetHierarchy/EffectiveAsset，以及 GenerationTarget、GenerationPlan、Compile、Submit、Status、Result。Media 还携带 URL、Generation Target 与 Provider 语义，Context 聚合全局 entities/assets/evidence/generation。这些结构会诱导 Agent 进入固定 Plan/Compile/Submit 路径，并把资产选择决策下沉到服务。

## 3. 重构后业务模型

```text
Historical Evidence
  -> Agent Research Context
  -> Work
     -> Script
        -> Episode
           -> Scene
              -> Shot

Asset Resolution = Agent 对稳定视觉记忆的发现与判断
Media Production = Provider-neutral Tool 返回稳定 mediaId
```

层级仅由 `Script.workId`、`Episode.scriptId`、`Scene.episodeId`、`Shot.sceneId` 表达。它是事实关系，不是状态机或执行顺序。Agent 可读取和修改任意上游对象、跳过阶段，并在每次 Tool Result 后重新选择下一动作。

## 4. Skill 调整清单

| 重构前 | 重构后 | 核心职责 |
|---|---|---|
| historical-research | historical-research | Evidence 形成 Agent Research Context；不建立历史 CRUD Domain。 |
| story-skeleton | work-creation | Research Context 创作文学 Work。 |
| continuity-review | script-adaptation | Work 的影视化改编；连续性规则吸收到各 Skill 完成条件。 |
| episode-writing | episode-development | 单集目标、Hook、冲突、信息增量、变化与连续性。 |
| scene-breakdown | scene-development | Scene 进入/退出状态、目标、冲突、对白与动作。 |
| storyboard | shot-design | 景别、机位、构图、站位、运动、时长与 Shot 状态。 |
| visual-asset-planning | asset-resolution | Agent 搜索、判断复用、生成标准图并登记稳定 Asset。 |
| shot-generation | shot-production | 使用 Shot/Scene/Asset/Media 生成图片、视频或音频。 |

每个 Skill Core 只包含方法论、最小 Context、Tool 策略与完成标准。任何 Skill 都不调用另一个 Skill；Agent 在 Tool Result 后决定下一 Skill。

## 5. Tool Contract 调整清单

Persistent Memory：

```text
work.create_work / get_work / save_work / list_works
script.create_script / get_script / save_script / list_scripts
episode.create_episode / get_episode / save_episode / list_episodes
scene.create_scene / get_scene / save_scene / list_scenes
shot.create_shot / get_shot / save_shot / list_shots
asset.create_asset / get_asset / save_asset / list_assets / search_assets
media.create_media / get_media / save_media / list_media
```

Run Research capability：

```text
research.search_sources / search_events / search_people / search_locations / verify_claim
```

Production capability：

```text
production.generate_image / generate_video / generate_audio
```

输入只包含 prompt、referenceAssetIds、referenceMediaIds、start/end frame mediaId 与必要 parameters；输出为 `Media`。

Context capability 保留 `context.build_context` 与 `context.refresh_context`，Host 管理 Run Context，Tool 不负责流程决策。

## 6. 删除/退出核心模型的旧概念

已从源码与 Tool code 删除：Project、Story、Character/Location/Prop 聚合、AssetLevel、AssetBinding、AssetHierarchy、EffectiveAsset、scene/shot hierarchy Tool、GenerationTarget、GenerationPlan、GenerationState、GenerationResult、create/compile/submit/status/result generation Tool、workflowCode、compiledPayload、Media URL、全局 generation Context，以及独立 continuity-review 流程 Skill。

核心源码、Skill、测试、示例和当前架构文档中不存在 Dify 依赖。文档中仅以否定边界说明“不实现固定 Workflow”，不构成模型依赖。

## 7. Asset 新语义

Asset 是跨 Scene、Shot 或 Agent Run 值得复用的稳定视觉记忆：

```text
id / assetType / name / description / referenceMediaIds
```

不存在 BASE/SCENE/SHOT 层级、Binding、EffectiveAsset 或变体继承。发现对象、判断是否值得成为 Asset、`FOUND/NOT_FOUND`、复用适配性和是否新建均属于 Agent + `asset-resolution` Skill。服务只保存 Agent 最终登记的事实。

## 8. Media 新语义

Media 是真实图片、视频或音频的稳定长期引用句柄：

```text
id / mediaType / mimeType / storageKey / metadata
```

`storageKey` 是服务/Adapter 使用的稳定非公开引用，不是 Agent 依赖的 URL。Agent 原则上只携带 mediaId 和必要语义。Media 不再表达 Generation Task、Provider Task、Plan 或 Compile Result。

## 9. Agent / Skill / Tool / MCP / Java / Adapter 职责边界

| 组件 | 职责 |
|---|---|
| Agent | 决策者；读取 Context、选择 Skill、调用 Tool、判断 Result、选择下一步。 |
| Skill | 平台无关方法论、业务规则、最小 Context 与完成判断。 |
| Tool | 执行动作；不判断资产是否复用、不控制创作流程。 |
| MCP | 能力协议与长期事实访问边界；不拥有业务决策。 |
| Java Drama Service | Persistent Memory / System of Record；保存七类长期事实。 |
| Generation Adapter | 解析 Asset/Media 引用并隔离 ComfyUI 或其他 Provider 物理细节。 |

Skill Core 不依赖 Java Controller path、MCP Server 类、FastAPI route、ComfyUI workflow JSON、node id、filename、bucket 或 Provider response。

## 10. Context 与 Persistent Memory 边界

Persistent Memory 是 Work、Script、Episode、Scene、Shot、Asset、Media。Run Context 是当前对象 ID、selectedAssetIds、generatedMediaIds、Research Context 与 temporaryState。

`DramaRunContext` 只加载当前 Scope 所需的最小持久对象链。例如 SHOT Context 包含 Work 到 Shot 的父链，但不会自动加载所有 Asset、Media 或 Research Evidence。Asset 与 Media Context 只读取对应对象。Host 拥有 Context 插入、合并和生命周期。

## 11. Host Adapter 调整

- 8 个 `agents/openai.yaml` 全部与新 Skill 名称和描述同步。
- default prompt 均显式使用 `$skill-name`。
- 业务方法论未写入 Host Adapter。
- OpenAI/Codex MCP dependency 只保留在 `shot-production/agents/openai.yaml`。
- `../../.codex-plugin/plugin.json` 描述改为 Agent-driven，并声明 Read/Write 能力。
- `.mcp.json` 仍指向既有 `drama-context` PoC；本批次未越界修改独立 MCP Server。
- 已使用 cachebuster `0.1.0+codex.20260812034616` 重装 `drama-plugin@drama-local`，安装缓存只包含新的 8 个 Skill 目录。

## 12. 测试与验证结果

```text
pytest: 24 collected, 24 passed, 0 failed
mypy: Success, 33 source files, 0 issues
Skill quick_validate: 8/8 PASS
Plugin validate_plugin: PASS
Demo: PASS
```

静态/合同验证：Skill 恰好 8 个；断链 0；Tool 重复 0；Tool 总数 39；旧 Plan/Compile/Binding/GenerationTarget Tool code 0；Dify 核心引用 0；Skill Core 中 Codex/OpenAI/localhost/具体 MCP Server 泄漏 0；Skill 间 `$other-skill` 调用 0；Asset/Media 最小 schema PASS；Mock 与 HTTP Tool schema 一致；最小 Context PASS。

## 13. 未解决问题

1. 独立 `drama-mcp-poc` 仍是上一批只暴露旧版固定 `context.build_context` 的 Stub；尚未实现本批次 39 个 Tool Contract。本批次按边界要求未修改它。
2. 当前 `content` 与 `metadata` 使用小型开放字典，足以验证边界但不是最终 Java 持久 schema；仅在真实校验需求出现时再收紧。
3. `storageKey` 的生成、访问授权和生命周期属于未来 Media Service/Adapter，Plugin Core 刻意不规定。

## 14. 后续 Java/MCP 接口需求

1. Java/MCP 实现 29 个 Persistent Memory 动作，并保留直接父 ID 与 Asset/Media 最小语义。
2. 独立 Research MCP 或检索能力实现 5 个 research 动作；结果默认返回 Agent Run Context，不进入 Drama CRUD。
3. ComfyUI/其他 Provider Adapter 实现 3 个 production 动作，内部完成 storage/media 解析与 `create_media`，只向 Agent 返回 Media。

以上是接口需求记录，不代表需要一次性建设完整服务。

## 15. 最终插件目录结构

```text
drama-plugin/
├── .codex-plugin/plugin.json
├── .mcp.json
├── README.md
├── plugin.yaml
├── config/drama-plugin.example.yaml
├── docs/
│   ├── architecture.md
│   └── reports/Drama Plugin Agent驱动业务模型重构执行报告.md
├── examples/build_shot_context.py
├── skills/
│   ├── historical-research/{SKILL.md,skill.yaml,agents/openai.yaml}
│   ├── work-creation/{SKILL.md,skill.yaml,agents/openai.yaml}
│   ├── script-adaptation/{SKILL.md,skill.yaml,agents/openai.yaml}
│   ├── episode-development/{SKILL.md,skill.yaml,agents/openai.yaml}
│   ├── scene-development/{SKILL.md,skill.yaml,agents/openai.yaml}
│   ├── shot-design/{SKILL.md,skill.yaml,agents/openai.yaml}
│   ├── asset-resolution/{SKILL.md,skill.yaml,agents/openai.yaml}
│   └── shot-production/{SKILL.md,skill.yaml,agents/openai.yaml}
├── src/drama_plugin/
│   ├── contracts/{creation.py,asset.py,media.py,research.py,context.py,...}
│   ├── providers/{base,http,mock}/
│   ├── context/
│   ├── skills/
│   └── tools/
└── tests/
```

## 16. 本批次实际修改文件清单

新增：7 个重命名后 Skill 目录共 21 个文件；`contracts/creation.py`；`contracts/research.py`；本报告。historical-research 原目录就地修改。

删除：7 个旧 Skill 目录共 21 个文件；`contracts/project.py`；`contracts/generation.py`；`contracts/history.py`。

修改：`../../.codex-plugin/plugin.json`、README、architecture、plugin manifest、config、Demo、Contract exports/Asset/Media/Context、Provider base/Mock/HTTP、Context、Plugin composition root、Tool catalog、7 个测试文件与 config fixture。

没有提交 Git；没有修改独立 MCP Server、Java 或 ComfyUI 工程。

## 最终明确回答

- **当前插件是否已经从 Workflow 驱动转向 Agent 驱动？** 是。Agent 在每次 Result 后自主决定下一 Tool/Skill，Skill 不互相调用，层级不构成状态机。
- **是否仍存在 Plan / Compile / GenerationTarget / Binding 核心依赖？** 否。相关核心类型、Tool、Provider 和 Skill 引用均已删除。
- **是否仍存在 Dify 核心依赖？** 否。
- **Skill 是否已经可以独立于 Codex Host 存在？** 是。业务规则全部位于平台无关 `SKILL.md`/`skill.yaml`；OpenAI dependency 仅在 adapter 文件。
- **当前 Tool Contract 是否足够支撑未来 Java/MCP 长期记忆服务？** 是，已覆盖七类长期事实的最小 create/get/save/list，并为 Asset 提供 search；具体 Java schema 可在真实需求出现时收紧。
- **当前 Tool Contract 是否足够支撑 ComfyUI/其他 Provider Adapter？** 是，三类生产 Tool 只暴露业务 prompt 与稳定 Asset/Media ID，足以在 Adapter 内替换物理 Provider。
- **是否存在本次任务范围外、下一批必须处理的问题？** 是。独立 MCP/Java 实现尚未迁移到新 39 Tool Contract；下一批在修改外部服务时必须处理，但不应把其实现细节回灌到 Skill Core。
