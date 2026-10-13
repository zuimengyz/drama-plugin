"""Native CHARACTER delivery regression: metadata fixtures, never paid APIs."""
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
from drama_plugin.execution.reference_delivery import native_character_originals, native_adopted_character_image
from drama_plugin.execution.transport import DefinitelyNotSubmitted
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.professional_design.reference_production import ReferenceProductionRecord
from drama_plugin.providers.ark_image import binding as image_binding
from drama_plugin.runtime.contracts import RuntimeRun, RuntimeScope
from drama_plugin.visual.frame_request import compile_frame
from drama_plugin.visual import production as still
from test_target_reference_production import evidence, reference_frame


BYTES = b'unchanged-character-fixture'


def fixture(monkeypatch, *, fingerprint=True):
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY', 'fixture-secret')
    monkeypatch.setenv('DRAMA_PLUGIN_ROUTE_IMAGE_MODEL', 'Doubao-Seedream-5.0-pro')
    narrative = SourcePin(key='fixture:narrative', kind='DESIGN', fingerprint='b'*64)
    design = dict(assetType='CHARACTER', name='Fixture person', design={'face':'Distinct fixture face'},
        subjectId='person', stableIdentity='fixture-character', revision=1, establishedSceneId='S',
        inheritedFromAssetId=None, identityRootAssetId=None, variantReason=None, referenceRequired=True,
        narrativeRef=dump_contract(narrative))
    design_ref = SourcePin(key='fixture:design', kind='DIRECTION', fingerprint=fp(design))
    item = {**design, 'designRef':dump_contract(design_ref), 'requirementKey':fp(design)}
    frame = compile_frame(reference_frame(item))
    prep = dict(schemaVersion='specialized-asset-preparation-v1', workId='W', sceneId='S',
        narrativeRef=dump_contract(narrative), rationale='Offline proof fixture', requirements=[item])
    prep_ref = SourcePin(key='fixture:preparation', kind='DIRECTION', fingerprint=fp(prep))
    stage = still.new_stage(stage_id='fixture-character', authorization_ref='fixture-cost', budget_credits=1,
        budget_unit='CNY', frames=[frame], protected_targets=[])
    quote = dict(request_fingerprint=fp(frame['request']), conservative_credits=.2,
        unit='CNY', uncertainty=None, evidence=evidence())
    attempt = still.reserve(stage, frame['spec']['shot_id'], quote=quote,
        balance=dict(available_credits=2, margin_credits=.1, unit='CNY', evidence=evidence()),
        execution_binding=image_binding(frame,evidence()))
    still.begin_submission(stage, attempt_id=attempt['attempt_id'])
    h = sha256(BYTES).hexdigest()
    correlation = {k:attempt['execution_binding'][k] for k in
        ('execution','endpoint_fingerprint','provider_schema_fingerprint','operation')}
    correlation.update(attempt_id=attempt['attempt_id'], task_id='fixture-task', request_fingerprint=fp(frame['request']))
    receipt = dict(status='COMPLETED', provider='ark', credential_source='DRAMA_VIDEO_SEEDANCE_API_KEY',
        model=frame['template']['model'], created=int(datetime.now(timezone.utc).timestamp()), usage={'generated_images':1},
        diagnostics={'http_status':200}, task_id='fixture-task', attempt_id=attempt['attempt_id'], work_id='W',
        request_fingerprint=fp(frame['request']), output_hash=h, output_bytes=len(BYTES), mime_type='image/png', correlation=correlation)
    if fingerprint:
        receipt['credential_fingerprint'] = sha256(b'fixture-secret').hexdigest()
    still.record_result(stage, attempt_id=attempt['attempt_id'], status='COMPLETED', job_id=receipt['task_id'],
        output_hash=h, execution_receipt=correlation, evidence='Offline receipt fixture')
    still.record_review(stage, still.Review(attempt_id=attempt['attempt_id'], output_hash=h, reviewer='OFFLINE_FIXTURE',
        evidence='Synthetic metadata, no visual quality claim', checks={'IDENTITY':'PASS','SINGLE_PERSON':'PASS'}))
    delivery = dict(persistenceStatus='VERIFIED', mediaId='M', contentHash=h, sourceRef='asset-reference:'+attempt['attempt_id'],
        technical={'streams':[{'width':1280,'height':720}]})
    before = ReferenceProductionRecord.seal(run_id='fixture-native-character', scope=RuntimeScope(work_id='W',scene_id='S'),
        preparation_ref=prep_ref, requirement_key=fp(design), author_context_ref=narrative,
        frame=frame, stage=stage, receipt=receipt, delivery=delivery)
    decision = UserDecisionRecord.seal(run_id=before.run_id, scope=before.scope, decision_id=before.run_id+':adopt',
        category='ADOPTION', accepted=True, source_ref=before.artifact_reference())
    record = ReferenceProductionRecord.seal(**{**before.model_dump(exclude={'fingerprint'}), 'adoption_ref':decision.artifact_reference()})
    adoption = dict(decision='ADOPT', workId='W', subjectFingerprint=fp(design), referenceMediaIds=['M'], referenceContentHash=h,
        reviewOriginal=still.current_review(attempt), referenceProductionRef=dump_contract(record.artifact_reference()),
        userDecisionRef=dump_contract(decision.artifact_reference()))
    adoption_ref = SourcePin(key='fixture:adoption', kind='DIRECTION', fingerprint=fp(adoption))
    asset = Asset(id='image-asset:media:M', work_id='W', asset_type='CHARACTER', name=design['name'], reference_media_ids=['M'],
        content={'specializedAsset':{**design, 'state':'ADOPTED', 'designRef':dump_contract(design_ref),
            'adoptionRef':dump_contract(adoption_ref), 'scenePreparationRef':dump_contract(prep_ref)}})
    media = Media(id='M', work_id='W', media_type='IMAGE', purpose='CHARACTER_REFERENCE', source_ref=delivery['sourceRef'],
        mime_type='image/png', file_size=len(BYTES), content_hash=h, content={'filmStorageVersion':2})
    target = RuntimeScope(work_id='W', scene_id='S2', shot_id='K04')
    b = NS(scope=target, origin_scope=before.scope, source_scope=before.scope, role='REFERENCE', subject_ids=('person',),
        authorization_scope='ADOPTED_PRODUCTION_INPUT', duties=(NS(role='CHARACTER',subject='person'),),
        media=NS(media_id='M', content_hash=h, review_ref='asset-adoption:'+asset.id+':'+fp(adoption),
            semantics=('identity',), width=1280,height=720))
    proof = dict(referenceRecord=dump_contract(record), preparationOriginal=prep, designOriginal=design, adoptionOriginal=adoption,
        userDecisionOriginal=dump_contract(decision), decisionSourceRecord=dump_contract(before))
    return NS(settings=NS(api_key=SecretStr('fixture-secret'))),media,asset,b,proof


