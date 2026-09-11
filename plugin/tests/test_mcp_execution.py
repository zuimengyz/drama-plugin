"""V2-12C: offline connected registries, never network or paid generation."""
from copy import deepcopy
from pathlib import Path

import pytest

from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.hosts.comfy_video import compile_request, verify_execution
from drama_plugin.hosts.mcp_execution import resolve_mcp, invoke_reserved as dispatch
from drama_plugin.visual.video_selection import seal_decision, verify_decision, ProductionRoute, qualify_route
from drama_plugin.visual import production as p
from seedance_helpers import seed_fixture, execution_plan, execution_contract, add_director_inputs
from test_video_selection import evidence, quote, fixture


def decision(tmp_path, local=False):
    if local:
        from test_cinematic_direction import frozen_example
        from drama_plugin.visual.cinematic import selection_handoff
        r,c,g,s,a=fixture(tmp_path)
        frozen=frozen_example()
        r=r.model_copy(update={'frozen_creative':selection_handoff(frozen)})
        r=add_director_inputs(r,a,frozen)
    else:
        r,c,g,s,a=seed_fixture(tmp_path)
    route=execution_plan(r,c)
    if local:
        route=ProductionRoute.model_validate({**route.model_dump(),
            'execution':execution_contract('flux-3','local-comfy')})
    request=compile_request(r,c,g,s,a['bindings'],r.frozen_creative['motion_prompt'])
    return seal_decision(r,c,request,stage_id='OFFLINE',rationale='offline',comparisons=[],
        fallback='stop',host_adapter=a,production_route=route)


def binding(d):
    return dict(execution=d['execution'],server_id='connected-server-42',
        tool_name='arbitrary_runtime_tool',operation=d['request']['tool'],
        provider_schema_fingerprint=d['execution_contract']['schema_fingerprint'],
        evidence=evidence(),authenticated=True)


async def invoke_reserved(attempt, registry, **kwargs):
    # Simulates the Work-owned serialized write/readback, independent of dispatch.
    async def claim(attempt_id):
        if attempt_id in registry.claims:raise ValueError('RECOVER_ORIGINAL_MCP_SUBMISSION')
        registry.claims.add(attempt_id)
        return {**deepcopy(attempt),'status':'UNKNOWN','submission_started':True}
    return await dispatch(attempt,registry,claim_submission=claim,**kwargs)


class Registry:
    def __init__(self, entries):
        self.entries=entries;self.calls=[];self.mutation=None;self.claims=set()
    async def discover(self):return deepcopy(self.entries)
    async def invoke(self,bound,request,attempt_id):
        self.calls.append((bound,deepcopy(request)))
        result={**bound.model_dump(mode='json'),'attempt_id':attempt_id,
                'request_fingerprint':fp(request),'task_id':'owned-task'}
        if self.mutation:self.mutation(result)
        return result


def desktop(d):
    raw=binding(d);raw['execution']=deepcopy(d['execution'])
    raw['execution']['transport']='GUI';raw['tool_name']='Comfy Desktop'
    return raw


def reserved(d):
    return dict(status='RESERVED',job_id=None,attempt_id='attempt',frame_snapshot=deepcopy(d),
        frame_fingerprint=d['fingerprint'],request=deepcopy(d['request']),
        request_fingerprint=d['request_fingerprint'],execution_binding=binding(d))


@pytest.mark.asyncio
async def test_a_seedance_cloud_mcp(tmp_path):
    d=decision(tmp_path);reg=Registry([binding(d)])
    b=await resolve_mcp(d,reg)
    assert b.execution.backend.provider=='comfy-cloud'
    assert b.execution.capability.model_key=='seedance-2.5'
    assert b.execution.transport=='MCP' and reg.calls==[]


@pytest.mark.asyncio
async def test_b_desktop_without_mcp_blocks_before_invocation(tmp_path):
    d=decision(tmp_path);reg=Registry([desktop(d)])
    with pytest.raises(ValueError,match='MCP_CAPABILITY_UNAVAILABLE'):
        await invoke_reserved(reserved(d),reg,verify_request=verify_execution)
    assert reg.calls==[]


@pytest.mark.asyncio
async def test_c_mcp_and_desktop_only_mcp_selected(tmp_path):
    d=decision(tmp_path);reg=Registry([desktop(d),binding(d)])
    receipt=await invoke_reserved(reserved(d),reg,verify_request=verify_execution)
    assert receipt['execution']['transport']=='MCP'
    assert len(reg.calls)==1 and reg.calls[0][0].tool_name=='arbitrary_runtime_tool'
    assert reg.calls[0][1]==d['request']


