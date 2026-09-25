# Prompt A0 — External Source Freeze

2026-09-26 · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED · STOP AT A2R

## 基线与冻结方法

本地仓库是 `drama-plugin/`，其父目录不是 Git 仓库。当前 HEAD 为 `789ed88d895bee045f24cf4432971da8220e5310`。初始已有未跟踪 `docs/external-research/.DS_Store`，不属于本轮产物。929 个 tracked 文件的 SHA-256 已冻结于 [local-baseline.json](evidence/local-baseline.json)；源码与历史报告定位见 [local-source-index.json](evidence/local-source-index.json)。审计读取 repository HEAD 对应工作树，不把安装缓存当当前 Runtime。

四仓库以 `git clone --depth 1` 读取远端默认分支，冻结 full commit SHA。首次沙箱内 DNS 失败，随后通过权限工具联网克隆成功。未安装依赖、未加载外部 skill、未执行外部 README/SKILL 的生成命令。源码隔离于 `/tmp/prompt-a0-research/`；没有将模板 bundle 复制进插件。临时 checkout 可能被系统清理，持久证据为 full SHA、GitHub commit 链接、相关文件逐项 hash 和本报告；可按 SHA 重建。

[external-source-freeze.json](evidence/external-source-freeze.json) 保存 UTC 获取时间、分支、commit 时间/标题、license 原文（存在时）、相关文件 hashes、checkout 位置、dirty 状态。深度 1 只能证明冻结提交存在，不能推断历史活跃率、issue 处理速度或 CI 成功。本轮不以星数/README 宣称质量。

## 来源逐项冻结

### A — Prompt Optimization

