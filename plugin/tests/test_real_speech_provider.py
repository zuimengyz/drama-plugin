from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from drama_plugin.audio import (
    audio_input_fingerprint,
    canonical_audio_source_ref,
    canonical_final_av_source_ref,
    compile_speech_request,
    final_av_attempt_source_ref,
)
from drama_plugin.audio.host_media import MediaProbe
from drama_plugin.config import SpeechServiceConfig, load_config
from drama_plugin.contracts import (
    CreativeVoiceProfile,
    Media,
    MediaType,
    ProviderVoiceMapping,
    SpeechGenerationRequest,
    SpeechGenerationResult,
    TargetTimingPolicy,
    VoiceProfile,
)
from drama_plugin.exceptions import (
    ConfigurationError,
    ProviderResultUnknown,
    SpeechProviderError,
)
from drama_plugin.providers.mock import MockDramaData, MockMediaProvider, MockProductionProvider
from drama_plugin.providers.speech import (
    BailianQwenSpeechProvider,
    OpenAiSpeechProvider,
    SpeechBackedProductionProvider,
    compile_bailian_qwen_speech_payload,
    compile_openai_speech_payload,
    resolve_speech_provider,
)


def speech_request(voice_id: str = "marin") -> SpeechGenerationRequest:
    mapping = ProviderVoiceMapping(
        provider="openai",
        model="gpt-4o-mini-tts",
        voice_id=voice_id,
        material_parameters={"response_format": "wav"},
    )
    profile = VoiceProfile(
        profile_id=f"profile:{voice_id}",
        speaker_key=f"speaker:{voice_id}",
        creative_profile=CreativeVoiceProfile(
            age_presentation="adult",
            timbre="neutral",
            temperament="restrained",
            baseline_pace="measured",
            power="moderate",
            restraint="high",
            language="zh-CN",
        ),
        provider_mappings=[mapping],
    )
    return compile_speech_request(
        work_id="work-real-tts",
        scene_id="scene-validation",
        spoken_content={
            "spokenContentId": f"spoken:{voice_id}",
            "speakerKey": profile.speaker_key,
            "text": "军报已经送到，请将军决断。",
            "performanceIntent": {"delivery": "restrained"},
        },
        voice_profile=profile,
        provider_mapping=mapping,
        pronunciation_guidance=[],
        material_render_parameters={"speed": 1.0},
        target_timing_policy=TargetTimingPolicy(policy="NATURAL"),
    )


def speech_config(**updates: Any) -> SpeechServiceConfig:
    values: dict[str, Any] = {
        "base_url": "https://unit.invalid/v1",
        "api_key": "unit-secret-must-not-leak",
        "max_transient_retries": 2,
    }
    values.update(updates)
    return SpeechServiceConfig.model_validate(values)


def qwen_request(
    voice_id: str = "Cherry",
    model: str = "qwen3-tts-instruct-flash",
) -> SpeechGenerationRequest:
    mapping = ProviderVoiceMapping(
        provider="bailian_qwen",
        model=model,
        voice_id=voice_id,
        material_parameters={"language_type": "Chinese"},
    )
    profile = VoiceProfile(
        profile_id=f"profile:qwen:{voice_id}",
        speaker_key=f"speaker:qwen:{voice_id}",
        creative_profile=CreativeVoiceProfile(
            age_presentation="adult",
            timbre="clear and grounded",
            temperament="restrained",
            baseline_pace="measured",
            power="moderate",
            restraint="high",
            language="zh-CN",
        ),
        provider_mappings=[mapping],
    )
    return compile_speech_request(
        work_id="work-qwen-real-tts",
        scene_id="scene-qwen-validation",
        spoken_content={
            "spokenContentId": f"spoken:qwen:{voice_id}",
            "speakerKey": profile.speaker_key,
            "text": "军报已经送到，请将军决断。",
            "performanceIntent": {"delivery": "neutral", "pace": "measured"},
        },
        voice_profile=profile,
        provider_mapping=mapping,
        pronunciation_guidance=[],
        material_render_parameters={"validationControl": "steady"},
        target_timing_policy=TargetTimingPolicy(policy="NATURAL"),
    )


