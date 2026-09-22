---
name: dialogue-design
description: Author or review exact spoken content, subtext and speaker/listener continuity. Use for Dialogue Bible authoring and review; no media generation.
---

# Dialogue Design

## Role and authority

Author or review exact spoken content, subtext and speaker/listener continuity.

Own: Canonical wording, speaker/listener identity, spoken meaning and historical register.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Character Bible; Scene Beat Bible; historical boundary; current SpokenContent IDs and approved wording.

## Professional decisions

Preserve exact text and stable speaker IDs during migration. For authorized new dialogue, make each turn a playable attempt on a listener: request, refusal, concealment, recognition or change in power. Information must alter behavior. Mark documentary quotation versus adaptation; historical register should be speakable rather than pseudo-archaic exposition. Silence is valid when action supplies the information.

## Outputs

Produce a versioned `Dialogue Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

No duplicated or lost canonical line; listener and line order resolve; quoted words retain their provenance; voice performance does not rewrite wording.

## Failure and escalation

Return causal defects to scene-development and historical doubts to adaptation-boundary. A production timing conflict requests coverage or upstream revision, never silent paraphrase.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.

## Character Package ownership

Consume dialogueVoice as language personality; author exact words only under screenplay authorization. Do not redefine personality or bind a TTS voice.

Use the unified read-only `CharacterRepository.resolve_character_package` contract in [Character External Driver](../../docs/character-external-driver.md). Pin characterPackageRef, characterPackageVersion and checksum. Never create or overwrite Character Core in this Skill. Missing or stale packages return to the driver; model memory and old chat are not assets. DESIGN_REVIEW access does not authorize casting or production.

## Production language adaptation

For a language-bound Literary Work, use `ProductionLanguageProfile` and the existing
performance rendition mechanism; see [production language](../../docs/production-language.md).
Consume approved screenplay meaning, original-language source dialogue, Character Dramaturgy,
relationship state and period/register in `SemanticDialogueIntent`. Produce a separately reviewed
`ProductionDialogueLine`; preserve honorifics, hesitation, repetition and self-correction.
Prefer original source dialogue over back-translation of review text. Meaning conflicts emit
`UPSTREAM_LOCALIZATION_CONFLICT`; do not rewrite upstream intent. Compile with
`compile_localization` against the pinned upstream context before requesting review.
