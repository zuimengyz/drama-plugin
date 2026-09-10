# Cinematic director IR v1

`contracts/cinematic.py` defines `VisualBible`, `CinematicShotSpec`,
`PerformanceBeat`, `BehaviorAnchor`, secondary motion, environment interaction,
stability rules, reference duties and execution demands. `visual/cinematic.py`
resolves inheritance, validates canon, emits explanatory review findings, seals
the existing creative result and projects a neutral execution brief. This is a
source-pinned artifact, not a new domain entity or state machine.

Authoring remains a Host creative task. Validation cannot infer all historical
meaning or act as an artistic approval. The same creative lifecycle supplies
Host review and revision. Null/omitted BehaviorAnchor is valid; explain when no
added activity is needed. A simple Shot may contain one continuous action beat.
Holds and overlaps are explicit; state equality catches declared continuity
contradictions, not every semantic contradiction in natural language.

## Source and visual inheritance

Pass the real Work/Script/Episode/Scene/Shot envelope chain. `narrative_source`
pins creative fields, excluding unrelated production, Media and finishing indexes.
Exact bound Scene words/speaker/order and Shot plannedDurationMs are checked at
freeze. Optional `context.dpdSnapshot` is validated with the existing DPD composer
and bound speaker/Scene, then pinned as `upstreamPerformance` in the frozen
artifact. This keeps temporary DPD lineage separate from the formal narrative
fingerprint; silent Shots do not invent DPD. The Host preserves its objective,
tactic and boundaries while authoring observable performance. Existing Cinematic
Intent belongs in the supplied narrative context.
Do not replace it with another emotion authority. No speech or media processing
is performed.

The Work VisualBible base plus sparse Episode/Scene/Shot overrides produces a
resolved effective view and fingerprint. Omitted keys inherit, arrays replace,
empty arrays clear, null and unknown keys fail. The artifact keeps the base and
overrides for recovery; each Shot uses the resolved view without pretending that
the entire bible must be copied into a provider prompt.

Suggested storage uses the existing creative revision and
`Shot.content.creativeArtifacts.cinematicDirection`; a Work-level base can use
`Work.content.creativeArtifacts.visualBible`. This run only writes local stable
IR artifacts. It does not mutate existing Shot direction, adoption or Media.

## Handoff into V2-06

New direction-aware routes set `requirements.creative_schema=cinematic-shot-v1`
and `requirements.cinematic_directions[target]` to the frozen artifact; existing
`shots[target]` still names the formal Shot. `qualify_route` checks all target
directions before input preparation. `save_route` refreshes formal canon.

After actual mode/inputs have been selected, place `selection_handoff(frozen)`
in the existing `Requirements.frozen_creative`. `validate_requirements` checks
the frozen spec, scope/duration and exact projection. `qualify` exposes director
demands and scoped evidence: unknown acting/motion proof stays LIMITED_TRIAL;
a documented failure of a HIGH demand excludes that candidate. No model scoring
or second price/selection system is introduced. Reference roles are duties,
not template slots; the original reference caps and role checks still apply.

The existing Host `compile_request` consumes the frozen neutral `motion_prompt`
through its existing validation path. Its actual adapter length and exposed
parameter limits remain valid. A long neutral brief must stop there for an
explicit future adapter projection, not be silently truncated or shortened by
this Core. There is no claim that every model accepts this neutral text unchanged.

`visual.production._route_frame_gate` rejects a video decision whose director
artifact differs from the route. Revision uses existing route revisions and
requalification; old records remain unchanged. Legacy routes without this schema
retain compatibility for recovery and adopted output. New authoring uses the
director node; this is not retroactive restaging of past media.

The offline `skills/cinematic-direction/scripts/direct_shot.py` takes context,
draft, visual resolution and Host review files, writes validated/frozen IR and
the selection handoff, and always reports submissionAllowed=false. It imports
no client, uploads no reference and creates no production stage.

## Review boundaries

Shot Stability Contract specifies permitted variation and forbidden divergence;
it is not a Negative Prompt. Reference role validation rejects a portrait/look
reference mislabeled as opening-state authority. Timeline/identity/text/role
errors are structural failures; repeated movement or absent optional detail
produces a contextual finding with a small revision suggestion. Host meaning
review checks historical fidelity, prop causality, camera purpose, dynamic
expression and motivated environmental feedback. Offline PASS never means
generated image quality, cost reduction or artistic adoption.
