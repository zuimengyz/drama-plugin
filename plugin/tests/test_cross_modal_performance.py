from typing import Any
from copy import deepcopy
import pytest
from pydantic import ValidationError
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.performance_direction import DirectorPerformanceIntent, PerformanceProjection
from drama_plugin.contracts.sequence import FilmFinding, FilmReview, PlaybackObservation
from drama_plugin.performance_direction import (review_av_performance, validate_projection, validate_intent,
    native_audio_disposition, reconcile_realized_performance, render_performance_pair, ALIGNMENT_DIMENSIONS)
from drama_plugin.visual.performance import build_realized_performance_snapshot
from drama_plugin.sequence import film_review_verdict
from performance_direction_helpers import make_case, CASES


def review(c: dict[str, Any]) -> FilmReview:
    return review_av_performance(dpd=c['dpd'],intent=c['intent'],visual=c['visual'],audio=c['audio'],realized=c['realized'],review=c['review'],current=c['current'])


def change_observation(c: dict[str, Any], channel: str, **updates: Any) -> None:
    key='visual_observation' if channel=='VISUAL' else 'voice_observation'
    observed=c[key].model_copy(update=updates)
    if channel=='VISUAL':
        c['realized']=build_realized_performance_snapshot({**dump_contract(c['realized']),'performanceObservations':[dump_contract(observed)]})
    else:c['review']=c['review'].model_copy(update={'performance_observations':(observed,)})
    c[key]=observed


@pytest.mark.parametrize('name',list(CASES))
def test_authored_chain_all_facets_pass_as_design_only(name: Any) -> None:
    c=make_case(name);before=deepcopy(c['dpd'])
    r=review(c)
    assert set(r.performance_alignment)==ALIGNMENT_DIMENSIONS
    assert set(r.performance_alignment.values())=={'PASS'}
    assert c['dpd']==before
    assert 'Actor / Visual' in render_performance_pair(c['dpd'],c['intent'],c['visual'],c['audio'],c['current'])
    assert film_review_verdict(r,r.media_hash)['status']!='CONTENT_REVIEW_COMPLETE_PENDING_USER_ADOPTION'


def test_pressure_is_not_external_amplitude_or_permanent_state() -> None:
    c=make_case('P03')
    assert c['dpd'].effective.internal_activation.value=='HIGH'
    assert c['visual'].director_performance.external_expression=='LOW'
    assert c['audio'].director_performance.external_control=='HIGH'
    assert '全片' in c['intent'].continuity_out
    assert '哭' not in c['audio'].intensity or '不把' in c['audio'].intensity
    next_c=make_case('P08');assert '笑' in next_c['intent'].performance_core
    assert c['audio'].voice_identity_ref==next_c['audio'].voice_identity_ref
    assert c['audio'].voice_profile_fingerprint==next_c['audio'].voice_profile_fingerprint


@pytest.mark.parametrize('field',['objective','obstacle','tactic','subtext','knowledge','internalEmotion','externalEmotion','Fish_parameter','Veo_setting'])
def test_no_second_psychology_or_provider_fields(field: Any) -> None:
    c=make_case('intimate')
    with pytest.raises(ValidationError):DirectorPerformanceIntent.model_validate({**dump_contract(c['intent']),field:'new truth'})
    with pytest.raises(ValidationError):PerformanceProjection.model_validate({**dump_contract(c['audio'].director_performance),field:'new truth'})


def test_mutated_dpd_is_rejected_before_projection() -> None:
    c=make_case('P03');bad=c['dpd'].model_copy(update={'effective':c['dpd'].effective.model_copy(update={'subtext':'different psychology'})})
    with pytest.raises(ValueError,match='DPD_REVIEW_REQUIRED'):validate_intent(c['intent'],bad,c['current'])


