"""Resumable current-fixture E2E. No work/voice/script edits, no automatic rerolls."""
from __future__ import annotations
import argparse, asyncio, hashlib, json, os, shutil, subprocess
from pathlib import Path
from dotenv import load_dotenv

from drama_plugin.plugin import DramaPlugin
from drama_plugin.contracts import DPDSnapshot, DialogueTimingPlan, RoleDubbingRequest, SpeechGenerationRequest, Media, VisualPerformanceBrief
from drama_plugin.contracts.audio_projection import PhraseDeliverySpan
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.audio.projection import compile_projected_speech_request
from drama_plugin.audio.foundation import audio_input_fingerprint
from drama_plugin.audio.host_media import probe_media
from drama_plugin.audio.intelligibility import analyze_pcm_wav
from drama_plugin.dialogue_timing import derive_visual_execution_timing
from drama_plugin.visual.performance import couple_dialogue_visual_performance, compile_video_motion_prompt, fingerprint_video_generation_request, fingerprint_visual_projection
from drama_plugin.providers.speech.fish_audio import compile_fish_tts_payload, map_audio_performance_to_fish
from drama_plugin.providers.http.media_source import allowed_media_roots

ROOT=Path(__file__).resolve().parents[3]
PLUGIN=ROOT/'drama-plugin/plugin'
OLD=ROOT/'artifacts/batch7-5/evidence'
OUT=ROOT/'artifacts/batch7-5r-fix'
E=OUT/'evidence'; REVIEW=OUT/'review'

def read(path): return json.loads(Path(path).read_text())
def write(path,value): Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def code_hash(): return sha256_canonical({str(p.relative_to(PLUGIN)):digest(p) for p in (PLUGIN/'src').rglob('*.py')})
def tested():
    proof=read(E/'tests.json')
    if proof['status']!='PASS' or proof['sourceHash']!=code_hash():raise RuntimeError('TESTED_SOURCE_REQUIRED_BEFORE_PAID_CALL')

def reserve_video_submission(journal_path, request_fingerprint, failure_evidence=None):
    journal_path=Path(journal_path)
    entries=read(journal_path) if journal_path.exists() else []
    if any(item['status']=='SUBMITTED_OR_UNKNOWN' for item in entries):
        raise RuntimeError('VIDEO_SUBMISSION_UNKNOWN_RECOVER_FIRST')
    if len(entries)>=2:raise RuntimeError('CORRECTIVE_VISUAL_BUDGET_EXHAUSTED')
    if entries and not failure_evidence:raise RuntimeError('CORRECTIVE_FAILURE_EVIDENCE_REQUIRED')
    if any(item['requestFingerprint']==request_fingerprint for item in entries):
        raise RuntimeError('REUSE_EXISTING_VIDEO_OPERATION')
    entries.append({'generation':len(entries),'status':'SUBMITTED_OR_UNKNOWN','requestFingerprint':request_fingerprint,'failureEvidence':failure_evidence})
    write(journal_path,entries)
    return entries[-1]

def audio_request():
    old=SpeechGenerationRequest.model_validate(read(OLD/'turn-a-resolved-request.json'))
    ctx=read(OLD/'current-context.json')
    dpd=DPDSnapshot.model_validate(read(ROOT/'artifacts/resume-7-4b-turn-a/evidence/turn-a-production-dpd.json'))
    spoken=next(s for s in ctx['scene']['content']['spokenContent'] if s['id']==old.spoken_content_id)
    # Fixture-specific execution interpretation of formal DPD; Core has no person or text branches.
    spans=[PhraseDeliverySpan(start_char=0,end_char=6,delivery='Ask the man beside you for a specific small force; a direct private request, not a declaration'),
           PhraseDeliverySpan(start_char=7,end_char=13,delivery='Make the proposed intervention concrete; a connected decisive phrase, without addressing an audience'),
           PhraseDeliverySpan(start_char=14,end_char=19,delivery='Offer the benefit to the listener; finish responsively and leave his decision open')]
    request=compile_projected_speech_request(work_id=old.work_id,dpd_snapshot=dpd,spoken_content=spoken,
        voice_profile=old.voice_profile,voice_identity_ref=old.audio_performance_brief.voice_identity_ref,
        timing_policy=old.target_timing_policy,phrase_delivery_spans=spans,
        non_material_metadata={'shotId':ctx['shot']['id'],'rejectedAudioHashes':['3b3b04ba33b87c8656c95a49f654d44f07e523f6f5e03e73c6ab213038c9dbbe'],
            'intermediateE2eAuthorized':True,'userFinalArtisticAcceptance':'PENDING'})
    request.provider_mapping=old.provider_mapping
    request.material_render_parameters={'performanceRendering':'PHRASE_CUES_V1'}
    request=SpeechGenerationRequest.model_validate(dump_contract(request))
    mapping=map_audio_performance_to_fish(request.audio_performance_brief)
    payload=compile_fish_tts_payload(exact_text=request.exact_text,reference_id=old.provider_mapping.voice_id,
        mode='directed',speed=mapping.speed,volume=mapping.volume,performance_brief=request.audio_performance_brief)
    write(E/'turn-a-request.json',dump_contract(RoleDubbingRequest(speech_request=request)))
    write(E/'turn-a-resolved-request.json',dump_contract(request))
    write(E/'turn-a-projection.json',{'brief':dump_contract(request.audio_performance_brief),'renderedText':payload['text'],
        'inputFingerprint':audio_input_fingerprint(request),'providerRequestFingerprint':sha256_canonical(payload),
        'mapping':dump_contract(mapping),'phrasePropagation':'APPROXIMATED','canonicalUnchanged':True})
    return request

