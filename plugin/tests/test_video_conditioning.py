from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from drama_plugin.audio.projection import compile_projected_speech_request
from drama_plugin.audio.video_conditioning import condition_audio_on_video
from drama_plugin.contracts import Media, SpeechGenerationRequest, TargetTimingPolicy
from drama_plugin.contracts.base import dump_contract
from drama_plugin.providers.speech.fish_audio import compile_fish_tts_payload
from drama_plugin.visual import build_realized_performance_snapshot
from test_audio_projection import inputs, snapshot, voice
from test_visual_performance import observed


def conditioning_inputs():
    spoken, cases = inputs()
    dpd = snapshot(cases[0])
    base = compile_projected_speech_request(
        work_id="work-1", dpd_snapshot=dpd, spoken_content=spoken,
        voice_profile=voice(), voice_identity_ref="voice-1",
        timing_policy=TargetTimingPolicy(policy="NATURAL"),
    )
    realized = build_realized_performance_snapshot(observed(
        mouthActivity="UNKNOWN", mouthActivityWindowsMs=[],
        preSpeechMotionWindowMs=None, postSpeechHoldMs=None,
    ))
    return dict(base_request=base, dpd_snapshot=dpd, realized_snapshot=realized,
                video_media=Media(id=realized.video_media_id, work_id="work-1",
                    shot_id=realized.shot_id, media_type="VIDEO", source_ref="video-source",
                    content_hash=realized.video_content_hash),
                shot_id=realized.shot_id, shot_scene_id=dpd.effective.scene_id,
                shot_spoken_content_ids=(base.spoken_content_id,), canonical_spoken_content=spoken,
                observed_speaker_key=base.speaker_key, bound_voice_id="voice-1",
                voice_content_hash="a"*64, accepted_realized_fingerprint=realized.fingerprint)


def test_conditioning_preserves_immutable_authorities_and_natural_timing():
    args = conditioning_inputs()
    before = deepcopy(args)
    final = condition_audio_on_video(**args)
    assert args == before
    assert final.exact_text == args["base_request"].exact_text
    assert final.voice_profile == args["base_request"].voice_profile
    assert final.audio_performance_brief.dpd_fingerprint == args["dpd_snapshot"].fingerprint
    assert final.target_timing_policy == TargetTimingPolicy(policy="NATURAL")
    assert final.audio_performance_brief != args["base_request"].audio_performance_brief
    assert condition_audio_on_video(**args) == final
    assert final.target_timing_policy.target_duration_ms is None
    directions = final.audio_performance_brief
    assert "7500" not in " ".join((directions.pace, directions.pause_strategy, directions.rhythm))


@pytest.mark.parametrize("change", ["video", "observation"])
def test_video_or_accepted_observation_change_invalidates_final_audio(change):
    args = conditioning_inputs()
    first = condition_audio_on_video(**args)
    updated = dump_contract(args["realized_snapshot"], exclude={"fingerprint"})
    if change == "video":
        updated["videoContentHash"] = "b"*64
        args["video_media"] = args["video_media"].model_copy(update={"content_hash": "b"*64})
    else:
        updated.update(visibleActivation="HIGH", headMotion="larger motion with frequent gaze shifts")
    args["realized_snapshot"] = build_realized_performance_snapshot(updated)
    args["accepted_realized_fingerprint"] = args["realized_snapshot"].fingerprint
    second = condition_audio_on_video(**args)
    assert first.video_conditioned_projection.fingerprint != second.video_conditioned_projection.fingerprint
    assert first.exact_text == second.exact_text
    assert first.voice_profile == second.voice_profile
    if change == "observation":
        assert first.audio_performance_brief.rhythm != second.audio_performance_brief.rhythm


@pytest.mark.parametrize("key,value,message", [
    ("dpd_snapshot", None, "required"),
    ("realized_snapshot", None, "required"),
    ("shot_id", "wrong-shot", "Shot"),
    ("shot_scene_id", "wrong-scene", "Scene"),
    ("observed_speaker_key", "wrong-speaker", "speaker"),
    ("bound_voice_id", "wrong-voice", "binding"),
    ("shot_spoken_content_ids", (), "binding"),
    ("accepted_realized_fingerprint", "0"*64, "stale"),
])
def test_invalid_inputs_fail_closed(key,value,message):
    args = conditioning_inputs(); args[key] = value
    with pytest.raises(ValueError, match=message): condition_audio_on_video(**args)


