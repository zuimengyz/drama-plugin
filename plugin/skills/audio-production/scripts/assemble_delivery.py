"""Explicit durable AV completion; never generates speech or adopts an output."""
import argparse,asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'src'))
from drama_plugin.hosts.mcp_media import McpMediaSession
from drama_plugin.media_delivery import MediaIdentity,assemble_av_delivery
from drama_plugin.contracts.audio import AvAssemblyManifest
from drama_plugin.contracts.media import MediaType
async def run(config,request):
    data=json.loads(Path(request).read_text())
    for key in ['source_identity','mix_identity']:
        data[key]['media_type']=MediaType(data[key]['media_type']);data[key]=MediaIdentity(**data[key])
    data['manifest']=AvAssemblyManifest.model_validate(data['manifest'])
    for key in ['output','cache']:data[key]=Path(data[key])
    async with McpMediaSession(Path(config)) as session:
        result=await assemble_av_delivery(session.media,session.memory,session.asset,**data)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mcp-config',required=True);parser.add_argument('--request',required=True);args=parser.parse_args()
    asyncio.run(run(args.mcp_config,args.request))
