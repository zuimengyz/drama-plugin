---
name: action-choreography
description: Specify causal body and object mechanics before a complex shot is produced. Use for Action Bible authoring and review; no media generation.
---

# Action Choreography

## Role and authority

Specify causal body and object mechanics before a complex shot is produced.

Own: Contact, grip, load, support, balance and ordered physical action phases.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Approved action outcome; Blocking; Performance intent; Prop and Animal interaction constraints.

## Professional decisions

Decompose action by physical changes: preparation, contact, support/load transfer, correction, consequence and recovery. Name actor, limb/side, receiver/object, grip establishment and release. A failed attempt must alter the next action; do not jump from reach to successful mount. Declare what must remain observable and what cannot overlap safely or plausibly. Complexity may propose coverage changes, never rewrite the event.

## Outputs

Produce a versioned `Action Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Every result has an enabling contact and support; body/prop states bridge phases; injury and fatigue constrain execution; no physically impossible teleportation.

## Failure and escalation

Missing Blocking or object scale returns dependency failure; proposed event changes go to Screenplay/Director. A provider limitation cannot replace choreography with vague action words.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.

## Route-owned expression

Within the Director-selected route envelope, author anticipation, acceleration, impact, follow-through and environmental reaction. Preserve support/contact/weight and canonical outcomes. A character action signature does not propagate to other actors. Read [expression route contract](../../docs/expression-route-contract.md) when using character or action expression profiles.

## Character Package ownership

Combine screenplay facts, Director intent and the packaged actionSignature. Do not decide the character movement identity anew or add event outcomes.

Use the unified read-only `CharacterRepository.resolve_character_package` contract in [Character External Driver](../../docs/character-external-driver.md). Pin characterPackageRef, characterPackageVersion and checksum. Never create or overwrite Character Core in this Skill. Missing or stale packages return to the driver; model memory and old chat are not assets. DESIGN_REVIEW access does not authorize casting or production.

## Character Embodiment ownership

Combine script action + Director intent + embodiment baseline + actionSignature. Do not invent movement identity or new action results.

Read [Embodiment contract](../../docs/character-embodiment.md). Use the unified read-only `characters.embodiment.embodiment_handoff` with exact ref/version/checksum and route. Never create or overwrite embodiment in downstream execution. Comparisons are reasoning-only; they do not enter the generation prompt.

## Still live-action professional knowledge

For opt-in STILL/LIVE_ACTION, project only the approved current body_mechanics or contact_constraints slice into existing action/contact facts. Ordered future phases and movement timing remain internal to this still consumer. Identity references cannot create an action. Support/load/contact comes from Action and Blocking; material response and conditional contact shadow remain Lighting/QA responsibilities.

Read [mapping and evidence profile](../../docs/still-professional-mapping.md) when preparing these still records. Knowledge remains LOCAL_EXPERIMENTAL until scoped A5 media evidence.
