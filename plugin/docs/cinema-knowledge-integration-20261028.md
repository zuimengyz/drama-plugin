# 电影风格 Knowledge 与专业应用交付

2026-10-28；在master工作区实施，未commit／push。本轮任务已从审计转为建设；V6正式剧本、导演、分镜、资产和生产记录未改写，V5未作输入。未改Runtime、Provider、调度或已验收的生成编译路径；未生成付费媒体。

**交付判断：已经接通“表达问题→案例正文读取→专业设计转化→现有执行字段→实际Prompt编译”的本地路径，并完成V6-01-04的离线应用。** 这不是电影艺术质量保证，也不是Seedance动态摄影已通过验证。当前助手确实阅读并应用了知识；作者接口回放证明正文送达和设计传递，不能证明独立模型未来必然作出好选择。

## 1. 目录与实际内容

复用唯一案例库 `knowledge/film-craft/cases`，没有复制第二套film-cases。原10个案例保持位置，扩充到16个。新增7种风格导航、8项共享专业方法、表达目标与专业手段交叉索引。风格不是互斥标签，导航只链接正文；没有为目录完整制造空案例。

| 本轮操作 | 案例与内容 |
|---|---|
| 新增6个正式案例 | 《公民凯恩》：报社低机位／纵深与调度；《历劫佳人》：边境开场的路线交会与知情；《人类之子》：车内摄影及离开主角的观察；《1917》：路径排练、设备交接与夜城光源；《让娜·迪尔曼》：固定观看、家务时间及省略；《巴里·林登》：餐桌窗光、赌桌烛光与可见性代价 |
| 实质扩充3个旧案 | 《东京物语》：低机位、听完说话与空间持续；《玩乐时间》：机场误认、多主体注意及固定替代；《花样年华》：遮挡、距离、光影与不确定灯位；补核摄影署名 |
| 其余7案保持正文、增加索引 | 《芬妮与亚历山大》《豹》《游戏规则》《雨月物语》《野草莓》《镜子》《相见恨晚》；既有来源核验日期保留，不冒充本轮重新观片 |

入口：[风格导航](../knowledge/cinema-styles/README.md)、[唯一案例索引](../knowledge/film-craft/index.json)、[共享技法索引](../knowledge/shared-techniques/index.json)。风格包含古典叙事、观察现实主义、诗性、表现主义、黑色／悬疑、史诗／冒险、实验；它们是讨论倾向，不是给导演贴唯一标签。

11种表达目标覆盖等待、疏离、亲密、压迫、误认、揭示、共处、时间、倾听、记忆、沉浸。15种专业手段标签可交叉查找。尚无经本轮核验的“焦点转移”“负补光”专门电影案例，不能为了结果非空虚构案例；这些方法已在共享条目中提供，可直接用techniqueIds读取。

## 2. 知识覆盖与证据质量

| 方法正文 | 可用于设计的内容 | 核心来源／边界 |
|---|---|---|
| [机位](../knowledge/shared-techniques/camera-placement.md) | 高度、方向、距离、视线、主客观与观察权；双人／过肩／反打的收益损失 | 小津、阿克曼、用户对话教学；不将角度等同情绪 |
| [运动](../knowledge/shared-techniques/camera-movement.md) | 推拉摇移跟环绕升降手持；触发、路径、速度、终点及固定／剪辑替代 | Cuarón／Lubezki、Welles、Deakins资料；无模型精确轨迹保证 |
| [构图与光学](../knowledge/shared-techniques/composition-and-optics.md) | 透视与焦距区别、景深、遮挡、负空间、画中画、焦点转移 | Toland与Tati方法分析；数字镜头参数不是物理模拟证明 |
| [人物调度](../knowledge/shared-techniques/blocking-and-staging.md) | 人物独立任务、进出与穿越、前后景、遮挡期间行动、摄影路径与人物路径分开 | 多主体案例与固定时间案例；避免群众同步等主角 |
| [长镜头](../knowledge/shared-techniques/long-take.md) | 连续时间线、注意交接、路径可行性、固定与运动区别、电影镜头与技术单元区别 | 《1917》《历劫佳人》《让娜·迪尔曼》；不强制预演或固定时长 |
| [灯位](../knowledge/shared-techniques/lighting-placement.md) | C／A／W／P／背景的统一布局；主辅轮廓背景光、侧逆顶正面反射、距离范围、面积软硬、负补与遮光 | ARRI手册、Alcott采访；不编造灯数功率光比 |
| [光影与色彩](../knowledge/shared-techniques/lighting-and-color.md) | 动机光源、前中后层、冷暖、肤色材质、人物与摄影换位的光影连续 | 《巴里·林登》《1917》《花样年华》；不把色调当情绪规则 |
| [剪辑与声音](../knowledge/shared-techniques/editing-and-sound.md) | 声源引导、动作切点、听者时间、声画持续、连续音乐母带与模型分段的区别 | 小津、阿克曼及相关案例；本轮无音乐或声音听审 |

制作事实、署名评论、方法推导与当前场面候选明确分开。主要公开资料为ASC制作访谈、BFI、Criterion创作者／评论资料及British Cinematographer的Deakins访谈；不是泛化网页摘要。见[来源与定位](../knowledge/film-craft/research-sources-20261028.json)。原片灯图、精确机位／焦距未知时明确保留未知；未下载或批量转载电影素材。

用户目录全部可访问，3视频、19图片、ZIP20项均检查访问与去重。已看图片联系表、视频全长按时间采样；**没有完整音轨听审或逐帧观片**。教学词汇已转化成空间与观看问题，未采纳通用情绪公式和名导风格Prompt套装。详见[材料吸收与采样记录](../knowledge/film-craft/teaching-materials-20261028.md)。

## 3. 为什么需要这几处实际集成

