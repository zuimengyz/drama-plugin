"""V2-12 offline contracts; no credentials, upload, submission, or model calls."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import subprocess,sys
import pytest
from drama_plugin.contracts.base import dump_contract,sha256_canonical as fp
from drama_plugin.contracts.cinematic import CinematicShotSpec
from drama_plugin.visual.cinematic import freeze_direction,selection_handoff,validate_canon
from drama_plugin.visual.video_selection import Requirements,Candidate,qualify,seal_decision,verify_decision
from drama_plugin.hosts.comfy_video import compile_request,inspect_graph,verify_execution,bind_capability
from drama_plugin.hosts.cinematic_projection import project,validate_projection
from seedance_helpers import seed_fixture


def compile_all(r,c,g,s,a):return compile_request(r,c,g,s,a['bindings'],r.frozen_creative['motion_prompt'])

def seal(r,c,g,s,a,**kw):
 return seal_decision(r,c,compile_all(r,c,g,s,a),stage_id='OFFLINE',rationale='OFFLINE',comparisons=[],fallback='requalify',host_adapter=a,**kw)

@pytest.mark.parametrize('mode',['t2v','r2v','flf2v'])
def test_official_modes_and_limited_trial(tmp_path,mode):
 r,c,g,s,a=seed_fixture(tmp_path,mode);req=compile_all(r,c,g,s,a);ins=inspect_graph(g,s)
 assert c.capability['node_schema']['name']==ins['class_type']
 assert req['input_overrides'][ins['model_node']]['model.duration']==8
 assert len(a['bindings'])=={'t2v':0,'r2v':1,'flf2v':2}[mode]
 assert qualify(r,c)['eligible'] and qualify(r,c)['qualification']=='LIMITED_TRIAL'
 assert not qualify(r,c,trial=False)['eligible']
 verify_execution(seal(r,c,g,s,a))

@pytest.mark.parametrize('field,value',[('model.duration',3),('model.duration',31),('model.resolution','999p'),('model.output_format','mov'),('model.task_type','edit'),('model.task_type','auto'),('seed',-1)])
def test_current_ranges_and_deferred_modes(tmp_path,field,value):
 r,c,g,s,a=seed_fixture(tmp_path);c.parameters[field]=value
 if field=='model.duration':r=r.model_copy(update={'duration_seconds':value})  # Canon/requirements must also reject duration drift.
 with pytest.raises(ValueError):compile_all(r,c,g,s,a)

@pytest.mark.parametrize('duration',[4,30])
def test_schema_boundary_duration(tmp_path,duration):
 r,c,g,s,a=seed_fixture(tmp_path,duration=duration)
 # Legacy is kept to isolate current L1 range validation from the 8s director.
 r=Requirements.model_validate({**r.model_dump(),'duration_seconds':duration,'frozen_creative':{'motion_prompt':'continuous action'},'reference_duties':[]})
 assert compile_all(r,c,g,s,a)['input_overrides'][inspect_graph(g,s)['model_node']]['model.duration']==duration

@pytest.mark.parametrize('mutation',['missing','wrong_subject','wrong_media','wrong_hash','wrong_slot','fake_motion','missing_formal','source_ref','endpoint'])
def test_reference_failures_before_seal(tmp_path,mutation):
 r,c,g,s,a=seed_fixture(tmp_path,'flf2v' if mutation=='endpoint' else 'r2v')
 data=r.model_dump()
 if mutation=='missing':data['reference_duties']=[]
 elif mutation=='wrong_subject':data['reference_duties'][0]['subject']='Other'
 elif mutation=='wrong_media':data['reference_duties'][0]['media_id']='unknown'
 elif mutation=='wrong_hash':data['reference_duties'][0]['content_hash']='0'*64
 elif mutation=='wrong_slot':data['reference_duties'][0]['provider_slot']='model.reference_images.image_2'
 elif mutation=='missing_formal':a['bindings'][0]['formal_media']={}
 elif mutation=='source_ref':a['bindings'][0]['formal_media']['source_ref']='different'
 elif mutation=='endpoint':data['inputs'][1]['endpoint_state']='sitting elsewhere'
 elif mutation=='fake_motion':
  frozen=data['frozen_creative']['cinematic_direction'];raw=frozen['spec'];raw['referenceRequirements'][0]['role']='PERFORMANCE';raw['executionRequirements']['referenceRoles']=['PERFORMANCE'];frozen['fingerprint']=fp({k:v for k,v in frozen.items() if k!='fingerprint'});data['frozen_creative']=selection_handoff(frozen);data['reference_duties'][0]['role']='PERFORMANCE'
 with pytest.raises((ValueError,KeyError)):seal(Requirements.model_validate(data),c,g,s,a)


def test_same_director_two_resolutions_and_all_critical_fields(tmp_path):
 r,c,g,s,a=seed_fixture(tmp_path);requests=[]
 for res in ['480p','720p']:
  c.parameters['model.resolution']=res;requests.append(seal(r,c,g,s,a))
 assert requests[0]['execution_contract']['cinematic_direction_fingerprint']==requests[1]['execution_contract']['cinematic_direction_fingerprint']
 assert requests[0]['request_fingerprint']!=requests[1]['request_fingerprint']
 projection=requests[0]['execution_contract']['semantic_projection']
 for item in projection['manifest']:
  assert not item['required_for_execution'] or item['destination'] in ['PROMPT','PARAMETER','REFERENCE','UPSTREAM_LOCK']
 broken=deepcopy(projection);next(x for x in broken['manifest'] if x['required_for_execution'])['destination']='UNSUPPORTED'
 with pytest.raises(ValueError,match='CRITICAL'):validate_projection(broken)


def test_long_prompt_no_truncation_and_verified_limit(tmp_path):
 r,c,g,s,a=seed_fixture(tmp_path);f=r.frozen_creative['cinematic_direction'];f['spec']['performance']['beats'][0]['actions'][0]['prop']='木架接触点保持在双手之间。'*220+'END_SENTINEL'
 f['fingerprint']=fp({k:v for k,v in f.items() if k!='fingerprint'});r=r.model_copy(update={'frozen_creative':selection_handoff(f)})
 req=compile_all(r,c,g,s,a);text=req['input_overrides'][inspect_graph(g,s)['model_node']]['model.prompt']
 assert len(text)>2000 and 'END_SENTINEL' in text
 cap=deepcopy(c.capability);next(x for x in cap['node_schema']['input_details'] if x['name']=='model.prompt')['max_length']=100
 cap['fingerprint']=fp({k:v for k,v in cap.items() if k!='fingerprint'});c=c.model_copy(update={'capability':cap})
 with pytest.raises(ValueError,match='VERIFIED_PROVIDER_PROMPT_LIMIT'):compile_all(r,c,g,s,a)


def test_source_sound_optional_enable_disable_and_conflict(tmp_path):
 r,c,g,s,a=seed_fixture(tmp_path,'t2v');f=r.frozen_creative['cinematic_direction']
 f['spec']['dialogue']=[];f['spec']['sourceSoundIntent']={'nativeAudioPolicy':'DISABLED','canonicalDialogueBindings':[],'diegetic':[],'ambience':[],'intentionalSilence':['完整静默'],'generatedMusic':'FORBIDDEN','continuity':[]}
 f['fingerprint']=fp({k:v for k,v in f.items() if k!='fingerprint'});r=r.model_copy(update={'frozen_creative':selection_handoff(f)});r=r.model_copy(update={'sound':'SILENT','controls':('TEXT',)});c.parameters['model.generate_audio']=False
 assert compile_all(r,c,g,s,a)['input_overrides']['9']['model.generate_audio'] is False
 c.parameters['model.generate_audio']=True
 with pytest.raises(ValueError,match='SOURCE_SOUND_PARAMETER'):compile_all(r,c,g,s,a)


def test_single_authority_and_legacy_compatibility(tmp_path):
 r,c,g,s,a=seed_fixture(tmp_path)
 r.frozen_creative['visualPerformanceBrief']={'motion':'conflicting'}
 with pytest.raises(ValueError,match='DOUBLE_VISUAL'):compile_all(r,c,g,s,a)
 from test_visual_performance import snapshot
 from drama_plugin.visual.performance import project_visual_performance,compile_video_motion_prompt
 # Use the established legacy projection tests' argument shape.
 import inspect
 assert 'creative_schema' in inspect.signature(compile_video_motion_prompt).parameters
 with pytest.raises(ValueError):
  compile_video_motion_prompt(brief=None,shot_action='x',camera_design='fixed',creative_schema='cinematic-shot-v1')

@pytest.mark.parametrize('mutation',['expired','schema','prompt','reference_package','projection','audio'])
def test_sealed_drift(tmp_path,mutation):
 r,c,g,s,a=seed_fixture(tmp_path);d=seal(r,c,g,s,a)
 if mutation=='expired':
  d['candidate']['capability']['evidence']['expires_at']=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
 elif mutation=='schema':
  s['nodes'][0]['inputs']['image']='changed';Path(a['schema_path']).write_text(json.dumps(s))
 elif mutation=='prompt':d['request']['input_overrides']['24']['model.prompt']='different'
 elif mutation=='reference_package':d['execution_contract']['reference_package_fingerprint']='0'*64
 elif mutation=='projection':d['execution_contract']['semantic_projection']['prompt']='shorter'
 elif mutation=='audio':d['candidate']['parameters']['model.generate_audio']=False
 with pytest.raises(ValueError):verify_execution(d)


def test_unknown_price_seals_only_offline_and_actual_cli(tmp_path):
 r,c,g,s,a=seed_fixture(tmp_path);c=c.model_copy(update={'cost':c.cost.model_copy(update={'components':{'video':None},'uncertainty':('UNKNOWN',)})})
 assert qualify(r,c)['incremental_credits'] is None and not qualify(r,c)['eligible']
 d=seal(r,c,g,s,a,dry_run=True);verify_execution(d,allow_dry_run=True)
 with pytest.raises(ValueError,match='DRY_RUN'):verify_execution(d)
 with pytest.raises(ValueError,match='INELIGIBLE'):seal(r,c,g,s,a)
 data={'requirements':r.model_dump(mode='json'),'candidate':c.model_dump(mode='json'),'host_adapter':a,'stage_id':'OFFLINE','rationale':'OFFLINE','fallback':'requalify'}
 path=tmp_path/'input.json';path.write_text(json.dumps(data));entry=Path(__file__).resolve().parents[1]/'skills/shot-production/scripts/compile_video.py'
 result=subprocess.run([sys.executable,str(entry),'--input',str(path),'--output',str(tmp_path/'out')],capture_output=True,text=True)
 assert result.returncode==0,result.stderr
 assert json.loads(result.stdout)['submissionAllowed'] is False
 assert json.loads((tmp_path/'out/request.json').read_text())==d['request']


def shared_fixture(role="REACTION"):
 from test_cinematic_direction import example
 from drama_plugin.visual.cinematic import narrative_source
 from drama_plugin.visual.dialogue_coverage import shot_projection
 spec,ctx,visual=example();line=ctx['scene']['content']['spokenContent'][0];line.update(text='Hold it. Keep it level.',estimatedDurationMs=10000)
 first=ctx['shot'];first['content']['spokenContentBindings']=[{'spokenContentId':'L','coverageIntent':'ON_SCREEN_SPEAKER'}]
 second=deepcopy(first);second['id']='REACTION';second['content']['spokenContentBindings'][0]['coverageIntent']=role
 group=[first,second];artifact={'shots':[shot_projection(s) for s in group],'canonicalFingerprint':fp([line]),'turns':[{'spokenContentId':'L','startMs':1000,'endMs':11000,'slices':[{'shotId':'SHOT','textRange':[0,9]},{'shotId':'REACTION','textRange':[9,len(line['text'])]}]}]}
 ctx['sceneShots']=group;ctx['dialogueCoverage']=artifact
 from drama_plugin.visual.dialogue_coverage import coverage_intervals
 intervals=coverage_intervals(ctx,artifact);out=[]
 for sh in group:
  c=deepcopy(ctx);c['shot']=sh;raw=dump_contract(spec);raw.update(shotId=sh['id'],sourceFingerprint=fp(narrative_source(c)))
  raw['performance']['beats']=[{'start':0,'end':8,'kind':'CONTINUOUS','startState':spec.opening_state,'endState':spec.ending_state,'actions':[{'actor':'A','behavior':'持续托架；听者看手与架的接触'}]}]
  item=intervals[sh['id']]['L'];d=raw['dialogue'][0];d.update(text=line['text'],start=item['start'],end=item['end'],canonicalInterval=list(item['canonical_interval']),textRange=list(item['text_range']),coverageIntent=item['coverage_intent'])
  current=CinematicShotSpec.model_validate(raw);f=freeze_direction(current,context=c,visual_resolution=visual,host_review='OFFLINE contiguous spoken group; no repeated words')
  out.append((current,c,f))
 return out


def test_shared_dialogue_reaction_covers_only_own_interval():
 out=shared_fixture();a,b=[x[0].dialogue[0] for x in out]
 assert a.end-a.start==7 and b.end-b.start==3
 assert a.text[a.text_range[0]:a.text_range[1]]+b.text[b.text_range[0]:b.text_range[1]]==a.text
 assert b.coverage_intent=='REACTION'
 spec,ctx,_=out[1];ctx['sceneShots'][0]['content']['plannedDurationMs']=7000
 with pytest.raises(ValueError,match='STALE_DIALOGUE'):validate_canon(spec,ctx)


def test_architecture_does_not_add_skills_or_provider_core_dialects():
 root=Path(__file__).resolve().parents[1]
 assert len(list((root/'skills').glob('*/skill.yaml')))==14
 for file in ['contracts/cinematic.py','visual/cinematic.py','visual/dialogue_coverage.py','visual/reference_duties.py']:
  text=(root/'src/drama_plugin'/file).read_text().lower()
  assert all(s not in text for s in ['bytedance','seedance','minimax','comfy_video','hosts.'])
 text=(root/'src/drama_plugin/hosts/comfy_video.py').read_text()
 assert 'prompt[:2000]' not in text and 'len(prompt) > 2000' not in text


@pytest.mark.asyncio
async def test_formal_entry_refreshes_media_before_any_write(tmp_path):
 from drama_plugin.hosts.route_production import operate
 from drama_plugin.contracts.creation import Work,Script,Episode,Scene,Shot
 from drama_plugin.contracts.media import Media
 from test_cinematic_direction import example
 from drama_plugin.visual.cinematic import narrative_source
 from test_production_route import route as route_fixture
 r,c,g,s,a=seed_fixture(tmp_path);spec,ctx,visual=example()
 ctx['script']['title']='S';ctx['episode'].update(title='E',episode_no=1);ctx['scene'].update(title='SC',order=1);ctx['shot']['shot_no']='S1'
 models={'work':Work,'script':Script,'episode':Episode,'scene':Scene,'shot':Shot};entities={k:models[k].model_validate(v) for k,v in ctx.items()};ctx={k:v.model_dump(mode='json') for k,v in entities.items()}
 spec.source_fingerprint=fp(narrative_source(ctx));f=freeze_direction(spec,context=ctx,visual_resolution=visual,host_review='OFFLINE')
 r=r.model_copy(update={'frozen_creative':selection_handoff(f),'source_fingerprint':spec.source_fingerprint})
 d=seal(r,c,g,s,a)
 route=route_fixture(tmp_path).model_dump(mode='json');route.update(creative_fingerprint=spec.source_fingerprint,candidate=c.model_dump(mode='json'))
 route['requirements'].update(creative_schema='cinematic-shot-v1',cinematic_directions={'S1':f},shots={'S1':'SHOT'})
 entities['work'].content.update(productionRoute=route,productionStage={'frames':{'S1':d},'attempts':[]})
 class Memory:
  writes=0
  def __getattr__(self,name):
   assert name.startswith('get_')
   async def get(identity):return deepcopy(entities[name[4:]])
   return get
  async def save_work(self,*args,**kwargs):self.writes+=1
 class MediaReader:
  reads=0
  async def get_media(self,identity):
   self.reads+=1
   return Media.model_validate({**a['bindings'][0]['formal_media'],'source_ref':'changed','content':{}})
 memory=Memory();reader=MediaReader()
 with pytest.raises(ValueError,match='FORMAL_REFERENCE_REFRESH'):
  await operate(memory,'W','reserve',{'shot_id':'S1'})
 with pytest.raises(ValueError,match='FORMAL_REFERENCE_MEDIA_CHANGED'):
  await operate(memory,'W','reserve',{'shot_id':'S1'},media=reader)
 assert memory.writes==0 and reader.reads==1


def test_required_reference_missing_cannot_qualify_even_limited_trial(tmp_path):
 r,c,*_=seed_fixture(tmp_path)
 with pytest.raises(ValueError,match='REQUIRED_REFERENCE_UNFULFILLED'):
  qualify(r.model_copy(update={'reference_duties':()}),c)


def test_coverage_mismatched_text_slice_rejected_after_refreeze():
 spec,ctx,frozen=shared_fixture()[1]
 frozen['spec']['dialogue'][0]['textRange']=[0,len(spec.dialogue[0].text)]
 frozen['fingerprint']=fp({k:v for k,v in frozen.items() if k!='fingerprint'})
 from drama_plugin.visual.cinematic import verify_frozen
 with pytest.raises(ValueError,match='FROZEN_DIALOGUE_COVERAGE_CHANGED'):verify_frozen(frozen)


def test_camera_and_performance_refs_need_actual_motion_not_character_picture(tmp_path):
 for role in ['CAMERA_MOTION','PERFORMANCE']:
  r,c,g,s,a=seed_fixture(tmp_path);f=r.frozen_creative['cinematic_direction'];spec=f['spec']
  spec['referenceRequirements'].append({'role':role,'subject':'movement','purpose':'observed motion','necessity':'REQUIRED','establishesOpeningState':False});spec['executionRequirements']['referenceRoles'].append(role)
  f['fingerprint']=fp({k:v for k,v in f.items() if k!='fingerprint'})
  r=r.model_copy(update={'frozen_creative':selection_handoff(f)})
  with pytest.raises(ValueError,match='REQUIRED_REFERENCE'):seal(r,c,g,s,a)


@pytest.mark.parametrize('role',['OFF_SCREEN','REACTION'])
def test_shared_role_from_formal_binding_is_preserved(role):
 spec,ctx,frozen=shared_fixture(role)[1]
 assert spec.dialogue[0].coverage_intent==role
 assert spec.dialogue[0].end-spec.dialogue[0].start==3
 from drama_plugin.visual.cinematic import verify_frozen
 assert verify_frozen(frozen)==spec


def test_duplicate_requirement_cannot_hide_a_duty(tmp_path):
 r,c,g,s,a=seed_fixture(tmp_path);f=r.frozen_creative['cinematic_direction']
 f['spec']['referenceRequirements'].append(deepcopy(f['spec']['referenceRequirements'][0]))
 f['fingerprint']=fp({k:v for k,v in f.items() if k!='fingerprint'})
 r=r.model_copy(update={'frozen_creative':selection_handoff(f)})
 with pytest.raises(ValueError,match='DUPLICATE_REFERENCE'):qualify(r,c)


def test_legacy_seal_without_new_optional_fields_replays(tmp_path):
 from test_video_selection import decision
 d=decision(tmp_path)
 for owner in ('requirements','spec'):
  d[owner].pop('reference_duties')
  for inp in d[owner]['inputs']:
   for key in ('source_ref','mime_type','endpoint_state','endpoint_evidence','width','height'):
    inp.pop(key)
 d['candidate'].pop('capability')
 d['fingerprint']=fp({k:v for k,v in d.items() if k!='fingerprint'})
 before=deepcopy(d);verify_execution(d)
 assert d==before
