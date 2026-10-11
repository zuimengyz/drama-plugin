"""Pinned task/film/scene persistence, using metadata-only HTTP fixtures."""
from copy import deepcopy
import json
import httpx
import pytest
from drama_plugin.config.models import ServiceConfig
from drama_plugin.contracts.base import dump_contract
from drama_plugin.creative_engine.contracts import Authority, Kind, WorkBody, ScriptBody, SceneBody, SourceBody
from drama_plugin.creative_engine.persistence import NativeTaskPersistence
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.providers.http.client import HttpProviderClient
from drama_plugin.providers.http.providers import HttpMemoryProvider
from drama_plugin.runtime.contracts import RuntimeScope, ArtifactReference


def originals(tmp_path):
    store=CreativeVersionStore(tmp_path/'originals')
    scope=RuntimeScope(work_id='native-same-task')
    source=store.write(writer=Authority.SOURCE,kind=Kind.SOURCE,scope=scope,
        body=SourceBody(goal='OFFLINE task',text='Designated source',spoken_language='en'),sources=(),operation='source')
    refs=[source]
    for kind,body,where in ((Kind.WORK,WorkBody(interpretation='Approved',dramatic_intent='Approved',character_meaning='Approved'),scope),
            (Kind.SCRIPT,ScriptBody(screenplay='Full film unchanged'),scope),
            (Kind.SCENE,SceneBody(scene_text='Scene unchanged'),scope.model_copy(update={'scene_id':'native-scene'}))):
        candidate=store.write(writer=Authority.CANON,kind=kind,scope=where,body=body,
            sources=(source,),operation=kind.value+':candidate')
        ref=store.write(writer=Authority.CANON,kind=kind,scope=where,body=body,sources=(source,),
            operation=kind.value+':adopted',adoption_decision=ArtifactReference(owner='user-decision',artifact_ref='offline-adoption',version=1),
            candidate_origin=candidate)
        refs.append(ref)
    return store,tuple(refs)


class MemoryWire:
    def __init__(self):
        self.work=None; self.scripts={}; self.posts=[]; self.corrupt=False
    def __call__(self,request):
        if request.method=='POST':
            assert request.url.path=='/api/tool/work/persist-native'
            plan=json.loads(request.content);self.posts.append(plan)
            source=json.loads(plan['source']['originJson']);work=source['scope']['workId']
            content={'nativeTask':{'authority':'PLUGIN_NATIVE_ORIGINAL','storageRole':'TASK',
                'originals':{r['ref']['fingerprint']:r for r in (plan['source'],*plan['works'])}}}
            self.work={'id':work,'title':source['body']['goal'],'version':1,'content':content}
            for record in plan['scripts']:
                self.scripts[record['ref']['identity']]={'id':record['ref']['identity'],'workId':work,'title':'OFFLINE screenplay',
                    'content':{'nativeScript':{'authority':'PLUGIN_NATIVE_ORIGINAL','storageRole':'SCREENPLAY',
                        'originals':{record['ref']['fingerprint']:record}}}}
            return httpx.Response(200,json=self.work)
        if request.url.path=='/api/tool/work/get':
            if self.work is None:
                return httpx.Response(404,json={'code':40400})
            value=deepcopy(self.work)
            if self.corrupt:value['content']['nativeTask']['originals']={}
            return httpx.Response(200,json=value)
        assert request.url.path=='/api/tool/script/get'
        return httpx.Response(200,json=self.scripts[request.url.params['script_id']])


def memory(wire):
    client=httpx.AsyncClient(base_url='https://service.invalid',transport=httpx.MockTransport(wire))
    config=ServiceConfig(base_url='https://service.invalid',operations={
        'persist_native_task':'/api/tool/work/persist-native','get_work':'/api/tool/work/get','get_script':'/api/tool/script/get'})
    return HttpMemoryProvider(HttpProviderClient(config,client)),client


@pytest.mark.parametrize('route,explicit,expected',[
    ('/api/tool/work/get',None,'/api/tool/work/persist-native'),
    ('/api/tool/work/get','/custom/exact-originals','/custom/exact-originals'),
    ('/custom/tasks/read',None,None),
])
def test_native_operation_mapping_only_extends_known_service_contract(tmp_path,route,explicit,expected):
    from drama_plugin.config import load_config
    operations={'get_work':route}
    if explicit:operations['persist_native_task']=explicit
    path=tmp_path/'config.json'
    path.write_text(json.dumps({'services':{'memory':{'operations':operations}}}))
    assert load_config(path,{}).services.memory.operations.get('persist_native_task')==expected


@pytest.mark.asyncio
async def test_native_persistence_roundtrip_exact_task_and_both_script_scopes(tmp_path):
    store,refs=originals(tmp_path);wire=MemoryWire();provider,client=memory(wire)
    try:
        owner=NativeTaskPersistence(store,provider)
        result=await owner.persist(refs)
        assert result.id=='native-same-task'
        plan=wire.posts[0]
        assert len(plan['works'])==1 and len(plan['scripts'])==2
        assert {json.loads(r['originJson'])['kind'] for r in plan['scripts']}=={'SCRIPT','SCENE'}
        assert set(wire.scripts)=={r.identity for r in refs[2:]}
        assert all(json.loads(r['originJson'])['adoptionDecisionRef']['artifactRef']=='offline-adoption' for r in plan['scripts'])
        assert (await owner.persist(refs)).id==result.id
        assert wire.posts[0]==wire.posts[1]
    finally:await client.aclose()


