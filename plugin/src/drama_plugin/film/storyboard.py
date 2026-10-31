"""Native Film scene storyboard selection and derived views, no production loop.

The Sequence owns order/time/continuity. Compiled Frame originals own reference
uses. Host chooses panels; the same immutable selection drives gallery and animatic.
"""
from __future__ import annotations
import html
import json
from pathlib import Path
from urllib.parse import quote

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.sequence import SceneStoryboard, SequencePackage, SourcePin
from drama_plugin.hosts.picture_edit import _hash
from drama_plugin.hosts.storyboard_animatic import render_storyboard_animatic
from drama_plugin.sequence import sequence_handoff
from drama_plugin.visual.frame_request import FrameSpec, verify_compiled


def read_file(evidence):
    path = Path(evidence.path).expanduser().resolve(strict=True)
    if _hash(path) != evidence.content_hash:
        raise ValueError('STORYBOARD_FILE_CHANGED:' + str(path))
    return path


def compiled_frame(panel):
    if panel.frame is None:
        raise ValueError('STORYBOARD_FRAME_DESIGN_REQUIRED')
    value = json.loads(read_file(panel.frame).read_text())
    verify_compiled(value)
    if value['spec']['shot_id'] != panel.key:
        raise ValueError('STORYBOARD_FRAME_PANEL_MISMATCH')
    # Check the actual selected image bytes, not only a declared asset ID.
    for reference in value['spec']['references']:
        if _hash(Path(reference['local_path'])) != reference['content_hash']:
            raise ValueError('STORYBOARD_REFERENCE_CHANGED')
    return value


def project(selection: SceneStoryboard, current_fingerprints: dict[str, str]):
    selection = SceneStoryboard.model_validate(dump_contract(selection))
    sequence_handoff(selection.sequence, current_fingerprints)
    rows, attachments, offset = [], {}, 0.0
    for shot, timing in zip(selection.sequence.shots, selection.sequence.editorial.coverage):
        nodes = [p for p in selection.panels if p.shot_key == shot.key]
        attachments[shot.key] = []
        for i, panel in enumerate(nodes):
            end = nodes[i+1].at if i+1 < len(nodes) else timing.duration
            frame = compiled_frame(panel) if panel.frame else None
            image = str(read_file(panel.image)) if panel.image else None
            refs = [{k:r[k] for k in ('entity_key','kind','asset_id','media_id','version','content_hash','facts','state')}
                for r in frame['spec']['references']] if frame else []
            rows.append(dict(key=panel.key, shotKey=shot.key, sourceShot=shot.source_shot_id,
                sceneId=shot.scene_id, nodeAt=panel.at, displayIn=offset+panel.at, displayOut=offset+end,
                duration=end-panel.at, filmCutBefore=i == 0 and bool(rows), state=panel.state,
                image=image, imageHash=panel.image.content_hash if panel.image else None,
                frame= dump_contract(panel.frame) if panel.frame else None,
                productionRef=dump_contract(panel.production_ref) if panel.production_ref else None,
                requestFingerprint=sha256_canonical(frame['request']) if frame else None,
                references=refs, notes=list(panel.notes), cameraReason=shot.camera_reason,
                incomingState=shot.incoming_state,outgoingState=shot.outgoing_state))
            if image:
                attachments[shot.key].append(dict(path=image, duration=end-panel.at))
        offset += timing.duration
    return dict(schemaVersion='scene-storyboard-view-v1', selectionFingerprint=sha256_canonical(selection),
        sequenceFingerprint=sha256_canonical(selection.sequence), selectionReason=selection.selection_reason,
        rows=rows, attachments=attachments, duration=offset,
        bridges=[dump_contract(b) for b in selection.sequence.bridges],
        audio='SILENT_PLACEHOLDER', formalAdoption=False, productionAuthorized=False)


