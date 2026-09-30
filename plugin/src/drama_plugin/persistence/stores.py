"""Typed durable adapters for the T1–T5R Foundation Store interfaces."""
from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import fcntl
import hashlib
import os
from pathlib import Path
from typing import AsyncIterator

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.generation.contracts import (
    AudioExecutionPlan, DerivedArtifact, ExecutionDiagnostic, FinalPromptArtifact,
    GenerationInput, GenerationPreparation, PromptCoverage, PromptIR,
)
from drama_plugin.governance.contracts import GateDecision, GateFinding, GovernanceInput
from drama_plugin.persistence.ledger import ProductionLedger
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.production.contracts import (
    AssemblyIssueCode, AssemblyValidation, ProductionPackage, SourceReference, SourceOwner,
)
from drama_plugin.production.references import ReferenceExecutionBinding, ReferenceExecutionStore
from drama_plugin.production.sources import OwnedSource, SourceReadError
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeRun, RuntimeScope


def package_scope(package: ProductionPackage) -> RuntimeScope:
    return RuntimeScope(work_id=package.scope.work.artifact_ref,
        scene_id=package.scope.scene.artifact_ref, shot_id=package.scope.shot.artifact_ref)


class DurableRunStore:
    durability = ProductionLedger.durability

    def __init__(self, ledger: ProductionLedger):
        self.ledger = ledger
        self._locks: dict[str, asyncio.Lock] = {}
        self._lock_directory = ledger.path.parent / (ledger.path.name + ".run-locks")
        self._lock_directory.mkdir(exist_ok=True)

    def create(self, run: RuntimeRun) -> RuntimeRun:
        return self.ledger.create_run(run)

    def load(self, run_id: str) -> RuntimeRun:
        return self.ledger.load_run(run_id)

    def save(self, run: RuntimeRun, *, expected_revision: int) -> RuntimeRun:
        return self.ledger.save_run(run, expected_revision=expected_revision)

    @asynccontextmanager
    async def lock(self, run_id: str) -> AsyncIterator[None]:
        """One Target run advances in one process at a time, including capability work.

        SQLite CAS remains the independent stale-writer check. This advisory
        local-file lock is deliberately not a distributed lease or sender claim.
        """
        local = self._locks.setdefault(run_id, asyncio.Lock())
        async with local:
            name = hashlib.sha256(run_id.encode("utf-8")).hexdigest() + ".lock"
            fd = os.open(self._lock_directory / name, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        await asyncio.sleep(0.02)
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)


class DurableProductionPackageStore:
    durability = ProductionLedger.durability
    creative_authority = False

    def __init__(self, ledger: ProductionLedger):
        self.ledger = ledger

    def put(self, package: ProductionPackage) -> ArtifactReference:
        package = ProductionPackage.model_validate(package.model_dump())
        ref = package.artifact_reference()
        self.ledger.put_artifact("production-package", ref, package_scope(package),
            package.fingerprint, package)
        return ref

    def get(self, reference: ArtifactReference) -> ProductionPackage:
        if reference.owner != "production-package" or reference.version != 1:
            raise ValueError("Not a production package reference")
        body, scope, fingerprint = self.ledger.get_artifact("production-package", reference)
        package = ProductionPackage.model_validate(body)
        if package.artifact_reference() != reference or package_scope(package) != scope or package.fingerprint != fingerprint:
            raise ValueError("ProductionPackage reference/scope/fingerprint mismatch")
        return package

    def retain_validation(self, validation: AssemblyValidation, *, scope: RuntimeScope | None = None) -> ArtifactReference:
        if scope is None:
            raise ValueError("Durable assembly validation requires Shot scope")
        validation = AssemblyValidation.model_validate(validation.model_dump())
        identity = "assembly-validation:" + sha256_canonical([
            scope.model_dump(mode="json", by_alias=True), validation.model_dump(mode="json", by_alias=True)])
        ref = ArtifactReference(owner="assembly-validation", artifact_ref=identity, version=1)
        self.ledger.put_artifact("assembly-validation", ref, scope, sha256_canonical(validation), validation)
        return ref

    def validation(self, reference: ArtifactReference) -> AssemblyValidation:
        if reference.owner != "assembly-validation" or reference.version != 1:
            raise ValueError("Not an assembly validation reference")
        body, scope, fingerprint = self.ledger.get_artifact("assembly-validation", reference)
        value = AssemblyValidation.model_validate(body)
        identity = "assembly-validation:" + sha256_canonical([
            scope.model_dump(mode="json", by_alias=True), value.model_dump(mode="json", by_alias=True)])
        if reference.artifact_ref != identity or sha256_canonical(value) != fingerprint:
            raise ValueError("AssemblyValidation identity mismatch")
        return value


