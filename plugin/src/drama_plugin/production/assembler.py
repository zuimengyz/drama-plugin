"""One ASSEMBLER: select owner-authored references, never fill creative meaning."""
from __future__ import annotations

from typing import Any

from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.production.contracts import (
    AssemblyBoundary, AssemblyIssue, AssemblyIssueCode, AssemblyResult, AssemblyValidation,
    DomainReference, GenerationIntent, PackageContent, PackageScope, ProductionPackage,
    SourceDomain as D, SourceOwner, SourceReference,
)
from drama_plugin.production.sources import AssemblySources, OwnedSource, SourceReadError
from drama_plugin.runtime.contracts import ArtifactReference, RunMode, RuntimeScope

# Migration read selection, not the Professional registry/DAG or a list of mandatory departments.
DEPARTMENT_DOMAINS = {
    "director": D.DIRECTION, "shot-design": D.DIRECTION, "editorial-design": D.EDITORIAL,
    "cinematography": D.CAMERA, "lighting-design": D.LIGHTING, "color-design": D.COLOR,
    "color-grading": D.COLOR, "dramatic-performance-direction": D.PERFORMANCE,
    "blocking": D.PERFORMANCE, "action-choreography": D.ACTION,
    "character-art": D.SUBJECTS, "costume-design": D.SUBJECTS, "look-continuity": D.SUBJECTS,
    "environment-design": D.WORLD, "environment-art": D.WORLD, "scene-layout": D.WORLD,
    "set-decoration": D.WORLD, "prop-design": D.WORLD, "animal-design": D.SUBJECTS,
    "battle-crowd-choreography": D.ACTION, "vfx-planning": D.WORLD,
    "sound-design": D.SOUND, "music-direction": D.SOUND, "dialogue-design": D.SOUND,
    "voice-direction": D.SOUND, "reference-strategy": D.REFERENCE, "clip-decomposition": D.EDITORIAL,
}


def _owner(domain: D) -> SourceOwner:
    return SourceOwner.DIRECTION if domain in {D.DIRECTION, D.EDITORIAL} else SourceOwner.PROFESSIONAL


