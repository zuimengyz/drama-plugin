"""MIGRATION_ONLY read selection from existing approved owners; no DAG execution."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.production.contracts import (
    AssemblyIssue, AssemblyIssueCode as I, AssemblyValidation, DomainReference, PackageScope,
    SourceDomain as D, SourceOwner,
)
from drama_plugin.production.sources import AssemblySources, OwnedSource, SourceReadError
from drama_plugin.professional_design.catalog import CORE_SOURCES, DEPARTMENT_DOMAINS, RECORD_REQUIRED
from drama_plugin.professional_design.contracts import ProfessionalDesignRequest, ProfessionalDesignSelection, ProfessionalReferenceCheck
from drama_plugin.runtime.contracts import RuntimeScope


def _owner(domain: D) -> SourceOwner:
    return SourceOwner.DIRECTION if domain in {D.DIRECTION, D.EDITORIAL} else SourceOwner.PROFESSIONAL


def _scope_matches(body: dict[str, Any], scope: PackageScope) -> bool:
    return body["workRef"] == scope.work.artifact_ref and (
        not body.get("sceneRefs") or scope.scene.artifact_ref in body["sceneRefs"]
    ) and (not body.get("shotRefs") or scope.shot.artifact_ref in body["shotRefs"])


class LegacyProfessionalDesignSources:
    lifecycle = "MIGRATION_ONLY"

    def __init__(self, sources: AssemblySources, *, catalog: Mapping[str, D] = DEPARTMENT_DOMAINS) -> None:
        self.sources = sources
        self.catalog = catalog

    async def select(self, request: ProfessionalDesignRequest) -> ProfessionalDesignSelection:
        issues: list[AssemblyIssue] = []
        selected: list[DomainReference] = []

        def issue(code: I, domain: D, owner: SourceOwner, ref: str) -> None:
            item = AssemblyIssue(code=code, domain=domain, owner=owner, artifact_ref=ref)
            if item not in issues:
                issues.append(item)

        scope = RuntimeScope(work_id=request.scope.work.artifact_ref,
            scene_id=request.scope.scene.artifact_ref, shot_id=request.scope.shot.artifact_ref)
        try:
            work, scene, shot = await self.sources.scope_sources(scope)
            for source, expected in zip((work, scene, shot),
                    (request.scope.work, request.scope.scene, request.scope.shot), strict=True):
                if source.reference() != expected:
                    raise SourceReadError(I.VERSION_MISMATCH, source.owner, source.artifact_ref)
        except SourceReadError as error:
            return ProfessionalDesignSelection(domains=request.domains, issues=(AssemblyIssue(
                code=error.code, domain=D.DIRECTION, owner=error.owner, artifact_ref=error.artifact_ref),))
        content = shot.body["content"]
        pins = content.get("departmentRefs", {})
        if not isinstance(pins, dict):
            pins = {}
        wanted = set(request.domains) if request.domains else {
            D.DIRECTION, D.CAMERA, *(self.catalog[d] for d in pins if d in self.catalog),
        }
        departments = {d for d in pins if d in self.catalog and self.catalog[d] in wanted}
        # Shot Design holds the already-authored subject/coverage relations. This read is
        # context for selection, not traversal or execution of its authoring dependencies.
        reads = departments | ({"shot-design"} if "shot-design" in pins and wanted & {
            D.SUBJECTS, D.WORLD, D.PERFORMANCE, D.ACTION, D.SOUND,
        } else set())
        for required in CORE_SOURCES:
            if self.catalog[required] in wanted and required not in pins:
                domain = self.catalog[required]
                issue(I.MISSING_REQUIRED_SOURCE, domain, _owner(domain), required)
        bodies: dict[str, OwnedSource] = {}
        for department in sorted(reads):
            domain = self.catalog[department]
            try:
                source = await self.sources.professional(department, SourcePin.model_validate(pins[department]))
            except SourceReadError as error:
                issue(error.code, domain, _owner(domain), error.artifact_ref)
                continue
            except ValueError:
                issue(I.AUTHORITY_MISMATCH, domain, _owner(domain), department)
                continue
            if not _scope_matches(source.body, request.scope):
                issue(I.SCOPE_MISMATCH, domain, _owner(domain), source.artifact_ref)
                continue
            if source.body["status"] == "NOT_REQUIRED":
                if department in CORE_SOURCES:
                    issue(I.MISSING_REQUIRED_SOURCE, domain, _owner(domain), source.artifact_ref)
                continue
            bodies[department] = source
        shot_record: dict[str, Any] | None = None
        design = bodies.get("shot-design")
        if design:
            matches = [r for r in design.body["content"] if r["id"] in {
                scope.shot_id, content.get("coverageCandidateId"),
            } or r["values"].get("shot_ref") == scope.shot_id]
            if len(matches) == 1:
                shot_record = matches[0]
            else:
                issue(I.MISSING_REQUIRED_SOURCE, D.DIRECTION, SourceOwner.DIRECTION, design.artifact_ref)
        subjects = set(shot_record["values"].get("subjects", ())) if shot_record else set()
        spoken = {binding.get("spokenContentId") for binding in content.get("spokenContentBindings", ())}
        requirements = set(content.get("referenceRequirements", ()))
        for department, source in bodies.items():
            if department not in departments:
                continue
            domain = self.catalog[department]
            count = 0
            for index, record in enumerate(source.body["content"]):
                values, scopes = record["values"], record["scopeRefs"]
                if not {scope.work_id, scope.scene_id, scope.shot_id} & set(scopes):
                    continue
                if values.get("shot_ref") and values["shot_ref"] not in {scope.shot_id, content.get("coverageCandidateId")}:
                    continue
                if values.get("beat_ref") and values["beat_ref"] != content.get("beatRef"):
                    continue
                if department == "cinematography" and record["id"] != content.get("cameraRecord"):
                    continue
                if department == "shot-design" and record is not shot_record:
                    continue
                if values.get("character_ref") and values["character_ref"] not in subjects:
                    continue
                if department == "dialogue-design" and record["id"] not in spoken:
                    continue
                if department in {"prop-design", "animal-design"} and not (
                    {record["id"], values.get("prop_id"), values.get("animal_id")} & requirements
                ):
                    continue
                if department == "action-choreography" and not values.get("beat_ref") and not values.get("shot_ref"):
                    continue
                shared = scope.shot_id not in scopes and not values.get("beat_ref") and not values.get("shot_ref") and department != "cinematography"
                selected.append(DomainReference(domain=domain, reference=source.reference("content", str(index), "values"),
                    use="SCENE_CONSTRAINT" if shared else "SHOT_FACT"))
                count += 1
            if department == "action-choreography" and source.body["content"]:
                selected.append(DomainReference(domain=domain, reference=source.reference("content"), use="SCENE_CONSTRAINT"))
                count += 1
            if department in RECORD_REQUIRED and not count:
                issue(I.MISSING_REQUIRED_SOURCE, domain, _owner(domain), source.artifact_ref)
        unique = {(s.domain, s.reference.owner, s.reference.artifact_ref, s.reference.path, s.use): s for s in selected}
        return ProfessionalDesignSelection(domains=tuple(sorted(wanted)),
            sources=tuple(unique[k] for k in sorted(unique)), issues=tuple(issues))

    async def validate(self, request: ProfessionalReferenceCheck) -> AssemblyValidation:
        scope = request.scope
        issues: list[AssemblyIssue] = []
        try:
            _, _, shot = await self.sources.scope_sources(RuntimeScope(work_id=scope.work.artifact_ref,
                scene_id=scope.scene.artifact_ref, shot_id=scope.shot.artifact_ref))
            pins = shot.body["content"].get("departmentRefs", {})
            if not isinstance(pins, dict):
                raise SourceReadError(I.AUTHORITY_MISMATCH, SourceOwner.SHOT, scope.shot.artifact_ref)
        except SourceReadError as error:
            return AssemblyValidation(status="UNRESOLVED", issues=(AssemblyIssue(code=error.code,
                domain=D.DIRECTION, owner=error.owner, artifact_ref=error.artifact_ref),))
        # Cache only within this invocation. Future calls must re-read current owners.
        bodies: dict[tuple[SourceOwner, str, int | None, str], OwnedSource] = {}
        for selection in request.sources:
            reference = selection.reference
            try:
                if reference.owner not in {SourceOwner.DIRECTION, SourceOwner.PROFESSIONAL}:
                    raise SourceReadError(I.AUTHORITY_MISMATCH, reference.owner, reference.artifact_ref)
                # Existing Shot bindings supply the address after restore; no library scan.
                bindings = [department for department, pin in pins.items() if isinstance(pin, dict)
                    and pin.get("key") == reference.artifact_ref and department in self.catalog
                    and self.catalog[department] == selection.domain]
                if not bindings:
                    raise SourceReadError(I.VERSION_MISMATCH, reference.owner, reference.artifact_ref)
                if len(bindings) != 1:
                    raise SourceReadError(I.AUTHORITY_MISMATCH, reference.owner, reference.artifact_ref)
                key = (reference.owner, reference.artifact_ref, reference.version, reference.fingerprint)
                source = bodies.get(key)
                if source is None:
                    source = await self.sources.professional(bindings[0], SourcePin(key=reference.artifact_ref,
                        kind="DESIGN", fingerprint=reference.fingerprint))
                    bodies[key] = source
                if source.owner != reference.owner:
                    raise SourceReadError(I.AUTHORITY_MISMATCH, reference.owner, reference.artifact_ref)
                if source.version != reference.version:
                    raise SourceReadError(I.VERSION_MISMATCH, reference.owner, reference.artifact_ref)
                if not _scope_matches(source.body, scope):
                    raise SourceReadError(I.SCOPE_MISMATCH, reference.owner, reference.artifact_ref)
                selected: Any = source.body
                try:
                    for segment in reference.path:
                        selected = selected[int(segment)] if isinstance(selected, list) else selected[segment]
                except (KeyError, IndexError, ValueError, TypeError) as error:
                    raise SourceReadError(I.MISSING_REQUIRED_SOURCE, reference.owner, reference.artifact_ref) from error
            except SourceReadError as error:
                item = AssemblyIssue(code=error.code, domain=selection.domain, owner=error.owner, artifact_ref=error.artifact_ref)
                if item not in issues:
                    issues.append(item)
        return AssemblyValidation(status="UNRESOLVED" if issues else "READY", issues=tuple(issues))
