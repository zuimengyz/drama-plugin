# T2 第一轮实施：导演统领人物、观看与视觉叙事

日期：2026-10-25。范围：T2-1、T2-3，以及 T2-2 的人物生命感核心方法。

本轮已修改源码与 Skills，并完成离线传递验证。没有更新正式 S01、重做资产或生成影片。
实现使用现有 Host 支持/选择、WorkDirectingAuthority、FilmDirection、专业作者和资产序列；
没有新增创作审批、评分器、风格配置或生产主循环。Host 保留独立剧本及最终艺术选择权。

## 实际改变

| 环节 | 这轮改变 | 权责边界 |
|---|---|---|
| Director / T2-1 | 将人物正在做的事、观众的观看位置、场景间与场景内部的视觉发展，纳入同一次场景选择；记录选得与所失 | 专业可以提出反衬和不同解释，Host 不必强迫各专业表达同一种情绪 |
| Performance + Embodiment / T2-2 核心 | 用投入、承重、注意、受打断和等待理解人物生命状态；区分身体倾向与此刻策略 | 不靠动作数量、脏旧、皮肤纹理制造生命感；不将一次愤怒或防御姿态变成人物身份 |
| Production Design + Asset Design | 在覆盖、参考证明冻结前考虑身体、服装、道具、环境能否承载选定关系；资产读取整场导演方案 | Production Design 协调冲突，具体资产仍由其作者设计；中性身份证明不自动成为影片摄影标准 |
| Camera + Lighting + Color / T2-3 | 共同选择可见与不可见、世界持续存在的层次、光色随关系的变化或反衬 | 不把全面展示当默认目标；维持物理世界不等于所有镜头复制同一亮度、色温和构图 |
| Shot 与专业输出 | 已选意义进入 purpose、performanceDirection、cameraIntent，再由专业写成当下可见/可听事实 | 理由留在既有导演原件、DPD、continuityInterpretation；最终请求不附整篇美学说明 |

方法集中在 [scene-collaboration.md](../skills/director/references/scene-collaboration.md)。
各 Skill 只补充本专业的关键职责及入口，没有各自复制一套规则。
创作协作由 Host 按问题调用现有支持能力；代码没有自动强制所有部门会商或增加付费调用。
本轮也没有新增外部 Character Repository 导入器；已有、可溯源的 Embodiment 仍由原 owner 提供。

## 最小代码修补

1. `film/capability.py`：原生电影子任务固定同一已选 FilmDirection 的逐场引用。
   镜头作者继续读取本场有序覆盖及当前镜头；资产准备可以读取更早场景自己的完整导演上下文。
2. `professional_design/asset_sequence.py`：读取独立场景剧本时，同时保留已选导演上下文。
   资产作者及其保留的参考图作者输入获得整场方案，不带当前镜头选择。
   原先已准备或已采纳的资产不自动重写；历史单场输入仍可使用原有 sceneDirection。
3. `creative_engine/author_projection.py`：内部逐场引用留在本地，只将被选择场景的创作语义交给作者。
4. `creative_engine/backends.py`：真实 Director、专业、资产及参考图作者入口加载同一协作方法。
   专业作者的共享指令覆盖人物任务、观看关系和当下光色，不再只强调走位/摄影/剪辑接合。

未新增必填美学 DTO 或模型输出字段。新增引用由既有对象存储固定，Runtime 仍不产生艺术决定。
当前已选原件改变时，需要按既有版本/资产重审路径工作，不会覆盖旧子任务的固定输入。

## S01 离线案例：选择怎样落地

此案例是本轮编写的 **OFFLINE_AUTHORED_FIXTURE**，不是 S01 的新正式导演版。
它抽取“合奏—冲突—工钱”三个观察片段，不替换完整剧本、台词或 K01–K06。
测试中的 8 秒仅用于请求序列化，不是本轮确定的电影时长，也不是 Skill 规则。

