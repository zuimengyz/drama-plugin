# Drama Plugin 长期记忆 Tool 接口补齐执行报告

## 1. 执行摘要

本批次从当前 Agent 驱动插件真实代码出发，完成长期记忆 Tool Contract 的定向补齐。修改前共有 39 个 Tool，其中长期记忆 Tool 29 个；修改后共有 42 个 Tool，其中长期记忆 Tool 32 个。

本批次新增 `work.search_works`、`scene.search_scenes`、`shot.search_shots`，并将 `work.list_works(query?)` 中混入的搜索语义拆出。`list_episodes`、`list_scenes`、`list_shots` 获得最小结构化过滤参数。未增加 `search_scripts`、`search_episodes` 或 `search_media`，没有新增依赖、Workflow、状态机或搜索技术实现。

结论：长期记忆合同已能支持 Agent 在稳定 ID 丢失时，按自然语言重新发现 Work、Scene、Shot 和 Asset，并沿父级关系恢复 Script、Episode 与 Shot Context。

## 2. 修改前 Tool 清单

| Domain | 修改前 Tool | 状态 |
|---|---|---|
| Work | create_work, get_work, save_work, list_works(query?) | 缺 search；list 混入模糊查询语义 |
| Script | create_script, get_script, save_script, list_scripts(workId) | 完整 |
| Episode | create_episode, get_episode, save_episode, list_episodes(scriptId) | 基础完整；list 缺轻量过滤 |
| Scene | create_scene, get_scene, save_scene, list_scenes(episodeId) | 缺 search；list 缺轻量过滤 |
| Shot | create_shot, get_shot, save_shot, list_shots(sceneId) | 缺 search；list 缺轻量过滤 |
| Asset | create_asset, get_asset, save_asset, list_assets, search_assets | 完整 |
| Media | create_media, get_media, save_media, list_media | 完整 |

扫描 Tool catalog、Provider Protocol、Mock/HTTP binding、8 个 Skill、README、Plugin manifest、配置、示例与测试后，未发现 `fetch/load/find/query/lookup/update_xxx` 等重复同义 Tool。历史报告保留其当时事实，不作为当前可执行合同。

## 3. 缺失 Tool 分析

- Work 是创作树入口；Agent 经常只有作品名或描述，因此必须支持自然语言发现。
- Scene 数量较多，用户常用地点、人物和事件描述定位场景，因此需要可选 Episode 范围的搜索。
- Shot 数量更多，用户常以“某个特写”等自然语言找回镜头，因此需要可选 Scene 范围的搜索。
- 原 `list_works(query?)` 同时表达结构列举和模糊发现，违反 list/search 分层，已拆分。
- Episode、Scene、Shot 的 list 需要轻量过滤，但无需 Query DSL。

## 4. 新增 Tool 清单

| Tool code | 必需参数 | 可选参数 | 返回 |
|---|---|---|---|
| `work.search_works` | `query` | 无 | `list[Work]` |
| `scene.search_scenes` | `query` | `episode_id` | `list[Scene]` |
| `shot.search_shots` | `query` | `scene_id` | `list[Shot]` |

同时调整：

- `work.list_works()`：移除 query，不再承担搜索。
- `episode.list_episodes(script_id, episode_no?, title?)`。
- `scene.list_scenes(episode_id, order?, location?, character?)`。
- `shot.list_shots(scene_id, shot_no?, shot_type?, character?)`。

合同只规定自然语言候选发现，不规定 SQL LIKE、全文索引、Embedding、向量数据库、RAG、阈值或重排策略。

## 5. 保留但未增加 search 的 Domain 及原因

- Script：优先通过稳定 `scriptId` 精确读取，或通过已知 `workId` 调用 `list_scripts`。当前没有独立模糊检索需求。
- Episode：优先通过稳定 `episodeId`，或通过 `scriptId + episodeNo/title` 调用 `list_episodes`。结构定位已足够。
- Media：优先通过 `mediaId`、`Asset.referenceMediaIds`、Shot Context 或 Agent Run Context 获取。Media 是物理媒体句柄，不是主要语义检索对象。

