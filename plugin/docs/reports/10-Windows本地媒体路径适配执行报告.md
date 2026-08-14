# 10-Windows 本地媒体路径适配执行报告

执行日期：2026-08-14

## 1. 执行摘要

本次在 Drama Plugin 的本地媒体入口增加了最小的 Windows `file://` URI 路径适配。Windows URI path 先通过 Python 标准库 `nturl2path.url2pathname()` 转换，再进入既有的 `Path.resolve()`、allowed-roots 校验和文件读取流程；macOS/Linux 继续使用原有的 URL decode 与 POSIX Path 语义。

未修改 Drama MCP Tool Contract、Java Media Service、MySQL、MinIO、Media 数据模型、`sourceRef`、`mediaId` 或 Signed URL 机制。

## 2. 原始问题

Windows 输入：

```text
file:///D:/home/AI/test.png
```

URI parser 产生的 path 是：

```text
/D:/home/AI/test.png
```

原实现直接执行：

```python
Path(unquote(parsed.path)).resolve(strict=False)
```

前导 `/` 未按 Windows file URI 规则转换，后续可能丢失 drive-absolute 语义，形成 `D:home\AI\test.png` 一类 drive-relative path，最终被 allowed-roots 拒绝。

## 3. 根因分析

问题不在 Java Media Service、对象存储或数据库，而在 Plugin 本地文件读取前的 URI-to-path 边界：URI path 是 URL 表示，不能在 Windows 上未经平台转换就直接作为本机路径解析。

原有 allowed-roots 判断使用 `Path.is_relative_to()`，不是字符串 `startswith()`，其目录边界语义正确。问题发生在候选路径进入安全判断之前，因此无需删除或绕过安全限制。

## 4. 修改文件

| 文件 | 修改内容 |
|---|---|
| `plugin/src/drama_plugin/providers/http/media_source.py` | 增加 Windows/POSIX file URI path 转换；提取原有相对目录安全判断以支持跨平台语义测试。 |
| `plugin/tests/test_media_import.py` | 增加 Windows 盘符、allowed root、越界、相似目录、POSIX 回归和 URL decode 测试。 |
| `plugin/docs/reports/10-Windows本地媒体路径适配执行报告.md` | 本报告。 |

## 5. 修改前后路径解析行为

| 平台 | 输入 | 修改前 | 修改后 |
|---|---|---|---|
| Windows | `file:///D:/home/AI/test.png` | `/D:/home/AI/test.png` 可能失去绝对盘符语义 | `D:\home\AI\test.png`，drive-absolute |
| Windows | `file:///D:/home/My%20Files/test.png` | 平台转换不完整 | `D:\home\My Files\test.png` |
| macOS | `file:///Users/test/AI/test.png` | `/Users/test/AI/test.png` | 不变 |
| Linux | `file:///home/test/AI/test.png` | `/home/test/AI/test.png` | 不变 |

## 6. Windows URI 处理方式

新增 `_file_uri_path()` 作为 URI path 到平台 PurePath 的薄适配层：

- Windows 使用标准库 `nturl2path.url2pathname()` 完成百分号解码、盘符前导斜杠移除和分隔符转换，并以 `PureWindowsPath` 保留 Windows 路径语义。
- macOS/Linux 继续使用 `unquote()` 和 `PurePosixPath`，不替换现有 POSIX 路径系统。
- 实际运行平台默认由 `os.name == "nt"` 决定；测试可以显式选择 Windows 语义，避免在 macOS 上错误使用宿主 `Path.resolve()` 模拟 Windows。
- 未扩大 UNC 支持范围。既有规则仍只接受空 hostname 或 `localhost`，`file://server/share/...` 仍不属于本次支持范围。

## 7. Allowed Roots 安全校验

候选路径和配置根目录仍在本机通过 `Path.resolve(strict=False)` canonicalize，随后使用 `Path.is_relative_to()` 判断目录包含关系。

验证结果：

| Root | Candidate | 结果 |
|---|---|---|
| `D:\home\AI` | `D:\home\AI\test.png` | PASS |
| `D:\home\AI` | `D:\other\test.png` | REJECT |
| `D:\home\AI` | `D:\home\AI-evil\test.png` | REJECT |

