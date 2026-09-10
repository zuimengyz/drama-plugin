#!/usr/bin/env python3
"""Actual local finishing entry; existing public service adapters for retention."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from drama_plugin.audio.finishing import render, retain

parser=argparse.ArgumentParser(description=__doc__)
sub=parser.add_subparsers(dest='command',required=True)
p=sub.add_parser('render');p.add_argument('--recipe',type=Path,required=True);p.add_argument('--paths',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
p=sub.add_parser('retain');p.add_argument('--recipe',type=Path,required=True);p.add_argument('--render',type=Path,required=True);p.add_argument('--staging',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--config',type=Path,default=ROOT/'.mcp.json')
p=sub.add_parser('recover');p.add_argument('--work',required=True);p.add_argument('--revision',required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--config',type=Path,default=ROOT/'.mcp.json')

async def main(a):
    if a.command=='render':
        result=render(json.loads(a.recipe.read_text()),json.loads(a.paths.read_text()),a.output)
        print(json.dumps(result,ensure_ascii=False,indent=2));return
    from drama_plugin.hosts.mcp_media import McpMediaSession
    from drama_plugin.media_delivery import verify_media,MediaIdentity
    async with McpMediaSession(a.config) as session:
        if a.command=='retain':
            result=await retain(session,json.loads(a.recipe.read_text()),json.loads(a.render.read_text()),staging=a.staging,cache=a.cache)
        else:
            work=await session.memory.get_work(a.work)
            record=work.content['finishingRevisions'][a.revision]
            recipe=record['recipe'];ids={recipe['sourceMediaId'],*recipe['sources']}
            if record.get('delivery'):ids.add(record['delivery']['mediaId'])
            paths={}
            for media_id in sorted(ids):
                m=await session.media.get_media(media_id)
                if m.work_id!=work.id:raise ValueError('Recovery ownership mismatch')
                expected=(recipe['sourceHash'] if media_id==recipe['sourceMediaId'] else
                          recipe['sources'][media_id] if media_id in recipe['sources'] else record['delivery']['contentHash'])
                if m.content_hash!=expected:raise ValueError('Recovery hash mismatch')
                r=await verify_media(session.media,MediaIdentity.from_media(m),a.cache)
                paths[media_id]=r['cachePath']
            a.cache.mkdir(parents=True,exist_ok=True)
            (a.cache/'recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2))
            (a.cache/'paths.json').write_text(json.dumps(paths,ensure_ascii=False,indent=2))
            result={'record':record,'paths':paths,'generationCalls':0}
        print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':asyncio.run(main(parser.parse_args()))
