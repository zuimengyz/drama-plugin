# 53 — Batch 7.2S Skill 驱动的场景感知配音验证

日期：2026-08-26

## 1. 本次目标

Batch 7.2S 是 Batch 7.2R 之后的语义加固批次，不是重新验证 Transport，也没有进入 Batch 7.3。

- 7.2R 证明：`MCP → Plugin → Speech Provider → Qwen → WAV → Media / MinIO` 的真实链路可用。
- 7.2S 证明：Historical Drama Skill 能从真实剧情层级读取人物、场景、关系和对白，生成 provider-neutral Character Voice Profile 与 Performance Intent，并把语义传播到 Provider boundary。

本次在两条最终试听 Audio 生成并完成技术验证后停止。

## 2. 7.2R User Review Feedback

既有用户结论：

```text
USER_AUDIO_REVIEW = REJECTED
AUDIO_APPROVED = NO
VOICE_CASTING_MATCH = FAIL
SCENE_PERFORMANCE_MATCH = FAIL
```

7.2R 的 `speaker:validation-* + preset voice` 只验证了真实 Provider 链路，不能代表正式角色 casting。问题同时涉及人物年龄感、历史身份、统帅/部将关系、场景压力、说话目的、克制与潜台词，因此不能用单纯更换一个 preset voice 解决。

## 3. Context Bootstrap

本批先通过正式 MCP Tool 搜索并读取已有持久化数据。Batch 6 的真实潼关剧情仍存在，因此没有创建 fixture、没有直接写数据库，也没有新增重复 Work。

```text
workId    = work_9cc5d11969a64f93bce4a544f349c793
scriptId  = script_a404a8277fef45eda8ef3aaf478307cc
episodeId = episode_c33021fe53ba4af08cd8b98113184dd2
sceneId   = scene_3ad95aa042e647d9a9be05a51dd8a009
shotId    = shot_83db7eb53b2f49d3a58428d4659e584e
```

Scene：`关门未开`；Shot：`1-03 三十骑之议`。

Dialogue：

| speaker | dialogueId | exact Dialogue |
| --- | --- | --- |
| 王思礼 | `spoken-s1-wangsili-proposal` | `请给我三十骑，取杨国忠首级，为大帅除患。` |
| 哥舒翰 | `spoken-s1-geshuhan-refusal` | `此事若行，我便是反臣。不可。` |

历史叙事层级保持不变：哥舒翰是潼关主战场 PRIMARY 统帅人物；王思礼是有史料与既有 Script 支持的 SECONDARY 部将和对话角色。

当前持久层没有独立 Character Asset，但 Work 的 `historicalActorHierarchy`、Scene 状态、Dialogue speaker/listener 关系已提供足够的结构化 Character Context。Asset 与 Media 没有被混同，也没有创建人物图片 placeholder。

## 4. Skill Audit / Changes

实际负责 Audio Production 的现有 Skill：

```text
drama-plugin/plugin/skills/audio-production/
```

选择修改该 Skill，而没有新建大型 Audio Skill 体系。新增 `references/scene-aware-audio.md` 并对 `SKILL.md`、`skill.yaml`、OpenAI Host Adapter 做最小更新，明确：

- 生成前读取 Scene、Episode、Script、Work、Shot 和必要 Character Context；
- Character Voice Profile 与 line/Scene Performance Intent 分离；
- exact Dialogue text 不得被 Audio Layer 改写；
- Skill 只输出 provider-neutral 语义，具体 model/voice 只在 Provider adapter 选择；
- 禁止 validation speaker、Provider default casting、gender-only casting、忽略关系/场景、随机换声线和自动批准表演；
- Audio 技术通过后停在用户听审边界。

Skill Core 扫描结果：没有 Qwen、Bailian、DashScope、OpenAI、Cherry、Ethan、Moon 或 Eldric Sage 等 vendor/preset generation rule。Skill 中出现的 `speaker:validation-*` 仅位于明确禁止项。

## 5. Skill Invocation Evidence

当前 Mac 最初没有安装本地 drama-plugin。Host 集成事实恢复后，使用项目已有 `drama-marketplace` 和官方 local-plugin cachebuster/reinstall 流程安装最终版本：

