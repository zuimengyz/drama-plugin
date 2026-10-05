"""Unified author recovery: offline text wire, temporary owners and ledgers only."""
import json
from collections import Counter

import httpx
import pytest
from pydantic import TypeAdapter

from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.backends import (FormalProfessionalAuthor, TextCompositionBackend,
    professional_model_schema, validate_professional_facts)
from drama_plugin.creative_engine.contracts import Authority, DesignBody, Kind
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure, AuthorUnavailable, structural_feedback
from drama_plugin.creative_engine.sources import NativeCreativeSources
from drama_plugin.runtime.contracts import CapabilityInput, RecoveryClass, ResultStatus, RunMode, RuntimeState
from test_formal_author_backends import ENV, SKILLS, configured, model_output, request, response, source

ROLE_MODEL = {ENV['DRAMA_PLUGIN_' + role.upper() + '_AUTHOR_MODEL']: role
    for role in ('canon', 'direction', 'professional')}


def observed_wire(content, finish='stop'):
    from author_model_helpers import model_dto
    try: content=json.dumps(model_dto(json.loads(content)))
    except json.JSONDecodeError: pass
    return httpx.Response(200, json={'usage': {'prompt_tokens': 12, 'completion_tokens': 10,
        'completion_tokens_details': {'reasoning_tokens': 3}}, 'choices': [{'finish_reason': finish,
        'message': {'role': 'assistant', 'content': content,
            'reasoning_content': 'HIDDEN_REASONING_MUST_NOT_RETAIN'}}]})


def diagnostics(plugin):
    return [json.loads(path.read_text()) for path in (plugin.creative_versions.root / 'objects').glob('*.json')
        if json.loads(path.read_text()).get('schemaVersion') == 'author-failure-diagnostic-v1']


@pytest.mark.parametrize('role', ('canon', 'direction', 'professional'))
@pytest.mark.parametrize('bad_kind', ('json', 'length'))
async def test_all_formal_roles_correct_once_with_safe_structural_feedback(monkeypatch, tmp_path, role, bad_kind):
    p = configured(monkeypatch, tmp_path)
    calls = Counter()
    seen = []
    def handle(http_request):
        payload = json.loads(http_request.content)
        actual = ROLE_MODEL[payload['model']]
        calls[actual] += 1
        seen.append((actual, payload))
        if actual == role and calls[actual] == 1:
            return observed_wire('invalid-secret-model-output' if bad_kind == 'json' else json.dumps(model_output(actual)),
                finish='stop' if bad_kind == 'json' else 'length')
        return response(model_output(actual))
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    run = p.create_film_run(work_id='bounded-authors', mode=RunMode.PRODUCTION, source=source())
    result = await p.runtime.run(run.run_id)
    assert result.state == RuntimeState.WAITING_USER and result.cursor == 6
    assert calls == Counter({r: 2 if r == role else 1 for r in ('canon', 'direction', 'professional')})
    retry_payload = [payload for actual, payload in seen if actual == role][1]
    first_payload = [payload for actual, payload in seen if actual == role][0]
    assert len(retry_payload['messages']) == 3
    assert retry_payload['messages'][:2] == first_payload['messages']
    feedback = retry_payload['messages'][2]['content']
    assert 'Structural correction' in feedback
    assert 'invalid-secret-model-output' not in feedback and 'HIDDEN_REASONING' not in feedback
    records = diagnostics(p)
    assert len(records) == 1
    d = records[0]['diagnostic']
    assert d['provider'] == ENV['DRAMA_PLUGIN_TEXT_COMPOSITION_PROVIDER']
    assert d['model'] == ENV['DRAMA_PLUGIN_' + role.upper() + '_AUTHOR_MODEL']
    assert d['attempt'] == 1 and d['execution_revision'] == d['execution_fingerprint']
    assert d['usage']['reasoning_tokens'] == 3 and d['response_hash']
    serialized = json.dumps(records)
    assert ENV['DRAMA_PLUGIN_TEXT_COMPOSITION_API_KEY'] not in serialized
    assert 'HIDDEN_REASONING' not in serialized and 'invalid-secret-model-output' not in serialized
    assert structural_feedback.get() is None
    await p.aclose()