def qwen_config(**updates: Any) -> SpeechServiceConfig:
    values: dict[str, Any] = {
        "bailian_base_url": "https://unit.invalid/api/v1",
        "dashscope_api_key": "dashscope-unit-secret-must-not-leak",
        "max_transient_retries": 2,
    }
    values.update(updates)
    return SpeechServiceConfig.model_validate(values)


def test_real_provider_config_parsing_and_secret_redaction() -> None:
    config = load_config(
        environment={
            "DRAMA_PLUGIN_PROVIDER_SPEECH_MODE": "openai",
            "DRAMA_PLUGIN_SERVICE_SPEECH_BASE_URL": "https://unit.invalid/v1",
            "OPENAI_API_KEY": "unit-secret-must-not-leak",
            "DRAMA_PLUGIN_SERVICE_SPEECH_OUTPUT_DIRECTORY": "/tmp/unit-speech",
            "DRAMA_PLUGIN_SERVICE_SPEECH_MAX_TRANSIENT_RETRIES": "1",
        }
    )
    assert config.providers.speech.mode == "openai"
    assert config.services.speech.max_transient_retries == 1
    assert config.services.speech.api_key is not None
    assert config.services.speech.api_key.get_secret_value() == "unit-secret-must-not-leak"
    assert "unit-secret-must-not-leak" not in repr(config)


def test_bailian_config_parsing_and_secret_redaction() -> None:
    config = load_config(
        environment={
            "DRAMA_PLUGIN_PROVIDER_SPEECH_MODE": "bailian_qwen",
            "DRAMA_PLUGIN_SERVICE_SPEECH_BAILIAN_BASE_URL": (
                "https://unit.invalid/api/v1"
            ),
            "DASHSCOPE_API_KEY": "dashscope-unit-secret-must-not-leak",
            "DRAMA_PLUGIN_SERVICE_SPEECH_OUTPUT_DIRECTORY": "/tmp/unit-speech",
        }
    )
    assert config.providers.speech.mode == "bailian_qwen"
    assert config.services.speech.dashscope_api_key is not None
    assert config.services.speech.dashscope_api_key.get_secret_value() == (
        "dashscope-unit-secret-must-not-leak"
    )
    assert "dashscope-unit-secret-must-not-leak" not in repr(config)


def test_unknown_speech_provider_mode_fails_closed() -> None:
    with pytest.raises(ConfigurationError, match="Invalid Drama Plugin configuration"):
        load_config(environment={"DRAMA_PLUGIN_PROVIDER_SPEECH_MODE": "unknown"})


def test_missing_real_provider_credential_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(SpeechProviderError, match="credential is missing"):
        OpenAiSpeechProvider(SpeechServiceConfig(), tmp_path)
    with pytest.raises(SpeechProviderError, match="credential is missing"):
        BailianQwenSpeechProvider(SpeechServiceConfig(), tmp_path)


@pytest.mark.asyncio
async def test_provider_resolver_selects_exactly_one_adapter_without_fallback(
    tmp_path: Path,
) -> None:
    openai = resolve_speech_provider("openai", speech_config(), tmp_path)
    qwen = resolve_speech_provider("bailian_qwen", qwen_config(), tmp_path)
    try:
        assert isinstance(openai, OpenAiSpeechProvider)
        assert isinstance(qwen, BailianQwenSpeechProvider)
    finally:
        await openai.aclose()
        await qwen.aclose()


