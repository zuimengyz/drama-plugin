"""The single Target entry: ProductionPackageRef + task, never scattered Bibles."""
from __future__ import annotations

from dataclasses import dataclass

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.generation.audio import AudioPerformanceAssembler, package_scope
from drama_plugin.generation.contracts import (
    AudioExecutionPlan, CoverageEntry, CoverageStatus as S, ExecutionDiagnostic, FinalPromptArtifact,
    GenerationPreparation, GenerationTask, Obligation as O, PromptCoverage, PromptIR,
)
from drama_plugin.generation.projection import ExecutionProjection
from drama_plugin.generation.seedance import ModelPolicyCatalog, SeedanceTargetAdapter
from drama_plugin.generation.sources import PackageReader
from drama_plugin.generation.sources import child
from drama_plugin.generation.references import ExecutionReferenceResolver
from drama_plugin.generation.store import GenerationArtifactStore
from drama_plugin.production.contracts import SourceDomain as D
from drama_plugin.production.sources import SourceReadError
from drama_plugin.production.store import ProductionPackageStore
from drama_plugin.runtime.contracts import ArtifactReference


@dataclass(frozen=True)
class CompilationResult:
    preparation_ref: ArtifactReference | None
    diagnostics_ref: ArtifactReference
    prompt_ir_ref: ArtifactReference | None = None
    audio_plan_ref: ArtifactReference | None = None


