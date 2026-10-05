"""Adjacent operations preserve the original Film unit; HTTP stays in MockTransport."""
from datetime import datetime,timedelta,timezone
from dataclasses import replace
import pytest
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.contracts import Kind
from drama_plugin.execution.contracts import MediaBinding,ExecutionOperation,CreativeMediaReview
from drama_plugin.execution.live_transport import TargetHttpTransport,wire_payload
from drama_plugin.execution.review import ReviewResponse
from drama_plugin.generation.contracts import GenerationTask,GenerationPreparation,FinalPromptArtifact
from drama_plugin.generation.operation import resolve_profile
from drama_plugin.production.references import ReferenceExecutionBinding
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.runtime.contracts import ArtifactReference,DecisionCategory,RuntimeScope,RuntimeState
from test_unified_mainline import load,task_for,video,prepare_goal


def referenced_task(p,package,task,media,review_ref,binding_id='adjacent-reference',mode='reference'):
    profile=resolve_profile(model=task.profile.model,duration_ms=4000,resolution='720p',ratio='16:9',
        native_audio=task.profile.native_audio,mode=mode,policy=p.operation_resolver.policy)
    scope=RuntimeScope(work_id=package.scope.work.artifact_ref,scene_id=package.scope.scene.artifact_ref,shot_id=package.scope.shot.artifact_ref)
    subject=next(v.body.facts['presentSubjects'][0]['id'] for r in task.owners.adopted_refs for v in (p.creative_versions.resolve(r),) if v.kind==Kind.PROFESSIONAL and v.body.domain=='SUBJECTS')
    authority=next(s.reference for s in package.sources if s.domain=='REFERENCE')
    source=p.creative_versions.objects.read_ref(task.owners.rights_pin)
    material={k:v for k,v in source.items() if k not in ('externalProcessingAuthorized','requestRef','decisionRef')}
    material['processingScope']={**material['processingScope'],'mode':mode}
    material['profile']=profile.model_dump(mode='json',by_alias=True)
    pin=p.creative_versions.objects.put('test-reference-rights:'+sha256_canonical(material),material)
    request=ArtifactReference(owner='source-owner',artifact_ref=pin.key,version=1)
    old_decision,decision_scope,_=p.ledger.get_artifact('user-decision',task.owners.rights_decision_ref)
    decision=UserDecisionRecord.seal(run_id=old_decision['runId'],scope=decision_scope,decision_id=old_decision['runId']+':reference-rights',
        category=DecisionCategory.ADOPTION,accepted=True,source_ref=request)
    ref=p.reviews.put_user_decision(decision)
    rights=p.creative_versions.objects.put('test-reference-authorized:'+sha256_canonical(material),
        {**material,'externalProcessingAuthorized':True,'requestRef':request.model_dump(mode='json',by_alias=True),
         'decisionRef':ref.model_dump(mode='json',by_alias=True)})
    bindings=ReferenceExecutionBinding(binding_id=binding_id,version=1,scope=scope,
        media=dict(media_id=media.id,version='1',content_hash=media.content_hash,kind='video',
            semantics=('identity','environment','motion','continuity'),duration=4,width=1280,height=720,
            review_ref=review_ref.artifact_ref),duties=(dict(role='CHARACTER',necessity='REQUIRED',subject=subject,
            purpose='Identity proof'),),subject_ids=(subject,),role='REFERENCE',
        authorization_scope='REVIEWED_TRIAL_INPUT',authority_refs=(authority,))
    binding_ref=p.execution_references.register(bindings)
    owners=task.owners.model_copy(update={'rights_pin':rights,'rights_request_ref':request,'rights_decision_ref':ref})
    # The fixture's explicit risk disposition is still approved; the new input is separately pinned.
    return GenerationTask.model_validate({**task.model_dump(),'profile':profile,'input_mode':mode,'owners':owners,
        'execution_reference_refs':(binding_ref,)})


