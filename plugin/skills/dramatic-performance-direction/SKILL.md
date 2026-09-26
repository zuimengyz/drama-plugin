---
name: dramatic-performance-direction
description: Build a replayable, provider- and modality-neutral Scene/Beat/Line performance direction from an approved dramatic scene; do not generate media or provider controls.
---

# Dramatic Performance Direction

Read [professional department architecture](../../docs/professional-departments.md).

## Role and authority

Performance direction: retain DPD psychological truth and author physical expression in a separate Performance Bible facet.

## Inputs and dependencies

Scene/Character/Dialogue, Director Performance Intent, Blocking and causal action constraints.

## Outputs

Performance Bible with DPD refs plus gesture, micro-action, listening, breathing and physical-state direction.

## Forbidden authority

Do not rewrite character identity, speech, spatial paths or detailed force/contact mechanics. Voice execution belongs to voice-direction.

## Quality gates

Check actor and listener task, restraint, physical load and continuity per beat; internal pressure is independent of outward amplitude.

## Failure and escalation

Return path defects to Blocking, impossible mechanics to Action and source conflicts to Screenplay. No generation follows from performance design.


## Partners and groups are source-owned too (R3)

Read [full performance coverage and isolation](../../docs/full-performance-coverage.md). Every important listener needs its own sourced DPD task, obstacle and tactic, not a reaction label or a Director-invented psychology. Missing partner direction returns PARTNER_DPD_REQUIRED to this owner. Background listeners may use an existing BeatDPD group task; no Crowd Psychology. Candidate screenplay previews stay DESIGN_FIXTURE_ONLY, separately stored from formal DPD. Continuity summaries reference these DPDs without copying objective/subtext/knowledge/relationship truth.

## One cross-modal performance truth (R2)

Read the [shared performance contract](../../docs/cross-modal-performance-direction.md) when projecting into body and voice. Scene/Beat/Line DPD and the composed snapshot remain the only owners of objective, obstacle, tactic, subtext, knowledge, relationship, internal activation, external control and interaction target. Preserve the source and composition fingerprints; an inconsistent snapshot requires DPD review.

The Director adds audience-facing performance scale and release, not another psychological layer. VisualPerformanceBrief and AudioPerformanceBrief reference the same DPD, Director intent, Beat and SpokenContent. Never translate HIGH internalActivation automatically into crying, shouting, shaking or whispering. Keep externalControl independent. Return an actual conflict in source psychology to this owner; execution mismatch alone belongs to visual/audio repair.

## Opt-in Director authority

DPD remains the canonical owner of objective, obstacle, tactic and subtext. Consume a Director request as pinned intent and constraints, not another psychological truth. Its Scene dramaticPurpose is a source-derived summary, not independently editable purpose. Return the original DPD snapshot/fingerprint, evidence and unmet requirements in CapabilityFeedback. Director may accept or return the proposal; conflicts with source dialogue require upstream review rather than a silent rewrite.


Build one compact `dpd-v1` direction for an approved Scene before modality-specific production. Read the [DPD Core contract](../../docs/dpd-core-contract.md) before composing it.

Load only the context needed to explain the current dramatic action. Start with `scene.get_scene`; use `episode.get_episode`, `script.get_script`, and `work.get_work` only for unresolved dramatic purpose, stable speaker identity, relationship, hierarchy, or historical/social constraint. Use `context.build_context` only when these direct reads cannot supply a required parent relation. Do not retrieve history independently or copy whole Character profiles into the direction.

Create three sparse layers in temporary Agent state:

- Scene DPD: dramatic purpose, active conflict, power structure, public/private context, and only material climate, urgency, information, or social constraints.
- Beat DPD: current actor, target, objective, obstacle, tactic, authority/relationship position, internal activation, external control, and transition trigger.
- Line DPD: the canonical `spokenContentId` and speaker, this line's dramatic action, observable intent, continuity/change, and only genuine Beat overrides.

