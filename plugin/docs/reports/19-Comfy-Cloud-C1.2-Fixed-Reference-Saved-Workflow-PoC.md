# Batch C1.2 — Fixed Reference Saved Workflow PoC 执行报告

> 执行日期：2026-08-15  
> 原计划文件名：`10-Comfy-Cloud-C1.2-Fixed-Reference-Saved-Workflow-PoC.md`  
> 实际文件名：`19-Comfy-Cloud-C1.2-Fixed-Reference-Saved-Workflow-PoC.md`  
> 顺延原因：报告目录已存在无关的 `10-Windows本地媒体路径适配执行报告.md`，本批未覆盖历史报告。

## 1. 执行摘要

本批按照 C1.2 边界创建了一个固定 2 图 Saved Workflow：`DRAMA_REFERENCE_2_V1`。它基于官方 `image_mage_flow_edit_turbo_int8`，只增加一个独立 `LoadImage` 节点和一条到第二参考图入口的链接，没有修改官方模型、采样、conditioning、decode、SaveImage 或 Drama 系统代码。

真实运行未通过。Comfy Cloud 的 Saved Workflow save-format 转换器没有把新增 `LoadImage` 输出路由到 `TextEncodeMageFlowEdit.images.image_2`，而是错误路由到 `PrimitiveInt (Height)` 的 `value`。两个真实 job 均在输出执行前以相同的 `IMAGE -> INT` 类型错误失败，没有生成图片，也没有输出下载。

第一次失败后，根据转换回显将 link 的 `target_slot` 从顶层 UI 输入下标 `6` 最小纠正为 subgraph definition 中 `images.image_2` 的 ordinal `11`，并原位更新同一 Saved Workflow。纠正后的第二次实际转换仍产生完全相同的错误映射，说明阻断点位于 Comfy Cloud Saved Workflow 的 subgraph 外部输入转换/绑定层，而不是 filename 上传、`LoadImage` 节点或单一 link tuple 数值。

按任务的失败门槛，本批在 2 图失败后停止，没有创建或运行 `DRAMA_REFERENCE_3_V1`，也没有尝试内嵌 LoadImage、重排 subgraph inputs、动态 graph、Saved Workflow 变体或其他 workaround。

结论：

- 2 图 Saved Workflow：`FAIL`
- 3 图 Saved Workflow：`BLOCKED`
- 多参考图生产阻断：仍存在
- Drama 源码：未修改
- 动态 Workflow：未引入
- Batch C1.2：`FAIL`

## 2. C1 / C1.1 继承事实

本批直接继承并未重复执行以下已通过能力：

- Comfy Cloud MCP 连接、认证、工具发现：PASS
- 官方 TEXT_TO_IMAGE：PASS
- 官方 Mage 单参考图：PASS
- 两张 C1 图片的生成、下载与本地文件校验：PASS
- 官方 Mage 模板具有 `images.image_1`、`images.image_2`、`images.image_3` 三个语义入口
- C1.1 已证明 filename 不能直接写入 `TextEncodeMageFlowEdit.images.image_2`，否则出现 `'str' object has no attribute 'movedim'`

本批只验证固定 2/3 图 Saved Workflow 兜底，不执行视频，不重新搜索模板。

## 3. 基线与输入

轻量 MCP 配置检查结果：

```text
comfy-cloud = enabled
drama-tools = enabled
```

2 图 PoC 使用两张既有 C1 图片：

| Reference | 本地路径 | 大小 | Cloud filename |
| --- | --- | ---: | --- |
| reference_1 | `plugin/docs/reports/artifacts/comfy-cloud-c1/text-to-image.png` | 1,698,806 bytes | `0ee6e1d16bb8149a85dab5afd41086cd16448155d4eb55960d1a27a52d0ede36.png` |
| reference_2 | `plugin/docs/reports/artifacts/comfy-cloud-c1/reference-to-image.png` | 1,209,865 bytes | `c516157d429f04ec7430fab3d3336740206a61aef64285b8fbcbd514d860787b.png` |

两张文件均通过 Comfy Cloud `upload_file` 签发的一次性、无凭证 PUT URL 上传成功。报告未保存上传 URL、OAuth token、signed URL 或任何凭据。

## 4. 官方 Workflow 最小改造

来源模板：

```text
image_mage_flow_edit_turbo_int8
workflow id = e13112f7-3d09-4ae1-9e84-633a0627d945
revision = 0
baseline top-level nodes = 5
baseline top-level links = 2
```

保留不变：

