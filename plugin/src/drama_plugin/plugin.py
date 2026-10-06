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
from pydantic import JsonValue, ValidationError

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
from drama_plugin.generation.policy import MEDIA_WORKFLOW, MEDIA_WORKFLOWS, media_cursor


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

    def __init__(self, root: Path, config: DramaPluginConfig, manifest: PluginManifest, providers: ProviderBundle, skills: SkillRegistry, tools: ToolRegistry, http_clients: list[HttpProviderClient] | None = None, *, production_artifact_roots: tuple[Path, ...] = (), production_package_store: ProductionPackageStore | None = None, gate_finding_store: GateFindingStore | None = None, generation_artifact_store: GenerationArtifactStore | None = None, reference_execution_store: ReferenceExecutionStore | None = None, ledger_path: Path | str | None = None, test_foundation: bool = False, target_transports: dict[str, ProviderTransport] | None = None, target_reviewer: CreativeReviewer | None = None, target_audio: AudioConsumer | None = None, target_media_root: Path | None = None, creative_root: Path | None = None, canon_author: CanonAuthor | None = None, direction_author: CreativeDirectionAuthor | None = None, professional_author: ProfessionalAuthor | None = None, film_canon_author: FilmCanonAuthor | None = None, film_direction_author: FilmDirectionAuthor | None = None, film_reviewer: FilmReviewer | None = None, film_recipes: ExecutionRecipeSource | None = None, target_formal_media: bool = False, legacy_reads: bool = False) -> None:
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
        from drama_plugin.runtime.store import RunStore
        from drama_plugin.production.store import PackageStore
        from drama_plugin.production.references import ReferenceStore
        from drama_plugin.governance.store import FindingStore
        from drama_plugin.generation.store import GenerationStore
        from drama_plugin.persistence.stores import DurableReviewStore
        runs: RunStore
        self.production_packages: PackageStore
        self.execution_references: ReferenceStore
        self.gate_findings: FindingStore
        self.generation_artifacts: GenerationStore
        self.reviews: DurableReviewStore | None
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
        from drama_plugin.production.references import ReferenceBoundSources
        from drama_plugin.creative_engine.store import CreativeVersionStore, CreativeStateStore
        from drama_plugin.creative_engine.sources import NativeCreativeSources, CreativeAwareSources, CreativeAwareProfessional
        self.creative_versions = CreativeVersionStore(creative_root if creative_root else
            (self.ledger.path.parent / (self.ledger.path.name + ".creative") if self.ledger else
             Path(mkdtemp(prefix="target-creative-foundation-"))))
        # Historical read compatibility is explicitly selected by the caller.
        # New Target goals compose native owners only; no failed native read falls back.
        from drama_plugin.production.sources import AssemblySources
        from drama_plugin.professional_design.resolver import ProfessionalDesignBackend
        creative_sources: AssemblySources
        professional_backend: ProfessionalDesignBackend
        native_sources = NativeCreativeSources(self.creative_versions, references=self.execution_references)
        if legacy_reads:
            assembly_sources = ReferenceBoundSources(LegacyAssemblySources(tools, production_artifact_roots), self.execution_references)
            creative_sources = CreativeAwareSources(assembly_sources, self.creative_versions)
            professional_backend = CreativeAwareProfessional(LegacyProfessionalDesignSources(creative_sources), creative_sources)
        else:
            creative_sources = native_sources
            professional_backend = native_sources
        self.professional_design = ProfessionalDesignResolver(professional_backend, author=professional_author)
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
            PackageReader(creative_sources, LegacyExecutionReferences(production_artifact_roots) if legacy_reads else None, self.operation_resolver),
            media_reader=providers.media)
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
            assert isinstance(self.gate_findings, DurableGateFindingStore)
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
        from drama_plugin.film.policy import FilmPolicy, film_workflow, film_revision_workflow, film_media_workflow
        self.film = FilmCapabilities(self, FilmStore(self.ledger, self.creative_versions),
            canon=film_canon_author, direction=film_direction_author, reviewer=film_reviewer, recipes=film_recipes) if self.ledger else None
        film_native = self.film.registrations() if self.film else {}
        film_flows = {flow.workflow_id: flow for flow in (film_workflow(), film_revision_workflow(), film_media_workflow())} if self.film else {}
        self.runtime = RuntimeEngine(TargetCapabilityRouter({**package_capability.registrations(),
            **self.gate_governance.registrations(), **self.generation_capability.registrations(), **execution_native, **self.creative.registrations(), **film_native},
            LegacyCapabilityBridge.from_tools(tools) if legacy_reads else None, self.legacy_boundary), store=runs,
            workflows={**foundation_workflows(), workflow.workflow_id: workflow,
                governance_workflow.workflow_id: governance_workflow, generation_flow.workflow_id: generation_flow,
                execution_flow.workflow_id: execution_flow, creative_flow.workflow_id: creative_flow,
                dependency_flow.workflow_id: dependency_flow, **film_flows,
                **{wid: media_review_workflow(wid) for wid in MEDIA_WORKFLOWS}},
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
    def load(cls, root: Path | str | None = None, config_path: Path | str | None = None, *, mock_data: MockDramaData | None = None, production_artifact_roots: tuple[Path, ...] = (), production_package_store: ProductionPackageStore | None = None, gate_finding_store: GateFindingStore | None = None, generation_artifact_store: GenerationArtifactStore | None = None, reference_execution_store: ReferenceExecutionStore | None = None, ledger_path: Path | str | None = None, target_transports: dict[str, ProviderTransport] | None = None, target_reviewer: CreativeReviewer | None = None, target_audio: AudioConsumer | None = None, target_media_root: Path | None = None, creative_root: Path | None = None, canon_author: CanonAuthor | None = None, direction_author: CreativeDirectionAuthor | None = None, professional_author: ProfessionalAuthor | None = None, film_canon_author: FilmCanonAuthor | None = None, film_direction_author: FilmDirectionAuthor | None = None, film_reviewer: FilmReviewer | None = None, film_recipes: ExecutionRecipeSource | None = None, target_formal_media: bool = False, legacy_reads: bool = False) -> "DramaPlugin":
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
        if film_canon_author is None:
            film_canon_author = formal_canon
        if film_direction_author is None:
            film_direction_author = formal_direction
        return cls(plugin_root, config, manifest, providers, skills, tools, clients,
                   production_artifact_roots=production_artifact_roots, production_package_store=production_package_store,
                   gate_finding_store=gate_finding_store, generation_artifact_store=generation_artifact_store,
                   reference_execution_store=reference_execution_store, ledger_path=ledger_path,
                   test_foundation=mock_data is not None, target_transports=target_transports,
                   target_reviewer=target_reviewer, target_audio=target_audio, target_media_root=target_media_root,
                   creative_root=creative_root, canon_author=canon_author, direction_author=direction_author,
                   professional_author=professional_author, film_canon_author=film_canon_author, film_direction_author=film_direction_author, film_reviewer=film_reviewer, film_recipes=film_recipes, target_formal_media=target_formal_media, legacy_reads=legacy_reads)

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
                               estimated_shot_cost_microunits: int = 0, workflow_id: str | None = None) -> RuntimeRun:
        """Film scope entry: only goal/source, owner metadata and execution policy."""
        if self.film is None:
            raise ConfigurationError("Film production requires durable ProductionLedger")
        if languages is None:
            from drama_plugin.execution.transport import CapabilityAbsent
            raise CapabilityAbsent("SOURCE_ORIGINAL_WORK_LANGUAGE_METADATA_ABSENT")
        from drama_plugin.film.contracts import FilmInput
        from drama_plugin.runtime.contracts import RunMode
        from drama_plugin.film.policy import film_media_workflow
        from drama_plugin.creative_engine.contracts import Authority, Kind
        if source.spoken_language != languages.spoken_language:
            raise ValueError("Source/Canon metadata must explicitly resolve spoken language")
        run = self.runtime.draft_run(work_id=work_id,mode=RunMode.PRODUCTION,workflow_id=workflow_id or film_media_workflow().workflow_id,run_id=run_id)
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
        try:
            existing = self.runtime.store.load(run_id)
        except KeyError:
            return self.runtime.store.create(run)
        if (existing.scope, existing.mode, existing.workflow_id, existing.workflow_fingerprint) != (
                run.scope, run.mode, run.workflow_id, run.workflow_fingerprint):
            raise ValueError("Film entry identity conflict")
        return existing

    async def resume_source_film_run(self, run_id: str) -> RuntimeRun:
        """One parent action reconciles child waits; callers never select internal tools."""
        if self.film is None:
            raise ConfigurationError("Film production requires durable ProductionLedger")
        from drama_plugin.film.policy import film_workflow, film_revision_workflow, film_media_workflow
        from drama_plugin.runtime.contracts import CapabilityInput, ResultStatus, RuntimeState, DecisionCategory
        run = await self.runtime.recover_run(run_id)
        cp = self.film.store.checkpoint(run_id)
        if run.state==RuntimeState.FAILED and run.last_result and run.last_result.code in {'FINANCIAL_AUTHORITY_ALREADY_CONSUMED','RECOVERY_TRANSPORT_READ_ONLY'}:
            await self._repair_source_film_revision_dispatch(run_id)
            run=self.runtime.store.load(run_id)
        if cp.media_batch_ref and not any(b.batch_ref == cp.media_batch_ref for b in run.execution_batches):
            from drama_plugin.film.contracts import FilmMediaBatch
            batch = self.film.store.get(cp.media_batch_ref, FilmMediaBatch)
            self.operation_resolver.decision(batch.authorization_ref, category=DecisionCategory.ADOPTION,
                scope=run.scope, source_ref=self.generation_artifacts.inputs(batch.opening_run_id).task.owners.rights_request_ref)
            run = await self.runtime.resume_media_batch(run_id,batch_ref=cp.media_batch_ref,decision_ref=batch.authorization_ref)
        if (cp.media_batch_ref and run.state == RuntimeState.SUCCEEDED and cp.scene_media_run_ids
                and self.runtime.store.load(cp.scene_media_run_ids[-1]).state == RuntimeState.PLANNED):
            # A later human-authorized adjacent phase can arrive after this batch
            # completed. Preserve that completion and re-enter only its media step.
            from drama_plugin.generation.operation import continuation_frame, validate_continuation
            child_id = cp.scene_media_run_ids[-1]
            task = self.generation_artifacts.inputs(child_id).task
            validate_continuation(self.ledger, task)
            _, predecessor, _, _ = continuation_frame(self.ledger, task.continuation.frame_ref,
                allow_unverified_audio=bool(task.continuation.allow_unverified_audio))
            previous_id = cp.scene_media_run_ids[-2] if len(cp.scene_media_run_ids) > 1 else self.source_film_media_opening(run_id)
            if (predecessor.run_id != previous_id or self.runtime.store.load(previous_id).state != RuntimeState.SUCCEEDED
                    or self.gate_findings.inputs(child_id).package_ref != cp.units[0].package_ref):
                raise ValueError('IMMEDIATE_REVIEWED_PREDECESSOR_REQUIRED')
            self.operation_resolver.decision(task.owners.rights_decision_ref, category=DecisionCategory.ADOPTION,
                scope=run.scope, source_ref=task.owners.rights_request_ref)
            run = await self.runtime.resume_media_batch(run_id,batch_ref=cp.media_batch_ref,
                decision_ref=task.owners.rights_decision_ref,continuation_goal_hash=cp.scene_media_goal_hash)
        if cp.media_batch_ref and run.state == RuntimeState.FAILED and run.last_result and run.last_result.code == 'TECHNICAL_MEDIA_FAILURE':
            await self._repair_source_film_video_duration(run_id)
            run = self.runtime.store.load(run_id)
        if cp.media_batch_ref and run.state == RuntimeState.FAILED and run.last_result and run.last_result.code == 'HUMAN_REVIEW_CONTEXT_MISMATCH':
            await self._repair_source_film_review_response(run_id)
            run = self.runtime.store.load(run_id)
        if (cp.media_batch_ref and run.state == RuntimeState.FAILED and run.last_result
                and run.last_result.code == 'EXECUTION_IDENTITY_UNAVAILABLE'
                and run.last_result.exception_type == 'KeyError'):
            # Same-batch cache inspection repair: no child execution or paid
            # request existed at this boundary; completed old batches are retained.
            child_id = self.source_film_media_opening(run_id)
            child = self.runtime.store.load(child_id)
            with self.ledger.transaction() as db:
                paid = db.execute('SELECT 1 FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL',(child_id,)).fetchone()
            if child.state == RuntimeState.PLANNED and child.cursor == 0 and paid is None:
                inspection = self.film.inspect_media_execution(CapabilityInput(run_id=run_id,operation_id=run_id+':5',scope=run.scope))
                run = await self.runtime.repair_inspection_failure(run_id,expected_revision=run.revision,
                    cursor=5,capability_key='film.execute:v1',input_fingerprint=inspection.revision.input_fingerprint)
        flows = {f.workflow_id: f for f in (film_workflow(), film_revision_workflow(), film_media_workflow())}
        flow = flows.get(run.workflow_id)
        if flow is None:
            raise ValueError("Wrong Film workflow")
        if run.workflow_id != flow.workflow_id:
            raise ValueError("Wrong Film workflow")
        if run.state == RuntimeState.FAILED and run.last_result and run.last_result.code in {'GOVERNED_HARD_STOP','EXECUTION_REVISION_CHANGED'}:
            await self._repair_official_frame_compilation(run_id)
            await self._repair_adjacent_reference_readiness(run_id)
            run = self.runtime.store.load(run_id)
        if (run.state == RuntimeState.FAILED and run.last_result is not None
                and run.last_result.code in {"EXTERNAL_RECONCILIATION_ERROR", "FORMAL_MEDIA_NOT_FOUND"}):
            await self._repair_completed_media_import_configuration(run_id)
            run = self.runtime.store.load(run_id)
        if run.state in {RuntimeState.WAITING_EXTERNAL,RuntimeState.WAITING_USER} and run.last_result and run.last_result.external_ref:
            await self.runtime.reconcile_wait(run_id)
        elif run.state == RuntimeState.BLOCKED and run.wait_reason == "INTERRUPTED_CAPABILITY":
            await self.runtime.retry(run_id)
        return await self.runtime.run(run_id)

    async def _repair_source_film_revision_dispatch(self, run_id: str) -> None:
        """Repair a revised intent collision only while its dispatch is provably RESERVED."""
        from drama_plugin.film.contracts import FilmSegmentRevision
        from drama_plugin.execution.contracts import ExecutionOperation,ProviderAttempt,OperationState
        from drama_plugin.generation.contracts import GenerationPreparation
        from drama_plugin.runtime.contracts import RuntimeState,ArtifactReference,DecisionCategory
        parent=self.runtime.store.load(run_id);cp=self.film.store.checkpoint(run_id)
        links=[r.artifact_ref for r in parent.last_result.artifact_refs if r.owner=='runtime']
        if len(links)!=1 or links[0] not in (cp.scene_media_run_ids or ()):
            return
        child=self.runtime.store.load(links[0])
        if (child.state!=RuntimeState.FAILED or not child.last_result
                or child.last_result.code not in {'FINANCIAL_AUTHORITY_ALREADY_CONSUMED','RECOVERY_TRANSPORT_READ_ONLY'}
                or media_cursor(child.workflow_id,child.cursor)!=9):
            return
        revision_ref=next((r for r in cp.scene_media_revision_refs or ()
            if self.film.store.get(r,FilmSegmentRevision).replacement_run_id==child.run_id),None)
        if revision_ref is None:return
        with self.ledger.transaction() as db:
            row=db.execute('SELECT operation_ref_json,dispatch_state FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL',(child.run_id,)).fetchone()
        if not row or row['dispatch_state'] not in {'RESERVED','FAILED'}:return
        op=self.execution.store.get(ArtifactReference.model_validate_json(row['operation_ref_json']),ExecutionOperation)
        check=self.execution.store.checkpoint(op.artifact_reference())
        attempt=self.execution.store.get(check.attempt_ref,ProviderAttempt)
        if check.receipt_ref or attempt.ordinal!=1 or check.progress.attempt_history:
            return
        if child.last_result.code=='RECOVERY_TRANSPORT_READ_ONLY':
            if check.state==OperationState.FAILED:self.execution.store.repair_unsubmitted_transport(op.artifact_reference())
            elif check.state!=OperationState.RESERVED:return
        elif check.state!=OperationState.RESERVED:return
        prepared=self.generation_artifacts.get(op.preparation_ref,GenerationPreparation)
        self.operation_resolver.decision(op.authorization.approval_ref,category=DecisionCategory.COST_APPROVAL,
            scope=child.scope,source_ref=op.preparation_ref)
        self.ledger.put_index('film-segment-dispatch-revision',child.run_id,revision_ref,scope=child.scope,once=True)
        self.execution.dispatch_rights_key(op,attempt)
        self._compose_media_owners(prepared.task,run_id=child.run_id)
        await self.runtime.repair_revision_dispatch(child.run_id,expected_revision=child.revision,
            capability_key='execution.provider:v1',decision_ref=op.authorization.approval_ref)
        await self.runtime.repair_revision_dispatch(run_id,expected_revision=parent.revision,
            capability_key='film.execute:v1',decision_ref=op.authorization.approval_ref)

    async def _repair_source_film_review_response(self, run_id: str) -> None:
        """Retain an actual scoped REVISE after a reviewer response protocol error."""
        from drama_plugin.runtime.contracts import RuntimeState,ArtifactReference
        from drama_plugin.execution.contracts import ExecutionOperation,MediaBinding,CreativeMediaReview
        from drama_plugin.execution.review import HumanReviewer,MockReviewer
        parent=self.runtime.store.load(run_id);cp=self.film.store.checkpoint(run_id)
        links=[r.artifact_ref for r in parent.last_result.artifact_refs if r.owner=='runtime']
        if len(links)!=1 or links[0] not in (cp.scene_media_run_ids or ()):
            return
        child=self.runtime.store.load(links[0])
        if (media_cursor(child.workflow_id,child.cursor)!=11 or child.state not in {RuntimeState.FAILED,RuntimeState.READY}
                or not child.last_result or child.last_result.code not in {'HUMAN_REVIEW_CONTEXT_MISMATCH',None}):
            return
        with self.ledger.transaction() as db:
            row=db.execute('SELECT operation_ref_json FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL',(child.run_id,)).fetchone()
        op=self.execution.store.get(ArtifactReference.model_validate_json(row[0]),ExecutionOperation)
        checkpoint=self.execution.store.checkpoint(op.artifact_reference())
        if checkpoint.progress.video_creative_ref:
            review=self.execution.store.get(checkpoint.progress.video_creative_ref,CreativeMediaReview)
        else:
            if isinstance(self.execution.reviewer,(HumanReviewer,MockReviewer)) or self.execution.reviewer is None:
                return  # No external attestation is fabricated or bypassed.
            media=self.execution.store.get(checkpoint.progress.video_ref,MediaBinding)
            review=await self.execution._creative(op,checkpoint,media.media)
            if review.outcome!='REVISE':
                return
            self.execution.store.progress(op.artifact_reference(),video_creative_ref=self.execution.store.put(review))
        if review.outcome!='REVISE' or review.operation_ref!=op.artifact_reference():
            return
        if child.state==RuntimeState.FAILED:
            await self.runtime.repair_review_response(child.run_id,expected_revision=child.revision,
                capability_key='execution.media_review:v1',decision_ref=op.authorization.approval_ref)
        await self.runtime.repair_review_response(run_id,expected_revision=parent.revision,
            capability_key='film.execute:v1',decision_ref=op.authorization.approval_ref)

    async def _repair_source_film_video_duration(self, run_id: str) -> None:
        """Re-probe exact bytes after the confirmed container-vs-video duration bug."""
        from drama_plugin.execution.contracts import ExecutionOperation,MediaBinding,TechnicalMediaReview
        from drama_plugin.generation.contracts import GenerationPreparation
        from drama_plugin.runtime.contracts import ArtifactReference,RuntimeState
        parent = self.runtime.store.load(run_id)
        cp = self.film.store.checkpoint(run_id)
        child_id = next((r.artifact_ref for r in parent.last_result.artifact_refs if r.owner == 'runtime'),None)
        if child_id not in (self.source_film_media_opening(run_id),*(cp.scene_media_run_ids or ())):
            return
        child = self.runtime.store.load(child_id)
        if child.state != RuntimeState.FAILED or not child.last_result or child.last_result.code != 'TECHNICAL_MEDIA_FAILURE':
            return
        with self.ledger.transaction() as db:
            row = db.execute('SELECT operation_ref_json FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL',(child_id,)).fetchone()
        op = self.execution.store.get(ArtifactReference.model_validate_json(row[0]),ExecutionOperation)
        checkpoint = self.execution.store.checkpoint(op.artifact_reference())
        progress = checkpoint.progress
        old = self.execution.store.get(progress.video_technical_ref,TechnicalMediaReview)
        if old.outcome != 'FAIL' or old.findings != ('RESULT_DURATION_MISMATCH',) or old.policy_version != 'technical-media-v1':
            return
        binding = self.execution.store.get(progress.video_ref,MediaBinding)
        task = self.generation_artifacts.get(op.preparation_ref,GenerationPreparation).task
        fresh = self.execution._technical(op,checkpoint,binding.media,None,audio_expected=task.profile.native_audio)
        if fresh.outcome != 'PASS':
            return
        repaired = TechnicalMediaReview.seal(**{**fresh.model_dump(exclude={'fingerprint'}),'supersedes_ref':progress.video_technical_ref})
        repaired_ref = self.execution.store.put(repaired)
        self.execution.store.progress(op.artifact_reference(),video_technical_repair_ref=repaired_ref)
        self._compose_media_owners(task,run_id=child_id)
        await self.runtime.repair_video_duration_review(child_id,expected_revision=child.revision,
            capability_key='execution.media_review:v1',decision_ref=op.authorization.approval_ref)
        await self.runtime.repair_video_duration_review(run_id,expected_revision=parent.revision,
            capability_key='film.execute:v1',decision_ref=op.authorization.approval_ref)

    async def _repair_official_frame_compilation(self, run_id: str) -> None:
        """Repair the reference compiler's omitted bounded-audio policy, before creation."""
        from drama_plugin.runtime.contracts import RuntimeState,ExecutionRevision,CapabilityInput,DecisionCategory
        from drama_plugin.contracts.base import sha256_canonical
        from drama_plugin.governance.contracts import GateCode
        parent=self.runtime.store.load(run_id);cp=self.film.store.checkpoint(run_id)
        if not cp.media_batch_ref or not parent.last_result or parent.last_result.code!='GOVERNED_HARD_STOP':
            return
        links=[r.artifact_ref for r in parent.last_result.artifact_refs if r.owner=='runtime']
        if len(links)!=1 or links[0] not in (cp.scene_media_run_ids or ()):
            return
        child=self.runtime.store.load(links[0])
        if child.state!=RuntimeState.FAILED or media_cursor(child.workflow_id,child.cursor)!=4 or not child.last_result:
            return
        task=self.generation_artifacts.inputs(child.run_id).task
        if not task.continuation or not task.continuation.allow_unverified_audio:
            return
        with self.ledger.transaction() as db:
            if db.execute('SELECT 1 FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL',(child.run_id,)).fetchone():
                raise ValueError('REFERENCE_REPAIR_MUST_PRECEDE_PAID_OPERATION')
        failed_gates=[r for r in child.last_result.artifact_refs if r.owner=='gate-decision']
        if len(failed_gates)!=1:
            return
        old=self.gate_findings.decision(failed_gates[0])
        findings=[self.gate_findings.finding(r) for r in old.finding_refs]
        required=[f for f in findings if f.required]
        if not required or any(f.code!=GateCode.REQUEST_INPUT_MISSING or f.owner!='production-selection' for f in required):
            return
        diagnostics=[d for f in required for d in self.generation_artifacts.diagnostics(f.evidence_ref) if d.required]
        if not diagnostics or any(d.code!='EXECUTION_REQUIRED_MISSING' or d.owner!='production-selection' for d in diagnostics):
            return
        package_ref=self.gate_findings.inputs(child.run_id).package_ref
        result=await self.prompt_compiler.compile(package_ref,task)
        fresh=self.generation_artifacts.diagnostics(result.diagnostics_ref)
        if not result.preparation_ref or any(d.required for d in fresh):
            return
        if any(d.required for d in await self.prompt_compiler.validate_execution_sources(result.preparation_ref)):
            return
        auth=task.owners.rights_decision_ref
        self.operation_resolver.decision(auth,category=DecisionCategory.ADOPTION,scope=child.scope,
            source_ref=task.owners.rights_request_ref,allow_parent_scope=True)
        self.generation_artifacts.set_prepared(child.run_id,result.preparation_ref)
        from drama_plugin.generation.checks import execution_findings
        fixed=self.gate_governor.govern(execution_findings(fresh,scope=child.scope,evidence_ref=result.diagnostics_ref),
            scope=child.scope,mode=child.mode,package_ref=package_ref)
        self.gate_findings.put_decision(fixed,run_id=child.run_id)
        current=child.execution_revision or ExecutionRevision(fingerprint=sha256_canonical(task),
            input_fingerprint=sha256_canonical([package_ref.model_dump(mode='json'),task.model_dump(mode='json')]))
        await self.runtime.repair_resolved_reference_gate(child.run_id,expected_revision=child.revision,decision_ref=auth,current=current)
        inspection=self.film.inspect_media_execution(CapabilityInput(run_id=run_id,operation_id=f'{run_id}:{parent.cursor}',scope=parent.scope))
        await self.runtime.repair_resolved_reference_gate(run_id,expected_revision=parent.revision,decision_ref=auth,current=inspection.revision)

    async def _repair_adjacent_reference_readiness(self, run_id: str) -> None:
        """Repair only the confirmed native-reference omission, before any paid reservation."""
        from drama_plugin.runtime.contracts import RuntimeState,ExecutionRevision,CapabilityInput,DecisionCategory
        from drama_plugin.generation.contracts import GenerationPreparation
        from drama_plugin.contracts.base import sha256_canonical
        from drama_plugin.governance.contracts import GateCode
        parent=self.runtime.store.load(run_id);cp=self.film.store.checkpoint(run_id)
        links=[r.artifact_ref for r in parent.last_result.artifact_refs if r.owner=='runtime']
        if len(links)!=1 or links[0] not in (cp.scene_media_run_ids or ()):
            return
        child=self.runtime.store.load(links[0])
        previous_repair=next((r for r in child.external_repairs if r.cursor==child.cursor
            and r.capability_key=='generation.ready:v1' and r.failed_result.code=='GOVERNED_HARD_STOP'),None)
        already_repaired=previous_repair is not None
        if (child.state not in {RuntimeState.FAILED,RuntimeState.READY} or child.last_result is None
                or child.last_result.code not in {'GOVERNED_HARD_STOP','EXECUTION_REVISION_CHANGED'}
                or child.last_result.code=='EXECUTION_REVISION_CHANGED' and not already_repaired
                or media_cursor(child.workflow_id,child.cursor)!=6
                or child.state==RuntimeState.READY and not already_repaired):
            return
        ref=self.generation_artifacts.prepared(child.run_id)
        prepared=self.generation_artifacts.get(ref,GenerationPreparation)
        if not prepared.task.execution_reference_refs:
            return
        with self.ledger.transaction() as db:
            if db.execute('SELECT 1 FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL',(child.run_id,)).fetchone():
                raise ValueError('REFERENCE_REPAIR_MUST_PRECEDE_PAID_OPERATION')
        # A crash may have written the replacement Gate before either Runtime save.
        # Read the exact retained failure evidence, never the mutable latest index.
        failed_result=previous_repair.failed_result if previous_repair else child.last_result
        failed_gates=[r for r in failed_result.artifact_refs if r.owner=='gate-decision']
        if len(failed_gates)!=1:
            return
        old_gate=self.gate_findings.decision(failed_gates[0])
        old_findings=[self.gate_findings.finding(r) for r in old_gate.finding_refs]
        if not old_findings or any(f.code!=GateCode.REQUEST_INPUT_MISSING for f in old_findings):
            return
        diagnostics=[d for f in old_findings for d in self.generation_artifacts.diagnostics(f.evidence_ref)]
        if any(d.required and d.code!='REFERENCE_INPUT_UNRESOLVED' for d in diagnostics):
            return
        if any(d.required for d in await self.prompt_compiler.validate_execution_sources(ref)):
            return
        package=self.production_packages.get(prepared.source_package_ref)
        self.operation_resolver.validate(package,prepared.task)
        validation=await self.shot_assembler.validate_sources(package)
        if validation.status != 'READY':
            return
        auth=prepared.task.owners.rights_decision_ref
        self.operation_resolver.decision(auth,category=DecisionCategory.ADOPTION,scope=child.scope,
            source_ref=prepared.task.owners.rights_request_ref,allow_parent_scope=True)
        current=child.execution_revision or ExecutionRevision(
            fingerprint=sha256_canonical(['reference-readiness-v2',ref.model_dump(mode='json',by_alias=True)]),
            input_fingerprint=sha256_canonical([prepared.source_package_ref.model_dump(mode='json',by_alias=True),
                prepared.task.model_dump(mode='json',by_alias=True),ref.model_dump(mode='json',by_alias=True)]))
        if child.state==RuntimeState.FAILED:
            fixed=self.gate_governor.govern((),scope=child.scope,mode=child.mode,package_ref=prepared.source_package_ref)
            self.gate_findings.put_decision(fixed,run_id=child.run_id)
            await self.runtime.repair_resolved_reference_gate(child.run_id,expected_revision=child.revision,decision_ref=auth,current=current)
        inspection=self.film.inspect_media_execution(CapabilityInput(run_id=run_id,operation_id=f'{run_id}:{parent.cursor}',scope=parent.scope))
        await self.runtime.repair_resolved_reference_gate(run_id,expected_revision=parent.revision,decision_ref=auth,current=inspection.revision)

    def source_film_media_opening(self, run_id: str) -> str:
        from drama_plugin.film.contracts import FilmMediaBatch
        cp = self.film.store.checkpoint(run_id)
        return (self.film.store.get(cp.media_batch_ref,FilmMediaBatch).opening_run_id
            if cp.media_batch_ref else cp.units[0].generation_run_id)

    async def restart_source_film_media(self, run_id: str, *, batch_id: str,
                                         tasks: tuple[GenerationTask, ...], allow_unverified_audio: bool = False) -> RuntimeRun:
        """A new bounded media batch on the same adopted Film; historical requests stay immutable."""
        from drama_plugin.film.contracts import FilmCheckpoint, FilmMediaBatch
        from drama_plugin.contracts.base import sha256_canonical
        from drama_plugin.runtime.contracts import RuntimeState
        from drama_plugin.generation.operation import validate_segment_progress
        parent = self.runtime.store.load(run_id)
        cp = self.film.store.checkpoint(run_id)
        goal_hash = sha256_canonical([t.model_dump(mode='json',by_alias=True) for t in tasks])
        if cp.media_batch_ref:
            current = self.film.store.get(cp.media_batch_ref,FilmMediaBatch)
            if current.batch_id == batch_id:
                if current.goal_hash != goal_hash or current.allow_unverified_audio != allow_unverified_audio:
                    raise ValueError('MEDIA_BATCH_IDENTITY_CHANGED')
                return await self.resume_source_film_run(run_id)
        if (parent.workflow_id != 'source-to-reviewed-media:v1' or parent.state != RuntimeState.SUCCEEDED
                or parent.cursor != 6 or not 3 <= len(tasks) <= 4 or not cp.units):
            raise ValueError('COMPLETED_FILM_BOUNDED_REPRODUCTION_REQUIRED')
        unit = cp.units[0]
        opening = tasks[0]
        if (opening.input_mode != 'text_to_video' or opening.execution_reference_refs or opening.continuation
                or opening.return_last_frame is not True or opening.unit.action_refs[0].path[-2:] != ('0','action')):
            raise ValueError('FRESH_TEXT_OPENING_WITH_OFFICIAL_TAIL_REQUIRED')
        package = self.production_packages.get(unit.package_ref)
        for index, task in enumerate(tasks):
            self.operation_resolver.validate(package,task)
            if (task.owners.adopted_refs != unit.refs or task.return_last_frame is not True
                    or task.profile.provider != cp.operation_task.profile.provider
                    or task.profile.model != cp.operation_task.profile.model
                    or task.profile.resolution != cp.operation_task.profile.resolution
                    or task.profile.aspect_ratio != cp.operation_task.profile.aspect_ratio
                    or task.profile.native_audio != cp.operation_task.profile.native_audio):
                raise ValueError('ADJACENT_SCENE_CONTINUITY_ROUTE_REQUIRED')
            if index:
                if task.continuation or task.execution_reference_refs or task.input_mode != 'image_to_video':
                    raise ValueError('DEFERRED_CONTINUATION_INPUT_REQUIRED')
                validate_segment_progress(task.unit,tuple(t.unit for t in reversed(tasks[:index])))
        child = self.create_media_review_run(package_ref=unit.package_ref,task=opening)
        if child.run_id in (unit.generation_run_id,*(cp.scene_media_run_ids or ())):
            raise ValueError('MEDIA_BATCH_MUST_HAVE_NEW_OPENING')
        batch = FilmMediaBatch.seal(scope=parent.scope,run_id=run_id,film_version=cp.film_version,
            batch_id=batch_id,authorization_ref=opening.owners.rights_decision_ref,opening_run_id=child.run_id,
            goal_hash=goal_hash,allow_unverified_audio=allow_unverified_audio,previous_checkpoint=cp)
        ref = self.film.store.put(batch)
        self.film.store.save(run_id,parent.scope,FilmCheckpoint.model_validate({**cp.model_dump(),
            'media_batch_ref':ref,'media_batch_opening_review_ref':None,
            'scene_media_run_ids':None,'scene_media_review_refs':None,'scene_media_pending_tasks':tasks[1:],
            'scene_media_goal_hash':goal_hash}))
        return await self.resume_source_film_run(run_id)

    def source_film_preview_manifest(self, run_id: str) -> str:
        """Rebuild from immutable completions, never accumulated concat text."""
        from drama_plugin.execution.contracts import ExecutionOperation
        from drama_plugin.film.assembly import scene_segments
        from drama_plugin.runtime.contracts import ArtifactReference
        cp = self.film.store.checkpoint(run_id)
        refs = []
        for child in (self.source_film_media_opening(run_id), *(cp.scene_media_run_ids or ())):
            with self.ledger.transaction() as db:
                row = db.execute('SELECT operation_ref_json FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL', (child,)).fetchone()
            op_ref = ArtifactReference.model_validate_json(row[0])
            refs.append(self.execution.store.checkpoint(op_ref).progress.video_ref)
        segments = scene_segments(tuple(refs), self.execution.store)
        return 'ffconcat version 1.0\n' + ''.join("file '"+str(self.execution.media.path(b.media)).replace("'", "'\\''")+"'\n" for _, b in segments)

    async def revise_source_film_segment(self, run_id: str, *, slot: int, task: GenerationTask) -> RuntimeRun:
        """Use the existing native media child for a scoped revised candidate, never replay paid success."""
        from drama_plugin.film.contracts import FilmCheckpoint, FilmSegmentRevision
        from drama_plugin.execution.contracts import ExecutionOperation,CreativeMediaReview
        from drama_plugin.generation.contracts import GenerationTask,CameraExecutionDirection
        from drama_plugin.runtime.contracts import ArtifactReference,RuntimeState,CapabilityInput
        from drama_plugin.generation.operation import validate_continuation
        from drama_plugin.production.references import ReferenceExecutionBinding
        from drama_plugin.contracts.base import sha256_canonical
        parent=self.runtime.store.load(run_id);cp=self.film.store.checkpoint(run_id)
        for ref in cp.scene_media_revision_refs or ():
            prior=self.film.store.get(ref,FilmSegmentRevision)
            if prior.slot==slot and self.generation_artifacts.inputs(prior.replacement_run_id).task.camera_direction_ref==task.camera_direction_ref:
                return await self.resume_source_film_run(run_id)
        ids=list(cp.scene_media_run_ids or ())
        if (parent.workflow_id!='source-to-reviewed-media:v1' or parent.cursor!=5
                or parent.state not in {RuntimeState.WAITING_USER,RuntimeState.WAITING_EXTERNAL,RuntimeState.FAILED}
                or slot!=len(ids)-1 or len(cp.scene_media_revision_refs or ())>=3):
            raise ValueError('EXACT_FAILED_ADJACENT_CANDIDATE_REQUIRED')
        old_id=ids[slot];old=self.generation_artifacts.inputs(old_id).task
        with self.ledger.transaction() as db:
            row=db.execute('SELECT operation_ref_json FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL',(old_id,)).fetchone()
        if row is None:
            failed=self.runtime.store.load(old_id)
            if (parent.state!=RuntimeState.FAILED or failed.state!=RuntimeState.FAILED
                    or failed.cursor!=2 or not failed.last_result or failed.last_result.code!='GOVERNED_HARD_STOP'):
                raise ValueError('EXACT_PREPAYMENT_PLANNING_FAILURE_REQUIRED')
            evidence=next(r for r in failed.last_result.artifact_refs if r.owner=='gate-decision')
            gate=self.gate_findings.decision(evidence)
            required=[self.gate_findings.finding(r) for r in gate.finding_refs if self.gate_findings.finding(r).required]
            if not required or any(f.code.value!='PROVIDER_HARD_LIMIT' or f.owner!='prompt-compiler' for f in required):
                raise ValueError('EXACT_PREPAYMENT_PLANNING_FAILURE_REQUIRED')
        else:
            op_ref=ArtifactReference.model_validate_json(row[0]);progress=self.execution.store.checkpoint(op_ref).progress
            review=self.execution.store.get(progress.video_creative_ref,CreativeMediaReview)
            if review.outcome!='REVISE':raise ValueError('BOUNDED_CAMERA_REVISION_REQUIRED')
            evidence=progress.video_creative_ref
        if (not task.camera_direction_ref or old.unit!=task.unit
                or old.profile!=task.profile or old.owners!=task.owners or old.continuation!=task.continuation
                or task.execution_reference_refs!=old.execution_reference_refs):
            raise ValueError('BOUNDED_CAMERA_REVISION_REQUIRED')
        self.operation_resolver.validate(self.production_packages.get(cp.units[0].package_ref),task)
        ref=old.execution_reference_refs[0]
        raw,_,_=self.ledger.get_artifact('reference-execution-binding',ArtifactReference(owner=ref.owner.value,artifact_ref=ref.artifact_ref,version=ref.version))
        endpoint=ReferenceExecutionBinding.model_validate(raw)
        endpoint=endpoint.model_copy(update={'binding_id':endpoint.binding_id+'-camera-'+task.camera_direction_ref.artifact_ref[-16:],
            'endpoint_state':'Begin from the supplied actual final frame, inheriting its axis, pose and current framing. Subsequent camera changes follow the selected narrative camera direction; the segment boundary is not a movement trigger.'})
        task=GenerationTask.model_validate({**task.model_dump(),'execution_reference_refs':(self.execution_references.register(endpoint),)})
        validate_continuation(self.ledger,task)
        if parent.state==RuntimeState.FAILED:
            fresh=await self.prompt_compiler.compile(cp.units[0].package_ref,task)
            if not fresh.preparation_ref or any(d.required for d in self.generation_artifacts.diagnostics(fresh.diagnostics_ref)):
                raise ValueError('REVISED_PREPARATION_MUST_PASS_BEFORE_RESUME')
            if any(d.required for d in await self.prompt_compiler.validate_execution_sources(fresh.preparation_ref)):
                raise ValueError('REVISED_PREPARATION_MUST_PASS_BEFORE_RESUME')
        child=self.create_media_review_run(package_ref=cp.units[0].package_ref,task=task)
        if child.run_id==old_id:raise ValueError('REVISED_REQUEST_REQUIRED')
        record=FilmSegmentRevision.seal(scope=parent.scope,run_id=run_id,film_version=cp.film_version,slot=slot,
            previous_run_id=old_id,replacement_run_id=child.run_id,review_ref=evidence,
            camera_direction_ref=task.camera_direction_ref,previous_checkpoint=cp)
        revision_ref=self.film.store.put(record);ids[slot]=child.run_id
        self.ledger.put_index('film-segment-dispatch-revision',child.run_id,revision_ref,scope=child.scope,once=True)
        self.film.store.save(run_id,parent.scope,FilmCheckpoint.model_validate({**cp.model_dump(),
            'scene_media_run_ids':tuple(ids),'scene_media_review_refs':(cp.scene_media_review_refs or ())[:slot],
            'scene_media_pending_tasks':(), 'scene_media_revision_refs':(*(cp.scene_media_revision_refs or ()),revision_ref)}))
        if parent.state==RuntimeState.FAILED:
            binding=self.generation_artifacts.get(task.camera_direction_ref,CameraExecutionDirection)
            inspection=self.film.inspect_media_execution(CapabilityInput(run_id=run_id,operation_id=f'{run_id}:5',scope=parent.scope))
            await self.runtime.resume_unsubmitted_segment_revision(run_id,expected_revision=parent.revision,
                previous_child_id=old_id,revision_ref=revision_ref,decision_ref=binding.approval_ref,current=inspection.revision)
        return await self.resume_source_film_run(run_id)

    async def reconcile_historical_unknown(self, operation_ref: ArtifactReference) -> ArtifactReference:
        """One bounded read for an already completed business goal; financial uncertainty stays attributed once."""
        from drama_plugin.execution.contracts import ExecutionOperation,ProviderAttempt,OperationState,HistoricalUnknownAccounting
        from drama_plugin.generation.contracts import GenerationPreparation
        from drama_plugin.execution.live_transport import TargetHttpTransport
        op=self.execution.store.get(operation_ref,ExecutionOperation);cp=self.execution.store.checkpoint(operation_ref)
        if cp.progress.historical_unknown_accounting_ref:return cp.progress.historical_unknown_accounting_ref
        if cp.state!=OperationState.SUCCEEDED or not cp.progress.video_ref or len(cp.progress.attempt_history or ())!=1:
            raise ValueError('COMPLETED_SUPPLEMENT_WITH_HISTORICAL_UNKNOWN_REQUIRED')
        old=cp.progress.attempt_history[0]
        if old.state!=OperationState.UNKNOWN:raise ValueError('HISTORICAL_UNKNOWN_REQUIRED')
        self._compose_media_owners(self.generation_artifacts.get(op.preparation_ref,GenerationPreparation).task,run_id=op.run_id)
        transport=self.execution.transports[op.route];recovered=None;code='NO_EXACT_TASK_RECOVERED'
        try:
            if isinstance(transport,TargetHttpTransport):
                recovered=await transport.recover_unknown(op,self.execution.store.get(old.attempt_ref,ProviderAttempt))
            if recovered:code='EXACT_TASK_RECOVERED_ACCOUNTING_PENDING'
        except Exception:code='TASK_LOOKUP_TRANSIENT_ACCOUNTING_PENDING'
        receipt_ref=self.execution.store.put(recovered) if recovered else None
        record=HistoricalUnknownAccounting.seal(scope=op.scope,run_id=op.run_id,source_package_ref=op.source_package_ref,
            operation_ref=operation_ref,unknown_attempt_ref=old.attempt_ref,completed_by_media_ref=cp.progress.video_ref,
            recovered_receipt_ref=receipt_ref,query_code=code,reserved_cost_microunits=old.reserved_cost_microunits)
        ref=self.execution.store.put(record)
        self.execution.store.progress(operation_ref,historical_unknown_accounting_ref=ref)
        return ref

    async def retain_source_film_last_frame(self, child_id: str) -> ArtifactReference:
        """Persist the provider-original JPEG for any completed segment, including the last."""
        from drama_plugin.execution.contracts import ExecutionOperation, MediaBinding, ProviderReceipt, ProviderAttempt, ContinuationFrame
        from drama_plugin.execution.media import LocalMediaStore, probe_jpeg
        from drama_plugin.execution.transport import CapabilityAbsent
        from drama_plugin.generation.contracts import GenerationPreparation
        from drama_plugin.runtime.contracts import ArtifactReference
        from urllib.parse import urlsplit
        with self.ledger.transaction() as db:
            row = db.execute('SELECT operation_ref_json FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL', (child_id,)).fetchone()
        op_ref = ArtifactReference.model_validate_json(row[0])
        op = self.execution.store.get(op_ref,ExecutionOperation)
        progress = self.execution.store.checkpoint(op_ref).progress
        source_ref = progress.video_ref
        source = self.execution.store.get(source_ref,MediaBinding)
        previous = self.generation_artifacts.get(op.preparation_ref,GenerationPreparation).task
        # Historical tasks that never requested the official frame are not probed.
        if previous.return_last_frame is not True:
            raise ValueError('OFFICIAL_TAIL_NOT_REQUESTED')
        try:
            frame_ref = ArtifactReference.model_validate(self.ledger.get_index('continuation-frame', source_ref.artifact_ref))
            frame = self.execution.store.get(frame_ref, ContinuationFrame)
            LocalMediaStore(self.execution.media.directory).path(frame.media)
        except KeyError:
            receipt = self.execution.store.get(source.receipt_ref, ProviderReceipt)
            self._compose_media_owners(previous, run_id=child_id)
            transport = self.execution.transports[receipt.provider]
            if not receipt.last_frame_url:
                # One read-only lookup; this path never creates or retries a task.
                from drama_plugin.contracts.video import ProviderTask
                raw = await transport.adapter._http('GET', '/contents/generations/tasks/'+receipt.remote_identity)
                queried = transport.adapter.normalize(raw, ProviderTask(provider=receipt.provider,model=op.model,
                    provider_task_id=receipt.remote_identity,client_request_id=receipt.client_identity,
                    request_fingerprint=receipt.request_fingerprint,status='SUCCEEDED'))
                attempt = self.execution.store.get(source.attempt_ref, ProviderAttempt)
                receipt = transport.receipt(op, attempt, queried)
            if not receipt.last_frame_url or receipt.state != 'SUCCEEDED':
                raise CapabilityAbsent('PROVIDER_LAST_FRAME_UNAVAILABLE')
            url = urlsplit(receipt.last_frame_url)
            if url.scheme != 'https' or not url.hostname or url.username or url.password:
                raise ValueError('REFERENCE_DELIVERY_REQUIRES_HTTPS')
            response = await transport.adapter.client.get(receipt.last_frame_url)
            response.raise_for_status()
            if not response.content.startswith(b'\xff\xd8\xff'):
                raise ValueError('PROVIDER_LAST_FRAME_JPEG_REQUIRED')
            media_store = LocalMediaStore(self.execution.media.directory)
            image = media_store.retain(response.content, kind='IMAGE', mime='image/jpeg')
            width, height = probe_jpeg(media_store.path(image))
            from drama_plugin.execution.contracts import TechnicalMediaReview
            source_probe = self.execution.store.get(progress.current_video_technical_ref, TechnicalMediaReview).observation
            if (width, height) != (source_probe.width, source_probe.height):
                raise ValueError('PROVIDER_LAST_FRAME_DIMENSIONS_MISMATCH')
            receipt_ref = self.execution.store.put(receipt)
            frame = ContinuationFrame.seal(scope=source.scope,run_id=source.run_id,source_package_ref=source.source_package_ref,
                predecessor_media_ref=source_ref,receipt_ref=receipt_ref,media=image,width=width,height=height)
            frame_ref = self.execution.store.put(frame)
            self.ledger.put_index('continuation-frame',source_ref.artifact_ref,frame_ref,scope=source.scope,once=True)
        return frame_ref

    async def prepare_source_film_continuation(self, run_id: str, *, task: GenerationTask) -> GenerationTask:
        """Freeze the immediately preceding native result as a new endpoint input.

        No create POST, creative rewrite or authority/financial approval is made here.
        A missing official last frame is an explicit input limitation, not a fallback
        to the opening video or an invented trusted local extraction.
        """
        from drama_plugin.execution.contracts import ExecutionOperation, MediaBinding, ProviderReceipt, ProviderAttempt, ContinuationFrame
        from drama_plugin.execution.media import LocalMediaStore, probe_jpeg
        from drama_plugin.execution.transport import CapabilityAbsent
        from drama_plugin.generation.contracts import ContinuationInput, GenerationPreparation, GenerationTask
        from drama_plugin.generation.operation import continuation_context, validate_continuation
        from drama_plugin.film.contracts import FilmMediaBatch
        from drama_plugin.production.references import ReferenceExecutionBinding
        from drama_plugin.runtime.contracts import ArtifactReference, RuntimeState
        from urllib.parse import urlsplit
        cp = self.film.store.checkpoint(run_id)
        previous_id = (cp.scene_media_run_ids or (self.source_film_media_opening(run_id),))[-1]
        previous_run = self.runtime.store.load(previous_id)
        if previous_run.state != RuntimeState.SUCCEEDED or task.input_mode != 'image_to_video':
            raise ValueError('REVIEWED_PREDECESSOR_AND_FIRST_FRAME_ROUTE_REQUIRED')
        if task.continuation:
            validate_continuation(self.ledger, task)
            return task
        with self.ledger.transaction() as db:
            row = db.execute('SELECT operation_ref_json FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL', (previous_id,)).fetchone()
        op_ref = ArtifactReference.model_validate_json(row[0])
        op = self.execution.store.get(op_ref, ExecutionOperation)
        progress = self.execution.store.checkpoint(op_ref).progress
        source_ref = progress.video_ref
        source = self.execution.store.get(source_ref, MediaBinding)
        previous = self.generation_artifacts.get(op.preparation_ref, GenerationPreparation).task
        if task.profile.provider != 'seedance' or task.profile.model != previous.profile.model:
            raise ValueError('ADJACENT_SCENE_CONTINUITY_ROUTE_REQUIRED')
        global_ref = (previous.continuation.global_reference_ref if previous.continuation else
            (task.execution_reference_refs or (None,))[0])
        if global_ref is None:
            # Build global identity/room context exclusively from this batch's new opening.
            from drama_plugin.creative_engine.contracts import Kind
            from drama_plugin.execution.contracts import TechnicalMediaReview
            package = self.production_packages.get(source.source_package_ref)
            selections = await self.prompt_compiler.reader.selections(package)
            reference = next(v for v in selections if v.selection.domain == 'REFERENCE' and isinstance(v.value,dict) and 'references' in v.value)
            subject = next(v.body.facts['presentSubjects'][0]['id'] for r in previous.owners.adopted_refs
                for v in (self.creative_versions.resolve(r),) if v.kind == Kind.PROFESSIONAL and v.body.domain == 'SUBJECTS')
            duties = []
            for row in reference.value['references']:
                if row['priority'] != 'REQUIRED':
                    continue
                role = 'CHARACTER' if 'identity' in row['inputDuty'].lower() else 'LOCATION' if 'topology' in row['inputDuty'].lower() else 'PERFORMANCE'
                duties.append(dict(role=role,necessity='REQUIRED',subject=subject if role in ('CHARACTER','PERFORMANCE') else source.scope.scene_id,purpose=row['inputDuty']))
            probe = self.execution.store.get(progress.current_video_technical_ref,TechnicalMediaReview).observation
            global_ref = self.execution_references.register(ReferenceExecutionBinding(
                binding_id='batch-opening-'+source.media.content_hash,version=1,scope=source.scope,
                media=dict(media_id=source.canonical_media_ref.artifact_ref,version=str(source.canonical_media_ref.version or 1),
                    content_hash=source.media.content_hash,kind='video',semantics=('identity','costume','environment','style','motion','continuity'),
                    duration=probe.duration_ms/1000,width=probe.width,height=probe.height,review_ref=progress.video_creative_ref.artifact_ref),
                duties=tuple(duties),subject_ids=(subject,),role='REFERENCE',authorization_scope='ADOPTED_PRODUCTION_INPUT',
                authority_refs=(reference.selection.reference,)))
        raw, _, _ = self.ledger.get_artifact('reference-execution-binding',
            ArtifactReference(owner=global_ref.owner.value, artifact_ref=global_ref.artifact_ref, version=global_ref.version))
        global_binding = ReferenceExecutionBinding.model_validate(raw)
        if global_binding.source().reference() != global_ref or global_binding.scope != source.scope:
            raise ValueError('GLOBAL_CONTINUITY_REFERENCE_MISMATCH')
        frame_ref = await self.retain_source_film_last_frame(previous_id)
        frame = self.execution.store.get(frame_ref,ContinuationFrame)
        # Retain the opening reference as global context; I2V and multimodal
        # reference_video are mutually exclusive in this provider's wire API.
        endpoint = self.execution_references.register(ReferenceExecutionBinding(
            binding_id='continuation-'+frame.fingerprint,version=1,scope=source.scope,
            media=dict(media_id=frame.media.media_id,version='1',content_hash=frame.media.content_hash,kind='image',
                semantics=global_binding.media.semantics,width=frame.width,height=frame.height,
                review_ref=global_binding.media.review_ref),duties=global_binding.duties,subject_ids=global_binding.subject_ids,
            role='FIRST_FRAME',endpoint_frame_ref=frame_ref,
            endpoint_state='Continue from the supplied actual final frame. Preserve its framing and axis; do not replay the establishing view or reset the camera distance.',
            authorization_scope=global_binding.authorization_scope,authority_refs=global_binding.authority_refs))
        bound = GenerationTask.model_validate({**task.model_dump(), 'execution_reference_refs':(endpoint,),
            'return_last_frame':True, 'continuation':ContinuationInput(predecessor_media_ref=source_ref,frame_ref=frame_ref,
                global_reference_ref=global_ref,context_fact_refs=continuation_context(task.unit,previous.unit),
                allow_unverified_audio=True if cp.media_batch_ref and self.film.store.get(cp.media_batch_ref,FilmMediaBatch).allow_unverified_audio else None)})
        validate_continuation(self.ledger, bound)
        return bound

    def queue_source_film_media(self, run_id: str, *, tasks: tuple[GenerationTask, ...]) -> tuple[str, ...]:
        """Append a bounded adjacent Scene batch to the existing Film execution boundary."""
        from drama_plugin.runtime.contracts import RuntimeState, RuntimeScope
        from drama_plugin.film.contracts import FilmCheckpoint
        if not self.film or not self.operation_resolver or not 1 <= len(tasks) <= 3:
            raise ValueError('BOUNDED_SCENE_CONTINUATION_REQUIRED')
        parent = self.runtime.store.load(run_id)
        cp = self.film.store.checkpoint(run_id)
        from drama_plugin.contracts.base import sha256_canonical
        goal_hash = sha256_canonical([t.model_dump(mode='json',by_alias=True) for t in tasks])
        if parent.workflow_id == 'source-to-reviewed-media:v1' and cp.scene_media_goal_hash == goal_hash:
            return cp.scene_media_run_ids
        active_boundary = (parent.cursor == 5 and parent.state in {
            RuntimeState.READY,RuntimeState.WAITING_USER,RuntimeState.WAITING_EXTERNAL})
        completed_boundary = (parent.cursor == 6 and parent.state == RuntimeState.SUCCEEDED and cp.media_batch_ref is not None)
        if (parent.workflow_id != 'source-to-reviewed-media:v1' or not (active_boundary or completed_boundary)
                or not cp.units or cp.units[0].package_ref is None):
            raise ValueError('EXISTING_FILM_EXECUTION_BOUNDARY_REQUIRED')
        unit = cp.units[0]
        package = self.production_packages.get(unit.package_ref)
        scope = RuntimeScope(work_id=parent.scope.work_id,scene_id=unit.scene_id,shot_id=unit.shot_id)
        from drama_plugin.generation.operation import validate_continuation, continuation_frame, validate_segment_progress
        task = tasks[0]
        if not task.continuation:
            raise ValueError('EXACT_CONTINUATION_FIRST_FRAME_REQUIRED')
        validate_continuation(self.ledger, task)
        _, preceding, _, _ = continuation_frame(self.ledger, task.continuation.frame_ref,
            allow_unverified_audio=bool(task.continuation.allow_unverified_audio))
        queued = cp.scene_media_run_ids or ()
        # Repeated queue calls recover the same child; they do not append it again.
        if queued and self.generation_artifacts.inputs(queued[-1]).task == task and not tasks[1:]:
            return queued
        previous_id = (queued or (self.source_film_media_opening(run_id),))[-1]
        if preceding.run_id != previous_id or self.runtime.store.load(previous_id).state != RuntimeState.SUCCEEDED:
            raise ValueError('IMMEDIATE_REVIEWED_PREDECESSOR_REQUIRED')
        if len(queued) + len(tasks) > 3 or cp.scene_media_pending_tasks:
            raise ValueError('BOUNDED_SCENE_CONTINUATION_REQUIRED')
        for previous, following in zip(tasks,tasks[1:]):
            if following.continuation is not None or following.input_mode != 'image_to_video':
                raise ValueError('DEFERRED_CONTINUATION_INPUT_REQUIRED')
            validate_segment_progress(following.unit,(previous.unit,))
        for task in tasks:
            self.operation_resolver.validate(package,task,require_scope=False)
            if (not task.execution_reference_refs or task.owners.adopted_refs != unit.refs
                    or task.profile.provider != cp.operation_task.profile.provider
                    or task.profile.model != cp.operation_task.profile.model
                    or task.profile.resolution != cp.operation_task.profile.resolution
                    or task.profile.aspect_ratio != cp.operation_task.profile.aspect_ratio
                    or task.profile.native_audio != cp.operation_task.profile.native_audio):
                raise ValueError('ADJACENT_SCENE_CONTINUITY_ROUTE_REQUIRED')
        # Later descriptors contain source/profile authority but no frozen media
        # goal or preparation until their actual predecessor exists.
        ids = (self.create_media_review_run(package_ref=unit.package_ref,task=tasks[0]).run_id,)
        if len(set(ids)) != len(ids) or unit.generation_run_id in ids:
            raise ValueError('SCENE_CONTINUATION_DUPLICATE_OPERATION')
        self.film.store.save(run_id,parent.scope,FilmCheckpoint.model_validate({**cp.model_dump(),
            'scene_media_run_ids':(*queued,*ids),'scene_media_review_refs':cp.scene_media_review_refs or (),
            'scene_media_pending_tasks':tasks[1:],'scene_media_goal_hash':goal_hash}))
        return (*queued,*ids)

    async def _repair_completed_media_import_configuration(self, run_id: str) -> None:
        """Only the same successful recovery operation may repair this local preflight failure."""
        from drama_plugin.execution.contracts import ExecutionOperation, ProviderAttempt, OperationState
        from drama_plugin.execution.live_transport import FinancialTerms
        from drama_plugin.generation.contracts import GenerationPreparation
        from drama_plugin.generation.policy import media_review_workflow
        from drama_plugin.providers.http.media_source import open_media_source
        from drama_plugin.runtime.contracts import RuntimeState, DecisionCategory, ArtifactReference
        if not self.execution or not self.reviews or not self.ledger:
            return
        parent = self.runtime.store.load(run_id)
        cp = self.film.store.checkpoint(run_id)
        children = [r.artifact_ref for r in parent.last_result.artifact_refs if r.owner == "runtime"]
        if len(children) != 1 or not any(u.generation_run_id == children[0] for u in cp.units):
            return
        child = self.runtime.store.load(children[0])
        if (child.state != RuntimeState.FAILED or child.last_result is None
                or child.last_result.code != parent.last_result.code
                or (child.last_result.code == "EXTERNAL_RECONCILIATION_ERROR"
                    and child.last_result.exception_type != "MediaImportSourceError")
                or child.workflow_id not in MEDIA_WORKFLOWS
                or media_review_workflow(child.workflow_id).steps[child.cursor].capability_key != "execution.media_intake:v1"):
            return
        decision_ref = ArtifactReference.model_validate(self.ledger.get_index("execution-recovery-authorization", child.run_id))
        decision = self.reviews.user_decision(decision_ref)
        terms = FinancialTerms.model_validate(decision.financial_terms)
        operation = self.execution.store.get(terms.recovery_operation_ref, ExecutionOperation)
        checkpoint = self.execution.store.checkpoint(operation.artifact_reference())
        attempt = self.execution.store.get(checkpoint.attempt_ref, ProviderAttempt)
        if (not decision.accepted or decision.category != DecisionCategory.COST_APPROVAL
                or decision.run_id != child.run_id or decision.scope != child.scope
                or operation.run_id != child.run_id or operation.scope != child.scope
                or operation.preparation_ref != decision.source_ref
                or attempt.ordinal != 2 or attempt.approval_ref != decision_ref
                or checkpoint.state != OperationState.SUCCEEDED or checkpoint.receipt_ref is None
                or checkpoint.progress.intake_media is None or checkpoint.progress.video_ref is not None):
            raise ValueError("Exact successful operation and unchanged intake cache required")
        prepared = self.generation_artifacts.get(operation.preparation_ref, GenerationPreparation)
        self._compose_media_owners(prepared.task, run_id=child.run_id)
        path = self.execution.media.path(checkpoint.progress.intake_media)
        async with open_media_source(path.as_uri()):
            pass  # Existing configured allowlist must authorize the exact retained file.
        if child.last_result.code == "FORMAL_MEDIA_NOT_FOUND":
            from drama_plugin.execution.formal_media import FormalMediaStore
            if not isinstance(self.execution.media, FormalMediaStore):
                raise ValueError("Canonical Media owner required")
            self.execution.media.repair_definitely_rejected_import(operation, checkpoint.progress.intake_media)
        await self.runtime.repair_media_intake_configuration(child.run_id, expected_revision=child.revision,
            capability_key="execution.media_intake:v1", decision_ref=decision_ref)
        await self.runtime.repair_media_intake_configuration(run_id, expected_revision=parent.revision,
            capability_key="film.execute:v1", decision_ref=decision_ref)

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
        from drama_plugin.runtime.contracts import CapabilityInput, ResultStatus, RuntimeState, DecisionCategory
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
                GenerationTask.model_validate({"input_mode":self.execution_references.mode(scope)}),
                cached_preparation_ref=cached_preparation_ref)
            run = self.runtime.draft_run(work_id=work_id, scene_id=scene_id, shot_id=shot_id,
                mode=mode, workflow_id=WORKFLOW, run_id=run_id)
            return self.ledger.create_target_run(run, GovernanceInput(package_ref=package_ref), values)
        run = self.runtime.create_run(work_id=work_id, scene_id=scene_id, shot_id=shot_id,
            mode=mode, workflow_id=WORKFLOW, run_id=run_id)
        self.gate_findings.bind(run.run_id, GovernanceInput(package_ref=package_ref))
        self.generation_artifacts.bind(run.run_id, GenerationInput(
            task=task if task is not None else GenerationTask.model_validate({"input_mode":self.execution_references.mode(run.scope)}),
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
        from drama_plugin.runtime.capabilities import TargetCapabilityRouter
        if isinstance(self.runtime.executor, TargetCapabilityRouter) and self.runtime.executor.legacy is not None:
            raise ConfigurationError("Formal media goals require native-only composition; historical reads are recovery-only")
        if not self.ledger or not self.execution or not self.operation_resolver or not task.profile or not task.unit or not task.owners:
            raise ConfigurationError("Exact durable operation selection/profile/owner bindings required")
        package = self.production_packages.get(package_ref)
        self.operation_resolver.validate(package,task,require_scope=False)
        scope = package_scope(package)
        identity_parts = [package_ref.model_dump(mode="json",by_alias=True),
            task.unit.model_dump(mode="json",by_alias=True,exclude={"scope_decision_ref"}), task.profile.model_dump(mode="json",by_alias=True), task.owners.model_dump(mode="json",by_alias=True)]
        if task.execution_reference_refs is not None:
            identity_parts.append([r.model_dump(mode='json',by_alias=True) for r in task.execution_reference_refs])
        if task.continuation is not None or task.return_last_frame is not None:
            identity_parts.append({'continuation':task.continuation.model_dump(mode='json',by_alias=True) if task.continuation else None,
                'returnLastFrame':task.return_last_frame})
        if task.camera_direction_ref is not None:
            identity_parts.append({'cameraDirectionRef':task.camera_direction_ref.model_dump(mode='json',by_alias=True)})
        identity = "media-proof:" + sha256_canonical(identity_parts)
        if offline_authorization and (offline_authorization.execution_mode != "OFFLINE_ONLY"
                or offline_authorization.estimated_cost_microunits or offline_authorization.budget_microunits):
            raise ValueError("Goal entry cannot accept a live authorization or paid fixture")
        self._compose_media_owners(task)
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

    def _compose_media_owners(self, task: GenerationTask, *, run_id: str | None = None) -> None:
        """Compose pinned owners for entry or recovery; this performs no HTTP call."""
        from drama_plugin.runtime.contracts import ArtifactReference
        from drama_plugin.execution.review import HumanReviewer
        from drama_plugin.execution.formal_media import FormalMediaStore
        from drama_plugin.execution.live_transport import configured_http_transport
        from drama_plugin.execution.transport import CapabilityAbsent
        if not self.ledger or not self.execution or not task.profile:
            raise ConfigurationError("Exact durable operation owners required")
        if not isinstance(self.providers.media,HttpMediaProvider):
            raise CapabilityAbsent("FORMAL_MEDIA_PROVIDER_CONFIGURATION_REQUIRED")
        if not isinstance(self.execution.media,FormalMediaStore):
            self.execution.media = FormalMediaStore(self.execution.media.directory,self.providers.media,self.execution.store)
        if self.execution.reviewer is None:
            self.execution.reviewer = HumanReviewer()
        recovery_ref = None
        if run_id is not None:
            with self.ledger.transaction() as db:
                rows = db.execute("SELECT operation_ref_json FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL LIMIT 2",(run_id,)).fetchall()
            if len(rows) > 1:
                raise ConfigurationError("Media run operation identity is not unique")
            if rows:
                candidate=ArtifactReference.model_validate_json(rows[0][0])
                from drama_plugin.execution.contracts import OperationState
                # Intent reservation alone does not mean the Provider saw a request.
                if self.execution.store.checkpoint(candidate).state!=OperationState.RESERVED:
                    recovery_ref=candidate
        from drama_plugin.execution.live_transport import TargetHttpTransport
        current = self.execution.transports.get(task.profile.provider)
        # A query-only transport pinned to the first paid operation must never
        # fence an independently authorized adjacent child, or query its sibling.
        rebind = isinstance(current,TargetHttpTransport) and not current.offline and (
            current.recovery_operation_ref != recovery_ref or current.adapter.model != task.profile.model
            or current.resolution != task.profile.resolution or current.aspect_ratio != task.profile.aspect_ratio)
        if current is None or rebind:
            try:
                self.execution.transports[task.profile.provider] = configured_http_transport(model=task.profile.model,
                    receipt_root=self.ledger.path.parent/(self.ledger.path.name+".receipts"),ledger=self.ledger,
                    resolution=task.profile.resolution,aspect_ratio=task.profile.aspect_ratio,
                    recovery_operation_ref=recovery_ref)
            except CapabilityAbsent:
                pass  # Exact owner reports absence; no alternative route.

    def _bind_media_execution(self, run_id: str, preparation_ref: ArtifactReference) -> None:
        from drama_plugin.execution.contracts import Authorization, ExecutionInput
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
        self.ledger.put_index("execution-input",run_id,ExecutionInput(preparation_ref=preparation_ref,authorization=auth,
            route=prepared.task.profile.provider),scope=run.scope,once=media_cursor(run.workflow_id,run.cursor) != 9)

    def _pending_media_child(self, run_id: str) -> str | None:
        """Find the exact child exposed by Film; never choose the next capability."""
        from drama_plugin.runtime.contracts import RuntimeState
        run = self.runtime.store.load(run_id)
        if run.workflow_id in MEDIA_WORKFLOWS:
            return None
        if run.state not in {RuntimeState.WAITING_USER,RuntimeState.WAITING_EXTERNAL} or run.last_result is None:
            raise ValueError("No pending Film child result")
        children = [ref.artifact_ref for ref in run.last_result.artifact_refs if ref.owner == "runtime"]
        if len(children) != 1 or children[0] == run_id:
            raise ValueError("Film child identity is not unique")
        child = self.runtime.store.load(children[0])
        if child.workflow_id not in MEDIA_WORKFLOWS or child.scope.work_id != run.scope.work_id:
            raise ValueError("Wrong native media child scope/workflow")
        return child.run_id

    async def recover_unknown_media_submission(self, run_id: str, *, terms: FinancialTerms, accepted: bool) -> RuntimeRun:
        """Retain renewed human cost terms and repair the exact existing UNKNOWN child."""
        from drama_plugin.execution.contracts import ExecutionOperation, ProviderAttempt, OperationState
        from drama_plugin.execution.live_transport import TargetHttpTransport
        from drama_plugin.generation.contracts import GenerationPreparation, FinalPromptArtifact
        from drama_plugin.persistence.review import UserDecisionRecord
        from drama_plugin.contracts.base import sha256_canonical
        from drama_plugin.runtime.contracts import DecisionCategory, RuntimeState
        if accepted is not True or not self.film or not self.execution or not self.ledger or not self.reviews:
            raise ValueError('Explicit accepted cost authorization required')
        parent = self.runtime.store.load(run_id)
        cp = self.film.store.checkpoint(run_id)
        terms.validate_current()
        operation = self.execution.store.get(terms.recovery_operation_ref, ExecutionOperation)
        allowed_children = (self.source_film_media_opening(run_id), *(cp.scene_media_run_ids or ()))
        if operation.run_id not in allowed_children:
            raise ValueError('Exact failed Film/UNKNOWN child required')
        child = self.runtime.store.load(operation.run_id)
        terminal = (parent.state == child.state == RuntimeState.FAILED and parent.last_result
            and child.last_result and parent.last_result.code == child.last_result.code == 'PROVIDER_UNKNOWN_WITHOUT_LOOKUP')
        waiting = (parent.state == child.state == RuntimeState.WAITING_EXTERNAL and parent.last_result
            and child.last_result and child.last_result.external_ref == operation.artifact_reference()
            and any(r.owner == 'runtime' and r.artifact_ref == child.run_id for r in parent.last_result.artifact_refs))
        if not (terminal or waiting):
            raise ValueError('Exact failed Film/UNKNOWN child required')
        checkpoint = self.execution.store.checkpoint(operation.artifact_reference())
        attempt = self.execution.store.get(checkpoint.attempt_ref, ProviderAttempt)
        prepared = self.generation_artifacts.get(terms.preparation_ref, GenerationPreparation)
        final = self.generation_artifacts.get(prepared.final_prompt_ref, FinalPromptArtifact)
        if (not terms.supplemental or operation.run_id != child.run_id
                or terms.prior_attempt_ref != checkpoint.attempt_ref or attempt.ordinal != 1
                or checkpoint.state != OperationState.UNKNOWN or checkpoint.receipt_ref is not None
                or terms.reserved_unknown_microunits < operation.authorization.budget_microunits
                or terms.preparation_ref != operation.preparation_ref or terms.profile != prepared.task.profile
                or terms.wire_payload_hash != sha256_canonical(TargetHttpTransport.preview(prepared, final, ledger=self.ledger))):
            raise ValueError('Exact operation/prior UNKNOWN/preparation/wire recovery terms required')
        self._compose_media_owners(prepared.task, run_id=child.run_id)
        receipt = UserDecisionRecord.seal(run_id=child.run_id, scope=child.scope,
            decision_id=f'{child.run_id}:recovery-{child.revision}', category=DecisionCategory.COST_APPROVAL,
            accepted=True, source_ref=terms.preparation_ref, terms_hash=terms.fingerprint,
            financial_terms=terms.model_dump(mode='json', by_alias=True))
        ref = self.reviews.put_user_decision(receipt)
        self.ledger.put_index('media-proof-cost-terms', child.run_id, terms, scope=child.scope)
        self.ledger.put_index('execution-recovery-authorization', child.run_id, ref, scope=child.scope)
        if waiting:
            return parent  # The native provider capability reconciles this same wait and consumes the new receipt.
        await self.runtime.repair_unknown_submission(child.run_id, expected_revision=child.revision,
            capability_key='execution.provider:v1', decision_ref=ref)
        return await self.runtime.repair_unknown_submission(run_id, expected_revision=parent.revision,
            capability_key='film.execute:v1', decision_ref=ref)

    async def provide_media_cost_terms(self, run_id: str, terms: FinancialTerms) -> RuntimeRun:
        child = self._pending_media_child(run_id)
        if child:
            await self.provide_media_cost_terms(child,terms)
            return await self.resume_source_film_run(run_id)
        from drama_plugin.generation.contracts import FinalPromptArtifact, GenerationPreparation
        from drama_plugin.execution.live_transport import TargetHttpTransport
        from drama_plugin.contracts.base import sha256_canonical
        from drama_plugin.runtime.contracts import CapabilityResult, ResultStatus, RuntimeState
        if not self.ledger:
            raise ConfigurationError("Durable terms required")
        run = await self.runtime.recover_run(run_id)
        cost_reauthorization = (run.state == RuntimeState.WAITING_USER and run.last_result is not None
            and run.last_result.user_decision is not None and run.last_result.user_decision.category.value == "COST_APPROVAL"
            and media_cursor(run.workflow_id,run.cursor) == 9)
        pending_approval = run.state == RuntimeState.WAITING_USER and media_cursor(run.workflow_id,run.cursor) == 8
        if run.workflow_id not in MEDIA_WORKFLOWS or (not cost_reauthorization and not pending_approval and
                (media_cursor(run.workflow_id, run.cursor) != 7 or run.state != RuntimeState.WAITING_EXTERNAL)):
            raise ValueError("No pending cost terms boundary")
        prepared = self.generation_artifacts.get(self.generation_artifacts.prepared(run_id),GenerationPreparation)
        final = self.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
        terms.validate_current()
        if (terms.preparation_ref != prepared.artifact_reference() or terms.profile != prepared.task.profile
                or terms.wire_payload_hash != sha256_canonical(TargetHttpTransport.preview(prepared,final,ledger=self.ledger))):
            raise ValueError("Exact preparation/wire financial terms required")
        self.ledger.put_index("media-proof-cost-terms",run_id,terms,scope=run.scope,
            once=not (cost_reauthorization or pending_approval))
        if cost_reauthorization or pending_approval:
            return run  # New exact terms await a fresh accepted cost receipt.
        assert run.last_result and run.last_result.external_ref
        await self.runtime.record_external_result(run_id,external_ref=run.last_result.external_ref,
            result=CapabilityResult(status=ResultStatus.SUCCEEDED,artifact_refs=(terms.preparation_ref,)))
        return await self.runtime.run(run_id)

    async def provide_human_media_review(self, run_id: str, *, media_ref: ArtifactReference,
                                        context_hash: str, response: ReviewResponse) -> RuntimeRun:
        child = self._pending_media_child(run_id)
        if child:
            await self.provide_human_media_review(child,media_ref=media_ref,context_hash=context_hash,response=response)
            await self.runtime.reconcile_wait(run_id)
            return await self.runtime.run(run_id)
        from drama_plugin.runtime.contracts import CapabilityResult, ResultStatus, RuntimeState
        if not self.execution:
            raise ConfigurationError("Execution owner required")
        run = await self.runtime.recover_run(run_id)
        if run.workflow_id not in MEDIA_WORKFLOWS or run.state not in {RuntimeState.WAITING_EXTERNAL,RuntimeState.WAITING_USER} or media_cursor(run.workflow_id, run.cursor) != 11:
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
        from drama_plugin.runtime.contracts import CapabilityInput, ResultStatus, RuntimeState, DecisionCategory
        run = await self.runtime.recover_run(run_id)
        from drama_plugin.generation.policy import MEDIA_WORKFLOW, media_review_workflow
        if run.workflow_id not in {WORKFLOW,*MEDIA_WORKFLOWS}:
            raise ValueError("Only E1 execution runs can use execution reconciliation")
        flow = media_review_workflow(run.workflow_id) if run.workflow_id in MEDIA_WORKFLOWS else execution_workflow()
        if run.workflow_id in MEDIA_WORKFLOWS:
            task = self.generation_artifacts.inputs(run_id).task
            if task.profile is not None:
                # Execution validates pinned authorities and permits query of an
                # already paid task even if today's route policy has changed.
                self._compose_media_owners(task,run_id=run_id)
        if run.state == RuntimeState.WAITING_EXTERNAL:
            # The typed result owns the wait. A canonical read can occur at the
            # review cursor; genuine human decisions remain WAITING_USER.
            await self.runtime.reconcile_wait(run_id)
        elif run.state == RuntimeState.BLOCKED and run.wait_reason == "INTERRUPTED_CAPABILITY":
            await self.runtime.retry(run_id)
        return await self.runtime.run(run_id)

    async def decide_target_run(self, run_id: str, *, decision_id: str, accepted: bool,
                                source_ref: ArtifactReference | None = None) -> RuntimeRun:
        """Retain a real user decision receipt before advancing its existing Run."""
        if self.reviews is None:
            raise ConfigurationError("Durable Review Store required for formal Target decisions")
        from drama_plugin.persistence.review import UserDecisionRecord
        from drama_plugin.runtime.contracts import ActionKind, RuntimeState, RecoveryClass, ArtifactReference
        run = await self.runtime.recover_run(run_id)
        action = self.runtime.next_action(run_id)
        if run.state != RuntimeState.WAITING_USER or action.kind != ActionKind.REQUEST_USER_DECISION:
            raise ValueError("Run does not await a user decision")
        if decision_id != self.runtime.decision_id(run_id):
            raise ValueError("Decision identity mismatch")
        if run.workflow_id in MEDIA_WORKFLOWS and media_cursor(run.workflow_id, run.cursor) == 11:
            raise ValueError("Human media review requires exact typed PASS/REVISE receipt")
        from drama_plugin.creative_engine.policy import WORKFLOW as CREATIVE_WORKFLOW
        if self.film and run.workflow_id in {"source-to-final-film:v1", "source-to-reviewed-media:v1", "final-film-revision:v1"}:
            cp = self.film.store.checkpoint(run_id)
            dynamic = run.last_result is not None and run.last_result.recovery_class == RecoveryClass.USER_DECISION
            child = next((r for r in run.last_result.artifact_refs if r.owner == "runtime"),None) if dynamic and run.last_result else None
            if child:
                resolved = await self.decide_target_run(child.artifact_ref,decision_id=self.runtime.decision_id(child.artifact_ref),
                    accepted=accepted,source_ref=source_ref)
                assert resolved.last_result is not None
                receipt = next(r for r in resolved.last_result.artifact_refs if r.owner == "user-decision")
                return await self.runtime.decide(run_id,decision_id=decision_id,accepted=accepted,decision_ref=receipt)
            expected = (run.last_result.external_ref if dynamic and run.last_result else
                cp.plan_ref if run.workflow_id in {"source-to-final-film:v1","source-to-reviewed-media:v1"} and run.cursor == 3 else cp.final_ref)
            if source_ref != expected:
                raise ValueError("Film decision must bind exact immutable candidate/hash")
        if run.workflow_id == CREATIVE_WORKFLOW:
            candidate = self.creative.state.checkpoint(run_id).candidate_ref
            if source_ref != candidate:
                raise ValueError("Adoption must bind the exact candidate version-set hash")
        assert action.decision is not None
        film_dynamic = (self.film is not None and run.workflow_id == "source-to-reviewed-media:v1"
            and run.last_result is not None and run.last_result.recovery_class == RecoveryClass.USER_DECISION)
        record = UserDecisionRecord.seal(run_id=run_id, scope=run.scope,
            decision_id=decision_id, category=action.decision.category,
            accepted=accepted, source_ref=source_ref,
            terms_hash=self._media_decision_terms(run_id,source_ref) if run.workflow_id in MEDIA_WORKFLOWS else
                self.film.pending_decision_terms(run_id) if film_dynamic and self.film else None,
            financial_terms=self._reviewed_financial_terms(run_id) if run.workflow_id in MEDIA_WORKFLOWS
                and action.decision.category.value == "COST_APPROVAL" else None)
        ref = self.reviews.put_user_decision(record)
        resume_same_step = False
        if film_dynamic and self.film:
            self.film.consume_decision(run_id,ref,accepted)
        if accepted and run.workflow_id in MEDIA_WORKFLOWS:
            self._consume_media_decision(run_id,ref,record.category)
        if accepted and run.workflow_id in {"govern-shot:v1","prepare-generation:v1"}:
            from drama_plugin.governance.contracts import GateEffect
            remaining = self.gate_governance.consume_user_decision(run_id,ref)
            resume_same_step = remaining.effect in {GateEffect.WAIT_USER,GateEffect.REVIEW_REQUIRED}
        return await self.runtime.decide(run_id, decision_id=decision_id,
            accepted=accepted, decision_ref=ref,resume_same_step=resume_same_step)

    def _reviewed_financial_terms(self, run_id: str) -> dict[str, JsonValue]:
        from drama_plugin.execution.live_transport import FinancialTerms
        from pydantic import JsonValue, TypeAdapter
        assert self.ledger
        terms = FinancialTerms.model_validate(self.ledger.get_index("media-proof-cost-terms",run_id))
        return TypeAdapter(dict[str,JsonValue]).validate_python(terms.model_dump(mode="json",by_alias=True))

    def _media_decision_terms(self, run_id: str, source_ref: ArtifactReference | None) -> str:
        from drama_plugin.execution.live_transport import FinancialTerms
        assert self.ledger
        run = self.runtime.store.load(run_id)
        if media_cursor(run.workflow_id, run.cursor) == 4:
            task = self.generation_artifacts.inputs(run_id).task
            package = self.gate_findings.inputs(run_id).package_ref
            if not task.unit or package is None or package != source_ref:
                raise ValueError("Scope decision must bind exact Package/unit/duties")
            return task.unit.terms_hash(package)
        terms = FinancialTerms.model_validate(self.ledger.get_index("media-proof-cost-terms",run_id))
        terms.validate_current()
        if media_cursor(run.workflow_id, run.cursor) not in {8,9} or source_ref != terms.preparation_ref:
            raise ValueError("Cost decision must bind exact preparation/terms")
        from drama_plugin.generation.contracts import GenerationPreparation, FinalPromptArtifact
        from drama_plugin.execution.live_transport import TargetHttpTransport
        from drama_plugin.contracts.base import sha256_canonical
        prepared = self.generation_artifacts.get(terms.preparation_ref,GenerationPreparation)
        final = self.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
        if terms.profile != prepared.task.profile or terms.wire_payload_hash != sha256_canonical(TargetHttpTransport.preview(prepared,final,ledger=self.ledger)):
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
        if terms.supplemental:
            self.ledger.put_index('execution-recovery-authorization', run_id, ref, scope=run.scope)
            return  # Preserve the original operation and its original Authorization.
        authorization = Authorization(approval_ref=ref,authorized=True,budget_microunits=terms.budget_microunits,
            estimated_cost_microunits=ceil(terms.cost_quote.amount*1000000),execution_mode="CONTROLLED_LIVE")
        self.ledger.put_index("media-proof-authorization",run_id,authorization,scope=run.scope,once=media_cursor(run.workflow_id,run.cursor) != 9)
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
