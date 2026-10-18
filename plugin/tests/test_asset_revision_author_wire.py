"""Asset revision wire regression only; no evidence of model creativity or media."""
import json
from pathlib import Path

import httpx
import pytest

from drama_plugin.config.text_composition import TextCompositionConfig
from drama_plugin.creative_engine.backends import FormalProfessionalAuthor, TextCompositionBackend
from drama_plugin.creative_engine.contracts import AuthorRequest, Authority, RevisionRequest, VersionRef
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope
from test_formal_author_backends import canon, source
from test_target_reference_production import reference_frame


@pytest.mark.asyncio
async def test_scene_asset_revision_reaches_configured_author_without_shot_projection():
    calls = []

    def receive(request):
        wire = json.loads(request.content)
        calls.append(wire)
        payload = json.loads(wire['messages'][1]['content'])
        assert payload['revisionInstruction'] == 'Reassess the requested proof, retaining identity.'
        assert payload['assetPreparation']['sceneOrdinal'] == 0
        assert 'visualContinuity' not in payload
        assert len(wire['messages']) == 2  # No Shot revision task or guessed Shot.
        assert wire['model'] == 'offline-professional-model'
        assert 'tools' not in wire
        # Fixture outcome checks only transport/parsing, not aesthetic adequacy.
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': json.dumps({
                'assets': [], 'rationale': 'Offline empty result for wire isolation only.'})}}]})

    cfg = TextCompositionConfig(provider='offline', base_url='https://author.invalid/v1',
        api_key='offline-secret', professional_model='offline-professional-model')
    author = FormalProfessionalAuthor(TextCompositionBackend(cfg, transport=httpx.MockTransport(receive)),
        Path(__file__).resolve().parents[1] / 'skills')
    request = AuthorRequest(scope=RuntimeScope(work_id='offline', scene_id='scene'),
        source=source(), source_refs=(), canon=canon(), shot=None,
        revision=RevisionRequest(owner=Authority.PROFESSIONAL,
            target_ref=VersionRef(identity='offline-parent', version=1, fingerprint='a' * 64),
            finding_ref=ArtifactReference(owner='art-review', artifact_ref='offline-proof-review'),
            instruction='Reassess the requested proof, retaining identity.'),
        professional_context={'assetPreparation': {'sceneOrdinal': 0,
            'subjectCandidates': [], 'assetCandidates': []}})
    result = await author.design_assets(request)
    assert result.assets == () and len(calls) == 1


@pytest.mark.asyncio
async def test_retained_artwork_is_candidate_evidence_without_machine_or_new_frame_prefill():
    pin = {'key': 'offline-parent', 'kind': 'DIRECTION', 'fingerprint': 'b' * 64}
    item = {'assetType': 'CHARACTER', 'name': 'A', 'subjectId': 'owner-only-subject-id',
        'designRef': pin, 'design': {'face': 'Approved individual A'}}
    prior = reference_frame(item)
    parent = {'id': 'owner-only-asset-id', 'assetType': 'CHARACTER', 'name': 'A',
        'content': {'specializedAsset': {'design': item['design']}}}
    calls = []

    def receive(request):
        wire = json.loads(request.content)
        payload = json.loads(wire['messages'][1]['content'])
        candidate = payload['assetPreparation']['assetCandidates'][0]['referenceArtworkCandidate']
        assert candidate['composition'] == prior.composition
        assert candidate['prompt_ir']['lighting']['light_sources']['text'] == prior.prompt_ir['lighting']['light_sources']['text']
        encoded = json.dumps(payload)
        for machine in ('owner-only-subject-id', 'owner-only-asset-id', 'source_fingerprint', 'provider_family', 'reference_lock'):
            assert machine not in encoded
        skills = Path(__file__).resolve().parents[1] / 'skills'
        assert (skills / 'specialized-asset-design/SKILL.md').read_text() in wire['messages'][0]['content']
        assert (skills / 'reference-strategy/SKILL.md').read_text() in wire['messages'][0]['content']
        calls.append(wire)
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'role': 'assistant', 'content': json.dumps({'assets': [], 'rationale': 'Wire fixture only.'})}}]})

    cfg = TextCompositionConfig(provider='offline', base_url='https://author.invalid/v1',
        api_key='offline-secret', professional_model='offline-professional-model')
    author = FormalProfessionalAuthor(TextCompositionBackend(cfg, transport=httpx.MockTransport(receive)),
        Path(__file__).resolve().parents[1] / 'skills')
    request = AuthorRequest(scope=RuntimeScope(work_id='offline', scene_id='scene'),
        source=source(), source_refs=(), canon=canon(),
        revision=RevisionRequest(owner=Authority.PROFESSIONAL,
            target_ref=VersionRef(identity='offline-parent', version=1, fingerprint='a' * 64),
            finding_ref=ArtifactReference(owner='art-review', artifact_ref='offline-proof-review'),
            instruction='Reassess the selected viewing plan.'),
        professional_context={'assetPreparation': {'sceneOrdinal': 0, 'subjectCandidates': [],
            'assetCandidates': [{'selection': 0, 'asset': parent}]},
            'currentDesigns': [{'domain': 'REFERENCE', 'facts': {'assetId': parent['id'],
                'frame': prior.model_dump(mode='json')}}]})
    result = await author.design_assets(request)
    assert result.assets == () and len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('parent_selection', [0, 9])
