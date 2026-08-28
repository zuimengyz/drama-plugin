# Batch 63R — Runtime Ownership / Host / Storage Boundary Reconciliation

## 1. Executive Summary

本批已完成真实审计、生产代码整改、外部 Runtime 迁移、单元/静态测试、独立进程验证和既有 63 号 Voice/Media 的真实存储回归。

核心结论：63 号让 Host 感知 MinIO，不是因为 MCP 或 Plugin 持有 S3 SDK，而是因为 Java 的 `resolve_voice` / `resolve_media` 把 **MinIO/S3 presigned URL** 直接返回给 Host；Branch B 与生产 E2E 随后用通用 HTTP client 直接下载该 URL。旧的聚合 Runtime 又同时携带 `DRAMA_MEDIA_STORAGE_ENDPOINT`，使这项数据路径泄漏进一步变成 Host 部署责任。

整改后，Java 返回 `/api/content/voice/{id}` 与 `/api/content/media/{id}` 的 **Drama Service-owned temporary content URL**。Java 验证 HMAC 临时令牌、查 DB、从 Object Storage 打开对象并流式返回。Plugin 强制内容 URL 与配置的 Drama Service 同源；Storage origin 会被拒绝。

```text
BATCH_63R_RUNTIME_STORAGE_RECONCILIATION = PASS
HOST_STORAGE_INDEPENDENCE = PASS
FISH_REAL_CALLS = 0
```

## 2. Scope / DPD Freeze

本批只修改 Runtime Ownership、Host Boundary 与 Storage Boundary。

未创建 `dramatic-performance-direction` Skill；未修改 PerformanceIntent、SceneState、Character Understanding、Creative Voice Casting、DPD contract/snapshot/fingerprint proposal、Audio/Visual projection；未实现 Lip Sync。

```text
DPD_IMPLEMENTATION = NOT_STARTED
DPD_FROZEN = PASS
DPD_CODE_CHANGES = NONE
NEXT_DPD_BATCH = NOT_STARTED
LIP_SYNC = NOT_STARTED
```

## 3. AS-IS Runtime Topology

审计开始时的真实状态：

```text
~/.config/historical-plugin/runtime.env
        ├── MCP bind/client + Plugin config
        ├── Plugin provider modes / Drama Service tokens
        ├── Fish
        ├── Java server
        ├── MySQL
        ├── MinIO/S3
        └── historical frontend/harness variables
                    ↓ manual source
        MCP / Plugin / Java / integration shell

drama-mcp-service repository .env
                    ↓ implicit python-dotenv load
               MCP settings

drama-service application.yml
                    ↓ contained deployment-specific credential defaults
             Java default profile
```

物理上能够启动，不等于 ownership 正确。聚合文件使 Service-only Storage 配置可见于 Host；MCP 的隐式 `.env` 又形成第二个配置入口。

## 4. AS-IS Storage Access Topology

真实代码恢复如下：

```text
Codex / integration runner
        ↓ MCP
drama-mcp-service
        ↓
drama-plugin
        ↓ resolve_voice / resolve_media
drama-service
        ↓ S3Presigner
MinIO/S3 presigned URL
        ↑ returned to Host
Host generic HTTP GET
        ↓
MinIO/S3
```

`URL_OWNER = STORAGE`。

Branch B 的真实路径为：

```text
FishRoleDubbingProvider._materialize_mapping
  → voices.resolve_voice
  → generic httpx GET(resolved.url)
  → MinIO
  → local master bytes
  → Fish Create Model
```

这正是 63 号操作中 Host 需要修正 MinIO endpoint 的代码原因。

## 5. Runtime Variable Ownership Audit

### 5.1 MCP Host active assignments

| Variable | Current consumer / code reference | Correct owner | Action |
| --- | --- | --- | --- |
| `DRAMA_MCP_URL` | integration clients (`run_mcp_e2e.py` 等) | `MCP_HOST` | MOVE to `mcp-host.env` |
| `DRAMA_PLUGIN_CONFIG` | `drama_mcp_service.settings.Settings.from_environment` | `MCP_HOST` | MOVE to `mcp-host.env` |

