"""Exact reviewed-input owner contracts; fictional text/metadata fixtures only.

No test invokes a real model, network, image generation or business storage.
Earlier fixture authors only establish source evidence. The handoff itself must
reuse that result without another author call or automatic Runtime submission.
"""
from copy import deepcopy
import socket
import subprocess

import httpx
import pytest

from drama_plugin.contracts.base import canonical_json, dump_contract, sha256_canonical as fp
from drama_plugin.creative_engine.contracts import AuthorRequest, Authority, RevisionRequest
from drama_plugin.professional_design.asset_sequence import AssetPreparationPending
from drama_plugin.professional_design.reference_production import (
    OWNER, WORKFLOW, ReferenceProductionRecord, TargetReferenceProduction,
)
from drama_plugin.runtime.contracts import ArtifactReference, RunMode, RuntimeState
from drama_plugin.visual.frame_request import FrameSpec, Reference
from drama_plugin.providers.ark_image import binding
from test_asset_sequence import accept_pending
from test_formal_asset_candidate_entry import candidate_setup
from test_target_reference_production import (
    evidence, fake_persistence, fake_submission, pass_review, prepared, reference_frame,
)
from test_visual_prompt_ir import fact


REUSE_INDEX = 'asset-reference-reuse-origin'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Candidate handoff contract tests cannot use network or subprocesses')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket.socket, 'connect_ex', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    monkeypatch.setattr(subprocess, 'Popen', denied)
    monkeypatch.setenv('DRAMA_PLUGIN_ROUTE_IMAGE_MODEL', 'Doubao-Seedream-5.0-pro')


def assets(p):
    return [dump_contract(a) for a in p.providers.asset.data.assets]


def author_counts(author):
    return (len(author.scenes), len(author.reference_requests), len(getattr(author, 'candidates', ())))


def source_frame(value):
    return FrameSpec.model_validate(deepcopy(value.frame['spec']))


def anchor_ref(p, run_id):
    # A private owner index, not another public/creative JSON contract.
    with p.ledger.transaction() as db:
        row = db.execute('SELECT value_json FROM ledger_index WHERE index_type=? AND index_key=?',
            (REUSE_INDEX, run_id)).fetchone()
    assert row is not None
    return ArtifactReference.model_validate_json(row['value_json'])


def restamp(frame, **updates):
    value = frame.model_copy(update=updates)
    ir = deepcopy(value.prompt_ir)
    ir['source_fingerprint'] = fp(value.model_dump(mode='json', exclude={'prompt_ir'}))
    return value.model_copy(update={'prompt_ir': ir})


async def selected_source(tmp_path, monkeypatch):
    p, inp, old_id, old, author = await prepared(tmp_path, monkeypatch)
    await accept_pending(p, AssetPreparationPending(old.preparation_ref))
    assert assets(p)
    return p, inp, old_id, old, author


async def candidate_source(tmp_path, monkeypatch):
    # These are explicitly synthetic prior authors, not new handoff authorship.
    p, author, request, selected, ids = await candidate_setup(tmp_path, monkeypatch)
    p.providers.memory.data.work = p.providers.memory.data.work.model_copy(update={'id': request.scope.work_id})
    candidate = await p.tools.invoke('specialized_assets.revise_assets', request=request,
        preparation_ref=selected, asset_ids=ids)
    packet = p.asset_sequence.objects.read_ref(candidate)
    parent = p.runtime.create_run(work_id=request.scope.work_id, scene_id=request.scope.scene_id,
        mode=RunMode.EXPERIMENT, run_id='offline-old-candidate-parent')
    result = await p.reference_production.pending(candidate, parent.run_id, request,
        requirement_key=packet['requirements'][0]['requirementKey'])
    old_id = next(r.artifact_ref for r in result.artifact_refs if r.owner == 'runtime')
    old = p.reference_production.get(old_id)
    assert old.frame is not None and old.required_action == 'REFERENCE_PREPARATION_NOT_SELECTED'
    return p, request, old_id, old, author


