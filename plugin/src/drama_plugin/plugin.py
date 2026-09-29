from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from drama_plugin.production.store import ProductionPackageStore
    from drama_plugin.governance.store import GateFindingStore
    from drama_plugin.runtime.contracts import ArtifactReference, RunMode, RuntimeRun

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from drama_plugin.config import DramaPluginConfig, ServiceConfig, load_config
from drama_plugin.context import ContextBuilder, LocalContextProvider
from drama_plugin.context.rhythm import RhythmContextProvider
from drama_plugin.contracts.manifest import PluginManifest
from drama_plugin.exceptions import ConfigurationError
from drama_plugin.providers.base import AssetProvider, ContextProvider, MediaProvider, MemoryProvider, ProductionProvider, ResearchProvider, RoleDubbingProvider, VoiceProvider
from drama_plugin.providers.http import HttpAssetProvider, HttpMediaProvider, HttpMemoryProvider, HttpProductionProvider, HttpProviderClient, HttpResearchProvider, HttpVoiceProvider, RemoteContextProvider
from drama_plugin.providers.mock import MockAssetProvider, MockDramaData, MockMediaProvider, MockMemoryProvider, MockProductionProvider, MockResearchProvider, MockVoiceProvider
from drama_plugin.providers.speech.fish_audio import FishAudioHttpClient
from drama_plugin.providers.speech.role_dubbing import FishRoleDubbingProvider, UnavailableRoleDubbingProvider
from drama_plugin.skills import SkillRegistry, SkillToolReferenceValidator
from drama_plugin.tools import ToolRegistry, build_tool_registry
from drama_plugin.providers.base.audio_semantic import AudioSemanticProvider
from drama_plugin.providers.http.qwen_omni import BailianQwenOmniAudioSemanticProvider


@dataclass
class ProviderBundle:
    memory: MemoryProvider
    asset: AssetProvider
    research: ResearchProvider
    production: ProductionProvider
    media: MediaProvider
    context: ContextProvider
    voice: VoiceProvider | None = None
    role_dubbing: RoleDubbingProvider | None = None
    audio_semantic: AudioSemanticProvider | None = None