@pytest.mark.parametrize('role', ('canon', 'direction', 'professional'))
async def test_all_roles_exhaust_exactly_five_total_calls_without_nested_budget(monkeypatch, tmp_path, role):
    p = configured(monkeypatch, tmp_path)
    calls = Counter()
    def handle(http_request):
        actual = ROLE_MODEL[json.loads(http_request.content)['model']]
        calls[actual] += 1
        return observed_wire('invalid-json') if actual == role else response(model_output(actual))
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    run = p.create_film_run(work_id='exhausted-author', mode=RunMode.PRODUCTION, source=source())
    result = await p.runtime.run(run.run_id)
    assert result.state == RuntimeState.FAILED and result.last_result.code == 'RETRY_LIMIT_REACHED'
    assert result.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    assert calls[role] == 5 and result.step_attempts == result.step_retry_limit == 5
    assert len([d for d in diagnostics(p) if d['diagnostic']['role'] == role]) == 5
    before = calls.copy()
    assert (await p.runtime.run(run.run_id)).state == RuntimeState.FAILED
    assert calls == before
    await p.aclose()


@pytest.mark.parametrize('fault,role,stage', (
    ('required_field', 'canon', 'DTO_SCHEMA'),
    ('invalid_type', 'direction', 'DTO_SCHEMA'),
    ('invalid_enum', 'direction', 'DTO_SCHEMA'),
    ('spoken_ids', 'direction', 'DIALOGUE_AUTHORITY'),
    ('missing_domain', 'professional', 'DTO_SCHEMA'),
    ('source_pins', 'professional', 'DTO_SCHEMA'),
    ('timeout', 'canon', 'PROVIDER_PROTOCOL'),
))
async def test_actual_producer_faults_auto_correct_once_before_immutable_publication(monkeypatch, tmp_path, fault, role, stage):
    p = configured(monkeypatch, tmp_path)
    calls = Counter()
    requests = []
    def handle(http_request):
        payload = json.loads(http_request.content)
        actual = ROLE_MODEL[payload['model']]
        calls[actual] += 1
        requests.append((actual, payload))
        output = model_output(actual)
        if actual == role and calls[actual] == 1:
            if fault == 'required_field':
                output.pop('scene')
            elif fault == 'invalid_type':
                output['durationMs'] = 'private-model-invalid-value'
            elif fault == 'invalid_enum':
                output['professionalDomains'] = ['NOT_A_DOMAIN']
            elif fault == 'spoken_ids':
                output['spokenIds'] = ['not-canon-dialogue']
            elif fault == 'missing_domain':
                output = []
            elif fault == 'source_pins':
                output[0]['facts']['sourcePins'] = [{'identity': 'MODEL_INVENTED_SYSTEM_REF'}]
            elif fault == 'timeout':
                raise httpx.ReadTimeout('credential=PRIVATE must not retain', request=http_request)
            return observed_wire(json.dumps(output))
        return response(output)
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    run = p.create_film_run(work_id='producer-fault-' + fault, mode=RunMode.PRODUCTION, source=source())
    ready = await p.runtime.run(run.run_id)
    assert ready.state == RuntimeState.WAITING_USER and ready.cursor == 6
    assert calls[role] == 2 and sum(calls.values()) == 4
    ds = diagnostics(p)
    assert len(ds) == 1 and ds[0]['diagnostic']['failure_stage'] == stage
    assert ds[0]['diagnostic']['recovery_class'] == 'RETRY_SAME_STEP'
    # Only the valid second DTO is published as a fixed creative version.
    expected = {'canon': Kind.WORK, 'direction': Kind.SHOT, 'professional': Kind.PROFESSIONAL}[role]
    assert sum(v.kind == expected for v in p.creative_versions.versions()) == 1
    second = [payload for actual, payload in requests if actual == role][1]
    assert len(second['messages']) == 3
    serialized = json.dumps(ds)
    assert all(secret not in serialized for secret in ('PRIVATE', 'private-model-invalid-value',
        'MODEL_INVENTED_SYSTEM_REF', 'HIDDEN_REASONING', ENV['DRAMA_PLUGIN_TEXT_COMPOSITION_API_KEY']))
    await p.aclose()


