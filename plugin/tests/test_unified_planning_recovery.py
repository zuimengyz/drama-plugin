"""Source planning uses approved typed facts, no network, no fabricated dialogue."""
import socket
import pytest
from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.creative_engine.contracts import SourceBody, WorkBody, ScriptBody, SceneBody, ShotBody, DesignBody, Kind
from drama_plugin.film.contracts import FilmCanon, FilmDirection, CanonScene, DirectedShot, LanguageMetadata, DeliveryProfile
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeState, RecoveryClass, CapabilityInput, ResultStatus
from drama_plugin.generation.contracts import GenerationPreparation, AudioExecutionPlan

REF = ArtifactReference(owner="source-owner",artifact_ref="offline-language-metadata",version=1)
DOMAINS = tuple(sorted(("ACTION","CAMERA","COLOR","EDITORIAL","LIGHTING","PERFORMANCE","REFERENCE","SOUND","SUBJECTS","WORLD")))

class StructuredAuthors:
    def __init__(self): self.calls=[]
    async def author_film(self, request):
        self.calls.append("canon")
        return FilmCanon(work=WorkBody(interpretation="Observe a bounded source action.",dramatic_intent="The approved state changes.",character_meaning="The authored action remains legible."),
            script=ScriptBody(screenplay="An approved silent action is completed."),scenes=(CanonScene(scene_id="native-scene",scene=SceneBody(scene_text="An actor traverses the approved space.")),))
    async def direct_film(self, request):
        self.calls.append("direction")
        return FilmDirection(shots=(DirectedShot(scene_id="native-scene",shot_id="native-shot",shot=ShotBody(
            purpose="Observe the approved state",required_transition="The approved gesture ends",duration_ms=60000,
            subject_action="Actor completes an approved gesture",entry_state="Before the gesture",exit_state="After the gesture",
            coverage="One approved state change",blocking_intent="Keep the action visible",camera_intent="Observe the action",
            editing_relation="Hold the approved action",performance_direction="Maintain authored intention",professional_domains=DOMAINS)),))
    async def author(self, request):
        raise AssertionError("Fixed film Canon/Direction must not run again")
    async def design(self, request):
        self.calls.append("professional")
        direction={"objective":"Complete the approved gesture","interactionTarget":"Approved space","tactic":"Maintain authored movement",
            "authorityPosition":"Self-directed","relationshipStance":"No invented exchange","internalActivation":"LOW","externalControl":"HIGH","publicPrivateContext":"Public space"}
        facts={
            "ACTION":{"actionPhases":[{"beatId":"beat-1","action":"The actor completes the approved gesture.","entryState":"The gesture has not begun.","observable":"The gesture has completed.","spokenIds":[]}],"physicalStateConstraints":["Preserve the approved action."]},
            "CAMERA":{"movement":{"policy":"The camera remains fixed."},"pointOfView":"Observe the approved action."},
            "WORLD":{"setting":"Approved open space."},
            "SUBJECTS":{"presentSubjects":[{"id":"actor","role":"Approved actor.","inSceneBehaviour":"Complete the approved gesture."}]},
            "SOUND":{"ambience":[{"design":"Quiet source ambience."}],"orderingRules":["No added speech."]},
            "LIGHTING":{"sources":["Approved visible source."],"directionAndQuality":["Soft directional light."]},
            "COLOR":{"scenePalette":["Muted authored colors."]},"EDITORIAL":{"temporalStructure":"Hold through the approved gesture."},
            "REFERENCE":{"references":[]},
            "PERFORMANCE":{"sceneDPD":{"dramaticPurpose":"Complete the authored transition.","conflictCondition":"No invented conflict.","powerStructure":"Self-directed action.","direction":direction},
                "beats":[{"id":"beat-1","actor":"actor","target":"Approved space","objective":"Complete the approved gesture","obstacle":"No additional obstacle.","tactic":"Maintain movement.","note":"Only the approved action.","transitionTrigger":"The gesture completes.","direction":{"objective":"Complete the approved gesture."},"physicalExpression":"Maintain the authored movement."}],
                "lines":[],"projectionSubjects":[{"subjectRef":"actor","sourceTargetLabel":"Approved actor","role":"INTERACTIVE_PARTNER","beatIds":["beat-1"],"spokenIds":[],"objectives":["Complete approved gesture"]}]}}
        return tuple(DesignBody(domain=d,facts=facts[d]) for d in DOMAINS)


