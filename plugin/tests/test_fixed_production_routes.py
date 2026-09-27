import pytest
from drama_plugin.config.production_routes import selected, ROUTES, SEEDREAM_MODELS, require_image, require_video
from drama_plugin.providers.ark_image import image_payload


def test_exactly_one_enabled():
    assert sum(r['enabled'] for r in ROUTES.values()) == 1
    assert selected({})['route'] == 'ark_seedream_seedance'
    assert selected({})['video_model'] == 'seedance-2-fast'


@pytest.mark.parametrize('name,model', SEEDREAM_MODELS.items())
def test_model_choice(name, model):
    assert selected({'DRAMA_PLUGIN_ROUTE_IMAGE_MODEL':name})['image_model'] == model
    assert selected({'DRAMA_PLUGIN_ROUTE_IMAGE_MODEL':model})['image_model'] == model
    body = image_payload(model, 'Four adults at a table.', (2560,1440), 1)
    assert body['model'] == model
    assert body['response_format'] == 'b64_json'
    assert 'approved_interpretation_refs' not in body
    assert 'api_key' not in body


@pytest.mark.parametrize('route',['image2_vidu','image2_minimax_h3','unknown'])
def test_disabled_routes(route):
    with pytest.raises(ValueError,match='DISABLED_OR_NOT_UNIQUE'):
        selected({'DRAMA_PLUGIN_ACTIVE_ROUTE':route})


def test_unknown_or_wrong_models():
    with pytest.raises(ValueError): selected({'DRAMA_PLUGIN_ROUTE_IMAGE_MODEL':'fake-seedream'})
    with pytest.raises(ValueError): selected({'DRAMA_PLUGIN_ROUTE_VIDEO_MODEL':'vidu-q3-pro'})
    with pytest.raises(ValueError): require_image('comfy_cloud','gpt-image-2')
    with pytest.raises(ValueError): require_video('comfy_cloud','seedance-2-fast')
    with pytest.raises(ValueError): image_payload(SEEDREAM_MODELS['Doubao-Seedream-5.0-lite'],'x',(1280,720),1)


@pytest.mark.parametrize('name',['Doubao-Seedream-5.0-pro','Doubao-Seedream-5.0-flash'])
def test_model_specific_resolution_limits(name):
    model=SEEDREAM_MODELS[name]
    assert image_payload(model,'x',(1280,720),1)['size']=='1280x720'
    with pytest.raises(ValueError,match='SIZE_UNSUPPORTED'):
        image_payload(model,'x',(4096,4096),1)


def test_existing_video_choices_are_real_registry_keys():
    from drama_plugin.providers.video.registry import registry
    for route in ROUTES.values():
        assert set(route['video_models']) <= set(registry()['models'])


async def test_formal_save_rejects_disabled_retained_route_before_write(tmp_path):
    from test_production_route import route
    from drama_plugin.hosts.route_production import save_route
    class Memory:
        async def get_work(self, *args): raise AssertionError('must reject before reading/writing')
        async def save_work(self, *args): raise AssertionError('disabled route must never save')
    with pytest.raises(ValueError, match='FIXED_PRODUCTION_VIDEO_ROUTE_MISMATCH'):
        await save_route(Memory(), 'W', route(tmp_path).model_dump(mode='json'))


