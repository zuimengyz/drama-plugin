"""Offline storage fault simulation plus actual public completion/consumer paths."""
from pathlib import Path
from types import SimpleNamespace
import httpx
import pytest
from drama_plugin.media_delivery import (MediaIdentity,PersistenceError,complete_retained_media,
    verify_media,prepare_bound_media,file_hash)
from drama_plugin.contracts.media import MediaType
from drama_plugin.providers.mock import MockDramaData,MockMemoryProvider,MockAssetProvider
from drama_plugin.exceptions import RemoteServiceError
from test_role_dubbing import FakeMediaProvider
from test_performance_native_mix import sounds


class Store(FakeMediaProvider):
    def __init__(self):
        super().__init__();self.imports=0;self.reads=0;self.lost=False;self.expired=False
    async def import_media(self, **kw):
        self.imports+=1
        m=await super().import_media(**kw)
        m=m.model_copy(update={'mime_type':'video/mp4' if m.media_type==MediaType.VIDEO else 'audio/wav'})
        self.values[-1]=m
        if self.lost:
            self.lost=False
            raise httpx.ReadTimeout('response lost after commit')
        return m
    async def get_media(self, media_id):
        found=[m for m in self.values if m.id==media_id]
        if not found:raise RemoteServiceError('missing',status_code=404,error_code='NOT_FOUND')
        return found[0]
    async def download_media(self, media_id, destination):
        self.reads+=1
        if self.expired:
            self.expired=False
            raise RemoteServiceError('expired URL',status_code=403,error_code='MEDIA_UNAVAILABLE')
        if media_id not in self.objects:raise RemoteServiceError('object missing',status_code=404)
        return await super().download_media(media_id,destination)


@pytest.fixture
def setup(sounds):
    video,_,tmp=sounds;data=MockDramaData();store=Store()
    memory=MockMemoryProvider(data);asset=MockAssetProvider(data)
    ident=MediaIdentity(data.work.id,MediaType.VIDEO,'paid:job1',file_hash(video),shot_id=data.shot.id,purpose='VIDEO_CANDIDATE')
    async def complete(**kwargs):
        return await complete_retained_media(store,memory,asset,ident,source=video,content={'providerJobId':'job1'},
            cache=tmp/'cache',target_id='clip1',**kwargs)
    return SimpleNamespace(video=video,tmp=tmp,data=data,store=store,memory=memory,asset=asset,ident=ident,complete=complete)


@pytest.mark.asyncio
async def test_local_probe_without_valid_media_cannot_finish(setup):
    x=setup
    with pytest.raises(PersistenceError,match='local file'):
        await verify_media(x.store,x.ident,x.tmp/'cache')
    with pytest.raises(RemoteServiceError):
        await verify_media(x.store,MediaIdentity(**{**x.ident.__dict__,'media_id':'nonexistent'}),x.tmp/'cache')


@pytest.mark.asyncio
@pytest.mark.parametrize('fault',['missing','hash','scope','selected_version'])
async def test_public_consumer_rejects_invalid_formal_media(setup,fault):
    x=setup;rec=await x.complete();m=x.store.values[0]
    if fault=='missing':del x.store.objects[m.id]
    elif fault=='hash':x.store.objects[m.id]=b'x'*m.file_size
    elif fault=='scope':x.store.values[0]=m.model_copy(update={'work_id':'another-work'})
    else:
        x.data.shot.content['mediaBindings'][0]['contentHash']='a'*64
    with pytest.raises((PersistenceError,RemoteServiceError)):
        await prepare_bound_media(x.store,x.memory,shot_id=x.data.shot.id,target_id='clip1',cache=x.tmp/'empty')
    assert x.store.imports==1


@pytest.mark.asyncio
async def test_lost_import_response_recovers_same_id_before_binding(setup):
    x=setup;x.store.lost=True
    first=await x.complete();second=await x.complete()
    assert first['mediaId']==second['mediaId'] and x.store.imports==1
    assert len(x.data.shot.content['mediaBindings'])==1


@pytest.mark.asyncio
async def test_interruption_before_binding_never_reimports_or_generates(setup,monkeypatch):
    x=setup;save=x.memory.save_shot
    async def fail(*a,**k):raise httpx.ReadTimeout('binding unavailable')
    monkeypatch.setattr(x.memory,'save_shot',fail)
    with pytest.raises(httpx.ReadTimeout):await x.complete()
    assert x.store.imports==1 and 'mediaBindings' not in x.data.shot.content
    monkeypatch.setattr(x.memory,'save_shot',save)
    result=await x.complete()
    assert result['deliveryStatus']=='CANDIDATE_SAVED' and x.store.imports==1


@pytest.mark.asyncio
async def test_expired_url_gets_fresh_resolve_and_same_identity(setup):
    x=setup;x.store.expired=True
    result=await x.complete()
    assert result['persistenceStatus']=='VERIFIED' and x.store.reads==2 and x.store.imports==1
    assert 'url' not in result and result['storageDelivery']['signedQuerySaved'] is False


@pytest.mark.asyncio
async def test_candidate_storage_does_not_approve_content_or_adopt(setup):
    x=setup;r=await x.complete()
    assert r['binding']['retention']=='CANDIDATE'
    assert r['binding']['contentReview']=='PENDING_REVIEW' and r['binding']['userAdoption']=='PENDING'
    with pytest.raises(PersistenceError):
        await prepare_bound_media(x.store,x.memory,shot_id=x.data.shot.id,target_id='clip1',cache=x.tmp/'empty',adopted=True)


