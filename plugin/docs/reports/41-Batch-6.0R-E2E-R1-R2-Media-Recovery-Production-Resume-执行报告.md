# Batch 6.0R-E2E-R1/R2 Media Recovery & Production Resume 执行报告

执行时间：2026-08-19（Asia/Shanghai）

## 1. 执行摘要

R1 已通过正式 Drama Media Contract 恢复 8 个既有 Java Media 的缺失 MinIO object。8 个 `mediaId`、Media 行数及 Asset→Media 绑定均未改变；resolve、MIME、size 和 Local/Java/MinIO SHA-256 全部通过，生产门已打开。

R2 自动进入信用额度预检。`comfy-cloud-2` 的只读 `get_server_info`、`get_billing_activity`、`get_usage_report` 均未返回当前真实 credit balance，无法安全计算 `EFFECTIVE_R2_BUDGET` 与下一任务的 `SAFE_CREDITS_LEFT`。依据“不得猜测 credits、付费提交前必须读取真实余额”的规则，R2 fail-closed 停止。未提交 Comfy job，实际消费 0 credits。

## 2. R1 初始状态

以报告 40、`reference-asset-manifest.json`、`resolved-references/` 和 Java 查询为基线，仅复核 R1 依赖事实：8 个 Java Media 与 8 个本地 reference 均存在，Local SHA 与 Java SHA 8/8 一致，正式 MinIO object 8/8 缺失。R1 期间 Comfy paid generation 为 0。

运行时 MinIO 配置来自 `drama-service` 当前 default profile/application configuration：endpoint `http://192.168.1.86:9000`、bucket `drama-media`、region `zh-east-1`；local allowed root 为 `/Users/yizhao/PyProject/historical_plugin`。报告未记录 access key、secret 或 API key。

## 3. 当前正式 Media Contract 与代码修改

审计确认原 Contract 只有新 Media import 与 resolve，没有“保留现有 mediaId、恢复其缺失物理 object”的正式能力，因此实现了最小通用能力 `media.restore_media_object(mediaId, sourceUri)`：

- 必须先存在 Media，并由服务端读取其既有 storage identity、SHA-256、MIME 和 size；调用者不能指定 bucket、object key、owner 或 Asset binding。
- local source 继续使用现有 allowed-root、regular-file、readable 与 `file://` 规范化校验。
- local SHA/MIME/size 不匹配时拒绝上传；object 已存在且一致返回 `ALREADY_PRESENT`；已存在且冲突返回 `OBJECT_CONFLICT`，不覆盖。
- object 缺失时使用原 object identity 条件写入并回读验证；不创建或更新 Media row。
- 同一 mediaId 与相同 source 重复调用幂等；本轮探针返回 `ALREADY_PRESENT`。

修改范围仅包括 Java Media service/storage/controller、Plugin contract/provider/tool exposure、映射配置和最小测试；无数据库 migration、后台 repair、管理 UI 或业务重构。`drama-service/server/src/main/resources/application.yml` 在本任务开始前已修改，本任务未改动或归属该差异。

### R1 修改文件

Java：

- `server/src/main/java/com/drama/common/exception/ErrorCode.java`
- `server/src/main/java/com/drama/memory/media/MediaDtos.java`
- `server/src/main/java/com/drama/memory/media/MediaController.java`
- `server/src/main/java/com/drama/memory/media/MediaImportService.java`
- `server/src/main/java/com/drama/memory/media/storage/MediaStorage.java`
- `server/src/main/java/com/drama/memory/media/storage/S3CompatibleMediaStorage.java`
- `server/src/main/java/com/drama/memory/media/storage/UnconfiguredMediaStorage.java`
- `server/src/test/java/com/drama/MediaStorageUnitTest.java`
- `server/src/test/java/com/drama/memory/media/storage/S3CompatibleMediaStorageTest.java`
- `docs/plugin-http-operations.yaml`