class ShotAssembler:
    role = "ASSEMBLER"

    def __init__(self, sources: AssemblySources) -> None:
        self.sources = sources

    async def assemble(self, scope: RuntimeScope, *, mode: RunMode,
                       policy_ref: ArtifactReference) -> AssemblyResult:
        issues: list[AssemblyIssue] = []
        selected: list[DomainReference] = []

        def issue(code: AssemblyIssueCode, domain: D, owner: SourceOwner, ref: str) -> None:
            item = AssemblyIssue(code=code, domain=domain, owner=owner, artifact_ref=ref)
            if item not in issues:
                issues.append(item)

        def add(domain: D, source: OwnedSource, *path: str, shared: bool = False) -> None:
            selected.append(DomainReference(domain=domain, reference=source.reference(*path),
                use="SCENE_CONSTRAINT" if shared else "SHOT_FACT"))

        try:
            work, scene, shot = await self.sources.scope_sources(scope)
        except SourceReadError as error:
            return AssemblyResult(validation=AssemblyValidation(status="UNRESOLVED", issues=(
                AssemblyIssue(code=error.code, domain=D.CANON, owner=error.owner,
                              artifact_ref=error.artifact_ref),)))
        wc, sc, content = work.body["content"], scene.body["content"], shot.body["content"]
        for source in (work, scene):
            if source.body["content"].get("approval", {}).get("status") != "APPROVED":
                issue(AssemblyIssueCode.AUTHORITY_MISMATCH, D.CANON, source.owner, source.artifact_ref)
        obligations: list[SourceReference] = []
        for field in ("purpose", "requiredTransition"):
            if not content.get(field):
                issue(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, D.DIRECTION, SourceOwner.SHOT, shot.artifact_ref)
            else:
                obligations.append(shot.reference("content", field))
        duration = content.get("plannedDurationMs")
        if type(duration) is not int or not 0 < duration <= 3_600_000:
            issue(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, D.DIRECTION, SourceOwner.SHOT, shot.artifact_ref)
        pins = content.get("departmentRefs", {})
        if not isinstance(pins, dict):
            pins = {}
        for required in ("director", "shot-design", "cinematography"):
            if required not in pins:
                domain = DEPARTMENT_DOMAINS[required]
                issue(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, domain, _owner(domain), required)
        bodies: dict[str, OwnedSource] = {}
        for department in sorted(set(pins) & DEPARTMENT_DOMAINS.keys()):
            domain = DEPARTMENT_DOMAINS[department]
            try:
                source = await self.sources.professional(department, SourcePin.model_validate(pins[department]))
            except SourceReadError as error:
                issue(error.code, domain, _owner(domain), error.artifact_ref)
                continue
            except ValueError:
                issue(AssemblyIssueCode.AUTHORITY_MISMATCH, domain, _owner(domain), department)
                continue
            bible = source.body
            if bible["workRef"] != scope.work_id or (
                bible.get("sceneRefs") and scope.scene_id not in bible["sceneRefs"]
            ) or (bible.get("shotRefs") and scope.shot_id not in bible["shotRefs"]):
                issue(AssemblyIssueCode.SCOPE_MISMATCH, domain, _owner(domain), source.artifact_ref)
                continue
            if bible["status"] == "NOT_REQUIRED":
                if department in {"director", "shot-design", "cinematography"}:
                    issue(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, domain, _owner(domain), source.artifact_ref)
                continue
            bodies[department] = source
        shot_record: dict[str, Any] | None = None
        design = bodies.get("shot-design")
        if design:
            matches = [r for r in design.body["content"] if r["id"] in {
                scope.shot_id, content.get("coverageCandidateId")
            } or r["values"].get("shot_ref") == scope.shot_id]
            if len(matches) == 1:
                shot_record = matches[0]
            else:
                issue(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, D.DIRECTION, SourceOwner.DIRECTION, design.artifact_ref)
        subjects = set(shot_record["values"].get("subjects", ())) if shot_record else set()
        spoken = {binding.get("spokenContentId") for binding in content.get("spokenContentBindings", ())}
        requirements = set(content.get("referenceRequirements", ()))
        for department, source in bodies.items():
            domain = DEPARTMENT_DOMAINS[department]
            count = 0
            for index, record in enumerate(source.body["content"]):
                values = record["values"]
                scopes = record["scopeRefs"]
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
                # No action-to-beat relation exists in this legacy Bible. Preserve its explicitly
                # referenced scene constraints, never pretend all its actions execute in this Shot.
                if department == "action-choreography" and not values.get("beat_ref") and not values.get("shot_ref"):
                    continue
                add(domain, source, "content", str(index), "values",
                    shared=scope.shot_id not in scopes and not values.get("beat_ref")
                           and not values.get("shot_ref") and department != "cinematography")
                count += 1
            if department == "action-choreography" and source.body["content"]:
                add(domain, source, "content", shared=True)
                count += 1
            if department in {"director", "shot-design", "cinematography", "dramatic-performance-direction", "blocking"} and not count:
                issue(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, domain, _owner(domain), source.artifact_ref)
        for index, line in enumerate(sc.get("spokenContent", ())):
            if line.get("id") in spoken:
                add(D.SOUND, scene, "content", "spokenContent", str(index))
                spoken.remove(line["id"])
        if spoken:
            issue(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, D.SOUND, SourceOwner.SCENE, scene.artifact_ref)
        add(D.CANON, scene, "content", "approvedSceneText", shared=True)
        if not sc.get("approvedSceneText"):
            issue(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, D.CANON, SourceOwner.SCENE, scene.artifact_ref)
        for field, domain in (("subjectAction", D.ACTION), ("visualEntryState", D.PERFORMANCE),
                              ("visualExitState", D.PERFORMANCE), ("spokenContentBindings", D.SOUND),
                              ("referenceRequirements", D.REFERENCE)):
            if content.get(field):
                add(domain, shot, "content", field)
        for index, ref in enumerate(wc.get("specializedAssetCompilationRefs", ())):
            if isinstance(ref, dict) and ref.get("key", "").split(":")[-1] in requirements:
                add(D.REFERENCE, work, "content", "specializedAssetCompilationRefs", str(index))
        if issues:
            return AssemblyResult(validation=AssemblyValidation(status="UNRESOLVED", issues=tuple(issues)))
        # Duplicate selections are collapsed; conflicting owner revisions remain contract errors.
        unique = {tuple((s.domain, s.reference.owner, s.reference.artifact_ref, s.reference.path, s.use)): s
                  for s in selected}
        package = ProductionPackage.freeze(PackageContent(
            scope=PackageScope(work=work.reference(), scene=scene.reference(), shot=shot.reference()),
            sources=tuple(unique[key] for key in sorted(unique)), obligations=tuple(obligations),
            generation_intent=GenerationIntent(duration_ms=duration,
                duration_ref=shot.reference("content", "plannedDurationMs")),
            boundary=AssemblyBoundary(mode=mode, policy_ref=policy_ref)))
        return AssemblyResult(validation=AssemblyValidation(status="READY"), package=package)

    async def validate_sources(self, package: ProductionPackage) -> AssemblyValidation:
        """Internal read comparison, not a freshness Gate or a production authorization."""
        refs = [package.scope.work, package.scope.scene, package.scope.shot, *package.obligations,
                package.generation_intent.duration_ref, *(s.reference for s in package.sources)]
        domains = {(s.reference.owner, s.reference.artifact_ref, s.reference.path): s.domain
                   for s in package.sources}
        issues: list[AssemblyIssue] = []
        for ref in refs:
            try:
                await self.sources.resolve(ref)
            except SourceReadError as error:
                item = AssemblyIssue(code=error.code,
                                     domain=domains.get((ref.owner, ref.artifact_ref, ref.path), D.CANON), owner=ref.owner,
                                     artifact_ref=ref.artifact_ref)
                if item not in issues:
                    issues.append(item)
        return AssemblyValidation(status="UNRESOLVED" if issues else "READY", issues=tuple(issues))
