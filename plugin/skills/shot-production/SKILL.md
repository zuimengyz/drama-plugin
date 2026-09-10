---
name: shot-production
description: Produce image, video, or audio media for an approved historical-drama Shot. Use when combining Shot and Scene context, selected stable Assets, and prior Media into start frames, end frames, video, dialogue, ambience, or other physical media outputs.
---

# Shot Production

New Shot production consumes a frozen `CinematicShotSpec` from cinematic-direction
before video-model-selection. Use the existing [director handoff](../../docs/cinematic-direction-contract.md)
to carry acting beats, camera motivation, reference duties and execution demands
into the same route/request checks. Do not replace it with a free emotional label,
skip its frozen projection, or change an adopted original AV while adding direction.

Use `shot.get_shot` and `scene.get_scene` when their stable IDs are known and the approved production context was not already supplied. For a continuous Scene, establish one shared Sequence Context before producing its Shots. Load [references/production-rules.md](references/production-rules.md) to plan stable facts, references, Shot deltas, review, and revision. When a Shot has `spokenContentBindings`, also load the [Dialogue Layer content convention](../../docs/dialogue-layer-content-convention.md), resolve every binding against the Scene's canonical `spokenContent`, and require numeric `plannedDurationMs` plus a passed `DURATION_FEASIBILITY` check before physical media production. Keep these decisions in Agent Run Context rather than creating new domain records.

Discover reference candidates from named visible characters, the Scene, focal props, costume variants, and other relevant stable visual entities. Use `asset.get_asset`, `asset.list_assets`, or `asset.search_assets` without inventing references. Inspect stable reference Media with `media.get_media`; use `media.list_media` only for a clear structural media scope, not broad discovery. Select no more than three stable Asset-plus-Media references. Record selected and omitted candidates with rationale. Return `MISSING_STABLE_REFERENCE` for a key visible character whose stable identity is absent; do not silently omit it, substitute an informal image, or generate an unreviewed master inside Shot production. This blocks only media that must show that character; it does not invalidate the Work-scoped `speakerKey`, Scene dialogue authoring, narration, or non-visual speaker identity.

Do not require a visual provider for context reads, non-visual planning, Shot design, or other non-visual work. For image or video planning and execution, load [references/visual-provider.md](references/visual-provider.md) so the plan includes the complete reference-to-provider-to-Media handoff. Before actual execution, preflight only the Drama and visual capabilities required by that request. Return `DRAMA_PROVIDER_UNAVAILABLE`, `VISUAL_PROVIDER_UNAVAILABLE`, or `VISUAL_PROVIDER_CAPABILITY_MISSING` when the corresponding capability is unavailable; stop rather than installing, configuring, or simulating a provider.

Before preparing new video inputs, consume a qualified ProductionRoute from [video model selection](../video-model-selection/SKILL.md). Select only after Shot narrative, performance and sound requirements are fixed. This planning record has input duties, not placeholder Media. Seal the executable video decision only after its actual inputs are reviewed and formally recoverable. For video and its necessary input images, use one stage budget in [first-pass production](references/first-pass-production.md); submit only the reserved request and requalify after any material change.

Before visual generation, compile each approved Shot into stable identity and environment facts plus current action, composition, representative keyframe intent, required visual evidence, forbidden visual outcomes, and continuity constraints. For new image production and image revisions, load [first-pass production](references/first-pass-production.md) and use its executable request preflight and persistent reservation/review gate before calling the Host provider. Qualify up to three representative planned Shots before expansion, preserve reference versions and actor/action ownership, and change strategy when material failures repeat. Use resolved dialogue only for the visible delivery, reaction, off-screen, or voice-over intent relevant to the binding; never copy its text into the Shot or provider-owned state. Resolve each selected input through `media.resolve_media`, execute the available visual capability, and apply the per-Shot review defined in the production rules. Reject an unsuitable candidate without ending the task. One focused correction is a useful default, not a target limit. The Host may reassess prior candidates, select a suitable working input, or replan composition, supported inputs, model or template within the existing task and stage totals, without another creative approval. Preserve core story facts and user adoption; record the reason, next choice, key change and incremental cost, then continue. Do not regenerate a suitable candidate for ordinary flaws.

