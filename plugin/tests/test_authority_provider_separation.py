"""Real saved authority chain replay; synthetic inputs never generate media."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.hosts.specialized_asset import (compile_authority_context, validate_authority_context,
    validate_visual_submission, bind_video_request, authority_semantics)
from drama_plugin.hosts.cinematic_projection import project, validate_projection
from drama_plugin.hosts.prompt_budget import budget_prompt
from test_specialized_asset import fixture
from test_official_video_providers import request

ROOT = Path(__file__).parent / 'fixtures'


@pytest.fixture
def real_authority(tmp_path, monkeypatch):
    captured = json.loads((ROOT / 'authority-provider/S02-K02-authority.json').read_text())
    for name, value in captured['store'].items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    monkeypatch.setenv('DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT', str(tmp_path))
    work = NS(**captured['work'])
    frozen = json.loads((ROOT / 'prompt-budget/S02-K02-frozen.json').read_text())
    return work, frozen, compile_authority_context(work, frozen)


def diagnostic(frozen, context):
    node = json.loads((ROOT / 'prompt-budget/vidu-current-node.json').read_text())['data'][0]
    r = NS(frozen_creative={'cinematic_direction': frozen}, sound='NATIVE_AUDIO', reference_duties=(), authority_context=context)
    c = NS(parameters={'model.audio': True}, model='Vidu Q3 Turbo', variant='viduq3-turbo', capability={'node_schema': node})
    with pytest.raises(ValueError, match='REQUIRED_REFERENCE_UNFULFILLED') as failure:
        project(r, c, {'class_type': 'Vidu3ImageToVideoNode'})
    return failure.value.projection


def test_real_9736_authority_context_and_provider_budget(real_authority):
    work, frozen, context = real_authority
    before = deepcopy(frozen)
    assert sum(len(a['receipt']['prompt']) for a in context['assets']) == 9736
    validate_authority_context(context, frozen, work)
    result = diagnostic(frozen, context)
    payload = {'tool': 'run_template', 'name': 'api_vidu_q3_image_to_video', 'input_overrides': {'14': {'prompt': result['prompt']}}}
    validate_visual_submission(work, payload, authority_context=context, creative_intent=frozen)
    validate_visual_submission(work, {'videoRequest': {'inputMode': 'text_to_video', 'prompt': result['prompt']}},
                               authority_context=context, creative_intent=frozen)
    assert len(result['prompt']) <= 2000
    assert '后续S05' not in result['prompt']
    assert result['prompt_budget']['hardMaxPromptCharacters'] == 2000
    for asset in context['assets']:
        assert asset['receipt']['prompt'] not in result['prompt']
        assert asset['executableSemantic'] in result['prompt']
    assert 'authority_context' not in json.dumps(payload)
    assert frozen == before
    assert '"妈妈……先生，妈妈……"' in result['prompt']
    with pytest.raises(ValueError, match='EXECUTION_CRITICAL_UNSUPPORTED'):
        validate_projection(result)


@pytest.mark.parametrize('fault', ['asset', 'hash', 'source_map', 'compiled_from', 'source_text', 'intent', 'semantic'])
def test_missing_or_changed_evidence_fails_even_with_refingerprinting(real_authority, fault):
    work, frozen, context = real_authority
    altered = deepcopy(context)
    if fault == 'asset':
        altered['assets'].pop()
    elif fault == 'hash':
        altered['assets'][0]['compilationFingerprint'] = '0' * 64
    elif fault == 'source_map':
        altered['assets'][0]['sourceMap'] = {}
    elif fault == 'compiled_from':
        altered['assets'][0]['compiledFrom'] = {}
    elif fault == 'source_text':
        altered['assets'][0]['receipt']['prompt'] = 'look plausible'
    elif fault == 'intent':
        altered['creativeIntent'] = {}
    else:
        altered['assets'][0]['executableSemantic'] = 'invented'
    altered['fingerprint'] = fp({k: v for k, v in altered.items() if k != 'fingerprint'})
    with pytest.raises(ValueError, match='AUTHORITY_CONTEXT_CHANGED'):
        validate_authority_context(altered, frozen, work)


def test_correct_looking_prompt_cannot_replace_missing_context(real_authority):
    work, frozen, context = real_authority
    payload = {'prompt': authority_semantics(context)}
    with pytest.raises(ValueError, match='AUTHORITY_CONTEXT_REQUIRED'):
        validate_visual_submission(work, payload, creative_intent=frozen)
    with pytest.raises(ValueError, match='SEMANTICS_MISSING'):
        validate_visual_submission(work, {'prompt': 'plausible scene'}, authority_context=context, creative_intent=frozen)
    changed = deepcopy(work)
    changed.content['specializedAssetCompilationRefs'].pop()
    with pytest.raises(ValueError, match='AUTHORITY_CONTEXT_CHANGED'):
        validate_visual_submission(changed, payload, authority_context=context, creative_intent=frozen)


def test_pollution_fails_final_budget(real_authority):
    _, frozen, context = real_authority
    result = diagnostic(frozen, context)
    polluted = result['prompt'] + '\n' + '\n'.join(a['receipt']['prompt'] for a in context['assets'])
    with pytest.raises(ValueError, match='PROVIDER_PROMPT_BUDGET_EXCEEDED'):
        budget_prompt(polluted, polluted, model='Vidu Q3 Turbo', limit=2000, source='runtime_node_schema')


def test_generic_video_and_http_payload_only_send_executable_semantics(tmp_path, monkeypatch):
    host, bible, ref, current = fixture(tmp_path, medium='cg')
    compilation = host.compile(ref, 'room', current=current)
    monkeypatch.setenv('DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT', str(tmp_path))
    work = NS(id='work', content={'movieVisualMediumRef': dump_contract(bible.runtime_ref),
        'specializedAssetCompilationRefs': [compilation['compilationRef']], 'visualSourceCurrent': current})
    r = request()
    r.continuity.work_id = 'work'
    from test_official_video_providers import with_ir
    r = with_ir(r)
    bound = bind_video_request(work, r)
    validate_visual_submission(work, dump_contract(bound))
    validate_visual_submission(work, {'provider': 'seedance', 'videoRequest': dump_contract(bound)})
    assert r.authority_context is None
    assert compilation['compilation']['prompt'] not in bound.prompt
    from drama_plugin.providers.video.adapters import SeedanceProvider
    provider = NS(model_spec={'vendor_model': 'offline'})
    body = SeedanceProvider.payload(provider, bound, {}, 'offline')
    assert 'authority_context' not in json.dumps(body)
    assert compilation['compilation']['prompt'] not in json.dumps(body)
    changed = dump_contract(bound)
    changed['prompt'] = 'correct-looking prompt'
    with pytest.raises(ValueError, match='COMPILED_REPRESENTATION_CHANGED'):
        validate_visual_submission(work, changed)


def test_legacy_asset_image_chain_still_valid(tmp_path, monkeypatch):
    host, bible, ref, current = fixture(tmp_path)
    compilation = host.compile(ref, 'room', current=current)
    monkeypatch.setenv('DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT', str(tmp_path))
    work = NS(id='work', content={'movieVisualMediumRef': dump_contract(bible.runtime_ref),
        'specializedAssetCompilationRefs': [compilation['compilationRef']], 'visualSourceCurrent': current})
    validate_visual_submission(work, {'prompt': compilation['projection']['prompt']})
    with pytest.raises(ValueError, match='CONTAINS_AUTHORITY_CONTEXT'):
        validate_visual_submission(work, {'prompt': compilation['compilation']['prompt']})