class DurableGateFindingStore:
    durability = ProductionLedger.durability
    creative_authority = False

    def __init__(self, ledger: ProductionLedger):
        self.ledger = ledger

    def put_finding(self, finding: GateFinding) -> ArtifactReference:
        finding = GateFinding.model_validate(finding.model_dump())
        identity = "gate-finding:" + sha256_canonical(finding)
        ref = ArtifactReference(owner="gate-finding", artifact_ref=identity, version=1)
        self.ledger.put_artifact("gate-finding", ref, finding.scope, sha256_canonical(finding), finding)
        return ref

    def finding(self, ref: ArtifactReference) -> GateFinding:
        if ref.owner != "gate-finding" or ref.version != 1:
            raise ValueError("Expected a finding reference")
        body, scope, fingerprint = self.ledger.get_artifact("gate-finding", ref)
        item = GateFinding.model_validate(body)
        if item.scope != scope or ref.artifact_ref != "gate-finding:" + fingerprint or sha256_canonical(item) != fingerprint:
            raise ValueError("GateFinding identity mismatch")
        return item

    def put_decision(self, decision: GateDecision, *, run_id: str) -> ArtifactReference:
        decision = GateDecision.model_validate(decision.model_dump())
        if self.ledger.load_run(run_id).scope != decision.scope:
            raise ValueError("GateDecision belongs to another Run scope")
        identity = "gate-decision:" + sha256_canonical(decision)
        ref = ArtifactReference(owner="gate-decision", artifact_ref=identity, version=1)
        self.ledger.put_artifact("gate-decision", ref, decision.scope, sha256_canonical(decision), decision)
        self.ledger.put_index("latest-decision", run_id, ref, scope=decision.scope)
        return ref

    def decision(self, ref: ArtifactReference) -> GateDecision:
        if ref.owner != "gate-decision" or ref.version != 1:
            raise ValueError("Expected a decision reference")
        body, scope, fingerprint = self.ledger.get_artifact("gate-decision", ref)
        item = GateDecision.model_validate(body)
        if item.scope != scope or ref.artifact_ref != "gate-decision:" + fingerprint or sha256_canonical(item) != fingerprint:
            raise ValueError("GateDecision identity mismatch")
        return item

    def latest(self, run_id: str) -> ArtifactReference:
        return ArtifactReference.model_validate(self.ledger.get_index("latest-decision", run_id))

    def bind(self, run_id: str, inputs: GovernanceInput) -> None:
        inputs = GovernanceInput.model_validate(inputs.model_dump())
        scope = self.ledger.load_run(run_id).scope
        if not self.ledger.put_index("governance-input", run_id, inputs, scope=scope, once=True):
            raise ValueError("Governance inputs are already bound")

    def inputs(self, run_id: str) -> GovernanceInput:
        # A crash between Run creation and binding must fail closed; the
        # Foundation's convenient empty default could choose the wrong input.
        return GovernanceInput.model_validate(self.ledger.get_index("governance-input", run_id))

    def set_package(self, run_id: str, ref: ArtifactReference) -> None:
        self.ledger.put_index("governance-input", run_id,
            GovernanceInput(package_ref=ref, finding_refs=self.inputs(run_id).finding_refs),
            scope=self.ledger.load_run(run_id).scope)

    def claim_maintenance(self, run_id: str) -> bool:
        return self.ledger.put_index("governance-maintenance", run_id, 1,
            scope=self.ledger.load_run(run_id).scope, once=True)

    def maintenance_count(self, run_id: str) -> int:
        try:
            return int(self.ledger.get_index("governance-maintenance", run_id))
        except KeyError:
            return 0


