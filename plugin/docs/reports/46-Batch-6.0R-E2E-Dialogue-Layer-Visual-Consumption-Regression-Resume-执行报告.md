# 46 — Batch 6.0R-E2E Dialogue Layer Visual Consumption Regression Resume 执行报告

## 1. 执行摘要

本次仅回归一个真实含对白视觉单元：Episode 1 / Scene 1 / Shot 1-03「三十骑之议」。Dialogue 已实际驱动人物选择、画面表演、时序映射和静音视频生成；最终 Image 与 Video 均完成视觉审查、Media 导入、MinIO 持久化、Resolve 回读及 SHA-256 一致性验证。达到单单元成功停止条件后立即停止，未生成 Audio/TTS，整批状态仍为 PARTIAL。

## 2. Resume Checkpoint

- 起点：Shot 1-03，未重做 Shot 1-01/1-02。
- Work：`work_9cc5d11969a64f93bce4a544f349c793`
- Scene：`scene_3ad95aa042e647d9a9be05a51dd8a009`
- Shot：`shot_83db7eb53b2f49d3a58428d4659e584e`
- 恢复前阻塞仅为最终 start frame 上传授权；用户授权后只上传该文件。

## 3. Artifact Root

证据根目录：`artifacts/batch6-0re2e/`。本次专项证据位于 `artifacts/batch6-0re2e/dialogue-visual-regression/`。

## 4. Credit

本次 resume 新增 4 个付费任务：王思礼稳定参考图 1、Shot image 初稿 1、Shot image 定向修订 1、Shot video 1。实际计费 612.94 credits；保守记账 659 credits。整批 11 个付费任务，已知实际计费合计 1036.21，保守记账合计 1262，预算余量 733。视频静态估算为 256，实际遥测为 564.24，因此按实际向上取整记 565。

## 5. Current Memory

生产服务中当前 Work/Scene/Shot 读取成功。Shot 1-03 的 `plannedDurationMs=10500`，Scene `spokenSource` 与 Shot 绑定均存在且内容匹配；未用报告中的旧快照替代当前记忆。

## 6. Dialogue Context

消费了两个 Scene Dialogue：

1. 王思礼：`speaker:wangsili`，5,000ms，ON_SCREEN_SPEAKER；压低声音、急而不张扬地提出取杨国忠首级。
2. 哥舒翰：`speaker:geshuhan`，3,200ms，ON_SCREEN_SPEAKER；停顿后低声断然拒绝。

总 spoken load 为 8,200ms，画面与视频 prompt 均显式携带两段动作意图。

## 7. Host Requirements

Shot 要求双人中景、帅帐内低声试探、无额外人物、无字幕/文字、无音轨、无镜头切换。最终媒体满足这些边界。

## 8. Speaker Identity

人物身份从当前 Work 的 `historicalActorHierarchy` 获取，而不是从 Dialogue 文本猜测。`speaker:wangsili` 与 `speaker:geshuhan` 均解析到 Work 范围内的稳定人物身份。

## 9. Asset Discovery / Resolution

哥舒翰复用当前 Work 已验收 Asset `asset_807f5ae3694746ccab81c828ab57e990` / Media `media_2a0e7a10b8fc4dc5863731c02e5392ef`。已知属于错误 Work 的旧王思礼 Asset 被拒绝；新建当前 Work Asset `asset_0bfe891941184a66bd9e6f6aee0b622c` / Media `media_04f98e81cb5a4b9d80779283ab70bfb3`，SHA `923558b5535d7219014a76367c287b7643bf2f8847fe5e1f9221fef949b105bf`，回读一致。

## 10. Binding

Shot 绑定消费了两位在场角色与双人构图，并把第一段动作分配给王思礼、第二段动作分配给哥舒翰。Dialogue 与 Asset 保持解耦：Dialogue 只给出 `speakerKey`，Asset 由 Work 身份上下文解析。

## 11. Planned Duration

消费 `plannedDurationMs=10500`，没有复用遗留的固定 5 秒计划。

## 12. Capability Matching

当前 `api_bfl_flux3_i2v` 支持 5–20 秒整数时长、image-to-video 及关闭音频，能够承载 10.5 秒 Shot。最终仅使用获授权的 start frame 作为视频输入。

## 13. Duration Mapping

映射规则为向上取整且不得短于计划：10.5 秒映射为 11 秒。实测时长 11.041667 秒。0–5 秒为王思礼提议表演，5–11 秒为哥舒翰停顿与拒绝表演。

## 14. Image Generation

最终图由双身份参考驱动。初稿因背景伪汉字未通过审查；进行一次定向修订后通过。最终文件 `shot-1-03-final-image.jpeg`，Media `media_02a759ce46e5479f9612ba7e73bae695`，SHA `8b9ad5d8c7b33fedb4a641e312d1efdf232405f5327eddb374baac94f32e1ca3`。

## 15. Video Generation

