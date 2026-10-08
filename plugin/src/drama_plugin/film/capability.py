"""Film domain actions. The existing Runtime drives every parent and child workflow."""
from __future__ import annotations
from typing import TYPE_CHECKING
from collections.abc import Awaitable, Callable
from pydantic import TypeAdapter, ValidationError
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.generation.operation import resolve_profile
from drama_plugin.creative_engine.contracts import Authority, Kind, RouteRequest, DependencyTask, RoutePlan, SourceBody, VersionRef
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure, AuthorUnavailable, run_author_capability, failure
from drama_plugin.execution.contracts import ReviewedAVCandidate, CreativeMediaReview, ExecutionOperation
from drama_plugin.execution.transport import CapabilityAbsent
from drama_plugin.film.assembly import assemble, final_qa, validate_cues
from drama_plugin.film.contracts import (FilmAuthorRequest, FilmCanon, FilmDirection, FilmPlan, FilmCheckpoint, ShotUnit, SubtitleCue,
    FilmShotBinding, FinalFilmCandidate, FinalTechnicalQA, FinalCreativeReview, FinalDelivery, FilmRevisionFeedback)
from drama_plugin.film.ports import FilmCanonAuthor, FilmDirectionAuthor, FilmReviewer, ExecutionRecipeSource
from drama_plugin.film.store import FilmStore
from drama_plugin.generation.contracts import GenerationPreparation, GenerationTask, OwnerBindings
from drama_plugin.generation.policy import MEDIA_WORKFLOWS, media_cursor
from drama_plugin.governance.contracts import GateCode, GateFinding
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.runtime.policy import AUTHOR_CONTENT_ATTEMPT_LIMIT
from drama_plugin.runtime.capabilities import TargetCapability
from drama_plugin.runtime.contracts import (ArtifactReference, CapabilityInput, CapabilityResult, DecisionCategory,
    ResultStatus, RunMode, RuntimeScope, RuntimeState, RuntimeRun, RecoveryClass, UserDecisionRequest, ExecutionInspection, ExecutionRevision)
if TYPE_CHECKING:
    from drama_plugin.plugin import DramaPlugin

REVISION_WORKFLOW = 'final-film-revision:v1'
REVISION_KEYS = ('execute','assemble','review','decision','deliver')
KEYS = ('canon','direction','prepare','decision','adopt','execute','assemble','review','decision','deliver')
WORKFLOW = 'source-to-final-film:v1'
MEDIA_WORKFLOW = 'source-to-reviewed-media:v1'
MEDIA_KEYS = ('canon','direction','prepare','decision','adopt','execute')

