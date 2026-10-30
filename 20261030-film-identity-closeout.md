# Film Identity 继承链收尾验证

2026-10-30。工作区增量验证，未发布或重载插件。承接[上一轮交付](/Users/zy/historical-plugin/drama-plugin/20261029-film-world-visual-identity.md)，不重新设计架构。下面的《药》均为隔离候选，选定者是当前 Codex Host，不表示用户批准正式影片。

## 结果

三个缺证部分均得到文本层面的实际调用证明：无预选World/Look的Director冷启动、同场三个机位共享依据、Q-X艺术例外进入Lighting/Color与离线执行表达。唯一产品代码补充是完整快照的可读变更回执，以及该回执在创作上下文中的隔离。没有新增创作阶段、Skill、数据库或生产Gate。

证明范围是当前Host逐步创作、现有作者入口接收和绑定、专业原稿与执行事实继承；不是独立模型创造力、影像连续性或完整生产验证。

## 一、真正冷启动

从前轮相同原著全文与《出门》编剧启动`native_director_narrative`，使用明确的本地HOST配置。初始handoff没有`filmIdentity`、`filmLook`或世界/美学原稿，完整[首次请求](/tmp/film-identity-closeout-20261030/cold-film-request.json)保留了真实输入。

当前Host读取请求后创作[冷启动导演候选](/tmp/film-identity-closeout-20261030/cold-film.md)。它主动提出共享经营/起居空间、日光增加而认识未必改善、低彩材料而保留肤色等观看选择。它同时区分：

- 原著依据：“大清”、两间茶馆屋子、秋季后半夜、清明西关外坟场。
- 本次改编候选：清末语境、无名江南城镇、秋事到次年清明的时间连接。
- 布景设计假设：南门、西窗、西铺、北里间、东茶桌及米制坐标；不是原著实测。
- 未定事项：精确年份与城市；1919署期不作故事年。

第一次候选返回后，在[待写单场请求](/tmp/film-identity-closeout-20261030/cold-pending-scene.json)处检查：导演候选正文已传到场级，但并没有自动生成选定Film Identity。此时停留于文本候选，不把其中的设定当作历史事实或正式世界权威。

然后由Host明确拆出并保留[World](/tmp/film-identity-closeout-20261030/world.md)、[Look](/tmp/film-identity-closeout-20261030/look.md)、来源区别和场状态，调用既有`retain_context`及`bind_professional_context`，再通过`bind_director_narrative`明确重选同一导演原文。没有自动抽取/自动批准世界设定。原稿仍保留首次候选措辞，选择状态由精确引用和Host理由表达，不事后篡改其创作历史。

[选定handoff](/tmp/film-identity-closeout-20261030/selection-handoff.json)保留`AUTHOR_CONCEPT`、`selectedBy=HOST`、`formalAdoption=false`。随后[单场N请求](/tmp/film-identity-closeout-20261030/selected-scene-N-request.json)实际读到选定World/Look、N状态与全片方向，并继续到Shot和专业作者。

结论：现有冷启动可以由Host提出并选择世界/美学，再继续导演与专业链；没有证明Grok等独立模型能稳定完成同等判断，也没有新增自动选择机制。全片方向只是局部实验假设。

## 二、同一华家茶馆的三个机位

三个机位取同一个交钱事件、同一昼夜窗口和人物初末状态，属于覆盖候选，不是人物反复交钱三次，也不是已经决定三个镜头全部串剪。

共同布局：西南为坐标原点，东+x、北+y。母亲在西铺(0.6,2.4)，父亲在(1.3,2.4)面西；油灯(1.8,2.8)、灯焰约0.7米；西纸窗(0,3)，北口(2,5)，南门(2,0)，东茶桌(3.6,2.5)。尺寸均属隔离设计候选。

|机位|具体观看选择|艺术收益与代价|照明继承|
|---|---|---|---|
|N-A|东南(2.8,0.8)，高1.2米，朝西北|手、母亲关注与铺边通路同处；不强求东桌入画|同一油灯在人物东侧偏北，母亲面东较易受光，父亲面西较暗|
|N-B|南侧(1.0,0.6)，高1.2米，朝北|侧向距离、交付后的空手更可见；减少部分场所信息|灯不移位，按新观看方向说明受光面，而非复制A屏幕亮边|
|N-C|东北(2.6,3.8)，高1.25米，朝西南|越过父亲近肩看母亲接收，更亲近；可能遮手且越轴|更靠近源方向看见母亲受光面；父亲暗脸不能凭空补成正面亮脸|

