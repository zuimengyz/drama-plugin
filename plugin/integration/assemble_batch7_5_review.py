"""Local review only. Existing reconciliation is the sole placement input."""
import hashlib
import json
import math
import subprocess
import wave
from array import array
from pathlib import Path

from drama_plugin.contracts.dialogue_reconciliation import DialogueTimingReconciliation
from run_batch7_5_voice_review import EVIDENCE, REVIEW, digest, write


def pcm(path):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','s16le','-ar','24000','-ac','1','pipe:1'])


def main():
    r=DialogueTimingReconciliation.model_validate_json((EVIDENCE/'new-reconciliation.json').read_text())
    assert r.full_dialogue_coverage=='COMPLETE' and r.physical_feasibility=='FEASIBLE'
    assert r.recommended_placement_status=='PROPOSED'
    compatibility=json.loads((EVIDENCE/'visual-dialogue-compatibility.json').read_text())
    assert compatibility['status'] in ('SUPPORTED','QUESTIONABLE')
    paths=[REVIEW/'02-turn-a-after.wav',EVIDENCE/'turn-b-frozen.wav']
    track=bytearray(round(r.video_duration_ms*24)*2)
    placements=[]
    end_sample=0
    for t,path in zip(r.turns,paths):
        assert digest(path)==t.audio_content_hash
        raw=pcm(path); start=round(t.proposed_start_ms*24);end=start+len(raw)//2
        assert start>=end_sample and end<=len(track)//2
        track[start*2:end*2]=raw
        assert bytes(track[start*2:end*2])==raw
        placements.append({'spokenContentId':t.spoken_content_id,'audioMediaId':t.audio_media_id,
            'hash':digest(path),'startSample':start,'endSample':end,'decodedDurationMs':len(raw)/48,
            'exactPcmHash':hashlib.sha256(raw).hexdigest(),'occurrences':1})
        end_sample=end
    wave_path=REVIEW/'dialogue-aware-review-track.wav'
    with wave.open(str(wave_path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(track)
    video=REVIEW/'04-dialogue-aware-video.mp4'; video_hash=digest(video)
    assert video_hash==r.video_content_hash
    output=REVIEW/'05-dialogue-aware-preview.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-i',str(wave_path),'-map','0:v:0','-map','1:a:0',
                    '-c:v','copy','-c:a','aac','-b:a','128k','-movflags','+faststart',str(output)],check=True)
    assert digest(video)==video_hash
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(output)]))
    assert {s['codec_type'] for s in probe['streams']}=={'video','audio'}
    subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True)
    packets=[]
    for path in (video,output):
        value=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-']).decode().strip()
        packets.append(value)
    assert packets[0]==packets[1]
    samples=array('h');samples.frombytes(track)
    peak=max(abs(v) for v in samples)
    decoded=array('h');decoded.frombytes(pcm(output)); decoded_peak=max(abs(v) for v in decoded)
    assert peak<32767 and decoded_peak<32767
    alias=REVIEW/'dialogue-aware-review-preview.mp4'
    if alias.exists(): assert digest(alias)==digest(output)
    else: alias.hardlink_to(output)
    write(EVIDENCE/'complete-preview-qc.json',{'status':'PASS','preview':str(output),'previewHash':digest(output),
        'sourceVideoHash':video_hash,'reconciliationFingerprint':r.fingerprint,'placements':placements,
        'durationMs':round(float(probe['format']['duration'])*1000),'probe':probe,'videoPacketHash':packets[0],
        'videoStreamCopy':'PASS','audioCoverage':'COMPLETE','noDuplicate':'PASS','noTruncation':'PASS',
        'noOverlap':'PASS','peakDbfs':20*math.log10(peak/32768),'decodedAacPeakDbfs':20*math.log10(decoded_peak/32768),
        'clipping':False,'reviewOnly':True,'timingAuthority':'UNACCEPTED_PROPOSAL',
        'lipSync':'NOT_STARTED','finalAv':'NOT_STARTED','productionMediaImport':False,
        'visualDialogueCompatibility':compatibility['status']})
    print(output)


if __name__=='__main__': main()
