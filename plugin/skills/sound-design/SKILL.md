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

Follow the same event relations as Action, Performance and Voice. One person's
footsteps can cease while the other's continue; a held cup has no new set-down
impact. Scope a contact sound to its authorized cause instead of importing a
generic list of object noises. Keep explicitly authored offscreen or asynchronous
relations, with their source and listening perspective. A visual pause does not
silence the room or stop another speaker. Consume the current Voice decision for
each spoken event; merely loading Sound does not create that decision.

Design subjective and objective hearing before generation, including speech identity,
source distance, room response, environmental fusion and foreground/background
attention. Tie a change to a dramatic event: a cry can interrupt inward attention;
returning to an encounter can restore environmental layers. Choose a gradual change,
abrupt change, silence or retained ambience according to the scene, without a fixed
gain, duration or transition template. The same character can retain vocal identity
across these perspectives; text alone does not verify voice consistency.

For the native author contract, `audio_events` selects the canonical utterance
with `spokenSelection`; the system binds IDs and speaker. Use existing delivery
modes and performance/space/attention/continuity leaves for phrase-relative or
estimated local timing. Do not invent `window_ms`. Put a segment's contact sound
in existing `contactTiedSound` records with `phaseIndex` and `design`, not one
unscoped whole-shot string. Within one Action, use existing `spokenSelections`
to bind narrower applicability; the system resolves these to `spokenIds` for
selection, not a new time track. A deliberately continuous contact names all
applicable utterances/units; persistent ambience stays shared. Keep
`dialogueAndLegibility` and `orderingRules` to shared intelligibility: the selected
utterance's delivery leaves own its local pause and vocal entry. Silence can
withhold a layer without deleting the room. Keep a prelap or offscreen sound tied
to its authored listening event rather than forcing visual synchrony. Verify these
relations in the final request; native joint AV does not prove acoustic success,
and independent TTS remains a separately authorized route.

## Outputs

When Editorial selects source ranges, distinguish visual exit from acoustic exit.
A room, breath or source-music phrase may bridge a film cut; a technical file edge
does not motivate a fresh attack, silence or fade. Give Finishing the intended
listener perspective and causal relation, then conform against actual audio.
Do not prelap an unplayed instrument or coin impact merely to hide a seam. With
mixed native tracks, a bridge also carries their speech and contact sounds: choose
a supported donor interval and disclose competing events rather than call it an
isolated ambience stem. If hearing is unavailable, a rendered experiment remains
UNKNOWN; waveform continuity alone cannot establish musical or dramatic success.

Produce a versioned `Sound Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Sound cannot precede its cause unintentionally; acoustics match space; source continuity survives cuts; no invented battlefield event conveyed by sound.

## Failure and escalation

Return vocal performance to diegetic-vocal/Voice and score to Music. Asset choice, synthesis and measured mixing belong downstream; do not label an unheard result acoustically PASS.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.


## Optional film-craft application

Use [expression-led case reading](../director/references/film-practice.md) when it expands the current creative question. Use source location, offscreen persistence and listening to organize attention; do not make every camera change a sound reset. Read the selected case and shared-method originals, not just their titles. Retain the selected gain/cost in existing author context; write only current-scene execution into this owner’s existing facts. No lookup quota or automatic adoption.
