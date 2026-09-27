"""Offline lifecycle tests; real compiler, frozen seal and continuity gate."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from drama_plugin.hosts import route_production as host
from drama_plugin.hosts.http_video import candidate
from drama_plugin.visual.video_selection import Cost, Evidence, Quality
from test_video_selection import evidence
from test_production_route import route
from test_seedance_prompt_generator import cinematic_sample


def setup(tmp_path):
    r=cinematic_sample(tmp_path)
    r=r.model_copy(update={"source_fingerprint":r.frozen_creative["cinematic_direction"]["spec"]["sourceFingerprint"]})
    c=candidate(r,'seedance-2-mini',cost=Cost(components={'video':20,'audio':0,'references':0,'addons':0,'correction':0},evidence=evidence()),evidence=Evidence.model_validate(evidence()),quality=Quality())
    old=route(tmp_path).model_copy(update={'work_id':r.work_id,'video_targets':(r.target_id,'later'),'candidate':c})
    new=old.model_copy(deep=True,update={'creative_fingerprint':r.source_fingerprint})
    new.requirements.update(creative_schema='cinematic-shot-v1',cinematic_directions={r.target_id:r.frozen_creative['cinematic_direction']},shots={r.target_id:r.shot_id},video_requests={r.target_id:r.video_request.model_dump(mode='json',by_alias=True)})
    work=SimpleNamespace(id=r.work_id,content={'continuityPacks':{r.video_request.continuity.segment_id:r.video_request.continuity.model_dump(mode='json',by_alias=True)}})
    class Memory:
        async def get_work(self,wid):assert wid==work.id;return work
        async def get_shot(self,sid):return SimpleNamespace(content={'creativeArtifacts':{'cinematicDirection':self.frozen}})
        frozen=deepcopy(r.frozen_creative['cinematic_direction'])
    return r,old,new,work,Memory()


@pytest.mark.asyncio
@pytest.mark.parametrize('change',[None,'hash','targets','stage','route','work','target','downgrade','seal','pack','source','missing','retained','provider'])
async def test_only_verified_forward_binding(tmp_path,monkeypatch,change):
    r,old,new,w,m=setup(tmp_path);target=r.target_id;calls=[]
    async def current_sources(memory,work,route):
        calls.append(True)
        if change=='source':raise ValueError('SOURCE_CHANGED')
    monkeypatch.setattr(host,'validate_route_direction_sources',current_sources)
    if change=='hash':new=new.model_copy(update={'creative_fingerprint':'b'*64})
    if change=='targets':new=new.model_copy(update={'video_targets':(target,)})
    if change=='stage':new=new.model_copy(update={'stage_id':'new'})
    if change=='route':new=new.model_copy(update={'route_id':'new'})
    if change=='work':new=new.model_copy(update={'work_id':'other'})
    if change=='target':target='later'
    if change=='downgrade':old.requirements['creative_schema']='cinematic-shot-v1'
    if change=='seal':new.requirements['cinematic_directions'][target]['fingerprint']='b'*64
    if change=='pack':w.content['continuityPacks']={}
    if change=='missing':r=None
    if change=='retained':m.frozen={}
    if change=='provider':new.candidate.parameters['unexpected']='change'
    if change:
        with pytest.raises(ValueError):await host.validate_canonical_source_binding(m,w,old,new,target,r,())
    else:
        await host.validate_canonical_source_binding(m,w,old,new,target,r,())
        assert calls==[True]

@pytest.mark.asyncio
async def test_formal_save_journals_and_idempotent_replay(tmp_path,monkeypatch):
    r,old,new,w,m=setup(tmp_path)
    from drama_plugin.visual.history import resolve
    w.title='offline';w.description=''
    w.content.update(productionRoute=old.model_dump(mode='json'),productionStage={
        'production_route':old.model_dump(mode='json'),'stage':{'budget_unit':'credits','budget_credits':300},'attempts':[],'frames':{}})
    async def save(wid,title,content,description):w.content=deepcopy(content)
    m.save_work=save
    async def sources(*args):pass
    monkeypatch.setattr(host,'validate_route_direction_sources',sources)
    monkeypatch.setattr(host,'choose_routes',lambda *a,**kw:{'selected':True,'route_policy_resolution':{}})
    monkeypatch.setattr(host,'qualify_route',lambda *a,**kw:{'eligible':True,'incremental_credits':20})
    raw=new.model_dump(mode='json')
    await host.save_route(m,w.id,raw,execution_target=r.target_id,canonical_requirements=r)
    stage=w.content['productionStage'];assert len(stage['route_revisions'])==1
    assert resolve(stage,stage['route_revisions'][0]['previous_route_ref'],'route')==old.model_dump(mode='json')
    assert stage['production_route']==raw
    await host.save_route(m,w.id,raw,execution_target=r.target_id,canonical_requirements=r)
    assert len(w.content['productionStage']['route_revisions'])==1
    with pytest.raises(ValueError):await host.save_route(m,w.id,old.model_dump(mode='json'),execution_target=r.target_id,canonical_requirements=r)
