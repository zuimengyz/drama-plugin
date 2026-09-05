from copy import deepcopy
import re

import pytest
from pydantic import ValidationError

from drama_plugin.audio.projection import compile_projected_speech_request, fingerprint_audio_projection
from drama_plugin.audio.video_conditioning import condition_audio_on_video
from drama_plugin.contracts import TargetTimingPolicy, SpeechGenerationRequest
from drama_plugin.contracts.audio_projection import PhraseDeliverySpan
from drama_plugin.contracts.base import dump_contract
from drama_plugin.dialogue_timing import derive_visual_execution_timing
from drama_plugin.dialogue_reconciliation import evaluate_target_performance_fit, reconcile_dialogue_timing, validate_dialogue_reconciliation
from drama_plugin.visual.performance import couple_dialogue_visual_performance, compile_video_motion_prompt, build_realized_performance_snapshot
from drama_plugin.providers.speech.fish_audio import compile_fish_tts_payload, compile_fish_rendered_text
from test_dialogue_visual_performance import inputs as visual_inputs
from test_dialogue_reconciliation import dialogue_led_inputs
from test_video_conditioning import conditioning_inputs


def fit_inputs():
    args = dialogue_led_inputs()
    plan=args['plan']; video=args['video']
    audio={m.content['spokenContentId']:m for m in args['audio_candidates']}
    execution=derive_visual_execution_timing(plan=plan,actual_durations_ms={k:m.duration_ms for k,m in audio.items()},target_video_duration_ms=video.duration_ms)
    rps={t.speaker_key:build_realized_performance_snapshot({**dump_contract(args['realized']),'observedSpeakerKey':t.speaker_key}) for t in plan.turns}
    obs={t.spoken_content_id:{'videoContentHash':video.content_hash,'status':'SUPPORTED','fitWindowMs':[0,video.duration_ms],'evidence':'controlled observation: participation remains visible'} for t in plan.turns}
    return dict(plan=plan,video=video,audio_by_spoken_content=audio,realized_by_speaker=rps,execution_timing=execution,phase_observations=obs,review_decisions={}),args


def test_actual_timing_changes_visual_without_plan_mutation():
    args=visual_inputs(); before=deepcopy(args['plan']); keys=[t.spoken_content_id for t in before.turns]
    execution=derive_visual_execution_timing(plan=before,actual_durations_ms=dict(zip(keys,[3898,4107])),target_video_duration_ms=11000)
    assert [(t['startMs'],t['endMs']) for t in execution['turns']]==[(500,4398),(5198,9305)]
    assert execution['postHoldMs']==1695 and args['plan']==before
    coupled=couple_dialogue_visual_performance(**args,execution_timing=execution)
    assert coupled.dialogue_performance_phases[3].relative_timing_range==(5198/11000,9305/11000)
    assert coupled.execution_timing_fingerprint==execution['fingerprint']
    # Rendering must consume actual phases, direction and boundaries, not just hash them.
    prompt=compile_video_motion_prompt(brief=coupled,shot_action='request and answer',camera_design='static',speaker_labels={before.turns[0].speaker_key:'Left',before.turns[1].speaker_key:'Right'})
    assert '47%-85%' in prompt
    assert all(b in prompt for b in coupled.performance_boundaries)
    assert all(p.transition_purpose in prompt for p in coupled.dialogue_performance_phases)


@pytest.mark.parametrize('bad',[{}, {'a':1}])
def test_incomplete_audio_cannot_drive_execution(bad):
    with pytest.raises(ValueError): derive_visual_execution_timing(plan=visual_inputs()['plan'],actual_durations_ms=bad,target_video_duration_ms=11000)


def test_execution_rejects_short_budget_and_tamper():
    args=visual_inputs();durations={t.spoken_content_id:4000 for t in args['plan'].turns}
    with pytest.raises(ValueError,match='TIMING_CONFLICT'):derive_visual_execution_timing(plan=args['plan'],actual_durations_ms=durations,target_video_duration_ms=8500)
    execution=derive_visual_execution_timing(plan=args['plan'],actual_durations_ms=durations,target_video_duration_ms=11000)
    execution['turns'][0]['endMs']+=1
    with pytest.raises(ValueError,match='STALE'):couple_dialogue_visual_performance(**args,execution_timing=execution)