```text
drama-plugin = 0.1.0+codex.20260826143457
```

独立 Codex Skill Host 从用户级任务开始：

```text
“为当前 Scene 的两位真实角色对白生成新的可试听配音。”
```

最终正式 Tool sequence：

```text
scene.get_scene
→ episode.get_episode
→ script.get_script
→ work.get_work
→ shot.get_shot
→ media.list_media
→ production.generate_audio (王思礼)
→ media.get_media
→ media.resolve_media
→ production.generate_audio (哥舒翰)
→ media.get_media
→ media.resolve_media
```

可审计证据：

- `artifacts/batch7-2/evidence/skill-generation-recast-task-7.2s.txt`
- `artifacts/batch7-2/evidence/skill-generation-recast-trace-7.2s.jsonl`
- `artifacts/batch7-2/evidence/skill-generation-recast-result-7.2s.json`

Trace 只保留用户任务、结构化 Tool calls 和结果；signed URL 已脱敏，不保存 private reasoning。

```text
SKILL_ACTUALLY_INVOKED = YES
FIXTURE_BYPASS = NO
```

## 6. Character Voice Profiles

### 王思礼

```yaml
speakerKey: speaker:wangsili
agePresentation: 成熟成年将领
genderPresentation: 男性
timbre: 坚实、偏锐
resonance: 中等、收束
texture: 克制而略带紧张
temperament: 果决、敢冒险、善于试探
authority: 资深部将
power: 相对主帅居下，但具行动能力
energy: 受控的高能量
baselinePace: 略快而清晰
articulation: 军令式简洁，字头明确
restraint: 高
consistency: 即使急迫，也不演成轻佻、莽撞喊叫或越权主帅
```

### 哥舒翰

```yaml
speakerKey: speaker:geshuhan
agePresentation: 成熟成年主帅
genderPresentation: 男性
timbre: 低沉、厚实
resonance: 深而稳定
texture: 略显病中疲惫，但不虚弱
temperament: 审慎、自持、承担后果
authority: 统军主帅
power: 高，来自军令权与自我约束
energy: 低至中等、内聚
baselinePace: 沉稳偏慢
articulation: 清楚、断句明确
restraint: 极高
consistency: 病态只表现为轻微负担，不削弱判断力，不以咆哮制造威严
```

两个 Profile 都是 transient provider-neutral planning object，没有新增数据库表或 schema migration。

## 7. Performance Intent

### 王思礼：三十骑之议

```yaml
emotion: 焦灼中的决断
emotionCause: 政治威胁已逼近守关军，常规路径似不足以自保
intensity: 中高但内收
pace: 略快
urgency: 高
restraint: 高
volumeTendency: 低声
pausePlan: “三十骑”后极短停顿，后半句连续推进
emphasis: [三十骑, 除患]
subtext: 既献策，也在测试主帅是否愿意越过忠逆边界
speakerObjective: 说服哥舒翰批准迅速清除杨国忠
listenerRelationship: 部将向主帅秘密进言
performanceBoundary: 不得喊叫、炫勇或演成公开煽动
```

### 哥舒翰：断然拒绝

```yaml
emotion: 警惕与沉重的自我约束
emotionCause: 威胁真实存在，但该方案会使自己成为反臣
intensity: 中等、压实
pace: 沉稳偏慢
urgency: 中高
restraint: 极高
volumeTendency: 低声
pausePlan: 开口前短停；“反臣”后收束；“不可”独立成句
emphasis: [反臣, 不可]
subtext: 拒绝的不只是行动，也是让政治恐惧替代军事判断
speakerObjective: 关闭劫相方案并维持忠臣与军令边界
listenerRelationship: 主帅对可信部将作最终裁决
performanceBoundary: 不咆哮、不辩解、不软化拒绝
```

## 8. Semantic Propagation

正式链路：

```text
Persisted Character / Scene / Dialogue
→ installed audio-production Skill
→ provider-neutral Voice Profile + Performance Intent
→ SpeechGenerationRequest(providerMapping = null)
→ SpeechBackedProductionProvider
→ BailianQwenSpeechProvider.resolve_request
→ provider-specific voice + instruction
→ Qwen request
→ WAV
→ Drama Service Media
→ MinIO
```

