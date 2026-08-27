from __future__ import annotations

import hashlib
import wave
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from drama_plugin.audio.host_media import MediaProbe, probe_wav_duration_ms
from drama_plugin.contracts.audio import (
    CreativeCastingDimension,
    CreativeVoiceCastingProfile,
    CreativeVoiceProfile,
    RoleDubbingRequest,
    SpeechGenerationRequest,
    TargetTimingPolicy,
    VoiceProfile,
)
from drama_plugin.contracts.media import Media, MediaType
from drama_plugin.contracts.voice import (
    Voice,
    VoiceContent,
    VoiceResolveResult,
    VoiceSourceType,
    VoiceStatus,
)
from drama_plugin.exceptions import ProviderError, RoleDubbingError
from drama_plugin.providers.mock import MockDramaData, MockMemoryProvider
from drama_plugin.providers.speech.fish_audio import (
    FishAsrResult,
    FishModelResult,
    FishVoiceDesignCandidate,
    FishVoiceDesignResult,
)
from drama_plugin.providers.speech.role_dubbing import FishRoleDubbingProvider


def wav_bytes(duration_ms: int = 400) -> bytes:
    import io
    import math
    import struct

    output = io.BytesIO()
    rate = 24000
    with wave.open(output, "wb") as target:
        target.setnchannels(1); target.setsampwidth(2); target.setframerate(rate)
        target.writeframes(b"".join(struct.pack("<h", round(5000 * math.sin(2 * math.pi * 220 * i / rate)))
                                    for i in range(round(rate * duration_ms / 1000))))
    return output.getvalue()


def probe(path: Path | str) -> MediaProbe:
    return MediaProbe(duration_ms=probe_wav_duration_ms(path),
                      streams=({"codec_type": "audio", "codec_name": "pcm_s16le"},),
                      implementation="test-wave", version="1")


class FakeVoiceProvider:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.values: dict[str, Voice] = {}

    async def import_voice(self, name: str, source_type: VoiceSourceType, source_uri: str,
                           duration_ms: int, content: VoiceContent) -> Voice:
        voice_id = f"voice-{len(self.values) + 1}"
        source = Path(source_uri.removeprefix("file://"))
        master = self.root / f"{voice_id}-master.wav"
        master.write_bytes(source.read_bytes())
        digest = hashlib.sha256(master.read_bytes()).hexdigest()
        voice = Voice(id=voice_id, name=name, source_type=source_type, status=VoiceStatus.ACTIVE,
                      storage_type="TEST", bucket_name="test", object_key=str(master),
                      mime_type="audio/wav", file_size=master.stat().st_size,
                      duration_ms=duration_ms, content_hash=digest, content=content, version=1)
        self.values[voice_id] = voice
        return voice

    async def get_voice(self, voice_id: str) -> Voice:
        return self.values[voice_id]

    async def search_voices(self, query: str | None = None, status: VoiceStatus | None = None) -> list[Voice]:
        return list(self.values.values())

    async def update_voice(self, voice_id: str, content: VoiceContent, expected_version: int,
                           name: str | None = None, status: VoiceStatus | None = None) -> Voice:
        current = self.values[voice_id]
        assert current.version == expected_version
        changed = current.model_copy(update={"content": content, "version": current.version + 1,
                                             "name": name or current.name, "status": status or current.status})
        self.values[voice_id] = changed
        return changed

    async def resolve_voice(self, voice_id: str) -> VoiceResolveResult:
        voice = self.values[voice_id]
        return VoiceResolveResult(voice_id=voice.id, url=Path(voice.object_key).as_uri(),
                                  expires_at=datetime.now(UTC) + timedelta(minutes=5),
                                  mime_type=voice.mime_type, size_bytes=voice.file_size,
                                  content_hash=voice.content_hash)


class RecoverableVoiceProvider(FakeVoiceProvider):
    fail_import = True

    async def import_voice(self, name: str, source_type: VoiceSourceType, source_uri: str,
                           duration_ms: int, content: VoiceContent) -> Voice:
        if self.fail_import:
            raise ProviderError("diagnosed downstream storage failure")
        return await super().import_voice(name, source_type, source_uri, duration_ms, content)


