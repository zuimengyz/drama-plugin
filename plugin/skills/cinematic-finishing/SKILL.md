---
name: cinematic-finishing
description: Finish existing edited drama with scene sound continuity, local ambience repair, optional BGM and a retained derived Media. Use for picture edit planning from reviewed source Media, or for sound finishing after picture editing when performances and timing should remain intact.
---

# Cinematic Finishing

## Full AV observation coverage (R3)

Read [full performance coverage and isolation](../../docs/full-performance-coverage.md). Bind FilmReview with bind_full_performance_review from all performance-bearing source fragments. performance_required_beats is the full set, not a highlight reel. Keep required channel coverage per fragment: silent actions require visible evidence, spoken/shared vocal responses also require listening. One missing ordinary Beat yields AV_PERFORMANCE_COVERAGE_INCOMPLETE; UNKNOWN is never PASS. A full design manifest is only an observation obligation, not playback evidence. Preserve R2 evidence when a later semantic defect is found; report the finding with actual source context and repair owner.

## AV performance alignment facet (R2)

Read the [shared performance contract](../../docs/cross-modal-performance-direction.md). Use existing FilmReview / FilmFinding, not a parallel AV review contract. Compare pinned planned DPD/Director/visual/voice with actual RealizedPerformanceSnapshot and listening evidence across amplitude, control, target, physical/vocal effort, breath, timing, pause, spatial reach, partner cue, release, continuity, native suitability and meaning. Include byte hash, speaker/Beat/line, observed time interval and evidence reference. Missing evidence remains UNKNOWN.

Review every required performance-bearing Beat; a later PASS cannot erase an earlier failure. Each finding names the visual, audio or Director repair owner; DPD review is reserved for actual source-psychology conflict. Review repaired bytes again before adoption. DESIGN_ONLY evidence never proves observed media; OBSERVED never means ADOPTED. Full native reuse needs listening coverage; a local sound defect cannot authorize full dialogue replacement. Contract-valid alignment does not establish moving or artistically successful acting.

## Opt-in Director authority

Keep EditorialRhythmPlan, PictureEditPlan, SequencePackage and FilmReview as the original owners. Director intent governs acceptance without a parallel edit plan or review. Return existing output/evidence references; use the optional FilmReview director facet for actual-media intent coverage and causal disposition. A design-only judgment stays in Bible review, never a fabricated AV review. Director approval does not imply user adoption, and technical success does not imply Director approval. Native-audio policy and source-preserving finishing remain unchanged.


If the user later adopts an `authorial-voice` candidate, preserve its literary text,
provenance, intent, form and semantic position. Finishing owns its actual screen/sound
delivery (subtitle, black, overlay, reading or silent display) and timing. The presence
of an unadopted literary sidecar does not authorize adding a coda to the film.

Recover the selected assembly with `work.get_work`, its actual `shot.get_shot`
and `scene.get_scene` relations, and `media.get_media` / `media.resolve_media`.
Use `media.list_media` for scoped source material discovery. Source bytes, hash,
duration, tracks, timeline and ownership must agree before editing. Preserve the
original. A filename is not selection or recovery authority.

## Consume the Sound Bible for measured finishing

Read Sound Design’s continuous passage plan, independently of Shot file edges:
Dialogue; Diegetic / Source Sound; Persistent Ambience; Transition; Silence.
Music Direction separately supplies BGM decisions. Conform each approved cue’s
source, function, passage range, entry/exit and perspective to observed Media. One cue can cross
several Shots and adjacent Scenes. A cut does not restart or stop it. Use J/L
cuts, crossfades and envelopes only where they serve space, action or attention.
Do not mechanically loop a short vocal/music phrase to fill a longer passage.

Default priority is Dialogue > narratively important diegetic sound > persistent
ambience > BGM. Protect the actual words and synchronized action sounds. Duck
lower layers around measured dialogue, with natural ramps. Do not mute mixed
dialogue to remove an overlapping effect. Seek original tracks first; if only a
mix exists, use a localized, evidenced repair and disclose its collateral limits.
An isolated wrong sound does not justify inventing a new battle or changing story.

