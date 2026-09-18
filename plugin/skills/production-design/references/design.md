# Authoring and handoff

Use `contracts/production_design.py`: CharacterVisualSpec, VisualAuthority,
FirstAppearanceContract, FactionVisualSystem, LocationDesignSpec and VisualMotifSpec.
These are typed open-content values, not new entities. Body/face subfields are
optional; a brief should explain distinguishing choices, not fill a template.

HistoricalCanonPolicy retains claim/source/classification/limits. Apply the same
policy to costume, location and motifs. A recovered artifact from one polity or
period is comparative evidence, not proof of another's exact uniform. Unsupported
story-changing additions remain hypotheses outside adopted Canon.

ProductionDesignContent stores a typed spec, semanticKey, revision, provenance,
validation and usageMode. Use PROJECT_DERIVED and CANDIDATE for a project proposal.
APPROVED_DESIGN needs approvalEvidence. Only a stable reuse reason justifies Asset
storage; one scene's dirt, injury and held item remain CharacterState. Text-only
OTHER Assets use no referenceMediaIds. An actual casting image later belongs to a
separate physical identity lifecycle.

`production_design.design_handoff` includes the exact content fingerprint and
historical policy fingerprint, with CharacterState outside stable material.
`verify_design_handoff` detects changed stable traits or constraints;
`validate_reference_design` requires an approved design fingerprint in the
resolved physical Asset. A candidate can be inspected offline but cannot enter
production as a silent replacement. A design revision changes the fingerprint;
old frozen Shots and existing image references remain recoverable.

Use cinematic language selectively for shot/camera interpretation; it does not
repair unsuitable casting. Do not automatically persist every draft or create
more images to test a text contract.

For an explicitly authorized casting reconciliation, use `CastingReconciliation`
to state population/regional direction, apparent-age range, hair, observable
face/body proportions and avoid conditions. Keep this user-directed search profile
separate from the unchanged formal CharacterVisualSpec. `casting_briefs` consumes
the source-pinned asset-resolution handoff and identical `CastingTestConditions`;
only each candidate's bone-structure direction varies. That legacy reconciliation
contract is a single-person test, not a universal casting sequence. For a staged
role search or relative scale claim, use performance-casting's role-neutral artifacts;
they permit declared reference people and a shared-plane scale proof. Do not stretch
the legacy additional_people=0 contract to represent a three-person proof.
Provider-specific projection belongs to the Host (`hosts/casting_projection.py`),
not this skill. Audit every compiled projection before spending; an audit PASS
proves field propagation and equality, not visual adherence. Review the actual
images before any shortlist costume fit. Neither shortlist nor fit permits formal
reference replacement or video without the user's explicit casting decision.

## Screen appeal and candidate reconciliation

Author the positive casting target before exclusions: apparent age, distinctive
face/body relationships, temperament and why a viewer wants to keep watching this
particular person. “Not an idol” does not mean “ordinary, unremarkable or old.”
Young authority may include confidence, pride and controlled physical ease. Name
the intended personality; a permanent frown cannot substitute for it. Evaluate
neutral face/body suitability independently from lighting, armor and background.
Only then test how costume and blocking realize the character's social position.

A user-directed search-profile revision can express this new target while keeping
its source CharacterVisualSpec immutable. Explicitly resolve ambiguous old wording
in the candidate brief; do not silently strip prohibitions from a frozen prompt.
Derive period, regional and stylization exclusions from the approved Work evidence
and visual route. Contemporary hair, European medieval dress or mythic imagery
are mismatches only when they contradict that particular world or declared mode.
Do not copy a specific performer or IP design. Preserve screen appeal within the
current character and historical boundary. Candidate review remains separate from user selection.
