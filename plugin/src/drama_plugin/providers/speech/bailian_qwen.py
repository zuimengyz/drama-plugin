from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from drama_plugin.audio.foundation import (
    audio_input_fingerprint,
    voice_profile_fingerprint,
)
from drama_plugin.config.models import SpeechServiceConfig
from drama_plugin.contracts.audio import (
    ProviderMappingStatus,
    ProviderVoiceMapping,
    SpeechGenerationRequest,
    SpeechGenerationResult,
)
from drama_plugin.exceptions import (
    ProviderResultUnknown,
    SpeechProviderError,
    SpeechRejectionReason,
)
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
_QWEN_AUDIO_TTS_MODELS = {
    "qwen-audio-3.0-tts-plus",
    "qwen-audio-3.0-tts-flash",
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
_MAX_INSTRUCTION_CHARACTERS = 2048
VOICE_DESIGN_PROMPT_LIMIT = 500
VOICE_DESIGN_PREVIEW_MIN_CHARACTERS = 15
VOICE_DESIGN_PREVIEW_MAX_CHARACTERS = 200
QWEN_AUDIO_INSTRUCTION_LIMIT = 128
VoiceModelFamily = Literal["QWEN3_TTS", "QWEN_AUDIO_TTS"]
VoiceModelCompatibility = Literal["COMPATIBLE", "INCOMPATIBLE", "UNKNOWN"]
_MANAGED_CANDIDATE_VOICES = frozenset(
    {"Ethan", "Moon", "Eldric Sage", "Neil", "Kai", "Cherry", "Serena", "Maia"}
)
_MODEL_COMPATIBLE_MANAGED_VOICES = {
    "qwen3-tts-instruct-flash": _MANAGED_CANDIDATE_VOICES,
    "qwen3-tts-instruct-flash-2026-01-26": _MANAGED_CANDIDATE_VOICES,
    "qwen3-tts-flash": _MANAGED_CANDIDATE_VOICES,
    "qwen3-tts-flash-2025-11-27": _MANAGED_CANDIDATE_VOICES,
    # Of the repository-managed candidates, the official legacy snapshot list
    # contains only Cherry and Ethan.
    "qwen3-tts-flash-2025-09-18": frozenset({"Cherry", "Ethan"}),
}
_DIAGNOSTIC_URL = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_DIAGNOSTIC_BEARER = re.compile(r"\bBearer\s+[^\s,;]+", re.IGNORECASE)
_DIAGNOSTIC_API_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}")
_DIAGNOSTIC_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(authorization|api[_ -]?key|access[_ -]?token|cookie|credential)"
    r"\s*[:=]\s*([^\s,;]+)"
)
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


