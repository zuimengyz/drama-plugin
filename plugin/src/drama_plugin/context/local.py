from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.context import ContextBuildRequest, ContextChange, ContextScope, DramaContextPatch, DramaRunContext
from drama_plugin.exceptions import ContextBuildError
from drama_plugin.providers.base import AssetProvider, MediaProvider, MemoryProvider

ScopeHandler = Callable[[ContextBuildRequest], Awaitable[DramaRunContext]]


class LocalContextProvider:
    """Build the smallest persistent-object chain needed for one agent task."""

    def __init__(self, memory: MemoryProvider, asset: AssetProvider, media: MediaProvider) -> None:
        self.memory = memory
        self.asset = asset
        self.media = media
        self._scope_handlers: dict[ContextScope, ScopeHandler] = {
            ContextScope.WORK: self._work_context,
            ContextScope.SCRIPT: self._script_context,
            ContextScope.EPISODE: self._episode_context,
            ContextScope.SCENE: self._scene_context,
            ContextScope.SHOT: self._shot_context,
            ContextScope.ASSET: self._asset_context,
            ContextScope.MEDIA: self._media_context,
        }

    async def build_context(self, request: ContextBuildRequest) -> DramaRunContext:
        try:
            return await self._scope_handlers[request.scope](request)
        except ContextBuildError:
            raise
        except Exception as exc:
            raise ContextBuildError(f"Cannot build {request.scope} context for {request.resource_id}") from exc

    async def refresh_context(self, request: ContextBuildRequest, current: DramaRunContext) -> DramaContextPatch:
        rebuilt = await self.build_context(request)
        before = dump_contract(current, exclude={"version", "built_at"})
        after = dump_contract(rebuilt, exclude={"version", "built_at"})
        changes: list[ContextChange] = []
        for key in sorted(set(before) | set(after)):
            if key not in after: changes.append(ContextChange(operation="remove", path=f"/{key}"))
            elif key not in before: changes.append(ContextChange(operation="add", path=f"/{key}", value=after[key]))
            elif before[key] != after[key]: changes.append(ContextChange(operation="replace", path=f"/{key}", value=after[key]))
        return DramaContextPatch(context_id=current.context_id, base_version=current.version, new_version=current.version + 1, changes=changes)

    def _empty(self, request: ContextBuildRequest, **values: Any) -> DramaRunContext:
        options = request.options
        return DramaRunContext(
            context_id=f"drama:{request.scope.value.lower()}:{request.resource_id}",
            version=1,
            scope=request.scope,
            purpose=str(request.purpose),
            selected_asset_ids=list(options.get("selectedAssetIds", options.get("selected_asset_ids", []))),
            generated_media_ids=list(options.get("generatedMediaIds", options.get("generated_media_ids", []))),
            research_context=dict(options.get("researchContext", options.get("research_context", {}))),
            temporary_state=dict(options.get("temporaryState", options.get("temporary_state", {}))),
            **values,
        )

    async def _work_context(self, request: ContextBuildRequest) -> DramaRunContext:
        return self._empty(request, work=await self.memory.get_work(request.resource_id))

    async def _script_context(self, request: ContextBuildRequest) -> DramaRunContext:
        script = await self.memory.get_script(request.resource_id)
        return self._empty(request, work=await self.memory.get_work(script.work_id), script=script)

    async def _episode_context(self, request: ContextBuildRequest) -> DramaRunContext:
        episode = await self.memory.get_episode(request.resource_id)
        script = await self.memory.get_script(episode.script_id)
        return self._empty(request, work=await self.memory.get_work(script.work_id), script=script, episode=episode)

    async def _scene_context(self, request: ContextBuildRequest) -> DramaRunContext:
        scene = await self.memory.get_scene(request.resource_id)
        episode = await self.memory.get_episode(scene.episode_id)
        script = await self.memory.get_script(episode.script_id)
        return self._empty(request, work=await self.memory.get_work(script.work_id), script=script, episode=episode, scene=scene)

    async def _shot_context(self, request: ContextBuildRequest) -> DramaRunContext:
        shot = await self.memory.get_shot(request.resource_id)
        scene = await self.memory.get_scene(shot.scene_id)
        episode = await self.memory.get_episode(scene.episode_id)
        script = await self.memory.get_script(episode.script_id)
        return self._empty(request, work=await self.memory.get_work(script.work_id), script=script, episode=episode, scene=scene, shot=shot)

    async def _asset_context(self, request: ContextBuildRequest) -> DramaRunContext:
        return self._empty(request, asset=await self.asset.get_asset(request.resource_id))

    async def _media_context(self, request: ContextBuildRequest) -> DramaRunContext:
        return self._empty(request, media=await self.media.get_media(request.resource_id))
