from copy import deepcopy
from array import array
import hashlib
import re
import shutil
import subprocess
import wave
import pytest
from pydantic import ValidationError
from drama_plugin.audio.foundation import audio_input_fingerprint, audio_input_material, resolve_performance_text, select_performance_language, text_hash
from drama_plugin.audio.projection import compile_projected_speech_request
from drama_plugin.audio.intelligibility import intelligibility_qc
from drama_plugin.audio.host_media import assemble_reviewed_native_mix, mux_video_and_audio
from drama_plugin.contracts.audio import SpeechGenerationRequest, RoleDubbingQcPolicy, TargetTimingPolicy
from drama_plugin.contracts.audio_projection import PhraseDeliverySpan
from drama_plugin.contracts.base import dump_contract
from drama_plugin.providers.speech.fish_audio import compile_fish_tts_payload
from test_audio_foundation import request as legacy_request
from test_audio_projection import inputs, snapshot, voice


def rendition(source):
    return dict(sourceLineId=source.get('id',source.get('spokenContentId')),speakerKey=source['speakerKey'],sourceTextHash=text_hash(source['text']),performanceLanguage='en-US',performanceText='Wait here.',renditionVersion='reviewed-1',reviewStatus='PASS')


def projected():
    source,cases=inputs();record=rendition(source);profile=voice();profile.creative_profile.language='en-US'
    req=compile_projected_speech_request(work_id='work-fixture',dpd_snapshot=snapshot(cases[1]),spoken_content=source,voice_profile=profile,voice_identity_ref='voice-fixture',timing_policy=TargetTimingPolicy(policy='NATURAL'),performance_rendition=record,phrase_delivery_spans=[PhraseDeliverySpan(start_char=0,end_char=10,delivery='gently concerned')])
    req.material_render_parameters={'performanceRendering':'PHRASE_CUES_V2'}
    return source,record,req


def test_language_selection():
    assert select_performance_language(explicit_language='en-US',scene_language='fr-FR')=='en-US'
    assert select_performance_language(explicit_language='en-US',dubbed_language='zh-CN')=='zh-CN'
    assert select_performance_language(scene_language='ar')=='ar'
    with pytest.raises(ValueError):select_performance_language()


def test_source_identity_tts_english_qc_and_instruction_leak():
    source,record,req=projected();before=deepcopy(source)
    assert resolve_performance_text(source,record)['text']==req.exact_text=='Wait here.'
    assert source==before and source['text']!=req.exact_text
    assert req.spoken_content_id==record['sourceLineId'] and req.speaker_key==record['speakerKey']
    assert req.audio_performance_brief.text_fingerprint==text_hash(req.exact_text)
    payload=compile_fish_tts_payload(exact_text=req.exact_text,reference_id='test',mode='directed',speed=1,volume=0,performance_brief=req.audio_performance_brief,compact_phrases=True)
    assert re.sub(r'\[[^\]]+\]','',payload['text'])==req.exact_text
    assert req.audio_performance_brief.control not in payload['text']
    assert intelligibility_qc(canonical_text=req.exact_text,transcript='WAIT HERE!',proper_nouns=[],policy=RoleDubbingQcPolicy()).status.value=='PASS'
    for extra in ['gently concerned Wait here.','Wait here. Address the listener directly.','Wait there.']:
        assert intelligibility_qc(canonical_text=req.exact_text,transcript=extra,proper_nouns=[],policy=RoleDubbingQcPolicy()).status.value=='FAIL'


@pytest.mark.parametrize('key,value',[('sourceTextHash','0'*64),('sourceLineId','other'),('speakerKey','other'),('reviewStatus','PENDING')])
def test_stale_rendition(key,value):
    source,record,_=projected();record[key]=value
    with pytest.raises(ValueError):resolve_performance_text(source,record)


@pytest.mark.parametrize('key,value',[('performanceText','Other words'),('sourceLineId','other'),('speakerKey','other'),('performanceLanguage','de'),('reviewStatus','PENDING')])
def test_wire_conflict(key,value):
    _,_,req=projected();wire=dump_contract(req);wire['performanceRendition'][key]=value
    with pytest.raises(ValidationError):SpeechGenerationRequest.model_validate(wire)


def test_fingerprint_version_language_cache_and_v1():
    old=legacy_request();base=audio_input_fingerprint(old)
    source={'spokenContentId':old.spoken_content_id,'speakerKey':old.speaker_key,'text':old.exact_text}
    wire=dump_contract(old);wire['performanceRendition']=rendition(source);wire['exactText']='Wait here.';wire['voiceProfile']['creativeProfile']['language']='en-US'
    current=audio_input_fingerprint(SpeechGenerationRequest.model_validate(wire));assert current!=base
    assert 'performanceRendition' not in audio_input_material(old)
    for field,value in [('renditionVersion','reviewed-2'),('sourceTextHash','a'*64)]:
        changed=deepcopy(wire);changed['performanceRendition'][field]=value
        assert audio_input_fingerprint(SpeechGenerationRequest.model_validate(changed))!=current
    changed=deepcopy(wire);changed['performanceRendition']['subtitleText']='可选字幕'
    assert audio_input_fingerprint(SpeechGenerationRequest.model_validate(changed))==current
    for render in ('PHRASE_CUES_V1','PHRASE_CUES_V2'):
        changed=deepcopy(wire);changed['materialRenderParameters']={'performanceRendering':render}
        assert audio_input_fingerprint(SpeechGenerationRequest.model_validate(changed))!=current


