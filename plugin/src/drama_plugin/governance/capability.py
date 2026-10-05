"""Native shadow checks and bounded local rebuild, never Canon or paid side effects."""
from __future__ import annotations

from drama_plugin.governance.checks import assembly_findings
from drama_plugin.governance.contracts import GateCategory, GateCode, GateDecision, GateFinding, RULES
from drama_plugin.governance.governor import GateGovernor
from drama_plugin.governance.policy import ASSESS, BLOCK, MAINTAIN, REJECT, RELEASE, RESOLVE
from drama_plugin.governance.store import FindingStore
from drama_plugin.production.assembler import ShotAssembler
from drama_plugin.production.store import PackageStore
from drama_plugin.runtime.capabilities import TargetCapability
from drama_plugin.runtime.contracts import ArtifactReference, CapabilityInput, CapabilityResult, ResultStatus, RecoveryClass, UserDecisionRequest, DecisionCategory
from drama_plugin.runtime.store import RunStore


class GateGovernanceCapability:
    def __init__(self, governor: GateGovernor, findings: FindingStore, packages: PackageStore,
                 assembler: ShotAssembler, runs: RunStore):
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

    def consume_user_decision(self, run_id: str, receipt_ref: ArtifactReference) -> GateDecision:
        """Consume one exact category; retain the other independent requests."""
        from drama_plugin.persistence.review import UserDecisionRecord
        from drama_plugin.persistence.stores import DurableRunStore
        if not isinstance(self.runs, DurableRunStore):
            raise ValueError("Durable user decision owner required")
        run = self.runs.load(run_id)
        current_ref = self.findings.latest(run_id)
        current = self.findings.decision(current_ref)
        if current.user_decision is None and current.effect != "REVIEW_REQUIRED":
            raise ValueError("No pending independent user category")
        category = current.user_decision.category if current.user_decision else DecisionCategory.ART_APPROVAL
        body, scope, fingerprint = self.runs.ledger.get_artifact("user-decision", receipt_ref)
        receipt = UserDecisionRecord.model_validate(body)
        found = tuple(self.findings.finding(ref) for ref in current.finding_refs)
        selected = tuple(f for f in found if RULES[f.code][2] == category or
            current.effect == "REVIEW_REQUIRED" and f.category == GateCategory.WARNING and f.required)
        evidence = {f.evidence_ref for f in selected}
        targets = {current_ref}
        if len(evidence) == 1:
            targets.update(evidence)
        if current.package_ref and (not evidence or evidence == {current.package_ref}):
            targets.add(current.package_ref)
        if (receipt.artifact_reference() != receipt_ref or receipt.fingerprint != fingerprint or receipt.run_id != run_id
                or scope != run.scope or receipt.scope != run.scope or receipt.category != category
                or receipt.source_ref not in targets or not receipt.accepted):
            raise ValueError("User decision category/exact target mismatch")
        remaining = tuple(f for f in found if f not in selected)
        following = self.governor.govern(remaining, scope=run.scope, mode=run.mode, package_ref=current.package_ref)
        self.findings.put_decision(following, run_id=run_id)
        return following

    async def release(self, inputs: CapabilityInput) -> CapabilityResult:
        decision = self._decision(inputs)
        if decision.effect != "CONTINUE" or decision.package_ref is None:
            raise ValueError("Only continued decisions release packages")
        return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(decision.package_ref,))

    async def block(self, inputs: CapabilityInput) -> CapabilityResult:
        decision = self._decision(inputs)
        if decision.effect in {"CAPABILITY_ABSENT", "REVIEW_REQUIRED"}:
            return await self.resolve(inputs)
        if decision.effect != "BLOCK":
            raise ValueError("Only four-family hard stops use this capability")
        return CapabilityResult(status=ResultStatus.FAILED, code="GOVERNED_HARD_STOP",
                                artifact_refs=inputs.input_refs, recovery_class=RecoveryClass.HARD_BLOCK)

    async def resolve(self, inputs: CapabilityInput) -> CapabilityResult:
        decision = self._decision(inputs)
        if decision.effect == "CAPABILITY_ABSENT":
            return CapabilityResult(status=ResultStatus.FAILED, code="REQUIRED_CAPABILITY_ABSENT", artifact_refs=inputs.input_refs,
                recovery_class=RecoveryClass.HARD_BLOCK)
        if decision.effect == "REVIEW_REQUIRED":
            return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, artifact_refs=inputs.input_refs,
                external_ref=inputs.input_refs[0], recovery_class=RecoveryClass.USER_DECISION,
                user_decision=UserDecisionRequest(category=DecisionCategory.ART_APPROVAL, question="Review the exact candidate and required quality findings before continuing."))
        return await self.release(inputs)

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
            return CapabilityResult(status=ResultStatus.FAILED,
                code="TECHNICAL_MAINTENANCE_EXHAUSTED", artifact_refs=inputs.input_refs, recovery_class=RecoveryClass.HARD_BLOCK)
        tasks = [self.findings.finding(ref) for ref in decision.finding_refs
                 if self.findings.finding(ref).category == GateCategory.AUTO_MAINTENANCE]
        receipt_tasks = [task for task in tasks if task.code == GateCode.RECEIPT_RECONCILIATION]
        if receipt_tasks:
            targets = {task.evidence_ref for task in receipt_tasks}
            if len(targets) != 1 or next(iter(targets)).owner not in {"provider-receipt", "provider-attempt", "execution-operation"}:
                return CapabilityResult(status=ResultStatus.FAILED, code="RECONCILIATION_IDENTITY_OR_OWNER_ABSENT", artifact_refs=inputs.input_refs, recovery_class=RecoveryClass.HARD_BLOCK)
            target=next(iter(targets))
            from drama_plugin.persistence.stores import DurableRunStore
            from drama_plugin.execution.contracts import ProviderReceipt,ProviderAttempt,ExecutionOperation,ExecutionArtifact
            if not isinstance(self.runs,DurableRunStore):
                return CapabilityResult(status=ResultStatus.FAILED,code="RECONCILIATION_IDENTITY_OR_OWNER_ABSENT",artifact_refs=inputs.input_refs,recovery_class=RecoveryClass.HARD_BLOCK)
            try:
                body,scope,fingerprint=self.runs.ledger.get_artifact(target.owner,target)
                models: dict[str,type[ExecutionArtifact]]={"provider-receipt":ProviderReceipt,"provider-attempt":ProviderAttempt,"execution-operation":ExecutionOperation}
                model=models[target.owner]
                authoritative=model.model_validate(body)
                if authoritative.artifact_reference()!=target or authoritative.fingerprint!=fingerprint or scope!=inputs.scope:
                    raise ValueError("Reconciliation owner scope mismatch")
            except (KeyError,ValueError):
                return CapabilityResult(status=ResultStatus.FAILED,code="RECONCILIATION_IDENTITY_OR_OWNER_ABSENT",artifact_refs=inputs.input_refs,recovery_class=RecoveryClass.HARD_BLOCK)
            return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,external_ref=target,
                artifact_refs=inputs.input_refs,recovery_class=RecoveryClass.WAIT_EXTERNAL)
        # Package/projection maintenance is deterministic reassembly from the
        # existing exact Assembler inputs; it cannot invent authoritative facts.
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
