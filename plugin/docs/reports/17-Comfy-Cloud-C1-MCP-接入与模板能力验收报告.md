# Batch C1 — Comfy Cloud MCP 接入与模板能力验收报告

执行日期：2026-08-15（Asia/Shanghai）

## 1. 执行摘要

本批在不修改 Drama Plugin 核心业务逻辑、不接入 Java Service、不创建 Saved Workflow、不中途进入正式视觉生产的边界内，完成了 Comfy Cloud MCP 的 Host 注册、OAuth 认证、工具发现和三类官方模板审计。

Comfy Cloud MCP 已通过正常 Codex MCP 注册流程接入官方端点 `https://cloud.comfy.org/mcp`。服务端 `get_server_info` 返回生产环境 `comfyui-cloud` v0.39.1、`authenticated (OAuth)`、40 个工具。原有 `drama-tools` 仍保持启用，Drama 链路配置未被替换。

三类生产原语均找到了官方候选模板：

- TEXT_TO_IMAGE：官方模板可直接满足，并完成一次真实生成、等待、取回和本地下载。
- REFERENCE_TO_IMAGE：官方 Mage-Flow-Edit Turbo 模板在 workflow 结构上存在 3 个独立参考图输入，但当前 `get_template_schema` / `slot_overrides` 映射发生整体错位。单参考图可通过官方支持的 `input_overrides` 路径运行并完成下载；“最多 3 张参考图可稳定通过 MCP 运行”尚未被证明，因此不将其写成 PASS。
- START_END_TO_VIDEO：官方 Seedance 2.0 模板明确具备独立 first/last frame 输入；两张测试图均已上传，但约 319 credits 的真实运行在当前非交互 Host 确认流程中返回 `Cancelled — no credits were spent`，没有创建 job。

因此，接入、认证、工具发现和模板结构审计已通过；但 3 图稳定运行路径与首尾帧视频实跑仍有明确阻断，本批统一结论为 `BLOCKED`，不建议直接进入正式 Drama 视觉生产。

## 2. 本批边界

本批实际执行范围：

- Codex Host 增量注册 Comfy Cloud MCP；
- OAuth 认证；
- MCP 服务器与工具发现；
- 官方模板搜索、workflow 与 schema 审计；
- 条件允许时的最小真实生成；
- 输出下载与文件校验。

未执行：

- Drama Plugin tool contract 修改；
- Drama Plugin 业务代码修改；
- Java Service 或数据库接入；
- Saved Workflow 创建；
- 自定义动态多图 Workflow；
- 正式资产生产。

## 3. 接入配置结果

| 项目 | 结果 |
| --- | --- |
| MCP 名称 | `comfy-cloud` |
| 官方地址 | `https://cloud.comfy.org/mcp` |
| Transport | Streamable HTTP |
| Codex 配置位置 | `/home/ubuntu/.codex/config.toml` |
| 配置文件权限 | `0600` |
| 注册方式 | `codex mcp add comfy-cloud --url https://cloud.comfy.org/mcp` |
| 原 Drama MCP | `drama-tools -> http://127.0.0.1:8765/mcp`，仍为 enabled |
| API Key | 未使用；执行环境中 `COMFY_API_KEY` 不存在 |
| 仓库密钥 | 无 |

注册后 `codex mcp list` 同时显示：

```text
comfy-cloud  https://cloud.comfy.org/mcp  enabled
drama-tools  http://127.0.0.1:8765/mcp    enabled
```

Codex 远程 HTTP MCP 与 OAuth 配置机制参考官方说明：<https://learn.chatgpt.com/docs/extend/mcp?surface=cli>。

## 4. 认证结果

优先认证路径为 OAuth，实际注册时 Host 检测到 OAuth 支持并启动授权流程，随后返回：

```text
Successfully logged in.
```

真实 MCP 返回：

```json
{
  "server_name": "comfyui-cloud",
  "server_identity": "Comfy Cloud hosted MCP server (https://cloud.comfy.org/mcp)",
  "environment": "production",
  "host": "https://cloud.comfy.org",
  "version": "0.39.1",
  "auth_state": "authenticated (OAuth)",
  "tool_count": 40
}
```

本次授权使用了当前 Host 已有登录态，没有观察到需要用户手动操作浏览器的步骤。新环境若没有 Comfy 登录态，正常 OAuth 流程仍可能要求在浏览器确认。X-API-Key 回退路径未使用；若未来必须使用，应仅通过环境变量注入，不得写入仓库。

## 5. 工具发现结果