@pytest.mark.parametrize('fault',['target','control','amplitude','collapse','unapproved-release','coordination','stale-source','stale-grammar'])
def test_projection_authority_and_anti_overacting(fault: Any) -> None:
    c=make_case('P03');p=c['visual'].director_performance;current=dict(c['current'])
    changes={'target':{'interaction_target':'crowd'},'control':{'external_control':'LOW'},'amplitude':{'external_expression':'HIGH'},'collapse':{'behaviors':('collapse',)},'unapproved-release':{'release':('shouted_lament',)},'coordination':{'coordination':()}}
    p=p.model_copy(update=changes.get(fault,{}))
    if fault=='stale-source':current['r1-proposal']='0'*64
    if fault=='stale-grammar':current['grammar:stylized_cinematic_cg']='0'*64
    with pytest.raises(ValueError):validate_projection(c['intent'],c['dpd'],p,current,'VISUAL')


@pytest.mark.parametrize('channel,changes,facet,owner',[
 ('VISUAL',{'behaviors':('sobbing','collapse'),'external_expression':'HIGH'},'emotional_amplitude','shot-production'),
 ('VOICE',{'behaviors':('sobbing',),'external_expression':'HIGH'},'emotional_amplitude','audio-production'),
 ('VOICE',{'spatial_projection':'army-command scale'},'spatial_projection','audio-production'),
 ('VOICE',{'interaction_target':'crowd'},'interaction_target','audio-production'),
 ('VOICE',{'external_control':'LOW'},'external_control','audio-production'),
 ('VOICE',{'breath':'continuous ceremonial breath'},'breath','audio-production'),
 ('VOICE',{'continuity_out':'permanent sobbing through every following scene'},'continuity','director'),
])
def test_adversarial_av_conflicts(channel: Any, changes: Any, facet: Any, owner: Any) -> None:
    c=make_case('P03');change_observation(c,channel,**changes);r=review(c)
    assert r.performance_alignment[facet]=='FAIL'
    f=next(x for x in r.findings if x.key.endswith(':'+facet))
    assert f.repair_owner==owner and 'Evidence:' in f.observation
    assert film_review_verdict(r,r.media_hash)['status']=='REPAIR_REQUIRED'


def test_exhausted_body_cannot_have_unbroken_ceremonial_projection() -> None:
    c=make_case('P08');change_observation(c,'VOICE',behaviors=('unbroken_ceremonial_breath',));r=review(c)
    assert r.performance_alignment['body_voice_effort']=='FAIL'


@pytest.mark.parametrize('name,event,value',[('P03','rise_start',5000),('P03','gaze_returns',3000),('P03','tear_at',1000),('P03','hand_pause_at',9000),('P08','consequence_enters',4000),('P09','refusal_visible',500)])
def test_partner_release_event_timing(name: Any, event: Any, value: Any) -> None:
    c=make_case(name);events=dict(c['visual_observation'].event_times_ms);events[event]=value
    change_observation(c,'VISUAL',event_times_ms=events);r=review(c)
    assert r.performance_alignment['timing']=='FAIL'
    assert next(f for f in r.findings if f.key.endswith(':timing')).repair_owner=='shot-production'


def test_voice_does_not_cover_partner_for_four_seconds() -> None:
    c=make_case('P03');events=dict(c['voice_observation'].event_times_ms);events['own_voice_end']=7600
    change_observation(c,'VOICE',event_times_ms=events);r=review(c)
    assert r.performance_alignment['timing']=='FAIL'
    assert next(f for f in r.findings if f.key.endswith(':timing')).repair_owner=='audio-production'


@pytest.mark.parametrize('behavior',['bitter_smile','hysterical_laugh','skyward_laugh','evil_smirk','instant_tragic_collapse'])
def test_real_joy_not_tragic_villain_or_mad_smile(behavior: Any) -> None:
    c=make_case('P08');change_observation(c,'VISUAL',behaviors=(behavior,))
    assert review(c).performance_alignment['emotional_amplitude']=='FAIL'


@pytest.mark.parametrize('behavior',['crying_from_first_line','funeral_tone','heroic_declamation','tragic_tail_each_sentence','whisper_of_death'])
def test_boat_choice_not_predecided_death_performance(behavior: Any) -> None:
    c=make_case('P09');change_observation(c,'VOICE',behaviors=(behavior,))
    assert review(c).performance_alignment['emotional_amplitude']=='FAIL'


