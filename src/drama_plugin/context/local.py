from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from drama_plugin.contracts.context import (
    AssetContext,
    ContextBuildRequest,
    ContextChange,
    ContextPurpose,
    ContextScope,
    DramaContextPatch,
    DramaModelContext,
    EntityContext,
    GenerationContext,
)
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.generation import GenerationTarget
from drama_plugin.exceptions import ContextBuildError
from drama_plugin.providers.base import AssetProvider, GenerationProvider, HistoryProvider, ProjectProvider

ScopeHandler = Callable[[ContextBuildRequest], Awaitable[DramaModelContext]]
Projection = Callable[[DramaModelContext, ContextBuildRequest], DramaModelContext]


class PurposeProjectionRegistry:
    """Extensible purpose projection registry; unknown purposes receive the default projection."""

    def __init__(self) -> None:
        self._projections: dict[str, Projection] = {}

    def register(self, purpose: str, projection: Projection) -> None:
        self._projections[purpose] = projection

    def apply(self, context: DramaModelContext, request: ContextBuildRequest) -> DramaModelContext:
        projection = self._projections.get(str(request.purpose), self._default)
        return projection(context, request)

    @staticmethod
    def _default(context: DramaModelContext, request: ContextBuildRequest) -> DramaModelContext:
        constraints = {**context.constraints, "purpose": str(request.purpose)}
        return context.model_copy(update={"constraints": constraints})


class LocalContextProvider:
    """Compose domain providers into a model-facing context payload."""

    def __init__(
        self,
        project: ProjectProvider,
        asset: AssetProvider,
        history: HistoryProvider,
        generation: GenerationProvider,
        projections: PurposeProjectionRegistry | None = None,
    ) -> None:
        self.project = project
        self.asset = asset
        self.history = history
        self.generation = generation
        self.projections = projections or PurposeProjectionRegistry()
        for purpose in ContextPurpose:
            self.projections.register(purpose.value, PurposeProjectionRegistry._default)
        self._scope_handlers: dict[ContextScope, ScopeHandler] = {
            ContextScope.PROJECT: self._project_context,
            ContextScope.STORY: self._story_context,
            ContextScope.EPISODE: self._episode_context,
            ContextScope.SCENE: self._scene_context,
            ContextScope.SHOT: self._shot_context,
            ContextScope.ASSET: self._asset_context,
            ContextScope.HISTORICAL: self._historical_context,
        }

    async def build_context(self, request: ContextBuildRequest) -> DramaModelContext:
        try:
            context = await self._scope_handlers[request.scope](request)
            return self.projections.apply(context, request)
        except ContextBuildError:
            raise
        except Exception as exc:
            raise ContextBuildError(f"Cannot build {request.scope} context for {request.resource_id}") from exc

    async def refresh_context(self, request: ContextBuildRequest, current: DramaModelContext) -> DramaContextPatch:
        rebuilt = await self.build_context(request)
        before = dump_contract(current, exclude={"version", "built_at"})
        after = dump_contract(rebuilt, exclude={"version", "built_at"})
        changes: list[ContextChange] = []
        for key in sorted(set(before) | set(after)):
            if key not in after:
                changes.append(ContextChange(operation="remove", path=f"/{key}"))
            elif key not in before:
                changes.append(ContextChange(operation="add", path=f"/{key}", value=after[key]))
            elif before[key] != after[key]:
                changes.append(ContextChange(operation="replace", path=f"/{key}", value=after[key]))
        return DramaContextPatch(
            context_id=current.context_id,
            base_version=current.version,
            new_version=current.version + 1,
            changes=changes,
        )

    def _empty(self, request: ContextBuildRequest, **values: Any) -> DramaModelContext:
        return DramaModelContext(
            context_id=f"drama:{request.scope.value.lower()}:{request.resource_id}",
            version=1,
            scope=request.scope,
            purpose=str(request.purpose),
            **values,
        )

    async def _entities(self, resource_id: str) -> EntityContext:
        return EntityContext(
            characters=await self.project.list_characters(resource_id),
            locations=await self.project.list_locations(resource_id),
            props=await self.project.list_props(resource_id),
        )

    async def _project_context(self, request: ContextBuildRequest) -> DramaModelContext:
        project = await self.project.get_project(request.resource_id)
        return self._empty(request, project=project, entities=await self._entities(project.id))

    async def _story_context(self, request: ContextBuildRequest) -> DramaModelContext:
        story = await self.project.get_story(request.resource_id)
        project = await self.project.get_project(story.project_id)
        return self._empty(request, project=project, story=story, entities=await self._entities(story.id))

    async def _episode_context(self, request: ContextBuildRequest) -> DramaModelContext:
        episode = await self.project.get_episode(request.resource_id)
        story = await self.project.get_story(episode.story_id)
        project = await self.project.get_project(story.project_id)
        return self._empty(request, project=project, story=story, episode=episode, entities=await self._entities(episode.id))

    async def _scene_context(self, request: ContextBuildRequest) -> DramaModelContext:
        scene = await self.project.get_scene(request.resource_id)
        episode = await self.project.get_episode(scene.episode_id)
        story = await self.project.get_story(episode.story_id)
        project = await self.project.get_project(story.project_id)
        hierarchy = await self.asset.resolve_asset_hierarchy(scene_id=scene.id)
        evidence = await self.history.search_historical_location(scene.heading)
        return self._empty(request, project=project, story=story, episode=episode, scene=scene, entities=await self._entities(scene.id), assets=AssetContext(**hierarchy.model_dump()), historical_evidence=evidence)

    async def _shot_context(self, request: ContextBuildRequest) -> DramaModelContext:
        shot = await self.project.get_shot(request.resource_id)
        scene = await self.project.get_scene(shot.scene_id)
        episode = await self.project.get_episode(scene.episode_id)
        story = await self.project.get_story(episode.story_id)
        project = await self.project.get_project(story.project_id)
        hierarchy = await self.asset.resolve_asset_hierarchy(scene_id=scene.id, shot_id=shot.id)
        evidence = await self.history.search_historical_person(" ".join(shot.character_ids))
        plan = await self.generation.create_generation_plan(GenerationTarget.SHOT_VIDEO, shot.id)
        state = await self.generation.get_generation_status(plan.id)
        return self._empty(request, project=project, story=story, episode=episode, scene=scene, shot=shot, entities=await self._entities(shot.id), assets=AssetContext(**hierarchy.model_dump()), historical_evidence=evidence, generation=GenerationContext(plans=[plan], state=state))

    async def _asset_context(self, request: ContextBuildRequest) -> DramaModelContext:
        asset = await self.asset.get_asset(request.resource_id)
        hierarchy = await self.asset.resolve_asset_hierarchy()
        assets = AssetContext(**hierarchy.model_dump())
        if asset.level.value == "BASE" and asset not in assets.base:
            assets.base.append(asset)
        return self._empty(request, assets=assets)

    async def _historical_context(self, request: ContextBuildRequest) -> DramaModelContext:
        evidence = await self.history.search_historical_event(request.resource_id)
        return self._empty(request, historical_evidence=evidence)
