# 59 — Historical Plugin — Role Dubbing / Lip Sync / Video Production 全架构审计

日期：2026-08-27（Asia/Shanghai）  
审计类型：Architecture / Contract / Production Pipeline Audit  
结论：`ARCHITECTURE_AUDIT = COMPLETE`

## 1. Executive Summary

本批只进行了代码、Contract、Skill、历史报告、测试与官方外部资料审计；没有修改生产业务代码，没有调用真实 TTS、ComfyUI、Comfy Cloud 或 Lip Sync，没有生成 Audio / Video，也没有改变 Runtime 配置。

核心结论：

1. `Work → Script → Episode → Scene → Shot` 的创作与长期记忆主链 **不需要重构**。现有 `Scene.content.spokenContent[]`、Work-scoped `speakerKey`、`Shot.content.spokenContentBindings[]` 与 `plannedDurationMs` 已构成 Role Dubbing / Lip Sync 的可靠上游。
2. 主生产顺序推荐 **`TIMELINE_FIRST_HYBRID`**。当前代码已经把 Dialogue 估算时长与 Shot 计划时长放在生成前，最小演进应是补一个 transient Timing Plan / speech window，再让 Visual Production 与 Role Dubbing 在同一时间预算下并行，之后显式 Timing Fit、Lip Sync、Audio Post。
3. 专业 Role Dubbing 不应继续被解释为“为 `production.generate_audio` 再加一个 Provider”。建议新增且仅新增一个高层 `production.generate_role_dubbing` Tool；它内部复用现有 `SpeechGenerationRequest`、Speech Provider seam、Media、fingerprint、attempt/PASS 与错误语义。保留 `production.generate_audio` 给普通单段 speech 与向后兼容。两者不共享第二套 Provider abstraction。
4. Lip Sync 必须是独立、可追踪的 production step，建议未来只暴露一个 `production.lip_sync` Tool。它读取已持久化 Raw Video 与已审 Dialogue dry track，产生新的 derived Video Media；不得覆盖原视频，也不得暗藏在 `generate_video` 内。
5. 默认不新增 Java Domain、数据库表、微服务、Voice Binding Entity、Timeline Entity、ASR Tool 或 Generation Attempt Entity。现有 open `content`、`purpose`、全局唯一 `sourceRef`、物理 `durationMs/contentHash` 与 Media import/resolve 已足以承载最小演进。
6. Voice Binding 继续复用 `Work.content.voiceProfiles[].providerMappings[]` 的 approved mapping；reference audio 的物理对象是 `Media(AUDIO)`，需要稳定可复用语义身份时可复用既有 `AssetType.AUDIO_INPUT`，不新增 `VOICE_REFERENCE` / `CHARACTER_VOICE` Asset type。
7. `exactTextInputVerified=true` 只证明输入正确，不能证明输出可懂。ASR/CER/专名差异检查应是 External Role Dubbing Workflow 内部 QC；Skill 与 MCP 只消费汇总结果，不暴露 `run_asr` Tool。自动 QC 不能取代中文专名、表演和角色适配的人工听审。
8. `PRIMARY_BAKEOFF_CANDIDATES = {IndexTTS 2.5, Fish Audio S2 Pro}`。IndexTTS 2.5 更适合验证单角色参考音色、音色/情绪分离、中文读音与相对语速控制；Fish Audio S2 Pro 更适合验证自然语言表演控制、跨句/多轮上下文和多说话人能力。正式选型必须由相同输入 Bakeoff 决定。

强制精简性结论：除两个高层 production Tool contract、Role Dubbing QC 结果约定、transient timing plan 与 derived Media purpose/provenance 约定外，其余新增层都可以延后而不影响正确工作，因此全部 `DEFER`。

## 2. Current AS-IS Architecture

### 2.1 三工程真实边界

```text
Host / Agent
  ↓ reads SKILL.md + skill.yaml
drama-plugin
  ├─ platform-neutral Skill Core
  ├─ typed Tool catalog / JSON Schema
  ├─ Memory / Asset / Media / Production Provider protocols
  ├─ SpeechGenerationRequest + Speech Provider adapters
  └─ Host-local media probe / mux utility
  ↓ generic tool registry projection
drama-mcp-service
  ├─ dynamic tools/list
  ├─ schema validation + typed coercion
  ├─ JSON serialization
  └─ safe error mapping
  ↓ HTTP-backed domain providers
drama-service
  ├─ Work / Script / Episode / Scene / Shot / Asset / Media persistence
  ├─ S3-compatible object storage import / resolve / restore
  └─ sourceRef uniqueness + physical metadata
```

### 2.2 长期记忆链

```text
Work
  ↓ workId
Script
  ↓ scriptId
Episode
  ↓ episodeId
Scene.content.spokenContent[]
  ↓ spokenContentId + speakerKey
Shot.content.spokenContentBindings[]
  ↓ shotId / coverageIntent / plannedDurationMs
Asset (stable reusable semantic object)
  ↔ referenceMediaIds
Media (immutable physical output + provenance)
```

### 2.3 当前 production Tool

```text
production.generate_image(prompt, stable references, parameters) → Media
production.generate_video(prompt, exactly one image OR start/end pair, parameters) → Media
production.generate_audio(SpeechGenerationRequest, optional referenceMediaIds) → Media(AUDIO)
```

AS-IS 没有 `generate_role_dubbing`、`lip_sync`、`run_asr`、Timeline Domain 或 Generation Attempt Domain。

### 2.4 当前 AS-IS 图

```text
[UNCHANGED] Work → Script → Episode → Scene
                                   ├─ spokenContent[]
                                   │  (exactText, speakerKey,
                                   │   performanceIntent,
                                   │   estimatedDurationMs)
                                   ↓
[UNCHANGED] Shot Design
              ├─ plannedDurationMs
              └─ spokenContentBindings[]
                         ↓
[UNCHANGED] Shot Production (no mandatory fixed media order)
              ├─ Asset discovery / stable Media resolve
              ├─ generate_image → reviewed Image Media
              ├─ generate_video → reviewed silent/raw Video Media
              └─ generate_audio → Speech Clip Media(PENDING/PASS)
                                            ↓
[UNCHANGED] av-assembly-v1 Host mux
              raw Video + Speech Clip / Dialogue Mix
                         ↓
              new Media(VIDEO, FINAL_AV)
```

## 3. drama-plugin Audit

### 3.1 Skill responsibilities

| Responsibility | Current Skill | Current fact |
|---|---|---|
| Work | `work-creation` | premise, spine, actor hierarchy, narrative authority |
| Script | `script-adaptation` | audiovisual structure, arcs, pacing, escalation |
| Episode | `episode-development` | episode goal, conflict progression, continuity |
| Scene | `scene-development` | canonical `spokenContent`, scene state/action/turn |
| Shot | `shot-design` | coverage, camera, `plannedDurationMs`, spoken bindings |
| Asset | `asset-resolution` | stable reusable **visual** identity and reference Media |
| Visual production | `shot-production` | reference planning, image/video production and visual review |
| Audio production | `audio-production` | Character Understanding through speech, review, duration, Media and AV mux |
| Review | distributed | each creative/production Skill owns its applicable gate; no central Review service |

### 3.2 `audio-production` responsibility concentration

Current `audio-production` has accumulated:

