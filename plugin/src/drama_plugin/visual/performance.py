from __future__ import annotations

from typing import Any, Iterable

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import DPDSnapshot, PerformanceLevel
from drama_plugin.contracts.visual_performance import (
    RealizedPerformanceSnapshot,
    VisualPerformanceBrief,
)


class VisualProjectionError(ValueError):
    pass


def _brief_material(brief: VisualPerformanceBrief) -> dict[str, Any]:
    return dump_contract(brief, exclude={"fingerprint"})


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
) -> str:
    """Combine separate performance and Shot-owned camera facts for materialization."""

    if not shot_action.strip() or not camera_design.strip():
        raise VisualProjectionError("Shot action and camera design are required")
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


def _snapshot_material(snapshot: RealizedPerformanceSnapshot) -> dict[str, Any]:
    material = dump_contract(snapshot, exclude={"fingerprint", "video_media_id"})
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