def load(tmp_path, monkeypatch, authors=None):
    def no_network(*args,**kwargs): raise AssertionError("No real network in planning recovery")
    monkeypatch.setattr(socket.socket,"connect",no_network)
    monkeypatch.setattr(socket.socket,"connect_ex",no_network)
    monkeypatch.setattr("drama_plugin.plugin.load_config",lambda _:DramaPluginConfig())
    a=authors or StructuredAuthors()
    p=DramaPlugin.load(mock_data=MockDramaData.empty(),ledger_path=tmp_path/"ledger.sqlite",creative_root=tmp_path/"owners",
        target_media_root=tmp_path/"cache",canon_author=a,direction_author=a,professional_author=a,film_canon_author=a,film_direction_author=a)
    return p,a


def create(p,run_id="native-film"):
    return p.create_source_film_run(work_id="native-work",run_id=run_id,source=SourceBody(goal="A bounded offline film",text="Designated source action.",spoken_language="ru"),
        languages=LanguageMetadata(source_document_language="en",original_work_language="ru",spoken_language="ru",authority_ref=REF),
        profile=DeliveryProfile(width=1280,height=720,audio_required=False),rights_refs=(REF,),route="seedance",model="seedance-2-fast")


@pytest.mark.asyncio
async def test_empty_source_adoption_silent_dpd_native_rights_request(tmp_path,monkeypatch):
    p,a=load(tmp_path,monkeypatch)
    run=create(p); run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER, run.model_dump()
    cp=p.film.store.checkpoint(run.run_id)
    assert run.cursor==3 and cp.plan_ref and a.calls==["canon","direction","professional"]
    assert p.providers.memory.data.work is None
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=cp.plan_ref)
    run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER and run.cursor==5,run.model_dump()
    assert run.last_result.recovery_class==RecoveryClass.USER_DECISION
    request,ref=p.film.pending_decision(run.run_id)
    assert ref.owner=="source-owner" and "source-rights-request:" in ref.artifact_ref
    cp=p.film.store.checkpoint(run.run_id)
    assert cp.rights_decision_ref is None and cp.operation_task is None
    package=p.production_packages.get(cp.units[0].package_ref)
    assert package.generation_intent.duration_ms==60000
    dpd_pin,scope_pin,snapshots=p.operation_resolver.compose_performance(cp.units[0].refs)
    assert snapshots==()
    body=p.creative_versions.objects.read_ref(dpd_pin)
    assert body["fullShotDPDCoverage"]["status"]=="PASS" and len(body["beatBindings"])==1
    assert body["snapshotBindings"]==[]
    assert a.calls==["canon","direction","professional"]
    restored,a2=load(tmp_path,monkeypatch)
    recovered=await restored.runtime.recover_run(run.run_id)
    assert recovered.state==RuntimeState.WAITING_USER
    assert restored.film.pending_decision(run.run_id)==(request,ref) and not a2.calls
    before=restored.film.store.checkpoint(run.run_id)
    restored.film.store.bind(run.run_id,recovered.scope,restored.film.store.input(run.run_id))
    assert restored.film.store.checkpoint(run.run_id)==before


@pytest.mark.asyncio
async def test_direction_postvalidation_never_publishes_invalid_owner(tmp_path,monkeypatch):
    class Bad(StructuredAuthors):
        async def direct_film(self,request):
            self.calls.append("direction")
            value=await super().direct_film(request)
            return value.model_copy(update={"shots":(value.shots[0].model_copy(update={"scene_id":"wrong-scene"}),)})
    p,a=load(tmp_path,monkeypatch,Bad())
    run=create(p);run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.FAILED and run.cursor==1,run.model_dump()
    assert a.calls.count("canon")==1
    assert p.film.store.author_ref(run.run_id,"film-direction") is None
    assert p.film.store.checkpoint(run.run_id).direction_ref is None
    diagnostic=next(ref for ref in run.last_result.artifact_refs if ref.owner=="creative-diagnostic")
    body=p.creative_versions.objects.read_ref(__import__('drama_plugin.contracts.source_pin',fromlist=['SourcePin']).SourcePin(key=diagnostic.artifact_ref,kind="CANON",fingerprint=diagnostic.artifact_ref.split(':')[1]))
    assert body["diagnostic"]["code"]=="FILM_DIRECTION_SCENE_COVERAGE"
    assert body["diagnostic"]["recovery_class"]=="RETRY_SAME_STEP"

