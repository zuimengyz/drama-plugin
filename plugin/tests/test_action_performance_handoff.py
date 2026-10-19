"""B1: formal DTO -> selected unit -> final wire, using DESIGN_FIXTURE_ONLY inputs.

These tests prove structural compatibility and delivery, not an author's creative
judgment or the physical correctness of a generated film.
"""
from copy import deepcopy
import hashlib
import json
import socket

import httpx
import pytest

from drama_plugin.creative_engine.author_projection import professional_schema, professional_projection
from drama_plugin.creative_engine.backends import PROFESSIONAL_CRAFT
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure
from test_event_scope_delivery import material, pipeline
from test_formal_author_backends import configured


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('B1 handoff tests cannot call an author or media service')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)


def structure(value):
    if isinstance(value, dict):
        return {key: structure(child) for key, child in value.items() if key not in {'description', 'title'}}
    if isinstance(value, list):
        return [structure(child) for child in value]
    return value


def shared_beat_material(*, renamed=False):
    req, raw = material()
    action = raw[0]['facts']['actionPhases']
    action[0].update(beatSelection=1,
        action='The courier establishes the receiving grip before lifting; meanwhile the keeper approaches the free side.',
        observable='The grip carries the packet; the courier has not started walking.')
    action[1].update(
        entryState=action[0]['observable'],
        action='The courier walks and speaks while the keeper yields; the keeper waits, the courier continues past.',
        observable='Once the packet and carrier clear the shared path, the keeper resumes; no second lift.')
    raw[1]['facts']['beats'][1]['physicalExpression'] = 'The courier keeps attention on the occupied working space.'
    raw[1]['facts']['beats'][2]['physicalExpression'] = 'PARTNER_WHOLE_BEAT: approach, yield, then resume.'
    raw[2]['facts']['movement'] = {'policy': 'Fixed view of the counter and shared path.'}
    raw[5]['facts']['contactTiedSound'] = [
        {'phaseIndex': 0, 'design': 'Grip contact belongs to the support transfer.'},
        {'phaseIndex': 1, 'design': 'The carrier footsteps continue while the waiting person is still.'}]
    raw[5]['facts']['audio_events'][0].update(
        performance='Speak once during passage.', continuity='Keep the receiving opportunity without another transfer.')
    raw[6]['facts']['protectedEvents'] = [
        {'phaseIndex': 0, 'design': 'End when the receiving support is established.'},
        {'phaseIndex': 1, 'design': 'End after clearance permits the keeper to resume.'}]
    if renamed:
        def rename(text):
            return text.replace('courier', 'porter').replace('Courier', 'Porter').replace(
                'keeper', 'clerk').replace('Keeper', 'Clerk').replace('packet', 'tray')
        raw = json.loads(rename(json.dumps(raw)))
        req = type(req).model_validate_json(rename(req.model_dump_json()))
    return req, raw


