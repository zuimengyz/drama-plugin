---
name: video-model-selection
description: Select a video model, input mode and execution path for an approved Shot before preparing new inputs. Compare verified capability, task quality evidence and complete incremental cost; leave generation and adoption to production.
---

# Video Model Selection

## Role and authority

Qualify a production route against approved creative requirements. Fitness, verified capability, quality evidence and cost belong here; creative decisions remain upstream.

## Inputs and dependencies

Read the professional DirectorPackage, Asset Manifest, Reference Plan, Generation Clip Plan and current department/continuity refs. For actual execution consume the frozen CinematicShotSpec and existing approval/budget gates.

## Outputs

Return a Video Route Policy or source-pinned qualified route with explicit unresolved capabilities. A planning contract does not assert an implemented provider adapter.

## Forbidden authority

Do not change department content, canonical speech, action order or continuity to fit a route. Provider-specific controls stay in route, Prompt Compiler and adapter layers; no creative Bible changes merely because a provider changes.

## Quality gates

Before capability or cost comparison, read per-model `enabled` through the Host's model availability view (`video_provider.py models`). Only enabled models may enter selection. Skip `enabled=false` / `DISABLED` models in AUTO, PREFER, fallbacks and PIN; a disabled pinned model produces no executable candidate. Recheck before a new submission. Enabled does not override missing credentials, capabilities, continuity or budget. Do not switch a continuity-locked segment merely because its primary model was disabled; return for an authorized route revision. Existing submitted tasks may still be polled and retained.

Verify required inputs and capabilities, then quality evidence and full incremental cost. Missing evidence remains UNKNOWN. Route eligibility, authorization, observed media quality and adoption remain separate.

## Failure and escalation

Return unsupported demands to Director with the originating department identified. The department can propose an authorized creative revision; this selector cannot silently supply one. No viable route means NO_EXECUTABLE_CANDIDATE, not a fabricated request.


Model qualification and execution binding are separate facts. Retain all model
fit, quality, reference, duration, native-audio and cost decisions. Bind the
selected capability to an explicitly supported Host execution route; preserve
its backend/model/transport identity through compilation, sealing and invocation.
Missing capabilities block that route, never silently switch provider or transport.
The packaged MCP integration is one qualified implementation described in the
[Host adapter contract](../../docs/visual-provider-host-integration.md).
This Skill neither requires a particular GUI nor grants an unimplemented transport.
For new Shot authoring, freeze cinematic-direction's source-pinned
`CinematicShotSpec` before selection. Consume its structured Execution Requirements,
Reference Requirements and `CINEMATIC_DIRECTION_FROZEN` through the
[director handoff](../../docs/cinematic-direction-contract.md). Narrative → director
execution → frozen direction → this selection → input preparation → production is
the freeze boundary. Existing adopted and archived routes retain their original
identity; this is not permission to restage them or enlarge reference limits.

Read `shot.get_shot`, `scene.get_scene`, `media.get_media` and `media.resolve_media` only when the approved context or stable input facts are missing. Keep alternatives in Agent Run Context. For an authorized persistent production task, save the reviewed route and input duties through existing Work open metadata; do not create route entities or a parallel Skill. Select after narrative, performance and sound requirements are settled, before paying for input images. Return the decision to the calling production workflow; selection itself never submits generation, imports Media or adopts a result.

Freeze Work/Scene/Shot and video target, narrative duration, entry/exit state, actor/action ownership, camera, canonical dialogue rendition and speakers, required sound controls, prop/costume state, adjacent-shot continuity and reviewed input versions. Never shorten required acting, remove dialogue, exchange actions or add external speech to fit a cheaper candidate. An unresolved rendition or required voice control blocks that path only.

Use creative requirements as admission gates, task-specific quality thresholds, then complete incremental cost among eligible routes. Existing-image compatibility is a reuse benefit or a priced conversion/new-input choice, never the first veto for a new work. Missing endpoints or a different image ratio cannot reject an entire model when an inspected mode and bounded input preparation can meet the requirement. Translate “keyframes” into first-frame conditioning, independent start/end, subject/style references or actual timed image constraints. Multiple references do not prove endpoints or intermediate timing; independent capabilities do not prove their combination. Preserve the project contract: image preparation has at most three stable references; legacy Comfy video retains its inspected input limits. Official video uses the unified VideoRequest and the current registry combination limits, including qualified multimodal references. A larger vendor limit never permits omitting required canonical references.

Inspect a small relevant candidate set through the Host. Separate official model claims, current node/interface support, actual template exposure, project adaptation and project quality samples. A missing current path is not executable even if documentation exists. Host details belong in the adapter, not this core. Unknown nodes, uninspected nested graphs, hidden paid enhancement and additional generation stages must fail closed. Provider changes require the qualified route, continuity gate and existing budget authorization. Do not install local models.

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
placeholder Media ID. Compare 2–3 relevant routes; preserve each qualified input contract.
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
Image preparation remains capped at three references. Legacy Comfy video keeps its inspected modes; official video may consume the unified multimodal bundle after capability and continuity gates. Extra slots do not expand project authorization.

The Host's single semantic projection binds direction, canonical dialogue,
reference package, qualification, schema/template, duration, resolution and audio
policy to the existing request seal. Requalify on drift. Official interface plus
offline execution is not visual quality: UNKNOWN quality remains LIMITED_TRIAL,
and paid eligibility still requires complete current cost. Partial price metadata
is not a complete zero cost. Offline seals cannot reserve/submit; real production
keeps the formal Work stage, budget and billing history. No second selector.

See [the execution reconciliation contract](../../docs/video-execution-reconciliation.md) for current request sealing and reference/coverage checks.


## Multi-provider video and continuity

Use the data-backed Video Model Capability Registry through the Host and the existing `choose` / `qualify_route` pipeline. Skill authors specify input mode, duration, resolution, native sound, required reference semantics, motion/camera complexity and continuity; they never call vendor endpoints or keep vendor task identities. Read the [unified video contract](../../docs/video-provider-contract.md) when selecting or switching a video route.

First require compatible input modes and combinations, the complete continuity bundle, reference counts, duration, resolution and native sound. Among eligible candidates compare creative fit, scoped continuity reliability, observed generation quality, measured cost per accepted shot, then the complete single-call cost. Unknown quality and unknown invoices remain unknown; do not invent rankings or exchange rates.

Keep one Primary Provider and Model per Continuity Segment. Continuous close-ups, dialogue, armor/action and emotional performance default to identity-critical. A change requires a demonstrated primary-model capability gap and a Shot Boundary, except an explicitly authored edit/extension workflow. A cheaper price is never a gap.

Consume the Work-owned Canonical Continuity Pack: pinned character/face/body/age/hair/costume/armor/weapon/prop definitions, place/time/weather/light, a separate CG or live-action RouteStyleContract, color/lens/camera language, required canonical Media and accepted previous shot/frame. No provider owns a separate character prompt. Transfer the accepted tail frame as first frame when compatible; otherwise bind it as a reviewed continuity reference with explicit semantics. If the necessary canonical bundle cannot coexist with that mode, the route is ineligible.

Seedance Standard is a complex-interaction/hero candidate; Fast and Mini participate in cost-sensitive routing. MiniMax is an action/motion/camera candidate; Vidu is a routine/environment/iteration candidate; Wan is a long-take/multi-subject candidate; Kling is a consistency/Omni/motion specialist. These are routing hypotheses, not benchmark quality scores. Comfy remains image primary and video fallback/experimental. Image production keeps its existing path.
