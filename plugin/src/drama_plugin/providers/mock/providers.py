from __future__ import annotations

from typing import Any, TypeVar

from drama_plugin.contracts.asset import Asset, AssetType
from drama_plugin.contracts.creation import Episode, Scene, Script, Shot, Work
from drama_plugin.contracts.media import Media, MediaType
from drama_plugin.contracts.research import ClaimAssessment, ResearchEvidence, ResearchSource
from drama_plugin.exceptions import ProviderError
from drama_plugin.providers.mock.data import MockDramaData

T = TypeVar("T", Work, Script, Episode, Scene, Shot)


class MockMemoryProvider:
    def __init__(self, data: MockDramaData) -> None: self.data = data

    async def create_work(self, title: str, description: str | None = None, content: dict[str, Any] | None = None) -> Work:
        self.data.work = Work(id="work-new", title=title, description=description, content=content or {})
        return self.data.work
    async def get_work(self, work_id: str) -> Work: return self._get(self.data.work, work_id, "work")
    async def save_work(self, work: Work) -> Work: self.data.work = work; return work
    async def list_works(self) -> list[Work]: return [self.data.work]
    async def search_works(self, query: str) -> list[Work]: return [self.data.work] if self._matches(query, self.data.work.title, self.data.work.description, self.data.work.content) else []

    async def create_script(self, work_id: str, title: str, content: dict[str, Any] | None = None) -> Script:
        self.data.script = Script(id="script-new", work_id=work_id, title=title, content=content or {}); return self.data.script
    async def get_script(self, script_id: str) -> Script: return self._get(self.data.script, script_id, "script")
    async def save_script(self, script: Script) -> Script: self.data.script = script; return script
    async def list_scripts(self, work_id: str) -> list[Script]: return [self.data.script] if self.data.script.work_id == work_id else []

    async def create_episode(self, script_id: str, number: int, title: str, content: dict[str, Any] | None = None) -> Episode:
        self.data.episode = Episode(id="episode-new", script_id=script_id, number=number, title=title, content=content or {}); return self.data.episode
    async def get_episode(self, episode_id: str) -> Episode: return self._get(self.data.episode, episode_id, "episode")
    async def save_episode(self, episode: Episode) -> Episode: self.data.episode = episode; return episode
    async def list_episodes(self, script_id: str, episode_no: int | None = None, title: str | None = None) -> list[Episode]:
        episode = self.data.episode
        return [episode] if episode.script_id == script_id and (episode_no is None or episode.number == episode_no) and (title is None or title.lower() in episode.title.lower()) else []

    async def create_scene(self, episode_id: str, number: int, heading: str, content: dict[str, Any] | None = None) -> Scene:
        self.data.scene = Scene(id="scene-new", episode_id=episode_id, number=number, heading=heading, content=content or {}); return self.data.scene
    async def get_scene(self, scene_id: str) -> Scene: return self._get(self.data.scene, scene_id, "scene")
    async def save_scene(self, scene: Scene) -> Scene: self.data.scene = scene; return scene
    async def list_scenes(self, episode_id: str, order: int | None = None, location: str | None = None, character: str | None = None) -> list[Scene]:
        scene = self.data.scene
        return [scene] if scene.episode_id == episode_id and (order is None or scene.number == order) and (location is None or self._matches(location, scene.heading, scene.content)) and (character is None or self._matches(character, scene.content)) else []
    async def search_scenes(self, query: str, episode_id: str | None = None) -> list[Scene]:
        scene = self.data.scene
        return [scene] if (episode_id is None or scene.episode_id == episode_id) and self._matches(query, scene.heading, scene.content) else []

    async def create_shot(self, scene_id: str, number: int, description: str, duration_seconds: float | None = None, content: dict[str, Any] | None = None) -> Shot:
        self.data.shot = Shot(id="shot-new", scene_id=scene_id, number=number, description=description, duration_seconds=duration_seconds, content=content or {}); return self.data.shot
    async def get_shot(self, shot_id: str) -> Shot: return self._get(self.data.shot, shot_id, "shot")
    async def save_shot(self, shot: Shot) -> Shot: self.data.shot = shot; return shot
    async def list_shots(self, scene_id: str, shot_no: int | None = None, shot_type: str | None = None, character: str | None = None) -> list[Shot]:
        shot = self.data.shot
        return [shot] if shot.scene_id == scene_id and (shot_no is None or shot.number == shot_no) and (shot_type is None or self._matches(shot_type, shot.description, shot.content)) and (character is None or self._matches(character, shot.description, shot.content)) else []
    async def search_shots(self, query: str, scene_id: str | None = None) -> list[Shot]:
        shot = self.data.shot
        return [shot] if (scene_id is None or shot.scene_id == scene_id) and self._matches(query, shot.description, shot.content) else []

    @staticmethod
    def _get(value: T, requested_id: str, kind: str) -> T:
        if value.id != requested_id: raise ProviderError(f"Mock {kind} not found: {requested_id}")
        return value

    @staticmethod
    def _matches(query: str, *values: object) -> bool:
        return query.casefold() in " ".join(str(value) for value in values if value is not None).casefold()


