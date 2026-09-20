# Cinematic preproduction: owners, gates and source-bound evidence

> For current department authority and authoring, read [professional departments](professional-departments.md). The composite schemas below remain backward-compatible representations, not ownership grants for new packages.

This is a planning system, not a renderer or a second screenplay. Use on complete
film/episode direction and on explicitly requested preproduction reconciliation.
Narrow legacy Shot work remains compatible; it cannot claim a complete Production
Book or bypass this gate by selecting legacy mode.

## Gate registry

`drama_plugin.preproduction.GATE_REGISTRY` is the ordered registry:
G0 current formal source; G1 Screenplay Readiness; G2 Director preliminary intent;
G3 route design; G4 film production design; G5 scene visual development;
G6 cinematography and lighting; G7 coverage and transitions; G8 production book
self review; G9 user directorial review. G10 route-specific character/casting, G11 route-specific visual development,
G12 route-specific identity/art approval, G13 ProductionDesignFreeze, G14 current model
qualification, G15 production preflight, G16 user production authorization retain
their existing owners. No downstream result upgrades an earlier gate. Design
completeness is never freeze, artistic approval or spending permission.

The full-film Host creates DirectorWorkspace with `preproductionRequired=true`
and a source-bound `readinessRef`. Director `enter` and artifact-store `resume`
resolve the review before permitting delegation. Missing review stops at
SCREENPLAY_READINESS_REQUIRED. MAJOR/UNKNOWN or an unresolved significant
historical opportunity returns DIRECTOR_REQUESTS_SCRIPT_REVIEW. A fresh local
branch after upstream revision needs new source pins and review; never patch a
historical workspace or reuse an old readiness decision.

## Contract reconciliation

- Dramatic Bible/Cinematic Intent retain Canon, character meaning, choices,
  knowledge and Film → Episode → Scene → Shot obligations.
- DPD remains Scene/Beat/Line psychological authority; no new parallel psyche.
- VisualBible remains the route look. FilmProductionDesign references it and adds
  whole-film color progression, environment, costume, prop and crowd coordination.
- Reusable LocationDesign originals are optionally indexed by FilmProductionDesign;
  SceneProductionDesignPacket references them with bounded local overrides. Existing
  inline LocationDesignSpec inputs keep their serialized form. See
  [location and character design](location-character-design.md) for evidence,
  multi-scene reuse, character coverage and migration-free reconciliation.
- CostumeState extends existing transient CharacterState and references stable
  CostumeBible/CharacterVisualSpec. A new state is not a redesigned identity.
- LightingScript is the legacy representation of Lighting Design. CinematicShotSpec
  projects independently owned acting/camera originals; consume the lighting pin when
  translating the scene, without changing DPD or the stable design.
- EditorialRhythmPlan now optionally includes `transitions`; old empty plans keep
  their serialized form. New full preproduction requires adjacent coverage edges,
  or an explicit single-view omission reason. Cross-scene plans can include both
  scenes in this existing multi-scene contract; audit every episode boundary.
- PictureEditPlan and FilmReview continue to use actual immutable Media. A text
  book never fabricates observed FilmReview PASS.
- DirectorDepartmentPacket is only a source/intent/result/conflict index. Human
  Production Book is a rendered aggregation, not a new database entity.

All new sidecars use `contracts.preproduction`; intended transitions extend
`contracts.dramatic_editorial`. Immutable local artifact refs use the existing
DirectorArtifactStore, not Work/Scene/Asset writes. LocalCapabilityBridge validates
incubation readiness, production-design and lighting results alongside existing
DPD/coverage owners. CONTRACT_VALID is not a creative verdict.

## Integration and conflict review

Call `department_integration(packet, review, current, artifacts)` using resolved
originals, not copied summaries. Every scene needs design, costume, lighting,
performance, coverage and sound. Film design must cover all scene color keys;
state changes require causes and predecessor fingerprints. Unknown sources,
stale refs, wrong owner/scope/intent and incomplete transitions stop integration.

The Director must read across departments and record evidence-backed conflict
findings, including: dark costume lost against dark space/light; doorway/layout
incompatible with blocking; changed screen direction/axis without reorientation;
heroic gold contradicting a restrained film color phase. Compare actual artifact
fields, not keyword matches. Automated checks additionally detect absent motivated
light sources, scene/film color disagreement, uncaused costume resets and missing
coverage edges. Semantic judgment remains a professional review, not an NLP claim.

Return DEPARTMENT_CONFLICT with original subject refs and repair owner. Costume,
color → color-design; doorway topology → environment-design; exposure/separation →
lighting-design; movement → blocking; camera axis → cinematography; cuts → editorial-design; intention/causality →
incubation. A conflict may involve two owners; retain linked findings rather than
silently modifying either original. A resolution references fresh evidence and
reruns affected neighbors. Major conflicts prevent the book from being ready.
Missing departments return DIRECTOR_PRODUCTION_BOOK_NOT_READY. Self review must
reference all exact department revisions. G9 remains the user's own decision.

## Book and bounded work

Render: film proposition and audience path; character principles (DPD refs);
readiness/upstream disposition; route policy; film design and color script;
scene environment/layout/costume/props; performance/blocking; lighting/camera;
coverage intent, opening/ending, transition continuity; sound; production
constraints and alternate coverage; conflict dispositions; self review and user
questions. Keep departments' original pins visible. Do not dump state JSON as the
main reading experience. At most two internal design repair cycles by default;
unresolved major issues retain their owner and stop readiness, not an auto retry.

No new agents, tools, Java endpoints or business tables are needed. Visual
development belongs to the independent art departments; their owner,
inputs, revisions and handoff are the same. Independent visual-development would
only be justified by a distinct reusable authority and lifecycle, not another
name for these outputs. Future Lookdev can consume these briefs only after its
separate authorization and gates.
