from __future__ import annotations
from typing import Any,cast
from collections.abc import Callable,Awaitable
from typing import get_type_hints
import inspect
from drama_plugin.tools.catalog import _domain_tool
from drama_plugin.film_storage.storage import FilmStorage

def register_film_tools(registry:Any,store:FilmStorage)->None:
    async def get_work(work_id:str)->dict[str,Any]:return cast(dict[str,Any],await store.client.request('work',params={'work_id':work_id}))
    async def get_script(work_id:str,scene_id:str|None=None,script_id:str|None=None,version:int|None=None)->dict[str,Any]:
        return cast(dict[str,Any],await store.client.request('script',params={k:v for k,v in {'work_id':work_id,'scene_id':scene_id,'script_id':script_id,'version':version}.items() if v is not None}))
    async def characters(work_id:str)->list[dict[str,Any]]:return await store.client.query('drama_character',{'work_id':work_id})
    async def character(character_id:str)->dict[str,Any]:
        rows=await store.client.query('drama_character',{'id':character_id},1)
        if len(rows)!=1:raise ValueError('CHARACTER_NOT_FOUND')
        return rows[0]
    async def asset(asset_id:str)->dict[str,Any]:
        rows=await store.client.query('drama_asset',{'id':asset_id},1)
        if len(rows)!=1:raise ValueError('ASSET_NOT_FOUND')
        return rows[0]
    async def assets(work_id:str,character_id:str|None=None,state:str|None='ADOPTED',limit:int=30)->list[dict[str,Any]]:
        return await store.client.query('drama_asset',{k:v for k,v in {'work_id':work_id,'character_id':character_id,'state':state}.items() if v is not None},limit)
    async def scene_assets(scene_id:str)->list[dict[str,Any]]:return await store.client.query('drama_scene_asset',{'scene_id':scene_id})
    async def takes(work_id:str,scene_id:str|None=None,state:str|None=None,limit:int=30)->list[dict[str,Any]]:
        return await store.client.query('drama_shot',{k:v for k,v in {'work_id':work_id,'scene_id':scene_id,'state':state}.items() if v is not None},limit)
    async def get_request(request_id:str)->dict[str,Any]:
        values=await store.client.query('drama_generation_request',{'id':request_id},1)
        if len(values)!=1:raise ValueError('REQUEST_NOT_FOUND')
        result=values[0];result['inputs']=sorted(await store.client.query('drama_request_input',{'request_id':request_id},100),key=lambda row:row['ordinal'])
        return result
    async def inputs(request_id:str)->list[dict[str,Any]]:return sorted(await store.client.query('drama_request_input',{'request_id':request_id},100),key=lambda row:row['ordinal'])
    async def scripts(work_id:str,scene_id:str|None=None,state:str|None=None,limit:int=30,cursor:str|None=None)->dict[str,Any]:
        return await store.client.query_page('drama_script',{k:v for k,v in {
            'work_id':work_id,'scene_id':scene_id,'state':state}.items() if v is not None},limit,cursor)
    async def restore(work_id:str,scene_id:str|None=None,page_size:int=30,cursors:dict[str,str]|None=None)->dict[str,Any]:
        import json
        return cast(dict[str,Any],await store.client.request('context',params={'work_id':work_id,
            'page_size':page_size,**({'scene_id':scene_id} if scene_id else {}),
            **({'cursors':json.dumps(cursors)} if cursors is not None else {})}))
    async def get_file(media_id:str)->dict[str,Any]:return cast(dict[str,Any],await store.client.request('file',params={'media_id':media_id}))
    async def flush()->dict[str,Any]:return await store.flush()
    declarations:list[tuple[str,Callable[...,Awaitable[Any]],dict[str,Any],Any]]=[('get_work',get_work,{'work_id':str},dict[str,Any]),
        ('get_script',get_script,{'work_id':str},dict[str,Any]),('scripts',scripts,{'work_id':str},dict[str,Any]),('characters',characters,{'work_id':str},list[dict[str,Any]]),
        ('get_character',character,{'character_id':str},dict[str,Any]),('get_asset',asset,{'asset_id':str},dict[str,Any]),
        ('assets',assets,{'work_id':str},list[dict[str,Any]]),('scene_assets',scene_assets,{'scene_id':str},list[dict[str,Any]]),
        ('takes',takes,{'work_id':str},list[dict[str,Any]]),('get_request',get_request,{'request_id':str},dict[str,Any]),
        ('request_inputs',inputs,{'request_id':str},list[dict[str,Any]]),('restore_context',restore,{'work_id':str},dict[str,Any]),
        ('get_file',get_file,{'media_id':str},dict[str,Any]),('flush_storage',flush,{},dict[str,Any])]
    for name,method,required,result in declarations:
        hints=get_type_hints(method)
        optional={key:hints[key] for key in inspect.signature(method).parameters if key not in required}
        registry.register(_domain_tool('film.'+name,'Read Film V2 files/relations or retry retained storage only. No creative adoption or production execution.',
            method,result,required=required,optional=optional))