class MockAssetProvider:
    def __init__(self, data: MockDramaData) -> None: self.data = data
    async def create_asset(self, asset_type: AssetType, name: str, description: str | None = None, reference_media_ids: list[str] | None = None) -> Asset:
        asset = Asset(id="asset-new", asset_type=asset_type, name=name, description=description, reference_media_ids=reference_media_ids or []); self.data.assets.append(asset); return asset
    async def get_asset(self, asset_id: str) -> Asset:
        match = next((item for item in self.data.assets if item.id == asset_id), None)
        if match is None: raise ProviderError(f"Mock asset not found: {asset_id}")
        return match
    async def save_asset(self, asset: Asset) -> Asset:
        self.data.assets = [asset if item.id == asset.id else item for item in self.data.assets]; return asset
    async def list_assets(self, asset_type: AssetType | None = None) -> list[Asset]: return [item for item in self.data.assets if asset_type is None or item.asset_type is asset_type]
    async def search_assets(self, query: str, asset_type: AssetType | None = None) -> list[Asset]:
        lowered = query.lower(); return [item for item in await self.list_assets(asset_type) if lowered in f"{item.name} {item.description or ''}".lower()]


class MockResearchProvider:
    def __init__(self, data: MockDramaData) -> None: self.data = data
    async def search_sources(self, query: str) -> list[ResearchSource]: return [self.data.source]
    async def search_events(self, query: str) -> list[ResearchEvidence]: return [self.data.evidence]
    async def search_people(self, query: str) -> list[ResearchEvidence]: return [self.data.evidence]
    async def search_locations(self, query: str) -> list[ResearchEvidence]: return [self.data.evidence]
    async def verify_claim(self, claim: str) -> ClaimAssessment: return ClaimAssessment(claim=claim, supported=True, evidence=[self.data.evidence], rationale="Mock evidence supports the claim.")


class MockMediaProvider:
    def __init__(self, data: MockDramaData) -> None: self.data = data
    async def create_media(self, media_type: MediaType, mime_type: str, storage_key: str, metadata: dict[str, Any] | None = None) -> Media:
        media = Media(id="media-new", media_type=media_type, mime_type=mime_type, storage_key=storage_key, metadata=metadata or {}); self.data.media.append(media); return media
    async def get_media(self, media_id: str) -> Media:
        match = next((item for item in self.data.media if item.id == media_id), None)
        if match is None: raise ProviderError(f"Mock media not found: {media_id}")
        return match
    async def save_media(self, media: Media) -> Media:
        self.data.media = [media if item.id == media.id else item for item in self.data.media]; return media
    async def list_media(self, media_type: MediaType | None = None) -> list[Media]: return [item for item in self.data.media if media_type is None or item.media_type is media_type]


class MockProductionProvider:
    def __init__(self, data: MockDramaData) -> None: self.data = data
    async def generate_image(self, prompt: str, reference_asset_ids: list[str] | None = None, reference_media_ids: list[str] | None = None, parameters: dict[str, Any] | None = None) -> Media:
        return await self._result(MediaType.IMAGE, "image/png", prompt, reference_media_ids)
    async def generate_video(self, prompt: str, start_frame_media_id: str | None = None, end_frame_media_id: str | None = None, reference_media_ids: list[str] | None = None, parameters: dict[str, Any] | None = None) -> Media:
        refs = [item for item in [start_frame_media_id, end_frame_media_id, *(reference_media_ids or [])] if item]; return await self._result(MediaType.VIDEO, "video/mp4", prompt, refs)
    async def generate_audio(self, prompt: str, reference_media_ids: list[str] | None = None, parameters: dict[str, Any] | None = None) -> Media:
        return await self._result(MediaType.AUDIO, "audio/mpeg", prompt, reference_media_ids)
    async def _result(self, media_type: MediaType, mime_type: str, prompt: str, refs: list[str] | None) -> Media:
        media = Media(id=f"media-generated-{media_type.value.lower()}", media_type=media_type, mime_type=mime_type, storage_key=f"mock/generated/{media_type.value.lower()}", metadata={"prompt": prompt, "referenceMediaIds": refs or []}); self.data.media.append(media); return media
