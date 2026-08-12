---
name: asset-resolution
description: Resolve stable reusable visual assets for a Work, Script, Episode, Scene, or Shot. Use when an agent must discover visual objects, decide whether they merit long-term Asset identity, reuse an existing Asset, or create a new standard reference.
---

# Asset Resolution

Analyze only the current creative context and identify visual objects that may deserve reuse across Scenes, Shots, or Agent runs. Use `asset.get_asset` for a known `assetId`. Use `asset.list_assets` for a structured type scope; use `asset.search_assets` when only a natural-language identity or description is known. Judge candidates before creating anything. `FOUND` and `NOT_FOUND`, suitability, classification, and reuse decisions belong to the Agent.

Use `media.get_media` when an existing reference Media ID must be inspected. When no suitable Asset exists and a standard image is necessary, use `production.generate_image`; use its returned stable Media directly. Use `media.create_media` only when the generation capability returned an unregistered physical result, and never register an already stable `mediaId` again. Use `asset.create_asset` only after producing the complete initial formal state needed to register a genuinely new stable Asset. A successful create is the normal first write and returns the stable ID; do not call `asset.save_asset` immediately afterward unless a concrete revision has actually occurred. Use `asset.save_asset` only to revise an already persisted Asset because of a specific user request, discovered error, upstream change, or necessary addition to its formal state.

Use `context.build_context` only when required creative context was not supplied, and use `context.refresh_context` only after a relevant state change. Keep chosen IDs in Agent Run Context. Do not create hierarchy, binding, or variant domains, and do not expose storage or implementation details.
