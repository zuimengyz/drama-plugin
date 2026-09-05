---
name: cinematic-screenplay-incubation
description: Incubate a historical screen drama from evidence through character, story, scenes and dialogue, with a shared Dramatic Bible and bounded targeted revision. Use for complete screenplay creation or cross-scene creative repair; production remains downstream.
---

# Cinematic Screenplay Incubation · 影视编剧孵化

Own the creative working process from Historical Material to a readable, reviewed screenplay. The six modules below are stages of one Agent's work, not separate agents or an automatic skill chain. Preserve an already approved foundation; choose only the stages affected by the request.

## Scope and compatibility

The existing hierarchy is Work → Script → Episode → Scene → Shot; a Work is not limited to one Episode. Work retains the literary foundation, Script the adaptation architecture, Episode its dramatic unit, Scene the canonical action and `spokenContent`. The existing work-creation and script-adaptation entrypoints remain valid for narrow requests. Their historical attribution, persistence and revision gates still apply; this Skill shares their results in one working context rather than redefining their contracts.

Use supplied context first. For existing identities, read `work.get_work`, `script.get_script`, `episode.get_episode`, `scene.get_scene` only as needed. Use `context.build_context` for missing parent context. For material evidence gaps use `research.search_sources` and `research.verify_claim`; unresolved contested history requires an adaptation position, not silent certainty. Do not require a live domain object to write a requested standalone screenplay artifact.

For an explicit persistent deliverable, apply the relevant existing owner stage's write rules after review. This Skill's own tool set is read-only; it does not automatically create Work, Script, Episode or Scene. A local creative E2E is actual authored work, not a mocked provider response, and does not require media generation.

## Meta dramaturgy before incubation

For a new work derive a lightweight load profile, explicit narrative aperture, POV contract and style from the request and evidence, using [meta dramaturgy](references/meta-dramaturgy.md). These select emphasis within the existing twenty dimensions; they are not another mandatory exposition checklist. Core grounding/causality/character/knowledge/continuity/review remain active; conditional war, ensemble, logistics, parallel narrative or spectacle may be N/A. No subject, period, person, tragedy, restraint, silence or spectacle is the default model of a good screenplay. Test stories are replaceable fixtures, never production rules.

For long work, use Global Bible → Episode Working Set → Scene Working Set. Read only relevant facts and creative constraints; author facts never automatically become character knowledge. Use [projection and dependency conventions](references/working-sets.md) to identify context and invalidated consumers before revising. Episode boundaries do not reset body, status, relationship, information or promises.

## Plan → Execute → Review → Revise → Freeze

Create a compact Dramatic Bible using [working state](references/bible.md). Keep one source of truth for historical constraints, characters, knowledge and continuity. Use stable local IDs before domain persistence; never pretend local IDs are durable entity IDs. Retain initial draft and review evidence. Read [craft controls](references/craft.md) for the relevant modules; all twenty dimensions receive an applicability decision, not twenty mandatory blocks of exposition.

### 1. Historical & Logic

Establish scope, evidence-backed causal spine and actor authority before thesis or protagonist. Preserve who actually decided, what they knew and what constrained them. Separate historical causality from dramatized presentation: deleting a fictional action may remove this scene's experiential logic, but cannot become the sole explanation of an established historical outcome. Historical Event != Scene.

Trace travel and message arrival in relative time when dates/distances are uncertain. Do not create precision from a map guess. Freeze forbidden historical contradictions and record alternatives where sources conflict.

### 2. Character & Relationship

Turn traits into behavior under pressure, disagreement, humiliation, uncertainty and unequal rank. Give each principal a few invariants, qualitative capability strengths and limits, and a distinct textual voice. Record elasticity where pressure, fatigue, injury or power changes can produce an earned deviation and a recovery pattern; consistency is not identical behavior. Distinguish formal authority from practical military, political and information power. Private psychology and relationship interpretation are creative positions, not biographical discoveries.

### 3. Story & Rhythm

