# Batch 5.2R — Comfy Cloud OAuth Stabilization & 5.2 Resume

## 1. Executive Summary

本批先修复 Comfy Cloud MCP 的 OAuth 状态，再从 Batch 5.2 的 Provider preflight 断点继续。初始只读调用真实返回 `invalid_grant: refresh token reuse detected`；执行一次官方 `codex mcp login comfy-cloud` 后，连续三次串行 `get_server_info` 均通过，之后全部上传、生成、等待和输出获取也保持串行，未再次出现 token reuse。

两个既有标准 Reference 均从 Drama stable Media resolve 为真实字节并完成 hash 复核，随后被 Provider 实际接收并作为每个 Shot 的同一组 2 references 使用。三个真实 Shot 均完成生成、输出下载和图片解码：Shot A 在首次与唯一一次 revise 后仍把碗贴近嘴部，不满足“只暖手不饮”，Visual Content Review 为 FAIL；Shot B 在一次 revise 后 PASS；Shot C 首次 PASS。

按质量门禁，仅 Shot B/C 生成身份标注 derivative 并进入正式 Drama Media。两者均通过 `get → resolve → download → SHA-256`，正式 MinIO 回读与本地标注图字节一致。由于三张图没有全部通过单图审核，Cross-Shot 正式验收未启动；结果为 `BATCH_5_2R = PARTIAL`，已通过的 Shot 被保留。

## 2. Previous Blocker

初始 `comfy-cloud/get_server_info` 返回：

```text
invalid_grant: refresh token reuse detected
OAuth authorization required
```

未读取、复制或输出 Token、Authorization Code、Cookie、API Key 或 OAuth 凭据文件。

## 3. Codex / MCP Client State

- OS：macOS Darwin 25.5.0 arm64
- Codex：`codex-cli 0.148.0-alpha.9`
- Comfy MCP：`comfy-cloud`，Streamable HTTP，`https://cloud.comfy.org/mcp`，enabled
- Codex App：运行中
- 进程快照：一个 App 集成 Codex host；另见 2 个由 App/tool runtime 派生的 `codex` 子进程
- 这些子进程不足以证明存在独立用户会话或独立凭据消费者，因此 `OTHER_CODEX_SESSION_DETECTED = UNKNOWN`
- 多个潜在 MCP/OAuth 消费者同时存在的可能性不能排除，因此 `POTENTIAL_OAUTH_CONCURRENCY = YES`
- 未终止任何不明进程，未修改 Codex config

## 4. OAuth Recovery

| Item | Evidence | Result |
|---|---|---|
| Initial server info | `invalid_grant: refresh token reuse detected` | FAIL |
| Logout | 未执行 | NO |
| Login | 执行一次 `codex mcp login comfy-cloud` | YES |
| Browser authorization | 既有浏览器登录态完成授权；未要求用户粘贴任何凭据 | PASS |
| CLI result | `Successfully logged in to MCP server 'comfy-cloud'.` | PASS |
| Recovery count | 1，未循环 login/retry | COMPLIANT |

## 5. OAuth Stability Validation

| Call | Tool | Mode | Result |
|---|---|---|---|
| 1 | `get_server_info` | serial | PASS — production / 0.39.1 / authenticated |
| 2 | `get_server_info` | serial | PASS — production / 0.39.1 / authenticated |
| 3 | `get_server_info` | serial | PASS — production / 0.39.1 / authenticated |

后续生产期间未再次发生 OAuth refresh token reuse。Comfy Cloud MCP 报告可用工具数为 40。

## 6. Root Cause Assessment

```text
ROOT_CAUSE = UNKNOWN_OAUTH_ROTATION_CONFLICT
POTENTIAL_MULTI_CLIENT_FACTOR = POSSIBLE_NOT_PROVEN
```

证据只证明初始 refresh token 已因 reuse 被拒绝，以及一次官方重新登录后串行调用持续稳定。进程快照中存在 App host 与派生子进程，但无法证明某个独立客户端实际竞争刷新同一凭据，因此不能提升为 `MULTI_CLIENT_REFRESH_RACE`、`STALE_CLIENT_CREDENTIAL` 或其他确定结论。

