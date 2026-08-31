# Shot Production Rules

Use these rules for visual production of one Shot or a continuous Shot sequence. Treat Asset and Media as visual facts, these rules as production behavior, and the runtime as tool execution only.

## Sequence context

Establish one Sequence Context for continuous Shots in the same Scene, and reuse it until authoritative context changes. Derive facts only from Work, Script, Episode, Scene, Shot, stable Asset, stable Media, and explicit business state. Treat generated output as review evidence, never as domain truth.

Organize the context without persisting a new schema:

- **Stable Facts**
  - Character: identity, age, face, hair, beard, and general physical appearance.
  - Costume: base costume, color, material, major silhouette, and active variant.
  - Scene: location identity, spatial structure, historical material, and major fixed objects.
  - Lighting: time of day, major source, warm/cool relationship, exposure, and atmosphere.
  - Props: only continuity-significant ownership, presence, state, and location.
- **Locked Facts**: facts that must remain stable across the sequence.
- **Allowed Delta**: justified pose, gaze, expression, body direction, natural folds, framing-dependent background visibility, and scale changes.
- **Shot-specific Delta**: the action, composition, camera intent, and explicit state transition required by the current Shot.

Do not classify an explicit state transition as drift. When one Shot shows a held bowl and the next says it is put on the table, lock the bowl's identity but apply the new location and hand state as the next Shot's delta. Only unjustified changes violate continuity.

## Reference planning

Set `MAX_REFERENCE_COUNT = 3`. Build candidates only from stable Asset identity with suitable stable reference Media. Never use a temporary provider URL, prior provider filename, unexplained local file, web image, or unpersisted proof-of-concept output.

Discover candidates from:

1. named visible characters that require identity continuity;
2. a Shot-focal unique prop whose appearance must remain stable;
3. the Scene or location when spatial continuity matters;
4. an active independent costume variant;
5. other secondary stable visual objects.

Prefer a `MASTER_CHARACTER_CARD` or the current contract's equivalent for every clearly visible named principal. If a key visible character lacks suitable stable Asset-plus-Media identity, record `MISSING_STABLE_REFERENCE`, name the missing entity, mark the plan incomplete, and stop visual execution. Do not silently ignore the character or create an unreviewed substitute. Return the missing fact so the existing asset-resolution capability can address it without copying that capability here.

When candidate count is three or fewer, select every suitable candidate. When it exceeds three, select exactly the most consequential three by the priority above plus Shot focality. Do not use a scoring framework or expand the limit. Record:

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

## DPD visual projection boundary

When the run includes an authoritative `DPDSnapshot`, translate it once into a provider-neutral `VisualPerformanceBrief` before compiling the Provider motion prompt. DPD remains intended dramatic authority; the brief only expresses observable performance. Do not copy stable face, age, hair, costume, location appearance, camera scale, lens, angle, composition, or camera movement into the brief. Combine the brief with those independently owned inputs only at materialization.

Map activation and control compositionally. In particular, high internal activation plus high external control normally calls for visible tension, low-amplitude movement, stable posture, restrained head/gesture behavior, and focused gaze rather than a large generic expression. High activation plus low control may permit larger, less stable movement. Never introduce an emotion classifier, facial-expression taxonomy, gesture library, or body-language DSL.

## Per-Shot review and targeted revision

Review only applicable dimensions, including:

- Shot Semantic Accuracy, including every required and forbidden Shot-delta condition;
- Character Identity, Age, Hair / Beard, and Costume;
- Scene and Lighting;
- Prop State and Composition;
- Anatomy / Structural Errors;
- Historical Plausibility and Modern Artifact Check.

Treat Shot-specific semantic correctness as a hard gate. Beauty or general identity similarity cannot compensate for a failed action, forbidden reading, prop state, or composition.

Generate once. Revise only after a concrete Review FAIL, and allow at most one targeted revision. Preserve Stable Facts and the Reference Plan; change only constraints connected to confirmed failures. Change the Reference Plan only when review proves it was wrong, such as omitting a key visible character. Do not regenerate stable references, replace the entire prompt, switch references without evidence, benchmark alternatives, or loop until PASS.

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

When one Shot drifts, identify the failed dimension and apply its one allowed targeted revision while preserving Stable Facts and Reference Plan. When two or more Shots would need continuity regeneration, stop with `SEQUENCE_CONTINUITY_REQUIRES_REPLAN` rather than starting a regeneration loop.

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
