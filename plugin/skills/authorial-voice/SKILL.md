---
name: authorial-voice
description: Judge whether a developed story passage has earned sparse authorial literary intervention, defaulting to silence; compare source-pinned literary candidates. Use at a historical or character closure point, not for character dialogue, story rewriting, casting, or media finishing.
---

# Authorial Voice

Default to `NO_AUTHORIAL_INTERVENTION`. Calling this skill creates no duty to write.
Ask whether the character/event has earned a final authorial gesture through the
actual drama. Importance, death and historical fame alone do not earn a coda.

Read the developed Script/Sequence, the relevant actions and dialogue, historical
sources and previous interventions. Pin their revisions/hashes. Distinguish a
SCRIPT_DRY_RUN from a REVIEWED_SEQUENCE: text on a page is not a viewed final edit.
Use local Artifact sidecars first; no new tables or authoritative story entity.
Read current context with `work.get_work`, `script.get_script`, `scene.get_scene`,
`asset.get_asset` and `asset.list_assets`. These reads do not authorize adoption writes.

Keep three voices separate: Character Voice is what people say; World Voice is
action, environment, objects and sound; Authorial Voice is the work intervening.
Exhaust relevant World Voice possibilities before explaining what a character
cannot say. Do not rewrite dialogue, facts, photography, casting or production design.
The screenplay skill owns story; this skill starts at an existing candidate point.

Read [the literary decision contract](references/decision.md) and apply the
AuthorialInterventionGate: narrative weight, audience investment, arc completion,
historical weight, resonance surplus, visual sufficiency, redundancy/scarcity and
over-explanation risk. Use QUALIFIED / PARTIAL /
NOT_QUALIFIED with source-grounded reasons, never a summed score. A very important
protagonist may still receive no text if action and image suffice.

Before writing any candidate, answer Literary Intent: why now; characters cannot
say; image already says; what remains unsaid; desired aftertaste; why this form;
why not silence. If the answers fail, retain silence. Compare text against silence
on the same passage. Longer or cleverer summary is not greater resonance.

Literary form stays open: a short sentence, inscription, praise, elegy, historian
comment, chronicle note, poem, memorial, episode title, letter fragment, proclamation,
custom form or no-text visual coda. A letter/proclamation here is an authorial framing
proposal, never newly attributed character dialogue. Death is only one possible
closure; exile, victory, a changed regime, a completed letter or identity ending may
qualify. Never manufacture a minor character's death to justify an epitaph.

Choose intent before register. Do not default to pseudo-classical formulas such as
呜呼、悲夫、壮哉、千古、江水滔滔、魂归. Modern prose, one plain sentence or silence
may fit better. Authorial Voice is not an automatic moral verdict: preserve ambiguity,
leave a question, record an image, or explicitly label a project interpretation.

Record HISTORICAL_QUOTE / ADAPTED_HISTORICAL_TEXT / ORIGINAL_PROJECT_TEXT precisely.
Verify quoted text against a pinned excerpt; explain adaptations. Original writing
also carries AUTHORIAL_INTERPRETATION and never becomes historical Canon. A source
inspiring an original line does not make the line historical. Recheck factual claims
against project evidence; eloquence cannot introduce new facts.

Use AuthorialVoiceBudget to read actual recent interventions, form repetition,
semantic repetition and emotional redundancy. Each actual use adds a duty to explain
the next intervention's distinct contribution. This is no per-episode/count quota.
Dry-run alternatives are not uses and do not consume the ledger. Silence remains
available even after qualification and a persuasive intent.

Run [voice.py](scripts/voice.py) for schema/validation/gate checks. The pure contract
cannot judge literary quality or certify a source from its hash alone. Retain all
alternatives PENDING_USER_REVIEW. It does not adopt, generate, or save formal dialogue.
Only future explicit user adoption may retain text as an existing text-only Creative
Asset with provenance. Then cinematic-finishing owns subtitles, black, overlay,
reading/silence and exact timing. This skill hands over only literary content, intent,
form requirements and semantic position; no animation or UI timings.

For a declared visual route, read [route-sensitive presentation](references/visual-routes.md). The literary gate and scarcity remain shared; presentation cannot grant literary eligibility.
