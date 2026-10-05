"""Unified external recovery: temporary owners, Mock HTTP, zero live side effects."""
from pathlib import Path
import hashlib
import json
import socket
import httpx
import pytest
from pydantic import SecretStr

from drama_plugin.config import DramaPluginConfig
from drama_plugin.execution.contracts import (FinishingRecipe, ProviderAttempt, ProviderReceipt,
    CreativeMediaReview, TechnicalMediaReview, MediaBinding, OperationState, ReviewObservation)
from drama_plugin.generation.contracts import GenerationPreparation
from drama_plugin.execution.live_transport import TargetHttpTransport
from drama_plugin.execution.transport import IntakeTransient
from drama_plugin.execution.review import MockReviewer, ReviewResponse
from drama_plugin.providers.video.adapters import SeedanceProvider
from drama_plugin.providers.video.registry import ProviderSettings
from drama_plugin.runtime.contracts import CapabilityInput, RecoveryClass, ResultStatus, RuntimeState
from test_production_package import fixture
from test_prompt_audio_convergence import generation_fixture
from test_target_execution import setup, checkpoint, submissions, recorded_video
from test_unified_mainline import load as formal_load, task_for, prepare_goal, video, MediaService, no_external_calls


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Unified repair qualification permits Mock HTTP only')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)


async def http_setup(generation_fixture, tmp_path, recorded_video, handler):
    p, replay, prior = await setup(generation_fixture, tmp_path, recorded_video)
    bound = p.execution.store.inputs(prior.run_id)
    prepared = p.generation_artifacts.get(bound.preparation_ref, GenerationPreparation)
    recipe = p.execution.store.get(bound.recipe_ref, FinishingRecipe)
    recipe = FinishingRecipe.seal(**{**recipe.model_dump(exclude={'fingerprint'}), 'run_id':'http-execute'})
    calls=[]
    def observe(request):
        calls.append(request)
        return handler(request)
    async def no_reference(_):
        raise AssertionError('No paid reference operation')
    adapter = SeedanceProvider(prepared.task.target_model,
        ProviderSettings(base_url='https://ark.cn-beijing.volces.com/api/v3',api_key=SecretStr('MOCK-ONLY')),
        resolve=no_reference, client=httpx.AsyncClient(transport=httpx.MockTransport(observe)))
    transport=TargetHttpTransport(adapter, tmp_path/'acks', ledger=p.ledger, qualification_only=True)
    p.execution.transports['seedance']=transport
    run=p.create_execution_run(run_id='http-execute',mode=p.runtime.store.load(prior.run_id).mode,
        preparation_ref=bound.preparation_ref,authorization=bound.authorization,recipe=recipe,route='seedance')
    return p,transport,CapabilityInput(run_id=run.run_id,operation_id=run.run_id+':0',scope=run.scope),calls


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['timeout',429,503,'malformed'])
async def test_known_task_read_failure_retains_identity_and_never_reposts(generation_fixture,tmp_path,recorded_video,failure):
    def handler(request):
        if request.method=='POST':
            return httpx.Response(200,json={'id':'same-task','status':'running'})
        if failure=='timeout':
            raise httpx.ReadTimeout('Credential-free fixture',request=request)
        if failure=='malformed':
            return httpx.Response(200,content=b'not JSON')
        return httpx.Response(failure,json={'arbitrary':'must not enter evidence'})
    p,transport,inputs,calls=await http_setup(generation_fixture,tmp_path,recorded_video,handler)
    first=await p.execution.execute(inputs)
    assert first.recovery_class==RecoveryClass.WAIT_EXTERNAL, first.model_dump()
    second=await p.execution.execute(inputs)
    assert second.recovery_class==RecoveryClass.WAIT_EXTERNAL
    cp=checkpoint(p,inputs)
    receipt=p.execution.store.get(cp.receipt_ref,ProviderReceipt)
    expected={'timeout':'TRANSPORT_UNCERTAIN','malformed':'INVALID_PROVIDER_RESPONSE'}.get(failure,'HTTP_'+str(failure))
    assert receipt.remote_identity=='same-task' and receipt.query_code==expected
    assert cp.progress.query_attempts==1 and cp.progress.query_started_at_ms
    assert cp.progress.query_last_code==expected
    assert sum(c.method=='POST' for c in calls)==1
    # A new transport process composition gets no new attempt/horizon budget.
    p.execution.transports['seedance']=TargetHttpTransport(transport.adapter,tmp_path/'acks',ledger=p.ledger,qualification_only=True)
    await p.execution.execute(inputs)
    assert checkpoint(p,inputs).progress.query_attempts==2
    assert checkpoint(p,inputs).progress.query_started_at_ms==cp.progress.query_started_at_ms
    assert sum(c.method=='POST' for c in calls)==1


@pytest.mark.asyncio
async def test_unknown_without_authorized_supplement_waits_and_retains_possible_side_effect(generation_fixture,tmp_path,recorded_video):
    def handler(request):
        return httpx.Response(200,json={'status':'running'})
    p,_,inputs,calls=await http_setup(generation_fixture,tmp_path,recorded_video,handler)
    result=await p.execution.execute(inputs)
    assert result.status==ResultStatus.WAITING_EXTERNAL and result.recovery_class==RecoveryClass.WAIT_EXTERNAL
    assert result.external_ref.owner=='execution-operation'
    cp=checkpoint(p,inputs)
    assert cp.state==OperationState.UNKNOWN and cp.progress.query_last_code=='REMOTE_IDENTITY_UNRESOLVED'
    await p.execution.execute(inputs)
    assert sum(c.method=='POST' for c in calls)==1
    assert checkpoint(p,inputs).attempt_ref==cp.attempt_ref