class VoiceDesignSpec(BaseModel):
    """Provider-facing projection of one existing stable creative voice profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_model: str
    voice_prompt: str = Field(min_length=1, max_length=VOICE_DESIGN_PROMPT_LIMIT)
    preview_text: str = Field(
        min_length=VOICE_DESIGN_PREVIEW_MIN_CHARACTERS,
        max_length=VOICE_DESIGN_PREVIEW_MAX_CHARACTERS,
    )
    prefix: str = Field(pattern=r"^[A-Za-z0-9]{1,10}$")
    language_hints: tuple[Literal["zh", "en"], ...] = ("zh",)
    sample_rate: Literal[16000, 24000, 48000] = 24000
    response_format: Literal["pcm", "wav", "mp3"] = "wav"

    @model_validator(mode="after")
    def validate_qwen_audio_target(self) -> "VoiceDesignSpec":
        if self.target_model not in _QWEN_AUDIO_TTS_MODELS:
            raise ValueError("Voice Design targetModel must be Qwen-Audio TTS")
        if len(self.language_hints) != 1:
            raise ValueError("Voice Design accepts exactly one language hint")
        return self


class VoiceDesignResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    voice_id: str
    target_model: str
    status: Literal["OK"]
    preview_source_uri: str
    preview_mime_type: str
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


def bailian_qwen_voice_compatibility(
    model: str, voice_id: str
) -> VoiceModelCompatibility:
    """Return compatibility only when repository capability evidence is explicit."""

    compatible = _MODEL_COMPATIBLE_MANAGED_VOICES.get(model)
    if compatible is None or voice_id not in _MANAGED_CANDIDATE_VOICES:
        return "UNKNOWN"
    return "COMPATIBLE" if voice_id in compatible else "INCOMPATIBLE"


def bailian_qwen_model_family(model: str) -> VoiceModelFamily:
    if model in _INSTRUCT_MODELS | _FLASH_MODELS:
        return "QWEN3_TTS"
    if model in _QWEN_AUDIO_TTS_MODELS:
        return "QWEN_AUDIO_TTS"
    raise SpeechProviderError(
        "Unsupported Bailian Qwen speech model",
        provider_error_code="LOCAL_UNSUPPORTED_MODEL_FAMILY",
        rejection_reason="UNSUPPORTED_PARAMETER",
    )


def _safe_diagnostic_text(value: Any, *, limit: int = 500) -> str | None:
    if not isinstance(value, str):
        return None
    rendered = " ".join(value.replace("\x00", " ").split())
    if not rendered:
        return None
    rendered = _DIAGNOSTIC_URL.sub("[REDACTED_URL]", rendered)
    rendered = _DIAGNOSTIC_BEARER.sub("Bearer [REDACTED]", rendered)
    rendered = _DIAGNOSTIC_API_KEY.sub("[REDACTED_API_KEY]", rendered)
    rendered = _DIAGNOSTIC_SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}=[REDACTED]", rendered
    )
    return rendered[:limit]


def _safe_diagnostic_identifier(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    rendered = value.strip()
    if not rendered or len(rendered) > 200:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", rendered):
        return None
    return rendered


def _rejection_reason(
    status_code: int,
    provider_error_code: str | None,
    provider_error_message: str | None,
) -> SpeechRejectionReason:
    material = f"{provider_error_code or ''} {provider_error_message or ''}".lower()
    if any(
        marker in material
        for marker in (
            "voice/model",
            "model/voice",
            "voice is invalid",
            "invalid voice",
            "voice not available",
            "voice unsupported",
            "unsupported voice",
            "error code: 418",
            "engine error [418]",
        )
    ):
        return "VOICE_MODEL_INCOMPATIBLE"
    if status_code == 402 or any(
        marker in material
        for marker in ("arrearage", "quota", "insufficient balance", "out_of_service")
    ):
        return "QUOTA_OR_ACCOUNT"
    if status_code in {401, 403} or any(
        marker in material
        for marker in (
            "invalidapikey",
            "invalid_api_key",
            "accessdenied",
            "access_denied",
            "permission",
            "unauthorized",
        )
    ):
        return "AUTH_OR_PERMISSION"
    if any(
        marker in material
        for marker in ("datainspection", "content rejected", "content policy", "riskcontrol")
    ):
        return "CONTENT_REJECTED"
    if "unsupported parameter" in material or (
        "parameter" in material and "not supported" in material
    ):
        return "UNSUPPORTED_PARAMETER"
    if any(
        marker in material
        for marker in (
            "invalidparameter",
            "invalid_parameter",
            "required parameter",
            "input length",
            "range of input",
        )
    ):
        return "INVALID_REQUEST"
    return "UNKNOWN_REJECTION"


def _bailian_rejection_diagnostics(response: httpx.Response) -> dict[str, Any]:
    provider_error_code: str | None = None
    provider_error_message: str | None = None
    provider_request_id: str | None = None
    try:
        body = response.json()
    except (ValueError, json.JSONDecodeError):
        body = None
    if isinstance(body, dict):
        raw_code = body.get("code")
        if isinstance(raw_code, str | int):
            provider_error_code = _safe_diagnostic_identifier(str(raw_code))
        provider_error_message = _safe_diagnostic_text(body.get("message"))
        provider_request_id = _safe_diagnostic_identifier(
            body.get("request_id") or body.get("requestId")
        )
    if provider_request_id is None:
        provider_request_id = _safe_diagnostic_identifier(
            response.headers.get("x-dashscope-request-id")
            or response.headers.get("x-request-id")
        )
    return {
        "provider_error_code": provider_error_code,
        "provider_error_message": provider_error_message,
        "provider_request_id": provider_request_id,
        "rejection_reason": _rejection_reason(
            response.status_code, provider_error_code, provider_error_message
        ),
    }


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


def _meaningful_semantic_value(value: Any) -> Any:
    if value is None or value == "UNKNOWN" or value == [] or value == {}:
        return None
    if isinstance(value, dict):
        compact = {
            key: selected
            for key, item in value.items()
            if key not in {"confidence", "evidenceRefs", "unknownFields"}
            and (selected := _meaningful_semantic_value(item)) is not None
        }
        return compact or None
    if isinstance(value, list):
        compact_list = [
            selected
            for item in value
            if (selected := _meaningful_semantic_value(item)) is not None
        ]
        return compact_list or None
    return value


def _compact_base_voice(request: SpeechGenerationRequest) -> dict[str, Any]:
    creative = request.voice_profile.creative_profile.model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    selected_keys = (
        "vocalAge",
        "vocalWeight",
        "resonanceDepth",
        "timbreBrightness",
        "articulationFirmness",
        "phraseAttack",
        "baselinePace",
        "baselineEnergy",
        "breathSupport",
        "commandPresence",
        "gravitas",
        "controlledPower",
        "sentenceFinality",
        "emotionalContainment",
        "consistencyNotes",
    )
    return {
        key: compact
        for key in selected_keys
        if (compact := _meaningful_semantic_value(creative.get(key))) is not None
    }


def compile_voice_design_spec(
    request: SpeechGenerationRequest, *, preview_text: str
) -> VoiceDesignSpec:
    """Project only stable voice identity into the bounded Voice Design contract."""

    mapping = request.provider_mapping
    if mapping is None or mapping.provider.lower() != "bailian_qwen":
        raise SpeechProviderError(
            "Voice Design requires a Bailian provider mapping",
            provider_error_code="LOCAL_VOICE_DESIGN_MAPPING_REQUIRED",
            rejection_reason="INVALID_REQUEST",
        )
    if bailian_qwen_model_family(mapping.model) != "QWEN_AUDIO_TTS":
        raise SpeechProviderError(
            "Voice Design requires a Qwen-Audio TTS target model",
            provider_error_code="LOCAL_VOICE_DESIGN_TARGET_INVALID",
            rejection_reason="INVALID_REQUEST",
        )
    stable_voice = _compact_base_voice(request)
    if not stable_voice:
        raise SpeechProviderError(
            "Stable Voice Profile has no usable Voice Design attributes",
            provider_error_code="LOCAL_VOICE_DESIGN_PROFILE_EMPTY",
            rejection_reason="INVALID_REQUEST",
        )
    voice_prompt = (
        "请设计长期稳定的角色基础声线。只依据以下已有稳定声音属性，不加入场景情绪、"
        "本句动作、人物姓名或价值评价："
        f"{_compact_json(stable_voice)}。保持声音身份跨句一致。"
    )
    if len(voice_prompt) > VOICE_DESIGN_PROMPT_LIMIT:
        raise SpeechProviderError(
            "Voice Design prompt exceeds the local provider limit",
            provider_error_code="LOCAL_VOICE_DESIGN_PROMPT_LENGTH_GUARD",
            rejection_reason="INVALID_REQUEST",
        )
    language = request.voice_profile.creative_profile.language.lower()
    language_hint: Literal["zh", "en"]
    if language.startswith("zh"):
        language_hint = "zh"
    elif language.startswith("en"):
        language_hint = "en"
    else:
        raise SpeechProviderError(
            "Voice Design preview language is unsupported",
            provider_error_code="LOCAL_VOICE_DESIGN_LANGUAGE_UNSUPPORTED",
            rejection_reason="UNSUPPORTED_PARAMETER",
        )
    prefix = "vd" + voice_profile_fingerprint(request.voice_profile)[:8]
    try:
        return VoiceDesignSpec(
            target_model=mapping.model,
            voice_prompt=voice_prompt,
            preview_text=preview_text,
            prefix=prefix,
            language_hints=(language_hint,),
        )
    except ValueError as exc:
        raise SpeechProviderError(
            "Voice Design spec failed local validation",
            provider_error_code="LOCAL_VOICE_DESIGN_SPEC_INVALID",
            rejection_reason="INVALID_REQUEST",
        ) from exc


def voice_design_fingerprint(spec: VoiceDesignSpec) -> str:
    return hashlib.sha256(
        _compact_json(spec.model_dump(mode="json")).encode("utf-8")
    ).hexdigest()


def compile_bailian_voice_design_payload(
    spec: VoiceDesignSpec,
) -> dict[str, Any]:
    return {
        "model": "voice-enrollment",
        "input": {
            "action": "create_voice",
            "target_model": spec.target_model,
            "voice_prompt": spec.voice_prompt,
            "preview_text": spec.preview_text,
            "prefix": spec.prefix,
            "language_hints": list(spec.language_hints),
        },
        "parameters": {
            "sample_rate": spec.sample_rate,
            "response_format": spec.response_format,
        },
    }


def _compact_scene_state(request: SpeechGenerationRequest) -> dict[str, Any]:
    if request.scene_state is None:
        return {}
    state = request.scene_state.model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    selected_keys = (
        "currentEmotion",
        "internalActivation",
        "externalExpressiveness",
        "urgency",
        "stressLevel",
        "restraint",
        "physicalCondition",
        "presentationMode",
    )
    compact: dict[str, Any] = {}
    for key in selected_keys:
        raw = state.get(key)
        value = raw.get("value") if isinstance(raw, dict) else raw
        selected = _meaningful_semantic_value(value)
        if selected is not None:
            compact[key] = selected
    return compact


def _compact_line_performance(request: SpeechGenerationRequest) -> dict[str, Any]:
    selected_keys = (
        "baseline",
        "sceneDelta",
        "delivery",
        "pace",
        "speakerObjective",
        "subtext",
        "performanceBoundary",
    )
    return {
        key: compact
        for key in selected_keys
        if (
            compact := _meaningful_semantic_value(
                request.performance_intent.get(key)
            )
        )
        is not None
    }


def _qwen_audio_instruction(request: SpeechGenerationRequest) -> str:
    """Compile line performance only; the custom voice owns stable identity."""

    translations = {
        "HIGH": "高",
        "VERY_HIGH": "极高",
        "MEDIUM_HIGH": "中高",
        "MEDIUM": "中",
        "LOW": "低",
        "SLIGHTLY_FASTER_NOT_RUSHED": "稍快但不仓促",
        "SLIGHTLY_SLOWER_NOT_DRAWN_OUT": "稍慢但不拖沓",
        "LOWER_WITHOUT_WEAKNESS": "降低但不显软弱",
        "OPEN_FOR_SUPERIOR_DECISION": "为上级决断留余地",
        "CURRENT_ILLNESS_BURDEN_WITHOUT_AUTHORITY_REDUCTION": (
            "有病体负担但不削弱控制力"
        ),
    }

    def rendered(value: Any) -> str | None:
        if not isinstance(value, str) or not value or value == "UNKNOWN":
            return None
        return translations.get(value, value)

    state = request.scene_state
    performance = request.performance_intent
    baseline = performance.get("baseline", {})
    delta = performance.get("sceneDelta", {})
    candidates: list[str] = []
    if state is not None:
        for label, dimension in (
            ("情绪", state.current_emotion),
            ("内在", state.internal_activation),
            ("外显", state.external_expressiveness),
            ("克制", state.restraint),
            ("紧迫", state.urgency),
            ("身体", state.physical_condition),
        ):
            value = rendered(dimension.value if dimension is not None else None)
            if value:
                candidates.append(f"{label}{value}")
    if isinstance(delta, dict):
        for label, key in (
            ("节奏", "paceAdjustment"),
            ("音量", "volumeAdjustment"),
        ):
            value = rendered(delta.get(key))
            if value:
                candidates.append(f"{label}{value}")
        pause_plan = delta.get("pausePlan")
        if isinstance(pause_plan, list) and pause_plan:
            candidates.append("停顿" + "、".join(map(str, pause_plan)))
        emphasis = delta.get("emphasis")
        if isinstance(emphasis, list) and emphasis:
            candidates.append("强调" + "、".join(map(str, emphasis)))
    if request.pronunciation_guidance:
        candidates.append(
            "发音"
            + "、".join(
                f"{item.term}={item.reviewed_reading}"
                for item in request.pronunciation_guidance
            )
        )
    if isinstance(baseline, dict):
        raw_finality = baseline.get("sentenceFinality")
        finality = (
            "坚定收束" if raw_finality == "HIGH" else rendered(raw_finality)
        )
        if finality:
            candidates.append(f"收句{finality}")
    boundaries = performance.get("performanceBoundary")
    if isinstance(boundaries, list) and boundaries:
        candidates.append("边界" + "、".join(map(str, boundaries)))
    objective = rendered(performance.get("speakerObjective"))
    if objective:
        candidates.append(f"目的{objective}")
    subtext = rendered(performance.get("subtext"))
    if subtext:
        candidates.append(f"潜台词{subtext}")

    parts = ["逐字朗读，不增删改写"]
    for candidate in candidates:
        proposed = "；".join([*parts, candidate]) + "。"
        if len(proposed) <= QWEN_AUDIO_INSTRUCTION_LIMIT:
            parts.append(candidate)
    instruction = "；".join(parts) + "。"
    if len(instruction) > QWEN_AUDIO_INSTRUCTION_LIMIT:  # pragma: no cover
        raise SpeechProviderError(
            "Qwen-Audio instruction exceeds the observed provider limit",
            provider_error_code="LOCAL_QWEN_AUDIO_INSTRUCTION_LENGTH_GUARD",
            rejection_reason="INVALID_REQUEST",
        )
    return instruction


def _qwen_instructions(request: SpeechGenerationRequest) -> str:
    """Compress rich upstream semantics into bounded provider voice controls."""

    mapping = request.provider_mapping
    if mapping is None:
        raise SpeechProviderError(
            "Bailian Qwen adapter requires a resolved provider mapping"
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
        f"{_compact_json(_compact_base_voice(request))}。",
    ]
    scene_state = _compact_scene_state(request)
    if scene_state:
        sections.append(
            "当前场景状态（仅作用于本句，不固化为人物长期声音）："
            f"{_compact_json(scene_state)}。"
        )
    line_performance = _compact_line_performance(request)
    if line_performance:
        sections.append(
            "本句表演变化（相对长期基础声音调整，不改变角色身份）："
            f"{_compact_json(line_performance)}。"
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
    family = bailian_qwen_model_family(mapping.model)
    if family == "QWEN_AUDIO_TTS":
        metadata = mapping.non_material_metadata
        if (
            metadata.get("voiceDesignTargetModel") != mapping.model
            or metadata.get("voiceDesignStatus") != "OK"
            or not isinstance(metadata.get("voiceDesignFingerprint"), str)
            or not isinstance(metadata.get("voicePromptHash"), str)
        ):
            raise SpeechProviderError(
                "Qwen-Audio custom voice lacks verified Voice Design provenance",
                provider_error_code="LOCAL_VOICE_DESIGN_PROVENANCE_INVALID",
                rejection_reason="INVALID_REQUEST",
            )
        parameters = {
            **mapping.material_parameters,
            **request.material_render_parameters,
        }
        audio_format = str(parameters.get("format", "wav"))
        sample_rate = parameters.get("sample_rate", 24000)
        language_hints = parameters.get("language_hints", ["zh"])
        if audio_format not in {"mp3", "pcm", "wav", "opus"}:
            raise SpeechProviderError(
                "Qwen-Audio output format is unsupported",
                provider_error_code="LOCAL_QWEN_AUDIO_FORMAT_INVALID",
                rejection_reason="UNSUPPORTED_PARAMETER",
            )
        if sample_rate not in {8000, 16000, 22050, 24000, 44100, 48000}:
            raise SpeechProviderError(
                "Qwen-Audio sample rate is unsupported",
                provider_error_code="LOCAL_QWEN_AUDIO_SAMPLE_RATE_INVALID",
                rejection_reason="UNSUPPORTED_PARAMETER",
            )
        if (
            not isinstance(language_hints, list)
            or len(language_hints) != 1
            or language_hints[0] not in {"zh", "en"}
        ):
            raise SpeechProviderError(
                "Qwen-Audio language hints are invalid",
                provider_error_code="LOCAL_QWEN_AUDIO_LANGUAGE_INVALID",
                rejection_reason="UNSUPPORTED_PARAMETER",
            )
        return {
            "model": mapping.model,
            "input": {
                "text": request.exact_text,
                "voice": mapping.voice_id,
                "instruction": _qwen_audio_instruction(request),
                "format": audio_format,
                "sample_rate": sample_rate,
                "language_hints": language_hints,
            },
        }

    compatibility = bailian_qwen_voice_compatibility(
        mapping.model, mapping.voice_id
    )
    if compatibility != "COMPATIBLE":
        reason: SpeechRejectionReason = (
            "VOICE_MODEL_INCOMPATIBLE"
            if compatibility == "INCOMPATIBLE"
            else "UNKNOWN_REJECTION"
        )
        raise SpeechProviderError(
            "Bailian Qwen voice/model compatibility preflight failed",
            provider_error_code="LOCAL_VOICE_MODEL_COMPATIBILITY_PREFLIGHT",
            rejection_reason=reason,
        )
    parameters = {**mapping.material_parameters, **request.material_render_parameters}
    language_type = str(parameters.get("language_type", "Chinese"))
    input_payload: dict[str, Any] = {
        "text": request.exact_text,
        "voice": mapping.voice_id,
        "language_type": language_type,
    }
    if mapping.model in _INSTRUCT_MODELS:
        instructions = _qwen_instructions(request)
        if len(instructions) > _MAX_INSTRUCTION_CHARACTERS:
            raise SpeechProviderError(
                "Bailian Qwen instruction exceeds the local provider limit",
                provider_error_code="LOCAL_INSTRUCTION_LENGTH_GUARD",
                rejection_reason="INVALID_REQUEST",
            )
        input_payload["instructions"] = instructions
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

    _QWEN3_GENERATION_PATH = "services/aigc/multimodal-generation/generation"
    _QWEN_AUDIO_SYNTHESIS_PATH = "services/audio/tts/SpeechSynthesizer"
    _VOICE_DESIGN_PATH = "services/audio/tts/customization"

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

    async def _submit(
        self, path: str, payload: dict[str, Any]
    ) -> tuple[httpx.Response, int, int]:
        calls = 0
        retries = 0
        for retry_index in range(self.config.max_transient_retries + 1):
            calls += 1
            try:
                response = await self.client.post(
                    path,
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
                diagnostics = _bailian_rejection_diagnostics(response)
                raise SpeechProviderError(
                    "Bailian speech provider rejected the request",
                    status_code=response.status_code,
                    **diagnostics,
                )
            return response, calls, retries
        raise SpeechProviderError("Bailian speech provider returned no result")

    async def _submit_voice_design_once(
        self, payload: dict[str, Any]
    ) -> httpx.Response:
        """Submit non-idempotent create_voice once; uncertainty forbids resubmission."""

        try:
            response = await self.client.post(
                self._VOICE_DESIGN_PATH,
                json=payload,
                headers={
                    "Authorization": self._authorization,
                    "Content-Type": "application/json",
                },
            )
        except (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
        ) as exc:
            raise ProviderResultUnknown(
                "Bailian Voice Design result is unknown; create_voice must not be repeated"
            ) from exc
        if response.status_code == 429 or 500 <= response.status_code <= 599:
            raise SpeechProviderError(
                "Bailian Voice Design returned an explicit transient response",
                status_code=response.status_code,
                retryable=True,
            )
        if response.is_error:
            diagnostics = _bailian_rejection_diagnostics(response)
            raise SpeechProviderError(
                "Bailian Voice Design rejected the request",
                status_code=response.status_code,
                **diagnostics,
            )
        return response

    @staticmethod
    def _json_object(response: httpx.Response, operation: str) -> dict[str, Any]:
        try:
            body = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise SpeechProviderError(
                f"Bailian {operation} returned invalid JSON"
            ) from exc
        if not isinstance(body, dict):
            raise SpeechProviderError(f"Bailian {operation} returned invalid JSON")
        return body

    def _validate_qwen_audio_region(self) -> None:
        host = (urlparse(self.config.bailian_base_url).hostname or "").lower()
        if host == "dashscope.aliyuncs.com" or host.endswith(
            ".cn-beijing.maas.aliyuncs.com"
        ):
            return
        raise SpeechProviderError(
            "Qwen-Audio Voice Design requires a China Beijing Bailian endpoint",
            provider_error_code="LOCAL_QWEN_AUDIO_REGION_INVALID",
            rejection_reason="AUTH_OR_PERMISSION",
        )

    async def verify_voice(
        self,
        voice_id: str,
        target_model: str,
        *,
        max_status_queries: int = 3,
        status_poll_interval_seconds: float = 2.0,
    ) -> dict[str, Any]:
        """Read-only bounded verification for a created custom voice."""

        self._validate_qwen_audio_region()
        if max_status_queries < 1 or max_status_queries > 5:
            raise SpeechProviderError(
                "Voice Design status query bound is invalid",
                provider_error_code="LOCAL_VOICE_DESIGN_QUERY_BOUND_INVALID",
                rejection_reason="INVALID_REQUEST",
            )
        status = ""
        status_request_id: str | None = None
        status_query_calls = 0
        status_query_retries = 0
        for query_index in range(max_status_queries):
            query_payload = {
                "model": "voice-enrollment",
                "input": {"action": "query_voice", "voice_id": voice_id},
            }
            query_response, calls, retries = await self._submit(
                self._VOICE_DESIGN_PATH, query_payload
            )
            status_query_calls += calls
            status_query_retries += retries
            query_body = self._json_object(query_response, "Voice Design status")
            query_output = query_body.get("output")
            if not isinstance(query_output, dict):
                raise SpeechProviderError(
                    "Bailian Voice Design status response has no output"
                )
            status_request_id = _safe_diagnostic_identifier(
                query_body.get("request_id")
            )
            if query_output.get("voice_id") != voice_id:
                raise SpeechProviderError(
                    "Bailian Voice Design status returned another voice"
                )
            if query_output.get("target_model") != target_model:
                raise SpeechProviderError(
                    "Bailian Voice Design status target model mismatch",
                    provider_error_code="VOICE_DESIGN_TARGET_MODEL_MISMATCH",
                    rejection_reason="INVALID_REQUEST",
                )
            status = str(query_output.get("status", ""))
            if status == "OK":
                return {
                    "status": status,
                    "voiceStatusRequestId": status_request_id,
                    "voiceStatusQueryCallCount": status_query_calls,
                    "voiceStatusQueryRetryCount": status_query_retries,
                }
            if status == "UNDEPLOYED":
                raise SpeechProviderError(
                    "Bailian Voice Design was not deployed",
                    provider_error_code="VOICE_DESIGN_UNDEPLOYED",
                    rejection_reason="UNKNOWN_REJECTION",
                )
            if status != "DEPLOYING":
                raise SpeechProviderError(
                    "Bailian Voice Design returned an unknown status"
                )
            if query_index + 1 < max_status_queries:
                await asyncio.sleep(status_poll_interval_seconds)
        raise SpeechProviderError(
            "Bailian Voice Design status remained pending",
            provider_error_code="VOICE_DESIGN_STATUS_PENDING",
            retryable=True,
        )

    async def design_voice(
        self,
        spec: VoiceDesignSpec,
        *,
        max_status_queries: int = 3,
        status_poll_interval_seconds: float = 2.0,
    ) -> VoiceDesignResult:
        """Create one custom voice and verify its bounded deployment lifecycle."""

        self._validate_qwen_audio_region()
        if max_status_queries < 1 or max_status_queries > 5:
            raise SpeechProviderError(
                "Voice Design status query bound is invalid",
                provider_error_code="LOCAL_VOICE_DESIGN_QUERY_BOUND_INVALID",
                rejection_reason="INVALID_REQUEST",
            )
        payload = compile_bailian_voice_design_payload(spec)
        response = await self._submit_voice_design_once(payload)
        body = self._json_object(response, "Voice Design")
        output = body.get("output")
        if not isinstance(output, dict):
            raise SpeechProviderError("Bailian Voice Design response has no output")
        voice_id = _safe_diagnostic_identifier(output.get("voice_id"))
        target_model = output.get("target_model")
        preview_audio = output.get("preview_audio")
        request_id = _safe_diagnostic_identifier(body.get("request_id"))
        if voice_id is None:
            raise SpeechProviderError("Bailian Voice Design response has no voice ID")
        if target_model is not None and target_model != spec.target_model:
            raise SpeechProviderError(
                "Bailian Voice Design target model mismatch",
                provider_error_code="VOICE_DESIGN_TARGET_MODEL_MISMATCH",
                rejection_reason="INVALID_REQUEST",
            )
        if not isinstance(preview_audio, dict):
            raise SpeechProviderError(
                "Bailian Voice Design response has no preview audio"
            )
        encoded = preview_audio.get("data")
        response_format = preview_audio.get("response_format")
        sample_rate = preview_audio.get("sample_rate")
        if not isinstance(encoded, str) or not encoded:
            raise SpeechProviderError("Bailian Voice Design preview audio is empty")
        if response_format != spec.response_format or sample_rate != spec.sample_rate:
            raise SpeechProviderError(
                "Bailian Voice Design preview format mismatch",
                provider_error_code="VOICE_DESIGN_PREVIEW_FORMAT_MISMATCH",
                rejection_reason="INVALID_REQUEST",
            )
        try:
            preview_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise SpeechProviderError(
                "Bailian Voice Design preview audio is invalid"
            ) from exc
        if not preview_bytes:
            raise SpeechProviderError("Bailian Voice Design preview audio is empty")

        verified = await self.verify_voice(
            voice_id,
            spec.target_model,
            max_status_queries=max_status_queries,
            status_poll_interval_seconds=status_poll_interval_seconds,
        )

        self.output_directory.mkdir(parents=True, exist_ok=True)
        fingerprint = voice_design_fingerprint(spec)
        attempt_id = uuid.uuid4().hex
        extension = f".{spec.response_format}"
        preview_path = self.output_directory / (
            f"voice-design-preview-{fingerprint}-{attempt_id}{extension}"
        )
        preview_path.write_bytes(preview_bytes)
        preview_mime = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "pcm": "audio/pcm",
        }[spec.response_format]
        metadata: dict[str, Any] = {
            "provider": "bailian_qwen",
            "voiceDesignModel": "voice-enrollment",
            "voiceDesignFingerprint": fingerprint,
            "voicePromptHash": hashlib.sha256(
                spec.voice_prompt.encode("utf-8")
            ).hexdigest(),
            "providerRequestFingerprint": hashlib.sha256(
                _compact_json(payload).encode("utf-8")
            ).hexdigest(),
            "voiceDesignCallCount": 1,
            "voiceStatusQueryCallCount": verified["voiceStatusQueryCallCount"],
            "voiceStatusQueryRetryCount": verified["voiceStatusQueryRetryCount"],
            "previewBytes": len(preview_bytes),
            "previewSha256": hashlib.sha256(preview_bytes).hexdigest(),
            "sampleRate": spec.sample_rate,
            "responseFormat": spec.response_format,
        }
        if request_id:
            metadata["voiceDesignRequestId"] = request_id
        if verified.get("voiceStatusRequestId"):
            metadata["voiceStatusRequestId"] = verified["voiceStatusRequestId"]
        return VoiceDesignResult(
            voice_id=voice_id,
            target_model=spec.target_model,
            status="OK",
            preview_source_uri=preview_path.as_uri(),
            preview_mime_type=preview_mime,
            provider_metadata=metadata,
        )

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
                diagnostics = _bailian_rejection_diagnostics(response)
                raise SpeechProviderError(
                    "Bailian speech audio download was rejected",
                    status_code=response.status_code,
                    **diagnostics,
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
        family = bailian_qwen_model_family(mapping.model)
        path = (
            self._QWEN_AUDIO_SYNTHESIS_PATH
            if family == "QWEN_AUDIO_TTS"
            else self._QWEN3_GENERATION_PATH
        )
        response, calls, retries = await self._submit(path, payload)
        body = self._json_object(response, "speech provider")
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
