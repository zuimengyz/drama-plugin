# Character External Driver / Character Package v1

Approved Screenplay → Character External Driver → Host Design → Character Package → External Repository → read-only Character Art / Casting / Director / Expression / Action / Dialogue / Production.

No character soul in generic Skills. No production-time reinvention. Memory != Character Repository.

## Configuration and portable storage

`DRAMA_CHARACTER_REPOSITORY_ROOT` is a Plugin-owned environment setting. Blank resolves to a user data directory: macOS `~/Library/Application Support/drama-plugin/character-repository`; Linux `$XDG_DATA_HOME/drama-plugin/character-repository` or `~/.local/share/drama-plugin/character-repository`; Windows LocalAppData equivalent. Resolution does not create files. Relative roots and roots inside Plugin source/Git are rejected after symlink resolution. An external repository may have its own Git history, private permissions, distribution and license.

Structure: `characters/<project-or-universe>/<character-id>/<version>/`. Explicit versions such as v1 and v2 coexist. No `latest` resolution for a locked Work. Source snapshots live in repository-relative `sources/`; missing or changed source bytes fail recovery. Copy the repository including sources when exporting. P1 does not implement a marketplace or license enforcement.

## Contract

`contracts.character_package.CharacterPackage` exports a JSON schema using `model_json_schema(by_alias=True)`. Eleven required files:

| File | Authority |
| --- | --- |
| manifest.yaml | packageId, characterId, projectId, version, status, sourceWork, sourceRevision, sourceFingerprint, createdAt/updatedAt, supportedRoutes, publisher, license, authors, compatibility, dependencies, checksum and fileChecksums |
| core.yaml | identity, historicalRole, lifeStage, dramaticRole, personalityCore, desire, fear, belief, contradiction, decisionPattern, dramaticArc; no visual implementation |
| dramatic-identity.yaml | authorialStatement, selfImage, socialPosition, pressure, distinctiveChoices, two or more sameArchetypeComparisons, unresolvedQuestions |
| visual-expression.yaml | independently authored routes; no missing-route fallback |
| action-signature.yaml | movementCharacter, decisionTempo, powerSource, weaponRelationship, mobilityStyle, combatRhythm, recoveryStyle, forbiddenDrifts, eventBoundary |
| performance.yaml | baseline, states, relationalVariations and continuityLimits |
| dialogue-voice.yaml | syntax/rhetoric/exposure/power/relations; providerBinding=UNBOUND |
| anti-drift.yaml | character-specific avoid rules and reviewTests |
| relationships.yaml | directional power/trust/emotion/debt/fear/dependence/surface/internal relationships and evidenceRefs |
| historical-basis.yaml | documentedFacts, strongInferences, artisticInterpretations, uncertainElements, sourceRefs |
| provenance.json | sourceWork, sourceFiles with hashes, historicalSources, host, createdAt, revision, userFeedback, referenceAssets, license, authorshipBoundary, approvalEvidence |

Optional references/prompts/reviews must be manifested. Prompt caches are projections, never Source of Truth. Checksums provide integrity, not proof of ownership or cryptographic publisher authentication. Credentials and signed URLs are rejected. Status: DRAFT → DESIGN_REVIEW → VISUAL_TESTING → USER_APPROVED → PRODUCTION_READY; DEPRECATED remains readable for audits. P1 writer creates immutable versions; workflow authorization is not an OS security sandbox.

## Unified read contract

Use `DramaPlugin.characters` or `CharacterRepository(config.character_repository_root)`; no Skill-specific YAML reading. `load_character_package(ref, version, checksum=...)` verifies schema, identity, all document hashes and source snapshots. `resolve_character_package(CharacterPackageRef(...), consumer=..., purpose=..., route=...)` returns a detached READ_ONLY context containing packageId/characterId/version/status and all character sections. Consumers may change their in-memory projection, never persist it to the repository. `verify_downstream_core` rejects changed cores. The reader exposes no save/update/delete API. The separate authoring module accepts only explicit driver CREATE_VERSION authorization with source and directive hash. Existing versions cannot be replaced.

DESIGN_REVIEW may read drafts; CASTING requires VISUAL_TESTING or later; PRODUCTION requires PRODUCTION_READY. Missing package, unversioned ref, checksum mismatch, unsupported route or insufficient status blocks execution. Before an executable casting brief, bind characterPackageRef, characterPackageVersion and checksum to the current Work. A core role without a package cannot be reinterpreted silently. Archive compilation is not execution authorization.

`live_action_realist` requires REAL_HUMAN / HUMAN_PERFORMABLE / WEARABLE_EXECUTABLE. `realistic_cg` requires GROUNDED_DESIGNED. `heroic_cinematic_cg` may authorize HEROIC_GROUNDED. CG envelopes map to stylized_cinematic_cg at the existing rendering boundary. Core is shared; expression amplitude is not. Selecting a route returns only its envelope; no automatic live-action branch creation.

## Ownership

| Consumer | May decide | Must not decide |
| --- | --- | --- |
| Character External Driver | Source-bound core, distinctiveness, relationships, signatures; authorized new version | New screenplay facts or user approval |
| Character Art | Face/body/visual design within package route and core | Invent core psychology or identity distinction |
| Performance Casting | Candidate realizations and evidence | Discover fundamental identity or edit package |
| Expression/compiler | Generic route vocabulary and task projections | Own a named character's anatomy, temperament or weapon |
| Director | Which existing facet this scene reveals | Redefine who the person is |
| Action | Causal scene choreography under script outcomes + signature | Change movement identity or introduce events |
| Dialogue / Voice | Authorized exact words / delivery | Redefine language personality |
| TTS / image / video provider | Render authorized request | Own character truth |

Before screenplay approval, Character Dramaturgy still owns Character Bible authoring. After approval, the driver consolidates that source into portable packages. Contradictions go back to the source owner; a package does not supersede screenplay facts. Instance experiments and failed images are evidence only, never inherited canonical identity. Any current package's missing approval must be visible at the gate.

## Observable character layer

See [Character Embodiment](character-embodiment.md): source-bound physical reasoning is a versioned external asset between identity and Art, not a prompt or image requirement. Existing package versions remain readable and locked.