class PromptCompiler:
    role = "COMPILER"
    creative_authority = False

    def __init__(self, packages: ProductionPackageStore, artifacts: GenerationArtifactStore, reader: PackageReader,
                 catalog: ModelPolicyCatalog | None = None, *, media_reader=None):
        self.packages, self.artifacts, self.reader = packages, artifacts, reader
        self.catalog = catalog if catalog is not None else ModelPolicyCatalog()
        self.audio = AudioPerformanceAssembler()
        self.projection = ExecutionProjection(reader)
        self.generator = SeedanceTargetAdapter()
        self.references = ExecutionReferenceResolver(media_reader)

    async def compile(self, package_ref: ArtifactReference, task: GenerationTask = GenerationTask()) -> CompilationResult:
        package = self.packages.get(package_ref)
        diagnostics: list[ExecutionDiagnostic] = []

        def result(prepared=None, ir=None, audio=None):
            return CompilationResult(prepared, self.artifacts.retain_diagnostics(tuple(diagnostics),
                scope=package_scope(package)), ir, audio)

        policy = self.catalog.policy(task.target_model)
        if policy is None:
            diagnostics.append(ExecutionDiagnostic(code="GENERATOR_ABSENT", owner="model-generator", domain=D.DIRECTION, required=True))
            return result()
        if task.native_audio == "REQUIRED" and not policy.native_audio:
            diagnostics.append(ExecutionDiagnostic(code="REQUEST_UNSUPPORTED", owner="model-capability", domain=D.SOUND, required=True))
            return result()
        from drama_plugin.providers.video.registry import registry
        model = registry()["models"].get(task.target_model, {})
        if model and task.input_mode not in model["input_modes"]:
            diagnostics.append(ExecutionDiagnostic(code="REQUEST_UNSUPPORTED", owner="model-capability", domain=D.REFERENCE, required=True))
            return result()
        duration = task.profile.requested_duration_ms if task.profile else package.generation_intent.duration_ms
        if model and duration / 1000 not in model["durations"]:
            diagnostics.append(ExecutionDiagnostic(code="REQUEST_UNSUPPORTED", owner="model-capability", domain=D.DIRECTION, required=True))
            return result()
        try:
            if task.unit:
                if self.reader.operations is None:
                    raise ValueError("OPERATION_RESOLVER_ABSENT")
                selected = await self.reader.operations.selected(package, task, self.reader)
            else:
                selected = await self.reader.selections(package)
            audio_result = self.audio.assemble(package, task, selected)
            diagnostics.extend(audio_result.diagnostics)
            if audio_result.plan is None:
                return result()
            plan = audio_result.plan
            audio_ref = self.artifacts.put(plan)
            projection_task = task
            if task.native_audio == "OPTIONAL" and not policy.native_audio:
                projection_task = task.model_copy(update={"native_audio": "DISABLED"})
                diagnostics.append(ExecutionDiagnostic(code="OPTIONAL_COVERAGE", owner="native-audio", domain=D.SOUND))
            projection = await self.projection.project(package, projection_task, plan, selected)
            diagnostics.extend(projection.diagnostics)
            if plan.speech_events:
                diagnostics.append(ExecutionDiagnostic(code="TTS_CAPABILITY_ABSENT", owner="tts-execution", domain=D.SOUND,
                    required=task.tts_required))
            if projection.ir is None:
                return result(audio=audio_ref)
            ir = projection.ir
            references = await self.references.resolve(package, task, selected,
                subjects={f.subject_id for f in ir.facts if f.subject_id})
            diagnostics.extend(references.diagnostics)
            if any(d.required for d in references.diagnostics):
                return result(audio=audio_ref)
            if model:
                limits = dict(zip(("image", "video", "audio"), model.get("reference_limits", ())))
                if any(sum(i.binding.media.kind == kind for i in references.inputs) > maximum
                       for kind, maximum in limits.items()):
                    diagnostics.append(ExecutionDiagnostic(code="HARD_LIMIT_OVERFLOW", owner="model-capability",
                        domain=D.REFERENCE, required=True))
                    return result(audio=audio_ref)
            ir = PromptIR.seal(**{**ir.model_dump(exclude={"fingerprint", "execution_reference_refs"}),
                "execution_reference_refs": tuple(i.source_ref for i in references.inputs)})
            ir_ref = self.artifacts.put(ir)
        except SourceReadError as error:
            diagnostics.append(ExecutionDiagnostic(code="PACKAGE_STALE" if error.code.value == "VERSION_MISMATCH"
                else "SCOPE_MISMATCH" if error.code.value in {"SCOPE_MISMATCH", "AUTHORITY_MISMATCH"}
                else "EXECUTION_REQUIRED_MISSING", owner=error.owner.value, domain=D.CANON, required=True))
            return result()
        except ValueError as error:
            diagnostics.append(ExecutionDiagnostic(code="SCOPE_DECISION_REQUIRED" if str(error) == "UNIT_SCOPE_DECISION_REQUIRED"
                else "SCOPE_MISMATCH" if any(s in str(error) for s in ("SCOPE", "VERSION", "ADOPT", "RIGHTS", "DECISION", "PROFILE"))
                else "EXECUTION_REQUIRED_MISSING", owner="production-selection", domain=D.DIRECTION, required=True))
            return result()
        key = sha256_canonical([package_ref.model_dump(mode="json"), task.model_dump(mode="json"), policy.fingerprint])
        final_ref = self.artifacts.final_for(key)
        if final_ref is None:
            try:
                generated = self.generator.generate(ir, plan, policy=policy, input_mode=task.input_mode,
                    references=references.inputs)
            except ValueError as error:
                code = str(error)
                diagnostics.append(ExecutionDiagnostic(code="HARD_LIMIT_OVERFLOW" if "CRITICAL_BUDGET_OVERFLOW" in code
                    else "EXECUTION_REQUIRED_MISSING", owner="prompt-compiler", domain=D.DIRECTION, required=True))
                return result(ir=ir_ref, audio=audio_ref)
            facts = {f.fact_id: f for f in ir.facts}
            entries = list(projection.internal)
            # Duty coverage requires an actually resolved, reviewed media input and
            # the generator's corresponding immutable media/hash slot receipt.
            for execution in references.inputs:
                binding = execution.binding
                slot = next((s for s in generated["input_slots"] if s["media_id"] == binding.media.media_id
                    and s["content_hash"] == binding.media.content_hash and s["version"] == binding.media.version), None)
                if slot is None:
                    diagnostics.append(ExecutionDiagnostic(code="REFERENCE_INPUT_UNRESOLVED", owner="reference-strategy",
                        domain=D.REFERENCE, required=True))
                    return result(ir=ir_ref, audio=audio_ref)
                for index, duty in enumerate(binding.duties):
                    source = child(execution.source_ref, "duties", str(index))
                    entries.append(CoverageEntry(fact_id="reference-duty:" + sha256_canonical(source), domain=D.REFERENCE,
                        source_ref=source, obligation=O.EXECUTION_REQUIRED if duty.necessity == "REQUIRED" else O.QUALITY_SUPPORTING,
                        status=S.REFERENCE_COVERED, input_ref=ArtifactReference(owner="media", artifact_ref=binding.media.media_id)))
            mapping = generated["target_mapping"]
            covered = {row["obligation_id"]: row for row in generated["coverage"]}
            for atom in generated["atoms"]:
                path = atom["path"]
                fact = facts[mapping[path]]
                receipt = covered.get(path)
                if receipt is not None:
                    status, span = S(receipt["status"]), tuple(receipt["span"])
                elif path in {row["path"] for row in generated["omitted"]}:
                    status, span = S.OPTIONAL_OMITTED, None
                else:
                    # Semantic exact duplicates have one receipt; other authored references
                    # retain the same obligation through the generator's dedup receipt.
                    match = next((row for row in generated["atoms"] if row["text"] == atom["text"] and
                                  row["obligation_id"] in covered), None)
                    status, span = (S.TEXT_COVERED, tuple(covered[match["obligation_id"]]["span"])) if match else (S.UNRESOLVED, None)
                entries.append(CoverageEntry(fact_id=fact.fact_id, domain=fact.domain, source_ref=fact.source_ref,
                    obligation=fact.obligation, status=status, span=span))
            by_fact = {entry.fact_id: entry for entry in entries}
            for canonical_id, alias in projection.aliases:
                receipt = by_fact[canonical_id]
                entries.append(CoverageEntry(fact_id=alias.fact_id, domain=alias.domain, source_ref=alias.source_ref,
                    obligation=alias.obligation, status=receipt.status, span=receipt.span))
            if any(e.obligation == O.EXECUTION_REQUIRED and e.status == S.UNRESOLVED for e in entries):
                diagnostics.append(ExecutionDiagnostic(code="EXECUTION_REQUIRED_MISSING", owner="prompt-compiler", domain=D.DIRECTION, required=True))
                return result(ir=ir_ref, audio=audio_ref)
            coverage = PromptCoverage.seal(source_package_ref=package_ref, entries=tuple(entries))
            coverage_ref = self.artifacts.put(coverage)
            final = FinalPromptArtifact.seal(task=task, model_family=policy.family,
                generator_policy_fingerprint=policy.fingerprint, prompt_text=generated["prompt"], source_package_ref=package_ref,
                prompt_ir_fingerprint=ir.fingerprint, coverage_ref=coverage_ref,
                execution_reference_refs=ir.execution_reference_refs)
            final_ref = self.artifacts.put(final)
            self.artifacts.register_final(key, final_ref)
        final = self.artifacts.get(final_ref, FinalPromptArtifact)
        coverage = self.artifacts.get(final.coverage_ref, PromptCoverage)
        if any(e.status == S.OPTIONAL_OMITTED for e in coverage.entries):
            diagnostics.append(ExecutionDiagnostic(code="OPTIONAL_COVERAGE", owner="prompt-compiler", domain=D.DIRECTION))
        prepared = GenerationPreparation.seal(source_package_ref=package_ref, task=task,
            final_prompt_ref=final_ref, audio_plan_ref=audio_ref)
        return result(self.artifacts.put(prepared), ir_ref, audio_ref)

    def stale(self, ref: ArtifactReference, package_ref: ArtifactReference, task: GenerationTask) -> bool:
        prepared = self.artifacts.get(ref, GenerationPreparation)
        final = self.artifacts.get(prepared.final_prompt_ref, FinalPromptArtifact)
        policy = self.catalog.policy(task.target_model)
        return (prepared.source_package_ref != package_ref or prepared.task != task or policy is None or
                final.generator_policy_fingerprint != policy.fingerprint)

    async def validate_execution_sources(self, ref: ArtifactReference) -> tuple[ExecutionDiagnostic, ...]:
        prepared = self.artifacts.get(ref, GenerationPreparation)
        final = self.artifacts.get(prepared.final_prompt_ref, FinalPromptArtifact)
        ir = self.artifacts.get(ArtifactReference(owner="prompt-ir", artifact_ref="prompt-ir:" + final.prompt_ir_fingerprint, version=1), PromptIR)
        if prepared.task.unit:
            try:
                if self.reader.operations is None:
                    raise ValueError("OPERATION_RESOLVER_ABSENT")
                await self.reader.operations.selected(self.packages.get(prepared.source_package_ref), prepared.task, self.reader)
            except (KeyError, ValueError, OSError):
                return (ExecutionDiagnostic(code="SCOPE_MISMATCH", owner="production-selection", domain=D.DIRECTION, required=True),)
        try:
            await self.reader.validate_execution_refs(tuple(f.source_ref for f in ir.facts) + ir.execution_reference_refs,
                work_id=ir.scope.work_id)
        except SourceReadError as error:
            return (ExecutionDiagnostic(code="PACKAGE_STALE" if error.code.value == "VERSION_MISMATCH" else "EXECUTION_REQUIRED_MISSING",
                owner=error.owner.value, domain=D.PERFORMANCE, required=True),)
        package = self.packages.get(prepared.source_package_ref)
        checked = await self.references.resolve(package, prepared.task, await self.reader.selections(package),
            subjects={f.subject_id for f in ir.facts if f.subject_id})
        return checked.diagnostics
