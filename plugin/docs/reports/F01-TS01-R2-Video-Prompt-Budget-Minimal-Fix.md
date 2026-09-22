# F01-TS01-R2 — Video Prompt Budget Minimal Fix

结果：**Prompt Budget 修复 PASS；真实 S02-K02 完整投影仍因缺少必需参考绑定而 BLOCKED。收费生成 0。**

## 1. Root Cause

旧投影逐层展开完整结构标签及审计指纹，只在末尾拒绝超长 prompt，不提供压缩路径。S02-K02 的既有 2941 字符记录是**添加 reference 前**的正文，原记录同时报告 `REQUIRED_REFERENCE_UNFULFILLED`。

本次再次通过真实 Comfy MCP `get_node(Vidu3ImageToVideoNode)` 核实上限。当前原始 schema 在 prompt 的 tooltip 中写明 `max 2000 characters`，未提供名为 maxPromptCharacters 的原始机器字段；修复将该事实规范化为 Provider Capability 的 `maxPromptCharacters=2000`，不改变上限。

## 2. Files Changed

- `src/drama_plugin/hosts/prompt_budget.py`：模型长度解析、FIT/COMPRESSIBLE/EXCEEDED、结构压缩及明确异常。
- `src/drama_plugin/hosts/cinematic_projection.py`：从同一完整意图生成普通/紧凑投影；包含 reference 段后计数；压缩审计写入 projection，进入现有 seal fingerprint。
- `src/drama_plugin/hosts/comfy_video.py`：capability 统一长度字段；最终请求再次校验预算。
- `tests/test_prompt_budget.py`、`tests/fixtures/prompt-budget/`：8 项测试、真实 Vidu schema 和真实 S02-K02 冻结意图副本。
- `tests/test_seedance_contract.py`、`tests/test_video_reconciliation.py`：更新长度失败断言至新错误契约。
- 工作区 `artifacts/f01-ts01-r2/`：只读回归脚本和诊断证据。

未修改现有 `specialized_asset.py`、`test_literary_visual_convergence.py` 的用户改动；未修改 Director、Shot、剧本、环境配置或生产素材。

## 3. Prompt Budget Contract

来源优先级：当前 node schema（机器限制或明确的字符上限 tooltip）→ capability.maxPromptCharacters → adapter fallback。无已知限制的模型记录 NOT_DECLARED，不套用 Vidu 的 2000。

预算记录包含 model、maxPromptCharacters、hardMaxPromptCharacters、reservedPromptCharacters、effectivePromptBudget、limitSource、原始/最终字符数、status 和压缩规则版本。

- **FIT**：原 prompt 原样通过，包括空白和原词。
- **COMPRESSIBLE**：原文超限，完整紧凑投影在预算内。
- **EXCEEDED**：紧凑投影仍超限，抛出 `PROVIDER_PROMPT_BUDGET_EXCEEDED`，包含 model、original_length、compressed_length、hard_limit，并附结构化 budget。

当前投影在预算处理前已经拼入所有 reference / wrapper 文本，后续 compile 不追加 prompt 内容，因此 reservedPromptCharacters **精确为 0**。最终 compile 和 projection validation 均校验完整 prompt。裸字符串 legacy prompt 不作猜测式改写，超限时明确失败。

## 4. Compression Rule

确定性 `structural-labels-and-provenance-v1`，仅在超限时启用：

1. 将编译器生成的冗长英文结构标签改为短而明确的标签，收紧分隔空白。
2. 从表演/声音的模型正文中移出 directorIntentFingerprint、grammarFingerprint、beatId、spokenContentId；这些审计数据仍留在完整冻结意图、manifest/source hash 和 seal 中。
3. 保留所有创作值原文、角色与对象分组、动作顺序、对白及时间窗、呼吸/表演要求、空间关系、摄影、光线、声音和连续性。不同角色的相同动作不去重，不改写自由文本。

