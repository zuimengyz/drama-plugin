"""Current-fixture observation replay, frozen-window sync inputs and final assembly.

Live provider submission stays in the explicit journalled Comfy MCP operations.
"""
from __future__ import annotations
import argparse, asyncio, json, math, os, shutil, subprocess, wave
from array import array
from pathlib import Path
from dotenv import load_dotenv
from run_batch7_5r_fix import ROOT, PLUGIN, OLD, E, REVIEW, read, write, digest
from evaluate_dialogue_reconciliation import load_inputs
from drama_plugin.plugin import DramaPlugin
from drama_plugin.contracts import Media
from drama_plugin.contracts.media import MediaType
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.audio import AvAssemblyManifest, FinalAvFingerprintInput
from drama_plugin.contracts.av_sync import build_av_sync_plan, build_acoustic_mix_plan
from drama_plugin.visual.performance import build_realized_performance_snapshot
from drama_plugin.dialogue_reconciliation import reconcile_dialogue_timing, evaluate_target_performance_fit
from drama_plugin.providers.lip_sync import prepare_speaker_operation, validate_lip_derivative
from drama_plugin.providers.http.media_source import allowed_media_roots

def run(args): subprocess.run(args,check=True)
def pcm(path): return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','s16le','-ar','24000','-ac','1','pipe:1'])
def wav(path,raw):
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(raw)
def probe(path): return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]))

def reconcile():
    video=read(E/'new-video-media.json');obs=read(E/'production-observations.json')
    assert obs['videoHash']==video['contentHash']
    rps={}
    for key,facts in obs['views'].items():
        rp=build_realized_performance_snapshot({**facts,'videoMediaId':video['id'],'videoContentHash':video['contentHash'],
            'shotId':video['shotId'],'videoDurationMs':video['durationMs']})
        write(E/('new-rp-'+key+'.json'),dump_contract(rp));rps[key]=rp
    fixture=read(OLD/'new-reconciliation-inputs.json')
    a=read(E/'turn-a-result.json')['media'];aid=a['content']['spokenContentId']
    fixture.update(video=video,realized=dump_contract(rps['shot']),acceptedRealizedFingerprint=rps['shot'].fingerprint)
    fixture['audioCandidates']=[a,read(E/'turn-b-frozen.json')]
    fixture['currentAudioRequests'][aid]=read(E/'turn-a-resolved-request.json')
    path=E/'new-reconciliation-inputs.json';write(path,fixture);inputs=load_inputs(path)
    phases={k:{**v,'videoContentHash':video['contentHash']} for k,v in obs['phases'].items()}
    fitinputs={'realized_by_speaker':{rp.observed_speaker_key:rp for key,rp in rps.items() if key!='shot'},
        'execution_timing':read(E/'execution-timing.json'),'phase_observations':phases}
    reviews={'3b3b04ba33b87c8656c95a49f654d44f07e523f6f5e03e73c6ab213038c9dbbe':'FAIL',
        '99731a95b7d64c7a5448d5c24b8c7e66bd4a46a70cf896819a8c1e3af2176430':'FAIL'}
    fit=evaluate_target_performance_fit(plan=inputs['plan'],video=inputs['video'],
        audio_by_spoken_content={m.content['spokenContentId']:m for m in inputs['audio_candidates']},review_decisions=reviews,**fitinputs)
    write(E/'target-performance-fit.json',fit)
    result=reconcile_dialogue_timing(**inputs,target_fit_inputs=fitinputs,review_decisions=reviews)
    write(E/'new-reconciliation.json',dump_contract(result))
    assert result.physical_feasibility=='FEASIBLE' and result.artistic_compatibility in ('SUPPORTED','QUESTIONABLE')
    assert result.full_dialogue_coverage=='COMPLETE' and result.recommended_placement_status=='PROPOSED'
    write(E/'execution-timing-review.json',{'authority':'EXPLICIT_PRODUCTION_ANCHOR','userFinalReview':'PENDING',
        'reason':'Latest user authorized this batch to continue intermediate E2E on reconciled windows',
        'reconciliationFingerprint':result.fingerprint,'placements':fit['placements'],'changesAllowedByLipSync':False})
    print(json.dumps({'feasibility':result.physical_feasibility,'visualFit':result.artistic_compatibility,'placements':fit['placements']}))

