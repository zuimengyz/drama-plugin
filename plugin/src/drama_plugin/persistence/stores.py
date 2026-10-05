"""Typed durable adapters for the T1–T5R Foundation Store interfaces."""
from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import fcntl
import hashlib
import os
import time
from pathlib import Path
from typing import AsyncIterator, Literal, overload

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
        await asyncio.wait_for(local.acquire(),timeout=30)
        try:
            name = hashlib.sha256(run_id.encode("utf-8")).hexdigest() + ".lock"
            fd = os.open(self._lock_directory / name, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                deadline = time.monotonic() + 30
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("RUNTIME_OWNER_BUSY")
                        await asyncio.sleep(0.02)
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
        finally:
            local.release()


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
        # The owner input pins its exact completed decision. The lookup index
        # can then be rebuilt without guessing another run's or newer decision.
        with self.ledger.transaction(write=True) as db:
            row = db.execute("SELECT value_json FROM ledger_index WHERE index_type='governance-input' AND index_key=?", (run_id,)).fetchone()
            if row is not None:
                inputs = GovernanceInput.model_validate_json(row[0]).model_copy(update={"decision_ref": ref})
                db.execute("UPDATE ledger_index SET value_json=? WHERE index_type='governance-input' AND index_key=?",
                    (inputs.model_dump_json(by_alias=True), run_id))
            db.execute("""INSERT INTO ledger_index VALUES ('latest-decision',?,?,?,?,?)
                ON CONFLICT(index_type,index_key) DO UPDATE SET value_json=excluded.value_json""",
                (run_id,decision.scope.work_id,decision.scope.scene_id,decision.scope.shot_id,ref.model_dump_json(by_alias=True)))
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
        ref: ArtifactReference | None
        try:
            ref = ArtifactReference.model_validate(self.ledger.get_index("latest-decision", run_id))
        except KeyError:
            run = self.ledger.load_run(run_id)
            ref = self.inputs(run_id).decision_ref
            if ref is None:
                exact = tuple(r for r in (run.last_result.artifact_refs if run.last_result else ()) if r.owner == "gate-decision")
                if len(exact) != 1:
                    raise KeyError("Exact governance decision unavailable")
                ref = exact[0]
            decision = self.decision(ref)
            if decision.scope != run.scope or decision.mode != run.mode:
                raise ValueError("Governance decision recovery scope/mode conflict")
            self.ledger.put_index("latest-decision",run_id,ref,scope=run.scope)
        assert ref is not None
        self.decision(ref)
        return ref

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
            value = self.ledger.get_index("governance-maintenance", run_id)
        except KeyError:
            return 0
        if type(value) is not int:
            raise ValueError("Stored maintenance claim must be an integer")
        return value


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

    @overload
    def prepared(self, run_id: str, *, required: Literal[True] = True) -> ArtifactReference: ...

    @overload
    def prepared(self, run_id: str, *, required: bool) -> ArtifactReference | None: ...

    def prepared(self, run_id: str, *, required: bool = True) -> ArtifactReference | None:
        try:
            ref = ArtifactReference.model_validate(self.ledger.get_index("prepared", run_id))
        except KeyError:
            inputs = self.inputs(run_id)
            goal = GovernanceInput.model_validate(self.ledger.get_index("governance-input", run_id))
            exact = inputs.cached_preparation_ref
            if exact is not None:
                item = self.get(exact, GenerationPreparation)
                if item.task != inputs.task or item.source_package_ref != goal.package_ref:
                    raise ValueError("Prepared input authority conflict")
            else:
                candidates = []
                with self.ledger.transaction() as db:
                    rows = db.execute("SELECT artifact_id FROM immutable_artifact WHERE artifact_type='generation-preparation' AND work_id=? AND scene_id IS ? AND shot_id IS ? LIMIT 257", (self.ledger.load_run(run_id).scope.work_id,self.ledger.load_run(run_id).scope.scene_id,self.ledger.load_run(run_id).scope.shot_id)).fetchall()
                if len(rows) > 256:
                    raise ValueError("Exact preparation recovery bound exceeded")
                for row in rows:
                    candidate = ArtifactReference(owner="generation-preparation", artifact_ref=row[0], version=1)
                    item = self.get(candidate, GenerationPreparation)
                    if item.task == inputs.task and item.source_package_ref == goal.package_ref:
                        candidates.append(candidate)
                if not candidates and not required:
                    return None
                if len(candidates) != 1:
                    raise KeyError("Exact preparation cannot be uniquely resolved")
                exact = candidates[0]
            self.set_prepared(run_id, exact)
            return exact
        # An explicit retained reference is always checked, even before READY.
        # Missing/corrupt artifacts or multiple candidates are not optional absence.
        self.get(ref, GenerationPreparation)
        return ref

    def claim_rebuild(self, run_id: str) -> bool:
        return self.ledger.put_index("generation-rebuild", run_id, 1,
            scope=self.ledger.load_run(run_id).scope, once=True)

    def final_for(self, key: str) -> ArtifactReference | None:
        try:
            return ArtifactReference.model_validate(self.ledger.get_index("final-prompt-key", key))
        except KeyError:
            # The task itself remains in its input owner; this index is a projection.
            with self.ledger.transaction() as db:
                rows = db.execute("SELECT artifact_id FROM immutable_artifact WHERE artifact_type='final-prompt' LIMIT 257").fetchall()
                inputs = db.execute("SELECT value_json FROM ledger_index WHERE index_type='generation-input' LIMIT 257").fetchall()
            if len(rows) > 256 or len(inputs) > 256:
                raise ValueError("Exact FinalPrompt recovery bound exceeded")
            tasks = [GenerationInput.model_validate_json(row[0]).task for row in inputs]
            matches = []
            for row in rows:
                ref = ArtifactReference(owner="final-prompt", artifact_ref=row[0], version=1)
                final = self.get(ref, FinalPromptArtifact)
                for task in tasks:
                    if final.matches_task(task) and key == sha256_canonical([
                            final.source_package_ref.model_dump(mode="json"), task.model_dump(mode="json"),
                            final.generator_policy_fingerprint]):
                        matches.append(ref)
            unique = set(matches)
            if len(unique) > 1:
                raise ValueError("Conflicting exact FinalPrompt recovery")
            if not unique:
                return None
            ref = unique.pop()
            self.register_final(key, ref)
            return ref

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
