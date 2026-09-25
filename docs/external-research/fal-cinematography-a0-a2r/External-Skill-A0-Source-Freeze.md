# External Skill A0 — Source Freeze

审计日：2026-09-25。范围：STILL / CINEMATOGRAPHY / LIVE-ACTION REALISM。状态：A0–A2R 完成，STOP；无 A3/A4 执行。

## 冻结来源

| 项目 | 已观察值 |
|---|---|
| Repository | [https://github.com/fal-ai-community/skills](https://github.com/fal-ai-community/skills) |
| Remote URL | `https://github.com/fal-ai-community/skills.git` |
| Default branch | `main`（git origin/HEAD 与 GitHub API 一致） |
| Checked-out SHA | `9ca850412943251fc9a466c4c29fdaf7a303a3d8` |
| Commit time | `2026-05-13T21:10:57+01:00` |
| Tags / Releases | 完整 clone 中没有 tag；GitHub releases 返回空数组 |
| Temporary clone | `/private/tmp/fal-skills-a0-20260925`，未安装 |
| Main target | `skills/cinematography/SKILL.md` 和三个 `references/*.md` |
| Local target | `8f805217f9b7b692a10f3ec0a5363a938f91b192`；初始工作树 clean；先读当前源码再读外部 |

[冻结元数据](evidence/external-freeze.json)保存全部 97 个 tracked 文件的 SHA-256；[Git 历史](evidence/external-history.txt)保存 commit、日期和主题。[本地基线](evidence/local-baseline.json)保存 835 个 tracked 文件 hashes。GitHub issues/releases 是审计日动态快照，不冒充冻结 commit 的一部分。

## License 核验

[冻结 README](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/README.md)声明 MIT。完整树中没有根目录 LICENSE/COPYING；仅 `skills/fal-redesign/LICENSE` 有 MIT 全文，不能推定它覆盖兄弟目录。GitHub repository metadata 的 `license=null` 与缺少机器可识别根许可一致，不等于断言无许可。

MIT 标准条款允许使用、修改、合并、分发，但复制实质内容须保留版权与许可通知。**此处只确认仓库的 MIT 声明，尚未完整确认 cinematography 文本的版权通知/许可覆盖**。裁决：`LICENSE_DECLARED_MIT_NOTICE_INCOMPLETE`。本轮只保存审计改写与出处，不 vendor 外部 Skill、不复制模板进 Runtime。后续若要复制或再分发原文，须先补齐明确适用的授权通知；不能拿 nested LICENSE 冒充根许可。知识候选的独立表述与文献引用可进入设计研究，许可不完整不赋予复制授权。

## 结构与依赖边

| 来源节点 | 真实边/用途 | 本轮处理 |
|---|---|---|
| cinematography | 明确 load 三个本地 references 与 model-routing | 全部阅读与原子拆分 |
| cinematography → genmedia | CLI 执行依赖 | 只读命令/安装/路由语义；REJECT runtime adoption |
| cinematography → storytelling | sequence 时的条件交接 | 阅读 SKILL、shot-planning/workflows；视频候选留下一轮 |
| cinematography → relevant domain skill | 角色/产品连续性先由领域 Skill 决定 | 角色 SKILL/anchor-system 已读；不把 commercial 自动纳入 |
| fal-recipes/cinematography | 同源重述的 umbrella recipe，非直接必需依赖 | 核对重复内容，不当独立验证样本 |
| fal-recipes/realism | 与电影 still 相关的独立配方，通过 recipe/catalog/prompting 交叉引用发现 | 只审计与首轮真人写实重合部分；不是直接依赖/整包吸收 |
| fal-prompting/GPT Image 2 | 从 realism/catalog 连到模型提示指南 | 只查 still prompt 和参数边界 |
| fal-models-catalog T2I/I2I | recipe 的 endpoint 来源 | 读相关 reference，不能导入路由表 |

没有把 Kling、Happy Horse、商业广告、fan-cam、3D 的实产叙述当作 cinematography 验证；PR 元数据可作仓库维护线索。未执行外部 shell/installer/genmedia。

## External Validation Classification

```yaml
validation:
  classification: EXTERNAL_CANDIDATE
  confidence: HIGH
  evidence:
    - 摄影 SKILL 有明确输入、词汇、工作流、五个文本示例与质量检查
    - 完整 git history 可追踪到 8390c77 的 2026-05-01 重组和 653a2b7 的目录扁平化
    - model/schema/pricing/upload/run/status/download 是具体工作流程描述
    - 存在仓库使用反馈和维护 PR，但不是摄影规则效果评测
  limitations:
    - 未发现与摄影示例配对的输入输出媒体、参数、结果观察与盲评
    - 无 cinematography 专项自动测试或模型对照基准
    - 无可证明 same-scope 专业规则优于本地的实产证据
    - 示例和作者质量宣称不构成 VALIDATED_EXTERNAL
    - provider 参数文档已发现不一致，不能盲信旧提示指南
```

这里 HIGH 是“候选而非充分验证”的分类把握，不是摄影效果置信度。专业子能力默认 EXTERNAL_CANDIDATE/MEDIUM；过时参数、排名、安装和示例本身为 REFERENCE_ONLY。`VALIDATED_EXTERNAL` 列表为空。

| 检查项 | 证据 | 结论/局限 |
|---|---|---|
| Production usage | issue #3 泛称 Claude Code 使用成功；PR #10 指向另一个 3D 工作流 | 不能迁移为摄影实产效果 |
| Examples | cinema 五个 prompt；realism 四个文本场景 | 有设计示例，无配对媒体验收 |
| Tests | 当前树没有摄影 tests；build-skills-index 是索引/hash 工具 | 结构检查不验证照片质量；本轮未运行外部脚本 |
| Version history | 根历史 41 commits；目标 follow history 两次：重组与移动 | 无逐条摄影准则效果修订记录 |
| Revisions/feedback | PR #16 描述 agent 忽略 smart routing 的实际会话；#22 报 YAML 安装缺陷；#24 模型更新待合并 | 证明局部运行反馈，不证明专业摄影准则 |
| Failure handling | generic→具体描述；漂移→reference/edit；schema checks；异步 task id | 有建议，但缺本地式预算、UNKNOWN recovery、正式 Media 契约 |
| Maintenance | 非 archived；main 最后更新 2026-05-13，距审计约 134 天；9月仍有 issue | 有社区活动，不能宣称摄影持续维护 |
| Prompt collection? | 目标主要是 Markdown 规则+模板+命令，无独立实现 | 不只是零散 prompts，但也不是经验证摄影引擎 |
| fal coupling | endpoint/defaults、genmedia、上传、下载、安装紧耦合 | K/Q 可拆；P/R 不能整体迁移 |

[反馈全量快照](evidence/github-issues.json)覆盖一页 25 条 issue/PR（全部不足 100）；所有条目 comments=0，唯 #1 有 1 条、主题为旧路径可移植性，不作为摄影效果证据。[仓库状态](evidence/github-repo.json)、[releases](evidence/github-releases.json)已保留。closed PR 不自动等于 merged；本报告所称合并以本地 git log 可见 merge 为准。

## Provider currency 只读核查

2026-09-25 阅读 [fal T2I 文档](https://fal.ai/models/openai/gpt-image-2/api)与 [fal edit schema](https://fal.ai/models/openai/gpt-image-2/edit/api)：edit 列出最多 16 个 `image_urls`，mask 字段为 `mask_url`；未列出指南声称的 `input_fidelity`。这支持参数资料只能作待核验参考；不能把缺少字段当成已测试拒绝，也不能把 fal 能力推给本地 Comfy node。本轮未验证其余 endpoint 的实时可用性、价格或“最佳质量”排名。

## 保管边界

报告位于 `docs/external-research/`，不在 `plugin/skills`、`.agents/skills` 或安装缓存。没有 `SKILL.md`/`skill.yaml`，没有 manifest/registry/import 修改。源码 `plugin/src/drama_plugin/skills/registry.py::load_directory` 只读取配置 skill 根下具备两文件的直接子目录。外部 clone 只留在临时目录；以后可用 SHA 重建。审计 JSON 是 NON_RUNTIME reference metadata，不是新 Canonical Contract。
