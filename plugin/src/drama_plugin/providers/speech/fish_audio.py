from __future__ import annotations

import json
import mimetypes
import base64
import binascii
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from drama_plugin.exceptions import ProviderResultUnknown, SpeechProviderError


FISH_AUDIO_BASE_URL = "https://api.fish.audio"
FISH_TTS_MODEL = "s2-pro"
FISH_VOICE_DESIGN_MODEL = "voice-design-1"


@dataclass(frozen=True)
class FishVoiceDesignCandidate:
    candidate_id: str
    index: int
    audio: bytes
    sample_rate: int
    duration_ms: int
    text: str
    instruction: str
    language: str


@dataclass(frozen=True)
class FishVoiceDesignResult:
    candidates: tuple[FishVoiceDesignCandidate, ...]
    provider_request_id: str | None


@dataclass(frozen=True)
class FishModelResult:
    reference_id: str
    state: str
    provider_request_id: str | None


@dataclass(frozen=True)
class FishAsrResult:
    text: str
    duration_seconds: float
    language: str | None
    segments: tuple[dict[str, Any], ...]
    provider_request_id: str | None


def compile_fish_tts_payload(
    *,
    exact_text: str,
    reference_id: str,
    mode: str,
    speed: float | None = None,
    volume: float | None = None,
) -> dict[str, Any]:
    if mode not in {"baseline", "directed"}:
        raise ValueError("Fish validation mode must be baseline or directed")
    if not exact_text:
        raise ValueError("Fish TTS exact text must not be empty")
    if not reference_id:
        raise ValueError("Fish TTS reference id must not be empty")
    payload: dict[str, Any] = {
        "text": exact_text,
        "reference_id": reference_id,
        "format": "wav",
        "sample_rate": 24000,
        "normalize": True,
    }
    if mode == "directed":
        if speed is None or volume is None:
            raise ValueError("Directed Fish TTS requires speed and volume")
        if not 0.5 <= speed <= 2.0:
            raise ValueError("Fish prosody speed must be between 0.5 and 2.0")
        if not -20.0 <= volume <= 20.0:
            raise ValueError("Fish prosody volume must be between -20 and 20")
        payload["prosody"] = {
            "speed": speed,
            "volume": volume,
            "normalize_loudness": True,
        }
    return payload


def compile_fish_voice_design_payload(
    *, instruction: str, reference_text: str, candidate_count: int = 3
) -> dict[str, Any]:
    if not 1 <= len(instruction) <= 2000:
        raise ValueError("Fish Voice Design instruction must be 1 to 2000 characters")
    if len(reference_text) > 150:
        raise ValueError("Fish Voice Design reference text must not exceed 150 characters")
    if not 1 <= candidate_count <= 4:
        raise ValueError("Fish Voice Design candidate count must be between 1 and 4")
    return {
        "instruction": instruction,
        "reference_text": reference_text,
        "language": "zh",
        "n": candidate_count,
        "speed": 1.0,
        "num_step": 32,
        "guidance_scale": 2.0,
        "instruct_guidance_scale": 0.0,
        "seed": 7202,
    }


def _request_id(response: httpx.Response) -> str | None:
    for name in ("x-request-id", "x-trace-id", "request-id", "trace-id"):
        value = response.headers.get(name)
        if value:
            return str(value)
    return None


def _safe_error(response: httpx.Response, secrets: tuple[str, ...]) -> SpeechProviderError:
    provider_code: str | None = None
    provider_message: str | None = None
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict):
        raw_code = payload.get("code", payload.get("status"))
        if raw_code is not None:
            provider_code = str(raw_code)[:80]
        raw_message = payload.get("message", payload.get("reason"))
        if raw_message is not None:
            provider_message = str(raw_message)[:500]
            for secret in secrets:
                if secret:
                    provider_message = provider_message.replace(secret, "[REDACTED]")
    return SpeechProviderError(
        "Fish Audio API rejected the request",
        status_code=response.status_code,
        retryable=response.status_code == 429 or response.status_code >= 500,
        provider_error_code=provider_code,
        provider_error_message=provider_message,
        provider_request_id=_request_id(response),
    )


