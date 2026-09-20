"""Model disable flags block new spending, but do not strand paid tasks."""
import httpx
import pytest
from drama_plugin.providers.video.registry import model_keys, model_enabled_env, model_enabled, model_availability
from drama_plugin.visual.video_selection import choose, verify_decision, qualify_route, ProductionRoute
from test_video_route_policy import candidates, policy
from test_official_video_providers import formal_setup, request, config, resolve, MODELS, created, response
from drama_plugin.providers.video.adapters import ADAPTERS
from test_media_delivery import setup
from test_performance_native_mix import sounds


@pytest.mark.parametrize('value,expected', [('true',True),(' TRUE ',True),('false',False),('',False),('yes',False),('1',False),('typo',False)])
def test_flag_parsing_and_status(value,expected):
    key=model_enabled_env('vidu-q3-turbo');env={key:value}
    assert model_enabled('vidu-q3-turbo',env) is expected
    assert model_availability(env)['vidu-q3-turbo']['status']==('NOT_CONFIGURED' if expected else 'DISABLED')


def test_all_known_models_have_unique_flags_and_legacy_defaults():
    assert len(model_keys())==14
    assert len({model_enabled_env(k) for k in model_keys()})==14
    assert all(model_enabled(k,{}) for k in model_keys())
    assert model_enabled_env('MiniMax H3')=='DRAMA_VIDEO_MODEL_MINIMAX_H3_ENABLED'


def test_disabled_comfy_model_cannot_win_auto_prefer_pin_or_dry_run(tmp_path,monkeypatch):
    r,cs=candidates(tmp_path)
    monkeypatch.setenv(model_enabled_env('seedance-2.5'),'false')
    assert choose(r,cs,policy=policy())['selected']=='minimax-h3'
    assert choose(r,cs,policy=policy('AUTO'))['selected']!='seedance-2.5'
    assert choose(r,cs,policy=policy('PIN'))['selected'] is None
    assert choose(r,cs,policy=policy('PIN'),dry_run=True)['selected'] is None
    for c in cs:monkeypatch.setenv(model_enabled_env(c.model),'false')
    assert choose(r,cs)['selected'] is None


@pytest.mark.parametrize('provider',MODELS)
async def test_official_disabled_direct_create_makes_no_network_call(provider,monkeypatch):
    monkeypatch.setenv(model_enabled_env(MODELS[provider]),'false')
    def unexpected(req):raise AssertionError('Disabled model must not send requests')
    async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected)) as c:
        p=ADAPTERS[provider](MODELS[provider],config(provider),resolve=resolve,client=c)
        with pytest.raises(ValueError,match='MODEL_DISABLED'):
            await p.create_task(request(provider),client_request_id='disabled')


async def test_disable_after_reservation_blocks_submission(setup,monkeypatch):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req:pytest.fail('No paid call allowed'))) as c:
        h,id=await formal_setup(setup,c)
        w=await setup.memory.get_work(setup.data.work.id)
        monkeypatch.setenv(model_enabled_env(MODELS['seedance']),'false')
        route=ProductionRoute.model_validate(w.content['productionRoute'])
        assert 'MODEL_DISABLED' in qualify_route(route)['exclusions']
        with pytest.raises(ValueError,match='INELIGIBLE'):await h.submit(setup.data.work.id,id)


async def test_disable_after_submit_still_recovers_and_imports_original_task(setup,monkeypatch):
    posts=[]
    def handler(req):
        if req.url.host=='cdn.example.test':return httpx.Response(200,content=setup.video.read_bytes())
        if req.method=='POST':posts.append(req);return httpx.Response(200,json=created('seedance'))
        return httpx.Response(200,json=response('seedance'))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        h,id=await formal_setup(setup,c)
        await h.submit(setup.data.work.id,id)
        monkeypatch.setenv(model_enabled_env(MODELS['seedance']),'false')
        task=await h.poll(setup.data.work.id,id)
        assert task.output_media_id and task.status=='SUCCEEDED'
    assert len(posts)==1 and setup.store.imports==1
