"""Read exact existing owners, project small relations/files. No history-to-adoption inference."""
from __future__ import annotations
import json,sqlite3
from typing import Any,cast
import yaml  # type: ignore[import-untyped]
from drama_plugin.contracts.base import canonical_json,sha256_canonical,dump_contract
from drama_plugin.film_storage.client import FilmStorageUnavailable

def ledger_paths(store:Any)->list[Any]:
    native=getattr(getattr(getattr(store,'plugin',None),'ledger',None),'path',None)
    return list(dict.fromkeys(path for path in (native,store.root/'production.sqlite3') if path is not None and path.exists()))

def actual_wire(store:Any,client_id:str)->dict[str,Any]|None:
    files=[file for path in ledger_paths(store) for file in path.with_name(path.name+'.receipts').glob(client_id+'.*.wire.json')]
    values={file.read_bytes() for file in files}
    if len(values)!=1:return None
    raw=json.loads(next(iter(values)))
    return raw if isinstance(raw,dict) and isinstance(raw.get('model'),str) else None

def ledger_body(store:Any,ref:dict[str,Any],expected_type:str|None=None)->tuple[dict[str,Any],dict[str,Any]]:
    for path in ledger_paths(store):
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            row=db.execute('SELECT * FROM immutable_artifact WHERE artifact_id=? AND version=?',
                (ref['artifactRef'],ref['version'])).fetchone()
        if row is None:continue
        if row['artifact_type']!=(expected_type or ref['owner']):raise FilmStorageUnavailable('Retained source owner differs')
        body=json.loads(row['body_json'])
        return body,{'workId':row['work_id'],'sceneId':row['scene_id'],'shotId':row['shot_id']}
    raise FilmStorageUnavailable('Exact retained source artifact is missing')

async def ensure_scene(store:Any,work:str,scene:str|None,event:str,order:int)->None:
    if scene is None:return
    if not await store.client.query('drama_scene',{'id':scene},1):
        # A real execution scope proves the Scene identity, not a guessed title/location/order.
        await store.client.rows([store.row('drama_scene',event,order,id=scene,work_id=work,title=scene,source_ref=event)])

async def ensure_media(store:Any,media_id:str,event:str,order:int,*,delivery_path:str|None=None,expected_hash:str|None=None)->dict[str,Any]:
    known=await store.client.query('drama_media',{'id':media_id},1)
    if known:return cast(dict[str,Any],known[0])
    if media_id.startswith('media:sha256:'):
        # This is the Ledger's virtual identity. Resolve only its original formal
        # registration, never invent another business Media ID from a matching hash.
        found:list[str]=[]
        for path in ledger_paths(store):
            with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
                rows=db.execute("SELECT body_json FROM immutable_artifact WHERE artifact_type='formal-media-registration'").fetchall()
            found.extend(json.loads(r[0])['canonicalMediaRef']['artifactRef'] for r in rows
                if json.loads(r[0])['identity']['mediaId']==media_id)
        if len(set(found))!=1:
            # Old virtual IDs may lack a formal registration. A preserved actual
            # wire URL identifies the exact object key; hash and Work are checked
            # as additional evidence, never used alone to invent an alias.
            if delivery_path and expected_hash:
                from urllib.parse import unquote
                path=unquote(delivery_path).lstrip('/')
                files=await store.client.query('drama_media',{'content_hash':expected_hash},100)
                exact=[f for f in files if path==f['bucket_name']+'/'+f['object_key'] or path==f['object_key'] or path.endswith('/'+f['object_key']) or path.endswith('/'+f['id'])]
                if len(exact)==1:return cast(dict[str,Any],exact[0])
            raise FilmStorageUnavailable('Exact canonical Media registration is not retained yet')
        media_id=found[0]
        # A new Native video was already imported directly into Film V2.
        # Resolve its canonical ID in that index before trying legacy import.
        known=await store.client.query('drama_media',{'id':media_id},1)
        if known:return cast(dict[str,Any],known[0])
    return cast(dict[str,Any],await store.client.request('existing-file',method='POST',body={
        'mediaId':media_id,'sourceEvent':event,'sourceOrder':order}))

