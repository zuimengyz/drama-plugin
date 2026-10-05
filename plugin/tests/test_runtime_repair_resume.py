"""Revision-bound, single-use recovery without erasing ordinary attempts."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.persistence.ledger import ProductionLedger
from drama_plugin.persistence.stores import DurableRunStore
from drama_plugin.runtime.bridge import LegacyCapabilityBridge
from drama_plugin.runtime.capabilities import TargetCapability, TargetCapabilityRouter
from drama_plugin.runtime.contracts import (ActionKind, ArtifactReference, CapabilityResult,
    ExecutionInspection, ExecutionRevision, ExhaustedExecutionEvidence, ResultStatus,
    RunMode, RuntimeAction, RuntimeState, RuntimeWorkflow)
from drama_plugin.runtime.engine import RuntimeEngine, validate_transition

KEY='author.direction:v1'
FLOW=RuntimeWorkflow(workflow_id='repair-test:v1',steps=(RuntimeAction(kind=ActionKind.CALL_CAPABILITY,capability_key=KEY),))

class Owner:
    fingerprint=sha256_canonical('old-contract')
    inputs=sha256_canonical('fixed-authority-refs')
    completed=False
    calls=0
    status=ResultStatus.RETRYABLE_FAILURE
    crash=False

    def inspect(self, inputs):
        return ExecutionInspection(revision=ExecutionRevision(fingerprint=self.fingerprint,input_fingerprint=self.inputs),completed=self.completed)

    async def execute(self, inputs):
        self.calls+=1
        if self.crash: raise asyncio.CancelledError()
        if self.status==ResultStatus.SUCCEEDED:self.completed=True
        return CapabilityResult(status=self.status,code='TEST_FAILURE' if self.status!=ResultStatus.SUCCEEDED else None)


def engine(path, owner):
    ledger=ProductionLedger(path)
    router=TargetCapabilityRouter({KEY:TargetCapability(owner.execute,True,owner.inspect)},LegacyCapabilityBridge({}))
    return RuntimeEngine(router,store=DurableRunStore(ledger),workflows={FLOW.workflow_id:FLOW}),ledger


def evidence(revision, attempts=2):
    return ExhaustedExecutionEvidence(revision=revision,historical_attempts=attempts,
        evidence_ref=ArtifactReference(owner='execution-audit',artifact_ref='sha256:'+sha256_canonical(revision),version=1))

async def exhausted(path):
    owner=Owner(); runtime,ledger=engine(path,owner)
    run=runtime.create_run(work_id='work',mode=RunMode.PRODUCTION,workflow_id=FLOW.workflow_id)
    run=await runtime.run(run.run_id)
    assert run.step_attempts==2
    assert run.state==RuntimeState.FAILED and run.last_result.code=='RETRY_LIMIT_REACHED'
    return owner,runtime,ledger,run,evidence(run.execution_revision)


def rows(ledger):
    with ledger.transaction() as db:
        return [tuple(row) for row in db.execute('SELECT * FROM production_operation ORDER BY attempt_identity')]

@pytest.mark.asyncio
async def test_same_revision_exhausted_survives_fresh_process(tmp_path):
    owner,runtime,ledger,run,proof=await exhausted(tmp_path/'ledger.sqlite')
    before=rows(ledger)
    for r in (runtime,engine(ledger.path,owner)[0]):
        with pytest.raises(ValueError,match='RETRY_LIMIT_REACHED'):
            await r.repair_resume(run.run_id,cursor=0,capability_key=KEY,exhausted=proof)
    program="""
import sys
from drama_plugin.persistence.ledger import ProductionLedger
r=ProductionLedger(sys.argv[1]).load_run(sys.argv[2])
assert r.state.value=='FAILED' and r.step_attempts==2
assert r.execution_revision.fingerprint==sys.argv[3] and not r.repair_resumes
print('RESTORE_PASS')
"""
    result=subprocess.run([sys.executable,'-c',program,str(ledger.path),run.run_id,owner.fingerprint],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'RESTORE_PASS' in result.stdout and rows(ledger)==before and owner.calls==2

@pytest.mark.asyncio
async def test_changed_revision_one_resume_preserves_history_and_restores(tmp_path):
    owner,runtime,ledger,run,proof=await exhausted(tmp_path/'ledger.sqlite'); before=rows(ledger)
    owner.fingerprint=sha256_canonical('repaired-contract')
    reserved=await runtime.repair_resume(run.run_id,cursor=0,capability_key=KEY,exhausted=proof)
    assert reserved.step_attempts==2 and reserved.repair_resumes[0].attempts==0
    assert reserved.repair_resumes[0].exhausted==proof and rows(ledger)==before
    # New process restores the reservation, without creating a fresh allowance.
    program="""
