# Batch 5.0.1 — Visual Provider Integration Contract 执行报告

> 执行日期：2026-08-16  
> 报告编号：22  
> 执行范围：Drama Plugin Skill Core、OpenAI/Codex Host adapter、Host integration 文档、静态/运行 smoke。  
> 未执行：付费生成、文件上传、Saved/Custom/Dynamic Workflow、Java/MCP/数据库或 Drama Tool Contract 修改。

## 1. 执行摘要

本批已把 Batch 5 中依赖任务 Prompt 手工串联 Drama 与 Comfy 的知识，收口到 `shot-production` Skill 与 Host adapter：

```text
Drama Skill Core
→ 声明平台中立 Visual Production Capability
→ 0/1/2/3 reference 策略
→ Stable Media resolve / provider handoff / review / import

OpenAI/Codex Host adapter
→ 当前用 external comfy-cloud MCP 满足视觉能力

Drama Domain / MCP / Java / DB
→ 不知道 Comfy，保持不变
```

最终正常 marketplace 安装版本为 `0.1.0+codex.20260815155920`。工作区、安装缓存中的 Skill、reference、Host adapter SHA-256 完全一致。三个零成本 Host 场景通过，Comfy OAuth 在出现 refresh-token reuse 后通过官方登录流程恢复，真实只读服务探测返回 `authenticated (OAuth)`、40 tools。

```text
BATCH_5_0_1 = PASS
```

## 2. 插件结构与边界审计

真实结构：

```text
plugin/.codex-plugin/plugin.json
plugin/.mcp.json
plugin/skills/shot-production/{SKILL.md,skill.yaml,agents/openai.yaml}
plugin/skills/shot-production/references/visual-provider.md
plugin/docs/visual-provider-host-integration.md
```

- Skill 共 8 个；本批未新增 Skill。
- Drama Tool 共 44 个；本批未新增、删除或修改 Tool Contract。
- `.mcp.json` 只声明 `drama-tools = http://127.0.0.1:8765/mcp`。
- 仓库没有既有项目级 `.codex/config.toml`，因此未为本批强行新增。
- Comfy Cloud 是 Host 外部依赖，不是 Drama bundled MCP。

审计哈希：

| 对象 | 修改前 | 修改后 | 结论 |
| --- | --- | --- | --- |
| `.mcp.json` | `835627d669b0cffb2629c4e98995496ecf237a52c08758ef338f1ee86aea8687` | 相同 | 未修改 |
| Tool catalog | `150b34e40890fa0e0ec234b9ad876fe0b54c5b719112f60083d38b71dddcde5b` | 相同 | 44-tool Contract 未修改 |
| Java Service | 既有用户修改 `application.yml` | 本批未触碰 | Java Contract 未修改 |
| Drama MCP Service | clean | clean | 未修改 |

## 3. 最小实现

### 3.1 Skill Core

`shot-production` 现在明确：

- 非视觉上下文、研究、创作、Shot design 不依赖 Visual Provider；
- 图片/视频规划和执行加载最小 capability reference；
- 真正执行前只预检本次所需 Drama 与视觉能力；
- 缺失时返回 `DRAMA_PROVIDER_UNAVAILABLE`、`VISUAL_PROVIDER_UNAVAILABLE` 或 `VISUAL_PROVIDER_CAPABILITY_MISSING`；
- reference 数量固定为 `0/1/2/3`，够用就少用；
- 正式 reference 必须优先来自 stable Asset/Media；
- 输入链为 `Asset → Media → resolve → local download → provider upload`；
- 输出链为 `wait → fetch → Visual Review PASS → media.import_media → stable mediaId`；
- Review FAIL 默认最多一次最小 Prompt/reference 修正；
- 禁止 Saved、Custom、Dynamic Workflow 与模型 benchmark。

Skill Core 只维护以下语义能力，不包含 Comfy 品牌或 Tool schema：

```text
visual.template.discover
visual.input.upload
visual.image.generate
visual.job.wait
visual.output.fetch
```

### 3.2 Host adapter

`agents/openai.yaml` 使用规范已支持的 `dependencies.tools`，声明：

```text
type = mcp
value = comfy-cloud
transport = streamable_http
url = https://cloud.comfy.org/mcp
```

该声明只属于 OpenAI/Codex adapter。其他 Host 可用自己的 MCP Client 或 Tool Adapter 提供同一能力；Skill Core 不依赖 Codex。

### 3.3 当前 Comfy capability mapping

| Skill capability | 当前 Comfy Cloud 实现 |
| --- | --- |
| template discover | `search_templates`、`get_template`，必要时 `get_template_schema` |
| input upload | `upload_file` |
| image generate | `run_template` |
| job wait | `wait_for_job`，必要时 `get_job_status` |
| output fetch | `get_output` |

只记录名称与语义。`runtime MCP server` 是 input/output schema 的唯一真源；仓库没有新增任何 Comfy schema 副本。

### 3.4 当前 verified preferences

