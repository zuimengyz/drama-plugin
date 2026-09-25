# Face A3 — 交付索引

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED

基线：2026-09-25，HEAD `3b286cca94ad3a1683060d4df2a986a6f789236f`。全部建议尚未实施；知识成熟度至多 LOCAL_EXPERIMENTAL，媒体效果 NOT_PLATFORM_VALIDATED。

**READY_FOR_FACE_A4 = YES（仅设计准备度）。JOINT_CINEMATOGRAPHY_FACE_A4 = RECOMMENDED。本轮已停止在A3。**

- [逐项表达审计与35项allowlist](Face-A3-Canonical-Expressiveness-Audit.md)
- [身份、年龄、皮肤知识契约](Face-A3-Facial-Identity-Knowledge-Contract.md)
- [Reference职责契约](Face-A3-Reference-Identity-Contract.md)
- [QC观察与修复职责](Face-A3-QC-Contract.md)
- [Source→IR→Consumer映射](Face-A3-Source-IR-Consumer-Mapping.md)
- [A4最小逐文件计划与联合实施](Face-A3-A4-Minimal-Implementation-Plan.md)
- [未来A5对照验证契约](Face-A3-A5-Validation-Contract.md)

四份JSON draft为NON_RUNTIME：knowledge-contract、expressiveness-matrix、qc-contract、contract-delta。Face专用schema新增0，共享摄影CINE_D2；不更改serializer。35条知识均保留source/commit/section与rule hash，最大LOCAL_EXPERIMENTAL。

验证证据见[evidence/completion-check.json](evidence/completion-check.json)及[input-freeze](evidence/input-freeze.json)。没有A4实施、人物生成、provider调用、外部搜索或安装。预存`.DS_Store`保持原状。