@pytest.mark.asyncio
@pytest.mark.parametrize('status',[400,401,403,429])
async def test_definite_provider_rejection_never_retries_paid_post(generation_fixture,tmp_path,recorded_video,status):
    p,_,inputs,calls=await http_setup(generation_fixture,tmp_path,recorded_video,
        lambda request:httpx.Response(status,json={'secret':'must not be retained'}))
    result=await p.execution.execute(inputs)
    assert result.recovery_class==RecoveryClass.HARD_BLOCK and result.code=='HTTP_'+str(status)
    assert checkpoint(p,inputs).state==OperationState.FAILED
    await p.execution.execute(inputs)
    assert sum(c.method=='POST' for c in calls)==1
    evidence=p.ledger.path.read_bytes()
    assert b'must not be retained' not in evidence and b'MOCK-ONLY' not in evidence


@pytest.mark.asyncio
async def test_known_task_query_horizon_is_durable_and_bounded(generation_fixture,tmp_path,recorded_video):
    p,_,inputs,calls=await http_setup(generation_fixture,tmp_path,recorded_video,
        lambda request:httpx.Response(200,json={'id':'bounded-task','status':'running'}))
    await p.execution.execute(inputs)
    cp=checkpoint(p,inputs)
    p.execution.store.progress(cp.operation_ref,query_attempts=60)
    result=await p.execution.execute(inputs)
    assert result.code=='PROVIDER_QUERY_RETRY_EXHAUSTED' and result.recovery_class==RecoveryClass.HARD_BLOCK
    assert len(calls)==1


@pytest.mark.asyncio
async def test_success_without_locator_keeps_task_for_safe_query(generation_fixture,tmp_path,recorded_video):
    p,_,inputs,calls=await http_setup(generation_fixture,tmp_path,recorded_video,
        lambda request:httpx.Response(200,json={'id':'result-task','status':'succeeded'}))
    result=await p.execution.execute(inputs)
    assert result.recovery_class==RecoveryClass.WAIT_EXTERNAL
    receipt=p.execution.store.get(checkpoint(p,inputs).receipt_ref,ProviderReceipt)
    assert receipt.remote_identity=='result-task' and receipt.query_code=='PROVIDER_RESULT_LOCATOR_PENDING'
    await p.execution.execute(inputs)
    assert sum(c.method=='POST' for c in calls)==1


@pytest.mark.asyncio
async def test_runtime_intake_uses_three_read_attempts_without_another_submit(generation_fixture,tmp_path,recorded_video,monkeypatch):
    p,replay,inputs=await setup(generation_fixture,tmp_path,recorded_video)
    obtain=replay.obtain
    reads=[]
    async def fail_twice(result):
        reads.append(result.result_id)
        if len(reads)<3:
            raise IntakeTransient()
        return await obtain(result)
    monkeypatch.setattr(replay,'obtain',fail_twice)
    done=await p.runtime.run(inputs.run_id)
    assert done.state==RuntimeState.SUCCEEDED,done
    assert len(reads)==3 and checkpoint(p,inputs).progress.intake_attempts==3
    assert len(submissions(replay))==1


@pytest.mark.asyncio
async def test_media_intake_exhaustion_is_hard_failure_with_last_cause(generation_fixture,tmp_path,recorded_video,monkeypatch):
    p,replay,inputs=await setup(generation_fixture,tmp_path,recorded_video)
    async def fails(result):
        raise IntakeTransient()
    monkeypatch.setattr(replay,'obtain',fails)
    done=await p.runtime.run(inputs.run_id)
    assert done.state==RuntimeState.FAILED and done.last_result.code=='MEDIA_INTAKE_RETRY_EXHAUSTED'
    assert done.last_result.recovery_class==RecoveryClass.HARD_BLOCK
    assert checkpoint(p,inputs).progress.intake_attempts==3
    assert checkpoint(p,inputs).progress.intake_last_code=='MEDIA_INTAKE_TRANSIENT'
    assert len(submissions(replay))==1


@pytest.mark.asyncio
@pytest.mark.parametrize('status',[400,401,403,422,503])
async def test_formal_media_query_preserves_read_vs_identity_auth_failures(tmp_path,monkeypatch,video,status):
    service=MediaService(video)
    handler=service.handler
    def unavailable(request):
        if request.url.path=='/media/list':
            return httpx.Response(status,json={'code':'UNAUTHORIZED' if status==401 else 50000})
        return handler(request)
    service.handler=unavailable
    p,package,service,calls=formal_load(tmp_path,monkeypatch,video,service=service)
    done=await prepare_goal(p,package,task_for(p,package))
    expected=RuntimeState.WAITING_EXTERNAL if status==503 else RuntimeState.FAILED
    assert done.state==expected,done
    assert done.last_result.recovery_class==(RecoveryClass.WAIT_EXTERNAL if status==503 else RecoveryClass.HARD_BLOCK)
    cp=p.execution.store.checkpoint(next(r for r in done.last_result.artifact_refs if r.owner=='execution-operation'))
    assert cp.progress.intake_media and cp.progress.intake_attempts==1
    assert service.imports==0 and sum(c.method=='POST' for c in calls)==1
    assert cp.progress.media_last_code


