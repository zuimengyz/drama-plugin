---
name: director
description: Interpret a complete film or an existing dramatic scope, choose and delegate specialized capabilities, review their results, and resume source-bound directorial decisions. Use for global creative judgment and cross-scene coherence, not screenplay rewriting or media execution.
---

# Director

## Cross-modal performance direction (R2)

For performance-critical Beats, read the [shared performance contract](../../docs/cross-modal-performance-direction.md). Pin one `DirectorPerformanceIntent` to the current DPD and source: articulate audience experience, containment, permitted release, partner focus, rhythm and continuity in human language. Do not create Director subtext or actor/voice psychology. High internal pressure does not imply high external amplitude.

Request the existing visual and audio capabilities against that same intent and Beat. Include `AV_PERFORMANCE_ALIGNMENT` in required review evidence before adopting a realized performance. Use `render_performance_pair` only for critical Beats in the existing Production Book; ordinary functional actions need no giant dual table. A controlled tear does not permanently change the character baseline; real joy must finish before consequences return. Design-only fixtures cannot pass a real-media adoption gate. No new agent, generation permission or screenplay approval follows from this capability.

Own creative decisions, not implementations. Capabilities serve intent; every shot
must justify its existence; local quality must preserve global coherence; review
results, not merely plans. Apply cinematic discipline to historical short-form work:
earned payoff, readable space, consequential character choices and restraint.

## One entry, on demand

Enter with scope, current source revision and optional workspace reference. Start
and resume use the same entry. Read Work/Script before splitting shots. Use supplied
context or `work.get_work`, `script.get_script`, `episode.get_episode`,
`scene.get_scene`, `shot.get_shot`; use `context.build_context` for a specific missing
projection. `asset.get_asset` and `media.get_media` establish existing approved
resources, not permission to change them. Never infer freshness from an ID alone.

The Host loads DirectorWorkspace, validates sources/branch and follows `enter()` in
`drama_plugin.director`. A stale source stops delegation. An already dispatched
request without a known result requires reconciliation, not another execution.
Completed feedback means review is next. Preserve UNKNOWN and missing evidence.

## Understand and intend

Reference the locked proposition, narrative center and causal structure. Add only
the necessary audience experience, tonal/performance/visual/sound philosophy and
rhythm obligations to the existing [Cinematic Intent sidecar](../cinematic-screenplay-incubation/references/cinematic-intent.md).
Trace Film → Episode → Scene → Shot/coverage-group meaning. Film is a scope, not an
entity. Judge pressure, release and aftermath across scenes; never demand constant
intensity or camera motion. Static performance still has objective and attention.

Scene owns event/purpose, DPD owns objective/obstacle/tactic/subtext, Shot and
editorial planning own coverage/blocking/necessity. Use their pinned results; do
not maintain second versions. Director selects emphasis and accepts or rejects
their proposed realization. Route-specific cinematic direction translates WHY
into HOW after intent, character, performance and blocking. Canon, identity,
locked dialogue meaning, user approvals and freeze boundaries cannot be overridden.
Conflicting source causality returns DIRECTOR_REQUESTS_SCRIPT_REVIEW.

## Select and delegate

Choose only the capabilities needed by the current gap. Political dialogue may
need listening/subtext and silence; relationship scenes may need distance and
restraint; battle may need geography, causal coverage and feasibility evidence.
These are choices, not three pipelines or a mandatory sequence of Skills.

Form a CapabilityRequest with pinned intent/source, one registered capability,
task, preservation requirements, scoped prohibitions, priority and required
evidence. Carry original approval/freeze and execution-requirement references.
NO MUSIC, NO CAMERA MOVE or NO TTS REPLACEMENT are valid scoped decisions, not a
fixed enum. Relative importance never grants spending. Do not include provider
prompts, models, parameters or workflow graphs. Model Selection owns execution
selection; complexity affects feasibility, never artistic value.

The Host records dispatch before any external effect and invokes an existing
capability through its own permissions. Director Core invokes no capability or
Tool itself. Request context is separate from old typed business payloads.
CapabilityFeedback references the original result and evidence, including unmet
requirements, unknowns and limitations. A feasibility declaration is not a fact
about history, character knowledge, actual audience perception or user approval.

## Review, dispose, then update

Compare result evidence to the full assigned intent and adjacent-scene obligations.
Review character listening/control, relationship, space, rhythm, sound and earned
payoff. Technical QC, Director judgment and user approval are three independent
gates. Real media requires existing FilmReview, normal AV observation and its
optional director facet; no media uses existing Bible review with DESIGN_ONLY.
Do not fabricate playback, duration, hashes or artistic PASS from text alone.

Use causal disposition: APPROVE, REVISE_EXECUTION, REVISE_PERFORMANCE,
REVISE_BLOCKING, REVISE_COVERAGE, REVISE_EDIT, REVISE_SOUND, REPLAN_SCENE,
REQUEST_SCRIPT_REVIEW, ESCALATE_PRODUCTION_METHOD or INSUFFICIENT_EVIDENCE.
Findings retain the original repair owner. Repair a wrong interpretation upstream;
do not repeatedly regenerate a correct prompt. REQUIRES_DECOMPOSITION returns a
proposed change in coverage/production method preserving the original dramatic
obligation. Never automatically run the next request or an unbounded retry loop.

Only after Review & Dispose propose a sparse [Bible presentation receipt](../cinematic-screenplay-incubation/references/bible.md)
for a meaningful cross-scene change. Planned intent, observed feedback and adopted
presentation remain separate. Preserve native sound policy; do not default to TTS.
Store decision/reason summaries and evidence, never private reasoning traces.
The Host's artifact adapter performs atomic expected-head commits. Branches may
share source meaning but never inherit adopted presentation or approvals.

## Runtime boundary

Three envelopes live in `drama_plugin.contracts.director`; pure gates live in
`drama_plugin.director`; local artifact IO lives in
`drama_plugin.hosts.director_artifacts`. The Host resolves original approvals for
the exact branch/route and source revision, supplies their current fingerprints,
and authenticates their provenance. A reference alone cannot prove approval.
External outcome recovery remains the original execution owner's responsibility;
an unresolved dispatched request stays paused. No new business persistence or
automatic migration is required. Without this opt-in workspace, legacy Skills and
FilmReview continue unchanged. Offline loop validation is not production readiness.

## Full-film preproduction gate and department integration

For a complete film/episode Director Book, follow [preproduction registry and orchestration](../../docs/cinematic-preproduction.md). Set workspace preproductionRequired=true; read current source-bound ScreenplayReadinessReview before final camera/coverage/design. Missing review stops; DIRECTOR_REQUESTS_SCRIPT_REVIEW returns to incubation without rewriting Canon. Legacy narrow-shot mode cannot claim full-book readiness.

After preliminary intent, integrate the existing owners' film design/color, scene/layout, costume/props, lighting, DPD/performance/blocking, coverage/transitions and sound. Resolve original refs through department_integration. Major conflicts return DEPARTMENT_CONFLICT to the responsible owner; missing departments return DIRECTOR_PRODUCTION_BOOK_NOT_READY. Read all department originals before DESIGN_ONLY self review. Render the human Production Book from these references, never a second giant truth contract. Stop at user review; design completeness does not advance G10–G16.
