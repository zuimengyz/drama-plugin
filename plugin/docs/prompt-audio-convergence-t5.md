# T5：镜头生产表达 Foundation

唯一 Target workflow 是 `prepare-generation:v1`。Host 仅提供 Work、Scene、Shot、RunMode；
Plugin 通过既有 ShotAssembler / ProfessionalDesignResolver 准备 Package，经 T3 政策编译
Target PromptIR、独立 AudioExecutionPlan 和不可变 FinalPromptArtifact。

```python
from drama_plugin.runtime import RunMode

run = plugin.create_generation_run(
    work_id=work_id, scene_id=scene_id, shot_id=shot_id,
    mode=RunMode.EXPERIMENT,
)
completed = await plugin.runtime.run(run.run_id)
# 成功结果：FinalPromptRef、AudioPlanRef、GenerationPreparationRef。
# GenerationPreparation.readiness == "READY_FOR_PROVIDER"
# GenerationPreparation.provider_submission_allowed is False
```

当前默认任务是 `VIDEO / seedance-2-standard / OPTIONAL native audio`；输入模式由当前 Shot
已登记的 required execution binding 机械决定，没有 binding 时为 text_to_video。
可通过有界 `GenerationTask` 显式选模型/输入模式/声音要求。模型生成器不存在返回
CAPABILITY_ABSENT。T5R 新增 source binding 后，reference/image/first_last_frame 可解析
已审核真实媒体；只有 design reference、没有真正 required 媒体时仍由 T3 判 HS4。
同一张图的两人身份通过原 Seedance generator 的 joint subjects 语法映射，不复制 generator。

服务启动时注入 `reference_execution_store=ReferenceExecutionStore()`；由已有 owner 登记
已审核 `ReferenceExecutionBinding`，内部复用 VideoReference / ReferenceRequirement。
这属于配置读取服务，不是 Host 在每个任务手工构造输入。ShotAssembler 将该 Shot 的
binding 纳入 Package REFERENCE refs；Compiler 仅按授权 ref 与 media.get_media(bound ID)
读取。没有 URL、Provider slot、media bytes 或旧 spec/prompt/request side-load。

下游唯一入口 `PromptCompiler.compile(package_ref, task)`。PackageReader 仅解析 Package
选中的来源及其明确带 hash 的 DPD / asset compilation 依赖；不读取完整批准 Scene、
Work Prompt history，不调用旧 Host 或 Professional DAG。有限字段投影只翻译已写明的
执行事实，缺 Camera/action/world 等必需输入返回 owner，不补创作。

Target IR 通过一个临时结构视图交给原 Seedance2PromptGenerator。没有第二个 Seedance
生成器。真正 hard limit 来自现有视频能力目录；可选项按政策省略，required 不静默删。
最终文字仅由 FinalPromptArtifact 持有；ExactPromptTransfer 返回原字符串。
本阶段没有接入任何 Provider 传输入口，也没有声称旧 Adapter 已迁完。

AudioPerformanceAssembler 引用 Scene spokenContent 和当前 Shot 绑定。精确文字属于原
Scene；计划不存文字。三层人声和六种时间关系必须来自 Sound/Performance 原件；
仅一个明确 mustKeep 的句子可以直接形成 PRIMARY，不需要发明跨句排序。多句缺少
作者关系会返回 CREATIVE_SOURCE_INSUFFICIENT。Native audio 是一个 consumer，TTS
当前没有 Target 执行能力；video-only/非必需 TTS 不因此阻断。字幕仍为能力缺口。

RuntimeEngine、ShotAssembler、GateGovernor 未加入 Prompt/Audio 业务逻辑，也未新增
RuntimeState。GenerationPolicy 仅消费既有 GateEffect，内部维护不要求用户批准。
末端 READY 再检查原件引用及编译依赖，stale 自动重组/重编译最多一次。

所有 Store 均为 `IN_MEMORY_TEST_FOUNDATION`。检查点恢复要复用 ProductionPackageStore、
GateFindingStore、GenerationArtifactStore 和当前已审核 ReferenceExecutionStore；已经完成的组装/生成不重放。该验证不是磁盘
crash recovery、跨进程去重或付费 exactly-once；长期存储属于 T6。

离线检查：

```sh
PYTHONPATH=plugin/src .venv/bin/python -m pytest -q plugin/tests/test_prompt_audio_convergence.py
PYTHONPATH=plugin/src .venv/bin/python plugin/integration/prompt_audio_convergence_shadow.py \
  --output /Users/zy/historical-plugin/未来架构/迁移/evidence
```

T5R 同任务 R15 首帧 shadow / required parity 见
`plugin/integration/prompt_obligation_reconciliation_shadow.py` 与
`未来架构/迁移/T5R-RequiredObligationSourceBinding-Implementation-Report.md`。
2.0–6.2s 属 Legacy derived，不迁移；Audio 六关系与 S01 不足的判定保持。

STOP AT T5R：Provider submission / paid calls / media generation 均为 0；不改 Canon，
不删除 Legacy Prompt/Audio，不新增数据库表或顶级 Skill。