@pytest.mark.asyncio
async def test_import_claim_waits_same_source_without_second_import_or_download(tmp_path,monkeypatch,video):
    service=MediaService(video)
    handler=service.handler
    imports=[]
    def ambiguous(request):
        if request.url.path=='/media/import':
            imports.append(request)
            raise httpx.ReadTimeout('Synthetic lost multipart ACK',request=request)
        return handler(request)
    service.handler=ambiguous
    p,package,_,calls=formal_load(tmp_path,monkeypatch,video,service=service)
    waiting=await prepare_goal(p,package,task_for(p,package))
    assert waiting.state==RuntimeState.WAITING_EXTERNAL and waiting.last_result.recovery_class==RecoveryClass.WAIT_EXTERNAL
    for _ in range(2):
        waiting=await p.resume_execution_run(waiting.run_id)
    assert len(imports)==1 and sum(c.method=='POST' for c in calls)==1
    cp=p.execution.store.checkpoint(next(r for r in waiting.last_result.artifact_refs if r.owner=='execution-operation'))
    assert cp.progress.intake_attempts==1


@pytest.mark.asyncio
async def test_canonical_cache_and_index_recover_exact_human_review_unit(tmp_path,monkeypatch,video):
    p,package,service,calls=formal_load(tmp_path,monkeypatch,video)
    waiting=await prepare_goal(p,package,task_for(p,package))
    assert waiting.state==RuntimeState.WAITING_USER and waiting.last_result.recovery_class==RecoveryClass.USER_DECISION
    video_ref=next(r for r in waiting.last_result.artifact_refs if r.owner=='media-binding')
    binding=p.execution.store.get(video_ref,MediaBinding)
    # Lose derived lookup/cache only; immutable registration and Media are retained.
    with p.ledger.transaction(write=True) as db:
        db.execute("DELETE FROM ledger_index WHERE index_type='formal-media-current'")
    p.execution.media.path(binding.media).unlink()
    await p.execution.media.restore(waiting.scope,binding.media)
    assert service.downloads==1 and service.imports==1
    assert hashlib.sha256(p.execution.media.path(binding.media).read_bytes()).hexdigest()==binding.media.content_hash
    op,_,_=p.execution._approved(CapabilityInput(run_id=waiting.run_id,operation_id='review',scope=waiting.scope))
    context=p.execution.review_context(op,binding.media,binding.canonical_media_ref)
    response=ReviewResponse('REVISE',(ReviewObservation(code='PERFORMANCE_REVIEW',owner='PERFORMANCE',
        finding='Physical performance requires scoped revision.',required_revision='Revise the selected operation performance projection.'),))
    done=await p.provide_human_media_review(waiting.run_id,media_ref=video_ref,context_hash=context,response=response)
    assert done.state==RuntimeState.SUCCEEDED
    assert sum(c.method=='POST' for c in calls)==1
    assert p.execution.store.get(p.execution.store.checkpoint(op.artifact_reference()).progress.video_creative_ref,
        CreativeMediaReview).outcome=='REVISE'


@pytest.mark.asyncio
async def test_mock_reviewer_cannot_formal_pass_and_technical_failure_is_not_capability_wait(tmp_path,monkeypatch,video):
    p,package,service,calls=formal_load(tmp_path,monkeypatch,video)
    p.execution.reviewer=MockReviewer()
    failed=await prepare_goal(p,package,task_for(p,package))
    assert failed.state==RuntimeState.FAILED and failed.last_result.code=='FORMAL_MOCK_REVIEW_FORBIDDEN'
    assert sum(c.method=='POST' for c in calls)==1
    # Same physical media with wrong requested duration remains a Technical Media Failure.
    operation,_,_=p.execution._approved(CapabilityInput(run_id=failed.run_id,operation_id='review',scope=failed.scope))
    cp=p.execution.store.checkpoint(operation.artifact_reference())
    original=p.execution._technical
    def failed_qa(*args,**kwargs):
        result=original(*args,**kwargs)
        return TechnicalMediaReview.seal(**{**result.model_dump(exclude={'fingerprint'}),'outcome':'FAIL',
            'findings':('RESULT_DURATION_MISMATCH',)})
    monkeypatch.setattr(p.execution,'_technical',failed_qa)
    # Prior PASS is immutable; directly verify a new QA result is classified using original media.
    with p.ledger.transaction(write=True) as db:
        progress=cp.progress.model_dump(mode='json',by_alias=True)
        progress['videoTechnicalRef']=None
        db.execute('UPDATE production_operation SET progress_json=? WHERE operation_id=?',(json.dumps(progress),cp.operation_ref.artifact_ref))
    result=await p.execution.review(CapabilityInput(run_id=failed.run_id,operation_id='review',scope=failed.scope))
    assert result.code=='TECHNICAL_MEDIA_FAILURE' and result.recovery_class==RecoveryClass.HARD_BLOCK
    assert sum(c.method=='POST' for c in calls)==1

