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

Split only where an action state can be handed off clearly; never cut between unresolved support and its immediate consequence without a continuity bridge. Keep canonical Shot/Coverage IDs and name clip consumers separately. Allocate meaningful performance, dialogue and transition time; model duration caps are later feasibility constraints, not artistic rhythm.

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

Produce a versioned `Generation Clip Plan` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Every clip begins/ends in a recoverable state; all protected events and exact lines are covered; no formal Shot is invented by a production split.

## Failure and escalation

Return overload to Shot/Editorial for authorized coverage change; missing interaction references to Reference Strategy. No provider submission follows from a plan.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
