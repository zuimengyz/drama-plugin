# 51 — Environment Configuration Audit & Consolidation

审计日期：2026-08-25  
审计范围：`historical-plugin` workspace 下的 `drama-plugin`、`drama-mcp-service`、`drama-service`，以及与其当前 runtime integration 直接相关的脚本、测试和文档。  
安全边界：未读取或记录任何真实 secret value；未调用任何真实 Provider；未生成 Audio/Image/Video；未访问 Comfy Cloud；未修改任何现有 `.env`；未提交代码。

## 1. Executive Summary

本次从实际代码读取点反查，而不是以 `.env.example` 为唯一依据。共确认 **57 个唯一的当前活跃环境变量名**：`drama-plugin` 消费 40 个，`drama-mcp-service` 消费 2 个，`drama-service` 消费 17 个；`OPENAI_API_KEY` 和 `DRAMA_TOOL_SECRET` 分别跨项目共享，因此去重后为 57 个。

审计结论为 **FAIL**，原因不是 inventory 不完整，而是当前 workspace 存在以下配置风险：

1. `drama-service/server/src/main/resources/application.yml` 含 credential-like 默认值；本报告只记为 `REDACTED`。
2. 同一文件含旧 Host/机器相关数据库 endpoint 默认值；本报告只记为 `REDACTED`。
3. 三个工程都不会自动加载其仓库根 `.env`；现有 `.env.example` 不能证明 `.env` 会生效。
4. `drama-plugin` 存在大量代码读取但项目 `.env.example` 未覆盖的 service override。
5. Real TTS 使用两个不同 gate：`DRAMA_PLUGIN_REAL_TTS_E2E` 与 `REAL_TTS_E2E`，语义重复但消费者不同。
6. `drama-service` 前端使用 `VITE_API_BASE_URL`，但仓库根 `.env.example` 未记录；Vite 的自动 `.env` 目录又是 `drama-service/web`，不是 workspace 根。

已在非 Git workspace root 新增聚合层：`.env.example`、`scripts/load-env.sh`、`scripts/check-env.sh`。三个独立仓库原有 `.env.example` 均保留；三个仓库的 `.gitignore` 已经各自忽略 `.env`，无需修改。

## 2. Current configuration loading mechanism

### drama-plugin

- `plugin/src/drama_plugin/config/loader.py:86-103` 可显式读取 YAML，然后用 `os.environ` 覆盖。
- `plugin/src/drama_plugin/config/loader.py:100` 只读取当前 process environment；没有 `load_dotenv`、`python-dotenv`、Pydantic `BaseSettings` 或 `env_file`。
- `plugin/src/drama_plugin/plugin.py:59-65` 调用 `load_config(config_path)`，没有寻找 `.env`。
- `plugin/pyproject.toml` 没有 dotenv dependency。

结论：`PLUGIN_ENV_FILE_AUTO_LOAD = NO`。

### drama-mcp-service

- `examples/minimal_run.py:14-19` 与 `tests/test_live_openai_e2e.py:14-30` 直接调用 `os.getenv`。
- runtime 自身接收已构造的 model 字符串；未实现 `.env` loader。
- `pyproject.toml` 没有 dotenv dependency，也没有 Pydantic Settings。

结论：`MCP_ENV_FILE_AUTO_LOAD = NO`。

### drama-service

- Spring backend 在 `server/src/main/resources/application.yml` 使用 `${ENV_VAR:default}`，由 Spring Environment 解析 process environment / JVM properties / Spring config sources。
- `server/pom.xml` 没有 Spring dotenv、dotenv-java 或同类 dependency；Spring Boot 本身不会把仓库根 `.env` 当作 `application.yml` 自动加载。
- `application-local.yml` 和 `application-test.yml` 是 Spring profile config，不是 dotenv loader。
- 前端 Vite 会处理其 **Vite root** 下的 `.env*` 并只暴露 `VITE_*`；当前 `vite.config.ts` 没有 `envDir`。因此它不会自动读取 workspace root 或 `drama-service` 仓库根的聚合 `.env`。通过 `source scripts/load-env.sh` 进入 process environment 的 `VITE_API_BASE_URL` 则可被子进程继承。