async def test_film_direction_graph_fault_auto_retries_before_publishing_fixed_output(monkeypatch, tmp_path):
    from drama_plugin.film.contracts import FilmCanon, FilmDirection, CanonScene, DirectedShot, LanguageMetadata, DeliveryProfile
    from drama_plugin.film.policy import film_workflow
    from test_formal_author_backends import canon, shot, REF
    p = configured(monkeypatch, tmp_path)
    run = p.create_source_film_run(work_id='direction-graph', run_id='direction-graph', source=source(),
        languages=LanguageMetadata(source_document_language='en', original_work_language='ru', spoken_language='ru', authority_ref=REF),
        profile=DeliveryProfile(width=1280, height=720), rights_refs=(REF,), route='offline', model='offline-model',
        workflow_id=film_workflow().workflow_id)
    c = canon()
    film = FilmCanon(work=c.work, script=c.script, scenes=(CanonScene(scene_id='first', scene=c.scene),))
    direction = FilmDirection(shots=(DirectedShot(scene_id='first', shot_id='first-view', shot=shot()),))
    calls = Counter()
    def handle(http_request):
        role = ROLE_MODEL[json.loads(http_request.content)['model']]
        calls[role] += 1
        if role == 'canon':
            return response(film.model_dump(mode='json', by_alias=True))
        assert role == 'direction'
        assert p.film.store.checkpoint(run.run_id).direction_ref is None
        assert p.film.store.author_ref(run.run_id, 'film-direction') is None
        result = direction.model_dump(mode='json', by_alias=True)
        if calls[role] == 1:
            result['shots'][0]['requires'] = ['first-view']
        return observed_wire(json.dumps(result))
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    ready = await p.runtime.run(run.run_id, max_ticks=5)
    assert ready.state == RuntimeState.READY and ready.cursor == 2
    assert calls == Counter({'canon': 1, 'direction': 2})
    cp = p.film.store.checkpoint(run.run_id)
    assert p.film.store.author(cp.direction_ref, FilmDirection).shots[0].shot.purpose==direction.shots[0].shot.purpose
    diag = diagnostics(p)[0]['diagnostic']
    assert diag['code'] == 'AUTHOR_SELECTION_NOT_IN_AUTHORITY'
    assert diag['failure_stage'] == 'DIALOGUE_AUTHORITY' and diag['issues'][0]['field_path'] == ['shots', 0, 'requiresSelections']
    assert diag['execution_fingerprint'] == diag['execution_revision'] and diag['response_hash']
    await p.aclose()


@pytest.mark.parametrize('status', (401, 403, 404))
async def test_credential_model_failures_are_hard_without_retry(monkeypatch, tmp_path, status):
    p = configured(monkeypatch, tmp_path)
    calls = []
    p.creative.canon_author.client.transport = httpx.MockTransport(lambda req: calls.append(req) or
        httpx.Response(status, json={'error': ENV['DRAMA_PLUGIN_TEXT_COMPOSITION_API_KEY']}))
    run = p.create_film_run(work_id='invalid-service-config', mode=RunMode.PRODUCTION, source=source())
    failed = await p.runtime.run(run.run_id)
    assert failed.state == RuntimeState.FAILED and failed.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    assert len(calls) == 1
    assert diagnostics(p)[0]['diagnostic']['http_status'] == status
    await p.aclose()


@pytest.mark.parametrize('status', (429, 500, 502, 503, 504))
async def test_safe_text_http_transient_is_bounded_same_step_retry(monkeypatch, tmp_path, status):
    p = configured(monkeypatch, tmp_path)
    calls = []
    def handle(req):
        actual = ROLE_MODEL[json.loads(req.content)['model']]
        calls.append(actual)
        if actual == 'canon' and calls.count(actual) == 1:
            return httpx.Response(status, json={'error': 'untrusted-message'})
        return response(model_output(actual))
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    result = await p.runtime.run(p.create_film_run(work_id='safe-transient', mode=RunMode.PRODUCTION, source=source()).run_id)
    assert result.state == RuntimeState.WAITING_USER and calls.count('canon') == 2
    assert diagnostics(p)[0]['diagnostic']['recovery_class'] == 'RETRY_SAME_STEP'
    await p.aclose()


