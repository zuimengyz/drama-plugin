"""Native offline preparation. T5 stops at exact artifacts, never transport."""
from drama_plugin.generation.audio import package_scope
from drama_plugin.generation.checks import execution_findings
from drama_plugin.generation.compiler import PromptCompiler
from drama_plugin.generation.contracts import ExecutionDiagnostic, GenerationPreparation
from drama_plugin.generation.policy import COMPILE, REBUILD, READY, RELEASE
from drama_plugin.generation.store import GenerationArtifactStore
from drama_plugin.governance.capability import GateGovernanceCapability
from drama_plugin.governance.checks import assembly_findings
from drama_plugin.governance.contracts import GateCode, GateEffect, GateFinding
from drama_plugin.production.contracts import SourceDomain
from drama_plugin.runtime.capabilities import TargetCapability
from drama_plugin.runtime.contracts import CapabilityInput, CapabilityResult, ResultStatus


class GenerationCapability:
    def __init__(self, compiler: PromptCompiler, artifacts: GenerationArtifactStore, governance: GateGovernanceCapability):
        self.compiler, self.artifacts, self.governance = compiler, artifacts, governance

    def _decision_result(self, run, diagnostics, package_ref):
        evidence = self.artifacts.retain_diagnostics(tuple(diagnostics), scope=run.scope)
        findings = execution_findings(tuple(diagnostics), scope=run.scope, evidence_ref=evidence)
        decision = self.governance.governor.govern(findings, scope=run.scope, mode=run.mode, package_ref=package_ref)
        return CapabilityResult(status=ResultStatus.SUCCEEDED,
            artifact_refs=(self.governance.findings.put_decision(decision, run_id=run.run_id),))

    async def compile(self, inputs: CapabilityInput) -> CapabilityResult:
        run = self.governance.runs.load(inputs.run_id)
        package_ref = self.governance.findings.inputs(run.run_id).package_ref
        if inputs.scope != run.scope or package_ref is None:
            raise ValueError("Generation requires a governed package")
        package = self.compiler.packages.get(package_ref)
        if package_scope(package) != run.scope or package.boundary.mode != run.mode:
            return self._decision_result(run, (ExecutionDiagnostic(code="SCOPE_MISMATCH", owner="production-package",
                domain=SourceDomain.CANON, required=True),), package_ref)
        task = self.artifacts.inputs(run.run_id)
        if task.cached_preparation_ref is not None and self.compiler.stale(task.cached_preparation_ref, package_ref, task.task):
            return self._decision_result(run, (ExecutionDiagnostic(code="PROMPT_STALE", owner="prompt-compiler",
                domain=SourceDomain.DIRECTION),), package_ref)
        return await self._compile(run, package_ref)

    async def _compile(self, run, package_ref):
        result = await self.compiler.compile(package_ref, self.artifacts.inputs(run.run_id).task)
        if result.preparation_ref is not None:
            self.artifacts.set_prepared(run.run_id, result.preparation_ref)
        return self._decision_result(run, self.artifacts.diagnostics(result.diagnostics_ref), package_ref)

    async def rebuild(self, inputs: CapabilityInput) -> CapabilityResult:
        decision = self.governance._decision(inputs)
        if decision.effect != GateEffect.AUTO_MAINTAIN:
            raise ValueError("Expected an internal maintenance decision")
        if not self.artifacts.claim_rebuild(inputs.run_id):
            return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="EXECUTION_REBUILD_EXHAUSTED", artifact_refs=inputs.input_refs)
        tasks = [self.governance.findings.finding(ref) for ref in decision.finding_refs]
        if any(f.code == GateCode.PACKAGE_STALE for f in tasks):
            result = await self.governance.maintain(inputs)
            current = self.governance.findings.decision(self.governance.findings.latest(inputs.run_id))
            if current.effect != GateEffect.CONTINUE:
                return result
        elif any(f.category == "AUTO_MAINTENANCE" and f.code != GateCode.DERIVED_REFRESH for f in tasks):
            raise ValueError("Unregistered execution maintenance")
        run = self.governance.runs.load(inputs.run_id)
        return await self._compile(run, self.governance.findings.inputs(run.run_id).package_ref)

    async def release(self, inputs: CapabilityInput) -> CapabilityResult:
        decision = self.governance._decision(inputs)
        if decision.effect != GateEffect.CONTINUE:
            raise ValueError("Only governed continuation can release execution artifacts")
        prepared = self.artifacts.prepared(inputs.run_id)
        return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(prepared,))

    async def ready(self, inputs: CapabilityInput) -> CapabilityResult:
        decision = self.governance._decision(inputs)
        if decision.effect != GateEffect.CONTINUE or decision.package_ref is None:
            raise ValueError("READY requires governed artifacts")
        run = self.governance.runs.load(inputs.run_id)
        ref = self.artifacts.prepared(inputs.run_id)
        prepared = self.artifacts.get(ref, GenerationPreparation)
        validation = await self.governance.assembler.validate_sources(self.compiler.packages.get(decision.package_ref))
        findings = assembly_findings(validation, scope=run.scope,
            evidence_ref=self.compiler.packages.retain_validation(validation, scope=run.scope))
        if not findings:
            diagnostics = await self.compiler.validate_execution_sources(ref)
            evidence = self.artifacts.retain_diagnostics(diagnostics, scope=run.scope)
            findings = execution_findings(diagnostics, scope=run.scope, evidence_ref=evidence)
        if findings:
            # Do not skip a pending maintenance or hard stop at the last boundary.
            new = self.governance.governor.govern(findings, scope=run.scope, mode=run.mode, package_ref=decision.package_ref)
            latest = self.governance.findings.put_decision(new, run_id=run.run_id)
            maintenance = inputs.model_copy(update={"input_refs": (latest,)})
            if new.effect == GateEffect.AUTO_MAINTAIN:
                rebuilt = await self.rebuild(maintenance)
                if rebuilt.status != ResultStatus.SUCCEEDED:
                    return rebuilt
                following = self.governance.findings.decision(self.governance.findings.latest(run.run_id))
                if following.effect == GateEffect.CONTINUE:
                    prepared_ref = self.artifacts.prepared(run.run_id)
                    prepared = self.artifacts.get(prepared_ref, GenerationPreparation)
                    return CapabilityResult(status=ResultStatus.SUCCEEDED,
                        artifact_refs=(prepared.final_prompt_ref, prepared.audio_plan_ref, prepared_ref))
            elif new.effect == GateEffect.BLOCK:
                return await self.governance.block(maintenance)
            if new.effect != GateEffect.CONTINUE:
                return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="EXECUTION_INPUT_CHANGED", artifact_refs=(latest,))
            # Optional diagnostics can recur at the release check. T3 retains
            # them as warnings; they must not turn into a technical retry/STOP.
        if self.compiler.stale(ref, decision.package_ref, self.artifacts.inputs(run.run_id).task):
            assessed = self._decision_result(run, (ExecutionDiagnostic(code="PROMPT_STALE", owner="prompt-compiler",
                domain=SourceDomain.DIRECTION),), decision.package_ref)
            rebuilt = await self.rebuild(inputs.model_copy(update={"input_refs": assessed.artifact_refs}))
            following = self.governance.findings.decision(self.governance.findings.latest(run.run_id))
            if rebuilt.status != ResultStatus.SUCCEEDED or following.effect != GateEffect.CONTINUE:
                return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="EXECUTION_INPUT_CHANGED", artifact_refs=rebuilt.artifact_refs)
            ref = self.artifacts.prepared(run.run_id)
            prepared = self.artifacts.get(ref, GenerationPreparation)
        return CapabilityResult(status=ResultStatus.SUCCEEDED,
            artifact_refs=(prepared.final_prompt_ref, prepared.audio_plan_ref, ref))

    def registrations(self):
        return {COMPILE: TargetCapability(self.compile, replay_safe=True), REBUILD: TargetCapability(self.rebuild, replay_safe=True),
                RELEASE: TargetCapability(self.release, replay_safe=True), READY: TargetCapability(self.ready, replay_safe=True)}
