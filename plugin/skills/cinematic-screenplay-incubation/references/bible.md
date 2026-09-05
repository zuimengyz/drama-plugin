# Dramatic Bible as local structured state

Keep one compact JSON/YAML artifact alongside drafts. It is temporary creative context,
not a new Domain entity, database, universal schema or another canonical dialogue store.
For a resumed task read this artifact plus the specific changed draft/scenes. A scene ID
links its creative state to the readable body; do not duplicate all dialogue in the Bible.

Use these small sections; omit irrelevant optional detail rather than padding:

- `historicalGrounding`: sources keyed by ID; event claims with ID, actor/time/location,
  cause/motivation/knownInformation/constraint/decision/consequence/evidence/certainty;
  ordered cause links, timeline/geography constraints, adaptationPosition and forbidden
  contradictions. Disputed readings retain alternatives, never silently collapse.
- `direction`: scope, thesis (centralQuestion/conflict/audiencePromise; tragicMechanism only when applicable),
  POV, story/episode jobs, tension/emotional curve, narrativeTexture, a few visualMotifs.
- `characters`: stable speaker-keyed behaviorModel, invariants, capability limits,
  desire/fear/belief/blindSpot, textualVoice and sparse performanceGuidance.
- `relationships`: relevant power dimensions, changing dependence/trust and evidence
  boundary; no claim of invented psychological state as historical certainty.
- `sequence`: scene order, owner/goal/obstacle/tactic/counterTactic/turn/exitHook,
  dramaticDelta, nextCausalLink, input and output state, intentional offscreen transitions.
- `ledger`: initial state; per-scene state changes; knowledge receipts and false beliefs,
  audience disclosure; foreshadow setup/status/expectedPayoff/actualPayoff/expiry.
- `review`: dimension results, findings, revision history and freeze status.

For war material add only relevant `warDramaturgy` and `armyBehavior` under direction.
No required Scene/Shot counts, numeric personality scores or universal timing targets.

## Replayable convention for the optional checker

The checker consumes JSON with `sources` and `claims` inside historicalGrounding;
`characters` keyed by speaker; sequence scenes with `id`, `inputState`, `outputState`,
`receipts` (speaker, information ID, beforeBeat, channel), `decisions` (speaker, beat,
uses IDs), and `knowledgeIn` mapping speakers to information IDs. State transitions
between scenes are declared as `entryChanges` with `reason`, `key`, `value`; this allows
offscreen travel without pretending teleportation. First scene input equals ledger.initialState.
Only record state facts that later scenes depend on; unknown is an explicit value.

`review.findings` carries id/problem/severity/layer/evidence/recommendedRevisionScope,
and resolved status. `review.rounds` records round number, finding IDs, changedScopes,
before/after scene-body SHA-256 maps. Freeze marks the reviewed revision; a severe
unresolved issue prohibits FROZEN. The checker catches record contradictions, not
whether the record matches good drama or credible history. Always read the actual body.

## Ownership and freshness

History changes → recheck its causal descendants, dependent character interpretations
and relevant scenes. Character invariants change → recheck that person's scenes and
relationships. Information receipt changes → recheck dependent decisions and later
ledger state. Dialogue wording changes → review voice/subtext and performance guidance
for that line; preserve unaffected scene bodies. Scene turns change → recheck next
input and episode rhythm. No rule says every change regenerates the whole Work.

On explicitly requested domain persistence, reviewed Work/Script/Scene facts may use
their existing open content through their owner entrypoints. Do not persist this whole
working Bible, rejected draft, reviewer notes or fabricated database IDs as domain data.

## Optional meta control for new work

Under `direction.meta` keep loadProfile, capabilityUse, narrativeAperture, povContract
and subjectiveLens together. Existing V2-01 artifacts without meta remain readable;
do not invent retrospective POV decisions to migrate a frozen work. New complete
incubations use the [meta conventions](meta-dramaturgy.md).

Reuse `direction.episodeArchitecture` for episode rhythm and anchors; annotate sequence
scenes with episodeId, scene POV and their explicit working-set selection. Character
elasticity belongs beside invariants. Reuse review findings/rounds for dependency
analysis; no new global timeline, schema or service. [Working sets](working-sets.md)
explain the optional deterministic projection/checker convention.