def render(selection, directory, *, current_fingerprints, animatic=True):
    view = project(selection,current_fingerprints)
    root = Path(directory).resolve() / view['selectionFingerprint']
    # Never place generated files alongside a retained input.
    inputs = [read_file(f) for p in selection.panels for f in (p.image,p.frame) if f]
    if any(path == root or root in path.parents for path in inputs):
        raise ValueError('STORYBOARD_OUTPUT_OVERLAPS_INPUT')
    root.mkdir(parents=True,exist_ok=True)
    result = None
    if animatic:
        if any(row['image'] is None for row in view['rows']):
            raise ValueError('STORYBOARD_IMAGES_PENDING')
        result = render_storyboard_animatic(selection.sequence,view['attachments'],root/'animatic',
            current_fingerprints=current_fingerprints)
    view['animatic'] = result['render'] if result else None
    # Linked images are exact byte copies; filenames never use untrusted panel IDs.
    pictures=root/'pictures'; pictures.mkdir(exist_ok=True)
    for row in view['rows']:
        if row['image']:
            src=Path(row['image']); name=row['imageHash']+src.suffix.lower()
            target=pictures/name
            if target.exists() and _hash(target)!=row['imageHash']:
                raise ValueError('STORYBOARD_DERIVED_IMAGE_CHANGED')
            if not target.exists(): target.write_bytes(src.read_bytes())
            row['displayImage']='pictures/'+name
    if project(selection,current_fingerprints)['selectionFingerprint'] != view['selectionFingerprint']:
        raise ValueError('STORYBOARD_SELECTION_CHANGED')
    (root/'selection.json').write_text(json.dumps(dump_contract(selection),ensure_ascii=False,indent=2))
    (root/'view.json').write_text(json.dumps(view,ensure_ascii=False,indent=2))
    esc=html.escape
    parts=['<!doctype html><meta charset="utf-8"><title>Scene storyboard</title>',
        '<style>body{background:#181b1e;color:#eee;font:16px/1.6 system-ui;margin:28px}a{color:#9bd3ff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px}article{background:#252b31;padding:16px}img,video{width:100%}pre{white-space:pre-wrap}small{color:#bfc8d1}</style>',
        '<h1>'+esc(selection.sequence.scope_id)+' · 场景分镜</h1>',
        '<p>Host 选定用于预演；正式采纳不变。静态画格与占位静音，不证明连续运动或声音表演。</p>',
        '<p>'+esc(selection.selection_reason)+'</p>',
        '<a href="selection.json">选定原稿</a> · <a href="view.json">时间与引用</a>']
    if result:
        relative=Path(result['render']['output']).relative_to(root).as_posix()
        parts += ['<video controls preload="metadata" src="'+quote(relative)+'"></video>']
    parts += ['<div class="grid">']
    for row in view['rows']:
        parts += ['<article><h2>'+esc(row['key'])+'</h2><small>'+esc(row['shotKey'])+
            f" · {row['displayIn']:g}–{row['displayOut']:g}s · "+('电影切点' if row['filmCutBefore'] else '镜头内节点／首格')+'</small>']
        if row.get('displayImage'): parts += ['<img src="'+row['displayImage']+'">']
        parts += ['<p>'+esc(row['state'])+'</p><p>'+esc(row['cameraReason'])+'</p>',
            '<details><summary>资产版本、用途、状态与来源</summary><pre>'+esc(json.dumps(row,ensure_ascii=False,indent=2))+'</pre></details>',
            '<p>'+esc('；'.join(row['notes']))+'</p></article>']
    parts += ['</div><h2>镜间关系</h2><pre>'+esc(json.dumps(view['bridges'],ensure_ascii=False,indent=2))+'</pre>']
    (root/'index.html').write_text('\n'.join(parts))
    return dict(selectionFingerprint=view['selectionFingerprint'], overview=str(root/'index.html'),
        manifest=str(root/'view.json'), animatic=view['animatic'], panelCount=len(view['rows']),
        shotCount=len(selection.sequence.shots), duration=view['duration'], formalAdoption=False)


