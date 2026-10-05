"""Collect existing Professional findings and bound complete author regenerations.

All requests terminate at an in-process mock transport; owners/ledgers are temporary.
"""
import asyncio
import copy
import json
import subprocess
import sys
from collections import Counter

import httpx
import pytest

from drama_plugin.config.loader import load_config
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.backends import (FormalProfessionalAuthor, TextCompositionBackend,
    validate_professional_facts)
from drama_plugin.creative_engine.contracts import DesignBody
from drama_plugin.creative_engine.diagnostics import (AuthorDiagnostic, AuthorResultFailure,
    MAX_SAFE_FINDINGS, aggregate_failures, failure)
from drama_plugin.production.contracts import SourceDomain
from drama_plugin.runtime.contracts import RecoveryClass, RunMode, RuntimeState
from test_formal_author_backends import (ENV, SKILLS, REF, canon, configured, model_output,
    response, shot, source)
from test_partner_coverage_diagnostics import coverage_fault, performance_request
from test_runtime_repair_resume import Owner, FLOW, KEY, engine, evidence, rows
from test_unified_author_recovery import ROLE_MODEL, diagnostics, observed_wire, performance_fixture


def two_errors():
    facts = coverage_fault('BEAT_ACTOR_MISSING')
    facts['projectionSubjects'][0]['spokenIds'] = []
    return facts


def design(facts):
    return DesignBody(domain='PERFORMANCE', facts=facts)


def codes(diagnostic):
    return {issue.code for issue in diagnostic.issues}


def test_spoken_inventory_and_beat_coverage_are_collected_without_mutation():
    req = performance_request()
    facts = two_errors()
    before = copy.deepcopy(facts)
    authority = req.model_dump()
    with pytest.raises(AuthorResultFailure) as caught:
        validate_professional_facts((design(facts),), req)
    diagnostic = caught.value.diagnostic
    assert len(diagnostic.issues) == 2
    assert codes(diagnostic) == {'PROFESSIONAL_PROJECTION_SPOKEN_INVENTORY_INVALID',
        'PROFESSIONAL_PARTNER_DPD_REQUIRED'}
    inventory = next(i for i in diagnostic.issues if i.allowed_spoken_ids is not None)
    assert inventory.allowed_spoken_ids == ('appeal',)
    coverage = next(i for i in diagnostic.issues if i.reason)
    assert (coverage.reason, coverage.missing_subject_id, coverage.beat_id,
        coverage.expected_coverage_role) == ('BEAT_ACTOR_MISSING', 'uncovered-actor',
            'uncovered-beat', 'INTERACTIVE_PARTNER')
    assert all(i.stage and i.validator and i.domain == SourceDomain.PERFORMANCE for i in diagnostic.issues)
    assert facts == before and req.model_dump() == authority
    assert 'RAW-PROFESSIONAL-FACT' not in diagnostic.model_dump_json()


def test_independent_canon_speaker_and_all_beat_actors_are_reported():
    facts = coverage_fault('CANON_SPEAKER_MISSING')
    facts['beats'][0]['actor'] = 'uncovered-actor'
    with pytest.raises(AuthorResultFailure) as caught:
        validate_professional_facts((design(facts),), performance_request())
    coverage = [i for i in caught.value.diagnostic.issues if i.reason]
    assert {i.reason for i in coverage} == {'CANON_SPEAKER_MISSING', 'BEAT_ACTOR_MISSING'}
    assert next(i for i in coverage if i.reason == 'CANON_SPEAKER_MISSING').spoken_id == 'appeal'


