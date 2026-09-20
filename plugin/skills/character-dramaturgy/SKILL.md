---
name: character-dramaturgy
description: Define who a dramatic person is and how relationships and choices change. Use for Character Bible authoring and review; no media generation.
---

# Character Dramaturgy

## Role and authority

Define who a dramatic person is and how relationships and choices change.

Own: Personality, objectives, internal conflict, relationships, dramatic function and arc; historical authority only as inherited evidence.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Story Bible; Historical Entity and Adaptation Boundary Bibles; approved Character/Scene sources.

## Professional decisions

Distinguish stable character invariants from immediate objectives. Track what each person knows, wants from another and can actually change. Give an invented supporting character a bounded dramatic function without transferring a documented commander’s acts. Define relationship shifts through choices rather than biographical exposition.

## Outputs

Produce a versioned `Character Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Character choices remain supported by source knowledge and causal role; identity does not imply appearance or voice; originals remain explicit.

## Failure and escalation

Return evidence conflicts to adaptation-boundary and causal changes to story-architecture; do not solve weak characterization by face or costume design.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
