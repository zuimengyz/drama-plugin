---
name: literary-adaptation
description: Decide what a literary adaptation preserves or changes and map source units to film destinations; no screenplay or media generation.
---

# Literary Adaptation

Own AdaptationContract and DramaticCompression in `contracts/creative_source.py`. Consume reviewed LiteraryAnalysis and PhilosophicalCore. Preserve must-keep units, core relationships/events, arc, theme conflict and narrative identity. Record permitted operations and a reason, source-unit reference and narrative effect for each decision. Decisions are ADAPTATION_INVENTION, including choices to preserve or compress source material; never write them back into analysis.

Account for every source unit with KEEP, MERGE, COMPRESS, REMOVE, REORDER, EXTERNALIZE or an explicitly permitted other operation. Compression maps those same decision IDs to Film Beat/Scene IDs; do not maintain a second decision list or summarize without destinations. REMOVE has no destination. Preserved units cannot disappear. A significant causal or character change requires upstream contract revision and renewed review before screenplay persistence.

Bind the combined adaptation/compression review to the source revision. Rights come from supplied artifact assertions and the deterministic gate, not this Skill. No formal screenplay text belongs to this upstream package.

Use [Creative Source boundary](../../docs/creative-source.md) for review hashes, routing, persistence and source-map consumers. `source.prepare_screenplay` validates the complete reviewed package; it does not author missing specialist outputs.

For missing retained context read `work.get_work`, `script.get_script`, or `context.build_context`.
