---
name: scene-development
description: Develop scene dramaturgy and causal beats from an Episode, then assemble department references; dialogue, staging, art and execution retain their independent owners.
---

## Creative Source applicability

Consume the parent Script's current ScreenplayInput. Historical evidence, historical beat coverage, actor hierarchy and reconstruction rules in this Skill and its references apply to HISTORICAL. For LITERARY consume the pinned adaptation decisions, compression destinations, cinematic translation and arc stages instead; return new causal changes or source reinterpretation upstream. Shared continuity, knowledge, review and persistence gates remain mandatory. See [Creative Source](../../docs/creative-source.md). Do not use old Media or casting as a literary source.


# Scene Development

Read [professional department architecture](../../docs/professional-departments.md).

## Role and authority

Own scene purpose, conflict, beat, reversal, emotional/information change and causal input/output.

## Inputs and dependencies

Episode/Story/Character Bibles; historical boundary; current adjacent scene states; reviewed Dialogue refs.

## Outputs

Scene Beat Bible and thin SceneAssembly; preserve canonical Scene IDs and compatibility content when required.

## Forbidden authority

Do not design camera, lights, costumes, sound, music, choreography or edit details. Do not independently rewrite Dialogue Design output.

## Quality gates

Beat transitions preserve story locks and all required refs resolve; review design readiness separately from media.

## Failure and escalation

Return specialist gaps to registry owners; a missing department does not justify inflating Scene into its replacement.


## Opt-in Director authority

Scene dramaturgy remains the owner of scene event and purpose; Dialogue Design owns exact spoken meaning. Canonical Scene.spokenContent remains the compatibility storage location, not a second dialogue author. In an opt-in Director request, consume pinned intent, preservation constraints and evidence obligations; develop the existing Scene structure and return its source-bound result or conflict. Director selects audience emphasis and reviews global usefulness, not a second Scene purpose. If requested emphasis changes locked causality or dialogue meaning, return DIRECTOR_REQUESTS_SCRIPT_REVIEW before any source change.


Consume the unified `creativeRhythm` from the actual creation context before planning, even when source text is already supplied. Follow [narrative rhythm](../../docs/narrative-rhythm.md); Skills never read env directly. Pin this profile to the creative revision; refresh/resume keeps it, while a new revision reads current configuration.

Turn one approved part of an Episode into a necessary, playable, state-changing dramatic event that covers assigned historical beats and realizes an explicit Narrative Input State → Required Transition → Narrative Output State. Do not design Shots.

When a [shared Dramatic Bible](../cinematic-screenplay-incubation/references/bible.md) is supplied, check knowledge at each decision, character invariants, power changes and entry/exit continuity. Review dialogue voice and subtext separately from scene causality; a wording revision preserves unrelated scene bodies and stable spoken-item IDs. Control metadata stays outside the readable script body; canonical SpokenContent ownership below remains unchanged.

When supplied, consume [CharacterEvidence and reusable LocationDesign](../../docs/location-character-design.md).
An attested person's existence does not prove presence in this Scene. Keep original
and composite identities explicit; never resolve them to historical people by name.
Reference existing places and request local time, ground, light or population
changes; altered geography returns to environment-design rather than duplicating a
new base environment inside every Scene. Preserve approved unrelated scenes in a
targeted revision.

For an authorized standalone candidate rewrite, use [whole-scene craft proof](../cinematic-screenplay-incubation/references/scene-craft-proof.md): retain formal sources and user locks, pin the candidate wording, and keep source mappings outside the readable body. Candidate approval never implicitly replaces formal `spokenContent`.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates a new Scene or revises an existing one, the parent Episode, requested dramatic moment and outcome, and explicit location, time, character, continuity, historical, or user constraints. Identify the concrete change that makes this Scene necessary; “show a relationship” or “discuss the situation” is not yet a sufficient purpose.

### 2. Gather Context

For screenplay handoff, read the [Cinematic Intent convention](../cinematic-screenplay-incubation/references/cinematic-intent.md). Retain only this scene's source-pinned POV, applicable opening/closing, subjective moments, bridges and MUST/SHOULD/FREE intent in its working set. Preserve approved scene action and exact dialogue; missing relevant intent is a focused context gap, not permission to pass the whole Bible downstream.

