from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from drama_plugin.contracts import (
    BeatDPD,
    LineDPD,
    RealizedPerformanceSnapshot,
    SceneDPD,
    VisualPerformanceBrief,
)
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.dpd import compose_dpd
from drama_plugin.visual import (
    VisualProjectionError,
    build_realized_performance_snapshot,
    compile_video_motion_prompt,
    fingerprint_realized_performance,
    fingerprint_video_generation_request,
    fingerprint_visual_projection,
    project_visual_performance,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/dpd-core-v1.yaml"


def snapshot(*, external_control: str = "HIGH"):
    value = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    dialogue = value["dialogue"]
    case = deepcopy(value["cases"][0])
    case["beat"]["direction"]["externalControl"] = external_control
    scene = case["scene"]
    beat = {
        **case["beat"],
        "sceneId": scene["sceneId"],
    }
    line = {
        **case["line"],
        "sceneId": scene["sceneId"],
        "beatId": beat["beatId"],
        "spokenContentId": dialogue["spokenContentId"],
        "speaker": dialogue["speakerKey"],
    }
    return compose_dpd(
        SceneDPD.model_validate(scene),
        BeatDPD.model_validate(beat),
        LineDPD.model_validate(line),
    )


def project(*, external_control: str = "HIGH") -> VisualPerformanceBrief:
    current = snapshot(external_control=external_control)
    return project_visual_performance(
        dpd_snapshot=current,
        shot_id="shot-consequence",
        shot_scene_id=current.effective.scene_id,
        shot_fingerprint="1" * 64,
        shot_spoken_content_ids=(current.line.spoken_content_id,),
        shot_character_keys=(current.effective.actor, "speaker:listener"),
        primary_character_key=current.effective.actor,
        character_identity_key=current.effective.actor,
        character_visual_identity_fingerprint="2" * 64,
        scene_visual_identity_fingerprint="3" * 64,
    )


def observed(**updates: object) -> dict[str, object]:
    base: dict[str, object] = {
        "videoMediaId": "media-video-1",
        "videoContentHash": "4" * 64,
        "shotId": "shot-consequence",
        "videoDurationMs": 10000,
        "shotScale": "medium two-shot",
        "speakerScreenPresence": "primary speaker remains fully visible",
        "speakerOrientation": "three-quarter profile toward interaction partner",
        "gazeDirection": "predominantly toward interaction partner",
        "headMotion": "one small downward adjustment followed by a stable hold",
        "bodyMotion": "low-amplitude forward settling",
        "visibleActivation": "MEDIUM",
        "facialTension": "HIGH",
        "expressionChange": "PRESENT",
        "gestureActivity": "one low-amplitude hand emphasis",
        "interactionDistance": "across one narrow table",
        "preSpeechAction": "holds gaze before mouth activity",
        "mouthActivity": "PRESENT",
        "postSpeechAction": "returns to a stable hold",
        "speakerVisibleStartMs": 0,
        "preSpeechMotionWindowMs": [0, 800],
        "mouthActivityWindowsMs": [[900, 3300], [4700, 6800]],
        "majorHeadMotionWindowsMs": [[300, 700]],
        "majorGestureWindowsMs": [[2400, 3100]],
        "visiblePauseWindowsMs": [[3300, 4700]],
        "postSpeechHoldMs": 2500,
        "observationMethod": "CONTROLLED_FRAME_SAMPLING",
    }
    base.update(updates)
    return base


def test_high_activation_high_control_projects_composed_visible_behavior() -> None:
    brief = project()
    assert "low-amplitude" in brief.body_activity
    assert "stable posture" in brief.body_activity
    assert "abrupt turns" in brief.head_behavior
    assert "predominantly directed" in brief.gaze_behavior
    assert "facial muscle tension" in brief.facial_tension
    assert "restrained gestures" in brief.gesture_policy
    assert "briefly observe" in brief.pre_speech_behavior
    assert "high visible control" in brief.visible_control


def test_material_dpd_change_changes_projection_without_mutating_dpd() -> None:
    controlled_snapshot = snapshot()
    before = dump_contract(controlled_snapshot)
    controlled = project()
    uncontrolled = project(external_control="LOW")
    assert controlled.fingerprint != uncontrolled.fingerprint
    assert controlled.body_activity != uncontrolled.body_activity
    assert "larger-amplitude" in uncontrolled.body_activity
    assert dump_contract(controlled_snapshot) == before


def test_projection_and_request_fingerprints_are_deterministic() -> None:
    first = project()
    second = project()
    assert first == second
    assert fingerprint_visual_projection(first) == first.fingerprint

    prompt = compile_video_motion_prompt(
        brief=first,
        shot_action="the speaker rejects the proposal across the campaign table",
        camera_design="hold the approved medium two-shot without reframing",
    )
    request_a = fingerprint_video_generation_request(
        brief=first,
        source_media_content_hash="5" * 64,
        camera_design_fingerprint="6" * 64,
        motion_prompt=prompt,
        target_duration_ms=10000,
    )
    request_b = fingerprint_video_generation_request(
        brief=second,
        source_media_content_hash="5" * 64,
        camera_design_fingerprint="6" * 64,
        motion_prompt=prompt,
        target_duration_ms=10000,
    )
    assert request_a == request_b
    assert request_a != fingerprint_video_generation_request(
        brief=project(external_control="LOW"),
        source_media_content_hash="5" * 64,
        camera_design_fingerprint="6" * 64,
        motion_prompt=compile_video_motion_prompt(
            brief=project(external_control="LOW"),
            shot_action="the speaker rejects the proposal across the campaign table",
            camera_design="hold the approved medium two-shot without reframing",
        ),
        target_duration_ms=10000,
    )


def test_camera_and_stable_identity_stay_outside_performance_contract() -> None:
    brief = project()
    forbidden = {
        "framing",
        "shot_scale",
        "lens",
        "camera_angle",
        "camera_movement",
        "costume",
        "face",
        "hair",
        "location_design",
    }
    assert forbidden.isdisjoint(VisualPerformanceBrief.model_fields)
    prompt = compile_video_motion_prompt(
        brief=brief,
        shot_action="reject the proposal",
        camera_design="medium close-up, locked camera",
    )
    assert "CAMERA: medium close-up, locked camera" in prompt
    assert "medium close-up" not in dump_contract(brief).values()


def test_projection_rejects_missing_dpd_shot_speaker_and_identity_mismatch() -> None:
    current = snapshot()
    common = {
        "dpd_snapshot": current,
        "shot_id": "shot-consequence",
        "shot_scene_id": current.effective.scene_id,
        "shot_fingerprint": "1" * 64,
        "shot_spoken_content_ids": (current.line.spoken_content_id,),
        "shot_character_keys": (current.effective.actor,),
        "primary_character_key": current.effective.actor,
        "character_identity_key": current.effective.actor,
        "character_visual_identity_fingerprint": "2" * 64,
        "scene_visual_identity_fingerprint": "3" * 64,
    }
    with pytest.raises(VisualProjectionError, match="DPDSnapshot"):
        project_visual_performance(**{**common, "dpd_snapshot": None})  # type: ignore[arg-type]
    with pytest.raises(VisualProjectionError, match="scene mismatch"):
        project_visual_performance(**{**common, "shot_scene_id": "scene-other"})
    with pytest.raises(VisualProjectionError, match="not bound"):
        project_visual_performance(**{**common, "shot_spoken_content_ids": ("spoken-other",)})
    with pytest.raises(VisualProjectionError, match="wrong Character"):
        project_visual_performance(**{**common, "character_identity_key": "speaker:other"})


def test_visual_contract_rejects_unknown_provider_camera_and_empty_direction() -> None:
    payload = dump_contract(project())
    with pytest.raises(ValidationError, match="schemaVersion"):
        VisualPerformanceBrief.model_validate(
            {**payload, "schemaVersion": "visual-performance-brief-v2"}
        )
    with pytest.raises(ValidationError):
        VisualPerformanceBrief.model_validate({**payload, "comfyNodeId": "424"})
    with pytest.raises(ValidationError):
        VisualPerformanceBrief.model_validate({**payload, "cameraAngle": "low"})
    with pytest.raises(ValidationError):
        VisualPerformanceBrief.model_validate({**payload, "bodyActivity": " "})
    assert {
        "provider",
        "workflow",
        "model",
        "task_id",
        "node_id",
        "temporary_url",
    }.isdisjoint(VisualPerformanceBrief.model_fields)


def test_snapshot_fingerprint_is_deterministic_and_media_id_is_nonmaterial() -> None:
    first = build_realized_performance_snapshot(observed())
    reordered = dict(reversed(list(observed().items())))
    second = build_realized_performance_snapshot(reordered)
    alias = build_realized_performance_snapshot(
        observed(videoMediaId="media-video-alias")
    )
    assert first == second
    assert fingerprint_realized_performance(first) == first.fingerprint
    assert alias.fingerprint == first.fingerprint


def test_video_byte_change_changes_snapshot_and_future_audio_lineage() -> None:
    first = build_realized_performance_snapshot(observed())
    second = build_realized_performance_snapshot(observed(videoContentHash="7" * 64))
    assert first.fingerprint != second.fingerprint

    fixed = {
        "schemaVersion": "future-final-audio-projection-v1",
        "dpdFingerprint": "8" * 64,
        "voiceFingerprint": "9" * 64,
        "spokenContentFingerprint": "a" * 64,
    }
    audio_a = sha256_canonical(
        {**fixed, "realizedPerformanceFingerprint": first.fingerprint}
    )
    audio_b = sha256_canonical(
        {**fixed, "realizedPerformanceFingerprint": second.fingerprint}
    )
    assert audio_a != audio_b


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"schemaVersion": "realized-performance-snapshot-v2"}, "schemaVersion"),
        ({"mouthActivityWindowsMs": [[4000, 3000]]}, "ends before"),
        ({"mouthActivityWindowsMs": [[900, 11000]]}, "outside video"),
        ({"speakerVisibleStartMs": 11000}, "visible start"),
        ({"mouthActivity": "PRESENT", "mouthActivityWindowsMs": []}, "requires"),
        ({"mouthActivity": "UNKNOWN", "mouthActivityWindowsMs": [[900, 1000]]}, "require"),
    ],
)
def test_snapshot_rejects_invalid_version_and_timestamps(
    updates: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        build_realized_performance_snapshot(observed(**updates))


def test_snapshot_rejects_provider_and_psychological_authority_fields() -> None:
    for field, value in (
        ("comfyTaskId", "task-1"),
        ("providerModel", "model-1"),
        ("objective", "intimidate"),
        ("subtext", "threaten"),
        ("relationship", "dominant"),
        ("internalActivation", "HIGH"),
    ):
        with pytest.raises(ValidationError):
            build_realized_performance_snapshot(observed(**{field: value}))
    assert {
        "objective",
        "subtext",
        "relationship",
        "internal_activation",
        "provider",
        "model",
        "workflow",
        "task_id",
    }.isdisjoint(RealizedPerformanceSnapshot.model_fields)