def persist_originals(tmp_path, asset, proof):
    from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
    from drama_plugin.persistence.ledger import ProductionLedger
    originals = DirectorArtifactStore(tmp_path/'originals')
    for key, refkey in [('preparationOriginal','scenePreparationRef'), ('designOriginal','designRef'), ('adoptionOriginal','adoptionRef')]:
        original = originals.put(asset.content['specializedAsset'][refkey]['key'], proof[key])
        assert dump_contract(original) == asset.content['specializedAsset'][refkey]
    ledger = ProductionLedger(tmp_path/'ledger.sqlite')
    record = ReferenceProductionRecord.model_validate(proof['referenceRecord'])
    ledger.create_run(RuntimeRun(run_id=record.run_id, scope=record.scope, mode='PRODUCTION', policy_id='fixture',
        workflow_id='fixture', workflow_fingerprint='a'*64))
    for key, cls in [('decisionSourceRecord',ReferenceProductionRecord), ('referenceRecord',ReferenceProductionRecord),
            ('userDecisionOriginal',UserDecisionRecord)]:
        value = cls.model_validate(proof[key]); ref=value.artifact_reference()
        ledger.put_artifact(ref.owner,ref,value.scope,value.fingerprint,value)
    return ledger,originals


def test_compact_native_character_reads_exact_owners_and_keeps_identity(tmp_path,monkeypatch):
    a,m,asset,b,proof=fixture(monkeypatch)
    ledger, originals=persist_originals(tmp_path,asset,proof)
    real=native_character_originals(ledger,originals,asset)
    assert real==proof
    identity=native_adopted_character_image(a,m,asset,b,real)
    assert identity.content_hash==m.content_hash and identity.byte_count==len(BYTES)
    assert m.content=={'filmStorageVersion':2} and ':' in asset.id


def test_compact_asset_resolves_omitted_preparation_and_history_fields_from_adoption_owner(tmp_path,monkeypatch):
    a,m,asset,b,proof=fixture(monkeypatch)
    ledger, originals=persist_originals(tmp_path,asset,proof)
    value=asset.content['specializedAsset']
    for key in ('scenePreparationRef','establishedSceneId','inheritedFromAssetId','identityRootAssetId','variantReason'):
        value.pop(key)
    value['filmStorageValidated']=True
    real=native_character_originals(ledger,originals,asset)
    assert real==proof
    assert native_adopted_character_image(a,m,asset,b,real).content_hash==m.content_hash


