from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from drama_plugin.visual.frame_request import FrameSpec, Template, compile_frame, verify_compiled
from drama_plugin.visual.production import new_campaign, reserve, record_result, record_review, Review, resume, metrics
from drama_plugin.contracts.base import sha256_canonical


def material(tmp_path, sid='S1', state='fixed', delta=None):
    refs=[]
    for key,kind in [('w','CHARACTER'),('o','CHARACTER'),('glider','PROP')]:
        path=tmp_path/(key+'.png');path.write_bytes(('test-only-'+key).encode())
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        receipt=tmp_path/(key+'.receipt.json');receipt.write_text(json.dumps({'name':key+'.png','content_hash':digest}))
        refs.append(dict(entity_key=key,kind=kind,asset_id='asset-'+key,media_id='media-'+key,
                         version='r1',content_hash=digest,local_path=str(path),upload_name=key+'.png',
                         uploaded_hash=digest,upload_receipt=str(receipt),facts=key+' stable reviewed identity',
                         state='fixed',review='PASS'))
    actors=[dict(entity_key='w',label='Wilbur',identity='35, balding, clean-shaven',costume='grey shirt',
                 position='left beside wing',pose='standing',action='braces wing',gaze='toward pilot'),
            dict(entity_key='o',label='Orville',identity='31, wavy hair, moustache',costume='off-white shirt',
                 position='right inside cradle',pose='prone on stomach',action='holds control cord',gaze='toward Wilbur')]
    spec=FrameSpec(shot_id=sid,shot_fingerprint='1'*64,entry_state='grounded ready to launch',
                   composition='side view, both actors and skids visible',environment='sand, wood shed, daylight',
                   actors=actors,props=[dict(entity_key='glider',state=state,geometry='two fixed rear vertical fins; front horizontal elevator',
                    placement='wood skids on sand',forbidden=['engine','wheels'],reference_delta=delta)],
                   required=['pilot prone','two fixed rear fins'],forbidden=['engine','identity swap'],references=refs,
                   reference_lock={f"{r['asset_id']}/{r['media_id']}/{r['version']}":r['content_hash'] for r in refs},
                   shot_type='PERSON_PROP',target_size=(1536,1024),seed=20)
    graph={'nodes':[{'id':slot,'type':'LoadImage'} for slot in [2,3,10]] + [
        {'id':18,'type':'TestModel','inputs':[{'name':f'model.images.image_{i}','link':i} for i in [1,2,3]],
         'widgets_values_named':{'prompt':'example','seed':0,'model.width':1536,'model.height':1024}}],
        'links':[[i,slot,0,18,i,'IMAGE'] for i,slot in enumerate([2,3,10],1)]}
    graph_path=tmp_path/'graph.json';graph_path.write_text(json.dumps(graph))
    template=Template(name='test-only-template',model='test-only-model',evidence='offline fixture, not live capability',
                      graph_hash=sha256_canonical(graph),graph_path=str(graph_path),image_slots=['2','3','10'],prompt_node='18',output_size=(1536,1024),supported_types=['PERSON_PROP'])
    return spec,template


def frames(tmp_path):
    return [compile_frame(*material(tmp_path,f'S{i}')) for i in range(1,5)]


def outcome(state, attempt):
    record_result(state,attempt_id=attempt['attempt_id'],status='COMPLETED',job_id='job-'+attempt['attempt_id'],
                  output_hash='a'*64,evidence='offline provider fixture')


def review_for(state, attempt, category=None, minor=False):
    spec=state['frames'][attempt['shot_id']]['spec']
    checks={k:'PASS' for k in ['IDENTITY','COSTUME','BLOCKING','PROP_STRUCTURE','PROP_STATE','SCENE','ANATOMY','MODERN_ARTIFACT','CROP']}
    checks.update({'required:'+x:'PASS' for x in spec['required']})
    checks.update({'forbidden:'+x:'PASS' for x in spec['forbidden']})
    findings=[]
    if category:
        if not minor: checks[category]='FAIL'
        findings=[dict(category=category,severity='MINOR' if minor else 'MAJOR',evidence='test observation: '+category,
                       remedy='POSTPROCESS' if minor else 'REGENERATE')]
    return Review(attempt_id=attempt['attempt_id'],output_hash='a'*64,reviewer='offline-test',evidence='fixture observation',checks=checks,findings=findings)