async def test_cross_process_author_budget_and_safe_feedback_survive(monkeypatch, tmp_path):
    p = configured(monkeypatch, tmp_path)
    calls = []
    p.creative.canon_author.client.transport = httpx.MockTransport(lambda req: calls.append(req) or observed_wire('bad-json'))
    run = p.create_film_run(work_id='restart-author', mode=RunMode.PRODUCTION, source=source(), run_id='restart-author')
    await p.runtime.run(run.run_id, max_ticks=2)
    blocked = await p.runtime.run(run.run_id, max_ticks=1)
    assert blocked.state == RuntimeState.BLOCKED and blocked.cursor == 1 and blocked.step_attempts == 1
    fingerprint = blocked.execution_revision.fingerprint
    await p.aclose()
    p = configured(monkeypatch, tmp_path)
    wire = []
    def handle(req):
        payload = json.loads(req.content)
        wire.append(payload)
        return response(model_output(ROLE_MODEL[payload['model']]))
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    restored = p.runtime.store.load(run.run_id)
    assert restored.step_attempts == 1 and restored.execution_revision.fingerprint == fingerprint
    result = await p.runtime.run(run.run_id)
    assert result.state == RuntimeState.WAITING_USER
    assert len([payload for payload in wire if ROLE_MODEL[payload['model']] == 'canon']) == 1
    assert len(wire[0]['messages']) == 3 and 'AUTHOR_DOMAIN_JSON_INVALID' in wire[0]['messages'][2]['content']
    assert len(calls) == 1
    await p.aclose()


async def test_committed_author_and_owner_bytes_recover_without_second_completion(monkeypatch, tmp_path):
    p = configured(monkeypatch, tmp_path)
    calls = []
    p.creative.canon_author.client.transport = httpx.MockTransport(lambda req: calls.append(
        ROLE_MODEL[json.loads(req.content)['model']]) or response(model_output(calls[-1])))
    run = p.create_film_run(work_id='owner-crash', mode=RunMode.PRODUCTION, source=source(), run_id='owner-crash')
    original = p.creative_versions.io.write
    failed_once = []
    def interrupt(path, data):
        if path.name.startswith('operation-') and '"identity":"creative-work:' in data and not failed_once:
            failed_once.append(True)
            raise OSError('private-error-not-retained')
        return original(path, data)
    monkeypatch.setattr(p.creative_versions.io, 'write', interrupt)
    await p.runtime.run(run.run_id, max_ticks=2)
    blocked = await p.runtime.run(run.run_id, max_ticks=1)
    assert blocked.state == RuntimeState.BLOCKED
    assert blocked.last_result.recovery_class == RecoveryClass.AUTO_RECOVER
    assert calls == ['canon']
    monkeypatch.setattr(p.creative_versions.io, 'write', original)
    await p.aclose()
    p = configured(monkeypatch, tmp_path)
    p.creative.canon_author.client.transport = httpx.MockTransport(lambda req: calls.append(
        ROLE_MODEL[json.loads(req.content)['model']]) or response(model_output(calls[-1])))
    result = await p.runtime.run(run.run_id)
    assert result.state == RuntimeState.WAITING_USER and calls == ['canon', 'direction', 'professional']
    versions = p.creative_versions.versions()
    assert sum(v.kind == Kind.WORK for v in versions) == 1
    await p.aclose()


