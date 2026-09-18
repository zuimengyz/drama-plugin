from pathlib import Path
from copy import deepcopy
import sys
import pytest
from drama_plugin.contracts.base import dump_contract,sha256_canonical as fp
from drama_plugin.contracts.film_score import FilmScorePlan,MusicCue,MusicGenerationRequirements
from drama_plugin.contracts.performance_direction import VocalDelivery
from drama_plugin.contracts.creative_asset import MusicRights
from drama_plugin.contracts.sequence import SourcePin
from drama_plugin.music_direction import review_score_plan,composer_brief,cue_production_eligible,qualify_music_requirements,validate_score_context
from drama_plugin.vocal_direction import historical_verse_realization,require_vocal_capability,native_vocal_disposition
from performance_direction_helpers import make_case
sys.path.insert(0,str(Path(__file__).parents[1]/'integration/fixtures'))
from r3_fixture_builder import build_fixture
from music_fixture_builder import gaixia_score,silent_plan,cue

@pytest.fixture(scope='module')
def gaixia():
    f=build_fixture((Path(__file__).parents[1]/'integration/fixtures/r3_source_proposal.md').read_text(),'a'*64,music_constraints={'P02':('NO_SCORE',),'P03':('NO_SCORE',),'P08':('PRESERVE_REAL_JOY',),'P09':('NO_FATALISTIC_FORESHADOWING',)})
    return f,gaixia_score(f,'b'*64)

def review(f,result,plan):return review_score_plan(plan,current=result['current'],expected_scene_ids=list(f['intents']),performance_intents=f['intents'],excluded_performance_refs=result['plan'].excluded_performance_refs)

def test_all_ten_scenes_reviewed_with_multiple_silences(gaixia):
    f,r=gaixia;assert r['review']['status']=='SCORE_DESIGN_REVIEW_READY'
    assert r['review']['sceneCoverage']==10 and r['review']['scoreScenes']==3 and not r['review']['allScenesHaveMusic']
    assert {d.scene_id for d in r['plan'].scene_music_decisions if d.cue_refs}=={'P01','P04','P08'}
    assert len(r['composer_briefs'])==3
    assert all(not cue_production_eligible(c) for c in r['plan'].music_cues)

@pytest.mark.parametrize('field',['narrativeFunction','entryTrigger','exitTrigger'])
def test_cue_requires_real_dramatic_instruction(gaixia,field):
    raw=dump_contract(gaixia[1]['plan']);raw['musicCues'][0][field]=''
    with pytest.raises(ValueError):FilmScorePlan.model_validate(raw)

def test_no_timeline_only_design(gaixia):
    raw=dump_contract(gaixia[1]['plan']);raw['musicCues'][0]['entryTrigger']='00:42.5'
    with pytest.raises(ValueError,match='DRAMATIC_TRIGGER'):FilmScorePlan.model_validate(raw)

@pytest.mark.parametrize('fault',['missing-scene','stale','verse-binding','verse-cue','verse-reference','no-ai-requirements','foreign-motif','vendor-params'])
def test_score_fail_closed(gaixia,fault):
    f,r=gaixia;raw=dump_contract(r['plan'])
    if fault=='missing-scene':raw['sceneMusicDecisions'].pop()
    elif fault=='stale':raw['sourcePins'][0]['fingerprint']='0'*64
    elif fault=='verse-binding':raw['musicCues'][0]['bindingRefs']=[dump_contract(SourcePin(key='P03:spoken:N04',kind='DIRECTION',fingerprint='c'*64))]
    elif fault=='verse-cue':raw['musicCues'][0]['contentKind']='HISTORICAL_VERSE_PERFORMANCE'
    elif fault=='verse-reference':raw['musicCues'][0]['generationRequirements']['referenceRefs']=[dump_contract(SourcePin(key='P03:spoken:N05',kind='DIRECTION',fingerprint='c'*64))]
    elif fault=='no-ai-requirements':raw['musicCues'][0]['generationRequirements']=None
    elif fault=='foreign-motif':raw['musicCues'][0]['motifRefs']=['FOREIGN']
    else:raw['musicCues'][0]['generationRequirements']['providerTemperature']=0.8
    with pytest.raises(ValueError):review(f,r,FilmScorePlan.model_validate(raw))

