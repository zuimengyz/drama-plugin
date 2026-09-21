---
name: costume-design
description: Design clothing and armor identity and its causal scene variants. Use for Costume Bible authoring and review; no media generation.
---

# Costume Design

## Role and authority

Design clothing and armor identity and its causal scene variants.

Own: Garment/armor construction intent, rank distinction, layers, materials, wear and costume state transitions.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Character Art; Character Bible; historical boundary; Director Vision; approved story actions and continuity input.

## Professional decisions

Distinguish faction grammar from documented uniform regulations. Explain layer relationships, armor articulation, material response and occupational wear in relation to movement. Each scene/stage variant declares predecessor, cause, retained damage and what may change. Repairs must have a sourced action or a supported interval; a time-of-day cut does not repair armor. Saddle/weapon designs are referenced, not re-authored.

## Outputs

Produce a versioned `Costume Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

Rank and role remain readable; hands and joints can perform required actions; broken pieces never reset without an event; no replacement costume for aesthetic convenience.

## Failure and escalation

Route injury physiology to Look, physical feasibility to Action, new outfit events to screenwriting. An unresolved repair stays damaged or UNKNOWN, never implicitly pristine.

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
