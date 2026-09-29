"""Small reference-only orchestration contracts; no creative or provider state."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Self

from pydantic import ConfigDict, Field, StringConstraints, model_validator

from drama_plugin.contracts.base import ContractModel

Identifier = Annotated[str, StringConstraints(min_length=1, max_length=256, pattern=r"^\S+$")]


class RuntimeContract(ContractModel):
    model_config = ConfigDict(frozen=True, revalidate_instances="always")


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
    decision: UserDecisionRequest | None = None
    external_ref: ArtifactReference | None = None
    reason: Identifier | None = None

    @model_validator(mode="after")
    def action_shape(self) -> Self:
        calls = self.kind in {ActionKind.CALL_CAPABILITY, ActionKind.AUTO_MAINTENANCE}
        if calls != (self.capability_key is not None):
            raise ValueError("Only capability/maintenance actions require a capability_key")
        if not calls and self.input_refs:
            raise ValueError("Only capability actions accept input references")
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

    @model_validator(mode="after")
    def wait_shape(self) -> Self:
        waiting = self.state in {
            RuntimeState.WAITING_USER, RuntimeState.WAITING_EXTERNAL, RuntimeState.BLOCKED,
        }
        if waiting != (self.wait_reason is not None):
            raise ValueError("Only a waiting/blocked state requires a wait reason")
        if self.state == RuntimeState.WAITING_EXTERNAL:
            if self.last_result is None or self.last_result.status != ResultStatus.WAITING_EXTERNAL:
                raise ValueError("External wait requires its reference-only result")
        return self
