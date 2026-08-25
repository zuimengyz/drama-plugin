from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

import httpx

from drama_plugin.audio.foundation import audio_input_fingerprint
from drama_plugin.config.models import SpeechServiceConfig
from drama_plugin.contracts.audio import SpeechGenerationRequest, SpeechGenerationResult
from drama_plugin.exceptions import ProviderResultUnknown, SpeechProviderError


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


def _style_instructions(request: SpeechGenerationRequest) -> str:
    parts = [
        "Speak exactly the supplied input text without adding, removing, or rewriting words."
    ]
    if request.performance_intent:
        material = ", ".join(
            f"{key}={request.performance_intent[key]}"
            for key in sorted(request.performance_intent)
        )
        parts.append(f"Performance intent: {material}.")
    for guidance in request.pronunciation_guidance:
        parts.append(
            f"Reviewed pronunciation: {guidance.term} should be read as "
            f"{guidance.reviewed_reading}."
        )
    return " ".join(parts)


def compile_openai_speech_payload(request: SpeechGenerationRequest) -> dict[str, Any]:
    mapping = request.provider_mapping
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

    async def generate_speech(
        self, request: SpeechGenerationRequest
    ) -> SpeechGenerationResult:
        payload = compile_openai_speech_payload(request)
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
            "model": request.provider_mapping.model,
            "voiceId": request.provider_mapping.voice_id,
            "attemptId": attempt_id,
            "callCount": calls,
            "retryCount": retries,
            "responseFormat": response_format,
            "responseBytes": len(response.content),
            "responseSha256": hashlib.sha256(response.content).hexdigest(),
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
