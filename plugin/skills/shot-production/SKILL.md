---
name: shot-production
description: Produce image, video, or audio media for an approved historical-drama Shot. Use when combining Shot and Scene context, selected stable Assets, and prior Media into start frames, end frames, video, dialogue, ambience, or other physical media outputs.
---

# Shot Production

Use `shot.get_shot` and `scene.get_scene` when their stable IDs are known and the approved production context was not already supplied. Use `asset.get_asset` or `media.get_media` only when a selected stable reference needs inspection; use `media.list_media` only for a clear structural media scope, not broad discovery.

Choose `production.generate_image`, `production.generate_video`, or `production.generate_audio` according to the requested output; there is no mandatory generation sequence. Pass only business prompts and stable reference IDs. Use `context.build_context` only when required Shot context was not supplied, and use `context.refresh_context` only when generated Media makes the current context stale.

Treat returned Media as stable references and keep their IDs in Agent Run Context. Never depend on storage locations, filenames, implementation tasks, workflow documents, node IDs, or implementation-specific responses. Stop when the requested media exists and its role is clear; do not redesign the Shot or continue to another Skill automatically.
