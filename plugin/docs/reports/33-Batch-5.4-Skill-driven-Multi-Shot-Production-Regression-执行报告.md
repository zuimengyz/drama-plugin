# Batch 5.4 — Skill-driven Multi-Shot Production Regression 执行报告

执行日期：2026-08-17（Asia/Shanghai）  
Work：`work_4cf81e8862234727b082cf2115ec699b`  
Scene：`scene_399ace55923e47be8092eb808d7d284c`（5-2 一桌家书）

## 1. Executive Summary

本批实际加载并以正式 `shot-production` Skill Core 作为生产规则源；安装缓存中的 `SKILL.md`、`production-rules.md` 与仓库 Batch 5.3 正式版本 SHA-256 分别一致。Host 只使用第 3 节记录的简短业务 Prompt，没有把外围验收文字改写成 Provider Prompt 或独立导演规则。

Skill 已自主完成三条 Shot 的权威上下文读取、Visible Entity Discovery、Reference Candidate Discovery、Reference Planning、缺失 Reference 识别、Sequence Context、Prop State Transition 与 Shot Delta Compilation。它识别出 5-2-04/05 的关键可见人物苏武没有 `MASTER_CHARACTER_CARD`，返回 `MISSING_STABLE_REFERENCE = 苏武`，并依正式协作边界激活 `asset-resolution`。

运行在正式生成前被视觉能力门禁阻断：当前 Windows Host 的正式 MCP 清单只有 `drama-tools`，没有 `comfy-cloud`；Drama MCP 的 `production` provider mode 为 `mock`，不能充当真实 Reference 或 Shot Provider。正式 Skill 明确要求在这种情况下返回 `VISUAL_PROVIDER_UNAVAILABLE`，不得临时安装、配置或模拟 Provider。因此没有创建苏武 Master，没有提交 Shot job，没有 Provider 输出、Per-Shot Review、Targeted Revise、Cross-Shot Review、Identity Annotation 或新 Shot Media persistence。

环境 fallback 本身验证通过：李陵 Character Master 与苏武穹庐 Scene Master 的 Shared MySQL `content_hash` 均与仓库中已完成 Review/Annotation 的 artifact SHA-256 完全相等。当前 Local MinIO 健康端点 PASS，但两个历史 object 的真实下载均为 HTTP 404，所以只能标记 `TRUSTED_ARTIFACT_FALLBACK`，不能声称 `CURRENT_HOST_STABLE_MEDIA_RESOLVE = PASS`。

结论：Skill-driven planning/compilation 成立，完整的 Skill-driven online production 本批未成立；`BATCH_5_4 = BLOCKED`。阻断来自当前 Host 缺少正式视觉 Provider，不是历史 Local MinIO portability，也不是 Reference Planning/Continuity 规则缺失。

## 2. Minimal Environment Bootstrap

### 2.1 Runtime

| Item | Result | Evidence |
|---|---|---|
| Shared MySQL | PASS | Java 使用当前 `drama-service` 配置启动；对 `drama_media` 的只读查询返回两项 Stable Media metadata 与 `content_hash` |
| Current Local MinIO health | PASS | `http://localhost:9000/minio/health/live` 返回 200 |
| Current Local MinIO historical object availability | FAIL | 两项 `media.resolve_media` 均返回可解析 metadata，但实际下载均为 HTTP 404 |
| Drama Java | PASS | 当前 jar 按仓库 `application.yml` 启动于 8080；未改配置 |
| Drama MCP | PASS | 当前 `.env` 启动于 8765；44 项正式 Tool Contract 可发现 |
| Visual Provider | FAIL | 当前 Host MCP 清单无 `comfy-cloud`；Drama `production` mode 为 `mock`，不具备正式视觉执行资格 |

### 2.2 Existing Stable Reference bootstrap

