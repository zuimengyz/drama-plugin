# Cross-modal performance direction — R2

ONE DPD → ONE DIRECTOR PERFORMANCE INTENT → BODY + VOICE → OBSERVATION → REVIEW → ADOPT.

This is an opt-in extension of existing capabilities, not a new Skill, Tool, Agent or production authorization. R1 proposals used as fixtures remain unapproved and non-canonical.

## Authority and contract budget

Script owns events and exact words. SceneDPD / BeatDPD / LineDPD / DPDSnapshot own objective, obstacle, tactic, subtext, knowledge, relationship, internalActivation, externalControl and interactionTarget. They remain unchanged. Director owns audience experience, performance scale, containment, release and continuity. Visual and voice project these sources without new psychology.

The only new top-level contract is `DirectorPerformanceIntent` in `contracts/performance_direction.py`. Existing CinematicIntent was an untyped working sidecar, insufficient for shared validated performance pins. Intent has source/DPD/Beat refs, human performance core, audience experience, focus, containment, external expression ceiling, permitted release/point, rhythm, continuity and prohibitions. It cannot contain DPD-owned fields or provider controls.

`PerformanceProjection`, `PerformanceObservation` and `BeatCoordination` are nested value objects: no independent schema version, persistence identity, approval lifecycle or Tool. Existing VisualPerformanceBrief and AudioPerformanceBrief embed projection; RealizedPerformanceSnapshot and FilmReview embed observation; intent/projection embed event coordination. Existing CinematicShotSpec embeds the same projections as its sole execution authority. Legacy omitted fields serialize identically and retain fingerprints.

## Authoring and projection

Use `validate_intent`, `performance_envelope`, `project_visual_performance` and `compile_projected_speech_request`. Supply the same DPD, `director_intent`, `performance_projection`, `current_fingerprints`. Visual projection additionally binds the current route grammar hash; voice and intent have no route field. Exact SpokenContent, stable VoiceProfile/identity and timing remain required.

Each projection carries concrete authored language, not an emotion-to-prompt heuristic. Actor fields cover body, posture, weight, movement, eyes, head, hands, visible breath, prop, partner, distance, timing, release, continuity and do_not. Voice fields cover voice core, interaction, spatial projection, pace, rhythm, intensity, breath support, phrase attack, articulation, emphasis, pause function, closure, coloration, release, continuity and do_not. The DPD target/control must match; release and amplitude stay within intent. HIGH pressure + HIGH control may yield LOW expression. Emotion does not automatically produce sobbing, collapse, shaking, shouting or whispering.

Every performance-bearing fragment requires direction. Use `render_performance_pair` for expanded critical Beat inserts; concise standard direction covers every other fragment. See [R3 full coverage](full-performance-coverage.md). It does not generate a new book contract. The authored language must say what an observer sees/hears and why an action waits for the partner. Merely writing “restrained / sad” fails creative review even if a string validator accepts it.

Use `attach_cinematic_performance` before freezing CinematicShotSpec. Frozen direction binds the intent and source/grammar pins; native video execution carries the two channels through the same spec. Do not send a second independent visual prompt. Legacy speech adaptation rejects extended R2 briefs with `DIRECTOR_VOICE_ADAPTER_QUALIFICATION_REQUIRED` until a later adapter qualification preserves all intended semantics. Never remove the new fields to bypass this guard. No provider is selected by this contract.

## Beat coordination and realized performance

Coordination refers to existing Beat + SpokenContent. Event relations NOT_BEFORE / NOT_AFTER / WITHIN express voice-before-action, voice-during-action, voice-ending-before-action, action-interrupting-voice, partner-triggered-line and pauses-waiting-for-partner. These are relative constraints, not new dialogue, a second Beat owner or a fabricated lip-sync timeline.

Observe actual output into RealizedPerformanceSnapshot and FilmReview: media hash, speaker, Beat/line, method, interval, evidence reference, visible/audible state and observed event times. Frames cannot establish voice performance. Meaning and unknown facts must be recorded honestly. Do not label synthetic fixtures NORMAL_AV.

`reconcile_realized_performance` returns observed action events/load/breath. `condition_audio_on_video` preserves exact words/identity/DPD and carries those facts into the video-conditioned brief. It neither invents mouth windows nor automatically retimes audio. Changed meaning returns VISUAL_REVISION_REQUIRED; unknown meaning remains insufficient evidence. After actual dubbing, compare actual body and sound again.

## Review and native audio

`review_av_performance` extends existing FilmReview with 13 alignment dimensions and per-required-performance-bearing-Beat results, planned source refs and observations. It preserves findings from other Beats. FilmFinding already provides evidence text, interval, severity, repair_owner and proposed_repair. Voice mismatch → audio-production; body/story deviation → shot-production; inconsistent release/continuity intent → director; only contradictory DPD semantics → dramatic-performance-direction. A timing repair names the owner of the offending event. No new AVPerformanceReview is needed.

`native_audio_disposition` is read-only:

- KEEP_NATIVE → existing PRESERVE / empty AvAssemblyManifest external audio and timeline; no new Media.
- LOCAL_REPAIR → existing LOCAL_REPLACE bounded windows; cannot escalate to full dubbing.
- DUBBING_REQUIRED → an actual failed dialogue/identity/intelligibility/performance criterion plus explicit matching reason; still no generation authorization.

Good native audio wins even with a full voice brief. Actual native decisions require complete listening coverage; uncertainty requires review. A bounded sound issue is localized automatically. A semantic decision is not an assembly execution, provider call or spend approval.

`film_review_verdict` and Director receipt require complete observed alignment plus existing film checks before adoption can be considered. Director requests mark `AV_PERFORMANCE_ALIGNMENT` as required evidence. DESIGN_ONLY can pass contract comparisons but never real-media adoption. OBSERVED ≠ ADOPTED; the user gate remains unchanged.

## Validation limits

The checker compares authored structured observations and pins. It does not hear audio, perceive acting or prove that natural-language labels describe the bytes correctly. Film review must verify those labels against playback. Contract valid ≠ good acting; alignment valid ≠ moving performance. R2 fixtures exercise consistency and repair routing only. Source can be revised solely by its owner and only under the appropriate approval; current R1 remains pending user screenplay review.
