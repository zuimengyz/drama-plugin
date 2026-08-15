# 16-Host Skill 加载与 Shot 列表运行集成收口执行报告

## 1. 执行摘要

本批严格按 Phase A → Phase B 执行，没有重新生成 Research → Work → Script → Episode → Scene → Shot 数据，也没有进入 Asset Resolution、ComfyUI 或 Media Production。

最终结论：

```text
REAL_SKILL_AUTO_SELECTION = PASS
REAL_SKILL_AUTO_LOAD = PASS
SHOT_LIST_GET_CONSISTENCY = PASS

BATCH_4_INTEGRATION_CLOSURE = PASS
READY_FOR_COMFYUI_MCP = YES
```

Phase A 通过 Codex 正常 marketplace、cachebuster、plugin reinstall 和独立临时 Host 会话完成。Phase B 证明 `shot.list_shots` 的问题不是 MCP schema、MCP adapter、Java Domain 或 MySQL 数据，而是 Plugin HTTP Provider 把未提供的可选过滤参数以空字符串发送给 Java，导致 Java 正确执行了 `shot_no = ''` / `shot_type = ''` 过滤。源码只在 `HttpMemoryProvider.list_shots` 省略 `None` 参数，并新增一个既有 pytest 模式的回归测试。

## 2. Batch 4 遗留问题复核

Batch 4 已经证明真实 Creative E2E、Java persistence、stable-ID reload、质量 rubric、persist gate 和父子完整性均通过。本批仅复核两个遗留项：

1. Host 注册/缓存是否确实加载 Batch 1～3 最新五个 Creative Skill；
2. 真实 Scene `scene_399ace55923e47be8092eb808d7d284c` 的 10 个 Shot 是否可通过 `shot.list_shots` 稳定枚举，并与 `get_shot`、Java HTTP 和 DB 一致。

## 3. 本批边界

实际执行：

- 读取报告 15；
- Host/plugin/MCP runtime 版本与路径取证；
- 五个 Creative Skill hash 对比；
- 无持久化 Work Review smoke；
- 既有 Scene/Shot 的 list/get/search 只读回归；
- 最小 Plugin Provider bugfix 与回归测试；
- Plugin、Skill、MCP 自动化回归；
- 报告落盘。

明确未执行：

- 新建或保存任何 Creative Domain 对象；
- 修改 Creative Skill；
- 修改 Tool/MCP Contract；
- 修改 Java Domain、DTO、repository 或 schema；
- 修改数据库数据；
- ComfyUI、Asset、Image、Video 或 Audio 生产。

## 4. 修改前环境

| 项目 | 修改前事实 |
|---|---|
| Workspace | `/home/ubuntu/AI_PROJECT/historical-plugin/drama-plugin/plugin` |
| Git branch | `master` |
| Git commit | `71b97e58a4a709fa2c318cedb8b6a237741db2dc` |
| origin/master | 与 HEAD 一致，ahead/behind=`0/0` |
| Plugin manifest version | `0.1.0+codex.20260812052808` |
| Codex marketplace source | `https://github.com/zuimengyz/drama-plugin.git` |
| Host cache | `~/.codex/plugins/cache/drama-marketplace/drama-plugin/0.1.0+codex.20260812052808` |
| Cache materialized time | `2026-08-15 11:43:37 +08:00` |
| MCP process | 修改前未运行 |
| Java process | 修改前未运行 |
| MCP `.venv` | 存在，但尚未安装项目依赖 |

本批开始时三个 Git 仓库均无工作区改动。报告 15 所述同版本旧 cache 已在本批任务启动前由 Host 重新物化；本批修改前对整个 `plugin/` 与该 cache 执行逐文件比较，结果为零差异，五个核心 Skill hash 已相等。

## 5. Workspace / Git / Installed / Cache / MCP Runtime 版本事实表

