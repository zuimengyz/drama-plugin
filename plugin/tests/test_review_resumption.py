"""Use-based review and autonomous recovery; synthetic offline events only."""
from copy import deepcopy
import pytest
from test_route_image_inputs import image_input
from test_visual_first_pass import review_for, outcome
from drama_plugin.visual.frame_request import FrameSpec, compile_frame
from drama_plugin.visual import production as p
from drama_plugin.contracts.base import sha256_canonical as fp

def setup(tmp_path):
 spec,t=image_input(tmp_path,True);frame=compile_frame(spec,t);state=p.new_campaign([frame])
 for n in range(2):
  if state['pause']:p.resume(state,reason='Change motion framing after observed prop error')
  a=p.reserve(state,spec.shot_id);outcome(state,a);p.record_review(state,review_for(state,a,'PROP_STRUCTURE'))
 a['delivery']={'mediaId':spec.references[0].media_id};a['persistence_status']='VERIFIED'
 state['pause']='TARGETED_REVISION_FAILED'
 return state,spec,t,a

def test_normal_occlusion_and_noncritical_detail_pass_with_notes(tmp_path):
 state,s,t,a=setup(tmp_path);old=deepcopy(a['review']);r=review_for(state,a).model_dump(mode='json')
 r['checks']={'ACTION':'PASS','CONTINUITY':'PASS'}
 r['findings']=[dict(category='BLOCKING',severity='MINOR',evidence='Far hand naturally occluded, core pressing action readable at normal size',remedy='ACCEPT'),dict(category='PROP_STRUCTURE',severity='MINOR',evidence='Background type texture does not affect this action',remedy='ACCEPT')]
 assert p.revise_review(state,review=r,reason='Review actual normal-view use',expected_review_hash=fp(old))=='PASS_WITH_NOTES'
 selection=p.select_input(state,attempt_id=a['attempt_id'],purpose='FIRST_FRAME',reason='Reuse suitable older frame, avoid failed editing')
 assert state['pause'] is None and selection['authority']=='HOST_WORKING_INPUT'
 assert a['review']==old and a['original_review_status']=='FAIL' and len(state['attempts'])==2
 assert a.get('user_adoption')!='USER_SELECTED'
 with pytest.raises(ValueError,match='REVIEW_CHANGED'):p.revise_review(state,review=r,reason='stale',expected_review_hash=fp(old))

def test_missing_core_prop_still_rejected_and_unknown_is_not_failure(tmp_path):
 state,s,t,a=setup(tmp_path)
 with pytest.raises(ValueError,match='USABLE'):p.select_input(state,attempt_id=a['attempt_id'],purpose='FIRST_FRAME',reason='try missing board')
 r=review_for(state,a).model_dump(mode='json');r['checks']={'SOUND':'UNKNOWN'}
 assert p.revise_review(state,review=r,reason='Audio not observed; no claim of error',expected_review_hash=fp(a['review']))=='PENDING_REVIEW'
 assert a['current_review']['checks']['SOUND']=='UNKNOWN'

def test_old_stop_can_replan_without_target_authorization_or_reset(tmp_path,monkeypatch):
 state,s,t,a=setup(tmp_path);state['stage']={'id':'offline','protected_targets':[]}
 raw=s.model_dump();raw['composition']='Revised camera emphasizing the independent pressing board'
 frame=compile_frame(FrameSpec.model_validate(raw),t)
 p.replan(state,frame=frame,reason='Change composition to show core action',incremental_credits=40)
 monkeypatch.setattr(p,'_stage_gate',lambda *args:40)
 b=p.reserve(state,s.shot_id)
 assert b['ordinal']==3 and len(state['attempts'])==3
 assert state['remediations'][-1]['previous_pause']=='TARGETED_REVISION_FAILED'
 assert b['frame_snapshot']['fingerprint']==frame['fingerprint']
 assert 'authorization' not in state['remediations'][-1]

def test_unknown_submission_still_blocks_replanning(tmp_path):
 state,s,t,a=setup(tmp_path);a['status']='UNKNOWN'
 with pytest.raises(ValueError,match='RECOVER_ORIGINAL'):p.resume(state,reason='Need outcome first')

def test_plan_and_uploaded_bytes_still_checked(tmp_path):
 state,s,t,a=setup(tmp_path);state['frames'][s.shot_id]['request']['extra']='tampered'
 with pytest.raises(ValueError,match='PLAN_CHANGED'):p.check_campaign(state)


def test_legacy_plan_order_reseal_requires_original_receipt():
    from copy import deepcopy
    from drama_plugin.contracts.base import sha256_canonical as fp
    frames = [{'spec': {'shot_id': sid}} for sid in ['I01', 'I02', 'B03']]
    for f in frames: f['fingerprint'] = fp(f)
    state = {'frames': {f['spec']['shot_id']: f for f in reversed(frames)}, 'plan_fingerprint': fp(frames)}
    with pytest.raises(ValueError, match='CAMPAIGN_PLAN_CHANGED'): p.check_campaign(state)
    wrong = deepcopy(frames); wrong[0]['spec']['action'] = 'changed'
    with pytest.raises(ValueError, match='ORIGINAL_PLAN'): p.reseal_plan(state, sealed_frames=wrong)
    p.reseal_plan(state, sealed_frames=frames)
    state['frames'] = dict(reversed(list(state['frames'].items())))
    p.check_campaign(state)
    state['frames']['I01']['spec']['action'] = 'changed'
    with pytest.raises(ValueError, match='CAMPAIGN_PLAN_CHANGED'): p.check_campaign(state)