| 必需工具 | 真实调用 | 结果证据 | 结论 |
| --- | --- | --- | --- |
| `get_server_info` | 是 | production、v0.39.1、OAuth、40 tools | PASS |
| `search_templates` | 是 | 通用 image 查询返回 1/431；专项 T2I 查询返回官方候选 | PASS |
| `search_models` | 是 | `flux` 查询返回 1/202，示例 `bfl/flux-pro-1.1-ultra` | PASS |
| `search_nodes` | 是 | `image` 查询返回 1/925，示例 core `ImageScale` | PASS |

当前 Host 还发现了本批所需完整链路工具：

```text
get_template
get_template_schema
upload_file
estimate_credits
run_template
wait_for_job
get_output
```

首次新会话初始化期间观察到间歇性 HTTP 502，以及 SSE GET/DELETE 400 日志；Host 重试后只读搜索与生成链路均可成功建立。该现象属于连接稳定性风险，不是 OAuth 拒绝。

## 6. 模板能力审计

### 6.1 TEXT_TO_IMAGE

搜索词：`text to image`、`Text to Image`。

候选：

- `api_google_nano_banana2_text_to_image` — Nano Banana 2: Text to Image；
- `image_krea2_turbo_t2i` — Krea-2: Text to Image；
- `image_mage_flow_t2i_int8` — Mage-Flow: Text to Image。

选定模板：`api_google_nano_banana2_text_to_image`。

| 能力 | 真实结果 |
| --- | --- |
| 用途 | 文本生成单张图片 |
| 文件输入 | 不要求 |
| 主要运行参数 | node 24 `prompt`、模型、比例、分辨率、seed 等 |
| 图片参考槽 | 不作为本原语要求；workflow 有未连接的可选 image port，但 schema 未将其暴露为稳定 slot |
| 输出 | `IMAGE -> SaveImage` |
| 适配结论 | 适合作为 TEXT_TO_IMAGE 候选 |

`get_template_schema` 返回 `slots: []`，并明确说明应使用 `run_template.input_overrides` 按节点覆盖。真实运行使用 node 24 的 `prompt`，成功完成。

### 6.2 REFERENCE_TO_IMAGE

搜索词：`reference to image`、`multiple reference images image edit`。

候选：

- `image_mage_flow_edit_turbo_int8` — Mage-Flow-Edit Turbo: Image Edit；
- `image_mage_flow_edit_int8` — Mage-Flow-Edit: Image Edit；
- `image_krea2_turbo_int8_image_style_reference` — Krea-2 Int8: Image Style Reference。

选定模板：`image_mage_flow_edit_turbo_int8`。

模板搜索描述声明该模板接受 1–3 张参考图并输出编辑图片。`get_template` 进一步确认子图存在三个不同的 IMAGE 输入：

```text
images.image_1
images.image_2
images.image_3
```

它们是三个独立地址，不是 batch，也不是同一输入的重复引用。内部 `TextEncodeMageFlowEdit` 也分别连接 `images.image_1`、`images.image_2`、`images.image_3`。

但是 `get_template_schema` 的地址和值发生整体错位：

| schema 地址 | 声明类型 | schema 返回 default | 纯转换探针的实际落点 |
| --- | --- | --- | --- |
| `12.images.image_1` | IMAGE | `Remove all hot air balloons` | 内部 node 5 的 prompt |
| `12.prompt` | STRING | 一个 seed 整数 | 内部 node 6 的 seed |
| `12.seed` | INT | boolean | 后续输入继续错位 |

真实失败证据：用 `slot_overrides` 传 `12.prompt=<字符串>` 时，运行前校验返回：

```text
seed: expected INT, got string
```

该次调用没有创建 job，也没有产生生成费用。之后只读调用 `apply_slots` 证明错位发生在子图 slot 到 proxyWidgets 的映射层；没有修改或保存 workflow。

官方 `input_overrides` 路径可绕开错误 slot 映射：

```json
{
  "7": {"image": "<uploaded filename>"},
  "5": {"prompt": "<edit instruction>"}
}
```

服务端将唯一子图内部 node 5 重映射为展开执行节点 `12:5`。单参考图真实运行成功并输出图片。

结论分层：

- 官方模板结构支持 1/2/3 个独立参考输入：是；
- 单参考图通过现有 MCP 执行链运行：是；
- `get_template_schema + slot_overrides` 可稳定驱动最多 3 图：否，当前映射错误；
- 三张独立参考图的真实运行验收：未执行，也不能从单图成功推断；
- `REFERENCE_TO_IMAGE_UP_TO_3_SUPPORTED`：FAIL（稳定运行证据不足且存在真实映射 bug）。