@pytest.mark.asyncio
async def test_expired_native_cost_terms_wait_before_operation_reservation(tmp_path,monkeypatch,video):
    """A temporary cost receipt never grants stale terms a paid intent."""
    from datetime import datetime,timedelta,timezone
    from drama_plugin.contracts.base import sha256_canonical
    from drama_plugin.contracts.video import CostEstimate
    from drama_plugin.execution.live_transport import FinancialTerms
    from drama_plugin.generation.contracts import FinalPromptArtifact
    p,package,_,calls=formal_load(tmp_path,monkeypatch,video)
    fixed=await prepare_goal(p,package,task_for(p,package))
    prep=p.generation_artifacts.get(p.generation_artifacts.prepared(fixed.run_id),GenerationPreparation)
    final=p.generation_artifacts.get(prep.final_prompt_ref,FinalPromptArtifact)
    now=datetime.now(timezone.utc)
    digest=sha256_canonical(TargetHttpTransport.preview(prep,final))
    quote=CostEstimate(amount=1,currency='CNY',source='OFFLINE_CONTRACT_ONLY_NOT_REAL_QUOTE',
        checked_at=now,expires_at=now+timedelta(minutes=10),request_fingerprint=digest)
    terms=FinancialTerms(preparation_ref=prep.artifact_reference(),wire_payload_hash=digest,
        profile=prep.task.profile,cost_quote=quote,budget_microunits=1000000)
    from drama_plugin.execution.contracts import Authorization,ExecutionInput
    from drama_plugin.persistence.review import UserDecisionRecord
    from drama_plugin.runtime.contracts import DecisionCategory
    # This isolated admission unit uses another temporary execution scope; fixed
    # owner bytes and exact preparation are read, never reauthored or overwritten.
    run=p.runtime.draft_run(work_id=fixed.scope.work_id,scene_id=fixed.scope.scene_id,
        shot_id=fixed.scope.shot_id,mode=fixed.mode,workflow_id='package-to-reviewed-media:v2',run_id='expired-native-admission')
    p.runtime.store.create(run)
    decision=UserDecisionRecord.seal(run_id=run.run_id,scope=run.scope,decision_id=run.run_id+':cost',
        category=DecisionCategory.COST_APPROVAL,accepted=True,source_ref=prep.artifact_reference(),terms_hash=terms.fingerprint)
    p.ledger.put_artifact('user-decision',decision.artifact_reference(),run.scope,decision.fingerprint,decision)
    auth=Authorization(approval_ref=decision.artifact_reference(),authorized=True,
        budget_microunits=1000000,estimated_cost_microunits=1000000,execution_mode='CONTROLLED_LIVE')
    p.ledger.put_index('execution-input',run.run_id,ExecutionInput(preparation_ref=prep.artifact_reference(),
        authorization=auth,route='seedance'),scope=run.scope,once=True)
    transport=p.execution.transports['seedance']
    p.execution.transports['seedance']=TargetHttpTransport(transport.adapter,tmp_path/'acks',ledger=p.ledger)
    expired=terms.model_copy(update={'cost_quote':quote.model_copy(update={'expires_at':now-timedelta(seconds=1)})})
    p.ledger.put_index('media-proof-cost-terms',run.run_id,expired,scope=run.scope)
    result=await p.execution.execute(CapabilityInput(run_id=run.run_id,operation_id='admission',scope=run.scope))
    assert result.recovery_class==RecoveryClass.USER_DECISION and result.external_ref==prep.artifact_reference()
    assert sum(c.method=='POST' for c in calls)==1  # only the earlier offline fixture
    with p.ledger.transaction() as db:
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='execution-operation' AND json_extract(body_json,'$.runId')=?",(run.run_id,)).fetchone()[0]==0
        assert db.execute("SELECT count(*) FROM production_operation WHERE operation_ref_json IS NOT NULL AND run_id=?",(run.run_id,)).fetchone()[0]==0
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='controlled-live-grant'").fetchone()[0]==0

@pytest.mark.asyncio
async def test_formal_storage_failure_waits_existing_import_claim_without_reupload(tmp_path,monkeypatch,video):
    service=MediaService(video)
    handler=service.handler
    imports=[]
    def storage_error(request):
        if request.url.path=='/media/import':
            imports.append(request)
            return httpx.Response(422,json={'code':42202})
        return handler(request)
    service.handler=storage_error
    p,package,_,calls=formal_load(tmp_path,monkeypatch,video,service=service)
    waiting=await prepare_goal(p,package,task_for(p,package))
    assert waiting.state==RuntimeState.WAITING_EXTERNAL
    assert waiting.last_result.recovery_class==RecoveryClass.WAIT_EXTERNAL
    assert p.execution.store.checkpoint(waiting.last_result.external_ref).progress.media_last_code=='FORMAL_MEDIA_STORAGE_ERROR'
    await p.resume_execution_run(waiting.run_id)
    assert len(imports)==1 and sum(c.method=='POST' for c in calls)==1

