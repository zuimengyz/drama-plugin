from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import DPDSnapshot, PerformanceLevel
from drama_plugin.contracts.dialogue_timing import DialogueTimingPlan
from drama_plugin.dpd import compose_dpd
from drama_plugin.dialogue_timing import derive_visual_execution_timing
from drama_plugin.contracts.visual_performance import (
    RealizedPerformanceSnapshot,
    VisualPerformanceBrief,
)


class VisualProjectionError(ValueError):
    pass


def _brief_material(brief: VisualPerformanceBrief) -> dict[str, Any]:
    material = dump_contract(brief, exclude={"fingerprint"})
    if brief.execution_timing_fingerprint is None:
        material.pop("executionTimingFingerprint", None)
    # Preserve all pre-dialogue brief/request fingerprints byte for byte.
    if not brief.dialogue_performance_phases:
        for key in ("dialogueTimingPlanFingerprint", "dialogueSourceFingerprint", "dialoguePerformancePhases"):
            material.pop(key)
    return material


def fingerprint_visual_projection(brief: VisualPerformanceBrief) -> str:
    return sha256_canonical(_brief_material(brief))


def _visible_language(snapshot: DPDSnapshot) -> dict[str, str]:
    effective = snapshot.effective
    activation = effective.internal_activation
    control = effective.external_control
    target = effective.interaction_target

    if activation is PerformanceLevel.HIGH and control is PerformanceLevel.HIGH:
        body = "low-amplitude body activity with a stable posture under visible pressure"
        head = "restrained, deliberate head movement; avoid abrupt turns"
        face = "clearly visible facial muscle tension without exaggerated distortion"
        gesture = "restrained gestures limited to task-directed emphasis"
        pre_speech = "briefly observe the interaction target before visible mouth activity"
        visible_control = "high visible control: stillness carries pressure without passivity"
    elif activation is PerformanceLevel.HIGH and control is PerformanceLevel.LOW:
        body = "larger-amplitude body activity with visibly unstable recovery"
        head = "quicker head movement with uneven settling"
        face = "high visible facial tension with an observable expression change"
        gesture = "allow broader gestures while preserving readable action"
        pre_speech = "enter speech with little settling time after the preceding movement"
        visible_control = "low visible control: pressure escapes into movement"
    elif activation is PerformanceLevel.MEDIUM and control is PerformanceLevel.HIGH:
        body = "low-to-medium body activity with a stable base"
        head = "small responsive head adjustments with controlled recovery"
        face = "moderate facial tension with contained variation"
        gesture = "use sparse, low-amplitude gestures"
        pre_speech = "hold a short observation beat before visible mouth activity"
        visible_control = "high visible control with responsive rather than rigid stillness"
    else:
        body = (
            f"{activation.value.lower()} visible body activation with "
            f"{control.value.lower()} movement control"
        )
        head = "proportionate head movement with a readable return to the interaction"
        face = "proportionate visible facial tension without an emotion label"
        gesture = "use only gestures that make the current dramatic action readable"
        pre_speech = "show a readable transition into visible mouth activity"
        visible_control = f"keep visible control at {control.value.lower()} level"

    if control is PerformanceLevel.LOW:
        gaze = f"allow brief gaze breaks, then visibly reacquire {target}"
    else:
        gaze = f"keep gaze predominantly directed toward {target}; avoid unmotivated scanning"

    return {
        "body_activity": body,
        "head_behavior": head,
        "gaze_behavior": gaze,
        "facial_tension": face,
        "gesture_policy": gesture,
        "interaction_orientation": f"keep the body and face spatially oriented toward {target}",
        "pre_speech_behavior": pre_speech,
        "visible_control": visible_control,
    }


def project_visual_performance(
    *,
    dpd_snapshot: DPDSnapshot,
    shot_id: str,
    shot_scene_id: str,
    shot_fingerprint: str,
    shot_spoken_content_ids: Iterable[str],
    shot_character_keys: Iterable[str],
    primary_character_key: str,
    character_identity_key: str,
    character_visual_identity_fingerprint: str,
    scene_visual_identity_fingerprint: str,
) -> VisualPerformanceBrief:
    """Translate authoritative DPD into visible behavior without camera or identity design."""

    if dpd_snapshot is None:
        raise VisualProjectionError("DPDSnapshot is required")
    effective = dpd_snapshot.effective
    if not shot_id.strip() or not shot_scene_id.strip():
        raise VisualProjectionError("shot identity is required")
    if effective.scene_id != shot_scene_id:
        raise VisualProjectionError("DPD and Shot scene mismatch")
    if dpd_snapshot.line.spoken_content_id not in tuple(shot_spoken_content_ids):
        raise VisualProjectionError("DPD speaker line is not bound to the Shot")
    if primary_character_key not in tuple(shot_character_keys):
        raise VisualProjectionError("primary character is not visible in the Shot")
    if character_identity_key != primary_character_key:
        raise VisualProjectionError("wrong Character visual identity supplied")
    if effective.actor != primary_character_key or effective.speaker != primary_character_key:
        raise VisualProjectionError("DPD actor/speaker and primary character mismatch")

    material: dict[str, Any] = {
        "schemaVersion": "visual-performance-brief-v1",
        "dpdFingerprint": dpd_snapshot.fingerprint,
        "sceneId": shot_scene_id,
        "shotId": shot_id,
        "shotFingerprint": shot_fingerprint,
        "primaryCharacterKey": primary_character_key,
        "characterVisualIdentityFingerprint": character_visual_identity_fingerprint,
        "sceneVisualIdentityFingerprint": scene_visual_identity_fingerprint,
        **_visible_language(dpd_snapshot),
        "performanceBoundaries": effective.performance_boundaries,
    }
    provisional = VisualPerformanceBrief.model_validate(
        {**material, "fingerprint": "0" * 64}
    )
    return provisional.model_copy(
        update={"fingerprint": fingerprint_visual_projection(provisional)}
    )


