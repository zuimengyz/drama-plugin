# Face A3 — Source / IR / Consumer Mapping

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED

基线：2026-09-25，HEAD `3b286cca94ad3a1683060d4df2a986a6f789236f`。全部建议尚未实施；知识成熟度至多 LOCAL_EXPERIMENTAL，媒体效果 NOT_PLATFORM_VALIDATED。

## 唯一目标链

approved CharacterAsset + upstream批准来源 → exact SourcePin → 现有decision leaf → Reference Plan duties/coverage → 共享pure still_knowledge mapper及receipt → FrameSpec共享CINE_D2 → VisualPromptIR Fact/source、subject/preserve → compile_ir → 当前image_serializer → 既有adapter。

当前代码没有 D2 professional_sources 和该 pure mapper；上述是未来链，不是已完成消费。沿用摄影A3 COPY_LEAF / JOIN_ORDERED_LEAVES / SELECT_SCOPED_ITEM，不新增重写、推理、provider模板operation。FrameSpec actors.identity的适配与formal IR必须来自同一选定事实集，不能一份actor鼻型另一份IR鼻型。

## 事实、理由、观察与知识各自去向

| Source | IR/目的 | Provider是否得到 | 当前消费风险/未来验证 |
|---|---|---|---|
| decisions.face.text | subjects[id].face | YES，既有static/edit选择 | 细节仍是单Fact，不声称逐词像素遵从 |
| surface_state.text baseline + physical_identity.text stable marks | 与face按固定顺序JOIN到同一face Fact | YES，若该主体用途需要 | 不混Look当前汗伤；整叶映射，禁止偷偷挑词 |
| age_presentation.text | subjects[id].apparent_age | static YES；edit按现有policy可能省略 | 需要显式保留时须有批准preserve声明 |
| hair.text / facial_hair.text | subjects[id].hair / beard | static YES；edit检查retained/omitted | 不能改selector暗中变政策 |
| 当前Look的可见肤况/妆/伤污 | subjects[id].visible_condition | static YES；edit用途专门检查 | 由当前scope item选取，不能覆盖baseline |
| 当前Performance expression | action.expression Fact | 按当前serializer | 引用Performance而非肖像表情 |
| Blocking pose/gaze与当前行动 | 既有blocking/action路径 | 按当前serializer | 不从face/reference推导 |
| Reference Plan批准carry/exclude保留声明 | preserve[] Fact | YES，现有preserve section | source-bound原文，不由mapper写新命令 |
| AssetDecision.reason，上游历史年龄解释 | receipt/review依据 | NO | 即使含好看的prompt词也不输出 |
| coverage、VISIBLE/INFERRED/UNCONFIRMED、QC criteria/observations | metadata / QA evidence | NO | 不把UNKNOWN当生成补全指令 |
| rule_id/version/hash + 外部commit/section | provenance only | NO | 不能占用character fact source_refs |

face JOIN固定顺序 face → surface_state → physical_identity，只有该profile已批准且用途选定的叶；缺可选叶省略，缺required叶阻断。每个源叶标明唯一destination；同一事实跨多个source重复时退原owner消歧，不靠mapper摘要去重。baseline用face是因为现有IR无baseline skin字段；visible_condition留当前状态，足以表达而无需新IR。

## Pin 与 receipt 的可信边界

SourcePin引用真实本地原件key/kind/fingerprint（版本由对应不可变原件解析，不新增SourcePin.version），JSON pointer引用其中exact leaf；源pin字符串非空不代表当前/批准/同Work。reserve和begin-submission都从现有store读取真实current和approval，校验owner、Work、character/arc_stage、批准状态、pin/hash、reference bytes/slot/order与leaf文本。调用方自报approved不能代替Host判断。

冻结顺序继承摄影A3：先冻结canonical originals及审批Reference Plan，再生成只含source及mapping rows的普通receipt，计算其hash；D2 professional_sources pin原件及receipt；计算FrameSpec source fingerprint；构造IR Fact.source指receipt行；现有编译器验证source_fingerprint。receipt不得包含最终FrameSpec/IR/prompt hash导致循环；后续execution记录可记录这些hash。

每mapping row含mapping_id、capability/rule refs、唯一author owner、scope、source pins+pointer、operation、target path、selected text hash、retained/omitted及理由。JOIN保留有序全部叶源。Fact.source沿摄影提案使用receipt-key@fingerprint#rows/id，host必须解析回原件；禁止只检查字符串。receipt不能自己授权未批准事实，不创建storage API或权威。

知识rule refs放receipt的knowledge provenance，与fact source列表分离；不塞入AssetDecision限定的source_refs。Reference Plan为正式责任原件；coverage只引用资产字段且不含新身份值。没有新的隐形Face JSON事实仓库。

## Deltas

FACE_SCHEMA_DELTAS=[]。共享CINE_D2是唯一Face必需的生产字段扩展：FrameSpec.professional_sources可空、旧dump精确省略空字段、非空入fingerprint，消费者为共享source resolver/mapper与已有compile_ir；owner为既有Frame compiler，scope仅opt-in still。新源/映射版本使hash改变并走现有requalify，不借旧批准。Face不要求CINE_D1 imaging_character；若联合实施D1，其值必须与Face A5对照双边固定。

Reference roles/requirements、coverage、mapping receipt及QC evidence是现有开放容器内的语义profile，A4需严格校验，不能宣称当前已typed/enforced。拒绝的替代方案：FaceDesign复活、几十个骨骼字段、FaceRealismBible、IR.face_geometry、第二face serializer、扩大reference cap。若现有profile在实现中确实不可达，停止报告具体consumer gap，不能随手扩大scope。