| Layer | Path | Version/Commit | Evidence |
|---|---|---|---|
| Workspace | `/home/ubuntu/AI_PROJECT/historical-plugin/drama-plugin/plugin` | `0.1.0+codex.20260815040146`；Git base `71b97e58…2dc` | manifest、`git rev-parse` |
| Git source | `/home/ubuntu/AI_PROJECT/historical-plugin/drama-plugin`；origin=`https://github.com/zuimengyz/drama-plugin.git` | `master@71b97e58…2dc`，本批改动尚未 commit/push | `git remote -v`、`git status` |
| Codex marketplace | `/home/ubuntu/AI_PROJECT/historical-plugin/drama-plugin/.agents/plugins/marketplace.json` | local development source | `codex plugin marketplace add`、`~/.codex/config.toml` |
| Codex installed plugin | `/home/ubuntu/AI_PROJECT/historical-plugin/drama-plugin/plugin` | `0.1.0+codex.20260815040146` | `codex plugin list` |
| Codex cache | `/home/ubuntu/.codex/plugins/cache/drama-marketplace/drama-plugin/0.1.0+codex.20260815040146` | `0.1.0+codex.20260815040146` | `codex plugin add --json`、逐文件 diff |
| MCP runtime package | `/home/ubuntu/AI_PROJECT/historical-plugin/drama-plugin/plugin/src/drama_plugin` | editable `drama-plugin==0.1.0`，workspace source | Python `__file__` |
| MCP adapter | `/home/ubuntu/AI_PROJECT/historical-plugin/drama-mcp-service/src/drama_mcp_service` | Git `32008119…b4d`，workspace clean | Python `__file__`、Git status |

关键输出：

```text
WORKSPACE_PLUGIN_VERSION = 0.1.0+codex.20260815040146
INSTALLED_PLUGIN_VERSION = 0.1.0+codex.20260815040146
HOST_CACHE_VERSION = 0.1.0+codex.20260815040146
MCP_RUNTIME_PLUGIN_PATH = /home/ubuntu/AI_PROJECT/historical-plugin/drama-plugin/plugin/src/drama_plugin/__init__.py
```

## 6. Runtime Python Import Source

在 MCP 的真实 Python 环境执行 import，结果：

```text
PYTHON = /home/ubuntu/AI_PROJECT/historical-plugin/drama-mcp-service/.venv/bin/python
DRAMA_PLUGIN = /home/ubuntu/AI_PROJECT/historical-plugin/drama-plugin/plugin/src/drama_plugin/__init__.py
SHOT_PROVIDER = /home/ubuntu/AI_PROJECT/historical-plugin/drama-plugin/plugin/src/drama_plugin/providers/http/providers.py
SKILL_REGISTRY = /home/ubuntu/AI_PROJECT/historical-plugin/drama-plugin/plugin/src/drama_plugin/skills/registry.py
MCP_ADAPTER = /home/ubuntu/AI_PROJECT/historical-plugin/drama-mcp-service/src/drama_mcp_service/adapter.py
```

因此：

```text
RUNTIME_PLUGIN_SOURCE = /home/ubuntu/AI_PROJECT/historical-plugin/drama-plugin/plugin/src/drama_plugin
MCP_RUNTIME_SOURCE_MISMATCH = NO
```

## 7. Host Skill Hash 对比

| Skill | Workspace SHA-256 | 新 Host cache SHA-256 | 结果 |
|---|---|---|---|
| Work | `8d5612eaabe4f8ae9166a819a9c869300cd5622d3d1a7e01a02eb0729efcaa40` | 同左 | PASS |
| Script | `a04173a7e7dc052674512518f654ee4625517670899dafdaffd6551e01e45372` | 同左 | PASS |
| Episode | `798360fce2425cd65cfdf711b90bc1e437dc7fc2c1e2e858d6b2e57e75a8410e` | 同左 | PASS |
| Scene | `d4482f99456f38db53d4c8a4342c9a19750cece604e8803cef67495c09fe8636` | 同左 | PASS |
| Shot | `08a79e0d9fc02a49971f7233a747f26c6bb40b9dd1846cbc263341b6f6139ce0` | 同左 | PASS |

附加冻结项：

