from __future__ import annotations

from typing import Any

from drama_plugin.contracts.asset import Asset, AssetBinding, AssetHierarchy, AssetLevel, EffectiveAsset
from drama_plugin.contracts.generation import GenerationPlan, GenerationResult, GenerationState, GenerationStatus, GenerationTarget
from drama_plugin.contracts.history import ClaimVerification, HistoricalEvidence, HistoricalSource
from drama_plugin.contracts.media import ImageMetadata, Media, VideoMetadata
from drama_plugin.contracts.project import Character, Episode, Location, Project, Prop, Scene, Shot, Story
from drama_plugin.exceptions import ProviderError
from drama_plugin.providers.mock.data import MockDramaData


class MockProjectProvider:
    def __init__(self, data: MockDramaData) -> None:
        self.data = data

    async def get_project(self, project_id: str) -> Project:
        self._require(project_id, self.data.project.id, "project")
        return self.data.project

    async def get_story(self, story_id: str) -> Story:
        self._require(story_id, self.data.story.id, "story")
        return self.data.story

    async def get_episode(self, episode_id: str) -> Episode:
        self._require(episode_id, self.data.episode.id, "episode")
        return self.data.episode

    async def list_episodes(self, story_id: str) -> list[Episode]:
        self._require(story_id, self.data.story.id, "story")
        return [self.data.episode]

    async def get_scene(self, scene_id: str) -> Scene:
        self._require(scene_id, self.data.scene.id, "scene")
        return self.data.scene

    async def list_scenes(self, episode_id: str) -> list[Scene]:
        self._require(episode_id, self.data.episode.id, "episode")
        return [self.data.scene]

    async def get_shot(self, shot_id: str) -> Shot:
        self._require(shot_id, self.data.shot.id, "shot")
        return self.data.shot

    async def list_shots(self, scene_id: str) -> list[Shot]:
        self._require(scene_id, self.data.scene.id, "scene")
        return [self.data.shot]

    async def list_characters(self, resource_id: str) -> list[Character]:
        return [self.data.character]

    async def list_locations(self, resource_id: str) -> list[Location]:
        return [self.data.location]

    async def list_props(self, resource_id: str) -> list[Prop]:
        return [self.data.prop]

    @staticmethod
    def _require(actual: str, expected: str, kind: str) -> None:
        if actual != expected:
            raise ProviderError(f"Mock {kind} not found: {actual}")


class MockAssetProvider:
    def __init__(self, data: MockDramaData) -> None:
        self.data = data

    async def search_assets(self, query: str) -> list[Asset]:
        lowered = query.lower()
        return [asset for asset in self.data.assets if lowered in asset.name.lower() or lowered in " ".join(asset.semantic_labels).lower()]

    async def get_asset(self, asset_id: str) -> Asset:
        for asset in self.data.assets:
            if asset.id == asset_id:
                return asset
        raise ProviderError(f"Mock asset not found: {asset_id}")

    async def get_scene_asset_bindings(self, scene_id: str) -> list[AssetBinding]:
        return [AssetBinding(resource_id=scene_id, asset_id=a.id, level=a.level) for a in self.data.assets if a.level is AssetLevel.SCENE]

    async def get_shot_asset_bindings(self, shot_id: str) -> list[AssetBinding]:
        return [AssetBinding(resource_id=shot_id, asset_id=a.id, level=a.level) for a in self.data.assets if a.level is AssetLevel.SHOT]

    async def resolve_asset_hierarchy(self, *, scene_id: str | None = None, shot_id: str | None = None) -> AssetHierarchy:
        base = [a for a in self.data.assets if a.level is AssetLevel.BASE]
        scene = [a for a in self.data.assets if a.level is AssetLevel.SCENE] if scene_id or shot_id else []
        shot = [a for a in self.data.assets if a.level is AssetLevel.SHOT] if shot_id else []
        effective: list[EffectiveAsset] = []
        for entity_type, entity_id in {(a.entity_type, a.entity_id) for a in base + scene + shot}:
            base_asset = next((a for a in base if a.entity_id == entity_id), None)
            scene_asset = next((a for a in scene if a.entity_id == entity_id), None)
            shot_asset = next((a for a in shot if a.entity_id == entity_id), None)
            chosen = shot_asset or scene_asset or base_asset
            if chosen:
                effective.append(EffectiveAsset(entity_type=entity_type, entity_id=entity_id, base_asset=base_asset, scene_variant=scene_asset, shot_variant=shot_asset, effective_asset=chosen))
        return AssetHierarchy(base=base, scene=scene, shot=shot, effective=effective)


