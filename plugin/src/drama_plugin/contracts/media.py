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
    media_type: MediaType
    mime_type: str
    storage_key: str
    metadata: dict[str, Any] = Field(default_factory=dict)
