# F01-TS01-R5 — Complete Route Cost Minimal Fix

## 1. Root Cause

现有 `Cost.components` 只有金额或 `None`，无法表达不同成本 authority；资格和 reservation 均将任何 `None` 视为未解析。生产脚本因 Comfy 不包含 runtime/storage，把 `addons` 留为 `None`，只能阻断。代码并非显式检查“每项都是 Provider Quote”，但缺少内部已解析成本的表达路径，导致同样结果。

## 2. Files Changed

- `src/drama_plugin/visual/video_selection.py`：最小 `CostResolution`、逐项 evidence 校验、成本汇总及分类输出。
- `src/drama_plugin/visual/production.py`：reservation 识别已解析的 unmetered 项，保留预算门禁并要求覆盖所有已解析计费金额。
- `tests/test_cost_authority.py`：8 项必要测试；本报告。
- workspace `artifacts/f01-ts01-r5/replay-cost.py`、`result.json`：真实七镜只读回归及证据。

## 3. Cost Authority Classification

复用 `components` 的金额、unit 和现有带有效期的 `Evidence`，新增可选逐项 `resolutions`：

| Authority | 金额与证据要求 |
| --- | --- |
| PROVIDER_QUOTE | Provider 报价金额及有效证据 |
| INTERNAL_FIXED | 内部固定金额及有效策略证据 |
| INTERNAL_UNMETERED | 金额必须为 `null`；需有效的内部不单独计费依据 |
| EXTERNAL_METERED_UNKNOWN | 始终未解析；即使填入 0 仍阻断 |

启用分类后，所有 component 都必须有 resolution，并显式包括 runtime/storage。缺失、未验证或过期证据仍阻断。旧有无分类记录保持原金额校验。系统不会仅凭 endpoint 或余额自动推断 unmetered。

## 4. Old Validation

全部 component 必须是非负确定金额，否则 complete cost 不成立；reservation 也拒绝任何 `None`。

## 5. New Validation

所有 component 均由各自有效 authority 解析后，只有实际计费金额参与合计；unmetered 不生成虚假 0 报价。资格输出及 sealed candidate 分别保留 Provider 金额、内部固定金额、unmetered 项及证据。未知成本门禁、quote 请求指纹和累计预算门禁继续有效。reservation 不能只覆盖 Provider 金额而遗漏内部固定成本。

没有修改 Provider quote、模型、projection、duration、资产、剧本或 2000 credits 授权。

## 6. Tests

**208 passed**，包括本轮 8 项成本测试及 production route、selection、Vidu/Seedance reconciliation、MCP execution、Clip duration 回归。

覆盖 Provider Quote + 两项有证据 unmetered 通过；外部未知/缺失/过期证据阻断；unmetered 不报告为 Provider Quote=0；Provider 金额原样保留；sealed candidate 保存分类；reservation 覆盖内部固定成本；2000 credits 累计预算超限仍拒绝。两处源文件 mypy、`git diff --check` 均通过。

测试里的内部策略证据明确标注为离线夹具，不作为真实部署计费结论。

## 7. S02 Seven-Clip Regression

使用保存的 `full-route-preflight-input.json`、`current-production-inspection.json`、`user-S02-budget-authorization.json` 回归：

- 七镜非成本资格 **PASS**；保存时点完整资格仅因 `COMPLETE_ROUTE_COST_UNRESOLVED` 阻断。
- 保存的 Comfy 报价：12s=152、14s=177、16s=203 credits，原始响应保留未改写。路线原规划 video envelope=1421 也未修改，未将其称为实际 Provider 总报价。
- 已识别原 **2000 credits** 授权，未重新请求或扩大授权。
- 三个输入文件前后 SHA-256 相同；收费调用 **0**。未伪造新的真实 quote 或可提交 sealed request。

复现命令（workspace 根目录）：

```sh
drama-mcp-service/.venv/bin/python artifacts/f01-ts01-r5/replay-cost.py
```

## 8. Remaining Blocker

真实 runtime/storage 的内部成本依据不足，故保留 **COMPLETE_ROUTE_COST_UNRESOLVED**。

Comfy 原响应排除 GPU/queue time 和 storage，并不证明这些成本不存在。`MediaStorageConfig` / `MediaStorageProperties` 只证明使用配置的 S3-compatible 服务，现有 service 配置没有找到 billing/unmetered/cost-policy 声明；远端 MinIO/S3 endpoint 本身不能证明免费或固定成本。现有证据也不足以断言必然存在外部按量计费，因此真实报告保留 authority 未确定、resolved=false，而非猜测分类。

合同修复已完成；没有为取得 PASS 编造内部策略或价格。按任务要求在此停止。
