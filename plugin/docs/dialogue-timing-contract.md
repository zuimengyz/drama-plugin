# Dialogue Timing Planning v1

`DialogueTimingPlan` is a deterministic intermediate artifact for **one Shot,
before video production**. It answers when each whole canonical spoken item is
planned to happen. It does not determine motivation, delivery, identity, mouth
motion, actual performance, mixing or accepted placement. No database, CRUD,
provider, persistent timing entity or additional service is involved.

## Input authority

`dialogue_timing_context(scene, shot, dpd_by_spoken_content)` resolves
`Shot.content.spokenContentBindings` in **array order**, starting sequence at 1.
The existing binding format remains unchanged. This v1 consumer gives that array
an explicit ordering interpretation; it never sorts by Scene array order, name,
ID or DPD map order. Missing/unordered bindings fail `DIALOGUE_ORDER_REQUIRED`.
Each item must resolve uniquely in the parent Scene; speaker identity comes from
that canonical item's `speakerKey`, already bound in the Work. No visual Asset,
Voice, VisualPerformanceBrief or RealizedPerformanceSnapshot is required.

Every bound item needs one valid, recomposable `DPDSnapshot` with matching
Scene, spoken item, actor and speaker. Existing DPD contracts are unchanged.
Additional snapshots outside this Shot are rejected. A `REACTION` coverage
binding still refers to the same whole audible item, not a second silent turn.
Cross-Shot slices/overlapping coverage and multi-Shot scheduling are not inputs.

The existing positive integer `estimatedDurationMs` is used unchanged as a
**planning estimate**. Its authority is Scene authoring, including the existing
language/rate heuristic and reviewed delivery assumptions; it is not measured
TTS duration. No central executable estimator was found in the AS-IS audit.
Because the canonical convention already requires estimates, v1 reports
`DURATION_ESTIMATE_REQUIRED` if one is missing, or `INVALID_DURATION_ESTIMATE`
for zero, negative, boolean, noninteger or string values. It does not fabricate
a character-rate estimate. Supply a reviewed estimate upstream before retrying.

Only `Shot.content.plannedDurationMs` supplies a target. Missing target stays
`null`; the plan then reports required duration without asserting target fit.
Invalid targets fail. Prose duration, actual Video duration and Audio duration
cannot supply or override it.

## DPD semantics, then milliseconds

The planner deliberately does not interpret arbitrary natural language through
an emotion dictionary or a growing keyword classifier. The existing Shot Design
Agent judges adjacent DPD turns and creates the small internal `TransitionIntent`:

- `contextFingerprint`: SHA-256 of `dialogue_timing_context()`;
- `transition`: `OPENING`, `IMMEDIATE_RESPONSE`, `SHORT_REACTION`,
  `DELIBERATE_REACTION`, or the rejection sentinel `OVERLAP`;
- `rationale`: concise combined dramatic reasoning, without dialogue text or ms.

This is temporary input validation, not a new versioned business contract.
For each decision, consider the preceding action and current dramatic action,
objective, tactic, relationship, authority, internal activation, external
control, continuity/change and transition trigger together. Opening defaults
to readable establishment; only an explicit immediate-opening interpretation
permits zero pre-hold. An immediate answer takes the turn **after** the previous
line ends. Speech that must begin before it finishes is `OVERLAP`, which fails
`OVERLAPPING_DIALOGUE_NOT_SUPPORTED`; never relabel it to hide the limitation.

`plan_dialogue_timing()` validates context fingerprints and applies one numeric
policy. It performs no LLM calls, random sampling or semantic reinterpretation.
Same Scene/Shot/DPD, reviewed intent and policy produce exactly the same plan.
The semantic judgment itself is an auditable Agent decision, not a claim of
deterministic natural-language understanding. Missing intent fails
`TIMING_INTENT_REQUIRED`; changed context fails `STALE_TIMING_INTENT` and requires
new semantic review, not blind fingerprint restamping.

## Platform policy

The tiny internal `DialogueTimingPolicy` is frozen and rejects unknown fields.
These values are **current platform planning policy**, not film-industry standards:

| Decision | Milliseconds |
| --- | ---: |
| Normal pre-dialogue establishment | 500 |
| Explicit immediate opening | 0 |
| Immediate response / minimum inter-turn separation | 100 |
| Short reaction | 350 |
| Deliberate reaction | 800 |
| Minimum post-dialogue hold | 500 |

