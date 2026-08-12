# Drama Plugin Skill 持久化语义加固执行报告

## 1. 执行摘要

本批次仅加固 Skill 对 `create_xxx` 与 `save_xxx` 的选择方法论：新长期事实在当前 Skill 已形成足够完整的初始正式状态后，通过一次 `create_xxx` 完成首次持久化并取得稳定 ID；`save_xxx` 仅用于已有稳定 ID 对象发生具体修订的低频场景，不是 create 后的默认第二步。

实际修改 6 个具有实体 create/save 职责的 `SKILL.md`、README 中两条语义说明及轻量测试。`historical-research`、`shot-production`、全部 `skill.yaml`、Tool catalog、Provider 与 Host Adapter 均未修改。

验证结果为 32 个测试全部通过、mypy 0 issue、8 个 Skill 格式校验全部通过、示例通过。Tool 数量、code、description、输入与输出 Schema 前后完全一致。

## 2. 修改前 create/save 使用方式审计

| Skill | Create 使用 | Save 使用 | 修改前问题 | 处理 |
|---|---|---|---|---|
| work-creation | `work.create_work` | `work.save_work` | 已区分新建与修订，但未明确 create 写入完整初始正式状态，也未禁止 create 后例行 save | 已加固 |
| script-adaptation | `script.create_script` | `script.save_script` | 同上 | 已加固 |
| episode-development | `episode.create_episode` | `episode.save_episode` | 同上 | 已加固 |
| scene-development | `scene.create_scene` | `scene.save_scene` | 同上 | 已加固 |
| shot-design | `shot.create_shot` | `shot.save_shot` | 同上 | 已加固 |
| asset-resolution | `asset.create_asset`、条件性 `media.create_media` | `asset.save_asset` | 已禁止重复登记稳定 Media，但未明确 Asset create 后不得例行 save | 已加固，并强化 Media 去重语义 |
| shot-production | 无 create/save Tool 声明；生成 Tool 直接返回稳定 Media | 无 | 不承担首次 Media 登记或 metadata 修订，无需强行加入持久化章节 | 未修改 |
| historical-research | 无长期记忆写入 | 无 | Research Context 不进入长期实体 CRUD | 未修改 |

扫描 `skills/*/SKILL.md`、`skills/*/skill.yaml`、README、测试与 Tool catalog 后确认：

- 修改前不存在明示的 `create → save` 固定流程；
- 不存在“create 空对象取得 ID，再 save 完整内容”的方法论；
- 不存在“每次 Skill 完成都调用 save”的说明；
- 不存在“为确保已持久化而在 create 后再次 save”的说明；
- 主要缺口是规则表达不够严格，无法阻止 Agent 把 save 误当成常规 finalize 动作；
- Tool catalog 的 create/save 描述没有鼓励上述错误模式，无需修改。

## 3. 最终 Create 语义

`create_xxx` 是新长期事实的正常首次持久化操作。

Agent 应先在当前 Skill 中形成使对象成为有效长期事实所需的完整初始正式状态，再调用一次 create。create 成功表示首次正式持久化已经完成，并返回稳定 ID；不得先创建空壳再依赖 save 填充正常初始内容。

冻结语义：

> Create is the normal first-write operation for a newly generated long-term fact. Create should persist the complete initial formal state required by the current Skill.

## 4. 最终 Save 语义

`save_xxx` 仅用于已经持久化且拥有稳定 ID 的对象发生明确修订时，例如：

- 用户明确要求修改；
- Agent 发现已有内容错误；
- 上游正式事实变化使当前对象失效；
- 必须补充属于该对象正式状态的重要信息。

save 不是首次持久化、不是生成完成后的固定动作，也不是 create 后的默认第二步。没有具体修订时不调用。

冻结语义：

> Save is a revision operation for an already persisted object with a stable ID. Save must not be called routinely after Create unless a concrete revision has actually occurred.

## 5. 修改的 Skill 清单

### work-creation/SKILL.md

明确 `work.create_work` 应一次写入本 Skill 所需的完整初始正式状态；`work.save_work` 只处理已有 Work 的具体修订，并禁止 create 后例行 save。

### script-adaptation/SKILL.md

明确完整初始 Script 通过 `script.create_script` 首次落库；`script.save_script` 只用于已有 Script 的明确修订。

### episode-development/SKILL.md

明确完整初始 Episode 通过 `episode.create_episode` 首次落库；`episode.save_episode` 只用于已有 Episode 的明确修订。

### scene-development/SKILL.md

明确完整初始 Scene 通过 `scene.create_scene` 首次落库；`scene.save_scene` 只用于已有 Scene 的明确修订。

