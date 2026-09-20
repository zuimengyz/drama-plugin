---
name: diegetic-vocal
description: Design source singing, chanting, ritual and historical verse performance. Use for Vocal Performance Bible authoring and review; no media generation.
---

# Diegetic and Historical Vocal

## Role and authority

Design source singing, chanting, ritual and historical verse performance.

Own: Vocal mode, participation, delivery structure and historical vocal uncertainty; no score ownership.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Exact approved words or non-lexical source behavior; Performance; Voice Direction/Identity; historical boundary.

## Professional decisions

Distinguish spoken verse, recitative, sung melody, shared response and nonverbal vocal sound. Preserve exact lyrics where authored, identify who participates and who can hear, and keep missing melody/composition UNRESOLVED. A surviving text does not prove its ancient tune. Declare whether performance is unaccompanied and what must remain uncertain; silence or a restrained mode can be a deliberate choice.

## Outputs

Produce a versioned `Vocal Performance Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

No invented historical melody, added duet words or automatic choir; vocal events remain diegetic and source-bound; unresolved composition is not production-ready.

## Failure and escalation

Return missing text to Dialogue and authenticity claims to Historical Research. Music Direction owns nondiegetic score; unsupported vocal execution blocks the route, not a fallback to plain TTS.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
