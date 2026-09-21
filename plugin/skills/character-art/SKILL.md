---
name: character-art
description: Design reusable face, body and screen identity under approved character meaning. Use for Character Art Bible authoring and review; no media generation.
---

# Character Art

## Role and authority

Design reusable face, body and screen identity under approved character meaning.

Own: Stable visual archetype, apparent age, proportions, face structure, silhouette and readable identity anchors.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Character Package with authored Embodiment; Director Vision; Adaptation Boundary; explicit route. Existing approved appearance is optional for first design.

## Professional decisions

Specify apparent age, height impression, body proportion/mass and shoulder-to-waist relation only to useful discriminating precision. Describe face structure, jaw, eyes, brows, nose, skin, hair and facial hair as a coherent person; avoid a checklist of unrelated ideal features. Separate dominant and secondary traits and screen presence. State realistic and CG translations of the same identity, camera-readable anchors, forbidden appearance and future reference proof duties. Stable hair identity belongs here; scene grooming and injury belong to Look.

## Outputs

Produce a versioned `Character Art Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Character distinction and leading/supporting hierarchy work without costume spectacle; no real-star copy or unsupported exact historical portrait; reference requirements test identity rather than prettiness.

## Failure and escalation

Return dramatic identity to character-dramaturgy; costume to costume-design; transient wear to look-continuity. Missing evidence remains a design choice with its boundary, not an asserted fact.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.

## Route-owned expression

Own the route-specific face/body/silhouette and neutral dominant presence. Share narrative core only; never copy a CG expression envelope into a live-action design. Read [expression route contract](../../docs/expression-route-contract.md) when using character or action expression profiles.

## Character Package ownership

Design visual realization from the selected package envelope. Do not invent personality, psychology, fundamental archetype or character distinction. Return missing identity to Character External Driver.

Use the unified read-only `CharacterRepository.resolve_character_package` contract in [Character External Driver](../../docs/character-external-driver.md). Pin characterPackageRef, characterPackageVersion and checksum. Never create or overwrite Character Core in this Skill. Missing or stale packages return to the driver; model memory and old chat are not assets. DESIGN_REVIEW access does not authorize casting or production.

For the first external-package-only visual test, emit source-pinned PackageVisualParagraph records for `characters.casting`. Mark concrete face/body/wardrobe/pose choices as VISUAL_INTERPRETATION_NOT_NEW_CORE; unresolved appearance is a candidate proposal, not a new fact or approved identity. Every paragraph points back to the selected package. Do not read an archived instance to fill it.

## Character Embodiment ownership

Consume Character Core + Embodiment + the explicit Visual Route before choosing concrete appearance. Do not rediscover bodily personality from literary labels. A missing canonical image is valid for first design; missing embodiment returns to its author, missing character meaning to Driver.

Read [Embodiment contract](../../docs/character-embodiment.md). Use the unified read-only `characters.embodiment.embodiment_handoff` with exact ref/version/checksum and route. Never create or overwrite embodiment in downstream execution. Comparisons are reasoning-only; they do not enter the generation prompt.
