# Route-owned character and action expression

CG heroic expression ≠ live-action expression. Narrative identity does not confer visual amplitude.

## Contract and ownership

`contracts/expression.py` defines `CharacterExpressionProfiles`: shared `characterCoreProfile` (identity, personality, historical position, story facts, source pins) plus independent `liveActionExpressionProfile` and `cgExpressionProfile`. Select exactly the effective Work/sequence route; missing branch fails, never fall back. Do not copy CG shape, camera or acting prose into live-action. The Work stores current bundles in `characterExpressionProfiles[character]`; revisions and fingerprints bind the chosen character and route. Neither bundle implies an approved reference.

`RouteStyleContract.visualLanguage` distinguishes LIVE_ACTION_REALIST / REALISTIC_CG / HEROIC_CINEMATIC_CG. The last two belong only to stylized_cinematic_cg. Leave legacy unbound archives unmodified. A newly declared expression language must use route-owned templates, not the legacy casting wrapper.

Live action uses real human proportions, achievable actor expression, wearable equipment, executable actions and restrained motivated camera. Its schema has no heroic/exaggeration fields and caps action at cinematic. Never infer a live-action amplitude from a CG version of the same person. Historical facts can transfer; references, morphology, performance amplitude and approval cannot transfer automatically.

CG separates grounded articulation, material physics, gravity and equipment function from authored shape and presentation. `heroicExaggeration` is restrained (ordinary, low amplitude), elevated (moderate designed emphasis), heroic (distinct proportion/silhouette/presence), or legendary (rare character/occasion). `silhouetteStrength`, `physicalPresence`, `facialIntensity`, `costumeIconicity`, `kineticPotential`, `cinematicScale`, `martialAura`, `imperialPresence` express separate choices, not a universal multiplier. REALISTIC_CG caps exaggeration at elevated and action at cinematic. No default promotes every character in a heroic film. Author concrete face/body/costume/posture/camera/actionSignature in the selected branch; archetype is an interpretation source, not deterministic physiognomy.

## Casting

DESIGN_NEUTRAL displays proportion/clothing readably. HERO_CASTING is CG-only, requires HEROIC_CINEMATIC_CG and heroic/legendary. It uses sculpted volumes, character-specific silhouette and an authored heroic composition, never actor-audition prose plus a CG suffix. Keep full body/head/feet/hands/weapon readable; For HEROIC_CINEMATIC_CG, use an explicit low-angle hero composition, three-quarter orientation and motivated depth while keeping the entire design visible. A complex battle poster is not a casting proof. Character distinction and presence precede conventional attractiveness; neutral dominance need not be an angry expression.

`expression.casting_expression` has independent positive templates. `full_body_casting` binds the new bundle to formal Work and existing single-candidate authorization/ledger. New expression profiles replace legacy body/face and full-body spec styling prose; only source profile/plan fingerprints are reused. Author the visible decisions in profile.design. Route rendering/material/boundary remain explicit. Prefix forbidden drifts as prohibitions, never bare positive prompt fragments. Providers transport the compiled intent unchanged. No provider owns intensity policy.

## Director, Action, Camera, Shot

`ActionExpressionBinding` binds shared core, selected profile, immutable source beat fingerprint and `DirectorExpressionDecision` for Work/Scene/Shot. Director chooses grounded/cinematic/heroic/extreme_heroic by scene function and rhythm. This is amplitude/weight/momentum/presentation, not casualty or violence level. Quiet/routine scenes cap at cinematic; extreme_heroic requires a scoped climax and character envelope. An ordinary soldier's declared cap remains independent of the hero's cap.

Action authors anticipation → acceleration → impact → follow-through → environmental reaction, with support, grip, whole-body load, contact and recovery. The Director decision pins Action and Camera sources; camera choices serve authored force and space (tracking, push, impact response only when motivated), never permanent shake/speed ramps. A signature distinguishes whole-body power/momentum/dominance from light sword acrobatics. Preserve plot events, participants, hits and outcomes exactly; no magical shockwaves, luminous weapons, weightless flight, invented mass casualties or equipment that cannot function. Physical plausibility does not require all CG movement to be small.

Shot projects approved records, cannot escalate intensity or invent new choreography. `CinematicShotSpec.expressionDirection` is optional and absent on legacy snapshots; when present its scope and source beats are checked. Formal canon freeze also verifies current Work route and character bundle. Provider-neutral execution brief and Host cinematic projection retain the envelope and all source beats, applying the expression only to its named character. Natural-language choreography still requires causal and historical review; hashes protect the source events, not semantic truth of arbitrary prose.

