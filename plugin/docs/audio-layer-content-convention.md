# Audio Layer Content Convention v1

Status: **FROZEN for Audio v1**

This convention defines provider-neutral speech, Media, freshness, and AV assembly semantics. It adds no Audio entity, database table, or Audio CRUD Tool.

## 1. Dialogue authority

`Scene.content.spokenContent[].text` is the only authoritative Dialogue text. Audio consumers MUST copy the selected item's exact text into `SpeechGenerationRequest.exactText`; they MUST NOT rewrite, add, remove, split, merge, or persist pronunciation changes back into Dialogue. `spokenContentId`, `speakerKey`, `performanceIntent`, and `estimatedDurationMs` remain Scene-owned inputs. Provider markup, phonemes, pinyin, SSML, transcripts, and pronunciation dictionaries are derivative adapter state, never canonical Dialogue.

## 2. Work-owned voice identity

`Work.content.voiceProfiles[]`, when persisted, is keyed by Work-scoped `speakerKey` and supports actors and narrators equally. A production run may instead carry a transient Character Voice Profile derived from persisted Work/Scene/Character context when no reviewed Work-level profile exists; this does not require a new database entity. The derivation begins with a transient, evidence-scoped `CharacterUnderstanding` containing neutral identity/life-stage, experience, decision, emotional-regulation, interaction, responsibility, communication, physical-baseline, presentation-mode, and alignment/constraint dimensions with confidence and explicit unknowns. It is not a personality ontology or a historical-value judgment. Every profile logically separates:

- `creativeProfile`: durable voice identity such as vocal age/weight, resonance depth, timbre brightness, articulation firmness, phrase attack, baseline pace/energy, breath support, command presence, gravitas, controlled power, sentence finality, emotional containment, language/register, and consistency notes.
- `providerMappings[]`: replaceable implementations containing provider, model, voice ID, candidate/approved/retired status, and material controls.

Temporary `SceneState` is separate from Character Understanding and the durable creative profile. `performanceIntent` expresses a baseline plus line-specific delta. Fatigue does not imply low authority, restraint does not imply low energy, age does not imply slow pace, authority does not imply loudness, and anger does not imply shouting.

Changing Provider MUST NOT mutate `creativeProfile`. The Skill never chooses a concrete mapping. A Provider adapter ranks no more than three compatible candidates from the profile at its boundary; a generated candidate has `voiceBindingStatus=PENDING` and is not an approved reusable character binding. An already approved explicit mapping remains supported for backward compatibility. Display names, operational notes, timestamps, and other non-material metadata do not change the creative or mapping fingerprint. A material creative attribute or resolved mapping input does.

## 3. Pronunciation

`Work.content.pronunciationGuidance[]` is provider-agnostic. Each entry identifies `term`, `language`, `reviewedReading`, and optional `speakerKey`. Adapter-specific syntax is compiled only at the Provider boundary. Guidance notes are non-material; term, language, reviewed reading, and speaker scope are material.

## 4. Structured speech request and Provider seam

`SpeechGenerationRequest` (`schemaVersion=speech-generation-v1`) contains the exact text as a typed field, plus `workId`, `sceneId`, `spokenContentId`, `speakerKey`, provider-neutral `voiceProfile` with its Character Understanding, separate `sceneState`, applicable `pronunciationGuidance`, baseline-plus-delta `performanceIntent`, material render parameters, target timing policy, and optional non-material context references. `providerMapping` may be absent at the Tool boundary; the active Provider adapter must resolve a candidate before fingerprinting or generation. An explicit approved mapping remains valid for backward compatibility. Exact Dialogue text MUST NOT exist only inside a natural-language prompt.

The existing `production.generate_audio` capability accepts this structured request. A Plugin adapter compiles it to the generic `ProductionProvider.generate_audio` seam while preserving the complete request in structured parameters. The Audio Skill treats the Audio Provider as a replaceable capability; HTTP-backed or MCP-backed implementations may be added behind the adapter without changing the Skill.

## 5. Audio purposes and ownership

