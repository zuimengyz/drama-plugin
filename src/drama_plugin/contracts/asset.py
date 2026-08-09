from __future__ import annotations

from enum import StrEnum

from drama_plugin.contracts.base import ContractModel


class AssetType(StrEnum):
    CHARACTER = "CHARACTER"
    LOCATION = "LOCATION"
    PROP = "PROP"


class AssetLevel(StrEnum):
    BASE = "BASE"
    SCENE = "SCENE"
    SHOT = "SHOT"


class Asset(ContractModel):
    id: str
    name: str
    asset_type: AssetType
    level: AssetLevel
    entity_type: str
    entity_id: str
    parent_asset_id: str | None = None
    semantic_labels: list[str] = []


class AssetBinding(ContractModel):
    resource_id: str
    asset_id: str
    level: AssetLevel


class EffectiveAsset(ContractModel):
    entity_type: str
    entity_id: str
    base_asset: Asset | None = None
    scene_variant: Asset | None = None
    shot_variant: Asset | None = None
    effective_asset: Asset


class AssetHierarchy(ContractModel):
    base: list[Asset] = []
    scene: list[Asset] = []
    shot: list[Asset] = []
    effective: list[EffectiveAsset] = []
