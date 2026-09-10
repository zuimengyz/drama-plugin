---
name: video-model-selection
description: Select a video model, input mode and execution path for an approved Shot before preparing new inputs. Compare verified capability, task quality evidence and complete incremental cost; leave generation and adoption to production.
---

# Video Model Selection

For new Shot authoring, freeze cinematic-direction's source-pinned
`CinematicShotSpec` before selection. Consume its structured Execution Requirements,
Reference Requirements and `CINEMATIC_DIRECTION_FROZEN` through the
[director handoff](../../docs/cinematic-direction-contract.md). Narrative → director
execution → frozen direction → this selection → input preparation → production is
the freeze boundary. Existing adopted and archived routes retain their original
identity; this is not permission to restage them or enlarge reference limits.

Read `shot.get_shot`, `scene.get_scene`, `media.get_media` and `media.resolve_media` only when the approved context or stable input facts are missing. Keep alternatives in Agent Run Context. For an authorized persistent production task, save the reviewed route and input duties through existing Work open metadata; do not create route entities or a parallel Skill. Select after narrative, performance and sound requirements are settled, before paying for input images. Return the decision to the calling production workflow; selection itself never submits generation, imports Media or adopts a result.

Freeze Work/Scene/Shot and video target, narrative duration, entry/exit state, actor/action ownership, camera, canonical dialogue rendition and speakers, required sound controls, prop/costume state, adjacent-shot continuity and reviewed input versions. Never shorten required acting, remove dialogue, exchange actions or add external speech to fit a cheaper candidate. An unresolved rendition or required voice control blocks that path only.

Use creative requirements as admission gates, task-specific quality thresholds, then complete incremental cost among eligible routes. Existing-image compatibility is a reuse benefit or a priced conversion/new-input choice, never the first veto for a new work. Missing endpoints or a different image ratio cannot reject an entire model when an inspected mode and bounded input preparation can meet the requirement. Translate “keyframes” into first-frame conditioning, independent start/end, subject/style references or actual timed image constraints. Multiple references do not prove endpoints or intermediate timing; independent capabilities do not prove their combination. Preserve the project contract: image preparation has at most three stable references; video accepts exactly one stable image, or one same-target start/end pair, without mixing. Do not enlarge this contract from a provider's higher limit.

Inspect a small relevant candidate set through the Host. Separate official model claims, current node/interface support, actual template exposure, project adaptation and project quality samples. A missing current path is not executable even if documentation exists. Host details belong in the adapter, not this core. Unknown nodes, uninspected nested graphs, hidden paid enhancement and additional generation stages must fail closed. Do not switch paid platforms or install local models.

Record quality evidence for identity/props, action/narrative, sound/performance and continuity, with applicable task conditions and sample count. Unmeasured quality is UNKNOWN; resolution and audio-track presence are not quality evidence. A new candidate with verified hard capabilities may receive LIMITED_TRIAL eligibility in the authorized budget; this never grants expansion. One passing sample proves only that result and its conditions. Consider a stable scene path and switching costs without making continuity a permanent veto.

Compare complete incremental cost: necessary new input assets + generation + reference charges + enabled enhancement/regeneration + bounded correction. Existing reviewed assets cost zero incrementally. Record unit, variant, parameters, price source, query time and unknown charges. Never estimate success probability without samples. Obtain a fresh conservative quote for the exact final request before each paid reservation. Unknown fees remain unresolved, not zero.

Use the [decision and execution contract](references/decision-contract.md) for structured qualification and the production handoff. Freeze candidate exclusions, chosen model/variant/mode/template/parameters, ordered references, graph and request fingerprints, quality evidence, risks, expiry, stage budget association, and fallback conditions. Any material change requires requalification and a fresh quote. Reuse compatible approved inputs; prepare only those the chosen mode actually needs.

Return NO_EXECUTABLE_CANDIDATE with specific missing capabilities when necessary. Complete read-only and offline work while authorization is absent. Ask once for a concrete stage budget after the production quote is ready. Account balance is not authorization. Preserve the same stage state through recovery, model and campaign changes; every artistic retry is a new paid attempt. Existing adopted AV is immutable and is not an external reference by default.