class FilmCapabilities:
    def __init__(self, plugin: DramaPlugin, store: FilmStore, *, canon: FilmCanonAuthor | None = None,
                 direction: FilmDirectionAuthor | None = None, reviewer: FilmReviewer | None = None,
                 recipes: ExecutionRecipeSource | None = None):
        self.plugin, self.store = plugin, store
        self.canon_author, self.direction_author = canon, direction
        self.reviewer, self.recipes = reviewer, recipes
    def registrations(self) -> dict[str, TargetCapability]:
        methods = {'canon':self.canon,'direction':self.direction,'prepare':self.prepare,'decision':self.decision,
            'adopt':self.adopt,'execute':self.execute,'assemble':self.assemble,'review':self.review,'deliver':self.deliver}
        inspectors={'canon':self.inspect_canon_execution,'direction':self.inspect_direction_execution,'execute':self.inspect_media_execution}
        return {'film.'+key+':v1':TargetCapability(self.guard(method), replay_safe=True,inspect_execution=inspectors.get(key)) for key,method in methods.items()}
    def _author_inspection(self, inputs: CapabilityInput, role: str, fingerprint: str) -> ExecutionInspection:
        value,cp=self.store.input(inputs.run_id),self.store.checkpoint(inputs.run_id)
        if self.plugin.creative_versions.stale(value.source_ref):
            raise ValueError("CREATIVE_EXECUTION_INPUT_STALE")
        authoritative={"sourceRef":value.source_ref.model_dump(mode="json",by_alias=True),
            "filmInput":value.model_dump(mode="json",by_alias=True),"scope":inputs.scope.model_dump(mode="json",by_alias=True)}
        if role=='direction':
            if cp.canon_ref is None:
                raise ValueError("DIRECTION_CANON_PREREQUISITE_ABSENT")
            self.store.author(cp.canon_ref,FilmCanon)
            authoritative["canonRef"]=cp.canon_ref.model_dump(mode="json",by_alias=True)
        fixed=cp.canon_ref if role=='canon' else cp.direction_ref
        return ExecutionInspection(revision=ExecutionRevision(fingerprint=fingerprint,input_fingerprint=sha256_canonical(authoritative)),
            retry_limit=AUTHOR_CONTENT_ATTEMPT_LIMIT,
            completed=fixed is not None or self.plugin.creative_versions.has_author_output(inputs.operation_id,role))
    def inspect_canon_execution(self, inputs: CapabilityInput) -> ExecutionInspection | None:
        from drama_plugin.creative_engine.backends import FormalCanonAuthor
        return self._author_inspection(inputs,'canon',self.canon_author.execution_fingerprint(film=True)) if isinstance(self.canon_author,FormalCanonAuthor) else None
    def inspect_direction_execution(self, inputs: CapabilityInput) -> ExecutionInspection | None:
        from drama_plugin.creative_engine.backends import FormalDirectionAuthor
        return self._author_inspection(inputs,'direction',self.direction_author.execution_fingerprint(film=True)) if isinstance(self.direction_author,FormalDirectionAuthor) else None
    def inspect_media_execution(self, inputs: CapabilityInput) -> ExecutionInspection | None:
        run=self.plugin.runtime.store.load(inputs.run_id)
        if run.workflow_id!=MEDIA_WORKFLOW:
            return None
        cp=self.store.checkpoint(inputs.run_id)
        value=self.store.input(inputs.run_id)
        refs=[ref.model_dump(mode="json",by_alias=True) for unit in cp.units for ref in unit.refs]
        identity={"filmInput":value.model_dump(mode="json",by_alias=True),"refs":refs,
            "planRef":cp.plan_ref.model_dump(mode="json",by_alias=True) if cp.plan_ref else None,
            "scope":inputs.scope.model_dump(mode="json",by_alias=True)}
        if cp.media_batch_ref:
            identity['mediaBatchRef'] = cp.media_batch_ref.model_dump(mode='json',by_alias=True)
        committed=False
        if cp.units and self.plugin.source_film_media_opening(inputs.run_id):
            child_id = (cp.scene_media_run_ids or (self.plugin.source_film_media_opening(inputs.run_id),))[-1]
            unit = self.plugin.source_film_unit_for_task(inputs.run_id,self.plugin.generation_artifacts.inputs(child_id).task)
            child=self.plugin.runtime.store.load(child_id)
            if child.workflow_id not in MEDIA_WORKFLOWS:
                raise ValueError("CHILD_PREPARATION_WORKFLOW_MISMATCH")
            # Compilation can still be waiting for scope approval at logical
            # cursors 4/5. Reaching READY (6) guarantees a preparation.
            # Earlier committed artifacts are checked too, but absence is normal.
            prepared=self.plugin.generation_artifacts.prepared(child.run_id,
                required=media_cursor(child.workflow_id,child.cursor)>=6)
            if prepared is not None:
                artifact=self.plugin.generation_artifacts.get(prepared,GenerationPreparation)
                from drama_plugin.generation.audio import package_scope
                if package_scope(self.plugin.production_packages.get(artifact.source_package_ref))!=child.scope or artifact.source_package_ref!=unit.package_ref:
                    raise ValueError("CHILD_PREPARATION_SCOPE_MISMATCH")
                committed=True
        return ExecutionInspection(revision=ExecutionRevision(
            fingerprint=sha256_canonical({"capability":"film.execute:v1","workflow":run.workflow_fingerprint,"owner":"TargetExecution/native-media-review",
                "preparationLifecycle":"child-stage-v1"}),
            input_fingerprint=sha256_canonical(identity)),completed=committed)
    def guard(self, handler: Callable[[CapabilityInput], Awaitable[CapabilityResult]]) -> Callable[[CapabilityInput], Awaitable[CapabilityResult]]:
        async def governed(inputs: CapabilityInput) -> CapabilityResult:
            run = self.plugin.runtime.store.load(inputs.run_id)
            if handler.__name__ in {"canon", "direction"}:
                return await run_author_capability(handler, role="canon" if handler.__name__ == "canon" else "direction",
                    versions=self.plugin.creative_versions, inputs=inputs, run=run,
                    version_refs=(self.store.input(inputs.run_id).source_ref,), author_round=run.step_attempts)
            try:
                return await handler(inputs)
            except CapabilityAbsent:
                return self.wait(inputs,'film-consumer-capability')
            except (ValueError, KeyError) as error:
                stable = str(error) if str(error) in {
                    "NATIVE_PERFORMANCE_CAPABILITY_ABSENT", "NATIVE_PERFORMANCE_CONTRACT_MISSING",
                    "NATIVE_OPERATION_UNIT_CAPABILITY_ABSENT", "NATIVE_OPERATION_UNIT_CONTRACT_MISSING",
                    "DPD_CANON_DIALOGUE_MISMATCH", "DPD_DUPLICATE_BEAT", "DPD_INPUT_NOT_ADOPTED",
                    "FILM_ROUTE_PROFILE_MISMATCH", "MEDIA_REVIEW_RECEIPT_MISSING",
                    "PERFORMANCE_SCOPE_UNAPPROVED", "PERFORMANCE_SCOPE_PARENT_MISMATCH",
                    "SHOT_BEAT_DPD_COVERAGE_MISMATCH", "SHOT_SPOKEN_DPD_COVERAGE_MISMATCH",
                    "REFERENCE_REQUIRED_DISPOSITION_INVALID", "REFERENCE_OUT_OF_UNIT_UNPROVEN",
                    "SCENE_CONTINUATION_SCOPE_MISMATCH"
                } else "FILM_AUTHORITY_OR_CONTRACT_INVALID"
                evidence=self.store.input(inputs.run_id).source_ref.runtime_ref()
                finding=GateFinding.classified(GateCode.CANON_AUTHORITY_MISMATCH,owner='film-contract',
                    scope=inputs.scope,evidence_ref=evidence,required=True)
                decision=self.plugin.gate_governor.govern((finding,),scope=inputs.scope,
                    mode=run.mode,package_ref=None)
                ref=self.plugin.gate_findings.put_decision(decision,run_id=inputs.run_id)
                return CapabilityResult(status=ResultStatus.FAILED,code=stable,artifact_refs=(ref,), recovery_class=RecoveryClass.HARD_BLOCK)
        return governed
    def success(self, cp: FilmCheckpoint) -> CapabilityResult:
        ref = cp.delivery_ref or cp.final_ref or cp.plan_ref or cp.direction_ref or cp.canon_ref
        return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(ref,) if ref else ())
    def save(self, inputs: CapabilityInput, **changes: object) -> FilmCheckpoint:
        cp = self.store.checkpoint(inputs.run_id)
        value = FilmCheckpoint.model_validate({**cp.model_dump(), **changes})
        self.store.save(inputs.run_id, inputs.scope, value)
        return value
    def wait(self, inputs: CapabilityInput, owner: str, evidence: ArtifactReference | None = None) -> CapabilityResult:
        value = self.store.input(inputs.run_id)
        ref = evidence or value.source_ref.runtime_ref()
        if self.plugin.runtime.store.load(inputs.run_id).workflow_id == MEDIA_WORKFLOW:
            return CapabilityResult(status=ResultStatus.FAILED, code='FILM_CAPABILITY_ABSENT', artifact_refs=(ref,), recovery_class=RecoveryClass.HARD_BLOCK)
        finding = GateFinding.classified(GateCode.CAPABILITY_NOT_IMPLEMENTED, owner=owner, scope=inputs.scope, evidence_ref=ref, required=True)
        decision = self.plugin.gate_governor.govern((finding,), scope=inputs.scope,
            mode=self.plugin.runtime.store.load(inputs.run_id).mode, package_ref=None)
        gate = self.plugin.gate_findings.put_decision(decision,run_id=inputs.run_id)
        return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, artifact_refs=(gate,),
            external_ref=ArtifactReference(owner=owner,artifact_ref=ref.artifact_ref,version=ref.version))
    def request(self, inputs: CapabilityInput) -> FilmAuthorRequest:
        value = self.store.input(inputs.run_id)
        source = self.plugin.creative_versions.resolve(value.source_ref)
        if source.scope != inputs.scope or not isinstance(source.body,SourceBody) or source.body.spoken_language != value.languages.spoken_language:
            raise ValueError('Source/Film language or scope mismatch')
        cp = self.store.checkpoint(inputs.run_id)
        return FilmAuthorRequest(scope=inputs.scope, source=source.body, languages=value.languages,source_ref=value.source_ref,
            canon=self.store.author(cp.canon_ref,FilmCanon) if cp.canon_ref else None,
            production_goal="MEDIA_REVIEW" if self.plugin.runtime.store.load(inputs.run_id).workflow_id == MEDIA_WORKFLOW else None)
    async def canon(self, inputs: CapabilityInput) -> CapabilityResult:
        cp = self.store.checkpoint(inputs.run_id)
        if cp.canon_ref:
            return self.success(cp)
        fixed = self.store.author_ref(inputs.run_id,'film-canon')
        if fixed is None:
            if self.canon_author is None:
                raise CapabilityAbsent('CANON_AUTHOR_ABSENT')
            sources = (self.store.input(inputs.run_id).source_ref,)
            value = self.plugin.creative_versions.author_output(inputs.operation_id,'canon',sources,TypeAdapter(FilmCanon))
            if value is None:
                value = FilmCanon.model_validate((await self.canon_author.author_film(self.request(inputs))).model_dump())
            self.plugin.creative_versions.retain_author_output(inputs.operation_id,'canon',sources,value)
            fixed = self.store.put_author(inputs.run_id,value)
        return self.success(self.save(inputs,canon_ref=fixed))
    async def direction(self, inputs: CapabilityInput) -> CapabilityResult:
        cp = self.store.checkpoint(inputs.run_id)
        native_media = self.plugin.runtime.store.load(inputs.run_id).workflow_id == MEDIA_WORKFLOW
        if cp.direction_ref and not native_media:
            return self.success(cp)
        fixed = cp.direction_ref or self.store.author_ref(inputs.run_id,'film-direction')
        fresh = fixed is None
        if fixed is None:
            if self.direction_author is None:
                raise CapabilityAbsent('DIRECTION_AUTHOR_ABSENT')
            sources = (self.store.input(inputs.run_id).source_ref,)
            cached = self.plugin.creative_versions.author_output(inputs.operation_id,'direction',sources,TypeAdapter(FilmDirection))
            direction = cached if cached is not None else FilmDirection.model_validate((await self.direction_author.direct_film(self.request(inputs))).model_dump())
        else:
            direction = self.store.author(fixed,FilmDirection)
        def invalid(code: str, path: tuple[str | int, ...]) -> None:
            if fresh:
                raise AuthorResultFailure(failure('SHOT_POST_VALIDATION', code, field_path=path, validator='FilmDirection.structure'))
            raise ValueError(code)
        value = self.store.input(inputs.run_id)
        assert cp.canon_ref
        canon = self.store.author(cp.canon_ref,FilmCanon)
        scene_ids = [s.scene_id for s in canon.scenes]
        if set(s.scene_id for s in direction.shots) != set(scene_ids):
            invalid('FILM_DIRECTION_SCENE_COVERAGE', ('shots', 'sceneId'))
        # Order comes from the authors. Returning to an earlier Scene is not silently re-edited.
        if [scene_ids.index(s.scene_id) for s in direction.shots] != sorted(scene_ids.index(s.scene_id) for s in direction.shots):
            invalid('FILM_DIRECTION_SCENE_ORDER', ('shots', 'sceneId'))
        costs = value.estimated_shot_cost_microunits
        estimated = costs if native_media else costs * len(direction.shots)
        if not native_media and estimated > value.max_cost_microunits:
            finding=GateFinding.classified(GateCode.BUDGET_EXCEEDED,owner='film-dependency',scope=inputs.scope,
                evidence_ref=value.source_ref.runtime_ref(),required=True)
            decision=self.plugin.gate_governor.govern((finding,),scope=inputs.scope,mode=RunMode.PRODUCTION,package_ref=None)
            ref=self.plugin.gate_findings.put_decision(decision,run_id=inputs.run_id)
            return CapabilityResult(status=ResultStatus.FAILED,code=decision.effect.value,artifact_refs=(ref,))
        tasks = []
        for i,shot in enumerate(direction.shots):
            requires=shot.requires
            if i and direction.shots[i-1].scene_id!=shot.scene_id:
                requires=tuple(dict.fromkeys((*requires,direction.shots[i-1].shot_id)))
            tasks.append(DependencyTask(task_id=shot.shot_id,output='video',requires=requires,estimated_cost=costs if not native_media or i == 0 else 0))
        ids = [s.shot_id for s in direction.shots]
        groups = [tuple(ids[i:i+4]) for i in range(0,len(ids),4)]
        tasks.extend(DependencyTask(task_id=f'av-group-{i}',output='video',requires=g) for i,g in enumerate(groups))
        tasks.append(DependencyTask(task_id='film-assembly',output='video',requires=tuple(f'av-group-{i}' for i in range(len(groups)))))
        tasks.append(DependencyTask(task_id='final-delivery',output='video',requires=('film-assembly',)))
        # A dependency on a later edit slot cannot be handled by this bounded sequential executor.
        for i,shot in enumerate(direction.shots):
            if not set(shot.requires) <= set(ids[:i]):
                invalid('FILM_DIRECTION_DEPENDENCY_ORDER', ('shots', i, 'requires'))
        try:
            graph = RoutePlan(route=value.route,tasks=tuple(tasks),max_tasks=32,max_depth=16,
                capability_available=value.route in (self.plugin.execution.transports if self.plugin.execution else {}),
                authorization_required=bool(costs),cost_limit=max(estimated,value.max_cost_microunits) if native_media else value.max_cost_microunits)
        except ValidationError as error:
            invalid('FILM_DIRECTION_DEPENDENCY_GRAPH_INVALID', ('shots', *error.errors(include_input=False,include_context=False)[0]['loc']))
            raise AssertionError('invalid graph must fail')
        for i, shot in enumerate(direction.shots):
            scene = next(s.scene for s in canon.scenes if s.scene_id == shot.scene_id)
            if self.plugin.runtime.store.load(inputs.run_id).workflow_id == MEDIA_WORKFLOW and not {"ACTION","CAMERA","PERFORMANCE","SOUND","SUBJECTS","WORLD"} <= set(shot.shot.professional_domains):
                invalid("SHOT_MEDIA_REQUIRED_DOMAINS_MISSING", ("shots",i,"shot","professionalDomains"))
            if not set(shot.shot.spoken_ids) <= {line.id for line in scene.dialogue}:
                invalid('SHOT_DIALOGUE_CANON_AUTHORITY', ('shots', i, 'shot', 'spokenIds'))
        if fixed is None:
            self.plugin.creative_versions.retain_author_output(inputs.operation_id,'direction',
                (self.store.input(inputs.run_id).source_ref,),direction)
            fixed = self.store.put_author(inputs.run_id, direction)
        cp = self.save(inputs,direction_ref=fixed,graph=graph)
        if native_media and estimated > value.max_cost_microunits and cp.planning_cost_decision_ref is None:
            request, target = self.pending_decision(inputs.run_id)
            finding=GateFinding.classified(GateCode.COST_APPROVAL_REQUIRED,owner='film-planning',scope=inputs.scope,evidence_ref=target,required=True)
            decision=self.plugin.gate_governor.govern((finding,),scope=inputs.scope,mode=RunMode.PRODUCTION,package_ref=None)
            gate=self.plugin.gate_findings.put_decision(decision,run_id=inputs.run_id)
            return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,external_ref=target,artifact_refs=(gate,target),
                recovery_class=RecoveryClass.USER_DECISION,user_decision=request)
        return self.success(cp)
    async def drive_child(self, run_id: str) -> RuntimeRun:
        p = self.plugin
        run = await p.runtime.recover_run(run_id)
        if run.state == RuntimeState.WAITING_EXTERNAL:
            await p.runtime.reconcile_wait(run_id)
        return await p.runtime.run(run_id)

    def child_result(self, child: RuntimeRun) -> CapabilityResult:
        link = ArtifactReference(owner="runtime", artifact_ref=child.run_id)
        last = child.last_result
        refs = tuple(dict.fromkeys((*(last.artifact_refs if last else ()), link)))
        if child.state == RuntimeState.WAITING_USER:
            request = last.user_decision if last and last.user_decision else self.plugin.runtime.next_action(child.run_id).decision
            if request is None:
                raise ValueError("CHILD_USER_DECISION_MISSING")
            exact = last.external_ref if last and last.external_ref else None
            if exact is None:
                exact = next((r for r in refs if r.owner not in {"runtime", "creative-diagnostic"}), link)
            return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, external_ref=exact, artifact_refs=refs,
                recovery_class=RecoveryClass.USER_DECISION, user_decision=request)
        if child.state == RuntimeState.WAITING_EXTERNAL:
            if last is None or last.external_ref is None:
                raise ValueError("CHILD_EXTERNAL_IDENTITY_MISSING")
            return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, external_ref=last.external_ref,
                artifact_refs=refs, recovery_class=RecoveryClass.WAIT_EXTERNAL)
        return CapabilityResult(status=ResultStatus.FAILED, code=(last.code if last and last.code else child.wait_reason) or "CHILD_HARD_BLOCK",
            artifact_refs=refs, recovery_class=RecoveryClass.HARD_BLOCK)

    async def child(self, run_id: str) -> bool:
        p = self.plugin
        run = await p.runtime.recover_run(run_id)
        if run.state == RuntimeState.WAITING_EXTERNAL:
            from drama_plugin.creative_engine.policy import WORKFLOW as CREATIVE
            from drama_plugin.execution.policy import WORKFLOW as EXECUTION
            if run.workflow_id == CREATIVE:
                run = await p.resume_film_run(run_id)
            elif run.workflow_id == EXECUTION:
                run = await p.resume_execution_run(run_id)
            elif run.workflow_id in (WORKFLOW, REVISION_WORKFLOW):
                run = await p.resume_source_film_run(run_id)
        elif run.state == RuntimeState.BLOCKED and run.wait_reason == 'INTERRUPTED_CAPABILITY':
            await p.runtime.retry(run_id)
            run = await p.runtime.run(run_id)
        else:
            run = await p.runtime.run(run_id)
        return run.state == RuntimeState.SUCCEEDED
    def create_unit(self, inputs: CapabilityInput, slot: int) -> ShotUnit:
        p = self.plugin
        cp = self.store.checkpoint(inputs.run_id)
        assert cp.direction_ref and cp.canon_ref
        canon,direction = self.store.author(cp.canon_ref,FilmCanon),self.store.author(cp.direction_ref,FilmDirection)
        shot = direction.shots[slot]
        scene = next(s for s in canon.scenes if s.scene_id == shot.scene_id)
        scope = RuntimeScope(work_id=inputs.scope.work_id,scene_id=shot.scene_id,shot_id=shot.shot_id)
        source = self.request(inputs).source
        versions = p.creative_versions
        refs = [self.store.input(inputs.run_id).source_ref]
        work_scope = inputs.scope
        for kind,body in ((Kind.WORK,canon.work),(Kind.SCRIPT,canon.script),(Kind.SCENE,scene.scene),(Kind.SHOT,shot.shot)):
            owner_scope = scope if kind == Kind.SHOT else RuntimeScope(work_id=scope.work_id,scene_id=scope.scene_id if kind == Kind.SCENE else None)
            author_key = shot.shot_id if kind == Kind.SHOT else scene.scene_id if kind == Kind.SCENE else 'film'
            refs.append(versions.write(writer=Authority.DIRECTION if kind==Kind.SHOT else Authority.CANON,
                kind=kind,scope=owner_scope,body=body,sources=tuple(refs),operation=f'{inputs.run_id}:canon:{author_key}:{kind.value}'))
        # The author result is fixed. E2 professional/route/review/package still run through native actions.
        run_id = f'{inputs.run_id}:unit:{slot}:creative'
        try:
            p.runtime.store.load(run_id)
        except KeyError:
            p.create_film_run(work_id=scope.work_id,scene_id=scope.scene_id,shot_id=scope.shot_id,mode=RunMode.EXPERIMENT,
                source_ref=refs[0],base_refs=tuple(refs),run_id=run_id,
                route=RouteRequest(available_capabilities=('text_to_video',)))
        return ShotUnit(scene_id=shot.scene_id,shot_id=shot.shot_id,creative_run_id=run_id,refs=tuple(refs))
    async def prepare(self, inputs: CapabilityInput) -> CapabilityResult:
        cp = self.store.checkpoint(inputs.run_id)
        if cp.plan_ref:
            return self.success(cp)
        assert cp.direction_ref and cp.canon_ref and cp.graph
        shots = self.store.author(cp.direction_ref,FilmDirection).shots
        units = list(cp.units)
        for slot in range(len(shots)):
            if slot >= len(units):
                units.append(self.create_unit(inputs,slot))
                self.save(inputs,units=tuple(units))
            unit = units[slot]
            child = await self.drive_child(unit.creative_run_id)
            if child.state != RuntimeState.SUCCEEDED:
                return self.child_result(child)
            ucp = self.plugin.creative.state.checkpoint(unit.creative_run_id)
            units[slot] = ShotUnit.model_validate({**unit.model_dump(),'refs':ucp.refs,'package_ref':ucp.package_ref})
            self.save(inputs,units=tuple(units))
        value = self.store.input(inputs.run_id)
        plan = FilmPlan.seal(scope=inputs.scope,run_id=inputs.run_id,film_version=cp.film_version,
            source_ref=value.source_ref,canon_ref=cp.canon_ref,direction_ref=cp.direction_ref,
            unit_version_refs=tuple(u.refs for u in units),graph=cp.graph,languages=value.languages)
        return self.success(self.save(inputs,plan_ref=self.store.put(plan)))
    def decision_record(self, inputs: CapabilityInput, category: DecisionCategory, target: ArtifactReference) -> tuple[ArtifactReference,UserDecisionRecord]:
        run = self.plugin.runtime.store.load(inputs.run_id)
        if not run.last_result or len(run.last_result.artifact_refs)!=1:
            raise ValueError('Exact user decision required')
        ref = run.last_result.artifact_refs[0]
        body,scope,_ = self.store.ledger.get_artifact('user-decision',ref)
        record = UserDecisionRecord.model_validate(body)
        if scope!=inputs.scope or record.run_id!=inputs.run_id or record.category!=category or record.source_ref!=target or not record.accepted:
            raise ValueError('Wrong Film decision/candidate/version/hash')
        return ref,record
    async def decision(self, inputs: CapabilityInput) -> CapabilityResult:
        return self.success(self.store.checkpoint(inputs.run_id))
    async def adopt(self, inputs: CapabilityInput) -> CapabilityResult:
        p = self.plugin
        cp = self.store.checkpoint(inputs.run_id)
        assert cp.plan_ref
        if cp.adoption_ref is None:
            ref,_ = self.decision_record(inputs,DecisionCategory.ADOPTION,cp.plan_ref)
            if any(p.creative_versions.stale(r) for u in cp.units for r in u.refs):
                raise ValueError('Film adoption dependencies stale')
            cp = self.save(inputs,adoption_ref=ref)
        # Adopt the shared Work/Scene Canon once, then its Shot/professional
        # descendants. Every member binds the one exact reviewed Film bundle.
        remapped: dict[VersionRef,VersionRef] = {}
        for unit in cp.units:
            for prior in unit.refs:
                if prior in remapped:
                    continue
                artifact=p.creative_versions.resolve(prior)
                if artifact.kind==Kind.SOURCE or artifact.state=='ADOPTED':
                    remapped[prior]=prior
                else:
                    parents=tuple(remapped[parent] for parent in artifact.source_refs)
                    remapped[prior]=p.creative_versions.write(writer=artifact.authority,kind=artifact.kind,
                        scope=artifact.scope,body=artifact.body,sources=parents,
                        operation=inputs.run_id+':film-adopt:'+prior.fingerprint,adoption_decision=cp.adoption_ref,candidate_origin=prior)
        cp=self.save(inputs,units=tuple(ShotUnit.model_validate({**u.model_dump(),'refs':tuple(remapped[r] for r in u.refs)}) for u in cp.units))
        units=list(cp.units)
        for slot,unit in enumerate(units):
            identity=unit.production_run_id or f'{inputs.run_id}:unit:{slot}:production:v{cp.film_version}'
            try:
                child=p.runtime.store.load(identity)
            except KeyError:
                child=p.create_film_run(work_id=inputs.scope.work_id,scene_id=unit.scene_id,shot_id=unit.shot_id,
                    mode=RunMode.PRODUCTION,source_ref=unit.refs[0],base_refs=unit.refs,run_id=identity,
                    route=RouteRequest(available_capabilities=('text_to_video',)))
            child=await p.runtime.run(identity)
            if child.state==RuntimeState.WAITING_USER:
                childcp=p.creative.state.checkpoint(identity)
                # Consumer of one explicitly reviewed Film adoption: bind each exact
                # member hash. No new user gate or implicit creative change is introduced.
                assert childcp.candidate_ref and p.reviews
                receipt=UserDecisionRecord.seal(run_id=identity,scope=child.scope,decision_id=p.runtime.decision_id(identity),
                    category=DecisionCategory.ADOPTION,accepted=True,source_ref=childcp.candidate_ref)
                child=await p.runtime.decide(identity,decision_id=receipt.decision_id,accepted=True,decision_ref=p.reviews.put_user_decision(receipt))
                child=await p.runtime.run(identity)
            if child.state!=RuntimeState.SUCCEEDED:
                return self.child_result(child)
            childcp=p.creative.state.checkpoint(identity)
            units[slot]=ShotUnit.model_validate({**unit.model_dump(),'production_run_id':identity,'refs':childcp.refs,'package_ref':childcp.package_ref})
            self.save(inputs,units=tuple(units))
        return self.success(self.store.checkpoint(inputs.run_id))
    async def execute(self, inputs: CapabilityInput) -> CapabilityResult:
        p,cp=self.plugin,self.store.checkpoint(inputs.run_id)
        if p.runtime.store.load(inputs.run_id).workflow_id == MEDIA_WORKFLOW:
            return await self.execute_media(inputs)
        if self.recipes is None or p.execution is None:
            return self.wait(inputs,'approved-execution-recipe')
        units=list(cp.units)
        for slot,unit in enumerate(units):
            if unit.candidate_ref:
                continue
            if unit.package_ref is None and unit.production_run_id:
                if not await self.child(unit.production_run_id):
                    return self.wait(inputs,'creative-revision',ArtifactReference(owner='runtime-run',artifact_ref=unit.production_run_id,version=1))
                revision_cp=p.creative.state.checkpoint(unit.production_run_id)
                unit=ShotUnit.model_validate({**unit.model_dump(),'package_ref':revision_cp.package_ref,'refs':revision_cp.refs})
                units[slot]=unit
                self.save(inputs,units=tuple(units))
            assert unit.package_ref
            if any(p.creative_versions.stale(r) for r in unit.refs):
                return self.wait(inputs,'stale-shot-owner',unit.package_ref)
            generation=unit.generation_run_id or f'{inputs.run_id}:unit:{slot}:prepare:v{cp.film_version}'
            try:
                p.runtime.store.load(generation)
            except KeyError:
                p.create_generation_run(work_id=inputs.scope.work_id,scene_id=unit.scene_id,shot_id=unit.shot_id,
                    mode=RunMode.PRODUCTION,package_ref=unit.package_ref,run_id=generation,
                    task=GenerationTask(target_model=self.store.input(inputs.run_id).model,native_audio='REQUIRED'))
            if not await self.child(generation):
                return self.wait(inputs,'preparation-child')
            pref=p.generation_artifacts.prepared(generation)
            assert pref
            prep=p.generation_artifacts.get(pref,GenerationPreparation)
            execution=unit.execution_run_id or f'{inputs.run_id}:unit:{slot}:execute:v{cp.film_version}'
            try:
                p.runtime.store.load(execution)
            except KeyError:
                scope=RuntimeScope(work_id=inputs.scope.work_id,scene_id=unit.scene_id,shot_id=unit.shot_id)
                p.create_execution_run(run_id=execution,mode=RunMode.PRODUCTION,preparation_ref=pref,
                    authorization=self.recipes.authorization(unit.package_ref),route=self.store.input(inputs.run_id).route,
                    recipe=self.recipes.recipe(run_id=execution,scope=scope,preparation_ref=pref,package_ref=unit.package_ref,audio_plan_ref=prep.audio_plan_ref))
            units[slot]=ShotUnit.model_validate({**unit.model_dump(),'generation_run_id':generation,'execution_run_id':execution})
            self.save(inputs,units=tuple(units))
            # Durable delegation precedes Provider work. The parent is WAITING,
            # so crashes at several child stages do not consume the parent's
            # same-action retry budget or hold a Film dispatch claim.
            if p.runtime.store.load(inputs.run_id).state == RuntimeState.RUNNING:
                return self.wait(inputs,'execution-child',ArtifactReference(owner='runtime-run',artifact_ref=execution,version=1))
            if not await self.child(execution):
                run=p.runtime.store.load(execution)
                if run.last_result:
                    for ref in run.last_result.artifact_refs:
                        if ref.owner=='creative-media-review':
                            review=p.execution.store.get(ref,CreativeMediaReview)
                            if review.outcome=='REVISE':
                                return await self.revise_shot(inputs,slot,ref)
                # E1 records the review ref inside its governed finding.
                checkpoint=p.execution.store.checkpoint(p.execution._approved(CapabilityInput(run_id=execution,scope=p.runtime.store.load(execution).scope,operation_id=execution+':0'))[0].artifact_reference())
                for review_pointer in (checkpoint.progress.video_creative_ref,checkpoint.progress.av_creative_ref):
                    if review_pointer and p.execution.store.get(review_pointer,CreativeMediaReview).outcome=='REVISE':
                        return await self.revise_shot(inputs,slot,review_pointer)
                return self.wait(inputs,'execution-child',ArtifactReference(owner='runtime-run',artifact_ref=execution,version=1))
            result=p.runtime.store.load(execution).last_result
            assert result
            candidate_ref=next(ref for ref in result.artifact_refs if ref.owner=='reviewed-av-candidate')
            units[slot]=ShotUnit.model_validate({**units[slot].model_dump(),'candidate_ref':candidate_ref})
            self.save(inputs,units=tuple(units))
        return self.success(self.store.checkpoint(inputs.run_id))
    def pending_decision(self, run_id: str) -> tuple[UserDecisionRequest, ArtifactReference]:
        cp = self.store.checkpoint(run_id)
        run = self.plugin.runtime.store.load(run_id)
        value = self.store.input(run_id)
        if run.workflow_id == MEDIA_WORKFLOW and run.cursor == 1 and cp.direction_ref and cp.planning_cost_decision_ref is None and value.estimated_shot_cost_microunits > value.max_cost_microunits:
            return (UserDecisionRequest(category=DecisionCategory.COST_APPROVAL,
                question="The bounded one-operation planning estimate exceeds the planning ceiling. Allow this exact approved Direction to continue preparation? This approves planning only; no external operation, actual price, dispatch, or payment is authorized."), cp.direction_ref)
        if run.workflow_id == MEDIA_WORKFLOW and run.cursor == 5 and cp.units:
            unit = self.plugin.source_film_unit_for_task(run_id,cp.operation_task) if cp.operation_task else next(
                u for u in cp.units if (u.scene_id,u.shot_id)==tuple(self.plugin.source_film_production_progress(run_id)['nextUnit'][k] for k in ('sceneId','shotId')))
            if any(self.plugin.creative_versions.stale(r) for r in unit.refs):
                assert unit.package_ref is not None
                return (UserDecisionRequest(category=DecisionCategory.ART_APPROVAL,
                    question="An exact adopted creative dependency has been revised. Provide the bounded original-owner revision and its exact new adopted candidate for this Shot before continuing. Accepting the old Package cannot restore stale authority."),unit.package_ref)
        if cp.rights_request_pin is None or cp.rights_decision_ref is not None:
            raise ValueError("No pending source processing rights request")
        return (UserDecisionRequest(category=DecisionCategory.ADOPTION,
            question="Authorize necessary Source/Canon-derived information of this exact adopted Shot for one external video operation, with zero paid references/retries? This grants no cost, submission or release approval."),
            ArtifactReference(owner="source-owner", artifact_ref=cp.rights_request_pin.key, version=1))

    def pending_decision_terms(self, run_id: str) -> str | None:
        request, target = self.pending_decision(run_id)
        if request.category == DecisionCategory.ART_APPROVAL:
            unit=next(u for u in self.store.checkpoint(run_id).units if u.package_ref==target)
            return sha256_canonical({"packageRef":target.model_dump(mode="json",by_alias=True),
                "staleRefs":[r.model_dump(mode="json",by_alias=True) for r in unit.refs if self.plugin.creative_versions.stale(r)],
                "purpose":"EXACT_OWNER_REVISION_REQUIRED", "revisionDepth":unit.revision_depth})
        if request.category == DecisionCategory.COST_APPROVAL:
            value = self.store.input(run_id)
            return sha256_canonical({"purpose":"FILM_PLANNING_ONLY", "directionRef":target.model_dump(mode="json",by_alias=True),
                "estimatedCostMicrounits":value.estimated_shot_cost_microunits,"previousCeilingMicrounits":value.max_cost_microunits,
                "maxOperations":1,"dispatchAuthorized":False})
        return None

    def consume_decision(self, run_id: str, ref: ArtifactReference, accepted: bool) -> None:
        cp = self.store.checkpoint(run_id)
        request, target = self.pending_decision(run_id)
        body, scope, _ = self.store.ledger.get_artifact("user-decision", ref)
        receipt = UserDecisionRecord.model_validate(body)
        run = self.plugin.runtime.store.load(run_id)
        if (receipt.run_id != run_id or receipt.scope != run.scope or scope != run.scope or receipt.source_ref != target
                or receipt.category != request.category or receipt.accepted != accepted
                or receipt.terms_hash != self.pending_decision_terms(run_id)):
            raise ValueError("Rights decision does not bind the pending exact request")
        if not accepted:
            return
        if request.category == DecisionCategory.ART_APPROVAL:
            raise ValueError("An exact adopted owner revision is required; a boolean cannot approve stale authority")
        if request.category == DecisionCategory.COST_APPROVAL:
            self.store.save(run_id,run.scope,cp.model_copy(update={"planning_cost_decision_ref":ref}))
            return
        assert cp.rights_request_pin is not None
        material = self.plugin.creative_versions.objects.read_ref(cp.rights_request_pin)
        manifest = {**material, "externalProcessingAuthorized": True,
            "requestRef": target.model_dump(mode="json", by_alias=True), "decisionRef": ref.model_dump(mode="json", by_alias=True)}
        pin = self.plugin.creative_versions.objects.put("source-rights:"+sha256_canonical(manifest), manifest)
        self.store.save(run_id, run.scope, FilmCheckpoint.model_validate({**cp.model_dump(), "rights_decision_ref": ref, "rights_pin": pin}))

    async def provide_creative_revision_result(self, run_id: str, revision_run_id: str) -> RuntimeRun:
        """Consume a completed, explicitly adopted original-owner result, never latest."""
        p,cp=self.plugin,self.store.checkpoint(run_id)
        run=p.runtime.store.load(run_id)
        if run.workflow_id!=MEDIA_WORKFLOW or run.state!=RuntimeState.WAITING_USER or run.cursor!=5 or not cp.units:
            raise ValueError("No pending native creative revision scope")
        request,target=self.pending_decision(run_id)
        if request.category!=DecisionCategory.ART_APPROVAL or run.last_result is None or run.last_result.external_ref!=target:
            raise ValueError("Exact stale creative scope required")
        old=next(u for u in cp.units if u.package_ref==target)
        child=p.runtime.store.load(revision_run_id)
        value=p.creative.state.input(revision_run_id)
        fixed=p.creative.state.checkpoint(revision_run_id)
        revision=value.revision
        if (child.state!=RuntimeState.SUCCEEDED or child.scope!=RuntimeScope(work_id=run.scope.work_id,scene_id=old.scene_id,shot_id=old.shot_id)
                or revision is None or revision.target_ref not in old.refs or revision.depth!=old.revision_depth+1 or revision.depth>3
                or value.source_ref!=self.store.input(run_id).source_ref or fixed.package_ref is None
                or fixed.candidate_ref is None or fixed.decision_ref is None
                or any(p.creative_versions.stale(ref) for ref in fixed.refs)):
            raise ValueError("Wrong or incomplete exact owner revision")
        source=p.creative_versions.resolve(revision.target_ref)
        if source.authority!=revision.owner:
            raise ValueError("Revision changed the creative owner")
        if fixed.candidate_ref.artifact_ref != "creative-candidate:"+sha256_canonical([ref.model_dump(mode="json",by_alias=True) for ref in fixed.candidate_version_refs]):
            raise ValueError("Wrong exact replacement candidate")
        if p.operation_resolver is None:
            raise ValueError("Native operation owner absent")
        receipt=p.operation_resolver.decision(fixed.decision_ref,category=DecisionCategory.ADOPTION,
            scope=child.scope,source_ref=fixed.candidate_ref)
        if receipt.run_id!=revision_run_id:
            raise ValueError("Wrong exact replacement adoption")
        signature=sha256_canonical([revision.owner.value,revision.target_ref.model_dump(mode="json",by_alias=True),revision.instruction])
        if signature in old.revision_signatures:
            raise ValueError("Creative revision cycle")
        units=list(cp.units)
        units[cp.units.index(old)]=old.model_copy(update={"production_run_id":revision_run_id,"refs":fixed.refs,"package_ref":fixed.package_ref,
            "candidate_ref":None,"generation_run_id":None,"execution_run_id":None,"revision_depth":revision.depth,
            "revision_signatures":(*old.revision_signatures,signature)})
        self.store.save(run_id,run.scope,FilmCheckpoint.model_validate({**cp.model_dump(),"units":tuple(units),"operation_task":None,
            "rights_request_pin":None,"rights_pin":None,"rights_decision_ref":None}))
        # The real child adoption receipt resolves the artistic replacement choice;
        # it does not complete the media capability or authorize execution.
        return await p.runtime.decide(run_id,decision_id=p.runtime.decision_id(run_id),accepted=True,
            decision_ref=fixed.decision_ref,resume_same_step=True)

    async def execute_media(self, inputs: CapabilityInput) -> CapabilityResult:
        p, cp = self.plugin, self.store.checkpoint(inputs.run_id)
        if p.operation_resolver is None or p.execution is None or not cp.units or cp.adoption_ref is None:
            return self.wait(inputs, "native-production-composition")
        # Frozen work recovers its exact owner. A fresh unit comes from the
        # adopted plan/coverage view, rather than an implicit first-Shot scope.
        if cp.operation_task:
            unit = p.source_film_unit_for_task(inputs.run_id,cp.operation_task)
        else:
            target = p.source_film_production_progress(inputs.run_id)['nextUnit']
            if target is None: return self.success(cp)
            unit = next(u for u in cp.units if (u.scene_id,u.shot_id)==(target['sceneId'],target['shotId']))
        slot = cp.units.index(unit)
        if cp.media_batch_ref:
            child_id = p.source_film_media_opening(inputs.run_id)
            task = p.generation_artifacts.inputs(child_id).task
            p._compose_media_owners(task,run_id=child_id)
            child = await self.drive_child(child_id)
            if child.state != RuntimeState.SUCCEEDED:
                if (child.state == RuntimeState.WAITING_USER and child.last_result and child.last_result.external_ref
                        and child.last_result.external_ref.owner == 'media-binding'):
                    await p.retain_source_film_last_frame(child_id)
                return self.child_result(child)
            review_ref = next((ref for ref in child.last_result.artifact_refs if ref.owner == 'creative-media-review'),None)
            if review_ref is None:
                raise ValueError('MEDIA_REVIEW_RECEIPT_MISSING')
            await p.retain_source_film_last_frame(child_id)
            self.save(inputs,media_batch_opening_review_ref=review_ref)
            return await self.execute_scene_media(inputs)
        if unit.candidate_ref:
            return await self.execute_scene_media(inputs)
        if unit.package_ref is None:
            return CapabilityResult(status=ResultStatus.FAILED, code="ADOPTED_PACKAGE_SCOPE_OR_VERSION_INVALID", recovery_class=RecoveryClass.HARD_BLOCK)
        if any(p.creative_versions.stale(r) for r in unit.refs):
            request,target=self.pending_decision(inputs.run_id)
            stale=tuple(r.runtime_ref() for r in unit.refs if p.creative_versions.stale(r))
            finding=GateFinding.classified(GateCode.ART_APPROVAL_REQUIRED,owner="creative-owner-revision",scope=inputs.scope,evidence_ref=target,required=True)
            decision=p.gate_governor.govern((finding,),scope=inputs.scope,mode=RunMode.PRODUCTION,package_ref=None)
            gate=p.gate_findings.put_decision(decision,run_id=inputs.run_id)
            return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,external_ref=target,artifact_refs=(gate,*stale),
                recovery_class=RecoveryClass.USER_DECISION,user_decision=request)
        assert unit.production_run_id is not None
        shot_owner=next(p.creative_versions.resolve(ref) for ref in unit.refs if p.creative_versions.resolve(ref).kind==Kind.SHOT)
        adoption=shot_owner.adoption_decision_ref
        if adoption is None:
            raise ValueError("OPERATION_NOT_ADOPTED")
        package = p.production_packages.get(unit.package_ref)
        task = cp.operation_task
        if task is not None and unit.generation_run_id:
            current_task = p.generation_artifacts.inputs(unit.generation_run_id).task
            if current_task != task:
                if (task.unit is None or current_task.unit is None or current_task.owners != task.owners
                        or current_task.profile != task.profile or
                        current_task.unit.model_dump(exclude={"scope_decision_ref"}) != task.unit.model_dump(exclude={"scope_decision_ref"})):
                    raise ValueError("OPERATION_TASK_AUTHORITY_DRIFT")
                p.operation_resolver.validate(package,current_task)
                task = current_task
                cp = self.save(inputs,operation_task=task)
        if task is None:
            value = self.store.input(inputs.run_id)
            dimensions = {(1280,720):("720p","16:9"), (1920,1080):("1080p","16:9"), (720,1280):("720p","9:16"),
                (1080,1920):("1080p","9:16")}
            if (value.profile.width, value.profile.height) not in dimensions:
                raise CapabilityAbsent("DELIVERY_OPERATION_PROFILE_UNSUPPORTED")
            resolution, ratio = dimensions[(value.profile.width,value.profile.height)]
            profile = resolve_profile(model=value.model,duration_ms=value.operation_duration_ms,resolution=resolution,
                ratio=ratio,native_audio=value.profile.audio_required,policy=p.operation_resolver.policy)
            if value.route != profile.provider:
                raise ValueError("FILM_ROUTE_PROFILE_MISMATCH")
            dpd_pin, projection_pin, snapshots = p.operation_resolver.compose_performance(unit.refs)
            selection = await p.operation_resolver.select_unit(package, p.prompt_compiler.reader)
            if cp.rights_request_pin is None:
                assert cp.adoption_ref is not None
                adopted = [r.model_dump(mode="json", by_alias=True) for r in unit.refs if p.creative_versions.resolve(r).kind != Kind.PROFESSIONAL]
                material = {"scope": p.runtime.store.load(unit.production_run_id).scope.model_dump(mode="json", by_alias=True),
                    "adoptedRefs": adopted, "sourceRef": next(r for r in adopted if str(r["identity"]).startswith("creative-source:")),
                    "creativeAdoptionDecisionRef": adoption.model_dump(mode="json", by_alias=True),
                    "dpdBindingRef": {"owner":"dpd-core","artifactRef":"dpd-binding:"+dpd_pin.fingerprint,"version":1},
                    "profile": profile.model_dump(mode="json",by_alias=True), "processingScope": {
                        "purpose":"MINIMAL_CONTROLLED_LIVE_TECHNICAL_PROOF", "material":"necessary Source-derived / Canon-derived information of exact adopted Shot",
                        "providerModelAuthority":"CURRENT_B1_REQUALIFICATION", "durationSeconds":profile.requested_duration_ms / 1000,
                        "resolution":profile.resolution,"aspectRatio":profile.aspect_ratio,"mode":profile.mode,
                        "maxLogicalVideoOperations":1,"paidReferences":0,"paidRetries":0}}
                pin = p.creative_versions.objects.put("source-rights-request:"+sha256_canonical(material),material)
                cp = self.save(inputs,rights_request_pin=pin)
            if cp.rights_decision_ref is None:
                request, ref = self.pending_decision(inputs.run_id)
                finding = GateFinding.classified(GateCode.ADOPTION_REQUIRED, owner="source-rights", scope=inputs.scope, evidence_ref=ref)
                governed = p.gate_governor.govern((finding,),scope=inputs.scope,mode=RunMode.PRODUCTION,package_ref=unit.package_ref)
                gate = p.gate_findings.put_decision(governed,run_id=inputs.run_id)
                return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,artifact_refs=(ref,gate),external_ref=ref,
                    recovery_class=RecoveryClass.USER_DECISION,user_decision=request)
            assert cp.rights_pin is not None and cp.rights_request_pin is not None and cp.adoption_ref is not None
            owners = OwnerBindings(adopted_refs=unit.refs,dpd_pin=dpd_pin,performance_scope_pin=projection_pin,snapshot_pins=snapshots,
                rights_pin=cp.rights_pin,rights_request_ref=ArtifactReference(owner="source-owner",artifact_ref=cp.rights_request_pin.key,version=1),
                rights_decision_ref=cp.rights_decision_ref,adoption_decision_ref=adoption)
            task = GenerationTask(target_model=profile.model,input_mode=profile.mode,native_audio="REQUIRED" if profile.native_audio else "DISABLED",
                unit=selection,profile=profile,owners=owners,
                return_last_frame=True if profile.provider == 'seedance' else None)
            cp = self.save(inputs,operation_task=task)
        if unit.generation_run_id:
            child = p.runtime.store.load(unit.generation_run_id)
            # A fresh process must restore the same pinned physical owners before
            # reconciling its existing child task, without re-entering goal creation.
            p._compose_media_owners(task, run_id=child.run_id)
        else:
            child = p.create_media_review_run(package_ref=unit.package_ref,task=task)
        if unit.generation_run_id != child.run_id:
            units = list(cp.units)
            units[slot] = ShotUnit.model_validate({**unit.model_dump(), "generation_run_id": child.run_id})
            self.save(inputs,units=tuple(units))
        child = await self.drive_child(child.run_id)
        if child.state != RuntimeState.SUCCEEDED:
            return self.child_result(child)
        if child.last_result is None:
            raise ValueError("MEDIA_REVIEW_RECEIPT_MISSING")
        review_ref = next((ref for ref in child.last_result.artifact_refs if ref.owner == "creative-media-review"), None)
        if review_ref is None:
            raise ValueError("MEDIA_REVIEW_RECEIPT_MISSING")
        cp = self.store.checkpoint(inputs.run_id)
        units = list(cp.units)
        units[slot] = ShotUnit.model_validate({**units[slot].model_dump(), "candidate_ref": review_ref})
        self.save(inputs,units=tuple(units))
        return await self.execute_scene_media(inputs)

    async def execute_scene_media(self, inputs: CapabilityInput) -> CapabilityResult:
        """Ordered adjacent clips beneath the original adopted Shot, using native child goals."""
        p, cp = self.plugin, self.store.checkpoint(inputs.run_id)
        refs = list(cp.scene_media_review_refs or ())
        for index, child_id in enumerate(cp.scene_media_run_ids or ()):
            task = p.generation_artifacts.inputs(child_id).task
            unit = p.source_film_unit_for_task(inputs.run_id,task)
            child = p.runtime.store.load(child_id)
            previous_id = cp.scene_media_run_ids[index-1] if index else p.source_film_media_opening(inputs.run_id)
            p.validate_source_film_boundary(inputs.run_id,task=task,previous_id=previous_id)
            if task.continuation:
                from drama_plugin.generation.operation import validate_continuation, continuation_frame
                validate_continuation(p.ledger, task)
                _, predecessor, _, _ = continuation_frame(p.ledger, task.continuation.frame_ref,
                    allow_unverified_audio=bool(task.continuation.allow_unverified_audio))
                previous_id = cp.scene_media_run_ids[index-1] if index else p.source_film_media_opening(inputs.run_id)
                if predecessor.run_id != previous_id:
                    raise ValueError('IMMEDIATE_REVIEWED_PREDECESSOR_REQUIRED')
            from drama_plugin.film.media_units import validate_child_package
            validate_child_package(p,child_id,unit)
            p._compose_media_owners(task,run_id=child_id)
            child = await self.drive_child(child_id)
            if child.state != RuntimeState.SUCCEEDED:
                if (task.return_last_frame and child.state == RuntimeState.WAITING_USER and child.last_result
                        and child.last_result.external_ref and child.last_result.external_ref.owner == 'media-binding'):
                    await p.retain_source_film_last_frame(child_id)
                return self.child_result(child)
            review_ref = next((r for r in child.last_result.artifact_refs if r.owner == 'creative-media-review'),None)
            if review_ref is None:
                raise ValueError('SCENE_CONTINUATION_REVIEW_MISSING')
            from drama_plugin.execution.contracts import CreativeMediaReview
            if p.execution.store.get(review_ref,CreativeMediaReview).outcome != 'PASS':
                return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,external_ref=review_ref,
                    artifact_refs=(review_ref,ArtifactReference(owner='runtime',artifact_ref=child_id)),
                    recovery_class=RecoveryClass.USER_DECISION,user_decision=UserDecisionRequest(
                        category=DecisionCategory.ART_APPROVAL,question='This adjacent clip failed continuity review; resolve its exact observations before continuing.'))
            if task.return_last_frame:
                await p.retain_source_film_last_frame(child_id)
            if index < len(refs):
                if refs[index] != review_ref:
                    raise ValueError('SCENE_CONTINUATION_REVIEW_DRIFT')
            else:
                refs.append(review_ref)
                self.save(inputs,scene_media_review_refs=tuple(refs))
        current = self.store.checkpoint(inputs.run_id)
        if current.scene_media_pending_tasks:
            # Bind only now, after the immediately preceding result and review.
            # A crash replays the same frame/goal identities, never a paid create.
            task = await p.prepare_source_film_unit(inputs.run_id,task=current.scene_media_pending_tasks[0])
            unit = p.source_film_unit_for_task(inputs.run_id,task)
            child = p.create_media_review_run(package_ref=unit.package_ref,task=task)
            self.save(inputs,scene_media_run_ids=(*(current.scene_media_run_ids or ()),child.run_id),
                scene_media_pending_tasks=current.scene_media_pending_tasks[1:])
            return await self.execute_scene_media(inputs)
        opening = p.source_film_unit_for_task(inputs.run_id,p.generation_artifacts.inputs(p.source_film_media_opening(inputs.run_id)).task)
        return CapabilityResult(status=ResultStatus.SUCCEEDED,artifact_refs=(cp.media_batch_opening_review_ref or opening.candidate_ref,*refs))

    async def revise_shot(self, inputs: CapabilityInput, slot: int, review_ref: ArtifactReference) -> CapabilityResult:
        p,cp=self.plugin,self.store.checkpoint(inputs.run_id)
        unit=cp.units[slot]
        if unit.revision_depth>=3 or unit.production_run_id is None:
            return self.wait(inputs,'revision-bound',review_ref)
        revision_id=f'{inputs.run_id}:unit:{slot}:revision:{unit.revision_depth+1}'
        try:
            revised=p.runtime.store.load(revision_id)
        except KeyError:
            revised=p.route_creative_review(unit.production_run_id,review_ref,run_id=revision_id)
        # Revision reaches a genuine new adoption boundary. The Film parent waits;
        # callers supply a creative decision, never an internal capability choice.
        await p.runtime.run(revised.run_id)
        units=list(cp.units)
        units[slot]=ShotUnit.model_validate({**unit.model_dump(),'production_run_id':revision_id,
            'package_ref':None,'candidate_ref':None,'generation_run_id':None,'execution_run_id':None,
            'revision_depth':unit.revision_depth+1})
        self.save(inputs,units=tuple(units),film_version=cp.film_version+1,final_ref=None,qa_ref=None,review_ref=None,acceptance_ref=None,delivery_ref=None)
        return self.wait(inputs,'creative-revision',ArtifactReference(owner='runtime-run',artifact_ref=revision_id,version=1))
    async def assemble(self, inputs: CapabilityInput) -> CapabilityResult:
        p,cp=self.plugin,self.store.checkpoint(inputs.run_id)
        if cp.final_ref:
            return self.success(cp)
        assert p.execution and cp.plan_ref
        shots:list[FilmShotBinding]=[]
        for unit in cp.units:
            if not unit.candidate_ref or not unit.package_ref:
                return self.wait(inputs,'reviewed-av-candidate')
            candidate=p.execution.store.get(unit.candidate_ref,ReviewedAVCandidate)
            if candidate.scope!=RuntimeScope(work_id=inputs.scope.work_id,scene_id=unit.scene_id,shot_id=unit.shot_id) or candidate.source_package_ref!=unit.package_ref:
                raise ValueError('Cross-scope Film candidate')
            shot_ref=next(ref for ref in unit.refs if p.creative_versions.resolve(ref).kind==Kind.SHOT)
            if p.creative_versions.stale(shot_ref):
                return self.wait(inputs,'stale-approved-shot')
            from drama_plugin.execution.media import probe
            observed=probe(p.execution.media.path(candidate.media))
            shots.append(FilmShotBinding(scene_id=unit.scene_id,shot_id=unit.shot_id,shot_ref=shot_ref,
                package_ref=unit.package_ref,candidate_ref=unit.candidate_ref,media=candidate.media,duration_ms=observed.duration_ms))
        value=self.store.input(inputs.run_id)
        old_plan=self.store.get(cp.plan_ref,FilmPlan)
        if old_plan.unit_version_refs != tuple(u.refs for u in cp.units) or old_plan.film_version!=cp.film_version:
            revised_plan=FilmPlan.seal(scope=inputs.scope,run_id=inputs.run_id,film_version=cp.film_version,
                source_ref=value.source_ref,canon_ref=old_plan.canon_ref,direction_ref=old_plan.direction_ref,
                unit_version_refs=tuple(u.refs for u in cp.units),graph=old_plan.graph,languages=value.languages)
            cp=self.save(inputs,plan_ref=self.store.put(revised_plan))
        cues=value.subtitle_cues
        if value.profile.subtitle_required and not cues:
            from drama_plugin.execution.contracts import AudioExecution
            from drama_plugin.creative_engine.contracts import SceneBody, ShotBody
            measured: list[SubtitleCue]=[]
            language=value.languages.subtitle_language
            if language is None:
                return self.wait(inputs,'approved-subtitle-translation')
            for unit, binding in zip(cp.units, shots, strict=True):
                candidate=p.execution.store.get(binding.candidate_ref,ReviewedAVCandidate)
                audio=p.execution.store.get(candidate.audio_execution_ref,AudioExecution)
                scene=next(p.creative_versions.resolve(r).body for r in unit.refs if p.creative_versions.resolve(r).kind==Kind.SCENE)
                shot=p.creative_versions.resolve(binding.shot_ref).body
                assert isinstance(scene,SceneBody) and isinstance(shot,ShotBody)
                timings={t.spoken_content_id:t for t in audio.timings if t.spoken_content_id}
                if not set(shot.spoken_ids)<=timings.keys():
                    return self.wait(inputs,'reliable-subtitle-timing')
                for line in scene.dialogue:
                    if line.id not in shot.spoken_ids:
                        continue
                    timing=timings[line.id]
                    text_ref=ArtifactReference(owner=timing.source_ref.owner.value,artifact_ref=timing.source_ref.artifact_ref,version=timing.source_ref.version)
                    subtitle_text=line.text
                    localization_ref=None
                    if language!=value.languages.spoken_language:
                        canon=self.store.author(old_plan.canon_ref,FilmCanon)
                        source_scene=next(s for s in canon.scenes if s.scene_id==unit.scene_id)
                        localized=next((q for q in source_scene.subtitle_localizations if q.dialogue_id==line.id and q.language==language and q.source_text_hash==sha256_canonical(line.text)),None)
                        if localized is None:
                            return self.wait(inputs,'approved-subtitle-localization')
                        subtitle_text,localization_ref=localized.text,old_plan.canon_ref
                    measured.append(SubtitleCue(shot_id=unit.shot_id,language=language,text=subtitle_text,start_ms=timing.start_ms,
                        localization_ref=localization_ref,
                        end_ms=timing.end_ms,timing_ref=candidate.audio_execution_ref,text_ref=text_ref))
            if not measured:
                return self.wait(inputs,'reliable-subtitle-timing')
            cues=tuple(measured)
        try:
            if cues and any(cue.language != value.languages.subtitle_language for cue in cues):
                raise ValueError('Subtitle language differs from approved Source metadata')
            text=validate_cues(cues,tuple(shots),p.execution.store,p.creative_versions,self.store.author(old_plan.canon_ref,FilmCanon),old_plan.canon_ref) if cues else None
            content,sref=assemble(tuple(shots),p.execution.media,text)
        except CapabilityAbsent:
            return self.wait(inputs,'reliable-subtitle-timing')
        assert cp.plan_ref
        media=p.execution.media.retain(content,kind='VIDEO',mime='video/mp4')
        from drama_plugin.execution.formal_media import FormalMediaStore
        canonical_media_ref = None
        if isinstance(p.execution.media, FormalMediaStore):
            canonical_media_ref = await p.execution.media.register(media,scope=inputs.scope,source_ref=cp.plan_ref,parents=tuple(s.media for s in shots))
        final=FinalFilmCandidate.seal(scope=inputs.scope,run_id=inputs.run_id,film_version=cp.film_version,
            plan_ref=cp.plan_ref,shots=tuple(shots),media=media,canonical_media_ref=canonical_media_ref,subtitle_ref=sref,profile=value.profile,
            duration_ms=sum(s.duration_ms for s in shots))
        return self.success(self.save(inputs,final_ref=self.store.put(final)))
    async def review(self, inputs: CapabilityInput) -> CapabilityResult:
        p,cp=self.plugin,self.store.checkpoint(inputs.run_id)
        assert cp.final_ref and p.execution
        final=self.store.get(cp.final_ref,FinalFilmCandidate)
        if cp.qa_ref is None:
            checks,failures=final_qa(p.execution.media.path(final.media),final.profile,final.duration_ms,final.media.content_hash)
            qa=FinalTechnicalQA.seal(scope=inputs.scope,run_id=inputs.run_id,film_version=cp.film_version,
                candidate_ref=cp.final_ref,media_hash=final.media.content_hash,outcome='FAIL' if failures else 'PASS',checks=checks,failures=failures)
            cp=self.save(inputs,qa_ref=self.store.put(qa))
        assert cp.qa_ref
        if self.store.get(cp.qa_ref,FinalTechnicalQA).outcome!='PASS':
            return self.wait(inputs,'final-technical-repair',cp.qa_ref)
        if cp.review_ref is None:
            if self.reviewer is None:
                return self.wait(inputs,'final-creative-review',cp.final_ref)
            review=FinalCreativeReview.model_validate((await self.reviewer.review_film(final)).model_dump())
            if (review.candidate_ref,review.media_hash,review.scope,review.run_id,review.film_version)!=(cp.final_ref,final.media.content_hash,inputs.scope,inputs.run_id,cp.film_version):
                raise ValueError('Final Review exact version mismatch')
            live = any(p.execution.store.get(p.execution.store.get(u.candidate_ref,ReviewedAVCandidate).operation_ref,
                ExecutionOperation).authorization.execution_mode == 'CONTROLLED_LIVE' for u in cp.units if u.candidate_ref)
            if live and review.qualification == 'OFFLINE_FIXTURE':
                return self.wait(inputs,'qualified-final-creative-review',cp.final_ref)
            cp=self.save(inputs,review_ref=self.store.put(review))
        assert cp.review_ref
        review=self.store.get(cp.review_ref,FinalCreativeReview)
        if review.outcome=='REVISE':
            child_id=cp.revision_child_run_id or f'{inputs.run_id}:final-revision:{cp.film_version}'
            if cp.revision_child_run_id is None:
                from drama_plugin.creative_engine.feedback import CANON_OWNERS,DIRECTION_OWNERS
                from drama_plugin.creative_engine.contracts import RevisionRequest
                from drama_plugin.professional_design.resolver import professional_owner_domain
                requests: dict[VersionRef,RevisionRequest]={}
                observations=[o for o in review.observations if o.required_revision]
                if len(observations)!=1:
                    return self.wait(inputs,'bounded-final-owner-arbitration',cp.review_ref)
                observation=observations[0]
                for unit in cp.units:
                    if unit.shot_id not in review.affected_shots:
                        continue
                    if observation.owner in CANON_OWNERS:
                        owner,kind,domain=Authority.CANON,Kind.SCENE,None
                    elif observation.owner in DIRECTION_OWNERS:
                        owner,kind,domain=Authority.DIRECTION,Kind.SHOT,None
                    else:
                        owner,kind,domain=Authority.PROFESSIONAL,Kind.PROFESSIONAL,professional_owner_domain(observation.owner)
                        if domain is None:
                            return self.wait(inputs,'final-owner-resolution',cp.review_ref)
                    refs=[r for r in unit.refs if p.creative_versions.resolve(r).kind==kind and (domain is None or getattr(p.creative_versions.resolve(r).body,'domain',None)==domain)]
                    if len(refs)!=1 or unit.revision_depth>=3:
                        return self.wait(inputs,'final-revision-bound',cp.review_ref)
                    assert observation.required_revision
                    requests[refs[0]]=RevisionRequest(owner=owner,target_ref=refs[0],finding_ref=cp.review_ref,
                        instruction=observation.required_revision,depth=unit.revision_depth+1)
                feedback=FilmRevisionFeedback.seal(scope=inputs.scope,run_id=inputs.run_id,film_version=cp.film_version,
                    candidate_ref=cp.final_ref,decision_or_review_ref=cp.review_ref,requests=tuple(requests.values()))
                self.revision_run(inputs.run_id,feedback,child_id)
                cp=self.save(inputs,revision_child_run_id=child_id)
                return self.wait(inputs,'final-owner-revision',ArtifactReference(owner='runtime-run',artifact_ref=child_id,version=1))
            if not await self.child(child_id):
                return self.wait(inputs,'final-owner-revision',ArtifactReference(owner='runtime-run',artifact_ref=child_id,version=1))
            fixed=self.store.checkpoint(child_id)
            return self.success(self.save(inputs,units=fixed.units,film_version=fixed.film_version,
                plan_ref=fixed.plan_ref,final_ref=fixed.final_ref,qa_ref=fixed.qa_ref,review_ref=fixed.review_ref,
                acceptance_ref=fixed.acceptance_ref))
        if review.outcome!='PASS':
            return self.wait(inputs,'final-creative-review',cp.review_ref)
        return self.success(cp)
    def revision_run(self, parent_id: str, feedback: FilmRevisionFeedback, run_id: str) -> RuntimeRun:
        p,cp=self.plugin,self.store.checkpoint(parent_id)
        parent=p.runtime.store.load(parent_id)
        if feedback.candidate_ref!=cp.final_ref or feedback.scope!=parent.scope or feedback.run_id!=parent_id or feedback.film_version!=cp.film_version:
            raise ValueError('Feedback must pin exact Film/version/hash')
        final=self.store.get(feedback.candidate_ref,FinalFilmCandidate)
        body,_,_=self.store.ledger.get_artifact(feedback.decision_or_review_ref.owner,feedback.decision_or_review_ref)
        if feedback.decision_or_review_ref.owner=='user-decision':
            decision=UserDecisionRecord.model_validate(body)
            if decision.run_id!=parent_id or decision.category!=DecisionCategory.FINAL_ACCEPTANCE or decision.accepted or decision.source_ref!=cp.final_ref:
                raise ValueError('Exact final rejection required')
        elif feedback.decision_or_review_ref.owner=='final-creative-review':
            review=FinalCreativeReview.model_validate(body)
            if review.outcome!='REVISE' or review.candidate_ref!=cp.final_ref:
                raise ValueError('Exact final REVISE review required')
        else:
            raise ValueError('Wrong final feedback authority')
        targets={request.target_ref:request for request in feedback.requests}
        if len(targets)!=len(feedback.requests):
            raise ValueError('Duplicate revision targets')
        if not set(targets)<=set(r for u in cp.units for r in u.refs):
            raise ValueError('Feedback targets wrong Shot/version')
        from drama_plugin.creative_engine.contracts import AUTHORITY
        for target,request in targets.items():
            if request.finding_ref!=feedback.decision_or_review_ref or request.owner!=AUTHORITY[p.creative_versions.resolve(target).kind]:
                raise ValueError('Feedback owner/finding mismatch')
        ref=self.store.put(feedback)
        try:
            retained=p.runtime.store.load(run_id)
        except KeyError:
            retained=None
        if retained:
            if retained.scope!=parent.scope or retained.workflow_id!=REVISION_WORKFLOW or self.store.checkpoint(run_id).revision_parent_ref!=ref:
                raise ValueError('Revision Run identity reused for different feedback')
            return retained
        units=list(cp.units)
        for slot,unit in enumerate(units):
            requests=[targets[r] for r in unit.refs if r in targets]
            if not requests:
                continue
            if len(requests)!=1 or unit.revision_depth>=3 or unit.production_run_id is None:
                raise ValueError('Bounded revision needs one owner per affected unit')
            request=requests[0]
            revision_id=f'{run_id}:unit:{slot}:revision:{unit.revision_depth+1}'
            try:
                existing=p.runtime.store.load(revision_id)
            except KeyError:
                p.create_creative_revision_run(unit.production_run_id,request,run_id=revision_id)
            else:
                if p.creative.state.input(existing.run_id).revision!=request:
                    raise ValueError('Revision child identity conflict')
            units[slot]=ShotUnit.model_validate({**unit.model_dump(),'production_run_id':revision_id,
                'package_ref':None,'candidate_ref':None,'generation_run_id':None,'execution_run_id':None,'revision_depth':unit.revision_depth+1})
        run=p.runtime.draft_run(work_id=parent.scope.work_id,mode=parent.mode,workflow_id=REVISION_WORKFLOW,run_id=run_id)
        self.store.bind(run_id,run.scope,self.store.input(parent_id))
        self.store.save(run_id,run.scope,FilmCheckpoint.model_validate({**cp.model_dump(),'units':tuple(units),
            'film_version':cp.film_version+1,'revision_parent_ref':ref,'revision_child_run_id':None,'final_ref':None,'qa_ref':None,'review_ref':None,'acceptance_ref':None,'delivery_ref':None}))
        return p.runtime.store.create(run)

    async def deliver(self, inputs: CapabilityInput) -> CapabilityResult:
        cp=self.store.checkpoint(inputs.run_id)
        if cp.delivery_ref:
            return self.success(cp)
        assert cp.final_ref and cp.qa_ref and cp.review_ref
        if cp.acceptance_ref and cp.revision_child_run_id:
            body,scope,_=self.store.ledger.get_artifact('user-decision',cp.acceptance_ref)
            record=UserDecisionRecord.model_validate(body)
            if scope!=inputs.scope or record.run_id!=cp.revision_child_run_id or record.category!=DecisionCategory.FINAL_ACCEPTANCE or not record.accepted or record.source_ref!=cp.final_ref or self.plugin.runtime.store.load(record.run_id).state!=RuntimeState.SUCCEEDED:
                raise ValueError('Delegated final acceptance mismatch')
            ref=cp.acceptance_ref
        else:
            ref,_=self.decision_record(inputs,DecisionCategory.FINAL_ACCEPTANCE,cp.final_ref)
        final=self.store.get(cp.final_ref,FinalFilmCandidate)
        qa=self.store.get(cp.qa_ref,FinalTechnicalQA)
        assert cp.review_ref
        review=self.store.get(cp.review_ref,FinalCreativeReview)
        if qa.outcome!='PASS' or review.outcome!='PASS' or qa.candidate_ref!=cp.final_ref or review.candidate_ref!=cp.final_ref:
            raise ValueError('Final delivery requires current reviewed candidate')
        if any(self.plugin.creative_versions.stale(r) for unit in cp.units for r in unit.refs):
            raise ValueError('Accepted Film dependency stale')
        value=self.store.input(inputs.run_id)
        delivery=FinalDelivery.seal(scope=inputs.scope,run_id=inputs.run_id,film_version=cp.film_version,
            candidate_ref=cp.final_ref,media=final.media,canonical_media_ref=final.canonical_media_ref,subtitle_ref=final.subtitle_ref,technical_ref=cp.qa_ref,
            creative_ref=cp.review_ref,acceptance_ref=ref,source_ref=value.source_ref,rights_refs=value.rights_refs,profile=value.profile)
        return self.success(self.save(inputs,acceptance_ref=ref,delivery_ref=self.store.put(delivery)))