结论：以 `drama-service` 仓库根/backend 的 `.env` 为判断对象，`SERVICE_ENV_FILE_AUTO_LOAD = NO`。

## 3. Complete environment variable inventory

说明：

- “条件必需”表示默认 mock/disabled 路径不需要，但选择相应 HTTP/real provider 后必须非空。
- “文档状态”中的 `EXAMPLE` 指原项目 `.env.example` 已覆盖；`ROOT-ONLY` 指本次新增 workspace aggregation 才覆盖；`README` 指 README 有说明但项目 `.env.example` 缺失；`HISTORICAL` 指仅旧执行报告出现。
- `USED_BUT_UNDOCUMENTED` 以原项目 `.env.example` 是否覆盖为主判据。

### 3.1 drama-plugin variables

| Exact variable | Consumer / source | Description and default | Required / sensitive | Scope / provider | Documentation / class |
|---|---|---|---|---|---|
| `DRAMA_PLUGIN_PROVIDER_MEMORY_MODE` | loader.py:22-24 | memory provider；默认 `mock` | optional / NO | runtime / neutral | EXAMPLE / OPTIONAL_RUNTIME |
| `DRAMA_PLUGIN_PROVIDER_ASSET_MODE` | loader.py:22-24 | asset provider；默认 `mock` | optional / NO | runtime / neutral | EXAMPLE / OPTIONAL_RUNTIME |
| `DRAMA_PLUGIN_PROVIDER_RESEARCH_MODE` | loader.py:22-24 | research provider；默认 `mock` | optional / NO | runtime / neutral | EXAMPLE / OPTIONAL_RUNTIME |
| `DRAMA_PLUGIN_PROVIDER_PRODUCTION_MODE` | loader.py:22-24 | production provider；默认 `mock` | optional / NO | runtime / neutral | EXAMPLE / OPTIONAL_RUNTIME |
| `DRAMA_PLUGIN_PROVIDER_MEDIA_MODE` | loader.py:22-24 | media provider；默认 `mock` | optional / NO | runtime / neutral | EXAMPLE / OPTIONAL_RUNTIME |
| `DRAMA_PLUGIN_PROVIDER_CONTEXT_MODE` | loader.py:22-24 | context provider；默认 `local` | optional / NO | runtime / neutral | EXAMPLE / OPTIONAL_RUNTIME |
| `DRAMA_PLUGIN_PROVIDER_SPEECH_MODE` | loader.py:42-46 | `disabled/openai/bailian_qwen`；默认 `disabled` | optional / NO | runtime / neutral selector | EXAMPLE / OPTIONAL_RUNTIME |
| `DRAMA_PLUGIN_SERVICE_MEMORY_BASE_URL` | loader.py:25-28 | memory HTTP base URL；默认空 | conditional / NO | runtime / neutral | EXAMPLE / REQUIRED_RUNTIME when HTTP |
| `DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN` | loader.py:25-30 | memory Bearer token；默认空 | conditional / YES | runtime / neutral | EXAMPLE / SECRET |
| `DRAMA_PLUGIN_SERVICE_MEMORY_TIMEOUT_SECONDS` | loader.py:25-35 | timeout；默认 `10` | optional / NO | runtime / neutral | ROOT-ONLY / USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_ASSET_BASE_URL` | loader.py:25-28 | asset HTTP base URL；默认空 | conditional / NO | runtime / neutral | EXAMPLE / REQUIRED_RUNTIME when HTTP |
| `DRAMA_PLUGIN_SERVICE_ASSET_API_TOKEN` | loader.py:25-30 | asset Bearer token；默认空 | conditional / YES | runtime / neutral | EXAMPLE / SECRET |
| `DRAMA_PLUGIN_SERVICE_ASSET_TIMEOUT_SECONDS` | loader.py:25-35 | timeout；默认 `10` | optional / NO | runtime / neutral | ROOT-ONLY / USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_RESEARCH_BASE_URL` | loader.py:25-28 | research HTTP base URL；默认空 | conditional / NO | runtime / neutral | ROOT-ONLY / USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_RESEARCH_API_TOKEN` | loader.py:25-30 | research Bearer token；默认空 | conditional / YES | runtime / neutral | ROOT-ONLY / SECRET + USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_RESEARCH_TIMEOUT_SECONDS` | loader.py:25-35 | timeout；默认 `10` | optional / NO | runtime / neutral | ROOT-ONLY / USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_PRODUCTION_BASE_URL` | loader.py:25-28 | production HTTP base URL；默认空 | conditional / NO | runtime / neutral | ROOT-ONLY / USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_PRODUCTION_API_TOKEN` | loader.py:25-30 | production Bearer token；默认空 | conditional / YES | runtime / neutral | ROOT-ONLY / SECRET + USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_PRODUCTION_TIMEOUT_SECONDS` | loader.py:25-35 | timeout；默认 `30` | optional / NO | runtime / neutral | ROOT-ONLY / USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_MEDIA_BASE_URL` | loader.py:25-28 | media HTTP base URL；默认空 | conditional / NO | runtime / neutral | EXAMPLE / REQUIRED_RUNTIME when HTTP |
| `DRAMA_PLUGIN_SERVICE_MEDIA_API_TOKEN` | loader.py:25-30 | media Bearer token；默认空 | conditional / YES | runtime / neutral | EXAMPLE / SECRET |
| `DRAMA_PLUGIN_SERVICE_MEDIA_TIMEOUT_SECONDS` | loader.py:25-35 | timeout；默认 `10` | optional / NO | runtime / neutral | ROOT-ONLY / USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_CONTEXT_BASE_URL` | loader.py:25-28 | context HTTP base URL；默认空 | conditional / NO | runtime / neutral | ROOT-ONLY / USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_CONTEXT_API_TOKEN` | loader.py:25-30 | context Bearer token；默认空 | conditional / YES | runtime / neutral | ROOT-ONLY / SECRET + USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_CONTEXT_TIMEOUT_SECONDS` | loader.py:25-35 | timeout；默认 `30` | optional / NO | runtime / neutral | ROOT-ONLY / USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_SPEECH_BASE_URL` | loader.py:48-50 | OpenAI-compatible legacy/general base URL；默认模型值为 OpenAI official URL | optional / NO | runtime / OpenAI-specific in effect | HISTORICAL + ROOT-ONLY / USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_SERVICE_SPEECH_OPENAI_BASE_URL` | loader.py:51-52 | 覆盖上项；默认 OpenAI official URL | optional / NO | runtime / OpenAI | EXAMPLE / PROVIDER_SPECIFIC |
| `DRAMA_PLUGIN_SERVICE_SPEECH_BAILIAN_BASE_URL` | loader.py:53-54 | Bailian endpoint；默认 DashScope official URL | optional / NO | runtime / Bailian Qwen | EXAMPLE / PROVIDER_SPECIFIC |
| `OPENAI_API_KEY` | loader.py:55-56；MCP 亦消费 | OpenAI credential；默认空 | conditional / YES | runtime + live-E2E / OpenAI | EXAMPLE / SECRET + PROVIDER_SPECIFIC |
| `DASHSCOPE_API_KEY` | loader.py:57-58 | DashScope credential；默认空 | conditional / YES | runtime + live-E2E / Bailian Qwen | EXAMPLE / SECRET + PROVIDER_SPECIFIC |
| `DRAMA_PLUGIN_SERVICE_SPEECH_OUTPUT_DIRECTORY` | loader.py:59-60；plugin.py:96-100 | real speech 本地输出目录；默认空 | conditional / NO | runtime / speech-neutral | EXAMPLE / REQUIRED_RUNTIME when speech enabled |
| `DRAMA_PLUGIN_SERVICE_SPEECH_TIMEOUT_SECONDS` | loader.py:61-65 | timeout；默认 `30` | optional / NO | runtime / speech-neutral | EXAMPLE / OPTIONAL_RUNTIME |
| `DRAMA_PLUGIN_SERVICE_SPEECH_MAX_TRANSIENT_RETRIES` | loader.py:66-70 | retry；默认 `2`，允许 `0..2` | optional / NO | runtime / speech-neutral | EXAMPLE / OPTIONAL_RUNTIME |
| `DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS` | media_source.py:28-31 | `file://` import allowlist；默认空并拒绝 local import | conditional / NO | runtime / neutral | EXAMPLE / REQUIRED_RUNTIME for local import |
| `DRAMA_TOOL_SECRET` | run_batch7_1_media_roundtrip.py:106-117；Java 亦消费 | media round-trip Bearer secret | test conditional / YES | integration / neutral | service EXAMPLE / SECRET + TEST_ONLY |
| `DRAMA_MCP_URL` | run_batch6_0r_text_regression.py:18；run_batch6_0re2e_text_regression.py:20 | MCP endpoint；默认 loopback `8765/mcp` | optional / NO | integration / neutral | ROOT-ONLY / USED_BUT_UNDOCUMENTED |
| `DRAMA_E2E_PREFIX_FAMILY` | run_drama_service_e2e.py:46-48 | E2E data prefix family；有固定测试默认 | optional / NO | integration test / neutral | ROOT-ONLY / TEST_ONLY + USED_BUT_UNDOCUMENTED |
| `DRAMA_PLUGIN_REAL_TTS_E2E` | run_batch7_2_preflight.py:134-147 | OpenAI Batch 7.2 gate；默认 false | conditional / NO | live-E2E / OpenAI | HISTORICAL + ROOT-ONLY / LIVE_E2E_ONLY |
| `REAL_TTS_E2E` | run_batch7_2r_preflight.py:155-175 | Bailian Batch 7.2R gate；默认 false | conditional / NO | live-E2E / Bailian Qwen | EXAMPLE / LIVE_E2E_ONLY |
| `BATCH72R_QWEN_MODEL` | run_batch7_2r_preflight.py:133-135 | 仅 preflight model override；有 Qwen 默认 | optional / NO | live-E2E / Bailian Qwen | ROOT-ONLY / LIVE_E2E_ONLY + USED_BUT_UNDOCUMENTED |