def compile_video_motion_prompt(
    *,
    brief: VisualPerformanceBrief,
    shot_action: str,
    camera_design: str,
    speaker_labels: Mapping[str, str] | None = None,
) -> str:
    """Combine separate performance and Shot-owned camera facts for materialization."""

    if not shot_action.strip() or not camera_design.strip():
        raise VisualProjectionError("Shot action and camera design are required")
    if brief.fingerprint != fingerprint_visual_projection(brief):
        raise VisualProjectionError("STALE_VISUAL_PERFORMANCE_BRIEF")
    if brief.dialogue_performance_phases:
        phases = brief.dialogue_performance_phases
        labels = speaker_labels or {}
        speakers = {p.active_speaker for p in phases if p.active_speaker} | {p.listener for p in phases}
        if set(labels) != speakers or any(not label.strip() for label in labels.values()) or len(set(labels.values())) != len(labels):
            raise VisualProjectionError("VERIFIED_DISTINCT_SPEAKER_LABELS_REQUIRED")
        directions = []
        for phase in phases:
            role = (f"{labels[phase.active_speaker]} speaks TO {labels[phase.listener]}; {labels[phase.listener]} listens"
                    if phase.active_speaker else f"Nobody speaks; reaction focus on {labels[phase.listener]}")
            start, end = phase.relative_timing_range
            if brief.execution_timing_fingerprint:
                directions.append(f"{phase.order} ({start:.0%}-{end:.0%}): {role}. {phase.dramatic_action}; {phase.visible_performance_focus}; {phase.transition_purpose}.")
                continue
            directions.append(f"{phase.order} ({start:.0%}-{end:.0%} approx): {role}. {phase.dramatic_action}. {phase.visible_performance_focus}.")
        prompt = (f"ACTION: {shot_action}. ORDERED PERFORMANCE, relative phases, not exact speech timestamps: "
                  + " ".join(directions) + f" CAMERA: {camera_design}. "
                  "Keep both faces readable; no simultaneous speaking. Preserve identities, beard, costume, props and background; "
                  "one continuous shot. Restrained gaze, head and breath changes; no broad gestures, shouting, standing or table strikes.")
        if brief.execution_timing_fingerprint:
            boundaries = "; ".join(brief.performance_boundaries)
            prompt += f" Boundaries: {boundaries}."
        if len(prompt) > 2000:
            raise VisualProjectionError("compiled video motion prompt exceeds 2000 characters")
        return prompt
    performance = "; ".join(
        (
            brief.body_activity,
            brief.head_behavior,
            brief.gaze_behavior,
            brief.facial_tension,
            brief.gesture_policy,
            brief.interaction_orientation,
            brief.pre_speech_behavior,
            brief.visible_control,
        )
    )
    boundaries = "; ".join(brief.performance_boundaries) or "no additional boundary"
    prompt = (
        f"ACTION: {shot_action}. PERFORMANCE: {performance}. "
        f"PERFORMANCE BOUNDARIES: {boundaries}. CAMERA: {camera_design}. "
        "Preserve the source image identities, costume, environment, props, and composition; "
        "one continuous shot; no new characters; no identity or costume changes."
    )
    if len(prompt) > 2000:
        raise VisualProjectionError("compiled video motion prompt exceeds 2000 characters")
    return prompt


