"""Approved Performance projection scope. Consumers cannot issue exemptions.

No psychology authoring, workflow, provider, or additional persistence store.
The immutable declaration lives with its originals, never in the execution ledger.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from pydantic import Field, JsonValue, TypeAdapter, model_validator

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.dpd import PerformanceTargetRole
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.contracts import Authority, DesignBody, Kind, SceneBody, ShotBody, VersionRef
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.runtime.contracts import ArtifactReference, Identifier, RuntimeContract, RuntimeScope


class SubjectProjection(RuntimeContract):
    subject_ref: Identifier
    source_target_label: str = Field(min_length=1)
    role: PerformanceTargetRole
    beat_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=100)
    spoken_ids: tuple[Identifier, ...] = Field(default=(), max_length=100)
    reciprocal_actions: tuple[str, ...] = ()
    authored_responses: tuple[str, ...] = ()
    listener_tasks: tuple[str, ...] = ()
    objectives: tuple[str, ...] = ()
    obstacles: tuple[str, ...] = ()
    tactics: tuple[str, ...] = ()
    dramatic_exchanges: tuple[str, ...] = ()
    spatial_presence_only: bool = False
    behavior_expansion_forbidden: bool = False

    @model_validator(mode="after")
    def destination_has_no_performance(self) -> Self:
        if self.role == PerformanceTargetRole.NON_INTERACTIVE_DESTINATION and (
            not self.spatial_presence_only or not self.behavior_expansion_forbidden
            or any((self.spoken_ids, self.reciprocal_actions, self.authored_responses,
                    self.listener_tasks, self.objectives, self.obstacles, self.tactics, self.dramatic_exchanges))
        ):
            raise ValueError("PARTNER_DPD_REQUIRED: destination has interactive obligations")
        return self


class ProjectionEvidence(RuntimeContract):
    field_path: tuple[str, ...] = Field(min_length=1, max_length=12)
    value_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class PerformanceProjectionScope(RuntimeContract):
    scope: RuntimeScope
    performance_ref: VersionRef
    scene_ref: VersionRef
    shot_ref: VersionRef
    adoption_decision_ref: ArtifactReference
    evidence: tuple[ProjectionEvidence, ...] = Field(min_length=1, max_length=32)
    subjects: tuple[SubjectProjection, ...] = Field(min_length=1, max_length=100)


_ISSUER = object()
JSON: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)


def _facts_at(facts: JsonValue, path: tuple[str, ...]) -> JsonValue:
    value = facts
    for part in path:
        if isinstance(value, dict):
            value = value[part]
        elif isinstance(value, list) and part.isdecimal():
            value = value[int(part)]
        else:
            raise ValueError("PERFORMANCE_SCOPE_EVIDENCE_PATH")
    return value


def _validate(versions: CreativeVersionStore, declaration: PerformanceProjectionScope) -> None:
    originals = [versions.resolve(r) for r in (
        declaration.performance_ref, declaration.scene_ref, declaration.shot_ref)]
    performance, scene, shot = originals
    if (performance.kind != Kind.PROFESSIONAL or not isinstance(performance.body, DesignBody)
            or performance.body.domain.value != "PERFORMANCE"
            or not isinstance(scene.body, SceneBody) or not isinstance(shot.body, ShotBody)):
        raise ValueError("PERFORMANCE_SCOPE_WRONG_OWNER")
    if any(v.state != "ADOPTED" or v.scope != declaration.scope
           or v.adoption_decision_ref != declaration.adoption_decision_ref for v in originals):
        raise ValueError("PERFORMANCE_SCOPE_UNAPPROVED")
    if any(versions.stale(v.ref()) for v in originals):
        raise ValueError("PARTNER_DPD_REQUIRED: STALE_PERFORMANCE_SCOPE")
    if not {declaration.scene_ref, declaration.shot_ref} <= set(performance.source_refs):
        raise ValueError("PERFORMANCE_SCOPE_PARENT_MISMATCH")
    facts = JSON.validate_python(performance.body.facts)
    for evidence in declaration.evidence:
        if sha256_canonical(_facts_at(facts, evidence.field_path)) != evidence.value_hash:
            raise ValueError("PERFORMANCE_SCOPE_EVIDENCE_MISMATCH")
    subjects = {s.subject_ref: s for s in declaration.subjects}
    if len(subjects) != len(declaration.subjects):
        raise ValueError("DUPLICATE_PERFORMANCE_SUBJECT")
    for line in scene.body.dialogue:
        subject = subjects.get(line.speaker)
        if subject is None or subject.role == PerformanceTargetRole.NON_INTERACTIVE_DESTINATION:
            raise ValueError("PARTNER_DPD_REQUIRED: canonical spoken content")
    authored_beats = performance.body.facts.get("beats")
    if not isinstance(authored_beats, list):
        raise ValueError("PERFORMANCE_BEAT_INVENTORY_REQUIRED")
    for beat in authored_beats:
        if not isinstance(beat, dict):
            raise ValueError("PERFORMANCE_BEAT_INVENTORY_REQUIRED")
        actor = beat.get("actor")
        subject = subjects.get(actor) if isinstance(actor, str) else None
        if (subject is None or subject.role != PerformanceTargetRole.INTERACTIVE_PARTNER
                or beat.get("id") not in subject.beat_ids):
            raise ValueError("PARTNER_DPD_REQUIRED: authored actor inventory")
    for subject in subjects.values():
        if subject.role == PerformanceTargetRole.INTERACTIVE_PARTNER:
            exact_lines = {line.id for line in scene.body.dialogue if line.speaker == subject.subject_ref}
            if set(subject.spoken_ids) != exact_lines:
                raise ValueError("PERFORMANCE_SCOPE_SPOKEN_INVENTORY_MISMATCH")
    for subject in subjects.values():
        if subject.role != PerformanceTargetRole.NON_INTERACTIVE_DESTINATION:
            continue
        rows = [b for b in authored_beats if isinstance(b, dict) and b.get("id") in subject.beat_ids]
        if len(rows) != len(subject.beat_ids) or any(b.get("target") != subject.source_target_label for b in rows):
            raise ValueError("PERFORMANCE_DESTINATION_SOURCE_BINDING")
        for b in rows:
            # These are missing *requirements*, not negative psychology. Only an
            # explicit authority declaration can interpret the bound note.
            if any(b.get(field) != "Not authored." for field in ("objective", "obstacle", "tactic")):
                raise ValueError("PARTNER_DPD_REQUIRED: authored exchange requirement")
            if not isinstance(b.get("note"), str) or not str(b["note"]).strip():
                raise ValueError("PERFORMANCE_DESTINATION_EVIDENCE_REQUIRED")
            expected_paths = {("beats", str(authored_beats.index(b)), field)
                              for field in ("note", "objective", "obstacle", "tactic", "target")}
            if not expected_paths <= {e.field_path for e in declaration.evidence}:
                raise ValueError("PERFORMANCE_DESTINATION_EVIDENCE_REQUIRED")
        def reject_authored_response(value: JsonValue) -> None:
            if isinstance(value, dict):
                keys = (subject.subject_ref, subject.source_target_label)
                if any(value.get(k) in keys for k in ("actor", "speaker", "listener", "subjectRef", "subject_ref")):
                    if any(value.get(k) not in (None, "", "Not authored.", [], ()) for k in (
                        "action", "actions", "response", "responses", "authoredResponse", "authored_responses",
                        "reciprocalAction", "reciprocal_action", "reciprocal_actions", "listenerTask", "listener_task", "listener_tasks",
                        "objective", "obstacle", "tactic", "dialogue", "spokenContent")):
                        raise ValueError("PARTNER_DPD_REQUIRED: authored destination response")
                for child in value.values():
                    reject_authored_response(child)
            elif isinstance(value, list):
                for child in value:
                    reject_authored_response(child)
        reject_authored_response(facts)


@dataclass(frozen=True)
class PerformanceScopeWitness:
    """Ephemeral owner-issued witness, patterned on FormalSourceWitness."""
    _issuer: object
    _versions: CreativeVersionStore
    _pin: SourcePin

    def current(self) -> PerformanceProjectionScope:
        if self._issuer is not _ISSUER:
            raise ValueError("TRUSTED_PERFORMANCE_SCOPE_REQUIRED")
        declaration = PerformanceProjectionScope.model_validate(self._versions.objects.read_ref(self._pin))
        _validate(self._versions, declaration)
        return declaration


def retain_performance_scope(versions: CreativeVersionStore, declaration: PerformanceProjectionScope,
                             *, writer: Authority) -> SourcePin:
    """Explicit composed Performance authority write; never a consumer default."""
    if writer != Authority.PROFESSIONAL:
        raise ValueError("PERFORMANCE_SCOPE_WRONG_WRITER")
    _validate(versions, declaration)
    body = declaration.model_dump(mode="json", by_alias=True)
    return versions.objects.put("performance-projection-scope:" + sha256_canonical(body), body)


def read_performance_scope(versions: CreativeVersionStore, pin: SourcePin) -> PerformanceScopeWitness:
    if not pin.key.startswith("performance-projection-scope:"):
        raise ValueError("TRUSTED_PERFORMANCE_SCOPE_REQUIRED")
    witness = PerformanceScopeWitness(_ISSUER, versions, pin)
    witness.current()
    return witness