- node `7`：官方第一参考图 `LoadImage`
- node `12`：官方 Mage-Flow subgraph instance
- node `10`：`SaveImageAdvanced`
- 所有 subgraph 内模型、conditioning、sampler、resize、decode 节点及链接
- `images.image_3` 未连接

仅新增：

```text
node 32: LoadImage
link 63: node 32 IMAGE -> node 12 second-reference input
```

没有新增模型、sampler、conditioning、decode、输出节点或任何运行框架。

## 5. DRAMA_REFERENCE_2_V1

### 5.1 保存结果

```text
Saved Workflow name = DRAMA_REFERENCE_2_V1
Saved Workflow id = 5cf47398-6bda-4cf3-a0d1-51fdeacb8e03
filename = drama-reference-2-v1.json
current version = 2
top-level nodes = 6
top-level links = 3
```

初始保存图：

```text
node 7  -> node 12 / image_1
node 32 -> node 12 / intended image_2
image_3 = unconnected
```

远程 Saved Workflow 身份保存成功，但真实执行失败，因此它不是可投入生产的已验收 Workflow。

### 5.2 第一次真实运行

输入覆盖：

```json
{
  "7": {
    "image": "0ee6e1d16bb8149a85dab5afd41086cd16448155d4eb55960d1a27a52d0ede36.png"
  },
  "32": {
    "image": "c516157d429f04ec7430fab3d3336740206a61aef64285b8fbcbd514d860787b.png"
  },
  "12:5": {
    "prompt": "Use the first image as the main composition and color palette. Incorporate one clear visual motif from the second image while preserving a coherent single scene."
  }
}
```

未使用 `slot_overrides`，也未把 filename 直接写入 IMAGE tensor 输入。

```text
job_id = 3f0f3c47-8786-4e74-9fd4-61782e50111b
raw_status = failed
error_type = prompt_outputs_failed_validation / return_type_mismatch
error_node = 12:21
output = none
reported charges = unknown
```

关键错误：

```text
PrimitiveInt.value expected INT
received IMAGE from ["32", 0]
```

本次转换后的执行图没有出现：

```text
12:5.inputs["images.image_2"] = ["32", 0]
```

反而出现：

```text
12:21.inputs.value = ["32", 0]
```

### 5.3 单 link 最小纠正

第一次 save-format 使用：

```text
[63, 32, 0, 12, 6, "IMAGE"]
```

真实 workflow definition 中 subgraph inputs 的 ordinal 为：

```text
images.image_2 = 11
images.image_3 = 12
```

因此只将同一 link 原位纠正为：

```text
[63, 32, 0, 12, 11, "IMAGE"]
```

其他节点、链接和 subgraph 内容未修改。Saved Workflow ID 保持不变，版本从 1 更新到 2，没有创建副本。

### 5.4 纠正后的第二次真实转换与 job

```text
job_id = 923aadd1-b61e-4fea-b004-2b4629e35fea
raw_status = failed
error_type = prompt_outputs_failed_validation / return_type_mismatch
error_node = 12:21
output = none
reported charges = unknown
```

纠正后的实际 Converted API workflow 仍然是：

```text
12:5.images.image_2 = absent
12:21.value = ["32", 0]
```

因此第二次 job 以与第一次完全相同的 IMAGE→INT 类型错误终止。

判定：

```text
REFERENCE_IMAGE_2_SAVED_WORKFLOW = FAIL
```

## 6. DRAMA_REFERENCE_3_V1

任务要求只有 2 图真实 E2E 成功后才允许创建 3 图版本。2 图未通过，因此：

```text
DRAMA_REFERENCE_3_V1 created = NO
3-image upload/run = NOT EXECUTED
REFERENCE_IMAGE_3_SAVED_WORKFLOW = BLOCKED
```

本批没有准备第三张图片，没有新增 Cloud Workflow，也没有产生 3 图 artifact。

## 7. Workflow 差异摘要

预期最小结构是：

```text
official 1-image workflow
  + one LoadImage
  + one IMAGE link
= fixed 2-image workflow
```

实际远程保存图满足这一机械差异，但 Comfy Cloud 从 save-format 转为 API-format 时，没有将新增外部 link 路由到 `images.image_2`，而是路由到 subgraph 的第 6 个定义输入对应的 `PrimitiveInt (Height)`。

对 link target slot 做 `6 -> 11` 的单字段纠正后，远程原始 `workflow_json` 已保存新值，但运行转换结果仍沿用错误映射。由此可将根因收敛为：

