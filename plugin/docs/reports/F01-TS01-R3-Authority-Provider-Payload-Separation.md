# F01-TS01-R3 — Authority / Provider Payload Separation

## 1. Root Cause

`bind_video_request` 将资产 compilation 全文拼入 prompt；`validate_visual_submission` 再以全文子串证明资产消费。内部权威证据因此占用模型执行预算。S02-K02 的 5 项资产全文共 9736 字符，不能附加到 Vidu 的 2000 字符 prompt 中。

## 2. Old Flow

已批准资产 → 完整资产文本追加到 prompt → 全文子串校验 → Provider 请求。1490 字符执行文本追加资产全文及分隔符后达到 11231 字符。

## 3. New Flow

已批准资产 → 原有来源、审批、当前版本和 compilation 重放校验 → 独立 `authority_context` → 必要资产语义投影 → 原有 Prompt Budget → Provider 请求。

内部 context 保留完整 Creative Intent、所有必需资产 receipt、asset ID/type、compiled-from pin、fingerprint、source map 和 Work authority snapshot。校验时重新从权威 store 编译并精确比较，而非信任调用方填写的 hash。正式提交门禁再次使用当前 Work 校验。

Provider prompt 只增加有精确来源映射的连续性语句：CHARACTER 优先 visual_continuity，COSTUME 优先 continuity，SCENE 优先 environment_continuity；缺少这些字段时分别回退到既有 face/body、garment_structure/material、architecture 字段。无可映射字段则阻断。角色标签与资产类型保留。完整人物外观仍依赖必需参考素材绑定；本轮不豁免该门禁。

`Requirements.authority_context` 和 typed `VideoRequest.authority_context` 是内部材料；现有 Provider adapter 仍只序列化其显式执行字段。Cinematic projection 在渲染前重放 context，输出只包含 context fingerprint 和短语义。图像/casting 原有合法校验链保留。未修改压缩器、模型限制、资产、剧本或 Director。

## 4. Files Changed

- `src/drama_plugin/hosts/specialized_asset.py`：context 编译、重放验证、短语义派生；替换视频全文拼接/消费判断。
- `src/drama_plugin/hosts/cinematic_projection.py`：投影前验证、短语义预算、context fingerprint。
- `src/drama_plugin/hosts/route_production.py`：将内部证据与完整意图传给现有正式提交门禁。
- `src/drama_plugin/contracts/video.py`、`visual/video_selection.py`：内部 context 字段。
- `tests/test_authority_provider_separation.py`、`tests/fixtures/authority-provider/S02-K02-authority.json`：真实资产链与负向测试。
- 本报告；workspace `artifacts/f01-ts01-r3/`：只读回归脚本及分离后的诊断证据。

## 5. Validation Evidence

新增测试覆盖：9736 字符权威全文与短 prompt 同时通过各自校验；缺失/篡改 asset、hash、sourceMap、compiledFrom、原文、意图或短语义均失败（包括重算外层 hash）；正确外观的 prompt 不能代替证据；必要短语义保留；完整资产全文不进入 Provider prompt；污染全文仍被预算拒绝；HTTP adapter 不发送 context；图像及 typed video 合法链回归。

相关 cinematic、Prompt Budget、Vidu/Seedance reconciliation、selection、production 测试组 **234 passed**；权威资产和官方 Provider 测试组 **107 passed**（两组共有本轮新增的 12 项测试，共 329 项不同测试）。5 个修改的 Python 源文件 mypy 通过，`git diff --check` 通过。

## 6. S02-K02 Regression

使用保存的正式 Work、K02 frozen intent、production-authority 原始对象及已捕获真实 MCP node schema 重放；未调用生成接口。证据位于 workspace `artifacts/f01-ts01-r3/result.json`，复现命令（workspace 根目录）：

```sh
drama-mcp-service/.venv/bin/python artifacts/f01-ts01-r3/replay-s02-k02.py
```

- 5 项资产，全文 9736 字符；Authority Validation **PASS**。
- 保留全部投影到 PROMPT 的创作字符串与资产短语义；Prompt Budget **PASS**。
- frozen intent、正式 Work、权威 store JSON 文件前后 SHA-256 一致。
- `authority-context.json` 与 `provider-payload-DIAGNOSTIC.json` 分开保存；没有 sealed request 或收费调用。

## 7. Final Provider Prompt Length

**1726 / 2000 characters**。在此前 1490 字符基础上加入 236 字符资产连续性标签和短语义。限制来源为保存的真实 `runtime_node_schema`；完整 prompt 已包含包装文本，reserve=0。完整权威全文不计入模型预算。

## 8. Remaining Blocker

完整 Projection Validation 仍为 **BLOCKED**：`REQUIRED_REFERENCE_UNFULFILLED`。C_MAN/C_GIRL 的 CHARACTER reference 与 S02-K02 opening COMPOSITION reference 尚未绑定实际 Media；`validate_projection` 返回 `EXECUTION_CRITICAL_UNSUPPORTED`。本轮已解除权威全文与 prompt 的错误耦合，保留该独立门禁并停止，没有将诊断结果标为可提交。