### 3.2 drama-mcp-service variables

| Exact variable | Consumer / source | Description and default | Required / sensitive | Scope / provider | Documentation / class |
|---|---|---|---|---|---|
| `OPENAI_API_KEY` | examples/minimal_run.py:14-15；tests/test_live_openai_e2e.py:14-16；OpenAI Agents SDK | live run credential；默认空/测试 skip | conditional / YES | development + live-E2E / OpenAI | EXAMPLE / SECRET + PROVIDER_SPECIFIC |
| `HARNESS_MODEL` | examples/minimal_run.py:19；tests/test_live_openai_e2e.py:29-30 | SDK model；默认 `gpt-5-mini` | optional / NO | development + live-E2E / OpenAI | EXAMPLE / PROVIDER_SPECIFIC |

当前该仓库实际是 Harness runtime；没有代码读取 MCP auth、Plugin URL、Drama Service URL 或独立 `MCP_*` 变量。不要根据仓库名推断不存在的配置项。

### 3.3 drama-service variables

| Exact variable | Consumer / source | Description and default | Required / sensitive | Scope / provider | Documentation / class |
|---|---|---|---|---|---|
| `DB_HOST` | application.yml:6 | MySQL host；当前代码默认 `REDACTED` | operational required / NO | runtime / MySQL | EXAMPLE / REQUIRED_RUNTIME |
| `DB_PORT` | application.yml:6 | MySQL port；默认 `3306` | optional / NO | runtime / MySQL | EXAMPLE / PROVIDER_SPECIFIC |
| `DB_NAME` | application.yml:6 | database；默认 `drama` | optional / NO | runtime / MySQL | EXAMPLE / PROVIDER_SPECIFIC |
| `DB_USERNAME` | application.yml:7 | database user；当前代码默认 `REDACTED` | operational required / YES | runtime / MySQL | EXAMPLE / SECRET |
| `DB_PASSWORD` | application.yml:8 | database password；当前代码默认 `REDACTED` | operational required / YES | runtime / MySQL | EXAMPLE / SECRET |
| `DRAMA_MEDIA_MAX_FILE_SIZE` | application.yml:14 | multipart file limit；默认 `1GB` | optional / NO | runtime / neutral | EXAMPLE / OPTIONAL_RUNTIME |
| `DRAMA_MEDIA_MAX_REQUEST_SIZE` | application.yml:15 | multipart request limit；默认 `1GB` | optional / NO | runtime / neutral | EXAMPLE / OPTIONAL_RUNTIME |
| `SERVER_PORT` | application.yml:18 | backend port；默认 `8080` | optional / NO | runtime / neutral | README, not EXAMPLE / USED_BUT_UNDOCUMENTED |
| `DRAMA_TOOL_SECRET` | application.yml:31；ToolSecretInterceptor.java:21 | `/api/tool/**` Bearer secret；当前代码默认 `REDACTED` | operational required / YES | runtime / neutral | EXAMPLE / SECRET + REQUIRED_RUNTIME |
| `DRAMA_MEDIA_STORAGE_ENDPOINT` | application.yml:34 | S3-compatible endpoint；默认 loopback | media conditional / NO | runtime / S3-compatible | EXAMPLE / PROVIDER_SPECIFIC |
| `DRAMA_MEDIA_STORAGE_BUCKET` | application.yml:35 | object bucket；默认 `drama-media` | media conditional / NO | runtime / S3-compatible | EXAMPLE / PROVIDER_SPECIFIC |
| `DRAMA_MEDIA_STORAGE_ACCESS_KEY` | application.yml:36 | storage access key；当前代码默认 `REDACTED` | media conditional / YES | runtime / S3-compatible | EXAMPLE / SECRET + PROVIDER_SPECIFIC |
| `DRAMA_MEDIA_STORAGE_SECRET_KEY` | application.yml:37 | storage secret；当前代码默认 `REDACTED` | media conditional / YES | runtime / S3-compatible | EXAMPLE / SECRET + PROVIDER_SPECIFIC |
| `DRAMA_MEDIA_STORAGE_REGION` | application.yml:38 | region；YAML 默认与 Java fallback 不一致 | optional / NO | runtime / S3-compatible | EXAMPLE / PROVIDER_SPECIFIC |
| `DRAMA_MEDIA_RESOLVE_TTL_SECONDS` | application.yml:39 | signed URL TTL；默认 `900` | optional / NO | runtime / S3-compatible | EXAMPLE / OPTIONAL_RUNTIME |
| `CORS_ALLOWED_ORIGINS` | application.yml:41；WebConfig.java:18 | trusted frontend origins；默认 loopback frontend | optional / NO | runtime / neutral | EXAMPLE / OPTIONAL_RUNTIME |
| `VITE_API_BASE_URL` | web/src/api/http.ts:7 | frontend API base；默认 same-origin empty string | optional / NO | development/runtime build / neutral | ROOT-ONLY / DEVELOPMENT_ONLY + USED_BUT_UNDOCUMENTED |