@pytest.mark.asyncio
async def test_actual_native_consumer_uses_empty_cache_without_source_or_processing(setup,monkeypatch):
    x=setup
    selection={'decision':'REUSE_SOURCE_AV','authority':'USER_EXPLICIT_ADOPTION','audioProcessing':[]}
    r=await x.complete(retention='FORMAL',user_adoption='USER_SELECTED',content_review='NOT_VERIFIED',selection=selection)
    # Remove only this synthetic source. The consumer has no source path argument.
    x.video.unlink()
    import subprocess
    run=subprocess.run;commands=[]
    def guard(cmd,*a,**k):
        assert Path(cmd[0]).name=='ffprobe';commands.append(cmd);return run(cmd,*a,**k)
    monkeypatch.setattr(subprocess,'run',guard)
    ready=await prepare_bound_media(x.store,x.memory,shot_id=x.data.shot.id,target_id='clip1',cache=x.tmp/'brand-new',adopted=True)
    assert ready['status']=='READY' and ready['audioProcessing']==[] and not ready['createdMedia']
    assert file_hash(Path(ready['path']))==r['contentHash'] and commands and x.store.imports==1


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['image','video'])
async def test_public_generation_tools_execute_completion_gate(setup,kind):
    from drama_plugin.tools.catalog import build_tool_registry
    x=setup;r=await x.complete();m=x.store.values[0]
    calls=[]
    class Producer:
        async def generate_image(self,*a,**k):calls.append('image');return m
        async def generate_video(self,*a,**k):calls.append('video');return m
    from drama_plugin import DramaPlugin
    p=DramaPlugin.load(Path(__file__).resolve().parents[1]).providers
    # Fill unused media operations so the real registry can discover its full schema.
    for name in ['create_media','save_media','restore_media_object']:
        setattr(x.store,name,getattr(p.media,name))
    registry=build_tool_registry(x.memory,x.asset,p.research,Producer(),x.store,p.context,p.voice,p.role_dubbing)
    # Output object missing even though generation returned an ID and valid local bytes.
    del x.store.objects[m.id]
    with pytest.raises(RemoteServiceError):
        await registry.get('production.generate_'+kind).handler(prompt='frozen',reference_media_ids=['one'])
    assert calls==[kind] and x.store.imports==1


@pytest.mark.asyncio
async def test_visual_attempt_persists_format_failure_as_candidate_without_resetting_cost(setup,monkeypatch):
    from drama_plugin.hosts.visual_delivery import complete_attempt
    x=setup
    class Session:
        def __init__(self,*a):self.media=x.store;self.memory=x.memory;self.asset=x.asset;self.calls=[]
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
    monkeypatch.setattr('drama_plugin.hosts.visual_delivery.McpMediaSession',Session)
    a={'attempt_id':'attempt1','shot_id':'clip1','status':'COMPLETED','technical_status':'FAIL',
       'technical':{'checks':{'integrity':'PASS','linkage':'PASS','dimensions':'FAIL'},'probe':{'format':{'duration':'1'}}},
       'media_kind':'VIDEO','job_id':'job1','output_hash':file_hash(x.video),'request_fingerprint':'a'*64,
       'credits':513,'reserved_credits':570,'content_status':'PENDING_REVIEW','user_adoption':'PENDING'}
    state={'attempts':[a],'stage':{'id':'v2-06','budget_credits':1200},'plan_fingerprint':'p',
           'frames':{'clip1':{'schema':'video-decision-v1','spec':{},'requirements':{
               'work_id':x.data.work.id,'shot_id':x.data.shot.id,'inputs':[]}}}}
    args=dict(attempt_id='attempt1',mcp_config='fixture',source_path=str(x.video),cache=str(x.tmp/'visual'),
              work_id=x.data.work.id,shot_id=x.data.shot.id)
    first=await complete_attempt(state,**args);second=await complete_attempt(state,**args)
    assert first['mediaId']==second['mediaId'] and x.store.imports==1
    assert a['technical_status']=='FAIL' and a['content_status']=='PENDING_REVIEW' and a['user_adoption']=='PENDING'
    assert a['credits']==513 and len(state['attempts'])==1 and a['delivery_status']=='CANDIDATE_SAVED'


@pytest.mark.asyncio
async def test_explicit_av_entry_persists_and_resumes_without_remux(setup,sounds,monkeypatch):
    from drama_plugin.media_delivery import assemble_av_delivery
    from drama_plugin.contracts.audio import AvAssemblyManifest
    x=setup;_,speech,_=sounds;source=await x.complete();video=x.store.values[0]
    audio=await x.store.import_media(work_id=x.data.work.id,media_type=MediaType.AUDIO,
        source_uri=speech.as_uri(),content={},source_ref='reviewed-mix',shot_id=x.data.shot.id,purpose='SHOT_DIALOGUE_MIX')
    manifest=AvAssemblyManifest(source_video_media_id=video.id,audio_mix_media_id=audio.id,timeline=[])
    args=dict(source_identity=MediaIdentity.from_media(video),mix_identity=MediaIdentity.from_media(audio),
        manifest=manifest,output=x.tmp/'new-assembly.mp4',source_ref='assembly:attempt1',cache=x.tmp/'assembly-cache',target_id='assembly1')
    result=await assemble_av_delivery(x.store,x.memory,x.asset,**args)
    assert result['deliveryStatus']=='CANDIDATE_SAVED' and result['persistenceStatus']=='VERIFIED'
    assert result['binding']['userAdoption']=='PENDING' and x.store.imports==3
    import drama_plugin.audio.host_media as host
    def deny(*a,**k):raise AssertionError('Imported assembly must not remux on recovery')
    monkeypatch.setattr(host,'assemble_av',deny)
    again=await assemble_av_delivery(x.store,x.memory,x.asset,**args)
    assert again['mediaId']==result['mediaId'] and x.store.imports==3