async def adopt_to_rights(p):
    run=create(p);run=await p.runtime.run(run.run_id)
    cp=p.film.store.checkpoint(run.run_id)
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=cp.plan_ref)
    run=await p.runtime.run(run.run_id)
    ref=p.film.pending_decision(run.run_id)[1]
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=ref)
    return run.run_id

@pytest.mark.asyncio
async def test_current_cost_input_wait_never_fabricates_quote_or_authorization(tmp_path,monkeypatch):
    from test_unified_mainline import MediaService
    p,a=load(tmp_path,monkeypatch)
    p.providers.media=MediaService(tmp_path/'unused.mp4').provider()
    run_id=await adopt_to_rights(p)
    result=await p.runtime.run(run_id)
    assert result.state==RuntimeState.WAITING_EXTERNAL and result.last_result.recovery_class==RecoveryClass.WAIT_EXTERNAL
    assert result.last_result.external_ref.owner=='generation-preparation'
    child_id=next(ref.artifact_ref for ref in result.last_result.artifact_refs if ref.owner=='runtime')
    prepared=p.generation_artifacts.get(p.generation_artifacts.prepared(child_id),GenerationPreparation)
    plan=p.generation_artifacts.get(prepared.audio_plan_ref,AudioExecutionPlan)
    ir=await p.prompt_compiler.prompt_ir(prepared)
    assert ir.duration_ms==plan.duration_ms==4000 and plan.native_audio_policy=='DISABLED' and plan.source_roles==()
    assert not any(f.slot=='video.audio_requirements' for f in ir.facts)
    assert a.calls==['canon','direction','professional']
    with p.ledger.transaction() as db:
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='execution-operation'").fetchone()[0]==0
        assert db.execute("SELECT count(*) FROM ledger_index WHERE index_type IN ('media-proof-cost-terms','media-proof-authorization')").fetchone()[0]==0

@pytest.mark.asyncio
async def test_required_reference_real_scope_choice_and_optional_no_gate(tmp_path,monkeypatch):
    from test_unified_mainline import MediaService
    class ReferenceAuthors(StructuredAuthors):
        async def design(self,request):
            designs=await super().design(request)
            return tuple(d.model_copy(update={'facts':{'references':[
                {'id':'required-proof','priority':'REQUIRED','beatIds':['beat-1'],'designPurpose':'Verify approved state.','inputDuty':'REFERENCE'},
                {'id':'preferred-proof','priority':'PREFERRED','beatIds':['beat-1'],'designPurpose':'Support quality.','inputDuty':'REFERENCE'}]}}) if d.domain=='REFERENCE' else d for d in designs)
    p,a=load(tmp_path,monkeypatch,ReferenceAuthors());p.providers.media=MediaService(tmp_path/'unused.mp4').provider()
    run_id=await adopt_to_rights(p);result=await p.runtime.run(run_id)
    assert result.state==RuntimeState.WAITING_USER and result.last_result.user_decision.category.value=='ART_APPROVAL',result.model_dump_json()
    cp=p.film.store.checkpoint(run_id)
    assert dict(cp.operation_task.unit.reference_disposition)=={'required-proof':'TECHNICAL_RISK_ACCEPTED','preferred-proof':'OPTIONAL_OMITTED'}
    package=p.production_packages.get(cp.units[0].package_ref)
    malicious=cp.operation_task.model_copy(update={'unit':cp.operation_task.unit.model_copy(update={'reference_disposition':(('required-proof','OPTIONAL_OMITTED'),('preferred-proof','OPTIONAL_OMITTED'))})})
    with pytest.raises(ValueError,match='REFERENCE_REQUIRED_DISPOSITION_INVALID'):
        await p.operation_resolver.selected(package,malicious,p.prompt_compiler.reader)
    malicious=cp.operation_task.model_copy(update={'unit':cp.operation_task.unit.model_copy(update={'reference_disposition':(('required-proof','OUT_OF_UNIT'),('preferred-proof','OPTIONAL_OMITTED'))})})
    with pytest.raises(ValueError,match='REFERENCE_OUT_OF_UNIT_UNPROVEN'):
        await p.operation_resolver.selected(package,malicious,p.prompt_compiler.reader)
    assert a.calls==['canon','direction','professional']