本例不需要删除外貌、场景或其他创作描述，也不假定尚未提供的 reference 已承担这些语义。没有 substring、尾部删除、模型切换或镜头拆分。切换到无已知上限的 Seedance 投影时，仍从完整 frozen intent 重新生成原始完整 prompt。

## 5. Tests

在 `/Users/zy/historical-plugin/drama-plugin` 执行：

```sh
../drama-mcp-service/.venv/bin/python -m pytest plugin/tests/test_prompt_budget.py plugin/tests/test_video_reconciliation.py plugin/tests/test_seedance_contract.py -q
# 122 passed

../drama-mcp-service/.venv/bin/python -m pytest plugin/tests/test_cinematic_direction.py plugin/tests/test_mcp_execution.py plugin/tests/test_video_selection.py plugin/tests/test_expression_routes.py -q
# 107 passed

../drama-mcp-service/.venv/bin/python -m mypy plugin/src/drama_plugin/hosts/prompt_budget.py plugin/src/drama_plugin/hosts/cinematic_projection.py plugin/src/drama_plugin/hosts/comfy_video.py --follow-imports=silent
# Success: no issues found in 3 source files

git diff --check
# 无错误
```

**合计 229 项相关测试通过。** 覆盖 FIT 原样通过、可压缩、无法压缩、正式 Vidu request <=2000、source 不变、切换模型重新编译、runtime 优先级、reserved 预算、追加文本阻断和缺失参考继续拒绝。

## 6. S02-K02 Regression Result

直接读取当前工作区原文件 `artifacts/flagship-literary-film-01/test-shoot-01/S02-cinematic/K02-frozen.json`，不是测试替身，也未重新编写其内容。

| 项目 | 结果 |
|---|---|
| 既有 reference 前完整正文 | 2941 字符 |
| 本次包含两项缺失 reference 诊断的原始正文 | 3071 字符 |
| 紧凑诊断投影 | **1490 字符** |
| 真实 schema hard limit | **2000 字符** |
| Budget | **COMPRESSIBLE / PASS** |
| 原对白 | `妈妈……先生，妈妈……` 完整保留 |
| 所有 manifest 中发送的创作字符串 | 逐项原文包含性检查 PASS |
| 原始意图文件 SHA-256 前后 | 相同：`f6e70e04f8a9ecbb9d324cfd6c9f2b3cfd38f4b9af56a3e263ed90204b20d194` |
| 完整 projection validation | **BLOCKED：REQUIRED_REFERENCE_UNFULFILLED** |
| seal / submission | 未形成真实 seal，未提交 |

1490 字符文本是**不可提交的诊断投影**，包含缺失参考说明，不能冒充已经绑定首帧的最终 Provider request。自动化测试另使用明确的模拟素材验证真实 compile 返回的完整 Vidu prompt 在上限内。

重放：

```sh
cd /Users/zy/historical-plugin
drama-mcp-service/.venv/bin/python artifacts/f01-ts01-r2/replay-s02-k02.py
```

证据：[回归结果](/Users/zy/historical-plugin/artifacts/f01-ts01-r2/S02-K02-regression-result.json)、[诊断 prompt](/Users/zy/historical-plugin/artifacts/f01-ts01-r2/S02-K02-compact-prompt-DIAGNOSTIC.txt)、[被阻断的投影与 manifest](/Users/zy/historical-plugin/artifacts/f01-ts01-r2/S02-K02-provider-projection-BLOCKED.json)。

## 7. Remaining Blocker

当前 S02-K02 仍缺少履行两项 REQUIRED reference 的真实素材/绑定：`CHARACTER / C_MAN+C_GIRL` 和 `COMPOSITION / S02-K02 opening`。长度不再是阻碍，但完整生产投影不能据此宣称 PASS。未伪造 Media、未放宽 reference 校验，也未生成首帧；后续真实素材绑定后，正式编译会对实际 reference 文本重新计数。