async def store_asset(store:Any,asset:Any,event:str,order:int)->None:
    s=asset.content.get('specializedAsset')
    if not isinstance(s,dict) or s.get('state')!='ADOPTED' or not store.plugin.asset_sequence._proof(asset):
        raise ValueError('Only an actually registered, source-proved adopted asset can be projected as adopted')
    subject=s.get('subjectId');work=asset.work_id;identity=s['stableIdentity']
    if s.get('filmStorageValidated') is True:
        # The registered V2 asset already owns its immutable verified design MD.
        # Do not transcribe it into another competing representation on replay.
        scene=s.get('sceneId') or s.get('establishedSceneId')
        if scene:
            await ensure_scene(store,work,scene,event,order)
            await store.client.rows([store.row('drama_scene_asset',event,order,scene_id=scene,asset_id=asset.id,
                purpose='CHARACTER_IDENTITY' if subject else 'SCENE_ASSET',source_ref=canonical_json(s['designRef']))])
        return
    if subject and not await store.client.query('drama_character',{'id':subject},1):
        await store.client.rows([store.row('drama_character',event,order,id=subject,work_id=work,
            name=asset.name,identity_ref=identity)])
    # Keep concrete design and small provenance in readable Markdown. No copied
    # ScenePreparationOriginal, Work, Package, prompt body or production snapshot.
    metadata={k:s[k] for k in ('subjectId','stableIdentity','revision','assetType','name','designRef','adoptionRef',
        'inheritedFromAssetId','variantReason','sceneId','sources') if k in s}
    metadata['referenceMediaIds']=list(asset.reference_media_ids)
    text='# '+asset.name+'\n\n## 具体设计\n\n```yaml\n'+yaml.safe_dump(s['design'],allow_unicode=True,sort_keys=False)+'```\n\n## 来源与采用引用\n\n```yaml\n'+yaml.safe_dump(metadata,allow_unicode=True,sort_keys=False)+'```\n'
    doc='asset-design:'+s['designRef']['fingerprint']
    await store.client.document(work,'ASSET_DESIGN',doc,text.encode(),event,order)
    for i,mid in enumerate(asset.reference_media_ids):
        media=await ensure_media(store,mid,event,order)
        if media['media_type']!='IMAGE':continue  # Video identity evidence stays a video, not an image Asset.
        existing=await store.client.query('drama_asset',{'media_id':mid},1)
        if existing and existing[0]['id']!=asset.id:
            continue  # A reused body/reference remains the same image index; no copied bytes.
        aid=asset.id if i==0 else 'image-asset:'+mid
        fields={'id':aid,'work_id':work,'character_id':subject,'asset_type':s['assetType'] if i==0 else 'COSTUME',
            'name':asset.name if i==0 else asset.name+'｜既有身体／服装参考', 'media_id':mid,'identity_key':identity,
            'version':s['revision'],'design_media_id':doc,'state':'ADOPTED','review_outcome':'PASS',
            'adoption_ref':canonical_json(s['adoptionRef']),'source_ref':canonical_json(s['designRef'])}
        parent=s.get('inheritedFromAssetId') if i==0 else asset.id
        if parent and await store.client.query('drama_asset',{'id':parent},1):fields['parent_asset_id']=parent
        await store.client.rows([store.row('drama_asset',event,order,**fields)])
    scene=s.get('sceneId') or s.get('establishedSceneId')
    if scene:
        await ensure_scene(store,work,scene,event,order)
        await store.client.rows([store.row('drama_scene_asset',event,order,scene_id=scene,asset_id=asset.id,
            purpose='CHARACTER_IDENTITY' if subject else 'SCENE_ASSET',source_ref=canonical_json(s['designRef']))])

async def request_for_attempt(store:Any,ref:dict[str,Any],event:str,order:int)->str:
    attempt,scope=ledger_body(store,ref);op,_=ledger_body(store,attempt['operationRef'])
    final,_=ledger_body(store,op['finalPromptRef'])
    work=scope['workId'];await ensure_scene(store,work,scope['sceneId'],event,order)
    wire=actual_wire(store,attempt['clientIdentity'])
    text='\n'.join(i['text'] for i in wire.get('content',[]) if i.get('type')=='text') if wire else final['promptText']
    media=await store.client.prompt_id(work,text)
    await store.client.document(work,'GENERATION_PROMPT',media,text.encode(),event,order)
    rid=ref['artifactRef'];fields={'id':rid,'work_id':work,'scene_id':scope['sceneId'],'logical_shot_id':scope['shotId'],
        'operation_id':attempt['operationRef']['artifactRef'],'attempt_id':attempt['clientIdentity'],
        'operation_type':'VIDEO','provider':attempt['provider'],'model':wire['model'] if wire else None,'declared_model':op['model'],'provider_task_id':None,
        'prompt_media_id':media,'status':'PREPARED','input_evidence':'BOUND_PRE_DISPATCH' if not wire else 'PARTIAL',
        'request_fingerprint':attempt['requestFingerprint'],'source_ref':canonical_json(ref)}
    existing=await store.client.query('drama_generation_request',{'id':rid},1)
    if existing:
        # Replaying an earlier immutable preparation is not a new transition back
        # to PREPARED, nor may it erase an already returned remote task identity.
        for key in ('status','provider_task_id'):
            fields.pop(key,None)
        if not wire:
            for key in ('model','prompt_media_id','input_evidence'):fields.pop(key,None)
    await store.client.rows([store.row('drama_generation_request',event,order,**fields)])
    await project_inputs(store,op,rid,event,order,wire)
    return str(rid)

