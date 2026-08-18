# Batch 6：短命令到多场景多镜头真实视频完整 Creative E2E 执行报告

## 1. Final Result

```text
BATCH_6 = PASS
SHORT_COMMAND_INTAKE = PASS
HISTORICAL_RESEARCH = PASS_WITH_HOST_FALLBACK
HISTORICAL_FACT_LEDGER = PASS

WORK_E2E = PASS
SCRIPT_E2E = PASS
EPISODE_E2E = PASS
MULTI_SCENE_CREATION = PASS
MULTI_SHOT_CREATION = PASS

ASSET_RESOLUTION = PASS
REFERENCE_SELECTION = PASS
SHOT_IMAGE_GENERATION = PASS
SHOT_IMAGE_REVIEW = PASS
SHOT_IMAGE_MEDIA_PERSISTENCE = PASS

SHOT_VIDEO_GENERATION = PASS
SHOT_VIDEO_DYNAMIC_REVIEW = PASS
VIDEO_TARGETED_REVISE = NOT_TRIGGERED_NO_CONTENT_FAILURE
SHOT_VIDEO_MEDIA_PERSISTENCE = PASS
MULTI_SCENE_VIDEO_E2E = PASS

MYSQL_PERSISTENCE = PASS
MINIO_PERSISTENCE = PASS
MEDIA_RESOLVE = PASS
MEDIA_INTEGRITY = PASS

DRAMA_SERVICE_CONFIG_DISCOVERY = PASS
MINIO_CONFIG_SOURCE = DRAMA_SERVICE_ACTIVE_APPLICATION_CONFIG
LOCALHOST_FALLBACK_USED = NO

CROSS_SHOT_CONTINUITY = PASS
CROSS_SCENE_CONTINUITY = PASS
EXECUTION_DECISION_TRACE = COMPLETE
HOST_INTERVENTION_LEDGER = COMPLETE

AUDIO_GENERATION = NOT_RUN
VIDEO_EDITING = NOT_RUN
NEXT_BATCH_6_1_READY = YES
```

本批从唯一短命令开始，真实建立 `Work → Script → Episode → 2 Scenes → 4 Shots → 1 Stable Asset → 5 Images → 4 Videos` 正式对象链。四条 Shot 均有 Review-PASS 图片和 Review-PASS 视频；两个 Scene 各有 2 条已持久化视频。9 条本批正式 Media 均完成 `Drama MCP → Java drama-service → MySQL → configured MinIO → media.resolve → SHA-256 equality`。

Batch 5.6 的 `FAIL_CONTENT_REVIEW` 历史结论未修改。本批没有出现足以触发 Video Content Review FAIL 的真实问题，因此没有为了展示流程强行制造 Video Revise；图片阶段有两次真实内容失败并各执行一次定向修订，最终 PASS。

## 2. Short Command

唯一业务输入原样为：

```text
创作一部关于安史之乱前期潼关之战的历史短剧。
```

用户没有补充 Scene、Shot、人物、台词、资产、Reference、视觉 Prompt、Motion Prompt、Provider 或 workflow。后续结构和生产参数由已激活的 historical-plugin Skills 结合正式 Tool Contract 编译。

## 3. Historical Research

### 3.1 Research 路由结果

优先执行正式 Research Tool Contract，但当前 `research.search_sources` 返回与潼关之战无关的《旧唐书·狄仁杰传》，`research.verify_claim` 又错误地用同一无关证据返回 supported。该结果被判为不可用于史料驱动创作，未写入事实账本。

为满足 Research First，Host 只读检索并选取 5 个一手史籍页面。该回退完整记录在 `HOST_INTERVENTION_LEDGER`；没有以模型记忆代替研究。

