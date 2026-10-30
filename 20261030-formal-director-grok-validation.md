# 正式 Director 作者补正与《药》真实验证

2026-10-30。工作区 HEAD `3019c89a6e97cb983a909aa7379e2d74e1b39d26` 加本轮未提交修改。

## 结论与未完成部分

正式作者补正已实施，真实 Grok 已经通过 `FormalDirectionAuthor` 自主完成 World、Look、全片方向和《出门》单场原稿；Host 阅读、选择并绑定了原文，编剧文本没有被覆盖。Canon、Professional 保持 HOST。

**本轮不能宣称完整导演生产闭环已验收。** 第三次真实调用的镜头覆盖被实验设置的 4,096 可见输出 Token 截断，后端明确拒绝了不完整结果。保留全部原始响应，只从其中四个已完整返回的对象里取第三镜做隔离专业实验，未补完第五镜、未将部分响应冒充完整 FilmDirection。

三次官方报告费用合计 **$0.558870**；预算保守记账 $0.564054，无未知费用请求。剩余计划额度不足以支持既定推理预留下的完整重试或茶馆实验，停止新增调用。C 未执行，不能以 Host 文字代替 Grok 跨场景证明。

艺术上，本轮证明了独立创作和准确继承，**未证明比旧 Grok／Host 方案更有电影创造力**。Grok 对色彩使用和结尾关系有清楚选择；地域、空间与具体摄影仍欠发展。完整覆盖、同场群像和实际影像都未验收。

## 1. 代码、配置和真实调用

| 文件（均在 `plugin/`） | 实际修改 |
|---|---|
| [src/drama_plugin/config/text_composition.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/config/text_composition.py) | Canon／Direction／Professional 独立作者来源；省略时沿用旧全局值；stream、超时与 reasoning 配置。max_tokens 注释明确不能通用地保证总推理费用。 |
| [src/drama_plugin/config/loader.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/config/loader.py) | 加载三个角色作者开关及 stream／timeout 环境变量。 |
| [src/drama_plugin/creative_engine/backends.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/backends.py) | 按角色决定 HOST／MODEL；现有兼容后端发送精确模型和推理参数；解析 SSE、返回模型与 usage；独立冷启动输出 world／look／text。 |
| [src/drama_plugin/creative_engine/text_wire.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/text_wire.py)（新增） | 已核实 Grok 模型的 reasoning 支持；不支持时明确失败；SSE 正文、结束标记、模型身份及 usage 解析。 |
| [src/drama_plugin/creative_engine/direction_narrative.py](/Users/zy/historical-plugin/drama-plugin/plugin/src/drama_plugin/creative_engine/direction_narrative.py) | 默认 helper 内冷启动、保留 MODEL 候选、Host 指纹选择、原文绑定到既有 Film Identity 与导演原件，再进入场级创作。 |
| [skills/director/references/world-visual-inheritance.md](/Users/zy/historical-plugin/drama-plugin/plugin/skills/director/references/world-visual-inheritance.md) | 补充实际角色路由、候选作者与选择者分离的说明。没有新增 Skill。 |
| [docs/host-first-creation.md](/Users/zy/historical-plugin/drama-plugin/plugin/docs/host-first-creation.md) | 说明独立角色配置、SSE、超时和选择机制。 |
| [tests/test_director_model_authorship.py](/Users/zy/historical-plugin/drama-plugin/plugin/tests/test_director_model_authorship.py)（新增） | 9 项离线路由／协议／冷启动选择／恢复测试，不作为真实创作证据。 |

实际路径：

```text
native_director_narrative
  → select_cold_model_film
  → FormalDirectionAuthor.film_treatment
  → TextCompositionBackend.complete / _complete
  → httpx.AsyncClient → https://api.x.ai/v1/chat/completions
  → 原样候选与响应证据
  → HostOriginalRequired（只选择候选指纹及理由）
  → bind_host_author_original
  → retain_context / bind_identity / retain_selection
  → FormalDirectionAuthor.scene_treatment
  → Host 选择单场原稿
  → FormalDirectionAuthor.direct_film（本次因输出截断而失败）
```

