from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from drama_plugin.contracts.asset import Asset, AssetType
from drama_plugin.contracts.context import ContextBuildRequest, DramaContextPatch, DramaRunContext
from drama_plugin.contracts.creation import Episode, Scene, Script, Shot, Work
from drama_plugin.contracts.media import Media, MediaResolveResult, MediaType
from drama_plugin.contracts.research import ClaimAssessment, ResearchEvidence, ResearchSource
from drama_plugin.providers.base import AssetProvider, ContextProvider, MediaProvider, MemoryProvider, ProductionProvider, ResearchProvider
from drama_plugin.tools.registry import ToolDefinition, ToolHandler, ToolRegistry, tool
from drama_plugin.tools.schemas import object_schema, schema_for


def _domain_tool(code: str, description: str, handler: ToolHandler, output: Any, *, required: Mapping[str, Any] | None = None, optional: Mapping[str, Any] | None = None, defaults: Mapping[str, Any] | None = None) -> ToolDefinition:
    return tool(code, description, handler, input_schema=object_schema(required=required, optional=optional, defaults=defaults), output_schema=schema_for(output))


def build_tool_registry(memory: MemoryProvider, asset: AssetProvider, research: ResearchProvider, production: ProductionProvider, media: MediaProvider, context: ContextProvider) -> ToolRegistry:
    registry = ToolRegistry()
    specs = [
        _domain_tool("work.create_work", "Create a complete initial work as persistent memory.", memory.create_work, Work, required={"title": str, "content": dict[str, Any]}, optional={"description": str | None}),
        _domain_tool("work.get_work", "Read a work by stable ID.", memory.get_work, Work, required={"work_id": str}),
        _domain_tool("work.save_work", "Replace the formal state of an existing work revision.", memory.save_work, Work, required={"work_id": str, "title": str, "content": dict[str, Any]}, optional={"description": str | None}),
        _domain_tool("work.list_works", "List works in the available structural scope.", memory.list_works, list[Work]),
        _domain_tool("work.search_works", "Discover works when the stable ID is unknown, using a natural-language query.", memory.search_works, list[Work], required={"query": str}),
        _domain_tool("script.create_script", "Create a complete initial script under a work.", memory.create_script, Script, required={"work_id": str, "title": str, "content": dict[str, Any]}),
        _domain_tool("script.get_script", "Read a script by stable ID.", memory.get_script, Script, required={"script_id": str}),
        _domain_tool("script.save_script", "Replace the formal state of an existing script revision.", memory.save_script, Script, required={"script_id": str, "title": str, "content": dict[str, Any]}),
        _domain_tool("script.list_scripts", "List scripts under a work.", memory.list_scripts, list[Script], required={"work_id": str}),
        _domain_tool("episode.create_episode", "Create a complete initial episode under a script.", memory.create_episode, Episode, required={"script_id": str, "episode_no": int, "title": str, "content": dict[str, Any]}),
        _domain_tool("episode.get_episode", "Read an episode by stable ID.", memory.get_episode, Episode, required={"episode_id": str}),
        _domain_tool("episode.save_episode", "Replace the formal state of an existing episode revision.", memory.save_episode, Episode, required={"episode_id": str, "episode_no": int, "title": str, "content": dict[str, Any]}),
        _domain_tool("episode.list_episodes", "List episodes under a script with optional episode number or title filters.", memory.list_episodes, list[Episode], required={"script_id": str}, optional={"episode_no": int | None, "title": str | None}),
        _domain_tool("scene.create_scene", "Create a complete initial scene under an episode.", memory.create_scene, Scene, required={"episode_id": str, "order": int, "title": str, "content": dict[str, Any]}, optional={"location": str | None}),
        _domain_tool("scene.get_scene", "Read a scene by stable ID.", memory.get_scene, Scene, required={"scene_id": str}),
        _domain_tool("scene.save_scene", "Replace the formal state of an existing scene revision.", memory.save_scene, Scene, required={"scene_id": str, "order": int, "title": str, "content": dict[str, Any]}, optional={"location": str | None}),
        _domain_tool("scene.list_scenes", "List scenes under an episode with optional structural filters.", memory.list_scenes, list[Scene], required={"episode_id": str}, optional={"order": int | None, "location": str | None, "character": str | None}),
        _domain_tool("scene.search_scenes", "Discover scenes when the stable ID is unknown, optionally scoped to an episode.", memory.search_scenes, list[Scene], required={"query": str}, optional={"episode_id": str | None}),
        _domain_tool("shot.create_shot", "Create a complete initial shot under a scene.", memory.create_shot, Shot, required={"scene_id": str, "shot_no": str, "content": dict[str, Any]}, optional={"title": str | None, "shot_type": str | None}),
        _domain_tool("shot.get_shot", "Read a shot by stable ID.", memory.get_shot, Shot, required={"shot_id": str}),
        _domain_tool("shot.save_shot", "Replace the formal state of an existing shot revision.", memory.save_shot, Shot, required={"shot_id": str, "shot_no": str, "content": dict[str, Any]}, optional={"title": str | None, "shot_type": str | None}),
        _domain_tool("shot.list_shots", "List shots under a scene with optional structural filters.", memory.list_shots, list[Shot], required={"scene_id": str}, optional={"shot_no": str | None, "shot_type": str | None, "character": str | None}),
        _domain_tool("shot.search_shots", "Discover shots when the stable ID is unknown, optionally scoped to a scene.", memory.search_shots, list[Shot], required={"query": str}, optional={"scene_id": str | None}),
        _domain_tool("asset.create_asset", "Register a complete agent-approved stable reusable asset.", asset.create_asset, Asset, required={"work_id": str, "asset_type": AssetType, "name": str, "content": dict[str, Any]}, optional={"episode_id": str | None, "scene_id": str | None, "shot_id": str | None, "description": str | None, "reference_media_ids": list[str]}, defaults={"reference_media_ids": []}),
        _domain_tool("asset.get_asset", "Read an asset by stable ID.", asset.get_asset, Asset, required={"asset_id": str}),
        _domain_tool("asset.save_asset", "Replace the mutable formal state of an existing asset revision.", asset.save_asset, Asset, required={"asset_id": str, "name": str, "content": dict[str, Any]}, optional={"description": str | None, "reference_media_ids": list[str]}, defaults={"reference_media_ids": []}),
        _domain_tool("asset.list_assets", "List assets with an optional type filter.", asset.list_assets, list[Asset], optional={"asset_type": AssetType | None}),
        _domain_tool("asset.search_assets", "Discover reusable assets by semantic query and optional type.", asset.search_assets, list[Asset], required={"query": str}, optional={"asset_type": AssetType | None}),
        _domain_tool("media.create_media", "Register a complete stable opaque physical media reference.", media.create_media, Media, required={"work_id": str, "media_type": MediaType, "source_ref": str, "content": dict[str, Any]}, optional={"asset_id": str | None, "shot_id": str | None, "purpose": str | None}),
        _domain_tool("media.get_media", "Read media metadata by stable ID.", media.get_media, Media, required={"media_id": str}),
        _domain_tool("media.save_media", "Replace the mutable formal state of an existing media revision.", media.save_media, Media, required={"media_id": str, "content": dict[str, Any]}, optional={"purpose": str | None}),
        _domain_tool("media.list_media", "List media with an optional type filter.", media.list_media, list[Media], optional={"media_type": MediaType | None}),
        _domain_tool("media.import_media", "Import an external media source into durable Drama-managed storage.", media.import_media, Media, required={"work_id": str, "media_type": MediaType, "source_uri": str, "content": dict[str, Any]}, optional={"asset_id": str | None, "shot_id": str | None, "purpose": str | None}),
        _domain_tool("media.resolve_media", "Resolve durable Drama-managed media to a temporary consumable URL.", media.resolve_media, MediaResolveResult, required={"media_id": str}),
        _domain_tool("production.generate_image", "Generate an image from business-level prompt and stable references.", production.generate_image, Media, required={"prompt": str}, optional={"reference_asset_ids": list[str] | None, "reference_media_ids": list[str] | None, "parameters": dict[str, Any] | None}),
        _domain_tool("production.generate_video", "Generate a video from business-level prompt and stable media references.", production.generate_video, Media, required={"prompt": str}, optional={"start_frame_media_id": str | None, "end_frame_media_id": str | None, "reference_media_ids": list[str] | None, "parameters": dict[str, Any] | None}),
        _domain_tool("production.generate_audio", "Generate audio from a business-level prompt and stable references.", production.generate_audio, Media, required={"prompt": str}, optional={"reference_media_ids": list[str] | None, "parameters": dict[str, Any] | None}),
        _domain_tool("research.search_sources", "Search external historical sources for the current run.", research.search_sources, list[ResearchSource], required={"query": str}),
        _domain_tool("research.search_events", "Search historical event evidence for the current run.", research.search_events, list[ResearchEvidence], required={"query": str}),
        _domain_tool("research.search_people", "Search historical person evidence for the current run.", research.search_people, list[ResearchEvidence], required={"query": str}),
        _domain_tool("research.search_locations", "Search historical location evidence for the current run.", research.search_locations, list[ResearchEvidence], required={"query": str}),
        _domain_tool("research.verify_claim", "Assess a claim against available historical evidence.", research.verify_claim, ClaimAssessment, required={"claim": str}),
        _domain_tool("context.build_context", "Build a minimal DramaRunContext; the host owns run context.", context.build_context, DramaRunContext, required={"request": ContextBuildRequest}),
        _domain_tool("context.refresh_context", "Build a DramaContextPatch; the host owns merging.", context.refresh_context, DramaContextPatch, required={"request": ContextBuildRequest, "current": DramaRunContext}),
    ]
    for definition in specs: registry.register(definition)
    return registry
