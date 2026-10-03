from __future__ import annotations

from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from drama_plugin.production.store import ProductionPackageStore
    from drama_plugin.governance.store import GateFindingStore
    from drama_plugin.generation.store import GenerationArtifactStore
    from drama_plugin.production.references import ReferenceExecutionStore
    from drama_plugin.generation.contracts import GenerationTask
    from drama_plugin.runtime.contracts import ArtifactReference, DecisionCategory, RunMode, RuntimeRun
    from drama_plugin.execution.transport import ProviderTransport
    from drama_plugin.execution.review import CreativeReviewer
    from drama_plugin.execution.audio import AudioConsumer
    from drama_plugin.execution.contracts import Authorization, FinishingRecipe
    from drama_plugin.execution.live_transport import FinancialTerms
    from drama_plugin.execution.review import ReviewResponse
    from drama_plugin.film.ports import FilmCanonAuthor, FilmDirectionAuthor, FilmReviewer, ExecutionRecipeSource
    from drama_plugin.film.contracts import LanguageMetadata, DeliveryProfile
    from drama_plugin.creative_engine.authors import CanonAuthor, CreativeDirectionAuthor, ProfessionalAuthor
    from drama_plugin.creative_engine.contracts import SourceBody, VersionRef, RouteRequest, RevisionRequest

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

    def __init__(self, root: Path, config: DramaPluginConfig, manifest: PluginManifest, providers: ProviderBundle, skills: SkillRegistry, tools: ToolRegistry, http_clients: list[HttpProviderClient] | None = None, *, production_artifact_roots: tuple[Path, ...] = (), production_package_store: ProductionPackageStore | None = None, gate_finding_store: GateFindingStore | None = None, generation_artifact_store: GenerationArtifactStore | None = None, reference_execution_store: ReferenceExecutionStore | None = None, ledger_path: Path | str | None = None, test_foundation: bool = False, target_transports: dict[str, ProviderTransport] | None = None, target_reviewer: CreativeReviewer | None = None, target_audio: AudioConsumer | None = None, target_media_root: Path | None = None, creative_root: Path | None = None, canon_author: CanonAuthor | None = None, direction_author: CreativeDirectionAuthor | None = None, professional_author: ProfessionalAuthor | None = None, film_canon_author: FilmCanonAuthor | None = None, film_direction_author: FilmDirectionAuthor | None = None, film_reviewer: FilmReviewer | None = None, film_recipes: ExecutionRecipeSource | None = None, target_formal_media: bool = False) -> None:
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
        from drama_plugin.creative_engine.store import CreativeVersionStore, CreativeStateStore
        from drama_plugin.creative_engine.sources import CreativeAwareSources, CreativeAwareProfessional
        self.creative_versions = CreativeVersionStore(creative_root if creative_root else
            (self.ledger.path.parent / (self.ledger.path.name + ".creative") if self.ledger else
             Path(mkdtemp(prefix="target-creative-foundation-"))))
        creative_sources = CreativeAwareSources(assembly_sources, self.creative_versions)
        self.professional_design = ProfessionalDesignResolver(CreativeAwareProfessional(
            LegacyProfessionalDesignSources(creative_sources), creative_sources), author=professional_author)
        self.shot_assembler = ShotAssembler(creative_sources, self.professional_design, self.execution_references)
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
        from drama_plugin.generation.operation import OperationResolver
        from drama_plugin.generation.compiler import PromptCompiler
        from drama_plugin.generation.capability import GenerationCapability
        from drama_plugin.generation.policy import GenerationPolicy, generation_workflow, media_review_workflow
        self.operation_resolver = OperationResolver(self.creative_versions, self.ledger, config.video_route_policy) if self.ledger else None
        self.prompt_compiler = PromptCompiler(self.production_packages, self.generation_artifacts,
            PackageReader(creative_sources, LegacyExecutionReferences(production_artifact_roots), self.operation_resolver),
            media_reader=BoundMediaReader(tools))
        self.generation_capability = GenerationCapability(self.prompt_compiler, self.generation_artifacts, self.gate_governance)
        generation_flow = generation_workflow()
        from drama_plugin.execution.capability import TargetExecution
        from drama_plugin.execution.store import ExecutionStore
        from drama_plugin.execution.media import LocalMediaStore
        from drama_plugin.execution.policy import execution_workflow
        self.execution = None
        execution_native = {}
        execution_flow = execution_workflow()
        if self.ledger is not None:
            self.execution = TargetExecution(ExecutionStore(self.ledger),
                LocalMediaStore(target_media_root if target_media_root is not None else
                    self.ledger.path.parent / (self.ledger.path.name + ".media")),
                self.gate_governor, self.gate_findings, transports=target_transports,
                reviewer=target_reviewer, audio=target_audio, operations=self.operation_resolver)
            if target_formal_media:
                from drama_plugin.execution.formal_media import FormalMediaStore
                self.execution.media = FormalMediaStore(self.execution.media.directory, providers.media, self.execution.store)
            execution_native = self.execution.registrations()
        self.legacy_boundary = LegacyBoundary()
        self.legacy_recovery = LegacyRecovery(providers.memory, self.legacy_boundary)
        from drama_plugin.creative_engine.capability import CreativeEngineCapabilities
        from drama_plugin.creative_engine.policy import CreativePolicy, creative_workflow, dependency_workflow
        self.creative = CreativeEngineCapabilities(self.creative_versions, CreativeStateStore(self.ledger),
            self.production_packages, self.gate_governor, self.gate_findings,
            canon_author, direction_author, self.professional_design)
        creative_flow, dependency_flow = creative_workflow(), dependency_workflow()
        from drama_plugin.film.store import FilmStore
        from drama_plugin.film.capability import FilmCapabilities
        from drama_plugin.film.policy import FilmPolicy, film_workflow, film_revision_workflow
        self.film = FilmCapabilities(self, FilmStore(self.ledger, self.creative_versions),
            canon=film_canon_author, direction=film_direction_author, reviewer=film_reviewer, recipes=film_recipes) if self.ledger else None
        film_native = self.film.registrations() if self.film else {}
        film_flows = {film_workflow().workflow_id: film_workflow(), film_revision_workflow().workflow_id: film_revision_workflow()} if self.film else {}
        self.runtime = RuntimeEngine(TargetCapabilityRouter({**package_capability.registrations(),
            **self.gate_governance.registrations(), **self.generation_capability.registrations(), **execution_native, **self.creative.registrations(), **film_native},
            LegacyCapabilityBridge.from_tools(tools), self.legacy_boundary), store=runs,
            workflows={**foundation_workflows(), workflow.workflow_id: workflow,
                governance_workflow.workflow_id: governance_workflow, generation_flow.workflow_id: generation_flow,
                execution_flow.workflow_id: execution_flow, creative_flow.workflow_id: creative_flow,
                dependency_flow.workflow_id: dependency_flow, **film_flows,
                "package-to-reviewed-media:v1": media_review_workflow()},
            policies={mode: FilmPolicy(mode, self.gate_findings, self.film.store, self.gate_governor) if self.film else CreativePolicy(mode, self.gate_findings) for mode in RunMode})
        self.creative.runtime = self.runtime
        for mode_policy in self.runtime._policies.values():
            if isinstance(mode_policy, GenerationPolicy):
                mode_policy.mainline_ledger = self.ledger
        self.generation_capability.on_ready = self._bind_media_execution
        self.context = ContextBuilder(providers.context)
        self._http_clients = http_clients or []
        self._fish_client = (
            providers.role_dubbing.fish
            if isinstance(providers.role_dubbing, FishRoleDubbingProvider)
            else None
        )

    @classmethod
    def load(cls, root: Path | str | None = None, config_path: Path | str | None = None, *, mock_data: MockDramaData | None = None, production_artifact_roots: tuple[Path, ...] = (), production_package_store: ProductionPackageStore | None = None, gate_finding_store: GateFindingStore | None = None, generation_artifact_store: GenerationArtifactStore | None = None, reference_execution_store: ReferenceExecutionStore | None = None, ledger_path: Path | str | None = None, target_transports: dict[str, ProviderTransport] | None = None, target_reviewer: CreativeReviewer | None = None, target_audio: AudioConsumer | None = None, target_media_root: Path | None = None, creative_root: Path | None = None, canon_author: CanonAuthor | None = None, direction_author: CreativeDirectionAuthor | None = None, professional_author: ProfessionalAuthor | None = None, film_canon_author: FilmCanonAuthor | None = None, film_direction_author: FilmDirectionAuthor | None = None, film_reviewer: FilmReviewer | None = None, film_recipes: ExecutionRecipeSource | None = None, target_formal_media: bool = False) -> "DramaPlugin":
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
        from drama_plugin.creative_engine.backends import compose_authors
        formal_canon, formal_direction, formal_professional = compose_authors(
            config.text_composition, plugin_root / manifest.skills_directory)
        if canon_author is None:
            canon_author = formal_canon
        if direction_author is None:
            direction_author = formal_direction
        if professional_author is None:
            professional_author = formal_professional
        return cls(plugin_root, config, manifest, providers, skills, tools, clients,
                   production_artifact_roots=production_artifact_roots, production_package_store=production_package_store,
                   gate_finding_store=gate_finding_store, generation_artifact_store=generation_artifact_store,
                   reference_execution_store=reference_execution_store, ledger_path=ledger_path,
                   test_foundation=mock_data is not None, target_transports=target_transports,
                   target_reviewer=target_reviewer, target_audio=target_audio, target_media_root=target_media_root,
                   creative_root=creative_root, canon_author=canon_author, direction_author=direction_author,
                   professional_author=professional_author, film_canon_author=film_canon_author, film_direction_author=film_direction_author, film_reviewer=film_reviewer, film_recipes=film_recipes, target_formal_media=target_formal_media)

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

    def create_source_film_run(self, *, work_id: str, source: SourceBody,
                               languages: LanguageMetadata | None = None, profile: DeliveryProfile,
                               rights_refs: tuple[ArtifactReference, ...], route: str, model: str,
                               run_id: str, max_cost_microunits: int = 0,
                               estimated_shot_cost_microunits: int = 0) -> RuntimeRun:
        """Film scope entry: only goal/source, owner metadata and execution policy."""
        if self.film is None:
            raise ConfigurationError("Film production requires durable ProductionLedger")
        if languages is None:
            from drama_plugin.execution.transport import CapabilityAbsent
            raise CapabilityAbsent("SOURCE_ORIGINAL_WORK_LANGUAGE_METADATA_ABSENT")
        from drama_plugin.film.contracts import FilmInput
        from drama_plugin.runtime.contracts import RunMode
        from drama_plugin.film.capability import WORKFLOW
        from drama_plugin.creative_engine.contracts import Authority, Kind
        if source.spoken_language != languages.spoken_language:
            raise ValueError("Source/Canon metadata must explicitly resolve spoken language")
        run = self.runtime.draft_run(work_id=work_id,mode=RunMode.PRODUCTION,workflow_id=WORKFLOW,run_id=run_id)
        source = type(source).model_validate({**source.model_dump(),
            "source_document_language":languages.source_document_language,
            "original_work_language":languages.original_work_language,
            "language_metadata_ref":languages.authority_ref,
            "spoken_language_policy":languages.spoken_language_policy})
        source_ref = self.creative_versions.write(writer=Authority.SOURCE,kind=Kind.SOURCE,
            scope=run.scope,body=source,sources=(),operation=run_id+":film-source")
        self.film.store.bind(run_id,run.scope,FilmInput(source_ref=source_ref,languages=languages,
            profile=profile,rights_refs=rights_refs,route=route,model=model,
            max_cost_microunits=max_cost_microunits,estimated_shot_cost_microunits=estimated_shot_cost_microunits))
        return self.runtime.store.create(run)

    async def resume_source_film_run(self, run_id: str) -> RuntimeRun:
        """One parent action reconciles child waits; callers never select internal tools."""
        if self.film is None:
            raise ConfigurationError("Film production requires durable ProductionLedger")
        from drama_plugin.film.policy import film_workflow, film_revision_workflow
        from drama_plugin.runtime.contracts import CapabilityInput, ResultStatus, RuntimeState
        run = await self.runtime.recover_run(run_id)
        flow = film_workflow() if run.workflow_id == film_workflow().workflow_id else film_revision_workflow()
        if run.workflow_id != flow.workflow_id:
            raise ValueError("Wrong Film workflow")
        if run.state == RuntimeState.WAITING_EXTERNAL:
            key = flow.steps[run.cursor].capability_key
            assert key and run.last_result and run.last_result.external_ref
            result = await self.runtime.executor.execute(key,CapabilityInput(run_id=run_id,
                operation_id=f"{run_id}:{run.cursor}",scope=run.scope))
            if result.status == ResultStatus.WAITING_EXTERNAL:
                return run
            await self.runtime.record_external_result(run_id,external_ref=run.last_result.external_ref,result=result)
        elif run.state == RuntimeState.BLOCKED and run.wait_reason == "INTERRUPTED_CAPABILITY":
            await self.runtime.retry(run_id)
        return await self.runtime.run(run_id)

    def pending_film_decisions(self, run_id: str) -> tuple[RuntimeRun, ...]:
        """Expose genuine decisions only; owner/tool selection remains internal."""
        from drama_plugin.runtime.contracts import RuntimeState
        if self.film is None:
            raise ConfigurationError("Film domain unavailable")
        cp = self.film.store.checkpoint(run_id)
        if cp.revision_child_run_id:
            return self.pending_film_decisions(cp.revision_child_run_id)
        parent = self.runtime.store.load(run_id)
        if parent.state == RuntimeState.WAITING_USER:
            return (parent,)
        children = tuple(self.runtime.store.load(u.production_run_id) for u in cp.units if u.production_run_id)
        return tuple(child for child in children if child.state == RuntimeState.WAITING_USER)

    def create_film_run(self, *, work_id: str, mode: RunMode, scene_id: str | None = None, shot_id: str | None = None,
                        source: SourceBody | None = None, source_ref: VersionRef | None = None,
                        approved_canon_refs: tuple[VersionRef, ...] = (),
                        route: RouteRequest | None = None, run_id: str | None = None,
                        revision: RevisionRequest | None = None,
                        base_refs: tuple[VersionRef, ...] = (),
                        prior_revision_signatures: tuple[str, ...] = ()) -> RuntimeRun:
        """A goal/source is enough; Plugin workflow owns all subsequent owner selection."""
        if self.ledger is None and not self._test_foundation:
            raise ConfigurationError("Target creative production requires ProductionLedger")
        from drama_plugin.creative_engine.contracts import Authority, FilmInput, Kind, RouteRequest
        from drama_plugin.creative_engine.policy import WORKFLOW
        run = self.runtime.draft_run(work_id=work_id, scene_id=scene_id or work_id + ":scene",
            shot_id=shot_id or work_id + ":shot", mode=mode, workflow_id=WORKFLOW, run_id=run_id)
        if (source is None) == (source_ref is None):
            raise ValueError("Select source text/reference or an existing source artifact")
        if source is not None:
            source_ref = self.creative_versions.write(writer=Authority.SOURCE, kind=Kind.SOURCE,
                scope=run.scope, body=source, sources=(), operation=run.run_id + ":source-input")
        assert source_ref is not None
        inputs = FilmInput(source_ref=source_ref, approved_canon_refs=approved_canon_refs,
            route=route or RouteRequest(), revision=revision, base_refs=base_refs,
            prior_revision_signatures=prior_revision_signatures)
        self.creative.state.bind(run.run_id, run.scope, inputs)
        return self.runtime.store.create(run)

    async def reconcile_creative_candidate(self, run_id: str, *, candidate_ref: ArtifactReference) -> RuntimeRun:
        """Explicit system provenance revision only; remain at the same ADOPTION wait."""
        return await self.creative.reconcile_candidate_integrity(run_id, candidate_ref)

    def create_adoption_run(self, candidate_run_id: str, *, run_id: str | None = None) -> RuntimeRun:
        """Experiment remains isolated until a separate Production ADOPTION decision."""
        from drama_plugin.runtime.contracts import RunMode, RuntimeState
        candidate = self.runtime.store.load(candidate_run_id)
        cp = self.creative.state.checkpoint(candidate_run_id)
        if candidate.mode != RunMode.EXPERIMENT or candidate.state != RuntimeState.SUCCEEDED or cp.package_ref is None:
            raise ValueError("A completed reviewed Experiment candidate is required")
        value = self.creative.state.input(candidate_run_id)
        return self.create_film_run(work_id=candidate.scope.work_id, mode=RunMode.PRODUCTION,
            source_ref=value.source_ref, base_refs=cp.refs, route=value.route, run_id=run_id)

    def create_creative_revision_run(self, parent_run_id: str, request: RevisionRequest,
                                     *, run_id: str | None = None) -> RuntimeRun:
        """Route an exact observation to its writer, carrying bounded revision history."""
        from drama_plugin.contracts.base import sha256_canonical
        prior = self.creative.state.input(parent_run_id)
        cp = self.creative.state.checkpoint(parent_run_id)
        parent = self.runtime.store.load(parent_run_id)
        history = prior.prior_revision_signatures
        if prior.revision:
            target = self.creative_versions.resolve(prior.revision.target_ref)
            history = (*history, sha256_canonical([prior.revision.owner, target.kind, prior.revision.instruction]))
        expected_depth = 1 if prior.revision is None else prior.revision.depth + 1
        if request.depth != expected_depth:
            raise ValueError("Revision depth must advance from its parent")
        run = self.create_film_run(work_id=parent.scope.work_id, scene_id=parent.scope.scene_id, shot_id=parent.scope.shot_id, mode=parent.mode,
            source_ref=prior.source_ref, route=prior.route, revision=request, base_refs=cp.refs,
            prior_revision_signatures=history, run_id=run_id)
        from drama_plugin.creative_engine.contracts import CreativeCheckpoint
        self.creative.state.save(run.run_id, run.scope, CreativeCheckpoint(author_rounds=cp.author_rounds))
        return run

    def route_creative_review(self, parent_run_id: str, review_ref: ArtifactReference,
                              *, run_id: str | None = None) -> RuntimeRun:
        """E1 observation routes back to its exact E2 owner without authoring in E1."""
        if self.execution is None:
            raise ConfigurationError("Retained E1 review required")
        from drama_plugin.execution.contracts import CreativeMediaReview
        from drama_plugin.creative_engine.feedback import revision_requests
        review = self.execution.store.get(review_ref, CreativeMediaReview)
        cp = self.creative.state.checkpoint(parent_run_id)
        parent = self.runtime.store.load(parent_run_id)
        if review.scope != parent.scope or review.source_package_ref != cp.package_ref:
            raise ValueError("Review scope/package differs from referenced creative chain")
        prior = self.creative.state.input(parent_run_id).revision
        requests = revision_requests(review, review_ref, cp.refs, self.creative_versions,
            depth=1 if prior is None else prior.depth + 1)
        return self.create_creative_revision_run(parent_run_id, requests[0], run_id=run_id)

    async def resume_film_run(self, run_id: str) -> RuntimeRun:
        """Reconcile the pending registered author action; callers do not select a tool."""
        from drama_plugin.creative_engine.policy import WORKFLOW
        from drama_plugin.runtime.contracts import CapabilityInput, ResultStatus, RuntimeState
        run = await self.runtime.recover_run(run_id)
        if run.workflow_id != WORKFLOW:
            raise ValueError("Only creative runs can resume here")
        if run.state == RuntimeState.WAITING_EXTERNAL:
            workflow = self.runtime._workflows[run.workflow_id]
            key = workflow.steps[run.cursor].capability_key
            assert key and run.last_result and run.last_result.external_ref
            result = await self.runtime.executor.execute(key, CapabilityInput(run_id=run_id,
                operation_id=f"{run_id}:{run.cursor}", scope=run.scope))
            if result.status == ResultStatus.WAITING_EXTERNAL:
                return run
            await self.runtime.record_external_result(run_id, external_ref=run.last_result.external_ref, result=result)
        elif run.state == RuntimeState.BLOCKED and run.wait_reason == "INTERRUPTED_CAPABILITY":
            await self.runtime.retry(run_id)
        return await self.runtime.run(run_id)

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

    def create_media_review_run(self, *, package_ref: ArtifactReference, task: GenerationTask,
                                offline_authorization: Authorization | None = None) -> RuntimeRun:
        """Package goal entry; the existing Runtime chooses every internal action."""
        from drama_plugin.contracts.base import sha256_canonical
        from drama_plugin.generation.policy import MEDIA_WORKFLOW
        from drama_plugin.generation.contracts import GenerationInput
        from drama_plugin.governance.contracts import GovernanceInput
        from drama_plugin.generation.audio import package_scope
        from drama_plugin.execution.review import HumanReviewer
        from drama_plugin.execution.formal_media import FormalMediaStore
        from drama_plugin.execution.live_transport import configured_http_transport
        from drama_plugin.execution.transport import CapabilityAbsent
        if not self.ledger or not self.execution or not self.operation_resolver or not task.profile or not task.unit or not task.owners:
            raise ConfigurationError("Exact durable operation selection/profile/owner bindings required")
        package = self.production_packages.get(package_ref)
        self.operation_resolver.validate(package,task,require_scope=False)
        scope = package_scope(package)
        identity = "media-proof:" + sha256_canonical([package_ref.model_dump(mode="json",by_alias=True),
            task.unit.model_dump(mode="json",by_alias=True,exclude={"scope_decision_ref"}), task.profile.model_dump(mode="json",by_alias=True), task.owners.model_dump(mode="json",by_alias=True)])
        if offline_authorization and (offline_authorization.execution_mode != "OFFLINE_ONLY"
                or offline_authorization.estimated_cost_microunits or offline_authorization.budget_microunits):
            raise ValueError("Goal entry cannot accept a live authorization or paid fixture")
        if not isinstance(self.providers.media,HttpMediaProvider):
            raise CapabilityAbsent("FORMAL_MEDIA_PROVIDER_CONFIGURATION_REQUIRED")
        if not isinstance(self.execution.media,FormalMediaStore):
            self.execution.media = FormalMediaStore(self.execution.media.directory,self.providers.media,self.execution.store)
        if self.execution.reviewer is None:
            self.execution.reviewer = HumanReviewer()
        if task.profile.provider not in self.execution.transports:
            try:
                self.execution.transports[task.profile.provider] = configured_http_transport(model=task.profile.model,
                    receipt_root=self.ledger.path.parent/(self.ledger.path.name+".receipts"),ledger=self.ledger,
                    resolution=task.profile.resolution,aspect_ratio=task.profile.aspect_ratio)
            except CapabilityAbsent:
                pass  # Failure remains an explicit unavailable capability; no fallback.
        try:
            existing = self.runtime.store.load(identity)
            if self.generation_artifacts.inputs(identity).task != task:
                raise ValueError("Goal identity/input conflict")
            return existing
        except KeyError:
            run = self.runtime.draft_run(work_id=scope.work_id,scene_id=scope.scene_id,shot_id=scope.shot_id,
                mode=package.boundary.mode,workflow_id=MEDIA_WORKFLOW,run_id=identity)
            created = self.ledger.create_target_run(run,GovernanceInput(package_ref=package_ref),GenerationInput(task=task))
            if offline_authorization:
                self.ledger.put_index("media-proof-authorization",identity,offline_authorization,scope=scope,once=True)
            return created

    def _bind_media_execution(self, run_id: str, preparation_ref: ArtifactReference) -> None:
        from drama_plugin.execution.contracts import Authorization, ExecutionInput, FinishingRecipe
        from drama_plugin.generation.contracts import GenerationPreparation
        if not self.ledger or not self.execution:
            raise ConfigurationError("Durable execution owner required")
        try:
            auth = Authorization.model_validate(self.ledger.get_index("media-proof-authorization",run_id))
        except KeyError:
            return  # No accepted cost: no operation/grant/placeholder authorization.
        prepared = self.generation_artifacts.get(preparation_ref,GenerationPreparation)
        assert prepared.task.profile
        run = self.runtime.store.load(run_id)
        recipe = FinishingRecipe.seal(scope=run.scope,run_id=run_id,source_package_ref=prepared.source_package_ref,
            preparation_ref=preparation_ref,audio_plan_ref=prepared.audio_plan_ref,approval_ref=auth.approval_ref,native_policy="PRESERVE")
        self.execution.store.put(recipe)
        self.ledger.put_index("execution-input",run_id,ExecutionInput(preparation_ref=preparation_ref,authorization=auth,
            recipe_ref=recipe.artifact_reference(),route=prepared.task.profile.provider),scope=run.scope,once=True)

    async def provide_media_cost_terms(self, run_id: str, terms: FinancialTerms) -> RuntimeRun:
        from drama_plugin.generation.contracts import FinalPromptArtifact, GenerationPreparation
        from drama_plugin.execution.live_transport import TargetHttpTransport
        from drama_plugin.contracts.base import sha256_canonical
        from drama_plugin.runtime.contracts import CapabilityResult, ResultStatus, RuntimeState
        if not self.ledger:
            raise ConfigurationError("Durable terms required")
        run = await self.runtime.recover_run(run_id)
        if run.workflow_id != "package-to-reviewed-media:v1" or run.cursor != 7 or run.state != RuntimeState.WAITING_EXTERNAL:
            raise ValueError("No pending cost terms boundary")
        prepared = self.generation_artifacts.get(self.generation_artifacts.prepared(run_id),GenerationPreparation)
        final = self.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
        terms.validate_current()
        if (terms.preparation_ref != prepared.artifact_reference() or terms.profile != prepared.task.profile
                or terms.wire_payload_hash != sha256_canonical(TargetHttpTransport.preview(prepared,final))):
            raise ValueError("Exact preparation/wire financial terms required")
        self.ledger.put_index("media-proof-cost-terms",run_id,terms,scope=run.scope,once=True)
        assert run.last_result and run.last_result.external_ref
        await self.runtime.record_external_result(run_id,external_ref=run.last_result.external_ref,
            result=CapabilityResult(status=ResultStatus.SUCCEEDED,artifact_refs=(terms.preparation_ref,)))
        return await self.runtime.run(run_id)

    async def provide_human_media_review(self, run_id: str, *, media_ref: ArtifactReference,
                                        context_hash: str, response: ReviewResponse) -> RuntimeRun:
        from drama_plugin.runtime.contracts import CapabilityResult, ResultStatus, RuntimeState
        if not self.execution:
            raise ConfigurationError("Execution owner required")
        run = await self.runtime.recover_run(run_id)
        if run.workflow_id != "package-to-reviewed-media:v1" or run.state != RuntimeState.WAITING_EXTERNAL or run.cursor != 11:
            raise ValueError("No pending human operation review")
        ref = self.execution.record_human_review(run_id,media_ref=media_ref,context_hash=context_hash,response=response)
        assert run.last_result and run.last_result.external_ref
        await self.runtime.record_external_result(run_id,external_ref=run.last_result.external_ref,
            result=CapabilityResult(status=ResultStatus.SUCCEEDED,artifact_refs=(ref,)))
        return await self.runtime.run(run_id)

    def create_execution_run(self, *, run_id: str, mode: RunMode,
                             preparation_ref: ArtifactReference, authorization: Authorization,
                             recipe: FinishingRecipe, route: str) -> RuntimeRun:
        """E1 starts from approved preparation; never recompiles or adopts Canon."""
        if self.execution is None:
            raise ConfigurationError("Target execution requires durable ProductionLedger")
        from drama_plugin.execution.contracts import ExecutionInput
        from drama_plugin.execution.policy import WORKFLOW
        from drama_plugin.generation.contracts import GenerationPreparation
        prepared = self.execution.derived(preparation_ref, GenerationPreparation)
        scope = self.production_packages.get(prepared.source_package_ref).scope
        run = self.runtime.draft_run(work_id=scope.work.artifact_ref,
            scene_id=scope.scene.artifact_ref, shot_id=scope.shot.artifact_ref,
            mode=mode, workflow_id=WORKFLOW, run_id=run_id)
        if recipe.preparation_ref != preparation_ref or recipe.audio_plan_ref != prepared.audio_plan_ref:
            raise ValueError("Finishing recipe must pin the selected preparation/audio plan")
        return self.execution.store.create_run(run, ExecutionInput(preparation_ref=preparation_ref,
            authorization=authorization, recipe_ref=recipe.artifact_reference(), route=route), recipe)

    async def resume_execution_run(self, run_id: str) -> RuntimeRun:
        """Reconcile a pending domain capability; Runtime still owns state progression."""
        if self.execution is None:
            raise ConfigurationError("Target execution requires durable ProductionLedger")
        from drama_plugin.execution.policy import WORKFLOW, execution_workflow
        from drama_plugin.runtime.contracts import CapabilityInput, ResultStatus, RuntimeState
        run = await self.runtime.recover_run(run_id)
        from drama_plugin.generation.policy import MEDIA_WORKFLOW, media_review_workflow
        if run.workflow_id not in {WORKFLOW,MEDIA_WORKFLOW}:
            raise ValueError("Only E1 execution runs can use execution reconciliation")
        flow = media_review_workflow() if run.workflow_id == MEDIA_WORKFLOW else execution_workflow()
        if run.workflow_id == MEDIA_WORKFLOW:
            package_ref = self.gate_findings.inputs(run_id).package_ref
            assert package_ref is not None
            self.create_media_review_run(package_ref=package_ref,
                task=self.generation_artifacts.inputs(run_id).task)
        if run.state == RuntimeState.WAITING_EXTERNAL:
            if run.workflow_id == MEDIA_WORKFLOW and run.cursor in {7,11}:
                return run  # Needs actual quote or human result, never synthetic completion.
            key = flow.steps[run.cursor].capability_key
            assert key and run.last_result and run.last_result.external_ref
            result = await self.runtime.executor.execute(key, CapabilityInput(run_id=run_id,
                operation_id=f"{run_id}:{run.cursor}", scope=run.scope))
            if result.status in {ResultStatus.WAITING_EXTERNAL, ResultStatus.RETRYABLE_FAILURE}:
                return run
            await self.runtime.record_external_result(run_id, external_ref=run.last_result.external_ref, result=result)
        elif run.state == RuntimeState.BLOCKED and run.wait_reason == "INTERRUPTED_CAPABILITY":
            await self.runtime.retry(run_id)
        return await self.runtime.run(run_id)

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
        from drama_plugin.creative_engine.policy import WORKFLOW as CREATIVE_WORKFLOW
        if self.film and run.workflow_id in {"source-to-final-film:v1", "final-film-revision:v1"}:
            cp = self.film.store.checkpoint(run_id)
            expected = cp.plan_ref if run.workflow_id == "source-to-final-film:v1" and run.cursor == 3 else cp.final_ref
            if source_ref != expected:
                raise ValueError("Film decision must bind exact immutable candidate/hash")
        if run.workflow_id == CREATIVE_WORKFLOW:
            candidate = self.creative.state.checkpoint(run_id).candidate_ref
            if source_ref != candidate:
                raise ValueError("Adoption must bind the exact candidate version-set hash")
        assert action.decision is not None
        record = UserDecisionRecord.seal(run_id=run_id, scope=run.scope,
            decision_id=decision_id, category=action.decision.category,
            accepted=accepted, source_ref=source_ref,
            terms_hash=self._media_decision_terms(run_id,source_ref) if run.workflow_id == "package-to-reviewed-media:v1" else None)
        ref = self.reviews.put_user_decision(record)
        if accepted and run.workflow_id == "package-to-reviewed-media:v1":
            self._consume_media_decision(run_id,ref,record.category)
        return await self.runtime.decide(run_id, decision_id=decision_id,
            accepted=accepted, decision_ref=ref)

    def _media_decision_terms(self, run_id: str, source_ref: ArtifactReference | None) -> str:
        from drama_plugin.execution.live_transport import FinancialTerms
        assert self.ledger
        run = self.runtime.store.load(run_id)
        if run.cursor == 4:
            task = self.generation_artifacts.inputs(run_id).task
            package = self.gate_findings.inputs(run_id).package_ref
            if not task.unit or package is None or package != source_ref:
                raise ValueError("Scope decision must bind exact Package/unit/duties")
            return task.unit.terms_hash(package)
        terms = FinancialTerms.model_validate(self.ledger.get_index("media-proof-cost-terms",run_id))
        terms.validate_current()
        if run.cursor != 8 or source_ref != terms.preparation_ref:
            raise ValueError("Cost decision must bind exact preparation/terms")
        from drama_plugin.generation.contracts import GenerationPreparation, FinalPromptArtifact
        from drama_plugin.execution.live_transport import TargetHttpTransport
        from drama_plugin.contracts.base import sha256_canonical
        prepared = self.generation_artifacts.get(terms.preparation_ref,GenerationPreparation)
        final = self.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
        if terms.profile != prepared.task.profile or terms.wire_payload_hash != sha256_canonical(TargetHttpTransport.preview(prepared,final)):
            raise ValueError("APPROVED_FINANCIAL_TERMS_DRIFT")
        assert self.operation_resolver
        self.operation_resolver.validate(self.production_packages.get(prepared.source_package_ref),prepared.task)
        return terms.fingerprint

    def _consume_media_decision(self, run_id: str, ref: ArtifactReference, category: DecisionCategory) -> None:
        from drama_plugin.generation.contracts import GenerationInput
        from drama_plugin.execution.contracts import Authorization
        from drama_plugin.execution.live_transport import FinancialTerms
        from drama_plugin.runtime.contracts import DecisionCategory
        from math import ceil
        assert self.ledger and self.execution
        run = self.runtime.store.load(run_id)
        if category == DecisionCategory.ART_APPROVAL:
            values = self.generation_artifacts.inputs(run_id)
            assert values.task.unit
            task = type(values.task).model_validate({**values.task.model_dump(),"unit":{
                **values.task.unit.model_dump(),"scope_decision_ref":ref}})
            self.ledger.put_index("generation-input",run_id,GenerationInput(task=task),scope=run.scope)
            return
        terms = FinancialTerms.model_validate(self.ledger.get_index("media-proof-cost-terms",run_id))
        terms.validate_current()
        authorization = Authorization(approval_ref=ref,authorized=True,budget_microunits=terms.budget_microunits,
            estimated_cost_microunits=ceil(terms.cost_quote.amount*1000000),execution_mode="CONTROLLED_LIVE")
        self.ledger.put_index("media-proof-authorization",run_id,authorization,scope=run.scope,once=True)
        self._bind_media_execution(run_id,terms.preparation_ref)
        # TargetExecution derives and validates the grant from this exact receipt
        # only at dispatch. No operation is reserved by financial preview/approval.

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
