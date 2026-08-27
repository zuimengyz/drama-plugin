from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field

from drama_plugin.contracts.base import ContractModel


class VoiceSourceType(StrEnum):
    DESIGNED = "DESIGNED"
    REFERENCE_CLONED = "REFERENCE_CLONED"


class VoiceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class VoiceProviderMappingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    RETIRED = "RETIRED"


class VoiceProviderMapping(ContractModel):
    provider: str
    model: str
    provider_voice_id: str
    material_fingerprint: str
    status: VoiceProviderMappingStatus = VoiceProviderMappingStatus.ACTIVE
    created_at: datetime


class VoiceContent(ContractModel):
    schema_version: Literal["voice-v1"] = "voice-v1"
    creative_casting_profile: dict[str, Any]
    source_provenance: dict[str, Any]
    provider_mappings: list[VoiceProviderMapping] = Field(default_factory=list)


class Voice(ContractModel):
    id: str
    name: str
    source_type: VoiceSourceType
    status: VoiceStatus
    storage_type: str
    bucket_name: str
    object_key: str
    mime_type: str
    file_size: int = Field(gt=0)
    duration_ms: int = Field(gt=0)
    content_hash: str
    content: VoiceContent
    version: int = Field(gt=0)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class VoiceResolveResult(ContractModel):
    voice_id: str
    url: str
    expires_at: datetime
    mime_type: str
    size_bytes: int = Field(gt=0)
    content_hash: str
