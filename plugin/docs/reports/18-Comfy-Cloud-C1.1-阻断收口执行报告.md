# Batch C1.1 — Comfy Cloud 阻断收口执行报告

执行日期：2026-08-15（Asia/Shanghai）

## 1. 执行摘要

本批严格继承 Batch C1 已通过的 MCP 接入、OAuth、工具发现、文生图、单参考图和图片下载结果，只处理多参考图与首尾帧视频两个遗留问题。

实际结果：

- 2 图参考生成：两张图片分别上传成功，真实 job 已创建；但 `TextEncodeMageFlowEdit` 收到上传 filename 字符串而不是 IMAGE tensor，执行失败，无 output，判定 FAIL。
- 3 图参考生成：2 图已证明当前纯 `input_overrides` 路径不能把未连接 IMAGE 输入的 filename 转换为 tensor；阶段 A 没有生成可作为第三张输入的新图片，工作区也没有第三张其他图片。为避免重复提交已知同因失败的 job，本阶段判定 BLOCKED。
- 首尾帧视频：官方模板、两个独立输入和约 319 credits 成本均已确认；非交互 Host 强制 `approval: never` 并取消 MCP 调用，正式 `codex -a on-request` TUI 又无法从当前自动化执行通道获得可写终端 session，因此没有 job。判定 `BLOCKED_BY_HOST_CONFIRMATION`，不是 Comfy 视频能力失败。

当前仍有生产级阻断：官方 Mage-Flow 模板在不使用错误 `slot_overrides`、不修改 graph 的约束下只有一个顶层 LoadImage，无法以 filename 驱动第二、第三个 IMAGE tensor；视频真实运行仍缺正式 Host 费用确认。

## 2. C1 继承基线

以下结果直接继承 C1，不重复执行：

```text
COMFY_CLOUD_MCP_CONNECT = PASS
COMFY_CLOUD_AUTH = PASS
COMFY_CLOUD_TOOL_DISCOVERY = PASS
TEXT_TO_IMAGE_TEMPLATE_FOUND = PASS
REAL_TEXT_TO_IMAGE_RUN = PASS
REFERENCE_IMAGE_1 = PASS
START_END_TO_VIDEO_TEMPLATE_FOUND = PASS
C1 IMAGE get_output -> signed URL -> local download = PASS
```

本批仅做轻量配置回归：

```text
comfy-cloud  https://cloud.comfy.org/mcp  enabled
drama-tools  http://127.0.0.1:8765/mcp    enabled
```

执行初期，Comfy OAuth refresh token 被服务端以 `invalid_grant: refresh token reuse detected` 拒绝。通过正常 `codex mcp login comfy-cloud` OAuth 流程刷新后恢复；没有改端点、没有使用 API Key、没有影响 `drama-tools`。

## 3. 输入文件基线

| 角色 | 本地路径 | 格式 | 尺寸 | Size | SHA-256 |
| --- | --- | --- | --- | ---: | --- |
| reference_1 / start | `plugin/docs/reports/artifacts/comfy-cloud-c1/text-to-image.png` | PNG RGBA | 1024×1024 | 1,698,806 bytes | `f3520c3ec6c5ac05c8ccbb89498eb973ec85758d5d28bc12c652bd6f8acb046c` |
| reference_2 / end | `plugin/docs/reports/artifacts/comfy-cloud-c1/reference-to-image.png` | PNG RGB | 1024×1024 | 1,209,865 bytes | `efcf98f79bfc6aee44871b687664ef48a0649dc6352287b1e27440622cec2a65` |

工作区除这两张 C1 产物外没有其他 PNG/JPEG/WebP。原计划将 2 图输出作为第三张独立参考图，但阶段 A 没有产出 output，因此没有伪造或复制第三张输入。

## 4. 实际节点映射复核

本批没有重新搜索模板，只对固定模板 `image_mage_flow_edit_turbo_int8` 调用一次只读 `get_template`。

真实 workflow：

```text
top-level node 7: LoadImage
  -> link 13
  -> subgraph instance 12.images.image_1

subgraph inner node 5: TextEncodeMageFlowEdit
  prompt         <- internal link 16
  images.image_1 <- internal link 27
  images.image_2 <- internal link 61, target slot 2
  images.image_3 <- internal link 62, target slot 3
```

因此三个 IMAGE 输入在 graph 结构上确实独立；问题不在“是否存在三个端口”，而在第二、第三个端口没有对应顶层 LoadImage，上传 filename 不能自动成为执行节点需要的 IMAGE tensor。

## 5. 2 图参考生成真实 E2E

### 5.1 上传结果