原有 `SkillAuthor.knowledge(paths)` 只加载列出的文件，不会沿Markdown链接递归读取案例；正式文本作者接口也没有检索工具。只在Skill中加案例链接，不能保证正文进入调用。因此增加一个约百行的本地reader，复用现有索引与作者上下文，未增加检索服务或生产状态。

实际调用链：

```text
Host／Skill提出表达问题
  → find_cases.py --expression／--style／--goal／--means／--discipline
  → 选择或拒绝案例；读取case正文和共享方法（含来源边界与SHA256）
  → 已有authorContext.craftKnowledge／professional_context.craftKnowledge
  → FormalDirectionAuthor／FormalProfessionalAuthor同一次调用收到全文
  → Host选择后的具体方案进入已有专业owner字段
  → 原有OperationSelection → Prompt IR → Seedance编译
```

修改的现有Skill：Director、Cinematography、Blocking、Dramatic Performance Direction、Lighting Design、Production Design、Color Design、Shot Design、Editorial Design、Sound Design。各增加短的角色衔接，方法集中在[共享应用说明](../skills/director/references/film-practice.md)，没有重复案例库或新Skill。Storyboard／Previsualization通过现有Shot Design及协作引用使用空间／状态依据；未增加一个并行Storyboard owner。

[reader实现](../src/drama_plugin/creative_engine/craft_knowledge.py)与[正式作者入口](../src/drama_plugin/creative_engine/backends.py)只在已有上下文包含craftKnowledge时加载。Director的film_treatment／author／direct_film和Professional的design均接入；没有新增作者调用次数。Professional既有请求相关fingerprint包含读入正文；回放另留Director实际system摘要。没有选择时保持原路径。原`--problem`检索兼容，旧测试顺序不变。

检索是可检查别名与文本／标签匹配，**不是通用自然语言语义搜索**；它不会自动懂任意表达或自动决定运镜。目录顺序不是艺术排序。Host可扩大limit、指定案例、跨风格检索或拒绝全部；没有每镜案例配额、新审稿轮次或生产Gate。

专业职责保持：Director选择观看；Camera写机位和运动；Blocking／Performance写行动及时间；Lighting写来源和相对位置；Production Design核对同一空间；Editorial／Sound维护持续与切点。案例理由留在作者上下文或continuityInterpretation，执行条件进入原字段。没有把案例、作者名和论文段落堆入Prompt。

## 4. V6-01-04的实际应用结果

完整结果：[两案、灯位示意、时间关系、来源转化与技术边界](../knowledge/ai-production-evidence/v6-01-04/README.md)。

A固定：从门内雅科夫右后侧斜看对面窗口，让他占左缘较暗前景；青年折返和吻手自行改变注意，摄影不追随Y的一瞥。收益是观众有发现与持续观看的余地，代价是小屏动作可读性。

B移动：同一起点，街上折返触发门内短斜移，减少近景遮挡；接帽／吻手关系清楚时停下，摄影的停留长于Y的关注。收益是把观看空间逐步让给公共关系，代价是可能过度强调亲密或暴露未知地理。不是自动优于A。

两案共用街上天空、门洞、对面窗和墙面反射；移动后光源不跟摄影机走，没有新增浪漫轮廓灯。取自《玩乐时间》的自主发现、《人类之子》的独立注意、《巴里·林登》的光源与空间关系；保留收益代价和未采用部分，不复制原片场面。当前已选04-a只是观察证据，并未重新作为新起始帧绑定。

关键专业字段实际经过原编译代码：cameraPosition、height、lensIntention、movement.policy、sources、directionAndQuality、intensityRatios、constraints。每案31项文本覆盖，未覆盖执行项为0；A1110字符，B1176字符。该数字只证明传递，不能验收艺术效果。可读[固定Prompt](../knowledge/ai-production-evidence/v6-01-04/fixed-prompt.txt)、[移动Prompt](../knowledge/ai-production-evidence/v6-01-04/moving-prompt.txt)及[逐项继承记录](../knowledge/ai-production-evidence/v6-01-04/inheritance.json)。

当前助手完成的方案是真实知识应用；ReplayClient返回这份保留原稿，不是另一模型创造了方案。回放通过真实作者入口确认全文加载、通过专业字段验证，再运行实际native选择和编译。没有以Mock或通过测试宣称导演艺术能力已自动化达标。

## 5. 离线回归与未证明范围

运行命令（工作目录plugin）：

```sh
PYTHONDONTWRITEBYTECODE=1 ../.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_craft_knowledge_application.py tests/test_film_practice_delivery.py \
  tests/test_formal_author_backends.py tests/test_author_context_delivery.py \
  tests/test_seedance_unit_reconciliation.py tests/test_lighting_field_alignment.py
```

结果：**50 passed，2.45秒**。新增5项验证：无需预知技法的表达检索与交叉筛选、完整正文加载／无选择行为／路径边界、目录引用一致性、A／B真实native投影。A／B测试禁止socket连接；无模型／媒体调用。旧正式作者、上下文、灯光字段和T5相关编译测试通过。本轮未运行全仓库全部测试；无关架构没有修改。

尚未证明：独立文本作者在多种新场面中的选择质量；V6真实资产绑定后的几何可行性；Blender路径／视锥／灯光动态；Animatic可观看的节奏；Seedance的视差、吻手接触、转头时序、固定光源与跨段连续性；声画听审。没有本轮视频，就不能把文字条件齐全说成这些能力已实现。

建议Host只根据两案的实际表达价值决定是否继续。若继续，先解决B的门内通路与最大遮挡处，以及A的小屏可读性；再决定是否需要白模和小规模视频。无强制实验次数、固定镜长或新增阻断。保持Seedream 5.0 Pro／Seedance 2.0路线与现有技术成果。