After production, backfill request/job/output/review/billing evidence. Keep technical validation, content review and user adoption separate. Unreliable playback or listening remains PENDING_REVIEW/UNKNOWN. Production owns safe recovery, Media import/readback and adoption permissions.


## Durable completion and recovery

For retained image, video, audio or derived AV, formal completion requires full
readback SHA-256/size, decodable media, correct business ownership and a queryable
stable business binding. A local path, upload name, returned ID or temporary URL
alone is PERSISTENCE_PENDING. Content PASS, user adoption and persistence are
independent; persistence must never rewrite an existing adoption decision.

The shared completion entry `complete_retained_media` implements import/reuse,
readback and binding. Visual attempts call it through `visual_preflight.py persist`;
role speech calls it before returning a production result; an explicit mux calls
it on the new output before formal delivery. Adopted native AV consumption uses
`prepare_bound_media(adopted=True)` to recover the selected original from its formal
business reference. It performs no dubbing, separation, mixing or remuxing.

After a successful generation, resume at import/readback/binding with the same
job, output hash and sourceRef. After an uncertain import, query the exact stable
source first; ambiguity, permission denial, hash conflict or unknown ownership
blocks completion. Retry transient reads with finite backoff and fresh resolve.
Never generate again to repair missing cache or persistence. Do not import
unneeded DEBUG/REJECTED files or invent an output that was never generated.

## Production route before images

For a new story, call `ProductionRoute` / `qualify_route` before any paid input.
Each planned input has a stable target duty, purpose, role, consumer targets,
preparation choice, specification, rationale and explicit cost key. It has no
placeholder Media ID. Compare 2–3 relevant routes; preserve fixed reference caps.
Include image preparation/conversion, each video, native or external audio,
references, enabled extra nodes and correction reserve. Unknown fees block a
complete cost claim. Report current cash separately from hypothetical series
amortization; do not invent a success probability for unknown quality.

The actual new-story Host entry is
`../shot-production/scripts/route_preflight.py`. Save the route on the new Work,
then initialize the existing visual stage only after explicit stage-wide monetary
authorization. Its Work-owned stage is canonical; local state and Excel are
rebuildable audit views. `check-input` and each reservation enforce the necessary
input duty and current route. `add-frame` materializes one input or video without
resetting the stage. After input review and full Media readback, seal the existing
video decision with actual input identities and the current exact graph quote.

Keep neighboring targets on the same qualified route/specification unless evidence
justifies a change. First produce the least input needed and one representative
video. Only a reviewed pass may unlock the adjacent target; a concrete failure
may spend the second video on a focused correction. UNKNOWN is not a retry trigger.
Model changes, technical recreation and content correction retain target identity,
all call events and shared stage exposure. Stop at the task's global video/image
limits; never count a multiple-generation workflow as one generation.

## Execution contract reconciliation

For cinematic-shot-v1 consume frozen direction, reference duties and source sound.
An unfulfilled REQUIRED reference is ineligible even for LIMITED_TRIAL. A route
may plan future inputs; a materialized request cannot claim they already exist.
Preparation remains capped at three references; video uses qualified zero-image
text mode, single image/reference or a same-target endpoint pair. Extra exposed
multimodal slots do not expand project authorization.

The Host's single semantic projection binds direction, canonical dialogue,
reference package, qualification, schema/template, duration, resolution and audio
policy to the existing request seal. Requalify on drift. Official interface plus
offline execution is not visual quality: UNKNOWN quality remains LIMITED_TRIAL,
and paid eligibility still requires complete current cost. Partial price metadata
is not a complete zero cost. Offline seals cannot reserve/submit; real production
keeps the formal Work stage, budget and billing history. No second selector.

See [the execution reconciliation contract](../../docs/video-execution-reconciliation.md) for current request sealing and reference/coverage checks.