def test_structured_request_compiles_without_exact_text_mutation_and_two_voices_differ() -> None:
    first = speech_request("marin")
    second = speech_request("cedar")
    first_payload = compile_openai_speech_payload(first)
    second_payload = compile_openai_speech_payload(second)
    assert first_payload["input"] == first.exact_text
    assert second_payload["input"] == second.exact_text
    assert first_payload["voice"] != second_payload["voice"]
    assert first.exact_text not in first_payload["instructions"]


def test_qwen_payload_keeps_dialogue_exact_and_controls_separate() -> None:
    first = qwen_request("Cherry")
    second = qwen_request("Ethan")
    first_payload = compile_bailian_qwen_speech_payload(first)
    second_payload = compile_bailian_qwen_speech_payload(second)
    assert first_payload["input"]["text"] == first.exact_text
    assert first.exact_text not in first_payload["input"]["instructions"]
    assert first_payload["input"]["optimize_instructions"] is False
    assert first_payload["input"]["language_type"] == "Chinese"
    assert first_payload["input"]["voice"] == "Cherry"
    assert second_payload["input"]["voice"] == "Ethan"
    assert "表演意图" in first_payload["input"]["instructions"]
    assert "创作声音画像" in first_payload["input"]["instructions"]
    assert "材质控制" in first_payload["input"]["instructions"]
    assert audio_input_fingerprint(first) != audio_input_fingerprint(second)


def test_qwen_flash_fallback_is_only_an_explicit_mapping_choice() -> None:
    payload = compile_bailian_qwen_speech_payload(
        qwen_request("Cherry", model="qwen3-tts-flash")
    )
    assert payload["model"] == "qwen3-tts-flash"
    assert "instructions" not in payload["input"]
    assert "optimize_instructions" not in payload["input"]


def test_openai_and_qwen_mappings_change_fingerprint_not_dialogue_or_profile() -> None:
    openai_mapping = ProviderVoiceMapping(
        provider="openai",
        model="gpt-4o-mini-tts",
        voice_id="marin",
        material_parameters={"response_format": "wav"},
    )
    qwen_mapping = ProviderVoiceMapping(
        provider="bailian_qwen",
        model="qwen3-tts-instruct-flash",
        voice_id="Cherry",
        material_parameters={"language_type": "Chinese"},
    )
    profile = VoiceProfile(
        profile_id="profile:provider-neutral",
        speaker_key="speaker:provider-neutral",
        creative_profile=CreativeVoiceProfile(
            age_presentation="adult",
            timbre="neutral",
            temperament="restrained",
            baseline_pace="measured",
            power="moderate",
            restraint="high",
            language="zh-CN",
        ),
        provider_mappings=[openai_mapping, qwen_mapping],
    )
    spoken = {
        "spokenContentId": "spoken:provider-neutral",
        "speakerKey": profile.speaker_key,
        "text": "军令未下，各部不得擅动。",
        "performanceIntent": {"delivery": "neutral"},
    }
    common = {
        "work_id": "work-provider-neutral",
        "scene_id": "scene-provider-neutral",
        "spoken_content": spoken,
        "voice_profile": profile,
        "pronunciation_guidance": [],
        "material_render_parameters": {},
        "target_timing_policy": TargetTimingPolicy(policy="NATURAL"),
    }
    openai_request = compile_speech_request(
        **common, provider_mapping=openai_mapping
    )
    qwen_render_request = compile_speech_request(
        **common, provider_mapping=qwen_mapping
    )
    assert openai_request.exact_text == qwen_render_request.exact_text == spoken["text"]
    assert openai_request.speaker_key == qwen_render_request.speaker_key
    assert (
        openai_request.voice_profile.creative_profile
        == qwen_render_request.voice_profile.creative_profile
    )
    assert audio_input_fingerprint(openai_request) != audio_input_fingerprint(
        qwen_render_request
    )


