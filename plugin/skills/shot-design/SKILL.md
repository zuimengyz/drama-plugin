---
name: shot-design
description: Design actual shots, coverage purpose and start/end states from approved camera, blocking and action originals; use for coverage and thin Shot assembly, not camera or editorial re-authorship.
---

## Creative Source applicability

Consume the parent Script's current ScreenplayInput. Historical evidence, historical beat coverage, actor hierarchy and reconstruction rules in this Skill and its references apply to HISTORICAL. For LITERARY consume the pinned adaptation decisions, compression destinations, cinematic translation and arc stages instead; return new causal changes or source reinterpretation upstream. Shared continuity, knowledge, review and persistence gates remain mandatory. See [Creative Source](../../docs/creative-source.md). Do not use old Media or casting as a literary source.


# Shot Design

Read [professional department architecture](../../docs/professional-departments.md).

## Role and authority

Own actual shot purpose, subjects, coverage and entry/exit relation.

## Inputs and dependencies

Camera, Blocking, Performance, Action, Lighting, Sound, Editorial and continuity refs under current Scene dramaturgy.

## Outputs

Shot Bible and thin ShotAssembly; generation clip refs stay distinct from canonical Shot identity.

## Forbidden authority

Do not re-author lens/camera grammar, paths, choreography, lighting, sound or cuts; do not copy full character/set/costume prose.

## Quality gates

Coverage preserves source action and exact spoken bindings; each receiver state is reachable from its predecessor.

## Failure and escalation

Return missing specialist decisions to the owner; route infeasibility cannot change creative content.


When a scene supplies reusable environment refs, resolve the source-pinned
[LocationDesign and local overrides](../../docs/location-character-design.md)
before blocking and coverage. Keep landmarks, routes and sight lines consistent
across scenes using the same place; a local time/damage delta cannot relocate a
doorway or reverse a riverbank. Request a base-design revision from
environment-design for geometry changes. Camera affordances permit a view; they
do not prescribe every shot or authorize media generation.

## Opt-in Director authority

Shot Design retains coverage; Blocking retains actor movement and Editorial Design retains cut/hold necessity and EditorialRhythmPlan. Consume the Director request and its source/intent pins; propose realization in those existing owners and return result/evidence/limitations. Director judges global usefulness, priority and rejection; it does not create DirectorShotPlan or replace canonical blocking. A constraint that cannot be realized returns to Director for an explicit disposition; locked event changes require upstream review.


After the reviewed narrative Shot exists, hand its source-pinned action, opening,
ending, duration, exact dialogue, rhythm and cinematic intent to cinematic-direction
to assemble approved physical acting and camera originals before video model selection. Follow the
[director IR boundary](../../docs/cinematic-direction-contract.md); do not choose
a model or generate media from this Shot-authoring step.

Consume the unified `creativeRhythm` from the actual creation context before planning, even when source text is already supplied. Follow [narrative rhythm](../../docs/narrative-rhythm.md); Skills never read env directly. Pin this profile to the creative revision; refresh/resume keeps it, while a new revision reads current configuration.

Express an approved Scene through minimal necessary, narratively motivated, continuous, provider-agnostic coverage. Plan the group before individual Shots; every Shot must declare Narrative Input State, Required Transition, and Narrative Output State in addition to visual entry/exit state. Do not redesign the Scene or produce media.

For a single Shot's dialogue timing request, follow the [Dialogue Timing contract](../../docs/dialogue-timing-contract.md). Resolve the existing binding array in order, canonical speakers and estimates, and each line's DPD; use `dialogue_timing_context()` to obtain the complete adjacent-turn context. Form a transient `TransitionIntent` for each turn, pin it to that context fingerprint, and explain the combined dramatic action, objective, tactic, relationship/authority, activation/control and continuity/change basis. Choose only opening, immediate response, short reaction, or deliberate reaction; explicitly required simultaneous speech uses the unsupported overlap intent. Immediate response means the preceding line has finished; a literal interruption while it continues is overlap. Do not classify emotions or assign milliseconds. Call `plan_dialogue_timing()` to apply the deterministic platform policy and retain the plan in Agent state. Missing estimates require an upstream planning estimate; a conflict reports the minimum required Shot duration for upstream review. On changed input, review the semantics again rather than simply replacing an old intent's fingerprint. For timing-only requests, stop after the plan/diagnostics and review, before the creative persistence steps below. Planned windows are separate artifacts, never Shot binding fields, observed mouth timing, accepted AV placement, or authority to generate/mux media.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates new Shot coverage or revises existing Shots, the parent Scene and exact coverage scope, the requested visual outcome, and explicit format, duration, continuity, stable-reference, or production constraints. Identify what the camera must express about the Scene turn. Do not equate one sentence or dialogue line with one Shot automatically.

### 2. Gather Context

