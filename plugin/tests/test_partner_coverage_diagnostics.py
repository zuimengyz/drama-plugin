"""Exact Professional coverage diagnostics; offline author wire and temporary owners."""
import copy
import json
from collections import Counter

import httpx
import pytest

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.backends import (FormalProfessionalAuthor,
    TextCompositionBackend, professional_model_schema, validate_professional_facts)
from drama_plugin.creative_engine.contracts import DesignBody
from drama_plugin.creative_engine.diagnostics import (AuthorDiagnostic, AuthorResultFailure,
    previous_diagnostic, response_context, retain_author_diagnostic)
from drama_plugin.production.contracts import SourceDomain
from drama_plugin.runtime.contracts import (ArtifactReference, CapabilityInput, CapabilityResult,
    ExecutionRevision, ExhaustedExecutionEvidence, RecoveryClass, RepairResumeRecord,
    ResultStatus, RunMode, RuntimeState)
from test_formal_author_backends import ENV, SKILLS, configured, model_output, request, response, source
from test_unified_author_recovery import diagnostics, observed_wire, performance_fixture


def performance_request():
    original = request('professional')
    return original.model_copy(update={'shot': original.shot.model_copy(update={
        'professional_domains': (SourceDomain.PERFORMANCE,)})})


def coverage_fault(reason):
    facts = performance_fixture()
    if reason == 'BEAT_ACTOR_MISSING':
        missing = copy.deepcopy(facts['beats'][0])
        missing.update(id='uncovered-beat', actor='uncovered-actor',
            note='RAW-PROFESSIONAL-FACT-MUST-NOT-RETAIN')
        facts['beats'].append(missing)
    elif reason == 'CANON_SPEAKER_MISSING':
        # The silent Beat actor is fully covered. Only the exact Canon speaker
        # remains missing, isolating the existing second coverage check.
        facts['beats'][0]['actor'] = 'silent-actor'
        facts['projectionSubjects'] = [{
            'subjectRef': 'silent-actor', 'sourceTargetLabel': 'silent-actor',
            'role': 'INTERACTIVE_PARTNER', 'beatIds': ['appeal-beat'], 'spokenIds': []}]
    else:
        raise AssertionError(reason)
    return facts


@pytest.mark.parametrize('reason,subject_id,beat_id,spoken_id', (
    ('BEAT_ACTOR_MISSING', 'uncovered-actor', 'uncovered-beat', None),
    ('CANON_SPEAKER_MISSING', 'traveler', None, 'appeal'),
))
def test_coverage_failure_names_exact_validator_facts_without_semantic_repair(
        reason, subject_id, beat_id, spoken_id):
    req = performance_request()
    facts = coverage_fault(reason)
    before = copy.deepcopy(facts)
    canonical_before = req.canon.model_dump()
    design = DesignBody(domain='PERFORMANCE', facts=facts)
    with pytest.raises(AuthorResultFailure) as caught:
        validate_professional_facts((design,), req)
    diagnostic = caught.value.diagnostic
    assert diagnostic.failure_stage == 'DTO_SCHEMA'
    assert diagnostic.code == 'PROFESSIONAL_PARTNER_DPD_REQUIRED'
    assert diagnostic.validator == 'FormalProfessionalAuthor.interactive_coverage'
    assert diagnostic.issues[0].field_path == ('facts', 'projectionSubjects')
    assert diagnostic.reason == reason
    assert diagnostic.missing_subject_id == subject_id
    assert diagnostic.beat_id == beat_id
    assert diagnostic.spoken_id == spoken_id
    assert diagnostic.expected_coverage_role == 'INTERACTIVE_PARTNER'
    assert diagnostic.recovery_class == RecoveryClass.RETRY_SAME_STEP
    assert facts == before and design.facts == before
    assert req.canon.model_dump() == canonical_before