async def reuse(p, old, run_id, *, frame=None, preparation_ref=None, author_context_ref=None):
    return await p.tools.invoke('specialized_assets.prepare_reference', run_id=run_id,
        preparation_ref=preparation_ref or old.preparation_ref,
        author_context_ref=author_context_ref or old.author_context_ref,
        frame=frame or source_frame(old))


async def quote(p, run_id):
    value = p.reference_production.get(run_id)
    return await p.reference_production.quote_reference(run_id,
        quote=dict(request_fingerprint=fp(value.frame['request']), conservative_credits=1,
            unit='CNY', uncertainty=None, evidence=evidence()),
        balance=dict(available_credits=20, margin_credits=1, unit='CNY', evidence=evidence()),
        budget=2, execution_binding=binding(value.frame, evidence()))


@pytest.mark.asyncio
async def test_same_adopted_design_reuses_exact_frame_without_author_or_automatic_runtime(tmp_path, monkeypatch):
    p, inp, old_id, old, author = await selected_source(tmp_path, monkeypatch)
    before_assets, before_old, calls = assets(p), dump_contract(old), author_counts(author)
    run_id = 'offline-reviewed-reference-same-design'
    result = await reuse(p, old, run_id)
    assert result.frame == old.frame and result.preparation_ref == old.preparation_ref
    assert result.author_context_ref == old.author_context_ref
    assert result.requirement_key == old.requirement_key
    assert all(getattr(result, k) is None for k in (
        'stage', 'quote', 'balance', 'execution_binding', 'cost_ref', 'receipt',
        'delivery', 'adoption_ref', 'asset_id', 'budget'))
    run = p.runtime.store.load(run_id)
    assert run.mode == RunMode.PRODUCTION and run.workflow_id == WORKFLOW
    assert run.state == RuntimeState.PLANNED and run.cursor == 0
    origin = anchor_ref(p, run_id)
    body, scope, fingerprint = p.ledger.get_artifact(OWNER, origin)
    initial = ReferenceProductionRecord.model_validate(body)
    assert initial.artifact_reference() == origin and initial.scope == scope
    assert initial.fingerprint == fingerprint and initial.frame == old.frame
    assert initial.run_id == run_id
    assert author_counts(author) == calls and assets(p) == before_assets
    assert dump_contract(p.reference_production.get(old_id)) == before_old
    # Ordinary pending still cannot regenerate an already accepted requirement.
    request = AuthorRequest.model_validate(p.asset_sequence.objects.read_ref(old.author_context_ref))
    with pytest.raises(ValueError, match='REFERENCE_REQUIREMENT_ALREADY_ACCEPTED'):
        await p.reference_production.pending(old.preparation_ref, inp.run_id, request,
            requirement_key=old.requirement_key)
    assert author_counts(author) == calls
    assert not list(tmp_path.rglob('*.png')) and not list(tmp_path.rglob('*.mp4'))


@pytest.mark.asyncio
async def test_registered_handoff_tool_reuses_existing_input_and_record_contracts(tmp_path, monkeypatch):
    p, _, _, _, _ = await selected_source(tmp_path, monkeypatch)
    definition = p.tools.get('specialized_assets.prepare_reference')
    assert definition.input_schema['type'] == 'object'
    assert set(definition.input_schema['required']) == {
        'run_id', 'preparation_ref', 'author_context_ref', 'frame'}
    assert set(definition.input_schema['properties']) == {
        'run_id', 'preparation_ref', 'author_context_ref', 'frame'}
    assert definition.input_schema['additionalProperties'] is False
    # Freeze the public record shape: the private origin index must not grow a
    # second creative payload, approval flag, workflow or handoff field here.
    assert set(ReferenceProductionRecord.model_fields) == {
        'schema_version', 'run_id', 'scope', 'preparation_ref', 'requirement_key',
        'author_context_ref', 'frame', 'stage', 'receipt', 'delivery', 'quote',
        'balance', 'execution_binding', 'budget', 'budget_unit', 'cost_ref',
        'adoption_ref', 'asset_id', 'required_action', 'fingerprint'}
    assert set(definition.output_schema['properties']) == {
        'schemaVersion', 'runId', 'scope', 'preparationRef', 'requirementKey',
        'authorContextRef', 'frame', 'stage', 'receipt', 'delivery', 'quote',
        'balance', 'executionBinding', 'budget', 'budgetUnit', 'costRef',
        'adoptionRef', 'assetId', 'requiredAction', 'fingerprint'}


