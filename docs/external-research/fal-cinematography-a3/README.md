# A3 Canonical Cinematography Knowledge Contract Design

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED

范围仅 A2R 的 16 项 ADAPT。当前 HEAD 未变；无 Runtime、Provider route 或安装变更。

- [A：现有合同表达能力审计](A3-Canonical-Expressiveness-Audit.md)
- [B：专业知识合同](A3-Professional-Knowledge-Contract.md)
- [C：来源 → IR → Consumer 映射](A3-Source-IR-Consumer-Mapping.md)
- [D：A4 最小实施计划与 readiness matrix](A3-A4-Minimal-Implementation-Plan.md)
- [E：A5 配对验证合同](A3-A5-Validation-Contract.md)

设计只提出两个可选字段：GlobalVisualStyle.imaging_character、FrameSpec.professional_sources。Camera/Lighting/VisualPromptIR/Review 顶层字段不扩展；保留共享静态 serializer 和当前 GPT Image 2 route。

READY_FOR_A4 = YES（仅最小、显式启用的实现范围；知识仍 LOCAL_EXPERIMENTAL）。本轮已 STOP，未执行 A4/A5。

[最小字段差异草案](contract-delta-draft.json) / [规则与来源草案](knowledge-contract-draft.json) / [映射草案](source-ir-mapping-draft.json) / [输入冻结](evidence/input-freeze.json) / [完成核对](evidence/completion-check.json)。所有 JSON 都只是设计元数据，不是可执行或已批准的生产合同。
