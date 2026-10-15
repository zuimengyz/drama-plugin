"""B2 pure-text scope proofs. Deterministic fixtures, never real author/media evidence."""
from copy import deepcopy
import json
import socket
import subprocess

import pytest

from drama_plugin.creative_engine.author_projection import professional_candidate_view, professional_projection
from drama_plugin.creative_engine.contracts import Dialogue
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure
from drama_plugin.execution.live_transport import TargetHttpTransport
from drama_plugin.generation.contracts import GenerationPreparation, FinalPromptArtifact
from test_event_scope_delivery import material, pipeline


@pytest.fixture(autouse=True)
def text_only(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('B2 forbids network, subprocesses and media fixtures')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)
    monkeypatch.setattr(subprocess, 'Popen', deny)


def utterance_material():
    req, raw = material(single=True)
    scene = req.canon.scene.model_copy(update={'dialogue': (*req.canon.scene.dialogue,
        Dialogue(id='reply', speaker='keeper', text='Я слушаю.'))})
    req = req.model_copy(update={'canon': req.canon.model_copy(update={'scene': scene}),
        'shot': req.shot.model_copy(update={'spoken_ids': ('call', 'reply')})})
    f = {row['domain']: row['facts'] for row in raw}
    f['ACTION']['actionPhases'][0].update(spokenSelections=[0, 1],
        entryState='Both remain at the counter; the keeper already holds the packet.',
        action='The selected speaker addresses the partner while the keeper retains support.',
        observable='The packet remains supported; there is no second handoff.')
    f['PERFORMANCE']['beats'][1]['physicalExpression'] = 'The courier attends to the partner without a repeated gesture.'
    f['PERFORMANCE']['lines'][0].update(dramaticAction='Address on-screen.', observableIntent='Speak to the partner.')
    f['PERFORMANCE']['lines'].append({'spokenSelection': 1, 'beatSelection': 2,
        'dramaticAction': 'Answer on-screen.', 'observableIntent': 'Let the partner be heard.',
        'continuity': 'The packet remains supported.', 'changeFromPrevious': 'Answer without another handoff.'})
    f['CAMERA']['movement'] = {'policy': 'HOLD: a steady two-person view for both utterances.'}
    f['SOUND']['audio_events'] = [
        {'spokenSelection': 0, 'delivery_mode': 'ON_SCREEN', 'performance': 'FIRST_DELIVERY: address once.'},
        {'spokenSelection': 1, 'delivery_mode': 'ON_SCREEN', 'performance': 'SECOND_DELIVERY: answer once.'}]
    f['SOUND']['speechRelations'] = [{'spokenSelection': 1, 'targetSpokenSelection': 0, 'relation': 'AFTER'}]
    f['SOUND']['contactTiedSound'] = [
        {'phaseIndex': 0, 'spokenSelections': [0], 'design': 'FIRST_CONTACT: a brief offscreen cloth contact under the appeal.'},
        {'phaseIndex': 0, 'spokenSelections': [1], 'design': 'SECOND_CONTACT: a light sleeve contact during the answer.'},
        {'phaseIndex': 0, 'spokenSelections': [0, 1], 'design': 'SHARED_APPROVED_CONTACT: a sustained offscreen rustle throughout both utterances.'}]
    f['EDITORIAL']['temporalStructure'] = 'The speakers attend to one another without resetting support.'
    f['EDITORIAL']['protectedEvents'] = [
        {'phaseIndex': 0, 'spokenSelections': [0], 'design': 'FIRST_HOLD: allow the appeal to be received.'},
        {'phaseIndex': 0, 'spokenSelections': [1], 'design': 'SECOND_HOLD: allow the answer to settle.'}]
    return req, raw


