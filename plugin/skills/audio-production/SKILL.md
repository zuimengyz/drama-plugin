---
name: audio-production
description: Produce exact-text dialogue speech clips, dialogue mixes, and final AV from approved Drama Dialogue and immutable source video. Use for provider-neutral voice resolution, speech freshness, duration probing, review, and deterministic AV assembly; do not use for authoring or revising Dialogue.
---

# Audio Production

## Choose the adopted performance before processing

Audio production is complete when an appropriate existing audiovisual performance
is adopted and its source is ready for editing. First read the latest user source
selection and inspect available native AV; only then decide whether speech or
postproduction is necessary. User adoption of the original overrides older dubbing
queues and candidate selections within that scope. Preserve the script as source,
but record the adopted presentation separately: adoption or reviewed action/semantic
equivalence can resolve the production requirement without additional speech.
Do not convert every frozen line into a perpetual dubbing debt. Keep explicit
verbatim quotations, key information and causality protected; report a material
missing meaning rather than forcing speech onto footage that cannot carry it.
Do not silently promote random provider words into canonical dialogue.

For native reuse, use the public Host `assemble_av` with the adopted file/hash and
an `AvAssemblyManifest` whose external audio and timeline are empty. It returns
the original path as READY, without TTS, separation, mixing, mux or a new Media.
This precedes cache selection and speech generation. Run speech-only steps below
only after a concrete dubbing need is established. Off-screen, rear-facing or
reaction-shot dialogue can be valid with real narrative/spatial evidence; neither
missing visible mouth movement nor available milliseconds decides this alone.
An audition's ASR match and duration fit do not approve placing it in the scene.
If voice/scene fit cannot be heard, record the limit; do not require the model to
re-approve an explicit user adoption or claim the user verified other facts.

Load the [Audio Layer content convention](../../docs/audio-layer-content-convention.md), the [Audio Projection contract](../../docs/audio-projection-contract.md), and the [scene-aware audio rules](references/scene-aware-audio.md). Treat the Audio Provider as a replaceable capability. Do not encode a vendor, transport, server, workflow, preset voice, or provider-specific pronunciation syntax in this Skill or in Drama content.

For video-conditioned final dubbing (Batch 7.3D), also read the [video-conditioned contract](../../docs/video-conditioned-audio-contract.md). This phase overrides the later Voice-design and AV-assembly steps: reuse frozen Video/Voice and accepted RealizedPerformanceSnapshot, keep DPD as dramatic-intent authority, and condition execution on actual visible facts. Preflight Video and Voice through the Drama Service owner with download/hash checks after storage migration; missing objects require reconciliation, never new identity. With unknown mouth activity, preserve natural delivery without guessed speech windows or filling the Video duration. Preserve a strict baseline separately; stop after durable dry dialogue and its review package, before lip sync, sound design, mixing or mux. Do not derive a new Character Voice Profile for this phase.

Gather the Scene with `scene.get_scene`, its Episode with `episode.get_episode`, its Script with `script.get_script`, its Work with `work.get_work`, and any requested Shot with `shot.get_shot`. Use `asset.search_assets` and `asset.get_asset` only when the Work/Scene chain does not already provide sufficient structured Character context; Character Assets do not require Media. Resolve each target only from `Scene.content.spokenContent[]`; preserve its exact `text`, `spokenContentId`, and `speakerKey`. A Provider adapter may derive a separately fingerprinted rendered-text representation using only officially documented and locally allowlisted controls, but it must preserve lexical content and never overwrite the canonical line. First produce an evidence-scoped, value-neutral Character Understanding with explicit unknowns; then derive a stable Character Voice Profile. When an approved `DPDSnapshot` is available, combine it with canonical SpokenContent, the stable Voice/Casting identity, the Voice baseline, and necessary Timing Context to create one typed `AudioPerformanceBrief`. The brief is the sole performance authority for the new path; do not also send Scene State or legacy Performance Intent. Include the hierarchy, Shot, Dialogue, character, listener, confidence, and evidence references in the structured request. Resolve applicable `Work.content.pronunciationGuidance[]`; stop on insufficient identity, DPD objective/relationship, Voice baseline, or unresolved pronunciation, and never repair gaps by changing Dialogue or DPD.

