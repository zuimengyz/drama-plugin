# Dialogue Timing Reconciliation — Batch 7.4B

`DialogueTimingReconciliation` is a provider-neutral, single-Shot Phase A artifact. It answers whether the complete dialogue can fit before emitting a timing recommendation. It never accepts timing or drives AV assembly.

## Inputs and execution order

Call `reconcile_dialogue_timing` with the immutable 7.4A plan, current Scene/Shot/Work, the plan's DPD snapshots and transition intents, actual Video Media, accepted shot-observation RealizedPerformanceSnapshot and its accepted fingerprint, the observed speaker, current Work-bound Voices, resolved current final-speech requests, and the complete candidate Audio set. When an actual Audio was produced from a DPD or speaker-specific RealizedPerformanceSnapshot distinct from the planning inputs, also supply `audio_dpd_by_spoken_content` and `audio_realized_by_spoken_content`. The caller supplies current data; the helper performs no I/O.

The helper replays 7.4A validation, then evaluates:

1. Every canonical turn and its current final Audio lineage.
2. Actual or explicitly mixed duration budget.
3. Protected pre-hold, inter-turn reaction and minimum post-hold.
4. Accepted visible-performance constraints.
5. Evidence-based conflict diagnostics.
6. Whole-line placement, only if the applicable budget fits and there is no hard visual conflict.

It retains the source plan inside the result to reuse its validation and protected hold semantics. No exact dialogue text is copied into the result. The original plan remains unchanged.

## Audio evidence and coverage

Each ordered turn remains present even when Audio is missing. `audioStatus` is `PRESENT`, `MISSING` or `STALE`; only `PRESENT` permits a non-null actual duration and `ACTUAL_AUDIO` authority. Missing/stale turns use `PLANNING_ESTIMATE` only in the explicitly limited calculation.

Selection checks canonical SpokenContent identity/text hash, speaker, Work Voice binding, active Voice/master/mapping, current resolved request fingerprint, production DPD, base/final Audio projection, Video/speaker-specific RP lineage, Media purpose/source reference and technical/intelligibility review. The source plan still validates against its planning DPD; an Audio is never required to pretend that planning DPD is its production authority. Both DPD and RP snapshots are independently recomposed/refingerprinted and scoped to the same Scene/Shot/Video/turn before their lineage can select a candidate. Old same-text clips are not substitutes for current final Audio. Multiple equally current candidates are ambiguous and are not selected.

`reviewStatus=PENDING` with verified current lineage and technical/intelligibility PASS may supply **measured-duration evidence only**; the turn retains `AUDIO_REVIEW_PENDING`. The frozen `is_audio_fresh` accepted-use gate still requires review PASS. Phase A neither calls that pending clip accepted nor authorizes production reuse. Failed or stale material contributes no actual duration.

| Evidence | Coverage | Full physical feasibility | Separate budget | Placement |
|---|---|---|---|---|
| All current actual turns | COMPLETE / REALIZED | FEASIBLE or CONFLICT | NOT_NEEDED | PROPOSED only if gates allow |
| Some actual turns | INCOMPLETE / HYBRID | EVIDENCE_LIMITED | Hybrid FEASIBLE or CONFLICT | CONDITIONAL_HYBRID only if gates allow |
| No actual turns | INCOMPLETE / PLANNING_ONLY | EVIDENCE_LIMITED | Estimate-only budget, explicitly labelled | BLOCKED |

`requiredMinimumDurationMs` describes the active evidence mode. `fullRealizedRequiredMinimumMs` is null until coverage is complete. Neither a hybrid fit nor technical review proves artistic quality.

## Budget and visual constraints

The required minimum is pre-hold + complete speech durations + all planned transition holds + minimum post-hold. Reallocation consumes extra actual Video duration first, then the planned post-hold surplus above its minimum. The versioned rule is `VIDEO_DELTA_THEN_POST_SURPLUS_V1`; it introduces no second timing-policy entity. No other slack is currently declared flexible.

