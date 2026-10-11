"""No pixels generated: symbolic PNG header and mocked retained Media only."""
import base64
import hashlib
import json
from pathlib import Path
import struct
import pytest
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual.frame_request import FrameSpec, Reference, compile_frame, verify_compiled
from drama_plugin.providers.ark_image import CAPABILITY, IMAGE_TO_IMAGE_CAPABILITY, image_payload, inline_image
from drama_plugin.professional_design.asset_sequence import AssetChoice
from test_target_reference_production import reference_frame
from test_visual_prompt_ir import visual_ir, fact


def symbolic_input(tmp_path,monkeypatch):
    # Metadata-only fixture, not a decodable image or new physical media.
    data=b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',32,32)
    digest=hashlib.sha256(data).hexdigest();local=tmp_path/'virtual-retained-input'
    read=Path.read_bytes
    monkeypatch.setattr(Path,'read_bytes',lambda p:data if p==local else read(p))
    receipt=tmp_path/'inline.json'
    receipt.write_text(json.dumps({'name':'inline:'+digest,'content_hash':digest,'transport':'INLINE_BASE64','provider':'ark'}))
    ref=Reference(entity_key='selected-person',kind='CHARACTER',asset_id='accepted-A',media_id='retained-A',
        version='1',content_hash=digest,local_path=str(local),upload_name='inline:'+digest,uploaded_hash=digest,
        upload_receipt=str(receipt),facts='Approved narrow face',state='Exact adopted reference',review='PASS')
    return data,ref


def reference_spec(ref):
    item={'subjectId':'selected-person','designRef':{'key':'approved','kind':'CANON','fingerprint':'a'*64},
        'assetType':'CHARACTER','name':'Selected person','design':{'face':'Approved narrow face'}}
    base=reference_frame(item)
    spec=base.model_copy(update={'references':(ref,),'reference_lock':{f'{ref.asset_id}/{ref.media_id}/{ref.version}':ref.content_hash},
        'identity_bootstrap':None,'prompt_ir':None,'image_mode':'image_to_image'})
    from drama_plugin.config.production_routes import selected
    ir=visual_ir('REFERENCE_EDIT',selected()['image_model'])
    ir['subjects'][0].update(id='selected-person',face=fact(base.actors[0].identity))
    ir['preserve']=[fact('The selected person identity and proportions')]
    ir['edit_delta']=[{'operation':'replace','region':'costume','source_issue':fact('Previous clothing state'),
        'target_correction':fact('Approved worn wool clothing variation')}]
    ir['source_fingerprint']=fp(spec.model_dump(mode='json',exclude={'prompt_ir'}))
    return spec.model_copy(update={'prompt_ir':ir})


def test_default_t2i_seal_unchanged_and_explicit_i2i_delivers_exact_bytes(tmp_path,monkeypatch):
    data,ref=symbolic_input(tmp_path,monkeypatch);spec=reference_spec(ref)
    compiled=compile_frame(spec);verify_compiled(compiled)
    body=compiled['request']['body']
    assert base64.b64decode(body['image'].split(',',1)[1])==data
    assert compiled['template']['graph_hash']==fp(IMAGE_TO_IMAGE_CAPABILITY)
    assert compiled['prompt_ir_compilation']['ir']['task']['task_type']=='REFERENCE_EDIT'
    assert compiled['spec']['actors'][0]['entity_key']==ref.entity_key
    t2i=spec.model_copy(update={'image_mode':'text_to_image','references':(), 'reference_lock':{},
        'identity_bootstrap':'Inherited identity text design','prompt_ir':None})
    raw=t2i.model_dump(mode='json');assert 'image_mode' not in raw
    t=compile_frame(t2i)
    assert 'image' not in t['request']['body'] and t['template']['graph_hash']==fp(CAPABILITY)
    assert t['fingerprint']==compile_frame(FrameSpec.model_validate(raw))['fingerprint']
    assert not list(tmp_path.rglob('*.png'))