def fingerprint_video_generation_request(
    *,
    brief: VisualPerformanceBrief,
    source_media_content_hash: str,
    camera_design_fingerprint: str,
    motion_prompt: str,
    target_duration_ms: int,
) -> str:
    if target_duration_ms <= 0:
        raise VisualProjectionError("target video duration must be positive")
    if brief.fingerprint != fingerprint_visual_projection(brief):
        raise VisualProjectionError("STALE_VISUAL_PERFORMANCE_BRIEF")
    return sha256_canonical(
        {
            "schemaVersion": "video-generation-request-v1",
            "visualProjectionFingerprint": brief.fingerprint,
            "shotId": brief.shot_id,
            "inputMode": "SINGLE_IMAGE",
            "sourceMediaContentHash": source_media_content_hash,
            "cameraDesignFingerprint": camera_design_fingerprint,
            "motionPrompt": motion_prompt,
            "targetDurationMs": target_duration_ms,
            "audioPolicy": "NONE",
        }
    )


def couple_dialogue_visual_performance(
    *, plan: DialogueTimingPlan, ordered_spoken_content: Sequence[Mapping[str, Any]],
    dpd_by_spoken_content: Mapping[str, DPDSnapshot],
    briefs_by_spoken_content: Mapping[str, VisualPerformanceBrief],
    execution_timing: Mapping[str, Any] | None = None,
) -> VisualPerformanceBrief:
    """Extend existing per-line briefs with ordered relative visual phases.

    Production DPD may differ from planning DPD; both lineages remain explicit.
    No actual audio duration, provider, or copied full dialogue enters a phase.
    """
    plan = DialogueTimingPlan.model_validate(dump_contract(plan))
    if plan.status != "PLANNED":
        raise VisualProjectionError("TIMING_CONFLICT")
    ids = [t.spoken_content_id for t in plan.turns]
    if [s.get("id") for s in ordered_spoken_content] != ids:
        raise VisualProjectionError("SPOKEN_TURN_ORDER_MISMATCH")
    if set(dpd_by_spoken_content) != set(ids) or set(briefs_by_spoken_content) != set(ids):
        raise VisualProjectionError("COMPLETE_PRODUCTION_DPD_AND_BRIEFS_REQUIRED")
    sources: list[dict[str, Any]] = []
    phases: list[dict[str, Any]] = []
    duration = plan.planned_duration_ms
    execution_turns: dict[str, Any] = {}
    if execution_timing is not None:
        checked = derive_visual_execution_timing(plan=plan,
            actual_durations_ms={t["spokenContentId"]: t["durationMs"] for t in execution_timing["turns"]},
            target_video_duration_ms=execution_timing["targetVideoDurationMs"])
        if checked != execution_timing:
            raise VisualProjectionError("STALE_VISUAL_EXECUTION_TIMING")
        duration = checked["targetVideoDurationMs"]
        execution_turns = {t["spokenContentId"]: t for t in checked["turns"]}
    speakers = {t.speaker_key for t in plan.turns}
    if len(speakers) != 2:
        raise VisualProjectionError("TWO_PERSON_DIALOGUE_REQUIRED")

    def add(active: str | None, listener: str, action: str, focus: str, purpose: str, start: int, end: int) -> None:
        if end > start:
            phases.append({"order": len(phases) + 1, "activeSpeaker": active, "listener": listener,
                           "dramaticAction": action, "visiblePerformanceFocus": focus,
                           "transitionPurpose": purpose, "relativeTimingRange": [start / duration, end / duration]})

    add(None, plan.turns[0].speaker_key, "establish mutual attention", "both seated and oriented toward each other",
        "opening", 0, plan.pre_dialogue_hold_ms)
    boundaries: list[str] = []
    for turn, spoken in zip(plan.turns, ordered_spoken_content):
        dpd = dpd_by_spoken_content[turn.spoken_content_id]
        brief = briefs_by_spoken_content[turn.spoken_content_id]
        if dpd != compose_dpd(dpd.scene, dpd.beat, dpd.line) or brief.fingerprint != fingerprint_visual_projection(brief):
            raise VisualProjectionError("STALE_PRODUCTION_DIRECTION")
        if (spoken.get("speakerKey") != turn.speaker_key or spoken.get("kind") != "DIALOGUE"
                or dpd.effective.speaker != turn.speaker_key or dpd.effective.actor != turn.speaker_key
                or dpd.line.spoken_content_id != turn.spoken_content_id or dpd.effective.scene_id != plan.scene_id
                or brief.dpd_fingerprint != dpd.fingerprint or brief.primary_character_key != turn.speaker_key
                or brief.shot_id != plan.shot_id or brief.scene_id != plan.scene_id):
            raise VisualProjectionError("DIALOGUE_SPEAKER_DPD_SCOPE_MISMATCH")
        fields = ("id", "kind", "speakerKey", "text", "intent", "mustKeep", "performanceIntent", "provenance", "estimatedDurationMs")
        if sha256_canonical({k: spoken.get(k) for k in fields}) != turn.spoken_content_fingerprint:
            raise VisualProjectionError("STALE_PLANNED_SPOKEN_CONTENT")
        listener = dpd.effective.interaction_target
        if listener not in speakers or listener == turn.speaker_key:
            raise VisualProjectionError("VISIBLE_LISTENER_REQUIRED")
        start = execution_turns.get(turn.spoken_content_id, {}).get("startMs", turn.planned_start_ms)
        end = execution_turns.get(turn.spoken_content_id, {}).get("endMs", turn.planned_end_ms)
        if turn.sequence > 1:
            add(None, turn.speaker_key, "previous speaker stops and yields the floor",
                "incoming speaker makes a small gaze/head response; partner holds still",
                "reaction and speaker handoff", start - turn.transition_hold_ms, start)
        focus = ("small target-directed head and facial changes; listener holds attentive gaze" if dpd.effective.external_control == PerformanceLevel.HIGH
                 else "responsive head and body movement; listener remains attentive")
        if execution_timing is not None:
            focus = "; ".join((brief.interaction_orientation, brief.gaze_behavior, brief.gesture_policy))
        add(turn.speaker_key, listener, dpd.effective.dramatic_action, focus,
            dpd.line.observable_intent, start, end)
        sources.append({"spokenContentId": turn.spoken_content_id, "speakerKey": turn.speaker_key,
            "spokenFingerprint": turn.spoken_content_fingerprint, "planningDpdFingerprint": turn.dpd_fingerprint,
            "productionDpdFingerprint": dpd.fingerprint, "visualBriefFingerprint": brief.fingerprint})
        boundaries.extend(brief.performance_boundaries)
    add(None, plan.turns[-1].speaker_key, "response ends; both hold the changed exchange",
        "speaking mouth settles; partner remains oriented toward the responder", "ending",
        execution_turns.get(ids[-1], {}).get("endMs", plan.turns[-1].planned_end_ms), duration)
    material = dump_contract(briefs_by_spoken_content[ids[0]])
    material.update(dialogueTimingPlanFingerprint=plan.fingerprint,
                    dialogueSourceFingerprint=sha256_canonical(sources),
                    dialoguePerformancePhases=phases, performanceBoundaries=list(dict.fromkeys(boundaries)))
    if execution_timing is not None:
        material["executionTimingFingerprint"] = execution_timing["fingerprint"]
    coupled = VisualPerformanceBrief.model_validate(material)
    return coupled.model_copy(update={"fingerprint": fingerprint_visual_projection(coupled)})


