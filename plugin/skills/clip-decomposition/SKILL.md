---
name: clip-decomposition
description: Plan executable clip boundaries while preserving canonical coverage and action. Use for Generation Clip Plan authoring and review; no media generation.
---

# Generation Clip Planning

## Role and authority

Plan executable clip boundaries while preserving canonical coverage and action.

Own: Clip-level grouping, entry/exit bridges and event protection beneath stable Shot IDs.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Shot/Editorial; Action and Performance; Asset/Reference Plan; continuity ledger.

## Professional decisions

Split only where an action state can be handed off clearly; never cut between unresolved support and its immediate consequence without a continuity bridge. Keep canonical Shot/Coverage IDs and name clip consumers separately. Allocate meaningful performance, dialogue and transition time; verified model duration/input limits inform provisional coverage and are rechecked at execution; they do not define artistic rhythm.

## Outputs

Before choosing boundaries, read the scene's action-rhythm passages and the
Performance/Editorial realization. Group a continuous task and the contrast that
gives it meaning; do not map each verb or beat to a separate generation. Neither
equal shares of the Shot estimate nor the provider maximum determines clip length.
Explain each necessary split through action, dialogue, support and recoverable
state, including its cost to momentum. A boundary must not add another wait or
restart preparation already completed. AUTO chooses output length, not dramatic
pacing: preserve relative speed, purposeful holds and release triggers explicitly.
If the scene genuinely needs equal rhythm, retain it with its source reason.
Record remaining feasibility uncertainty rather than promise that AUTO will fit.

Retain a Host-selected grouping in the existing Editorial facts as optional
`generationGroups: [{phaseIndices: [0, 1], reason: "selected viewing tradeoff"}]`.
These are explicit Clip Plan selections, not new Shot identities or a timing
state machine. Indices refer to the current Action original; revise both together.
The native opening selector and next-unit preview consume these groups. Records
without them retain historical single-row selection; no automatic regrouping of
adopted work occurs. Duration remains the separately selected execution profile.

Use the existing native `OperationResolver.select_unit(..., phase_indices=(...))`
to bind a Host-selected consecutive group of Action analysis rows; `phase_index`
retains the legacy single-row choice. This explicit selection does not infer
parallel action, film cuts or duration. Keep the selected action/beat/line refs,
first entry and last outcome; pass the chosen technical duration separately.
For a technical continuation, retain the exact predecessor and continuing
camera, support, action and audio state. For film coverage, use authored Shots
and editorial relations rather than disguising a new view as a technical child.
The remaining-content read view is an inventory, not an instruction to generate
each remaining Phase. Record intended edit use separately; actual trims wait for
footage. Historical frozen selections are not automatically regrouped.

Produce a versioned `Generation Clip Plan` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Every clip begins/ends in a recoverable state; all protected events and exact lines are covered; no formal Shot is invented by a production split.

## Failure and escalation

Return overload to Shot/Editorial for authorized coverage change; missing interaction references to Reference Strategy. No provider submission follows from a plan.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
