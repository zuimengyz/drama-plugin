---
name: shot-production
description: Produce image, video, or audio media for an approved historical-drama Shot. Use when combining Shot and Scene context, selected stable Assets, and prior Media into start frames, end frames, video, dialogue, ambience, or other physical media outputs.
---

# Shot Production

Use the approved Shot, relevant Scene context, selected stable `assetId` values, and prior `mediaId` artifacts. Choose image, video, or audio generation according to the current need; there is no mandatory image-to-frame-to-video sequence. Pass only business prompts, stable Asset IDs, Media IDs, and necessary generation parameters.

Treat returned Media as stable physical references and keep their `mediaId` values in Agent Run Context. Read Media directly when its stable ID is known; use upstream Asset references, Shot Context, or a structurally scoped Media list otherwise. Do not perform broad semantic Media search. Never depend on storage URLs, local paths, buckets, filenames, provider tasks, workflow JSON, node IDs, or provider response structures. Stop when the requested media exists and its role is clear; do not continue to another Skill automatically.
