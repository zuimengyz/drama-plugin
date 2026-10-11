"""Native reference chain with metadata/HTTP fixtures only; writes no media."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import base64
import json
from pathlib import Path
import httpx
import pytest
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.media import Media
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.runtime.contracts import RuntimeState, ArtifactReference, CapabilityInput
from drama_plugin.visual.frame_request import Actor, FrameSpec, compile_frame
from drama_plugin.visual.production import Review, Finding
from drama_plugin.providers.ark_image import binding
from test_asset_sequence import Author, plugin, request_for, accept_pending
from test_visual_prompt_ir import visual_ir, fact


def reference_frame(item):
    subject = item['subjectId']
    pin = SourcePin.model_validate(item['designRef'])
    actor = (Actor(entity_key=subject, label=item['name'], identity=item['design']['face'],
        costume='Approved worn wool', position='Centre', pose='Upright', action='Standing', gaze='Towards lens', visibility='FACE')
        if item['assetType']=='CHARACTER' else None)
    spec = FrameSpec(shot_id='asset-reference:'+pin.fingerprint, shot_fingerprint=pin.fingerprint,
        entry_state='One selected adult at rest',
        composition='Single-person identity proof', environment='Unobtrusive neutral backdrop',
        actors=(actor,) if actor else (), props=(), required=('Selected asset readable',),
        forbidden=('Additional people', 'Unapproved location layout'), references=(), reference_lock={},
        identity_bootstrap='First approved identity design reference' if actor else None, shot_type='SINGLE_STATIC',
        target_size=(1280,720), seed=1)
    ir=visual_ir('TEXT_TO_IMAGE', 'doubao-seedream-4-5-251128')
    # Actual selected active model, with all test art explicitly fixture-only.
    from drama_plugin.config.production_routes import selected
    ir['task'].update(provider_family=selected()['image_model'], subject_kind='CHARACTER')
    if actor:
        ir['subjects'][0].update(id=subject, face=fact(actor.identity))
    else:
        ir['subjects']=[];ir['task']['subject_kind']='SCENE';ir.pop('blocking');ir.pop('action')
    if actor:
        ir['blocking'].update(positions=fact('One selected person at centre'),
            orientation=fact('Face towards lens'), contact=fact('Hands at rest'), visible_relation=fact('Only one person'))
    ir['world']['location']=fact('Neutral identity reference backdrop')
    ir['environment'].update(architecture=fact('Neutral backdrop','IMPORTANT'),
        topology=fact('No implied room layout','IMPORTANT'), required_period_objects=fact('Approved clothing','IMPORTANT'))
    ir['camera']['framing']=fact('One person, readable face','IMPORTANT')
    if not actor:
        ir['negative_constraints']=[];ir['secondary_details']=[]
        ir['world']['location']=fact(item['name'])
        ir['environment']['architecture']=fact(item['design'].get('architecture','Neutral object proof background'),'IMPORTANT')
        ir['camera']['framing']=fact('Selected asset and its spatial relationships','IMPORTANT')
    ir['source_fingerprint']=fp(spec.model_dump(mode='json',exclude={'prompt_ir'}))
    return spec.model_copy(update={'prompt_ir':ir})


class ReferenceAuthor(Author):
    def __init__(self):
        super().__init__();self.reference_requests=[]
    async def design_asset_reference(self, request, requirement):
        self.reference_requests.append((request,requirement))
        return reference_frame(requirement)


def evidence():
    now=datetime.now(timezone.utc)
    return dict(source='OFFLINE_FIXTURE_ONLY',verified=True,checked_at=now.isoformat(),
        expires_at=(now+timedelta(minutes=5)).isoformat())


async def prepared(tmp_path, monkeypatch, author=None):
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY','OFFLINE_TEST_SECRET')
    author=author or ReferenceAuthor()
    p=plugin(tmp_path,monkeypatch,author); inp,request=request_for(p,'s-1')
    # A real registered business Work is the existing Asset/import API contract.
    # This isolated metadata fixture does not register the user's Native movie.
    p.providers.memory.data.work=p.providers.memory.data.work.model_copy(update={'id':inp.scope.work_id})
    result=await p.creative._professional(inp)
    child=next(r.artifact_ref for r in result.artifact_refs if r.owner=='runtime')
    value=p.reference_production.get(child)
    assert value.frame and value.scope.scene_id=='s-1' and value.scope.shot_id is None
    assert p.runtime.store.load(child).state==RuntimeState.WAITING_EXTERNAL
    return p,inp,child,value,author


async def quote_and_approve(p, child):
    value=p.reference_production.get(child)
    quote=dict(request_fingerprint=fp(value.frame['request']), conservative_credits=1,
        unit='CNY',uncertainty=None,evidence=evidence())
    balance=dict(available_credits=20,margin_credits=1,unit='CNY',evidence=evidence())
    await p.tools.invoke('specialized_assets.quote_reference',run_id=child,
        quote=quote,balance=balance,budget=2,execution_binding=binding(value.frame,evidence()))
    run=await p.tools.invoke('specialized_assets.resume_reference',run_id=child)
    assert run.state==RuntimeState.WAITING_USER
    value=p.reference_production.get(child)
    await p.decide_target_run(child, decision_id=p.runtime.decision_id(child),accepted=True,
        source_ref=value.artifact_reference())


def fake_submission(monkeypatch, calls):
    import drama_plugin.professional_design.reference_production as module
    async def submit(work,attempt,frame,cache):
        calls.append(deepcopy(attempt))
        assert attempt['submission_started'] and attempt['status']=='UNKNOWN'
        b=attempt['execution_binding']
        correlation={k:b[k] for k in ('execution','endpoint_fingerprint','provider_schema_fingerprint','operation')}
        correlation.update(attempt_id=attempt['attempt_id'],task_id='offline-request',request_fingerprint=fp(attempt['request']))
        return dict(status='COMPLETED',task_id='offline-request',attempt_id=attempt['attempt_id'],
            work_id=work,request_fingerprint=fp(attempt['request']),output_path='/OFFLINE_METADATA_ONLY/no-file.png',
            output_hash='a'*64,mime_type='image/png',output_bytes=120,correlation=correlation)
    monkeypatch.setattr(module,'submit_reserved',submit)


def fake_persistence(monkeypatch, p, *, fail_first=False, dimensions=None):
    import drama_plugin.professional_design.reference_production as module
    calls=[]
    async def persist(provider,expected,**kwargs):
        calls.append(expected)
        if fail_first and len(calls)==1:
            raise OSError('Offline readback interrupted')
        mid='offline-reference-'+expected.source_ref[-12:]
        rows=provider.data.media
        if not any(m.id==mid for m in rows):
            rows.append(Media(id=mid,work_id=expected.work_id,media_type='IMAGE',purpose=expected.purpose,
                source_ref=expected.source_ref,content_hash=expected.content_hash,file_size=120,mime_type='image/png',
                content={**kwargs['content'],'qualification':'OFFLINE_METADATA_FIXTURE_ONLY'}))
        width,height=dimensions or (kwargs['content']['width'],kwargs['content']['height'])
        return dict(persistenceStatus='VERIFIED',mediaId=mid,contentHash=expected.content_hash,
            sourceRef=expected.source_ref,workId=expected.work_id,mediaType='IMAGE',purpose=expected.purpose,
            technical={'implementation':'OFFLINE_METADATA_FIXTURE_ONLY','streams':[{'width':width,'height':height}]})
    async def verify(provider,expected,cache):
        calls.append(expected)
        value=p.reference_production.get(next(r for r in runs(p) if ':asset-reference:' in r))
        return dict(value.delivery)
    monkeypatch.setattr(module,'persist_media',persist)
    monkeypatch.setattr(module,'verify_media',verify)
    return calls


def runs(p):
    with p.ledger.transaction() as db:
        return [r['run_id'] for r in db.execute('SELECT run_id FROM production_run')]


async def pass_review(p,child):
    value=p.reference_production.get(child);attempt=value.stage['attempts'][0]
    review=Review(attempt_id=attempt['attempt_id'],output_hash=attempt['output_hash'],
        reviewer='OFFLINE_FIXTURE_ONLY',evidence='Metadata fixture; no visual quality claim',
        checks={'IDENTITY':'PASS','SCENE':'PASS','CROP':'PASS'})
    await p.tools.invoke('specialized_assets.review_reference',run_id=child,review=review)
    run=await p.reference_production.resume(child)
    assert run.state==RuntimeState.WAITING_USER and run.cursor==5
    return p.reference_production.get(child)


@pytest.mark.asyncio
async def test_native_reference_complete_chain_and_restart_without_media(tmp_path,monkeypatch):
    p,inp,child,value,author=await prepared(tmp_path,monkeypatch)
    assert author.reference_requests[0][0].scope.shot_id is None
    assert value.frame['spec']['actors'][0]['entity_key']=='A'
    assert value.frame['request']['tool']=='image.create'
    assert 'Distinct approved A' in value.frame['request']['body']['prompt']
    calls=[];fake_submission(monkeypatch,calls);fake_persistence(monkeypatch,p)
    await quote_and_approve(p,child)
    run=await p.reference_production.resume(child)
    assert run.state==RuntimeState.WAITING_EXTERNAL and run.cursor==4
    assert len(calls)==1 and not await p.providers.asset.list_assets()
    candidate=await pass_review(p,child)
    assert not await p.providers.asset.list_assets()  # PASS is not adoption.
    with pytest.raises(ValueError,match='exact request'):
        await p.decide_target_run(child,decision_id=p.runtime.decision_id(child),accepted=True,
            source_ref=value.artifact_reference())
    await p.decide_target_run(child,decision_id=p.runtime.decision_id(child),accepted=True,
        source_ref=candidate.artifact_reference())
    run=await p.reference_production.resume(child)
    assert run.state==RuntimeState.SUCCEEDED
    result=p.reference_production.get(child)
    asset=await p.providers.asset.get_asset(result.asset_id)
    assert asset.content['specializedAsset']['subjectId']=='A'
    assert asset.reference_media_ids==[result.delivery['mediaId']]
    assert p.asset_sequence._proof(asset)
    # Reload the actual owner against the same Ledger and originals.
    from drama_plugin.professional_design.reference_production import TargetReferenceProduction
    reloaded=TargetReferenceProduction(p)
    assert reloaded.get(child)==result
    assert (await reloaded.resume(child)).state==RuntimeState.SUCCEEDED and len(calls)==1
    assert len(await p.providers.asset.list_assets())==1
    parent=await p.creative._professional(inp)
    # Next missing LOCATION receives its own native child; A is not generated again.
    next_child=next(r.artifact_ref for r in parent.artifact_refs if r.owner=='runtime')
    assert p.reference_production.get(next_child).requirement_key != result.requirement_key
    assert p.runtime.store.load(next_child).state==RuntimeState.WAITING_EXTERNAL
    assert len(calls)==1
    assert not list(tmp_path.rglob('*.png')) and not list(tmp_path.rglob('*.mp4'))


@pytest.mark.asyncio
async def test_unknown_dispatch_is_durable_and_never_reposts(tmp_path,monkeypatch):
    p,inp,child,value,a=await prepared(tmp_path,monkeypatch)
    await quote_and_approve(p,child)
    import drama_plugin.professional_design.reference_production as module
    calls=[]
    async def timeout(work,attempt,frame,cache):
        calls.append(attempt)
        assert p.reference_production.get(child).stage['attempts'][0]['submission_started']
        raise httpx.ReadTimeout('OFFLINE_FIXTURE')
    monkeypatch.setattr(module,'submit_reserved',timeout)
    run=await p.reference_production.resume(child)
    assert run.state==RuntimeState.WAITING_EXTERNAL and run.cursor==2
    for _ in range(3):
        run=await p.reference_production.resume(child)
    assert len(calls)==1 and p.reference_production.get(child).stage['attempts'][0]['status']=='UNKNOWN'
    assert not await p.providers.asset.list_assets()


@pytest.mark.asyncio
async def test_intake_retry_uses_same_output_and_checks_dimensions(tmp_path,monkeypatch):
    p,inp,child,value,a=await prepared(tmp_path,monkeypatch)
    calls=[];fake_submission(monkeypatch,calls)
    imports=fake_persistence(monkeypatch,p,fail_first=True)
    await quote_and_approve(p,child)
    run=await p.reference_production.resume(child)
    assert run.cursor==3 and run.state==RuntimeState.WAITING_EXTERNAL
    run=await p.reference_production.resume(child)
    assert run.cursor==4 and len(calls)==1
    assert len(imports)==2 and imports[0]==imports[1]
    assert not list(tmp_path.rglob('*.png'))


@pytest.mark.asyncio
async def test_review_rejection_never_registers_or_auto_regenerates(tmp_path,monkeypatch):
    p,inp,child,value,a=await prepared(tmp_path,monkeypatch)
    calls=[];fake_submission(monkeypatch,calls);fake_persistence(monkeypatch,p)
    await quote_and_approve(p,child);await p.reference_production.resume(child)
    value=p.reference_production.get(child);attempt=value.stage['attempts'][0]
    with pytest.raises(ValueError,match='REVIEW_OUTPUT_MISMATCH'):
        await p.reference_production.review_reference(child,Review(attempt_id=attempt['attempt_id'],
            output_hash='b'*64,reviewer='OFFLINE',evidence='Wrong media',checks={'IDENTITY':'PASS'}))
    await p.reference_production.review_reference(child,Review(attempt_id=attempt['attempt_id'],
        output_hash=attempt['output_hash'],reviewer='OFFLINE',evidence='Fixture identity mismatch',
        checks={'IDENTITY':'FAIL'},findings=(Finding(category='IDENTITY',severity='MAJOR',
            evidence='Wrong selected face',remedy='REGENERATE'),)))
    assert (await p.reference_production.resume(child)).state==RuntimeState.FAILED
    assert not await p.providers.asset.list_assets() and len(calls)==1


@pytest.mark.asyncio
async def test_raw_or_wrong_identity_frame_cannot_bypass_asset_design(tmp_path,monkeypatch):
    p,inp,child,value,a=await prepared(tmp_path,monkeypatch)
    spec=FrameSpec.model_validate(value.frame['spec'])
    with pytest.raises(ValueError,match='REQUIRES_EXISTING_PROMPT_IR'):
        await p.reference_production.supply_frame(child,spec.model_copy(update={'prompt_ir':None}))
    with pytest.raises(ValueError,match='CHARACTER_BINDING'):
        await p.reference_production.supply_frame(child,spec.model_copy(update={'actors':(spec.actors[0].model_copy(update={'entity_key':'B'}),)}))
    assert not p.reference_production.get(child).stage


def test_shared_http_success_parser_writes_no_media():
    from drama_plugin.visual.ark_submission import parse_output
    # Retained legacy test response bytes, not a generated/decoded image.
    fixture=b'\x89PNG\r\n\x1a\nfixture'
    response=httpx.Response(200,headers={'x-request-id':'offline-request'},
        json={'data':[{'b64_json':base64.b64encode(fixture).decode()}]})
    data,receipt=parse_output(response,'OFFLINE_SECRET')
    assert data==fixture and receipt['output_hash']==fp_bytes(fixture)
    assert 'OFFLINE_SECRET' not in json.dumps(receipt)


def fp_bytes(value):
    import hashlib
    return hashlib.sha256(value).hexdigest()


@pytest.mark.asyncio
async def test_formal_reference_artist_receives_selected_design_and_projects_ids(tmp_path,monkeypatch):
    from test_formal_author_backends import SKILLS
    from drama_plugin.creative_engine.backends import FormalProfessionalAuthor, TextCompositionBackend
    from drama_plugin.config.text_composition import TextCompositionConfig
    p,inp,child,value,a=await prepared(tmp_path,monkeypatch)
    request,item=a.reference_requests[0]
    semantic=dump_contract(reference_frame(item))
    for key in ('shot_id','shot_fingerprint','professional_sources','references','reference_lock',
                'reference_members','edit_source','scope_context','prompt_normalization','identity_bootstrap'):
        semantic.pop(key,None)
    semantic['prompt_ir'].pop('source_fingerprint')
    for key in ('provider_family','task_type','input_mode'):
        semantic['prompt_ir']['task'].pop(key)
    semantic['actors'][0].pop('entity_key');semantic['prompt_ir']['subjects'][0].pop('id')
    wire=[]
    def handle(req):
        body=json.loads(req.content);wire.append(body)
        assert 'Distinct approved A' in json.dumps(body['messages'])
        assert 'OFFLINE_TEST_SECRET' not in json.dumps(body)
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{
            'role':'assistant','content':json.dumps(semantic)}}]})
    config=TextCompositionConfig(provider='offline-compatible',base_url='https://text.invalid/v1',
        api_key='OFFLINE_TEXT_KEY',professional_model='offline-professional-model')
    author=FormalProfessionalAuthor(TextCompositionBackend(config,transport=httpx.MockTransport(handle)),SKILLS)
    spec=await author.design_asset_reference(request,item)
    compiled=compile_frame(spec)
    assert spec.actors[0].entity_key=='A' and spec.shot_fingerprint==item['designRef']['fingerprint']
    assert spec.prompt_ir['subjects'][0]['id']=='A'
    assert compiled['request']['body']['model']==value.frame['request']['body']['model']
    assert len(wire)==1


@pytest.mark.asyncio
async def test_shared_submission_replays_http_receipt_and_legacy_host_stays_compatible(tmp_path,monkeypatch):
    from drama_plugin.visual.ark_submission import submit_reserved
    from drama_plugin.hosts.ark_image import ArkImageHost
    from types import SimpleNamespace
    p,inp,child,value,a=await prepared(tmp_path,monkeypatch)
    attempt={'attempt_id':'f'*64,'request':value.frame['request'],'status':'RESERVED','job_id':None,
        'execution_binding':binding(value.frame,evidence())}
    work=SimpleNamespace(content={'productionStage':{'attempts':[attempt]}})
    class Memory:
        async def get_work(self,id):return work
    commands=[];posts=[]
    async def operate(memory,work_id,command,payload,**kwargs):
        commands.append(command)
        if command=='begin-submission':
            attempt.update(submission_started=True,status='UNKNOWN')
    monkeypatch.setattr('drama_plugin.hosts.ark_image.operate',operate)
    monkeypatch.setattr('drama_plugin.hosts.ark_image.attempt_frame',lambda *args:value.frame)
    def handle(req):
        posts.append(json.loads(req.content))
        return httpx.Response(400,headers={'x-request-id':'offline-400'},json={'error':{'code':'InvalidParameter','message':'Offline fixture'}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        host=ArkImageHost(Memory(),tmp_path/'legacy-receipts',client=client)
        first=await host.submit(value.scope.work_id,attempt['attempt_id'])
        assert first['status']=='NOT_CREATED'
        assert await host.submit(value.scope.work_id,attempt['attempt_id'])==first
    assert commands==['begin-submission','result'] and posts==[value.frame['request']['body']]
    assert not list(tmp_path.rglob('*.png'))


@pytest.mark.asyncio
async def test_quote_requires_exact_wire_and_cannot_change_during_user_decision(tmp_path,monkeypatch):
    p,inp,child,value,a=await prepared(tmp_path,monkeypatch)
    q=dict(request_fingerprint='0'*64,conservative_credits=1,unit='CNY',evidence=evidence())
    b=dict(available_credits=20,margin_credits=1,unit='CNY',evidence=evidence())
    with pytest.raises(ValueError,match='REQUEST_QUOTE_MISMATCH'):
        await p.reference_production.quote_reference(child,quote=q,balance=b,budget=2,
            execution_binding=binding(value.frame,evidence()))
    q['request_fingerprint']=fp(value.frame['request'])
    await p.reference_production.quote_reference(child,quote=q,balance=b,budget=2,
        execution_binding=binding(value.frame,evidence()))
    await p.reference_production.resume(child)
    with pytest.raises(ValueError,match='ALREADY_PRESENTED'):
        await p.reference_production.quote_reference(child,quote=q,balance=b,budget=3,
            execution_binding=binding(value.frame,evidence()))
    assert p.reference_production.get(child).stage is None


@pytest.mark.asyncio
async def test_text_asset_without_required_reference_skips_media_and_cost(tmp_path,monkeypatch):
    from drama_plugin.professional_design.asset_sequence import AssetChoice, SceneAssetDraft, AssetPreparationPending
    class TextAuthor(Author):
        async def design_assets(self, request):
            draft=await super().design_assets(request)
            return SceneAssetDraft(assets=(*draft.assets,AssetChoice(asset_type='OTHER',name='Text material design',
                design={'material':'Approved narrative material'},reference_required=False)),rationale=draft.rationale)
    a=TextAuthor();p=plugin(tmp_path,monkeypatch,a);inp,req=request_for(p,'s-1')
    p.providers.memory.data.work=p.providers.memory.data.work.model_copy(update={'id':inp.scope.work_id})
    try:
        await p.professional_design.prepare_assets(req)
    except AssetPreparationPending as pending:
        packet=p.asset_sequence.objects.read_ref(pending.ref)
        for row in packet['requirements']:
            if not row['referenceRequired']:
                continue
            mid='offline-established-'+row['requirementKey'][:12]
            p.providers.media.data.media.append(Media(id=mid,work_id=req.scope.work_id,media_type='IMAGE',
                source_ref='OFFLINE_METADATA_FIXTURE',content_hash=fp(mid),content={'width':1024,'height':1024}))
            review=p.asset_sequence.objects.put('offline-previous-adoption:'+mid,{'decision':'ADOPT',
                'workId':req.scope.work_id,'subjectFingerprint':row['designRef']['fingerprint'],'referenceMediaIds':[mid]})
            await p.asset_sequence.accept(pending.ref,row['requirementKey'],adoption_ref=review,reference_media_ids=(mid,))
    result=await p.creative._professional(inp)
    child=next(r.artifact_ref for r in result.artifact_refs if r.owner=='runtime')
    value=p.reference_production.get(child)
    assert value.frame is None and value.stage is None and value.cost_ref is None
    assert p.runtime.store.load(child).state==RuntimeState.WAITING_USER
    await p.tools.invoke('specialized_assets.decide_reference',run_id=child,
        decision_id=p.runtime.decision_id(child),accepted=True,source_ref=value.artifact_reference())
    assert (await p.reference_production.resume(child)).state==RuntimeState.SUCCEEDED
    asset=await p.providers.asset.get_asset(p.reference_production.get(child).asset_id)
    assert not asset.reference_media_ids and p.asset_sequence._proof(asset)
    assert (await p.creative._professional(inp)).status.value=='SUCCEEDED'
    assert not list(tmp_path.rglob('*.png'))


@pytest.mark.asyncio
async def test_media_identity_drift_between_review_and_adoption_cannot_register(tmp_path,monkeypatch):
    p,inp,child,value,a=await prepared(tmp_path,monkeypatch)
    calls=[];fake_submission(monkeypatch,calls);fake_persistence(monkeypatch,p)
    await quote_and_approve(p,child);await p.reference_production.resume(child)
    value=await pass_review(p,child)
    await p.decide_target_run(child,decision_id=p.runtime.decision_id(child),accepted=True,
        source_ref=value.artifact_reference())
    for index,row in enumerate(p.providers.media.data.media):
        if row.id==value.delivery['mediaId']:
            p.providers.media.data.media[index]=row.model_copy(update={'content_hash':'b'*64})
    assert (await p.reference_production.resume(child)).state==RuntimeState.FAILED
    assert not await p.providers.asset.list_assets() and len(calls)==1


@pytest.mark.asyncio
async def test_absent_business_work_stops_before_spending_or_submission(tmp_path,monkeypatch):
    p,inp,child,value,a=await prepared(tmp_path,monkeypatch)
    p.providers.memory.data.work=p.providers.memory.data.work.model_copy(update={'id':'unrelated-work'})
    q=dict(request_fingerprint=fp(value.frame['request']),conservative_credits=1,unit='CNY',evidence=evidence())
    b=dict(available_credits=20,margin_credits=1,unit='CNY',evidence=evidence())
    await p.reference_production.quote_reference(child,quote=q,balance=b,budget=2,
        execution_binding=binding(value.frame,evidence()))
    run=await p.reference_production.resume(child)
    value=p.reference_production.get(child)
    assert run.state==RuntimeState.WAITING_EXTERNAL
    assert value.required_action=='FORMAL_ASSET_WORK_SCOPE_REQUIRED'
    assert value.cost_ref is None and value.stage is None and not await p.providers.asset.list_assets()
