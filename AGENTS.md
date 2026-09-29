# T0：当前架构维护约束

`master` 是 Current Architecture 的正式代码基线。迁移目标以工作区
`未来架构/` 中的已批准设计为准；旧实现不能反向改写目标原则。

旧 Runtime 允许严重 bug 修复、兼容当前正式 Work、查询与恢复历史生产。
禁止新增顶级 Host、顶级 Gate、第二套生产主循环，或给旧 Host 增加长期编排职责。
不得因迁移重写稳定 Provider / Storage；已有在途任务继续由原执行路径恢复。

新的流程推进职责集中到 `plugin/src/drama_plugin/runtime/`。
迁移桥必须标为 `MIGRATION_ONLY`，通过显式注册调用旧能力，不复制旧能力实现。
Runtime 只保存身份、运行状态和必要引用，不保存 Work、Script、Scene、Bible、
Director package 或 Prompt IR 正文，也不产生创作意义。

T1–T4 已合入 master。当前明确授权阶段为 T5：ProductionPackage-only Prompt
编译、复用 Seedance 2 生成器、独立分层音频执行计划、离线影子与复杂度验证。
T5R 仅修正式义务来源绑定：复用 VideoReference/ReferenceRequirement，绑定已审核媒体；
一次性审计旧时窗和 Visual/Voice 来源，排除 Legacy derived；同输入模式验证。STOP AT T5R，不进入 T6。
STOP AT T5：不改创作正文/Authority，不删除旧部门/Bible/Gate/Prompt/Audio，不删旧 Host / Skill /
Provider，不新增数据库表，不提交 Provider，不生成媒体，不 commit / push / merge。
