"""HTTP and formal Media adapters qualified exclusively with in-process fakes."""
import hashlib
from pathlib import Path
import httpx
import pytest
from pydantic import SecretStr
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.media import Media, MediaType
from drama_plugin.execution.contracts import ExecutionOperation, ProviderAttempt, ProviderRequest, ProviderReceipt
from drama_plugin.execution.live_transport import TargetHttpTransport
from drama_plugin.execution.formal_media import FormalMediaStore
from drama_plugin.execution.transport import CapabilityAbsent, PossiblySubmitted
from drama_plugin.execution.media import probe
from drama_plugin.providers.video.adapters import SeedanceProvider
from drama_plugin.providers.video.registry import ProviderSettings
from drama_plugin.runtime.contracts import ArtifactReference, CapabilityInput, RuntimeState
from test_film_engine import load, create, approve, video, REF, Authors

async def prepared(tmp_path,monkeypatch,video):
    p,a=load(tmp_path,monkeypatch,video,authors=Authors(scenes=1,shots=1))
    await p.runtime.run(create(p).run_id)
    await approve(p,'film',p.film.store.checkpoint('film').plan_ref)
    unit=p.film.store.checkpoint('film').units[0]
    run=p.runtime.store.load(unit.execution_run_id)
    inputs=CapabilityInput(run_id=run.run_id,scope=run.scope,operation_id=run.run_id+':0')
    operation,request,_=p.execution._approved(inputs)
    checkpoint=p.execution.store.checkpoint(operation.artifact_reference())
    attempt=p.execution.store.get(checkpoint.attempt_ref,ProviderAttempt)
    return p,operation,request,attempt

async def http_prepared(tmp_path,monkeypatch,video):
    """The direct HTTP contract uses an exact Seedance identity, not Replay's."""
    p,prior,request,_=await prepared(tmp_path,monkeypatch,video)
    operation=ExecutionOperation.seal(**{**prior.model_dump(exclude={'fingerprint'}),'route':'seedance'})
    request=request.model_copy(update={'operation_ref':operation.artifact_reference()})
    attempt=ProviderAttempt.seal(scope=operation.scope,run_id=operation.run_id,
        source_package_ref=operation.source_package_ref,operation_ref=operation.artifact_reference(),
        provider='seedance',request_fingerprint=sha256_canonical(request),
        client_identity=sha256_canonical([operation.artifact_reference().model_dump(mode='json',by_alias=True),'seedance',1]))
    return p,operation,request,attempt

async def no_reference(ref):
    raise CapabilityAbsent('REFERENCE_NOT_QUALIFIED')

