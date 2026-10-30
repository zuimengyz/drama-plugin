# Film World & Visual Identity Inheritance 最小实施交付

2026-10-29，工作区实现，未发布或重载桌面插件。基于 HEAD `b56043963806ce468d62fb3676503135f6de9a3d`。没有修改当前Grok配置或调用付费作者。

## 已实现的结果

选定的世界、美学、文学理解和场景状态原稿现在可以经既有入口进入全片Director、单场Director、Shot与专业作者，并进入原件依赖和恢复依据。不是仅在Director报告里加一段背景介绍。

此次确认并修复的具体丢失是：原有结构化Film Look虽能进入部分专业/coverage上下文，`film_packet`/`scene_packet`却只带编剧与导演叙事，未把已选Film Look送入导演原稿创作；导演原件依据只含编剧hash和全片导演指纹，不能识别世界/美学基准变化。场级handoff、Shot子输入与专业缓存也缺少一致的片级原稿依据。

复用了ContextOriginal、ScreenplayWorkshop、SourcePin、Host原稿选择与现有作者任务。新增的`filmIdentity`只是**选定原件快照**：正文仍是可读文本，不新增世界观数据库、顶层阶段、艺术评分器或生产Gate。既有WorkDirectingAuthority仍可作为结构化Film Look使用；新选择只能选一套基准，不能同时注入多版或同时选择相互竞争的结构化/正文Film Look。历史已绑定输入保持可读。

## 原件与职责

|内容|负责者与边界|本次表达|
|---|---|---|
|文学理解|Literary Source Analysis提供事实与解释，导演不把解释变成原著事实|选定可读analysis原件；保留status与authorityRef。未自动扫描正式分析库或历史意见|
|Film World|Director结合原著/编剧与美术研究提出世界选择|Markdown说明年代范围、地域候选、生活/空间、季节与时间跨度、未知问题；不是强制字段表单|
|Film Look|Director主导，专业方法协助|观看、色彩/明暗、材质、时间/声音及场间发展；允许非写实，不默认低彩|
|场景状态|Director在已选世界中明确此场发生条件与有意例外|短场景头＋连续叙事；场级例外不重置其他场面|
|专业设计|Camera/Lighting/Color/World等各自落实；Production Design做一致性对齐|现有专业facts和Shot字段，不复制一套世界/美学结构|

新创作可先用`screenplay.retain_context`保留这些Markdown正文，通常是AUTHOR_CONCEPT；已有事实或研究依据保留原有status及authorityRef。选定不是正式采纳。若尚未选定基准，现有film_treatment任务会要求Director在候选稿中建立可读世界与美学，并明确未知，不以缺少新字段阻断旧工作。

沿原有`screenplay.bind_professional_context`增加可选参数：`world_ref`、`look_ref`、`analysis_ref`、`scene_state_refs`、`reason`。原`design_refs`不变。每次新基准选择是完整快照，更新场状态时重带希望保留的world/look refs；没有默默合并历史版本。无需新增同义Skill或绑定工具。

## 实际调用链

```text
既有编剧选择（正文不变）
  → retain_context：世界/美学/分析/场状态可读原件
  → bind_professional_context：明确选择、SourcePin、理由、formalAdoption=false
  → native_director_narrative
      film_treatment：编剧 + 原著 + 选定世界/美学/分析 + 场状态
      scene_treatment：选定全片导演 + 当前编剧 + 当前场状态 + 邻场关系
  → direct_film / Direction.author：选定片场导演 + 当前世界/美学
  → 原有Film子Shot handoff / Canon+Shot专业作者
  → World/Camera/Lighting/Color/Sound现有执行事实
  → 已有ExecutionProjection / PromptIR（当前需要的叶值）
```

原有`sceneDirection`仍表示有序镜头覆盖，未改名冒充单场导演剧本。全片作者可读全部明确选择的场状态；当前场/专业视图只带当前场状态与对应导演正文。编剧会话的身份不因视觉原稿变化而被重建；既有编剧原件和Canon不被覆盖。

world/look或场状态选择变化会改变新的导演输入依据；旧导演正文不能默默解释成基于新世界创作。Host可以明确重选原文，不必强制再次创作。已经冻结的Shot恢复仍走既有恢复路径，不因新层存在而补写。专业缓存增加此选定依据，专业原件使用既有`continuityDesignRefs`留住精确快照；当前版本变化只在原有新创作/显式继续路径生效。