@pytest.mark.asyncio
async def test_fixed_film_author_owner_index_recovers_without_new_completion(tmp_path,monkeypatch):
    p,a=load(tmp_path,monkeypatch)
    run=create(p);run=await p.runtime.run(run.run_id)
    cp=p.film.store.checkpoint(run.run_id)
    for owner in ('film-canon','film-direction'):
        p.creative_versions._path('film-author',[run.run_id,owner]).unlink()
    p2,a2=load(tmp_path,monkeypatch)
    assert p2.film.store.author_ref(run.run_id,'film-canon')==cp.canon_ref
    assert p2.film.store.author_ref(run.run_id,'film-direction')==cp.direction_ref
    assert not a2.calls

@pytest.mark.asyncio
async def test_planning_cost_choice_is_exact_recoverable_and_never_dispatch_grant(tmp_path,monkeypatch):
    p,a=load(tmp_path,monkeypatch)
    run=p.create_source_film_run(work_id="native-work",run_id="planning-choice",source=SourceBody(goal="A bounded offline film",text="Designated source action.",spoken_language="ru"),
        languages=LanguageMetadata(source_document_language="en",original_work_language="ru",spoken_language="ru",authority_ref=REF),
        profile=DeliveryProfile(width=1280,height=720,audio_required=False),rights_refs=(REF,),route="seedance",model="seedance-2-fast",
        max_cost_microunits=1,estimated_shot_cost_microunits=2)
    run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER and run.cursor==1
    cp=p.film.store.checkpoint(run.run_id)
    request,target=p.film.pending_decision(run.run_id)
    assert request.category.value=="COST_APPROVAL" and target==cp.direction_ref
    assert a.calls==["canon","direction"] and cp.graph.cost_limit==2
    p2,a2=load(tmp_path,monkeypatch)
    assert p2.film.pending_decision_terms(run.run_id)==p.film.pending_decision_terms(run.run_id)
    await p2.decide_target_run(run.run_id,decision_id=p2.runtime.decision_id(run.run_id),accepted=True,source_ref=target)
    run=await p2.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER and run.cursor==3,run.model_dump()
    cp=p2.film.store.checkpoint(run.run_id)
    assert cp.planning_cost_decision_ref and cp.adoption_ref is None and cp.operation_task is None
    assert a2.calls==["professional"]
    with p2.ledger.transaction() as db:
        assert db.execute("SELECT count(*) FROM immutable_artifact WHERE artifact_type='execution-operation'").fetchone()[0]==0


@pytest.mark.asyncio
async def test_resolved_disabled_audio_cannot_silently_drop_required_speech_or_policy(tmp_path,monkeypatch):
    from pydantic import ValidationError
    from drama_plugin.generation.contracts import GenerationTask
    p,a=load(tmp_path,monkeypatch)
    run_id=await adopt_to_rights(p)
    await p.runtime.run(run_id)
    task=p.film.store.checkpoint(run_id).operation_task
    assert task and task.profile.native_audio is False and task.unit.spoken_ids==()
    value=task.model_dump()
    value["unit"]["spoken_ids"]=("spoken-1",)
    with pytest.raises(ValidationError,match="REQUEST_UNSUPPORTED_REQUIRED_SPEECH"):
        GenerationTask.model_validate(value)
    value=task.model_dump()
    value["native_audio"]="REQUIRED"
    with pytest.raises(ValidationError,match="Task/profile conflict"):
        GenerationTask.model_validate(value)

@pytest.mark.asyncio
async def test_film_graph_failure_retries_exact_step_before_owner_publication(tmp_path,monkeypatch):
    class Corrected(StructuredAuthors):
        async def direct_film(self,request):
            result=await super().direct_film(request)
            if self.calls.count('direction')==1:
                return result.model_copy(update={'shots':(result.shots[0].model_copy(update={'requires':('missing-child',)}),)})
            return result
    p,a=load(tmp_path,monkeypatch,Corrected())
    run=create(p);run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER and run.cursor==3,run.model_dump()
    assert a.calls==['canon','direction','direction','professional']
    cp=p.film.store.checkpoint(run.run_id)
    assert cp.direction_ref and cp.plan_ref and cp.graph
    assert p.film.store.author(cp.direction_ref,FilmDirection).shots[0].requires==()

