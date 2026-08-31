from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from drama_plugin.audio import (
    AudioProjectionError,
    compile_projected_speech_request,
    fingerprint_audio_projection,
    project_audio_performance,
)
from drama_plugin.contracts import (
    AudioCapabilityDiagnostic,
    AudioPerformanceBrief,
    BeatDPD,
    CapabilityStatus,
    CreativeVoiceProfile,
    LineDPD,
    SceneDPD,
    SpeechGenerationRequest,
    TargetTimingPolicy,
    VoiceProfile,
)
from drama_plugin.dpd import compose_dpd
from drama_plugin.providers.speech.fish_audio import (
    FishAudioPerformanceMapping,
    map_audio_performance_to_fish,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/dpd-core-v1.yaml"


def voice() -> VoiceProfile:
    return VoiceProfile(
        profile_id="profile:shared-questioner",
        speaker_key="speaker:questioner",
        creative_profile=CreativeVoiceProfile(
            vocal_age="MATURE_ADULT",
            vocal_weight="MEDIUM",
            resonance_depth="BALANCED",
            texture="CLEAN_SUBTLE_GRAIN",
            baseline_pace="MODERATE",
            articulation_firmness="FIRM",
        ),
    )


def inputs() -> tuple[dict[str, object], list[dict[str, object]]]:
    value = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    return value["dialogue"], value["cases"]


def snapshot(case: dict[str, object]):
    dialogue, _ = inputs()
    scene = deepcopy(case["scene"])
    beat = deepcopy(case["beat"])
    line = deepcopy(case["line"])
    beat["sceneId"] = scene["sceneId"]
    line.update(
        {
            "sceneId": scene["sceneId"],
            "beatId": beat["beatId"],
            "spokenContentId": dialogue["spokenContentId"],
            "speaker": dialogue["speakerKey"],
        }
    )
    return compose_dpd(
        SceneDPD.model_validate(scene),
        BeatDPD.model_validate(beat),
        LineDPD.model_validate(line),
    )


def briefs() -> list[AudioPerformanceBrief]:
    dialogue, cases = inputs()
    profile = voice()
    return [
        project_audio_performance(
            dpd_snapshot=snapshot(case),
            spoken_content=dialogue,
            voice_profile=profile,
            voice_identity_ref="voice:shared-questioner",
            timing_policy=TargetTimingPolicy(policy="NATURAL"),
        )
        for case in cases
    ]


def test_same_text_voice_and_casting_project_to_three_distinct_briefs() -> None:
    projected = briefs()
    assert len({item.text_fingerprint for item in projected}) == 1
    assert len({item.voice_profile_fingerprint for item in projected}) == 1
    assert {item.voice_identity_ref for item in projected} == {"voice:shared-questioner"}
    assert [item.fingerprint for item in projected] == [
        "32156da4aeb80b256fa5f530f4a78f6220068a12c05e6b26efa0fd73e6ced402",
        "cb6ef44964874e49397aa9b9e831e405b945d0f8c9792a051817c52e5c29a67c",
        "80742a6dd707f3bd95dc758ed0451880a808c0a7b87baa55c5e67a1bcdc4d8b2",
    ]
    assert [(item.pace_tendency.value, item.volume_tendency.value) for item in projected] == [
        ("SLOWER", "NEUTRAL"),
        ("NEUTRAL", "LOWER"),
        ("SLOWER", "LOWER"),
    ]
    assert "loudness" in projected[0].articulation
    assert "observe" in projected[1].pace
    assert "superior" in projected[2].sentence_ending


def test_projection_and_fingerprint_are_deterministic_and_do_not_mutate_dpd() -> None:
    dialogue, cases = inputs()
    current = snapshot(cases[0])
    before = current.model_dump(mode="json", by_alias=True)
    first = project_audio_performance(
        dpd_snapshot=current,
        spoken_content=dialogue,
        voice_profile=voice(),
        voice_identity_ref="voice:shared-questioner",
        timing_policy=TargetTimingPolicy(policy="NATURAL"),
    )
    second = project_audio_performance(
        dpd_snapshot=current.model_copy(deep=True),
        spoken_content=dict(reversed(list(dialogue.items()))),
        voice_profile=voice(),
        voice_identity_ref="voice:shared-questioner",
        timing_policy=TargetTimingPolicy(policy="NATURAL"),
    )
    assert first == second
    assert fingerprint_audio_projection(first) == first.fingerprint
    assert current.model_dump(mode="json", by_alias=True) == before


def test_fish_mapping_is_explicit_bounded_and_distinct() -> None:
    mappings = [map_audio_performance_to_fish(item) for item in briefs()]
    assert [(item.speed, item.volume) for item in mappings] == [
        (0.92, 0.0),
        (1.0, -2.0),
        (0.92, -2.0),
    ]
    statuses = {
        item.dimension: item.status.value for item in mappings[0].capabilities
    }
    assert statuses == {
        "pace": "SUPPORTED",
        "volumeTendency": "SUPPORTED",
        "rhythm": "TEXT_RENDERABLE",
        "intensity": "TEXT_RENDERABLE",
        "pauseStrategy": "TEXT_RENDERABLE",
        "articulation": "UNSUPPORTED",
        "emphasis": "TEXT_RENDERABLE",
        "sentenceEnding": "TEXT_RENDERABLE",
        "control": "TEXT_RENDERABLE",
        "preUtterancePreparation": "APPROXIMATED",
        "postUtteranceHold": "UNSUPPORTED",
    }


def test_projection_validation_rejects_missing_or_mismatched_inputs() -> None:
    dialogue, cases = inputs()
    current = snapshot(cases[0])
    common = {
        "dpd_snapshot": current,
        "spoken_content": dialogue,
        "voice_profile": voice(),
        "voice_identity_ref": "voice:shared-questioner",
        "timing_policy": TargetTimingPolicy(policy="NATURAL"),
    }
    with pytest.raises(AudioProjectionError, match="DPDSnapshot"):
        project_audio_performance(**{**common, "dpd_snapshot": None})  # type: ignore[arg-type]
    with pytest.raises(AudioProjectionError, match="identity mismatch"):
        project_audio_performance(**{**common, "spoken_content": {**dialogue, "spokenContentId": "other"}})
    with pytest.raises(AudioProjectionError, match="speaker mismatch"):
        project_audio_performance(**{**common, "spoken_content": {**dialogue, "speakerKey": "speaker:other"}})
    missing_baseline = voice().model_copy(
        update={"creative_profile": CreativeVoiceProfile(baseline_pace="UNKNOWN")}
    )
    with pytest.raises(AudioProjectionError, match="baseline pace"):
        project_audio_performance(**{**common, "voice_profile": missing_baseline})
    with pytest.raises(AudioProjectionError, match="identity reference"):
        project_audio_performance(**{**common, "voice_identity_ref": ""})


def test_projection_contract_rejects_version_unknown_and_provider_fields() -> None:
    payload = briefs()[0].model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError, match="schemaVersion"):
        AudioPerformanceBrief.model_validate({**payload, "schemaVersion": "audio-projection-v2"})
    with pytest.raises(ValidationError):
        AudioPerformanceBrief.model_validate({**payload, "fishVoiceId": "provider-voice"})
    with pytest.raises(ValidationError):
        AudioPerformanceBrief.model_validate({**payload, "providerPrompt": "speak slowly"})
    assert {
        "fish",
        "provider",
        "model",
        "voice_id",
        "speed",
        "volume",
        "api_key",
        "endpoint",
    }.isdisjoint(AudioPerformanceBrief.model_fields)


