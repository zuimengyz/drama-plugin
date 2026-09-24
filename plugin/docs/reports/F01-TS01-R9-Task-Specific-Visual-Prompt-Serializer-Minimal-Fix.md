# F01-TS01-R9 — Task-Specific Visual Prompt Serializer Minimal Fix

## 1. Root Cause

静态图片与视频共用逐字段渲染，将 IR priority、字段路径和字段内容直接发送给 Provider。IMAGE_EDIT 虽有排序，但纠错仍被整份资产描述淹没。

## 2. Old Serializer

输出 `CRITICAL subject.…`、`IMPORTANT blocking.…` 等内部合同文本；首次生成和编辑未采用各自的执行格式。

## 3. New Initial Image Format

TEXT_TO_IMAGE、FIRST_FRAME、KEY_FRAME 输出 TARGET WORLD / SUBJECTS / CURRENT BLOCKING / ENVIRONMENT / CAMERA / LIGHTING / TARGET LOOK。内容来自当前 IR，以人物角色和自然描述组织，不输出内部 priority 或字段路径，也不生成源图纠错指令。

## 4. New Image Edit Format

依次输出 MUST CHANGE / PRESERVE / TARGET RESULT。完整 correct / replace / remove delta 优先；显式 preserve、当前人物关系及必要身份/服装锚点保留。源图其余内容通过保留指令承接，不再展开无关头发、体型、鞋裂、袖口磨损和 continuity prose。人物面部、服装和建筑的必要语义锚点继续满足原 authority 校验。

选择与去重仅发生在 Provider projection，完整 IR、priority、source delta 和 continuity 均保留。现有预算逻辑继续执行；关键纠错不能因预算被丢弃，无法容纳时仍报 PROVIDER_PROMPT_BUDGET_EXCEEDED。视频渲染保持原样。

## 5. Files Changed

- `plugin/src/drama_plugin/visual/image_serializer.py`：新增静态任务选择与自然语言渲染。
- `plugin/src/drama_plugin/visual/prompt_ir.py`：仅将静态任务接入新 serializer。
- `plugin/tests/test_image_serializer.py`：任务格式、预算保护、IR 不变及视频基线测试。
- `plugin/tests/test_visual_prompt_ir.py`：更新静态输出格式断言。
- 本报告；离线证据保存在 [artifacts/f01-ts01-r9-image-serializer](/Users/zy/historical-plugin/artifacts/f01-ts01-r9-image-serializer)。

未修改 IR schema、预算引擎、scope guard、authority、资产、路线、Provider adapter 或持久化逻辑。

## 6. Tests

191 passed：image_serializer、visual_prompt_ir、prompt_budget、payload_scope、authority_provider_separation、route_image_inputs、official_video_providers、video_reconciliation。包含三种首次静态任务、编辑顺序、完整 preserve、紧预算阻断、完整 IR 不变，以及四种 VIDEO input mode 的完整编译记录指纹与修改前一致。

两个修改/新增源文件 mypy 通过；git diff --check 通过。

## 7. S02 Old/New Prompt Diff

使用保存的 `S02-inputs/K02-prompt-ir-r10.json` 与对应旧 frame compilation 离线重编译：2922 → 819 字符。男人年龄纠错与右侧停车牌替换位于最前；显式 preserve 完整保留，时代、彼得堡地域及真人电影目标保留。

- [Old prompt](/Users/zy/historical-plugin/artifacts/f01-ts01-r9-image-serializer/old-prompt.txt)
- [New prompt](/Users/zy/historical-plugin/artifacts/f01-ts01-r9-image-serializer/new-prompt.txt)
- [Diff](/Users/zy/historical-plugin/artifacts/f01-ts01-r9-image-serializer/prompt.diff)
- [Regression result](/Users/zy/historical-plugin/artifacts/f01-ts01-r9-image-serializer/result.json)
- [Offline replay](/Users/zy/historical-plugin/artifacts/f01-ts01-r9-image-serializer/replay.py)

现有 scope、asset authority、编译记录与 frame request 重放验证均 PASS。完整 IR 与全部读取源文件哈希未变化，Provider request 中除 prompt 外的字段未变化。收费生成调用为 0；未上传、预留或提交任务。

## 8. Remaining Blocker

本轮离线 serializer 回归无阻塞。新静态 prompt 必须使用重新编译的记录；未验证实际生成效果或 Provider moderation 接受结果，亦未执行收费验证。
