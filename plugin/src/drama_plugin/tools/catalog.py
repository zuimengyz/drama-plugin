from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import PositiveInt

from drama_plugin.contracts.asset import Asset, AssetType
from drama_plugin.contracts.audio import RoleDubbingRequest, RoleDubbingResult
from drama_plugin.contracts.context import ContextBuildRequest, DramaContextPatch, DramaRunContext
from drama_plugin.contracts.creation import Episode, Scene, Script, Shot, Work
from drama_plugin.contracts.media import Media, MediaResolveResult, MediaRestoreResult, MediaType
from drama_plugin.contracts.research import ClaimAssessment, ResearchEvidence, ResearchSource
from drama_plugin.contracts.voice import Voice, VoiceContent, VoiceResolveResult, VoiceSourceType, VoiceStatus
from drama_plugin.exceptions import ContractValidationError
from drama_plugin.providers.base import AssetProvider, ContextProvider, MediaProvider, MemoryProvider, ProductionProvider, ResearchProvider, RoleDubbingProvider, VoiceProvider
from drama_plugin.tools.registry import ToolDefinition, ToolHandler, ToolRegistry, tool
from drama_plugin.tools.schemas import object_schema, schema_for


def _domain_tool(code: str, description: str, handler: ToolHandler, output: Any, *, required: Mapping[str, Any] | None = None, optional: Mapping[str, Any] | None = None, defaults: Mapping[str, Any] | None = None) -> ToolDefinition:
    return tool(code, description, handler, input_schema=object_schema(required=required, optional=optional, defaults=defaults), output_schema=schema_for(output))


def build_tool_registry(memory: MemoryProvider, asset: AssetProvider, research: ResearchProvider, production: ProductionProvider, media: MediaProvider, context: ContextProvider, voice: VoiceProvider, role_dubbing: RoleDubbingProvider) -> ToolRegistry:
    registry = ToolRegistry()

    async def generate_video(
        prompt: str,
        start_frame_media_id: str | None = None,
        end_frame_media_id: str | None = None,
        reference_media_ids: list[str] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Media:
        references = reference_media_ids or []
        has_start = start_frame_media_id is not None
        has_end = end_frame_media_id is not None
        if has_start or has_end:
            if not (has_start and has_end) or references:
                raise ContractValidationError(
                    "Start-end video requires exactly one start frame and one end frame, without arbitrary references"
                )
        elif len(references) != 1:
            raise ContractValidationError(
                "Single-image video requires exactly one reference media input"
            )
        if len(prompt) > 2000:
            raise ContractValidationError(
                "Video motion prompt exceeds the 2000-character contract limit"
            )
        return await production.generate_video(
            prompt,
            start_frame_media_id,
            end_frame_media_id,
            references,
            parameters,
        )

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
        _domain_tool("media.list_media", "List media with optional type, work, purpose, and source-reference filters.", media.list_media, list[Media], optional={"media_type": MediaType | None, "work_id": str | None, "purpose": str | None, "source_ref": str | None}),
        _domain_tool("media.import_media", "Import an external media source and host-probed physical metadata into durable Drama-managed storage.", media.import_media, Media, required={"work_id": str, "media_type": MediaType, "source_uri": str, "content": dict[str, Any]}, optional={"asset_id": str | None, "shot_id": str | None, "purpose": str | None, "source_ref": str | None, "duration_ms": PositiveInt | None}),
        _domain_tool("media.resolve_media", "Resolve durable Drama-managed media to a temporary consumable URL.", media.resolve_media, MediaResolveResult, required={"media_id": str}),
        _domain_tool("media.restore_media_object", "Restore a missing physical object for an existing stable Media without changing its identity.", media.restore_media_object, MediaRestoreResult, required={"media_id": str, "source_uri": str}),
        _domain_tool("voice.import_voice", "Import one selected stable master reference as a durable provider-neutral Voice.", voice.import_voice, Voice, required={"name": str, "source_type": VoiceSourceType, "source_uri": str, "duration_ms": PositiveInt, "content": VoiceContent}),
        _domain_tool("voice.get_voice", "Read a durable Voice by stable identity.", voice.get_voice, Voice, required={"voice_id": str}),
        _domain_tool("voice.search_voices", "Search durable Voices by name and lifecycle status.", voice.search_voices, list[Voice], optional={"query": str | None, "status": VoiceStatus | None}),
        _domain_tool("voice.save_voice", "Update provider mappings or lifecycle metadata with optimistic version safety.", voice.update_voice, Voice, required={"voice_id": str, "content": VoiceContent, "expected_version": PositiveInt}, optional={"name": str | None, "status": VoiceStatus | None}),
        _domain_tool("voice.resolve_voice", "Resolve the stable Voice master reference to a temporary consumable URL.", voice.resolve_voice, VoiceResolveResult, required={"voice_id": str}),
        _domain_tool("production.generate_image", "Generate an image from business-level prompt and stable references.", production.generate_image, Media, required={"prompt": str}, optional={"reference_asset_ids": list[str] | None, "reference_media_ids": list[str] | None, "parameters": dict[str, Any] | None}),
        _domain_tool("production.generate_video", "Generate a video from exactly one source image or one same-target start/end frame pair.", generate_video, Media, required={"prompt": str}, optional={"start_frame_media_id": str | None, "end_frame_media_id": str | None, "reference_media_ids": list[str] | None, "parameters": dict[str, Any] | None}),
        _domain_tool("production.generate_role_dubbing", "Resolve or create a durable role Voice, synthesize exact Dialogue, run intelligibility QC, and persist Audio Media.", role_dubbing.generate_role_dubbing, RoleDubbingResult, required={"request": RoleDubbingRequest}),
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
