"""Bounded UNKNOWN recovery; every HTTP request is in-process MockTransport."""
from dataclasses import replace
import json, socket
import httpx
import pytest
from pydantic import SecretStr
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.video import ProviderTask
from drama_plugin.execution.contracts import ExecutionOperation, ProviderAttempt, MediaBinding, OperationState
from drama_plugin.execution.live_transport import FinancialTerms, TargetHttpTransport
from drama_plugin.providers.video.adapters import SeedanceProvider
from drama_plugin.providers.video.registry import ProviderSettings
from drama_plugin.runtime.contracts import CapabilityResult, ResultStatus, RecoveryClass, RuntimeState
from test_preparation_lifecycle_repair import reference_boundary, offline_terms
from test_unified_mainline import MediaService, video, FAKE_SECRET

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Only MockTransport permitted')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)

async def failed_film(tmp_path, monkeypatch, video, mode):
    p, authors, parent, child, cp = await reference_boundary(tmp_path, monkeypatch)
    await p.decide_target_run(parent.run_id, decision_id=p.runtime.decision_id(parent.run_id),
        accepted=True, source_ref=cp.units[0].package_ref)
    await p.resume_source_film_run(parent.run_id)
    terms = offline_terms(p, child.run_id)
    await p.provide_media_cost_terms(parent.run_id, terms)
    await p.decide_target_run(parent.run_id, decision_id=p.runtime.decision_id(parent.run_id),
        accepted=True, source_ref=terms.preparation_ref)
    calls=[]
    def handle(request):
        calls.append(request)
        if request.method == 'POST':
            if sum(r.method == 'POST' for r in calls) == 1 or mode == 'unknown':
                raise httpx.ReadTimeout('Fixture ACK loss', request=request)
            return httpx.Response(200, json={'id':'second-task', 'status':'running'})
        if request.url.path.endswith('/contents/generations/tasks'):
            return httpx.Response(200, json={'total':0, 'items':[]})
        if '/contents/generations/tasks/' in request.url.path:
            return httpx.Response(200, json={'id':'first-task' if mode == 'recover' else 'second-task',
                'status':'succeeded','content':{'video_url':'https://result.invalid/video.mp4'},
                'usage':{'completion_tokens':86400}})
        return httpx.Response(200, content=video.read_bytes())
    async def no_reference(_):
        raise AssertionError('No input generation')
    adapter=SeedanceProvider('seedance-2-fast',ProviderSettings(api_key=SecretStr(FAKE_SECRET),
        base_url='https://ark.cn-beijing.volces.com/api/v3'),resolve=no_reference,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handle)))
    transport=TargetHttpTransport(adapter,tmp_path/'acks',ledger=p.ledger)
    p.execution.transports['seedance']=transport
    service=MediaService(video);p.providers.media=service.provider()
    p.execution.media.provider=p.providers.media
    monkeypatch.setenv('DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS', str(tmp_path))
    # Reproduce the historical terminal outcome through the normal Runtime owner.
    native=p.runtime.executor._native['execution.provider:v1']
    async def old_behavior(inputs):
        result=await native.handler(inputs)
        return CapabilityResult(status=ResultStatus.FAILED,code='PROVIDER_UNKNOWN_WITHOUT_LOOKUP',
            artifact_refs=result.artifact_refs,recovery_class=RecoveryClass.HARD_BLOCK)
    p.runtime.executor._native['execution.provider:v1']=replace(native,handler=old_behavior)
    failed=await p.resume_source_film_run(parent.run_id)
    p.runtime.executor._native['execution.provider:v1']=native
    assert failed.state == RuntimeState.FAILED
    with p.ledger.transaction() as db:
        row=db.execute('SELECT operation_ref_json FROM production_operation WHERE operation_ref_json IS NOT NULL').fetchone()
    from drama_plugin.runtime.contracts import ArtifactReference
    ref=ArtifactReference.model_validate_json(row[0])
    op=p.execution.store.get(ref,ExecutionOperation);checkpoint=p.execution.store.checkpoint(ref)
    old_attempt=p.execution.store.get(checkpoint.attempt_ref,ProviderAttempt)
    retry=FinancialTerms(**{**terms.model_dump(), 'budget_microunits':2000000,
        'max_paid_operations':2,'paid_retries':1,'recovery_operation_ref':ref,
        'prior_attempt_ref':checkpoint.attempt_ref,'reserved_unknown_microunits':1000000})
    if mode == 'recover':
        task=ProviderTask(provider='seedance',model='seedance-2-fast',provider_task_id='first-task',
            client_request_id=old_attempt.client_identity, request_fingerprint=old_attempt.request_fingerprint,
            status='SUCCEEDED',output_url='https://result.invalid/video.mp4')
        receipt=transport.receipt(op,old_attempt,task)
        transport._path(old_attempt).write_text(receipt.model_dump_json(by_alias=True))
    return p,authors,failed,child,cp,op,old_attempt,retry,transport,calls,service

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['recover','success','unknown'])
async def test_same_film_operation_bounded_supplement_and_persistence(tmp_path,monkeypatch,video,mode):
    p,a,failed,child,cp,op,old,retry,t,calls,service=await failed_film(tmp_path,monkeypatch,video,mode)
    composed=[]
    def same_transport(**kwargs):
        composed.append(kwargs['recovery_operation_ref'])
        return t
    monkeypatch.setattr('drama_plugin.execution.live_transport.configured_http_transport',same_transport)
    p.execution.transports.clear()
    original_child=p.runtime.store.load(child.run_id)
    repaired=await p.recover_unknown_media_submission(failed.run_id,terms=retry,accepted=True)
    assert repaired.external_repairs[0].failed_result == failed.last_result
    assert p.runtime.store.load(child.run_id).external_repairs[0].failed_result == original_child.last_result
    assert repaired.step_attempts == failed.step_attempts
    assert composed == [op.artifact_reference()]
    result=await p.resume_source_film_run(failed.run_id)
    for _ in range(3):
        if p.execution.store.checkpoint(op.artifact_reference()).progress.video_ref:
            break
        result=await p.resume_source_film_run(failed.run_id)
    current=p.execution.store.checkpoint(op.artifact_reference())
    assert p.generation_artifacts.prepared(child.run_id) == retry.preparation_ref
    fixed=p.film.store.checkpoint(failed.run_id)
    assert fixed.units[0].package_ref == cp.units[0].package_ref and fixed.units[0].refs == cp.units[0].refs
    assert a.calls == ['canon','direction','professional']
    assert sum(r.method == 'POST' for r in calls) == (1 if mode == 'recover' else 2)
    assert p.execution.store.get(old.artifact_reference(),ProviderAttempt) == old
    if mode == 'recover':
        assert current.attempt_ref == old.artifact_reference() and not current.progress.attempt_history
    else:
        assert current.progress.attempt_history[0].state == OperationState.UNKNOWN
        assert current.progress.attempt_history[0].reserved_cost_microunits == 1000000
        assert p.execution.store.get(current.attempt_ref,ProviderAttempt).previous_attempt_ref == old.artifact_reference()
    if mode == 'unknown':
        assert result.state == RuntimeState.WAITING_EXTERNAL and current.state == OperationState.UNKNOWN
        for _ in range(3):await p.resume_source_film_run(failed.run_id)
        assert sum(r.method == 'POST' for r in calls) == 2
        assert p.execution.store.checkpoint(op.artifact_reference()).progress.unknown_lookup_attempts == 4
    else:
        assert current.progress.video_ref is not None, (result.model_dump(), p.runtime.store.load(child.run_id).model_dump(), current)
        binding=p.execution.store.get(current.progress.video_ref,MediaBinding)
        assert binding.canonical_media_ref and service.imports == 1
        assert p.execution.media.path(binding.media).read_bytes() == video.read_bytes()
    with p.ledger.transaction() as db:
        assert db.execute('SELECT count(*) FROM production_operation WHERE operation_ref_json IS NOT NULL').fetchone()[0] == 1
    saved=p.runtime.store.load(failed.run_id)
    with pytest.raises(ValueError,match='history is immutable'):
        p.runtime.store.save(saved.model_copy(update={'revision':saved.revision+1,'external_repairs':()}),expected_revision=saved.revision)