@pytest.mark.asyncio
async def test_qwen_success_downloads_ephemeral_url_without_persisting_it(
    tmp_path: Path,
) -> None:
    seen: dict[str, Any] = {}
    signed_url = "https://download.invalid/result.wav?Signature=sensitive-signed-value"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            seen["generationUrl"] = str(request.url)
            seen["authorizationPresent"] = request.headers.get(
                "authorization", ""
            ).startswith("Bearer ")
            seen["payload"] = request.read().decode("utf-8")
            return httpx.Response(
                200,
                json={
                    "request_id": "dashscope-request-unit",
                    "output": {
                        "audio": {
                            "url": signed_url,
                            "id": "audio-unit",
                            "expires_at": 9999999999,
                        }
                    },
                },
            )
        seen["downloadUrl"] = str(request.url)
        return httpx.Response(
            200, content=b"RIFF-qwen-real-audio", headers={"content-type": "audio/wav"}
        )

    async with httpx.AsyncClient(
        base_url="https://unit.invalid/api/v1/", transport=httpx.MockTransport(handler)
    ) as client:
        result = await BailianQwenSpeechProvider(
            qwen_config(), tmp_path, client
        ).generate_speech(qwen_request())
    assert seen["generationUrl"].endswith(
        "/api/v1/services/aigc/multimodal-generation/generation"
    )
    assert seen["downloadUrl"] == signed_url
    assert seen["authorizationPresent"] is True
    assert qwen_request().exact_text in seen["payload"]
    output = Path(result.source_uri.removeprefix("file://"))
    assert output.read_bytes() == b"RIFF-qwen-real-audio"
    assert result.provider_metadata["providerRequestId"] == "dashscope-request-unit"
    assert result.provider_metadata["providerAudioId"] == "audio-unit"
    assert result.provider_metadata["callCount"] == 1
    assert result.provider_metadata["downloadCallCount"] == 1
    assert result.provider_metadata["responseSha256"]
    assert signed_url not in repr(result)
    assert "sensitive-signed-value" not in repr(result)
    assert "dashscope-unit-secret-must-not-leak" not in repr(result)


@pytest.mark.asyncio
async def test_qwen_rejects_nonaudio_download_without_leaking_response(
    tmp_path: Path,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "request_id": "req-nonaudio",
                    "output": {"audio": {"url": "https://download.invalid/result.wav"}},
                },
            )
        return httpx.Response(
            200,
            content=b"sensitive html body",
            headers={"content-type": "text/html"},
        )

    async with httpx.AsyncClient(
        base_url="https://unit.invalid/api/v1/", transport=httpx.MockTransport(handler)
    ) as client:
        provider = BailianQwenSpeechProvider(qwen_config(), tmp_path, client)
        with pytest.raises(SpeechProviderError) as raised:
            await provider.generate_speech(qwen_request())
    assert "sensitive html body" not in str(raised.value)


@pytest.mark.asyncio
async def test_qwen_maps_http_error_without_body_url_or_secret(tmp_path: Path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "message": "sensitive upstream body",
                "url": "https://signed.invalid/x?Signature=sensitive",
            },
        )

    async with httpx.AsyncClient(
        base_url="https://unit.invalid/api/v1/", transport=httpx.MockTransport(handler)
    ) as client:
        provider = BailianQwenSpeechProvider(qwen_config(), tmp_path, client)
        with pytest.raises(SpeechProviderError) as raised:
            await provider.generate_speech(qwen_request())
    rendered = str(raised.value)
    assert raised.value.status_code == 400
    assert "sensitive upstream body" not in rendered
    assert "Signature" not in rendered
    assert "dashscope-unit-secret-must-not-leak" not in rendered