Compile the provider-neutral `SpeechGenerationRequest` with exact text in its typed field. Do not select a concrete provider, model, preset voice, reference identifier, transport, or endpoint. For the DPD Projection path, retain the platform Voice identity reference and the DPD/Projection fingerprints; the adapter reports every brief dimension as supported, approximated, or unsupported. It must not silently discard a direction or invent an unavailable parameter. The Role Dubbing Tool resolves `Work + speakerKey → voiceId → Voice`; the projected path requires that stable binding to match the brief. The legacy path may still reuse or materialize an approved Voice. For a new Voice, declare the stable use case (`CHARACTER_DIALOGUE` or `NARRATION`), reject every technically failing candidate before creative-fit comparison, and stop when the hash-addressed review package returns `VOICE_ARTISTIC_REVIEW_REQUIRED`. AI ranking is not approval. Only resume with an explicit user approval matching that package; do not redesign, import, materialize, bind, or synthesize before approval. A successful new binding identifies the durable Voice, never one Dialogue Media result.

Preflight only the required Role Dubbing and local probe capability. In contract-only, dry-run, or foundation work, stop before generation. For explicitly required independent dubbing, call `production.generate_role_dubbing` once per stale spoken item with the structured request; never ask the Provider to write or improve the line. The Tool owns synthesis, output-side ASR, CER/missing/extra/repetition/proper-noun gates, durable Audio import, Voice identity, provider materialization, and Work binding. A failed intelligibility result cannot become formal Dialogue Media. A technically passing result remains `reviewStatus=PENDING` for human artistic Audio review while its technical review is PASS.

Inspect the durable identity with `voice.get_voice` when binding or provider-materialization evidence is required. Inspect the returned `ROLE_DUBBING_AUDIO` with `media.get_media` and resolve it with `media.resolve_media` when physical integrity or user review is required. Reconcile actual duration against the visual window without deleting, adding, or rewriting words. Prefer reviewed pace/pause or visual re-plan when needed. Deleting or invalidating a Dialogue Audio result never deletes its Voice; retiring a Voice never deletes historical Media.

Build one `av-assembly-v1` manifest for the selected source strategy. Native reuse needs no new Audio or FINAL_AV Media. When external dialogue is required, reuse one speech clip across all relevant Shot slices; `spokenContentBindings` remains the visual coverage authority. An optional `SHOT_DIALOGUE_MIX` is derivative. Resolve durable inputs with `media.resolve_media`; never persist signed URLs. Mux to a new path, capture implementation/version/settings, probe both streams and duration, hash all inputs/output, and confirm the source Video hash is unchanged. If the capability is missing, return `AV_ASSEMBLY_CAPABILITY_MISSING` while preserving completed speech-foundation results.

Import a successful mux with `media.import_media` as a new `mediaType=VIDEO`, `purpose=FINAL_AV` Media identity with positive probed duration and the committed manifest/fingerprint. Resolve and hash-review it. A preview awaiting any MUST Audio review uses `final-av-attempt:<fingerprint>:<attempt-id>`; only a fully reviewed result uses `final-av:<fingerprint>`. Stop when the requested reviewed clips/mix/final AV are stable; do not begin another Scene or expand into sound design automatically.

## Coordinated single-Shot execution

For a user-authorized coordinated E2E, keep PLANNED, EXECUTION, REALIZED and ACCEPTED separate. Resolve latest hash-bound user failures before candidate reuse; cache/source validity never clears artistic rejection. Use exact-text Production Audio to derive actual durations for visual execution. A pending best-evidence candidate may continue when the user explicitly authorizes intermediate E2E progress; label it pending and never fabricate USER approval. Voice redesign still requires identity evidence; do not redesign because an acting Take failed.

Author optional `phraseDeliverySpans` inside AudioPerformanceBrief from canonical character offsets and DPD action progression. Preserve target-directed interaction, relationship, phrase rhythm and responsive ending. The adapter must report actual rendering or a limitation. Video conditioning validates and retains an authored brief; it cannot replace phrase actions with generic finality. Changed source Video makes its old conditioned wrapper stale; target-reviewed reuse retains true source provenance and is a separate decision.

