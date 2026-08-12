---
name: asset-resolution
description: Resolve stable reusable visual assets for a Work, Script, Episode, Scene, or Shot. Use when an agent must discover visual objects, decide whether they merit long-term Asset identity, reuse an existing Asset, or create a new standard reference.
---

# Asset Resolution

Analyze only the current creative context and identify visual objects that may deserve reuse across Scenes, Shots, or Agent runs. Decide through reasoning whether each object is stable enough to become an Asset. When an `assetId` is known, read it directly or use sufficient Context data. When the ID is unknown, search by natural-language description and optional type. `FOUND` and `NOT_FOUND`, suitability, classification, and reuse decisions belong to the Agent, not the Tool or service.

When no suitable Asset exists, define a stable standard description and generate an image through a business-level production tool when needed. Use the returned stable Media directly; register it with `media.create_media` only if the generation capability returned an unregistered physical result. Then register the approved Asset with its `referenceMediaIds`. Put chosen `assetId` and `mediaId` values in Agent Run Context. Do not create scene/shot hierarchy, binding, or variant domains, and do not expose storage or provider details.
