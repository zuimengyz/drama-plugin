"""Durable same-step recovery, exact dynamic actions and genuine human waits."""
from __future__ import annotations
import asyncio
import json
import subprocess
import sys

import pytest
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.persistence.ledger import ProductionLedger
from drama_plugin.persistence.stores import DurableRunStore
from drama_plugin.runtime.capabilities import TargetCapability, TargetCapabilityRouter
from drama_plugin.runtime.contracts import (ActionKind, ArtifactReference, CapabilityInput,
    CapabilityResult, DecisionCategory, ExecutionInspection, ExecutionRevision, RecoveryClass,
    ResultStatus, RunMode, RuntimeAction, RuntimeState, RuntimeWorkflow, UserDecisionRequest)
from drama_plugin.runtime.engine import RuntimeEngine
from drama_plugin.runtime.policy import FoundationPolicy

KEY='test.author'
FLOW=RuntimeWorkflow(workflow_id='unified-runtime:v1',steps=(RuntimeAction(kind=ActionKind.CALL_CAPABILITY,capability_key=KEY),))
REV=ExecutionRevision(fingerprint=sha256_canonical('contract'),input_fingerprint=sha256_canonical('exact authority'))

def engine(tmp_path, handler, *, inspection=None, store=None, policy=None, native=None):
    registrations=native or {KEY:TargetCapability(handler,True,inspection)}
    return RuntimeEngine(TargetCapabilityRouter(registrations),store=store or DurableRunStore(ProductionLedger(tmp_path/'ledger.sqlite')),
        workflows={FLOW.workflow_id:FLOW},policies={m:policy if policy and policy.mode==m else FoundationPolicy(m) for m in RunMode})

def create(runtime):
    return runtime.create_run(work_id='work',mode=RunMode.PRODUCTION,workflow_id=FLOW.workflow_id,run_id='same-run')

@pytest.mark.asyncio
async def test_retry_same_revision_automatic_with_append_only_history(tmp_path):
    calls=[]
    async def author(inputs):
        calls.append(inputs.operation_id)
        return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE,code='JSON_PARSE',recovery_class=RecoveryClass.RETRY_SAME_STEP) if len(calls)==1 else CapabilityResult(status=ResultStatus.SUCCEEDED)
    r=engine(tmp_path,author,inspection=lambda _:ExecutionInspection(revision=REV,completed=False));run=create(r)
    assert (await r.run(run.run_id)).state==RuntimeState.SUCCEEDED
    assert calls==['same-run:0','same-run:0']
    with r.store.ledger.transaction() as db:
        rows=db.execute('SELECT attempt_identity,result_identity FROM production_operation').fetchall()
    assert [row[0] for row in rows]==['same-run:0:1','same-run:0:2']
    assert all(row[1] for row in rows)

@pytest.mark.asyncio
async def test_process_restart_keeps_attempt_budget_and_execution_revision(tmp_path):
    async def fail(inputs):
        return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE,code='SCHEMA_FIELD',recovery_class=RecoveryClass.RETRY_SAME_STEP)
    inspection=lambda _:ExecutionInspection(revision=REV,completed=False)
    r=engine(tmp_path,fail,inspection=inspection);run=create(r)
    first=await r.run(run.run_id,max_ticks=2)
    assert first.state==RuntimeState.BLOCKED and first.step_attempts==1
    program='''
import sys
from drama_plugin.persistence.ledger import ProductionLedger
r=ProductionLedger(sys.argv[1]).load_run('same-run')
assert r.step_attempts==1 and r.execution_revision.fingerprint==sys.argv[2]
'''
    assert subprocess.run([sys.executable,'-c',program,str(tmp_path/'ledger.sqlite'),REV.fingerprint]).returncode==0
    fresh=engine(tmp_path,fail,inspection=inspection)
    result=await fresh.run(run.run_id)
    assert result.state==RuntimeState.FAILED and result.step_attempts==2
    assert result.last_result.code=='RETRY_LIMIT_REACHED'
    assert (await fresh.run(run.run_id))==result

@pytest.mark.asyncio
async def test_committed_owner_output_before_checkpoint_reconciles_without_author(tmp_path):
    fixed=False;calls=[]
    async def author(inputs):
        nonlocal fixed
        if fixed:return CapabilityResult(status=ResultStatus.SUCCEEDED)
        calls.append(inputs.operation_id);fixed=True
        raise asyncio.CancelledError()
    inspection=lambda _:ExecutionInspection(revision=REV,completed=fixed)
    r=engine(tmp_path,author,inspection=inspection);run=create(r)
    with pytest.raises(asyncio.CancelledError):await r.run(run.run_id)
    fresh=engine(tmp_path,author,inspection=inspection)
    assert (await fresh.recover_run(run.run_id)).state==RuntimeState.READY
    assert (await fresh.run(run.run_id)).state==RuntimeState.SUCCEEDED and len(calls)==1
    with fresh.store.ledger.transaction() as db:
        assert db.execute('SELECT COUNT(*) FROM production_operation').fetchone()[0]==1

@pytest.mark.asyncio
async def test_cas_stale_writer_reload_does_not_repeat_success(tmp_path):
    calls=[]
    async def success(inputs):calls.append(inputs.operation_id);return CapabilityResult(status=ResultStatus.SUCCEEDED)
    r=engine(tmp_path,success);run=create(r);original=r.store.save;conflicted=False
    def save(following,*,expected_revision):
        nonlocal conflicted
        result=original(following,expected_revision=expected_revision)
        if following.state==RuntimeState.READY and following.cursor==1 and not conflicted:
            conflicted=True;raise ValueError('Runtime revision conflict')
        return result
    r.store.save=save
    assert (await r.run(run.run_id)).state==RuntimeState.SUCCEEDED and len(calls)==1

