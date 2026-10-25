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

Use [shared scene collaboration](../director/references/scene-collaboration.md)
to develop the spectator's changing relation across scenes and within a scene.
Carry the selected arc in Color Script, and only its current observable consequence
in scenePalette. A scene-wide mood label must not erase different encounters or
force a warm/cold switch at each turn. Preserve a motivated counterpoint.

Track hue, value, saturation and warm/cool relationships over dramatic phases. Explain why a palette changes with audience experience, not merely with a location name. Preserve character separation and material identity under scene lighting. Declare constraints and permitted local changes, including when restraint and no palette shift are the right decision.

Begin with the work's central contradiction and the audience's changing relation
to its people. Form a film-wide color proposition, then test it against concrete
scenes and a counterexample. A cold dominant world may contain ordinary warmth;
grief need not make daylight dark, and dawn need not signify forgiveness. Follow
the particular work rather than prescribing a genre palette or moral color code.

Develop the arc through motivated warm/cool relations, saturation, tonal
separation and the visible reach of light. Distinguish a material's stable color
from how it appears under changing light. A transition can let a previously
closed space become perceptible without turning it golden or repainting faces.
Retain local contradictions when they carry dramatic meaning.

With Lighting, locate how warm and cool contributions meet in a material's
midtones, highlights and shadows. Decide their relative reach and saturation,
not just two hue names: a warm face against a cold wall can become a cutout when
the intervening planes share no light or color relation. Separation or a sharp
boundary may instead be the intended effect. Across encounters, change or retain
these relations through source balance, position and view; preserve local skin
and garment identity. Finishing can change perceived color and tone; do not assume
it will resolve an unaddressed material conflict, or infer from a successful
correction that the original material choice was appropriate.

Consider time of day as an expressive choice with Lighting and Director. Read
the scene's actual chronology, work, travel, public activity and spoken cues
before proposing dusk, night or dawn. Color cannot silently turn approved day
into night. Put any necessary time revision through the existing Scene owner;
carry its consequences into World, Lighting, Sound and adjacent scenes. Keep
source-compatible palette decisions distinct from proposed time changes. Store
the film's choices in its Color Script and current professional originals, not
in this Skill or an appended generation prompt.

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

## Still live-action professional knowledge

For STILL/LIVE_ACTION, author source-bound scene/sequence palette and character/environment relations under the existing keys. Separate actual hue/value/saturation obligations from mood labels. Required targets map to critical preservation; only explicitly optional decoration may be secondary. Preserve approved complexion and costume/material identity under light. Story era never determines capture era. No preset filter, provider parameters or unapproved whitening.

Read [mapping and evidence profile](../../docs/still-professional-mapping.md) when preparing these still records. Knowledge remains LOCAL_EXPERIMENTAL until scoped A5 media evidence.
