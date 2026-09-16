"""Real contract boundaries, synthetic judgments, retained sources. NO Provider E2E."""
import asyncio
from copy import deepcopy
import hashlib
import json

import pytest
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.director import CapabilityFeedback
from drama_plugin.contracts.dpd import DPDSnapshot
from drama_plugin.contracts.sequence import FilmReview
from drama_plugin.director import DirectorError, request_pin, feedback_pin, pin
from drama_plugin.hosts.director_runtime import dispatch_local, resume_with_execution
from drama_plugin.hosts.director_capabilities import next_responsibility, CAPABILITIES
from drama_plugin.visual.cinematic import selection_handoff
from drama_plugin.visual.video_selection import Requirements, Candidate
from drama_plugin.visual_route import verify_route_artifact
from drama_plugin.tools.catalog import build_tool_registry
from drama_plugin.contracts.creation import Scene, Shot
from director_integration_helpers import Session, dpd_input, coverage, cinematic, route, MEANING
from test_director import design_review
from test_sequence_production import media, package, review as legacy_review, observation
from test_video_selection import fixture as selection_fixture
from seedance_helpers import add_director_inputs


def test_s2_real_read_tool_scene_dpd_coverage_revision_and_resume(tmp_path):
    s=Session(tmp_path,2);original=deepcopy(s.sample['canonicalScene'])
    class FixtureOwner:
        async def get_scene(self,scene_id):
            assert scene_id==s.w.scope_id
            return Scene.model_validate(original)
        def __getattr__(self,name):
            async def no_call(*args,**kwargs):raise AssertionError('Unexpected business/provider call: '+name)
            return no_call
    owner=FixtureOwner();tools=build_tool_registry(*([owner]*8))
    scene=asyncio.run(tools.invoke('scene.get_scene',scene_id=s.w.scope_id))
    assert len(tools.list())==50
    q,inp=s.request('scene-development',{'scene':dump_contract(scene)})
    f=s.run(q,inp);assert s.store.read_ref(f.result_refs[0])==dump_contract(scene)
    s.review(q,f)
    q,inp=s.request('dramatic-performance-direction',dpd_input(s))
    f=s.run(q,inp);dpd=DPDSnapshot.model_validate(s.store.read_ref(f.result_refs[0]))
    assert '假设' in dpd.scene.direction.subtext
    assert s.w.adopted_head is None
    s.review(q,f,'REVISE_PERFORMANCE',receipt=True)
    assert s.w.adopted_head is None
    assert next_responsibility('REVISE_PERFORMANCE')['capability']=='dramatic-performance-direction'
    # One explicit creative revision, preserving the unique DPD owner and source meaning.
    revised=dpd_input(s);revised['scene']['direction']['tactic']='听见楚歌后向军吏求证，保持疑问而不宣告结果'
    q,inp=s.request('dramatic-performance-direction',revised,revision=1)
    f=s.run(q,inp);s.review(q,f,receipt=True)
    assert s.w.adopted_head
    assert s.store.read_ref(s.w.adopted_head)['userApproval']=='UNCHANGED'
    q,inp=s.request('shot-design',coverage(s));f=s.run(q,inp);s.review(q,f)
    assert s.sample['canonicalScene']==original
    assert not any(k in dump_contract(s.w) for k in ('subtext','purpose','objective'))
    assert s.store.resume(s.w.workspace_id,s.w.branch_id,s.current)['action']=='NEXT_DECISION'
    assert next_responsibility('REVISE_COVERAGE',revision_cycles=1)['stop']=='ITERATION_BOUND_REACHED'


