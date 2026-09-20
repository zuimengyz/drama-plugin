---
name: scene-layout
description: Place people, formations and action objects within an approved environment. Use for Scene Layout Bible authoring and review; no media generation.
---

# Scene Layout

## Role and authority

Place people, formations and action objects within an approved environment.

Own: Scene-specific zones, initial/final placements, action lanes and occupied space.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Environment topology; Scene Beat Bible; approved people/objects and crowd intent.

## Professional decisions

Use the Environment zone graph rather than a second map. Set character start positions, relation distances, army placement, practical object locations and viable movement lanes. Distinguish a current placement from a permanent landmark. Give only useful functional scale; reserve space for an actor to turn, mount, pass or hand off.

## Outputs

Produce a versioned `Scene Layout Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Every placement and lane resolves to topology; needed entrances/exits are reachable; formations fit; no camera or art choice changes the map.

## Failure and escalation

Request geometry repair from Environment and object changes from Props; Blocking owns timed actor movement. Incomplete topology blocks final layout.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