```text
HISTORICAL_RESEARCH_WORKSPACE_HASH = 45db79aee3204db440756e9b9a95025cd4f0abaaf815752de46097b71d5f96ad
HISTORICAL_RESEARCH_RUNTIME_HASH = 45db79aee3204db440756e9b9a95025cd4f0abaaf815752de46097b71d5f96ad
```

要求的逐项输出：

```text
WORK_SKILL_WORKSPACE_HASH = 8d5612eaabe4f8ae9166a819a9c869300cd5622d3d1a7e01a02eb0729efcaa40
WORK_SKILL_RUNTIME_HASH = 8d5612eaabe4f8ae9166a819a9c869300cd5622d3d1a7e01a02eb0729efcaa40

SCRIPT_SKILL_WORKSPACE_HASH = a04173a7e7dc052674512518f654ee4625517670899dafdaffd6551e01e45372
SCRIPT_SKILL_RUNTIME_HASH = a04173a7e7dc052674512518f654ee4625517670899dafdaffd6551e01e45372

EPISODE_SKILL_WORKSPACE_HASH = 798360fce2425cd65cfdf711b90bc1e437dc7fc2c1e2e858d6b2e57e75a8410e
EPISODE_SKILL_RUNTIME_HASH = 798360fce2425cd65cfdf711b90bc1e437dc7fc2c1e2e858d6b2e57e75a8410e

SCENE_SKILL_WORKSPACE_HASH = d4482f99456f38db53d4c8a4342c9a19750cece604e8803cef67495c09fe8636
SCENE_SKILL_RUNTIME_HASH = d4482f99456f38db53d4c8a4342c9a19750cece604e8803cef67495c09fe8636

SHOT_SKILL_WORKSPACE_HASH = 08a79e0d9fc02a49971f7233a747f26c6bb40b9dd1846cbc263341b6f6139ce0
SHOT_SKILL_RUNTIME_HASH = 08a79e0d9fc02a49971f7233a747f26c6bb40b9dd1846cbc263341b6f6139ce0
```

## 8. Plugin 更新/缓存刷新过程

本批没有向 cache 复制文件。实际流程：

1. 读取 Codex 配置，确认修改前 `drama-marketplace` 是 Git source；
2. 本批开始时验证 Host 已重新物化旧版本号 cache，且 Skill 内容与 workspace 相等；
3. Shot Provider 源码 bugfix 完成后，使用内置 plugin update helper 将单一 cachebuster 从 `20260812052808` 更新为 `20260815040146`；
4. 通过 Codex CLI 将 `drama-marketplace` 开发源切换为当前 Git 工作区；
5. 执行 `codex plugin add drama-plugin@drama-marketplace --json` 正式重装；
6. CLI 返回新 cache path；
7. 对 workspace plugin 与新 cache 做逐文件 diff（排除运行生成的 `__pycache__` / `.pytest_cache`），零差异；
8. 启动独立 `codex exec --ephemeral --sandbox read-only` Host 会话做 post-reinstall 自动加载验证。

