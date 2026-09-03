from __future__ import annotations

from pydantic import ValidationError
import pytest

from drama_plugin.contracts.av_sync import (
    AcousticMixPlan,
    AVSyncPlan,
    build_acoustic_mix_plan,
    build_av_sync_plan,
    final_shot_fingerprint,
)
from drama_plugin.contracts.base import dump_contract


VIDEO_HASH = "1" * 64
D1_HASH = "2" * 64


def sync_plan(
    *,
    timing_authority: str = "NONE",
    dialogue_start_ms: int | None = None,
    dialogue_end_ms: int | None = None,
    lip_sync_policy: str = "NOT_APPLIED_FOR_LOW_VISIBILITY",
    alignment_confidence: str = "UNKNOWN",
) -> AVSyncPlan:
    return build_av_sync_plan(
        shot_id="shot-1",
        spoken_content_id="spoken-1",
        speaker_key="speaker-1",
        video_media_id="media-video",
        video_content_hash=VIDEO_HASH,
        video_duration_ms=11_042,
        dialogue_media_id="media-d1",
        dialogue_content_hash=D1_HASH,
        dialogue_duration_ms=4_107,
        timing_authority=timing_authority,  # type: ignore[arg-type]
        dialogue_start_ms=dialogue_start_ms,
        dialogue_end_ms=dialogue_end_ms,
        lip_sync_policy=lip_sync_policy,  # type: ignore[arg-type]
        alignment_confidence=alignment_confidence,  # type: ignore[arg-type]
    )


def mix_plan(
    *,
    dialogue_hash: str = D1_HASH,
    ambience_bindings: dict[str, str] | None = None,
    sfx_bindings: dict[str, str] | None = None,
    ambience_gain_db: float | None = None,
    sfx_gain_db: float | None = None,
) -> AcousticMixPlan:
    return build_acoustic_mix_plan(
        work_id="work-1",
        scene_id="scene-1",
        shot_id="shot-1",
        dialogue_media_id="media-d1",
        dialogue_content_hash=dialogue_hash,
        dialogue_perspective="CLOSE_CONVERSATIONAL",
        ambience_bindings=ambience_bindings,
        sfx_bindings=sfx_bindings,
        spatial_treatment="NONE",
        dialogue_gain_db=0,
        ambience_gain_db=ambience_gain_db,
        sfx_gain_db=sfx_gain_db,
    )


def test_unknown_mouth_and_no_authority_preserve_unknown_timing() -> None:
    plan = sync_plan()
    assert plan.timing_authority == "NONE"
    assert plan.dialogue_start_ms is None
    assert plan.dialogue_end_ms is None
    assert plan.alignment_confidence == "UNKNOWN"


@pytest.mark.parametrize(
    ("start_ms", "end_ms", "message"),
    [
        (-1, 4_106, "greater than or equal"),
        (1_000, 500, "greater than dialogueStartMs"),
        (8_000, 12_107, "exceeds video duration"),
        (1_000, 4_000, "preserve the frozen D1 duration"),
    ],
)
def test_invalid_dialogue_windows_fail(
    start_ms: int, end_ms: int, message: str
) -> None:
    with pytest.raises((ValidationError, ValueError), match=message):
        sync_plan(
            timing_authority="EXPLICIT_PRODUCTION_ANCHOR",
            dialogue_start_ms=start_ms,
            dialogue_end_ms=end_ms,
            lip_sync_policy="NOT_REQUIRED",
            alignment_confidence="HIGH",
        )


def test_none_authority_cannot_fabricate_a_window() -> None:
    with pytest.raises(ValueError, match="cannot carry fabricated"):
        sync_plan(dialogue_start_ms=0, dialogue_end_ms=4_107)


def test_material_authority_requires_a_complete_window() -> None:
    with pytest.raises(ValueError, match="requires a complete dialogue window"):
        sync_plan(
            timing_authority="USER_REVIEW",
            lip_sync_policy="NOT_REQUIRED",
            alignment_confidence="HIGH",
        )


def test_lip_sync_policy_requires_matching_authority() -> None:
    with pytest.raises(ValueError, match="audio-driven timing authority"):
        sync_plan(
            timing_authority="EXPLICIT_PRODUCTION_ANCHOR",
            dialogue_start_ms=500,
            dialogue_end_ms=4_607,
            lip_sync_policy="AUDIO_DRIVEN_RETARGET",
            alignment_confidence="HIGH",
        )


def test_provider_and_psychological_fields_are_rejected() -> None:
    payload = dump_contract(sync_plan())
    payload["comfyWorkflowId"] = "workflow-1"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AVSyncPlan.model_validate(payload)
    payload = dump_contract(sync_plan())
    payload["subtext"] = "threaten"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AVSyncPlan.model_validate(payload)


def test_plan_fingerprints_are_deterministic_and_material() -> None:
    first = sync_plan()
    second = sync_plan()
    assert first.fingerprint == second.fingerprint
    assert first.fingerprint != sync_plan(lip_sync_policy="BLOCKED").fingerprint
    acoustic_first = mix_plan()
    acoustic_second = mix_plan()
    assert acoustic_first.fingerprint == acoustic_second.fingerprint


