"""Real local renderer and existing formal retention, using synthetic sound cues."""
from array import array
from copy import deepcopy
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from drama_plugin.audio.finishing import render, retain, run, digest, video_packets
from drama_plugin.media_delivery import file_hash
from drama_plugin.contracts.media import MediaType
from drama_plugin.providers.mock import MockDramaData, MockMemoryProvider, MockAssetProvider
from test_media_delivery import Store


@pytest.fixture
def material(tmp_path):
    source=tmp_path/'source.mp4'; donor=tmp_path/'donor.wav'
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=160x90:r=24:d=4',
        '-f','lavfi','-i',r"aevalsrc=0.02*sin(2*PI*440*t)+0.1*sin(2*PI*1800*t)*between(t\,2.2\,2.7):s=48000:d=4",
        '-c:v','libx264','-c:a','aac',str(source)])
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','aevalsrc=0.03*sin(2*PI*880*t):s=48000:d=4',str(donor)])
    recipe={'revision':'r1','workId':'w','sourceMediaId':'video','sourceHash':file_hash(source),
      'sceneIds':[],'scope':{'shots':['A','B','C'],'cutSeconds':[1,2]},
      'sources':{'audio':file_hash(donor)},'soundPlan':{'bgm':{'decision':'NO_BGM','purpose':'Source cue carries information'}},
      'protectedDialogue':[[1.1,1.7]],'patches':[{'start':2.1,'end':2.8,'fade':.06,
       'mediaId':'audio','sourceStart':0,'gain':.2,'evidence':'Synthetic isolated 1800 Hz wrong effect; outside dialogue'}],
      'layers':[{'role':'DIEGETIC','mediaId':'audio','sourceStart':0,'start':.5,'duration':3,
        'gain':[[0,0],[.1,1],[.5,1],[.6,.1],[1.2,.1],[1.3,1],[2.8,1],[3,0]]}],
      'review':{'status':'AUDIO_UNKNOWN','audio':'UNKNOWN'}}
    return recipe,{'video':str(source),'audio':str(donor)},tmp_path


def amplitude(path, start, duration, frequency):
    a=array('f');a.frombytes(run(['ffmpeg','-v','error','-ss',str(start),'-t',str(duration),
       '-i',str(path),'-ac','1','-ar','48000','-f','f32le','-']))
    real=sum(x*math.cos(2*math.pi*frequency*i/48000) for i,x in enumerate(a))
    imag=sum(x*math.sin(2*math.pi*frequency*i/48000) for i,x in enumerate(a))
    return 2*math.hypot(real,imag)/len(a)


@pytest.mark.parametrize('role', ['DIEGETIC', 'BGM'])
def test_actual_scene_cue_crosses_cuts_ducks_and_removes_only_local_effect(material, role):
    recipe,paths,tmp=material
    if role == 'BGM':
        recipe['soundPlan']['bgm'].update(decision='SUBTLE',sourceKind='EXISTING_MEDIA',purpose='Carry tension across the cut, retreat for dialogue')
        recipe['layers'][0]['role']='BGM'
        # Isolated synthetic renderer fixture only; never registered as formal BGM.
        from test_creative_assets import bgm_fixture
        from drama_plugin.contracts.base import dump_contract
        from drama_plugin.creative_assets import select_bgm
        asset,media=bgm_fixture(known=True)
        media.content_hash=recipe['sources']['audio']
        media.file_size=Path(paths['audio']).stat().st_size
        asset.content['media']['contentHash']=media.content_hash
        selection=select_bgm(asset,media,decision='SUBTLE',selected_range=(0,3),reason='isolated cross-cut cue')
        recipe['layers'][0].update(bgmAsset=dump_contract(asset),bgmMedia=dump_contract(media),bgmSelection=dump_contract(selection))
    r=render(recipe,paths,tmp/'render');mix=tmp/'render/mix.wav'
    # Cue remains on both sides of the first Shot cut, then ducks for dialogue.
    assert amplitude(mix,.85,.1,880)>.02 and amplitude(mix,1.01,.05,880)>.018
    assert amplitude(mix,1.3,.2,880)<.006
    assert amplitude(mix,1.85,.1,880)>.02 and amplitude(mix,2.02,.05,880)>.02
    assert amplitude(mix,2.35,.2,1800)<.001
    assert amplitude(Path(paths['video']),2.35,.2,1800)>.05
    assert amplitude(mix,1.3,.2,440)>.018
    assert r['videoPacketsIdentical'] and video_packets(Path(paths['video']))==video_packets(Path(r['output']))
    assert file_hash(Path(paths['video']))==recipe['sourceHash']
    assert render(recipe,paths,tmp/'render')==r


