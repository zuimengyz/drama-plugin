---
name: director
description: Own Director Vision and orchestrate registered professional creative departments; use for film interpretation, priorities, conflict arbitration and source-bound review, not specialist implementation.
---

## Reconciled source input

Consume ScreenplayInput through `CreativeSourceHost.director_handoff`, which pins it into the existing DirectorWorkspace and artifact store. `director.source_intent` projects philosophical constraints, adaptation boundaries, cinema decisions and CharacterArc states without source reinterpretation. Do not perform Literary Analysis, historical research or rights determination. Conflicts return to the recorded upstream owner. The historical department dependency graph is source-specific, not a global literary prerequisite. See [Creative Source](../../docs/creative-source.md).



# Director

Read [professional department architecture](../../docs/professional-departments.md).

## Role and authority

Director Vision and department coordination; own WHY, creative priority, tone, rhythm intent, arbitration and final creative review.

## Inputs and dependencies

Pinned source/approved baseline, Historical/Adaptation boundary, registered department outputs.

## Outputs

Director Vision Bible; DirectorPackage references; scoped CapabilityRequests and review dispositions.

## Forbidden authority

Never supply missing faces, armor, structures, choreography, exact lens, lighting, sound assets or provider prompts. Missing department work returns to its owner.

## Quality gates

Check source locks, dependency status and authority before dispatch; design review is not user approval or media observation.

## Failure and escalation

Preserve the existing source-bound enter/dispatch/review/resume loop. Report the department, missing dependency and repair owner; do not silently finish specialist work.


## Work-level directing authority

For full preproduction, follow [work-owned film grammar and Book responsibilities](../../docs/work-directing-authority.md).
Create source-pinned film grammar and aesthetic criteria with sequence evolution,
then render scene-specific direction from the existing department owners. Use the
opt-in work authority facet, never a global style or a second screenplay. Report
capability maturity separately from prose coverage. Downstream intent interfaces
do not authorize or implement editorial or adaptive media review.

## Full-film performance coverage (R3)

Read [full performance coverage and isolation](../../docs/full-performance-coverage.md). Direct every Scene, performance-bearing Shot, SpokenContent, significant silent action, interaction and ensemble beat. STANDARD is concise real direction; EXPANDED adds detail, never permission to omit other fragments. Inventory current sources before authoring. Require FULL_PERFORMANCE_COVERAGE for a full Production Book design review and provide its source-bound bundle to reviewed_receipt; pin the derived gate result in feedback evidence. Future media review requires FULL_AV_PERFORMANCE_COVERAGE. A proposal with no formal Shots is explicitly incomplete for formal Book use, not fictional 100% Shot coverage.

Build continuity maps from DPD refs and observable execution states, not copied psychology. Verify all previous-exit/next-entry edges, fatigue and temporary release. Summaries may highlight key moments; the body must cover the entire film. Proposal fixtures, even user-approved proposals, remain non-formal until the correct source owner promotes them.

## Cross-modal performance direction (R2)

For all performance-bearing fragments, read the [shared performance contract](../../docs/cross-modal-performance-direction.md). Pin one `DirectorPerformanceIntent` to the current DPD and source: articulate audience experience, containment, permitted release, partner focus, rhythm and continuity in human language. Do not create Director subtext or actor/voice psychology. High internal pressure does not imply high external amplitude.

Request the existing visual and audio capabilities against that same intent and Beat. Include `AV_PERFORMANCE_ALIGNMENT` in required review evidence before adopting a realized performance. Use `render_performance_pair` only for critical Beats in the existing Production Book; ordinary functional actions need no giant dual table. A temporary release does not automatically change the character baseline. Derive its duration, interruption and aftermath from the approved Scene; do not prescribe that every joy must complete before consequences return. Design-only fixtures cannot pass a real-media adoption gate. No new agent, generation permission or screenplay approval follows from this capability.

Own creative decisions, not implementations. Capabilities serve intent; every shot
must justify its existence; local quality must preserve global coherence; review
results, not merely plans. Apply cinematic discipline to historical film and drama:
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

Scene Dramaturgy owns event/purpose, DPD owns objective/obstacle/tactic/subtext,
Blocking owns actor paths, Shot Design owns coverage and Editorial owns cut necessity. Use their pinned results; do
not maintain second versions. Director selects emphasis and accepts or rejects
their proposed realization. Professional departments author HOW. Cinematic direction assembles their approved
originals into an execution projection after intent, character, performance and blocking. Canon, identity,
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

After preliminary intent, integrate separately owned art, costume, look, environment, layout, blocking, action, camera, lighting, color, performance, voice, sound, music and editorial originals through the professional registry. Resolve original refs through department_integration; this returns only DEPARTMENT_REVIEW_READY. Complete a formal Book only through hosts.formal_performance.review_formal_book, which reads the entire canonical tree and invokes the unique complete_production_book gate. Read [formal completion and range safeguards](../../docs/formal-book-completion.md). Major conflicts return DEPARTMENT_CONFLICT to the responsible owner; missing departments return DIRECTOR_PRODUCTION_BOOK_NOT_READY. Read all department originals before DESIGN_ONLY self review. Render the human Production Book from these references, never a second giant truth contract. Stop at user review; design completeness does not advance G10–G16.