| Reference | Stable Asset | Stable Media | Shared MySQL `content_hash` | Current Host resolve | Trusted artifact SHA-256 | Result / source mode |
|---|---|---|---|---|---|---|
| 李陵 Character Master | `asset_df44cfb7db1646f2a7b7eae2463a032e` | `media_fe9dae51b9a74c8ea4819784eca27154` | `742bd90ef8d5da24be3c1037b386079fe3d8d6cb6869b5b5d5a81c9b41bfa51d` | FAIL / object 404 | `742bd90ef8d5da24be3c1037b386079fe3d8d6cb6869b5b5d5a81c9b41bfa51d` | Hash equality PASS / `TRUSTED_ARTIFACT_FALLBACK` |
| 苏武穹庐 Scene Master | `asset_c13dbef904f04c63bc48de0a8505be66` | `media_ec444a5cf36040bcb96b2b12b8a6ea6e` | `5e0eddccf35284a98ba79087abed64ceb539614aab308138fa151f45f0b8eb71` | FAIL / object 404 | `5e0eddccf35284a98ba79087abed64ceb539614aab308138fa151f45f0b8eb71` | Hash equality PASS / `TRUSTED_ARTIFACT_FALLBACK` |

两张 artifact 均在本批实际打开检查，标签与主体可见；其既有 `visualContentReview=PASS`、`annotationValidation=PASS` provenance 来自 Stable Media/Asset metadata 和 29 号报告。本批没有重新 Review、重新标注或重新导入它们。

明确记录：

```text
GLOBAL_MEDIA_METADATA = EXISTS
LOCAL_MEDIA_OBJECT = UNAVAILABLE
CURRENT_HOST_STABLE_MEDIA_RESOLVE = FAIL
TRUSTED_ARTIFACT_FALLBACK = PASS
```

未研究或修改 MinIO；未直接写 MinIO；未创建重复 Stable Asset。

## 3. Host Prompt

本批真正用于启动 Skill 的 Host 业务 Prompt 原样如下：

> 继续制作 Scene `5-2 一桌家书` 的连续镜头 `5-2-04`、`5-2-05`、`5-2-06`。  
> 使用 historical-plugin 的正式 Skill 自主完成必要的资产解析、Reference Planning、连续性控制、镜头生产、质量审查、必要修订和 Media 持久化。  
> 不生成视频。

外围 Batch 文本只作为环境降级和验收边界；下述 Reference、Continuity、Delta、Review 门禁均来自正式 Skill Core 与权威 Scene/Shot/Asset/Media Tool 结果。

## 4. Skill Activation

### `shot-production`

实际加载：

- `skills/shot-production/SKILL.md`
- `skills/shot-production/references/production-rules.md`
- `skills/shot-production/references/visual-provider.md`

执行内容：读取 Scene/Shot；发现可见实体；搜索 Stable Asset/Media；建立不持久化的 Sequence Context；规划不超过 3 项 Reference；编译 Shot Delta；执行 Drama/Visual preflight。

### `asset-resolution`

由 `shot-production` 的 `MISSING_STABLE_REFERENCE = 苏武` 自主触发，而非 Host 手写“生成苏武 Reference”。`asset-resolution` 再次 search-before-create，确认苏武 `MASTER_CHARACTER_CARD = NOT_FOUND`。由于正式视觉 Provider 不可用，它在生成前停止，未调用 mock `production.generate_image`，未创建 Media 或 Asset。

```text
DRAMA_PROVIDER_UNAVAILABLE = NO
VISUAL_PROVIDER_UNAVAILABLE = YES
VISUAL_PROVIDER_CAPABILITY_MISSING = YES
PROVIDER_AUTH = NOT_ATTEMPTED
```

没有出现 `invalid_grant`，故没有执行 OAuth recovery；这符合“只有再次出现指定 OAuth 错误时最多 login 一次”的边界。

## 5. Reference Planning

`MAX_REFERENCE_COUNT = 3` 来自正式 Skill Core。以下是 Agent Run Context 中的实际规划；“actual count”统一指真正进入 Provider 的 Reference 数，本批均因 preflight gate 为 0。

### Shot A — 5-2-04

