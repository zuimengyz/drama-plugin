"""One durable Target operation, one attempt and an atomic dispatch claim.

SQLite serializes claims; a single-host advisory lock covers the sender/query and
all intake/review/finishing checkpoints. A dead process releases the lock. The
persisted SUBMITTING boundary remains uncertain regardless of lock ownership.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
from dataclasses import dataclass
import fcntl
import hashlib
import os
from typing import AsyncIterator, TypeVar

from drama_plugin.contracts.base import canonical_json
from drama_plugin.execution.contracts import (
    EXECUTION_TYPES, AVDerivative, AudioExecution, CreativeMediaReview,
    ExecutionArtifact, ExecutionInput, ExecutionOperation, FinishingRecipe, MediaBinding,
    OperationProgress, OperationState, ProviderAttempt, ProviderReceipt, ReviewedAVCandidate, TechnicalMediaReview, MediaIdentity, AttemptHistory,
)
from drama_plugin.persistence.ledger import ProductionLedger
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeRun

E = TypeVar("E", bound=ExecutionArtifact)


class ExecutionIntegrityError(ValueError):
    """Safe existing-owner invariant code, without artifact or credential text."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class OperationCheckpoint:
    operation_ref: ArtifactReference
    attempt_ref: ArtifactReference
    state: OperationState
    receipt_ref: ArtifactReference | None
    progress: OperationProgress