## 4. Required runtime variables

默认 `drama-plugin` 使用 mock/local/disabled，因此 **零环境变量即可构造默认 Plugin**。一旦选择 HTTP provider，则对应 `*_BASE_URL` 与 `*_API_TOKEN` 条件必需；一旦启用 speech，则 output directory 与选中 Provider credential 条件必需。

`drama-service` 默认 profile 实际依赖 MySQL。安全的新 Host 应显式提供 `DB_HOST`、`DB_USERNAME`、`DB_PASSWORD` 与强随机 `DRAMA_TOOL_SECRET`，不要接受当前 hard-coded fallback。`DB_PORT`、`DB_NAME` 可采用明确的本地默认。对象存储相关变量在使用 media import/resolve 时为一组条件必需配置。

## 5. Optional variables

可选项主要是端口、timeout、retry、CORS、multipart limit、storage region/TTL、Vite API base、Harness model、MCP URL 与 E2E prefix。默认值已写入 workspace `.env.example`；secret 字段保持空白。

## 6. Secret variables

以下名称必须按 secret 管理，值不得进入 Git、报告、日志或前端：

- `OPENAI_API_KEY`
- `DASHSCOPE_API_KEY`
- `DB_USERNAME`（按本 workspace 的敏感配置策略处理）
- `DB_PASSWORD`
- `DRAMA_TOOL_SECRET`
- `DRAMA_MEDIA_STORAGE_ACCESS_KEY`
- `DRAMA_MEDIA_STORAGE_SECRET_KEY`
- 所有 `DRAMA_PLUGIN_SERVICE_{MEMORY,ASSET,RESEARCH,PRODUCTION,MEDIA,CONTEXT}_API_TOKEN`