def test_candidates_remain_candidates_and_cross_work_is_rejected(tmp_path):
    store,refs=originals(tmp_path);owner=NativeTaskPersistence(store,None)
    candidate=store.resolve(store.resolve(refs[2]).candidate_origin_ref).ref()
    plan=owner.plan((refs[0],candidate))
    assert plan['scripts']==[] and plan['works']==[]
    other=store.write(writer=Authority.SOURCE,kind=Kind.SOURCE,scope=RuntimeScope(work_id='other'),
        body=SourceBody(goal='Other',text='Other source',spoken_language='en'),sources=(),operation='other')
    with pytest.raises(ValueError,match='CROSS_WORK'):owner.plan((other,refs[2]))
    with pytest.raises(ValueError,match='EXACT_NATIVE_TASK_SOURCE'):owner.plan(refs[1:])


@pytest.mark.asyncio
async def test_readback_is_required_not_a_successful_post_only(tmp_path):
    store,refs=originals(tmp_path);wire=MemoryWire();wire.corrupt=True;provider,client=memory(wire)
    try:
        with pytest.raises(ValueError,match='ORIGINAL_READBACK_MISMATCH'):
            await NativeTaskPersistence(store,provider).persist(refs)
    finally:await client.aclose()


@pytest.mark.asyncio
async def test_creative_adoption_persists_task_without_promoting_shot_copies(tmp_path,monkeypatch):
    from test_creative_engine import plugin,SOURCE,finish
    from drama_plugin.config import DramaPluginConfig
    from drama_plugin.runtime.contracts import RunMode,RuntimeState
    monkeypatch.setattr('drama_plugin.plugin.load_config',lambda _:DramaPluginConfig())
    p=plugin(tmp_path);wire=MemoryWire();provider,client=memory(wire)
    p.native_task_persistence.memory=provider
    try:
        run=p.create_film_run(work_id='automatic-task',source=SOURCE,mode=RunMode.PRODUCTION)
        assert (await finish(p,run)).state==RuntimeState.SUCCEEDED
        assert len(wire.posts)==1
        retained=wire.posts[0]
        assert json.loads(retained['source']['originJson'])['scope']['workId']=='automatic-task'
        # This small creative Run owns Shot-scoped Canon copies. They must not
        # become invented full-film/scene Script identities during persistence.
        assert retained['scripts']==[] and retained['works']==[]
        assert (await p.runtime.run(run.run_id)).state==RuntimeState.SUCCEEDED
        assert len(wire.posts)==1  # Completed replay does not perform another write.
    finally:await client.aclose()


@pytest.mark.asyncio
async def test_film_adoption_persists_shared_task_and_scene_scripts_before_children(tmp_path,monkeypatch):
    from test_creative_engine import plugin
    from test_film_engine import Authors,create
    from drama_plugin.config import DramaPluginConfig
    from drama_plugin.runtime.contracts import CapabilityInput,RuntimeState
    monkeypatch.setattr('drama_plugin.plugin.load_config',lambda _:DramaPluginConfig())
    author=Authors(scenes=2,shots=2);p=plugin(tmp_path,author)
    p.film.canon_author=author;p.film.direction_author=author
    wire=MemoryWire();provider,client=memory(wire);p.native_task_persistence.memory=provider
    try:
        run=await p.runtime.run(create(p).run_id)
        assert run.state==RuntimeState.WAITING_USER
        cp=p.film.store.checkpoint(run.run_id)
        await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=cp.plan_ref)
        class StopBeforeChild(Exception):pass
        def no_children(**kwargs):raise StopBeforeChild()
        monkeypatch.setattr(p,'create_film_run',no_children)
        with pytest.raises(StopBeforeChild):
            await p.film.adopt(CapabilityInput(run_id=run.run_id,scope=run.scope,operation_id='offline-film-adoption'))
        plan=wire.posts[0]
        assert len(plan['works'])==1 and len(plan['scripts'])==3
        assert len({r['ref']['identity'] for r in plan['scripts']})==3
        assert {json.loads(r['originJson'])['scope']['sceneId'] for r in plan['scripts']}=={None,'canon-scene-0','canon-scene-1'}
        assert not list(tmp_path.rglob('*.mp4'))
    finally:await client.aclose()


@pytest.mark.asyncio
async def test_reference_preflight_recovers_actual_work_scope_without_spending(tmp_path,monkeypatch):
    from test_target_reference_production import prepared
    p,_,child,record,_=await prepared(tmp_path,monkeypatch)
    wire=MemoryWire();provider,client=memory(wire)
    p.providers.memory=provider;p.native_task_persistence.memory=provider
    try:
        assert await p.reference_production.formal_scope(record)
        assert len(wire.posts)==1
        assert wire.work['id']==record.scope.work_id
        assert p.reference_production.get(child).stage is None
        assert p.reference_production.get(child).receipt is None
    finally:await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('failure',['server','timeout'])
async def test_reference_preflight_never_creates_task_after_unavailable_read(tmp_path,monkeypatch,failure):
    from test_target_reference_production import prepared
    p,_,child,record,_=await prepared(tmp_path,monkeypatch)
    wire=MemoryWire()
    def unavailable(request):
        assert request.method=='GET'
        if failure=='timeout':raise httpx.ReadTimeout('offline simulated unavailable read',request=request)
        return httpx.Response(503,json={'code':'UNAVAILABLE'})
    provider,client=memory(unavailable)
    p.native_task_persistence.memory=provider
    # The formal-scope read must use the same actual memory endpoint as retention.
    from dataclasses import replace
    p.providers=replace(p.providers,memory=provider)
    try:
        from drama_plugin.exceptions import RemoteServiceError
        with pytest.raises((RemoteServiceError,httpx.HTTPError)):
            await p.reference_production.formal_scope(record)
        assert wire.posts==[]
        assert p.reference_production.get(child).stage is None
    finally:await client.aclose()