@pytest.mark.asyncio
async def test_native_video_reference_compiles_and_transfers_exact_reviewed_original(tmp_path,monkeypatch,video):
    p,package,service,calls=load(tmp_path,monkeypatch,video)
    task=task_for(p,package)
    waiting=await prepare_goal(p,package,task)
    cp=p.execution.store.ledger
    with cp.transaction() as db:
        row=db.execute('SELECT operation_ref_json FROM production_operation WHERE operation_ref_json IS NOT NULL').fetchone()
    op_ref=ArtifactReference.model_validate_json(row[0]);op=p.execution.store.get(op_ref,ExecutionOperation)
    progress=p.execution.store.checkpoint(op_ref).progress
    binding=p.execution.store.get(progress.video_ref,MediaBinding)
    context=p.execution.review_context(op,binding.media,binding.canonical_media_ref)
    done=await p.provide_human_media_review(waiting.run_id,media_ref=progress.video_ref,context_hash=context,response=ReviewResponse('PASS'))
    review_ref=next(r for r in done.last_result.artifact_refs if r.owner=='creative-media-review')
    from drama_plugin.contracts.media import Media
    media=Media.model_validate(service.records[0])
    async def get_media(_):return media
    monkeypatch.setattr(p.providers.media,'get_media',get_media)
    p.prompt_compiler.references.media_reader=p.providers.media
    task=p.generation_artifacts.inputs(waiting.run_id).task
    next_task=referenced_task(p,package,task,media,review_ref)
    first_bytes=p.generation_artifacts.get(p.generation_artifacts.prepared(waiting.run_id),GenerationPreparation).model_dump_json()
    await p.operation_resolver.selected(package,next_task,p.prompt_compiler.reader)
    result=await p.prompt_compiler.compile(package.artifact_reference(),next_task)
    assert result.preparation_ref is not None, p.ledger.get_artifact('execution-diagnostic',result.diagnostics_ref)[0]
    prep=p.generation_artifacts.get(result.preparation_ref,GenerationPreparation)
    final=p.generation_artifacts.get(prep.final_prompt_ref,FinalPromptArtifact)
    assert not any(d.required for d in await p.prompt_compiler.validate_execution_sources(prep.artifact_reference()))
    assert '@视频1' in final.prompt_text
    preview=TargetHttpTransport.preview(prep,final,ledger=p.ledger)
    assert preview['content'][1]['role']=='reference_video'
    assert preview['content'][1]['video_url']['url']=='media:'+media.id+':'+media.content_hash
    assert 'https://' not in str(preview)
    child=p.create_media_review_run(package_ref=package.artifact_reference(),task=next_task)
    # Goal creation never creates or repeats a paid operation.
    assert child.run_id!=waiting.run_id and sum(r.method=='POST' for r in calls)==1
    assert p.generation_artifacts.get(p.generation_artifacts.prepared(waiting.run_id),GenerationPreparation).model_dump_json()==first_bytes
    transport=p.execution.transports['seedance']
    from drama_plugin.execution.contracts import RequestReference
    request_ref=RequestReference(binding_ref=next_task.execution_reference_refs[0],media_id=media.id,
        content_hash=media.content_hash,role='REFERENCE',kind='video')
    assert await transport.reference_url(request_ref,op)=='https://result.invalid/clip.mp4'
    with pytest.raises(ValueError,match='IDENTITY_MISMATCH'):
        await transport.reference_url(request_ref.model_copy(update={'content_hash':'0'*64}),op)
    with pytest.raises(Exception,match='LEDGER_REQUIRED'):
        TargetHttpTransport.preview(prep,final)


@pytest.mark.asyncio
async def test_phase_selection_keeps_only_requested_authored_phase(tmp_path,monkeypatch,video):
    p,package,_,_=load(tmp_path,monkeypatch,video)
    reader=p.prompt_compiler.reader
    selected=await reader.selections(package)
    action=next(v for v in selected if v.selection.domain=='ACTION' and isinstance(v.value,dict) and 'actionPhases' in v.value)
    rows=[{**r,'beatId':r.get('beatId','beat-1'),'spokenIds':r.get('spokenIds',[])} for r in action.value['actionPhases']]
    later={**rows[0],'beatId':'later-approved-beat','action':'The later authored action.', 'entryState':'Later entry.', 'observable':'Later exit.'}
    async def sources(_):return (replace(action,value={**action.value,'actionPhases':[rows[0],later]}),)
    monkeypatch.setattr(reader,'selections',sources)
    original=await p.operation_resolver.select_unit(package,reader)
    following=await p.operation_resolver.select_unit(package,reader,phase_index=1)
    assert original.action_refs[0].path[-2:] == ('0','action')
    assert following.action_refs[0].path[-2:] == ('1','action')
    assert following.beat_ids==('later-approved-beat',)
    assert all(('actionPhases','0') != r.reference.path[-3:-1] for r in following.fact_refs)
    with pytest.raises(ValueError,match='OUT_OF_RANGE'):
        await p.operation_resolver.select_unit(package,reader,phase_index=2)

