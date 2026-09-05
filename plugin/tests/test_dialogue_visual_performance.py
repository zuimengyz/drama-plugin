from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from drama_plugin.contracts import DPDSnapshot, DialogueTimingPlan, VisualPerformanceBrief
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.visual.performance import (
    couple_dialogue_visual_performance, diagnose_dialogue_visual_compatibility,
    compile_video_motion_prompt, fingerprint_visual_projection,
    fingerprint_video_generation_request, project_visual_performance,
)

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    f = json.loads((ROOT / 'tests/fixtures/dialogue-reconciliation-72.json').read_text())
    p = json.loads((ROOT / 'tests/fixtures/dialogue-timing-72.json').read_text())
    plan = DialogueTimingPlan.model_validate(f['sourcePlan'])
    dpds = {k: DPDSnapshot.model_validate(v) for k, v in p['dpdBySpokenContent'].items()}
    briefs = {t.spoken_content_id: project_visual_performance(
        dpd_snapshot=dpds[t.spoken_content_id], shot_id=plan.shot_id, shot_scene_id=plan.scene_id,
        shot_fingerprint=plan.shot_fingerprint, shot_spoken_content_ids=[x.spoken_content_id for x in plan.turns],
        shot_character_keys=[x.speaker_key for x in plan.turns], primary_character_key=t.speaker_key,
        character_identity_key=t.speaker_key, character_visual_identity_fingerprint=str(t.sequence)*64,
        scene_visual_identity_fingerprint='3'*64,
    ) for t in plan.turns}
    spoken = [next(s for s in p['scene']['content']['spokenContent'] if s['id']==t.spoken_content_id) for t in plan.turns]
    return dict(plan=plan, ordered_spoken_content=spoken, dpd_by_spoken_content=dpds, briefs_by_spoken_content=briefs)


def test_complete_ordered_phases_consume_plan_and_preserve_sources():
    args=inputs(); before=deepcopy(args)
    brief=couple_dialogue_visual_performance(**args)
    phases=brief.dialogue_performance_phases
    assert [p.active_speaker for p in phases]==[None,'speaker:wangsili',None,'speaker:geshuhan',None]
    assert phases[1].listener=='speaker:geshuhan' and phases[3].listener=='speaker:wangsili'
    assert phases[2].listener=='speaker:geshuhan'
    assert phases[1].relative_timing_range==(500/10500,5500/10500)
    assert brief.dialogue_timing_plan_fingerprint==args['plan'].fingerprint
    assert args==before
    assert all(s['text'] not in str(dump_contract(brief)) for s in args['ordered_spoken_content'])
    labels={'speaker:wangsili':'left officer','speaker:geshuhan':'right commander'}
    prompt=compile_video_motion_prompt(brief=brief,shot_action='request then refuse',camera_design='locked two-shot',speaker_labels=labels)
    assert prompt.index('left officer speaks TO right commander') < prompt.index('right commander speaks TO left officer')
    assert 'not exact speech timestamps' in prompt and len(prompt)<=2000


@pytest.mark.parametrize('mutation',['order','speaker','text','missing','listener'])
def test_mismatched_or_partial_sources_fail_closed(mutation):
    args=inputs()
    if mutation=='order': args['ordered_spoken_content'].reverse()
    if mutation=='speaker': args['ordered_spoken_content'][0]['speakerKey']='wrong'
    if mutation=='text': args['ordered_spoken_content'][0]['text']+='extra'
    if mutation=='missing': args['briefs_by_spoken_content'].pop(args['plan'].turns[0].spoken_content_id)
    if mutation=='listener': args['dpd_by_spoken_content'][args['plan'].turns[0].spoken_content_id].effective.interaction_target='offscreen'
    with pytest.raises(ValueError): couple_dialogue_visual_performance(**args)


def test_legacy_fingerprint_and_dialogue_request_change():
    args=inputs(); base=next(iter(args['briefs_by_spoken_content'].values()))
    legacy=dump_contract(base,exclude={'fingerprint','dialogue_timing_plan_fingerprint','dialogue_source_fingerprint','dialogue_performance_phases'})
    assert sha256_canonical(legacy)==base.fingerprint
    coupled=couple_dialogue_visual_performance(**args)
    common=dict(source_media_content_hash='a'*64,camera_design_fingerprint='b'*64,motion_prompt='same',target_duration_ms=11000)
    assert fingerprint_video_generation_request(brief=base,**common)!=fingerprint_video_generation_request(brief=coupled,**common)
    bad=coupled.model_copy(update={'dialogue_source_fingerprint':'c'*64})
    with pytest.raises(ValueError,match='STALE'): fingerprint_video_generation_request(brief=bad,**common)
    payload=dump_contract(coupled);payload['dialoguePerformancePhases'].reverse()
    with pytest.raises(ValidationError): VisualPerformanceBrief.model_validate(payload)


def test_compatibility_is_observation_scoped_and_wrong_mouth_fails():
    brief=couple_dialogue_visual_performance(**inputs())
    observations=[dict(order=p.order,activeSpeaker=p.active_speaker,listener=p.listener,
                       activeParticipation='SUPPORTED',listenerBehavior='SUPPORTED',transitionBehavior='SUPPORTED') for p in brief.dialogue_performance_phases]
    def audit(): return diagnose_dialogue_visual_compatibility(brief=brief,observed_phases=observations,video_content_hash='a'*64,observed_video_content_hash='a'*64)
    assert audit()=='SUPPORTED'
    observations[1]['activeParticipation']='QUESTIONABLE'; assert audit()=='QUESTIONABLE'
    observations[1]['activeParticipation']='UNKNOWN'; assert audit()=='UNKNOWN'
    observations[1]['wrongSpeakerMouth']=True; assert audit()=='CONFLICTING'
    assert diagnose_dialogue_visual_compatibility(brief=brief,observed_phases=observations,video_content_hash='b'*64,observed_video_content_hash='a'*64)=='UNKNOWN'
