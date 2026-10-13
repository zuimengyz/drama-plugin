---
name: asset-resolution
description: Resolve stable reusable visual assets for a Work, Script, Episode, Scene, or Shot. Use when an agent must discover visual objects, decide whether they merit long-term Asset identity, reuse an existing Asset, or create a new standard reference.
---

# Asset Resolution

Resolve continuity-critical props from the screenplay-derived Asset Manifest and
Prop Design original as stable PROP identities. Search within the current Work
before creation; record the first narrative appearance and exact later consumers.
Reuse the accepted asset/design version and verified reference Media for the same
physical object. A new Shot, angle, open lid or change of carrier is a use/state,
not a new baseline. Similar object names do not prove identity. When a required
reference is absent, retain preparation as pending and use the existing reference
production workflow only under applicable authorization. Never promote a text
original or a failed video frame to an accepted visual asset.

New reference production uses only configured and authorized official HTTP APIs.
Comfy Cloud MCP is retired for discovery, prompt guidance, generation and fallback.
Keep historical Media/receipts readable without treating them as new route authority.

For native narrative asset preparation, read the exact pending reference through
`specialized_assets.read_preparation`. Resolve each missing requirement in that
Scene before later Scenes: reuse accepted assets/references first, or use the
native `specialized_assets.*_reference` chain for a necessary new reference. The
pending result retains its preparation ref and a Runtime child ref. Read that
child with `read_reference`: the existing specialized professional author supplies
source-bound artwork, and the existing still compiler seals its request. If the
artwork is supplied interactively, `frame_reference` accepts a complete typed
FrameSpec with the exact target/design fingerprint, not a raw prompt. Native
source authority is checked by this owner; `professional_sources` is reserved for
the separate opt-in retained Still Knowledge receipt and must not be repurposed.
Use `quote_reference` for current request-bound quote/balance and one-operation
budget. `decide_reference` delegates exact COST_APPROVAL/ADOPTION to the existing
Target decision owner. `resume_reference` advances that same child. Review actual
retained pixels and record exact-hash checks/findings using `review_reference`;
PASS alone does not adopt. Accepted candidates register through the existing
SpecializedAssetSequence and AssetProvider, then the parent prepares its remaining
narrative dependencies. No earlier Scene videos are required.

A pending preparation grants no media-spending authority. Do not
call retired raw-prompt generation or automatically adopt candidates/templates.
After the existing artistic adoption covers the exact design and reference media,
use `specialized_assets.accept`; it reads back the complete registration and reuses
an already accepted requirement on replay. Keep new variations as separate versions
with an accepted parent, retaining old records. Then resume the existing creative
Run; it advances remaining predecessor assets and the requested Scene automatically.
Drama-Service persists these originals, proofs and bindings through AssetProvider;
it does not decide appearance, order, or artistic adoption.
The existing Asset and ordinary image import APIs require a registered business
Work with this exact identity. Check that scope before spending. The separate
Target-video native-scope receipt cannot authorize asset-image import; never forge
a Shot, Package or Service Work alias to make a reference appear registered.

Analyze only the current creative context and identify visual objects that may deserve reuse across Scenes, Shots, or Agent runs. Use `asset.get_asset` for a known `assetId`. Use `asset.list_assets` for a structured type scope; use `asset.search_assets` when only a natural-language identity or description is known. Judge candidates before creating anything. `FOUND` and `NOT_FOUND`, suitability, classification, and reuse decisions belong to the Agent.

Use `media.get_media` when an existing reference Media ID must be inspected. When no suitable Asset exists and a standard image is necessary, return the missing reference duty to Specialized Asset Design for concrete characters/environments/costume, or Prop Design for its independent object originals, then use the native reference production chain above. Deprecated character-art/environment-art are retained read views. Consume only the resulting compiled, gated and reserved request; raw-prompt `production.generate_image` is retired. Asset resolution owns reuse and registration, not visual design. Import an unregistered physical result with `media.import_media`, then get, resolve, download and verify its complete hash before binding it. `media.create_media` registers an opaque reference only; it does not prove stored bytes. never register an already stable `mediaId` again. Use `asset.create_asset` only after producing the complete initial formal state needed to register a genuinely new stable Asset. A successful create is the normal first write and returns the stable ID; do not call `asset.save_asset` immediately afterward unless a concrete revision has actually occurred. Use `asset.save_asset` only to revise an already persisted Asset because of a specific user request, discovered error, upstream change, or necessary addition to its formal state.

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

## Designed casting and identity authority

For new or revised casting, consume production-design's source-pinned CharacterVisualSpec and HistoricalCanonPolicy. production-design decides what the character should look like; this skill finds/creates/reuses and maintains the corresponding identity. Validate the approved fingerprint with `production_design.validate_reference_design`; do not redesign stable traits to fit an available reference. Legacy references remain readable. A candidate spec is not authority to replace current referenceMediaIds. State remains Scene/Shot state; a new accepted design needs a new reference revision, preserving old Media. Text-only production design uses OTHER and the four typed creative kinds through the same `creative_assets.remember` flow.

## Sequence production handoff

For sequence reuse, contribute current identity/reference fingerprints to [Bible indexes](../../docs/sequence-production-contract.md). An index selects the necessary views and interaction checks for actual coverage; it does not create another identity or approve candidates. Verify stable grip/scale/contact for recurring props and rider/animal relations only when the scene needs them.

For a Sequence ProductionDesignFreeze, resolve current Asset IDs, content fingerprints, explicit user approval evidence and any required verified Media bytes. A text-only design or HOST_WORKING_REFERENCE cannot fulfill an approved face/media duty. Return every missing role, including mount/tack when required; never approve a candidate to complete the seal.

For explicit [visual routes](../../docs/visual-route-contract.md), use route-aware discovery before reference selection. Existing untagged assets remain legacy evidence requiring review, never implicit CG matches. Store visualRoute only on newly authorized route-specific content; create a separate design/reference revision rather than overwriting a live-action identity or copying its approval.

Seedream supports text-to-image (default) and explicitly selected image-to-image.
Existing assets alone never change the mode. Image-to-image selects accepted Asset
references through reference_selections (or the inherited parent), verifies their
formal Media bytes and sends them in the official image field, with distinct
identity/location duties. Text rendering of a justified variant still inherits
the approved identity design; it must not claim image conditioning or establish a
new face. Both modes require actual review and adoption. Unknown synchronous
submission cannot be queried by pretending a video task ID is an image task.
Recover the exact retained receipt/output or leave that uncertain attempt pending;
never POST again on resume.
