"""Compile existing production DPD + canonical turns + unchanged 7.4A plan."""
import json
from pathlib import Path

from drama_plugin.contracts import DPDSnapshot, DialogueTimingPlan
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.visual.performance import (
    couple_dialogue_visual_performance, compile_video_motion_prompt,
    fingerprint_video_generation_request, project_visual_performance,
)
from run_batch7_5_voice_review import ROOT, EVIDENCE, write


def main():
    context=json.loads((EVIDENCE/'current-context.json').read_text())
    plan=DialogueTimingPlan.model_validate_json((ROOT/'artifacts/batch7-4a/evidence/dialogue-timing-plan.json').read_text())
    dpds={
        plan.turns[0].spoken_content_id: DPDSnapshot.model_validate_json((ROOT/'artifacts/resume-7-4b-turn-a/evidence/turn-a-production-dpd.json').read_text()),
        plan.turns[1].spoken_content_id: DPDSnapshot.model_validate_json((ROOT/'artifacts/batch7-3d/evidence/dpd-snapshot.json').read_text()),
    }
    refs=json.loads((EVIDENCE/'visual-reference-lineage.json').read_text())
    assets=json.loads((EVIDENCE/'current-assets.json').read_text())
    frame=json.loads((EVIDENCE/'source-frame-media.json').read_text())
    identities={}
    for speaker,aid,mid in [('speaker:wangsili','asset_0bfe891941184a66bd9e6f6aee0b622c','media_04f98e81cb5a4b9d80779283ab70bfb3'),('speaker:geshuhan','asset_807f5ae3694746ccab81c828ab57e990','media_2a0e7a10b8fc4dc5863731c02e5392ef')]:
        asset=next(a for a in assets if a['id']==aid)
        media=next(m for m in refs if m['id']==mid)
        assert mid in asset['referenceMediaIds'] and asset['content']['reviewStatus']=='PASS'
        identities[speaker]={'assetId':aid,'mediaId':mid,'contentHash':media['contentHash'],'assetContent':asset['content']}
    shot=context['shot']; scene=context['scene']
    scene_fp=sha256_canonical({'sourceFrameHash':frame['contentHash'],'sceneId':scene['id'],'sceneContent':scene['content']})
    briefs={t.spoken_content_id: project_visual_performance(
        dpd_snapshot=dpds[t.spoken_content_id],shot_id=shot['id'],shot_scene_id=scene['id'],
        shot_fingerprint=sha256_canonical(shot),shot_spoken_content_ids=[p.spoken_content_id for p in plan.turns],
        shot_character_keys=list(identities),primary_character_key=t.speaker_key,character_identity_key=t.speaker_key,
        character_visual_identity_fingerprint=sha256_canonical(identities[t.speaker_key]),scene_visual_identity_fingerprint=scene_fp)
        for t in plan.turns}
    spoken=[next(s for s in scene['content']['spokenContent'] if s['id']==t.spoken_content_id) for t in plan.turns]
    brief=couple_dialogue_visual_performance(plan=plan,ordered_spoken_content=spoken,dpd_by_spoken_content=dpds,briefs_by_spoken_content=briefs)
    camera='locked medium two-shot across the map table; preserve the original composition'
    labels={'speaker:wangsili':'Wang Sili, LEFT in black cap','speaker:geshuhan':'Geshu Han, RIGHT with grey beard'}
    prompt=compile_video_motion_prompt(brief=brief,shot_action='private request for authorization, then the commander refuses',camera_design=camera,speaker_labels=labels)
    fp=fingerprint_video_generation_request(brief=brief,source_media_content_hash=frame['contentHash'],camera_design_fingerprint=sha256_canonical(camera),motion_prompt=prompt,target_duration_ms=11000)
    write(EVIDENCE/'visual-performance-brief.json',dump_contract(brief))
    write(EVIDENCE/'visual-projection-inputs.json',{'dialogueTimingPlan':dump_contract(plan),'productionDpd':{k:dump_contract(v) for k,v in dpds.items()},'perTurnBriefs':{k:dump_contract(v) for k,v in briefs.items()},'characterIdentities':identities,'sourceFrame':frame,'speakerLabels':labels,'referenceInputCount':1,'oldVideoUse':'REFERENCE_ONLY'})
    write(EVIDENCE/'video-request.json',{'videoRequestFingerprint':fp,'visualProjectionFingerprint':brief.fingerprint,'dialogueTimingPlanFingerprint':plan.fingerprint,'dialogueSourceFingerprint':brief.dialogue_source_fingerprint,'sourceFrameMediaId':frame['id'],'sourceFrameContentHash':frame['contentHash'],'inputMode':'SINGLE_IMAGE','targetDurationMs':11000,'motionPrompt':prompt,'provider':'Comfy Cloud','template':'api_bfl_flux3_i2v','generateAudio':False,'primaryBudget':1,'safeRetryBudget':2})
    print(prompt)
    print('CHARS',len(prompt),'FINGERPRINT',fp)


if __name__=='__main__': main()
