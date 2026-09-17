# Full performance coverage, interaction and semantic isolation — R3

R3 adds zero Skills, Tools, Agents or top-level contracts. It extends the existing Director intent/projection/review chain and supplies pure validators in `performance_coverage.py`. Coverage manifests are derived artifacts, not DB entities or dramatic truth.

## Full Book gate

Inventory the current source before directing: all Scenes, actual Shots, lexical SpokenContent, significant silent/action units, important interactions, relevant ensemble units, adjacent character appearance edges and required AV observations. The source owner determines the scope. `full_performance_coverage_gate` requires 100% with no missing ordinary fragment; for proposal text it independently reparses current Scene, line and action inventories so shrinking the manifest cannot fabricate 100%. A formal Book must supply its actual Shot inventory. No-actor exemptions require a reason and no actors, voice or performing groups.

Every STANDARD direction includes performance core, objective reference, target, expression range, physical priority, partner/listener relation, continuity in/out and do_not; speaking also requires voice, speech action, mode, handoff and closure. EXPANDED adds fine containment, release, gaze, hands, breath, timing and AV criteria. It never replaces standard full coverage. Shared long-term rules are labeled separately from scene-specific direction.

Director design requests require `FULL_PERFORMANCE_COVERAGE`. `reviewed_receipt(..., performance_coverage_bundle=...)` recomputes the gate, checks its source against request pins and requires the gate fingerprint in feedback evidence. The bundle consists of inventory, directions, current_source_hash, bound contexts, DPD objects and (for proposal scope) current source_text. It is not a new review authority.

## Context isolation

Context records resolve entity refs to display names with scope, kind, source ref and evidence. `render_bound_direction` replaces only bound placeholders (including scoped refs); unbound refs fail, no sample fallback. `validate_performance_context_isolation` checks structured ownership and known foreign entity/partner/prop/location/action/voice-target tokens. Qualified aliases and mentions in source context must be explicit; they do not authorize those entities to appear on screen.

Projection binds context_fingerprint and context_refs. The source resolver supplies `performance-context` and a `context-ref:<ref>` → context fingerprint entry in current pins for each valid ref. Unknown or stale refs block projection. Coverage review additionally checks the actual context table and recorded professional semantic review. Lexical detection cannot prove arbitrary natural language semantics: record finding, evidence and source context; never claim “looks good” as proof.

R2 generic fixture inheritance imported historical props, partners and spaces. Its retained artifacts remain baseline evidence; source fixtures now have independently authored contexts. No fixture inherits a historical scene's prose as generic defaults.

## Interaction and ensemble

`validate_interaction` requires speaker and listener source DPD refs, each side's action/attention, targets, gaze/voice/physical handoff, partner cue, response timing and next Beat owner. Missing important listener DPD returns PARTNER_DPD_REQUIRED. Background participants can be group-directed.

`validate_ensemble` reuses BeatDPD tasks. Each layer has attention, a received trigger, response, relative latency, task persistence and individual variation. Default synchronized emotional response is rejected unless a script reason permits uniform action. No Crowd Psychology, no extra spoken content. All military/background sound stays under Script/SourceSoundIntent authority.

## Observable continuity

Derived maps contain only physical load, fatigue, injury influence, breath/voice load, external expression baseline, recent release residue, attention, interaction residue and return condition, plus DPD refs. `validate_continuity_edge` compares actual previous exit and next entry. Changes require a reason and source event; absent explanation fails. High bodily load cannot magically become fully rested voice. A temporary release cannot become a permanent emotional baseline. One-scene characters have entry/change/exit with no invented post-exit history.

## Vocal mode and melody

The nested `VocalDelivery` value extends existing PerformanceProjection and SourceSoundIntent; AudioPerformanceBrief already embeds the voice projection. PhraseDeliverySpan controls wording delivery, VoiceProfile stable identity, and existing source kinds did not encode singing qualification. Thus there is no new SingingPerformanceBrief.

Modes: SPOKEN, RECITATIVE, SUNG, SHARED_RESPONSE, NONVERBAL. The value also references source, approved lyric availability, melody status and optional approved melody ref. Non-lyrical response never creates words. `require_vocal_capability` rejects unsupported mode with VOCAL_MODE_CAPABILITY_REQUIRED, and unresolved melody still blocks new execution even if the mode is supported. Existing unqualified speech/native-video adapters invoke this guard; no adapter may silently convert sung to spoken. Later model qualification must establish support; no provider is selected by semantics.

`native_vocal_disposition` preserves acceptable existing sung/chant performance using the native-first policy, provided observed mode matches. Keeping existing sound is not new melody production or a historical-authenticity claim.

## Full AV review

`bind_full_performance_review` derives all performance_required_beats and channel obligations from the full inventory, with a coverage fingerprint in existing FilmReview. `full_av_coverage` requires the corresponding observations and known PASS checks for every unit. `film_review_verdict` blocks incomplete coverage. Media Director requests require `FULL_AV_PERFORMANCE_COVERAGE`, in addition to existing checks. Action-reference keys for silent/non-lexical units are coverage refs, not invented canonical SpokenContent IDs.

Planned obligations ≠ observed evidence ≠ adopted media. No actual media means actual AV coverage remains incomplete even when design coverage is 100%. Contract consistency and semantic isolation tests cannot establish artistic success. Core uses no platform-specific IO.