async def audio(live):
    request=audio_request()
    if not live:print('AUDIO_PREPARED; PROVIDER_CALLS=0');return
    tested()
    plugin=DramaPlugin.load(root=PLUGIN,config_path=PLUGIN/'config/drama-service-http.example.yaml')
    try:
        ctx=read(OLD/'current-context.json'); mem=plugin.providers.memory; media=plugin.providers.media; voices=plugin.providers.voice
        work=await mem.get_work(request.work_id);scene=await mem.get_scene(request.scene_id);shot=await mem.get_shot(ctx['shot']['id'])
        for value,old in [(work,ctx['work']),(scene,ctx['scene']),(shot,ctx['shot'])]:
            assert dump_contract(value)==old,'FROZEN_DOMAIN_CHANGED'
        voice=await voices.get_voice(request.audio_performance_brief.voice_identity_ref)
        assert voice.content_hash=='265c94c6c3b019a25fae34ad715ad8f1a33198d71c156397d61ed49cc695ef28'
        await voices.download_voice(voice.id,E/'voice-master.wav');assert digest(E/'voice-master.wav')==voice.content_hash
        b=await media.get_media('media_6f4d16d785b84b52b3062e0666a826b5')
        await media.download_media(b.id,REVIEW/'02-turn-b-final.wav');assert digest(REVIEW/'02-turn-b-final.wav')==b.content_hash
        source=await media.get_media('media_3e48554b57e64b4caabf98e50b4bebab')
        await media.download_media(source.id,E/'source-frame.png');assert digest(E/'source-frame.png')==source.content_hash
        write(E/'source-frame-media.json',dump_contract(source));write(E/'turn-b-frozen.json',dump_contract(b))
        write(E/'current-context.json',{'work':dump_contract(work),'scene':dump_contract(scene),'shot':dump_contract(shot),'voice':dump_contract(voice)})
        fp=audio_input_fingerprint(request)
        existing=await media.list_media(work_id=work.id,media_type='AUDIO',purpose='ROLE_DUBBING_AUDIO',source_ref='role-dubbing:'+fp)
        journal=E/'tts-submission.json'
        if existing:
            assert len(existing)==1
            result=existing[0]
        else:
            if journal.exists():raise RuntimeError('TTS_SUBMISSION_UNKNOWN_RECOVER_DO_NOT_RETRY')
            write(journal,{'status':'SUBMITTED_OR_UNKNOWN','primaryTts':1,'inputFingerprint':fp})
            provider=plugin.providers.role_dubbing
            provider.fish._max_transient_retries=2
            response=await provider.generate_role_dubbing(RoleDubbingRequest(speech_request=request))
            result=await media.get_media(response.audio_media_id)
            write(journal,{'status':'DURABLE','primaryTts':1,'asr':1,'mediaId':result.id})
        await media.download_media(result.id,REVIEW/'01-turn-a-final.wav')
        assert digest(REVIEW/'01-turn-a-final.wav')==result.content_hash
        qc=analyze_pcm_wav(REVIEW/'01-turn-a-final.wav')
        assert not qc['obviousClipping'] and result.content['intelligibilityQc']['status']=='PASS'
        write(E/'turn-a-result.json',{'media':dump_contract(result),'cloudHash':'PASS','qc':qc,
            'voiceSelection':'REUSE_USER_SELECTED_CANDIDATE_1','artisticAcceptance':'PENDING','narratorBias':'UNKNOWN'})
        print(json.dumps({'mediaId':result.id,'durationMs':result.duration_ms,'cloudHash':'PASS','turnBFrozen':True}))
    finally:await plugin.aclose()