| Field | Result |
|---|---|
| visible entities | 李陵、苏武、苏武穹庐 |
| candidates | 李陵 Character Master；苏武 Character Master；苏武穹庐 Scene Master |
| selected suitable existing | 李陵 Character Master；苏武穹庐 Scene Master |
| missing | 苏武 Character Master（关键清晰可见人物） |
| omitted | 无可合法静默省略项 |
| rationale | 两名主要人物身份和 Scene 连续性均必要；苏武缺失使计划不完整，必须先由 `asset-resolution` 解决 |
| source modes | 李陵=`TRUSTED_ARTIFACT_FALLBACK`；穹庐=`TRUSTED_ARTIFACT_FALLBACK`；苏武=`UNAVAILABLE` |
| planned count after required resolution | 3 |
| actual Provider count | 0 |
| status | `MISSING_STABLE_REFERENCE` → `VISUAL_PROVIDER_UNAVAILABLE` |

### Shot B — 5-2-05

| Field | Result |
|---|---|
| visible entities | 李陵、苏武、汉节、苏武穹庐 |
| candidates | 李陵 Character Master；苏武 Character Master；汉节 Prop Reference；苏武穹庐 Scene Master |
| selected suitable existing | 李陵 Character Master；苏武穹庐 Scene Master |
| missing | 苏武 Character Master（关键清晰可见人物） |
| omitted / unavailable | 汉节没有 Stable PROP Reference；它不是人物身份门禁，不用临时图填充，外观需求由 Shot Delta 保留 |
| rationale | 当前只有两项合法 Stable 候选；不为凑满 3 张补图。若苏武 Master 创建成功，则选择李陵 + 苏武 + Scene，count=3；汉节继续省略 |
| source modes | 李陵=`TRUSTED_ARTIFACT_FALLBACK`；穹庐=`TRUSTED_ARTIFACT_FALLBACK`；苏武=`UNAVAILABLE`；汉节=`UNAVAILABLE/OMITTED` |
| planned count after required resolution | 3 |
| actual Provider count | 0 |
| status | `MISSING_STABLE_REFERENCE` → `VISUAL_PROVIDER_UNAVAILABLE` |

### Shot C — 5-2-06

| Field | Result |
|---|---|
| visible entities | 李陵、苏武穹庐；苏武仅为画外关系，不是可见身份 Reference |
| candidates | 李陵 Character Master；苏武穹庐 Scene Master |
| selected | 两项均选 |
| missing | 无 |
| omitted | 无；没有 padding reference |
| rationale | 正面近景只需锁定李陵身份和 Scene/lighting；两项足够 |
| source modes | 两项均 `TRUSTED_ARTIFACT_FALLBACK` |
| planned count | 2 |
| actual Provider count | 0（串行门禁停在 Shot A 前） |
| status | Plan COMPLETE；execution NOT_RUN |

## 6. Sequence Continuity

以下 Sequence Context 只保存在 Agent Run Context，没有创建 Domain schema 或数据库记录。

### Stable / Locked Facts

- 李陵：同一中年身份、脸型、散发/短须、深色胡服与皮毛主要轮廓。
- 苏武：同一成熟身份、年龄、脸、发须和基础服装；但其稳定视觉身份必须先由缺失的 Master 提供，不能由 Shot 输出偶然决定。
- Scene：同一苏武穹庐内部、历史皮毛/木质材料和主要空间身份。
- Lighting：入夜、冷暗环境、弱火暖光、低曝光与压抑氛围。
- Props：同一只碗的身份与连续状态；同一残损汉节及旄毛的身份、归属和位置逻辑。

### Allowed Delta

姿态、视线、表情、身体方向、自然衣褶、不同景别/机位造成的背景可见量与尺度变化。它们不能被误判为 drift。

### Shot-specific Delta

- 5-2-04：苏武双手持碗只暖手不饮；李陵以前景肩/背建立过肩关系。
- 5-2-05：碗从手持转为已放在低桌，苏武双手空出；李陵扶残损汉节；构图从物件关系转到双人关系。
- 5-2-06：李陵手停在汉节上，正面近景承受画外苏武反问；不得出现王印。

### Prop State Transition

