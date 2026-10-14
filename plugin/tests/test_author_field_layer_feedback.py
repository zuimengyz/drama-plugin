"""Wrong-layer schema names stay rejected and reach safe author correction."""
from copy import deepcopy
import json

import httpx
import pytest

from author_model_helpers import model_dto
from drama_plugin.creative_engine.author_projection import professional_projection
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure, structural_feedback
from test_formal_author_backends import configured
from test_partner_coverage_diagnostics import performance_request
from test_unified_author_recovery import performance_fixture


def model_output():
    facts = performance_fixture()
    facts['sceneDPD']['socialConstraints'] = ['A stranger waits outside.']
    facts['sceneDPD']['direction']['performanceBoundaries'] = ['No invented answer.']
    return model_dto([{'domain': 'PERFORMANCE', 'facts': facts}])


@pytest.mark.parametrize('key,expected', [
    ('socialConstraints', 'socialConstraints'),
    ('PRIVATE_UNTRUSTED_KEY', '<extra>'),
    ('sourceFingerprint', 'sourceFingerprint'),
])
def test_wrong_layer_or_owned_fields_reject_without_echoing_values(key, expected):
    raw = model_output()
    raw[0]['facts']['sceneDPD']['direction'][key] = ['PRIVATE_UNTRUSTED_VALUE']
    before = deepcopy(raw)
    req = performance_request(); authority = req.model_dump_json()
    with pytest.raises(AuthorResultFailure) as caught:
        professional_projection(raw, req)
    diagnostic = caught.value.diagnostic
    assert diagnostic.code == 'AUTHOR_SYSTEM_FIELD_FORBIDDEN'
    prefix = ('facts',) if key == 'sourceFingerprint' else ()
    assert diagnostic.issues[0].field_path == (*prefix, 'sceneDPD', 'direction', expected)
    assert 'PRIVATE_UNTRUSTED' not in diagnostic.model_dump_json()
    assert raw == before and req.model_dump_json() == authority


async def test_precise_rejected_layer_reaches_formal_wire_and_valid_layers_survive(monkeypatch, tmp_path):
    p = configured(monkeypatch, tmp_path)
    req = performance_request(); before = req.model_dump_json()
    valid = model_output(); invalid = deepcopy(valid)
    scene = invalid[0]['facts']['sceneDPD']
    scene['direction']['socialConstraints'] = scene.pop('socialConstraints')
    scene['direction']['socialConstraints'] = ['PRIVATE_PRIOR_VALUE']
    wire = []
    def receive(request):
        wire.append(json.loads(request.content))
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': json.dumps(invalid if len(wire) == 1 else valid)}}]})
    p.professional_design.author.client.transport = httpx.MockTransport(receive)
    with pytest.raises(AuthorResultFailure) as caught:
        await p.professional_design.design(req)
    assert len(wire) == 1  # No implicit nested retry or semantic repair.
    token = structural_feedback.set(caught.value.diagnostic)
    try:
        result = await p.professional_design.design(req)
    finally:
        structural_feedback.reset(token)
        await p.aclose()
    feedback = wire[1]['messages'][2]['content']
    assert 'socialConstraints' in feedback and 'direction' in feedback
    assert 'PRIVATE_PRIOR_VALUE' not in feedback
    scene = result[0].facts['sceneDPD']
    assert scene['socialConstraints'] == valid[0]['facts']['sceneDPD']['socialConstraints']
    assert scene['direction']['performanceBoundaries'] == ['No invented answer.']
    assert 'socialConstraints' not in scene['direction']
    assert req.model_dump_json() == before