@pytest.mark.asyncio
async def test_malformed_import_ack_has_safe_dto_field_diagnostic_and_no_second_upload(tmp_path,monkeypatch,video):
    service=MediaService(video)
    handler=service.handler
    uploads=[]
    def malformed(request):
        if request.url.path=='/media/import':
            uploads.append(request)
            return httpx.Response(200,json={'id':{'credential':'DO-NOT-RETAIN'},'work_id':'fixture'})
        return handler(request)
    service.handler=malformed
    p,package,_,calls=formal_load(tmp_path,monkeypatch,video,service=service)
    waiting=await prepare_goal(p,package,task_for(p,package))
    assert waiting.state==RuntimeState.WAITING_EXTERNAL and waiting.last_result.recovery_class==RecoveryClass.WAIT_EXTERNAL
    # Inspect the existing bounded diagnostics family without response inputs.
    with p.ledger.transaction() as db:
        bodies=[row[0] for row in db.execute("SELECT body_json FROM immutable_artifact WHERE artifact_type='execution-diagnostic'").fetchall()]
    assert any('FORMAL_MEDIA_DTO:id:string_type' in body for body in bodies)
    assert all('DO-NOT-RETAIN' not in body and 'credential' not in body for body in bodies)
    await p.resume_execution_run(waiting.run_id)
    assert len(uploads)==1 and sum(c.method=='POST' for c in calls)==1

@pytest.mark.asyncio
async def test_known_native_task_reconciles_after_current_route_policy_changes(tmp_path,monkeypatch,video):
    from drama_plugin.config.video_route import VideoRoutePolicy
    p,package,_,calls=formal_load(tmp_path,monkeypatch,video)
    transport=p.execution.transports['seedance']
    known_calls=[]
    def running(request):
        known_calls.append(request)
        return httpx.Response(200,json={'id':'frozen-native-task','status':'running'})
    transport.adapter.client=httpx.AsyncClient(transport=httpx.MockTransport(running))
    waiting=await prepare_goal(p,package,task_for(p,package))
    assert waiting.state==RuntimeState.WAITING_EXTERNAL and len(known_calls)==1
    # No new paid authorization: the existing exact task can still be queried.
    p.execution.operations.policy=VideoRoutePolicy(provider='vidu')
    restored=TargetHttpTransport(transport.adapter,tmp_path/'acks',ledger=p.ledger,qualification_only=True)
    p.execution.transports['seedance']=restored
    result=await p.execution.execute(CapabilityInput(run_id=waiting.run_id,operation_id='same-query',scope=waiting.scope))
    assert result.recovery_class==RecoveryClass.WAIT_EXTERNAL
    assert sum(c.method=='POST' for c in known_calls)==1
    assert sum(c.method=='GET' for c in known_calls)==1
    cp=p.execution.store.checkpoint(result.external_ref)
    assert cp.progress.query_attempts==1
    assert p.execution.store.get(cp.receipt_ref,ProviderReceipt).remote_identity=='frozen-native-task'

@pytest.mark.asyncio
async def test_missing_formal_native_owner_credential_hard_blocks_before_import_claim(tmp_path,monkeypatch,video):
    p,package,service,calls=formal_load(tmp_path,monkeypatch,video)
    p.providers.media.http.config=p.providers.media.http.config.model_copy(update={'api_token':None})
    blocked=await prepare_goal(p,package,task_for(p,package))
    assert blocked.state==RuntimeState.FAILED and blocked.last_result.recovery_class==RecoveryClass.HARD_BLOCK
    assert blocked.last_result.code=='FORMAL_MEDIA_NATIVE_OWNER_AUTHENTICATION_ABSENT'
    assert service.imports==0 and sum(c.method=='POST' for c in calls)==1
    assert not list((tmp_path/'ledger.sqlite.formal-media-refs').glob('*.claim'))