def adapter(handler):
    return SeedanceProvider('seedance-2-standard',ProviderSettings(api_key=SecretStr('offline-fake-key'),base_url='https://ark.cn-beijing.volces.com/api/v3'),
        resolve=no_reference,client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

@pytest.mark.asyncio
async def test_http_exact_prompt_remote_identity_and_synthetic_ack_interrupt(tmp_path,monkeypatch,video):
    p,op,request,attempt=await http_prepared(tmp_path,monkeypatch,video)
    calls=[]
    def handle(req):
        calls.append(req)
        if req.method=='POST':
            import json
            body=json.loads(req.content)
            assert body['content'][0]['text']==request.prompt_text
            return httpx.Response(200,json={'id':'real-format-task-id','status':'running'})
        return httpx.Response(200,json={'id':'real-format-task-id','status':'succeeded','content':{'video_url':'https://result.invalid/clip.mp4'}})
    transport=TargetHttpTransport(adapter(handle),tmp_path/'acks',ledger=p.ledger,qualification_only=True)
    receipt=await transport.submit(op,attempt,request)
    assert receipt.remote_identity=='real-format-task-id'
    # The execution process may lose its ACK after transport persisted the task.
    restored=TargetHttpTransport(adapter(handle),tmp_path/'acks',ledger=p.ledger,qualification_only=True)
    resolved=await restored.query(op,attempt,None)
    assert resolved.state=='SUCCEEDED' and resolved.remote_identity==receipt.remote_identity
    assert sum(r.method=='POST' for r in calls)==1
    assert all('real-format-task-id' in str(r.url) for r in calls if r.method=='GET')

@pytest.mark.asyncio
async def test_configured_credentials_do_not_authorize_live_submission(tmp_path,monkeypatch,video):
    p,op,request,attempt=await http_prepared(tmp_path,monkeypatch,video)
    calls=[]
    transport=TargetHttpTransport(adapter(lambda r:calls.append(r) or httpx.Response(200,json={})),tmp_path/'acks',ledger=p.ledger)
    with pytest.raises(CapabilityAbsent,match='GRANT_REQUIRED'):
        await transport.submit(op,attempt,request)
    assert calls==[]

@pytest.mark.asyncio
async def test_uncertain_ack_without_task_id_never_creates_second_operation(tmp_path,monkeypatch,video):
    p,op,request,attempt=await http_prepared(tmp_path,monkeypatch,video)
    calls=[]
    transport=TargetHttpTransport(adapter(lambda r:calls.append(r) or httpx.Response(200,json={'status':'running'})),tmp_path/'acks',ledger=p.ledger,qualification_only=True)
    with pytest.raises(PossiblySubmitted):
        await transport.submit(op,attempt,request)
    assert await transport.query(op,attempt,None) is None
    assert len(calls)==1

class FormalProviderFake:
    def __init__(self):
        self.records=[]
        self.imports=0
        self.crash_after_import=False
    async def list_media(self,**kwargs):
        return [m for m in self.records if m.work_id==kwargs['work_id'] and m.source_ref==kwargs['source_ref']]
    async def import_media(self,**kwargs):
        self.imports+=1
        from urllib.parse import urlsplit,unquote
        content=Path(unquote(urlsplit(kwargs['source_uri']).path)).read_bytes()
        media=Media(id='formal-media-'+str(self.imports),work_id=kwargs['work_id'],shot_id=kwargs['shot_id'],source_ref=kwargs['source_ref'],
            media_type=kwargs['media_type'],mime_type='video/mp4',file_size=len(content),content_hash=hashlib.sha256(content).hexdigest(),
            duration_ms=kwargs['duration_ms'],content=kwargs['content'])
        self.records.append(media)
        if self.crash_after_import:
            raise RuntimeError('synthetic process loss after remote canonical import')
        return media

@pytest.mark.asyncio
async def test_formal_import_crash_restore_same_canonical_identity_no_regeneration(tmp_path,monkeypatch,video):
    p,op,request,attempt=await prepared(tmp_path,monkeypatch,video)
    provider=FormalProviderFake()
    provider.crash_after_import=True
    media=p.execution.media.retain(video.read_bytes(),kind='VIDEO',mime='video/mp4')
    store=FormalMediaStore(tmp_path/'formal-cache',provider,p.execution.store)
    store.retain(video.read_bytes(),kind='VIDEO',mime='video/mp4')
    with pytest.raises(RuntimeError,match='synthetic process'):
        await store.register(media,scope=op.scope,source_ref=op.artifact_reference(),attempt_ref=attempt.artifact_reference(),package_ref=op.source_package_ref)
    restored=FormalMediaStore(tmp_path/'formal-cache',provider,p.execution.store)
    ref=await restored.register(media,scope=op.scope,source_ref=op.artifact_reference(),attempt_ref=attempt.artifact_reference(),package_ref=op.source_package_ref)
    again=await restored.register(media,scope=op.scope,source_ref=op.artifact_reference())
    assert ref==again and ref.artifact_ref=='formal-media-1' and provider.imports==1
    assert provider.records[0].content['sourceOperation']['artifactRef']==op.artifact_reference().artifact_ref
    assert provider.records[0].content['providerAttempt']['artifactRef']==attempt.artifact_reference().artifact_ref

@pytest.mark.asyncio
async def test_ambiguous_formal_import_no_blind_upload_retry(tmp_path,monkeypatch,video):
    p,op,request,attempt=await prepared(tmp_path,monkeypatch,video)
    provider=FormalProviderFake()
    provider.crash_after_import=True
    store=FormalMediaStore(tmp_path/'formal-cache',provider,p.execution.store)
    media=store.retain(video.read_bytes(),kind='VIDEO',mime='video/mp4')
    with pytest.raises(RuntimeError):
        await store.register(media,scope=op.scope,source_ref=op.artifact_reference())
    provider.records=[]
    with pytest.raises(CapabilityAbsent,match='RECONCILIATION_REQUIRED'):
        await store.register(media,scope=op.scope,source_ref=op.artifact_reference())
    assert provider.imports==1

@pytest.mark.asyncio
async def test_formal_http_multipart_wire_and_immutable_registration_refs(tmp_path,monkeypatch,video):
    from drama_plugin.config import ServiceConfig
    from drama_plugin.providers.http.client import HttpProviderClient
    from drama_plugin.providers.http.providers import HttpMediaProvider
    p,op,request,attempt=await prepared(tmp_path,monkeypatch,video)
    monkeypatch.setenv('DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS',str(tmp_path))
    records=[]
    def handler(req):
        if req.method=='GET':
            return httpx.Response(200,json=records)
        import re,json
        # Inspect the real MIME multipart framing produced by HttpMediaProvider.
        body=req.content
        assert b'Content-Type: video/mp4' in body and b'filename="' in body and b'.mp4"' in body
        metadata=json.loads(re.search(rb'name="metadata"\r\nContent-Type: application/json\r\n\r\n(.*?)\r\n--',body,re.S).group(1))
        media=Media(id='drama-service-canonical-id',work_id=metadata['work_id'],shot_id=metadata['shot_id'],source_ref=metadata['source_ref'],
            media_type=MediaType.VIDEO,mime_type='video/mp4',file_size=len(video.read_bytes()),content_hash=hashlib.sha256(video.read_bytes()).hexdigest(),
            content=metadata['content'],duration_ms=metadata['duration_ms'])
        records.append(media.model_dump(mode='json',by_alias=True))
        return httpx.Response(200,json=records[0])
    http=HttpProviderClient(ServiceConfig(base_url='https://service.invalid',operations={'list_media':'/media/list','import_media':'/media/import'}),
        client=httpx.AsyncClient(base_url='https://service.invalid',transport=httpx.MockTransport(handler)))
    store=FormalMediaStore(tmp_path/'formal-cache',HttpMediaProvider(http),p.execution.store)
    media=store.retain(video.read_bytes(),kind='VIDEO',mime='video/mp4')
    first=await store.register(media,scope=op.scope,source_ref=op.artifact_reference(),attempt_ref=attempt.artifact_reference(),package_ref=op.source_package_ref)
    second=await store.register(media,scope=op.scope,source_ref=op.artifact_reference())
    assert first==second and len(records)==1
    ref=ArtifactReference.model_validate(p.ledger.get_index('formal-media-current',op.scope.work_id+':'+media.content_hash))
    body,scope,digest=p.ledger.get_artifact('formal-media-registration',ref)
    assert body['canonicalMediaRef']['artifactRef']=='drama-service-canonical-id' and scope==op.scope

@pytest.mark.asyncio
async def test_live_quote_exact_wire_profile_budget_before_dispatch(tmp_path,monkeypatch,video):
    from datetime import datetime,timedelta,timezone
    from drama_plugin.execution.live_transport import ControlledLiveGrant
    from drama_plugin.execution.contracts import Authorization
    from drama_plugin.persistence.review import UserDecisionRecord
    from drama_plugin.runtime.contracts import DecisionCategory
    from drama_plugin.contracts.video import CostEstimate
    p,prior,request,attempt=await prepared(tmp_path,monkeypatch,video)
    decision=UserDecisionRecord.seal(run_id=prior.run_id,scope=prior.scope,decision_id=prior.run_id+':cost',
        category=DecisionCategory.COST_APPROVAL,accepted=True,source_ref=prior.preparation_ref)
    p.ledger.put_artifact('user-decision',decision.artifact_reference(),prior.scope,decision.fingerprint,decision)
    operation=ExecutionOperation.seal(**{**prior.model_dump(exclude={'fingerprint'}),'authorization':Authorization(
        approval_ref=decision.artifact_reference(),authorized=True,budget_microunits=20000,estimated_cost_microunits=10000,execution_mode='CONTROLLED_LIVE')})
    request=ProviderRequest.model_validate({**request.model_dump(),'operation_ref':operation.artifact_reference()})
    calls=[]
    transport=TargetHttpTransport(adapter(lambda r:calls.append(r) or httpx.Response(200,json={})),tmp_path/'acks',ledger=p.ledger)
    now=datetime.now(timezone.utc)
    quote=CostEstimate(amount=.01,currency='CNY',source='OFFLINE_TEST_QUOTE_NOT_A_REAL_PRICE',checked_at=now,expires_at=now+timedelta(minutes=5),
        request_fingerprint=sha256_canonical(transport.approved_payload(request)))
    grant=ControlledLiveGrant(scope=operation.scope,operation_ref=operation.artifact_reference(),decision_ref=decision.artifact_reference(),
        provider='seedance',model=operation.model,budget_microunits=20000,cost_quote=quote,resolution='720p',aspect_ratio='16:9',currency='CNY')
    transport.grant=grant
    transport._grant(operation,request)
    for changes in ({'budget_microunits':1},{'resolution':'1080p'},{'cost_quote':quote.model_copy(update={'request_fingerprint':'0'*64})},
                    {'cost_quote':quote.model_copy(update={'expires_at':now-timedelta(seconds=1)})}):
        transport.grant=ControlledLiveGrant.model_validate({**grant.model_dump(),**changes})
        with pytest.raises(ValueError):
            await transport.submit(operation,attempt,request)
    assert calls==[]
    # The native owner, not the transport, consumes the one-operation permission.
    from drama_plugin.execution.contracts import FinishingRecipe
    from drama_plugin.execution.store import OperationState
    native_id='controlled-native-execution'
    native_decision=UserDecisionRecord.seal(run_id=native_id,scope=operation.scope,decision_id=native_id+':cost',
        category=DecisionCategory.COST_APPROVAL,accepted=True,source_ref=operation.preparation_ref)
    p.ledger.put_artifact('user-decision',native_decision.artifact_reference(),operation.scope,native_decision.fingerprint,native_decision)
    recipe=p.execution.store.get(p.execution.store.inputs(prior.run_id).recipe_ref,FinishingRecipe)
    recipe=FinishingRecipe.seal(**{**recipe.model_dump(exclude={'fingerprint'}),'run_id':native_id})
    authorization=operation.authorization.model_copy(update={'approval_ref':native_decision.artifact_reference()})
    native=p.create_execution_run(run_id=native_id,mode=p.runtime.store.load(prior.run_id).mode,
        preparation_ref=operation.preparation_ref,authorization=authorization,recipe=recipe,route='seedance')
    native_calls=[]
    def native_handler(req):
        native_calls.append(req)
        return httpx.Response(200,json={'id':'native-task','status':'running'})
    native_transport=TargetHttpTransport(adapter(native_handler),tmp_path/'native-acks',ledger=p.ledger)
    p.execution.transports['seedance']=native_transport
    native_op,native_request,_=p.execution._approved(CapabilityInput(run_id=native_id,scope=native.scope,operation_id=native_id+':0'))
    native_quote=quote.model_copy(update={'request_fingerprint':sha256_canonical(native_transport.approved_payload(native_request))})
    native_grant=grant.model_copy(update={'operation_ref':native_op.artifact_reference(),'decision_ref':native_decision.artifact_reference(),'cost_quote':native_quote})
    native_transport.grant=native_grant
    waiting=await p.runtime.run(native_id)
    assert waiting.state==RuntimeState.WAITING_EXTERNAL
    assert p.execution.store.checkpoint(native_op.artifact_reference()).state==OperationState.RUNNING
    persisted=ArtifactReference.model_validate(p.ledger.get_index('execution-live-grant',native_decision.artifact_reference().artifact_ref))
    assert persisted==native_grant.artifact_reference()
    # Restore queries the saved task; the expired/absent send grant is not needed for a free query.
    p.execution.transports['seedance']=TargetHttpTransport(adapter(native_handler),tmp_path/'native-acks',ledger=p.ledger)
    await p.resume_execution_run(native_id)
    assert sum(r.method=='POST' for r in native_calls)==1
    assert any('native-task' in str(r.url) for r in native_calls if r.method=='GET')
    another=ExecutionOperation.seal(**{**native_op.model_dump(exclude={'fingerprint'}),'authorization':authorization.model_copy(update={'budget_microunits':10001})})
    another_grant=native_grant.model_copy(update={'operation_ref':another.artifact_reference()})
    p.ledger.put_artifact(another_grant.owner,another_grant.artifact_reference(),another.scope,another_grant.fingerprint,another_grant)
    with pytest.raises(ValueError):
        p.ledger.put_index('execution-live-grant',native_decision.artifact_reference().artifact_ref,another_grant.artifact_reference(),scope=another.scope,once=True)
    cross_run=ExecutionOperation.seal(**{**native_op.model_dump(exclude={'fingerprint'}),'run_id':native_id+':other'})
    native_transport.grant=native_grant.model_copy(update={'operation_ref':cross_run.artifact_reference()})
    with pytest.raises(ValueError,match='Exact cost decision'):
        native_transport._grant(cross_run,native_request.model_copy(update={'operation_ref':cross_run.artifact_reference()}))
    assert sum(r.method=='POST' for r in native_calls)==1