@pytest.mark.parametrize('permanent', (False, True))
@pytest.mark.parametrize('first_invalid', (False, True))
async def test_second_author_call_committed_output_recovers_without_third_completion(monkeypatch, tmp_path, permanent, first_invalid):
    p = configured(monkeypatch, tmp_path)
    calls = Counter()
    def handle(req):
        role = ROLE_MODEL[json.loads(req.content)['model']]
        calls[role] += 1
        return observed_wire('invalid-json') if first_invalid and role == 'canon' and calls[role] == 1 else response(model_output(role))
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    run = p.create_film_run(work_id='second-call-commit', mode=RunMode.PRODUCTION, source=source())
    original = p.creative_versions.io.write
    failed_once = []
    def interrupt(path, data):
        if path.name.startswith('operation-') and '"identity":"creative-work:' in data and (permanent or not failed_once):
            failed_once.append(True)
            raise OSError('private-commit-failure')
        return original(path, data)
    monkeypatch.setattr(p.creative_versions.io, 'write', interrupt)
    expected_calls = 2 if first_invalid else 1
    blocked = await p.runtime.run(run.run_id, max_ticks=5 if first_invalid else 3)
    assert blocked.state == RuntimeState.BLOCKED and blocked.cursor == 1 and blocked.step_attempts == expected_calls
    assert blocked.last_result.recovery_class == RecoveryClass.AUTO_RECOVER and calls['canon'] == expected_calls
    with p.runtime.store.ledger.transaction() as db:
        historical = dict(db.execute('SELECT attempt_identity,result_identity FROM production_operation WHERE operation_id=?',
            (run.run_id + ':1',)).fetchall())
    assert len(historical) == expected_calls and all(historical.values())
    monkeypatch.setattr(p.creative_versions.io, 'write', original)
    await p.aclose()
    p = configured(monkeypatch, tmp_path)
    p.creative.canon_author.client.transport = httpx.MockTransport(handle)
    inspection = p.creative.inspect_canon_execution(CapabilityInput(run_id=run.run_id,
        operation_id=run.run_id + ':1', scope=run.scope))
    assert inspection.completed
    assert inspection.revision == blocked.execution_revision, (inspection.revision, blocked.execution_revision)
    if permanent:
        original = p.creative_versions.io.write
        monkeypatch.setattr(p.creative_versions.io, 'write', interrupt)
    ready = await p.runtime.run(run.run_id)
    if permanent:
        assert ready.state == RuntimeState.FAILED and ready.last_result.code == 'RETRY_LIMIT_REACHED'
        assert ready.step_attempts == expected_calls and ready.maintenance_attempts == 2
        assert calls == Counter({'canon': expected_calls}) and len(failed_once) == 3
        assert (await p.runtime.run(run.run_id)) == ready
    else:
        assert ready.state == RuntimeState.WAITING_USER and ready.cursor == 6, ready
        assert calls == Counter({'canon': expected_calls, 'direction': 1, 'professional': 1})
    assert sum(v.kind == Kind.WORK for v in p.creative_versions.versions()) == 1
    with p.runtime.store.ledger.transaction() as db:
        restored = dict(db.execute('SELECT attempt_identity,result_identity FROM production_operation WHERE operation_id=?',
            (run.run_id + ':1',)).fetchall())
    assert all(restored[attempt] == result for attempt, result in historical.items())
    assert len(restored) == expected_calls + (2 if permanent else 1)
    assert all(':recovery:' in attempt for attempt in restored.keys() - historical.keys())
    await p.aclose()


async def test_lost_exact_indices_rebuild_from_immutable_owner_bytes(monkeypatch, tmp_path):
    p = configured(monkeypatch, tmp_path)
    p.creative.canon_author.client.transport = httpx.MockTransport(lambda req: response(model_output(
        ROLE_MODEL[json.loads(req.content)['model']])))
    run = p.create_film_run(work_id='index-rebuild', mode=RunMode.PRODUCTION, source=source())
    assert (await p.runtime.run(run.run_id)).state == RuntimeState.WAITING_USER
    cp = p.creative.state.checkpoint(run.run_id)
    await p.decide_target_run(run.run_id, decision_id=p.runtime.decision_id(run.run_id), accepted=True, source_ref=cp.candidate_ref)
    assert (await p.runtime.run(run.run_id)).state == RuntimeState.SUCCEEDED
    cp = p.creative.state.checkpoint(run.run_id)
    sources = NativeCreativeSources(p.creative_versions, cp.refs)
    owned = await sources.scope_sources(run.scope)
    expected = owned[-1].reference('content')
    retained = p.creative_versions.resolve(next(r for r in cp.refs if p.creative_versions.resolve(r).kind == Kind.SHOT))
    for group in ('projection', 'selection', 'scope-selection', 'fingerprint', 'head'):
        for path in p.creative_versions.index.glob(group + '-*.json'):
            path.unlink()
    assert p.creative_versions.from_runtime_ref(retained.ref().runtime_ref()) == retained
    assert not p.creative_versions.stale(retained.ref())
    rebuilt = NativeCreativeSources(p.creative_versions)
    assert await rebuilt.resolve(expected) == owned[-1].body['content']
    assert p.creative_versions.selected_refs(retained.ref()) == cp.refs
    assert p.creative_versions.approved_selection(run.scope) == cp.refs
    await p.aclose()


