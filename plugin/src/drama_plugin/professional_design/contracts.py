"""Small, ephemeral Professional Design queries and reference selections."""
from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from drama_plugin.production.contracts import (
    AssemblyIssue, DomainReference, PackageScope, SourceDomain, SourceOwner,
)
from drama_plugin.runtime.contracts import RuntimeContract


class ProfessionalDesignRequest(RuntimeContract):
    scope: PackageScope
    # Empty means the existing Shot's declared professional references, not the platform registry.
    domains: tuple[SourceDomain, ...] = Field(default=(), max_length=11)

    @model_validator(mode="after")
    def professional_domains(self) -> Self:
        if SourceDomain.CANON in self.domains or self.domains != tuple(sorted(set(self.domains))):
            raise ValueError("Professional domains must be unique, canonical and exclude CANON")
        return self


class ProfessionalDesignSelection(RuntimeContract):
    """Not a creative package, ledger, new Canon, or required/optional policy."""
    domains: tuple[SourceDomain, ...] = Field(max_length=11)
    sources: tuple[DomainReference, ...] = Field(default=(), max_length=64)
    issues: tuple[AssemblyIssue, ...] = Field(default=(), max_length=64)

    @model_validator(mode="after")
    def reference_only(self) -> Self:
        if SourceDomain.CANON in self.domains or self.domains != tuple(sorted(set(self.domains))):
            raise ValueError("Selection must use the existing professional domain vocabulary")
        signatures = [(s.domain, s.reference.owner, s.reference.artifact_ref, s.reference.path, s.use)
                      for s in self.sources]
        if signatures != sorted(set(signatures)):
            raise ValueError("Professional selection must be unique and deterministic")
        if any(s.domain not in self.domains or s.reference.owner not in {
            SourceOwner.DIRECTION, SourceOwner.PROFESSIONAL,
        } for s in self.sources):
            raise ValueError("Professional selection must preserve existing professional/direction owners")
        return self

    @property
    def status(self) -> Literal["RESOLVED", "MISSING", "CONFLICT"]:
        if not self.issues:
            return "RESOLVED"
        if any(i.code != "MISSING_REQUIRED_SOURCE" for i in self.issues):
            return "CONFLICT"
        return "MISSING"


class ProfessionalReferenceCheck(RuntimeContract):
    """One bounded validation batch; ref-only, without the rest of a ProductionPackage."""
    scope: PackageScope
    sources: tuple[DomainReference, ...] = Field(min_length=1, max_length=64)
