"""M4 input views preserve creative evidence; mock authors are not effect proof."""
from copy import deepcopy
import json
import socket

import httpx
import pytest

from drama_plugin.creative_engine.author_projection import (
    professional_candidate_view, professional_projection, professional_schema,
)
from drama_plugin.creative_engine.backends import PROFESSIONAL_CRAFT
from drama_plugin.creative_engine.contracts import Authority, RevisionRequest, VersionRef
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure, structural_feedback, failure
from drama_plugin.execution.transport import CapabilityAbsent
from drama_plugin.runtime.contracts import ArtifactReference
from drama_plugin.production.contracts import SourceDomain
from test_event_scope_delivery import material
from test_formal_author_backends import configured


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('M4 regression cannot call a real author')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)


def fixture():
    req, raw = material()
    req = req.model_copy(update={'shot': req.shot.model_copy(update={
        'professional_domains': tuple(sorted((*req.shot.professional_domains, SourceDomain.REFERENCE)))})})
    raw.append({'domain': 'REFERENCE', 'facts': {'references': [
        {'priority': 'REQUIRED', 'beatSelections': [0, 1], 'designPurpose': 'Packet identity',
            'inputDuty': 'The same packet, not a new transfer.'}]}})
    sound = next(r['facts'] for r in raw if r['domain'] == 'SOUND')
    sound['speechRelations'] = []
    candidate = professional_projection(raw, req)
    revision = RevisionRequest(owner=Authority.PROFESSIONAL,
        target_ref=VersionRef(identity='retained-candidate', version=1, fingerprint='a'*64),
        finding_ref=ArtifactReference(owner='professional-review', artifact_ref='offline-finding'),
        instruction='REVISE_TASK_ONCE: resolve the identified contact uncertainty; preserve approved intent.')
    req = req.model_copy(update={'professional_context': {'currentDesigns': candidate}, 'revision': revision})
    return req, raw, candidate


def test_exact_inverse_uses_canon_order_and_preserves_all_semantic_fields():
    req, raw, candidate = fixture()
    before = deepcopy(candidate); authority = req.model_dump_json()
    view = professional_candidate_view(candidate, req)
    assert view == raw
    assert professional_projection(view, req) == candidate
    assert candidate == before and req.model_dump_json() == authority
    # A word that resembles an infrastructure key inside prose is never rewritten.
    candidate[0]['facts']['actionPhases'][0]['action'] = 'Keep literal beatId and courier in this sentence.'
    assert professional_candidate_view(candidate, req)[0]['facts']['actionPhases'][0]['action'] == candidate[0]['facts']['actionPhases'][0]['action']


def test_unknown_or_ambiguous_history_is_preserved_without_guess_or_new_gate():
    req, raw, candidate = fixture()
    perf = next(r['facts'] for r in candidate if r['domain'] == 'PERFORMANCE')
    perf['beats'][0]['target'] = 'almost Keeper'
    perf['beats'][1]['actor'] = []
    candidate[0]['facts']['actionPhases'][0]['beatId'] = 'unknown-historical-beat'
    event = next(r['facts'] for r in candidate if r['domain'] == 'SOUND')['audio_events'][0]
    event['speaker_key'] = 'conflicting-historical-speaker'
    view = professional_candidate_view(candidate, req)
    assert view[0]['facts']['actionPhases'][0]['beatId'] == 'unknown-historical-beat'
    assert next(r['facts'] for r in view if r['domain'] == 'PERFORMANCE')['beats'][0]['target'] == 'almost Keeper'
    assert next(r['facts'] for r in view if r['domain'] == 'PERFORMANCE')['beats'][1]['actor'] == []
    assert next(r['facts'] for r in view if r['domain'] == 'SOUND')['audio_events'][0] == event
    # Same display name is not sufficient to pick one of two canonical identities.
    scene = req.canon.scene.model_copy(update={'subjects': tuple(s.model_copy(update={'name': 'Same'}) for s in req.canon.scene.subjects)})
    perf['beats'][0]['target'] = 'Same'
    ambiguous = req.model_copy(update={'canon': req.canon.model_copy(update={'scene': scene})})
    assert next(r['facts'] for r in professional_candidate_view(candidate, ambiguous) if r['domain'] == 'PERFORMANCE')['beats'][0]['target'] == 'Same'
    # Evidence retention does not relax the model's output contract.
    with pytest.raises(AuthorResultFailure): professional_projection(view, req)


@pytest.mark.parametrize('revision,invalid', [(True, False), (False, False), (True, True)])
async def test_formal_entry_orders_revision_once_and_loads_methods_without_retry(tmp_path, monkeypatch, revision, invalid):
    req, raw, candidate = fixture()
    if not revision: req = req.model_copy(update={'revision': None})
    before = req.model_dump_json(); schema = professional_schema()
    p = configured(monkeypatch, tmp_path); calls = []
    def receive(wire):
        payload = json.loads(wire.content); calls.append(payload)
        messages = payload['messages']; inherited = json.loads(messages[1]['content'])
        assert inherited['source']['text'] == req.source.text
        assert inherited['shot']['purpose'] == req.shot.purpose
        if revision:
            task = json.loads(messages[-1]['content'].split('\n', 1)[1])
            assert task == {'currentDesigns': raw, 'revisionInstruction': req.revision.instruction}
            assert 'currentDesigns' not in inherited['visualContinuity'] and 'revisionInstruction' not in inherited
            assert sum(m['content'].count(req.revision.instruction) for m in messages) == 1
        else:
            assert len(messages) == 2 and inherited['visualContinuity']['currentDesigns'] == raw
        for domain in req.shot.professional_domains:
            for name in PROFESSIONAL_CRAFT[domain]:
                assert (p.professional_design.author.skills_root / name).read_text() in messages[0]['content']
        body = deepcopy(raw)
        if invalid: next(r['facts'] for r in body if r['domain'] == 'PERFORMANCE')['physicalExpression'] = 'Illegal top-level output'
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'role': 'assistant', 'content': json.dumps(body)}}]})
    p.professional_design.author.client.transport = httpx.MockTransport(receive)
    token = structural_feedback.set(failure('DTO_SCHEMA', 'AUTHOR_MODEL_FIELD_INVALID', role='professional') if invalid else None)
    try:
        if invalid:
            with pytest.raises(AuthorResultFailure): await p.professional_design.revise(req)
        else:
            result = await (p.professional_design.revise(req) if revision else p.professional_design.design(req))
            assert [r.model_dump(mode='json', by_alias=True) for r in result] == candidate
        assert len(calls) == 1
        assert req.model_dump_json() == before and professional_schema() == schema
    finally:
        structural_feedback.reset(token)
        await p.aclose()


async def test_revision_partition_does_not_bypass_existing_input_bound(tmp_path, monkeypatch):
    req, _, _ = fixture()
    context = deepcopy(req.professional_context)
    context['currentDesigns'][0]['facts']['physicalStateConstraints'] = 'x' * 2_000_001
    req = req.model_copy(update={'professional_context': context})
    p = configured(monkeypatch, tmp_path)
    def forbidden(_): raise AssertionError('Oversized revision must not call the service')
    p.professional_design.author.client.transport = httpx.MockTransport(forbidden)
    try:
        with pytest.raises(CapabilityAbsent, match='AUTHOR_INPUT_BOUND_EXCEEDED'):
            await p.professional_design.revise(req)
    finally: await p.aclose()
