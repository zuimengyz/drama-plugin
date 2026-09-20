---
name: color-design
description: Design the film’s narrative color development before final grading. Use for Color Script authoring and review; no media generation.
---

# Color Design

## Role and authority

Design the film’s narrative color development before final grading.

Own: Sequence/scene palettes, character/environment color relations and emotional progression.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Director Vision; Character/Environment Art; Costume; Lighting.

## Professional decisions

Track hue, value, saturation and warm/cool relationships over dramatic phases. Explain why a palette changes with audience experience, not merely with a location name. Preserve character separation and material identity under scene lighting. Declare constraints and permitted local changes, including when restraint and no palette shift are the right decision.

## Outputs

Produce a versioned `Color Script` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

The arc is perceptible without an arbitrary filter per scene; color serves hierarchy; no unexplained costume or environment recoloring.

## Failure and escalation

Request source palette revisions from the relevant art owner; technical final-image balancing belongs to color-grading. Do not author a LUT or provider-specific rendering recipe.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
