"""Domain actions for the one Runtime. Author content is supplied through typed ports."""
from __future__ import annotations
from drama_plugin.creative_engine.contracts import scope_contains

from typing import TYPE_CHECKING

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.authors import CanonAuthor, CreativeDirectionAuthor, ProfessionalAuthor
from drama_plugin.creative_engine.contracts import (
    AUTHORITY, Authority, AuthorRequest, CanonDraft, CreativeCheckpoint, DesignBody, FilmInput,
    Kind, SceneBody, ScriptBody, ShotBody, SourceBody, VersionRef, WorkBody,
)
from drama_plugin.creative_engine.diagnostics import (AuthorResultFailure, failure,
    validation_failure, run_author_capability)
from drama_plugin.execution.transport import CapabilityAbsent
from pydantic import ValidationError
from drama_plugin.creative_engine.routes import RouteSelector
from drama_plugin.creative_engine.sources import NativeCreativeSources
from drama_plugin.creative_engine.store import CreativeStateStore, CreativeVersionStore
from drama_plugin.governance.contracts import GateCode, GateFinding
from drama_plugin.governance.governor import GateGovernor
from drama_plugin.governance.store import FindingStore
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.production.assembler import ShotAssembler
from drama_plugin.production.store import PackageStore
from drama_plugin.professional_design.resolver import ProfessionalDesignResolver
from drama_plugin.runtime.capabilities import TargetCapability
from drama_plugin.runtime.policy import AUTHOR_CONTENT_ATTEMPT_LIMIT
from drama_plugin.runtime.contracts import (
    ArtifactReference, CapabilityInput, CapabilityResult, DecisionCategory, ResultStatus, RunMode,
    ExecutionInspection, ExecutionRevision, RecoveryClass,
    RuntimeRun, RuntimeScope, RuntimeState, UserDecisionRequest,
)

if TYPE_CHECKING:
    from drama_plugin.runtime.engine import RuntimeEngine
    from drama_plugin.creative_engine.persistence import NativeTaskPersistence

PREFIX = "creative."
KEYS = ("source", "canon", "direction", "professional", "route", "review", "adoption", "package", "prerequisite")


