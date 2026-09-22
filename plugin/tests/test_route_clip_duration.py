"""Saved route regression and offline seals/quotes; no generation calls."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual.video_selection import (ProductionRoute, qualify_route, same_execution_candidate,
    Requirements, seal_decision)
from drama_plugin.visual.cinematic import selection_handoff
from drama_plugin.hosts.comfy_video import verify_execution, inspect_graph
from drama_plugin.visual import production as p
from test_video_reconciliation import current_fixture, compile_all
from test_video_selection import quote
from seedance_helpers import execution_plan


def saved_route():
    return ProductionRoute.model_validate(json.loads((Path(__file__).parent /
        'fixtures/route-duration/S02-adjacent-route.json').read_text()))


def test_saved_adjacent_durations_and_scope():
    route = saved_route()
    before = route.model_dump(mode='json')
    result = qualify_route(route, now=route.generation_count_evidence.checked_at)
    assert set(result['cinematic_directions']) == {'K02', 'K03'}
    assert [r['spec']['durationSeconds'] for r in route.requirements['cinematic_directions'].values()] == [14, 16]
    assert not any('DURATION' in e for e in result['exclusions'])
    assert route.model_dump(mode='json') == before
    # Saved preflight deliberately has pending official/cost evidence.
    assert not result['eligible']
    changed = route.model_copy(deep=True)
    changed.requirements['shots']['K03'] = 'wrong-shot'
    with pytest.raises(ValueError, match='ROUTE_CINEMATIC_SCOPE_OR_DURATION_CHANGED'):
        qualify_route(changed)
    changed = route.model_copy(deep=True)
    raw = changed.requirements['cinematic_directions']['K03']
    raw['spec']['durationSeconds'] = 17
    raw['spec']['executionRequirements']['durationSeconds'] = 17
    raw['spec']['performance']['beats'][-1]['end'] = 17
    raw['fingerprint'] = fp({k: v for k, v in raw.items() if k != 'fingerprint'})
    with pytest.raises(ValueError, match='CLIP_DURATION_OUT_OF_ROUTE_CAPABILITY'):
        qualify_route(changed)


def synthetic_clip(tmp_path, duration, target):
    r, c, g, s, host = current_fixture(tmp_path, 'api_vidu_q3_text_to_video', 'viduq3-turbo')
    frozen = deepcopy(r.frozen_creative['cinematic_direction'])
    frozen['spec']['durationSeconds'] = duration
    frozen['spec']['executionRequirements']['durationSeconds'] = duration
    frozen['spec']['performance']['beats'][-1]['end'] = duration
    frozen['fingerprint'] = fp({k: v for k, v in frozen.items() if k != 'fingerprint'})
    r = Requirements.model_validate({**r.model_dump(), 'target_id': target, 'duration_seconds': duration,
                                    'frozen_creative': selection_handoff(frozen)})
    c.parameters['model.duration'] = duration
    return r, c, g, s, host


def test_same_route_seals_exact_durations_and_rejects_reused_quote(tmp_path, monkeypatch):
    first_dir = tmp_path / 'first'; first_dir.mkdir()
    second_dir = tmp_path / 'second'; second_dir.mkdir()
    clips = [synthetic_clip(first_dir, 14, 'K02'), synthetic_clip(second_dir, 16, 'K03')]
    r, c, *_ = clips[0]
    clips[1][1].capability.clear()
    clips[1][1].capability.update(deepcopy(c.capability))
    route = execution_plan(r, c).model_copy(update={'video_targets': ('K02', 'K03')})
    route.requirements['cinematic_directions']['K03'] = clips[1][0].frozen_creative['cinematic_direction']
    route.requirements['shots']['K03'] = clips[1][0].shot_id
    route.candidate.cost.components.update({'video': 300, 'audio': 0, 'references': 0, 'addons': 0, 'correction': 0})
    assert qualify_route(route)['eligible']
    sealed = []
    for r, c, g, s, host in clips:
        request = compile_all(r, c, g, s, host)
        assert request['input_overrides'][inspect_graph(g, s)['model_node']]['model.duration'] == r.duration_seconds
        d = seal_decision(r, c, request, stage_id='OFFLINE', rationale='OFFLINE duration test',
                         comparisons=[], fallback='stop', host_adapter=host, production_route=route)
        verify_execution(d)
        sealed.append(d)
    assert sealed[0]['route_fingerprint'] == sealed[1]['route_fingerprint']
    assert [d['requirements']['duration_seconds'] for d in sealed] == [14, 16]
    monkeypatch.setattr(p, 'video_verifier', verify_execution)
    state = p.new_stage(stage_id='OFFLINE', authorization_ref='OFFLINE 2000 credits', budget_credits=2000,
                        frames=[], protected_targets=[], production_route=route.model_dump(mode='json'))
    # Explicit synthetic prior review to exercise the existing adjacent-clip gate.
    state['attempts'] = [{'media_kind': 'VIDEO', 'shot_id': 'K02', 'review_status': 'PASS',
        'status': 'COMPLETED', 'credits': 140, 'reserved_credits': 140}]
    quotes = [quote(d, amount=d['requirements']['duration_seconds'] * 10) for d in sealed]
    for d, q in zip(sealed, quotes):
        assert p._stage_gate(state, d, d['request'], q['quote'], q['balance']) == d['requirements']['duration_seconds'] * 10
    with pytest.raises(ValueError, match='REQUEST_QUOTE_MISMATCH'):
        p._stage_gate(state, sealed[1], sealed[1]['request'], quotes[0]['quote'], quotes[0]['balance'])
    state['stage']['budget_credits'] = 299
    with pytest.raises(ValueError, match='BUDGET'):
        p._stage_gate(state, sealed[1], sealed[1]['request'], quotes[1]['quote'], quotes[1]['balance'])


def test_other_route_parameters_remain_immutable():
    planned = saved_route().candidate
    actual = planned.model_copy(deep=True)
    actual.parameters['model.duration'] = 16.0
    assert same_execution_candidate(planned, actual)
    actual.parameters['model.duration'] = 17
    assert not same_execution_candidate(planned, actual)
    actual.parameters['model.duration'] = 16
    actual.parameters['model.resolution'] = '1080p'
    assert not same_execution_candidate(planned, actual)