三份专业输入的World/Look/N状态完全一致；World正文、光源列表与Color正文相同，Camera与视点相关受光说明不同。[证据断言](/tmp/film-identity-closeout-20261030/check_evidence.py)核对实际返回原稿，并确认其机位、灯光、色彩和空间叶值进入实际离线投影。

可直接对照：[A专业原稿](/tmp/film-identity-closeout-20261030/N-A-professional-originals.json)、[B专业原稿](/tmp/film-identity-closeout-20261030/N-B-professional-originals.json)、[C专业原稿](/tmp/film-identity-closeout-20261030/N-C-professional-originals.json)，以及[A执行文本](/tmp/film-identity-closeout-20261030/N-A-execution.txt)、[B执行文本](/tmp/film-identity-closeout-20261030/N-B-execution.txt)、[C执行文本](/tmp/film-identity-closeout-20261030/N-C-execution.txt)。

Production Design由当前Host依据现有Skill进行实际对齐，读取上述原稿并保留[文件指纹](/tmp/film-identity-closeout-20261030/alignment-inputs.json)，见[对齐意见](/tmp/film-identity-closeout-20261030/production-design-alignment.md)。没有把监督意见伪装成独立模型或第二套美术原件。

对齐中实际发现并修正两处创作不一致：A初稿强称可见东桌近缘，改为允许桌子在画外，未搬桌；D初稿朝向与东桌位置不符，改为同位置转向东北。修改前绑定记录保留在[修订前调用](/tmp/film-identity-closeout-20261030/pre-alignment-calls.json)，没有以接口通过掩盖设计错误。

## 三、昼夜变化不重置Film Look

D-A采用同一秋日天亮之后的明确场状态，已经跨过外出返家；不是N交钱过程中突然天亮。World和Look引用与N相同，建筑不动；营业事件使人物来到东桌，这与换机位无关。

灯光改为同一西窗的天空漫射及南门街面回光，油灯熄灭但留在原桌；不制造西窗射入东方晨阳。低彩木布及真实肤色继续，允许日间可见度和中间调增加。实际经过单场、Shot、专业作者与投影：[D-A专业输入](/tmp/film-identity-closeout-20261030/D-A-professional-input.json)、[日间执行文本](/tmp/film-identity-closeout-20261030/D-A-execution.txt)。本次仍不是完整茶馆群像覆盖。

## 四、Q-X例外实际传递

沿用前轮“环境暗部偏紫”的候选，明确为Q的独立实验版本，保留片级World/Look与N/D原件。由Host进一步发展为[单场导演正文](/tmp/film-identity-closeout-20261030/Q-X-direction.md)：紫限于环境阴影与低中间调，清明天空仍为共同漫射来源，肤色亮面和红白花保持；不造紫色场内灯，不把这种处理宣称为真实天气或显灵事实。

实际链条为：

```text
Q-X场状态的精确选择
→ 原有scene_treatment的Host请求与绑定
→ Q-X Shot（观看关系与局部紫暗面）
→ Lighting（同一天空源＋局部处理边界）
→ Color（明确哪些表面偏紫、哪些保留）
→ 原有ExecutionProjection → PromptIR事实
```

[专业原稿](/tmp/film-identity-closeout-20261030/Q-X-professional-originals.json)及[最终离线执行文本](/tmp/film-identity-closeout-20261030/Q-X-execution.txt)均包含这些具体条件。它们没有被自动否决为“不写实”，也没有只停在导演说明中。

隔离核对：在包含Q-X的同一片级快照下，重新构造N的真实作者投影，使用N自己的Canon/Shot；[当前场输入](/tmp/film-identity-closeout-20261030/scope-check.json)没有Q的紫色正文。N/D执行文本亦无紫色处理。例外只替换Q状态，World、Look、N和D状态的指纹均保留。

艺术上，这种陌生化有可能被误读为显灵提示；文本传递成功不证明艺术效果成立，须观看预演或实际输出后判断。

## 五、最小代码补充与可见回执

完整快照此前虽然会移除遗漏引用，但没有直接可读的保留/替换/取消清单。本轮增加`filmIdentityChanges`，只记录精确before/after pins与ADDED、RETAINED、REPLACED、REMOVED。没有合并历史版本，也没有自动恢复被取消的引用。

既有绑定工具可选传`include_selection_changes=true`，直接返回：

```text
{ handoffRef: 后续继续使用的原SourcePin,
  filmIdentityChanges: 完整快照变更清单 }
```

默认不传时仍返回原SourcePin，保持旧调用兼容。无新Film Identity更新时不显示上一次陈旧回执。取消所有实验基准可显式用空场状态快照；仅重绑专业design_refs则不暗中取消已有世界。