| 角色 | 本地路径 | Content-Type | Cloud filename | 结果 |
| --- | --- | --- | --- | --- |
| image_1 | `.../comfy-cloud-c1/text-to-image.png` | `image/png` | `0ee6e1d16bb8149a85dab5afd41086cd16448155d4eb55960d1a27a52d0ede36.png` | PASS |
| image_2 | `.../comfy-cloud-c1/reference-to-image.png` | `image/png` | `c516157d429f04ec7430fab3d3336740206a61aef64285b8fbcbd514d860787b.png` | PASS |

两次均使用官方 `upload_file` 获取单次上传 URL，并执行其原样 PUT 命令。

### 5.2 提交参数

未使用 `slot_overrides`。真实 `input_overrides`：

```json
{
  "7": {
    "image": "0ee6e1d16bb8149a85dab5afd41086cd16448155d4eb55960d1a27a52d0ede36.png"
  },
  "5": {
    "prompt": "Use the first image as the main bronze lamp composition and the second image as warm-light reference; produce one coherent bronze lamp image on a dark background.",
    "images.image_2": "c516157d429f04ec7430fab3d3336740206a61aef64285b8fbcbd514d860787b.png"
  }
}
```

服务端确认 inner node 5 自动重映射为执行节点 `12:5`。

### 5.3 Job 与错误

```text
template = image_mage_flow_edit_turbo_int8
job_id = 595d6798-db4b-40f0-9f29-8055ae7d256c
job_created = YES
job_status = error
error_code = execution.node
node_id = 12:5
node_type = TextEncodeMageFlowEdit
error_type = AttributeError
error_message = 'str' object has no attribute 'movedim'
get_output = no output; job.failed
credits_spent = UNKNOWN
```

根因：`input_overrides` 在 workflow 转换后直接设置执行节点输入。对 node 7 `LoadImage.image` 传 filename 是合法的，因为 LoadImage 会读取文件；对 `TextEncodeMageFlowEdit.images.image_2` 直接传 filename 时，该值保持 Python string，没有转换为 IMAGE tensor，随后在图像维度处理调用 `movedim` 时失败。

没有本地输出文件，因此 size、格式与 SHA-256 不存在。

```text
REFERENCE_IMAGE_2 = FAIL
```

## 6. 3 图参考生成

### 6.1 为什么没有重复提交已知失败 job

只读 `get_prompting_guide(topic="templates")` 明确说明：

- `input_overrides` 在转换后设置节点输入；
- 子图 instance/inner node ID 可重映射；
- 没有声明上传 filename 会转换为未连接端口的 IMAGE tensor。

2 图真实 job 已直接证明 filename 传入 `images.image_2` 后仍是 string。`images.image_3` 与 `images.image_2` 属于同一个 `TextEncodeMageFlowEdit` 的同类 IMAGE 端口，且同样没有 LoadImage 上游。重复提交三图只会重现同一错误，不会产生新能力证据。

此外，阶段 A 没有 output，工作区也没有第三张不同图片；不得复制同一个文件、拼图或 batch 冒充第三个独立参考输入。

因此：

```text
image_1 planned = node 7 LoadImage
image_2 planned = node 12:5 images.image_2, blocked by filename->tensor gap
image_3 planned = node 12:5 images.image_3, same gap
3-reference job_id = NONE
REFERENCE_IMAGE_3 = BLOCKED
```

这不是把未知写成支持。当前官方模板的三个结构端口存在，但官方模板 + 纯 `input_overrides` 不能在本批约束下稳定完成 2/3 图加载。

## 7. slot_overrides 已知问题

C1 已确认 `get_template_schema / slot_overrides` 的子图地址发生整体错位，例如 prompt 被映射为 seed。本批没有再次使用错误路径。

由于纯 `input_overrides` 又无法把第二、第三个上传 filename 转换为 IMAGE tensor，slot 问题当前仍直接阻断固定 2/3 图生产：

```text
SLOT_OVERRIDES_ISSUE = BLOCKING
```

它不影响 C1 已通过的单参考图路径，但影响“最多 3 张独立参考图”的正式原语。按任务边界，本批没有创建 Saved Workflow 或自定义 graph。

## 8. Start-End Frame 视频运行

### 8.1 模板、输入与成本

```text
template = api_seedance2_0_flf2v
start frame node = 3.image
end frame node = 4.image
prompt node = 1.model.prompt
start Cloud filename = 0ee6e1d16bb8149a85dab5afd41086cd16448155d4eb55960d1a27a52d0ede36.png
end Cloud filename = c516157d429f04ec7430fab3d3336740206a61aef64285b8fbcbd514d860787b.png
prompt = A static ancient bronze lamp gradually begins to glow warmly, locked camera, subtle light transition, no cuts.
```

真实 `estimate_credits`：