@pytest.mark.asyncio
async def test_qwen_generation_rate_limit_retry_and_ambiguous_timeout_safety(
    tmp_path: Path,
) -> None:
    rate_limit_calls = 0

    def retry_handler(request: httpx.Request) -> httpx.Response:
        nonlocal rate_limit_calls
        if request.method == "POST":
            rate_limit_calls += 1
            if rate_limit_calls == 1:
                return httpx.Response(429)
            return httpx.Response(
                200,
                json={
                    "request_id": "req-retry",
                    "output": {"audio": {"url": "https://download.invalid/retry.wav"}},
                },
            )
        return httpx.Response(
            200, content=b"RIFF-retry", headers={"content-type": "audio/wav"}
        )

    async with httpx.AsyncClient(
        base_url="https://unit.invalid/api/v1/",
        transport=httpx.MockTransport(retry_handler),
    ) as client:
        result = await BailianQwenSpeechProvider(
            qwen_config(), tmp_path, client
        ).generate_speech(qwen_request())
    assert rate_limit_calls == 2
    assert result.provider_metadata["callCount"] == 2
    assert result.provider_metadata["retryCount"] == 1

    timeout_calls = 0

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        nonlocal timeout_calls
        timeout_calls += 1
        raise httpx.ReadTimeout("ambiguous sensitive upstream text", request=request)

    async with httpx.AsyncClient(
        base_url="https://unit.invalid/api/v1/",
        transport=httpx.MockTransport(timeout_handler),
    ) as client:
        provider = BailianQwenSpeechProvider(qwen_config(), tmp_path, client)
        with pytest.raises(ProviderResultUnknown) as raised:
            await provider.generate_speech(qwen_request())
    assert timeout_calls == 1
    assert "sensitive upstream text" not in str(raised.value)


@pytest.mark.asyncio
async def test_provider_http_success_saves_original_audio_and_redacted_metadata(
    tmp_path: Path,
) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorizationPresent"] = request.headers.get("authorization", "").startswith(
            "Bearer "
        )
        seen["body"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            content=b"RIFF-real-audio",
            headers={"content-type": "audio/wav", "x-request-id": "req-unit"},
        )

    async with httpx.AsyncClient(
        base_url="https://unit.invalid/v1/", transport=httpx.MockTransport(handler)
    ) as client:
        provider = OpenAiSpeechProvider(speech_config(), tmp_path, client)
        result = await provider.generate_speech(speech_request())
    assert seen["url"] == "https://unit.invalid/v1/audio/speech"
    assert seen["authorizationPresent"] is True
    assert speech_request().exact_text in seen["body"]
    output = Path(result.source_uri.removeprefix("file://"))
    assert output.read_bytes() == b"RIFF-real-audio"
    assert result.provider_metadata["callCount"] == 1
    assert result.provider_metadata["retryCount"] == 0
    assert "unit-secret-must-not-leak" not in repr(result)


@pytest.mark.asyncio
async def test_provider_maps_http_error_without_response_body_or_secret(tmp_path: Path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "sensitive upstream detail"})

    async with httpx.AsyncClient(
        base_url="https://unit.invalid/v1/", transport=httpx.MockTransport(handler)
    ) as client:
        provider = OpenAiSpeechProvider(speech_config(), tmp_path, client)
        with pytest.raises(SpeechProviderError) as raised:
            await provider.generate_speech(speech_request())
    rendered = str(raised.value)
    assert "sensitive upstream detail" not in rendered
    assert "unit-secret-must-not-leak" not in rendered
    assert raised.value.status_code == 400


@pytest.mark.asyncio
async def test_explicit_rate_limit_is_safely_retried(tmp_path: Path) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429)
        return httpx.Response(200, content=b"RIFF-ok", headers={"content-type": "audio/wav"})

    async with httpx.AsyncClient(
        base_url="https://unit.invalid/v1/", transport=httpx.MockTransport(handler)
    ) as client:
        result = await OpenAiSpeechProvider(speech_config(), tmp_path, client).generate_speech(
            speech_request()
        )
    assert calls == 2
    assert result.provider_metadata["callCount"] == 2
    assert result.provider_metadata["retryCount"] == 1