def test_historical_verse_never_composer_or_generation(gaixia):
    _,r=gaixia
    for ref in ('P03:spoken:N04','P03:spoken:N05','P03:nonlexical-vocal'):
        with pytest.raises(ValueError,match='HISTORICAL_VERSE'):composer_brief(r['plan'],ref,current=r['current'])
    raw=dump_contract(r['plan'].music_cues[0].generation_requirements);raw['contentKind']='HISTORICAL_VERSE_PERFORMANCE'
    with pytest.raises(ValueError):MusicGenerationRequirements.model_validate(raw)

def test_current_amendment_preserves_words_without_modern_song():
    old=VocalDelivery(mode='SUNG',source_ref='historical-text',lyric_status='EXACT_SOURCE',melody_status='UNRESOLVED')
    new=historical_verse_realization(old,policy_ref='policy',policy_fingerprint='b'*64,current={'policy':'b'*64})
    assert new.mode=='DECLAMED_VERSE' and new.melody_status=='NOT_APPLICABLE' and old.mode=='SUNG'
    with pytest.raises(ValueError):require_vocal_capability(new,supported_modes={'SPOKEN'})
    assert require_vocal_capability(new,supported_modes={'DECLAMED_VERSE'})['status']=='SEMANTIC_REQUIREMENT_SATISFIED'
    response=historical_verse_realization(old,policy_ref='policy',policy_fingerprint='b'*64,current={'policy':'b'*64},shared_response=True)
    assert response.lyric_status=='NO_APPROVED_LYRICS' and response.realization_status=='UNRESOLVED'
    with pytest.raises(ValueError):require_vocal_capability(response,supported_modes={'SHARED_RESPONSE'})
    with pytest.raises(ValueError):VocalDelivery(mode='DECLAMED_VERSE',source_ref='verse',lyric_status='EXACT_SOURCE',melody_status='APPROVED',melody_ref='modern-song')

def test_native_declaimed_performance_still_kept():
    c=make_case('intimate');delivery=VocalDelivery(mode='DECLAMED_VERSE',source_ref='text',lyric_status='EXACT_SOURCE',melody_status='NOT_APPLICABLE')
    assert native_vocal_disposition(c['review'],delivery,observed_mode='DECLAMED_VERSE')['disposition']=='KEEP_NATIVE'

@pytest.mark.parametrize('scene,emotion,relation',[('P08','MOURNING','SUPPORT_ACTION'),('P09','MOURNING','SUPPORT_ACTION'),('P03','NEUTRAL_TEXTURE','SUPPORT_ACTION'),('P01','PROPULSION','DUPLICATE_EMOTION')])
def test_music_cannot_override_performance_or_duplicate_it(gaixia,scene,emotion,relation):
    f,r=gaixia;raw=dump_contract(r['plan']);sid=scene
    if sid in ('P03','P09'):
        c=cue('bad',sid,'test contrary musical intent','scene begins','scene ends',emotion=emotion,relation=relation,motif='M01');raw['musicCues'].append(dump_contract(c))
        d=next(d for d in raw['sceneMusicDecisions'] if d['sceneId']==sid);d.update(decision='SCORE_PRESENT',cueRefs=['bad'],sourceStrategy='ORIGINAL_AI')
    else:
        c=next(c for c in raw['musicCues'] if sid in c['sceneIds']);c.update(emotionalDirection=emotion,performanceRelation=relation)
    out=review(f,r,FilmScorePlan.model_validate(raw));assert out['status']=='DEPARTMENT_CONFLICT'
    assert all(c['repairOwner']=='music-direction' for c in out['conflicts'])

def test_joy_is_allowed_without_third_climax(gaixia):
    _,r=gaixia;assert next(c for c in r['plan'].music_cues if 'P08' in c.scene_ids).emotional_direction=='JOY'
    assert next(d for d in r['plan'].scene_music_decisions if d.scene_id=='P10').decision=='NO_SCORE'

def test_rights_split_and_temp_release_guard(gaixia):
    _,r=gaixia;c=r['plan'].music_cues[0]
    legacy=MusicRights(status='VERIFIED',source='owned',license='commercial',commercial_use=True,attribution='none')
    assert legacy.allows_production()
    incomplete=legacy.model_copy(update={'composition_rights':'PUBLIC_DOMAIN','recording_rights':'UNKNOWN'})
    assert not incomplete.allows_production()
    cleared=incomplete.model_copy(update={'recording_rights':'CLEARED'})
    assert cue_production_eligible(c.model_copy(update={'rights':cleared}))
    assert not cue_production_eligible(c.model_copy(update={'rights':cleared,'source_strategy':'TEMP_REFERENCE'}))