临时 `RecordingTransport` 仅转发真实 `httpx.AsyncHTTPTransport` 并保存无认证头的请求正文与响应，不实现替代 HTTP 作者。覆盖调用记录了运行时栈 `_complete → complete → direct_film`；A 的正式后端响应 SHA 与捕获 SSE 一致。没有 MockTransport／ReplayClient 参与这三次真实调用。测试中的 MockTransport 明确仅是离线契约测试。

[版本证据](/tmp/grok-formal-director-20261030/versions.json)、[有效实验配置](/tmp/grok-formal-director-20261030/configuration.json)、[正式后端响应对照](/tmp/grok-formal-director-20261030/A-formal-backend-evidence.json)、[实际调用脚本](/tmp/grok-formal-director-20261030/run.py)。

**配置与部署限制：** 正式环境文件仍是全局 HOST、Director 独立作者来源未设置。对工作区外环境文件的持久修改被自动审批拒绝，理由是启用付费作者的配置授权不足；没有绕过该拒绝。本轮按附件明确授权在隔离进程显式启用 Direction MODEL，继续读取原配置的 `grok-4.7`、`high`、官方地址和凭据。Canon／Professional 不切换。工作区、安装缓存和已初始化进程不一致，未发布或重载，不能称桌面正式默认已经启用 Grok。

## 2. A：无预选 World／Look 的真实冷启动

输入为《药》全文、原选《出门》编剧稿、用户艺术意图及现有 Knowledge。实际发出全文 4,647 字符，与来源文件相同；原编剧 SHA256 始终为 `1984bb611e13fd79bc33347bb2ac48aa70cc3089f49a3a53a77f52f2e8ff28aa`。请求没有旧 Host／Grok World、Look 或镜头答案。

真实输出，均未经 Host 润色：

- [Film World](/tmp/grok-formal-director-20261030/A-world.md)
- [Film Look](/tmp/grok-formal-director-20261030/A-look.md)
- [文学理解与全片导演方向](/tmp/grok-formal-director-20261030/A-text.md)
- [原始可见响应正文](/tmp/grok-formal-director-20261030/A/original-content.txt)、[原始 SSE](/tmp/grok-formal-director-20261030/A/raw-response.sse)

World 明确清末县城、店堂与里间共墙、秋夜至早晨及清明跳转、刑场街口与西关墓地关系；未把发表日期当故事年份。次年清明被说明为依据文本作出的时间解释。**不足是没有进一步提出地域改编选择或足够明确的建筑生活形制**；不把绍兴写成原著事实是正确的谨慎，但不能由此直接推论电影世界已经完备。

Look 没有接受近黑白作为既定答案。它提出“颜色只跟物件的使用走”：血被纸包、荷叶入火、馒头乌黑、红白花留在黄土上。它拒绝让红独立成为全片滤镜，也不让花给墓地整体上色。这是独立艺术选择，不是 Host 纠正后的文本。

全片方向连接父亲相信能把生命带回家与母亲等待显灵，以“答应不落”收束。它保留转述中的夏瑜、不补牢狱英雄戏、不解释放花者，小栓之死留到新坟确认。此处有可讨论的导演立场；但这些文学理解与旧实验已有明显连续性，不能宣称新接口自动创造了更深思想。

Host 选择了这组三原件作为**实验依据**，同时记录地域不足与未正式采纳状态。选择只包含指纹和理由，不包含可替换艺术正文的字段。[选择理由](/tmp/grok-formal-director-20261030/host-selection.json)、[真实绑定记录](/tmp/grok-formal-director-20261030/A-host-selection-binding.json)。选择原件中的 `actualAuthor: HOST` 指的是选择意见；候选与片级导演原稿的 `actualAuthor: MODEL` 不变。

## 3. B：真实单场与覆盖结果

[《出门》原始单场稿](/tmp/grok-formal-director-20261030/B-scene.md)、[单场选择](/tmp/grok-formal-director-20261030/B-host-selection.json)。

