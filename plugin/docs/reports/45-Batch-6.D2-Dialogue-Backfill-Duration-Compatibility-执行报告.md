# Batch 6.D2 — Dialogue Backfill & Duration Compatibility 执行报告

执行日期：2026-08-19（Asia/Shanghai）

性质：HOST-DRIVEN PRODUCTION DATA BACKFILL + DURATION COMPATIBILITY REVIEW

结论：**PASS**

## 1. 执行摘要

本批从当前 `drama-service` 正式 Tool Contract 重新读取 Work → Script → Episode → 6 Scenes → 27 Shots，以及当前作品 Assets/Media，再进行 Host-driven spoken-mode 判断；没有机械复制 D0 Gap Matrix。

最终 4 个 Scene 需要人物对白，2 个 Scene 保持纯视觉/沉默，不需要旁白。正式长期记忆新增 5 个 Work-scoped speaker keys、7 个 reviewed `DIALOGUE` items、7 个 canonical Shot bindings，并为全部 27 Shots 增加正整数 `plannedDurationMs`。所有 Scene/Shot 经 full-replacement save 后立即 get 回读，27/27 duration checks PASS。

没有视觉、音频、TTS、Asset 或 Media 生成。已完成 Shot 1-01/1-02 的 Media 和原生产 checkpoint/ledger 均未改变。

## 2. Artifact Root 与 Git 边界

通过当前 project root 文件系统定位，而非沿用旧报告路径：

```text
ARTIFACT_ROOT = /Users/yizhao/PyProject/historical_plugin/artifacts/batch6-0re2e
D2_ARTIFACT_DIR = /Users/yizhao/PyProject/historical_plugin/artifacts/batch6-0re2e/dialogue-backfill
ARTIFACTS_GIT_MANAGED = NO
```

Artifacts 位于三个源码 Git repository 之外。本批未执行 `git add/restore/checkout` 处理 artifacts；真实性由正式服务回读、文件存在、内容比较和 SHA-256 验证。

## 3. 当前业务事实源

正式读取对象：

- Work：`work_9cc5d11969a64f93bce4a544f349c793`；
- Script：`script_a404a8277fef45eda8ef3aaf478307cc`；
- Episode：`episode_c33021fe53ba4af08cd8b98113184dd2`；
- 6 Scenes、27 Shots；
- 当前作品 8 Assets、12 Media。

读取与写入均通过当前 `drama-service` authenticated HTTP Tool Contract；未用旧 JSON snapshot 替代长期记忆。

## 4. Host Dialogue Reasoning

判断原则是“观众必须明确理解、且视觉动作不能无歧义承担的语言行为才进入 Dialogue”。结果：

- Scene 1：王思礼的具体建议与哥舒翰拒绝决定人物权力归属，必须说出；
- Scene 2：杨国忠的判断、唐玄宗的最终命令、哥舒翰的军事异议必须分属不同 speaker；
- Scene 3：只保留哥舒翰催前军推进的短令，地形与敌军诱敌继续由视觉表达；
- Scene 4：木石、毡车、火烟、误射与后袭完全依靠动作；战场呼号属于未来 SFX；
- Scene 5：溃散、壕沟、残部入关与关旗坠落已完整表达结果，不加解释性对白；
- Scene 6：火拔归仁以敌至为由迫主帅上马是不可替代的欺骗行动；被缚与长安后果保持视觉。

没有为环境、战斗或地理转场添加旁白，也没有因为 Dialogue Layer 存在而增加无功能台词。

## 5. Scene Backfill Matrix

| Scene ID | Order / title | Mode | Items D/N | Speaker keys | Provenance | Spoken ms | Review / persistence |
|---|---|---|---:|---|---|---:|---|
| `scene_3ad95aa042e647d9a9be05a51dd8a009` | 1 关门未开 | DIALOGUE | 2 / 0 | `speaker:wangsili`, `speaker:geshuhan` | ADAPTED ×2 | 8,200 | PASS / durable round-trip |
| `scene_8275463717ab408db6164960d7291b0b` | 2 项背诏使 | DIALOGUE | 3 / 0 | `speaker:yangguozhong`, `speaker:tangxuanzong`, `speaker:geshuhan` | ADAPTED ×3 | 15,700 | PASS / durable round-trip |
| `scene_b511326f3687480893dd11f1cff64e80` | 3 七十里隘道 | DIALOGUE | 1 / 0 | `speaker:geshuhan` | ADAPTED ×1 | 2,800 | PASS / durable round-trip |
| `scene_3378a2d6482043d883596f66a8745d61` | 4 烟火断军 | SILENT | 0 / 0 | — | — | 0 | PASS / durable round-trip |
| `scene_07276a4f20dd4761a23da62dc392c321` | 5 关门易手 | SILENT | 0 / 0 | — | — | 0 | PASS / durable round-trip |
| `scene_8b735bc438de45259833d9725e1e66c6` | 6 平安火不至 | DIALOGUE | 1 / 0 | `speaker:huobaguiren` | ADAPTED ×1 | 3,000 | PASS / durable round-trip |

