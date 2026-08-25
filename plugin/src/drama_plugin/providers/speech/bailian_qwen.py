from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from drama_plugin.audio.foundation import audio_input_fingerprint
from drama_plugin.config.models import SpeechServiceConfig
from drama_plugin.contracts.audio import SpeechGenerationRequest, SpeechGenerationResult
from drama_plugin.exceptions import ProviderResultUnknown, SpeechProviderError


_INSTRUCT_MODELS = {
    "qwen3-tts-instruct-flash",
    "qwen3-tts-instruct-flash-2026-01-26",
}
_FLASH_MODELS = {
    "qwen3-tts-flash",
    "qwen3-tts-flash-2025-11-27",
    "qwen3-tts-flash-2025-09-18",
}
_MIME_BY_EXTENSION = {
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
}


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _qwen_instructions(request: SpeechGenerationRequest) -> str:
    """Compile creative controls without copying Dialogue into instructions."""

    creative = request.voice_profile.creative_profile.model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    controls = {
        key: value
        for key, value in {
            **request.provider_mapping.material_parameters,
            **request.material_render_parameters,
        }.items()
        if key not in {"language_type"}
    }
    sections = [
        "严格逐字朗读 input.text，不得增删、改写或补充台词。",
        f"创作声音画像：{_compact_json(creative)}。",
    ]
    if request.performance_intent:
        sections.append(f"表演意图：{_compact_json(request.performance_intent)}。")
    if controls:
        sections.append(f"材质控制：{_compact_json(controls)}。")
    if request.pronunciation_guidance:
        guidance = [
            {
                "term": item.term,
                "language": item.language,
                "reviewedReading": item.reviewed_reading,
            }
            for item in request.pronunciation_guidance
        ]
        sections.append(f"已审核发音：{_compact_json(guidance)}。")
    return "".join(sections)


def compile_bailian_qwen_speech_payload(
    request: SpeechGenerationRequest,
) -> dict[str, Any]:
    mapping = request.provider_mapping
    if mapping.provider.lower() != "bailian_qwen":
        raise SpeechProviderError(
            "Bailian Qwen adapter requires provider mapping 'bailian_qwen'"
        )
    if mapping.model not in _INSTRUCT_MODELS | _FLASH_MODELS:
        raise SpeechProviderError("Unsupported Bailian Qwen speech model")
    parameters = {**mapping.material_parameters, **request.material_render_parameters}
    language_type = str(parameters.get("language_type", "Chinese"))
    input_payload: dict[str, Any] = {
        "text": request.exact_text,
        "voice": mapping.voice_id,
        "language_type": language_type,
    }
    if mapping.model in _INSTRUCT_MODELS:
        input_payload["instructions"] = _qwen_instructions(request)
        # Keep instructions deterministic and auditable for exact-text validation.
        input_payload["optimize_instructions"] = False
    return {"model": mapping.model, "input": input_payload}


def _download_mime(response: httpx.Response, audio_url: str) -> tuple[str, str]:
    mime_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    extension = Path(urlparse(audio_url).path).suffix.lower()
    inferred = _MIME_BY_EXTENSION.get(extension)
    if mime_type.startswith("audio/"):
        return mime_type, extension or ".audio"
    if mime_type in {"", "application/octet-stream", "binary/octet-stream"} and inferred:
        return inferred, extension
    raise SpeechProviderError("Bailian speech download returned non-audio content")


