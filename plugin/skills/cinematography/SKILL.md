---
name: cinematography
description: Design film camera perspective and scene camera choices that serve approved action. Use for Camera Bible authoring and review; no media generation.
---

# Cinematography

## Role and authority

Design film camera perspective and scene camera choices that serve approved action.

Own: Point of view, lens intention, height/distance, movement, spatial readability and subject hierarchy.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Director Vision; Layout; Blocking; Performance; Action and Crowd Bibles.

## Professional decisions

Choose the information and relationship the audience must perceive, then the
view. A wide view can disclose geography or isolation; a medium view can keep
hands and partners together; a close view selects a reaction or detail while
withholding space. Compare what each gains and loses, rather than cycling sizes.
Height, angle, distance and depth work together: low does not automatically mean
powerful. Motivate movement by a discovery or changing relation; a fixed view may
let the action supply it. Protect the partner's unfinished beat.

Simultaneous visibility is not simultaneous understanding. Decide which people
or actions must coexist in the frame, then organize discovery through depth,
focus, occlusion, light/color contrast and action timing with their owners. Deep
focus can preserve competing relations; shallow focus can select attention while
withholding another plane. Neither guarantees the viewer's attention. Motivate a
focus change by an authored action or attention event; stable focus and a fixed
frame may let the viewer discover the relation without a new cut or story turn.

Distinguish the relevant optical choices: camera position/distance changes
perspective; focal length changes field of view from that position. A dolly
changes viewpoint, a zoom changes framing; coordinated dolly/zoom can preserve
subject size while changing spatial relations. Viewing position, tilt/pan/roll
and a diagonal arrangement of subjects are different choices; a diagonal line
does not require a Dutch angle. Lens tilt changes the focus-plane relation and
shift changes framing; neither means generic blur. Exposure duration, capture
frame rate and playback speed have different effects on motion rendering.
Use these distinctions for an observable intention, without numeric recipes or
promising exact physical optical simulation in generated footage.

For alternate views, locate each camera against the same landmarks and action
axis; preserve actor facing, eyeline targets and travel vectors in world space
before checking their screen directions. A motivated axis crossing can use a
visible crossing, neutral view or spatial re-establishment; state how the audience
reorients. Reframing is not permission to relocate actors or mirror the set.

Check the critical contact and its consequence from the proposed view, including
actor/object occlusion at intervening poses. Framing four faces does not by itself
make a tiny ink drop readable. State which relation must be seen directly and
which can be understood through a continuous consequence; flag unresolved detail
scale instead of promising visibility. Check a move's whole path and stopping
frame against the same action and listener task. Request a scoped staging or
coverage alternative when needed; do not move a wall or require a close-up solely
to certify every mechanical detail.

For serial segments, bind `movement.phaseDirections` to Action's final units:
inherited view, CONTINUE/START/CHANGE/STOP/HOLD, trigger, trajectory, extent and
end state. Tie start and stop to the same action/phrase and estimated local timing
as Editorial, distinguishing estimates from measured footage. Whole-scene times
cannot be reused as segment-local seconds. Keep preceding/following events as
background; `movement.policy` is whole-shot intent when phase decisions exist.
A file boundary is never a new dramatic trigger. An exact approved
`CameraExecutionDirection` can bind this elaboration without replacing Canon.

## Outputs

Produce a versioned `Camera Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

For the native handoff, put the chosen viewing position, contact sightline and
occlusion conditions in `cameraPosition`, `height`, `lensIntention` or the current
`movement` decision. `continuityInterpretation` explains the reasoning but is not
an execution field. Preserve a concise usable decision in the former fields,
without copying the whole explanation. Align `phaseDirections.phaseIndex` with
the final Action execution units, not individual actors' beats or discarded
substeps. A trigger and its visible consequence must belong to that same unit.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Camera can occupy its position; action cause and consequence remain readable; visual hierarchy serves story rather than constant motion.

## Failure and escalation

Return obstructed geography to Layout/Environment and insufficient coverage to Shot Design; do not change acting to justify a camera move or let model limits set film grammar.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.

## Route-owned expression

Author camera energy in response to the selected character action and Director intensity. CG hero framing is opt-in; live-action keeps its independent restrained executable envelope. Camera never invents physical action. Read [expression route contract](../../docs/expression-route-contract.md) when using character or action expression profiles.

## Still live-action professional knowledge

For the opt-in STILL/LIVE_ACTION profile, author one visible `intent` per existing field, with separate reason/constraints/criteria. Decide the required subjects, hands, contacts and landmarks in `spatial_readability` before `shot_scale_philosophy`. Keep observer relation (`camera_point_of_view`), height, distance and optical-axis/depth relation (`perspective`) distinct: a low camera can remain level. `subject_hierarchy` owns framing and attention; symmetry and centered framing are valid choices. `lens_intention.intent` may be an ordered list of spatial effect, current focus plane and permitted softness decisions. Do not invent millimeters from genre or promise exact optical simulation. Resolve distance/lens/readability conflicts against Layout, not by moving actors. Replace generic cinematic praise with observable choices at the authoring source; the mapper cannot polish them. No focus pulls or camera-motion facts enter this still profile.

Read [mapping and evidence profile](../../docs/still-professional-mapping.md) when preparing these still records. Knowledge remains LOCAL_EXPERIMENTAL until scoped A5 media evidence.