## BGM decision

Consume Music Direction’s reviewed NO_BGM, SUBTLE or ACTIVE decision for the
Scene/passage. If no reviewed music decision exists, return to that owner.
Distinguish it from unavailable music. For music, state whose situation it helps
the audience understand, its entry/exit, cross-Shot scope, and how dialogue and
important source sounds retain attention. An emotion label alone is insufficient.
Do not automatically score sadness/battle, cover editing errors, or fade every
Shot independently. Diegetic singing is not automatically BGM.

Sources may be EXISTING_MEDIA or LOCAL_LICENSED with traceable usage rights;
GENERATED is a future capability seam, never an implicit fallback. Retain any
adopted local material through `media.import_media`, verify full hash/get/resolve,
then use its stable Media ID and source ranges. Missing material stops only the
dependent finishing operation with a precise source/range recovery point. It
never authorizes new picture, voice or music generation.

## Local execution and review

The Host translates the plan into a local recipe: verified inputs, source trims,
placements, envelopes, replacement windows, protected dialogue and remux. Use
the packaged `scripts/finish.py` entry and [Host contract](../../docs/cinematic-finishing-host.md).
Department originals own creative decisions; the Host handles extraction, trim, fades,
crossfade, ducking, mixing, probe and video stream copy. Verify compressed video
packets AND timestamps; a changed container hash is expected. Do not re-encode
picture as a convenience. Preserve original audio outside approved edits.

Review the full passage at normal playback, especially cue continuity, dialogue,
transitions, perspective and unwanted sound sources. Tiny noise/loudness
differences alone do not block. A major finding states observed sound/picture,
broken requirement and narrative consequence. Re-plan locally in scope without
repeated creative approval. Do not infer failure or PASS from absent evidence.
ASR, waveforms and spectral checks support localization, not listening. If the
Host cannot actually hear, keep audio review UNKNOWN and retain a clearly named
candidate; never claim final audible repair. Seek available observation first.

## Persistence and recovery

Use `work.save_work` and `scene.save_scene` to merge the current finishing
revision and references into existing content (save replaces content: preserve
unrelated fields). Keep source Media/hash, scope, sound plan, compact numeric
recipe with stable source IDs/ranges, derived Media/hash, review and userAdoption.
Local commands/PCM/probes are working artifacts, not the only recovery memory.
Keep historical revisions; changing a sealed recipe needs a new revision.

Use the shared import/get/resolve/full-hash/business-binding completion for the
new derived Media. A retained UNKNOWN candidate is not an adopted final. Host
selection and the user's eventual USER_SELECTED are distinct. Repeating the same
revision reuses the same Media; ambiguous imports are queried before any write.
Storage failure recovers identical output, never generates another picture.
Completion states exactly what was rendered, heard, verified and still unknown.

## Long-term BGM retrieval and rights

Decide NO_BGM / SUBTLE / ACTIVE before retrieval. NO_BGM skips music search,
selection and assembly. Otherwise call `asset.search_assets(query="BGM",
asset_type="AUDIO_INPUT")`, retaining only `creativeKind=MUSIC, role=BGM`.
`creative_assets.search_bgm` applies optional mood/narrative-function filters and
returns explainable candidates; assess energy, dialogue compatibility, duration,
entry/exit and rights. Search rank never makes the final choice; listen when needed.

UNKNOWN rights remain discoverable memory with productionEligible=false. Production
requires VERIFIED source/license/commercialUse/attribution plus bound durable
AUDIO Media. Refresh `asset.get_asset` rights before a new production, verify
`media.get_media`, resolve and full hash. Never infer rights, BPM or instruments.

Explicit selection uses `creative_assets.select_bgm` and records assetId,
assetFingerprint, mediaId, contentHash, selectedRange and reason. Each BGM recipe
layer retains `bgmSelection`, `bgmAsset` and `bgmMedia` snapshots. Existing render
validates rights, ranges and lineage before even reusing a cached output; normal
full-byte hash checks remain mandatory. Missing/unknown rights stop BGM execution.
Metadata edits never regenerate audio. See [creative memory contract](../../docs/creative-assets.md).