@pytest.mark.parametrize('category',['motif','character','location','prop','cue','score_strategy','historical_assumption'])
def test_foreign_score_context_isolation(gaixia,category):
    _,r=gaixia
    def ctx(scope):return {'scope':scope,'entities':{'only':{'scope':scope,'display':category+'_'+scope,'kind':category,'source_ref':'fixture:'+scope,'evidence':'only '+scope}}}
    a,b=ctx('A'),ctx('B');p=r['plan'].model_copy(update={'score_thesis':category+'_A'})
    assert validate_score_context(p,b,foreign_contexts=[a])['status']=='FAIL'

@pytest.mark.parametrize('case',['intimate','victory','decision'])
@pytest.mark.parametrize('route',['live_action','stylized_cinematic_cg'])
def test_generic_silence_is_complete_and_route_independent(case,route):
    c=make_case(case,route);i=c['intent'];source=SourcePin(key='source',kind='DESIGN',fingerprint=i.source_fingerprints[next(iter(i.source_fingerprints))]);film=SourcePin(key='film',kind='DIRECTION',fingerprint='a'*64)
    plan=silent_plan(case,(source,),film,{i.scene_id:i});current={**c['current'],'source':source.fingerprint,'film':film.fingerprint,'performance:'+i.scene_id:fp(i)}
    out=review_score_plan(plan,current=current,expected_scene_ids=(i.scene_id,),performance_intents={i.scene_id:i})
    assert out['status']=='SCORE_DESIGN_REVIEW_READY' and out['scoreScenes']==0

def test_requirements_do_not_mean_qualified_or_authorized(gaixia):
    _,r=gaixia;c=r['plan'].music_cues[0];out=qualify_music_requirements(c,{})
    assert out['status']=='PRODUCTION_QUALIFICATION_BLOCKED' and 'stems' in out['missingOrFailed']
    assert not out['providerImplemented'] and not out['productionAuthorized']


def test_emotion_label_alone_is_not_a_cue(gaixia):
    raw=dump_contract(gaixia[1]['plan'].music_cues[0]);raw['narrativeFunction']='悲壮'
    with pytest.raises(ValueError,match='DRAMATIC_FUNCTION'):MusicCue.model_validate(raw)


def test_music_capability_bridge_uses_existing_request_and_feedback(gaixia,tmp_path):
    from drama_plugin import DramaPlugin
    from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
    from drama_plugin.hosts.director_capabilities import LocalCapabilityBridge
    from drama_plugin.contracts.director import CapabilityRequest
    f,r=gaixia;store=DirectorArtifactStore(tmp_path/'store');plugin=DramaPlugin.load(Path(__file__).parents[1])
    raw={'plan':dump_contract(r['plan']),'sceneIds':list(f['intents']),'performanceIntents':{k:dump_contract(v) for k,v in f['intents'].items()},'excludedPerformanceRefs':list(r['plan'].excluded_performance_refs)}
    ref=store.put('score-input',raw);current={**r['current'],ref.key:ref.fingerprint}
    q=CapabilityRequest(request_id='score-request',workspace_id='workspace',scope_id=r['plan'].scope_id,branch_id='music-design',source_pins=r['plan'].source_pins,intent_refs=(r['plan'].film_intent_ref,),requirement_refs=(ref,),capability='music-direction',task='Review source-bound score design',result_kind='DESIGN_ONLY',must_preserve=('Script and DPD authority',),prohibitions=('NO PROVIDER',),priority='HIGH',required_evidence=('CONTRACT_VALID',))
    feedback=LocalCapabilityBridge(store,plugin.skills.get).run(q,ref,current)
    assert feedback.execution=='COMPLETED' and feedback.fulfilled==('CONTRACT_VALID',)

@pytest.mark.parametrize('name',['war','intimate','political','silence'])
def test_authored_generic_music_fixtures(name):
    from music_fixture_builder import generic_score
    r=generic_score(name)
    assert r['review']['status']=='SCORE_DESIGN_REVIEW_READY'
    text=str(dump_contract(r['plan']))
    assert not any(x in text for x in ('虞','亭长','乌江','垓下'))
    assert bool(r['plan'].music_cues)==(name in ('war','political'))
