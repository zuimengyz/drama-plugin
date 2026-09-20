---
name: environment-design
description: Design reusable physical places, routes and spatial constraints. Use for Environment Bible authoring and review; no media generation.
---

# Environment Functional Design

## Role and authority

Design reusable physical places, routes and spatial constraints.

Own: Location identity, macro geography, terrain, topology, entrances/exits, zones, routes, sightlines, scale and spatial continuity.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Historical geography and boundary; approved scene events; existing LocationDesign originals.

## Professional decisions

Build a connected zone graph with distinct land, water and passable movement routes. Separate macro geography from staging choices and unsupported survey precision. Record visibility, ground slope/support, bottlenecks and clearances that constrain armies, actors, horses and objects. Shared places retain the same graph across scenes; time, weather or damage may affect use but cannot silently relocate an exit.

## Outputs

Produce a versioned `Environment Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Every route ends in known zones; water crossings have a physical means; parent places and scene references resolve; constraints permit the required action.

## Failure and escalation

Return topology revision to this owner; ask history for consequential geography uncertainty. Do not fill environment fields with camera, lighting, sound, costume or art direction; reference those Bibles.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