async def test_existing_character_parent_uniquely_binds_subject_without_editing_art(parent_selection):
    """Regression for a real result: reuse selection already identifies the person."""
    raw = {'assets': [{'assetType': 'CHARACTER', 'name': 'A', 'reuseSelection': parent_selection,
        'design': {'proof': 'Authored candidate view, unchanged by identity projection.'},
        'variantReason': 'Review the existing proof.'}], 'rationale': 'Fixture authored reason.'}
    content = json.dumps(raw)

    def receive(request):
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'role': 'assistant', 'content': content}}]})

    cfg = TextCompositionConfig(provider='offline', base_url='https://author.invalid/v1',
        api_key='offline-secret', professional_model='offline-professional-model')
    author = FormalProfessionalAuthor(TextCompositionBackend(cfg, transport=httpx.MockTransport(receive)),
        Path(__file__).resolve().parents[1] / 'skills')
    parent = {'id': 'approved-A', 'assetType': 'CHARACTER', 'name': 'A',
        'content': {'specializedAsset': {'subjectId': 'known-A', 'design': {'identity': 'Approved A'}}}}
    request = AuthorRequest(scope=RuntimeScope(work_id='offline', scene_id='scene'),
        source=source(), source_refs=(), canon=canon(),
        professional_context={'assetPreparation': {'sceneOrdinal': 0,
            'subjectCandidates': [{'selection': 3, 'id': 'known-A', 'name': 'A',
                'meaning': 'Existing person', 'inherited': parent}],
            'assetCandidates': [{'selection': 0, 'asset': parent}]}})
    if parent_selection == 0:
        result = await author.design_assets(request)
        assert result.assets[0].subject_selection == 3
        assert result.assets[0].reuse_selection == parent_selection
        assert result.assets[0].design == raw['assets'][0]['design']
        assert result.rationale == raw['rationale']
    else:
        with pytest.raises(AuthorResultFailure):
            await author.design_assets(request)
    assert json.dumps(raw) == content and 'subjectSelection' not in raw['assets'][0]