def retain(p, selection, *, current_fingerprints, run_id=None):
    selection=SceneStoryboard.model_validate(selection)
    project(selection,current_fingerprints)
    if run_id is not None:
        cp=p.film.store.checkpoint(run_id)
        from drama_plugin.film.contracts import FilmDirection
        direction=p.film.store.author(cp.direction_ref,FilmDirection)
        expected=[s for s in direction.shots if s.scene_id==selection.sequence.scope_id]
        if [s.shot_id for s in expected] != [s.key for s in selection.sequence.shots]:
            raise ValueError('STORYBOARD_NATIVE_SHOT_MISMATCH')
        pin=next((v for v in selection.sequence.source_pins if v.key==cp.direction_ref.artifact_ref),None)
        if pin is None or pin.fingerprint!=sha256_canonical(direction):
            raise ValueError('STORYBOARD_NATIVE_DIRECTION_CHANGED')
    body=dict(schemaVersion='native-film-storyboard-selection-v1',runId=run_id,
        selection=dump_contract(selection),currentFingerprints=current_fingerprints)
    return p.creative_versions.objects.put('scene-storyboard:'+selection.sequence.scope_id,body)


def render_selected(p, ref, directory, *, animatic=True):
    ref=SourcePin.model_validate(ref)
    body=p.creative_versions.objects.read_ref(ref)
    if body.get('schemaVersion')!='native-film-storyboard-selection-v1':
        raise ValueError('STORYBOARD_SELECTION_REQUIRED')
    selection=SceneStoryboard.model_validate(body['selection'])
    # Frozen selected versions are retained, never silently updated to new heads.
    return render(selection,directory,current_fingerprints=body['currentFingerprints'],animatic=animatic)


def native_sequence(p, run_id, scene_id):
    """Read selected Director coverage; no re-authoring or automatic panels."""
    from drama_plugin.film.contracts import FilmDirection, FilmCanon
    cp=p.film.store.checkpoint(run_id)
    direction=p.film.store.author(cp.direction_ref,FilmDirection)
    canon=p.film.store.author(cp.canon_ref,FilmCanon)
    scene=next(s for s in canon.scenes if s.scene_id==scene_id)
    selected=[s for s in direction.shots if s.scene_id==scene_id]
    if not selected: raise ValueError('STORYBOARD_NATIVE_SCENE_MISSING')
    pins=[SourcePin(key=cp.canon_ref.artifact_ref,kind='CANON',fingerprint=sha256_canonical(canon)),
          SourcePin(key=cp.direction_ref.artifact_ref,kind='DIRECTION',fingerprint=sha256_canonical(direction))]
    shots=[]; coverage=[]; beats=[]; bridges=[]
    for index, directed in enumerate(selected):
        s=directed.shot; key=directed.shot_id
        pin=p.creative_versions.objects.put('storyboard-source:'+key,dump_contract(directed));pins.append(pin)
        shots.append(dict(key=key,sourceShotId=pin.key,sceneId=scene_id,
            incomingState={'state':s.entry_state},outgoingState={'state':s.exit_state},
            storyboard=s.coverage,performanceChange=s.performance_direction,cameraReason=s.camera_intent,
            editHandles=s.editing_relation))
        beats.append(dict(key=key,information=s.subject_action,focus=s.camera_intent,change=s.required_transition))
        coverage.append(dict(key=key,beatIds=[key],duration=s.duration_ms/1000,
            durationBasis='DRAMATIC_INFORMATION',durationReason=s.purpose,purpose='SETUP',holdReason=s.editing_relation))
        if index:
            bridges.append(dict(outgoing=selected[index-1].shot_id,incoming=key,relation='CONTINUOUS',
                motivation=s.editing_relation,motionBridge=s.required_transition,visualBridge=s.entry_state,
                audioBridge='Read selected Sound original; no recorded audio implied',carryKeys=[]))
    # FilmDirection.cut does not assert a time jump. Leave semantic judgment to
    # Director; a selected Sequence can explicitly replace any bridge with ellipsis.
    return SequencePackage.model_validate(dict(revision=cp.direction_ref.version.__str__(),scopeId=scene_id,
        sourcePins=[dump_contract(x) for x in pins],objective=selected[0].shot.purpose,
        payoff=selected[-1].shot.required_transition,aftermath=selected[-1].shot.exit_state,
        geography=[dict(sceneId=scene_id,anchors={'scene':scene.scene.scene_text},traversableRelations=[],
            axisAndViewpoint='Read selected camera/blocking originals',scaleBasis='Design not measured')],
        editorial=dict(sceneIds=[scene_id],sourceFingerprint=sha256_canonical(scene),revision='director-selected',
            informationBeats=beats,coverage=coverage,cuts=[],reactionChain=[],
            transitionOmissionReason='See selected bridges',establishingNeed=selected[0].shot.purpose,
            visualContrastRhythm='Read selected Director coverage'),shots=shots,bridges=bridges))


