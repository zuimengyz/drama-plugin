from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, TypeAdapter

from drama_plugin.contracts.asset import Asset, AssetType
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.context import ContextBuildRequest, DramaContextPatch, DramaRunContext
from drama_plugin.contracts.creation import Episode, Scene, Script, Shot, Work
from drama_plugin.contracts.media import Media, MediaResolveResult, MediaRestoreResult, MediaType
from drama_plugin.contracts.research import ClaimAssessment, ResearchEvidence, ResearchSource
from drama_plugin.exceptions import ContractValidationError
from drama_plugin.audio.host_media import validate_media_mime
from drama_plugin.providers.http.client import HttpProviderClient
from drama_plugin.providers.http.media_source import open_media_source

T = TypeVar("T", bound=BaseModel)


def _one(model: type[T], payload: Any) -> T:
    try: return model.model_validate(payload)
    except Exception as exc: raise ContractValidationError(f"Remote payload does not match {model.__name__}") from exc


def _many(model: type[T], payload: Any) -> list[T]:
    try: return TypeAdapter(list[model]).validate_python(payload)  # type: ignore[valid-type]
    except Exception as exc: raise ContractValidationError(f"Remote payload does not match list[{model.__name__}]") from exc


class HttpMemoryProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def _create(self, operation: str, model: type[T], body: dict[str, Any]) -> T: return _one(model, await self.http.request(operation, method="POST", json=body))
    async def create_work(self, title: str, content: dict[str, Any], description: str | None = None) -> Work: return await self._create("create_work", Work, {"title": title, "description": description, "content": content})
    async def get_work(self, work_id: str) -> Work: return _one(Work, await self.http.request("get_work", params={"work_id": work_id}))
    async def save_work(self, work_id: str, title: str, content: dict[str, Any], description: str | None = None) -> Work: return await self._create("save_work", Work, {"work_id": work_id, "title": title, "description": description, "content": content})
    async def list_works(self) -> list[Work]: return _many(Work, await self.http.request("list_works"))
    async def search_works(self, query: str) -> list[Work]: return _many(Work, await self.http.request("search_works", params={"query": query}))
    async def create_script(self, work_id: str, title: str, content: dict[str, Any]) -> Script: return await self._create("create_script", Script, {"work_id": work_id, "title": title, "content": content})
    async def get_script(self, script_id: str) -> Script: return _one(Script, await self.http.request("get_script", params={"script_id": script_id}))
    async def save_script(self, script_id: str, title: str, content: dict[str, Any]) -> Script: return await self._create("save_script", Script, {"script_id": script_id, "title": title, "content": content})
    async def list_scripts(self, work_id: str) -> list[Script]: return _many(Script, await self.http.request("list_scripts", params={"work_id": work_id}))
    async def create_episode(self, script_id: str, episode_no: int, title: str, content: dict[str, Any]) -> Episode: return await self._create("create_episode", Episode, {"script_id": script_id, "episode_no": episode_no, "title": title, "content": content})
    async def get_episode(self, episode_id: str) -> Episode: return _one(Episode, await self.http.request("get_episode", params={"episode_id": episode_id}))
    async def save_episode(self, episode_id: str, episode_no: int, title: str, content: dict[str, Any]) -> Episode: return await self._create("save_episode", Episode, {"episode_id": episode_id, "episode_no": episode_no, "title": title, "content": content})
    async def list_episodes(self, script_id: str, episode_no: int | None = None, title: str | None = None) -> list[Episode]: return _many(Episode, await self.http.request("list_episodes", params={"script_id": script_id, "episode_no": episode_no, "title": title}))
    async def create_scene(self, episode_id: str, order: int, title: str, content: dict[str, Any], location: str | None = None) -> Scene: return await self._create("create_scene", Scene, {"episode_id": episode_id, "order": order, "title": title, "location": location, "content": content})
    async def get_scene(self, scene_id: str) -> Scene: return _one(Scene, await self.http.request("get_scene", params={"scene_id": scene_id}))
    async def save_scene(self, scene_id: str, order: int, title: str, content: dict[str, Any], location: str | None = None) -> Scene: return await self._create("save_scene", Scene, {"scene_id": scene_id, "order": order, "title": title, "location": location, "content": content})
    async def list_scenes(self, episode_id: str, order: int | None = None, location: str | None = None, character: str | None = None) -> list[Scene]: return _many(Scene, await self.http.request("list_scenes", params={"episode_id": episode_id, "order": order, "location": location, "character": character}))
    async def search_scenes(self, query: str, episode_id: str | None = None) -> list[Scene]: return _many(Scene, await self.http.request("search_scenes", params={"query": query, "episode_id": episode_id}))
    async def create_shot(self, scene_id: str, shot_no: str, content: dict[str, Any], title: str | None = None, shot_type: str | None = None) -> Shot: return await self._create("create_shot", Shot, {"scene_id": scene_id, "shot_no": shot_no, "title": title, "shot_type": shot_type, "content": content})
    async def get_shot(self, shot_id: str) -> Shot: return _one(Shot, await self.http.request("get_shot", params={"shot_id": shot_id}))
    async def save_shot(self, shot_id: str, shot_no: str, content: dict[str, Any], title: str | None = None, shot_type: str | None = None) -> Shot: return await self._create("save_shot", Shot, {"shot_id": shot_id, "shot_no": shot_no, "title": title, "shot_type": shot_type, "content": content})
    async def list_shots(self, scene_id: str, shot_no: str | None = None, shot_type: str | None = None, character: str | None = None) -> list[Shot]:
        optional = {"shot_no": shot_no, "shot_type": shot_type, "character": character}
        params = {"scene_id": scene_id, **{key: value for key, value in optional.items() if value is not None}}
        return _many(Shot, await self.http.request("list_shots", params=params))
    async def search_shots(self, query: str, scene_id: str | None = None) -> list[Shot]: return _many(Shot, await self.http.request("search_shots", params={"query": query, "scene_id": scene_id}))


class HttpAssetProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def create_asset(self, work_id: str, asset_type: AssetType, name: str, content: dict[str, Any], episode_id: str | None = None, scene_id: str | None = None, shot_id: str | None = None, description: str | None = None, reference_media_ids: list[str] | None = None) -> Asset: return _one(Asset, await self.http.request("create_asset", method="POST", json={"work_id": work_id, "episode_id": episode_id, "scene_id": scene_id, "shot_id": shot_id, "asset_type": asset_type, "name": name, "description": description, "reference_media_ids": reference_media_ids or [], "content": content}))
    async def get_asset(self, asset_id: str) -> Asset: return _one(Asset, await self.http.request("get_asset", params={"asset_id": asset_id}))
    async def save_asset(self, asset_id: str, name: str, content: dict[str, Any], description: str | None = None, reference_media_ids: list[str] | None = None) -> Asset: return _one(Asset, await self.http.request("save_asset", method="POST", json={"asset_id": asset_id, "name": name, "description": description, "reference_media_ids": reference_media_ids or [], "content": content}))
    async def list_assets(self, asset_type: AssetType | None = None) -> list[Asset]: return _many(Asset, await self.http.request("list_assets", params={"asset_type": asset_type}))
    async def search_assets(self, query: str, asset_type: AssetType | None = None) -> list[Asset]: return _many(Asset, await self.http.request("search_assets", params={"query": query, "asset_type": asset_type}))


class HttpResearchProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def search_sources(self, query: str) -> list[ResearchSource]: return _many(ResearchSource, await self.http.request("search_sources", params={"query": query}))
    async def search_events(self, query: str) -> list[ResearchEvidence]: return _many(ResearchEvidence, await self.http.request("search_events", params={"query": query}))
    async def search_people(self, query: str) -> list[ResearchEvidence]: return _many(ResearchEvidence, await self.http.request("search_people", params={"query": query}))
    async def search_locations(self, query: str) -> list[ResearchEvidence]: return _many(ResearchEvidence, await self.http.request("search_locations", params={"query": query}))
    async def verify_claim(self, claim: str) -> ClaimAssessment: return _one(ClaimAssessment, await self.http.request("verify_claim", method="POST", json={"claim": claim}))


class HttpProductionProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def generate_image(self, prompt: str, reference_asset_ids: list[str] | None = None, reference_media_ids: list[str] | None = None, parameters: dict[str, Any] | None = None) -> Media: return _one(Media, await self.http.request("generate_image", method="POST", json={"prompt": prompt, "referenceAssetIds": reference_asset_ids or [], "referenceMediaIds": reference_media_ids or [], "parameters": parameters or {}}))
    async def generate_video(self, prompt: str, start_frame_media_id: str | None = None, end_frame_media_id: str | None = None, reference_media_ids: list[str] | None = None, parameters: dict[str, Any] | None = None) -> Media: return _one(Media, await self.http.request("generate_video", method="POST", json={"prompt": prompt, "startFrameMediaId": start_frame_media_id, "endFrameMediaId": end_frame_media_id, "referenceMediaIds": reference_media_ids or [], "parameters": parameters or {}}))
    async def generate_audio(self, prompt: str, reference_media_ids: list[str] | None = None, parameters: dict[str, Any] | None = None) -> Media: return _one(Media, await self.http.request("generate_audio", method="POST", json={"prompt": prompt, "referenceMediaIds": reference_media_ids or [], "parameters": parameters or {}}))


class HttpMediaProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def create_media(self, work_id: str, media_type: MediaType, source_ref: str, content: dict[str, Any], asset_id: str | None = None, shot_id: str | None = None, purpose: str | None = None) -> Media: return _one(Media, await self.http.request("create_media", method="POST", json={"work_id": work_id, "asset_id": asset_id, "shot_id": shot_id, "media_type": media_type, "purpose": purpose, "source_ref": source_ref, "content": content}))
    async def get_media(self, media_id: str) -> Media: return _one(Media, await self.http.request("get_media", params={"media_id": media_id}))
    async def save_media(self, media_id: str, content: dict[str, Any], purpose: str | None = None) -> Media: return _one(Media, await self.http.request("save_media", method="POST", json={"media_id": media_id, "purpose": purpose, "content": content}))
    async def list_media(self, media_type: MediaType | None = None, work_id: str | None = None, purpose: str | None = None, source_ref: str | None = None) -> list[Media]:
        optional = {"media_type": media_type, "work_id": work_id, "purpose": purpose, "source_ref": source_ref}
        return _many(Media, await self.http.request("list_media", params={key: value for key, value in optional.items() if value is not None}))
    async def import_media(self, work_id: str, media_type: MediaType, source_uri: str, content: dict[str, Any], asset_id: str | None = None, shot_id: str | None = None, purpose: str | None = None, source_ref: str | None = None, duration_ms: int | None = None) -> Media:
        metadata = {"work_id": work_id, "asset_id": asset_id, "shot_id": shot_id, "media_type": media_type, "purpose": purpose, "source_ref": source_ref, "duration_ms": duration_ms, "content": content}
        async with open_media_source(source_uri) as source:
            validate_media_mime(media_type, purpose, source.content_type)
            return _one(Media, await self.http.multipart_request("import_media", metadata=metadata, stream=source.stream, filename=source.filename, content_type=source.content_type))
    async def resolve_media(self, media_id: str) -> MediaResolveResult:
        return _one(MediaResolveResult, await self.http.request("resolve_media", params={"media_id": media_id}))
    async def restore_media_object(self, media_id: str, source_uri: str) -> MediaRestoreResult:
        async with open_media_source(source_uri) as source:
            return _one(MediaRestoreResult, await self.http.multipart_request(
                "restore_media_object",
                metadata={"media_id": media_id},
                stream=source.stream,
                filename=source.filename,
                content_type=source.content_type,
            ))


class RemoteContextProvider:
    def __init__(self, http: HttpProviderClient) -> None: self.http = http
    async def build_context(self, request: ContextBuildRequest) -> DramaRunContext: return _one(DramaRunContext, await self.http.request("build_context", method="POST", json=dump_contract(request)))
    async def refresh_context(self, request: ContextBuildRequest, current: DramaRunContext) -> DramaContextPatch: return _one(DramaContextPatch, await self.http.request("refresh_context", method="POST", json={"request": dump_contract(request), "currentContext": dump_contract(current)}))