def official_continuation_delivered(store:Any,binding:dict[str,Any],file:dict[str,Any],url:str,scope:dict[str,Any])->bool:
    """An official tail URL is not a MinIO key; prove its exact retained lineage."""
    ref=binding.get('endpointFrameRef')
    if binding.get('role')!='FIRST_FRAME' or not isinstance(ref,dict) or ref.get('owner')!='continuation-frame':return False
    try:
        frame,frame_scope=ledger_body(store,ref,'continuation-frame')
        receipt,receipt_scope=ledger_body(store,frame['receiptRef'],'provider-receipt')
    except (FilmStorageUnavailable,KeyError,ValueError):return False
    media=frame.get('media',{})
    return bool(url and frame_scope==receipt_scope==scope==binding.get('scope')==frame.get('scope')==receipt.get('scope')
        and receipt.get('state')=='SUCCEEDED' and receipt.get('provider')=='seedance'
        and receipt.get('runId')==frame.get('runId') and receipt.get('lastFrameUrl')==url
        and media.get('mediaId')==binding['media']['mediaId']
        and media.get('contentHash')==binding['media']['contentHash']==file.get('content_hash')
        and media.get('byteCount')==file.get('file_size') and media.get('kind')=='IMAGE'
        and file.get('media_type')=='IMAGE' and file.get('storage_state')=='READY')

async def project_inputs(store:Any,op:dict[str,Any],rid:str,event:str,order:int,wire:dict[str,Any]|None=None)->None:
    delivered=[];delivered_urls=[]
    if wire:
        from urllib.parse import urlsplit,unquote
        for part in wire.get('content',[]):
            if part.get('type')=='text':continue
            value=part.get(part.get('type',''),{})
            url=value.get('url','') if isinstance(value,dict) else ''
            delivered_urls.append(url)
            delivered.append(unquote(urlsplit(url).path))
    verified=[]
    for i,binding_ref in enumerate(op.get('referenceBindings',[])):
        binding,_=ledger_body(store,{'owner':'reference-execution-binding','artifactRef':binding_ref['artifactRef'],'version':binding_ref['version']})
        file=await ensure_media(store,binding['media']['mediaId'],event,order,delivery_path=delivered[i] if i<len(delivered) else None,expected_hash=binding['media']['contentHash'])
        verified.append(bool(wire and i<len(delivered) and (delivered[i].endswith('/'+file['object_key'])
            or delivered[i].endswith('/'+file['id'])
            or official_continuation_delivered(store,binding,file,delivered_urls[i],op['scope']))))
        role=binding['role'];provider_role=role;kinds={d['role'] for d in binding.get('duties',[])}
        if role not in {'FIRST_FRAME','LAST_FRAME'}:
            role=('FIRST_FRAME' if file['purpose']=='FIRST_FRAME' else
                'CHARACTER_IDENTITY_'+file['media_type'] if kinds & {'IDENTITY','CHARACTER'} else
                'SCENE_REFERENCE' if 'ENVIRONMENT' in kinds else 'REFERENCE_'+file['media_type'])
        ids=binding.get('subjectIds',[]);character=None
        if role.startswith('CHARACTER_IDENTITY') and len(ids)==1 and await store.client.query('drama_character',{'id':ids[0]},1):character=ids[0]
        await store.client.rows([store.row('drama_request_input',event,order,request_id=rid,ordinal=i,media_id=file['id'],
            purpose=role,provider_role=provider_role,character_id=character,binding_ref=canonical_json(binding_ref),content_hash=binding['media']['contentHash'])])
    if wire and len(delivered)==len(verified) and all(verified):
        await store.client.rows([store.row('drama_generation_request',event+':delivered',order+1,id=rid,input_evidence='COMPLETE')])

