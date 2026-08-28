from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar

from drama_plugin.contracts.asset import Asset, AssetType
from drama_plugin.contracts.creation import Episode, Scene, Script, Shot, Work
from drama_plugin.contracts.media import Media, MediaResolveResult, MediaRestoreResult, MediaRestoreStatus, MediaType
from drama_plugin.contracts.research import ClaimAssessment, ResearchEvidence, ResearchSource
from drama_plugin.contracts.voice import Voice, VoiceContent, VoiceResolveResult, VoiceSourceType, VoiceStatus
from drama_plugin.exceptions import ProviderError
from drama_plugin.providers.mock.data import MockDramaData

T = TypeVar("T", Work, Script, Episode, Scene, Shot)


class MockMemoryProvider:
    def __init__(self, data: MockDramaData) -> None: self.data = data

    async def create_work(self, title: str, content: dict[str, Any], description: str | None = None) -> Work:
        self.data.work = Work(id="work-new", title=title, description=description, content=content)
        return self.data.work
    async def get_work(self, work_id: str) -> Work: return self._get(self.data.work, work_id, "work")
    async def save_work(self, work_id: str, title: str, content: dict[str, Any], description: str | None = None) -> Work:
        self._get(self.data.work, work_id, "work")
        self.data.work = Work(id=work_id, title=title, description=description, content=content, version=self.data.work.version + 1)
        return self.data.work
    async def bind_work_voice(self, work_id: str, speaker_key: str, voice_id: str, expected_version: int) -> Work:
        work = self._get(self.data.work, work_id, "work")
        if work.version != expected_version: raise ProviderError("Mock work version changed")
        content = work.model_copy(deep=True).content
        profiles = content.setdefault("voiceProfiles", [])
        binding = next((item for item in profiles if item.get("speakerKey") == speaker_key), None)
        if binding is None:
            binding = {"speakerKey": speaker_key}; profiles.append(binding)
        binding["voiceId"] = voice_id
        self.data.work = work.model_copy(update={"content": content, "version": work.version + 1})
        return self.data.work
    async def list_works(self) -> list[Work]: return [self.data.work]
    async def search_works(self, query: str) -> list[Work]: return [self.data.work] if self._matches(query, self.data.work.title, self.data.work.description, self.data.work.content) else []

    async def create_script(self, work_id: str, title: str, content: dict[str, Any]) -> Script:
        self.data.script = Script(id="script-new", work_id=work_id, title=title, content=content); return self.data.script
    async def get_script(self, script_id: str) -> Script: return self._get(self.data.script, script_id, "script")
    async def save_script(self, script_id: str, title: str, content: dict[str, Any]) -> Script:
        existing = self._get(self.data.script, script_id, "script")
        self.data.script = Script(id=script_id, work_id=existing.work_id, title=title, content=content)
        return self.data.script
    async def list_scripts(self, work_id: str) -> list[Script]: return [self.data.script] if self.data.script.work_id == work_id else []

    async def create_episode(self, script_id: str, episode_no: int, title: str, content: dict[str, Any]) -> Episode:
        self.data.episode = Episode(id="episode-new", script_id=script_id, episode_no=episode_no, title=title, content=content); return self.data.episode
    async def get_episode(self, episode_id: str) -> Episode: return self._get(self.data.episode, episode_id, "episode")
    async def save_episode(self, episode_id: str, episode_no: int, title: str, content: dict[str, Any]) -> Episode:
        existing = self._get(self.data.episode, episode_id, "episode")
        self.data.episode = Episode(id=episode_id, script_id=existing.script_id, episode_no=episode_no, title=title, content=content)
        return self.data.episode
    async def list_episodes(self, script_id: str, episode_no: int | None = None, title: str | None = None) -> list[Episode]:
        episode = self.data.episode
        return [episode] if episode.script_id == script_id and (episode_no is None or episode.episode_no == episode_no) and (title is None or title.lower() in episode.title.lower()) else []

    async def create_scene(self, episode_id: str, order: int, title: str, content: dict[str, Any], location: str | None = None) -> Scene:
        self.data.scene = Scene(id="scene-new", episode_id=episode_id, order=order, title=title, location=location, content=content); return self.data.scene
    async def get_scene(self, scene_id: str) -> Scene: return self._get(self.data.scene, scene_id, "scene")
    async def save_scene(self, scene_id: str, order: int, title: str, content: dict[str, Any], location: str | None = None) -> Scene:
        existing = self._get(self.data.scene, scene_id, "scene")
        self.data.scene = Scene(id=scene_id, episode_id=existing.episode_id, order=order, title=title, location=location, content=content)
        return self.data.scene
    async def list_scenes(self, episode_id: str, order: int | None = None, location: str | None = None, character: str | None = None) -> list[Scene]:
        scene = self.data.scene
        return [scene] if scene.episode_id == episode_id and (order is None or scene.order == order) and (location is None or self._matches(location, scene.location)) and (character is None or self._matches(character, scene.content)) else []
    async def search_scenes(self, query: str, episode_id: str | None = None) -> list[Scene]:
        scene = self.data.scene
        return [scene] if (episode_id is None or scene.episode_id == episode_id) and self._matches(query, scene.title, scene.location, scene.content) else []

    async def create_shot(self, scene_id: str, shot_no: str, content: dict[str, Any], title: str | None = None, shot_type: str | None = None) -> Shot:
        self.data.shot = Shot(id="shot-new", scene_id=scene_id, shot_no=shot_no, title=title, shot_type=shot_type, content=content); return self.data.shot
    async def get_shot(self, shot_id: str) -> Shot: return self._get(self.data.shot, shot_id, "shot")
    async def save_shot(self, shot_id: str, shot_no: str, content: dict[str, Any], title: str | None = None, shot_type: str | None = None) -> Shot:
        existing = self._get(self.data.shot, shot_id, "shot")
        self.data.shot = Shot(id=shot_id, scene_id=existing.scene_id, shot_no=shot_no, title=title, shot_type=shot_type, content=content)
        return self.data.shot
    async def list_shots(self, scene_id: str, shot_no: str | None = None, shot_type: str | None = None, character: str | None = None) -> list[Shot]:
        shot = self.data.shot
        return [shot] if shot.scene_id == scene_id and (shot_no is None or shot.shot_no == shot_no) and (shot_type is None or shot.shot_type == shot_type) and (character is None or self._matches(character, shot.content)) else []
    async def search_shots(self, query: str, scene_id: str | None = None) -> list[Shot]:
        shot = self.data.shot
        return [shot] if (scene_id is None or shot.scene_id == scene_id) and self._matches(query, shot.title, shot.content) else []

    @staticmethod
    def _get(value: T, requested_id: str, kind: str) -> T:
        if value.id != requested_id: raise ProviderError(f"Mock {kind} not found: {requested_id}")
        return value

    @staticmethod
    def _matches(query: str, *values: object) -> bool:
        return query.casefold() in " ".join(str(value) for value in values if value is not None).casefold()