def diagnose_dialogue_visual_compatibility(
    *, brief: VisualPerformanceBrief, observed_phases: Sequence[Mapping[str, Any]],
    video_content_hash: str, observed_video_content_hash: str,
) -> str:
    """Report-only visible participation gate. Mouth activity never proves intent."""
    if not brief.dialogue_performance_phases or video_content_hash != observed_video_content_hash:
        return "UNKNOWN"
    if brief.fingerprint != fingerprint_visual_projection(brief):
        raise VisualProjectionError("STALE_VISUAL_PERFORMANCE_BRIEF")
    if len(observed_phases) != len(brief.dialogue_performance_phases):
        return "UNKNOWN"
    statuses = []
    for phase, observation in zip(brief.dialogue_performance_phases, observed_phases):
        if observation.get("order") != phase.order:
            return "UNKNOWN"
        if observation.get("activeSpeaker") != phase.active_speaker or observation.get("listener") != phase.listener:
            return "CONFLICTING"
        values = [observation.get(k, "UNKNOWN") for k in ("activeParticipation", "listenerBehavior", "transitionBehavior")]
        if observation.get("wrongSpeakerMouth") is True or "CONFLICTING" in values:
            return "CONFLICTING"
        if any(v not in {"SUPPORTED", "QUESTIONABLE", "CONFLICTING", "UNKNOWN"} for v in values):
            raise VisualProjectionError("INVALID_OBSERVATION_DIAGNOSTIC")
        statuses.extend(values)
    return "UNKNOWN" if "UNKNOWN" in statuses else "QUESTIONABLE" if "QUESTIONABLE" in statuses else "SUPPORTED"


def _snapshot_material(snapshot: RealizedPerformanceSnapshot) -> dict[str, Any]:
    material = dump_contract(snapshot, exclude={"fingerprint", "video_media_id"})
    if snapshot.observed_speaker_key is None:
        material.pop("observedSpeakerKey", None)
    return material


def fingerprint_realized_performance(snapshot: RealizedPerformanceSnapshot) -> str:
    return sha256_canonical(_snapshot_material(snapshot))


def build_realized_performance_snapshot(
    observed: dict[str, Any],
) -> RealizedPerformanceSnapshot:
    """Validate an accepted observation result and fingerprint its canonical facts."""

    provisional = RealizedPerformanceSnapshot.model_validate(
        {**observed, "fingerprint": "0" * 64}
    )
    return provisional.model_copy(
        update={"fingerprint": fingerprint_realized_performance(provisional)}
    )
