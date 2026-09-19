# Work-owned film grammar and director production book

The Director creates the Work's grammar, not a global camera style. Read the entire
current screenplay, meaning deltas, provenance, performance, score and design before
authoring. Each rule needs a narrative cause, applicability, concrete realization,
exception and ending condition. Sequence states identify perceptual ownership (not
necessarily a first-person camera), changing spatial/movement/scale relations and
the reasons they change. Do not prescribe heroism, silence, war or a runtime by default.

`contracts.film_grammar.WorkDirectingAuthority` is an opt-in design sidecar. Reference
it through existing DirectorWorkspace.intent_refs and CapabilityRequest.intent_refs;
source freshness uses existing SourcePin handling. Work/Script content and their
owners still own story and meaning. Existing DirectorDepartmentPacket remains the
department index. There is no ProductionBook database entity or parallel Shot plan.
The human Book aggregates original refs and work-authored direction, organized by
dramatic priority, with a responsibility index instead of repeated empty fields.

Account for story/provenance, dialogue, performance, blocking, camera, action,
environment, ensemble, design, costume continuity, lighting, sound, score,
transitions, runtime and generation intent. An omission needs an applicability
reason and owner; it must not hide an unfulfilled production obligation. Every scene
must show what changes, who acts, where they stand, why the camera attends, what the
world continues doing and what the next scene inherits. Key groups declare purpose,
subject, information, movement, hold/exit and blocking/performance/sound dependencies.
Use the existing CinematicShotSpec, SourceSoundIntent, DPD, LightingScript,
CostumeState, FilmScorePlan and runtime contracts when formal source binding exists.
Do not invent formal Shot IDs, line IDs, observation receipts or department approvals.

The aesthetic constitution contains positive preferences, exclusions and contextual
tests. Explain why an attractive image can violate this Work's meaning. Its rules
belong to the Work sidecar and are never loaded as defaults for another Work.

`EditorialIntentHandoff` and `AdaptiveIntentHandoff` describe later inputs only.
`AestheticPairwiseReviewContract` is a future evidence payload, not a new review
entity: its eventual results can be pinned in existing CapabilityFeedback.evidence_refs,
with observations retained in FilmReview. Its schema does not implement comparison,
playback, editing, surprise handling, repair or adoption. No new runtime consumer is
registered. A future consumer must validate candidate scope, actual evidence and every
constitution rule reference; current structural validation does not establish these.

Separate DESCRIBABLE, CONTRACTED, ORCHESTRATABLE, PRODUCIBLE and OBSERVABLE. A valid
sidecar proves only structure; a Skill reference proves conditional discoverability,
not automatic Host execution or qualified Provider output. Long takes, crowds and
complex contact may remain unqualified despite precise direction. Report the installed
runtime separately from source implementation. Keep formal Book completion at the
existing canonical-source gate; a complete design proposal is not formal readiness.

## Optional intent priority, spatial continuity and phase readiness

Use `contracts.directing_continuity` as referenced design facets in the existing
intent refs. Examples are evidence, not defaults. Neither objects nor departments
have a fixed priority: the Work declares each intent at its actual scope.

P0 INVIOLABLE protects approved source, historical boundaries, identity, key
relationships and necessary continuity. P1 DRAMATIC CORE carries action, goals,
relationship change, causal space and required receiving performance. P2 DIRECTORIAL
FORM may be substituted by a form that still satisfies this Work's grammar. P3
AESTHETIC ENRICHMENT may be reduced before higher obligations. The Work can elevate
any particular form or object when it carries dramatic meaning. Never infer a tier
from a noun. `DirectorIntentPriority` declares protected/degradable intent IDs, ordered
protect/sacrifice lists, explicit sacrifice-before and never-sacrifice-for pairs.
An allowed substitution changes realization, not approved meaning. Exhausted options
or contradictory source requirements mean STOP_AND_REPORT_CONFLICT; this interface
makes no retake or production decision.

`SpatialContinuity` declares primary axis, projected screen/entry/exit directions,
subject relations, crossing policy and reset anchor. Preserve approved spatial
relationships across coverage. A direction change must be visibly motivated or
re-established: a visible camera/subject crossing or a newly legible master may do
this. Stable axis is not an absolute prohibition on crossing. Labels and coordinates
are Work decisions, including for still conversation and walking scenes.

`PhaseReadiness` separates required authority, binding, runtime and installation
states using category/required_state records. Its result summarizes declared evidence;
it is not an authenticated gate runner. MET needs matching state and evidence;
UNKNOWN never clears a blocking requirement. The responsible Host must authenticate
approval, exact source bindings and source/cache fingerprints before proceeding.
Identity uses a Work-bound stable intent ID plus separately versioned fingerprints;
headings alone do not bind intent. Rebind, install and fingerprint operations must
preserve approved language, dialogue, actions, grammar, score placement and aesthetic
criteria byte-for-byte where copied. A source conflict means STOP_AND_REPORT_CONFLICT.
No new default style, entity, consumer, tool, migration or editing system is added.
