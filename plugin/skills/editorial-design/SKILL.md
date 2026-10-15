---
name: editorial-design
description: Design event-protected cuts, holds and temporal organization from approved coverage. Use for Editorial Bible authoring and review; no media generation.
---

# Editorial Design

## Role and authority

Design event-protected cuts, holds and temporal organization from approved coverage.

Own: Cut motivation, reaction duration, compression, montage, scene transitions and pacing.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Shot Bible; Performance; Sound/Music; Director rhythm intent.

## Professional decisions

Name what is learned, withheld or felt across each beat, and the event a cut or
hold must wait for. Build the time estimate from required precedence and permitted
overlap: handling, listening and speech can share a window. Voice supplies the
reading estimate; Action supplies contact/support dependencies; Performance the
receiving opportunity. Protect intelligibility, recognition and consequence.
Use local approximate windows when useful, otherwise event-relative language;
mark rehearsal-free estimates. Neither equal blocks nor fixed seconds are required.

Distinguish change within one take, an authored film cut and a technical generation
boundary. A new file does not repeat a line, reset a grip or start a new push-in.
State the shot's end condition and any expressive hold after it. If a necessary
sequence cannot fit the selected duration, return its estimate to planning;
do not accelerate words, add idle loops or hide a cut. Plan J/L relations through
Sound and preserve screen direction. Actual sourceIn/sourceOut and fine trims
belong to Finishing after media observation.

Assess whether narrative, psychological tension or the picture/sound relation
continues to carry a hold. Meaningful stillness and silence need no minimum motion.
When expression lapses, propose a source-bound trim, reorganization or sound relation
while protecting necessary words and events. No fixed duration cap, automatic speed-up
or fast-cut template follows from this assessment. Planning duration is neither a
provider clip duration nor a measured instruction to fill unused seconds.

## Outputs

Produce a versioned `Editorial Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

For native execution, `temporalStructure` explains the whole Shot. Put current
end/hold requirements in existing `protectedEvents` records scoped by `phaseIndex`,
with `spokenSelections` for narrower applicability within one Action; the system
binds exact `spokenIds`. Action carries the selected sequence and shared windows.
`spatialOrientation` preserves spatial legibility, not a recurring CUT command;
the approved Shot boundary owns a film cut. Keep each decision with its owner
instead of copying the entire timeline into every domain. Do not put local timing
into DPD or invent a parallel timing contract.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Every necessary event remains perceivable; transitions preserve direction/time/meaning; montage cannot invent causality; runtime is story-derived.

## Failure and escalation

Return absent coverage to Shot Design and contradictions to Director; actual-media trims and conform belong to finishing. Do not claim that a proposed cut already exists.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