def test_s8_dpd_shot_native_audio_prohibition_reaches_real_audio(tmp_path,media):
    s=Session(tmp_path/'director',8)
    for name,inputs in [('dramatic-performance-direction',dpd_input(s)),('shot-design',coverage(s))]:
        q,inp=s.request(name,inputs);f=s.run(q,inp);s.review(q,f)
    clip=media[1]['red'];digest=hashlib.sha256(clip.read_bytes()).hexdigest()
    s.bridge.media_path=lambda ref: clip if ref=='LOCAL_SYNTHETIC_AUDIO_FIXTURE' else pytest.fail('wrong Media ref')
    inputs={'manifest':{'sourceVideoMediaId':'LOCAL_SYNTHETIC_AUDIO_FIXTURE','timeline':[]},'sourceHash':digest}
    q,inp=s.request('audio-production',inputs);f=s.run(q,inp)
    result=s.store.read_ref(f.result_refs[0]);evidence=s.store.read_ref(f.evidence_refs[0])
    assert result['operation']=='REUSE_SOURCE_AV' and result['audioProcessing']==[] and result['createdMedia'] is False
    assert 'NO TTS REPLACEMENT' in evidence['prohibitions']
    assert result['independentArtisticReview']=='NOT_VERIFIED'
    assert hashlib.sha256(clip.read_bytes()).hexdigest()==digest
    assert s.w.adopted_head is None
    s.review(q,f,receipt=True)
    assert s.w.adopted_head
    bad=deepcopy(inputs);bad['manifest']['audioMixMediaId']='unauthorized'
    q,inp=s.request('audio-production',bad)
    with pytest.raises(DirectorError,match='NO TTS REPLACEMENT'):
        s.bridge.run(q,inp,s.current)


def test_s7_real_selection_limit_changes_coverage_not_dramatic_consequence(tmp_path):
    s=Session(tmp_path/'director',7)
    q,inp=s.request('cinematic-direction',cinematic(s));f=s.run(q,inp)
    routed=s.store.read_ref(f.result_refs[0]);frozen=routed['sourcePayload'];s.review(q,f)
    r,c,_,_,adapter=selection_fixture(tmp_path)
    r=Requirements.model_validate({**r.model_dump(), 'work_id':frozen['spec']['workId'],'scene_id':s.w.scope_id,
        'shot_id':frozen['spec']['shotId'], 'duration_seconds':int(frozen['spec']['durationSeconds']),
        'source_fingerprint':frozen['spec']['sourceFingerprint'],'frozen_creative':selection_handoff(frozen),
        'required':[MEANING[7]],'forbidden':['NO CANON CHANGE']})
    r=add_director_inputs(r,adapter,frozen)
    c=Candidate.model_validate({**c.model_dump(),'durations':[r.duration_seconds],'quality':{
        'status':'PASS','samples':1,'task_types':[r.shot_type],'evidence':['OFFLINE SIMULATED contact evidence, not model benchmark'],
        'dimensions':{'identity_props':'PASS','action_narrative':'PASS','sound_performance':'PASS','continuity':'PASS',
           'motion.horse_contact':'FAIL','motion.camera_complexity':'PASS','continuity.identity':'PASS','continuity.spatial':'PASS','performance.temporal_adherence':'PASS'}}})
    q,inp=s.request('video-model-selection',{'requirements':r.model_dump(mode='json'),'candidate':c.model_dump(mode='json')})
    f=s.run(q,inp)
    assert f.feasibility=='REQUIRES_DECOMPOSITION'
    assert any('horse_contact' in x for x in f.limitations)
    assert s.store.read_ref(f.result_refs[0])['incremental_credits']==200  # Selection-owned synthetic quote
    with pytest.raises(DirectorError,match='CAPABILITY_LIMITATION'):
        s.review(q,f,receipt=True)
    s.review(q,f,'REVISE_COVERAGE')
    assert s.w.adopted_head is None
    nextq,inp=s.request('shot-design',coverage(s,True),revision=1)
    assert nextq.task==q.task and nextq.must_preserve==q.must_preserve
    f=s.run(nextq,inp);plan=s.store.read_ref(f.result_refs[0])
    assert len(plan['coverage'])==4
    assert '重围' in plan['informationBeats'][-1]['information']
    s.review(nextq,f,receipt=True)
    assert s.w.adopted_head and s.store.resume(s.w.workspace_id,s.w.branch_id,s.current)['action']=='NEXT_DECISION'
    assert not any(k in dump_contract(nextq) for k in ('model','seed','budget','provider'))