@pytest.mark.asyncio
async def test_ambiguous_read_timeout_is_never_automatically_retried(tmp_path: Path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("ambiguous", request=request)

    async with httpx.AsyncClient(
        base_url="https://unit.invalid/v1/", transport=httpx.MockTransport(handler)
    ) as client:
        provider = OpenAiSpeechProvider(speech_config(), tmp_path, client)
        with pytest.raises(ProviderResultUnknown):
            await provider.generate_speech(speech_request())
    assert calls == 1


class CountingSpeechProvider:
    def __init__(self, source: Path) -> None:
        self.source = source
        self.calls = 0

    async def generate_speech(
        self, request: SpeechGenerationRequest
    ) -> SpeechGenerationResult:
        self.calls += 1
        return SpeechGenerationResult(
            source_uri=self.source.as_uri(),
            mime_type="audio/wav",
            provider_metadata={"attemptId": "attempt-unit"},
        )


@pytest.mark.asyncio
async def test_canonical_media_idempotency_gate_prevents_real_provider_call(
    tmp_path: Path,
) -> None:
    current = speech_request()
    fingerprint = audio_input_fingerprint(current)
    data = MockDramaData()
    existing = Media(
        id="media-reviewed",
        work_id=current.work_id,
        media_type=MediaType.AUDIO,
        purpose="SPEECH_CLIP",
        source_ref=canonical_audio_source_ref(fingerprint),
        duration_ms=1000,
        content={"reviewStatus": "PASS", "audioInputFingerprint": fingerprint},
    )
    data.media.append(existing)
    source = tmp_path / "unused.wav"
    source.write_bytes(b"unused")
    speech = CountingSpeechProvider(source)
    provider = SpeechBackedProductionProvider(
        MockProductionProvider(data), speech, MockMediaProvider(data)
    )
    result = await provider.generate_audio(
        current.exact_text,
        parameters={"speechRequest": current.model_dump(mode="json", by_alias=True)},
    )
    assert result.id == "media-reviewed"
    assert speech.calls == 0


@pytest.mark.asyncio
async def test_generated_physical_audio_is_imported_only_as_pending_attempt(
    tmp_path: Path,
) -> None:
    current = speech_request()
    source = tmp_path / "real.wav"
    source.write_bytes(b"RIFF-real")
    data = MockDramaData()
    speech = CountingSpeechProvider(source)
    physical = MediaProbe(
        duration_ms=1234,
        streams=({"codec_type": "audio", "codec_name": "pcm_s16le"},),
        implementation="ffprobe",
        version="ffprobe unit",
    )
    provider = SpeechBackedProductionProvider(
        MockProductionProvider(data),
        speech,
        MockMediaProvider(data),
        probe=lambda _: physical,
    )
    result = await provider.generate_audio(
        current.exact_text,
        parameters={"speechRequest": current.model_dump(mode="json", by_alias=True)},
    )
    assert speech.calls == 1
    assert result.duration_ms == 1234
    assert result.source_ref.startswith(
        f"audio-attempt:{audio_input_fingerprint(current)}:"
    )
    assert result.content["reviewStatus"] == "PENDING"
    assert result.content["textHash"]
    assert "exactText" not in result.content


def test_final_av_canonical_and_attempt_source_refs_are_distinct() -> None:
    fingerprint = "f" * 64
    assert canonical_final_av_source_ref(fingerprint) == f"final-av:{fingerprint}"
    assert final_av_attempt_source_ref(fingerprint, "review-1") == (
        f"final-av-attempt:{fingerprint}:review-1"
    )
    with pytest.raises(ValueError):
        final_av_attempt_source_ref(fingerprint, "bad:attempt")


def test_audio_skill_remains_vendor_neutral() -> None:
    skill = (
        Path(__file__).resolve().parents[1] / "skills" / "audio-production" / "SKILL.md"
    ).read_text(encoding="utf-8").lower()
    assert "openai" not in skill
    assert "elevenlabs" not in skill
    assert "qwen" not in skill
    assert "dashscope" not in skill
    assert "bailian" not in skill