async def superseded_by_revision(store:Any,candidate:dict[str,Any],event:str,order:int)->None:
    operation_ref=candidate.get('operationRef')
    if not isinstance(operation_ref,dict):return
    operation,scope=ledger_body(store,operation_ref)
    # The existing Runtime already pins one explicitly authorized replacement
    # position. Same Shot, another take, a later timestamp or PASS is insufficient.
    revision_ref=None
    for path in ledger_paths(store):
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            row=db.execute("SELECT value_json FROM ledger_index WHERE index_type='film-segment-dispatch-revision' AND index_key=?",(operation['runId'],)).fetchone()
        if row:
            revision_ref=json.loads(row[0]);break
    if revision_ref is None:return
    revision,revised_scope=ledger_body(store,revision_ref)
    if revised_scope!=scope or revision['replacementRunId']!=operation['runId']:raise ValueError('EXACT_REPLACEMENT_SCOPE_REQUIRED')
    previous=revision['previousRunId']
    if revision['previousCheckpoint']['sceneMediaRunIds'][revision['slot']]!=previous:raise ValueError('EXACT_REPLACEMENT_POSITION_REQUIRED')
    for path in ledger_paths(store):
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            rows=db.execute("SELECT body_json FROM immutable_artifact WHERE artifact_type='media-binding'").fetchall()
        for row in rows:
            prior=json.loads(row[0])
            if prior['runId']!=previous:continue
            prior_operation,prior_scope=ledger_body(store,prior['operationRef'])
            if prior_scope!=scope:raise ValueError('PREVIOUS_MEDIA_SCOPE_DIFFERS')
            file=await ensure_media(store,prior['media']['mediaId'],event,order)
            for take in await store.client.query('drama_shot',{'media_id':file['id']},1):
                await store.client.rows([store.row('drama_shot',event+':explicit-replacement',order,
                    id=take['id'],take_no=take['take_no'],state='SUPERSEDED',retention_reason=canonical_json(revision_ref))])