async def selected_wire(compiler, package, base, *, spoken_range):
    unit = await compiler.reader.operations.select_unit(package, compiler.reader,
        phase_index=0, spoken_range=spoken_range)
    task = base['task'].model_copy(update={'unit': unit})
    result = await compiler.compile(package.artifact_reference(), task)
    assert result.preparation_ref, compiler.artifacts.diagnostics(result.diagnostics_ref)
    ready = compiler.artifacts.get(result.preparation_ref, GenerationPreparation)
    final = compiler.artifacts.get(ready.final_prompt_ref, FinalPromptArtifact)
    wire = json.loads(json.dumps(TargetHttpTransport.preview(ready, final,
        ledger=compiler.reader.operations.ledger)))
    assert wire['content'][0]['text'] == final.prompt_text
    assert not ready.provider_submission_allowed
    return {'task': task, 'ready': ready, 'final': final, 'wire': wire}


def test_nested_existing_utterance_selections_bind_and_roundtrip_without_prose_changes():
    req, raw = utterance_material()
    before = deepcopy(raw)
    projected = professional_projection(raw, req)
    f = {r['domain']: r['facts'] for r in projected}
    assert f['SOUND']['contactTiedSound'][0].get('spokenIds') == ['call']
    assert f['EDITORIAL']['protectedEvents'][1].get('spokenIds') == ['reply']
    assert 'spokenSelections' not in f['SOUND']['contactTiedSound'][0]
    assert professional_candidate_view(projected, req) == raw
    assert raw == before


async def test_same_action_beat_spoken_range_reaches_only_current_final_prompt(tmp_path, monkeypatch):
    req, raw = utterance_material()
    p, compiler, package, out = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        rows = [await selected_wire(compiler, package, out[0], spoken_range=(i, i+1)) for i in (0, 1)]
        assert rows[0]['task'].unit.beat_ids == rows[1]['task'].unit.beat_ids
        assert rows[0]['task'].unit.action_refs == rows[1]['task'].unit.action_refs
        for i, row in enumerate(rows):
            text = row['wire']['content'][0]['text']
            current, other = ('FIRST', 'SECOND') if i == 0 else ('SECOND', 'FIRST')
            for suffix in ('CONTACT', 'HOLD', 'DELIVERY'):
                assert current+'_'+suffix in text
                assert other+'_'+suffix not in text
            assert text.count('SHARED_APPROVED_CONTACT') == 1
            assert text.count('PERSISTENT_WIND') == 1
            assert 'Courier' in text and 'Keeper' in text
            words = ('Помогите.', 'Я слушаю.')
            assert text.count('{'+words[i]+'}') == 1
            assert words[1-i] not in text
            assert 'spokenSelections' not in text and 'spokenIds' not in text
    finally:
        await p.aclose()


@pytest.mark.parametrize('selection', [[99], [-1], [True], ['call']])
def test_nested_scope_does_not_relax_authority(selection):
    req, raw = utterance_material()
    raw[5]['facts']['contactTiedSound'][0]['spokenSelections'] = selection
    with pytest.raises(AuthorResultFailure):
        professional_projection(raw, req)


def test_unresolved_historical_scope_is_preserved_not_guessed():
    req, raw = utterance_material()
    projected = professional_projection(raw, req)
    sound = next(r['facts'] for r in projected if r['domain'] == 'SOUND')
    sound['contactTiedSound'][0].pop('spokenSelections', None)
    sound['contactTiedSound'][0]['spokenIds'] = ['unresolved-historical-id']
    candidate = professional_candidate_view(projected, req)
    row = next(r['facts'] for r in candidate if r['domain'] == 'SOUND')['contactTiedSound'][0]
    assert row['spokenIds'] == ['unresolved-historical-id']
    assert 'spokenSelections' not in row
    with pytest.raises(AuthorResultFailure):
        professional_projection(candidate, req)


@pytest.mark.parametrize('fault', ['audio-text', 'ordering-object', 'temporal-object', 'internal-id'])
def test_event_scope_fix_does_not_widen_formal_contract(fault):
    req, raw = utterance_material()
    if fault == 'audio-text':
        raw[5]['facts']['audio_events'][0]['text'] = 'Rewritten dialogue is forbidden.'
    elif fault == 'ordering-object':
        raw[5]['facts']['orderingRules'] = [{'phaseIndex': 0, 'design': 'New typed timing lane'}]
    elif fault == 'temporal-object':
        raw[6]['facts']['temporalStructure'] = {'phaseIndex': 0, 'design': 'New typed timeline'}
    else:
        raw[5]['facts']['contactTiedSound'][0]['spokenIds'] = ['call']
    with pytest.raises(AuthorResultFailure):
        professional_projection(raw, req)