## 7. Stable Reference Resume

| Reference | Stable Asset | Stable Media | Resolved SHA-256 | Provider handoff |
|---|---|---|---|---|
| 李陵 Character Master | `asset_df44cfb7db1646f2a7b7eae2463a032e` | `media_fe9dae51b9a74c8ea4819784eca27154` | `742bd90ef8d5da24be3c1037b386079fe3d8d6cb6869b5b5d5a81c9b41bfa51d` | ACCEPTED / USED |
| 苏武穹庐 Scene Master | `asset_c13dbef904f04c63bc48de0a8505be66` | `media_ec444a5cf36040bcb96b2b12b8a6ea6e` | `5e0eddccf35284a98ba79087abed64ceb539614aab308138fa151f45f0b8eb71` | ACCEPTED / USED |

两个 Reference 均由 Drama stable Media resolve 得到真实 PNG 字节，不是旧 Cloud filename、临时 PoC 图或无 mediaId 文件。两个实际上传结果被同一 Provider template family 接收，并在 A/B/C 每个 job 中以相同顺序绑定；实际 reference count 均为 2。未重新生成、重标或修改 Standard Reference。

共同执行策略：Comfy Cloud / 官方 `image_qwen_image_edit_2511` template family / 两个 stable references。模板由当前 provider capability 与 verified implementation 自主选择；未创建 Custom、Saved 或 Dynamic Workflow。

真实领域范围：

- Work：`work_4cf81e8862234727b082cf2115ec699b`
- Script：`script_5f16ca3b7a3b4b2e80b2f2711e37b2ce`
- Episode：`episode_3a900d6a26b246889970af5b7f5a1475`
- Scene：`scene_399ace55923e47be8092eb808d7d284c`

## 8. Shot A — 5-2-04 只暖手不饮

- shotId：`shot_a9dc0ba7dfdc4e7ea2d1d479403c6274`
- shotType：双人过肩组接
- Production instruction：从李陵肩后观察苏武，苏武双手捧碗停在唇下、只借热气暖手而不饮；穹庐夜景、弱火、冷暗连续。
- References：Character Master + Scene Master，actual count = 2
- Provider/template：Comfy Cloud / `image_qwen_image_edit_2511`
- v1 job：`6d0aa501-df72-456d-bd49-e00f1e731b5b`
- v1 artifact：`shot-5-2-04-provider-v1.png`，1,029,420 bytes，SHA-256 `9525cf804f5918e5f5c14ec7cb0ac794903ea68b2e59405e75eb95ebb2b94133`
- v1 review：FAIL。碗口贴近嘴部，普通观众会读成饮用动作。
- Revise：仅一次；强化“碗与嘴之间必须有明显可见间隙、不得触唇”，保持相同 References 与策略。
- v2 job：`11fbeb62-5346-4da8-8782-ae9bc8483951`
- v2 artifact：`shot-5-2-04-provider-v2.png`，1,124,322 bytes，SHA-256 `22b602b78a049fe4f8bbdc63a91a3476f9e472ba50bd2cf92d986ebf0f2ed348`
- v2 review：FAIL。碗仍位于嘴边，且构图由预期过肩组接漂移为正面双人画面。
- Generation count：2，已达到上限；未继续抽卡。
- Identity annotation / Media import：NOT_RUN。失败图未进入长期记忆。

## 9. Shot B — 5-2-05 扶节