已有 S01 场面意图中“合奏确实成立”“留下者仍须工作”“被遣走者需要下一次工钱”得以保留。
参考依据为生产目录的 `S01/01-导演场面构思.md` 与 `S01/05-协作往返与Host选择.md`；
这些原件本轮只读，未改写。三张审美参考转化为以下能力：

- 图一：演奏任务组织头颈肩、手与注意，允许局部遮挡；不借用参考人物的脸、头发或服装。
- 图三：环境与其他人有自己的活动，摄影不默认清空空间来展示主角；不照搬构图或场所。
- 图二：身体、视线、桌面和光区共同构成关系压力；冷峻不能只靠冷色滤镜。

| 片段 | 已选导演关系 | 进入专业设计和最终视频请求的可见选择 |
|---|---|---|
| 合奏 | 劳动投入带来暂时自在，其他人仍有自己的工作 | 肩颈随运弓承重，注意琴弓接触；侧前方观察，局部遮挡；暖实用光照手与侧脸，背墙暗，远侧弱冷层 |
| 冲突 | 手艺支配变成对同伴的压迫，婚宴未随之停摆 | 两人保持对视距离及持物状态；侧面同时容纳双方与客席；保留婚宴暖色，转身改变面部受光，拒绝自动全场变蓝 |
| 工钱 | 逞强后仍要等雇主回答下一次是否用他 | 钱已入袋，手停袋口，抬眼等答；偏侧面保留视线间隔；墙席弱冷窗光主导近处，远宴暖光仍在，暗面不普遍补亮 |

工钱方案是有代价的案例选择：它强化受雇关系的转折，但必须在将来的画面中验证墙席、窗与人物的关系。
另一种“始终保持暖宴环境”的处理也有价值，可以表现环境对人物处境的漠然。
Host 在本案例选择前者，同时保留冲突段的暖色反衬；没有将“暖=善、冷=恶”写入通用方法。

实际离线路径如下：

`完整场景摘编 → 支持意见 → Host KEEP_ALL 与艺术选择 → 选定 WorkDirectingAuthority
→ 原生 Film Direction 作者入口 → 三个 Shot → 固定场景上下文
→ 资产作者 / 参考图作者输入 → 已选资产的测试元数据
→ 专业作者入口与专业 owner 持久化 → ShotAssembler
→ PromptCompiler → TargetHttpTransport.preview`

测试使用真正的生产代码入口和序列化器，但文本响应由预写夹具通过 MockTransport 返回。
没有调用模型作创作判断。资产采纳仅存在于隔离的临时测试库，引用的是无图片文件的测试元数据。
最终视频请求是 text_to_video 的离线预览，`provider_submission_allowed=false`。
因此，这证明选定意义的传递与字段消费，不证明参考图像控制、模型表演能力或影片审美已提高。

已核实的边界：

- 从工钱镜头开始准备，资产作者仍收到整场三个阶段，参考图作者沿用同一个保留上下文。
- 三个镜头沿用同一批测试资产身份，资产作者没有被要求永久固定某一阶段的表情。
- 当前镜头的身体、摄影、灯光、色彩、剪辑决定进入实际请求文本。
- 核心身体与摄影决定在本案例请求中各出现一次；邻镜的摄影/灯光、未选方案、内部引用和艺术理由不混入。
- 后来的导演版本不会回写旧子任务输入，或重新创作已准备的前序资产。
- 跨场景逆序准备使用各场自己的固定上下文，不拿后场的表现代替前场身份。

## 验证结果与限制

验证进程禁止 socket 网络连接；真实服务调用数为零。

- 相关回归批次：95 项通过；2 项旧 mock 因匹配过时的 `same Host author` 文句失败。
  改为按实际 `preservedV1` 输入结构识别后，这两项复跑均通过。共 97 项相关用例得到通过结果。
