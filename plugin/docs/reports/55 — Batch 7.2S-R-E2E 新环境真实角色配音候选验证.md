# 55 — Batch 7.2S-R-E2E 新环境真实角色配音候选验证

日期：2026-08-27  
结论：`BATCH_7_2S_R_E2E = BLOCKED`

## 1. Goal

7.2S-R 是 Character Understanding、Voice Profile、Scene State、Performance Intent、候选排序和 paid-request 异常分类的 implementation/reconciliation。本 7.2S-R-E2E 只验证新 Host 上由 `audio-production` Skill 驱动的真实 Provider 与当前环境 Media 链路，不修改人物模型，也不进入 Batch 7.3。

恢复外部 runtime 后，本次提交了一个与历史 ambiguous operation 无关的新 Rank 1 候选。Provider 明确拒绝请求，没有生成 Audio 或 Media。接口只提供 `PROVIDER_REJECTED` 分类，不能证明拒绝原因仅为具体 voice incompatibility，因此依照安全规则停止其余三个 planned candidates，不盲重试，也不动态换 voice。

## 2. Environment Topology

```text
Narrative Domain = SHARED_PUBLIC_CLOUD_PERSISTENCE
Media Physical Storage = ENVIRONMENT_SPECIFIC
```

`~/.config/historical-plugin/runtime.env` 存在且可读，未被修改、复制或写入 repository。脱敏预检：

```text
REAL_TTS_E2E = ENABLED
SPEECH_PROVIDER_MODE = BAILIAN_QWEN
DASHSCOPE_API_KEY = PRESENT
Drama Service credential = PRESENT
Media credential = PRESENT
```

该文件存在一条不能作为 shell assignment 执行的内容；直接 `source` 会产生 shell 错误，而且 `load-env.sh` 的末尾命令会掩盖该错误状态。本次没有修改用户 env 文件，改用已安装的 `python-dotenv` 仅向 MCP 子进程安全注入配置，并为该进程覆盖 repository 内的本批 review 输出目录。没有输出或保存变量值。

```text
Python = 3.13.13
Java = Temurin 17.0.19
Maven = 3.9.16
ffmpeg = 8.1.2
ffprobe = 8.1.2

Drama MCP health = HTTP 200
Drama Service unauthenticated boundary = HTTP 401
Drama Service authenticated Domain reads = PASS_VIA_MCP
Current Media Storage health = HTTP 200
Plugin load = PASS
MCP tools = 45
production.generate_audio discovery = PASS
audio-production Skill available = YES
```

## 3. Shared Context Recovery

实际通过正式 MCP Tool 执行 `work.search_works`、五层 Domain get 和 `media.list_media`。共享 Context 可读：

```text
workId    = work_9cc5d11969a64f93bce4a544f349c793
scriptId  = script_a404a8277fef45eda8ef3aaf478307cc
episodeId = episode_c33021fe53ba4af08cd8b98113184dd2
sceneId   = scene_3ad95aa042e647d9a9be05a51dd8a009
shotId    = shot_83db7eb53b2f49d3a58428d4659e584e
```

Scene `关门未开`、Shot `1-03 三十骑之议`及两条 Dialogue binding 均通过当前服务读取。没有创建或修改 Work、Script、Episode、Scene、Shot、Dialogue。

```text
SHARED_WORK = PASS
SHARED_SCRIPT = PASS
SHARED_EPISODE = PASS
SHARED_SCENE = PASS
SHARED_SHOT = PASS
DUPLICATE_WORK_CREATED = NO
DOMAIN_WRITES = 0
OLD_ENVIRONMENT_MEDIA = NOT_VALIDATED
OLD_ENV_MEDIA_REQUIRED = NO
```

Work 可列出四条旧 Audio metadata；旧环境 physical objects 不属于本批验证范围。

## 4. Skill-Driven Semantic Plan

