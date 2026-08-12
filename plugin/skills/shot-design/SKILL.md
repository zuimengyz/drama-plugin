---
name: shot-design
description: Design or revise shots for a historical-drama Scene. Use when choosing framing, camera position, composition, blocking, action, expression, camera movement, dialogue coverage, duration, or shot entry and exit state.
---

# Shot Design

Cover the Scene's dramatic turn with the fewest necessary Shots. For each Shot, specify framing, camera position, composition, blocking, action, expression, camera movement, dialogue coverage, duration, and entry/exit state. Preserve spatial, performance, prop, wardrobe, and temporal continuity.

Use `scene.get_scene` for a known parent Scene. Use `shot.get_shot` for a known `shotId`. With a known `sceneId`, use `shot.list_shots` for structural enumeration; when only a natural-language description is known, use `shot.search_shots` and scope it to the Scene when possible. Judge candidates before revising coverage. Use `shot.create_shot` only for a genuinely new Shot, and use `shot.save_shot` to persist a revised existing Shot.

Use `asset.get_asset` or `media.get_media` only when a stable reference is needed to judge continuity. Use `context.build_context` only when required context was not supplied, and use `context.refresh_context` only after a relevant state change. Do not resolve assets or produce media automatically.