- 新增 S01 全链路及跨场景/版本恢复两项用例均通过；它们包含于上述相关用例。
- 9 个涉及的 Skill 通过 `quick_validate.py`；`git diff --check` 通过。
- 额外的原生跨镜测试发现 4 项 `CROSS_SHOT_HOST_JUDGMENT_REQUIRED` 失败。
  将本轮修改的生产方法在内存中替换为 Git HEAD 版本后，四项仍同样失败。
  这些测试缺少既有跨镜 Host 判断记录，本轮没有改变该生产机制或伪造判断来使它们变绿。
  扩展批次在发现这些失败后中止，不宣称全仓测试通过。

四项已复现的基线失败位于 `tests/test_native_film_boundaries.py`：

- `test_observed_adult_identity_excludes_forbidden_child_age_in_native_cut`
- `test_native_cut_school_return_location_and_recovery_actual_wire`
- `test_designed_cross_scene_boundary_not_scene_id_rule[match]`
- `test_same_shot_montage_cuts_do_not_replay_or_require_equal_tail`

测试本身不能验证人物是否鲜活、观众是否感受到受雇压力、光色反差是否自然，
也未证明现有 S01 已采纳资产足以支持这些新选择。那些结论需要将来获授权后的实际画面评审。
本轮没有自动安装或热替换应用中的 Plugin 缓存；交付为当前源码工作区的未提交修改。

## 修改文件

生产代码四个文件：

- `src/drama_plugin/film/capability.py`
- `src/drama_plugin/professional_design/asset_sequence.py`
- `src/drama_plugin/creative_engine/author_projection.py`
- `src/drama_plugin/creative_engine/backends.py`

Skills 共九个专业、十一个文件：

- `skills/director/SKILL.md`
- `skills/director/references/scene-collaboration.md`
- `skills/director/references/work-aesthetic-design.md`
- `skills/dramatic-performance-direction/SKILL.md`
- `skills/character-embodiment/SKILL.md`
- `skills/production-design/SKILL.md`
- `skills/cinematography/SKILL.md`
- `skills/lighting-design/SKILL.md`
- `skills/color-design/SKILL.md`
- `skills/specialized-asset-design/references/relational-aesthetics.md`
- `skills/shot-design/SKILL.md`

测试及说明：

- `tests/test_director_encounter_delivery.py`：新增离线场景选择、作者输入、最终请求与版本恢复追踪。
- `tests/test_event_scope_delivery.py`：既有离线编译辅助函数可复用同一 Plugin，经真实专业 owner 保留资产绑定。
- `tests/test_work_aesthetic_delivery.py`、`tests/test_formal_author_backends.py`：修复过时 mock 识别条件。
- 本文 `docs/director-encounter-r1.md`。

本轮开始前已有的 `src/drama_plugin/visual/frame_request.py`、`tests/test_visual_prompt_ir.py`
及 `.DS_Store` 工作区改动均保留，不计入本轮实施。

## 证据与复跑

证据目录：`/Users/zy/historical-plugin/artifacts/t2-director-encounter-r1-20261025/evidence/`。

- `s01-01-selected-direction.json`：支持原件、Host 选择、Director 实际输入及选定输出。
- `s01-02-asset-authors.json`：资产作者/参考图作者实际输入、保留上下文及测试资产设计。
- `s01-03-video-ensemble.json`、`s01-03-video-conflict.json`、`s01-03-video-wages.json`：专业输入、专业原件及实际最终请求预览。
- `s01-04-recovery-and-cross-scene.json`：前序场景上下文、旧子任务与已准备资产不变的回归证据。

在仓库根目录复跑核心案例：

```sh
AESTHETIC_EVIDENCE_DIR=/private/tmp/t2-encounter-evidence .venv/bin/python -m pytest plugin/tests/test_director_encounter_delivery.py -q
```

核心案例自身禁止网络。输出只有 JSON 文本证据；没有生成图片、视频或音频。
未调用 Seedance、Seedream 或任何付费文本模型，未改写既有正式生产数据库、Prompt、资产或采纳记录；
未 commit、push 或 merge。