def test_hash_text_and_guessed_timing_rejected():
    args = conditioning_inputs()
    args["video_media"] = args["video_media"].model_copy(update={"content_hash":"c"*64})
    with pytest.raises(ValueError, match="hash mismatch"): condition_audio_on_video(**args)
    args = conditioning_inputs(); args["canonical_spoken_content"] = {**args["canonical_spoken_content"],"text":"invented"}
    with pytest.raises(ValueError, match="text mismatch"): condition_audio_on_video(**args)
    args = conditioning_inputs()
    args["base_request"] = args["base_request"].model_copy(update={"target_timing_policy":TargetTimingPolicy(policy="FIT_WINDOW",target_duration_ms=11042)})
    with pytest.raises(ValueError, match="guessed"): condition_audio_on_video(**args)


def test_final_contract_version_provider_fields_and_legacy_conflict():
    data = dump_contract(condition_audio_on_video(**conditioning_inputs()))
    for update in ({"schemaVersion":"v2"},{"fishVoiceId":"private"},{"speechStartMs":2700}):
        changed=deepcopy(data); changed["videoConditionedProjection"].update(update)
        with pytest.raises(ValidationError): SpeechGenerationRequest.model_validate(changed)
    with pytest.raises(ValidationError, match="legacy"):
        SpeechGenerationRequest.model_validate({**data,"performanceIntent":{"objective":"other"}})


def test_same_adapter_compiles_base_and_final_without_emotion_shortcut():
    args=conditioning_inputs(); final=condition_audio_on_video(**args)
    payloads=[compile_fish_tts_payload(exact_text=request.exact_text, reference_id="fixed",
        mode="directed", speed=0.92, volume=0, performance_brief=request.audio_performance_brief)
        for request in (args["base_request"],final)]
    assert payloads[0]["text"] != payloads[1]["text"]
    for payload in payloads:
        assert payload["text"].endswith(final.exact_text)
        assert "[curious]" not in payload["text"]
        assert payload["prosody"] == payloads[0]["prosody"]
    plain=compile_fish_tts_payload(exact_text=final.exact_text,reference_id="fixed",mode="directed",speed=.92,volume=0)
    assert plain["text"] == final.exact_text  # default production behavior unchanged


def test_base_render_parameters_are_not_silently_discarded():
    args = conditioning_inputs()
    args["base_request"] = args["base_request"].model_copy(update={"material_render_parameters": {"speed": 2}})
    with pytest.raises(ValueError, match="silent overwrite"):
        condition_audio_on_video(**args)


def test_final_fingerprint_ordering_and_freshness():
    from drama_plugin.audio.foundation import audio_input_fingerprint, is_audio_fresh
    from drama_plugin.contracts.audio import ProviderVoiceMapping
    args = conditioning_inputs()
    final = condition_audio_on_video(**args)
    mapping = ProviderVoiceMapping(provider="fish", model="s2-pro", voice_id="fixed", status="APPROVED")
    final = final.model_copy(update={"provider_mapping": mapping,
        "voice_profile": final.voice_profile.model_copy(update={"provider_mappings": [mapping]})})
    content = {"reviewStatus": "PASS", "audioInputFingerprint": audio_input_fingerprint(final)}
    assert is_audio_fresh(content, final)
    raw = dump_contract(final)
    assert audio_input_fingerprint(SpeechGenerationRequest.model_validate(dict(reversed(list(raw.items()))))) == content["audioInputFingerprint"]
    realized = dump_contract(args["realized_snapshot"], exclude={"fingerprint"})
    realized["headMotion"] = "review corrected observed head movement"
    args["realized_snapshot"] = build_realized_performance_snapshot(realized)
    args["accepted_realized_fingerprint"] = args["realized_snapshot"].fingerprint
    changed = condition_audio_on_video(**args).model_copy(update={"provider_mapping": mapping})
    assert not is_audio_fresh(content, changed)