def visual():
    a=read(E/'turn-a-result.json')['media']; b=read(E/'turn-b-frozen.json'); inputs=read(OLD/'visual-projection-inputs.json')
    plan=DialogueTimingPlan.model_validate(inputs['dialogueTimingPlan']);context=read(E/'current-context.json')
    execution=derive_visual_execution_timing(plan=plan,actual_durations_ms={a['content']['spokenContentId']:a['durationMs'],b['content']['spokenContentId']:b['durationMs']},target_video_duration_ms=11000)
    briefs={k:VisualPerformanceBrief.model_validate(v) for k,v in inputs['perTurnBriefs'].items()}
    # Compact authored visible execution; stable identities/camera remain independently frozen.
    for k,brief in briefs.items():
        fields={'interaction_orientation':'Face the seated partner across the map',
                'gaze_behavior':'Sustain direct partner gaze while speaking; listener keeps attention',
                'gesture_policy':'Small head/chin changes; hands stay by the map'}
        brief=brief.model_copy(update=fields);brief=brief.model_copy(update={'fingerprint':fingerprint_visual_projection(brief)})
        briefs[k]=brief
    spoken=[next(s for s in context['scene']['content']['spokenContent'] if s['id']==t.spoken_content_id) for t in plan.turns]
    coupled=couple_dialogue_visual_performance(plan=plan,ordered_spoken_content=spoken,dpd_by_spoken_content={k:DPDSnapshot.model_validate(v) for k,v in inputs['productionDpd'].items()},briefs_by_spoken_content=briefs,execution_timing=execution)
    labels={plan.turns[0].speaker_key:'LEFT black cap',plan.turns[1].speaker_key:'RIGHT grey beard'}
    camera='locked medium two-shot across map table'
    prompt=compile_video_motion_prompt(brief=coupled,shot_action='private request for approval, then refusal',camera_design=camera,speaker_labels=labels)
    source=read(E/'source-frame-media.json')
    fp=fingerprint_video_generation_request(brief=coupled,source_media_content_hash=source['contentHash'],camera_design_fingerprint=sha256_canonical(camera),motion_prompt=prompt,target_duration_ms=11000)
    write(E/'execution-timing.json',execution);write(E/'visual-performance-brief.json',dump_contract(coupled))
    write(E/'video-request.json',{'fingerprint':fp,'prompt':prompt,'targetDurationMs':11000,'inputMode':'SINGLE_IMAGE','sourceHash':source['contentHash'],
        'sourcePath':str(E/'source-frame.png'),'executionTimingFingerprint':execution['fingerprint'],'visualBriefFingerprint':coupled.fingerprint,
        'audioEvidence':{a['id']:a['contentHash'],b['id']:b['contentHash']},'strategy':'MONOLITHIC','userArtisticAcceptance':'PENDING'})
    print(prompt);print('REQUEST',fp,'CHARS',len(prompt))

async def import_video(path):
    request=read(E/'video-request.json');p=Path(path);probe=probe_media(p)
    assert probe.duration_ms>0
    plugin=DramaPlugin.load(root=PLUGIN,config_path=PLUGIN/'config/drama-service-http.example.yaml')
    try:
        media=plugin.providers.media;ctx=read(E/'current-context.json');ref='batch7-5r-fix-video:'+request['fingerprint']
        existing=await media.list_media(work_id=ctx['work']['id'],media_type='VIDEO',purpose='SHOT_VIDEO',source_ref=ref)
        if existing:result=existing[0]
        else:
            staging=next(r for r in allowed_media_roots() if str(r).startswith(str(ROOT)))/('batch7-5r-fix-'+digest(p)+'.mp4')
            shutil.copyfile(p,staging)
            result=await media.import_media(work_id=ctx['work']['id'],shot_id=ctx['shot']['id'],media_type='VIDEO',purpose='SHOT_VIDEO',source_ref=ref,source_uri=staging.as_uri(),duration_ms=probe.duration_ms,
                content={'schemaVersion':'dialogue-performance-source-v1','videoRequest':request,'executionTiming':read(E/'execution-timing.json'),
                    'visualPerformanceBrief':read(E/'visual-performance-brief.json'),'sourceProvenance':read(E/'comfy-submission.json'),
                    'reviewStatus':'PENDING','technicalReviewStatus':'PASS','userArtisticAcceptance':'PENDING'})
        got=await media.get_media(result.id);await media.download_media(got.id,REVIEW/'03-dialogue-performance-video.mp4')
        assert got.content_hash==digest(p)==digest(REVIEW/'03-dialogue-performance-video.mp4')
        write(E/'new-video-media.json',dump_contract(got));write(E/'video-cloud-hash.json',{'status':'PASS','mediaId':got.id,'hash':got.content_hash})
        print(json.dumps({'mediaId':got.id,'hash':got.content_hash,'durationMs':got.duration_ms}))
    finally:await plugin.aclose()

if __name__=='__main__':
    load_dotenv(Path.home()/'.config/historical-plugin/drama-plugin.env',override=True)
    os.environ['NO_PROXY']='localhost,127.0.0.1';os.environ['no_proxy']=os.environ['NO_PROXY']
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['audio-prepare','audio-live','visual','import-video']);parser.add_argument('--path');args=parser.parse_args()
    if args.stage.startswith('audio'):asyncio.run(audio(args.stage=='audio-live'))
    elif args.stage=='visual':visual()
    else:asyncio.run(import_video(args.path))
