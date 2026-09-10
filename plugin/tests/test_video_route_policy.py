"""Offline synthetic evidence only, never a production authorization."""
import json, os, subprocess, sys
from pathlib import Path
from copy import deepcopy
import pytest
from drama_plugin.config import load_config, VideoRoutePolicy as Policy
from drama_plugin.config.video_route import MODEL_KEYS, canonical_model_key
from drama_plugin.exceptions import ConfigurationError
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual.video_selection import choose, qualify, seal_decision, verify_decision
from drama_plugin.hosts.comfy_video import NODES, compile_request
from test_video_selection import fixture
from seedance_helpers import seed_fixture

def policy(mode='PREFER', model='seedance-2.5', fallbacks=('minimax-h3','flux-3')):
 return Policy(mode=mode,preferred_model=model,fallbacks=fallbacks)
def candidates(tmp_path):
 r,c,*_=fixture(tmp_path)
 return r,[c.model_copy(update={'candidate_id':key,'model':label,'variant':label}) for key,label in [('seedance-2.5','Seedance 2.5'),('minimax-h3','MiniMax H3'),('flux-3','FLUX 3')]]
def test_identity():
 assert MODEL_KEYS=={canonical_model_key(n['model']) for n in NODES.values()}
def test_auto(tmp_path):
 r,cs=candidates(tmp_path);p=load_config(environment={}).video_route_policy;a=choose(r,cs,policy=p)
 expected=[qualify(r,c) for c in cs]
 assert a['candidates']==expected
 assert a['selected']==sorted(expected,key=lambda v:(v['qualification']!='QUALIFIED',v['incremental_credits'],v['candidate_id']))[0]['candidate_id']
 assert a['route_policy_resolution']['source']=='DEFAULT_AUTO'
@pytest.mark.parametrize('mode',['AUTO','auto','PREFER','prefer','PIN','pin'])
def test_modes(mode):assert policy(mode).mode==mode.upper()
@pytest.mark.parametrize('mode',['FASTEST','CHEAPEST','SEEDANCE_ONLY'])
def test_bad_mode(mode):
 with pytest.raises(ValueError):policy(mode)
@pytest.mark.parametrize('mode',['PREFER','PIN'])
def test_required(mode):
 with pytest.raises(ValueError,match='PREFERRED_MODEL_REQUIRED'):policy(mode,' ')
@pytest.mark.parametrize('key,value',[('DRAMA_PLUGIN_VIDEO_MODEL_PREFERRED','typo'),('DRAMA_PLUGIN_VIDEO_MODEL_FALLBACKS','flux-3,typo')])
def test_unknown(key,value):
 with pytest.raises(ConfigurationError,match='UNKNOWN_MODEL_KEY'):load_config(environment={key:value})
def test_env_normalization():
 assert load_config(environment={'DRAMA_PLUGIN_VIDEO_ROUTE_MODE':' '}).video_route_policy.source=='DEFAULT_AUTO'
 p=load_config(environment={'DRAMA_PLUGIN_VIDEO_ROUTE_MODE':' prefer ','DRAMA_PLUGIN_VIDEO_MODEL_PREFERRED':'seedance-2.5','DRAMA_PLUGIN_VIDEO_MODEL_FALLBACKS':' seedance-2.5, minimax-h3, ,flux-3,minimax-h3'}).video_route_policy
 assert p.source=='PLUGIN_ENV_DEFAULT' and p.sequence()==('seedance-2.5','minimax-h3','flux-3')
def test_prefer_qualification(tmp_path):
 r,cs=candidates(tmp_path);a=choose(r,cs,policy=policy())
 assert a['selected']=='seedance-2.5' and a['candidates']==[qualify(r,c) for c in cs]
 assert a['candidates'][0]['qualification']=='LIMITED_TRIAL'
 assert choose(r,cs,policy=policy(),trial=False)['selected'] is None
 assert choose(r,cs,policy=policy(),task_policy=policy('PIN','minimax-h3'),trial=False)['selected'] is None

def test_fallback(tmp_path):
 r,cs=candidates(tmp_path);cs[0]=cs[0].model_copy(update={'controls':(),'combinations':()})
 a=choose(r,cs,policy=policy());assert a['selected']=='minimax-h3'
 assert 'MISSING_REQUIRED_CONTROL' in a['route_policy_resolution']['attempts'][0]['reason']
 assert choose(r,cs,policy=policy(fallbacks=('flux-3','minimax-h3')))['selected']=='flux-3'
 assert choose(r,cs,policy=policy(fallbacks=()))['selected'] is None
 cs=[c.model_copy(update={'durations':()}) for c in cs]
 assert choose(r,cs,policy=policy())['selected'] is None