最小 contract 变化：

- `SpeechGenerationRequest.providerMapping` 变为可选；
- Voice Profile 可携带新增的 provider-neutral 音色维度；
- Speech Provider interface 增加 `resolve_request`；
- fingerprint 在 Provider 完成具体 mapping 后计算；
- OpenAI adapter 保留，并拥有同样的 provider-boundary resolution 路径；
- 不新增 vendor-specific MCP Tool，不修改 Java Domain，不做数据库 migration。

Qwen instruct payload 将完整 creative profile 与 performance intent 编译到 `instructions`，同时 `input.text` 仍是批准过的 Dialogue 原文。两个最终请求的 text hash 与 Scene 原文一致，且 provider request fingerprint 不同。

```text
AUDIO_SEMANTIC_PROPAGATION = PASS
exactTextInputVerified = true (2/2 final review items)
```

## 9. Voice Casting

第一次真实运行产生了两条技术有效的 Ethan candidate，但最终审计发现旧 resolver 的 concrete voice 分支仍过度依赖 gender。这不满足 7.2S casting 规则，因此没有把它们作为最终试听交付，也没有隐瞒或删除证据。

进行了最小 Provider-side 修正：对 age、timbre/resonance、texture、authority/power、energy、temperament、articulation、restraint 做 deterministic multi-dimensional scoring。它不包含历史人物姓名映射。

最终结果：

| Character Profile | Provider selected voice | Provider-side rationale |
| --- | --- | --- |
| 王思礼 | Moon | 果决/敢冒险、受控高能量、坚实偏锐、资深部将等维度命中行动型男性候选 |
| 哥舒翰 | Eldric Sage | 低沉厚实、深稳定、病中疲惫、统军主帅、极高克制等维度命中苍劲稳重候选 |

当前音色与 instruct model 兼容性依据 Alibaba Cloud 的 Qwen-TTS voice list；具体 preset 名只存在于 Provider adapter、Media evidence 和本报告，不存在于 Skill Core。

本次总计 4 个 generation items：前 2 条为审计后淘汰的技术 candidate，后 2 条为最终试听。总数没有超过 Batch 7.2S 的 2~4 条上限；没有因审美连续 reroll。

```text
PROVIDER_CALLS = 4
SAFE_RETRIES = 0
AMBIGUOUS_ITEMS = 0
```

## 10. Real Audio Evidence

### 最终用户试听 Audio

| Character | mediaId | voice | size | duration | codec | sample rate | channels | SHA-256 |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| 王思礼 | `media_ba8fecb6d58d49c19a7b113d24b772c4` | Moon | 257324 B | 5.360 s | pcm_s16le | 24000 Hz | 1 | `976f5949e7b1dff8160d0dddbe75b0a07fdea61cf3dcae030ecaaa979b76bcdc` |
| 哥舒翰 | `media_4dbc4dfa0a4a422080d9fa70c5dcad84` | Eldric Sage | 195884 B | 4.080 s | pcm_s16le | 24000 Hz | 1 | `928090b3e37023e7b3d5c7171d238cabc5a715285013072067c570020386d2ce` |

Local review artifacts：

- `artifacts/batch7-2/review/speech-3b72123dadf580bafa9902cfb7c8148eb9cd3a0eeb730659ddbe3759a107d15a-c445d1a17d1d49b2aace5180eadd07a2.wav`
- `artifacts/batch7-2/review/speech-df0b6a84147ce2607a6fb7103dd8e7375677da08171d14292987c8be278fd4ed-06d0a026fc8e48fd95d732e0f633198b.wav`

两条都经过：

```text
audio bytes > 0 = PASS
ffprobe = PASS
Media resolve = PASS
MinIO download roundtrip = PASS
downloaded SHA-256 == local SHA-256 == Media contentHash = PASS
reviewStatus = PENDING
```

技术证据：`artifacts/batch7-2/evidence/audio-technical-validation-7.2s.json`。

## 11. Tests

实际执行：