没有为了 API 对称性增加无意义接口。

## 6. get / list / search 语义定义

- `get_xxx`：已知稳定 ID 时读取唯一完整对象；不负责模糊搜索。
- `list_xxx`：已知父级或明确结构范围时列举，并可使用轻量结构过滤；不等同全文搜索。
- `search_xxx`：稳定 ID 未知、只有名称或自然语言描述时发现候选；Agent 判断候选是否匹配。
- `create_xxx`：创建新的长期事实对象并获得稳定 ID。
- `save_xxx`：基于稳定 ID 保存已有对象的新正式状态，不负责定位对象。

Tool description、Provider 签名、README 和 Skill 方法论已按上述语义对齐。

## 7. Work 长期记忆恢复能力

当前合同可表达以下非固定恢复策略：

```text
work.search_works("神龙")
→ script.list_scripts(workId)
→ episode.list_episodes(scriptId, episodeNo=3)
→ scene.search_scenes("张柬之夜闯皇宫", episodeId)
→ shot.list_shots(sceneId) 或 shot.search_shots(query, sceneId)
```

Mock 合同测试已真实执行同类链路，从作品自然语言查询恢复至 Shot ID。各 Result 仍由 Agent 判断，不存在自动编排器。

## 8. Scene / Shot 语义搜索能力

`scene.search_scenes(query, episodeId?)` 与 `shot.search_shots(query, sceneId?)` 均以 query 为唯一必需参数，父级 ID 只是推荐的范围限制。返回完整合同对象，便于 Agent 判断候选；接口不暴露底层搜索实现。

已知父级时仍优先使用 list：Scene 可按 order/location/character 过滤，Shot 可按 shotNo/shotType/character 过滤。已知稳定 ID 时直接 get。

## 9. Asset Resolution Tool 能力

Asset 仍提供 create/get/save/list/search 五种必要能力。`search_assets(query, assetType?)` 返回 Asset 候选，包含 `assetId`、type、name、description、referenceMediaIds，足以完成首轮复用判断，无需强制逐个 get。

`asset-resolution` Skill 已明确：已知 assetId 时直接读取或使用足够的 Context；未知 ID 时搜索；FOUND/NOT_FOUND、适用性和是否新建由 Agent 判断。没有引入 resolve binding、asset plan、compile 或 generation task。

当无可用 Asset 时，可生成标准图并取得稳定 Media；仅当生成能力返回尚未登记的物理结果时才调用 `media.create_media`，避免对已经返回稳定 Media 的 Adapter 重复登记，然后创建 Asset 并保存 referenceMediaIds。

## 10. Media Tool 边界

Media 只负责稳定物理媒体引用的 create/get/save/list；Generation 仍由 `production.generate_image/video/audio` 负责。Skill Core 只依赖 assetId、mediaId、prompt 和必要业务参数，不依赖 URL、bucket、filename、ComfyUI node、workflow JSON、上传 API 或 Provider response。

本批次没有增加 `search_media`，也没有修改任何真实 Provider Adapter 或外部服务。

## 11. Skill 引用调整

- work-creation：加入 `work.search_works`，明确 ID/get、自然语言/search、结构/list 的选择。
- script-adaptation：明确通过 workId + list_scripts 发现 Script。
- episode-development：明确通过 scriptId + list_episodes 及 episodeNo/title 定位 Episode。
- scene-development：加入 `scene.search_scenes`，明确 get/list/search 分层。
- shot-design：加入 `shot.search_shots`，明确 get/list/search 分层。
- asset-resolution：明确 assetId/search 选择，并允许必要时登记未注册 Media。
- shot-production：明确 Media 优先通过稳定 ID、上游引用或结构 list 获取，不做广泛语义搜索。
- historical-research：无需修改。

Skill 不互相调用，没有把恢复策略写成固定 Workflow。

## 12. README / SKILL.md 调整

README 新增五类基础语义、完整长期记忆 Tool 清单、list 过滤参数、可选恢复链、未增加 search 的 Domain 及原因，并明确 Search 技术无关边界。

