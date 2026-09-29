# T4 Professional Design 引用接口

新的镜头准备继续使用 T3 `create_governed_run`。Runtime 自动调用 ShotAssembler；
组装器通过唯一 ProfessionalDesignResolver 读取当前 Shot 的专业原件引用。
Host 只提交对象身份和模式，不指定 Camera/Lighting/Performance 部门或文件。

```python
from drama_plugin.runtime import RunMode

run = plugin.create_governed_run(
    work_id=work_id, scene_id=scene_id, shot_id=shot_id,
    mode=RunMode.EXPERIMENT,
)
done = await plugin.runtime.run(run.run_id)
package = plugin.production_packages.get(done.last_result.artifact_refs[0])
```

若只查询已有包对应的专业需求与权威引用，可以使用同一只读接口：

```python
from drama_plugin.professional_design import ProfessionalDesignRequest

selection = await plugin.professional_design.resolve(
    ProfessionalDesignRequest(scope=package.scope)
)
print(selection.domains, selection.status)
```

`domains=()` 表示沿当前 Shot 已声明引用选择，并保留 T2 的核心来源要求；
不表示展开全部平台注册能力。显式 `domains=(SourceDomain.CAMERA,)` 只查询摄影领域。
选源请求只含三种 scope refs 和至多 11 个既有专业领域，没有创作正文或 registry。

ProfessionalDesignSelection 是瞬态、不可变、extra-forbid 的 domains/sources/issues。
sources 复用 T2 DomainReference：domain、reference、use；原件正文仍在原 owner。
status 为 RESOLVED/MISSING/CONFLICT，不授予 STOP 权，也不生成 required/optional 政策。
原 T2 core 最小要求只在 MIGRATION_ONLY 内部适配中保留，未增加新义务。

恢复/新包校验使用 ProfessionalReferenceCheck：scope + 至多 64 条领域引用。
同次校验内同一版本原件只读取一次；缓存不跨调用，后续修改仍会被识别。
地址从当前 Shot 绑定定位，冷恢复不扫描整个 Bible 目录。

唯一部门→领域映射在 professional_design/catalog.py。LegacyProfessionalDesignSources
仅调用原有限定 Canon reads 与 keyed Bible read；不执行 authoring DAG、Skill、Host
任务、Provider 或 Prompt。Historical/Literary 共用一个 Resolver，没有第二套 facade。

创作内容、正式 owner 与批准权限保持不变；不会自动写 pin、修摄影、补表演或合并
艺术冲突。缺项仍经 AssemblyValidation → T3 GateFinding/GateGovernor。
已有包的可选 Lighting/Color 缺失按 T3 Experiment WARNING 继续；错误 scope 为 HS1。
原 T2 初次组装 Contract 仍严格，无法形成合法包时如实返回 unresolved，不伪造 partial 包。

T1/T2/T3 workflow、Policy ID、ProductionPackage schema/fingerprint、恢复 Store 均保持
原契约。ShotAssembler 构造增加注入的 Resolver；DramaPlugin 在组合根中创建唯一实例，
应用调用 DramaPlugin.load 无须新增参数。未新增 Skill、数据库表或长期专业存储。

完整实施与映射见：

- [T4 实施报告](/Users/zy/historical-plugin/未来架构/迁移/T4-ProfessionalConsolidation-Implementation-Report.md)
- [完整 Current → Target 映射](/Users/zy/historical-plugin/未来架构/迁移/T4-Professional-Current-to-Target-Mapping.md)

STOP AT T4；不提交 Provider，不生成媒体，不 commit / push / merge。
