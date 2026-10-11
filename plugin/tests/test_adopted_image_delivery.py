"""Mixed native inputs and rejected image provenance before a paid POST."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace as NS
from hashlib import sha256
import httpx
import pytest
from pydantic import SecretStr
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.execution.contracts import ProviderRequest, RequestReference
from drama_plugin.production.contracts import SourceReference
from drama_plugin.execution.live_transport import wire_payload
from drama_plugin.execution.reference_delivery import adopted_original_image, managed_original_url
from drama_plugin.execution.transport import DefinitelyNotSubmitted, CapabilityAbsent
from drama_plugin.runtime.contracts import RuntimeScope
from drama_plugin.contracts.media import Media, MediaResolveResult
from drama_plugin.contracts.asset import Asset


def fixture():
    key = 'fixture-secret'
    now = int(datetime.now(timezone.utc).timestamp())
    h = sha256(b'original-image').hexdigest()
    receipt = dict(status='COMPLETED', diagnostics={'http_status':200}, provider='ark',
        credential_source='DRAMA_VIDEO_SEEDANCE_API_KEY', model='doubao-seedream-5-0-pro-260628',
        output_hash=h, output_bytes=14, mime_type='image/png', task_id='task', request_fingerprint='a'*64,
        created=now, usage={'input_images':0})
    proof = dict(receipt=receipt,accountAttestation=dict(evidence='HOST_OBSERVED_SYNCHRONOUS_CREATE_SAME_CONFIG',
        credentialFingerprint=sha256(key.encode()).hexdigest(),receiptFingerprint=fp(receipt)))
    proof['fingerprint']=fp(proof)
    ref=dict(mediaId='M',duty='IDENTITY_PORTRAIT',sha256=h,generationMode='TEXT_TO_IMAGE',
        unalteredOriginal=True,modelId=receipt['model'],taskId='task',sourceRequestFingerprint='a'*64,
        generatedAt=datetime.fromtimestamp(now,timezone.utc).isoformat())
    design=dict(workId='W',assetType='CHARACTER',subjectId='person',referenceMedia=[ref])
    adoption=dict(workId='W',decision='ADOPT',subjectFingerprint=fp(design),referenceMediaIds=['M'])
    value=dict(**design,state='ADOPTED',designOriginal=design,adoptionOriginal=adoption,
        designRef={'fingerprint':fp(design)},adoptionRef={'fingerprint':fp(adoption)})
    asset=Asset(id='A',work_id='W',asset_type='CHARACTER',name='Person',
        reference_media_ids=['M'],content={'specializedAsset':value})
    media=Media(id='M',work_id='W',media_type='IMAGE',source_ref='original',file_size=14,
        content_hash=h,mime_type='image/png',content=dict(subjectId='person',generationMode='TEXT_TO_IMAGE',
        unalteredOriginal=True,sourceInputMediaIds=[],imageReview={'output_hash':h,'checks':{'IDENTITY':'PASS'}},
        reviewStatus='PASS',usageMode='ADOPTED',modelId=receipt['model'],sourceCompiledRequestFingerprint='a'*64,
        originalImageProvenance=proof))
    binding=NS(scope=RuntimeScope(work_id='W',scene_id='S',shot_id='shot'),origin_scope=RuntimeScope(work_id='W'),
        source_scope=None,subject_ids=('person',),media=NS(content_hash=h,review_ref='asset-adoption:A:'+fp(adoption)))
    adapter=NS(settings=NS(api_key=SecretStr(key)))
    return adapter,media,asset,binding


def test_mixed_image_video_wire_keeps_exact_slots_and_hashes():
    ref=SourceReference(owner='professional',artifact_ref='R',version=1,fingerprint='a'*64,path=('media',))
    refs=tuple(RequestReference(binding_ref=ref,media_id=k,content_hash='b'*64,role='REFERENCE',kind=k)
        for k in ('video','image'))
    request=ProviderRequest(model='seedance-2-fast',input_mode='reference',prompt_text='test',
        duration_ms=14000,native_audio='REQUIRED',references=refs)
    wire=wire_payload(request,provider='seedance',resolution='720p',aspect_ratio='16:9')
    assert [r['role'] for r in wire['content'][1:]]==['reference_video','reference_image']
    assert wire['content'][2]['image_url']['url']=='media:image:'+ 'b'*64
    with pytest.raises(CapabilityAbsent):
        wire_payload(request.model_copy(update={'input_mode':'image_to_video'}),provider='seedance',resolution='720p',aspect_ratio='16:9')


async def test_exact_adopted_image_get_uses_work_source_scope_and_no_credentials():
    a,m,asset,b=fixture(); identity=adopted_original_image(a,m,asset,b)
    class Store:
        async def get_media(self,_):return m
        async def resolve_media(self,_,*,provider_delivery):
            from datetime import timedelta
            assert provider_delivery
            return MediaResolveResult(media_id='M',url='https://objects.example.com/original.png',
                mime_type=m.mime_type,size_bytes=m.file_size,expires_at=datetime.now(timezone.utc)+timedelta(minutes=10))
    def handle(request):
        assert request.method=='GET' and 'authorization' not in request.headers
        return httpx.Response(200,content=b'original-image',headers={'Content-Type':'image/png'})
    async with httpx.AsyncClient(headers={'Authorization':'Bearer forbidden'},transport=httpx.MockTransport(handle)) as client:
        assert await managed_original_url(Store(),client,identity,b.origin_scope,media_id=m.id)=='https://objects.example.com/original.png'


@pytest.mark.parametrize('change',['edit','account','asset','subject','hash','receipt','expired','missing','pending'])
def test_unqualified_or_changed_image_cannot_dispatch(change):
    a,m,asset,b=fixture()
    if change=='edit':m.content['generationMode']='IMAGE_TO_IMAGE'
    if change=='account':a.settings.api_key=SecretStr('other')
    if change=='asset':asset.content['specializedAsset']['adoptionOriginal']['decision']='REJECT'
    if change=='subject':b.subject_ids=('other',)
    if change=='hash':b.media.content_hash='f'*64
    if change=='receipt':m.content['originalImageProvenance']['receipt']['output_hash']='e'*64
    if change=='expired':
        proof=m.content['originalImageProvenance'];proof['receipt']['created']-=31*86400
        asset.content['specializedAsset']['designOriginal']['referenceMedia'][0]['generatedAt']=datetime.fromtimestamp(proof['receipt']['created'],timezone.utc).isoformat()
        value=asset.content['specializedAsset'];value['designRef']['fingerprint']=fp(value['designOriginal'])
        value['adoptionOriginal']['subjectFingerprint']=value['designRef']['fingerprint']
        value['adoptionRef']['fingerprint']=fp(value['adoptionOriginal']);b.media.review_ref='asset-adoption:A:'+value['adoptionRef']['fingerprint']
        proof['accountAttestation']['receiptFingerprint']=fp(proof['receipt']);proof['fingerprint']=fp({k:v for k,v in proof.items() if k!='fingerprint'})
    if change=='missing':del m.content['originalImageProvenance']
    if change=='pending':m.content['imageReview']['checks']['IDENTITY']='PENDING'
    with pytest.raises(DefinitelyNotSubmitted):adopted_original_image(a,m,asset,b)