def test_contract_shape_stays_at_accepted_b8c50c9_baseline():
    # Captured before B1: descriptions can clarify ownership but must not alter
    # accepted fields, enum choices, required keys or validation constraints.
    fingerprint = hashlib.sha256(json.dumps(structure(professional_schema()),
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert fingerprint == '479f8f12c61c38dc880600d0761fb1218b7fffa08248cf027449cc0f29484b37'


@pytest.mark.parametrize('renamed', [False, True])
async def test_shared_beat_keeps_current_action_and_parallel_partner_in_final_wire(tmp_path, monkeypatch, renamed):
    req, raw = shared_beat_material(renamed=renamed)
    p, _, _, outputs = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        phases = raw[0]['facts']['actionPhases']
        common = raw[1]['facts']['beats'][1]['physicalExpression']
        for index, output in enumerate(outputs):
            text = output['wire']['content'][0]['text']
            assert phases[index]['action'] in text
            assert phases[1-index]['action'] not in text
            assert common.rstrip('.') in text
            assert 'PARTNER_WHOLE_BEAT' not in text
            assert 'PERSISTENT_WIND' in text
            assert not output['ready'].provider_submission_allowed
        assert outputs[0]['task'].unit.beat_ids == outputs[1]['task'].unit.beat_ids
        assert outputs[0]['task'].unit.end_ref != outputs[1]['task'].unit.end_ref
        assert '{Помогите.}' not in outputs[0]['wire']['content'][0]['text']
        assert outputs[1]['wire']['content'][0]['text'].count('{Помогите.}') == 1
        # No consumer silently edits a shared Beat to synthesize stage-local art.
        assert raw[1]['facts']['beats'][2]['physicalExpression'].startswith('PARTNER_WHOLE_BEAT')
    finally:
        await p.aclose()


async def test_known_bad_shared_expression_is_retained_as_author_failure_not_compiler_repair(tmp_path, monkeypatch):
    req, raw = shared_beat_material()
    bad = 'ALREADY_WALKING: the carrier is walking with the packet throughout preparation.'
    raw[1]['facts']['beats'][1]['physicalExpression'] = bad
    p, _, _, outputs = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        # Expected negative design: both clauses survive, so review can identify
        # the source contradiction. Passing this test does NOT pass this design.
        text = outputs[0]['wire']['content'][0]['text']
        assert bad.rstrip('.') in text and raw[0]['facts']['actionPhases'][0]['observable'] in text
    finally:
        await p.aclose()


async def test_formal_author_loads_methods_and_field_authority_in_actual_wire(tmp_path, monkeypatch):
    req, raw = shared_beat_material()
    p = configured(monkeypatch, tmp_path)
    author = p.professional_design.author
    calls = []
    def receive(wire):
        payload = json.loads(wire.content)
        calls.append(payload)
        system, encoded_schema = payload['messages'][0]['content'].split('\nOutput JSON schema:\n', 1)
        assert json.loads(encoded_schema) == professional_schema()
        for domain in req.shot.professional_domains:
            for name in PROFESSIONAL_CRAFT[domain]:
                assert (author.skills_root / name).read_text() in system
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'role': 'assistant', 'content': json.dumps(raw)}}]})
    author.client.transport = httpx.MockTransport(receive)
    before = deepcopy(raw)
    try:
        designs = await author.design(req)
        assert len(calls) == 1
        assert [d.model_dump(mode='json', by_alias=True) for d in designs] == professional_projection(raw, req)
        assert raw == before
    finally:
        await p.aclose()


@pytest.mark.parametrize('fault', ['top-expression', 'beat-phase', 'beat-time'])
def test_stage_scope_does_not_open_new_performance_fields(fault):
    req, raw = shared_beat_material()
    facts = raw[1]['facts']
    if fault == 'top-expression':
        facts['physicalExpression'] = 'A new execution lane'
    else:
        facts['beats'][1]['phaseIndex' if fault == 'beat-phase' else 'window_ms'] = 0
    with pytest.raises(AuthorResultFailure):
        professional_projection(raw, req)


@pytest.mark.parametrize('action,expression', [
    ('The courier makes a brisk full-arm push while keeping the hand fixed in handle space; the tool slides on the counter.',
     'Controlled effort remains decisive at full amplitude.'),
    ('The courier deliberately releases the packet into free flight toward the keeper.',
     'The release is intentional; receiving support begins at the catch.'),
    ('The courier waits with hands resting on the counter and listens without adding a gesture.',
     'Stillness sustains attention to the keeper.'),
])
async def test_contextual_action_choices_survive_final_wire(tmp_path, monkeypatch, action, expression):
    # Delivery coverage, not evidence that a model or actor performs these well.
    req, raw = shared_beat_material()
    raw[0]['facts']['actionPhases'][0]['action'] = action
    raw[1]['facts']['beats'][1]['physicalExpression'] = expression
    p, _, _, outputs = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        text = outputs[0]['wire']['content'][0]['text']
        assert action in text
        assert expression.rstrip('.') in text
        assert not outputs[0]['ready'].provider_submission_allowed
    finally:
        await p.aclose()