async def test_domain_inventory_metadata_and_structured_paths_share_one_diagnostic():
    req = performance_request()
    req = req.model_copy(update={'shot': req.shot.model_copy(update={
        'professional_domains': (SourceDomain.LIGHTING, SourceDomain.PERFORMANCE)})})
    facts = two_errors()
    facts['sourcePins'] = [{'identity': 'PRIVATE_MODEL_METADATA_MUST_NOT_RETAIN'}]
    output = [design(facts).model_dump(mode='json', by_alias=True),
        design(performance_fixture()).model_dump(mode='json', by_alias=True),
        {'domain': 'SOUND', 'facts': {'legacy': 'not-executable'}}]
    client = TextCompositionBackend(load_config(environment=ENV).text_composition,
        transport=httpx.MockTransport(lambda req: response(output)))
    with pytest.raises(AuthorResultFailure) as caught:
        await FormalProfessionalAuthor(client, SKILLS).design(req)
    diagnostic = caught.value.diagnostic
    mismatch = [i for i in diagnostic.issues if i.code == 'PROFESSIONAL_DOMAIN_AUTHORITY_MISMATCH']
    assert {i.domain for i in mismatch} == {SourceDomain.LIGHTING, SourceDomain.PERFORMANCE, SourceDomain.SOUND}
    assert 'AUTHOR_SYSTEM_FIELD_FORBIDDEN' in codes(diagnostic)
    assert 'AUTHOR_SELECTION_NOT_IN_AUTHORITY' in codes(diagnostic)
    assert len(diagnostic.issues)>3
    missing = [i.field_path for i in diagnostic.issues if i.code == 'AUTHOR_MODEL_FIELD_REQUIRED']
    assert ('ambience',) in missing and ('orderingRules',) in missing
    assert 'PRIVATE_MODEL_METADATA' not in diagnostic.model_dump_json()
    assert output[0]['facts'] == facts


def test_invalid_baseline_does_not_hide_independent_coverage_or_other_domain():
    facts = two_errors()
    facts['sceneDPD'] = {'direction': 'UNTRUSTED_WRONG_TYPE'}
    with pytest.raises(AuthorResultFailure) as caught:
        validate_professional_facts((design(facts), DesignBody(domain='LIGHTING', facts={'legacy': 'not-executable'})), performance_request())
    diagnostic = caught.value.diagnostic
    assert {'PROFESSIONAL_EXECUTABLE_FACTS_INVALID', 'PROFESSIONAL_PARTNER_DPD_REQUIRED',
        'PROFESSIONAL_PROJECTION_SPOKEN_INVENTORY_INVALID'} <= codes(diagnostic)
    assert {i.domain for i in diagnostic.issues} == {SourceDomain.PERFORMANCE, SourceDomain.LIGHTING}
    assert 'UNTRUSTED_WRONG_TYPE' not in diagnostic.model_dump_json()


def test_unsafe_array_row_does_not_hide_safe_sibling_coverage():
    facts = two_errors()
    facts['beats'].insert(0, {'actor': 'PRIVATE_INVALID_ROW'})
    facts['projectionSubjects'].append({'subjectRef': 'PRIVATE_INVALID_ROW'})
    before = copy.deepcopy(facts)
    with pytest.raises(AuthorResultFailure) as caught:
        validate_professional_facts((design(facts),), performance_request())
    diagnostic = caught.value.diagnostic
    assert {'PROFESSIONAL_EXECUTABLE_FACTS_INVALID', 'PROFESSIONAL_PARTNER_DPD_REQUIRED',
        'PROFESSIONAL_PROJECTION_SPOKEN_INVENTORY_INVALID'} <= codes(diagnostic)
    coverage = next(i for i in diagnostic.issues if i.reason == 'BEAT_ACTOR_MISSING')
    assert coverage.missing_subject_id == 'uncovered-actor' and coverage.beat_id == 'uncovered-beat'
    assert 'PRIVATE_INVALID_ROW' not in diagnostic.model_dump_json()
    assert facts == before