def test_provided_preparation_must_match_sealed_native_record(tmp_path,monkeypatch):
    a,m,asset,b,proof=fixture(monkeypatch)
    ledger, originals=persist_originals(tmp_path,asset,proof)
    asset.content['specializedAsset']['scenePreparationRef']['fingerprint']='e'*64
    with pytest.raises(DefinitelyNotSubmitted):native_character_originals(ledger,originals,asset)


def test_historical_missing_key_is_specific_unverified_not_current_key_backfill(tmp_path,monkeypatch):
    a,m,asset,b,proof=fixture(monkeypatch,fingerprint=False)
    ledger, originals=persist_originals(tmp_path,asset,proof)
    with pytest.raises(DefinitelyNotSubmitted,match='REFERENCE_ACCOUNT_UNVERIFIED'):
        native_adopted_character_image(a,m,asset,b,native_character_originals(ledger,originals,asset))
    assert 'credential_fingerprint' not in proof['referenceRecord']['receipt']


@pytest.mark.parametrize('change',['account','wrong-work','wrong-media','wrong-size','wrong-dimensions','subject','duty',
    'purpose','adoption','design','frame','image-input','review','failed-receipt','receipt-hash','source-scope','decision'])
def test_changed_or_unqualified_native_portrait_cannot_dispatch(monkeypatch,change):
    a,m,asset,b,p=fixture(monkeypatch)
    if change=='account':a.settings.api_key=SecretStr('other-key')
    if change=='wrong-work':m.work_id='OTHER'
    if change=='wrong-media':b.media.media_id='OTHER'
    if change=='wrong-size':m.file_size+=1
    if change=='wrong-dimensions':b.media.width=640
    if change=='subject':b.subject_ids=('other',)
    if change=='duty':b.duties=(NS(role='LOCATION',subject='person'),)
    if change=='purpose':m.purpose='START_FRAME'
    if change=='adoption':p['adoptionOriginal']['decision']='REJECT'
    if change=='design':p['designOriginal']['design']['face']='Another person'
    if change=='frame':p['referenceRecord']['frame']['spec']['actors'][0]['identity']='Another person'
    if change=='image-input':p['referenceRecord']['frame']['request']['body']['image']=['https://example.invalid/edit.png']
    if change=='review':p['referenceRecord']['stage']['attempts'][0]['review']['checks']['IDENTITY']='FAIL'
    if change=='failed-receipt':p['referenceRecord']['receipt']['status']='FAILED'
    if change=='receipt-hash':p['referenceRecord']['receipt']['output_hash']='f'*64
    if change=='source-scope':b.source_scope=RuntimeScope(work_id='W',scene_id='OTHER')
    if change=='decision':p['userDecisionOriginal']['accepted']=False
    with pytest.raises(DefinitelyNotSubmitted):native_adopted_character_image(a,m,asset,b,p)


