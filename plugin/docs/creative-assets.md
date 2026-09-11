# Creative memory in existing Asset / Media

Cinematic language: `assetType=OTHER`, `content.creativeKind=CINEMATIC_LANGUAGE`.
Music: `assetType=AUDIO_INPUT`, `content.creativeKind=MUSIC`, `role=BGM`.
No new Skill, Tool, domain, table or Asset enum. `Asset.content` remains a JSON
object; `referenceMediaIds` remains optional for ordinary Assets and text patterns.
BGM production requires a bound AUDIO Media, verified rights and readback bytes.

Canonical schemas live in `contracts/creative_asset.py`. Optional pattern dimensions
may be omitted; never fill fields merely for uniformity. `examples/cinematic-language-seeds.json`
contains ten independent patterns, all PROJECT_DERIVED with provenance, never
third-party original prompts. Each is a REFERENCE_PATTERN, not an instruction to
apply to every Shot. Provider-specific evidence belongs in notes/evidenceRefs.

Use `creative_assets.remember(tools, work_id, content)` through existing tools.
Exact semanticKey (cinematic language) or contentHash (BGM) is unique within Work.
Across Works the existing ownership boundary remains; retrieval is global and
permits reuse of text knowledge without making duplicate text assets in each Work.
The service locks the existing Work row for creative create/save checks. Equivalent
creates return the existing ID; conflicting content fails without replacing it.
Use explicit save for a deliberate revision. No automatic revision of historic IR.
Search matches name, description and JSON content before limiting to 100 matches;
this minimal implementation scans the scoped type, without embeddings or rankings.

A content fingerprint is SHA-256 over canonical JSON of the complete persisted
content (UTF-8, sorted keys, compact separators). It is computed, not self-stored.
The database's internal version is not exposed by the current Asset Tool, so IR
pins `assetId + contentFingerprint + appliedPurpose`. Freeze copies this reference
and expanded execution semantics; asset updates cannot alter frozen Shots.
Usually select 1–3 patterns; zero is valid. `search_patterns` explains purpose,
tags and suitableFor. Host must still compare avoidWhen and current creative context.

Music records originalSource, rights.source/license/attribution/commercialUse/status,
media.mediaId/sourceRef/contentHash, and optional duration, mood, narrativeFunctions,
energy, instrumentation, tempo, dialogueCompatibility and usage. Unknown values are
null/UNKNOWN. Only VERIFIED commercial rights with documented source, license and
attribution (empty string explicitly means none required) permit productionEligible.
UNKNOWN material remains searchable and blocked for production. Eligibility is an
explicit opt-in plus validation, never inferred from filename or successful storage.

Search BGM only after SUBTLE/ACTIVE. `search_bgm` returns candidates, not a choice.
`select_bgm` records Asset fingerprint, mediaId/hash, source range and reason.
Each executable BGM layer retains bgmAsset/bgmMedia/bgmSelection snapshots, checked
by render before cache reuse or writing output. Refresh formal rights for a new
production. Full source hash/probe checks still guard actual audio before rendering.
NO_BGM skips retrieval and rejects all BGM layers. Metadata changes never regenerate
or overwrite Media bytes. Historical recipe snapshots preserve past provenance.

For a local real project source, `creative_assets.retain_bgm_media` implements the
existing Tool/import/resolve/readback path: inspect AUDIO Media and formal usage by
hash before import; use media.import_media with a stable Work/hash sourceRef for
idempotent retries, get/resolve and full SHA-256 verification, then remember the BGM.
Do not register synthetic test tones, silence or downloaded arbitrary music as a
formal BGM. With no real source report PENDING_REAL_SOURCE. Test-only fixtures prove
contracts, not formal persistence or creative listening quality.
