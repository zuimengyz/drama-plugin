---
name: voice-direction
description: Direct delivery of approved exact dialogue against performance and listener context. Use for Voice Bible authoring and review; no media generation.
---

# Voice Direction

## Role and authority

Direct delivery of approved exact dialogue against performance and listener context.

Own: Pace, breath, pause, emphasis, restraint, interruption/overlap and vocal effort.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Dialogue Bible; Performance DPD and Director intent; Blocking/listener distance; stable voice identity if available.

## Professional decisions

For each line identify whom it acts upon, spatial reach, attack, articulation, emphasis, pause function, release and after-line closure. High internal pressure need not become loudness; close address need not be whisper. Bound breath and intensity to physical load and injury. Preserve explicit overlap as an unresolved execution demand when unsupported; never convert it to invented sequential speech.

Distinguish continuing speech, a playable listening silence and an empty wait.
Specify what a pause receives or withholds and what releases the next phrase;
one shared event must not acquire separate Voice and Editorial pauses. Give Sound
the line's entry/release and protected phrase, allowing speech over ongoing work
when approved. Reading estimates inform local windows, not measured lip-sync or
mandatory gaps. In native `audio_events` use the selected line's existing delivery
leaves; preserve its exact text once. Retrospective voice-over remains separate
from the visible person's mouth and task.

## Outputs

Produce a versioned `Voice Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

All exact line IDs, words and speakers survive; recipient resolves; delivery changes have dramatic causes; native performance reuse remains possible.

Read each important entry against the current speaker's received event and the
partner's listening task, rather than copying one generic turn-taking instruction
across all lines. Share its release with Performance/Action/Editorial: receiving
may occur during speech, and a sourced non-response need not create a new gap.
Check that an indicated third person does not silently become the vocal addressee,
and that pressure in the common DPD has not become an independently invented vocal
emotion. Use the cross-owner handoff checks in the
[received-action and attention review](../dramatic-performance-direction/references/received-action-review.md)
when the delivery depends on a reaction or attention transfer.

## Failure and escalation

Return wording to Dialogue and psychology to Performance; missing identity to voice-identity. Do not select a TTS model, synthesize or replace accepted native sound.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.

## Character Package ownership

Consume dialogueVoice and performance as read-only identity; direct delivery of exact words. TTS provider/voice selection is implementation, not language personality.

Use the unified read-only `CharacterRepository.resolve_character_package` contract in [Character External Driver](../../docs/character-external-driver.md). Pin characterPackageRef, characterPackageVersion and checksum. Never create or overwrite Character Core in this Skill. Missing or stale packages return to the driver; model memory and old chat are not assets. DESIGN_REVIEW access does not authorize casting or production.