```text
Saved Workflow graph
  -> subgraph external IMAGE input
  -> API workflow conversion
```

这一层的路由/映射缺口。

## 8. 已知 Comfy Cloud 问题

```text
OFFICIAL_MULTI_REFERENCE_TEMPLATE_BINDING = BLOCKING
MULTI_REFERENCE_FILENAME_TO_IMAGE_BINDING = BLOCKING
```

阻断点不是文件上传，也不是 `LoadImage` 对 filename 的解析。两个上传文件都能被独立的 `LoadImage` 节点识别；失败发生在 Saved Workflow 将顶层链接投影到 subgraph 内部输入时。

本批没有继续研究或修改：

- proxyWidgets
- slot mapping
- subgraph inputs 重排
- subgraph 内嵌 LoadImage
- Comfy server internals
- Saved Workflow 变体
- 动态 Workflow

这符合“2 图 Saved Workflow 失败后停止 3 图和其他绕过”的任务边界。

## 9. Artifact 与下载

本批没有成功输出，因此没有创建：

```text
plugin/docs/reports/artifacts/comfy-cloud-c1-2/reference-2-saved-workflow.png
plugin/docs/reports/artifacts/comfy-cloud-c1-2/reference-3-saved-workflow.png
```

两个 job 均没有 output、signed URL 或可下载文件，不能声明图片输出 E2E PASS。

## 10. Drama 回归保护

轻量检查确认：

```text
comfy-cloud = enabled
drama-tools = enabled
```

本批未修改：

- Drama Plugin Tool Contract
- Drama Plugin Skill Core
- Drama Plugin business logic
- Drama MCP Service
- Java Service
- Database
- Media / Asset Contract

`git diff --name-only` 在报告生成前为空；已有 C1/C1.1 报告与 artifact 是进入本批前已存在的未跟踪文件。本批本地新增内容仅为本执行报告。

## 11. 风险与下一步建议

当前不能冻结 0/1/2/3 reference 的生产选择，因为 2 图 Saved Workflow 尚未通过，3 图也未被允许验证。

建议下一步不要进入 Batch 5 的多参考生产。应先由 Comfy Cloud 修复或明确支持以下能力之一：

1. save-format 顶层 `LoadImage` 到 subgraph `images.image_2` / `images.image_3` 的稳定转换；或
2. 提供一个官方可运行的固定多参考 Saved Workflow / binding 示例，能够在 Converted API workflow 中明确产生 `TextEncodeMageFlowEdit.images.image_2` 与 `images.image_3` 的 IMAGE links。

如开展后续独立诊断，范围应仍保持为一个固定 2 图 Workflow，不应引入动态 Workflow framework。视频仍属于独立的人工 Host confirmation E2E，本批没有执行或消耗视频 credits。

## 12. 修改与新增清单

### Comfy Cloud 远程状态

```text
CREATED:
- DRAMA_REFERENCE_2_V1
  workflow_id = 5cf47398-6bda-4cf3-a0d1-51fdeacb8e03
  current version = 2
  status = saved but E2E failed; not production-approved

NOT CREATED:
- DRAMA_REFERENCE_3_V1
```

### 本地仓库

```text
ADDED:
- plugin/docs/reports/19-Comfy-Cloud-C1.2-Fixed-Reference-Saved-Workflow-PoC.md

MODIFIED:
- none

ARTIFACTS ADDED:
- none
```

## 13. 统一验收结论

```text
COMFY_CLOUD_MCP_BASELINE = PASS

TEXT_TO_IMAGE = PASS
REFERENCE_IMAGE_1 = PASS

REFERENCE_IMAGE_2_SAVED_WORKFLOW = FAIL
REFERENCE_IMAGE_3_SAVED_WORKFLOW = BLOCKED

REFERENCE_TO_IMAGE_UP_TO_3 = FAIL

DRAMA_REFERENCE_2_V1_SAVED = PASS
DRAMA_REFERENCE_3_V1_SAVED = BLOCKED

MULTI_REFERENCE_FILENAME_TO_IMAGE_BINDING = BLOCKING
OFFICIAL_MULTI_REFERENCE_TEMPLATE_BINDING = BLOCKING

DRAMA_SOURCE_CODE_UNCHANGED = PASS
DYNAMIC_WORKFLOW_INTRODUCED = NO

BATCH_C1_2 = FAIL
```

补充限定：`DRAMA_REFERENCE_2_V1_SAVED = PASS` 仅表示远程稳定 ID 与图保存成功，不表示运行验收通过；该 Workflow 当前不得用于生产。

