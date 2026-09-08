"""Synthetic events only. They never enter the delivered workbook."""
from copy import deepcopy
from test_production_route import route
from drama_plugin.visual.audit_view import project
import pytest

def work(tmp_path, attempts):
 return {'id':'W','title':'OFFLINE','content':{'productionRoute':route(tmp_path).model_dump(mode='json'),'productionStage':{'attempts':attempts}}}
def event(n,status='COMPLETED',**extra):
 return {'attempt_id':str(n),'call_id':str(n),'shot_id':'S1','status':status,'job_id':('j'+str(n)) if status in ('COMPLETED','FAILED') else None,
         'media_kind':'VIDEO','credits':None,'call_reason':'INITIAL',**extra}
def test_no_calls_no_example_spend(tmp_path):
 v=project(work(tmp_path,[event(0,'RESERVED')]))
 assert v['calls']==[] and v['targets'][-1][5] is None
def test_first_failure_survives_successful_rework_and_reexport(tmp_path):
 a=event(1,review_status='FAIL',review={'evidence':'OFFLINE failure'})
 b=event(2,review_status='PASS',call_reason='CONTENT_REWORK')
 w=work(tmp_path,[a,b,b]);v=project(w)
 assert len(v['calls'])==2 and v['targets'][-1][5]=='失败'
 assert project(w)==v and v['calls'][1][3]=='内容返工'
def test_technical_noncreation_and_unknown_are_calls_not_created(tmp_path):
 v=project(work(tmp_path,[event(1,'NOT_CREATED'),event(2,'UNKNOWN',call_reason='TECHNICAL_RETRY')]))
 assert len(v['calls'])==2 and [c[4] for c in v['calls']]==['确认未创建','结果不明']
 assert v['targets'][-1][5] is None
def test_settlement_and_adoption_independent_no_currency_guess(tmp_path):
 a=event(1,credits=12,billing_event_id='bill',review_status='PASS',technical={'probe':{'format':{'duration':'6'}}})
 v=project(work(tmp_path,[a]));assert v['calls'][0][7]==12 and v['calls'][0][8] is None and v['calls'][0][10] is None

def test_provider_credit_estimate_never_becomes_settlement(tmp_path):
 a=event(1,reserved_credits=12,provider_usage={'credits':9.5,'event_id':'usage-only'})
 v=project(work(tmp_path,[a]))
 assert v['calls'][0][5]=='未知/未结算' and v['calls'][0][7:9]==[None,None]
 assert v['usage']==[[9.5,12,'usage-only']]
def test_same_bytes_adoption_intervals_not_double_counted(tmp_path):
 a=event(1,user_adoption='USER_SELECTED',output_hash='a'*64,adopted_intervals=[[0,4],[2,5]],technical={'probe':{'duration':6}})
 b=event(2,user_adoption='USER_SELECTED',output_hash='a'*64,adopted_intervals=[[1,6]],technical={'probe':{'duration':6}})
 v=project(work(tmp_path,[a,b]));assert [c[10] for c in v['calls']]==[5,1]
def test_scope_and_duplicate_job_conflicts_stop(tmp_path):
 w=work(tmp_path,[event(1),event(2,job_id='j1')])
 with pytest.raises(ValueError,match='TWICE'):project(w)
 w=work(tmp_path,[event(1,shot_id='OLD-C16')])
 with pytest.raises(ValueError,match='OUTSIDE'):project(w)
