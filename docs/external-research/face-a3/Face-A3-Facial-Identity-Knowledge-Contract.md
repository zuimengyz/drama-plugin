# Face A3 — Facial Identity Knowledge Contract

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED

基线：2026-09-25，HEAD `3b286cca94ad3a1683060d4df2a986a6f789236f`。全部建议尚未实施；知识成熟度至多 LOCAL_EXPERIMENTAL，媒体效果 NOT_PLATFORM_VALIDATED。

## 最小决定

不新增 FaceRealismAsset、HumanRealismBible、FaceSuperSkill 或 CharacterAsset.face_model。使用既有 CharacterAsset.decisions；给显式选择本 profile 的新批准原件制定语义规则。旧资产不自动迁移，不按词猜测拆分，不把旧 FaceDesign 重新设为 author。CreativeRecord.values 可承载 Reference/QC 的结构化记录，但不能另存一份有权改鼻子的 face truth。

结构化由既有决定键、唯一事实出处、scope、引用和覆盖索引共同实现，不靠几十个新增测量字段。关系描述可为长/宽相对关系、转折、投射与特定人物区别；无默认毫米、理想比例、皮相推骨骼或强制完整解剖表。

## 唯一决定位置与 owner

| 决定 | 正式落点 | 唯一 author / 边界 |
|---|---|---|
| 脸形、纵向/投射、眉骨/眼窝、颧/颊/面中、颌/颏、眼鼻唇、可知耳形 | decisions.face.text | specialized-asset-design；F01–F12；每关系独立叙述，耳只保留已知身份，不扩耳部测量学 |
| 发际线、基础密度/质地 | decisions.hair.text | specialized-asset-design；F13/F14；遮帽未见不能声称恢复真实发际线 |
| 自然眉及眉眼距离 | decisions.face.text | specialized-asset-design；F09；当前描眉/皱眉分别归 Look/Performance |
| 阶段稳定年龄呈现 | decisions.age_presentation.text | specialized-asset-design；F20；casting 提供候选证据，不自动升级事实 |
| 基础肤色家族、稳定区域肤况 | decisions.surface_state.text | specialized-asset-design；F15/F16；本 profile 限为 baseline，不能混当前汗污 |
| 稳定痣、疤、雀斑等辨识标记 | decisions.physical_identity.text | specialized-asset-design；F18；visible_life_history.reason 可解释由来，不重复 author 同一形态 |
| 当前发型扰动、妆、疲劳、临时红/汗/伤/血/污 | Look Continuity 的 hair/skin_condition/fatigue/wounds 等 | look-continuity；伤疤何时成为阶段稳定事实须原 owner 新版本批准，QA不能搬运 |
| 表情与肌肉紧张 | Performance 原件 | dramatic-performance-direction；不能用冷脸替代真实感 |
| 当前站位、姿势、视线 | Blocking 原件 | blocking；identity reference 无自动权限 |
| 相机、光线、grade/imaging | 各摄影/灯光/调色原件；GlobalStyle媒介边界 | 各自唯一 owner；不可重写鼻、颌、年龄、肤色身份 |
| 人物结构差异的候选比较 | Casting discriminants/proofs | performance-casting；选择后由正式资产承接批准决定 |
| 观察和修复建议 | QA + Production Review | QA author observation；原事实 owner author repair，Production 才处理执行请求 |

F29/F54 是责任分离规则，不创造一个共同 owner。每个 record 必须说明是 baseline、current state 还是 imaging；mixed leaf 在 opt-in path 退回原 owner 澄清，不由 mapper 删除不喜欢的词。发须使用既有 facial_hair；非面部 body 等字段保持原职责。

## 年龄及皮肤

chronological/source age 属历史/人物上游事实，不直接等于看起来几岁。apparent casting age 是选角意图；批准资产在特定 arc_stage 固定 age_presentation。F20 只要求核对该人物已经批准的眼口区域形态/体积/毛发成熟特征：结构放 face，纹理放 surface_state，发放 hair，年龄摘要不重复发明这些特征。年龄数字绝不生成通用皱纹数量。生病、熬夜、红肿是当前 Look；美化造成的减龄由 F31/F32 比对，不能靠加皱纹把错误脸变老。

基础肤色不从族群/职业标签填值，也不等于某张参考受光 RGB。baseline、当前状态与反射/色调各有不同 source。真人不要求毛孔、黑眼圈、痘、鼻红、灰尘或固定半哑光；干净、对称、漂亮、无皱纹都可合法。已有批准不对称按 KEEP_LOCAL 保持，不强制制造新不对称。

## 覆盖与不确定性

新 profile 的 coverage 记录在现有 Reference Plan.requirements 中，以 capability_id + canonical field pointer 引用，禁止在索引中重写脸部值。每 facet 标 REQUIRED_FOR_USE / OPTIONAL / NOT_OBSERVABLE_FOR_USE（这是新设计 metadata 词汇，不是新增生产 enum）。配独立 evidence_state：VISIBLE / INFERRED / UNCONFIRMED；推测只有经适当 adaptation/design 审批才能进入正式资产，不能凭分类自动通过。

REQUIRED 未批准或证据不足则请求原 owner 解决当前用途，不能自动补全。OPTIONAL 未知省略；不要求每人写所有35项。遮挡可使媒体检查 UNKNOWN；不撤销已知身份。覆盖索引 hash 绑定资产版本/字段与审批的 Reference Plan，只有原件文本是事实。若旧整段含冲突或无法准确绑定，重写并重新批准整段；不引入 NLP 隐式裁判或新 text-span 编辑语言。

## 反审美与反刻板

更大眼、更小鼻、更尖颌、更光滑、更年轻、完全对称、时尚整理都可能是审美选择，必须有该角色批准设计；无权称为通用 human realism。将军→方颌、反派→窄眼、知识分子→苍白瘦脸、穷人→粗皮肤、贵族→无瑕均标 AESTHETIC_OR_STEREOTYPE_HEURISTIC，REJECT FROM CANONICAL IDENTITY。禁止从气质/职业/性别族群标签自动推结构。

历史人物允许明确的 casting/adaptation 审美选择，但不能伪称史实；有史料则标来源与不确定性，无面貌证据可做批准创作，不能默用现代美貌覆盖，也不能把历史真实等同丑化。

## 来源、成熟度与版本

knowledge-contract-draft.json 恰有35条新 rule，逐条 rule_id/version/hash、外部 source commit/section/文件sha256、local owner、scope、adaptation type、validation status。hash 定义在文件内；任何边界/来源变化须新版本新hash。来源 A 无许可证，故只独立表述知识并保留 attribution，不拷贝文本包/代码；B/C/D 的限制继续随前轮原件保存，没有来源升级为 VALIDATED_EXTERNAL。

知识引用只是 provenance。AssetDecision.source_refs 仍只接受当前允许的 Director/Dramaturgy/World pins，并含自身 Dramaturgy。casting/media 决定需经既有批准设计链承接，相关候选证据另在 Reference/审批记录精确引用，不冒充可直接写入 AssetDecision.source_refs。缺这条批准链就不能把候选写成已批准事实。LOCAL_EXPERIMENTAL 表示本地设计候选，绝不意味着媒体已验证。