class MockAssetProvider:
    def __init__(self, data: MockDramaData) -> None: self.data = data
    async def create_asset(self, work_id: str, asset_type: AssetType, name: str, content: dict[str, Any], episode_id: str | None = None, scene_id: str | None = None, shot_id: str | None = None, description: str | None = None, reference_media_ids: list[str] | None = None) -> Asset:
        asset = Asset(id="asset-new", work_id=work_id, episode_id=episode_id, scene_id=scene_id, shot_id=shot_id, asset_type=asset_type, name=name, description=description, reference_media_ids=reference_media_ids or [], content=content); self.data.assets.append(asset); return asset
    async def get_asset(self, asset_id: str) -> Asset:
        match = next((item for item in self.data.assets if item.id == asset_id), None)
        if match is None: raise ProviderError(f"Mock asset not found: {asset_id}")
        return match
    async def save_asset(self, asset_id: str, name: str, content: dict[str, Any], description: str | None = None, reference_media_ids: list[str] | None = None) -> Asset:
        existing = await self.get_asset(asset_id)
        asset = existing.model_copy(update={"name": name, "description": description, "reference_media_ids": reference_media_ids or [], "content": content})
        self.data.assets = [asset if item.id == asset_id else item for item in self.data.assets]
        return asset
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
    async def create_media(self, work_id: str, media_type: MediaType, source_ref: str, content: dict[str, Any], asset_id: str | None = None, shot_id: str | None = None, purpose: str | None = None) -> Media:
        media = Media(id="media-new", work_id=work_id, asset_id=asset_id, shot_id=shot_id, media_type=media_type, purpose=purpose, source_ref=source_ref, content=content); self.data.media.append(media); return media
    async def get_media(self, media_id: str) -> Media:
        match = next((item for item in self.data.media if item.id == media_id), None)
        if match is None: raise ProviderError(f"Mock media not found: {media_id}")
        return match
    async def save_media(self, media_id: str, content: dict[str, Any], purpose: str | None = None) -> Media:
        existing = await self.get_media(media_id)
        media = existing.model_copy(update={"purpose": purpose, "content": content})
        self.data.media = [media if item.id == media_id else item for item in self.data.media]
        return media
    async def list_media(self, media_type: MediaType | None = None, work_id: str | None = None, purpose: str | None = None, source_ref: str | None = None) -> list[Media]:
        return [item for item in self.data.media if (media_type is None or item.media_type is media_type) and (work_id is None or item.work_id == work_id) and (purpose is None or item.purpose == purpose) and (source_ref is None or item.source_ref == source_ref)]
    async def import_media(self, work_id: str, media_type: MediaType, source_uri: str, content: dict[str, Any], asset_id: str | None = None, shot_id: str | None = None, purpose: str | None = None, source_ref: str | None = None, duration_ms: int | None = None) -> Media:
        media = Media(id="media-imported", work_id=work_id, asset_id=asset_id, shot_id=shot_id, media_type=media_type, purpose=purpose, source_ref=source_ref or "mock:storage:imported", duration_ms=duration_ms, content=content)
        self.data.media.append(media)
        return media
    async def resolve_media(self, media_id: str) -> MediaResolveResult:
        await self.get_media(media_id)
        return MediaResolveResult(media_id=media_id, url=f"https://mock.invalid/media/{media_id}", expires_at=datetime.now(UTC) + timedelta(minutes=15), mime_type="application/octet-stream", size_bytes=0)
    async def download_media(self, media_id: str, destination: Path) -> MediaResolveResult:
        resolved = await self.resolve_media(media_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"mock-media")
        return resolved
    async def restore_media_object(self, media_id: str, source_uri: str) -> MediaRestoreResult:
        await self.get_media(media_id)
        return MediaRestoreResult(media_id=media_id, status=MediaRestoreStatus.ALREADY_PRESENT, content_hash="mock", mime_type="application/octet-stream", size_bytes=0)