async def project_event(store:Any,event:dict[str,Any],identity:str,order:int)->None:
    if event['kind']=='ASSET':
        await store_asset(store,await store.plugin.providers.asset.get_asset(event['assetId']),identity,order);return
    kind=event['type'];body,scope=ledger_body(store,event['ref'],kind);work=scope['workId']
    if kind=='provider-attempt':
        await request_for_attempt(store,event['ref'],identity,order)
    elif kind=='provider-receipt':
        rid=body['attemptRef']['artifactRef']
        if not await store.client.query('drama_generation_request',{'id':rid},1):
            await request_for_attempt(store,body['attemptRef'],identity+':request',order-1)
        wire=actual_wire(store,body['clientIdentity'])
        if wire:await request_for_attempt(store,body['attemptRef'],identity+':wire',order-2)
        update={'provider_task_id':body['remoteIdentity'],'status':body['state']}
        if wire:update['model']=wire['model']
        await store.client.rows([store.row('drama_generation_request',identity,order,id=rid,**update)])
    elif kind=='media-binding':
        file=await ensure_media(store,body['media']['mediaId'],identity,order)
        scene=scope['sceneId'];shot=scope['shotId']
        if file['media_type']!='VIDEO' or scene is None or shot is None:return
        await ensure_scene(store,work,scene,identity,order)
        rid=body['attemptRef']['artifactRef']
        if not await store.client.query('drama_generation_request',{'id':rid},1):
            await request_for_attempt(store,body['attemptRef'],identity+':request',order-1)
        prior=await store.client.query('drama_shot',{'media_id':file['id']},1)
        if prior:return
        takes=await store.client.query('drama_shot',{'id':shot},100)
        number=max([t['take_no'] for t in takes]+[0])+1
        await store.client.rows([store.row('drama_shot',identity,order,id=shot,take_no=number,work_id=work,scene_id=scene,
            title=shot,media_id=file['id'],request_id=rid,state='CANDIDATE',source_ref=canonical_json(event['ref']))])
    elif kind=='reference-execution-binding':
        file=await ensure_media(store,body['media']['mediaId'],identity,order)
        if scope['sceneId'] and file['media_type']=='IMAGE':
            await ensure_scene(store,work,scope['sceneId'],identity,order)
            for asset in await store.client.query('drama_asset',{'media_id':file['id']},1):
                await store.client.rows([store.row('drama_scene_asset',identity,order,scene_id=scope['sceneId'],
                    asset_id=asset['id'],purpose=body['role'],source_ref=canonical_json(event['ref']))])
    elif kind=='formal-media-registration':
        await ensure_media(store,body['canonicalMediaRef']['artifactRef'],identity,order)
    elif kind=='creative-media-review':
        file=await ensure_media(store,body['media']['mediaId'],identity,order)
        for table in ('drama_shot','drama_asset'):
            rows=await store.client.query(table,{'media_id':file['id']},1)
            if rows:
                r=rows[0];keys={'id':r['id'],**({'take_no':r['take_no']} if table=='drama_shot' else {})}
                # PASS/REVISE are review facts. Neither is a user adoption/discard decision.
                await store.client.rows([store.row(table,identity,order,**keys,review_outcome=body['outcome'])])
    elif kind=='production-package':
        from drama_plugin.creative_engine.contracts import DesignBody
        from drama_plugin.creative_engine.sources import NativeCreativeSources
        from drama_plugin.creative_engine.store import CreativeVersionStore
        from drama_plugin.production.contracts import SourceReference
        native_store=getattr(getattr(store,'plugin',None),'creative_versions',None)
        archive_store=CreativeVersionStore(store.root/'creative-authority')
        native=NativeCreativeSources(native_store or archive_store)
        for source in body.get('sources',[]):
            reference=source.get('reference',source)
            if reference.get('owner')!='professional' or not reference.get('fingerprint') or not reference.get('artifactRef','').startswith('creative-professional:'):continue
            # Package fingerprints identify OwnedSource projections, not whole
            # CreativeVersion seals. Use the existing exact projection resolver.
            try:design=native.exact_projection(SourceReference.model_validate(reference))
            except (OSError,KeyError,ValueError):
                design=NativeCreativeSources(archive_store).exact_projection(SourceReference.model_validate(reference))
            if not isinstance(design.body,DesignBody):raise ValueError('Package source is not a professional design')
            bindings=design.body.facts.get('assetBindings',[])
            if not isinstance(bindings,list):raise ValueError('Retained asset bindings are malformed')
            for asset in bindings:
                if not isinstance(asset,dict):raise ValueError('Retained asset binding is malformed')
                aid=asset.get('assetId') or asset.get('id')
                if aid and scope['sceneId']:
                    await ensure_scene(store,work,scope['sceneId'],identity,order)
                    await store.client.rows([store.row('drama_scene_asset',identity,order,scene_id=scope['sceneId'],
                        asset_id=aid,purpose=asset.get('assetType','asset:'+str(asset.get('asset_type','REFERENCE'))),source_ref=canonical_json(event['ref']))])
    elif kind=='execution-operation':
        final,_=ledger_body(store,body['finalPromptRef'])
        await ensure_scene(store,work,scope['sceneId'],identity,order)
        doc=await store.client.prompt_id(work,final['promptText'])
        await store.client.document(work,'GENERATION_PROMPT',doc,final['promptText'].encode(),identity,order)
        await store.client.rows([store.row('drama_generation_request',identity,order,id=event['ref']['artifactRef'],
            work_id=work,scene_id=scope['sceneId'],logical_shot_id=scope['shotId'],operation_id=event['ref']['artifactRef'],
            attempt_id=None,operation_type='VIDEO',provider=body['route'],model=None,declared_model=body['model'],
            provider_task_id=None,prompt_media_id=doc,status='ESTABLISHED',input_evidence='BOUND_PRE_DISPATCH',
            source_ref=canonical_json(event['ref']))])
        await project_inputs(store,body,event['ref']['artifactRef'],identity,order)
    elif kind=='final-prompt':return
    elif kind=='user-decision':
        if body.get('category') not in {'ADOPTION','FINAL_ACCEPTANCE'}:return
        # Only named candidate media covered by the existing decision may change state.
        source=body.get('sourceRef')
        if not isinstance(source,dict) or source.get('owner') not in {'media-binding','reviewed-av-candidate','final-film-candidate','av-derivative','asset-reference-production'}:return
        if source.get('owner')=='asset-reference-production' and body.get('accepted'):
            # The specialized register capability must persist the exact design
            # and identity before its Asset event adopts the candidate image.
            # Promoting the file index here prevents that same registration.
            return
        candidate,_=ledger_body(store,source)
        media=candidate.get('media') or candidate.get('finalMedia') or candidate.get('delivery')
        if not isinstance(media,dict):return
        file=await ensure_media(store,media['mediaId'],identity,order)
        for table in ('drama_shot','drama_asset'):
            for r in await store.client.query(table,{'media_id':file['id']},1):
                keys={'id':r['id'],**({'take_no':r['take_no']} if table=='drama_shot' else {})}
                await store.client.rows([store.row(table,identity,order,**keys,state='ADOPTED' if body.get('accepted') else 'DISCARDED',adoption_ref=canonical_json(event['ref']))])
        if body.get('accepted'):await superseded_by_revision(store,candidate,identity,order+1)
    elif kind=='asset-reference-production':
        # Implemented separately because the still owner retains its real request,
        # input locks, media recovery, review and adoption in one immutable record.
        from drama_plugin.film_storage.reference import project_reference
        await project_reference(store,body,identity,order)
    else:raise ValueError('Unsupported Film source event')
