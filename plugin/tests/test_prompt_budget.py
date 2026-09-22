"""No network or paid generation; real S02-K02 intent + synthetic transport tests."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.hosts.prompt_budget import prompt_limit, budget_prompt, PromptBudgetExceeded, compact_prose, PROVENANCE
from drama_plugin.hosts.cinematic_projection import project, validate_projection, leaves
from drama_plugin.hosts.comfy_video import NODES
from drama_plugin.visual.cinematic import selection_handoff
from test_video_reconciliation import current_fixture, compile_all

ROOT = Path(__file__).parent / 'fixtures/prompt-budget'


def test_limit_source_priority_and_runtime_tooltip():
    node = json.loads((ROOT / 'vidu-current-node.json').read_text())['data'][0]
    assert prompt_limit({'node_schema': node, 'maxPromptCharacters': 9999}, NODES['Vidu3ImageToVideoNode'], 'viduq3-pro') == (2000, 'runtime_node_schema')
    assert prompt_limit({'node_schema': {'maxPromptCharacters': 100}, 'maxPromptCharacters': 300}, {'prompt': 'prompt', 'prompt_limit': 50}) == (100, 'runtime_node_schema')
    assert prompt_limit({'maxPromptCharacters': 300}, {'prompt': 'prompt', 'prompt_limit': 50}) == (300, 'provider_capability')
    assert prompt_limit({}, {'prompt': 'prompt', 'prompt_limit': 50}) == (50, 'adapter_fallback')
    assert prompt_limit({}, {'prompt': 'prompt'}) == (None, 'NOT_DECLARED')


def test_fit_is_byte_for_byte_and_reservation():
    original = '对白: "不要改写……"\n  retain spaces'
    final, budget = budget_prompt(original, 'not used', model='x', limit=len(original) + 10, source='test', reserved=10)
    assert final == original and budget['status'] == 'FIT'
    assert budget['effectivePromptBudget'] == len(original)
    with pytest.raises(PromptBudgetExceeded) as failure:
        budget_prompt(original, original, model='x', limit=len(original), source='test', reserved=1)
    assert failure.value.budget['status'] == 'EXCEEDED'
    assert 'model=x' in str(failure.value) and 'compressed_length=' in str(failure.value)


def test_structural_compaction_preserves_values_and_actor_scope():
    data = [{'actor': 'A', 'behavior': '抓住左袖，不放手', 'target': 'B'}, {'actor': 'B', 'behavior': '抓住左袖，不放手', 'target': 'A'}]
    out = compact_prose(data)
    assert out == '{人:A；行为:抓住左袖，不放手；对象:B}；{人:B；行为:抓住左袖，不放手；对象:A}'
    assert compact_prose({'instructions': {'unknown': 'startState: 原词不可替换'}}) == '指令:unknown:startState: 原词不可替换'


def test_formal_vidu_final_budget_and_source_immutable(tmp_path):
    r, c, g, s, host = current_fixture(tmp_path)
    frozen = r.frozen_creative['cinematic_direction']
    frozen['spec']['performance']['beats'][0]['actions'][0]['prop'] = '木架必须持续被双手支撑，不能消失。' * 40
    frozen['fingerprint'] = fp({k: v for k, v in frozen.items() if k != 'fingerprint'})
    r = r.model_copy(update={'frozen_creative': selection_handoff(frozen)})
    before = deepcopy(r.model_dump())
    result = project(r, c, {'class_type': 'Vidu3ImageToVideoNode'})
    assert result['prompt_budget']['originalCharacters'] > 2000
    assert result['prompt_budget']['status'] == 'COMPRESSIBLE'
    request = compile_all(r, c, g, s, host)
    assert request['input_overrides']['14']['prompt'] == result['prompt']
    assert len(result['prompt']) <= 2000
    assert frozen['spec']['performance']['beats'][0]['actions'][0]['prop'] in result['prompt']
    assert r.model_dump() == before
    validate_projection(result)
    # A different model recompiles the intact source, never the compact text.
    other = project(r, NS(parameters={'model.generate_audio': True}, capability={}, model='Seedance 2.5', variant='Seedance 2.5'), {'class_type': 'ByteDance2ReferenceNodeV2'})
    assert other['prompt_budget']['status'] == 'FIT' and len(other['prompt']) > 2000
    assert 'GLOBAL VISUAL / WORLD' in other['prompt']


def test_uncompressible_blocks_without_touching_source(tmp_path):
    r, c, g, s, host = current_fixture(tmp_path)
    f = r.frozen_creative['cinematic_direction']
    f['spec']['performance']['beats'][0]['actions'][0]['behavior'] = '不可删除的关键动作' * 300
    f['fingerprint'] = fp({k: v for k, v in f.items() if k != 'fingerprint'})
    r = r.model_copy(update={'frozen_creative': selection_handoff(f)})
    before = deepcopy(r.model_dump())
    with pytest.raises(PromptBudgetExceeded) as failure:
        compile_all(r, c, g, s, host)
    budget = failure.value.budget
    assert budget['compressedCharacters'] > 2000 and budget['originalCharacters'] > 2000
    assert budget['model'] == 'Vidu Q3 Pro' and budget['hardMaxPromptCharacters'] == 2000
    assert r.model_dump() == before


def test_current_s02_k02_budget_passes_but_missing_media_still_blocks():
    frozen = json.loads((ROOT / 'S02-K02-frozen.json').read_text())
    original = deepcopy(frozen)
    node = json.loads((ROOT / 'vidu-current-node.json').read_text())['data'][0]
    r = NS(frozen_creative={'cinematic_direction': frozen}, sound='NATIVE_AUDIO', reference_duties=())
    c = NS(parameters={'model.audio': True}, capability={'node_schema': node}, model='Vidu Q3 Pro', variant='viduq3-pro')
    with pytest.raises(ValueError, match='REQUIRED_REFERENCE_UNFULFILLED') as failure:
        project(r, c, {'class_type': 'Vidu3ImageToVideoNode'})
    result = failure.value.projection
    assert result['prompt_budget']['limitSource'] == 'runtime_node_schema'
    assert result['prompt_budget']['status'] == 'COMPRESSIBLE'
    assert len(result['prompt']) <= 2000
    assert '"妈妈……先生，妈妈……"' in result['prompt']
    # Every creative string still sent verbatim; only four provenance keys leave
    # the model text. This guards actual actions, voice, space and continuity.
    for item in result['manifest']:
        if item['destination'] == 'PROMPT':
            value = leaves(frozen['spec'])[item['canonical_field']]
            if isinstance(value, str) and value:
                assert value in result['prompt'], item['canonical_field']
    assert frozen == original
    with pytest.raises(ValueError, match='EXECUTION_CRITICAL_UNSUPPORTED'):
        validate_projection(result)


def test_final_projection_budget_cannot_ignore_appended_text(tmp_path):
    r, c, *_ = current_fixture(tmp_path)
    result = project(r, c, {'class_type': 'Vidu3ImageToVideoNode'})
    result['prompt'] += 'X' * 2000
    with pytest.raises(ValueError, match='PROMPT_BUDGET_INVALID'):
        validate_projection(result)
