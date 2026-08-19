# Batch 6.0R-E2E Recovery & Resume 执行报告

执行日期：2026-08-19（Asia/Shanghai）  
执行 Host：macOS 26.5 / arm64  
最终结论：`BATCH_6_0R_E2E = PARTIAL`

## 1. 执行摘要

本轮严格按 `RECOVER → RECONCILE → RESUME → VERIFY` 执行，没有从头重建 Batch 6.0R-E2E，也没有把上一会话记忆当作事实来源。

Recovery Audit 确认：

- Work、Script、Episode、6 个 Scene、27 个 Shot 均真实存在于 Java 长期状态中，ID 与本地 checkpoint 一致。
- 8 个稳定 Asset 和 8 个稳定参考 Media 均真实存在，Asset→Media 引用与本地 manifest 一致。
- `batch6-0re2e` 含 29 个昨日证据文件：26 个 PNG、3 个 JSON；没有 MP4、视频 metadata、已完成 Shot 图片或 Shot 视频。
- 8 个正式 identity-annotated 参考 PNG 的本地 SHA-256 与 manifest、Java Media `content.sha256` 全部一致，MIME 与文件大小也一致。
- Java `media.resolve_media` 能为 8 个 Media 返回 resolve 信息，但当前 MinIO 对 8 个物理对象均返回 HTTP 404。
- 现有正式 Contract 没有“保留原 mediaId、恢复同一 object”的能力。按照任务的情况 B 规则，没有创建重复 Media、没有直传 MinIO、没有修改数据库。
- `comfy-cloud-2/search_templates(q="image", limit=1)` 首次成功，总匹配数 432；没有 OAuth、没有生成提交。

因此恢复门禁尚未通过，不能把本地文件绕过 Java 直接交给 Provider，也不能用新 Media 替换已有 Media。真实阻断点是 8 条 `MEDIA_RECONCILIATION_BLOCKED`，不是 Comfy 认证。

```text
REUSED_LOCAL_MEDIA_COUNT = 8
RECOVERED_MEDIA_COUNT = 0
NEW_IMAGE_GENERATION_COUNT = 0
NEW_VIDEO_GENERATION_COUNT = 0
AVOIDED_REGENERATION_COUNT = 8
```

`REUSED_LOCAL_MEDIA_COUNT` 表示 8 个正式本地参考文件已被识别、校验并作为恢复真值保留；因 MinIO 恢复被阻断，它们尚未进入新的 Provider handoff。

## 2. 当前运行环境

| 项目 | 实际值 | 结果 |
|---|---|---|
| OS | macOS 26.5, Darwin 25.5.0, arm64 | PASS |
| project root | `/Users/yizhao/PyProject/historical_plugin` | PASS |
| batch6-0re2e | `/Users/yizhao/PyProject/historical_plugin/drama-plugin/plugin/docs/reports/artifacts/batch6-0re2e` | PASS |
| Java service | `127.0.0.1:8080`，default profile；启动后真实 Work 查询成功 | PASS |
| Drama MCP | `drama-tools`，`127.0.0.1:8765/mcp`；工具发现成功 | PASS |
| Comfy MCP | `comfy-cloud-2`，`https://cloud.comfy.org/mcp` | PASS |
| Comfy auth | 当前 X-API-Key 配置；未读取或输出密钥；未发起 OAuth | PASS |

Java 与 Drama MCP 在本轮开始时未运行。本轮按仓库既有 jar、既有 `.env` 和既有 Tool Contract 启动，没有修改配置。

## 3. Recovery 输入

优先读取并采信以下自描述证据：

1. `text-regression-result.json`：文本树 ID、27 Shot、历史与连续性 review、视觉调用为 0。
2. `reference-asset-manifest.json`：8 Asset、8 Media、正式 SHA-256、8 次 initial reference generation 加 1 次杨国忠定向修订。
3. `pre-spend-production-plan.json`：19 个回归目标 Shot、首次出场 ledger、计划模板与 `submittedJobs = 0`。
4. 8 个 `resolved-references/REF_*.png`：本地正式参考字节。
5. 8 个 `references/marked/*.png`：身份标注版本，与 resolved copies 逐一同 hash。

未发现昨天的 MP4、Shot provider output、Shot Media manifest、Comfy Shot jobId/promptId 或已提交 Shot job 记录。

## 4. 本地产物清单摘要

完整逐文件清单见：

`artifacts/batch6-0re2e/recovery/LOCAL_RECOVERY_INVENTORY.json`

| 类型/角色 | 数量 | 说明 |
|---|---:|---|
| PNG | 26 | 9 个 Provider reference output、8 个 identity-annotated reference、8 个 resolved stable copy、1 个 resolve probe |
| JSON | 3 | 文本 checkpoint、Asset/Media manifest、pre-spend plan |
| MP4 / 其他视频 | 0 | 未发现 |
| Markdown / 日志 | 0 | 目录内未发现 |

