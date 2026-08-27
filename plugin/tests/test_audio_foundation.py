from __future__ import annotations

from copy import deepcopy
import wave
from pathlib import Path

import pytest
from pydantic import ValidationError

from drama_plugin import DramaPlugin
from drama_plugin.audio import (
    audio_input_fingerprint,
    capability_report,
    compile_speech_request,
    final_av_fingerprint,
    is_audio_fresh,
    mux_video_and_audio,
    probe_wav_duration_ms,
    source_ref_for_review,
    text_hash,
    validate_media_mime,
    compile_fish_creative_casting_brief,
    project_creative_voice_casting_profile,
)
from drama_plugin.contracts import (
    AudioReviewStatus,
    AvAssemblyManifest,
    AvTimelineItem,
    CreativeVoiceProfile,
    CreativeCastingDimension,
    FinalAvFingerprintInput,
    Media,
    MediaType,
    PronunciationGuidance,
    ProviderMappingStatus,
    ProviderVoiceMapping,
    SpeechGenerationRequest,
    TargetTimingPolicy,
    VoiceProfile,
)


ROOT = Path(__file__).resolve().parents[1]


def mapping(**updates: object) -> ProviderVoiceMapping:
    values: dict[str, object] = {
        "provider": "fake-speech",
        "model": "fake-v1",
        "voice_id": "voice-actor",
        "status": ProviderMappingStatus.APPROVED,
        "material_parameters": {"stability": 0.7},
        "non_material_metadata": {"operatorNote": "baseline"},
    }
    values.update(updates)
    return ProviderVoiceMapping.model_validate(values)


def voice(speaker_key: str = "speaker:actor", **creative_updates: object) -> VoiceProfile:
    creative: dict[str, object] = {
        "age_presentation": "middle-aged",
        "timbre": "dark",
        "temperament": "restrained",
        "baseline_pace": "measured",
        "power": "authoritative",
        "restraint": "high",
        "language": "zh-CN",
        "register": "formal",
        "consistency_notes": ["avoid theatrical exaggeration"],
    }
    creative.update(creative_updates)
    selected = mapping(voice_id="voice-narrator" if speaker_key.startswith("narrator:") else "voice-actor")
    return VoiceProfile(
        profile_id=f"profile:{speaker_key}",
        speaker_key=speaker_key,
        creative_profile=CreativeVoiceProfile.model_validate(creative),
        provider_mappings=[selected],
        display_name="Display only",
        non_material_metadata={"updatedBy": "fixture"},
    )


def request() -> SpeechGenerationRequest:
    profile = voice()
    selected = profile.provider_mappings[0]
    spoken = {
        "spokenContentId": "spoken-1",
        "speakerKey": "speaker:actor",
        "text": "守住此关。",
        "performanceIntent": {"delivery": "restrained", "pauseAfterMs": 200},
        "estimatedDurationMs": 1800,
    }
    return compile_speech_request(
        work_id="work-1",
        scene_id="scene-1",
        spoken_content=spoken,
        voice_profile=profile,
        provider_mapping=selected,
        pronunciation_guidance=[
            PronunciationGuidance(term="此关", language="zh-CN", reviewed_reading="reviewed-reading")
        ],
        material_render_parameters={"speed": 1.0, "format": "wav"},
        target_timing_policy=TargetTimingPolicy(policy="FIT_WINDOW", target_duration_ms=2000, allow_rate_adjustment=True),
    )


def rebuild(value: SpeechGenerationRequest, **updates: object) -> SpeechGenerationRequest:
    payload = value.model_dump(mode="python")
    payload.update(updates)
    return SpeechGenerationRequest.model_validate(payload)


def test_actor_and_narrator_voice_profiles_keep_creative_identity_separate_from_mapping() -> None:
    actor = voice()
    narrator = voice("narrator:primary", temperament="observant")
    assert actor.speaker_key == "speaker:actor"
    assert narrator.speaker_key == "narrator:primary"
    assert actor.creative_profile.timbre == "dark"
    assert actor.provider_mappings[0].voice_id == "voice-actor"
    assert narrator.provider_mappings[0].voice_id == "voice-narrator"
    assert "provider" not in CreativeVoiceProfile.model_fields


