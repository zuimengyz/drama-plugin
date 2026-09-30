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

T1–T5R 已合入 master。当前明确授权阶段为 T6：仅将新 Target Runtime 的 checkpoint、
不可变执行工件、Reference Binding 与 Review/Finding 持久化，并验证跨进程恢复、CAS、去重和
Work 大小边界。目标设计仍以 `未来架构/` 为 Authority；Canon、Media 和旧在途任务继续由原 owner 持有。
STOP AT T6：不迁旧 productionHistory，不删除旧部门/Bible/Gate/Prompt/Audio/Host/Skill，
不接 Provider、不生成媒体，不 commit / push / merge。不得向 Work 无限追加新 Target 生产历史。