@pytest.mark.parametrize('number',[2,8,7])
def test_route_contracts_branch_adoption_and_approvals_cannot_transfer(tmp_path,number):
    a,b=Session(tmp_path,number),Session(tmp_path,number,cg=True)
    for s in (a,b):
        q,inp=s.request('cinematic-direction',cinematic(s));f=s.run(q,inp)
        packet=s.store.read_ref(f.result_refs[0]);verify_route_artifact(packet,route(s.w.scope_id,s is b))
        assert not packet['approvalTransferAllowed'] and not packet['productionAllowed']
        other=b if s is a else a;before=other.store.load(other.w.workspace_id,other.w.branch_id)
        s.review(q,f,receipt=True)
        assert other.store.load(other.w.workspace_id,other.w.branch_id)==before
    assert a.w.adopted_head!=b.w.adopted_head
    gate=pin('original:cg-lookdev',{'route':'stylized_cinematic_cg','status':'NOT_APPROVED'})
    q,inp=b.request('shot-production',{'never':'invoked'},approvals=(gate,))
    with pytest.raises(DirectorError,match='USER_APPROVAL_REQUIRED'):
        dispatch_local(b.store,b.bridge,b.w,inp,b.current,retain_execution=lambda *_:pytest.fail('not called'))


def test_interrupt_recovers_original_capability_result_not_workspace_truth(tmp_path):
    s=Session(tmp_path,2);q,inp=s.request('dramatic-performance-direction',dpd_input(s))
    execution_owner=tmp_path/'capability-execution.json';calls=[]
    def retained_then_crash(request,feedback):
        calls.append(request_pin(request))
        execution_owner.write_text(json.dumps({'request':dump_contract(request_pin(request)), 'result':dump_contract(feedback)}))
        s.record_current(feedback)
        raise InterruptedError('after original result persisted, before Director feedback checkpoint')
    with pytest.raises(InterruptedError):
        dispatch_local(s.store,s.bridge,s.w,inp,s.current,retain_execution=retained_then_crash)
    s.w=s.store.load(s.w.workspace_id,s.w.branch_id)
    assert s.w.feedback_ref is None and s.w.checkpoint=='DISPATCHED'
    assert not list((tmp_path/'completed').glob('*.json')) if (tmp_path/'completed').exists() else True
    def lookup(request):
        record=json.loads(execution_owner.read_text())
        assert record['request']==dump_contract(request_pin(request))
        return CapabilityFeedback.model_validate(record['result'])
    state=resume_with_execution(s.store,s.w.workspace_id,s.w.branch_id,s.current,lookup)
    assert state['action']=='REVIEW_PENDING' and not state['delegate'] and len(calls)==1
    s.w=s.store.load(s.w.workspace_id,s.w.branch_id);assert s.w.adopted_head is None
    s.review(q,lookup(q),receipt=True)
    assert s.w.adopted_head


def test_unknown_execution_never_resubmits_and_stale_blocks_lookup(tmp_path):
    s=Session(tmp_path,7);q,inp=s.request('shot-design',coverage(s))
    s.w=s.store.transition(s.w,'DISPATCH',None,s.current)
    for lookup in (lambda _:None, lambda _:CapabilityFeedback(request_ref=request_pin(q),source_pins=q.source_pins,next_responsibility='reconcile')):
        state=resume_with_execution(s.store,s.w.workspace_id,s.w.branch_id,s.current,lookup)
        assert state['action']=='RECONCILIATION_REQUIRED' and not state['delegate']
    s.current[s.source.key]='f'*64
    state=resume_with_execution(s.store,s.w.workspace_id,s.w.branch_id,s.current,lambda _:pytest.fail('stale must stop before lookup'))
    assert state['action']=='STALE_SOURCE'
    with pytest.raises(DirectorError,match='STALE_SOURCE'):s.bridge.run(q,inp,s.current)


def test_locked_source_conflict_escalates_cannot_overwrite(tmp_path):
    s=Session(tmp_path,2);original=deepcopy(s.sample['canonicalScene'])
    q,inp=s.request('scene-development',{'scene':original,'proposedContent':{'fact':'楚地已经全部失陷'}})
    f=s.run(q,inp)
    assert f.next_responsibility=='REQUEST_SCRIPT_REVIEW'
    assert s.store.read_ref(f.result_refs[0])==dump_contract(Scene.model_validate(original))
    s.review(q,f,'REQUEST_SCRIPT_REVIEW',receipt=True)
    assert s.w.adopted_head is None and s.sample['canonicalScene']==original


@pytest.mark.parametrize('disposition,target',[
 ('REVISE_PERFORMANCE','dramatic-performance-direction'),('REVISE_BLOCKING','shot-design'),
 ('REVISE_COVERAGE','shot-design'),('REVISE_EDIT','cinematic-finishing'),('REVISE_SOUND','audio-production'),
 ('REPLAN_SCENE','scene-development'),('REVISE_EXECUTION','shot-production'),
 ('REQUEST_SCRIPT_REVIEW','cinematic-screenplay-incubation'),('ESCALATE_PRODUCTION_METHOD','video-model-selection')])