## Picture Edit Plan

After actual performance review, use the [picture-edit contract](../../docs/dramatic-peak-editorial-contract.md) and typed PictureEditPlan. Select sourceIn/sourceOut by information and measured action, rather than always using the whole generated file; record cut reason, reaction hold, match action, audio carry and pace function. Verify Media ID/hash/range and protected dialogue through `production_design.picture_edit_handoff`. Unknown listening remains DRAFT. This extends picture planning only; the existing sound renderer's source-packet preservation is unchanged. A picture assembly is separately authorized and produces a derived Media. Do not rewrite Script peaks, alter original AV or add music to manufacture a missing payoff. Review monotony, overcutting, missing reactions/detail/establishing context and contrast across the passage.

## Sequence production handoff

For authorized picture assembly, use the bounded local [sequence execution and review contract](../../docs/sequence-production-contract.md) and scripts/edit_picture.py. Reuse PictureEditPlan; hard picture cuts and native audio trims produce a new candidate. Then fulfill sound bridges, retain Media and review the complete rendered passage. Whole-film observation and findings are source-hash pinned; stills and technical checks cannot grant full AV review.

Consume executable Sequence audio/edit obligations separately from design readiness. Bind the actual output hash to FilmReview; UNKNOWN sound or missing normal AV coverage cannot become REVIEWED. Keep produced, reviewed and user-adopted states distinct.

## Intended transitions are upstream requirements

Consume shot-design's EditorialRhythmPlan.transitions as intended continuity, including time/space and sound carry. Finishing owns the actual measured-media cut and PictureEditPlan. Do not treat a planned match action or prelap as already observed or executed. Return infeasible continuity to its owner and retain actual Media evidence.

## Film score boundary

Consume music-direction FilmScorePlan dramatic triggers as requirements. Own measured picture conform, fades/duck/stems; preserve legacy NO_BGM and local repairs. Report music/performance conflicts through existing FilmReview, without changing acting or dialogue. See [Film Score Direction](../../docs/film-score-direction.md).

For every available FilmScorePlan, attach the current plan and source evidence in the existing recipe scorePlacement facet, and bind each BGM layer with scoreBinding. Do not omit a known plan to bypass its protection. NO_SCORE, NO_SCORE_MUST_PRESERVE and DIEGETIC_ONLY block score; empty space is not permission to fill it. Only Director/music-direction re-review may change the plan. Proposal-only plans cannot render into formal finishing. Existing legacy recipes with no score plan remain compatible.

Before impact the score may dominate; at physical contact native impact, breath, horse and armor may take over. Follow the reviewed event policy; no automatic music return after dialogue, real joy, pursuit or death. Map actual source events to reviewed Shot/Beat and Media intervals only after picture exists. An action combining build and impact requires observed phase refinement before execution. This semantic guard does not verify sample-level overlap by itself.

## Film editorial authority facet

For work-level minimum coverage, event-protected cuts or dailies usability, read
[film editorial authority](../../docs/film-editorial-authority.md). Reuse the existing
EditorialRhythmPlan and FilmReview optional facets, and retain PictureEditPlan as
the measured picture timeline. Work-approved priorities and sources govern all
substitution; missing performance values are not permission to author them.

## Coverage production formalization

When approved editorial Coverage enters shot design, generation planning or dailies,
use [coverage production formalization](../../docs/coverage-production-formalization.md).
Keep Coverage IDs stable; resolve split/shared realization through the existing
Shot, SequencePackage and Media owners. The opt-in Host runs realization_handoff,
generation_handoff and media_handoff at their respective boundaries. Policy-ready
is not formalized, and intended lineage is not observed evidence.

## Observed adaptive direction

For evidence-based performance correction, useful unplanned results or adaptive
repair decisions, follow [adaptive director review](../../docs/adaptive-director-review.md).
Reuse FilmReview and Director feedback; separate intended authority, observable
facts and judgment. Resolve the production lineage before live review, preserve
UNSPECIFIED and good material, and pass only a minimal source-bound execution delta
to the existing owner. A dry-run never authorizes production or media adoption.
