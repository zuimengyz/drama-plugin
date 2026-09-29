# T3：镜头准备与阻断权治理

新镜头准备使用 `create_governed_run()`，由同一 RuntimeEngine 执行 `govern-shot:v1`。
调用者只给对象范围、模式及已有输入引用；不手工刷新 Package、推进 cursor 或修维护证据。

```python
from drama_plugin.runtime import RunMode

run = plugin.create_governed_run(
    work_id=work_id, scene_id=scene_id, shot_id=shot_id,
    mode=RunMode.EXPERIMENT,
    package_ref=existing_package_ref,  # 可省略，Plugin 自行调用 T2 ShotAssembler。
)
completed_or_waiting = await plugin.runtime.run(run.run_id)
decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
explanation = plugin.gate_governor.explain(decision)
```

T1 `inspect-work:v1`、T2 `prepare-shot:v1` 保留原版本行为与 checkpoint 身份，
供基线兼容与复测。新任务通过上述治理入口，不继续以 T2 的原始 fail-closed
AssemblyResult 作为未来生产政策。

## 六类结果与实际等待

| 分类 | EXPERIMENT | PRODUCTION |
| --- | --- | --- |
| HARD_STOP | HS1 对象/Canon、HS2 费用/授权、HS3 防重/身份、HS4 精确请求不可执行；BLOCK 风险副作用 | 相同四族，不夹带艺术质量 |
| AUTO_MAINTENANCE | 内部维护，不问用户技术问题 | 同样内部维护 |
| WARNING | 记录后继续，包括 required 质量 finding | 仅明确 required 的质量进入 REVIEW_REQUIRED，普通 optional 继续 |
| USER_DECISION | 仅 T1 五类真实决定 | 相同边界 |
| CAPABILITY_ABSENT | optional 记录继续，required 进入能力依赖等待 | 按真实交付义务判断 |
| LEGACY_GUARD | 拒绝旧新生产入口，不进入艺术审批 | 保留旧任务恢复 |

`GateFinding` 只有 code/category/owner/scope/evidenceRef/riskFamily/required；
code 的类别与风险族不能被 caller 改写。`GateDecision` 保存有界引用，
RuntimeRun 不保存 warning 正文、Canon 或新 history 容器。

治理在
[GateGovernor](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/governance/governor.py)，
动作翻译在
[GovernedPolicy](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/governance/policy.py)。
RuntimeEngine 只需支持 Policy 生成的既有动作，不识别任何具体 GateCode。

能力缺失与质量评审均使用 T1 的 WAITING_EXTERNAL，但分别采用
`capability-absence` 和 `quality-review` 引用；真实用户决定用 WAITING_USER。
不能把这些等待计成已成功。多种不同用户决定同时待决时，当前单决定步骤协调器
尚未实现，明确报告 CAPABILITY_ABSENT；不把批准艺术方案当成费用或 adoption 授权。

## T2 检查的 T3 含义

- SCOPE_MISMATCH → HS1，不额外制造一个“缺 Package”的派生硬阻断。
- VERSION_MISMATCH → AUTO，重新使用 ShotAssembler 创建新的不可变包。
- AUTHORITY_MISMATCH → HS1，不能由维护者代替合法 owner 写入或授予批准。
- MISSING_REQUIRED_SOURCE → 对当前精确输入确实必需时 HS4；可选 Lighting / Color
  来源缺失时 WARNING。既有 Package 的可选引用缺失可以记录后继续影子消费。

T2 的组装 Contract 未重写。若初始没有任何有效 Package 且原 T2 assembler 无法
形成一个包，T3 会公开说明 Package 输入尚不存在，不伪造 partial Package。
完整交付义务与能力路线的判断仍属于后续 T4/T5。

stale 重组只读已经由 owner 更新的原件与固定 pin；维护者不更新 Canon/SourcePin。
每个 run 的本地重组最多一次；原 pin 未由合法 owner 更新或维护仍不能完成，
明确报告 TECHNICAL_MAINTENANCE_EXHAUSTED，不要求用户批准 freshness。

hash/binding/receipt/checkpoint 等其他维护 owner 已映射，但没有在 T3 重写所有旧机制。
对尚未接入的维护 handler 明确报告能力缺口。Provider 接收未知必须单独产生 HS3，
不能假装普通 receipt refresh 就能安全重发。

## 内存、恢复与边界

GateFindingStore 为 IN_MEMORY_TEST_FOUNDATION，仅有不可变 finding/decision、输入引用、
最新诊断引用及有限维护计数。恢复 T3 checkpoint 时需同时保留/注入 PackageStore 与
GateFindingStore；T6 持久化未实施。T1/T2 的既有 Store 和状态枚举没有改变。

本轮没有真实 Provider submission、收费请求、媒体生成、Prompt 迁移或旧 Gate 删除。
`PRODUCTION` 模式也仍使用 T2 的 SHADOW_ASSEMBLY_ONLY Package 边界。

离线入口：

```bash
PYTHONPATH=plugin/src .venv/bin/python -m pytest -q plugin/tests/test_gate_governance.py plugin/tests/test_runtime_engine.py plugin/tests/test_production_package.py
PYTHONPATH=plugin/src .venv/bin/python plugin/integration/gate_governance_shadow.py --output /private/tmp/t3-shadow.json
```

[实施报告](/Users/zy/historical-plugin/未来架构/迁移/T3-GateGovernance-Implementation-Report.md)与
[旧检查映射](/Users/zy/historical-plugin/未来架构/迁移/T3-Current-Gate-Mapping.md)
记录实际接入范围、真实镜头证据与尚未迁移项。STOP AT T3。
