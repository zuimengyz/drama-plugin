---
name: asset-resolution
description: Resolve stable reusable visual assets for a Work, Script, Episode, Scene, or Shot. Use when an agent must discover visual objects, decide whether they merit long-term Asset identity, reuse an existing Asset, or create a new standard reference.
---

# Asset Resolution

Analyze only the current creative context and identify visual objects that may deserve reuse across Scenes, Shots, or Agent runs. Use `asset.get_asset` for a known `assetId`. Use `asset.list_assets` for a structured type scope; use `asset.search_assets` when only a natural-language identity or description is known. Judge candidates before creating anything. `FOUND` and `NOT_FOUND`, suitability, classification, and reuse decisions belong to the Agent.

Use `media.get_media` when an existing reference Media ID must be inspected. When no suitable Asset exists and a standard image is necessary, use `production.generate_image`; require its verified durable completion. Import an unregistered physical result with `media.import_media`, then get, resolve, download and verify its complete hash before binding it. `media.create_media` registers an opaque reference only; it does not prove stored bytes. never register an already stable `mediaId` again. Use `asset.create_asset` only after producing the complete initial formal state needed to register a genuinely new stable Asset. A successful create is the normal first write and returns the stable ID; do not call `asset.save_asset` immediately afterward unless a concrete revision has actually occurred. Use `asset.save_asset` only to revise an already persisted Asset because of a specific user request, discovered error, upstream change, or necessary addition to its formal state.

When standard-image production uses an external visual provider, load the shared [Visual Provider Capability and Technical Retry Policy](../shot-production/references/visual-provider.md). Apply its retry classification, bounded per-operation budget, submission-uncertainty protection, same-job recovery, and separate technical retry versus Visual Review revision counters. Do not duplicate or weaken that policy here.

Organize persistence as **Stable Envelope + Domain Content**. For a new Asset, keep its Work and optional narrower scope IDs, asset type, name, optional description, and reference Media IDs in the Stable Envelope; place type-specific approved visual identity and reusable creative facts in the `content` JSON object. For an Asset revision, preserve its scope and type, and submit the stable Asset ID with its complete revised mutable formal state. When `media.create_media` is genuinely needed, pass the stable scope, media type, purpose, and opaque `source_ref` as envelope data; never interpret that reference as a URL, bucket, path, filename, workflow node, or Provider response. Put only confirmed semantic Media facts in Domain Content. Do not hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Use each save operation as a full replacement, never as a patch, stringified JSON, scratchpad, or routine follow-up to create.

Use `context.build_context` only when required creative context was not supplied, and use `context.refresh_context` only after a relevant state change. Keep chosen IDs in Agent Run Context. Do not create hierarchy, binding, or variant domains, and do not expose storage or implementation details.


## Durable completion and recovery

For retained image, video, audio or derived AV, formal completion requires full
readback SHA-256/size, decodable media, correct business ownership and a queryable
stable business binding. A local path, upload name, returned ID or temporary URL
alone is PERSISTENCE_PENDING. Content PASS, user adoption and persistence are
independent; persistence must never rewrite an existing adoption decision.

The shared completion entry `complete_retained_media` implements import/reuse,
readback and binding. Visual attempts call it through `visual_preflight.py persist`;
role speech calls it before returning a production result; an explicit mux calls
it on the new output before formal delivery. Adopted native AV consumption uses
`prepare_bound_media(adopted=True)` to recover the selected original from its formal
business reference. It performs no dubbing, separation, mixing or remuxing.

After a successful generation, resume at import/readback/binding with the same
job, output hash and sourceRef. After an uncertain import, query the exact stable
source first; ambiguity, permission denial, hash conflict or unknown ownership
blocks completion. Retry transient reads with finite backoff and fresh resolve.
Never generate again to repair missing cache or persistence. Do not import
unneeded DEBUG/REJECTED files or invent an output that was never generated.

Use `media.list_media` to reconcile a stable source and `media.resolve_media` for each formal readback.

## New-story route gate

For a new production Work, finish narrative and text identity first, jointly
plan the route and its minimum input duties with video-model-selection, and save
that route using the existing Work contract. Asset discovery before route selection
is read-only. A shared reviewed image may establish several necessary identities;
do not automatically create separate character, location, prop and endpoint sets.
Use `shot-production/scripts/route_preflight.py` for the Work-owned stage. Paid
images must match a current necessary duty and explicit whole-stage budget.
Materialize and review only the inputs for the current representative target;
no full-episode asset expansion follows from route selection. Keep all result,
review, settlement and persistence updates on that same formal stage.

## Creative text and music memory

The same Asset tools also register provider-neutral creative knowledge and BGM.
Cinematic language uses OTHER with creativeKind=CINEMATIC_LANGUAGE, semanticKey,
REFERENCE_PATTERN, structured pattern, provenance and validation. Media is optional:
never fabricate a txt file or Media to store text. Use canonical content SHA-256
for references, and PROJECT_DERIVED / OBSERVED_PATTERN until actual evidence exists.
Never copy third-party long prompts into the library.

BGM uses AUDIO_INPUT with creativeKind=MUSIC and role=BGM; referenceMediaIds binds
the existing Media and content.media pins its sourceRef/hash. A path is original
provenance only. Import real existing project audio via media.import_media if
needed, then resolve and verify full bytes. UNKNOWN rights may be registered but
productionEligible must be false. Do not generate music for registration.

Search before create by exact cinematic semanticKey, or BGM contentHash within
the Work. `creative_assets.remember` reuses identical content, reports differing
content as a revision conflict, and verifies create/get/search. Server serializes
same-work creative creation to avoid duplicates. Deliberate revisions use existing
save_asset with full state; preserve the stable key, unrelated content and old
frozen Shot snapshots. Reuse existing Media by hash before any import; use a
deterministic sourceRef based on Work/hash for first import retry safety. Never
create another BGM identity merely because a filename changes.

For a confirmed local project source, `creative_assets.retain_bgm_media` searches
existing Media by hash, uses a deterministic sourceRef only for the first import,
and verifies resolve/readback. A saturated listing blocks ambiguous imports.
