# 67 — Batch 7.3B.1 Fish Audio 表演控制面与短语级表演审计

日期：2026-08-29（Asia/Shanghai）  
批次：Batch 7.3B.1 — Fish Audio Expressive Control Surface & Phrase-Level Performance Audit  
结论：`BATCH_7_3B_1 = PASS`

## 1. 执行摘要

本批接受用户对 7.3B 三案例的真实听审结论，不扩 DPD，也不扩
`AudioPerformanceBrief`。审计定位到 Case B 的主要问题发生在 Fish Provider
compilation：Brief 已明确“同级试探、观察空间、开放句尾”，但实际 Fish request
只收到 `speed=1.0 / volume=-2.0`，大量表演语义在 adapter 层丢失。

Fish 当前官方文档证明 S2-Pro 不止 speed/volume：它支持方括号自然语言
expression cues、`[emphasis]`、`[break]/[long-break]`，API 还暴露
temperature、top_p、chunk/continuity 等生成参数。因此上一批 Capability Matrix
“rhythm/pause/sentence ending 完全 unsupported”的判断不完整。

本批实现最小受限 rendered-text compiler 与 Capability Matrix 2.0，并完成 7 次
真实 TTS：5 条 native speed/volume control audit，2 条 Case B rendered-text
候选。Speed、volume 物理效果真实有效；B1/B2 均技术可播放、ASR intelligibility
PASS、稳定 Media/Drama Service roundtrip PASS。Phrase segmentation 没有进入：
单请求官方控制面已有可测效果，且艺术优劣仍待用户听审。

## 2. 用户听审反馈

- A：已有试探/表演倾向，较旧配音明显进步，但离成熟历史剧台词很远；
- B：明显生硬、不自然，是三条中问题最突出者；
- C：劝诫、谨慎方向基本成立；
- 总体差距：自然节奏、句内层次、心理动机停顿、行动性重音与人物态度句尾。

《老三国演义》只作为表演质量参照。本批没有模仿、复制或重建任何具体演员
声音。

## 3. 本批范围

已完成：仓库与 Fish 官方控制面审计、Capability Matrix 2.0、受限
canonical→rendered text 编译、speed/volume 实验、Case B 两个单请求候选、技术
QC、Media 持久化、A/C 防回归、全量测试与报告。

未做：DPD/Brief ontology 扩张、Voice Design/Create Model/Voice Clone、Phrase
segmentation/stitch、Provider 切换、7.3C、Visual/Video/Lip Sync、Java/DB/MCP CRUD。

## 4. Architecture Freeze

```text
DPD Core                 FROZEN / NO CHANGE
SceneDPD                  FROZEN / NO CHANGE
BeatDPD                   FROZEN / NO CHANGE
LineDPD                   FROZEN / NO CHANGE
DPDSnapshot               FROZEN / NO CHANGE
AudioPerformanceBrief     FROZEN / FIELD CHANGES = 0
CreativeVoiceProfile      FROZEN / NO CHANGE
Casting Contract          FROZEN / NO CHANGE
```

仅为 capability audit 给现有 `CapabilityStatus` 增加
`TEXT_RENDERABLE/SEGMENT_RENDERABLE` 两个状态；这不是 Brief ontology 扩张。

## 5. Fish AS-IS 控制面

仓库 7.3B 真实 payload：

```text
text
reference_id
format=wav
sample_rate=24000
normalize=true
model header=s2-pro
prosody.speed
prosody.volume
prosody.normalize_loudness=true
```

没有后处理变速、音量归一化、裁切或统一时长。Role Dubbing 在 Fish response 后只
写 WAV、probe、ASR QC、Media import；因此最终时长差异来自 Provider output。

## 6. Fish 官方 / 真实 Contract 审计

官方 REST schema 证明：

- speed 范围 0.5–2.0，volume 范围 -20–20；
- temperature 控制表现变化度，top_p 控制采样多样性；
- chunk length、min chunk length、condition on previous chunks、latency、repetition
  penalty、max tokens、early stop 与 quality-guard 属于生成稳定性/吞吐控制；
- S2 family 支持自然语言 expression markers；
- `[emphasis]`、`[break]`、`[long-break]` 是官方 text control；
- Chinese phoneme tags 解决发音，不等价于 articulation/acting control。

官方来源：