- Repository: [getsentry/skills](https://github.com/getsentry/skills)
- Branch: `main`；SHA: [`c2f99a5b04b4cd992ec3022d7c2c3e23e938d241`](https://github.com/getsentry/skills/commit/c2f99a5b04b4cd992ec3022d7c2c3e23e938d241)。
- Commit 元数据: 2026-08-25T07:33:48-07:00 fix(iterate-pr): Remove default Claude attribution (#169)。Maintenance: 仅据该冻结提交记录近期性，不推断持续维护承诺。
- License: Apache-2.0；根 LICENSE。
- Relevant paths: `skills/prompt-optimizer`。
- Tests/examples: SKILL、SPEC、SOURCES 和四份 references；有改写示例及人工 checklist，目标目录没有可执行 eval/test harness。
- Validation evidence: 源文件确认 causal trimming、单规则 owner、固定 eval slice、holdout 和停止条件。未运行模型 eval；不证明影视语义保持。
- Limitations: 面向 agent/system/developer prompt，文件引用只有模型真能读文件时才成立；图像/视频模型不能凭仓库路径读取 Canon。
- Classification: **EXTERNAL_CANDIDATE**；不存在本平台 STILL/VIDEO 已验证的效果结论。

### B — Model-family Prompting

- Repository: [fal-ai-community/skills](https://github.com/fal-ai-community/skills)
- Branch: `main`；SHA: [`9ca850412943251fc9a466c4c29fdaf7a303a3d8`](https://github.com/fal-ai-community/skills/commit/9ca850412943251fc9a466c4c29fdaf7a303a3d8)。
- Commit 元数据: 2026-05-13T21:10:57+01:00 Merge pull request #16 from koumpas/feat/genmedia-smart-routing。Maintenance: 仅据该冻结提交记录近期性，不推断持续维护承诺。
- License: README 声明 MIT；冻结树未找到根 LICENSE，不能声称已核验完整许可文本。
- Relevant paths: `skills/fal-prompting`。
- Tests/examples: fal-prompting/SKILL.md 与 GPT Image 2、Kling、Happy Horse 三份指南；目标目录没有测试或配对媒体证据。
- Validation evidence: 确认分模型、分模式的写法主张确实存在；未验证效果或实时 endpoint 参数。
- Limitations: 社区指导不等于模型厂商验证。词数、参考图数量、质量优势均是来源主张；本地 route contract 优先。genmedia/fal runtime 为 REFERENCE_ONLY 且不吸收。
- Classification: **EXTERNAL_CANDIDATE**；不存在本平台 STILL/VIDEO 已验证的效果结论。

### C — Prompt Compression Concepts

- Repository: [microsoft/LLMLingua](https://github.com/microsoft/LLMLingua)
- Branch: `main`；SHA: [`5a4c78ae18ab17a98cf997e8259354e546081d64`](https://github.com/microsoft/LLMLingua/commit/5a4c78ae18ab17a98cf997e8259354e546081d64)。
- Commit 元数据: 2026-09-10T16:36:23-07:00 Merge pull request #257 from danfiedler-msft/danfiedler/pin-actions。Maintenance: 仅据该冻结提交记录近期性，不推断持续维护承诺。
- License: MIT；根 LICENSE。
- Relevant paths: `llmlingua/prompt_compressor.py`, `tests`, `examples/LLMLingua2.ipynb`。
- Tests/examples: prompt_compressor.py；tests/test_llmlingua.py、test_longllmlingua.py、test_llmlingua2.py；LLMLingua2 等 notebook 示例。
- Validation evidence: 源码和测试含 rate/target_token、force_context_ids、force_tokens、数字保留与结构段落保留。测试需要模型权重；未下载或运行。
- Limitations: 针对 LLM token/context 压缩。词/token 被保留不等于动作、否定、方向、时间和人物关系被保留；不作为视觉 Runtime 算法。
- Classification: **REFERENCE_ONLY**；不存在本平台 STILL/VIDEO 已验证的效果结论。

### D — Prompt Evaluation

- Repository: [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo)
- Branch: `main`；SHA: [`8ebdb3818c10b4ac7c2b665cd148d996f4fcd740`](https://github.com/promptfoo/promptfoo/commit/8ebdb3818c10b4ac7c2b665cd148d996f4fcd740)。
- Commit 元数据: 2026-09-25T12:03:36-04:00 chore(deps): update vitest to v5.0.1 (#11069)。Maintenance: 仅据该冻结提交记录近期性，不推断持续维护承诺。
- License: MIT；根 LICENSE（此结论只覆盖读取的根项目，不泛化所有第三方依赖）。
- Relevant paths: `plugins/promptfoo/skills/promptfoo-evals`, `src/assertions`, `test/assertions`, `examples/compare-claude-vs-gpt-image`。
- Tests/examples: plugins/promptfoo/skills/promptfoo-evals/{SKILL.md,references/eval-patterns.md}；src/assertions 与 test/assertions；图像分析比较示例。
- Validation evidence: 源码/skill 确认固定测试、assertion 校准、holdout、失败/错误区分和 CI gate。未安装、未跑 provider 或 grader。
- Limitations: 图像分析示例评估“回答对图的描述”，不是生成视频时间/空间保真验证；框架不能替作品定义艺术成功标准。
- Classification: **EXTERNAL_CANDIDATE**；不存在本平台 STILL/VIDEO 已验证的效果结论。

## 证据等级与准入

`VALIDATED_EXTERNAL` 仅用于有范围明确、可核对验证结果的外部能力，不能因为仓库开源或有 tests 目录就赋值。本轮四来源中，没有视觉提示效果能力达到此等级。源码存在性已核验，与能力有效性分开记录。A/C 中可借鉴的预算/保留思想、D 的测试组织法，只作为本地适配候选，不自动晋级。

A1 每项能力单独分类；A2 的 ADAPT/KEEP_LOCAL 是下一阶段研究处置，不是已吸收、已部署。B 的 GPT Image 2 内容只作为该社区仓库的主张，不把其五段模板、16 图上限、输入保真参数或 Happy Horse 词数搬入本地。当前本地三图与 route 限制保持。

## 既有 A3/A4 衔接

已读取摄影/Face A3 的表达审计、Source→IR mapping、A4 plan、A5 validation，以及合并的 [Still-LiveAction-A4-Implementation-Report](../still-liveaction-a4/Still-LiveAction-A4-Implementation-Report.md)。两项 A4 均在此合并报告中，不伪造独立 A4 文件。

A3 报告中的“mapper/D2 尚不存在”是旧基线事实；当前 HEAD 已有 `still_knowledge.py`、D1/D2 与支付前 source replay。A4 明确仍为 LOCAL_EXPERIMENTAL、opt-in STILL/LIVE_ACTION，不等于 A5 媒体效果通过。A4 报告还记载全库两个既有 Video `compiledBy` 失败；本轮不修复、不宣称全库绿色。

## 本轮执行证据

- [offline-probes.json](evidence/offline-probes.json)：16 个合成、无网络的既有编译器观察，包含预期的预算拒绝；不是获批作品或媒体实验。
- [local-tests.log](evidence/local-tests.log)：既有 still mapping、VisualPromptIR、image serializer、budget 测试 72 PASS。仅验证相关代码行为，不升级任何媒体知识。
- [completion-check.json](evidence/completion-check.json)：结束时核对 tracked files 不变、报告/枚举/link 完整性及停止门。

没有外部 skill installation，没有模型下载，没有图片/视频生成，没有 Prompt A3/A4 实施。
