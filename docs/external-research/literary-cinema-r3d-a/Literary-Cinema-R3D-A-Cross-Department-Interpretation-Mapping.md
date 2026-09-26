# Literary Cinema R3D-A — Cross-Department Interpretation Mapping

> 2026-09-26 · NON_RUNTIME / ARCHITECTURE DESIGN INPUT · SELF_AUDIT。本文所有新增解释、义务与结构均为审计建议，未获用户采纳、未写入创作源或 Runtime。R3 candidate 保持 NOT_ADOPTED / R3C_BLOCKED_BY_RUNTIME。证据定位、版本及原文锚点见 [Evidence Index](Evidence-Index.md)。

## 同一解释，不同部门问题

建议复用现有 Cinematic Intent 的 item/scope/source/priority/avoid，与 SourceMapEntry、CapabilityRequest、CreativeRecord.source_refs 连接。Interpretive Implication Map 只存“为什么该部门要判断、需要保护什么”，结果引用该部门原件，不存第二份专业方案。本表的批准前提是未来条件，目前所有新增项均 PROPOSED。

以候选 WI-REL（退出不能取消关系，参与不能取消他人自主）、WI-STAR（今夜决定与梦中回指，机制未知）为例：

| 消费者 | Should consume / 精确层级 | question / obligation | professional owner → output | must not consume / author |
|---|---|---|---|---|
| Screenplay/Story/Scene | YES，适用全片或场的选用解释+source/decision refs | 哪些状态变化、知情窗口与因果不可丢？S03延迟非弃枪，S16跟随非保证获救 | Story跨场，Scene场内，Dialogue原话 → 已有剧本/Scene dramaturgy | 不复制 Board 当对白；不新增理论段 |
| Character | YES，人物阶段/关系轴 | 决定、残存感觉与参与程度怎样同时成立？ | Character Dramaturgy → CharacterArc/Character Bible；Driver批准后包装 | 不以 Director观众情绪替换角色信念 |
| Costume / Appearance | CONDITIONAL，获准人物状态及社会处境的资产问题 | 有哪些可证明的自我照料/维护/阶段连续性限制？未知哪些？ | Specialized Asset → CharacterAsset/CostumeAsset；Look临时状态 | 不消费“虚无”并自动造破衣或新脸 |
| Embodiment | YES，获准 package/state 条件 | 什么稳定倾向有证据、何种关系压力下可变？ | Character Embodiment → 有条件的 observable evidence | 不新增人生经历或当前场动作 |
| DPD / Performance | YES，状态边界/当前源行动/已转译观众重点 | 这次接受了多少注意，拒绝什么，哪些改变尚未发生？ | DPD任务，Performance身体，Voice发声；Blocking路径，Action力学 | 不将所有场都归为“麻木”，不复制未来弧到当前表现 |
| Cinematography | YES，perceptual / spatial obligation | 何时观众必须注意星？如何辨别停步与同行、人物与他人生活的关系？ | Camera Bible 的 subject_hierarchy / spatial_readability → 后续Shot | 不独立选文学象征，不凭主题发明动作 |
| Lighting | YES，visibility/关系限制，经Director/Camera转译 | 哪些实际源下的识别关系须成立？场景不能替他否定全部社会生活 | Lighting Bible motivation/visibility_priorities | 不写“虚无灯光”；不能把原夜间改昼 |
| Color | YES，阶段关系和允许不变的边界 | 关系变了是否确需色彩变化？如何不把现实/梦贴成两类？ | Color Script；Grade只负责批准目标匹配 | 不以黑=死、红=危险重建作品意义 |
| Sound | YES，听者/声源/关系义务 | 主人公不注意和世界无声如何区分？邻声与自语怎样避免伪造回答？ | Sound Bible → source/distance/acoustic/attention continuity | 不默认drone、静音或用音效确证树说话 |
| Music | YES，dramatic function/反向情感/须让位条件 | 配乐增添什么？何时会抢先裁定星或替演员贴情绪？ | Music Direction → FilmScorePlan、SceneMusicDecision、cue/yieldPolicy | 不代写戏内歌，不自动悲伤配乐；可NO_SCORE |
| Editorial | YES，跨场回声/不可跳过的认知变化 | 何种事件完成后才能切？S01声音→楼梯→街→星的关系是否保留？ | Editorial Bible / EditorialRhythmPlan；Sound合作 | 不改源因果，不能靠蒙太奇制造原作未有解释 |
| Shot | INDIRECT，批准Camera/Blocking/Action/Editorial + scoped intent | 覆盖是否使每条义务可读？组级回声是否落空？ | Shot Design → Shot/coverage组保留矩阵 | 不补意义、台词、表演心理 |
| Reference Strategy | INDIRECT，专业设计需证明的具体关系 | 哪个参考证明身份/接触/空间，不能证明什么？ | Reference Plan → proof duties | 漂亮参考图不能验证哲学或升级人设 |
| Cinematic Direction | INDIRECT，所有批准专业原件 | 缺哪个可见/可听决定，哪些冲突需回owner？ | existing CinematicShotSpec projection | 不在合成阶段再导演 |
| Prompt Generator | NO raw interpretation；仅最终observable/audible obligations | 每个批准事实是否保留，无法表达是否报上游？ | provider-specific等义投影/coverage receipt | 不消费文学原文解释，不创造意象/心理/时代事实 |

