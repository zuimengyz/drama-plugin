# Character Art Visual Medium Contract

`contracts.visual_medium.VisualMediumIntent` is the provider-neutral authority:

```json
{
  "visualMedium": "CINEMATIC_CG",
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

`visual_medium.compile_character_art` validates source prose and composes separately
compiled medium, treatment, realism and casting-mode sections. CG compilation
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
sections; the gate never adds prose. Submission requires PASS.

`visualMediumCompilation` records compiler/version, intent, control-plane origin,
compiled constraints, emitted sections/offsets/hashes, prompt hash and gate status.
Host prose is marked `CHARACTER_FACTS_ONLY` or `LEGACY_CONFLICT_INPUT`; it is never
compiler evidence. `verify_medium_compilation` replays generated sections, checks
source-map reconstruction and re-runs the gate against the final prompt before
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