Assess context sufficiency before planning. Continue when the approved Scene's assigned historical beats, Narrative Input/Output State, Required Transition, purpose/action/turn, canonical `spokenContent`, spatial layout, blocking, time/environment, neighboring Shot states, and production constraints are supplied. Use `scene.get_scene` for the stable parent and `shot.get_shot` for a known `shotId`. With a known `sceneId`, use `shot.list_shots` for structural enumeration and neighboring continuity; when only a natural-language identity is known, use `shot.search_shots` scoped to the Scene when possible and judge candidates.

Use `asset.get_asset` or `media.get_media` only when a selected stable reference is needed to judge character, location, prop, wardrobe, or visual continuity. Use `context.build_context` only when required parent or existing Shot context was not supplied. Consume approved historical context rather than repeating research per Shot. If a consequential historical issue is unresolved, formulate a focused question and stop before planning or persistence so the Agent or Host can choose an existing research capability. If Scene intent, required references, spatial state, or continuity cannot be obtained or conflicts, state the blocker and do not draft or persist.

### 3. Plan

For a supplied screenplay intent handoff, apply [Cinematic Intent translation and preservation](../cinematic-screenplay-incubation/references/cinematic-intent.md). Project relevant intent from the scene set to this coverage group, retaining source, priority, POV relation and boundary obligations. Translate meaning into concrete action/composition/continuity; MUST constrains meaning, SHOULD allows a justified alternative, FREE may be discarded. Keep the full assigned-intent list for group review even when individual shots receive smaller selections.

Before drafting, read [Professional Shot Planning](references/planning.md) and the [Dialogue Layer content convention](../../docs/dialogue-layer-content-convention.md), then apply them. Create an internal coverage plan that inherits rather than repairs the Scene; define required historical/story observations, coverage strategy, Shot economy, and for each retained Shot its narrative purpose, `narrativeInputState`, `requiredTransition`, `narrativeOutputState`, subject/action with Blocking and Camera refs, reviewed editorial rhythm, positive integer `plannedDurationMs`, visual entry/exit state, continuity, references, and feasibility. When spoken content exists, decide which Shots bind each item and why as `ON_SCREEN_SPEAKER`, `REACTION`, `OFF_SCREEN`, or `VOICE_OVER`; do not copy or rewrite its text. Keep it in Agent Run Context or temporary working state. Do not call `shot.create_shot` or `shot.save_shot` to store it.

### 4. Execute Draft

Execute the strategy as complete candidate formal Shot states that together cover the Scene turn with the fewest necessary Shots. Each Shot persists `plannedDurationMs`; a Shot carrying speech persists only `spokenContentBindings[]` objects with `spokenContentId` and `coverageIntent`. A Scene item may bind across speaker and reaction Shots without duplication and remains one future audio item. Consume Camera choices that serve information, performance, spatial relation, emotion, action, or continuity; preserve screen direction, axis/eyeline, positions, action phase, performance energy, assets, props, costume, time, lighting, and ongoing motion. Simplify, split, or redesign an overloaded Shot until its action, space, movement, references, spoken load, and entry/exit states are executable downstream. The draft must not contain copied dialogue/narration text, audio timing, one-line-one-shot splitting, redundant coverage, camera labels without subject/action, test content, or scratchpad. Do not persist partial Shot drafts.

### 5. Review

When an intent handoff exists, add an Intent Preservation Matrix against actual shot IDs and sequence: PASS, ACCEPTABLE_INTERPRETATION, INTENT_LOSS, CONFLICT or N/A. Missing MUST or a conflicting interpretation blocks the group. FREE omission does not; a SHOULD alternative is judged by preserved purpose. Check the first/last effective perception and subjective-to-objective return, not just item presence. Keep user cinematic acceptance separate from record validation.

Before any write, read [Shot Review and Revision](references/review.md) and apply the entire coverage rubric. Critical checks are reported as `CHARACTER_VISUAL_CONTINUITY`, `COSTUME_PERIOD_CONTINUITY`, `PROP_STATE_CONTINUITY`, `SHOT_ACTION_CONTINUITY`, `SCENE_STATE_CONTINUITY`, `CAUSAL_NARRATIVE_CONTINUITY`, `HISTORICAL_BEAT_COVERAGE`, `FULL_STORY_ARC`, and `DURATION_FEASIBILITY` separately. Validate every binding against the parent Scene, coverage intent, absence of copied body/timing, and numeric duration. Deduplicate an item shared across a contiguous coverage group; its estimated duration must fit the group's total planned duration with playable room for action, reaction, and silence. If `Previous Narrative Output State → Current Narrative Input State` fails or an indispensable action/state is skipped, return `FAIL_NARRATIVE_TRANSITION` even when visual checks pass. Unmotivated or redundant coverage, unresolved narrative continuity, unproducible complexity, spoken overload, or failure to cover the Scene turn is critical. Mark Review PASS only when every gate passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

