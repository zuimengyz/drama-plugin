"""Source-event placement gates; synthetic fixtures, no provider or formal IO."""
from pathlib import Path
import sys
from copy import deepcopy
import pytest
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.film_score import FilmScorePlan, MusicYieldPolicy
from drama_plugin.music_placement import review_placement, require_score_permission, reconcile_material, validate_finishing_score_binding
from drama_plugin.music_direction import composer_brief
sys.path.insert(0,str(Path(__file__).parents[1]/'integration/fixtures'))
from music_fixture_builder import generic_score, gaixia_score
from r3_fixture_builder import build_fixture


def event(ref, action):
    return dict(sourceRef=dict(key=ref,kind='DESIGN',fingerprint=fp(ref)),trigger='Source action '+ref,action=action,primarySound='native action',reason='Preserve information and weight')

def policy(refs):
    return dict(events=[event(refs[0],'ENTER'),event(refs[1],'BUILD'),event(refs[2],'DROP'),event(refs[3],'DO_NOT_RETURN')],protectedNoScoreRefs=[dict(key=refs[3],kind='DESIGN',fingerprint=fp(refs[3]))],reentryPolicy='DO_NOT_RETURN')

def placed():
    r=generic_score('war');raw=dump_contract(r['plan']);refs=['build','narrow','impact','response'];raw['musicCues'][0]['yieldPolicy']=policy(refs)
    return FilmScorePlan.model_validate(raw),{**r['current'],**{k:fp(k) for k in refs}},{k:'generic-war' for k in refs}

def allow(p,ref='build',scene='generic-war'):
    require_score_permission(p,scene_id=scene,action_refs=[ref],cue_id='cue-war')

def recipe(p,current,scenes):
    return dict(scorePlacement=dict(plan=dump_contract(p),planFingerprint=fp(p),current=current,actionScenes=scenes),soundPlan={'bgm':{'decision':'ACTIVE'}},layers=[dict(role='BGM',scoreBinding=dict(planFingerprint=fp(p),sceneId='generic-war',cueId='cue-war',actionRefs=['build']))])

def test_build_drop_impact_and_brief_mapping():
    p,c,s=placed();assert review_placement(p,current=c,action_scenes=s)['status']=='PLACEMENT_DESIGN_READY';allow(p)
    b=composer_brief(p,'cue-war',current=c);assert b['yieldPolicy']['events'][2]['action']=='DROP'
    with pytest.raises(ValueError,match='OUTSIDE'):allow(p,'impact')

@pytest.mark.parametrize('flag',['yieldToDialogue','yieldToPhysicalImpact','yieldToNativeBreath','yieldToPartnerResponse','yieldToDiegeticMusic'])
def test_priority_protection_cannot_be_disabled(flag):
    raw=policy(['a','b','c','d']);raw[flag]=False
    with pytest.raises(ValueError):MusicYieldPolicy.model_validate(raw)

@pytest.mark.parametrize('decision',['NO_SCORE','NO_SCORE_MUST_PRESERVE','DIEGETIC_ONLY'])
def test_silence_active_cannot_autofill(decision):
    r=generic_score('intimate');raw=dump_contract(r['plan']);raw['sceneMusicDecisions'][0]['decision']=decision;p=FilmScorePlan.model_validate(raw)
    assert review_placement(p,current=r['current'],action_scenes={})['scoreScenes']==[]
    with pytest.raises(ValueError,match='NO_SCORE_ACTIVE'):allow(p,scene='generic-intimate')
    raw['sceneMusicDecisions'][0]['cueRefs']=['auto-fill']
    with pytest.raises(ValueError,match='SILENCE'):FilmScorePlan.model_validate(raw)

@pytest.mark.parametrize('fault',['missing','stale','unknown-action','timestamp','no-exit','auto-return','development-after-drop','protected-enter'])
def test_fail_closed_placement(fault):
    p,c,s=placed();raw=dump_contract(p);q=raw['musicCues'][0]['yieldPolicy']
    if fault=='missing':raw['musicCues'][0]['yieldPolicy']=None
    elif fault=='stale':c['build']='0'*64
    elif fault=='unknown-action':s.pop('build')
    elif fault=='timestamp':q['events'][0]['trigger']='18.3s'
    elif fault=='no-exit':q['events'][2]['action']='HOLD'
    elif fault=='auto-return':q['events'][-1]['action']='RETURN'
    elif fault=='development-after-drop':q['events'][-1]['action']='HOLD';q['protectedNoScoreRefs']=[]
    elif fault=='protected-enter':q['protectedNoScoreRefs']=[q['events'][0]['sourceRef']]
    with pytest.raises(ValueError):review_placement(FilmScorePlan.model_validate(raw),current=c,action_scenes=s)

def test_reviewed_return_is_possible_but_not_automatic():
    q=policy(['a','b','c','d']);q['events'] += [event('e','RETURN'),event('f','STOP')];q['reentryPolicy']='SOURCE_EVENT'
    assert MusicYieldPolicy.model_validate(q).events[-2].action=='RETURN'

def test_historical_verse_never_placement():
    p,c,s=placed();raw=dump_contract(p);raw['excludedPerformanceRefs']=['build'];p=FilmScorePlan.model_validate(raw)
    with pytest.raises(ValueError,match='HISTORICAL_VERSE'):review_placement(p,current=c,action_scenes=s)
    with pytest.raises(ValueError,match='HISTORICAL_VERSE'):allow(p)

