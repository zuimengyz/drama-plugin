from copy import deepcopy
from pathlib import Path
import shutil
import subprocess
import pytest
from drama_plugin.contracts.base import sha256_canonical, dump_contract
from drama_plugin.contracts.production_language import (
    SubtitlePolicy, ObservedSubtitleTiming, ReviewSubtitleCue, ReviewSubtitleTrack,SubtitleTextBasis,
)
from drama_plugin.production_language import export_review_subtitles, require_subtitle_export

def fixture():
    observations={};offsets={};cues=[]
    for i in range(3):
        source=str(i+1)*64;offsets[source]=i*2+.032
        obs={'receipt':{'sourceMediaHash':source,'sourceStart':0,'sourceEnd':2},
             'observation':{'speechEvents':[{'start':.2,'end':1.2,'description':f'actual speech {i}'}]}}
        ref=f'check-{i}';observations[ref]=obs
        cues.append(ReviewSubtitleCue(cueId=f'cue-{i}',sceneId='scene',dialogueLineId=f'line-{i}',
            sourceTextLanguage='ru',targetLanguage='en',subtitleText=f'Actual speech {i}',
            semanticIntentRef='a'*64,speakerRef='speaker',productionLineHash='b'*64,
            localizationReason='Translated observed audio, canon used only for intent',
            observedTiming=ObservedSubtitleTiming(sourceMediaHash=source,observationRef=ref,
                observationHash=sha256_canonical(obs),transcribedText=f'actual speech {i}',
                sourceStart=.2,sourceEnd=1.2,editOffset=offsets[source])))
    track=ReviewSubtitleTrack(trackId='review-en',workId='work',trackLanguage='en',
        languageProfileHash='c'*64,purpose='PRODUCTION',cues=cues,editMediaHash='d'*64,editDuration=6.1)
    kwargs=dict(policy=SubtitlePolicy(enabled=True,languages=('en',)),expected_edit_hash='d'*64,
        source_offsets=offsets,observations=observations)
    return track,kwargs


def clean_fixture():
    track,kwargs=fixture();lines={};assigned={}
    for q in track.cues:
        text='Approved complete '+q.dialogue_line_id
        lines[q.dialogue_line_id]={'sceneId':q.scene_id,'speaker':q.speaker_ref,
            'hash':q.production_line_hash,'scriptRef':'approved-scene-v2','text':text}
        assigned[q.observed_timing.source_media_hash]=[q.dialogue_line_id]
        q.text_basis=SubtitleTextBasis(kind='SCRIPT',sourceText=text,scriptRef='approved-scene-v2',
            scriptLineHash=q.production_line_hash,scriptRange=(0,len(text)),scriptFragment=text)
        q.subtitle_text='A complete natural sentence.'
        q.observed_timing.uncertainty='Internal recognition doubt; no viewer marker required.'
    kwargs.update(clean_authorization={'workId':'work','policy':'ASR_THEN_APPROVED_SCRIPT_CLEAN',
        'userAuthorized':True,'requestRef':'actual-user-request'},script_lines=lines,assigned_lines=assigned)
    return track,kwargs


def test_clean_script_fallback_uses_exact_assigned_version_without_promoting_audio():
    import json
    track,kwargs=clean_fixture();ref='check-1'
    old=kwargs['observations'][ref];raw=old.pop('observation')
    raw['environmentEvents']=[{'description':'Invalid auxiliary data'}]
    old.update(raw=json.dumps(raw),status='AUDIO_SEMANTIC_RESPONSE_INVALID')
    track.cues[1].observed_timing.observation_hash=sha256_canonical(old)
    text=export_review_subtitles(track,**kwargs)
    assert text.count('A complete natural sentence.')==3
    assert not any(word in text for word in ('待核','unclear','UNVERIFIED','Internal'))
    assert track.review_status=='CANDIDATE' and old['status']=='AUDIO_SEMANTIC_RESPONSE_INVALID'
    assert export_review_subtitles(track,**kwargs)==text