@pytest.mark.parametrize('key,value',[
    ('provider','local-comfy'),('backend_key','wrong-backend'),('model_key','flux-3'),
    ('transport','GUI'),('task_id','other-task'),('attempt_id','other-attempt'),
    ('server_id','other-server'),('tool_name','other-tool')])
@pytest.mark.asyncio
async def test_d_result_identity_mismatch_not_formally_completed(tmp_path,key,value):
    d=decision(tmp_path);a=reserved(d);reg=Registry([binding(d)])
    receipt=await invoke_reserved(a,reg,verify_request=verify_execution)
    if key in ('provider','backend_key'):receipt['execution']['backend'][key]=value
    elif key=='model_key':receipt['execution']['capability'][key]=value
    elif key=='transport':receipt['execution'][key]=value
    else:receipt[key]=value
    state={'attempts':[a]}
    with pytest.raises(ValueError,match='EXECUTION_ROUTE_MISMATCH'):
        p.record_result(state,attempt_id='attempt',status='COMPLETED',job_id='owned-task',
            output_hash='a'*64,evidence='offline',execution_receipt=receipt)
    assert a['status']=='RESERVED' and a['job_id'] is None


@pytest.mark.asyncio
async def test_e_unknown_host_and_runtime_tool_name(tmp_path):
    d=decision(tmp_path);reg=Registry([binding(d)]);a=reserved(d)
    receipt=await invoke_reserved(a,reg,verify_request=verify_execution)
    p.record_result({'attempts':[a]},attempt_id='attempt',status='COMPLETED',
        job_id='owned-task',output_hash='b'*64,evidence='offline',execution_receipt=receipt)
    assert a['status']=='COMPLETED' and a['execution_receipt']['task_id']=='owned-task'
    assert 'arbitrary_runtime_tool' not in str(d['production_route'])


@pytest.mark.asyncio
async def test_f_future_flux_local_backend_still_mcp(tmp_path):
    d=decision(tmp_path,local=True);reg=Registry([binding(d),desktop(d)])
    result=await invoke_reserved(reserved(d),reg,verify_request=verify_execution)
    assert result['execution']['backend']['provider']=='local-comfy'
    assert result['execution']['capability']['model_key']=='flux-3'
    assert result['execution']['transport']=='MCP'


@pytest.mark.parametrize('path,value',[
    (('transport',),'GUI'),(('backend','provider'),'private-comfy'),
    (('backend','backend_key'),'private-mcp'),(('mcp','capability_key'),'other-capability')])
def test_g_execution_changes_route_fingerprint_and_invalidates_seal(tmp_path,path,value):
    d=decision(tmp_path);changed=deepcopy(d)
    target=changed['production_route']['execution']
    for key in path[:-1]:target=target[key]
    target[path[-1]]=value
    assert fp(changed['production_route'])!=d['route_fingerprint']
    assert fp(changed['production_route']['execution'])!=d['execution_fingerprint']
    with pytest.raises(ValueError):verify_execution(changed)
    changed['fingerprint']=fp({k:v for k,v in changed.items() if k!='fingerprint'})
    with pytest.raises(ValueError):verify_decision(changed)


@pytest.mark.parametrize('transport',['GUI','Desktop','HTTP','LOCALHOST','browser'])
def test_new_cinematic_route_cannot_express_direct_execution(tmp_path,transport):
    d=decision(tmp_path);raw=deepcopy(d['production_route']);raw['execution']['transport']=transport
    with pytest.raises(ValueError):ProductionRoute.model_validate(raw)
    raw.pop('execution')
    with pytest.raises(ValueError,match='MCP_CAPABILITY_UNAVAILABLE'):
        qualify_route(ProductionRoute.model_validate(raw))


def test_reserve_requires_discovered_binding_and_result_requires_receipt(tmp_path,monkeypatch):
    d=decision(tmp_path);monkeypatch.setattr(p,'video_verifier',verify_execution)
    state=p.new_stage(stage_id='OFFLINE',authorization_ref='offline',budget_credits=300,
        frames=[d],protected_targets=[])
    with pytest.raises(ValueError,match='MCP_CAPABILITY_UNAVAILABLE'):
        p.reserve(state,'S1',**quote(d))
    a=p.reserve(state,'S1',**quote(d),execution_binding=binding(d))
    with pytest.raises(ValueError,match='EXECUTION_ROUTE_MISMATCH'):
        p.record_result(state,attempt_id=a['attempt_id'],status='COMPLETED',job_id='job',
            output_hash='a'*64,evidence='unattributed output')