class CreativeEngineCapabilities:
    def __init__(self, versions: CreativeVersionStore, state: CreativeStateStore,
                 packages: PackageStore, governor: GateGovernor, findings: FindingStore,
                 canon: CanonAuthor | None = None, direction: CreativeDirectionAuthor | None = None,
                 professional: ProfessionalDesignResolver | None = None):
        self.versions, self.state, self.packages = versions, state, packages
        self.governor, self.findings = governor, findings
        self.canon_author, self.direction_author, self.professional_author = canon, direction, professional
        from drama_plugin.creative_engine.screenplay import ScreenplayWorkshop
        self.screenplays = ScreenplayWorkshop(versions.objects)
        self.route_selector = RouteSelector()
        self.runtime: RuntimeEngine | None = None
        self.reference_production = None
        self.native_task_persistence: NativeTaskPersistence | None = None

    def registrations(self) -> dict[str, TargetCapability]:
        methods = (self.source, self.canon, self.direction, self.professional, self.route,
                   self.review, self.adoption, self.package, self.prerequisite)
        inspectors = {"canon": self.inspect_canon_execution, "direction": self.inspect_direction_execution,
            "professional": self.inspect_professional_execution}
        return {PREFIX + key + ":v1": TargetCapability(method, replay_safe=True,
                    inspect_execution=inspectors.get(key))
                for key, method in zip(KEYS, methods, strict=True)}

    def _inspection(self, inputs: CapabilityInput, owner: Authority, fingerprint: str) -> ExecutionInspection:
        request = self._request(inputs, owner)
        cp = self.state.checkpoint(inputs.run_id)
        immutable_kinds = ({Kind.SOURCE} if owner == Authority.CANON else
            {Kind.SOURCE, Kind.WORK, Kind.SCRIPT, Kind.SCENE} if owner == Authority.DIRECTION else
            {Kind.SOURCE, Kind.WORK, Kind.SCRIPT, Kind.SCENE, Kind.SHOT})
        if any(self.versions.stale(ref) for ref in request.source_refs if self.versions.resolve(ref).kind in immutable_kinds):
            raise ValueError("CREATIVE_EXECUTION_INPUT_STALE")
        input_identity = {"scope": inputs.scope.model_dump(mode="json", by_alias=True),
            "refs": [ref.model_dump(mode="json", by_alias=True) for ref in request.source_refs],
            "film_input": self.state.input(inputs.run_id).model_dump(mode="json", by_alias=True)}
        if owner == Authority.PROFESSIONAL and cp.screenplay_ref is not None:
            input_identity['scene_screenplay'] = cp.screenplay_ref.model_dump(mode="json", by_alias=True)
        return ExecutionInspection(revision=ExecutionRevision(fingerprint=fingerprint,
            input_fingerprint=sha256_canonical(input_identity)),
            retry_limit=AUTHOR_CONTENT_ATTEMPT_LIMIT,
            completed=inputs.operation_id in cp.completed_operations or self.versions.has_author_output(
                inputs.operation_id, {Authority.CANON: "canon", Authority.DIRECTION: "direction", Authority.PROFESSIONAL: "professional"}[owner]))

    def inspect_canon_execution(self, inputs: CapabilityInput) -> ExecutionInspection | None:
        from drama_plugin.creative_engine.backends import FormalCanonAuthor
        if self._author_required(inputs, Authority.CANON) and (self.canon_author is None or
                isinstance(self.canon_author, FormalCanonAuthor) and not self.canon_author.client.config.available("canon")):
            raise CapabilityAbsent("FORMAL_CANON_AUTHOR_CONFIGURATION_ABSENT")
        return self._inspection(inputs, Authority.CANON, self.canon_author.execution_fingerprint()) if isinstance(self.canon_author, FormalCanonAuthor) else None

    def inspect_professional_execution(self, inputs: CapabilityInput) -> ExecutionInspection | None:
        from drama_plugin.creative_engine.backends import FormalProfessionalAuthor
        author = self.professional_author.author if self.professional_author else None
        if self._author_required(inputs, Authority.PROFESSIONAL) and (author is None or
                isinstance(author, FormalProfessionalAuthor) and not author.client.config.available("professional")):
            raise CapabilityAbsent("FORMAL_PROFESSIONAL_AUTHOR_CONFIGURATION_ABSENT")
        return self._inspection(inputs, Authority.PROFESSIONAL, author.execution_fingerprint(
            self._request(inputs, Authority.PROFESSIONAL))) if isinstance(author, FormalProfessionalAuthor) else None

    def inspect_direction_execution(self, inputs: CapabilityInput) -> ExecutionInspection | None:
        from drama_plugin.creative_engine.backends import FormalDirectionAuthor
        if self._author_required(inputs, Authority.DIRECTION) and (self.direction_author is None or
                isinstance(self.direction_author, FormalDirectionAuthor) and not self.direction_author.client.config.available("direction")):
            raise CapabilityAbsent("FORMAL_DIRECTION_AUTHOR_CONFIGURATION_ABSENT")
        if not isinstance(self.direction_author, FormalDirectionAuthor):
            return None
        from drama_plugin.creative_engine.backends import FormalCanonAuthor
        fingerprint = self.direction_author.execution_fingerprint()
        if isinstance(self.canon_author, FormalCanonAuthor):
            fingerprint = sha256_canonical([fingerprint, self.canon_author.scene_execution_fingerprint()])
        inspection = self._inspection(inputs, Authority.DIRECTION, fingerprint)
        request = self._request(inputs, Authority.DIRECTION)
        revising = self.state.input(inputs.run_id).revision is not None
        return ExecutionInspection(revision=inspection.revision,
            retry_limit=inspection.retry_limit,
            completed=inspection.completed or (request.shot is not None and not revising))

    def _author_required(self, inputs: CapabilityInput, owner: Authority) -> bool:
        request = self._request(inputs, owner)
        cp = self.state.checkpoint(inputs.run_id)
        role = {Authority.CANON: "canon", Authority.DIRECTION: "direction", Authority.PROFESSIONAL: "professional"}[owner]
        if inputs.operation_id in cp.completed_operations or self.versions.has_author_output(inputs.operation_id, role):
            return False
        revision = self.state.input(inputs.run_id).revision
        revising = revision is not None and revision.owner == owner
        return not ((owner == Authority.CANON and request.canon is not None or
            owner == Authority.DIRECTION and request.shot is not None) and not revising)

    def _success(self, checkpoint: CreativeCheckpoint) -> CapabilityResult:
        return CapabilityResult(status=ResultStatus.SUCCEEDED,
            artifact_refs=(checkpoint.package_ref,) if checkpoint.package_ref else
                tuple(ref.runtime_ref() for ref in checkpoint.refs))

    def _save(self, inputs: CapabilityInput, checkpoint: CreativeCheckpoint, **changes: object) -> CreativeCheckpoint:
        checked = CreativeCheckpoint.model_validate({**checkpoint.model_dump(), **changes,
            "completed_operations": (*checkpoint.completed_operations, inputs.operation_id)})
        self.state.save(inputs.run_id, inputs.scope, checked)
        return checked

    def _absence(self, inputs: CapabilityInput, owner: str) -> CapabilityResult:
        assert self.runtime is not None
        evidence = self.state.input(inputs.run_id).source_ref.runtime_ref()
        finding = GateFinding.classified(GateCode.CAPABILITY_NOT_IMPLEMENTED, owner=owner,
            scope=inputs.scope, evidence_ref=evidence, required=True)
        decision = self.governor.govern((finding,), scope=inputs.scope,
            mode=self.runtime.store.load(inputs.run_id).mode, package_ref=None)
        ref = self.findings.put_decision(decision, run_id=inputs.run_id)
        return CapabilityResult(status=ResultStatus.FAILED, code="AUTHOR_CAPABILITY_ABSENT",
            recovery_class=RecoveryClass.HARD_BLOCK, artifact_refs=(ref,))

    def _blocked(self, inputs: CapabilityInput, code: GateCode) -> CapabilityResult:
        assert self.runtime is not None
        finding = GateFinding.classified(code, owner="creative-contract", scope=inputs.scope,
            evidence_ref=self.state.input(inputs.run_id).source_ref.runtime_ref(), required=True)
        decision = self.governor.govern((finding,), scope=inputs.scope,
            mode=self.runtime.store.load(inputs.run_id).mode, package_ref=None)
        ref = self.findings.put_decision(decision, run_id=inputs.run_id)
        return CapabilityResult(status=ResultStatus.FAILED, code=code.value,
            recovery_class=RecoveryClass.HARD_BLOCK, artifact_refs=(ref,))

    def _request(self, inputs: CapabilityInput, owner: Authority) -> AuthorRequest:
        value = self.state.input(inputs.run_id)
        checkpoint = self.state.checkpoint(inputs.run_id)
        source = self.versions.resolve(value.source_ref)
        if not scope_contains(source.scope, inputs.scope) or not isinstance(source.body, SourceBody):
            raise ValueError("PACKAGE_SCOPE_MISMATCH")
        versions = [self.versions.resolve(ref) for ref in checkpoint.refs]
        work = next((v.body for v in versions if v.kind == Kind.WORK), None)
        script = next((v.body for v in versions if v.kind == Kind.SCRIPT), None)
        scene = next((v.body for v in versions if v.kind == Kind.SCENE), None)
        shot = next((v.body for v in versions if v.kind == Kind.SHOT), None)
        canon = CanonDraft(work=work, script=script, scene=scene) if isinstance(work, WorkBody) and isinstance(
            script, ScriptBody) and isinstance(scene, SceneBody) else None
        context = self.screenplays.objects.read_ref(checkpoint.screenplay_ref) if checkpoint.screenplay_ref else self.screenplays.bound_packet(value.screenplay_ref, work_id=inputs.scope.work_id, scene_id=inputs.scope.scene_id)
        professional = self.screenplays.professional_context(context, work_id=inputs.scope.work_id,
            scene_id=inputs.scope.scene_id) if owner in {Authority.DIRECTION, Authority.PROFESSIONAL} else None
        if owner == Authority.DIRECTION and professional is not None:
            # Direction inherits selected Work meaning, not department originals.
            professional = {'filmLook': professional['filmLook']}
        if owner == Authority.PROFESSIONAL and professional is not None:
            shot_ref = next((v.ref() for v in versions if v.kind == Kind.SHOT), None)
            professional['currentDesigns'] = [{'ref': v.ref().model_dump(mode='json', by_alias=True),
                'domain': v.body.domain.value, 'facts': v.body.facts} for v in versions
                if v.kind == Kind.PROFESSIONAL and isinstance(v.body, DesignBody)
                and v.scope == inputs.scope and (shot_ref is None or shot_ref in v.source_refs)]
        # Preserve exact refs across native handoffs; author_payload omits them
        # from model inputs; Canon never receives preselected aesthetic rules.
        return AuthorRequest(scope=inputs.scope, source=source.body, source_refs=checkpoint.refs,
            screenplay_context=context, professional_context=professional,
            canon=canon, shot=shot if isinstance(shot, ShotBody) else None, revision=value.revision if value.revision and value.revision.owner == owner else None)

    def _replay(self, inputs: CapabilityInput) -> CapabilityResult | None:
        cp = self.state.checkpoint(inputs.run_id)
        return self._success(cp) if inputs.operation_id in cp.completed_operations else None

    def _round_allowed(self, inputs: CapabilityInput) -> bool:
        return self.state.checkpoint(inputs.run_id).author_rounds < self.state.input(inputs.run_id).max_author_rounds

    async def source(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        value, cp = self.state.input(inputs.run_id), self.state.checkpoint(inputs.run_id)
        try:
            source = self.versions.resolve(value.source_ref)
            if not scope_contains(source.scope, inputs.scope) or source.kind != Kind.SOURCE:
                return self._blocked(inputs, GateCode.PACKAGE_SCOPE_MISMATCH)
            refs = value.base_refs or value.approved_canon_refs
            kinds = {self.versions.resolve(r).kind for r in refs}
            if value.approved_canon_refs and kinds != {Kind.WORK, Kind.SCRIPT, Kind.SCENE}:
                return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
            for ref in refs:
                artifact = self.versions.resolve(ref)
                if not scope_contains(artifact.scope, inputs.scope):
                    return self._blocked(inputs, GateCode.PACKAGE_SCOPE_MISMATCH)
                if value.approved_canon_refs and (artifact.state != "ADOPTED" or self.versions.stale(ref)):
                    return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
            selected_refs = {value.source_ref, *refs}
            if any(parent not in selected_refs for ref in refs for parent in self.versions.resolve(ref).source_refs):
                return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
            # Adoption remaps parents before descendants. A closed but unordered
            # list must not retain reviewed parents beneath an adopted child.
            seen = {value.source_ref}
            for ref in refs:
                if any(parent not in seen for parent in self.versions.resolve(ref).source_refs):
                    return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
                seen.add(ref)
            revision = value.revision
            if revision:
                target = self.versions.resolve(revision.target_ref)
                if not scope_contains(target.scope, inputs.scope) or revision.target_ref not in refs:
                    return self._blocked(inputs, GateCode.PACKAGE_SCOPE_MISMATCH)
                if AUTHORITY[target.kind] != revision.owner:
                    return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
                signature = sha256_canonical([revision.owner, target.kind, revision.instruction])
                if signature in value.prior_revision_signatures or len(value.prior_revision_signatures) >= 3:
                    return CapabilityResult(status=ResultStatus.FAILED, code="REVISION_CYCLE_OR_DEPTH_BOUND",
                        recovery_class=RecoveryClass.HARD_BLOCK)
                self.versions.invalidate(revision.target_ref)
            refs = tuple(r for r in refs if self.versions.resolve(r).kind != Kind.SOURCE)
            return self._success(self._save(inputs, cp, refs=(value.source_ref, *refs)))
        except (ValueError, OSError, KeyError):
            return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)

    async def canon(self, inputs: CapabilityInput) -> CapabilityResult:
        assert self.runtime is not None
        cp = self.state.checkpoint(inputs.run_id)
        return await run_author_capability(self._canon, role="canon", versions=self.versions,
            inputs=inputs, run=self.runtime.store.load(inputs.run_id), version_refs=cp.refs, author_round=cp.author_rounds)

    async def _canon(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        cp, value = self.state.checkpoint(inputs.run_id), self.state.input(inputs.run_id)
        request = self._request(inputs, Authority.CANON)
        needs = request.canon is None or bool(value.revision and value.revision.owner == Authority.CANON)
        if not needs:
            return self._success(self._save(inputs, cp))
        revision_path = None
        if value.revision and value.revision.owner == Authority.CANON:
            revision_path = self.versions._path("owner-revision", value.revision.model_dump(mode="json", by_alias=True))
            if revision_path.exists():
                from pydantic import TypeAdapter
                fixed = TypeAdapter(tuple[VersionRef, ...]).validate_json(revision_path.read_text())
                if fixed[0] != value.source_ref or any(not scope_contains(self.versions.resolve(r).scope, inputs.scope) for r in fixed):
                    return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
                return self._success(self._save(inputs, cp, refs=fixed))
        if self.canon_author is None:
            return self._absence(inputs, Authority.CANON.value)
        from pydantic import TypeAdapter
        draft = self.versions.author_output(inputs.operation_id, "canon", request.source_refs, TypeAdapter(CanonDraft))
        if draft is None:
            if not self._round_allowed(inputs):
                return CapabilityResult(status=ResultStatus.FAILED, code="AUTHOR_ROUND_BOUND", recovery_class=RecoveryClass.HARD_BLOCK)
            self.state.save(inputs.run_id, inputs.scope, CreativeCheckpoint.model_validate(
                {**cp.model_dump(), "author_rounds": cp.author_rounds + 1}))
            from drama_plugin.creative_engine.backends import FormalCanonAuthor
            if isinstance(self.canon_author, FormalCanonAuthor) and request.canon is None:
                from drama_plugin.creative_engine.screenplay_author import native_film_original
                request = request.model_copy(update={'screenplay_context': await native_film_original(
                    self.screenplays, self.canon_author, request, operation=inputs.operation_id)})
                assert request.screenplay_context is not None
                cp = CreativeCheckpoint.model_validate({**self.state.checkpoint(inputs.run_id).model_dump(),
                    'screenplay_ref': self.screenplays.objects.put('native-film-handoff:' + inputs.run_id, request.screenplay_context)})
                self.state.save(inputs.run_id, inputs.scope, cp)
            try:
                draft = CanonDraft.model_validate((await self.canon_author.author(request)).model_dump())
            except ValidationError as error:
                from pydantic import JsonValue
                schema = TypeAdapter(dict[str, JsonValue]).validate_python(TypeAdapter(CanonDraft).json_schema(by_alias=True))
                raise AuthorResultFailure(validation_failure(error, role="canon", output_schema=schema)) from None
            from drama_plugin.creative_engine.backends import validate_selected_screenplay
            validate_selected_screenplay(request, draft)
            self.versions.retain_author_output(inputs.operation_id, "canon", request.source_refs, draft)
        from drama_plugin.creative_engine.backends import validate_selected_screenplay
        validate_selected_screenplay(request, draft)
        original_sources = [r.model_dump(mode='json', by_alias=True) for r in request.source_refs]
        self.screenplays.native_original(inputs.operation_id, work_id=inputs.scope.work_id,
            scope='FILM', scene_id=None, text=draft.script.screenplay, source_refs=original_sources)
        self.screenplays.native_original(inputs.operation_id, work_id=inputs.scope.work_id,
            scope='SCENE', scene_id=inputs.scope.scene_id, text=draft.scene.scene_text, source_refs=original_sources)
        refs = [value.source_ref]
        for kind, body in ((Kind.WORK, draft.work), (Kind.SCRIPT, draft.script), (Kind.SCENE, draft.scene)):
            existing = next((self.versions.resolve(r) for r in cp.refs if self.versions.resolve(r).kind == kind), None)
            if existing and existing.body == body and existing.source_refs == tuple(refs) and not self.versions.stale(existing.ref()):
                refs.append(existing.ref())
            else:
                refs.append(self.versions.write(writer=Authority.CANON, kind=kind,
                    scope=existing.scope if existing else inputs.scope, body=body, sources=tuple(refs),
                    operation=inputs.operation_id + ":" + kind.value))
        if revision_path is not None:
            from drama_plugin.contracts.base import canonical_json
            self.versions.io.write(revision_path, canonical_json([r.model_dump(mode="json", by_alias=True) for r in refs]))
        rounds = self.state.checkpoint(inputs.run_id).author_rounds
        return self._success(self._save(inputs, cp, refs=tuple(refs), author_rounds=rounds))

    async def direction(self, inputs: CapabilityInput) -> CapabilityResult:
        assert self.runtime is not None
        cp = self.state.checkpoint(inputs.run_id)
        return await run_author_capability(self._direction, role="direction", versions=self.versions,
            inputs=inputs, run=self.runtime.store.load(inputs.run_id), version_refs=cp.refs, author_round=cp.author_rounds)

    async def _direction(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        cp, value = self.state.checkpoint(inputs.run_id), self.state.input(inputs.run_id)
        request = self._request(inputs, Authority.DIRECTION)
        needs = request.shot is None or bool(value.revision and value.revision.owner in {Authority.CANON, Authority.DIRECTION})
        if not needs:
            return self._success(self._save(inputs, cp))
        if self.direction_author is None:
            return self._absence(inputs, Authority.DIRECTION.value)
        from pydantic import TypeAdapter
        shot = self.versions.author_output(inputs.operation_id, "direction", request.source_refs, TypeAdapter(ShotBody))
        if shot is None:
            if not self._round_allowed(inputs):
                return CapabilityResult(status=ResultStatus.FAILED, code="AUTHOR_ROUND_BOUND", recovery_class=RecoveryClass.HARD_BLOCK)
            self.state.save(inputs.run_id, inputs.scope, CreativeCheckpoint.model_validate(
                {**cp.model_dump(), "author_rounds": cp.author_rounds + 1}))
            from drama_plugin.creative_engine.backends import FormalCanonAuthor
            if isinstance(self.canon_author, FormalCanonAuthor) and request.canon is not None:
                from drama_plugin.creative_engine.screenplay_author import native_scene_screenplay, native_film_decision
                script_version = next((v for r in request.source_refs if (v := self.versions.resolve(r)).kind == Kind.SCRIPT), None)
                if script_version and script_version.state != 'ADOPTED':
                    request = request.model_copy(update={'screenplay_context': await native_film_decision(
                        self.screenplays, self.canon_author, request, operation=inputs.operation_id,
                        screenplay=request.canon.script.screenplay)})
                request = request.model_copy(update={'screenplay_context': await native_scene_screenplay(
                    self.screenplays, self.canon_author, request, operation=inputs.operation_id,
                    scene_id=inputs.scope.scene_id or inputs.scope.work_id + ':scene')})
                assert request.screenplay_context is not None
                cp = CreativeCheckpoint.model_validate({**self.state.checkpoint(inputs.run_id).model_dump(),
                    'screenplay_ref': self.screenplays.objects.put('native-scene-handoff:' + inputs.run_id, request.screenplay_context)})
                self.state.save(inputs.run_id, inputs.scope, cp)
            try:
                shot = ShotBody.model_validate((await self.direction_author.author(request)).model_dump())
            except ValidationError as error:
                from pydantic import JsonValue
                schema = TypeAdapter(dict[str, JsonValue]).validate_python(TypeAdapter(ShotBody).json_schema(by_alias=True))
                raise AuthorResultFailure(validation_failure(error, role="direction", output_schema=schema)) from None
        if request.canon is None or not set(shot.spoken_ids) <= {line.id for line in request.canon.scene.dialogue}:
            raise AuthorResultFailure(failure("DIALOGUE_AUTHORITY", "DIRECTION_DIALOGUE_AUTHORITY_MISMATCH",
                field_path=("spokenIds",), validator="CreativeEngineCapabilities.direction.canon_dialogue_authority"))
        self.versions.retain_author_output(inputs.operation_id, "direction", request.source_refs, shot)
        refs = tuple(r for r in cp.refs if self.versions.resolve(r).kind not in {Kind.SHOT, Kind.PROFESSIONAL})
        ref = self.versions.write(writer=Authority.DIRECTION, kind=Kind.SHOT, scope=inputs.scope,
            body=shot, sources=refs, operation=inputs.operation_id)
        return self._success(self._save(inputs, cp, refs=(*refs, ref), author_rounds=self.state.checkpoint(inputs.run_id).author_rounds))

    async def professional(self, inputs: CapabilityInput) -> CapabilityResult:
        assert self.runtime is not None
        cp = self.state.checkpoint(inputs.run_id)
        return await run_author_capability(self._professional, role="professional", versions=self.versions,
            inputs=inputs, run=self.runtime.store.load(inputs.run_id), version_refs=cp.refs, author_round=cp.author_rounds)

    async def _professional(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        cp = self.state.checkpoint(inputs.run_id)
        request = self._request(inputs, Authority.PROFESSIONAL)
        if request.shot is None:
            raise CapabilityAbsent("PROFESSIONAL_SHOT_PREREQUISITE_ABSENT")
        if self.professional_author is not None:
            from drama_plugin.professional_design.asset_sequence import AssetPreparationPending
            while True:
                try:
                    request = await self.professional_author.prepare_assets(request)
                    break
                except AssetPreparationPending as pending:
                    if self.reference_production is not None:
                        result = await self.reference_production.pending(pending.ref, inputs.run_id, request)
                        if result.status == ResultStatus.SUCCEEDED:
                            continue
                        return result
                    return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, external_ref=pending.runtime_ref(),
                        recovery_class=RecoveryClass.WAIT_EXTERNAL, artifact_refs=(pending.runtime_ref(),))
        native = NativeCreativeSources(self.versions, cp.refs)
        bound = native.bound_professionals(native.version(Kind.SHOT))
        bodies = [v.body for v in bound]
        required = {*request.shot.professional_domains, *(body.domain for body in bodies if isinstance(body, DesignBody))}
        current = {body.domain for body in bodies if isinstance(body, DesignBody)}
        inheritance_current = (self.professional_author is None or
            self.professional_author.asset_inheritance_current(request, (body for body in bodies if isinstance(body, DesignBody))))
        if required <= current and inheritance_current and not (request.revision and request.revision.owner == Authority.PROFESSIONAL):
            return self._success(self._save(inputs, cp))
        if self.professional_author is None or self.professional_author.author is None:
            return self._absence(inputs, Authority.PROFESSIONAL.value)
        from pydantic import TypeAdapter
        # Keep upstream department parents; replace only this Shot's realizations.
        # The required-domain query does not rewrite the retained thin Shot.
        refs = tuple(r for r in cp.refs if self.versions.resolve(r).kind != Kind.PROFESSIONAL
            or self.versions.resolve(r).scope != inputs.scope)
        fixed_request = AuthorRequest.model_validate({**request.model_dump(), "source_refs": refs,
            "shot": {**request.shot.model_dump(), "professional_domains": tuple(sorted(required))}})
        author_operation = inputs.operation_id
        asset_bindings = self.professional_author.asset_bindings(fixed_request)
        if asset_bindings is not None:
            from drama_plugin.contracts.base import sha256_canonical
            author_operation += ':assets:' + sha256_canonical(asset_bindings)
        designs = self.versions.author_output(author_operation, "professional", refs, TypeAdapter(tuple[DesignBody, ...]))
        if designs is None:
            if not self._round_allowed(inputs):
                return CapabilityResult(status=ResultStatus.FAILED, code="AUTHOR_ROUND_BOUND", recovery_class=RecoveryClass.HARD_BLOCK)
            self.state.save(inputs.run_id, inputs.scope, CreativeCheckpoint.model_validate(
                {**cp.model_dump(), "author_rounds": cp.author_rounds + 1}))
            try:
                designs = tuple(DesignBody.model_validate(d.model_dump()) for d in await (
                    self.professional_author.revise(fixed_request) if fixed_request.revision else self.professional_author.design(fixed_request)))
            except ValidationError as error:
                from pydantic import JsonValue
                schema = TypeAdapter(dict[str, JsonValue]).validate_python(TypeAdapter(tuple[DesignBody, ...]).json_schema(by_alias=True))
                raise AuthorResultFailure(validation_failure(error, role="professional", output_schema=schema)) from None
            except ValueError as error:
                if str(error) != "PROFESSIONAL_SYSTEM_METADATA_MODEL_OWNERSHIP":
                    raise
                raise AuthorResultFailure(failure("DTO_SCHEMA", "PROFESSIONAL_SYSTEM_METADATA_MODEL_OWNERSHIP", role="professional",
                    field_path=("facts", "<system-metadata>"), validator="reject_model_metadata")) from None
        if len(designs) != len(required) or {d.domain for d in designs} != required:
            raise AuthorResultFailure(failure("DTO_SCHEMA", "PROFESSIONAL_DOMAIN_AUTHORITY_MISMATCH", role="professional",
                field_path=("domain",), validator="CreativeEngineCapabilities.professional.required_domains"))
        from drama_plugin.professional_design.provenance import reject_model_metadata
        try:
            for design in designs:
                reject_model_metadata(design.facts)
        except ValueError:
            raise AuthorResultFailure(failure("DTO_SCHEMA", "PROFESSIONAL_SYSTEM_METADATA_MODEL_OWNERSHIP", role="professional",
                field_path=("facts", "<system-metadata>"), validator="reject_model_metadata")) from None
        self.versions.retain_author_output(author_operation, "professional", refs, designs)
        selected = tuple(self.professional_author.persist(self.versions, fixed_request, design,
            operation=author_operation + ":" + design.domain.value) for design in sorted(designs, key=lambda d: d.domain.value))
        return self._success(self._save(inputs, cp, refs=(*refs, *selected),
            author_rounds=self.state.checkpoint(inputs.run_id).author_rounds))

    async def route(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        cp = self.state.checkpoint(inputs.run_id)
        try:
            route = self.state.input(inputs.run_id).route
            available = set(route.available_inputs)
            # Consume formal adopted references already bound by the professional
            # owner, rather than requesting their production again from a label.
            for ref in cp.refs:
                body = self.versions.resolve(ref).body
                if isinstance(body, DesignBody):
                    for asset in body.facts.get('assetBindings', []):
                        if isinstance(asset, dict) and asset.get('referenceMediaIds'):
                            if asset.get('assetType') == 'CHARACTER':
                                available.add('character_reference')
                            elif asset.get('assetType') == 'LOCATION':
                                available.add('environment_reference')
            route = route.model_copy(update={'available_inputs': tuple(sorted(available))})
            plan = self.route_selector.plan(route)
        except ValueError:
            return self._blocked(inputs, GateCode.BUDGET_EXCEEDED)
        assert self.runtime is not None
        children: list[str] = []
        # Only prerequisites become child tasks. Their native owner resolves exact
        # selected asset duties; a route label alone cannot invent reference art.
        for task in plan.tasks[1:]:
            identity = inputs.run_id + ":dependency:" + task.task_id
            try:
                child = self.runtime.store.load(identity)
            except KeyError:
                from drama_plugin.creative_engine.policy import CHILD_WORKFLOW
                child = self.runtime.create_run(work_id=inputs.scope.work_id, scene_id=inputs.scope.scene_id,
                    shot_id=inputs.scope.shot_id, run_id=identity,
                    mode=self.runtime.store.load(inputs.run_id).mode, workflow_id=CHILD_WORKFLOW)
                self.state.bind(identity, inputs.scope, self.state.input(inputs.run_id))
                self.state.save(identity, inputs.scope, CreativeCheckpoint(refs=cp.refs,
                    screenplay_ref=cp.screenplay_ref))
            child = await self.runtime.run(child.run_id)
            children.append(identity)
            if child.state != RuntimeState.SUCCEEDED:
                self.state.save(inputs.run_id, inputs.scope, CreativeCheckpoint.model_validate(
                    {**cp.model_dump(), "route_plan": plan, "child_runs": tuple(children)}))
                if child.last_result is None:
                    return CapabilityResult(status=ResultStatus.FAILED, code="DEPENDENCY_RESULT_ABSENT",
                        recovery_class=RecoveryClass.HARD_BLOCK)
                return child.last_result
        return self._success(self._save(inputs, cp, route_plan=plan, child_runs=tuple(children)))

    async def prerequisite(self, inputs: CapabilityInput) -> CapabilityResult:
        if self.professional_author is not None and self.reference_production is not None:
            from drama_plugin.professional_design.asset_sequence import AssetPreparationPending
            request = self._request(inputs, Authority.PROFESSIONAL)
            try:
                await self.professional_author.prepare_assets(request)
            except AssetPreparationPending as pending:
                return await self.reference_production.pending(pending.ref, inputs.run_id, request)
        # A first-frame/environment route obligation requires its own selected
        # professional artwork. Never synthesize it from the dependency name.
        return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,
            external_ref=self.state.input(inputs.run_id).source_ref.runtime_ref(),
            recovery_class=RecoveryClass.WAIT_EXTERNAL)

    async def review(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        cp = self.state.checkpoint(inputs.run_id)
        if any(self.versions.stale(ref) for ref in cp.refs):
            return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
        try:
            from drama_plugin.professional_design.provenance import ORDER, creative_facts, project_metadata
            revised = []
            for ref in cp.refs:
                artifact = self.versions.resolve(ref)
                if isinstance(artifact.body, DesignBody):
                    self._professional_core(artifact.ref(), cp.refs, inputs.scope)
                    projected = project_metadata(artifact.body, self.versions, artifact.scope, artifact.source_refs)
                    if creative_facts(projected.facts) != creative_facts(artifact.body.facts):
                        raise ValueError("Integrity cannot change creative content")
                    if projected != artifact.body:
                        if artifact.state == "ADOPTED":
                            raise ValueError("Integrity cannot rewrite adopted content")
                        ref = self.versions.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL,
                            scope=artifact.scope, body=projected, sources=artifact.source_refs,
                            operation=inputs.operation_id + ":metadata:" + ref.fingerprint)
                revised.append(ref)
            cp = CreativeCheckpoint.model_validate({**cp.model_dump(), "refs": tuple(revised)})
            self.validate_candidate_integrity(cp, inputs.scope)
        except ValueError:
            return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
        candidate = ArtifactReference(owner="creative-candidate", artifact_ref="creative-candidate:" + cp.candidate_fingerprint(), version=1)
        cp = self._save(inputs, cp, candidate_ref=candidate, candidate_version_refs=cp.refs)
        assert self.runtime is not None
        run = self.runtime.store.load(inputs.run_id)
        if run.mode == RunMode.PRODUCTION:
            finding = GateFinding.classified(GateCode.ADOPTION_REQUIRED, owner="creative-adoption",
                scope=inputs.scope, evidence_ref=candidate)
            decision = self.governor.govern((finding,), scope=inputs.scope, mode=run.mode, package_ref=None)
            self.findings.put_decision(decision, run_id=run.run_id)
        return self._success(cp)

    def _professional_core(self, ref: VersionRef, refs: tuple[VersionRef, ...], scope: RuntimeScope) -> None:
        """Validate each original at its own scope; only real ancestors may differ."""
        from drama_plugin.professional_design.provenance import ORDER
        artifact = self.versions.resolve(ref)
        if not scope_contains(artifact.scope, scope):
            raise ValueError("PROFESSIONAL_SOURCE_PIN_AUTHORITY_MISMATCH")
        core = {r for r in refs for v in (self.versions.resolve(r),)
            if v.kind in ORDER and scope_contains(v.scope, artifact.scope)}
        parents = {r for r in artifact.source_refs if self.versions.resolve(r).kind in ORDER}
        if parents != core:
            raise ValueError("PROFESSIONAL_SOURCE_PIN_AUTHORITY_MISMATCH")
        if artifact.scope != scope:
            roots = [r for r in refs for v in (self.versions.resolve(r),)
                if v.scope == scope and v.kind in {Kind.SHOT, Kind.PROFESSIONAL}]
            seen: set[VersionRef] = set()
            def collect(parent: VersionRef) -> None:
                if parent in seen:
                    return
                if parent not in refs:
                    raise ValueError("PROFESSIONAL_SOURCE_PIN_AUTHORITY_MISMATCH")
                seen.add(parent)
                for ancestor in self.versions.resolve(parent).source_refs:
                    collect(ancestor)
            for root in roots:
                collect(root)
            if ref not in seen:
                raise ValueError("PROFESSIONAL_SOURCE_PIN_AUTHORITY_MISMATCH")

    def validate_candidate_integrity(self, cp: CreativeCheckpoint, scope: RuntimeScope) -> None:
        from drama_plugin.professional_design.provenance import ORDER, validate_metadata
        for ref in cp.refs:
            artifact = self.versions.resolve(ref)
            if isinstance(artifact.body, DesignBody):
                self._professional_core(ref, cp.refs, scope)
                validate_metadata(artifact.body, self.versions, artifact.scope, artifact.source_refs)

    async def reconcile_candidate_integrity(self, run_id: str, expected: ArtifactReference) -> RuntimeRun:
        """Explicit metadata-only revision at ADOPTION wait. Never invokes an author.

        A bounded reference-only journal allows recovery between owner version
        writes and checkpoint publication without erasing the original candidate.
        """
        from drama_plugin.professional_design.provenance import ORDER, creative_facts, project_metadata
        assert self.runtime is not None
        if self.state.ledger is None:
            raise ValueError("Integrity reconciliation requires durable Target state")
        async with self.runtime.store.lock(run_id):
            run = self.runtime.store.load(run_id)
            cp = self.state.checkpoint(run_id)
            action = self.runtime.next_action(run_id)
            if (run.state != RuntimeState.WAITING_USER or run.cursor != 6
                    or run.workflow_id != "source-to-approved-package:v1" or cp.decision_ref or cp.package_ref
                    or action.decision is None or action.decision.category != DecisionCategory.ADOPTION):
                raise ValueError("Integrity reconciliation requires unaccepted Creative ADOPTION wait")
            try:
                saved = self.state.ledger.get_index("creative-integrity-reconciliation", run_id)
            except KeyError:
                saved = None
            if saved is not None:
                if not isinstance(saved, dict) or saved.get("parent") != expected.model_dump(mode="json", by_alias=True):
                    raise ValueError("Integrity revision identity mismatch")
                original = tuple(VersionRef.model_validate(r) for r in saved["originalRefs"])
                published = ArtifactReference.model_validate(saved["candidate"]) if saved.get("candidate") else None
                if cp.candidate_ref not in (expected, published):
                    raise ValueError("Integrity candidate changed")
                retained = tuple(VersionRef.model_validate(r) for r in saved.get("revisedRefs", []))
                if cp.refs not in (original, retained):
                    raise ValueError("Integrity authority inputs changed")
            else:
                if cp.candidate_ref != expected or cp.candidate_version_refs != cp.refs:
                    raise ValueError("Integrity candidate changed")
                original = cp.refs
                self.state.ledger.put_index("creative-integrity-reconciliation", run_id,
                    {"parent": expected.model_dump(mode="json", by_alias=True),
                     "originalRefs": [r.model_dump(mode="json", by_alias=True) for r in original]}, scope=run.scope)
            revised = []
            for ref in original:
                artifact = self.versions.resolve(ref)
                if not isinstance(artifact.body, DesignBody):
                    if self.versions.stale(ref):
                        raise ValueError("Integrity cannot revise Source/Canon/Shot")
                    revised.append(ref)
                    continue
                try:
                    self._professional_core(ref, original, run.scope)
                except ValueError as error:
                    raise ValueError("Integrity cannot repair a wrong authority object") from error
                projected = project_metadata(artifact.body, self.versions, artifact.scope, artifact.source_refs)
                if creative_facts(projected.facts) != creative_facts(artifact.body.facts):
                    raise ValueError("Integrity cannot change creative content")
                revised.append(ref if projected == artifact.body else self.versions.write(
                    writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL, scope=artifact.scope, body=projected,
                    sources=artifact.source_refs, operation=run_id + ":integrity:" + expected.artifact_ref + ":" + ref.fingerprint))
            proposed = CreativeCheckpoint.model_validate({**cp.model_dump(), "refs": tuple(revised)})
            self.validate_candidate_integrity(proposed, run.scope)
            candidate = ArtifactReference(owner="creative-candidate", artifact_ref="creative-candidate:" + proposed.candidate_fingerprint(), version=1)
            proposed = CreativeCheckpoint.model_validate({**proposed.model_dump(), "candidate_ref": candidate,
                "candidate_version_refs": proposed.refs})
            self.state.ledger.put_index("creative-integrity-reconciliation", run_id,
                {"parent": expected.model_dump(mode="json", by_alias=True),
                 "originalRefs": [r.model_dump(mode="json", by_alias=True) for r in original],
                 "candidate": candidate.model_dump(mode="json", by_alias=True),
                 "revisedRefs": [r.model_dump(mode="json", by_alias=True) for r in proposed.refs]}, scope=run.scope)
            self.state.save(run_id, run.scope, proposed)
            finding = GateFinding.classified(GateCode.ADOPTION_REQUIRED, owner="creative-adoption",
                scope=run.scope, evidence_ref=candidate)
            self.findings.put_decision(self.governor.govern((finding,), scope=run.scope,
                mode=run.mode, package_ref=None), run_id=run_id)
            # Publish references at the SAME user wait, without accepting it.
            refreshed = RuntimeRun.model_validate({**run.model_dump(), "revision": run.revision + 1,
                "last_result": self._success(proposed)})
            return self.runtime.store.save(refreshed, expected_revision=run.revision)

    async def adoption(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        assert self.runtime is not None
        run, cp = self.runtime.store.load(inputs.run_id), self.state.checkpoint(inputs.run_id)
        if run.mode == RunMode.EXPERIMENT:
            return self._success(self._save(inputs, cp))
        if self.state.ledger is None or run.last_result is None or len(run.last_result.artifact_refs) != 1:
            if cp.candidate_ref is None:
                return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
            return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,
                recovery_class=RecoveryClass.USER_DECISION, external_ref=cp.candidate_ref,
                user_decision=UserDecisionRequest(category=DecisionCategory.ADOPTION,
                    question="Adopt the exact reviewed creative candidate for production?"))
        ref = run.last_result.artifact_refs[0]
        try:
            body, scope, _ = self.state.ledger.get_artifact("user-decision", ref)
            record = UserDecisionRecord.model_validate(body)
            if (scope != inputs.scope or record.run_id != inputs.run_id or record.category != DecisionCategory.ADOPTION
                    or not record.accepted or record.source_ref != cp.candidate_ref
                    or cp.candidate_ref is None or cp.candidate_ref.artifact_ref != "creative-candidate:" + cp.candidate_fingerprint()):
                return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
            if any(self.versions.stale(version) for version in cp.refs):
                return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
            self.validate_candidate_integrity(cp, inputs.scope)
            remapped: dict[VersionRef, VersionRef] = {}
            for prior in cp.refs:
                artifact = self.versions.resolve(prior)
                if artifact.kind == Kind.SOURCE or artifact.state == "ADOPTED":
                    remapped[prior] = prior
                    continue
                parents = tuple(remapped.get(parent, parent) for parent in artifact.source_refs)
                production = next((self.versions.resolve(r) for r in self.state.input(inputs.run_id).base_refs
                    if self.versions.resolve(r).kind == artifact.kind and self.versions.resolve(r).scope == artifact.scope and
                    self.versions.resolve(r).state == "ADOPTED"), None)
                head = self.versions.head(production.identity) if production else None
                fixed_production = self.versions.resolve(head) if head else None
                if fixed_production and fixed_production.candidate_origin_ref == prior and fixed_production.source_refs == parents and not self.versions.stale(fixed_production.ref()):
                    remapped[prior] = fixed_production.ref()
                    continue
                remapped[prior] = self.versions.write(writer=artifact.authority, kind=artifact.kind,
                    scope=artifact.scope, body=artifact.body, sources=parents,
                    operation=inputs.operation_id + ":" + prior.fingerprint, adoption_decision=ref, candidate_origin=prior)
        except (KeyError, ValueError, OSError):
            return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
        adopted=tuple(remapped.values())
        if self.native_task_persistence is not None and self.native_task_persistence.enabled:
            await self.native_task_persistence.persist(adopted)
        return self._success(self._save(inputs,cp,refs=adopted,decision_ref=ref))

    async def package(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        cp = self.state.checkpoint(inputs.run_id)
        assert self.runtime is not None
        run = self.runtime.store.load(inputs.run_id)
        if any(self.versions.stale(ref) for ref in cp.refs) or (run.mode == RunMode.PRODUCTION and any(
                self.versions.resolve(ref).kind != Kind.SOURCE and self.versions.resolve(ref).state != "ADOPTED" for ref in cp.refs)):
            return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
        sources = NativeCreativeSources(self.versions, cp.refs)
        assembler = ShotAssembler(sources, ProfessionalDesignResolver(sources))
        assembled = await assembler.assemble(inputs.scope, mode=run.mode,
            policy_ref=ArtifactReference(owner="runtime-policy", artifact_ref=run.policy_id, version=1))
        if assembled.package is None:
            return self._blocked(inputs, GateCode.REQUEST_INPUT_MISSING)
        self.versions.remember_selection(inputs.scope, cp.refs)
        ref = self.packages.put(assembled.package)
        return self._success(self._save(inputs, cp, package_ref=ref))
