---
name: adaptation-boundary
description: Judge what a historical drama may infer or reconstruct from bounded evidence. Use for Adaptation Boundary Bible authoring and review; no media generation.
---

## Domain scope

This Skill owns historical evidence/reconstruction boundaries. Literary preservation and compression decisions belong to literary-adaptation; source facts to literary-source-analysis. Do not run historical reconstruction checks as global literary requirements. Both packages converge through ScreenplayInput; no competing literary decisions are kept here.



# Adaptation Boundary

## Role and authority

Judge what a historical drama may infer or reconstruct from bounded evidence.

Own: Evidence-use boundary and exclusion decisions; source facts remain Historical Research authority.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Historical Source Bible; Historical Entity Bible; proposed narrative choices.

## Professional decisions

Classify each consequential claim as DOCUMENTED, PLAUSIBLE_INFERENCE, DRAMATIC_RECONSTRUCTION, UNRESOLVED or EXCLUDED_WITH_REASON. Separate a person’s attested identity from presence at an event and from invented gestures. Retain dissenting sources and the reason an uncertainty matters to adaptation. An original person may act inside a documented event without receiving historical command authority.

## Outputs

Produce a versioned `Adaptation Boundary Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

No evidence upgrade without a new source adjudication; every exclusion has a reason; reconstructed specifics are identifiable.

## Failure and escalation

Return uncertain evidence to historical-research and meaning changes to screenwriting; do not settle uncertainty through confident visual prose.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.