@pytest.mark.parametrize('coverage_fault_kind', ('wrong_role', 'missing_beat_membership'))
def test_existing_beat_role_and_membership_rules_still_reject(coverage_fault_kind):
    req = performance_request()
    facts = performance_fixture()
    if coverage_fault_kind == 'wrong_role':
        facts['projectionSubjects'][0].update(role='NON_INTERACTIVE_DESTINATION',
            spokenIds=[], spatialPresenceOnly=True, behaviorExpansionForbidden=True)
    else:
        another = copy.deepcopy(facts['beats'][0])
        another['id'] = 'another-beat'
        facts['beats'].append(another)
        facts['projectionSubjects'][0]['beatIds'] = ['another-beat']
    before = copy.deepcopy(facts)
    with pytest.raises(AuthorResultFailure) as caught:
        validate_professional_facts((DesignBody(domain='PERFORMANCE', facts=facts),), req)
    diagnostic = caught.value.diagnostic
    assert diagnostic.code == 'PROFESSIONAL_PARTNER_DPD_REQUIRED'
    assert diagnostic.reason == 'BEAT_ACTOR_MISSING'
    assert diagnostic.missing_subject_id == 'traveler'
    assert diagnostic.beat_id == 'appeal-beat'
    assert diagnostic.expected_coverage_role == 'INTERACTIVE_PARTNER'
    assert facts == before


def test_valid_professional_coverage_still_passes_unchanged():
    req = performance_request()
    facts = performance_fixture()
    before = copy.deepcopy(facts)
    validate_professional_facts((DesignBody(domain='PERFORMANCE', facts=facts),), req)
    assert facts == before


@pytest.mark.parametrize('reason,subject_id,beat_id,spoken_id', (
    ('BEAT_ACTOR_MISSING', 'uncovered-actor', 'uncovered-beat', None),
    ('CANON_SPEAKER_MISSING', 'traveler', None, 'appeal'),
))
async def test_exact_coverage_fields_reach_existing_safe_retry_feedback_and_diagnostics(
        monkeypatch, tmp_path, reason, subject_id, beat_id, spoken_id):
    plugin = configured(monkeypatch, tmp_path)
    role_models = {ENV['DRAMA_PLUGIN_' + role.upper() + '_AUTHOR_MODEL']: role
        for role in ('canon', 'direction', 'professional')}
    calls = Counter()
    requests = []

    def handle(http_request):
        payload = json.loads(http_request.content)
        role = role_models[payload['model']]
        calls[role] += 1
        requests.append((role, payload))
        if role == 'direction':
            output = model_output(role)
            output['professionalDomains'] = ['PERFORMANCE']
            return response(output)
        from test_creative_chain_reconciliation import canon_dto, professional_dto, raw_response
        if role == 'professional':
            dto=next(row for row in professional_dto() if row['domain']=='PERFORMANCE')
            if calls[role]==1:
                if reason=='BEAT_ACTOR_MISSING':
                    dto['facts']['beats'][0]['actorSelection']=1
                    dto['facts']['lines'][0]['beatSelection']=1
                else:
                    for beat in dto['facts']['beats']:beat['actorSelection']=1
                    dto['facts']['projectionSubjects'][0]['subjectSelection']=1
            return raw_response([dto])
        dto=canon_dto();dto['scene']['subjects'].append({'name':'partner','meaning':'Canonical listener.'})
        return raw_response(dto)

    plugin.creative.canon_author.client.transport = httpx.MockTransport(handle)
    run = plugin.create_film_run(work_id='exact-professional-coverage-' + reason.lower(),
        mode=RunMode.PRODUCTION, source=source())
    result = await plugin.runtime.run(run.run_id)
    assert result.state == RuntimeState.WAITING_USER and result.cursor == 6
    assert calls == Counter({'canon': 1, 'direction': 1, 'professional': 2})
    records = diagnostics(plugin)
    assert len(records) == 1
    diagnostic = records[0]['diagnostic']
    from drama_plugin.creative_engine.author_projection import identity
    from drama_plugin.creative_engine.contracts import Kind
    fixed_scene=next(v for v in plugin.creative_versions.versions() if v.kind==Kind.SCENE).body
    subject_id=fixed_scene.subjects[1 if reason=='BEAT_ACTOR_MISSING' else 0].id
    beat_id=identity('beat',[run.scope.work_id,run.scope.scene_id,run.scope.shot_id],0) if reason=='BEAT_ACTOR_MISSING' else None
    spoken_id=None if reason=='BEAT_ACTOR_MISSING' else fixed_scene.dialogue[0].id
    assert diagnostic['reason'] == reason
    assert diagnostic['missing_subject_id'] == subject_id
    assert diagnostic['beat_id'] == beat_id
    assert diagnostic['spoken_id'] == spoken_id
    assert diagnostic['expected_coverage_role'] == 'INTERACTIVE_PARTNER'
    assert diagnostic['response_hash'] and diagnostic['finish_reason'] == 'stop'
    assert diagnostic['attempt'] == 1
    assert diagnostic['execution_fingerprint'] == diagnostic['execution_revision']
    serialized = json.dumps(records)
    assert all(secret not in serialized for secret in (
        'RAW-PROFESSIONAL-FACT-MUST-NOT-RETAIN', 'HIDDEN_REASONING_MUST_NOT_RETAIN',
        ENV['DRAMA_PLUGIN_TEXT_COMPOSITION_API_KEY'], 'authorization', 'reasoning_content'))
    retry = [payload for role, payload in requests if role == 'professional'][1]
    feedback = json.loads(retry['messages'][2]['content'].split('\n', 1)[1])
    assert feedback['reason'] == reason
    assert feedback['missingSubjectSelection'] == (1 if reason=='BEAT_ACTOR_MISSING' else 0)
    assert feedback.get('beatSelection') == (0 if beat_id is not None else None)
    assert feedback.get('spokenSelection') == (0 if spoken_id is not None else None)
    assert subject_id not in retry['messages'][2]['content']
    assert feedback['expectedCoverageRole'] == 'INTERACTIVE_PARTNER'
    assert 'do not patch or quote prior output' in retry['messages'][2]['content']
    assert 'RAW-PROFESSIONAL-FACT-MUST-NOT-RETAIN' not in retry['messages'][2]['content']
    assert 'HIDDEN_REASONING' not in retry['messages'][2]['content']
    await plugin.aclose()