class DramaPlugin:
    """Composition root with an opt-in Plugin-owned T1 runtime foundation.

    Legacy production entry points stay intact; new runtime workflows advance
    inside the Plugin and do not depend on a host choosing each next tool.
    """

    def __init__(self, root: Path, config: DramaPluginConfig, manifest: PluginManifest, providers: ProviderBundle, skills: SkillRegistry, tools: ToolRegistry, http_clients: list[HttpProviderClient] | None = None, *, production_artifact_roots: tuple[Path, ...] = (), production_package_store: ProductionPackageStore | None = None, gate_finding_store: GateFindingStore | None = None) -> None:
        self.root = root
        self.config = config
        from drama_plugin.characters import CharacterRepository
        self.characters = CharacterRepository(config.character_repository_root, plugin_root=root)
        self.manifest = manifest
        self.providers = providers
        self.skills = skills
        self.tools = tools
        from drama_plugin.runtime import InMemoryRunStore, LegacyCapabilityBridge, RunMode, RuntimeEngine
        from drama_plugin.runtime.capabilities import TargetCapabilityRouter
        from drama_plugin.runtime.engine import foundation_workflows
        from drama_plugin.production import (LegacyAssemblySources, ProductionPackageCapability,
            ProductionPackageStore, ShotAssembler, assembly_workflow)
        runs = InMemoryRunStore()
        self.production_packages = production_package_store if production_package_store is not None else ProductionPackageStore()
        from drama_plugin.professional_design import ProfessionalDesignResolver
        from drama_plugin.professional_design.legacy import LegacyProfessionalDesignSources
        assembly_sources = LegacyAssemblySources(tools, production_artifact_roots)
        self.professional_design = ProfessionalDesignResolver(LegacyProfessionalDesignSources(assembly_sources))
        self.shot_assembler = ShotAssembler(assembly_sources, self.professional_design)
        package_capability = ProductionPackageCapability(self.shot_assembler, self.production_packages, runs)
        workflow = assembly_workflow()
        from drama_plugin.governance import GateFindingStore, GateGovernor
        from drama_plugin.governance.capability import GateGovernanceCapability
        from drama_plugin.governance.policy import GovernedPolicy, governed_workflow
        self.gate_findings = gate_finding_store if gate_finding_store is not None else GateFindingStore()
        self.gate_governor = GateGovernor(self.gate_findings)
        self.gate_governance = GateGovernanceCapability(self.gate_governor, self.gate_findings,
            self.production_packages, self.shot_assembler, runs)
        governance_workflow = governed_workflow()
        self.runtime = RuntimeEngine(TargetCapabilityRouter({**package_capability.registrations(),
            **self.gate_governance.registrations()},
            LegacyCapabilityBridge.from_tools(tools)), store=runs,
            workflows={**foundation_workflows(), workflow.workflow_id: workflow,
                governance_workflow.workflow_id: governance_workflow},
            policies={mode: GovernedPolicy(mode, self.gate_findings) for mode in RunMode})
        self.context = ContextBuilder(providers.context)
        self._http_clients = http_clients or []
        self._fish_client = (
            providers.role_dubbing.fish
            if isinstance(providers.role_dubbing, FishRoleDubbingProvider)
            else None
        )

    @classmethod
    def load(cls, root: Path | str | None = None, config_path: Path | str | None = None, *, mock_data: MockDramaData | None = None, production_artifact_roots: tuple[Path, ...] = (), production_package_store: ProductionPackageStore | None = None, gate_finding_store: GateFindingStore | None = None) -> "DramaPlugin":
        plugin_root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
        manifest = cls._load_manifest(plugin_root / "plugin.yaml")
        config = load_config(config_path)
        if config.plugin.name != manifest.name: raise ConfigurationError("Configuration plugin name does not match plugin manifest")
        providers, clients = cls._initialize_providers(config, mock_data=mock_data)
        skills = SkillRegistry(); skills.load_directory(plugin_root / manifest.skills_directory)
        if providers.voice is None or providers.role_dubbing is None:
            raise ConfigurationError("Voice and Role Dubbing providers must be configured")
        tools = build_tool_registry(providers.memory, providers.asset, providers.research, providers.production, providers.media, providers.context, providers.voice, providers.role_dubbing)
        SkillToolReferenceValidator.validate(skills, tools)
        return cls(plugin_root, config, manifest, providers, skills, tools, clients,
                   production_artifact_roots=production_artifact_roots, production_package_store=production_package_store,
                   gate_finding_store=gate_finding_store)

    @staticmethod
    def _load_manifest(path: Path) -> PluginManifest:
        try: return PluginManifest.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        except (OSError, yaml.YAMLError, ValidationError) as exc: raise ConfigurationError(f"Invalid plugin manifest: {path}") from exc

    @staticmethod
    def _initialize_providers(config: DramaPluginConfig, *, mock_data: MockDramaData | None = None) -> tuple[ProviderBundle, list[HttpProviderClient]]:
        data = mock_data if mock_data is not None else MockDramaData.empty(); services = config.services; selections = config.providers
        modes = {"memory": selections.memory.mode, "asset": selections.asset.mode, "research": selections.research.mode, "production": selections.production.mode, "media": selections.media.mode, "context": selections.context.mode, "voice": selections.voice.mode}
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
        voice: VoiceProvider = MockVoiceProvider(data) if selections.voice.mode == "mock" else HttpVoiceProvider(client(services.voice))
        role_config = services.role_dubbing
        role_dubbing: RoleDubbingProvider
        if role_config.api_key is None:
            role_dubbing = UnavailableRoleDubbingProvider()
        else:
            if not role_config.output_directory.strip():
                raise ConfigurationError("Fish Role Dubbing requires an output directory")
            fish = FishAudioHttpClient(
                role_config.api_key.get_secret_value(), base_url=role_config.base_url,
                tts_model=role_config.tts_model,
                timeout_seconds=role_config.timeout_seconds,
                max_transient_retries=role_config.max_transient_retries,
            )
            role_dubbing = FishRoleDubbingProvider(
                memory=memory, voices=voice, media=media, fish=fish,
                output_directory=Path(role_config.output_directory),
            )
        context: ContextProvider = LocalContextProvider(memory, asset, media) if selections.context.mode == "local" else RemoteContextProvider(client(services.context))
        context = RhythmContextProvider(context, config)
        audio_semantic: AudioSemanticProvider | None = None
        if selections.audio_semantic.mode == 'bailian_qwen_omni':
            audio_semantic = BailianQwenOmniAudioSemanticProvider(services.qwen_omni)
        return ProviderBundle(memory, asset, research, production, media, context, voice, role_dubbing, audio_semantic), clients

    def create_governed_run(self, *, work_id: str, scene_id: str, shot_id: str,
                            mode: RunMode, run_id: str | None = None,
                            package_ref: ArtifactReference | None = None,
                            finding_refs: tuple[ArtifactReference, ...] = ()) -> RuntimeRun:
        """New Shot preparation enters T3 policy; T1/T2 versioned workflows remain readable."""
        from drama_plugin.governance.contracts import GovernanceInput
        from drama_plugin.governance.policy import WORKFLOW
        inputs = GovernanceInput(package_ref=package_ref, finding_refs=finding_refs)
        run = self.runtime.create_run(work_id=work_id, scene_id=scene_id, shot_id=shot_id,
            mode=mode, workflow_id=WORKFLOW, run_id=run_id)
        self.gate_findings.bind(run.run_id, inputs)
        return run

    def capabilities(self) -> dict[str, Any]:
        from drama_plugin.professional import registry, dependency_order
        from drama_plugin.contracts.base import dump_contract
        return {"plugin": self.manifest.model_dump(mode="json", by_alias=True), "skills": [skill.code for skill in self.skills.list()], "tools": [tool.describe() for tool in self.tools.list()],
                "professionalDepartments": [dump_contract(registry()[key]) for key in dependency_order()]}

    def creative_source_host(self, artifact_root: Path | str) -> Any:
        from drama_plugin.hosts.creative_source import CreativeSourceHost
        return CreativeSourceHost(artifact_root)

    def professional_host(self, artifact_root: Path | str, *, source_type: str = 'HISTORICAL') -> Any:
        """Explicit design-only Host entry; never starts an agent or production loop."""
        from drama_plugin.hosts.professional import ProfessionalDepartmentHost
        return ProfessionalDepartmentHost(artifact_root, self.skills.get, source_type=source_type)

    def specialized_asset_host(self) -> Any:
        from drama_plugin.hosts.specialized_asset import SpecializedAssetHost
        self.skills.get('specialized-asset-design')
        return SpecializedAssetHost(self.config)

    def video_provider_host(self, cache: Path | str) -> Any:
        """Host-neutral official HTTP lifecycle; Comfy MCP/image production stays intact."""
        from drama_plugin.hosts.http_video import VideoProviderHost
        return VideoProviderHost(self.providers.memory, self.providers.media, self.providers.asset, Path(cache))

    async def aclose(self) -> None:
        if self.providers.audio_semantic is not None:
            await self.providers.audio_semantic.aclose()
        for client in self._http_clients: await client.aclose()
        if self._fish_client is not None:
            await self._fish_client.aclose()
    async def __aenter__(self) -> "DramaPlugin": return self
    async def __aexit__(self, *_: object) -> None: await self.aclose()
