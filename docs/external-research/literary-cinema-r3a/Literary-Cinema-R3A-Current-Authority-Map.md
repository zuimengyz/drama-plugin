# Literary Cinema R3A — Current Authority Map

> 审计日期：2026-09-26。源码基线：`bb83843074ae685a5fdd53ed94b1a27bd863a014`。范围：NON_RUNTIME / NO SCREENPLAY REWRITE / NO MEDIA GENERATION。本文的未来设计建议不是已实施能力，也不是剧本批准。

当前不是“没有文学改编和导演表演能力”。现有源码同时存在 source-bound 改编链、Scene 戏剧过程规范、DPD 心理语义、Director 表演意图及正式逐句覆盖审阅链。断点主要在粒度、交接和验证：能证明来源与动作载体，不等于证明信息在阻力和回应中出现；R2 候选能映射到 DPD，不等于已拥有当前版本的正式 Director Performance 覆盖。

## 1. 证据边界与实际基线

重新读取当前源码、Skill、当前 R2 正文和 sidecar；旧报告仅作为历史，不作为实现证据。没有读取线上持久化 Work 树，因此不能宣称线上 Production Book 已通过或失败。此次文本诊断有用户问题和既有创作背景，属于上下文内审计，不是独立冷读，也不是演员/观众实测。

- [当前 R2 正文](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/screenplay-r2/04-screenplay-r2.md)：SHA-256 `dae155c1d27e6091d8277e773fa22e1ca20b549e6a3e936322256a246b425c08`。
- [R2 performance-sidecar](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/screenplay-r2/performance-sidecar.json)：DESIGN_FIXTURE_ONLY、未 adopted；仅 S01–S03，10 个 actor beats、12 个 dialogue turns。
- [源包](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/literary-package.json)、[screenplay 结构](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/screenplay.json)、[Dramatic Bible](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/dramatic-bible.json)、[旧版 Director screenplay](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/director-screenplay.json)均单独审计。
- screenplay.json 的 B01–B16 每项覆盖完整 Scene，明确不等于 performance micro-beat。R2 的 actor beat 又是另一粒度；不能按同名 Beat 推定一一对应。
- director-screenplay.json 源绑定仍为 R1；它可说明既有导演意图，不能充作当前 R2 已接通的意图凭证。不同文件使用原始文本哈希与 canonical JSON 哈希，不直接混比。

## 2. 实际链路与验证强度

```text
SourceArtifact + SourceAnchor
 → LiteraryAnalysis（原作事实/叙述次序）
 → PhilosophicalCore
 → Literary Adaptation（Preservation + AdaptationDecision）
 → DramaticCompression mappings
 → CinemaTranslation
 → compiled ScreenplayInput + source_map
 → Work/Script + screenplay incubation / Story / Scene authoring
 → approved Scene / exact SpokenContent
 → SceneDPD → BeatDPD → LineDPD → composed DPDSnapshot
 → DirectorPerformanceIntent + Performance / Voice projections
 → reviewed Blocking / Action / Camera / Editorial
 → CinematicShotSpec / visual IR
 → model-specific prompt projection
```

真实源码把 Adaptation 决策放在 CinemaExpression 之前；不能为了符合概念图，倒置已实现的 authority。DirectorWorkspace 接收编译后来源；不是第二次做小说分析。

