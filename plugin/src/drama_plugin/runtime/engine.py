"""Plugin-owned bounded orchestration. No creative planning or Provider submission."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.runtime.bridge import CapabilityExecutor, ExecutionInspector
from drama_plugin.runtime.contracts import (
    ActionKind, ArtifactReference, CapabilityInput, CapabilityResult, ResultStatus,
    RunMode, RuntimeAction, RuntimeRun, RuntimeScope, RuntimeState, RuntimeWorkflow,
    ExecutionInspection, ExhaustedExecutionEvidence, RepairResumeRecord,
)
from drama_plugin.runtime.policy import RuntimePolicy, default_policies
from drama_plugin.runtime.store import InMemoryRunStore

TERMINAL_STATES = frozenset({RuntimeState.SUCCEEDED, RuntimeState.FAILED})
TRANSITIONS = {
    RuntimeState.PLANNED: frozenset({RuntimeState.READY}),
    RuntimeState.READY: frozenset({RuntimeState.RUNNING, RuntimeState.WAITING_USER,
        RuntimeState.WAITING_EXTERNAL, RuntimeState.SUCCEEDED, RuntimeState.FAILED}),
    RuntimeState.RUNNING: frozenset({RuntimeState.READY, RuntimeState.WAITING_EXTERNAL,
        RuntimeState.BLOCKED, RuntimeState.FAILED}),
    RuntimeState.WAITING_USER: frozenset({RuntimeState.READY, RuntimeState.FAILED}),
    RuntimeState.WAITING_EXTERNAL: frozenset({RuntimeState.READY, RuntimeState.BLOCKED, RuntimeState.FAILED}),
    RuntimeState.BLOCKED: frozenset({RuntimeState.READY, RuntimeState.FAILED}),
    RuntimeState.SUCCEEDED: frozenset(),
    RuntimeState.FAILED: frozenset(),
}


def validate_transition(previous: RuntimeState, following: RuntimeState) -> None:
    if following not in TRANSITIONS[previous]:
        raise ValueError(f"Invalid runtime transition: {previous.value} -> {following.value}")


def foundation_workflows() -> dict[str, RuntimeWorkflow]:
    workflow = RuntimeWorkflow(workflow_id="inspect-work:v1", steps=(
        RuntimeAction(kind=ActionKind.CALL_CAPABILITY, capability_key="work.get_work"),
    ))
    return {workflow.workflow_id: workflow}


class RuntimeEngine:
    """Own next_action and run-until-wait/terminal for registered Plugin workflows."""

    def __init__(self, executor: CapabilityExecutor, *, store: InMemoryRunStore | None = None,
                 workflows: Mapping[str, RuntimeWorkflow] | None = None,
                 policies: Mapping[RunMode, RuntimePolicy] | None = None) -> None:
        self.executor = executor
        self.store = store if store is not None else InMemoryRunStore()
        self._workflows = dict(foundation_workflows() if workflows is None else workflows)
        self._policies = dict(default_policies() if policies is None else policies)
        if any(key != w.workflow_id for key, w in self._workflows.items()):
            raise ValueError("Workflow registry identity mismatch")
        if any(key != p.mode or p.max_step_attempts < 1 for key, p in self._policies.items()):
            raise ValueError("Policy registry identity mismatch")

    def draft_run(self, *, work_id: str, mode: RunMode,
                   workflow_id: str = "inspect-work:v1", run_id: str | None = None,
                   scene_id: str | None = None, shot_id: str | None = None) -> RuntimeRun:
        policy = self._policies[mode]
        workflow = self._workflows[workflow_id]
        return RuntimeRun(run_id=run_id or str(uuid4()),
            scope=RuntimeScope(work_id=work_id, scene_id=scene_id, shot_id=shot_id),
            mode=mode, policy_id=policy.policy_id, workflow_id=workflow_id,
            workflow_fingerprint=sha256_canonical(workflow))

    def create_run(self, *, work_id: str, mode: RunMode,
                   workflow_id: str = "inspect-work:v1", run_id: str | None = None,
                   scene_id: str | None = None, shot_id: str | None = None) -> RuntimeRun:
        return self.store.create(self.draft_run(work_id=work_id, mode=mode,
            workflow_id=workflow_id, run_id=run_id, scene_id=scene_id, shot_id=shot_id))

    def _context(self, run: RuntimeRun) -> tuple[RuntimePolicy, RuntimeWorkflow]:
        policy, workflow = self._policies[run.mode], self._workflows[run.workflow_id]
        if run.policy_id != policy.policy_id or run.workflow_fingerprint != sha256_canonical(workflow):
            raise ValueError("Runtime policy/workflow changed; explicit migration required")
        if run.cursor > len(workflow.steps) or run.step_attempts > policy.max_step_attempts:
            raise ValueError("Runtime cursor/attempt bound invalid")
        if run.state == RuntimeState.PLANNED and (
            run.cursor != 0 or run.step_attempts != 0 or run.last_result is not None
        ):
            raise ValueError("Planned run cannot contain execution progress")
        if run.state == RuntimeState.SUCCEEDED and run.cursor < len(workflow.steps):
            if workflow.steps[run.cursor].kind != ActionKind.COMPLETE:
                raise ValueError("Successful run cannot skip pending steps")
        if run.state in {RuntimeState.RUNNING, RuntimeState.BLOCKED}:
            if run.cursor == len(workflow.steps) or workflow.steps[run.cursor].kind not in {
                ActionKind.CALL_CAPABILITY, ActionKind.AUTO_MAINTENANCE,
            } or run.step_attempts < 1:
                raise ValueError("In-flight/blocked run must identify a capability step")
        if run.state == RuntimeState.WAITING_USER:
            if run.cursor == len(workflow.steps) or policy.next_action(run, workflow).kind != ActionKind.REQUEST_USER_DECISION:
                raise ValueError("User wait must identify its decision step")
        if run.state == RuntimeState.WAITING_EXTERNAL:
            if run.cursor == len(workflow.steps) or workflow.steps[run.cursor].kind not in {
                ActionKind.CALL_CAPABILITY, ActionKind.AUTO_MAINTENANCE, ActionKind.WAIT_EXTERNAL,
            }:
                raise ValueError("External wait must identify its dependency step")
            step = workflow.steps[run.cursor]
            assert run.last_result is not None
            if step.kind == ActionKind.WAIT_EXTERNAL and step.external_ref != run.last_result.external_ref:
                raise ValueError("External wait reference differs from its workflow")
        return policy, workflow

    def next_action(self, run_id: str) -> RuntimeAction:
        run = self.store.load(run_id)
        policy, workflow = self._context(run)
        return policy.next_action(run, workflow)

    def _transition(self, run: RuntimeRun, state: RuntimeState, **changes: Any) -> RuntimeRun:
        validate_transition(run.state, state)
        values = run.model_dump()
        values.update(changes, state=state, revision=run.revision + 1)
        following = RuntimeRun.model_validate(values)
        self._context(following)
        return self.store.save(following, expected_revision=run.revision)

    def _record_result(self, run: RuntimeRun, result: CapabilityResult) -> RuntimeRun:
        if result.status == ResultStatus.SUCCEEDED:
            return self._transition(run, RuntimeState.READY, cursor=run.cursor + 1,
                step_attempts=0, wait_reason=None, last_result=result, execution_revision=None)
        if result.status == ResultStatus.WAITING_EXTERNAL:
            return self._transition(run, RuntimeState.WAITING_EXTERNAL,
                wait_reason="EXTERNAL_RESULT_PENDING", last_result=result)
        state = RuntimeState.BLOCKED if result.status == ResultStatus.RETRYABLE_FAILURE and run.active_repair() is None else RuntimeState.FAILED
        return self._transition(run, state, last_result=result,
            wait_reason=result.code if state == RuntimeState.BLOCKED else None)

    def _inspection(self, run: RuntimeRun, key: str) -> ExecutionInspection | None:
        if not isinstance(self.executor, ExecutionInspector):
            return None
        return self.executor.inspect_execution(key, CapabilityInput(run_id=run.run_id,
            operation_id=f"{run.run_id}:{run.cursor}", scope=run.scope))

    async def repair_resume(self, run_id: str, *, cursor: int, capability_key: str,
                            exhausted: ExhaustedExecutionEvidence) -> RuntimeRun:
        """One explicitly authorized repair per step; ordinary retry is unchanged.

        Pre-revision checkpoints require audited historical evidence from the
        recovery caller. Later checkpoints must also match their captured revision.
        No artifact contents or secrets enter this metadata.
        """
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            policy, workflow = self._context(run)
            if (run.state != RuntimeState.FAILED or run.last_result is None
                    or run.last_result.status != ResultStatus.FAILED or run.last_result.code != "RETRY_LIMIT_REACHED"):
                raise ValueError("REPAIR_REQUIRES_EXHAUSTED_FAILURE")
            if (cursor != run.cursor or cursor >= len(workflow.steps)
                    or workflow.steps[cursor].capability_key != capability_key):
                raise ValueError("REPAIR_STEP_MISMATCH")
            if run.active_repair() is not None:
                raise ValueError("REPAIR_OPPORTUNITY_ALREADY_USED")
            if (run.step_attempts != policy.max_step_attempts
                    or exhausted.historical_attempts != run.step_attempts):
                raise ValueError("REPAIR_ATTEMPT_HISTORY_MISMATCH")
            inspection = self._inspection(run, capability_key)
            if inspection is None or inspection.completed:
                raise ValueError("REPAIR_UNSUPPORTED_OR_STEP_COMPLETED")
            if run.execution_revision is not None and run.execution_revision != exhausted.revision:
                raise ValueError("REPAIR_EXHAUSTED_REVISION_MISMATCH")
            if inspection.revision.input_fingerprint != exhausted.revision.input_fingerprint:
                raise ValueError("REPAIR_AUTHORITY_INPUT_CHANGED")
            if inspection.revision.fingerprint == exhausted.revision.fingerprint:
                raise ValueError("RETRY_LIMIT_REACHED")
            record = RepairResumeRecord(cursor=cursor, capability_key=capability_key,
                exhausted=exhausted, current=inspection.revision)
            # Deliberately do not widen FAILED's general transition table.
            following = RuntimeRun.model_validate({**run.model_dump(), "state": RuntimeState.READY,
                "revision": run.revision + 1, "wait_reason": None,
                "execution_revision": inspection.revision,
                "repair_resumes": (*run.repair_resumes, record)})
            self._context(following)
            return self.store.save(following, expected_revision=run.revision)

    async def run(self, run_id: str, *, max_ticks: int = 64) -> RuntimeRun:
        """Advance internally; return on genuine waits, failures or terminal state.

        max_ticks bounds one turn, not a new production state. The injected
        store serializes callers advancing the same Run.
        """
        if max_ticks < 1:
            raise ValueError("max_ticks must be positive")
        async with self.store.lock(run_id):
            for _ in range(max_ticks):
                run = self.store.load(run_id)
                self._context(run)
                if run.state in TERMINAL_STATES or run.state in {
                    RuntimeState.WAITING_USER, RuntimeState.WAITING_EXTERNAL, RuntimeState.BLOCKED,
                }:
                    return run
                if run.state == RuntimeState.RUNNING:
                    return self._transition(run, RuntimeState.BLOCKED, wait_reason="INTERRUPTED_CAPABILITY")
                if run.state == RuntimeState.PLANNED:
                    self._transition(run, RuntimeState.READY)
                    continue
                action = self.next_action(run_id)
                if action.kind == ActionKind.COMPLETE:
                    return self._transition(run, RuntimeState.SUCCEEDED)
                if action.kind == ActionKind.STOP:
                    return self._transition(run, RuntimeState.FAILED,
                        last_result=CapabilityResult(status=ResultStatus.FAILED, code=action.reason))
                if action.kind == ActionKind.REQUEST_USER_DECISION:
                    return self._transition(run, RuntimeState.WAITING_USER, wait_reason="USER_DECISION_PENDING")
                if action.kind == ActionKind.WAIT_EXTERNAL:
                    return self._transition(run, RuntimeState.WAITING_EXTERNAL,
                        wait_reason="EXTERNAL_RESULT_PENDING", last_result=CapabilityResult(
                            status=ResultStatus.WAITING_EXTERNAL, external_ref=action.external_ref))
                assert action.capability_key is not None
                repair = run.active_repair()
                try:
                    inspection = self._inspection(run, action.capability_key)
                except Exception:
                    return self._transition(run, RuntimeState.FAILED,
                        last_result=CapabilityResult(status=ResultStatus.FAILED, code="EXECUTION_IDENTITY_UNAVAILABLE"))
                if repair is not None:
                    if (repair.attempts >= repair.limit or inspection is None or inspection.completed
                            or inspection.revision != repair.current):
                        return self._transition(run, RuntimeState.FAILED,
                            last_result=CapabilityResult(status=ResultStatus.FAILED, code="REPAIR_EXECUTION_DENIED"))
                    consumed = RepairResumeRecord.model_validate({**repair.model_dump(), "attempts": 1})
                    executing = self._transition(run, RuntimeState.RUNNING,
                        repair_resumes=tuple(consumed if r.cursor == run.cursor else r for r in run.repair_resumes))
                elif run.step_attempts >= self._policies[run.mode].max_step_attempts:
                    return self._transition(run, RuntimeState.FAILED,
                        last_result=CapabilityResult(status=ResultStatus.FAILED, code="RETRY_LIMIT_REACHED"))
                else:
                    revision = inspection.revision if inspection is not None else None
                    if run.execution_revision is not None and run.execution_revision != revision:
                        return self._transition(run, RuntimeState.FAILED,
                            last_result=CapabilityResult(status=ResultStatus.FAILED, code="EXECUTION_REVISION_CHANGED"))
                    executing = self._transition(run, RuntimeState.RUNNING,
                        step_attempts=run.step_attempts + 1, execution_revision=revision)
                inputs = CapabilityInput(run_id=run.run_id, operation_id=f"{run.run_id}:{run.cursor}",
                    scope=run.scope, input_refs=(run.last_result.artifact_refs
                        if action.input_from_previous and run.last_result is not None else action.input_refs))
                try:
                    result = CapabilityResult.model_validate(await self.executor.execute(action.capability_key, inputs))
                except Exception:
                    # Do not persist arbitrary exception strings containing Canon or secrets.
                    result = CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="CAPABILITY_EXECUTION_ERROR")
                self._record_result(executing, result)
            return self.store.load(run_id)

    def serialize(self, run_id: str) -> str:
        run = self.store.load(run_id)
        self._context(run)
        return run.model_dump_json(by_alias=True)

    def restore(self, snapshot: str) -> RuntimeRun:
        run = RuntimeRun.model_validate_json(snapshot)
        self._context(run)
        self.store.create(run)
        if run.state == RuntimeState.RUNNING:
            return self._transition(run, RuntimeState.BLOCKED, wait_reason="INTERRUPTED_CAPABILITY")
        return run

    async def recover_run(self, run_id: str) -> RuntimeRun:
        """Open the same durable checkpoint after restart, without recreating it."""
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            self._context(run)
            if run.state == RuntimeState.RUNNING:
                return self._transition(run, RuntimeState.BLOCKED, wait_reason="INTERRUPTED_CAPABILITY")
            return run

    async def retry(self, run_id: str) -> RuntimeRun:
        """Internal retry routing, never an artificial user approval of bookkeeping."""
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            policy, workflow = self._context(run)
            if run.state != RuntimeState.BLOCKED:
                raise ValueError("Only a blocked capability can be retried")
            key = workflow.steps[run.cursor].capability_key
            assert key is not None
            if not self.executor.replay_safe(key):
                raise ValueError("Capability is not declared replay-safe; reconciliation required")
            if run.step_attempts >= policy.max_step_attempts:
                return self._transition(run, RuntimeState.FAILED, wait_reason=None,
                    last_result=CapabilityResult(status=ResultStatus.FAILED, code="RETRY_LIMIT_REACHED"))
            return self._transition(run, RuntimeState.READY, wait_reason=None)

    def decision_id(self, run_id: str) -> str:
        run = self.store.load(run_id)
        if run.state != RuntimeState.WAITING_USER:
            raise ValueError("Run is not waiting for a user decision")
        return f"{run.run_id}:{run.cursor}"

    async def decide(self, run_id: str, *, decision_id: str, accepted: bool,
                     decision_ref: ArtifactReference) -> RuntimeRun:
        if not isinstance(accepted, bool):
            raise ValueError("User decision must be an explicit boolean")
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            self._context(run)
            if decision_id != self.decision_id(run_id):
                raise ValueError("Decision belongs to another step")
            if accepted:
                return self._transition(run, RuntimeState.READY, cursor=run.cursor + 1,
                    wait_reason=None, last_result=CapabilityResult(status=ResultStatus.SUCCEEDED,
                        artifact_refs=(decision_ref,)))
            return self._transition(run, RuntimeState.FAILED, wait_reason=None,
                last_result=CapabilityResult(status=ResultStatus.FAILED, code="USER_DECLINED",
                    artifact_refs=(decision_ref,)))

    async def record_external_result(self, run_id: str, *, external_ref: ArtifactReference,
                                     result: CapabilityResult) -> RuntimeRun:
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            self._context(run)
            if run.state != RuntimeState.WAITING_EXTERNAL or run.last_result is None:
                raise ValueError("Run is not waiting for an external result")
            if run.last_result.external_ref != external_ref:
                raise ValueError("External result belongs to another dependency")
            result = CapabilityResult.model_validate(result)
            if result.status == ResultStatus.WAITING_EXTERNAL:
                raise ValueError("External result must resolve this wait")
            if result.status == ResultStatus.RETRYABLE_FAILURE:
                raise ValueError("Transient external failure leaves the dependency wait unresolved")
            return self._record_result(run, result)
