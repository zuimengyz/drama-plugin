from __future__ import annotations

import hashlib
import json
import json
import uuid
from pathlib import Path
from typing import Any

import httpx

from drama_plugin.audio.foundation import audio_input_fingerprint
from drama_plugin.config.models import SpeechServiceConfig
from drama_plugin.contracts.audio import (
    ProviderMappingStatus,
    ProviderVoiceMapping,
    SpeechGenerationRequest,
    SpeechGenerationResult,
)
from drama_plugin.exceptions import ProviderResultUnknown, SpeechProviderError
from drama_plugin.providers.speech.casting import VoiceCandidate, rank_voice_candidates


_MIME_BY_FORMAT = {
    "aac": "audio/aac",
    "flac": "audio/flac",
    "mp3": "audio/mpeg",
    "opus": "audio/ogg",
    "pcm": "audio/L16",
    "wav": "audio/wav",
}
_EXTENSION_BY_FORMAT = {
    "aac": ".aac",
    "flac": ".flac",
    "mp3": ".mp3",
    "opus": ".opus",
    "pcm": ".pcm",
    "wav": ".wav",
}
_OPENAI_VOICE_CANDIDATES = (
    VoiceCandidate(
        "cedar",
        frozenset({"masculine", "feminine"}),
        {
            "vocal_age": 0.6,
            "vocal_weight": 0.7,
            "resonance_depth": 0.7,
            "timbre_brightness": 0.35,
            "articulation_firmness": 0.7,
            "phrase_attack": 0.65,
            "baseline_pace": 0.5,
            "baseline_energy": 0.6,
            "breath_support": 0.7,
            "command_presence": 0.75,
            "gravitas": 0.75,
            "controlled_power": 0.75,
            "sentence_finality": 0.75,
            "emotional_containment": 0.7,
        },
    ),
    VoiceCandidate(
        "marin",
        frozenset({"masculine", "feminine"}),
        {
            "vocal_age": 0.45,
            "vocal_weight": 0.45,
            "resonance_depth": 0.45,
            "timbre_brightness": 0.65,
            "articulation_firmness": 0.65,
            "phrase_attack": 0.55,
            "baseline_pace": 0.55,
            "baseline_energy": 0.6,
            "breath_support": 0.65,
            "command_presence": 0.5,
            "gravitas": 0.5,
            "controlled_power": 0.6,
            "sentence_finality": 0.6,
            "emotional_containment": 0.6,
        },
    ),
)


def _resolve_openai_mapping(request: SpeechGenerationRequest) -> ProviderVoiceMapping:
    ranked = rank_voice_candidates(
        request.voice_profile.creative_profile,
        _OPENAI_VOICE_CANDIDATES,
        limit=2,
    )
    ranking = [
        {
            "rank": index,
            "voiceId": item.voice_id,
            "score": item.score,
            "comparedDimensions": list(item.compared_dimensions),
        }
        for index, item in enumerate(ranked, start=1)
    ]
    selected = ranked[0]
    return ProviderVoiceMapping(
        provider="openai",
        model="gpt-4o-mini-tts",
        voice_id=selected.voice_id,
        status=ProviderMappingStatus.CANDIDATE,
        material_parameters={"response_format": "wav"},
        non_material_metadata={
            "selectionStrategy": "provider-profile-vector-v1",
            "candidateRanking": ranking,
            "selectedRank": 1,
            "voiceBindingStatus": "PENDING",
        },
    )


def _bind_mapping(
    request: SpeechGenerationRequest, mapping: ProviderVoiceMapping
) -> SpeechGenerationRequest:
    existing = [
        item
        for item in request.voice_profile.provider_mappings
        if (item.provider, item.model, item.voice_id)
        != (mapping.provider, mapping.model, mapping.voice_id)
    ]
    profile = request.voice_profile.model_copy(
        update={"provider_mappings": [*existing, mapping]}
    )
    payload = request.model_dump(mode="python")
    payload.update({"voice_profile": profile, "provider_mapping": mapping})
    return SpeechGenerationRequest.model_validate(payload)


def _style_instructions(request: SpeechGenerationRequest) -> str:
    parts = [
        "Speak exactly the supplied input text without adding, removing, or rewriting words."
    ]
    creative = request.voice_profile.creative_profile.model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    parts.append(
        "Maintain these stable base-voice characteristics across scenes: "
        f"{json.dumps(creative, ensure_ascii=False, sort_keys=True)}."
    )
    if request.scene_state:
        scene_state = request.scene_state.model_dump(
            mode="json", by_alias=True, exclude_none=True
        )
        parts.append(
            "Treat this scene state as temporary and do not turn it into a permanent "
            f"voice trait: {json.dumps(scene_state, ensure_ascii=False, sort_keys=True)}."
        )
    if request.performance_intent:
        parts.append(
            "For this line only, apply these performance changes relative to the base "
            "voice without changing identity: "
            f"{json.dumps(request.performance_intent, ensure_ascii=False, sort_keys=True)}."
        )
    for guidance in request.pronunciation_guidance:
        parts.append(
            f"Reviewed pronunciation: {guidance.term} should be read as "
            f"{guidance.reviewed_reading}."
        )
    return " ".join(parts)


