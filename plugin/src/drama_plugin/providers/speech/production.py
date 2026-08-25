from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from drama_plugin.audio.foundation import (
    audio_input_fingerprint,
    is_audio_fresh,
    pronunciation_fingerprint,
    provider_mapping_fingerprint,
    source_ref_for_review,
    text_hash,
    voice_profile_fingerprint,
)
from drama_plugin.audio.host_media import MediaProbe, probe_media
from drama_plugin.contracts.audio import AudioReviewStatus, SpeechGenerationRequest
from drama_plugin.contracts.media import Media, MediaType
from drama_plugin.exceptions import ContractValidationError
from drama_plugin.providers.base.interfaces import MediaProvider, ProductionProvider, SpeechProvider


class SpeechBackedProductionProvider:
    """Adds real structured speech to production while delegating visual methods."""

    def __init__(
        self,
        delegate: ProductionProvider,
        speech: SpeechProvider,
        media: MediaProvider,
        probe: Callable[[Path | str], MediaProbe] = probe_media,
    ) -> None:
        self.delegate = delegate
        self.speech = speech
        self.media = media
        self.probe = probe

    async def generate_image(
        self,
        prompt: str,
        reference_asset_ids: list[str] | None = None,
        reference_media_ids: list[str] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Media:
        return await self.delegate.generate_image(
            prompt, reference_asset_ids, reference_media_ids, parameters
        )

    async def generate_video(
        self,
        prompt: str,
        start_frame_media_id: str | None = None,
        end_frame_media_id: str | None = None,
        reference_media_ids: list[str] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Media:
        return await self.delegate.generate_video(
            prompt,
            start_frame_media_id,
            end_frame_media_id,
            reference_media_ids,
            parameters,
        )

    async def generate_audio(
        self,
        prompt: str,
        reference_media_ids: list[str] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Media:
        raw = (parameters or {}).get("speechRequest")
        if raw is None:
            raise ContractValidationError("Real speech requires speechRequest")
        request = SpeechGenerationRequest.model_validate(raw)
        if prompt != request.exact_text:
            raise ContractValidationError("Speech prompt must equal exactText")
        fingerprint = audio_input_fingerprint(request)
        canonical_ref = source_ref_for_review(fingerprint, AudioReviewStatus.PASS)
        reusable = await self.media.list_media(
            media_type=MediaType.AUDIO,
            work_id=request.work_id,
            purpose="SPEECH_CLIP",
            source_ref=canonical_ref,
        )
        for existing in reusable:
            if is_audio_fresh(existing.content, request):
                return existing

        generated = await self.speech.generate_speech(request)
        parsed_source = urlparse(generated.source_uri)
        if parsed_source.scheme != "file":
            raise ContractValidationError("Real speech provider must return a local file URI")
        source_path = Path(unquote(parsed_source.path))
        physical = self.probe(source_path)
        if not any(stream.get("codec_type") == "audio" for stream in physical.streams):
            raise ContractValidationError("Generated speech has no physical audio stream")
        attempt_id = str(generated.provider_metadata.get("attemptId", ""))
        source_ref = source_ref_for_review(
            fingerprint, AudioReviewStatus.PENDING, attempt_id=attempt_id
        )
        provider_request_id = generated.provider_metadata.get("providerRequestId")
        response_sha256 = generated.provider_metadata.get("responseSha256")
        content: dict[str, Any] = {
            "schemaVersion": "speech-clip-v1",
            "sceneId": request.scene_id,
            "spokenContentId": request.spoken_content_id,
            "speakerKey": request.speaker_key,
            "textHash": text_hash(request.exact_text),
            "voiceProfileFingerprint": voice_profile_fingerprint(request.voice_profile),
            "providerMappingFingerprint": provider_mapping_fingerprint(
                request.provider_mapping
            ),
            "pronunciationFingerprint": pronunciation_fingerprint(
                request.pronunciation_guidance
            ),
            "audioInputFingerprint": fingerprint,
            "provider": request.provider_mapping.provider,
            "model": request.provider_mapping.model,
            "actualDurationMs": physical.duration_ms,
            "reviewStatus": AudioReviewStatus.PENDING.value,
            "exactTextInputVerified": True,
        }
        if provider_request_id:
            content["providerJobId"] = provider_request_id
        if response_sha256:
            content["audioSha256"] = response_sha256
        return await self.media.import_media(
            work_id=request.work_id,
            media_type=MediaType.AUDIO,
            source_uri=generated.source_uri,
            content=content,
            purpose="SPEECH_CLIP",
            source_ref=source_ref,
            duration_ms=physical.duration_ms,
        )