If screenplay and intent are correct, an intent-loss finding belongs to SHOT_PLANNING. Declare affected shots and continuity neighbors, preserve unrelated shots and all upstream text, and review the complete group after a focused correction or Host replan; no permanent per-target creative revision limit. An upstream ambiguity goes to its actual owner. A standalone requested Shot Plan can remain a reviewed local artifact without Domain writes or media production.

On Review FAIL, do not persist. Follow [Shot Review and Revision](references/review.md): Locally revise the owned coverage purpose, binding or start/end relation; route framing/angle/movement to Cinematography, actor paths to Blocking and cut timing to Editorial. Reconcile duration only against those current originals. Resolve spoken-duration conflict through reviewed coverage changes, extending/splitting Shots, reaction coverage, or an upstream Scene revision of non-`mustKeep` content; never let this Skill or a Provider silently rewrite the Scene source. Re-plan the current Shot group when coverage strategy, economy, spatial/axis logic, Scene-turn coverage, or generation feasibility fails. If the Scene lacks playable conflict/action/state change, label an upstream Scene issue instead of hiding it with camera technique. After any revision or re-plan, review the complete coverage again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft coverage exist, all critical checks pass, and the design is minimal necessary, narratively motivated, continuous, and production-ready without unresolved Scene/reference conflict. One-line-one-shot splitting, repeated coverage, missing narrative purpose or subject/action, spatial/action discontinuity, asset drift, or unproducible complexity cannot pass. Plan, draft reasoning, rejected alternatives, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Shot `content`. Persist only reviewed formal Shot results.

Use `shot.create_shot` only for a genuinely new Shot after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `shot.save_shot` immediately afterward unless a concrete revision has actually occurred. Use `shot.save_shot` only to revise an already persisted Shot because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Scene ID, string-valued shot number, optional title, and optional shot type in the create envelope; use the stable Shot ID, shot number, title, and type for a revision. Put reviewed narrative purpose, Narrative Input State, Required Transition, Narrative Output State, subject/action, department refs for blocking/camera/performance/action/lighting/sound/continuity, reference requirements, feasibility, positive integer `plannedDurationMs`, canonical `spokenContentBindings`, visual entry/exit state, and other formal Shot facts in the open `content` object. Bindings contain only `spokenContentId` and `coverageIntent`; never persist copied text, Shot-local `spokenContent`, `spokenContentRefs`, audio/subtitle timing, or aliases. These are creative content, not new persistence fields. Do not move the parent Scene ID or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Read a stable Asset/Media only when continuity requires it; do not create or resolve assets, produce media, add provider workflow/model parameters, redesign the Scene, or automatically invoke another Skill.

## Visual authority and editorial rhythm

Before coverage, read the [peak/editorial contract](../../docs/dramatic-peak-editorial-contract.md). Consume production-design's stable visual authority and the Scene's FirstAppearanceContract: frame the silhouette, costume/blocking/light hierarchy, first action and others' reactions so a caption does not carry all identity weight. Consume Editorial Design’s EditorialRhythmPlan when planning a Scene group, binding its VisualInformationBeat, CutMotivation and ReactionChain to actual coverage. Judge SingleTakeFeasibility for10s+ multi-focus passages, with staging or an alternative; never derive duration from model capacity. Set pieces need setup/escalation/reaction/payoff/aftermath functions, not a fixed shot count. Include a hero function only when approved dramatic intent calls for it; a civilian or political set piece need not heroicize anyone. Give HeroShot an earned reason and every hold a purpose; compare scale/movement/light/space/subject/silence contrasts. Check missing reactions/details/navigation, overloaded takes, pointless cuts and prolonged visual sameness. Keep alternative re-splits offline until the requested revision scope permits formal changes.

## Sequence production handoff

For multi-shot production, compose the existing coverage into the [sequence package](../../docs/sequence-production-contract.md): ordered storyboard cards, current source pins, geography, and an explicit receiver at every cut. Keep proposed subshots outside formal Canon until coverage revision is authorized. Minimum necessary coverage means no redundant shots; it does not mean placing several incompatible attention changes in one long provider clip.

For executable Sequence coverage, retain source Shot IDs and provide each receiver with ProductionClip semantics, action consequences and observable bridge criteria. Mount/rider interactions belong to the existing Bible; use the [executable sequence contract](../../docs/sequence-production-contract.md#production-design-freeze-and-executable-closure). Proposed subclips do not create formal Shots.

## Shot Transition Plan in existing editorial contract

Before full Production Book completion, follow [intended transitions](references/shot-transitions.md). Audit every adjacent shot and scene boundary for direction, axis, eyeline, motion, sound, time and space. Actual edits remain with finishing.

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

## Route-owned expression

Read approved route expression plus Director/Action/Camera originals. Thin Shot assembly may project their scope and source hashes; it cannot promote quiet beats or ordinary soldiers to the hero amplitude. Read [expression route contract](../../docs/expression-route-contract.md) when using character or action expression profiles.