async def prepare_frame(p, selection_ref, panel_key, child_id):
    """One existing Target image workflow; no automatic batch/submission/adoption."""
    from drama_plugin.professional_design.reference_production import ReferenceProductionRecord, WORKFLOW, OWNER, INDEX
    from drama_plugin.runtime.contracts import RunMode
    selection_ref=SourcePin.model_validate(selection_ref)
    body=p.creative_versions.objects.read_ref(selection_ref)
    if body.get('schemaVersion')!='native-film-storyboard-selection-v1' or not body.get('runId'):
        raise ValueError('STORYBOARD_NATIVE_PARENT_REQUIRED')
    selection=SceneStoryboard.model_validate(body['selection'])
    # Revalidate against the frozen selected Native Film version before spending.
    retain(p,selection,current_fingerprints=body['currentFingerprints'],run_id=body['runId'])
    panel=next(x for x in selection.panels if x.key==panel_key)
    frame=compiled_frame(panel)
    parent=p.runtime.store.load(body['runId'])
    packet=dict(schemaVersion='native-film-storyboard-frame-v1',workId=parent.scope.work_id,
        sceneId=selection.sequence.scope_id,shotId=panel.shot_key,panelKey=panel.key,
        selectionRef=dump_contract(selection_ref),frameFingerprint=sha256_canonical(frame))
    preparation=p.creative_versions.objects.put('storyboard-frame:'+panel.key,packet)
    owner=p.reference_production
    async with owner.lock(child_id):
        try: old=owner.get(child_id)
        except KeyError: old=None
        if old:
            if old.preparation_ref!=preparation or old.frame!=frame:
                raise ValueError('STORYBOARD_RUN_ALREADY_BOUND')
            return old
        run=p.runtime.draft_run(work_id=packet['workId'],scene_id=packet['sceneId'],shot_id=packet['shotId'],
            run_id=child_id,mode=RunMode.PRODUCTION,workflow_id=WORKFLOW)
        value=ReferenceProductionRecord.seal(run_id=child_id,scope=run.scope,preparation_ref=preparation,
            requirement_key=panel.key,author_context_ref=selection_ref,frame=frame)
        from drama_plugin.contracts.base import canonical_json
        with p.ledger.transaction(write=True) as db:
            p.ledger._insert_run(db,run)
            p.ledger._put_artifact(db,OWNER,value.artifact_reference(),run.scope,value.fingerprint,value)
            db.execute('INSERT INTO ledger_index VALUES (?,?,?,?,?,?)',
                (INDEX,child_id,run.scope.work_id,run.scope.scene_id,run.scope.shot_id,canonical_json(value.artifact_reference())))
        return value