import sys
from drama_plugin.persistence.ledger import ProductionLedger
r=ProductionLedger(sys.argv[1]).load_run(sys.argv[2])
assert r.state.value=='READY' and r.step_attempts==2
assert len(r.repair_resumes)==1 and r.repair_resumes[0].attempts==0
assert r.repair_resumes[0].current.fingerprint==sys.argv[3]
"""
    assert subprocess.run([sys.executable,'-c',program,str(ledger.path),run.run_id,owner.fingerprint]).returncode==0
    fresh,_=engine(ledger.path,owner)
    failed=await fresh.run(run.run_id)
    assert failed.state==RuntimeState.FAILED and failed.step_attempts==2
    assert failed.repair_resumes[0].attempts==1 and owner.calls==3
    assert all(row in rows(ledger) for row in before) and len(rows(ledger))==3
    with pytest.raises(ValueError):await fresh.repair_resume(run.run_id,cursor=0,capability_key=KEY,exhausted=proof)
    assert (await fresh.run(run.run_id)).state==RuntimeState.FAILED and owner.calls==3
    snapshot=fresh.serialize(run.run_id)
    assert 'api_key' not in snapshot and 'system_content' not in snapshot

@pytest.mark.asyncio
async def test_success_advances_same_runtime_only_once(tmp_path):
    owner,runtime,ledger,run,proof=await exhausted(tmp_path/'ledger.sqlite')
    owner.fingerprint=sha256_canonical('new');owner.status=ResultStatus.SUCCEEDED
    await runtime.repair_resume(run.run_id,cursor=0,capability_key=KEY,exhausted=proof)
    result=await runtime.run(run.run_id)
    assert result.state==RuntimeState.SUCCEEDED and result.cursor==1
    assert result.repair_resumes[0].exhausted.historical_attempts==2
    assert result.repair_resumes[0].attempts==1 and owner.calls==3
    assert len(rows(ledger))==3

@pytest.mark.asyncio
@pytest.mark.parametrize('change,code',[('inputs','REPAIR_AUTHORITY_INPUT_CHANGED'),('completed','STEP_COMPLETED'),('cursor','STEP_MISMATCH'),('capability','STEP_MISMATCH'),('attempts','ATTEMPT_HISTORY_MISMATCH'),('old','EXHAUSTED_REVISION_MISMATCH')])
async def test_repair_predicates_fail_closed(tmp_path,change,code):
    owner,runtime,ledger,run,proof=await exhausted(tmp_path/'ledger.sqlite');before=rows(ledger)
    owner.fingerprint=sha256_canonical('new');cursor=0;key=KEY
    if change=='inputs':owner.inputs=sha256_canonical('changed-source-or-canon')
    if change=='completed':owner.completed=True
    if change=='cursor':cursor=1
    if change=='capability':key='other:v1'
    if change=='attempts':proof=evidence(proof.revision,1)
    if change=='old':proof=evidence(ExecutionRevision(fingerprint=sha256_canonical('fake-old'),input_fingerprint=owner.inputs))
    with pytest.raises(ValueError,match=code):await runtime.repair_resume(run.run_id,cursor=cursor,capability_key=key,exhausted=proof)
    assert rows(ledger)==before and owner.calls==2

@pytest.mark.asyncio
async def test_other_terminal_failures_and_general_transition_stay_terminal(tmp_path):
    owner=Owner();owner.status=ResultStatus.FAILED
    runtime,ledger=engine(tmp_path/'ledger.sqlite',owner)
    run=runtime.create_run(work_id='w',mode=RunMode.PRODUCTION,workflow_id=FLOW.workflow_id)
    run=await runtime.run(run.run_id)
    owner.fingerprint=sha256_canonical('new')
    with pytest.raises(ValueError,match='EXHAUSTED_FAILURE'):
        await runtime.repair_resume(run.run_id,cursor=0,capability_key=KEY,exhausted=evidence(run.execution_revision,1))
    with pytest.raises(ValueError):validate_transition(RuntimeState.FAILED,RuntimeState.READY)
    with pytest.raises(ValueError,match='Only a blocked'):await runtime.retry(run.run_id)

@pytest.mark.asyncio
async def test_crash_after_debit_cannot_retry_or_repair_again(tmp_path):
    owner,runtime,ledger,run,proof=await exhausted(tmp_path/'ledger.sqlite')
    owner.fingerprint=sha256_canonical('new');owner.crash=True
    await runtime.repair_resume(run.run_id,cursor=0,capability_key=KEY,exhausted=proof)
    with pytest.raises(asyncio.CancelledError):await runtime.run(run.run_id)
    fresh,_=engine(ledger.path,owner)
    restored=await fresh.recover_run(run.run_id)
    assert restored.state==RuntimeState.READY and restored.repair_resumes[0].attempts==1
    assert (await fresh.run(run.run_id)).last_result.code=='RETRY_LIMIT_REACHED'
    with pytest.raises(ValueError,match='OPPORTUNITY_ALREADY_USED'):
        await fresh.repair_resume(run.run_id,cursor=0,capability_key=KEY,exhausted=proof)
    owner.fingerprint=sha256_canonical('yet-another-contract')
    with pytest.raises(ValueError,match='OPPORTUNITY_ALREADY_USED'):
        await fresh.repair_resume(run.run_id,cursor=0,capability_key=KEY,exhausted=proof)
    assert owner.calls==3 and len(rows(ledger))==3

@pytest.mark.asyncio
@pytest.mark.parametrize('field',['fingerprint','inputs','completed'])
async def test_drift_between_reservation_and_execution_denied(tmp_path,field):
    owner,runtime,ledger,run,proof=await exhausted(tmp_path/'ledger.sqlite')
    owner.fingerprint=sha256_canonical('new')
    await runtime.repair_resume(run.run_id,cursor=0,capability_key=KEY,exhausted=proof)
    setattr(owner,field,True if field=='completed' else sha256_canonical('drift'))
    result=await runtime.run(run.run_id)
    assert result.state==RuntimeState.FAILED and result.last_result.code=='REPAIR_EXECUTION_DENIED'
    assert owner.calls==2 and len(rows(ledger))==2

@pytest.mark.asyncio
async def test_repair_metadata_cannot_be_erased_or_replaced(tmp_path):
    owner,runtime,ledger,run,proof=await exhausted(tmp_path/'ledger.sqlite')
    owner.fingerprint=sha256_canonical('new')
    reserved=await runtime.repair_resume(run.run_id,cursor=0,capability_key=KEY,exhausted=proof)
    with pytest.raises(ValueError,match='history cannot be removed'):
        runtime.store.save(reserved.model_copy(update={'revision':reserved.revision+1,'repair_resumes':()}),expected_revision=reserved.revision)

@pytest.mark.asyncio
async def test_pre_revision_checkpoint_uses_explicit_audited_evidence(tmp_path):
    # An existing checkpoint legitimately created before revision capture.
    from drama_plugin.runtime.store import InMemoryRunStore
    from drama_plugin.runtime.bridge import CapabilityExecutor
    class OldExecutor:
        async def execute(self,key,inputs):return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE,code='OLD_FAILURE')
        def replay_safe(self,key):return True
    old=RuntimeEngine(OldExecutor(),workflows={FLOW.workflow_id:FLOW})
    run=old.create_run(work_id='w',mode=RunMode.PRODUCTION,workflow_id=FLOW.workflow_id)
    run=await old.run(run.run_id)
    assert run.execution_revision is None and 'executionRevision' not in json.loads(old.serialize(run.run_id))
    owner=Owner();snapshot=owner.inspect(None).revision;owner.fingerprint=sha256_canonical('new')
    router=TargetCapabilityRouter({KEY:TargetCapability(owner.execute,True,owner.inspect)},LegacyCapabilityBridge({}))
    new=RuntimeEngine(router,store=old.store,workflows={FLOW.workflow_id:FLOW})
    resumed=await new.repair_resume(run.run_id,cursor=0,capability_key=KEY,exhausted=evidence(snapshot))
    assert resumed.repair_resumes[0].exhausted.evidence_ref.owner=='execution-audit'

@pytest.mark.asyncio
async def test_formal_direction_revision_matches_actual_projection_and_policy():
    import httpx
    from drama_plugin.config.loader import load_config
    from drama_plugin.creative_engine.backends import compose_authors
    from test_formal_author_backends import ENV, SKILLS, model_output, request, response
    config=load_config(environment=ENV).text_composition
    captured=[]
    def mock(wire):captured.append(json.loads(wire.content));return response(model_output('direction'))
    _,author,_=compose_authors(config,SKILLS,transport=httpx.MockTransport(mock))
    first=author.execution_fingerprint()
    await author.author(request('direction'))
    identity='creative.direction:v1:FormalDirectionAuthor'
    assert first==author.client.execution_fingerprint('direction',identity,captured[0]['messages'][0]['content'])
    secret=config.api_key.get_secret_value()
    assert secret not in first and first==author.execution_fingerprint()
    for field,value in [('direction_model','different-model'),('max_output_tokens',16384),('reasoning_effort','high')]:
        new_config=config.model_copy(update={field:value})
        _,changed,_=compose_authors(new_config,SKILLS)
        assert changed.execution_fingerprint()!=first
    assert author.client.execution_fingerprint('direction',identity,captured[0]['messages'][0]['content']+'changed-schema')!=first
