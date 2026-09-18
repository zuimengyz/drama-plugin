"""R3 contract/coverage regression; all observations are test attestations."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
import sys
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'integration/fixtures'))
from r3_fixture_builder import build_fixture
from drama_plugin.contracts.base import sha256_canonical as fp, dump_contract
from drama_plugin.contracts.performance_direction import VocalDelivery, PerformanceProjection, PerformanceObservation
from drama_plugin.contracts.sequence import FilmReview
from drama_plugin.performance_coverage import (full_performance_coverage_gate, validate_performance_context_isolation, render_bound_direction, validate_interaction, validate_ensemble, validate_continuity_edge, bind_full_performance_review, full_av_coverage, CATEGORIES, CONTINUITY_FIELDS)
from drama_plugin.performance_direction import validate_projection, ALIGNMENT_DIMENSIONS
from drama_plugin.vocal_direction import require_vocal_capability, native_vocal_disposition
from performance_direction_helpers import make_case

SOURCE=(Path(__file__).parents[1]/'integration/fixtures/r3_source_proposal.md').read_text()

@pytest.fixture(scope='module')
def film() -> dict[str,Any]:return build_fixture(SOURCE,'a'*64)

def gate(f: dict[str,Any]) -> dict[str,Any]:
    return full_performance_coverage_gate(f['inventory'],f['directions'],current_source_hash=f['source_hash'],contexts=f['contexts'],dpds=f['dpds'],source_text=SOURCE)


def test_all_scenes_lexical_actions_and_nonlyrical_voices_derived_from_source(film: dict[str,Any]) -> None:
    r=gate(film);assert r['status']=='FULL_PERFORMANCE_COVERAGE_READY'
    assert r['coverage']['scenes']['covered']==len(film['scenes'])==10
    assert r['coverage']['spoken']['covered']==sum(len(s['scene']['spoken']) for s in film['scenes'])
    assert r['coverage']['silent']['covered']==sum(len(s['scene']['action_paragraphs']) for s in film['scenes'])
    assert len(film['projections'])==r['coverage']['spoken']['covered']
    assert r['coverage']['voice']['covered']==r['coverage']['spoken']['covered']+3
    assert r['coverage']['shots']['status']=='NOT_APPLICABLE_WITH_REASON'


@pytest.mark.parametrize('category',[k for k in CATEGORIES if k!='shots'])
def test_missing_ordinary_fragment_blocks_full_coverage(film: dict[str,Any],category: str) -> None:
    f=deepcopy(film);ref=f['inventory'][category][0]['ref'];del f['directions'][ref]
    assert gate(f)['status']=='FULL_PERFORMANCE_COVERAGE_INCOMPLETE'


@pytest.mark.parametrize('category',['scenes','spoken','silent'])
def test_shrinking_inventory_cannot_fake_100_percent(film: dict[str,Any],category: str) -> None:
    f=deepcopy(film);f['inventory'][category].pop()
    with pytest.raises(ValueError,match='SOURCE_COVERAGE_INVENTORY'):gate(f)


def test_formal_book_must_supply_real_shots(film: dict[str,Any]) -> None:
    f=deepcopy(film);f['inventory']['scope']='FORMAL_PRODUCTION_BOOK'
    with pytest.raises(ValueError,match='TRUSTED_FORMAL_READER_REQUIRED'):gate(f)


def test_no_actor_exemption_requires_reason_and_no_actor_voice_group(film: dict[str,Any]) -> None:
    f=deepcopy(film);item={'ref':'environment-only','scene':'P01','source_ref':'P01:R1-proposal','performance_bearing':False,'actors':False,'vocal':False,'ensemble':False}
    f['inventory']['shots']=[item];f['directions']['environment-only']={'status':'NOT_APPLICABLE_WITH_REASON','reason':'Pure terrain; no actor, voice or performing group.'}
    assert gate(f)['coverage']['shots']['notApplicable']==1
    item['actors']=True;assert gate(f)['status']=='FULL_PERFORMANCE_COVERAGE_INCOMPLETE'
    item['actors']=False;f['directions']['environment-only']['reason']='';assert gate(f)['status']=='FULL_PERFORMANCE_COVERAGE_INCOMPLETE'


def sentinel(scope: str) -> dict[str,Any]:
    return {'scope':scope,'entities':{k:{'scope':scope,'kind':k,'display':k+'_'+scope,'source_ref':'fixture:'+scope,'evidence':'Bound source '+k+'_'+scope} for k in ('character','partner','prop','location','action','voice_target')}}


@pytest.mark.parametrize('kind',['character','partner','prop','location','action','voice_target'])
def test_foreign_ref_and_natural_language_sentinel_leak(kind: str) -> None:
    a=sentinel('A');b=sentinel('B')
    good=render_bound_direction('{character} passes {prop} to {partner} in {location}; {action}; voice to {voice_target}',b,foreign_contexts=[a])
    assert '_A' not in good
    r=validate_performance_context_isolation(context=b,refs=[kind],text=good+' '+kind+'_A',foreign_contexts=[a]);assert r['status']=='FAIL' and r['findings'][0]['evidence']==kind+'_A'
    b['entities'][kind]['scope']='A'
    assert validate_performance_context_isolation(context=b,refs=[kind],text='',foreign_contexts=[a])['status']=='FAIL'


def test_missing_template_ref_does_not_become_sample_fallback() -> None:
    with pytest.raises(ValueError,match='UNBOUND_TEMPLATE'):render_bound_direction('Wait for {unbound_partner}',sentinel('B'))


@pytest.mark.parametrize('name,forbidden',[('intimate',('虞','杯')),('decision',('亭长','船'))])
def test_r2_specific_leaks_removed_with_independent_context(name: str,forbidden: tuple[str,...]) -> None:
    c=make_case(name)
    texts=str(dump_contract(c['visual']))+str(dump_contract(c['audio']))
    assert all(token not in texts for token in forbidden)
    ctx=sentinel(name);foreign=sentinel('P03' if name=='intimate' else 'P09')
    ctx['entities']['character']['display']=c['config']['actor'];ctx['entities']['partner']['display']=c['config']['target'];ctx['entities']['prop']['display']='工具' if name=='intimate' else '地图'
    for k,word in zip(('partner','prop'),forbidden):foreign['entities'][k]['display']=word
    assert validate_performance_context_isolation(context=ctx,refs=['character','partner','prop'],text=texts,foreign_contexts=[foreign])['status']=='PASS'
    assert ctx['entities']['partner']['scope']==name


@pytest.mark.parametrize('missing',['speaker_action','listener_action','partner_cue','physical_handoff','voice_handoff','gaze_handoff','response_timing','next_beat_owner'])
def test_both_sides_and_handoffs_required(film: dict[str,Any],missing: str) -> None:
    i=deepcopy(film['directions']['P03:interaction:1']['interaction']);i[missing]=''
    with pytest.raises(ValueError,match='INTERACTION_DIRECTION_INCOMPLETE'):validate_interaction(i,film['dpds'])


def test_listener_missing_dpd_returns_owner_not_invented_psychology(film: dict[str,Any]) -> None:
    i=film['directions']['P09:interaction:1']['interaction'];dpds=dict(film['dpds']);dpds.pop(i['listener_dpd'])
    with pytest.raises(ValueError,match='PARTNER_DPD_REQUIRED'):validate_interaction(i,dpds)


def test_yu_boatman_and_lv_have_own_tasks(film: dict[str,Any]) -> None:
    for ref in ('P03:actor:虞美人','P09:actor:亭长','P10:actor:吕马童'):
        d=film['dpds'][ref];assert d.direction.objective and d.obstacle and d.direction.tactic
    assert '登船' in film['dpds']['P09:actor:亭长'].direction.objective
    assert film['continuity']['虞美人'][0]['post_exit']=='NO_INVENTED_POST_EXIT_STATE'


@pytest.mark.parametrize('field',['physical_load','fatigue','injury','voice_load','attention'])
def test_previous_exit_next_entry_requires_sourced_transition(film: dict[str,Any],field: str) -> None:
    e=deepcopy(film['edges'][0]);e['next_entry'][field]='different';e['transitions'].pop(field,None)
    with pytest.raises(ValueError,match='PERFORMANCE_CONTINUITY_CONFLICT'):validate_continuity_edge(e)


def test_release_is_temporary_and_body_voice_load_stays_compatible(film: dict[str,Any]) -> None:
    e=deepcopy(next(e for e in film['edges'] if e['character']=='项羽' and e['from']=='P03'))
    assert e['next_entry']['release_residue']!='PERMANENT:sad'
    e['next_entry']['release_residue']='PERMANENT:sad'
    with pytest.raises(ValueError,match='RELEASE_CANNOT'):validate_continuity_edge(e)
    e=deepcopy(film['edges'][0]);e['next_entry']['physical_load']='HIGH';e['next_entry']['voice_load']='LOW'
    e['transitions']={k:{'reason':'fixture described change','source_ref':'fixture'} for k in CONTINUITY_FIELDS if e['previous_exit'][k]!=e['next_entry'][k]}
    with pytest.raises(ValueError,match='BODY_VOICE_LOAD'):validate_continuity_edge(e)


def test_continuity_has_no_duplicate_dpd_psychology(film: dict[str,Any]) -> None:
    e=deepcopy(film['edges'][0]);e['next_entry']['subtext']='new psychology'
    with pytest.raises(ValueError,match='SECOND_PSYCHOLOGY'):validate_continuity_edge(e)


def test_p01_ensemble_has_separate_layers_and_task_persistence(film: dict[str,Any]) -> None:
    ens=film['directions']['P01:ensemble']['ensemble'];validate_ensemble(ens,film['dpds'])
    assert len(ens['groups'])==6 and len({g['latency_order']for g in ens['groups']})>1
    assert all(g['task_persistence'] and g['attention'] for g in ens['groups'])


@pytest.mark.parametrize('fault',['sync','task','dpd','psychology','new-speech'])
def test_ensemble_does_not_become_npc_or_new_authority(film: dict[str,Any],fault: str) -> None:
    ens=deepcopy(film['directions']['P01:ensemble']['ensemble'])
    if fault=='sync':
        for g in ens['groups']:g['latency_order']=0
    elif fault=='task':ens['groups'][0]['task_persistence']=''
    elif fault=='dpd':ens['groups'][0]['dpd_ref']='missing'
    elif fault=='psychology':ens['psychology']='crowd mental model'
    else:ens['added_spoken_content']=True
    with pytest.raises(ValueError):validate_ensemble(ens,film['dpds'])


@pytest.mark.parametrize('mode',['SPOKEN','RECITATIVE','SUNG','SHARED_RESPONSE','NONVERBAL'])
def test_vocal_mode_preserved_and_unsupported_fails(mode: Any) -> None:
    d=VocalDelivery(mode=mode,source_ref='generic:vocal',lyric_status='NO_APPROVED_LYRICS' if mode in ('SHARED_RESPONSE','NONVERBAL') else 'EXACT_SOURCE',melody_status='UNRESOLVED' if mode in ('SUNG','RECITATIVE','SHARED_RESPONSE') else 'NOT_APPLICABLE')
    assert d.mode==mode
    with pytest.raises(ValueError,match='VOCAL_MODE_CAPABILITY_REQUIRED'):require_vocal_capability(d,supported_modes=set())
    if d.melody_status=='UNRESOLVED':
        with pytest.raises(ValueError,match='MELODY_UNRESOLVED'):require_vocal_capability(d,supported_modes={mode})
    else:assert require_vocal_capability(d,supported_modes={mode})['mode']==mode


def test_shared_response_no_new_lyric_and_good_native_stays_native() -> None:
    d=VocalDelivery(mode='SHARED_RESPONSE',source_ref='P03:response',lyric_status='NO_APPROVED_LYRICS',melody_status='UNRESOLVED')
    with pytest.raises(ValueError,match='NEW_LYRICS'):require_vocal_capability(d,supported_modes={'SHARED_RESPONSE'},lyrics='invented poem')
    c=make_case('P03');r=native_vocal_disposition(c['review'],d,observed_mode='SHARED_RESPONSE');assert r['disposition']=='KEEP_NATIVE'
    assert native_vocal_disposition(c['review'],d,observed_mode='SPOKEN')['disposition']=='REVIEW_REQUIRED'


def test_actual_audio_adapter_cannot_silently_speak_a_song(film: dict[str,Any]) -> None:
    from drama_plugin.contracts.audio_projection import AudioPerformanceBrief
    from drama_plugin.providers.speech.fish_audio import map_audio_performance_to_fish
    brief=AudioPerformanceBrief.model_validate(film['projections']['P03:spoken:N04']['audioPerformanceBrief'])
    with pytest.raises(ValueError,match='VOCAL_MODE_CAPABILITY_REQUIRED'):map_audio_performance_to_fish(brief)


def test_all_av_fragments_including_ordinary_need_observation(film: dict[str,Any]) -> None:
    r=bind_full_performance_review(FilmReview(media_hash='a'*64,duration=10),film['inventory'])
    assert len(r.performance_required_beats)==len(film['inventory']['av_plan'])
    assert full_av_coverage(r)['status']=='AV_PERFORMANCE_COVERAGE_INCOMPLETE'
    keys=r.performance_required_beats;rows={k:{x:'PASS' for x in ALIGNMENT_DIMENSIONS} for k in keys}
    evidence=[]
    for k in keys:
        beat,line=k.split('#')
        for channel in r.performance_coverage_channels[k]:evidence.append(PerformanceObservation(channel=channel,beat_id=beat,spoken_content_id=line,speaker_key='fixture',media_hash='a'*64,method='NORMAL_AV',observer='simulated test',evidence_ref='test-only',start_ms=0,end_ms=10000,external_expression='LOW',external_control='HIGH',body_load='LOW',meaning_preserved='PASS',interaction_target='fixture partner',breath='supported',continuity_in='task in progress',continuity_out='task continues'))
    complete=r.model_copy(update={'performance_beats':rows,'performance_observations':tuple(evidence)})
    assert full_av_coverage(complete)['status']=='COVERED'
    unknown=complete.model_copy(update={'performance_observations':(evidence[0].model_copy(update={'external_control':'UNKNOWN'}),*evidence[1:])})
    assert full_av_coverage(unknown)['status']=='AV_PERFORMANCE_COVERAGE_INCOMPLETE'
    partial=complete.model_copy(update={'performance_observations':tuple(evidence[1:])})
    assert full_av_coverage(partial)['status']=='AV_PERFORMANCE_COVERAGE_INCOMPLETE'


def test_live_action_coverage_interaction_continuity_voice_independent(film: dict[str,Any]) -> None:
    live=build_fixture(SOURCE,'b'*64,'live_action');assert gate(live)['status']=='FULL_PERFORMANCE_COVERAGE_READY'
    assert live['intents']==film['intents'] and live['edges']==film['edges'] and live['dpds']==film['dpds']
    for k,p in live['projections'].items():
        assert p['audioPerformanceBrief']==film['projections'][k]['audioPerformanceBrief']
        assert p['visualProjection']!=film['projections'][k]['visualProjection']


def test_generic_ensemble_meeting_with_task_persistence() -> None:
    from drama_plugin.contracts.dpd import BeatDPD, DPDLayerState
    dpds={}
    groups=[]
    for order,(name,task,trigger,response) in enumerate([('presenter_B','finish explaining route_B','question_B','stop pointing and listen'),('recorder_B','record decision_B','speaker ends','look up after writing'),('doorwatch_B','keep exit_B usable','evacuation cue_B','open clearance after checking outside')]):
        ref='meeting_B:'+name;dpds[ref]=BeatDPD(scene_id='meeting_B',beat_id=ref,actor=name,obstacle='different sight lines',transition_trigger=trigger,direction=DPDLayerState(objective=task,interaction_target='meeting_B',tactic=response))
        groups.append({'group_ref':name,'dpd_ref':ref,'attention':task,'trigger':trigger,'response':response,'latency_order':order,'task_persistence':task,'variation':'respond only after locally received cue'})
    validate_ensemble({'groups':groups,'added_spoken_content':False},dpds)


def test_projection_cannot_resolve_an_unbound_context_reference(film: dict[str,Any]) -> None:
    d=film['directions']['P03:spoken:N01'];p=PerformanceProjection.model_validate(film['projections'][d['ref']]['visualProjection']);ctx=film['contexts']['P03']
    current={'r1-proposal':film['source_hash'],'grammar:stylized_cinematic_cg':'a'*64,'performance-context':fp(ctx),**{'context-ref:'+r:fp(ctx) for r in ctx['entities']}}
    bad=p.model_copy(update={'context_refs':('prop:foreign_A',)})
    with pytest.raises(ValueError,match='STALE_PERFORMANCE_CONTEXT'):validate_projection(film['intents']['P03'],film['dpds'][d['objective_ref']],bad,current,'VISUAL')


def test_director_store_requires_recomputed_full_coverage_before_design_receipt(film: dict[str,Any],tmp_path: Path) -> None:
    from drama_plugin.contracts.director import DirectorWorkspace,CapabilityRequest,CapabilityFeedback
    from drama_plugin.contracts.sequence import SourcePin,DirectorReviewFacet
    from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
    from drama_plugin.director import request_pin,feedback_pin,DirectorError
    store=DirectorArtifactStore(tmp_path)
    source=SourcePin(key='proposal-fixture',kind='CANON',fingerprint=film['source_hash'])
    intent=store.put('intent-fixture',{'type':'DESIGN_ONLY'})
    w=store.create(DirectorWorkspace(workspace_id='r3-test',scope_id='proposal-fixture',branch_id='design-fixture',source_pins=(source,),intent_refs=(intent,)))
    q=CapabilityRequest(request_id='q',workspace_id=w.workspace_id,scope_id=w.scope_id,branch_id=w.branch_id,source_pins=w.source_pins,intent_refs=w.intent_refs,capability='cinematic-direction',task='Full performance coverage design fixture',result_kind='DESIGN_ONLY',must_preserve=('R1 unchanged',),prohibitions=('NO PRODUCTION',),priority='HIGH',required_evidence=('FULL_PERFORMANCE_COVERAGE',))
    qr=store.put(request_pin(q).key,dump_contract(q));current={p.key:p.fingerprint for p in (source,intent)}
    w=store.transition(w,'REQUEST',qr,current)
    result=store.put('direction-fixture',{'notFormal':True});evidence=store.put('coverage-fixture',gate(film));delta=store.put('delta-fixture',{'domain':'character_presentation','summary':'Synthetic design coverage receipt, no real source adoption','presentationOnly':True})
    current.update({p.key:p.fingerprint for p in (result,evidence,delta)})
    f=CapabilityFeedback(request_ref=qr,source_pins=w.source_pins,result_refs=(result,),evidence_refs=(evidence,),execution='COMPLETED',feasibility='SUPPORTED',fulfilled=q.required_evidence,next_responsibility='director')
    fr=store.retain_feedback(q,f);w=store.transition(w,'FEEDBACK',fr,current)
    facet=DirectorReviewFacet(workspace_id=w.workspace_id,scope_id=w.scope_id,branch_id=w.branch_id,source_pins=w.source_pins,intent_refs=w.intent_refs,request_ref=qr,feedback_ref=feedback_pin(f),intent_coverage={intent.key:'PASS'},disposition='APPROVE',reason_summary='Simulated design review only',adopted_delta_ref=delta)
    rr=store.put('review-fixture',{'subjectKind':'DESIGN_ONLY','director':dump_contract(facet),'findings':[]})
    with pytest.raises(DirectorError,match='coverage bundle'):store.transition(w,'REVIEW',rr,current)
    bundle={'inventory':film['inventory'],'directions':film['directions'],'current_source_hash':film['source_hash'],'contexts':film['contexts'],'dpds':film['dpds'],'source_text':SOURCE}
    updated=store.transition(w,'REVIEW',rr,current,performance_coverage_bundle=bundle)
    assert updated.adopted_head is not None