@pytest.mark.asyncio
async def test_character_reference_wire_requires_existing_single_actor_contract():
    """Real 02 omitted actors: disclose the existing duty before authorship.

    The empty response deliberately fails; this test verifies neither creative
    quality nor recovery of the recorded real result.
    """
    seen = []

    def receive(request):
        wire = json.loads(request.content)
        schema = json.loads(wire['messages'][0]['content'].split('\nOutput JSON schema:\n')[-1])
        assert 'actors' in schema['required']
        assert schema['properties']['actors']['minItems'] == 1
        assert schema['properties']['actors']['maxItems'] == 1
        subjects = schema['properties']['prompt_ir']['properties']['subjects']
        assert subjects['minItems'] == subjects['maxItems'] == 1
        assert {'subjects', 'blocking', 'action'} <= set(schema['properties']['prompt_ir']['required'])
        for key in ('blocking', 'action'):
            assert '$ref' in schema['properties']['prompt_ir']['properties'][key]
        assert 'entity_key' not in schema['$defs']['Actor']['properties']
        assert 'id' not in schema['$defs']['Subject']['properties']
        critical = schema['$defs']['ReferenceCurrentCriticalFact']['properties']
        important = schema['$defs']['ReferenceCurrentImportantFact']['properties']
        assert critical['priority']['enum'] == ['CRITICAL']
        assert critical['scope']['const'] == important['scope']['const'] == 'CURRENT'
        assert important['priority']['enum'] == ['CRITICAL', 'IMPORTANT']
        for key in ('era', 'location', 'historical_context'):
            assert schema['$defs']['World']['properties'][key]['$ref'].endswith('CriticalFact')
        assert schema['$defs']['World']['properties']['environment_rules']['items']['$ref'].endswith('CriticalFact')
        for key in ('continuity', 'preserve'):
            assert schema['properties']['prompt_ir']['properties'][key]['items']['$ref'].endswith('CriticalFact')
        seen.append(wire)
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'role': 'assistant', 'content': json.dumps({'prompt_ir': {'subjects': [{}]}})}}]})

    cfg = TextCompositionConfig(provider='offline', base_url='https://author.invalid/v1',
        api_key='offline-secret', professional_model='offline-professional-model')
    author = FormalProfessionalAuthor(TextCompositionBackend(cfg, transport=httpx.MockTransport(receive)),
        Path(__file__).resolve().parents[1] / 'skills')
    item = {'assetType': 'CHARACTER', 'name': 'A', 'subjectId': 'known-A',
        'designRef': {'key': 'approved-A', 'kind': 'DIRECTION', 'fingerprint': 'a' * 64},
        'design': {'identity': 'Approved A'}, 'variantReason': 'Reference proof.'}
    request = AuthorRequest(scope=RuntimeScope(work_id='offline', scene_id='scene'),
        source=source(), source_refs=(), canon=canon())
    with pytest.raises(AuthorResultFailure):
        await author.design_asset_reference(request, item)
    assert len(seen) == 1  # No filled Actor and no automatic model retry.


@pytest.mark.asyncio
async def test_reference_wire_matches_compiler_scope_and_priority_without_rewriting_result():
    """Contract examples only, not synthetic substitutes for real author results."""
    from copy import deepcopy
    from jsonschema import Draft202012Validator, ValidationError as SchemaError

    item = {'assetType': 'CHARACTER', 'name': 'A', 'subjectId': 'known-A',
        'designRef': {'key': 'approved-A', 'kind': 'DIRECTION', 'fingerprint': 'a' * 64},
        'design': {'face': 'Approved A'}, 'variantReason': 'Reference proof.'}
    frame = reference_frame(item)
    raw = frame.model_dump(mode='json')
    for key in ('shot_id', 'shot_fingerprint', 'professional_sources', 'references',
                'reference_lock', 'reference_members', 'edit_source', 'scope_context',
                'prompt_normalization', 'identity_bootstrap', 'image_mode'):
        raw.pop(key, None)
    raw['prompt_ir'].pop('source_fingerprint')
    for key in ('provider_family', 'task_type', 'input_mode'):
        raw['prompt_ir']['task'].pop(key)
    raw['actors'][0].pop('entity_key')
    raw['prompt_ir']['subjects'][0].pop('id')
    before = deepcopy(raw)

    def receive(request):
        wire = json.loads(request.content)
        schema = json.loads(wire['messages'][0]['content'].split('\nOutput JSON schema:\n')[-1])
        validator = Draft202012Validator(schema)
        validator.validate(raw)
        for defect in ('actors', 'blocking', 'priority', 'scope'):
            invalid = deepcopy(raw)
            if defect == 'actors':
                invalid.pop('actors')
            elif defect == 'blocking':
                invalid['prompt_ir'].pop('blocking')
            else:
                invalid['prompt_ir']['world']['era'][defect] = 'IMPORTANT' if defect == 'priority' else 'CAPABILITY'
            with pytest.raises(SchemaError):
                validator.validate(invalid)
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'role': 'assistant', 'content': json.dumps(raw)}}]})

    cfg = TextCompositionConfig(provider='offline', base_url='https://author.invalid/v1',
        api_key='offline-secret', professional_model='offline-professional-model')
    author = FormalProfessionalAuthor(TextCompositionBackend(cfg, transport=httpx.MockTransport(receive)),
        Path(__file__).resolve().parents[1] / 'skills')
    request = AuthorRequest(scope=RuntimeScope(work_id='offline', scene_id='scene'),
        source=source(), source_refs=(), canon=canon())
    result = await author.design_asset_reference(request, item)
    assert result.actors[0].entity_key == item['subjectId']
    assert raw == before  # The projection did not repair a defective business response.
