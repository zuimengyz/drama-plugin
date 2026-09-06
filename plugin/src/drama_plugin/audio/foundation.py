from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any, Mapping

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
from drama_plugin.contracts.base import (
    canonical_json as canonical_json,
    dump_contract,
    sha256_canonical as sha256_canonical,
)


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
    material = {
        "schemaVersion": "audio-input-v1",
        "workId": request.work_id,
        "sceneId": request.scene_id,
        "spokenContentId": request.spoken_content_id,
        "textHash": text_hash(request.exact_text),
        "speakerKey": request.speaker_key,
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
    if request.performance_rendition is not None:
        # Presentation/reviewer notes are not material; the active version is.
        material["performanceRendition"] = {
            key: request.performance_rendition[key] for key in (
                "sourceLineId", "speakerKey", "sourceTextHash", "performanceLanguage",
                "performanceText", "renditionVersion",
            )
        }
    if request.video_conditioned_projection is not None:
        material["performanceAuthority"] = "VIDEO_CONDITIONED_FINAL_AUDIO"
        material["finalAudioProjectionFingerprint"] = request.video_conditioned_projection.fingerprint
    elif request.audio_performance_brief is not None:
        material["performanceAuthority"] = "DPD_AUDIO_PROJECTION"
        material["audioProjectionFingerprint"] = request.audio_performance_brief.fingerprint
    else:
        material["performanceIntentHash"] = sha256_canonical(request.performance_intent)
        material["sceneStateHash"] = sha256_canonical(request.scene_state)
    return material


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


def is_audio_fresh(media_content: Mapping[str, Any], request: SpeechGenerationRequest, *,
                   review_decisions: Mapping[str, str] | None = None, content_hash: str | None = None) -> bool:
    return (
        (not review_decisions or (content_hash is not None and review_decisions.get(content_hash) != "FAIL"))
        and media_content.get("reviewStatus") == AudioReviewStatus.PASS.value
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


def select_performance_language(*, explicit_language: str | None = None,
                                dubbed_language: str | None = None,
                                scene_language: str | None = None) -> str:
    """Caller supplies reviewed scene context; UI language/nationality are not inputs."""
    language = dubbed_language or explicit_language or scene_language
    if not language or not language.strip():
        raise ValueError("performance language needs explicit choice or reviewed scene context")
    return language.strip()


def resolve_performance_text(source: Mapping[str, Any],
                             rendition: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a working spoken item without mutating the frozen Scene source."""
    working = deepcopy(dict(source))
    if rendition is None:
        return working
    identity = source.get("id") or source.get("spokenContentId")
    if (rendition.get("sourceLineId") != identity
            or rendition.get("speakerKey") != source.get("speakerKey")
            or rendition.get("sourceTextHash") != text_hash(str(source["text"]))):
        raise ValueError("performance rendition does not match frozen source")
    for key in ("performanceLanguage", "performanceText", "renditionVersion"):
        if not isinstance(rendition.get(key), str) or not str(rendition[key]).strip():
            raise ValueError("performance rendition is incomplete")
    if rendition.get("reviewStatus") != "PASS":
        raise ValueError("performance text must be reviewed before synthesis")
    working["text"] = rendition["performanceText"]
    return working
