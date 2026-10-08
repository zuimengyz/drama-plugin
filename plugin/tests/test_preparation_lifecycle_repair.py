"""The normal reference decision can resume its Film child before preparation.

All production data and prices here are temporary offline fixtures. No socket
or paid action is allowed; the real Run is exercised separately by its Runtime.
"""
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import json
import pytest

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.video import CostEstimate
from drama_plugin.execution.live_transport import FinancialTerms,TargetHttpTransport
from drama_plugin.generation.contracts import GenerationPreparation,FinalPromptArtifact
from drama_plugin.runtime.contracts import CapabilityInput,RuntimeState
from test_unified_mainline import MediaService
from test_unified_planning_recovery import StructuredAuthors,load,adopt_to_rights


class ReferenceAuthors(StructuredAuthors):
    async def design(self,request):
        designs=await super().design(request)
        return tuple(d.model_copy(update={'facts':{'references':[
            {'id':'required-proof','priority':'REQUIRED','beatIds':['beat-1'],
             'designPurpose':'Verify the approved actor.','inputDuty':'Identity proof'}]}})
            if d.domain=='REFERENCE' else d for d in designs)


def input_for(run):
    return CapabilityInput(run_id=run.run_id,operation_id=f'{run.run_id}:{run.cursor}',scope=run.scope)


def offline_terms(plugin,child_id):
    ref=plugin.generation_artifacts.prepared(child_id)
    prepared=plugin.generation_artifacts.get(ref,GenerationPreparation)
    final=plugin.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
    digest=sha256_canonical(TargetHttpTransport.preview(prepared,final))
    now=datetime.now(timezone.utc)
    return FinancialTerms(preparation_ref=ref,profile=prepared.task.profile,wire_payload_hash=digest,
        cost_quote=CostEstimate(currency='CNY',amount=1,source='OFFLINE_FIXTURE_NO_PAID_ACTION',
            checked_at=now,expires_at=now+timedelta(hours=1),request_fingerprint=digest),
        budget_microunits=1000000)


async def reference_boundary(tmp_path,monkeypatch):
    plugin,authors=load(tmp_path,monkeypatch,ReferenceAuthors())
    plugin.providers.media=MediaService(tmp_path/'unused.mp4').provider()
    run_id=await adopt_to_rights(plugin)
    parent=await plugin.runtime.run(run_id)
    assert parent.state==RuntimeState.WAITING_USER and parent.last_result.user_decision.category.value=='ART_APPROVAL'
    cp=plugin.film.store.checkpoint(run_id)
    child=plugin.runtime.store.load(cp.units[0].generation_run_id)
    assert child.cursor==2
    return plugin,authors,parent,child,cp


@pytest.mark.asyncio
async def test_scope_wait_and_approved_scope_are_normal_absence_then_prepare(tmp_path,monkeypatch):
    p,a,parent,child,cp=await reference_boundary(tmp_path,monkeypatch)
    assert not p.film.inspect_media_execution(input_for(parent)).completed
    assert p.generation_artifacts.prepared(child.run_id,required=False) is None
    await p.decide_target_run(parent.run_id,decision_id=p.runtime.decision_id(parent.run_id),
        accepted=True,source_ref=cp.units[0].package_ref)
    assert not p.film.inspect_media_execution(input_for(parent)).completed
    result=await p.resume_source_film_run(parent.run_id)
    fixed=p.film.store.checkpoint(parent.run_id)
    assert fixed.units[0].generation_run_id==child.run_id
    assert result.state==RuntimeState.WAITING_EXTERNAL and result.last_result.external_ref.owner=='generation-preparation'
    prepared=p.generation_artifacts.get(p.generation_artifacts.prepared(child.run_id),GenerationPreparation)
    assert (await p.prompt_compiler.prompt_ir(prepared)).duration_ms==4000
    assert p.film.inspect_media_execution(input_for(result)).completed
    terms=offline_terms(p,child.run_id)
    with pytest.raises(ValueError,match='Exact preparation/wire'):
        await p.provide_media_cost_terms(parent.run_id,terms.model_copy(update={'wire_payload_hash':'0'*64,
            'cost_quote':terms.cost_quote.model_copy(update={'request_fingerprint':'0'*64})}))
    result=await p.provide_media_cost_terms(parent.run_id,terms)
    assert result.state==RuntimeState.WAITING_USER and result.last_result.user_decision.category.value=='COST_APPROVAL'
    assert a.calls==['canon','direction','professional']
    with p.ledger.transaction() as db:
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='execution-operation'").fetchone()[0]==0


