from __future__ import annotations

from enum import StrEnum
from typing import Any

from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.generation import GenerationTarget


class MediaType(StrEnum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class MediaSemanticMetadata(ContractModel):
    entity_type: str | None = None
    entity_id: str | None = None
    entity_name: str | None = None
    asset_id: str | None = None
    generation_target: GenerationTarget | None = None
    semantic_labels: list[str] = []


class Media(ContractModel):
    id: str
    media_type: MediaType
    url: str
    mime_type: str
    semantic: MediaSemanticMetadata
    technical_metadata: dict[str, Any] = {}


class ImageMetadata(ContractModel):
    width: int
    height: int
    color_space: str | None = None


class VideoMetadata(ContractModel):
    width: int
    height: int
    duration_seconds: float
    frame_rate: float | None = None