@pytest.mark.asyncio
async def test_recovery_keeps_unknown_reserve_and_rejects_request_or_budget_drift(tmp_path,monkeypatch,video):
    p,a,failed,child,cp,op,old,terms,t,calls,service=await failed_film(tmp_path,monkeypatch,video,'unknown')
    with pytest.raises(ValueError,match='INVALID_OR_EXPIRED'):
        await p.recover_unknown_media_submission(failed.run_id,
            terms=terms.model_copy(update={'budget_microunits':1999999}),accepted=True)
    changed=terms.model_copy(update={'wire_payload_hash':'0'*64,
        'cost_quote':terms.cost_quote.model_copy(update={'request_fingerprint':'0'*64})})
    with pytest.raises(ValueError,match='Exact operation'):
        await p.recover_unknown_media_submission(failed.run_id,terms=changed,accepted=True)
    assert p.runtime.store.load(failed.run_id) == failed
    assert sum(r.method == 'POST' for r in calls) == 1

@pytest.mark.asyncio
async def test_completed_video_import_configuration_failure_resumes_same_result(tmp_path,monkeypatch,video):
    from drama_plugin.exceptions import MediaImportSourceError
    p,a,failed,child,cp,op,old,terms,t,calls,service=await failed_film(tmp_path,monkeypatch,video,'success')
    await p.recover_unknown_media_submission(failed.run_id,terms=terms,accepted=True)
    await p.resume_source_film_run(failed.run_id)
    monkeypatch.setenv('DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS',str(tmp_path/'unrelated'))
    waiting=await p.resume_source_film_run(failed.run_id)
    assert waiting.state == RuntimeState.WAITING_EXTERNAL
    assert p.execution.store.checkpoint(op.artifact_reference()).progress.media_last_code == 'FORMAL_MEDIA_IMPORT_SOURCE_CONFIGURATION'
    native=p.runtime.executor._native['execution.media_intake:v1']
    async def historical_uncaught_configuration(inputs):
        raise MediaImportSourceError('Historical import allowlist omission',error_code='INVALID_ARGUMENT')
    p.runtime.executor._native['execution.media_intake:v1']=replace(native,handler=historical_uncaught_configuration)
    broken=await p.resume_source_film_run(failed.run_id)
    broken_child=p.runtime.store.load(child.run_id)
    assert broken.state == RuntimeState.FAILED and broken_child.last_result.exception_type == 'MediaImportSourceError'
    p.runtime.executor._native['execution.media_intake:v1']=native
    # The guard refuses to reopen until the exact cached file passes the allowlist.
    with pytest.raises(MediaImportSourceError):
        await p.resume_source_film_run(failed.run_id)
    assert p.runtime.store.load(child.run_id) == broken_child
    monkeypatch.setenv('DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS',str(tmp_path))
    recovered=await p.resume_source_film_run(failed.run_id)
    current=p.execution.store.checkpoint(op.artifact_reference())
    assert current.progress.video_ref and current.state == OperationState.SUCCEEDED
    binding=p.execution.store.get(current.progress.video_ref,MediaBinding)
    assert binding.canonical_media_ref and service.imports == 1
    assert p.execution.media.path(binding.media).read_bytes() == video.read_bytes()
    assert sum(r.method == 'POST' for r in calls) == 2
    assert a.calls == ['canon','direction','professional']
    assert p.generation_artifacts.prepared(child.run_id) == terms.preparation_ref
    assert recovered.external_repairs[-1].failed_result == broken.last_result
    assert p.runtime.store.load(child.run_id).external_repairs[-1].failed_result == broken_child.last_result