B 实际请求中的 World、Look、Film Treatment、Screenplay 均与选定文本逐字相同，见 [A→B 证据](/tmp/grok-formal-director-20261030/A-to-B-inheritance.json)。覆盖请求又精确带入片级和场级导演正文，见 [B→覆盖证据](/tmp/grok-formal-director-20261030/B-to-coverage-inheritance.json)。旧 `sceneDirection` 镜头上下文没有被改名冒充单场导演稿。

B 的有效电影表达包括：母亲看钱和手、父亲听里间，注意不是一个统一的中心；灯笼带走光，母亲留在暗铺；咳嗽阻住开口，孩子不以反应特写出现；街道不先铺上刑场声音。对白仍保留“唔”“你给我罢”和最后一句原停顿。

不足同样明确：场景头被三段重复的全片说明推后；铺面形制被继续搁置；“不……把这几步拍成出门”措辞不清；起始无天光却要求暗中手和袋口可读，需要明确第一可读画面是否就是火柴点燃时，不能仅靠文字声称已经成立。声音与停步的书写先后也需要排演消歧。

第三次请求原计划形成完整覆盖，但 `finish_reason=length`。**这是本次实验控制器将原配置的 65,536 输出上限收紧至 4,096 后出现的交付限制；不能把它伪装成完整导演结果，也不能简单归咎于 Grok 的艺术理解。**

[完整截断原文](/tmp/grok-formal-director-20261030/coverage/original-content.txt)、[后端失败记录](/tmp/grok-formal-director-20261030/coverage-error.json)。原始正文已完整写出前四个对象：开灯与短答 28 秒、交钱 24 秒、灯与门口等待 42 秒、让路出门 16 秒；第五镜街道写至表演说明中途，整体 JSON 未闭合。这些秒数仅为创作估时。

只读解析器保存完整对象的原始字符范围与哈希，未补括号、补第五镜或补任何艺术文字。[取证结果](/tmp/grok-formal-director-20261030/coverage-complete-prefix-objects.json)、[第三镜选择边界](/tmp/grok-formal-director-20261030/shot-selection.json)。选定第三镜经既有 `direction_projection` 绑定 Canon 对白，作为局部专业实验样本；**这不撤销整个覆盖请求的失败状态。**

## 4. Host 专业实现与离线执行表达

Host 阅读 Grok 原件及第三镜后，使用现有 Cinematography、Lighting、Blocking、Performance、Color、Sound、Editorial 方法创作。现有 Professional 作者接口发出 Host 请求，Host 绑定原稿，再经 `FormalProfessionalAuthor.design` 校验 10 域。原稿、调用请求、绑定与结果分别保存：

[专业请求](/tmp/grok-formal-director-20261030/professional-host-request.json) · [Host 专业原稿](/tmp/grok-formal-director-20261030/professional-host-original.json) · [绑定](/tmp/grok-formal-director-20261030/professional-host-binding.json) · [Owner 设计](/tmp/grok-formal-director-20261030/professional-owner-designs.json) · [验证](/tmp/grok-formal-director-20261030/professional-validation.json)。

| Grok 选择 | Host 的具体专业发展 | 艺术收益与待验证条件 |
|---|---|---|
| 固定画面同时留暗铺与门口 | 摄影机靠外间侧墙，与门口站位接近同深度；母亲在右近层，父亲左侧脸与门在左后层；中广视角，不跨门槛 | 观众同时承受被留在暗处与向里间听候的关系。必须排演验证视场、遮挡和嘴部尺度，不宣称已由三维或画面证实。 |
| 灯离开母亲 | 桌灯在铺与通道间；父亲提灯笼到门口后，桌灯照明撤除，不给母亲留下独立美光；门口依靠低位灯笼和弱墙面反射 | 关系由光的实际移动变化，非整体压暗。暗部与父亲嘴部的可读性仍须照明测试。 |
| 颜色跟使用走 | 油污茶渍不统一去色；青白中间调与局部暖灯焰共存；母亲处降低明度而非突然换成另一套蓝 | 保留 Grok 拒绝整片近黑白的选择；具体成像未验证，未冒充灯具色温测量。 |
| 咳嗽决定开口 | 父亲持续提灯承重；续咳时收住开口，咳停后说完整原句；母亲同时整理被角 | 克制有接收和行动变化。不是要求演员始终面无表情。 |
| 话后不切孩子 | 声源在门后；房间底声持续；保留整句与无回应后的接收，听完且未转身才结束 | 不用数字静音或反应特写代替等待；时长与自然表演必须用排演／连续声画判断。 |