## Continuity and controlled validation

Keep route-tagged candidates pending user review. Only user-approved representation can enter canonical character references; later image/video providers reuse it rather than redesigning the person. A one-image authorization does not authorize video, further candidates or another character. Stop after the first retained result, including a visually imperfect result.

## Final visual compilation (R3)

For HEROIC_CINEMATIC_CG, FullBodyCastingSpec.modeVisualIntents explicitly supplies DESIGN_NEUTRAL and HERO_CASTING descriptions for bodyProportion, facialIntensity, silhouette, pose, camera, costumeIconicity, environmentEnergy, kineticPotential and weapon. These are owner-authored realizations of the same character core, not new expression levels or automatic anatomy inferred from personality. Existing R2 profile design is source material to reconcile, not extra prose to concatenate after the mode decisions. Legacy spec costume/weapon/posture/lighting summaries remain source metadata on this path; modeVisualIntents is the executing source.

casting_visual_compiler.compile_heroic_visual_intent turns all nine existing heroic fields into visible prose, combines the selected mode intent with the unchanged core, framing, rendering, materials and historical boundary, and returns character offsets plus source paths for every paragraph. Bare expression JSON is not the final prompt. Missing mode intent or known contradictory positive phrases fail before paid reservation. Contextual neutral gaze, normal joint articulation and restrained embers remain valid; the narrow text check is not a universal language validator.

Before submission, retain final-compiled-hero-casting-prompt.txt and prompt-source-map.json, inspect the exact final prompt, and verify provider prompt equality. Test actual mode contrasts and field-to-prose changes, not only metadata presence. LIVE_ACTION_REALIST and REALISTIC_CG cannot enter this compiler. A prior download/storage failure must be recovered or the durable completion path verified before another paid candidate; recover an existing job without re-generation.


### Approved amplitude range and ownership

Generic HEROIC_CINEMATIC_CG controls amplify authored structures; they supply no default gender, age, body shape, martial identity, palette, clothing, weapon or camera angle. Explicit `CastingArchetypeProfile` traits describe dramatic relations, never one person's anatomy or equipment. `config/casting-archetypes.json` is an opt-in library, not a fallback. Character core, route expression and mode intents belong to the instance.

An optional `ApprovedVisualTargetRange` pins the user's directive and reference Media hash, positive amplitude traits and negative drift traits. It is STYLE_AMPLITUDE_ONLY, with identityAdoption=false. No exact face, garment motif, equipment, pose, cloth direction, placement or color-layout copying. A range applies only to its named character and HEROIC_CINEMATIC_CG route; it cannot upgrade REALISTIC_CG or enter live action. Work must hold the exact range and archetype before execution. The target's approval source bytes are checked at reservation.

Each compiled paragraph includes sourceLayer, sourceLayers, source paths, topic and text offsets. Generic expression rules selected by instance values name both layers. Camera/composition and anti-drift are topics, not untraceable ownership shortcuts. Inspect the final prompt contextually: ordinary/simple/plain may be correct for an authored role, but may not cancel its approved target. Never make role-specific prohibited wording global. Before a paid range regression, verify provider download and durable Media full-byte readback; generate only the expressly authorized count and stop. Approval of amplitude never adopts identity.

Project-scoped range and mode intent snapshots may live in `profiles/instances/<project>/<character>/`. They are explicitly selected inputs, never auto-loaded route defaults. Execution still requires exact current Work range/archetype binding. Local profile persistence is not proof of successful Work binding or provider availability.

## External character authority

Character-specific values now come from a locked Character Package through the unified read-only resolver in [Character External Driver](character-external-driver.md). Generic grammar owns vocabulary and route isolation only. Never embed character body/face/weapon/temperament in this compiler. Legacy instance profiles are experimental evidence, not approved identity. Core is shared; visual envelopes are independently authored. Missing package/route blocks new dedicated-character execution.

## Embodiment boundary

Character Embodiment supplies what to express and why; Expression supplies generic medium amplitude. Consume it read-only via [the embodiment contract](character-embodiment.md). No character-specific body, temperament or weapon defaults belong here. Do not infer a live-action amplitude from CG. No canonical image is required for embodiment authoring.
