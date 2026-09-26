---
name: cinematic-direction
description: Assemble approved professional direction into the existing CinematicShotSpec before route selection; use for source-bound projection, not new art, camera or acting design.
---

# Cinematic Execution Projection

## Role and authority

Own the compatibility projection into CinematicShotSpec and its freeze evidence. Creative decisions belong to the referenced departments; this is not a fifth department that redesigns them.

Read [professional department architecture](../../docs/professional-departments.md) for owned Bible records, dependency gates and Host handoff.

## Inputs and dependencies

Current Shot and exact SpokenContent bindings; Director intent; Camera, Lighting, Color, Blocking, Performance, Action, Crowd, Voice, source-sound, reference and continuity originals.

## Professional decisions

Resolve source refs before assembling Opening → authored beats → Ending. Preserve the existing DPD objective/target and exact dialogue speaker/text. Carry physical acting and native voice from their reviewed briefs, non-lexical vocal intent through SourceSoundIntent, and reference roles as REQUIRED/PREFERRED. Reconcile simultaneous demands; never fill a missing beat with invented gesture, lens, light or vocal instruction. The projection may format existing decisions into execution requirements, but must not optimize creative meaning for a selected model. Omit irrelevant optional fields rather than inventing defaults.

## Outputs

The existing source-pinned CinematicShotSpec, its source/visual fingerprints, unresolved requirements and projection coverage evidence. Department originals remain independently versioned.

## Forbidden authority

Do not author Look Development, camera, physical performance, temporal choreography, voice or lighting here. Do not create a provider prompt, model/workflow parameter, Media or approval. A frozen projection cannot cure an incomplete department dependency.

## Quality gates

Use the existing attach_cinematic_performance and source/grammar validators. Preserve canonical lines, DPD/intent fingerprints, inherited visual identity and all department continuity states. Offline validity is not performance quality or production authorization.

## Failure and escalation

Return a missing or conflicting field to its registered owner. If departments disagree, Director arbitrates WHY; the owner revises HOW. Route infeasibility returns through video-model-selection without silently dropping a requirement.

Read [existing IR and freeze contract](../../docs/cinematic-direction-contract.md), [cross-modal bindings](../../docs/cross-modal-performance-direction.md) and [full coverage](../../docs/full-performance-coverage.md) only for the applicable projection path.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.

## Route-owned expression

Project the approved envelope as CinematicShotSpec.expressionDirection when supplied. Verify exact Work route, character/core revision, Director scope and source beat fingerprint. Preserve all canonical facts. Read [expression route contract](../../docs/expression-route-contract.md) when using character or action expression profiles.


## Actor-playable screenplay handoff (Screenplay R2)

Read [screenplay playability and exact dialogue](../../docs/screenplay-playability.md). Consume mapped DPD and reviewed ObservableAction/Blocking. Project the same meaning into existing CinematicShotSpec; absent objective/action fails upstream, never requests creative repair from a Prompt Generator.
