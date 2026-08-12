from enum import StrEnum

from pydantic import Field

from drama_plugin.contracts.base import ContractModel


class AssetType(StrEnum):
    CHARACTER = "CHARACTER"
    LOCATION = "LOCATION"
    PROP = "PROP"
    COSTUME = "COSTUME"
    OTHER = "OTHER"


class Asset(ContractModel):
    id: str
    asset_type: AssetType
    name: str
    description: str | None = None
    reference_media_ids: list[str] = Field(default_factory=list)