## 6. Dialogue Review 结果

7 个 item 均具有 canonical `id/kind/speakerKey/text/intent/mustKeep/performanceIntent/provenance/estimatedDurationMs`。正文完成了建议、拒绝、推动、下令、申辩、催进、诱骗等当前戏剧行动；没有把 speech-act 摘要当正文。

语言保持可懂、简洁、符合权力关系；没有现代网络语、管理术语、百科讲解或堆砌文言。事实归属保持：王思礼只建议，唐玄宗下最终命令，杨国忠推动，哥舒翰判断并执行，火拔归仁实施欺骗与控制。

## 7. Speaker Matrix

| Display name | speakerKey | Status | Visual Asset exists | Asset required for Dialogue |
|---|---|---|---:|---:|
| 哥舒翰 | `speaker:geshuhan` | BACKFILLED | YES | NO |
| 唐玄宗 | `speaker:tangxuanzong` | BACKFILLED | YES | NO |
| 杨国忠 | `speaker:yangguozhong` | BACKFILLED | YES | NO |
| 王思礼 | `speaker:wangsili` | BACKFILLED | NO | NO |
| 火拔归仁 | `speaker:huobaguiren` | BACKFILLED | YES | NO |

没有为不发言的崔乾祐或其他人物无脑增加 key，也没有创建 narrator identity。

## 8. Historical Provenance Matrix

| Relation | Count | Review |
|---|---:|---|
| DIRECT_QUOTE | 0 | 无逐字证据，因此不作原话声明 |
| ADAPTED | 7 | PASS；每项有 spine/source refs 与 adaptationNote |
| DRAMATIZED | 0 | 不需要以无来源戏剧化台词填充 |
| FUNCTIONAL | 0 | 所有保留台词都直接承载有史料依据的 speech act |

当前 Work 提供人物行为、建议、命令与判断的来源定位，但没有可核对的 exact excerpt。故全部 wording 明确标为 `ADAPTED`，没有把一般 evidenceRef 升级为 `DIRECT_QUOTE`。

```text
DIRECT_QUOTE_EVIDENCE_GATE_PASS = 0
DIRECT_QUOTE_EVIDENCE_GATE_FAIL = 0
HISTORICAL_PROVENANCE_REVIEW = PASS
```

## 9. Spoken Item ID Stability

首次 backfill 使用语义化、Scene 内唯一 ID，例如 `spoken-s1-wangsili-proposal`，不使用自然数组位置。每个 ID 经 save/get 保持；没有在 Review wording 调整后重生 ID。全部 7 个 item 都恰好被一个 Shot coverage binding 引用，无 dangling 或重复正文。

## 10. Shot Binding Matrix

