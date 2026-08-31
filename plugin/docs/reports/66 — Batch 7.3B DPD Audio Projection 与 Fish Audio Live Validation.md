# 66 — Batch 7.3B DPD Audio Projection 与 Fish Audio Live Validation

日期：2026-08-29（Asia/Shanghai）  
批次：Batch 7.3B — DPD Audio Projection & Fish Audio Live Validation  
结论：`BATCH_7_3B = PASS`

## 1. 执行摘要

本批先审计 7.3A DPD Core、现有 Audio contracts、CreativeVoiceProfile/Casting、Role Dubbing、Fish Audio adapter、fingerprint、runtime 与真实 E2E，再建立严格 typed、provider-neutral、可序列化、可审计、可 fingerprint 的 `AudioPerformanceBrief`。

正式新路径为：

```text
DPDSnapshot + canonical SpokenContent + CreativeVoiceProfile
            + stable Voice identity + Timing
                         ↓
                 Audio Projection
                         ↓
             AudioPerformanceBrief
                         ↓
              existing Fish adapter
                         ↓
                  Fish Audio TTS
                         ↓
             stable Drama Media + WAV
```

同一句“你可知道后果？”、同一角色、同一 Work Voice、同一 Fish provider/model，在只改变 DPD 的条件下完成 A/B/C 三例真实生成。三条音频均通过技术 QC、Drama Service mediated content 下载与 SHA-256 校验；艺术表演是否符合创作预期仍由用户听审决定。

## 2. 本批范围

已完成：

- provider-neutral `AudioPerformanceBrief` 与 capability diagnostic；
- DPD + SpokenContent + Voice baseline + stable Voice identity + Timing 的 deterministic projection；
- Projection fingerprint、Provider request fingerprint 与 Media lineage；
- Fish capability mapping；
- 新/旧 performance authority 互斥；
- projected Role Dubbing 使用既有 Work Voice binding；
- 离线 contract、mapping、negative、Role Dubbing、Plugin、MCP 回归；
- Fish Audio A/B/C live E2E 与可听审 WAV。

明确未做：Visual Projection、Image/Video、Lip Sync、AV mux、7.3C、DPD/Projection CRUD、Java/DB schema、新业务 Service、新 Provider。

## 3. 开始前 AS-IS 审计

真实 AS-IS Fish TTS request 只验证并使用：

```text
text
reference_id
model = s2-pro
prosody.speed
prosody.volume
```

原 Role Dubbing `_native_performance()` 从 `materialRenderParameters` 和 legacy `performanceIntent` 读取 speed/volume；SceneState、戏剧动作、权力关系、节奏、停顿、咬字、句尾等丰富语义没有正式进入 Fish。Voice identity 已通过 Work `voiceProfiles[].voiceId` 与 Voice provider mapping 独立存在，不应复制进 DPD。

当前 canonical fingerprint 工具可直接复用；Fish adapter 与 Voice lifecycle 已可用，无需重写 adapter 或重新 Voice Design/Create Model。

Runtime 审计只核对变量是否存在及 owner，不读取或输出 secret。MCP 进程加载 `mcp-host.env + drama-plugin.env`，DB/MinIO/service-only variables 保持 unset；`drama-service.env` 未进入 MCP 进程。本批没有修改三个 env 文件，也没有恢复合并 `runtime.env`。

## 4. 7.3A Contract 复用情况

直接复用：

- `SceneDPD / BeatDPD / LineDPD / EffectiveDPD / DPDSnapshot`；
- 7.3A `dpd-core-v1.yaml` 三案例 fixture；
- canonical JSON + SHA-256 fingerprint；
- stable scene/beat/spoken/speaker identity；
- DPD immutable snapshot 语义。

Projection 单向消费 snapshot，不修改任何 DPD layer，不补造缺失戏剧方向；authority/relationship 无法唯一判定时以 `AUDIO_DIRECTION_INSUFFICIENT` fail fast。

## 5. Audio Projection 最终职责

Audio Projection 属于 Drama Plugin 的 provider-neutral Audio orchestration/core 层。它把 authoritative dramatic direction 与独立事实源组合成“人类配音导演可理解”的声音表演 brief，不负责选择 Provider、不拥有 Voice identity、不调用 HTTP、不持久化业务 Entity。

`DPDSnapshot` 是唯一 dramatic-performance authority，但不是 Projection 的唯一输入。真实台词来自 canonical SpokenContent，长期声音基线来自 CreativeVoiceProfile，发声者身份来自 stable Casting/Voice，时间约束来自 Timing policy。

## 6. Input Authority 设计