When an authoritative `DPDSnapshot` is supplied for a visible speaker, first project it into a typed, provider-neutral `VisualPerformanceBrief`. The brief owns only current visible behavior such as body activity, head behavior, gaze, facial tension, gesture policy, interaction orientation, pre-speech behavior, and visible control. Stable Character/Scene appearance remains in Asset/Media; framing, lens, angle, composition, and camera movement remain in Shot design. The projection must not reinterpret objective, tactic, relationship, subtext, or historical context. Materialize the brief together with the separate Shot camera/design facts, and record unsupported or approximate Provider controls without pretending they are exact.

After technical/source checks, preserve a worthwhile paid output as CANDIDATE even while content review is pending. Use the production gate `persist` operation for an existing visual attempt: call `media.import_media` or reuse by stable source, get/resolve/download, verify full bytes and ownership, and write/read back its formal business binding. Keep content review and user adoption independent. Any required identity annotation is a separate derived version; it is not a Provider quality criterion and must not replace already adopted bytes. Keep the verified `mediaId` and role in both the formal business record and Agent Run Context. For a DPD-directed performance video, inspect playback or a controlled set of representative frames and record an accepted `RealizedPerformanceSnapshot` from actual visible facts, including only the minimum useful timing windows. Describe the video even when it deviates from DPD; a conformance diagnostic may inform regeneration but must not block Media, Snapshot, or downstream work and must never rewrite the observation. Unknown or obscured facts remain `UNKNOWN`. Observation never infers objective, tactic, relationship, subtext, or internal activation. Compare only Review-PASS Shots during cross-Shot continuity review. If two or more Shots require continuity regeneration, stop with `SEQUENCE_CONTINUITY_REQUIRES_REPLAN`. When audio production is explicitly requested, `production.generate_role_dubbing` may consume the resolved Scene text, Work-scoped speaker identity, performance intent, provenance, estimated duration, and Shot coverage intent; it must not rewrite, delete, split, merge, or replace canonical `spokenContent`. There is no mandatory image-to-video-to-audio sequence and no separate Dialogue record or Audio timeline in this Skill. An explicitly adopted existing AV may go directly to Host assembly preparation with its original sound; source dialogue bindings are not a mandate to add external speech to an already adopted performance. Record a material narrative gap separately without silently rewriting the screenplay or automatically scheduling dubbing.

Use `context.build_context` only when required Shot context was not supplied, and use `context.refresh_context` only after stable generated Media makes the current context stale. Never expose temporary URLs, storage locations, filenames, provider task IDs, workflow documents, node IDs, or provider-specific responses as Drama domain facts. For a DPD-directed performance video, stop when both the stable Media role and accepted Realized Performance Snapshot are clear; otherwise stop when the requested media exists in stable Drama memory and its role is clear. Do not redesign the Shot or continue to another Skill automatically.

## Dialogue-coupled execution

When complete actual Audio exists, derive this Video's execution timing from its measured durations, the immutable DialogueTimingPlan's protected reactions/holds, and the production target. Never let original estimates exclusively determine speech phases. Consume the derived material in the schema-authoritative projection (legacy VisualPerformanceBrief or new CinematicShotSpec) and the real request; emit active speaker, listener, visible action, reaction, transition purpose and performance boundaries rather than only hashing them.

Keep monolithic production for the current single-Shot baseline. New Video requires new shot-level RP and speaker-specific snapshots with observedSpeakerKey; null denotes aggregate only. Observe visible participation and handoff, not guessed psychological states or mouth-as-speech-onset. A physical fit does not prove visual fit. Respect latest user rejection and the current task's explicit intermediate-review authorization. Record one shared corrective visual rebuild budget; if that fails, do not enter an unbounded Audio/Video loop. Mouth derivatives require fresh face/non-speaker/identity/continuity observation, preserving original source Media and timing authority.


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

