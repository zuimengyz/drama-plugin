"""Failure abstraction preserves safe classification while hiding all arbitrary text."""
import json

import pytest
from drama_plugin.runtime.contracts import ArtifactReference, CapabilityResult, RecoveryClass, ResultStatus, RuntimeState
from drama_plugin.runtime.bridge import CapabilityAvailability, LegacyCapability, LegacyCapabilityBridge
from drama_plugin.runtime.capabilities import TargetCapabilityRouter
from drama_plugin.runtime.engine import RuntimeEngine
from test_unified_runtime_recovery import engine, create

PRIVATE = 'credential=SECRET hidden reasoning source body https://signed.invalid/?token=SECRET'


async def test_unexpected_capability_bug_is_one_call_hard_with_safe_stage_and_type(tmp_path):
    calls = []
    async def broken(inputs):
        calls.append(inputs.operation_id)
        raise RuntimeError(PRIVATE)
    runtime = engine(tmp_path, broken)
    run = create(runtime)
    failed = await runtime.run(run.run_id)
    assert failed.state == RuntimeState.FAILED
    assert failed.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    assert failed.last_result.failure_stage == 'CAPABILITY_EXECUTION'
    assert failed.last_result.exception_type == 'RuntimeError' and len(calls) == 1
    assert 'SECRET' not in runtime.serialize(run.run_id) and PRIVATE not in runtime.serialize(run.run_id)
    assert (await runtime.run(run.run_id)) == failed and len(calls) == 1


async def test_inspection_bug_never_dispatches_or_exposes_exception_text(tmp_path):
    calls = []
    async def handler(inputs):
        calls.append(inputs.operation_id)
        return CapabilityResult(status=ResultStatus.SUCCEEDED)
    def inspect(inputs):
        raise ValueError(PRIVATE)
    runtime = engine(tmp_path, handler, inspection=inspect)
    failed = await runtime.run(create(runtime).run_id)
    assert failed.state == RuntimeState.FAILED and failed.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    assert failed.last_result.failure_stage == 'EXECUTION_INSPECTION' and failed.last_result.exception_type == 'ValueError'
    assert calls == [] and 'SECRET' not in runtime.serialize(failed.run_id)


async def test_external_owner_unexpected_bug_preserves_exact_wait_identity_and_safe_diagnostic(tmp_path):
    calls = []
    task = ArtifactReference(owner='external-task', artifact_ref='stable-task')
    async def query(inputs):
        calls.append(inputs.operation_id)
        if len(calls) == 1:
            return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, external_ref=task,
                recovery_class=RecoveryClass.WAIT_EXTERNAL)
        raise RuntimeError(PRIVATE)
    runtime = engine(tmp_path, query)
    run = create(runtime)
    waiting = await runtime.run(run.run_id)
    assert waiting.state == RuntimeState.WAITING_EXTERNAL and waiting.last_result.external_ref == task
    failed = await runtime.reconcile_wait(run.run_id)
    assert failed.state == RuntimeState.FAILED and failed.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    assert failed.last_result.failure_stage == 'EXTERNAL_RECONCILIATION' and failed.last_result.exception_type == 'RuntimeError'
    assert calls == ['same-run:0', 'same-run:0'] and 'SECRET' not in runtime.serialize(run.run_id)


def test_historical_results_do_not_gain_empty_failure_metadata():
    historical = {'status': 'FAILED', 'artifactRefs': [], 'code': 'OLD_CODE', 'externalRef': None}
    assert json.loads(CapabilityResult.model_validate(historical).model_dump_json(by_alias=True)) == historical


async def test_missing_registry_capability_is_hard_before_inspection_or_attempt(tmp_path):
    from test_unified_runtime_recovery import FLOW
    from drama_plugin.persistence.ledger import ProductionLedger
    from drama_plugin.persistence.stores import DurableRunStore
    class Absent(LegacyCapabilityBridge):
        def inspect_execution(self, key, inputs):
            raise AssertionError('absence must precede inspection')
        async def execute(self, key, inputs):
            raise AssertionError('absence must never dispatch')
    executor = Absent({})
    assert isinstance(executor, CapabilityAvailability)
    store = DurableRunStore(ProductionLedger(tmp_path / 'absent.sqlite'))
    runtime = RuntimeEngine(executor, workflows={FLOW.workflow_id: FLOW}, store=store)
    failed = await runtime.run(create(runtime).run_id)
    assert failed.state == RuntimeState.FAILED and failed.cursor == 0 and failed.step_attempts == 0
    assert failed.execution_revision is None and failed.executing_action is None
    assert failed.last_result.code == 'CAPABILITY_NOT_REGISTERED'
    assert failed.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    with store.ledger.transaction() as db:
        assert db.execute('SELECT COUNT(*) FROM production_operation').fetchone()[0] == 0