MCP allowlist 还明确支持 `DRAMA_MCP_HOST`、`DRAMA_MCP_PORT`、`DRAMA_PLUGIN_ROOT`；当前外部 Runtime 未赋值，使用代码默认值，因此没有人为新增 assignment。

### 5.2 Plugin active assignments

动态读取点为 `drama_plugin.config.loader:_environment_overrides`；本地导入根读取点为 `providers/http/media_source.py`。

| Variable family / exact active names | Consumer | Correct owner | Action |
| --- | --- | --- | --- |
| `DRAMA_PLUGIN_PROVIDER_MEMORY_MODE`, `...ASSET...`, `...RESEARCH...`, `...PRODUCTION...`, `...MEDIA...`, `...CONTEXT...`, `...VOICE...` | provider composition | `PLUGIN` | MOVE |
| `DRAMA_PLUGIN_SERVICE_MEMORY_BASE_URL/API_TOKEN/TIMEOUT_SECONDS` | Memory HTTP provider | `PLUGIN` | MOVE |
| `DRAMA_PLUGIN_SERVICE_ASSET_BASE_URL/API_TOKEN/TIMEOUT_SECONDS` | Asset HTTP provider | `PLUGIN` | MOVE |
| `DRAMA_PLUGIN_SERVICE_RESEARCH_BASE_URL/API_TOKEN/TIMEOUT_SECONDS` | Research HTTP provider | `PLUGIN` | MOVE |
| `DRAMA_PLUGIN_SERVICE_PRODUCTION_BASE_URL/API_TOKEN/TIMEOUT_SECONDS` | Production HTTP provider | `PLUGIN` | MOVE |
| `DRAMA_PLUGIN_SERVICE_MEDIA_BASE_URL/API_TOKEN/TIMEOUT_SECONDS` | Media HTTP provider | `PLUGIN` | MOVE |
| `DRAMA_PLUGIN_SERVICE_CONTEXT_BASE_URL/API_TOKEN/TIMEOUT_SECONDS` | Context HTTP provider | `PLUGIN` | MOVE |
| `DRAMA_PLUGIN_SERVICE_VOICE_BASE_URL`, `...API_TOKEN` | Voice HTTP provider | `PLUGIN` | MOVE |
| `DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS` | Host-local media source policy | `PLUGIN` | MOVE |
| `DRAMA_PLUGIN_ROLE_DUBBING_OUTPUT_DIRECTORY`, `...TIMEOUT_SECONDS` | Role Dubbing composition | `PLUGIN` | MOVE |
| `FISH_AUDIO_API_KEY`, `FISH_AUDIO_BASE_URL`, `FISH_TTS_MODEL` | Fish external provider boundary | `PLUGIN` | MOVE |

共 33 个 active Plugin assignments。Token/API key 是 secret；base URL、mode、timeout、path、model 不是 secret。完整逐变量表位于 `plugin/docs/runtime-ownership.md`，不记录任何值。

### 5.3 Drama Service active assignments

实际读取点为 `server/src/main/resources/application.yml`。