def test_prompt_and_provider_slots_preserve_actor_blocking(tmp_path):
    spec,t=material(tmp_path);compiled=compile_frame(spec,t)
    ov=compiled['request']['input_overrides'];p=ov['18']['prompt']
    assert [ov[s]['image'] for s in ['2','3','10']]==['w.png','o.png','glider.png']
    assert 'Wilbur [w]' in p and 'pose=standing' in p and 'Orville [o]' in p and 'pose=prone on stomach' in p
    assert 'state NOW=fixed' in p and 'front horizontal elevator' in p
    assert 'no standing' not in p and 'Entry state only; leave room for subsequent action' not in p
    verify_compiled(compiled)
    compiled['request']['input_overrides']['2']['image']='o.png'
    with pytest.raises(ValueError,match='STALE'): verify_compiled(compiled)


@pytest.mark.parametrize('mutation,match',[
 ('missing','MISSING_STABLE'),('swap','RECEIPT_MISMATCH'),('hash','UPLOAD_HASH'),
 ('version','VERSION_NOT_LOCKED'),('label','DISTINCT_ACTOR'),('size','OUTPUT_ASPECT'),
 ('template','CANNOT_OVERRIDE'),('slot','DUPLICATE_PROVIDER'),('intent','INTENT_NOT_VERIFIED'),
 ('local','LOCAL_HASH'),('receipt','RECEIPT_MISMATCH')])
def test_request_rejects_paid_failure_modes(tmp_path,mutation,match):
    spec,t=material(tmp_path);s=spec.model_dump();v=t.model_dump()
    if mutation=='missing':s['references']=s['references'][1:];v['image_slots']=v['image_slots'][1:]
    if mutation=='swap':s['references'][0]['upload_name'],s['references'][1]['upload_name']=s['references'][1]['upload_name'],s['references'][0]['upload_name']
    if mutation=='hash':s['references'][0]['uploaded_hash']='b'*64
    if mutation=='version':s['references'][0]['version']='r2'
    if mutation=='label':s['actors'][1]['label']='Wilbur'
    if mutation=='size':s['target_size']=(1280,720)
    if mutation=='template':v['settings']={'prompt':'both seated'}
    if mutation=='slot':v['image_slots']=('2','2','10')
    if mutation=='intent':v['supported_types']=['SINGLE_STATIC']
    if mutation=='local':Path(s['references'][0]['local_path']).write_bytes(b'changed')
    if mutation=='receipt':Path(s['references'][0]['upload_receipt']).write_text('{}')
    with pytest.raises(ValueError,match=match):compile_frame(FrameSpec.model_validate(s),Template.model_validate(v))


def test_prop_state_delta_requires_new_risk_qualification(tmp_path):
    s,t=material(tmp_path,sid='S4',state='movable')
    with pytest.raises(ValueError,match='STATE_CONFLICT'):compile_frame(s,t)
    s=s.model_copy(update={'props':(s.props[0].model_copy(update={'reference_delta':'replace twin fixed fins with one movable rear rudder'}),)})
    f=compile_frame(s,t)
    assert 'STATE_TRANSITION:glider:movable' in f['risks']
    batch=frames(tmp_path);batch[3]=f
    assert 'S4' in new_campaign(batch)['pilots']


def test_cross_shot_identity_and_version_drift(tmp_path):
    batch=frames(tmp_path)
    s=deepcopy(batch[1]['spec']);s['actors'][0]['costume']='brown vest'
    batch[1]=compile_frame(FrameSpec.model_validate(s),Template.model_validate(batch[1]['template']))
    with pytest.raises(ValueError,match='COSTUME_DRIFT'):new_campaign(batch)
    batch=frames(tmp_path);s=deepcopy(batch[1]['spec']);s['references'][0]['version']='r2'
    r=s['references'][0];s['reference_lock'][f"{r['asset_id']}/{r['media_id']}/r2"]=r['content_hash']
    batch[1]=compile_frame(FrameSpec.model_validate(s),Template.model_validate(batch[1]['template']))
    with pytest.raises(ValueError,match='VERSION_DRIFT'):new_campaign(batch)