def test_typed_dpd_failures_and_independent_action_sound_reference_are_collected():
    facts = two_errors()
    # Valid JSON shape, but the existing typed DPD contract rejects empty text.
    facts['lines'][0]['dramaticAction'] = ''
    facts['lines'][0]['observableIntent'] = ''
    facts['projectionSubjects'].append({'subjectRef': 'destination', 'sourceTargetLabel': 'destination',
        'role': 'NON_INTERACTIVE_DESTINATION', 'beatIds': ['appeal-beat'],
        'spatialPresenceOnly': True, 'behaviorExpansionForbidden': True, 'objectives': ['Not permitted']})
    action = DesignBody(domain='ACTION', facts={'actionPhases': [{
        'beatId': 'wrong-beat', 'action': 'Approved action', 'entryState': 'Entry',
        'observable': 'Exit', 'spokenIds': ['not-canon']}]})
    sound = DesignBody(domain='SOUND', facts={'ambience': [{'design': 'Silence'}],
        'orderingRules': [], 'speechRelations': [{'eventId': 'appeal',
            'targetEventId': 'not-canon', 'relation': 'AFTER'}]})
    reference = DesignBody(domain='REFERENCE', facts={'references': [{'id': 'reference',
        'priority': 'REQUIRED', 'beatIds': ['not-a-beat'],
        'designPurpose': 'Approved presence', 'inputDuty': 'Visual presence'}]})
    with pytest.raises(AuthorResultFailure) as caught:
        validate_professional_facts((design(facts), action, sound, reference), performance_request())
    diagnostic = caught.value.diagnostic
    assert {'AUTHOR_DOMAIN_RESULT_INVALID', 'PROFESSIONAL_PARTNER_DPD_REQUIRED',
        'PROFESSIONAL_PROJECTION_SPOKEN_INVENTORY_INVALID', 'PROFESSIONAL_ACTION_SOURCE_SCOPE_INVALID',
        'PROFESSIONAL_SPEECH_RELATION_SCOPE_INVALID', 'PROFESSIONAL_REFERENCE_SOURCE_SCOPE_INVALID'} <= codes(diagnostic)
    paths = {i.field_path for i in diagnostic.issues if i.code == 'PROFESSIONAL_EXECUTABLE_FACTS_INVALID'}
    assert (0, 'facts', 'lines', 0, 'dramaticAction') in paths
    assert (0, 'facts', 'lines', 0, 'observableIntent') in paths


@pytest.mark.parametrize('schedule', ('correct-second', 'correct-third', 'exhausted'))
async def test_runtime_sends_all_current_findings_and_has_no_sixth_call(monkeypatch, tmp_path, schedule):
    p = configured(monkeypatch, tmp_path)
    calls = Counter()
    seen = []
    def handle(req):
        payload = json.loads(req.content)
        role = ROLE_MODEL[payload['model']]
        calls[role] += 1
        seen.append((role, payload))
        body = model_output(role)
        if role == 'direction':
            body['professionalDomains'] = ['PERFORMANCE']
        if role == 'professional':
            facts = performance_fixture()
            if calls[role] == 1 or schedule == 'exhausted':
                facts = two_errors()
                facts['lines'][0]['spokenContentId']='outside-canonical-selection'
            elif schedule == 'correct-third' and calls[role] == 2:
                facts = coverage_fault('BEAT_ACTOR_MISSING')
            body = [design(facts).model_dump(mode='json', by_alias=True)]
        return observed_wire(json.dumps(body))
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    run = p.create_film_run(work_id='collect-all-' + schedule, mode=RunMode.PRODUCTION, source=source())
    result = await p.runtime.run(run.run_id)
    assert calls['professional'] == (5 if schedule == 'exhausted' else 2 if schedule == 'correct-second' else 3)
    requests = [payload for role, payload in seen if role == 'professional']
    feedback = json.loads(requests[1]['messages'][2]['content'].split('\n', 1)[1])
    # Spoken inventories are now system-derived; model feedback reports all
    # illegal semantic selections instead of asking the model to fix IDs.
    assert {i['code'] for i in feedback['issues']} == {'AUTHOR_SELECTION_NOT_IN_AUTHORITY'}
    assert len(feedback['issues'])>=2
    assert all(i['validator']=='authority_candidate_selection' for i in feedback['issues'])
    if schedule == 'correct-third':
        latest=json.loads(requests[2]['messages'][2]['content'].split('\n',1)[1])
        assert {i['code'] for i in latest['issues']} == {'AUTHOR_SELECTION_NOT_IN_AUTHORITY'}
    if schedule == 'exhausted':
        assert result.state == RuntimeState.FAILED and result.last_result.code == 'RETRY_LIMIT_REACHED'
        assert result.step_attempts == result.step_retry_limit == 5
    else:
        assert result.state == RuntimeState.WAITING_USER and result.cursor == 6
        assert len([v for v in p.creative_versions.versions() if v.kind.value == 'PROFESSIONAL']) == 1
    retained = json.dumps(diagnostics(p)) + json.dumps(requests[1:])
    # Corrective request includes original authoritative input, never prior invalid facts.
    assert all(secret not in retained for secret in ('RAW-PROFESSIONAL-FACT', 'HIDDEN_REASONING',
        ENV['DRAMA_PLUGIN_TEXT_COMPOSITION_API_KEY']))
    before = calls.copy()
    await p.aclose()
    p = configured(monkeypatch, tmp_path)
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    assert (await p.runtime.run(run.run_id)) == result
    assert calls == before
    await p.aclose()