| Shot ID | No. | spokenContentIds / coverage | planned ms | Duration | Visual status |
|---|---|---|---:|---|---|
| `shot_dbdd2e45a8d34c26836c371f6e5f8b4f` | 1-01 | — | 5,000 | PASS | DURABLE PASS video |
| `shot_0d5835773da94201ae2f3c9e9c075fd1` | 1-02 | — | 5,000 | PASS | DURABLE PASS video |
| `shot_83db7eb53b2f49d3a58428d4659e584e` | 1-03 | `spoken-s1-wangsili-proposal` ON_SCREEN; `spoken-s1-geshuhan-refusal` ON_SCREEN | 10,500 | PASS | not generated |
| `shot_976935b56e9d4a4f84a01f6c38d697e5` | 1-04 | — | 5,500 | PASS | not generated |
| `shot_3c3b162e7d5b4097abd18af7fc51b5d4` | 2-01 | `spoken-s2-yangguozhong-urge` ON_SCREEN | 6,000 | PASS | not generated |
| `shot_8c2267a998c04898b18f859bc0da1110` | 2-02 | `spoken-s2-xuanzong-order` ON_SCREEN | 6,500 | PASS | not generated |
| `shot_610f08d03405453e83e99b48e135afc9` | 2-03 | `spoken-s2-geshuhan-defense` ON_SCREEN | 9,500 | PASS | not generated |
| `shot_7f61b162d85249fea465f3b55a7b89e4` | 2-04 | — | 6,000 | PASS | not generated |
| `shot_260cf036eef549f284acc1f41f334f47` | 2-05 | — | 5,500 | PASS | not generated |
| `shot_bed8f63ef7874fbd9d5b5807e272b06d` | 3-01 | — | 5,500 | PASS | not generated |
| `shot_16acbe807a3f40fab816d57039fed8fa` | 3-02 | — | 6,500 | PASS | not generated |
| `shot_14cd3406eb8a4e0e851ab5f5a6af3097` | 3-03 | — | 6,000 | PASS | not generated |
| `shot_419af9cb3a1c4868bca59ce983c19310` | 3-04 | `spoken-s3-geshuhan-advance` ON_SCREEN | 6,000 | PASS | not generated |
| `shot_97915a0b5fb242878b3dce8e3747850b` | 4-01 | — | 5,500 | PASS | not generated |
| `shot_b4099076e078424d90d8e1c22d540115` | 4-02 | — | 5,500 | PASS | not generated |
| `shot_05f407a51a984c849544584aa1e1292e` | 4-03 | — | 6,000 | PASS | not generated |
| `shot_69860023db424b4db23ab40bd0a4d9f1` | 4-04 | — | 5,500 | PASS | not generated |
| `shot_6f49453a246d4249a3723b8834f8bdd4` | 4-05 | — | 6,000 | PASS | not generated |
| `shot_ae2bcaca83ce4942b7f4d1eb4657091f` | 4-06 | — | 6,000 | PASS | not generated |
| `shot_79e58b2909f1458b87177e48319f2507` | 5-01 | — | 5,500 | PASS | not generated |
| `shot_0a0903ed7462454498f6ea4855bdfe0e` | 5-02 | — | 6,000 | PASS | not generated |
| `shot_4df48f47871b476183b8eb8c1e3ed24f` | 5-03 | — | 5,500 | PASS | not generated |
| `shot_aa14db6c62c54db991d62e30bf0903e7` | 5-04 | — | 6,000 | PASS | not generated |
| `shot_97f0cb50f62845a1a67786f5cf4935ff` | 6-01 | — | 5,500 | PASS | not generated |
| `shot_d9c2b11097e742a7994558b5d3df975c` | 6-02 | `spoken-s6-huobaguiren-pretext` ON_SCREEN | 6,000 | PASS | not generated |
| `shot_ea2dc98b5f6045a9a5167df178199a4b` | 6-03 | — | 5,500 | PASS | not generated |
| `shot_80ffcd5d57c84beeb11413d9f5488850` | 6-04 | — | 7,000 | PASS | not generated |

Bindings 只含 `spokenContentId` 与 `coverageIntent`，没有 copied text、audio timing、subtitle、voice 或 parallel alias。当前既有 Shot topology 足以承载正文，因此没有 create/delete/renumber Shot。

## 11. Duration Matrix — Spoken Shots

| Shot/group | Spoken estimate ms | Planned ms | Headroom ms | Arithmetic | Playable-room review |
|---|---:|---:|---:|---|---|
| 1-03 | 8,200 | 10,500 | 2,300 | PASS | 两人提议/拒绝及停顿可表演 |
| 2-01 | 4,100 | 6,000 | 1,900 | PASS | 展军报与施压有空间 |
| 2-02 | 4,400 | 6,500 | 2,100 | PASS | 决令与反应有空间 |
| 2-03 | 7,200 | 9,500 | 2,300 | PASS | 指图、陈说与停顿有空间 |
| 3-04 | 2,800 | 6,000 | 3,200 | PASS | 发令、推进、偃旗可完成 |
| 6-02 | 3,000 | 6,000 | 3,000 | PASS | 围驿、借口与控制动作可完成 |

