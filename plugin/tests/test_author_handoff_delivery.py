"""F3-F5 formal originals -> current projection -> exact Seedance JSON.

All scenes and text responses are controlled contract examples. They test
authorship boundaries and delivery; they are not real author creativity or AV
quality evidence. No movie originals, paid model or media provider is used.
"""
import json
from pathlib import Path
import socket

import httpx
import pytest

from drama_plugin.creative_engine.author_projection import professional_projection
from drama_plugin.creative_engine.backends import FormalProfessionalAuthor, professional_model_schema
from drama_plugin.creative_engine.contracts import DesignBody, Kind
from drama_plugin.professional_design.provenance import creative_facts
from test_event_scope_delivery import material, pipeline
from test_formal_author_backends import configured


@pytest.fixture(autouse=True)
def offline_handoff(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Author-handoff verification forbids external network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket.socket, 'connect_ex', denied)


WAIT = '说完先看对方扶包的手；等对方目光转来才解除等待。'
HOLD = '尾音自然消退前不要结束当前画面'
TRANSITION = 'Both hands settle flat on the closed counter edge before this view ends'
PURPOSE = 'Let the audience recognize that the recipient controls the pace'
FUTURE = 'In a later scene the recipient will refuse a second request'


def facts(raw, domain):
    return next(row['facts'] for row in raw if row['domain'] == domain)


def prompt(row):
    return row['wire']['content'][0]['text']


def entries(row, *, suffix=None):
    return [e for e in row['coverage'].entries if suffix is None
            or e.source_ref.path[-len(suffix):] == suffix]


def internal_lines(row):
    line_rows = entries(row, suffix=('lines',))
    assert len(line_rows) == 1
    assert line_rows[0].domain == 'PERFORMANCE'
    assert line_rows[0].status == 'INTERNAL_ONLY' and line_rows[0].span is None
    # One review pointer to the retained container, not a second copy of DPD.
    assert not any('lines' in e.source_ref.path and e.status == 'TEXT_COVERED'
                   for e in row['coverage'].entries)


def assert_exact_receipt(row, source_ref, text):
    receipts = [e for e in row['coverage'].entries if e.source_ref == source_ref]
    assert len(receipts) == 1 and receipts[0].status == 'TEXT_COVERED'
    start, end = receipts[0].span
    # Generator receipts cover their complete rendered atom, including this
    # existing end-state label. They must contain the full authored fact.
    assert prompt(row)[start:end] == '终态：' + text
    return receipts[0]


@pytest.mark.asyncio
async def test_line_only_listener_wait_stays_a_visible_handoff_gap(tmp_path, monkeypatch):
    req, raw = material(single=True)
    line = facts(raw, 'PERFORMANCE')['lines'][0]
    line['observableIntent'] = WAIT
    line['continuity'] = 'Keep this listener condition for professional realization'
    p, compiler, package, out = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        row = out[0]
        assert WAIT not in prompt(row)
        assert prompt(row).count('{Помогите.}') == 1
        internal_lines(row)
        # A successful preview is not a claim that the line-only design has
        # already been staged. The existing coverage exposes its retained owner.
        preview = await compiler.preview_request(package.artifact_reference(), row['task'])
        assert preview['request'] == row['wire']
        line_rows = [e for e in preview['coverage']['entries']
                     if e['sourceRef']['path'][-1:] == ['lines']]
        assert len(line_rows) == 1 and line_rows[0]['status'] == 'INTERNAL_ONLY'
        assert preview['submitted'] is False and preview['productionAuthorized'] is False
    finally:
        await p.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('lane', ['ACTION', 'BEAT', 'AUDIO'])
async def test_existing_owner_realization_delivers_listener_wait_without_copying_dpd(tmp_path, monkeypatch, lane):
    req, raw = material(single=True)
    facts(raw, 'PERFORMANCE')['lines'][0]['observableIntent'] = WAIT
    if lane == 'ACTION':
        facts(raw, 'ACTION')['actionPhases'][0]['action'] += ' ' + WAIT
        suffix = ('actionPhases', '0', 'action')
    elif lane == 'BEAT':
        facts(raw, 'PERFORMANCE')['beats'][1]['physicalExpression'] = WAIT
        suffix = ('beats', '1', 'physicalExpression')
    else:
        facts(raw, 'SOUND')['audio_events'][0]['continuity'] = WAIT
        suffix = ('audio_events', '0', 'continuity')
    p, _, _, out = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        row = out[0]
        assert WAIT in prompt(row)
        internal_lines(row)
        covered = entries(row, suffix=suffix)
        assert len(covered) == 1 and covered[0].status == 'TEXT_COVERED'
        a, b = covered[0].span
        assert WAIT in prompt(row)[a:b]
        assert prompt(row).count('{Помогите.}') == 1
    finally:
        await p.aclose()