视频 Job `916fd559-5393-448b-8543-8a4f08c1af78` 使用 `api_bfl_flux3_i2v`，duration=11、audio=false。最终文件 `shot-1-03-final-video.mp4`：11.041667 秒、1280×704、24fps、H.264，仅视频流。Media `media_63787886dc85413c90207e17d68df520`。

## 16. Dialogue-aware Review

五个审查帧覆盖 0、2.75、5.5、8.25、10.5 秒。王思礼在前半段有克制的口型与动作并随后停止；哥舒翰先听、停顿，再于后半段开口拒绝。身份稳定，无不可能的同时说话，无额外人物、字幕、伪文字或镜头切换。Image 与 Video 均 PASS。

## 17. Source Mutation

对 `sceneSpokenSource` 采用 `jq -cS` 且不附加尾随换行的规范化字节。执行前后 SHA 均为 `8a23f975c5c544aa2f838706d47ab362476a52c526f15ff3cc2661ccd6d0e87e`；Mutation Count = 0。早期含 shell 尾随换行的哈希未作为证据使用。

## 18. Media / MinIO / Resolve / Hash

最终 Image 与 Video 均正式导入 Media、存在 MinIO 对象、可通过 Resolve 下载。本地与回读哈希分别一致：Image `8b9ad5...e1ca3`；Video `5027499b630045813e09ac082c90f9251a95e292bcb4d9767e7d7b0a5a0a065a`。

## 19. Checkpoint

`lastCompletedNode=Episode 1 / Scene 1 / Shot 1-03 / VIDEO_MEDIA_VERIFY`。检查点已写入最终 Media、Job、路径、哈希、预算和单单元停止原因。

## 20. Ledger

Ledger 新增 sequence 8–11，并将视频实际超估算差异显式记录为 `CONSERVATIVE_CEIL_ACTUAL_TELEMETRY_ESTIMATE_UNDERSHOT`。整批保守记账 1262，余量 733。

## 21. Silent Reuse Check

Shot 1-03 在本次前没有可复用的完成视觉 Media，因此 `SILENT_VISUAL_REUSE=NO`。本次生成的是新 Image 与新静音 Video；没有把旧 Shot 的视觉结果冒充回归通过。

## 22. Regression Pass / Fail

```text
SECOND_STAGE_DIALOGUE_VISUAL_REGRESSION=PASS
DIALOGUE_CONTEXT_LOADED=YES
SCENE_SPOKEN_SOURCE_CONSUMED=YES
SHOT_BINDING_CONSUMED=YES
SPOKEN_SOURCE_MUTATION_COUNT=0
WORK_SCOPED_SPEAKER_IDENTITY_CONSUMED=YES
SPEAKER_ASSET_DECOUPLING=PASS
PLANNED_DURATION_CONSUMED=YES
DURATION_AWARE_WORKFLOW_SELECTION=PASS
VISUAL_PERFORMANCE_FROM_DIALOGUE=PASS
ASSET_DISCOVERY_FROM_CONTEXT=PASS
ASSET_RESOLUTION=PASS
IMAGE_PRODUCTION=PASS
VIDEO_PRODUCTION=PASS
VISUAL_REVIEW=PASS
MEDIA_IMPORT=PASS
MINIO_OBJECT=PASS
RESOLVE=PASS
HASH_EQUALITY=PASS
SILENT_VISUAL_REUSE=NO
CODE_CHANGED=NO
PAID_JOBS_THIS_RESUME=4
PAID_CREDITS_ACTUAL_THIS_RESUME=612.94
PAID_CREDITS_ACCOUNTED_THIS_RESUME=659
PAID_JOBS_BATCH_TOTAL=11
PAID_CREDITS_ACTUAL_BATCH_TOTAL=1036.21
PAID_CREDITS_ACCOUNTED_BATCH_TOTAL=1262
BATCH_BUDGET_REMAINING=733
LAST_COMPLETED_NODE=Episode 1 / Scene 1 / Shot 1-03 / VIDEO_MEDIA_VERIFY
NEXT_NODE=Episode 1 / Scene 1 / Shot 1-04 / IMAGE_REFERENCE_RESOLUTION
STOP_REASON=ONE_DIALOGUE_BEARING_UNIT_DURABLE_PASS_STOP_RULE
BATCH_6_0R_E2E=PARTIAL
DIALOGUE_LAYER_VISUAL_CONSUMER_READY=YES
AUDIO_LAYER_VALIDATED=NO
```

## 23. Stop Reason

`ONE_DIALOGUE_BEARING_UNIT_DURABLE_PASS_STOP_RULE`。已证明一个含对白单元的完整持久化链路，故立即关闭付费提交门；没有继续 Shot 1-04，也没有触碰 Audio/TTS。

## 24. Next Node

若未来恢复整批生产，从 `Episode 1 / Scene 1 / Shot 1-04 / IMAGE_REFERENCE_RESOLUTION` 开始。不得重新生成 Shot 1-01、1-02 或 1-03。当前批次最终状态：`BATCH_6_0R_E2E=PARTIAL`。
