import inspect
from pathlib import Path

import pytest

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.exceptions import DuplicateToolError, ToolNotFoundError
from drama_plugin.plugin import DramaPlugin as PluginRuntime
from drama_plugin.tools import build_tool_registry
from drama_plugin.tools.registry import ToolDefinition, ToolRegistry


async def handler(value: str) -> str:
    return value


ROOT = Path(__file__).resolve().parents[1]


def test_tool_register_find_list_and_duplicate() -> None:
    registry = ToolRegistry()
    definition = ToolDefinition(
        code="demo.echo",
        domain="demo",
        name="echo",
        description="Echo",
        input_schema={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
            "additionalProperties": False,
        },
        output_schema={"type": "string"},
        handler=handler,
    )
    registry.register(definition)
    assert registry.get("demo.echo") is definition
    assert registry.list("demo") == [definition]
    assert registry.exists("demo.echo")
    assert registry.describe("demo.echo")["output_schema"] == {"type": "string"}
    with pytest.raises(DuplicateToolError):
        registry.register(definition)


def test_missing_tool_fails() -> None:
    with pytest.raises(ToolNotFoundError):
        ToolRegistry().get("missing.tool")


def test_every_registered_tool_has_stable_input_and_output_schema() -> None:
    plugin = DramaPlugin.load(ROOT)
    assert len(plugin.tools.list()) == 42
    for tool in plugin.tools.list():
        assert tool.input_schema["type"] == "object"
        assert isinstance(tool.input_schema["required"], list)
        assert tool.output_schema
        signature = inspect.signature(tool.handler)
        expected_required = [
            name
            for name, parameter in signature.parameters.items()
            if parameter.default is inspect.Parameter.empty
            and parameter.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )
        ]
        assert tool.input_schema["required"] == expected_required


def test_context_tools_expose_real_pydantic_schemas() -> None:
    plugin = DramaPlugin.load(ROOT)
    build = plugin.tools.get("context.build_context")
    request_schema = build.input_schema["properties"]["request"]
    assert request_schema["title"] == "ContextBuildRequest"
    assert request_schema["properties"]["resourceId"]["type"] == "string"
    assert build.output_schema["title"] == "DramaRunContext"
    assert plugin.tools.get("context.refresh_context").output_schema["title"] == "DramaContextPatch"


def test_representative_output_contracts() -> None:
    plugin = DramaPlugin.load(ROOT)
    assert plugin.tools.get("asset.get_asset").output_schema["title"] == "Asset"
    assert plugin.tools.get("work.create_work").output_schema["title"] == "Work"
    assert plugin.tools.get("production.generate_image").output_schema["title"] == "Media"
    assert plugin.tools.describe("context.build_context")["code"] == "context.build_context"


def test_persistent_memory_and_production_contracts_are_minimal() -> None:
    plugin = DramaPlugin.load(ROOT)
    expected = (
        {f"work.{action}_work" if action != "list" else "work.list_works" for action in ("create", "get", "save", "list")}
        | {f"script.{action}_script" if action != "list" else "script.list_scripts" for action in ("create", "get", "save", "list")}
        | {f"episode.{action}_episode" if action != "list" else "episode.list_episodes" for action in ("create", "get", "save", "list")}
        | {f"scene.{action}_scene" if action != "list" else "scene.list_scenes" for action in ("create", "get", "save", "list")}
        | {f"shot.{action}_shot" if action != "list" else "shot.list_shots" for action in ("create", "get", "save", "list")}
        | {
        "work.search_works", "scene.search_scenes", "shot.search_shots",
        "asset.create_asset", "asset.get_asset", "asset.save_asset", "asset.list_assets", "asset.search_assets",
        "media.create_media", "media.get_media", "media.save_media", "media.list_media",
        "production.generate_image", "production.generate_video", "production.generate_audio",
        }
    )
    codes = {tool.code for tool in plugin.tools.list()}
    assert expected <= codes
    forbidden = ("plan", "compile", "binding", "generation_target", "workflow")
    assert not any(term in code for code in codes for term in forbidden)
    assert {"script.search_scripts", "episode.search_episodes", "media.search_media"}.isdisjoint(codes)

    asset_schema = plugin.tools.get("asset.get_asset").output_schema
    assert set(asset_schema["properties"]) == {"id", "assetType", "name", "description", "referenceMediaIds"}
    media_schema = plugin.tools.get("media.get_media").output_schema
    assert set(media_schema["properties"]) == {"id", "mediaType", "mimeType", "storageKey", "metadata"}


def test_get_list_and_search_contracts_have_distinct_minimal_semantics() -> None:
    plugin = DramaPlugin.load(ROOT)
    assert plugin.tools.get("work.list_works").input_schema["properties"] == {}
    assert plugin.tools.get("work.search_works").input_schema["required"] == ["query"]
    assert plugin.tools.get("scene.search_scenes").input_schema["required"] == ["query"]
    assert plugin.tools.get("shot.search_shots").input_schema["required"] == ["query"]
    assert set(plugin.tools.get("episode.list_episodes").input_schema["properties"]) == {"script_id", "episode_no", "title"}
    assert set(plugin.tools.get("scene.list_scenes").input_schema["properties"]) == {"episode_id", "order", "location", "character"}
    assert set(plugin.tools.get("shot.list_shots").input_schema["properties"]) == {"scene_id", "shot_no", "shot_type", "character"}

    memory_domains = {"work", "script", "episode", "scene", "shot", "asset", "media"}
    memory_tools = [tool for tool in plugin.tools.list() if tool.domain in memory_domains]
    assert all("stable ID" in tool.description for tool in memory_tools if tool.name.startswith("get_"))
    assert all("search" not in tool.description.lower() for tool in memory_tools if tool.name.startswith("list_"))
    assert all("stable ID is unknown" in tool.description for tool in memory_tools if tool.name.startswith("search_") and tool.domain != "asset")


def test_no_duplicate_legacy_memory_tool_synonyms() -> None:
    plugin = DramaPlugin.load(ROOT)
    forbidden_actions = ("fetch_", "load_", "find_", "query_", "lookup_", "update_")
    assert not any(tool.name.startswith(forbidden_actions) for tool in plugin.tools.list())


@pytest.mark.asyncio
async def test_tool_contracts_do_not_change_with_http_provider_bindings() -> None:
    mock_plugin = DramaPlugin.load(ROOT)
    service = {"base_url": "https://unit.invalid", "operations": {}}
    config = DramaPluginConfig.model_validate(
        {
            "providers": {
                "memory": {"mode": "http"},
                "asset": {"mode": "http"},
                "research": {"mode": "http"},
                "production": {"mode": "http"},
                "media": {"mode": "http"},
                "context": {"mode": "http"},
            },
            "services": {
                name: service
                for name in ("memory", "asset", "research", "production", "media", "context")
            },
        }
    )
    providers, clients = PluginRuntime._initialize_providers(config)
    http_registry = build_tool_registry(
        providers.memory,
        providers.asset,
        providers.research,
        providers.production,
        providers.media,
        providers.context,
    )
    assert mock_plugin.tools.describe() == http_registry.describe()
    for client in clients:
        await client.aclose()