这些局部空间与灯位是 **Host 专业候选**，不反写为 Grok World 原文或原著事实。专业初稿一个空 DPD 层被现有校验拒绝，Host 补入明确的续咳接收 tactic；原失败稿仍保留。没有因此改校验器或模型结果。

使用内存 PackageReader 替身和明确选出的当前 Owner 执行叶，实际经过 `ExecutionProjection._operation → SeedanceTargetAdapter → 现有 Seedance2 generator`。没有创建正式 ProductionPackage，也没有调用规划采纳、Runtime 或 Provider。

[最终离线 Prompt](/tmp/grok-formal-director-20261030/offline-seedance-prompt.txt)、[PromptIR](/tmp/grok-formal-director-20261030/professional-prompt-ir.json)、[逐项继承核对](/tmp/grok-formal-director-20261030/end-to-end-evidence.json)、[投影范围](/tmp/grok-formal-director-20261030/offline-projection-evidence.json)。

43 项选定执行事实进入文本，required 未覆盖为 0；机位、两处光源、色彩、表演细节、结束条件及原句逐字保留。整段 Film Look、案例正文和 Host 来源标签未进入 Prompt。这个计数只证明传递；不证明艺术效果。临时读取替身曾暴露指纹／字段层级不匹配，已在实验夹具中修正，未修改生产投影代码。

42 秒是一个电影镜头的估时，**不是已验证的单次 Seedance 时长**。未来需要按实际模型能力决定技术分段与连续性方案；镜头内的点灯、移动、门口等待状态不自动变成三个电影镜头或三次请求。本次连一次媒体请求也没有创建。

## 5. Knowledge 与艺术对照

实际加载了《游戏规则》《历劫佳人》案例，以及光源位置、表现性分镜（已集成 ClipShot／MIT 来源）全文和指纹，见 [输入与 Knowledge 记录](/tmp/grok-formal-director-20261030/input-provenance.json)。未重构 Knowledge。

Grok 输出有多主体注意、不把剪辑交给说话者、固定纵深内光和声音改变注意等方法；这些与输入资料相容，但不能据此证明某一具体句子必然由某案例导致。Host 专业则明确采用机位—人物—光源联合布局方法，把固定摄影中的不同状态作为同一镜头内的变化；未因为提供了《历劫佳人》就强加连续运动。

真实请求完成并停止新增调用后，才读取旧导演原稿作对照，未回填给 Grok。

| 判断维度 | 本轮与旧稿的实际差异 |
|---|---|
| 文学思想 | 本轮“答应不落”更集中，但旧 Grok 已写过乌鸦不服从请求，旧 Host 已写过理解的可能与重新退回熟悉秩序。没有证据证明本轮更深。 |
| 作者立场 | 不整片近黑白、颜色随物件使用是明确的独立选择，值得保留；旧 Host 也已反对选择性色彩和冷暖道德公式，不能虚构二者完全对立。 |
| 电影世界 | 本轮世界原件独立、来源与解释较清楚，继承技术有进步；地域与建筑仍保守。旧 Grok 六镜稿反而给出了更多具体布局，具体并不自动等于空间可靠。 |
| 开场关系 | 本轮强调光离开母亲、观众与孩子保持听觉关系；旧 Host／Grok 也已有相近方法。这是独立创作中的有效重现，不是本轮独创或明显超越。 |
| 摄影与场面创造 | 当前完整返回的镜头仍以固定和硬切为主，覆盖几乎依次对应动作段落。固定镜头本身不低级，第三镜可承载复杂关系；但没有看到比旧稿显著更有作者性的空间重组或注意组织。 |
| 可拍摄性 | 本轮 Host 专业发展让侧脸、暗铺、灯位和声音更具体；这部分功劳属于 Host 专业实现。Grok 尚未独立完成足够具体的局部布局，且完整覆盖交付失败。 |

