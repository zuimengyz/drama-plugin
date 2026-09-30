"""Native shadow checks and bounded local rebuild, never Canon or paid side effects."""
from __future__ import annotations

from drama_plugin.governance.checks import assembly_findings
from drama_plugin.governance.contracts import GateCategory, GateCode, GateDecision, GateFinding
from drama_plugin.governance.governor import GateGovernor
from drama_plugin.governance.policy import ASSESS, BLOCK, MAINTAIN, REJECT, RELEASE
from drama_plugin.governance.store import GateFindingStore
from drama_plugin.production.assembler import ShotAssembler
from drama_plugin.production.store import ProductionPackageStore
from drama_plugin.runtime.capabilities import TargetCapability
from drama_plugin.runtime.contracts import ArtifactReference, CapabilityInput, CapabilityResult, ResultStatus
from drama_plugin.runtime.store import InMemoryRunStore


class GateGovernanceCapability:
    def __init__(self, governor: GateGovernor, findings: GateFindingStore, packages: ProductionPackageStore,
                 assembler: ShotAssembler, runs: InMemoryRunStore):
        self.governor, self.findings, self.packages = governor, findings, packages
        self.assembler, self.runs = assembler, runs

    async def assess(self, inputs: CapabilityInput) -> CapabilityResult:
        run = self.runs.load(inputs.run_id)
        if inputs.scope != run.scope:
            raise ValueError("Governance capability scope mismatch")
        request = self.findings.inputs(run.run_id)
        found = [self.findings.finding(ref) for ref in request.finding_refs]
        package_ref = request.package_ref
        if package_ref is None:
            assembled = await self.assembler.assemble(run.scope, mode=run.mode,
                policy_ref=ArtifactReference(owner="runtime-policy", artifact_ref=run.policy_id, version=1))
            if assembled.package is not None:
                package_ref = self.packages.put(assembled.package)
                self.findings.set_package(run.run_id, package_ref)
            else:
                validation_ref = self.packages.retain_validation(assembled.validation, scope=run.scope)
                found.extend(assembly_findings(assembled.validation, scope=run.scope, evidence_ref=validation_ref))
        if package_ref is not None:
            try:
                package = self.packages.get(package_ref)
                same_scope = (package.scope.work.artifact_ref, package.scope.scene.artifact_ref,
                    package.scope.shot.artifact_ref) == (run.scope.work_id, run.scope.scene_id, run.scope.shot_id)
                if not same_scope or package.boundary.mode != run.mode:
                    found.append(GateFinding.classified(GateCode.PACKAGE_SCOPE_MISMATCH,
                        owner="production-package", scope=run.scope, evidence_ref=package_ref))
                else:
                    validation = await self.assembler.validate_sources(package)
                    found.extend(assembly_findings(validation, scope=run.scope,
                        evidence_ref=self.packages.retain_validation(validation, scope=run.scope)))
            except (KeyError, ValueError):
                found.append(GateFinding.classified(GateCode.REQUEST_INPUT_MISSING,
                    owner="production-package-store", scope=run.scope, evidence_ref=package_ref, required=True))
        elif not any(f.category in {GateCategory.HARD_STOP, GateCategory.AUTO_MAINTENANCE} for f in found):
            found.append(GateFinding.classified(GateCode.REQUEST_INPUT_MISSING,
                owner="production-package", scope=run.scope,
                evidence_ref=ArtifactReference(owner="runtime-run", artifact_ref=run.run_id), required=True))
        decision = self.governor.govern(tuple(found), scope=run.scope, mode=run.mode, package_ref=package_ref)
        return CapabilityResult(status=ResultStatus.SUCCEEDED,
            artifact_refs=(self.findings.put_decision(decision, run_id=run.run_id),))

    def _decision(self, inputs: CapabilityInput) -> GateDecision:
        if len(inputs.input_refs) != 1:
            raise ValueError("One governance decision reference is required")
        decision = self.findings.decision(inputs.input_refs[0])
        run = self.runs.load(inputs.run_id)
        if decision.scope != inputs.scope or run.scope != inputs.scope or decision.mode != run.mode:
            raise ValueError("Governance decision scope/mode mismatch")
        if self.findings.latest(run.run_id) != inputs.input_refs[0]:
            raise ValueError("Governance decision is no longer current")
        return decision

    async def release(self, inputs: CapabilityInput) -> CapabilityResult:
        decision = self._decision(inputs)
        if decision.effect != "CONTINUE" or decision.package_ref is None:
            raise ValueError("Only continued decisions release packages")
        return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(decision.package_ref,))

    async def block(self, inputs: CapabilityInput) -> CapabilityResult:
        decision = self._decision(inputs)
        if decision.effect != "BLOCK":
            raise ValueError("Only four-family hard stops use this capability")
        return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="GOVERNED_HARD_STOP",
                                artifact_refs=inputs.input_refs)

    async def reject(self, inputs: CapabilityInput) -> CapabilityResult:
        decision = self._decision(inputs)
        if decision.effect != "LEGACY_REJECT":
            raise ValueError("Expected legacy boundary rejection")
        return CapabilityResult(status=ResultStatus.FAILED, code="LEGACY_PATH_REJECTED", artifact_refs=inputs.input_refs)

    async def maintain(self, inputs: CapabilityInput) -> CapabilityResult:
        decision = self._decision(inputs)
        if decision.effect != "AUTO_MAINTAIN":
            raise ValueError("Expected internal maintenance")
        if not self.findings.claim_maintenance(inputs.run_id):
            return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE,
                code="TECHNICAL_MAINTENANCE_EXHAUSTED", artifact_refs=inputs.input_refs)
        tasks = [self.findings.finding(ref) for ref in decision.finding_refs
                 if self.findings.finding(ref).category == GateCategory.AUTO_MAINTENANCE]
        if any(task.code != GateCode.PACKAGE_STALE for task in tasks):
            absent = GateFinding.classified(GateCode.CAPABILITY_NOT_IMPLEMENTED,
                owner="runtime-maintenance", scope=inputs.scope, evidence_ref=inputs.input_refs[0], required=True)
            new = self.governor.govern((absent,), scope=inputs.scope, mode=decision.mode, package_ref=decision.package_ref)
            return CapabilityResult(status=ResultStatus.SUCCEEDED,
                artifact_refs=(self.findings.put_decision(new, run_id=inputs.run_id),))
        # A new immutable assembly is the only repair. No SourcePin or Canon writes.
        run = self.runs.load(inputs.run_id)
        assembled = await self.assembler.assemble(run.scope, mode=run.mode,
            policy_ref=ArtifactReference(owner="runtime-policy", artifact_ref=run.policy_id, version=1))
        if assembled.package is None:
            validation_ref = self.packages.retain_validation(assembled.validation, scope=run.scope)
            found = assembly_findings(assembled.validation, scope=run.scope, evidence_ref=validation_ref)
            new = self.governor.govern(found, scope=run.scope, mode=run.mode, package_ref=decision.package_ref)
            return CapabilityResult(status=ResultStatus.SUCCEEDED,
                artifact_refs=(self.findings.put_decision(new, run_id=run.run_id),))
        self.findings.set_package(run.run_id, self.packages.put(assembled.package))
        return await self.assess(inputs)

    def registrations(self) -> dict[str, TargetCapability]:
        return {ASSESS: TargetCapability(self.assess, replay_safe=True),
            MAINTAIN: TargetCapability(self.maintain, replay_safe=True),
            RELEASE: TargetCapability(self.release, replay_safe=True),
            BLOCK: TargetCapability(self.block), REJECT: TargetCapability(self.reject)}