| Variable | Consumer | Correct owner | Action |
| --- | --- | --- | --- |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD` | Spring datasource | `DRAMA_SERVICE` | MOVE |
| `DRAMA_TOOL_SECRET` | Tool auth + temporary content token signing | `DRAMA_SERVICE` | MOVE |
| `SERVER_PORT`, `CORS_ALLOWED_ORIGINS` | Java HTTP server | `DRAMA_SERVICE` | MOVE |
| `DRAMA_MEDIA_STORAGE_ENDPOINT`, `...BUCKET`, `...ACCESS_KEY`, `...SECRET_KEY`, `...REGION` | Java S3-compatible adapter | `DRAMA_SERVICE` | MOVE |
| `DRAMA_MEDIA_RESOLVE_TTL_SECONDS` | Service content-token TTL | `DRAMA_SERVICE` | KEEP semantics / MOVE |
| `DRAMA_MEDIA_MAX_FILE_SIZE`, `...MAX_REQUEST_SIZE` | Spring multipart limits | `DRAMA_SERVICE` | MOVE |

共 16 个 active Service assignments。

### 5.4 Obsolete assignments

| Variable | Audit result | Action |
| --- | --- | --- |
| `OPENAI_API_KEY` | current Plugin source has no consumer | REMOVE from active runtime |
| `DASHSCOPE_API_KEY` | current Plugin source has no consumer | REMOVE |
| `VITE_API_BASE_URL` | frontend deployment concern, not one of the three processes | REMOVE |
| `HARNESS_MODEL` | no current consumer | REMOVE |
| `DRAMA_E2E_PREFIX_FAMILY` | integration-only historical setting; default sufficient | REMOVE |

```text
ACTIVE_RUNTIME_ASSIGNMENTS = 51
ACTIVE_RUNTIME_UNCLASSIFIED_VARIABLES = 0
```

## 6. Existing runtime.env Problems

1. 同一 active source 混合 Host、Plugin、Fish、Java、DB、Storage。
2. Storage endpoint 因 presigned URL 数据路径而被 Host 实际依赖。
3. MCP 又会隐式读取 repository `.env`，启动入口不唯一。
4. 三个 Git 仓库跟踪 `.env.example`；workspace 聚合 example 曾混合多个组件语义。
5. 旧 `migrate-role-dubbing-runtime.sh` 会把 Storage endpoint 写回聚合 Runtime，继续固化泄漏。
6. Java `application.yml` 含 deployment-specific credential defaults，掩盖 Service runtime 缺失。

## 7. Target Runtime Ownership

```text
~/.config/historical-plugin/
├── mcp-host.env       # MCP_HOST
├── drama-plugin.env   # PLUGIN
└── drama-service.env  # DRAMA_SERVICE
```

三个 active 文件均为 mode `0600`。没有 `.env`、`.env.example` 或 Runtime 文件进入 Git。

## 8. MCP Host Responsibility

MCP 仅读取 Plugin root/config、bind host/port。已删除 `python-dotenv` 依赖和隐式 repository `.env` 加载。启动器只加载 `mcp-host.env + drama-plugin.env`，随后显式 unset Service-only variables。

## 9. Drama Plugin Responsibility

Plugin 读取 provider mode、Drama Service HTTP credential、Fish credential/model、Host-local allowed roots 与 Role Dubbing output/timeout。它不读取 MySQL、MinIO/S3、bucket 或 storage credentials。

## 10. Drama Service Responsibility

Java 是唯一 DB/Object Storage consumer。`application.yml` 现在要求通过 Service process environment 提供 DB、Tool secret 和 Storage 配置；已删除 deployment credential defaults。S3 SDK 仅存在于 Java Storage adapter。

## 11. Host Direct Storage Access Audit

### HOST_STORAGE_ACCESS_MATRIX

| Caller | AS-IS operation | Direct Storage? | Needed? | Fix |
| --- | --- | ---: | ---: | --- |
| `FishRoleDubbingProvider._materialize_mapping` | GET Voice presigned URL | YES | bytes needed；Storage URL 不需要 | `VoiceProvider.download_voice` → same-origin Drama Service content |
| `HttpVoiceProvider` | returned storage URL to caller | contract leak | NO | service-origin enforced download method |
| `HttpMediaProvider` | returned storage URL to caller | contract leak | NO | service-origin enforced download method |
| Fish production E2E runner | GET Voice/Media resolved URL | YES | integrity bytes needed | assert `URL_OWNER=DRAMA_SERVICE` before GET |
| Batch 7.1 media runner | GET resolved Media URL | YES | roundtrip bytes needed | assert Service origin; use Plugin credential name |
| MCP service | tool projection only | NO | NO | unchanged; static negative test |
| Codex | could receive storage URL through resolve contract | indirect leak | NO | resolve now returns Service route |
| Java Storage adapter | bucket read/write/restore/delete | YES | YES | retained as sole Storage owner |

## 12. MinIO Preflight Audit

没有发现必须保留的 committed Host → MinIO health probe。真实阻断来自 Host 需要下载 presigned URL，而不是独立 health endpoint。

已删除会把 `DRAMA_MEDIA_STORAGE_ENDPOINT` 注入聚合 Runtime 的旧 migration script。新的 E2E preflight 只验证 MCP、Plugin、Drama Service HTTP 与 storage-backed operation；不 GET MinIO health。

```text
DIRECT_MINIO_PREFLIGHT_REMOVED = YES
```

## 13. resolve_voice Audit

BEFORE：`VoiceImportService` 调用 `MediaStorage.resolve`；S3 adapter 使用 `S3Presigner`；结果 URL owner 为 Storage。

AFTER：`ContentDeliveryService.resolveVoice` 查询 Voice、签发绑定 `kind + id + expiry` 的 HMAC token，并返回：

```text
/api/content/voice/{voiceId}?token=<redacted>
```

```text
URL_OWNER = DRAMA_SERVICE
```

Host-facing Voice DTO 同时移除了 `storageType`、`bucketName`、`objectKey`；字段继续保留在 Java Entity/DB，作为 server-side persisted metadata。

## 14. resolve_media Audit

BEFORE：同样由 S3 presigner 返回 Storage URL。

AFTER：

```text
/api/content/media/{mediaId}?token=<redacted>
URL_OWNER = DRAMA_SERVICE
```

Media Tool envelope 原本已隐藏 bucket/object key，继续保持。

## 15. Branch B Voice Master Access Audit

修正后的 Branch B：

```text
FishRoleDubbingProvider
  → VoiceProvider.download_voice
  → HttpVoiceProvider
  → HttpProviderClient same-origin gate
  → Drama Service /api/content/voice/{id}
  → Java DB lookup
  → Java S3 client
  → bytes
  → local SHA-256 verification
  → Fish Create Model
