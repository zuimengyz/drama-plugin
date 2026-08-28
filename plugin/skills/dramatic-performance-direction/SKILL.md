---
name: dramatic-performance-direction
description: Build a replayable, provider- and modality-neutral Scene/Beat/Line performance direction from an approved dramatic scene; do not generate media or provider controls.
---

# Dramatic Performance Direction

Build one compact `dpd-v1` direction for an approved Scene before modality-specific production. Read the [DPD Core contract](../../docs/dpd-core-contract.md) before composing it.

Load only the context needed to explain the current dramatic action. Start with `scene.get_scene`; use `episode.get_episode`, `script.get_script`, and `work.get_work` only for unresolved dramatic purpose, stable speaker identity, relationship, hierarchy, or historical/social constraint. Use `context.build_context` only when these direct reads cannot supply a required parent relation. Do not retrieve history independently or copy whole Character profiles into the direction.

Create three sparse layers in temporary Agent state:

- Scene DPD: dramatic purpose, active conflict, power structure, public/private context, and only material climate, urgency, information, or social constraints.
- Beat DPD: current actor, target, objective, obstacle, tactic, authority/relationship position, internal activation, external control, and transition trigger.
- Line DPD: the canonical `spokenContentId` and speaker, this line's dramatic action, observable intent, continuity/change, and only genuine Beat overrides.

Compose `Scene → Beat → Line` with the typed Core. Missing and null fields inherit; v1 has no scalar-reset syntax. A supplied list replaces the parent list, and an empty list clears it. Line wins over Beat, Beat wins over Scene. Any mismatched Scene or Beat reference is invalid. Keep the resulting `DPDSnapshot` and fingerprint together so downstream work can replay the same decision without reinterpreting the whole script.

Use action and relationship language, not moral labels or a single emotion label. Keep internal activation distinct from external control: high activation may remain highly controlled. `speakerKey` references identity; it does not duplicate age, rank, biography, personality, or Voice Profile.

Do not add speech speed, pitch, loudness, pause milliseconds, breath, articulation, voice identity, provider prompt, model settings, camera, framing, gaze, posture, gesture, blocking, or physical motion. Those are projection concerns. Do not generate Audio/Visual Media, persist a new business entity, or invent a DPD-specific Tool.

Finish when the three contracts validate, the effective direction is materially playable and distinct from character identity, and the canonical fingerprint is recorded. If essential objective, target, relationship, or historical/social constraint is unsupported or contradictory, report the missing input instead of filling it with stereotype or provider detail.