## New-story route gate

For a new production Work, finish narrative and text identity first, jointly
plan the route and its minimum input duties with video-model-selection, and save
that route using the existing Work contract. Asset discovery before route selection
is read-only. A shared reviewed image may establish several necessary identities;
do not automatically create separate character, location, prop and endpoint sets.
Use `shot-production/scripts/route_preflight.py` for the Work-owned stage. Paid
images must match a current necessary duty and explicit whole-stage budget.
Materialize and review only the inputs for the current representative target;
no full-episode asset expansion follows from route selection. Keep all result,
review, settlement and persistence updates on that same formal stage.

Initial visual identity creation belongs to asset-resolution and may share a
necessary first frame. Mark `identity_bootstrap` explicitly in the existing image
preflight; it is a creation intent, never a claim of identity continuity PASS.
After inspection and formal persistence, bind a joint image once and enumerate
its `reference_members`; preserve distinct named actor blocking. Subsequent
frames require the reviewed reference and cannot use bootstrap to bypass identity
review. Fixed reference limits remain unchanged.

## Use-based content review and autonomous recovery

Judge whether the shot works at normal viewing size, duration and in context. Natural occlusion, imprecise background/type detail, unlocked initial appearance preferences, minor costume/light/framing differences and unconfirmed contact do not by themselves block. An input still is not a magnifiable technical diagram. Do not infer an error from missing evidence. A major failure must describe the visible observation, the core requirement it breaks and why that affects this use; a category label alone is insufficient. Missing action-critical props, contradictory action causality, serious established identity/continuity errors, explicit distortion of important historical facts or severe normal-playback audio/visual defects remain failures.

Record applicable checks, notes and major findings in existing reviews. Omit irrelevant dimensions; relevant unknown evidence remains pending and the Host first seeks observations. Pending sound does not block independent visual work or become sound PASS. Append reassessments without replacing original review or paid/rework events. Consume the latest effective review for the stated use. The Host can choose a verified suitable Media as HOST_WORKING_INPUT; this never implies USER_SELECTED or final artistic acceptance.

Use existing route_preflight revise-review, select-input, resume and replan operations. Old TARGETED_REVISION_FAILED records remain historical; normal Host replanning releases the content pause without resetting attempts or requesting an exception. Requalify changed routes and compile/seal changed requests normally. Confirmed created jobs count toward stage totals; confirmed noncreation stays a bounded technical attempt, unknown creation must be recovered before another submission. Unknown settlement retains its reserve but is not a running generation. Never repeat a failed approach without changed strategy or reasonable success evidence.

## One visual execution authority

For `creative_schema = cinematic-shot-v1`, DPD is the dramatic authority and
CinematicShotSpec is the only visual/time/camera execution projection. The
VisualPerformanceBrief instructions above apply only to legacy schemas; keep old
briefs as lineage, never another compiled motion prompt. RealizedPerformanceSnapshot
remains observation of actual Media after generation.

The existing Host adapter must preserve every execution-critical semantic in its
projection manifest. REQUIRED references need formal Media identity, sourceRef,
hash/type, reviewed duty and actual slot, or an explicit supported equivalent.
Static portraits cannot fulfill performance references. Check observed endpoint
state against frozen Opening/Ending; conflict requires re-plan. Input caps remain.

SourceSoundIntent covers generation-time native speech, diegetic/ambient sound,
silence, unwanted music and continuity. It does not choose voices or mix audio.
Original AV stays immutable; authorized repairs create new derivatives.

`scripts/compile_video.py` uses the actual compiler/seal offline and always emits
non-submittable dry requests. Paid use requires fresh canon/Media through
`route_preflight.py`, current capability, complete quote and the existing stage
reservation. Unknown complete cost stays unknown. Only verified provider metadata
may impose a prompt limit; no shared 2000-character cap or silent truncation.