现有符号链接逃逸测试继续通过：候选符号链接 resolve 到 allowed root 外部时仍被拒绝。

## 8. 自动化测试结果

### 新增路径与安全用例

| 用例 | 结果 |
|---|---|
| CASE-01 Windows 标准盘符 URI | PASS |
| CASE-02 Windows allowed root | PASS |
| CASE-03 Windows 越界 | PASS（正确拒绝） |
| CASE-04 Windows 相似目录攻击 | PASS（正确拒绝） |
| CASE-05 macOS 路径回归 | PASS |
| CASE-06 Linux 路径回归 | PASS |
| CASE-07 URL encoded path | PASS |

### 命令结果

```text
Drama Plugin Media tests: 15 passed
Drama Plugin full tests:  60 passed
Drama Plugin mypy:        Success, 34 source files
Drama MCP Service tests:  13 passed
git diff --check:         PASS
```

## 9. macOS/Linux 回归结果

- 当前执行宿主为 macOS；现有真实临时文件读取、文件存在性、普通文件、可读性和符号链接逃逸测试全部通过。
- macOS 与 Linux 共用 POSIX 转换分支；`PurePosixPath` 分别验证 `/Users/test/AI/test.png` 和 `/home/test/AI/test.png` 保持不变。
- 未在 Linux 实机执行完整 E2E，因此这里只声明 POSIX 路径单测与现有测试回归通过。

## 10. 真实 E2E 结果

```text
WINDOWS_PATH_UNIT_TEST = PASS
WINDOWS_REAL_E2E = NOT_RUN
WINDOWS_MEDIA_IMPORT_E2E = NOT_RUN
WINDOWS_MEDIA_RESOLVE_E2E = NOT_RUN
WINDOWS_HASH_EQUALITY = NOT_RUN
```

原因：当前执行宿主是 macOS，不存在验收案例要求的 `D:\home\AI\test.png` Windows 文件系统；未伪造 Windows E2E 结果。本任务未重跑会写入 Java/MySQL/MinIO 的真实媒体 E2E。

## 11. 未修改范围

- Java Media Service 与 Java API Contract
- MySQL 与 MinIO 配置、持久化和对象存储逻辑
- Media Contract、数据模型与 import/resolve 业务语义
- MCP Tool 名称、输入输出 schema 与工具数量
- `sourceRef`、`mediaId` 与 Signed URL 机制
- Research、Production、Generation、ComfyUI
- `.env` 配置名称与 allowed-roots 安全要求

Java 工作区已有的 `application.yml` 本地 MinIO 配置改动属于用户原有改动，本次未触碰。

## 12. 遗留问题

- 需要在 Windows 实机使用真实存在的 `D:\home\AI\test.png` 重跑 Media Import、Resolve 和 bytes hash E2E，才能声明 Windows 真实链路通过。
- 标准 hostname UNC URI `file://server/share/test.png` 仍按既有策略拒绝；本次未扩大功能范围。

## 13. 最终验收结论

```text
WINDOWS_FILE_URI_PARSE = PASS
WINDOWS_DRIVE_ABSOLUTE_PATH = PASS
WINDOWS_ALLOWED_ROOT = PASS
WINDOWS_OUTSIDE_ROOT_REJECT = PASS
WINDOWS_PREFIX_ESCAPE_REJECT = PASS

MACOS_PATH_REGRESSION = PASS
LINUX_PATH_REGRESSION = PASS

MEDIA_EXISTING_TESTS = PASS
MCP_EXISTING_TESTS = PASS
JAVA_SERVICE_MODIFIED = NO
MEDIA_CONTRACT_MODIFIED = NO

WINDOWS_PATH_ADAPTER = PASS
WINDOWS_ALLOWED_ROOT_SECURITY = PASS
MACOS_REGRESSION = PASS
LINUX_REGRESSION = PASS
MCP_REGRESSION = PASS
MEDIA_REGRESSION = PASS
JAVA_SERVICE_UNCHANGED = PASS
```