其余 21 Shots 没有 spoken load，但仍按动作、地理、反应、停顿和节奏设置 5,000–7,000 ms；没有无脑统一为 5,000。全片 numeric planning 合计 165,000 ms，落在 Script/Work 已批准 165–225 秒范围下界。

```text
DURATION_PASS_COUNT = 27
DURATION_FAIL_COUNT = 0
DURATION_FEASIBILITY_REVIEW = PASS
```

## 12. Existing Visual Reuse Matrix

| Shot | Current final Media | Dialogue impact | Duration impact | Result |
|---|---|---|---|---|
| 1-01 | `media_8c2a03f8e3fd431ca2598821eb4ddb09` | Scene 中保持无对白 | `plannedDurationMs=5000` 来自原 provider plan，不冒充 5.041667s actual | SAFE_TO_REUSE |
| 1-02 | `media_b11d88f165bd4d8d9cb1bc164b92c6bc` | Scene 中保持无对白 | `plannedDurationMs=5000` 来自原 provider plan，不冒充 5.083333s actual | SAFE_TO_REUSE |

Media final read 与 D2 前当前作品 Media snapshot 完全相同。

```text
EXISTING_VISUAL_SAFE_TO_REUSE_COUNT = 2
EXISTING_VISUAL_AUDIO_ONLY_COUNT = 0
EXISTING_VISUAL_REVISION_CANDIDATE_COUNT = 0
COMPLETED_VISUAL_REUSE = PASS
```

## 13. Future Visual Asset Gap

| Entity | Why identity may be required | Existing reusable Asset | Future resolution | Blocks Dialogue |
|---|---|---:|---:|---:|
| 王思礼 | Shot 1-03 中可见的共同说话者 | NO | YES | NO |

这与 R2 checkpoint 的 `MISSING_STABLE_REFERENCE_REF_WANGSILI` 一致，但结论来自当前 Assets/Shot/Dialogue 联合回读。D2 没有创建 Asset/Media 或调用 Provider。

## 14. Visual Workflow 与 Shot Topology

```text
VISUAL_ASSET_RESOLUTION_REQUIRED = YES
VISUAL_WORKFLOW_REPLAN_REQUIRED = YES
SHOT_TOPOLOGY_REPLAN_REQUIRED = NO
```

旧 pre-spend plan 的固定 5 秒不能覆盖部分新的 creative requirements，尤其 1-03 的 10,500 ms 与 2-03 的 9,500 ms。D2 没有为旧 provider workflow 反向压缩正式台词。后续 Resume 应选择支持计划时长的 workflow/coverage；现有 27-Shot topology 无需重建。

## 15. Full Replacement Safety

每个实体均执行：latest get → copy full content → merge canonical D2 fields → save full content → immediate get → compare unrelated content。

- Work：仅 5 个 `historicalActorHierarchy[].speakerKey` 改变；其他内容及 envelope 相同；
- 6 Scenes：仅 `content.spokenContent` 改变；objective/opposition/stakes/tactics/beats/spine/continuity 等保持；
- 27 Shots：仅 `content.spokenContentBindings` 与 `content.plannedDurationMs` 改变；subject/action/framing/camera/composition/continuity/transition 等保持；
- 读回未发现字段丢失、alias、dangling binding 或 Shot-local spoken body。

正式 Tool Contract 不暴露 version，故没有伪造 version before/after；artifact 明确记录 `NOT_EXPOSED_BY_TOOL_CONTRACT`，并保存每个实体 unrelated-content before/after canonical SHA-256，两侧逐项相等。

```text
FULL_REPLACEMENT_SAFETY = PASS
LONG_TERM_MEMORY_ROUND_TRIP = PASS
```

## 16. Production Freeze

R2 文件在 D2 前后哈希保持：

```text
r2-production-checkpoint.json = b41d7834fb04c4c13355c7d81afe72a770590651093b0c28d75d1b62a9f683a7
r2-credit-ledger.json          = 98d3095b8da65b40160e271b30acd5ccddf85c16709cc91cc069a8723f4430d3
```

没有改变 `lastCompletedNode`、paid jobs、accounted usage 603、remaining batch budget 1392、production files 或 MinIO/Media。独立 D2 checkpoint 记录 backfill，不篡改视觉生产历史。

## 17. D2 Artifacts

非 Git D2 目录包含：