Drama Plugin / MCP：

- `plugin/src/drama_plugin/contracts/media.py`
- `plugin/src/drama_plugin/contracts/__init__.py`
- `plugin/src/drama_plugin/providers/base/interfaces.py`
- `plugin/src/drama_plugin/providers/http/providers.py`
- `plugin/src/drama_plugin/providers/http/client.py`
- `plugin/src/drama_plugin/providers/mock/providers.py`
- `plugin/src/drama_plugin/tools/catalog.py`
- `plugin/config/drama-service-http.example.yaml`
- `plugin/tests/test_tools.py`
- `plugin/tests/test_plugin.py`
- `plugin/tests/test_drama_service_http_config.py`
- `plugin/tests/test_media_import.py`
- `drama-mcp/tests/test_adapter.py`
- `drama-mcp/tests/test_protocol.py`
- `drama-mcp/integration/run_mcp_e2e.py`
- `drama-mcp/integration/verify_runtime_config.py`

## 4. R1 测试结果

| Suite | Result |
|---|---:|
| Java `mvn test` | PASS |
| Java package | PASS |
| Plugin pytest | 94 passed |
| MCP pytest | 13 passed |
| Plugin mypy | PASS, 34 source files |
| MCP mypy | PASS, 4 source files |

覆盖 missing+matching→RESTORED、existing+matching→ALREADY_PRESENT、local hash mismatch→REJECT、existing conflict→NO OVERWRITE、media not found、outside allowed root、重复恢复幂等。

## 5. R1 Media Recovery Matrix

| Reference | mediaId before/after | Restore | Resolve | SHA/MIME/Size | Result |
|---|---|---|---|---|---|
| REF_GESHUIHAN | `media_2a0e7a10b8fc4dc5863731c02e5392ef` / unchanged | RESTORED | reachable | match | PASS |
| REF_YANGGUOZHONG | `media_9acf2344f16d4314861cc86b669507bb` / unchanged | RESTORED | reachable | match | PASS |
| REF_XUANZONG | `media_29d74ccf25a14b6eaaca7c279cf3973b` / unchanged | RESTORED | reachable | match | PASS |
| REF_CUIQIANYOU | `media_75a43189c6e04bb68eae14af9b5d2c44` / unchanged | RESTORED | reachable | match | PASS |
| REF_HUOBAGUIREN | `media_09d311a310d947e0b3bcc13a3ed5ad77` / unchanged | RESTORED | reachable | match | PASS |
| REF_TONGPASS | `media_0bbcae64f15e4d82b1e8f34512ea5f9f` / unchanged | RESTORED | reachable | match | PASS |
| REF_LINGBAO | `media_d5550347e77145e1a2064b4d55ed72ae` / unchanged | RESTORED | reachable | match | PASS |
| REF_CHANGAN | `media_837edf2e0766462888b427aa0c98192d` / unchanged | RESTORED | reachable | match | PASS |

8 个对象均由 resolve URL 下载后重新计算 SHA-256，结果与 local 和 Java 三方相等；MIME 均为 `image/png`，size 均相等。Media row count 为 8→8，Asset binding change 为 0，duplicate/new Media 为 0。

**R1_MEDIA_RECOVERY = PASS**  
**PRODUCTION_GATE = OPEN**

## 6. R2 Credit Preflight

R2 按要求自动从 `Episode 1 / Scene 1 / Shot 1-01 / IMAGE` 进入预检，并且仅使用 `comfy-cloud-2`、X-API-Key。只读余额查询结果如下：

| Tool | Paid | Current balance returned |
|---|---:|---:|
| get_server_info | No | No |
| get_billing_activity | No | No |
| get_usage_report | No | No |

因此：

```text
CREDIT_BALANCE_AT_R2_START = UNKNOWN
EFFECTIVE_R2_BUDGET = UNKNOWN
CUMULATIVE_CREDITS_CONSUMED = 0
BATCH_BUDGET_LEFT = 1995
```