Assess context sufficiency before planning. Continue when the governing Work/Script context needed for historical evidence and Work-scoped `speakerKey` identity, the Episode dramatic job, assigned `requiredSpineBeatIds`, actor attribution, historical boundary, previous Scene Narrative Output State, next intended Narrative Input State, and required transition are supplied. Use `episode.get_episode` for the stable parent and `scene.get_scene` for a known `sceneId`. With a known `episodeId`, use `scene.list_scenes` for structural enumeration and neighboring continuity; when only a natural-language identity is known, use `scene.search_scenes` scoped to the Episode when possible and judge candidates. Read existing neighboring Scenes when speaker identity or spoken-item continuity must be preserved.

Use `context.build_context` only when required parent or existing Scene context was not supplied. Use adequate research context first; use `research.search_locations` only when missing location evidence affects the Scene and `research.verify_claim` only for a consequential unresolved claim. If broader evidence is required, formulate a focused research question and stop before planning or persistence so the Agent or Host can choose an existing research capability. If Episode intent, character state, essential continuity, or consequential evidence cannot be obtained or conflicts, state the blocker and do not draft or persist.

### 3. Plan

Before drafting, read [Professional Scene Planning](references/planning.md) and the [Dialogue Layer content convention](../../docs/dialogue-layer-content-convention.md), then apply them. Create an internal Scene plan that inherits the Episode; state assigned historical beats, a change-based purpose, `narrativeInputState`, `requiredTransition`, playable objective/opposition where appropriate, supported stakes, playable beats, meaningful turn, `narrativeOutputState`, necessity/coverage evidence, Shot-design contract, and unresolved questions. Decide whether exact spoken content is needed: environment, pure action, silence, reaction, battle, transition, or visually sufficient information may require none. When speech or narration is necessary, request reviewed exact text, stable speaker identity, dramatic intent, provenance and estimates from Dialogue Design before Shot design. Performance Direction separately supplies performance intent. Keep the plan in Agent Run Context or temporary working state. Do not call `scene.create_scene` or `scene.save_scene` to store it.

### 4. Execute Draft

Execute the dramaturgy plan as a complete candidate formal Scene state with approved causal action and, only when required, Dialogue Design’s reviewed exact spoken content. The professional SceneAssembly references the independent departments; do not paste their art, lighting, performance or editorial Bibles into Scene. A silent Scene keeps `spokenContent` empty; never add dialogue merely because the unit is a Scene. When speech is required, persist each `DIALOGUE` or `NARRATION` item with `id`, `kind`, `speakerKey`, exact `text`, `intent`, `mustKeep`, `performanceIntent`, `provenance`, and positive integer `estimatedDurationMs`. Character dialogue resolves its Work-scoped key without requiring a visual Asset; narration uses a stable `narrator:` key. Let resistance force tactic changes; use beats when objective, tactic, information, or power changes; let important information alter behavior; express interior states through behavior, movement, interaction, object use, reaction, choice, silence, distance, or position. A dialogue-function summary such as `dialogueSubtextIntent` may supplement but never replace required exact text. The draft must let Shot design cover approved action without inventing the conflict or spoken words. It must not be characters plus location, talking heads, historical exposition, static conversation, interior summary, placeholder, test content, or scratchpad. Do not persist a partial draft.

### 5. Review

Check that assigned cinematic meanings and their priorities survive in the Scene-to-Shot working context, including the subjective return and episode boundary when applicable. Keep a separate Historical Epilogue outside scene action and spokenContent. If a correct scene is merely misinterpreted by shots, route that finding to Shot planning; do not rewrite the scene.

