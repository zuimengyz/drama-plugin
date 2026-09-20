---
name: vfx-planning
description: Plan visual extensions and composites without changing recorded historical events. Use for VFX Bible authoring and review; no media generation.
---

# VFX and Compositing Planning

## Role and authority

Plan visual extensions and composites without changing recorded historical events.

Own: Crowd/environment extension and smoke/dust compositing requirements.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Approved Environment/Art; Camera; Crowd/Action; Shot and continuity states.

## Professional decisions

Separate foreground practical/hero action from distant extension. Specify depth planes, occlusion, contact/atmospheric integration and elements that must remain stable for compositing. Crowd extension preserves the approved army identity, scale and movement pattern. Choose NOT_REQUIRED with a reason when existing design has no effect duty.

## Outputs

Produce a versioned `VFX Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

No new historical participant or event is invented; extensions match light, perspective and continuity; effects do not obscure causal action.

## Failure and escalation

Return action/formation gaps to those owners and camera conflicts to Cinematography; no generation or render pipeline is authorized by a plan.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
