---
name: episode-development
description: Develop or revise one historical short-drama Episode from a Script. Use when deciding the episode goal, opening hook, conflict progression, information gain, character change, ending hook, or cross-episode continuity.
---

# Episode Development

Give the Episode one clear dramatic job within the Script. Use `script.get_script` when the stable parent ID is known. Use `episode.get_episode` for a known `episodeId`; otherwise use `episode.list_episodes` under the known Script, filtering by episode number or title when available. Use `episode.create_episode` only for a genuinely new Episode, after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `episode.save_episode` immediately afterward unless a concrete revision has actually occurred. Use `episode.save_episode` only to revise an already persisted Episode because of a specific user request, discovered error, upstream change, or necessary addition to its formal state. Use `research.verify_claim` only when the Episode decision depends on uncertain history.

Design an opening hook, conflict progression, information gain, character change, and ending hook. Check neighboring Episodes only when continuity requires it. Use `context.build_context` only when required context was not supplied, and use `context.refresh_context` only after a relevant state change. Do not decompose the Episode into Scenes automatically.
