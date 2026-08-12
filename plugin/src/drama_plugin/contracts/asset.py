from enum import StrEnum
from typing import Any

from pydantic import Field

from drama_plugin.contracts.base import ContractModel


class AssetType(StrEnum):
    CHARACTER = "CHARACTER"
    LOCATION = "LOCATION"
    PROP = "PROP"
    COSTUME = "COSTUME"
    OTHER = "OTHER"
    STANDARD_FACE = "STANDARD_FACE"
    MASTER_CHARACTER_CARD = "MASTER_CHARACTER_CARD"
    MASTER_SCENE_CARD = "MASTER_SCENE_CARD"
    GROUP_ROLE = "GROUP_ROLE"
    COSTUME_REFERENCE = "COSTUME_REFERENCE"
    SCENE_REFERENCE = "SCENE_REFERENCE"
    START_FRAME = "START_FRAME"
    END_FRAME = "END_FRAME"
    KEY_FRAME = "KEY_FRAME"
    VIDEO_INPUT = "VIDEO_INPUT"
    AUDIO_INPUT = "AUDIO_INPUT"


class Asset(ContractModel):
    id: str
    work_id: str
    episode_id: str | None = None
    scene_id: str | None = None
    shot_id: str | None = None
    asset_type: AssetType
    name: str
    description: str | None = None
    reference_media_ids: list[str] = Field(default_factory=list)
    content: dict[str, Any] = Field(default_factory=dict)