async def test_adoption_consumer_without_receipt_waits_for_exact_candidate(monkeypatch, tmp_path):
    p = configured(monkeypatch, tmp_path)
    calls = []
    p.creative.canon_author.client.transport = httpx.MockTransport(lambda req: calls.append(
        ROLE_MODEL[json.loads(req.content)['model']]) or response(model_output(calls[-1])))
    run = p.create_film_run(work_id='exact-pending-adoption', mode=RunMode.PRODUCTION, source=source())
    waiting = await p.runtime.run(run.run_id)
    assert waiting.state == RuntimeState.WAITING_USER and waiting.cursor == 6
    cp = p.creative.state.checkpoint(run.run_id)
    result = await p.creative.adoption(CapabilityInput(run_id=run.run_id,
        operation_id=run.run_id + ':6', scope=run.scope))
    assert result.status == ResultStatus.WAITING_EXTERNAL
    assert result.recovery_class == RecoveryClass.USER_DECISION
    assert result.external_ref == cp.candidate_ref and result.user_decision.category.value == 'ADOPTION'
    assert result.code is None and p.creative.state.checkpoint(run.run_id).decision_ref is None
    assert calls == ['canon', 'direction', 'professional']
    await p.aclose()


def test_formal_professional_schema_is_typed_and_system_metadata_free():
    schema = professional_model_schema()
    conditional = schema['$defs']['DesignBody']['allOf']
    contracts = {row['if']['properties']['domain']['const']: row['then']['properties']['facts'] for row in conditional}
    performance = contracts['PERFORMANCE']['properties']
    assert {'sceneDPD', 'beats', 'lines', 'projectionSubjects'} <= performance.keys()
    assert 'sceneId' not in performance['sceneDPD']['properties']
    assert 'sourceFingerprint' not in performance['sceneDPD']['properties']
    assert 'speaker' not in performance['lines']['items']['properties']
    assert 'physicalExpression' in performance['beats']['items']['required']
    assert set(contracts) == {'ACTION', 'CAMERA', 'COLOR', 'EDITORIAL', 'LIGHTING', 'PERFORMANCE', 'REFERENCE', 'SOUND', 'SUBJECTS', 'WORLD'}


def test_professional_executable_leaves_rejected_without_filter_or_repair():
    req = request('professional')
    malformed = DesignBody(domain='LIGHTING', facts={'source': 'old flat', 'direction': 'old flat'})
    with pytest.raises(AuthorResultFailure) as caught:
        validate_professional_facts((malformed,), req)
    assert caught.value.diagnostic.code == 'PROFESSIONAL_EXECUTABLE_FACTS_INVALID'
    assert caught.value.diagnostic.issues[0].field_path == (0, 'facts', 'sources')
    assert malformed.facts == {'source': 'old flat', 'direction': 'old flat'}
    valid = DesignBody(domain='LIGHTING', facts={'sources': ['practical'], 'directionAndQuality': 'side'})
    validate_professional_facts((valid,), req)


