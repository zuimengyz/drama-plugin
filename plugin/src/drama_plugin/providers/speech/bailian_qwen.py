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
from drama_plugin.contracts.audio import (
    ProviderMappingStatus,
    ProviderVoiceMapping,
    SpeechGenerationRequest,
    SpeechGenerationResult,
)
from drama_plugin.exceptions import ProviderResultUnknown, SpeechProviderError
from drama_plugin.providers.speech.casting import (
    VoiceCandidate,
    rank_voice_candidates,
)


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
_DEFAULT_INSTRUCT_MODEL = "qwen3-tts-instruct-flash"
_QWEN_VOICE_CANDIDATES = (
    VoiceCandidate(
        "Ethan",
        frozenset({"masculine"}),
        {
            "vocal_age": 0.35,
            "vocal_weight": 0.45,
            "resonance_depth": 0.4,
            "timbre_brightness": 0.75,
            "articulation_firmness": 0.55,
            "phrase_attack": 0.55,
            "baseline_pace": 0.55,
            "baseline_energy": 0.8,
            "breath_support": 0.65,
            "command_presence": 0.45,
            "gravitas": 0.35,
            "controlled_power": 0.55,
            "sentence_finality": 0.5,
            "emotional_containment": 0.45,
        },
    ),
    VoiceCandidate(
        "Moon",
        frozenset({"masculine"}),
        {
            "vocal_age": 0.5,
            "vocal_weight": 0.65,
            "resonance_depth": 0.6,
            "timbre_brightness": 0.45,
            "articulation_firmness": 0.7,
            "phrase_attack": 0.75,
            "baseline_pace": 0.55,
            "baseline_energy": 0.75,
            "breath_support": 0.75,
            "command_presence": 0.8,
            "gravitas": 0.65,
            "controlled_power": 0.8,
            "sentence_finality": 0.75,
            "emotional_containment": 0.65,
        },
    ),
    VoiceCandidate(
        "Eldric Sage",
        frozenset({"masculine"}),
        {
            "vocal_age": 0.8,
            "vocal_weight": 0.8,
            "resonance_depth": 0.85,
            "timbre_brightness": 0.25,
            "articulation_firmness": 0.75,
            "phrase_attack": 0.65,
            "baseline_pace": 0.5,
            "baseline_energy": 0.55,
            "breath_support": 0.65,
            "command_presence": 0.85,
            "gravitas": 0.9,
            "controlled_power": 0.85,
            "sentence_finality": 0.85,
            "emotional_containment": 0.85,
        },
    ),
    VoiceCandidate(
        "Neil",
        frozenset({"masculine"}),
        {
            "vocal_age": 0.5,
            "vocal_weight": 0.55,
            "resonance_depth": 0.5,
            "timbre_brightness": 0.55,
            "articulation_firmness": 0.9,
            "phrase_attack": 0.6,
            "baseline_pace": 0.55,
            "baseline_energy": 0.5,
            "breath_support": 0.7,
            "command_presence": 0.65,
            "gravitas": 0.7,
            "controlled_power": 0.7,
            "sentence_finality": 0.9,
            "emotional_containment": 0.85,
        },
    ),
    VoiceCandidate(
        "Kai",
        frozenset({"masculine"}),
        {
            "vocal_age": 0.45,
            "vocal_weight": 0.4,
            "resonance_depth": 0.55,
            "timbre_brightness": 0.5,
            "articulation_firmness": 0.5,
            "phrase_attack": 0.35,
            "baseline_pace": 0.5,
            "baseline_energy": 0.35,
            "breath_support": 0.65,
            "command_presence": 0.25,
            "gravitas": 0.5,
            "controlled_power": 0.45,
            "sentence_finality": 0.4,
            "emotional_containment": 0.6,
        },
    ),
    VoiceCandidate(
        "Cherry",
        frozenset({"feminine"}),
        {
            "vocal_age": 0.3,
            "vocal_weight": 0.3,
            "resonance_depth": 0.3,
            "timbre_brightness": 0.85,
            "articulation_firmness": 0.55,
            "phrase_attack": 0.55,
            "baseline_pace": 0.6,
            "baseline_energy": 0.8,
            "breath_support": 0.65,
            "command_presence": 0.4,
            "gravitas": 0.3,
            "controlled_power": 0.5,
            "sentence_finality": 0.5,
            "emotional_containment": 0.4,
        },
    ),
    VoiceCandidate(
        "Serena",
        frozenset({"feminine"}),
        {
            "vocal_age": 0.35,
            "vocal_weight": 0.35,
            "resonance_depth": 0.45,
            "timbre_brightness": 0.55,
            "articulation_firmness": 0.45,
            "phrase_attack": 0.3,
            "baseline_pace": 0.5,
            "baseline_energy": 0.4,
            "breath_support": 0.65,
            "command_presence": 0.3,
            "gravitas": 0.5,
            "controlled_power": 0.45,
            "sentence_finality": 0.45,
            "emotional_containment": 0.7,
        },
    ),
    VoiceCandidate(
        "Maia",
        frozenset({"feminine"}),
        {
            "vocal_age": 0.5,
            "vocal_weight": 0.5,
            "resonance_depth": 0.55,
            "timbre_brightness": 0.5,
            "articulation_firmness": 0.7,
            "phrase_attack": 0.5,
            "baseline_pace": 0.5,
            "baseline_energy": 0.5,
            "breath_support": 0.7,
            "command_presence": 0.65,
            "gravitas": 0.7,
            "controlled_power": 0.7,
            "sentence_finality": 0.75,
            "emotional_containment": 0.75,
        },
    ),
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


def rank_bailian_qwen_voice_candidates(
    request: SpeechGenerationRequest, *, limit: int = 3
) -> list[ProviderVoiceMapping]:
    creative = request.voice_profile.creative_profile
    dimensions = {
        "genderPresentation": creative.gender_presentation,
        "vocalAge": creative.vocal_age,
        "vocalWeight": creative.vocal_weight,
        "resonanceDepth": creative.resonance_depth,
        "timbreBrightness": creative.timbre_brightness,
        "articulationFirmness": creative.articulation_firmness,
        "phraseAttack": creative.phrase_attack,
        "baselinePace": creative.baseline_pace,
        "baselineEnergy": creative.baseline_energy,
        "breathSupport": creative.breath_support,
        "commandPresence": creative.command_presence,
        "gravitas": creative.gravitas,
        "controlledPower": creative.controlled_power,
        "sentenceFinality": creative.sentence_finality,
        "emotionalContainment": creative.emotional_containment,
    }
    ranked = rank_voice_candidates(creative, _QWEN_VOICE_CANDIDATES, limit=limit)
    ranking = [
        {
            "rank": index,
            "voiceId": item.voice_id,
            "score": item.score,
            "comparedDimensions": list(item.compared_dimensions),
        }
        for index, item in enumerate(ranked, start=1)
    ]
    return [
        ProviderVoiceMapping(
            provider="bailian_qwen",
            model=_DEFAULT_INSTRUCT_MODEL,
            voice_id=item.voice_id,
            status=ProviderMappingStatus.CANDIDATE,
            material_parameters={"language_type": "Chinese"},
            non_material_metadata={
                "selectionStrategy": "provider-profile-vector-v1",
                "semanticDimensions": {
                    key: value for key, value in dimensions.items() if value is not None
                },
                "candidateRanking": ranking,
                "selectedRank": index,
                "voiceBindingStatus": "PENDING",
            },
        )
        for index, item in enumerate(ranked, start=1)
    ]


def _resolve_qwen_mapping(request: SpeechGenerationRequest) -> ProviderVoiceMapping:
    return rank_bailian_qwen_voice_candidates(request, limit=3)[0]


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _qwen_instructions(request: SpeechGenerationRequest) -> str:
    """Compile creative controls without copying Dialogue into instructions."""

    mapping = request.provider_mapping
    if mapping is None:
        raise SpeechProviderError(
            "Bailian Qwen adapter requires a resolved provider mapping"
        )
    creative = request.voice_profile.creative_profile.model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    controls = {
        key: value
        for key, value in {
            **mapping.material_parameters,
            **request.material_render_parameters,
        }.items()
        if key not in {"language_type"}
    }
    sections = [
        "严格逐字朗读 input.text，不得增删、改写或补充台词。",
        "长期基础声音（跨场景保持，不因本句临时状态改变角色身份）："
        f"{_compact_json(creative)}。",
    ]
    if request.scene_state:
        scene_state = request.scene_state.model_dump(
            mode="json", by_alias=True, exclude_none=True
        )
        sections.append(
            "当前场景状态（仅作用于本句，不固化为人物长期声音）："
            f"{_compact_json(scene_state)}。"
        )
    if request.performance_intent:
        sections.append(
            "本句表演变化（相对长期基础声音调整，不改变角色身份）："
            f"{_compact_json(request.performance_intent)}。"
        )
    sections.append(
        "不得把高克制解释为低能量，不得把身体负担解释为低控制力，"
        "不得把年龄解释为必然拖慢语速，不得把责任或权力解释为提高音量。"
    )
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
    if mapping is None:
        raise SpeechProviderError(
            "Bailian Qwen adapter requires a resolved provider mapping"
        )
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

    def resolve_request(
        self, request: SpeechGenerationRequest
    ) -> SpeechGenerationRequest:
        mapping = request.provider_mapping
        if mapping is None:
            mapping = _resolve_qwen_mapping(request)
        if mapping.provider.lower() != "bailian_qwen":
            raise SpeechProviderError(
                "Bailian Qwen adapter requires provider mapping 'bailian_qwen'"
            )
        return _bind_mapping(request, mapping)

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
        request = self.resolve_request(request)
        payload = compile_bailian_qwen_speech_payload(request)
        mapping = request.provider_mapping
        if mapping is None:  # pragma: no cover - guaranteed by resolve_request
            raise SpeechProviderError(
                "Bailian Qwen adapter requires a resolved provider mapping"
            )
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
            "model": mapping.model,
            "voiceId": mapping.voice_id,
            "attemptId": attempt_id,
            "callCount": calls,
            "retryCount": retries,
            "downloadCallCount": download_calls,
            "responseBytes": len(downloaded.content),
            "responseSha256": hashlib.sha256(downloaded.content).hexdigest(),
            "providerRequestFingerprint": hashlib.sha256(
                _compact_json(payload).encode("utf-8")
            ).hexdigest(),
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