```text
5-2-04: bowl = HELD_BY_SU_WU / used_for_warmth / not drinking
    ↓ explicit narrative transition
5-2-05: bowl = ON_LOW_TABLE / Su Wu hands = FREE / Li Ling supports Han tally
    ↓ same scene, tighter reaction framing
5-2-06: bowl = remains on table or legitimately outside close framing;
        Han tally = under Li Ling's stopped hand
```

这是合法 Shot-specific Delta，不是 Continuity drift。生成输出若存在也只能作为 Review evidence，不能反向提升为 Domain Truth。

## 7. Shot Delta Compilation

### Shot A — 5-2-04（重点）

| Compiler field | Compiled constraint |
|---|---|
| source semantics | 苏武“只暖手不饮”；双人过肩组接；固定机位内拉焦 |
| Stable Identity | 李陵与苏武身份、年龄、发须、基础服装保持；苏武身份 Reference 当前缺失 |
| Stable Environment | 同一穹庐、入夜、冷暗弱火、历史材料 |
| Action State | 苏武双手包住碗壁借热度暖手，不饮用；李陵前倾观察 |
| Required Visual Evidence | 双手包住碗壁；碗口明显低于下唇；碗与嘴之间有清晰可见距离；姿态表现取暖而非饮用 |
| Forbidden Visual Outcome | 嘴唇接触碗沿；碗口遮住嘴；头部向碗做饮用动作；吞咽/喝水姿态 |
| Composition Constraint | 前景必须出现李陵肩部或局部背影；苏武为主要清晰主体；禁止完全正面并排双人构图 |
| Static Camera Intent | 不要求单图表现拉焦经过；建立清楚的前景肩背/后景主体层次与最终注意中心 |
| Continuity Constraints | 碗仍在苏武双手中；同一服装、穹庐与夜间弱火；不把可见间隙和过肩关系牺牲给美观 |

### Shot B — 5-2-05

| Compiler field | Compiled constraint |
|---|---|
| source semantics | 扶节；物件特写上摇双人近景；承接上一 Shot 的碗状态变化 |
| Action State | 李陵扶残损汉节；苏武已放下碗且双手空出 |
| Required Visual Evidence | 残损汉节及旄毛形成视觉轴；李陵手与节有明确支撑关系；碗明确位于低桌；苏武双手不再持碗；双人关系仍可读 |
| Forbidden Visual Outcome | 苏武仍持碗；碗位置含混导致仍可读成手持；汉节被替换成现代或无关物件；只剩孤立物件而失去双人关系 |
| Composition Constraint | 保留焦点物件到双人关系；静帧选择上摇代表性终点或同时成立的物件—人物关系，不伪装时间运动 |
| Static Camera Intent | 以汉节为前/下方注意锚点，人物关系为终点；不要求一张图画出上摇轨迹 |
| Continuity Constraints | bowl transition 必须成立；人物、服装、穹庐、夜间弱火锁定 |

### Shot C — 5-2-06

| Compiler field | Compiled constraint |
|---|---|
| source semantics | 反问；李陵正面近景；固定机位轻微推近 |
| Action State | 李陵手停在汉节上，目光面向画外苏武，承受“哪个朝廷”的反问 |
| Required Visual Evidence | 李陵正面近景；手与汉节关系可读；画外视线与停顿/受压反应可读 |
| Forbidden Visual Outcome | 出现王印；苏武被错误安排为同等可见主角；泛化为无叙事关系的普通肖像 |
| Composition Constraint | 李陵为单一清晰主体，画外方向稳定；背景只需保留足以识别同一穹庐和光线的信息 |
| Static Camera Intent | 采用轻推的更紧代表性终点构图，不要求单帧表现推进过程 |
| Continuity Constraints | 李陵身份、服装、Scene、Lighting 和汉节状态保持；碗可因近景不入画，不算丢失 |

上述编译在 Provider preflight 前已经完成，但因正式视觉能力缺失，没有把它们提交给 Provider。

## 8. Shot A / B / C