def test_prose_actor_and_beat_labels_are_not_fabricated_as_diagnostic_ids():
    req = performance_request()
    facts = coverage_fault('BEAT_ACTOR_MISSING')
    facts['beats'][1].update(actor='Private prose actor label', id='Private prose beat label')
    before = copy.deepcopy(facts)
    with pytest.raises(AuthorResultFailure) as caught:
        validate_professional_facts((DesignBody(domain='PERFORMANCE', facts=facts),), req)
    diagnostic = caught.value.diagnostic
    assert diagnostic.code == 'PROFESSIONAL_PARTNER_DPD_REQUIRED'
    assert diagnostic.reason == 'BEAT_ACTOR_MISSING'
    assert diagnostic.role == 'professional'
    assert diagnostic.missing_subject_id is None and diagnostic.beat_id is None
    assert diagnostic.expected_coverage_role == 'INTERACTIVE_PARTNER'
    assert 'Private prose' not in diagnostic.model_dump_json()
    assert facts == before


async def test_repair_feedback_accepts_only_exact_exhausted_diagnostic_and_revision(monkeypatch, tmp_path):
    plugin = configured(monkeypatch, tmp_path)
    run = plugin.create_film_run(work_id='repair-safe-feedback', mode=RunMode.PRODUCTION, source=source())
    inputs = CapabilityInput(run_id=run.run_id, operation_id=run.run_id + ':0', scope=run.scope)
    authority_hash = sha256_canonical('fixed-source-and-canon-refs')
    old = ExecutionRevision(fingerprint=sha256_canonical('old-implementation'), input_fingerprint=authority_hash)
    current = ExecutionRevision(fingerprint=sha256_canonical('diagnostic-repaired-implementation'), input_fingerprint=authority_hash)
    diagnostic = AuthorDiagnostic(role='professional', failure_stage='DTO_SCHEMA',
        code='PROFESSIONAL_PARTNER_DPD_REQUIRED', validator='FormalProfessionalAuthor.interactive_coverage',
        execution_fingerprint=old.fingerprint, reason='BEAT_ACTOR_MISSING',
        missing_subject_id='uncovered-actor', beat_id='uncovered-beat', expected_coverage_role='INTERACTIVE_PARTNER')
    exact_ref = retain_author_diagnostic(plugin.creative_versions, inputs, diagnostic,
        author_round=2, version_refs=())
    repair = RepairResumeRecord(cursor=0, capability_key='creative.professional:v1',
        exhausted=ExhaustedExecutionEvidence(revision=old, historical_attempts=2, evidence_ref=exact_ref),
        current=current)
    pending = run.model_copy(update={'execution_revision': current,
        'repair_resumes': (repair,), 'last_result': CapabilityResult(
            status=ResultStatus.RETRYABLE_FAILURE, code='CAPABILITY_EXECUTION_ERROR', artifact_refs=(exact_ref,))})
    assert previous_diagnostic(plugin.creative_versions, inputs, pending) == diagnostic
    wrong_ref = ArtifactReference(owner='creative-diagnostic',
        artifact_ref='author-diagnostic:' + sha256_canonical('other-evidence'), version=1)
    wrong_evidence = repair.model_copy(update={'exhausted': repair.exhausted.model_copy(update={'evidence_ref': wrong_ref})})
    assert previous_diagnostic(plugin.creative_versions, inputs,
        pending.model_copy(update={'repair_resumes': (wrong_evidence,)})) is None
    wrong_revision = repair.model_copy(update={'exhausted': repair.exhausted.model_copy(update={
        'revision': old.model_copy(update={'fingerprint': sha256_canonical('wrong-old-revision')})})})
    assert previous_diagnostic(plugin.creative_versions, inputs,
        pending.model_copy(update={'repair_resumes': (wrong_revision,)})) is None
    assert previous_diagnostic(plugin.creative_versions, inputs,
        pending.model_copy(update={'repair_resumes': ()})) is None

    # Existing diagnostic artifacts without new optional fields remain readable;
    # they do not acquire a guessed subject, beat or reason during recovery.
    old_body = diagnostic.model_dump(mode='json', exclude={
        'reason', 'missing_subject_id', 'beat_id', 'spoken_id', 'expected_coverage_role'})
    restored = AuthorDiagnostic.model_validate(old_body)
    assert restored.code == diagnostic.code
    assert restored.reason is None and restored.missing_subject_id is None and restored.beat_id is None
    await plugin.aclose()