@pytest.mark.parametrize('role', ('canon', 'direction'))
async def test_other_formal_authors_can_succeed_on_third_complete_generation(monkeypatch, tmp_path, role):
    p = configured(monkeypatch, tmp_path)
    calls = Counter()
    def handle(req):
        actual = ROLE_MODEL[json.loads(req.content)['model']]
        calls[actual] += 1
        return observed_wire('invalid-json') if actual == role and calls[actual] < 3 else response(model_output(actual))
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    run = p.create_film_run(work_id='third-' + role, mode=RunMode.PRODUCTION, source=source())
    assert (await p.runtime.run(run.run_id)).state == RuntimeState.WAITING_USER
    assert calls[role] == 3 and sum(calls.values()) == 5
    await p.aclose()


@pytest.mark.parametrize('role', ('canon', 'direction', 'professional'))
@pytest.mark.parametrize('succeeds', (True, False))
async def test_film_parent_and_child_share_per_step_five_call_bound(monkeypatch, tmp_path, role, succeeds):
    from drama_plugin.film.contracts import FilmCanon, FilmDirection, CanonScene, DirectedShot, LanguageMetadata, DeliveryProfile
    from drama_plugin.film.policy import film_workflow
    p = configured(monkeypatch, tmp_path)
    c = canon()
    film = FilmCanon(work=c.work, script=c.script, scenes=(CanonScene(scene_id='first', scene=c.scene),))
    direction = FilmDirection(shots=(DirectedShot(scene_id='first', shot_id='view', shot=shot().model_copy(update={
        'professional_domains': (SourceDomain.PERFORMANCE,)})),))
    calls = Counter()
    def handle(req):
        actual = ROLE_MODEL[json.loads(req.content)['model']]
        calls[actual] += 1
        if actual == role and (not succeeds or calls[actual] < 5):
            return observed_wire('invalid-json')
        output = {'canon': film.model_dump(mode='json', by_alias=True),
            'direction': direction.model_dump(mode='json', by_alias=True),
            'professional': [design(performance_fixture()).model_dump(mode='json', by_alias=True)]}[actual]
        return response(output)
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    run = p.create_source_film_run(work_id='film-bound', run_id='film-bound', source=source(),
        languages=LanguageMetadata(source_document_language='en', original_work_language='ru',
            spoken_language='ru', authority_ref=REF), profile=DeliveryProfile(width=1280, height=720),
        rights_refs=(REF,), route='offline', model='offline-model', workflow_id=film_workflow().workflow_id)
    result = await p.runtime.run(run.run_id)
    assert calls[role] == 5
    if succeeds:
        assert result.state == RuntimeState.WAITING_USER and result.cursor == 3
    else:
        assert result.state == RuntimeState.FAILED
    before = calls.copy()
    await p.runtime.run(run.run_id)
    assert calls == before
    await p.aclose()