def test_empty_and_nested_event_scopes_roundtrip_without_touching_other_fields():
    req, raw = utterance_material()
    sound = raw[5]['facts']
    sound['contactTiedSound'] = {'design': 'Shared event context', 'parts': [
        {'spokenSelections': [], 'design': 'Explicitly shared contact'},
        {'spokenSelections': [1], 'design': 'Current utterance contact'}]}
    projected = professional_projection(raw, req)
    f = {r['domain']: r['facts'] for r in projected}
    assert f['SOUND']['contactTiedSound']['parts'][0]['spokenIds'] == []
    assert f['SOUND']['contactTiedSound']['parts'][1]['spokenIds'] == ['reply']
    assert professional_candidate_view(projected, req) == raw
    # Empty applicability remains the existing shared meaning; no invented gate.
    assert f['SOUND']['ambience'] == sound['ambience']


async def test_opaque_old_sequence_remains_negative_design_evidence(tmp_path, monkeypatch):
    req, raw = utterance_material()
    bad = 'UNSCOPED_OLD_SEQUENCE: lift, speak, then put down the packet.'
    raw[0]['facts']['actionPhases'][0]['action'] = bad
    p, compiler, package, out = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        for i in (0, 1):
            row = await selected_wire(compiler, package, out[0], spoken_range=(i, i+1))
            # Passing this assertion preserves a known bad original. It does not
            # pass that design or let the Compiler guess a missing event boundary.
            assert bad in row['wire']['content'][0]['text']
    finally:
        await p.aclose()


@pytest.mark.parametrize('boundary', ['cut', 'match', 'continuous'])
async def test_authored_boundary_and_motivated_axis_crossing_survive(tmp_path, monkeypatch, boundary):
    req, raw = material()
    raw[0]['facts']['actionPhases'][1]['transition'] = boundary
    raw[2]['facts']['axisAndScreenDirection'] = 'The motivated visible crossing keeps the doorway readable; do not mirror the set.'
    raw[6]['facts']['spatialOrientation'] = 'The doorway remains the orientation landmark.'
    p, _, _, out = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        first, second = [r['wire']['content'][0]['text'] for r in out]
        assert 'NEW SHOT START' not in first
        if boundary == 'continuous':
            assert out[1]['task'].unit.execution_context.boundary == 'CONTINUE'
            assert 'NEW SHOT START' not in second
        else:
            assert 'NEW SHOT START after a '+boundary.upper() in second
        assert 'motivated visible crossing' in second
        assert '2–8s: hold the resulting view' in second
        assert 'WHOLE_CAMERA_POLICY' not in second
    finally:
        await p.aclose()


async def test_scoped_sound_keeps_prelap_offscreen_and_layer_specific_silence(tmp_path, monkeypatch):
    req, raw = material()
    sound = raw[5]['facts']
    sound['contactTiedSound'] += [
        {'phaseIndex': 0, 'design': 'APPROVED_PRELAP: an offscreen cloth contact is heard before its source enters the view.'},
        {'phaseIndex': 1, 'design': 'SUBJECTIVE_HEARING: retain the rain at the listener position under the current contact.'}]
    sound['silence'] = 'Withhold score only; the room and wind continue through the pause.'
    p, _, _, out = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        for i, row in enumerate(out):
            text = row['wire']['content'][0]['text']
            assert ('APPROVED_PRELAP' in text) == (i == 0)
            assert ('SUBJECTIVE_HEARING' in text) == (i == 1)
            assert 'Withhold score only' in text and 'PERSISTENT_WIND' in text
            assert ('receiving grip; no second impact' in text) == (i == 1)
    finally:
        await p.aclose()