@pytest.mark.asyncio
@pytest.mark.parametrize('corrected',[True,False])
async def test_film_child_author_retry_is_driven_or_exactly_exhausted_without_fake_wait(tmp_path,monkeypatch,corrected):
    class BadProfessional(StructuredAuthors):
        async def design(self,request):
            designs=await super().design(request)
            if not corrected or self.calls.count('professional')==1:
                return designs[:-1]
            return designs
    p,a=load(tmp_path,monkeypatch,BadProfessional())
    run=create(p);run=await p.runtime.run(run.run_id)
    assert a.calls==['canon','direction'] + ['professional'] * (2 if corrected else 5)
    cp=p.film.store.checkpoint(run.run_id)
    child=p.runtime.store.load(cp.units[0].creative_run_id)
    assert next(ref.artifact_ref for ref in run.last_result.artifact_refs if ref.owner=='runtime')==child.run_id if not corrected else True
    if corrected:
        assert run.state==RuntimeState.WAITING_USER and run.cursor==3
    else:
        assert run.state==RuntimeState.FAILED and run.last_result.recovery_class==RecoveryClass.HARD_BLOCK
        assert run.last_result.code==child.last_result.code=='RETRY_LIMIT_REACHED'
        assert run.last_result.external_ref is None and cp.plan_ref is None
        assert child.step_attempts == child.step_retry_limit == 5
        calls=a.calls[:]
        assert (await p.runtime.run(run.run_id)) == run
        assert a.calls == calls

@pytest.mark.asyncio
async def test_stale_adopted_owner_requires_exact_new_scope_not_boolean_approval(tmp_path,monkeypatch):
    from drama_plugin.creative_engine.contracts import Authority
    p,a=load(tmp_path,monkeypatch)
    run=create(p);run=await p.runtime.run(run.run_id)
    cp=p.film.store.checkpoint(run.run_id)
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=cp.plan_ref)
    run=await p.runtime.run(run.run_id)
    cp=p.film.store.checkpoint(run.run_id);old_package=cp.units[0].package_ref
    target=next(p.creative_versions.resolve(r) for r in cp.units[0].refs if p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL)
    p.creative_versions.invalidate(target.ref())
    run=await p.runtime.reconcile_wait(run.run_id)
    assert run.state==RuntimeState.WAITING_USER and run.cursor==5
    request,exact=p.film.pending_decision(run.run_id)
    assert request.category.value=='ART_APPROVAL' and exact==old_package
    assert target.ref().runtime_ref() in run.last_result.artifact_refs
    with pytest.raises(ValueError,match='boolean cannot approve stale authority'):
        await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=exact)
    assert p.film.store.checkpoint(run.run_id).units[0].package_ref==old_package
    assert a.calls==['canon','direction','professional']

@pytest.mark.asyncio
async def test_exact_adopted_owner_revision_replaces_only_affected_package(tmp_path,monkeypatch):
    from drama_plugin.creative_engine.contracts import Authority,RevisionRequest
    class Revising(StructuredAuthors):
        async def revise(self,request): return await self.design(request)
    p,a=load(tmp_path,monkeypatch,Revising())
    from test_unified_mainline import MediaService
    p.providers.media=MediaService(tmp_path/'unused.mp4').provider()
    run=create(p);run=await p.runtime.run(run.run_id)
    cp=p.film.store.checkpoint(run.run_id)
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=cp.plan_ref)
    run=await p.runtime.run(run.run_id)
    cp=p.film.store.checkpoint(run.run_id);old=cp.units[0]
    target=next(p.creative_versions.resolve(r) for r in old.refs if p.creative_versions.resolve(r).kind==Kind.PROFESSIONAL)
    p.creative_versions.invalidate(target.ref())
    run=await p.runtime.reconcile_wait(run.run_id)
    revision=p.create_creative_revision_run(old.production_run_id,RevisionRequest(owner=Authority.PROFESSIONAL,target_ref=target.ref(),
        finding_ref=run.last_result.artifact_refs[0],instruction='Revise only the exact professional dependency under its original owner.',depth=1),run_id='exact-owner-revision')
    revision=await p.runtime.run(revision.run_id)
    assert revision.state==RuntimeState.WAITING_USER,revision.model_dump()
    fixed=p.creative.state.checkpoint(revision.run_id)
    await p.decide_target_run(revision.run_id,decision_id=p.runtime.decision_id(revision.run_id),accepted=True,source_ref=fixed.candidate_ref)
    revision=await p.runtime.run(revision.run_id)
    assert revision.state==RuntimeState.SUCCEEDED,revision.model_dump()
    run=await p.film.provide_creative_revision_result(run.run_id,revision.run_id)
    assert run.state==RuntimeState.READY and run.cursor==5
    run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_USER,run.model_dump()
    new=p.film.store.checkpoint(run.run_id)
    assert new.units[0].package_ref!=old.package_ref and p.production_packages.get(old.package_ref)
    assert new.units[0].production_run_id==revision.run_id and new.units[0].revision_depth==1
    assert new.rights_decision_ref is None and new.operation_task is None
    assert p.film.pending_decision(run.run_id)[0].category.value=='ADOPTION'
    assert a.calls==['canon','direction','professional','professional']
    revised=next(p.creative_versions.resolve(ref) for ref in new.units[0].refs if p.creative_versions.resolve(ref).kind==Kind.PROFESSIONAL)
    p.operation_resolver.validate_independent_adoption(revised,p.runtime.store.load(revision.run_id).scope)
    borrowed=revised.model_copy(update={"adoption_decision_ref":new.adoption_ref})
    with pytest.raises(ValueError,match="PROFESSIONAL_ADOPTION_CANDIDATE_MISMATCH"):
        p.operation_resolver.validate_independent_adoption(borrowed,p.runtime.store.load(revision.run_id).scope)
    request,target=p.film.pending_decision(run.run_id)
    await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=target)
    run=await p.runtime.run(run.run_id)
    assert run.state==RuntimeState.WAITING_EXTERNAL and run.last_result.external_ref.owner=='generation-preparation',run.model_dump()
    task=p.film.store.checkpoint(run.run_id).operation_task
    p.operation_resolver.validate(p.production_packages.get(new.units[0].package_ref),task)