async def test_internal_error_is_hard_and_does_not_run_later_fact_validators(monkeypatch, tmp_path):
    p = configured(monkeypatch, tmp_path)
    calls = Counter()
    def handle(req):
        role = ROLE_MODEL[json.loads(req.content)['model']]
        calls[role] += 1
        return response(model_output(role))
    def internal_failure(*args):
        raise RuntimeError('PRIVATE INTERNAL IMPLEMENTATION FAILURE')
    def never_validate(*args, **kwargs):
        pytest.fail('Unsafe internal error must terminate before further validators')
    monkeypatch.setattr('drama_plugin.creative_engine.backends.professional_projection', internal_failure)
    monkeypatch.setattr('drama_plugin.creative_engine.backends.validate_professional_facts', never_validate)
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    run = p.create_film_run(work_id='hard-internal', mode=RunMode.PRODUCTION, source=source())
    result = await p.runtime.run(run.run_id)
    assert result.state == RuntimeState.FAILED and result.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    assert result.last_result.code == 'UNEXPECTED_AUTHOR_BACKEND_FAILURE'
    assert calls['professional'] == 1
    assert 'PRIVATE INTERNAL' not in json.dumps(diagnostics(p))
    await p.aclose()


async def test_immutable_input_conflict_stops_before_any_author_output_validation(monkeypatch, tmp_path):
    p = configured(monkeypatch, tmp_path)
    calls = []
    p.creative.canon_author.client.transport = httpx.MockTransport(lambda req: calls.append(req) or response(model_output('canon')))
    run = p.create_film_run(work_id='bad-authority', mode=RunMode.PRODUCTION, source=source())
    ready = await p.runtime.run(run.run_id, max_ticks=2)
    assert ready.cursor == 1 and ready.state == RuntimeState.READY
    def authority_failure(_):
        raise ValueError('IMMUTABLE_HASH_CONFLICT_PRIVATE_DETAILS')
    monkeypatch.setattr(p.creative_versions, 'resolve', authority_failure)
    result = await p.runtime.run(run.run_id)
    assert result.state == RuntimeState.FAILED and result.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    assert result.last_result.code == 'EXECUTION_IDENTITY_UNAVAILABLE' and not calls
    assert not diagnostics(p)
    await p.aclose()


def test_aggregate_is_bounded_deduplicated_and_cannot_hide_hard_failure():
    findings = tuple(failure('DTO_SCHEMA', 'PROFESSIONAL_EXECUTABLE_FACTS_INVALID', role='professional',
        field_path=('facts', 'beats', i), validator='FormalProfessionalAuthor.executable_fact_schema',
        domain=SourceDomain.PERFORMANCE) for i in range(MAX_SAFE_FINDINGS + 1))
    diagnostic = aggregate_failures((*findings, findings[0]))
    assert len(diagnostic.issues) == MAX_SAFE_FINDINGS and diagnostic.omitted_issue_count == 1
    hard = failure('INTERNAL', 'AUTHOR_IMMUTABLE_INPUT_OR_OWNER_INVALID', role='professional')
    with pytest.raises(AuthorResultFailure) as caught:
        aggregate_failures((*findings, hard))
    assert caught.value.diagnostic == hard
    old = AuthorDiagnostic.model_validate({'role': 'professional', 'failure_stage': 'DTO_SCHEMA',
        'code': 'AUTHOR_DOMAIN_RESULT_INVALID', 'issues': [{'field_path': ['facts'], 'error_type': 'missing'}]})
    assert old.issues[0].code is None and old.omitted_issue_count == 0


class BoundedAuthor(Owner):
    limit = 3

    def inspect(self, inputs):
        return super().inspect(inputs).model_copy(update={'retry_limit': self.limit})