```text
paid node = ByteDance2FirstLastFrameNode, node 1
estimated credits = ~319
GPU / queue / storage = not included
```

### 8.2 正式确认结果

非交互 `codex exec` 会话实际显示：

```text
approval: never
mcp: comfy-cloud/run_template (failed)
user cancelled MCP tool call
```

两次参数级尝试均在提交前被取消，没有 job、没有 credits 消费。显式 config override 也没有改变 `codex exec` 的 `approval: never`。

随后启动官方交互模式：

```text
codex -a on-request --no-alt-screen ...
```

该 TUI 进入等待态，但当前自动化执行通道只返回 cell ID，没有可用于 `write_stdin` 的终端 session ID，无法把费用批准选择送回 Host。为避免悬挂或绕过确认，主动终止该未提交会话。

最终证据：

```text
HOST_CONFIRMATION = NOT_COMPLETED
BLOCKED_BY_HOST_CONFIRMATION
job_id = NONE
job_status = NOT_SUBMITTED
credits_spent = NO
output = NONE
local video = NONE
```

因此无法提供 duration、resolution、size、SHA-256 或 ffprobe 结果。

```text
REAL_START_END_VIDEO_RUN = BLOCKED
VIDEO_OUTPUT_DOWNLOAD_E2E = BLOCKED
```

该状态不得解释为 `COMFY_VIDEO_CAPABILITY_FAIL`：模板结构、文件上传和成本估算均正常，阻断发生在当前 Host 费用确认交互通道。

## 9. 输出下载结论

C1 的单参考图与文生图下载仍保持 PASS，但本批要求的 2 图、3 图没有图片 output：

```text
C1 inherited image download = PASS
C1.1 2-reference image download = FAIL, job failed
C1.1 3-reference image download = BLOCKED, no job
IMAGE_OUTPUT_DOWNLOAD_E2E = FAIL
```

视频没有 job 和 signed URL：

```text
VIDEO_OUTPUT_DOWNLOAD_E2E = BLOCKED
```

## 10. 剩余风险

1. `image_mage_flow_edit_turbo_int8` 只有一个顶层 LoadImage；第二、第三参考图缺少 filename 到 IMAGE tensor 的官方转换路径。
2. `slot_overrides` 的子图映射 bug 仍阻断固定 2/3 图路径。
3. 当前自动化执行通道无法向 `codex -a on-request` TUI 写入高成本确认选择。
4. 新建多个并发 Host 会话曾导致 OAuth refresh token reuse；本批通过正常重新登录恢复，后续应避免并发刷新同一 token。

## 11. 下一步建议

本批未达到进入 Batch 5 的门槛。

仅建议两个精简收口动作：

1. 按任务允许的后续范围，评估一个固定三个 LoadImage、固定 image_1/image_2/image_3 的 Saved Workflow；不构建动态 workflow framework。
2. 在能真实承接 Codex `on-request` MCP 费用确认的前台交互会话中，只执行一次 Seedance FLF2V，并完成视频下载与 ffprobe。

在两项完成前，不修改 Drama Plugin Tool Contract、核心业务逻辑、Drama MCP Service、Java Service 或数据库。

## 12. 修改文件与回归保护

本批新增：

```text
plugin/docs/reports/09-Comfy-Cloud-C1.1-阻断收口执行报告.md
```

本批没有新增 C1.1 图片或视频 artifact，因为没有成功 output。Host OAuth 凭据通过正常 login 刷新，但仓库未保存密钥。

未修改：

```text
Drama Plugin Tool Contract
Drama Plugin core business logic
Drama MCP Service
Java Service
Database
Workflow graph
Saved Workflow
```

## 13. 统一验收结论

```text
COMFY_CLOUD_MCP_BASELINE = PASS

REFERENCE_IMAGE_1 = PASS
REFERENCE_IMAGE_2 = FAIL
REFERENCE_IMAGE_3 = BLOCKED
REFERENCE_TO_IMAGE_UP_TO_3_SUPPORTED = FAIL

SLOT_OVERRIDES_ISSUE = BLOCKING

START_END_TO_VIDEO_TEMPLATE = PASS
REAL_START_END_VIDEO_RUN = BLOCKED

IMAGE_OUTPUT_DOWNLOAD_E2E = FAIL
VIDEO_OUTPUT_DOWNLOAD_E2E = BLOCKED

COMFY_CLOUD_VISUAL_PRIMITIVES = FAIL
BATCH_C1_1 = FAIL
```

最终判定依据：2 图已经创建真实 job 并发生执行节点失败，因此多参考图原语是 FAIL；视频没有创建 job，且阻断在 Host 确认层，因此单列 BLOCKED。两者不能合并或降格为 PASS。