@pytest.mark.asyncio
async def test_failed_inspection_repair_restores_same_child_and_preserves_failure(tmp_path,monkeypatch):
    p,a,parent,child,cp=await reference_boundary(tmp_path,monkeypatch)
    await p.decide_target_run(parent.run_id,decision_id=p.runtime.decision_id(parent.run_id),
        accepted=True,source_ref=cp.units[0].package_ref)
    capability=p.runtime.executor._native['film.execute:v1']
    def old_inspector(inputs):
        p.generation_artifacts.prepared(child.run_id)
        return capability.inspect_execution(inputs)
    p.runtime.executor._native['film.execute:v1']=replace(capability,inspect_execution=old_inspector)
    failed=await p.runtime.run(parent.run_id)
    assert failed.state==RuntimeState.FAILED and failed.step_attempts==0
    assert failed.last_result.code=='EXECUTION_IDENTITY_UNAVAILABLE' and failed.last_result.exception_type=='KeyError'
    restored,a2=load(tmp_path,monkeypatch)
    restored.providers.media=MediaService(tmp_path/'unused.mp4').provider()
    inspection=restored.film.inspect_media_execution(input_for(failed))
    reserved=await restored.runtime.repair_inspection_failure(failed.run_id,expected_revision=failed.revision,
        cursor=5,capability_key='film.execute:v1',input_fingerprint=inspection.revision.input_fingerprint)
    assert reserved.step_attempts==failed.step_attempts and reserved.cursor==failed.cursor
    assert reserved.inspection_repairs[0].failed_result==failed.last_result
    assert reserved.inspection_repairs[0].failed_revision==failed.revision
    # Re-open the existing durable owner before driving the original child.
    fresh,a3=load(tmp_path,monkeypatch)
    fresh.providers.media=MediaService(tmp_path/'unused.mp4').provider()
    assert fresh.runtime.store.load(failed.run_id)==reserved
    result=await fresh.resume_source_film_run(failed.run_id)
    assert result.state==RuntimeState.WAITING_EXTERNAL and result.last_result.external_ref.owner=='generation-preparation'
    result=await fresh.provide_media_cost_terms(failed.run_id,offline_terms(fresh,child.run_id))
    assert result.state==RuntimeState.WAITING_USER and result.last_result.user_decision.category.value=='COST_APPROVAL'
    fixed=fresh.film.store.checkpoint(failed.run_id)
    assert fixed.plan_ref==cp.plan_ref and fixed.units[0].package_ref==cp.units[0].package_ref
    assert fixed.units[0].refs==cp.units[0].refs and fixed.units[0].generation_run_id==child.run_id
    assert not a2.calls and not a3.calls and a.calls==['canon','direction','professional']
    assert json.loads(fresh.runtime.serialize(failed.run_id))['inspectionRepairs'][0]['failedResult']['code']=='EXECUTION_IDENTITY_UNAVAILABLE'
    with pytest.raises(ValueError,match='history is immutable'):
        fresh.runtime.store.save(result.model_copy(update={'revision':result.revision+1,'inspection_repairs':()}),expected_revision=result.revision)
    with fresh.ledger.transaction() as db:
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='production-package'").fetchone()[0]==2
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='execution-operation'").fetchone()[0]==0


@pytest.mark.asyncio
async def test_absence_after_ready_and_corrupt_early_reference_still_fail(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from drama_plugin.film.capability import FilmCapabilities
    p,a,parent,child,cp=await reference_boundary(tmp_path,monkeypatch)
    # Read-only inspector receives a later child phase; no fake checkpoint write.
    store=SimpleNamespace(load=lambda run_id:parent if run_id==parent.run_id else child.model_copy(update={'cursor':4,'state':RuntimeState.READY,'wait_reason':None}))
    view=SimpleNamespace(runtime=SimpleNamespace(store=store),generation_artifacts=p.generation_artifacts,
        production_packages=p.production_packages,source_film_media_opening=p.source_film_media_opening,
        source_film_unit_for_task=p.source_film_unit_for_task)
    owner=FilmCapabilities(view,p.film.store)
    with pytest.raises(KeyError,match='Exact preparation'):
        owner.inspect_media_execution(input_for(parent))
    # An early retained preparation failure must not be hidden as optional absence.
    def corrupt(*args,**kwargs):raise ValueError('Derived artifact reference/scope/fingerprint mismatch')
    monkeypatch.setattr(p.generation_artifacts,'prepared',corrupt)
    with pytest.raises(ValueError,match='fingerprint mismatch'):
        p.film.inspect_media_execution(input_for(parent))


@pytest.mark.asyncio
async def test_inspection_repair_denies_wrong_revision_or_authority(tmp_path,monkeypatch):
    p,a,parent,child,cp=await reference_boundary(tmp_path,monkeypatch)
    await p.decide_target_run(parent.run_id,decision_id=p.runtime.decision_id(parent.run_id),
        accepted=True,source_ref=cp.units[0].package_ref)
    original=p.runtime.executor._native['film.execute:v1']
    def broken(_):raise KeyError('before preparation')
    p.runtime.executor._native['film.execute:v1']=replace(original,inspect_execution=broken)
    failed=await p.runtime.run(parent.run_id)
    p.runtime.executor._native['film.execute:v1']=original
    inspection=p.film.inspect_media_execution(input_for(failed))
    for revision,identity,error in [(failed.revision-1,inspection.revision.input_fingerprint,'REVISION_MISMATCH'),
        (failed.revision,'0'*64,'AUTHORITY_INPUT_CHANGED')]:
        with pytest.raises(ValueError,match=error):
            await p.runtime.repair_inspection_failure(parent.run_id,expected_revision=revision,cursor=5,
                capability_key='film.execute:v1',input_fingerprint=identity)
    assert p.runtime.store.load(parent.run_id)==failed
