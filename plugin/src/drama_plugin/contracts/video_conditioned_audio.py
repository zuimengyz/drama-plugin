from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from drama_plugin.contracts.audio_projection import AudioPerformanceBrief, Fingerprint, NonBlankText
from drama_plugin.contracts.base import ContractModel, dump_contract, sha256_canonical


class VideoConditionedAudioProjection(ContractModel):
    """Lineage wrapper composing the existing Audio brief, not a new audio ontology."""

    schema_version: Literal["video-conditioned-audio-v1"] = "video-conditioned-audio-v1"
    base_audio_projection_fingerprint: Fingerprint
    realized_performance_fingerprint: Fingerprint
    video_media_id: NonBlankText
    video_content_hash: Fingerprint
    shot_id: NonBlankText
    voice_material_fingerprint: Fingerprint
    final_audio_performance_brief: AudioPerformanceBrief
    fingerprint: Fingerprint

    @model_validator(mode="after")
    def verify_fingerprints(self) -> "VideoConditionedAudioProjection":
        brief = self.final_audio_performance_brief
        if brief.fingerprint != sha256_canonical(dump_contract(brief, exclude={"fingerprint"})):
            raise ValueError("final Audio brief fingerprint is invalid")
        if self.fingerprint != sha256_canonical(dump_contract(self, exclude={"fingerprint"})):
            raise ValueError("final Audio Projection fingerprint is invalid")
        return self
