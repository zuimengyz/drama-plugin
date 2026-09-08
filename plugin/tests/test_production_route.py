"""OFFLINE fixtures only; no generated media or project quality claims."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from test_video_selection import fixture, evidence, decision, quote
from drama_plugin.visual.video_selection import ProductionRoute, qualify_route, route_input_gate
from drama_plugin.visual import production as p
from drama_plugin.hosts.route_production import operate, save_route, guard_direct_generation
from drama_plugin.hosts.comfy_video import verify_execution

def route(tmp_path):
 r,c,*_=fixture(tmp_path)
 data=c.model_dump(mode='json'); data['cost']['components']={'input_I':5,'video':200,'audio':0,'references':2,'addons':0,'correction':10}
 return ProductionRoute(route_id='R',work_id='W',stage_id='v206',creative_fingerprint='a'*64,
  video_targets=['S1'],requirements={'controls':['FIRST_FRAME','NATIVE_AUDIO'],'duration_seconds':8,'aspect_ratio':'16:9','sound':'NATIVE','language':'en','shot_type':'PERSON_PROP'},candidate=data,
  inputs=[dict(target_id='I',purpose='START',role='FIRST_FRAME',for_targets=['S1'],preparation='NEW',specification='recreate incompatible old image',rationale='priced5; no media required before plan',cost_key='input_I')],
  quality_thresholds={'action_narrative':'coherent lift'},stops=['max2 all video attempts'],fallback='requalify preserving events',generations_per_video_request=1,generation_count_evidence=evidence(),video_request_credits=100)

def test_joint_plan_before_existing_inputs(tmp_path):
 r=route(tmp_path); assert qualify_route(r)['eligible']
 assert route_input_gate(r,'I','START').source_media_id is None
 with pytest.raises(ValueError,match='NECESSARY'):route_input_gate(r,'whole-cast-package','START')

@pytest.mark.parametrize('key',['input_I','references','audio','addons','correction'])
def test_every_preparation_cost_required(tmp_path,key):
 d=route(tmp_path).model_dump();d['candidate']['cost']['components'].pop(key)
 assert not qualify_route(ProductionRoute.model_validate(d))['eligible']

@pytest.mark.parametrize('key,value',[('sounds',['SILENT']),('controls',['REFERENCE']),('combinations',[['FIRST_FRAME'],['NATIVE_AUDIO']])])
def test_cheap_hard_requirement_failure_rejected(tmp_path,key,value):
 d=route(tmp_path).model_dump();d['candidate'][key]=value
 assert not qualify_route(ProductionRoute.model_validate(d))['eligible']

def test_extra_generation_is_not_one_workflow(tmp_path):
 d=route(tmp_path).model_dump(); d['generations_per_video_request']=2
 assert not qualify_route(ProductionRoute.model_validate(d))['eligible']
 d['generations_per_video_request']=1;d['generation_count_evidence']['verified']=False
 assert not qualify_route(ProductionRoute.model_validate(d))['eligible']

class Memory:
 def __init__(self):self.work=SimpleNamespace(id='W',title='Offline',description='',content={'creative':'do not replace'})
 async def get_work(self,wid):assert wid=='W';return deepcopy(self.work)
 async def save_work(self,wid,title,content,description):assert wid=='W';self.work.content=deepcopy(content)

@pytest.mark.asyncio
async def test_formal_entry_no_route_no_budget_no_provider(tmp_path):
 m=Memory()
 with pytest.raises(ValueError,match='FORMAL_ROUTE'):await operate(m,'W','check-input',{'target_id':'I','purpose':'START'})
 await save_route(m,'W',route(tmp_path).model_dump(mode='json'))
 with pytest.raises(ValueError,match='BUDGET'):await operate(m,'W','check-input',{'target_id':'I','purpose':'START'})
 with pytest.raises(Exception,match='RESERVATION'):await guard_direct_generation(m,{'workId':'W'})
 assert 'productionStage' not in m.work.content and m.work.content['creative']=='do not replace'

@pytest.mark.asyncio
async def test_formal_stage_cannot_reset_and_wrong_work_rejected(tmp_path):
 m=Memory();raw=route(tmp_path).model_dump(mode='json');await save_route(m,'W',raw)
 await operate(m,'W','init-stage',{'authorization_ref':'OFFLINE ONLY','budget_credits':300})
 with pytest.raises(ValueError,match='RESTORE_EXISTING'):await operate(m,'W','init-stage',{'authorization_ref':'OFFLINE ONLY','budget_credits':300})
 raw['work_id']='OLD'
 with pytest.raises(ValueError,match='WORK_MISMATCH'):await save_route(m,'W',raw)

def test_technical_recreation_keeps_original_call_and_video_limit(tmp_path,monkeypatch):
 monkeypatch.setattr(p,'video_verifier',verify_execution)
 r=route(tmp_path);d=decision(tmp_path)
 s=p.new_stage(stage_id='v206',authorization_ref='OFFLINE',budget_credits=400,frames=[d],protected_targets=[],production_route=r.model_dump(mode='json'))
 a=p.reserve(s,'S1',**quote(d));p.record_result(s,attempt_id=a['attempt_id'],status='NOT_CREATED',job_id=None,evidence='OFFLINE provider confirms')
 b=p.retry_not_created(s,attempt_id=a['attempt_id'],evidence='OFFLINE confirmed',**quote(d))
 assert len(s['attempts'])==2 and a['status']=='NOT_CREATED' and b['call_reason']=='TECHNICAL_RETRY'
 p.record_result(s,attempt_id=b['attempt_id'],status='NOT_CREATED',job_id=None,evidence='OFFLINE confirms')
 with pytest.raises(ValueError,match='EXHAUSTED'):p.retry_not_created(s,attempt_id=b['attempt_id'],evidence='OFFLINE',**quote(d))
 assert p.exposure(s)==200

def test_route_change_cannot_relabel_model(tmp_path,monkeypatch):
 monkeypatch.setattr(p,'video_verifier',verify_execution)
 r=route(tmp_path);d=decision(tmp_path)
 s=p.new_stage(stage_id='v206',authorization_ref='OFFLINE',budget_credits=400,frames=[],protected_targets=[],production_route=r.model_dump(mode='json'))
 d['candidate']['graph_hash']='b'*64
 with pytest.raises(ValueError,match='DIFFERS_FROM_ROUTE'):p._route_frame_gate(s,d)

def test_video_cannot_rebind_creative_source_or_formal_shot(tmp_path):
 r=route(tmp_path).model_dump(mode='json');r['requirements']['shots']={'S1':'EXPECTED'}
 s={'production_route':r,'attempts':[]};d=decision(tmp_path)
 with pytest.raises(ValueError,match='FORMAL_SHOT_CHANGED'):p._route_frame_gate(s,d)
 d['requirements']['shot_id']='EXPECTED';d['requirements']['source_fingerprint']='b'*64
 with pytest.raises(ValueError,match='CREATIVE'):p._route_frame_gate(s,d)

def test_explicit_no_cap_preserves_balance_and_call_limits(tmp_path,monkeypatch):
 monkeypatch.setattr(p,'video_verifier',verify_execution)
 r=route(tmp_path);d=decision(tmp_path)
 kwargs=dict(stage_id='v206',authorization_ref='OFFLINE explicit no monetary cap',budget_credits=None,frames=[d],protected_targets=[],production_route=r.model_dump(mode='json'))
 with pytest.raises(ValueError,match='BUDGET'):p.new_stage(**kwargs)
 s=p.new_stage(**kwargs,no_monetary_cap=True)
 low=quote(d);low['balance']['available_credits']=50
 with pytest.raises(ValueError,match='BALANCE'):p.reserve(s,'S1',**low)
 assert p.reserve(s,'S1',**quote(d))['reserved_credits']==100
 assert s['stage']['budget_credits'] is None and s['stage']['no_monetary_cap']

@pytest.mark.asyncio
async def test_usage_observation_preserves_unknown_reservation(tmp_path):
 m=Memory();await save_route(m,'W',route(tmp_path).model_dump(mode='json'))
 await operate(m,'W','init-stage',{'authorization_ref':'OFFLINE','budget_credits':300})
 s=m.work.content['productionStage']
 s['attempts']=[dict(attempt_id='a',shot_id='I',job_id='j',credits=None,reserved_credits=12,status='COMPLETED'),dict(attempt_id='b',shot_id='I',job_id='k',credits=None,reserved_credits=12,status='COMPLETED')]
 payload=dict(attempt_id='a',job_id='j',event_id='u',credits=9.5,evidence='OFFLINE provider display estimate')
 result=await operate(m,'W','usage',payload)
 assert result['result']['invoiceSettlement']=='UNKNOWN'
 assert result['state']['attempts'][0]['credits'] is None and p.exposure(result['state'])==24
 assert (await operate(m,'W','usage',payload))['result']['usageRecorded']
 with pytest.raises(ValueError,match='ALREADY_LINKED'):
  await operate(m,'W','usage',{**payload,'attempt_id':'b','job_id':'k'})
