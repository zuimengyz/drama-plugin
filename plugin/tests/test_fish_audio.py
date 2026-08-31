from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from drama_plugin.exceptions import ProviderResultUnknown, SpeechProviderError
from drama_plugin.providers.speech.fish_audio import (
    FISH_TTS_MODEL,
    FISH_VOICE_DESIGN_MODEL,
    FishAudioHttpClient,
    compile_fish_rendered_text,
    compile_fish_tts_payload,
    compile_fish_voice_design_payload,
)


def test_fish_payload_preserves_exact_dialogue_and_separates_modes() -> None:
    text = "请给我三十骑，取杨国忠首级，为大帅除患。"
    baseline = compile_fish_tts_payload(
        exact_text=text, reference_id="voice-1", mode="baseline"
    )
    directed = compile_fish_tts_payload(
        exact_text=text,
        reference_id="voice-1",
        mode="directed",
        speed=1.05,
        volume=-1.0,
    )
    assert baseline["text"] == directed["text"] == text
    assert baseline["reference_id"] == directed["reference_id"] == "voice-1"
    assert "prosody" not in baseline
    assert directed["prosody"] == {
        "speed": 1.05,
        "volume": -1.0,
        "normalize_loudness": True,
    }


def test_fish_rendered_text_preserves_canonical_words_and_limits_markers() -> None:
    canonical = "你可知道后果？"
    punctuation = "你……可知道后果？"
    expressive = "[curious]你可知道[break][emphasis]后果？"
    assert compile_fish_rendered_text(
        canonical_text=canonical, rendered_text=punctuation
    ) == punctuation
    assert compile_fish_tts_payload(
        exact_text=canonical,
        rendered_text=expressive,
        reference_id="voice-1",
        mode="directed",
        speed=1.0,
        volume=-2.0,
    )["text"] == expressive
    with pytest.raises(ValueError, match="unsupported S2 marker"):
        compile_fish_rendered_text(
            canonical_text=canonical,
            rendered_text="[make this perfect]你可知道后果？",
        )
    with pytest.raises(ValueError, match="preserve canonical lexical content"):
        compile_fish_rendered_text(
            canonical_text=canonical, rendered_text="你可明白后果？"
        )


def test_dramatic_action_is_not_hardcoded_to_fish_emotion_marker() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src/drama_plugin/providers/speech/fish_audio.py"
    ).read_text(encoding="utf-8")
    assert "dramatic_action" not in source
    assert '"probe"' not in source
    assert compile_fish_tts_payload(
        exact_text="你可知道后果？",
        reference_id="voice-1",
        mode="directed",
        speed=1.0,
        volume=0.0,
    )["text"] == "你可知道后果？"


def test_voice_design_payload_is_small_and_requests_three_candidates() -> None:
    instruction = "Mandarin Chinese voice with firm articulation and moderate pace."
    payload = compile_fish_voice_design_payload(
        instruction=instruction,
        reference_text="此事若行，我便是反臣。不可。",
        candidate_count=3,
    )
    assert payload == {
        "instruction": instruction,
        "reference_text": "此事若行，我便是反臣。不可。",
        "language": "zh",
        "n": 3,
        "speed": 1.0,
        "num_step": 32,
        "guidance_scale": 2.0,
        "instruct_guidance_scale": 0.0,
        "seed": 7202,
    }