用户给出的 1995 是本轮 hard cap，不能替代“当前真实账户余额”。由于无法计算 `SAFE_CREDITS_LEFT = min(CURRENT_ACCOUNT_CREDITS, BATCH_BUDGET_LEFT)`，未进入 estimate/submit，不以猜测余额承担超额或 billing failure 风险。

## 7. R2 Production / Media / Retry Matrix

| Item | Result |
|---|---:|
| Paid jobs submitted | 0 |
| Images generated | 0 |
| Videos generated | 0 |
| Completed Shots | 0 |
| New Shot Media | 0 |
| Comfy retries | 0 |
| Duplicate jobs | 0 |
| Credits consumed | 0 |

没有 Provider output，因而无待下载、导入或角标后处理的付费结果。冻结的剧情、Shot 计划、reference identity 和首次出场姓名角标 ledger 均未修改。

## 8. R2 Checkpoint 与停止原因

```text
LAST_COMPLETED_NODE = R1 / REF_CHANGAN / MEDIA_RESOLVE_HASH_VERIFY
NEXT_NODE = Episode 1 / Scene 1 / Shot 1-01 / IMAGE_CREDIT_PREFLIGHT
STOP_REASON = CREDIT_BALANCE_UNAVAILABLE
R2_PRODUCTION = NOT_STARTED
R2_RESUME_SAFETY = PASS
```

恢复要求：`comfy-cloud-2` 能可靠返回当前余额后，从同一 `IMAGE_CREDIT_PREFLIGHT` 重新查询余额、正式估价，再决定是否提交；不能直接 submit。

持久化文件：

- `artifacts/batch6-0re2e/r1-media-recovery-checkpoint.json`
- `artifacts/batch6-0re2e/r2-credit-ledger.json`
- `artifacts/batch6-0re2e/r2-production-checkpoint.json`

## 9. 关键计数

```text
R1_RECOVERY_TARGET_COUNT = 8
R1_RECOVERED_COUNT = 8
R1_ALREADY_PRESENT_COUNT = 0
R1_CONFLICT_COUNT = 0
R1_NEW_MEDIA_COUNT = 0

R2_STARTING_CREDITS = UNKNOWN
R2_EFFECTIVE_BUDGET = UNKNOWN
R2_CREDITS_CONSUMED = 0
R2_CREDITS_REMAINING = UNKNOWN

NEW_IMAGE_GENERATION_COUNT = 0
NEW_VIDEO_GENERATION_COUNT = 0
COMPLETED_SHOT_COUNT = 0
NEW_MEDIA_COUNT = 0
COMFY_JOB_COUNT = 0
COMFY_RETRY_COUNT = 0
AVOIDED_DUPLICATE_JOB_COUNT = 0
```

`R1_ALREADY_PRESENT_COUNT` 指首次 8 条恢复调用；另有一次幂等探针返回 `ALREADY_PRESENT`，不计入恢复目标结果。

## 10. 最终判定

| Gate | Result |
|---|---:|
| R1 object available 8/8 | PASS |
| R1 resolve reachable 8/8 | PASS |
| R1 SHA equality 8/8 | PASS |
| R1 no duplicate/binding change | PASS |
| R2 budget preflight | BLOCKED — current balance unavailable |
| R2 no paid orphan output | PASS |
| R2 resume checkpoint | PASS |
| OAuth required | NO |
| Comfy MCP | `comfy-cloud-2` / X-API-Key |

```text
R1_MEDIA_RECOVERY = PASS
R2_PRODUCTION = NOT_STARTED
BATCH_6_0R_E2E = PARTIAL
PRIMARY_BLOCKER = CREDIT_BALANCE_UNAVAILABLE
```

这是技术性 credit telemetry 阻断，不包装为 `CREDIT_HARD_STOP`，也未发生余额不足或超出 1995 上限。
