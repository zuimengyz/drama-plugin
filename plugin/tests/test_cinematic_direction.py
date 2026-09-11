from seedance_helpers import execution_contract,execution_plan
"""OFFLINE director IR and existing selection/Host paths; no media submission."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.cinematic import CinematicShotSpec
from drama_plugin.visual.cinematic import (resolve_visual_bible, narrative_source,
    freeze_direction, verify_frozen, review_direction, selection_handoff, validate_canon)
from drama_plugin.visual.video_selection import Requirements, Candidate, qualify, qualify_route, validate_requirements, seal_decision
from drama_plugin.hosts.comfy_video import compile_request
from test_video_selection import fixture as video_fixture
from test_production_route import route as route_fixture

ROOT = Path(__file__).resolve().parents[1]


def example():
    base = {'realism':'保留使用痕迹','palette':{'dominant':['土褐'],'accent':['暗红']},
        'lighting':{'philosophy':'窗侧光','fill':'墙面弱反射','faceShadowAllowed':True},
        'imageCharacter':{'saturation':'克制','contrast':'脸部可读','highlight':'保留纹理','blackLevel':'不抬灰'},
        'materials':{'skin':'有纹理','costume':'粗布','metal':'局部反光','environment':'木土结构'},
        'atmosphere':'无额外天气','cameraPhilosophy':'按行动观察','forbidden':['现代标识']}
    visual = resolve_visual_bible(base, {'episode':{},'scene':{'palette':{'accent':[]}},'shot':{}})
    context = {'work':{'id':'W','title':'OFFLINE','content':{}},
        'script':{'id':'S','work_id':'W','content':{}},'episode':{'id':'E','script_id':'S','content':{}},
        'scene':{'id':'SC','episode_id':'E','content':{'spokenContent':[{'id':'L','text':'Hold it.','speakerKey':'A','estimatedDurationMs':1500}]}},
        'shot':{'id':'SHOT','scene_id':'SC','content':{'plannedDurationMs':8000,'action':'A holds a wooden frame and asks B to help','spokenContentBindings':[{'spokenContentId':'L'}]}}}
    def beat(a,b,kind,entry,action,exit):
        return dict(start=a,end=b,kind=kind,startState=entry,actions=[{'actor':'A','behavior':action}],endState=exit)
    spec = CinematicShotSpec.model_validate({'workId':'W','sceneId':'SC','shotId':'SHOT','creativeRevision':'offline-r1',
        'sourceFingerprint':fp(narrative_source(context)),'visualBibleFingerprint':visual['fingerprint'],
        'narrativeIntent':'请同伴扶住木架','visualBible':visual['effective'],'durationSeconds':8,
        'openingState':'甲持木架','behaviorAnchor':None,'anchorOmissionReason':'开场已在扶架，不增加准备动作',
        'performance':{'objective':'让乙扶稳木架','interactionTarget':'B','emotionalArc':['观察','求助','等候'],
            'beats':[beat(0,1,'ACTION','甲持木架','手保持托力，转眼看乙','甲看乙'),
                     beat(1,3,'DIALOGUE','甲看乙','向乙开口，木架仍由手托住','甲说完'),
                     beat(3,8,'HOLD','甲说完','保持托力等乙回应，手不突然松开','木架仍稳')]},
        'dialogue':[{'spokenContentId':'L','speakerKey':'A','text':'Hold it.','start':1,'end':3,'target':'B','delivery':'近距离低声，重音在Hold','afterLine':'看乙的手'}],
        'cinematography':{'shotSize':'中景','composition':'两人和木架同框','placement':'侧面','height':'胸高','subjectOrientation':'相对','lensIntent':'正常透视','focusTarget':'手和脸','focusTransition':'维持','movementClass':'LOCKED','movement':'固定','amplitude':'无','openingComposition':'甲与架','endingComposition':'架仍稳'},
        'lighting':'侧光照出木纹','secondaryMotion':[{'element':'袖口','cause':'前臂托架','response':'微小折动','limit':'无风飘'}],
        'environmentInteraction':[],
        'stabilityContract':[{'dimension':'prop','allowed':'托架和小幅调整','forbidden':'木架消失','reason':'动作依赖该物'}],
        'referenceRequirements':[{'role':'CHARACTER','necessity':'REQUIRED','subject':'A','purpose':'面容身份'}],
        'executionRequirements':{'durationSeconds':8,'performance':{'micro_expression':'MEDIUM','temporal_adherence':'HIGH'},'motion':{'camera_complexity':'LOW'},'continuity':{'identity':'HIGH'},'referenceRoles':['CHARACTER'],'timingIntent':'动作、对白、等候'},
        'sourceSoundIntent':{'nativeAudioPolicy':'REQUIRED','canonicalDialogueBindings':['L']},
        'endingState':'木架仍稳'})
    return spec, context, visual


def frozen_example():
    spec, context, visual = example()
    return freeze_direction(spec, context=context, visual_resolution=visual, host_review='OFFLINE canon and physical causality reviewed')


def test_registry_adds_exactly_one_skill_and_no_new_domain_tools():
    from drama_plugin import DramaPlugin
    p=DramaPlugin.load(ROOT)
    expected={'asset-resolution','audio-production','cinematic-finishing','cinematic-screenplay-incubation',
        'dramatic-performance-direction','episode-development','historical-research','scene-development',
        'script-adaptation','shot-design','shot-production','video-model-selection','work-creation'}
    assert {s.code for s in p.skills.list()} == expected | {'cinematic-direction'}
    assert len(p.tools.list()) == 50


def test_inherited_override_effective_and_input_immutable():
    _,_,visual=example();base=visual['base'];before=deepcopy(base)
    resolved=resolve_visual_bible(base,{'episode':{'palette':{'dominant':['灰']}},
        'scene':{'lighting':{'fill':'火盆反射'}},'shot':{'palette':{'accent':[]}}})
    assert base==before and resolved['effective']['palette']=={'dominant':['灰'],'accent':[]}
    assert resolved['layers'][1]['inherited']['palette']['dominant']==['灰']
    assert resolved['layers'][1]['override']=={'lighting':{'fill':'火盆反射'}}
    assert resolved['effective']['lighting']['faceShadowAllowed'] is True
    for patch in [{'nonsense':1},{'lighting':{'fill':None}}]:
        with pytest.raises(ValueError):resolve_visual_bible(base,{'shot':patch})


@pytest.mark.parametrize('fault',['overflow','negative','reverse','gap','overlap','opening','ending','prop_jump','dialogue_overflow','reference_role','execution_duration'])
def test_contract_counterexamples(fault):
    spec,_,_=example();raw=dump_contract(spec);beats=raw['performance']['beats']
    if fault=='overflow':beats[-1]['end']=12
    elif fault=='negative':beats[0]['start']=-1
    elif fault=='reverse':beats[1]['start']=.5;beats[1]['end']=.8;beats[1]['overlapReason']='parallel'
    elif fault=='gap':beats[1]['start']=1.2
    elif fault=='overlap':beats[1]['start']=.8
    elif fault=='opening':beats[0]['startState']='人物不在现场'
    elif fault=='ending':beats[-1]['endState']='木架已消失'
    elif fault=='prop_jump':beats[1]['startState']='木架落地'
    elif fault=='dialogue_overflow':raw['dialogue'][0]['end']=9
    elif fault=='reference_role':raw['referenceRequirements'][0]['establishesOpeningState']=True
    elif fault=='execution_duration':raw['executionRequirements']['durationSeconds']=12
    with pytest.raises(ValidationError):CinematicShotSpec.model_validate(raw)


def test_anchor_optionality_simple_action_and_explained_overlap():
    spec,_,_=example();assert spec.behavior_anchor is None and review_direction(spec)['status']=='PASS'
    raw=dump_contract(spec);raw['performance']['beats'][1].update(start=.8,overlapReason='开口时手部托架仍继续')
    CinematicShotSpec.model_validate(raw)
    raw=dump_contract(spec);raw['dialogue']=[]
    raw['performance']['beats']=[dict(start=0,end=8,kind='CONTINUOUS',startState=raw['openingState'],endState=raw['endingState'],actions=[{'actor':'A','behavior':'保持托力并随木架微调'}])]
    assert len(CinematicShotSpec.model_validate(raw).performance.beats)==1


def test_abstract_intent_is_not_execution_review_and_small_revision():
    spec,context,visual=example();raw=dump_contract(spec)
    raw['performance']['beats'][0]['actions'][0]['behavior']='悲伤、电影感、epic'
    bad=CinematicShotSpec.model_validate(raw);review=review_direction(bad)
    assert review['status']=='FAIL' and review['findings'][0]['evidence'] and review['findings'][0]['revise']
    with pytest.raises(ValueError):freeze_direction(bad,context=context,visual_resolution=visual,host_review='not enough')
    raw['performance']['beats'][0]['actions'][0]['behavior']='手继续托架，目光先向乙移动再转头'
    fixed=CinematicShotSpec.model_validate(raw)
    assert freeze_direction(fixed,context=context,visual_resolution=visual,host_review='Only the vague gesture revised')['state']=='CINEMATIC_DIRECTION_FROZEN'
    assert fixed.source_fingerprint==spec.source_fingerprint


def test_camera_feedback_look_and_stability_findings_are_contextual():
    spec,_,_=example();raw=dump_contract(spec)
    raw['cinematography'].update(movementClass='DYNAMIC',movement='orbit')
    raw['secondaryMotion']=[{'element':'火焰','cause':'火盆','response':'升起','limit':'盆内'}]
    draft=CinematicShotSpec.model_validate(raw);review=review_direction(draft)
    assert review['status']=='PASS_WITH_NOTES'
    assert {x['field'] for x in review['findings']}=={'cinematography.movement','environmentInteraction'}
    raw['stabilityContract'][0]['allowed']=raw['stabilityContract'][0]['forbidden']
    assert review_direction(CinematicShotSpec.model_validate(raw))['status']=='FAIL'
    other=deepcopy(spec);other.visual_bible.palette.dominant=('亮紫',)
    assert any(x['field']=='visualBible.sequence' for x in review_direction(spec,neighbors=(other,))['findings'])


@pytest.mark.parametrize('fault',['source','dialogue','speaker','omit','bible','frozen','duration'])
def test_source_frozen_and_dialogue_authority(fault):
    spec,ctx,visual=example();raw=dump_contract(spec)
    if fault=='source':ctx['shot']['content']['action']='different canon'
    elif fault=='dialogue':raw['dialogue'][0]['text']='Let go.'
    elif fault=='speaker':raw['dialogue'][0]['speakerKey']='B'
    elif fault=='omit':raw['dialogue']=[]
    elif fault=='bible':raw['visualBible']['materials']['skin']='smooth'
    elif fault=='duration':ctx['shot']['content']['plannedDurationMs']=12000
    else:
        f=frozen_example();f['spec']['narrativeIntent']='changed'
        with pytest.raises(ValueError):verify_frozen(f)
        return
    with pytest.raises(ValueError):freeze_direction(CinematicShotSpec.model_validate(raw),context=ctx,visual_resolution=visual,host_review='OFFLINE')


def test_existing_dpd_lineage_is_consumed_without_a_second_performance_authority():
    from test_visual_performance import snapshot
    from drama_plugin.dpd import compose_dpd
    spec,ctx,visual=example();dpd=snapshot()
    dpd.scene.scene_id='SC';dpd.beat.scene_id='SC';dpd.line.scene_id='SC'
    dpd.line.spoken_content_id='L';dpd.line.speaker='A';dpd.beat.actor='A'
    dpd=compose_dpd(dpd.scene,dpd.beat,dpd.line)
    ctx['dpdSnapshot']=dump_contract(dpd)
    frozen=freeze_direction(spec,context=ctx,visual_resolution=visual,host_review='OFFLINE DPD projection review')
    assert frozen['upstreamPerformance']['fingerprint']==dpd.fingerprint
    assert verify_frozen(frozen)==spec
    ctx['dpdSnapshot']['fingerprint']='0'*64
    with pytest.raises(ValueError,match='STALE_UPSTREAM_DPD'):
        freeze_direction(spec,context=ctx,visual_resolution=visual,host_review='OFFLINE')


def test_existing_v206_qualification_and_host_compiler_receive_frozen_direction(tmp_path):
    r,c,g,s,a=video_fixture(tmp_path);f=frozen_example();material=selection_handoff(f)
    r=Requirements.model_validate({**r.model_dump(),'frozen_creative':material})
    from seedance_helpers import add_director_inputs
    r=add_director_inputs(r,a,f)
    result=qualify(r,c)
    assert result['eligible'] and result['qualification']=='LIMITED_TRIAL'
    assert result['cinematic_direction']['execution_requirements']['durationSeconds']==8
    assert result['cinematic_direction']['reference_requirements'][0]['role']=='CHARACTER'
    request=compile_request(r,c,g,s,a['bindings'],material['motion_prompt'])
    from drama_plugin.hosts.cinematic_projection import project
    from drama_plugin.hosts.comfy_video import inspect_graph
    assert request['input_overrides']['2']['prompt']==project(r,c,inspect_graph(g,s))['prompt']
    assert 'Hold it.' in request['input_overrides']['2']['prompt']
    d=seal_decision(r,c,request,stage_id='OFFLINE',rationale='OFFLINE',comparisons=[],fallback='requalify',host_adapter=a,production_route=execution_plan(r,c))
    assert d['requirements']['frozen_creative']['cinematic_direction']['fingerprint']==f['fingerprint']
    altered=deepcopy(material);altered['motion_prompt']='cinematic only'
    with pytest.raises(ValueError):validate_requirements(Requirements.model_validate({**r.model_dump(),'frozen_creative':altered}))
    bad=c.model_dump();bad['quality']={'status':'PASS','samples':1,'task_types':['PERSON_PROP'],
        'evidence':['OFFLINE scoped observation'],'dimensions':{'identity_props':'PASS','action_narrative':'PASS','sound_performance':'PASS','continuity':'PASS','performance.temporal_adherence':'FAIL'}}
    rejected=qualify(r,Candidate.model_validate(bad))
    assert not rejected['eligible'] and 'DIRECTOR_REQUIREMENT_FAILED:performance.temporal_adherence' in rejected['exclusions']


def test_route_before_inputs_and_real_frame_gate_preserve_direction(tmp_path):
    route=route_fixture(tmp_path);raw=route.model_dump();f=frozen_example()
    raw['execution']=execution_contract('flux-3')
    raw['requirements'].update(creative_schema='cinematic-shot-v1',cinematic_directions={'S1':f},shots={'S1':'SHOT'})
    from drama_plugin.visual.video_selection import ProductionRoute
    route=ProductionRoute.model_validate(raw)
    result=qualify_route(route)
    assert result['eligible'] and result['cinematic_directions']['S1']['fingerprint']==f['fingerprint']
    r,c,g,s,a=video_fixture(tmp_path);r=Requirements.model_validate({**r.model_dump(),'frozen_creative':selection_handoff(f)})
    from seedance_helpers import add_director_inputs
    r=add_director_inputs(r,a,f)
    request=compile_request(r,c,g,s,a['bindings'],r.frozen_creative['motion_prompt'])
    decision=seal_decision(r,c,request,stage_id='v206',rationale='OFFLINE',comparisons=[],fallback='requalify',host_adapter=a,production_route=route)
    from drama_plugin.visual.production import _route_frame_gate
    state={'production_route':route.model_dump(mode='json'),'attempts':[]}
    _route_frame_gate(state,decision)
    decision['requirements']['frozen_creative'].pop('cinematic_direction')
    with pytest.raises(ValueError,match='DIRECTOR_CHANGE'):_route_frame_gate(state,decision)
    raw['requirements']['cinematic_directions']={}
    with pytest.raises(ValueError,match='COMPLETE_FROZEN'):qualify_route(ProductionRoute.model_validate(raw))


def test_existing_replan_accepts_director_revision_without_resetting_history(tmp_path,monkeypatch):
    from drama_plugin.visual import production as p
    from drama_plugin.hosts.comfy_video import verify_execution
    monkeypatch.setattr(p,'video_verifier',verify_execution)
    r,c,g,s,adapter=video_fixture(tmp_path);spec,context,visual=example()
    def decision(spec):
        frozen=freeze_direction(spec,context=context,visual_resolution=visual,host_review='OFFLINE local camera revision')
        req=Requirements.model_validate({**r.model_dump(),'frozen_creative':selection_handoff(frozen)})
        from seedance_helpers import add_director_inputs
        req=add_director_inputs(req,adapter,frozen)
        request=compile_request(req,c,g,s,adapter['bindings'],req.frozen_creative['motion_prompt'])
        return seal_decision(req,c,request,stage_id='v206',rationale='OFFLINE',comparisons=[],fallback='requalify',host_adapter=adapter,production_route=execution_plan(req,c,'v206'))
    old=decision(spec);state=p.new_stage(stage_id='v206',authorization_ref='OFFLINE',budget_credits=300,frames=[old],protected_targets=['C07','C12'])
    state['attempts']=[{'shot_id':'S1','status':'FAILED','credits':100,'reserved_credits':100}]
    history=deepcopy(state['attempts']);changed=deepcopy(spec)
    changed.cinematography.height='略低于胸高，仍是同一侧面'
    new=decision(changed);p.replan(state,frame=new,reason='camera height clarifies the hands',incremental_credits=100)
    assert state['attempts']==history and state['frames']['S1']==new
    assert state['remediations'][-1]['previous_frame']==old
    # A director replan is not authority to change the canonical narrative source.
    context['shot']['content']['action']='Different event';changed.source_fingerprint=fp(narrative_source(context))
    with pytest.raises(ValueError,match='CREATIVE_REQUIREMENTS_CHANGED'):
        p.replan(state,frame=decision(changed),reason='unsupported canon change')


@pytest.mark.asyncio
async def test_actual_host_refreshes_canon_before_route_and_submission_boundary(tmp_path):
    from drama_plugin.contracts.creation import Work,Script,Episode,Scene,Shot
    from drama_plugin.hosts.route_production import save_route,operate
    spec,context,visual=example()
    context['script']['title']='S';context['episode'].update(title='E',episode_no=1)
    context['scene'].update(title='SC',order=1);context['shot'].update(shot_no='S1')
    models={'work':Work,'script':Script,'episode':Episode,'scene':Scene,'shot':Shot}
    entities={k:models[k].model_validate(v) for k,v in context.items()}
    context={k:v.model_dump(mode='json') for k,v in entities.items()}
    spec.source_fingerprint=fp(narrative_source(context))
    frozen=freeze_direction(spec,context=context,visual_resolution=visual,host_review='OFFLINE formal context')
    class Memory:
        writes=0
        def __getattr__(self,name):
            assert name.startswith('get_')
            async def get(identity):
                entity=entities[name[4:]];assert entity.id==identity;return deepcopy(entity)
            return get
        async def save_work(self,wid,title,content,description):
            self.writes+=1;entities['work'].content=deepcopy(content)
    memory=Memory();raw=route_fixture(tmp_path).model_dump(mode='json')
    raw['execution']=execution_contract('flux-3')
    raw['requirements'].update(creative_schema='cinematic-shot-v1',cinematic_directions={'S1':frozen},shots={'S1':'SHOT'})
    await save_route(memory,'W',raw)
    await operate(memory,'W','init-stage',{'authorization_ref':'OFFLINE','budget_credits':300})
    assert memory.writes==2
    entities['shot'].content['action']='upstream changed'
    with pytest.raises(ValueError,match='STALE_CINEMATIC_NARRATIVE_SOURCE'):
        await operate(memory,'W','reserve',{'shot_id':'S1'})
    assert memory.writes==2 and entities['work'].content['productionStage']['attempts']==[]


def assert_neutral(text):
    assert not any(x in text.lower() for x in ['seedance','minimax','kling','flux','comfy','node_id','if model ==','if provider =='])


def test_core_provider_neutrality_and_architecture_counterexample():
    for p in [ROOT/'skills/cinematic-direction/SKILL.md',ROOT/'skills/cinematic-direction/skill.yaml',
              ROOT/'src/drama_plugin/contracts/cinematic.py',ROOT/'src/drama_plugin/visual/cinematic.py']:
        assert_neutral(p.read_text())
    with pytest.raises(AssertionError):assert_neutral('if model == "seedance": special_parameter = 3')


def test_real_offline_entry_writes_handoff_without_network(tmp_path):
    spec,context,visual=example()
    for name,value in [('draft',dump_contract(spec)),('context',context),('visual',visual)]:
        (tmp_path/f'{name}.json').write_text(json.dumps(value,ensure_ascii=False))
    (tmp_path/'review.txt').write_text('OFFLINE Host reviewed source/physical causality')
    # A subprocess guard makes any accidental network setup in this entry fail.
    (tmp_path/'sitecustomize.py').write_text('import socket\ndef forbidden(*a,**k): raise RuntimeError("OFFLINE_NETWORK_FORBIDDEN")\nsocket.socket.connect=forbidden\nsocket.socket.connect_ex=forbidden\n')
    import os
    command=[sys.executable,str(ROOT/'skills/cinematic-direction/scripts/direct_shot.py'),
        '--context',str(tmp_path/'context.json'),'--draft',str(tmp_path/'draft.json'),
        '--visual-resolution',str(tmp_path/'visual.json'),'--host-review',str(tmp_path/'review.txt'),'--output',str(tmp_path/'result')]
    result=subprocess.run(command,check=True,capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(tmp_path)})
    receipt=json.loads(result.stdout)
    assert receipt['paidGenerationCalls']==0 and receipt['submissionAllowed'] is False
    handoff=json.loads((tmp_path/'result/selection-handoff.json').read_text())
    assert verify_frozen(handoff['cinematic_direction']).source_fingerprint==spec.source_fingerprint
    assert handoff['execution_requirements']['durationSeconds']==8
    assert handoff['motion_prompt'] and receipt['state']=='CINEMATIC_DIRECTION_FROZEN'
