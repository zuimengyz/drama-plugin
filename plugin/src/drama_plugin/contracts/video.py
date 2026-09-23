"""Canonical video intent and normalized async results, independent of transport."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel, sha256_canonical
from drama_plugin.contracts.creative_asset import Text, Hash
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.contracts.visual_route import RouteStyleContract

InputMode = Literal['text_to_video', 'image_to_video', 'first_last_frame', 'reference', 'motion_transfer', 'edit', 'extend']


class VideoReference(ContractModel):
    media_id: Text
    version: Text
    content_hash: Hash
    kind: Literal['image', 'video', 'audio']
    semantics: tuple[Literal['identity', 'costume', 'prop', 'environment', 'style', 'motion', 'camera', 'continuity'], ...] = Field(min_length=1)
    # IDs and hashes are canonical. Signed delivery URLs exist only in the adapter.
    duration: float | None = Field(default=None, gt=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    review_ref: Text


class CharacterContinuity(ContractModel):
    character_id: Text
    face_identity: Text
    body_type: Text
    age: Text
    hair: Text
    costume: Text
    armor: Text
    weapons: Text
    props: Text


class ContinuityPack(ContractModel):
    work_id: Text
    segment_id: Text
    revision: Text
    sources: tuple[SourcePin, ...] = Field(min_length=1)
    characters: tuple[CharacterContinuity, ...] = ()
    location_identity: Text
    time_of_day: Text
    weather: Text
    lighting: Text
    style: RouteStyleContract
    color_language: Text
    lens_language: Text
    references: tuple[VideoReference, ...] = ()
    required_reference_ids: tuple[Text, ...] = ()
    accepted_previous_shot: Text | None = None
    accepted_previous_last_frame: VideoReference | None = None
    primary_provider: Text
    primary_model: Text
    identity_critical: bool = True

    @model_validator(mode='after')
    def coherent(self) -> Self:
        ids = [r.media_id for r in self.references]
        if len(ids) != len(set(ids)) or not set(self.required_reference_ids) <= set(ids):
            raise ValueError('CONTINUITY_REFERENCE_IDENTITY_INVALID')
        if self.accepted_previous_last_frame and (not self.accepted_previous_shot or self.accepted_previous_last_frame.kind != 'image'):
            raise ValueError('PREVIOUS_FRAME_REQUIRES_ACCEPTED_SHOT')
        return self


class SwitchEvidence(ContractModel):
    primary_capability_gap: Text
    evidence_ref: Text
    at_shot_boundary: bool


class VideoRequest(ContractModel):
    authority_context: dict[str, Any] | None = Field(default=None, alias='authority_context')
    prompt_normalization: dict[str, Any] | None = Field(default=None, alias='prompt_normalization')
    prompt: Text
    negative_prompt: str = ''
    input_mode: InputMode
    first_frame: VideoReference | None = None
    last_frame: VideoReference | None = None
    reference_images: tuple[VideoReference, ...] = ()
    reference_videos: tuple[VideoReference, ...] = ()
    reference_audios: tuple[VideoReference, ...] = ()
    duration: int = Field(gt=0)
    resolution: Text
    aspect_ratio: Text
    native_audio: bool
    seed: int | None = Field(default=None, ge=0, le=2147483647)
    character_references: tuple[Text, ...] = ()
    scene_references: tuple[Text, ...] = ()
    style_references: tuple[Text, ...] = ()
    provider_hints: dict[str, Any] = Field(default_factory=dict)
    continuity: ContinuityPack
    switch_evidence: SwitchEvidence | None = None

    def references(self) -> tuple[VideoReference, ...]:
        return tuple(r for r in (self.first_frame, self.last_frame) if r) + self.reference_images + self.reference_videos + self.reference_audios

    @model_validator(mode='after')
    def input_shape(self) -> Self:
        for collection, kind in ((self.reference_images, 'image'), (self.reference_videos, 'video'), (self.reference_audios, 'audio')):
            if any(r.kind != kind for r in collection):
                raise ValueError('REFERENCE_KIND_MISMATCH')
        if any(r and r.kind != 'image' for r in (self.first_frame, self.last_frame)):
            raise ValueError('ENDPOINT_MUST_BE_IMAGE')
        if self.last_frame and not self.first_frame:
            raise ValueError('FIRST_FRAME_REQUIRED')
        if self.input_mode == 'text_to_video' and self.references():
            raise ValueError('TEXT_MODE_HAS_REFERENCES')
        if self.input_mode == 'image_to_video' and (not self.first_frame or self.last_frame):
            raise ValueError('SINGLE_FIRST_FRAME_REQUIRED')
        if self.input_mode == 'first_last_frame' and not (self.first_frame and self.last_frame):
            raise ValueError('ENDPOINT_PAIR_REQUIRED')
        if self.input_mode in {'reference', 'motion_transfer', 'edit', 'extend'} and (self.first_frame or self.last_frame or not self.references()):
            raise ValueError('REFERENCE_MODE_SHAPE_INVALID')
        ids = [r.media_id for r in self.references()]
        if len(ids) != len(set(ids)):
            raise ValueError('DUPLICATE_REFERENCE')
        if not set(self.character_references + self.scene_references + self.style_references) <= set(ids):
            raise ValueError('UNBOUND_SEMANTIC_REFERENCE')
        return self


class CostEstimate(ContractModel):
    amount: float = Field(ge=0, allow_inf_nan=False)
    currency: Text
    source: Text
    checked_at: datetime
    expires_at: datetime
    request_fingerprint: Hash


class ProviderTask(ContractModel):
    provider: Text
    model: Text
    provider_task_id: Text | None = None
    client_request_id: Text
    request_fingerprint: Hash
    status: Literal['QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELED', 'UNKNOWN', 'NOT_CREATED']
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    resolution: str | None = None
    fps: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    output_url: str | None = Field(default=None, repr=False)
    output_media_id: str | None = None
    usage: dict[str, int | float | str] = Field(default_factory=dict)
    estimated_cost: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    actual_cost: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    currency: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False

    def durable(self) -> dict[str, Any]:
        return self.model_dump(mode='json', by_alias=True, exclude={'output_url'})


VideoGenerationResult = ProviderTask


def request_fingerprint(request: VideoRequest) -> str:
    return sha256_canonical(request)
