---
name: look-continuity
description: Plan hair, makeup, fatigue, dirt and injury progression across scenes. Use for Look Continuity Bible authoring and review; no media generation.
---

# Hair Makeup and Injury

## Role and authority

Plan hair, makeup, fatigue, dirt and injury progression across scenes.

Own: Scene grooming, facial wear, blood/wounds and visible physiological progression.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Character Art; Performance; approved action and Costume states; continuity ledger input.

## Professional decisions

Separate persistent hair/beard identity from loosened strands, sweat, dust, wetness and makeup states. Localize each wound and its visible consequences without inventing a medical diagnosis. Track what accumulates, dries, is wiped, becomes mud or remains hidden by costume. Fatigue can alter skin and breath without changing facial identity. Specify from/until bounds and changed_by events for every meaningful delta.

## Outputs

Produce a versioned `Look Continuity Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

No wound or grime disappears at a cut; injury does not change sides; makeup supports readable performance without exaggerated gore.

## Failure and escalation

Return new injury events to screenplay/action owners, stable face changes to Character Art and impossible physical demands to Performance/Action; do not fabricate treatment.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.

## Medium-first fact handoff

Author structured, source-pinned facts and artistic intent, not provider prompt prose.
Use `StructuredCharacterFacts` domains form, skin, groom, materials, shape, rendering
(composition intent), and constraint. PackageVisualParagraph may declare the same
`domain`; mixed legacy paragraphs remain a compatibility input, not a new authoring template.
Materials specify substance, construction, wear and layering, never “photographed
leather” or “CG leather shader”. Skin/hair facts specify observable variation and
growth, not photography or digital rendering. Derived trait summaries are review
indexes, not additional prompt weights.

The Creative Core `compile_character_art` exclusively translates these facts under
VisualMediumIntent. Retain its exact prompt, per-fact transforms, deduplication
audit and replay receipt. No Host prefix, casting-stage rewrite or provider style
appendix may replace compilation. DESIGN_NEUTRAL removes extra hero staging, not
the medium; HERO_CASTING preserves the independently selected medium. Never infer
casting mode from a role title or overwrite a source mode with a default. Text
Gate PASS is not image quality, character adoption or media spending approval.

## Still live-action professional knowledge

For opt-in STILL/LIVE_ACTION, `skin_condition`, fatigue, dirt/blood/wounds and current grooming describe the current shot state. Do not rewrite CharacterAsset baseline complexion, hairline, age or marks. A newly lasting scar needs the asset owner's approved stage revision; fatigue does not authorize rejuvenation or a new age. Never add universal redness, sweat, wrinkles or dirt to make a face real. Keep makeup effects distinct from geometry; their source-pinned leaves map to visible_condition.

Read [mapping and evidence profile](../../docs/still-professional-mapping.md) when preparing these still records. Knowledge remains LOCAL_EXPERIMENTAL until scoped A5 media evidence.