def test_good_native_stays_native_despite_voice_brief() -> None:
    c=make_case('P03');assert c['audio'] is not None
    assert native_audio_disposition(review(c))['disposition']=='KEEP_NATIVE'
    with pytest.raises(ValueError,match='Good native'):native_audio_disposition(review(c),replacement_reason='fundamental_performance_violation')


@pytest.mark.parametrize('issue',['abrupt sound','missing ambience','broken phrase'])
def test_local_issue_never_becomes_full_replacement(issue: Any) -> None:
    c=make_case('P03');r=review(c).model_copy(update={'findings':(FilmFinding(key='local',start=2,end=2.4,domain='SOUND',severity='NOTE',observation=issue,consequence='local audible defect',repair_owner='cinematic-finishing',proposed_repair='local repair preserving surrounding native performance'),)})
    result=native_audio_disposition(r,local_finding_keys=('local',))
    assert result['disposition']=='LOCAL_REPAIR' and result['fullReplacementAllowed'] is False
    with pytest.raises(ValueError):native_audio_disposition(r,local_finding_keys=('local',),replacement_reason='unusable_speech')


def test_full_dubbing_requires_actual_failed_native_dimension() -> None:
    c=make_case('P09');r=review(c)
    r=r.model_copy(update={'native_audio_suitability':{**r.native_audio_suitability,'dialogue':'FAIL'}})
    assert native_audio_disposition(r)['disposition']=='REVIEW_REQUIRED'
    result=native_audio_disposition(r,replacement_reason='dialogue_missing')
    assert result['disposition']=='DUBBING_REQUIRED' and result['needsRealizedPerformance']
    assert result['generationAuthorized'] is False


def test_realized_changed_timing_is_consumed_and_story_change_returns_visual() -> None:
    c=make_case('P03');events=dict(c['visual_observation'].event_times_ms);events['rise_start']=7700
    change_observation(c,'VISUAL',event_times_ms=events)
    r=reconcile_realized_performance(c['dpd'],c['intent'],c['visual'],c['realized'],c['current'])
    assert r['observedEventsMs']['rise_start']==7700 and not r['adopted']
    change_observation(c,'VISUAL',meaning_preserved='FAIL')
    r=reconcile_realized_performance(c['dpd'],c['intent'],c['visual'],c['realized'],c['current'])
    assert r['status']=='VISUAL_REVISION_REQUIRED'


def test_unknown_and_design_evidence_cannot_be_adopted() -> None:
    c=make_case('P03');change_observation(c,'VOICE',external_expression='UNKNOWN');r=review(c)
    assert r.performance_alignment['emotional_amplitude']=='UNKNOWN'
    assert film_review_verdict(r,r.media_hash)['status']=='REVIEW_INCOMPLETE'
    with pytest.raises(ValueError,match='[Dd]esign fixture|DESIGN_FIXTURE'):review_av_performance(dpd=c['dpd'],intent=c['intent'],visual=c['visual'],audio=c['audio'],realized=c['realized'],review=c['review'].model_copy(update={'performance_review_basis':'OBSERVED_MEDIA'}),current=c['current'])


def test_route_isolation_and_live_action_compatibility() -> None:
    cg=make_case('decision');live=make_case('decision','live_action')
    assert cg['dpd']==live['dpd'] and cg['intent']==live['intent'] and cg['audio']==live['audio']
    assert cg['visual']!=live['visual']
    assert 'CG轮廓强化' in live['visual'].body_activity
    assert set(review(live).performance_alignment.values())=={'PASS'}


