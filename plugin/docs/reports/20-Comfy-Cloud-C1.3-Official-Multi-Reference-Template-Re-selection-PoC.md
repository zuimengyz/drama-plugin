# Batch C1.3 — Official Multi-Reference Template Re-selection PoC 执行报告

> 执行日期：2026-08-15  
> 报告编号：20  
> 执行边界：仅使用 Comfy Cloud 官方模板与 `run_template`；未创建/修改 Saved Workflow、未提交自定义 graph、未修改 Drama 系统、未执行视频。

## 1. 执行摘要

本批已经找到并真实跑通无需修改 Workflow graph 的官方多参考模板：

- 官方双参考：`Qwen Image Edit 2511 - Material Replacement`（`image_qwen_image_edit_2511`）具有两个独立、原生预连接的 `LoadImage`，真实 job 完成，输出已下载并校验。
- 官方三参考：`FLUX.2 [max]: Object Swap`（`api_bfl_flux2_max_sofa_swap`）具有三个独立、原生预连接的 `LoadImage`，真实 job 完成，输出已下载并校验。
- Priority 1 `Flux.2 [Klein] 4B Distilled: Image Edit` 的图结构满足双参考要求，但官方模板 schema/proxyWidget 的 prompt 绑定在提交前失败；没有创建 job、没有消费证据。按优先级进入 Qwen 后即成功，因此未测试 Flux.2 Dev。

最终结果：

```text
OFFICIAL_REFERENCE_IMAGE_2 = PASS
OFFICIAL_REFERENCE_IMAGE_3 = PASS
REFERENCE_TO_IMAGE_UP_TO_3 = PASS
BATCH_C1_3 = PASS
```

达到停止条件。无需进入 flat API-format Workflow、Saved Workflow 或动态 Workflow 设计。

## 2. Mage 路线冻结说明

直接继承 C1.2 的真实结论：`DRAMA_REFERENCE_2_V1` 在 Saved Workflow editor-format 转 API workflow 时，把新增 `IMAGE` link 错误映射到 `PrimitiveInt.value`，产生 `IMAGE -> INT / return_type_mismatch`。对 target slot 做一次最小纠正后，转换结果仍相同。

本批严格执行冻结：

```text
DRAMA_REFERENCE_2_V1 = deprecated candidate
DRAMA_REFERENCE_2_V1 = NOT PRODUCTION APPROVED
DRAMA_REFERENCE_2_V1 rerun = NO
DRAMA_REFERENCE_3_V1 created = NO
Mage graph/proxyWidgets/slot mapping research = NO
```

## 3. 基线、连接与输入

轻量配置复核：

```text
comfy-cloud = enabled
drama-tools = enabled
Comfy endpoint = https://cloud.comfy.org/mcp
```

执行中出现过 OAuth refresh token reuse 与瞬时 HTTP 502。通过官方 `codex mcp login comfy-cloud` OAuth 流程恢复；未修改 endpoint、未绕过 OAuth、未保存 token 或 signed URL。恢复后模板搜索、运行与输出读取均成功。

复用的两个 C1 输入：

| Reference | 本地路径 | 文件 | Cloud filename |
| --- | --- | --- | --- |
| reference_1 | `plugin/docs/reports/artifacts/comfy-cloud-c1/text-to-image.png` | PNG, 1024×1024, 1,698,806 bytes | `0ee6e1d16bb8149a85dab5afd41086cd16448155d4eb55960d1a27a52d0ede36.png` |
| reference_2 | `plugin/docs/reports/artifacts/comfy-cloud-c1/reference-to-image.png` | PNG, 1024×1024, 1,209,865 bytes | `c516157d429f04ec7430fab3d3336740206a61aef64285b8fbcbd514d860787b.png` |

两张输入均已在 C1/C1.1 经官方上传能力验证。本批确认本地文件存在、size > 0、可识别为 PNG，并复用其 Cloud filename，没有重复生成 Drama 素材。

## 4. 候选模板发现与筛选

仅围绕多参考图片编辑执行定向 `search_templates`，没有全量审计、视频搜索或无关模型比较。

