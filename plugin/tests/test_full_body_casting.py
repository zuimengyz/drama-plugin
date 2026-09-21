from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import pytest

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creation import Work
from drama_plugin.contracts.visual_route import RouteCastingContext
from drama_plugin.full_body_casting import FullBodyCastingSpec, full_body_design, executable_full_body, reserve_full_body
from drama_plugin.hosts.casting_projection import full_body_seedream_projection
from test_casting_discriminants import profile, plan
from test_visual_route import context


def fixture(tmp_path):
    p = profile(); v = plan(p); c0 = context()
    c = RouteCastingContext(**dump_contract(c0), characterIdentity=p.identity,
        profileFingerprint=v.profile_fingerprint, planFingerprint=sha256_canonical(v))
    source = tmp_path / 'source.txt'; source.write_text('source')
    s = FullBodyCastingSpec(character=p.identity, variant='n', costume='jointed armor',
        weapon='one spear', posture='standing with hands visible', lightingBackground='neutral',
        sources={str(source): hashlib.sha256(source.read_bytes()).hexdigest()})
    d = full_body_design(p,v,c,s)
    auth = {'authorizationId':'task','authority':'USER_EXPLICIT_SINGLE_CANDIDATE',
        'directiveRef':str(source),'directiveHash':next(iter(s.sources.values())),
        'workId':'w','workRevision':'r','character':p.identity,'purpose':s.purpose,
        'maxOutputs':1,'stopAfterFirstResult':True,'inputsFingerprint':d['inputsFingerprint'],'status':'AUTHORIZED'}
    w = Work(id='w',title='Synthetic',content={'revisionId':'r','approval':{'status':'APPROVED'},
        'visualRoute':'stylized_cinematic_cg','visualLanguage':'HEROIC_CINEMATIC_CG','visualRouteBinding':{'workRevision':'r',
        'project':dump_contract(c.project),'styleFingerprint':sha256_canonical(c.style),'sourcePins':s.sources},
        'characterCastingAuthorizations':{'task':auth}})
    from character_package_fixture import make_package
    repo, package, ref, _, _ = make_package(tmp_path/'character-repository',status='VISUAL_TESTING',identity=p.identity)
    import os
    os.environ['DRAMA_CHARACTER_REPOSITORY_ROOT'] = str(repo.root)
    w.content['characterPackageRoster'] = {'sourceRevision':'r','characters':[{'characterId':'actor','name':p.identity,'category':'PRIMARY_CHARACTER','dedicatedPackageRequired':True,'package':ref}]}
    return w,p,v,c,s


def test_whole_body_is_separate_and_needs_no_adopted_face(tmp_path):
    w,p,v,c,s=fixture(tmp_path); old=dump_contract(p)
    b=executable_full_body(w,p,v,c,s,'task')
    assert b['referenceMediaIds']==[] and b['maxOutputs']==1
    assert 'FULL BODY' in b['prompt'] and 'jointed armor' in b['prompt']
    assert b['userAdoption']=='PENDING' and dump_contract(p)==old


@pytest.mark.parametrize('change', ['missing','route','revision','character','count','consumed','spec'])
def test_scope_fails_closed(tmp_path,change):
    w,p,v,c,s=fixture(tmp_path)
    a=w.content['characterCastingAuthorizations']['task']
    if change=='missing':w.content['characterCastingAuthorizations']={}
    if change=='route':w.content['visualRoute']='live_action_realist'
    if change=='revision':w.content['revisionId']='other'
    if change=='character':a['character']='someone_else'
    if change=='count':a['maxOutputs']=2
    if change=='consumed':a['status']='RESERVED'
    if change=='spec':s.weapon='different'
    with pytest.raises(ValueError):executable_full_body(w,p,v,c,s,'task')


def request_for(b):
    e={'checkedAt':datetime.now(timezone.utc).isoformat(),'schema':{
       'id':'api_bytedance_seedream_5_0_pro_t2i','nodes':[
       {'id':'3','class_type':'ByteDanceSeedreamNodeV3','inputs':{'model.width':1,'model.height':1,'prompt':''}},
       {'id':'2','class_type':'SaveImageAdvanced','inputs':{}}]}}
    return {'transport':'MCP','modality':'IMAGE','mock':False,'outputCount':1,'seed':1,
        'prompt':b['prompt'],'capabilityEvidence':e,'durableCompletionAvailable':True,
        'providerRequest':full_body_seedream_projection(b,e,seed=1)}


class Memory:
    def __init__(self,w):self.w=deepcopy(w)
    async def get_work(self,wid):return deepcopy(self.w)
    async def save_work(self,wid,title,content,description):self.w.content=deepcopy(content)


@pytest.mark.asyncio
async def test_reservation_survives_restart_and_no_second_submission(tmp_path):
    w,p,v,c,s=fixture(tmp_path);m=Memory(w);req=request_for(executable_full_body(w,p,v,c,s,'task'))
    await reserve_full_body(m,'w',p,v,c,s,'task',req,tmp_path/'ledger')
    assert m.w.content['characterCastingAuthorizations']['task']['status']=='RESERVED'
    with pytest.raises(ValueError,match='ALREADY_RESERVED'):
        await reserve_full_body(m,'w',p,v,c,s,'task',req,tmp_path/'ledger')
    with pytest.raises(ValueError,match='CONSUMED'):
        await reserve_full_body(m,'w',p,v,c,s,'task',req,tmp_path/'different-cache')


@pytest.mark.asyncio
@pytest.mark.parametrize('change',['mock','prompt','source','provider'])
async def test_no_spend_on_changed_source_or_request(tmp_path,change):
    w,p,v,c,s=fixture(tmp_path);m=Memory(w);req=request_for(executable_full_body(w,p,v,c,s,'task'))
    if change=='mock':req['mock']=True
    if change=='prompt':req['prompt']='changed'
    if change=='source':(tmp_path/'source.txt').write_text('changed')
    if change=='provider':req['providerRequest']['input_overrides']['3']['prompt']='changed'
    with pytest.raises(ValueError):await reserve_full_body(m,'w',p,v,c,s,'task',req,tmp_path/'ledger')
    assert m.w.content['characterCastingAuthorizations']['task']['status']=='AUTHORIZED'

@pytest.fixture(autouse=True)
def restore_character_environment(monkeypatch):
    import os
    monkeypatch.setenv('DRAMA_CHARACTER_REPOSITORY_ROOT',os.environ.get('DRAMA_CHARACTER_REPOSITORY_ROOT',''))
