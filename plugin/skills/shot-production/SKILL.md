---
name: shot-production
description: Produce image, video, or audio media for an approved historical-drama Shot. Use when combining Shot and Scene context, selected stable Assets, and prior Media into start frames, end frames, video, dialogue, ambience, or other physical media outputs.
---

# Shot Production

Use `shot.get_shot` and `scene.get_scene` when their stable IDs are known and the approved production context was not already supplied. Use `asset.get_asset`, `asset.list_assets`, or `asset.search_assets` to discover relevant stable visual memory without inventing references. Inspect selected references with `media.get_media`; use `media.list_media` only for a clear structural media scope, not broad discovery.

Do not require a visual provider for context reads, non-visual planning, Shot design, or other non-visual work. For image or video planning and execution, load [references/visual-provider.md](references/visual-provider.md) so the plan includes the complete reference-to-provider-to-Media handoff. Before actual execution, preflight only the Drama and visual capabilities required by that request. Return `DRAMA_PROVIDER_UNAVAILABLE`, `VISUAL_PROVIDER_UNAVAILABLE`, or `VISUAL_PROVIDER_CAPABILITY_MISSING` when the corresponding capability is unavailable; stop rather than installing, configuring, or simulating a provider.

For visual production, select no more than three stable reference Media, resolve each selected input through `media.resolve_media`, execute the Host-provided visual capability, review the fetched file, and use `media.import_media` only after Review PASS. Keep the returned stable `mediaId` and its Shot role in Agent Run Context. For audio, use `production.generate_audio`; there is no mandatory image-to-video-to-audio sequence.

Use `context.build_context` only when required Shot context was not supplied, and use `context.refresh_context` only after stable generated Media makes the current context stale. Never expose temporary URLs, storage locations, filenames, provider task IDs, workflow documents, node IDs, or provider-specific responses as Drama domain facts. Stop when the requested media exists in stable Drama memory and its role is clear; do not redesign the Shot or continue to another Skill automatically.
