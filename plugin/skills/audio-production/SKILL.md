---
name: audio-production
description: Produce exact-text dialogue speech clips, dialogue mixes, and final AV from approved Drama Dialogue and immutable source video. Use for provider-neutral voice resolution, speech freshness, duration probing, review, and deterministic AV assembly; do not use for authoring or revising Dialogue.
---

# Audio Production

Load the [Audio Layer content convention](../../docs/audio-layer-content-convention.md). Treat the Audio Provider as a replaceable capability. Do not encode a vendor, transport, server, workflow, or provider-specific pronunciation syntax in this Skill or in Drama content.

Gather the Work with `work.get_work`, the Scene with `scene.get_scene`, and any requested Shot with `shot.get_shot`. Resolve each target only from `Scene.content.spokenContent[]`; preserve its exact `text`, `spokenContentId`, `speakerKey`, and `performanceIntent`. Resolve the matching `Work.content.voiceProfiles[]` creative identity, one approved provider mapping, and applicable `Work.content.pronunciationGuidance[]`. Stop with a specific missing-profile, missing-mapping, or unresolved-pronunciation blocker; never repair these gaps by changing Dialogue.

Compile `SpeechGenerationRequest` with exact text in its typed field, then compute the canonical Audio input fingerprint. Use `media.list_media` with `work_id`, `purpose=SPEECH_CLIP`, and canonical `source_ref` to look for a current `reviewStatus=PASS` result. A failed, pending, or debug candidate uses an attempt sourceRef and does not block retry. Inspect a selected result with `media.get_media` when physical metadata or provenance must be confirmed.

Preflight only the required speech capability and any local probe/assembly capability. In contract-only, dry-run, or foundation work, stop before generation. In an explicitly authorized production run, call `production.generate_audio` once per stale spoken item with the structured request; never ask the Provider to write or improve the line. Keep Provider duration informational. Review exact text, speaker/voice, pronunciation, performance intent, intelligibility, clipping/noise, and consistency. Before reliable human Audio review, persist only a `reviewStatus=PENDING` candidate with an attempt sourceRef. A failed or pending review never receives the canonical sourceRef.

Probe the reviewed physical Audio on the Host. Import a PASS clip with `media.import_media` only after measurement, using `mediaType=AUDIO`, `purpose=SPEECH_CLIP`, Work scope, null Shot/Asset ownership, canonical sourceRef, positive probed `duration_ms`, and physical provenance. Reconcile actual duration against the visual window without deleting, adding, or rewriting words. Prefer reviewed pace/pause or visual re-plan when needed.

Build one `av-assembly-v1` manifest. Reuse one speech clip across all relevant Shot slices; `spokenContentBindings` remains the visual coverage authority. An optional `SHOT_DIALOGUE_MIX` is derivative. Resolve durable inputs with `media.resolve_media`; never persist signed URLs. Mux to a new path, capture implementation/version/settings, probe both streams and duration, hash all inputs/output, and confirm the source Video hash is unchanged. If the capability is missing, return `AV_ASSEMBLY_CAPABILITY_MISSING` while preserving completed speech-foundation results.

Import a successful mux with `media.import_media` as a new `mediaType=VIDEO`, `purpose=FINAL_AV` Media identity with positive probed duration and the committed manifest/fingerprint. Resolve and hash-review it. A preview awaiting any MUST Audio review uses `final-av-attempt:<fingerprint>:<attempt-id>`; only a fully reviewed result uses `final-av:<fingerprint>`. Stop when the requested reviewed clips/mix/final AV are stable; do not begin another Scene or expand into sound design automatically.
