from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from drama_plugin.contracts.asset import Asset, AssetBinding, AssetHierarchy
from drama_plugin.contracts.context import ContextBuildRequest, DramaContextPatch, DramaModelContext
from drama_plugin.contracts.generation import (
    GenerationPlan,
    GenerationResult,
    GenerationState,
    GenerationTarget,
)
from drama_plugin.contracts.history import ClaimVerification, HistoricalEvidence, HistoricalSource
from drama_plugin.contracts.media import ImageMetadata, Media, VideoMetadata
from drama_plugin.contracts.project import Character, Episode, Location, Project, Prop, Scene, Shot, Story
from drama_plugin.providers.base import (
    AssetProvider,
    ContextProvider,
    GenerationProvider,
    HistoryProvider,
    MediaProvider,
    ProjectProvider,
)
from drama_plugin.tools.registry import ToolDefinition, ToolHandler, ToolRegistry, tool
from drama_plugin.tools.schemas import object_schema, schema_for


def _domain_tool(
    code: str,
    description: str,
    handler: ToolHandler,
    output: Any,
    *,
    required: Mapping[str, Any] | None = None,
    optional: Mapping[str, Any] | None = None,
) -> ToolDefinition:
    return tool(
        code,
        description,
        handler,
        input_schema=object_schema(required=required, optional=optional),
        output_schema=schema_for(output),
    )


def build_tool_registry(
    project: ProjectProvider,
    asset: AssetProvider,
    history: HistoryProvider,
    generation: GenerationProvider,
    media: MediaProvider,
    context: ContextProvider,
) -> ToolRegistry:
    registry = ToolRegistry()
    specs = [
        _domain_tool("project.get_project", "Read a drama project.", project.get_project, Project, required={"project_id": str}),
        _domain_tool("project.get_story", "Read a story.", project.get_story, Story, required={"story_id": str}),
        _domain_tool("project.get_episode", "Read an episode.", project.get_episode, Episode, required={"episode_id": str}),
        _domain_tool("project.list_episodes", "List story episodes.", project.list_episodes, list[Episode], required={"story_id": str}),
        _domain_tool("project.get_scene", "Read a scene.", project.get_scene, Scene, required={"scene_id": str}),
        _domain_tool("project.list_scenes", "List episode scenes.", project.list_scenes, list[Scene], required={"episode_id": str}),
        _domain_tool("project.get_shot", "Read a shot.", project.get_shot, Shot, required={"shot_id": str}),
        _domain_tool("project.list_shots", "List scene shots.", project.list_shots, list[Shot], required={"scene_id": str}),
        _domain_tool("project.list_characters", "List relevant characters.", project.list_characters, list[Character], required={"resource_id": str}),
        _domain_tool("project.list_locations", "List relevant locations.", project.list_locations, list[Location], required={"resource_id": str}),
        _domain_tool("project.list_props", "List relevant props.", project.list_props, list[Prop], required={"resource_id": str}),
        _domain_tool("asset.search_assets", "Search domain assets.", asset.search_assets, list[Asset], required={"query": str}),
        _domain_tool("asset.get_asset", "Read an asset.", asset.get_asset, Asset, required={"asset_id": str}),
        _domain_tool("asset.get_scene_asset_bindings", "Read scene asset bindings.", asset.get_scene_asset_bindings, list[AssetBinding], required={"scene_id": str}),
        _domain_tool("asset.get_shot_asset_bindings", "Read shot asset bindings.", asset.get_shot_asset_bindings, list[AssetBinding], required={"shot_id": str}),
        _domain_tool("asset.resolve_asset_hierarchy", "Resolve base, scene, shot, and effective assets.", asset.resolve_asset_hierarchy, AssetHierarchy, optional={"scene_id": str | None, "shot_id": str | None}),
        _domain_tool("history.search_sources", "Search historical sources.", history.search_sources, list[HistoricalSource], required={"query": str}),
        _domain_tool("history.search_historical_event", "Search historical event evidence.", history.search_historical_event, list[HistoricalEvidence], required={"query": str}),
        _domain_tool("history.search_historical_person", "Search historical person evidence.", history.search_historical_person, list[HistoricalEvidence], required={"query": str}),
        _domain_tool("history.search_historical_location", "Search historical location evidence.", history.search_historical_location, list[HistoricalEvidence], required={"query": str}),
        _domain_tool("history.get_evidence", "Read one evidence record.", history.get_evidence, HistoricalEvidence, required={"evidence_id": str}),
        _domain_tool("history.verify_claim", "Verify a claim against historical evidence.", history.verify_claim, ClaimVerification, required={"claim": str}),
        _domain_tool("generation.create_generation_plan", "Create a transport-neutral generation plan.", generation.create_generation_plan, GenerationPlan, required={"generation_target": GenerationTarget, "resource_id": str}, optional={"parameters": dict[str, Any] | None}),
        _domain_tool("generation.compile_generation_plan", "Compile a plan through the generation service.", generation.compile_generation_plan, GenerationPlan, required={"plan_id": str}),
        _domain_tool("generation.submit_generation", "Submit a compiled generation plan.", generation.submit_generation, GenerationState, required={"plan_id": str}),
        _domain_tool("generation.get_generation_status", "Read generation state.", generation.get_generation_status, GenerationState, required={"plan_id": str}),
        _domain_tool("generation.get_generation_result", "Read generation outputs.", generation.get_generation_result, GenerationResult, required={"plan_id": str}),
        _domain_tool("media.get_media", "Read media with semantic identity.", media.get_media, Media, required={"media_id": str}),
        _domain_tool("media.list_asset_media", "List media belonging to an asset.", media.list_asset_media, list[Media], required={"asset_id": str}),
        _domain_tool("media.get_image_metadata", "Read image technical metadata.", media.get_image_metadata, ImageMetadata, required={"media_id": str}),
        _domain_tool("media.get_video_metadata", "Read video technical metadata.", media.get_video_metadata, VideoMetadata, required={"media_id": str}),
        _domain_tool("context.build_context", "Build a DramaModelContext payload; the host owns insertion.", context.build_context, DramaModelContext, required={"request": ContextBuildRequest}),
        _domain_tool("context.refresh_context", "Build a DramaContextPatch payload; the host owns merging.", context.refresh_context, DramaContextPatch, required={"request": ContextBuildRequest, "current": DramaModelContext}),
    ]
    for definition in specs:
        registry.register(definition)
    return registry