```

Storage-origin URL 会以 `UNRESOLVABLE_MEDIA` provider error 拒绝；Drama Service delivery failure 在 Role Dubbing 边界转为 `VOICE_REFERENCE_UNAVAILABLE`。

## 16. Storage Boundary Root Cause

根因不是 “当前 MinIO 在哪台机器”，而是 Host-facing resolve contract 暴露了 Storage-owned address。只要 Storage endpoint 对 Host 不可达，Host 就失败；聚合 Runtime 因而被迫携带并修改 MinIO endpoint。

正确修复是把 bytes delivery 收回 Drama Service，而不是让 Plugin 安装 boto3/MinIO SDK，也不是修另一个 endpoint。

## 17. Runtime Migration

迁移按以下顺序完成：

1. 只读取 assignment name 并逐项分类；未打印 value。
2. 创建时间戳 pre-migration backup。
3. 写入三个 `0600` owner file，并逐文件运行 allowlist validation。
4. 将原文件重命名为 retired backup；active `runtime.env` 不再存在。
5. 移除 5 个 obsolete assignments。

外部备份：

```text
runtime.env.pre-63r-20260828T133301Z.bak
runtime.env.retired-63r-20260828T133301Z.bak
```

备份未复制到 Git，报告不含值。

```text
COMBINED_RUNTIME_ENV = RETIRED
MCP_HOST_ENV = PASS (2 active assignments)
DRAMA_PLUGIN_ENV = PASS (33 active assignments)
DRAMA_SERVICE_ENV = PASS (16 active assignments)
```

## 18. Startup / Loader Migration

workspace deployment scripts：

- `scripts/start-drama-mcp.sh`：validate/load Host + Plugin，unset Service-only vars，exec MCP。
- `scripts/start-drama-service.sh`：validate/load Service，unset Plugin/Fish/MCP vars，exec Java。
- `scripts/runtime-env-ownership.py`：三个显式 allowlist。
- `scripts/load-env.sh`：仍是通用单文件 loader；现在必须传 explicit file。
- `scripts/validate-env-syntax.py`：拒绝 command substitution、pipeline、额外 command 等可执行 shell syntax。

真实 PID environment 只检查变量名存在性，不输出 value：

```text
MCP_PROCESS_SERVICE_ONLY_VARS = NONE
DRAMA_SERVICE_FOREIGN_VARS = NONE
DRAMA_SERVICE_REQUIRED_VARS = PRESENT
```

## 19. Service-mediated Voice Content

`ContentController` 对 token 校验后调用 `storage.open(bucket,key)`；`S3CompatibleMediaStorage.open` 使用 Java S3Client 获取 stream，Controller 使用 `StreamingResponseBody` 返回，设置 `no-store`、Content-Type、Content-Length，并关闭 input stream。

无效 token 真实 HTTP 验证：`401`。

## 20. Service-mediated Media Content

Media 使用同一 delivery service 与 storage adapter。Java 不再创建 `S3Presigner`；active source 中不存在 `presignGetObject`、`GetObjectPresignRequest` 或 `storage.resolve(...)`。

## 21. Error Ownership

新的错误链：

```text
MinIO/S3 failure
  ↓ Java S3CompatibleMediaStorage
