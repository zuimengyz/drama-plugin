---
name: shot-design
description: Design or revise shots for a historical-drama Scene. Use when choosing framing, camera position, composition, blocking, action, expression, camera movement, dialogue coverage, duration, or shot entry and exit state.
---

# Shot Design

Cover the Scene's dramatic turn with the fewest necessary Shots. For each Shot, specify framing, camera position, composition, blocking, action, expression, camera movement, dialogue coverage, duration, and entry/exit state. Preserve spatial, performance, prop, wardrobe, and temporal continuity.

Use `scene.get_scene` for a known parent Scene. Use `shot.get_shot` for a known `shotId`. With a known `sceneId`, use `shot.list_shots` for structural enumeration; when only a natural-language description is known, use `shot.search_shots` and scope it to the Scene when possible. Judge candidates before revising coverage. Use `shot.create_shot` only for a genuinely new Shot, after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `shot.save_shot` immediately afterward unless a concrete revision has actually occurred. Use `shot.save_shot` only to revise an already persisted Shot because of a specific user request, discovered error, upstream change, or necessary addition to its formal state.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Scene ID, string-valued shot number, optional title, and optional shot type in the create envelope; use the stable Shot ID plus shot number, title, and type when saving a revision. Put framing, camera, composition, blocking, action, expression, movement, dialogue coverage, duration, entry/exit state, and other formal shot facts in the `content` JSON object. Do not move the parent Scene ID during save or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit `shot.save_shot` as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create.

Use `asset.get_asset` or `media.get_media` only when a stable reference is needed to judge continuity. Use `context.build_context` only when required context was not supplied, and use `context.refresh_context` only after a relevant state change. Do not resolve assets or produce media automatically.
