"""Package-bound reads. No department discovery, Host projection, history or Canon write."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Protocol

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.production.contracts import (
    AssemblyIssueCode, DomainReference, ProductionPackage, SourceOwner, SourceReference,
)
from drama_plugin.production.sources import SourceReadError


class ReferenceResolver(Protocol):
    async def resolve(self, reference: SourceReference) -> Any: ...


@dataclass(frozen=True)
class SelectedValue:
    selection: DomainReference
    value: Any


def child(ref: SourceReference, *path: str) -> SourceReference:
    return SourceReference(**{**ref.model_dump(), "path": ref.path + path})


class LegacyExecutionReferences:
    """MIGRATION_ONLY: explicit transitive pins already present in a Package selection.

    Storage layout is configured once by the existing professional roots. Only two
    historical formats are decoded, never arbitrary file paths or tool passthrough.
    A pin is a dependency of the approved selected record, not permission to author.
    """
    lifecycle = "MIGRATION_ONLY"

    def __init__(self, roots: tuple[Path, ...]):
        self.roots = roots

    def resolve_pin(self, pin: dict[str, Any], *, work_id: str) -> tuple[SourceReference, Any]:
        key = pin.get("key", "")
        found = []
        for root in self.roots:
            if key.startswith("performance:") and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", key.split(":", 1)[1]):
                file = root.parent / (key.split(":", 1)[1] + "-performance-direction.json")
                if file.is_file():
                    found.append(json.loads(file.read_text()))
            elif key.startswith("asset-compilation:" + work_id + ":"):
                file = root / "asset-compilations.json"
                if file.is_file():
                    found.extend(row["compilation"] for row in json.loads(file.read_text())
                                 if row.get("compilationRef", {}).get("key") == key)
        if not found:
            raise SourceReadError(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, SourceOwner.PROFESSIONAL, key)
        if any(sha256_canonical(value) != pin.get("fingerprint") for value in found):
            raise SourceReadError(AssemblyIssueCode.VERSION_MISMATCH, SourceOwner.PROFESSIONAL, key)
        value = found[0]
        if key.startswith("asset-compilation:") and value.get("workId") != work_id:
            raise SourceReadError(AssemblyIssueCode.SCOPE_MISMATCH, SourceOwner.PROFESSIONAL, key)
        return SourceReference(owner=SourceOwner.PROFESSIONAL, artifact_ref=key, version=None,
                               fingerprint=sha256_canonical(value)), value

    def resolve_reference(self, reference: SourceReference, *, work_id: str) -> Any:
        _, body = self.resolve_pin({"key": reference.artifact_ref, "fingerprint": reference.fingerprint}, work_id=work_id)
        selected = body
        try:
            for segment in reference.path:
                selected = selected[int(segment)] if isinstance(selected, list) else selected[segment]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise SourceReadError(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, reference.owner, reference.artifact_ref) from error
        return selected


class PackageReader:
    """The production consumer only resolves the selections granted by this Package."""
    creative_authority = False

    def __init__(self, resolver: ReferenceResolver, dependencies: LegacyExecutionReferences):
        self.resolver, self.dependencies = resolver, dependencies

    async def selections(self, package: ProductionPackage) -> tuple[SelectedValue, ...]:
        values = []
        for selection in package.sources:
            # Full approved Scene is a Canon lock, never a Prompt material pool.
            if selection.domain == "CANON":
                continue
            values.append(SelectedValue(selection, await self.resolver.resolve(selection.reference)))
        return tuple(values)

    async def obligation_values(self, package: ProductionPackage) -> tuple[tuple[SourceReference, Any], ...]:
        return tuple([(ref, await self.resolver.resolve(ref)) for ref in package.obligations])

    async def validate_execution_refs(self, references: tuple[SourceReference, ...], *, work_id: str) -> None:
        for ref in dict.fromkeys(references):
            if ref.artifact_ref.startswith(("performance:", "asset-compilation:")):
                self.dependencies.resolve_reference(ref, work_id=work_id)
            else:
                await self.resolver.resolve(ref)
