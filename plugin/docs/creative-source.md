# Creative Source contract and execution boundary

`source.prepare_screenplay(request)` is the registered transport-neutral entry.
MCP projects it from the same registry; no host/provider creative routing exists.
Contracts live in `src/drama_plugin/contracts/creative_source.py`; the sole
validator/compiler/rights gate is `src/drama_plugin/creative_source.py`.

HISTORICAL preserves Research → Scope → Spine → Actor Hierarchy → Narrative
Authority → Protagonist → Story Architecture. Its input retains Work domain
content and the existing incubation Bible; compilation executes that Bible's
checker. Legacy Work without creativeSourceType retains historical behavior.

LITERARY uses designated artifact → LiteraryAnalysis → PhilosophicalCore →
AdaptationContract + DramaticCompression → CinemaTranslation → ScreenplayInput.
Each authored stage requires a source-bound specialist review. Compilation does
not invent missing inputs or provide artistic/legal approval. Use `review_hashes`
to bind the actual reviewed content; a hash alone is not proof a review occurred.

The literary-source-analysis owner separates SOURCE_FACT and INTERPRETATION.
Adaptation decisions are ADAPTATION_INVENTION and never overwrite source units.
Every unit is accounted for; every non-removal decision has a destination and
cinematic expression. Compression references the same decision IDs, not copied
operations. CharacterArc is owned by character-dramaturgy; Director consumes its
performance implications while Character Art only consumes continuity boundaries.

Philosophy is an interpretive question/conflict/choice/consequence/ambiguity
constraint. The canonical preference order is THEME_EXPRESSION_ORDER in the
compiler, projected to consumers. Explicit explanation/voice-over needs recorded
source/character/structure justification and a Director choice. No vocabulary
blacklist claims to evaluate dramatic quality; specialist reviews evaluate it.

Rights bind each SourceArtifact independently, including translations/editions.
PUBLIC_DOMAIN is a recorded assertion, never derived from age/author metadata.
Licensed sources need scope. Evidence, assertion owner, basis, jurisdiction and
permitted uses are required for adaptation/commercial authorization. UNKNOWN and
RESTRICTED block those uses. STUDY permits structural inspection and always
returns authorized=false. NON_COPYING_REFERENCE never supplies facts or grants
copying permission. Modern adaptation artifacts cannot be designated source truth.
The gate enforces records; it does not verify legal truth or provide legal advice.

Persist canonical camelCase `creativeSourceType: LITERARY`, `literaryPackage`,
and the exact compiled `screenplayInput` inside existing Work.content. Script
must inherit that same screenplayInput. Plugin validates on writes and Work
reads. Java retains only persistence invariants, never semantic/rights authority;
its acceptance is not a production permit. Formal production reservation
rechecks current rights for Work.content.productionJurisdiction. No migration,
media, new provider, or new credentials are required.

`CreativeSourceHost.prepare` retains originals in the existing hash-addressed
DirectorArtifactStore. `director_handoff` verifies the current Work/Script and
pins source, screenplay input and screenplay into DirectorWorkspace. Director's
`source_intent` is a read-only constraint projection; it cannot rewrite literary
analysis, rights or historical evidence. Every source-map row has an origin,
owner, package SourcePin, JSON pointer, anchor IDs and (where applicable) decision
ID. Any changed package or compiled map fails exact replay until recompiled.

Standalone literary incubation supplies creativeSourceType/literaryPackage/
screenplayInput instead of historicalGrounding. Existing knowledge, continuity,
review and working-set checks still apply. The synthetic fixture is only a
TECHNICAL_FIXTURE. Legacy media or casting is never a new literary source.

Professional registry is now explicitly source-scoped: `registry('HISTORICAL')`
preserves its exact graph and historical serialization; `registry('LITERARY')`
replaces only historical roots with a validated literary-source-input module and
literary-source-qa. `professional_host(..., source_type='LITERARY')` actually
validates that root and all dependent Bibles. CreativeBible/DirectorPackage carry
sourceType for literary artifacts; cross-source dependencies are rejected. The
module owns no analysis: it replays the same package/compiler. Generic downstream
owners remain unchanged. Historical-only field names become source-scoped names
for Literary records. Character dramaturgy must consume the approved arc; any
change returns upstream. Source type cannot be switched by a Host default.

For literary Character Bible/Character Art Bible, optional `source_authority` /
`source_identity` is the exact `{sourceUnitId, origin}` of its inherited analysis
unit, never a fresh historical status. Appearance and narrative arc authority
remain separate. Registered source tools and professional Host are offline design
boundaries; no plugin reinstall or running-service deployment is implied by edits.

An ADAPTATION_INVENTION CharacterArcState must name adaptationDecisionId and inherit its source-unit scope. A factual or interpretive stage cannot relabel an adaptation decision. Literary Character Art must consume exact arc_continuity_boundaries from those approved states.