class FakeMediaProvider:
    def __init__(self) -> None:
        self.values: list[Media] = []

    async def list_media(self, media_type: MediaType | None = None, work_id: str | None = None,
                         purpose: str | None = None, source_ref: str | None = None) -> list[Media]:
        return [item for item in self.values if (media_type is None or item.media_type is media_type)
                and (work_id is None or item.work_id == work_id)
                and (purpose is None or item.purpose == purpose)
                and (source_ref is None or item.source_ref == source_ref)]

    async def import_media(self, work_id: str, media_type: MediaType, source_uri: str,
                           content: dict[str, Any], asset_id: str | None = None,
                           shot_id: str | None = None, purpose: str | None = None,
                           source_ref: str | None = None, duration_ms: int | None = None) -> Media:
        path = Path(source_uri.removeprefix("file://"))
        media = Media(id=f"media-{len(self.values) + 1}", work_id=work_id,
                      media_type=media_type, purpose=purpose, source_ref=source_ref or "test",
                      duration_ms=duration_ms, mime_type="audio/wav", file_size=path.stat().st_size,
                      content_hash=hashlib.sha256(path.read_bytes()).hexdigest(), content=content)
        self.values.append(media)
        return media


@dataclass
class FakeFish:
    transcript: str
    design_calls: int = 0
    model_calls: int = 0
    tts_calls: int = 0
    asr_calls: int = 0

    async def design_voice(self, payload: dict[str, Any]) -> FishVoiceDesignResult:
        self.design_calls += 1
        audio = wav_bytes()
        return FishVoiceDesignResult(tuple(FishVoiceDesignCandidate(
            candidate_id=f"candidate-{index}", index=index, audio=audio,
            sample_rate=24000, duration_ms=400, text=str(payload["reference_text"]),
            instruction=str(payload["instruction"]), language="zh") for index in range(3)), "design")

    async def transcribe(self, audio_path: Path) -> FishAsrResult:
        self.asr_calls += 1
        return FishAsrResult(text=self.transcript, duration_seconds=0.4, language="zh",
                             segments=(), provider_request_id="asr")

    async def create_model(self, *, reference_audio: Path, title: str,
                           reference_text: str | None = None) -> FishModelResult:
        self.model_calls += 1
        return FishModelResult(reference_id=f"reference-{self.model_calls}", state="created",
                               provider_request_id="model")

    async def synthesize(self, payload: dict[str, Any]) -> tuple[bytes, str | None]:
        self.tts_calls += 1
        return wav_bytes(600), "tts"


def request(text: str, spoken_id: str = "spoken-1") -> RoleDubbingRequest:
    profile = VoiceProfile(profile_id="profile-1", speaker_key="speaker:commander",
                           creative_profile=CreativeVoiceProfile(
                               vocal_age="MATURE_ADULT", vocal_weight="MEDIUM",
                               resonance_depth="BALANCED", timbre_brightness="NEUTRAL",
                               texture="CLEAN_SUBTLE_GRAIN", baseline_pace="MODERATE"))
    casting = CreativeVoiceCastingProfile(source_profile_id=profile.profile_id, dimensions={
        "vocalAge": CreativeCastingDimension(value="MATURE_ADULT"),
        "vocalWeight": CreativeCastingDimension(value="MEDIUM"),
        "resonance": CreativeCastingDimension(value="BALANCED"),
        "brightness": CreativeCastingDimension(value="NEUTRAL"),
        "texture": CreativeCastingDimension(value="CLEAN_SUBTLE_GRAIN"),
        "baselinePace": CreativeCastingDimension(value="MODERATE"),
        "language": CreativeCastingDimension(value="zh-CN"),
    })
    return RoleDubbingRequest(speech_request=SpeechGenerationRequest(
        work_id="work-1", scene_id="scene-1", spoken_content_id=spoken_id,
        exact_text=text, speaker_key="speaker:commander", voice_profile=profile,
        creative_casting_profile=casting, target_timing_policy=TargetTimingPolicy(policy="NATURAL")))


