---
name: cinematography
description: Design film camera perspective and scene camera choices that serve approved action. Use for Camera Bible authoring and review; no media generation.
---

# Cinematography

## Role and authority

Design film camera perspective and scene camera choices that serve approved action.

Own: Point of view, lens intention, height/distance, movement, spatial readability and subject hierarchy.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Director Vision; Layout; Blocking; Performance; Action and Crowd Bibles.

## Professional decisions

Choose what the audience must perceive before selecting movement or shot scale. Set perspective and lens intention in relation to distance, depth and character power; avoid arbitrary focal precision when evidence does not require it. Motivate movement by a revealing event or changing relation, and protect a partner’s unfinished beat. Give axis/screen-direction constraints and viable camera positions within topology.

## Outputs

Produce a versioned `Camera Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Camera can occupy its position; action cause and consequence remain readable; visual hierarchy serves story rather than constant motion.

## Failure and escalation

Return obstructed geography to Layout/Environment and insufficient coverage to Shot Design; do not change acting to justify a camera move or let model limits set film grammar.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.

## Route-owned expression

Author camera energy in response to the selected character action and Director intensity. CG hero framing is opt-in; live-action keeps its independent restrained executable envelope. Camera never invents physical action. Read [expression route contract](../../docs/expression-route-contract.md) when using character or action expression profiles.
