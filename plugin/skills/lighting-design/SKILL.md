---
name: lighting-design
description: Design motivated light and visibility across scenes without changing art. Use for Lighting Bible authoring and review; no media generation.
---

# Lighting Design

## Role and authority

Design motivated light and visibility across scenes without changing art.

Own: Sources, motivation, direction, intensity ratios, contrast, falloff and day/night continuity.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Environment Art; Camera; scene time/weather; Director visibility priorities; Prop practicals.

## Professional decisions

Identify where light physically comes from and what it reveals or conceals. Separate practical visible flame/lamp from its motivated illumination intent. Describe relative intensity, falloff, contrast and face/background separation, preserving material and skin identity. A dawn delta must replace night illumination coherently rather than retaining contradictory key sources.

## Outputs

Produce a versioned `Lighting Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Required action, eyes/hands or silhouette stay readable for the intended shot; source direction and time are continuous; lighting does not repaint materials or rebuild a set.

## Failure and escalation

Return impossible source placement to Layout/Props and material conflicts to Environment Art. Color Design decides palette development; grading does not retrospectively excuse an unmotivated source.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
