# F01-TS01-R10 — High-Fidelity Keyframe Route Minimal Audit

## 1. Current Route

2026-09-24 只读检查，以最新保存的 **r12 实际请求及输出** 为准，不沿用此前 IMAGE_EDIT 路线假设。

| 项目 | 核实结果 |
| --- | --- |
| Provider / Model | Comfy Cloud，BFL `Flux.2 [pro]` |
| Template / Node | `F01-inspected-Flux2-zero-reference`；`Flux2ImageNode` #23 → `SaveImage` |
| Input / Mode | 首次 text-to-image，零 reference；不是编辑模式 |
| Resolution | 请求与 PNG 均为 **1280×720**，约 0.92 MP，16:9 |
| Seed | 22090202 |
| Reference capability | 今日 MCP schema：pro/max 均支持最多 8 个可选 image 输入；当前未使用。未暴露 mask、ControlNet、脸部专用锁定参数 |
| 后处理 | 当前 graph 无 upscale、face detail、refinement stage |
| Runtime | 当前 `drama-plugin.env` 加载结果为 `live_action`；实际导入当前仓库 `visual/frame_request.py` |

证据：[r12 编译请求](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/test-shoot-01/S02-inputs/K02-scoped-compiled-r12.json)、[成功提交回执](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/test-shoot-01/S02-inputs/K02-r12-submit.json)、[当前 runtime 摘要](/Users/zy/historical-plugin/artifacts/f01-ts01-r10-keyframe-audit/runtime-summary.json)、[今日 MCP schema 与估价](/Users/zy/historical-plugin/artifacts/f01-ts01-r10-keyframe-audit/live-schema-and-estimates.json)。旧 `runtime.env` 已不存在，未将未配置的 shell 结果当作正式配置。

## 2. Current Quality Ceiling

已直接查看 [r12](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/test-shoot-01/S02-inputs/K02-r12.png) 和 [r11](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/test-shoot-01/S02-inputs/K02-r11.png)。r12 能形成可信的湿夜街道、毛料外套、胡茬和主光，但女孩脸部较均匀、背景立面较平滑，整体仍有摆拍感。背景部分低细节同时符合景深虚化，不能全部归为模型纹理失败。

**当前已证明的是“720p 可用候选图”，尚未证明“高保真 Hero Keyframe”，也没有测出 pro 模型的绝对上限。** r12 仍缺脚部、女孩看镜头，未完整实现接近动作；保存的视觉 review 也是 PENDING_REVIEW、用户采用 PENDING。这些是首帧锚点的独立问题，高清化不会自动修正。r11 的全身关系更明显，但时代物件、年龄等也有偏差；两图不是控制变量实验。

本轮没有可逐帧核对的《归墟》指定参考图，不能量化与其差距或宣称已达到同等级。

## 3. Main Quality Bottleneck

| 因素 | 判断与证据边界 |
| --- | --- |
| 分辨率 / 人脸像素占比 | 明确限制：只有 0.92 MP，两人共享画面，女孩脸部可用像素更少。当前 MCP 同节点允许宽高各至 2048；16:9 可测 2048×1152（2.36 MP），像素数为当前 2.56 倍 |
| 模型 / 指令服从 | 样本显示构图、视线和动作没有全部兑现；可能同时影响摄影真实感。尚无同条件跨模型证据，不能把所有问题定性为 pro 的不可突破上限 |
| reference control | 能力存在但当前为零参考。文字身份不能证明跨镜脸部稳定；提升分辨率也不能替代经审阅的身份锚点 |
| 超分 / 精修缺失 | 确实缺失；但新增细节不等于恢复真实细节，脸部精修可能改变年龄与身份，不能默认有净收益 |
| 材质 / 摄影 | 墙面均匀、肤质和摆拍感是本次视觉观察。需分别比较皮肤、毛发、织物、石路与虚焦区域，避免将锐化误认成电影真实感 |

因此当前最明确的组合是：**低输出像素预算 + 零视觉参考 + 单阶段生成，叠加仍未稳定兑现的构图/表演关系**。各因素贡献比例尚未知。

## 4. Available Better Route

仅比较当前 Comfy 可发现的近邻候选；“可发现”不等于已通过本项目质量验证。

