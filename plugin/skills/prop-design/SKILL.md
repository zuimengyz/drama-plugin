---
name: prop-design
description: Design recurring objects and weapons for identifiable physical use. Use for Prop Bible authoring and review; no media generation.
---

# Props and Weapons

## Role and authority

Design recurring objects and weapons for identifiable physical use.

Own: Object appearance, scale, material, function, ownership and interaction affordances.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Historical boundary; approved action; Environment/Layout; Character and Costume requirements.

## Professional decisions

Assign stable prop IDs to recurring weapons, flags, vessels, lamps, ropes, saddles, boats, gangplanks and poles. Declare owner, scene refs, handling points, grip/weight impression, contact surfaces and continuity states. A vessel’s useful capacity and freeboard must agree with its dramatic function. Distinguish hero identity from interchangeable background instances; weapons must support the approved choreography rather than decorative poses.

## Outputs

Read the selected screenplay in narrative Scene order to identify manipulated,
transferred or visually distinctive objects, including continuity across Shots
within one Scene. Record first appearance, consumers and whether later mentions
refer to the same physical object, a changed state or another instance. Similar
names or a common maker do not establish identity. Background dressing need not
become a separate reusable Asset.

For a continuity-critical prop, author one baseline with function, silhouette,
dimensions or relative scale, construction and separable parts, materials and
recognizable surface features. Distinguish the object, its separable parts and its
current state: an open construction view can prove the same body's matching lid
without authorizing an opening or closing in a later carrying shot. Cite the
current Action for entry, permitted change and exit; keep grip/support mechanics
with Action and placement with Layout. Wear or damage has a sourced history, not
a new identity each time it becomes visible. Pin user clarifications separately
from source facts and design interpretation; uncalibrated images establish
proportions, not exact dimensions.

Hand the baseline and its actual consumers to Asset Planning/Resolution. Establish
necessary visual proof at first narrative use, then reuse accepted identity,
version and Media. A changed state or angle is not a new asset. Preserve useful
approved views; request another proof only for a concrete unmet use, not a complete
view set. Missing proof stays pending and does not authorize generation. A sound
baseline can coexist with failed handling in a take: revise the failing use rather
than redesigning the object to match the generated mistake.

Produce a versioned `Prop Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Each important object has an actionable function and scale; ownership/handoff and damage are traceable; no invented technology or magically changing dimensions.

## Failure and escalation

Return body mechanics to Action, placement to Layout and appearance conflicts to Production Design alignment. Animals have their own design owner and are not Props.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
