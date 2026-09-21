# Character Art Visual Medium Contract

Current normative behavior is v3 (render visibility and presentation section below).
The v1/v2 descriptions document the legacy medium-only compatibility path; they
do not establish visible-filmic readiness for unspecified CG records.

`contracts.visual_medium.VisualMediumIntent` is the provider-neutral authority:

```json
{
  "visualMedium": "CINEMATIC_CG",
  "renderStylization": "VISIBLE_FILMIC_CG",
  "renderStylizationSource": "current-character-art/revision-3",
  "presentationMode": "LOOKDEV_NEUTRAL",
  "characterTreatment": "HEROIC",
  "realismLevel": "GROUNDED_STYLIZED",
  "castingMode": "HERO_CASTING"
}
```

The axes are independent. `HERO_CASTING` is legal with `LIVE_ACTION_PHOTOREAL`;
`HEROIC` never chooses a medium. New `PackageCastingProjection` and `CastingBrief`
inputs use `visualMediumIntent`. Package `route` remains the selected, pinned
package envelope key; it must agree with the medium, and the projection's legacy
`castingMode` must agree with the intent. A Work's explicit `visualMediumIntent`,
when present, must match at execution. Contract changes enter the authorization
fingerprint; they cannot reuse an old paid authorization.

## Compilation and Host boundary

Host paragraphs carry appearance, historical clothing, performance and framing
facts with source pointers. They cannot positively declare **even the matching**
CG/3D/actor-photography medium. Move these decisions into the structured intent.
Negated exclusions are permitted. Conflicting text fails instead of being erased.

`visual_medium.compile_character_art` v2 validates neutral source facts, establishes the
medium anchor first, and translates each fact in its domain before treatment, realism
and casting-mode constraints. Raw facts never precede an appended medium grammar. CG compilation
provides form, skin/subsurface/roughness, grooming, costume materials, shape design
and digital rendering. Live-action compilation supplies human performance,
photographed skin, practical hair/costume and photographic optics. The compiler
preserves ordinary anatomy, natural stubble, historical construction and authored
identity. It never infers a role, body type, equipment, composition or historical event.

## Gate and source proof

`medium_consistency_gate` detects positive medium contradictions in both directions.
Its deterministic bilingual heuristic scopes negation to clauses and resets it on
affirmative transitions. A `negative`/`core` label alone grants no exemption. An explicit rejection of the selected medium (such as `No CG` on the CG route) also fails.
CG completeness requires positive evidence across six domains after stripping
CG/3D/digital/render labels; weak labels yield WARN. The compiler emits complete
sections; the gate never adds prose. CG also requires a leading medium anchor and
medium-native positive semantics in each fact paragraph. Six-domain boilerplate
at the end, or a Host CG prefix before naked facts, is blocking WARN. Explicit
photographic skin, wardrobe-test and casting-photo affordances fail. Submission
requires PASS. These deterministic checks do not predict image quality.

`visualMediumCompilation` records compiler/version, intent, control-plane origin,
compiled constraints, emitted sections/offsets/hashes, prompt hash and gate status.
Host prose is marked `CHARACTER_FACTS_ONLY` or `LEGACY_CONFLICT_INPUT`; it is never
compiler evidence. `verify_medium_compilation` recompiles the retained original inputs, including
domain transforms, deduplication, every emitted source span and the entire receipt,
and re-runs the gate against the final prompt before
provider projection. This is deterministic provenance verification, not a digital
signature or a guarantee that arbitrary natural language or generated imagery is correct.

The provider adapter only maps compiled text and existing execution options.
`prompt_optimization=standard` and `thinking=true` remain unchanged.

## Legacy migration

`legacy_medium_intent` maps existing serialized labels without editing approved packages:

| Legacy language | Medium | Treatment | Realism |
| --- | --- | --- | --- |
| HEROIC_CINEMATIC_CG | CINEMATIC_CG | HEROIC | GROUNDED_STYLIZED |
| REALISTIC_CG | CINEMATIC_CG | NATURAL | NATURALISTIC |
| LIVE_ACTION_REALIST | LIVE_ACTION_PHOTOREAL | NATURAL | NATURALISTIC |

Casting mode is copied independently. Omitted intent on the old photographic
`CastingBrief` explicitly retains the live-action default; the old CG-only
`full_body_design` interface derives its default from its validated CG route.
Existing package files/checksums remain unchanged. Legacy matching medium prose
is labelled as conflict input and passes the same gate; it cannot stand in for
emitted medium sections. Legacy contradictory prose must be repaired explicitly.

Old full-body heroic field amplification remains a compatibility adapter for
owner-authored intensity and mode intents; generic medium compilation is shared.
The old full-body API still has its historical CG scope; live-action full-body
execution uses the package entry with an explicitly supported live-action envelope.

Compiled outputs and authorization fingerprints intentionally change. Recompile
old briefs and bind any future authorization to the new fingerprint; old missing
compiler receipts fail closed at provider projection. Do not rewrite retained
artifacts or auto-renew an authorization.

## Text verification

`tests/test_visual_medium.py` covers contracts, compilation, both conflict directions,
negation, label-stripped completeness, source-proof tampering and provider equality.
`tests/snapshots/character-medium-*.txt` pin deterministic same-facts outputs.
`integration/validate_character_medium.py --output <directory>` runs A/B/C/D through
package resolution, compilation, execution validation and request projection with
network blocked. It submits nothing and generates no media. Provider A/B testing
requires a separately authorized next phase.

## Medium-first fact contract (compiler 2.0.0)