class ExecutionStore:
    def __init__(self, ledger: ProductionLedger):
        self.ledger = ledger
        self.locks = ledger.path.parent / (ledger.path.name + ".execution-locks")
        self.locks.mkdir(exist_ok=True)

    @asynccontextmanager
    async def lock(self, identity: str) -> AsyncIterator[None]:
        path = self.locks / (hashlib.sha256(identity.encode()).hexdigest() + ".lock")
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
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

    def put(self, item: E) -> ArtifactReference:
        item = type(item).model_validate(item.model_dump())
        if type(item) not in EXECUTION_TYPES.values():
            raise ExecutionIntegrityError("EXECUTION_ARTIFACT_TYPE_INVALID", "Unregistered execution artifact")
        if self.ledger.load_run(item.run_id).scope != item.scope:
            raise ExecutionIntegrityError("EXECUTION_ARTIFACT_SCOPE_MISMATCH", "Execution artifact Run scope mismatch")
        # All execution lineage refs must resolve to immutable evidence of the
        # same run/package, not a moving latest-media selector.
        for ref in self._lineage(item):
            body, scope, _ = self.ledger.get_artifact(ref.owner, ref)
            if scope != item.scope:
                raise ExecutionIntegrityError("EXECUTION_LINEAGE_SCOPE_MISMATCH", "Execution lineage crosses Shot scope")
            if ref.owner in EXECUTION_TYPES:
                parent = EXECUTION_TYPES[ref.owner].model_validate(body)
                if parent.run_id != item.run_id or parent.source_package_ref != item.source_package_ref:
                    raise ExecutionIntegrityError("EXECUTION_LINEAGE_PACKAGE_MISMATCH", "Execution lineage crosses Run/Package")
        ref = item.artifact_reference()
        self.ledger.put_artifact(item.owner, ref, item.scope, item.fingerprint, item)
        return ref

    @staticmethod
    def _lineage(item: ExecutionArtifact) -> tuple[ArtifactReference, ...]:
        # Approval is external authority; the named execution fields are exact
        # local artifact relationships. No prose or arbitrary payload admission.
        fields = ("preparation_ref", "final_prompt_ref", "audio_plan_ref", "operation_ref", "attempt_ref", "previous_attempt_ref",
                  "receipt_ref", "recipe_ref", "audio_execution_ref", "video_binding_ref",
                  "video_technical_ref", "video_creative_ref", "audio_technical_ref",
                  "av_derivative_ref", "av_technical_ref", "av_creative_ref")
        return tuple(ref for field in fields if isinstance(ref := getattr(item, field, None), ArtifactReference))

    def get(self, ref: ArtifactReference, model: type[E]) -> E:
        if ref.owner != model.owner or ref.version != 1:
            raise ExecutionIntegrityError("EXECUTION_ARTIFACT_TYPE_MISMATCH", "Execution artifact type mismatch")
        body, scope, fingerprint = self.ledger.get_artifact(model.owner, ref)
        item = model.model_validate(body)
        if item.artifact_reference() != ref or item.scope != scope or item.fingerprint != fingerprint:
            raise ExecutionIntegrityError("EXECUTION_ARTIFACT_IDENTITY_MISMATCH", "Execution artifact identity mismatch")
        return item

    def create_run(self, run: RuntimeRun, inputs: ExecutionInput, recipe: FinishingRecipe) -> RuntimeRun:
        run = RuntimeRun.model_validate(run.model_dump())
        inputs = ExecutionInput.model_validate(inputs.model_dump())
        recipe = FinishingRecipe.model_validate(recipe.model_dump())
        if recipe.run_id != run.run_id or recipe.scope != run.scope or recipe.artifact_reference() != inputs.recipe_ref:
            raise ExecutionIntegrityError("EXECUTION_RECIPE_RUN_MISMATCH", "Execution input/recipe Run mismatch")
        with self.ledger.transaction(write=True) as db:
            self.ledger._insert_run(db, run)
            self.ledger._put_artifact(db, recipe.owner, recipe.artifact_reference(),
                                     recipe.scope, recipe.fingerprint, recipe)
            db.execute("INSERT INTO ledger_index VALUES ('execution-input',?,?,?,?,?)",
                (run.run_id, run.scope.work_id, run.scope.scene_id, run.scope.shot_id, canonical_json(inputs)))
        return run

    def inputs(self, run_id: str) -> ExecutionInput:
        return ExecutionInput.model_validate(self.ledger.get_index("execution-input", run_id))

    def reserve(self, operation: ExecutionOperation, attempt: ProviderAttempt) -> OperationCheckpoint:
        operation_ref = self.put(operation)
        attempt_ref = self.put(attempt)
        if attempt.operation_ref != operation_ref:
            raise ExecutionIntegrityError("EXECUTION_ATTEMPT_OPERATION_MISMATCH", "Attempt belongs to another logical operation")
        with self.ledger.transaction(write=True) as db:
            prior = db.execute("SELECT * FROM production_operation WHERE operation_id=? AND operation_ref_json IS NOT NULL",
                               (operation_ref.artifact_ref,)).fetchone()
            if prior is not None:
                if (prior["operation_ref_json"], prior["attempt_ref_json"]) != (
                        canonical_json(operation_ref), canonical_json(attempt_ref)):
                    raise ExecutionIntegrityError("EXECUTION_ATTEMPT_IDENTITY_CONFLICT", "Logical operation already has a different attempt")
            else:
                db.execute("""INSERT INTO production_operation
                    (operation_id,attempt_identity,run_id,dispatch_state,operation_ref_json,attempt_ref_json,progress_json)
                    VALUES (?,?,?,'RESERVED',?,?,?)""", (operation_ref.artifact_ref, attempt_ref.artifact_ref,
                        operation.run_id, canonical_json(operation_ref), canonical_json(attempt_ref),
                        canonical_json(OperationProgress())))
        return self.checkpoint(operation_ref)

    def checkpoint(self, ref: ArtifactReference) -> OperationCheckpoint:
        with self.ledger.transaction() as db:
            row = db.execute("SELECT * FROM production_operation WHERE operation_id=? AND operation_ref_json IS NOT NULL",
                             (ref.artifact_ref,)).fetchone()
        if row is None:
            raise KeyError(ref.artifact_ref)
        operation = ArtifactReference.model_validate_json(row["operation_ref_json"])
        if operation != ref:
            raise ExecutionIntegrityError("EXECUTION_OPERATION_REF_MISMATCH", "Operation reference mismatch")
        return OperationCheckpoint(operation, ArtifactReference.model_validate_json(row["attempt_ref_json"]),
            OperationState(row["dispatch_state"]),
            ArtifactReference.model_validate_json(row["receipt_ref_json"]) if row["receipt_ref_json"] else None,
            OperationProgress.model_validate_json(row["progress_json"]))

    def claim_dispatch(self, ref: ArtifactReference) -> bool:
        # Persist the uncertainty boundary BEFORE invoking any transport.
        with self.ledger.transaction(write=True) as db:
            return db.execute("""UPDATE production_operation SET dispatch_state='SUBMITTING'
                WHERE operation_id=? AND dispatch_state='RESERVED' AND operation_ref_json IS NOT NULL""",
                (ref.artifact_ref,)).rowcount == 1

    def supplement(self, ref: ArtifactReference, attempt: ProviderAttempt, *, reserved_unknown_microunits: int) -> OperationCheckpoint:
        """Append the UNKNOWN witness before linking one explicitly approved attempt."""
        prior = self.checkpoint(ref)
        operation = self.get(ref, ExecutionOperation)
        old = self.get(prior.attempt_ref, ProviderAttempt)
        if (prior.state != OperationState.UNKNOWN or prior.receipt_ref is not None
                or old.ordinal != 1 or prior.progress.attempt_history
                or attempt.ordinal != 2 or attempt.previous_attempt_ref != prior.attempt_ref
                or attempt.operation_ref != ref or attempt.request_fingerprint != old.request_fingerprint
                or attempt.provider != old.provider or attempt.client_identity == old.client_identity
                or reserved_unknown_microunits < operation.authorization.budget_microunits):
            raise ExecutionIntegrityError("SUPPLEMENTAL_ATTEMPT_NOT_AUTHORIZED", "Exact unresolved prior attempt required")
        from drama_plugin.persistence.review import UserDecisionRecord
        from drama_plugin.execution.live_transport import FinancialTerms
        body, scope, _ = self.ledger.get_artifact('user-decision', attempt.approval_ref)
        receipt = UserDecisionRecord.model_validate(body)
        terms = FinancialTerms.model_validate(receipt.financial_terms)
        terms.validate_current()
        if (not receipt.accepted or scope != operation.scope or receipt.run_id != operation.run_id
                or not terms.supplemental or terms.recovery_operation_ref != ref
                or terms.prior_attempt_ref != prior.attempt_ref
                or terms.reserved_unknown_microunits != reserved_unknown_microunits
                or receipt.source_ref != operation.preparation_ref):
            raise ExecutionIntegrityError("SUPPLEMENTAL_ATTEMPT_NOT_AUTHORIZED", "Exact cost receipt required")
        attempt_ref = self.put(attempt)
        history = AttemptHistory(attempt_ref=prior.attempt_ref, state=prior.state,
            receipt_ref=prior.receipt_ref, query_last_code=prior.progress.query_last_code,
            reserved_cost_microunits=reserved_unknown_microunits)
        progress = OperationProgress.model_validate({**prior.progress.model_dump(), 'attempt_history': (history,)})
        with self.ledger.transaction(write=True) as db:
            changed = db.execute("""UPDATE production_operation SET attempt_identity=?,attempt_ref_json=?,
                dispatch_state='RESERVED',progress_json=? WHERE operation_id=? AND dispatch_state='UNKNOWN'
                AND attempt_ref_json=? AND receipt_ref_json IS NULL""", (attempt_ref.artifact_ref,
                    canonical_json(attempt_ref), canonical_json(progress), ref.artifact_ref,
                    canonical_json(prior.attempt_ref))).rowcount
            if changed != 1:
                raise ExecutionIntegrityError("SUPPLEMENTAL_ATTEMPT_CONFLICT", "Prior attempt changed")
        return self.checkpoint(ref)

    def unknown(self, ref: ArtifactReference) -> None:
        with self.ledger.transaction(write=True) as db:
            db.execute("""UPDATE production_operation SET dispatch_state='UNKNOWN'
                WHERE operation_id=? AND dispatch_state IN ('SUBMITTING','RUNNING','UNKNOWN')""", (ref.artifact_ref,))

    def definite_not_submitted(self, ref: ArtifactReference) -> None:
        # No retry here either: a new authorized operation would be a new decision.
        with self.ledger.transaction(write=True) as db:
            db.execute("UPDATE production_operation SET dispatch_state='FAILED' WHERE operation_id=? AND dispatch_state='SUBMITTING'",
                       (ref.artifact_ref,))

    def receipt(self, ref: ArtifactReference, receipt: ProviderReceipt) -> ArtifactReference:
        checkpoint = self.checkpoint(ref)
        if checkpoint.state == OperationState.RESERVED:
            raise ExecutionIntegrityError("EXECUTION_DISPATCH_CLAIM_MISSING", "Receipt requires a persisted dispatch boundary")
        attempt = self.get(checkpoint.attempt_ref, ProviderAttempt)
        operation = self.get(ref, ExecutionOperation)
        if (receipt.operation_ref, receipt.attempt_ref, receipt.provider, receipt.client_identity,
                receipt.request_fingerprint, receipt.scope, receipt.run_id, receipt.source_package_ref) != (
                ref, checkpoint.attempt_ref, attempt.provider, attempt.client_identity,
                attempt.request_fingerprint, operation.scope, operation.run_id, operation.source_package_ref):
            raise ExecutionIntegrityError("PROVIDER_RECEIPT_IDENTITY_MISMATCH", "Provider receipt identity mismatch")
        if checkpoint.receipt_ref:
            previous = self.get(checkpoint.receipt_ref, ProviderReceipt)
            if previous.remote_identity != receipt.remote_identity:
                raise ExecutionIntegrityError("PROVIDER_TASK_IDENTITY_CHANGED", "Provider task identity changed")
            if checkpoint.state in {OperationState.SUCCEEDED, OperationState.FAILED} and previous != receipt:
                raise ExecutionIntegrityError("PROVIDER_TERMINAL_RESULT_CONFLICT", "Provider terminal result changed")
        receipt_ref = self.put(receipt)
        with self.ledger.transaction(write=True) as db:
            db.execute("""UPDATE production_operation SET dispatch_state=?, receipt_ref_json=?,
                external_task_ref=?,result_identity=? WHERE operation_id=?""", (
                receipt.state, canonical_json(receipt_ref), receipt.remote_identity,
                receipt.result.result_id if receipt.result else None, ref.artifact_ref))
        return receipt_ref

    def progress(self, ref: ArtifactReference, **updates: ArtifactReference | MediaIdentity | int | str | None) -> OperationProgress:
        expected: dict[str, type[ExecutionArtifact]] = {
            "video_ref": MediaBinding, "video_technical_ref": TechnicalMediaReview,
            "video_creative_ref": CreativeMediaReview, "audio_ref": AudioExecution,
            "audio_technical_ref": TechnicalMediaReview, "av_ref": AVDerivative,
            "av_technical_ref": TechnicalMediaReview, "av_creative_ref": CreativeMediaReview,
            "candidate_ref": ReviewedAVCandidate,
        }
        for field, value in updates.items():
            if isinstance(value, ArtifactReference):
                artifact = self.get(value, expected[field])
                if getattr(artifact, "operation_ref", None) != ref:
                    raise ExecutionIntegrityError("EXECUTION_PROGRESS_OPERATION_MISMATCH", "Execution stage belongs to another operation")
        with self.ledger.transaction(write=True) as db:
            row = db.execute("SELECT progress_json FROM production_operation WHERE operation_id=? AND operation_ref_json IS NOT NULL",
                             (ref.artifact_ref,)).fetchone()
            if row is None:
                raise KeyError(ref.artifact_ref)
            prior = OperationProgress.model_validate_json(row["progress_json"])
            for field, value in updates.items():
                old = getattr(prior, field)
                if isinstance(old, (ArtifactReference, MediaIdentity)) and old != value:
                    raise ExecutionIntegrityError("EXECUTION_PROGRESS_IMMUTABLE_CONFLICT", "Completed execution stage is immutable")
                if field in {"intake_attempts", "query_attempts", "unknown_lookup_attempts"} and isinstance(value, int) and value < (getattr(prior, field) or 0):
                    raise ExecutionIntegrityError("EXECUTION_RECOVERY_ATTEMPTS_REWOUND", "Recovery attempts cannot go backwards")
                if field == "query_started_at_ms" and old is not None and old != value:
                    raise ExecutionIntegrityError("EXECUTION_QUERY_HORIZON_CHANGED", "Query recovery horizon is immutable")
                if field == 'attempt_history' and value != old:
                    raise ExecutionIntegrityError("EXECUTION_ATTEMPT_HISTORY_IMMUTABLE", "Prior UNKNOWN witness is immutable")
            next_progress = OperationProgress.model_validate({**prior.model_dump(), **updates})
            db.execute("UPDATE production_operation SET progress_json=? WHERE operation_id=?",
                       (canonical_json(next_progress), ref.artifact_ref))
        return next_progress