对照来源：[旧 Grok 全片](/tmp/grok-director-20261029/01-film-recovery/original.md)、[旧 Grok 单场与六镜](/tmp/grok-director-20261029/02-scene-coverage/original.md)、[旧 Host 全片](/tmp/medicine-artistic-deepening-20261029/02-全片导演视听方向候选.md)、[旧 Host 单场](/tmp/medicine-artistic-deepening-20261029/03-出门单场导演剧本候选.md)。输入规模、任务格式和输出限额不同，本轮不是受控模型排名。

建议把 Grok 作为需要 Host 艺术选择的独立 Director 候选作者继续使用；目前不足以认定其稳定胜任无需专业补充的完整导演交付。后续若获授权，最值得检验的是未完成覆盖的简洁可执行交付，以及茶馆中权威形成、群体恢复笑谈和病人身体之间的关系；本轮不自动追加。

## 6. 用量、回归和边界

| 调用 | 输入 Token | 可见输出 | 推理 Token | 官方报告美元 | 结果 |
|---|---:|---:|---:|---:|---|
| A 冷启动 | 17,547 | 1,877 | 27,025 | 0.206778 | stop，三原件成功 |
| B 单场 | 16,460 | 1,395 | 14,341 | 0.125608 | stop，原文成功 |
| 覆盖 | 24,100 | 4,096 | 25,906 | 0.226484 | length，正式后端拒绝 |
| 合计 | **58,107** | **7,368** | **67,272** | **0.558870** | 3 次，无未知请求 |

全部请求与返回模型均为 `grok-4.7`，实际发送 `reasoning_effort=high`，无静默降级或作者回退。费用取 `cost_in_usd_ticks / 1e10`，并保留未扣缓存的保守估算。官方资料：[$2/M 输入、$0.50/M 缓存、$6/M 输出定价](https://docs.x.ai/developers/models/grok-4.7)、[推理参数](https://docs.x.ai/developers/model-capabilities/text/reasoning)、[长请求建议](https://docs.x.ai/developers/model-capabilities/text/best-practices)。全球端点、输入均低于 200k。

[费用账本](/tmp/grok-formal-director-20261030/cost-ledger.json)、[计费方法](/tmp/grok-formal-director-20261030/pricing-and-budget.md)、[C 停止理由](/tmp/grok-formal-director-20261030/C-not-executed.json)。每次预留 64,000 推理 Token 是基于历史 high 消耗的计划值，不是服务端硬上限；本次实际消费低于 $1。没有未知费用后盲目重试。

回归：**117 passed**，分两组 64+53；`git diff --check` 通过。[64 项日志](/tmp/grok-formal-director-20261030/regression-before-live.txt)、[53 项日志](/tmp/grok-formal-director-20261030/additional-regression.txt)。覆盖角色独立、Host 缺稿明确提示、冷候选复用而不重复调用、选定原文精确进入场级、编剧不变、旧选定稿恢复不重写，以及专业继承与电影文法。新代码测试使用离线替身，真实 API 证据另列，未混淆。

未验证：部署后的桌面调用；完整 FilmDirection 成功交付；茶馆跨场景创作；全片导演一致性；真实摄影几何、光照、演员表演、声画节奏；实际合法分段、参考资产、Seedance 执行及后期效果。没有创建正式 Work／Run，没有写 MySQL／MinIO、归档或制作包；未改 V6、未读取 V5 冻结资产；没有媒体 API、Runtime／Provider／调度改动、commit/push、发布或重载。
