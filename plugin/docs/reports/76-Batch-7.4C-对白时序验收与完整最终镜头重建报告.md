# Batch 7.4C — 对白时序验收与完整最终镜头重建报告

## 1. 当前状态

**Status=REVIEW_REQUIRED**。Phase A 已生成本地 review-only 完整双句对白预览并通过技术 QC。Timing 尚未接受，Phase B 尚未开始；没有创建 accepted AVSync、正式 Final Shot Media 或 Cloud 对象。

## 2. Current Preflight

通过 Drama Service 重新读取当前 Work、Scene、Shot、Video、两条 Audio、Voice 与完整 Audio candidate set，并用 current inputs 重放验证 7.4B reconciliation `c1ec9267e8aafc1f8bbe27f48c04fe4fe476aaeff604a7a85924e8b675913917`。

| 输入 | ID | Hash / duration | 结果 |
|---|---|---|---|
| Video | `media_ac9d14c5cdc74c43ba44562752cf9489` | `066b281d…` / 11042ms | PASS |
| Turn A | `media_76a8fb24233246189d030babc7ceffd4` | `0940ec4c…` / 4571ms | PASS |
| Turn B | `media_6f4d16d785b84b52b3062e0666a826b5` | `4db91e12…` / 4107ms | PASS |

Canonical SpokenContent、speaker、Voice/master、production DPD、speaker-specific RP、Video、projection、Media sourceRef、technical/intelligibility lineage 均保持 current。`FULL_DIALOGUE_COVERAGE=COMPLETE`、`FULL_REALIZED_FEASIBILITY=FEASIBLE`。

## 3. Review Proposal

| 分量 | 时间 |
|---|---:|
| Pre | 0–500ms |
| Turn A 王思礼 | 500–5071ms |
| Reaction | 5071–5871ms（800ms） |
| Turn B 哥舒翰 | 5871–9978ms |
| Post | 9978–11042ms（1064ms） |

这是7.4B proposal，不是 accepted timing。5871ms 尚无 production authority。

## 4. Review Preview Assembly

通过 ffmpeg 将 Turn A 延迟500ms、Turn B 延迟5871ms，`amix normalize=0` 后把 PCM buffer 补齐至11042ms，再与固定 Video 合成 [04-complete-dialogue-preview.mp4](../../../../artifacts/batch7-4c/review/04-complete-dialogue-preview.mp4)。Video 使用 stream copy，Audio 编码为24kHz mono AAC。

源 Video 和两条 Audio 均由 Drama Service 从 Cloud MinIO 下载到 review package；下载 SHA-256 与当前 Media hash 一致。没有改变源文件、语速、音高、语音长度或视频内容。

## 5. Physical Timing

Turn A 物理解码为109713 samples / 4.571375s，Turn B 为98568 samples / 4.107s，sample rate=24000Hz。A 从第12000 sample（500ms）开始，物理结束于5071.375ms；B 从第140904 sample（5871ms）开始。

两者物理间隔为19191 samples / 799.625ms，无 overlap。0.375ms差异来自 Turn A 的样本级真实时长与 Domain 整数毫秒四舍五入，不是裁剪或 timing 改写。合同时间轴继续表达5071–5871ms的800ms reaction。

## 6. Technical QC

| 检查 | 结果 |
|---|---|
| MP4 playable | PASS |
| Video / Audio stream | PASS / PASS |
| Video | H.264，1280×704，24fps，11042ms |
| Audio | AAC，24000Hz，mono |
| Turn A / Turn B each once | PASS |
| Source PCM preserved in mix | PASS |
| No overlap | PASS |
| No unexpected pre-anchor speech | PASS |
| No duplicate / truncation / unexpected audio | PASS |
| Mix peak | -3.111 dBFS |
| Clipping | false |
| Video stream copy | PASS；source/preview packet hash identical |

AAC stream 报告11008ms，和11042ms容器/视频尾点相差34ms，位于最后一句结束后的 post silence，属于AAC packet/edit-list粒度；两句 speech 均在9978ms前完整保留，Video 未截断。

详细证据见 [phase-a-preflight.json](../../../../artifacts/batch7-4c/evidence/phase-a-preflight.json)、[phase-a-assembly.json](../../../../artifacts/batch7-4c/evidence/phase-a-assembly.json) 与 [phase-a-technical-qc.json](../../../../artifacts/batch7-4c/evidence/phase-a-technical-qc.json)。

## 7. Review Package

- [01-source-video.mp4](../../../../artifacts/batch7-4c/review/01-source-video.mp4)
- [02-turn-a-wangsili.wav](../../../../artifacts/batch7-4c/review/02-turn-a-wangsili.wav)
- [03-turn-b-geshuhan.wav](../../../../artifacts/batch7-4c/review/03-turn-b-geshuhan.wav)
- [04-complete-dialogue-preview.mp4](../../../../artifacts/batch7-4c/review/04-complete-dialogue-preview.mp4)
- [timing-review-summary.md](../../../../artifacts/batch7-4c/review/timing-review-summary.md)

## 8. User Review Scope

本次只审核时序与整体对话效果：A 是否开口合适、A 后 reaction 是否自然、B 在5871ms接话是否自然、两句是否形成正常对话、1064ms结尾是否合理。Preview 不要求重新审核 Voice Design；Audio `reviewStatus` 仍为 PENDING。

## 9. Provider / Persistence Boundary

Fish=0、Comfy=0、TTS=0、Video Generation=0、Lip Sync=0。Phase A Domain Writes=0、Media Import=0、Cloud Persistence=0、Final AV Mux=0。这里的本地 review mux 不构成正式 Final Shot assembly。

## 10. Existing Final Shot

旧72 Final Shot `media_a78d6ab7e9e94d06912c76658d28d378` 未覆盖、未删除，仍只包含 Turn B。`72_FINAL_SHOT_DIALOGUE_COVERAGE=INCOMPLETE`。

## 11. Phase B 未开始

当前不存在 `accepted-av-sync.json` 或 `05-final-shot.mp4`。只有用户明确批准本次 preview timing 后，Phase B 才会重新验证 current inputs，审计/窄扩展 multi-turn AVSync，并重建新的 derivative Final Shot。

## 12. Phase A Gate

| Gate | 结果 |
|---|---|
| CURRENT_VIDEO | PASS |
| TURN_A_CURRENT_AUDIO | PASS |
| TURN_B_CURRENT_AUDIO | PASS |
| RECONCILIATION_CURRENT | PASS |
| FULL_DIALOGUE_COVERAGE | COMPLETE |
| FULL_REALIZED_FEASIBILITY | FEASIBLE |
| REVIEW_PREVIEW_ASSEMBLY | PASS |
| TURN_A_PLACEMENT | PASS |
| TURN_B_PLACEMENT | PASS |
| REACTION_GAP | PASS |
| NO_DIALOGUE_OVERLAP | PASS |
| PREVIEW_TECHNICAL_QC | PASS |
| NO_PROVIDER_CALLS | PASS |
| NO_DOMAIN_WRITES | PASS |
| USER_TIMING_REVIEW | REQUIRED |

## 13. Phase A Result

`BATCH_7_4C_PHASE_A=PASS`。

`REVIEW_PREVIEW_ONLY=true`；`ACCEPTED_TIMING=false`；`FINAL_PRODUCTION_MEDIA=false`。

## 14. Boundary

**STOP BEFORE TIMING ACCEPTANCE**。等待用户观看完整对白 preview 并明确批准或给出具体 timing component 反馈。