def performance_fixture():
    baseline = {'objective': 'Ask for the approved shelter', 'interactionTarget': 'The closed door',
        'tactic': 'Make the approved appeal', 'authorityPosition': 'Requester', 'relationshipStance': 'Unanswered appeal',
        'internalActivation': 'MEDIUM', 'externalControl': 'HIGH', 'publicPrivateContext': 'At the visible doorway'}
    return {'sceneDPD': {'dramaticPurpose': 'Observe the approved appeal', 'conflictCondition': 'The door stays closed',
        'powerStructure': 'The caller cannot open the door', 'direction': baseline},
        'beats': [{'id': 'appeal-beat', 'actor': 'traveler', 'target': 'The closed door',
            'objective': 'Ask for the approved shelter', 'obstacle': 'Closed door', 'tactic': 'Call once',
            'note': 'Remain within the approved action', 'transitionTrigger': 'The call becomes waiting',
            'direction': {'tactic': 'Call once'}, 'physicalExpression': 'The caller faces the closed door'}],
        'lines': [{'spokenContentId': 'appeal', 'beatId': 'appeal-beat', 'dramaticAction': 'Appeal',
            'observableIntent': 'Direct the appeal to the closed door', 'continuity': 'The caller stays at the door',
            'changeFromPrevious': 'The call ends in waiting'}],
        'projectionSubjects': [{'subjectRef': 'traveler', 'sourceTargetLabel': 'traveler', 'role': 'INTERACTIVE_PARTNER',
            'beatIds': ['appeal-beat'], 'spokenIds': ['appeal']}]}


@pytest.mark.parametrize('fault', ('none', 'missing_baseline', 'wrong_line', 'wrong_phase', 'bad_destination', 'model_scene_id'))
def test_complete_professional_dpd_and_source_scope_validate_at_producer(fault):
    from test_formal_author_backends import shot
    req = request('professional').model_copy(update={'shot': shot().model_copy(update={
        'professional_domains': ('ACTION', 'PERFORMANCE')})})
    facts = performance_fixture()
    action = {'actionPhases': [{'beatId': 'appeal-beat', 'action': 'The caller waits at the closed door',
        'entryState': 'At the closed door', 'observable': 'Still at the closed door', 'spokenIds': []}]}
    if fault == 'missing_baseline': facts['sceneDPD']['direction'].pop('objective')
    elif fault == 'wrong_line': facts['lines'][0]['spokenContentId'] = 'unapproved-line'
    elif fault == 'wrong_phase': action['actionPhases'][0]['spokenIds'] = ['unapproved-line']
    elif fault == 'bad_destination':
        facts['projectionSubjects'][0].update(role='NON_INTERACTIVE_DESTINATION', spatialPresenceOnly=True, behaviorExpansionForbidden=True)
    elif fault == 'model_scene_id': facts['sceneDPD']['sceneId'] = 'MODEL-GUESSED-AUTHORITY'
    designs = (DesignBody(domain='ACTION', facts=action), DesignBody(domain='PERFORMANCE', facts=facts))
    if fault == 'none':
        validate_professional_facts(designs, req)
    else:
        with pytest.raises(AuthorResultFailure) as caught:
            validate_professional_facts(designs, req)
        assert caught.value.diagnostic.recovery_class == RecoveryClass.RETRY_SAME_STEP
        assert 'MODEL-GUESSED-AUTHORITY' not in caught.value.diagnostic.model_dump_json()