def test_physical_fit_does_not_override_visible_conflict_or_unknown():
    args,_=fit_inputs();a,b=args['plan'].turns
    args['phase_observations'][b.spoken_content_id]['status']='CONFLICTING'
    result=evaluate_target_performance_fit(**args)
    assert result['physicalFit']=='FEASIBLE' and result['visualFit']=='CONFLICTING' and not result['placements']
    args['phase_observations'][b.spoken_content_id]['status']='UNKNOWN'
    assert evaluate_target_performance_fit(**args)['visualFit']=='UNKNOWN'


@pytest.mark.parametrize('change',['wrong_speaker','old_video','old_observation','rejected_audio','wrong_mouth'])
def test_target_scope_and_human_failure_gate(change):
    args,_=fit_inputs();t=args['plan'].turns[0]; rp=args['realized_by_speaker'][t.speaker_key]
    if change=='wrong_speaker':args['realized_by_speaker'][t.speaker_key]=rp.model_copy(update={'observed_speaker_key':'other'})
    if change=='old_video':args['video']=args['video'].model_copy(update={'content_hash':'e'*64})
    if change=='old_observation':args['realized_by_speaker'][t.speaker_key]=rp.model_copy(update={'head_motion':'changed unresigned'})
    if change=='rejected_audio':args['review_decisions'][args['audio_by_spoken_content'][t.spoken_content_id].content_hash]='FAIL'
    if change=='wrong_mouth':
        args['phase_observations'][t.spoken_content_id]['wrongSpeakerMouth']=True
        assert evaluate_target_performance_fit(**args)['visualFit']=='CONFLICTING'; return
    with pytest.raises(ValueError):evaluate_target_performance_fit(**args)


def test_constrained_reconciliation_preserves_reaction_and_cascades():
    fit,args=fit_inputs();a,b=args['plan'].turns
    original=reconcile_dialogue_timing(**args)
    fit['phase_observations'][b.spoken_content_id]['fitWindowMs'][0]=original.turns[1].proposed_start_ms+200
    args['target_fit_inputs']={k:fit[k] for k in ['execution_timing','phase_observations','realized_by_speaker']}
    result=reconcile_dialogue_timing(**args)
    assert result.turns[1].proposed_start_ms==original.turns[1].proposed_start_ms+200
    assert result.proposed_post_hold_ms==original.proposed_post_hold_ms-200
    assert args['audio_candidates'][1].content['sourceVideoMediaId']!=result.video_media_id
    args['target_fit_inputs']['phase_observations'][b.spoken_content_id]['status']='QUESTIONABLE'
    with pytest.raises(ValueError,match='STALE'):validate_dialogue_reconciliation(result,**args)


def phrase_request():
    args=conditioning_inputs();base=args['base_request'];text=base.exact_text
    spans=(PhraseDeliverySpan(start_char=0,end_char=2,delivery='Address the nearby listener directly'),PhraseDeliverySpan(start_char=2,end_char=len(text),delivery='Leave the decision open to the listener'))
    request=compile_projected_speech_request(work_id=base.work_id,dpd_snapshot=args['dpd_snapshot'],spoken_content=args['canonical_spoken_content'],voice_profile=base.voice_profile,voice_identity_ref='voice-1',timing_policy=TargetTimingPolicy(policy='NATURAL'),phrase_delivery_spans=spans)
    request.material_render_parameters={'performanceRendering':'PHRASE_CUES_V1'}
    return request,args


def test_phrase_text_reaches_fish_and_conditioning_preserves_ending():
    request,args=phrase_request();brief=request.audio_performance_brief
    payload=compile_fish_tts_payload(exact_text=request.exact_text,reference_id='fake',mode='directed',speed=1,volume=-2,performance_brief=brief)
    assert re.sub(r'\[[^\]]+\]','',payload['text'])==request.exact_text
    for span in brief.phrase_delivery_spans:assert '['+span.delivery+']' in payload['text']
    assert args['dpd_snapshot'].effective.interaction_target in payload['text']
    assert args['dpd_snapshot'].effective.authority_position in payload['text']
    args['base_request']=request
    final=condition_audio_on_video(**args)
    assert final.audio_performance_brief==brief
    assert final.video_conditioned_projection.base_audio_projection_fingerprint==brief.fingerprint
    assert final.material_render_parameters==request.material_render_parameters
    with pytest.raises(ValueError):compile_fish_rendered_text(canonical_text=request.exact_text,rendered_text='[curious]'+request.exact_text,performance_brief=brief)