async def test_target_availability_cannot_open_registered_legacy_provider_route(tmp_path):
    from test_unified_runtime_recovery import FLOW, KEY
    calls = []
    async def legacy(inputs):
        calls.append(inputs.operation_id)
        return CapabilityResult(status=ResultStatus.SUCCEEDED)
    bridge = LegacyCapabilityBridge({KEY: LegacyCapability(legacy, True),
        'work.get_work': LegacyCapability(legacy, True)})
    router = TargetCapabilityRouter({}, bridge)
    assert not router.availability(KEY) and router.availability('work.get_work')
    runtime = RuntimeEngine(router, workflows={FLOW.workflow_id: FLOW})
    run = create(runtime)
    failed = await runtime.run(run.run_id)
    assert failed.step_attempts == 0 and failed.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    from drama_plugin.runtime.contracts import CapabilityInput
    result = await router.execute(KEY, CapabilityInput(run_id=run.run_id,
        operation_id=run.run_id + ':0', scope=run.scope))
    assert result.code == 'LEGACY_GUARD' and calls == []
    assert not TargetCapabilityRouter({}, LegacyCapabilityBridge({})).availability('work.get_work')


@pytest.mark.parametrize('permanent', (False, True))
async def test_repair_fixed_output_local_recovery_never_gets_second_repair_author_call(tmp_path, permanent):
    from test_runtime_repair_resume import exhausted, engine as repair_engine, KEY
    from drama_plugin.contracts.base import sha256_canonical
    owner, runtime, ledger, run, proof = await exhausted(tmp_path / 'repair-commit.sqlite')
    owner.fingerprint = sha256_canonical('repaired-author-contract')
    async def commit(inputs):
        if not owner.completed:
            owner.calls += 1
            owner.completed = True
            return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code='OWNER_COMMIT_INTERRUPTED',
                recovery_class=RecoveryClass.AUTO_RECOVER)
        if permanent:
            return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code='OWNER_COMMIT_INTERRUPTED',
                recovery_class=RecoveryClass.AUTO_RECOVER)
        return CapabilityResult(status=ResultStatus.SUCCEEDED)
    owner.execute = commit
    await runtime.repair_resume(run.run_id, cursor=0, capability_key=KEY, exhausted=proof)
    fresh, _ = repair_engine(ledger.path, owner)
    blocked = await fresh.run(run.run_id, max_ticks=1)
    assert blocked.state == RuntimeState.BLOCKED and blocked.repair_resumes[0].attempts == 1
    assert blocked.step_attempts == 2 and owner.calls == 3
    with ledger.transaction() as db:
        historical = dict(db.execute('SELECT attempt_identity,result_identity FROM production_operation').fetchall())
    assert len(historical) == 3 and all(historical.values())
    restored, _ = repair_engine(ledger.path, owner)
    done = await restored.run(run.run_id)
    assert done.repair_resumes[0].attempts == 1 and done.repair_resumes[0].limit == 1 and owner.calls == 3
    assert done.state == (RuntimeState.FAILED if permanent else RuntimeState.SUCCEEDED)
    if permanent:
        assert done.last_result.code == 'RETRY_LIMIT_REACHED' and done.maintenance_attempts == 2
    with ledger.transaction() as db:
        following = dict(db.execute('SELECT attempt_identity,result_identity FROM production_operation').fetchall())
    assert all(following[attempt] == result for attempt, result in historical.items())
    assert len(following) == 3 + (2 if permanent else 1)
    assert all(':recovery:repair:' in attempt for attempt in following.keys() - historical.keys())
    assert await restored.run(run.run_id) == done and owner.calls == 3