以下只位于 Host integration 文档，是当前 Provider 实现偏好，不是 Drama 业务 Contract：

| Reference count | 当前已验证官方模板 |
| ---: | --- |
| 0 | `api_google_nano_banana2_text_to_image` |
| 1 | `image_mage_flow_edit_turbo_int8` |
| 2 | `image_qwen_image_edit_2511` |
| 3 | `api_bfl_flux2_max_sofa_swap` |

只有偏好不存在或不满足生成意图时才发现替代官方模板；不会自动创建 Workflow。

## 4. 迭代中发现并收口的问题

第一次 plan-only smoke 只给出了 Drama 上下文、Review 与 Media 回写，没有显式形成 provider upload/generate/wait/fetch。根因是 reference 只要求“执行前”加载。最小修正为“图片/视频规划或执行均加载 capability reference，只有实际执行才做 Provider preflight”。

第一次视觉 preflight 又把 Drama MCP 的旧逻辑 `production.generate_image` 误判为当前可用视觉 Provider。为避免假 READY，本批只从 `shot-production` Skill tool preference 移除了图片/视频逻辑 Tool；44-tool catalog 本身完全保留，音频 `production.generate_audio` 也保留。最终视觉路径必须由 Host-provided capability 满足。

没有新增 Manager、Registry、Router、Wrapper、Adapter Service 或 Workflow framework。

## 5. 正常安装与运行版本

使用仓库现有机制：

```text
update_plugin_cachebuster.py
→ codex plugin add drama-plugin@drama-marketplace
→ new cache directory
→ ephemeral Host smoke
```

最终证据：

```text
WORKSPACE_PLUGIN_VERSION = 0.1.0+codex.20260815155920
INSTALLED_PLUGIN_VERSION = 0.1.0+codex.20260815155920
HOST_CACHE_PATH = /home/ubuntu/.codex/plugins/cache/drama-marketplace/drama-plugin/0.1.0+codex.20260815155920

SHOT_PRODUCTION_SKILL_HASH = b40c2b9f108342c60a4011e2f319b0d6758fc03cde779951f1dfedef63071a68
VISUAL_PROVIDER_REFERENCE_HASH = a52227fc22543372f73baaaea3286a4bc1dbd1ae221fdc35d823f961254405a0
OPENAI_ADAPTER_HASH = 333132dde4fd328c74da34c6ae57f6b09a01aeaeceeb516bb36ea6f8276a1b4e
WORKSPACE_CACHE_HASH_MATCH = PASS
```

缓存仅是运行产物；Git/marketplace source 仍是插件真源，没有手工复制文件到缓存。

## 6. Host Integration smoke

### Scenario A — 非视觉任务

业务 Prompt 只要求读取并总结真实 Shot `shot_11b46c83ee77483fb01c6903cfa198c3` 的生产上下文。

结果：

- Host 自动选择 `drama-plugin:shot-production`；
- 实际加载最终安装缓存中的 Skill；
- 只调用 `drama-tools` 的 Shot、Scene、Context 读取；
- 没有加载视觉 capability reference，没有调用 Comfy，没有写操作；
- 即使当时 Comfy OAuth refresh 失败，Drama Context 仍完整返回。

```text
NON_VISUAL_WITHOUT_COMFY = PASS
```

### Scenario B — Visual Production Plan

业务 Prompt 只要求为真实 Shot 制定正式图片流程骨架，不列 Provider Tool 名称，不执行生成。

最终计划自动包含：

```text
Drama Context
→ Asset / stable Media discovery
→ 0–3 reference selection
→ media resolve / local download
→ Visual Provider preflight / upload / generate / wait / fetch
→ Visual Review
→ media import
→ stable mediaId / Shot role / context refresh
```

计划还包含三个标准失败状态、最多一次 revise、禁止动态 Workflow 与 Provider 临时信息进入长期记忆。

```text
VISUAL_SKILL_ORCHESTRATION = PASS
```

### Scenario C — Visual Provider Missing

通过业务 Prompt 安全模拟“Host 没有暴露外部视觉能力”，没有删除登录、修改全局配置或调用业务数据。

结果准确返回：

```text
VISUAL_PROVIDER_UNAVAILABLE
```

同时明确 Work、Script、Episode、Scene、Shot、Research、Context 与非视觉 planning 不受影响。

```text
VISUAL_PROVIDER_OPTIONAL_DEPENDENCY = PASS
```

## 7. Comfy Cloud 零成本真实 preflight

执行时 Host 的旧 OAuth refresh token 出现 `invalid_grant: refresh token reuse detected`。使用官方 `codex mcp login comfy-cloud` 流程恢复；未更改 endpoint、未保存凭据、未调用生成。

恢复后的真实只读证据：

```text
server_name = comfyui-cloud
environment = production
version = 0.39.1
auth_state = authenticated (OAuth)
tool_count = 40
```

`get_server_info`、`search_templates`、`get_template_schema` 成功。Host 确认具备发现、上传、生成、等待、取回能力；本批未实际调用上传/生成/等待/取回，未消费 credits。