@pytest.mark.parametrize('fault',['old-version','wrong-media-line','wrong-scene','missing-line','skip-range','marker','unauthorized'])
def test_clean_fallback_rejects_wrong_binding_gaps_and_viewer_markers(fault):
    track,kwargs=clean_fixture()
    if fault=='old-version':track.cues[0].text_basis.script_ref='old-scene-v1'
    if fault=='wrong-media-line':kwargs['assigned_lines'][track.cues[0].observed_timing.source_media_hash]=['not-filmed-line']
    if fault=='wrong-scene':kwargs['script_lines']['line-0']['sceneId']='other-scene'
    if fault=='missing-line':track.cues=track.cues[:-1]
    if fault=='skip-range':
        b=track.cues[0].text_basis;b.script_range=(1,b.script_range[1]);b.source_text=b.script_fragment=b.script_fragment[1:]
    if fault=='marker':track.cues[0].subtitle_text='Complete but [UNVERIFIED]'
    if fault=='unauthorized':kwargs['clean_authorization']['userAuthorized']=False
    with pytest.raises(ValueError):export_review_subtitles(track,**kwargs)


def test_sentence_alignment_inside_real_speech_window_has_no_word_precision_claim():
    track,kwargs=clean_fixture();first=track.cues[0];second=first.model_copy(deep=True)
    text=first.text_basis.script_fragment;cut=len(text)//2
    first.text_basis.script_range=(0,cut);first.text_basis.source_text=first.text_basis.script_fragment=text[:cut]
    second.cue_id='second-part';second.text_basis.script_range=(cut,len(text));second.text_basis.source_text=second.text_basis.script_fragment=text[cut:]
    first.observed_timing.source_end=.7;second.observed_timing.source_start=.7
    first.subtitle_text='First sentence.';second.subtitle_text='Second sentence.'
    track.cues=(first,second,*track.cues[1:])
    assert export_review_subtitles(track,**kwargs).count('-->')==4
    second.text_basis.script_range=(0,len(text));second.text_basis.source_text=second.text_basis.script_fragment=text
    with pytest.raises(ValueError,match='DUPLICATED_OR_SKIPPED'):export_review_subtitles(track,**kwargs)


def test_clean_reading_hold_preserves_speech_window_and_stays_inside_source():
    track,kwargs=clean_fixture();q=track.cues[0];q.display_source_end=1.8
    text=export_review_subtitles(track,**kwargs)
    assert '00:00:01,832' in text and q.observed_timing.source_end==1.2
    q.display_source_end=2.5
    with pytest.raises(ValueError,match='DISPLAY_HOLD_OUTSIDE_SOURCE'):export_review_subtitles(track,**kwargs)


def test_total_recognition_failure_uses_scoped_sentence_estimate_without_fake_asr():
    track,kwargs=clean_fixture();q=track.cues[0]
    obs=kwargs['observations']['check-0'];obs['observation']['speechEvents']=[]
    obs.update(status='QWEN_OMNI_REQUEST_FAILED',raw='Invalid model; no transcript')
    q.observed_timing.observation_hash=sha256_canonical(obs)
    q.observed_timing.transcribed_text='NO_RELIABLE_TRANSCRIPT'
    q.timing_basis='SENTENCE_ESTIMATE'
    assert 'A complete natural sentence.' in export_review_subtitles(track,**kwargs)
    assert not obs['observation']['speechEvents'] and obs['status']=='QWEN_OMNI_REQUEST_FAILED'
    q.text_basis.kind='ASR'
    with pytest.raises(ValueError,match='ESTIMATE_REQUIRES_UNVERIFIED_SCRIPT'):export_review_subtitles(track,**kwargs)


