from __future__ import annotations

import json
import mimetypes
import base64
import binascii
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import Field, model_validator

from drama_plugin.contracts.audio_projection import (
    AudioCapabilityDiagnostic,
    AudioPerformanceBrief,
    CapabilityStatus,
    PaceTendency,
    VolumeTendency,
)
from drama_plugin.contracts.base import ContractModel
from drama_plugin.exceptions import ProviderResultUnknown, SpeechProviderError


FISH_AUDIO_BASE_URL = "https://api.fish.audio"
FISH_TTS_MODEL = "s2-pro"
FISH_VOICE_DESIGN_MODEL = "voice-design-1"
FISH_S2_RENDER_MARKERS = frozenset(
    {"break", "curious", "emphasis", "long-break"}
)
_RENDER_MARKER = re.compile(r"\[([^\[\]]+)\]")
_RENDER_PUNCTUATION = frozenset(
    " \t\r\n，、。！？；：…—,.!?;:'\"“”‘’（）()"
)


class FishAudioPerformanceMapping(ContractModel):
    schema_version: Literal["fish-audio-performance-mapping-v1"] = (
        "fish-audio-performance-mapping-v1"
    )
    audio_projection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    speed: float = Field(ge=0.5, le=2.0)
    volume: float = Field(ge=-20.0, le=20.0)
    capabilities: tuple[AudioCapabilityDiagnostic, ...]

    @model_validator(mode="after")
    def validate_capability_set(self) -> "FishAudioPerformanceMapping":
        expected = {
            "pace",
            "volumeTendency",
            "rhythm",
            "intensity",
            "pauseStrategy",
            "articulation",
            "emphasis",
            "sentenceEnding",
            "control",
            "preUtterancePreparation",
            "postUtteranceHold",
        }
        actual = [item.dimension for item in self.capabilities]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError("Fish capability diagnostics are incomplete or duplicated")
        return self


def map_audio_performance_to_fish(
    brief: AudioPerformanceBrief,
) -> FishAudioPerformanceMapping:
    speed = {
        PaceTendency.SLOWER: 0.92,
        PaceTendency.NEUTRAL: 1.0,
        PaceTendency.FASTER: 1.08,
    }[brief.pace_tendency]
    volume = {
        VolumeTendency.LOWER: -2.0,
        VolumeTendency.NEUTRAL: 0.0,
        VolumeTendency.HIGHER: 2.0,
    }[brief.volume_tendency]
    diagnostics = (
        AudioCapabilityDiagnostic(
            dimension="pace",
            status=CapabilityStatus.SUPPORTED,
            mapped_control="prosody.speed",
            reason="Fish exposes a bounded speed control.",
        ),
        AudioCapabilityDiagnostic(
            dimension="volumeTendency",
            status=CapabilityStatus.SUPPORTED,
            mapped_control="prosody.volume",
            reason="Fish exposes a bounded volume adjustment.",
        ),
        AudioCapabilityDiagnostic(
            dimension="rhythm",
            status=CapabilityStatus.TEXT_RENDERABLE,
            mapped_control="S2 punctuation and [break]/[long-break] markers",
            reason="S2 can render phrase separation in text, but production promotion awaits listening review.",
        ),
        AudioCapabilityDiagnostic(
            dimension="intensity",
            status=CapabilityStatus.TEXT_RENDERABLE,
            mapped_control="S2 expression/tone markers",
            reason="S2 expression markers can render intensity; automatic use awaits listening review.",
        ),
        AudioCapabilityDiagnostic(
            dimension="pauseStrategy",
            status=CapabilityStatus.TEXT_RENDERABLE,
            mapped_control="S2 [break]/[long-break] markers",
            reason="S2 documents pause markers; automatic use awaits listening review.",
        ),
        AudioCapabilityDiagnostic(
            dimension="articulation",
            status=CapabilityStatus.UNSUPPORTED,
            reason="The verified Fish TTS request has no articulation control.",
        ),
        AudioCapabilityDiagnostic(
            dimension="emphasis",
            status=CapabilityStatus.TEXT_RENDERABLE,
            mapped_control="S2 [emphasis] marker",
            reason="S2 documents an emphasis marker; automatic use awaits listening review.",
        ),
        AudioCapabilityDiagnostic(
            dimension="sentenceEnding",
            status=CapabilityStatus.TEXT_RENDERABLE,
            mapped_control="canonical punctuation plus S2 expression markers",
            reason="Punctuation and expression cues can influence endings; automatic use awaits review.",
        ),
        AudioCapabilityDiagnostic(
            dimension="control",
            status=CapabilityStatus.TEXT_RENDERABLE,
            mapped_control="S2 natural-language expression marker",
            reason="S2 accepts concise expression cues; automatic use awaits listening review.",
        ),
        AudioCapabilityDiagnostic(
            dimension="preUtterancePreparation",
            status=CapabilityStatus.APPROXIMATED,
            mapped_control="leading S2 expression marker",
            reason="A leading cue can condition onset style but cannot guarantee an audible preparation.",
        ),
        AudioCapabilityDiagnostic(
            dimension="postUtteranceHold",
            status=CapabilityStatus.UNSUPPORTED,
            reason="The verified API has no durable post-utterance hold control.",
        ),
    )
    return FishAudioPerformanceMapping(
        audio_projection_fingerprint=brief.fingerprint,
        speed=speed,
        volume=volume,
        capabilities=diagnostics,
    )


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


