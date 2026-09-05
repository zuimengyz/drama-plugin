# DPD Visual Projection and Realized Performance Contract v1

## Coordinated execution extension (7.5R-FIX)

`derive_visual_execution_timing` consumes the immutable planned holds/reaction,
complete actual turn durations, and target Video duration. It returns deterministic
projection material, not a new entity or timing acceptance. `executionTimingFingerprint`
on VisualPerformanceBrief binds that material; actual relative phase ranges, interaction,
gaze, gesture, transition purpose and boundaries also reach the motion prompt. Provider
execution remains approximate. Omitted execution material preserves the legacy path.

`RealizedPerformanceSnapshot.observedSpeakerKey` is optional: null means aggregate
Shot observation, and a speaker key scopes only that person's observed facts. A fresh
Video requires fresh observations and fingerprints. `evaluate_target_performance_fit`
requires all speakers, current Video/Audio hashes, and production-reviewed participation
evidence before constrained placement. Participation envelopes are interpretations,
not automatic mouth/head-to-speech anchors; UNKNOWN and CONFLICTING remain explicit.

Lip-sync capability and coordinate selection stay in adapter evidence. A mouth-only
derivative preserves the reconciled windows and original Audio, receives a distinct
Video hash and new mouth/identity/non-speaker/continuity observation. Source RP remains
historical evidence; post-lip RP binds the derivative. No new DPD authority is created.

## Authority and one-way flow

```text
DPDSnapshot (intended dramatic performance)
  -> VisualPerformanceBrief (intended visible performance)
  -> provider-neutral video generation request
  -> generated Video Media (actual pixels over time)
  -> accepted observation
  -> RealizedPerformanceSnapshot (realized visible performance)
```

`DPDSnapshot` owns objective, target, tactic, authority, relationship, internal activation, external control, subtext, dramatic action, observable intent, and boundaries. `VisualPerformanceBrief` may only translate those decisions into body activity, head behavior, gaze, facial tension, gesture policy, interaction orientation, pre-speech behavior, and visible control. It cannot reinterpret dramatic intent.

## Independent identity and camera inputs

Stable Character appearance comes from `MASTER_CHARACTER_CARD`, Character Asset, costume/face reference, and their stable Media. Stable Scene appearance comes from `MASTER_SCENE_CARD`, `SCENE_REFERENCE`, and their stable Media. The brief stores only the material identity fingerprints used for lineage; it never owns age, face, hair, costume, architecture, or historical location design.

Framing, shot scale, lens, angle, composition, blocking, and camera movement remain in the approved Shot design. `compile_video_motion_prompt()` is the materialization boundary where the performance brief, Shot action, and separate camera design are combined. Camera fields are forbidden in `VisualPerformanceBrief`.

## Fingerprints

The visual projection fingerprint is canonical SHA-256 of the complete brief except its stored fingerprint. Material input includes the DPD fingerprint, Shot identity/fingerprint, relevant Character and Scene visual identity fingerprints, schema version, and projected behavior. It excludes timestamp, UUID, Host, Provider job/workflow/node/model, temporary URL, response, and secret.

The provider-neutral video request fingerprint hashes the visual projection fingerprint, Shot id, fixed input mode, source Media content hash, camera-design fingerprint, compiled motion prompt, target duration, and `audioPolicy=NONE`. Provider task identity is not material.

The realized performance fingerprint hashes the video content hash, Shot id, observation schema version, and accepted canonical observed facts. Stable `videoMediaId` is retained for audit but excluded from the material hash, so alias imports of identical bytes and observation do not change the realized fact identity. Changed video bytes always change the fingerprint.

## Realized observation boundary

`RealizedPerformanceSnapshot` is a deterministic intermediate artifact, not a psychological interpretation or database entity. It records only observable scale/presence/orientation/gaze, head/body motion, activation/tension level, expression change, gesture, interaction distance, pre/post-speech action, mouth activity, and minimum useful millisecond windows. Mouth activity is not phoneme, viseme, or lip-sync analysis.

Observation uses controlled playback or representative frame sampling. Model output is a proposal; the fingerprint applies to the accepted canonical observation. Obscured or unreliable facts are `UNKNOWN`. Objective, tactic, relationship, subtext, internal activation, Provider fields, and Comfy identifiers are forbidden.

Video deviation from DPD is never a blocker. A diagnostic may state `ALIGNED`, `DEVIATED`, or `SIGNIFICANTLY_DEVIATED`, but the Snapshot must always describe the actual video. If the intended drama is wrong, revise DPD. If DPD is right but the video is wrong, revise Visual Projection, video parameters, or stable inputs; regenerate Video; observe again.

## Future final Audio invalidation

Batch 7.3D may define:

```text
FinalAudioProjectionFingerprint = hash(
  dpdFingerprint
  + voiceFingerprint
  + spokenContentFingerprint
  + realizedPerformanceFingerprint
)
```

Therefore Video V1 -> Realized A -> Audio A, while changed Video V2 -> Realized B makes Audio A `STALE` and requires regeneration. Audio must follow actual generated video performance. This contract defines lineage only; it does not implement Audio projection, TTS, dubbing, lip sync, mix, or AV mux.

No Java entity, database table, CRUD service, MCP search tool, or Visual service is required. The detailed Snapshot remains an Agent-side deterministic artifact; stable Media and existing open content can carry its reference/fingerprint when a later lifecycle decision needs persistence.
# Batch 7.5 dialogue-coupled production

`VisualPerformanceBrief` optionally carries `dialogueTimingPlanFingerprint`,
`dialogueSourceFingerprint` and `dialoguePerformancePhases`. These are a narrow
extension of the existing brief, with no independent storage or service.
Legacy briefs retain their original fingerprints by omitting absent dialogue
extension fields from fingerprint material.

`couple_dialogue_visual_performance` validates the ordered canonical SpokenContent,
production DPD and existing per-turn visual briefs against the unchanged planned
timing. Planning DPD and production DPD fingerprints remain distinct in the input
evidence. The source fingerprint includes both and the stable visual identities.
Phases contain only order, active speaker, listener, dramatic action, visible
focus, transition purpose and relative timing range; they never copy dialogue text.

`compile_video_motion_prompt` requires verified distinct visible labels for both
speakers and projects opening, speaking/listening, handoff/reaction and ending.
Relative ranges express production intent, not guaranteed provider timestamps.
`diagnose_dialogue_visual_compatibility` is an observation-scoped report diagnostic:
SUPPORTED / QUESTIONABLE / CONFLICTING / UNKNOWN. A wrong-speaker observation or
visible participation conflict cannot pass. Missing or stale observations remain
UNKNOWN. Lip-sync and user artistic acceptance remain separate gates.
