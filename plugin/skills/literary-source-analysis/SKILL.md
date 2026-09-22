---
name: literary-source-analysis
description: Analyse a designated literary text into anchored source facts and distinct interpretations; never make adaptation decisions.
---

# Literary Source Analysis

Own LiteraryAnalysis and SourceAnchor in `contracts/creative_source.py`. Read only the designated SourceArtifact as source truth. Preserve exact text offsets and artifact hashes. Characters, relationships, events/order, POV, chronology, narrator, settings, objects, motifs/images, internal states, arcs, conflicts, scenes and narrative structure need coverage or a justified absent-category entry.

SOURCE_FACT requires direct source support. INTERPRETATION requires source-fact references and remains an interpretation even after review. Modern adaptation material is NON_COPYING_REFERENCE and cannot supply source anchors. Do not infer rights from an author date, inherit rights from an original into a translation, or use old Media/character assets as literary source.

Record a source-bound specialist StageReview. This validates an authored analysis, not literary truth by schema. Return missing text or contradictory anchors to the source owner. Do not author screenplay, compression or film decisions.

Use [Creative Source boundary](../../docs/creative-source.md) for review hashes, routing, persistence and source-map consumers. `source.prepare_screenplay` validates the complete reviewed package; it does not author missing specialist outputs.

For missing retained context read `work.get_work`, `script.get_script`, or `context.build_context`.