```text
hierarchy/context gather
→ Character Understanding
→ stable Voice Profile
→ Scene State
→ Performance Intent
→ voice candidate ranking / binding review
→ provider-neutral request compilation
→ Provider resolution / TTS
→ Audio review
→ duration probe / fit
→ Media import / freshness
→ AV assembly / mux
```

这已跨越 creative understanding、casting、render、QC 与 post/mux 五类职责。问题不是 Skill 文档过长本身，而是它开始描述候选排名、Provider casting 和最终 AV assembly 的完整实现流程，使“历史剧理解”和“专业配音工作流”难以分别替换。

### 3.3 Role Dubbing 后的 KEEP / MOVE / REMOVE / DEPRECATE

| Decision | 内容 | 理由 |
|---|---|---|
| KEEP | canonical Dialogue resolution、Character Understanding、Stable Voice Profile、Scene State、Performance Intent、pronunciation guidance、timing policy | 平台中立且是 Historical Drama 的核心语义价值 |
| KEEP | exact-text invariant、freshness review、Media provenance、human review gates | 跨 Provider 稳定合同 |
| MOVE | voice candidate search/ranking、reference conditioning、Provider prompt/tag/phoneme compilation、ASR、duration render retries | External Role Dubbing Workflow / Provider adapter |
| MOVE | Lip Sync、face selection、sync QC | 独立 External Lip Sync Workflow |
| MOVE | SFX/Ambience/Music/ducking/mastering | Audio Post / Mix，不能继续塞入 dubbing |
| REMOVE | 无 | 本批没有证据要求删除现有可用能力 |
| DEPRECATE | Skill 内的 Qwen-specific casting/Voice Design workflow 作为专业主流程 | 保留实现用于历史兼容/Bakeoff，不再把它当默认专业角色配音策略 |

推荐边界：

```text
Historical Drama Skill
  → Character / Scene Understanding
  → provider-neutral Role Dubbing Brief
  → External Role Dubbing Workflow
  → QC summary + durable Media
```

Skill 不实现专业声学模型、ASR、forced alignment 或多说话人解混。

### 3.4 Skill Core platform neutrality

现有 Core 仍遵守 `SKILL.md + skill.yaml` 平台中立原则；Vendor 细节位于 Python Provider adapter 与 integration scripts。新增 Role Dubbing / Lip Sync 时应保持同一原则：Skill 只引用稳定 Tool code，不引用 Codex、MCP transport、Java、Comfy node、HTTP endpoint 或模型 tag 语法。

## 4. drama-mcp-service Audit

`PluginToolAdapter` 是通用投影：动态读取 Plugin registry，原样传播 input schema，object-root output schema 可声明，调用前用 JSON Schema 验证并用 Pydantic 类型转换；它没有 domain dispatch。

现有错误映射包括：

- `INVALID_ARGUMENT`、`NOT_FOUND`、`CONFIGURATION_ERROR`；
- `AMBIGUOUS_RESULT`，用于提交可能成功时阻止盲目付费重试；
- `PROVIDER_REJECTED`、`TRANSIENT_RETRY_EXHAUSTED`、`PROVIDER_ERROR`；
- Provider 诊断会过滤 URL、credential 与 raw exception。

结论：

- Role Dubbing / Lip Sync 若新增 Plugin Tool，会自动投影为 MCP Tool；MCP service 不应编排 ASR、timing fit、face detection 或 Provider workflow。
- 只需未来为新增可识别的高层失败类别补通用安全映射；不需要专用 Controller、adapter class 或 MCP 子服务。
- Tool 粒度应保持两个高层能力：`production.generate_role_dubbing` 与 `production.lip_sync`。禁止把 Provider 内部步骤逐个投影给 Skill。

## 5. drama-service Audit

### 5.1 当前持久化能力

`drama_media` 已有：

```text
id / workId / assetId / shotId
mediaType / purpose / sourceRef (global UNIQUE)
storageType / bucketName / objectKey
mimeType / fileSize / width / height / durationMs / contentHash
content JSON / version / timestamps
```

`media.import_media` 已执行 MIME、positive duration、scope、object storage、hash 与 `sourceRef` idempotency/conflict 校验；`resolve` 返回临时 URL；`restore` 要求 MIME/size/hash 同一。

### 5.2 Java impact

Role Dubbing 与 Lip Sync 不要求 Java 理解：

```text
voice model
ASR
phoneme
face track
Comfy workflow
lip-sync provider
timing algorithm
```

这些都可放在 Media `content` 的 provider-neutral provenance/QC manifest 中。`purpose` 是开放字符串，已能表示 `VOICE_REFERENCE`、`ROLE_DUBBING_AUDIO`、`LIP_SYNCED_VIDEO`、`FINAL_AV` 等用途而无需 enum/DB migration。

结论：`JAVA_DOMAIN_CHANGE_REQUIRED = NO`。若后续规模证明 `media.list_media` 需要更多 filter，可以扩展现有 query contract；不能以此为由预建 Voice/Timeline/Attempt 表。

## 6. Current Visual Production Pipeline

真实顺序不是 Prompt 假设的固定链，而是：

```text
approved Shot
→ stable reference discovery (Asset + Media, max 3)
→ resolve stable Media
→ provider-neutral visual delta / motion prompt
→ external visual provider
→ output fetch
→ Visual Content Review PASS
→ optional identity annotation
→ media.import_media
```

Image 与 Video 的关系：

- Image 可由 `production.generate_image` 产生；
- Video 必须使用 exactly one single-image input，或同一 target 的 start/end frame pair；
- start/end/KEY_FRAME/VIDEO_INPUT 是既有 Asset type，但 Tool 输入使用 Media ID；
- Video motion prompt ≤ 2,000 字符；
- 当前 Tool contract 没有 typed `duration` 字段，实际 duration 多由 Provider `parameters` 与已批准 Shot `plannedDurationMs` 编译决定；
- 历史真实生产显示 Shot 1-03 `plannedDurationMs=10500` 被转换为 provider duration 11s，物理结果 11.041667s。故 Shot 是创意计划时长权威，Media 是物理实际时长权威，Provider 参数只是编译结果。

Comfy Cloud 是已验证过的 Visual Host implementation，不是 Drama Domain，也没有写入 Java。

## 7. Current Audio Production Pipeline

```text
Scene.spokenContent exact text
→ CharacterUnderstanding (transient)
→ VoiceProfile (stable creative profile)
→ SceneState (transient)
→ PerformanceIntent (line-level)
→ SpeechGenerationRequest
→ production.generate_audio
→ Speech Provider resolution / generation
→ local file + ffprobe
→ Media(AUDIO, SPEECH_CLIP, PENDING attempt sourceRef)
→ human review; PASS owns canonical audio-input:<fingerprint>
→ optional SHOT_DIALOGUE_MIX
→ av-assembly-v1 + immutable raw Video
→ Media(VIDEO, FINAL_AV)
```

已具备的安全性：exact text typed field、mapping/profile/pronunciation/scene/performance/timing fingerprint、physical duration probe、sourceRef attempt/canonical distinction、existing PASS reuse、local file requirement、Media hash/storage。

缺口：输出 speech 没有可靠的 ASR/intelligibility result；`exactTextInputVerified` 只是 input-side check；当前结果为 Media 而不是 workflow result；voice binding 仍多为 pending；AV assembly 是 mux，不是 Lip Sync；没有 speech window contract。

## 8. Role Dubbing Architecture Requirements

### 8.1 Option A vs Option B