最终Prompt不接收整个世界/美学或Knowledge。专业作者要把它们发展成当前的机位、空间、光源、材质色彩和声画事实，现有投影继续只消费这些事实。没有修改Runtime、Provider、生产调度、ExecutionProjection或PromptIR契约。

## 《药》真实Host隔离应用

材料使用前轮原著全文、相同《出门》编剧与Grok原稿分析；Grok正文和原始SSE均保持与API收据一致，编剧SHA256仍为`1984bb611e13fd79bc33347bb2ac48aa70cc3089f49a3a53a77f52f2e8ff28aa`。见[完整性证据](/tmp/film-world-look-20261029/11-original-integrity.json)。

当前Host独立创作了[Film World](/tmp/film-world-look-20261029/01-world.md)、[Film Look](/tmp/film-world-look-20261029/02-look.md)、[全片方向候选](/tmp/film-world-look-20261029/03-film-treatment.md)和[三场导演正文](/tmp/film-world-look-20261029/04-scenes.md)。这些不是Grok修订版，未被用户正式批准。原著“大清”是文本依据；清末、无名江南城镇与西窗布局是明确的改编/美术候选；1919署期没有进入故事年份。新的西窗不同于Grok的南窗，不能把它算作Grok自己解决了空间问题。

场景头示例：

> N｜内景，华家茶馆兼住宅。清末语境，年份未定，无名江南城镇候选。秋季后半夜、黎明前。北侧里间有病人；继承低彩材料与灰冷空间层次。西窗微弱夜空底光，铺东油灯，稍后点亮灯笼；本场内不发生日出。

|验证场|时间与地点|共同美学与实际差异|验证程度|
|---|---|---|---|
|N｜出门|秋季后半夜；临街茶馆兼住宅|微弱窗光＋铺东油灯；手与母亲眼线共处，经营桌沿仍可辨|导演→室内Shot→五个专业Owner→PromptIR|
|D｜茶馆公共生活|同一秋日，天亮之后；同一屋子与窗门|日间可见度提高，油灯退出主光；低彩材料、肤色关系保留；不让西窗射入东方日出|实际场级作者输入及选定正文；未完成群像覆盖|
|Q｜墓地|次年清明冷晨；明确是城外坟场|天空漫射、土草/布料层次、红白花仍可辨；不继承茶馆油灯|导演→外景Shot→五个专业Owner→PromptIR|
|Q-X｜艺术例外|独立版本，仍为清明冷晨|允许偏紫非自然主义暗部，保持肤色与坟路；不倒灌N/D|单独选择与场级语义视图已通过；未追加专业/影像执行|

本次全片方向只是局部实验的假设，不声称完整电影已经成立。N与Q各9秒只取交钱和跨路局部，不是强制时长规则；D与Q编剧输入是原著相应片段，未新造正式全片剧本。

真实经过8次现有Host作者请求/绑定/恢复：全片1次、场级3次、Shot2次、专业2次。[请求、指令、指纹、绑定原件记录](/tmp/film-world-look-20261029/06-host-call-and-binding-records.json)可逐项核查。正文由当前Codex Host创作；脚本只交接这些Host文本，不是MockTransport、ReplayClient或外部模型创作。

两个专业请求实际包含选定正文，并通过`craft_reading`载入已选《游戏规则》《公民凯恩》及灯位方法。它们帮助安排共同空间、注意和源位，不负责决定年代地域。[Production Design对齐记录](/tmp/film-world-look-20261029/09-production-design-alignment.md)由Host审阅不同专业原稿后写作，没有将监督职责变成另一个美术作者。

实际落实示例：N的Camera把观察点放在前屋东南，Lighting沿同一世界把油灯放在人物东侧、西窗提供微弱暗部底光，Color保留真实肤色与有限暖冷差；Q的Camera保留跨路距离，Lighting使用东侧较亮天空的宽漫射、土草反射承接暗部，Color保留低彩土草与红白花。这些句子确实进入[N执行事实](/tmp/film-world-look-20261029/N-execution-facts.txt)和[Q执行事实](/tmp/film-world-look-20261029/Q-execution-facts.txt)，不只是出现在说明中。