def test_pilot_then_expansion_and_pass_cannot_be_reworked(tmp_path):
    state=new_campaign(frames(tmp_path))
    with pytest.raises(ValueError,match='REPRESENTATIVE'):reserve(state,'S4')
    for sid in state['pilots']:
        attempt=reserve(state,sid)
        with pytest.raises(ValueError,match='NEEDS_OUTCOME'):reserve(state,'S4')
        outcome(state,attempt);record_review(state,review_for(state,attempt))
        with pytest.raises(ValueError,match='PASSED_SHOT'):reserve(state,sid)
    assert reserve(state,'S4')['ordinal']==1
    assert metrics(state)['first_pass_yield']==1


def test_two_failures_stop_and_resume_keeps_revision_budget(tmp_path):
    state=new_campaign(frames(tmp_path))
    for sid in ['S1','S2']:
        a=reserve(state,sid);outcome(state,a);record_review(state,review_for(state,a,'PROP_STRUCTURE'))
    assert state['pause']
    with pytest.raises(ValueError,match='PAUSED'):reserve(state,'S3')
    resume(state,reason='Reviewed reference conflict; preserve masters and enforce exact component count')
    a=reserve(state,'S1');assert a['ordinal']==2
    assert 'TARGETED CORRECTION' in a['request']['input_overrides']['18']['prompt']
    outcome(state,a);record_review(state,review_for(state,a,'PROP_STRUCTURE'))
    assert state['pause']=='TARGETED_REVISION_FAILED'
    with pytest.raises(ValueError):resume(state,reason='try again')
    assert metrics(state)['first_pass_yield']==0


def test_common_nonconsecutive_and_consecutive_different_failures(tmp_path):
    state=new_campaign(frames(tmp_path))
    for sid,category in [('S1','IDENTITY'),('S2',None),('S3','IDENTITY')]:
        a=reserve(state,sid);outcome(state,a);record_review(state,review_for(state,a,category))
    assert state['pause']=='COMMON_FAILURE_REPLAN'
    state=new_campaign(frames(tmp_path))
    for sid,category in [('S1','IDENTITY'),('S2','BLOCKING')]:
        a=reserve(state,sid);outcome(state,a);record_review(state,review_for(state,a,category))
    assert state['pause']=='CONSECUTIVE_FAILURE_REPLAN'


def test_minor_review_and_wrong_output_or_missing_evidence(tmp_path):
    state=new_campaign(frames(tmp_path));a=reserve(state,'S1');outcome(state,a)
    r=review_for(state,a,'COSMETIC',minor=True)
    with pytest.raises(ValueError,match='OUTPUT_MISMATCH'):record_review(state,r.model_copy(update={'output_hash':'b'*64}))
    checks=dict(r.checks);checks.pop('required:pilot prone')
    with pytest.raises(ValueError,match='CHECKS_MISSING'):record_review(state,r.model_copy(update={'checks':checks}))
    checks=dict(r.checks);checks['BLOCKING']='UNKNOWN'
    with pytest.raises(ValueError,match='INCOMPLETE'):record_review(state,r.model_copy(update={'checks':checks}))
    with pytest.raises(ValueError,match='DOWNGRADED'):record_review(state,review_for(state,a,'IDENTITY',minor=True))
    assert record_review(state,r)=='PASS_WITH_NOTES'
    assert metrics(state)['first_usable']==1


def test_uncertain_job_survives_restart_and_does_not_double_submit(tmp_path):
    state=new_campaign(frames(tmp_path));a=reserve(state,'S1')
    record_result(state,attempt_id=a['attempt_id'],status='UNKNOWN',job_id=None,evidence='timeout after send')
    state=json.loads(json.dumps(state))
    with pytest.raises(ValueError,match='NEEDS_OUTCOME'):reserve(state,'S2')
    record_result(state,attempt_id=a['attempt_id'],status='COMPLETED',job_id='recovered',output_hash='a'*64,evidence='same provider job recovered')
    record_review(state,review_for(state,state['attempts'][0]))
    assert len(state['attempts'])==1
    assert metrics(state)['billing_unknown_count']==1