STORAGE_ERROR (provider-neutral service error)
  ↓ HTTP
HttpVoiceProvider / HttpMediaProvider
  ↓
RemoteServiceError
  ↓ Role Dubbing when applicable
VOICE_REFERENCE_UNAVAILABLE
  ↓ MCP safe mapping
Tool failure without vendor credential/topology
```

MCP/Skill error taxonomy没有新增 `MINIO_TIMEOUT` 或 `S3_ERROR`。单元测试证明 Java numeric `42202` 映射为 `STORAGE_ERROR`，且不暴露 remote vendor message。

## 22. Runtime Ownership Tests

新增/更新覆盖：

- MCP/Plugin compose without DB/MinIO env。
- Fish Role Dubbing composition without DB/MinIO env，offline/no request。
- Plugin active source static scan 无 DB/Storage env reads。
- MCP active source static scan 无 DB/Storage env reads。
- 三组件 env allowlist cross-boundary negative cases。
- Drama Service `application.yml` 拥有 DB/Storage 且无 Fish/MCP/Plugin reads。
- generic env loader explicit-file 与 command-substitution negative test。
- repository `.env.example` 删除，`.gitignore` 拒绝 `.env.*`、`*.env`、`runtime.env`。

## 23. Host-storage Independence E2E

使用 63 号既有对象，未创建测试对象：

```text
Voice = voice_06ac45335157432e8322a9b32e8d9804
Media = media_dde17eef66804697a1b9be9d6f881cd0
```

MCP/Plugin 进程确认无 DB/Storage variables 后执行：

| Check | Result |
| --- | --- |
| MCP `/health` | HTTP 200 |
| MCP initialize / list tools | PASS |
| Plugin load | PASS |
| `voice.get_voice` | PASS；无 storage topology fields |
| `voice.resolve_voice` URL owner | DRAMA_SERVICE |
| Voice content download | 360492 bytes；hash match |
| `media.get_media` | PASS |
| `media.resolve_media` URL owner | DRAMA_SERVICE |
| Media content download | 190492 bytes；hash match |
| Host direct MinIO request | 0 |
| Fish request | 0 |

脱敏证据：`artifacts/runtime-storage-boundary/evidence.json`。不保存 token/URL/credential。

```text
HOST_STORAGE_INDEPENDENCE = PASS
DRAMA_SERVICE_STORAGE_ACCESS = PASS
VOICE_STORAGE_ROUNDTRIP = PASS
MEDIA_STORAGE_ROUNDTRIP = PASS
```

## 24. Voice / Role Dubbing Regression

Plugin 全量 139 tests 覆盖 Voice HTTP、Voice lifecycle、Branch A/B/C、Fish offline、Role Dubbing、Media import/resolve 与 MCP-facing contract。

```text
VOICE_REGRESSION = PASS
ROLE_DUBBING_REGRESSION = PASS
FISH_REAL_CALLS = 0
```

## 25. Full Tests

| Project | Command | Result |
| --- | --- | --- |
| drama-plugin | pytest | 139 passed |
| drama-plugin | mypy | 44 source files, no issues |
| drama-mcp-service | pytest | 24 passed |
| drama-mcp-service | mypy | 4 source files, no issues |
| drama-service | Maven test | 53 passed |
| drama-service | Maven package | BUILD SUCCESS |
| integration Python | `py_compile` | PASS |
| loader/ownership scripts | syntax + negative tests | PASS |
| Git | `diff --check` × 3 | PASS |
| secret scan | tracked working tree + artifacts exclusion | 0 findings |

## 26. BEFORE / AFTER Architecture

### BEFORE — Runtime

```text
                  combined runtime.env
        ┌───────────────┼────────────────┐
        ↓               ↓                ↓
   MCP + Plugin      Java Service    runners/frontend
        │               │
        │ also saw      ├── MySQL
        │ DB/MinIO      └── MinIO
        └── Fish