- shotId：`shot_5559407312e04d9988591a11d3bcbf7f`
- shotType：物件特写上摇双人近景
- Production instruction：残损汉节与旄毛作为视觉轴，李陵扶节，苏武已经把碗放下；保持人物服装、穹庐和夜间弱火连续。
- References：Character Master + Scene Master，actual count = 2
- Provider/template：Comfy Cloud / `image_qwen_image_edit_2511`
- v1 job：`07992984-553b-477a-b879-97da513d23bb`
- v1 artifact：`shot-5-2-05-provider-v1.png`，1,145,611 bytes，SHA-256 `a6e6ea548e06c15f85ea2c2f29017532ddfa547815b3da609431fc75facf299e`
- v1 review：FAIL。苏武仍手持碗，不符合“放下碗”。
- Revise：仅一次；要求碗明确落在低桌、苏武双手空出，保持相同 References 与策略。
- v2 job：`8dedd69a-1476-401b-b5f7-5d01121d5280`
- v2/final provider artifact：`shot-5-2-05-provider-v2.png`，1,189,587 bytes，SHA-256 `f9771dc16362686abed8c41a741c25611fd2ec0add76727fc139caef4cb16f22`
- Final review：PASS。碗明确位于桌面，苏武不再持碗；李陵扶残损汉节，双人关系、手部、历史材质、穹庐与光线可接受。
- Generation count：2
- Annotated derivative：`shot-5-2-05-reference.png`，1,128,866 bytes，SHA-256 `3b42338311eb832e3867a553d95cb03d46f56b58d7ac46791d49690664aa3f94`
- Annotation：左上角 `镜头：5-2-05`；未遮挡脸、手、汉节或碗，标注外像素保持不变。
- Final mediaId：`media_85a54029381e43cab20579d30cd34f4b`
- purpose：`SHOT_KEY_IMAGE`
- Formal resolve：1,128,866 bytes；SHA-256 与 annotated derivative 相同，PASS

## 10. Shot C — 5-2-06 反问

- shotId：`shot_11b46c83ee77483fb01c6903cfa198c3`
- shotType：李陵正面近景
- Production instruction：李陵手停在汉节上，正面近景中看向画外苏武并承受反问；不出现王印，保持同一服装、穹庐和夜间火光。
- References：Character Master + Scene Master，actual count = 2
- Provider/template：Comfy Cloud / `image_qwen_image_edit_2511`
- job：`a67aad60-8908-4f4e-8c11-3ddc6dd4d9b4`
- Provider artifact：`shot-5-2-06-provider.png`，989,941 bytes，SHA-256 `2ffaaf6aa98ea2f6e95f8b3f25ea4031725a673e36a3848d818ce72fe0b654e9`
- Review：PASS。李陵正面近景、画外视线、手停汉节、无王印；脸型、发须、深色皮毛服装、穹庐材质与弱火基调可接受，未见阻断性解剖错误。
- Generation count：1；未 revise。
- Annotated derivative：`shot-5-2-06-reference.png`，936,496 bytes，SHA-256 `662edff24e49fffd40256d1f4300b32124da956c07883b112e6c4bb6099137f2`
- Annotation：左上角 `镜头：5-2-06`；未遮挡脸、手或汉节，标注外像素保持不变。
- Final mediaId：`media_99a5660918264db5b6b3e2e49f8e9ec8`
- purpose：`SHOT_KEY_IMAGE`
- Formal resolve：936,496 bytes；SHA-256 与 annotated derivative 相同，PASS

## 11. Cross-Shot Review

本批严格门禁要求 A/B/C 三张单图先全部通过 Visual Content Review。Shot A 在允许的一次 revise 后仍 FAIL，因此未启动正式 Cross-Shot Consistency 验收，不能用 B/C 的局部观察替代三图结论。

| Dimension | Shot A | Shot B | Shot C | Consistency |
|---|---|---|---|---|
| Character identity | 单图语义 FAIL；候选构图亦有漂移 | 李陵身份可接受 | 李陵身份可接受 | NOT_RUN |
| Age | 未进入三图验收 | 成熟中年 | 成熟中年 | NOT_RUN |
| Hair / Beard | 未进入三图验收 | 散发、短须 | 散发、短须 | NOT_RUN |
| Costume | 未进入三图验收 | 深色胡服、皮毛 | 深色胡服、皮毛 | NOT_RUN |
| Scene | 未进入三图验收 | 同一冷暗穹庐语义 | 同一冷暗穹庐语义 | NOT_RUN |
| Lighting | 未进入三图验收 | 冷暗环境 + 弱火暖光 | 冷暗环境 + 弱火暖光 | NOT_RUN |

