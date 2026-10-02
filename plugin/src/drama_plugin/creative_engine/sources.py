"""Exact-version projection into existing Assembler/Professional/Compiler interfaces."""
from __future__ import annotations

from typing import cast
from pydantic import JsonValue, TypeAdapter

from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.production.contracts import (
    AssemblyIssue, AssemblyIssueCode as I, AssemblyValidation, DomainReference, SourceDomain as D,
    SourceOwner, SourceReference,
)
from drama_plugin.production.sources import AssemblySources, OwnedSource, SourceReadError
from drama_plugin.professional_design.contracts import (
    ProfessionalDesignRequest, ProfessionalDesignSelection, ProfessionalReferenceCheck,
)
from drama_plugin.professional_design.resolver import ProfessionalDesignBackend
from drama_plugin.runtime.contracts import RuntimeScope
from drama_plugin.creative_engine.contracts import (
    CreativeVersion, DesignBody, Kind, SceneBody, ShotBody, SourceBody, VersionRef, WorkBody,
)
from drama_plugin.creative_engine.store import CreativeVersionStore


def json_object(value: object) -> dict[str, JsonValue]:
    checked: JsonValue = TypeAdapter(JsonValue).validate_python(value)
    if not isinstance(checked, dict):
        raise ValueError("Object required")
    return checked


