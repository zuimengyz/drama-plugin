"""OFFLINE SIMULATION ONLY. Synthetic inputs and outcomes are not project quality evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest

from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual.video_selection import (Requirements, Candidate, choose, qualify, seal_decision, verify_decision)
from drama_plugin.hosts.comfy_video import inspect_graph, compile_request, verify_execution
from drama_plugin.visual import production as p


def evidence():
    now = datetime.now(timezone.utc)
    return dict(source='OFFLINE SIMULATION', checked_at=now.isoformat(),
                expires_at=(now + timedelta(hours=1)).isoformat(), verified=True)


def fixture(tmp_path, target='S1'):
    path = tmp_path / 'input.bin'; path.write_bytes(b'OFFLINE IMAGE SIMULATION')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = tmp_path / 'upload.json'; receipt.write_text(json.dumps({'name': 'upload.png', 'content_hash': digest}))
    graph = {'nodes': [
        {'id': 1, 'type': 'LoadImage'},
        {'id': 2, 'type': 'Flux3ImageToVideoNode', 'inputs': [{'name': 'keyframes.image_0', 'link': 1}]},
        {'id': 3, 'type': 'SaveVideo', 'inputs': [{'name': 'video', 'link': 2}]}],
        'links': [[1, 1, 0, 2, 0, 'IMAGE'], [2, 2, 0, 3, 0, 'VIDEO']]}
    params = {'duration': '8', 'resolution': '720p', 'placement': 'spread across the clip',
              'aspect_ratio': '16:9', 'generate_audio': True, 'seed': 42, 'safety_tolerance': 2}
    schema = {'id': 'offline-template', 'nodes': [
        {'id': '1', 'class_type': 'LoadImage', 'inputs': {'image': 'demo.png'}},
        {'id': '2', 'class_type': 'Flux3ImageToVideoNode', 'inputs': {**params, 'prompt': 'demo'}},
        {'id': '3', 'class_type': 'SaveVideo', 'inputs': {}}]}
    graphpath = tmp_path / 'graph.json'; graphpath.write_text(json.dumps(graph))
    schemapath = tmp_path / 'schema.json'; schemapath.write_text(json.dumps(schema))
    r = Requirements(work_id='W', scene_id='SC', shot_id='SHOT', target_id=target, shot_type='PERSON_PROP',
        source_fingerprint='a'*64, mode='SINGLE_IMAGE', controls=['FIRST_FRAME', 'NATIVE_AUDIO'],
        duration_seconds=8, aspect_ratio='16:9', sound='NATIVE', language='en',
        frozen_creative={'action': 'A lifts wing; B braces', 'dialogue': 'Hold it.', 'motion_prompt': 'A lifts wing; B braces. A says: Hold it.'},
        inputs=[dict(media_id='M', version='v1', content_hash=digest, target_id=target,
                     role='FIRST_FRAME', state='fixed', review_evidence='OFFLINE')],
        required=['wing lifted'], forbidden=['swap actors'])
    c = Candidate(candidate_id='c', model='FLUX 3', variant='FLUX 3', mode='SINGLE_IMAGE', template='offline-template',
        graph_hash=fp(graph), adapter_fingerprint=fp(inspect_graph(graph,schema)), parameters=params,
        layers={k: evidence() for k in ['official','interface','template','project']},
        controls=['FIRST_FRAME','NATIVE_AUDIO'], combinations=[['FIRST_FRAME','NATIVE_AUDIO']], durations=[8],
        aspect_ratios=['16:9'], sounds=['NATIVE'], languages=['en'], quality={'status':'UNKNOWN'},
        cost={'components':{'existing_input':0,'video':100,'reference':0,'enhancement':0,'correction':100},'evidence':evidence()})
    binding = {**r.inputs[0].model_dump(), 'local_path':str(path),'upload_name':'upload.png','upload_receipt':str(receipt)}
    adapter={'graph_path':str(graphpath), 'schema_path':str(schemapath), 'bindings':[binding]}
    return r,c,graph,schema,adapter


def decision(tmp_path, target='S1'):
    r,c,g,s,a = fixture(tmp_path,target)
    request=compile_request(r,c,g,s,a['bindings'],r.frozen_creative['motion_prompt'])
    return seal_decision(r,c,request,stage_id='v206',rationale='OFFLINE limited trial',comparisons=[],
                         fallback='only after content failure and requalification',host_adapter=a)


@pytest.fixture(autouse=True)
def host(monkeypatch):
    monkeypatch.setattr(p,'video_verifier',verify_execution)


def stage(tmp_path, **kw):
    return p.new_stage(stage_id='v206',authorization_ref='OFFLINE budget authorization',budget_credits=kw.get('budget',250),
                       frames=[decision(tmp_path)],protected_targets=['C07','C12'])


def quote(d, amount=100):
    return dict(quote={'request_fingerprint':fp(d['request']),'unit':'credits','conservative_credits':amount,
                       'uncertainty':[], 'evidence':evidence()},
                balance={'unit':'credits','available_credits':1000,'margin_credits':10,'evidence':evidence()})


def reserve(s):
    return p.reserve(s,'S1',**quote(s['frames']['S1']))


def complete(s,a,tmp_path,credits=None):
    output=tmp_path/'out.mp4';output.write_bytes(b'OFFLINE VIDEO SIMULATION')
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    p.record_result(s,attempt_id=a['attempt_id'],status='COMPLETED',job_id='job'+str(len(s['attempts'])),output_hash=digest,
                    evidence='OFFLINE result',credits=credits,billing_event_id='bill'+str(len(s['attempts'])) if credits is not None else None)
    p.inspect_output(s,attempt_id=a['attempt_id'],technical={'checks':{k:'PASS' for k in ['duration','dimensions','fps','audio','integrity','linkage']},'evidence':'OFFLINE probe','probe':{'duration':8}},
        copies=[{'job_id':a['job_id'],'content_hash':digest,'local_path':str(output),'upload_name':None,'media_id':None,'storage_object':None}],content_observation='PENDING_REVIEW')


def review(s,a,fail=False):
    keys=['IDENTITY','COSTUME','BLOCKING','PROP_STRUCTURE','PROP_STATE','SCENE','ANATOMY','MODERN_ARTIFACT','CROP','ACTION','CAMERA','DIALOGUE','SPEAKER','SOUND','CONTINUITY','ENDPOINTS','required:wing lifted','forbidden:swap actors']
    checks={k:'PASS' for k in keys}; findings=[]
    if fail:
        checks['ACTION']='FAIL';findings=[dict(category='ACTION',severity='MAJOR',remedy='REGENERATE',evidence='OFFLINE missing lift')]
    return p.Review(attempt_id=a['attempt_id'],output_hash=a['output_hash'],reviewer='OFFLINE',evidence='OFFLINE full review',checks=checks,findings=findings)


@pytest.mark.parametrize('change,expected',[
    ({'controls':['REFERENCE']},'MISSING_REQUIRED_CONTROL'),
    ({'combinations':[['FIRST_FRAME'],['NATIVE_AUDIO']]},'UNSUPPORTED_CONTROL_COMBINATION'),
    ({'sounds':['SILENT']},'REQUIRED_SOUND_OR_LANGUAGE_UNSUPPORTED'),
    ({'languages':['zh']},'REQUIRED_SOUND_OR_LANGUAGE_UNSUPPORTED'),
    ({'durations':[5]},'NARRATIVE_DURATION_UNSUPPORTED'),
    ({'mode':'START_END'},'MODE_MISMATCH'),
])
def test_cheap_incompatible_never_wins(tmp_path,change,expected):
    r,c,*_=fixture(tmp_path)
    bad=Candidate.model_validate({**c.model_dump(),**change,'candidate_id':'cheap','cost':{**c.cost.model_dump(),'components':{'video':1}}})
    result=choose(r,[bad,c]);assert result['selected']=='c'
    assert expected in result['candidates'][0]['exclusions']


def test_multiref_cannot_claim_timed_frames(tmp_path):
    r,c,*_=fixture(tmp_path);r=r.model_copy(update={'controls':('FIRST_FRAME','TIMED_IMAGE_AT_4S','NATIVE_AUDIO')})
    assert not qualify(r,c)['eligible']


def test_independent_layers_and_expiry(tmp_path):
    r,c,*_=fixture(tmp_path)
    for layer in ['official','interface','template','project']:
        data=c.model_dump();data['layers'][layer]['verified']=False
        assert not qualify(r,Candidate.model_validate(data))['eligible']
    d=decision(tmp_path)
    with pytest.raises(ValueError,match='EXPIRED'):
        verify_decision(d,now=datetime.now(timezone.utc)+timedelta(days=1))


def test_unknown_can_trial_never_expand_or_fabricate(tmp_path):
    r,c,*_=fixture(tmp_path)
    assert qualify(r,c)['qualification']=='LIMITED_TRIAL' and qualify(r,c)['eligible']
    assert not qualify(r,c,trial=False)['eligible']
    q=c.quality.model_copy(update={'status':'PASS'})
    assert not qualify(r,c.model_copy(update={'quality':q}))['eligible']
    q=c.quality.model_copy(update={'samples':1})
    assert not qualify(r,c.model_copy(update={'quality':q}))['eligible']


@pytest.mark.parametrize('field,value',[('duration','5'),('generate_audio',False),('placement','at times'),('aspect_ratio','1:1')])
def test_request_parameter_cannot_change_requirements(tmp_path,field,value):
    r,c,g,s,a=fixture(tmp_path);c=c.model_copy(update={'parameters':{**c.parameters,field:value}})
    with pytest.raises(ValueError):compile_request(r,c,g,s,a['bindings'],r.frozen_creative['motion_prompt'])


@pytest.mark.parametrize('mutation',['prompt','reference','param','graph','schema','receipt','bytes'])
def test_actual_entry_rejects_drift(tmp_path,mutation):
    d=decision(tmp_path);a=d['host_adapter']
    if mutation=='prompt':d['request']['input_overrides']['2']['prompt']='stand still'
    if mutation=='reference':d['request']['input_overrides']['1']['image']='other.png'
    if mutation=='param':d['request']['input_overrides']['2']['resolution']='1080p'
    if mutation in ['graph','schema']:
        path=Path(a[mutation+'_path']);x=json.loads(path.read_text());x['nodes'].append({'id':90,'type':'UnknownPaid'});path.write_text(json.dumps(x))
    if mutation=='receipt':Path(a['bindings'][0]['upload_receipt']).write_text('{}')
    if mutation=='bytes':Path(a['bindings'][0]['local_path']).write_bytes(b'changed')
    with pytest.raises((ValueError,KeyError)):verify_execution(d)


def test_unknown_and_hidden_graph_nodes_fail_closed(tmp_path):
    _,_,g,s,_=fixture(tmp_path)
    for kind in ['Unknown','MinimaxHailuo03ContextIRNode','MinimaxHailuo03RegenerateNode','ComfySwitchNode']:
        bad=deepcopy(g);bad['nodes'].append({'id':9,'type':kind})
        with pytest.raises(ValueError):inspect_graph(bad,s)


def test_budget_unsettled_restart_and_replan(tmp_path):
    s=stage(tmp_path,budget=150);a=reserve(s)
    assert p.exposure(s)==100
    p.record_result(s,attempt_id=a['attempt_id'],status='UNKNOWN',job_id='job1',evidence='OFFLINE timeout')
    s=json.loads(json.dumps(s))
    with pytest.raises(ValueError,match='NEEDS_OUTCOME'):reserve(s)
    a=s['attempts'][0];complete(s,a,tmp_path);p.record_review(s,review(s,a,fail=True))
    d=deepcopy(s['frames']['S1']);d['candidate']['parameters']['seed']=43;d['request']['input_overrides']['2']['seed']=43
    d['request_fingerprint']=fp(d['request']);d['fingerprint']=fp({k:v for k,v in d.items() if k!='fingerprint'})
    p.replan(s,frame=d,reason='OFFLINE seed change after missing lift, same creative requirements')
    with pytest.raises(ValueError,match='BUDGET'):reserve(s)
    assert s['attempts'][0]['credits'] is None and p.exposure(s)==100
    p.reconcile_billing(s,attempt_id=a['attempt_id'],job_id=a['job_id'],credits=40,billing_event_id='bill1')
    assert reserve(s)['ordinal']==2
    assert p.exposure(s)==140


def test_copies_not_generations_technical_not_content(tmp_path):
    s=stage(tmp_path);a=reserve(s);complete(s,a,tmp_path)
    assert len(s['attempts'])==1 and a['content_status']=='PENDING_REVIEW' and a['user_adoption']=='PENDING'
    copies=a['copies']*2
    p.inspect_output(s,attempt_id=a['attempt_id'],technical=a['technical'],copies=copies,content_observation='still needs listening')
    assert len(s['attempts'])==1 and p.exposure(s)==100
    with pytest.raises(ValueError,match='NEEDS_OUTCOME'):reserve(s)
    r=review(s,a);r=r.model_copy(update={'checks':{**r.checks,'SOUND':'UNKNOWN'}})
    with pytest.raises(ValueError,match='INCOMPLETE'):p.record_review(s,r)
    p.record_review(s,review(s,a));assert a['user_adoption']=='PENDING'
    with pytest.raises(ValueError,match='PASSED'):reserve(s)


def test_global_video_limit_and_new_campaign_cannot_clear_it(tmp_path):
    s=stage(tmp_path,budget=1000);a=reserve(s);complete(s,a,tmp_path);p.record_review(s,review(s,a,fail=True))
    d=deepcopy(s['frames']['S1']);d['candidate']['parameters']['seed']=43;d['request']['input_overrides']['2']['seed']=43
    d['request_fingerprint']=fp(d['request']);d['fingerprint']=fp({k:v for k,v in d.items() if k!='fingerprint'})
    p.replan(s,frame=d,reason='OFFLINE one targeted correction')
    a=reserve(s);complete(s,a,tmp_path);p.record_review(s,review(s,a,fail=True))
    assert len(s['attempts'])==2 and s['pause']=='TARGETED_REVISION_FAILED'
    with pytest.raises(ValueError,match='EXHAUSTED'):p.replan(s,frame=d,reason='try third model')
    with pytest.raises(ValueError,match='ONE_FORMAL_VIDEO'):p.replan(s,frame=decision(tmp_path,'S2'),reason='new campaign')
    assert p.exposure(s)==200


def test_quote_balance_unknown_cost_and_protection(tmp_path):
    s=stage(tmp_path);d=s['frames']['S1']
    for field,value in [('request_fingerprint','b'*64),('uncertainty',['GPU cost unknown']),('conservative_credits',float('nan'))]:
        q=quote(d);q['quote'][field]=value
        with pytest.raises(ValueError):p.reserve(s,'S1',**q)
    q=quote(d);q['balance']['available_credits']=100
    with pytest.raises(ValueError,match='BALANCE'):p.reserve(s,'S1',**q)
    with pytest.raises(ValueError,match='PROTECTED'):p.replan(s,frame=decision(tmp_path,'C07'),reason='OFFLINE')
    r,c,*_=fixture(tmp_path);bad=c.model_copy(update={'cost':c.cost.model_copy(update={'uncertainty':('unknown ref fee',)})})
    assert not qualify(r,bad)['eligible']


def test_scene_fit_precedes_quality_and_cost(tmp_path):
    r,c,*_=fixture(tmp_path)
    cheap=c.model_copy(update={'candidate_id':'cheap','fit_concerns':('adjacent continuity unverified',),
                              'cost':c.cost.model_copy(update={'components':{'video':1}})})
    assert choose(r,[cheap,c])['selected']=='c'
    assert c.cost.total()==200


def test_host_required_and_replan_cannot_change_action(tmp_path,monkeypatch):
    d=decision(tmp_path);s=stage(tmp_path)
    monkeypatch.setattr(p,'video_verifier',None)
    with pytest.raises(ValueError,match='HOST_VIDEO'):reserve(s)
    monkeypatch.setattr(p,'video_verifier',verify_execution)
    d['requirements']['frozen_creative']['action']='B lifts wing'
    d['spec']['frozen_creative']['action']='B lifts wing'
    d['fingerprint']=fp({k:v for k,v in d.items() if k!='fingerprint'})
    with pytest.raises(ValueError,match='CREATIVE'):p.replan(s,frame=d,reason='OFFLINE cheaper action')


def test_source_cli_persists_one_budget_and_exact_request(tmp_path):
    import subprocess,sys
    entry=Path(__file__).resolve().parents[1]/'skills/shot-production/scripts/visual_preflight.py'
    d=decision(tmp_path);init=tmp_path/'init.json';statepath=tmp_path/'stage.json'
    init.write_text(json.dumps(dict(stage_id='v206',authorization_ref='OFFLINE ONLY',budget_credits=300,frames=[d],protected_targets=['C07','C12'])))
    def run(*args):return subprocess.run([sys.executable,str(entry),*args],capture_output=True,text=True)
    assert run('init-stage','--state',str(statepath),'--input',str(init)).returncode==0
    q=tmp_path/'quote.json';q.write_text(json.dumps(quote(d)))
    result=run('reserve','--state',str(statepath),'--shot','S1','--input',str(q))
    assert result.returncode==0,result.stderr
    persisted=json.loads(statepath.read_text());returned=json.loads(result.stdout)
    assert persisted['attempts'][0]['request']==returned['request']==d['request']
    assert returned['stage_exposure_credits']==100
    assert run('reserve','--state',str(statepath),'--shot','S1','--input',str(q)).returncode!=0
    assert run('init-stage','--state',str(tmp_path/'reset.json'),'--input',str(init)).returncode!=0
    assert run('init','--state',str(tmp_path/'images.json'),'--input',str(init)).returncode!=0


def test_proven_no_job_can_safely_retry_but_unknown_cannot(tmp_path):
    s=stage(tmp_path);a=reserve(s)
    p.record_result(s,attempt_id=a['attempt_id'],status='UNKNOWN',job_id=None,evidence='OFFLINE transport timeout')
    with pytest.raises(ValueError):p.retry_not_created(s,attempt_id=a['attempt_id'],evidence='mere timeout',**quote(s['frames']['S1']))
    p.record_result(s,attempt_id=a['attempt_id'],status='NOT_CREATED',job_id=None,evidence='OFFLINE provider confirms no job')
    retried=p.retry_not_created(s,attempt_id=a['attempt_id'],evidence='OFFLINE proven prequeue failure',**quote(s['frames']['S1']))
    assert retried['attempt_id']==a['attempt_id'] and len(s['attempts'])==1 and p.exposure(s)==100


def test_shared_image_budget_and_counts(tmp_path):
    from test_visual_first_pass import material
    from drama_plugin.visual.frame_request import compile_frame
    imgs=[compile_frame(*material(tmp_path,sid='image'+str(i))) for i in range(3)]
    s=p.new_stage(stage_id='v206',authorization_ref='OFFLINE',budget_credits=250,frames=imgs,protected_targets=['C07','C12'])
    a=p.reserve(s,'image0',**quote(imgs[0],50))
    p.record_result(s,attempt_id=a['attempt_id'],status='FAILED',job_id='image-job',evidence='OFFLINE terminal failure')
    assert p.exposure(s)==50  # Failure is not a refund.
    with pytest.raises(ValueError,match='IMAGE_LIMIT'):
        p.replan(s,frame=compile_frame(*material(tmp_path,sid='image3')),reason='new campaign')
    assert len(s['attempts'])==1


def test_start_end_has_independent_same_target_ports(tmp_path):
    r,c,g,s,a=fixture(tmp_path)
    g['nodes'][1]['type']='MinimaxHailuo03FirstLastFrameNode'
    g['nodes'][1]['inputs']=[{'name':'first_frame','link':1},{'name':'last_frame','link':3}]
    g['nodes'].append({'id':4,'type':'LoadImage'});g['links'].append([3,4,0,2,1,'IMAGE'])
    s['nodes'][1]['class_type']='MinimaxHailuo03FirstLastFrameNode'
    s['nodes'].append({'id':'4','class_type':'LoadImage','inputs':{'image':'end.png'}})
    inspected=inspect_graph(g,s)
    assert inspected['mode']=='START_END' and inspected['image_slots']==['1','4']
    data=r.model_dump(mode='json');data['mode']='START_END';data['controls']=['FIRST_FRAME','LAST_FRAME']
    data['inputs'].append({**data['inputs'][0],'role':'LAST_FRAME','media_id':'end'})
    from drama_plugin.visual.video_selection import validate_requirements
    validate_requirements(Requirements.model_validate(data))
    data['inputs'][1]['target_id']='different-shot'
    with pytest.raises(ValueError,match='CROSS_TARGET'):validate_requirements(Requirements.model_validate(data))
    g['nodes'][1]['inputs'][1]['name']='model.reference_images.image_2'
    with pytest.raises(ValueError,match='COMBINATION'):inspect_graph(g,s)


def test_switch_model_carries_previous_spend(tmp_path):
    s=stage(tmp_path,budget=150);a=reserve(s);complete(s,a,tmp_path);p.record_review(s,review(s,a,fail=True))
    other=tmp_path/'other-model';other.mkdir()
    r,c,g,sc,adapter=fixture(other)
    g['nodes'][1]['type']='MinimaxHailuo03FirstLastFrameNode';g['nodes'][1]['inputs']=[{'name':'first_frame','link':1}]
    params={'model':'MiniMax H3','model.duration':8,'model.resolution':'2K','seed':42,'watermark':False}
    sc['id']='offline-h3';sc['nodes'][1].update(class_type='MinimaxHailuo03FirstLastFrameNode',inputs={**params,'model.prompt':'demo'})
    Path(adapter['graph_path']).write_text(json.dumps(g));Path(adapter['schema_path']).write_text(json.dumps(sc))
    c=c.model_copy(update={'candidate_id':'h3','model':'MiniMax H3','variant':'MiniMax H3','template':'offline-h3','graph_hash':fp(g),'adapter_fingerprint':fp(inspect_graph(g,sc)),'parameters':params})
    req=compile_request(r,c,g,sc,adapter['bindings'],r.frozen_creative['motion_prompt'])
    d=seal_decision(r,c,req,stage_id='v206',rationale='OFFLINE requalified fallback',comparisons=[],fallback='no further retries',host_adapter=adapter)
    p.replan(s,frame=d,reason='OFFLINE model switch after confirmed motion failure')
    with pytest.raises(ValueError,match='BUDGET'):reserve(s)
    assert p.exposure(s)==100 and len(s['attempts'])==1


def test_balance_observation_before_settlement_cannot_fund_next_attempt(tmp_path):
    s=stage(tmp_path);a=reserve(s);complete(s,a,tmp_path)
    old=quote(s['frames']['S1'])
    p.reconcile_billing(s,attempt_id=a['attempt_id'],job_id=a['job_id'],credits=100,billing_event_id='settled')
    with pytest.raises(ValueError,match='BALANCE_MUST_BE_REFRESHED_AFTER_SETTLEMENT'):
        p._stage_gate(s,s['frames']['S1'],s['frames']['S1']['request'],old['quote'],old['balance'])