def test_pin(tmp_path,monkeypatch):
 import drama_plugin.visual.video_selection as v
 r,cs=candidates(tmp_path);called=[];original=v.qualify
 def spy(r,c,**kw):called.append(c.model);return original(r,c,**kw)
 monkeypatch.setattr(v,'qualify',spy)
 a=choose(r,cs,policy=policy('PIN'))
 assert called==['Seedance 2.5'] and a['selected']=='seedance-2.5'
 assert a['route_policy_resolution']['fallbacks_state']=='INACTIVE'
 cs[0]=cs[0].model_copy(update={'durations':()})
 assert choose(r,cs,policy=policy('PIN'))['selected'] is None

def test_override(tmp_path):
 r,cs=candidates(tmp_path);a=choose(r,cs,policy=policy(),task_policy=policy('PIN','minimax-h3'))
 assert a['selected']=='minimax-h3' and a['route_policy_resolution']['source']=='TASK_OVERRIDE'

def test_price_and_dry_permission(tmp_path):
 r,cs=candidates(tmp_path);cs[0]=cs[0].model_copy(update={'cost':cs[0].cost.model_copy(update={'components':{'video':None}})})
 assert choose(r,cs,policy=policy('PIN'))['selected'] is None
 a=choose(r,cs,policy=policy('PIN'),dry_run=True)
 assert a['selected']=='seedance-2.5' and not a['candidates'][0]['eligible'] and a['route_policy_resolution']['dry_run_only']
 with pytest.raises(ValueError,match='INELIGIBLE'):seal_decision(r,cs[0],{},stage_id='offline',rationale='offline',comparisons=[],fallback='none',policy_resolution=a['route_policy_resolution'])

def test_seal(tmp_path,monkeypatch):
 r,c,g,s,a=fixture(tmp_path);request=compile_request(r,c,g,s,a['bindings'],r.frozen_creative['motion_prompt'])
 policy_result=choose(r,[c],policy=policy('PIN','flux-3'))['route_policy_resolution']
 d=seal_decision(r,c,request,stage_id='offline',rationale='offline',comparisons=[],fallback='none',policy_resolution=policy_result,dry_run=True);frozen=deepcopy(d)
 monkeypatch.setenv('DRAMA_PLUGIN_VIDEO_ROUTE_MODE','pin');monkeypatch.setenv('DRAMA_PLUGIN_VIDEO_MODEL_PREFERRED','seedance-2.5')
 assert load_config().video_route_policy.preferred_model=='seedance-2.5'
 verify_decision(d,allow_dry_run=True);assert d==frozen
 policy_result['effective_policy']['mode']='AUTO';assert d==frozen
 with pytest.raises(ValueError,match='DRY_RUN_REQUEST'):verify_decision(d)
 d['route_policy_resolution']['effective_policy']['preferred_model']='seedance-2.5'
 with pytest.raises(ValueError,match='DECISION_CHANGED'):verify_decision(d,allow_dry_run=True)
 d['fingerprint']=fp({k:v for k,v in d.items() if k!='fingerprint'})
 with pytest.raises(ValueError,match='POLICY_'):verify_decision(d,allow_dry_run=True)

def test_reference(tmp_path):
 r,c,g,s,a=seed_fixture(tmp_path);r=r.model_copy(update={'reference_duties':()})
 with pytest.raises(ValueError):choose(r,[c],policy=policy('PIN'),dry_run=True)

def test_architecture():
 root=Path(__file__).parents[1]
 for folder in ['src/drama_plugin/hosts','skills','src/drama_plugin/visual']:
  for p in (root/folder).rglob('*.py'):assert 'DRAMA_PLUGIN_VIDEO_' not in p.read_text(),p

def test_ownership(tmp_path):
 root=Path(__file__).parents[3];p=tmp_path/'drama-plugin.env';p.write_text('DRAMA_PLUGIN_VIDEO_ROUTE_MODE=auto\nDRAMA_PLUGIN_VIDEO_MODEL_PREFERRED=seedance-2.5\nDRAMA_PLUGIN_VIDEO_MODEL_FALLBACKS=minimax-h3,flux-3\n')
 for owner,success in [('drama-plugin',True),('mcp-host',False),('drama-service',False)]:
  result=subprocess.run([sys.executable,str(root/'scripts/runtime-env-ownership.py'),owner,str(p)],capture_output=True,text=True)
  assert (result.returncode==0)==success,result.stderr

