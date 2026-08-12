---
name: scene-development
description: Develop or revise a historical-drama Scene from an Episode. Use when defining place, time, characters, entry state, objective, conflict, dialogue, action, turn, or exit state.
---

# Scene Development

Give each Scene a concrete dramatic purpose. Use `episode.get_episode` when the stable parent ID is known. Use `scene.get_scene` for a known `sceneId`. With a known `episodeId`, use `scene.list_scenes` for structural enumeration; when only a natural-language description is known, use `scene.search_scenes` and scope it to the Episode when possible. Judge candidates before editing. Use `scene.create_scene` only for a genuinely new Scene, and use `scene.save_scene` to persist a revised existing Scene.

Use `research.search_locations` or `research.verify_claim` only when location or historical uncertainty affects the Scene. Use `context.build_context` only when required context was not supplied, and use `context.refresh_context` only after a relevant state change. Define entry state, objective, conflict, action, turn, and exit state. Do not generate Shots or resolve assets automatically.