```

### AFTER — Runtime

```text
               mcp-host.env
                     │
                     ↓
             drama-mcp-service
                     │ loads plugin
       drama-plugin.env
                     │
          ┌──────────┴─────────┐
          ↓                    ↓
   Drama Service HTTP       Fish API
          ↓
   drama-service process
          ↑
    drama-service.env
          │
       ┌──┴────┐
       ↓       ↓
     MySQL    MinIO
```

### BEFORE — Storage Access

```text
Plugin/MCP caller → Drama Service resolve → MinIO presigned URL → Host → MinIO
Plugin → Fish API
```

### AFTER — Storage Access

```text
Codex → MCP → Plugin → Drama Service content API → Java S3 client → MinIO
                    └→ Fish API
```

不存在 `Plugin → MinIO`、`MCP → MinIO`、`Codex → MinIO`。

## 27. Git Diff

任务开始时三个 Git worktree 均 clean，因此当前三仓库 diff 可归因于 63R；62/63 报告与 63 号 Landing 未被覆盖。

- drama-plugin：Voice host envelope 去 storage topology；service-content download/same-origin gate；Branch B；runners；tests；runtime docs；删除 tracked `.env.example`。
- drama-mcp-service：删除 implicit dotenv；runtime allowlist tests；real boundary E2E；删除 tracked `.env.example`。
- drama-service：content gateway/token/stream；S3 open；删除 presigner path；required Service config；tests；删除 tracked `.env.example`。
- workspace root 是非 Git deployment aggregation；loader/launch/ownership scripts 与外部 Runtime 迁移属于 deployment state，不伪装成任一子仓库 commit。

`git diff --check` 三仓库均 PASS；没有 reset、clean、覆盖 62/63 或删除 Fish landing。

## 28. Remaining Technical Debt

1. Service content URL 目前从受认证的 resolve request origin 构造；若未来部署在反向代理后，应正式配置并验证 trusted forwarded headers 或明确 public base URL。
2. content endpoint 暂未实现 Range request；当前 Voice/Media 下载与 Fish upload 不需要，未来大视频 seek 可单独设计。
3. 临时 token 位于 query string，已 HMAC、资源绑定、短 TTL、`no-store`；生产 access log 应继续屏蔽 query。若未来有 Gateway，可迁移到 opaque gateway token/header。
4. Frontend runtime 不属于本批三个文件；若启用独立 web deployment，应建立其自身 deployment ownership，不能重新并入 aggregate env。

这些项不要求 Host 知道 Storage topology，不阻塞本批结论。

## 29. Five Required Answers

### A. 为什么 63 号让 Host 感知 MinIO endpoint？

因为 Java resolve 使用 `S3Presigner` 返回 Storage-owned URL，Branch B 与 E2E runner 在 Host 上直接 GET。旧聚合 Runtime 又把 Storage endpoint 注入 Host shell。真实原因是 Host-facing content contract 泄漏，不是网络偶发现象。

### B. MinIO configuration 属于谁？

只属于 `drama-service`。代码证据是 S3Client、bucket read/write/restore/delete/open 全在 Java storage package；Plugin/MCP source 和 process environment 均无 Storage variables。

### C. Host 完全没有 MinIO/DB config 能否运行 MCP/Plugin？

能。真实 MCP PID 检查为 Service-only vars `NONE`，MCP health、Plugin load、Drama Service HTTP、Voice/Media get/resolve/download 全部 PASS。

### D. Plugin 需要 Voice/Media bytes 时能否始终走 Service？

能。HTTP providers 对 content URL 做 Drama Service same-origin 强制校验；Branch B 使用 `download_voice`；真实 Voice/Media URL owner 与下载 route 均为 DRAMA_SERVICE。Storage-origin negative test PASS。

### E. 是否已做到一个变量一个 Owner、组件只加载自身配置？

是。51 个 active assignments 全部归类，unclassified 为 0；三个文件均通过 allowlist；MCP 只加载 Host+Plugin，Java 只加载 Service；combined runtime 已退休。

## 30. Final Status

```text
BATCH_63R_RUNTIME_STORAGE_RECONCILIATION = PASS

