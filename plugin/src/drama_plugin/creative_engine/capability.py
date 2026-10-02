"""Domain actions for the one Runtime. Author content is supplied through typed ports."""
from __future__ import annotations

from typing import TYPE_CHECKING

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.authors import CanonAuthor, CreativeDirectionAuthor, ProfessionalAuthor
from drama_plugin.creative_engine.contracts import (
    AUTHORITY, Authority, AuthorRequest, CanonDraft, CreativeCheckpoint, DesignBody, FilmInput,
    Kind, SceneBody, ScriptBody, ShotBody, SourceBody, VersionRef, WorkBody,
)
from drama_plugin.creative_engine.routes import RouteSelector
from drama_plugin.creative_engine.sources import NativeCreativeSources
from drama_plugin.creative_engine.store import CreativeStateStore, CreativeVersionStore
from drama_plugin.governance.contracts import GateCode, GateFinding
from drama_plugin.governance.governor import GateGovernor
from drama_plugin.governance.store import GateFindingStore
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.production.assembler import ShotAssembler
from drama_plugin.production.store import ProductionPackageStore
from drama_plugin.professional_design.resolver import ProfessionalDesignResolver
from drama_plugin.runtime.capabilities import TargetCapability
from drama_plugin.runtime.contracts import (
    ArtifactReference, CapabilityInput, CapabilityResult, DecisionCategory, ResultStatus, RunMode,
)

if TYPE_CHECKING:
    from drama_plugin.runtime.engine import RuntimeEngine

PREFIX = "creative."
KEYS = ("source", "canon", "direction", "professional", "route", "review", "adoption", "package", "prerequisite")