@pytest.fixture
def sounds(tmp_path):
    if not shutil.which('ffmpeg'):pytest.skip('ffmpeg unavailable')
    def wav(path,frames,value):
        with wave.open(str(path),'wb') as f:
            f.setparams((2,2,48000,0,'NONE','not compressed'));f.writeframes(array('h',[value]*(frames*2)).tobytes())
    native=tmp_path/'native.wav';speech=tmp_path/'speech.wav';video=tmp_path/'source.mp4'
    wav(native,96000,100);wav(speech,12000,1000)
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=s=32x32:r=24:d=2','-i',str(native),'-c:v','libx264','-c:a','aac','-t','2',str(video)],check=True)
    return video,speech,tmp_path


def read_pcm(path):
    with wave.open(str(path),'rb') as f:return f.readframes(f.getnframes())


def placement(path):
    return dict(path=str(path),sourceLineId='line-a',speakerKey='speaker:a',kind='DIALOGUE',performanceFingerprint='active-performance',startMs=1000)


def test_preserve_and_add_only_full_speech_window_and_v1_mux(sounds):
    video,speech,tmp=sounds;before=hashlib.sha256(video.read_bytes()).hexdigest();native=tmp/'preserve.wav';out=tmp/'mixed.wav'
    policy={'mode':'PRESERVE','evidenceRef':'review','nativeLineIds':['native-line']}
    assemble_reviewed_native_mix(video,native,strategy=policy,placements=[])
    rec=assemble_reviewed_native_mix(video,out,strategy={**policy,'mode':'MIX','dialogueRegions':[{'startMs':0,'endMs':900,'kind':'NONLEXICAL'}]},placements=[placement(speech)])
    a,b=read_pcm(native),read_pcm(out);lo,hi=48000*4,60000*4
    assert a[:lo]==b[:lo] and a[hi:]==b[hi:] and a[lo:hi]!=b[lo:hi]
    assert len(a)==len(b) and rec['placements'][0]['measuredDurationMs']==250
    assert before==hashlib.sha256(video.read_bytes()).hexdigest()
    relocated=tmp/'relocated.wav';shutil.copyfile(speech,relocated)
    again=assemble_reviewed_native_mix(video,tmp/'mixed-2.wav',strategy={**policy,'mode':'MIX','dialogueRegions':[{'startMs':0,'endMs':900,'kind':'NONLEXICAL'}]},placements=[placement(relocated)])
    assert again['mixFingerprint']==rec['mixFingerprint']
    result=mux_video_and_audio(video,out,tmp/'final.mp4');assert result['settings'][:4]==['-map','0:v:0','-map','1:a:0']


@pytest.mark.parametrize('case',['native-line','repeat-line','repeat-bed','conflict','overflow','automatic'])
def test_no_double_audio_or_truncation(sounds,case):
    video,speech,tmp=sounds;items=[placement(speech)];policy={'mode':'MIX','evidenceRef':'review'}
    if case=='native-line':policy['nativeLineIds']=['line-a']
    if case=='repeat-line':items*=2
    if case=='repeat-bed':items[0]['path']=str(video)
    if case=='conflict':policy['dialogueRegions']=[{'startMs':900,'endMs':1300,'kind':'UNCERTAIN_DIALOGUE'}]
    if case=='overflow':items[0]['startMs']=1900
    if case=='automatic':policy['mode']='AUTO'
    with pytest.raises(ValueError):assemble_reviewed_native_mix(video,tmp/'bad.wav',strategy=policy,placements=items)


def test_local_change_range_and_finding(sounds):
    video,_,tmp=sounds;policy={'mode':'LOCAL_REPLACE','evidenceRef':'review','reviewStatus':'PENDING','replaceWindows':[{'startMs':500,'endMs':700,'finding':'localized wrong words'}]}
    with pytest.raises(ValueError):assemble_reviewed_native_mix(video,tmp/'bad.wav',strategy=policy,placements=[])
    policy['reviewStatus']='PASS';assemble_reviewed_native_mix(video,tmp/'local.wav',strategy=policy,placements=[])
    assemble_reviewed_native_mix(video,tmp/'base.wav',strategy={'mode':'PRESERVE','evidenceRef':'review'},placements=[])
    a,b=read_pcm(tmp/'base.wav'),read_pcm(tmp/'local.wav');lo,hi=24000*4,33600*4
    assert a[:lo]==b[:lo] and a[hi:]==b[hi:] and not any(b[lo:hi])


def test_conditioning_uses_rendition_preserves_version_and_frozen_source():
    from test_video_conditioning import conditioning_inputs
    from drama_plugin.audio.video_conditioning import condition_audio_on_video
    args=conditioning_inputs();source=args['canonical_spoken_content'];before=deepcopy(source)
    profile=args['base_request'].voice_profile.model_copy(deep=True);profile.creative_profile.language='en-US'
    req=compile_projected_speech_request(work_id=args['base_request'].work_id,dpd_snapshot=args['dpd_snapshot'],spoken_content=source,voice_profile=profile,voice_identity_ref='voice-1',timing_policy=TargetTimingPolicy(policy='NATURAL'),performance_rendition=rendition(source),phrase_delivery_spans=[PhraseDeliverySpan(start_char=0,end_char=10,delivery='gently concerned')])
    req.material_render_parameters={'performanceRendering':'PHRASE_CUES_V2'};args['base_request']=req
    final=condition_audio_on_video(**args)
    assert final.exact_text=='Wait here.' and final.performance_rendition==req.performance_rendition
    assert final.material_render_parameters==req.material_render_parameters and source==before
