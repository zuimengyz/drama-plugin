# Shot Production Rules

Use these rules for visual production of one Shot or a continuous Shot sequence. Treat Asset and Media as visual facts, these rules as production behavior, and the runtime as tool execution only.

## Sequence context

Establish one Sequence Context for continuous Shots in the same Scene, and reuse it until authoritative context changes. Derive facts only from Work, Script, Episode, Scene, Shot, stable Asset, stable Media, and explicit business state. Treat generated output as review evidence, never as domain truth.

Organize image preparation and legacy MCP context using the following facts. For official video, persist their source-pinned projection in the shared Work-owned Continuity Pack described by the [video contract](../../../docs/video-provider-contract.md); never create a provider-specific identity copy:

- **Stable Facts**
  - Character: identity, age, face, hair, beard, and general physical appearance.
  - Costume: base costume, color, material, major silhouette, and active variant.
  - Scene: location identity, spatial structure, historical material, and major fixed objects.
  - Sequence lighting continuity: independently approved time/source/relationship/exposure/atmosphere bounds. These are Lighting-owned continuity facts, never portrait identity or automatic reference inheritance.
  - Props: only continuity-significant ownership, presence, state, and location.
- **Locked Facts**: facts that must remain stable across the sequence.
- **Allowed Delta**: justified pose, gaze, expression, body direction, natural folds, framing-dependent background visibility, and scale changes.
- **Shot-specific Delta**: the action, composition, camera intent, and explicit state transition required by the current Shot.

Do not classify an explicit state transition as drift. When one Shot shows a held bowl and the next says it is put on the table, lock the bowl's identity but apply the new location and hand state as the next Shot's delta. Only unjustified changes violate continuity.

## Reference planning

Consume the source-pinned Reference Plan authored by reference-strategy. The currently inspected image adapter has `MAX_REFERENCE_COUNT = 3`; this is an execution limit, not authority to remove required proof. Official video uses the registry's actual per-mode reference limits and must consume every required continuity reference; it may not omit one to fit a cheaper model. Legacy MCP video retains its inspected compiler limits. Build candidates only from stable Asset identity with suitable stable reference Media. Never use a temporary provider URL, prior provider filename, unexplained local file, web image, or unpersisted proof-of-concept output.

Discover candidates from:

1. named visible characters that require identity continuity;
2. a Shot-focal unique prop whose appearance must remain stable;
3. the Scene or location when spatial continuity matters;
4. an active independent costume variant;
5. other secondary stable visual objects.

Prefer a `MASTER_CHARACTER_CARD` or the current contract's equivalent for every clearly visible named principal. If a key visible character lacks suitable stable Asset-plus-Media identity, record `MISSING_STABLE_REFERENCE`, name the missing entity, mark the plan incomplete, and stop visual execution. Do not silently ignore the character or create an unreviewed substitute. Return the missing fact so the existing asset-resolution capability can address it without copying that capability here.

Bind every REQUIRED reference duty from the Reference Plan. If the verified adapter cannot bind all required duties, return `REFERENCE_CAPABILITY_CONFLICT` and route back to reference-strategy and video-model-selection; do not silently truncate to three. PREFERRED candidates may be omitted only under the upstream plan’s priorities, with the reason recorded. Do not create a second priority list in Shot Production. Record:

- selected references and stable IDs;
- omitted candidates;
- missing stable references;
- selection rationale;
- final count and completeness.

Do not pad a plan to three. A single-character Shot whose identity and environment require two references must remain at two.

## Spoken source integrity

Before producing any physical media for a Shot with `spokenContentBindings`:

1. resolve every `spokenContentId` against the owning Scene's canonical `spokenContent`;
2. reject missing IDs, copied Shot-local dialogue bodies, unrecognized coverage intents, or non-numeric `plannedDurationMs`;
3. require the Shot or contiguous coverage group to pass `DURATION_FEASIBILITY`, deduplicating a spoken item covered by multiple Shots in the same group;
4. pass only the resolved fields needed by the provider, including visible performance intent for `ON_SCREEN_SPEAKER`, reaction intent for `REACTION`, and delivery context for `OFF_SCREEN` or `VOICE_OVER`.