@pytest.mark.asyncio
async def test_origin_artifact_failure_rolls_back_run_and_both_indexes(tmp_path, monkeypatch):
    p, _, _, old, author = await selected_source(tmp_path, monkeypatch)
    run_id = 'offline-reviewed-atomic-create'
    before_assets, calls = assets(p), author_counts(author)
    original = p.ledger._put_artifact
    failures = []

    def fail_artifact(db, *args, **kwargs):
        # Fail after _insert_run, inside the actual owner transaction.
        assert db.execute('SELECT 1 FROM production_run WHERE run_id=?', (run_id,)).fetchone()
        failures.append(True)
        raise OSError('OFFLINE_INJECTED_ARTIFACT_FAILURE')

    monkeypatch.setattr(p.ledger, '_put_artifact', fail_artifact)
    with pytest.raises(OSError, match='OFFLINE_INJECTED_ARTIFACT_FAILURE'):
        await reuse(p, old, run_id)
    assert failures == [True]
    with pytest.raises(KeyError):
        p.runtime.store.load(run_id)
    with p.ledger.transaction() as db:
        assert db.execute('SELECT 1 FROM ledger_index WHERE index_key=?', (run_id,)).fetchone() is None
    monkeypatch.setattr(p.ledger, '_put_artifact', original)
    result = await reuse(p, old, run_id)
    assert result.frame == old.frame and anchor_ref(p, run_id) == result.artifact_reference()
    assert author_counts(author) == calls and assets(p) == before_assets


