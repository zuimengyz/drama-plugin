# Face A3 — Reference Identity Contract

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED

基线：2026-09-25，HEAD `3b286cca94ad3a1683060d4df2a986a6f789236f`。全部建议尚未实施；知识成熟度至多 LOCAL_EXPERIMENTAL，媒体效果 NOT_PLATFORM_VALIDATED。

## C15 延伸，D2 共享

继续 stable identity != current shot state。Reference Strategy 负责图的职责与适用性；CharacterAsset 决定身份；参考图本身无作者权限。角色 portrait 可 carry 被批准且能确认的脸几何、发际线/基础毛发、稳定标记；身体证据需独立可见性说明。不能自动 carry pose/gaze/expression/muscle tension/light/camera/composition/action/伤妆。场景图也不能自动授予这些权限。

扩展落于已有 Reference Plan.values.reference_roles 与 requirements 的 opt-in structured profile，不新增 registry 顶层键。每个 duty entry 包含 selected reference entity_key、media/version/content_hash、slot、目标 actor id、用途、carry 的 canonical pointers、exclude 的当前状态领域、区域可见性/遮挡/证据状态、原件 pins、明确 source-bound 的 preservation text。requirements 包含上篇 coverage 索引；reference_images 仍是 list。文字由 Reference owner 对已批准职责作决定，不允许 mapper生成“请更真实”等新意图。

## 三参考的实际表示

| Slot | 既有 kind / distinct entity key | carry | 不自动 carry |
|---|---|---|---|
| A | CHARACTER / 对应 actor 的 key | 已批准脸部身份；可限制仅 geometry | 表情、姿势、衣服、灯光 |
| B | COSTUME / 独立 costume asset key | 指定 actor 的服装身份 | 不提供第二个脸身份，不满足 actor 的 CHARACTER绑定 |
| C | SCENE / 独立 scene asset key | 批准环境/布局证据 | 不替代 Blocking/Camera/Lighting 原件 |

这是符号结构示例，不是真实 fixture 或新生成图。目标 actor 的 costume 关联在 Reference Plan职责 metadata 显式表达；不能在 FrameSpec 中给 A/B 使用重复 entity_key。当前要求 references 的 entity/media/upload 唯一；同一 actor 不能重复出现在 reference_members 多个组中。shared reference 可列多个 actor，但要明确各自可见身份且没有歧义。多角度图库可以大于三张用于审阅；单次请求仍最多三张，选片/已有批准拼板按现有规则，不拆图绕 cap，不把合成视图当独立真值。

F23/F24：暗部、侧面、浓妆、遮帽、低分辨率可限制某 facet；不能由不可见处推事实。F25：脸部近照可证明脸，不证明全身体型；全身图也可能不够证明眼睑/皮肤。多视图之间须版本、阶段和身份一致，矛盾交原 owner，不投票合成新脸。

## Identity preservation 与 redescription

canonical asset 是事实源；reference 是获批视觉证据；duty 决定只携带哪些责任。正常静态 IR.subject.face 等仍按现有 serializer 输出批准文本；Face A3 不保证长描述更好，也不通过删除/改序创建 provider 策略实验。多字段只在一个映射位置拼接一次，同一事实不靠多个 prompt 段反复强化。

现有编辑源与 references/bootstrap/reference_members 互斥。edit_source 是获批编辑基底，不自动变成长期 identity master。现有 edit serializer 会选 face/role/costume，而 age/hair/visible_condition 非默认全量重述；如果本次编辑要求它们明确保留，映射到既有 preserve 的批准保留声明。不能声称设置 subject.age 就确保 edit prompt包含它。必须在 A4 离线检查 retained/omitted 与用途覆盖，不改 selector。

Reference duty 的 carry/exclude文本只走既有 IR.preserve，当前状态仍在其专用 IR 字段；纯 mapping 不重写措辞。D2 来源链同时锁定 Reference Plan、资产原件、mapping receipt 和当前状态来源。若必需 duty 在既有 serializer 中不可达，新 profile请求阻断并报告 consumer gap，不临时追加 provider face prompt；provider-specific redescription策略必须独立研究授权。