def test_causal_disposition_has_explicit_real_owner(disposition,target):
    assert next_responsibility(disposition)['capability']==target
    assert not next_responsibility(disposition)['automaticDispatch']


def test_obligation_not_proven_by_contract_success_remains_unmet(tmp_path):
    s=Session(tmp_path,8);q,inp=s.request('dramatic-performance-direction',dpd_input(s),evidence=('actual performance watched',))
    f=s.run(q,inp)
    assert f.fulfilled==() and f.unmet==q.required_evidence
    with pytest.raises(DirectorError,match='INSUFFICIENT_EVIDENCE'):s.review(q,f,receipt=True)


def test_production_replay_uses_actual_campaign_result_and_never_submits(tmp_path):
    from test_visual_first_pass import material,outcome
    from drama_plugin.visual.frame_request import FrameSpec,compile_frame
    from drama_plugin.visual.production import new_campaign,reserve
    from director_integration_helpers import SOURCES
    s=Session(tmp_path/'director',7)
    shot=next(x for x in SOURCES['shots'] if x['scene_id']==s.w.scope_id)
    spec,template=material(tmp_path,shot['id']);raw=spec.model_dump()
    raw.update(shot_fingerprint=fp(Shot.model_validate(shot)),entry_state='楚骑已在东侧会点',composition='项羽与回应的楚从骑同框',environment='东城坡地',
        required=['保持项羽与从骑身份','空间会合可读'],forbidden=['局部胜利变成全局胜利'])
    for a,label in zip(raw['actors'],['项羽','楚从骑']):
        a.update(label=label,identity=label+' OFFLINE synthetic reference',costume='楚军衣甲',position='东侧会点',pose='保持重心',action='面对同伴回应',gaze='场内同伴')
    raw['props'][0].update(geometry='旗杆与旗面',placement='坡地会点旁',forbidden=['现代标志'])
    for ref in raw['references']:ref['facts']='OFFLINE battle reference, not a formal Asset approval'
    frame=compile_frame(FrameSpec.model_validate(raw),template)
    campaign=new_campaign([frame]);attempt=reserve(campaign,shot['id']);outcome(campaign,attempt)
    q,inp=s.request('shot-production',{'campaign':campaign,'attemptId':attempt['attempt_id'],'shot':shot})
    f=s.run(q,inp);result=s.store.read_ref(f.result_refs[0])
    assert result['attempt']['job_id']==attempt['job_id'] and result['mode']=='REPLAY_EVIDENCE_ONLY'
    assert f.feasibility=='UNKNOWN' and len(campaign['attempts'])==1 and s.w.adopted_head is None
    with pytest.raises(DirectorError,match='INVALID_SOURCE'):
        s.bridge.run(q.model_copy(update={'scope_id':'other-scene'}),inp,s.current)


def test_original_production_freeze_still_blocks_after_director_approve(tmp_path):
    from test_production_freeze_sequence import freeze,executable,submit,binding
    from drama_plugin.hosts.sequence_execution import SequenceRequestBinding
    s=Session(tmp_path,8);q,inp=s.request('shot-design',coverage(s));f=s.run(q,inp);s.review(q,f,receipt=True)
    original=freeze('PENDING_USER_REVIEW');p=executable(original)
    with pytest.raises(ValueError,match='SEQUENCE_PRODUCTION_DESIGN_BLOCKED'):
        submit(original,p,SequenceRequestBinding(**binding(original,p)))
    assert original.entries[0].approval_status=='PENDING_USER_REVIEW'