`contracts.character_prompt.StructuredCharacterFacts` separates authored facts from
rendered prose. Each fact has id, domain, text and source pointers. Domains are form,
skin, groom, materials, shape, rendering (composition intent), and constraint.
PackageVisualParagraph supports an explicit domain. New authors should use this
structured path; legacy section dictionaries use a deterministic topic/text adapter.
No named-character rules or new anatomy defaults exist. Mixed legacy paragraphs are
compatible inputs, not a recommended authoring format.

Compilation order is anchor → form → skin → groom → materials → shape → presentation
→ treatment → realism → casting mode → source exclusions. Each domain policy leads
its translated facts; compact native labels avoid repeating full grammar per fact.
CG skin wording replaces natural-texture/photo-detail vocabulary while retaining
tone and texture variation. Costume substance/construction and physical framing
remain unchanged; the compiler selects CG material/look-development or live-action
practical-material/photographic semantics. Grounded anatomy does not select photography.

In v3, DESIGN_NEUTRAL controls baseline casting assessment only. Independent
presentationMode controls the image presentation under the selected medium. HERO_CASTING is legal in both media.
A contradictory explicit mode in source prose fails instead of silently overriding
VisualMediumIntent. Treatment does not invent mass, rank, equipment or expression.

Exact normalized clause deduplication prioritizes base facts over derived summaries.
Unique summary clauses survive; removed copies retain source aliases and the retained
section id in `deduplicatedFacts`. This is conservative lexical deduplication, not
a claim to resolve arbitrary paraphrases.

The receipt adds all four axes, inputSections, legacy adapter flag, mediumAnchor,
translatedFactSections, generatedMediumSections, deduplicatedFacts, negativeGuards
and mediumBalanceStatus. A transformed fact records sourceFactText, source pointers,
mediumTransform, transformedBy/transformVersion, span and text fingerprint. This is
replay provenance, not a signature or confirmation of upstream source approval.

Package casting, production-design casting briefs, expression/full-body compatibility
paths, visual discriminants and legacy route projections use the same compiler.
When composing intermediate compilations, reuse receipt inputSections rather than
feeding provider prose back as facts. Provider adapters remain parameter mappings.
Old v1 receipts fail v2 replay. Do not overwrite evidence or carry forward spending
authorization after a changed prompt fingerprint.

Offline regression runners: `integration/validate_medium_first.py` accepts explicit
current art, retained failed compilation and output paths;
`integration/test_medium_first_offline.py --output <json>` runs every related test
file with socket connections blocked. Neither runner executes production tools.

## v3: render visibility and presentation are independent axes

`VisualMediumIntent` adds nullable `renderStylization`, `renderStylizationSource`
and `presentationMode`. CG styles are PHOTOREAL_DIGITAL_HUMAN, VISIBLE_FILMIC_CG
and HEIGHTENED_FILMIC_CG. Non-CG media reject CG style values. An explicit style
requires a nonempty owner source and an explicit presentation mode. Legacy missing
style stays null with LEGACY_GENERIC_CG_UNSPECIFIED receipt status; it never inherits
a global visible-CG default. `revise_render_intent` creates an explicit owner revision
without changing the original. Environment consumers can reuse the vocabulary;
this implementation composes character prompts only.

Character Art owns style realization under Director philosophy. Casting consumes
that pinned contract; Production Design reviews it; Provider adapters map the
compiled text unchanged. The current project can opt in through an explicit
Character Art revision, not a compiler branch naming a Work or character.

`realismLevel` controls anatomy/weight/joints/historical physical plausibility.
`renderStylization` controls visible digital design versus near-photographic CG.
`castingMode` controls role assessment/importance. `presentationMode` independently
controls LOOKDEV_NEUTRAL, HERO_PRESENTATION or PERFORMANCE_PRESENTATION. A hero
may use neutral look development without becoming DESIGN_NEUTRAL.

Explicit revised contracts use `render_stylization.compose_domains`: one section
for identity/face, body, skin, groom, material, shape, lighting/presentation,
treatment/casting, realism and exclusions. Policies appear once per domain, with
all concrete facts underneath; no per-fact CG boilerplate. Fact spans in
translatedFactSections point into these composite sections. Compact compilation
adds no muscles, jaw, armor or unapproved pose. Photoreal CG retains fine pores,
individual strand realism, material micro-noise and near-photographic illumination.
Visible CG has six positive evidence domains: FORM_HIERARCHY, MICRODETAIL_CONTROL,
GROOM_MASSING, MATERIAL_GROUPING, SHAPE_ABSTRACTION, LIGHTING_PRESENTATION.
Heightened CG strengthens only authored structural contrasts.

`render_stylization_gate` is a separate deterministic bilingual evidence test.
It returns mediumStatus, renderStylizationStatus, target, positiveEvidence,
photorealPullEvidence, missingDomains, conflicts and blocking. Complementary
evidence per domain is required; a visible-CG label alone is insufficient.
Negated evidence grants no PASS, and positive reassertion after a prohibition
is still inspected. Missing visible evidence or competing photographic priority
produces FAIL_RENDER_STYLIZATION even when mediumStatus is PASS. Legacy style
returns LEGACY_UNSPECIFIED; live action returns NOT_APPLICABLE. Neither is a
claim of visible-filmic readiness.

Receipts record renderStylization/source/compiler/version/evidence, presentationMode
and the full original intent; verification recompiles every section, fact span
and gate. A changed style, source, presentation or casting mode changes the receipt
and authorization fingerprint. Old receipts cannot pass v3 verification.

Text gates prove bounded contract consistency, not image quality or provider
causality. The two retained photographic-looking images can be reinterpreted as
ambiguous CG medium / photoreal-digital-human appearance / visible-filmic target
failure, while retaining the original FAIL_MEDIUM reports unchanged. New production
requires separately authorized visual validation.