当前不应为此构建复杂动态多图 workaround。后续应优先等待/修复 Comfy Cloud 模板 schema 映射；若生产必须固定 3 图且官方模板问题持续，再评估一个精简 Saved Workflow。

### 6.3 START_END_TO_VIDEO

搜索词：`start end frame video`、`first last frame to video`。

候选：

- `api_seedance2_0_flf2v` — Seedance2.0: First-Last-Frame to Video；
- `api_seedance2_5_flf2v` — Seedance 2.5: FLF2V；
- `api_kling_v3_flf2v` — Kling 3.0: First Last Frame to Video；
- `video_ltx2_5_flf2v` — LTX-2.5: FLF2V。

选定模板：`api_seedance2_0_flf2v`。

`get_template` 真实确认：

- node 3 `LoadImage` 连接 `ByteDance2FirstLastFrameNode.first_frame`；
- node 4 `LoadImage` 连接 `ByteDance2FirstLastFrameNode.last_frame`；
- node 1 输出 `VIDEO` 并连接 `SaveVideo`；
- 两张图是两个独立输入，不是单图复用。

`get_template_schema` 的 `slots` 为空，但 `nodes` 明确给出 `3.image` 和 `4.image`，可通过 `input_overrides` 覆盖。模板结构完全匹配 START_END_TO_VIDEO 原语。

## 7. 成本与运行权限检查

`get_usage_report` 可读取当前 workspace 最近一个月真实用量，说明 OAuth 账户具备用量读取权限；本批不在报告中展开账户级明细。`estimate_credits` 返回：

| 模板 | 估算 |
| --- | --- |
| `api_google_nano_banana2_text_to_image` | 约 18 credits / image |
| `image_mage_flow_edit_turbo_int8` | 0 paid API credits；GPU/队列/存储未包含 |
| `api_seedance2_0_flf2v` | 默认约 319 credits |

估算工具不能证明实时余额。两次图片生成实际成功，说明账户并非整体无生成权限；视频调用返回取消则说明当前 Host 对该高成本运行仍有未完成的确认门槛。

## 8. 最小真实生成验收

### 8.1 文生图

| 项目 | 结果 |
| --- | --- |
| 模板 | `api_google_nano_banana2_text_to_image` |
| `run_template` | PASS |
| job ID | `757ac149-43d3-4679-9bd5-84953b0a0975` |
| `wait_for_job` | `completed` |
| `get_output` | PASS |
| 本地文件 | `artifacts/comfy-cloud-c1/text-to-image.png` |
| 文件规格 | PNG，1024×1024，RGBA，1,698,806 bytes |
| SHA-256 | `f3520c3ec6c5ac05c8ccbb89498eb973ec85758d5d28bc12c652bd6f8acb046c` |

视觉复核：生成结果为居中构图、暗背景、未点亮的古代青铜灯，无文字，符合测试提示。

### 8.2 参考图生图

| 项目 | 结果 |
| --- | --- |
| 模板 | `image_mage_flow_edit_turbo_int8` |
| 输入 | 上述文生图 PoC 输出，一张参考图 |
| 首次 slot 调用 | 运行前校验失败；未创建 job、未产生费用 |
| 安全重试 | 使用已由只读探针证明的 `input_overrides` |
| `run_template` | PASS |
| job ID | `57cd79c7-9dcc-4f59-8d6b-bc4926526e50` |
| `wait_for_job` | `completed` |
| `get_output` | PASS |
| 本地文件 | `artifacts/comfy-cloud-c1/reference-to-image.png` |
| 文件规格 | PNG，1024×1024，RGB，1,209,865 bytes |
| SHA-256 | `efcf98f79bfc6aee44871b687664ef48a0649dc6352287b1e27440622cec2a65` |

视觉复核：输出保持青铜灯主体与暗背景构图，并在灯体内部增加暖光，符合编辑指令。

运行警告：内部 node 5 被重映射为展开节点 `12:5`，执行覆盖不会反映到可重新打开的 UI workflow；顶层 LoadImage 还报告一个额外 widget 未映射。这些警告不影响本次输出，但不应在正式生产前忽略。

### 8.3 首尾帧视频

两张 PoC 图片均成功上传，并使用以下已验证节点：

```text
3.image = start frame
4.image = end frame
1.model.prompt = transition instruction
```

`run_template(confirm=true)` 返回：

```text
Cancelled — no credits were spent.
```

没有 job ID，因而不能调用 `wait_for_job` 或 `get_output`。本批没有重复提交，也没有绕过高成本确认机制。