Compose `Scene → Beat → Line` with the typed Core. Missing and null fields inherit; v1 has no scalar-reset syntax. A supplied list replaces the parent list, and an empty list clears it. Line wins over Beat, Beat wins over Scene. Any mismatched Scene or Beat reference is invalid. Keep the resulting `DPDSnapshot` and fingerprint together so downstream work can replay the same decision without reinterpreting the whole script.

Use action and relationship language, not moral labels or a single emotion label. Keep internal activation distinct from external control: high activation may remain highly controlled. `speakerKey` references identity; it does not duplicate age, rank, biography, personality, or Voice Profile.

Do not add speech speed, pitch, loudness, pause milliseconds, articulation, voice identity, provider prompt, model settings, camera or framing to DPD. Reuse the existing DPD fields; the R2 nested playability witnesses add source/carrier evidence without a second psychological authority. The separately owned Performance Bible may author gaze, posture, gesture, breath behavior and physical-state expression; Blocking owns paths/positions and Action owns physical mechanics. Voice Direction consumes that common performance truth for vocal delivery. Do not generate Audio/Visual Media, persist a new business entity, or invent a DPD-specific Tool.

Finish when the three contracts validate, the effective direction is materially playable and distinct from character identity, and the canonical fingerprint is recorded. If essential objective, target, relationship, or historical/social constraint is unsupported or contradictory, report the missing input instead of filling it with stereotype or provider detail.

For a text-only candidate, pin the selected screenplay artifact revision and line locators instead of pretending it is an adopted Scene. Extract only its dramatic action; do not copy or rewrite its speech. Keep the same Scene/Beat/Line ownership and clearly local identities. An unapproved visual design does not block this offline interpretation or authorize production. See [whole-scene craft proof](../cinematic-screenplay-incubation/references/scene-craft-proof.md).

An explicit [visual route](../../docs/visual-route-contract.md) belongs to the downstream visual projection. Preserve this modality-neutral DPD and its fingerprint; the Performance Bible supplies physical realization while cinematic-direction projects its reviewed references without re-authoring it.

## Range and formal source safeguards

Author internalActivation and externalControl per actor and Beat; never assign a film-wide HIGH/HIGH default. Anti-overacting does not mean low physical energy. Director envelopes can permit high physical release while voice projection remains limited to the actual listeners. Distinguish forbidden emotional collapse from a scripted physical loss of support after its source action; source-exact physical consequences are scoped in Director intent and checked by validate_action_performance. Never use a global “no collapse” to contradict Script.

For formal review, SceneDPD must bind the current canonical Scene fingerprint, with real parent/Beat/SpokenContent and speaker bindings. Proposal previews cannot be relabeled formal; compose DPD anew after promotion. See [formal completion](../../docs/formal-book-completion.md).

## Observed adaptive direction

For evidence-based performance correction, useful unplanned results or adaptive
repair decisions, follow [adaptive director review](../../docs/adaptive-director-review.md).
Reuse FilmReview and Director feedback; separate intended authority, observable
facts and judgment. Resolve the production lineage before live review, preserve
UNSPECIFIED and good material, and pass only a minimal source-bound execution delta
to the existing owner. A dry-run never authorizes production or media adoption.

## Character Embodiment ownership

Use embodiment for stable physical tendencies and pressure/social transformations; author only scene/beat realization. Do not replace packaged character meaning with new psychology.

Read [Embodiment contract](../../docs/character-embodiment.md). Use the unified read-only `characters.embodiment.embodiment_handoff` with exact ref/version/checksum and route. Never create or overwrite embodiment in downstream execution. Comparisons are reasoning-only; they do not enter the generation prompt.


## Actor-playable screenplay handoff (Screenplay R2)

Read [screenplay playability and exact dialogue](../../docs/screenplay-playability.md). Consume the source-authored playable task and its line intent. Bind BeatDPD/LineDPD playability witnesses and exact dialogue hashes; do not infer a new objective from abstract emotion. Keep actor and listener tasks distinct.