@pytest.mark.asyncio
async def test_auth_renewal_same_seal_and_wrong_schema_stop(tmp_path):
    d=decision(tmp_path);before=deepcopy(d);b=binding(d);b['authenticated']=False
    reg=Registry([b])
    with pytest.raises(ValueError,match='MCP_AUTHENTICATION_REQUIRED'):await resolve_mcp(d,reg)
    reg.entries[0]['authenticated']=True
    assert (await resolve_mcp(d,reg)).authenticated and d==before
    reg.entries[0]['provider_schema_fingerprint']='0'*64
    with pytest.raises(ValueError,match='EXECUTION_ROUTE_MISMATCH'):await resolve_mcp(d,reg)
    assert reg.calls==[]


def test_core_has_no_host_api_dependency_or_model_dispatch():
    root=Path(__file__).resolve().parents[1]
    for name in ('shot-production','video-model-selection'):
        text=(root/'skills'/name/'SKILL.md').read_text()
        for forbidden in ('cua.getApp','osascript','mcp__codex_app','ChatGPT Desktop API','macOS GUI API'):
            assert forbidden not in text
    source=(root/'src/drama_plugin/visual/execution.py').read_text()
    assert all(x not in source for x in ('hosts.', 'comfy', 'seedance', 'Codex', 'subprocess'))
    assert len(list((root/'skills').glob('*/skill.yaml')))==14


@pytest.mark.asyncio
async def test_ambiguous_call_is_not_submitted_twice(tmp_path):
    d=decision(tmp_path);reg=Registry([binding(d)])
    def fail(result):raise TimeoutError('unknown cloud outcome')
    reg.mutation=fail
    with pytest.raises(TimeoutError):await invoke_reserved(reserved(d),reg,verify_request=verify_execution)
    with pytest.raises(ValueError,match='RECOVER_ORIGINAL_MCP_SUBMISSION'):
        await invoke_reserved(reserved(d),reg,verify_request=verify_execution)
    assert len(reg.calls)==1


@pytest.mark.asyncio
async def test_invocation_rejects_wrong_backend_return(tmp_path):
    d=decision(tmp_path);reg=Registry([binding(d)])
    reg.mutation=lambda result:result['execution']['backend'].update(provider='local-comfy')
    with pytest.raises(ValueError,match='EXECUTION_ROUTE_MISMATCH'):
        await invoke_reserved(reserved(d),reg,verify_request=verify_execution)


def test_durable_claim_is_unknown_and_cannot_repeat(tmp_path,monkeypatch):
    monkeypatch.setattr(p,'video_verifier',verify_execution)
    a=reserved(decision(tmp_path));state={'attempts':[a]}
    assert p.begin_submission(state,attempt_id='attempt')['status']=='UNKNOWN'
    with pytest.raises(ValueError,match='RECOVER_ORIGINAL_MCP_SUBMISSION'):
        p.begin_submission(state,attempt_id='attempt')


@pytest.mark.asyncio
async def test_dry_discovery_never_allows_dispatch(tmp_path):
    d=decision(tmp_path);d.update(dry_run_only=True,submission_allowed=False)
    d['fingerprint']=fp({k:v for k,v in d.items() if k!='fingerprint'})
    reg=Registry([binding(d)])
    with pytest.raises(ValueError,match='DRY_RUN'):await resolve_mcp(d,reg)
    assert await resolve_mcp(d,reg,allow_dry_run=True)
    with pytest.raises(ValueError,match='DRY_RUN'):
        await invoke_reserved(reserved(d),reg,verify_request=verify_execution)
    assert reg.calls==[] and not reg.claims


def test_current_formal_route_drift_blocks_old_seal(tmp_path):
    d=decision(tmp_path);route=deepcopy(d['production_route'])
    route['candidate']['cost']['components']={'video':200,'audio':0,'references':0,'addons':0,'correction':0}
    route['inputs']=[dict(target_id='I',purpose='VIDEO_INPUT',role='REFERENCE',for_targets=['S1'],
        preparation='REUSE',specification='offline existing',rationale='offline',cost_key='references',source_media_id='M')]
    assert qualify_route(ProductionRoute.model_validate(route))['eligible']
    # Even unchanged execution with a changed complete route requires resealing.
    with pytest.raises(ValueError,match='EXECUTION_ROUTE_MISMATCH'):
        p._route_frame_gate({'production_route':route,'attempts':[]},d)
    route['execution']['backend']['provider']='local-comfy'
    with pytest.raises(ValueError,match='EXECUTION_ROUTE_MISMATCH'):
        p._route_frame_gate({'production_route':route,'attempts':[]},d)