DPD_FROZEN = PASS
DPD_CODE_CHANGES = NONE
DPD_IMPLEMENTATION = NOT_STARTED

RUNTIME_OWNERSHIP_AUDIT = COMPLETE
ACTIVE_RUNTIME_UNCLASSIFIED_VARIABLES = 0
RUNTIME_ENV_OWNERSHIP = PASS
COMBINED_RUNTIME_ENV = RETIRED

MCP_HOST_ENV = PASS
DRAMA_PLUGIN_ENV = PASS
DRAMA_SERVICE_ENV = PASS

MCP_PROCESS_SERVICE_ONLY_VARS = NONE
PLUGIN_PROCESS_MINIO_VARS = NONE
PLUGIN_PROCESS_DB_VARS = NONE
DRAMA_SERVICE_FISH_VARS = NONE

DIRECT_HOST_MINIO_PREFLIGHT = REMOVED
DIRECT_MINIO_PREFLIGHT_REMOVED = YES
HOST_TO_MINIO_DEPENDENCY = NONE
PLUGIN_TO_MINIO_DEPENDENCY = NONE
MCP_TO_MINIO_DEPENDENCY = NONE

DRAMA_SERVICE_OWNS_STORAGE = PASS
VOICE_CONTENT_PATH = VIA_DRAMA_SERVICE
MEDIA_CONTENT_PATH = VIA_DRAMA_SERVICE
VOICE_CONTENT_ACCESS = VIA_DRAMA_SERVICE
MEDIA_CONTENT_ACCESS = VIA_DRAMA_SERVICE

HOST_STORAGE_INDEPENDENCE = PASS
DRAMA_SERVICE_STORAGE_ACCESS = PASS
VOICE_STORAGE_ROUNDTRIP = PASS
MEDIA_STORAGE_ROUNDTRIP = PASS

FISH_REAL_CALLS = 0
FISH_ROLE_DUBBING_REGRESSION = PASS
VOICE_REGRESSION = PASS
ROLE_DUBBING_REGRESSION = PASS

DRAMA_PLUGIN_TESTS = PASS (139)
DRAMA_MCP_TESTS = PASS (24)
DRAMA_SERVICE_TESTS = PASS (53)
DRAMA_SERVICE_PACKAGE = PASS

SECRET_LEAKAGE = 0
NEXT_DPD_BATCH = NOT_STARTED
LIP_SYNC = NOT_STARTED
```