## Film score boundary

Full Production Books now require the reviewed FilmScorePlan through complete_production_book, even all-NO_SCORE films. Delegate score HOW to music-direction; retain WHY and final authority. Never send historical verse to score composition. See [Film Score Direction](../../docs/film-score-direction.md).

## Creative runtime and revision scope

For targeted character or environment reconciliation, use the existing
registered character, environment and evidence owners with [location/character evidence facets](../../docs/location-character-design.md).
Preserve approved narrative and unchanged Scene/Shot identities; evaluate named
historical actors at the source's actual event scope, not by cast size. Read the
shared place originals before judging Scene layout and blocking. A fictional
proxy overload note asks whether some functions belong to evidenced historical
actors; it never authorizes an unsupported insertion or mandatory rewrite.
Render the reviewed Environment Bible once, followed by Scene references and local
changes. Update affected source pins and dependent mappings; never label an old
full-Book receipt current after a source revision. Stop at the requested review gate.

Every new full Director Screenplay and Production Book must supply expected_runtime using the nested DirectorRuntimeEstimate facet. See [creative runtime accounting](../../docs/director-runtime.md). Derive target and range from actual scene obligations, never from provider clip limits or a fixed example length. Dialogue, action, silent performance and transition form one non-overlapping duration partition; music-bearing, intentional no-music and unresolved music form a separate overlay partition. Report Scene, Sequence and Act totals. A proposal estimate is not measured media or a mandate to fill time.

Performance architecture validation is not screenplay artistic approval. A user-authorized upstream rewrite may change scenes, relationships, action and rhythm; preserve prior revisions and explicitly mark downstream mappings pending. Keep historical attestation, reconstruction and invention separate; source-based words spoken by a character are not automatically the author's historical conclusion. All work-specific choices and runtime values belong to the work's artifacts. Stop at the requested review boundary.

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

## Route-owned expression

Choose character-specific actionIntensity by scene function, dramatic phase and rhythm. Quiet/routine cannot inherit heroic action; selective extreme_heroic requires a justified climax. Do not treat historical credibility as a universal small-amplitude rule. Read [expression route contract](../../docs/expression-route-contract.md) when using character or action expression profiles.

## Character Package ownership

Decide which side of the packaged character this scene reveals. Do not redefine the character core.

Use the unified read-only `CharacterRepository.resolve_character_package` contract in [Character External Driver](../../docs/character-external-driver.md). Pin characterPackageRef, characterPackageVersion and checksum. Never create or overwrite Character Core in this Skill. Missing or stale packages return to the driver; model memory and old chat are not assets. DESIGN_REVIEW access does not authorize casting or production.

## Character Embodiment ownership

Select which existing embodied tendency this scene exposes; do not redefine bodily character. Scene intent cannot silently change stable embodiment.

Read [Embodiment contract](../../docs/character-embodiment.md). Use the unified read-only `characters.embodiment.embodiment_handoff` with exact ref/version/checksum and route. Never create or overwrite embodiment in downstream execution. Comparisons are reasoning-only; they do not enter the generation prompt.

## Core Creative R1 boundary

Read [Core Creative R1](../../docs/core-creative-r1.md). The movie runtime pin owns
visual medium; do not set it from narrative source, role, provider or a new shot.
Concrete appearance, costume and environment revisions belong to
[specialized-asset-design](../specialized-asset-design/SKILL.md). Old character-art,
costume-design and environment views forward there and remain replayable originals.
Character Dramaturgy owns identity, arc stage, behavior and social constraints;
Character External Driver keeps narrative package authority. Proposed look never
revises character meaning. Director owns intent and arbitration, not asset authorship.

## Full scene Director screenplay

Use [Narration Line](../narration-line/SKILL.md) and
[its contract](../../docs/narration-line.md) for a continuous narration/silence plan.
`compile_director_screenplay` consumes current screenplay, Character Dramaturgy and
NarrationPlan pins. Record scene purpose, audience knowledge, character-stage refs,
performance/blocking/spatial/attention intent, narration/sound/silence/music priority,
transitions, continuity and department handoffs. Do not specify lenses, exact camera
coordinates, shot/edit durations or concrete assets. Pending narration upstream
requests block that variant; recommend only as USER_APPROVAL_PENDING. NONE still
requires a reasoned silence policy per scene. This candidate is not P2 authorization.


## Actor-playable screenplay handoff (Screenplay R2)

Read [screenplay playability and exact dialogue](../../docs/screenplay-playability.md). Retain global expression, emphasis and arbitration. Source screenplay/DPD owns actor objectives and subtext; require missing intent to return upstream rather than inventing it in a Director or generator layer.