@pytest.mark.asyncio
async def test_media_read_uses_durable_owner_budget_three(tmp_path):
    calls=[]
    async def read(inputs):
        calls.append(inputs.operation_id)
        return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE,code='MEDIA_DOWNLOAD_TRANSIENT',
            recovery_class=RecoveryClass.RETRY_SAME_STEP,retry_limit=3) if len(calls)<3 else CapabilityResult(status=ResultStatus.SUCCEEDED)
    r=engine(tmp_path,read);run=create(r)
    assert (await r.run(run.run_id)).state==RuntimeState.SUCCEEDED and len(calls)==3

@pytest.mark.asyncio
async def test_dynamic_maintenance_recovers_then_runs_actual_business_step(tmp_path):
    repaired=False;calls=[]
    class Policy(FoundationPolicy):
        def next_action(self,run,workflow):
            if not repaired and run.state==RuntimeState.READY:
                return RuntimeAction(kind=ActionKind.AUTO_MAINTENANCE,capability_key='test.reindex')
            return super().next_action(run,workflow)
    async def reindex(inputs):
        nonlocal repaired
        calls.append('reindex');repaired=True
        return CapabilityResult(status=ResultStatus.SUCCEEDED,recovery_class=RecoveryClass.AUTO_RECOVER)
    async def business(inputs):calls.append('compile');return CapabilityResult(status=ResultStatus.SUCCEEDED)
    r=engine(tmp_path,business,policy=Policy(RunMode.PRODUCTION),native={KEY:TargetCapability(business,True),'test.reindex':TargetCapability(reindex,True)})
    run=create(r)
    assert (await r.run(run.run_id)).state==RuntimeState.SUCCEEDED
    assert calls==['reindex','compile']

@pytest.mark.asyncio
async def test_dynamic_human_review_is_user_wait_exact_external_receipt(tmp_path):
    ref=ArtifactReference(owner='human-review-context',artifact_ref='exact-media-hash')
    async def review(inputs):
        return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,recovery_class=RecoveryClass.USER_DECISION,
            external_ref=ref,user_decision=UserDecisionRequest(category=DecisionCategory.ART_APPROVAL,question='Review this exact media?'))
    r=engine(tmp_path,review);run=create(r);waiting=await r.run(run.run_id)
    assert waiting.state==RuntimeState.WAITING_USER
    assert r.next_action(run.run_id).kind==ActionKind.REQUEST_USER_DECISION
    with pytest.raises(ValueError,match='another dependency'):
        await r.record_external_result(run.run_id,external_ref=ref.model_copy(update={'artifact_ref':'wrong'}),result=CapabilityResult(status=ResultStatus.SUCCEEDED))
    receipt=ArtifactReference(owner='creative-media-review',artifact_ref='human-pass')
    await r.record_external_result(run.run_id,external_ref=ref,result=CapabilityResult(status=ResultStatus.SUCCEEDED,artifact_refs=(receipt,)))
    assert (await r.run(run.run_id)).state==RuntimeState.SUCCEEDED

@pytest.mark.asyncio
async def test_dynamic_authority_decision_wakes_same_step_without_skipping_consumer(tmp_path):
    accepted=False;calls=[]
    async def owner(inputs):
        calls.append(inputs.operation_id)
        if not accepted:return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,recovery_class=RecoveryClass.USER_DECISION,
            external_ref=ArtifactReference(owner='source-rights-request',artifact_ref='exact-request'),
            user_decision=UserDecisionRequest(category=DecisionCategory.ADOPTION,question='Authorize exact external processing scope?'))
        return CapabilityResult(status=ResultStatus.SUCCEEDED)
    r=engine(tmp_path,owner);run=create(r);await r.run(run.run_id)
    accepted=True
    resumed=await r.decide(run.run_id,decision_id=r.decision_id(run.run_id),accepted=True,
        decision_ref=ArtifactReference(owner='user-decision',artifact_ref='exact-receipt'))
    assert resumed.cursor==0
    assert (await r.run(run.run_id)).state==RuntimeState.SUCCEEDED and len(calls)==2


def test_historical_contract_bytes_have_no_empty_recovery_extensions():
    result=CapabilityResult(status=ResultStatus.SUCCEEDED)
    assert set(json.loads(result.model_dump_json(by_alias=True)))=={'status','artifactRefs','code','externalRef'}


@pytest.mark.asyncio
async def test_sqlite_busy_before_dispatch_reloads_without_new_attempt(tmp_path):
    import sqlite3
    calls=[]
    async def owner(inputs):
        calls.append(inputs.operation_id)
        return CapabilityResult(status=ResultStatus.SUCCEEDED)
    r=engine(tmp_path,owner);run=create(r);save=r.store.save;busy=True
    def save_once(following,*,expected_revision):
        nonlocal busy
        if busy:
            busy=False
            error=sqlite3.OperationalError('database is locked')
            error.sqlite_errorcode=sqlite3.SQLITE_BUSY
            raise error
        return save(following,expected_revision=expected_revision)
    r.store.save=save_once
    assert (await r.run(run.run_id)).state==RuntimeState.SUCCEEDED
    assert calls==['same-run:0']


@pytest.mark.asyncio
async def test_owner_busy_returns_exact_checkpoint_without_new_attempt(tmp_path):
    from contextlib import asynccontextmanager
    calls=[]
    async def owner(inputs):calls.append(inputs.operation_id);return CapabilityResult(status=ResultStatus.SUCCEEDED)
    r=engine(tmp_path,owner);run=create(r)
    @asynccontextmanager
    async def busy(run_id):
        raise TimeoutError('RUNTIME_OWNER_BUSY')
        yield
    r.store.lock=busy
    assert await r.run(run.run_id)==run and calls==[]