@pytest.mark.asyncio
async def test_retrospective_voiceover_and_future_line_context_are_not_new_actions(tmp_path, monkeypatch):
    req, raw = material(single=True)
    line = facts(raw, 'PERFORMANCE')['lines'][0]
    memory = 'He privately remembers a childhood journey before answering'
    line['dramaticAction'] = 'Retrospective reflection'
    line['observableIntent'] = memory
    line['continuity'] = FUTURE
    event = facts(raw, 'SOUND')['audio_events'][0]
    event['delivery_mode'] = 'VOICE_OVER'
    event['performance'] = 'One retrospective voice outside the pictured exchange'
    p, _, _, out = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        row = out[0]
        text = prompt(row)
        assert memory not in text and FUTURE not in text
        assert event['performance'] in text
        assert 'retrospective voice-over' in text
        assert 'Do not make the visible speaker lip-sync' in text
        assert facts(raw, 'ACTION')['actionPhases'][0]['action'] in text
        internal_lines(row)
    finally:
        await p.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('realized', [False, True])
async def test_numeric_whole_shot_hold_needs_existing_current_container(tmp_path, monkeypatch, realized):
    req, raw = material(single=True)
    editorial = facts(raw, 'EDITORIAL')
    timeline = '0–2秒接稳；2–5秒说话；5–8秒' + HOLD
    editorial['temporalStructure'] = timeline
    editorial.pop('protectedEvents', None)
    if realized:
        editorial['protectedEvents'] = [{'phaseIndex': 0, 'design': HOLD}]
    p, _, _, out = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        row = out[0]
        assert timeline not in prompt(row)
        assert (HOLD in prompt(row)) == realized
        context = entries(row, suffix=('temporalStructure',))
        assert len(context) == 1 and context[0].status == 'OUT_OF_UNIT'
        assert context[0].span is None
        if realized:
            protected = entries(row, suffix=('protectedEvents', '0', 'design'))
            assert len(protected) == 1
            a, b = protected[0].span
            assert protected[0].status == 'TEXT_COVERED' and prompt(row)[a:b] == HOLD
        else:
            assert not any(e.status == 'UNRESOLVED' for e in row['coverage'].entries)
    finally:
        await p.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('realization', ['NONE', 'EXACT', 'PARAPHRASE', 'EMBEDDED'])
async def test_shot_obligation_coverage_requires_full_owner_text_and_real_span(tmp_path, monkeypatch, realization):
    req, raw = material(single=True)
    req = req.model_copy(update={'shot': req.shot.model_copy(update={
        'purpose': PURPOSE, 'required_transition': TRANSITION})})
    paraphrase = 'End when the two hands rest on the counter edge'
    if realization != 'NONE':
        facts(raw, 'ACTION')['actionPhases'][0]['observable'] = {
            'EXACT': TRANSITION, 'PARAPHRASE': paraphrase,
            'EMBEDDED': TRANSITION + '; keep the packet supported'}[realization]
    p, compiler, package, out = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        row = out[0]
        assert PURPOSE not in prompt(row)
        assert len(package.obligations) == 2
        for ref in package.obligations:
            receipt = next(e for e in row['coverage'].entries if e.source_ref == ref)
            assert receipt.domain == 'DIRECTION'
            assert receipt.fact_id.startswith('shot-obligation:')
            is_transition = ref.path[-1] == 'requiredTransition'
            if is_transition and realization == 'EXACT':
                exact = assert_exact_receipt(row, ref, TRANSITION)
                action = entries(row, suffix=('actionPhases', '0', 'observable'))
                # One source can supply both selected event-result and end-state
                # slots; both existing receipts share the same rendered atom.
                assert action and all(e.status == 'TEXT_COVERED' and e.span == exact.span for e in action)
            else:
                assert receipt.status == 'INTERNAL_ONLY' and receipt.span is None
        assert (TRANSITION in prompt(row)) == (realization in {'EXACT', 'EMBEDDED'})
        assert (paraphrase in prompt(row)) == (realization == 'PARAPHRASE')
        preview = await compiler.preview_request(package.artifact_reference(), row['task'])
        assert preview['coverage'] == row['coverage'].model_dump(mode='json', by_alias=True)
        assert preview['request'] == row['wire']
    finally:
        await p.aclose()