| Priority | 实际模板 | 原生 LoadImage 结构 | 运行结果 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | `Flux.2 [Klein] 4B Distilled: Image Edit` / `image_flux2_klein_image_edit_4b_distilled` | node `76`、`81` 分别连接到双参考分支 node `92` 的 reference image 1/2 | 提交前 prompt binding 校验失败，无 job | FAIL，进入 Priority 2 |
| 2 | `Qwen Image Edit 2511 - Material Replacement` / `image_qwen_image_edit_2511` | node `41`、`83` 分别连接到 node `170` 的 `image`、`image2` | job completed，输出下载 PASS | PASS，停止双图候选比较 |
| 3 | Flux.2 Dev | 未执行 | 未执行 | NOT_TESTED |

Klein 的关键 link 证据：

```text
LoadImage 76 --link 169--> node 92 / reference_image1
LoadImage 81 --link 172--> node 92 / reference_image2
```

其首次 `run_template` 使用 `slot_overrides 92.text`，提交前报 `no proxyWidget mapping for slot 92.text`；允许的一次参数纠正改为 `input_overrides 92.text`，又在提交前报 node `92` 不存在于执行图。两次均没有 job_id，未报告消费。本批没有修改模板或继续研究该 binding。

## 5. 官方双参考结构审计

选中模板：

```text
title = Qwen Image Edit 2511 - Material Replacement
template_id = image_qwen_image_edit_2511
workflow version = 0.4
workflow revision = 0
output = image
SaveImage node = 9
```

真实 workflow link：

```text
LoadImage node 41 --link 376--> subgraph node 170 / image
LoadImage node 83 --link 377--> subgraph node 170 / image2
node 170 / image3 = unconnected
prompt execution node = 170:151
SaveImage node = 9
```

判定：

```text
REFERENCE_1_NATIVE_LOADIMAGE = YES
REFERENCE_2_NATIVE_LOADIMAGE = YES
OFFICIAL_NATIVE_REFERENCE_2_TEMPLATE_FOUND = PASS
```

## 6. 双参考真实 E2E

运行覆盖：

```text
node 41.image = reference_1 Cloud filename
node 83.image = reference_2 Cloud filename
node 170:151.prompt =
Use image 1 as the main subject and composition. Apply the clear blue ornamental
color motif from image 2 to the main subject, creating one coherent realistic scene.
```

完整链路：

```text
run_template
-> job_id 4c187448-0254-4fd7-aba2-624f7d90f517
-> wait_for_job
-> completed
-> get_output / SaveImage node 9
-> signed URL
-> local download
```

输出证据：

| Field | Value |
| --- | --- |
| Cloud output filename | `346f3f1a7ba9a6d1c5d198810868d5339a33987533b58e7970725fef4d679939.png` |
| 本地 artifact | `plugin/docs/reports/artifacts/comfy-cloud-c1-3/official-reference-2.png` |
| 文件类型 | PNG, 8-bit RGB, non-interlaced |
| 分辨率 | 1024×1024 |
| 大小 | 927,360 bytes |
| SHA-256 | `ba359321e247cfa629ffdd18f4deb3191f1806669b62db8cd524f2fdb408632d` |
| Credits | 服务端未返回数值 |

运行警告仅涉及两个 LoadImage 的额外 widget 值未映射，以及内部 prompt override 无法回写到可重开 UI workflow；执行图成功使用覆盖值，job 完成并产生有效输出。

最小视觉复核：输出非空，保持第一张图的主体与居中构图，并出现清晰的蓝/青色装饰材质与发光带；第二参考路径不是未连接端口，而是由独立 node `83` 原生进入官方执行链。未进行历史真实性或生产质量评分。

```text
OFFICIAL_REFERENCE_IMAGE_2 = PASS
```

## 7. 官方三参考能力发现

双图 PASS 后才进入本阶段。定向检索并检查候选的真实 graph：

