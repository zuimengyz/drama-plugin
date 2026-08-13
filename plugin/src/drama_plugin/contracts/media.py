from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from drama_plugin.contracts.base import ContractModel


class MediaType(StrEnum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"


class Media(ContractModel):
    id: str
    work_id: str
    asset_id: str | None = None
    shot_id: str | None = None
    media_type: MediaType
    purpose: str | None = None
    source_ref: str
    content: dict[str, Any] = Field(default_factory=dict)


class MediaResolveResult(ContractModel):
    media_id: str
    url: str
    expires_at: datetime
    mime_type: str | None = None
    size_bytes: int | None = None