@pytest.mark.asyncio
async def test_fresh_readonly_factory_recovers_paid_native_task_under_changed_policy(tmp_path,monkeypatch,video):
    from drama_plugin.execution.live_transport import configured_http_transport
    from drama_plugin.execution.transport import DefinitelyNotSubmitted,CapabilityAbsent
    from drama_plugin.config.video_route import VideoRoutePolicy
    p,package,_,calls=formal_load(tmp_path,monkeypatch,video)
    run=await prepare_goal(p,package,task_for(p,package),offline=False)
    prep=p.generation_artifacts.get(p.generation_artifacts.prepared(run.run_id),GenerationPreparation)
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),
        accepted=True,source_ref=prep.artifact_reference())
    prior=p.execution.transports['seedance']
    seen=[]
    def running(request):
        seen.append(request)
        return httpx.Response(200,json={'id':'native-paid-format-task','status':'running'})
    adapter=prior.adapter
    adapter.client=httpx.AsyncClient(transport=httpx.MockTransport(running))
    p.execution.transports['seedance']=TargetHttpTransport(adapter,tmp_path/'acks',ledger=p.ledger)
    waiting=await p.runtime.run(run.run_id)
    assert waiting.state==RuntimeState.WAITING_EXTERNAL,waiting.model_dump()
    inputs=CapabilityInput(run_id=run.run_id,operation_id='read-only',scope=run.scope)
    operation,request,_=p.execution._approved(inputs)
    cp=p.execution.store.checkpoint(operation.artifact_reference())
    attempt=p.execution.store.get(cp.attempt_ref,ProviderAttempt)
    env={'DRAMA_VIDEO_SEEDANCE_API_KEY':'MOCK-ONLY','DRAMA_VIDEO_MODEL_SEEDANCE_2_FAST_ENABLED':'false'}
    monkeypatch.setenv('DRAMA_VIDEO_MODEL_SEEDANCE_2_FAST_ENABLED','false')
    monkeypatch.setattr('drama_plugin.config.loader.load_config',lambda *a,**kw:
        DramaPluginConfig(video_route_policy=VideoRoutePolicy(provider='vidu')))
    with pytest.raises(ValueError,match='POLICY_CONFLICT'):
        configured_http_transport(model=operation.model,receipt_root=tmp_path/'acks',ledger=p.ledger,
            resolution='720p',aspect_ratio='16:9',environment=env)
    restored=configured_http_transport(model=operation.model,receipt_root=tmp_path/'acks',ledger=p.ledger,
        resolution='720p',aspect_ratio='16:9',environment=env,recovery_operation_ref=cp.operation_ref)
    await restored.adapter.client.aclose()
    restored.adapter.client=httpx.AsyncClient(transport=httpx.MockTransport(running))
    p.execution.transports['seedance']=restored
    recovered=await p.resume_execution_run(run.run_id)
    assert recovered.state==RuntimeState.WAITING_EXTERNAL
    assert sum(r.method=='POST' for r in seen)==1 and sum(r.method=='GET' for r in seen)==1
    with pytest.raises(DefinitelyNotSubmitted,match='READ_ONLY'):
        await restored.submit(operation,attempt,request)
    assert sum(r.method=='POST' for r in seen)==1
    # A reserved intention without a task is never eligible for this bypass.
    from drama_plugin.execution.contracts import ExecutionOperation
    unknown=ExecutionOperation.seal(**{**operation.model_dump(exclude={'fingerprint'}),
        'authorization':operation.authorization.model_copy(update={'budget_microunits':2000000})})
    other_attempt=ProviderAttempt.seal(scope=unknown.scope,run_id=unknown.run_id,source_package_ref=unknown.source_package_ref,
        operation_ref=unknown.artifact_reference(),provider='seedance',request_fingerprint='1'*64,client_identity='2'*64)
    p.execution.store.reserve(unknown,other_attempt)
    with pytest.raises(CapabilityAbsent,match='NOT_QUERYABLE'):
        configured_http_transport(model=unknown.model,receipt_root=tmp_path/'acks',ledger=p.ledger,
            resolution='720p',aspect_ratio='16:9',environment=env,recovery_operation_ref=unknown.artifact_reference())


@pytest.mark.asyncio
async def test_twice_interrupted_known_task_recovery_keeps_one_post_and_attempt_history(generation_fixture,tmp_path,recorded_video):
    p,_,inputs,calls=await http_setup(generation_fixture,tmp_path,recorded_video,
        lambda request:httpx.Response(200,json={'id':'twice-interrupted-task','status':'running'}))
    waiting=await p.runtime.run(inputs.run_id)
    assert waiting.state==RuntimeState.WAITING_EXTERNAL,waiting.model_dump()
    # Two process interruptions retain the exact execution claim and exhausted
    # outer invocation count. No model or side-effect budget is reset.
    from drama_plugin.execution.capability import EXECUTE
    from drama_plugin.runtime.contracts import ActionKind,RuntimeAction
    run=p.runtime.store.load(inputs.run_id)
    inspection=p.execution.inspect_execution(EXECUTE,inputs)
    assert inspection.completed
    interrupted=run.model_copy(update={'state':RuntimeState.RUNNING,'step_attempts':2,'wait_reason':None,
        'revision':run.revision+1,'executing_action':RuntimeAction(kind=ActionKind.CALL_CAPABILITY,capability_key=EXECUTE),
        'execution_revision':inspection.revision})
    p.runtime.store.save(interrupted,expected_revision=run.revision)
    recovered=await p.resume_execution_run(inputs.run_id)
    assert recovered.state==RuntimeState.WAITING_EXTERNAL and recovered.step_attempts==2
    run=recovered
    interrupted=run.model_copy(update={'state':RuntimeState.RUNNING,'revision':run.revision+1,'wait_reason':None,
        'executing_action':RuntimeAction(kind=ActionKind.CALL_CAPABILITY,capability_key=EXECUTE)})
    p.runtime.store.save(interrupted,expected_revision=run.revision)
    recovered=await p.resume_execution_run(inputs.run_id)
    assert recovered.state==RuntimeState.WAITING_EXTERNAL and recovered.step_attempts==2
    assert sum(r.method=='POST' for r in calls)==1
    assert checkpoint(p,inputs).progress.query_attempts==2