当前 Host 实际加载 `drama-plugin:audio-production`，从 user-level task 出发按 Skill 顺序读取 persisted Context，并保存 Character Understanding、稳定 Voice Profile、Scene State、Performance Intent、Provider-neutral Speech Request 和当前代码重新计算的候选排序。integration runner 消费这些 Skill 产物，没有用 fixture 替代 Skill 规划。

```text
SKILL_AVAILABLE = YES
AUDIO_PRODUCTION_SKILL_AVAILABLE = YES
SKILL_ACTUALLY_INVOKED = YES
FIXTURE_BYPASS = NO
NO_CHARACTER_SPECIFIC_RULE = PASS
VALUE_NEUTRAL_PROFILE = PASS
```

无证据的人物维度保持 `UNKNOWN`。同一 Dialogue 的 A/B 候选共享相同 Performance Intent，只改变 concrete base voice；Provider instruction 的离线 boundary 检查确认稳定基础声音和当前句表演指令分层传播。两条 TTS text 均与 persisted Dialogue exact match。

## 5. Current Candidate Ranking

排名由当前共享 Context、当前 Skill 产物和当前 Provider ranking code 重新计算，不复用旧报告排名：

| Speaker | Rank 1 | Rank 2 | Rank 3 | Planned |
| --- | --- | --- | --- | --- |
| `speaker:wangsili` | Neil 91.667 | Maia 90.000 | Ethan 86.667 | Neil, Maia |
| `speaker:geshuhan` | Eldric Sage 98.000 | Moon 92.000 | Neil 90.000 | Eldric Sage, Moon |

synthetic identity rename 后 voice ID、score 和理由保持不变：`IDENTITY_RENAME_INVARIANT = PASS`。Ranking 只是 audition plan，未建立 Voice Binding。

## 6. Historical Ambiguous Isolation

54 号报告记录的两个旧 operation 永久保持 `HISTORICAL_AMBIGUOUS / DO_NOT_RETRY`。本次创建全新的 E2E run identity 和 operation fingerprint；没有复用旧 generationAttemptId 或旧 request identity。

```text
OLD_AMBIGUOUS_REQUESTS_RETRIED = NO
FRESH_E2E_REQUESTS = YES
```

## 7. Real Provider Call and Safety Stop

Paid call 前固定顺序为王思礼 Rank 1、王思礼 Rank 2、哥舒翰 Rank 1、哥舒翰 Rank 2，最多四项。实际只提交第一项：

```text
Dialogue = spoken-s1-wangsili-proposal
Candidate rank = 1
Provider voice = Neil
exactTextInputVerified = true
freshE2E = true
historicalAmbiguousRetry = false
result = PROVIDER_REJECTED
```

MCP/Plugin 将真实 Provider HTTP 4xx 保留为 `PROVIDER_REJECTED`。这确认请求到达 Provider，并明确排除 `AMBIGUOUS_RESULT`；没有返回 Media ID、provider job ID 或音频文件。外层 MCP transport 在关闭 task group 时产生的 `ExceptionGroup` 只是 cleanup wrapper，证据 runner 已修正为保留内部 paid-call 分类。

由于公开错误边界没有提供可安全判定的具体拒绝原因，不能断言它只是 Neil voice incompatibility。按批次规则，不重试同一请求，也不继续其余独立候选。

```text
MAX_PLANNED_AUDIO_ITEMS = 4
PROVIDER_SUBMISSION_ATTEMPTS = 1
REAL_PROVIDER_CALLS = 1
SAFE_TRANSIENT_RETRIES = 0
AMBIGUOUS_ITEMS = 0
PROVIDER_REJECTED_ITEMS = 1
TRANSIENT_RETRY_EXHAUSTED_ITEMS = 0
OPENAI_REAL_CALLS = 0
```

## 8. Audio and Media Evidence

