"""Provider hard limits measure intact text; no pre-submit shortening path."""
import pytest
from drama_plugin.hosts.prompt_budget import prompt_limit, check_prompt_limit, PromptBudgetExceeded
from drama_plugin.hosts.comfy_video import NODES
import json
from pathlib import Path
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
    final, budget = check_prompt_limit(original, model='x', limit=len(original) + 10, source='test', reserved=10)
    assert final == original and budget['status'] == 'FIT'
    assert budget['effectivePromptBudget'] == len(original)
    with pytest.raises(PromptBudgetExceeded) as failure:
        check_prompt_limit(original, model='x', limit=len(original), source='test', reserved=1)
    assert failure.value.budget['status'] == 'EXCEEDED'
    assert 'model=x' in str(failure.value) and 'final_length=' in str(failure.value)



def test_overflow_never_selects_an_alternate_or_truncates():
    text = '动作和对白必须完整。' * 30
    with pytest.raises(PromptBudgetExceeded) as caught:
        check_prompt_limit(text, model='test', limit=50, source='test')
    assert caught.value.budget['finalCharacters'] == len(text)
    assert caught.value.budget['rule'] == 'unchanged'
    import drama_plugin.hosts.prompt_budget as module
    assert not hasattr(module, 'compact_prose')
    assert not hasattr(module, 'budget_prompt')