```text
drama-mcp-service/.venv/bin/python -m pytest -q \
  drama-plugin/plugin/tests/test_real_speech_provider.py
→ 24 passed

drama-mcp-service/.venv/bin/python -m pytest -q drama-plugin/plugin/tests
→ 142 passed

drama-mcp-service/.venv/bin/python -m mypy \
  drama-plugin/plugin/src/drama_plugin
→ PASS, 43 source files

cd drama-mcp-service && .venv/bin/python -m pytest -q
→ 14 passed

cd drama-mcp-service && .venv/bin/python -m mypy src/drama_mcp_service
→ PASS, 4 source files

IntelliJ bundled Maven 3.9.16: mvn test
→ 33 passed, 0 failure, 0 error, 0 skip

plugin-creator validate_plugin.py drama-plugin/plugin
→ PASS

validate_batch7_2s_audio.py
→ ffprobe PASS, Media roundtrip PASS, hash equality PASS
```

Regression 覆盖 resolver、OpenAI adapter offline path、Bailian adapter、exact text、semantic instruction、multi-dimensional casting、safe retry、ambiguous timeout no-retry、production.generate_audio contract、MCP protocol 和 Skill vendor-neutral scan。OpenAI 真实调用为 0。

## 12. Git Diff

任务开始时 workspace root 不是 Git repository；`drama-plugin`、`drama-mcp-service`、`drama-service` 各自是 repository。

开始前已有用户/7.2R 未提交修改：

- `drama-plugin`：52 号报告、7.2R preflight/E2E、host Media、speech production/tests 等；
- `drama-mcp-service`：Settings path fix 与 adapter/protocol/settings tests；
- `drama-service`：9 个 Media/operation/application/test 文件；
- root：`scripts/load-env.sh`、loader test 和 7.2R artifacts。

这些修改没有被回滚、覆盖或错误计入 7.2S。

7.2S 最小必要修改：

- `audio-production` Skill rules 与 scene-aware reference；
- provider-neutral Audio contract 的可选 mapping 和少量 voice dimensions；
- Speech Provider boundary resolution；
- Bailian 多维 casting 与 instruct semantic mapping；
- OpenAI preserved offline resolution；
- 对应 tests 与只读技术验证脚本；
- plugin cachebuster；
- 新增 7.2S artifacts、summary 和本报告。

没有修改 Java Domain schema，没有进入视觉生产，没有删除旧 Audio evidence，没有提交 runtime.env 或 secret。

## 13. Final Status

```text
BATCH_7_2S = READY_FOR_USER_AUDIO_REVIEW

REAL_NARRATIVE_CONTEXT = PASS
WORK = REAL_PERSISTED_ENTITY
SCRIPT = REAL_PERSISTED_ENTITY
EPISODE = REAL_PERSISTED_ENTITY
SCENE = REAL_PERSISTED_ENTITY
SHOT = REAL_PERSISTED_ENTITY

SKILL_AUDIO_RULES = PASS
SKILL_ACTUALLY_INVOKED = YES
FIXTURE_BYPASS = NO

CHARACTER_CONTEXT_LOADED = YES
SCENE_CONTEXT_LOADED = YES
VOICE_PROFILE_GENERATED = YES
PERFORMANCE_INTENT_GENERATED = YES
AUDIO_SEMANTIC_PROPAGATION = PASS
PROVIDER_NEUTRAL_AUDIO_SPEC = PASS
PROVIDER_NEUTRALITY = PASS

SPEECH_PROVIDER = bailian_qwen
REAL_QWEN_TTS = PASS
REAL_AUDIO_CREATED = YES
AUDIO_TECHNICAL_VALIDATION = PASS
MEDIA_ROUNDTRIP = PASS

GENERATION_ITEMS = 4
FINAL_REVIEW_AUDIO_ITEMS = 2
SAFE_RETRIES = 0
AMBIGUOUS_ITEMS = 0
OPENAI_REAL_CALLS = 0

USER_AUDIO_REVIEW = PENDING
AUDIO_APPROVED = NOT_SET

COMFYUI_CALLS = 0
IMAGE_GENERATION = NOT_STARTED
VIDEO_GENERATION = NOT_STARTED
BATCH_7_3 = NOT_STARTED
```

本批在真实 Skill-driven Audio 已生成、技术与语义证据完整后停止。角色适配、语气、节奏、自然度和历史短剧表演效果只由用户听审决定。