def test_cli(tmp_path):
 r,c,g,s,a=fixture(tmp_path);data={'requirements':r.model_dump(mode='json'),'candidate':c.model_dump(mode='json'),'host_adapter':a,'stage_id':'offline','rationale':'offline','fallback':'none'}
 inp=tmp_path/'request.json';inp.write_text(json.dumps(data));out=tmp_path/'out'
 script=Path(__file__).parents[1]/'skills/shot-production/scripts/compile_video.py'
 env={**os.environ,'DRAMA_PLUGIN_VIDEO_ROUTE_MODE':'pin','DRAMA_PLUGIN_VIDEO_MODEL_PREFERRED':'seedance-2.5'}
 cmd=[sys.executable,str(script),'--input',str(inp),'--output',str(out)]
 result=subprocess.run(cmd,env=env,capture_output=True,text=True)
 assert result.returncode!=0 and 'NO_EXECUTABLE_CANDIDATE' in result.stderr
 data['task_route_policy']={'mode':'PIN','preferred_model':'flux-3'};inp.write_text(json.dumps(data))
 result=subprocess.run(cmd,env=env,capture_output=True,text=True)
 assert result.returncode==0,result.stderr
 sealed=json.loads((out/'sealed-request.json').read_text())
 assert sealed['route_policy_resolution']['source']=='TASK_OVERRIDE' and sealed['dry_run_only'] and not sealed['submission_allowed']

@pytest.mark.asyncio
async def test_formal_plan_entry_consumes_policy_before_write(tmp_path):
 from test_production_route import route, Memory
 from drama_plugin.hosts.route_production import save_route
 from drama_plugin.visual.video_selection import choose_routes
 m=Memory();raw=route(tmp_path).model_dump(mode='json');before=deepcopy(m.work.content)
 with pytest.raises(ValueError,match='NO_EXECUTABLE_CANDIDATE'):
  await save_route(m,'W',raw,policy=policy('PIN'))
 assert m.work.content==before
 await save_route(m,'W',raw,policy=policy('PIN','flux-3'))
 assert m.work.content['productionPolicy']['videoRoutePolicyResolution']['selected_model']=='flux-3'
 assert choose_routes([route(tmp_path)],policy=policy('PIN'))['selected'] is None

@pytest.mark.parametrize('authorization,budget',[('',1000),('OFFLINE',None),('OFFLINE',0)])
def test_policy_is_not_stage_authorization(tmp_path,authorization,budget):
 from drama_plugin.visual import production
 r,c,g,s,a=fixture(tmp_path);choice=choose(r,[c],policy=policy('PIN','flux-3'))
 assert choice['selected']==c.candidate_id
 d=seal_decision(r,c,compile_request(r,c,g,s,a['bindings'],r.frozen_creative['motion_prompt']),stage_id='offline',rationale='offline',comparisons=[],fallback='none',policy_resolution=choice['route_policy_resolution'])
 with pytest.raises(ValueError,match='EXPLICIT_STAGE_BUDGET_REQUIRED'):
  production.new_stage(stage_id='offline',authorization_ref=authorization,budget_credits=budget,frames=[d],protected_targets=[])


def test_config_yaml_env_task(tmp_path):
 p=tmp_path/'config.yaml';p.write_text('video_route_policy:\n  mode: prefer\n  preferred_model: seedance-2.5\n')
 c=load_config(p,environment={});assert c.video_route_policy.source=='PLUGIN_ENV_DEFAULT'
 c=load_config(p,environment={'DRAMA_PLUGIN_VIDEO_ROUTE_MODE':'pin','DRAMA_PLUGIN_VIDEO_MODEL_PREFERRED':'minimax-h3'})
 assert c.video_route_policy.mode=='PIN' and c.video_route_policy.preferred_model=='minimax-h3'


def test_identity_conflict(tmp_path):
 r,cs=candidates(tmp_path);cs[0]=cs[0].model_copy(update={'capability':{'model_key':'flux-3'}})
 with pytest.raises(ValueError,match='MODEL_IDENTITY_MISMATCH'):choose(r,cs,policy=policy())