Providers consume the reviewed Scene source. They never edit its text, identity, provenance, duration estimate, or stable ID. A visual Asset is required only when visible identity continuity requires it; absence of one does not invalidate dialogue or narrator identity.

## Shot delta compilation

Translate Shot semantics into visual constraints instead of forwarding literary text unchanged. Produce this compact structure:

1. Stable Identity
2. Stable Environment
3. Action State
4. Composition Constraint
5. Camera / Framing Intent
6. Required Visual Evidence
7. Forbidden Visual Outcome
8. Continuity Constraints

For contrastive or negative semantics such as “do X but not Y” or “B rather than A,” express both visible positive proof and prohibited readings. Require measurable separation, placement, posture, gaze, hand state, or object state where relevant; forbid contact, occlusion, posture, or composition that would visually imply the rejected action.

Treat `shotType` as a strong composition source. For an over-the-shoulder two-person Shot, require foreground shoulder or partial back, specify primary-subject placement and camera relationship, and forbid a generic front-facing side-by-side two-shot.

Translate camera motion into representative static key-image intent:

- push-in: use the tighter destination framing and stronger subject pressure;
- tilt-up: preserve the focal object-to-character relationship or choose the representative endpoint;
- rack focus: establish foreground/background separation and the intended attention center.

Do not ask one still image to depict elapsed camera movement.

## Prompt conflict review

The Host reviews each newly compiled provider-facing prompt before request sealing
and reservation, and repeats the review after changes to prompt sources, technical
unit boundaries, references or model projection. Read the actual final wording,
including applicable negative instructions and audio controls, against the exact
current source versions. Do not assess only the input Bible or an earlier draft.

Check applicable relations rather than isolated keywords:

- **State and time:** identify whose state each sentence describes and when it
  applies. An open object that is later closed is a transition; requiring it to
  stay open throughout the same closing action is a conflict. Separate entry,
  current action and exit states, and inherited background from new events.
- **Action and objects:** prerequisites, hand/tool contacts, load/support, object
  identity and start/end consequences must fit the intended action. Distinguish
  an object from its parts; motion cannot silently replace its geometry or create
  another part. Keep the approved causal order and physical task.
- **Space and camera:** check simultaneous spatial, framing and motion demands
  against current blocking and camera sources. Distinct planned phases or a
  designed cut are not simultaneous camera conflicts.
- **Sound:** bind contact and vocal sounds to the current visible/off-screen
  event, speaker or established environment and its timing. Distinguish restrained
  performance, quiet background, local silence and a request for no sound. Do not
  invent continuous noise, fixed loudness or new music to remove an ambiguity.
  Check native-audio parameters against the selected sound plan; presence of an
  audio track is not a claim about its audibility or synchronization quality.
- **Scope and inputs:** check the selected unit's opening, ending and actual
  reference duties. Do not replay completed events, advance future ones or claim
  an unobserved reference state. Missing physical evidence remains unverified.
- **Repetition:** merge wording only when subject, time, scope, meaning and duty
  coincide. Keep necessary per-phase constraints, exact canonical speech and
  independent requirements even when they share a noun or similar words.

For each material conflict, retain the conflicting spans, their source/phase,
why they cannot coexist and the proposed correction. The Host autonomously
clarifies timing, separates inherited state from action and removes genuine
duplication within existing professional execution-expression authority. Revise
the corresponding source projection/Package as a new version and recompile;
never patch a sealed FinalPromptArtifact, append an alternate raw request or
silently drop required source obligations to make the check pass. If source
originals themselves disagree, ask the responsible existing department to resolve
that disagreement; do not rewrite the screenplay or Shot art in this review.

Review the resulting final text again and retain its exact scope, source versions,
prompt fingerprint, findings, corrections and disposition in existing preparation
or review originals/Agent Run Context. If new compilation reintroduces a conflict,
repair its responsible source or projection rather than repeating a cosmetic edit.
If no permitted repair can resolve it, keep only the affected request unsubmitted
and report the unresolved source issue; independent work can continue. Ordinary
expression repairs need no additional user approval and grant no paid retry.