def test_hash_mismatch_invalidates_contract_fingerprint() -> None:
    payload = dump_contract(sync_plan())
    payload["dialogueContentHash"] = "3" * 64
    with pytest.raises(ValueError, match="fingerprint is invalid"):
        AVSyncPlan.model_validate(payload)


def test_acoustic_plan_rejects_provider_fields_and_unbound_levels() -> None:
    with pytest.raises(ValueError, match="ambience gain requires"):
        mix_plan(ambience_gain_db=-30)
    payload = dump_contract(mix_plan())
    payload["providerModel"] = "some-model"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AcousticMixPlan.model_validate(payload)


def test_acoustic_binding_ownership_is_checked_when_available() -> None:
    with pytest.raises(ValueError, match="another Work/Scene"):
        build_acoustic_mix_plan(
            work_id="work-1",
            scene_id="scene-1",
            shot_id="shot-1",
            dialogue_media_id="media-d1",
            dialogue_content_hash=D1_HASH,
            dialogue_perspective="CLOSE_CONVERSATIONAL",
            ambience_bindings={"media-room": "4" * 64},
            ambience_gain_db=-36,
            ambience_scope={"media-room": ("work-other", "scene-other")},
        )


def test_unresolved_placement_blocks_final_shot_lineage() -> None:
    with pytest.raises(ValueError, match="requires resolved dialogue placement"):
        final_shot_fingerprint(sync_plan=sync_plan(), mix_plan=mix_plan())


def test_final_shot_fingerprint_is_deterministic_and_goes_stale() -> None:
    resolved = sync_plan(
        timing_authority="USER_REVIEW",
        dialogue_start_ms=2_000,
        dialogue_end_ms=6_107,
        lip_sync_policy="NOT_REQUIRED",
        alignment_confidence="HIGH",
    )
    first = final_shot_fingerprint(sync_plan=resolved, mix_plan=mix_plan())
    assert first == final_shot_fingerprint(sync_plan=resolved, mix_plan=mix_plan())
    moved = sync_plan(
        timing_authority="USER_REVIEW",
        dialogue_start_ms=2_100,
        dialogue_end_ms=6_207,
        lip_sync_policy="NOT_REQUIRED",
        alignment_confidence="HIGH",
    )
    assert first != final_shot_fingerprint(sync_plan=moved, mix_plan=mix_plan())
    with pytest.raises(ValueError, match="different D1 hashes"):
        final_shot_fingerprint(
            sync_plan=resolved,
            mix_plan=mix_plan(dialogue_hash="3" * 64),
        )


def test_final_shot_requires_exact_acoustic_hashes() -> None:
    resolved = sync_plan(
        timing_authority="EXPLICIT_PRODUCTION_ANCHOR",
        dialogue_start_ms=0,
        dialogue_end_ms=4_107,
        lip_sync_policy="NOT_REQUIRED",
        alignment_confidence="HIGH",
    )
    acoustic = mix_plan(
        ambience_bindings={"media-room": "4" * 64},
        ambience_gain_db=-36,
    )
    with pytest.raises(ValueError, match="ambience hashes"):
        final_shot_fingerprint(sync_plan=resolved, mix_plan=acoustic)
    assert final_shot_fingerprint(
        sync_plan=resolved,
        mix_plan=acoustic,
        ambience_content_hashes=["4" * 64],
    )


def test_final_shot_rejects_a_mix_plan_for_another_shot() -> None:
    resolved = sync_plan(
        timing_authority="EXPLICIT_PRODUCTION_ANCHOR",
        dialogue_start_ms=0,
        dialogue_end_ms=4_107,
        lip_sync_policy="NOT_REQUIRED",
        alignment_confidence="HIGH",
    )
    other_shot_mix = build_acoustic_mix_plan(
        work_id="work-1",
        scene_id="scene-1",
        shot_id="shot-other",
        dialogue_media_id="media-d1",
        dialogue_content_hash=D1_HASH,
        dialogue_perspective="CLOSE_CONVERSATIONAL",
    )
    with pytest.raises(ValueError, match="different Shots"):
        final_shot_fingerprint(sync_plan=resolved, mix_plan=other_shot_mix)


def test_user_review_5200_anchor_derives_valid_9307_window() -> None:
    pending = sync_plan()
    approved_start_ms = 5_200
    actual_d1_duration_ms = 4_107
    approved = sync_plan(
        timing_authority="USER_REVIEW",
        dialogue_start_ms=approved_start_ms,
        dialogue_end_ms=approved_start_ms + actual_d1_duration_ms,
        lip_sync_policy="NOT_APPLIED_FOR_LOW_VISIBILITY",
        alignment_confidence="HIGH",
    )
    assert approved.dialogue_start_ms == 5_200
    assert approved.dialogue_end_ms == 9_307
    assert approved.dialogue_end_ms <= approved.video_duration_ms
    assert approved.fingerprint != pending.fingerprint
    assert approved.lip_sync_policy == "NOT_APPLIED_FOR_LOW_VISIBILITY"