相关业务 Skill 的 SKILL.md 只增加完成当前判断所需的 Tool 选择方法论；skill.yaml 仅在新增 Tool 确实可用的 Skill 中补 allowed 引用。`agents/openai.yaml` 没有业务流程或 Tool 清单缺口，本批次未修改。

## 13. 测试结果

- `python -m pytest -ra`：collected 28，passed 28，failed 0。
- `python -m mypy src/drama_plugin`：33 个 source file，0 issue。
- `python examples/build_shot_context.py`：PASS，成功加载 shot-production 并构建 SHOT Context。
- 8 个 Skill `quick_validate.py`：全部 PASS。
- Plugin `validate_plugin.py`：PASS。
- 本地 `drama-local` Plugin 已刷新至 `0.1.0+codex.20260812052808`；缓存副本已核对包含三个新增 search Tool 与对应 Skill allowed 引用。
- `git diff --check`：PASS。
- 静态旧同义 Tool 扫描：0 命中。
- Plan/Compile/GenerationTarget/Binding 可执行合同回流扫描：0 命中；测试中的 forbidden 断言为防回归规则。
- Mock/HTTP registry schema 一致性：PASS。
- Skill 引用缺失：0；Tool code 重复：0。

新增测试覆盖必需 Tool、无意义 search 缺席、list/search schema、get/list/search 描述分层、旧同义名、自然语言恢复链及 Skill/README 引用。

## 14. 未解决问题

当前 Python Mock 与 HTTP binding 已表达新合同，但本批次按边界未修改 Java Drama Service 或独立 MCP Server。外部实现尚需在后续批次提供对应 operation，并决定其搜索技术；这不影响 Plugin Core 的稳定语义。

本地 Plugin 的 MCP dependency 仍指向既有 PoC Server，该 Server 不在本批次范围内，也未被修改为实现 42 个 Tool。

## 15. 实际修改文件清单

本批次实际修改：

- `README.md`
- `../../.codex-plugin/plugin.json`（仅本地开发 cachebuster）
- `src/drama_plugin/providers/base/interfaces.py`
- `src/drama_plugin/providers/mock/providers.py`
- `src/drama_plugin/providers/http/providers.py`
- `src/drama_plugin/tools/catalog.py`
- `skills/work-creation/SKILL.md`
- `skills/work-creation/skill.yaml`
- `skills/script-adaptation/SKILL.md`
- `skills/episode-development/SKILL.md`
- `skills/scene-development/SKILL.md`
- `skills/scene-development/skill.yaml`
- `skills/shot-design/SKILL.md`
- `skills/shot-design/skill.yaml`
- `skills/asset-resolution/SKILL.md`
- `skills/asset-resolution/skill.yaml`
- `skills/shot-production/SKILL.md`
- `tests/test_plugin.py`
- `tests/test_providers.py`
- `tests/test_skills.py`
- `tests/test_tools.py`
- `docs/reports/Drama Plugin 长期记忆Tool接口补齐执行报告.md`

工作区中还存在上一轮业务模型重构的未提交修改；本批次未回退、覆盖或提交这些改动。

## 最终明确回答

- Work 是否支持 search_works？**是，`work.search_works(query)`。**
- Scene 是否支持 search_scenes？**是，`scene.search_scenes(query, episodeId?)`。**
- Shot 是否支持 search_shots？**是，`shot.search_shots(query, sceneId?)`。**
- Asset 是否支持 search_assets？**是，`asset.search_assets(query, assetType?)`。**
- Script 是否仍优先通过 workId + list_scripts 发现？**是。**
- Episode 是否仍优先通过 scriptId + list_episodes 发现？**是，并支持 episodeNo/title 过滤。**
- Media 是否仍优先通过 mediaId / 上游引用获取？**是。**
- 当前 Agent 是否已经能够在丢失稳定 ID 时重新找回长期创作记忆？**是，Work、Scene、Shot、Asset 可语义发现，Script/Episode 可沿父级结构恢复。**
- 是否新增了任何不必要的对称性接口？**否。未增加 search_scripts、search_episodes、search_media。**
- 是否重新引入了 Workflow / Plan / Compile / Binding？**否。**
