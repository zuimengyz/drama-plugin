from pathlib import Path
import json
import subprocess
import pytest
from pydantic import ValidationError
from drama_plugin.contracts.sequence import SequencePackage, FilmReview
from drama_plugin.contracts.dramatic_editorial import PictureEditPlan
from drama_plugin.sequence import sequence_handoff, film_review_verdict
from drama_plugin.hosts.picture_edit import render_picture_edit, _hash
from test_production_design import editorial


def package():
    return dict(revision='r',scope_id='s',source_pins=[dict(key=k,kind='CANON',fingerprint='a'*64) for k in ['s','x','y']],
        objective='Make refusal legible',payoff='Captain rejects escape',aftermath='Crew must stay',
        bibles=[dict(key='console',kind='PROP',source_keys=['s'],invariants={'grip':'fixed handle'},
                    reference_duties={'STRUCTURE':'required before generation'},unresolved=['Reference not made'])],
        geography=[dict(scene_id='s',anchors={'door':'behind captain'},traversable_relations=['console to door'],
                        axis_and_viewpoint='door-console axis',scale_basis='human reach')],
        editorial=editorial(),shots=[dict(key=k,source_shot_id=k,scene_id='s',incoming_state={'lever':state},
            outgoing_state={'lever':'closed'},bible_keys=['console'],storyboard='Readable hand and door',
            performance_change='Signal to choice',camera_reason='Read decision',edit_handles='Hold after grip releases')
            for k,state in [('x','open'),('y','closed')]],
        bridges=[dict(outgoing='x',incoming='y',relation='CONTINUOUS',carry_keys=['lever'],motivation='Action to reaction',
                      motion_bridge='Hand settles',visual_bridge='Console stays left',audio_bridge='One room tone')])


def test_package_source_and_authorization_are_separate():
    p=SequencePackage.model_validate(package());h=sequence_handoff(p,{k:'a'*64 for k in ['s','x','y']})
    assert not h['productionAuthorized'] and not h['designReady'] and h['unresolved']
    with pytest.raises(ValueError):sequence_handoff(p,{'s':'b'*64})
    raw=package();raw['production_permission']='VIDEO'
    with pytest.raises(ValidationError):SequencePackage.model_validate(raw)


@pytest.mark.parametrize('defect',['state','edge','order','bible','geography','ellipsis','source'])
def test_unconnected_production_packages_fail(defect):
    raw=package()
    if defect=='source':raw['source_pins'].pop()
    if defect=='state':raw['shots'][1]['incoming_state']['lever']='open'
    if defect=='edge':raw['bridges']=[]
    if defect=='order':raw['shots'].reverse()
    if defect=='bible':raw['shots'][1]['bible_keys']=['unknown']
    if defect=='geography':raw['geography'][0]['scene_id']='elsewhere'
    if defect=='ellipsis':raw['bridges'][0]['relation']='ELLIPSIS'
    with pytest.raises(ValidationError):SequencePackage.model_validate(raw)


def review():
    return dict(media_hash='a'*64,duration=10,technical='PASS',story_rhythm='PASS',
                visual_continuity='PASS',sound='PASS',persistence_verified=True)


def observation(start,end,mode):
    return dict(start=start,end=end,mode=mode,observer='Test fixture only',evidence_ref='fixture')


@pytest.mark.parametrize('mode',['FRAMES','TECHNICAL','AUDIO','NORMAL_VIDEO'])
def test_sampling_cannot_be_full_av_review(mode):
    raw=review();raw['observations']=[observation(0,10,mode)]
    r=film_review_verdict(FilmReview(**raw),'a'*64)
    assert r['status']=='REVIEW_INCOMPLETE' and r['normalAvCoverageGaps']==[[0,10]]


def test_review_gaps_stale_hash_and_repair_evidence():
    raw=review();raw['observations']=[observation(0,4,'NORMAL_AV'),observation(5,10,'NORMAL_AV')]
    assert film_review_verdict(FilmReview(**raw),'a'*64)['normalAvCoverageGaps']==[[4,5]]
    raw['observations'].append(observation(3,6,'NORMAL_AV'))
    assert film_review_verdict(FilmReview(**raw),'a'*64)['status']=='CONTENT_REVIEW_COMPLETE_PENDING_USER_ADOPTION'
    with pytest.raises(ValueError):film_review_verdict(FilmReview(**raw),'b'*64)
    raw['findings']=[dict(key='jump',start=4,end=5,domain='CONTINUITY',severity='MAJOR',observation='Hand changes grip',
        consequence='Loss of action cause',repair_owner='finishing',proposed_repair='Choose alternate trim')]
    assert film_review_verdict(FilmReview(**raw),'a'*64)['status']=='REPAIR_REQUIRED'
    raw['findings'][0]['resolved']=True
    with pytest.raises(ValidationError):FilmReview(**raw)


@pytest.fixture
def media(tmp_path):
    paths={}
    for key,color in [('red','red'),('blue','blue')]:
        p=tmp_path/(key+'.mp4');subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color={color}:s=160x90:r=24:d=2',
           '-f','lavfi','-i','sine=frequency=440:duration=2:sample_rate=48000','-c:v','libx264','-c:a','aac',str(p)],check=True)
        paths[key]=p
    plan=PictureEditPlan(revision='test',source_canon_fingerprint='a'*64,status='REVIEWED',audio_review='PASS',
        sources=[dict(media_id=k,content_hash=_hash(p),duration=2,performance_review='Synthetic fixture') for k,p in paths.items()],
        picture_edit=[dict(source_media=k,source_in=.25,source_out=1.25,cut_reason='Synthetic edit order',
            audio_carry='Native trim only',pace_function='Color identity changes') for k in paths],
        protected_dialogue_review='Synthetic tones contain no dialogue')
    return plan,paths,tmp_path


def pixel(path,time):
    return subprocess.check_output(['ffmpeg','-v','error','-ss',str(time),'-i',str(path),'-frames:v','1',
        '-vf','scale=1:1','-pix_fmt','rgb24','-f','rawvideo','-'])


def test_actual_edit_trims_order_sound_hashes_and_recovers(media):
    plan,paths,tmp=media;before={k:_hash(p) for k,p in paths.items()}
    result=render_picture_edit(plan,paths,tmp/'edit',current_canon_fingerprint='a'*64);out=Path(result['output'])
    assert abs(result['duration']-2)<.1
    a,b=pixel(out,.5),pixel(out,1.5)
    assert a[0]>a[2]+100 and b[2]>b[0]+100
    streams=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(out)]))['streams']
    assert any(s['codec_type']=='audio' for s in streams)
    assert before=={k:_hash(p) for k,p in paths.items()} and result['fullPlaybackReview']=='UNKNOWN'
    assert result==render_picture_edit(plan,paths,tmp/'edit',current_canon_fingerprint='a'*64)
    out.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='Retained result'):render_picture_edit(plan,paths,tmp/'edit',current_canon_fingerprint='a'*64)


@pytest.mark.parametrize('defect',['unreviewed','canon','source','duration'])
def test_edit_gate_before_output(media,defect):
    plan,paths,tmp=media;canon='a'*64
    if defect=='unreviewed':plan.status='DRAFT'
    if defect=='canon':canon='b'*64
    if defect=='source':paths['red'].write_bytes(b'changed')
    if defect=='duration':plan.sources[0].duration=20
    with pytest.raises(ValueError):render_picture_edit(plan,paths,tmp/'blocked',current_canon_fingerprint=canon)
    assert not (tmp/'blocked').exists()