def production_item(owner, value):
    packet=owner.sequence.objects.read_ref(value.preparation_ref)
    if packet.get('schemaVersion')!='native-film-storyboard-frame-v1': return None
    body=owner.sequence.objects.read_ref(SourcePin.model_validate(packet['selectionRef']))
    selection=SceneStoryboard.model_validate(body['selection'])
    from drama_plugin.film.contracts import FilmDirection
    cp=owner.plugin.film.store.checkpoint(body['runId'])
    direction=owner.plugin.film.store.author(cp.direction_ref,FilmDirection)
    if not any(pin.key==cp.direction_ref.artifact_ref and pin.fingerprint==sha256_canonical(direction)
               for pin in selection.sequence.source_pins):
        raise ValueError('STORYBOARD_NATIVE_DIRECTION_CHANGED')
    if owner.plugin.runtime.store.load(body['runId']).scope.work_id!=value.scope.work_id:
        raise ValueError('STORYBOARD_NATIVE_WORK_CHANGED')
    panel=next(x for x in selection.panels if x.key==packet['panelKey'])
    frame=compiled_frame(panel)
    if ((packet['workId'],packet['sceneId'],packet['shotId']) !=
            (value.scope.work_id,value.scope.scene_id,value.scope.shot_id)
            or value.requirement_key!=panel.key or panel.shot_key!=packet['shotId']
            or sha256_canonical(frame)!=packet['frameFingerprint'] or value.frame!=frame):
        raise ValueError('STORYBOARD_PRODUCTION_SOURCE_CHANGED')
    return dict(referenceRequired=True,assetType='STORYBOARD',designRef=packet['selectionRef'],panelKey=panel.key)


def bind_image(p, selection_ref, panel_key, child_id, directory, reason):
    from drama_plugin.visual import production as still
    selection_ref=SourcePin.model_validate(selection_ref)
    value=p.reference_production.get(child_id)
    item=production_item(p.reference_production,value)
    if not item or item['panelKey']!=panel_key:
        raise ValueError('STORYBOARD_RESULT_SELECTION_MISMATCH')
    original=p.creative_versions.objects.read_ref(SourcePin.model_validate(item['designRef']))
    current=p.creative_versions.objects.read_ref(selection_ref)
    left=SceneStoryboard.model_validate(original['selection'])
    right=SceneStoryboard.model_validate(current['selection'])
    # Other panels may already have collected outcomes from the same batch.
    strip=lambda x: x.model_dump(exclude={'image','production_ref'})
    if (original['runId']!=current['runId'] or left.sequence!=right.sequence
            or [strip(x) for x in left.panels]!=[strip(x) for x in right.panels]):
        raise ValueError('STORYBOARD_RESULT_SELECTION_MISMATCH')
    if not value.receipt or not value.delivery or not value.stage or not still.usable(value.stage['attempts'][0]):
        raise ValueError('STORYBOARD_REVIEWED_IMAGE_REQUIRED')
    output_hash=value.receipt['output_hash']
    if value.delivery.get('contentHash')!=output_hash or value.stage['attempts'][0].get('output_hash')!=output_hash:
        raise ValueError('STORYBOARD_RESULT_HASH_MISMATCH')
    selection_body=p.creative_versions.objects.read_ref(selection_ref)
    selection=SceneStoryboard.model_validate(selection_body['selection'])
    evidence=p.creative_versions.objects.put('storyboard-result:'+panel_key,dump_contract(value))
    from drama_plugin.contracts.sequence import StoryboardFile
    rows=[x.model_copy(update={'image':StoryboardFile(path=value.receipt['output_path'],content_hash=value.receipt['output_hash']),
        'production_ref':evidence}) if x.key==panel_key else x for x in selection.panels]
    selection=selection.model_copy(update={'panels':tuple(rows),'selection_reason':reason})
    ref=retain(p,selection,current_fingerprints=selection_body['currentFingerprints'],run_id=selection_body['runId'])
    return {'selectionRef':dump_contract(ref),**render_selected(p,ref,directory,animatic=all(x.image for x in rows))}