审计 process environment 的 `CORE`、`SPEECH_OPENAI`、`SPEECH_BAILIAN`、`REAL_TTS_E2E` profiles 均只输出了 `UNSET`，未输出 value。

## 7. Provider-specific variables

Host-level Speech Provider configuration：

- 选择器：`DRAMA_PLUGIN_PROVIDER_SPEECH_MODE`
- OpenAI：`OPENAI_API_KEY`、`DRAMA_PLUGIN_SERVICE_SPEECH_OPENAI_BASE_URL`
- Bailian Qwen：`DASHSCOPE_API_KEY`、`DRAMA_PLUGIN_SERVICE_SPEECH_BAILIAN_BASE_URL`
- provider-neutral：speech output directory、timeout、retry

`Work.content.voiceProfiles[].providerMappings` 中的 `provider`、`model`、`voiceId` 与 material parameters 是 Work 级 Provider Mapping，不是 Host secret。生产 runtime 不应新增全局 `QWEN_MODEL`/`VOICE_ID` 来替代它们。现存 `BATCH72R_QWEN_MODEL` 仅是 live preflight 的测试 override，已明确归入 `LIVE_E2E_ONLY`，不作为推荐生产配置。

## 8. Live E2E / test-only variables

- `DRAMA_PLUGIN_REAL_TTS_E2E`：旧 OpenAI preflight gate。
- `REAL_TTS_E2E`：当前 Bailian Qwen preflight gate。
- `BATCH72R_QWEN_MODEL`：Batch 7.2R preflight-only。
- `DRAMA_E2E_PREFIX_FAMILY`：Drama Service integration data prefix。
- `DRAMA_MCP_URL`：text regression MCP endpoint。
- `DRAMA_TOOL_SECRET`：同时是 service runtime secret；在 round-trip script 中为 test input。
- `OPENAI_API_KEY`、`DASHSCOPE_API_KEY`：同时是 runtime credentials；live tests 只检查是否非空。

