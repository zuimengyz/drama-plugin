from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field

from drama_plugin.contracts.asset import Asset
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creation import Episode, Scene, Script, Shot, Work
from drama_plugin.contracts.media import Media


class ContextScope(StrEnum):
    WORK = "WORK"
    SCRIPT = "SCRIPT"
    EPISODE = "EPISODE"
    SCENE = "SCENE"
    SHOT = "SHOT"
    ASSET = "ASSET"
    MEDIA = "MEDIA"


class ContextPurpose(StrEnum):
    WORK_CREATION = "WORK_CREATION"
    SCRIPT_ADAPTATION = "SCRIPT_ADAPTATION"
    EPISODE_DEVELOPMENT = "EPISODE_DEVELOPMENT"
    SCENE_DEVELOPMENT = "SCENE_DEVELOPMENT"
    SHOT_DESIGN = "SHOT_DESIGN"
    ASSET_RESOLUTION = "ASSET_RESOLUTION"
    SHOT_PRODUCTION = "SHOT_PRODUCTION"
    HISTORICAL_RESEARCH = "HISTORICAL_RESEARCH"
    CONTINUITY_REVIEW = "CONTINUITY_REVIEW"


class ContextBuildRequest(ContractModel):
    scope: ContextScope
    resource_id: str
    purpose: ContextPurpose | str
    options: dict[str, Any] = Field(default_factory=dict)


class DramaRunContext(ContractModel):
    context_id: str
    version: int = Field(ge=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scope: ContextScope
    purpose: str
    work: Work | None = None
    script: Script | None = None
    episode: Episode | None = None
    scene: Scene | None = None
    shot: Shot | None = None
    asset: Asset | None = None
    media: Media | None = None
    selected_asset_ids: list[str] = Field(default_factory=list)
    generated_media_ids: list[str] = Field(default_factory=list)
    research_context: dict[str, Any] = Field(default_factory=dict)
    temporary_state: dict[str, Any] = Field(default_factory=dict)


class ContextChange(ContractModel):
    operation: Literal["add", "replace", "remove"]
    path: str
    value: Any | None = None


class DramaContextPatch(ContractModel):
    context_id: str
    base_version: int = Field(ge=1)
    new_version: int = Field(ge=2)
    changes: list[ContextChange] = Field(default_factory=list)
    built_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