def test_finishing_picture_sequence_and_real_filmreview_loop(tmp_path,media):
    s=Session(tmp_path/'director',8)
    plan,clips,_=media;clip=clips['red'];digest=hashlib.sha256(clip.read_bytes()).hexdigest()
    plan.source_canon_fingerprint=s.source.fingerprint
    raw=package();raw['scope_id']=s.w.scope_id
    # Original package schema, design-only retained data, no parallel edit plan.
    for shot in raw['shots']:shot['scene_id']=s.w.scope_id
    raw['geography'][0]['scene_id']=s.w.scope_id
    raw['source_pins'].append(dump_contract(s.source))
    raw['editorial']['scene_ids']=[s.w.scope_id]
    for p in raw['source_pins']:s.current[p['key']]=p['fingerprint']
    q,inp=s.request('cinematic-finishing',{'plan':dump_contract(plan),'mediaHashes':{x.media_id:x.content_hash for x in plan.sources},
        'canonFingerprint':s.source.fingerprint,'package':raw})
    f=s.run(q,inp);out=s.store.read_ref(f.result_refs[0])
    assert not out['edit']['sourceMutationAllowed'] and not out['sequence']['productionAuthorized']
    s.review(q,f)
    # Existing local bytes + synthetic observer attestations exercise FilmReview wire gates.
    # These are not judgments about the historical scene's actual acting.
    from drama_plugin.contracts.director import CapabilityRequest
    mq=CapabilityRequest.model_validate({**dump_contract(q),'requestId':'review-local-clip','resultKind':'MEDIA','supersedes':dump_contract(request_pin(q))})
    s.w=s.store.transition(s.w,'REQUEST',s.store.put(request_pin(mq).key,dump_contract(mq)),s.current)
    m=pin('local-synthetic-clip',{});m.kind='MEDIA';m.fingerprint=digest
    evidence=s.store.put('synthetic-attestation',{'mode':'LOCAL_SYNTHETIC_ONLY','actualHistoricalPerformance':'NOT_OBSERVED'})
    mf=CapabilityFeedback(request_ref=request_pin(mq),source_pins=mq.source_pins,result_refs=(m,),evidence_refs=(evidence,),
        execution='COMPLETED',feasibility='SUPPORTED',fulfilled=mq.required_evidence,next_responsibility='Director review')
    s.record_current(mf);s.w=s.store.transition(s.w,'FEEDBACK',s.store.retain_feedback(mq,mf),s.current)
    assert s.w.adopted_head is None
    delta=s.store.put('sparse-local-receipt',{'domain':'sound_strategy','summary':'Synthetic fixture native reuse only', 'presentationOnly':True});s.current[delta.key]=delta.fingerprint
    raw=legacy_review();raw.update(media_hash=digest,duration=2,observations=[observation(0,2,'NORMAL_AV')],
        director=design_review(s.w,mq,mf,delta,'REVISE_EDIT')['director'])
    film=FilmReview(**raw)
    from drama_plugin.sequence import film_review_verdict
    assert film_review_verdict(film,digest,require_director=True)['status']=='REPAIR_REQUIRED'
    assert film.technical=='PASS'
    raw['director']=design_review(s.w,mq,mf,delta)['director'];film=FilmReview(**raw)
    s.w=s.store.transition(s.w,'REVIEW',s.store.put('existing-FilmReview',dump_contract(film)),s.current)
    assert s.w.adopted_head and s.store.read_ref(s.w.adopted_head)['userApproval']=='UNCHANGED'
    assert s.store.resume(s.w.workspace_id,s.w.branch_id,s.current)['action']=='NEXT_DECISION'


def test_model_unknown_not_promoted_and_pending_feedback_stales(tmp_path):
    s=Session(tmp_path/'director',7)
    r,c,_,_,_=selection_fixture(tmp_path)
    r=Requirements.model_validate({**r.model_dump(),'scene_id':s.w.scope_id})
    q,inp=s.request('video-model-selection',{'requirements':r.model_dump(mode='json'),'candidate':c.model_dump(mode='json')})
    f=s.run(q,inp)
    assert f.feasibility=='UNKNOWN' and f.unknowns and s.w.adopted_head is None
    s.current[s.source.key]='e'*64
    assert s.store.resume(s.w.workspace_id,s.w.branch_id,s.current)['action']=='STALE_SOURCE'
    with pytest.raises(DirectorError,match='STALE_SOURCE'):s.review(q,f,receipt=True)


def test_design_request_keeps_unapproved_casting_pending(tmp_path):
    s=Session(tmp_path,2)
    casting=pin('casting:live',{'route':'live_action_realist','status':'PENDING_USER_REVIEW'})
    q,inp=s.request('cinematic-direction',cinematic(s),approvals=(casting,))
    with pytest.raises(DirectorError,match='USER_APPROVAL_REQUIRED'):
        dispatch_local(s.store,s.bridge,s.w,inp,s.current,retain_execution=lambda *_:pytest.fail('gate bypass'))
    assert s.store.load(s.w.workspace_id,s.w.branch_id).adopted_head is None