| 输入 | 拥有的事实 | Projection 行为 |
|---|---|---|
| `DPDSnapshot` | why/target/objective/tactic/authority/relationship/activation/control/subtext/action | 唯一当前戏剧表演权威 |
| SpokenContent | id、speaker、exact text | 校验 identity；只 hash 文本，不复制回 DPD |
| CreativeVoiceProfile | 长期声音基线 | 只取必要 baseline 并保留 profile fingerprint |
| Work Voice/Casting | 谁发声 | 只保留平台 stable Voice reference；Projection 不选择 Fish voice id |
| Timing policy | NATURAL 或批准时间窗口 | 形成独立 timing fingerprint |

新路径要求上述 identity 与 fingerprint 一致；mismatch、缺失 baseline、缺失 stable Voice binding 均显式失败。

## 7. Audio Performance Brief Contract

`audio-projection-v1` 保留 21 个最小 material/trace 字段：input identities/fingerprints、pace、pace tendency、rhythm、intensity、volume tendency、pause strategy、articulation、sentence ending、control、performance boundaries 与自身 fingerprint。

Brief 不含 Fish/provider/model/API endpoint/key/provider voice id、provider prompt field、timestamp、hostname、temporary URL 或随机 UUID。unsupported version 与 unknown field 由 strict Pydantic contract fail fast。

## 8. DPD → Audio 映射规则

映射先组合 `authority position + relationship stance + tactic + dramatic action` 得到 DOMINANT/EQUAL/SUBORDINATE，再组合 `internalActivation + externalControl` 形成压力、节奏与控制语言。

因此 `HIGH activation + HIGH control` 被表达为高内部压力但外部克制，而不是简单“更快、更响”。权威者强调有意识施压与明确收束；同侪强调观察空间与开放句尾；下位者强调礼制内的间接警示。Fish numeric controls 只由最后的 pace/volume tendency 在 adapter 层生成。

## 9. Character Voice / DPD 边界

CreativeVoiceProfile 继续拥有长期声龄、质感、共鸣、基线语速等身份。DPD 只描述此刻如何行动。Projection 以 Voice baseline 为底，再施加 DPD-induced delta，并保存 Voice profile id/fingerprint；没有把年龄、音色、Provider mapping 或完整 Voice Profile 复制进 DPD/Brief。

## 10. Casting / Projection 边界

Casting/Work Voice binding 决定“谁来发声”；Projection 决定“这一句怎么说”；Fish adapter 决定“如何映射成已验证的 Fish request”。Projected path 必须复用既有 stable Work Voice，缺失 binding 时返回 `VOICE_BINDING_REQUIRED`，identity 不一致时返回 `VOICE_BINDING_INVALID`，不会触发新 Voice Design 或 Create Model。

## 11. Fish Audio Adapter Mapping

扩展现有 Fish adapter，没有创建第二套 adapter：

| Projection tendency | Fish mapping |
|---|---|
| `pace=SLOWER` | `prosody.speed=0.92` |
| `pace=NEUTRAL` | `prosody.speed=1.0` |
| `pace=FASTER` | `prosody.speed=1.08` |
| `volume=LOWER` | `prosody.volume=-2.0` |
| `volume=NEUTRAL` | `prosody.volume=0.0` |
| `volume=HIGHER` | `prosody.volume=2.0` |

Fish request 仍使用现有 `text/reference_id/model/prosody` contract；没有编造 instructions、rhythm、pause 或 articulation 参数。

## 12. Fish Capability Matrix

| Brief dimension | 状态 | Fish control / 原因 |
|---|---|---|
| pace | SUPPORTED | `prosody.speed` |
| volume tendency | SUPPORTED | `prosody.volume` |
| intensity | APPROXIMATED | volume 只能近似幅度，不能表达戏剧压力 |
| control | APPROXIMATED | speed + volume 只能近似外部控制 |
| rhythm | UNSUPPORTED | 当前 verified request 无 phrase-shape 字段 |
| pause strategy | UNSUPPORTED | 无 semantic pause-plan 字段 |
| articulation | UNSUPPORTED | 无 articulation control |
| sentence ending | UNSUPPORTED | 无 sentence-ending control |

每次 provider mapping 都保存完整且不重复的八项 diagnostic。unsupported 项不会静默丢弃，也不会冒充已映射。

## 13. Legacy performanceIntent 兼容策略

旧路径保持可运行。新路径一旦携带 `AudioPerformanceBrief`：

- legacy `performanceIntent` 必须为空；
- `SceneState` 必须不存在；
- manual `materialRenderParameters.speed/volume` 禁止并存；
- Role Dubbing 只使用 DPD-derived mapping。

因此不存在两个导演同时控制一句话。旧字段本批不 destructive delete，只作为未进入新路径时的 compatibility fallback。