def assemble(video,output):
    r=read(E/'new-reconciliation.json');track=bytearray(round(r['videoDurationMs']*24)*2);end_sample=0;placements=[]
    for t,path in zip(r['turns'],[REVIEW/'01-turn-a-final.wav',REVIEW/'02-turn-b-final.wav']):
        assert digest(path)==t['audioContentHash'];raw=pcm(path);start=round(t['proposedStartMs']*24);end=start+len(raw)//2
        assert start>=end_sample and end<=len(track)//2
        track[start*2:end*2]=raw;assert bytes(track[start*2:end*2])==raw
        placements.append({'spokenContentId':t['spokenContentId'],'audioMediaId':t['audioMediaId'],'audioHash':digest(path),
            'startSample':start,'endSample':end,'pcmHash':__import__('hashlib').sha256(raw).hexdigest(),'occurrences':1})
        end_sample=end
    wav(E/'complete-dialogue-track.wav',track)
    run(['ffmpeg','-v','error','-y','-i',str(video),'-i',str(E/'complete-dialogue-track.wav'),'-map','0:v:0','-map','1:a:0',
        '-c:v','copy','-c:a','aac','-b:a','128k','-movflags','+faststart',str(output)])
    info=probe(output);assert {s['codec_type'] for s in info['streams']}=={'audio','video'}
    run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'])
    packet=[]
    for p in (video,output):packet.append(subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-']).decode().strip())
    assert packet[0]==packet[1]
    raw_samples=array('h');raw_samples.frombytes(track);decoded=array('h');decoded.frombytes(pcm(output))
    assert max(abs(v) for v in raw_samples)<32767 and max(abs(v) for v in decoded)<32767
    qc={'status':'PASS','path':str(output),'hash':digest(output),'sourceVideoHash':digest(video),'probe':info,
        'placements':placements,'audioCoverage':'COMPLETE','videoPacketHash':packet[0],'noDuplicate':True,'noTruncation':True,
        'noOverlap':True,'noClipping':True,'timingAuthority':'EXPLICIT_PRODUCTION_ANCHOR','userArtisticAcceptance':'PENDING',
        'reconciliationFingerprint':r['fingerprint']}
    write(E/(output.stem+'-qc.json'),qc);return qc

def prepare_lip():
    video=Media.model_validate(read(E/'new-video-media.json'));r=read(E/'new-reconciliation.json')
    assert r['artisticCompatibility'] in ('SUPPORTED','QUESTIONABLE')
    source=REVIEW/'03-dialogue-performance-video.mp4';assert digest(source)==video.content_hash
    info=probe(source);stream=next(s for s in info['streams'] if s['codec_type']=='video')
    assert stream['r_frame_rate']=='24/1';fps=24;count=int(stream['nb_frames'])
    # Split inside the reaction gap. Speech remains complete and at its exact original sample offset.
    split=math.floor(r['turns'][1]['proposedStartMs']*fps/1000)
    bounds=[(0,split),(split,count)]
    audios=[Media.model_validate(read(E/'turn-a-result.json')['media']),Media.model_validate(read(E/'turn-b-frozen.json'))]
    coords=read(E/'speaker-selection.json');ops=[]
    cap={'workflowId':'api_sync_so_lip_sync_video','explicitSpeakerSelection':True,
         'selectionParameter':'coordinates','evidenceRef':str(E/'sync3-capability.json')}
    for i,(turn,audio,(first,last)) in enumerate(zip(r['turns'],audios,bounds)):
        selected=coords[audio.content['speakerKey']]
        operation=prepare_speaker_operation(video=video,audio=audio,speaker_key=audio.content['speakerKey'],start_ms=turn['proposedStartMs'],end_ms=turn['proposedEndMs'],
            capability=cap,selection={'speakerKey':audio.content['speakerKey'],'videoHash':video.content_hash,'identityEvidence':selected['evidence'],'coordinates':selected['coordinates']})
        clip=E/f'lip-input-{i}.mp4';audio_path=E/f'lip-audio-{i}.wav'
        run(['ffmpeg','-v','error','-y','-i',str(source),'-vf',f'trim=start_frame={first}:end_frame={last},setpts=PTS-STARTPTS',
            '-an','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-r','24',str(clip)])
        raw=pcm(REVIEW/('01-turn-a-final.wav' if i==0 else '02-turn-b-final.wav'))
        padding=bytearray((last-first)*1000*2);offset=turn['proposedStartMs']*24-first*1000
        assert offset>=0 and offset*2+len(raw)<=len(padding)
        padding[offset*2:offset*2+len(raw)]=raw;assert bytes(padding[offset*2:offset*2+len(raw)])==raw;wav(audio_path,padding)
        operation.update(segment={'firstFrame':first,'lastFrameExclusive':last,'frameCount':last-first,'fps':fps,
             'durationMs':round((last-first)*1000/fps),'inputVideoHash':digest(clip),'inputAudioHash':digest(audio_path),
             'originalSpeechOffsetSamples':offset,'paddingOnly':True,'originalPcmHash':__import__('hashlib').sha256(raw).hexdigest()},
             inputVideo=str(clip),inputAudio=str(audio_path))
        # Outer execution evidence includes segmentation; keep inner guard fingerprint independently frozen.
        inner={k:v for k,v in operation.items() if k not in ('segment','inputVideo','inputAudio')}
        ops.append({'guard':inner,'segment':operation['segment'],'inputVideo':str(clip),'inputAudio':str(audio_path)})
    write(E/'lip-operations.json',ops);print(json.dumps(ops,ensure_ascii=False))

def finish_lip():
    ops=read(E/'lip-operations.json');qc=read(E/'lip-observation.json');paths=[];lineage=[]
    for i,item in enumerate(ops):
        path=E/f'lip-output-{i}.mp4';info=probe(path);s=next(s for s in info['streams'] if s['codec_type']=='video')
        assert s['r_frame_rate']=='24/1' and int(s['nb_frames'])==item['segment']['frameCount']
        assert digest(Path(item['inputVideo']))==item['segment']['inputVideoHash']
        assert digest(Path(item['inputAudio']))==item['segment']['inputAudioHash']
        evidence=validate_lip_derivative(operation=item['guard'],derivative_video_hash=digest(path),
            source_duration_ms=item['segment']['durationMs'],derivative_duration_ms=round(float(s['duration'])*1000),
            audio_hash=item['guard']['audioHash'],qc=qc['operations'][str(i)])
        lineage.append({**item,'outputHash':digest(path),'derivativeEvidence':evidence});paths.append(path)
    output=E/'lip-synced-source.mp4'
    run(['ffmpeg','-v','error','-y','-i',str(paths[0]),'-i',str(paths[1]),'-filter_complex',
        '[0:v]setpts=PTS-STARTPTS[v0];[1:v]setpts=PTS-STARTPTS[v1];[v0][v1]concat=n=2:v=1:a=0[v]',
        '-map','[v]','-an','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-r','24',str(output)])
    info=probe(output);s=next(s for s in info['streams'] if s['codec_type']=='video')
    assert int(s['nb_frames'])==265 and round(float(s['duration'])*1000)==read(E/'new-video-media.json')['durationMs']
    material={'sourceVideo':read(E/'new-video-media.json')['contentHash'],'derivativeHash':digest(output),'operations':lineage,
        'submissions':read(E/'lip-submission.json'),'postLipObservation':qc,'durationMs':round(float(s['duration'])*1000)}
    write(E/'lip-provenance.json',{**material,'fingerprint':sha256_canonical(material)})
    assemble(output,REVIEW/'05-lip-sync-preview.mp4')

async def import_result(path,purpose,ref,content):
    plugin=DramaPlugin.load(root=PLUGIN,config_path=PLUGIN/'config/drama-service-http.example.yaml')
    try:
        ctx=read(E/'current-context.json');provider=plugin.providers.media
        existing=await provider.list_media(work_id=ctx['work']['id'],media_type='VIDEO',purpose=purpose,source_ref=ref)
        if existing:result=existing[0]
        else:
            staging=next(r for r in allowed_media_roots() if str(r).startswith(str(ROOT)))/('batch7-5r-fix-'+digest(path)+'.mp4')
            shutil.copyfile(path,staging)
            result=await provider.import_media(work_id=ctx['work']['id'],shot_id=ctx['shot']['id'],media_type=MediaType.VIDEO,purpose=purpose,
                source_ref=ref,source_uri=staging.as_uri(),duration_ms=read(E/'new-video-media.json')['durationMs'],content=content)
        result=await provider.get_media(result.id);download=E/(result.id+'.mp4');await provider.download_media(result.id,download)
        assert digest(download)==result.content_hash==digest(path)
        return result
    finally:await plugin.aclose()

async def final():
    lip=read(E/'lip-provenance.json');review={'reviewStatus':'PENDING','userArtisticAcceptance':'PENDING','technicalReviewStatus':'PASS'}
    derivative=await import_result(E/'lip-synced-source.mp4','SHOT_VIDEO','lip-derivative:'+lip['fingerprint'],
        {'schemaVersion':'lip-synced-video-derivative-v1',**review,'lipSyncProvenance':lip})
    write(E/'lip-derivative-media.json',dump_contract(derivative))
    post_lip_rps={}
    for key,facts in read(E/'lip-observation.json')['views'].items():
        snapshot=build_realized_performance_snapshot({**facts,'videoMediaId':derivative.id,'videoContentHash':derivative.content_hash,
            'shotId':derivative.shot_id,'videoDurationMs':derivative.duration_ms})
        post_lip_rps[key]=dump_contract(snapshot);write(E/f'post-lip-rp-{key}.json',post_lip_rps[key])
    qc=assemble(E/'lip-synced-source.mp4',REVIEW/'06-final-av.mp4');r=read(E/'new-reconciliation.json');ctx=read(E/'current-context.json')
    audios=[read(E/'turn-a-result.json')['media'],read(E/'turn-b-frozen.json')]
    manifest=AvAssemblyManifest(source_video_media_id=derivative.id,speech_clip_media_ids=[m['id'] for m in audios],
        timeline=[{'spokenContentId':t['spokenContentId'],'audioMediaId':t['audioMediaId'],'startMs':t['proposedStartMs'],'sourceInMs':0,'sourceOutMs':t['actualDurationMs']} for t in r['turns']])
    sync=[];mix=[]
    for t,a in zip(r['turns'],audios):
        sync.append(dump_contract(build_av_sync_plan(shot_id=ctx['shot']['id'],spoken_content_id=t['spokenContentId'],speaker_key=t['speakerKey'],
            video_media_id=derivative.id,video_content_hash=derivative.content_hash,video_duration_ms=derivative.duration_ms,
            dialogue_media_id=a['id'],dialogue_content_hash=a['contentHash'],dialogue_duration_ms=a['durationMs'],
            timing_authority='EXPLICIT_PRODUCTION_ANCHOR',dialogue_start_ms=t['proposedStartMs'],dialogue_end_ms=t['proposedEndMs'],lip_sync_policy='MOUTH_ONLY_DERIVATIVE',alignment_confidence='MEDIUM')))
        mix.append(dump_contract(build_acoustic_mix_plan(work_id=ctx['work']['id'],scene_id=ctx['scene']['id'],shot_id=ctx['shot']['id'],
            dialogue_media_id=a['id'],dialogue_content_hash=a['contentHash'],dialogue_perspective='CLOSE_CONVERSATIONAL')))
    fingerprint_input=FinalAvFingerprintInput(manifest=manifest,source_video_content_hash=derivative.content_hash,
        audio_content_hashes={m['id']:m['contentHash'] for m in audios},mux_implementation='ffmpeg-copy-video-original-dialogue-pcm',
        mux_version=subprocess.check_output(['ffmpeg','-version']).decode().splitlines()[0],
        mux_settings={'audio':'aac128k','pcmRate':24000,'timing':r['fingerprint'],'avSync':sync,'acousticMix':mix,'lip':lip['fingerprint']})
    fp=sha256_canonical(dump_contract(fingerprint_input))
    content={'schemaVersion':'final-av-attempt-v1',**review,'timingAuthority':'EXPLICIT_PRODUCTION_ANCHOR','userTimingReview':'PENDING',
        'assemblyManifest':dump_contract(manifest),'assemblyFingerprintInput':dump_contract(fingerprint_input),'assemblyFingerprint':fp,
        'fullDialogueCoverage':'COMPLETE','technicalQc':qc,'sourceVideo':read(E/'new-video-media.json'),
        'dialogueTimingPlan':r['sourcePlan'],'executionTiming':read(E/'execution-timing.json'),'visualBrief':read(E/'visual-performance-brief.json'),
        'videoRequest':read(E/'video-request.json'),'realized':{k:read(E/f'new-rp-{k}.json') for k in ('shot','a','b')},
        'reconciliation':r,'currentAudioRequests':read(E/'new-reconciliation-inputs.json')['currentAudioRequests'],
        'productionDpd':read(E/'new-reconciliation-inputs.json')['audioDpdBySpokenContent'],'audioMedia':audios,
        'lipSyncProvenance':lip,'lipDerivativeMediaId':derivative.id,'postLipRealized':post_lip_rps,
        'ambience':'NOT_AVAILABLE','sfx':'NOT_AVAILABLE','music':'NONE'}
    write(E/'final-lineage.json',content)
    result=await import_result(REVIEW/'06-final-av.mp4','FINAL_AV','final-av-attempt:'+fp+':batch7-5r-fix',content)
    write(E/'final-media.json',dump_contract(result));write(E/'final-cloud-hash.json',{'status':'PASS','mediaId':result.id,'hash':result.content_hash})
    print(json.dumps({'mediaId':result.id,'hash':result.content_hash,'cloudHash':'PASS','userArtisticAcceptance':'PENDING'}))

if __name__=='__main__':
    load_dotenv(Path.home()/'.config/historical-plugin/drama-plugin.env',override=True);os.environ['NO_PROXY']='localhost,127.0.0.1';os.environ['no_proxy']=os.environ['NO_PROXY']
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['reconcile','no-lip','prepare-lip','finish-lip','final']);a=p.parse_args()
    if a.stage=='reconcile':reconcile()
    elif a.stage=='no-lip':assemble(REVIEW/'03-dialogue-performance-video.mp4',REVIEW/'04-no-lip-preview.mp4')
    elif a.stage=='prepare-lip':prepare_lip()
    elif a.stage=='finish-lip':finish_lip()
    else:asyncio.run(final())