class FishAudioHttpClient:
    """Minimal Fish Developer API client for the temporary validation workflow."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = FISH_AUDIO_BASE_URL,
        timeout_seconds: float = 120.0,
        max_transient_retries: int = 1,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise SpeechProviderError("Fish Audio credential is missing")
        if base_url.rstrip("/") != FISH_AUDIO_BASE_URL:
            raise SpeechProviderError("Fish validation requires the official api.fish.audio endpoint")
        self._authorization = f"Bearer {api_key}"
        self._owns_client = client is None
        self._max_transient_retries = max_transient_retries
        self.client = client or httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/", timeout=timeout_seconds
        )

    async def __aenter__(self) -> FishAudioHttpClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _post(self, path: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = self._authorization
        for retry_index in range(self._max_transient_retries + 1):
            try:
                response = await self.client.post(path, headers=headers, **kwargs)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                if retry_index >= self._max_transient_retries:
                    raise SpeechProviderError(
                        "Fish Audio connection failed before a confirmed result",
                        retryable=True,
                    ) from exc
                continue
            except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
                raise ProviderResultUnknown(
                    "Fish Audio result is unknown after an ambiguous timeout"
                ) from exc
            if response.status_code == 429 or response.status_code >= 500:
                if retry_index < self._max_transient_retries:
                    continue
            return response
        raise AssertionError("unreachable")

    async def create_model(
        self, *, reference_audio: Path, title: str, reference_text: str | None = None
    ) -> FishModelResult:
        mime = mimetypes.guess_type(reference_audio.name)[0] or "application/octet-stream"
        data = {
            "type": "tts",
            "title": title,
            "train_mode": "fast",
            "visibility": "private",
            "enhance_audio_quality": "true",
            "generate_sample": "false",
        }
        if reference_text:
            data["texts"] = reference_text
        response = await self._post(
            "model",
            data=data,
            files={"voices": (reference_audio.name, reference_audio.read_bytes(), mime)},
        )
        if response.status_code != 201:
            raise _safe_error(response, (self._authorization, self._authorization[7:]))
        payload = response.json()
        reference_id = str(payload.get("_id", "")).strip()
        if not reference_id:
            raise SpeechProviderError("Fish Create Model response omitted _id")
        return FishModelResult(
            reference_id=reference_id,
            state=str(payload.get("state", "")),
            provider_request_id=_request_id(response),
        )

    async def design_voice(
        self, payload: dict[str, Any]
    ) -> FishVoiceDesignResult:
        response = await self._post(
            "v1/voice-design",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "model": FISH_VOICE_DESIGN_MODEL,
            },
        )
        if response.status_code != 200:
            raise _safe_error(response, (self._authorization, self._authorization[7:]))
        body = response.json()
        raw_candidates = body.get("candidates")
        if not isinstance(raw_candidates, list) or not raw_candidates:
            raise SpeechProviderError("Fish Voice Design response omitted candidates")
        candidates: list[FishVoiceDesignCandidate] = []
        for raw in raw_candidates:
            if not isinstance(raw, dict):
                raise SpeechProviderError("Fish Voice Design candidate is invalid")
            try:
                audio = base64.b64decode(str(raw["audio_base64"]), validate=True)
            except (KeyError, binascii.Error, ValueError) as exc:
                raise SpeechProviderError(
                    "Fish Voice Design candidate audio is invalid"
                ) from exc
            if not audio:
                raise SpeechProviderError("Fish Voice Design candidate audio is empty")
            candidates.append(
                FishVoiceDesignCandidate(
                    candidate_id=str(raw.get("id", "")),
                    index=int(raw["index"]),
                    audio=audio,
                    sample_rate=int(raw.get("sample_rate", 0)),
                    duration_ms=int(raw.get("duration_ms", 0)),
                    text=str(raw.get("text", "")),
                    instruction=str(raw.get("instruct", "")),
                    language=str(raw.get("language", "")),
                )
            )
        expected_count = int(payload.get("n", 0))
        if expected_count and len(candidates) != expected_count:
            raise SpeechProviderError(
                "Fish Voice Design candidate count differs from the request"
            )
        return FishVoiceDesignResult(
            candidates=tuple(candidates), provider_request_id=_request_id(response)
        )

    async def synthesize(self, payload: dict[str, Any]) -> tuple[bytes, str | None]:
        response = await self._post(
            "v1/tts",
            json=payload,
            headers={"Content-Type": "application/json", "model": FISH_TTS_MODEL},
        )
        if response.status_code != 200:
            raise _safe_error(response, (self._authorization, self._authorization[7:]))
        if not response.content:
            raise SpeechProviderError("Fish TTS returned an empty audio response")
        return response.content, _request_id(response)

    async def transcribe(self, audio_path: Path) -> FishAsrResult:
        mime = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"
        response = await self._post(
            "v1/asr",
            data={"language": "zh", "ignore_timestamps": "true"},
            files={"audio": (audio_path.name, audio_path.read_bytes(), mime)},
        )
        if response.status_code != 200:
            raise _safe_error(response, (self._authorization, self._authorization[7:]))
        payload = response.json()
        text = str(payload.get("text", "")).strip()
        if not text:
            raise SpeechProviderError("Fish ASR response omitted text")
        raw_segments = payload.get("segments", [])
        return FishAsrResult(
            text=text,
            duration_seconds=float(payload.get("duration", 0.0)),
            language=(str(payload["language"]) if payload.get("language") else None),
            segments=tuple(item for item in raw_segments if isinstance(item, dict)),
            provider_request_id=_request_id(response),
        )
