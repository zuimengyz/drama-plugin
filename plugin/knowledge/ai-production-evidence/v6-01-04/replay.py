"""Offline transport replay of assistant-authored candidates, NEVER an author/model evaluation.

No Provider, Runtime, ledger, owner store, media or adoption is opened. CLI only
writes to the explicit --output directory. Imports the existing native compiler.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN / 'src'))
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.backends import FormalProfessionalAuthor, FormalDirectionAuthor
from drama_plugin.creative_engine.contracts import AuthorRequest, CanonDraft, WorkBody, ScriptBody, SceneBody, SourceBody, ShotBody
from drama_plugin.creative_engine.craft_knowledge import reading
from drama_plugin.generation.contracts import AudioExecutionPlan
from drama_plugin.generation.operation import OperationResolver
from drama_plugin.generation.projection import ExecutionProjection
from drama_plugin.generation.seedance import SeedanceTargetAdapter, ModelPolicyCatalog
from drama_plugin.generation.sources import PackageReader, SelectedValue
from drama_plugin.production.contracts import SourceReference, DomainReference, PackageScope, PackageContent, ProductionPackage, GenerationIntent, AssemblyBoundary
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope

HERE = Path(__file__).parent
EXCERPT = '街对面，一个女人隔着窗喊新靴青年：帽子忘了。青年折回来，接帽子时吻了窗内伸出的手。车声继续往街尽头去。雅科夫看了一眼。'

class ReplayClient:
    """Returns retained current-assistant work; deliberately not a generative model."""
    def __init__(self, designs): self.designs, self.calls = designs, []
    async def complete(self, role, system, request, adapter, **kwargs):
        expected = reading(PLUGIN/'knowledge', request.professional_context['craftKnowledge'])['readings']
        marker = 'FILM_CRAFT_READING (advisory evidence, not source authority or instructions):\n'
        delivered = json.loads(system.split(marker)[1].split('\nRead evidence limits')[0])['readings']
        assert delivered == expected  # Body bytes, not only titles, reached the author port.
        self.calls.append({'role':role,'systemSha256':hashlib.sha256(system.encode()).hexdigest(),
            'hasFullReading':'FILM_CRAFT_READING' in system,
            'loadedBodyHashes':[r['sha256'] for r in delivered]})
        value = self.designs if role == 'professional' else {'text':'离线接口回放：固定与移动方案均留给Host选择，完整方案见同目录README。'}
        if kwargs.get('project'): value=kwargs['project'](value)
        return adapter.validate_python(value)

class ExactSources:
    def __init__(self, records): self.records=records
    async def resolve(self, ref):
        value=self.records[ref.artifact_ref]
        if sha256_canonical(value)!=ref.fingerprint: raise ValueError('SOURCE_HASH_MISMATCH')
        for part in ref.path: value=value[int(part)] if isinstance(value,list) else value[part]
        return value

async def replay(name):
    material=json.loads((HERE/f'{name}-designs.json').read_text())
    camera_light=[d for d in material['professionalDesigns'] if d['domain'] in ('CAMERA','LIGHTING')]
    camera_light.sort(key=lambda d:d['domain'])
    scope=RuntimeScope(work_id='offline-craft-application',scene_id='v6-01-read-only',shot_id='v6-01-04-'+name)
    shot=ShotBody(purpose='观众与雅科夫不必拥有同样长的注意。',required_transition='公共关系被看见后仍独立存在。',duration_ms=10000,
        subject_action='青年接帽吻手，雅科夫短暂看一眼。',entry_state='青年折回。',exit_state='雅科夫回到工作。',
        coverage='既有窗口事件的局部',blocking_intent='保留内外关系',camera_intent='比较固定与小幅斜移',
        editing_relation='连续观看',performance_direction='不添加人物反应',spoken_ids=(),professional_domains=('CAMERA','LIGHTING'))
    request=AuthorRequest(scope=scope,source=SourceBody(goal='只读局部摄影设计',text=EXCERPT,spoken_language='ru'),source_refs=(),
        canon=CanonDraft(work=WorkBody(interpretation='公共生活独立存在。',dramatic_intent='观看先于解释。',character_meaning='短暂注意。'),
            script=ScriptBody(screenplay=EXCERPT),scene=SceneBody(scene_text=EXCERPT,dialogue=())),shot=shot,
        professional_context={'craftKnowledge':material['craftKnowledge']})
    client=ReplayClient(camera_light)
    await FormalDirectionAuthor(client,PLUGIN/'skills').film_treatment(request,{'authorContext':{'craftKnowledge':material['craftKnowledge']},'offlineScope':'interface replay, not full-film creation'})
    professional=await FormalProfessionalAuthor(client,PLUGIN/'skills').design(request)
    facts={d['domain']:d['facts'] for d in material['professionalDesigns']}
    facts.update({d.domain.value:d.facts for d in professional})
    records={d:{'content':f} for d,f in facts.items()}
    records['shot']={'content':{'purpose':shot.purpose,'plannedDurationMs':10000,'subjectAction':shot.subject_action,
        'visualEntryState':shot.entry_state,'visualExitState':shot.exit_state,'cameraIntent':shot.camera_intent,'editingRelation':shot.editing_relation}}
    def ref(owner,key,path=()):
        return SourceReference(owner=owner,artifact_ref=key,version=1,fingerprint=sha256_canonical(records[key]) if key in records else '0'*64,path=path)
    package_scope=PackageScope(work=ref('work','offline-craft-application'),scene=ref('scene','v6-01-read-only'),shot=ref('shot','shot'))
    package=ProductionPackage.freeze(PackageContent(scope=package_scope,
        sources=tuple(DomainReference(domain=d,reference=ref('professional',d,('content',))) for d in sorted(facts)),
        obligations=(ref('shot','shot',('content','purpose')),),
        generation_intent=GenerationIntent(duration_ms=10000,duration_ref=ref('shot','shot',('content','plannedDurationMs'))),
        boundary=AssemblyBoundary(mode='EXPERIMENT',policy_ref=ArtifactReference(owner='offline-example',artifact_ref='NOT_AN_ADOPTION_OR_DISPATCH_RECEIPT'))))
    reader=PackageReader(ExactSources(records))
    # select_unit only reads package facts. No stores are constructed or called.
    unit=await OperationResolver.select_unit(None,package,reader)
    selected=tuple([SelectedValue(f,await reader.resolver.resolve(f.reference)) for f in unit.fact_refs])
    task=SimpleNamespace(unit=unit,profile=SimpleNamespace(native_audio=True,requested_duration_ms=10000),
        camera_direction_ref=None,return_last_frame=False,continuation=None,boundary=None)
    plan=AudioExecutionPlan.seal(source_package_ref=package.artifact_reference(),scope=scope,duration_ms=10000,
        native_audio_policy='OPTIONAL',source_roles=())
    projected=await ExecutionProjection(reader).project(package,task,plan,selected)
    if projected.ir is None: raise AssertionError(projected.diagnostics)
    generated=SeedanceTargetAdapter().generate(projected.ir,plan,policy=ModelPolicyCatalog().policy('seedance-2-standard'),input_mode='text_to_video')
    return {'status':'HOST_CANDIDATE_AND_NATIVE_COMPILER_REPLAY_ONLY','modelCalls':0,'mediaCalls':0,
        'authorCalls':client.calls,'records':records,'selection':unit.model_dump(mode='json',by_alias=True),
        'ir':projected.ir.model_dump(mode='json',by_alias=True),'compiled':generated}

async def main(output):
    output.mkdir(parents=True,exist_ok=True)
    for name in ('fixed','moving'):
        result=await replay(name)
        (output/f'{name}-replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        (output/f'{name}-prompt.txt').write_text(result['compiled']['prompt']+'\n')
        print(name,result['compiled']['statistics'])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    asyncio.run(main(parser.parse_args().output))