两个 Real TTS gate 是同义漂移，但仍被不同脚本实际读取。本次只报告并在 workspace example 中都设为 `false`，没有自动统一代码。

## 9. USED_BUT_UNDOCUMENTED

相对于各项目原有 `.env.example`，以下 active reads 缺失：

- Plugin：所有六个 `*_TIMEOUT_SECONDS`；research/production/context 的 `BASE_URL` 与 `API_TOKEN`；`DRAMA_PLUGIN_SERVICE_SPEECH_BASE_URL`；`DRAMA_MCP_URL`；`DRAMA_E2E_PREFIX_FAMILY`；`DRAMA_PLUGIN_REAL_TTS_E2E`；`BATCH72R_QWEN_MODEL`。
- Service：`SERVER_PORT`（README 有，但 `.env.example` 缺失）；`VITE_API_BASE_URL`（README 和 `.env.example` 均缺失）。
- MCP/Harness：无；两个 active name 都在其 `.env.example`。

本次 workspace `.env.example` 已覆盖上述变量，但没有改写各仓库自身 example，保持独立仓库能力和用户现有改动。

## 10. DOCUMENTED_BUT_UNUSED

三个当前项目 `.env.example` 内的变量名全部存在实际 consumer，未发现 `DOCUMENTED_BUT_UNUSED`。

旧报告或外部 Host 集成文档出现的词不自动构成当前代码变量。例如 `OPENAI_BASE_URL` 只作为更长变量名的子串出现，当前仓库代码没有独立读取它。

## 11. LEGACY_UNUSED

- `DRAMA_PLUGIN_PROVIDER_PROJECT_MODE`：只见于旧历史报告，当前 loader 的 `_SERVICE_NAMES` 没有 `project`，代码不读取。
- `COMFY_API_KEY`：只见于旧 Comfy Cloud 执行报告；当前三个工程 runtime 没有读取点，且 Comfy Cloud 属于外部 Host integration，不纳入 workspace runtime `.env`。
- 文档中的大量 `MINIO_*`、`MYSQL_*`、`REAL_*` 大写结果标签是报告状态或概念名，不是 environment reads；实际代码分别使用 `DRAMA_MEDIA_STORAGE_*`、`DB_*` 和上表明确列出的 E2E gates。