def test_normal_media_alignment_still_requires_full_film_review() -> None:
    c=make_case('decision')
    for channel in ('VISUAL','VOICE'):change_observation(c,channel,method='NORMAL_AV')
    c['review']=c['review'].model_copy(update={'performance_review_basis':'OBSERVED_MEDIA'})
    r=review(c);assert film_review_verdict(r,r.media_hash)['status']=='REVIEW_INCOMPLETE'
    r=r.model_copy(update={'technical':'PASS','story_rhythm':'PASS','visual_continuity':'PASS','sound':'PASS','persistence_verified':True,'observations':(PlaybackObservation(start=0,end=10,mode='NORMAL_AV',observer='unit test simulated reviewer',evidence_ref='test-only'),)})
    assert film_review_verdict(r,r.media_hash)['status']=='CONTENT_REVIEW_COMPLETE_PENDING_USER_ADOPTION'


def test_local_evidence_without_explicit_strategy_still_cannot_trigger_full_tts() -> None:
    c=make_case('P03');r=review(c).model_copy(update={'findings':(FilmFinding(key='local',start=2,end=2.4,domain='SOUND',severity='MAJOR',observation='one broken phrase',consequence='localized speech gap',repair_owner='audio-production',proposed_repair='repair this phrase'),),'native_audio_suitability':{**c['review'].native_audio_suitability,'dialogue':'FAIL'}})
    assert native_audio_disposition(r)['disposition']=='LOCAL_REPAIR'
    with pytest.raises(ValueError,match='Local audio'):native_audio_disposition(r,replacement_reason='unusable_speech')


def test_good_native_rating_cannot_hide_observed_voice_conflict() -> None:
    c=make_case('P03');change_observation(c,'VOICE',behaviors=('sobbing',))
    assert native_audio_disposition(review(c))['disposition']=='REVIEW_REQUIRED'


def test_missing_other_required_beat_does_not_grant_full_av_pass() -> None:
    c=make_case('P03');c['review']=c['review'].model_copy(update={'performance_required_beats':(*c['review'].performance_required_beats,'unreviewed-next-beat#line')})
    r=review(c)
    assert 'UNKNOWN' in r.performance_alignment.values()
    assert film_review_verdict(r,r.media_hash)['status']=='REVIEW_INCOMPLETE'


def test_reviewing_current_beat_preserves_other_beat_failure() -> None:
    c=make_case('P03');prior='earlier#line';f=FilmFinding(key='AV:'+prior+':emotional_amplitude',start=0,end=1,domain='PERFORMANCE',severity='MAJOR',observation='prior uncontrolled sob',consequence='earlier beat still wrong',repair_owner='audio-production',proposed_repair='VOICE_REVISION_REQUIRED')
    c['review']=c['review'].model_copy(update={'performance_required_beats':(*c['review'].performance_required_beats,prior),'performance_beats':{prior:{k:('FAIL' if k=='emotional_amplitude' else 'PASS') for k in ALIGNMENT_DIMENSIONS}},'findings':(f,)})
    r=review(c);assert r.performance_alignment['emotional_amplitude']=='FAIL' and f in r.findings


def test_unqualified_legacy_adapter_cannot_silently_drop_new_voice_semantics() -> None:
    from drama_plugin.providers.speech.fish_audio import map_audio_performance_to_fish, compile_fish_tts_payload
    c=make_case('P03')
    with pytest.raises(ValueError,match='ADAPTER_QUALIFICATION'):map_audio_performance_to_fish(c['audio'])
    with pytest.raises(ValueError,match='ADAPTER_QUALIFICATION'):compile_fish_tts_payload(exact_text=c['spoken']['text'],reference_id='not-a-real-provider-identity',mode='directed',performance_brief=c['audio'])


