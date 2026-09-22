"""Captured live MCP schemas + offline receipts; never dispatch generation."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.hosts.comfy_video import bind_capability, compile_request, inspect_graph, verify_execution
from drama_plugin.hosts.cinematic_projection import project
from drama_plugin.visual.video_selection import Candidate, Requirements, seal_decision, model_key
from seedance_helpers import seed_fixture, execution_plan
from test_video_selection import evidence, quote

ROOT = Path(__file__).parent / 'fixtures/video-reconciliation'


def read(name):
    return json.loads((ROOT / (name + '.json')).read_text())


def current_fixture(tmp_path, route='api_vidu_q3_image_to_video', variant='viduq3-pro'):
    mode = 't2v' if route.endswith(('text_to_video', '_t2v')) else 'flf2v' if route.endswith('_flf2v') else 'r2v'
    r, c, _, _, host = seed_fixture(tmp_path, mode)
    graph = read(route + '-get_template')['workflow_json']
    schema = read(route + '-get_template_schema')
    inspected = inspect_graph(graph, schema)
    node = next(n for n in read('node-schemas')['data'] if n['name'] == inspected['class_type'])
    vidu = node['name'].startswith('Vidu')
    prompt_key = 'prompt' if vidu else 'model.prompt'
    params = next(n['inputs'].copy() for n in schema['nodes'] if n['class_type'] == node['name'])
    params.pop(prompt_key)
    params.update({'model': variant, 'model.duration': 8})
    for key in ('model.ratio', 'model.aspect_ratio'):
        if key in params:
            params[key] = '16:9'
    if vidu:
        params['model.audio'] = True
        data = r.model_dump()
        data['controls'] = inspected['controls'] + ['NATIVE_AUDIO']
        for inp in data['inputs']:
            inp['role'] = 'FIRST_FRAME'
        for duty in data['reference_duties']:
            duty['provider_slot'] = 'image'
        r = Requirements.model_validate(data)
    cap = bind_capability(node, graph, schema, evidence(), variant=variant if vidu else None)
    c = Candidate.model_validate({**c.model_dump(), 'model': 'Vidu Q3 ' + ('Pro' if variant == 'viduq3-pro' else 'Turbo') if vidu else variant,
        'variant': variant, 'template': route, 'parameters': params, 'capability': cap,
        'graph_hash': fp(graph), 'adapter_fingerprint': fp(inspected), 'controls': r.controls,
        'combinations': [r.controls], 'durations': list(range(1, 17)) if vidu else list(range(4, 31))})
    Path(host['graph_path']).write_text(json.dumps(graph))
    Path(host['schema_path']).write_text(json.dumps(schema))
    return r, c, graph, schema, host


def compile_all(r, c, graph, schema, host):
    return compile_request(r, c, graph, schema, host['bindings'], r.frozen_creative['motion_prompt'])


ROUTES = [(f'api_vidu_q3_{mode}_to_video', variant) for mode in ('image', 'text') for variant in ('viduq3-pro', 'viduq3-turbo')]
ROUTES += [(f'api_seedance2_5_{mode}', 'Seedance 2.5') for mode in ('t2v', 'r2v', 'flf2v')]


@pytest.mark.parametrize('route,variant', ROUTES)
def test_live_schema_compile_project_quote_seal(tmp_path, route, variant, monkeypatch):
    from drama_plugin.visual import production
    r, c, graph, schema, host = current_fixture(tmp_path, route, variant)
    request = compile_all(r, c, graph, schema, host)
    ins = inspect_graph(graph, schema)
    projection = project(r, c, ins)
    key = 'prompt' if variant.startswith('vidu') else 'model.prompt'
    assert request['input_overrides'][ins['model_node']][key] == projection['prompt']
    assert c.capability['model_key'] == model_key(c)
    assert {x['provider_field'] for x in projection['manifest'] if x['destination'] == 'PROMPT'} == {key}
    if variant.startswith('vidu'):
        assert len(projection['prompt']) <= 2000
        assert any(x['provider_field'] == 'model.audio' for x in projection['manifest'])
    sealed = seal_decision(r, c, request, stage_id='OFFLINE', rationale='Offline schema reconciliation', comparisons=[],
        fallback='stop', host_adapter=host, production_route=execution_plan(r, c))
    verify_execution(sealed)
    # Real reservation code, synthetic quote/receipt only, no MCP execution.
    monkeypatch.setattr(production, 'video_verifier', verify_execution)
    state = production.new_stage(stage_id='OFFLINE', authorization_ref='OFFLINE ONLY', budget_credits=1000,
        frames=[sealed], protected_targets=[])
    from test_mcp_execution import binding
    attempt = production.reserve(state, r.target_id, **quote(sealed), execution_binding=binding(sealed))
    assert attempt['status'] == 'RESERVED'
    dry = seal_decision(r, c, request, stage_id='OFFLINE', rationale='Offline', comparisons=[], fallback='stop', host_adapter=host, dry_run=True)
    verify_execution(dry, allow_dry_run=True)
    with pytest.raises(ValueError, match='DRY_RUN'):
        verify_execution(dry)


@pytest.mark.parametrize('variant', ['viduq3-pro', 'viduq3-turbo'])
@pytest.mark.parametrize('field,value', [('model.duration', 0), ('model.duration', 17), ('model.resolution', '480p'),
    ('model.audio', False), ('model', 'viduq3-unknown'), ('seed', -1)])
def test_invalid_parameters_block(tmp_path, variant, field, value):
    r, c, g, s, host = current_fixture(tmp_path, variant=variant)
    c.parameters[field] = value
    with pytest.raises(ValueError):
        compile_all(r, c, g, s, host)


@pytest.mark.parametrize('route,variant', ROUTES)
@pytest.mark.parametrize('mutation', ['unknown_paid', 'additional_paid', 'schema_type', 'duration_schema', 'removed_audio', 'wrong_input'])
def test_fail_closed(tmp_path, route, variant, mutation):
    r, c, g, s, host = current_fixture(tmp_path, route, variant)
    ins = inspect_graph(g, s)
    if mutation == 'unknown_paid':
        next(n for n in g['nodes'] if str(n['id']) == ins['model_node'])['type'] = 'UnknownPaidVideoNode'
    elif mutation == 'additional_paid':
        g['nodes'].append({'id': 9999, 'type': 'Vidu3TextToVideoNode'})
    elif mutation == 'schema_type':
        next(n for n in s['nodes'] if n['id'] == ins['model_node'])['class_type'] = 'DifferentVideoNode'
    elif mutation in ('duration_schema', 'removed_audio'):
        fields = c.capability['node_schema']['input_details']
        if mutation == 'duration_schema':
            next(f for f in fields if f['name'] == 'model.duration')['max'] = 999
        else:
            fields[:] = [f for f in fields if f['name'] not in ('model.audio', 'model.generate_audio')]
        c.capability['fingerprint'] = fp({k: v for k, v in c.capability.items() if k != 'fingerprint'})
    else:
        r = r.model_copy(update={'controls': ('LAST_FRAME', 'NATIVE_AUDIO')})
    with pytest.raises(ValueError):
        compile_all(r, c, g, s, host)


def test_vidu_identity_and_prompt_limit(tmp_path):
    r, c, g, s, host = current_fixture(tmp_path)
    c = c.model_copy(update={'model': 'Vidu Q3 Turbo'})
    with pytest.raises(ValueError, match='MODEL_MISMATCH'):
        compile_all(r, c, g, s, host)
    r, c, g, s, host = current_fixture(tmp_path)
    r = r.model_copy(update={'frozen_creative': {'motion_prompt': 'x' * 2001}})
    with pytest.raises(ValueError, match='PROVIDER_PROMPT_BUDGET_EXCEEDED'):
        compile_all(r, c, g, s, host)
    r = r.model_copy(update={'frozen_creative': {'motion_prompt': 'x' * 2000}})
    assert compile_all(r, c, g, s, host)


@pytest.mark.parametrize('duration', [1, 16])
def test_vidu_duration_boundaries_no_clamp(tmp_path, duration):
    r, c, g, s, host = current_fixture(tmp_path)
    r = r.model_copy(update={'duration_seconds': duration, 'frozen_creative': {'motion_prompt': 'Continuous action'}})
    c.parameters['model.duration'] = duration
    assert compile_all(r, c, g, s, host)['input_overrides']['14']['model.duration'] == duration


def test_real_compile_entry_is_offline(tmp_path):
    r, c, g, s, host = current_fixture(tmp_path)
    payload = {'requirements': r.model_dump(mode='json'), 'candidate': c.model_dump(mode='json'),
        'host_adapter': host, 'stage_id': 'OFFLINE', 'rationale': 'Offline', 'fallback': 'stop'}
    path = tmp_path / 'cli.json'
    path.write_text(json.dumps(payload))
    entry = Path(__file__).resolve().parents[1] / 'skills/shot-production/scripts/compile_video.py'
    result = subprocess.run([sys.executable, str(entry), '--input', str(path), '--output', str(tmp_path / 'out')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['paidGenerationCalls'] == 0
    assert json.loads(result.stdout)['submissionAllowed'] is False


@pytest.mark.parametrize('route,mode,kind,model', [
    ('api_bfl_flux3_i2v', 'r2v', 'Flux3ImageToVideoNode', 'FLUX 3'),
    ('api_minimax_h3_flf2v', 'flf2v', 'MinimaxHailuo03FirstLastFrameNode', 'MiniMax H3'),
    ('api_minimax_h3_r2v', 'r2v', 'MinimaxHailuo03ReferenceNode', 'MiniMax H3'),
])
def test_existing_adapters_with_live_schemas(tmp_path, route, mode, kind, model):
    r, c, _, _, host = seed_fixture(tmp_path, mode)
    g = read(route + '-get_template')['workflow_json']
    s = read(route + '-get_template_schema')
    ins = inspect_graph(g, s)
    node = read(kind)['data'][0]
    params = next(n['inputs'].copy() for n in s['nodes'] if n['class_type'] == kind)
    prompt_key = 'prompt' if model == 'FLUX 3' else 'model.prompt'
    params.pop(prompt_key)
    params['duration' if model == 'FLUX 3' else 'model.duration'] = '8' if model == 'FLUX 3' else 8
    for key in ('aspect_ratio', 'model.ratio'):
        if key in params:
            params[key] = '16:9'
    data = r.model_dump()
    data['controls'] = ins['controls'] + ['NATIVE_AUDIO']
    for i, inp in enumerate(data['inputs']):
        inp['role'] = ins['controls'][i]
    for duty in data['reference_duties']:
        duty['provider_slot'] = ins['input_ports'][0]
    r = Requirements.model_validate(data)
    c = Candidate.model_validate({**c.model_dump(), 'model': model, 'variant': model, 'parameters': params,
        'template': route, 'capability': bind_capability(node, g, s, evidence()), 'graph_hash': fp(g),
        'adapter_fingerprint': fp(ins), 'controls': r.controls, 'combinations': [r.controls]})
    Path(host['graph_path']).write_text(json.dumps(g))
    Path(host['schema_path']).write_text(json.dumps(s))
    request = compile_all(r, c, g, s, host)
    d = seal_decision(r, c, request, stage_id='OFFLINE', rationale='Regression', comparisons=[], fallback='stop',
        host_adapter=host, production_route=execution_plan(r, c))
    verify_execution(d)


def test_disabled_runtime_model_stays_blocked(tmp_path, monkeypatch):
    from drama_plugin.visual.video_selection import qualify
    r, c, g, s, host = current_fixture(tmp_path, 'api_seedance2_5_t2v', 'Seedance 2.5')
    monkeypatch.setenv('DRAMA_VIDEO_MODEL_SEEDANCE_2_5_ENABLED', 'false')
    assert 'MODEL_DISABLED' in qualify(r, c)['exclusions']
    with pytest.raises(ValueError, match='INELIGIBLE'):
        seal_decision(r, c, compile_all(r, c, g, s, host), stage_id='OFFLINE', rationale='Disabled', comparisons=[],
            fallback='stop', host_adapter=host, dry_run=True)


def test_schema_fixture_contract_is_reproducible():
    from drama_plugin.hosts.comfy_video import validate_node_contract
    for node in read('node-schemas')['data']:
        validate_node_contract(node)


def test_vidu_silent_and_input_derived_aspect(tmp_path):
    r, c, g, s, host = current_fixture(tmp_path)
    r = r.model_copy(update={'sound': 'SILENT', 'controls': ('FIRST_FRAME',), 'frozen_creative': {'motion_prompt': 'Hold still'}})
    c.parameters['model.audio'] = False
    assert compile_all(r, c, g, s, host)['input_overrides']['14']['model.audio'] is False
    r = r.model_copy(update={'aspect_ratio': '9:16'})
    with pytest.raises(ValueError, match='ASPECT_UNVERIFIED'):
        compile_all(r, c, g, s, host)


def test_text_route_cannot_use_image_route_2k_resolution(tmp_path):
    r, c, g, s, host = current_fixture(tmp_path, 'api_vidu_q3_text_to_video')
    c.parameters['model.resolution'] = '2K'
    with pytest.raises(ValueError, match='OPTION_UNSUPPORTED'):
        compile_all(r, c, g, s, host)
