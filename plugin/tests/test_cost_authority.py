"""Offline cost authority evidence; never a deployment billing declaration."""
from copy import deepcopy
import json

import pytest

from drama_plugin.visual.video_selection import Cost, ProductionRoute, qualify_route, Candidate, Requirements, seal_decision, verify_decision
from drama_plugin.visual import production as p
from test_production_route import route
from test_video_selection import evidence, decision, quote


def classified(raw):
    raw = deepcopy(raw)
    raw['components'].update(runtime=None, storage=None)
    raw['resolutions'] = {k: {'authority': 'PROVIDER_QUOTE' if k == 'video' else 'INTERNAL_FIXED',
        'evidence': {**evidence(), 'source': 'OFFLINE quote' if k == 'video' else 'OFFLINE formal fixed policy'}}
        for k in raw['components']}
    for k in ('runtime', 'storage'):
        raw['resolutions'][k] = {'authority': 'INTERNAL_UNMETERED',
            'evidence': {**evidence(), 'source': 'OFFLINE verified self-managed deployment no incremental billing policy'}}
    return raw


def test_resolved_internal_authorities_and_provider_quote_integrity(tmp_path):
    raw = route(tmp_path).model_dump(mode='json')
    original_provider_amount = raw['candidate']['cost']['components']['video']
    raw['candidate']['cost'] = classified(raw['candidate']['cost'])
    r = ProductionRoute.model_validate(raw)
    result = qualify_route(r)
    assert result['eligible']
    assert result['cost_resolution']['resolved']
    assert result['cost_resolution']['provider_quoted_components'] == {'video': original_provider_amount}
    assert result['cost_resolution']['unmetered_components'] == ['runtime', 'storage']
    serialized = json.loads(r.model_dump_json())['candidate']['cost']
    assert serialized['components']['runtime'] is None
    assert serialized['components']['storage'] is None
    assert serialized['resolutions']['storage']['authority'] == 'INTERNAL_UNMETERED'
    assert r.candidate.cost.total() == sum(v for v in serialized['components'].values() if v is not None)


@pytest.mark.parametrize('fault', ['external', 'unverified', 'expired', 'missing', 'missing_component'])
def test_unresolved_cost_still_blocks(tmp_path, fault):
    raw = route(tmp_path).model_dump(mode='json')
    cost = classified(raw['candidate']['cost'])
    if fault == 'external':
        cost['resolutions']['storage']['authority'] = 'EXTERNAL_METERED_UNKNOWN'
        cost['components']['storage'] = 0  # Cannot launder unknown into zero.
    elif fault == 'unverified':
        cost['resolutions']['storage']['evidence']['verified'] = False
    elif fault == 'expired':
        cost['resolutions']['storage']['evidence']['expires_at'] = '2000-01-01T00:00:00Z'
    elif fault == 'missing':
        del cost['resolutions']['storage']
    else:
        del cost['resolutions']['storage']; del cost['components']['storage']
    raw['candidate']['cost'] = cost
    assert 'COMPLETE_ROUTE_COST_UNRESOLVED' in qualify_route(ProductionRoute.model_validate(raw))['exclusions']


def test_unmetered_cannot_be_serialized_as_zero_amount(tmp_path):
    raw = classified(route(tmp_path).candidate.cost.model_dump(mode='json'))
    raw['components']['storage'] = 0
    with pytest.raises(ValueError, match='UNMETERED_COST_MUST_NOT_HAVE_AMOUNT'):
        Cost.model_validate(raw).total()


def test_reservation_covers_internal_cost_and_budget(tmp_path):
    d = decision(tmp_path)
    candidate = {**d['candidate'], 'cost': classified(d['candidate']['cost'])}
    d = seal_decision(Requirements.model_validate(d['requirements']), Candidate.model_validate(candidate),
        d['request'], stage_id='v206', rationale='OFFLINE authority seal', comparisons=[], fallback='stop')
    verify_decision(d)
    assert d['candidate']['cost']['components']['storage'] is None
    assert d['candidate']['cost']['components']['video'] == 100
    # Candidate costs are per-call here: 100 provider + 100 internal fixed.
    state = {'stage': {'id': 'v206', 'budget_credits': 2000, 'protected_targets': []}, 'attempts': []}
    q = quote(d, amount=200)
    assert p._stage_gate(state, d, d['request'], q['quote'], q['balance']) == 200
    q['quote']['conservative_credits'] = 100
    with pytest.raises(ValueError, match='RESERVATION_MUST_COVER_RESOLVED_COST'):
        p._stage_gate(state, d, d['request'], q['quote'], q['balance'])
    q['quote']['conservative_credits'] = 200
    state['attempts'] = [{'credits': 1900, 'reserved_credits': 1900, 'status': 'COMPLETED'}]
    with pytest.raises(ValueError, match='BUDGET'):
        p._stage_gate(state, d, d['request'], q['quote'], q['balance'])