class MockProductionProvider:
    def __init__(self, data: MockDramaData) -> None: self.data = data
    async def generate_image(self, prompt: str, reference_asset_ids: list[str] | None = None, reference_media_ids: list[str] | None = None, parameters: dict[str, Any] | None = None) -> Media:
        return await self._result(MediaType.IMAGE, "image/png", prompt, reference_media_ids)
    async def generate_video(self, prompt: str, start_frame_media_id: str | None = None, end_frame_media_id: str | None = None, reference_media_ids: list[str] | None = None, parameters: dict[str, Any] | None = None) -> Media:
        refs = [item for item in [start_frame_media_id, end_frame_media_id, *(reference_media_ids or [])] if item]; return await self._result(MediaType.VIDEO, "video/mp4", prompt, refs)
    async def _result(self, media_type: MediaType, mime_type: str, prompt: str, refs: list[str] | None, parameters: dict[str, Any] | None = None) -> Media:
        media = Media(id=f"media-generated-{media_type.value.lower()}", work_id=self.data.work.id, media_type=media_type, purpose="GENERATED_OUTPUT", source_ref=f"mock:generated:{media_type.value.lower()}", content={"mime_type": mime_type, "prompt": prompt, "reference_media_ids": refs or [], "parameters": parameters or {}}); self.data.media.append(media); return media


class MockVoiceProvider:
    def __init__(self, data: MockDramaData) -> None: self.data = data

    async def import_voice(self, name: str, source_type: VoiceSourceType, source_uri: str, duration_ms: int, content: VoiceContent) -> Voice:
        payload = b"mock-voice"
        voice = Voice(id=f"voice-{len(self.data.voices) + 1}", name=name, source_type=source_type,
                      status=VoiceStatus.ACTIVE,
                      mime_type="audio/wav", file_size=len(payload), duration_ms=duration_ms,
                      content_hash=hashlib.sha256(payload).hexdigest(), content=content, version=1)
        self.data.voices.append(voice); return voice

    async def get_voice(self, voice_id: str) -> Voice:
        match = next((item for item in self.data.voices if item.id == voice_id), None)
        if match is None: raise ProviderError(f"Mock voice not found: {voice_id}")
        return match

    async def search_voices(self, query: str | None = None, status: VoiceStatus | None = None) -> list[Voice]:
        return [item for item in self.data.voices if (query is None or query.casefold() in item.name.casefold()) and (status is None or item.status is status)]

    async def update_voice(self, voice_id: str, content: VoiceContent, expected_version: int, name: str | None = None, status: VoiceStatus | None = None) -> Voice:
        current = await self.get_voice(voice_id)
        if current.version != expected_version: raise ProviderError("Mock voice version changed")
        changed = current.model_copy(update={"content": content, "name": name or current.name,
                                             "status": status or current.status, "version": current.version + 1})
        self.data.voices = [changed if item.id == voice_id else item for item in self.data.voices]
        return changed

    async def resolve_voice(self, voice_id: str) -> VoiceResolveResult:
        voice = await self.get_voice(voice_id)
        return VoiceResolveResult(voice_id=voice.id, url=f"https://mock.invalid/voice/{voice.id}",
                                  expires_at=datetime.now(UTC) + timedelta(minutes=15),
                                  mime_type=voice.mime_type, size_bytes=voice.file_size,
                                  content_hash=voice.content_hash)

    async def download_voice(self, voice_id: str, destination: Path) -> VoiceResolveResult:
        resolved = await self.resolve_voice(voice_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"mock-voice")
        return resolved