| Item | Shot A 5-2-04 | Shot B 5-2-05 | Shot C 5-2-06 |
|---|---|---|---|
| shotId | `shot_a9dc0ba7dfdc4e7ea2d1d479403c6274` | `shot_5559407312e04d9988591a11d3bcbf7f` | `shot_11b46c83ee77483fb01c6903cfa198c3` |
| job | NOT_RUN | NOT_RUN | NOT_RUN |
| generation count | 0 | 0 | 0 |
| actual Provider references | 0 | 0 | 0 |
| new artifact | NOT_RUN | NOT_RUN | NOT_RUN |
| Visual Content Review | NOT_RUN | NOT_RUN | NOT_RUN |
| Targeted Revise | NOT_RUN | NOT_RUN | NOT_RUN |
| Identity Annotation | NOT_RUN | NOT_RUN | NOT_RUN |
| mediaId | NOT_RUN | NOT_RUN | NOT_RUN |

没有复用 31 号报告的旧 Provider outputs 充当本批生成结果；旧 Shot B/C Stable Media 也没有被重新导入或记为 5.4 PASS。

## 9. Cross-Shot Review

正式 Cross-Shot Review 的前置条件是至少有 Per-Shot Review PASS 的本批输出。当前没有 Provider 输出，所以本节 `NOT_RUN`。

已建立但未执行的正式比较维度：Character identity、Age、Hair/Beard、Costume、Scene、Lighting、Prop continuity。执行时必须按第 6 节区分 Locked Facts、Allowed Delta 与 Shot-specific Delta；不会要求三张图完全相同。

## 10. Media Persistence

没有合格的新 Shot 输出，因此没有执行：

```text
Identity Annotation
→ media.import_media
→ media.get_media
→ media.resolve_media
→ SHA-256 equality
```

本批没有新增 `drama_media` 记录。历史 Stable Reference 的 Shared MySQL metadata 与 Trusted Artifact hash equality PASS 只证明 fallback provenance，不等同于新 Shot Media persistence。

## 11. Environment Deviations

```text
LOCAL_MEDIA_OBJECT_MISSING = 李陵 Stable Media, 苏武穹庐 Stable Media
TRUSTED_ARTIFACT_FALLBACK = PASS (两项)
VISUAL_PROVIDER_UNAVAILABLE = current Windows Host has no comfy-cloud registration
TEST_ENVIRONMENT_ONLY = YES
LONG_TERM_STORAGE = SHARED_MINIO_OR_S3
```

本批没有建设同步、复制、迁移、rehydration 或新存储架构。Local MinIO 差异不是本次阻断：即使两项 fallback 已可用，苏武 Master 的真实生成和三个 Shot 的真实生成仍需要正式 Visual Provider。

## 12. Changed Files / Source Changes

新增：

- `plugin/docs/reports/33-Batch-5.4-Skill-driven-Multi-Shot-Production-Regression-执行报告.md`
- `plugin/docs/reports/artifacts/batch5-4/drama_mcp_call.py`：本批只读/调用正式 Drama MCP 的轻量执行辅助；resolve URL 始终在脚本内部消费，报告和终端输出不记录临时 URL。

未修改：

- Drama Plugin Skill/业务源码
- Drama MCP 源码或 `.env`
- Java 源码、jar 或 `application.yml`
- 数据库 schema 或业务数据
- MinIO 配置或对象
- Codex/MCP 配置

为读取 Host MCP 注册状态，曾把官方 Codex CLI 临时复制到本批目录；检查完成后已删除，不在 Changed Files 中。

## 13. Core Questions

1. Host 只给简短业务目标时，Skill 是否实际驱动？**YES（读取、规划、门禁与编译实际由 Skill 驱动）；但完整生产是否完成：NO。**
2. 是否自主发现可见实体并规划 Reference？**YES。**
3. 是否自主发现缺失 Stable Reference？**YES，苏武。**
4. “只暖手不饮”是否由 Skill 自主编译？**YES，已产生 Required Evidence、Forbidden Outcome、Composition Constraint 与 Static Camera Intent。**
5. 连续性是否来自 Skill 而非 Host Prompt？**YES。**
6. Review / Revise 是否按 Skill 实际执行？**NO；Provider preflight 阻断，二者正确地未运行。**