@pytest.mark.asyncio
async def test_definitely_rejected_service_import_repairs_without_another_generation(tmp_path,monkeypatch,video):
    from drama_plugin.exceptions import RemoteServiceError
    p,a,failed,child,cp,op,old,terms,t,calls,service=await failed_film(tmp_path,monkeypatch,video,'success')
    await p.recover_unknown_media_submission(failed.run_id,terms=terms,accepted=True)
    await p.resume_source_film_run(failed.run_id)
    provider=p.execution.media.provider
    import_media=provider.import_media
    async def old_service_refusal(**kwargs):
        raise RemoteServiceError('Old service native scope unavailable',status_code=404,error_code='NOT_FOUND')
    monkeypatch.setattr(provider,'import_media',old_service_refusal)
    broken=await p.resume_source_film_run(failed.run_id)
    broken_child=p.runtime.store.load(child.run_id)
    assert broken.state == RuntimeState.FAILED and broken_child.last_result.code == 'FORMAL_MEDIA_NOT_FOUND'
    checkpoint=p.execution.store.checkpoint(op.artifact_reference())
    claim=p.execution.media._registration_path(op.scope,checkpoint.progress.intake_media).with_suffix('.claim')
    assert claim.read_bytes() == b'SUBMITTING'
    monkeypatch.setattr(provider,'import_media',import_media)
    recovered=await p.resume_source_film_run(failed.run_id)
    current=p.execution.store.checkpoint(op.artifact_reference())
    assert current.progress.video_ref and service.imports == 1
    assert recovered.external_repairs[-1].failed_result == broken.last_result
    archive=json.loads(claim.with_suffix('.rejected-not-found.json').read_text())
    assert archive['failedResult'] == broken_child.last_result.model_dump(mode='json',by_alias=True)
    assert archive['claim'] == 'SUBMITTING'
    assert sum(r.method == 'POST' for r in calls) == 2 and a.calls == ['canon','direction','professional']
