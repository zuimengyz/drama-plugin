"""Native camera timing reaches real mock wire; revised candidates retain history."""
import pytest
from datetime import datetime,timedelta,timezone
from drama_plugin.contracts.video import CostEstimate
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.contracts import Authority,Kind,DesignBody
from drama_plugin.generation.contracts import CameraPhaseTiming,CameraExecutionDirection,GenerationPreparation,FinalPromptArtifact
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.execution.live_transport import TargetHttpTransport,FinancialTerms
from drama_plugin.execution.contracts import CreativeMediaReview,ReviewObservation
from drama_plugin.execution.review import ReviewResponse
from drama_plugin.runtime.contracts import DecisionCategory,RuntimeState
from test_continuation_endpoints import scenario,finish,following,completion,media_files

async def approve_mock_cost(p,r,child):
    await p.resume_source_film_run(r)
    ref=p.generation_artifacts.prepared(child);prep=p.generation_artifacts.get(ref,GenerationPreparation)
    final=p.generation_artifacts.get(prep.final_prompt_ref,FinalPromptArtifact)
    digest=sha256_canonical(TargetHttpTransport.preview(prep,final,ledger=p.ledger));now=datetime.now(timezone.utc)
    terms=FinancialTerms(preparation_ref=ref,profile=prep.task.profile,wire_payload_hash=digest,
        cost_quote=CostEstimate(currency='CNY',amount=1,source='MOCK_ONLY',checked_at=now,expires_at=now+timedelta(hours=1),request_fingerprint=digest),budget_microunits=1000000)
    await p.provide_media_cost_terms(r,terms)
    await p.decide_target_run(r,decision_id=p.runtime.decision_id(r),accepted=True,source_ref=ref)
    await p.resume_source_film_run(r)


def camera_binding(p,r,package,task,*,verbose=False):
    core=tuple(r for r in task.owners.adopted_refs if p.creative_versions.resolve(r).kind!=Kind.PROFESSIONAL)
    row=CameraPhaseTiming(phase_index=1,scene_context='A weary confession turns from self-mockery to affection.',
        preceding_beat_context='Opening establish and push are completed.',following_beat_context='Later solitude remains later.',
        inherited_state='Eye-level frontal close view from actual tail; push has settled.',decision='START',
        trigger='Only when the eyes soften with affection in this phase; never at the file boundary.',
        motivation='The audience discovers affection rather than inspecting the room.',trajectory='A small forward move on the same axis.',
        amplitude='A slight approach within the close view.',end_state='Settle in a slightly tighter frontal view.')
    if verbose:
        row=row.model_copy(update={'scene_context':'Already established room. '*100,'motivation':'Observe the affection within this beat. '*70})
    suffix='verbose' if verbose else 'concise'
    camera=p.creative_versions.write(writer=Authority.PROFESSIONAL,kind=Kind.PROFESSIONAL,scope=p.runtime.store.load(p.source_film_media_opening(r)).scope,
        body=DesignBody(domain='CAMERA',facts={'movement':{'policy':'Overall shot context only.', 'phaseDirections':[row.model_dump(mode='json',by_alias=True)]}}),sources=core,operation='camera-test-'+suffix)
    decision=UserDecisionRecord.seal(run_id=r,scope=p.runtime.store.load(r).scope,decision_id=r+':camera-test-accept-'+suffix,
        category=DecisionCategory.ART_APPROVAL,accepted=True,source_ref=camera.runtime_ref(),terms_hash=sha256_canonical([v.model_dump(mode='json',by_alias=True) for v in (package.artifact_reference(),task.unit,camera)]))
    decision_ref=p.reviews.put_user_decision(decision)
    binding=CameraExecutionDirection.seal(scope=p.runtime.store.load(p.source_film_media_opening(r)).scope,
        source_package_ref=package.artifact_reference(),camera_ref=camera,selection_hash=sha256_canonical(task.unit),approval_ref=decision_ref)
    return task.model_copy(update={'camera_direction_ref':p.generation_artifacts.put(binding)})