| 维度 | Option A：扩展 `generate_audio` | Option B：新增高层 Role Dubbing Tool |
|---|---|---|
| Contract clarity | 普通 TTS、casting、ASR、fit 混在一名下 | 专业 workflow 语义明确 |
| Backward compatibility | input 可加 optional；output 若从 Media 改 Result 会破坏兼容 | 旧 Tool 不变，新 Tool 独立版本化 |
| Skill complexity | Skill 需判断 Provider 是否支持 workflow QC | Skill 调用单一高层结果 |
| Provider complexity | 容易把 ASR/fit 写进每个 Speech Provider | workflow 内复用 Speech Provider 与独立 QC implementation |
| MCP complexity | 零新 Tool，但 schema/语义膨胀 | 仅新增 1 个自动投影 Tool |
| Java impact | 无 | 无 |
| future extensibility | 返回 Media 难表达 QC/binding candidate | Result 可稳定承载 QC 与 Media ref |
| 精简性 | 表面少一 Tool，长期隐式分支多 | 多 1 Tool，减少多处隐式分支 |

推荐 Option B，但明确复用现有基础；不是创建第二套 TTS Provider abstraction。

### 8.2 最小 RoleDubbingRequest 审计

推荐把已有 `SpeechGenerationRequest` 作为内核，而不是复制全部字段。

| Candidate | 分类 | 结论 |
|---|---|---|
| `characterRef` | DERIVABLE | 由 workId + speakerKey + non-material context refs 解析；不建立 Character Entity 强依赖 |
| `dialogueRef` | REQUIRED | 已由 `sceneId + spokenContentId` 表达；不要新增别名 |
| `exactText` | REQUIRED | 继续使用现有 typed exactText |
| `voiceBindingRef` | OPTIONAL | 有 approved mapping/reference 时复用；首次 casting 可为空 |
| `voiceBrief` | DERIVABLE | 由现有 VoiceProfile / CharacterUnderstanding 生成，不复制自然语言大 prompt |
| `sceneState` | OPTIONAL | 表演需要时提供；事实不足可显式 unknown/none |
| `performanceIntent` | REQUIRED | 专业角色配音的最小戏剧语义 |
| `pronunciationHints` | OPTIONAL | 只在存在已审 guidance 时提供 |
| `targetDurationMs` | OPTIONAL | 已由 `TargetTimingPolicy.targetDurationMs` 表达；自然模式可为空 |
| `speechWindow.startMs/endMs` | NOT_NEEDED | placement/timeline 责任，不应成为单句声学生成的重复输入；target duration 足够驱动 fit |

最小概念：

```text
RoleDubbingRequest v1
  speechRequest: SpeechGenerationRequest v1
  voiceBindingRef?: approved Work voice mapping or AUDIO_INPUT Asset reference
  qcPolicy?: default INTELLIGIBILITY_V1
```

`voiceBindingRef` 与 `qcPolicy` 是否成为显式字段可在 P0 contract spike 决定；当前绝不能复制 `exactText/speakerKey/voiceProfile` 到 wrapper 顶层。

### 8.3 最小 RoleDubbingResult 审计

| Candidate | 分类 | 结论 |
|---|---|---|
| `audioMediaRef` | REQUIRED | 下游唯一稳定物理输入 |
| `speakerRef` | DERIVABLE | request 与 Media content 已有 speakerKey |
| `durationMs` | REQUIRED | 必须来自物理 probe；可从 Media 读取但 workflow result 应直接回传 |
| `asrTranscript` | OPTIONAL | QC evidence；默认 transient，必要时摘要持久化 |
| `textMatchScore` | OPTIONAL | 单一 score 不足以判定；应配 CER 与 mismatch categories |
| `wordTiming` | OPTIONAL | 字幕/诊断/某些 Provider 可用；Lip Sync v1 不要求 |
| `phonemeTiming` | NOT_NEEDED | 当前候选 Lip Sync 以 Audio+Video 工作，不应预建 |
| `pronunciationReport` | OPTIONAL | 历史专名/失败时有价值 |
| `voiceBindingCandidate` | OPTIONAL | 首次 casting 返回；已有 binding 时不需要 |
| `providerMetadata` | OPTIONAL | 只保留可追溯、安全且 material 的摘要，不能成为 Skill 逻辑 |

此外 Result 必须有一个小型 `intelligibilityQc`：`status`、`cer`、missing/extra/repetition/properNoun findings 与 human-review-required。这个汇总比强制暴露完整 ASR transcript 更稳定。

## 9. IndexTTS 2.5 Capability Audit

核验时间：2026-08-27。官方版本/模型：IndexTTS-2.5，官方仓库新闻标记 2026-08-10 发布；模型卡输出 22.05 kHz waveform，约 0.8B GPT backbone，推理约 6 GB VRAM。

官方来源：