@pytest.mark.asyncio
async def test_native_v2_derived_maintenance_keeps_cursor_then_compiles(tmp_path,monkeypatch):
    from test_unified_mainline import MediaService
    from drama_plugin.generation.contracts import GenerationInput
    from drama_plugin.generation.policy import MEDIA_WORKFLOW
    from drama_plugin.governance.contracts import GovernanceInput
    from drama_plugin.governance.policy import MAINTAIN
    from drama_plugin.production.contracts import AssemblyValidation,AssemblyIssue,AssemblyIssueCode,SourceDomain,SourceOwner
    p,a=load(tmp_path,monkeypatch);p.providers.media=MediaService(tmp_path/'unused.mp4').provider()
    run_id=await adopt_to_rights(p)
    parent=await p.runtime.run(run_id)
    cp=p.film.store.checkpoint(run_id);task=cp.operation_task;package=cp.units[0].package_ref
    scope=p.production_packages.get(package).scope
    from drama_plugin.runtime.contracts import RuntimeScope,RunMode
    runtime_scope=RuntimeScope(work_id=scope.work.artifact_ref,scene_id=scope.scene.artifact_ref,shot_id=scope.shot.artifact_ref)
    # Fault-injection fixture uses only a separate test Run and the exact existing
    # owner inputs; it does not edit a formal workflow/checkpoint.
    draft=p.runtime.draft_run(work_id=runtime_scope.work_id,scene_id=runtime_scope.scene_id,shot_id=runtime_scope.shot_id,
        mode=RunMode.PRODUCTION,workflow_id=MEDIA_WORKFLOW,run_id='derived-maintenance-native-v2')
    injected=p.ledger.create_target_run(draft,GovernanceInput(package_ref=package),GenerationInput(task=task))
    validate=p.shot_assembler.validate_sources
    validations=0
    async def one_stale_projection(current):
        nonlocal validations
        validations+=1
        if validations==1:
            return AssemblyValidation(status='UNRESOLVED',issues=(AssemblyIssue(code=AssemblyIssueCode.VERSION_MISMATCH,
                domain=SourceDomain.DIRECTION,owner=SourceOwner.DIRECTION,artifact_ref=current.scope.shot.artifact_ref),))
        return await validate(current)
    monkeypatch.setattr(p.shot_assembler,'validate_sources',one_stale_projection)
    calls=[];execute=p.runtime.executor.execute
    async def observe(key,inputs):
        calls.append((key,p.runtime.store.load(inputs.run_id).cursor))
        return await execute(key,inputs)
    monkeypatch.setattr(p.runtime.executor,'execute',observe)
    result=await p.runtime.run(injected.run_id)
    assert result.state==RuntimeState.WAITING_EXTERNAL and result.last_result.external_ref.owner=='generation-preparation'
    assert ('generation.rebuild:v1',1) not in calls  # ASSESS maintenance is owned by Governance.
    assert (MAINTAIN,1) in calls and ('generation.compile:v1',1) in calls,calls
    assert p.generation_artifacts.prepared(injected.run_id)
    assert a.calls==['canon','direction','professional']