@pytest.mark.asyncio
async def test_existing_parent_queues_only_same_scene_without_recreating_first(tmp_path,monkeypatch,video):
    from test_preparation_lifecycle_repair import reference_boundary
    from drama_plugin.contracts.media import Media
    p,a,parent,first,cp=await reference_boundary(tmp_path,monkeypatch)
    package=p.production_packages.get(cp.units[0].package_ref)
    media=Media(id='offline-reviewed-native',work_id=first.scope.work_id,shot_id=first.scope.shot_id,
        media_type='VIDEO',mime_type='video/mp4',source_ref='offline-input',file_size=video.stat().st_size,
        content_hash=__import__('hashlib').sha256(video.read_bytes()).hexdigest(),duration_ms=4000)
    evidence=ArtifactReference(owner='creative-media-review',artifact_ref='offline-visual-evidence',version=1)
    tasks=tuple(referenced_task(p,package,cp.operation_task,media,evidence,binding_id='clip-'+str(i)) for i in (1,2))
    before=p.runtime.store.load(first.run_id)
    with pytest.raises(ValueError,match='EXACT_CONTINUATION_FIRST_FRAME'):
        p.queue_source_film_media(parent.run_id,tasks=tasks)
    with pytest.raises(ValueError,match='EXACT_CONTINUATION_FIRST_FRAME'):
        p.queue_source_film_media(parent.run_id,tasks=tasks[:1])
    assert p.runtime.store.load(first.run_id)==before
    assert p.film.store.checkpoint(parent.run_id).units==cp.units
    assert p.film.store.checkpoint(parent.run_id).operation_task==cp.operation_task
    assert a.calls==['canon','direction','professional']
    with pytest.raises(ValueError,match='BOUNDED'):
        p.queue_source_film_media(parent.run_id,tasks=tasks*2)
    with pytest.raises(ValueError,match='EXACT_CONTINUATION_FIRST_FRAME'):
        p.queue_source_film_media(parent.run_id,tasks=(cp.operation_task,))
    with p.ledger.transaction() as db:
        assert db.execute("SELECT count(*) FROM production_operation WHERE operation_ref_json IS NOT NULL").fetchone()[0]==0

@pytest.mark.asyncio
async def test_first_operation_query_transport_does_not_fence_new_child(tmp_path,monkeypatch,video):
    p,package,_,_=load(tmp_path,monkeypatch,video)
    original=p.execution.transports['seedance']
    original.offline=False
    old_ref=ArtifactReference(owner='execution-operation',artifact_ref='completed-original-operation',version=1)
    original.recovery_operation_ref=old_ref
    fresh=TargetHttpTransport(original.adapter,tmp_path/'new-acks',ledger=p.ledger)
    composed=[]
    def configure(**kwargs):composed.append(kwargs['recovery_operation_ref']);return fresh
    monkeypatch.setattr('drama_plugin.execution.live_transport.configured_http_transport',configure)
    p._compose_media_owners(task_for(p,package))
    assert composed==[None]
    assert p.execution.transports['seedance'] is fresh
    assert original.recovery_operation_ref==old_ref and fresh.recovery_operation_ref is None


