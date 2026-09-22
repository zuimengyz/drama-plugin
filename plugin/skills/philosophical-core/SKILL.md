---
name: philosophical-core
description: Author question, conflicting values, choices, consequences and ambiguity from a reviewed literary analysis; no thesis speech generation.
---

# Philosophical Core

Own PhilosophicalCore in `contracts/creative_source.py`. Consume reviewed LiteraryAnalysis. Keep QUESTION, CONFLICT, VALUE POLES, CHARACTER CHOICE, CONSEQUENCE and AMBIGUITY explicit, with source-unit references. Mark the entire result INTERPRETATION. Do not claim a definitive author intention.

The output constrains Screenplay and Director; it is not dialogue, narration, a slogan or a monologue. Consume the compiler-projected themeExpressionOrder from `creative_source.py` rather than defining a competing ordering or word blacklist. Review whether the question survives choices and consequences without explanatory speech. Record a pinned specialist StageReview; do not mutate analysis or adaptation.

Use [Creative Source boundary](../../docs/creative-source.md) for review hashes, routing, persistence and source-map consumers. `source.prepare_screenplay` validates the complete reviewed package; it does not author missing specialist outputs.

For missing retained context read `work.get_work`, `script.get_script`, or `context.build_context`.