`codex mcp list` 同时保留：

```text
drama-tools = enabled
comfy-cloud = enabled
```

## 8. 自动化回归

| 检查 | 结果 |
| --- | --- |
| Skill quick validation | PASS |
| Plugin validation | PASS |
| Drama Plugin pytest | `74 passed` |
| Drama Plugin strict mypy | `Success: no issues found in 34 source files` |
| Drama MCP Service pytest | `13 passed` |
| Tool count / Skill count | `44 / 8` |
| `git diff --check` | PASS |

pytest 首轮曾受 shell 中无效 `socks://` 代理环境影响；只在测试进程清除代理后全量通过，没有因此修改 HTTP Provider 源码。

## 9. 修改文件

MODIFIED：

```text
plugin/.codex-plugin/plugin.json
plugin/README.md
plugin/skills/shot-production/SKILL.md
plugin/skills/shot-production/skill.yaml
plugin/skills/shot-production/agents/openai.yaml
plugin/tests/test_plugin.py
plugin/tests/test_skills.py
```

ADDED：

```text
plugin/skills/shot-production/references/visual-provider.md
plugin/docs/visual-provider-host-integration.md
plugin/docs/reports/22-Batch5.0.1-Visual-Provider-Integration-Contract-执行报告.md
```

既有未跟踪的 Batch 5 报告/artifact 被保留，未改动。Java 仓库既有 `application.yml` 修改也未触碰。

## 10. 八个核心问题

1. **`comfy-cloud` 是否写入 Drama Plugin `.mcp.json`？** NO。`.mcp.json` 只管理 bundled `drama-tools`；Comfy 是 Host 外部、条件式视觉能力。
2. **如何表达 Visual Provider 需求而不绑定 Codex？** Skill Core 用五个语义 capability 与输入/输出 handoff 表达；Codex 只在 `agents/openai.yaml` 绑定当前实现。
3. **是否复制 Comfy Tool Schema？** NO。没有 schema 文件；runtime MCP server 是唯一真源。
4. **维护哪些 mapping？** template discover、input upload、image generate、job wait、output fetch，对应当前五组 Comfy Tool 名称。
5. **0/1/2/3 策略在哪里？** 平台中立的 `shot-production/references/visual-provider.md`；具体模板偏好在 Host integration 文档。
6. **Qwen/Flux 名称是什么？** 当前 verified provider implementation preference，不是稳定 Drama business contract。
7. **Comfy 不可用时什么仍工作？** Research、Work、Script、Episode、Scene、Shot、Context、非视觉 planning/design 与 Drama 长期记忆读取；只阻断图片/视频执行。
8. **Batch 5.1 能否只写业务目标？** YES。Scenario B 已证明不列 Provider Tool 名称也能自动形成 Drama → Visual Provider → Review → Drama Media 完整编排。

## 11. 已知风险与下一步

- Comfy OAuth 曾出现 refresh-token reuse；官方重新登录已恢复。Host 应继续管理登录态，Plugin 不管理凭据。
- 当前模板偏好可能随 Provider 模板可用性变化；运行时应只在偏好不可用/不适配时做最小官方模板发现。
- 本批验证编排与边界，不重复 Batch 5 付费生成质量。

建议进入 Batch 5.1，并让任务 Prompt 只描述业务目标与生产范围，用实际多 Shot 生产验证本批已固化的自主编排。

## 12. 统一验收结论

```text
PLUGIN_STRUCTURE_AUDIT = PASS

DRAMA_MCP_BOUNDARY = PASS
VISUAL_PROVIDER_BOUNDARY = PASS

COMFY_AS_BUNDLED_DRAMA_MCP = NO
COMFY_IN_PLUGIN_MCP_JSON = NO

VISUAL_CAPABILITY_CONTRACT = PASS
COMFY_TOOL_CAPABILITY_MAPPING = PASS
COMFY_TOOL_SCHEMA_DUPLICATED = NO

REFERENCE_COUNT_POLICY = PASS
VERIFIED_TEMPLATE_PREFERENCES = PASS

DRAMA_MEDIA_TO_VISUAL_PROVIDER_RULE = PASS
VISUAL_OUTPUT_TO_DRAMA_MEDIA_RULE = PASS

RUNTIME_PREFLIGHT = PASS
VISUAL_PROVIDER_OPTIONAL_DEPENDENCY = PASS

NON_VISUAL_WITHOUT_COMFY = PASS
VISUAL_SKILL_ORCHESTRATION = PASS

CODEX_HARD_DEPENDENCY_IN_SKILL_CORE = NO
COMFY_HARD_DEPENDENCY_IN_DOMAIN = NO

DRAMA_MCP_CONTRACT_CHANGED = NO
JAVA_CONTRACT_CHANGED = NO
DATABASE_CHANGED = NO

NEW_PROVIDER_FRAMEWORK_INTRODUCED = NO
DYNAMIC_WORKFLOW_INTRODUCED = NO

REGRESSION = PASS

BATCH_5_0_1 = PASS
```
