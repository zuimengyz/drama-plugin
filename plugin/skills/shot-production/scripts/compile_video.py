#!/usr/bin/env python3
"""Compile an inspected video request OFFLINE; never upload, reserve or submit."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'src'))
from drama_plugin.visual.video_selection import Requirements,Candidate,ProductionRoute,seal_decision,qualify,choose
from drama_plugin.config import load_config, VideoRoutePolicy
from drama_plugin.hosts.comfy_video import compile_request,verify_execution

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--plugin-config',type=Path)
 a=p.parse_args();data=json.loads(a.input.read_text());r=Requirements.model_validate(data['requirements'])
 config=load_config(a.plugin_config)
 task=VideoRoutePolicy.model_validate(data['task_route_policy']) if data.get('task_route_policy') is not None else None
 candidates=[Candidate.model_validate(c) for c in data.get('candidates',[data.get('candidate')])]
 choice=choose(r,candidates,policy=config.video_route_policy,task_policy=task,dry_run=True,trial=data.get('allow_limited_trial',True))
 a.output.mkdir(parents=True,exist_ok=True)
 (a.output/'route-policy-resolution.json').write_text(json.dumps(choice,ensure_ascii=False,indent=2))
 if not choice['selected']:raise ValueError('NO_EXECUTABLE_CANDIDATE')
 c=next(c for c in candidates if c.candidate_id==choice['selected'])
 host=data['host_adapters'][c.candidate_id] if 'host_adapters' in data else data['host_adapter']
 graph=json.loads(Path(host['graph_path']).read_text());schema=json.loads(Path(host['schema_path']).read_text())
 request=compile_request(r,c,graph,schema,host['bindings'],r.frozen_creative['motion_prompt'])
 route=ProductionRoute.model_validate(data['production_route']) if data.get('production_route') else None
 sealed=seal_decision(r,c,request,stage_id=data['stage_id'],rationale=data['rationale'],comparisons=data.get('comparisons',[]),fallback=data['fallback'],host_adapter=host,dry_run=True,production_route=route,policy_resolution=choice['route_policy_resolution'])
 verify_execution(sealed,allow_dry_run=True)
 a.output.mkdir(parents=True,exist_ok=True)
 for name,value in [('sealed-request',sealed),('request',request),('qualification',qualify(r,c)),('provider-semantic-projection',sealed.get('execution_contract',{}).get('semantic_projection',{}))]:
  (a.output/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2))
 print(json.dumps({'state':'SEALED_DRY_RUN','submissionAllowed':False,'paidGenerationCalls':0,'requestFingerprint':sealed['request_fingerprint']}))
if __name__=='__main__':main()