async def test_limit_is_persisted_before_first_call_and_crash_cannot_refresh_it(tmp_path):
    owner = BoundedAuthor()
    owner.crash = True
    path = tmp_path / 'ledger.sqlite'
    runtime, ledger = engine(path, owner)
    run = runtime.create_run(work_id='work', mode=RunMode.PRODUCTION, workflow_id=FLOW.workflow_id)
    for expected in (1, 2, 3):
        with pytest.raises(asyncio.CancelledError):
            await runtime.run(run.run_id)
        restored = ledger.load_run(run.run_id)
        assert restored.step_attempts == expected and restored.step_retry_limit == 3
        runtime, _ = engine(path, owner)
    before = rows(ledger)
    failed = await runtime.run(run.run_id)
    assert failed.state == RuntimeState.FAILED and failed.last_result.code == 'RETRY_LIMIT_REACHED'
    assert owner.calls == 3 and rows(ledger) == before
    program = """
import sys
from drama_plugin.persistence.ledger import ProductionLedger
r = ProductionLedger(sys.argv[1]).load_run(sys.argv[2])
assert r.state.value == 'FAILED' and r.step_attempts == r.step_retry_limit == 3
"""
    result = subprocess.run([sys.executable, '-c', program, str(path), run.run_id], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('capture_old_limit', (True, False))
async def test_old_two_attempt_execution_cannot_gain_new_default_budget(tmp_path, capture_old_limit):
    owner = BoundedAuthor()
    owner.limit = 2 if capture_old_limit else None
    runtime, ledger = engine(tmp_path / 'ledger.sqlite', owner)
    run = runtime.create_run(work_id='work', mode=RunMode.PRODUCTION, workflow_id=FLOW.workflow_id)
    blocked = await runtime.run(run.run_id, max_ticks=2)
    assert blocked.state == RuntimeState.BLOCKED and blocked.step_attempts == 1
    owner.limit = 3
    runtime, _ = engine(ledger.path, owner)
    failed = await runtime.run(run.run_id)
    assert owner.calls == 2 and failed.step_attempts == failed.step_retry_limit == 2
    assert failed.state == RuntimeState.FAILED and failed.last_result.code == 'RETRY_LIMIT_REACHED'
    historical = rows(ledger)
    owner.fingerprint = sha256_canonical('implementation-repair')
    assert (await runtime.run(run.run_id)) == failed
    assert rows(ledger) == historical and owner.calls == 2
    proof = evidence(failed.execution_revision, attempts=2)
    reserved = await runtime.repair_resume(run.run_id, cursor=0, capability_key=KEY, exhausted=proof)
    assert reserved.step_attempts == reserved.step_retry_limit == 2
    exhausted = await runtime.run(run.run_id)
    assert exhausted.state == RuntimeState.FAILED and owner.calls == 3
    assert all(row in rows(ledger) for row in historical)
    with pytest.raises(ValueError):
        await runtime.repair_resume(run.run_id, cursor=0, capability_key=KEY, exhausted=proof)
    await runtime.run(run.run_id)
    assert owner.calls == 3


async def test_three_attempt_exhaustion_requires_existing_single_use_repair_contract(tmp_path):
    owner = BoundedAuthor()
    runtime, ledger = engine(tmp_path / 'ledger.sqlite', owner)
    run = runtime.create_run(work_id='work', mode=RunMode.PRODUCTION, workflow_id=FLOW.workflow_id)
    failed = await runtime.run(run.run_id)
    assert failed.state == RuntimeState.FAILED and owner.calls == 3
    proof = evidence(failed.execution_revision, attempts=3)
    with pytest.raises(ValueError, match='RETRY_LIMIT_REACHED'):
        await runtime.repair_resume(run.run_id, cursor=0, capability_key=KEY, exhausted=proof)
    owner.fingerprint = sha256_canonical('new-implementation')
    historical = rows(ledger)
    await runtime.repair_resume(run.run_id, cursor=0, capability_key=KEY, exhausted=proof)
    exhausted = await runtime.run(run.run_id)
    assert exhausted.step_attempts == 3 and exhausted.repair_resumes[0].attempts == 1
    assert owner.calls == 4 and all(row in rows(ledger) for row in historical)
    # Fourth *ordinary* call is impossible; this one was a separate authorized repair.
    runtime, _ = engine(ledger.path, owner)
    with pytest.raises(ValueError):
        await runtime.repair_resume(run.run_id, cursor=0, capability_key=KEY, exhausted=proof)
    await runtime.run(run.run_id)
    assert owner.calls == 4