因此，本批只能证明 Batch 5.3 后的 Skill-driven planning/compilation 和 fail-closed 门禁，不能证明真实在线 multi-shot production E2E。

## 14. Unified Acceptance Fields

```text
SHARED_MYSQL = PASS
CURRENT_LOCAL_MINIO = FAIL

REFERENCE_ENVIRONMENT_FALLBACK_USED = YES

CHARACTER_REFERENCE_SOURCE_MODE = TRUSTED_ARTIFACT_FALLBACK
SCENE_REFERENCE_SOURCE_MODE = TRUSTED_ARTIFACT_FALLBACK
SU_WU_REFERENCE_STATUS = MISSING

SHOT_PRODUCTION_SKILL_ACTUALLY_DRIVEN = YES
REFERENCE_PLANNING_AUTONOMOUS = YES
MISSING_REFERENCE_DISCOVERY_AUTONOMOUS = YES
SEQUENCE_CONTINUITY_SKILL_DRIVEN = YES
SHOT_DELTA_COMPILATION_ACTUALLY_USED = YES
REVIEW_REVISE_SKILL_DRIVEN = NO

REFERENCE_MAX_COUNT_COMPLIANT = PASS

SHOT_A_ACTUAL_REFERENCE_COUNT = 0
SHOT_B_ACTUAL_REFERENCE_COUNT = 0
SHOT_C_ACTUAL_REFERENCE_COUNT = 0

SHOT_A_GENERATION = NOT_RUN
SHOT_B_GENERATION = NOT_RUN
SHOT_C_GENERATION = NOT_RUN

SHOT_A_VISUAL_CONTENT_REVIEW = NOT_RUN
SHOT_B_VISUAL_CONTENT_REVIEW = NOT_RUN
SHOT_C_VISUAL_CONTENT_REVIEW = NOT_RUN

SHOT_A_GENERATION_COUNT = 0
SHOT_B_GENERATION_COUNT = 0
SHOT_C_GENERATION_COUNT = 0

SHOT_A_IDENTITY_ANNOTATION = NOT_RUN
SHOT_B_IDENTITY_ANNOTATION = NOT_RUN
SHOT_C_IDENTITY_ANNOTATION = NOT_RUN

CHARACTER_IDENTITY_CONSISTENCY = NOT_RUN
COSTUME_CONSISTENCY = NOT_RUN
SCENE_CONSISTENCY = NOT_RUN
LIGHTING_CONTINUITY = NOT_RUN
PROP_STATE_CONTINUITY = NOT_RUN
CROSS_SHOT_VISUAL_CONSISTENCY = NOT_RUN

SHOT_A_MEDIA_PERSISTENCE = NOT_RUN
SHOT_B_MEDIA_PERSISTENCE = NOT_RUN
SHOT_C_MEDIA_PERSISTENCE = NOT_RUN

CURRENT_HOST_NEW_MEDIA_BYTE_EQUALITY = NOT_RUN

MINIO_SYNC_SYSTEM_INTRODUCED = NO
MEDIA_REPLICA_SYSTEM_INTRODUCED = NO
NEW_STORAGE_ARCHITECTURE_INTRODUCED = NO

DRAMA_PLUGIN_BUSINESS_SOURCE_CHANGED = NO
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO

COMFY_OAUTH_RECOVERY_COUNT = 0
PROVIDER_GENERATION_COUNT = 0

BATCH_5_4 = BLOCKED
NEXT_BATCH_READY = NO
```

字段说明：`CURRENT_LOCAL_MINIO = FAIL` 指本批需要的两项历史 Stable object 在当前 Host 不可用；MinIO 进程健康检查本身为 PASS。`REFERENCE_ENVIRONMENT_FALLBACK_USED = YES` 指 fallback 已完成 provenance/hash 验证并进入正式 Reference Plan；由于 Provider preflight 阻断，没有 Reference 实际上传。三个 `ACTUAL_REFERENCE_COUNT = 0` 按“实际进入 Provider”口径记录。

完成边界：本批在正式 Skill 的 Visual Provider preflight 门禁停止；未进入视频、首尾帧、音频、其他 Scene、Episode 扩批或存储同步建设。