After all coordinated offline regressions, generate only necessary Audio, derive execution timing, generate one dialogue-aware Video, observe every speaker, and reconcile physical then visible fit. Allow at most one evidence-directed visual rebuild; freeze Audio after that correction. Lip sync uses explicit speaker selection and current reconciled windows without changing Audio or timing. If intermediate continuation was explicitly authorized, continue through no-lip preview to verified mouth processing and final review; otherwise respect the requested review gate. A final AV awaiting human review is a derivative attempt with PENDING review, never an accepted canonical result.

## Reviewed language renditions and native sound

The exact-source rule above remains the V1 default. For explicitly authorized,
Scene-reviewed performance adaptation, consume the single source-bound rendition
using `resolve_performance_text` and `compile_projected_speech_request` with
`performance_rendition`. Never translate inside the adapter. The request exactText,
voice-profile language, content-QC reference, subtitle association and fingerprint
must all follow that version. Frozen authoring text remains intact. Only Scene
review may approve a native wording variant; ASR cannot make it canonical.

Before deciding on TTS, inspect each source audio timeline and compare required language,
speaker, meaning, order and acting. Separate environment/mechanical/cloth/footstep/
contact sounds, breath/exertion/nonlexical sounds, compliant dialogue, and wrong,
extra or uncertain dialogue. ASR, levels and frames are evidence, not listening.
If direct listening is unavailable, record NOT_VERIFIED and keep artistic review
pending. A grunt alone does not justify muting. A technically available Voice
requires target-language/role-fit review; a past role's approval does not transfer.
Use the necessary line itself for a bounded existing-Voice audition when authorized.

Choose one source for each line: reviewed native performance or controlled speech.
Do not generate extra TTS for a native line that already passes. Review unresolved
native speech before attempting replacement; never adapt the screenplay to random
provider dialogue. Preserve clean native sound by default. For local errors,
review and localize the window and overlaps; ducking still leaves erroneous words.
Separation or compatible same-source ambience patches require listening for damage
and explicit patch provenance. Do not presume perfect separation, add a model stack,
new paid service, music or lip-sync jobs automatically.

Postproduction owns placement and a complete mix. Use measured speech duration and
visible actions; keep raw TTS and video immutable. No syllable cuts, forced speed or
pitch, automatic whole-track mute, duplicate ambience bed or two dialogue sources.
`assemble_reviewed_native_mix` is a local Host helper with an explicit strategy,
source hash, per-line placements and bounded reviewed replacement windows. Its
pending mix is a candidate, not an acceptance result; its local silence operation
is not separation or a completed environmental repair. `mux_video_and_audio`
continues to replace audio with the supplied complete mix, preserving legal V1
replacement calls. Capture mix settings/fingerprint inside existing Final AV
fingerprint muxSettings and physical audio hashes. Never use MP4 byte equality as
proof of unchanged video: compare video packets or decoded frames. Lip review is
ALIGNED / APPROXIMATE / MISMATCH / NOT_VERIFIED independently of technical checks.


## Durable completion and recovery

For retained image, video, audio or derived AV, formal completion requires full
readback SHA-256/size, decodable media, correct business ownership and a queryable
stable business binding. A local path, upload name, returned ID or temporary URL
alone is PERSISTENCE_PENDING. Content PASS, user adoption and persistence are
independent; persistence must never rewrite an existing adoption decision.

The shared completion entry `complete_retained_media` implements import/reuse,
readback and binding. Visual attempts call it through `visual_preflight.py persist`;
role speech calls it before returning a production result; `assemble_av_delivery` resolves the declared source and complete mix, performs an
explicit mux, and calls it on the new output before formal delivery. Adopted native AV consumption uses
`prepare_bound_media(adopted=True)` to recover the selected original from its formal
business reference. It performs no dubbing, separation, mixing or remuxing.

After a successful generation, resume at import/readback/binding with the same
job, output hash and sourceRef. After an uncertain import, query the exact stable
source first; ambiguity, permission denial, hash conflict or unknown ownership
blocks completion. Retry transient reads with finite backoff and fresh resolve.
Never generate again to repair missing cache or persistence. Do not import
unneeded DEBUG/REJECTED files or invent an output that was never generated.

For an explicitly authorized replacement mix, use
[scripts/assemble_delivery.py](scripts/assemble_delivery.py) with the declared
source/mix identities and manifest. A stored derivative remains CANDIDATE until
content review and adoption are separately resolved. Native source adoption
continues through `prepare_bound_media` and never enters the replacement path.
