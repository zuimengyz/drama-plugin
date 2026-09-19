# Coverage production formalization

Use the existing EditorialRhythmPlan optional `coverageRealizations` facet and the
three typed contracts in `contracts.coverage_realization`. Coverage identity stays
in EditorialAuthority. ProductionFormalizationState is a literal, not an entity.
No new Shot Group service, generation API or review owner is introduced.

## One bridge, existing owners

Approved editorial authority → realization policy/dependencies → reviewed
shot-design → persisted Shot and existing SequencePackage/ShotReceiver group →
CinematicShotSpec / model selection → existing production adapter → retained Media
→ lineage gate → existing FilmReview/EditorialUsability. Intended lineage never
counts as observed evidence, user adoption or a permission to spend.

`realization_handoff` verifies source pins, exact Coverage identity and intent
membership, optional activation pins, event provenance, dependency scope and DAG.
Dependencies describe final causal order, not an obligatory generation-call order.
Shared-state relations apply to their declared boundary and dimensions; they never
freeze an approved state change or forbid a motivated axis reset.

## Splitting and sharing

SINGLE_MATERIAL_PREFERRED is a preference, not one-take enforcement.
MULTI_MATERIAL_ALLOWED permits technical decomposition; REQUIRED needs more than
one planned evidence segment. UNRESOLVED blocks dependent production until the
existing owners resolve feasibility. FREE still preserves all editorial duties.
CONTINUITY_GUARDED retains the named state. PROTECTED_SEQUENCE permits multiple
materials but preserves one ordered perception with no unrelated attention break.
NO_INTERNAL_SPLIT needs specific approved evidence of indivisibility, not taste.
None of these grant a new cut permission or shorten an existing protected hold.
An invisible continuation is a proposed implementation, never proof that an actual
join works. Existing CutCondition and actual dailies remain authoritative.

DEDICATED_EVIDENCE_REQUIRED means an independently locatable range, not a dedicated
video. Shared material explicitly lists all `satisfiesCoverageIds`. Several intents
referencing one unit do not schedule duplicate production. Store one realization
row per Coverage ID. Keep optional rows NOT_FORMALIZED until the condition has a
current source-bound activation receipt. Missing essential evidence is not an
excuse to activate ornamental coverage.

## Formal Shot and generation payload

No local candidate name is a canonical ID. After existing shot-design review, use
existing `shot.create_shot`; `save_shot` replaces full content and preserves all
unrelated approved fields. Put `coverageRealization` in Shot.content, alongside
existing duration/spokenContentBindings/narrative and visual states. Include:

- `satisfiesCoverageIds`, `directorIntentRefs`, `coverageSourceFingerprints`,
  `planFingerprint`;
- `mustPreserve`, `acceptableVariation`, `forbiddenDrift`, `continuityKeys`,
  `referencePriority`, `providerModeRequirement` (capabilities, not model names);
- `coverageSegments[coverageId]`: `eventRefs` in approved order, `continuityKeys`,
  `sharedState`, `attentionBreak`, `evidenceLocator` (planned role initially).

`plannedShotRefs` resolve actual IDs; `plannedShotGroupRefs` resolve existing
SequencePackage groups and their member IDs. Group refs cannot replace real Shot
membership. Each group is scoped to its declared Coverage; shared groups may have
shared member Shots when all participating mappings declare them.

The Host reads current Scene/Shot and approved work artifacts, supplies all scene
required mappings, current source fingerprints, resolved group members and an
approval fingerprint authenticated from the approved realization revision.
`generation_handoff` validates the entire scene's active mapping, every planned
Shot, segment sequence/shared-state obligations and forbidden sharing. It returns
one entry per unique formal Shot for existing generation planning, not one per
Director Intent. Source fingerprints and review identity travel with the existing
CinematicShotSpec. Model selection resolves mode, actual references and duration;
UNKNOWN required references/capability remain blocked there. No provider is picked
by this contract; no generation happens inside the function.

## Media and dailies

After the existing durable production completion/import/get/resolve flow, retain
`coverageRealization` in Media.content with `shotRef`, `shotFingerprint`,
`coverageRefs`, `directorIntentRefs`, `sceneId`, `sourceFingerprint` from the exact
generation receipt. Retain full contentHash and the receipt artifact. Cross-scene
files need separately located Shot-bound ranges, not a single ambiguous parent.
Host verifies bytes, current sources and actual canonical parents; a free-text
claim is not authoritative. `media_handoff` compares the receipt, current Shot hash,
Work/Shot/Scene relation and lineage. Failure is R5C_OBSERVATION_NOT_AUTHORIZED.
Success only permits intended-authority handoff: load the corresponding Coverage
requirements, priority, cut/axis/DPD/variability/aesthetic source pins into existing
FilmReview. Actual ranges, observation and artistic decisions remain downstream.

## Reachability and limits

These pure functions are opt-in Host orchestration used by existing skills. They
are not new MCP tools and do not intercept every legacy raw provider API. For an
opted-in work the Host must call them before production/dailies; bypassing them
cannot produce an authorized R5-C receipt. Missing formal Shots or exact approval
blocks generation, even if policy metadata is complete. Contracts validate stated
relationships, not visual continuity in media. Legacy planning with no facet keeps
its previous serialized shape. Examples are evidence, not defaults.