@pytest.mark.parametrize('span',[{'startChar':0,'endChar':0,'delivery':'x'},{'startChar':1,'endChar':2,'delivery':'[break]'}, {'startChar':True,'endChar':2,'delivery':'x'}])
def test_phrase_invalid_controls_and_ranges(span):
    with pytest.raises(ValidationError):PhraseDeliverySpan.model_validate(span)


def test_phrase_out_of_range_is_not_hidden_by_valid_hash():
    request,_=phrase_request();b=request.audio_performance_brief
    b=b.model_copy(update={'phrase_delivery_spans':(PhraseDeliverySpan(start_char=0,end_char=999,delivery='direct'),)})
    b=b.model_copy(update={'fingerprint':fingerprint_audio_projection(b)})
    with pytest.raises(ValueError,match='exceeds'):SpeechGenerationRequest.model_validate({**dump_contract(request),'audioPerformanceBrief':dump_contract(b)})


def test_lip_requires_explicit_face_and_preserves_audio_timing():
    from drama_plugin.providers.lip_sync import prepare_speaker_operation, validate_lip_derivative
    fit,_=fit_inputs();t=fit['plan'].turns[0];audio=fit['audio_by_spoken_content'][t.spoken_content_id];video=fit['video']
    args=dict(video=video,audio=audio,speaker_key=t.speaker_key,start_ms=500,end_ms=500+audio.duration_ms,
              capability={},selection={})
    with pytest.raises(ValueError,match='CAPABILITY_BLOCKED'):prepare_speaker_operation(**args)
    args['capability']={'explicitSpeakerSelection':True,'selectionParameter':'faceId','workflowId':'test-only','evidenceRef':'verified-test-schema'}
    args['selection']={'faceId':0,'speakerKey':t.speaker_key,'videoHash':video.content_hash,'identityEvidence':'verified-frame-test'}
    op=prepare_speaker_operation(**args)
    qc={k:'PASS' for k in ['activeSpeakerMouth','nonSpeakerMouthSafety','identityPreservation','eyes','beard','skin','costume','background','camera','temporalContinuity']};qc['observationEvidence']='test-only-comparison'
    call=dict(operation=op,derivative_video_hash='d'*64,source_duration_ms=video.duration_ms,derivative_duration_ms=video.duration_ms,audio_hash=audio.content_hash,qc=qc)
    assert validate_lip_derivative(**call)['newObservationRequired']
    for key in ['nonSpeakerMouthSafety','identityPreservation','beard']:
        with pytest.raises(ValueError,match='QC_FAILED'):validate_lip_derivative(**{**call,'qc':{**qc,key:'FAIL'}})
    with pytest.raises(ValueError):validate_lip_derivative(**{**call,'audio_hash':'e'*64})
    with pytest.raises(ValueError):validate_lip_derivative(**{**call,'derivative_duration_ms':video.duration_ms+1})


def test_fixture_preparation_and_shared_corrective_budget(tmp_path):
    import importlib.util
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/'integration/run_batch7_5r_fix.py'
    spec=importlib.util.spec_from_file_location('coordinated_fixture',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    journal=tmp_path/'calls.json'
    first=module.reserve_video_submission(journal,'first')
    assert first['generation']==0
    with pytest.raises(RuntimeError,match='UNKNOWN'):module.reserve_video_submission(journal,'second','failure')
    entries=module.read(journal);entries[0]['status']='COMPLETED';module.write(journal,entries)
    with pytest.raises(RuntimeError,match='EVIDENCE_REQUIRED'):module.reserve_video_submission(journal,'second')
    second=module.reserve_video_submission(journal,'second','observed late handoff')
    assert second['generation']==1
    entries=module.read(journal);entries[1]['status']='COMPLETED';module.write(journal,entries)
    with pytest.raises(RuntimeError,match='EXHAUSTED'):module.reserve_video_submission(journal,'third','still late')