@pytest.mark.asyncio
async def test_i2i_identity_check_is_exact_and_the_new_entry_calls_it(tmp_path, monkeypatch):
    p, author, request, selected, ids = await candidate_setup(tmp_path, monkeypatch)
    original = author.design_assets

    async def explicit_i2i(value):
        draft = await original(value)
        return draft.model_copy(update={'assets': tuple(choice.model_copy(update={
            'reference_mode': 'image_to_image', 'reference_selections': (choice.reuse_selection,)})
            for choice in draft.assets)})

    monkeypatch.setattr(author, 'design_assets', explicit_i2i)
    candidate = await p.tools.invoke('specialized_assets.revise_assets', request=request,
        preparation_ref=selected, asset_ids=ids)
    packet = p.asset_sequence.objects.read_ref(candidate)
    item = next(row for row in packet['requirements'] if row['assetType'] == 'LOCATION')
    parent = await p.providers.asset.get_asset(item['inheritedFromAssetId'])
    ref = Reference(entity_key=item['stableIdentity'], kind='SCENE', asset_id=parent.id,
        media_id=parent.reference_media_ids[0], version=str(parent.content['specializedAsset']['revision']),
        content_hash='a' * 64, local_path='/OFFLINE_METADATA_ONLY/not-an-image.bin',
        upload_name='fixture-reference', uploaded_hash='a' * 64,
        upload_receipt='/OFFLINE_METADATA_ONLY/not-a-receipt.json',
        facts='Fictional adopted reference metadata only', state='Exact adopted reference', review='PASS')
    frame = reference_frame(item)
    ir = deepcopy(frame.prompt_ir)
    ir['task'].update(task_type='REFERENCE_EDIT', input_mode='reference')
    ir['preserve'] = [fact('Retain the fictional room architecture')]
    ir['edit_delta'] = [dict(operation='correct', region='reference framing',
        source_issue=fact('Fictional earlier proof framing'),
        target_correction=fact('Fictional selected proof framing'))]
    frame = restamp(frame.model_copy(update={'prompt_ir': ir}), image_mode='image_to_image',
        references=(ref,), reference_lock={f'{ref.asset_id}/{ref.media_id}/{ref.version}':ref.content_hash})
    from drama_plugin.professional_design.reference_design import inherit_design
    frame = inherit_design(frame, item)
    TargetReferenceProduction.validate_reference_inputs(frame, (ref,))
    for key, wrong in (
            ('entity_key', 'another-identity'), ('kind', 'PROP'), ('asset_id', 'another-asset'),
            ('media_id', 'another-media'), ('version', '999'), ('content_hash', 'b' * 64)):
        with pytest.raises(ValueError, match='REFERENCE_ADOPTED_INPUT_IDENTITY_CHANGED'):
            TargetReferenceProduction.validate_reference_inputs(frame, (ref.model_copy(update={key: wrong}),))
    with pytest.raises(ValueError, match='REFERENCE_ADOPTED_INPUT_IDENTITY_CHANGED'):
        TargetReferenceProduction.validate_reference_inputs(frame, ())
    observed = []

    async def current_input_metadata(actual_item, work_id):
        assert actual_item['requirementKey'] == item['requirementKey']
        assert work_id == packet['workId']
        observed.append(True)
        # Stop at exact identity validation, before Compiler can read any file.
        return (ref.model_copy(update={'media_id': 'different-adopted-input'}),)

    monkeypatch.setattr(p.reference_production, 'reference_inputs_item', current_input_metadata)
    context = p.asset_sequence.objects.put('offline-i2i-source-context', packet['referenceAuthorContext'])
    calls = author_counts(author)
    run_id = 'offline-reviewed-i2i-mismatch'
    with pytest.raises(ValueError, match='REFERENCE_ADOPTED_INPUT_IDENTITY_CHANGED'):
        await p.reference_production.prepare_reference(run_id, candidate, context, frame)
    assert observed == [True] and author_counts(author) == calls
    with pytest.raises(KeyError):
        p.runtime.store.load(run_id)


@pytest.mark.asyncio
async def test_unoccupied_location_cannot_import_a_character_through_reuse(tmp_path, monkeypatch):
    p, _, _, old, author = await selected_source(tmp_path, monkeypatch)
    packet = p.asset_sequence.objects.read_ref(old.preparation_ref)
    item = next(row for row in packet['requirements'] if row['assetType'] == 'LOCATION')
    empty = reference_frame(item)
    person = source_frame(old)
    ir = deepcopy(empty.prompt_ir)
    for key in ('subjects', 'blocking', 'action'):
        ir[key] = deepcopy(person.prompt_ir[key])
    mixed = restamp(empty.model_copy(update={'prompt_ir': ir}), actors=person.actors)
    calls, run_id = author_counts(author), 'offline-reviewed-location-must-be-empty'
    with pytest.raises(ValueError, match='NON_CHARACTER_REFERENCE_MUST_NOT_INVENT_PEOPLE'):
        await reuse(p, old, run_id, frame=mixed)
    with pytest.raises(KeyError):
        p.runtime.store.load(run_id)
    assert author_counts(author) == calls


@pytest.mark.asyncio
async def test_exact_reentry_and_owner_reload_keep_one_immutable_input(tmp_path, monkeypatch):
    p, _, _, old, author = await selected_source(tmp_path, monkeypatch)
    run_id = 'offline-reviewed-reentry'
    first = await reuse(p, old, run_id)
    origin = anchor_ref(p, run_id)
    checkpoint = dump_contract(p.runtime.store.load(run_id))
    calls = author_counts(author)
    assert await reuse(p, old, run_id) == first
    reloaded = TargetReferenceProduction(p)
    assert await reloaded.prepare_reference(run_id=run_id, preparation_ref=old.preparation_ref,
        author_context_ref=old.author_context_ref, frame=source_frame(old)) == first
    assert anchor_ref(p, run_id) == origin
    assert dump_contract(p.runtime.store.load(run_id)) == checkpoint
    assert author_counts(author) == calls


