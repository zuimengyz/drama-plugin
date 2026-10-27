"""Mechanical text-contract tests, not creative or media validation."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_problem_lookup_returns_sources_without_a_template_or_score():
    path = ROOT / 'knowledge/film-craft/find_cases.py'
    spec = importlib.util.spec_from_file_location('film_cases', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = module.find_cases(problems=('public-life',), limit=3)
    assert [r['id'] for r in rows] == ['fanny-alexander', 'leopard', 'rules-game']
    assert module.find_cases(query='no such narrative question') == []
    with pytest.raises(ValueError, match='Unknown tags'):
        module.find_cases(problems=('invented-tag',))
    index = json.loads((path.parent / 'index.json').read_text())
    for row in index['cases']:
        assert (path.parent / row['path']).is_file()
        assert row['sources'] and all(s['url'].startswith('https://') for s in row['sources'])
        assert 'score' not in row and 'prompt' not in row


@pytest.mark.parametrize('authored_time', [
    'This is his present inner thought, at the same age as the visible person.',
    'The adult narrator recalls his childhood; the voice belongs to that later time.',
])
def test_voice_over_retains_authored_time_without_inventing_another_age(authored_time):
    from copy import deepcopy
    from drama_plugin.contracts.base import sha256_canonical as fp
    from drama_plugin.prompt_generators.contracts import ProjectionAnnotations
    from drama_plugin.visual.video_prompt import compile_request_ir
    from test_seedance_prompt_generator import audio_sample, rebound
    from test_visual_prompt_ir import fact

    request = audio_sample()
    ir = deepcopy(request.prompt_ir)
    ir['video_temporal']['performance'].append(fact(authored_time, scope='CLIP'))
    binding = request.prompt_projection.audio[0].model_copy(update={'kind': 'VOICE_OVER'})
    request = rebound(request.model_copy(update={'prompt_ir': ir}),
        prompt_projection=ProjectionAnnotations(audio=(binding,)))
    text = compile_request_ir(request)['prompt']
    assert authored_time in text
    assert '独立于画面人物的当前年龄' not in text
    assert '不作画内发声或对口型' in text
    assert text.count('螭龙山，我从未答应过你。') == 1
    assert binding.text_hash == fp('螭龙山，我从未答应过你。')
