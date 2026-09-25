# Prompt A1 — Capability Forensics

2026-09-26 · NON_RUNTIME · research conclusions only · STOP AT A2R

冻结版本、许可与验证限制见 [A0](Prompt-A0-External-Source-Freeze.md)。下列是源码能力拆解，不是技能安装，也不执行所读 SKILL 中的命令。K=knowledge，W=workflow，P=provider-specific，R=runtime architecture，Q=evaluation/quality，C=compression/distillation，M=meaning-preservation。

## 外部证据定位

所有链接锁定本轮 commit，不能用浮动 main 的内容替代本次判断。

| Evidence | Frozen source | 直接支持的内容 |
|---|---|---|
| A1 | [Sentry SKILL](https://github.com/getsentry/skills/blob/c2f99a5b04b4cd992ec3022d7c2c3e23e938d241/skills/prompt-optimizer/SKILL.md) | 契约先行、owner、因果上下文、精简、固定测试 |
| A2 | [core-patterns](https://github.com/getsentry/skills/blob/c2f99a5b04b4cd992ec3022d7c2c3e23e938d241/skills/prompt-optimizer/references/core-patterns.md) | policy/evidence 分离、跨层重复、最短有效表述 |
| A3 | [meta-optimization-loop](https://github.com/getsentry/skills/blob/c2f99a5b04b4cd992ec3022d7c2c3e23e938d241/skills/prompt-optimizer/references/meta-optimization-loop.md) | baseline、失败聚类、候选、holdout、停止条件 |
| A4 | [SPEC](https://github.com/getsentry/skills/blob/c2f99a5b04b4cd992ec3022d7c2c3e23e938d241/skills/prompt-optimizer/SPEC.md) | 目标为 agent prompt；不能无 eval 证明质量 |
| B1 | [fal-prompting](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/SKILL.md) | 家族差异、视觉事实、一次改变一个变量 |
| B2 | [GPT Image 2 guide](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md) | 静态结构、编辑 change/preserve、reference role、文字精确性 |
| B3 | [Happy Horse guide](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/happy-horse.md) | brevity-first、按输入模式区分、动作时间段 |
| B4 | [Kling guide](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/kling.md) | I2V 重运动、声明句、multi-prompt 需 schema 支持 |
| C1 | [PromptCompressor](https://github.com/microsoft/LLMLingua/blob/5a4c78ae18ab17a98cf997e8259354e546081d64/llmlingua/prompt_compressor.py) | `compress_prompt`/`compress_prompt_llmlingua2`、上下文/句/token 选择、预算和强制保留 |
| C2 | [LLMLingua2 tests](https://github.com/microsoft/LLMLingua/blob/5a4c78ae18ab17a98cf997e8259354e546081d64/tests/test_llmlingua2.py) | 文本输出/token 数断言、force tokens/数字示例；需权重 |
| D1 | [promptfoo-evals](https://github.com/promptfoo/promptfoo/blob/8ebdb3818c10b4ac7c2b665cd148d996f4fcd740/plugins/promptfoo/skills/promptfoo-evals/SKILL.md) | 固定 fixture、客观/语义断言、校准、失败可见性 |
| D2 | [eval-patterns](https://github.com/promptfoo/promptfoo/blob/8ebdb3818c10b4ac7c2b665cd148d996f4fcd740/plugins/promptfoo/skills/promptfoo-evals/references/eval-patterns.md) | known-good/bad、echo 校准、数据集、CI、faithfulness |
| D3 | [image analysis example](https://github.com/promptfoo/promptfoo/blob/8ebdb3818c10b4ac7c2b665cd148d996f4fcd740/examples/compare-claude-vs-gpt-image/promptfooconfig.yaml) | 带图 grader 的描述评估；不是生成影视质量试验 |

## PROMPT_EXTERNAL_CAPABILITY_INVENTORY

分类只用 A0 定义的三个等级。不存在“整个仓库已验证，故每项能力都已验证”的推导。

| ID | Capability | Tags | Evidence / mechanism | Classification | 本地迁移限制 |
|---|---|---|---|---|---|
| P01 | 先冻结目标、约束、owner | W,M,Q | A1 Step 1 | EXTERNAL_CANDIDATE | 目标须引用 Work/Scene/Shot，优化器不能另写主题 |
| P02 | 因果上下文选择 | K,C,M | A1/A2 只保留影响行为的上下文 | EXTERNAL_CANDIDATE | “不影响某次输出”不证明不影响罕见关键情节；需要反例 |
| P03 | 一种义务一个权威 owner | W,M | A2 层级与规则归属 | EXTERNAL_CANDIDATE | 可适配为语义去重；不是现成影视 atom resolver |
| P04 | 最短仍保持约束的语言 | K,C,M | A1 Step 4 | EXTERNAL_CANDIDATE | 保持语义优先于字符数，不许逐词删否定或施受关系 |
| P05 | 固定文件引用替代复制上下文 | W,C,R | A1 Step 2 / A4 limitation | REFERENCE_ONLY | 适用于能读取文件的 Host；不能把原件路径当视觉输入 |
| P06 | baseline→失败聚类→候选→holdout | W,Q | A3 | EXTERNAL_CANDIDATE | 每个影视实验只变 policy；不能一起改角色、摄影和模型 |
| P07 | 停止于 plateau/overfit/非 prompt 瓶颈 | W,Q | A3 | EXTERNAL_CANDIDATE | 不让测试框架自动发动再生成或更改故事 |
| P08 | 分 model family 的 projection | K,P,W | B1，A1 Step 3 | EXTERNAL_CANDIDATE | 保留共享事实；家族只选表达，不能拥有戏剧意图 |
| P09 | 静态分区与编辑 delta/preserve | K,P,C | B2 | EXTERNAL_CANDIDATE | 本地已存在独立 static/edit serializer；不复制五段模板 |
| P10 | I2V 减少重复静态叙述 | K,P,C | B3/B4 I2V | EXTERNAL_CANDIDATE | reference 确实承载才省略；不能删关键手、物、方向和身份约束 |
| P11 | 视频动作/运镜/时序表达 | K,P,M | B3 timecodes；B4 multi-prompt | EXTERNAL_CANDIDATE | 时间与镜头边界必须来自既有 Action/Editorial/Clip，不由 policy 拆镜头 |
| P12 | 固定词数与 plain prose 偏好 | K,P,C | B3 ~20；B4 30–40，带例外 | REFERENCE_ONLY | 不是硬限制，也没有本地 Vidu/Seedance 实测支持；B3 自己含较长与分段例外 |
| P13 | 可见事实替代赞美/风格标签 | K,C,M | B1/B2/B3/B4 | EXTERNAL_CANDIDATE | 无普适 blacklist；具象化须回专业 owner，不能凭空补 50mm/逆光 |
| P14 | reference 按职责绑定 | K,P,M | B2 | EXTERNAL_CANDIDATE | 本地 carry/exclude 更严格；全帧、身份肖像、服装参考不等价 |
| P15 | 字面文字与保留约束精确表达 | K,P,M | B2 typography/edit | EXTERNAL_CANDIDATE | 只在镜头真的需要文字时使用；不是为所有镜头加 no-logo |
| P16 | 重要性排序/分层过滤 | C,R | C1 context/sentence/token filtering、LLMLingua2 token classifier | REFERENCE_ONLY | 语言模型重要性分数不是作品 drop cost；不直接导入算法 |
| P17 | force context/token/数字保留 | C,M,R | C1 参数与 C2 测试 | REFERENCE_ONLY | 保住“女孩/袖口”两个词不保证谁抓谁、是否松手 |
| P18 | budget-aware 压缩与不压缩段落 | C,R | C1 rate/target_token/structured segments | REFERENCE_ONLY | 文档明确 tokenizer 引起实际预算波动；本地字符硬限不能替换成 token 目标 |
| P19 | prompt regression/固定数据与 CI | W,Q | D1/D2、src/assertions | EXTERNAL_CANDIDATE | 借测试组织法；无需将 promptfoo runtime 作为生产依赖 |
| P20 | 已知好/坏对照校准断言 | Q,W | D1/D2 echo/control | EXTERNAL_CANDIDATE | echo 只验证接线；视觉判断需要真实媒体及受控评审 |
| P21 | 客观断言与语义 grader 分层 | Q,M | D1/D2/D3 | EXTERNAL_CANDIDATE | substring 不等于关系保持；LLM grader 不等于视觉事实 owner |
| P22 | eval 留痕、错误/失败/零覆盖区分 | W,Q | D1/D2 | EXTERNAL_CANDIDATE | 必须记录 UNKNOWN/技术失败，不把空结果当 PASS |
| P23 | fal/genmedia 执行体系 | R,P | B1 runtime 段、B2–B4 CLI 示例 | REFERENCE_ONLY | 不在授权研究吸收范围；不安装、不替换本地 adapter/route |

## 能力边界判断

Meaning、Visible Semantic Atoms、Prompt Language 必须三分：Meaning 是选择与后果为何重要；Atoms 是在特定镜头与时间内承载它的可观察事实；Language 是给选定模型表达这些事实的文字。A 的“因果 prompting”指指令对模型行为有因果贡献，不等于历史/文学的戏剧因果系统。C 的 importance 也不是 Meaning 的自动评分器。

没有一个外部来源提供可直接接入本地的 Work→Scene→Shot→可见义务完整 Contract。B 提供的是表达经验，不能替代专业判断。D 提供的是验证工具和流程，成功条件仍来自本地批准原件。

## Compression 与 Distillation 的正式结论

选择 **Semantic-Preserving Prompt Distillation**。字符缩短是附属指标，只有语义覆盖、主体绑定、状态和时间关系都保留时才有收益。A1 的约束保留与 eval-first 支持此方向；C1 的强制保留说明不能无条件裁剪，但不能据此声称 LLMLingua 对图像/视频已有效。

最小反例：同样含“女孩、袖口、男人、转身”的短句，可能把“男人保持离开方向”变为“男人转身回应”，词覆盖很高而戏剧意义反转。只去掉“尚未”“左”“始终”“直到”也可能破坏关系或时间。atom 应保留完整关系，不把一个词当最小语义单位。

这些是由本地链路与外部能力边界作出的研究判断，不是已实测的视觉增益。具体本地缺口、现有反例和优先级建议见 [A2](Prompt-A2-Local-Capability-Mapping.md)；冲突 winner 与 A3 入场判断见 [A2R](Prompt-A2R-Conflict-Authority-Reconciliation.md)。