@pytest.mark.asyncio
async def test_real_unselected_candidate_has_a_separate_production_input_and_cost_wait(tmp_path, monkeypatch):
    p, _, old_id, old, author = await candidate_source(tmp_path, monkeypatch)
    before_assets, before_old, calls = assets(p), dump_contract(old), author_counts(author)
    # Old experiment remains unable to buy images even after the new entry exists.
    with pytest.raises(ValueError, match='REFERENCE_PREPARATION_AUTHORITY_MISMATCH'):
        await quote(p, old_id)
    run_id = 'offline-reviewed-unselected-candidate'
    result = await reuse(p, old, run_id)
    assert result.frame == old.frame and result.preparation_ref == old.preparation_ref
    assert p.asset_sequence.candidate_parent(result.preparation_ref) is not None
    assert p.runtime.store.load(run_id).mode == RunMode.PRODUCTION
    await quote(p, run_id)
    run = await p.reference_production.resume(run_id)
    assert run.state == RuntimeState.WAITING_USER and run.cursor == 1
    current = p.reference_production.get(run_id)
    assert current.stage is None and current.receipt is None and current.adoption_ref is None
    assert author_counts(author) == calls and assets(p) == before_assets
    assert dump_contract(p.reference_production.get(old_id)) == before_old
    with pytest.raises(ValueError, match='REFERENCE_PREPARATION_AUTHORITY_MISMATCH'):
        await quote(p, old_id)


@pytest.mark.asyncio
async def test_same_source_accepts_a_later_formal_revision_context_without_reverting_it(tmp_path, monkeypatch):
    p, _, _, old, author = await selected_source(tmp_path, monkeypatch)
    request = AuthorRequest.model_validate(p.asset_sequence.objects.read_ref(old.author_context_ref))
    newer = request.model_copy(update={'revision': RevisionRequest(owner=Authority.PROFESSIONAL,
        target_ref=request.source_refs[0], finding_ref=ArtifactReference(owner='offline-review',
            artifact_ref='offline-later-reference-field-review'),
        instruction='Keep approved art and organize current facts apart from internal notes.')})
    pin = p.asset_sequence.objects.put('offline-actual-later-reference-context', dump_contract(newer))
    calls = author_counts(author)
    result = await reuse(p, old, 'offline-review-new-context', author_context_ref=pin)
    assert result.author_context_ref == pin and result.frame == old.frame
    assert p.asset_sequence.objects.read_ref(result.author_context_ref) == dump_contract(newer)
    assert author_counts(author) == calls


@pytest.mark.asyncio
@pytest.mark.parametrize('changed', ['frame', 'preparation', 'context'])
async def test_same_run_identity_rejects_changed_input(tmp_path, monkeypatch, changed):
    p, _, _, old, author = await selected_source(tmp_path, monkeypatch)
    run_id = 'offline-reviewed-fixed-input'
    first = await reuse(p, old, run_id)
    options = {}
    if changed == 'frame':
        options['frame'] = restamp(source_frame(old), seed=old.frame['spec']['seed'] + 1)
    elif changed == 'preparation':
        packet = p.asset_sequence.objects.read_ref(old.preparation_ref)
        changed_packet = deepcopy(packet)
        changed_packet['referenceAuthorContext']['revision'] = dict(owner='professional-design-author',
            targetRef=dump_contract(AuthorRequest.model_validate(packet['referenceAuthorContext']).source_refs[0]),
            findingRef=dict(owner='offline-review', artifactRef='other', version=1), instruction='Other input')
        options['preparation_ref'] = p.asset_sequence.objects.put('offline-other-reference-input', changed_packet)
    else:
        request = AuthorRequest.model_validate(p.asset_sequence.objects.read_ref(old.author_context_ref))
        options['author_context_ref'] = p.asset_sequence.objects.put('offline-other-context',
            dump_contract(request.model_copy(update={'finding_refs': (
                ArtifactReference(owner='offline-review', artifact_ref='another-review'),)})))
    calls = author_counts(author)
    with pytest.raises(ValueError):
        await reuse(p, old, run_id, **options)
    assert p.reference_production.get(run_id) == first and author_counts(author) == calls