class CreativeEngineCapabilities:
    def __init__(self, versions: CreativeVersionStore, state: CreativeStateStore,
                 packages: ProductionPackageStore, governor: GateGovernor, findings: GateFindingStore,
                 canon: CanonAuthor | None = None, direction: CreativeDirectionAuthor | None = None,
                 professional: ProfessionalDesignResolver | None = None):
        self.versions, self.state, self.packages = versions, state, packages
        self.governor, self.findings = governor, findings
        self.canon_author, self.direction_author, self.professional_author = canon, direction, professional
        self.route_selector = RouteSelector()
        self.runtime: RuntimeEngine | None = None

    def registrations(self) -> dict[str, TargetCapability]:
        methods = (self.source, self.canon, self.direction, self.professional, self.route,
                   self.review, self.adoption, self.package, self.prerequisite)
        return {PREFIX + key + ":v1": TargetCapability(method, replay_safe=True)
                for key, method in zip(KEYS, methods, strict=True)}

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
        return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL,
            external_ref=ArtifactReference(owner="capability-absence", artifact_ref=ref.artifact_ref, version=1))

    def _blocked(self, inputs: CapabilityInput, code: GateCode) -> CapabilityResult:
        assert self.runtime is not None
        finding = GateFinding.classified(code, owner="creative-contract", scope=inputs.scope,
            evidence_ref=self.state.input(inputs.run_id).source_ref.runtime_ref(), required=True)
        decision = self.governor.govern((finding,), scope=inputs.scope,
            mode=self.runtime.store.load(inputs.run_id).mode, package_ref=None)
        self.findings.put_decision(decision, run_id=inputs.run_id)
        return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code=code.value)

    def _request(self, inputs: CapabilityInput, owner: Authority) -> AuthorRequest:
        value = self.state.input(inputs.run_id)
        checkpoint = self.state.checkpoint(inputs.run_id)
        source = self.versions.resolve(value.source_ref)
        if source.scope != inputs.scope or not isinstance(source.body, SourceBody):
            raise ValueError("PACKAGE_SCOPE_MISMATCH")
        versions = [self.versions.resolve(ref) for ref in checkpoint.refs]
        work = next((v.body for v in versions if v.kind == Kind.WORK), None)
        script = next((v.body for v in versions if v.kind == Kind.SCRIPT), None)
        scene = next((v.body for v in versions if v.kind == Kind.SCENE), None)
        shot = next((v.body for v in versions if v.kind == Kind.SHOT), None)
        canon = CanonDraft(work=work, script=script, scene=scene) if isinstance(work, WorkBody) and isinstance(
            script, ScriptBody) and isinstance(scene, SceneBody) else None
        return AuthorRequest(scope=inputs.scope, source=source.body, source_refs=checkpoint.refs,
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
            if source.scope != inputs.scope or source.kind != Kind.SOURCE:
                return self._blocked(inputs, GateCode.PACKAGE_SCOPE_MISMATCH)
            refs = value.base_refs or value.approved_canon_refs
            kinds = {self.versions.resolve(r).kind for r in refs}
            if value.approved_canon_refs and kinds != {Kind.WORK, Kind.SCRIPT, Kind.SCENE}:
                return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
            for ref in refs:
                artifact = self.versions.resolve(ref)
                if artifact.scope != inputs.scope:
                    return self._blocked(inputs, GateCode.PACKAGE_SCOPE_MISMATCH)
                if value.approved_canon_refs and (artifact.state != "ADOPTED" or self.versions.stale(ref)):
                    return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
            selected_refs = {value.source_ref, *refs}
            if any(parent not in selected_refs for ref in refs for parent in self.versions.resolve(ref).source_refs):
                return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
            revision = value.revision
            if revision:
                target = self.versions.resolve(revision.target_ref)
                if target.scope != inputs.scope or revision.target_ref not in refs:
                    return self._blocked(inputs, GateCode.PACKAGE_SCOPE_MISMATCH)
                if AUTHORITY[target.kind] != revision.owner:
                    return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
                signature = sha256_canonical([revision.owner, target.kind, revision.instruction])
                if signature in value.prior_revision_signatures or len(value.prior_revision_signatures) >= 3:
                    return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="REVISION_CYCLE_OR_DEPTH_BOUND")
                self.versions.invalidate(revision.target_ref)
            refs = tuple(r for r in refs if self.versions.resolve(r).kind != Kind.SOURCE)
            return self._success(self._save(inputs, cp, refs=(value.source_ref, *refs)))
        except (ValueError, OSError, KeyError):
            return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)

    async def canon(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        cp, value = self.state.checkpoint(inputs.run_id), self.state.input(inputs.run_id)
        request = self._request(inputs, Authority.CANON)
        needs = request.canon is None or bool(value.revision and value.revision.owner == Authority.CANON)
        if not needs:
            return self._success(self._save(inputs, cp))
        if self.canon_author is None:
            return self._absence(inputs, Authority.CANON.value)
        if not self._round_allowed(inputs):
            return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="AUTHOR_ROUND_BOUND")
        self.state.save(inputs.run_id, inputs.scope, CreativeCheckpoint.model_validate(
            {**cp.model_dump(), "author_rounds": cp.author_rounds + 1}))
        draft = CanonDraft.model_validate((await self.canon_author.author(request)).model_dump())
        refs = [value.source_ref]
        for kind, body in ((Kind.WORK, draft.work), (Kind.SCRIPT, draft.script), (Kind.SCENE, draft.scene)):
            refs.append(self.versions.write(writer=Authority.CANON, kind=kind, scope=inputs.scope,
                body=body, sources=tuple(refs), operation=inputs.operation_id + ":" + kind.value))
        return self._success(self._save(inputs, cp, refs=tuple(refs), author_rounds=cp.author_rounds + 1))

    async def direction(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        cp, value = self.state.checkpoint(inputs.run_id), self.state.input(inputs.run_id)
        request = self._request(inputs, Authority.DIRECTION)
        needs = request.shot is None or bool(value.revision and value.revision.owner in {Authority.CANON, Authority.DIRECTION})
        if not needs:
            return self._success(self._save(inputs, cp))
        if self.direction_author is None:
            return self._absence(inputs, Authority.DIRECTION.value)
        if not self._round_allowed(inputs):
            return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="AUTHOR_ROUND_BOUND")
        self.state.save(inputs.run_id, inputs.scope, CreativeCheckpoint.model_validate(
            {**cp.model_dump(), "author_rounds": cp.author_rounds + 1}))
        shot = ShotBody.model_validate((await self.direction_author.author(request)).model_dump())
        if request.canon is None or not set(shot.spoken_ids) <= {line.id for line in request.canon.scene.dialogue}:
            return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
        refs = tuple(r for r in cp.refs if self.versions.resolve(r).kind not in {Kind.SHOT, Kind.PROFESSIONAL})
        ref = self.versions.write(writer=Authority.DIRECTION, kind=Kind.SHOT, scope=inputs.scope,
            body=shot, sources=refs, operation=inputs.operation_id)
        return self._success(self._save(inputs, cp, refs=(*refs, ref), author_rounds=cp.author_rounds + 1))

    async def professional(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        cp = self.state.checkpoint(inputs.run_id)
        request = self._request(inputs, Authority.PROFESSIONAL)
        assert request.shot is not None
        required = set(request.shot.professional_domains)
        bodies = [self.versions.resolve(r).body for r in cp.refs]
        current = {body.domain for body in bodies if isinstance(body, DesignBody)}
        if required <= current and not (request.revision and request.revision.owner == Authority.PROFESSIONAL):
            return self._success(self._save(inputs, cp))
        if self.professional_author is None or self.professional_author.author is None:
            return self._absence(inputs, Authority.PROFESSIONAL.value)
        if not self._round_allowed(inputs):
            return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="AUTHOR_ROUND_BOUND")
        # Ordinary missing design routes internally, with a two-round bound and exact
        # Shot evidence; the unified professional interface retains all department logic.
        from drama_plugin.creative_engine.contracts import RevisionRequest
        refs = tuple(r for r in cp.refs if self.versions.resolve(r).kind != Kind.PROFESSIONAL)
        selected: dict[object, VersionRef] = {}
        rounds = cp.author_rounds
        for attempt in range(2):
            if rounds >= self.state.input(inputs.run_id).max_author_rounds:
                return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="AUTHOR_ROUND_BOUND")
            rounds += 1
            self.state.save(inputs.run_id, inputs.scope, CreativeCheckpoint.model_validate(
                {**cp.model_dump(), "author_rounds": rounds}))
            designs = tuple(DesignBody.model_validate(d.model_dump()) for d in await (
                self.professional_author.revise(request) if request.revision else self.professional_author.design(request)))
            if len({d.domain for d in designs}) != len(designs) or not {d.domain for d in designs} <= required:
                return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)
            for design in designs:
                selected[design.domain] = self.professional_author.persist(self.versions,
                    AuthorRequest.model_validate({**request.model_dump(), "source_refs": refs}), design,
                    operation=inputs.operation_id + ":" + str(attempt) + ":" + design.domain.value)
            if required <= selected.keys():
                authored = tuple(selected[key] for key in sorted(selected, key=str))
                return self._success(self._save(inputs, cp, refs=(*refs, *authored), author_rounds=rounds))
            shot_ref = next(ref for ref in refs if self.versions.resolve(ref).kind == Kind.SHOT)
            finding = GateFinding.classified(GateCode.PACKAGE_STALE, owner=Authority.PROFESSIONAL.value,
                scope=inputs.scope, evidence_ref=shot_ref.runtime_ref(), required=True)
            finding_ref = self.findings.put_finding(finding)
            repair = RevisionRequest(owner=Authority.PROFESSIONAL, target_ref=next(iter(selected.values())),
                finding_ref=finding_ref, instruction="Resolve the remaining declared professional obligations") if selected else None
            request = AuthorRequest.model_validate({**request.model_dump(), "revision": repair,
                "source_refs": (*refs, *selected.values()), "finding_refs": (finding_ref,)})
        return CapabilityResult(status=ResultStatus.RETRYABLE_FAILURE, code="PROFESSIONAL_OBLIGATION_UNRESOLVED")

    async def route(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        cp = self.state.checkpoint(inputs.run_id)
        try:
            plan = self.route_selector.plan(self.state.input(inputs.run_id).route)
        except ValueError:
            return self._blocked(inputs, GateCode.BUDGET_EXCEEDED)
        assert self.runtime is not None
        children: list[str] = []
        # Only prerequisites become child tasks. This E2 child workflow deliberately
        # reports missing generation capability, without invoking a transport.
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
            await self.runtime.run(child.run_id)
            children.append(identity)
        return self._success(self._save(inputs, cp, route_plan=plan, child_runs=tuple(children)))

    async def prerequisite(self, inputs: CapabilityInput) -> CapabilityResult:
        # No E2 media execution is authorized. E3 supplies a package-derived native
        # reference producer; until then this same Runtime child waits explicitly.
        return self._absence(inputs, "reference-production")

    async def review(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        cp = self.state.checkpoint(inputs.run_id)
        if any(self.versions.stale(ref) for ref in cp.refs):
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

    async def adoption(self, inputs: CapabilityInput) -> CapabilityResult:
        if result := self._replay(inputs):
            return result
        assert self.runtime is not None
        run, cp = self.runtime.store.load(inputs.run_id), self.state.checkpoint(inputs.run_id)
        if run.mode == RunMode.EXPERIMENT:
            return self._success(self._save(inputs, cp))
        if self.state.ledger is None or run.last_result is None or len(run.last_result.artifact_refs) != 1:
            return self._absence(inputs, "adoption-decision")
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
            remapped: dict[VersionRef, VersionRef] = {}
            for prior in cp.refs:
                artifact = self.versions.resolve(prior)
                if artifact.kind == Kind.SOURCE or artifact.state == "ADOPTED":
                    remapped[prior] = prior
                    continue
                parents = tuple(remapped.get(parent, parent) for parent in artifact.source_refs)
                remapped[prior] = self.versions.write(writer=artifact.authority, kind=artifact.kind,
                    scope=inputs.scope, body=artifact.body, sources=parents,
                    operation=inputs.operation_id + ":" + prior.fingerprint, adoption_decision=ref, candidate_origin=prior)
            return self._success(self._save(inputs, cp, refs=tuple(remapped.values()), decision_ref=ref))
        except (KeyError, ValueError, OSError):
            return self._blocked(inputs, GateCode.CANON_AUTHORITY_MISMATCH)

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