def design_frame(p, selection_ref, panel_key, frame, directory):
    """Compile the current authored Frame with existing visual compiler, no model IO."""
    from drama_plugin.visual.frame_request import FrameSpec, compile_frame
    from drama_plugin.visual.prompt_ir import require_submission_ir
    from drama_plugin.contracts.sequence import StoryboardFile
    selection_ref=SourcePin.model_validate(selection_ref)
    body=p.creative_versions.objects.read_ref(selection_ref)
    selection=SceneStoryboard.model_validate(body['selection'])
    panel=next(x for x in selection.panels if x.key==panel_key)
    frame=FrameSpec.model_validate(frame)
    if frame.shot_id!=panel.key:
        raise ValueError('STORYBOARD_FRAME_PANEL_MISMATCH')
    compiled=compile_frame(frame)
    require_submission_ir(compiled,compiled['request'])
    root=p.creative_versions.objects.root/'storyboard-frames'
    root.mkdir(exist_ok=True)
    path=root/(sha256_canonical(compiled)+'.json')
    if path.exists():
        if json.loads(path.read_text())!=compiled: raise ValueError('STORYBOARD_FRAME_FILE_CHANGED')
    else:
        from drama_plugin.execution.media import atomic_write
        atomic_write(path,json.dumps(compiled,ensure_ascii=False,indent=2).encode())
    evidence=StoryboardFile(path=str(path),content_hash=_hash(path))
    updated=panel.model_copy(update={'frame':evidence,
        'image':panel.image if panel.frame==evidence else None,
        'production_ref':panel.production_ref if panel.frame==evidence else None})
    selection=selection.model_copy(update={'panels':tuple(updated if x.key==panel_key else x for x in selection.panels)})
    ref=retain(p,selection,current_fingerprints=body['currentFingerprints'],run_id=body['runId'])
    return {'selectionRef':dump_contract(ref),**render_selected(p,ref,directory,animatic=all(x.image for x in selection.panels))}


def register_tools(p):
    from drama_plugin.tools.catalog import _domain_tool
    async def source(run_id: str,scene_id: str):
        return dump_contract(native_sequence(p,run_id,scene_id))
    async def select(selection: SceneStoryboard,current_fingerprints: dict[str,str],directory: str,run_id: str | None=None):
        selection=SceneStoryboard.model_validate(selection)
        ref=retain(p,selection,current_fingerprints=current_fingerprints,run_id=run_id)
        return {'selectionRef':dump_contract(ref),**render_selected(p,ref,directory,animatic=all(x.image for x in selection.panels))}
    async def design(selection_ref: SourcePin,panel_key: str,frame: FrameSpec,directory: str):
        return design_frame(p,selection_ref,panel_key,frame,directory)
    async def prepare(selection_ref: SourcePin,panel_key: str,child_id: str):
        return dump_contract(await prepare_frame(p,selection_ref,panel_key,child_id))
    async def collect(selection_ref: SourcePin,panel_key: str,child_id: str,directory: str,reason: str):
        return bind_image(p,selection_ref,panel_key,child_id,directory,reason)
    async def render_again(selection_ref: SourcePin,directory: str):
        return render_selected(p,selection_ref,directory)
    for name,handler,required,optional in [
        ('source',source,{'run_id':str,'scene_id':str},{}),
        ('select',select,{'selection':SceneStoryboard,'current_fingerprints':dict[str,str],'directory':str},{'run_id':str|None}),
        ('design_frame',design,{'selection_ref':SourcePin,'panel_key':str,'frame':FrameSpec,'directory':str},{}),
        ('prepare_frame',prepare,{'selection_ref':SourcePin,'panel_key':str,'child_id':str},{}),
        ('collect',collect,{'selection_ref':SourcePin,'panel_key':str,'child_id':str,'directory':str,'reason':str},{}),
        ('render',render_again,{'selection_ref':SourcePin,'directory':str},{})]:
        p.tools.register(_domain_tool('storyboard.'+name,
            'Native Film storyboard selection, derived overview/animatic and existing Target image handoff; no implicit paid submission or asset adoption.',
            handler,dict,required=required,optional=optional))