class DurableReviewStore:
    """Logical Review Store in the generic typed artifact table."""
    durability = ProductionLedger.durability
    creative_authority = False

    def __init__(self, ledger: ProductionLedger):
        self.ledger = ledger

    def put_user_decision(self, record: UserDecisionRecord) -> ArtifactReference:
        record = UserDecisionRecord.model_validate(record.model_dump())
        run = self.ledger.load_run(record.run_id)
        if run.scope != record.scope:
            raise ValueError("User decision belongs to another Run")
        ref = record.artifact_reference()
        self.ledger.put_artifact("user-decision", ref, record.scope, record.fingerprint, record)
        return ref

    def user_decision(self, ref: ArtifactReference) -> UserDecisionRecord:
        if ref.owner != "user-decision" or ref.version != 1:
            raise ValueError("Expected user decision reference")
        body, scope, fingerprint = self.ledger.get_artifact("user-decision", ref)
        record = UserDecisionRecord.model_validate(body)
        if record.scope != scope or record.fingerprint != fingerprint or record.artifact_reference() != ref:
            raise ValueError("User decision receipt identity mismatch")
        return record


DERIVED_TYPES = (PromptIR, PromptCoverage, FinalPromptArtifact, AudioExecutionPlan, GenerationPreparation)


class DurableGenerationArtifactStore:
    durability = ProductionLedger.durability
    creative_authority = False

    def __init__(self, ledger: ProductionLedger):
        self.ledger = ledger

    def _package_scope(self, ref: ArtifactReference) -> RuntimeScope:
        body, scope, _ = self.ledger.get_artifact("production-package", ref)
        package = ProductionPackage.model_validate(body)
        if package_scope(package) != scope:
            raise ValueError("Derived artifact's Package scope changed")
        return scope

    def put(self, artifact: DerivedArtifact) -> ArtifactReference:
        if type(artifact) not in DERIVED_TYPES:
            raise ValueError("Unknown derived artifact type")
        checked = type(artifact).model_validate(artifact.model_dump())
        ref = checked.artifact_reference()
        scope = self._package_scope(checked.source_package_ref)
        if hasattr(checked, "scope") and checked.scope != scope:
            raise ValueError("Derived artifact belongs to another Shot")
        self.ledger.put_artifact(checked.owner, ref, scope, checked.fingerprint, checked)
        return ref

    def get(self, ref: ArtifactReference, expected: type[DerivedArtifact]):
        if expected not in DERIVED_TYPES or ref.owner != expected.owner or ref.version != 1:
            raise ValueError("Wrong derived artifact reference/type")
        body, scope, fingerprint = self.ledger.get_artifact(expected.owner, ref)
        item = expected.model_validate(body)
        if (item.artifact_reference() != ref or item.fingerprint != fingerprint or
                self._package_scope(item.source_package_ref) != scope or
                hasattr(item, "scope") and item.scope != scope):
            raise ValueError("Derived artifact reference/scope/fingerprint mismatch")
        return item

    def retain_diagnostics(self, diagnostics: tuple[ExecutionDiagnostic, ...],
                           *, scope: RuntimeScope | None = None) -> ArtifactReference:
        if scope is None:
            raise ValueError("Durable diagnostics require Shot scope")
        if len(diagnostics) > 128:
            raise ValueError("Execution diagnostic budget exceeded")
        checked = tuple(ExecutionDiagnostic.model_validate(d.model_dump()) for d in diagnostics)
        fingerprint = sha256_canonical([d.model_dump(mode="json", by_alias=True) for d in checked])
        identity = "execution-diagnostic:" + sha256_canonical([
            scope.model_dump(mode="json", by_alias=True),
            [d.model_dump(mode="json", by_alias=True) for d in checked]])
        ref = ArtifactReference(owner="execution-diagnostic", artifact_ref=identity, version=1)
        self.ledger.put_artifact("execution-diagnostic", ref, scope, fingerprint,
            [d.model_dump(mode="json", by_alias=True) for d in checked])
        return ref

    def diagnostics(self, ref: ArtifactReference) -> tuple[ExecutionDiagnostic, ...]:
        if ref.owner != "execution-diagnostic" or ref.version != 1:
            raise ValueError("Expected diagnostic reference")
        body, scope, fingerprint = self.ledger.get_artifact("execution-diagnostic", ref)
        result = tuple(ExecutionDiagnostic.model_validate(d) for d in body)
        identity = "execution-diagnostic:" + sha256_canonical([
            scope.model_dump(mode="json", by_alias=True), body])
        if ref.artifact_ref != identity or sha256_canonical(body) != fingerprint:
            raise ValueError("Execution diagnostic identity mismatch")
        return result

    def bind(self, run_id: str, inputs: GenerationInput) -> None:
        inputs = GenerationInput.model_validate(inputs.model_dump())
        if not self.ledger.put_index("generation-input", run_id, inputs,
                scope=self.ledger.load_run(run_id).scope, once=True):
            raise ValueError("Generation task is already bound")

    def inputs(self, run_id: str) -> GenerationInput:
        return GenerationInput.model_validate(self.ledger.get_index("generation-input", run_id))

    def set_prepared(self, run_id: str, ref: ArtifactReference) -> None:
        item = self.get(ref, GenerationPreparation)
        if self._package_scope(item.source_package_ref) != self.ledger.load_run(run_id).scope:
            raise ValueError("Prepared artifact belongs to another Run")
        self.ledger.put_index("prepared", run_id, ref, scope=self.ledger.load_run(run_id).scope)

    def prepared(self, run_id: str) -> ArtifactReference:
        return ArtifactReference.model_validate(self.ledger.get_index("prepared", run_id))

    def claim_rebuild(self, run_id: str) -> bool:
        return self.ledger.put_index("generation-rebuild", run_id, 1,
            scope=self.ledger.load_run(run_id).scope, once=True)

    def final_for(self, key: str) -> ArtifactReference | None:
        try:
            return ArtifactReference.model_validate(self.ledger.get_index("final-prompt-key", key))
        except KeyError:
            return None

    def register_final(self, key: str, ref: ArtifactReference) -> None:
        final = self.get(ref, FinalPromptArtifact)
        self.ledger.put_index("final-prompt-key", key, ref,
            scope=self._package_scope(final.source_package_ref), once=True)