| 层级与证据 | 结构化程度 / 输出 | 真正消费者与验证 | 对 Screenplay 的作用与限制 |
|---|---|---|---|
| [Source 合同](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/creative_source.py:32) | Artifact 文本哈希、Anchor 偏移/引文、SourceUnit | validate_literary 检查锚点和引用 | 证明引用来源，不自动证明改编忠实 |
| [分析/哲学/改编](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/creative_source.py:62) | event_order、question/value poles、Preservation、permitted_changes、decisions | [validate_literary](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_source.py:74) 检查全集、决策映射、REMOVE 保护、review hashes | 保留边界是上游约束；没有把小说顺序强制变成电影顺序 |
| [压缩/电影表达](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/creative_source.py:112) | decision→destination IDs；channels、shootable_expression、choice_action_consequence、nonverbal alternative | 映射/显性解释例外/阶段审阅校验 | 已能传达心理外化方向；具体 Scene 过程仍须作者落实 |
| [compile_source](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_source.py:224) | ScreenplayInput + source_map + resolved_input | Work/Script 输入一致性验证；Host pin | validate_script_content 比较输入契约，不分析正文戏剧质量 |
| [Director source_intent](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/director.py:235) | 原样投影哲学、改编、角色弧、电影表达与 revision owner | [CreativeSourceHost](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/hosts/creative_source.py) → workspace/artifact store | 不接收原文重新解释；变更返回上游 |
| [incubation Bible](/Users/zy/historical-plugin/drama-plugin/plugin/skills/cinematic-screenplay-incubation/references/bible.md:29) | working JSON + 可读正文；knowledge receipts 有 beforeBeat | 可选 check_incubation 验证状态/知识记录；专业阅读正文 | 已有 WHEN 的一部分，但不是观众信息释放的全过程证明 |
| [R2 playability](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/screenplay_playability.py:31) | 动作来源 witness、精确台词 hash、DPD snapshots | 检查 source/actor/target/intent、动作子串、歧义/片段声明 | 不检查行动顺序、对方反馈因果、信息是否过早 |
| [Director intent](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/contracts/performance_direction.py:37) | audience experience、containment/release、partner、rhythm/continuity | validate_intent / validate_projection | 已有“为什么这样演”的正式位置；不是 actor psychology 的第二 owner |
| [正式 coverage Host](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/hosts/formal_performance.py:37) | 从当前持久化源枚举 spoken/silent/interactions 等 | [full coverage](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/performance_coverage.py:121) 与 [Book completion](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/preproduction.py:305) | 每句覆盖与双通道投影已有；本次候选没有自动进入正式链 |
| [cinematic assembly](/Users/zy/historical-plugin/drama-plugin/plugin/skills/cinematic-direction/SKILL.md) | 已审阅部门事实投影 | source pins / DPD 一致性 / IR 检查 | 不负责补戏剧过程 |
| [Seedance generator](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/prompt_generators/seedance_2/generator.py:74) | 来源 atoms、coverage、模型表达 | 缺动作/可观察载体等显式 UNRESOLVED | 忠实翻译弱上游仍会得到弱戏；语义覆盖不等于戏剧质量 |

## 3. LITERARY_CINEMA_AUTHORITY_MAP

以下为当前 authority 的归纳；最后一栏明确不能越界。当前能力的连接缺口另见 gap reports。