Inventory 每行记录 `relativePath/type/fileSize/SHA-256/mtime/possibleEntity/possibleShot/possibleAssetRole/possibleMediaType/evidenceBasis`。业务归属仅在 manifest 与 hash 支持时标记为 `MANIFEST_AND_HASH`；原始 Provider 文件只标为 filename/checkpoint 候选，不将文件名当作持久事实。

所有 26 个图像均经 `file` 识别为 `image/png`。没有移动、删除或覆盖原始文件。

## 5. Java 长期状态发现

查询经正式 Java Tool operation mapping 执行；没有直连 MySQL。

| Domain | 发现 | 状态 |
|---|---|---|
| Work | `work_9cc5d11969a64f93bce4a544f349c793` / 《关门以东》Batch 6.0R-E2E | EXISTS |
| Script | `script_a404a8277fef45eda8ef3aaf478307cc`，父级 Work 一致 | EXISTS |
| Episode | `episode_c33021fe53ba4af08cd8b98113184dd2`，父级 Script 一致 | EXISTS |
| Scene | 6/6，order 1–6，父级 Episode 一致 | EXISTS |
| Shot | 27/27，shotNo 1-01 至 6-04，Scene hierarchy 一致 | EXISTS |
| Asset | 8/8：5 个 MASTER_CHARACTER_CARD、3 个 MASTER_SCENE_CARD | PARTIAL（逻辑存在，物理参考对象缺失） |
| Media | 8/8 stable reference Media；无 Shot Media | PARTIAL（记录存在，MinIO 对象缺失） |

Java/Plugin 的公开 Media Contract 不暴露 bucket/object key/version/createdAt；报告没有通过数据库旁路补取这些字段。

## 6. MinIO 状态

实际运行配置来源：当前启动 jar 内嵌 `application.yml`，default profile，且启动命令未设置 storage env override。

```text
endpoint = http://192.168.1.86:9000
bucket = drama-media
region = zh-east-1
credentials = REDACTED
```

没有使用 localhost、127.0.0.1 或 Windows 昨日地址作为 MinIO 假设。

8 次 Java resolve 均返回 200、`image/png` 和声明大小；随后对当前 MinIO 签名对象执行实际 GET，8/8 返回 404。因此结论是“Java Media 存在、当前 bucket 对象缺失”，不是网络不可达，也不是 hash 冲突。

## 7. Local / Java / MinIO Reconciliation Matrix

| Reference | Local | Java Media | MinIO | Local↔Java hash | MIME | Size | 状态 |
|---|---|---|---|---|---|---|---|
| REF_GESHUIHAN | YES | YES | NO (404) | MATCH | MATCH | 1,650,471 MATCH | LOCAL_AND_JAVA / BLOCKED |
| REF_YANGGUOZHONG | YES | YES | NO (404) | MATCH | MATCH | 1,495,717 MATCH | LOCAL_AND_JAVA / BLOCKED |
| REF_XUANZONG | YES | YES | NO (404) | MATCH | MATCH | 1,573,493 MATCH | LOCAL_AND_JAVA / BLOCKED |
| REF_CUIQIANYOU | YES | YES | NO (404) | MATCH | MATCH | 1,522,837 MATCH | LOCAL_AND_JAVA / BLOCKED |
| REF_HUOBAGUIREN | YES | YES | NO (404) | MATCH | MATCH | 1,665,993 MATCH | LOCAL_AND_JAVA / BLOCKED |
| REF_TONGPASS | YES | YES | NO (404) | MATCH | MATCH | 1,936,840 MATCH | LOCAL_AND_JAVA / BLOCKED |
| REF_LINGBAO | YES | YES | NO (404) | MATCH | MATCH | 2,239,420 MATCH | LOCAL_AND_JAVA / BLOCKED |
| REF_CHANGAN | YES | YES | NO (404) | MATCH | MATCH | 1,654,401 MATCH | LOCAL_AND_JAVA / BLOCKED |

这里的 Java hash 指 Media 正式 `content.sha256`；MinIO hash 因对象 404 无法计算。没有 `HASH_CONFLICT`。

## 8. 恢复了哪些已有媒体

恢复到 MinIO/Java 的正式媒体：0。

8 个本地正式参考均通过完整性验证，但情况属于任务定义的情况 B：Java Media 存在、MinIO 对象缺失。现有 Tool Contract 只支持新 import 产生新 Media，不能安全恢复原 mediaId 对应的 object。因此全部标记：

```text
MEDIA_RECONCILIATION_BLOCKED
```

## 9. 哪些媒体被直接复用

