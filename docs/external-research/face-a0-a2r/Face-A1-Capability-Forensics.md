# Face A1 — Capability Forensics

审计日期：2026-09-25（Asia/Shanghai）。本轮仅 Face A0–A2R；所有候选均未安装、未实施、未作平台媒体验证。

## FACE_EXTERNAL_CAPABILITY_INVENTORY

K=professional knowledge；W=workflow；P=provider-specific；R=runtime architecture；Q=quality criteria；A=aesthetic preference。复合标签显式保留，不能因含 K 而接受整条。这里拆解的是源码中确实出现的主张；ADAPT 是待 Face A3 讨论，非已采用。

| ID | 原子 capability | 类型 | 冻结来源 | 限定／取舍 |
|---|---|---|---|---|
| F01 | 整体脸形与长宽关系 | K | [A-structure](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L5); [C-anchor](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6) | 记录批准人物差异；不统一瓜子脸或理想比。 |
| F02 | 纵向比例与前后突出程度分离 | K | [A-axes](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L15) | 比例是人物事实的描述轴，不是三等分达标线。 |
| F03 | 眉骨起伏与眼窝深度分离 | K | [A-structure](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L5); [A-axes](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L15) | 眉毛、眼睑、阴影不能替代骨骼；未知不补。 |
| F04 | 颧位、颧宽、前突与面颊软组织分离 | K | [A-structure](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L5); [A-axes](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L15) | 保留独立关系，拒绝高颧必瘦脸。 |
| F05 | 面中纵长与鼻基底／面中凸凹区分 | K | [A-axes](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L15); [A-nose](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/aesthetics.md#L46) | 只吸收关系描述；不吸收饱满才美的规范。 |
| F06 | 下颌相对颧宽及转折 | K | [A-structure](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L5); [C-anchor](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6) | 方窄圆钝均可；无英雄下颌默认。 |
| F07 | 下巴长度形状与前后投射／侧貌 | K | [A-axes](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L15); [A-profile](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/aesthetics.md#L54) | 不能用尖等于前伸；不使用理想角度。 |
| F08 | 眼形、间距、眼睑作为身份差异 | K | [C-anchor](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6); [A-roster](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L70) | 开合受当前表演影响；跨角度比较不得直接比像素宽。 |
| F09 | 自然眉形与眉眼间距 | K | [C-anchor](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6); [A-roster](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L70) | 自然毛发生长与眉妆、眉间紧张分开。 |
| F10 | 鼻梁、鼻尖与鼻翼／宽度 | K | [C-anchor](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6); [A-roster](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L70) | 拒绝统一高细鼻梁。 |
| F11 | 唇形、嘴宽与上下唇比例 | K | [C-anchor](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6); [A-roster](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L70) | 不把笑容、描唇与当前张口写成稳定形态。 |
| F12 | 耳廓身份保持 | K/Q | [B-principle](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/SKILL.md#L41); [A-three](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/realism_vs_refined.md#L170) | 外部只支持保存/检查，不提供完整耳部设计或测量法。 |
| F13 | 发际线身份与局部重建限制 | K/Q | [B-hair](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/prompts.md#L54); [D-duty](https://github.com/Shinning1010/realportrait-ai/blob/35728411922ddf83c612612bc4d2d1c6df8a94a0/skill/realportrait-ai/SKILL.md#L18) | 遮帽区域重建是提案，不能声称还原了未知真实发际线。 |
| F14 | 头发密度、质地与可信毛发 | K/Q | [A-bio](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/realism_vs_refined.md#L73); [B-qc](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/quality-gate.md#L5); [C-anchor](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6) | 保留批准密度长度；不普遍加碎发、灰发或头屑。 |
| F15 | 肤色家族与漂白防护 | K/Q | [B-principle](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/SKILL.md#L41); [B-skin](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/prompts.md#L22); [C-anchor](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6) | 受光颜色不是基础肤色；不按族裔或角色身份自动填色。 |
| F16 | 皮肤区域纹理与可见尺度 | K | [A-skin](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/prompt_craft.md#L116); [B-skin](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/prompts.md#L22) | 按年龄、肤况、妆、景别、光线判断可见度；不要求每张都见毛孔。 |
| F17 | 自然不对称的保存 | K/Q | [B-principle](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/SKILL.md#L41); [A-realism](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/realism_vs_refined.md#L27) | 本地已明确 retain individual asymmetry；保持批准不对称，不强制制造。 |
| F18 | 痣、雀斑、疤等辨识标记 | K | [C-anchor](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6); [B-skin](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/prompts.md#L22) | 来源和批准决定其是否长期/阶段性；不能为真实感随意添加。 |
| F19 | 年龄印象不得被精修改变 | K/Q | [B-principle](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/SKILL.md#L41); [C-anchor](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6) | 本地已禁止自动减龄；加强观察是 F31，不重复建年龄 owner。 |
| F20 | 年龄与眼口区纹理、体积及毛发成熟度核对 | K/Q | [A-bio](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/realism_vs_refined.md#L73); [B-qc](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/quality-gate.md#L5) | 外部仅部分线索；没有跨年龄可靠映射、通用皱纹数量或年龄估计器。 |
| F21 | 身份优先于美化 | K/Q | [B-principle](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/SKILL.md#L41); [A-decouple](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L26) | 本地已有 IDENTITY_WITHOUT_BEAUTIFICATION，非外部首次发现。 |
| F22 | 稳定 anchor 与当前变量分开 | K/W | [C-anchor](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6); [C-variable](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L37) | A3 C15 保持上位；C 的姿态/签名配饰/媒介不自动成为不可变脸身份。 |
| F23 | 身份参考可见性与质量适用性 | W/Q | [D-stop](https://github.com/Shinning1010/realportrait-ai/blob/35728411922ddf83c612612bc4d2d1c6df8a94a0/skill/realportrait-ai/SKILL.md#L138); [B-principle](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/SKILL.md#L41) | 不清楚/遮挡即不可确认；不把参考图暗部推成结构事实。 |
| F24 | 可见、推测、不可确认的面部参考证据 | K/Q | [A-visible](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L104) | 光影可能伪装深眼窝/颧点，观察不等于已批准事实。 |
| F25 | 多角度身份参考及脸部与全身证明分开 | W | [A-three](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/realism_vs_refined.md#L170); [A-proof](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/engineering.md#L5) | 多视图是待检查的证据，不是任意角度永不漂移保证；不生成。 |
| F26 | 表情变化中保持身份 | W/Q | [C-expression](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/prompt-patterns.md#L38); [C-variable](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L37) | 表情属于当前状态；外部九宫格模板不能替代场景表演。 |
| F27 | 多人对比检查结构区别而非只换装饰 | K/Q | [A-roster](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L70) | 吸收结构比较目的；不保证纯文字选项不同等于成像不同。 |
| F28 | 每对四组差异、模板三项触发、两轮上限 | A/W | [A-roster](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L70) | 来源自称治理启发式；不得成通用阈值、自动改脸或重试配额。 |
| F29 | 皮肤物理状态与光照响应分开 | K | [A-skin](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/prompt_craft.md#L116); [A-makeup](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L36) | 保留职责拆分；固定高光位置不是身份，不吸收 universal 半哑光。 |
| F30 | geometry drift 按区域观察 | Q | [B-qc](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/quality-gate.md#L5); [C-drift](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/SKILL.md#L140) | 脸形、眼距、鼻唇与 approved anchor 比；透视表情差异先控制。 |
| F31 | age drift 观察 | Q | [B-principle](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/SKILL.md#L41); [B-qc](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/quality-gate.md#L5); [C-drift](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/SKILL.md#L140) | 未来候选 QC-AGE-DRIFT；本轮不注册；不能从噪声或肤亮断言变年轻。 |
| F32 | beautification drift 观察 | Q | [B-qc](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/quality-gate.md#L5) | 检查未授权瘦颌、大眼、改鼻、磨平年龄与辨识细节。 |
| F33 | 皮肤塑料／蜡／绘制感观察 | Q | [B-qc](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/quality-gate.md#L5); [A-fail](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/engineering.md#L60) | 结合批准真人媒介、妆态、光照与局部证据，不以有没有瑕疵一刀切。 |
| F34 | 眼部与牙齿完整性观察 | Q | [B-qc](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/quality-gate.md#L5) | 形态、反射、重复结构/牙齿漂移；不让更亮更清等于更真实。 |
| F35 | 耳部完整性观察 | Q | [B-qc](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/quality-gate.md#L5); [B-hair](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/prompts.md#L54) | 遮挡合理性、额外耳廓、边界失真；不可见用 UNKNOWN。 |
| F36 | 下颌／下巴漂移观察 | Q | [B-qc](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/quality-gate.md#L5); [A-three](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/realism_vs_refined.md#L170) | 与人物身份和当前视角比；非方颌/尖颌达标。 |
| F37 | 发际线漂移及头发边界观察 | Q | [B-qc](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/quality-gate.md#L5); [B-hair](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/prompts.md#L54) | 角色版本与当前整理/遮挡分开，不将新造发际线当已知。 |
| F38 | 稳定标记漂移观察 | Q | [C-drift](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/SKILL.md#L140); [B-skin](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/prompts.md#L22) | 位置侧别在可见条件下比较；看不清不判消失。 |
| F39 | reference leakage 观察 | Q | [D-duty](https://github.com/Shinning1010/realportrait-ai/blob/35728411922ddf83c612612bc4d2d1c6df8a94a0/skill/realportrait-ai/SKILL.md#L18); [A-visible](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L104) | C15 细化到脸形身份与 pose/gaze/expression/light/camera 来源；D 非验证方法。 |
| F40 | 局部修复、回原锚点、保留其它已批准事实 | W | [B-passes](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/SKILL.md#L85); [B-repair](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/references/quality-gate.md#L18); [D-revision](https://github.com/Shinning1010/realportrait-ai/blob/35728411922ddf83c612612bc4d2d1c6df8a94a0/skill/realportrait-ai/SKILL.md#L91) | 吸收修复范围原则；禁止外部检查失败即自动调用。 |
| F41 | 修已有照片时保留原表情姿态相机 | W | [B-principle](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/SKILL.md#L41) | 只适用于批准编辑基底及保留范围；不能推广成所有镜头继承肖像状态。 |
| F42 | 场景参考自动提供表情、姿态、光照、构图 | W | [D-duty](https://github.com/Shinning1010/realportrait-ai/blob/35728411922ddf83c612612bc4d2d1c6df8a94a0/skill/realportrait-ai/SKILL.md#L18) | 拒绝自动授权；各部门可明确批准借鉴，scene reference 不成为全能 owner。 |
| F43 | 黄金比、三庭五眼、理想角度作为美貌达标 | A | [A-aesthetic](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/aesthetics.md#L28); [A-profile](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/aesthetics.md#L54); [A-academic](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/academic.md#L17) | 不能据此纠正批准人物；描述坐标与理想值强制是不同能力。 |
| F44 | 职业、性格、性别族群类型自动推脸型 | A | [A-auto](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/scripts/generate.py#L271); [A-theory](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/theory.md#L36); [A-prompt](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/prompt_standards.md#L9) | AESTHETIC_OR_STEREOTYPE_HEURISTIC；不能生成历史/文学人物面部事实。 |
| F45 | 通用皮肤段自动加泛红、细纹、半哑光及固定高光 | A/P | [A-inject](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/scripts/generate.py#L507); [A-skin](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/prompt_craft.md#L116) | 年龄占位只换词，中文还固定成年；不具年龄适应能力。 |
| F46 | 冷脸不笑、偏移视线作为身份／真实感铁律 | A/W | [A-realism](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/realism_vs_refined.md#L27); [A-claim](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/prompt_craft.md#L171) | 表演与身份分开，剧情需笑时不能用真实感禁笑。 |
| F47 | 手机感、噪点、失焦、倾斜就是更真实 | A | [A-candid](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/candid_snapshot.md#L8); [D-duty](https://github.com/Shinning1010/realportrait-ai/blob/35728411922ddf83c612612bc4d2d1c6df8a94a0/skill/realportrait-ai/SKILL.md#L18) | 只是风格选择，不是人脸身份或真人充分条件；不重审摄影。 |
| F48 | 精致路线完美皮肤、雕塑化脸部规范 | A | [A-style](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/scripts/generate.py#L426) | 在本任务真人身份职责下禁默认美化；不能据此声称实际模型必然 CG 化。 |
| F49 | 外部最终 prompt 模板、词权重和 provider 语法 | P/W | [A-prompt](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/prompt_standards.md#L9); [C-exec](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/SKILL.md#L37) | 无 same-provider 因果证据；不复制模板，不取得最终 prompt 所有权。 |
| F50 | 外部 CLI、模型路由、安装及 runtime context | P/R | [A-provider](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/scripts/generate.py#L939); [B-context](https://github.com/lovstudio/professional-portrait-skill/blob/923523b861e20b88544706e83b2a8e0726fc5542/SKILL.md#L180); [C-exec](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/SKILL.md#L37) | 依赖仅静态识别；不执行、不安装、不移植反馈审批系统。 |
| F51 | 视频／运动生成及端点切换 | P/W | [C-exec](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/SKILL.md#L37); [A-lock](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/engineering.md#L27) | 只记录排除边界，不进入 Video。 |
| F52 | 学术引文推出 AI 平均脸与词语机理 | A/K | [A-academic](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/academic.md#L17); [A-fail](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/engineering.md#L60) | 审美论文不验证此 skill、模型机理、固定角度或真实演员生成能力。 |
| F53 | 批量锁脸永不漂移／生产效果自我声明 | W/Q | [A-proof](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/engineering.md#L5); [A-claim](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/prompt_craft.md#L171) | 保留为待验证假设；文字记录不是已观察 paired output。 |
| F54 | 结构、妆容与气质解耦，未知不补全 | K | [A-decouple](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L26); [A-makeup](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L36); [A-visible](https://github.com/snowfrost/ai-character-designer/blob/4b531c9e1b429562504ad7ec1db3e20b27df79f5/references/structure_and_makeup.md#L104) | 仅保存 source/approved design 事实；不将化妆视觉效果反写骨相。 |

## IDENTITY / REALISM / BEAUTIFICATION / STYLE / PERFORMANCE

| 类别 | 本轮判断 | 不能混入 |
|---|---|---|
| IDENTITY | 批准人物的形态关系、毛发身份、稳定辨识标记及指定人生阶段 | 职业→骨相；拍摄阴影→永久结构 |
| REALISM | 在当前真人媒介、年龄、状态、光线和可见尺度下具有可信的人类表面与结构 | 更漂亮、更白、更年轻、纹理越多越真 |
| BEAUTIFICATION | 改变眼鼻颌、淡化年龄或消除标记可能改变身份；即便技术完成度高也不能默认 | 不能伪装成去 AI 化 |
| STYLE | 摄影/精修/手机/棚拍/CG 呈现方式受既有 Work 边界约束 | style 不批准人物解剖改变 |
| PERFORMANCE | 表情、视线、肌肉紧张、当下疲劳与情绪的可见行动 | 不能冻结成某人必须永远冷脸/不笑 |

## Facial geometry 的真实覆盖与空白

A 最新结构文件比其 16 型模板细：覆盖额眉眼、颧部、下颌下巴的关系与独立轴；C 有眼鼻唇及标记清单；B 有保存这些特征的目标。它们都不是经过标定的三维人脸模型或医学形态标准。耳部主要是保持与错误检查；发际线主要是编辑边界；完整颅骨、年龄相关体积分布、跨视角几何公差没有经过验证的方法。未知应留空，不为调查清单造能力。

A 内部有冲突：新结构文档强调气质和骨相可解耦，而 auto_bss 与主流程仍按职业/气质给脸型默认；新文档的反模板提醒不能证明旧脚本已停用。必须以原子规则和实际代码分别判定。

## Age Contract Audit

- B 明确锁 apparent age、保留 age-appropriate texture；C 有 age range 及 age drift；本地也有 age_presentation/apparent_age，不能说年龄完全缺失。
- A 提及不同年龄的眼窝、色素与灰白发，但没有可靠的年龄→脸部体积／眼口区／发际线规则。`skin_blocks` 只是替换 age 文本并注入同一纹理段，中文仍写成年；对儿童等尤其不能当已做年龄适配。
- 去眼下阴影、肤色均匀、磨皮在职业照可为请求目标，在剧情中可能擦掉疲劳、年龄或经历。未来需观察是否违背批准年龄与状态，而非强加老年皱纹表。
- F20/F31 是有界候选，不能宣称已获得 age estimator 或可靠 rejuvenation detector。

## Skin Realism Audit

| 现象 | 归属及证据条件 | 禁止默认 |
|---|---|---|
| 基础肤色／既有稳定标记 | Specialized Asset 的来源或批准人物设计 | 族群标签自动推肤色、凭真实感加痣 |
| 疤与皱纹 | 确认稳定性/人生阶段；疤可能由当前伤口演进，动态皱褶也可能是表演 | 所有疤都永久；所有皱纹都是年龄 |
| 汗、尘、红晕、短期痘、妆 | Look Continuity / 当前剧情状态；不确定保留来源限定 | 见瑕疵就清理、每个人都加鼻红 |
| 毛孔／绒毛／局部肌理 | 个体表面条件；可见度由距离、焦点、光照与妆决定 | 无孔就失败、全身要求毛孔细节 |
| 高光／亮度／颜色偏移 | Lighting / Color / Grade 对已批准表面作用 | 写死鼻梁/颧骨每次都亮；提亮等于肤色改白 |
| 塑料、重复纹理、融边 | 输出媒体 observation；需真实图像区域证据 | 仅见形容词就给真实感 PASS |

## AAA / game-realistic face 专项

技术清晰度、光照精致与人类个体身份是不同检查维度。以下是来源支持的候选观察或风险，不是当前试拍的已确诊原因；本轮没有获得该次试拍的图片/请求/配置回放，不能断言模型内部原因或实际 medium pin 错误。

| 调查维度 | 证据支持强度 | 本轮结论 |
|---|---|---|
| 过度对称 | A realism / B asymmetry；本地 medium 已提及 | 检查是否抹去批准差异；天然较对称不应惩罚 |
| 过净皮肤 | B plastic/over-whitened；A refined 默认 | 美化可能抹个体/年龄；不能假定干净皮肤不真人 |
| 均一毛孔 | A 分区域纹理建议 | 可观察均质重复感；无经验证定量阈值 |
| 蜡/塑料表面 | A/B 明确失败词 | 可列 QC 观察；词表不证明修复效果 |
| 过刻画面部平面 | A refined sculpted wording；本地 CG 分支确有 sculpted planes | 是媒介/风格污染风险，非这次输出的已证原因 |
| 理想比例／美化归一 | A aesthetic 数值规范与模板默认；B 反改脸 | 拒绝普遍达标化；保留批准设计 |
| CG 式过清眼睛 | B glassy eyes 与反射完整性 | 检查眼部自然性；没有清晰度越高越假规则 |
| 统一发丝 | B helmet/painted 与 A 碎发词 | 依批准 groom 和画面观察；不自动弄乱头发 |
| 完美发际线 | B plausible hairline、D preservation | 关注是否漂移；没有必须不规则发际线的证据 |
| 过度锐化 | B coherent sharpness；A 禁词猜测 | 仅候选呈现问题；8K 一词必触发塑料的机理说法不成立为证据 |
| 过控高光 | A 自己还默认固定高光部位；B lighting coherence | 必须退 Lighting 按本场判断，不能全脸消高光 |
| 缺少年龄差异 | B age 保持；A 年龄线索 | 需要按年龄/状态观察；没有通用年龄生成模型 |
| 个体不规则性不足 | A 结构对比、B 保留标记；本地 casting 有差异轴 | 可检查模板归一；不得人为给每人造瑕疵 |

真人身份不等于故意粗糙；摄影精致也不等于 CG。上述线索只能通过匹配人物事实与媒体观察联合评估。
