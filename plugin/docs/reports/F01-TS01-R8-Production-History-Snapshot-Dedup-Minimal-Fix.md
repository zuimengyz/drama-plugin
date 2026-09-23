# F01-TS01-R8 — Production History Snapshot Deduplication

## 1. Root Cause

每次 attempt 内联 `frame_snapshot`，每次 remediation 内联 `previous_frame`；完整编译件含 IR、资产回执、authority 和 source mapping。同一版本在多条历史记录中重复保存，随 Work 全量替换请求反复发送。`route_revisions.previous_route` 也内联完整路线。

## 2. Files Changed

- 新增 `visual/history.py`：内容哈希引用、解析、旧格式转换与去重。
- `visual/production.py`：新 attempt/retry/remediation 保存引用；更换 canonical Frame 前保留旧版本；本地保存前转换旧历史。
- `hosts/route_production.py`：正式保存前转换历史；route revision 引用化；读取历史 frame/route。
- `hosts/http_video.py`、`hosts/visual_delivery.py`、`hosts/mcp_execution.py`、`hosts/sequence_execution.py`、`providers/video/comfy.py`：从引用读取正确版本。仅调整内部读取，不改变 Provider 参数或 MCP 传输协议。
- 新增 `tests/test_production_history.py`；四个既有测试文件改用引用读取。

## 3. Old Representation

`attempts[].frame_snapshot = FULL_FRAME`；`remediations[].previous_frame = FULL_FRAME`；`route_revisions[].previous_route = FULL_ROUTE`。

## 4. New Reference Representation

使用现有 `sha256_canonical`，对完整对象取内容哈希：

- `attempts[].frame_ref`，继续保留原 `frame_fingerprint`。
- `remediations[].previous_frame_ref`，继续保留原 previous/result fingerprint 和修复记录。
- `route_revisions[].previous_route_ref`，继续保留原 next_route_id 等元数据。

当前版本只在 `productionStage.frames` / `production_route` 中保留。不同的历史版本分别在同一 stage 的 `history_frames[hash]` / `history_routes[hash]` 中各保存一次；不会删除旧版本。保存前剔除档案区与当前 canonical 对象的相同副本。

`attempt_frame(stage, attempt)` 与 `resolve(stage, ref, kind)` 校验哈希后解析。比较 frame_ref 与当前完整 Frame 哈希即可判断是否同一版本；原 revision 信息仍在对应编译件中。缺失/篡改引用明确报错，不回退到最新 Frame。

## 5. Backward Compatibility

旧 inline snapshot 继续可读，下次正常保存时转换，无须先运行全库迁移。转换幂等，失败不部分改写 state。新引用格式必须连同所属 stage 解析；脱离 stage 的 MCP/Sequence/Comfy 调用可传入新增的可选 `state` 参数，旧 inline 调用仍兼容。

HTTP Host 的临时执行视图按需展开 snapshot，不把展开副本写回历史。原本没有 snapshot/ref 的老审计条目保持原状，不凭空补造来源；需要执行/交付的历史对象必须能解析。预算、retry 次数、request、task receipt 和历史事件没有删除或重置。

## 6. Tests

相关回归 **241 passed**，八个改动源文件 mypy 通过，`git diff --check` 通过。

覆盖同 Frame 多 attempt、重复 previous frame、多版本解析、旧 inline 转换、幂等性、引用冲突/篡改/缺失、增长回归，以及 archived Frame 的 MCP 提交与重复提交阻断。原有 no-media recovery、HTTP 生命周期、交付、continuation、route 和 replan 测试通过。

## 7. Before / After Request Size

对保存的真实 `r10-request-body/reconstructed-request.json` 离线重放。采用与原文件相同的紧凑 UTF-8 JSON 序列化，基线精确复现 4,592,877 bytes。

| 字段 | Before bytes | After bytes |
| --- | ---: | ---: |
| total request | 4,592,877 | 2,599,870 |
| productionStage | 4,257,657 | 2,264,650 |
| attempts | 1,677,960 | 63,409 |
| remediations | 1,581,667 | 3,407 |
| route_revisions | 483,360 | 781 |
| frames | 416,070 | 416,070 |
| history_frames | 未存在 | 1,199,077 |
| history_routes | 未存在 | 483,270 |

净减少 **1,993,007 bytes（43.4%）**。档案区费用已计入 After 总量，没有把转移的对象当成删除收益。

5 条 attempt、7 条 remediation、5 条 route revision 全部保留并逐条回放一致；4 个不同旧 Frame 和 5 个不同旧 Route 各保留一份。canonical Frame、plan fingerprint、原 attempt 其他字段完全一致。原始证据文件未修改。

追加同一版本的 20 组模拟 attempt/remediation 后增长 **121,030 bytes**，其中保留了每条 attempt 的原 Provider request；历史对象区增长 **0 bytes**，不再复制完整 Frame。

证据：`/Users/zy/historical-plugin/artifacts/f01-ts01-r8-history-dedup/` 中的 `result.json`、`compacted-request.json`、`replay.py`。仅离线重序列化；没有调用真实 `work.save_work` 或收费生成，因此不声明服务器已接受剩余请求体。

## 8. Remaining Large Fields

最大剩余项是不同旧 Frame 的档案（1,199,077 bytes）、不同旧 Route 的档案（483,270 bytes）及当前 canonical Frame（416,070 bytes）。这些是仍需重放的不同版本；尤其本样本的五个旧 Route 均不同，引用化本身不减少其内容，只避免以后相同版本重复内联。

当前完整请求仍约 2.60 MB。本轮不继续拆分 persistence、不删除 evidence、不提高 HTTP body limit、不修改 Prompt/IR/authority/预算/重试策略，也不执行新的收费任务。
