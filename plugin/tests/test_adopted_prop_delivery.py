"""Native Prop delivery boundaries only; synthetic receipts, no Provider calls."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from types import SimpleNamespace as NS
import pytest
from pydantic import SecretStr

from drama_plugin.contracts.asset import Asset
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.media import Media
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.execution.reference_delivery import adopted_prop_original_image
from drama_plugin.execution.transport import DefinitelyNotSubmitted
from drama_plugin.professional_design.reference_production import ReferenceProductionRecord
from drama_plugin.providers.ark_image import binding as image_binding
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope
from drama_plugin.visual.frame_request import Prop, compile_frame
from drama_plugin.visual import production as still
from test_target_reference_production import evidence, reference_frame


def prop_fixture(monkeypatch):
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY','fixture-secret')
    monkeypatch.setenv('DRAMA_PLUGIN_ROUTE_IMAGE_MODEL','Doubao-Seedream-5.0-pro')
    identity='specialized-asset:coffin'
    narrative=SourcePin(key='fixture:narrative',kind='DESIGN',fingerprint='b'*64)
    design=dict(assetType='PROP',name='Fixture infant coffin',design={'geometry':'70 cm tapered body and separate lid'},
        subjectId=None,stableIdentity=identity,revision=1,establishedSceneId='S',inheritedFromAssetId=None,
        identityRootAssetId=None,variantReason=None,referenceRequired=True,narrativeRef=dump_contract(narrative))
    design_ref=SourcePin(key='fixture:prop-design',kind='DESIGN',fingerprint=fp(design))
    item={**design,'designRef':dump_contract(design_ref),'requirementKey':fp(design)}
    spec=reference_frame(item)
    spec=spec.model_copy(update={'props':(Prop(entity_key=identity,state='Open, matching lid alongside',
        geometry='70 cm tapered low body',placement='Reference table',forbidden=('People','Deep rectangular box')),),
        'omitted':{identity:'Initial selected object reference; no previous image'}})
    ir=deepcopy(spec.prompt_ir);ir['source_fingerprint']=fp(spec.model_dump(mode='json',exclude={'prompt_ir'}))
    frame=compile_frame(spec.model_copy(update={'prompt_ir':ir}))
    preparation=dict(schemaVersion='specialized-asset-preparation-v1',workId='W',sceneId='S',
        narrativeRef=dump_contract(narrative),rationale='Synthetic reference fixture',requirements=[item])
    prep_ref=SourcePin(key='fixture:preparation',kind='DESIGN',fingerprint=fp(preparation))
    stage=still.new_stage(stage_id='fixture-prop',authorization_ref='fixture-approval',budget_credits=1,
        budget_unit='CNY',frames=[frame],protected_targets=[])
    quote=dict(request_fingerprint=fp(frame['request']),conservative_credits=.2,unit='CNY',uncertainty=None,evidence=evidence())
    balance=dict(available_credits=2,margin_credits=.1,unit='CNY',evidence=evidence())
    attempt=still.reserve(stage,spec.shot_id,quote=quote,balance=balance,execution_binding=image_binding(frame,evidence()))
    still.begin_submission(stage,attempt_id=attempt['attempt_id'])
    h=sha256(b'unchanged-prop-fixture').hexdigest();now=int(datetime.now(timezone.utc).timestamp())
    correlation={k:attempt['execution_binding'][k] for k in
        ('execution','endpoint_fingerprint','provider_schema_fingerprint','operation')}
    correlation.update(attempt_id=attempt['attempt_id'],task_id='fixture-image-request',request_fingerprint=fp(frame['request']))
    receipt=dict(status='COMPLETED',provider='ark',credential_source='DRAMA_VIDEO_SEEDANCE_API_KEY',
        model=frame['template']['model'],created=now,usage={'input_images':0},diagnostics={'http_status':200},
        task_id='fixture-image-request',attempt_id=attempt['attempt_id'],work_id='W',request_fingerprint=fp(frame['request']),
        output_hash=h,output_bytes=22,mime_type='image/png',correlation=correlation)
    still.record_result(stage,attempt_id=attempt['attempt_id'],status='COMPLETED',job_id=receipt['task_id'],
        output_hash=h,execution_receipt=correlation,evidence='Synthetic fixture only')
    still.record_review(stage,still.Review(attempt_id=attempt['attempt_id'],output_hash=h,reviewer='OFFLINE_FIXTURE',
        evidence='Synthetic checks; no user media or visual judgment',checks={k:'PASS' for k in
            ('NO_PEOPLE','PROP_STRUCTURE','PROP_SCALE','PROP_MATERIAL')}))
    delivery=dict(persistenceStatus='VERIFIED',mediaId='M',contentHash=h,sourceRef='asset-reference:'+attempt['attempt_id'],
        technical={'streams':[{'width':1280,'height':720}]})
    record=ReferenceProductionRecord.seal(run_id='fixture-prop',scope=RuntimeScope(work_id='W',scene_id='S'),
        preparation_ref=prep_ref,requirement_key=fp(design),author_context_ref=narrative,frame=frame,stage=stage,
        receipt=receipt,delivery=delivery,adoption_ref=ArtifactReference(owner='user-decision',artifact_ref='fixture-adoption'))
    adoption=dict(decision='ADOPT',workId='W',subjectFingerprint=fp(design),referenceMediaIds=['M'],
        referenceContentHash=h,reviewOriginal=still.current_review(stage['attempts'][0]),
        referenceProductionRef=dump_contract(record.artifact_reference()),userDecisionRef=dump_contract(record.adoption_ref))
    adoption_ref=SourcePin(key='fixture:adoption',kind='DESIGN',fingerprint=fp(adoption))
    asset=Asset(id='A',work_id='W',asset_type='PROP',name='Coffin',reference_media_ids=['M'],
        content={'specializedAsset':{**design,'state':'ADOPTED','designRef':dump_contract(design_ref),'adoptionRef':dump_contract(adoption_ref)}})
    media=Media(id='M',work_id='W',media_type='IMAGE',purpose='PROP_REFERENCE',source_ref=delivery['sourceRef'],
        mime_type='image/png',file_size=22,content_hash=h,content={'filmStorageVersion':2})
    target=RuntimeScope(work_id='W',scene_id='S',shot_id='K03')
    binding=NS(scope=target,origin_scope=target,role='REFERENCE',subject_ids=(),authorization_scope='ADOPTED_PRODUCTION_INPUT',
        duties=(NS(role='CONTINUITY',subject=identity),),media=NS(media_id='M',content_hash=h,
            review_ref='pending-retained-prop-proof',semantics=('prop','continuity'),width=1280,height=720))
    proof=dict(referenceRecord=dump_contract(record),preparationOriginal=preparation,designOriginal=design,adoptionOriginal=adoption,
        accountAttestation=dict(evidence='HOST_OBSERVED_SYNCHRONOUS_CREATE_SAME_CONFIG',
            referenceProductionRef=dump_contract(record.artifact_reference()),receiptFingerprint=fp(receipt),
            credentialFingerprint=sha256(b'fixture-secret').hexdigest()))
    proof['fingerprint']=fp(proof)
    binding.media.review_ref='prop-asset-adoption:'+asset.id+':'+fp(proof)
    adapter=NS(settings=NS(api_key=SecretStr('fixture-secret')))
    return adapter,media,asset,binding,proof


def test_exact_native_prop_index_and_originals_are_accepted_without_portrait(monkeypatch):
    a,m,asset,b,proof=prop_fixture(monkeypatch)
    result=adopted_prop_original_image(a,m,asset,b,proof)
    assert result.content_hash==m.content_hash and result.byte_count==22
    assert b.subject_ids==() and asset.asset_type=='PROP'
    assert m.content=={'filmStorageVersion':2}


def test_prop_proof_pointer_preserves_asset_ids_containing_colons(monkeypatch):
    a,m,asset,b,proof=prop_fixture(monkeypatch)
    asset.id='image-asset:media:M'
    b.media.review_ref='prop-asset-adoption:'+asset.id+':'+fp(proof)
    assert adopted_prop_original_image(a,m,asset,b,proof).content_hash==m.content_hash


def test_native_t2i_receipt_may_omit_input_image_usage(monkeypatch):
    a,m,asset,b,proof=prop_fixture(monkeypatch)
    raw=deepcopy(proof['referenceRecord']);raw['receipt']['usage']={'generated_images':1}
    raw.pop('fingerprint')
    record=ReferenceProductionRecord.seal(**raw)
    adoption={**proof['adoptionOriginal'],'referenceProductionRef':dump_contract(record.artifact_reference())}
    asset.content['specializedAsset']['adoptionRef']['fingerprint']=fp(adoption)
    proof.update(referenceRecord=dump_contract(record),adoptionOriginal=adoption)
    proof['accountAttestation'].update(referenceProductionRef=dump_contract(record.artifact_reference()),receiptFingerprint=fp(record.receipt))
    proof['fingerprint']=fp({k:v for k,v in proof.items() if k!='fingerprint'})
    b.media.review_ref='prop-asset-adoption:'+asset.id+':'+fp(proof)
    assert adopted_prop_original_image(a,m,asset,b,proof).content_hash==m.content_hash


@pytest.mark.parametrize('change',['account','asset_type','owner','hash','subject','duty','purpose','size',
    'pending_review','design','adoption','receipt','proof','dimensions','missing'])
def test_changed_or_unqualified_prop_is_rejected_before_dispatch(monkeypatch,change):
    a,m,asset,b,proof=prop_fixture(monkeypatch)
    if change=='account':a.settings.api_key=SecretStr('another-account')
    if change=='asset_type':asset.asset_type='CHARACTER'
    if change=='owner':m.work_id='other-work'
    if change=='hash':b.media.content_hash='f'*64
    if change=='subject':b.subject_ids=('person',)
    if change=='duty':b.duties=(NS(role='CHARACTER',subject='person'),)
    if change=='purpose':m.purpose='START_FRAME'
    if change=='size':m.file_size=23
    if change=='dimensions':b.media.width=640
    if change=='pending_review':proof['referenceRecord']['stage']['attempts'][0]['review']['checks']['NO_PEOPLE']='UNKNOWN'
    if change=='design':proof['designOriginal']['design']['geometry']='Adult box'
    if change=='adoption':proof['adoptionOriginal']['decision']='REJECT'
    if change=='receipt':proof['referenceRecord']['receipt']['output_hash']='e'*64
    if change=='proof':proof['fingerprint']='e'*64
    if change=='missing':del proof['accountAttestation']
    if change!='proof':proof['fingerprint']=fp({k:v for k,v in proof.items() if k!='fingerprint'})
    with pytest.raises(DefinitelyNotSubmitted):
        adopted_prop_original_image(a,m,asset,b,proof)


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', [None, 'missing-owner', 'corrupt-proof'])
async def test_native_transport_reads_exact_prop_original_and_only_fetches_bytes(tmp_path,monkeypatch,failure):
    import httpx
    from datetime import timedelta
    from drama_plugin.contracts.media import MediaResolveResult
    from drama_plugin.execution.contracts import RequestReference
    from drama_plugin.execution.live_transport import TargetHttpTransport
    from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
    from drama_plugin.persistence.ledger import ProductionLedger
    from drama_plugin.persistence.stores import DurableReferenceExecutionStore
    from drama_plugin.production.references import ReferenceExecutionBinding
    a,m,asset,b,proof=prop_fixture(monkeypatch)
    asset.id='image-asset:media:M'
    originals=DirectorArtifactStore(tmp_path/'originals')
    pin=originals.put('prop-original-image-proof:fixture',proof)
    b.media.review_ref='prop-asset-adoption:'+asset.id+':'+pin.fingerprint
    ledger=ProductionLedger(tmp_path/'ledger.sqlite')
    binding=ReferenceExecutionBinding(binding_id='prop-fixture',version=1,scope=b.scope,
        media=dict(media_id=m.id,version='1',content_hash=m.content_hash,kind='image',
            semantics=('prop','continuity'),width=1280,height=720,review_ref=b.media.review_ref),
        duties=(dict(role='CONTINUITY',necessity='REQUIRED',subject='specialized-asset:coffin',purpose='Same object geometry'),),
        subject_ids=(),role='REFERENCE',authorization_scope='ADOPTED_PRODUCTION_INPUT',
        authority_refs=(dict(owner='professional',artifact_ref='approved-fixture-prop-use',version=1,fingerprint='a'*64),))
    ref=DurableReferenceExecutionStore(ledger).register(binding)
    selected=RequestReference(binding_ref=ref,media_id=m.id,content_hash=m.content_hash,role='REFERENCE',kind='image')
    if failure=='corrupt-proof':
        with originals._writer(): originals._write(originals._path('objects',pin.fingerprint),{'changed':True})
    calls=[]
    class Provider:
        async def get_media(self,identity):assert identity==m.id;return m
        async def get_asset(self,identity):assert identity==asset.id;return asset
        async def resolve_media(self,identity,*,provider_delivery):
            assert identity==m.id and provider_delivery
            return MediaResolveResult(media_id=m.id,url='https://objects.example.com/original-prop.png',
                mime_type=m.mime_type,size_bytes=m.file_size,expires_at=datetime.now(timezone.utc)+timedelta(minutes=10))
    def handle(request):
        calls.append(request.method)
        assert request.method=='GET' and 'authorization' not in request.headers
        return httpx.Response(200,content=b'unchanged-prop-fixture',headers={'Content-Type':'image/png'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        a.client=client;a.provider='seedance'
        transport=TargetHttpTransport(a,tmp_path/'receipts',ledger=ledger,media_provider=Provider(),
            asset_provider=Provider(),asset_originals=None if failure=='missing-owner' else originals)
        if failure:
            with pytest.raises(DefinitelyNotSubmitted): await transport.reference_url(selected,NS(scope=b.scope))
            assert calls==[]
        else:
            assert await transport.reference_url(selected,NS(scope=b.scope))=='https://objects.example.com/original-prop.png'
            assert calls==['GET']