After a changed prompt is ready, refresh its existing request seal and applicable
cost terms normally; old prompts, requests, results and billing remain retained.
An assessment covers only the exact final text reviewed and never proves Provider
performance, media acceptance or user adoption. No new schema, database entity,
Runtime review receipt or fixed artistic scale is introduced by this procedure.

## DPD visual projection boundary

When the run includes an authoritative `DPDSnapshot`, translate it once into a provider-neutral `VisualPerformanceBrief` before compiling the Provider motion prompt. DPD remains intended dramatic authority; the brief only expresses observable performance. Do not copy stable face, age, hair, costume, location appearance, camera scale, lens, angle, composition, or camera movement into the brief. Combine the brief with those independently owned inputs only at materialization.

Map activation and control compositionally. In particular, high internal activation plus high external control normally calls for visible tension, low-amplitude movement, stable posture, restrained head/gesture behavior, and focused gaze rather than a large generic expression. High activation plus low control may permit larger, less stable movement. Never introduce an emotion classifier, facial-expression taxonomy, gesture library, or body-language DSL.

## Per-Shot review and targeted revision

Use the normal-viewing, use-based review in SKILL.md. Check applicable core action, causality, important facts and established continuity; distinguish visible errors from unconfirmed details. Ordinary flaws pass with notes. Explain each major observation and its effect on the intended use. Do not assign severity from a category or demand literal realization of every prompt detail.

Reject the current candidate when necessary, then the Host chooses a better historical candidate or a materially changed production strategy within existing stage totals. One correction is a default suggestion, never an unrecoverable target budget. Append reassessment and planning history; do not require creative authorization or discard prior spending. Unknown facts remain unknown and prompt active observation only where relevant.

## Cross-Shot continuity review

Compare only Shots that passed per-Shot review. Check:

- `CHARACTER_IDENTITY_CONSISTENCY`
- `AGE_CONSISTENCY`
- `HAIR_BEARD_CONSISTENCY`
- `COSTUME_CONSISTENCY`
- `SCENE_CONSISTENCY`
- `LIGHTING_CONTINUITY`
- `PROP_STATE_CONTINUITY`

Require Locked Facts to remain stable, allow Allowed Delta, and require each Shot-specific Delta to be visible. Continuity is not visual duplication.

For material continuity drift, the Host replans the affected sequence while preserving core facts and user decisions. Prefer reuse and changed methods to repeating the same failed method; stage totals remain authoritative.

## Review, annotation, and persistence order

Use this order:

```text
Provider Output
-> Visual Content Review PASS
-> Identity Annotation when required
-> Media Import
```

Identity annotation is provenance or identity presentation, not Provider visual quality. Never fail visual review merely because an otherwise valid Provider output lacks an annotation.

For a DPD-directed performance video, continue after stable Media import:

```text
stable Review-PASS Video
-> controlled playback / representative frame sampling
-> accepted observable facts
-> RealizedPerformanceSnapshot
```

The Snapshot describes the actual video, not the intended DPD. Record visible expression, gaze, head/body motion, gesture, mouth-activity windows, pauses, and pre/post-speech action only when observable. Use `UNKNOWN` instead of guessing. DPD-versus-video deviation is diagnostic only: it never blocks or changes the Snapshot. A later replacement video must produce a new content hash and Realized Performance fingerprint, making any dependent final Audio stale.

## Still live-action observation evidence

Use [the shared still profile](../../../docs/still-professional-mapping.md) for executable observation validation. Its criteria refine existing QA/Review: approved requirement pin, visible region, comparison, output/reference hashes, use-based impact, hypothesis/confidence and one repair owner. No image evidence means UNKNOWN. Clean, symmetric, beautiful or unwrinkled skin is not failure; pores/roughness are not automatic PASS. Keep skin response separate from geometry and current makeup/light. Compare normal viewing usefulness, not imagined pixel-perfect anatomy. Existing FAIL-check/MAJOR-finding consistency remains mandatory; a minor defect is a note with ACCEPT/POSTPROCESS, never automatic REGENERATE. Observation metadata contains no creative replacement or generation command.
