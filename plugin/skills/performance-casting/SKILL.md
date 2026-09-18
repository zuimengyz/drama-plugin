---
name: performance-casting
description: Search and test screen-role candidates through role-specific face, relative-scale and performance proofs, then present a source-pinned shortlist for user selection. Use when casting suitability or performance range is unresolved; production-design retains stable appearance authority.
---

# Performance Casting

ROLE SALIENCE > AESTHETIC OPTIMIZATION. Modern screen appeal should amplify the
role's defining features. If prettier conflicts with more recognizably this role,
preserve the role. Aesthetic optimization may refine defining discriminants but
must never reduce their salience. Read [role salience and references](references/role-salience.md)
when reconciling a search or compiling an archetypal role.

Choose a person who can carry the scene, not a portrait whose styling supplies the
missing role. Read actual character/story/scene/director sources, current visual
specification, stylization policy, user preferences, previous search and approval
status. Preserve their fingerprints. Candidate scene interpretations can guide a
new search without rewriting adopted story or references.

Extract a RoleArchetypeProfile with the desired audience impression, its visible
carriers, body relationships, key scene tasks and failure modes. Presence dimensions
are authored for the role: moral insistence, comic uncertainty, maternal calm,
quiet threat and intellectual force need different faces and states. No gender,
age, ethnicity, beauty level, large body, aggression or tragedy is a global default.
Appearance expresses a fictional interpretation, not a scientific personality
inference. Static evidence can suggest range; it cannot establish acting ability.

Before a new search, read [character excavation](references/character-excavation.md).
Connect personality with identity, rank/occupation, social position, historical or
cultural environment and other people's treatment. Derive watchability, the shared
root of strength and limitation, fate contrast, counter-stereotype, performance range
and concrete visual choices. All ten questions must change a casting decision; short
answers or a reason why a contrast is inapplicable are preferable to generic essays.
Keep source-supported facts, project interpretation and casting implications separate.
`IDENTITY_LOST` and `ERA_CONTEXT_LOST` must both PASS: remove the name and check whether
occupation/status and situated values remain recognizable. Missing, failed or stale
excavation blocks new media generation. Legacy profiles remain readable, not spend-ready.

Casting does not impose charm. It discovers the character's watchability.
DO NOT CAST THE ENDING INTO THE FACE: betrayal need not look deceitful, sacrifice
saintly, or tragedy melancholy. Seek the capacity to travel the arc. Regal presence
means learned authority, bodily confidence, spatial rights and others' response;
never facial divination, a fixed nose, or an assumption that kindness erases rank.

Read [proof design and handoff](references/proofs.md) to choose a face-first,
body-first, performance-first or reduced route. Explain omitted stages. For every
stage, name the one principal question and concrete pass observations before
spending. Split conflicting questions instead of packing face, height, acting,
armor and heroism into one full-body generation. Search archetypes through genuinely
different visible structures; adjectives and seeds alone do not establish diversity.

Before another search, read [appeal, discriminants and complete proofs](references/visual-discriminants.md).
Choose the role's AudienceAppealMode: being liked and commanding respect are different
possible attractions. Neither youth, refinement nor intimidation is a universal default.
SEARCH tests contrasting authored structures and permits strong individuality or failure;
SELECTION assesses role-specific appeal, screen suitability and drift from actual evidence.
Use `VisualCastingPlan` and the CLI `compile`/`check-projection` modes to trace source
choices into submitted text. Do not replace the compiled prompt with a new hand summary.
The compiler preserves authored choices; it does not infer facial anatomy from psychology.
Story-dependent claims cannot be face criteria. Calibration outputs are diagnostic only.
For new candidate selection pass `--visual-plan`: its appeal finding and complete proof
scope supplement the existing selection gate. Key social identities require SOCIAL;
a COMPLETE candidate covers FACE, SCALE and SOCIAL, with performance when the role needs it.
Legacy profiles/reviews remain readable; they do not prove the new proof duties fulfilled.

Face search isolates face and baseline presence with equal chest-up framing/light.
A scale claim requires shared-plane anchors and visible contact with the same ground;
one unanchored portrait cannot prove exceptional height. A performance comparison
pins the selected identity and test conditions, changes a role-specific playable
state, and checks what stayed constant. Keep costume a controlled variable until
casting selection; costume approval is downstream.

For roles whose identity depends on social relations, schedule SOCIAL after relevant
body proof and before performance comparison. Show peers or differently ranked people
sharing real space: attention, spacing and who may decide reveal position. This can
mean sovereign distance, local professional authority, or ordinary group membership;
the subject need not be the center or highest power. Explain omission for other roles.

Use `contracts/performance_casting.py` and `performance_casting.stage_brief` for
provider-neutral, JSON-schema-exportable handoffs. The [local CLI](scripts/casting.py)
validates profiles, emits stage briefs, checks prior reviews/budget and presents the
user-selection gate. It never generates, creates entities or approves candidates.
Host/MCP/harness projects each brief into a currently verified provider route and
compares the executed request with the brief before reporting adherence.

Review actual media separately for attractiveness, distinctiveness, role/presence
fit, cultural fit, drift and performance hints. Use PASS / SHORTLIST / PARTIAL /
REJECT with visible reasons, not totals. Do not infer quality from contract validity.
Record `conditions_preserved` from the actual image: identical requests do not prove
identical light, framing or expression. This finding must PASS before any stage can
advance. A harder shadow or a frown cannot substitute for the requested presence.
Face SHORTLIST can advance within the declared count; scale and performance require
PASS on their essential observations. Failed prior proof cannot be skipped merely
to complete the pipeline. A reduced route requires a reason in the original profile,
not an after-failure waiver. Stop the search under the user's count/budget rules;
artistic dislike is not a technical retry.

For authorized generation, use the qualified Host visual execution route and durable
media completion. Read live capabilities and quotes; unknown balance remains unknown.
Keep owned task IDs, exact identity inputs, sourceRef and full-byte hashes. Import
successful outputs with media.import_media, resolve/read back, and retain candidates
as PENDING_USER_REVIEW without replacing formal Character references or adoption.
Present matched contact sheets and originals first. Stage readiness and Host PASS
are never user approval. Existing ProductionDesignFreeze remains the only downstream
production gate; report missing approval rather than manufacturing it.

For source reads use `work.get_work`, `script.get_script`, `scene.get_scene`,
`asset.get_asset`, `asset.search_assets`, `asset.list_assets`, `media.get_media`
and `media.list_media`. Retained physical outputs use `media.import_media` followed
by `media.resolve_media` and full-byte readback. Do not use source/adoption writes
to persist the local casting profile. The tool catalog remains unchanged.

For an explicit visual-medium route, read [route-aware casting](references/visual-routes.md). The route is separate from the face-first/body-first proof order; an omitted route sidecar preserves a frozen legacy brief without asserting its medium. New route-specific design requires an explicit Work route.
