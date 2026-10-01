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

T1–T6 已合入 master。当前明确授权阶段为 T7：隔离旧入口，令 Target Runtime 只执行
Target native capability 与显式只读迁移读取；旧 Work 生产状态仅供显式历史恢复。
Legacy 代码只允许修复 bug 和历史恢复兼容，不新增 feature、Provider、Prompt 能力、Gate
或专业设计行为。新能力必须进入 Target owner；Legacy Host 不得决定新 Target Run 的下一步。
目标设计仍以 `未来架构/` 为 Authority；Canon、Media 和旧在途任务继续由原 owner 持有。
STOP AT T7：不迁旧 productionHistory，不大量删除旧部门/Bible/Gate/Prompt/Audio/Host/Skill，
不迁 Provider、不生成媒体，不 commit / push / merge。Target 新生产状态只写 Production Ledger。
