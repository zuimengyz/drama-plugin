"""Offline still binding; unchanged compiled request and existing reservation."""
from copy import deepcopy
from pathlib import Path
from typing import Any
import pytest

# Retained provider contracts; active Ark admission has a separate test suite.
pytestmark = pytest.mark.usefixtures("retained_production_policy")
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual.frame_request import compile_frame, verify_compiled
from drama_plugin.visual.execution import still_execution, validate_binding
from drama_plugin.visual import production as p
from drama_plugin.hosts.mcp_execution import resolve_mcp, invoke_reserved
from test_route_image_inputs import image_input
from test_visual_prompt_ir import visual_ir
from test_video_selection import evidence
from test_mcp_execution import Registry


def fixture(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    spec, _ = image_input(tmp_path)  # type: ignore[no-untyped-call]
    ir = visual_ir('TEXT_TO_IMAGE')  # type: ignore[no-untyped-call]
    ir['subjects'] = [{**deepcopy(ir['subjects'][0]), 'id': a.entity_key} for a in spec.actors]
    ir['source_fingerprint'] = fp(spec.model_dump(mode='json', exclude={'prompt_ir'}))
    d = compile_frame(spec.model_copy(update={'prompt_ir': ir}))
    schema = {'nodes': [{'name': 'OpenAIGPTImageNodeV2', 'input_details': [
        {'name': k, **({'options': ['gpt-image-2']} if k == 'model' else {})}
        for k in ('prompt', 'model', 'model.size', 'model.custom_width', 'model.custom_height', 'model.background', 'model.quality', 'n', 'seed')]},
        {'name': 'SaveImage', 'input_details': [{'name': 'images'}, {'name': 'filename_prefix'}]}]}
    b = dict(execution=still_execution(d), server_id='offline-comfy', tool_name='submit_workflow',
        operation='submit_workflow', provider_schema=schema, provider_schema_fingerprint=fp(schema),
        request_fingerprint=fp(d['request']), evidence=evidence(), authenticated=True)  # type: ignore[no-untyped-call]
    return d,b


@pytest.mark.asyncio
async def test_existing_reservation_bind_claim_and_dispatch(tmp_path: Path) -> None:
    d,b = fixture(tmp_path); original = deepcopy(d)
    state = p.new_campaign([d]); a = p.reserve(state,d['spec']['shot_id'])
    before = deepcopy(a)
    reg = Registry([b])  # type: ignore[no-untyped-call]
    bound = await resolve_mcp(d, reg)
    p.bind_still_execution(state, attempt_id=a['attempt_id'], execution_binding=bound.model_dump(mode='json'))
    assert {k:v for k,v in a.items() if k != 'execution_binding'} == before
    async def claim(attempt_id: str) -> dict[str, Any]:return p.begin_submission(state, attempt_id=attempt_id)
    result = await invoke_reserved(deepcopy(a),reg,verify_request=verify_compiled,claim_submission=claim,state=state)
    assert len(state['attempts']) == 1 and len(reg.calls) == 1 and d == original
    assert reg.calls[0][1] == d['request']
    assert 'provider_schema' not in reg.calls[0][1] and 'approved_interpretation_refs' not in reg.calls[0][1]
    p.record_result(state,attempt_id=a['attempt_id'],status='COMPLETED',job_id=result['task_id'],output_hash='a'*64,evidence='offline',execution_receipt=result)
    with pytest.raises(ValueError,match='UNUSED_STILL'):p.bind_still_execution(state,attempt_id=a['attempt_id'],execution_binding=b)


@pytest.mark.asyncio
@pytest.mark.parametrize('fault',['missing','model','schema','request','node','authentication','expired'])
async def test_invalid_still_capability_rejected(tmp_path: Path, fault: str) -> None:
    d,b=fixture(tmp_path)
    if fault=='model':b['execution']['capability']['model_key']='other'
    if fault=='schema':b['provider_schema_fingerprint']='a'*64
    if fault=='request':b['request_fingerprint']='b'*64
    if fault=='node':
        b['provider_schema']['nodes']=[];b['provider_schema_fingerprint']=fp(b['provider_schema'])
    if fault=='authentication':b['authenticated']=False
    if fault=='expired':b['evidence']['expires_at']='2000-01-01T00:00:00Z'
    with pytest.raises(ValueError):await resolve_mcp(d,Registry([] if fault=='missing' else [b]))  # type: ignore[no-untyped-call]
    with pytest.raises(ValueError):validate_binding(d,None)


def test_missing_binding_cannot_claim_reserved_image(tmp_path: Path) -> None:
    d,_=fixture(tmp_path);state=p.new_campaign([d]);a=p.reserve(state,d['spec']['shot_id'])
    with pytest.raises(ValueError,match='still discovery'):p.begin_submission(state,attempt_id=a['attempt_id'])
    assert a['status']=='RESERVED' and len(state['attempts'])==1
