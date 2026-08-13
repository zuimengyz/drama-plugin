from pathlib import Path

import pytest

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.context import LocalContextProvider
from drama_plugin.exceptions import ConfigurationError, SkillLoadError
from drama_plugin.providers.http import HttpAssetProvider, HttpMediaProvider, HttpMemoryProvider, RemoteContextProvider
from drama_plugin.providers.mock import MockAssetProvider, MockMediaProvider, MockMemoryProvider
from drama_plugin.tools import ToolRegistry, build_tool_registry

ROOT = Path(__file__).resolve().parents[1]


def test_plugin_initializes_agent_driven_capabilities() -> None:
    plugin = DramaPlugin.load(ROOT)
    assert plugin.manifest.name == "drama-plugin"
    assert len(plugin.skills.list()) == 8
    codes = {tool.code for tool in plugin.tools.list()}
    assert len(codes) == 44
    assert {"work.search_works", "scene.search_scenes", "shot.search_shots", "asset.search_assets", "production.generate_video", "context.build_context"} <= codes
    assert not any("plan" in code or "compile" in code or "binding" in code for code in codes)


def _config_for_modes(**modes: str) -> DramaPluginConfig:
    providers = {name: {"mode": modes.get(name, "local" if name == "context" else "mock")} for name in ("memory", "asset", "research", "production", "media", "context")}
    services = {name: {"base_url": "https://unit.invalid", "api_token": "test-only", "operations": {}} for name, selection in providers.items() if selection["mode"] == "http"}
    return DramaPluginConfig.model_validate({"providers": providers, "services": services})


@pytest.mark.asyncio
async def test_context_http_can_initialize_with_other_domains_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config_for_modes(context="http")
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: config)
    plugin = DramaPlugin.load(ROOT)
    assert isinstance(plugin.providers.memory, MockMemoryProvider)
    assert isinstance(plugin.providers.asset, MockAssetProvider)
    assert isinstance(plugin.providers.context, RemoteContextProvider)
    assert len(plugin._http_clients) == 1
    await plugin.aclose()


@pytest.mark.asyncio
async def test_memory_http_can_mix_with_local_context(monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config_for_modes(memory="http")
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: config)
    plugin = DramaPlugin.load(ROOT)
    assert isinstance(plugin.providers.memory, HttpMemoryProvider)
    assert isinstance(plugin.providers.context, LocalContextProvider)
    assert len(plugin._http_clients) == 1
    await plugin.aclose()


@pytest.mark.asyncio
async def test_memory_asset_media_can_switch_to_http_independently(monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config_for_modes(memory="http", asset="http", media="http")
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: config)
    plugin = DramaPlugin.load(ROOT)
    assert isinstance(plugin.providers.memory, HttpMemoryProvider)
    assert isinstance(plugin.providers.asset, HttpAssetProvider)
    assert isinstance(plugin.providers.media, HttpMediaProvider)
    assert len(plugin._http_clients) == 3
    await plugin.aclose()


def test_http_mode_without_token_fails_without_mock_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    config = DramaPluginConfig.model_validate({
        "providers": {"memory": {"mode": "http"}},
        "services": {"memory": {"base_url": "https://unit.invalid"}},
    })
    monkeypatch.setattr("drama_plugin.plugin.load_config", lambda _: config)
    with pytest.raises(ConfigurationError, match=r"services\.memory\.api_token"):
        DramaPlugin.load(ROOT)


def test_plugin_fails_when_skill_references_missing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    def registry_without_generate_video(*providers: object) -> ToolRegistry:
        complete = build_tool_registry(*providers)
        incomplete = ToolRegistry()
        for definition in complete.list():
            if definition.code != "production.generate_video": incomplete.register(definition)
        return incomplete
    monkeypatch.setattr("drama_plugin.plugin.build_tool_registry", registry_without_generate_video)
    with pytest.raises(SkillLoadError, match=r"shot-production.*production\.generate_video"):
        DramaPlugin.load(ROOT)
