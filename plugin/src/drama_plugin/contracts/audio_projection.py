from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Any

from pydantic import Field, StringConstraints, model_validator, model_serializer, SerializerFunctionWrapHandler

from drama_plugin.contracts.base import ContractModel


NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Fingerprint = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class PaceTendency(StrEnum):
    SLOWER = "SLOWER"
    NEUTRAL = "NEUTRAL"
    FASTER = "FASTER"


class VolumeTendency(StrEnum):
    LOWER = "LOWER"
    NEUTRAL = "NEUTRAL"
    HIGHER = "HIGHER"


class CapabilityStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    APPROXIMATED = "APPROXIMATED"
    TEXT_RENDERABLE = "TEXT_RENDERABLE"
    SEGMENT_RENDERABLE = "SEGMENT_RENDERABLE"
    UNSUPPORTED = "UNSUPPORTED"


class PhraseDeliverySpan(ContractModel):
    """A canonical Unicode character span, not a separate planning entity."""
    start_char: Annotated[int, Field(strict=True, ge=0)]
    end_char: Annotated[int, Field(strict=True, gt=0)]
    delivery: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]

    @model_validator(mode="after")
    def validate_span(self) -> "PhraseDeliverySpan":
        if self.end_char <= self.start_char or any(c in self.delivery for c in "[]\n\r"):
            raise ValueError("invalid phrase delivery span")
        return self


class AudioPerformanceBrief(ContractModel):
    schema_version: Literal["audio-projection-v1"] = "audio-projection-v1"
    dpd_fingerprint: Fingerprint
    scene_id: NonBlankText
    spoken_content_id: NonBlankText
    speaker_key: NonBlankText
    text_fingerprint: Fingerprint
    voice_profile_id: NonBlankText
    voice_profile_fingerprint: Fingerprint
    voice_identity_ref: NonBlankText
    timing_context_fingerprint: Fingerprint
    pace: NonBlankText
    pace_tendency: PaceTendency
    rhythm: NonBlankText
    intensity: NonBlankText
    volume_tendency: VolumeTendency
    pause_strategy: NonBlankText
    articulation: NonBlankText
    sentence_ending: NonBlankText
    control: NonBlankText
    performance_boundaries: tuple[NonBlankText, ...] = ()
    phrase_delivery_spans: tuple[PhraseDeliverySpan, ...] = ()
    fingerprint: Fingerprint

    @model_serializer(mode="wrap")
    def serialize_material(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        if not self.phrase_delivery_spans:
            result.pop("phraseDeliverySpans", None)
            result.pop("phrase_delivery_spans", None)
        return result

    @model_validator(mode="after")
    def validate_phrase_order(self) -> "AudioPerformanceBrief":
        if len(self.phrase_delivery_spans) > 12 or any(
            a.end_char > b.start_char for a, b in zip(self.phrase_delivery_spans, self.phrase_delivery_spans[1:])
        ):
            raise ValueError("phrase spans must be ordered and non-overlapping")
        return self


class AudioCapabilityDiagnostic(ContractModel):
    dimension: NonBlankText
    status: CapabilityStatus
    mapped_control: NonBlankText | None = None
    reason: NonBlankText

    @model_validator(mode="after")
    def validate_mapping(self) -> "AudioCapabilityDiagnostic":
        if self.status is CapabilityStatus.UNSUPPORTED and self.mapped_control is not None:
            raise ValueError("unsupported capability must not claim a mapped control")
        if self.status is not CapabilityStatus.UNSUPPORTED and self.mapped_control is None:
            raise ValueError("supported or approximated capability requires a mapped control")
        return self
