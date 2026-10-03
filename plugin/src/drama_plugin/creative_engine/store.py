"""Minimal immutable creative resolver; bytes reuse the existing content-addressed owner IO.

No Director workspace/transition or legacy author workflow is called. Ledger keeps
only typed refs/checkpoints; the objects here remain outside execution persistence.
"""
from __future__ import annotations
from drama_plugin.creative_engine.contracts import scope_contains

import json
from pathlib import Path
from typing import TYPE_CHECKING

from drama_plugin.contracts.base import canonical_json, sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.hosts.artifact_io import native_io, reject_link
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.runtime.contracts import ArtifactReference, RunMode, RuntimeScope
from pydantic import TypeAdapter

from drama_plugin.creative_engine.contracts import (
    AUTHORITY, Authority, Body, CreativeCheckpoint, CreativeVersion, DesignBody, FilmInput, Kind, VersionRef,
)

if TYPE_CHECKING:
    from drama_plugin.persistence.ledger import ProductionLedger


class CreativeVersionStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.objects = DirectorArtifactStore(self.root)
        self.io = native_io()
        self.index = self.root / "creative-index"
        self.index.mkdir(exist_ok=True)

    def _path(self, group: str, key: object) -> Path:
        reject_link(self.index)
        return self.index / (group + "-" + sha256_canonical(key) + ".json")

    def _read_ref(self, path: Path) -> VersionRef:
        reject_link(path)
        return VersionRef.model_validate_json(path.read_text())

    def head(self, identity: str) -> VersionRef | None:
        path = self._path("head", identity)
        return self._read_ref(path) if path.exists() else None

    def resolve(self, ref: VersionRef) -> CreativeVersion:
        body = self.objects.read_ref(SourcePin(key=ref.identity, kind="CANON", fingerprint=ref.fingerprint))
        artifact = CreativeVersion.model_validate({**body, "fingerprint": ref.fingerprint})
        if artifact.ref() != ref:
            raise ValueError("Creative version identity mismatch")
        return artifact

    def from_runtime_ref(self, ref: ArtifactReference) -> CreativeVersion:
        if ref.owner != "creative-version" or ref.version is None or not ref.artifact_ref.startswith("creative:"):
            raise ValueError("Not an exact creative version")
        retained = self._read_ref(self._path("fingerprint", ref.artifact_ref.split(":", 1)[1]))
        if retained.runtime_ref() != ref:
            raise ValueError("Wrong creative version")
        return self.resolve(retained)

    def write(self, *, writer: Authority, kind: Kind, scope: RuntimeScope, body: Body,
              sources: tuple[VersionRef, ...], operation: str,
              adoption_decision: ArtifactReference | None = None, candidate_origin: VersionRef | None = None) -> VersionRef:
        if writer != AUTHORITY[kind]:
            raise ValueError("CANON_AUTHORITY_MISMATCH")
        for source in sources:
            prior = self.resolve(source)
            if not scope_contains(prior.scope, scope):
                raise ValueError("PACKAGE_SCOPE_MISMATCH")
        if adoption_decision:
            if candidate_origin is None:
                raise ValueError("Adoption needs its exact candidate origin")
            candidate = self.resolve(candidate_origin)
            from drama_plugin.professional_design.provenance import creative_facts
            same_body = (creative_facts(candidate.body.facts) == creative_facts(body.facts)
                if isinstance(body, DesignBody) and isinstance(candidate.body, DesignBody) else candidate.body == body)
            if candidate.state != "REVIEWED" or (candidate.kind, candidate.scope) != (kind, scope) or not same_body:
                raise ValueError("Adoption cannot rewrite its candidate content")
        if isinstance(body, DesignBody):
            from drama_plugin.professional_design.provenance import project_metadata, validate_metadata
            if adoption_decision:
                assert isinstance(candidate.body, DesignBody)
                validate_metadata(candidate.body, self, candidate.scope, candidate.source_refs)
            else:
                validate_metadata(body, self, scope, sources, required=False)
            body = project_metadata(body, self, scope, sources)
        phase = "production" if adoption_decision else "candidate"
        domain = getattr(body, "domain", "")
        identity = "creative-" + kind.value.lower() + ":" + sha256_canonical([scope.model_dump(mode="json", by_alias=True), phase, domain])
        with self.io.guard(self.root / ".creative-writer.lock"):
            op_path = self._path("operation", operation)
            if op_path.exists():
                retained = self.resolve(self._read_ref(op_path))
                if (retained.kind, retained.scope, retained.body, retained.source_refs, retained.adoption_decision_ref) != (
                        kind, scope, body, sources, adoption_decision):
                    raise ValueError("Creative operation identity conflict")
                return retained.ref()
            head = self.head(identity)
            if kind == Kind.SOURCE and head is not None and self.resolve(head).body == body:
                self.io.write(op_path, canonical_json(head))
                return head
            fields = dict(schema_version="creative-version-v1", identity=identity,
                version=1 if head is None else head.version + 1, kind=kind, authority=writer,
                scope=scope, mode=RunMode.PRODUCTION if adoption_decision else RunMode.EXPERIMENT,
                state="ADOPTED" if adoption_decision else "REVIEWED", source_refs=sources,
                body=body, adoption_decision_ref=adoption_decision)
            # Canonical model serialization includes defaults/aliases; derive its seal without bypassing validation.
            from drama_plugin.creative_engine.contracts import BODY_TYPES
            normalized = {"schemaVersion": fields["schema_version"], "identity": identity,
                "version": fields["version"], "kind": kind.value, "authority": writer.value,
                "scope": scope.model_dump(mode="json", by_alias=True), "mode": (RunMode.PRODUCTION if adoption_decision else RunMode.EXPERIMENT).value,
                "state": fields["state"], "sourceRefs": [r.model_dump(mode="json", by_alias=True) for r in sources],
                "body": BODY_TYPES[kind].model_validate(body.model_dump()).model_dump(mode="json", by_alias=True),
                "adoptionDecisionRef": adoption_decision.model_dump(mode="json", by_alias=True) if adoption_decision else None,
                "candidateOriginRef": candidate_origin.model_dump(mode="json", by_alias=True) if candidate_origin else None}
            fingerprint = sha256_canonical(normalized)
            artifact = CreativeVersion.model_validate({**normalized, "fingerprint": fingerprint})
            pin = self.objects.put(identity, normalized)
            if pin.fingerprint != fingerprint:
                raise ValueError("Owner content hash mismatch")
            ref = artifact.ref()
            for path in (self._path("version", [identity, ref.version]), self._path("fingerprint", fingerprint),
                         self._path("head", identity), op_path):
                self.io.write(path, canonical_json(ref))
            return ref

    def invalidate(self, ref: VersionRef) -> None:
        self.resolve(ref)
        with self.io.guard(self.root / ".creative-writer.lock"):
            self.io.write(self._path("stale", ref), "true")

    def stale(self, ref: VersionRef, ancestors: tuple[str, ...] = ()) -> bool:
        artifact = self.resolve(ref)
        if ref.fingerprint in ancestors:
            raise ValueError("Creative dependency cycle")
        if self._path("stale", ref).exists() or self.head(ref.identity) != ref:
            return True
        return any(self.stale(parent, (*ancestors, ref.fingerprint)) for parent in artifact.source_refs)

    def remember_projection(self, fingerprint: str, ref: VersionRef) -> None:
        path = self._path("projection", fingerprint)
        with self.io.guard(self.root / ".creative-writer.lock"):
            if path.exists() and self._read_ref(path) != ref:
                raise ValueError("Projection identity conflict")
            self.io.write(path, canonical_json(ref))

    def projection(self, fingerprint: str) -> CreativeVersion:
        return self.resolve(self._read_ref(self._path("projection", fingerprint)))

    def remember_selection(self, scope: RuntimeScope, refs: tuple[VersionRef, ...]) -> None:
        shot = next(self.resolve(ref) for ref in refs if self.resolve(ref).kind == Kind.SHOT)
        value = [ref.model_dump(mode="json", by_alias=True) for ref in refs]
        with self.io.guard(self.root / ".creative-writer.lock"):
            self.io.write(self._path("selection", shot.ref()), canonical_json(value))
            self.io.write(self._path("scope-selection", [scope.model_dump(mode="json", by_alias=True), shot.mode.value]), canonical_json(value))

    def selected_refs(self, shot: VersionRef) -> tuple[VersionRef, ...]:
        return TypeAdapter(tuple[VersionRef, ...]).validate_json(self._path("selection", shot).read_text())

    def approved_selection(self, scope: RuntimeScope) -> tuple[VersionRef, ...] | None:
        path = self._path("scope-selection", [scope.model_dump(mode="json", by_alias=True), RunMode.PRODUCTION.value])
        return TypeAdapter(tuple[VersionRef, ...]).validate_json(path.read_text()) if path.exists() else None