- [Fish Text-to-Speech API](https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech)
- [Fish Emotion Control](https://docs.fish.audio/developer-guide/core-features/emotions)
- [Fish Fine-grained Control](https://docs.fish.audio/developer-guide/core-features/fine-grained-control)
- [Fish Text-to-Speech Guide](https://docs.fish.audio/features/text-to-speech)

本批继续固定 `s2-pro`，不利用文档中新出现的 `s2.1-pro` 切换 Provider strategy。
Temperature/top_p 是随机性/多样性控制，不是“试探、权威、劝诫”的 typed
semantic control，不能替代表演 brief。

## 7. Speed 实验

固定 canonical text、speaker、Work Voice/Fish reference、model、volume=0、
normalize 与其他 request fields，只改变 speed：

| speed | total duration | speech-active | leading / trailing silence | Media |
|---:|---:|---:|---:|---|
| 0.6 | 2319 ms | 2056 ms | 156 / 107 ms | `media_c8fe26c148b64c7a86c6a4b47b106559` |
| 1.0 | 1483 ms | 1359 ms | 0 / 124 ms | `media_0ded82fefbc848c9a03fe38fbbc8f385` |
| 1.6 | 879 ms | 768 ms | 77 / 34 ms | `media_a33925e31c60438cbc50f27da37f10fb` |

`2056 > 1359 > 768 ms` 严格单调，slow/high active-duration 比为 2.68。
`prosody.speed` 确实进入并显著影响 S2-Pro generation。

7.3B 的 0.92/1.0 三条总时长同为 1483 ms，并非 wrapper 丢参或后处理统一裁切。
原因是差值太弱、台词太短，且生成具有随机变化；本批放大到 0.6/1.0/1.6 后
效应清晰。旧三条 active durations 实际分别为 A 1289、B 1338、C 1315 ms，
本来也并不完全相同。

## 8. Volume 实验

固定同一切面，只改变 volume，speed=1.0 且保留当前
`normalize_loudness=true`：

| volume | RMS dBFS | peak dBFS | speech-active | Media |
|---:|---:|---:|---:|---|
| -12 | -27.193 | -12.552 | 1225 ms | `media_3ba5771e2f884e17a142a2eabca40b6b` |
| 0 | -20.956 | -6.163 | 1359 ms | `media_0ded82fefbc848c9a03fe38fbbc8f385` |
| +6 | -14.958 | -0.259 | 1260 ms | `media_c058a29bb0384111970db484381138c1` |

RMS 与 peak 均严格单调，证明 volume 真实有效，且没有被 normalize_loudness
完全抵消。+6 dB 的 peak 已接近 0 dBFS，因此它只用于审计，不应成为常规表演
参数。Volume 只证明物理增益，不证明“下位谨慎”或任何戏剧语义。

## 9. Case B Root Cause

逐层审计：

```text
DPD
  probe / test reaction / peer / MEDIUM activation / HIGH control
  = 信息充分
↓
AudioPerformanceBrief
  responsive pace / observe listener / evaluative pause /
  non-commanding articulation / open ending
  = 信息充分
↓
7.3B Fish mapping
  speed=1.0 / volume=-2.0
  = rhythm/pause/emphasis/ending/control 丢失
↓
Fish request/model
  只接到数值 prosody，听感退化为朗读
```

主要根因是 Provider compilation 信息损失，不是 DPD 或 Brief 字段不足。其次，
短句与无 seed 的生成随机性限制了弱数值差异的可复现性。

## 10. Capability Matrix 2.0

| dimension | 状态 | 当前 Fish 实现面 |
|---|---|---|
| pace | SUPPORTED | native `prosody.speed` |
| volume | SUPPORTED | native `prosody.volume` |
| intensity | TEXT_RENDERABLE | S2 expression/tone marker；volume 仅物理近似 |
| control | TEXT_RENDERABLE | concise S2 natural-language expression marker |
| rhythm | TEXT_RENDERABLE | punctuation + `[break]/[long-break]` |
| pause | TEXT_RENDERABLE | `[break]/[long-break]`，不是精确毫秒停顿 |
| articulation | UNSUPPORTED | phoneme control 只管读音，不管咬字表演 |
| emphasis | TEXT_RENDERABLE | `[emphasis]` before word/phrase |
| sentence ending | TEXT_RENDERABLE | punctuation + sentence-level expression cue，非保证值 |
| pre-utterance preparation | APPROXIMATED | leading cue 可影响起音，不能保证心理/呼吸准备 |
| post-utterance hold | UNSUPPORTED | 无 durable hold control |

`SEGMENT_RENDERABLE` 被保留为 capability vocabulary，但本批没有任何 dimension
需要升级到它，也没有创建 Phrase Plan。

## 11. Text Rendering Experiment

Canonical SpokenContent 始终为 `你可知道后果？`，没有改 Scene 或
`SpeechGenerationRequest.exactText`。

| Ref | rendered representation | strategy | total / active | ASR | Media |
|---|---|---|---:|---|---|
| B0 | canonical | 7.3B baseline | 1483 / 1338 ms | prior PASS | `media_e0b7568bef8d494382ee7c9e4b911156` |
| B1 | `你……可知道后果？` | punctuation | 1715 / 1616 ms | PASS | `media_dfb294ac9ad84a849b3e484d7c89d8cd` |
| B2 | `[curious]你可知道[break][emphasis]后果？` | official S2 markers | 1390 / 1276 ms | PASS | `media_b4675623222a45a183a4a79623631f63` |

B1 比 B0 的 active duration 增加 278 ms（约 20.8%），说明省略号进入了实际
rendering。B2 的 waveform、时长、RMS/peak 均与 B0/B1 不同，且 markers 未被
ASR 当作对白。单次结果证明“有影响、可懂”，不能证明跨重复生成稳定，也不能
自动证明艺术更自然，因此 `TEXT_RENDERING_AUDIT = LIMITED`。

## 12. Phrase Plan 决策

`PHRASE_PLAN = NOT_NEEDED`。

原因：官方 S2 单请求已能表达 expression、pause、emphasis，两个候选也已经产生
可测且 intelligible 的差异。用户尚未听审 B1/B2，当前没有证据证明“分段生成 +
拼接”会比单次生成更自然。贸然拆段会新增 voice/pitch/room/noise/breath/boundary
continuity 风险，违反先证明必要性的门槛。

## 13. Phrase-Level Experiment

未执行 segment generation 或 stitch；segment count=0，额外 Fish calls=0。
本批的 phrase-level 实验只使用单请求 rendered text。Silent gap 也没有被冒充为
native dramatic pause。

## 14. Case B 改善结果

`CASE_B_ARTISTIC_IMPROVEMENT = PARTIAL`。

- 工程改善：PASS。B1/B2 均保存 canonical→rendered lineage、产生可测声学差异、
  ASR/technical/storage QC PASS；
- 艺术改善：PENDING。系统不能判断哪条更像真正的同级试探；
- 建议听审顺序：先 B0→B1（最小标点策略），再 B0→B2（官方 expression/pause/
  emphasis 策略）；
- 在用户选择前，两条均保持 experiment/PENDING，不自动进入默认 Role Dubbing
  mapping。

## 15. A/C Regression

A/C 没有重生成。原 stable Media 通过 Drama Service resolve/download/hash：

- A `media_a25dd7a0b7ef47adb4998f1c93ad44d3`
- C `media_1794a591609f4983b2dab68b05e49222`

生产 `map_audio_performance_to_fish()` 的 speed/volume 数值规则未改，默认 Role
Dubbing 仍发送 canonical exact text；experimental rendered text 未自动接入 A/B/C
正式生产。DPD/Brief frozen 与全量回归均 PASS。

## 16. Audio Technical QC

全部 7 条新实验音频：WAV PCM S16LE、mono、24 kHz、decode/playability PASS、
positive actual duration、leading/trailing silence、speech-active duration、RMS、peak、
content hash 均已记录；所有持久化后 bytes 经 Drama Service 下载并与 Media hash
一致。B1/B2 另经 Fish ASR intelligibility QC，CER/missing/extra/repetition 均满足
Role Dubbing policy。

审计过程中发现 Fish streaming WAV header 的 declared frame count 是占位值。
第一版 probe 信任 header，产生约 24 小时假时长；这 7 个错误 Media 没有删除，已
改为 `FISH_CONTROL_AUDIT_DEBUG / reviewStatus=DEBUG`。Probe 随后改为按实际读取
PCM sample 数计时，并用同一音频字节零 Fish 调用重新导入上述正式 Media。

## 17. Fingerprint / Evidence

每项 evidence 保存：experiment id、canonical SpokenContent/text hash、DPD
fingerprint、Audio Projection fingerprint、render strategy/rendered text fingerprint、
safe provider controls、provider request fingerprint、Media id/hash、duration/silence/
RMS/peak/QC。Reference provider id、API key、Authorization、signed URL 均未保存。

脱敏证据：`artifacts/batch7-3b-1/evidence/live-control-audit.json`。真实 primary TTS
generation 总数为 7；duration 修正阶段新增 Fish calls=0。

## 18. Fish Expressive Ceiling

`FISH_EXPRESSIVE_CEILING_IDENTIFIED = YES`。

S2-Pro 的能力上限高于上一批判断，但仍以 coarse text cues + stochastic generation
为主：没有 typed/continuous phrase timing、可验证重音强度、articulation、句尾姿态、
呼吸准备、post hold 或精确 pause duration；当前 cloud schema 也没有可用于本实验的
seed。Markers 能“影响”生成，不能像导演轨道一样保证结果。

## 19. 与高质量历史剧配音的剩余差距

最大差距不是再加 DPD 字段，而是将已经存在的行动语义稳定落实成演员式微观时间
组织：心理动机停顿、句内推进/转折、语义重音强度、起音与收尾、呼吸连续性，以及
多次生成之间可复现的角色行动感。当前 S2 markers 是有用但较粗的控制面，仍需要
人类听审和候选选择。

## 20. Complexity Audit

| 指标 | 结果 |
|---|---|
| DPD/Brief fields | +0 |
| 新 production class | 0 |
| CapabilityStatus enum values | +2 |
| 新 production helper | 1：受限 rendered-text validator/compiler |
| `compile_fish_tts_payload` fields | +1 optional `rendered_text` |
| allowlisted S2 markers | 4：curious/emphasis/break/long-break |
| 新 adapter abstraction/framework | 0 |
| 新 Phrase Plan / DSL / AST | 0 |
| 新 Service/Repository/DB/MCP Tool | 0 |
| 新 integration runner | 1 |

## 21. 未解决问题

- B1 与 B2 的艺术优劣必须听审；单样本不能证明 marker 的跨调用稳定性；
- 若 B1/B2 都不自然，下一步应先确认是否值得在同一 Voice 上测试更少/不同的官方
  cue，而不是直接拆段或扩 DPD；
- production mapping 尚未默认启用 rendered text，这是有意的人类 review gate；
- s2.1-pro 的质量/控制能力属于未来独立 Provider/model evaluation，本批未切换。

## 22. 后续建议

1. 用户只听 B0/B1/B2，选择“更自然/无改善/各有问题”；
2. 若 B1 或 B2 获得明确 PASS，再把对应最小规则泛化为 Brief-driven compiler，不能
   为这一句硬编码；
3. 若两者均失败，记录 Fish ceiling，未来独立评估更强 expressive Provider 或 Fish
   新模型/API；
4. 不在本批进入 Phrase segmentation、7.3C、Lip Sync 或 Video。

## 23. 最终问题回答与状态

1. Case B 主因：Fish adapter compilation 丢失已存在的 rich brief 语义。
2. 原 DPD 不足：否。
3. AudioPerformanceBrief 不足：否。
4. `prosody.speed`：真实有效，强差值下 active duration 严格单调。
5. `prosody.volume`：真实有效，RMS/peak 严格单调，normalize 未完全抵消。
6. 其他 native controls：temperature/top_p/chunk/continuity/repetition 等主要控制随机性、
   稳定性和吞吐；S2 expression/pause/emphasis 通过 text surface 提供。
7. 标点/rendered text：单次实验稳定进入输出并保持可懂；艺术稳定性仍 LIMITED。
8. Phrase Plan：当前不需要。
9. Segmentation 是否更自然：未执行，不能宣称；前置必要性未成立。
10. Case B 最优方案：尚待听审；B1 是最低复杂度候选，B2 是 richer official-control
    候选。
11. A/C 回归：PASS，未重生成、未改变默认 production payload。
12. Fish ceiling：coarse/stochastic text cues，缺少 deterministic typed micro-performance
    controls。
13. 最大剩余差距：把戏剧行动稳定落实为自然的句内节奏、停顿、重音、呼吸与句尾。

```text
FISH_CONTROL_SURFACE_AUDIT = PASS
SPEED_EFFECT_VALIDATED = PASS
VOLUME_EFFECT_VALIDATED = PASS
TEXT_RENDERING_AUDIT = PASS
CASE_B_ROOT_CAUSE = IDENTIFIED
DPD_REGRESSION = PASS
AUDIO_PROJECTION_REGRESSION = PASS
FISH_CAPABILITY_MATRIX_2 = PASS
TECHNICAL_QC = PASS

PHRASE_PLAN = NOT_NEEDED
CASE_B_ARTISTIC_IMPROVEMENT = PARTIAL
A_C_REGRESSION = PASS
FISH_EXPRESSIVE_CEILING_IDENTIFIED = YES

BATCH_7_3B_1 = PASS
BATCH_7_3C = NOT_STARTED
LIP_SYNC = NOT_STARTED
```
