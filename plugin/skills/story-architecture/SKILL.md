---
name: story-architecture
description: Design premise, dramatic question and causal film structure before scene writing. Use for Story Bible authoring and review; no media generation.
---

# Story Architecture

## Role and authority

Design premise, dramatic question and causal film structure before scene writing.

Own: Story theme, protagonist focus, acts, escalation, climax and ending.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Historical Source/Entity and Adaptation Boundary Bibles; authorized creative intent; existing Work/Script locks.

## Professional decisions

Map indispensable historical events to dramatic causes, consequences and audience knowledge. Choose the protagonist by causal scope, not by how easily a provider can depict them. Escalation must change available choices; climax answers the dramatic question; aftermath earns the ending. On migration extract the approved structure without adding a new act or a better ending.

## Outputs

Produce a versioned `Story Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Every sequence advances causality or necessary understanding; historical actor attribution survives; structure is not a quota.

## Failure and escalation

Request an explicit upstream story revision when approved causes conflict. Downstream design difficulty cannot authorize a rewrite.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