class CreativeStateStore:
    """Reference-only state in existing ledger indexes, in-memory only for Foundation tests."""
    def __init__(self, ledger: ProductionLedger | None):
        self.ledger = ledger
        self.inputs: dict[str, FilmInput] = {}
        self.checkpoints: dict[str, CreativeCheckpoint] = {}

    def bind(self, run_id: str, scope: RuntimeScope, value: FilmInput) -> None:
        if self.ledger is not None:
            self.ledger.put_index("creative-input", run_id, value, scope=scope, once=True)
            self.ledger.put_index("creative-checkpoint", run_id, CreativeCheckpoint(), scope=scope, once=True)
        elif run_id in self.inputs:
            raise ValueError("Creative input already bound")
        else:
            self.inputs[run_id], self.checkpoints[run_id] = value, CreativeCheckpoint()

    def input(self, run_id: str) -> FilmInput:
        return FilmInput.model_validate(self.ledger.get_index("creative-input", run_id)) if self.ledger else self.inputs[run_id]

    def checkpoint(self, run_id: str) -> CreativeCheckpoint:
        return CreativeCheckpoint.model_validate(self.ledger.get_index("creative-checkpoint", run_id)) if self.ledger else self.checkpoints[run_id]

    def save(self, run_id: str, scope: RuntimeScope, value: CreativeCheckpoint) -> None:
        value = CreativeCheckpoint.model_validate(value.model_dump())
        if self.ledger:
            self.ledger.put_index("creative-checkpoint", run_id, value, scope=scope)
        else:
            self.checkpoints[run_id] = value