## 12. Configuration drift and duplicate meanings

1. Speech OpenAI base URL 同时支持 `DRAMA_PLUGIN_SERVICE_SPEECH_BASE_URL` 与 `DRAMA_PLUGIN_SERVICE_SPEECH_OPENAI_BASE_URL`，后者覆盖前者。两者含义重叠；暂不自动删除兼容字段。
2. Real TTS gate 有 `DRAMA_PLUGIN_REAL_TTS_E2E` 与 `REAL_TTS_E2E` 两个 active name；应在后续独立低风险变更中统一，并保留一段兼容迁移期。
3. Plugin 对 memory/asset/media 分别使用独立 token，而 Java 端只有一个 `DRAMA_TOOL_SECRET`。当前 integration contract 要求三者取同一 secret。这是跨进程映射，不是可直接删掉的重复变量。
4. MCP regression URL 使用 `DRAMA_MCP_URL`，而 `plugin/.mcp.json` 写死同一 loopback endpoint；前者只影响脚本，后者只影响 Host config。
5. `DRAMA_MEDIA_STORAGE_REGION` 的 YAML 默认与 `MediaStorageProperties` 的 Java null fallback 不一致，应在后续修复中选定一个规范默认。

## 13. Hard-coded configuration findings

| Severity | Location | Finding |
|---|---|---|
| CRITICAL | drama-service application.yml:8 | database password-like fallback = `REDACTED` |
| CRITICAL | drama-service application.yml:31 | tool Bearer secret fallback = `REDACTED` |
| CRITICAL | drama-service application.yml:36-37 | object-storage access/secret fallback = `REDACTED` |
| HIGH | drama-service application.yml:6-7 | old Host-specific database endpoint/user fallback = `REDACTED` |
| MEDIUM | plugin/.mcp.json:5；integration scripts | loopback MCP URL hard-coded/defaulted；可接受开发默认，但需要 Host override |
| INFO | tests | `.invalid` URLs、test-only secret strings、fixture `/Users/test`/Windows paths均为隔离测试数据，不是 runtime defaults |

这些 credential-like defaults 没有在本次任务中修改，因为 `application.yml` 已有用户未提交改动，且移除默认值会改变启动行为，超出“轻量 consolidation”的安全边界。建议在单独变更中改为无默认的 `${VAR}` 或空值 fail-closed，并立即轮换任何可能曾真实使用的凭据。

## 14. `.env` automatic loading status

```text
PLUGIN_ENV_FILE_AUTO_LOAD = NO
MCP_ENV_FILE_AUTO_LOAD = NO
SERVICE_ENV_FILE_AUTO_LOAD = NO
```

`.env.example` 只是模板；三个 backend/runtime 都依赖启动进程已经具有相应 environment。Vite 子项目的框架级 `.env*` 行为不改变上述结论：它的默认目录是 `drama-service/web`，且只向客户端暴露 `VITE_*`。

## 15. Workspace `.env` recommendation and implementation

推荐模型：

```text
historical-plugin/
├── .env                 # local only；不提交；本次未创建
├── .env.example         # 聚合层；names/defaults/comments only
└── scripts/
    ├── load-env.sh      # source 到当前 shell
    └── check-env.sh     # 只输出 NAME=SET/UNSET
```

workspace root 本身不是 Git managed；三个子目录是独立 Git repository。因此 root aggregation files 当前不会自动被任何一个子仓库提交。若未来将 root 初始化为 Git repo，必须先加入 root `.gitignore`：`.env`。

三个子仓库当前 `.gitignore` 都已有 `.env` 规则；三个既有 `.env.example` 均保留。workspace example 是 local-host aggregation layer，不替代项目级模板。

## 16. macOS shell import behavior

推荐命令：

```sh
cp .env.example .env
# 编辑 .env，填入本机值；不要提交
source scripts/load-env.sh
./scripts/check-env.sh CORE
```

`load-env.sh`：