class BailianQwenSpeechProvider:
    """Non-realtime DashScope HTTP adapter with immediate signed-URL download."""

    _GENERATION_PATH = "services/aigc/multimodal-generation/generation"

    def __init__(
        self,
        config: SpeechServiceConfig,
        output_directory: Path,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        credential = config.dashscope_api_key
        if credential is None or not credential.get_secret_value().strip():
            raise SpeechProviderError("Bailian Qwen speech provider credential is missing")
        self.config = config
        self.output_directory = output_directory.resolve()
        self._owns_client = client is None
        self._authorization = f"Bearer {credential.get_secret_value()}"
        self.client = client or httpx.AsyncClient(
            base_url=f"{config.bailian_base_url.rstrip('/')}/",
            timeout=config.timeout_seconds,
        )

    async def _submit(self, payload: dict[str, Any]) -> tuple[httpx.Response, int, int]:
        calls = 0
        retries = 0
        for retry_index in range(self.config.max_transient_retries + 1):
            calls += 1
            try:
                response = await self.client.post(
                    self._GENERATION_PATH,
                    json=payload,
                    headers={
                        "Authorization": self._authorization,
                        "Content-Type": "application/json",
                    },
                )
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                if retry_index >= self.config.max_transient_retries:
                    raise SpeechProviderError(
                        "Bailian speech connection failed before a confirmed result",
                        retryable=True,
                    ) from exc
                retries += 1
                continue
            except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
                raise ProviderResultUnknown(
                    "Bailian speech result is unknown after an ambiguous timeout"
                ) from exc
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if retry_index < self.config.max_transient_retries:
                    retries += 1
                    continue
                raise SpeechProviderError(
                    "Bailian speech provider exhausted retryable responses",
                    status_code=response.status_code,
                    retryable=True,
                )
            if response.is_error:
                raise SpeechProviderError(
                    "Bailian speech provider rejected the request",
                    status_code=response.status_code,
                )
            return response, calls, retries
        raise SpeechProviderError("Bailian speech provider returned no result")

    async def _download(self, audio_url: str, request_id: str | None) -> tuple[httpx.Response, int]:
        parsed = urlparse(audio_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise SpeechProviderError("Bailian speech provider returned an invalid audio URL")
        attempts = 0
        for retry_index in range(self.config.max_transient_retries + 1):
            attempts += 1
            try:
                response = await self.client.get(audio_url)
            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
            ) as exc:
                if retry_index < self.config.max_transient_retries:
                    continue
                suffix = f" after provider request {request_id}" if request_id else ""
                raise SpeechProviderError(
                    f"Bailian speech audio download failed{suffix}", retryable=True
                ) from exc
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if retry_index < self.config.max_transient_retries:
                    continue
                suffix = f" after provider request {request_id}" if request_id else ""
                raise SpeechProviderError(
                    f"Bailian speech audio download exhausted retries{suffix}",
                    status_code=response.status_code,
                    retryable=True,
                )
            if response.is_error:
                raise SpeechProviderError(
                    "Bailian speech audio download was rejected",
                    status_code=response.status_code,
                )
            return response, attempts
        raise SpeechProviderError("Bailian speech audio download returned no result")

    async def generate_speech(
        self, request: SpeechGenerationRequest
    ) -> SpeechGenerationResult:
        payload = compile_bailian_qwen_speech_payload(request)
        response, calls, retries = await self._submit(payload)
        try:
            body = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise SpeechProviderError("Bailian speech provider returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise SpeechProviderError("Bailian speech provider returned invalid JSON")
        request_id = body.get("request_id")
        provider_request_id = str(request_id) if request_id else None
        try:
            audio = body["output"]["audio"]
            audio_url = audio["url"]
        except (KeyError, TypeError) as exc:
            raise SpeechProviderError(
                "Bailian speech provider response has no downloadable audio"
            ) from exc
        if not isinstance(audio_url, str) or not audio_url:
            raise SpeechProviderError(
                "Bailian speech provider response has no downloadable audio"
            )
        downloaded, download_calls = await self._download(audio_url, provider_request_id)
        if not downloaded.content:
            raise SpeechProviderError("Bailian speech provider returned empty audio")
        mime_type, extension = _download_mime(downloaded, audio_url)

        self.output_directory.mkdir(parents=True, exist_ok=True)
        attempt_id = uuid.uuid4().hex
        fingerprint = audio_input_fingerprint(request)
        output = self.output_directory / f"speech-{fingerprint}-{attempt_id}{extension}"
        output.write_bytes(downloaded.content)
        metadata: dict[str, Any] = {
            "provider": "bailian_qwen",
            "model": request.provider_mapping.model,
            "voiceId": request.provider_mapping.voice_id,
            "attemptId": attempt_id,
            "callCount": calls,
            "retryCount": retries,
            "downloadCallCount": download_calls,
            "responseBytes": len(downloaded.content),
            "responseSha256": hashlib.sha256(downloaded.content).hexdigest(),
        }
        if provider_request_id:
            metadata["providerRequestId"] = provider_request_id
        if isinstance(audio, dict) and audio.get("id"):
            metadata["providerAudioId"] = str(audio["id"])
        return SpeechGenerationResult(
            source_uri=output.as_uri(),
            mime_type=mime_type,
            provider_metadata=metadata,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()
