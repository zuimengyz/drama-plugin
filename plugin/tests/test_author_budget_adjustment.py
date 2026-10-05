"""Explicit larger author total preserves durable attempts, inputs and history."""
import pytest

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.runtime.capabilities import TargetCapability, TargetCapabilityRouter
from drama_plugin.runtime.contracts import (ActionKind, ArtifactReference, CapabilityResult,
    ResultStatus, RunMode, RuntimeAction, RuntimeState, RuntimeWorkflow)
from drama_plugin.runtime.engine import RuntimeEngine, validate_transition
from drama_plugin.persistence.stores import DurableRunStore
from test_professional_collect_all import BoundedAuthor
from test_runtime_repair_resume import engine, rows, KEY


async def failed_author(tmp_path):
    owner = BoundedAuthor()
    runtime, ledger = engine(tmp_path / 'ledger.sqlite', owner)
    run = runtime.create_run(work_id='new-work', mode=RunMode.PRODUCTION,
        workflow_id=next(iter(runtime._workflows)))
    run = await runtime.run(run.run_id)
    assert run.step_attempts == run.step_retry_limit == 3 and owner.calls == 3
    return owner, runtime, ledger, run


async def test_new_default_alone_does_not_reopen_old_execution(tmp_path):
    owner, runtime, ledger, run = await failed_author(tmp_path)
    owner.limit = 5
    fresh, _ = engine(ledger.path, owner)
    assert await fresh.run(run.run_id) == run
    with pytest.raises(ValueError, match='Only a blocked'):
        await fresh.retry(run.run_id)
    assert owner.calls == 3


async def test_approved_total_adds_only_two_calls_and_survives_restart(tmp_path):
    owner, runtime, ledger, run = await failed_author(tmp_path)
    before = rows(ledger)
    owner.limit = 5
    ready = await runtime.retry(run.run_id, approved_author_attempt_limit=5)
    assert ready.state == RuntimeState.READY
    assert ready.step_attempts == 3 and ready.step_retry_limit == 5
    assert ready.execution_revision == run.execution_revision and rows(ledger) == before
    fresh, _ = engine(ledger.path, owner)
    assert await fresh.retry(run.run_id, approved_author_attempt_limit=5) == ready
    done = await fresh.run(run.run_id)
    assert done.state == RuntimeState.FAILED and done.step_attempts == done.step_retry_limit == 5
    assert owner.calls == 5 and rows(ledger)[:len(before)] == before
    with pytest.raises(ValueError, match='REVISION_OR_LIMIT'):
        await fresh.retry(run.run_id, approved_author_attempt_limit=5)
    assert owner.calls == 5
    with pytest.raises(ValueError):
        validate_transition(RuntimeState.FAILED, RuntimeState.READY)


@pytest.mark.parametrize('change', ('inputs', 'contract', 'completed', 'wrong_limit', 'hard_failure', 'no_bound'))
async def test_budget_adjustment_cannot_change_authority_or_bypass_other_failure(tmp_path, change):
    owner, runtime, ledger, run = await failed_author(tmp_path)
    owner.limit = 5
    if change == 'inputs': owner.inputs = sha256_canonical('different-source')
    if change == 'contract': owner.fingerprint = sha256_canonical('different-contract')
    if change == 'completed': owner.completed = True
    if change == 'wrong_limit': owner.limit = 6
    if change == 'no_bound': owner.limit = None
    if change == 'hard_failure':
        run = runtime.store.save(run.model_copy(update={'revision': run.revision + 1,
            'last_result': CapabilityResult(status=ResultStatus.FAILED, code='SOURCE_CORRUPT')}),
            expected_revision=run.revision)
    before = rows(ledger)
    with pytest.raises(ValueError):
        await runtime.retry(run.run_id, approved_author_attempt_limit=5)
    assert runtime.store.load(run.run_id) == run and rows(ledger) == before and owner.calls == 3


async def test_parent_reconciles_exact_failed_child_without_resetting_calls(tmp_path):
    owner = BoundedAuthor()
    runtime, ledger = engine(tmp_path / 'ledger.sqlite', owner)
    child_flow = next(iter(runtime._workflows.values()))
    parent_flow = RuntimeWorkflow(workflow_id='parent:v1', steps=(RuntimeAction(
        kind=ActionKind.CALL_CAPABILITY, capability_key='parent.prepare:v1'),))
    child_id = 'parent:child'
    async def prepare(inputs):
        try:
            runtime.store.load(child_id)
        except KeyError:
            runtime.create_run(work_id=inputs.scope.work_id, mode=RunMode.PRODUCTION,
                workflow_id=child_flow.workflow_id, run_id=child_id)
        child = await runtime.run(child_id)
        if child.state == RuntimeState.SUCCEEDED:
            return CapabilityResult(status=ResultStatus.SUCCEEDED)
        return child.last_result.model_copy(update={'artifact_refs': (
            ArtifactReference(owner='runtime', artifact_ref=child_id),)})
    router = TargetCapabilityRouter({KEY: TargetCapability(owner.execute, True, owner.inspect),
        'parent.prepare:v1': TargetCapability(prepare, True)})
    runtime = RuntimeEngine(router, store=DurableRunStore(ledger),
        workflows={child_flow.workflow_id: child_flow, parent_flow.workflow_id: parent_flow})
    parent = runtime.create_run(work_id='new-work', mode=RunMode.PRODUCTION,
        workflow_id=parent_flow.workflow_id, run_id='parent')
    parent = await runtime.run(parent.run_id)
    assert parent.state == RuntimeState.FAILED and owner.calls == 3
    before = rows(ledger)
    owner.limit = 5
    await runtime.retry(parent.run_id, approved_author_attempt_limit=5)
    assert runtime.store.load(child_id).step_attempts == 3 and rows(ledger) == before
    owner.status = ResultStatus.SUCCEEDED
    parent = await runtime.run(parent.run_id)
    assert parent.state == RuntimeState.SUCCEEDED and owner.calls == 4
