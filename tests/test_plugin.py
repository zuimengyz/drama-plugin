from pathlib import Path

import pytest

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.context import LocalContextProvider
from drama_plugin.exceptions import SkillLoadError
from drama_plugin.providers.http import HttpProjectProvider, RemoteContextProvider
from drama_plugin.providers.mock import MockAssetProvider, MockProjectProvider
from drama_plugin.tools import ToolRegistry, build_tool_registry


ROOT = Path(__file__).resolve().parents[1]


def test_plugin_initializes_and_enumerates_capabilities() -> None:
    plugin = DramaPlugin.load(ROOT)
    assert plugin.manifest.name == "drama-plugin"
    assert len(plugin.skills.list()) == 8
    codes = {tool.code for tool in plugin.tools.list()}
    assert "asset.resolve_asset_hierarchy" in codes
    assert "context.build_context" in codes
    assert len(codes) == 33


def _config_for_modes(**modes: str) -> DramaPluginConfig:
    providers = {
        "project": {"mode": modes.get("project", "mock")},
        "asset": {"mode": modes.get("asset", "mock")},
        "history": {"mode": modes.get("history", "mock")},
        "generation": {"mode": modes.get("generation", "mock")},
        "media": {"mode": modes.get("media", "mock")},
        "context": {"mode": modes.get("context", "local")},
    }
    services = {
        name: {"base_url": "https://unit.invalid", "operations": {}}
        for name, selection in providers.items()
        if selection["mode"] == "http"
    }
    return DramaPluginConfig.model_validate({"providers": providers, "services": services})


@pytest.mark.asyncio
async def test_context_http_can_initialize_with_other_domains_mock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config_for_modes(context="http")
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: config)
    plugin = DramaPlugin.load(ROOT)
    assert isinstance(plugin.providers.project, MockProjectProvider)
    assert isinstance(plugin.providers.asset, MockAssetProvider)
    assert isinstance(plugin.providers.context, RemoteContextProvider)
    assert len(plugin._http_clients) == 1
    await plugin.aclose()


@pytest.mark.asyncio
async def test_project_http_can_mix_with_local_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config_for_modes(project="http")
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: config)
    plugin = DramaPlugin.load(ROOT)
    assert isinstance(plugin.providers.project, HttpProjectProvider)
    assert isinstance(plugin.providers.asset, MockAssetProvider)
    assert isinstance(plugin.providers.context, LocalContextProvider)
    assert len(plugin._http_clients) == 1
    await plugin.aclose()


def test_plugin_fails_when_skill_references_missing_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def registry_without_submit(*providers: object) -> ToolRegistry:
        complete = build_tool_registry(*providers)
        incomplete = ToolRegistry()
        for definition in complete.list():
            if definition.code != "generation.submit_generation":
                incomplete.register(definition)
        return incomplete

    monkeypatch.setattr(
        "drama_plugin.plugin.build_tool_registry",
        registry_without_submit,
    )
    with pytest.raises(
        SkillLoadError,
        match=r"shot-generation.*generation\.submit_generation",
    ):
        DramaPlugin.load(ROOT)