| Template | 顶层 LoadImage | 连接结果 | 三图资格 |
| --- | --- | --- | --- |
| `image_mage_flow_edit_turbo_int8` | `7` | 仅连接 `images.image_1` | NO |
| `template_3x3_contact_sheet` | `86,88,89` | 分流到两套双图模型输入，不是同一生成链三参考 | NO |
| `api_grok_imagine_image_2_image_edit` | `11,13` | 两个独立参考输入 | NO |
| `api_flux2` / Flux.2 Pro | `15,16,18,19` | 四个独立 LoadImage 分别连接同一模型 `images.image0..3` | YES |
| `api_bfl_flux2_max_sofa_swap` / FLUX.2 [max]: Object Swap | `2,3,10` | 三个独立 LoadImage 合并后进入同一模型 | YES，选择执行 |

选择 `api_bfl_flux2_max_sofa_swap` 是因为它恰好提供三个独立、预连接的 LoadImage，能以最小变量验证固定 3 图原语。

## 8. 官方三参考结构审计

真实 link 证据：

```text
LoadImage node 2  --link 20--> BatchImagesNode 15 / images.image0
LoadImage node 3  --link 21--> BatchImagesNode 15 / images.image1
LoadImage node 10 --link 22--> BatchImagesNode 15 / images.image2
BatchImagesNode 15 --link 23--> model node 1 / images
prompt node = model node 1 / prompt
output type = image
```

三个 reference 均由不同 Cloud filename 驱动；没有复制同一个文件标识、没有拼图、没有把 filename 写入 IMAGE tensor 输入，也没有改 graph。

第三输入直接复用本批双参考 job 的真实 Cloud 输出：

```text
reference_3 Cloud filename =
346f3f1a7ba9a6d1c5d198810868d5339a33987533b58e7970725fef4d679939.png
```

它与 reference_1、reference_2 是三个不同的真实图片文件，因此无需额外生成或重复上传。

```text
OFFICIAL_NATIVE_REFERENCE_3_TEMPLATE_FOUND = PASS
```

## 9. 三参考真实 E2E

运行覆盖：

```text
node 2.image  = reference_1 Cloud filename
node 3.image  = reference_2 Cloud filename
node 10.image = reference_3 Cloud filename
node 1.prompt =
Use image 1 as the main scene, replace its central object with the main object
from image 2, and apply the blue ornamental material and lighting cues from
image 3. Keep one coherent realistic composition.
```

首次从不可交互的嵌套 Host 发起确认时，`run_template` 在提交前被取消：无 job_id、无消费证据。随后使用 Codex 正式 `--approve-for-me` 审批通道提交同一个逻辑调用；这不是失败 job 重试，前一次没有进入 Comfy job 系统。

完整链路：

```text
run_template(confirm=true)
-> job_id f9d7a15b-62fe-4cf0-9ecc-53920e87efeb
-> wait_for_job
-> completed
-> get_output
-> signed URL
-> local download
```

输出证据：

| Field | Value |
| --- | --- |
| Cloud output filename | `5c13416980d907fd5a896f2a4d36424d313aaeacec7b6406515b5f1c863c43a1.png` |
| 本地 artifact | `plugin/docs/reports/artifacts/comfy-cloud-c1-3/official-reference-3.png` |
| 文件类型 | PNG, 8-bit RGBA, non-interlaced |
| 分辨率 | 1024×1024 |
| 大小 | 1,437,324 bytes |
| SHA-256 | `91243969aa1aac57c6c5d97548f7581bb629fdf89a571a97108dc27f4c2263d6` |
| Credits | 服务端未返回数值 |

最小视觉复核：输出为可读、非空的统一场景，主体明确，具有蓝青色材质、装饰纹理、锈蚀细节与发光结构，未出现错误文件、空白图或明显断裂的拼图结果。结构证据证明三张图片分别经 node `2`、`3`、`10` 进入同一官方生成链。视觉复核仅用于 PoC 有效性，不作生产质量评分。

```text
OFFICIAL_REFERENCE_IMAGE_3 = PASS
REFERENCE_TO_IMAGE_UP_TO_3 = PASS
```

## 10. Artifact 清单

本批只保存两个真实生成结果：

```text
plugin/docs/reports/artifacts/comfy-cloud-c1-3/official-reference-2.png
plugin/docs/reports/artifacts/comfy-cloud-c1-3/official-reference-3.png
```

未把 OAuth token、上传 URL、下载 signed URL 或其他凭据写入仓库。

## 11. Workflow 修改证明

本批只调用官方模板读取/搜索、上传、`run_template`、job 等待和输出读取能力。