观察性结论：B/C 的李陵身份、发须、皮毛服装、穹庐与弱火基调具有较好连续性；该观察不构成三 Shot 正式 PASS。

## 12. Identity Annotation

仅对 Visual Content Review PASS 的 Shot 生成 derivative：

| Shot | Provider output preserved | Derivative | Validation |
|---|---|---|---|
| A | v1/v2 均保留 | NOT_RUN | Visual review gate failed |
| B | `shot-5-2-05-provider-v2.png` | `shot-5-2-05-reference.png` | PASS |
| C | `shot-5-2-06-provider.png` | `shot-5-2-06-reference.png` | PASS |

复用了既有确定性脚本，并做极小 CLI 参数化，使其可显式接收 input/output/label；没有把标签烧录进 Provider 原图，也没有改写被拒绝版本。

## 13. Media Persistence

首次以裸本地路径调用 `media.import_media` 被真实 contract 拒绝，未产生 mediaId；按既有 contract 改用标准 `file://` URI 后成功。未修改 Tool、Java、MCP 或存储配置。

| Shot | Import | Stable mediaId | get metadata | Formal resolve | Byte equality |
|---|---|---|---|---|---|
| A | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| B | PASS | `media_85a54029381e43cab20579d30cd34f4b` | shotId/purpose/content PASS | PASS | PASS |
| C | PASS | `media_99a5660918264db5b6b3e2e49f8e9ec8` | shotId/purpose/content PASS | PASS | PASS |

两项正式 Media 的 `sourceRef` 均为 `storage:` 稳定引用；报告未记录任何预签名 URL。B/C 的 content 仅包含 shot 语义、review、annotation、reference count、stable Asset IDs 与本地完整性信息，不包含 Provider 临时文件名或凭据。

## 14. Changed Files

- `plugin/docs/reports/31-Batch-5.2R-Comfy-Cloud-OAuth-Stabilization-and-5.2-Resume-执行报告.md`
- `plugin/docs/reports/artifacts/batch5-2/shot-5-2-04-provider-v1.png`
- `plugin/docs/reports/artifacts/batch5-2/shot-5-2-04-provider-v2.png`
- `plugin/docs/reports/artifacts/batch5-2/shot-5-2-05-provider-v1.png`
- `plugin/docs/reports/artifacts/batch5-2/shot-5-2-05-provider-v2.png`
- `plugin/docs/reports/artifacts/batch5-2/shot-5-2-05-reference.png`
- `plugin/docs/reports/artifacts/batch5-2/shot-5-2-06-provider.png`
- `plugin/docs/reports/artifacts/batch5-2/shot-5-2-06-reference.png`
- `plugin/docs/reports/artifacts/batch5-1rr/annotate_references.py`（仅增加可选 CLI 参数）

另新增 2 条正式 Drama Media 领域记录（Shot B/C），不对应仓库文件。既有 30 号报告未覆盖或修改。

## 15. Source Changes

```text
DRAMA_PLUGIN_SOURCE_CHANGED = NO
HISTORICAL_SKILL_CHANGED = NO
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO
COMFY_WORKFLOW_CHANGED = NO
CODEX_CONFIG_CHANGED = NO
SECRET_EXPOSURE = NO
```

标注脚本位于测试/报告 artifacts，属于允许的执行辅助文件，不是 Drama Plugin 业务源码。

## 16. Unified Acceptance Fields