通过[既有注册工具实调](/tmp/film-identity-closeout-20261030/check_tool_receipt.py)验证：保留World、遗漏Look时显示REMOVED；替换Look显示REPLACED；Host恢复时精确返回原Look pin。[回执证据](/tmp/film-identity-closeout-20261030/snapshot-update-receipts.json)。这使遗漏可辨认，但不是自动审批或自动防错，Host仍需阅读回执并明确恢复误删项。

回执不进入作者语义视图，也不改变编剧会话身份；因此被取消的旧Look不会作为“变更历史”重新注入下游创作。

本轮相对上一轮的实际代码增量：

- [film_identity.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/film_identity.py:15)：纯引用差异函数。
- [screenplay.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/screenplay.py:389)：验证旧快照、保存变化回执；既有注册工具增加可选返回方式，默认返回不变。
- [author_projection.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/author_projection.py:609)：剔除Host回执。
- [screenplay_author.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/screenplay_author.py:103)：回执不影响编剧会话身份。
- [既有Director参考说明](/Users/zy/historical-plugin/drama-plugin/plugin/skills/director/references/world-visual-inheritance.md)：说明回执与旧返回方式；没有新建Skill。
- [继承测试](/Users/zy/historical-plugin/drama-plugin/plugin/tests/test_film_identity_inheritance.py:119)：补充快照差异/历史排除、冷启动显式选择、注册工具旧返回兼容三个测试。

工作区还保留上轮未提交改动；它们不全是本轮新增。

## 六、调用真实性、回归与边界

[最终调用记录](/tmp/film-identity-closeout-20261030/calls.json)含15次Host作者请求/绑定：1次冷启动全片、3次基础单场、1次Q-X单场、5次Shot、5次专业请求。每次包含实际输入、指纹、任务、Host原件与非正式采纳状态。专业作者的每次请求返回多个Owner原稿，不伪称另有多个外部模型。实际指令载有FILM_CRAFT_READING，方法阅读来自《游戏规则》及机位—人物—光源联合布局；未新增Knowledge。

Host先读取待创作请求，再形成该阶段原稿。第一次专业绑定因自造附加字段被拒绝，保留于[第一次记录](/tmp/film-identity-closeout-20261030/first-attempt-calls.json)；随后将内容并入已有字段，未改契约。内存进程结束后及对齐修订后，用相同选定Host原稿重建隔离状态并验证，见[复核脚本](/tmp/film-identity-closeout-20261030/verify.py)。后续重建是接口复核，不冒称又一次独立创作；未使用MockTransport、ReplayClient或外部作者API。

- 本轮完整相关回归曾为**132通过、8失败**；失败名称与上一轮已复现的8项基线问题一致：scene-replace-True旧fixture一项，临时Skill目录缺共享资料七项。见[完整日志](/tmp/film-identity-closeout-20261030/regression.txt)，本轮未顺带整改。
- 最终补入注册工具回执测试后，相关回归分批完成，合计**133项通过**：见[主要回归](/tmp/film-identity-closeout-20261030/final-regression.txt)与[补回scene-replace兼容项](/tmp/film-identity-closeout-20261030/remaining-scene-regression.txt)。排除仅上述8项已知问题；排除项不算通过。
- 回执/默认Host/注册及Markdown引用专项**31项通过**：[日志](/tmp/film-identity-closeout-20261030/receipt-regression.txt)。新增三个测试均通过，旧任务、冻结恢复与编剧保真沿原相关测试验证。
- [实际产物检查](/tmp/film-identity-closeout-20261030/evidence-checks.json)全部通过；编剧SHA256保持`1984bb611e13fd79bc33347bb2ac48aa70cc3089f49a3a53a77f52f2e8ff28aa`。数量和字段检查仅证明交接，不代替艺术评价。

《药》使用内存原件存储与临时文件，只有合同要求的合成scope标签，没有注册正式Work/Run。离线投影使用现有ExecutionProjection，但PackageReader/选择输入是内存替身；未建立正式ProductionPackage、运行完整生产预检、调用Provider或生成Seedance请求。结果为PromptIR执行事实，不是已提交的视频提示词。

尚未验证：实际构图/遮挡、光源效果、跨镜动作匹配、越轴剪辑、肤色与环境色分离、AI对Q-X例外范围的执行、影像艺术效果，以及桌面部署版本。无MySQL/MinIO写入、归档、付费调用、V6修改、V5读取、Runtime/Provider修改、配置变更、commit/push或发布。本轮止于上述交付。
