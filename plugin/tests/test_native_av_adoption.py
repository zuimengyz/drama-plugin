"""Adoption precedes optional dubbing; physical success is not artistic review."""
import hashlib
from pathlib import Path
from copy import deepcopy
import importlib.util
import socket
import subprocess
import pytest
from pydantic import ValidationError
from drama_plugin.audio import assemble_av
from drama_plugin.contracts.audio import AvAssemblyManifest
from test_performance_native_mix import sounds


def test_native_manifest_succeeds_without_external_audio_and_reuses_source(sounds):
    video,_,tmp=sounds;digest=hashlib.sha256(video.read_bytes()).hexdigest()
    result=assemble_av(video,manifest=AvAssemblyManifest(source_video_media_id='video-original',timeline=[]),source_video_hash=digest,output=tmp/'unnecessary.mp4')
    assert result['operation']=='REUSE_SOURCE_AV' and result['status']=='READY'
    assert result['path']==result['videoSourcePath']==result['audioSourcePath']==str(video)
    assert not (tmp/'unnecessary.mp4').exists() and not result['createdMedia']
    assert result['audioProcessing']==[] and result['independentArtisticReview']=='NOT_VERIFIED'
    assert hashlib.sha256(video.read_bytes()).hexdigest()==digest


def test_declared_external_audio_remains_explicit_not_automatic(sounds):
    video,speech,tmp=sounds;digest=hashlib.sha256(video.read_bytes()).hexdigest()
    native=AvAssemblyManifest(source_video_media_id='video-original',timeline=[])
    with pytest.raises(ValueError,match='cannot also add'):
        assemble_av(video,manifest=native,source_video_hash=digest,audio_mix=speech)
    with pytest.raises(ValueError,match='hash mismatch'):
        assemble_av(video,manifest=native,source_video_hash='f'*64)
    with pytest.raises(ValidationError):
        AvAssemblyManifest(source_video_media_id='video-original',timeline=[dict(spokenContentId='protected-quote',audioMediaId='undeclared',startMs=0,sourceInMs=0,sourceOutMs=250)])
    explicit=AvAssemblyManifest(source_video_media_id='video-original',audio_mix_media_id='complete-reviewed-mix',timeline=[])
    result=assemble_av(video,manifest=explicit,source_video_hash=digest,audio_mix=speech,audio_mix_hash=hashlib.sha256(speech.read_bytes()).hexdigest(),output=tmp/'external.mp4')
    assert result['operation']=='REPLACE_WITH_COMPLETE_MIX' and result['mux']['sourceVideoImmutable']
    assert (tmp/'external.mp4').exists()


def editor():
    root=Path(__file__).resolve().parents[3]
    path=root/'artifacts/v2-04/evidence/edit_episode.py'
    if not path.exists():pytest.skip('workspace fixture is not present in isolated Plugin checkout')
    spec=importlib.util.spec_from_file_location('actual_v204_editor',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_actual_adopted_files_ignore_legacy_takes_and_never_process_audio(monkeypatch):
    module=editor();real_run=subprocess.run;real_read=Path.read_text;commands=[]
    def guarded(args,*a,**k):
        assert Path(args[0]).name=='ffprobe', 'No generation, ffmpeg mux or processing in adoption'
        commands.append(args);return real_run(args,*a,**k)
    def read(path,*a,**k):
        assert path.name not in {'current-takes.json','dialogue-timeline.json','performance-text.json'},'Old dubbing checklist must not precede adoption'
        return real_read(path,*a,**k)
    def deny(*a,**k):raise AssertionError('No network in adoption preparation')
    monkeypatch.setattr(subprocess,'run',guarded);monkeypatch.setattr(Path,'read_text',read)
    monkeypatch.setattr(socket.socket,'connect',deny);monkeypatch.setattr(socket,'create_connection',deny)
    result=module.prepare(persist=False)
    assert len(result['selectedClips'])==2 and len(result['unselectedClipIds'])==20
    for row in result['selectedClips']:
        expected=(module.A/'visual/video'/f"{row['clipId']}.mp4").resolve()
        assert Path(row['path'])==expected and Path(row['audioSourcePath'])==expected
        assert row['status']=='READY' and row['operation']=='REUSE_SOURCE_AV'
        assert row['additionalDubbingLineIds']==[] and row['audioProcessing']==[]
        assert row['lipSyncReview']=='NOT_VERIFIED' and row['independentArtisticReview']=='NOT_VERIFIED'
    assert result['generationCalls']==result['newMediaFiles']==0 and commands
    assert result['languagePolicy']['performanceLanguage']=='en-US'
    assert result['languagePolicy']['authoringReviewLanguage']=='zh-CN'


def test_actual_rejected_derivative_cannot_replace_explicit_original_even_with_valid_cache(monkeypatch):
    module=editor();selection=deepcopy(module.load_selection());chosen=selection['selectedClips'][0]
    # A current/cached/more-recent TTS does not enter selection. Even a changed
    # path with the original identity is rejected by the physical hash check.
    chosen['sourcePath']='artifacts/v2-04r/final/C07-native-mix.mp4'
    monkeypatch.setattr(module,'load_selection',lambda:selection)
    with pytest.raises(ValueError,match='hash mismatch'):module.prepare(persist=False)


def test_adoption_does_not_silently_apply_to_changed_source_coverage(monkeypatch):
    module=editor();selection=deepcopy(module.load_selection())
    selection['selectedClips'][0]['sourceLineIds'].append('new-key-information')
    monkeypatch.setattr(module,'load_selection',lambda:selection)
    with pytest.raises(ValueError,match='coverage changed'):module.prepare(persist=False)