| 路线 | 写实、人脸、建筑材质与电影质感 | Reference / 视频锚点稳定性 | 接入差异 |
| --- | --- | --- | --- |
| FLUX.2 pro，2048×1152 | 更高原生采样分辨率；是否减少顺滑感待测 | 同样最多 8 图；零参考仍没有身份锁定证明 | 同一节点，仅尺寸变化 |
| **FLUX.2 max，2048×1152** | 官方定位为同家族最高质量、较强编辑一致性和指令服从；本场人脸/材质优势尚未实测 | 同节点多参考/edit 能力；身份、年龄和构图仍须复核 | **最小 Hero 替代候选**：相同节点与图结构，model/尺寸变化；需重新编译、报价和资格检查，非直接改旧 sealed request |
| Seedream 5.0 Pro | MCP 可发现高分辨率生成/编辑；没有本场样本，不能断言优于 max | 有单图/多参考编辑；schema reference slots 与 tooltip 数量不一致，不据此承诺上限；跨模型身份迁移未验证 | 不同节点 `ByteDanceSeedreamNodeV3`；当前自定义 API graph 分支仅接纳 Flux2ImageNode，不能视作直接可替换 |
| pro + SeedVR2 7B Int8 | 可发现图像超分模板；能否改善皮肤、砖石且不产生伪细节待测 | 继承源图构图，也继承其错误；脸部身份保真须单独验证 | 增加处理阶段，不是当前生产链已有能力；slot 默认值存在类型异常，执行前需核实底层 graph |

max 的质量定位来自 [BFL 官方说明](https://bfl.ai/models/flux-2-max)，属于厂商能力声明，不是本场实测结论。Seedream 与 SeedVR2 来自今日 `search_templates` / `get_template_schema` / `get_node`；未扩展其他 Provider。

## 5. Minimal Recommendation

**CURRENT_ROUTE：Hero Keyframe → REPLACE_FOR_HERO_KEYFRAME（候选决策，A/B 验证后才采用）；Ordinary Support Image → KEEP。**

唯一优先替代候选：**Comfy Cloud / Flux2ImageNode / FLUX.2 [max] / 2048×1152 原生生成或现有合规 reference-edit 路径**。先验证同节点升级，不先引入超分、自动脸部修复或另一套 Provider。若 pro 的原生高分辨率结果与 max 相当，则保留较便宜的 pro。

已批准身份必须继续受现有 reference/authority 流程约束，不通过换模型另造演员；当前 r12 未完成采用审阅，不将它自动固定为身份母版。无论选择何种模型，脚部、视线、当前动作的通过标准保持不变。普通辅助图不随 Hero 升级。

## 6. Whether A/B Test Is Required

**NEEDS_CONTROLLED_A_B_TEST。** 本轮未执行。

最小分辨实验：固定现有 IR、serializer、画幅、输入模式、参考集合与相同 seed 列表，比较 pro/max × 1280×720/2048×1152。先每格一张作筛查，不能凭单张宣称模型上限；只有发现明确收益再考虑重复验证。跨模型相同 seed 只是记录控制，不代表相同潜变量。

同时按原尺寸与统一显示尺寸比较：身份/年龄、目光/脚部/接近关系、皮肤与毛发、墙面/石路/织物、自然光与反光、伪细节。高分辨率若只更锐而未更真实，不判升级成功。现有 r12 可作历史参考，只有全部输入条件一致时才作为控制格复用。

本轮只写审计和证据；未改 Prompt、角色、脚本、模型配置、视频路线或预算，未提交收费任务。

## 7. Estimated Cost Impact

今日 `estimate_credits` 对明确的零参考 Flux2 API graph 返回：

| 单张路线 | Provider 节点估价 | 对当前 6 credits 估价的增量 |
| --- | ---: | ---: |
| pro 1280×720 | 6 credits（首次网络失败后只读重试成功） | — |
| pro 2048×1152 | 13 credits | +7 |
| max 1280×720 | 15 credits | +9 |
| max 2048×1152 | 27 credits | +21（4.5 倍） |

四格各一张共约 **61 credits 的 Provider 节点估价**，不是已批准执行计划；若合格复用当前基线，新三格约 55。仅升级一张 Hero 不应把全体图片预算乘以 4.5。

真实 r12 [usage 记录](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/test-shoot-01/S02-inputs/K02-r12-usage.json)显示 6.33 credits，记录明确不是最终账单结算，证明估价与实际可不同。Seedream 当前模板返回约 9 credits/image、整次 total unknown；SeedVR2 返回无付费 API 节点，**不代表免费**，GPU/队列与 storage 不在该估价内。

以上估价来自 MCP bundled pricing，可能滞后；reference-edit 必须按实际参考输入另行报价。未以预算余量代替成本，也未修改现有授权。本次新增收费调用：**0**。
