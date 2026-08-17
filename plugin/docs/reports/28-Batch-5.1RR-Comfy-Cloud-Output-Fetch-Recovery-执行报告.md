# Batch 5.1RR — Comfy Cloud Output Fetch Recovery 执行报告

> 执行日期：2026-08-17  
> 报告编号：28（不覆盖 27）  
> 最终状态：`PASS_WITH_REVIEW_REJECTION`

## 1. 执行摘要

用户将 `storage.googleapis.com` 绕过代理后，本轮继续复用 Batch 5.1 已完成的两个 Provider job，没有提交任何新生成任务。GCS 的 DNS、TCP 443、TLS 与 HTTP 均恢复；两个 `get_output` 均取得新鲜短链，Comfy MCP 返回的下载命令均由宿主 Shell 原样执行成功。

两个真实输出均完成 PNG magic bytes、MIME、解码、尺寸、字节数与 SHA-256 校验，并由 Agent 实际打开查看。人物和场景的主要视觉目标均成立，但两张图角落均没有规格要求检查的清晰身份标注。因此：输出获取恢复 PASS，两个 Visual Review 均 FAIL；按 5.1RR 规则保留审计 artifact，不导入正式 Reference Media，不创建稳定 Reference Asset，也不开始三个 Shot。

```text
OUTPUT_FETCH_RECOVERY = PASS
CHARACTER_VISUAL_REVIEW = FAIL
SCENE_VISUAL_REVIEW = FAIL
REFERENCE_PERSISTENCE = NOT_PERFORMED_REVIEW_REJECTED
BATCH_5_1RR = PASS_WITH_REVIEW_REJECTION
```

## 2. 前置事实回归

```text
formal MinIO = HTTP 200
Comfy Cloud MCP = enabled and authenticated
Character job 4296e4df-4f34-4365-8cba-52071f437ed9 = completed
Scene job ed74b5cd-9e45-4f12-beec-714f40535947 = completed
Drama MCP configuration = preserved
```

没有重新审计正式 MinIO；仅进行了健康回归。

## 3. Codex 权限模型

```text
Codex version = codex-cli 0.148.0-alpha.9
OS = macOS 26.5 arm64
Shell = /bin/zsh
permission model = managed workspace-write with one-time approved network
user config = /Users/yizhao/.codex/config.toml
project config = ABSENT
managed requirements.toml = NOT_FOUND
config.toml modified = NO
config backup = NOT_REQUIRED
restart required = NO
```

未通过持久化 `danger-full-access` 或修改 Codex 配置恢复下载。

## 4. 网络诊断

用户调整出口后，批准网络下的复测结果：

```text
storage.googleapis.com DNS = PASS
storage.googleapis.com TCP 443 = PASS
storage.googleapis.com TLS = PASS
storage.googleapis.com HTTP = PASS（根路径 HTTP 400，证明已到达服务端）
cloud.comfy.org shortlink = PASS
```

本轮两个短链均成功重定向并下载实际对象字节。没有记录完整短链、签名 URL、代理地址、代理凭据、OAuth Token、Cookie 或 Authorization Header。

```text
ROOT_CAUSE_PREVIOUS = OUTPUT_STORAGE_EGRESS_POLICY
ROOT_CAUSE_RECOVERY = storage.googleapis.com bypass proxy
HOST_EGRESS_TO_GCS = RECOVERED
```

## 5. 实际修复

本轮没有修改本地业务代码或 Codex 配置。实际生效变化是用户已将 `storage.googleapis.com` 绕过代理；Agent 随后：

1. 重新验证 GCS DNS、TCP 443、TLS 与 HTTP；
2. 顺序确认两个 existing job 仍为 `completed`；
3. 分别重新调用 `get_output`，没有复用过期 URL；
4. 原样执行 MCP 返回的原子下载命令；
5. 将下载结果移入 `.partial/` 校验，再原子移动为正式 artifact；
6. 确认 `.partial/` 中没有残留文件。

这是域名级、可逆的出口修复，没有开放全局网络。

## 6. Existing Job Recovery

### Character Master — 李陵

```text
jobId = 4296e4df-4f34-4365-8cba-52071f437ed9
terminal status = completed
get_output = PASS
download = PASS
local artifact = docs/reports/artifacts/batch5-1rr/character-master-liling-provider.png
MIME = image/png
magic bytes = 89 50 4E 47 0D 0A 1A 0A
size = 1,412,218 bytes
dimensions = 1024 × 1024
SHA-256 = 41ec29c7d6ae18c3503e50041c1784dc5ec74fd3770c5407e8cd22517a3135df
decode = PASS
```

### Scene Master — 穹庐

```text
jobId = ed74b5cd-9e45-4f12-beec-714f40535947
terminal status = completed
get_output = PASS
download = PASS
local artifact = docs/reports/artifacts/batch5-1rr/scene-master-qionglu-provider.png
MIME = image/png
magic bytes = 89 50 4E 47 0D 0A 1A 0A
size = 1,801,679 bytes
dimensions = 1024 × 1024
SHA-256 = e20301d471c46fb2e51f17c73727803c22ed5517658b47f3e2675a4844d35e90
decode = PASS
```

两个下载文件均为真实 PNG，不是 HTML、XML、JSON、认证错误页或重定向文本。

## 7. Visual Review

`job completed != visual review pass`。以下结论来自实际打开两张图片后的视觉检查。