def test_script_fragment_preserves_exact_whitespace_for_contiguous_ranges():
    track,kwargs=clean_fixture();q=track.cues[0];line=kwargs['script_lines'][q.dialogue_line_id]
    line['text']+=' '
    q.text_basis.script_range=(0,len(line['text']));q.text_basis.script_fragment=line['text']
    assert q.text_basis.script_fragment.endswith(' ')
    assert export_review_subtitles(track,**kwargs)

def test_review_timing_advances_from_actual_events_and_final_export_stays_closed():
    track,kwargs=fixture()
    srt=export_review_subtitles(track,**kwargs)
    assert all(x in srt for x in ('00:00:00,232','00:00:02,232','00:00:04,232'))
    assert srt.count('Actual speech')==3
    assert srt==export_review_subtitles(track,**kwargs)
    with pytest.raises(ValueError,match='FINAL_SUBTITLE_TIMING'):require_subtitle_export(track)
    wrong=track.model_copy(deep=True);wrong.cues[1].observed_timing.edit_offset=.032
    with pytest.raises(ValueError,match='OFFSET_MISMATCH'):export_review_subtitles(wrong,**kwargs)
    wrong=track.model_copy(deep=True);wrong.cues[0].observed_timing.transcribed_text='script instead of speech'
    with pytest.raises(ValueError,match='ACTUAL_SPEECH_EVENT_REQUIRED'):export_review_subtitles(wrong,**kwargs)

def test_uncertain_raw_speech_remains_visible_and_does_not_promote_final_audio():
    import json
    track,kwargs=fixture();ref='check-1'
    obs=deepcopy(kwargs['observations'][ref]);obs['raw']=json.dumps(obs.pop('observation'));obs['status']='AUDIO_SEMANTIC_RESPONSE_INVALID'
    kwargs['observations'][ref]=obs
    e=track.cues[1].observed_timing;e.observation_hash=sha256_canonical(obs)
    with pytest.raises(ValueError,match='VISIBLE_UNCERTAINTY'):export_review_subtitles(track,**kwargs)
    e.uncertainty='word unclear'
    with pytest.raises(ValueError,match='MUST_BE_VISIBLE'):export_review_subtitles(track,**kwargs)
    track.cues[1].subtitle_text+=' [unclear]'
    assert '[unclear]' in export_review_subtitles(track,**kwargs)
    assert track.review_status=='CANDIDATE'
    changed=deepcopy(kwargs);changed['observations'][ref]['raw']='{}'
    with pytest.raises(ValueError,match='OBSERVATION_BINDING'):export_review_subtitles(track,**changed)

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required')
@pytest.mark.parametrize('clean',[False,True])
def test_review_overlay_preserves_native_audio_and_picture_timing(tmp_path,clean):
    from drama_plugin.audio.finishing import render_subtitle_review, probe
    from drama_plugin.media_delivery import file_hash
    source=tmp_path/'source.mp4';image=tmp_path/'caption.png'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','testsrc2=s=160x90:r=24:d=6.1',
        '-f','lavfi','-i','sine=frequency=440:duration=6.1','-c:v','libx264','-c:a','aac','-y',str(source)],check=True)
    subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=yellow:s=12x12',
        '-frames:v','1','-y',str(image)],check=True)
    track,kwargs=clean_fixture() if clean else fixture();track.edit_media_hash=file_hash(source)
    track.edit_duration=float(probe(source)['format']['duration'])
    inputs=dict(source=source,tracks=[track],policy=kwargs['policy'],expected_hash=track.edit_media_hash,
        source_offsets=kwargs['source_offsets'],observations=kwargs['observations'],
        cue_images=[image]*3,directory=tmp_path/'review')
    if clean:inputs.update({k:kwargs[k] for k in ('clean_authorization','script_lines','assigned_lines')})
    result=render_subtitle_review(**inputs)
    assert result['nativeAudioPacketsIdentical'] and result['pictureTimingPreserved']
    assert result['audioFinalAcceptance']=='UNVERIFIED' and result['generationCalls']==0
    assert result==render_subtitle_review(**inputs)
