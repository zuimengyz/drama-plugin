---
name: character-external-driver
description: After screenplay approval, design distinct characters from current sources and persist portable versioned Character Packages in an external repository. Use for character identity authorship, roster decisions and authorized package revision; no media generation.
---

# Character External Driver

Skill knows how to create a character. Host creates the character. Repository remembers the character.
Director decides which side of the character to show. Production Skills execute the character. Provider only renders the request.

Read [package contract and ownership](../../docs/character-external-driver.md).
This Skill owns WHO IS THIS CHARACTER after screenplay approval. It consolidates approved Character Bible meaning without silently rewriting screenplay facts. It contains methods, never a project's character prompts.

## Current source and roster

Read CURRENT_APPROVED_WORK through `work.get_work`, its explicit revision and pinned screenplay/script through `script.get_script` or the authorized local source. Verify bytes against the Work authority. Current explicit approval outranks a preserved historical file heading, but report the distinction. Missing authority, hash disagreement or ambiguity blocks design. Never substitute old lineage, fixtures or remembered cast lists.

Inventory every actual scene's participants, speakers, action identities and groups. Use `characters.screenplay.approved_screenplay` for a raw inventory, then Host review for aliases and implicit action roles. Retain scene/line evidence and a decision for each entry. Classify PRIMARY_CHARACTER, SUPPORTING_CHARACTER, RECURRING_CHARACTER, ROLE_ARCHETYPE_ONLY or BACKGROUND_GROUP. Decide dedicatedPackageRequired explicitly from frequency, dramatic importance, independent personality, key performance, visual continuity, action/voice identity and historical significance. A background label is not automatically an individual; recurring nonhuman identities can return to Animal Design.

## Author meaning before projection

For each dedicated role explain historical/dramatic identity, life stage, social position and self-image; desire, fear, belief, contradiction, pressure and decision pattern; the particular tragic or comic contradiction. Separate attested behavior, inference, authorial design and uncertainty. Do not substitute adjectives or scores for reasoning.

Ask: if the name is hidden, why is this person not a similar person? Compare at least two same-archetype alternatives, identify concrete choices that distinguish them, and record source basis. Comparators are analytical contrasts, never copied faces, actors, clothing, franchise designs or IP. Preserve a literary authorialStatement alongside structured fields. Unresolved details remain unresolved.

## Portable asset authoring

Use `characters.authoring.create_character_version` with explicit CharacterDesignAuthorization identifying the user/workflow directive, current Work and revision, allowed refs and directive hash. Write only to the configured external repository. No downstream Skill may call this writer. Changes create a new version; do not overwrite a locked version or claim user approval from technical validation. First designs are DRAFT.

Author all eleven required files in the contract. Core is cross-route identity, not camera/body/material directions. Visual routes are separately authored envelopes; missing routes fail without fallback. Character-specific anti-drift applies to this character only. Action signature cannot add events, kills, powers or outcomes; performance includes listening, silence and pressure, not just neutral/angry/sad. Dialogue voice is language personality, never a TTS ID. Relationships identify both surface and internal dynamics. Record provenance, source bytes, license status, authorship and unresolved rights; no credentials or signed URLs. Do not presume all packages are free or locally authored.

Only authorized package authors revise character meaning. Character Art designs its visual realization; Casting evaluates candidates against it. Director selects a facet for the scene, Action choreographs script facts using its signature, Dialogue authors words under its language personality, and TTS realizes audio. Return identity conflicts here; never repair identity in a provider prompt.

## Review and stop

Read back every package through CharacterRepository, verify exact ref/version/checksum and source files. Present roster, dedication rationale, literary identity, route scope, uncertainties and draft status. A package load is not approval. Prompts are disposable task projections, not character truth. Memory != Character Repository: prove recovery from screenplay plus repository in a fresh process. Stop at the requested design review gate. This Skill never generates images, casting media, video or audio.

For scoped read-only corroboration use `episode.get_episode`, `scene.get_scene`, `asset.get_asset` and `media.get_media`. These reads do not authorize media generation or adoption.
