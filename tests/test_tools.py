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
    assert len(plugin.tools.list()) == 33
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
    assert build.output_schema["title"] == "DramaModelContext"
    assert plugin.tools.get("context.refresh_context").output_schema["title"] == "DramaContextPatch"


def test_representative_output_contracts() -> None:
    plugin = DramaPlugin.load(ROOT)
    assert plugin.tools.get("asset.get_asset").output_schema["title"] == "Asset"
    assert plugin.tools.get("generation.create_generation_plan").output_schema["title"] == "GenerationPlan"
    assert plugin.tools.describe("context.build_context")["code"] == "context.build_context"


@pytest.mark.asyncio
async def test_tool_contracts_do_not_change_with_http_provider_bindings() -> None:
    mock_plugin = DramaPlugin.load(ROOT)
    service = {"base_url": "https://unit.invalid", "operations": {}}
    config = DramaPluginConfig.model_validate(
        {
            "providers": {
                "project": {"mode": "http"},
                "asset": {"mode": "http"},
                "history": {"mode": "http"},
                "generation": {"mode": "http"},
                "media": {"mode": "http"},
                "context": {"mode": "http"},
            },
            "services": {
                name: service
                for name in ("project", "asset", "history", "generation", "media", "context")
            },
        }
    )
    providers, clients = PluginRuntime._initialize_providers(config)
    http_registry = build_tool_registry(
        providers.project,
        providers.asset,
        providers.history,
        providers.generation,
        providers.media,
        providers.context,
    )
    assert mock_plugin.tools.describe() == http_registry.describe()
    for client in clients:
        await client.aclose()
