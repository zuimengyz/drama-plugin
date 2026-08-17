# Batch 5.1RR — Comfy Cloud Output Fetch Recovery 执行报告

> 执行日期：2026-08-17  
> 报告编号：27  
> 最终状态：`BLOCKED`  
> 唯一阻断：`storage.googleapis.com` 在宿主批准网络下 TCP 443 已连接，但 TLS 握手被提前关闭（unexpected EOF / `SSL_ERROR_SYSCALL`）

## 1. 执行摘要

本轮严格复用了两个既有 Comfy Cloud job，没有调用任何生成工具，也没有开始三个正式 Shot。两个 job 均重新确认 `completed`，两个 `get_output` 均成功返回新鲜短链和下载命令；宿主 Shell 随后原样执行 MCP 返回的原子下载命令。

两次下载均成功访问 Comfy 短链，但重定向至 `storage.googleapis.com` 后在 TLS 握手阶段失败。普通 workspace sandbox 在 DNS/socket 层即失败；一次性批准网络下，DNS 和 TCP 443 均通过，但 GCS TLS 仍收到 unexpected EOF。macOS 当前 HTTP、HTTPS、SOCKS 系统代理均已启用；显式复用这些现有代理通道后，GCS TLS 仍失败。因此没有证据支持修改 Codex `config.toml`，也没有创建持久的危险权限。

未获得任何真实输出字节，故无法执行文件解码、真实 Visual Review、Media import、MinIO 回读或 Reference Asset 持久化。没有把 `job completed` 冒充 Review PASS。

## 2. 前置事实回归

```text
formal MinIO endpoint = 192.168.1.86:9000
formal MinIO health = HTTP 200
Drama Java service = READY on 127.0.0.1:8080
Drama MCP health = HTTP 200 on 127.0.0.1:8765
Comfy Cloud MCP = enabled; OAuth re-login completed after refresh-token rotation conflict

Character job 4296e4df-4f34-4365-8cba-52071f437ed9 = completed
Scene job ed74b5cd-9e45-4f12-beec-714f40535947 = completed
```

正式 MinIO 仅做轻量健康回归，没有重新审计前序对象恢复。

## 3. Codex 权限模型

```text
Codex version = codex-cli 0.148.0-alpha.9
OS = macOS 26.5 arm64
Shell = /bin/zsh
HOME = /Users/yizhao
CODEX_HOME = /Users/yizhao/.codex
user config = /Users/yizhao/.codex/config.toml
project config = ABSENT
runtime permission profile = managed workspace-write
managed requirements.toml = NOT_FOUND
legacy sandbox config in user config = NOT_CONFIGURED
permission profiles in user config = NOT_CONFIGURED
config.toml modified = NO
config backup = NOT_REQUIRED
restart required = NO
```

当前 App runtime 明确使用 managed permission profile；用户配置中没有可安全合并的 legacy network_access 或 permission profile。更关键的是，一次性批准网络仍不能完成 GCS TLS，因此不修改 Codex 配置。

## 4. 网络诊断

| 检查 | 普通 workspace sandbox | 一次性批准网络 |
| --- | --- | --- |
| `cloud.comfy.org` DNS | FAIL：sandbox socket/DNS denied | PASS |
| `cloud.comfy.org` TCP/TLS/HTTP | 未到达 | PASS，HTTP 200 |
| `storage.googleapis.com` DNS | FAIL：sandbox socket/DNS denied | PASS |
| `storage.googleapis.com` TCP 443 | 未到达 | PASS |
| `storage.googleapis.com` TLS | 未到达 | FAIL：unexpected EOF / `SSL_ERROR_SYSCALL` |
| `storage.googleapis.com` HTTP | 未到达 | FAIL：TLS 前停止 |

其他脱敏事实：

```text
curl = 8.7.1
TLS backend = SecureTransport / LibreSSL 3.3.6
system time = 2026-08-17T14:33:18+0800
HTTP_PROXY = ABSENT
HTTPS_PROXY = ABSENT
ALL_PROXY = ABSENT
NO_PROXY = ABSENT
macOS HTTP proxy = ENABLED
macOS HTTPS proxy = ENABLED
macOS SOCKS proxy = ENABLED
explicit current HTTP/HTTPS/SOCKS proxy tests = GCS TLS FAIL
Comfy shortlink hostname = cloud.comfy.org
output storage hostname = storage.googleapis.com
```

