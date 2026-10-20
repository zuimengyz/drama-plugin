"""Native non-person delivery: owner/receipt fixtures and GET-only fake HTTP."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from types import SimpleNamespace as NS

import httpx
import pytest
from pydantic import SecretStr

from drama_plugin.contracts.asset import Asset
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.media import Media, MediaResolveResult
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.execution.reference_delivery import (
    native_asset_originals, native_adopted_asset_image, native_adopted_character_image,
)
from drama_plugin.execution.transport import DefinitelyNotSubmitted
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.professional_design.reference_production import ReferenceProductionRecord
from drama_plugin.providers.ark_image import binding as image_binding
from drama_plugin.runtime.contracts import RuntimeScope
from drama_plugin.visual.frame_request import compile_frame
from drama_plugin.visual import production as still
from test_native_character_delivery import persist_originals
from test_target_reference_production import evidence, reference_frame

BYTES = b'unchanged-native-nonperson-fixture'
DUTIES = {'LOCATION': ('LOCATION', ('environment',)),
          'COSTUME': ('COSTUME', ('costume',)),
          'PROP': ('CONTINUITY', ('prop', 'continuity'))}


def repaired_fixture(tmp_path, monkeypatch):
    from drama_plugin.execution.reference_delivery import identity_repair_subject
    a, media, asset, binding, proof = fixture(monkeypatch, 'PROP')
    value = asset.content['specializedAsset']
    record = ReferenceProductionRecord.model_validate(proof['referenceRecord'])
    design = {**proof['designOriginal'], 'stableIdentity': 'specialized-asset:repaired'}
    design_ref = SourcePin(key='fixture:repaired-design', kind='DIRECTION', fingerprint=fp(design))
    item = {**design, 'designRef': dump_contract(design_ref), 'requirementKey': fp(design)}
    repair = {**proof['preparationOriginal'], 'requirements': [item],
        'professionalBasisRefs': [dump_contract(record.preparation_ref)],
        'identityRepair': {'originRunId': record.run_id, 'originRequirementKey': record.requirement_key,
                           'generatedAgain': False}}
    repair_ref = SourcePin(key='fixture:identity-repair', kind='DIRECTION', fingerprint=fp(repair))
    adoption = {**proof['adoptionOriginal'], 'subjectFingerprint': fp(design),
        'identityRepairRef': dump_contract(repair_ref),
        'originProductionRef': proof['adoptionOriginal']['referenceProductionRef']}
    del adoption['referenceProductionRef']
    adoption_ref = SourcePin(key='fixture:repaired-adoption', kind='DIRECTION', fingerprint=fp(adoption))
    value.update(**design, designRef=dump_contract(design_ref), adoptionRef=dump_contract(adoption_ref))
    binding.duties = (NS(role='CONTINUITY', subject=design['stableIdentity']),)
    binding.media.review_ref = 'asset-adoption:' + asset.id + ':' + fp(adoption)
    proof.update(designOriginal=design, adoptionOriginal=adoption)
    ledger, objects = persist_originals(tmp_path, asset, proof)
    objects.put(repair_ref.key, repair)
    decision = UserDecisionRecord.seal(run_id=record.run_id, scope=record.scope,
        decision_id=record.run_id + ':identity-repair', category='ADOPTION', accepted=True,
        source_ref=identity_repair_subject(asset, adoption))
    ledger.put_artifact('user-decision', decision.artifact_reference(), decision.scope, decision.fingerprint, decision)
    ledger.put_index('asset-identity-repair-authorization', fp(adoption),
                     decision.artifact_reference(), scope=record.scope)
    return a, media, asset, binding, ledger, objects


def test_repaired_prop_delivers_original_bytes_without_rewriting_generation(tmp_path, monkeypatch):
    a, media, asset, binding, ledger, objects = repaired_fixture(tmp_path, monkeypatch)
    proof = native_asset_originals(ledger, objects, asset)
    record = proof['referenceRecord']
    assert record['requirementKey'] != asset.content['specializedAsset']['designRef']['fingerprint']
    assert proof['preparationOriginal']['requirements'][0]['stableIdentity'] != proof['designOriginal']['stableIdentity']
    assert native_adopted_asset_image(a, media, asset, binding, proof).content_hash == sha256(BYTES).hexdigest()


@pytest.mark.parametrize('change', ['no-authorization', 'wrong-origin', 'changed-material',
    'changed-account', 'changed-hash', 'false-decision', 'wrong-duty', 'regenerated', 'changed-request'])
def test_repaired_prop_still_requires_exact_authority_artwork_and_production(tmp_path, monkeypatch, change):
    a, media, asset, b, ledger, objects = repaired_fixture(tmp_path, monkeypatch)
    if change == 'no-authorization':
        # A freshly persisted owner store without the separately accepted repair.
        def missing(*args): raise KeyError('missing repair authorization')
        monkeypatch.setattr(ledger, 'get_index', missing)
        with pytest.raises(DefinitelyNotSubmitted): native_asset_originals(ledger, objects, asset)
        return
    proof = native_asset_originals(ledger, objects, asset)
    if change == 'wrong-origin': proof['identityRepairOriginal']['identityRepair']['originRunId'] = 'unrelated'
    if change == 'changed-material': proof['designOriginal']['design']['architecture'] = 'different artwork'
    if change == 'changed-account': a.settings.api_key = SecretStr('other-account')
    if change == 'changed-hash': b.media.content_hash = 'e' * 64
    if change == 'false-decision': proof['identityRepairDecision']['accepted'] = False
    if change == 'wrong-duty': b.duties = (NS(role='LOCATION', subject=proof['designOriginal']['stableIdentity']),)
    if change == 'regenerated': proof['identityRepairOriginal']['identityRepair']['generatedAgain'] = True
    if change == 'changed-request': proof['referenceRecord']['frame']['request']['body']['prompt'] = 'different'
    with pytest.raises(DefinitelyNotSubmitted):
        native_adopted_asset_image(a, media, asset, b, proof)


def fixture(monkeypatch, kind, *, credential=True, failed_review=False):
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY', 'fixture-secret')
    monkeypatch.setenv('DRAMA_PLUGIN_ROUTE_IMAGE_MODEL', 'Doubao-Seedream-5.0-pro')
    narrative = SourcePin(key='fixture:fresh-narrative', kind='DIRECTION', fingerprint='b'*64)
    design = dict(assetType=kind, name='Selected ' + kind, design={'architecture': 'Selected source-bound visible structure'},
        subjectId='person' if kind == 'COSTUME' else None, stableIdentity='specialized-asset:fresh:fixture-' + kind,
        revision=1, establishedSceneId='S', inheritedFromAssetId=None, identityRootAssetId=None,
        variantReason=None, referenceRequired=True, narrativeRef=dump_contract(narrative))
    design_ref = SourcePin(key='fixture:design', kind='DIRECTION', fingerprint=fp(design))
    item = {**design, 'designRef': dump_contract(design_ref), 'requirementKey': fp(design)}
    spec = reference_frame(item).model_copy(update={
        'entry_state': 'One selected non-person asset at rest',
        'composition': 'Single still with readable selected structure'})
    ir = deepcopy(spec.prompt_ir)
    ir['source_fingerprint'] = fp(spec.model_dump(mode='json', exclude={'prompt_ir'}))
    frame = compile_frame(spec.model_copy(update={'prompt_ir': ir}))
    assert frame['spec']['actors'] == [] and frame['spec']['props'] == []
    prep = dict(schemaVersion='specialized-asset-preparation-v1', workId='W', sceneId='S',
                narrativeRef=dump_contract(narrative), rationale='Offline native fixture', requirements=[item])
    prep_ref = SourcePin(key='fixture:preparation', kind='DIRECTION', fingerprint=fp(prep))
    stage = still.new_stage(stage_id='fixture-' + kind, authorization_ref='fixture-cost', budget_credits=1,
                           budget_unit='CNY', frames=[frame], protected_targets=[])
    attempt = still.reserve(stage, spec.shot_id,
        quote=dict(request_fingerprint=fp(frame['request']), conservative_credits=.2, unit='CNY', uncertainty=None, evidence=evidence()),
        balance=dict(available_credits=2, margin_credits=.1, unit='CNY', evidence=evidence()),
        execution_binding=image_binding(frame, evidence()))
    still.begin_submission(stage, attempt_id=attempt['attempt_id'])
    h = sha256(BYTES).hexdigest()
    correlation = {k: attempt['execution_binding'][k] for k in
                   ('execution', 'endpoint_fingerprint', 'provider_schema_fingerprint', 'operation')}
    correlation.update(attempt_id=attempt['attempt_id'], task_id='fixture-task', request_fingerprint=fp(frame['request']))
    receipt = dict(status='COMPLETED', provider='ark', credential_source='DRAMA_VIDEO_SEEDANCE_API_KEY',
        model=frame['template']['model'], created=int(datetime.now(timezone.utc).timestamp()), usage={'generated_images': 1},
        diagnostics={'http_status': 200}, task_id='fixture-task', attempt_id=attempt['attempt_id'], work_id='W',
        request_fingerprint=fp(frame['request']), output_hash=h, output_bytes=len(BYTES), mime_type='image/png', correlation=correlation)
    if credential:
        receipt['credential_fingerprint'] = sha256(b'fixture-secret').hexdigest()
    still.record_result(stage, attempt_id=attempt['attempt_id'], status='COMPLETED', job_id=receipt['task_id'],
                        output_hash=h, execution_receipt=correlation, evidence='Synthetic receipt only')
    checks = {'READABLE_SELECTED_STRUCTURE': 'PASS', 'NO_PERSON_IN_SINGLE_STILL': 'PASS'}
    findings = ()
    if failed_review:
        checks['READABLE_SELECTED_STRUCTURE'] = 'FAIL'
        findings = (still.Finding(category='SCENE', severity='MAJOR',
                                 evidence='Synthetic wrong bed orientation', remedy='REGENERATE'),)
    still.record_review(stage, still.Review(attempt_id=attempt['attempt_id'], output_hash=h,
        reviewer='OFFLINE_FIXTURE', evidence='Metadata fixture, no pixel assessment', checks=checks, findings=findings))
    delivery = dict(persistenceStatus='VERIFIED', mediaId='M', contentHash=h,
                    sourceRef='asset-reference:' + attempt['attempt_id'], technical={'streams': [{'width': 1280, 'height': 720}]})
    before = ReferenceProductionRecord.seal(run_id='fixture-native-' + kind, scope=RuntimeScope(work_id='W', scene_id='S'),
        preparation_ref=prep_ref, requirement_key=fp(design), author_context_ref=narrative,
        frame=frame, stage=stage, receipt=receipt, delivery=delivery)
    decision = UserDecisionRecord.seal(run_id=before.run_id, scope=before.scope, decision_id=before.run_id + ':adopt',
                                     category='ADOPTION', accepted=True, source_ref=before.artifact_reference())
    record = ReferenceProductionRecord.seal(**{**before.model_dump(exclude={'fingerprint'}), 'adoption_ref': decision.artifact_reference()})
    adoption = dict(decision='ADOPT', workId='W', subjectFingerprint=fp(design), referenceMediaIds=['M'], referenceContentHash=h,
        reviewOriginal=still.current_review(attempt), referenceProductionRef=dump_contract(record.artifact_reference()),
        userDecisionRef=dump_contract(decision.artifact_reference()))
    adoption_ref = SourcePin(key='fixture:adoption', kind='DIRECTION', fingerprint=fp(adoption))
    asset = Asset(id='image-asset:media:M', work_id='W', asset_type=kind, name=design['name'], reference_media_ids=['M'],
        content={'specializedAsset': {**design, 'state': 'ADOPTED', 'designRef': dump_contract(design_ref),
                 'adoptionRef': dump_contract(adoption_ref), 'scenePreparationRef': dump_contract(prep_ref)}})
    media = Media(id='M', work_id='W', media_type='IMAGE', purpose=kind + '_REFERENCE', source_ref=delivery['sourceRef'],
                  mime_type='image/png', file_size=len(BYTES), content_hash=h, content={'filmStorageVersion': 2})
    target = RuntimeScope(work_id='W', scene_id='S2', shot_id='C01')
    duty, semantics = DUTIES[kind]
    from drama_plugin.production.contracts import SourceReference
    use = SourceReference(owner='professional', artifact_ref='fixture-selected-asset', version=1,
                          fingerprint='a' * 64, path=('content', 'assetBindings', '0'))
    state = SourceReference(owner='professional', artifact_ref='fixture-start-state', version=1, fingerprint='c' * 64)
    binding = NS(scope=target, origin_scope=before.scope, source_scope=before.scope, role='REFERENCE', subject_ids=(),
        use_ref=use, state_ref=state, authority_refs=(use,),
        authorization_scope='ADOPTED_PRODUCTION_INPUT', duties=(NS(role=duty, subject=design['stableIdentity']),),
        media=NS(media_id='M', content_hash=h, review_ref='asset-adoption:' + asset.id + ':' + fp(adoption),
                 semantics=semantics, width=1280, height=720))
    proof = dict(referenceRecord=dump_contract(record), preparationOriginal=prep, designOriginal=design,
                 adoptionOriginal=adoption, userDecisionOriginal=dump_contract(decision), decisionSourceRecord=dump_contract(before))
    return NS(settings=NS(api_key=SecretStr('fixture-secret'))), media, asset, binding, proof


@pytest.mark.parametrize('kind', DUTIES)
def test_nonperson_native_originals_use_real_adoption_and_captured_credential(tmp_path, monkeypatch, kind):
    a, m, asset, binding, proof = fixture(monkeypatch, kind)
    ledger, objects = persist_originals(tmp_path, asset, proof)
    actual = native_asset_originals(ledger, objects, asset)
    assert actual == proof and 'accountAttestation' not in actual
    result = native_adopted_asset_image(a, m, asset, binding, actual)
    assert result.content_hash == m.content_hash and result.byte_count == len(BYTES)
    with pytest.raises(DefinitelyNotSubmitted):
        native_adopted_character_image(a, m, asset, binding, actual)


@pytest.mark.parametrize('kind', DUTIES)
@pytest.mark.parametrize('change', ['wrong-duty', 'wrong-subject', 'character-subject', 'identity-semantics',
    'wrong-purpose', 'wrong-work', 'wrong-source-scene', 'wrong-adoption-pointer', 'unadopted', 'account',
    'hash', 'size', 'dimensions', 'changed-design', 'changed-frame', 'false-decision', 'different-predecessor',
    'missing-use', 'missing-state', 'ungranted-use', 'missing-source-scope'])
def test_nonperson_cannot_cross_duties_or_lose_native_identity(monkeypatch, kind, change):
    a, m, asset, b, proof = fixture(monkeypatch, kind)
    if change == 'wrong-duty': b.duties = (NS(role='CHARACTER', subject=proof['designOriginal']['stableIdentity']),)
    if change == 'wrong-subject': b.duties = (NS(role=DUTIES[kind][0], subject='other-asset'),)
    if change == 'character-subject': b.subject_ids = ('person',)
    if change == 'identity-semantics': b.media.semantics = (*b.media.semantics, 'identity')
    if change == 'wrong-purpose': m.purpose = 'CHARACTER_REFERENCE'
    if change == 'wrong-work': m.work_id = 'OTHER'
    if change == 'wrong-source-scene': b.source_scope = RuntimeScope(work_id='W', scene_id='OTHER')
    if change == 'wrong-adoption-pointer': b.media.review_ref = 'asset-adoption:' + asset.id + ':' + 'f' * 64
    if change == 'unadopted': asset.content['specializedAsset']['state'] = 'CANDIDATE'
    if change == 'account': a.settings.api_key = SecretStr('different-key')
    if change == 'hash': b.media.content_hash = 'f' * 64
    if change == 'size': m.file_size += 1
    if change == 'dimensions': b.media.width = 640
    if change == 'changed-design': proof['designOriginal']['design']['architecture'] = 'Unselected structure'
    if change == 'changed-frame': proof['referenceRecord']['frame']['request']['body']['image'] = ['https://unused.invalid/edit']
    if change == 'false-decision': proof['userDecisionOriginal']['accepted'] = False
    if change == 'different-predecessor': proof['decisionSourceRecord']['receipt']['output_hash'] = 'e' * 64
    if change == 'missing-use': b.use_ref = None
    if change == 'missing-state': b.state_ref = None
    if change == 'ungranted-use': b.authority_refs = ()
    if change == 'missing-source-scope': b.source_scope = None
    with pytest.raises(DefinitelyNotSubmitted):
        native_adopted_asset_image(a, m, asset, b, proof)


@pytest.mark.parametrize('kind', DUTIES)
def test_nonperson_requires_captured_key_and_does_not_backfill_attestation(monkeypatch, kind):
    a, m, asset, binding, proof = fixture(monkeypatch, kind, credential=False)
    proof['accountAttestation'] = {'credentialFingerprint': sha256(b'fixture-secret').hexdigest()}
    with pytest.raises(DefinitelyNotSubmitted, match='REFERENCE_ACCOUNT_UNVERIFIED'):
        native_adopted_asset_image(a, m, asset, binding, proof)


def test_failed_room_content_review_is_rejected_even_with_adoption_shaped_records(monkeypatch):
    a, m, asset, binding, proof = fixture(monkeypatch, 'LOCATION', failed_review=True)
    with pytest.raises(DefinitelyNotSubmitted):
        native_adopted_asset_image(a, m, asset, binding, proof)


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', DUTIES)
@pytest.mark.parametrize('failure', [None, 'compact-index', 'missing-owner', 'corrupt-original', 'wrong-account'])
async def test_transport_native_nonperson_reads_exact_owners_then_only_get(tmp_path, monkeypatch, kind, failure):
    from drama_plugin.execution.contracts import RequestReference
    from drama_plugin.execution.live_transport import TargetHttpTransport
    from drama_plugin.persistence.stores import DurableReferenceExecutionStore
    from drama_plugin.production.references import ReferenceExecutionBinding
    from drama_plugin.production.contracts import SourceReference
    a, m, asset, b, proof = fixture(monkeypatch, kind)
    ledger, objects = persist_originals(tmp_path, asset, proof)
    if failure == 'compact-index':
        value = asset.content['specializedAsset']
        for key in ('scenePreparationRef', 'establishedSceneId', 'inheritedFromAssetId', 'identityRootAssetId', 'variantReason'):
            value.pop(key)
        value['filmStorageValidated'] = True
    if failure == 'corrupt-original':
        pin = SourcePin.model_validate(asset.content['specializedAsset']['designRef'])
        with objects._writer(): objects._write(objects._path('objects', pin.fingerprint), {'changed': True})
    if failure == 'wrong-account': a.settings.api_key = SecretStr('different-key')
    use = SourceReference(owner='professional', artifact_ref='fixture-selected-asset', version=1, fingerprint='a' * 64,
                          path=('content', 'assetBindings', '0'))
    state = SourceReference(owner='professional', artifact_ref='fixture-start-state', version=1, fingerprint='c' * 64)
    binding = ReferenceExecutionBinding(binding_id='fixture-native-' + kind, version=1, scope=b.scope,
        source_scope=b.source_scope, use_ref=use, state_ref=state, authority_refs=(use,),
        media=dict(media_id=m.id, version='1', content_hash=m.content_hash, kind='image', semantics=b.media.semantics,
                   width=1280, height=720, review_ref=b.media.review_ref),
        duties=(dict(role=DUTIES[kind][0], necessity='REQUIRED', subject=proof['designOriginal']['stableIdentity'],
                     purpose='Only the selected current asset property'),),
        subject_ids=(), role='REFERENCE', authorization_scope='ADOPTED_PRODUCTION_INPUT')
    ref = DurableReferenceExecutionStore(ledger).register(binding)
    selected = RequestReference(binding_ref=ref, media_id=m.id, content_hash=m.content_hash, role='REFERENCE', kind='image')
    calls = []
    class Provider:
        async def get_media(self, identity): assert identity == m.id; return m
        async def get_asset(self, identity): assert identity == asset.id; return asset
        async def resolve_media(self, identity, *, provider_delivery):
            assert identity == m.id and provider_delivery
            return MediaResolveResult(media_id=m.id, url='https://objects.example.com/native-asset.png',
                mime_type=m.mime_type, size_bytes=m.file_size, expires_at=datetime.now(timezone.utc) + timedelta(minutes=10))
    def handle(request):
        calls.append(request.method)
        assert request.method == 'GET' and 'authorization' not in request.headers
        return httpx.Response(200, content=BYTES, headers={'Content-Type': 'image/png'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        a.client = client; a.provider = 'seedance'
        transport = TargetHttpTransport(a, tmp_path / 'receipts', ledger=ledger, media_provider=Provider(),
            asset_provider=Provider(), asset_originals=None if failure == 'missing-owner' else objects)
        if failure not in (None, 'compact-index'):
            with pytest.raises(DefinitelyNotSubmitted): await transport.reference_url(selected, NS(scope=b.scope))
            assert not calls
        else:
            assert await transport.reference_url(selected, NS(scope=b.scope)) == 'https://objects.example.com/native-asset.png'
            assert calls == ['GET']

@pytest.mark.parametrize('change', ['valid', 'account', 'receipt', 'production', 'digest'])
def test_submission_time_account_proof_is_bound_to_original(tmp_path, monkeypatch, change):
    from drama_plugin.execution.reference_delivery import retain_observed_image_credential
    a, media, asset, binding, proof = fixture(monkeypatch, 'PROP', credential=False)
    ledger, objects = persist_originals(tmp_path, asset, proof)
    production = ReferenceProductionRecord.model_validate(proof['referenceRecord'])
    original = {'referenceRecord': proof['referenceRecord'], 'accountAttestation': {
        'evidence': 'HOST_OBSERVED_SYNCHRONOUS_CREATE_SAME_CONFIG',
        'credentialFingerprint': sha256(b'fixture-secret').hexdigest(),
        'referenceProductionRef': dump_contract(production.artifact_reference()),
        'receiptFingerprint': fp(production.receipt)}}
    if change == 'account': original['accountAttestation']['credentialFingerprint'] = '0' * 64
    if change == 'receipt': original['accountAttestation']['receiptFingerprint'] = '0' * 64
    if change == 'production': original['referenceRecord'] = {}
    original['fingerprint'] = fp(original)
    if change == 'digest': original['fingerprint'] = '0' * 64
    ref = objects.put('existing-observed-original', original)
    def deliver():
        retain_observed_image_credential(objects, proof, ref)
        return native_adopted_asset_image(a, media, asset, binding, native_asset_originals(ledger, objects, asset))
    if change == 'valid': assert deliver().content_hash == media.content_hash
    else:
        with pytest.raises(DefinitelyNotSubmitted): deliver()

@pytest.mark.parametrize('change', ['valid', 'bytes', 'count', 'unreviewed', 'url', 'mode'])
def test_native_edited_image_inputs_require_exact_retained_bytes(change):
    import base64
    from drama_plugin.execution.reference_delivery import _native_image_inputs_valid
    frame={'spec':{'image_mode':'image_to_image','references':[{
        'asset_id':'asset:original','media_id':'media:original','review':'PASS','state':'ADOPTED',
        'content_hash':sha256(BYTES).hexdigest(),'uploaded_hash':sha256(BYTES).hexdigest()}]},
        'request':{'body':{'image':['data:image/png;base64,'+base64.b64encode(BYTES).decode()]}}}
    receipt={'usage':{'input_images':1}}
    if change=='bytes':frame['spec']['references'][0]['content_hash']='0'*64
    if change=='count':receipt['usage']['input_images']=0
    if change=='unreviewed':frame['spec']['references'][0]['review']='FAIL'
    if change=='url':frame['request']['body']['image']=['https://unverified.invalid/image.png']
    if change=='mode':frame['spec']['image_mode']='text_to_image'
    assert _native_image_inputs_valid(frame,receipt)==(change=='valid')

@pytest.mark.parametrize('missing', [None, 'identity_continuity', 'reference_scope'])
def test_existing_appearance_review_requires_identity_and_reference_scope(missing):
    from drama_plugin.execution.reference_delivery import _native_character_identity_review
    checks={k:'PASS' for k in ('identity_continuity','costume_materials','purpose_specific_composition','hands_and_grounding','reference_scope')}
    if missing:del checks[missing]
    assert _native_character_identity_review(checks)==(missing is None)
