"""Local preparation integration, not an artistic/physical Blender acceptance."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.film.previsualization import SCHEMA, _file, discover, prepare, external_skills, REQUIRED, SKILLS, source_fingerprint, validate_task
from drama_plugin.generation.contracts import GenerationTask
from drama_plugin.generation.sources import PackageReader
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.plugin import DramaPlugin
from drama_plugin.production.contracts import (AssemblyBoundary, DomainReference,
    GenerationIntent, PackageContent, PackageScope, ProductionPackage, SourceReference)
from drama_plugin.production.store import ProductionPackageStore
from drama_plugin.runtime.contracts import ArtifactReference, RunMode
from drama_plugin.skills import SkillRegistry


ROOT = Path(__file__).resolve().parents[1]


class LocalSource:
    async def resolve(self, reference):
        return {'currentAction': 'UNIT FIXTURE: support and contact; not a production design'}


class PreviewCompiler:
    def __init__(self):
        self.reader = PackageReader(LocalSource())
        self.calls = []

    async def preview_request(self, ref, task):
        self.calls.append((ref, task))
        return {'submitted': False, 'request': {'fixture': 'not a provider request'}}


def case(tmp_path):
    refs = {owner: SourceReference(owner=owner, artifact_ref=owner + '-unit', version=1,
        fingerprint=sha256_canonical({'unit': owner})) for owner in ('work', 'scene', 'shot')}
    package = ProductionPackage.freeze(PackageContent(
        scope=PackageScope(**refs), sources=(DomainReference(domain='DIRECTION', reference=refs['shot']),),
        obligations=(refs['shot'],), generation_intent=GenerationIntent(duration_ms=3000, duration_ref=refs['shot']),
        boundary=AssemblyBoundary(mode=RunMode.EXPERIMENT,
            policy_ref=ArtifactReference(owner='unit', artifact_ref='test-policy', version=1))))
    packages = ProductionPackageStore()
    ref = packages.put(package)
    skills = SkillRegistry(); skills.load_directory(ROOT / 'skills')
    p = SimpleNamespace(production_packages=packages, prompt_compiler=PreviewCompiler(),
        creative_versions=SimpleNamespace(objects=DirectorArtifactStore(tmp_path / 'creative')), skills=skills,
        execution_references=__import__('drama_plugin.production.references',fromlist=['ReferenceExecutionStore']).ReferenceExecutionStore())
    return p, ref, GenerationTask()


def external(tmp_path):
    for name in SKILLS:
        for rel in ('SKILL.md', *REQUIRED[name]):
            p=tmp_path/name/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture resource '+rel)
    return tmp_path


def test_discovery_requires_shared_siblings_and_records_content_version(tmp_path):
    root=external(tmp_path)
    result=external_skills(animation=True,roots=[root])
    assert result['status']=='AVAILABLE' and len(result['skills'])==3
    assert all(s['version'].startswith('sha256:') for s in result['skills'])
    (root/SKILLS[0]/'scripts/bx_review.py').unlink()
    assert external_skills(roots=[root])['status']=='DEPENDENCIES_MISSING'


@pytest.mark.asyncio
async def test_skip_persists_reason_without_external_tools_or_video(tmp_path,monkeypatch):
    p,ref,task=case(tmp_path)
    monkeypatch.setattr('drama_plugin.film.previsualization.external_skills',lambda **kw: pytest.fail('skip discovers no external dependency'))
    result,new=await prepare(p,ref,task,dict(action='SKIP',reason='No unresolved spatial relation'))
    assert new.previsualization_ref
    validate_task(p,ref,new)
    assert p.creative_versions.objects.read_ref(new.previsualization_ref)['reason']=='No unresolved spatial relation'
    assert not new.execution_reference_refs


@pytest.mark.asyncio
async def test_create_is_handoff_not_internal_blender_executor(tmp_path,monkeypatch):
    p,ref,task=case(tmp_path)
    monkeypatch.setenv('DRAMA_BLENDER_SKILLS_ROOT',str(external(tmp_path/'external')))
    monkeypatch.setattr('subprocess.run',lambda *a,**kw:pytest.fail('Plugin cannot render'))
    result,new=await prepare(p,ref,task,dict(action='CREATE',reason='Contact needs rehearsal',animation=True))
    assert len(result['handoff']['external']['skills'])==3
    assert result['handoff']['task']==task.model_dump(mode='json',by_alias=True)
    assert result['handoff']['sources']


@pytest.mark.asyncio
async def test_old_internal_output_is_history_never_reusable(tmp_path):
    p,ref,task=case(tmp_path)
    base,_=await prepare(p,ref,task)
    value=dict(schemaVersion='shot-previsualization-v1',scope=base['scope'],sourceFingerprint=base['sourceFingerprint'],createdAt='2026-01-01',outputs={})
    old=p.creative_versions.objects.put('previsualization:'+sha256_canonical(value),value)
    assert discover(p,base['scope'])[0]['historicalOnly']
    task=task.model_copy(update={'input_mode':'reference'})
    with pytest.raises(ValueError,match='PREVIS_EXTERNAL_ADOPTION_REQUIRED'):
        await prepare(p,ref,task,dict(action='REUSE',reason='Old draft',previousRef=old.model_dump()))


@pytest.mark.asyncio
async def test_skip_removes_only_rehearsal_bindings(tmp_path):
    from drama_plugin.production.references import ReferenceExecutionBinding
    from drama_plugin.contracts.source_pin import SourcePin
    from drama_plugin.generation.audio import package_scope
    p,ref,task=case(tmp_path)
    def binding(name,previs):
        return ReferenceExecutionBinding(binding_id=name,version=1,scope=package_scope(p.production_packages.get(ref)),
            media=dict(media_id=name,version='1',content_hash='a'*64,kind='video' if previs else 'image',
                semantics=('camera',) if previs else ('environment',),review_ref='review'),
            duties=(dict(role='CAMERA_MOTION' if previs else 'LOCATION',necessity='REQUIRED',subject='room',purpose='Specific duty'),),
            role='REFERENCE',authorization_scope='ADOPTED_PRODUCTION_INPUT',authority_refs=(p.production_packages.get(ref).scope.shot,),
            previsualization_ref=SourcePin(key='fixture',kind='DIRECTION',fingerprint='b'*64) if previs else None)
    image=p.execution_references.register(binding('image',False));video=p.execution_references.register(binding('video',True))
    task=task.model_copy(update={'input_mode':'reference','execution_reference_refs':(image,video)})
    result,new=await prepare(p,ref,task,dict(action='SKIP',reason='Updated shot does not need rehearsal'))
    assert new.execution_reference_refs==(image,)
    assert source_fingerprint(p,ref,new)==source_fingerprint(p,ref,task)
    validate_task(p,ref,new)
    with pytest.raises(ValueError,match='PREVIS_SKIP_HAS_VIDEO_BINDING'):
        validate_task(p,ref,new.model_copy(update={'execution_reference_refs':(image,video)}))


@pytest.mark.asyncio
async def test_changed_design_rejects_stale_decision(tmp_path):
    p,ref,task=case(tmp_path)
    _,new=await prepare(p,ref,task,dict(action='SKIP',reason='Clear shot'))
    # A camera direction is a creative input even on a skipped shot.
    changed=new.model_copy(update={'camera_direction_ref':ArtifactReference(owner='camera',artifact_ref='changed',version=1)})
    with pytest.raises(ValueError,match='PREVIS_SOURCE_CHANGED'):
        validate_task(p,ref,changed)


@pytest.mark.asyncio
async def test_shared_delivery_preserves_continuation_operation_context(tmp_path):
    from drama_plugin.execution.live_transport import TargetHttpTransport
    from drama_plugin.runtime.contracts import RuntimeScope
    scope=RuntimeScope(work_id='work')
    operation=SimpleNamespace(scope=scope,model='model',preparation_ref='continuation-preparation')
    seen=[]
    async def reference_url(reference,context):
        seen.append(context.preparation_ref)
        return 'https://storage.example/exact-first-frame.png'
    transport=SimpleNamespace(reference_url=reference_url)
    ref=SimpleNamespace(kind='image',role='FIRST_FRAME')
    result=await TargetHttpTransport.materialize_reference_payload(transport,
        {'content':[{'type':'text','text':'Continue the shot'}]},[ref],scope=scope,model='model',operation=operation)
    assert seen==['continuation-preparation']
    assert result['content'][1]['role']=='first_frame'
    with pytest.raises(ValueError,match='REFERENCE_DELIVERY_CONTEXT_MISMATCH'):
        await TargetHttpTransport.materialize_reference_payload(transport,{},[ref],scope=scope,model='other',operation=operation)


def test_optional_external_skills_are_selected_by_name(tmp_path):
    for name, files in REQUIRED.items():
        folder = tmp_path / name
        for rel in ('SKILL.md', *files):
            f = folder / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text('fixture')
    result = external_skills(rigging=True, storyboard=True, roots=[tmp_path])
    names = {s['name'] for s in result['skills']}
    assert names == {*SKILLS[:2], 'scenario-blender-rigging', 'scenario-blender-previs-storyboard'}
    assert SKILLS[2] not in names
    all_skills = external_skills(animation=True, rigging=True, storyboard=True, roots=[tmp_path])
    assert len(all_skills['skills']) == 5
    (tmp_path / 'scenario-blender-rigging/scripts/bx_rig.py').unlink()
    assert external_skills(rigging=True, roots=[tmp_path])['status'] == 'DEPENDENCIES_MISSING'
    assert external_skills(roots=[tmp_path])['status'] == 'AVAILABLE'
