"""External Blender handoff and reviewed input assembly; no modeling/render engine.

Creative originals and .blend attachments keep their existing owners. The Host
runs discovered Scenario tools, inspects their output, then explicitly adopts it.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.director import pin
from drama_plugin.generation.audio import package_scope

SCHEMA = 'external-blender-previsualization-v2'
DECISION = 'shot-previsualization-decision-v2'
SOURCE = 'https://github.com/scenario-labs/skills'
SKILLS = ('scenario-blender-expert', 'scenario-blender-blockout', 'scenario-blender-animation')
REQUIRED = {
    SKILLS[0]: ('scripts/bx_review.py', 'scripts/bx_audit.py', 'scripts/bx_gui.py', 'references/bpy-reliability.md', 'references/blender-5.2-deltas.md'),
    SKILLS[1]: ('scripts/bx_blockout.py', 'scripts/bx_kits.py', 'references/contract.md', 'references/audits.md', 'references/handoff.md'),
    SKILLS[2]: ('scripts/bx_anim.py', 'references/procedures.md', 'references/critique.md'),
    'scenario-blender-rigging': ('scripts/bx_rig.py', 'references/procedures.md', 'references/critique.md'),
    'scenario-blender-previs-storyboard': ('scripts/bx_previs.py', 'references/expert-notes.md', 'references/procedures.md'),
}


def _file(path: Path) -> dict:
    path = path.expanduser().resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError('PREVIS_OUTPUT_MISSING:' + str(path))
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)


def _verify_files(value):
    for evidence in value['outputs'].values():
        if _file(Path(evidence['path'])) != evidence:
            raise ValueError('PREVIS_ATTACHMENT_HASH_MISMATCH')


def external_skills(*, animation=False, rigging=False, storyboard=False, roots=None):
    """Discover a complete sibling installation; content hashes are its version.

    Never install or execute an unrelated provider automatically. Missing skills
    return the exact repository paths for the Host's existing skill-installer.
    """
    names = (*SKILLS[:2], *((SKILLS[2],) if animation else ()),
        *(('scenario-blender-rigging',) if rigging else ()),
        *(('scenario-blender-previs-storyboard',) if storyboard else ()))
    if roots is None:
        roots = [Path(v).expanduser() for v in os.environ.get('DRAMA_BLENDER_SKILLS_ROOT', '').split(os.pathsep) if v]
        roots += [Path.home()/'.agents/skills', Path(os.environ.get('CODEX_HOME', Path.home()/'.codex'))/'skills']
    missing = []
    for root in roots:
        root = Path(root).expanduser().resolve()
        absent = [f'{name}/{rel}' for name in names for rel in ('SKILL.md', *REQUIRED[name]) if not (root/name/rel).is_file()]
        if absent:
            missing.append(dict(root=str(root), missing=absent)); continue
        rows = []
        for name in names:
            folder = root/name
            files = {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(folder.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
            rows.append(dict(name=name, path=str(folder), repositoryPath='skills/dcc/blender/'+name,
                version='sha256:'+sha256_canonical(files), files=files, instructions=(folder/'SKILL.md').read_text()))
        return dict(status='AVAILABLE', source=SOURCE, discovery='explicit-root-or-user-sibling-skills', root=str(root), skills=rows,
            version=sha256_canonical([{k:v for k,v in row.items() if k not in ('path','instructions')} for row in rows]),
            execution='LOCAL_BLENDER_ONLY', videoProvider='EXISTING_DRAMA_SEEDANCE')
    return dict(status='DEPENDENCIES_MISSING', source=SOURCE, searched=missing,
        install=dict(skill='skill-installer', repo='scenario-labs/skills', paths=['skills/dcc/blender/'+n for n in names],
            dest=str(Path.home()/'.agents/skills')), requiredForAllShots=False)


def _bindings(p, task):
    from drama_plugin.production.references import ReferenceExecutionBinding
    return [(ref, ReferenceExecutionBinding.model_validate(p.execution_references.resolve(ref))) for ref in task.execution_reference_refs or ()]


def source_fingerprint(p, package_ref, task):
    package = p.production_packages.get(package_ref)
    refs = [ref.model_dump(mode='json',by_alias=True) for ref,b in _bindings(p,task) if b.previsualization_ref is None]
    return sha256_canonical(dict(package=package_ref.model_dump(mode="json",by_alias=True), packageFingerprint=package.fingerprint,
        unit=task.unit.model_dump(mode='json',by_alias=True,exclude={'scope_decision_ref'}) if task.unit else None,
        durationMs=task.profile.requested_duration_ms if task.profile else package.generation_intent.duration_ms,
        aspectRatio=task.profile.aspect_ratio if task.profile else None, references=refs,
        camera=task.camera_direction_ref.model_dump(mode="json") if task.camera_direction_ref else None,
        boundary=task.boundary.model_dump(mode="json") if task.boundary else None,
        continuation=task.continuation.model_dump(mode="json",exclude={"allow_unverified_audio"}) if task.continuation else None))


def discover(p, scope, *, source_fingerprint=None):
    found=[]
    inspections=[]
    for path in (p.creative_versions.objects.root/'objects').glob('*.json'):
        value=json.loads(path.read_text())
        if not isinstance(value,dict) or value.get('scope') != scope:
            continue
        if value.get('recordType')=='LOCAL_PREVIS_INSPECTION':
            inspection_ref=pin('previsualization-inspection:'+sha256_canonical(value),value)
            inspections.append((inspection_ref,value))
            continue
        if value.get('schemaVersion') not in (SCHEMA,'shot-previsualization-v1',DECISION):
            continue
        old=value['schemaVersion']=='shot-previsualization-v1'
        found.append(dict(resultRef=pin('previsualization:'+sha256_canonical(value),value).model_dump(mode='json',by_alias=True),
            schemaVersion=value['schemaVersion'], createdAt=value.get('createdAt'), decision=value.get('decision'),
            historicalOnly=old, matchesCurrentSources=not old and value.get('sourceFingerprint')==source_fingerprint,
            outputs=value.get('outputs',{}), reason=value.get('reason'), use=value.get('use'), supersedes=value.get('supersedes')))
    for result in found:
        result['inspectionArtifacts']=[dict(inspectionRef=ref.model_dump(mode='json',by_alias=True),
            conclusion=value.get('conclusion'),boundaries=value.get('boundaries'),files=value.get('files'))
            for ref,value in inspections if value.get('previsualizationResultRef')==result['resultRef']]
    return sorted(found,key=lambda row:row['createdAt'] or '',reverse=True)


def _put(p,value):
    return p.creative_versions.objects.put('previsualization:'+sha256_canonical(value),value)


def _probe(video):
    binary=shutil.which('ffprobe')
    if not binary: raise ValueError('PREVIS_FFPROBE_REQUIRED')
    result=subprocess.run([binary,'-v','error','-count_frames','-show_streams','-show_format','-of','json',str(video)],capture_output=True,text=True,check=True,timeout=120)
    value=json.loads(result.stdout)
    stream=next(s for s in value['streams'] if s['codec_type']=='video')
    if stream['codec_name']!='h264' or int(stream['nb_read_frames'])<2:
        raise ValueError('PREVIS_CONTINUOUS_H264_REQUIRED')
    return dict(durationMs=round(float(value['format']['duration'])*1000),width=stream['width'],height=stream['height'],
        frames=int(stream['nb_read_frames']),codec=stream['codec_name'])


def validate_adopted(objects, result_ref, binding=None):
    value=objects.read_ref(result_ref)
    if value.get('schemaVersion')!=SCHEMA or value.get('use')!='ADOPTED_VIDEO_INPUT':
        raise ValueError('PREVIS_EXTERNAL_ADOPTION_REQUIRED')
    _verify_files(value)
    if value['inspection'].get('videoSha256')!=value['outputs']['video']['sha256'] or value['inspection'].get('outcome')!='PASS':
        raise ValueError('PREVIS_EXACT_INSPECTION_REQUIRED')
    if binding and (binding.scope.model_dump(mode='json',by_alias=True)!=value['scope']
            or binding.media.content_hash!=value['outputs']['video']['sha256']
            or binding.media.review_ref!='previsualization:'+result_ref.fingerprint):
        raise ValueError('PREVIS_BINDING_MISMATCH')
    return value


def validate_task(p,package_ref,task):
    bindings=[b for _,b in _bindings(p,task) if b.previsualization_ref]
    if not task.previsualization_ref:
        if bindings: raise ValueError('PREVIS_DECISION_REQUIRED')
        return
    decision=p.creative_versions.objects.read_ref(task.previsualization_ref)
    if (decision.get('schemaVersion')!=DECISION or decision['sourceFingerprint']!=source_fingerprint(p,package_ref,task)
            or decision['scope']!=package_scope(p.production_packages.get(package_ref)).model_dump(mode='json',by_alias=True)):
        raise ValueError('PREVIS_SOURCE_CHANGED')
    if decision['decision']=='SKIP':
        if bindings: raise ValueError('PREVIS_SKIP_HAS_VIDEO_BINDING')
    elif len(bindings)!=1 or bindings[0].source().reference().model_dump(mode='json',by_alias=True)!=decision['bindingRef']:
        raise ValueError('PREVIS_EXACT_BINDING_REQUIRED')
    else:
        result=validate_adopted(p.creative_versions.objects,bindings[0].previsualization_ref,bindings[0])
        if result['sourceFingerprint']!=decision['sourceFingerprint']: raise ValueError('PREVIS_SOURCE_CHANGED')


async def prepare(p,package_ref,task,plan=None,*,compiler=None):
    compiler=compiler or p.prompt_compiler
    package=p.production_packages.get(package_ref)
    scope=package_scope(package).model_dump(mode='json',by_alias=True)
    fingerprint=source_fingerprint(p,package_ref,task)
    base=dict(entry='DramaPlugin.prepare_shot_preview',decisionOwner='Host',scope=scope,sourceFingerprint=fingerprint,
        requiredForAllShots=False,decision='HOST_JUDGMENT_PENDING',existing=discover(p,scope,source_fingerprint=fingerprint))
    if plan is None: return base,task
    action=plan.get('action'); reason=plan.get('reason','').strip()
    if action not in ('CREATE','ADJUST','ADOPT','REUSE','SKIP') or not reason: raise ValueError('PREVIS_HOST_DECISION_REQUIRED')
    base.update(decision=action,reason=reason)
    clean_refs=tuple(ref for ref,b in _bindings(p,task) if b.previsualization_ref is None)
    clean=task.model_copy(update={'execution_reference_refs':clean_refs or None,'previsualization_ref':None})
    if action in ('CREATE','ADJUST'):
        skills=external_skills(animation=bool(plan.get('animation')), rigging=bool(plan.get('rigging')),
            storyboard=bool(plan.get('storyboard')))
        sources=[dict(selection=v.selection.model_dump(mode='json',by_alias=True),value=v.value) for v in await compiler.reader.selections(package)]
        handoff=dict(schemaVersion=DECISION,createdAt=datetime.now(timezone.utc).isoformat(),scope=scope,sourceFingerprint=fingerprint,
            decision=action,reason=reason,packageRef=package_ref.model_dump(mode='json',by_alias=True),
            task=clean.model_dump(mode='json',by_alias=True),external=skills,sources=sources,
            supersedes=plan.get('previousRef'),use='DRAFT',medium='CURRENT_ADOPTED_DESIGN',provider='EXISTING_DRAMA_SEEDANCE')
        ref=_put(p,handoff)
        return {**base,'handoffRef':ref.model_dump(mode='json',by_alias=True),'handoff':handoff},clean
    if action=='SKIP':
        if not clean_refs and clean.input_mode=='reference':
            clean=clean.model_copy(update={'input_mode':'text_to_video','profile':clean.profile.model_copy(update={'mode':'text_to_video'}) if clean.profile else None})
        binding_ref=None
    else:
        if task.input_mode!='reference': raise ValueError('PREVIS_REQUIRES_SUPPORTED_REFERENCE_MODE')
        if action=='ADOPT':
            handoff=p.creative_versions.objects.read_ref(SourcePin.model_validate(plan['handoffRef']))
            if handoff.get('sourceFingerprint')!=fingerprint or handoff.get('scope')!=scope or handoff.get('decision') not in ('CREATE','ADJUST'):
                raise ValueError('PREVIS_HANDOFF_CHANGED')
            external=handoff['external']
            if external['status']!='AVAILABLE': raise ValueError('PREVIS_EXTERNAL_DEPENDENCIES_MISSING')
            selected_names={s['name'] for s in external['skills']}
            current=external_skills(animation=SKILLS[2] in selected_names,
                rigging='scenario-blender-rigging' in selected_names,
                storyboard='scenario-blender-previs-storyboard' in selected_names,roots=[external['root']])
            if current.get('version')!=external['version']: raise ValueError('PREVIS_EXTERNAL_SKILLS_CHANGED')
            outputs={role:_file(Path(path)) for role,path in plan['outputs'].items()}
            if not {'project','video','handoff','invocation'}<=outputs.keys(): raise ValueError('PREVIS_DELIVERABLES_REQUIRED')
            if Path(outputs['project']['path']).suffix!='.blend' or Path(outputs['video']['path']).suffix!='.mp4':
                raise ValueError('PREVIS_PROJECT_AND_VIDEO_REQUIRED')
            invocation=json.loads(Path(outputs['invocation']['path']).read_text())
            expected={s['name']:s['version'] for s in external['skills']}
            if invocation.get('skills')!=expected or invocation.get('exitCode')!=0 or not invocation.get('blenderVersion'):
                raise ValueError('PREVIS_EXTERNAL_EXECUTION_EVIDENCE_REQUIRED')
            if not invocation.get('calls') or not {'bx_blockout','bx_review'}<=set(invocation.get('modules',{})):
                raise ValueError('PREVIS_EXTERNAL_TOOL_CALLS_REQUIRED')
            module_paths = dict(bx_blockout=Path(external['root'])/SKILLS[1]/'scripts/bx_blockout.py',
                bx_review=Path(external['root'])/SKILLS[0]/'scripts/bx_review.py')
            if SKILLS[2] in selected_names:
                module_paths['bx_anim']=Path(external['root'])/SKILLS[2]/'scripts/bx_anim.py'
            if (invocation.get('sourceFingerprint')!=fingerprint or any(
                    Path(invocation.get('modules',{}).get(name,'')).resolve()!=path.resolve()
                    or not any(call.startswith(name+'.') for call in invocation['calls'])
                    for name,path in module_paths.items())):
                raise ValueError('PREVIS_EXTERNAL_INVOCATION_MISMATCH')
            inspection=plan['inspection']
            if (inspection.get('outcome')!='PASS' or inspection.get('videoSha256')!=outputs['video']['sha256']
                    or not inspection.get('continuousReview') or not inspection.get('notes')):
                raise ValueError('PREVIS_CONTINUOUS_HOST_REVIEW_REQUIRED')
            reference_purpose=plan.get('referencePurpose','')
            if not isinstance(reference_purpose,str) or len(reference_purpose)>1000:
                raise ValueError('PREVIS_REFERENCE_PURPOSE_INVALID')
            reference_semantics=plan.get('referenceSemantics',['motion','camera'])
            if (not isinstance(reference_semantics,list) or not reference_semantics
                    or any(s not in ('motion','camera') for s in reference_semantics)
                    or len(reference_semantics)!=len(set(reference_semantics))):
                raise ValueError('PREVIS_REFERENCE_SEMANTICS_INVALID')
            probe=_probe(outputs['video']['path'])
            value=dict(schemaVersion=SCHEMA,createdAt=datetime.now(timezone.utc).isoformat(),scope=scope,sourceFingerprint=fingerprint,
                packageRef=package_ref.model_dump(mode='json',by_alias=True),decision=action,reason=reason,use='ADOPTED_VIDEO_INPUT',
                external=external,outputs=outputs,inspection=inspection,probe=probe,
                referencePurpose=reference_purpose.strip(),referenceSemantics=reference_semantics,
                supersedes=handoff.get('supersedes'))
            result_ref=_put(p,value)
        else:
            result_ref=SourcePin.model_validate(plan['previousRef'])
            value=validate_adopted(p.creative_versions.objects,result_ref)
            if value['scope']!=scope or value['sourceFingerprint']!=fingerprint: raise ValueError('PREVIS_SOURCE_CHANGED')
        value=validate_adopted(p.creative_versions.objects,result_ref)
        # Existing Media storage owns upload/delivery. This is rehearsal footage,
        # never a provider-produced character original or a final film take.
        from drama_plugin.contracts.media import MediaType
        from drama_plugin.production.references import ReferenceExecutionBinding
        existing=next((b for _,b in _bindings(p,task) if b.previsualization_ref==result_ref),None)
        if existing:
            media=await p.providers.media.get_media(existing.media.media_id)
        else:
            media=await p.providers.media.import_media(work_id=scope['workId'],media_type=MediaType.VIDEO,
                source_uri=Path(value['outputs']['video']['path']).as_uri(),content=dict(previsualizationRef=result_ref.model_dump(mode='json',by_alias=True),
                    usageMode='PREVIS_REFERENCE',reviewStatus='PASS',probe=value['probe']),purpose='PREVIS_REFERENCE',
                source_ref='previsualization:'+result_ref.fingerprint,duration_ms=value['probe']['durationMs'])
        if media.content_hash!=value['outputs']['video']['sha256']: raise ValueError('PREVIS_IMPORTED_BYTES_MISMATCH')
        authority=task.unit.action_refs if task.unit else (package.scope.shot,)
        binding=ReferenceExecutionBinding(binding_id='external-previs:'+result_ref.fingerprint,version=1,scope=package_scope(package),
            media=dict(media_id=media.id,version='1',content_hash=media.content_hash,kind='video',
                semantics=tuple(value.get('referenceSemantics',('motion','camera'))),
                duration=value['probe']['durationMs']/1000,width=value['probe']['width'],height=value['probe']['height'],
                review_ref='previsualization:'+result_ref.fingerprint),
            duties=tuple(dict(role=role,subject=scope['shotId'],purpose=purpose,necessity='REQUIRED') for role,purpose in (
                ('CAMERA_MOTION' if 'camera' in value.get('referenceSemantics',('motion','camera')) else 'PERFORMANCE',
                 value.get('referencePurpose') or '视频提供空间、构图、运动路径和事件先后；人物外观取自正式图像，材质与光色按本镜文字。'),)),
            role='REFERENCE',authorization_scope='ADOPTED_PRODUCTION_INPUT',authority_refs=authority,previsualization_ref=result_ref)
        binding_ref=p.execution_references.register(binding)
        clean=clean.model_copy(update={'execution_reference_refs':(*clean_refs,binding_ref)})
        base.update(resultRef=result_ref.model_dump(mode='json',by_alias=True),mediaId=media.id,retained=value)
    decision=dict(schemaVersion=DECISION,createdAt=datetime.now(timezone.utc).isoformat(),scope=scope,sourceFingerprint=fingerprint,
        decision=action,reason=reason,bindingRef=binding_ref.model_dump(mode='json',by_alias=True) if binding_ref else None)
    decision_ref=_put(p,decision)
    clean=clean.model_copy(update={'previsualization_ref':decision_ref})
    validate_task(p,package_ref,clean)
    return {**base,'decisionRef':decision_ref.model_dump(mode='json',by_alias=True)},clean