@pytest.mark.asyncio
async def test_fish_auth_is_sent_but_never_exposed_in_error() -> None:
    secret = "test-secret-that-must-not-leak"

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == f"Bearer {secret}"
        return httpx.Response(
            401,
            json={"status": 401, "message": f"bad token {secret}"},
            headers={"x-request-id": "req-safe"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        base_url="https://api.fish.audio/", transport=transport
    ) as http_client:
        client = FishAudioHttpClient(secret, client=http_client)
        with pytest.raises(SpeechProviderError) as raised:
            await client.synthesize(
                compile_fish_tts_payload(
                    exact_text="不可。", reference_id="voice-1", mode="baseline"
                )
            )
    assert secret not in str(raised.value)
    assert secret not in str(raised.value.provider_error_message)
    assert raised.value.provider_error_message == "bad token [REDACTED]"
    assert raised.value.provider_request_id == "req-safe"


@pytest.mark.asyncio
async def test_create_model_serialization_and_asr_parsing(tmp_path: Path) -> None:
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"RIFF-fixture")
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        body = request.content
        if request.url.path == "/model":
            assert b'name="type"' in body and b"tts" in body
            assert b'name="train_mode"' in body and b"fast" in body
            assert b'name="visibility"' in body and b"private" in body
            assert b'name="voices"' in body and b"RIFF-fixture" in body
            return httpx.Response(
                201,
                json={"_id": "temporary-model", "state": "created"},
            )
        assert request.url.path == "/v1/asr"
        assert b'name="audio"' in body and b"RIFF-fixture" in body
        assert b'name="language"' in body and b"zh" in body
        return httpx.Response(
            200,
            json={
                "text": "不可",
                "duration": 1.2,
                "language": "zh",
                "segments": [],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        base_url="https://api.fish.audio/", transport=transport
    ) as http_client:
        client = FishAudioHttpClient("safe-test-key", client=http_client)
        model = await client.create_model(
            reference_audio=reference, title="temporary", reference_text="不可"
        )
        asr = await client.transcribe(reference)
    assert model.reference_id == "temporary-model"
    assert asr.text == "不可"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_tts_request_uses_requested_s2_pro_model() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["model"] == FISH_TTS_MODEL == "s2-pro"
        assert request.url.path == "/v1/tts"
        return httpx.Response(200, content=b"audio-bytes")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        base_url="https://api.fish.audio/", transport=transport
    ) as http_client:
        client = FishAudioHttpClient("safe-test-key", client=http_client)
        audio, _ = await client.synthesize(
            compile_fish_tts_payload(
                exact_text="不可。", reference_id="temporary-model", mode="baseline"
            )
        )
    assert audio == b"audio-bytes"


@pytest.mark.asyncio
async def test_voice_design_response_parsing_and_model_header() -> None:
    payload = compile_fish_voice_design_payload(
        instruction="Mandarin Chinese voice with firm articulation.",
        reference_text="不可。",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/voice-design"
        assert request.headers["model"] == FISH_VOICE_DESIGN_MODEL == "voice-design-1"
        assert request.headers["authorization"] == "Bearer safe-test-key"
        request_payload = __import__("json").loads(request.content)
        assert request_payload["n"] == 3
        return httpx.Response(
            200,
            headers={"x-request-id": "design-request"},
            json={
                "candidates": [
                    {
                        "id": f"candidate-{index}",
                        "index": index,
                        "audio_base64": base64.b64encode(
                            f"candidate-{index}-wav".encode()
                        ).decode(),
                        "sample_rate": 24000,
                        "duration_ms": 1000,
                        "text": "不可。",
                        "instruct": payload["instruction"],
                        "language": "zh",
                    }
                    for index in range(1, 4)
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        base_url="https://api.fish.audio/", transport=transport
    ) as http_client:
        client = FishAudioHttpClient("safe-test-key", client=http_client)
        result = await client.design_voice(payload)
    assert len(result.candidates) == 3
    assert result.candidates[1].index == 2
    assert result.candidates[1].audio == b"candidate-2-wav"
    assert result.provider_request_id == "design-request"


@pytest.mark.asyncio
async def test_ambiguous_timeout_is_not_retried() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("unknown", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        base_url="https://api.fish.audio/", transport=transport
    ) as http_client:
        client = FishAudioHttpClient(
            "safe-test-key", max_transient_retries=2, client=http_client
        )
        with pytest.raises(ProviderResultUnknown):
            await client.synthesize(
                compile_fish_tts_payload(
                    exact_text="不可。", reference_id="temporary-model", mode="baseline"
                )
            )
    assert calls == 1