@pytest.mark.asyncio
async def test_existing_run_cannot_be_converted_into_a_new_reuse_input(tmp_path, monkeypatch):
    p, _, old_id, old, author = await candidate_source(tmp_path, monkeypatch)
    before, calls = dump_contract(p.runtime.store.load(old_id)), author_counts(author)
    with pytest.raises(ValueError):
        await reuse(p, old, old_id)
    assert dump_contract(p.runtime.store.load(old_id)) == before
    assert author_counts(author) == calls
    with p.ledger.transaction() as db:
        assert db.execute('SELECT 1 FROM ledger_index WHERE index_type=? AND index_key=?',
            (REUSE_INDEX, old_id)).fetchone() is None


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['missing_facts', 'wrong_scope', 'changed_source', 'changed_film_look'])
async def test_missing_or_foreign_authority_does_not_create_a_run(tmp_path, monkeypatch, fault):
    p, _, _, old, author = await selected_source(tmp_path, monkeypatch)
    frame, context = source_frame(old), old.author_context_ref
    if fault == 'missing_facts':
        frame = frame.model_copy(update={'prompt_ir': None})
    else:
        request = AuthorRequest.model_validate(p.asset_sequence.objects.read_ref(context))
        if fault == 'wrong_scope':
            request = request.model_copy(update={'scope': request.scope.model_copy(update={'scene_id': 's-2'})})
        elif fault == 'changed_source':
            request = request.model_copy(update={'source': request.source.model_copy(update={'text': 'Unselected source text'})})
        else:
            request = request.model_copy(update={'professional_context': {
                **(request.professional_context or {}), 'filmLook': [{'ref': {
                    'key': 'unselected-look', 'kind': 'DIRECTION', 'fingerprint': 'a' * 64}, 'design': {}}]}})
        context = p.asset_sequence.objects.put('offline-invalid-context-' + fault, dump_contract(request))
    calls, before_assets = author_counts(author), assets(p)
    run_id = 'offline-rejected-' + fault
    with pytest.raises(ValueError):
        await reuse(p, old, run_id, frame=frame, author_context_ref=context)
    with pytest.raises(KeyError):
        p.runtime.store.load(run_id)
    assert author_counts(author) == calls and assets(p) == before_assets


@pytest.mark.asyncio
async def test_a_reassessment_label_without_its_real_parent_binding_is_rejected(tmp_path, monkeypatch):
    p, _, _, old, author = await candidate_source(tmp_path, monkeypatch)
    packet = p.asset_sequence.objects.read_ref(old.preparation_ref)
    forged = deepcopy(packet)
    forged['professionalBasisRefs'] = []
    context = forged['referenceAuthorContext']['professionalContext']['assetPreparation']
    context['revisionSourceRef']['fingerprint'] = '0' * 64
    pin = p.asset_sequence.objects.put('offline-forged-parent', forged)
    calls = author_counts(author)
    with pytest.raises(ValueError):
        await reuse(p, old, 'offline-forged-parent-run', preparation_ref=pin)
    with pytest.raises(KeyError):
        p.runtime.store.load('offline-forged-parent-run')
    assert author_counts(author) == calls