async def test_formal_begin_rejects_old_gpt_reference_before_claim(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from test_production_route import route
    from drama_plugin.hosts.route_production import operate
    raw=route(tmp_path).model_dump(mode='json')
    work=SimpleNamespace(id='W',content={'productionRoute':raw,
        'productionStage':{'attempts':[{'attempt_id':'old-gpt'}]}})
    class Memory:
        async def get_work(self,id):return work
        async def save_work(self,*a):raise AssertionError('disabled route cannot claim')
    async def sources(*a):pass  # This test isolates the live model gate.
    monkeypatch.setattr('drama_plugin.hosts.route_production.validate_route_direction_sources',sources)
    monkeypatch.setattr('drama_plugin.hosts.route_production.attempt_frame',lambda *a:
        {'schema':'visual-frame-preflight-v1','template':{'model':'gpt-image-2'}})
    with pytest.raises(ValueError,match='FIXED_PRODUCTION_IMAGE_ROUTE_MISMATCH'):
        await operate(Memory(),'W','begin-submission',{'attempt_id':'old-gpt'})


def test_replay_existing_frame_without_reselection():
    # Historical explicit templates retain their schema and fingerprint.
    from drama_plugin.visual.frame_request import Template
    t=Template(name='old',model='gpt-image-2',evidence='retained',graph_hash='a'*64,
               graph_path='old',image_slots=(),prompt_node='1',output_size=(1280,720),supported_types=('ordinary',))
    assert t.http_provider is None


def ark_frame(tmp_path):
    from test_visual_first_pass import material
    from drama_plugin.visual.frame_request import compile_frame
    spec, _ = material(tmp_path)
    spec = spec.model_copy(update=dict(references=(), reference_lock={},
        identity_bootstrap='Create initial identities from approved source', omitted={'glider':'source-described'},
        target_size=(1280,720)))
    return compile_frame(spec)


def test_official_frame_compilation_and_tamper(tmp_path):
    from drama_plugin.visual.frame_request import verify_compiled
    from drama_plugin.visual.image_route import execution_identity
    frame = ark_frame(tmp_path)
    verify_compiled(frame)
    assert frame['spec']['target_size'] == [1280,720]
    assert frame['template']['output_size'] == [2560,1440]
    assert frame['request']['tool'] == 'image.create'
    assert execution_identity(frame)['transport'] == 'HTTP'
    assert 'workflow' not in frame['request']
    frame['request']['body']['model'] = 'fake'
    with pytest.raises(ValueError): verify_compiled(frame)


def test_ark_binding_rejects_changed_request_and_missing_context(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from drama_plugin.providers.ark_image import binding, validate_binding
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY','OFFLINE_TEST_SECRET')
    frame = ark_frame(tmp_path)
    now = datetime.now(timezone.utc)
    e=dict(source='offline fixture',verified=True,checked_at=now.isoformat(),expires_at=(now+timedelta(minutes=5)).isoformat())
    b=binding(frame,e);validate_binding(frame,b)
    assert 'OFFLINE_TEST_SECRET' not in str(b)
    with pytest.raises(ValueError): validate_binding(frame,None)
    b['request_fingerprint']='0'*64
    with pytest.raises(ValueError): validate_binding(frame,b)


async def test_reserved_http_image_uses_exact_request_and_external_refs(tmp_path, monkeypatch):
    import base64, json, httpx
    from types import SimpleNamespace
    from datetime import datetime,timedelta,timezone
    from drama_plugin.providers.ark_image import binding
    from drama_plugin.hosts.ark_image import ArkImageHost
    from drama_plugin.contracts.base import sha256_canonical as fp
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY','OFFLINE_TEST_SECRET')
    f=ark_frame(tmp_path);now=datetime.now(timezone.utc)
    e=dict(source='offline',verified=True,checked_at=now.isoformat(),expires_at=(now+timedelta(minutes=5)).isoformat())
    a=dict(attempt_id='attempt',status='RESERVED',job_id=None,request=f['request'],execution_binding=binding(f,e))
    work=SimpleNamespace(content={'productionStage':{'attempts':[a]}})
    class Memory:
        async def get_work(self,id):return work
    calls=[]
    async def operate(memory, work, command, payload, **kwargs):
        calls.append((command,kwargs))
        if command=='begin-submission':
            if not kwargs.get('approved_interpretation_refs'):raise ValueError('USER_INTERPRETATION_APPROVAL_REQUIRED')
            a['status']='UNKNOWN'
    monkeypatch.setattr('drama_plugin.hosts.ark_image.operate',operate)
    monkeypatch.setattr('drama_plugin.hosts.ark_image.attempt_frame',lambda state,attempt:f)
    wire=[]
    def handler(req):
        body=json.loads(req.content);wire.append(body)
        assert body==f['request']['body']
        assert 'approved_interpretation_refs' not in body
        return httpx.Response(200,headers={'x-request-id':'real-fixture-request-id'},
            json={'created':123,'data':[{'b64_json':base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        host=ArkImageHost(Memory(),tmp_path/'cache',client=client)
        with pytest.raises(ValueError,match='APPROVAL_REQUIRED'):await host.submit('W','attempt')
        assert not wire
        refs=('opaque-fixture-external-context',)
        receipt=await host.submit('W','attempt',approved_interpretation_refs=refs)
        assert receipt['status']=='COMPLETED'
        assert receipt['request_fingerprint']==fp(f['request'])
        assert calls[-2][1]['approved_interpretation_refs']==refs
        assert await host.submit('W','attempt',approved_interpretation_refs=refs)==receipt
        assert len(wire)==1
