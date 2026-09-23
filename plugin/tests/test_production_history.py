from copy import deepcopy
import json
import pytest
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual.history import compact, resolve, attempt_frame, remember


def frame(version):
    material = {'spec': {'shot_id': 'S1', 'revision': version, 'authority': '证据'*10000}, 'request': {'prompt': 'small'}}
    return {**material, 'fingerprint': fp(material)}


def test_legacy_inline_history_migrates_and_grows_only_by_references():
    old, current = frame(1), frame(2)
    route = {'route_id':'route1', 'details':'route evidence'*1000}
    state = {'frames': {'S1':current}, 'production_route':route,
        'attempts':[{'frame_snapshot':deepcopy(old),'frame_fingerprint':old['fingerprint']} for _ in range(3)],
        'remediations':[{'previous_frame':deepcopy(old)} for _ in range(4)],
        'route_revisions':[{'previous_route':deepcopy(route)} for _ in range(3)]}
    assert attempt_frame(state,state['attempts'][0]) == old
    canonical = deepcopy(state['frames'])
    compact(state)
    assert state['frames']==canonical and len(state['history_frames'])==1
    assert 'history_routes' not in state
    for a in state['attempts']:
        assert 'frame_snapshot' not in a and attempt_frame(state,a)==old
    for r in state['remediations']:
        assert 'previous_frame' not in r and resolve(state,r['previous_frame_ref'])==old
    for r in state['route_revisions']:
        assert 'previous_route' not in r and resolve(state,r['previous_route_ref'],'route')==route
    before = deepcopy(state); compact(state); assert state==before
    size=lambda:len(json.dumps(state,ensure_ascii=False).encode())
    baseline=size()
    for _ in range(30):
        state['attempts'].append({'frame_ref':fp(current),'frame_fingerprint':current['fingerprint']})
        state['remediations'].append({'previous_frame_ref':fp(old)})
    compact(state)
    assert size()-baseline < 12000
    assert len(state['history_frames'])==1  # current is stored only in frames


def test_replacing_canonical_keeps_immutable_revision_and_detects_corruption():
    old,new=frame(1),frame(2)
    state={'frames':{'S1':old},'attempts':[{'frame_ref':fp(old),'frame_fingerprint':old['fingerprint']}]}
    remember(state,old)
    state['frames']['S1']=new
    compact(state)
    assert attempt_frame(state,state['attempts'][0])==old
    assert resolve(state,fp(new))==new
    state['history_frames'][fp(old)]['spec']['revision']=99
    before=deepcopy(state)
    with pytest.raises(ValueError,match='MISSING_OR_CHANGED'):
        compact(state)
    assert state==before


def test_missing_reference_never_falls_back_to_current_frame():
    state={'frames':{'S1':frame(2)},'attempts':[{'frame_ref':fp(frame(1))}]}
    with pytest.raises(ValueError,match='REFERENCE_MISSING'):
        compact(state)


def test_actual_reserve_only_writes_ref(tmp_path):
    from test_visual_first_pass import material
    from drama_plugin.visual.frame_request import compile_frame
    from drama_plugin.visual.production import new_campaign, reserve, record_review, resume
    from test_visual_first_pass import outcome, review_for
    compiled=compile_frame(*material(tmp_path))
    state=new_campaign([compiled])
    a=reserve(state,'S1')
    assert 'frame_snapshot' not in a and attempt_frame(state,a)==compiled
    outcome(state,a)
    record_review(state,review_for(state,a,'PROP_STRUCTURE'))
    if state['pause']:
        resume(state,reason='Targeted prop correction after actual review')
    # Same canonical frame across a controlled fresh reservation.
    b=reserve(state,'S1')
    assert a['frame_ref']==b['frame_ref']
    compact(state)
    assert 'history_frames' not in state


def test_mixed_inline_and_ref_conflict_blocks_without_mutation():
    state={'frames':{'S1':frame(1)},'attempts':[{'frame_snapshot':frame(1),'frame_ref':fp(frame(2))}]}
    before=deepcopy(state)
    with pytest.raises(ValueError,match='CONFLICT'):
        compact(state)
    assert state==before


@pytest.mark.asyncio
async def test_ref_only_mcp_attempt_replays_archived_revision(tmp_path,monkeypatch):
    from test_mcp_execution import decision, reserved, Registry, binding
    from drama_plugin.hosts.mcp_execution import invoke_reserved
    from drama_plugin.hosts.comfy_video import verify_execution
    from drama_plugin.visual import production
    original=decision(tmp_path,with_prompt_ir=True)
    a=reserved(original)
    state={'frames':{'S1':original},'attempts':[a]}
    compact(state)
    remember(state,original)
    # The historical attempt must not read a later canonical frame by shot ID.
    state['frames']['S1']=frame(99)
    compact(state)
    a=state['attempts'][0]
    assert 'frame_snapshot' not in a
    registry=Registry([binding(original)])
    monkeypatch.setattr(production,'video_verifier',verify_execution)
    async def claim(attempt_id):
        return production.begin_submission(state,attempt_id=attempt_id)
    result=await invoke_reserved(a,registry,verify_request=verify_execution,claim_submission=claim,state=state)
    assert result['task_id']=='owned-task' and len(registry.calls)==1
    assert attempt_frame(state,a)==original
    with pytest.raises(ValueError,match='PERSISTED_UNUSED'):
        await invoke_reserved(a,registry,verify_request=verify_execution,claim_submission=claim,state=state)
