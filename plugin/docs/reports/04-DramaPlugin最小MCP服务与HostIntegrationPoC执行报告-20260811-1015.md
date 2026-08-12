# Drama Plugin 最小 MCP 服务与 Host Integration PoC 执行报告

执行时间：2026-08-11 10:15（Asia/Shanghai，UTC+08:00）  
批次编号：04

## 1. 执行摘要

| 验证对象 | 状态 | 结论 |
|---|---|---|
| MCP SERVER | PASS | FastAPI 启动、`/health`、真实 Streamable HTTP MCP `tools/list` 与 `tools/call` 全部通过。 |
| PLUGIN PACKAGE | PASS | Plugin manifest 校验通过，本地 marketplace 可发现并安装，缓存副本包含本次 MCP/Skill dependency 配置。 |
| HOST INTEGRATION | PASS | 新 Codex CLI Host 读取安装缓存中的 `shot-generation` Skill，真实调用 `drama-context/context.build_context`，取得 structured Context 并完成下一步判断。 |

最终结论：**PASS**。

## 2. 最终目录结构

```text
historical_plugin/
├── drama-plugin/
│   ├── .codex-plugin/plugin.json
│   ├── .mcp.json
│   ├── skills/shot-generation/agents/openai.yaml
│   └── docs/reports/
│       └── 04-DramaPlugin最小MCP服务与HostIntegrationPoC执行报告-20260811-1015.md
├── drama-mcp-poc/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/main.py
│   └── tests/test_server.py
└── drama-local-marketplace/
    ├── .agents/plugins/marketplace.json
    └── plugins/drama-plugin -> ../../drama-plugin
```

工作区顶层 `.agents/` 被 sandbox 的显式只读规则阻止创建。因此使用仅含一个 manifest 和一个源码符号链接的 `drama-local-marketplace`；没有复制 `drama-plugin`，source 最终解析到当前真实工程。

## 3. drama-mcp-poc 文件清单

| 文件 | 存在理由 |
|---|---|
| `pyproject.toml` | Python 3.12 约束、3 个运行依赖、1 个开发依赖及 pytest 配置。 |
| `src/main.py` | FastAPI、MCP ASGI/lifespan、health 与唯一 Stub Tool 的全部实现。 |
| `tests/test_server.py` | 启动真实 uvicorn，并用官方 MCP Client 验证 health、list、call。 |
| `README.md` | 最短安装、启动、地址、测试和未来 Java 替换说明。 |

未增加 Docker、配置框架、业务分层、数据库、鉴权、Agent Loop 或 LLM 调用。

## 4. 直接依赖清单

实际验证环境为 Python 3.12.13。

| 类别 | 依赖声明 | 实际版本 | 理由 |
|---|---|---|---|
| 运行 | `fastapi>=0.116,<1` | 0.141.1 | 提供 `/health` 与顶层 ASGI Host。 |
| 运行 | `mcp==2.0.0` | 2.0.0 stable | 官方 MCP Python SDK，负责协议、schema、session 与 Streamable HTTP。 |
| 运行 | `uvicorn>=0.35,<1` | 0.52.1 | 启动 ASGI 服务。 |
| 开发 | `pytest>=8,<9` | 8.4.2 | 最少自动化验证。 |
| 构建 | `hatchling>=1.27,<2` | 构建隔离使用 | `pyproject.toml` 的轻量 build backend，不是服务运行依赖。 |

未直接声明或使用其他业务依赖。MCP SDK 自身的传递依赖不属于本工程直接依赖。

## 5. MCP Server 实现

- `GET /health` 返回 `200` 与 `{"status":"ok","service":"drama-mcp-poc"}`。
- `/mcp` 是官方 MCP SDK 2.0.0 提供的 Streamable HTTP ASGI app。
- FastAPI 顶层 lifespan 显式进入 `mcp.session_manager.run()`；不是只挂一个空路由。
- MCP 只注册一个 Tool：`context.build_context`。
- Tool 仅返回固定 Mock Context，不访问数据库、Plugin Core 或其他 HTTP 服务。

实现依据为官方 MCP Python SDK v2 文档；v2.0.0 是 2026-08-11 PyPI 当前 stable，未使用 pre-release。

## 6. MCP Tool Contract

实际 Tool name：`context.build_context`，无需 transport mapping。

实际 `tools/list` input schema：

