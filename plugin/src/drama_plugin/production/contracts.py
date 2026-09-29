"""Small immutable Shot inputs: references and execution facts, never Creative Canon."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Self

from pydantic import Field, StrictInt, StringConstraints, model_validator

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.creative_asset import Hash
from drama_plugin.runtime.contracts import ArtifactReference, Identifier, RunMode, RuntimeContract

PathSegment = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]+$", max_length=100)]


class SourceOwner(str, Enum):
    WORK = "work"
    SCENE = "scene"
    SHOT = "shot"
    DIRECTION = "direction"
    PROFESSIONAL = "professional"


class SourceReference(ArtifactReference):
    owner: SourceOwner
    version: Annotated[StrictInt, Field(gt=0)] | None = None
    fingerprint: Hash
    path: tuple[PathSegment, ...] = Field(default=(), max_length=8)


class PackageScope(RuntimeContract):
    work: SourceReference
    scene: SourceReference
    shot: SourceReference

    @model_validator(mode="after")
    def identity_owners(self) -> Self:
        for ref, owner in ((self.work, SourceOwner.WORK), (self.scene, SourceOwner.SCENE),
                           (self.shot, SourceOwner.SHOT)):
            if ref.owner != owner or ref.path:
                raise ValueError("Scope requires whole identity references from the correct owners")
        return self


class SourceDomain(str, Enum):
    CANON = "CANON"
    DIRECTION = "DIRECTION"
    SUBJECTS = "SUBJECTS"
    WORLD = "WORLD"
    PERFORMANCE = "PERFORMANCE"
    ACTION = "ACTION"
    CAMERA = "CAMERA"
    LIGHTING = "LIGHTING"
    COLOR = "COLOR"
    SOUND = "SOUND"
    EDITORIAL = "EDITORIAL"
    REFERENCE = "REFERENCE"


class DomainReference(RuntimeContract):
    domain: SourceDomain
    reference: SourceReference
    use: Literal["SHOT_FACT", "SCENE_CONSTRAINT"] = "SHOT_FACT"


class GenerationIntent(RuntimeContract):
    purpose: Literal["PREPARE_SHOT_INPUT"] = "PREPARE_SHOT_INPUT"
    duration_ms: Annotated[StrictInt, Field(gt=0, le=3_600_000)]
    duration_ref: SourceReference


class AssemblyBoundary(RuntimeContract):
    mode: RunMode
    policy_ref: ArtifactReference
    purpose: Literal["SHADOW_ASSEMBLY_ONLY"] = "SHADOW_ASSEMBLY_ONLY"
    provider_submission_allowed: Literal[False] = False
    canon_mutation_allowed: Literal[False] = False


class PackageContent(RuntimeContract):
    schema_version: Literal["production-package-v1"] = "production-package-v1"
    scope: PackageScope
    sources: tuple[DomainReference, ...] = Field(min_length=1, max_length=64)
    obligations: tuple[SourceReference, ...] = Field(min_length=1, max_length=8)
    generation_intent: GenerationIntent
    boundary: AssemblyBoundary

    @model_validator(mode="after")
    def bounded_unique_sources(self) -> Self:
        signatures = [(s.domain, s.reference.owner, s.reference.artifact_ref, s.reference.path, s.use)
                      for s in self.sources]
        if len(signatures) != len(set(signatures)):
            raise ValueError("Duplicate domain/reference selection")
        refs = [self.scope.work, self.scope.scene, self.scope.shot, *self.obligations,
                self.generation_intent.duration_ref, *(s.reference for s in self.sources)]
        if len(refs) > 64:
            raise ValueError("Package exceeds the 64 direct-reference design budget")
        versions: dict[tuple[SourceOwner, str], tuple[int | None, str]] = {}
        identities = {ref.owner: ref for ref in (self.scope.work, self.scope.scene, self.scope.shot)}
        for ref in refs:
            if ref.owner in identities:
                identity = identities[ref.owner]
                if (ref.artifact_ref, ref.version, ref.fingerprint) != (
                    identity.artifact_ref, identity.version, identity.fingerprint,
                ):
                    raise ValueError("Canonical selection differs from package scope")
            key, revision = (ref.owner, ref.artifact_ref), (ref.version, ref.fingerprint)
            if key in versions and versions[key] != revision:
                raise ValueError("Conflicting revisions of one source owner/artifact")
            versions[key] = revision
        if tuple(signatures) != tuple(sorted(signatures)):
            raise ValueError("Source selections must be in canonical order")
        if self.generation_intent.duration_ref.owner != SourceOwner.SHOT:
            raise ValueError("Shot execution duration requires its Shot owner")
        return self


class ProductionPackage(PackageContent):
    """Production snapshot/reference assembly; not a creative authority or ledger."""
    package_id: Identifier
    fingerprint: Hash

    @classmethod
    def freeze(cls, content: PackageContent) -> ProductionPackage:
        content = PackageContent.model_validate(content.model_dump())
        fingerprint = sha256_canonical(content)
        return cls(**content.model_dump(), package_id="production-package:" + fingerprint,
                   fingerprint=fingerprint)

    @model_validator(mode="after")
    def content_identity(self) -> Self:
        content = PackageContent.model_validate(self.model_dump(exclude={"package_id", "fingerprint"}))
        if self.fingerprint != sha256_canonical(content) or self.package_id != "production-package:" + self.fingerprint:
            raise ValueError("Package content identity mismatch")
        return self

    def artifact_reference(self) -> ArtifactReference:
        return ArtifactReference(owner="production-package", artifact_ref=self.package_id, version=1)


class AssemblyIssueCode(str, Enum):
    MISSING_REQUIRED_SOURCE = "MISSING_REQUIRED_SOURCE"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    VERSION_MISMATCH = "VERSION_MISMATCH"
    AUTHORITY_MISMATCH = "AUTHORITY_MISMATCH"


class AssemblyIssue(RuntimeContract):
    code: AssemblyIssueCode
    domain: SourceDomain
    owner: SourceOwner
    artifact_ref: Identifier


class AssemblyValidation(RuntimeContract):
    status: Literal["READY", "UNRESOLVED"]
    issues: tuple[AssemblyIssue, ...] = Field(default=(), max_length=64)

    @model_validator(mode="after")
    def honest_status(self) -> Self:
        if (self.status == "UNRESOLVED") != bool(self.issues):
            raise ValueError("Assembly unresolved status requires its owner issues")
        return self


class AssemblyResult(RuntimeContract):
    validation: AssemblyValidation
    package: ProductionPackage | None = None

    @model_validator(mode="after")
    def no_incomplete_package(self) -> Self:
        if (self.validation.status == "READY") != (self.package is not None):
            raise ValueError("Only resolved assembly can return a package")
        return self