@pytest.mark.asyncio
async def test_cached_intake_local_io_keeps_three_commit_attempts_not_free_recovery(tmp_path,monkeypatch,video):
    p,package,service,calls=formal_load(tmp_path,monkeypatch,video)
    commits=[]
    async def unavailable(*args,**kwargs):
        commits.append(True)
        raise OSError('Synthetic local commit failure')
    monkeypatch.setattr(p.execution,'_register_media',unavailable)
    failed=await prepare_goal(p,package,task_for(p,package))
    assert failed.state==RuntimeState.FAILED and failed.last_result.code=='MEDIA_INTAKE_RETRY_EXHAUSTED'
    assert failed.last_result.recovery_class==RecoveryClass.HARD_BLOCK
    assert len(commits)==3 and failed.step_attempts==3
    inputs=CapabilityInput(run_id=failed.run_id,operation_id='intake',scope=failed.scope)
    op,_,_=p.execution._approved(inputs)
    cp=p.execution.store.checkpoint(op.artifact_reference())
    assert cp.progress.intake_media is not None and cp.progress.intake_attempts==3
    assert cp.progress.intake_last_code=='FORMAL_MEDIA_LOCAL_IO_TRANSIENT'
    denied=await p.execution.intake(inputs)
    assert denied.code=='MEDIA_INTAKE_RETRY_EXHAUSTED' and len(commits)==3
    assert service.imports==0 and sum(r.method=='POST' for r in calls)==1
    # The terminal diagnostic points to the concrete last local failure without
    # repeating the download or receiving another paid operation allowance.
    assert failed.last_result.artifact_refs


@pytest.mark.asyncio
async def test_review_cached_local_io_exhausts_three_reads_without_repeating_qa(tmp_path,monkeypatch,video):
    p,package,service,calls=formal_load(tmp_path,monkeypatch,video)
    waiting=await prepare_goal(p,package,task_for(p,package))
    inputs=CapabilityInput(run_id=waiting.run_id,operation_id='review',scope=waiting.scope)
    op,_,_=p.execution._approved(inputs)
    cp=p.execution.store.checkpoint(op.artifact_reference())
    technical_ref=cp.progress.video_technical_ref
    binding=p.execution.store.get(cp.progress.video_ref,MediaBinding)
    p.execution.media.path(binding.media).unlink()
    interrupted=waiting.model_copy(update={'state':RuntimeState.RUNNING,'wait_reason':None,'revision':waiting.revision+1})
    p.runtime.store.save(interrupted,expected_revision=waiting.revision)
    reads=[]
    async def unavailable(*args,**kwargs):
        reads.append(True)
        raise OSError('Synthetic review cache IO failure')
    def no_qa(*args,**kwargs):
        raise AssertionError('Exact retained technical QA must not be repeated')
    monkeypatch.setattr(p.execution.media,'restore',unavailable)
    monkeypatch.setattr(p.execution,'_technical',no_qa)
    failed=await p.resume_execution_run(waiting.run_id)
    assert failed.state==RuntimeState.FAILED and failed.last_result.code=='RETRY_LIMIT_REACHED'
    assert failed.last_result.recovery_class==RecoveryClass.HARD_BLOCK
    assert len(reads)==3 and failed.step_attempts==3
    cp=p.execution.store.checkpoint(cp.operation_ref)
    assert cp.progress.video_technical_ref==technical_ref and cp.progress.video_creative_ref is None
    assert service.imports==1 and sum(r.method=='POST' for r in calls)==1
    assert failed.last_result.artifact_refs


@pytest.mark.asyncio
async def test_review_canonical_503_wait_restores_same_media_after_cache_loss(tmp_path,monkeypatch,video):
    service=MediaService(video)
    original=service.handler
    unavailable=False
    queries=[]
    def handler(request):
        if request.url.path=='/media/content':
            queries.append(request.url.path)
            if unavailable:
                return httpx.Response(503,json={'message':'DO-NOT-RETAIN-SIGNED-URL-OR-CREDENTIAL'})
        return original(request)
    service.handler=handler
    p,package,service,calls=formal_load(tmp_path,monkeypatch,video,service=service)
    waiting=await prepare_goal(p,package,task_for(p,package))
    op,_,_=p.execution._approved(CapabilityInput(run_id=waiting.run_id,operation_id='review',scope=waiting.scope))
    cp=p.execution.store.checkpoint(op.artifact_reference())
    technical_ref=cp.progress.video_technical_ref
    binding=p.execution.store.get(cp.progress.video_ref,MediaBinding)
    p.execution.media.path(binding.media).unlink()
    interrupted=waiting.model_copy(update={'state':RuntimeState.RUNNING,'wait_reason':None,'revision':waiting.revision+1})
    p.runtime.store.save(interrupted,expected_revision=waiting.revision)
    unavailable=True
    pending=await p.resume_execution_run(waiting.run_id)
    assert pending.state==RuntimeState.WAITING_EXTERNAL
    assert pending.last_result.recovery_class==RecoveryClass.WAIT_EXTERNAL
    assert pending.last_result.code is None
    assert pending.last_result.external_ref==binding.canonical_media_ref
    assert service.imports==1 and sum(r.method=='POST' for r in calls)==1
    with pytest.raises(FileNotFoundError):
        p.execution.media.path(binding.media)
    # Fresh owner composition opens the same persisted checkpoint and canonical
    # identity. Retained QA and pending USER receipt remain authoritative.
    unavailable=False
    restored,_,_,_=formal_load(tmp_path,monkeypatch,video,restore=True,service=service,vendor_calls=calls)
    def no_qa(*args,**kwargs):
        raise AssertionError('Recovery must consume the exact retained QA')
    monkeypatch.setattr(restored.execution,'_technical',no_qa)
    ready=await restored.resume_execution_run(waiting.run_id)
    assert ready.state==RuntimeState.WAITING_USER and ready.last_result.recovery_class==RecoveryClass.USER_DECISION,ready.model_dump()
    recovered=restored.execution.store.checkpoint(cp.operation_ref)
    assert recovered.progress.video_ref==cp.progress.video_ref and recovered.progress.video_technical_ref==technical_ref
    assert recovered.progress.video_creative_ref is None
    assert hashlib.sha256(restored.execution.media.path(binding.media).read_bytes()).hexdigest()==binding.media.content_hash
    assert len(queries)==2 and service.downloads==1 and service.imports==1
    assert sum(r.method=='POST' for r in calls)==1
    assert b'DO-NOT-RETAIN-SIGNED-URL-OR-CREDENTIAL' not in restored.ledger.path.read_bytes()


