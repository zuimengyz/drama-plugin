"""Owner-separated creative facts and reference-only engine checkpoints."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Self

from pydantic import Field, JsonValue, model_validator, model_serializer, SerializerFunctionWrapHandler

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.production.contracts import SourceDomain
from drama_plugin.runtime.contracts import ArtifactReference, Identifier, RunMode, RuntimeContract, RuntimeScope

Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Text = Annotated[str, Field(min_length=1, max_length=1000000)]


class Authority(str, Enum):
    SOURCE = "source-owner"
    CANON = "canon-author"
    DIRECTION = "creative-direction-author"
    PROFESSIONAL = "professional-design-author"


class Kind(str, Enum):
    SOURCE = "SOURCE"
    WORK = "WORK"
    SCRIPT = "SCRIPT"
    SCENE = "SCENE"
    SHOT = "SHOT"
    PROFESSIONAL = "PROFESSIONAL"


class SourceBody(RuntimeContract):
    goal: Text
    text: Text | None = None
    external_reference: Text | None = None
    spoken_language: str = Field(min_length=1, max_length=80)
    spoken_language_policy: Literal["source_original", "explicit"] = "source_original"
    subtitle_languages: tuple[str, ...] = Field(default=(), max_length=8)
    original_owner_ref: ArtifactReference | None = None
    source_document_language: Identifier | None = None
    original_work_language: Identifier | None = None
    language_metadata_ref: ArtifactReference | None = None

    @model_serializer(mode="wrap")
    def compatible_source(self, handler: SerializerFunctionWrapHandler) -> dict[str, object]:
        # E2 historical seals retain their original byte representation. E3 adds
        # explicit Source owner metadata only when it is actually present.
        from typing import cast
        body = cast(dict[str, object], handler(self))
        for field, alias in (("source_document_language", "sourceDocumentLanguage"),
                             ("original_work_language", "originalWorkLanguage"),
                             ("language_metadata_ref", "languageMetadataRef")):
            if getattr(self, field) is None:
                body.pop(field, None)
                body.pop(alias, None)
        return body

    @model_validator(mode="after")
    def source_required(self) -> Self:
        if self.text is None and self.external_reference is None:
            raise ValueError("Source text or designated reference required")
        if self.original_work_language and self.spoken_language_policy == "source_original" and self.spoken_language != self.original_work_language:
            raise ValueError("Source original language is explicit owner metadata")
        return self


class WorkBody(RuntimeContract):
    interpretation: Text
    dramatic_intent: Text
    character_meaning: Text


class ScriptBody(RuntimeContract):
    screenplay: Text


class Dialogue(RuntimeContract):
    id: Identifier
    speaker: Identifier
    text: Text
    must_keep: bool = False


class SceneBody(RuntimeContract):
    scene_text: Text
    dialogue: tuple[Dialogue, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def unique_lines(self) -> Self:
        if len({line.id for line in self.dialogue}) != len(self.dialogue):
            raise ValueError("Duplicate dialogue identity")
        return self


class ShotBody(RuntimeContract):
    purpose: Text
    required_transition: Text
    duration_ms: int = Field(gt=0, le=3600000)
    subject_action: Text
    entry_state: Text
    exit_state: Text
    coverage: Text
    blocking_intent: Text
    camera_intent: Text
    editing_relation: Text
    performance_direction: Text
    spoken_ids: tuple[Identifier, ...] = Field(default=(), max_length=100)
    professional_domains: tuple[SourceDomain, ...] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def domains(self) -> Self:
        if any(d in {SourceDomain.CANON, SourceDomain.DIRECTION} for d in self.professional_domains):
            raise ValueError("Professional author cannot own Canon or Shot intent")
        if self.professional_domains != tuple(sorted(set(self.professional_domains))):
            raise ValueError("Required professional domains must be canonical")
        return self


DESIGN_FIELD_DOMAINS = {
    "perspective": SourceDomain.CAMERA, "camera_movement": SourceDomain.CAMERA,
    "source": SourceDomain.LIGHTING, "direction": SourceDomain.LIGHTING,
    "contrast": SourceDomain.LIGHTING, "ambience": SourceDomain.SOUND,
    "silence_design": SourceDomain.SOUND, "audio_events": SourceDomain.SOUND,
    "audio_relations": SourceDomain.SOUND, "foreground_background_relationship": SourceDomain.SOUND,
    "location_identity": SourceDomain.WORLD, "topology": SourceDomain.WORLD,
    "face_structure": SourceDomain.SUBJECTS, "character_ref": SourceDomain.SUBJECTS,
    "cut_points": SourceDomain.EDITORIAL, "actor_movements": SourceDomain.PERFORMANCE,
}


class DesignBody(RuntimeContract):
    domain: SourceDomain
    facts: dict[str, JsonValue] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def authority(self) -> Self:
        if self.domain in {SourceDomain.CANON, SourceDomain.DIRECTION}:
            raise ValueError("Professional design cannot author Canon/Shot intent")
        if any(field in self.facts and domain != self.domain for field, domain in DESIGN_FIELD_DOMAINS.items()):
            raise ValueError("Cross-professional field authority violation")
        forbidden = {"dialogue", "scene_text", "screenplay", "interpretation", "purpose",
                     "required_transition", "spokenContent", "approvedSceneText", "dialogue_text"}
        def check(value: JsonValue) -> None:
            if isinstance(value, dict):
                if forbidden & value.keys():
                    raise ValueError("Professional field authority violation")
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
        check(self.facts)
        return self


Body = SourceBody | WorkBody | ScriptBody | SceneBody | ShotBody | DesignBody
BODY_TYPES: dict[Kind, type[RuntimeContract]] = {Kind.SOURCE: SourceBody, Kind.WORK: WorkBody, Kind.SCRIPT: ScriptBody,
              Kind.SCENE: SceneBody, Kind.SHOT: ShotBody, Kind.PROFESSIONAL: DesignBody}
AUTHORITY = {Kind.SOURCE: Authority.SOURCE, Kind.WORK: Authority.CANON,
             Kind.SCRIPT: Authority.CANON, Kind.SCENE: Authority.CANON,
             Kind.SHOT: Authority.DIRECTION, Kind.PROFESSIONAL: Authority.PROFESSIONAL}
# Consumers never receive a creative writer entry in this executable matrix.
FIELD_AUTHORITY = {"source_meaning": Authority.CANON, "dialogue": Authority.CANON,
    "character_meaning": Authority.CANON, "shot_intent": Authority.DIRECTION,
    "lighting_design": Authority.PROFESSIONAL, "sound_design": Authority.PROFESSIONAL,
    "production_package": "shot-assembler", "prompt": "prompt-compiler"}


class VersionRef(RuntimeContract):
    identity: Identifier
    version: int = Field(gt=0)
    fingerprint: Hash

    def runtime_ref(self) -> ArtifactReference:
        return ArtifactReference(owner="creative-version", artifact_ref="creative:" + self.fingerprint,
                                 version=self.version)


class CreativeVersion(RuntimeContract):
    schema_version: Literal["creative-version-v1"] = "creative-version-v1"
    identity: Identifier
    version: int = Field(gt=0)
    kind: Kind
    authority: Authority
    scope: RuntimeScope
    mode: RunMode
    state: Literal["REVIEWED", "ADOPTED"]
    source_refs: tuple[VersionRef, ...] = Field(default=(), max_length=32)
    body: Body
    adoption_decision_ref: ArtifactReference | None = None
    candidate_origin_ref: VersionRef | None = None
    fingerprint: Hash

    @model_validator(mode="after")
    def sealed(self) -> Self:
        if self.authority != AUTHORITY[self.kind] or type(self.body) != BODY_TYPES[self.kind]:
            raise ValueError("Field-level creative authority mismatch")
        if self.state == "ADOPTED" and (self.mode != RunMode.PRODUCTION or self.adoption_decision_ref is None or self.candidate_origin_ref is None):
            raise ValueError("Production adoption requires a decision")
        if self.state == "REVIEWED" and self.mode != RunMode.EXPERIMENT:
            raise ValueError("Reviewed candidate is isolated from production")
        if self.fingerprint != sha256_canonical(self.model_dump(mode="json", by_alias=True, exclude={"fingerprint"})):
            raise ValueError("Creative version hash mismatch")
        return self

    def ref(self) -> VersionRef:
        return VersionRef(identity=self.identity, version=self.version, fingerprint=self.fingerprint)


class CanonDraft(RuntimeContract):
    work: WorkBody
    script: ScriptBody
    scene: SceneBody


class RevisionRequest(RuntimeContract):
    owner: Authority
    target_ref: VersionRef
    finding_ref: ArtifactReference
    instruction: Text
    depth: int = Field(default=1, ge=1, le=3)


class AuthorRequest(RuntimeContract):
    scope: RuntimeScope
    source: SourceBody
    source_refs: tuple[VersionRef, ...]
    canon: CanonDraft | None = None
    shot: ShotBody | None = None
    revision: RevisionRequest | None = None
    finding_refs: tuple[ArtifactReference, ...] = Field(default=(), max_length=4)


class RouteRequest(RuntimeContract):
    output: Literal["video", "image", "audio"] = "video"
    input_mode: Literal["text_to_video", "image_to_video", "reference", "reference_video", "audio"] = "text_to_video"
    available_inputs: tuple[Literal["first_frame", "character_reference", "environment_reference", "audio"], ...] = ()
    available_capabilities: tuple[str, ...] = Field(default=(), max_length=16)
    estimated_child_cost: int = Field(default=0, ge=0)
    cost_limit: int = Field(default=0, ge=0)


class DependencyTask(RuntimeContract):
    task_id: Identifier
    output: Literal["video", "image", "audio"]
    requires: tuple[Identifier, ...] = Field(default=(), max_length=4)
    attempts: int = Field(default=0, ge=0, le=2)
    estimated_cost: int = Field(default=0, ge=0)


class RoutePlan(RuntimeContract):
    route: str
    tasks: tuple[DependencyTask, ...] = Field(min_length=1, max_length=32)
    max_tasks: int = Field(default=16, ge=1, le=32)
    max_depth: int = Field(default=3, ge=1, le=16)
    capability_available: bool
    authorization_required: bool
    cost_limit: int = Field(ge=0)

    @model_validator(mode="after")
    def bounded_acyclic(self) -> Self:
        nodes = {task.task_id: task for task in self.tasks}
        if len(self.tasks) > self.max_tasks:
            raise ValueError("Dependency child count exceeded")
        if len(nodes) != len(self.tasks):
            raise ValueError("Duplicate dependency task")
        def visit(identity: str, ancestors: tuple[str, ...]) -> None:
            if identity in ancestors or identity not in nodes:
                raise ValueError("Dependency cycle or missing child")
            if len(ancestors) > self.max_depth:
                raise ValueError("Dependency depth exceeded")
            for child in nodes[identity].requires:
                visit(child, (*ancestors, identity))
        for identity in nodes:
            visit(identity, ())
        if sum(task.estimated_cost for task in self.tasks) > self.cost_limit:
            raise ValueError("Dependency estimated cost exceeded")
        return self


class FilmInput(RuntimeContract):
    source_ref: VersionRef
    approved_canon_refs: tuple[VersionRef, ...] = Field(default=(), max_length=3)
    route: RouteRequest = RouteRequest()
    revision: RevisionRequest | None = None
    base_refs: tuple[VersionRef, ...] = Field(default=(), max_length=16)
    max_author_rounds: int = Field(default=6, ge=1, le=6)
    prior_revision_signatures: tuple[Hash, ...] = Field(default=(), max_length=3)


class CreativeIntegrityReconciliation(RuntimeContract):
    """One bounded reference-only publication journal per creative run."""
    parent: ArtifactReference
    original_refs: tuple[VersionRef, ...] = Field(min_length=1, max_length=16)
    candidate: ArtifactReference | None = None
    revised_refs: tuple[VersionRef, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def publication_shape(self) -> Self:
        if self.parent.owner != "creative-candidate" or self.parent.version != 1:
            raise ValueError("Integrity parent must be an exact creative candidate")
        if (self.candidate is None) != (not self.revised_refs):
            raise ValueError("Integrity publication requires its exact version set")
        if self.candidate is not None and (self.candidate.owner != "creative-candidate" or self.candidate.version != 1
                or self.candidate.artifact_ref != "creative-candidate:" + sha256_canonical(
                    [r.model_dump(mode="json", by_alias=True) for r in self.revised_refs])):
            raise ValueError("Integrity candidate hash mismatch")
        return self


class CreativeCheckpoint(RuntimeContract):
    refs: tuple[VersionRef, ...] = Field(default=(), max_length=16)
    author_rounds: int = Field(default=0, ge=0, le=6)
    route_plan: RoutePlan | None = None
    decision_ref: ArtifactReference | None = None
    candidate_ref: ArtifactReference | None = None
    candidate_version_refs: tuple[VersionRef, ...] = Field(default=(), max_length=16)
    package_ref: ArtifactReference | None = None
    child_runs: tuple[str, ...] = Field(default=(), max_length=4)
    completed_operations: tuple[str, ...] = Field(default=(), max_length=12)

    def candidate_fingerprint(self) -> str:
        return sha256_canonical([r.model_dump(mode="json", by_alias=True) for r in self.refs])


def scope_contains(author: RuntimeScope, consumer: RuntimeScope) -> bool:
    """A Work/Scene Canon ancestor may be shared; a Shot cannot cross its scope."""
    return (author.work_id == consumer.work_id and
            (author.scene_id is None or author.scene_id == consumer.scene_id) and
            (author.shot_id is None or author.shot_id == consumer.shot_id))
