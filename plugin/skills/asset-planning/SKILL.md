---
name: asset-planning
description: Choose reusable production assets from reviewed creative departments. Use for Asset Manifest authoring and review; no media generation.
---

# Asset Planning

## Role and authority

Choose reusable production assets from reviewed creative departments.

Own: Manifest necessity, variant scope, reuse and production duty for approved designs.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Reviewed DirectorPackage; Character/Costume/Environment/Prop/Animal/Voice originals; shot usage.

## Professional decisions

Inventory only what shots actually consume. Distinguish reusable identity, costume stage variants, location bases, hero props, animal references and voice identities from transient shot states. Reuse a suitable approved asset before requesting a new reference. Each planned item identifies consumers, source design and proof purpose; it is not a fabricated Asset or Media ID.

## Outputs

Include screenplay-derived prop consumers, not only dialogue speakers. For each
continuity-critical object, index its Prop Design original, first narrative Scene
and all relevant Scene/Shot uses. Establish its baseline once, then resolve the
same physical identity for later uses. Distinct objects of the same kind remain
distinct; temporary open/closed or carried state stays with the current action.
Require visual proof when silhouette, scale, separable construction, material or
handling continuity cannot be established by text alone. Do not mark that proof
optional merely to advance video production without an asset budget. Keep the
reference duty pending and continue independent unpaid preparation.

Produce a versioned `Asset Manifest` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

No orphan speculative assets; required recurring identities have coverage; planned versus existing assets remain distinct.

## Failure and escalation

Return missing design to its department and unresolved approval to the Host. This plan never creates images, audio or a paid provider request.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