@pytest.mark.asyncio
async def test_new_voice_then_existing_mapping_reuse(tmp_path: Path) -> None:
    data = MockDramaData()
    data.work = data.work.model_copy(update={"content": {"theme": "preserve"}})
    memory = MockMemoryProvider(data)
    voices = FakeVoiceProvider(tmp_path)
    media = FakeMediaProvider()
    fish = FakeFish("请给我三十骑")
    provider = FishRoleDubbingProvider(memory=memory, voices=voices, media=media,
                                       fish=fish, output_directory=tmp_path / "attempts", probe=probe)  # type: ignore[arg-type]

    first = await provider.generate_role_dubbing(request("请给我三十骑"))
    assert first.lifecycle_branch == "NEW_VOICE"
    assert first.voice_design_calls == first.create_model_calls == 1
    assert fish.design_calls == fish.model_calls == 1
    assert data.work.content["theme"] == "preserve"
    assert data.work.content["voiceProfiles"][0]["voiceId"] == first.voice_id
    assert len(voices.values[first.voice_id].content.provider_mappings) == 1
    assert media.values[0].content["reviewStatus"] == "PENDING"
    assert media.values[0].content["technicalReviewStatus"] == "PASS"

    fish.transcript = "守住潼关"
    second = await provider.generate_role_dubbing(request("守住潼关", "spoken-2"))
    assert second.lifecycle_branch == "EXISTING_MAPPING"
    assert second.voice_design_calls == second.create_model_calls == 0
    assert fish.design_calls == fish.model_calls == 1
    assert fish.tts_calls == 2


@pytest.mark.asyncio
async def test_existing_voice_without_mapping_materializes_from_master(tmp_path: Path) -> None:
    data = MockDramaData()
    memory = MockMemoryProvider(data)
    voices = FakeVoiceProvider(tmp_path)
    master = tmp_path / "seed.wav"; master.write_bytes(wav_bytes())
    voice = await voices.import_voice("Existing", VoiceSourceType.DESIGNED, master.as_uri(), 400,
                                      VoiceContent(creative_casting_profile={}, source_provenance={}))
    data.work = data.work.model_copy(update={"content": {"voiceProfiles": [
        {"speakerKey": "speaker:commander", "voiceId": voice.id}]}})
    fish = FakeFish("守住潼关")
    provider = FishRoleDubbingProvider(memory=memory, voices=voices, media=FakeMediaProvider(),
                                       fish=fish, output_directory=tmp_path / "attempts", probe=probe)  # type: ignore[arg-type]
    result = await provider.generate_role_dubbing(request("守住潼关"))
    assert result.lifecycle_branch == "MATERIALIZED_MAPPING"
    assert result.voice_design_calls == 0 and result.create_model_calls == 1
    assert fish.design_calls == 0 and fish.model_calls == 1


@pytest.mark.asyncio
async def test_all_candidates_failing_asr_never_create_voice(tmp_path: Path) -> None:
    data = MockDramaData()
    voices = FakeVoiceProvider(tmp_path)
    fish = FakeFish("完全不同")
    provider = FishRoleDubbingProvider(memory=MockMemoryProvider(data), voices=voices,
                                       media=FakeMediaProvider(), fish=fish,
                                       output_directory=tmp_path / "attempts", probe=probe)  # type: ignore[arg-type]
    with pytest.raises(RoleDubbingError) as raised:
        await provider.generate_role_dubbing(request("请给我三十骑"))
    assert raised.value.error_code == "VOICE_CASTING_FAILED"
    assert voices.values == {}
    assert fish.model_calls == fish.tts_calls == 0


@pytest.mark.asyncio
async def test_known_design_result_is_hash_verified_and_reused_after_import_failure(
    tmp_path: Path,
) -> None:
    data = MockDramaData()
    voices = RecoverableVoiceProvider(tmp_path)
    fish = FakeFish("请给我三十骑")
    provider = FishRoleDubbingProvider(
        memory=MockMemoryProvider(data), voices=voices, media=FakeMediaProvider(),
        fish=fish, output_directory=tmp_path / "attempts", probe=probe,  # type: ignore[arg-type]
    )

    with pytest.raises(ProviderError):
        await provider.generate_role_dubbing(request("请给我三十骑"))
    assert fish.design_calls == 1
    assert fish.model_calls == fish.tts_calls == 0

    voices.fail_import = False
    recovered = await provider.generate_role_dubbing(request("请给我三十骑"))
    assert recovered.lifecycle_branch == "NEW_VOICE"
    assert recovered.voice_design_calls == 0
    assert recovered.create_model_calls == 1
    assert fish.design_calls == 1
    assert fish.model_calls == fish.tts_calls == 1