def compile_fish_rendered_text(*, canonical_text: str, rendered_text: str,
                               performance_brief: AudioPerformanceBrief | None = None) -> str:
    """Validate a small, official S2 rendering surface without rewriting dialogue."""
    if not canonical_text or not rendered_text:
        raise ValueError("Fish canonical and rendered text must not be empty")
    approved_cue = _brief_expression_cue(performance_brief) if performance_brief is not None else None
    if len(rendered_text) > len(canonical_text) + (520 if approved_cue else 80):
        raise ValueError("Fish rendered text adds excessive provider direction")
    markers = _RENDER_MARKER.findall(rendered_text)
    if approved_cue is not None and rendered_text != f"[{approved_cue}]{canonical_text}":
        raise ValueError("production expression rendering must come entirely from the Audio brief")
    if any(marker not in FISH_S2_RENDER_MARKERS and marker != approved_cue for marker in markers):
        raise ValueError("Fish rendered text contains an unsupported S2 marker")
    without_markers = _RENDER_MARKER.sub("", rendered_text)
    if "[" in without_markers or "]" in without_markers:
        raise ValueError("Fish rendered text contains malformed S2 markers")

    def lexical(value: str) -> str:
        return "".join(character for character in value if character not in _RENDER_PUNCTUATION)

    if lexical(without_markers) != lexical(canonical_text):
        raise ValueError("Fish rendered text must preserve canonical lexical content")
    return rendered_text


def _brief_expression_cue(brief: AudioPerformanceBrief) -> str:
    """Serialize execution instructions; never inspect DPD, video, or dramatic-action labels."""
    cue = "; ".join((brief.control, brief.intensity, brief.rhythm,
                     brief.pause_strategy, brief.sentence_ending))
    if len(cue) > 500 or any(c in cue for c in "[]\n\r"):
        raise ValueError("Audio brief expression cue exceeds the safe bounded rendering surface")
    return cue


def compile_fish_tts_payload(
    *,
    exact_text: str,
    reference_id: str,
    mode: str,
    speed: float | None = None,
    volume: float | None = None,
    rendered_text: str | None = None,
    performance_brief: AudioPerformanceBrief | None = None,
) -> dict[str, Any]:
    if mode not in {"baseline", "directed"}:
        raise ValueError("Fish validation mode must be baseline or directed")
    if not exact_text:
        raise ValueError("Fish TTS exact text must not be empty")
    if not reference_id:
        raise ValueError("Fish TTS reference id must not be empty")
    if performance_brief is not None:
        if rendered_text is not None:
            raise ValueError("manual rendered text conflicts with Brief-derived rendering")
        rendered_text = f"[{_brief_expression_cue(performance_brief)}]{exact_text}"
    payload: dict[str, Any] = {
        "text": (
            compile_fish_rendered_text(
                canonical_text=exact_text, rendered_text=rendered_text,
                performance_brief=performance_brief,
            )
            if rendered_text is not None
            else exact_text
        ),
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

    async def _get(self, path: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = self._authorization
        try:
            return await self.client.get(path, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise SpeechProviderError("Fish Audio query failed", retryable=True) from exc

    async def find_model_by_title(self, title: str) -> FishModelResult | None:
        response = await self._get("model", params={"title": title})
        if response.status_code != 200:
            raise _safe_error(response, (self._authorization, self._authorization[7:]))
        body = response.json()
        items = body.get("items", []) if isinstance(body, dict) else []
        matches = [item for item in items if isinstance(item, dict) and item.get("title") == title]
        if not matches:
            return None
        if len(matches) != 1:
            raise ProviderResultUnknown("Fish Create Model recovery found multiple matching models")
        match = matches[0]
        reference_id = str(match.get("_id", "")).strip()
        if not reference_id:
            raise SpeechProviderError("Fish model recovery omitted _id")
        return FishModelResult(reference_id=reference_id, state=str(match.get("state", "")),
                               provider_request_id=_request_id(response))

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
        try:
            response = await self._post(
                "model",
                data=data,
                files={"voices": (reference_audio.name, reference_audio.read_bytes(), mime)},
            )
        except ProviderResultUnknown:
            recovered = await self.find_model_by_title(title)
            if recovered is not None:
                return recovered
            raise
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