官方 Codex 插件说明也要求在本地 marketplace 中安装后刷新/新会话测试，而不是手工修改 cache：[Build plugins](https://learn.chatgpt.com/docs/build-plugins)。

## 9. 更新后的 Host Plugin 版本

```text
PLUGIN_VERSION_OLD = 0.1.0+codex.20260812052808
PLUGIN_VERSION_NEW = 0.1.0+codex.20260815040146
HOST_REGISTERED_PLUGIN = drama-plugin@drama-marketplace
HOST_REGISTERED_STATUS = installed, enabled
HOST_CACHE_PATH = /home/ubuntu/.codex/plugins/cache/drama-marketplace/drama-plugin/0.1.0+codex.20260815040146
```

必须 bump 的原因：源码 bugfix 发生后，旧 cache key 无法证明整个 installed plugin 与 workspace 相等；当前仓库已经使用 `+codex.<cachebuster>` 机制，因此只替换既有 suffix，没有引入版本框架。

## 10. Skill 自动 Selection / Load 验证

独立临时 Host 输入：

> 仅审查“苏武奉命出使，后被扣北海牧羊十九年。最终归汉。”是否达到 Work 持久化条件；禁止 create/save。

真实 Host trace：

```text
selected skill = drama-plugin:work-creation
loaded path = /home/ubuntu/.codex/plugins/cache/drama-marketplace/drama-plugin/
              0.1.0+codex.20260815040146/skills/work-creation/SKILL.md
loaded reference = .../work-creation/references/review.md
Review = FAIL
Persist = NO PERSIST
```

判断原因与新版 rubric 一致：该稿只是历史梗概，缺少主人公主动选择/内在需要、有效对抗、具体 stakes、因果递进、人物与关系弧、主题拷问、高潮、结构、史实/虚构边界和 downstream readiness。

该会话使用 `--ephemeral --sandbox read-only`，没有调用 MCP 或任何写入工具。

```text
SKILL_LOAD_PROOF = DIRECT
REAL_SKILL_AUTO_SELECTION = PASS
REAL_SKILL_AUTO_LOAD = PASS
```

## 11. Phase A 最终结论

```text
HOST_PLUGIN_RUNTIME_CURRENT = PASS
WORK_SKILL_HASH_MATCH = PASS
SCRIPT_SKILL_HASH_MATCH = PASS
EPISODE_SKILL_HASH_MATCH = PASS
SCENE_SKILL_HASH_MATCH = PASS
SHOT_SKILL_HASH_MATCH = PASS
```

Host 问题根因分类：

```text
HOST_ROOT_CAUSE = PLUGIN_CACHE_STALE + HOST_REGISTRATION_STALE
```

本批开始时 Host 已重新物化同版本 cache 并消除 Skill 内容差异；为保证本批源码修复后的整个 Plugin 也可验证，进一步使用 cachebuster 与正式重装生成新版本目录。

## 12. Batch 4 Scene / Shot 数据复核

继续使用原有数据，没有创建新 Shot：

```text
TEST_SCENE_ID = scene_399ace55923e47be8092eb808d7d284c
EXPECTED_SHOT_COUNT = 10
```

Batch 4 的 10 个 stable IDs 全部仍存在。

## 13. shot.list_shots 刷新后首次复测

刷新运行版本、启动真实 Java/MCP、但尚未修改源码时：

```text
tool = shot.list_shots
arguments = {"scene_id":"scene_399ace55923e47be8092eb808d7d284c"}
MCP tool count = 44
MCP list result = []
MCP_LIST_SHOT_COUNT_BEFORE_FIX = 0
```

因此 Shot 问题不是单纯 stale runtime，按层继续诊断。

## 14. MCP 参数检查

MCP 的真实 `shot.list_shots` schema：

```text
required = ["scene_id"]
properties = scene_id, shot_no, shot_type, character
additionalProperties = false
```

真实调用使用 `scene_id`，没有使用 `sceneId`、`parent_id`、`work_id` 或 `episode_id`。MCP validation 与 argument coercion 均通过，结果不是 error。

## 15. Plugin Tool 层检查

在同一 Python runtime 绕过 MCP transport、保留 `DramaPlugin` Tool registry 与 HTTP Provider，直接调用：

```text
plugin.tools.invoke("shot.list_shots", scene_id=TEST_SCENE_ID)
PLUGIN_TOOL_LIST_COUNT_BEFORE_FIX = 0
```

因此问题不在 MCP projection/serialization，继续进入 Provider/HTTP 层。

## 16. Provider / HTTP Binding 检查

源码逻辑当时传入：

```python
{
  "scene_id": scene_id,
  "shot_no": None,
  "shot_type": None,
  "character": None,
}
```

真实 httpx URL 语义为：

```text
?scene_id=<id>&shot_no=&shot_type=&character=
```

Java 的 optional `@RequestParam` 因参数实际存在而得到空字符串，不是 `null`；Java list implementation 随即正确添加 `shot_no = ''` 和 `shot_type = ''` 过滤，结果为 0。

## 17. Java HTTP 检查

使用相同认证、相同 Java endpoint，但只发送真正提供的参数：

```text
HTTP method = GET
URL path = /api/tool/shot/list
query = scene_id=scene_399ace55923e47be8092eb808d7d284c
JAVA_HTTP_LIST_SHOT_COUNT = 10
```

返回的 10 个 stable IDs 与 Batch 4 集合相等。认证值没有进入日志或报告。

## 18. DB 只读交叉检查

对现有云 MySQL 执行只读查询：

```sql
SELECT COUNT(*)
FROM drama_shot
WHERE scene_id = 'scene_399ace55923e47be8092eb808d7d284c';
```

结果：

```text
DB_SHOT_COUNT = 10
DB stable-ID set = Batch 4 known set
DB_WRITE_COUNT = 0
```

## 19. 根因定位

```text
SHOT_LIST_ROOT_CAUSE = HTTP_PROVIDER_BINDING
```

准确根因：Plugin HTTP Provider 没有省略未提供的可选 query 参数；httpx 将 `None` 编码为空值，Java 将空值视为显式过滤条件。

已排除：

- `STALE_RUNTIME`：统一 runtime 后仍复现；
- `MCP_ARGUMENT_MAPPING`：schema 和真实参数正确；
- `MCP_ADAPTER`：Plugin 直接调用同样为 0；
- `PLUGIN_TOOL_IMPLEMENTATION`：registry 正确绑定现有 provider；
- `JAVA_HTTP_MAPPING`：只发 `scene_id` 时返回 10；
- `JAVA_QUERY_IMPLEMENTATION`：按非空过滤值执行的行为正确；
- `DB`：真实存在 10 行。

## 20. 最小修复说明

只修改 `HttpMemoryProvider.list_shots`：

- 始终发送必填 `scene_id`；
- `shot_no`、`shot_type`、`character` 仅在值不为 `None` 时加入 query params；
- 不修改通用 HTTP client；
- 不修改其他 list/search；
- 不新增 Tool、framework、adapter 或 query 体系。

## 21. shot.list_shots 最终结果

MCP Service 重启加载修复后：

```text
EXPECTED_SHOT_COUNT = 10
MCP_LIST_SHOT_COUNT = 10
JAVA_HTTP_LIST_SHOT_COUNT = 10
DB_SHOT_COUNT = 10
```

## 22. list/get stable ID 集合一致性

```text
LIST_SHOT_IDS = [
  shot_11b46c83ee77483fb01c6903cfa198c3,
  shot_278f97a987174dfeb973e53f3bbb5075,
  shot_27ff438363f64a948a6a66184a140cf1,
  shot_420f581d79ef4dc898359809900cb707,
  shot_5559407312e04d9988591a11d3bcbf7f,
  shot_6562bc6e4c0f47818f407fd0c3a11a83,
  shot_a9dc0ba7dfdc4e7ea2d1d479403c6274,
  shot_bddf109241874afb85376a773eff0691,
  shot_e1ba8436b6b047a8b12a9eba0ec19822,
  shot_e8433461bc644caa85914a8f9f0e739d
]

GET_SHOT_IDS = same set as LIST_SHOT_IDS
LIST_IDS_EQUAL_BATCH_4_KNOWN_IDS = PASS
LIST_GET_SET_EQUALITY = PASS
```

Contract 未声明必须按何种顺序，因此验收比较集合，不强制返回顺序。

## 23. parent scene 一致性

对 list 返回的每个 stable ID 调用 `shot.get_shot`：

```text
SHOT_GET_COUNT = 10
SHOT_GET_PASS = 10/10
all(get.sceneId == TEST_SCENE_ID) = true
PARENT_FILTER_CORRECT = PASS
```

## 24. search_shots 诊断结果

从真实 list 结果选择已知标题 `热酒越界` 作为明确可匹配查询，并限定同一 `scene_id`：

```text
SEARCH_QUERY = 热酒越界
SEARCH_COUNT = 1
SEARCH_IDS = [shot_6562bc6e4c0f47818f407fd0c3a11a83]
SEARCH_BEHAVIOR = PASS
```

本批没有把 search 定义为“返回 Scene 全部 10 条”。

## 25. Regression tests

新增既有 pytest 模式测试：

```text
test_http_list_shots_omits_absent_filters_and_returns_all_scene_shots
```

覆盖：

```text
scene has two shots
→ provider.list_shots(scene_id) without optional filters
→ request query contains only scene_id
→ returns both matching shots
```

定向结果：`1 passed`。

## 26. Tool Contract 稳定性

使用 `ToolRegistry.describe()` 的排序 canonical JSON 重新计算：

```text
TOOL_COUNT = 44
TOOL_CONTRACT_HASH = 824f09a38b954b36fe1f7ced616e5ce98d10b918171d838333caec97c6ac90ca
TOOL_CONTRACT_UNCHANGED = PASS
MCP_CONTRACT_UNCHANGED = PASS
```

## 27. Creative Skill 未修改证明

开始前五个核心 `SKILL.md` hash 来自报告 15 并在本批修改前重新计算；结束后再次计算，全部相同。`git diff -- plugin/skills` 为空，新 Host cache hash 也逐项相同。

```text
CREATIVE_SKILLS_MODIFIED = NO
CREATIVE_SKILLS_UNCHANGED = PASS
```

## 28. Java Domain / DB 未修改证明

`drama-service` 在本批开始与结束均为 clean Git worktree。Java Controller、DTO、Domain、Service、Mapper 和 schema 均未修改。

数据库仅执行 list/get/search 读链与两条只读 SELECT；没有 create/save/update/delete/schema 操作。

```text
JAVA_DOMAIN_MODIFIED = NO
JAVA_DOMAIN_UNCHANGED = PASS
DATABASE_MODIFIED = NO
```

## 29. Plugin 正确更新方法

当前本地开发机制的可重复流程：

1. Git 工作区是开发真源；确认目标变更和 `git status`；
2. 使用现有 cachebuster helper 更新 `.codex-plugin/plugin.json` 的 `+codex.<token>`，只替换 suffix；
3. 运行 plugin validation、Skill validation 和测试；
4. 用 `codex plugin marketplace list` 确认 `drama-marketplace` 指向当前正在编辑的 Git 工作区；
5. 执行 `codex plugin add drama-plugin@drama-marketplace --json` 重装；
6. 启动新任务或 `codex exec --ephemeral`，验证实际 Skill path/version/hash；
7. 验证 workspace 与生成 cache 内容一致。

cache 只是运行产物，禁止直接编辑 `~/.codex/plugins/cache/*`。

当前本批改动尚未 commit/push。其他机器或仍使用远端 Git marketplace 的 Host 必须先取得包含本批改动的 Git 提交，再按其配置的 marketplace refresh/reinstall 流程更新；不能把当前本机 cache 当作发布源。

## 30. 自动化回归

| 检查 | 结果 |
|---|---|
| Drama Plugin full pytest | PASS，`73 passed` |
| Skill tests | PASS，`21 passed` |
| 新 list_shots regression | PASS，`1 passed` |
| Plugin mypy | PASS，34 source files |
| MCP mypy | PASS，4 source files |
| Skill quick validation | PASS，8/8 Skills |
| Tool reference/config validation | PASS，13 tests |
| Plugin manifest validation | PASS |
| Drama MCP Service pytest | PASS，`13 passed` |
| Tool registry | PASS，44 tools |
| Tool Contract hash | PASS，冻结 hash |
| `git diff --check` | PASS |

首次 Plugin pytest 受到宿主 `ALL_PROXY=socks://127.0.0.1:7890` 与当前 httpx 支持的 proxy scheme 不兼容影响；清除仅影响测试的 proxy 环境变量后全量通过。这不是本批产品变更。

Java 源码没有修改，因此没有运行完整 Java test suite；本批已构建并启动当前 Java Service，真实 Java HTTP + 云 MySQL 只读回归通过。

## 31. 修改文件列表

```text
MODIFIED:
drama-plugin/plugin/.codex-plugin/plugin.json
drama-plugin/plugin/src/drama_plugin/providers/http/providers.py
drama-plugin/plugin/tests/test_providers.py

ADDED:
drama-plugin/plugin/docs/reports/16-Host Skill加载与Shot列表运行集成收口执行报告.md
```

运行环境变化（非仓库源码）：

- Codex `drama-marketplace` 从远端 Git snapshot 切换为当前本地 Git 工作区开发源；
- 新增合法 cache 目录 `0.1.0+codex.20260815040146`；
- workspace MCP `.venv` 安装 editable Plugin/MCP 与 dev dependencies；
- Java/MCP 进程在验收期间启动。

```text
RUNTIME_ONLY_CLOSURE = NO
```

## 32. 已知不足

- 本批改动尚未 commit/push；远端 Git marketplace 用户尚未获得 Provider 修复和新 cachebuster；
- Host 新版本加载通过一个独立临时 Codex 会话验证，不等于长期跨版本统计；
- 当前运行环境有一个 `socks://` proxy scheme 与 httpx 不兼容，启动 MCP/测试时需要对本地回环链路清除该 proxy；
- Java 全量测试未因本批重复运行，因为 Java 源码零修改；真实 HTTP 与 DB 回归已覆盖本问题；
- 本批没有测试 Asset/ComfyUI/Generation，READY 仅表示两个前置阻塞已清除。

## 33. 是否可以进入 ComfyUI MCP

Q1 与 Q2 均为 YES，平台进入门槛满足：

```text
Q1 = YES
Q2 = YES
READY_FOR_COMFYUI_MCP = YES
```

这只批准下一阶段开始，不代表 ComfyUI MCP、Asset Resolution 或媒体生成已经通过。

## 34. 最终验收

```text
HOST_PLUGIN_RUNTIME_CURRENT = PASS

REAL_SKILL_AUTO_SELECTION = PASS
REAL_SKILL_AUTO_LOAD = PASS

WORK_SKILL_HASH_MATCH = PASS
SCRIPT_SKILL_HASH_MATCH = PASS
EPISODE_SKILL_HASH_MATCH = PASS
SCENE_SKILL_HASH_MATCH = PASS
SHOT_SKILL_HASH_MATCH = PASS

SHOT_LIST_MCP = PASS
SHOT_LIST_JAVA_HTTP = PASS
SHOT_LIST_DB = PASS

SHOT_LIST_GET_CONSISTENCY = PASS
SHOT_PARENT_FILTER = PASS

SOURCE_CODE_BUG_FOUND = YES
SOURCE_CODE_MODIFIED = YES
RUNTIME_ONLY_CLOSURE = NO

CREATIVE_SKILLS_MODIFIED = NO
TOOL_CONTRACT_MODIFIED = NO
MCP_CONTRACT_MODIFIED = NO
JAVA_DOMAIN_MODIFIED = NO
DATABASE_MODIFIED = NO

PLUGIN_INSTALLATION_CHANGE_REQUIRED = YES
HARNESS_CODE_CHANGE_REQUIRED = NO
MCP_CODE_CHANGE_REQUIRED = NO
PLUGIN_CODE_CHANGE_REQUIRED = YES
JAVA_CODE_CHANGE_REQUIRED = NO

BATCH_4_INTEGRATION_CLOSURE = PASS

READY_FOR_COMFYUI_MCP = YES
```

### Q1

当前 Codex Host 正常自动 Skill selection/load 是否已经可以证明加载的是 Batch 1～3 最新 Work/Script/Episode/Scene/Shot Skill？

```text
YES
```

证据：五个 workspace/cache hash 全相等；重装后的独立只读 Host 会话自动选择 `drama-plugin:work-creation`，直接加载新 cache 路径 `0.1.0+codex.20260815040146` 并执行完整 review rubric，输出 `FAIL / NO PERSIST`。

### Q2

对真实 Scene 调用 `shot.list_shots(sceneId)` 是否稳定返回 Batch 4 全部 10 个 Shot？

```text
YES

MCP count = 10
Java HTTP count = 10
DB count = 10
stable-ID set equality = PASS
parent scene equality = PASS
```

本批最终把两个事实闭合为：

```text
Workspace distribution
= Installed Plugin / Host cache
= Host auto-loaded Creative Skill content

Scene
→ shot.list_shots
→ 10 stable Shots
→ 10/10 get_shot
```