```text
save_workflow = NOT CALLED
update_workflow = NOT CALLED
run_saved_workflow = NOT CALLED
submit_workflow = NOT CALLED
custom graph = NOT CREATED

CUSTOM_WORKFLOW_CREATED = NO
SAVED_WORKFLOW_CREATED = NO
WORKFLOW_GRAPH_MODIFIED = NO
DYNAMIC_WORKFLOW_INTRODUCED = NO
```

## 12. Drama 回归保护

执行后 `codex mcp list`：

```text
comfy-cloud = enabled
drama-tools = enabled
```

`git diff --name-only` 为空，`git diff --check` 通过。`git status --short` 仅显示既有/本批报告与 artifact 目录为 untracked；没有 tracked Drama 源码差异。

未修改：

- Drama Plugin Tool Contract / Skill Core / business logic
- Drama MCP Service
- Java Service / Database
- Media Contract / Asset Contract

```text
DRAMA_SOURCE_CODE_UNCHANGED = PASS
```

## 13. 剩余风险与边界

- 本批证明的是固定 2/3 图输入的官方模板运行能力，不是跨模型视觉一致性或历史真实性验收。
- Qwen 双参考运行使用了官方执行图内的 flattened prompt node override；服务端警告它不能回写到 UI workflow，但不影响本次 run_template 执行与输出。
- 三参考选用的官方 FLUX.2 [max] 模板语义为 Object Swap。正式 Batch 5 应把模板选择与固定参考数量、实际编辑意图一并做最小映射，但无需修改 Workflow graph。
- Comfy MCP 曾出现 OAuth refresh reuse 与 HTTP 502；官方重新登录后恢复。这是运行环境稳定性风险，不影响已完成 job 与 artifact 证据。
- 服务端未返回 credits 数值，不能从本报告推断单次成本。
- 视频仍维持既有状态，本批没有执行或改变其结论。

## 14. 下一步建议

多参考 Workflow 基础能力验证应在此停止：

```text
0 reference -> 既有官方 TEXT_TO_IMAGE
1 reference -> 既有官方单参考模板
2 references -> image_qwen_image_edit_2511
3 references -> api_bfl_flux2_max_sofa_swap
```

不要返回 Mage Saved Workflow，不需要 flat API workflow，也不要创建动态 Workflow 系统。下一步仅完成既定的视频人工 confirmation E2E，然后进入 Batch 5 Drama Visual Production E2E；正式生产模板选择与 Prompt/视觉 Review 属于 Batch 5，而不是继续研究 Workflow 编排。

## 15. 统一验收结论

```text
COMFY_CLOUD_MCP_BASELINE = PASS

TEXT_TO_IMAGE = PASS
REFERENCE_IMAGE_1 = PASS

MAGE_SAVED_WORKFLOW_ROUTE = DEPRECATED

FLUX2_KLEIN_MULTI_REFERENCE_TEMPLATE = FAIL
QWEN_MULTI_REFERENCE_TEMPLATE = PASS
FLUX2_DEV_MULTI_REFERENCE_TEMPLATE = NOT_TESTED

OFFICIAL_NATIVE_REFERENCE_2_TEMPLATE_FOUND = PASS
OFFICIAL_REFERENCE_IMAGE_2 = PASS

OFFICIAL_NATIVE_REFERENCE_3_TEMPLATE_FOUND = PASS
OFFICIAL_REFERENCE_IMAGE_3 = PASS

REFERENCE_TO_IMAGE_UP_TO_3 = PASS

CUSTOM_WORKFLOW_CREATED = NO
SAVED_WORKFLOW_CREATED = NO
WORKFLOW_GRAPH_MODIFIED = NO
DYNAMIC_WORKFLOW_INTRODUCED = NO

DRAMA_SOURCE_CODE_UNCHANGED = PASS

BATCH_C1_3 = PASS
```

最终回答：Comfy Cloud 当前存在无需修改 Workflow、无需 Saved Workflow 转换、原生具备多个独立 LoadImage 的官方模板，并已分别完成 2 图与 3 图真实 E2E。官方多参考路线可以作为后续 Drama 固定输入视觉生产原语候选。