```json
{
  "type": "object",
  "properties": {
    "scope": {"const": "SHOT", "type": "string"},
    "resourceId": {"type": "string"},
    "purpose": {"const": "SHOT_VIDEO_GENERATION", "type": "string"}
  },
  "required": ["scope", "resourceId", "purpose"]
}
```

实际输出示例：

```json
{
  "scope": "SHOT",
  "version": 1,
  "shot": {"id": "shot-1", "description": "Host Integration PoC shot"},
  "entities": {"characters": []},
  "assets": {"effective": []},
  "generation": {"state": null}
}
```

## 7. MCP 独立验证

使用固定服务地址 `http://127.0.0.1:8765/mcp` 和官方 `mcp.Client` 2.0.0：

| 验证 | 真实结果 |
|---|---|
| FastAPI startup | uvicorn startup complete，PASS |
| health | HTTP 200，payload 精确匹配，PASS |
| MCP connect | 官方 Client 成功连接，PASS |
| tools/list | 只返回 `context.build_context`，PASS |
| tools/call | 输入 `SHOT/shot-1/SHOT_VIDEO_GENERATION`，PASS |
| output | `scope=SHOT`、`shot.id=shot-1`，PASS |

没有手写 JSON-RPC、initialize、session 或 Streamable HTTP framing，也没有用普通 POST 模拟 MCP Client。

## 8. Drama Plugin 修改清单

- `../../.codex-plugin/plugin.json`：增加 `"mcpServers": "./.mcp.json"`；使用 cachebuster 将版本改为 `0.1.0+codex.20260811020915`。
- `.mcp.json`：新增一个 `drama-context` HTTP MCP Server 配置。
- `skills/shot-generation/agents/openai.yaml`：只为该 Skill 增加一个 MCP dependency；同时让既有 default prompt 按当前规范显式写为 `$shot-generation`。
- 官方 bundled `validate_plugin.py`：`Plugin validation passed`。

Plugin Core 的 Python runtime、ToolRegistry、Provider 和 Contract 实现均未修改。

## 9. Skill 修改情况

- `skills/shot-generation/SKILL.md`：未修改。
- `skills/shot-generation/skill.yaml`：未修改。
- `skills/shot-generation/agents/openai.yaml`：仅增加本次 MCP dependency 与规范化 default prompt。
- 其余 7 个 Skill：完全未修改；`git diff --name-only -- skills` 只显示 shot-generation 的 `agents/openai.yaml`。

## 10. MCP 配置方式

Codex 实际看到：

```text
server name: drama-context
transport:   streamable_http（Plugin .mcp.json 中 type=http）
URL:         http://127.0.0.1:8765/mcp
status:      enabled
auth:        Unknown（本地无鉴权 PoC）
```

`codex mcp list` 已显示该 server；没有 command、stdio 或 Plugin 内置 Python 进程配置。

## 11. Plugin 本地安装 / Marketplace 验证

- Marketplace name：`drama-local`。
- Marketplace root：`historical_plugin/drama-local-marketplace`。
- Source：`./plugins/drama-plugin`，该路径为指向真实 `../../drama-plugin` 的符号链接，不是副本。
- 注册命令：`codex plugin marketplace add <absolute-marketplace-root>`。
- 安装命令：`codex plugin add drama-plugin@drama-local`。
- `codex plugin list`：`installed, enabled`，版本 `0.1.0+codex.20260811020915`。
- 安装缓存：`~/.codex/plugins/cache/drama-local/drama-plugin/0.1.0+codex.20260811020915`。
- 已逐项读取缓存内 `.mcp.json` 与 shot-generation `agents/openai.yaml`，确认是本次配置。
- Host 验证使用新的 `codex exec --ephemeral` 进程，不依赖当前桌面会话热加载。

## 12. Host Integration 真实执行

测试 Prompt：

```text
使用 shot-generation Skill 处理 shot-1。

本次只执行“获取当前镜头 Context”这一步。
不要创建资产，不要生成图片，不要创建 Generation Plan。

获取 Context 后告诉我：
1. 当前 scope；
2. 当前 shot id；
3. 当前是否存在 effective assets；
4. 下一步理论上应该做什么。

不要执行下一步。
```

真实行为：

