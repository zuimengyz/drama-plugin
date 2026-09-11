"""OFFLINE synthetic Media receipts + captured official node/template schemas."""
import json
from pathlib import Path
from drama_plugin.contracts.base import dump_contract,sha256_canonical as fp
from drama_plugin.visual.video_selection import Requirements,Candidate
from drama_plugin.hosts.comfy_video import inspect_graph,bind_capability
from test_video_selection import fixture,evidence


def add_director_inputs(r,a,frozen,port='keyframes.image_0'):
    spec=frozen['spec'];inp=r.inputs[0].model_dump();inp.update(source_ref='offline:formal:M',mime_type='image/png',endpoint_state=spec['openingState'],endpoint_evidence='OFFLINE observed endpoint agrees',width=1600,height=900)
    formal={'id':inp['media_id'],'work_id':r.work_id,'source_ref':inp['source_ref'],'content_hash':inp['content_hash'],'mime_type':'image/png','media_type':'IMAGE'}
    a['bindings'][0].update(formal_media=formal,formal_media_fingerprint=fp(formal))
    ref=spec['referenceRequirements'][0]
    duty=dict(role=ref['role'],subject=ref['subject'],purpose=ref['purpose'],media_id=inp['media_id'],source_ref=inp['source_ref'],content_hash=inp['content_hash'],mime_type='image/png',provider_input_type='IMAGE',provider_slot=port,target_shot=r.shot_id,fulfills=['identity'],evidence='OFFLINE host observed')
    return Requirements.model_validate({**r.model_dump(),'inputs':[inp],'reference_duties':[duty]})


def seed_fixture(tmp_path,mode='r2v',resolution='720p',duration=8):
    from test_cinematic_direction import example
    from drama_plugin.visual.cinematic import freeze_direction,selection_handoff
    r,c,_,_,a=fixture(tmp_path)
    spec,context,visual=example()
    spec.source_sound_intent=__import__('drama_plugin.contracts.cinematic',fromlist=['SourceSoundIntent']).SourceSoundIntent(native_audio_policy='REQUIRED',canonical_dialogue_bindings=['L'])
    if mode=='t2v':spec.reference_requirements=();spec.execution_requirements.reference_roles=()
    frozen=freeze_direction(spec,context=context,visual_resolution=visual,host_review='OFFLINE')
    root=Path(__file__).parent/'fixtures/seedance'
    g=json.loads((root/(mode+'-graph.json')).read_text());s=json.loads((root/(mode+'-schema.json')).read_text());ins=inspect_graph(g,s)
    node=json.loads((root/'node-schemas.json').read_text())[ins['class_type']]
    params=next(n for n in s['nodes'] if n['class_type']==ins['class_type'])['inputs'].copy();params.pop('model.prompt');params.update({'model.duration':duration,'model.resolution':resolution})
    if 'model.ratio' in params:params['model.ratio']='16:9'
    r=Requirements.model_validate({**r.model_dump(),'frozen_creative':selection_handoff(frozen),'mode':ins['mode'],'controls':ins['controls']+['NATIVE_AUDIO'],'inputs':[] if mode=='t2v' else [{**r.inputs[0].model_dump(),'role':'REFERENCE' if mode=='r2v' else 'FIRST_FRAME'}]})
    if mode=='t2v':a['bindings']=[]
    else:
        r=add_director_inputs(r,a,frozen,ins['input_ports'][0])
        if mode=='flf2v':
            inp=r.inputs[0].model_dump();inp.update(media_id='END',role='LAST_FRAME',endpoint_state=spec.ending_state)
            b=a['bindings'][0].copy();b.update(media_id='END',upload_name='end.png',upload_receipt=str(tmp_path/'end-receipt.json'))
            Path(b['upload_receipt']).write_text(json.dumps({'name':'end.png','content_hash':inp['content_hash']}))
            b['formal_media']={**b['formal_media'],'id':'END'};b['formal_media_fingerprint']=fp(b['formal_media']);a['bindings'].append(b)
            r=Requirements.model_validate({**r.model_dump(),'inputs':[r.inputs[0].model_dump(),inp]})
    Path(a['graph_path']).write_text(json.dumps(g));Path(a['schema_path']).write_text(json.dumps(s))
    c=Candidate.model_validate({**c.model_dump(),'model':'Seedance 2.5','variant':'Seedance 2.5','candidate_id':'seedance-2.5-'+mode,'mode':ins['mode'],'template':s['id'],'graph_hash':fp(g),'adapter_fingerprint':fp(ins),'parameters':params,'capability':bind_capability(node,g,s,evidence()),'controls':r.controls,'combinations':[r.controls],'durations':list(range(4,31))})
    return r,c,g,s,a


def execution_contract(model_key='seedance-2.5', provider='comfy-cloud'):
    return dict(transport='MCP',backend=dict(provider=provider,backend_key='https://cloud.comfy.org/mcp' if provider=='comfy-cloud' else 'offline:local-mcp'),capability=dict(kind='video_generation',model_key=model_key),mcp=dict(capability_key='comfy.video_generation'))


def execution_plan(r,c,stage_id='OFFLINE'):
    from drama_plugin.visual.video_selection import ProductionRoute,model_key
    return ProductionRoute(route_id='OFFLINE-MCP',work_id=r.work_id,stage_id=stage_id,
        creative_fingerprint=r.source_fingerprint,video_targets=[r.target_id],candidate=c,
        execution=execution_contract(model_key(c)),requirements=dict(controls=r.controls,
        duration_seconds=r.duration_seconds,aspect_ratio=r.aspect_ratio,sound=r.sound,
        language=r.language,shot_type=r.shot_type,creative_schema='cinematic-shot-v1',
        cinematic_directions={r.target_id:r.frozen_creative['cinematic_direction']},shots={r.target_id:r.shot_id}),
        quality_thresholds={'action_narrative':'coherent'},stops=['OFFLINE'],fallback='stop',
        generations_per_video_request=1,generation_count_evidence=evidence(),video_request_credits=100)
