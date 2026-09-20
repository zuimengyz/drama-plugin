# Reusable locations and character evidence

> For current department authority and authoring, read [professional departments](professional-departments.md). The composite schemas below remain backward-compatible representations, not ownership grants for new packages.

Character Art owns stable appearance; Environment Functional Design owns spatial
places, and Environment Art owns their screen appearance under Director intent.
Scene owns dramatic events; Layout and Blocking own placement and movement.
Camera owns the view; Shot Design owns coverage. These optional facets extend
the existing preproduction path; they add no top-level Skill, entity matching,
business table, media call or approval authority.

## Environment authoring and consumption

Use `contracts.location_design.LocationDesign` for a reusable place, not one copy
per Scene. Give it an ID, revision, extensible `location_type`, permitted Scene IDs,
historical basis/classification/unknowns, dramatic function, macro geography,
terrain/ground, structures/boundaries, zones/landmarks, entrances/exits/routes and
sight lines. Design scale/density, activity/logistics, material/texture/props,
time/weather/light/color, camera and blocking affordances, action constraints,
acoustics, continuity, future visual requirements and forbidden assumptions.
Routes contain known zone IDs; human prose explains how and why they are used.
Functional dimensions are design choices unless the cited evidence establishes
them. `location_type` is open text: a camp, palace, street, fortification or future
setting is supported, never automatically inserted into a story.

A nested tent or gateway can name a parent location. A route uses an ordered list
of distinct places; separate a ford, fork, wetland and high ground whenever they
impose different action or continuity constraints. Reuse the same high ground in
an arrival and later battle, or the same shore before and after departure.

Persist source-pinned originals in the existing local Director artifact adapter.
`FilmProductionDesign.location_design_refs` indexes `LocationDesignRef` values
(location ID and exact artifact SourcePin). The Scene packet's `environment_refs`
holds ordered `SceneLocationBinding` values. Use either the new refs or the old
inline `location`, never both. `SceneLocationOverride` permits transient time,
weather, light, population, ground, damage and temporary obstacles, with a change
reason and continuity note. It cannot redefine zones, routes or stable structures.
A structural change needs a new base revision and affected references.

`production_design.resolve_location_design` verifies the ID, fingerprint and
Scene scope, then returns the base and delta separately. `department_integration`
resolves every film-owned place, checks usage against scene refs and validates
parent identity/cycles. Missing, stale or out-of-scope originals fail; neither the
resolver nor a rendered Bible implies production approval. A LocationDesign may
also use the existing `ProductionDesignContent` LOCATION_DESIGN candidate/handoff
when long-term reuse warrants it. Asset creation is not required for Phase I.

Render one Environment Design Bible from these originals before Scene prose;
each Scene lists its Environment refs and local changes without copying the whole
place again. Scene-specific camera, acting and sound execution remain in place.
Future Art/visual planning consumes the same originals and tests the declared
visual requirements only when production is separately authorized.

## Historical character identity and coverage

The existing `HistoricalCanonPolicy.historical` marks a historical setting's
design constraints; it is not a person's historical identity. An original person
can and should retain that setting policy. Use the evidence facet exclusively for
identity and scene attestation; do not cast a boolean policy into an identity label.

`CharacterVisualSpec.evidence` is `CharacterEvidence` from
`contracts.character_evidence`. It records historical status, identity kind,
source basis, dramatic functions, historical authority, fictionalization boundary,
Scene refs and an assessment for each placement. Historical identity and historical
action are different claims. A documented person can have reconstructed private
behavior or an unresolved later fate; identify these limits explicitly.

Documented identity needs IDENTITY evidence; documented scene presence needs
SCENE_PLACEMENT evidence at that exact Scene. Original/composite people remain
DRAMATIC_RECONSTRUCTION, cannot claim documented placement and cannot acquire
historical authority. Names never trigger lookup, merging, aliasing or promotion.
The contract checks the declaration and scope, not the truth of a historical text;
the author must read the source and the Director reviews the inference boundary.

For coverage, build `CharacterCoverageReview.documented_scene_actors` from actual
evidenced actions in the selected story, then decide INCLUDE,
EXCLUDE_WITH_REASON or UNRESOLVED for each. Do not set a minimum cast size or infer
that everyone from the period belongs in the scene. `review_character_coverage`
requires explicit inclusion evidence, preserves justified exclusions and reports
unresolved coverage. Film opt-in pairs `character_visual_refs` with
`character_coverage_ref`; the existing department gate checks both and checks the
Scene layout's named participants against their allowed placements.

When an invented person carries five or more declared distinct functions, the
lightweight review emits FICTIONAL_PROXY_OVERLOAD with NOTE severity. This is a
prompt for human judgment, not a semantic measurement or hard failure. Consider
whether evidenced actors should carry military decisions or information, while
keeping a useful ordinary observer. Record why remaining functions are accepted;
do not evade review by renaming equivalent functions or erase all fictional roles.

## Compatibility and revision

All facets are opt-in. Absent new fields preserve old serialization and hashes;
legacy inline designs still validate. Typed additions do not auto-migrate sources
or infer evidence for old characters. For a targeted revision, preserve baseline
text and unaffected IDs, pin the changed Scene/Shot material and rebind only the
affected department outputs. An old full Book receipt proves only its own source
revision. New design-only evidence never replaces user artistic approval,
ProductionDesignFreeze or a production authorization.
