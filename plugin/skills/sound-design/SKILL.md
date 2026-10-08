---
name: sound-design
description: Build the physical and dramatic listening world through ambience, foley and silence. Use for Sound Bible authoring and review; no media generation.
---

# Sound Design

## Role and authority

Build the physical and dramatic listening world through ambience, foley and silence.

Own: Source sounds, acoustic space, distance, foreground/background attention and diegetic silence.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Environment physical spaces; Action/Crowd; Blocking; Dialogue/Voice; Director intent.

## Professional decisions

Locate each sound source and listener perspective. Relate footsteps, tack, weapons, water and cloth to contact events, with plausible distance and occlusion. Design persistent ambience across shot edges; a cut need not restart a wind or river bed. Distinguish physical silence, withheld attention and absent score. Important words and causal impacts remain legible without an indiscriminate sound layer.

Design subjective and objective hearing before generation, including speech identity,
source distance, room response, environmental fusion and foreground/background
attention. Tie a change to a dramatic event: a cry can interrupt inward attention;
returning to an encounter can restore environmental layers. Choose a gradual change,
abrupt change, silence or retained ambience according to the scene, without a fixed
gain, duration or transition template. The same character can retain vocal identity
across these perspectives; text alone does not verify voice consistency.

For the native source-to-reviewed-media path, reuse Sound `audio_events` with exact
`event_id` / `spoken_content_id` / `speaker_key`, existing delivery modes and concise
performance, space, attention and continuity leaves. Scope ambient/contact/silence
records to the current beat and, where one beat spans units, `phaseIndex`. Keep IDs,
evidence and review status internal. Production compiles only applicable decisions
through the model-specific adapter and verifies the final request. Native joint
audio/video remains the default when selected; independent TTS/redubbing is a separate
authorized route, not a Sound default. This handoff does not claim deterministic
provider control or acoustic success before hearing the actual output.

## Outputs

Produce a versioned `Sound Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Sound cannot precede its cause unintentionally; acoustics match space; source continuity survives cuts; no invented battlefield event conveyed by sound.

## Failure and escalation

Return vocal performance to diegetic-vocal/Voice and score to Music. Asset choice, synthesis and measured mixing belong downstream; do not label an unheard result acoustically PASS.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