def test_actual_video_conditioned_entry_reads_changed_rp_and_preserves_identity() -> None:
    from drama_plugin.audio.video_conditioning import condition_audio_on_video
    from drama_plugin.contracts.media import Media, MediaType
    c=make_case('P03');events=dict(c['visual_observation'].event_times_ms);events['rise_start']=7900
    change_observation(c,'VISUAL',event_times_ms=events);rp=c['realized']
    args=dict(base_request=c['request'],dpd_snapshot=c['dpd'],realized_snapshot=rp,video_media=Media(id=rp.video_media_id,work_id='fixture-work',shot_id=rp.shot_id,media_type=MediaType.VIDEO,source_ref='DESIGN_FIXTURE_ONLY',content_hash=rp.video_content_hash),shot_id=rp.shot_id,shot_scene_id=c['dpd'].effective.scene_id,shot_spoken_content_ids=(c['audio'].spoken_content_id,),canonical_spoken_content=c['spoken'],observed_speaker_key=c['audio'].speaker_key,bound_voice_id=c['audio'].voice_identity_ref,voice_content_hash='a'*64,accepted_realized_fingerprint=rp.fingerprint,director_intent=c['intent'],visual_brief=c['visual'],current_fingerprints=c['current'])
    final=condition_audio_on_video(**args)
    assert final.audio_performance_brief is not None and final.video_conditioned_projection is not None
    assert '7900' in final.audio_performance_brief.pause_strategy
    assert final.exact_text==c['spoken']['text'] and final.voice_profile==c['request'].voice_profile
    assert final.audio_performance_brief.director_performance==c['audio'].director_performance
    assert final.video_conditioned_projection.realized_performance_fingerprint==rp.fingerprint
    change_observation(c,'VISUAL',meaning_preserved='FAIL')
    args.update(realized_snapshot=c['realized'],accepted_realized_fingerprint=c['realized'].fingerprint)
    with pytest.raises(ValueError,match='VISUAL_REVISION_REQUIRED'):condition_audio_on_video(**args)


def test_cinematic_spec_transfers_both_channels_without_second_visual_prompt() -> None:
    from test_cinematic_direction import example
    from drama_plugin.contracts.cinematic import CinematicShotSpec
    from drama_plugin.performance_direction import attach_cinematic_performance
    from drama_plugin.visual.cinematic import execution_brief
    c=make_case('decision','live_action');spec,_,_=example();payload=dump_contract(spec)  # type: ignore[no-untyped-call]
    payload.update(sceneId=c['dpd'].effective.scene_id,shotId=c['visual'].shot_id)
    payload['performance'].update(objective=c['dpd'].effective.objective,interactionTarget=c['dpd'].effective.interaction_target)
    payload['dialogue'][0].update(spokenContentId=c['audio'].spoken_content_id,speakerKey=c['audio'].speaker_key,text=c['spoken']['text'])
    projected=attach_cinematic_performance(CinematicShotSpec.model_validate(payload),dpd=c['dpd'],intent=c['intent'],visual=c['visual'],audio=c['audio'],current=c['current'])
    assert projected.performance.director_performance==c['visual'].director_performance
    assert projected.dialogue[0].voice_performance==c['audio'].director_performance
    prose=execution_brief(projected)
    assert c['config']['hands'] in prose and c['config']['voice'] in prose


def test_partial_native_listening_cannot_authorize_keep() -> None:
    c=make_case('decision')
    for channel in ('VISUAL','VOICE'):change_observation(c,channel,method='NORMAL_AV')
    c['review']=c['review'].model_copy(update={'performance_review_basis':'OBSERVED_MEDIA'})
    r=review(c).model_copy(update={'observations':(PlaybackObservation(start=0,end=2,mode='AUDIO',observer='simulated test reviewer',evidence_ref='test-only'),)})
    assert native_audio_disposition(r)['disposition']=='REVIEW_REQUIRED'


def test_aggregate_pass_cannot_hide_incomplete_beat_dimensions() -> None:
    c=make_case('decision')
    for channel in ('VISUAL','VOICE'):change_observation(c,channel,method='NORMAL_AV')
    c['review']=c['review'].model_copy(update={'performance_review_basis':'OBSERVED_MEDIA'})
    r=review(c).model_copy(update={'technical':'PASS','story_rhythm':'PASS','visual_continuity':'PASS','sound':'PASS','persistence_verified':True,'observations':(PlaybackObservation(start=0,end=10,mode='NORMAL_AV',observer='unit test simulated reviewer',evidence_ref='test-only'),),'performance_beats':{c['review'].performance_required_beats[0]:{'timing':'PASS'}}})
    assert film_review_verdict(r,r.media_hash)['status']=='REVIEW_INCOMPLETE'