结论：`REAL_START_END_VIDEO_RUN = BLOCKED`。阻断层是当前非交互 Host 的高成本运行确认/授权门槛，不是模板缺失、输入槽缺失或 OAuth 整体失败。

## 9. 输出下载 E2E

文生图与参考图生图均按以下真实链路完成：

```text
run_template
-> wait_for_job
-> get_output
-> 临时下载 URL
-> curl 下载到 workspace
-> file / size / SHA-256 校验
```

因此图片输出下载端到端为 PASS。视频没有输出可下载，状态随视频运行记为 BLOCKED；统一 `OUTPUT_DOWNLOAD_E2E` 以已经成功完成的两条真实输出链路记为 PASS，并在状态中单列视频阻断，不掩盖缺失的视频下载证据。

## 10. 阻断点与风险

1. **三图稳定运行未证明**：模板结构有 3 个独立输入，但 schema/slot 映射错位是可复现 bug；不能把结构能力写成稳定生产能力。
2. **视频高成本确认被取消**：约 319 credits 的模板没有创建 job；需要在支持交互确认的 Host 会话中明确批准，或由账户管理员确认策略与余额后再验收。
3. **连接初始化抖动**：多次新 Host 会话出现可重试 HTTP 502、SSE GET/DELETE 400；业务调用最终可成功，但需纳入集成稳定性观察。
4. **模板 schema 质量**：部分 default 与声明类型明显不一致，生产集成不能盲信 default；必须将 schema、模板版本和真实运行证据一起校验。
5. **临时下载 URL**：`get_output` 返回的 URL 约 5 分钟过期，生产侧以后需要在取得结果后立即下载或刷新链接。

## 11. 是否建议进入下一批

不建议直接进入正式 Drama 视觉生产批次。

可以进入一个严格限界的“Comfy Cloud 阻断收口”小批次，仅处理：

1. 在支持显式交互确认的 Host 中完成一次 Seedance FLF2V 运行与视频下载；
2. 复测 Comfy Cloud 是否已修复 Mage-Flow-Edit 的 schema/slot 映射；若未修复，只评估是否需要一个固定 3 图、无动态抽象的 Saved Workflow。

在上述两点完成前，不修改 Drama Plugin 协议，也不把 Comfy 模板细节接入 Java Service。

## 12. 变更与未变更证明

仓库新增：

```text
plugin/docs/reports/08-Comfy-Cloud-MCP-接入与模板能力验收报告.md
plugin/docs/reports/artifacts/comfy-cloud-c1/text-to-image.png
plugin/docs/reports/artifacts/comfy-cloud-c1/reference-to-image.png
```

Host 全局配置发生的预期变更：

```text
/home/ubuntu/.codex/config.toml
新增 comfy-cloud MCP 注册与 OAuth 凭据引用；文件权限 0600。
```

未修改：

```text
Drama Plugin core business logic
Drama Plugin tool contract
Drama MCP Service code
Java Service
Database
Saved Workflow
```

本批没有源码变更，因此没有为了形式而运行无关的 pytest/Java build。回归验证由真实 MCP 工具调用、两条生成 E2E、下载文件校验、`codex mcp list/get` 与仓库状态检查组成。

## 13. 统一验收结论

```text
COMFY_CLOUD_MCP_CONNECT = PASS
COMFY_CLOUD_AUTH = PASS
COMFY_CLOUD_TOOL_DISCOVERY = PASS

TEXT_TO_IMAGE_TEMPLATE_FOUND = PASS
REFERENCE_TO_IMAGE_TEMPLATE_FOUND = PASS
REFERENCE_TO_IMAGE_UP_TO_3_SUPPORTED = FAIL
START_END_TO_VIDEO_TEMPLATE_FOUND = PASS

REAL_TEXT_TO_IMAGE_RUN = PASS
REAL_REFERENCE_IMAGE_RUN = PASS
REAL_START_END_VIDEO_RUN = BLOCKED
OUTPUT_DOWNLOAD_E2E = PASS

BATCH_C1 = BLOCKED
```

判定说明：

- `REFERENCE_TO_IMAGE_UP_TO_3_SUPPORTED = FAIL` 不代表模板没有 3 个输入，而是当前 MCP 的 schema/slot 运行路径不稳定，且没有完成三图真实运行，不能满足“稳定支持”的验收措辞。
- `BATCH_C1 = BLOCKED` 不代表 MCP 接入失败；接入、OAuth、工具发现、模板发现和两类图片生成均已通过。阻断来自三图稳定性与首尾帧视频真实运行尚未闭环。
