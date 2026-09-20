---
name: color-grading
description: Define final image balancing intent distinct from preproduction color design. Use for Grade Bible authoring and review; no media generation.
---

# Final Color Grading

## Role and authority

Define final image balancing intent distinct from preproduction color design.

Own: Shot matching, tonal balance, skin/material fidelity and final grade constraints.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Color Script; Lighting; Camera; later measured image evidence if available.

## Professional decisions

Preserve the approved narrative color arc while identifying shot matching, exposure and skin/material fidelity objectives. Keep design-time targets separate from corrections justified by actual footage. If no footage exists, state intended tolerances and unresolved conform duties; do not invent a successful grade or numeric transform.

## Outputs

Produce a versioned `Grade Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Grade does not change costume identity, time of day or lighting causality; matched shots still belong to the film’s color arc.

## Failure and escalation

Return creative palette changes to Color Design and missing imagery to future postproduction. A grade is not a repair for unsupported source lighting or missing action.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