def test_new_and_legacy_authorities_cannot_coexist() -> None:
    dialogue, cases = inputs()
    request = compile_projected_speech_request(
        work_id="work-1",
        dpd_snapshot=snapshot(cases[0]),
        spoken_content=dialogue,
        voice_profile=voice(),
        voice_identity_ref="voice:shared-questioner",
        timing_policy=TargetTimingPolicy(policy="NATURAL"),
    )
    payload = request.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError, match="legacy performance authority"):
        SpeechGenerationRequest.model_validate(
            {**payload, "performanceIntent": {"delivery": "legacy"}}
        )
    with pytest.raises(ValidationError, match="manual Fish prosody"):
        SpeechGenerationRequest.model_validate(
            {**payload, "materialRenderParameters": {"speed": 1.2}}
        )


def test_malformed_capability_result_fails_fast() -> None:
    mapping = map_audio_performance_to_fish(briefs()[0])
    payload = mapping.model_dump(mode="json", by_alias=True)
    payload["capabilities"] = payload["capabilities"][:-1]
    with pytest.raises(ValidationError, match="incomplete or duplicated"):
        FishAudioPerformanceMapping.model_validate(payload)
    with pytest.raises(ValidationError, match="mapped control"):
        AudioCapabilityDiagnostic(
            dimension="rhythm",
            status=CapabilityStatus.UNSUPPORTED,
            mapped_control="prosody.speed",
            reason="invalid fixture",
        )
