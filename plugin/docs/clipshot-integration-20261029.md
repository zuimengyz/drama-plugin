# ClipShot 分镜专业能力吸收与离线验证

2026-10-29。工作区基线 `e4c1f7a`；增量修改在工作区验证，未发布插件缓存。结论：已把表现性分镜方法接入既有 Knowledge、五个专业 Skill 和分镜说明；当前 Host 用《药》已有导演段落实际读取、选择、画图和修正。验证了设计与附件契约，没有验证演员运动、光照成像或 Seedance 动态执行。

## 1. 来源、完整阅读与取舍

上游：[TanShilongMario/clipshot @ 095ab36e8184ce8b182711ebc8c63cf682e70942](https://github.com/TanShilongMario/clipshot/tree/095ab36e8184ce8b182711ebc8c63cf682e70942)。完整阅读 `SKILL.md`、全部五份 `references/`、`examples/market-chase/` 的三份文本；没有安装上游 Skill 或执行其生产流程。

逐文件 SHA-256、长度与阅读边界保存在 [source-manifest.json](../knowledge/film-craft/sources/clipshot/source-manifest.json)。保留 [MIT全文](../knowledge/film-craft/sources/clipshot/LICENSE)及 `Copyright (c) 2026 TanShilongMario`，改写归属见 [NOTICE](../knowledge/film-craft/sources/clipshot/NOTICE.md)。

|上游材料|实际吸收|没有照搬的部分|
|---|---|---|
|SKILL.md|先拆观看与动作关系，再用图检查是否画出来；局部问题可局部修正|九宫格、固定媒介、强制流程、反复重绘及新审批|
|cinematic-language.md|近处尺度、切边、斜线、特殊视点、框内分区；区分Dutch、ROLL与TILT|比例神话和“某机位必然代表某情绪”的公式|
|action-cinematography.md|重心、支撑、接触、惯性、后果；摄影与身体的同步、迟随和反向关系|把动作阶段硬拆成固定镜头数，或把武打强度移植到日常生活|
|deliverable-schema.md|同镜a/b/c、唯一镜头计时、节点与切点分离|新的平行JSON契约、固定格数及每节点独立生成|
|keyframe-production.md|制作沟通图与成片视觉关键帧用途分开|强制线稿、强制追加关键帧审批；不改变现有KEY_FRAME/FIRST_FRAME权限|
|visual-production.md|摄影、人物、视线、光源分层标记；参考材料按实际用途使用|严格材质排除、全套重做至PASS、以图解代替电影艺术预览|
|market-chase三份文本|九格实际为七镜，S04a/b/c合计六秒、全段24秒；柱子横穿画面、身体压低与支撑、手刹接触、手推车位置形成具体连续性|不把节点称为“关键帧”就映射成正式资产；不移植追逐动作或角色。其定稿图未提交仓库，文本声称画面已达到的效果未获本轮图像证实|

因此保留的是专业方法，绝非另一套分镜工作流。原项目示例也不是真实电影拍摄事实或模型能力证据。

## 2. 与当前能力逐项对照

|既有能力与源码依据|本次补强|保持的职责与限制|
|---|---|---|
|[Director](../skills/director/SKILL.md)：已有观看意图、完整场面及案例读取|主动提出特殊位置、强构图、静止或复杂运动，先说明表达收益，再研究技术风险|Director／Host作艺术选择；不以模型风险提前筛掉作者方案|
|[Cinematography](../skills/cinematography/SKILL.md)：已有机位、光学、movement与阶段表达|把切边、前景尺度、失衡、反向移动转成可画的空间关系；节点覆盖整条摄影变化|摄影专业负责物理方案；图上节点不成为新剪辑|
|[Blocking](../skills/blocking/SKILL.md)：已有路线、眼线、遮挡、让路|补充中间支撑、共享空间和动作后留下的人|不为了摄影配方强迫人物新增动作|
|[Action](../skills/action-choreography/SKILL.md)：已有接触、负载和道具身份|用中间节点暴露“起势／完成”两图掩盖的动作机制|不新增强制动作阶段、镜头数量或力学评分|
|[Shot Design](../skills/shot-design/SKILL.md)：已有覆盖、关键帧、Sequence接入与薄组装|明确候选阶段主动协同提出有表现力的覆盖；a/b/c归属一个镜头及一次总时长|最终组装仍继承专业原稿，不夺取Camera或Editorial所有权|
|[Storyboard/Animatic说明](director-storyboard-animatic.md)、[附件适配器](../src/drama_plugin/hosts/storyboard_animatic.py)|显式区分“被请求的制作图研究”与“电影艺术预览”；图形层不自动进入成片|没有另建Storyboard Skill；适配器本来支持一镜多附件，本轮只加回归测试，没有改运行代码|
|[Knowledge读取器](../src/drama_plugin/creative_engine/craft_knowledge.py)|新增一份共享方法及索引；从现有专业入口可读全文和哈希|电影风格、电影案例保持原位置；ClipShot归专业方法来源，不伪装成电影案例|

T1–T5逐项核对：

|机制|现有责任|本次处理|
|---|---|---|
|[T1](runtime-engine-t1.md)|统一执行、引用、恢复与权限|没有增加调用阶段、循环或Runtime状态|
|[T2](production-package-t2.md)、[assembler](../src/drama_plugin/production/assembler.py)|从选定原件组装事实，不承担创作|分镜节点不新建ProductionPackage或技术生成单元|
|[T3](gate-governance-t3.md)|沿现有Gate分类处理真实事实、授权与错误|不把特殊机位、非线稿或不够九格变成生产阻断|
|[T4](professional-consolidation-t4.md)、[resolver](../src/drama_plugin/professional_design/resolver.py)|精确选择专业原件，保持owner边界|所选关系写回Camera／Action／Lighting／Sound／Editorial，不由图像文件偷改专业决定|
|[T5](prompt-audio-convergence-t5.md)、[compiler](../src/drama_plugin/generation/compiler.py)|选定专业事实进入已有Prompt表达与音画职责|执行关系可下传；案例名、画格号、箭头、九宫格或研究文字不堆进最终Prompt。本轮未对《药》构建正式包或编译提交|

这些机制的存在不证明电影表达达标。本次的增量在作者设计与制作图表达层，保留既有技术成果及其艺术能力边界。

## 3. 实际调用与创作证据

链路：已有导演意图 → 修改后的专业Skill指向共享方法 → 现有 `craftKnowledge` 选择 → `reading` / `author_reading` 加载正文及哈希 → 当前Host读后创作局部专业设计 → 制作图检查 → 既有附件适配器的独立契约验证。

不是新增自动研究调用。原有读取器不会追踪所有Markdown链接；需要选中方法时明确使用 `techniqueIds: ["expressive-storyboarding"]`，由已有作者上下文传入。这一点已写进 [film-practice](../skills/director/references/film-practice.md)，没有用“加了链接”冒充正文已加载。

本次表达问题是：**交钱之后，母亲仍在共同生活空间内，而不是被镜头追随钱袋的动作丢下。** 实际选择《玩乐时间》既有空间使用案例、新表现性分镜方法和既有灯位方法；三份完整正文与哈希见 [读取结果](/tmp/clipshot-medicine-study-20261029/01-reading.json)，现有作者上下文实际输出见 [author-context](/tmp/clipshot-medicine-study-20261029/01-author-context.txt)，选择和原件哈希见 [receipt](/tmp/clipshot-medicine-study-20261029/01-receipt.json)。

由当前Host读取后创作，未通过MockTransport或ReplayClient回放；没有外部作者模型调用。附属单元测试仍是合成接口测试，不能混称为真实艺术创作。

## 4. 《药》的具体设计变化与艺术判断

只读来源是已有[编剧原文](/tmp/medicine-host-20261029-live/01-screenplay/original.md)、[单场导演候选](/tmp/medicine-artistic-deepening-20261029/03-出门单场导演剧本候选.md)和[专业深化](/tmp/medicine-artistic-deepening-20261029/05-必要专业深化与Knowledge取舍.md)。没有改台词、剧情、原件或资产。

新的[局部分镜设计候选](/tmp/clipshot-medicine-study-20261029/02-分镜设计候选.md)及[制作图](/tmp/clipshot-medicine-study-20261029/03-production-board.png)均在临时目录。

|原有方案|本轮实际变化|观看收益与代价|
|---|---|---|
|约1.2米偏侧共同视野，茶桌在边缘|候选机位降至0.95米，桌沿从右侧切入；图上发现桌子只剩一尖后微调观看方向，未移动桌子救画面|手、身体和经营桌在同一观看关系中；低位可能使袋口更易遮挡，须排练，不宣称更低必然更好|
|完整交钱，母亲空手、父亲调整握法|Ma由母亲承重；Mb双方短暂托同一包钱；Mc母亲放手收回、父亲碰袋边并换握；图中只一包钱|关系由接触和释放呈现，无需增加忧虑特写或新冲突。图解仍不能呈现演员的细微心理|
|文字要求灯位连续|固定桌灯与西纸窗、人物及C共同画进平面图；手经过同一光区，不逐节点追光|世界位置可检查；图上色块不是曝光或真实光照模拟|
|没有为本局部确定节点映射|同镜M内Ma/Mb/Mc，局部估时9秒，附件显示4/4/1秒，总时长只计一次|检查中间状态而不拆成蒙太奇；显示停留不是演员必须停住的时长|

本次选择固定，保留一个从(1.0,0.4)向(0.65,0.4)侧移、由接住触发、以母亲空手获得间隙为目的的未选方案。固定的收益是同时保留交付与留下；运动可能更清楚揭露空手，却可能使视差盖过微小接触。后者未做动态预演，没有因模型风险被预先否决，也没有宣称路径已可执行。

图已实际查看，并对桌面可见面积、托底接触图的悬空缝隙做了局部修正。当前图能读出相同机位与灯位、钱的三种支撑状态、母亲空手及前景桌沿。它是简化人体与几何投影的制作图，不能当作自然表演、成片光影或完成的Cinematic Animatic。候选来自Host本轮创作，不表示用户已批准正式采用。

## 5. 离线验证结果与边界

实际调用原有 `storyboard_attachment_plan`，把三张制作节点图接入一个**独立的内存合成契约夹具**：结果 **1镜头行、3附件、9秒、0内部切点、0生成请求、automaticFirstFrame=false、productionAuthorized=false、adoption=UNCHANGED**。[结果JSON](/tmp/clipshot-medicine-study-20261029/04-attachment-verification.json)及[验证脚本](/tmp/clipshot-medicine-study-20261029/check_attachment_contract.py)。

现有Sequence schema要求CANON pin，故没有将《药》候选伪装成正式Canon来满足它。夹具使用明确标注的通用合成pin，仅测试附件分组；《药》的艺术文本和图像作为候选另存。没有保存正式Sequence/ProductionPackage、登记Work或创建生产身份。原编剧及两份导演／专业原件前后SHA-256相同。

回归命令（工作区 `.venv`，无网络／媒体生产）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=plugin/src .venv/bin/python -m pytest -q -p no:cacheprovider \
  plugin/tests/test_craft_knowledge_application.py -k 'not retained_application' \
  plugin/tests/test_storyboard_animatic.py plugin/tests/test_sequence_production.py \
  plugin/tests/test_skills.py plugin/tests/test_screenplay_incubation.py \
  plugin/tests/test_runtime_engine.py plugin/tests/test_production_package.py \
  plugin/tests/test_gate_governance.py plugin/tests/test_professional_consolidation.py \
  plugin/tests/test_prompt_audio_convergence.py
```

结果 **250通过、9失败、2排除**。排除的是历史V6案例回放，不作为本次《药》创作输入或证明。T3/T4/T5所选文件均通过。9项失败为：Skill逻辑工具文案检查；旧planning行数上限与概念检查；旧OpenAI适配器依赖要求；旧视觉Provider文案两项；T1一项及T2两项固定52工具数量断言（当前78）。

对这9项在独立pytest进程中把本轮已修改的受控文件读取内容恢复为HEAD文本再执行，**全部同样失败**；未回滚或修改工作区文件。见[基线复核日志](/tmp/clipshot-medicine-study-20261029/baseline-test-output.txt)、[读取覆盖清单](/tmp/clipshot-medicine-study-20261029/baseline-overlay.json)。这是只读文本基线复核，不冒充完整独立部署验证；没有顺带修复历史测试。

新增全文加载测试、多节点同镜测试及现有Skill链接测试单独重跑，**3通过**，[JUnit结果](/tmp/clipshot-medicine-study-20261029/focused.xml)。新增测试验证方法全文进入Director/Professional已有上下文，以及多节点不乘镜头数／时间／请求数；不评价艺术优劣。

已验证：知识正文可被读取；Host实际转化设计；图上关系可检查；同镜附件和时间归属正确。待验证：连续动作的自然性、共享承重的手指细节、衣袋摩擦、运动候选路径、真实光影与表演，以及Seedance保留这些条件的能力。未生成视频或声音，未测试《药》的最终Prompt编译，不宣称已证明动态摄影。

## 6. 修改文件与停止范围

- Knowledge：新增 `shared-techniques/expressive-storyboarding.md`；登记 `shared-techniques/index.json`；更新 `film-craft/README.md`；新增 `film-craft/sources/clipshot/{LICENSE,NOTICE.md,source-manifest.json}`。
- Skill：Director、Cinematography、Blocking、Action Choreography、Shot Design各一处职责内增补；更新Director既有 `references/film-practice.md`。
- 说明：更新 `docs/director-storyboard-animatic.md`，增加本报告。
- 测试：仅增补 `test_craft_knowledge_application.py` 和 `test_storyboard_animatic.py`，没有改旧断言。

没有新增Skill、Runtime状态、检索服务、Provider实现或生产调度。没有改V6、读取V5冻结创作资产、写MySQL/MinIO、付费生成、提交或推送。临时图文不进入作品索引。当前工作结束，不自动进入生产或后续整改。