Bands must strictly increase; all nonzero holds are positive integers. There is
no tolerance, speed adjustment, random offset, silence deletion or automatic
estimate inflation. The opening turn has `transitionHoldMs=0`; its pre-hold is
accounted for once in `preDialogueHoldMs`.

```
start[0] = preHold
end[i] = start[i] + canonicalEstimatedDuration[i]
start[i+1] = end[i] + reactionHold[i+1]
minimum = lastEnd + minimumPostHold
```

If target is sufficient, remaining budget goes to the final hold. This is an
explicit conservative policy choice, not optimized artistic pacing. A very
long target may therefore yield a long closing hold that needs creative review.
If insufficient, return `status=CONFLICT`, `diagnostic=TIMING_CONFLICT`, and
`recommendedMinimumShotDurationMs`. Keep all speech and reaction demand intact;
overflow windows describe the requested budget and cannot be used as a valid
target-fitting schedule. Only upstream review may revise dialogue, split or
extend coverage. The planner never modifies its inputs.

## Contract and reuse validation

`contracts/dialogue_timing.py` defines only `DialogueTimingPlan` and
`DialogueTurnTiming`. JSON aliases use camelCase; schema is
`dialogue-timing-plan-v1`. Turns retain canonical IDs, speakers, 1-based sequence,
planned start/duration/end, transition/hold/reason, estimate authority and source
fingerprints. They never retain the spoken text itself.

Plan fields retain Scene/Shot identity, planning Shot/source and policy hashes,
target, turns, holds, minimum and total duration, PLANNED/CONFLICT, diagnostic and
fingerprint. Strict integer/time arithmetic, contiguous sequence, duplicate
sequence/item detection, non-overlap, pre/post/reaction accounting, target
status and canonical fingerprint are validated on deserialization. Unknown or
provider/actual-media fields are forbidden at plan, turn, intent and policy boundaries.

`validate_dialogue_timing_plan(plan, ...)` must be used before reuse against
current sources. It first revalidates even a mutated model, then replays and
compares the complete plan. A self-consistent hash alone cannot prove that an
artifact belongs to the requested Scene/Shot or remains current. Wrong identity,
new policy, changed inputs or tampered output fail reuse validation.

## Fingerprint material

Reuse `sha256_canonical` (sorted dictionary keys, significant array order).
The plan hash covers all serialized material except its own hash, including:

- version, Shot identity and **planning projection** fingerprint;
- ordered canonical item fingerprints, speakers, full DPD fingerprints;
- unchanged duration estimates, reviewed intent/context and rationale;
- policy version/hash, target and materialized output.

The planning Shot projection includes ID/parent, binding order, target and a
whitelist of narrative purpose, input/output/required transition, action/blocking
and visual entry/exit state. The small Scene context includes purpose, objective,
opposition, stakes, turn/beats and narrative state. Camera/framing/lens, free
production metadata, Video/D1 hashes, timestamps, jobs, random IDs and previous
USER_REVIEW placement are excluded. No whole open Shot content hash is reused,
since it could silently pull post-production dependencies into planning.

Changed text, order, speaker, DPD, estimate, planned target or policy invalidates
the plan. Some changes can leave milliseconds equal while changing lineage; a
DPD change requires semantic review before a different transition may be chosen.

## Offline replay and evaluation

From the plugin root with its dependencies available:

```sh
PYTHONPATH=src python integration/evaluate_dialogue_timing.py \
  --fixture tests/fixtures/dialogue-timing-72.json \
  --output /tmp/dialogue-timing-review \
  --evaluation tests/fixtures/dialogue-timing-72-evaluation.json
```

The runner writes the plan before loading the separate evaluation file. The
real fixture contains current read-only Domain Scene/Shot, the unchanged prior
refusal DPD and an explicitly documented new transient proposal DPD. Historical
Video duration, D1 duration and old anchor exist only in the evaluation sidecar.
Tests prove changing those evaluation values cannot change plan bytes.

## Planned versus accepted

`DialogueTimingPlan -> Video production -> actual Video -> future reconciliation
-> accepted timing -> AVSyncPlan -> Final AV` is the intended future relationship.
Only the first stage is implemented here. A planned start is not a new accepted
`timingAuthority`, and this batch makes no changes to `AVSyncPlan`, Final Assembly,
Audio/Visual projections or DPD. Lip sync, phoneme/viseme alignment and mouth
retargeting are outside scope. Stop before Batch 7.4B.
