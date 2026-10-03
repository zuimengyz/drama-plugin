"""Small reference-only orchestration contracts; no creative or provider state."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, ClassVar, Self

from pydantic import ConfigDict, Field, SerializerFunctionWrapHandler, StringConstraints, model_serializer, model_validator

from drama_plugin.contracts.base import ContractModel

Identifier = Annotated[str, StringConstraints(min_length=1, max_length=256, pattern=r"^\S+$")]


class RuntimeContract(ContractModel):
    model_config = ConfigDict(frozen=True, revalidate_instances="always")


class ExtendedRuntimeContract(RuntimeContract):
    """Absent optional extensions preserve the bytes/hash of historical contracts."""
    extension_fields: ClassVar[tuple[str, ...]] = ()

    @model_serializer(mode="wrap")
    def preserve_historical_shape(self, handler: SerializerFunctionWrapHandler) -> dict[str, object]:
        data: dict[str, object] = handler(self)
        for field in self.extension_fields:
            if getattr(self, field) is None:
                data.pop(field, None)
                data.pop(type(self).model_fields[field].alias or field, None)
        return data


class RunMode(str, Enum):
    EXPERIMENT = "EXPERIMENT"
    PRODUCTION = "PRODUCTION"


class RuntimeState(str, Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_USER = "WAITING_USER"
    WAITING_EXTERNAL = "WAITING_EXTERNAL"
    BLOCKED = "BLOCKED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ActionKind(str, Enum):
    CALL_CAPABILITY = "CALL_CAPABILITY"
    AUTO_MAINTENANCE = "AUTO_MAINTENANCE"
    REQUEST_USER_DECISION = "REQUEST_USER_DECISION"
    WAIT_EXTERNAL = "WAIT_EXTERNAL"
    COMPLETE = "COMPLETE"
    STOP = "STOP"


class DecisionCategory(str, Enum):
    ART_APPROVAL = "ART_APPROVAL"
    COST_APPROVAL = "COST_APPROVAL"
    MAJOR_ADAPTATION = "MAJOR_ADAPTATION"
    ADOPTION = "ADOPTION"
    FINAL_ACCEPTANCE = "FINAL_ACCEPTANCE"


class ArtifactReference(RuntimeContract):
    """Pointer into its existing owner; no new SourcePin or hash protocol."""
    owner: Identifier
    artifact_ref: Identifier
    version: int | None = Field(default=None, gt=0)


class RuntimeScope(RuntimeContract):
    work_id: Identifier
    scene_id: Identifier | None = None
    shot_id: Identifier | None = None


class UserDecisionRequest(RuntimeContract):
    category: DecisionCategory
    question: str = Field(min_length=1, max_length=300)


class RuntimeAction(RuntimeContract):
    kind: ActionKind
    capability_key: Identifier | None = None
    input_refs: tuple[ArtifactReference, ...] = Field(default=(), max_length=32)
    input_from_previous: bool = False
    decision: UserDecisionRequest | None = None
    external_ref: ArtifactReference | None = None
    reason: Identifier | None = None

    @model_serializer(mode="wrap")
    def preserve_t1_workflow_identity(self, handler: SerializerFunctionWrapHandler) -> dict[str, object]:
        data: dict[str, object] = handler(self)
        if not self.input_from_previous:
            data.pop("inputFromPrevious", None)
            data.pop("input_from_previous", None)
        return data

    @model_validator(mode="after")
    def action_shape(self) -> Self:
        calls = self.kind in {ActionKind.CALL_CAPABILITY, ActionKind.AUTO_MAINTENANCE}
        if calls != (self.capability_key is not None):
            raise ValueError("Only capability/maintenance actions require a capability_key")
        if not calls and self.input_refs:
            raise ValueError("Only capability actions accept input references")
        if self.input_from_previous and (not calls or self.input_refs):
            raise ValueError("Previous-result input requires a capability action without static inputs")
        if (self.kind == ActionKind.REQUEST_USER_DECISION) != (self.decision is not None):
            raise ValueError("Only user-decision actions require a decision")
        if (self.kind == ActionKind.WAIT_EXTERNAL) != (self.external_ref is not None):
            raise ValueError("Only external-wait actions require an external reference")
        if (self.kind == ActionKind.STOP) != (self.reason is not None):
            raise ValueError("Only stop actions require a reason")
        return self


class RuntimeWorkflow(RuntimeContract):
    """Versioned executable steps registered inside the Plugin, not by an agent per tick."""
    workflow_id: Identifier
    steps: tuple[RuntimeAction, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def no_unreachable_steps(self) -> Self:
        if any(s.kind in {ActionKind.COMPLETE, ActionKind.STOP} for s in self.steps[:-1]):
            raise ValueError("Terminal action must be last")
        return self


class ResultStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    FAILED = "FAILED"
    WAITING_EXTERNAL = "WAITING_EXTERNAL"


class CapabilityInput(RuntimeContract):
    run_id: Identifier
    # A run identifier may use all 256 characters; the bounded step suffix adds 3.
    operation_id: Annotated[str, StringConstraints(min_length=1, max_length=260, pattern=r"^\S+$")]
    scope: RuntimeScope
    input_refs: tuple[ArtifactReference, ...] = Field(default=(), max_length=32)


class CapabilityResult(RuntimeContract):
    status: ResultStatus
    artifact_refs: tuple[ArtifactReference, ...] = Field(default=(), max_length=32)
    code: Identifier | None = None
    external_ref: ArtifactReference | None = None

    @model_validator(mode="after")
    def result_shape(self) -> Self:
        if (self.status == ResultStatus.WAITING_EXTERNAL) != (self.external_ref is not None):
            raise ValueError("Only an external wait requires an external reference")
        if self.status in {ResultStatus.FAILED, ResultStatus.RETRYABLE_FAILURE}:
            if self.code is None:
                raise ValueError("Failure requires a code")
        elif self.code is not None:
            raise ValueError("Non-failure result cannot carry a failure code")
        return self


class ExecutionRevision(RuntimeContract):
    """Contract identity and authoritative input identity, without author text."""
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    input_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class ExecutionInspection(RuntimeContract):
    revision: ExecutionRevision
    completed: bool


class ExhaustedExecutionEvidence(RuntimeContract):
    """Explicit audited attestation for checkpoints predating revision capture.

    This is supplied by the authorized recovery caller, never by model output.
    It remains in the durable checkpoint and does not rewrite historical rows.
    """
    revision: ExecutionRevision
    evidence_ref: ArtifactReference
    historical_attempts: int = Field(ge=1)


class RepairResumeRecord(RuntimeContract):
    cursor: int = Field(ge=0, lt=32)
    capability_key: Identifier
    exhausted: ExhaustedExecutionEvidence
    current: ExecutionRevision
    attempts: int = Field(default=0, ge=0, le=1)
    limit: int = Field(default=1, ge=1, le=1)


class RuntimeRun(RuntimeContract):
    schema_version: int = Field(default=1, ge=1, le=1)
    run_id: Identifier
    scope: RuntimeScope
    mode: RunMode
    policy_id: Identifier
    workflow_id: Identifier
    workflow_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    state: RuntimeState = RuntimeState.PLANNED
    cursor: int = Field(default=0, ge=0, le=32)
    step_attempts: int = Field(default=0, ge=0)
    revision: int = Field(default=0, ge=0)
    last_result: CapabilityResult | None = None
    wait_reason: Identifier | None = None
    execution_revision: ExecutionRevision | None = None
    repair_resumes: tuple[RepairResumeRecord, ...] = Field(default=(), max_length=32)

    @model_serializer(mode="wrap")
    def preserve_existing_checkpoint_shape(self, handler: SerializerFunctionWrapHandler) -> dict[str, object]:
        data: dict[str, object] = handler(self)
        for field, alias, absent in (("execution_revision", "executionRevision", self.execution_revision is None),
                                     ("repair_resumes", "repairResumes", not self.repair_resumes)):
            if absent:
                data.pop(field, None)
                data.pop(alias, None)
        return data

    def active_repair(self) -> RepairResumeRecord | None:
        return next((r for r in self.repair_resumes if r.cursor == self.cursor), None)

    def attempt_identity(self) -> str:
        operation = f"{self.run_id}:{self.cursor}"
        repair = self.active_repair()
        if repair is not None and repair.attempts:
            return f"{operation}:repair:{repair.current.fingerprint}:{repair.attempts}"
        return f"{operation}:{self.step_attempts}"

    @model_validator(mode="after")
    def wait_shape(self) -> Self:
        if len({r.cursor for r in self.repair_resumes}) != len(self.repair_resumes):
            raise ValueError("Only one repair opportunity per step")
        if any(r.cursor > self.cursor or r.current.input_fingerprint != r.exhausted.revision.input_fingerprint
               or r.current.fingerprint == r.exhausted.revision.fingerprint for r in self.repair_resumes):
            raise ValueError("Repair revision/input identity invalid")
        waiting = self.state in {
            RuntimeState.WAITING_USER, RuntimeState.WAITING_EXTERNAL, RuntimeState.BLOCKED,
        }
        if waiting != (self.wait_reason is not None):
            raise ValueError("Only a waiting/blocked state requires a wait reason")
        if self.state == RuntimeState.WAITING_EXTERNAL:
            if self.last_result is None or self.last_result.status != ResultStatus.WAITING_EXTERNAL:
                raise ValueError("External wait requires its reference-only result")
        return self


def validate_repair_history(previous: RuntimeRun, following: RuntimeRun) -> None:
    """Append-only repair provenance; consumption may only advance once."""
    if len(following.repair_resumes) < len(previous.repair_resumes):
        raise ValueError("Repair history cannot be removed")
    for old, new in zip(previous.repair_resumes, following.repair_resumes):
        if old.model_dump(exclude={"attempts"}) != new.model_dump(exclude={"attempts"}) or new.attempts < old.attempts:
            raise ValueError("Repair history is immutable")