| Source | 类型 | 本批支持的事实 | 不确定性 / 边界 |
| --- | --- | --- | --- |
| [《资治通鉴》卷二百十八](https://zh.wikisource.org/zh-hant/資治通鑑/卷218) | 编年史 | 朝廷反复催促哥舒翰出关；灵宝西原战局、烟火、草车与败退因果；潼关失守 | 具体人物瞬时站位与逐字对话不详 |
| [《旧唐书》卷九](https://zh.wikisource.org/zh-hant/舊唐書/卷9) | 本纪 | 天宝十五载潼关战败、关门失守及其政治军事后果 | 不制造精确到日时的画面时间 |
| [《旧唐书》卷一百四](https://zh.wikisource.org/zh-hant/舊唐書/卷104) | 列传 | 哥舒翰守关与被迫出战、兵败被执等主线 | 不将戏剧台词冒充原诏原话 |
| [《旧唐书》卷一百六](https://zh.wikisource.org/zh-hant/舊唐書/卷106) | 列传 | 王思礼等将领处于前军/关键军事实践位置，可作为观察与行动视角 | 救旗手不是史料特指事件 |
| [《新唐书》卷一百三十五](https://zh.wikisource.org/zh-hans/新唐書/卷135) | 列传 | 王思礼身份、战事背景及败后延续性 | 人物神态、手势和私人措辞属改编 |

### 3.2 HISTORICAL_FACT_LEDGER

#### SOURCE_SUPPORTED

- 时间范围为天宝十五载、安史之乱前期的潼关失守前后。
- 守潼关本为有利态势，朝廷持续催促哥舒翰出关决战。
- 王思礼等将领参与唐军前军与战事执行，可作为非帝王中心的观察视角。
- 灵宝西原受南山与黄河夹逼，地形狭窄，唐军难以展开。
- 崔乾祐以弱阵诱敌，并利用山侧伏兵、滚石、草车、烟火和后续骑兵造成唐军崩溃。
- 唐军大败，残部极少返关，潼关最终失守，哥舒翰被俘。

#### DRAMATIZED_BUT_COMPATIBLE

- 作品选择王思礼为主视角，使用军议厅内“诏书压地图”的视觉隐喻。
- 中使不具名；具体言辞、令牌形制、地图画法、关门开启时机为戏剧化。
- 王思礼横马停旗、弃旗救活人，是将“识破危险但无法阻止大势、转而保存残部”外化为可拍动作。
- 军议厅调度、手势、眼神、旗手和传骑均为兼容性改编，不宣称史料逐项记载。

#### PROHIBITED_OR_UNSUPPORTED

- 不改变唐军战败、潼关失守、哥舒翰被俘的历史结果。
- 不把具体皇命措辞、人物心理或救旗手事件写成史料原文事实。
- 不制造无史料依据的精确日期、精确兵力或逐字诏书。
- 不把王思礼拍成扭转战局、击败叛军或庆祝胜利。

## 4. Business Object Tree

```text
Work  《潼关烟阵》
work_084411597e604d80ab704b299e73b254
└── Script  《潼关烟阵》短剧剧本
    script_00e6a377e6e945159105ab338ad0cf07
    └── Episode 01  关门之外
        episode_041d48a3a482446abb06b84cc9e5ab30
        ├── Scene 1  三催出关｜潼关关城军议厅
        │   scene_00c51d8eab484c7aa50f0a177858c468
        │   ├── Shot 1-01  诏压关图｜OTS_MEDIUM
        │   │   shot_3d90642edaa8418dac8fd795bc56f0dd
        │   └── Shot 1-02  接令开关｜MEDIUM_CLOSE
        │       shot_f110992f04ee46ef8e2570864392d248
        └── Scene 2  烟断归路｜灵宝西原南山与黄河之间狭道
            scene_cc05b7ad67bf4be18b8c72aa273e9344
            ├── Shot 2-01  弱阵烟起｜WIDE_MEDIUM
            │   shot_5196dc7b56204a01a0e38ebd0ea3b145
            └── Shot 2-02  弃旗救人｜MEDIUM_LOW
                shot_ac638206bee94baf9fa7fbda7b9f74ca
```

两个 Scene 在地点、叙事阶段、人物目标和事件功能上均真实不同：Scene 1 是关内战前决策，Scene 2 是关外战事执行与败局选择，不是同场景换景别。

文学 Review 结论：历史兼容性、主角动机、Scene purpose、Shot continuity 和视觉可执行性均 PASS。没有为展示流程强行修改已通过的 Work / Script / Episode / Scene / Shot。

## 5. Assets

Search First 对 `王思礼 + MASTER_CHARACTER_CARD` 返回空结果后才创建唯一稳定人物资产。没有创建 Shot 级重复身份，也没有为填满上限生成无关 Scene Master。

| assetId | Type | 状态 | Stable mediaId | 使用范围 |
| --- | --- | --- | --- | --- |
| `asset_6463c232c62f45a8b4253c92294bba56` | `MASTER_CHARACTER_CARD` | CREATED_AFTER_SEARCH_MISS | `media_1dcc573d78de4412b866bd5162e215be` | Scene 1/2、Shot 1-01/1-02/2-01/2-02 |

稳定 Reference：

- 实体：王思礼。
- Reference 数量：每条 Shot 1 张，小于 `MAX_REFERENCE_IMAGES = 3`，未为凑数添加图片。
- 锁定：四十至五十岁、清瘦结实、长脸与清晰颧骨、灰黑短须、黑色战巾、深褐札甲、暗红内衬。
- Master Provider 图视觉 Review PASS 后才加确定性标注并导入。
- 标注版 SHA-256：`4ff96cb63391e2c4e1e72f21c70593facb6831da9decbba5ec73625f67652059`。
- Drama / MinIO resolve / 本地 artifact 三方 hash equality：PASS。

## 6. Image Results

Comfy workflow 为官方 `api_google_nano_banana2_image_edit`，模型为 Nano Banana 2，1K、16:9。四镜均只传入上述单一王思礼稳定 Reference。

| Scene | Shot | References | Generation | Revise | Review | Media |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 三催出关 | 1-01 诏压关图 | 1 | 1 | 0 | PASS | `media_5797696a2e234f7ba8f804cd393ab2e8` |
| 三催出关 | 1-02 接令开关 | 1 | 2 | 1 | PASS_AFTER_REVISE | `media_9bf51dfab9d1437784ae665fb8a80b91` |
| 烟断归路 | 2-01 弱阵烟起 | 1 | 1 | 0 | PASS | `media_d8cf8fc39ca84958b406d264309f3308` |
| 烟断归路 | 2-02 弃旗救人 | 1 | 2 | 1 | PASS_AFTER_REVISE | `media_c0c3307d80cc4b3abf8573b236bee947` |

Provider jobs：

| Target | Initial Job | Revision Job |
| --- | --- | --- |
| Master 王思礼 | `8d500de0-2723-4f95-8674-7e5b6edbf7d1` | — |
| Shot 1-01 | `00abd609-8d0d-418d-aad9-53a64ef30a0f` | — |
| Shot 1-02 | `8e343d8c-55ca-40fd-b402-53ee6130d996` | `2cc61493-04b3-4c3a-b49a-690f0c7caab0` |
| Shot 2-01 | `612d62a1-feb5-4366-b7e6-2c4d0a7f9d27` | — |
| Shot 2-02 | `cabaaf7d-136a-4d2f-a4af-e09bad92d252` | `31ed5be9-05b5-4870-b1a4-9f5460c2000c` |

最终四图均为 1376×768 PNG。顺序严格为：

```text
Provider Image
→ Content / Structural Review
→ optional one targeted revise
→ Review PASS
→ deterministic shot annotation
→ media.import
→ media.get / media.resolve
→ integrity PASS
```

## 7. Video Results

正式视频 workflow 为官方 `api_seedance2_0_r2v`，模型 `Seedance 2.0 Mini`，单一 persisted START_FRAME，720p、16:9、4 秒、静音、无 watermark。每条 Motion Prompt 分离记录 Motion Intent、Camera Intent、Required Dynamic Evidence 与 Forbidden Dynamic Completion，没有整段复制图片 Prompt。

| Scene | Shot | Job | Generation | Technical Retry | Revise | Review | Media |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| 三催出关 | 1-01 | `2ea25a5e-5eea-4b08-ae99-431516ad65e0` | 1 | 0 | 0 | PASS | `media_94549833dccc442fa054a0b5fe83ee71` |
| 三催出关 | 1-02 | `b1b64700-61d0-4345-bf70-3ecff96e259c` | 1 | 0 | 0 | PASS | `media_347081f3c5a844f8ae2215b1ae229a2a` |
| 烟断归路 | 2-01 | `d5a346eb-1f08-4074-bdcb-da8acc044d18` | 1 | 0 | 0 | PASS | `media_511270d6c21647a8872cc95af5251e8d` |
| 烟断归路 | 2-02 | `497fac8a-a558-4acc-9a02-fcc178607f45` | 1 | 0 | 0 | PASS | `media_f81358b00d9646938e55d88266c56ba1` |

四个 MP4 技术属性一致：H.264、1280×720、24 fps、4.041667 秒、无音频流。动态 Review 抽取 first / 25% / 50% / 75% / last，并额外生成每 0.5 秒一帧的 8-frame contact sheet。四镜人物身份、服装、场景结构、关键道具与动作因果均稳定，无肢体融合、现代物、胜利语义或禁止的自动动作补全。

轻微视觉备注：Shot 1-01 的诏卷在末帧出现不可辨伪字形；Shot 2-01 旗面保留起始帧已有“唐”字。二者不是可读逐字皇命、现代文字或重大历史事实伪造，不影响动态叙事证据，Review 仍判 PASS；没有为审美微瑕疵无限抽卡。

### 7.1 已取消的消费门事故批次

一次不带 `confirm` 的成本探测调用没有返回门禁，Provider 反而意外入队四个视频 job。因用户当时只授权了上传、未授权视频消费，Host 立即取消并核验 `0 ready / 0 pending / 4 cancelled-or-failed`：

- `834b696f-a37e-46c6-a319-2f6248ec0709`
- `8c4dd8e5-97db-4451-b2d6-d1bcbc4ad7c8`
- `3492bf72-6613-4a9b-820e-f84756adacf9`
- `c4d74b2e-e0d3-4459-92e6-a8f9d7c40e3b`

该事故批次无产物、不计正式 Generation / Technical Retry / Revise。Comfy Tool 未暴露账单明细，因此取消批次是否产生瞬时预扣不作无证据断言。正式批次只在用户明确同意约 364 credits 后提交。

## 8. Review / Revise Cases

### Case 1：Shot 1-02 Image

```text
Initial Review = FAIL_CONTENT
Root Cause = 可见伪文字；地图过于现代化，违反“不伪造逐字诏令 / 不出现现代印刷地图”边界
Failure Classification = WRONG_TEXT_AND_PROP_RENDERING
Revision = 保持身份、构图、令牌、关门与轴线，只移除全部文字、图例和现代地图特征；诏书闭合
Generation Count = 2
Targeted Revise Count = 1
Technical Retry Count = 0
Result = PASS
```

### Case 2：Shot 2-02 Image

```text
Initial Review = FAIL_REQUIRED_SEMANTICS
Root Cause = 完整旗杆仍形成高位视觉主线；残旗没有明确低位西撤；救人双手动作不够清晰
Failure Classification = WRONG_PROP_STATE_AND_ACTION
Revision = 明确完整旗杆无人持有并斜落地面；传骑只低持半幅烧损残旗；王思礼双手拖救活人
Generation Count = 2
Targeted Revise Count = 1
Technical Retry Count = 0
Result = PASS
```

### Video Revise

```text
VIDEO_CONTENT_FAILURE_COUNT = 0
VIDEO_TARGETED_REVISE_COUNT = 0
VIDEO_TARGETED_REVISE = NOT_TRIGGERED_NO_CONTENT_FAILURE
```

Batch 5.6 的教训已转化为四条 compact Motion Prompt 中的 Forbidden Dynamic Completion；本批没有出现明确可修的 Forbidden Dynamic Semantic，故不强行生成第二版视频。

## 9. MinIO / MySQL

### 9.1 Active Configuration

```text
DRAMA_SERVICE_CONFIG_SOURCE = drama-service/server/src/main/resources/application.yml
ACTIVE_SPRING_PROFILE = default
MYSQL_HOST = rm-bp1cbl2dvuat0780nvo.mysql.rds.aliyuncs.com
MYSQL_PORT = 3306
MYSQL_DATABASE = drama
MYSQL_CREDENTIALS_PRESENT = YES

MINIO_CONFIG_SOURCE = DRAMA_SERVICE_ACTIVE_APPLICATION_CONFIG
MINIO_ENDPOINT = http://192.168.1.86:9000
MINIO_BUCKET = drama-media
MINIO_REGION = zh-east-1
MINIO_CREDENTIALS_PRESENT = YES
MINIO_CONNECTIVITY = PASS
LOCALHOST_FALLBACK_USED = NO
```

报告未输出数据库密码、MinIO access key、secret key、Drama Tool secret、Provider token 或签名 URL。

### 9.2 Media / Object Evidence

下表 objectKey 来自按 active drama-service 配置执行的只读 MySQL SELECT。正式写入全部通过 `Drama MCP → Java Media Contract`，没有 Agent 直写 MinIO。

| mediaId | Shot | Type / Purpose | objectKey | Bytes | SHA-256 / Resolve |
| --- | --- | --- | --- | ---: | --- |
| `media_1dcc573d78de4412b866bd5162e215be` | Master | IMAGE / REFERENCE | `work/work_084411597e604d80ab704b299e73b254/media/media_1dcc573d78de4412b866bd5162e215be/a1e42710-e588-4a82-839c-683d5f2755ea-wang-sili-master-reference.png` | 2,051,376 | `4ff96cb6…205959` / PASS |
| `media_5797696a2e234f7ba8f804cd393ab2e8` | 1-01 | IMAGE / START_FRAME | `work/work_084411597e604d80ab704b299e73b254/media/media_5797696a2e234f7ba8f804cd393ab2e8/18b0561d-0191-48be-86b3-af1612ca8850-shot-1-01-final.png` | 1,729,825 | `0602a51d…551b65` / PASS |
| `media_9bf51dfab9d1437784ae665fb8a80b91` | 1-02 | IMAGE / START_FRAME | `work/work_084411597e604d80ab704b299e73b254/media/media_9bf51dfab9d1437784ae665fb8a80b91/92ca94da-0cab-4068-b032-d9621c9f8b99-shot-1-02-final.png` | 1,820,607 | `0327949a…714e9` / PASS |
| `media_d8cf8fc39ca84958b406d264309f3308` | 2-01 | IMAGE / START_FRAME | `work/work_084411597e604d80ab704b299e73b254/media/media_d8cf8fc39ca84958b406d264309f3308/25214660-d5f6-4c0d-a0e7-0308ac2c7d26-shot-2-01-final.png` | 1,997,357 | `bc389e9e…1c2e4` / PASS |
| `media_c0c3307d80cc4b3abf8573b236bee947` | 2-02 | IMAGE / START_FRAME | `work/work_084411597e604d80ab704b299e73b254/media/media_c0c3307d80cc4b3abf8573b236bee947/e81f3376-e7c6-45ee-b6aa-08c1c1e11520-shot-2-02-final.png` | 1,955,598 | `60379a8b…621e8` / PASS |
| `media_94549833dccc442fa054a0b5fe83ee71` | 1-01 | VIDEO / VIDEO | `work/work_084411597e604d80ab704b299e73b254/media/media_94549833dccc442fa054a0b5fe83ee71/492acbbb-8a69-4e8f-8f80-ab3cf8cf3304-shot-1-01-video.mp4` | 4,886,703 | `83a04fcf…0bdc5` / PASS |
| `media_347081f3c5a844f8ae2215b1ae229a2a` | 1-02 | VIDEO / VIDEO | `work/work_084411597e604d80ab704b299e73b254/media/media_347081f3c5a844f8ae2215b1ae229a2a/955667a4-6f41-420c-9c2c-ee9a80fe671e-shot-1-02-video.mp4` | 5,941,353 | `4bddfb70…783b7` / PASS |
| `media_511270d6c21647a8872cc95af5251e8d` | 2-01 | VIDEO / VIDEO | `work/work_084411597e604d80ab704b299e73b254/media/media_511270d6c21647a8872cc95af5251e8d/acdc62fc-87df-46c5-88fd-af8edad46b69-shot-2-01-video.mp4` | 6,989,350 | `2bd0c492…5cbd4` / PASS |
| `media_f81358b00d9646938e55d88266c56ba1` | 2-02 | VIDEO / VIDEO | `work/work_084411597e604d80ab704b299e73b254/media/media_f81358b00d9646938e55d88266c56ba1/9192cf25-e4e3-4923-9044-6e4aaf25a19a-shot-2-02-video.mp4` | 7,322,983 | `2da05701…adc6` / PASS |

对每条 Media 均满足：

```text
MYSQL_ROW_EXISTS = YES
MINIO_OBJECT_EXISTS = YES
media.get = PASS
media.resolve = PASS
LOCAL_ARTIFACT_SHA256 == METADATA_CONTENT_HASH == RESOLVED_SHA256
```

## 10. Cross-Shot / Cross-Scene Review

### 10.1 Scene 1 Cross-Shot

- Character：王思礼脸型、年龄、发须和黑战巾一致。
- Costume：深褐札甲与暗红内衬一致。
- Scene / Lighting：同一关城军议厅、同侧轴线、冷暗自然光一致。
- Props：1-01 诏压完整地图；1-02 延续同一诏书并将地图卷起，新增令牌符合 Shot delta。
- Motion：1-01 静态对峙；1-02 极慢推进和卷图，动作强度递进但不跨轴。
- Narrative：从拒接诏书到压抑接令、关门开缝，因果连续。

### 10.2 Scene 2 Cross-Shot

- Character / Costume：同一王思礼、同一甲胄，合理增加尘土而不换装。
- Geography：南山右、黄河左远景和西撤方向保持可解释。
- Props：2-01 完整前军旗；2-02 完整旗杆弃地、半幅残旗低位西撤，状态转移清晰。
- Motion：2-01 横马停旗与士卒继续挤行；2-02 低机位救人和撤退，运动风格由警戒转为保存残部。
- Structural：马、人物、双手、旗杆和烟幕未出现不可接受形变。

### 10.3 Cross-Scene

- Same Character Identity：两地均复用同一 Master Asset / Media，脸、发须、年龄和甲胄轮廓稳定。
- Period Consistency：室内与战场均维持唐代军政视觉语汇，无现代物。
- Costume Progression：Scene 2 仅增加尘灰，属于允许的场景 delta。
- Narrative Continuity：关内识别风险却被迫出战，直接过渡到关外识破诱敌、败局中救人撤退。
- Historical Continuity：未改变战败、潼关失守和主战因果；不同地点没有被误判为背景不一致。
- Lighting：Scene 1 冷暗关城、Scene 2 灰黄烟尘是叙事阶段差异，不是 continuity failure。

## 11. Execution Decision Trace

下表只记录外部可观察的高层关键转折，不包含隐藏推理或逐 token 思维过程。

| # | State | Decision | Reason Category | Owner | Action | Result |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | 仅收到短命令 | 先 Research | HISTORICAL_EVIDENCE_REQUIRED | SKILL | `historical-research` + research tools | 正式 Research 返回无关证据 |
| 2 | Research Tool 证据不可用 | Host 回退一手史籍检索 | PROVIDER_EVIDENCE_INVALID | HOST | 只读 web research | 建立可追溯 Fact Ledger |
| 3 | 事实边界完成 | 创建独立 Batch 6 Work | SEARCH_MISS_CURRENT_CONTEXT | SKILL / TOOL_CONTRACT | search → create Work | Work PASS |
| 4 | Work 完成 | 采用王思礼非帝王视角 | DRAMATIC_VIEWPOINT | SKILL | work / script adaptation | Script / Episode PASS |
| 5 | Episode 目标确定 | 划分关内决策与关外败局两 Scene | MULTI_SCENE_DRAMATIC_FUNCTION | SKILL | scene development | 2 Scene PASS |
| 6 | Scene 可视化 | 每 Scene 两 Shot | VISUAL_EXECUTABILITY | SKILL | shot design | 4 Shot PASS |
| 7 | 四镜均出现王思礼 | Search 后只建一个 Master Asset | STABLE_IDENTITY_REUSE | SKILL | asset search/create | 1 Asset + 1 Reference Media |
| 8 | Shot image planning | 每镜只用 1 张稳定 Reference | MINIMAL_EXPLAINABLE_REFERENCE | SKILL | Comfy image edit batch | 4 初始图完成 |
| 9 | 1-02 / 2-02 图片 Review FAIL | 各执行一次定向修订 | WRONG_TEXT / WRONG_PROP_STATE | SKILL | targeted image edit | 两镜 PASS，修订封顶 1 |
| 10 | 四张图片 PASS | 先标注再持久化 | REVIEW_BEFORE_PERSISTENCE | TOOL_CONTRACT | annotation → media.import/resolve | 4 START_FRAME integrity PASS |
| 11 | Persisted Shot images ready | 选择 Single Image → Video | VALID_INPUT_AVAILABLE | SKILL | motion compilation | 4 条 compact Motion Prompt |
| 12 | 未确认成本却意外入队 | 立即取消 | SPEND_AUTHORITY_NOT_GRANTED | HOST | cancel 4 jobs | 0 ready / 4 cancelled |
| 13 | 用户明确确认视频消费 | 正式提交一批四视频 | PROVIDER_CONFIRMATION_OBTAINED | HOST / TOOL_CONTRACT | Comfy submit_batch | 4 jobs completed |
| 14 | 视频完成 | 动态抽帧而非只看 job 状态 | SEMANTIC_REVIEW_REQUIRED | SKILL | ffprobe + 0.5s contact sheets + last | 4 Review PASS |
| 15 | 视频 Review PASS | 不强行 Video Revise | NO_CONTENT_FAILURE | SKILL | continue to persistence | revise 0 |
| 16 | 4 MP4 PASS | 通过正式 Java Media Contract 持久化 | DURABLE_MEDIA_REQUIRED | TOOL_CONTRACT | import/get/resolve/hash | 4 Video integrity PASS |
| 17 | 两 Scene 各有 2 视频 | 完成跨镜/跨场审计 | CONTINUITY_GATE | SKILL | structured review | PASS |

## 12. Host Intervention Ledger

| # | Type | Intervention | Why | Could Skill Own It? |
| ---: | --- | --- | --- | --- |
| 1 | HOST_INTEGRATION | 读取并激活 historical research / work / script / episode / scene / shot / asset / production Skills | 正常 Plugin/Host 执行 | 否，属于 Host 加载与路由 |
| 2 | BUSINESS_DECISION | Research Tool 返回无关且自相矛盾证据后，Host 选择 5 个一手史籍页面 | 史料驱动任务不能使用无关 mock 证据 | 可；应由未来可靠 Research Provider / Skill fallback 承担 |
| 3 | ENVIRONMENT | 从 active `application.yml` 解析 MySQL / MinIO；检查 credentials present、connectivity 和 profile | 避免 localhost fallback | 否，属于运行环境核验 |
| 4 | ENVIRONMENT | 常驻 Java / MCP 会话退出后按原配置恢复服务 | 继续真实持久化链路 | 否 |
| 5 | PROVIDER_CONFIRMATION | 用户分别确认 Master、四图、两图定向修订、四视频消费 | 正式 Provider spend gate | 否，必须保留 Host/User 安全交互 |
| 6 | ENVIRONMENT | 私有 Reference / Shot frames 上传 Comfy 前请求用户明确授权 | 外部数据传输边界 | 否，必须保留安全确认 |
| 7 | HOST_INTEGRATION | macOS 按 Provider 签名 URL 下载输出 | 正常输出传输 | 否 |
| 8 | ENVIRONMENT | 并发 upload 触发 OAuth `refresh token reuse detected`，用户重新授权后改为串行上传 | Provider OAuth 运行故障 | 否；Adapter 可改进令牌刷新互斥 |
| 9 | PROVIDER_CONFIRMATION | 无 confirm 成本探测意外入队四视频，Host 立即取消 | 用户尚未授权视频消费 | 否；Tool spend gate 应修复 |
| 10 | HOST_INTEGRATION | 通过只读 MySQL SELECT 补充 Tool Contract 未暴露的 objectKey | 报告硬性审计字段 | 部分；未来审计 Tool 可安全暴露非敏感存储证据 |
| 11 | ENVIRONMENT | 用 ffprobe/ffmpeg 提取技术属性、0.5 秒密集帧和末帧 | 动态 Review 证据 | 可部分封装为既有 Production Review 工具，但本批不重构 |

```text
HOST_BUSINESS_DECISION_COUNT = 1
```

该业务干预仅为无效 Research Provider 的证据回退；Scene、Shot、Asset、Reference、Image/Video Prompt 和 Review/Revise 均按 Skill 方法自主产生，不来自用户扩展输入。此处只记录，不提前实施 Batch 6.1 重构。

## 13. Spend / Retry Ledger

```text
MASTER_IMAGE_GENERATION = 1
SHOT_IMAGE_INITIAL_GENERATION = 4
SHOT_IMAGE_TARGETED_REGENERATION = 2
SHOT_VIDEO_FORMAL_GENERATION = 4

IMAGE_TARGETED_REVISE_COUNT = 2 targets × 1
VIDEO_TARGETED_REVISE_COUNT = 0
GENERATION_TECHNICAL_RETRY_COUNT = 0
```

用户确认时的估算：Master 约 18 credits，四图约 72，两图定向修订约 36，四视频约 364，总授权估算约 490 credits。Comfy Tool 未提供最终账单或实际 debit，报告不将估算冒充实扣。被取消的意外视频批次是否产生预扣未知。

OAuth reauthorization、服务恢复、只读 polling、get_output 刷新、curl 自带网络重试、Media file-URI 契约纠正均不计 Generation Technical Retry。初次 `media.import` 使用裸路径被 Tool 在读文件前拒绝，改为规范 `file://` URI 后成功；没有重复业务对象。

## 14. Changed Files

```text
CODE_CHANGED = NO
PRODUCTION_SOURCE_CHANGED = NO
```

本批新增执行报告：

- `docs/reports/06-00-short-command-multiscene-video-full-e2e.md`

本批新增审计 artifacts：

- `docs/reports/artifacts/batch6/annotate_frame.py`：只用于 macOS 确定性标注，面板外像素不变；不是生产框架。
- 王思礼 Provider / Reference 图各 1。
- 四镜首轮 Provider 图 4、定向修订图 2、最终标注图 4。
- 最终 MP4 4、0.5 秒 contact sheets 4、末帧 4。

工作树中原有 `docs/reports/37-Batch5.6-real-video-generation-validation.md` 修改不是本批产生，本批未覆盖或修改 Batch 5.6 报告。

## 15. Technical Debt

```text
Windows GCS Signed URL download = DEFERRED_TECHNICAL_DEBT
```

macOS 本批四图、两张修订图和四视频均成功从 `storage.googleapis.com` 下载，没有复现 Windows 问题，因此未建设 proxy、GCS adapter 或 custom downloader。

新增观察但不在 Batch 6 修复：

- Research HTTP Provider 当前 mock 证据与主题无关，且 verify_claim 可错误返回 supported。
- Comfy OAuth 并发 refresh 会触发 `invalid_grant: refresh token reuse detected`；串行调用可恢复。
- Comfy submit_batch 的原生 elicitation 在当前客户端不可用，需要手动消费确认；一次无 confirm 探测仍意外入队，Spend Gate 行为需要审计。
- Media Tool Contract 不返回 objectKey，报告只能用只读 MySQL 补证。
- Java Media Result 把 storage hash / mime / size 留在内部列，当前审计需要在 Media content 冗余写入 hash 字段。

以上只作为 Batch 6.1 输入，本批没有修改 Skill Core、Tool Contract、Adapter 或 orchestration framework。

## 16. Batch 6.1 Readiness

```text
HOST_DEPENDENCY_EVIDENCE_CAPTURED = YES
DECISION_TRACE_COMPLETE = YES
HOST_INTERVENTION_LEDGER_COMPLETE = YES

NEXT_BATCH_6_1_READY = YES
```

Batch 6 到此停止。没有进入 TTS、BGM、音效、lip sync、audio mux、timeline、字幕、镜头拼接或最终 Episode render；下一步仅为 `Batch 6.1 — Host Dependency Audit`。