def test_creative_casting_and_fish_prompt_are_identity_and_scene_invariant() -> None:
    base = voice()
    decisions = {
        "vocalAge": CreativeCastingDimension(
            value="LATE_MIDDLE_ADULT", basis_refs=["creative:age-composite"]
        ),
        "vocalWeight": CreativeCastingDimension(
            value="MEDIUM_HEAVY", basis_refs=["creative:responsibility"]
        ),
        "resonance": CreativeCastingDimension(
            value="DEEP", basis_refs=["creative:command-load"]
        ),
        "brightness": CreativeCastingDimension(
            value="SLIGHTLY_DARK", basis_refs=["creative:casting"]
        ),
        "texture": CreativeCastingDimension(
            value="DRY_AGE_TEXTURED", basis_refs=["creative:casting"]
        ),
    }
    first = project_creative_voice_casting_profile(
        base, artistic_decisions=decisions
    )
    renamed = base.model_copy(
        update={
            "profile_id": "profile:speaker:synthetic-renamed",
            "speaker_key": "speaker:synthetic-renamed",
            "display_name": "Different",
        }
    )
    second = project_creative_voice_casting_profile(
        renamed, artistic_decisions=decisions
    )
    assert first.dimensions == second.dimensions
    assert first.source_profile_id != second.source_profile_id
    first_prompt = compile_fish_creative_casting_brief(first)
    second_prompt = compile_fish_creative_casting_brief(second)
    assert first_prompt == second_prompt
    serialized = str(first_prompt)
    assert "synthetic-renamed" not in serialized
    assert "SceneState" not in serialized
    assert "PerformanceIntent" not in serialized
    assert "pitch shortcut" in serialized


def test_exact_dialogue_and_pronunciation_compile_without_dialogue_mutation() -> None:
    profile = voice()
    spoken = {
        "spokenContentId": "spoken-1",
        "speakerKey": "speaker:actor",
        "text": "原文不可改。",
        "performanceIntent": {"delivery": "quiet"},
        "estimatedDurationMs": 1500,
    }
    before = deepcopy(spoken)
    compiled = compile_speech_request(
        work_id="work-1",
        scene_id="scene-1",
        spoken_content=spoken,
        voice_profile=profile,
        provider_mapping=profile.provider_mappings[0],
        pronunciation_guidance=[PronunciationGuidance(term="原文", language="zh-CN", reviewed_reading="reviewed")],
        material_render_parameters={},
        target_timing_policy=TargetTimingPolicy(policy="NATURAL"),
    )
    assert compiled.exact_text == spoken["text"]
    assert compiled.pronunciation_guidance[0].reviewed_reading not in compiled.exact_text
    assert spoken == before


def test_text_hash_and_audio_input_fingerprint_are_deterministic() -> None:
    current = request()
    assert text_hash(current.exact_text) == text_hash(current.exact_text)
    assert audio_input_fingerprint(current) == audio_input_fingerprint(request())
    assert len(audio_input_fingerprint(current)) == 64


@pytest.mark.parametrize("change", ["text", "speaker", "performance", "voice", "mapping", "pronunciation", "render", "timing"])
def test_material_audio_changes_are_stale(change: str) -> None:
    baseline = request()
    changed = baseline
    if change == "text":
        changed = rebuild(baseline, exact_text="守住另一关。")
    elif change == "speaker":
        new_profile = voice("speaker:other")
        changed = rebuild(baseline, speaker_key="speaker:other", voice_profile=new_profile, provider_mapping=new_profile.provider_mappings[0])
    elif change == "performance":
        changed = rebuild(baseline, performance_intent={"delivery": "forceful"})
    elif change == "voice":
        changed = rebuild(baseline, voice_profile=voice(timbre="bright"))
    elif change == "mapping":
        changed_mapping = mapping(voice_id="voice-actor-v2")
        changed_profile = baseline.voice_profile.model_copy(update={"provider_mappings": [changed_mapping]})
        changed = rebuild(baseline, voice_profile=changed_profile, provider_mapping=changed_mapping)
    elif change == "pronunciation":
        changed = rebuild(baseline, pronunciation_guidance=[PronunciationGuidance(term="此关", language="zh-CN", reviewed_reading="different-reviewed-reading")])
    elif change == "render":
        changed = rebuild(baseline, material_render_parameters={"speed": 0.95, "format": "wav"})
    elif change == "timing":
        changed = rebuild(baseline, target_timing_policy=TargetTimingPolicy(policy="FIT_WINDOW", target_duration_ms=2300, allow_rate_adjustment=True))
    fingerprint = audio_input_fingerprint(baseline)
    stored = {"reviewStatus": "PASS", "audioInputFingerprint": fingerprint}
    assert audio_input_fingerprint(changed) != fingerprint
    assert not is_audio_fresh(stored, changed)


