# Video-conditioned Final Audio（7.3D）

`DPD + canonical SpokenContent + frozen Voice + accepted RealizedPerformanceSnapshot`
组成最终 AudioPerformanceBrief；声音执行跟随实际 accepted Video，人物 objective、
action、relationship、subtext 仍由 DPD 拥有。偏离 DPD 的画面不是阻断器。

## 最小组合

`VideoConditionedAudioProjection` 只有一个现有 `AudioPerformanceBrief` 和 lineage：
baseAudioProjectionFingerprint、realizedPerformanceFingerprint、videoMediaId、
videoContentHash、shotId、voiceMaterialFingerprint、schemaVersion、fingerprint。
不复制 Audio ontology，不引入服务/表/Entity。`SpeechGenerationRequest` 可携带它；
其 final brief 必须与 request 的 audioPerformanceBrief 完全一致。

`audio.video_conditioning.condition_audio_on_video` 校验原始 DPD、accepted RP hash、
Video bytes identity、Shot/Scene/SpokenContent/actor/speaker/Voice binding。
它不会改写输入，重新解释剧情、改写台词或推导稳定音色。
观察结果的枚举 UNKNOWN 保持 UNKNOWN；可观察表情变化、头部动作只帮助相对句式执行，
不把低头写成悲伤，不把动作急写成语速快，不把近景写成混响或低声。

## 时间与边界

7.3D 只允许 `NATURAL`，无 targetDuration、rate adjustment 或自造 timing constraints。
视频时长不是配音时长。嘴部 UNKNOWN 时没有绝对 speech window、pause anchor 或 phrase plan。
7.3C 的头动窗口也不是 speech anchor。最终声音仍为 dry dialogue。
禁止 Lip Sync、SFX、ambience、music、mix、AV mux；本阶段在 durable Audio/review 后停止。

## Fingerprint 与失效

final projection fingerprint = canonical SHA-256(wrapper excluding fingerprint)。
嵌套 final brief 带 DPD/text/creativeVoice/identity fingerprints；wrapper 带 Video hash 和 RP
fingerprint、Voice master material fingerprint。时间戳、主机、临时 URL、provider task ID 和秘密不参与。

Video bytes 或合法修订的 accepted canonical observation 改变，final fingerprint 必变；
现有 audio-input fingerprint 纳入 final fingerprint，旧 Audio 为 STALE，需重新生成。
旧 Audio 不删除、不被 baseline 覆盖。`is_audio_fresh` 复用既有审核/依赖检查。
Role Dubbing 在缓存查找前重读 Video、Shot、Scene、Work binding 与 Voice master hash，
防止旧 request 悄悄命中旧 Audio；最新 accepted observation 仍由调用方提供，未新增观察数据库。

## Provider materialization

Adapter 只读最终 brief，不读取视频或重新推断 DPD。显式 `BRIEF_CUES_V1` 请求可由
Fish adapter 从 control/intensity/rhythm/pause/ending 编译一个有界声音执行 cue；
canonical text 完全保留，rendered text 单独 fingerprint。B0/D1 使用相同 compiler、
model、Voice mapping、native prosody。旧 native 路径默认保持不变。

Cue 是 provider adapter 的 opt-in materialization，不是 core 字段或情绪标签分类器。
文本可渲染不等于 provider 保证实现，艺术效果必须听审。未验证结果不能宣称 live PASS。

## Storage / budget gate

Drama Service 独占云端 storage；Plugin 只 get/resolve/download/import，不直接访问 MinIO。
组件 env 分离，不 source service env 到 Host/Plugin。先验证唯一云端 endpoint 配置与
Service 重启状态，再经 Service 检查 Video、Voice 下载 hash；之后才允许真实 TTS。

metadata 存在而对象 404：返回 `STORAGE_MIGRATION_RECONCILIATION_REQUIRED`。
仅当受信本地 Video artifact hash 完全一致且现有 restore contract 支持时，通过
`media.restore_media_object` 恢复相同 identity；Voice 没有 restore API 时停止，不新建 Voice。

集成 runner 默认 prepare-only，`--live` 与 `--confirm-service-restarted` 必须由操作方明确启用。
B0 严格匹配 source fingerprint 才复用；否则最多生成一次。D1 最多一次，自动重试为 0。
提交前写 journal；模糊结果先按 sourceRef reconcile，不能删 journal 盲重提。
成功产物进入 `ROLE_DUBBING_AUDIO`，具备 stable ID/hash/size/MIME/source lineage。