- 相对脚本位置解析 workspace root；不依赖当前工作目录。
- 缺少 `.env` 时明确失败。
- 使用 shell parser，因此支持 comments、blank lines、quoted values、引号内 spaces；前提是 `.env` 使用 shell-compatible syntax。
- 通过 `set -a` export assignments，并恢复调用前的 allexport 状态。
- 不打印任何变量 value。
- 必须被 `source`；直接执行会明确失败，因为子 shell 的 export 无法反向改变父 shell。

`source scripts/load-env.sh` 只影响 **当前 shell 和其后启动的 child processes**。关闭 shell 后不会永久保存，也不会自动改变其他 Terminal 窗口或所有 macOS GUI applications。

## 17. GUI / CLI inheritance note

- CLI-launched Host：先 `source scripts/load-env.sh`，随后从同一 shell 启动 IDE、Codex Host、Python、Maven 或 npm；child process 会继承 environment。
- GUI-launched Host：从 Finder/Dock 启动时通常不会继承某个 Terminal session 里后续 `source` 的 environment。
- GUI/IDE 推荐优先顺序：IDE Run Configuration env file；workspace launcher script；Host 明确提供的 env-file 配置。
- 不推荐把大量 secrets 永久写入 macOS 全局 `launchctl setenv` 作为默认开发方案。

当前 workspace 静态文件无法证明已运行的 Codex GUI Host 继承了哪个 Terminal 环境；本次检查针对当前审计 process，相关 profiles 均为 `UNSET`。

## 18. Environment checker

支持：

```sh
./scripts/check-env.sh CORE
./scripts/check-env.sh SPEECH_OPENAI
./scripts/check-env.sh SPEECH_BAILIAN
./scripts/check-env.sh REAL_TTS_E2E
```

输出严格为 `VARIABLE_NAME=SET` 或 `VARIABLE_NAME=UNSET`，空字符串按 `UNSET` 处理；不输出 value。

## 19. Migration checklist for a new Mac

1. 将完整 workspace 迁移到新 Host，保持三个子仓库相对位置不变。
2. 确认所需 Python、Java 17、Maven、Node/npm 与外部 MySQL/S3-compatible services 已由用户批准并安装。
3. 在 workspace root 执行 `cp .env.example .env`。
4. 只在 local `.env` 填写 secrets；禁止复制旧 Host 的 credential-like defaults。
5. 为数据库、tool auth、object storage、OpenAI/DashScope 使用新 Host 独立凭据；轮换任何可能曾暴露于 tracked config 的旧凭据。
6. 设置真实的 `DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS`；不得沿用旧 `/Users/<name>/...` 或 Windows drive path。
7. 若只开发 mock Plugin，保持 `speech=disabled`、其他 provider 为 mock/local，所有 real-E2E gate 为 false。
8. 若接入 Drama Service，按启用的 domain 设置对应 mode/base URL/API token；确认三个 Plugin token 与 Java `DRAMA_TOOL_SECRET` 的现行 contract。
9. 执行 `source scripts/load-env.sh`，再运行相应 `check-env.sh` profile。
10. 从同一 shell 启动 CLI Host；GUI Host 则配置 IDE/Host env file 或 launcher。
11. 在任何 live test 前单独人工确认 gate、credential、endpoint 与成本；本审计没有执行 live test。
12. 修复 `application.yml` 的 hard-coded defaults 后，再将 `ENVIRONMENT_AUDIT` 重新评估为 PASS。

## 20. Final status

```text
ENVIRONMENT_AUDIT = FAIL
COMPLETE_ENV_INVENTORY = YES

PLUGIN_ENV_FILE_AUTO_LOAD = NO
MCP_ENV_FILE_AUTO_LOAD = NO
SERVICE_ENV_FILE_AUTO_LOAD = NO

WORKSPACE_ENV_RECOMMENDED = YES
WORKSPACE_ENV_EXAMPLE_CREATED = YES
LOAD_ENV_SCRIPT_CREATED = YES
CHECK_ENV_SCRIPT_CREATED = YES

REAL_SECRET_VALUES_IN_REPORT = 0
REAL_PROVIDER_CALLS = 0
COMFY_CLOUD_USAGE = 0
```
