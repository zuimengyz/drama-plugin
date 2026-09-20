"""Offline official API fixtures; no live calls or artistic quality claims."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
import httpx
import pytest
from drama_plugin.contracts.video import VideoRequest, VideoReference, ProviderTask
from drama_plugin.providers.video.adapters import ADAPTERS
from drama_plugin.providers.video.registry import registry, settings, ProviderSettings, validate_request, capability_errors, continuity_errors
from drama_plugin.hosts.http_video import VideoProviderHost, candidate, compile_request, cost_metrics
from drama_plugin.visual.video_selection import Requirements, Evidence, Cost, Quality, ProductionRoute, seal_decision, qualify
from drama_plugin.visual.execution import ExecutionRoute
from drama_plugin.hosts.route_production import save_route, operate
from test_video_selection import evidence, quote
from test_media_delivery import setup
from test_performance_native_mix import sounds

MODELS={'seedance':'seedance-2-mini','minimax':'minimax-h3','vidu':'vidu-q3-turbo','wan':'wan-3-video-prime','kling':'kling-3'}
BASES={'wan':'https://test-workspace.ap-southeast-1.maas.aliyuncs.com/api/v1','kling':'https://api-singapore.klingai.com'}


def request(provider='seedance', **changes):
    r=dict(prompt='An empty ancient courtyard in soft morning light.',inputMode='text_to_video',duration=5,
        resolution='768p' if provider=='minimax' else '720p',aspectRatio='16:9',nativeAudio=True,
        continuity=dict(workId='W',segmentId='C1',revision='1',sources=[dict(key='canon:1',kind='CANON',fingerprint='a'*64)],
            locationIdentity='stone courtyard',timeOfDay='morning',weather='clear',lighting='soft sun',
            style=dict(visualRoute='stylized_cinematic_cg',revision='1',medium='DESIGNED_CG',rendering='cinematic CG',
                castingCriteria=['designed silhouettes'],shapeLanguage='natural proportions',materialPalette='matte stone',
                cameraGrammar='fixed shot',performanceGrammar='restrained',historicalBoundary='no modern objects',forbiddenDrifts=['photographic recast']),
            colorLanguage='warm grey',lensLanguage='normal lens',primaryProvider=provider,primaryModel=MODELS[provider]))
    r.update(changes)
    return VideoRequest.model_validate(r)


def ref(id='ref1',kind='image',semantics=('identity',),duration=None):
    return VideoReference(media_id=id,version='1',content_hash='b'*64,kind=kind,semantics=semantics,review_ref='approved:1',
                          width=1280,height=720,duration=duration)


def config(provider):
    return ProviderSettings(api_key='OFFLINE_SECRET_NEVER_LOG',base_url=BASES.get(provider,registry()['providers'][provider]['base_url']))


async def resolve(ref): return 'https://media.example.test/'+ref.media_id


def response(provider, state='succeeded',id='job1',url='https://cdn.example.test/result.mp4'):
    if provider=='seedance':return dict(id=id,status=state,created_at=1789990000,updated_at=1789990020,content={'video_url':url},usage={'total_tokens':100})
    if provider=='minimax':return {'task':dict(id=id,status=state,content={'url':url},usage={'output_seconds':5})}
    if provider=='vidu':return dict(id=id,state='success' if state=='succeeded' else state,creations=[{'url':url,'video':{'duration':5,'fps':24}}],credits=3)
    if provider=='wan':return dict(output=dict(task_id=id,task_status=state.upper(),video_url=url),usage={'output_video_duration':5,'fps':30})
    return dict(code=0,data=[dict(id=id,status=state,outputs=[dict(type='video',url=url,duration='5')],billing=[dict(charge_type='cash',amount='.1',currency='USD')])])


def created(provider):
    if provider=='seedance':return {'id':'job1'}
    if provider=='minimax':return {'task_id':'job1'}
    if provider=='vidu':return {'task_id':'job1','state':'created'}
    if provider=='wan':return {'output':{'task_id':'job1','task_status':'PENDING'}}
    return {'code':0,'data':{'id':'job1','status':'submitted'}}


@pytest.mark.parametrize('provider',MODELS)
async def test_shared_lifecycle_and_official_wire_contract(provider):
    calls=[]
    def handler(req):
        calls.append(req)
        return httpx.Response(200,json=created(provider) if req.method=='POST' else response(provider))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        p=ADAPTERS[provider](MODELS[provider],config(provider),resolve=resolve,client=client)
        t=await p.create_task(request(provider),client_request_id='attempt1')
        assert t.status=='QUEUED' and t.provider_task_id=='job1'
        t=await p.get_task(t)
        assert t.status=='SUCCEEDED' and t.output_url.endswith('result.mp4')
        assert 'outputUrl' not in t.durable() and await p.cancel_task(t) is None
        assert p.estimate_cost(request(provider)) is None
    body=json.loads(calls[0].content)
    assert calls[0].headers['Authorization']==('Token ' if provider=='vidu' else 'Bearer ')+'OFFLINE_SECRET_NEVER_LOG'
    assert 'An empty ancient courtyard' in json.dumps(body)
    assert 'DESIGNED_CG' in json.dumps(body) and 'no modern objects' in json.dumps(body)
    if provider=='minimax':assert body['model']=='MiniMax-H3' and body['resolution']=='768P' and calls[1].url.path=='/v2/query/video_generation/job1'
    if provider=='wan':assert calls[0].headers['X-DashScope-Async']=='enable' and body['parameters']['prompt_extend'] is False
    if provider=='kling':assert calls[0].url.path=='/text-to-video/kling-3.0' and calls[1].url.params['task_ids']=='job1' and t.actual_cost==.1
    if provider=='vidu':assert t.actual_cost is None and t.usage['credits']==3


@pytest.mark.parametrize('provider',MODELS)
@pytest.mark.parametrize('failure',['timeout','503','429','failed'])
async def test_bounded_transient_and_ambiguous_submission(provider,failure,monkeypatch):
    async def instant(_):pass
    monkeypatch.setattr('drama_plugin.providers.video.base.asyncio.sleep',instant)
    posts=0;gets=0
    def handler(req):
        nonlocal posts,gets
        if req.method=='POST':
            posts+=1
            if failure=='timeout':raise httpx.ReadTimeout('raw secret OFFLINE_SECRET_NEVER_LOG')
            if failure in {'503','429'}:return httpx.Response(int(failure),text='OFFLINE_SECRET_NEVER_LOG')
            return httpx.Response(200,json=created(provider))
        gets+=1
        if not req.url.params.get('task_ids') and provider=='kling' and failure!='failed':return httpx.Response(200,json={'data':[]})
        if gets==1:return httpx.Response(502,text='transient')
        return httpx.Response(200,json=response(provider,'failed'))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        p=ADAPTERS[provider](MODELS[provider],config(provider),resolve=resolve,client=c)
        t=await p.create_task(request(provider),client_request_id='same')
        if failure in {'timeout','503'}:assert t.status=='UNKNOWN' and posts==1 and not t.retryable
        elif failure=='429':assert t.status=='NOT_CREATED' and posts==3
        else:
            t=await p.get_task(t);assert t.status=='FAILED' and posts==1 and gets==2
        assert 'OFFLINE_SECRET_NEVER_LOG' not in json.dumps(t.durable())


async def test_kling_timeout_reconciles_external_id_without_recreate():
    calls=[]
    def handler(req):
        calls.append(req)
        if req.method=='POST':raise httpx.ReadTimeout('lost')
        return httpx.Response(200,json={'code':0,'data':[dict(id='accepted',external_id='stable',status='processing')]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        p=ADAPTERS['kling'](MODELS['kling'],config('kling'),resolve=resolve,client=c)
        t=await p.create_task(request('kling'),client_request_id='stable')
        assert t.provider_task_id=='accepted' and t.status=='RUNNING' and len(calls)==2
        assert calls[1].url.params['external_task_ids']=='stable'


@pytest.mark.parametrize('provider',MODELS)
def test_unconfigured_provider_is_optional_and_endpoint_official(provider):
    assert settings({})[provider].status(provider)=='NOT_CONFIGURED'
    assert config(provider).status(provider)=='READY'
    assert ProviderSettings(api_key='secret',base_url='https://unofficial.example').status(provider)=='INVALID_ENDPOINT'
    assert 'OFFLINE_SECRET_NEVER_LOG' not in repr(config(provider))


def with_refs(r,refs,**changes):
    pack=r.continuity.model_copy(update={'references':tuple(refs),'required_reference_ids':tuple(x.media_id for x in refs)})
    return VideoRequest.model_validate(r.model_copy(update={'continuity':pack,**changes}).model_dump())


@pytest.mark.parametrize('provider',['seedance','minimax','wan','vidu'])
def test_reference_combinations_and_no_dropped_native_audio(provider):
    r=request(provider);first=ref();extra=ref('costume',semantics=('costume',))
    r=with_refs(r,[first,extra],input_mode='image_to_video',first_frame=first,reference_images=(extra,))
    assert 'ENDPOINT_REFERENCE_MODES_EXCLUSIVE' in capability_errors(r,MODELS[provider])
    if provider=='minimax':assert 'UNSUPPORTED_NATIVE_AUDIO' in capability_errors(request(provider,nativeAudio=False),MODELS[provider])
    if provider=='vidu':
        r=with_refs(request(provider),[ref('motion','video',('motion',),5)],input_mode='reference',reference_videos=(ref('motion','video',('motion',),5),))
        assert 'REFERENCE_COUNT_EXCEEDED' in capability_errors(r,MODELS[provider])


def test_continuity_lock_cannot_be_bought_out_and_reference_truth():
    r=request('seedance');a=ref();r=with_refs(r,[a],input_mode='reference',reference_images=(a,))
    assert 'SWITCH_REQUIRES_BOUNDARY_AND_CAPABILITY_GAP' in continuity_errors(r,'vidu','vidu-q3-turbo')
    r.switch_evidence=dict() if False else None
    from drama_plugin.contracts.video import SwitchEvidence
    r.switch_evidence=SwitchEvidence(primary_capability_gap='cheaper',evidence_ref='claim',at_shot_boundary=True)
    assert 'PRIMARY_CAPABILITY_GAP_NOT_PROVEN' in continuity_errors(r,'vidu','vidu-q3-turbo')
    r.reference_images=(a.model_copy(update={'content_hash':'c'*64}),)
    assert 'NON_CANONICAL_REFERENCE' in continuity_errors(r,'seedance',MODELS['seedance'])


def test_wan_long_take_switch_requires_same_visual_bridge():
    r=request('seedance',duration=25);a=ref();r=with_refs(r,[a],input_mode='reference',reference_images=(a,))
    from drama_plugin.contracts.video import SwitchEvidence
    r.switch_evidence=SwitchEvidence(primary_capability_gap='UNSUPPORTED_DURATION',evidence_ref='registry duration 4-15',at_shot_boundary=True)
    assert not capability_errors(r,'wan-3-video') and not continuity_errors(r,'wan','wan-3-video')
    r.continuity.accepted_previous_shot='previous';r.continuity.accepted_previous_last_frame=ref('last')
    assert 'PREVIOUS_ACCEPTED_FRAME_BRIDGE_REQUIRED' in continuity_errors(r,'wan','wan-3-video')


def test_registry_all_requested_models_and_specialist_roles():
    d=registry()
    assert set(ADAPTERS)=={'seedance','minimax','vidu','wan','kling'}
    assert len(d['models'])==12
    assert d['providers']['comfy_cloud']['role']==['image_primary','video_fallback','experimental_video']
    assert d['providers']['kling']['role']==['specialist']


async def formal_setup(x,client):
    r=request('seedance');r.continuity.work_id=x.data.work.id
    x.data.work.content['continuityPacks']={'C1':r.continuity.model_dump(mode='json',by_alias=True)}
    req=Requirements(work_id=x.data.work.id,scene_id=x.data.scene.id,shot_id=x.data.shot.id,target_id='clip1',shot_type='ENVIRONMENT',
        source_fingerprint='a'*64,mode='TEXT_TO_VIDEO',controls=['TEXT'],duration_seconds=5,aspect_ratio='16:9',sound='NATIVE',
        frozen_creative={'motion_prompt':r.prompt},inputs=[],video_request=r,required=['courtyard'],forbidden=['modern objects'])
    c=candidate(req,MODELS['seedance'],cost=Cost(components={'video':20,'audio':0,'references':0,'addons':0,'correction':0},evidence=evidence()),
                evidence=Evidence.model_validate(evidence()),quality=Quality())
    ex=ExecutionRoute(transport='HTTP',backend={'provider':'seedance','backend_key':'official'},capability={'kind':'video_generation','model_key':c.model})
    route=ProductionRoute(route_id='http1',work_id=x.data.work.id,stage_id='stage1',creative_fingerprint='a'*64,
        video_targets=['clip1'],candidate=c,execution=ex,requirements=dict(controls=['TEXT'],duration_seconds=5,aspect_ratio='16:9',
        sound='NATIVE',shot_type='ENVIRONMENT',video_requests={'clip1':r.model_dump(mode='json',by_alias=True)},shots={'clip1':x.data.shot.id}),
        quality_thresholds={'continuity':'source preserved'},stops=['one paid call'],fallback='recover original',
        generations_per_video_request=1,generation_count_evidence=evidence(),video_request_credits=10,max_video_attempts=1)
    await save_route(x.memory,x.data.work.id,route.model_dump(mode='json'))
    await operate(x.memory,x.data.work.id,'init-stage',dict(authorization_ref='OFFLINE TEST',budget_credits=30))
    decision=seal_decision(req,c,compile_request(req,c),stage_id='stage1',rationale='offline',comparisons=[],fallback='recover',production_route=route)
    await operate(x.memory,x.data.work.id,'add-frame',{'frame':decision})
    h=VideoProviderHost(x.memory,x.store,x.asset,x.tmp/'http-cache',configuration={'seedance':config('seedance')},http_client=client,download_client=client)
    binding=await h.bind(x.data.work.id,decision)
    result=await operate(x.memory,x.data.work.id,'reserve',dict(shot_id='clip1',execution_binding=binding,**quote(decision,20)))
    return h,result['result']['attempt_id']


async def test_formal_http_full_media_closure_and_expired_url_resume(setup):
    x=setup;posts=[];downloads=0
    def handler(req):
        nonlocal downloads
        if req.url.host=='cdn.example.test':
            downloads+=1
            assert 'authorization' not in req.headers
            return httpx.Response(403) if downloads==1 else httpx.Response(200,content=x.video.read_bytes())
        if req.method=='POST':posts.append(req);return httpx.Response(200,json=created('seedance'))
        return httpx.Response(200,json=response('seedance'))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        h,id=await formal_setup(x,client)
        await h.submit(x.data.work.id,id)
        with pytest.raises(ValueError,match='RECOVER'):await h.submit(x.data.work.id,id)
        result=await h.poll(x.data.work.id,id)
        assert result.output_media_id and result.output_url is None
        assert (await h.poll(x.data.work.id,id)).output_media_id==result.output_media_id
    assert len(posts)==1 and downloads==2 and x.store.imports==1 and x.store.reads>=1
    work=await x.memory.get_work(x.data.work.id)
    state=work.content['productionStage'];a=state['attempts'][0]
    assert a['persistence_status']=='VERIFIED' and a['content_status']=='PENDING_REVIEW' and a['user_adoption']=='PENDING'
    assert 'https://cdn.example.test' not in json.dumps(work.content)
    assert cost_metrics(state['attempts'])[0]['cost_per_accepted_shot'] is None


async def test_formal_unknown_submission_never_recreates(setup):
    x=setup;posts=[]
    def handler(req):
        if req.method=='POST':posts.append(req);raise httpx.ReadTimeout('uncertain')
        raise AssertionError('No undocumented lookup')
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        h,id=await formal_setup(x,client)
        assert (await h.submit(x.data.work.id,id)).status=='UNKNOWN'
        assert (await h.poll(x.data.work.id,id)).status=='UNKNOWN'
        with pytest.raises(ValueError,match='RECOVER'):await h.submit(x.data.work.id,id)
    assert len(posts)==1 and x.store.imports==0

@pytest.mark.parametrize('provider',MODELS)
async def test_first_last_frame_wire_mapping(provider):
    r=request(provider);a,b=ref('first'),ref('last')
    r=with_refs(r,[a,b],input_mode='first_last_frame',first_frame=a,last_frame=b)
    calls=[]
    def handler(req): calls.append(req);return httpx.Response(200,json=created(provider))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        p=ADAPTERS[provider](MODELS[provider],config(provider),resolve=resolve,client=client)
        assert (await p.create_task(r,client_request_id='pair')).provider_task_id=='job1'
    body=json.loads(calls[0].content)
    if provider in {'seedance','minimax'}:assert [x['role'] for x in body['content'][1:]]==['first_frame','last_frame']
    elif provider=='vidu':assert calls[0].url.path=='/ent/v2/start-end2video' and body['images']==['https://media.example.test/first','https://media.example.test/last']
    elif provider=='wan':assert [x['type'] for x in body['input']['media']]==['first_frame','last_frame']
    else:assert calls[0].url.path=='/image-to-video/kling-3.0' and [x['type'] for x in body['contents'][1:]]==['first_frame','last_frame']


async def test_vidu_reference_alias_and_kling_omni_motion_modes():
    a=ref();r=request('vidu');r.continuity.primary_model='vidu-q3-pro'
    r=with_refs(r,[a],input_mode='reference',reference_images=(a,))
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda q:httpx.Response(200,json={}))) as c:
        p=ADAPTERS['vidu']('vidu-q3-pro',config('vidu'),resolve=resolve,client=c)
        r,urls=await p.materialize(r)
        assert p.payload(r,urls,'id')['model']=='viduq3'
        v=ref('motion','video',('motion',),5)
        r=request('kling');r.continuity.primary_model='kling-3-omni'
        r=with_refs(r,[a,v],input_mode='reference',reference_images=(a,),reference_videos=(v,),native_audio=False)
        assert 'REFERENCE_VIDEO_REQUIRES_EXPLICIT_MULTI_SHOT' in capability_errors(r,'kling-3-omni')
        r.provider_hints={'multi_shot':True}
        p=ADAPTERS['kling']('kling-3-omni',config('kling'),resolve=resolve,client=c)
        r,urls=await p.materialize(r)
        assert p.create_path(r)=='/omni-video/kling-3.0-omni'
        assert p.payload(r,urls,'id')['contents'][-1]['type']=='feature_video'
        r.continuity.primary_model='kling-3-motion';r.input_mode='motion_transfer';r.provider_hints={'allow_duration_truncation':True}
        p=ADAPTERS['kling']('kling-3-motion',config('kling'),resolve=resolve,client=c)
        r,urls=await p.materialize(r)
        assert p.create_path(r)=='/motion-control/kling-3.0'
        assert p.payload(r,urls,'id')['settings']=={'resolution':'720p','character_orientation':'video','audio':'off'}


async def test_lost_formal_task_write_recovers_receipt_without_new_create(setup,monkeypatch):
    x=setup;posts=[]
    def handler(req):
        if req.url.host=='cdn.example.test':return httpx.Response(200,content=x.video.read_bytes())
        if req.method=='POST':posts.append(req);return httpx.Response(200,json=created('seedance'))
        return httpx.Response(200,json=response('seedance'))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        h,id=await formal_setup(x,client);record=h._record
        async def fail(*a,**k):raise ConnectionError('Work write unavailable')
        monkeypatch.setattr(h,'_record',fail)
        with pytest.raises(ConnectionError):await h.submit(x.data.work.id,id)
        monkeypatch.setattr(h,'_record',record)
        assert (await h.poll(x.data.work.id,id)).output_media_id
    assert len(posts)==1 and x.store.imports==1


async def test_current_pack_change_blocks_new_submit_but_not_paid_recovery(setup):
    x=setup;posts=[]
    def handler(req):
        if req.method=='POST':posts.append(req);return httpx.Response(200,json=created('seedance'))
        return httpx.Response(200,json=response('seedance','running'))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        h,id=await formal_setup(x,client)
        x.data.work.content['continuityPacks']['C1']['revision']='changed'
        with pytest.raises(ValueError,match='CONTINUITY_PACK'):await h.submit(x.data.work.id,id)
        x.data.work.content['continuityPacks']['C1']['revision']='1'
        await h.submit(x.data.work.id,id)
        x.data.work.content['continuityPacks']['C1']['revision']='changed'
        assert (await h.poll(x.data.work.id,id)).status=='RUNNING'
    assert len(posts)==1


def test_environment_annotation_preserves_shell_assignments(tmp_path):
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('envdoc',Path(__file__).resolve().parents[2]/'scripts/update-video-env.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    p=tmp_path/'private.env';original="FISH_AUDIO_API_KEY='offline sample with spaces'\nFISH_AUDIO_BASE_URL=https://api.fish.audio\n"
    p.write_text(original);before=m.assignments(original)
    result=m.update(p,True)
    assert result['existingValuesPreserved'] and all(m.assignments(p.read_text())[k]==v for k,v in before.items())
    assert m.validate_comments(p.read_text())==12
    assert 'offline sample' not in json.dumps(result)


def test_real_env_optional_provider_does_not_break_plugin_load():
    from drama_plugin.plugin import DramaPlugin
    from pathlib import Path
    p=DramaPlugin.load(Path(__file__).resolve().parents[1])
    assert p.video_provider_host('/tmp/offline-video').availability()['seedance']=='NOT_CONFIGURED'
    assert p.tools.exists('production.generate_image') and p.tools.exists('production.generate_video')


async def test_malformed_success_metadata_is_not_accepted():
    def handler(req):
        raw=response('seedance');raw['duration']=-4
        return httpx.Response(200,json=raw)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        p=ADAPTERS['seedance'](MODELS['seedance'],config('seedance'),resolve=resolve,client=c)
        t=await p.create_task(request(),client_request_id='bad')
        assert t.status=='UNKNOWN' and t.error_code=='INVALID_PROVIDER_RESPONSE'


def test_primary_identity_cannot_fabricate_a_capability_gap():
    from drama_plugin.contracts.video import SwitchEvidence
    r=request();r.continuity.primary_model='invented-cheap-model'
    r.switch_evidence=SwitchEvidence(primary_capability_gap='UNKNOWN_OFFICIAL_MODEL',evidence_ref='fake',at_shot_boundary=True)
    r=VideoRequest.model_validate(r.model_dump())
    errors=continuity_errors(r,'seedance',MODELS['seedance'])
    assert 'PRIMARY_MODEL_PROVIDER_INVALID' in errors and 'PRIMARY_CAPABILITY_GAP_NOT_PROVEN' in errors


async def test_unified_comfy_facade_preserves_task_identity():
    from drama_plugin.providers.video.comfy import ComfyCloudProvider
    async def claim(id):raise AssertionError('No paid call in poll test')
    async def read(task):return task.model_copy(update={'status':'SUCCEEDED'})
    p=ComfyCloudProvider(attempt={'frame_snapshot':{'execution':{'capability':{'model_key':'minimax-h3'}}}},
        registry=None,claim_submission=claim,read_task=read)
    t=ProviderTask(provider='comfy_cloud',model='minimax-h3',provider_task_id='mcp-job',
        client_request_id='attempt',request_fingerprint='a'*64,status='RUNNING')
    assert (await p.fetch_result(t)).status=='SUCCEEDED' and await p.cancel_task(t) is None
    with pytest.raises(ValueError,match='IDENTITY'):await p.get_task(t.model_copy(update={'provider':'minimax'}))


async def test_http_frame_must_match_planned_canonical_request(setup):
    from drama_plugin.visual.production import _route_frame_gate
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda q:httpx.Response(200,json={}))) as c:
        h,id=await formal_setup(setup,c)
        w=await setup.memory.get_work(setup.data.work.id)
        state=w.content['productionStage'];frame=deepcopy(state['attempts'][0]['frame_snapshot'])
        frame['requirements']['video_request']['negative_prompt']='changed after route approval'
        with pytest.raises(ValueError,match='CANONICAL_VIDEO_REQUEST_REQUIRES_ROUTE_REPLAN'):_route_frame_gate(state,frame)