class NativeCreativeSources:
    def __init__(self, store: CreativeVersionStore, refs: tuple[VersionRef, ...]):
        self.store = store
        self.refs = refs

    def version(self, kind: Kind) -> CreativeVersion:
        found = [self.store.resolve(r) for r in self.refs if self.store.resolve(r).kind == kind]
        if len(found) != 1:
            raise ValueError("Exact unique creative version required")
        return found[0]

    def project(self, artifact: CreativeVersion) -> OwnedSource:
        body, scope = artifact.body, artifact.scope
        content: dict[str, JsonValue]
        identity: str | None
        if isinstance(body, WorkBody):
            owner, identity = SourceOwner.WORK, scope.work_id
            content = json_object(body.model_dump(mode="json", by_alias=True))
        elif isinstance(body, SceneBody):
            owner, identity = SourceOwner.SCENE, scope.scene_id
            source = self.version(Kind.SOURCE).body
            assert isinstance(source, SourceBody)
            content = {"approvedSceneText": body.scene_text,
                "spokenContent": [{"id": line.id, "speakerKey": line.speaker, "kind": "DIALOGUE", "mustKeep": line.must_keep, "text": line.text,
                    "language": source.spoken_language, "spokenLanguage": source.spoken_language,
                    "deliveryMode": "speech"} for line in body.dialogue],
                "spokenLanguagePolicy": source.spoken_language_policy,
                "subtitleLanguages": list(source.subtitle_languages)}
        elif isinstance(body, ShotBody):
            owner, identity = SourceOwner.SHOT, scope.shot_id
            content = {"purpose": body.purpose, "requiredTransition": body.required_transition,
                "plannedDurationMs": body.duration_ms, "subjectAction": body.subject_action,
                "visualEntryState": body.entry_state, "visualExitState": body.exit_state,
                "spokenContentBindings": [{"spokenContentId": line} for line in body.spoken_ids],
                "referenceRequirements": [], "coverage": body.coverage,
                "blockingIntent": body.blocking_intent, "cameraIntent": body.camera_intent,
                "editingRelation": body.editing_relation, "performanceDirection": body.performance_direction}
        elif isinstance(body, DesignBody):
            owner, identity = SourceOwner.PROFESSIONAL, artifact.identity
            content = body.facts
        else:
            raise ValueError("Only production fact owners are projected")
        if identity is None:
            raise ValueError("PACKAGE_SCOPE_MISMATCH")
        content = {**content, "approval": {"status": "APPROVED"},
                   "creativeVersionRef": json_object(artifact.ref().model_dump(mode="json", by_alias=True))}
        projected = {"id": identity, "version": artifact.version, "content": content,
            "sourceRefs": [json_object(r.model_dump(mode="json", by_alias=True)) for r in artifact.source_refs]}
        result = OwnedSource(owner, identity, artifact.version, projected)
        self.store.remember_projection(result.reference().fingerprint, artifact.ref())
        return result

    async def scope_sources(self, scope: RuntimeScope) -> tuple[OwnedSource, OwnedSource, OwnedSource]:
        artifacts = tuple(self.version(kind) for kind in (Kind.WORK, Kind.SCENE, Kind.SHOT))
        if any(a.scope != scope for a in artifacts):
            raise SourceReadError(I.SCOPE_MISMATCH, SourceOwner.SHOT, scope.shot_id or scope.work_id)
        return self.project(artifacts[0]), self.project(artifacts[1]), self.project(artifacts[2])

    async def professional(self, department: str, pin: SourcePin) -> OwnedSource:
        raise SourceReadError(I.AUTHORITY_MISMATCH, SourceOwner.PROFESSIONAL, pin.key)

    async def resolve(self, reference: SourceReference) -> JsonValue:
        try:
            artifact = self.store.projection(reference.fingerprint)
            projected = self.direction(artifact) if reference.owner == SourceOwner.DIRECTION else self.project(artifact)
        except (KeyError, OSError, ValueError) as error:
            raise SourceReadError(I.VERSION_MISMATCH, reference.owner, reference.artifact_ref) from error
        actual = projected.reference(*reference.path)
        if actual != reference:
            raise SourceReadError(I.VERSION_MISMATCH, reference.owner, reference.artifact_ref)
        value: JsonValue = json_object(projected.body)
        try:
            for segment in reference.path:
                if isinstance(value, list):
                    value = value[int(segment)]
                elif isinstance(value, dict):
                    value = value[segment]
                else:
                    raise ValueError("Invalid source path")
        except (IndexError, KeyError, ValueError) as error:
            raise SourceReadError(I.MISSING_REQUIRED_SOURCE, reference.owner, reference.artifact_ref) from error
        return value

    async def select(self, request: ProfessionalDesignRequest) -> ProfessionalDesignSelection:
        scope = RuntimeScope(work_id=request.scope.work.artifact_ref,
            scene_id=request.scope.scene.artifact_ref, shot_id=request.scope.shot.artifact_ref)
        owned = await self.scope_sources(scope)
        issues: list[AssemblyIssue] = []
        for source, expected in zip(owned, (request.scope.work, request.scope.scene, request.scope.shot), strict=True):
            if source.reference() != expected:
                issues.append(AssemblyIssue(code=I.VERSION_MISMATCH, domain=D.DIRECTION,
                    owner=source.owner, artifact_ref=expected.artifact_ref))
        shot = self.version(Kind.SHOT)
        assert isinstance(shot.body, ShotBody)
        domains = tuple(sorted({D.DIRECTION, *(request.domains or shot.body.professional_domains)}))
        selected = [DomainReference(domain=D.DIRECTION, reference=self.direction(shot).reference("content"))]
        for domain in domains:
            if domain == D.DIRECTION:
                continue
            matches = [self.store.resolve(ref) for ref in self.refs if self.store.resolve(ref).kind == Kind.PROFESSIONAL
                       and cast(DesignBody, self.store.resolve(ref).body).domain == domain]
            if len(matches) != 1:
                issues.append(AssemblyIssue(code=I.MISSING_REQUIRED_SOURCE, domain=domain,
                    owner=SourceOwner.PROFESSIONAL, artifact_ref="professional:" + domain.value))
                continue
            design = matches[0]
            if design.scope != scope or shot.ref() not in design.source_refs:
                issues.append(AssemblyIssue(code=I.SCOPE_MISMATCH, domain=domain,
                    owner=SourceOwner.PROFESSIONAL, artifact_ref=design.identity))
                continue
            selected.append(DomainReference(domain=domain, reference=self.project(design).reference("content")))
        return ProfessionalDesignSelection(domains=domains, sources=tuple(sorted(selected,
            key=lambda s: (s.domain, s.reference.owner, s.reference.artifact_ref, s.reference.path, s.use))), issues=tuple(issues))

    async def validate(self, request: ProfessionalReferenceCheck) -> AssemblyValidation:
        issues: list[AssemblyIssue] = []
        for source in (*request.sources,):
            try:
                version = self.store.projection(source.reference.fingerprint)
                if version.scope != RuntimeScope(work_id=request.scope.work.artifact_ref,
                        scene_id=request.scope.scene.artifact_ref, shot_id=request.scope.shot.artifact_ref):
                    raise SourceReadError(I.SCOPE_MISMATCH, source.reference.owner, source.reference.artifact_ref)
                await self.resolve(source.reference)
                if self.store.stale(version.ref()):
                    raise SourceReadError(I.VERSION_MISMATCH, source.reference.owner, source.reference.artifact_ref)
            except SourceReadError as error:
                issues.append(AssemblyIssue(code=error.code, domain=source.domain,
                    owner=error.owner, artifact_ref=error.artifact_ref))
        return AssemblyValidation(status="UNRESOLVED" if issues else "READY", issues=tuple(issues))

    def direction(self, artifact: CreativeVersion) -> OwnedSource:
        assert isinstance(artifact.body, ShotBody)
        result = OwnedSource(SourceOwner.DIRECTION, artifact.identity, artifact.version,
            {"content": {"camera_intent": artifact.body.camera_intent, "coverage": artifact.body.coverage,
                         "editing_relation": artifact.body.editing_relation,
                         "restraint_principles": artifact.body.performance_direction},
             "creativeVersionRef": artifact.ref().model_dump(mode="json", by_alias=True)})
        self.store.remember_projection(result.reference().fingerprint, artifact.ref())
        return result


