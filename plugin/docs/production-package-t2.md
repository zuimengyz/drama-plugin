# T2：镜头生产输入准备

Plugin 的 `prepare-shot:v1` workflow 由 RuntimeEngine 自行推进：

```text
create_run → RuntimePolicy → production.assemble_package:v1
           → ShotAssembler → ProductionPackageStore → PackageRef
           → production.inspect_package:v1 → SUCCEEDED
```

调用者只提供对象范围与模式。专业原件目录是 Plugin 初始化时注入的存储配置，
镜头调用者不选择 Camera / Lighting / Performance 文件，也不手工组装或保存 Package。

```python
from pathlib import Path
from drama_plugin import DramaPlugin
from drama_plugin.runtime import RunMode, RuntimeState

async def prepare(plugin: DramaPlugin,
                  work_id: str, scene_id: str, shot_id: str):
    run = plugin.runtime.create_run(
        work_id=work_id, scene_id=scene_id, shot_id=shot_id,
        mode=RunMode.EXPERIMENT, workflow_id="prepare-shot:v1",
    )
    completed = await plugin.runtime.run(run.run_id)
    if completed.state != RuntimeState.SUCCEEDED:
        return completed  # 内部诊断引用指出缺项的 domain / owner / artifact。
    return completed.last_result.artifact_refs[0]

# 在应用初始化时调用 DramaPlugin.load(plugin_root,
#     production_artifact_roots=(professional_root,))。
# prepare(plugin, ...) 的调用只给 scope；保留该 Plugin/Store 供后续 consumer 解析 Ref。
```

`PRODUCTION` 使用同一实现。本轮两种模式均限定 `SHADOW_ASSEMBLY_ONLY`，
`providerSubmissionAllowed=false`；模式名称不能授予真实生成权限。

## 职责与 Contract

[ShotAssembler](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/production/assembler.py:34)
是唯一组装 owner，读取已存在的批准事实与显式关系，不创作内容、不解释人物心理，
也不调用旧 Projection、Prompt 或 Provider。RuntimeEngine 只接收 Scope、状态和引用。

[ProductionPackage](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/production/contracts.py:118)
采用冻结 Contract，拒绝未知字段和任意扩展容器。最小结构是
`schemaVersion / scope / sources / obligations / generationIntent / boundary / packageId / fingerprint`。
`sources` 是领域分类的有界引用数组，不是整个 Professional registry 的展开。

来源引用是 `owner / artifactRef / version / fingerprint / path`。`path` 是原件内字段路径，
不能表示任意文件路径；原件正文仍由原 owner 持有。旧 Scene / Shot 没有版本字段，
诚实保留 `version=null` 并固定内容哈希，不能捏造版本号。

相同来源、版本、Shot scope、执行要求与明确模式/政策引用产生相同内容身份；
Run ID、运行时间和临时地址不进入身份计算。修改原件后旧包不变，重新组装得到新包。
内部 `validate_sources()` 可报告旧引用已变化，不构成新生产 Gate。

## 迁移读取与选取

[LegacyAssemblySources](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/production/sources.py:41)
显式标记 `MIGRATION_ONLY`，只允许五个 Canon read 和已配置 owner 根目录的 keyed Bible read。
Scene → Episode → Script → Work 与 Shot → Scene 必须一致。专业数据从 Shot 的现有
`departmentRefs` 出发，并按 coverage、camera、beat、subject、spoken-content、reference
显式关系选择。`NOT_REQUIRED` 和未声明的部门不生成空字段。

旧 Action Bible 缺少 action-to-beat 关系时，只引用其共享场景约束；当前动作仍来自
Shot 的 `subjectAction`。这不会把场景中的所有动作声明为本 Shot 执行动作。

缺必要原件、范围/版本/Authority 不一致时返回 `UNRESOLVED + domain + owner + artifact`，
原生能力保留小型诊断引用并让 T1 Runtime 进入内部 `BLOCKED`；本轮没有自动创作修复、
用户审批 Gate 或新的 Runtime 状态。

## 内存恢复边界

[ProductionPackageStore](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/production/store.py:9)
是 `IN_MEMORY_TEST_FOUNDATION`，既不拥有创作 Authority，也不是 Production Ledger。
恢复 Runtime checkpoint 时保留/注入同一个 Store，或先将已验证的 Package JSON 放回
Store；同一 PackageRef 可传入后续只读 consumer，已完成的组装步骤不会重放。
丢失 Store 时返回 `PACKAGE_STORE_RESTORE_REQUIRED`，不会倒退 cursor 或重造 Package。
长期持久化仍属于 T6。

## 离线验证入口

在仓库根目录 `/Users/zy/historical-plugin/drama-plugin` 执行：

```bash
PYTHONPATH=plugin/src .venv/bin/python -m pytest -q plugin/tests/test_production_package.py plugin/tests/test_runtime_engine.py
PYTHONPATH=plugin/src .venv/bin/python plugin/integration/production_package_shadow.py --output /private/tmp/t2-shadow.json
```

第二个入口读取本地现有旗舰 S02-K02 快照，并禁止网络、旧 Prompt projection 和生成调用。
默认 fixture 路径、Package、来源哈希、对照与恢复证据见
[T2 实施报告](/Users/zy/historical-plugin/未来架构/迁移/T2-ProductionPackage-Implementation-Report.md)。

STOP AT T2：旧 Gate、Professional DAG、旧 Prompt / Provider 入口保持原状；本轮没有真实生产。