@pytest.mark.asyncio
@pytest.mark.parametrize('failure',[None,'compact-asset','missing-owner','wrong-owner','corrupt-design','account'])
async def test_transport_native_portrait_owner_resolution_precedes_only_get(tmp_path,monkeypatch,failure):
    from drama_plugin.execution.contracts import RequestReference
    from drama_plugin.execution.live_transport import TargetHttpTransport
    from drama_plugin.persistence.stores import DurableReferenceExecutionStore
    from drama_plugin.production.references import ReferenceExecutionBinding
    from drama_plugin.production.contracts import SourceReference
    a,m,asset,b,proof=fixture(monkeypatch)
    ledger, originals=persist_originals(tmp_path,asset,proof)
    if failure=='compact-asset':
        value=asset.content['specializedAsset']
        for key in ('scenePreparationRef','establishedSceneId','inheritedFromAssetId','identityRootAssetId','variantReason'):
            value.pop(key)
        value['filmStorageValidated']=True
    if failure=='wrong-owner':asset.content['specializedAsset']['adoptionRef']['fingerprint']='e'*64
    if failure=='corrupt-design':
        pin=SourcePin.model_validate(asset.content['specializedAsset']['designRef'])
        with originals._writer(): originals._write(originals._path('objects',pin.fingerprint),{'changed':True})
    if failure=='account':a.settings.api_key=SecretStr('other-key')
    use=SourceReference(owner='professional',artifact_ref='fixture-target-character',version=1,fingerprint='a'*64)
    binding=ReferenceExecutionBinding(binding_id='fixture-native-character',version=1,scope=b.scope,source_scope=b.source_scope,
        media=dict(media_id=m.id,version='1',content_hash=m.content_hash,kind='image',semantics=('identity',),
            width=1280,height=720,review_ref=b.media.review_ref),
        duties=(dict(role='CHARACTER',necessity='REQUIRED',subject='person',purpose='Same person at new camera angle'),),
        subject_ids=('person',),role='REFERENCE',authorization_scope='ADOPTED_PRODUCTION_INPUT',authority_refs=(use,),
        use_ref=use,state_ref=use)
    ref=DurableReferenceExecutionStore(ledger).register(binding)
    selected=RequestReference(binding_ref=ref,media_id=m.id,content_hash=m.content_hash,role='REFERENCE',kind='image')
    class Provider:
        async def get_media(self,identity):assert identity==m.id;return m
        async def get_asset(self,identity):assert identity==asset.id;return asset
        async def resolve_media(self,identity,*,provider_delivery):
            assert identity==m.id and provider_delivery
            return MediaResolveResult(media_id=m.id,url='https://objects.example.com/unchanged-character.png',
                mime_type=m.mime_type,size_bytes=m.file_size,expires_at=datetime.now(timezone.utc)+timedelta(minutes=10))
    calls=[]
    def handle(request):
        calls.append(request.method)
        assert request.method=='GET' and 'authorization' not in request.headers
        return httpx.Response(200,content=BYTES,headers={'Content-Type':'image/png'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        a.client=client;a.provider='seedance'
        t=TargetHttpTransport(a,tmp_path/'receipts',ledger=ledger,media_provider=Provider(),asset_provider=Provider(),
            asset_originals=None if failure=='missing-owner' else originals)
        if failure and failure!='compact-asset':
            with pytest.raises(DefinitelyNotSubmitted):await t.reference_url(selected,NS(scope=b.scope))
            assert not calls
        else:
            assert await t.reference_url(selected,NS(scope=b.scope))=='https://objects.example.com/unchanged-character.png'
            assert calls==['GET']


def confirm(objects,proof,*,key='fixture-secret',source='current-human-reply:fixture:0',when=None):
    from drama_plugin.execution.reference_delivery import retain_historical_character_credential
    return retain_historical_character_credential(objects,proof,credential_fingerprint=sha256(key.encode()).hexdigest(),
        confirmation_source=source,confirmed_at=when or datetime.now(timezone.utc),
        user_statement='确认，一直是当前这把 Key，未更换')


def test_explicit_human_confirmation_recovers_old_original_without_receipt_mutation(tmp_path,monkeypatch):
    a,m,asset,b,proof=fixture(monkeypatch,fingerprint=False)
    ledger,originals=persist_originals(tmp_path,asset,proof)
    old=deepcopy(proof['referenceRecord']['receipt'])
    now=datetime.now(timezone.utc)
    ref=confirm(originals,proof,when=now)
    count=len(tuple((originals.root/'objects').glob('*.json')))
    assert confirm(originals,proof,when=now)==ref
    assert confirm(originals,proof,when=now+timedelta(microseconds=1))==ref
    assert len(tuple((originals.root/'objects').glob('*.json')))==count
    actual=native_character_originals(ledger,originals,asset)
    assert actual['referenceRecord']['receipt']==old and 'credential_fingerprint' not in old
    assert actual['historicalCredentialConfirmation']['evidence']=='USER_CONFIRMED_HISTORICAL_UNCHANGED_CREDENTIAL'
    assert native_adopted_character_image(a,m,asset,b,actual).content_hash==m.content_hash
    with pytest.raises(ValueError,match='CONFIRMATION_CONFLICT'):confirm(originals,proof,key='other-secret')
    assert len(tuple((originals.root/'objects').glob('*.json')))==count


@pytest.mark.parametrize('change',['work','record','receipt','request','hash','key','source','time','statement','unchanged','evidence'])
def test_confirmation_must_identify_exact_historical_request(monkeypatch,tmp_path,change):
    a,m,asset,b,proof=fixture(monkeypatch,fingerprint=False)
    ledger,originals=persist_originals(tmp_path,asset,proof)
    confirm(originals,proof)
    actual=native_character_originals(ledger,originals,asset)
    c=actual['historicalCredentialConfirmation']
    fields={'work':'workId','receipt':'receiptFingerprint','request':'requestFingerprint','hash':'outputHash',
        'key':'credentialFingerprint','source':'confirmationSource','statement':'userStatement','evidence':'evidence'}
    if change in fields:c[fields[change]]='' if change=='statement' else 'wrong'
    if change=='record':c['referenceProductionRef']['artifactRef']='wrong-record'
    if change=='time':c['confirmedAt']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    if change=='unchanged':c['keyUnchangedSinceGeneration']=False
    with pytest.raises(DefinitelyNotSubmitted,match='REFERENCE_ACCOUNT_UNVERIFIED'):
        native_adopted_character_image(a,m,asset,b,actual)


def test_captured_wrong_credential_never_falls_back_to_later_human_confirmation(tmp_path,monkeypatch):
    a,m,asset,b,proof=fixture(monkeypatch)
    ledger,originals=persist_originals(tmp_path,asset,proof)
    with pytest.raises(ValueError,match='EXPLICIT_HISTORICAL_CREDENTIAL_CONFIRMATION_REQUIRED'):
        confirm(originals,proof)
    # A caller-supplied confirmation is ineffective when dispatch captured a different key.
    proof['historicalCredentialConfirmation']={'evidence':'USER_CONFIRMED_HISTORICAL_UNCHANGED_CREDENTIAL',
        'credentialFingerprint':sha256(b'new-key').hexdigest()}
    a.settings.api_key=SecretStr('new-key')
    with pytest.raises(DefinitelyNotSubmitted,match='REFERENCE_ACCOUNT_UNVERIFIED'):
        native_adopted_character_image(a,m,asset,b,proof)


def test_human_confirmation_cannot_override_failed_visual_review(tmp_path,monkeypatch):
    a,m,asset,b,proof=fixture(monkeypatch,fingerprint=False)
    ledger,originals=persist_originals(tmp_path,asset,proof)
    confirm(originals,proof)
    actual=native_character_originals(ledger,originals,asset)
    actual['adoptionOriginal']['reviewOriginal']['checks']['IDENTITY']='FAIL'
    with pytest.raises(DefinitelyNotSubmitted,match='REFERENCE_ADOPTED_IMAGE_PROOF_REQUIRED'):
        native_adopted_character_image(a,m,asset,b,actual)


def test_native_character_binding_producer_uses_asset_identity_without_changing_location_pointer(monkeypatch):
    import drama_plugin.film.media_references as module
    import drama_plugin.creative_engine.sources as sources
    from drama_plugin.production.contracts import SourceReference
    subject=NS(scope=RuntimeScope(work_id='W',scene_id='S2',shot_id='K04'),body=NS(facts={
        'presentSubjects':[{'id':'person'}], 'assetBindings':[{'id':'image-asset:media:M','assetType':'CHARACTER',
        'content':{'specializedAsset':dict(subjectId='person',stableIdentity='person',establishedSceneId='S',
            adoptionRef=dict(key='asset-reference-adoption:hash',fingerprint='a'*64))},
        'resolvedMedia':[dict(mediaId='M',version='1',contentHash='b'*64,mediaType='IMAGE',width=1280,height=720)]}]}))
    world=NS(scope=subject.scope,body=NS(facts={'locationAssetId':'LOCATION','assetBindings':[{
        'id':'LOCATION','assetType':'LOCATION','content':{'specializedAsset':dict(stableIdentity='room',establishedSceneId='S',
            adoptionRef=dict(key='location-old-adoption',fingerprint='c'*64))},
        'resolvedMedia':[dict(mediaId='ROOM',version='1',contentHash='d'*64,mediaType='IMAGE',width=1280,height=720)]}]}))
    class Native:
        def __init__(self,*args):pass
        def project(self,*args):return self
        def reference(self,*path):return SourceReference(owner='professional',artifact_ref='fixture',version=1,
            fingerprint='e'*64,path=path)
    monkeypatch.setattr(sources,'NativeCreativeSources',Native)
    monkeypatch.setattr(module,'professional',lambda p,unit,domain:subject if domain=='SUBJECTS' else world)
    selection=NS(fact_refs=(NS(domain='SUBJECTS',reference=NS(path=('content','presentSubjects','0'))),),
        start_ref=SourceReference(owner='professional',artifact_ref='start',version=1,fingerprint='f'*64))
    p=NS(creative_versions=None,execution_references=None)
    result=module.asset_reference_candidates(p,NS(refs=()),selection)
    assert result[0].media.review_ref=='asset-adoption:image-asset:media:M:'+ 'a'*64
    assert result[1].media.review_ref=='location-old-adoption:'+ 'c'*64