媒介在解释之后：LIVE_ACTION / CG 决定批准事实如何实现，不拥有意义。没有已验证 provider 特殊需要的证据，本案例不使用“把原文哲学直接交给模型”的例外。

## 一条完整的未来 trace（说明性 ID，不新建 Canon）

`A005 + A018–019` → source observation O-S1/O-S4 → hypothesis H-S1/H-S2@vN（带反证A020及原因未知）→ existing Cinematic Intent item（引用相关D02/D04/X02/X04）→ 用户批准当前适用范围 → implication “这两个时刻必须可辨认其关联，不能提前宣布救赎” → Director向Camera/Editorial/Lighting发各自问题 → 各专业原件 source_refs 回指同一版本 → Shot coverage review给出实际实现引用 → CinematicShotSpec → Prompt。

本轮未生成此工作流的正式收据。`interpretation id + version + source pins + scope + confidence + approval status`应随引用可解析；下游只需拿适用问题/限制及原件ref，不必抄整本证据账。

## S01→S02 跨场责任

Story确定跨场状态与信息设计；Scene保存各自入/出及过渡事件；Director确定应保留的社会声/注意变化；Editorial拥有过渡、切换与回声组织；Sound拥有实际连续声音/距离；Camera/Shot提供批准覆盖。没有一个部门可单独把“无人呼唤”改成有人挽留，或用声音把无关邻人改为知道其自杀计划。

当前既有 DirectorScenePlan.transitionIn/Out、cinematic-intent 的 bridges、Editorial.scene_transitions 可以承载，不能说跨场完全无owner。缺的是同一 interpretation pin 下的联合消费与语义审阅证明，而非再造 Transition Department。

## Department interpretation drift 反例

候选批准解释：世界不以他为中心继续生活，他将其体验为无关；现实也确有寒湿、病患、恐惧。

若 Lighting把全城处理成“无任何可辨的人的生活”，Sound消除所有源内人声，Performance把所有朋友/邻人写成沉默冷漠，三个局部风格可能各自自洽，却共同删除A004/A006/A007及本版关系。未来应产生带scope、义务id、专业output pin、冲突证据、repair owner的 DEPARTMENT_INTERPRETATION_DRIFT finding。Director调和全局WHY，各专业重作HOW；若源解释本身有争议回文学/改编owner。不能由Host改灯、加音或改演员动作。

不是一见黑夜或安静就报 drift：A004夜暗和A039寂静有源。需核对的是具体 protected relation 是否被吞掉。确定性部分能检查缺引用/旧版本/批准范围；“画面是否还读得出社会生活”依赖专业语义审阅，后续成片还需实际观察。

## 局部更新与 stale

WI-STAR选用改变：受影响S02/S04的Director、Camera/Lighting/Color（若消费）、Sound/Music（若消费）、Editorial的关联边、相关Shot/IR/Prompt与Book审批应重审。未消费该item的服装原件不因“星”改义自动重写。WI-REL改变可能影响全片Character/Scene/DPD及依赖资产/声音/剪辑，是大范围但仍由实际引用决定。变更审批状态本身亦须进入gate，不能仅盯文本hash。

现有整包hash校验仍适用；本建议不能让消费者拿“其实不相关”为旧指纹开后门。旧媒体保留为历史证据，不再自动可采用或续制。
