"""Offline route sidecars: resolve, bind a design, or inspect an Asset snapshot."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'src'))
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.asset import Asset
from drama_plugin.contracts.visual_route import RouteContext,RouteCastingContext
from drama_plugin.visual_route import resolved_context,bind_route_artifact,discover_route_assets
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('mode',choices=['schema','resolve','bind','discover'])
p.add_argument('--context',type=Path);p.add_argument('--input',type=Path);p.add_argument('--output',type=Path,required=True)
p.add_argument('--responsibility',choices=['CASTING','ART_DIRECTION','CAMERA','PERFORMANCE','AUTHORIAL_PRESENTATION'])
a=p.parse_args()
if a.mode=='schema':result={'routeContext':RouteContext.model_json_schema(by_alias=True),'routeCastingContext':RouteCastingContext.model_json_schema(by_alias=True)}
else:
 if not a.context:p.error('--context required')
 context=RouteContext.model_validate_json(a.context.read_text());route=resolved_context(context)
 if a.mode=='resolve':result=dump_contract(route)
 else:
  if not a.input:p.error('--input required')
  raw=json.loads(a.input.read_text())
  if a.mode=='bind':
   if not a.responsibility:p.error('--responsibility required')
   result=bind_route_artifact(raw,context,responsibility=a.responsibility)
  else:result=discover_route_assets([Asset.model_validate(x) for x in raw],work_id=route.work_id,visual_route=route.visual_route)
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(a.output),'paidGenerationCalls':0,'formalWrites':0}))