| 层 | Knows | Owns | Emits | Consumed by | Can modify | Cannot modify |
|---|---|---|---|---|---|---|
| Source Canon | 指定版本原文、来源 | 原作事实与锚点 | SourceArtifact/Unit | 分析、改编 | 授权来源更正 | 以电影需要改原文事实 |
| Preservation | 关键人物/关系/因果/思想/弧线 | 改编保护边界 | preserved、must_keep | Adaptation、review | 经上游批准修订边界 | 下游静默豁免 |
| Cinema Translation | 已批准决策、可用电影通道 | 心理意义如何可拍的表达方案 | CinemaExpression | ScreenplayInput、作者 | 决策内表达载体 | 无授权新关键事件/新思想 |
| Adaptation | 原作、保护范围、版本选择 | 变更自由与来源解释 | AdaptationDecision/Contract | compression、cinema、story | 授权 reorder/merge 等 | 绕过 preserved 或权利边界 |
| Work / Script | compiled source、作品/版本目标 | 对应层故事事实与脚本组织 | Work/Script content | Story、Scene、Director | 授权版本内组织 | 重写 source canon |
| Story | 版本冲突、人物弧、结局 | 全片因果、结构与层级节奏 | Story Bible | Scene、script author | 幕/段/Scene 组织 | 自行扩大改编许可 |
| Scene | 场景状态、人物关系、上游事实 | Scene 过程、目的、冲突与场内事件/信息安排 | Scene Beat Bible、正文 | Dialogue、DPD、Director | 授权创作阶段 beat 组织 | 冻结后由下游暗改 |
| Beat | Scene 内行动/回应与状态变化 | 属 Scene Dramaturgy 的过程单位；DPD 只解释角色任务 | 源 beat + actor DPD | Performance、Blocking | 上游 author 改过程 | 把 actor beat 当独立剧情 Canon |
| Dialogue | 正式用词、speaker/target、语义 | 台词原文；authoring 下的言语行动 | SpokenContent / Dialogue Bible | DPD、voice、prompt | screenplay 授权的对白创作/修订 | Performance 擅改文学台词 |
| Director | 源、DPD、全片观众体验 | WHY、重点、强度/释放、节奏意图、审阅仲裁 | Vision、DirectorPerformanceIntent | 部门、Book | 解释/取舍已批准实现 | 再造 objective/subtext、改事件/台词 |
| Performance / DPD | 源 Scene、角色、Dialogue | DPD 唯一 objective/obstacle/tactic/subtext；独立 facet 拥有身体实现 | DPD + Performance Bible | visual/voice、Blocking、assembly | 来源支持的解释及可观察体现 | 改人物目标事实、对白、路径/力学 |
| Character Dramaturgy | 身份、长期欲求、角色弧 | 稳定人物逻辑 | Character Bible/Package | Scene、DPD、embodiment | 授权角色发展 | 替代当前 beat intention |
| Character Embodiment | 角色包与阶段 | 稳定身体/行为倾向 | source-traced embodiment | appearance、Performance | 有依据的倾向 | 凭心理标签新造本场动作 |
| Blocking | 任务、空间、听见/看见 | 路径、站位、目光关系 | Blocking Bible | Action、Shot、Performance | 批准场内空间实现 | 改目标和事件结果 |
| Action | 批准动作、接触/物件状态 | 身体力学、顺序和可行性 | Action Bible | Shot、IR | 物理实现 | 新戏剧策略或结果 |
| Editorial | 已有 coverage、信息/动作义务 | 剪切、持留、反应时间、获准压缩 | EditorialRhythmPlan | Shot、edit | 呈现时点与切换 | 改角色知情/因果需先回 Scene |
| Shot | approved camera/blocking/action/editorial | 覆盖与起终状态 | Shot / spec | compilation | 镜头覆盖组织 | 以新镜头掩盖缺失的戏 |
| Prompt | 批准 IR、输入、模型规则 | 表达、排序、去重、覆盖验证 | 最终 prompt | Adapter | 等义模型表达 | 猜目标/回应/事件/台词 |

注册关系依据：[professional.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/professional.py)；部门职责依据当前 [Scene](/Users/zy/historical-plugin/drama-plugin/plugin/skills/scene-development/SKILL.md)、[Director](/Users/zy/historical-plugin/drama-plugin/plugin/skills/director/SKILL.md)、[DPD](/Users/zy/historical-plugin/drama-plugin/plugin/skills/dramatic-performance-direction/SKILL.md)、[Blocking](/Users/zy/historical-plugin/drama-plugin/plugin/skills/blocking/SKILL.md)、[Action](/Users/zy/historical-plugin/drama-plugin/plugin/skills/action-choreography/SKILL.md)、[Editorial](/Users/zy/historical-plugin/drama-plugin/plugin/skills/editorial-design/SKILL.md)。这些文件是本轮被审计对象，没有运行它们的创作/生成流程。

## 4. 不能混为一谈的三种 PASS

1. 来源/结构 PASS：hash、ID、exact dialogue、source carrier 一致。
2. 专业设计审阅 PASS：审阅者认为过程、策略、信息时机成立；应保留理由与反例检查。
3. 观众/演员/媒体结果：需要后续实证。本轮没有这种证据。

现有 semantic_review 的 PASS 是审阅声明，不是代码理解了戏剧。R2 已改善第一种，也提供第二种输入；不能因此宣称第三种成功。