没有记录代理地址、代理凭据、签名 URL、OAuth Token、Cookie 或 Authorization Header。

诊断：

```text
NORMAL_SANDBOX_NETWORK = FAIL_AT_DNS_SOCKET
APPROVED_NETWORK = PARTIAL（DNS/TCP PASS；GCS TLS FAIL）
ROOT_CAUSE = OUTPUT_STORAGE_EGRESS_POLICY
HOST_EGRESS_TO_GCS = BLOCKED
```

## 5. 实际修复

已执行的最小、可逆操作：

1. 对相同域名申请一次性受控网络权限，而非持久开放全局网络。
2. 在不打印地址或凭据的前提下，复用 macOS 当前已启用的 HTTP、HTTPS、SOCKS 代理分别测试 GCS。
3. Comfy OAuth 因并发状态读取触发 `invalid_grant: refresh token reuse detected` 后，执行一次官方 `codex mcp login comfy-cloud`；重新登录成功，随后所有 Comfy 调用改为顺序执行。
4. 重新获取每个 job 的新鲜 `get_output`，没有复用 26 号报告中的旧 URL。
5. 对每个 job 原样执行 MCP 返回的下载命令；命令自身的 `.part` 清理成功，没有留下伪造或空 artifact。

未修改 `config.toml`：批准网络和现有系统代理均在同一 GCS TLS 层失败，持久修改 Codex sandbox 配置不会解决宿主出口策略。

## 6. Existing Job Recovery

### Character Master — 李陵

```text
jobId = 4296e4df-4f34-4365-8cba-52071f437ed9
terminal status = completed
get_output = PASS（新鲜短链与命令）
download command = EXECUTED VERBATIM
shortlink reachability = PASS
redirect storage hostname = storage.googleapis.com
download result = FAIL_AT_TLS
local artifact = NOT_CREATED
MIME = NOT_AVAILABLE
size = NOT_AVAILABLE
dimensions = NOT_AVAILABLE
SHA-256 = NOT_AVAILABLE
```

### Scene Master — 穹庐

```text
jobId = ed74b5cd-9e45-4f12-beec-714f40535947
terminal status = completed
get_output = PASS（新鲜短链与命令）
download command = EXECUTED VERBATIM
shortlink reachability = PASS
redirect storage hostname = storage.googleapis.com
download result = FAIL_AT_TLS
local artifact = NOT_CREATED
MIME = NOT_AVAILABLE
size = NOT_AVAILABLE
dimensions = NOT_AVAILABLE
SHA-256 = NOT_AVAILABLE
```

没有提交新 Provider job。

## 7. Visual Review

两个输出均未取得实际字节，故不能解码或打开图片：

```text
CHARACTER_VISUAL_REVIEW = NOT_RUN
SCENE_VISUAL_REVIEW = NOT_RUN
```

`job completed != visual review pass`。本轮没有把 Provider metadata、文件名或 Prompt 当作视觉证据。

## 8. Media Persistence

allowed root 已确认：

```text
DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS = /Users/yizhao/PyProject/historical_plugin
target artifact directory = plugin/docs/reports/artifacts/batch5-1rr/
allowed-root relationship = PASS
```

由于没有本地文件：

```text
Character media.import_media = BLOCKED
Scene media.import_media = BLOCKED
media.resolve_media for recovered outputs = NOT_RUN
provider local SHA-256 = NOT_AVAILABLE
import source SHA-256 = NOT_AVAILABLE
resolved stable SHA-256 = NOT_AVAILABLE
MEDIA_BYTE_EQUALITY = NOT_RUN
```

没有把临时 URL 直接传入 `media.import_media`。

## 9. Asset Persistence

未通过 Visual Review，因此没有创建或保存稳定 Reference Asset：