## 14. Fingerprint / Traceability

正式 lineage：

```text
DPD fingerprint
  → Audio Projection fingerprint
  → Fish provider request fingerprint
  → stable Media id / content hash
```

Projection material 包含 DPD、SpokenContent text、Voice baseline、Voice identity 与 Timing fingerprints；不含 runtime、provider response、URL、secret 或时间戳。Role Dubbing Media content 保存 `performanceAuthority=DPD_AUDIO_PROJECTION` 及上述三个 fingerprint，不保存原始 request 或 Fish provider voice id。

## 15. Deterministic Fixture

离线 fixture 固定 text/speaker/Voice/Casting/Timing，仅改变 7.3A DPD：

| Case | DPD action / relation | Brief tendency | Projection fingerprint |
|---|---|---|---|
| A | warn；superior → subordinate | SLOWER / NEUTRAL | `32156da4aeb80b256fa5f530f4a78f6220068a12c05e6b26efa0fd73e6ced402` |
| B | probe；peer → peer | NEUTRAL / LOWER | `cb6ef44964874e49397aa9b9e831e405b945d0f8c9792a051817c52e5c29a67c` |
| C | caution；subordinate → superior | SLOWER / LOWER | `80742a6dd707f3bd95dc758ed0451880a808c0a7b87baa55c5e67a1bcdc4d8b2` |

三个 fingerprint 两两不同；相同 input/reordered mapping 结果相同；Projection 后 DPD snapshot byte-equivalent 未改变。

## 16. Tests

| 验证 | 结果 |
|---|---|
| Projection/DPD/Audio/Fish targeted tests | PASS |
| unsupported version / unknown/provider field | PASS |
| missing/mismatched DPD/Spoken/Voice/Casting | PASS |
| new/legacy authority conflict | PASS |
| malformed capability diagnostic | PASS |
| projected Role Dubbing no-binding negative | PASS |
| projected Role Dubbing lineage | PASS |
| drama-plugin full pytest | `161 passed` |
| drama-plugin strict mypy | PASS（49 source files） |
| Audio Production Skill validation | PASS |
| drama-mcp-service full pytest | `24 passed` |
| drama-mcp-service strict mypy | PASS（4 source files） |
| lint / formatter | NOT PRESENT（项目未配置） |
| drama-service tests | NOT APPLICABLE（无 Java/HTTP contract 变更） |
| git diff check | PASS |

## 17. Real Fish Audio E2E

Live runner 在真实调用前验证：Fish credential 已配置；MCP 以分离的 host/plugin env 启动；MCP 进程 DB/MinIO variables unset；Work 存在唯一 stable Voice binding；`voice.get_voice → voice.resolve_voice → Drama Service content URL` 下载 Voice Master 并通过 SHA-256。`localhost:8080` 与 `127.0.0.1:8080` 被视为同一 loopback Drama Service origin；其他 host/port 仍 fail closed。

随后 A/B/C 各调用一次 `production.generate_role_dubbing`。每例均复用同一 Work Voice，无 Voice Design/Create Model，Fish model 均为 `s2-pro`。没有 ambiguous timeout；client 只保留已有的一次 safe transient retry budget。本批没有调用其他 TTS Provider。

三条 Media 均为 `ROLE_DUBBING_AUDIO`，technical review PASS、intelligibility QC PASS、artistic review PENDING；`media.resolve_media` 返回 Drama Service-owned content URL，下载 bytes 与 Media content hash 一致。URL/signature/secret 没有写入证据、报告或 stdout。

## 18. 三案例 Audio Artifact

固定控制项：台词 `你可知道后果？`、speaker `speaker:geshuhan`、同一 Voice id、同一 CreativeVoiceProfile fingerprint、同一 Timing、同一 Fish provider/model。

| Case | DPD / Audio Brief 摘要 | Fish mapping | Stable Media | 本地听审文件 |
|---|---|---|---|---|
| A | superior warning；克制高压、明确收束 | speed 0.92 / volume 0.0 | `media_a25dd7a0b7ef47adb4998f1c93ad44d3` | `artifacts/batch7-3b/review/case-a.wav` |
| B | peer probe；保留观察空间、开放句尾 | speed 1.0 / volume -2.0 | `media_e0b7568bef8d494382ee7c9e4b911156` | `artifacts/batch7-3b/review/case-b.wav` |
| C | subordinate caution；礼制内间接警示 | speed 0.92 / volume -2.0 | `media_1794a591609f4983b2dab68b05e49222` | `artifacts/batch7-3b/review/case-c.wav` |

三文件均为 WAV / PCM 16-bit / mono / 24 kHz，duration 1483 ms；SHA-256 分别为：