8 个 `resolved-references/REF_*.png` 被直接复用为 Recovery truth，并与 8 个 `references/marked/*.png` 逐一 hash 对齐。它们没有被重新生成，也没有被覆盖。

由于正式 resolve handoff 失败，这些本地字节没有越过 Contract 直接上传给 Comfy。

## 10. 哪些媒体真正重新生成

本轮没有任何重新生成：

- 图片：0
- 视频：0
- Comfy job submit：0
- Comfy job wait/output fetch：0

## 11. 为什么没有重新生成

MinIO 缺失不能成为重新付费生成理由。本地已有 8 个正式、review PASS、带身份标识且 hash 与 Java 记录一致的参考文件。重新生成会违反“已有本地媒体不重新生成”和 `QUERY/RECOVER BEFORE RESUBMIT` 原则。

## 12. FIRST_REAL_INCOMPLETE_NODE

```text
FIRST_REAL_INCOMPLETE_NODE =
Work work_9cc5d11969a64f93bce4a544f349c793
/ Stable Reference Media
/ REF_GESHUIHAN（与其余 7 个参考并列）
/ MINIO_OBJECT_RECOVERY
```

如果 8 个原 Media 对象通过正式能力恢复并通过 hash 验证，下一生产断点才是：

```text
Episode 1 / Scene 1 / Shot 1-01 / IMAGE
```

依据是 `pre-spend-production-plan.json` 的 `submittedJobs = 0`，且本地没有任何 Shot image/video output。

## 13. Resume 执行路径

实际路径：

```text
Recovery Audit
→ Local/Java/MinIO Reconciliation
→ 8 × MEDIA_RECONCILIATION_BLOCKED
→ Resume generation gate remains CLOSED
```

没有重新 Research、创建或保存 Work/Script/Episode/Scene/Shot/Asset/Media。

## 14. Comfy Cloud 调用与重试记录

| Operation | Attempt | Result | Retry |
|---|---:|---|---|
| `comfy-cloud-2/search_templates(q="image", limit=1)` | 1 | PASS，432 matches | 不需要 |

调用成功后的 SSE session cleanup 出现 GET/DELETE 400 日志，但 tool result 已成功，未把清理日志误判为业务失败，也没有重试或提交 job。

```text
COMFY_MCP = comfy-cloud-2
AUTH_MODE = X-API-Key
OAUTH_REQUIRED = NO
MCP_RETRY = PASS（本次无需重试；预算规则已保持）
```

未调用旧 `comfy-cloud`，未执行 `codex mcp login`，未修改 MCP 配置。

## 15. 图片生成结果

- 既有稳定参考：8 个 accepted reference，另有 1 个历史杨国忠 targeted revision provider output。
- 本轮新生成：0。
- 27 个计划 Shot image：均 `NOT_STARTED`。
- 本地正式参考 integrity：8/8 PASS。
- 当前正式存储闭环：0/8，因 MinIO 404。

## 16. 视频生成结果

- 本地 MP4：0。
- Java Shot Video Media：0。
- 计划 regression target video：19。
- 本轮新视频生成：0。
- 状态：`NOT_STARTED / BLOCKED_BY_REFERENCE_MEDIA_RECOVERY`。

## 17. 首次出场姓名角标检查

Pre-spend ledger 已冻结以下首次清晰出场：

| Shot | 人物 | 应用角标 |
|---|---|---|
| 1-02 | 哥舒翰 | 哥舒翰｜潼关主帅 |
| 2-01 | 杨国忠 | 杨国忠｜右相 |
| 2-02 | 唐玄宗 | 唐玄宗｜唐朝皇帝 |
| 3-03 | 崔乾祐 | 崔乾祐｜燕军将领 |
| 6-02 | 火拔归仁 | 火拔归仁｜哥舒翰部将 |

最终视频尚未生成，因此 `FIRST_APPEARANCE_NAME_TAG = NOT_EXECUTED`，不能虚报 PASS。后续恢复后必须优先用非生成型后处理加入安全区角标，再导入最终 Media。

## 18. 历史主线检查

真实 Work/Script/Episode/Scene/Shot 内容与本地 text checkpoint 一致：

- 潼关有效守势 → 政治互疑与强令出关 → 灵宝西原诱敌伏击 → 火烟与后袭 → 全军崩溃与失关 → 哥舒翰被执 → 长安转入避乱。
- 哥舒翰是主角；王思礼只保留劫相建议和前军行动的次要史实作用，没有承接主战场决定权。
- P1–P9 historical spine、Scene/Shot continuity、fact attribution 均为 PASS。

```text
HISTORICAL_MAINLINE = PASS
CHARACTER_ROLE_BOUNDARY = PASS
SCENE_CONTINUITY = PASS
SHOT_CONTINUITY = PASS（文本/设计层）
```