```text
Character asset search/create = NOT_RUN_AFTER_FETCH_BLOCK
Scene asset search/create = NOT_RUN_AFTER_FETCH_BLOCK
Character assetId/mediaId = NOT_CREATED
Scene assetId/mediaId = NOT_CREATED
```

bootstrap Media `media_f1048149fd0f485c822481f91ea6a894` 未修改、未改 purpose、未重新分类。

## 10. Changed Files

| 文件 | 原因 | 源码 |
| --- | --- | --- |
| `plugin/docs/reports/27-Batch-5.1RR-Comfy-Cloud-Output-Fetch-Recovery-执行报告.md` | 新增本批正式报告 | NO |

创建了运行目录 `plugin/docs/reports/artifacts/batch5-1rr/.partial/`，但下载命令失败并清理临时文件，目录中没有输出 artifact。

没有修改 Drama Plugin、historical Skill、Drama MCP、Java、数据库 schema、项目 `.env`、项目 `.mcp.json` 或 Codex 配置。

## 11. Remaining Blocker

唯一精确阻断：

```text
storage.googleapis.com:
  DNS = PASS under approved network
  TCP 443 = PASS under approved network
  TLS handshake = FAIL, peer/path closes before certificate exchange
  curl = LibreSSL SSL_connect: SSL_ERROR_SYSCALL
  openssl = unexpected EOF while reading
```

所需最小外部变化：宿主代理/VPN/防火墙出口策略允许 `storage.googleapis.com:443` 完成 TLS 握手。不是开放全局网络，也不是修改 Drama 或 Codex 业务代码。

```text
SOURCE_CODE_ROOT_CAUSE_DISCOVERED = NO
```

## 12. 统一验收字段

```text
FORMAL_OBJECT_STORAGE_REGRESSION = PASS

CHARACTER_EXISTING_JOB_REUSED = YES
SCENE_EXISTING_JOB_REUSED = YES

NEW_CHARACTER_JOB_SUBMITTED = NO
NEW_SCENE_JOB_SUBMITTED = NO
NEW_PROVIDER_JOB_SUBMITTED = NO

CODEX_PERMISSION_MODEL = MANAGED_POLICY
CODEX_SHELL_NETWORK_ACCESS = FAIL
COMFY_SHORTLINK_REACHABLE = PASS
GCS_DNS = PASS
GCS_TCP_443 = PASS
GCS_TLS = FAIL
GCS_HTTP_REACHED = FAIL

CHARACTER_GET_OUTPUT = PASS
SCENE_GET_OUTPUT = PASS

CHARACTER_OUTPUT_FETCH = FAIL
SCENE_OUTPUT_FETCH = FAIL
OUTPUT_FETCH_RECOVERY = BLOCKED

CHARACTER_FILE_DECODE = FAIL
SCENE_FILE_DECODE = FAIL

CHARACTER_VISUAL_REVIEW = NOT_RUN
SCENE_VISUAL_REVIEW = NOT_RUN

CHARACTER_MEDIA_IMPORT = BLOCKED
SCENE_MEDIA_IMPORT = BLOCKED

CHARACTER_REFERENCE_ASSET_PERSISTENCE = BLOCKED
SCENE_REFERENCE_ASSET_PERSISTENCE = BLOCKED

MEDIA_BYTE_EQUALITY = NOT_RUN
REFERENCE_REUSE_READY = NO

SHOT_GENERATION_STARTED = NO
SHOT_COUNT = 0

CUSTOM_WORKFLOW_CREATED = NO
SAVED_WORKFLOW_CREATED = NO
DYNAMIC_WORKFLOW_INTRODUCED = NO

DRAMA_PLUGIN_SOURCE_CHANGED = NO
HISTORICAL_SKILL_CHANGED = NO
DRAMA_MCP_CHANGED = NO
JAVA_CHANGED = NO
DATABASE_CHANGED = NO

CODEX_CONFIG_CHANGED = NO
CODEX_CONFIG_BACKUP = NOT_REQUIRED
RESTART_REQUIRED = NO
SECRET_EXPOSURE = NO

BATCH_5_1RR = BLOCKED
NEXT_BATCH_READY = NO
```
