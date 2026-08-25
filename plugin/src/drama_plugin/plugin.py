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
from drama_plugin.providers.base import AssetProvider, ContextProvider, MediaProvider, MemoryProvider, ProductionProvider, ResearchProvider, SpeechProvider
from drama_plugin.providers.http import HttpAssetProvider, HttpMediaProvider, HttpMemoryProvider, HttpProductionProvider, HttpProviderClient, HttpResearchProvider, RemoteContextProvider
from drama_plugin.providers.mock import MockAssetProvider, MockDramaData, MockMediaProvider, MockMemoryProvider, MockProductionProvider, MockResearchProvider
from drama_plugin.providers.speech import (
    BailianQwenSpeechProvider,
    OpenAiSpeechProvider,
    ResolvedSpeechProvider,
    SpeechBackedProductionProvider,
    resolve_speech_provider,
)
from drama_plugin.skills import SkillRegistry, SkillToolReferenceValidator
from drama_plugin.tools import ToolRegistry, build_tool_registry


@dataclass
class ProviderBundle:
    memory: MemoryProvider
    asset: AssetProvider
    research: ResearchProvider
    production: ProductionProvider
    media: MediaProvider
    context: ContextProvider
    speech: SpeechProvider | None = None


class DramaPlugin:
    """Composition root only; the host remains the decision-maker and agent loop owner."""

    def __init__(self, root: Path, config: DramaPluginConfig, manifest: PluginManifest, providers: ProviderBundle, skills: SkillRegistry, tools: ToolRegistry, http_clients: list[HttpProviderClient] | None = None) -> None:
        self.root = root
        self.config = config
        self.manifest = manifest
        self.providers = providers
        self.skills = skills
        self.tools = tools
        self.context = ContextBuilder(providers.context)
        self._http_clients = http_clients or []
        self._speech_client: ResolvedSpeechProvider | None = (
            providers.speech
            if isinstance(
                providers.speech, (OpenAiSpeechProvider, BailianQwenSpeechProvider)
            )
            else None
        )

    @classmethod
    def load(cls, root: Path | str | None = None, config_path: Path | str | None = None) -> "DramaPlugin":
        plugin_root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
        manifest = cls._load_manifest(plugin_root / "plugin.yaml")
        config = load_config(config_path)
        if config.plugin.name != manifest.name: raise ConfigurationError("Configuration plugin name does not match plugin manifest")
        providers, clients = cls._initialize_providers(config)
        skills = SkillRegistry(); skills.load_directory(plugin_root / manifest.skills_directory)
        tools = build_tool_registry(providers.memory, providers.asset, providers.research, providers.production, providers.media, providers.context)
        SkillToolReferenceValidator.validate(skills, tools)
        return cls(plugin_root, config, manifest, providers, skills, tools, clients)

    @staticmethod
    def _load_manifest(path: Path) -> PluginManifest:
        try: return PluginManifest.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        except (OSError, yaml.YAMLError, ValidationError) as exc: raise ConfigurationError(f"Invalid plugin manifest: {path}") from exc

    @staticmethod
    def _initialize_providers(config: DramaPluginConfig) -> tuple[ProviderBundle, list[HttpProviderClient]]:
        data = MockDramaData(); services = config.services; selections = config.providers
        modes = {"memory": selections.memory.mode, "asset": selections.asset.mode, "research": selections.research.mode, "production": selections.production.mode, "media": selections.media.mode, "context": selections.context.mode}
        for name, mode in modes.items():
            service = getattr(services, name)
            if mode == "http" and not service.base_url.strip():
                raise ConfigurationError(f"HTTP provider requires services.{name}.base_url")
            if mode == "http" and not (service.api_token and service.api_token.strip()):
                raise ConfigurationError(f"HTTP provider requires services.{name}.api_token")
        clients: list[HttpProviderClient] = []
        def client(service: ServiceConfig) -> HttpProviderClient:
            value = HttpProviderClient(service); clients.append(value); return value
        memory: MemoryProvider = MockMemoryProvider(data) if selections.memory.mode == "mock" else HttpMemoryProvider(client(services.memory))
        asset: AssetProvider = MockAssetProvider(data) if selections.asset.mode == "mock" else HttpAssetProvider(client(services.asset))
        research: ResearchProvider = MockResearchProvider(data) if selections.research.mode == "mock" else HttpResearchProvider(client(services.research))
        production: ProductionProvider = MockProductionProvider(data) if selections.production.mode == "mock" else HttpProductionProvider(client(services.production))
        media: MediaProvider = MockMediaProvider(data) if selections.media.mode == "mock" else HttpMediaProvider(client(services.media))
        speech_client: ResolvedSpeechProvider | None = None
        speech: SpeechProvider | None = None
        if selections.speech.mode != "disabled":
            if not services.speech.output_directory.strip():
                raise ConfigurationError(
                    "Speech provider requires services.speech.output_directory"
                )
            speech_client = resolve_speech_provider(
                selections.speech.mode,
                services.speech,
                Path(services.speech.output_directory),
            )
            speech = speech_client
            production = SpeechBackedProductionProvider(production, speech, media)
        context: ContextProvider = LocalContextProvider(memory, asset, media) if selections.context.mode == "local" else RemoteContextProvider(client(services.context))
        return ProviderBundle(memory, asset, research, production, media, context, speech), clients

    def capabilities(self) -> dict[str, Any]:
        return {"plugin": self.manifest.model_dump(mode="json", by_alias=True), "skills": [skill.code for skill in self.skills.list()], "tools": [tool.describe() for tool in self.tools.list()]}

    async def aclose(self) -> None:
        for client in self._http_clients: await client.aclose()
        if self._speech_client is not None:
            await self._speech_client.aclose()
    async def __aenter__(self) -> "DramaPlugin": return self
    async def __aexit__(self, *_: object) -> None: await self.aclose()
