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

Use the Environment zone graph rather than a second map. Distinguish current
placements from permanent landmarks. For a contested passage or handoff, sketch
the relevant footprint at useful relative scale: include the carried object,
hands and receiver, not just actor centres. Check the turn's swept space and a
waiting position outside the through-path; a narrow lane need not fit two people
abreast. Label assumed dimensions and show what would invalidate the arrangement.
Keep this proof with the existing layout; hand Blocking the usable lane and
release boundary, and Camera the visible landmarks. A clear plan does not prove
body reach, vertical clearance or image readability.

## Outputs

Produce a versioned `Scene Layout Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

In the native WORLD handoff, retain the selected arrangement and its usable
clearance conditions in `setting` and `physicalWorldRules`. A deferred instruction
to "check that it fits" is still unresolved. Distinguish a feasible arrangement
under stated relative-scale assumptions from measured space; keep the critical
occupied regions and release boundary available to Action and Camera consumers.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Every placement and lane resolves to topology; needed entrances/exits are reachable; formations fit; no camera or art choice changes the map.

## Failure and escalation

Request geometry repair from Environment and object changes from Props; Blocking owns timed actor movement. Incomplete topology blocks final layout.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
