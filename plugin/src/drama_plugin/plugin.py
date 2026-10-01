from __future__ import annotations

from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from drama_plugin.production.store import ProductionPackageStore
    from drama_plugin.governance.store import GateFindingStore
    from drama_plugin.generation.store import GenerationArtifactStore
    from drama_plugin.production.references import ReferenceExecutionStore
    from drama_plugin.generation.contracts import GenerationTask
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
    """Composition root for the Plugin-owned Target Runtime and stores.

    Legacy production remains a separate recovery island. Target workflows
    advance inside the Plugin through native capabilities and named Canon reads.
    """

    def __init__(self, root: Path, config: DramaPluginConfig, manifest: PluginManifest, providers: ProviderBundle, skills: SkillRegistry, tools: ToolRegistry, http_clients: list[HttpProviderClient] | None = None, *, production_artifact_roots: tuple[Path, ...] = (), production_package_store: ProductionPackageStore | None = None, gate_finding_store: GateFindingStore | None = None, generation_artifact_store: GenerationArtifactStore | None = None, reference_execution_store: ReferenceExecutionStore | None = None, ledger_path: Path | str | None = None, test_foundation: bool = False) -> None:
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
        from drama_plugin.runtime.legacy_boundary import LegacyBoundary
        from drama_plugin.runtime.legacy_recovery import LegacyRecovery
        from drama_plugin.runtime.engine import foundation_workflows
        from drama_plugin.production import (LegacyAssemblySources, ProductionPackageCapability,
            ProductionPackageStore, ShotAssembler, assembly_workflow)
        selected_ledger_path = ledger_path if ledger_path is not None else config.production_ledger_path
        self.ledger = None
        self._test_foundation = test_foundation
        if selected_ledger_path:
            if any(store is not None for store in (production_package_store, gate_finding_store,
                    generation_artifact_store, reference_execution_store)):
                raise ConfigurationError("A durable Target run cannot mix in-memory Foundation stores")
            from drama_plugin.persistence import (ProductionLedger, DurableRunStore,
                DurableProductionPackageStore, DurableGateFindingStore,
                DurableGenerationArtifactStore, DurableReferenceExecutionStore, DurableReviewStore)
            self.ledger = ProductionLedger(selected_ledger_path)
            runs = DurableRunStore(self.ledger)
            self.production_packages = DurableProductionPackageStore(self.ledger)
            self.execution_references = DurableReferenceExecutionStore(self.ledger)
            self.gate_findings = DurableGateFindingStore(self.ledger)
            self.generation_artifacts = DurableGenerationArtifactStore(self.ledger)
            self.reviews = DurableReviewStore(self.ledger)
        else:
            runs = InMemoryRunStore()
            self.production_packages = production_package_store if production_package_store is not None else ProductionPackageStore()
            from drama_plugin.production.references import ReferenceExecutionStore
            self.execution_references = reference_execution_store if reference_execution_store is not None else ReferenceExecutionStore()
            from drama_plugin.governance import GateFindingStore
            self.gate_findings = gate_finding_store if gate_finding_store is not None else GateFindingStore()
            from drama_plugin.generation.store import GenerationArtifactStore
            self.generation_artifacts = generation_artifact_store if generation_artifact_store is not None else GenerationArtifactStore()
            self.reviews = None
        from drama_plugin.professional_design import ProfessionalDesignResolver
        from drama_plugin.professional_design.legacy import LegacyProfessionalDesignSources
        from drama_plugin.production.references import ReferenceBoundSources, BoundMediaReader
        assembly_sources = ReferenceBoundSources(LegacyAssemblySources(tools, production_artifact_roots), self.execution_references)
        self.professional_design = ProfessionalDesignResolver(LegacyProfessionalDesignSources(assembly_sources))
        self.shot_assembler = ShotAssembler(assembly_sources, self.professional_design, self.execution_references)
        package_capability = ProductionPackageCapability(self.shot_assembler, self.production_packages, runs)
        workflow = assembly_workflow()
        from drama_plugin.governance import GateGovernor
        from drama_plugin.governance.capability import GateGovernanceCapability
        from drama_plugin.governance.policy import governed_workflow
        self.gate_governor = GateGovernor(self.gate_findings)
        self.gate_governance = GateGovernanceCapability(self.gate_governor, self.gate_findings,
            self.production_packages, self.shot_assembler, runs)
        governance_workflow = governed_workflow()
        from drama_plugin.generation.sources import PackageReader, LegacyExecutionReferences
        from drama_plugin.generation.compiler import PromptCompiler
        from drama_plugin.generation.capability import GenerationCapability
        from drama_plugin.generation.policy import GenerationPolicy, generation_workflow
        self.prompt_compiler = PromptCompiler(self.production_packages, self.generation_artifacts,
            PackageReader(assembly_sources, LegacyExecutionReferences(production_artifact_roots)),
            media_reader=BoundMediaReader(tools))
        self.generation_capability = GenerationCapability(self.prompt_compiler, self.generation_artifacts, self.gate_governance)
        generation_flow = generation_workflow()
        self.legacy_boundary = LegacyBoundary()
        self.legacy_recovery = LegacyRecovery(providers.memory, self.legacy_boundary)
        self.runtime = RuntimeEngine(TargetCapabilityRouter({**package_capability.registrations(),
            **self.gate_governance.registrations(), **self.generation_capability.registrations()},
            LegacyCapabilityBridge.from_tools(tools), self.legacy_boundary), store=runs,
            workflows={**foundation_workflows(), workflow.workflow_id: workflow,
                governance_workflow.workflow_id: governance_workflow, generation_flow.workflow_id: generation_flow},
            policies={mode: GenerationPolicy(mode, self.gate_findings) for mode in RunMode})
        self.context = ContextBuilder(providers.context)
        self._http_clients = http_clients or []
        self._fish_client = (
            providers.role_dubbing.fish
            if isinstance(providers.role_dubbing, FishRoleDubbingProvider)
            else None
        )

    @classmethod
    def load(cls, root: Path | str | None = None, config_path: Path | str | None = None, *, mock_data: MockDramaData | None = None, production_artifact_roots: tuple[Path, ...] = (), production_package_store: ProductionPackageStore | None = None, gate_finding_store: GateFindingStore | None = None, generation_artifact_store: GenerationArtifactStore | None = None, reference_execution_store: ReferenceExecutionStore | None = None, ledger_path: Path | str | None = None) -> "DramaPlugin":
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
                   gate_finding_store=gate_finding_store, generation_artifact_store=generation_artifact_store,
                   reference_execution_store=reference_execution_store, ledger_path=ledger_path,
                   test_foundation=mock_data is not None)

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
        if self.ledger is None and not self._test_foundation:
            raise ConfigurationError("Target production needs configured production_ledger_path")
        from drama_plugin.governance.contracts import GovernanceInput
        from drama_plugin.governance.policy import WORKFLOW
        inputs = GovernanceInput(package_ref=package_ref, finding_refs=finding_refs)
        if self.ledger is not None:
            run = self.runtime.draft_run(work_id=work_id, scene_id=scene_id, shot_id=shot_id,
                mode=mode, workflow_id=WORKFLOW, run_id=run_id)
            return self.ledger.create_target_run(run, inputs)
        run = self.runtime.create_run(work_id=work_id, scene_id=scene_id, shot_id=shot_id,
            mode=mode, workflow_id=WORKFLOW, run_id=run_id)
        self.gate_findings.bind(run.run_id, inputs)
        return run

    def create_generation_run(self, *, work_id: str, scene_id: str, shot_id: str,
                              mode: RunMode, run_id: str | None = None,
                              task: GenerationTask | None = None,
                              package_ref: ArtifactReference | None = None,
                              cached_preparation_ref: ArtifactReference | None = None) -> RuntimeRun:
        """T5 package-only preparation; the Plugin owns every step and stops before transport."""
        if self.ledger is None and not self._test_foundation:
            raise ConfigurationError("Target production needs configured production_ledger_path")
        from drama_plugin.generation.contracts import GenerationInput, GenerationTask
        from drama_plugin.generation.policy import WORKFLOW
        from drama_plugin.governance.contracts import GovernanceInput
        if self.ledger is not None:
            from drama_plugin.runtime.contracts import RuntimeScope
            scope = RuntimeScope(work_id=work_id, scene_id=scene_id, shot_id=shot_id)
            values = GenerationInput(task=task if task is not None else
                GenerationTask(input_mode=self.execution_references.mode(scope)),
                cached_preparation_ref=cached_preparation_ref)
            run = self.runtime.draft_run(work_id=work_id, scene_id=scene_id, shot_id=shot_id,
                mode=mode, workflow_id=WORKFLOW, run_id=run_id)
            return self.ledger.create_target_run(run, GovernanceInput(package_ref=package_ref), values)
        run = self.runtime.create_run(work_id=work_id, scene_id=scene_id, shot_id=shot_id,
            mode=mode, workflow_id=WORKFLOW, run_id=run_id)
        self.gate_findings.bind(run.run_id, GovernanceInput(package_ref=package_ref))
        self.generation_artifacts.bind(run.run_id, GenerationInput(
            task=task if task is not None else GenerationTask(input_mode=self.execution_references.mode(run.scope)),
            cached_preparation_ref=cached_preparation_ref))
        return run

    async def decide_target_run(self, run_id: str, *, decision_id: str, accepted: bool,
                                source_ref: ArtifactReference | None = None) -> RuntimeRun:
        """Retain a real user decision receipt before advancing its existing Run."""
        if self.reviews is None:
            raise ConfigurationError("Durable Review Store required for formal Target decisions")
        from drama_plugin.persistence.review import UserDecisionRecord
        from drama_plugin.runtime.contracts import ActionKind, RuntimeState
        run = await self.runtime.recover_run(run_id)
        action = self.runtime.next_action(run_id)
        if run.state != RuntimeState.WAITING_USER or action.kind != ActionKind.REQUEST_USER_DECISION:
            raise ValueError("Run does not await a user decision")
        if decision_id != self.runtime.decision_id(run_id):
            raise ValueError("Decision identity mismatch")
        record = UserDecisionRecord.seal(run_id=run_id, scope=run.scope,
            decision_id=decision_id, category=action.decision.category,
            accepted=accepted, source_ref=source_ref)
        ref = self.reviews.put_user_decision(record)
        return await self.runtime.decide(run_id, decision_id=decision_id,
            accepted=accepted, decision_ref=ref)

    async def resume_legacy_run(self, *, work_id: str, attempt_id: str) -> dict[str, Any]:
        """Explicit historical handoff; never imports old history into Target Ledger."""
        if self.ledger is not None:
            try:
                self.ledger.load_run(attempt_id)
            except KeyError:
                pass
            else:
                raise ValueError("LEGACY_GUARD: Target run identity")
        return await self.legacy_recovery.resume_legacy_run(work_id=work_id, attempt_id=attempt_id)

    @asynccontextmanager
    async def legacy_recovery_session(self, *, work_id: str,
                                      attempt_id: str) -> AsyncIterator[dict[str, Any]]:
        """The only formal grant for retained Work-stage mutation/recovery."""
        await self.resume_legacy_run(work_id=work_id, attempt_id=attempt_id)
        async with self.legacy_recovery.session(work_id=work_id, attempt_id=attempt_id) as snapshot:
            yield snapshot

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