- [IndexTTS 官方仓库](https://github.com/index-tts/index-tts)
- [IndexTTS-2.5 官方模型卡](https://huggingface.co/IndexTeam/IndexTTS-2.5)
- [IndexTTS 2.5 官方技术报告页](https://index-tts.github.io/index-tts2-5.github.io/)
- [官方 License](https://github.com/index-tts/index-tts/blob/main/LICENSE)

| 能力 | 状态 | 官方证据 / 限制 |
|---|---|---|
| single-reference voice cloning | VERIFIED | 单一 `spk_audio_prompt` zero-shot cloning |
| timbre/emotion separation | VERIFIED | 独立 emotion reference、8 维 vector、emotion text；官方称与 timbre disentangled |
| Chinese pronunciation control | VERIFIED | `<word|Pinyin>`；并支持 CMU/Kana；只保证有效词表组合 |
| relative speed control | VERIFIED | `duration_factor` 0.5–2.0；>1 变慢 |
| exact target duration | UNVERIFIED | 官方 2.5 可见接口证明 relative speed；未证明任意 `targetDurationMs` 精确命中 |
| multi-speaker generation | UNVERIFIED | 官方 2.5 文档未证明单次多 speaker contract |
| multi-turn context | UNVERIFIED | 官方文档未证明跨轮上下文输入 |
| isolated speaker tracks | UNVERIFIED | 无官方输出 contract |
| batch | VERIFIED | 官方仓库有 batch/CLI 路径；属于多任务执行，不等于 multi-speaker |
| deterministic behavior | PARTIALLY VERIFIED | `use_random=False` 是默认且关闭显式随机采样；跨 GPU/版本 bitwise determinism 未证明 |
| deployment/API | VERIFIED | Python API、WebUI、官方指向 vLLM production recipe；没有等同 managed SaaS 的稳定 REST SLA 证明 |
| license/production | VERIFIED RISK | Bilibili Model Use License + disclaimer，不是 Apache/MIT；正式商业使用必须完成法务审查 |

架构适配：适合“一条 canonical spoken item → 一个 dry speech clip”的现有 ownership；reference audio、emotion control、duration factor、拼音控制都可由 Provider adapter 编译，不应进入 Character Understanding。

## 10. Fish Audio S2 Pro Capability Audit

核验时间：2026-08-27。官方 repository/model card 称 S2-Pro 为 4B/5B 级 full model；官方 hosted API 当前同时列出 `s2-pro`、`s2.1-pro` 与 free variant，本报告只审计用户指定的 S2 Pro 能力，不把后续 S2.1 能力自动归因给 S2 Pro。

官方来源：

- [Fish Speech 官方仓库](https://github.com/fishaudio/fish-speech)
- [Fish Audio S2 Pro 官方模型卡](https://huggingface.co/fishaudio/s2-pro)
- [Fish Audio 官方 TTS API](https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech)
- [Fish Speech 官方文档](https://speech.fish.audio/)
- [官方 License](https://github.com/fishaudio/fish-speech/blob/main/LICENSE)

| 能力 | 状态 | 官方证据 / 限制 |
|---|---|---|
| voice cloning/reference | VERIFIED | hosted API 支持 `reference_id` 或 zero-shot `references`；repo 称 10–30s reference |
| multi-speaker | VERIFIED | S2 family speaker tags + voice ID/reference arrays；repo 也描述 multi-speaker reference |
| multi-turn context | VERIFIED | 官方 repo 明确 extended context 利用 previous information |
| isolated speaker tracks | UNVERIFIED | hosted endpoint 返回单一音频流，未找到官方 isolated stem 输出说明 |
| emotion/performance tags | VERIFIED | sub-word natural-language tags，含 whisper/excited/angry/pause 等 |
| pronunciation control | UNVERIFIED | 官方 API 证明中英 normalization，但未证明类似 Pinyin/phoneme 的确定读音 override |
| relative speed/volume | VERIFIED | hosted API `prosody.speed/volume` |
| exact target duration | UNVERIFIED | 没有 `targetDurationMs` 精确命中证明 |
| output formats | VERIFIED | WAV/PCM/MP3/Opus，多 sample rate，mono |
| hosted API | VERIFIED | `/v1/tts`、Bearer、streaming SDK；具体商用条款仍需对 API Terms 单独法务确认 |
| self-host deployment | VERIFIED | official server/Docker/SGLang/vLLM guidance |
| batch/throughput | VERIFIED AT ENGINE LEVEL | continuous batching/streaming；不等于业务 batch idempotency |
| deterministic behavior | UNVERIFIED | API 有 temperature/top_p，未证明可重现相同 waveform |
| license/production | VERIFIED RISK | weights 为 Fish Audio Research License；免费研究/非商用，商用需另行授权 |

架构适配：它的 multi-speaker/multi-turn 能力是 Bakeoff 优势，但 Historical Plugin v1 仍应要求 isolated per-spoken-item dry track；不能因 Provider 能一次生成多人混合，就改变 canonical Dialogue ownership 或把 mixed track 直接交给 Lip Sync。

## 11. Role Dubbing Candidate Comparison

| 维度 | IndexTTS 2.5 | Fish Audio S2 Pro |
|---|---|---|
| Character voice stability | single-reference clone；关闭 random 有利于一致性；需 Bakeoff | reference ID/zero-shot clone；官方称 consistent；需 Bakeoff |
| Emotion separation | 明确与 timbre 分离，reference/vector/text 三路 | inline natural-language performance tags；是否严格与 timbre 分离需 Bakeoff |
| Chinese intelligibility | 官方称改善拼音/自然度；需本项目 CER/听审 | 官方公布很低中文 WER benchmark；需本项目复验 |
| Duration control | `duration_factor` 相对语速；精确窗口未证 | API speed；精确窗口未证 |
| Pronunciation control | 明确 Pinyin override | 未找到明确 phoneme/Pinyin override |
| Multi-speaker | UNVERIFIED | VERIFIED |
| Dialogue context | 跨 segment prosody 有官方限制；multi-turn 未证 | multi-turn VERIFIED |
| Isolated speaker tracks | UNVERIFIED | UNVERIFIED；multi-speaker output 不等于 stems |
| Lip Sync friendliness | 单句 dry clip、speed/Pinyin 对齐友好 | 单句或上下文强；必须额外要求 per-speaker dry output |
| Self-host | VERIFIED，约 6GB VRAM model-card claim | VERIFIED，模型更大且高性能示例使用 H200 |
| API integration | Python/vLLM serving；需自建稳定 HTTP facade | 官方 hosted `/v1/tts` + self-host server |
| Commercial/license risk | custom Bilibili license，需审查 | Research License；weights 商用需另授权 |
| Current project fit | 强单角色、中文发音、时长相对控制候选 | 强表演、多轮、多角色候选 |

不做总分。两者都必须经过同输入、同审查的 Stage A Bakeoff。

## 12. Voice Binding / Voice Reference Design

### 12.1 Voice Binding

推荐继续：

```text
Work.content.voiceProfiles[]
  key = speakerKey
  creativeProfile = provider-neutral stable voice identity
  providerMappings[]
    provider / model / voiceId-or-reference-binding
    materialParameters
    status = CANDIDATE | APPROVED | RETIRED
```

这是现有最小长期机制。Binding 属于 Work-scoped character voice identity，不属于 Scene、Media 或 Plugin Run Context。Media 记录“本次用了哪个 binding fingerprint”，但不拥有 binding。

不推荐：

- new `voice_binding` table / Entity / CRUD Tool；
- Character Asset 直接拥有 Provider voice ID；
- 每个 Scene 复制 voice mapping；
- 把 Voice Binding 只写在输出 Media，导致下一 Scene 无法稳定发现。

### 12.2 Reference audio lifecycle

```text
physical reference WAV/MP3
  → Media(AUDIO, purpose=VOICE_REFERENCE, immutable/hash/duration)
  → optional Asset(type=AUDIO_INPUT, referenceMediaIds=[...])
  → Work.voiceProfiles[].providerMappings[].materialParameters references stable Media/Asset ID
```

- reference audio 首先是 `Media`，因为它是物理对象；
- 只有当一组参考音频本身需要可命名、可审、跨 Scene/Run 复用的语义身份时，才创建既有 `AUDIO_INPUT` Asset；
- 不新增 Asset type；
- Media 不承担 binding approval；
- provider 临时 upload ID、signed URL、local path 不持久化为 Domain fact。

## 13. Audio Intelligibility / ASR QC

### 13.1 问题定义

```text
exactTextInputVerified = true
≠ generated waveform says the exact text
≠ listener can understand the exact text
```

### 13.2 最小 QC

```text
generated dry Dialogue Audio
→ ASR (independent from TTS Provider where practical)
→ normalized transcript
→ compare canonical exactText
→ CER + structured mismatch findings
→ human review when threshold/finding requires
```

至少检查：

- CER；
- missing characters / words；
- extra characters / hallucination；
- repetition；
- historical proper noun / person / place errors；
- reviewed pronunciation guidance mismatch；
- inaudible/clipped/noisy spans。

不能把 ASR 结果设为新的 Dialogue 或字幕真源。ASR 自身会错，专名、古语、口音和情绪表演必须人工复核。

### 13.3 Layer placement

| Layer | Responsibility |
|---|---|
| Role Dubbing Workflow | **owns ASR execution, normalization, compare, thresholds and QC result** |
| Provider adapter | 只做某一 TTS/ASR provider transport/compile；不做业务最终裁决 |
| Plugin Skill | declares gate, reads summarized result, decides stop/review/retry |
| MCP | projects one high-level Tool; no `run_asr` Tool |
| drama-service | persists approved Media and compact QC provenance; no ASR runtime |

结论：ASR 是 workflow-internal capability，不是 Drama Domain，也不是独立 Skill-facing Tool。

## 14. Timing / Speech Window Audit

### 14.1 四类时长权威

| Duration | Produced by | Persisted/consumed at |
|---|---|---|
| Scene Dialogue estimate | `scene-development` heuristic + review | `spokenContent[].estimatedDurationMs`；Shot feasibility input |
| Shot planned duration | `shot-design` creative/coverage decision | `Shot.content.plannedDurationMs`；visual production budget |
| Video actual duration | visual Provider output + Host probe | `Media.durationMs`；Lip Sync physical input |
| Audio actual duration | Role Dubbing output + Host probe | `Media.durationMs`；timing fit/Lip Sync input |

“谁决定一个 Shot 持续几秒”的答案：**Shot Design / approved coverage plan 决定 `plannedDurationMs`；Provider 只能编译/近似，物理文件由 Media probe 记录实际时长。**

### 14.2 当前稳定 contract 与 gap

稳定：positive `plannedDurationMs`、Dialogue estimates、`TargetTimingPolicy`、Media actual duration、`av-assembly-v1.timeline.startMs/sourceInMs/sourceOutMs`。

Gap：没有 generation 前的 `speechWindow.startMs/endMs`；当前 Shot convention 还明确禁止把 audio timing 放入 Shot content。

### 14.3 推荐 speech window 边界

推荐在 **transient Production Timing Plan** 中产生：

```text
shotId
videoTargetDurationMs
spokenContentId
coverage group
speechWindow { startMs, endMs }
```

生成完成后，把 committed placement 固化到 derived Audio Mix / Lip-Synced Video / Final AV Media manifest。不要新增 Timeline Entity，不要在 Shot content 复制 exact text/audio ID/word timing。

## 15. Video-first vs Audio-first vs Timeline-first

### 15.1 Architecture A — Video First

优点：Visual Provider 可先锁镜头；适合无对白、画外音、reaction、宽景；复用既有已生成 raw Video。

缺点：固定 Video 与 speech window 会给 TTS 施加强压；过度 time-stretch 损害可懂度/表演；超窗时重做 Video 成本高；嘴部运动可能与对白节奏天然冲突。

Retry cost：Audio 可多试但 Video 已沉没；最终可能仍需 visual re-plan。

### 15.2 Architecture B — Audio First

优点：最终 Audio duration 可直接决定讲话镜头长度；更保护可懂度、呼吸与表演；Lip Sync 输入清晰。

缺点：Video Provider 常只支持离散时长；把所有镜头节奏交给 TTS 会破坏 Scene pacing；动作、reaction、silence 与 montage 不应由对白独占；Audio 变更会触发 Video 重生。

适用：纯 talking head、独白、口播式 Shot。

### 15.3 Architecture C — Timeline First / Hybrid

优点：复用现有 `estimatedDurationMs + plannedDurationMs + DURATION_FEASIBILITY`；在付费生成前协调 speech/action/silence；Visual 与 Dubbing 可并行；只有 fit 超界才重规划；保留导演自由。

缺点：需要一个小型 transient Timing Plan；Provider 实际时长仍需 post-fit；不能假装计划窗口就是物理事实。

当前项目 fit：最高。它是现有代码的自然延伸，不是新 Timeline Domain。

## 16. Recommended Production Ordering

主方案：`TIMELINE_FIRST_HYBRID`

理由：

1. 当前 `shot-design` 已在物理生产前完成 Dialogue binding 与 duration feasibility；
2. Shot 的创意持续时间不应由任一 TTS Provider 反向统治；
3. Role Dubbing 需要目标窗口，但最终 Audio 仍可能偏差；
4. Visual generation 成本高，预先时间预算比 Video-first 的事后挤压更安全；
5. 无对白/不露嘴 Shot 可继续直接 Visual-first；纯讲话 Shot 可作为 Audio-first 特例。

特殊模式：

- `VIDEO_FIRST`：无 Lip Sync、画外音、宽景、reaction、已有不可重生历史素材；
- `AUDIO_FIRST`：单人 talking head / 独白，且 Video Provider 可接受目标时长；
- 默认其余 Dialogue Shot：Hybrid。

## 17. Lip Sync Architecture

Lip Sync 是独立 step：

```text
Raw Video Media (immutable)
  + reviewed dry Dialogue Audio Media
  + active speaker / optional face target
  + committed speech window
→ production.lip_sync
→ new Media(VIDEO, purpose=LIP_SYNCED_VIDEO)
→ LIP_SYNC_QC
```

### 17.1 Generation attempt / Media identity

- Lip Sync 应有独立 **attempt identity**，复用 sourceRef fingerprint/attempt pattern 与 `ProviderResultUnknown` 语义；
- 不新增 GenerationAttempt Entity；
- 成功物理输出产生新 Media；失败但无输出只保存轻量 run evidence/error，不制造空 Media；
- 原始 Video 永远保留；
- lip-synced output 是 derived Media；
- final mixed video 是另一个 derived Media，不覆盖 lip-synced video。

### 17.2 Lip Sync quality gate

自动检查适合：AV duration/stream、AV drift、SyncNet-like confidence、duration preservation、frame decode、gross temporal instability。

人工 Review 负责：face identity、嘴唇/牙齿 artifacts、表情自然度、遮挡、历史人物脸部一致性、可接受的局部画质下降。

自动 PASS 不能替代人工画面审查；自动 FAIL 可阻止进入 Audio Post。

## 18. Lip Sync Provider-neutral Contract

最小输入：

| Field | 分类 | 说明 |
|---|---|---|
| `videoMediaRef` | REQUIRED | reviewed raw Video Media |
| `audioMediaRef` | REQUIRED | reviewed per-speaker dry Dialogue Audio |
| `speakerRef` | REQUIRED semantic | stable speakerKey；单脸时可由 plan 推导但必须可追溯 |
| `faceTarget` | OPTIONAL | 多脸/ambiguous shot 才需要；可为 stable character/asset + transient bbox/track hint |
| `speechWindow` | OPTIONAL | full-clip talking 可省；局部讲话/多人/有前后动作时需要 |

最小输出：

| Field | 分类 | 说明 |
|---|---|---|
| `lipSyncedVideoMediaRef` | REQUIRED | new derived Video Media |
| `durationMs` | REQUIRED | physical probe |
| `syncMetadata` | OPTIONAL | compact provider-neutral QC/provenance summary |

建议 contract：

```text
LipSyncRequest v1
  videoMediaId
  audioMediaId
  speakerKey
  speechWindow?
  faceTarget?

LipSyncResult v1
  videoMediaId
  durationMs
  qc { status, avDriftMs?, syncConfidence?, humanReviewRequired }
```

不要把 workflow node、mask path、detector output、Provider job URL 写入 Domain contract。

## 19. Multi-face / Active Speaker Considerations

现有 `speakerKey + spokenContentBindings.coverageIntent=ON_SCREEN_SPEAKER` 已能确定语义说话者，但不能自动把人绑定到画面中的哪张脸。

Contract 只需预留 optional `faceTarget`：

```text
character/asset reference
+ optional transient faceTrackId or normalized bounding box hint
+ applicable time range
```

规则：

- 单一清晰正脸：无需额外 face binding；
- 多脸且 active speaker 明确：必须有 faceTarget 或 workflow 能可靠解析；
- 无法可靠解析：`ACTIVE_SPEAKER_FACE_AMBIGUOUS`，不得随机选择第一张脸；
- bbox、detector confidence、frame-by-frame track 默认 transient；只有为重现/审计必要的摘要进入 Media provenance。

内容生产策略（建议而非硬规则）：Dialogue-heavy coverage 优先单一 active speaking face；speaker medium/close → listener reaction → next speaker medium/close。多人同框、正脸并存、复杂遮挡可以保留导演自由，但必须显式提高 workflow 与 review 成本。

## 20. Media / Asset / Provenance Impact

### 20.1 Media provenance

现有 Media 可通过 envelope + open content 表达：

```text
purpose
sourceRef fingerprint / attempt identity
durationMs / mimeType / fileSize / contentHash
content.schemaVersion
content.derivedFromMediaIds
content.generationAttempt
content.reviewStatus
content.provider / model / material settings fingerprint
content.qc summary
```

最小 Gap 不是数据库字段，而是尚未冻结 `role-dubbing-media-v1` 与 `lip-sync-media-v1` content convention。Java 不需要解析这些字段。

### 20.2 Asset type audit

| Proposed type | 分类 | 结论 |
|---|---|---|
| `VOICE_REFERENCE` | CAN_REUSE_EXISTING | 用 `AUDIO_INPUT` Asset + `Media purpose=VOICE_REFERENCE` |
| `CHARACTER_VOICE` | NOT_NEEDED | binding 在 Work.voiceProfiles；避免 Asset/voice identity 混同 |
| `DIALOGUE_AUDIO` | NOT_NEEDED | Media purpose 足够，不是 reusable semantic Asset |
| `LIP_SYNC_INPUT` | CAN_REUSE_EXISTING / NOT_NEEDED | raw Video/Audio 直接按 Media ID 输入；需要 Asset 时已有 VIDEO_INPUT/AUDIO_INPUT |
| `LIP_SYNC_VIDEO` | NOT_NEEDED | output 是 Media purpose，不是 Asset |

### 20.3 Persistence audit

长期：approved Work voice binding、approved reference Media/optional AUDIO_INPUT Asset、reviewed Dialogue Audio、reviewed raw Video、reviewed lip-synced Video、final mixed Video、committed manifests/fingerprints。

Transient：candidate ranking、temporary Provider prompt/tag、完整 ASR intermediate、face detection boxes/tracks、timing solver candidates、signed URLs、provider upload IDs、rejected scratch outputs（若无审计价值）。

## 21. Domain Impact Matrix

| Domain | Impact | Evidence / recommendation |
|---|---|---|
| Work | METADATA ONLY | 继续用 open content 的 voiceProfiles/providerMappings；不加列/Entity |
| Script | NO CHANGE | 不拥有声音、时序或 Media |
| Episode | NO CHANGE | 不拥有声音、时序或 Media |
| Scene | NO CHANGE | spokenContent 已足；ASR transcript 不回写 |
| Shot | CONTRACT GAP | 不改 Java；transient production plan 需要 speech window/active speaker/lipSyncRequired，Shot content 继续只保存 binding + plannedDuration |
| Asset | NO CHANGE | 复用 AUDIO_INPUT/VIDEO_INPUT 与 referenceMediaIds |
| Media | METADATA ONLY | 冻结 purpose/content provenance convention；现有 envelope/DB 足够 |

`DOMAIN_CHANGE_REQUIRED = NONE`。Shot 的 gap 是 production contract/convention gap，不是新字段或表。

## 22. MCP Tool Contract Impact

### 22.1 Tool Contract Matrix

| Category | Tools |
|---|---|
| Existing | Work/Script/Episode/Scene/Shot/Asset/Media CRUD/read/list/search；`generate_image/video/audio`；context；research |
| Reuse | `work.get_work`、`scene.get_scene`、`shot.get/list`、`asset.get/search`、`media.get/list/import/resolve`、existing `generate_audio` internals |
| Need extension | error taxonomy/fingerprint conventions；Media content conventions；no required Java Tool extension |
| Potentially needed | `production.generate_role_dubbing`、`production.lip_sync` |
| Should NOT exist | `create_voice`、`clone_voice`、`rank_voice`、`generate_emotion`、`generate_dialogue`、`run_asr`、`fit_duration`、`create_timeline`、`detect_face`、`track_face`、`lip_sync_face`、Provider-specific Tools |

### 22.2 新 Tool 判定

- Role Dubbing：**需要 1 个高层 Tool**，因为现有 output=Media 无法无破坏地表达 workflow QC/result；旧 `generate_audio` 保留。
- Lip Sync：**需要 1 个独立 Tool**，因为它有两个 durable Media inputs、独立成本/重试/QC 和 derived output；不能塞入 `generate_video`。
- MCP service 本身无需 domain-specific implementation；动态投影即可。

## 23. Service Responsibility Matrix

注：表中的 “Skill” 指 Skill Core 的方法/门槛；“drama-plugin” 指 typed contract、adapter 与 Host utility。

| Responsibility | Skill | drama-plugin | drama-mcp-service | drama-service | External Workflow |
|---|---|---|---|---|---|
| Character understanding | 定义方法/证据/neutrality | typed objects | 投影 | Work/Scene facts persistence | — |
| Voice casting brief | 生成 provider-neutral brief | request contract | 投影 | optional Work metadata | consume brief |
| Voice generation | 不实现 | high-level adapter/seam | 投影 | persist Media | **owns model inference** |
| Voice binding | 提议并要求 human approval | fingerprint/status convention | 投影 | persist Work open content | produce candidate evidence |
| Dialogue synthesis | gate/exact text | request/result contract | 投影 | persist Media | **owns render** |
| ASR QC | declares acceptance gate | summarized QC schema | 投影 | compact evidence only | **owns ASR/compare** |
| Timing fit | defines stop/re-plan rule | transient plan/result helpers | 投影 | committed manifest only | render-level fit attempt |
| Video generation | visual plan/review | existing production contract | 投影 | persist Media | **owns inference** |
| Lip sync | declares input/review | Tool contract/adapter | 投影 | persist derived Media | **owns inference/QC metrics** |
| Media persistence | selects semantics | Media provider | 投影 | **owns DB/storage/hash/resolve** | returns physical output |
| AV mix | declares order/review | Host deterministic utility/manifest | no special logic | persist final Media | optional external post engine |

## 24. Review Gates

| Gate | Value | Minimal policy |
|---|---|---|
| `VOICE_CASTING_REVIEW` | 高 | 仅首次 binding、material voice/reference change 或 provider migration；人审 |
| `DIALOGUE_AUDIO_REVIEW` | 必须 | 每个 stale output：ASR/intelligibility + human performance/voice/pronunciation |
| `LIP_SYNC_REVIEW` | 必须于 required shots | auto metrics + human artifact/identity review |
| `FINAL_AV_REVIEW` | 必须但轻量 | sequence/sample review：mix、dialogue clarity、continuity、stream/hash |

不建立审批系统；沿用 Media `reviewStatus` 与 attempt/canonical sourceRef。Casting PASS 更新 Work mapping；其余 PASS 选择 canonical Media。

## 25. Retry / Failure Semantics

### 25.1 Reuse current safety

- fingerprint material input；
- PASS canonical sourceRef；
- PENDING/FAILED/debug attempt sourceRef；
- submission outcome unknown 时返回 `AMBIGUOUS_RESULT`，先恢复 job，禁止盲目重投；
- polling/fetch/download 对同一 job 安全重试；
- technical retry 不改变 creative input，不等于 review revision；
- rejected output 保留为 evidence 但不占 canonical key。

### 25.2 建议错误类别

```text
ROLE_DUBBING_QC_FAILED
INTELLIGIBILITY_QC_FAILED
DURATION_FIT_FAILED
VOICE_BINDING_REVIEW_REQUIRED
LIP_SYNC_QC_FAILED
ACTIVE_SPEAKER_FACE_AMBIGUOUS
PROVIDER_SUBMISSION_OUTCOME_UNKNOWN / AMBIGUOUS_RESULT
```

不要为每个 Provider error 新建 Tool。外部 workflow 把 raw error 映射为稳定高层类别。

### 25.3 Explicit rejection

人审 reject 不是 technical retry。只有明确的 targeted reason（错字、专名、表演、音色、超窗、嘴部 artifact）才允许新 attempt；同一失败重复三次应停止并请求 re-plan/provider change，不能无限生成。

## 26. Target TO-BE Architecture

```text
[UNCHANGED] Work → Script → Episode → Scene
                                   ↓
[MODIFIED] Shot Planning
              ├─ existing plannedDurationMs / spokenContentBindings
              └─ [NEW transient] Timing Plan
                   activeSpeaker / speechRequired /
                   targetDuration / speechWindow / lipSyncRequired
                         │
             ┌───────────┴────────────┐
             ↓                        ↓
[UNCHANGED] Visual Production    [NEW] Role Dubbing Workflow
             ↓                        ├─ existing Character Understanding
       Raw Video Media                ├─ provider casting / speech
                                      ├─ ASR intelligibility QC
                                      └─ Dialogue dry Audio Media
             └───────────┬────────────┘
                         ↓
                  [NEW] Timing Fit
                         ↓
                  [NEW] Lip Sync Step
                         ↓
              Derived Lip-Synced Video Media
                         ↓
              [NEW] Audio Post / Mix
              Dialogue + SFX + Ambience + Music
                         ↓
                 Final Shot / Final AV Media
```

`DEPRECATED`：把 Qwen preset ranking / Voice Design 调参当作最终专业主流程；把 final mixed audio 作为 Lip Sync 输入；把 Lip Sync 隐藏进 video generation。

## 27. AS-IS vs TO-BE Gap Matrix

| Capability | AS-IS | TO-BE | Action |
|---|---|---|---|
| hierarchy | stable 7-domain chain | same | UNCHANGED |
| Character understanding | typed, provider-neutral | same upstream brief | UNCHANGED |
| voice binding | Work mapping, mostly pending operationally | approved mapping + reference Media convention | MODIFIED metadata convention |
| speech generation | `generate_audio` → Media | high-level Role Dubbing Result + legacy audio | NEW Tool, reuse internals |
| intelligibility | input exactness + human expectation | ASR/CER/findings + human gate | NEW workflow QC |
| timing | estimates + planned duration + final manifest | transient pre-generation speech window | NEW transient contract |
| raw video | stable Media | same | UNCHANGED |
| lip sync | absent/deferred | explicit Tool/attempt/derived Media | NEW |
| provenance | open Media content/sourceRef | frozen role/lip manifests | MODIFIED convention only |
| audio post | minimal dialogue mux | dry-dialogue lip sync, then full mix | NEW later |
| Java domains | 7 stable entities | same | UNCHANGED |
| MCP projection | generic | generic | UNCHANGED |

## 28. P0 / P1 / P2 / Deferred

### P0 — Required Before Role Dubbing Integration

1. Freeze `production.generate_role_dubbing` input/output contract as thin wrapper/reuse of `SpeechGenerationRequest`。
2. Freeze `role-dubbing-media-v1` provenance and canonical/attempt sourceRef material。
3. Define Intelligibility QC v1：CER + missing/extra/repetition/proper noun + human-review-required。
4. Define approved Voice Binding/reference reuse convention on existing Work voiceProfiles + Media/AUDIO_INPUT。
5. Add only offline contract/unit tests and mock workflow tests。

If skipped：系统无法区分“普通 TTS 成功”与“专业配音通过”，因此 P0 必须。

### P1 — Required Before Lip Sync

1. Freeze transient Timing Plan / speechWindow convention without changing Shot Domain。
2. Freeze `production.lip_sync` request/result and provider-neutral error/QC contract。
3. Freeze `lip-sync-media-v1` derivedFrom/fingerprint/review convention。
4. Define active speaker / optional faceTarget behavior and ambiguous multi-face failure。
5. Stage B offline adapter contract tests + one separately authorized Bakeoff plan。

### P2 — Required Before Final AV Production

1. Freeze dry Dialogue → Lip Sync → SFX/Ambience/Music mix ordering and final mix manifest。
2. Add deterministic Audio Post capability preflight、stream/duration/hash review。
3. Define `FINAL_AV_REVIEW` minimal sequence gate and stale propagation from any input。
4. Run separately authorized integrated single-Shot E2E after Stage A/B selection。

### Deferred

- Voice/Audio/Timeline/FaceTrack/GenerationAttempt database entities；
- word/phoneme timing as mandatory contract；
- isolated speaker stems until a Provider proves them；
- automatic face tracking/domain persistence；
- Scene-wide sound design、mastering、spatial audio；
- tool explosion and Provider-specific Tools；
- rewriting current three projects；
- automatic provider selection/score。

## 29. Risk Register

| Risk | Evidence / impact | Mitigation |
|---|---|---|
| architecture risk | audio Skill responsibility concentration | move render/QC orchestration behind one workflow Tool |
| provider lock-in | Qwen adapter and mapping artifacts already substantial | preserve SpeechGenerationRequest/Work creative profile; adapter-only syntax |
| license risk | Index custom license; Fish research license | legal review before commercial deployment; Bakeoff ≠ production authorization |
| GPU/resource risk | Index ~6GB claim; Fish larger; LatentSync 8/18GB; provider variance | capability preflight, separate deployment decision |
| commercial deployment risk | self-host/API terms differ | treat API terms and weights license separately |
| intelligibility risk | real user heard unintelligible output despite exact input | ASR/CER + proper noun + human QC mandatory |
| voice consistency risk | pending candidate or scene-local reselection | approved Work mapping reused across Scenes |
| lip-sync degradation | official MuseTalk notes identity/jitter; LatentSync guidance tradeoff | preserve raw video, separate derived Media, human gate |
| duration mismatch | neither Role Dubbing candidate proves exact target ms | Hybrid budget + bounded fit + visual re-plan |
| multi-character risk | semantic speaker does not equal detected face | optional faceTarget + fail ambiguity + shot strategy |
| Media provenance risk | open content has no frozen role/lip convention | schemaVersion + derivedFrom IDs + input fingerprint + review status |
| retry/cost risk | paid submission outcome may be unknown | existing ambiguous-result recovery semantics |

### 29.1 Observed technical debt, not fixed in this batch

Only code-observed items：

1. Batch-specific runtime names such as `BATCH72R_QWEN_MODEL` remain in integration scripts。
2. Old Qwen model families, preset candidate ranking, Voice Design and Bailian-specific implementation occupy a large single provider module。
3. `audio-production` Skill combines Character analysis、casting、TTS、review、fit 与 final AV mux。
4. `ProductionProvider.generate_audio(prompt, reference_media_ids, parameters)` remains a generic legacy seam; structured speech is wrapped through `parameters.speechRequest`。
5. Speech config still has provider enum `disabled/openai/bailian_qwen` and shared local `output_directory`，so future workflow deployment topology is not yet generic。
6. Visual production Tool schema has no typed target duration; current duration reaches Provider through parameters/host planning。
7. Media provenance relies on open JSON conventions; Role Dubbing/Lip Sync schema versions尚未冻结。

这些都不阻断本次架构结论，也不应在接入前一次性重构。

## 30. Next Bakeoff Proposal

### 30.1 Stage A — Role Dubbing selection

固定输入：

```text
same Character Understanding
same Character Voice Brief
same approved/reference voice strategy
same canonical Dialogue exactText
same Scene State + Performance Brief
same target duration policy
same output format and review method
```

比较 IndexTTS 2.5 vs Fish Audio S2 Pro：角色音色适配、跨句角色一致性、中文可懂度/CER、专名发音、表演自然度、情绪控制、时长控制、重复/漏字、多角色能力、Lip Sync friendliness、推理成本/性能、部署复杂度与 license path。

样本应包含：平静陈述、克制高压、快速命令、历史专名、短句、长句、同角色跨 Scene、两角色交替。每个 Provider 使用相同审听表，不提前批准任何 binding。

### 30.2 Stage B — Lip Sync selection

固定同一 source Video 与同一 Stage A approved dry Dialogue Audio，比较 LatentSync、MuseTalk、Wav2Lip/其他当前可信 workflow。

官方资料边界：

- [LatentSync 官方仓库](https://github.com/bytedance/LatentSync)：1.6、Apache-2.0、512 face region、18GB minimum inference claim；1.5 8GB；官方说明 guidance 提高 sync 可能增加 distortion/jitter。
- [MuseTalk 官方仓库](https://github.com/TMElyralab/MuseTalk)：1.5、audio+video input、Chinese/English/Japanese、30fps+ V100 claim、MIT code/商业可用模型声明，但依赖许可需逐项核验；官方明确 identity detail 与 jitter limitations。
- [Wav2Lip 官方仓库](https://github.com/Rudrabha/Wav2Lip)：open-source weights 明确 non-commercial，当前仅作为 contract/quality baseline；商业版是另一产品路径。

指标：嘴型准确、中文表现、identity preservation、teeth/lip artifacts、temporal stability、multi-face handling、分辨率、速度、GPU、license、失败恢复。不得下载模型或在本批运行。

### 30.3 Stage C — Integrated AV E2E

在 A、B 各自有结论后，使用一个已批准 Shot 验证：Timing Plan → Role Dubbing → ASR QC → raw Video → Lip Sync → LIP_SYNC_QC → Dialogue/SFX/Ambience/Music mix → Final AV Media/resolve/hash。

Stage A/B/C 拆分合理且必要：否则声音质量、嘴型质量、时长 fit 与 mix 失败会互相污染，无法定位 Provider 或 Contract 问题。

## 31. Final Recommendation

### Q1 — 主创作链是否调整？

**不调整 Domain 主链。** `Work → Script → Episode → Scene → Shot` 保持不变；只在 Shot Planning 与物理生产之间增加 transient Timing Plan，并在 production pipeline 增加 Role Dubbing、Lip Sync、Audio Post steps。

### Q2 — Role Dubbing 位于 Video 前、后还是 Hybrid？

**`TIMELINE_FIRST_HYBRID`。** Visual 与 Role Dubbing 在同一已审时间预算下并行；final Audio/Video 完成后做 Timing Fit，再 Lip Sync。Video-first/Audio-first 只作为特殊 Shot 模式。

### Q3 — 新 Role Dubbing Tool 还是继续 generate_audio？

**新增一个 `production.generate_role_dubbing` 高层 Tool，保留并复用 `production.generate_audio`。** 理由是 QC/result 与专业 workflow 语义无法在不破坏 Media output contract 的情况下清晰表达；但不得新增第二套 Speech Provider abstraction 或暴露内部步骤。

### Q4 — Lip Sync 是否独立 step？

**是。** 独立 attempt/fingerprint/QC，输出新 derived Media，保留 raw Video；未来用一个 `production.lip_sync` Tool。

### Q5 — 是否修改 Work/Script/Episode/Scene/Shot/Asset/Media Domain？

**不修改 Java Domain、不加表。** Work/Media 使用现有 open metadata；Shot 的 speech window 位于 transient Production Plan；Asset 复用 AUDIO_INPUT/VIDEO_INPUT。

### Q6 — Voice Binding 复用哪个机制？

**`Work.content.voiceProfiles[].providerMappings[]` approved mapping。** approved physical reference 用 Media；有必要时由既有 AUDIO_INPUT Asset 组织 referenceMediaIds。

### Q7 — ASR / Intelligibility QC 在哪层？

**External Role Dubbing Workflow owns execution；Plugin Skill sees summarized QC；drama-service only persists compact evidence。** 不新增 Skill-facing `run_asr` Tool。

### Q8 — Shot Planning 是否提前产生 timing/speech-window？

**是，但只在 transient Production Timing Plan。** 继续持久化现有 `plannedDurationMs` 与 spoken bindings，不把 audio timeline/word timing 塞入 Shot Domain；committed window 最终进入 derived Media manifest。

### Q9 — IndexTTS 2.5 与 Fish Audio S2 Pro 各自角色？

**IndexTTS 2.5**：Stage A 的单角色 reference cloning、音色/情绪分离、中文 Pinyin control、相对 duration control 候选。  
**Fish Audio S2 Pro**：Stage A 的 fine-grained performance、multi-turn context、multi-speaker 与 hosted API/self-host 双路径候选。  
两者的 isolated stems 与精确 target duration 均未被官方资料证明，不能预设。

### Q10 — 下一步最小实现批次？

**只做 P0 Contract/Foundation：** 定义 `RoleDubbingRequest/Result` 的最小 wrapper、一个 `production.generate_role_dubbing` Tool schema、Intelligibility QC v1、Work voice binding/reference convention、Media provenance/fingerprint convention，以及 mock/offline tests。不要同时接 Index/Fish，不做真实生成，不做 Lip Sync。

## 32. Static Verification / Git Safety Baseline

### Git

| Repository | branch / HEAD | pre-audit status |
|---|---|---|
| drama-plugin | `master` / `e842554` | 4 个既存 untracked `.DS_Store`；未触碰 |
| drama-mcp-service | `main` / `e2beb17` | clean |
| drama-service | `main` / `382140e` | clean |

### Tests

| Suite | Result |
|---|---|
| drama-plugin `.venv/bin/python -m pytest -q plugin/tests` | `161 passed in 1.21s` |
| drama-mcp-service `.venv/bin/python -m pytest -q tests` | `18 passed in 0.94s` |
| drama-service `mvn -q test` | exit 0；43 tests，0 failure/error/skip |

首次 `python -m pytest` 仅因 shell 无 `python` alias 未启动；随后使用各仓库既有 `.venv` 完成 baseline。没有安装依赖。

### Prohibited execution confirmation

```text
REAL_TTS_CALLS = 0
COMFY_UI_CALLS = 0
COMFY_CLOUD_CALLS = 0
LIP_SYNC_CALLS = 0
NEW_AUDIO_FILES = 0
NEW_VIDEO_FILES = 0
RUNTIME_CONFIG_CHANGES = 0
JAVA_DOMAIN_CHANGES = 0
```

## 33. Final Status

```text
ARCHITECTURE_AUDIT = COMPLETE

ROLE_DUBBING_IMPLEMENTATION = NOT_STARTED
INDEXTTS_INTEGRATION = NOT_STARTED
FISH_AUDIO_INTEGRATION = NOT_STARTED

LIP_SYNC_IMPLEMENTATION = NOT_STARTED

PRODUCTION_CODE_CHANGES = NONE

NEXT_BATCH = PROPOSED_ONLY
```

到此停止。等待用户决定下一批实现任务。