@pytest.mark.asyncio
@pytest.mark.parametrize('tamper', ['foreign_record', 'missing_anchor', 'untyped_marker'])
async def test_private_origin_is_a_verified_record_not_a_string_waiver(tmp_path, monkeypatch, tamper):
    p, _, old_id, old, author = await candidate_source(tmp_path, monkeypatch)
    run_id = 'offline-reviewed-origin-check'
    value = await reuse(p, old, run_id)
    calls = author_counts(author)
    with p.ledger.transaction(write=True) as db:
        if tamper == 'missing_anchor':
            db.execute('DELETE FROM ledger_index WHERE index_type=? AND index_key=?', (REUSE_INDEX, run_id))
        else:
            raw = (dump_contract(old.artifact_reference()) if tamper == 'foreign_record'
                else {'approved': True, 'marker': 'REVIEWED_REFERENCE_CANDIDATE'})
            db.execute('UPDATE ledger_index SET value_json=? WHERE index_type=? AND index_key=?',
                (canonical_json(raw), REUSE_INDEX, run_id))
    with pytest.raises((ValueError, KeyError)):
        await quote(p, run_id)
    assert p.reference_production.get(old_id) == old and author_counts(author) == calls
    assert p.reference_production.get(run_id).frame == value.frame


@pytest.mark.asyncio
async def test_record_text_does_not_turn_an_old_experiment_into_production(tmp_path, monkeypatch):
    p, _, old_id, old, author = await candidate_source(tmp_path, monkeypatch)
    current = p.reference_production.save(old, required_action='REVIEWED_REFERENCE_CANDIDATE_APPROVED')
    calls = author_counts(author)
    with pytest.raises(ValueError, match='REFERENCE_PREPARATION_AUTHORITY_MISMATCH'):
        await quote(p, old_id)
    assert p.reference_production.get(old_id) == current and author_counts(author) == calls


@pytest.mark.asyncio
@pytest.mark.parametrize('later_adoption_decision', [False, True])
async def test_metadata_lifecycle_cannot_report_an_old_asset_as_the_new_image(
        tmp_path, monkeypatch, later_adoption_decision):
    p, _, _, old, author = await selected_source(tmp_path, monkeypatch)
    run_id = 'offline-reviewed-one-submit:asset-reference:candidate'
    before_assets, calls = assets(p), author_counts(author)
    value = await reuse(p, old, run_id)
    posts = []
    fake_submission(monkeypatch, posts)
    fake_persistence(monkeypatch, p)
    await quote(p, run_id)
    run = await p.reference_production.resume(run_id)
    assert run.state == RuntimeState.WAITING_USER and not posts
    value = p.reference_production.get(run_id)
    await p.decide_target_run(run_id, decision_id=p.runtime.decision_id(run_id), accepted=True,
        source_ref=value.artifact_reference())
    run = await p.reference_production.resume(run_id)
    assert len(posts) == 1 and run.state == RuntimeState.WAITING_EXTERNAL and run.cursor == 4
    assert p.reference_production.get(run_id).adoption_ref is None
    assert p.reference_production.get(run_id).asset_id is None
    await p.reference_production.resume(run_id)
    assert len(posts) == 1
    reviewed = await pass_review(p, run_id)
    assert reviewed.asset_id is None and reviewed.adoption_ref is None
    assert assets(p) == before_assets and author_counts(author) == calls
    assert reviewed.frame == old.frame
    if later_adoption_decision:
        # A subsequent fixture adoption receipt is still not an implementation
        # of replacing the known Asset's earlier picture. Do not turn its old
        # identity/readback into success for this new candidate media.
        await p.decide_target_run(run_id, decision_id=p.runtime.decision_id(run_id), accepted=True,
            source_ref=reviewed.artifact_reference())
        run = await p.reference_production.resume(run_id)
        assert run.state != RuntimeState.SUCCEEDED
        assert p.reference_production.get(run_id).asset_id is None
        assert assets(p) == before_assets and len(posts) == 1
    assert not list(tmp_path.rglob('*.png')) and not list(tmp_path.rglob('*.mp4'))