```text
COMFY_CLOUD_MCP_REGISTERED = PASS
COMFY_CLOUD_AUTH_INITIAL = FAIL

POTENTIAL_OAUTH_CONCURRENCY = YES
CODEX_APP_RUNNING = YES
CODEX_CLI_PROCESS_COUNT = 2
OTHER_CODEX_SESSION_DETECTED = UNKNOWN

OAUTH_RECOVERY_PERFORMED = YES
OAUTH_LOGOUT_PERFORMED = NO
OAUTH_LOGIN_PERFORMED = YES

COMFY_OAUTH_SERIAL_CALL_1 = PASS
COMFY_OAUTH_SERIAL_CALL_2 = PASS
COMFY_OAUTH_SERIAL_CALL_3 = PASS

COMFY_OAUTH_STABLE = YES
OAUTH_REUSE_RECURRED_AFTER_RECOVERY = NO

OAUTH_ROOT_CAUSE = UNKNOWN_OAUTH_ROTATION_CONFLICT

FORMAL_OBJECT_STORAGE = PASS
STABLE_CHARACTER_REFERENCE = PASS
STABLE_SCENE_REFERENCE = PASS

REFERENCE_REUSE_READY = YES
REFERENCE_REUSE_ACTUALLY_USED = YES

SHOT_A_PLANNED_REFERENCE_COUNT = 2
SHOT_B_PLANNED_REFERENCE_COUNT = 2
SHOT_C_PLANNED_REFERENCE_COUNT = 2

SHOT_A_ACTUAL_REFERENCE_COUNT = 2
SHOT_B_ACTUAL_REFERENCE_COUNT = 2
SHOT_C_ACTUAL_REFERENCE_COUNT = 2

SHOT_COUNT = 3

SHOT_A_GENERATION_COUNT = 2
SHOT_B_GENERATION_COUNT = 2
SHOT_C_GENERATION_COUNT = 1

SHOT_A_GENERATION = PASS
SHOT_B_GENERATION = PASS
SHOT_C_GENERATION = PASS

SHOT_A_OUTPUT_FETCH = PASS
SHOT_B_OUTPUT_FETCH = PASS
SHOT_C_OUTPUT_FETCH = PASS

SHOT_A_FILE_DECODE = PASS
SHOT_B_FILE_DECODE = PASS
SHOT_C_FILE_DECODE = PASS

SHOT_A_VISUAL_CONTENT_REVIEW = FAIL
SHOT_B_VISUAL_CONTENT_REVIEW = PASS
SHOT_C_VISUAL_CONTENT_REVIEW = PASS

SHOT_A_IDENTITY_ANNOTATION = NOT_RUN
SHOT_B_IDENTITY_ANNOTATION = PASS
SHOT_C_IDENTITY_ANNOTATION = PASS

CHARACTER_IDENTITY_CONSISTENCY = NOT_RUN
AGE_CONSISTENCY = NOT_RUN
HAIR_BEARD_CONSISTENCY = NOT_RUN
COSTUME_CONSISTENCY = NOT_RUN
SCENE_CONSISTENCY = NOT_RUN
LIGHTING_CONTINUITY = NOT_RUN

CROSS_SHOT_VISUAL_CONSISTENCY = NOT_RUN

SHOT_A_MEDIA_IMPORT = NOT_RUN
SHOT_B_MEDIA_IMPORT = PASS
SHOT_C_MEDIA_IMPORT = PASS

SHOT_A_MEDIA_RESOLVE = NOT_RUN
SHOT_B_MEDIA_RESOLVE = PASS
SHOT_C_MEDIA_RESOLVE = PASS

SHOT_A_MEDIA_BYTE_EQUALITY = NOT_RUN
SHOT_B_MEDIA_BYTE_EQUALITY = PASS
SHOT_C_MEDIA_BYTE_EQUALITY = PASS

SHOT_MEDIA_PERSISTENCE = PARTIAL

STANDARD_REFERENCE_REGENERATION = NO
NEW_CHARACTER_MASTER_CREATED = NO
NEW_SCENE_MASTER_CREATED = NO

NEW_CUSTOM_WORKFLOW_CREATED = NO
NEW_SAVED_WORKFLOW_CREATED = NO
DYNAMIC_WORKFLOW_INTRODUCED = NO

DRAMA_PLUGIN_SOURCE_CHANGED = NO
HISTORICAL_SKILL_CHANGED = NO
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO
COMFY_WORKFLOW_CHANGED = NO
CODEX_CONFIG_CHANGED = NO

SECRET_EXPOSURE = NO

BATCH_5_2R = PARTIAL
BATCH_5_2_RESUMED = YES
NEXT_BATCH_READY = NO
```

停止边界：本批未进入视频、首尾帧、音频、其他 Scene 或 Episode 扩批。