Before any write, read [Scene Review and Revision](references/review.md) and apply the entire domain rubric, Before/After Gate, Delete Scene Test, narrative transition gate, and spoken-content gates. Critical checks separately cover assigned historical beat coverage, fact attribution, Narrative Input/Output State, Required Transition, `SCENE_STATE_CONTINUITY`, `CAUSAL_NARRATIVE_CONTINUITY`, historical integrity, necessity, and downstream readiness in addition to playable drama. When spoken content exists, also check speaker correctness, exact-text completeness, dramatic function, historical consistency, fact attribution, modern-language contamination, valid numeric duration, and provenance. `DIRECT_QUOTE` requires matching text plus nonblank source reference, exact locator, and excerpt; otherwise Review FAIL or explicitly downgrade it. If the prior output cannot lead to the current input, or an indispensable state change is skipped, return `FAIL_NARRATIVE_TRANSITION`. Mark Review PASS only when every critical check passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Follow [Scene Review and Revision](references/review.md): Locally revise dialogue, one tactic or beat, action clarity, subtext, or minor continuity. Preserve a spoken item `id` when wording, performance, duration estimate, or provenance detail changes but its logical identity remains. Only addition, deletion, split, or merge may create or retire affected IDs, and every unaffected ID remains stable. Re-plan the current Scene when its purpose, objective, opposition, conflict-in-action, turn, state change, playability, or necessity fails. If the root cause is the Episode dramatic job, label an upstream Episode issue instead of rewriting the Episode here. After any revision or re-plan, review the complete draft again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft exist as a playable state-changing dramatic Scene, all critical checks pass, and no historical or continuity conflict remains. Characters-plus-location/dialogue, pure exposition, missing objective/opposition/turn/state change, unplayable interior summary, or a removable Scene cannot pass. Plan, draft reasoning, rejected alternatives, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Scene `content`. Persist only the reviewed formal result.

Use `scene.create_scene` only for a genuinely new Scene after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `scene.save_scene` immediately afterward unless a concrete revision has actually occurred. Use `scene.save_scene` only to revise an already persisted Scene because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Episode ID, scene order, title, and optional location in the create envelope; use the stable Scene ID, order, title, and optional location for a revision. Put reviewed required spine beats, purpose, characters, time, Narrative Input State, Required Transition, objective/opposition, playable action, turn, Narrative Output State, necessity/coverage evidence, canonical `spokenContent`, and other formal Scene facts in the open `content` object. `spokenContent` is the sole reviewed source and may be empty. Do not persist aliases such as `dialogues`, `dialogueLines`, `spokenLines`, or `speech`, and do not create a Scene-local speaker registry. These are creative content, not new persistence fields. Do not move the parent Episode ID or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create; reconcile stable spoken item IDs before replacing content. Use `context.refresh_context` only after a write makes current context stale. Do not specify framing, camera position, coverage, create Shots, resolve assets, or automatically invoke another Skill.

## Performance language adaptation

Keep authoring/review, performance, and subtitle/epilogue languages distinct.
Resolve the current exchange language from explicit user choice and reviewed
character/scene context. Explicit dubbed editions remain valid. UI language,
nationality, and mother tongue alone never decide the exchange language (including
translation, diplomacy and multilingual scenes).

When the user authorizes a performance rendition, read full neighboring dialogue
and actions first. Preserve meaning, listener, subtext, character expression,
action prerequisites, historical events and Cinematic Intent. Review idiomatic
performance wording before audio production; the provider cannot adapt it.
Keep the frozen authoring source. A source-bound working artifact may hold
sourceLineId, speakerKey, sourceTextHash, performanceLanguage, performanceText,
renditionVersion, reviewStatus and optional subtitleText. Exactly one reviewed
rendition per line is active in a production attempt. Do not claim formal Scene
updates when only this artifact exists. Scene authoring owns eventual full-state
save/reconciliation through existing spokenContent, preserving IDs and source
provenance; audio production only consumes the selected wording. Unrequested lines
remain pending, and a wording change does not itself invalidate images/videos.

## Pressure, release and first appearance

Use the [peak/editorial contract](../../docs/dramatic-peak-editorial-contract.md) for PressureRelease and Scene-level DramaticPeakMap. State starting pressure, escalation, turn, release (or purposeful deferral) and aftermath, so equal tension at entry/exit is not mistaken for progression. Scene decides how a character enters; production-design decides visual importance; shot-design chooses the exact view. A core FirstAppearanceContract checks silhouette, costume/space/light priority, surrounding reactions and the first readable action/attitude. A name caption cannot replace these. Equal treatment with extras requires a hidden-identity story purpose. Do not write recommended peak changes over approved Canon merely to obtain intensity.


## Actor-playable screenplay handoff (Screenplay R2)

Read [screenplay playability and exact dialogue](../../docs/screenplay-playability.md). For each important actor/Beat, author objective, obstacle, playable action, current state, turn and reaction. Resolve explanatory prose to a visible/audible carrier or intent metadata. Preserve exact approved Dialogue and explicit targets.