- `dialogue-backfill-analysis.json`
- `dialogue-backfill-checkpoint.json`
- `speaker-key-backfill.json`
- `scene-spoken-content-matrix.json`
- `shot-spoken-binding-matrix.json`
- `duration-feasibility-matrix.json`
- `historical-provenance-matrix.json`
- `visual-reuse-assessment.json`
- `full-replacement-safety.json`

全部 9 个 JSON 已通过解析；checkpoint 最终状态为 `PASS`，`nextNode=STOP_AWAIT_EXPLICIT_6_0R_RESUME`。

## 18. Code / Convention / Schema 变更

```text
CODE_CHANGED = NO
DIALOGUE_CONVENTION_CHANGED = NO
PLUGIN_CONTRACT_CHANGED = NO
TOOL_CHANGED = NO
MCP_CHANGED = NO
DATABASE_CHANGED = NO
```

D2 只新增本执行报告和非 Git runtime artifacts；没有修改 Skill、Convention、Java、Python production code、Tool、MCP 或数据库 schema。Workspace 中原有未提交 Media recovery/D1 修改保持原状，不归属于 D2。

## 19. 计数信息

```text
TOTAL_SCENES_ANALYZED = 6
TOTAL_SHOTS_ANALYZED = 27

SILENT_SCENE_COUNT = 2
DIALOGUE_SCENE_COUNT = 4
NARRATION_SCENE_COUNT = 0
MIXED_SCENE_COUNT = 0

SPOKEN_ITEM_COUNT = 7
DIALOGUE_ITEM_COUNT = 7
NARRATION_ITEM_COUNT = 0

SPEAKER_KEY_EXISTING_COUNT = 0
SPEAKER_KEY_BACKFILLED_COUNT = 5

DIRECT_QUOTE_COUNT = 0
ADAPTED_COUNT = 7
DRAMATIZED_COUNT = 0
FUNCTIONAL_COUNT = 0

SHOT_BINDING_COUNT = 7

DURATION_PASS_COUNT = 27
DURATION_FAIL_COUNT = 0

EXISTING_VISUAL_SAFE_TO_REUSE_COUNT = 2
EXISTING_VISUAL_AUDIO_ONLY_COUNT = 0
EXISTING_VISUAL_REVISION_CANDIDATE_COUNT = 0

FUTURE_VISUAL_ASSET_GAP_COUNT = 1
```

## 20. Resume Readiness

Dialogue Layer 已完整、所有 Scene mode 已审查、全部 spoken items/provenance/IDs/bindings 可消费、27 Shots numeric duration 完成且无 unresolved conflict。王思礼 Asset 缺口和 variable-duration visual workflow 选择属于后续正常 Resume production planning，不是 D2 Dialogue blocker。

```text
BATCH_6_0R_RESUME_READY = YES
```

## 21. 最终关键判定

```text
BATCH_6_D2 = PASS

HOST_DIALOGUE_REASONING = PASS
WORK_SPEAKER_BACKFILL = PASS

SCENE_SPOKEN_CONTENT_BACKFILL = PASS
SHOT_SPOKEN_BINDING_BACKFILL = PASS

HISTORICAL_PROVENANCE_REVIEW = PASS
DURATION_FEASIBILITY_REVIEW = PASS

FULL_REPLACEMENT_SAFETY = PASS
LONG_TERM_MEMORY_ROUND_TRIP = PASS

COMPLETED_VISUAL_REUSE = PASS

VISUAL_ASSET_RESOLUTION_REQUIRED = YES
VISUAL_WORKFLOW_REPLAN_REQUIRED = YES
SHOT_TOPOLOGY_REPLAN_REQUIRED = NO

ARTIFACTS_GIT_MANAGED = NO

CODE_CHANGED = NO
PRODUCTION_DATA_CHANGED = YES
PRODUCTION_CHECKPOINT_CHANGED = NO
CREDIT_LEDGER_CHANGED = NO

COMFY_PAID_GENERATION = 0
IMAGE_GENERATION = 0
VIDEO_GENERATION = 0
AUDIO_GENERATION = 0
TTS_GENERATION = 0
CREDIT_CONSUMPTION = 0

BATCH_6_0R_RESUME_READY = YES
```

**STOP：未自动 Resume 6.0R-E2E，未进入 Batch 7 或 Audio Production。**
