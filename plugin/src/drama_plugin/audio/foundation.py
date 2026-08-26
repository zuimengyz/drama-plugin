from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel

from drama_plugin.contracts.audio import (
    AudioReviewStatus,
    FinalAvFingerprintInput,
    PronunciationGuidance,
    ProviderVoiceMapping,
    SceneState,
    SpeechGenerationRequest,
    TargetTimingPolicy,
    VoiceProfile,
)
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.media import Media
from drama_plugin.providers.base.interfaces import ProductionProvider


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, Enum):
        return value.value
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_canonical(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def text_hash(exact_text: str) -> str:
    return hashlib.sha256(exact_text.encode("utf-8")).hexdigest()


def voice_profile_fingerprint(profile: VoiceProfile) -> str:
    return sha256_canonical(
        {
            "schemaVersion": "voice-creative-profile-v1",
            "speakerKey": profile.speaker_key,
            "creativeProfile": dump_contract(profile.creative_profile),
        }
    )


def provider_mapping_fingerprint(mapping: ProviderVoiceMapping) -> str:
    return sha256_canonical(
        {
            "schemaVersion": "provider-voice-mapping-v1",
            "provider": mapping.provider,
            "model": mapping.model,
            "voiceId": mapping.voice_id,
            "status": mapping.status.value,
            "materialParameters": mapping.material_parameters,
        }
    )


def pronunciation_fingerprint(guidance: list[PronunciationGuidance]) -> str:
    material = [
        {
            "term": item.term,
            "language": item.language,
            "reviewedReading": item.reviewed_reading,
            "speakerKey": item.speaker_key,
        }
        for item in guidance
    ]
    return sha256_canonical(sorted(material, key=canonical_json))


def audio_input_material(request: SpeechGenerationRequest) -> dict[str, Any]:
    mapping = request.provider_mapping
    if mapping is None:
        raise ValueError("Audio fingerprint requires a provider-resolved request")
    return {
        "schemaVersion": "audio-input-v1",
        "workId": request.work_id,
        "sceneId": request.scene_id,
        "spokenContentId": request.spoken_content_id,
        "textHash": text_hash(request.exact_text),
        "speakerKey": request.speaker_key,
        "performanceIntentHash": sha256_canonical(request.performance_intent),
        "sceneStateHash": sha256_canonical(request.scene_state),
        "voiceProfileFingerprint": voice_profile_fingerprint(request.voice_profile),
        "providerMappingFingerprint": provider_mapping_fingerprint(mapping),
        "pronunciationFingerprint": pronunciation_fingerprint(
            request.pronunciation_guidance
        ),
        "provider": mapping.provider,
        "model": mapping.model,
        "materialRenderParameters": request.material_render_parameters,
        "targetTimingPolicy": dump_contract(request.target_timing_policy),
    }


def audio_input_fingerprint(request: SpeechGenerationRequest) -> str:
    return sha256_canonical(audio_input_material(request))


def final_av_fingerprint(value: FinalAvFingerprintInput) -> str:
    return sha256_canonical(value)


def canonical_final_av_source_ref(fingerprint: str) -> str:
    return f"final-av:{fingerprint}"


def final_av_attempt_source_ref(fingerprint: str, attempt_id: str) -> str:
    if not attempt_id or ":" in attempt_id:
        raise ValueError("attemptId must be non-empty and must not contain ':'")
    return f"final-av-attempt:{fingerprint}:{attempt_id}"


def canonical_audio_source_ref(fingerprint: str) -> str:
    return f"audio-input:{fingerprint}"


def audio_attempt_source_ref(fingerprint: str, attempt_id: str) -> str:
    if not attempt_id or ":" in attempt_id:
        raise ValueError("attemptId must be non-empty and must not contain ':'")
    return f"audio-attempt:{fingerprint}:{attempt_id}"


def source_ref_for_review(
    fingerprint: str,
    status: AudioReviewStatus,
    *,
    attempt_id: str | None = None,
) -> str:
    if status is AudioReviewStatus.PASS:
        return canonical_audio_source_ref(fingerprint)
    if attempt_id is None:
        raise ValueError("non-PASS candidates require attemptId")
    return audio_attempt_source_ref(fingerprint, attempt_id)


def is_audio_fresh(media_content: Mapping[str, Any], request: SpeechGenerationRequest) -> bool:
    return (
        media_content.get("reviewStatus") == AudioReviewStatus.PASS.value
        and media_content.get("audioInputFingerprint")
        == audio_input_fingerprint(request)
    )


def compile_speech_request(
    *,
    work_id: str,
    scene_id: str,
    spoken_content: Mapping[str, Any],
    voice_profile: VoiceProfile,
    provider_mapping: ProviderVoiceMapping,
    pronunciation_guidance: list[PronunciationGuidance],
    material_render_parameters: Mapping[str, Any],
    target_timing_policy: TargetTimingPolicy,
    scene_state: SceneState | None = None,
    non_material_metadata: Mapping[str, Any] | None = None,
) -> SpeechGenerationRequest:
    return SpeechGenerationRequest(
        work_id=work_id,
        scene_id=scene_id,
        spoken_content_id=str(spoken_content["spokenContentId"]),
        exact_text=str(spoken_content["text"]),
        speaker_key=str(spoken_content["speakerKey"]),
        voice_profile=voice_profile.model_copy(deep=True),
        provider_mapping=provider_mapping.model_copy(deep=True),
        pronunciation_guidance=deepcopy(pronunciation_guidance),
        scene_state=scene_state.model_copy(deep=True) if scene_state else None,
        performance_intent=deepcopy(spoken_content.get("performanceIntent", {})),
        material_render_parameters=deepcopy(dict(material_render_parameters)),
        target_timing_policy=target_timing_policy.model_copy(deep=True),
        non_material_metadata=deepcopy(dict(non_material_metadata or {})),
    )


class StructuredSpeechProductionAdapter:
    """Compile the structured speech contract into the existing production seam."""

    def __init__(self, production: ProductionProvider) -> None:
        self.production = production

    async def generate_speech(
        self,
        request: SpeechGenerationRequest,
        reference_media_ids: list[str] | None = None,
    ) -> Media:
        parameters: dict[str, Any] = {"speechRequest": dump_contract(request)}
        if request.provider_mapping is not None:
            parameters["audioInputFingerprint"] = audio_input_fingerprint(request)
        return await self.production.generate_audio(
            request.exact_text,
            reference_media_ids,
            parameters,
        )