### Character Master — 李陵

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| 中年男性身份 | PASS | 单一中年男性主体，年龄与既有李陵基线一致 |
| 脸型与身份稳定 | PASS | 长脸、颧骨、眼型和鼻部结构与 bootstrap 视觉身份连续 |
| 长发 | PASS | 深色长发束于后方，鬓发自然散落 |
| 胡须 | PASS | 短髭与下颌胡须清晰、克制 |
| 气质 | PASS | 疲惫、沉静、克制，没有夸张表演 |
| 胡服/皮毛 | PASS | 深褐色粗布胡服与毛皮肩领明确 |
| 避免特定 Shot 动作 | PASS | 中性坐姿，没有扶节、反问或饮酒动作 |
| 避免特殊道具固化 | PASS | 手中无刀、节杖、酒器等身份化道具 |
| 跨 Shot 可复用 | PASS | 单人中近景、脸部与服装信息完整 |
| 现代元素/多余人物 | PASS | 未见现代物件；仅一人 |
| 手脸结构 | PASS | 五官无重复，双手未见明显畸形 |
| 角落身份标注 | FAIL | 四角均没有清晰的“李陵”或等价身份标注 |

```text
CHARACTER_VISUAL_REVIEW = FAIL
```

失败原因仅为标准 Reference 所要求的角落身份标注缺失；本批禁止改图或重新生成，因此不做修补。

### Scene Master — 穹庐

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| 无人穹庐内部 | PASS | 圆形毡帐内部，无人物 |
| 夜间氛围 | PASS | 门外雪地与深蓝夜空清晰 |
| 弱火/弱光 | PASS | 中央低矮火盆提供暖光 |
| 冷暗基调 | PASS | 蓝黑环境光与局部暖火形成连续夜景基调 |
| 历史材质 | PASS | 毡墙、放射木骨、皮毛、木器和陶器成立 |
| 现代物件 | PASS | 未见电灯、塑料、现代家具或设备 |
| 避免人物/Shot 动作 | PASS | 场景为空，无特定动作 |
| 空间复用 | PASS | 中央活动区、两侧铺位与入口关系明确，支持不同景别和机位 |
| 透视/结构 | PASS | 圆形顶部骨架、墙体与地面关系合理，无严重空间错误 |
| 角落身份标注 | FAIL | 四角均没有清晰的“苏武穹庐”或等价场景身份标注 |

```text
SCENE_VISUAL_REVIEW = FAIL
```

失败原因仅为标准 Reference 所要求的角落场景身份标注缺失；本批不修改 Provider 输出。

## 8. Media Persistence

两个 Review 均 FAIL，按 5.1RR 规则不得导入为正式 Reference Media：

```text
Character media.import_media = NOT_PERFORMED_REVIEW_REJECTED
Scene media.import_media = NOT_PERFORMED_REVIEW_REJECTED
media.resolve_media = NOT_RUN
MEDIA_BYTE_EQUALITY = NOT_RUN
```

本地 artifact 位于已配置 allowed root 内，但 Review 门槛先于 import，因此没有产生 `mediaId`。

## 9. Asset Persistence

Review 失败后停止持久化：

```text
Character asset search/create = NOT_PERFORMED_REVIEW_REJECTED
Scene asset search/create = NOT_PERFORMED_REVIEW_REJECTED
Character assetId/mediaId = NOT_CREATED
Scene assetId/mediaId = NOT_CREATED
```

bootstrap Media `media_f1048149fd0f485c822481f91ea6a894` 未修改、未改 purpose、未重新分类。

## 10. Changed Files

| 文件 | 变更原因 | 源码 |
| --- | --- | --- |
| `plugin/docs/reports/artifacts/batch5-1rr/character-master-liling-provider.png` | Character existing job 的真实恢复输出 | NO |
| `plugin/docs/reports/artifacts/batch5-1rr/scene-master-qionglu-provider.png` | Scene existing job 的真实恢复输出 | NO |
| `plugin/docs/reports/28-Batch-5.1RR-Comfy-Cloud-Output-Fetch-Recovery-执行报告.md` | 本轮续跑正式报告 | NO |

## 11. Remaining Blocker

网络阻断已经消除。唯一剩余问题是两个 Provider 输出均缺少标准 Reference 要求的角落身份标注，导致 Visual Review 被拒绝。

该问题不能在 5.1RR 内通过改图、revise 或重新生成解决。按照停止边界，本批不扩大生产范围。

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
CODEX_SHELL_NETWORK_ACCESS = PASS
COMFY_SHORTLINK_REACHABLE = PASS
GCS_DNS = PASS
GCS_TCP_443 = PASS
GCS_TLS = PASS
GCS_HTTP_REACHED = PASS

CHARACTER_GET_OUTPUT = PASS
SCENE_GET_OUTPUT = PASS

CHARACTER_OUTPUT_FETCH = PASS
SCENE_OUTPUT_FETCH = PASS
OUTPUT_FETCH_RECOVERY = PASS

CHARACTER_FILE_DECODE = PASS
SCENE_FILE_DECODE = PASS

CHARACTER_VISUAL_REVIEW = FAIL
SCENE_VISUAL_REVIEW = FAIL

CHARACTER_MEDIA_IMPORT = NOT_PERFORMED_REVIEW_REJECTED
SCENE_MEDIA_IMPORT = NOT_PERFORMED_REVIEW_REJECTED

CHARACTER_REFERENCE_ASSET_PERSISTENCE = NOT_PERFORMED_REVIEW_REJECTED
SCENE_REFERENCE_ASSET_PERSISTENCE = NOT_PERFORMED_REVIEW_REJECTED

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

BATCH_5_1RR = PASS_WITH_REVIEW_REJECTION
NEXT_BATCH_READY = NO
```
