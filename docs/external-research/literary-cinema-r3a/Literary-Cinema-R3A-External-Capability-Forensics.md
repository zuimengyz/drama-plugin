# Literary Cinema R3A — External Capability Forensics

> 审计日期：2026-09-26。源码基线：`bb83843074ae685a5fdd53ed94b1a27bd863a014`。范围：NON_RUNTIME / NO SCREENPLAY REWRITE / NO MEDIA GENERATION。本文的未来设计建议不是已实施能力，也不是剧本批准。

外部材料只提供待评估机制，不能授予本地创作权限。四个仓库均没有足够的当前平台创作/表演验证证据；本轮 **VALIDATED_EXTERNAL = 0**。最小增益是把本地已有戏剧过程规范落实为可审阅的因果交接与冷读证据，不是导入整套导演方法。

## 1. A0 freeze 与许可证

全部使用 commit 固定原始文件。完整的 30 个精确路径、链接、字节数和 SHA-256 见 [external-source-freeze.json](/Users/zy/historical-plugin/drama-plugin/docs/external-research/literary-cinema-r3a/external-source-freeze.json)。各仓库 recursive tree 返回 truncated=false。只读取公开文件；未安装、未运行生成工作流或仓库测试；未抓取影视书籍。

| 仓库 | 冻结 commit | 许可证证据与边界 | 等级 |
|---|---|---|---|
| gaojesse999/ai-scripts | `73e8ebaa85199dc14cf73d8c46610dd87ac87a66` | 目标 screenwriter-skill 与仓库根未找到适用 LICENSE；其他 skill/依赖有许可证，不能外推。README 为通用模板，不能解决目标授权 | REFERENCE_ONLY；机制可评估，禁止直接搬运 |
| 62656456/ai-film-skills | `f680c2ed0ba4d3b5692bd779ca8707e47b770d98` | [根 LICENSE](https://github.com/62656456/ai-film-skills/blob/f680c2ed0ba4d3b5692bd779ca8707e47b770d98/LICENSE) Apache-2.0；不把代码许可证当作被引用图书授权 | EXTERNAL_CANDIDATE |
| OSideMedia/higgsfield-ai-prompt-skill | `c0b73ab946df6658cca513db78bdc3909a655bfd` | [LICENSE](https://github.com/OSideMedia/higgsfield-ai-prompt-skill/blob/c0b73ab946df6658cca513db78bdc3909a655bfd/LICENSE) MIT；不自动覆盖其所声称电影素材/第三方理论 | EXTERNAL_CANDIDATE；模型经验仅参考 |
| 0xhughs/director-skills | `35ca0a2b4cd55b0668aa9ea0f40273324b774bb4` | [LICENSE](https://github.com/0xhughs/director-skills/blob/35ca0a2b4cd55b0668aa9ea0f40273324b774bb4/LICENSE) MIT | 编剧机制 EXTERNAL_CANDIDATE；model-adaptation 为 REFERENCE_ONLY |

许可证记录是所读文件的 provenance，不是对所有第三方内容权利作法律结论。

## 2. 精确机制与测试/示例效力

### E1 — screenwriter-skill

读取 [SKILL](https://github.com/gaojesse999/ai-scripts/blob/73e8ebaa85199dc14cf73d8c46610dd87ac87a66/skills/screenwriter-skill/SKILL.md)、[methodology](https://github.com/gaojesse999/ai-scripts/blob/73e8ebaa85199dc14cf73d8c46610dd87ac87a66/skills/screenwriter-skill/methodology.md)、[workflow](https://github.com/gaojesse999/ai-scripts/blob/73e8ebaa85199dc14cf73d8c46610dd87ac87a66/skills/screenwriter-skill/workflow.md)、[timing-and-cutting](https://github.com/gaojesse999/ai-scripts/blob/73e8ebaa85199dc14cf73d8c46610dd87ac87a66/skills/screenwriter-skill/timing-and-cutting.md)、treatment template 和 README。

价值：区分因果推进与事件并列，场景价值变化、铺垫回收、限定范围修订。限制：书籍名和理论出处不是能力验证；目标目录未发现自动化戏剧质量测试，模板不等于成功作品。固定反转数量、固定比例、统一裁掉停顿/开头秒数可能毁掉本片倾听与拒绝过程；不采用。没有复制或重建其所称理论书。

### E2 — director-agent

核心依据：[screenplay-state-engine](https://github.com/62656456/ai-film-skills/blob/f680c2ed0ba4d3b5692bd779ca8707e47b770d98/skills/director-agent/references/screenplay-state-engine.md)、[writing-core](https://github.com/62656456/ai-film-skills/blob/f680c2ed0ba4d3b5692bd779ca8707e47b770d98/skills/director-agent/references/screenplay-writing-core.md)、[cold-read-protocol](https://github.com/62656456/ai-film-skills/blob/f680c2ed0ba4d3b5692bd779ca8707e47b770d98/skills/director-agent/references/screenplay-cold-read-protocol.md)。另读取 SKILL、director-thinking-spine、AI execution compiler。

明确机制：先可复述因果；角色即时目标、可行替代和代价；Scene 入/出状态；刺激→理解→目标/策略→对方反应→状态变化；区分 audience knows / character knows / withheld；先修行动过程，再修对白；可读剧本与执行细节分开。冷读要求隔离创作解释，没有隔离必须标记自审。

[before-after 示例](https://github.com/62656456/ai-film-skills/blob/f680c2ed0ba4d3b5692bd779ca8707e47b770d98/examples/director-agent-before-after.md)明确标记 SELF-AUDIT ONLY，不能当独立创作效果证明。[test_function_conservation.py](https://github.com/62656456/ai-film-skills/blob/f680c2ed0ba4d3b5692bd779ca8707e47b770d98/tests/test_function_conservation.py)主要检查文字/机制仍存在；[test_public_contracts.py](https://github.com/62656456/ai-film-skills/blob/f680c2ed0ba4d3b5692bd779ca8707e47b770d98/tests/test_public_contracts.py)检查仓库公开结构/契约，不能证明演员可演或观众感受。本轮未执行这些测试。

风险：其 Director 覆盖写剧本与修因果的范围大于本地 Director；只能把过程审查交给本地 Scene/Screenplay owner。固定窗口、每场必转、两次同策略就删等只能作诊断启发，不能压过原作重复、悬置或梦逻辑。

### E3 — higgsfield-acting

读取 [acting SKILL](https://github.com/OSideMedia/higgsfield-ai-prompt-skill/blob/c0b73ab946df6658cca513db78bdc3909a655bfd/skills/higgsfield-acting/SKILL.md)。可取：objective/obstacle/tactics、listener 也有任务、内心压力不等于单一 emotion label、跨场累积状态。

未验证：仓库提及长片与行业经验，但本文没有独立核验成片或比较实验；示范段本身有 UNPROVEN HERE 声明。[cinema eval cases](https://github.com/OSideMedia/higgsfield-ai-prompt-skill/blob/c0b73ab946df6658cca513db78bdc3909a655bfd/evals/cases/cinema.json)针对 cinema 技能，[lint tests](https://github.com/OSideMedia/higgsfield-ai-prompt-skill/blob/c0b73ab946df6658cca513db78bdc3909a655bfd/tests/test_lint_rules.py)主要是提示规则，不是 acting outcome 测试。

不采用：统一反应必须早于台词结束、统一微停顿、强者静弱者动、固定眼部运动/表情、强制每场若干 beat、所有角色固定长 acting paragraph、模型擅自把做不到的动作换成别的行为。“状态代替过程”会损坏本任务重点保护的因果与接触连续性。Prompt 层替角色编 objective、重写具体实现，违反本地 authority。

### E4 — director-skills

读取 [screenplay-and-scene-writing](https://github.com/0xhughs/director-skills/blob/35ca0a2b4cd55b0668aa9ea0f40273324b774bb4/skills/screenplay-and-scene-writing/SKILL.md)、scene_construction、dialogue_and_subtext；[short-film-development](https://github.com/0xhughs/director-skills/blob/35ca0a2b4cd55b0668aa9ea0f40273324b774bb4/skills/short-film-development/SKILL.md)及 story workflow、logline example；[model-adaptation](https://github.com/0xhughs/director-skills/blob/35ca0a2b4cd55b0668aa9ea0f40273324b774bb4/skills/model-adaptation/SKILL.md)与各自 tests 文档。

可取：Scene 作为交易/冲突过程，目标—战术—阻力—选择—退出状态；对白作为行为；从短片压力与结局反推必要场景。现有本地规则已有大部分。

[screenplay_scene_tests.md](https://github.com/0xhughs/director-skills/blob/35ca0a2b4cd55b0668aa9ea0f40273324b774bb4/skills/screenplay-and-scene-writing/tests/screenplay_scene_tests.md)与 [prompt_translation_tests.md](https://github.com/0xhughs/director-skills/blob/35ca0a2b4cd55b0668aa9ea0f40273324b774bb4/skills/model-adaptation/tests/prompt_translation_tests.md)是 Markdown 检查场景，不是可执行测试通过记录。logline example 是作者示例，不是观众实证。model-adaptation 是模型提示适配，**不是文学影视化改编**；不能用名字填补 Adaptation 审计。未知模型降级模板不能进入本地 Seedance 正式 fail-closed 路线。

## 3. External Capability Forensics

| 能力 | 外部机制/证据 | 本地等价 | Authority overlap | 可能价值 | 风险与 disposition |
|---|---|---|---|---|---|
| ADAPTATION | E1 压缩；E4 从压力/结局组织 | AdaptationContract、compression、CinemaExpression | 原作改编许可在 literary-adaptation | 补“变了什么/为什么电影需要”审查 | 未提供成熟 source-critical 证明；参考，不移交 Director |
| DRAMATURGY | E2 因果/状态 engine | incubation、Story、Scene craft | Scene/Story author | 阻力如何改变下一策略的可审阅记录 | 不新增顶级 skill |
| SCENE | E2/E4 入场→阻力→退出 | SceneBeatBible、working sets | Scene owner | 重要 Scene 过程审阅 | 不统一套公式/强制反转 |
| BEAT | E2 stimulus→response→delta | BeatDPD + transition trigger | 事件在 Scene；心理在 DPD | 明确跨角色回应边 | 不能把每句/每个动作当新 canonical beat |
| DIALOGUE | E2/E4 言语社会行动 | Dialogue Bible、LineDPD | 原文在 Dialogue/Screenplay | 区分信息交代和改变对方 | 不靠“自然口语”替代过程 |
| ACTOR OBJECTIVE | E2 期待对方改变；E3 task | DPD objective + target | DPD 唯一心理解释 | expected response 与实际 response 对照 | 外部 Director 不取代 DPD |
| PLAYABLE ACTION | E3 tactic；E2 策略变化 | DPD tactic、ObservableAction | DPD / Performance 各自心理/身体 | 防“情绪就是指导” | 不自动补小动作 |
| SUBTEXT | E3/E4 表层话与用意 | DPD subtext，源 Dialogue intent | DPD 单源 | 标记多义高风险需更密指导 | 禁新增另一份 Director subtext |
| LISTENER REACTION | E3 listener task；E2 counter-tactic | interaction coverage / partner DPD | partner DPD + Performance | 从有反应字段推进到反馈因果 | 禁统一抢反应时点 |
| SILENCE | E2 silence 也是刺激 | SILENCE/REACTION channel、silent coverage | Scene 功能；DPD 任务；Performance 体现 | 验证等待的对象与后果 | 禁统一删停顿或量化微表情 |
| DIRECTOR PERFORMANCE | E3 scene acting；E2 execution分离 | DirectorPerformanceIntent + projections | 本地 Director WHY，部门 HOW | 紧凑 sidecar 来源绑定 | 拒绝 prompt 自动导演 |
| RHYTHM | E1 时间裁切；E2 代价递增；E4 压力结构 | meta dramaturgy、EditorialRhythmPlan | Story/Scene 内容、Director意图、Editorial实现 | 区分累积、停顿、释放 | 固定秒数/配方不引入 |
| EVALUATION | E2 隔离冷读、earliest break | professional semantic review、source gate | 审阅证据独立于创作权限 | 标识自审、证据范围、分轴评估 | 无独立读者不冒称 independent PASS |

## 4. 最小吸收建议（仅 R3B 输入）

只研究三项：重要 Scene 的行动—回应—策略/关系变化证明；信息释放相对该过程的位置；逐句与倾听/沉默指导的精确 source-bound 交接。优先连接现有 owner、contract 和 review。

不导入外部 Skill、书籍理论体系、模型默认动作或硬节奏比例。不把外部示例当本片质量证据。本文没有执行外部编剧/生成指令。