async def test_professional_diagnostic_revision_matches_request_without_creative_contract_drift():
    from drama_plugin.config.loader import load_config
    config = load_config(environment=ENV).text_composition
    captured = []
    req = performance_request()
    output = [DesignBody(domain='PERFORMANCE', facts=performance_fixture()).model_dump(mode='json', by_alias=True)]

    def handle(http_request):
        captured.append(json.loads(http_request.content))
        return response(output)

    client = TextCompositionBackend(config, transport=httpx.MockTransport(handle))
    author = FormalProfessionalAuthor(client, SKILLS)
    schema = professional_model_schema()
    system = author.system_contract(req)
    inspected = author.execution_fingerprint(req)
    token = response_context.set(None)
    try:
        result = await author.design(req)
        diagnostic = response_context.get()
    finally:
        response_context.reset(token)
    from author_model_helpers import model_dto
    from drama_plugin.creative_engine.author_projection import professional_projection
    assert result[0].facts == professional_projection(model_dto(output),req)[0]['facts']
    assert diagnostic.execution_fingerprint == inspected
    wire_system = captured[0]['messages'][0]['content']
    assert inspected == client.execution_fingerprint('professional', author.implementation_identity, wire_system)
    old_identity = 'creative.professional:v1:FormalProfessionalAuthor'
    assert inspected != client.execution_fingerprint('professional', old_identity, wire_system)
    assert author.system_contract(req) == system and professional_model_schema() == schema
    assert captured[0]['model'] == config.professional_model
    assert captured[0]['max_tokens'] == config.max_output_tokens
    assert config.api_key.get_secret_value() not in inspected
