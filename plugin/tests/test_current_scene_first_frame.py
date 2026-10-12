"""Opening-image delivery, portrait qualification and cut semantics stay separate.

Fixtures are metadata only. No image/video model or paid endpoint is called.
"""
from datetime import datetime, timezone
from hashlib import sha256
from types import SimpleNamespace as NS
import pytest
from pydantic import SecretStr
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.contracts.media import Media
from drama_plugin.execution.reference_delivery import reviewed_original_frame
from drama_plugin.execution.transport import DefinitelyNotSubmitted
from drama_plugin.execution.live_transport import wire_payload
from drama_plugin.execution.contracts import ProviderRequest, RequestReference
from drama_plugin.production.contracts import SourceReference
from drama_plugin.generation.contracts import GenerationTask, MediaBoundary
from drama_plugin.runtime.contracts import RuntimeScope, ArtifactReference


def opening(mode='IMAGE_TO_IMAGE', face='NONE'):
    scope=RuntimeScope(work_id='W',scene_id='current-scene',shot_id='opening')
    ref=SourceReference(owner='professional',artifact_ref='current-action',version=1,fingerprint='a'*64,path=('entryState',))
    h=sha256(b'symbolic-metadata-only').hexdigest()
    receipt=dict(status='COMPLETED',diagnostics={'http_status':200},provider='ark',
        credential_source='DRAMA_VIDEO_SEEDANCE_API_KEY',model='doubao-seedream-5-0-pro-260628',
        output_hash=h,output_bytes=22,mime_type='image/png',request_fingerprint='b'*64,
        created=int(datetime.now(timezone.utc).timestamp()),usage={'input_images':int(mode=='IMAGE_TO_IMAGE')})
    proof=dict(receipt=receipt,accountAttestation=dict(evidence='HOST_OBSERVED_SYNCHRONOUS_CREATE_SAME_CONFIG',
        credentialFingerprint=sha256(b'test-key').hexdigest(),receiptFingerprint=fp(receipt)))
    proof['fingerprint']=fp(proof)
    review=dict(scope=scope.model_dump(mode='json'),output_hash=h,state_ref=ref.model_dump(mode='json'),
        authority_refs=[ref.model_dump(mode='json')],checks={'CURRENT_SCENE':'PASS','OPENING_STATE':'PASS','FACE_CLASSIFICATION':'PASS'})
    media=Media(id='current-frame',work_id='W',media_type='IMAGE',source_ref='unchanged-current-output',
        purpose='START_FRAME',content_hash=h,file_size=22,mime_type='image/png',content=dict(
            targetNativeSceneId='current-scene',targetNativeShotId='opening',imageReview=review,
            originalImageProvenance=proof,sourceInputMediaIds=['adopted-V1'] if mode=='IMAGE_TO_IMAGE' else [],
            generationMode=mode,modelId=receipt['model'],sourceCompiledRequestFingerprint='b'*64,
            faceContent=face,reviewStatus='PASS',usageMode='ADOPTED',unalteredOriginal=True))
    binding=NS(scope=scope,origin_scope=scope,role='FIRST_FRAME',endpoint_frame_ref=None,state_ref=ref,
        authority_refs=(ref,),media=NS(content_hash=h,review_ref='image-review:'+fp(review)))
    return NS(settings=NS(api_key=SecretStr('test-key'))),media,binding


def test_current_edited_environment_opening_delivers_without_fake_t2i():
    a,m,b=opening()
    identity=reviewed_original_frame(a,m,b)
    assert identity.content_hash==m.content_hash
    assert m.content['generationMode']=='IMAGE_TO_IMAGE'
    assert m.content['sourceInputMediaIds']==['adopted-V1']


def test_edited_portrait_needs_official_qualification_before_dispatch():
    a,m,b=opening(face='HUMAN_STYLE')
    with pytest.raises(DefinitelyNotSubmitted,match='SEEDANCE_EDITED_PORTRAIT_TRUST_UNVERIFIED'):
        reviewed_original_frame(a,m,b)


def test_original_qualifying_t2i_face_is_accepted_as_opening_not_character_asset():
    a,m,b=opening(mode='TEXT_TO_IMAGE',face='HUMAN_STYLE')
    assert reviewed_original_frame(a,m,b).content_hash==m.content_hash


@pytest.mark.parametrize('change',['old-scene','wrong-bytes','pending','unreviewed','unknown-face','other-account','altered','false-mode'])
def test_wrong_scope_identity_or_incomplete_proof_cannot_deliver(change):
    a,m,b=opening()
    if change=='old-scene':m.content['targetNativeSceneId']='scene1'
    if change=='wrong-bytes':b.media.content_hash='f'*64
    if change=='pending':m.content['imageReview']['checks']['OPENING_STATE']='PENDING'
    if change=='unreviewed':b.media.review_ref='unreviewed'
    if change=='unknown-face':m.content['faceContent']='UNKNOWN'
    if change=='other-account':a.settings.api_key=SecretStr('other-key')
    if change=='altered':m.content['unalteredOriginal']=False
    if change=='false-mode':m.content['generationMode']='TEXT_TO_IMAGE'
    with pytest.raises(DefinitelyNotSubmitted):reviewed_original_frame(a,m,b)


def test_cut_can_begin_new_image_without_inheriting_previous_space():
    _,_,b=opening()
    boundary=MediaBoundary(kind='CUT',predecessor_media_ref=ArtifactReference(owner='canonical-media',artifact_ref='previous',version=1),source_ref=b.state_ref)
    task=GenerationTask(input_mode='image_to_video',boundary=boundary)
    assert task.boundary.kind=='CUT' and task.continuation is None
    ref=RequestReference(binding_ref=b.state_ref,media_id='current-frame',content_hash='d'*64,role='FIRST_FRAME',kind='image')
    request=ProviderRequest(model='seedance-2-fast',input_mode='image_to_video',prompt_text='Current Scene3 opening',duration_ms=14000,native_audio='REQUIRED',references=(ref,))
    body=wire_payload(request,provider='seedance',resolution='720p',aspect_ratio='16:9')
    assert len(body['content'])==2
    assert body['content'][1]['role']=='first_frame'
    assert body['content'][1]['type']=='image_url'
    assert all(r.get('role')!='reference_video' for r in body['content'])