class DurableReferenceExecutionStore:
    durability = ProductionLedger.durability
    creative_authority = False

    def __init__(self, ledger: ProductionLedger):
        self.ledger = ledger

    def register(self, binding: ReferenceExecutionBinding) -> SourceReference:
        binding = ReferenceExecutionBinding.model_validate(binding.model_dump())
        source = binding.source()
        ref = source.reference()
        self.ledger.register_reference(ArtifactReference(owner=SourceOwner.PROFESSIONAL.value,
            artifact_ref=ref.artifact_ref, version=ref.version), binding.scope,
            sha256_canonical(source.body), binding)
        return ref

    def _binding(self, ref: ArtifactReference) -> ReferenceExecutionBinding:
        body, scope, fingerprint = self.ledger.get_artifact("reference-execution-binding", ref)
        binding = ReferenceExecutionBinding.model_validate(body)
        if (binding.scope != scope or binding.source().artifact_ref != ref.artifact_ref or
                binding.version != ref.version or sha256_canonical(binding.source().body) != fingerprint):
            raise ValueError("Reference Binding identity/scope/hash mismatch")
        return binding

    def select(self, scope: RuntimeScope) -> tuple[OwnedSource, ...]:
        refs = tuple(ArtifactReference.model_validate(r)
            for r in self.ledger.scoped_index("execution-reference-current", scope))
        return tuple(self._binding(ref).source() for ref in refs)

    def mode(self, scope: RuntimeScope) -> str:
        refs = self.ledger.scoped_index("execution-reference-current", scope)
        roles = {binding.role for binding in (self._binding(ArtifactReference.model_validate(ref)) for ref in refs)
            if any(d.necessity == "REQUIRED" for d in binding.duties)}
        return ("first_last_frame" if "LAST_FRAME" in roles else "image_to_video" if "FIRST_FRAME" in roles
            else "reference" if roles else "text_to_video")

    def resolve(self, ref: SourceReference):
        # Reuse T5R's tested scope/path/authority validator after loading the
        # immutable binding version. No media-library or Canon directory scan.
        try:
            current = ArtifactReference.model_validate(self.ledger.get_index(
                "execution-reference-current", ref.artifact_ref))
        except KeyError as error:
            raise SourceReadError(AssemblyIssueCode.MISSING_REQUIRED_SOURCE,
                ref.owner, ref.artifact_ref) from error
        if current.version != ref.version:
            raise SourceReadError(AssemblyIssueCode.VERSION_MISMATCH, ref.owner, ref.artifact_ref)
        binding = self._binding(ArtifactReference(owner=SourceOwner.PROFESSIONAL.value,
            artifact_ref=ref.artifact_ref, version=ref.version))
        temporary = ReferenceExecutionStore()
        temporary.register(binding)
        return temporary.resolve(ref)
