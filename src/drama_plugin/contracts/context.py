from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field

from drama_plugin.contracts.asset import Asset, EffectiveAsset
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.generation import GenerationPlan, GenerationResult, GenerationState
from drama_plugin.contracts.history import HistoricalEvidence
from drama_plugin.contracts.project import Character, Episode, Location, Project, Prop, Scene, Shot, Story


class ContextScope(StrEnum):
    PROJECT = "PROJECT"
    STORY = "STORY"
    EPISODE = "EPISODE"
    SCENE = "SCENE"
    SHOT = "SHOT"
    ASSET = "ASSET"
    HISTORICAL = "HISTORICAL"


class ContextPurpose(StrEnum):
    SHOT_VIDEO_GENERATION = "SHOT_VIDEO_GENERATION"
    SHOT_IMAGE_GENERATION = "SHOT_IMAGE_GENERATION"
    STORY_WRITING = "STORY_WRITING"
    HISTORICAL_RESEARCH = "HISTORICAL_RESEARCH"
    CONTINUITY_REVIEW = "CONTINUITY_REVIEW"
    ASSET_PLANNING = "ASSET_PLANNING"


class ContextBuildRequest(ContractModel):
    scope: ContextScope
    resource_id: str
    purpose: ContextPurpose | str
    options: dict[str, Any] = {}


class EntityContext(ContractModel):
    characters: list[Character] = []
    locations: list[Location] = []
    props: list[Prop] = []


class AssetContext(ContractModel):
    base: list[Asset] = []
    scene: list[Asset] = []
    shot: list[Asset] = []
    effective: list[EffectiveAsset] = []


class GenerationContext(ContractModel):
    plans: list[GenerationPlan] = []
    outputs: list[GenerationResult] = []
    state: GenerationState | None = None


class DramaModelContext(ContractModel):
    context_id: str
    version: int = Field(ge=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scope: ContextScope
    purpose: str
    project: Project | None = None
    story: Story | None = None
    episode: Episode | None = None
    scene: Scene | None = None
    shot: Shot | None = None
    entities: EntityContext = Field(default_factory=EntityContext)
    assets: AssetContext = Field(default_factory=AssetContext)
    historical_evidence: list[HistoricalEvidence] = []
    generation: GenerationContext = Field(default_factory=GenerationContext)
    constraints: dict[str, Any] = {}


class ContextChange(ContractModel):
    operation: Literal["add", "replace", "remove"]
    path: str
    value: Any | None = None


class DramaContextPatch(ContractModel):
    context_id: str
    base_version: int = Field(ge=1)
    new_version: int = Field(ge=2)
    changes: list[ContextChange] = []
    built_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