存储边界：所有ScreenplayWorkshop原件/索引/选择使用内存IO替身；没有创建登记Work/Run、数据库、MinIO或正式ProductionPackage。真实ExecutionProjection执行其native unit分支，reader/package selection使用内存替身；schema所需production-package引用是**未登记的合成引用**，不是生产权限。结果只落在临时实验目录。该部分证明执行叶值继承，未验证完整生产准入或Provider编译。

## 修改文件

创作代码：

- [film_identity.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/film_identity.py)：新增薄选择/验证/阅读模块，复用ContextOriginal和SourcePin，非世界字段模型。
- [screenplay.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/screenplay.py)：既有绑定入口的可选原件参数、版本选择、专业上下文解析。
- [direction_narrative.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/direction_narrative.py)：片场原稿输入、基准指纹与原件来源依赖。
- [backends.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/backends.py)：仅创作任务指令；世界/美学说明、场景头及专业落实义务。HTTP/Provider实现未改。
- [author_projection.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/author_projection.py)：选定正文语义视图、当前场过滤。
- [screenplay_author.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/screenplay_author.py)：视觉基准不重建编剧；已选场面之后继承。
- [film/capability.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/film/capability.py)：只补现有子Shot创作上下文的精确引用传递，不改生产调度。
- [professional_design/resolver.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/professional_design/resolver.py)：专业原件依赖与缓存指纹保留选定基准。

Skills：Director、Literary Source Analysis、Shot Design、Cinematography、Lighting Design、Color Design、Production Design、Sound Design的既有SKILL.md增加短衔接；Director现有`narrative-handoff.md`和`work-aesthetic-design.md`更新。新增一个共享参考[world-visual-inheritance.md](/Users/zy/historical-plugin/drama-plugin/plugin/skills/director/references/world-visual-inheritance.md)，没有新增Skill、Knowledge目录或重复案例。

测试：[test_film_identity_inheritance.py](/Users/zy/historical-plugin/drama-plugin/plugin/tests/test_film_identity_inheritance.py)新增8项；[test_host_author_closeout.py](/Users/zy/historical-plugin/drama-plugin/plugin/tests/test_host_author_closeout.py)增加带基准的默认Host全链参数；[test_professional_design_refresh.py](/Users/zy/historical-plugin/drama-plugin/plugin/tests/test_professional_design_refresh.py)增加Film Identity替换/移除两项，经过既有专业原稿、native package、compiler和最终离线wire。测试全部使用通用一次性fixture，不为《药》注册作品。

## 回归结果与未完成证明

- 本轮相关回归完整运行：**130通过、8失败**。8项均用HEAD基线源码隔离复现，不是本次新增失败；未掩盖为全绿，也未顺带修复。
- 其中1项是既有`test_changed_selected_design_reauthors_finite_facts_and_changes_final_wire[scene-replace-True]`：旧依赖更新后的Direction进入另一作者任务，现有fixture按Shot请求取字段而失败。见[基线复现](/tmp/film-world-look-20261029/baseline-refresh.txt)。
- 另7项是既有`test_formal_wire_reads_scoped_current_method_files`：临时Skill目录缺少早已加载的共享资料，报`FORMAL_AUTHOR_SKILL_ABSENT`。见[基线复现](/tmp/film-world-look-20261029/baseline-craft.txt)。
- 明确排除上述已复现基线问题后，最终相关回归 **130 passed, 8 deselected**；不是将排除项声称通过。[最终日志](/tmp/film-world-look-20261029/final-targeted-regression.txt)、[包含失败的完整日志](/tmp/film-world-look-20261029/regression.txt)。
- 新增11个验证分支全部通过：原件篡改/跨作品拒绝、版本替换与未选历史排除、结构化Film Look进入treatment、当前场隔离、艺术例外、默认Host链、最终执行文本更新。冻结恢复、旧输入、编剧保真沿原有测试继续通过。
- 两项历史注册/Markdown引用测试通过；8个修改Skill的quick_validate通过；`git diff --check`通过。

已证明的是原件选择和文本创作继承、具体专业设计及离线执行事实。没有以测试分数宣称电影艺术达标。尚未证明机位的真实画格构图、光照质感、演员动作、跨镜时间体验、Animatic、Seedream/Seedance、完整影片一致性或桌面已加载版本。

没有更改Runtime、Provider、生产调度、T1–T5契约、Grok配置；没有读V5冻结资产、改V6、付费生成、commit/push、发布或重载。当前工作区改动保留待Host审查，本轮到此停止。
