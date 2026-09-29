"""One ASSEMBLER: select owner-authored references, never fill creative meaning."""
from __future__ import annotations

from typing import TYPE_CHECKING

from drama_plugin.production.contracts import (
    AssemblyBoundary, AssemblyIssue, AssemblyIssueCode, AssemblyResult, AssemblyValidation,
    DomainReference, GenerationIntent, PackageContent, PackageScope, ProductionPackage,
    SourceDomain as D, SourceOwner, SourceReference,
)
from drama_plugin.production.sources import AssemblySources, OwnedSource, SourceReadError
from drama_plugin.runtime.contracts import ArtifactReference, RunMode, RuntimeScope

if TYPE_CHECKING:
    from drama_plugin.professional_design.resolver import ProfessionalDesignResolver


class ShotAssembler:
    role = "ASSEMBLER"

    def __init__(self, sources: AssemblySources, professional_design: ProfessionalDesignResolver) -> None:
        self.sources = sources
        self.professional_design = professional_design

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
        from drama_plugin.professional_design.contracts import ProfessionalDesignRequest
        package_scope = PackageScope(work=work.reference(), scene=scene.reference(), shot=shot.reference())
        professional = await self.professional_design.resolve(ProfessionalDesignRequest(scope=package_scope))
        selected.extend(professional.sources)
        issues.extend(item for item in professional.issues if item not in issues)
        spoken = {binding.get("spokenContentId") for binding in content.get("spokenContentBindings", ())}
        requirements = set(content.get("referenceRequirements", ()))
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
            scope=package_scope,
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
        professional_refs = tuple(s for s in package.sources if s.reference.owner in {
            SourceOwner.DIRECTION, SourceOwner.PROFESSIONAL,
        })
        if professional_refs:
            from drama_plugin.professional_design.contracts import ProfessionalReferenceCheck
            checked = await self.professional_design.validate(ProfessionalReferenceCheck(
                scope=package.scope, sources=professional_refs))
            issues.extend(checked.issues)
        for ref in refs:
            if ref.owner in {SourceOwner.DIRECTION, SourceOwner.PROFESSIONAL}:
                continue
            try:
                await self.sources.resolve(ref)
            except SourceReadError as error:
                item = AssemblyIssue(code=error.code,
                                     domain=domains.get((ref.owner, ref.artifact_ref, ref.path), D.CANON), owner=ref.owner,
                                     artifact_ref=ref.artifact_ref)
                if item not in issues:
                    issues.append(item)
        return AssemblyValidation(status="UNRESOLVED" if issues else "READY", issues=tuple(issues))
