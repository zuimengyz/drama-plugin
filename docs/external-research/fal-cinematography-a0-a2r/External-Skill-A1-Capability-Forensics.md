# External Skill A1 — Capability Forensics

## EXTERNAL_CAPABILITY_INVENTORY

这是来源法证清单，不是本地 Skill 或待执行指令。每条含真实外部出处、输入输出、外部 decision owner、运行行为与验证局限。`produces_prompt_text` 描述外部行为；K/Q 即使产出文字，也不因此取得本地 prompt ownership。

K=专业知识；W=流程；P=provider 细节；R=runtime 架构；Q=质量门。条目使用一个主分类，交叠行为通过独立条目拆分。`both` 仅准许本轮审计它的 still 投影，所有时间轴执行仍排除。

主摄影 Skill 的全部语义已覆盖 C01–C14、C22–C24、C27、C36、C38；角色/写实/GPT/叙事依赖只增加指定切片。Inventory 的完整机器可读版本在 [capabilities.json](evidence/capabilities.json)，不是 Runtime registry。

### C01 — 按镜头需要收集输入

来源：[skills/cinematography/SKILL.md § ## Inputs to collect](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L22)。

```json
{
  "capability_id": "C01",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/SKILL.md",
    "section": "## Inputs to collect",
    "line": 22,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L22"
  },
  "classification": "W",
  "purpose": "按镜头需要收集输入",
  "inputs": "主体、动作、任务、构图、光线、格式",
  "outputs": "镜头 brief",
  "decision_owner": "外部 cinematography agent",
  "runtime_behavior": "收集缺失输入并开始执行准备",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": false,
  "dependencies": [
    "model-routing"
  ],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "外部 medium 一词混用任务类型；不能当 Work visual medium。"
}
```

### C02 — 景别与可读内容

来源：[skills/cinematography/references/shot-language.md § ## Shot sizes](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/shot-language.md#L3)。

```json
{
  "capability_id": "C02",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/references/shot-language.md",
    "section": "## Shot sizes",
    "line": 3,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/shot-language.md#L3"
  },
  "classification": "K",
  "purpose": "景别与可读内容",
  "inputs": "可读细节、人物/环境关系",
  "outputs": "景别选择",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "以可读身体/环境范围描述镜头",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": ""
}
```

### C03 — 相机角度、高度、视点

来源：[skills/cinematography/references/shot-language.md § ## Angles](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/shot-language.md#L13)。

```json
{
  "capability_id": "C03",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/references/shot-language.md",
    "section": "## Angles",
    "line": 13,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/shot-language.md#L13"
  },
  "classification": "K",
  "purpose": "相机角度、高度、视点",
  "inputs": "观众与人物空间关系",
  "outputs": "角度/视点意图",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "给角度和常见情绪联想",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "情绪联想是选项；低角度不能自动升级人物权力。"
}
```

### C04 — 相机距离与透视一致性

来源：[skills/cinematography/SKILL.md § ## Quality bar](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L132)。

```json
{
  "capability_id": "C04",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/SKILL.md",
    "section": "## Quality bar",
    "line": 132,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L132"
  },
  "classification": "Q",
  "purpose": "相机距离与透视一致性",
  "inputs": "lens、景别、角度",
  "outputs": "一致性 review",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "发现互相矛盾的镜头描述",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": false,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": ""
}
```

### C05 — 构图选项和主体层级

来源：[skills/cinematography/references/shot-language.md § ## Composition](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/shot-language.md#L35)。

```json
{
  "capability_id": "C05",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/references/shot-language.md",
    "section": "## Composition",
    "line": 35,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/shot-language.md#L35"
  },
  "classification": "K",
  "purpose": "构图选项和主体层级",
  "inputs": "注意力、空间与画幅",
  "outputs": "对称/留白/前景/线条等选择",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "将常见构图关联表现意图",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": ""
}
```

### C06 — 焦段语言

来源：[skills/cinematography/references/lighting-lens-color.md § ## Lens feel](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L16)。

```json
{
  "capability_id": "C06",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/references/lighting-lens-color.md",
    "section": "## Lens feel",
    "line": 16,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L16"
  },
  "classification": "K",
  "purpose": "焦段语言",
  "inputs": "视角、距离、任务",
  "outputs": "焦段 feel",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "提供 wide/normal/tele/macro 语汇与常见用途",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "不是精确物理模拟或自动给定 mm；保留距离和视觉目标。"
}
```

### C07 — 景深与静态焦平面

来源：[skills/cinematography/references/lighting-lens-color.md § ## Depth of field](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L26)。

```json
{
  "capability_id": "C07",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/references/lighting-lens-color.md",
    "section": "## Depth of field",
    "line": 26,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L26"
  },
  "classification": "K",
  "purpose": "景深与静态焦平面",
  "inputs": "主体关系和可读区域",
  "outputs": "浅/深景深意图",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "隔离主体或保持环境/关系可读",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "rack focus 拆到 C08。"
}
```

### C08 — 运镜与拉焦

来源：[skills/cinematography/references/shot-language.md § ## Camera movement](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/shot-language.md#L23)。

```json
{
  "capability_id": "C08",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/references/shot-language.md",
    "section": "## Camera movement",
    "line": 23,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/shot-language.md#L23"
  },
  "classification": "K",
  "purpose": "运镜与拉焦",
  "inputs": "动作、揭示、空间变化",
  "outputs": "push/pull/tracking/rack-focus intent",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "视频时间内移动相机或焦点",
  "provider_specific": false,
  "target_modality": "video",
  "produces_prompt_text": true,
  "dependencies": [
    "skills/cinematography/references/lighting-lens-color.md § Depth of field"
  ],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "FUTURE_VIDEO_ROUND。"
}
```

### C09 — 动机光与光型

来源：[skills/cinematography/references/lighting-lens-color.md § ## Lighting setups](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L3)。

```json
{
  "capability_id": "C09",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/references/lighting-lens-color.md",
    "section": "## Lighting setups",
    "line": 3,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L3"
  },
  "classification": "K",
  "purpose": "动机光与光型",
  "inputs": "空间、实际灯具、时间",
  "outputs": "光源/方向/硬软/反差",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "选择 light setup",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": ""
}
```

### C10 — 色彩与 mood grade

来源：[skills/cinematography/references/lighting-lens-color.md § ## Color and grade](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L32)。

```json
{
  "capability_id": "C10",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/references/lighting-lens-color.md",
    "section": "## Color and grade",
    "line": 32,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L32"
  },
  "classification": "K",
  "purpose": "色彩与 mood grade",
  "inputs": "情绪与材质可读性",
  "outputs": "palette/grade intent",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "色调关联情绪与用途",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "palette 归 Color；实拍后匹配归 Grade，不增第三 owner。"
}
```

### C11 — 胶片/光学质感选项

来源：[skills/cinematography/references/lighting-lens-color.md § ## Texture](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L42)。

```json
{
  "capability_id": "C11",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/references/lighting-lens-color.md",
    "section": "## Texture",
    "line": 42,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/lighting-lens-color.md#L42"
  },
  "classification": "K",
  "purpose": "胶片/光学质感选项",
  "inputs": "拍摄感、光源与画面用途",
  "outputs": "grain/halation/bloom/shutter target",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "提供质感词汇",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "可选，不强加噪点或运动模糊。"
}
```

### C12 — SCLCAM 最终 Prompt 顺序

来源：[skills/cinematography/SKILL.md § ## Prompt build order](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L94)。

```json
{
  "capability_id": "C12",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/SKILL.md",
    "section": "## Prompt build order",
    "line": 94,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L94"
  },
  "classification": "W",
  "purpose": "SCLCAM 最终 Prompt 顺序",
  "inputs": "镜头方向",
  "outputs": "最终生成文本",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "按固定次序拼接含 controls 的 prompt",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "字段覆盖可参考；不得增加 final-prompt writer。"
}
```

### C13 — 具象描述代替空泛赞词

来源：[skills/cinematography/SKILL.md § If a result looks generic](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L144)。

```json
{
  "capability_id": "C13",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/SKILL.md",
    "section": "If a result looks generic",
    "line": 144,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L144"
  },
  "classification": "K",
  "purpose": "具象描述代替空泛赞词",
  "inputs": "generic result 的诊断",
  "outputs": "相机/光线/环境的具体改进要求",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "要求提升可见事实具体性",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "由原 owner 修改事实，不让 compiler 创作。"
}
```

### C14 — 静态模态边界

来源：[skills/cinematography/SKILL.md § 4. Camera motion](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L101)。

```json
{
  "capability_id": "C14",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/SKILL.md",
    "section": "4. Camera motion",
    "line": 101,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L101"
  },
  "classification": "K",
  "purpose": "静态模态边界",
  "inputs": "still 或 video 任务",
  "outputs": "静态可见状态/视频运动区分",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "still 仅在需要时表达可见 motion blur",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "still 的 blur 是画面属性，不是连续动作。"
}
```

### C15 — 角色 anchor 与变量分离

来源：[skills/character-design/references/anchor-system.md § ## Anchor fields](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6)。

```json
{
  "capability_id": "C15",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/character-design/references/anchor-system.md",
    "section": "## Anchor fields",
    "line": 6,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/references/anchor-system.md#L6"
  },
  "classification": "K",
  "purpose": "角色 anchor 与变量分离",
  "inputs": "身份参考与允许变化",
  "outputs": "身份不变量/镜头变量",
  "decision_owner": "外部 character-design",
  "runtime_behavior": "重复 anchor 并分离 pose/light/camera 变量",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "dependency read；只吸收与摄影连续性有关的拆分，不吸收角色创作全 Skill。"
}
```

### C16 — 写实编辑避免复述脸部

来源：[skills/fal-recipes/references/realism.md § ## Identity preservation](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L251)。

```json
{
  "capability_id": "C16",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-recipes/references/realism.md",
    "section": "## Identity preservation",
    "line": 251,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L251"
  },
  "classification": "P",
  "purpose": "写实编辑避免复述脸部",
  "inputs": "具体人物参考图",
  "outputs": "省略面部细节的 edit prompt",
  "decision_owner": "外部 realism recipe",
  "runtime_behavior": "使用 edit/reference 并避免 face 重描述",
  "provider_specific": true,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [
    "skills/fal-prompting/references/gpt-image-2.md"
  ],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "保留 required face anchor；外部未证明跨 Comfy 同样更好。"
}
```

### C17 — 角色漂移质量检查

来源：[skills/character-design/SKILL.md § ## Quality bar](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/SKILL.md#L140)。

```json
{
  "capability_id": "C17",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/character-design/SKILL.md",
    "section": "## Quality bar",
    "line": 140,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/character-design/SKILL.md#L140"
  },
  "classification": "Q",
  "purpose": "角色漂移质量检查",
  "inputs": "输出与 anchor",
  "outputs": "identity/costume/style drift findings",
  "decision_owner": "外部 character-design",
  "runtime_behavior": "发现漂移则拒绝或重试",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": false,
  "dependencies": [
    "skills/character-design/references/anchor-system.md"
  ],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "观察依据＋用途严重度，不把任何差异自动判 FAIL。"
}
```

### C18 — GPT 分节 Prompt 模板

来源：[skills/fal-prompting/references/gpt-image-2.md § ## Prompt structure](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L18)。

```json
{
  "capability_id": "C18",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-prompting/references/gpt-image-2.md",
    "section": "## Prompt structure",
    "line": 18,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L18"
  },
  "classification": "P",
  "purpose": "GPT 分节 Prompt 模板",
  "inputs": "镜头 brief",
  "outputs": "五段 final prompt",
  "decision_owner": "外部 fal-prompting",
  "runtime_behavior": "按模型专用模板输出",
  "provider_specific": true,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "只作为未来 provider serializer 候选，不覆盖 Canonical authoring。"
}
```

### C19 — 编辑 change/preserve 分离

来源：[skills/fal-prompting/references/gpt-image-2.md § ### Mode 2](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L56)。

```json
{
  "capability_id": "C19",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-prompting/references/gpt-image-2.md",
    "section": "### Mode 2",
    "line": 56,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L56"
  },
  "classification": "K",
  "purpose": "编辑 change/preserve 分离",
  "inputs": "exact source、edit target",
  "outputs": "修改/保留/约束",
  "decision_owner": "外部 fal-prompting",
  "runtime_behavior": "定向 edit，保护无关区域",
  "provider_specific": false,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "本地已实现且测试；无需重复模板。"
}
```

### C20 — 多参考图角色绑定

来源：[skills/fal-prompting/references/gpt-image-2.md § ### Mode 3](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L68)。

```json
{
  "capability_id": "C20",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-prompting/references/gpt-image-2.md",
    "section": "### Mode 3",
    "line": 68,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L68"
  },
  "classification": "K",
  "purpose": "多参考图角色绑定",
  "inputs": "多张已知图片",
  "outputs": "每个输入的责任",
  "decision_owner": "外部 fal-prompting",
  "runtime_behavior": "按角色标记输入并规定保持内容",
  "provider_specific": false,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": ""
}
```

### C21 — fal image 参数与 16 图容量

来源：[skills/fal-prompting/references/gpt-image-2.md § ## Common parameters](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L132)。

```json
{
  "capability_id": "C21",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-prompting/references/gpt-image-2.md",
    "section": "## Common parameters",
    "line": 132,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L132"
  },
  "classification": "P",
  "purpose": "fal image 参数与 16 图容量",
  "inputs": "fal endpoint schema",
  "outputs": "provider payload",
  "decision_owner": "外部 fal-prompting/genmedia",
  "runtime_behavior": "映射 size/quality/image_urls/mask 等字段",
  "provider_specific": true,
  "target_modality": "still",
  "produces_prompt_text": false,
  "dependencies": [],
  "validation_evidence": {
    "classification": "REFERENCE_ONLY",
    "confidence": "HIGH",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "16 为 fal edit；不是本地三图 gate 的错误。mask_image_url 与当前 fal 文档 mask_url 不同；input_fidelity 未列出。"
}
```

### C22 — 静态模型排名与回退

来源：[skills/cinematography/SKILL.md § ## Model routing](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L114)。

```json
{
  "capability_id": "C22",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/SKILL.md",
    "section": "## Model routing",
    "line": 114,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L114"
  },
  "classification": "P",
  "purpose": "静态模型排名与回退",
  "inputs": "质量/成本偏好",
  "outputs": "endpoint 顺序",
  "decision_owner": "外部 model-routing",
  "runtime_behavior": "GPT→其他模型/fast draft",
  "provider_specific": true,
  "target_modality": "still",
  "produces_prompt_text": false,
  "dependencies": [
    "skills/model-routing/SKILL.md"
  ],
  "validation_evidence": {
    "classification": "REFERENCE_ONLY",
    "confidence": "HIGH",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "不能凭外部排名改 route；没有 comparative benchmark。"
}
```

### C23 — schema 和成本先验检查

来源：[skills/cinematography/SKILL.md § 2. Inspect schema](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L57)。

```json
{
  "capability_id": "C23",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/SKILL.md",
    "section": "2. Inspect schema",
    "line": 57,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L57"
  },
  "classification": "Q",
  "purpose": "schema 和成本先验检查",
  "inputs": "候选 endpoint",
  "outputs": "已知能力/成本",
  "decision_owner": "外部 genmedia",
  "runtime_behavior": "检查实际字段与费用后执行",
  "provider_specific": true,
  "target_modality": "both",
  "produces_prompt_text": false,
  "dependencies": [
    "skills/genmedia/SKILL.md"
  ],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "原则一致，CLI 不继承。"
}
```

### C24 — genmedia 提交/轮询/下载

来源：[skills/cinematography/SKILL.md § ## Genmedia workflow](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L37)。

```json
{
  "capability_id": "C24",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/SKILL.md",
    "section": "## Genmedia workflow",
    "line": 37,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L37"
  },
  "classification": "R",
  "purpose": "genmedia 提交/轮询/下载",
  "inputs": "prompt、endpoint、文件",
  "outputs": "任务结果路径",
  "decision_owner": "外部 genmedia",
  "runtime_behavior": "直接执行 fal CLI 并按 downloaded_files 返回",
  "provider_specific": true,
  "target_modality": "both",
  "produces_prompt_text": false,
  "dependencies": [
    "skills/genmedia/SKILL.md"
  ],
  "validation_evidence": {
    "classification": "REFERENCE_ONLY",
    "confidence": "HIGH",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "不能替代 MCP、Host、预算和正式 Media。"
}
```

### C25 — 安装和 smart routing

来源：[skills/genmedia/SKILL.md § ## Critical rules](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/genmedia/SKILL.md#L19)。

```json
{
  "capability_id": "C25",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/genmedia/SKILL.md",
    "section": "## Critical rules",
    "line": 19,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/genmedia/SKILL.md#L19"
  },
  "classification": "R",
  "purpose": "安装和 smart routing",
  "inputs": "用户生成请求",
  "outputs": "自动 endpoint/技能安装",
  "decision_owner": "外部 genmedia",
  "runtime_behavior": "默认自动分类路由；init 安装 bundle",
  "provider_specific": true,
  "target_modality": "both",
  "produces_prompt_text": false,
  "dependencies": [],
  "validation_evidence": {
    "classification": "REFERENCE_ONLY",
    "confidence": "HIGH",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "只读发现；本轮无安装。"
}
```

### C26 — 顺序镜头与批准 still→video

来源：[skills/storytelling/references/workflows.md § ## Character narrative](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/storytelling/references/workflows.md#L35)。

```json
{
  "capability_id": "C26",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/storytelling/references/workflows.md",
    "section": "## Character narrative",
    "line": 35,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/storytelling/references/workflows.md#L35"
  },
  "classification": "W",
  "purpose": "顺序镜头与批准 still→video",
  "inputs": "anchor 与镜头表",
  "outputs": "I2V sequence",
  "decision_owner": "外部 storytelling",
  "runtime_behavior": "从批准静帧开始；按镜头检查",
  "provider_specific": true,
  "target_modality": "video",
  "produces_prompt_text": true,
  "dependencies": [
    "skills/character-design/SKILL.md"
  ],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "FUTURE_VIDEO_ROUND，不把 still-first 升成普遍 pipeline。"
}
```

### C27 — 单镜头/多 prompt 能力边界

来源：[skills/cinematography/SKILL.md § - Video prompt describes](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L140)。

```json
{
  "capability_id": "C27",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/SKILL.md",
    "section": "- Video prompt describes",
    "line": 140,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L140"
  },
  "classification": "Q",
  "purpose": "单镜头/多 prompt 能力边界",
  "inputs": "视频 prompt/schema",
  "outputs": "one-shot 或多镜头准入",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "按模型是否支持 multi-prompt 判定",
  "provider_specific": true,
  "target_modality": "video",
  "produces_prompt_text": false,
  "dependencies": [
    "model-routing"
  ],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "FUTURE_VIDEO_ROUND；provider 能力不能决定 canonical coverage。"
}
```

### C28 — 写实：材质接触与透视

来源：[skills/fal-prompting/references/gpt-image-2.md § **Edits, three-sentence pattern](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L100)。

```json
{
  "capability_id": "C28",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-prompting/references/gpt-image-2.md",
    "section": "**Edits, three-sentence pattern",
    "line": 100,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L100"
  },
  "classification": "K",
  "purpose": "写实：材质接触与透视",
  "inputs": "画面物体、光线、接触、视角",
  "outputs": "realism criteria",
  "decision_owner": "外部 fal-prompting",
  "runtime_behavior": "指定接触阴影、光线匹配、透视一致",
  "provider_specific": false,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "criteria 拆分到原 owners，不写新的通用造物 prompt。"
}
```

### C29 — 固定六段写实 Prompt 顺序

来源：[skills/fal-recipes/references/realism.md § ## Prompt build order](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L72)。

```json
{
  "capability_id": "C29",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-recipes/references/realism.md",
    "section": "## Prompt build order",
    "line": 72,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L72"
  },
  "classification": "W",
  "purpose": "固定六段写实 Prompt 顺序",
  "inputs": "写实 brief",
  "outputs": "不允许重排的最终 prompt",
  "decision_owner": "外部 realism recipe",
  "runtime_behavior": "强制 subject/action/setting/light/camera/imperfections 顺序",
  "provider_specific": false,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": ""
}
```

### C30 — 摄影 genre 与 capture era 分离

来源：[skills/fal-recipes/references/realism.md § ## Two orthogonal axes](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L83)。

```json
{
  "capability_id": "C30",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-recipes/references/realism.md",
    "section": "## Two orthogonal axes",
    "line": 83,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L83"
  },
  "classification": "K",
  "purpose": "摄影 genre 与 capture era 分离",
  "inputs": "风格目标",
  "outputs": "genre/capture-look 两轴",
  "decision_owner": "外部 realism recipe",
  "runtime_behavior": "分别选择拍摄类别与成像年代",
  "provider_specific": false,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "捕获风格不等于故事年代；不能自动引入现代物件或相机时代默认值。"
}
```

### C31 — 强制瑕疵与皮肤/眼睛特征

来源：[skills/fal-recipes/references/realism.md § ## Anti-AI-look checklist](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L234)。

```json
{
  "capability_id": "C31",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-recipes/references/realism.md",
    "section": "## Anti-AI-look checklist",
    "line": 234,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L234"
  },
  "classification": "K",
  "purpose": "强制瑕疵与皮肤/眼睛特征",
  "inputs": "被认为不真实的画面",
  "outputs": "pores/redness/dust/grain 等修复",
  "decision_owner": "外部 realism recipe",
  "runtime_behavior": "指定具体瑕疵并默认作为真实条件",
  "provider_specific": false,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "只能由资产/style owner 决定适用特征；不会自动加红眼/灰尘/疤痕。"
}
```

### C32 — 反居中/对称/正视/静止准则

来源：[skills/fal-recipes/references/realism.md § ## Anti-AI-look checklist](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L234)。

```json
{
  "capability_id": "C32",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-recipes/references/realism.md",
    "section": "## Anti-AI-look checklist",
    "line": 234,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L234"
  },
  "classification": "Q",
  "purpose": "反居中/对称/正视/静止准则",
  "inputs": "写实照片",
  "outputs": "偏心、非对称、离轴视线、动作",
  "decision_owner": "外部 realism recipe",
  "runtime_behavior": "将这些特征视为 realism 检查",
  "provider_specific": false,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "candid 子任务可作为 reference；不是 cinema 全局 gate。"
}
```

### C33 — 单主光与补光禁令

来源：[skills/fal-recipes/references/realism.md § ### Documentary / photojournalism](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L118)。

```json
{
  "capability_id": "C33",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-recipes/references/realism.md",
    "section": "### Documentary / photojournalism",
    "line": 118,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L118"
  },
  "classification": "K",
  "purpose": "单主光与补光禁令",
  "inputs": "documentary photo 子类型",
  "outputs": "单主光/无 fill",
  "decision_owner": "外部 realism recipe",
  "runtime_behavior": "以类型限制灯光",
  "provider_specific": false,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "保留精确 documentary 子范围，不能覆盖电影动机补光。"
}
```

### C34 — 2–4 variants 和 seed 迭代

来源：[skills/fal-recipes/references/realism.md § ## Common parameters](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L325)。

```json
{
  "capability_id": "C34",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-recipes/references/realism.md",
    "section": "## Common parameters",
    "line": 325,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L325"
  },
  "classification": "W",
  "purpose": "2–4 variants 和 seed 迭代",
  "inputs": "不稳定写实结果",
  "outputs": "多次候选输出",
  "decision_owner": "外部 realism recipe",
  "runtime_behavior": "多变体选优、固定 seed",
  "provider_specific": true,
  "target_modality": "still",
  "produces_prompt_text": false,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "不证明 seed 可复现；n=1/逐次预约是当前平台合同。"
}
```

### C35 — 一次改一个变量

来源：[skills/fal-prompting/references/gpt-image-2.md § **6. One revision](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L44)。

```json
{
  "capability_id": "C35",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-prompting/references/gpt-image-2.md",
    "section": "**6. One revision",
    "line": 44,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L44"
  },
  "classification": "W",
  "purpose": "一次改一个变量",
  "inputs": "失败观察",
  "outputs": "小步 edit",
  "decision_owner": "外部 fal-prompting",
  "runtime_behavior": "单 revision 而非大范围重写",
  "provider_specific": true,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "作为诊断试验设计，不能禁止修复一次涉及多个相互依赖字段。"
}
```

### C36 — 光线/色彩/镜头联合 QC

来源：[skills/cinematography/SKILL.md § ## Quality bar](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L132)。

```json
{
  "capability_id": "C36",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/SKILL.md",
    "section": "## Quality bar",
    "line": 132,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/SKILL.md#L132"
  },
  "classification": "Q",
  "purpose": "光线/色彩/镜头联合 QC",
  "inputs": "渲染结果与 shot intention",
  "outputs": "物理/方向/色彩 findings",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "质量核对后返回",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": false,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": ""
}
```

### C37 — 排版与精确字面文字

来源：[skills/fal-prompting/references/gpt-image-2.md § ## Text-in-image patterns](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L81)。

```json
{
  "capability_id": "C37",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-prompting/references/gpt-image-2.md",
    "section": "## Text-in-image patterns",
    "line": 81,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L81"
  },
  "classification": "P",
  "purpose": "排版与精确字面文字",
  "inputs": "海报/UI/sign copy",
  "outputs": "typographic instructions",
  "decision_owner": "外部 fal-prompting",
  "runtime_behavior": "精确文本和位置/字体",
  "provider_specific": true,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "第一轮 focus 是电影摄影与写实；不能改已批准对白/历史文字。"
}
```

### C38 — 示例提示词集合

来源：[skills/cinematography/references/examples.md § ## Noir close-up](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/examples.md#L6)。

```json
{
  "capability_id": "C38",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/cinematography/references/examples.md",
    "section": "## Noir close-up",
    "line": 6,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/cinematography/references/examples.md#L6"
  },
  "classification": "K",
  "purpose": "示例提示词集合",
  "inputs": "五类题材",
  "outputs": "方向 pattern 示例",
  "decision_owner": "外部 cinematography",
  "runtime_behavior": "示例按题材替换",
  "provider_specific": false,
  "target_modality": "both",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "示例没有输出/seed/review；不直接复制 prompt。"
}
```

### C39 — 自动 phone/mirrorless 年代默认

来源：[skills/fal-recipes/references/realism.md § If the brief does not name an era](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L232)。

```json
{
  "capability_id": "C39",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-recipes/references/realism.md",
    "section": "If the brief does not name an era",
    "line": 232,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L232"
  },
  "classification": "K",
  "purpose": "自动 phone/mirrorless 年代默认",
  "inputs": "缺少 capture-era 的 brief",
  "outputs": "2024 phone/mirrorless 默认",
  "decision_owner": "外部 realism recipe",
  "runtime_behavior": "缺失信息时填入摄影风格",
  "provider_specific": false,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "摄影时代不应从故事年代推断；缺失由 style owner 决定。"
}
```

### C40 — 命名人物与参考照片 fallback

来源：[skills/fal-recipes/references/realism.md § If a result still fails realism](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L323)。

```json
{
  "capability_id": "C40",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-recipes/references/realism.md",
    "section": "If a result still fails realism",
    "line": 323,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-recipes/references/realism.md#L323"
  },
  "classification": "W",
  "purpose": "命名人物与参考照片 fallback",
  "inputs": "写实失败",
  "outputs": "切换真实参考图 edit",
  "decision_owner": "外部 realism recipe",
  "runtime_behavior": "失败后换 reference/edit route",
  "provider_specific": true,
  "target_modality": "still",
  "produces_prompt_text": false,
  "dependencies": [],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "只能请求合规已批准参考和 qualified route；不能找陌生照片替代锁定角色。"
}
```

### C41 — 否定约束与 positive-target 序列化

来源：[skills/fal-prompting/references/gpt-image-2.md § ## Prompt structure](https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L18)。

```json
{
  "capability_id": "C41",
  "source": {
    "repository": "https://github.com/fal-ai-community/skills",
    "commit": "9ca850412943251fc9a466c4c29fdaf7a303a3d8",
    "file": "skills/fal-prompting/references/gpt-image-2.md",
    "section": "## Prompt structure",
    "line": 18,
    "url": "https://github.com/fal-ai-community/skills/blob/9ca850412943251fc9a466c4c29fdaf7a303a3d8/skills/fal-prompting/references/gpt-image-2.md#L18"
  },
  "classification": "P",
  "purpose": "否定约束与 positive-target 序列化",
  "inputs": "明确排除项与保留事项",
  "outputs": "constraints 文本或 schema 支持的 negative 字段",
  "decision_owner": "外部 fal-prompting / character-design",
  "runtime_behavior": "外部模板使用否定句；专用 negative 参数只在模型支持时使用",
  "provider_specific": true,
  "target_modality": "still",
  "produces_prompt_text": true,
  "dependencies": [
    "skills/character-design/SKILL.md:93-95"
  ],
  "validation_evidence": {
    "classification": "EXTERNAL_CANDIDATE",
    "confidence": "MEDIUM",
    "evidence": "冻结源码的规则/示例；未找到该能力实产配对结果或控制实验",
    "limitations": "不能由仓库名、PR 合并、示例或离线测试推断影像效果"
  },
  "notes": "本地保留原 constraint 但输出显式作者提供的 positive_target；edit correction 不被正向化。没有证据证明否定或正向措辞普遍更好。"
}
```

## 实际缺口与未发现的能力

外部没有 source-pin/source-map、强身份哈希、摄影实产验收集、可重复 physical simulator。身体接触真实性只有语言提示，不具备力学/手部几何约束求解。没有独立 camera-height 数值推导、光比计算、曝光校准或稳定 identity embedding 算法。不能为填满能力表而把这些能力归给它。

外部的 composing/blocking 是描述画面关系，不等于本地 Blocking/Action 的授权与持续状态。所谓 film texture 是成像意图，不是改变已批准历史环境、伤痕或人种外观的理由。将语义拆成 camera、lighting、color、surface、state、criteria，比复用原始 prompt 模板更有价值。
