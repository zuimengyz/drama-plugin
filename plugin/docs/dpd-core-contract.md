# Dramatic Performance Direction Core Contract v1

## 1. Ownership and boundary

DPD is an Agent-side, deterministic intermediate creative artifact. It is owned by the platform-neutral Skill Core and is neither a business entity nor a Runtime, transport, Provider adapter, Java service, database table, or media-generation request.

```text
approved Scene + minimal character/relationship/historical context
                         ↓
               Scene / Beat / Line DPD
                         ↓
                    DPDSnapshot
                     ↙       ↘
          future Audio       future Visual
           Projection         Projection
```

The Core states why a character acts, toward whom, with which objective/tactic/relationship position, and with what internal activation and external control. It does not decide how a microphone, voice model, image model, camera, body, or face implements that decision.

## 2. Contract layers

All input layers use `schemaVersion=dpd-v1` and reject unsupported versions, unknown fields, blank required text, and invalid scopes.

### SceneDPD

Scene owns stable dramatic context: `sceneId`, source fingerprint, dramatic purpose, conflict condition, power structure, public/private context, and optional emotional climate, urgency context, information asymmetry, and social constraints. It may seed inheritable direction values but does not copy the Scene, Work, Script, or Character record.

### BeatDPD

Beat owns `beatId`, current actor, obstacle, transition trigger, and a sparse direction delta. The composed state must resolve a target, objective, tactic, authority position, relationship stance, internal activation, and external control. A Beat is an action under resistance, not an emotion label.

### LineDPD

Line references canonical `spokenContentId` and `speaker`; it does not own or copy Dialogue text. It owns the line's dramatic action, observable intent, continuity, change from the previous line/Beat, and only genuine overrides.

### DPDLayerState

The only inheritable fields are:

```text
objective
interactionTarget
tactic
authorityPosition
relationshipStance
internalActivation
externalControl
publicPrivateContext
subtext
performanceBoundaries
```

`internalActivation` and `externalControl` use the sole small vocabulary `LOW | MEDIUM | HIGH`. All relational and action semantics remain concise free text so the contract does not become a character RPG or an oversized taxonomy.

Fields considered but deliberately omitted from v1:

- `confidence`: evidence confidence remains with Character/Historical inputs; dramatic certainty can be expressed in tactic or observable intent.
- `riskAwareness`: risk belongs in conflict, urgency, social constraints, and the chosen tactic unless a later fixture proves a distinct material need.
- `informationPosition`: Scene's `informationAsymmetry` plus line objective/subtext covers the current need.
- emotion labels: `emotionalClimate` is optional Scene context; emotion is never the main direction.
- physical gesture, gaze, posture, blocking, camera, pace, rhythm, breath, articulation, pitch, volume, or numeric pause: these are downstream projection fields.

## 3. Composition rules

Composition is deterministic:

```text
effective = Scene base → Beat override → Line override
```

- A missing field inherits the nearest parent value.
- Missing and explicit `null` both inherit. This makes a default JSON round-trip stable because omitted optional fields may be serialized as null. DPD v1 deliberately has no scalar-reset syntax.
- `performanceBoundaries` is replace-whole, not append. An omitted list inherits; an empty list explicitly clears it.
- A lower layer wins on an ordinary field conflict. There is no merge-by-prompt or implicit concatenation.
- `sceneId` and `beatId` mismatches are hard errors. One object per scope means same-priority conflicts cannot be represented.
- Scene/Beat/Line inputs are deep-copied into the snapshot, so later caller mutation cannot alter the recorded decision.

The effective object must contain objective, target, tactic, authority position, relationship stance, activation, control, and public/private context. This gate prevents a structurally valid but dramatically empty artifact.

## 4. Snapshot and fingerprint

`DPDSnapshot` uses `schemaVersion=dpd-snapshot-v1` and contains the three validated source layers, one flattened `EffectiveDPD`, and a 64-character lowercase SHA-256 fingerprint.

The fingerprint is calculated from compact, Unicode-preserving canonical JSON with sorted object keys and no timestamp, random ID, hostname, Provider output, or stored fingerprint field. Array order remains meaningful. Identical semantic input has the same fingerprint; any material direction change has a different fingerprint.

`sourceFingerprint` identifies the approved upstream dramatic source without copying that source. Persistence of a snapshot in existing open Scene content remains an optional future lifecycle decision; v1 adds no Java contract or database migration.

## 5. Character separation

Character Understanding answers who a person generally is and how they usually decide, relate, and regulate. DPD references the actor/speaker key and directs only the current dramatic moment. Age, biography, office, long-term temperament, Voice Profile, Creative Voice Casting, and Provider voice mapping are never copied into Line DPD.

Historical facts and social rank may constrain power, control, relationship, or tactic, but Research remains upstream. DPD does not retrieve evidence or decide historical truth.

## 6. 7.2S compatibility

The following compatibility inputs remain operational in Audio v1 and are not destructively removed in 7.3A:

| Existing structure | 7.3A status | Long-term ownership |
|---|---|---|
| `CharacterUnderstanding` / stable Voice Profile | KEEP | stable Character/Voice context |
| `SceneState.currentEmotion`, cause, urgency, stress, physical condition, presentation mode | KEEP | transient objective state input |
| `SceneState.internalActivation`, `externalExpressiveness`, target, objective, subtext, restraint | COMPATIBILITY / future deprecation | DPD becomes authoritative after projection migration |
| untyped `performanceIntent` cross-modal fields | COMPATIBILITY / future deprecation | DPD Core |
| `pace`, `volume`, breath, emphasis, articulation, sentence closure, precise pauses | KEEP FOR AUDIO COMPATIBILITY | future Audio Projection |
| legacy `delivery`, top-level `pace`, `pauseAfterMs` | DEPRECATE RECOMMENDED | replace during a later compatible Audio migration |

7.3A deliberately does not map `DPDSnapshot` into `SpeechGenerationRequest` and does not modify Provider behavior. That work belongs to Batch 7.3B Audio Projection.

## 7. Failure rules

Construction or composition fails fast for unsupported schema versions, wrong scope, empty direction objects, blank required fields, unknown/provider-specific fields, cross-layer reference mismatch, or missing effective requirements. No unknown field is silently ignored.
