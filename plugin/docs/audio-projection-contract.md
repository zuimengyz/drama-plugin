# Audio Projection Contract v1

## Ownership

Audio Projection is a deterministic transient layer inside the platform-neutral Audio foundation. It is not a business entity, persistence model, Tool, Runtime service, Provider request, or Voice-casting mechanism.

```text
DPDSnapshot (performance authority)
  + canonical SpokenContent (exact text authority)
  + CreativeVoiceProfile (stable voice baseline)
  + stable Voice/Casting identity (who speaks)
  + TargetTimingPolicy (timing context)
  → AudioPerformanceBrief
  → Provider adapter capability mapping
  → Provider request
```

DPD is the sole dramatic-performance authority, but not the sole Projection input. Projection never mutates DPD, copies Dialogue into DPD, selects a Provider voice, or fills missing dramatic meaning.

## AudioPerformanceBrief

`schemaVersion=audio-projection-v1`. Material identity fields are DPD, exact-text, Voice-profile, Voice-identity, and Timing fingerprints/references. The compact human-readable direction contains:

- pace plus `SLOWER | NEUTRAL | FASTER` tendency;
- rhythm;
- intensity plus `LOWER | NEUTRAL | HIGHER` volume tendency;
- pause strategy;
- articulation;
- sentence ending;
- external control;
- inherited performance boundaries.

The two tendencies are semantic deltas, not numeric Provider parameters. Breath and prosodic-emphasis ontologies are omitted because the current verified provider request cannot consume them and current fixtures do not prove a separate Core need.

Projection combines activation and control before authority/relationship/action. `HIGH + HIGH` becomes compressed internal pressure with restrained delivery; it never automatically means louder or faster. Authority classification also reads tactic, relationship stance, and dramatic action. Ambiguous authority/relationship fails `AUDIO_DIRECTION_INSUFFICIENT` instead of silently inventing another performance.

## Authority switch

`SpeechGenerationRequest.audioPerformanceBrief` presence selects the new path. On that path:

- `performanceIntent` must be empty;
- `sceneState` must be absent;
- `materialRenderParameters` may not contain `speed` or `volume`;
- request Scene, spoken item, speaker, exact-text hash, Voice-profile identity/fingerprint, and brief fingerprint must match.

Without a brief, the existing SceneState/PerformanceIntent path remains unchanged. The two paths never merge.

## Fingerprints

`audioProjectionFingerprint` is SHA-256 of canonical JSON for projection version, DPD fingerprint, canonical text hash, Voice profile ID/fingerprint, stable Voice identity reference, Timing fingerprint, human direction, tendencies, and boundaries. It excludes timestamp, Host, Provider, response, URL, and secret.

Lineage is:

```text
dpdFingerprint
  → audioProjectionFingerprint
  → providerRequestFingerprint
  → ROLE_DUBBING_AUDIO Media
```

The existing audio-input fingerprint includes `audioProjectionFingerprint` on the new path and retains legacy hashes only on the compatibility path.

## Capability degradation

Every provider adapter returns one diagnostic per brief dimension:

- `SUPPORTED`: a verified provider control directly carries the dimension;
- `APPROXIMATED`: a verified control carries only part of the intended semantics;
- `UNSUPPORTED`: no verified control exists; no parameter is invented.

For the current Fish S2-Pro adapter, pace and volume tendency map directly to
bounded `prosody.speed` and `prosody.volume`. Official S2 rendered-text controls
make rhythm, pause strategy, emphasis, sentence ending, intensity, and control
`TEXT_RENDERABLE`; they are not native numeric controls. Articulation and a
durable post-utterance hold remain unsupported, while a leading expression cue
only approximates pre-utterance preparation.

`SpeechGenerationRequest.exactText` remains canonical. A Fish-only rendered
representation may add a small allowlisted set of official S2 markers or
punctuation only after lexical-content validation. Canonical text, rendered text,
and their separate fingerprints remain traceable. Experimental rendered text is
not promoted to the default production mapping before human listening review.

## Voice and Casting

Projection reads only the stable creative Voice baseline and a platform Voice/Casting identity reference. It never sees or chooses a Fish reference ID. The Role Dubbing adapter resolves the Work binding and rejects a missing or mismatched stable Voice on the projected path. Provider materialization remains inside the adapter.