@pytest.mark.asyncio
async def test_future_transition_and_purpose_remain_internal_without_compiler_invention(tmp_path, monkeypatch):
    req, raw = material(single=True)
    req = req.model_copy(update={'shot': req.shot.model_copy(update={
        'purpose': PURPOSE, 'required_transition': FUTURE})})
    p, _, package, out = await pipeline(tmp_path, monkeypatch, req, raw)
    try:
        row = out[0]
        assert PURPOSE not in prompt(row) and FUTURE not in prompt(row)
        receipts = [e for e in row['coverage'].entries if e.source_ref in package.obligations]
        assert len(receipts) == len(package.obligations) == 2
        assert all(e.status == 'INTERNAL_ONLY' and e.span is None for e in receipts)
        assert facts(raw, 'ACTION')['actionPhases'][0]['action'] in prompt(row)
    finally:
        await p.aclose()


@pytest.mark.asyncio
async def test_formal_professional_controlled_response_is_contract_valid_persisted_and_delivered(tmp_path, monkeypatch):
    """Exercise the real author adapter, with an explicitly fixed local reply.

    This proves actual method/schema/DTO/source/wire plumbing, never the quality
    of a real model's decisions. HTTP MockTransport supplies text only.
    """
    req, raw = material(single=True)
    req = req.model_copy(update={'shot': req.shot.model_copy(update={
        'purpose': PURPOSE, 'required_transition': TRANSITION})})
    facts(raw, 'PERFORMANCE')['lines'][0]['observableIntent'] = WAIT
    facts(raw, 'ACTION')['actionPhases'][0]['action'] += ' ' + WAIT
    facts(raw, 'ACTION')['actionPhases'][0]['observable'] = TRANSITION
    facts(raw, 'EDITORIAL')['temporalStructure'] = '0–8秒安排当前等待并保留尾音'
    facts(raw, 'EDITORIAL')['protectedEvents'] = [{'phaseIndex': 0, 'design': HOLD}]
    author_owner = configured(monkeypatch, tmp_path/'formal-author')
    calls = []

    def controlled_text_response(request):
        payload = json.loads(request.content)
        calls.append(payload)
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'role': 'assistant', 'content': json.dumps(raw, ensure_ascii=False)}}]})

    author = author_owner.professional_design.author
    assert isinstance(author, FormalProfessionalAuthor)
    author.client.transport = httpx.MockTransport(controlled_text_response)
    try:
        authored = await author.design(req)
        assert len(calls) == 1
        expected = tuple(DesignBody.model_validate(row) for row in professional_projection(raw, req))
        assert authored == expected
        schema = professional_model_schema()
        system = calls[0]['messages'][0]['content']
        assert json.loads(system.split('\nOutput JSON schema:\n', 1)[1]) == schema
        skills = Path(__file__).resolve().parents[1]/'skills'
        for method in ('action-choreography/SKILL.md', 'editorial-design/SKILL.md',
                       'dramatic-performance-direction/SKILL.md'):
            assert (skills/method).read_text() in system
        # The same complete source bodies accepted by the real formal adapter
        # become the real native originals used by this isolated pipeline.
        p, _, package, out = await pipeline(tmp_path/'wire', monkeypatch, req, raw)
        try:
            versions = tuple(p.creative_versions.resolve(ref)
                             for ref in out[0]['task'].owners.adopted_refs)
            retained = tuple(version.body for version in versions if version.kind == Kind.PROFESSIONAL)
            assert tuple((row.domain, creative_facts(row.facts)) for row in retained) == tuple(
                (row.domain, creative_facts(row.facts)) for row in authored)
            for version in versions:
                if version.kind != Kind.PROFESSIONAL:
                    continue
                # Compare the concrete current source identities/versions/hashes,
                # not merely the presence of a nonempty metadata container.
                source_by_kind = {p.creative_versions.resolve(ref).kind: ref for ref in version.source_refs}
                order = (Kind.WORK, Kind.SCRIPT, Kind.SCENE, Kind.SHOT, Kind.SOURCE)
                assert set(source_by_kind) == set(order)
                assert version.body.facts['sourcePins'] == [source_by_kind[k].model_dump(
                    mode='json', by_alias=True) for k in order]
                assert version.scope == req.scope
                assert version.body.facts['scope'] == req.scope.model_dump(mode='json', by_alias=True)
            row = out[0]
            assert WAIT in prompt(row) and HOLD in prompt(row) and TRANSITION in prompt(row)
            transition_ref = next(ref for ref in package.obligations if ref.path[-1] == 'requiredTransition')
            assert_exact_receipt(row, transition_ref, TRANSITION)
            internal_lines(row)
            assert row['ready'].provider_submission_allowed is False
        finally:
            await p.aclose()
    finally:
        await author_owner.aclose()
