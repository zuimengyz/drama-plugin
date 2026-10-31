"""Offline native entry and real local render; generated art/model quality not tested."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.sequence import SceneStoryboard, StoryboardPanel, StoryboardFile, SourcePin
from drama_plugin.film.storyboard import project, render_selected, native_sequence
from drama_plugin.hosts.picture_edit import _hash
from drama_plugin.plugin import DramaPlugin
from test_storyboard_animatic import study
from test_asset_sequence import plugin, Author, request_for


def selected(tmp_path):
    seq,boards,pins=study(tmp_path)
    nodes=[]
    for shot,timing in zip(seq.shots,seq.editorial.coverage):
        for index,at in enumerate([0,timing.duration/2] if shot.key=='x' else [0]):
            path=boards[shot.key][0]['path']
            nodes.append(StoryboardPanel(key=shot.key+'-'+str(index),shot_key=shot.key,at=at,
                state='Synthetic contact state',image=StoryboardFile(path=path,content_hash=_hash(Path(path)))))
    return SceneStoryboard(sequence=seq,panels=tuple(nodes),selection_reason='Offline test selection'),pins


def test_single_selection_drives_gallery_and_animatic(tmp_path):
    sel,pins=selected(tmp_path)
    result=DramaPlugin.render_scene_storyboard(sel,tmp_path/'out',current_fingerprints=pins)
    view=json.loads(Path(result['manifest']).read_text())
    assert result['shotCount']==2 and result['panelCount']==3
    assert [r['filmCutBefore'] for r in view['rows']]==[False,False,True]
    assert [r['key'] for r in view['rows']]==[p.key for p in sel.panels]
    assert result['duration']==sum(c.duration for c in sel.sequence.editorial.coverage)
    assert abs(result['animatic']['duration']-result['duration'])<.1
    again=DramaPlugin.render_scene_storyboard(sel,tmp_path/'out',current_fingerprints=pins)
    assert result==again
    original=sel.model_dump_json()
    sel.panels[0].at=1
    with pytest.raises(ValueError,match='NODE_TIME'):
        project(sel,pins)
    assert original!=sel.model_dump_json()


@pytest.mark.parametrize('change',['duplicate','image','source'])
def test_changed_input_does_not_silently_retarget(tmp_path,change):
    sel,pins=selected(tmp_path)
    if change=='duplicate': sel.panels[1].key=sel.panels[0].key
    if change=='image': Path(sel.panels[0].image.path).write_bytes(b'changed')
    if change=='source': pins['s']='f'*64
    with pytest.raises(ValueError): project(sel,pins)


def test_authored_ellipsis_and_old_sequence_remain_valid(tmp_path):
    sel,pins=selected(tmp_path)
    before=sel.sequence.model_dump_json()
    sel.sequence.bridges[0].relation='ELLIPSIS'
    sel.sequence.bridges[0].discontinuity_explanation='Host selects a later return to this room'
    sel.sequence.bridges[0].carry_keys=()
    assert project(sel,pins)['bridges'][0]['relation']=='ELLIPSIS'
    from drama_plugin.contracts.sequence import SequencePackage
    assert 'panels' not in json.loads(SequencePackage.model_validate_json(before).model_dump_json())


@pytest.mark.asyncio
async def test_registered_native_source_selection_reopen_and_image_workflow(tmp_path,monkeypatch):
    p=plugin(tmp_path,monkeypatch,Author())
    request_for(p,'s-1')
    seq=native_sequence(p,'offline-film-sequence','s-1')
    pins={s.key:s.fingerprint for s in seq.source_pins}
    # Reuse the current image compiler fixture, never a real image/model call.
    from test_target_reference_production import reference_frame
    from drama_plugin.visual.frame_request import compile_frame
    item={'subjectId':'A','assetType':'CHARACTER','name':'A','design':{'face':'Distinct approved A'},
          'designRef':{'key':'fixture','kind':'DESIGN','fingerprint':'a'*64}}
    spec=reference_frame(item).model_copy(update={'shot_id':'panel-a'})
    spec.prompt_ir['source_fingerprint']=sha256_canonical(spec.model_dump(mode='json',exclude={'prompt_ir'}))
    compiled=compile_frame(spec)
    path=tmp_path/'compiled.json';path.write_text(json.dumps(compiled))
    selection=SceneStoryboard(sequence=seq,panels=(StoryboardPanel(key='panel-a',shot_key='s-1-shot',at=0,
        state='Fixture current pose',frame=StoryboardFile(path=str(path),content_hash=_hash(path))),),selection_reason='Test native selection')
    result=await p.tools.invoke('storyboard.select',selection=selection,current_fingerprints=pins,
        directory=str(tmp_path/'view'),run_id='offline-film-sequence')
    assert result['animatic'] is None
    ref=SourcePin.model_validate(result['selectionRef'])
    result=await p.tools.invoke('storyboard.design_frame',selection_ref=ref,panel_key='panel-a',frame=spec,directory=str(tmp_path/'design'))
    ref=SourcePin.model_validate(result['selectionRef'])
    value=await p.tools.invoke('storyboard.prepare_frame',selection_ref=ref,panel_key='panel-a',child_id='board-child')
    record=p.reference_production.get('board-child')
    assert record.frame==compiled and record.scope.shot_id=='s-1-shot'
    assert p.runtime.store.load('board-child').workflow_id=='specialized-asset-reference:v1'
    assert p.reference_production.item(record)['assetType']=='STORYBOARD'
    assert await p.reference_production.ensure_design_delivery(record)==record
    assert await p.tools.invoke('storyboard.prepare_frame',selection_ref=ref,panel_key='panel-a',child_id='board-child')==value
    # Native Runtime progresses to a missing formal Work/quote without any submission.
    async def no_formal_work(_): return False
    monkeypatch.setattr(p.reference_production,'formal_scope',no_formal_work)
    run=await p.reference_production.resume('board-child')
    assert run.state=='WAITING_EXTERNAL' and run.cursor==1
    assert p.reference_production.get('board-child').stage is None
    assert p.reference_production.get('board-child').asset_id is None
    from drama_plugin.runtime.contracts import CapabilityInput
    inp=CapabilityInput(run_id='board-child',operation_id='fixture',scope=record.scope)
    assert (await p.reference_production.adopt(inp)).status=='SUCCEEDED'
    assert (await p.reference_production.register(inp)).status=='SUCCEEDED'
    assert p.reference_production.get('board-child').adoption_ref is None
    # Fresh plugin instance discovers exact frozen sidecar without a new selection.
    other=plugin(tmp_path,monkeypatch,Author())
    reopened=render_selected(other,ref,tmp_path/'reopen',animatic=False)
    assert reopened['selectionFingerprint']==result['selectionFingerprint']
    bad=deepcopy(selection);bad.sequence.source_pins[1].fingerprint='b'*64
    from drama_plugin.film.storyboard import retain
    with pytest.raises(ValueError,match='DIRECTION_CHANGED'):
        retain(other,bad,current_fingerprints={s.key:s.fingerprint for s in bad.sequence.source_pins},run_id='offline-film-sequence')


@pytest.mark.asyncio
async def test_storyboard_target_completion_collects_without_asset_adoption(tmp_path,monkeypatch):
    """Full Runtime traversal with synthetic transport/media; zero provider IO."""
    from test_target_reference_production import reference_frame, fake_submission, fake_persistence, quote_and_approve
    from drama_plugin.visual.frame_request import compile_frame
    from drama_plugin.visual.production import Review
    from drama_plugin.film.storyboard import retain
    import subprocess
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY','OFFLINE_TEST_SECRET')
    p=plugin(tmp_path,monkeypatch,Author());request_for(p,'s-1')
    from typing import get_type_hints
    for tool in p.tools.list():
        if tool.code.startswith('storyboard.'):
            assert get_type_hints(tool.handler)  # MCP typed-argument resolution, not only direct invoke.
    seq=native_sequence(p,'offline-film-sequence','s-1');pins={x.key:x.fingerprint for x in seq.source_pins}
    item={'subjectId':'A','assetType':'CHARACTER','name':'A','design':{'face':'Distinct approved A'},
        'designRef':{'key':'fixture','kind':'DESIGN','fingerprint':'a'*64}}
    spec=reference_frame(item).model_copy(update={'shot_id':'panel-complete'})
    spec.prompt_ir['source_fingerprint']=sha256_canonical(spec.model_dump(mode='json',exclude={'prompt_ir'}))
    frame=compile_frame(spec);path=tmp_path/'frame.json';path.write_text(json.dumps(frame))
    selection=SceneStoryboard(sequence=seq,panels=(StoryboardPanel(key='panel-complete',shot_key='s-1-shot',at=0,
        state='Fixture state',frame=StoryboardFile(path=str(path),content_hash=_hash(path))),),selection_reason='Synthetic test')
    ref=retain(p,selection,current_fingerprints=pins,run_id='offline-film-sequence')
    child='storyboard-completion'
    await p.tools.invoke('storyboard.prepare_frame',selection_ref=ref,panel_key='panel-complete',child_id=child)
    calls=[];fake_submission(monkeypatch,calls);fake_persistence(monkeypatch,p)
    import drama_plugin.professional_design.reference_production as module
    submit=module.submit_reserved
    image=tmp_path/'fixture.png'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=green:s=160x90','-frames:v','1',str(image)],check=True)
    async def synthetic(*args):
        result=await submit(*args)
        return {**result,'output_path':str(image),'output_hash':_hash(image),'output_bytes':image.stat().st_size}
    monkeypatch.setattr(module,'submit_reserved',synthetic)
    async def formal(_): return True
    monkeypatch.setattr(p.reference_production,'formal_scope',formal)
    await quote_and_approve(p,child)
    run=await p.reference_production.resume(child)
    assert run.cursor==4 and run.state=='WAITING_EXTERNAL'
    value=p.reference_production.get(child);attempt=value.stage['attempts'][0]
    review=Review(attempt_id=attempt['attempt_id'],output_hash=attempt['output_hash'],reviewer='OFFLINE_FIXTURE',
        evidence='Synthetic protocol only',checks={'IDENTITY':'PASS','SCENE':'PASS','CROP':'PASS'})
    await p.reference_production.review_reference(child,review)
    assert (await p.reference_production.resume(child)).state=='SUCCEEDED'
    assert len(calls)==1 and not await p.providers.asset.list_assets()
    value=p.reference_production.get(child)
    assert value.delivery['purpose']=='STORYBOARD_REFERENCE' and value.adoption_ref is None and value.asset_id is None
    result=await p.tools.invoke('storyboard.collect',selection_ref=ref,panel_key='panel-complete',child_id=child,
        directory=str(tmp_path/'collected'),reason='Select synthetic output only for test preview')
    assert result['animatic'] and result['panelCount']==1
    view=json.loads(Path(result['manifest']).read_text())
    assert view['rows'][0]['productionRef'] and view['rows'][0]['imageHash']==_hash(image)
    again=await p.tools.invoke('storyboard.collect',selection_ref=SourcePin.model_validate(result['selectionRef']),
        panel_key='panel-complete',child_id=child,directory=str(tmp_path/'collected'),reason='Select synthetic output only for test preview')
    assert again==result and len(calls)==1