- Codex 从安装缓存读取 `skills/shot-generation/SKILL.md`：是。
- Codex 发现 MCP Server `drama-context`：是。
- Codex 真实调用 `context.build_context`：是。
- Tool 输入：`{"purpose":"SHOT_VIDEO_GENERATION","resourceId":"shot-1","scope":"SHOT"}`。
- Tool 返回：固定 structured Context，`scope=SHOT`、`shot.id=shot-1`、`assets.effective=[]`、`generation.state=null`。
- Codex 最终判断：scope 为 SHOT；shot id 为 shot-1；无 effective assets；理论下一步是确认 generationTarget/输入充分性并创建 Generation Plan，必要时先补齐有效资产。
- Codex 明确未执行下一步，未创建资产、图片或 Generation Plan。

第一次非交互 Host 尝试在 MCP 审批点产生了真实 call trace，但因 stdin 无人工审批而显示 `user cancelled MCP tool call`；没有将其计为成功。第二次使用 CLI 官方 `--approve-for-me` 模式完成调用与结果判断。

## 13. Host Integration 证据

Codex JSONL trace 核心记录：

```json
{
  "type": "item.completed",
  "item": {
    "type": "mcp_tool_call",
    "server": "drama-context",
    "tool": "context.build_context",
    "arguments": {
      "purpose": "SHOT_VIDEO_GENERATION",
      "resourceId": "shot-1",
      "scope": "SHOT"
    },
    "status": "completed",
    "error": null,
    "result": {
      "structured_content": {
        "scope": "SHOT",
        "shot": {"id": "shot-1"},
        "assets": {"effective": []},
        "generation": {"state": null}
      }
    }
  }
}
```

同一时段 MCP Server 日志：

```text
POST /mcp 200 OK
tool=context.build_context scope=SHOT resourceId=shot-1 purpose=SHOT_VIDEO_GENERATION
DELETE /mcp 200 OK
```

该证据同时覆盖 Host trace 与独立 Server handler 日志，不是单元测试、Inspector 或 Plugin Core `ToolRegistry.invoke()` 的替代证据。

## 14. drama-mcp-poc pytest

最终命令：`.venv/bin/python -m pytest -ra`

```text
collected: 2
passed:    2
failed:    0
duration:  0.62s
```

两个测试分别覆盖 health，以及真实 MCP Client 的 list+call。

## 15. drama-plugin 回归

| 命令 | 结果 |
|---|---|
| `.venv/bin/python -m pytest -ra` | 22 collected，22 passed，0 failed |
| `.venv/bin/python -m mypy src/drama_plugin` | Success，34 source files，0 issues |
| `.venv/bin/python examples/build_shot_context.py` | PASS；Plugin、shot-generation、SHOT Context、资产与 DRAFT state 正常输出 |

## 16. 两工程依赖检查

使用 `rg` 扫描源码、测试、pyproject 与 README：

```text
drama-plugin -> drama-mcp-poc = NO
drama-mcp-poc -> drama-plugin = NO
```

`drama-mcp-poc` 未加入 `../drama-plugin` 到 Python path，未执行 `pip install -e ../drama-plugin`。两工程唯一运行关系是 MCP protocol。

## 17. 是否出现架构越界

| 检查项 | 结论 |
|---|---|
| Plugin 是否实现 MCP Client | NO；只声明 Host 配置/dependency。 |
| Plugin 是否实现 MCP Server | NO。 |
| MCP PoC 是否 import Plugin | NO。 |
| 是否新增 Agent Loop | NO；Agent Loop 属于 Codex Host。 |
| 是否新增真实业务 | NO；Tool 为固定 Stub。 |
| Host 是否调用 Python DramaPlugin/ToolRegistry | NO。 |
| 是否扩展其他 Drama Tools | NO；MCP 只有一个 Tool。 |

## 18. PoC 最终结论

**PASS**

已证明完整链路真实发生：

```text
Codex Host
→ 安装缓存中的 Drama Plugin
→ shot-generation Skill
→ Host MCP Client
→ 外部 drama-mcp-poc /mcp
→ context.build_context
→ structured SHOT Context
→ Codex 下一步判断后停止
```

MCP Server 与 Drama Skill 之间只有稳定 Tool name、输入和输出协议关系。未来将 Python PoC 整体替换为实现同一 MCP Contract 的 Java Server 时，不要求因服务实现语言变化而重写 Skill。

## 19. 下一步建议

1. 下一阶段将同一 `context.build_context` MCP Contract 在 Java Server 中实现，并复用本报告 Prompt 做替换验证。
2. 为本地开发补一个不进入 Plugin 的一键启动说明或脚本，仅在重复联调出现实际需要时再做。
3. 在进入更多 Tool 前先固定 Java/Host 对 Tool error 与 schema compatibility 的验收方式。