async def test_pre_adoption_metadata_reconciliation_is_automatic_and_keeps_creative_bytes(tmp_path, monkeypatch):
    from test_creative_engine import Authors, SOURCE, plugin
    from drama_plugin.professional_design import provenance
    from drama_plugin.creative_engine.contracts import CreativeCheckpoint
    from drama_plugin.config import DramaPluginConfig
    monkeypatch.setattr('drama_plugin.plugin.load_config', lambda _: DramaPluginConfig())
    authors = Authors()
    p = plugin(tmp_path, authors)
    run = p.create_film_run(work_id='auto-integrity', mode=RunMode.PRODUCTION, source=SOURCE)
    ready = await p.runtime.run(run.run_id, max_ticks=6)
    assert ready.state == RuntimeState.READY and ready.cursor == 5
    cp = p.creative.state.checkpoint(run.run_id)
    original = next(r for r in cp.refs if p.creative_versions.resolve(r).kind == Kind.PROFESSIONAL)
    version = p.creative_versions.resolve(original)
    facts = json.loads(json.dumps(version.body.facts))
    facts['sourcePins'][0]['identity'] = 'malformed-historical-metadata'
    # Historical fixture only. Actual current owner refuses all malformed pins.
    with monkeypatch.context() as historic:
        historic.setattr(provenance, 'validate_metadata', lambda *args, **kwargs: None)
        historic.setattr(provenance, 'project_metadata', lambda design, *args: design)
        bad = p.creative_versions.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL,
            scope=run.scope, body=DesignBody(domain=version.body.domain, facts=facts), sources=version.source_refs,
            operation='historical-owned-metadata')
    fixed_refs = tuple(bad if ref == original else ref for ref in cp.refs)
    p.creative.state.save(run.run_id, run.scope, CreativeCheckpoint.model_validate({**cp.model_dump(), 'refs': fixed_refs}))
    calls = authors.calls[:]
    waiting = await p.runtime.run(run.run_id)
    assert waiting.state == RuntimeState.WAITING_USER and waiting.cursor == 6 and authors.calls == calls
    revised = p.creative.state.checkpoint(run.run_id)
    p.creative.validate_candidate_integrity(revised, run.scope)
    exact = next(p.creative_versions.resolve(ref) for ref in revised.refs if
        p.creative_versions.resolve(ref).kind == Kind.PROFESSIONAL and p.creative_versions.resolve(ref).body.domain == version.body.domain)
    assert exact.version == bad.version + 1 and p.creative_versions.resolve(bad).body.facts == facts
    assert provenance.creative_facts(exact.body.facts) == provenance.creative_facts(version.body.facts)
    assert revised.decision_ref is None and revised.package_ref is None
    await p.aclose()


@pytest.mark.parametrize('finish', ('tool_calls', 'content_filter'))
async def test_refusal_or_unsupported_finish_is_hard_and_never_calls_again(monkeypatch, tmp_path, finish):
    p = configured(monkeypatch, tmp_path)
    calls = []
    p.creative.canon_author.client.transport = httpx.MockTransport(lambda req: calls.append(req) or
        observed_wire(json.dumps(model_output('canon')), finish=finish))
    run = p.create_film_run(work_id='unsupported-finish', mode=RunMode.PRODUCTION, source=source())
    failed = await p.runtime.run(run.run_id)
    assert failed.state == RuntimeState.FAILED and failed.last_result.recovery_class == RecoveryClass.HARD_BLOCK
    assert len(calls) == 1
    await p.aclose()


def test_reference_model_projection_preserves_professional_and_shot_authority():
    from test_formal_author_backends import shot
    req = request('professional').model_copy(update={'shot': shot().model_copy(update={
        'professional_domains': ('REFERENCE',)})})
    design = DesignBody(domain='REFERENCE', facts={'references': [{'id': 'door-study', 'priority': 'REQUIRED',
        'beatIds': ['appeal-beat'], 'designPurpose': 'Check approved door presence', 'inputDuty': 'Visual reference'}]})
    validate_professional_facts((design,), req)
    schema = professional_model_schema()['$defs']['DesignBody']['allOf']
    facts = next(row['then']['properties']['facts'] for row in schema if row['if']['properties']['domain']['const'] == 'REFERENCE')
    fields = facts['properties']['references']['items']['properties']
    assert 'designPurpose' in fields and 'purpose' not in fields
    with pytest.raises(ValueError, match='authority violation'):
        DesignBody(domain='REFERENCE', facts={'references': [{'purpose': 'Re-author Shot purpose'}]})


async def test_silent_performance_beat_is_valid_without_spoken_snapshot():
    from test_formal_author_backends import shot
    req = request('professional').model_copy(update={'shot': shot().model_copy(update={
        'spoken_ids': (), 'professional_domains': ('PERFORMANCE',)})})
    facts = performance_fixture()
    facts['lines'] = []
    facts['projectionSubjects'][0]['spokenIds'] = []
    design = DesignBody(domain='PERFORMANCE', facts=facts)
    validate_professional_facts((design,), req)