Every semantic reaction remains intact. A counterfactual compressed-reaction calculation may explain a conflict but can never become a proposal. Overflow emits `TIMING_CONFLICT`, null proposed windows and `NOT_READY` review status. It never trims Audio, changes speed, changes dialogue/DPD, overlaps turns or extends Video.

Head, gesture and visible-pause windows remain evidence. They never become speech anchors. A known observed-speaker visibility start can block an incompatible ON_SCREEN_SPEAKER proposal; the helper does not invent a replacement onset. Mouth UNKNOWN cannot establish artistic support. Mouth ABSENT is QUESTIONABLE. Artistic compatibility remains SUPPORTED, QUESTIONABLE, CONFLICTING or UNKNOWN, with production review required for every proposal.

Candidates are limited to missing/stale Audio, duration-estimate drift, demonstrated Shot-duration shortage, compression-driven Shot-segmentation review, and timing observability. They are review leads, never automatic upstream fixes. This implementation has no evidence to diagnose dialogue length or abnormal Audio realization from duration alone.

## Validation and reuse

Contract validation rejects unsupported versions/extra fields, corrupt fingerprints, missing/duplicate/reordered turns, incorrect evidence authority, invalid duration, wrong budget/slack arithmetic, negative or incomplete windows, overlap/reaction compression, minimum-post violations and unauthorized acceptance fields.

Call `validate_dialogue_reconciliation(result, **current_inputs)` before reusing a saved result. It validates the artifact and deterministically replays all current inputs. Changes to the plan, canonical bindings/text, Video, accepted shot-observation RP, per-turn production DPD/RP, selected Audio, relevant candidate set or current Voice evidence invalidate prior reconciliation. Structural validation alone cannot establish current external identity.

Fingerprints include the plan, actual Video identity/hash/duration, accepted RP, per-turn current Audio material, coverage, policy and proposal. Neutral whitelisted lineage is used instead of arbitrary Media metadata. No host, temporary URL, request body, timestamp or historical anchor is added to the artifact. Sorting candidate sets and canonical JSON makes replay deterministic.

## Offline replay and boundary

From the workspace root:

```sh
PYTHONPATH=drama-plugin/plugin/src drama-mcp-service/.venv/bin/python \
  drama-plugin/plugin/integration/evaluate_dialogue_reconciliation.py \
  --fixture drama-plugin/plugin/tests/fixtures/dialogue-reconciliation-72.json \
  --output artifacts/batch7-4b/evidence \
  --historical-comparison drama-plugin/plugin/tests/fixtures/dialogue-timing-72-evaluation.json
```

The optional historical comparison is read only after reconciliation has been produced. It cannot affect its bytes or fingerprint. The current real fixture yields A PRESENT/4571ms, B PRESENT/4107ms, complete REALIZED coverage, full physical FEASIBLE, minimum 10478ms, slack 564ms and B's proposed window 5871–9978ms. Artistic compatibility remains UNKNOWN and user timing review remains REQUIRED.

There are no provider calls, Domain writes, acceptance endpoints, new MCP tools, services or database entities. STOP BEFORE TIMING ACCEPTANCE / AVSYNC / FINAL SHOT REBUILD. The existing 72 Final Shot remains dialogue-incomplete until a later user-approved phase accepts timing and rebuilds it.
# Batch 7.5 audio provenance input compatibility

The feasibility and placement algorithm remains unchanged. Reconciliation can
consume a current `DPD_AUDIO_PROJECTION` request produced before the new Video,
with exact canonical text, DPD, Voice/master/mapping and physical Audio lineage.
It must not invent a video-conditioned authority or a future RP dependency.

For an explicitly frozen video-conditioned clip, callers may provide its actual
source Video in `audio_source_videos_by_spoken_content` together with its actual
production RP. Both source identity/hash and Shot/Work scope are validated.
Omitting the explicit source retains the existing requirement to match the target
Video. This does not accept visual compatibility or timing: the new target Video
and newly observed RP remain mandatory and make old reconciliation stale.
No Audio metadata is rewritten to pretend it was produced from the new video.
