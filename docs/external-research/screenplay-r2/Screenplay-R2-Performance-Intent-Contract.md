# Screenplay R2 — Performance Intent Contract

## 权威与最小增量

没有新建 PerformanceIntentSuperSkill、ActorSkill、Director 或 Canon。沿用 Work／Character meaning → Scene purpose → 现有 DPD → ObservableAction／Performance／Blocking／Action → CinematicShotSpec。剧本作者设计源意图，DPD 保存它的可追溯表演投影；不是两份可各自改写的心理真相。

| 所需信息 | 实际 Runtime 位置 | 约束 |
|---|---|---|
| Beat / actor | BeatDPD.scene_id / beat_id / actor | 明确当前演员；听者独立任务 |
| Objective / target / tactic | BeatDPD.direction 原有字段 | 重要 Beat 显式声明；不能只填情绪，也不能让 generator 补 |
| Obstacle | BeatDPD.obstacle | 当前行动阻碍 |
| Turn | BeatDPD.transition_trigger | 保留原字段，不平行新建 turn |
| Playable action | BeatDPD.playability.playable_actions | 复用 ObservableAction；actor、behavior、target，行为有精确源载体 |
| Performance state | BeatDPD.playability.performance_state / state_scope | 唯一合法 scope 是 CURRENT_BEAT；不是 Character／Voice identity |
| Reaction | BeatDPD.playability.reaction | 现有 ObservableAction 类型；动作来自本场可见／可听文本 |
| Source / review | playability.source_scene_hash / source_excerpt / review_evidence | 当前 Scene 哈希、精确载体及作者判断证据 |
| Dialogue exact text | Scene.content.spokenContent[id].text | 单一对白权威，UTF-8 exact hash，不 normalize 或合并 |
| Speaker / target | spokenContent.speakerKey / target | 对照 LineDPD.speaker、Beat.actor、effective.interaction_target |
| Intent / delivery | spokenContent.intent / performanceIntent | 原有意图及说话状态；intent 与 LineDPD.dramatic_action 相等 |
| Subtext | DPD.direction.subtext → effective | 不进入台词；直说也要明确直说的意图，无默认补值 |
| Literal meaning / speakability | LineDPD.playability.literal_meaning / speakability_review | 审阅称谓、施受者、信息负荷、身体状态、作者腔与断句 |
| Fragmentation | LineDPD.playability.fragmentation / dramatic_purpose | CONTINUOUS / INTENTIONAL / INTENTIONALLY_UNINTELLIGIBLE；后两种必须说明目的 |

未增加独立 interruption、response_expected、forbidden_interpretation schema：中断原因放现有 turn／continuity／change，必要禁解放原 DPD.performance_boundaries 或当前 state，不强制每 Beat 堆负面文本。

## 映射和 Gates

`map_screenplay_performance` 收当前 Scene + SceneDPD + actor Beats + LineDPDs；不做创意自动补全。先验证 Scene 指纹、任务、当前状态、动作和反应载体，再要求每条 canonical spokenContent 恰好一个绑定，复用 compose_dpd，验证 exact text hash、speaker、target、intent、delivery、subtext、fragment purpose，返回深拷贝的现有 DPD 和源对白。无旁路字段可覆盖 Camera、Lighting、身份或对白。

`FormalSourceWitness.validate` 在已有 Host 正式 Production Book 审阅入口强制上述检查，并检查正式 spoken inventory 覆盖。这只是现有读取／审阅链的 validation 增量，没有新增 MCP、Service、Storage 或 persistence endpoint。缺项 UNRESOLVED，源变更 STALE，文本／说话人／对象／意图不符明确失败。下游 `attach_cinematic_performance` 对带 R2 witness 的 DPD 还比较 exact text hash 和 target，不能把已改写的 voice/text 成对传入而避开源对白。

称谓串诊断能确定拒绝旧 S02，而不是宣称理解所有自然语言歧义。自由文本语义、动作映射合理性、自然可说性需要有证据的作者审阅及人工创作审阅；文字非空不等于质量认证。可见／可听载体允许相同演员的 canonical speech（说话本身可以是行动），不复制台词到 screenplayAction。

## 兼容与未完成事项

无 playability 的旧 BeatDPD/LineDPD 序列化不输出新空字段，旧 dpd-v1 fixture 的固定哈希仍通过；旧快照可重放。新正式书审阅不允许缺 witness 的旧对象冒充已就绪，也不迁移补造目标。具体 token/provider/generator 路径不变。

本地 R2 sidecar 为 DESIGN_FIXTURE_ONLY，采用源角色称谓，不是正式 Speaker 注册、正式 Scene 写入或 screenplayAuthority 的替换。人工创作采纳后须把真实 canonical Scene／Speaker／Beat IDs 重新绑定并重新计算指纹。Screenplay body 与 sidecar 不构成两个可独立批准的版本：sidecar 绑定完整候选 SHA，并在测试逐行比对白。当前 scope 是前三场，不能宣称整部 R2 已生产就绪。
