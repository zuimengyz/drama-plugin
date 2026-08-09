from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from drama_plugin.config import DramaPluginConfig, ServiceConfig, load_config
from drama_plugin.context import ContextBuilder, LocalContextProvider
from drama_plugin.contracts.manifest import PluginManifest
from drama_plugin.exceptions import ConfigurationError
from drama_plugin.providers.base import AssetProvider, ContextProvider, GenerationProvider, HistoryProvider, MediaProvider, ProjectProvider
from drama_plugin.providers.http import (
    HttpAssetProvider,
    HttpGenerationProvider,
    HttpHistoryProvider,
    HttpMediaProvider,
    HttpProjectProvider,
    HttpProviderClient,
    RemoteContextProvider,
)
from drama_plugin.providers.mock import MockAssetProvider, MockDramaData, MockGenerationProvider, MockHistoryProvider, MockMediaProvider, MockProjectProvider
from drama_plugin.skills import SkillRegistry, SkillToolReferenceValidator
from drama_plugin.tools import ToolRegistry, build_tool_registry


@dataclass
class ProviderBundle:
    project: ProjectProvider
    asset: AssetProvider
    history: HistoryProvider
    generation: GenerationProvider
    media: MediaProvider
    context: ContextProvider


class DramaPlugin:
    """Composition root only; deliberately contains no agent loop."""

    def __init__(
        self,
        root: Path,
        config: DramaPluginConfig,
        manifest: PluginManifest,
        providers: ProviderBundle,
        skills: SkillRegistry,
        tools: ToolRegistry,
        http_clients: list[HttpProviderClient] | None = None,
    ) -> None:
        self.root = root
        self.config = config
        self.manifest = manifest
        self.providers = providers
        self.skills = skills
        self.tools = tools
        self.context = ContextBuilder(providers.context)
        self._http_clients = http_clients or []

    @classmethod
    def load(cls, root: Path | str | None = None, config_path: Path | str | None = None) -> "DramaPlugin":
        plugin_root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
        manifest = cls._load_manifest(plugin_root / "plugin.yaml")
        config = load_config(config_path)
        if config.plugin.name != manifest.name:
            raise ConfigurationError("Configuration plugin name does not match plugin manifest")
        providers, clients = cls._initialize_providers(config)
        skills = SkillRegistry()
        skills.load_directory(plugin_root / manifest.skills_directory)
        tools = build_tool_registry(
            providers.project,
            providers.asset,
            providers.history,
            providers.generation,
            providers.media,
            providers.context,
        )
        SkillToolReferenceValidator.validate(skills, tools)
        return cls(plugin_root, config, manifest, providers, skills, tools, clients)

    @staticmethod
    def _load_manifest(path: Path) -> PluginManifest:
        try:
            payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
            return PluginManifest.model_validate(payload)
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise ConfigurationError(f"Invalid plugin manifest: {path}") from exc

    @staticmethod
    def _initialize_providers(config: DramaPluginConfig) -> tuple[ProviderBundle, list[HttpProviderClient]]:
        data = MockDramaData()
        service_configs = config.services
        provider_configs = config.providers
        selected_modes = {
            "project": provider_configs.project.mode,
            "asset": provider_configs.asset.mode,
            "history": provider_configs.history.mode,
            "generation": provider_configs.generation.mode,
            "media": provider_configs.media.mode,
            "context": provider_configs.context.mode,
        }
        for name, mode in selected_modes.items():
            if mode == "http" and not getattr(service_configs, name).base_url:
                raise ConfigurationError(
                    f"HTTP provider requires services.{name}.base_url"
                )

        clients: list[HttpProviderClient] = []

        def http_client(service: ServiceConfig) -> HttpProviderClient:
            client = HttpProviderClient(service)
            clients.append(client)
            return client

        project: ProjectProvider = (
            MockProjectProvider(data)
            if provider_configs.project.mode == "mock"
            else HttpProjectProvider(http_client(service_configs.project))
        )
        asset: AssetProvider = (
            MockAssetProvider(data)
            if provider_configs.asset.mode == "mock"
            else HttpAssetProvider(http_client(service_configs.asset))
        )
        history: HistoryProvider = (
            MockHistoryProvider(data)
            if provider_configs.history.mode == "mock"
            else HttpHistoryProvider(http_client(service_configs.history))
        )
        generation: GenerationProvider = (
            MockGenerationProvider(data)
            if provider_configs.generation.mode == "mock"
            else HttpGenerationProvider(http_client(service_configs.generation))
        )
        media: MediaProvider = (
            MockMediaProvider(data)
            if provider_configs.media.mode == "mock"
            else HttpMediaProvider(http_client(service_configs.media))
        )
        context: ContextProvider = (
            LocalContextProvider(project, asset, history, generation)
            if provider_configs.context.mode == "local"
            else RemoteContextProvider(http_client(service_configs.context))
        )
        return ProviderBundle(project, asset, history, generation, media, context), clients

    def capabilities(self) -> dict[str, Any]:
        return {
            "plugin": self.manifest.model_dump(mode="json", by_alias=True),
            "skills": [skill.code for skill in self.skills.list()],
            "tools": [tool.describe() for tool in self.tools.list()],
        }

    async def aclose(self) -> None:
        for client in self._http_clients:
            await client.aclose()

    async def __aenter__(self) -> "DramaPlugin":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