class MockHistoryProvider:
    def __init__(self, data: MockDramaData) -> None:
        self.data = data

    async def search_sources(self, query: str) -> list[HistoricalSource]:
        return [self.data.source]

    async def search_historical_event(self, query: str) -> list[HistoricalEvidence]:
        return [self.data.evidence]

    async def search_historical_person(self, query: str) -> list[HistoricalEvidence]:
        return [self.data.evidence]

    async def search_historical_location(self, query: str) -> list[HistoricalEvidence]:
        return [self.data.evidence]

    async def get_evidence(self, evidence_id: str) -> HistoricalEvidence:
        if evidence_id != self.data.evidence.id:
            raise ProviderError(f"Mock evidence not found: {evidence_id}")
        return self.data.evidence

    async def verify_claim(self, claim: str) -> ClaimVerification:
        return ClaimVerification(claim=claim, supported=True, evidence_ids=[self.data.evidence.id], rationale="Mock evidence supports the claim.")


class MockGenerationProvider:
    def __init__(self, data: MockDramaData) -> None:
        self.data = data

    async def create_generation_plan(self, generation_target: GenerationTarget, resource_id: str, parameters: dict[str, Any] | None = None) -> GenerationPlan:
        return self.data.plan.model_copy(update={"generation_target": generation_target, "resource_id": resource_id, "parameters": parameters or {}})

    async def compile_generation_plan(self, plan_id: str) -> GenerationPlan:
        self._require_plan(plan_id)
        return self.data.plan.model_copy(update={"compiled_payload": {"workflowCode": self.data.plan.workflow_code, "mock": True}})

    async def submit_generation(self, plan_id: str) -> GenerationState:
        self._require_plan(plan_id)
        return self.data.generation_state.model_copy(update={"status": GenerationStatus.SUBMITTED, "message": "Submitted to mock generation service"})

    async def get_generation_status(self, plan_id: str) -> GenerationState:
        self._require_plan(plan_id)
        return self.data.generation_state

    async def get_generation_result(self, plan_id: str) -> GenerationResult:
        self._require_plan(plan_id)
        return GenerationResult(plan_id=plan_id, status=GenerationStatus.SUCCEEDED, media_ids=[self.data.media.id], metadata={"mock": True})

    def _require_plan(self, plan_id: str) -> None:
        if plan_id != self.data.plan.id:
            raise ProviderError(f"Mock generation plan not found: {plan_id}")


class MockMediaProvider:
    def __init__(self, data: MockDramaData) -> None:
        self.data = data

    async def get_media(self, media_id: str) -> Media:
        if media_id != self.data.media.id:
            raise ProviderError(f"Mock media not found: {media_id}")
        return self.data.media

    async def list_asset_media(self, asset_id: str) -> list[Media]:
        return [self.data.media] if asset_id == self.data.media.semantic.asset_id else []

    async def get_image_metadata(self, media_id: str) -> ImageMetadata:
        await self.get_media(media_id)
        return ImageMetadata(width=1024, height=1024, color_space="sRGB")

    async def get_video_metadata(self, media_id: str) -> VideoMetadata:
        return VideoMetadata(width=1920, height=1080, duration_seconds=4.0, frame_rate=24.0)