Derive thesis, narrative POV and the smallest coherent scope from the causal spine. Build story and episode jobs before selecting counts. Compare Beat → Scene → Sequence → Episode → Multi-Episode Arc; each episode records its start/end state, turn, peak, breathing space, after-effect and next pressure. Track pressure, development, breathing, escalation, turn, climax and aftermath as changes in options and knowledge, not timing quotas. Review adjacent scenes for repeated argument, meeting, battle or emotional peak. A quiet scene still changes something; do not remove needed causality merely to accelerate.

### 4. Scene & Dialogue

For each scene establish owner, goal, obstacle, tactic, counter-tactic, information/relationship/power/emotional change, turn and exit hook. Answer why the next scene follows. Track each speaker's knowledge at the moment of choice, not just at scene end. Give necessary dialogue exact words, differentiated diction, surface meaning, intent and subtext; allow a silent scene.

Keep control notes out of the audience-facing body. Preserve stable speaker and spoken-item identity during a local wording revision. Formal Scene persistence still uses the [existing dialogue convention](../../docs/dialogue-layer-content-convention.md), not a second dialogue store. Do not fabricate DIRECT_QUOTE status for adapted words.

### 5. War & Cinematic Expression

If conflict is armed, connect terrain/objective/command to unit behavior and bodily experience, then show the unit and operational consequence. Apply army training, fatigue, cohesion and supply to behavior. A retreat is neither automatically cowardice nor automatically a flawless maneuver. Do not insert a battle to satisfy a checklist; state N/A when war execution lies outside scope.

Use a small number of purposeful motifs and a chosen narrative texture. Test whether action, object, environment or silence can replace explanatory speech. Distinguish shootable visual intention from camera/production specifications. Derive episode opening/closing anchors from aperture, POV, texture and episode job. Subjective emphasis needs an anchor, a narrative purpose and a return to objective context; it cannot alter facts, outcomes or knowledge. See the meta reference for bounded subjectivity and text/artifact provenance.

### 6. Review & Revision

Apply [layered review](references/review.md) to the complete draft and the Bible. Record `problem`, `severity`, `layer`, exact `evidence`, `recommendedRevisionScope`, then declare changed facts, owner, invalidated consumers, unaffected scopes and required rechecks before revising. Recheck affected dependencies even if their words remain unchanged; do not regenerate them automatically. A dialogue defect does not authorize whole-Work regeneration.

Bound the process to Initial Draft + at most two targeted revision rounds. Each round may resolve several findings in their declared scopes. Review changed scenes and their dependencies, then recheck full-work coherence. Preserve before/after bodies and unchanged-scope hashes. Unresolved major defects at the limit produce PARTIAL/FAIL with concrete findings; do not label them PASS or continue indefinitely. A clean draft needs no manufactured defect, but a requested incubation regression must demonstrate at least one genuine targeted improvement.

Before freeze, run the optional offline [artifact checker](scripts/check_incubation.py) when using the Bible convention. It verifies references, recorded continuity/knowledge, optional meta control records, projection references, revision scope and budget; it cannot judge acting, prose quality or historical truth. Machine success never substitutes for reading the complete script. Freeze records the exact revision and outstanding limitations; user artistic acceptance stays separate from author review.

## Downstream handoff

Provide Character + Scene Dramatic State + canonical Dialogue Intent/Subtext + sparse Performance Intent. DPD owns its existing Scene/Beat/Line direction; the screenplay cannot redesign it. Surface/hidden emotion, target and intent are interpretive inputs; tempo, pause, force, breathing and restraint are upstream advisory language for later projection, not additional DPD fields or numeric controls. Shot anchors express the first/last effective perception and its purpose, not lens, frame size, camera movement, exact duration or shot lists. Detailed execution remains with the existing Scene/Shot/Production owners. Do not select voice identities, synthesize speech, render video, choose reference assets or bind provider parameters here. See the [existing DPD boundary](../../docs/dpd-core-contract.md) only when preparing that handoff.

Complete with a readable screenplay, supporting Bible, scoped review/revision trail and a freeze decision. Keep rejected drafts and review reasoning in local working artifacts, outside formal Domain content.
