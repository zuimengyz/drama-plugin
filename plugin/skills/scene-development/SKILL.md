---
name: scene-development
description: Develop or revise a historical-drama Scene from an Episode. Use when defining place, time, characters, entry state, objective, conflict, dialogue, action, turn, or exit state.
---

# Scene Development

Give each Scene a concrete dramatic purpose. Use `episode.get_episode` when the stable parent ID is known. Use `scene.get_scene` for a known `sceneId`. With a known `episodeId`, use `scene.list_scenes` for structural enumeration; when only a natural-language description is known, use `scene.search_scenes` and scope it to the Episode when possible. Judge candidates before editing. Use `scene.create_scene` only for a genuinely new Scene, after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `scene.save_scene` immediately afterward unless a concrete revision has actually occurred. Use `scene.save_scene` only to revise an already persisted Scene because of a specific user request, discovered error, upstream change, or necessary addition to its formal state.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Episode ID, scene order, title, and optional location in the create envelope; use the stable Scene ID plus order, title, and optional location when saving a revision. Put characters, time, entry state, objective, conflict, dialogue, action, turn, exit state, and other formal scene facts in the `content` JSON object. Do not move the parent Episode ID during save or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit `scene.save_scene` as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create.

Use `research.search_locations` or `research.verify_claim` only when location or historical uncertainty affects the Scene. Use `context.build_context` only when required context was not supplied, and use `context.refresh_context` only after a relevant state change. Define entry state, objective, conflict, action, turn, and exit state. Do not generate Shots or resolve assets automatically.