@pytest.mark.asyncio
@pytest.mark.parametrize('provider_outcome', ['UNKNOWN', 'NOT_CREATED'])
async def test_same_reused_input_never_reposts_an_unknown_or_not_created_attempt(
        tmp_path, monkeypatch, provider_outcome):
    import drama_plugin.professional_design.reference_production as module
    p, _, _, old, author = await selected_source(tmp_path, monkeypatch)
    run_id = 'offline-reviewed-no-paid-retry-' + provider_outcome.lower()
    await reuse(p, old, run_id)
    calls, before_assets, posts = author_counts(author), assets(p), []

    async def metadata_outcome(work, attempt, frame, cache):
        posts.append(deepcopy(attempt))
        assert p.reference_production.get(run_id).stage['attempts'][0]['submission_started']
        if provider_outcome == 'UNKNOWN':
            raise httpx.ReadTimeout('OFFLINE_UNKNOWN_FIXTURE_NO_RETRY')
        return dict(status='NOT_CREATED', task_id='offline-not-created',
            attempt_id=attempt['attempt_id'], work_id=work,
            request_fingerprint=fp(attempt['request']))

    monkeypatch.setattr(module, 'submit_reserved', metadata_outcome)
    await quote(p, run_id)
    assert (await p.reference_production.resume(run_id)).state == RuntimeState.WAITING_USER
    quoted = p.reference_production.get(run_id)
    await p.decide_target_run(run_id, decision_id=p.runtime.decision_id(run_id), accepted=True,
        source_ref=quoted.artifact_reference())
    run = await p.reference_production.resume(run_id)
    assert run.cursor == 2
    assert run.state == (RuntimeState.WAITING_EXTERNAL if provider_outcome == 'UNKNOWN' else RuntimeState.FAILED)
    first = p.reference_production.get(run_id)
    attempt_id = first.stage['attempts'][0]['attempt_id']
    assert len(posts) == 1
    for _ in range(2):
        current = await reuse(p, old, run_id)
        assert current.frame == old.frame and current.stage['attempts'][0]['attempt_id'] == attempt_id
        await p.reference_production.resume(run_id)
    final = p.reference_production.get(run_id)
    assert len(posts) == 1 and len(final.stage['attempts']) == 1
    assert final.stage['attempts'][0]['status'] == provider_outcome
    assert final.receipt is None if provider_outcome == 'UNKNOWN' else final.receipt['status'] == 'NOT_CREATED'
    assert final.asset_id is None and final.adoption_ref is None
    assert assets(p) == before_assets and author_counts(author) == calls
    assert not list(tmp_path.rglob('*.png')) and not list(tmp_path.rglob('*.mp4'))


@pytest.mark.asyncio
async def test_cost_wait_cannot_change_the_frozen_frame_or_runtime_checkpoint(tmp_path, monkeypatch):
    p, _, _, old, author = await selected_source(tmp_path, monkeypatch)
    run_id = 'offline-reviewed-cost-wait-freeze'
    await reuse(p, old, run_id)
    await quote(p, run_id)
    assert (await p.reference_production.resume(run_id)).state == RuntimeState.WAITING_USER
    current = p.reference_production.get(run_id)
    checkpoint = dump_contract(p.runtime.store.load(run_id))
    calls = author_counts(author)
    changed = restamp(source_frame(old), seed=old.frame['spec']['seed'] + 1)
    with pytest.raises(ValueError):
        await reuse(p, old, run_id, frame=changed)
    with pytest.raises(ValueError):
        await p.tools.invoke('specialized_assets.frame_reference', run_id=run_id, frame=changed)
    assert p.reference_production.get(run_id) == current
    assert dump_contract(p.runtime.store.load(run_id)) == checkpoint
    assert author_counts(author) == calls and current.stage is None and current.cost_ref is None
