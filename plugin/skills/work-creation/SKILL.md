---
name: work-creation
description: Create or revise a historical-drama Work from research context. Use when defining literary premise, theme, viewpoint, relationships, central conflict, dramatic timeline, or the overall structure of the source work.
---

# Work Creation

Turn research context into a coherent literary work, not a record of historical sources. Establish theme, narrative viewpoint, character relationships, central conflict, dramatic timeline, and overall structure. Mark invention and uncertainty where they affect the work's truth claims.

When a stable `workId` is known, use `work.get_work`. When only a title or natural-language description is known, use `work.search_works` and judge the candidates. Use `work.list_works` only to enumerate the available structural scope. Use `work.create_work` only when a new Work is genuinely required; use `work.save_work` to persist a revised existing Work. Use `research.verify_claim` only when a creative choice depends on an unresolved historical claim.

Use `context.build_context` only when the required Work context was not supplied, and use `context.refresh_context` only when a state-changing Tool has made the current context stale. Do not create a Script merely because the Work is complete: return the Work and let the Agent choose what follows.