### shot-design/SKILL.md

明确完整初始 Shot 通过 `shot.create_shot` 首次落库；`shot.save_shot` 只用于已有 Shot 的明确修订。

### asset-resolution/SKILL.md

明确完整初始 Asset 通过 `asset.create_asset` 首次登记；`asset.save_asset` 只用于已有 Asset 的明确修订。Generation 已返回稳定 `mediaId` 时禁止重复调用 `media.create_media`；只有未登记物理结果才可登记。

## 6. 未修改的 Skill 及原因

- `historical-research`：只形成 Agent Research Context，不承担长期实体 create/save；为统一格式添加持久化说明会制造无意义内容。
- `shot-production`：当前 Tool Contract 由 Generation Tool 直接返回稳定 Media，Skill 不声明 `media.create_media` 或 `media.save_media`；本批不改变其职责。

## 7. Tool Contract 是否发生变化

- Tool 数量是否变化：**否，修改前后均为 42。**
- Tool code 是否变化：**否。**
- Tool 参数 Schema 是否变化：**否。**
- Tool 输出 Schema 是否变化：**否。**
- Tool description 是否变化：**否。**
- Provider Protocol 是否变化：**否。**
- HTTP binding 或 Mock 行为是否变化：**否。**

修改前后 `ToolRegistry.describe()` 完整结果相等；稳定序列化 SHA-256 均为：

```text
a35fb5755aa91a84753e3f782120a4216f8f80da5d7b8a209f4f0c48217b5940
```

## 8. README / skill.yaml / Tool catalog 修改情况

- README：仅修改 create/save 两条说明，明确完整初始状态一次 create，以及 save 非默认后续步骤。
- skill.yaml：**未修改**。现有 preferred/allowed 与 refresh_after 引用仍正确；“可能导致 Context 变化”不代表必须调用 Tool。
- Tool catalog：**未修改**。现有 create 描述表达创建新对象，save 描述表达已有对象的新正式状态，没有鼓励 create→save。
- agents/openai.yaml：**未修改**。

## 9. 测试结果

实际执行：

```bash
../.venv/bin/python -m pytest -ra
../.venv/bin/python -m mypy src/drama_plugin
PYTHONPATH=src ../.venv/bin/python examples/build_shot_context.py
../.venv/bin/python .../skill-creator/scripts/quick_validate.py skills/<skill>
```

结果：

- pytest：32 collected，32 passed，0 failed；
- mypy：33 个 source file，0 issue；
- Demo：成功加载 `shot-production` 并构建 SHOT Context；
- Skill quick validation：8/8 PASS；
- Skill Tool 引用：全部合法；
- create/save 语义测试：6 个相关 Skill 均明确完整首次 create、具体修订才 save、禁止 create 后例行 save；
- Media 去重测试：`asset-resolution` 明确不重复登记稳定 mediaId；
- Tool Contract 前后快照：完全相等；
- `git diff --check`：PASS。

新增测试保持轻量，仅做稳定字符串与现有机器契约核对，没有引入 Markdown parser、AST 或新框架。

## 10. 边界确认

- 未新增 Tool；
- 未删除 Tool；
- 未重命名 Tool；
- 未修改 Java Drama Service；
- 未修改 MCP Server；
- 未修改 Provider、HTTP API、Mock 或数据结构；
- 未修改 get/list/search 语义；
- 未新增 Workflow、状态机或编排器；
- 未重新引入 Plan、Compile、Binding 或 GenerationTarget orchestration；
- 未引入新依赖、框架或运行时；
- 未实现 Media/Generation Provider 或 Harness。

## 11. 最终明确回答

1. 新对象正常首次持久化是否统一使用 `create_xxx`？**是。**
2. `create_xxx` 是否应该直接保存当前 Skill 所需的完整初始正式状态？**是。**
3. 是否禁止把 `create → save` 作为默认流程？**是；只有 create 后确实发生具体修订时才允许 save。**
4. `save_xxx` 是否仅用于已有稳定 ID 对象的明确修订？**是。**
5. save 是否仍保留为必要但低频能力？**是。**
6. get/list/search 的既有语义是否保持不变？**是。**
7. Tool 数量与 Schema 是否保持不变？**是，42 个 Tool，完整合同快照相等。**
8. 是否新增任何 Workflow / 状态机 / 编排逻辑？**否。**
9. 当前 Skill 是否已经适合后续 Java Drama Service 按该语义实现 create/update？**是。Skill 已冻结首次 create 与低频 revision save 的清晰边界，且不依赖 Java 实现细节。**

最终原则：**新建 → create；已有 → reuse；确需修改 → save。**
