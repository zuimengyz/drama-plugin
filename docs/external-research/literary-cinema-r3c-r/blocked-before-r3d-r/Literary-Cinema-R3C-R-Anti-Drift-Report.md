# Literary Cinema R3C-R — Anti-Drift / Runtime Blocker Report

## Outcome

**R3C_R_BLOCKED_BY_RUNTIME**。依据用户任务第 50 节：发现 R3D / R3B-R Runtime bug 即 STOP，不边改创作边改 Gate。本轮完成解释批准后，在改正文前的专业链路预检中停止。

## R3CR-RT01 — Specialized Asset drops trusted interpretation approval context

| 对照 | 实际结果 |
|---|---|
| 既有未 opt-in SpecializedAssetBible 的真实 validate_assets | PASS |
| 同一 Character Bible 增加有效 InterpretationUse，绑定精确合法 receipt；直接 validate_bible(..., approved_interpretation_refs=...) | PASS |
| 当前 SpecializedAssetHost.submit(candidate, current=...) | FAIL: USER_INTERPRETATION_APPROVAL_REQUIRED |
| 尝试向该入口传递同一批准上下文 | TypeError: unexpected keyword argument 'approved_interpretation_refs' |

复现使用独立临时目录内的既有离线 fixture，fixture 自审/审批不是当前作品的用户批准，也不生成当前人物外观。真实用户收据已独立在当前作品的 interpretation-approved.json 中落盘。复现没有 monkeypatch、删除依赖、改 Gate 或调用 Provider。

原因已经核对当前源码：

- [SpecializedAssetHost.submit](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/hosts/specialized_asset.py:73) 只有 current，没有批准上下文入口；直接调用 validate_assets。
- [validate_assets](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/specialized_asset.py:85) 进入既有角色/Director上游校验。
- [upstream](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/specialized_asset.py:78) 调用 validate_bible 时丢失批准上下文。
- [validate_bible](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/professional.py:206) 的 approved_interpretation_refs 默认空，因此 [approved_interpretation](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/interpretation.py:124) 正确执行安全边界，却拒绝本来有效的已批依赖。

因此这不是需要用户再次批准，也不是剧本措辞问题。任务要求 Costume / Specialized Asset 实际承接批准的 Character State，但该正式入口无法接收所需信任上下文。只导出一般 JSON 或删掉 InterpretationUse 会伪装完成，不能采用。

这是上一轮 R3D 的跨入口集成缺口；R3D 的通用 handoff/CreativeRecord 测试通过不等于具体 Specialized Asset 入口完成传递。该缺口不推翻既有 vocative/self-directed 修复，不能靠改它们解决。

**修复归属：Runtime integration owner，Specialized Asset / professional approval-context propagation。** 后续独立 Runtime 修复应保留 Host 信任边界，并验证 submit、compile、department_records 及其下游原件重放；本轮未执行这些修改。

## Anti-drift answers

| 问题 | 本轮证据 |
|---|---|
| 为 interpretation 加入不必要象征？ | 未改正文，未增加象征 |
| 为 Gate 新增 Beat？ | 没有；未生成新 DPD |
| 为星重要强行重复星？ | 没有 |
| 将 OPEN 写成答案？ | 没有；I-OPEN/H-S5 为 PRESERVE_AMBIGUITY，H-S3/H-S4 仍 OPEN |
| 文学解释直接塞进 Prompt？ | 没有；本轮未生成 Prompt 或 IR。不是本轮 Prompt 隔离测试 PASS 的宣称 |
| 部门各拍各的作品？ | 新专业 HOW 尚未生成，跨部门艺术一致性未评估 |
| Runtime / Gate 是否修改？ | 0；只新增审批、诊断及报告文件 |
| 媒体生成 / 付费调用？ | 0 |

[机器证据](runtime-blocker-evidence.json) · [复现脚本](reproduce_runtime_blocker.py) · [完整性证据](source-integrity.json)。