| purpose | envelope | ownership |
|---|---|---|
| `SPEECH_CLIP` | `mediaType=AUDIO`, `workId=<work>`, `shotId=null`, `assetId=null` | one reviewed `spokenContent` item → one reusable clip |
| `SHOT_DIALOGUE_MIX` | `mediaType=AUDIO`, normally `shotId=<shot>` | derivative ordered placements/pause mix |
| `FINAL_AV` | `mediaType=VIDEO`, normally `shotId=<shot>` | new Media identity derived from immutable source Video plus reviewed Audio |

A spoken item covered by multiple Shots still has one speech clip. `Shot.content.spokenContentBindings[]` remains the sole visual coverage semantic; Audio defines no parallel on-screen/reaction/off-screen enum.

## 6. Canonical input fingerprint

`AUDIO_INPUT_FINGERPRINT` is SHA-256 of UTF-8 deterministic canonical JSON (`sort_keys=true`, compact separators, Unicode preserved, non-finite numbers rejected) containing exactly:

```text
schemaVersion
workId
sceneId
spokenContentId
textHash
speakerKey
performanceIntentHash
sceneStateHash
voiceProfileFingerprint
providerMappingFingerprint
pronunciationFingerprint
provider
model
materialRenderParameters
targetTimingPolicy
```

`textHash` is SHA-256 of the exact UTF-8 Dialogue text. Creative voice, Provider mapping, and pronunciation are separately canonicalized. List ordering is ignored only for pronunciation entries; Dialogue and timeline ordering retain meaning. Non-material profile/mapping/guidance/request metadata is excluded.

A change to exact text, speaker, Scene State, performance intent, creative voice, resolved Provider mapping, applicable pronunciation, material render parameters, or target timing policy makes the prior clip stale. An unchanged fingerprint plus `reviewStatus=PASS` is fresh.

## 7. Source reference and retry semantics

Only a reviewed, current, reusable PASS result owns:

```text
audio-input:<audio-input-fingerprint>
```

Persisted failed, pending, or debug candidates use:

```text
audio-attempt:<audio-input-fingerprint>:<attempt-id>
```

A FAILED attempt therefore cannot occupy the canonical key or block retry. The existing unique `Media.sourceRef` mechanism is authoritative; no Audio idempotency table is introduced. Old Media remains immutable evidence but is excluded by freshness/review selection.

## 8. Physical Media and duration authority

`Media.durationMs`, `mimeType`, `fileSize`, and `contentHash` describe the persisted physical object. `durationMs`, when present, MUST be positive. AUDIO import requires `audio/*`; `FINAL_AV` requires `mediaType=VIDEO` and `video/*`.

`Scene.spokenContent.estimatedDurationMs` is planning input and is not actual duration. A Provider-reported duration is informational only. The Host MUST probe the final physical file with `ffprobe` or an equivalent media probe and pass the measured value to `media.import_media(duration_ms=...)`; Java persists it but does not execute media probes.

## 9. AV assembly v1

The minimal committed manifest is:

```json
{
  "schemaVersion": "av-assembly-v1",
  "sourceVideoMediaId": "media-source-video",
  "audioMixMediaId": "media-dialogue-mix-or-null",
  "speechClipMediaIds": ["media-speech-clip"],
  "timeline": [
    {
      "spokenContentId": "spoken-item",
      "audioMediaId": "media-speech-clip",
      "startMs": 0,
      "sourceInMs": 0,
      "sourceOutMs": 1000
    }
  ]
}
```

Multiple timeline slices may reference the same speech clip. A Host mux must write a new output path, capture implementation/version/settings, probe video and audio streams, hash inputs/output, and confirm that the source Video hash is unchanged. `FINAL_AV` is imported as a new Media object and identity; the silent source Video is never overwritten.

The canonical source reference for a fully reviewed result is `final-av:<finalAvFingerprint>`. A pending, failed, or debug preview uses `final-av-attempt:<finalAvFingerprint>:<attempt-id>` and must not occupy the canonical key. In particular, a mux awaiting human Audio review remains an attempt preview even when every physical and hash check passes.

## 10. Audio v1 boundary

Voice cloning, BGM, SFX, Foley, ambience, spatial audio, ducking, forced alignment, precise lip-sync, subtitles, mastering, and multi-Scene Audio E2E are deferred. Real speech generation requires a separately authorized Provider run and budget; contract/foundation validation never implies permission to invoke one.