@pytest.mark.asyncio
@pytest.mark.parametrize('interrupted_revision',[False,True])
async def test_failed_reference_readiness_recovery_preserves_gate_and_does_not_post(tmp_path,monkeypatch,video,interrupted_revision):
    from drama_plugin.generation.contracts import ExecutionDiagnostic
    from drama_plugin.production.contracts import SourceDomain
    from drama_plugin.runtime.contracts import ExecutionRevision
    from drama_plugin.contracts.media import Media
    p,package,service,calls=load(tmp_path,monkeypatch,video)
    waiting=await prepare_goal(p,package,task_for(p,package))
    with p.ledger.transaction() as db:
        op_ref=ArtifactReference.model_validate_json(db.execute('SELECT operation_ref_json FROM production_operation WHERE operation_ref_json IS NOT NULL').fetchone()[0])
    op=p.execution.store.get(op_ref,ExecutionOperation)
    progress=p.execution.store.checkpoint(op_ref).progress
    binding=p.execution.store.get(progress.video_ref,MediaBinding)
    done=await p.provide_human_media_review(waiting.run_id,media_ref=progress.video_ref,
        context_hash=p.execution.review_context(op,binding.media,binding.canonical_media_ref),response=ReviewResponse('PASS'))
    review_ref=next(r for r in done.last_result.artifact_refs if r.owner=='creative-media-review')
    media=Media.model_validate(service.records[0])
    async def get_media(_):return media
    monkeypatch.setattr(p.providers.media,'get_media',get_media)
    p.prompt_compiler.references.media_reader=p.providers.media
    task=referenced_task(p,package,p.generation_artifacts.inputs(waiting.run_id).task,media,review_ref)
    child=p.create_media_review_run(package_ref=package.artifact_reference(),task=task)
    original=p.prompt_compiler.validate_execution_sources
    async def broken(_):return (ExecutionDiagnostic(code='REFERENCE_INPUT_UNRESOLVED',owner='reference-strategy',domain=SourceDomain.REFERENCE,required=True),)
    monkeypatch.setattr(p.prompt_compiler,'validate_execution_sources',broken)
    failed=await p.runtime.run(child.run_id)
    assert failed.state==RuntimeState.FAILED and failed.last_result.code=='GOVERNED_HARD_STOP'
    old_gate=next(r for r in failed.last_result.artifact_refs if r.owner=='gate-decision')
    monkeypatch.setattr(p.prompt_compiler,'validate_execution_sources',original)
    prepared_ref=p.generation_artifacts.prepared(child.run_id)
    assert not any(d.required for d in await original(prepared_ref))
    # Simulate a crash after the replacement Gate is durable but before the Run save.
    fixed=p.gate_governor.govern((),scope=child.scope,mode=child.mode,package_ref=package.artifact_reference())
    p.gate_findings.put_decision(fixed,run_id=child.run_id)
    assert p.gate_findings.latest(child.run_id)!=old_gate
    current=ExecutionRevision(fingerprint=sha256_canonical(['reference-readiness-v2',prepared_ref.model_dump(mode='json',by_alias=True)]),
        input_fingerprint=sha256_canonical([package.artifact_reference().model_dump(mode='json',by_alias=True),
            task.model_dump(mode='json',by_alias=True),prepared_ref.model_dump(mode='json',by_alias=True)]))
    recovered=await p.runtime.repair_resolved_reference_gate(child.run_id,expected_revision=failed.revision,
        decision_ref=task.owners.rights_decision_ref,current=current)
    assert recovered.execution_revision is None  # This capability has no execution inspector.
    assert recovered.external_repairs[0].failed_result==failed.last_result
    if interrupted_revision:
        # A retained faulty repair must not permanently fence this inspector-free step.
        p.runtime.store.save(recovered.model_copy(update={'revision':recovered.revision+1,
            'execution_revision':current}),expected_revision=recovered.revision)
        denied=await p.runtime.run(child.run_id)
        assert denied.last_result.code=='EXECUTION_REVISION_CHANGED'
        repaired=await p.runtime.repair_resolved_reference_gate(child.run_id,expected_revision=denied.revision,
            decision_ref=task.owners.rights_decision_ref,current=current)
        assert repaired.execution_revision is None
        assert tuple(r.failed_result.code for r in repaired.external_repairs)==('GOVERNED_HARD_STOP','EXECUTION_REVISION_CHANGED')
    result=await p.runtime.run(child.run_id)
    assert result.state==RuntimeState.WAITING_EXTERNAL and result.last_result.external_ref==prepared_ref
    assert p.generation_artifacts.prepared(child.run_id)==prepared_ref
    assert p.gate_findings.decision(old_gate).effect.value=='BLOCK'
    assert sum(r.method=='POST' for r in calls)==1
