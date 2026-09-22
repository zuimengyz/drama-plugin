# F01-TS01-R4 — ProductionRoute Clip Duration Minimal Fix

## 1. Root Cause

`qualify_route` 将每个 frozen Clip 的 duration 与路线样例 duration 强制相等；decision seal、重放及 reservation 的 candidate 比较也将 duration 参数视为不变量。合法的 14s → 16s 因而被误判为路线改变。

## 2. Files Changed

- `src/drama_plugin/visual/video_selection.py`：逐 Clip capability 检查；路线参数比较仅允许合法 duration 变化。
- `src/drama_plugin/visual/production.py`：reservation 复用同一比较，检查 Clip duration 属于路线 capability。
- `tests/test_route_clip_duration.py`、`tests/fixtures/route-duration/S02-adjacent-route.json`：最小测试及保存的真实路线夹具。
- 本报告；workspace `artifacts/f01-ts01-r4/replay-route.py` 和 `result.json`：只读真实回归证据。

## 3. Old Validation

`clip.duration == route.requirements.duration_seconds`，且 candidate 的全部 parameters 必须完全相等。

## 4. New Validation

每个 frozen Clip 的 duration 必须属于现有 `Candidate.durations`。超出范围返回 `CLIP_DURATION_OUT_OF_ROUTE_CAPABILITY`；真正的 work/shot scope 变化继续原有阻断。

现有 adapter 的 `duration` / `model.duration` 参数允许在路线支持值中变化；参数键集合、其他参数、model、variant、mode、template、graph、adapter、capability 仍按原合同比较。路线对象和指纹不需要为 14s → 16s 改写。

Clip 精确 duration 继续进入原有 Requirements、Provider 编译、sealed request 和 MCP input_overrides。报价仍绑定完整 request fingerprint；预算/reservation 算法未修改。原有 2000 credits 批准未改写、未重新请求授权。

## 5. Tests

**230 passed**：新增最小测试及 production route、selection、Vidu/Seedance reconciliation、MCP execution、cinematic direction 回归。覆盖：

- 同一路线 14s / 16s 通过，17s 被拒绝；真实 scope 改变仍阻断。
- 同一路线指纹下分别封存 14s / 16s，MCP 参数保留精确时长。
- 离线 quote 使用各自 request fingerprint 和时长；将 14s quote 用于 16s 被拒绝；累计预算超限被拒绝。
- resolution 等其他路线参数变化仍被拒绝。

报价金额使用明确标注的离线测试值，不代表真实 Provider 报价。两处修改的源文件 mypy 与 `git diff --check` 通过。

## 6. S02-K02/K03 Regression Result

对保存的正式 frozen K02/K03 和 `adjacent-route-preflight-input.json` 重新执行资格检查：**K02 14s PASS；K03 16s PASS**（时长 capability / 路线身份门禁）。原 route 和 frozen 文件 SHA-256 保持不变；scope 负向对照仍返回原错误。

复现命令（workspace 根目录）：

```sh
drama-mcp-service/.venv/bin/python artifacts/f01-ts01-r4/replay-route.py
```

真实数据的完整资格结果仍为 `eligible=false`，原因见下节。精确时长 quote/seal 链路已用现有真实 MCP schema 的离线测试验证；未伪造真实报价或可提交封存，未调用收费生成。

## 7. Remaining Blocker

保存的 preflight 本身保留 `UNVERIFIED_OR_EXPIRED:official`、`COMPLETE_ROUTE_COST_UNRESOLVED`。这些与 duration 无关，本轮未补齐、未绕过，也未扩大审计。时长误阻断修复完成后停止。