@pytest.mark.parametrize('problem',['missing','overlap','range','bgm','changed'])
def test_dependent_missing_or_invalid_recipe_never_falls_back_to_generation(material,problem):
    recipe,paths,tmp=material
    if problem=='missing':paths.pop('audio')
    if problem=='overlap':recipe['patches'][0].update(start=1.2,end=1.5)
    if problem=='range':recipe['layers'][0]['sourceStart']=3
    if problem=='bgm':recipe['layers'][0]['role']='BGM'
    if problem=='changed':Path(paths['audio']).write_bytes(b'changed')
    with pytest.raises(ValueError):render(recipe,paths,tmp/'failed')
    assert not (tmp/'failed/finished.mp4').exists()


@pytest.mark.asyncio
async def test_real_completion_retries_one_revision_preserves_source_and_scoped_bindings(material):
    recipe,paths,tmp=material;data=MockDramaData();store=Store()
    session=SimpleNamespace(media=store,memory=MockMemoryProvider(data),asset=MockAssetProvider(data))
    ids={}
    for key,kind in [('video',MediaType.VIDEO),('audio',MediaType.AUDIO)]:
        m=await store.import_media(work_id=data.work.id,media_type=kind,source_uri=Path(paths[key]).as_uri(),
            content={},source_ref='source:'+key,purpose='SOURCE')
        ids[key]=m.id
    recipe.update(workId=data.work.id,sceneIds=[data.scene.id],sourceMediaId=ids['video'],sources={ids['audio']:recipe['sources']['audio']})
    for x in recipe['patches']+recipe['layers']:x['mediaId']=ids['audio']
    paths={ids[k]:v for k,v in paths.items()}
    r=render(recipe,paths,tmp/'render')
    before=store.imports;store.lost=True
    first=await retain(session,recipe,r,staging=tmp/'stage',cache=tmp/'read1')
    data.work.content['finishingRevisions']['r1']['observations']={'audio':'UNKNOWN','listenedSeconds':0}
    second=await retain(session,recipe,r,staging=tmp/'stage',cache=tmp/'read2')
    assert first['mediaId']==second['mediaId'] and store.imports==before+1
    assert first['binding']['userAdoption']=='PENDING'
    assert first['binding']['contentReview']=='AUDIO_UNKNOWN'
    assert len(data.scene.content['finishingReferences'])==1
    assert data.work.content['finishingRevisions']['r1']['recipe']['sources']==recipe['sources']
    assert data.work.content['finishingRevisions']['r1']['observations']=={'audio':'UNKNOWN','listenedSeconds':0}
    # Original is still independently recoverable after derivative import.
    from drama_plugin.media_delivery import verify_media,MediaIdentity
    original=await store.get_media(ids['video'])
    verified=await verify_media(store,MediaIdentity.from_media(original),tmp/'original-read')
    assert verified['contentHash']==recipe['sourceHash']
    changed=deepcopy(recipe);changed['soundPlan']['bgm']['purpose']='changed'
    with pytest.raises(ValueError,match='sealed'):
        await retain(session,changed,{**r,'recipeHash':digest(changed)},staging=tmp/'stage',cache=tmp/'read3')
