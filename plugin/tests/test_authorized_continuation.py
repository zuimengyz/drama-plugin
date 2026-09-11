"""Explicit new candidate: preserve historical successes, counts and budget."""
from copy import deepcopy
import pytest
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual import production as p
from drama_plugin.visual.video_selection import Candidate, ProductionRoute, seal_decision, qualify_route
from drama_plugin.hosts.comfy_video import verify_execution, compile_request
from seedance_helpers import seed_fixture, execution_plan
from test_video_selection import decision as old_decision, quote, evidence
from test_mcp_execution import binding


def prepared(tmp_path,monkeypatch):
    monkeypatch.setattr(p,'video_verifier',verify_execution)
    old=old_decision(tmp_path)
    state=p.new_stage(stage_id='v206',authorization_ref='original',budget_credits=600,
        frames=[old],protected_targets=[])
    history=dict(attempt_id='old',shot_id='S1',ordinal=1,status='COMPLETED',review_status='PASS_WITH_NOTES',
        job_id='old-job',credits=None,reserved_credits=200,media_kind='VIDEO',frame_snapshot=old,
        provider_usage=dict(event_id='old-usage',job_id='old-job',credits=190))
    state['attempts']=[history]
    original=deepcopy(state)
    r,c,g,s,a=seed_fixture(tmp_path)
    c=Candidate.model_validate({**c.model_dump(),'cost':{'components':dict(video=100,audio=0,references=0,addons=0,correction=0),'evidence':evidence()}})
    route=execution_plan(r,c,'v206').model_dump(mode='json')
    route['inputs']=[dict(target_id='I',purpose='INPUT',role='REFERENCE',for_targets=['S1'],preparation='REUSE',specification='existing',rationale='one authorized candidate',cost_key='references',source_media_id='M')]
    route['requirements']['shots']={'S1':'SHOT'}
    route['continuation']=dict(authorization_ref='USER:one new candidate',reason='explicit comparison authorization',
        target_id='S1',baseline_stage_fingerprint=fp(state),baseline_attempts_fingerprint=fp(state['attempts']),
        baseline_attempt_count=1,max_new_video_attempts=1,max_quoted_credits=120)
    route=ProductionRoute.model_validate(route)
    assert qualify_route(route)['eligible']
    p.continuation_baseline(state,route,opening=True)
    state['production_route']=route.model_dump(mode='json')
    req=compile_request(r,c,g,s,a['bindings'],r.frozen_creative['motion_prompt'])
    d=seal_decision(r,c,req,stage_id='v206',rationale='explicit candidate',comparisons=[],fallback='stop',host_adapter=a,production_route=route)
    return state,original,d,route


def test_new_candidate_keeps_pass_and_ordinal_and_cannot_repeat(tmp_path,monkeypatch):
    state,original,d,route=prepared(tmp_path,monkeypatch)
    p.replan(state,frame=d,reason='explicit same-shot candidate with current frozen Canon')
    a=p.reserve(state,'S1',**quote(d),execution_binding=binding(d))
    assert a['ordinal']==2 and a['call_reason']=='USER_AUTHORIZED_CANDIDATE'
    assert state['attempts'][0]==original['attempts'][0]
    assert state['stage']==original['stage']
    with pytest.raises(ValueError):p.reserve(state,'S1',**quote(d),execution_binding=binding(d))
    a.update(status='COMPLETED',review_status='FAIL')
    with pytest.raises(ValueError,match='CONTINUATION_VIDEO_ATTEMPTS_EXHAUSTED'):
        p._stage_gate(state,d,d['request'],**quote(d))


@pytest.mark.parametrize('mutation',['history','count','target','cap'])
def test_continuation_limits_fail_closed(tmp_path,monkeypatch,mutation):
    state,original,d,route=prepared(tmp_path,monkeypatch)
    if mutation=='history':
        state['attempts'][0]['review_status']='FAIL'
        with pytest.raises(ValueError,match='BASELINE'):p.continuation_baseline(state,route)
    elif mutation=='count':
        state['attempts']=[]
        with pytest.raises(ValueError,match='BASELINE'):p.continuation_baseline(state,route)
    elif mutation=='target':
        raw=route.model_dump();raw['video_targets']=['S2']
        with pytest.raises(ValueError,match='ONE_FROZEN_TARGET'):qualify_route(ProductionRoute.model_validate(raw))
    else:
        with pytest.raises(ValueError,match='QUOTE_EXCEEDS'):
            p._stage_gate(state,d,d['request'],**quote(d,amount=121))


def test_current_balance_includes_usage_but_stage_exposure_stays_reserved(tmp_path,monkeypatch):
    state,original,d,route=prepared(tmp_path,monkeypatch)
    q=quote(d);q['balance']['available_credits']=150
    with pytest.raises(ValueError,match='BUDGET_OR_BALANCE'):
        p._stage_gate(state,d,d['request'],**q)
    q['balance']['included_usage_events']=['old-usage']
    assert p._stage_gate(state,d,d['request'],**q)==100
    assert p.exposure(state)==200 and state['attempts']==original['attempts']
    state['stage']['budget_credits']=250
    with pytest.raises(ValueError,match='BUDGET_OR_BALANCE'):
        p._stage_gate(state,d,d['request'],**q)


@pytest.mark.parametrize('mutation',['unknown_event','unknown_job','wrong_job'])
def test_balance_cannot_release_unknown_usage(tmp_path,monkeypatch,mutation):
    state,original,d,route=prepared(tmp_path,monkeypatch);q=quote(d)
    q['balance']['included_usage_events']=['invented' if mutation=='unknown_event' else 'old-usage']
    if mutation=='unknown_job':state['attempts'][0]['status']='UNKNOWN'
    if mutation=='wrong_job':state['attempts'][0]['provider_usage']['job_id']='wrong'
    # Baseline validation also rejects rewritten history; no released cash either way.
    with pytest.raises(ValueError):p._stage_gate(state,d,d['request'],**q)


def test_no_authorization_still_requires_two_call_envelope(tmp_path,monkeypatch):
    state,original,d,route=prepared(tmp_path,monkeypatch)
    raw=route.model_dump();raw['continuation']=None
    assert not qualify_route(ProductionRoute.model_validate(raw))['eligible']
