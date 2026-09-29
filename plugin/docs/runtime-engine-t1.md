# T1：Plugin 自有运行时 Foundation

T0 开发约束见仓库根目录 [AGENTS.md](../../AGENTS.md)。正式基线为 `master`。
目标设计保存在上层工作区的 `未来架构/`；本实现只到 T1。

`DramaPlugin.runtime` 是新的流程推进核心。调用者创建一个目标运行，再调用
`await plugin.runtime.run(run_id)`。引擎根据内部注册的 workflow、模式政策和检查点
自行计算下一步，调用迁移桥、记录引用结果并继续，直到完成或明确等待。
默认仅注册 `inspect-work:v1`，经现有 `work.get_work` 读取原件并返回 ID/version 引用。

```python
from drama_plugin.runtime import RunMode

run = plugin.runtime.create_run(work_id="已有作品ID", mode=RunMode.EXPERIMENT)
result = await plugin.runtime.run(run.run_id)
snapshot = plugin.runtime.serialize(run.run_id)
```

`EXPERIMENT` 与 `PRODUCTION` 具有不同的政策身份，使用同一引擎。T1 不迁入现有
Gate policy。workflow 在 Plugin 代码中一次注册，不要求 Host 每一步指定工具。
新能力经 `CapabilityExecutor` 显式接入；`LegacyCapabilityBridge` 标记为
`MIGRATION_ONLY`，没有任意工具透传。默认未注册生成、写入或 Provider 提交能力。

状态只有编排意义。Run 保存对象身份、政策/workflow 指纹、游标、有限重试计数、
最后一次引用结果与等待原因；不存 Work/Script/Scene/Bible/Prompt 正文或完整历史。
workflow 指纹复用现有 canonical hash 工具，不建立新的 SourcePin / receipt 系统。
用户决定只有艺术、费用、重大改编、正式采纳和最终验收；内部维护和重试不属于用户决定。

持久化是 `IN_MEMORY_TEST_FOUNDATION`，只支持同进程/事件循环内共享 Store 的串行推进。
序列化/恢复是显式合同检查点，不是磁盘持久化。恢复 RUNNING 时进入内部 BLOCKED，
不会盲目重发；仅声明 replay-safe 的能力可在次数边界内重试。这里没有真实 Provider
submission，故不引入 UNKNOWN 状态；未来接入时必须仅用于服务接收与否不明。

离线 fixture 可复现：

```sh
# 在 drama-plugin 仓库根目录；使用项目已安装依赖的虚拟环境
.venv/bin/python plugin/integration/runtime_engine_offline.py
.venv/bin/python -m pytest plugin/tests/test_runtime_engine.py -q
```

默认 fixture 显式使用 mock 配置并拒绝网络；只读现有工具，不生成媒体、不写正式原件。
旧 Host/Gate/Skill/Provider 与工具注册项保持原有执行路径。ProductionPackage、
ShotAssembler、持久台账及真实生产路由仍待后续阶段。
