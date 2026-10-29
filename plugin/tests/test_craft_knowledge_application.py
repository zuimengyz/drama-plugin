"""Real local readings + native handoff; no claim of autonomous art or generated AV."""
import importlib.util
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from drama_plugin.creative_engine.craft_knowledge import discover, reading, author_reading, _read

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / 'knowledge'
EVIDENCE = KNOWLEDGE / 'ai-production-evidence/v6-01-04'


def test_expression_can_find_fixed_and_moving_without_naming_a_technique():
    result = discover(KNOWLEDGE, query='希望观众逐渐发现门外发生的事情', limit=16)
    assert result['expandedGoals'] == ['reveal']
    ids = {row['id'] for row in result['cases']}
    assert {'playtime', 'children-of-men'} <= ids
    assert discover(KNOWLEDGE, query='nonexistent-specific-expression')['cases'] == []
    filtered = discover(KNOWLEDGE, styles=('poetic-cinema',), disciplines=('LIGHTING',), limit=16)
    assert filtered['cases']
    assert all('poetic-cinema' in r['styles'] and 'LIGHTING' in r['disciplines'] for r in filtered['cases'])
    with pytest.raises(ValueError, match='Unknown means'):
        discover(KNOWLEDGE, means=('must-dolly',))


def test_author_reading_is_opt_in_full_body_and_path_confined(tmp_path):
    assert author_reading(ROOT/'skills', SimpleNamespace()) == ''
    selection = {'caseIds':['children-of-men'], 'techniqueIds':['lighting-placement']}
    loaded = reading(KNOWLEDGE, selection)
    context = SimpleNamespace(professional_context={'authorContext':{'craftKnowledge':selection}})
    delivered = author_reading(ROOT/'skills', context)
    for row in loaded['readings']:
        assert json.dumps(row['text'], ensure_ascii=False) in delivered
        assert row['sha256'] in delivered
    assert '无缝接点' in delivered and '负补光' in delivered
    with pytest.raises(ValueError, match='leaves its root'):
        _read(tmp_path, '../outside.txt')
    with pytest.raises(ValueError, match='Unknown cases'):
        reading(KNOWLEDGE, {'caseIds':['missing-film']})


def test_catalog_metadata_and_shared_methods_have_no_dangling_facets():
    taxonomy = json.loads((KNOWLEDGE/'cinema-styles/taxonomy.json').read_text())
    for row in json.loads((KNOWLEDGE/'film-craft/index.json').read_text())['cases']:
        for key in ('styles','goals','means','disciplines'):
            assert set(row[key]) <= set(taxonomy[key])
        loaded = reading(KNOWLEDGE, {'caseIds':[row['id']]})
        assert loaded['readings'] and all(r['text'].strip() for r in loaded['readings'])


def test_expressive_storyboard_method_reaches_existing_author_contexts():
    # A method can be selected without treating an open-source workflow as a film case.
    selection = {'query': 'clipshot-method-only-no-film-match',
                 'techniqueIds': ['expressive-storyboarding']}
    loaded = reading(KNOWLEDGE, selection)
    assert loaded['cases'] == []
    assert [r['id'] for r in loaded['readings']] == ['expressive-storyboarding']
    method = loaded['readings'][0]
    delivered = [
        author_reading(ROOT/'skills', packet={'authorContext': {'craftKnowledge': selection}}),
        author_reading(ROOT/'skills', SimpleNamespace(
            professional_context={'authorContext': {'craftKnowledge': selection}})),
    ]
    for context in delivered:
        assert json.dumps(method['text'], ensure_ascii=False) in context
        assert method['sha256'] in context
    assert author_reading(ROOT/'skills', packet={'authorContext': {}}) == ''


@pytest.mark.asyncio
@pytest.mark.parametrize('name', ['fixed','moving'])
async def test_retained_application_reaches_actual_author_port_and_native_prompt(name, monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('Offline craft replay must never call a model or provider')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)
    spec = importlib.util.spec_from_file_location('craft_application_replay', EVIDENCE/'replay.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = await module.replay(name)
    assert result['modelCalls'] == result['mediaCalls'] == 0
    calls = result['authorCalls']
    assert [c['role'] for c in calls] == ['direction', 'professional']
    assert all(c['hasFullReading'] and len(c['loadedBodyHashes']) == 9 for c in calls)
    prompt = result['compiled']['prompt']
    for domain, fields in {'CAMERA':('cameraPosition','height','lensIntention'),
                           'LIGHTING':('directionAndQuality','intensityRatios','constraints')}.items():
        for field in fields:
            assert result['records'][domain]['content'][field] in prompt
    camera = result['records']['CAMERA']['content']
    assert camera['movement']['policy'] in prompt
    assert all(source in prompt for source in result['records']['LIGHTING']['content']['sources'])
    assert camera['continuityInterpretation'] not in prompt
    assert all(name not in prompt for name in ('Playtime','Children of Men','Barry Lyndon','https://','sha256'))
    assert '吻手发生后看一眼' in prompt
    assert result['compiled']['statistics']['uncovered_required'] == 0
    assert not result['compiled']['input_slots']  # No asset adoption or input delivery was tested.
