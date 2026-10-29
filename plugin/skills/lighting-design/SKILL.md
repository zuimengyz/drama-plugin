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

In [shared scene collaboration](../director/references/scene-collaboration.md),
distinguish continuity of the room's sources from constancy of their effect on
people. Coordinate their changing place, camera viewpoint and visibility priority;
do not reset every later encounter to an admired earlier frame. Equally, emotional
change alone does not authorize relighting a source or inventing a new time.

Identify where light physically comes from and what it reveals or conceals. Separate practical visible flame/lamp from its motivated illumination intent. Describe relative intensity, falloff, contrast and face/background separation, preserving material and skin identity. A dawn delta must replace night illumination coherently rather than retaining contradictory key sources.

Develop light quality as well as source direction. Relate the effective source's
extent, any motivated diffusion or reflected contribution, and nearby absorbing
surfaces to the transition across face, neck, clothes and room. A small visible
practical does not explain a broad soft face light by itself. Use established
surfaces; do not invent a new window to justify a preferred effect. Choose where
highlights broaden or stay small, where midtones turn into shadow, and which
shadow planes remain distinguishable. Sweat or polished wood can retain localized
reflection without making the whole surface bright. Softness is neither blur nor
equal fill; a hard source can also carry rich tonal transitions. Choose according
to the encounter, not a universal cinematic-light recipe. Judge these relationships
in the output, separately from whether lamps and named colors are present.

Use dusk, night and dawn as changing relations between available sources and
people's activity, not as ready-made emotional filters. At dusk, direct sun and
cool sky are different sources; do not invent sunset entering a window on the
wrong wall. At night, name the source that lets the required action remain
readable. Let dawn develop through sky level, shadow separation and declining
practical dominance, with faces and materials retaining their identity. Check
the current Scene time and the neighboring transition; a palette request alone
does not rewrite chronology or require every scene to become darker.

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

## Still live-action professional knowledge

In the STILL/LIVE_ACTION profile, keep visible/implied source, motivation, direction/softness, relative intensity, contrast and falloff as independent decisions under the existing keys. `day_night_continuity` supplies current time. Light reveals authored skin/material; it does not supply skin identity, scars or a fixed facial highlight. Contact shadows are conditional on light and visibility, not compulsory darkness under every contact. No automatic rim, bloom, fill or imperfection recipe. Approved intent leaves alone are projected; reasons and observation questions remain internal.

Read [mapping and evidence profile](../../docs/still-professional-mapping.md) when preparing these still records. Knowledge remains LOCAL_EXPERIMENTAL until scoped A5 media evidence.

## Restoring a baseline from a different viewpoint

Keep the approved scene source design distinct from an observed frame that
demonstrates it and from a later frame that deviates. In a new view, retain source
positions and relationships in the room, then derive their effect on the actor's
turned face, working hands, reflective objects and visible background. Screen-left
illumination need not remain screen-left after a camera reversal. Preserve the
Director's encounter-specific visibility and the accepted soft/hard transitions;
do not freeze one face exposure or suppress a justified dramatic change.

A scoped LOOK input does not physically remove the illumination in other image
inputs. If a current-state reference competes with the scene baseline, weigh its
necessary state proof against that conflict with Reference Strategy. Record the
choice and the actual output question; successful Prompt transmission is not
proof that the model separated light from identity, material or pose.

Compare the selected accepted baseline's face/material illumination and background
separation, not merely its visible lamp colors. Map the motivated source to the
new view's face side, working hands and background; name the allowed window/door
contribution through the relevant action stages. Preserve justified variation
without replacing a baseline with a generic warm/cool filter.

Check whether selected image bytes visibly compete with the target illumination.
Reference exclusions and complete field projection do not remove those cues. With
Reference Strategy, justify whether scoped baseline evidence or a different input
is needed; do not automatically add images. Keep transmission, executable source
relations and actual light matching as separate review conclusions.


## Optional film-craft application

Use [expression-led case reading](../director/references/film-practice.md) when it expands the current creative question. Translate light into world-space source positions, height, extent, softness, reflection and control; test changing camera/actor relations. Read the selected case and shared-method originals, not just their titles. Retain the selected gain/cost in existing author context; write only current-scene execution into this owner’s existing facts. No lookup quota or automatic adoption.