def test_implicit_i2i_and_missing_explicit_input_are_rejected(tmp_path,monkeypatch):
    _,ref=symbolic_input(tmp_path,monkeypatch);spec=reference_spec(ref)
    with pytest.raises(ValueError,match='ARK_IMAGE_CAPABILITY_MISMATCH'):
        compile_frame(spec.model_copy(update={'image_mode':'text_to_image'}))
    with pytest.raises(ValueError,match='ARK_IMAGE_CAPABILITY_MISMATCH'):
        compile_frame(spec.model_copy(update={'references':(),'reference_lock':{},'identity_bootstrap':'Initial text identity'}))
    with pytest.raises(ValueError,match='EXPLICIT_IMAGE_TO_IMAGE'):
        AssetChoice(asset_type='PROP',name='Prop',design={'wood':'worn'},reference_selections=(0,))


def test_wire_uses_ordered_images_and_keeps_existing_reference_cap(tmp_path,monkeypatch):
    data,_=symbolic_input(tmp_path,monkeypatch)
    from drama_plugin.config.production_routes import selected
    model=selected()['image_model'];image=inline_image(data)
    plain=image_payload(model,'Approved reference',(2560,1440),1)
    assert 'image' not in plain
    multi=image_payload(model,'Approved reference',(2560,1440),1,images=(image,image))
    assert multi['image']==[image,image]
    with pytest.raises(ValueError,match='REFERENCE_PLAN_CAP'):
        image_payload(model,'Approved reference',(2560,1440),1,images=(image,)*4)
    with pytest.raises(ValueError,match='DIMENSIONS'):
        inline_image(b'\x89PNG\r\n\x1a\n'+b'\0'*8+struct.pack('>II',1,1))


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['text_to_image','image_to_image'])
async def test_inherited_reference_reaches_formal_artist_and_exact_projection(tmp_path,monkeypatch,mode):
    from test_asset_sequence import Author,plugin,request_for,resolve
    from drama_plugin.professional_design.asset_sequence import AssetPreparationPending
    author=Author(variant=True);p=plugin(tmp_path,monkeypatch,author)
    _,request=request_for(p,'s-1')
    await resolve(p,request,author)
    _,request=request_for(p,'s-2')
    await resolve(p,request,author)
    original=author.design_assets
    async def explicit(request):
        draft=await original(request)
        return draft.model_copy(update={'assets':tuple(c.model_copy(update={'reference_mode':mode})
            if c.variant_reason else c for c in draft.assets)})
    author.design_assets=explicit
    inputs,request=request_for(p,'s-3')
    try:await p.professional_design.prepare_assets(request)
    except AssetPreparationPending as pending:
        packet=p.asset_sequence.objects.read_ref(pending.ref)
        assert any(r.get('referenceMode','text_to_image')==mode and r.get('variantReason') for r in packet['requirements'])
    # Verify projection of the selected inherited requirement directly,
    # using the completed Scene's immutable preparation original.
    prepared_ref=p.asset_sequence.objects._read(p.asset_sequence.objects._path('asset-scene-design',
        [p.asset_sequence.selected(request).fingerprint,'s-3']))
    from drama_plugin.contracts.source_pin import SourcePin
    packet=p.asset_sequence.objects.read_ref(SourcePin.model_validate(prepared_ref))
    item=next(r for r in packet['requirements'] if r.get('variantReason'))
    data,ref=symbolic_input(tmp_path,monkeypatch)
    base_id=item['inheritedFromAssetId'];base=await p.providers.asset.get_asset(base_id)
    ref=ref.model_copy(update={'asset_id':base.id,'entity_key':item['subjectId'],'media_id':base.reference_media_ids[0],
        'version':str(base.content['specializedAsset']['revision'])})
    # Formal artwork author tested through the real composition projection, no model.
    from drama_plugin.creative_engine.backends import FormalProfessionalAuthor
    payloads=[]
    class Client:
        async def complete(self,*args,**kwargs):
            payloads.append(kwargs['model_payload']['selectedAssetReference'])
            semantic=reference_spec(ref).model_dump(mode='json')
            if mode=='text_to_image':
                semantic['prompt_ir']['edit_delta']=[]
                semantic['prompt_ir']['preserve']=[]
            for k in ('shot_id','shot_fingerprint','references','reference_lock','image_mode','identity_bootstrap'):
                semantic.pop(k,None)
            semantic['actors'][0].pop('entity_key')
            semantic['prompt_ir']['subjects'][0].pop('id')
            semantic['prompt_ir'].pop('source_fingerprint')
            for k in ('task_type','input_mode','provider_family'):semantic['prompt_ir']['task'].pop(k)
            return kwargs['project'](semantic)
    artist=FormalProfessionalAuthor(Client(),Path(__file__).parents[1]/'skills')
    frame=FrameSpec.model_validate(await artist.design_asset_reference(request,item,
        reference_inputs=(ref,) if mode=='image_to_image' else ()))
    assert frame.image_mode==mode
    assert frame.actors[0].entity_key==item['subjectId']
    if mode=='image_to_image':
        assert frame.identity_bootstrap is None
        assert frame.references[0].asset_id==item['inheritedFromAssetId']
        assert compile_frame(frame)['request']['body']['image']==inline_image(data)
    else:
        assert not frame.references and 'inherited adopted identity' in frame.identity_bootstrap
        assert 'image' not in compile_frame(frame)['request']['body']
    # Continue through the actual Target owner, with symbolic readback only.
    from drama_plugin.contracts.media import Media,MediaType
    parent_media=await p.providers.media.get_media(base.reference_media_ids[0])
    p.providers.media.data.media=[m.model_copy(update={'content_hash':ref.content_hash})
        if m.id==parent_media.id else m for m in p.providers.media.data.media]
    for row in packet['requirements']:
        if row.get('reuseAssetId') or row['requirementKey']==item['requirementKey']:continue
        mid='offline-room-reference'
        p.providers.media.data.media.append(Media(id=mid,work_id='offline-sequence',media_type=MediaType.IMAGE,
            purpose='LOCATION_REFERENCE',source_ref='offline-symbolic-room',content_hash='b'*64,content={}))
        adoption=p.screenplays.objects.put('offline-room-adoption',{'decision':'ADOPT','workId':'offline-sequence',
            'subjectFingerprint':row['designRef']['fingerprint'],'referenceMediaIds':[mid]})
        await p.asset_sequence.accept(SourcePin.model_validate(prepared_ref),row['requirementKey'],
            adoption_ref=adoption,reference_media_ids=(mid,))
    async def symbolic_readback(provider,expected,cache):
        return {'mediaId':parent_media.id,'contentHash':ref.content_hash,'cachePath':ref.local_path,
            'technical':{'streams':[{'width':32,'height':32}]},'persistenceStatus':'VERIFIED'}
    import drama_plugin.professional_design.reference_production as native
    monkeypatch.setattr(native,'verify_media',symbolic_readback)
    author.design_asset_reference=artist.design_asset_reference
    result=await p.reference_production.pending(SourcePin.model_validate(prepared_ref),inputs.run_id,request)
    child=next(r.artifact_ref for r in result.artifact_refs if r.owner=='runtime')
    actual=p.reference_production.get(child)
    assert payloads[-1]['inheritedDesign']==base.content['specializedAsset']['design']
    if mode=='image_to_image':
        assert actual.frame['request']['body']['image']==inline_image(data)
        assert actual.frame['spec']['references'][0]['asset_id']==item['inheritedFromAssetId']
        assert payloads[-1]['referenceInputs'][0]['asset_id']==item['inheritedFromAssetId']
    else:
        assert 'image' not in actual.frame['request']['body']
        assert payloads[-1]['referenceInputs']==[]
    assert actual.receipt is None and actual.stage is None
    assert not list(tmp_path.rglob('*.png'))