def test_non_material_metadata_does_not_unnecessarily_stale() -> None:
    baseline = request()
    changed_mapping = baseline.provider_mapping.model_copy(update={"non_material_metadata": {"note": "changed"}})
    changed_profile = baseline.voice_profile.model_copy(update={
        "display_name": "New display label",
        "non_material_metadata": {"timestamp": "later"},
        "provider_mappings": [changed_mapping],
    })
    changed_guidance = [baseline.pronunciation_guidance[0].model_copy(update={"notes": "editorial note"})]
    changed = rebuild(
        baseline,
        voice_profile=changed_profile,
        provider_mapping=changed_mapping,
        pronunciation_guidance=changed_guidance,
        non_material_metadata={"runLabel": "new"},
    )
    assert audio_input_fingerprint(changed) == audio_input_fingerprint(baseline)


def test_pass_and_failed_attempt_source_refs_have_distinct_retry_semantics() -> None:
    fingerprint = audio_input_fingerprint(request())
    canonical = source_ref_for_review(fingerprint, AudioReviewStatus.PASS)
    failed = source_ref_for_review(fingerprint, AudioReviewStatus.FAILED, attempt_id="attempt-1")
    retry = source_ref_for_review(fingerprint, AudioReviewStatus.PENDING, attempt_id="attempt-2")
    assert canonical == f"audio-input:{fingerprint}"
    assert failed == f"audio-attempt:{fingerprint}:attempt-1"
    assert retry != failed and retry != canonical


def test_audio_media_mime_duration_and_final_av_contracts() -> None:
    validate_media_mime(MediaType.AUDIO, "SPEECH_CLIP", "audio/wav")
    validate_media_mime(MediaType.VIDEO, "FINAL_AV", "video/mp4")
    with pytest.raises(ValueError):
        validate_media_mime(MediaType.AUDIO, "SPEECH_CLIP", "application/octet-stream")
    with pytest.raises(ValueError):
        validate_media_mime(MediaType.VIDEO, "FINAL_AV", "audio/wav")
    missing = Media(id="media-a", work_id="work-1", media_type=MediaType.AUDIO, purpose="SPEECH_CLIP", source_ref="audio-attempt:x:1", content={})
    assert missing.duration_ms is None
    with pytest.raises(ValidationError):
        Media(id="media-b", work_id="work-1", media_type=MediaType.AUDIO, purpose="SPEECH_CLIP", source_ref="audio-attempt:x:2", duration_ms=0, content={})


def test_host_side_wav_probe_is_authoritative_for_fixture(tmp_path: Path) -> None:
    fixture = tmp_path / "one-second.wav"
    with wave.open(str(fixture), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\x00\x00" * 16000)
    assert probe_wav_duration_ms(fixture) == 1000


def test_cross_shot_clip_reuse_final_av_fingerprint_and_source_path_immutability(tmp_path: Path) -> None:
    manifest = AvAssemblyManifest(
        source_video_media_id="media-silent",
        speech_clip_media_ids=["media-clip"],
        timeline=[
            AvTimelineItem(spoken_content_id="spoken-1", audio_media_id="media-clip", start_ms=0, source_in_ms=0, source_out_ms=600),
            AvTimelineItem(spoken_content_id="spoken-1", audio_media_id="media-clip", start_ms=800, source_in_ms=600, source_out_ms=1000),
        ],
    )
    value = FinalAvFingerprintInput(
        manifest=manifest,
        source_video_content_hash="source-hash",
        audio_content_hashes={"media-clip": "audio-hash"},
        mux_implementation="fake-mux",
        mux_version="1",
        mux_settings={"video": "copy", "audio": "aac"},
    )
    assert manifest.timeline[0].audio_media_id == manifest.timeline[1].audio_media_id
    assert final_av_fingerprint(value) == final_av_fingerprint(value.model_copy(deep=True))
    source = tmp_path / "source.mp4"
    audio = tmp_path / "audio.wav"
    source.write_bytes(b"immutable-source")
    audio.write_bytes(b"audio")
    with pytest.raises(ValueError, match="new path"):
        mux_video_and_audio(source, audio, source)
    assert source.read_bytes() == b"immutable-source"


def test_audio_foundation_does_not_add_audio_crud_tool() -> None:
    codes = {tool.code for tool in DramaPlugin.load(ROOT).tools.list()}
    assert not any(code.startswith("audio.") for code in codes)
    assert "production.generate_speech" not in codes
    assert "production.generate_audio" not in codes
    assert "production.generate_role_dubbing" in codes


def test_host_capability_is_explicit() -> None:
    report = capability_report()
    assert report["status"] in {"READY", "AV_ASSEMBLY_CAPABILITY_MISSING"}
    if report["status"] == "AV_ASSEMBLY_CAPABILITY_MISSING":
        assert report["ffmpeg"] is None or report["ffprobe"] is None