@pytest.mark.asyncio
async def test_camera_event_wire_and_same_endpoint_candidate_replacement(tmp_path,monkeypatch,media_files):
    p,r,service,calls,creates,auth,_=await scenario(tmp_path,monkeypatch,media_files)
    cp=p.film.store.checkpoint(r);first=cp.units[0].generation_run_id;package=p.production_packages.get(cp.units[0].package_ref)
    await finish(p,first,package.artifact_reference())
    original=p.generation_artifacts.get(p.generation_artifacts.prepared(first),GenerationPreparation).model_dump_json()
    task=await following(p,r,service,first,1)
    # Controlled-live semantics, but the adapter still uses only in-process MockTransport.
    p.execution.transports['seedance'].offline=False
    child=p.create_media_review_run(package_ref=package.artifact_reference(),task=task)
    ids=p.queue_source_film_media(r,tasks=(task,))
    run=await p.runtime.run(child.run_id)
    if run.cursor==2:
        await p.decide_target_run(child.run_id,decision_id=p.runtime.decision_id(child.run_id),accepted=True,source_ref=package.artifact_reference())
        run=await p.runtime.run(child.run_id)
    await approve_mock_cost(p,r,child.run_id)
    op,check,media=completion(p,child.run_id)
    rights_key='rights:'+task.owners.rights_decision_ref.artifact_ref
    original_rights_grant=p.ledger.get_index('execution-live-grant',rights_key)
    context=p.execution.review_context(op,media.media,media.canonical_media_ref)
    await p.provide_human_media_review(child.run_id,media_ref=check.progress.video_ref,context_hash=context,response=ReviewResponse('REVISE',(
        ReviewObservation(code='UNMOTIVATED_MOVE',finding='Observed movement lacks a beat trigger.',owner='cinematography',required_revision='Specify phase camera trigger.'),)))
    await p.resume_source_film_run(r)
    failed_review=p.execution.store.get(p.execution.store.checkpoint(op.artifact_reference()).progress.video_creative_ref,CreativeMediaReview).model_dump_json()
    # A Provider prompt-size refusal is retained, and does not create a paid task.
    verbose=camera_binding(p,r,package,task,verbose=True)
    await p.revise_source_film_segment(r,slot=0,task=verbose)
    preflight=p.film.store.checkpoint(r).scene_media_run_ids[0]
    assert p.runtime.store.load(r).state==RuntimeState.FAILED
    assert p.runtime.store.load(preflight).state==RuntimeState.FAILED
    assert p.runtime.store.load(preflight).cursor==2 and len(creates)==2
    previous=p.generation_artifacts.inputs(preflight).task
    revised=camera_binding(p,r,package,previous)
    await p.revise_source_film_segment(r,slot=0,task=revised)
    new=p.film.store.checkpoint(r).scene_media_run_ids[0]
    assert new!=child.run_id and len(creates)==2
    assert p.runtime.store.load(preflight).state==RuntimeState.FAILED
    assert p.runtime.store.load(r).external_repairs[-1].revision_ref is not None
    # Also reproduce and repair the historical bug: missing revised-intent binding,
    # already consumed predecessor Rights, and no dispatch before the refusal.
    with p.ledger.transaction(write=True) as db:
        db.execute("DELETE FROM ledger_index WHERE index_type='film-segment-dispatch-revision' AND index_key=?",(new,))
    await approve_mock_cost(p,r,new)
    assert p.runtime.store.load(r).state==RuntimeState.FAILED and len(creates)==2
    assert p.runtime.store.load(r).last_result.code=='FINANCIAL_AUTHORITY_ALREADY_CONSUMED'
    transport=p.execution.transports['seedance'];native_submit=transport.submit
    async def stale_read_only_transport(operation,attempt,request):
        transport.submit=native_submit
        transport.recovery_operation_ref=operation.artifact_reference()
        return await native_submit(operation,attempt,request)
    transport.submit=stale_read_only_transport
    await p.resume_source_film_run(r)
    assert p.runtime.store.load(r).state==RuntimeState.FAILED and len(creates)==2
    assert p.runtime.store.load(r).last_result.code=='RECOVERY_TRANSPORT_READ_ONLY'
    transport.recovery_operation_ref=None
    await p.resume_source_film_run(r)
    assert len(creates)==3 and p.runtime.store.load(r).state!=RuntimeState.FAILED
    assert p.ledger.get_index('execution-live-grant',rights_key)==original_rights_grant
    new_task=p.generation_artifacts.inputs(new).task
    assert new_task.unit==task.unit and new_task.continuation==task.continuation
    assert new_task.continuation.frame_ref==task.continuation.frame_ref
    compiled=await p.prompt_compiler.compile(package.artifact_reference(),new_task)
    assert compiled.preparation_ref,p.generation_artifacts.diagnostics(compiled.diagnostics_ref)
    prep=p.generation_artifacts.get(compiled.preparation_ref,GenerationPreparation)
    final=p.generation_artifacts.get(prep.final_prompt_ref,FinalPromptArtifact)
    wire=TargetHttpTransport.preview(prep,final,ledger=p.ledger)
    assert 'Only when the eyes soften' in wire['content'][0]['text']
    assert 'CURRENT SEGMENT, inherited camera state' in wire['content'][0]['text']
    assert 'BACKGROUND ONLY, already completed' in wire['content'][0]['text']
    assert 'Wide establishing view, then push closer.' not in wire['content'][0]['text']
    assert wire['return_last_frame'] and wire['content'][1]['role']=='first_frame'
    assert not await p.prompt_compiler.validate_execution_sources(compiled.preparation_ref)
    p.create_media_review_run(package_ref=package.artifact_reference(),task=new_task)
    await p.resume_source_film_run(r)
    if p.runtime.store.load(new).cursor==2:
        await p.decide_target_run(new,decision_id=p.runtime.decision_id(new),accepted=True,source_ref=package.artifact_reference())
    await p.resume_source_film_run(r)
    assert len(creates)==3
    assert 'Only when the eyes soften' in creates[-1]['content'][0]['text']
    assert creates[-1]['content'][1]['image_url']['url']=='https://result.invalid/tail-0.jpg'
    await p.revise_source_film_segment(r,slot=0,task=revised)
    assert len(creates)==3 and p.film.store.checkpoint(r).scene_media_run_ids==(new,)
    assert p.generation_artifacts.get(p.generation_artifacts.prepared(first),GenerationPreparation).model_dump_json()==original
    assert p.execution.store.get(p.execution.store.checkpoint(op.artifact_reference()).progress.video_creative_ref,CreativeMediaReview).model_dump_json()==failed_review