def test_protected_partner_response_remains_absent():
    p,_,_=placed()
    with pytest.raises(ValueError,match='NO_SCORE_MUST'):allow(p,'response')

def test_combined_build_and_impact_ref_is_not_whole_action_permission():
    p,c,s=placed();raw=dump_contract(p);raw['musicCues'][0]['yieldPolicy']['events'][2]['sourceRef']=raw['musicCues'][0]['yieldPolicy']['events'][1]['sourceRef'];p=FilmScorePlan.model_validate(raw)
    assert review_placement(p,current=c,action_scenes=s)['status']=='PLACEMENT_DESIGN_READY'
    with pytest.raises(ValueError,match='MIXED_PHASE'):allow(p,'narrow')

def test_reassign_good_material_does_not_fail_or_adopt():
    r=reconcile_material(material_hash='a'*64,planned='FULL_BATTLE_RELEASE',realized='PRE_CLIMAX_BUILD_UP',user_receipt={'materialHash':'a'*64,'contentListening':'ACCEPTABLE_MATERIAL'},disposition='REPLACE_FUNCTION')
    assert r['functionMismatch']=='PARTIAL' and not r['generationFailed'] and not r['adopted'] and not r['approved']
    with pytest.raises(ValueError):reconcile_material(material_hash='b'*64,planned='a',realized='b',user_receipt={'materialHash':'a'*64},disposition='REPLACE_FUNCTION')

@pytest.mark.parametrize('fault',['proposal','stale-plan','stale-source','unbound','protected','missing-plan','missing-layer'])
def test_finishing_blocks_before_any_render(fault):
    p,c,s=placed();p=p.model_copy(update={'source_kind':'FORMAL'});r=recipe(p,c,s)
    if fault=='proposal':r=recipe(p.model_copy(update={'source_kind':'PROPOSAL_ONLY'}),c,s)
    elif fault=='stale-plan':r['scorePlacement']['planFingerprint']='0'*64
    elif fault=='stale-source':r['scorePlacement']['current']['build']='0'*64
    elif fault=='unbound':r['layers'][0].pop('scoreBinding')
    elif fault=='protected':r['layers'][0]['scoreBinding']['actionRefs']=['response']
    elif fault=='missing-plan':r.pop('scorePlacement')
    else:r['layers']=[]
    with pytest.raises(ValueError):validate_finishing_score_binding(r)

def test_finishing_bound_formal_synthetic_and_legacy_compatible():
    p,c,s=placed();validate_finishing_score_binding(recipe(p.model_copy(update={'source_kind':'FORMAL'}),c,s));validate_finishing_score_binding({'layers':[]})

@pytest.fixture
def p08():
    f=build_fixture((Path(__file__).parents[1]/'integration/fixtures/r3_source_proposal.md').read_text(),'a'*64)
    r=gaixia_score(f,'b'*64);raw=dump_contract(r['plan']);current=dict(r['current']);scenes={}
    for cue in raw['musicCues']:
        sid=cue['sceneIds'][0];refs=[sid+':silent:'+str(n).zfill(2) for n in ([7,8,9,10] if sid=='P08' else [1,2,3,4])]
        cue['yieldPolicy']=policy(refs);current.update({x:fp(x) for x in refs});scenes.update({x:sid for x in refs})
        if sid=='P08':
            for ref in ['P08:spoken:s7-how','P08:spoken:s7-as','P08:silent:12','P08:silent:13']:
                cue['yieldPolicy']['protectedNoScoreRefs'].append(dict(key=ref,kind='DESIGN',fingerprint=fp(ref)));current[ref]=fp(ref);scenes[ref]=sid
            cue['yieldPolicy']['events'].append(event('P08:silent:13','DO_NOT_RETURN'))
    return FilmScorePlan.model_validate(raw),current,scenes

@pytest.mark.parametrize('ref',['P08:silent:01','P08:spoken:s7-last','P08:spoken:s7-how','P08:spoken:s7-as','P08:silent:12','P08:silent:13'])
def test_p08_start_speech_question_response_joy_pursuit_protected(p08,ref):
    p,_,_=p08
    with pytest.raises(ValueError):require_score_permission(p,scene_id='P08',action_refs=[ref],cue_id='C03')

def test_p08_second_pressure_and_impact_drop(p08):
    p,c,s=p08;assert review_placement(p,current=c,action_scenes=s)['scenes']==10
    for ref in ('P08:silent:07','P08:silent:08'):require_score_permission(p,scene_id='P08',action_refs=[ref],cue_id='C03')
    assert next(c for c in p.music_cues if c.cue_id=='C03').yield_policy.events[2].action=='DROP'
    for d in p.scene_music_decisions:assert d.rationale and d.entry_trigger and d.exit_trigger and d.dialogue_native_priority

def test_renderer_calls_gate_before_output_directory(tmp_path):
    from drama_plugin.audio.finishing import render
    p,c,s=placed();r=recipe(p,c,s)
    # An invalid plan must be rejected before probing files or requiring recipe paths.
    with pytest.raises(ValueError,match='PROPOSAL'):render(r, {}, tmp_path/'never-created')
    assert not (tmp_path/'never-created').exists()