## 19. Media / MinIO / Hash 完整性

| 验证 | 结果 |
|---|---|
| Local PNG readable/MIME | PASS 26/26 |
| Accepted local reference SHA vs manifest | PASS 8/8 |
| Accepted local reference SHA vs Java `content.sha256` | PASS 8/8 |
| Java Media record | PASS 8/8 |
| Java resolve response | PASS 8/8 |
| MinIO object GET | FAIL 0/8；8 × HTTP 404 |
| Tripartite hash equality | BLOCKED（无 MinIO bytes） |

## 20. 修改文件列表

本轮新增：

- `plugin/docs/reports/40-Batch-6.0R-E2E-Recovery-Resume-执行报告.md`
- `plugin/docs/reports/artifacts/batch6-0re2e/recovery/LOCAL_RECOVERY_INVENTORY.json`

未修改或覆盖任何昨天产物。

任务开始前已存在但未触碰的工作区状态：`drama-service/server/src/main/resources/application.yml` 为 modified；若干 `.DS_Store` 为 untracked。

## 21. 是否修改代码

```text
CODE_CHANGED = NO
```

没有修改 Plugin、MCP Server、Java、Skill、Comfy Adapter 或测试。

## 22. 遗留问题

唯一主要阻断：当前正式 Contract 缺少安全、幂等的“按已有 mediaId 恢复缺失 object”能力，而 8 个 Java Media 指向的当前 MinIO 对象全部 404。

允许的后续路线只能是其中之一：

1. 在保持原 mediaId、验证预期 hash/size/mime、禁止覆盖已存在对象的前提下，提供正式恢复能力；或
2. 由系统所有者明确批准新的 Media replacement/migration 语义，并同步修订 8 个 Asset 引用，且保留旧 Media，不制造歧义。

本轮未自行选择第 2 条，因为任务明确禁止在情况 B 直接创建新 Media。

## 23. 最终 PASS / FAIL Matrix

### Business

| 项目 | 结果 |
|---|---|
| WORK | PASS |
| SCRIPT | PASS |
| EPISODE | PASS |
| SCENE | PASS 6/6 |
| SHOT | PASS 27/27（设计与长期状态） |
| ASSET | PARTIAL 8/8 逻辑存在，物理参考缺失 |

### Media

| 项目 | 结果 |
|---|---|
| MEDIA_RECORD | PASS 8/8 |
| MINIO_OBJECT | FAIL 0/8 |
| RESOLVE | FAIL（URL issuance PASS，object retrieval 404） |
| HASH_EQUALITY | PARTIAL：Local↔Java PASS；MinIO unavailable |

### Production

| 项目 | 结果 |
|---|---|
| IMAGE_GENERATION | NOT_RESUMED |
| VIDEO_GENERATION | NOT_RESUMED |
| LOCAL_OUTPUT | PASS for 8 stable references；Shot outputs absent |
| MEDIA_IMPORT | BLOCKED / 0 |

### Historical / Creative

| 项目 | 结果 |
|---|---|
| HISTORICAL_MAINLINE | PASS |
| CHARACTER_ROLE_BOUNDARY | PASS |
| SCENE_CONTINUITY | PASS |
| SHOT_CONTINUITY | PASS at text/design layer；visual layer not executed |

### Visual identity

| 项目 | 结果 |
|---|---|
| REFERENCE_IMAGE_IDENTITY_LABEL | PASS 8/8；可见边缘标识与 manifest 唯一映射 |
| FIRST_APPEARANCE_NAME_TAG | NOT_EXECUTED；无最终视频 |

### Resume

| 项目 | 结果 |
|---|---|
| NO_DUPLICATE_WORK | PASS |
| NO_DUPLICATE_MEDIA | PASS |
| NO_UNNECESSARY_REGENERATION | PASS |
| RECOVERY_FROM_LOCAL_OUTPUT | PARTIAL：已识别/校验，正式恢复受阻 |
| RESUME_FROM_REAL_CHECKPOINT | PASS：断点已重建；生成门禁因前置阻断未开启 |

### MCP

| 项目 | 结果 |
|---|---|
| COMFY_MCP | PASS：`comfy-cloud-2` |
| AUTH_MODE | PASS：X-API-Key |
| OAUTH_REQUIRED | NO |
| MCP_RETRY | PASS |

## 最终判定

```text
BATCH_6_0R_E2E = PARTIAL

PRIMARY_BLOCKER =
8 existing Java Media records
+ 8 verified local reference files
+ 0 current MinIO objects
+ no formal same-mediaId object recovery contract
```

在该阻断解除前继续图片/视频生成会违反正式 reference handoff、已有媒体优先复用和禁止重复 Media 的约束，因此本轮在 Recovery Audit 后正确停止生成阶段。