```text
REAL_AUDIO_CREATED = NO
AUDIO_TECHNICAL_VALIDATION = NOT_RUN_NO_FRESH_AUDIO
LOCAL_REVIEW_PATHS = NONE

FRESH_AUDIO_MEDIA_CREATED = NO
CURRENT_ENV_MEDIA_ROUNDTRIP = NOT_RUN_NO_FRESH_AUDIO
OLD_ENVIRONMENT_MEDIA = NOT_VALIDATED
OLD_ENV_MEDIA_REQUIRED = NO
```

没有伪造 ffprobe、hash 或 Media round-trip 结果，没有删除旧 Media row、迁移旧对象或复制假对象。当前不存在足够的候选供用户听审。

## 9. Verification

Paid call 前：

```text
validate_batch7_2sr_semantics.py
  Character Understanding = 2
  Voice Profile = 2
  Candidate Ranking = 2
  identity rename invariant = PASS
  semantic invariants = PASS

pytest -q drama-plugin/plugin/tests/test_real_speech_provider.py
  27 passed

pytest -q drama-mcp-service/tests/test_adapter.py
  12 passed
```

收口重新执行 runner compile、semantic validator、JSON parse、secret-pattern scan 和 focused tests；结果见最终 evidence。

## 10. Git Safety

开始时：

- `drama-plugin` 只有既有 `.DS_Store` 未跟踪文件；
- `drama-mcp-service` 的 `integration/run_mcp_e2e.py` 与 `integration/verify_runtime_config.py` 是既有未提交修改；
- `drama-service` clean。

本批未修改 Provider、Audio contract、MCP、Java、Skill 或业务源码。新增 E2E evidence、integration runner 和本报告；runner 的唯一修正是保留 MCP cleanup wrapper 内已经确定的 Provider 错误分类。没有写入 runtime secret。

## 11. Final Status

```text
BATCH_7_2S_R_E2E = BLOCKED
BLOCKER = FIRST_FRESH_CANDIDATE_PROVIDER_REJECTED_REASON_NOT_PROVEN_VOICE_SPECIFIC

NEW_ENV_PREFLIGHT = PASS
SHARED_NARRATIVE_CONTEXT = PASS
DUPLICATE_WORK_CREATED = NO

SKILL_AVAILABLE = YES
SKILL_ACTUALLY_INVOKED = YES
FIXTURE_BYPASS = NO
CHARACTER_MODEL_GENERIC = PASS
VALUE_NEUTRAL_PROFILE = PASS
CHARACTER_UNDERSTANDING = PASS
STABLE_STATE_SEPARATION = PASS
VOICE_PROFILE = PASS
SCENE_STATE = PASS
PERFORMANCE_INTENT = PASS
SEMANTIC_INVARIANTS = PASS
PROVIDER_NEUTRALITY = PASS

VOICE_CANDIDATE_RANKING = PASS
VOICE_CANDIDATES_GENERATED = NO
VOICE_BINDING = PENDING

OLD_AMBIGUOUS_REQUESTS_RETRIED = NO
FRESH_E2E_REQUESTS = YES_ONE_SUBMITTED_THEN_SAFETY_STOP
REAL_PROVIDER_CALLS = 1
AMBIGUOUS_ITEMS = 0
PROVIDER_REJECTED_ITEMS = 1
TRANSIENT_RETRY_EXHAUSTED_ITEMS = 0

REAL_AUDIO_CREATED = NO
AUDIO_TECHNICAL_VALIDATION = NOT_RUN
FRESH_AUDIO_MEDIA_CREATED = NO
CURRENT_ENV_MEDIA_ROUNDTRIP = NOT_RUN
OLD_ENV_MEDIA_REQUIRED = NO

USER_AUDIO_REVIEW = NOT_READY
AUDIO_APPROVED = NOT_SET
COMFYUI_CALLS = 0
IMAGE_GENERATION = NOT_STARTED
VIDEO_GENERATION = NOT_STARTED
BATCH_7_3 = NOT_STARTED
```