@pytest.mark.asyncio
@pytest.mark.parametrize('locator',['http://result.invalid/clip.mp4','https://user:secret@result.invalid/clip.mp4'])
async def test_unsafe_provider_result_locator_hard_blocks_before_download(tmp_path,monkeypatch,video,locator):
    p,package,service,calls=formal_load(tmp_path,monkeypatch,video)
    observed=[]
    def vendor(request):
        observed.append(request)
        assert request.method=='POST', 'Unsafe result must not reach download transport'
        return httpx.Response(200,json={'id':'unsafe-result-task','status':'succeeded','content':{'video_url':locator}})
    p.execution.transports['seedance'].adapter.client=httpx.AsyncClient(transport=httpx.MockTransport(vendor))
    failed=await prepare_goal(p,package,task_for(p,package))
    assert failed.state==RuntimeState.FAILED and failed.last_result.code=='MEDIA_RESULT_IDENTITY_INVALID'
    assert failed.last_result.recovery_class==RecoveryClass.HARD_BLOCK
    assert len(observed)==1 and service.imports==0


@pytest.mark.asyncio
@pytest.mark.parametrize('failure',['empty','hash'])
async def test_intake_empty_or_hash_mismatch_hard_blocks_current_owner(tmp_path,monkeypatch,video,failure):
    p,package,service,calls=formal_load(tmp_path,monkeypatch,video)
    transport=p.execution.transports['seedance']
    if failure=='empty':
        async def empty(result):
            return b''
        monkeypatch.setattr(transport,'obtain',empty)
    else:
        original=transport.receipt
        def wrong_hash(*args,**kwargs):
            receipt=original(*args,**kwargs)
            return ProviderReceipt.seal(**{**receipt.model_dump(exclude={'fingerprint'}),
                'result':receipt.result.model_copy(update={'expected_hash':'a'*64})})
        monkeypatch.setattr(transport,'receipt',wrong_hash)
    failed=await prepare_goal(p,package,task_for(p,package))
    assert failed.state==RuntimeState.FAILED and failed.last_result.code=='MEDIA_RESULT_IDENTITY_INVALID'
    assert failed.last_result.recovery_class==RecoveryClass.HARD_BLOCK
    assert service.imports==0 and sum(r.method=='POST' for r in calls)==1


@pytest.mark.asyncio
async def test_missing_probe_capability_hard_blocks_current_intake(tmp_path,monkeypatch,video):
    p,package,service,calls=formal_load(tmp_path,monkeypatch,video)
    monkeypatch.setattr('drama_plugin.execution.media.shutil.which',lambda _:None)
    failed=await prepare_goal(p,package,task_for(p,package))
    assert failed.state==RuntimeState.FAILED and failed.last_result.code=='MEDIA_PROBE_ABSENT'
    assert failed.last_result.recovery_class==RecoveryClass.HARD_BLOCK
    assert service.imports==0 and sum(r.method=='POST' for r in calls)==1


@pytest.mark.asyncio
@pytest.mark.parametrize('failure',['work','shot','source','hash','duplicate'])
async def test_wrong_or_duplicate_canonical_media_hard_blocks_native_intake(tmp_path,monkeypatch,video,failure):
    from drama_plugin.contracts.media import Media
    p,package,service,calls=formal_load(tmp_path,monkeypatch,video)
    provider=p.providers.media
    if failure=='duplicate':
        async def duplicates(**kwargs):
            return [Media(id='one',work_id='wrong-work',media_type='VIDEO'),
                    Media(id='two',work_id='wrong-work',media_type='VIDEO')]
        monkeypatch.setattr(provider,'list_media',duplicates)
    else:
        original=provider.import_media
        async def wrong(**kwargs):
            media=await original(**kwargs)
            field={'work':'work_id','shot':'shot_id','source':'source_ref','hash':'content_hash'}[failure]
            return media.model_copy(update={field:'a'*64 if failure=='hash' else 'wrong-'+failure})
        monkeypatch.setattr(provider,'import_media',wrong)
    failed=await prepare_goal(p,package,task_for(p,package))
    assert failed.state==RuntimeState.FAILED and failed.last_result.code=='FORMAL_MEDIA_IDENTITY_INVALID'
    assert failed.last_result.recovery_class==RecoveryClass.HARD_BLOCK
    op,_,_=p.execution._approved(CapabilityInput(run_id=failed.run_id,operation_id='intake',scope=failed.scope))
    assert p.execution.store.checkpoint(op.artifact_reference()).progress.video_ref is None
    assert service.imports==(0 if failure=='duplicate' else 1)
    assert sum(r.method=='POST' for r in calls)==1