def test_cli_reservation_is_persisted_and_second_process_cannot_expand(tmp_path):
    inp=tmp_path/'frames.json';inp.write_text(json.dumps(frames(tmp_path)))
    state=tmp_path/'campaign.json'
    cmd=[sys.executable,'-m','drama_plugin.visual.production']
    def run(*args):return subprocess.run(cmd+list(args)+['--state',str(state)],capture_output=True,text=True)
    assert run('init','--input',str(inp)).returncode==0
    result=run('reserve','--shot','S1');assert result.returncode==0,result.stderr
    attempt=json.loads(result.stdout)
    assert json.loads(state.read_text())['attempts'][0]['attempt_id']==attempt['attempt_id']
    assert run('reserve','--shot','S2').returncode!=0
    assert run('init','--input',str(inp)).returncode!=0
    assert len(json.loads(state.read_text())['attempts'])==1


def test_template_linkage_and_graph_version_cannot_be_declared_away(tmp_path):
    s,t=material(tmp_path)
    wrong=t.model_copy(update={'image_slots':('3','2','10')})
    with pytest.raises(ValueError,match='WIRING_MISMATCH'):compile_frame(s,wrong)
    graph=json.loads(Path(t.graph_path).read_text());graph['links'][0][1]=3
    Path(t.graph_path).write_text(json.dumps(graph))
    with pytest.raises(ValueError,match='GRAPH_CHANGED'):compile_frame(s,t)


def test_replan_can_recover_without_resetting_first_pass_yield(tmp_path):
    state=new_campaign(frames(tmp_path))
    for sid in ['S1','S2']:
        a=reserve(state,sid);outcome(state,a);record_review(state,review_for(state,a,'PROP_STRUCTURE'))
    resume(state,reason='Inspected repeated structural defect and wrote exact targeted correction')
    for sid in state['pilots']:
        a=reserve(state,sid);outcome(state,a);record_review(state,review_for(state,a))
    assert not state['pause']
    assert reserve(state,'S4')['ordinal']==1
    assert metrics(state)['first_pass_yield']==1/3


def test_late_billing_cannot_attach_to_wrong_job_or_count_twice(tmp_path):
    from drama_plugin.visual.production import reconcile_billing
    state=new_campaign(frames(tmp_path));a=reserve(state,'S1');outcome(state,a)
    args=dict(attempt_id=a['attempt_id'],job_id=a['job_id'],credits=40.09,billing_event_id='event-1')
    with pytest.raises(ValueError,match='JOB_MISMATCH'):reconcile_billing(state,**{**args,'job_id':'wrong'})
    with pytest.raises(ValueError,match='INVALID_BILLING'):reconcile_billing(state,**{**args,'credits':float('nan')})
    reconcile_billing(state,**args);reconcile_billing(state,**args)
    assert metrics(state)['known_credits']==40.09
    assert metrics(state)['billing_unknown_count']==0


def test_many_distinct_unqualified_cohorts_do_not_expand_pilot_budget(tmp_path):
    batch=frames(tmp_path)
    for i,f in enumerate(batch):
        template=Template.model_validate({**f['template'],'model':f'test-model-{i}'})
        batch[i]=compile_frame(FrameSpec.model_validate(f['spec']),template)
    with pytest.raises(ValueError,match='SPLIT_CAMPAIGN'):new_campaign(batch)


def test_completed_job_and_billing_can_be_recorded_after_reference_cleanup(tmp_path):
    from drama_plugin.visual.production import check_campaign, reconcile_billing
    state=new_campaign(frames(tmp_path));a=reserve(state,'S1')
    (tmp_path/'w.png').unlink()
    check_campaign(state)
    outcome(state,a)
    record_review(state,review_for(state,a))
    reconcile_billing(state,attempt_id=a['attempt_id'],job_id=a['job_id'],credits=40.09,billing_event_id='late-event')
    with pytest.raises(FileNotFoundError):reserve(state,'S2')