- A `b1a8ee82aecb78349d859f90a9705c95d4e52a3ddfbfb90585a6ea4429558ad3`
- B `59e2d97e96308cfc00d319e5e86b58c4dd494d130ecbfbd921393e823fcafdd0`
- C `9c705c9ac06320dd05489ff6104dee9d80e874d1a332d8c44eff20afda918d13`

完整脱敏证据：`artifacts/batch7-3b/evidence/live-e2e.json`。

## 19. Complexity Audit

| 指标 | 数量 / 结论 |
|---|---|
| 新 provider-neutral contract | 2：Brief + CapabilityDiagnostic |
| 新 enums | 3：pace tendency、volume tendency、capability status |
| Brief fields | 21（含 schema/input lineage/fingerprint） |
| 新 provider mapping contract | 1，位于现有 Fish adapter |
| 新 public projection helpers | 3：project、fingerprint、compile request |
| 新 adapter abstraction | 0；扩展现有 Fish adapter |
| 新业务 Entity/Service/Repository/MCP Tool | 0 |
| 新 production files | 2：contract + projection |
| 新 test/live runner files | 2 |

没有新增 Emotion/Mood/Prosody/VoiceStyle ontology、capability framework、Projection repository 或 migration framework。

## 20. 未解决问题

- Fish 当前无法直接消费 rhythm、pause、articulation、sentence-ending 等大部分 rich brief；三案例真实差异受 speed/volume 能力上限约束。
- AudioPerformanceBrief 当前是 deterministic intermediate artifact，其 fingerprint/diagnostic 进入 Media lineage，但不是独立持久化 Entity。
- legacy SceneState/performanceIntent/material render fields 仍服务旧路径；需在所有生产 caller 迁移后再独立删除。
- DPD Visual Projection 尚未开始。

## 21. 用户听审边界

系统只确认结构控制变量、typed lineage、Provider mapping、文件完整性、ASR intelligibility 与技术可播放性。三条声音是否充分体现“权威克制 / 同侪试探 / 下位谨慎”，以及哪条艺术表现最好，必须由用户听审；本报告不宣称艺术完美。

## 22. 后续 7.3C 前置条件

未来 Visual Projection 可消费同一 DPD fingerprint，但不得复用 Audio-only fields，也不得让 Fish capability 反向污染 DPD。当前仅记录此边界：`BATCH_7_3C = NOT_STARTED`、`LIP_SYNC = NOT_STARTED`。

## 23. 最终问题回答与状态

1. Audio Projection 属于 Drama Plugin 的 provider-neutral Audio orchestration/core 层。
2. DPDSnapshot 不是唯一输入；还需要 canonical SpokenContent、CreativeVoiceProfile、stable Casting/Voice identity 与 Timing。
3. DPDSnapshot 是唯一 dramatic-performance authority。
4. CreativeVoiceProfile 提供长期基线，DPD 提供当前 delta；Projection 组合后只保留必要结果与 fingerprint。
5. Casting 选择谁发声；Projection 决定怎么说，不选择 Fish voice id。
6. Fish adapter 把 Brief tendency 映射成已验证的 provider request，并输出 capability diagnostics/request fingerprint。
7. Fish 直接支持 pace 与 volume tendency。
8. intensity 与 external control 只能由 speed/volume 近似。
9. rhythm、pause strategy、articulation、sentence ending 当前完全不支持。
10. legacy performanceIntent 不参与新路径；仅保留旧路径 fallback。
11. 三条真实 Audio 固定 text/speaker/Voice/Casting/provider/model/Timing，唯一主要变量是 DPD → Projection。
12. rich performanceIntent、SceneState 重叠字段、legacy delivery/pace/pause 与 manual speed/volume 已具备未来 deprecated 条件，但本批不删除。

```text
AUDIO_PROJECTION_CONTRACT = PASS
DPD_TO_AUDIO_PROJECTION = PASS
VOICE_PROFILE_SEPARATION = PASS
CASTING_SEPARATION = PASS
SPOKEN_CONTENT_AUTHORITY = PASS
PROJECTION_DETERMINISM = PASS
PROVIDER_NEUTRALITY = PASS
FISH_ADAPTER_MAPPING = PASS
CAPABILITY_DEGRADATION = PASS
LEGACY_AUTHORITY_CONTROL = PASS
REGRESSION = PASS

REAL_FISH_AUDIO_CASE_A = PASS
REAL_FISH_AUDIO_CASE_B = PASS
REAL_FISH_AUDIO_CASE_C = PASS
COMPARATIVE_LISTENING_ARTIFACTS = READY

BATCH_7_3B = PASS
BATCH_7_3C = NOT_STARTED
LIP_SYNC = NOT_STARTED
```