def compile_openai_speech_payload(request: SpeechGenerationRequest) -> dict[str, Any]:
    mapping = request.provider_mapping
    if mapping is None:
        raise SpeechProviderError("OpenAI adapter requires a resolved provider mapping")
    if mapping.provider.lower() != "openai":
        raise SpeechProviderError("OpenAI adapter requires provider mapping 'openai'")
    parameters = {**mapping.material_parameters, **request.material_render_parameters}
    response_format = str(parameters.get("response_format", "wav")).lower()
    if response_format not in _MIME_BY_FORMAT:
        raise SpeechProviderError("Unsupported OpenAI speech response format")
    payload: dict[str, Any] = {
        "model": mapping.model,
        "input": request.exact_text,
        "voice": mapping.voice_id,
        "response_format": response_format,
        "instructions": _style_instructions(request),
    }
    if "speed" in parameters:
        speed = float(parameters["speed"])
        if not 0.25 <= speed <= 4.0:
            raise SpeechProviderError("OpenAI speech speed must be between 0.25 and 4.0")
        payload["speed"] = speed
    return payload


class OpenAiSpeechProvider:
    """Single HTTP-backed real TTS adapter; never owns Dialogue or Media state."""

    def __init__(
        self,
        config: SpeechServiceConfig,
        output_directory: Path,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if config.api_key is None or not config.api_key.get_secret_value().strip():
            raise SpeechProviderError("OpenAI speech provider credential is missing")
        self.config = config
        self.output_directory = output_directory.resolve()
        self._owns_client = client is None
        self._authorization = f"Bearer {config.api_key.get_secret_value()}"
        self.client = client or httpx.AsyncClient(
            base_url=f"{config.base_url.rstrip('/')}/",
            timeout=config.timeout_seconds,
        )

    def resolve_request(
        self, request: SpeechGenerationRequest
    ) -> SpeechGenerationRequest:
        mapping = request.provider_mapping
        if mapping is None:
            mapping = _resolve_openai_mapping(request)
        if mapping.provider.lower() != "openai":
            raise SpeechProviderError("OpenAI adapter requires provider mapping 'openai'")
        return _bind_mapping(request, mapping)

    async def generate_speech(
        self, request: SpeechGenerationRequest
    ) -> SpeechGenerationResult:
        request = self.resolve_request(request)
        payload = compile_openai_speech_payload(request)
        mapping = request.provider_mapping
        if mapping is None:  # pragma: no cover - guaranteed by resolve_request
            raise SpeechProviderError("OpenAI adapter requires a resolved provider mapping")
        response_format = str(payload["response_format"])
        calls = 0
        retries = 0
        response: httpx.Response | None = None
        for retry_index in range(self.config.max_transient_retries + 1):
            calls += 1
            try:
                response = await self.client.post(
                    "audio/speech",
                    json=payload,
                    headers={
                        "Authorization": self._authorization,
                        "Content-Type": "application/json",
                    },
                )
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                if retry_index >= self.config.max_transient_retries:
                    raise SpeechProviderError(
                        "OpenAI speech connection failed before a confirmed result",
                        retryable=True,
                    ) from exc
                retries += 1
                continue
            except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
                raise ProviderResultUnknown(
                    "OpenAI speech result is unknown after an ambiguous timeout"
                ) from exc

            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if retry_index < self.config.max_transient_retries:
                    retries += 1
                    continue
                raise SpeechProviderError(
                    "OpenAI speech provider exhausted retryable responses",
                    status_code=response.status_code,
                    retryable=True,
                )
            if response.is_error:
                raise SpeechProviderError(
                    "OpenAI speech provider rejected the request",
                    status_code=response.status_code,
                )
            break

        if response is None or not response.content:
            raise SpeechProviderError("OpenAI speech provider returned empty audio")
        mime_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        expected_mime = _MIME_BY_FORMAT[response_format].lower()
        if not mime_type.startswith("audio/"):
            raise SpeechProviderError("OpenAI speech provider returned non-audio content")
        if response_format != "pcm" and mime_type != expected_mime:
            raise SpeechProviderError("OpenAI speech response MIME does not match requested format")

        self.output_directory.mkdir(parents=True, exist_ok=True)
        attempt_id = uuid.uuid4().hex
        fingerprint = audio_input_fingerprint(request)
        output = self.output_directory / (
            f"speech-{fingerprint}-{attempt_id}{_EXTENSION_BY_FORMAT[response_format]}"
        )
        output.write_bytes(response.content)
        request_id = response.headers.get("x-request-id")
        metadata: dict[str, Any] = {
            "provider": "openai",
            "model": mapping.model,
            "voiceId": mapping.voice_id,
            "attemptId": attempt_id,
            "callCount": calls,
            "retryCount": retries,
            "responseFormat": response_format,
            "responseBytes": len(response.content),
            "responseSha256": hashlib.sha256(response.content).hexdigest(),
            "providerRequestFingerprint": hashlib.sha256(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        }
        if request_id:
            metadata["providerRequestId"] = request_id
        return SpeechGenerationResult(
            source_uri=output.as_uri(),
            mime_type=mime_type,
            provider_metadata=metadata,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()