class CreativeAwareSources:
    lifecycle = "TARGET_VERSION_RESOLVER_WITH_MIGRATION_ONLY_READ_BACKEND"
    """Existing consumers can resolve E2 snapshots without altering legacy fingerprints."""
    def __init__(self, legacy: AssemblySources, store: CreativeVersionStore):
        self.legacy, self.store = legacy, store

    def snapshot(self, ref: SourceReference) -> NativeCreativeSources | None:
        try:
            artifact = self.store.projection(ref.fingerprint)
        except (OSError, KeyError):
            return None
        refs: dict[str, VersionRef] = {}
        def collect(value: CreativeVersion) -> None:
            refs[value.identity] = value.ref()
            for parent in value.source_refs:
                if parent.identity not in refs:
                    collect(self.store.resolve(parent))
        collect(artifact)
        return NativeCreativeSources(self.store, tuple(refs.values()))

    async def scope_sources(self, scope: RuntimeScope) -> tuple[OwnedSource, OwnedSource, OwnedSource]:
        approved = self.store.approved_selection(scope)
        if approved is not None:
            return await NativeCreativeSources(self.store, approved).scope_sources(scope)
        return await self.legacy.scope_sources(scope)

    async def professional(self, department: str, pin: SourcePin) -> OwnedSource:
        return await self.legacy.professional(department, pin)

    async def resolve(self, reference: SourceReference) -> object:
        snapshot = self.snapshot(reference)
        if snapshot is None:
            return await self.legacy.resolve(reference)
        artifact = self.store.projection(reference.fingerprint)
        if reference.owner == SourceOwner.DIRECTION:
            projected = snapshot.direction(artifact)
            if projected.reference(*reference.path) != reference:
                raise SourceReadError(I.VERSION_MISMATCH, reference.owner, reference.artifact_ref)
            value: JsonValue = json_object(projected.body)
            for segment in reference.path:
                if not isinstance(value, dict):
                    raise SourceReadError(I.MISSING_REQUIRED_SOURCE, reference.owner, reference.artifact_ref)
                value = value[segment]
            return value
        return await snapshot.resolve(reference)


class CreativeAwareProfessional:
    lifecycle = "TARGET_VERSION_RESOLVER_WITH_MIGRATION_ONLY_READ_BACKEND"
    def __init__(self, legacy: ProfessionalDesignBackend, sources: CreativeAwareSources):
        self.legacy, self.sources = legacy, sources

    async def select(self, request: ProfessionalDesignRequest) -> ProfessionalDesignSelection:
        snapshot = self.sources.snapshot(request.scope.shot)
        if snapshot is not None:
            shot = self.sources.store.projection(request.scope.shot.fingerprint)
            selected = self.sources.store.selected_refs(shot.ref())
            return await NativeCreativeSources(self.sources.store, selected).select(request)
        return await self.legacy.select(request)

    async def validate(self, request: ProfessionalReferenceCheck) -> AssemblyValidation:
        snapshot = self.sources.snapshot(request.scope.shot)
        if snapshot is None:
            return await self.legacy.validate(request)
        issues: list[AssemblyIssue] = []
        for selection in request.sources:
            ref = selection.reference
            try:
                artifact = self.sources.store.projection(ref.fingerprint)
                if artifact.scope != RuntimeScope(work_id=request.scope.work.artifact_ref,
                        scene_id=request.scope.scene.artifact_ref, shot_id=request.scope.shot.artifact_ref):
                    raise SourceReadError(I.SCOPE_MISMATCH, ref.owner, ref.artifact_ref)
                await self.sources.resolve(ref)
                if self.sources.store.stale(artifact.ref()):
                    raise SourceReadError(I.VERSION_MISMATCH, ref.owner, ref.artifact_ref)
            except SourceReadError as error:
                issues.append(AssemblyIssue(code=error.code, domain=selection.domain, owner=error.owner,
                    artifact_ref=error.artifact_ref))
        return AssemblyValidation(status="UNRESOLVED" if issues else "READY", issues=tuple(issues))
