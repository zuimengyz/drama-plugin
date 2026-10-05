"""Plugin-owned bounded orchestration. No creative planning or Provider submission."""
from __future__ import annotations

from collections.abc import Mapping
import asyncio
import sqlite3
from typing import Any
from uuid import uuid4

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.runtime.bridge import CapabilityAvailability, CapabilityExecutor, ExecutionInspector
from drama_plugin.runtime.contracts import (
    ActionKind, ArtifactReference, CapabilityInput, CapabilityResult, ResultStatus,
    RunMode, RuntimeAction, RuntimeRun, RuntimeScope, RuntimeState, RuntimeWorkflow,
    ExecutionInspection, ExhaustedExecutionEvidence, RepairResumeRecord, RecoveryClass,
    InspectionRepairRecord, ExternalRepairRecord,
)
from drama_plugin.runtime.policy import RuntimePolicy, default_policies
from drama_plugin.runtime.store import InMemoryRunStore, RunStore

TERMINAL_STATES = frozenset({RuntimeState.SUCCEEDED, RuntimeState.FAILED})
TRANSITIONS = {
    RuntimeState.PLANNED: frozenset({RuntimeState.READY}),
    RuntimeState.READY: frozenset({RuntimeState.RUNNING, RuntimeState.WAITING_USER,
        RuntimeState.WAITING_EXTERNAL, RuntimeState.SUCCEEDED, RuntimeState.FAILED}),
    RuntimeState.RUNNING: frozenset({RuntimeState.READY, RuntimeState.WAITING_USER, RuntimeState.WAITING_EXTERNAL,
        RuntimeState.BLOCKED, RuntimeState.FAILED}),
    RuntimeState.WAITING_USER: frozenset({RuntimeState.READY, RuntimeState.WAITING_EXTERNAL, RuntimeState.BLOCKED, RuntimeState.FAILED}),
    RuntimeState.WAITING_EXTERNAL: frozenset({RuntimeState.READY, RuntimeState.WAITING_USER, RuntimeState.BLOCKED, RuntimeState.FAILED}),
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

    def __init__(self, executor: CapabilityExecutor, *, store: RunStore | None = None,
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
        if run.cursor > len(workflow.steps) or run.step_attempts > (run.step_retry_limit or policy.max_step_attempts):
            raise ValueError("Runtime cursor/attempt bound invalid")
        if run.state == RuntimeState.PLANNED and (
            run.cursor != 0 or run.step_attempts != 0 or run.last_result is not None
        ):
            raise ValueError("Planned run cannot contain execution progress")
        if run.state == RuntimeState.SUCCEEDED and run.cursor < len(workflow.steps):
            if workflow.steps[run.cursor].kind != ActionKind.COMPLETE:
                raise ValueError("Successful run cannot skip pending steps")
        if run.state in {RuntimeState.RUNNING, RuntimeState.BLOCKED}:
            action = run.executing_action or (workflow.steps[run.cursor] if run.cursor < len(workflow.steps) else None)
            attempts = run.maintenance_attempts if action and action.kind == ActionKind.AUTO_MAINTENANCE else run.step_attempts
            if action is None or action.kind not in {ActionKind.CALL_CAPABILITY, ActionKind.AUTO_MAINTENANCE} or not attempts:
                raise ValueError("In-flight/blocked run must identify a capability step")
        if run.state == RuntimeState.WAITING_USER:
            dynamic = run.last_result is not None and run.last_result.recovery_class == RecoveryClass.USER_DECISION
            waiting = run.executing_action or policy.next_action(run, workflow)
            if run.cursor == len(workflow.steps) or (not dynamic and waiting.kind != ActionKind.REQUEST_USER_DECISION):
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
        if run.state == RuntimeState.WAITING_USER and run.last_result is not None and run.last_result.user_decision is not None:
            return RuntimeAction(kind=ActionKind.REQUEST_USER_DECISION, decision=run.last_result.user_decision)
        return policy.next_action(run, workflow)

    def _transition(self, run: RuntimeRun, state: RuntimeState, **changes: Any) -> RuntimeRun:
        if run.state != state:
            validate_transition(run.state, state)
        values = run.model_dump()
        values.update(changes, state=state, revision=run.revision + 1)
        following = RuntimeRun.model_validate(values)
        self._context(following)
        try:
            return self.store.save(following, expected_revision=run.revision)
        except ValueError as exc:
            if str(exc) != "Runtime revision conflict":
                raise
            current = self.store.load(run.run_id)
            self._context(current)
            if (current.scope != run.scope or current.workflow_fingerprint != run.workflow_fingerprint
                    or current.revision <= run.revision):
                raise
            # A stale writer never repeats a side effect or overwrites the winner.
            return current

    def _record_result(self, run: RuntimeRun, result: CapabilityResult) -> RuntimeRun:
        if result.status == ResultStatus.SUCCEEDED:
            _, workflow = self._context(run)
            maintenance = (run.executing_action is not None and run.executing_action.kind == ActionKind.AUTO_MAINTENANCE
                and run.executing_action != workflow.steps[run.cursor])
            return self._transition(run, RuntimeState.READY, cursor=run.cursor if maintenance else run.cursor + 1,
                step_attempts=run.step_attempts if maintenance else 0, wait_reason=None, last_result=result,
                execution_revision=run.execution_revision if maintenance else None, executing_action=None,
                step_retry_limit=run.step_retry_limit if maintenance else None,
                maintenance_attempts=None)
        if result.status == ResultStatus.WAITING_EXTERNAL:
            state = RuntimeState.WAITING_USER if result.recovery_class == RecoveryClass.USER_DECISION else RuntimeState.WAITING_EXTERNAL
            return self._transition(run, state, wait_reason="USER_DECISION_PENDING" if state == RuntimeState.WAITING_USER else "EXTERNAL_RESULT_PENDING", last_result=result)
        state = RuntimeState.BLOCKED if result.status == ResultStatus.RETRYABLE_FAILURE and (
            run.active_repair() is None or result.recovery_class == RecoveryClass.AUTO_RECOVER) else RuntimeState.FAILED
        return self._transition(run, state, last_result=result,
            step_retry_limit=run.step_retry_limit or result.retry_limit,
            wait_reason=result.code if state == RuntimeState.BLOCKED else None)

    def _retry_blocked(self, run: RuntimeRun) -> RuntimeRun:
        policy, workflow = self._context(run)
        action = run.executing_action or workflow.steps[run.cursor]
        key = action.capability_key
        assert key is not None
        if not self.executor.replay_safe(key):
            return self._transition(run, RuntimeState.FAILED, wait_reason=None,
                last_result=CapabilityResult(status=ResultStatus.FAILED,
                    code="REPLAY_UNSAFE", recovery_class=RecoveryClass.HARD_BLOCK))
        attempts = (run.maintenance_attempts or 0) if action.kind == ActionKind.AUTO_MAINTENANCE else run.step_attempts
        limit = run.step_retry_limit or policy.max_step_attempts
        recover_fixed = (run.last_result is not None and run.last_result.recovery_class == RecoveryClass.AUTO_RECOVER)
        if attempts >= limit or recover_fixed:
            if action.kind != ActionKind.AUTO_MAINTENANCE:
                try:
                    inspection = self._inspection(run, key)
                except Exception as error:
                    return self._transition(run, RuntimeState.FAILED, wait_reason=None,
                        last_result=CapabilityResult(status=ResultStatus.FAILED, code="EXECUTION_IDENTITY_UNAVAILABLE",
                            recovery_class=RecoveryClass.HARD_BLOCK, failure_stage="EXECUTION_INSPECTION",
                            exception_type=type(error).__name__))
                if (inspection is not None and inspection.completed and inspection.revision == run.execution_revision
                        and (run.maintenance_attempts or 0) < policy.max_step_attempts):
                    # A fixed owner output can finish its durable commit without
                    # another author/external invocation or refreshed call budget.
                    # Persist a separate finite local recovery count so repeated
                    # storage failures cannot obtain unbounded recovery attempts.
                    return self._transition(run, RuntimeState.READY, wait_reason=None,
                        maintenance_attempts=(run.maintenance_attempts or 0) + 1)
                if recover_fixed and inspection is not None and inspection.completed:
                    return self._transition(run, RuntimeState.FAILED, wait_reason=None,
                        last_result=CapabilityResult(status=ResultStatus.FAILED,
                            code="EXECUTION_REVISION_CHANGED" if inspection.revision != run.execution_revision else "RETRY_LIMIT_REACHED",
                            artifact_refs=run.last_result.artifact_refs if run.last_result else (),
                            recovery_class=RecoveryClass.HARD_BLOCK))
            if attempts < limit:
                return self._transition(run, RuntimeState.READY, wait_reason=None)
            return self._transition(run, RuntimeState.FAILED, wait_reason=None,
                last_result=CapabilityResult(status=ResultStatus.FAILED, code="RETRY_LIMIT_REACHED",
                    artifact_refs=run.last_result.artifact_refs if run.last_result else (),
                    recovery_class=RecoveryClass.HARD_BLOCK))
        return self._transition(run, RuntimeState.READY, wait_reason=None)

    def _recover_interrupted(self, run: RuntimeRun) -> RuntimeRun:
        _, workflow = self._context(run)
        action = run.executing_action or workflow.steps[run.cursor]
        assert action.capability_key is not None
        if self.executor.replay_safe(action.capability_key):
            # Owner-side reconciliation first resolves exact committed output/task.
            return self._transition(run, RuntimeState.READY, wait_reason=None, executing_action=action)
        return self._transition(run, RuntimeState.FAILED,
            last_result=CapabilityResult(status=ResultStatus.FAILED, code="INTERRUPTED_UNSAFE_CAPABILITY",
                recovery_class=RecoveryClass.HARD_BLOCK))

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
            if (run.step_attempts != (run.step_retry_limit or policy.max_step_attempts)
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

    async def resume_media_batch(self, run_id: str, *, batch_ref: ArtifactReference,
                                 decision_ref: ArtifactReference) -> RuntimeRun:
        """Re-enter only a completed Film media boundary for an owner-validated new batch."""
        from drama_plugin.runtime.contracts import ExecutionBatchResume
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            self._context(run)
            if any(record.batch_ref == batch_ref for record in run.execution_batches):
                return run
            if (run.workflow_id != 'source-to-reviewed-media:v1' or run.state != RuntimeState.SUCCEEDED
                    or run.cursor != 6 or run.last_result is None
                    or batch_ref.owner != 'film-media-batch' or decision_ref.owner != 'user-decision'):
                raise ValueError('COMPLETED_FILM_MEDIA_BATCH_REQUIRED')
            record = ExecutionBatchResume(batch_ref=batch_ref,decision_ref=decision_ref,
                completed_revision=run.revision,completed_cursor=run.cursor,completed_result=run.last_result)
            following = RuntimeRun.model_validate({**run.model_dump(), 'state':RuntimeState.READY,
                'cursor':5,'revision':run.revision+1,'last_result':None,'wait_reason':None,
                'step_attempts':0,'step_retry_limit':None,'maintenance_attempts':None,
                'execution_revision':None,'executing_action':None,
                'execution_batches':(*run.execution_batches,record)})
            self._context(following)
            return self.store.save(following,expected_revision=run.revision)

    async def repair_unknown_submission(self, run_id: str, *, expected_revision: int,
                                        capability_key: str, decision_ref: ArtifactReference) -> RuntimeRun:
        """Re-enter the exact UNKNOWN failure after owner-validated cost renewal."""
        return await self._repair_external_failure(run_id, expected_revision=expected_revision,
            capability_key=capability_key, decision_ref=decision_ref, code="PROVIDER_UNKNOWN_WITHOUT_LOOKUP")

    async def repair_resolved_reference_gate(self, run_id: str, *, expected_revision: int,
                                             decision_ref: ArtifactReference, current: ExecutionRevision) -> RuntimeRun:
        """Owner-verified preparation reference repair, once, retaining the hard-stop result."""
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            policy, workflow = self._context(run)
            key = workflow.steps[run.cursor].capability_key
            batch = run.execution_batches[-1].batch_ref if run.execution_batches else None
            prior=next((r for r in run.external_repairs if r.cursor==run.cursor
                and r.batch_ref==batch and r.failed_result.code=='GOVERNED_HARD_STOP' and r.capability_key==key),None)
            code=run.last_result.code if run.last_result else None
            inspection=self._inspection(run,key)
            correcting_revision=(code=='EXECUTION_REVISION_CHANGED' and prior is not None
                and (key=='film.execute:v1' or inspection is None and run.execution_revision==prior.current))
            if (run.state != RuntimeState.FAILED or run.last_result is None
                    or code != 'GOVERNED_HARD_STOP' and not correcting_revision
                    or run.revision != expected_revision or key not in {'generation.ready:v1','generation.release:v1','film.execute:v1'}
                    or not self.executor.replay_safe(key) or run.step_attempts >= (run.step_retry_limit or policy.max_step_attempts)
                    or any(r.cursor == run.cursor and r.failed_result.code == code and r.batch_ref==batch for r in run.external_repairs)
                    or run.execution_revision is not None and run.execution_revision.input_fingerprint != current.input_fingerprint):
                raise ValueError('EXACT_RESOLVED_REFERENCE_GATE_REQUIRED')
            record = ExternalRepairRecord(batch_ref=batch,cursor=run.cursor,capability_key=key,failed_revision=run.revision,
                failed_result=run.last_result,decision_ref=decision_ref,current=current)
            following = RuntimeRun.model_validate({**run.model_dump(),'state':RuntimeState.READY,'revision':run.revision+1,
                'wait_reason':None,'executing_action':None,
                'execution_revision':inspection.revision if inspection else None,
                'external_repairs':(*run.external_repairs,record)})
            action = policy.next_action(following,workflow)
            if action.kind != ActionKind.CALL_CAPABILITY or action.capability_key != key:
                raise ValueError('REFERENCE_GATE_STILL_UNRESOLVED')
            return self.store.save(following,expected_revision=run.revision)

    async def repair_media_intake_configuration(self, run_id: str, *, expected_revision: int,
                                                capability_key: str, decision_ref: ArtifactReference) -> RuntimeRun:
        """Re-enter a verified completed result after local import configuration repair."""
        failed = self.store.load(run_id).last_result
        if failed is None or failed.code not in {"EXTERNAL_RECONCILIATION_ERROR", "FORMAL_MEDIA_NOT_FOUND"}:
            raise ValueError("REPAIR_REQUIRES_EXACT_MEDIA_IMPORT_CONFIGURATION_FAILURE")
        return await self._repair_external_failure(run_id, expected_revision=expected_revision,
            capability_key=capability_key, decision_ref=decision_ref, code=failed.code)

    async def repair_video_duration_review(self, run_id: str, *, expected_revision: int,
                                            capability_key: str, decision_ref: ArtifactReference) -> RuntimeRun:
        return await self._repair_external_failure(run_id,expected_revision=expected_revision,
            capability_key=capability_key,decision_ref=decision_ref,code='TECHNICAL_MEDIA_FAILURE')

    async def repair_review_response(self, run_id: str, *, expected_revision: int,
                                    capability_key: str, decision_ref: ArtifactReference) -> RuntimeRun:
        return await self._repair_external_failure(run_id,expected_revision=expected_revision,
            capability_key=capability_key,decision_ref=decision_ref,code='HUMAN_REVIEW_CONTEXT_MISMATCH')

    async def repair_revision_dispatch(self, run_id: str, *, expected_revision: int,
                                       capability_key: str, decision_ref: ArtifactReference) -> RuntimeRun:
        failed=self.store.load(run_id).last_result
        if failed is None or failed.code not in {'FINANCIAL_AUTHORITY_ALREADY_CONSUMED','RECOVERY_TRANSPORT_READ_ONLY'}:
            raise ValueError('EXACT_UNSUBMITTED_REVISION_FAILURE_REQUIRED')
        return await self._repair_external_failure(run_id,expected_revision=expected_revision,
            capability_key=capability_key,decision_ref=decision_ref,code=failed.code,unsubmitted_local_repair=True)

    async def _repair_external_failure(self, run_id: str, *, expected_revision: int,
                                       capability_key: str, decision_ref: ArtifactReference, code: str,
                                       unsubmitted_local_repair: bool = False) -> RuntimeRun:
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            policy, workflow = self._context(run)
            if (run.state != RuntimeState.FAILED or run.last_result is None
                    or run.last_result.code != code):
                raise ValueError("REPAIR_REQUIRES_EXACT_EXTERNAL_FAILURE")
            if run.revision != expected_revision or workflow.steps[run.cursor].capability_key != capability_key:
                raise ValueError("REPAIR_FAILED_REVISION_OR_STEP_MISMATCH")
            if any(r.cursor == run.cursor and r.failed_result.code == code for r in run.external_repairs):
                raise ValueError("REPAIR_OPPORTUNITY_ALREADY_USED")
            limit=run.step_retry_limit or policy.max_step_attempts
            extra=(unsubmitted_local_repair and code in {'FINANCIAL_AUTHORITY_ALREADY_CONSUMED','RECOVERY_TRANSPORT_READ_ONLY'}
                and run.step_attempts>=limit and limit<=policy.max_step_attempts+1)
            if (not self.executor.replay_safe(capability_key) or run.step_attempts>=limit and not extra):
                raise ValueError("REPAIR_REPLAY_UNSAFE_OR_EXHAUSTED")
            inspection = self._inspection(run, capability_key)
            if (inspection is None or run.execution_revision is None
                    or inspection.revision.input_fingerprint != run.execution_revision.input_fingerprint):
                raise ValueError("REPAIR_AUTHORITY_INPUT_CHANGED")
            record = ExternalRepairRecord(cursor=run.cursor, capability_key=capability_key,
                failed_revision=run.revision, failed_result=run.last_result,
                decision_ref=decision_ref, current=inspection.revision)
            following = RuntimeRun.model_validate({**run.model_dump(), "state": RuntimeState.READY,
                "revision": run.revision + 1, "wait_reason": None, "executing_action": None,
                "execution_revision": inspection.revision, "external_repairs": (*run.external_repairs, record),
                "step_retry_limit":run.step_attempts+1 if extra else run.step_retry_limit,
                "last_result": CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(decision_ref,))})
            self._context(following)
            return self.store.save(following, expected_revision=run.revision)

    async def repair_inspection_failure(self, run_id: str, *, expected_revision: int,
                                        cursor: int, capability_key: str,
                                        input_fingerprint: str) -> RuntimeRun:
        """Explicit, single-use local repair; never reset attempts or general FAILED.

        The caller binds the reviewed failed checkpoint and fixed authority inputs.
        Successful inspection is required before the same capability can re-enter.
        Its failure result remains append-only in the existing Run owner.
        """
        async with self.store.lock(run_id):
            run=self.store.load(run_id)
            policy,workflow=self._context(run)
            if (run.state!=RuntimeState.FAILED or run.last_result is None
                    or run.last_result.status!=ResultStatus.FAILED
                    or run.last_result.code!="EXECUTION_IDENTITY_UNAVAILABLE"
                    or run.last_result.failure_stage!="EXECUTION_INSPECTION"
                    or run.last_result.recovery_class!=RecoveryClass.HARD_BLOCK):
                raise ValueError("REPAIR_REQUIRES_INSPECTION_FAILURE")
            if expected_revision!=run.revision:
                raise ValueError("REPAIR_FAILED_REVISION_MISMATCH")
            if (cursor!=run.cursor or cursor>=len(workflow.steps)
                    or workflow.steps[cursor].capability_key!=capability_key):
                raise ValueError("REPAIR_STEP_MISMATCH")
            batch_ref = run.execution_batches[-1].batch_ref if run.execution_batches else None
            if any(r.cursor==cursor and r.batch_ref==batch_ref for r in run.inspection_repairs) or run.active_repair() is not None:
                raise ValueError("REPAIR_OPPORTUNITY_ALREADY_USED")
            if not self.executor.replay_safe(capability_key):
                raise ValueError("REPAIR_REPLAY_UNSAFE")
            if run.step_attempts >= (run.step_retry_limit or policy.max_step_attempts):
                raise ValueError("REPAIR_REQUIRES_UNEXHAUSTED_ATTEMPTS")
            inspection=self._inspection(run,capability_key)
            if inspection is None:
                raise ValueError("REPAIR_INSPECTOR_REQUIRED")
            if (inspection.revision.input_fingerprint!=input_fingerprint
                    or run.execution_revision is not None
                    and run.execution_revision.input_fingerprint!=input_fingerprint):
                raise ValueError("REPAIR_AUTHORITY_INPUT_CHANGED")
            record=InspectionRepairRecord(cursor=cursor,capability_key=capability_key,batch_ref=batch_ref,
                failed_revision=run.revision,failed_result=run.last_result,
                previous_execution_revision=run.execution_revision,current=inspection.revision)
            following=RuntimeRun.model_validate({**run.model_dump(),"state":RuntimeState.READY,
                "revision":run.revision+1,"wait_reason":None,"executing_action":None,
                "execution_revision":inspection.revision,
                "inspection_repairs":(*run.inspection_repairs,record)})
            self._context(following)
            return self.store.save(following,expected_revision=run.revision)

    async def run(self, run_id: str, *, max_ticks: int = 64) -> RuntimeRun:
        for retry in range(3):
            try:
                return await self._run_locked(run_id, max_ticks=max_ticks)
            except TimeoutError:
                break  # Existing owner still holds this run; no new attempt.
            except sqlite3.OperationalError as error:
                if getattr(error,"sqlite_errorcode",None) not in {sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED}:
                    raise
                if retry < 2:
                    await asyncio.sleep(0.05 * (retry + 1))
        run = self.store.load(run_id)
        self._context(run)
        return run

    async def _run_locked(self, run_id: str, *, max_ticks: int = 64) -> RuntimeRun:
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
                if run.state in TERMINAL_STATES or run.state in {RuntimeState.WAITING_USER, RuntimeState.WAITING_EXTERNAL}:
                    return run
                if run.state == RuntimeState.BLOCKED:
                    if run.last_result is not None and run.last_result.status == ResultStatus.RETRYABLE_FAILURE:
                        self._retry_blocked(run)
                        continue
                    return run
                if run.state == RuntimeState.RUNNING:
                    self._recover_interrupted(run)
                    continue
                if run.state == RuntimeState.PLANNED:
                    self._transition(run, RuntimeState.READY)
                    continue
                action = run.executing_action or self.next_action(run_id)
                if action.kind == ActionKind.COMPLETE:
                    return self._transition(run, RuntimeState.SUCCEEDED)
                if action.kind == ActionKind.STOP:
                    return self._transition(run, RuntimeState.FAILED,
                        last_result=CapabilityResult(status=ResultStatus.FAILED, code=action.reason))
                if action.kind == ActionKind.REQUEST_USER_DECISION:
                    return self._transition(run, RuntimeState.WAITING_USER, wait_reason="USER_DECISION_PENDING",executing_action=action)
                if action.kind == ActionKind.WAIT_EXTERNAL:
                    return self._transition(run, RuntimeState.WAITING_EXTERNAL,
                        wait_reason="EXTERNAL_RESULT_PENDING", last_result=CapabilityResult(
                            status=ResultStatus.WAITING_EXTERNAL, external_ref=action.external_ref))
                assert action.capability_key is not None
                if isinstance(self.executor, CapabilityAvailability) and not self.executor.availability(action.capability_key):
                    return self._transition(run, RuntimeState.FAILED,
                        last_result=CapabilityResult(status=ResultStatus.FAILED, code="CAPABILITY_NOT_REGISTERED",
                            recovery_class=RecoveryClass.HARD_BLOCK))
                repair = run.active_repair()
                try:
                    inspection = self._inspection(run, action.capability_key)
                except Exception as error:
                    return self._transition(run, RuntimeState.FAILED,
                        last_result=CapabilityResult(status=ResultStatus.FAILED, code="EXECUTION_IDENTITY_UNAVAILABLE",
                            recovery_class=RecoveryClass.HARD_BLOCK, failure_stage="EXECUTION_INSPECTION",
                            exception_type=type(error).__name__))
                if repair is not None:
                    if inspection is None or inspection.revision != repair.current:
                        return self._transition(run, RuntimeState.FAILED,
                            last_result=CapabilityResult(status=ResultStatus.FAILED, code="REPAIR_EXECUTION_DENIED"))
                    if repair.attempts >= repair.limit:
                        if not inspection.completed:
                            return self._transition(run, RuntimeState.FAILED,
                                last_result=CapabilityResult(status=ResultStatus.FAILED, code="RETRY_LIMIT_REACHED",
                                    recovery_class=RecoveryClass.HARD_BLOCK))
                        executing = self._transition(run, RuntimeState.RUNNING, executing_action=action)
                    else:
                        if inspection.completed:
                            return self._transition(run, RuntimeState.FAILED,
                                last_result=CapabilityResult(status=ResultStatus.FAILED, code="REPAIR_EXECUTION_DENIED"))
                        consumed = RepairResumeRecord.model_validate({**repair.model_dump(), "attempts": 1})
                        executing = self._transition(run, RuntimeState.RUNNING,
                            repair_resumes=tuple(consumed if r.cursor == run.cursor else r for r in run.repair_resumes),
                            executing_action=action)
                else:
                    maintenance = action.kind == ActionKind.AUTO_MAINTENANCE
                    attempts = (run.maintenance_attempts or 0) if maintenance else run.step_attempts
                    completed = inspection is not None and inspection.completed
                    limit = run.step_retry_limit or self._policies[run.mode].max_step_attempts
                    if not maintenance and inspection is not None and inspection.retry_limit is not None:
                        # A historical execution keeps its prior policy bound even
                        # when it predates explicit limit capture. New executions
                        # pin the capability bound before calling the owner.
                        limit = run.step_retry_limit or (inspection.retry_limit if run.step_attempts == 0 else limit)
                    if attempts >= limit and not completed:
                        return self._transition(run, RuntimeState.FAILED,
                            last_result=CapabilityResult(status=ResultStatus.FAILED, code="RETRY_LIMIT_REACHED",
                                artifact_refs=run.last_result.artifact_refs if run.last_result else (),
                                recovery_class=RecoveryClass.HARD_BLOCK))
                    revision = inspection.revision if inspection is not None else None
                    if not maintenance and run.execution_revision is not None and run.execution_revision != revision:
                        return self._transition(run, RuntimeState.FAILED,
                            last_result=CapabilityResult(status=ResultStatus.FAILED, code="EXECUTION_REVISION_CHANGED",
                                recovery_class=RecoveryClass.HARD_BLOCK))
                    executing = self._transition(run, RuntimeState.RUNNING,
                        step_attempts=run.step_attempts if maintenance or (completed and run.step_attempts > 0) else run.step_attempts + 1,
                        step_retry_limit=limit if not maintenance and inspection is not None and inspection.retry_limit is not None else run.step_retry_limit,
                        maintenance_attempts=(attempts + 1) if maintenance else run.maintenance_attempts,
                        execution_revision=run.execution_revision if maintenance else revision,
                        executing_action=action)
                inputs = CapabilityInput(run_id=run.run_id, operation_id=f"{run.run_id}:{run.cursor}",
                    scope=run.scope, input_refs=(run.last_result.artifact_refs
                        if action.input_from_previous and run.last_result is not None else action.input_refs))
                try:
                    result = CapabilityResult.model_validate(await self.executor.execute(action.capability_key, inputs))
                except Exception as error:
                    # Class/stage are controlled metadata; exception text can contain secrets.
                    result = CapabilityResult(status=ResultStatus.FAILED, code="CAPABILITY_EXECUTION_ERROR",
                        recovery_class=RecoveryClass.HARD_BLOCK, failure_stage="CAPABILITY_EXECUTION",
                        exception_type=type(error).__name__)
                self._record_result(executing, result)
            return self.store.load(run_id)

    async def reconcile_wait(self, run_id: str) -> RuntimeRun:
        """Re-enter the recorded owner for the same external identity, never retry an author."""
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            _, workflow = self._context(run)
            if run.state not in {RuntimeState.WAITING_EXTERNAL,RuntimeState.WAITING_USER}:
                return run
            if run.last_result is None or run.last_result.external_ref is None:
                return run  # Static user decision belongs to its existing decision consumer.
            action = run.executing_action or workflow.steps[run.cursor]
            if action.capability_key is None:
                return run
            if not self.executor.replay_safe(action.capability_key):
                raise ValueError("External owner reconciliation is not declared safe")
            inputs = CapabilityInput(run_id=run_id,operation_id=f"{run_id}:{run.cursor}",scope=run.scope,
                input_refs=action.input_refs)
            try:
                result = CapabilityResult.model_validate(await self.executor.execute(action.capability_key,inputs))
            except Exception as error:
                result = CapabilityResult(status=ResultStatus.FAILED,code="EXTERNAL_RECONCILIATION_ERROR",
                    recovery_class=RecoveryClass.HARD_BLOCK, failure_stage="EXTERNAL_RECONCILIATION",
                    exception_type=type(error).__name__)
            return self._record_result(run,result)

    async def resume_unsubmitted_segment_revision(self, run_id: str, *, expected_revision: int,
            previous_child_id: str, revision_ref: ArtifactReference, decision_ref: ArtifactReference,
            current: ExecutionRevision) -> RuntimeRun:
        """An owner has validated a new scoped input after a pre-payment planning failure."""
        async with self.store.lock(run_id):
            run=self.store.load(run_id);_,workflow=self._context(run)
            if (run.state!=RuntimeState.FAILED or run.revision!=expected_revision or run.workflow_id!='source-to-reviewed-media:v1'
                    or run.cursor!=5 or not run.last_result or run.last_result.code!='GOVERNED_HARD_STOP'
                    or not any(r.owner=='runtime' and r.artifact_ref==previous_child_id for r in run.last_result.artifact_refs)
                    or revision_ref.owner!='film-segment-revision' or decision_ref.owner!='user-decision'
                    or any(r.revision_ref==revision_ref for r in run.external_repairs)
                    or run.execution_revision and run.execution_revision.input_fingerprint!=current.input_fingerprint):
                raise ValueError('EXACT_UNSUBMITTED_SEGMENT_REVISION_REQUIRED')
            record=ExternalRepairRecord(batch_ref=run.execution_batches[-1].batch_ref if run.execution_batches else None,
                revision_ref=revision_ref,cursor=run.cursor,capability_key='film.execute:v1',failed_revision=run.revision,
                failed_result=run.last_result,decision_ref=decision_ref,current=current)
            following=RuntimeRun.model_validate({**run.model_dump(),'state':RuntimeState.READY,'revision':run.revision+1,
                'executing_action':None,'wait_reason':None,'external_repairs':(*run.external_repairs,record)})
            if workflow.steps[following.cursor].capability_key!='film.execute:v1':
                raise ValueError('EXACT_UNSUBMITTED_SEGMENT_REVISION_REQUIRED')
            return self.store.save(following,expected_revision=run.revision)

    def serialize(self, run_id: str) -> str:
        run = self.store.load(run_id)
        self._context(run)
        return run.model_dump_json(by_alias=True)

    def restore(self, snapshot: str) -> RuntimeRun:
        run = RuntimeRun.model_validate_json(snapshot)
        self._context(run)
        self.store.create(run)
        if run.state == RuntimeState.RUNNING:
            return self._recover_interrupted(run)
        return run

    async def recover_run(self, run_id: str) -> RuntimeRun:
        """Open the same durable checkpoint after restart, without recreating it."""
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            self._context(run)
            if run.state == RuntimeState.RUNNING:
                return self._recover_interrupted(run)
            return run

    async def retry(self, run_id: str, *, approved_author_attempt_limit: int | None = None) -> RuntimeRun:
        """Internal retry routing, never an artificial user approval of bookkeeping."""
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            self._context(run)
            if approved_author_attempt_limit is not None:
                return await self._retry_with_approved_author_limit(run, approved_author_attempt_limit)
            if run.state != RuntimeState.BLOCKED:
                raise ValueError("Only a blocked capability can be retried")
            return self._retry_blocked(run)

    async def _retry_with_approved_author_limit(self, run: RuntimeRun, limit: int) -> RuntimeRun:
        """Explicit policy adjustment preserves attempts and exact authority inputs.

        A changed default never reopens history. The caller must supply the newly
        approved total; the capability's current inspection must advertise it.
        Failed parents only reconcile their exact, explicitly linked child.
        """
        _, workflow = self._context(run)
        action = run.executing_action
        if (isinstance(limit, bool) or not 1 <= limit <= 8 or action is None
                or action.kind != ActionKind.CALL_CAPABILITY or action.capability_key is None
                or run.cursor >= len(workflow.steps) or action != workflow.steps[run.cursor]
                or run.active_repair() is not None or not self.executor.replay_safe(action.capability_key)):
            raise ValueError("AUTHOR_BUDGET_ADJUSTMENT_UNSUPPORTED")
        inspection = self._inspection(run, action.capability_key)
        if (run.state == RuntimeState.READY and inspection is not None and not inspection.completed
                and inspection.revision == run.execution_revision and inspection.retry_limit == limit
                and run.step_retry_limit == limit and run.step_attempts < limit):
            # Crash between a child budget commit and parent reconciliation:
            # recover the existing allowance, never allocate another one.
            return run
        if (run.state != RuntimeState.FAILED or run.last_result is None
                or run.last_result.status != ResultStatus.FAILED
                or run.last_result.code != "RETRY_LIMIT_REACHED"):
            raise ValueError("AUTHOR_BUDGET_REQUIRES_EXHAUSTED_FAILURE")
        children = tuple(ref for ref in run.last_result.artifact_refs if ref.owner == "runtime")
        if children:
            if len(children) != 1 or not children[0].artifact_ref.startswith(run.run_id + ":"):
                raise ValueError("AUTHOR_BUDGET_CHILD_IDENTITY_MISMATCH")
            child = self.store.load(children[0].artifact_ref)
            if (child.scope.work_id != run.scope.work_id
                    or run.scope.scene_id is not None and child.scope.scene_id != run.scope.scene_id
                    or run.scope.shot_id is not None and child.scope.shot_id != run.scope.shot_id):
                raise ValueError("AUTHOR_BUDGET_CHILD_SCOPE_MISMATCH")
            await self.retry(child.run_id, approved_author_attempt_limit=limit)
            following = RuntimeRun.model_validate({**run.model_dump(), "state": RuntimeState.READY,
                "revision": run.revision + 1, "wait_reason": None})
        else:
            if (inspection is None or inspection.completed or inspection.retry_limit != limit
                    or run.execution_revision is None or inspection.revision != run.execution_revision
                    or run.step_retry_limit is None or run.step_attempts != run.step_retry_limit
                    or limit <= run.step_retry_limit):
                raise ValueError("AUTHOR_BUDGET_REVISION_OR_LIMIT_MISMATCH")
            following = RuntimeRun.model_validate({**run.model_dump(), "state": RuntimeState.READY,
                "revision": run.revision + 1, "wait_reason": None, "step_retry_limit": limit})
        self._context(following)
        # FAILED's general transition table and ordinary retry remain closed.
        return self.store.save(following, expected_revision=run.revision)

    def decision_id(self, run_id: str) -> str:
        run = self.store.load(run_id)
        if run.state != RuntimeState.WAITING_USER:
            raise ValueError("Run is not waiting for a user decision")
        return f"{run.run_id}:{run.cursor}"

    async def decide(self, run_id: str, *, decision_id: str, accepted: bool,
                     decision_ref: ArtifactReference, resume_same_step: bool = False) -> RuntimeRun:
        if not isinstance(accepted, bool):
            raise ValueError("User decision must be an explicit boolean")
        async with self.store.lock(run_id):
            run = self.store.load(run_id)
            self._context(run)
            if decision_id != self.decision_id(run_id):
                raise ValueError("Decision belongs to another step")
            if accepted:
                dynamic = resume_same_step or (run.last_result is not None and run.last_result.recovery_class == RecoveryClass.USER_DECISION)
                return self._transition(run, RuntimeState.READY, cursor=run.cursor if dynamic else run.cursor + 1,
                    step_attempts=0 if dynamic else run.step_attempts, executing_action=None,
                    step_retry_limit=None if dynamic else run.step_retry_limit,
                    execution_revision=None if dynamic else run.execution_revision,
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
            if (run.state not in {RuntimeState.WAITING_EXTERNAL, RuntimeState.WAITING_USER} or run.last_result is None
                    or (run.state == RuntimeState.WAITING_USER and run.last_result.recovery_class != RecoveryClass.USER_DECISION)):
                raise ValueError("Run is not waiting for an external result")
            if run.last_result.external_ref != external_ref:
                raise ValueError("External result belongs to another dependency")
            result = CapabilityResult.model_validate(result)
            if result.status == ResultStatus.WAITING_EXTERNAL and result.recovery_class is None:
                raise ValueError("External result must resolve this wait")
            if result.status == ResultStatus.RETRYABLE_FAILURE and result.recovery_class is None:
                raise ValueError("Transient external failure leaves the dependency wait unresolved")
            return self._record_result(run, result)
