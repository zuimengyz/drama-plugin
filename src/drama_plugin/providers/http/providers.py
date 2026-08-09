from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, TypeAdapter

from drama_plugin.contracts.asset import Asset, AssetBinding, AssetHierarchy
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.context import ContextBuildRequest, DramaContextPatch, DramaModelContext
from drama_plugin.contracts.generation import GenerationPlan, GenerationResult, GenerationState, GenerationTarget
from drama_plugin.contracts.history import ClaimVerification, HistoricalEvidence, HistoricalSource
from drama_plugin.contracts.media import ImageMetadata, Media, VideoMetadata
from drama_plugin.contracts.project import Character, Episode, Location, Project, Prop, Scene, Shot, Story
from drama_plugin.exceptions import ContractValidationError
from drama_plugin.providers.http.client import HttpProviderClient

T = TypeVar("T", bound=BaseModel)


def _one(model: type[T], payload: Any) -> T:
    try:
        return model.model_validate(payload)
    except Exception as exc:
        raise ContractValidationError(f"Remote payload does not match {model.__name__}") from exc


def _many(model: type[T], payload: Any) -> list[T]:
    try:
        return TypeAdapter(list[model]).validate_python(payload)  # type: ignore[valid-type]
    except Exception as exc:
        raise ContractValidationError(f"Remote payload does not match list[{model.__name__}]") from exc


class HttpProjectProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def get_project(self, project_id: str) -> Project: return _one(Project, await self.http.request("get_project", params={"project_id": project_id}))
    async def get_story(self, story_id: str) -> Story: return _one(Story, await self.http.request("get_story", params={"story_id": story_id}))
    async def get_episode(self, episode_id: str) -> Episode: return _one(Episode, await self.http.request("get_episode", params={"episode_id": episode_id}))
    async def list_episodes(self, story_id: str) -> list[Episode]: return _many(Episode, await self.http.request("list_episodes", params={"story_id": story_id}))
    async def get_scene(self, scene_id: str) -> Scene: return _one(Scene, await self.http.request("get_scene", params={"scene_id": scene_id}))
    async def list_scenes(self, episode_id: str) -> list[Scene]: return _many(Scene, await self.http.request("list_scenes", params={"episode_id": episode_id}))
    async def get_shot(self, shot_id: str) -> Shot: return _one(Shot, await self.http.request("get_shot", params={"shot_id": shot_id}))
    async def list_shots(self, scene_id: str) -> list[Shot]: return _many(Shot, await self.http.request("list_shots", params={"scene_id": scene_id}))
    async def list_characters(self, resource_id: str) -> list[Character]: return _many(Character, await self.http.request("list_characters", params={"resource_id": resource_id}))
    async def list_locations(self, resource_id: str) -> list[Location]: return _many(Location, await self.http.request("list_locations", params={"resource_id": resource_id}))
    async def list_props(self, resource_id: str) -> list[Prop]: return _many(Prop, await self.http.request("list_props", params={"resource_id": resource_id}))


class HttpAssetProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def search_assets(self, query: str) -> list[Asset]: return _many(Asset, await self.http.request("search_assets", params={"query": query}))
    async def get_asset(self, asset_id: str) -> Asset: return _one(Asset, await self.http.request("get_asset", params={"asset_id": asset_id}))
    async def get_scene_asset_bindings(self, scene_id: str) -> list[AssetBinding]: return _many(AssetBinding, await self.http.request("get_scene_asset_bindings", params={"scene_id": scene_id}))
    async def get_shot_asset_bindings(self, shot_id: str) -> list[AssetBinding]: return _many(AssetBinding, await self.http.request("get_shot_asset_bindings", params={"shot_id": shot_id}))
    async def resolve_asset_hierarchy(self, *, scene_id: str | None = None, shot_id: str | None = None) -> AssetHierarchy: return _one(AssetHierarchy, await self.http.request("resolve_asset_hierarchy", params={"scene_id": scene_id, "shot_id": shot_id}))


class HttpHistoryProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def search_sources(self, query: str) -> list[HistoricalSource]: return _many(HistoricalSource, await self.http.request("search_sources", params={"query": query}))
    async def search_historical_event(self, query: str) -> list[HistoricalEvidence]: return _many(HistoricalEvidence, await self.http.request("search_historical_event", params={"query": query}))
    async def search_historical_person(self, query: str) -> list[HistoricalEvidence]: return _many(HistoricalEvidence, await self.http.request("search_historical_person", params={"query": query}))
    async def search_historical_location(self, query: str) -> list[HistoricalEvidence]: return _many(HistoricalEvidence, await self.http.request("search_historical_location", params={"query": query}))
    async def get_evidence(self, evidence_id: str) -> HistoricalEvidence: return _one(HistoricalEvidence, await self.http.request("get_evidence", params={"evidence_id": evidence_id}))
    async def verify_claim(self, claim: str) -> ClaimVerification: return _one(ClaimVerification, await self.http.request("verify_claim", method="POST", json={"claim": claim}))


class HttpGenerationProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def create_generation_plan(self, generation_target: GenerationTarget, resource_id: str, parameters: dict[str, Any] | None = None) -> GenerationPlan: return _one(GenerationPlan, await self.http.request("create_generation_plan", method="POST", json={"generationTarget": generation_target, "resourceId": resource_id, "parameters": parameters or {}}))
    async def compile_generation_plan(self, plan_id: str) -> GenerationPlan: return _one(GenerationPlan, await self.http.request("compile_generation_plan", method="POST", json={"planId": plan_id}))
    async def submit_generation(self, plan_id: str) -> GenerationState: return _one(GenerationState, await self.http.request("submit_generation", method="POST", json={"planId": plan_id}))
    async def get_generation_status(self, plan_id: str) -> GenerationState: return _one(GenerationState, await self.http.request("get_generation_status", params={"plan_id": plan_id}))
    async def get_generation_result(self, plan_id: str) -> GenerationResult: return _one(GenerationResult, await self.http.request("get_generation_result", params={"plan_id": plan_id}))


class HttpMediaProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def get_media(self, media_id: str) -> Media: return _one(Media, await self.http.request("get_media", params={"media_id": media_id}))
    async def list_asset_media(self, asset_id: str) -> list[Media]: return _many(Media, await self.http.request("list_asset_media", params={"asset_id": asset_id}))
    async def get_image_metadata(self, media_id: str) -> ImageMetadata: return _one(ImageMetadata, await self.http.request("get_image_metadata", params={"media_id": media_id}))
    async def get_video_metadata(self, media_id: str) -> VideoMetadata: return _one(VideoMetadata, await self.http.request("get_video_metadata", params={"media_id": media_id}))


class RemoteContextProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def build_context(self, request: ContextBuildRequest) -> DramaModelContext:
        return _one(DramaModelContext, await self.http.request("build_context", method="POST", json=dump_contract(request)))
    async def refresh_context(self, request: ContextBuildRequest, current: DramaModelContext) -> DramaContextPatch:
        body = {"request": dump_contract(request), "currentContext": dump_contract(current)}
        return _one(DramaContextPatch, await self.http.request("refresh_context", method="POST", json=body))
