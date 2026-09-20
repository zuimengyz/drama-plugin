---
name: battle-crowd-choreography
description: Design group movement, military reactions and local versus global timing. Use for Battle / Crowd Bible authoring and review; no media generation.
---

# Battle and Crowd Choreography

## Role and authority

Design group movement, military reactions and local versus global timing.

Own: Formations, cavalry/infantry movement, retreat/pursuit and ensemble response timing.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Historical army/entity identities; Environment; Scene Layout; Action; approved battle causality.

## Professional decisions

Separate command, visible signal, receiving group and delayed response. Track formation frontage, depth, routes and what participants can know. Causal phases may include contact, retreat, wing entry, turn and renewed advance; use only the order approved in this story. Ordinary background participants react locally, not in perfect synchrony to an unseen event. Account for terrain, distance, dwindling strength and pursuit discovery.

## Outputs

Produce a versioned `Battle / Crowd Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Named commanders perform their documented causal duties; crowd flows have origins/destinations and avoid collisions; direction and army counts remain continuous.

## Failure and escalation

Return missing army identity to Historical Entity Registry and tactics beyond the source to adaptation-boundary; blockers in lanes return to Layout. Do not solve scale with random running or invented command dialogue.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
