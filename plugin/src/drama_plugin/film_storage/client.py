from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,cast
import httpx

class FilmStorageUnavailable(RuntimeError):pass

class FilmClient:
    """Storage/query HTTP only. Cannot call a provider, adopt, spend or advance Runtime."""
    def __init__(self,base_url:str,token:str,transport:httpx.AsyncBaseTransport|None=None):
        self.http=httpx.AsyncClient(base_url=base_url.rstrip('/'),headers={'Authorization':'Bearer '+token},
            timeout=180,trust_env=False,transport=transport)
    async def request(self,path:str,*,method:str='GET',params:dict[str,Any]|None=None,body:Any=None)->Any:
        if path not in {'work','script','query','query-page','context','file','status','sync','file-index','existing-file'}:
            raise ValueError('Film client is restricted to file/index storage')
        try:
            response=await self.http.request(method,'/api/tool/film/'+path,params=params,json=body)
            response.raise_for_status();return response.json()
        except httpx.HTTPStatusError as e:
            try:detail=e.response.json().get('message','Storage request rejected')
            except (ValueError,AttributeError):detail='Storage request rejected'
            raise FilmStorageUnavailable(str(detail)[:240]) from e
        except httpx.HTTPError as e:
            raise FilmStorageUnavailable('Film storage unavailable; recover the same source event') from e
    async def rows(self,rows:list[dict[str,Any]])->dict[str,int]:
        return cast(dict[str,int],await self.request('sync',method='POST',body={'rows':rows}))
    async def query(self,table:str,filters:dict[str,Any],limit:int=30)->list[dict[str,Any]]:
        return cast(list[dict[str,Any]],await self.request('query',method='POST',body={'table':table,'filters':filters,'limit':limit}))
    async def query_page(self,table:str,filters:dict[str,Any],limit:int=30,cursor:str|None=None)->dict[str,Any]:
        return cast(dict[str,Any],await self.request('query-page',method='POST',body={
            'table':table,'filters':filters,'limit':limit,'cursor':cursor}))
    async def prompt_id(self,work:str,text:str)->str:
        from drama_plugin.contracts.base import sha256_canonical
        existing=await self.query('drama_media',{'work_id':work,'media_type':'DOCUMENT','purpose':'GENERATION_PROMPT','content_hash':hashlib.sha256(text.encode()).hexdigest()},1)
        # Preserve existing IDs; equal wording in another Work must not alias a
        # file owned by this Work. No bytes are copied to resolve an identity.
        return str(existing[0]['id']) if existing else 'prompt-md:'+sha256_canonical([work,text])
    async def document(self,work:str,purpose:str,identity:str,raw:bytes,event:str,order:int)->dict[str,Any]:
        digest=hashlib.sha256(raw).hexdigest()
        metadata={'id':identity,'work_id':work,'source_ref':'film-document:'+identity,'media_type':'DOCUMENT',
            'purpose':purpose,'mime_type':'text/markdown','file_size':len(raw),'content_hash':digest,
            'source_event':event,'source_revision':1,'source_order':order}
        try:
            response=await self.http.post('/api/tool/film/files',files={'metadata':(None,json.dumps(metadata)),
                'file':(identity.replace(':','-')+'.md',raw,'text/markdown')})
            response.raise_for_status();result=response.json()
        except httpx.HTTPError as e:raise FilmStorageUnavailable('Recover the same document version') from e
        if result['id']!=identity or result['content_hash']!=digest or result['storage_state']!='READY':
            raise ValueError('FILM_FILE_READBACK_MISMATCH')
        response=await self.http.get('/api/tool/film/file-content',params={'media_id':identity})
        response.raise_for_status()
        if response.content!=raw:raise ValueError('FILM_DOCUMENT_BYTES_CHANGED')
        return cast(dict[str,Any],result)
    async def aclose(self)->None:await self.http.aclose()

