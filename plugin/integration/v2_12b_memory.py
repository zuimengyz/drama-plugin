#!/usr/bin/env python3
"""V2-12B real existing Tool -> HTTP Service audit/seed. No generation capabilities called."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shlex
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from drama_plugin import DramaPlugin
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.creative_asset import CinematicLanguageContent
from drama_plugin.creative_assets import remember,search_patterns,search_bgm


def write(out,name,v):
    (out/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')


async def snapshot(p):
    result={k:[] for k in ['work','script','episode','scene','shot','asset','media']}
    result['work']=[dump_contract(x) for x in await p.tools.invoke('work.list_works')]
    result['asset']=[dump_contract(x) for x in await p.tools.invoke('asset.list_assets')]
    media={}
    for w in result['work']:
        for m in await p.tools.invoke('media.list_media',work_id=w['id'],include_debug=True):media[m.id]=dump_contract(m)
        scripts=await p.tools.invoke('script.list_scripts',work_id=w['id'])
        result['script'] += [dump_contract(x) for x in scripts]
        for s in scripts:
            episodes=await p.tools.invoke('episode.list_episodes',script_id=s.id)
            result['episode'] += [dump_contract(x) for x in episodes]
            for e in episodes:
                scenes=await p.tools.invoke('scene.list_scenes',episode_id=e.id)
                result['scene'] += [dump_contract(x) for x in scenes]
                for sc in scenes:
                    shots=await p.tools.invoke('shot.list_shots',scene_id=sc.id)
                    result['shot'] += [dump_contract(x) for x in shots]
    # Follow every formal Media reference, including records beyond list limits.
    def refs(v):
        if isinstance(v,dict):
            for x in v.values():yield from refs(x)
        elif isinstance(v,list):
            for x in v:yield from refs(x)
        elif isinstance(v,str) and v.startswith('media_') and len(v)==38:yield v
    unreadable=[]
    for mid in set(refs(result))-set(media):
        try:media[mid]=dump_contract(await p.tools.invoke('media.get_media',media_id=mid))
        except Exception as e:unreadable.append({'mediaId':mid,'error':str(e)})
    # Explicitly search music purposes to avoid audio/debug list saturation.
    for purpose in ['BGM','MUSIC','BACKGROUND_MUSIC','SCORE']:
        for m in await p.tools.invoke('media.list_media',purpose=purpose,include_debug=True):media[m.id]=dump_contract(m)
    result['media']=list(media.values());result['unreadableRefs']=unreadable
    return result


async def main(a):
    for line in a.env.read_text().splitlines():
        line=line.strip().removeprefix('export ')
        if line and not line.startswith('#') and '=' in line:
            k,v=line.split('=',1)
            try:os.environ[k]=shlex.split(v)[0]
            except (ValueError,IndexError):pass
    os.environ['NO_PROXY']='localhost,127.0.0.1'
    # No speech/production provider is enabled by this memory audit.
    for k in list(os.environ):
        if 'FISH' in k or 'ROLE_DUBBING' in k:os.environ.pop(k)
    for d in ['MEMORY','ASSET','MEDIA','VOICE']:
        os.environ['DRAMA_PLUGIN_SERVICE_'+d+'_BASE_URL']='http://127.0.0.1:8080'
        os.environ['DRAMA_PLUGIN_SERVICE_'+d+'_API_TOKEN']=os.environ['DRAMA_TOOL_SECRET']
    p=DramaPlugin.load(ROOT,ROOT/'config/drama-service-http.example.yaml')
    a.output.mkdir(parents=True,exist_ok=True)
    try:
        if a.phase in ['discover','protect']:
            data=await snapshot(p)
            write(a.output,'formal-'+('snapshot-before' if a.phase=='discover' else 'snapshot-after')+'.json',data)
            print(json.dumps({k:len(v) for k,v in data.items()}))
        if a.phase=='media-probe':
            from drama_plugin.media_delivery import verify_media, MediaIdentity
            before=json.loads((a.output/'formal-snapshot-before.json').read_text())
            candidates=[x for x in before['media'] if x['mediaType']=='AUDIO' and x.get('contentHash') and x.get('fileSize')]
            record=min(candidates,key=lambda x:x['fileSize'])
            result={'mediaId':record['id'],'expectedHash':record['contentHash'],'purpose':'read-only existing Media regression'}
            try:
                m=await p.tools.invoke('media.get_media',media_id=record['id'])
                resolved=await p.tools.invoke('media.resolve_media',media_id=m.id)
                result['resolve']='VERIFIED'
                result['readback']=await verify_media(p.providers.media,MediaIdentity.from_media(m),a.output/'media-readback')
                result['status']='VERIFIED'
            except Exception as e:
                result['status']='BLOCKED';result['error']=str(e)
            write(a.output,'existing-media-readback.json',result)
            print(json.dumps(result,ensure_ascii=False))
        if a.phase=='persist':
            work=await p.tools.invoke('work.get_work',work_id=a.work_id)
            results=[]
            for raw in json.loads((ROOT/'examples/cinematic-language-seeds.json').read_text()):
                c=CinematicLanguageContent.model_validate(raw)
                try:
                    asset,state=await remember(p.tools,work.id,c)
                    # User explicitly requires save/get/search for each new seed; only
                    # freshly created task-owned Assets receive this same-state save.
                    if state=='CREATED':
                        await p.tools.invoke('asset.save_asset',asset_id=asset.id,name=asset.name,
                            description=asset.description,reference_media_ids=asset.reference_media_ids,content=asset.content)
                    got=await p.tools.invoke('asset.get_asset',asset_id=asset.id)
                    again,reused=await remember(p.tools,work.id,c)
                    assert again.id==got.id and reused=='REUSED' and got.content==dump_contract(c)
                    results.append({'key':c.semantic_key,'assetId':got.id,'status':state,
                        'contentFingerprint':sha256_canonical(got.content),'readback':'VERIFIED','rerun':'REUSED',
                        'save':'VERIFIED' if state=='CREATED' else 'NOT_NEEDED_EXISTING','asset':dump_contract(got)})
                except Exception as e:
                    results.append({'key':c.semantic_key,'status':'BLOCKED','error':str(e)})
                write(a.output,'seed-assets-persistence-result.json',results)
            write(a.output,'cinematic-language-search-result.json',{
                q:await search_patterns(p.tools,q) for q in ['restrained','reaction','dialogue','restrained-motivated-push-in']})
            write(a.output,'bgm-search-result.json',{'all':await search_bgm(p.tools,'SUBTLE'),
                'tragicDread':await search_bgm(p.tools,'SUBTLE',mood='tragic',narrative_function='dread'),
                'production':await search_bgm(p.tools,'ACTIVE',production_only=True),
                'NO_BGM':await search_bgm(p.tools,'NO_BGM')})
            print(json.dumps([{k:v for k,v in r.items() if k!='asset'} for r in results],ensure_ascii=False))
    finally:await p.aclose()


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--env',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--phase',choices=['discover','persist','protect','media-probe'],required=True)
    ap.add_argument('--work-id')
    asyncio.run(main(ap.parse_args()))