@pytest.mark.asyncio
async def test_final_role_dubbing_lineage_and_stale_inputs_before_cache(tmp_path: Path):
    from drama_plugin.contracts import RoleDubbingRequest
    from drama_plugin.contracts.voice import VoiceContent, VoiceSourceType, VoiceProviderMapping
    from drama_plugin.exceptions import RoleDubbingError
    from drama_plugin.providers.mock import MockDramaData, MockMemoryProvider
    from drama_plugin.providers.speech.role_dubbing import FishRoleDubbingProvider
    from test_role_dubbing import FakeVoiceProvider, FakeMediaProvider, FakeFish, probe, wav_bytes

    args = conditioning_inputs()
    voices = FakeVoiceProvider(tmp_path)
    master = tmp_path / "master.wav"
    master.write_bytes(wav_bytes())
    voice = await voices.import_voice("Frozen", VoiceSourceType.DESIGNED, master.as_uri(), 400,
        VoiceContent(creative_casting_profile={}, source_provenance={}))
    mapping = VoiceProviderMapping(provider="fish", model="s2-pro", provider_voice_id="fixed",
        material_fingerprint="b"*64, status="ACTIVE", created_at=datetime.now(UTC))
    voices.values[voice.id] = voice.model_copy(update={"content": voice.content.model_copy(update={"provider_mappings": [mapping]})})
    args["voice_content_hash"] = voice.content_hash
    final = condition_audio_on_video(**args)
    data = MockDramaData()
    data.work = data.work.model_copy(update={"content": {"voiceProfiles": [
        {"speakerKey": final.speaker_key, "voiceId": voice.id}]}})
    data.scene = data.scene.model_copy(update={"id": final.scene_id, "content": {"spokenContent": [args["canonical_spoken_content"]]}})
    data.shot = data.shot.model_copy(update={"id": args["shot_id"], "scene_id": final.scene_id,
        "content": {"spokenContentBindings": [{"spokenContentId": final.spoken_content_id}]}})

    class MediaStore(FakeMediaProvider):
        async def get_media(self, media_id):
            return args["video_media"]

        async def import_media(self, **kwargs):
            assert kwargs["shot_id"] == args["shot_id"]
            return await super().import_media(**kwargs)

    media = MediaStore()
    fish = FakeFish(final.exact_text)
    provider = FishRoleDubbingProvider(memory=MockMemoryProvider(data), voices=voices, media=media,
        fish=fish, output_directory=tmp_path / "attempts", probe=probe)
    result = await provider.generate_role_dubbing(RoleDubbingRequest(speech_request=final))
    assert result.voice_design_calls == result.create_model_calls == 0
    assert fish.tts_calls == 1
    content = media.values[0].content
    assert content["performanceAuthority"] == "VIDEO_CONDITIONED_FINAL_AUDIO"
    assert content["finalAudioProjectionFingerprint"] == final.video_conditioned_projection.fingerprint
    assert content["realizedPerformanceFingerprint"] == args["realized_snapshot"].fingerprint
    assert content["sourceVideoContentHash"] == args["video_media"].content_hash
    assert content["technicalReviewStatus"] == "PASS"
    await provider.generate_role_dubbing(RoleDubbingRequest(speech_request=final))
    assert fish.tts_calls == 1  # safe exact-request reuse
    args["video_media"] = args["video_media"].model_copy(update={"content_hash": "c"*64})
    with pytest.raises(RoleDubbingError, match="lineage changed"):
        await provider.generate_role_dubbing(RoleDubbingRequest(speech_request=final))
    assert fish.tts_calls == 1  # stale Video rejected BEFORE cached Audio can be reused
    voices.values[voice.id] = voices.values[voice.id].model_copy(update={"content_hash": "d"*64})
    with pytest.raises(RoleDubbingError, match="Frozen Voice material changed"):
        await provider.generate_role_dubbing(RoleDubbingRequest(speech_request=final))
    assert fish.design_calls == fish.model_calls == 0 and fish.tts_calls == 1
