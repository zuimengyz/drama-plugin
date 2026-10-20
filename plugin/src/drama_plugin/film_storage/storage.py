from __future__ import annotations
import asyncio,json,os,sqlite3
from pathlib import Path
from typing import Any,TYPE_CHECKING
from drama_plugin.contracts.base import dump_contract,canonical_json,sha256_canonical
from drama_plugin.contracts.creation import Work
from drama_plugin.creative_engine.contracts import Kind,VersionRef
from drama_plugin.film_storage.client import FilmClient,FilmStorageUnavailable
from drama_plugin.film_storage.outbox import FilmOutbox
if TYPE_CHECKING:
    from drama_plugin.plugin import DramaPlugin

class FilmStorage:
    """Mirror actual owner events; delayed storage never dispatches paid work."""
    def __init__(self,plugin:DramaPlugin,client:FilmClient,root:Path):
        self.plugin,self.client,self.root=plugin,client,root
        self.outbox=FilmOutbox(root/'.film-storage-outbox');self.worker:asyncio.Task[None]|None=None
        self.lock=asyncio.Lock();self.last_error: str|None=None
    def resolve(self,ref:VersionRef)->Any:
        try:return self.plugin.creative_versions.resolve(ref)
        except (KeyError,ValueError,OSError):
            from drama_plugin.creative_engine.store import CreativeVersionStore
            return CreativeVersionStore(self.root/'creative-authority').resolve(ref)
    @classmethod
    def configured(cls,plugin:DramaPlugin)->FilmStorage|None:
        if os.environ.get('DRAMA_PLUGIN_FILM_STORE_ENABLED','false')!='true':return None
        service=plugin.config.services.memory
        if not service.base_url or not service.api_token:return None
        source=os.environ.get('DRAMA_MCP_ARCHIVE_SOURCE_ROOT')
        root=Path(source) if source else plugin.creative_versions.root.parent
        return cls(plugin,FilmClient(service.base_url,service.api_token),root)
    def creative_event(self,ref:VersionRef)->None:
        value=self.resolve(ref)
        if value.kind==Kind.SOURCE or value.state=='ADOPTED' and value.kind in {Kind.WORK,Kind.SCRIPT,Kind.SCENE}:
            self.outbox.enqueue({'kind':'CREATIVE','ref':dump_contract(ref),'workId':value.scope.work_id})
    def ledger_event(self,kind:str,ref:Any,scope:Any,fingerprint:str)->None:
        if kind in {'execution-operation','provider-attempt','provider-receipt','final-prompt','media-binding',
                'formal-media-registration','reference-execution-binding','creative-media-review','user-decision','asset-reference-production','production-package'}:
            self.outbox.enqueue({'kind':'LEDGER','type':kind,'ref':dump_contract(ref),'workId':scope.work_id})
    def asset_event(self,asset:Any)->None:
        self.outbox.enqueue({'kind':'ASSET','assetId':asset.id,'workId':asset.work_id})
    def scene_asset_event(self,asset:Any,scene_id:str,source:Any)->None:
        self.outbox.enqueue({'kind':'SCENE_ASSET','assetId':asset.id,'sceneId':scene_id,'workId':asset.work_id,'sourceRef':dump_contract(source)})
    async def start(self)->None:
        if self.worker is None:self.worker=asyncio.create_task(self.synchronize())
    async def synchronize(self)->None:
        while True:
            await self.flush();await asyncio.sleep(5)
    async def flush(self)->dict[str,Any]:
        async with self.lock:
            count=0;errors=[]
            for identity,value in self.outbox.pending():
                try:
                    await self.project(value['event'],identity,value['sourceOrder'])
                    self.outbox.acknowledge(identity);count+=1
                except Exception as e:
                    # Keep the exact pointer. Storage recovery is not a new Run,
                    # another attempt or a replacement paid generation.
                    errors.append(type(e).__name__+": "+str(e)[:240])
            self.last_error=errors[0] if errors else None
            return {'acknowledged':count,'pending':len(self.outbox.pending()),'lastError':self.last_error,
                'doesNotAdvanceRuntime':True}
    @staticmethod
    def row(table:str,event:str,order:int,**fields:Any)->dict[str,Any]:
        return {'table':table,'fields':{**fields,'source_event':event,'source_revision':1,'source_order':order}}
    async def project(self,event:dict[str,Any],identity:str,order:int)->None:
        if event['kind']=='ASSET_REFERENCE_SELECTION':
            from drama_plugin.professional_design.reference_roles import project_selection
            from drama_plugin.contracts.source_pin import SourcePin
            await project_selection(self,SourcePin.model_validate(event['ref']),identity,order)
        elif event['kind']=='SCENE_ASSET':
            from drama_plugin.film_storage.projection import ensure_scene
            asset=await self.plugin.providers.asset.get_asset(event['assetId'])
            if asset.work_id!=event['workId'] or not self.plugin.asset_sequence._proof(asset):raise ValueError('SCENE_ASSET_NOT_ADOPTED')
            from drama_plugin.professional_design.reference_roles import reference_role
            purpose=('SUPPLEMENTAL_APPEARANCE' if reference_role(self.plugin.asset_sequence,asset)=='SUPPLEMENT'
                else 'CHARACTER_IDENTITY' if asset.asset_type=='CHARACTER' else 'SCENE_ASSET')
            await ensure_scene(self,event['workId'],event['sceneId'],identity,order)
            await self.client.rows([self.row('drama_scene_asset',identity,order,scene_id=event['sceneId'],asset_id=asset.id,
                purpose=purpose,source_ref=canonical_json(event['sourceRef']))])
        elif event['kind']=='CREATIVE':
            await self.persist_refs((VersionRef.model_validate(event['ref']),),event=identity,order=order)
        elif event['kind']=='NATIVE_SELECTED':
            await self.persist_refs(tuple(VersionRef.model_validate(r) for r in event['refs']),event=identity,order=order,
                include_reviewed=event.get('includeReviewed',False))
        else:
            from drama_plugin.film_storage.projection import project_event
            await project_event(self,event,identity,order)
    async def persist_refs(self,refs:tuple[VersionRef,...],*,event:str|None=None,order:int|None=None,include_reviewed:bool=False)->Work:
        versions=[self.resolve(r) for r in refs]
        work=versions[0].scope.work_id
        if any(v.scope.work_id!=work for v in versions):raise ValueError('FILM_STORAGE_CROSS_WORK')
        event=event or 'native-selected:'+sha256_canonical([dump_contract(r) for r in refs])
        if order is None:
            queued=self.outbox.enqueue({'kind':'NATIVE_SELECTED','workId':work,'rendererVersion':2,
                'includeReviewed':include_reviewed,'refs':[dump_contract(r) for r in refs]})
            packet=json.loads((self.outbox.path/(queued+'.json')).read_text());order=packet['sourceOrder']
            event=queued
        sources=[v for v in versions if v.kind==Kind.SOURCE]
        known=await self.client.query('drama_work',{'id':work},1)
        if not known:
            if not sources:raise FilmStorageUnavailable('A real designated task Source must be retained first')
            source=sources[0]
            await self.client.rows([self.row('drama_work',event,order,id=work,title=source.body.goal[:255],
                source_ref=canonical_json(dump_contract(source.ref())))])
        for v in versions:
            if (v.state!='ADOPTED' and not (include_reviewed and v.state=='REVIEWED')) or v.scope.shot_id is not None:continue
            if v.kind not in {Kind.SCRIPT,Kind.SCENE}:continue
            if v.kind==Kind.SCRIPT and v.scope.scene_id is not None:continue
            scene=v.scope.scene_id
            if v.kind==Kind.SCENE:
                if scene is None:continue
                text=v.body.scene_text
                scene_known=await self.client.query('drama_scene',{'id':scene},1)
                if not scene_known:
                    title=next((s.strip('# ').strip() for s in text.splitlines() if s.strip()),scene)[:255]
                    await self.client.rows([self.row('drama_scene',event,order,id=scene,work_id=work,title=title,
                        source_ref=canonical_json(dump_contract(v.ref())))])
                sections=[text]
                if v.body.dialogue and any(d.text not in text for d in v.body.dialogue):
                    sections+=['\n## 正式对白\n']+[f'**{d.speaker}**：{d.text}\n' for d in v.body.dialogue]
                markdown='\n'.join(sections)
            else:markdown=v.body.screenplay
            # Separate immutable file identity from the original creative version.
            # A corrected transcription retains the old file instead of replacing bytes.
            media='script-md:'+sha256_canonical([v.fingerprint,markdown])
            await self.client.document(work,'SCENE_SCREENPLAY' if scene else 'FILM_SCREENPLAY',media,
                markdown.encode(),event,order)
            await self.client.rows([self.row('drama_script',event,order,id=v.identity,version=v.version,
                work_id=work,scene_id=scene,script_type='SCENE' if scene else 'FILM',title='单场导演剧本' if scene else '总导演剧本',
                media_id=media,state='ADOPTED' if v.state=='ADOPTED' else 'CANDIDATE',
                adoption_ref=canonical_json(dump_contract(v.adoption_decision_ref)) if v.adoption_decision_ref else None,original_fingerprint=v.fingerprint)])
            # This pointer is the exact selected/adopted native original, not a
            # Service latest-version guess. Original adoption records stay intact.
            if v.state=='ADOPTED':
                await self.client.rows([self.row('drama_scene' if scene else 'drama_work',event+':selected',order+1,
                    id=scene or work,script_id=v.identity,script_version=v.version)])
            result=await self.client.request('script',params={'work_id':work,**({'scene_id':scene} if scene else {}),
                'script_id':v.identity,'version':v.version})
            if result['original_fingerprint']!=v.fingerprint or result['markdown']!=markdown:raise ValueError('FILM_SCREENPLAY_READBACK_CHANGED')
        result=await self.client.request('work',params={'work_id':work})
        return Work(id=result['id'],title=result['title'],content={'filmStorage':{'schemaVersion':2,'authority':'PLUGIN_NATIVE_ORIGINAL','storageRole':'TASK'}})
    async def aclose(self)->None:
        if self.worker:
            self.worker.cancel()
            try:await self.worker
            except asyncio.CancelledError:pass
        await self.client.aclose()

