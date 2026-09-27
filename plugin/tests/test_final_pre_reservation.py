"""Small unit fixtures; real current-Work sweep additionally exercises all Host gates."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import pytest
from drama_plugin.visual import production as p
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.contracts.video import request_fingerprint
from drama_plugin.visual.history import remember
from test_official_video_providers import request
from test_video_selection import decision,quote
from test_cost_authority import classified


def state():
 v=request();old={'schema':'video-decision-v1','stage_id':'stage','spec':{'shot_id':'S'},'request':{'videoRequest':v.model_dump(mode='json',by_alias=True)}}
 old['fingerprint']=fp(old)
 new=deepcopy(old);new['request']['videoRequest']['seed']=123;new['fingerprint']=fp({k:v for k,v in new.items() if k!='fingerprint'})
 a=dict(attempt_id='old',shot_id='S',ordinal=1,frame_fingerprint=old['fingerprint'],request=old['request'],request_fingerprint=fp(old['request']),status='NOT_CREATED',job_id=None,credits=None,reserved_credits=13,
        video_task=dict(provider='seedance',model='seedance-2-mini',clientRequestId='old',requestFingerprint=request_fingerprint(v),status='NOT_CREATED'))
 s=dict(stage={'id':'stage'},production_route={'route_id':'R'},frames={'S':new},attempts=[a],pause=None,pilots=['S'],remediations=[],route_revisions=[])
 ref=remember(s,old);a['frame_ref']=ref;s['plan_fingerprint']=fp(s['frames'])
 s['remediations']=[dict(reason='approved new execution',after_attempt=1,target='S',previous_frame_ref=ref,frame_fingerprint=new['fingerprint'])]
 return s,old,new


def test_new_reservation_preserves_noncreation_and_unknown_exposure(monkeypatch):
 s,old,new=state();prior=deepcopy(s['attempts'][0]);exposure=p.exposure(s)
 monkeypatch.setattr(p,'verify_visual',lambda *a,**k:None)
 monkeypatch.setattr(p,'_stage_gate',lambda *a:13)
 a=p.reserve(s,'S')
 assert a['attempt_id']!='old' and a['supersedes_attempt_id']=='old'
 assert s['attempts'][0]['replan_status']=='SUPERSEDED_BY_REPLAN'
 assert {k:s['attempts'][0][k] for k in prior}==prior
 assert p.exposure(s)==exposure+13 and s['attempts'][0]['credits'] is None
 assert len(s['attempts'])==2


@pytest.mark.parametrize('fault',['job','media','unknown','reserved','no_lineage','changed_request','same_request','wrong_receipt'])
def test_strict_noncreation_lineage(fault):
 s,old,new=state();a=s['attempts'][0]
 if fault=='job':a['video_task']['providerTaskId']='job'
 elif fault=='media':a['delivery']={'mediaId':'media'}
 elif fault=='unknown':a['status']='UNKNOWN'
 elif fault=='reserved':a['status']='RESERVED'
 elif fault=='no_lineage':s['remediations']=[]
 elif fault=='changed_request':new=deepcopy(new);new['request']['videoRequest']['seed']=456;new['fingerprint']=fp({k:v for k,v in new.items() if k!='fingerprint'})
 elif fault=='same_request':new=old
 else:a['video_task']['clientRequestId']='someone-else'
 assert p._not_created_replan_lineage(s,a,new) is None


def test_same_request_retry_still_uses_existing_path(monkeypatch):
 s,old,new=state();s['frames']['S']=old;s['plan_fingerprint']=fp(s['frames'])
 monkeypatch.setattr(p,'verify_visual',lambda *a,**k:None);monkeypatch.setattr(p,'_stage_gate',lambda *a:13)
 a=p.retry_not_created(s,attempt_id='old',evidence='provider confirmed no task',quote={},balance={})
 assert a['call_reason']=='TECHNICAL_RETRY' and a['retry_of']=='old'
 assert 'replan_status' not in s['attempts'][0]


def fixed_case(tmp_path):
 d=decision(tmp_path);d['candidate']['cost']=classified(d['candidate']['cost'])
 old=dict(source='fixed policy',checked_at='1999-01-01T00:00:00Z',expires_at='1999-01-02T00:00:00Z',verified=True)
 d['candidate']['cost']['evidence']=old
 for r in d['candidate']['cost']['resolutions'].values():
  if r['authority']=='PROVIDER_QUOTE':r['authority']='INTERNAL_FIXED'
  r['evidence']=old
 s={'stage':{'id':d['stage_id'],'budget_credits':1000,'protected_targets':[]},'attempts':[]}
 return s,d,quote(d,amount=200)


def test_fixed_policy_age_budget_and_unknown_spend(tmp_path):
 s,d,q=fixed_case(tmp_path)
 assert p._stage_gate(s,d,d['request'],q['quote'],q['balance'])==200
 s['attempts']=[dict(credits=None,reserved_credits=900,status='NOT_CREATED',job_id=None)]
 with pytest.raises(ValueError,match='BUDGET'):p._stage_gate(s,d,d['request'],q['quote'],q['balance'])
 assert s['attempts'][0]['credits'] is None


def test_dynamic_quotes_and_balance_still_expire(tmp_path):
 s,d,q=fixed_case(tmp_path)
 d['candidate']['cost']['resolutions']['video']['authority']='PROVIDER_QUOTE'
 with pytest.raises(ValueError,match='COST_UNRESOLVED'):p._stage_gate(s,d,d['request'],q['quote'],q['balance'])
 d['candidate']['cost']['resolutions']['video']['authority']='INTERNAL_FIXED'
 q['balance']['evidence']['expires_at']='1999-01-02T00:00:00Z'
 with pytest.raises(ValueError):p._stage_gate(s,d,d['request'],q['quote'],q['balance'])


@pytest.mark.parametrize('field,value',[('creative_fingerprint','0'*64),('candidate.model','nonexistent'),('candidate.cost.components.video',1)])
def test_changed_route_model_or_cost_binding_rejected(tmp_path,monkeypatch,field,value):
    from drama_plugin.hosts.comfy_video import verify_execution
    monkeypatch.setattr(p,"video_verifier",verify_execution)
    from test_production_route import route
    from test_video_selection import decision,quote
    r=route(tmp_path).model_dump(mode='json');d=decision(tmp_path)
    s=p.new_stage(stage_id='v206',authorization_ref='offline',budget_credits=250,frames=[d],protected_targets=[],production_route=r)
    node=s['production_route'];parts=field.split('.')
    for part in parts[:-1]:node=node[part]
    node[parts[-1]]=value
    q=quote(d)
    with pytest.raises(ValueError):p._stage_gate(s,d,d['request'],q['quote'],q['balance'])


def test_changed_budget_unit_invalidates_existing_quote(tmp_path):
    s,d,q=fixed_case(tmp_path);s['stage']['budget_unit']='USD'
    with pytest.raises(ValueError,match='BUDGET_UNIT'):p._stage_gate(s,d,d['request'],q['quote'],q['balance'])
