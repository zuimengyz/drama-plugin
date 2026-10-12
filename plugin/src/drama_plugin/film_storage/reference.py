from __future__ import annotations
from typing import Any
from drama_plugin.contracts.base import canonical_json,sha256_canonical
from drama_plugin.film_storage.projection import ensure_media,ensure_scene

async def project_reference(store:Any,body:dict[str,Any],event:str,order:int,*,source_ref:str|None=None)->None:
    frame=body.get('frame')
    if not frame:return
    scope=body['scope'];work=scope['workId'];scene=scope['sceneId']
    await ensure_scene(store,work,scene,event,order)
    request=frame['request'];wire=request.get('body',{})
    prompt=wire.get('prompt') or frame.get('prompt')
    if not isinstance(prompt,str):raise ValueError('Actual compiled still prompt is required')
    model=wire.get('model') or frame['template']['model']
    doc=await store.client.prompt_id(work,prompt)
    await store.client.document(work,'GENERATION_PROMPT',doc,prompt.encode(),event,order)
    stage=body.get('stage');receipt=body.get('receipt') or {}
    attempts=stage.get('attempts',[]) if stage else []
    attempt=next((a for a in attempts if a.get('attempt_id')==receipt.get('attempt_id')),None) if receipt else None
    if attempt is None:
        matching=[a for a in attempts if a.get('frame_fingerprint')==frame.get('fingerprint')]
        attempt=matching[-1] if matching else {}
    rid='image-request:'+attempt['attempt_id'] if attempt.get('attempt_id') else 'image-operation:'+sha256_canonical([body['runId'],frame.get('fingerprint')])
    status='SUCCEEDED' if receipt.get('status')=='COMPLETED' else 'FAILED' if receipt.get('status')=='FAILED' else 'SUBMITTING' if attempt.get('submission_started') else 'PREPARED'
    await store.client.rows([store.row('drama_generation_request',event,order,id=rid,work_id=work,scene_id=scene,
        operation_id=body['runId'],attempt_id=attempt.get('attempt_id'),operation_type='IMAGE',
        provider=receipt.get('provider') or request.get('provider','comfy'),model=model,provider_task_id=receipt.get('task_id') if receipt.get('provider') not in {None,'ark'} else None,
        provider_request_id=receipt.get('diagnostics',{}).get('request_id') if receipt else None,
        prompt_media_id=doc,status=status,input_evidence='COMPLETE' if receipt else 'BOUND_PRE_DISPATCH',request_fingerprint=sha256_canonical(request),
        source_ref=source_ref or 'asset-reference-production:'+body['fingerprint'])])
    refs=[frame['spec']['edit_source']] if frame['spec'].get('edit_source') else frame['spec'].get('references',[])
    if bool(wire.get('image'))!=bool(refs) and receipt and receipt.get('provider')=='ark':raise ValueError('Posted image mode differs from its actual source bindings')
    for i,ref in enumerate(refs):
        file=await ensure_media(store,ref['media_id'],event,order)
        candidates=await store.client.query('drama_asset',{'media_id':ref['media_id']},1)
        subject=ref.get('entity_key') if ref.get('kind')=='CHARACTER' else candidates[0].get('character_id') if candidates else None
        if subject and not await store.client.query('drama_character',{'id':subject},1):subject=None
        await store.client.rows([store.row('drama_request_input',event,order,request_id=rid,ordinal=i,
            media_id=file['id'],content_hash=ref['content_hash'],character_id=subject,
            purpose='CHARACTER_IDENTITY_IMAGE' if subject else 'SCENE_REFERENCE' if ref.get('kind')=='SCENE' else 'EDIT_SOURCE',
            provider_role='image',binding_ref=ref.get('asset_id'))])
    delivery=body.get('delivery')
    if not delivery:return
    file=await ensure_media(store,delivery['mediaId'],event,order)
    if file['media_type']!='IMAGE':raise ValueError('Still recovery cannot index a video as an image')
    existing=await store.client.query('drama_asset',{'media_id':file['id']},1)
    if existing and existing[0].get('request_id') is None:
        await store.client.rows([store.row('drama_asset',event+':request',order+1,id=existing[0]['id'],request_id=rid)])
    if not existing:
        await store.client.rows([store.row('drama_asset',event,order,id='image-asset:'+file['id'],work_id=work,
            asset_type='OTHER',name='已回收图片；具体采用由专用资产原件负责',media_id=file['id'],
            identity_key='file:'+file['id'],version=1,request_id=rid,state='CANDIDATE',
            source_ref=source_ref or 'asset-reference-production:'+body['fingerprint'])])
    # Registration/adoption projection consumes the actual accepted Asset event,
    # not a PASS review or a convenient generated frame.

