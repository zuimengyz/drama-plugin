"""Film manifests bind immutable author versions; consumers have no writing authority."""
from __future__ import annotations
from typing import ClassVar, Literal, Self
from pydantic import Field, ValidationInfo, model_validator
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.contracts import CanonDraft, SceneBody, ShotBody, SourceBody, VersionRef, WorkBody, ScriptBody, RoutePlan, RevisionRequest
from drama_plugin.execution.contracts import MediaIdentity, ReviewObservation
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.generation.contracts import GenerationTask
from drama_plugin.runtime.contracts import ArtifactReference, Identifier, RuntimeContract, ExtendedRuntimeContract, RuntimeScope

_SEAL = object()

class LanguageMetadata(RuntimeContract):
    source_document_language: Identifier
    original_work_language: Identifier
    spoken_language_policy: Literal['source_original', 'explicit'] = 'source_original'
    spoken_language: Identifier
    subtitle_language: Identifier | None = None
    authority_ref: ArtifactReference

    @model_validator(mode='after')
    def original(self) -> Self:
        if self.spoken_language_policy == 'source_original' and self.spoken_language != self.original_work_language:
            raise ValueError('Source owner must resolve original work language explicitly')
        return self

class SubtitleLocalization(RuntimeContract):
    dialogue_id: Identifier
    source_text_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    language: Identifier
    text: str = Field(min_length=1, max_length=3000)

class CanonScene(RuntimeContract):
    scene_id: Identifier
    scene: SceneBody
    subtitle_localizations: tuple[SubtitleLocalization, ...] = Field(default=(), max_length=100)

class FilmCanon(RuntimeContract):
    work: WorkBody
    script: ScriptBody
    scenes: tuple[CanonScene, ...] = Field(min_length=1, max_length=12)

    @model_validator(mode='after')
    def identities(self) -> Self:
        if len({s.scene_id for s in self.scenes}) != len(self.scenes):
            raise ValueError('Duplicate Scene')
        return self

class DirectedShot(RuntimeContract):
    scene_id: Identifier
    shot_id: Identifier
    shot: ShotBody
    requires: tuple[Identifier, ...] = Field(default=(), max_length=4)
    # Only already represented cuts are executable; unsupported transitions wait.
    transition: Literal['cut'] = 'cut'

class FilmDirection(RuntimeContract):
    shots: tuple[DirectedShot, ...] = Field(min_length=1, max_length=12)

    @model_validator(mode='after')
    def identities(self) -> Self:
        if len({s.shot_id for s in self.shots}) != len(self.shots):
            raise ValueError('Duplicate Shot')
        return self

class FilmAuthorRequest(RuntimeContract):
    scope: RuntimeScope
    source: SourceBody
    languages: LanguageMetadata
    source_ref: VersionRef
    canon: FilmCanon | None = None
    production_goal: Literal["MEDIA_REVIEW"] | None = None

class SubtitleCue(RuntimeContract):
    shot_id: Identifier
    language: Identifier
    text: str = Field(min_length=1, max_length=3000)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    timing_ref: ArtifactReference
    text_ref: ArtifactReference
    localization_ref: ArtifactReference | None = None
    @model_validator(mode='after')
    def ordered(self) -> Self:
        if self.end_ms <= self.start_ms:
            raise ValueError('Measured speech timing required')
        return self

class DeliveryProfile(RuntimeContract):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    audio_required: bool = True
    duration_tolerance_ms: int = Field(default=250, ge=0, le=1000)
    subtitle_required: bool = False

class FilmInput(RuntimeContract):
    source_ref: VersionRef
    languages: LanguageMetadata
    route: Identifier
    model: Identifier
    profile: DeliveryProfile
    rights_refs: tuple[ArtifactReference, ...] = Field(min_length=1, max_length=8)
    subtitle_cues: tuple[SubtitleCue, ...] = Field(default=(), max_length=100)
    max_cost_microunits: int = Field(default=0, ge=0)
    estimated_shot_cost_microunits: int = Field(default=0, ge=0)
    operation_duration_ms: int = Field(default=4000, ge=1000, le=15000)

class ShotUnit(RuntimeContract):
    scene_id: Identifier
    shot_id: Identifier
    creative_run_id: Identifier
    production_run_id: Identifier | None = None
    generation_run_id: Identifier | None = None
    execution_run_id: Identifier | None = None
    refs: tuple[VersionRef, ...] = Field(default=(), max_length=16)
    package_ref: ArtifactReference | None = None
    candidate_ref: ArtifactReference | None = None
    revision_depth: int = Field(default=0, ge=0, le=3)
    revision_signatures: tuple[str, ...] = Field(default=(), max_length=3)

class FilmCheckpoint(ExtendedRuntimeContract):
    extension_fields = ('scene_media_run_ids', 'scene_media_review_refs', 'scene_media_pending_tasks', 'scene_media_goal_hash', 'media_batch_ref', 'media_batch_opening_review_ref')
    canon_ref: ArtifactReference | None = None
    direction_ref: ArtifactReference | None = None
    plan_ref: ArtifactReference | None = None
    units: tuple[ShotUnit, ...] = Field(default=(), max_length=12)
    graph: RoutePlan | None = None
    adoption_ref: ArtifactReference | None = None
    film_version: int = Field(default=1, ge=1)
    final_ref: ArtifactReference | None = None
    qa_ref: ArtifactReference | None = None
    review_ref: ArtifactReference | None = None
    acceptance_ref: ArtifactReference | None = None
    delivery_ref: ArtifactReference | None = None
    revision_parent_ref: ArtifactReference | None = None
    revision_child_run_id: Identifier | None = None
    planning_cost_decision_ref: ArtifactReference | None = None
    rights_request_pin: SourcePin | None = None
    rights_decision_ref: ArtifactReference | None = None
    rights_pin: SourcePin | None = None
    scope_request_pin: SourcePin | None = None
    scope_decision_ref: ArtifactReference | None = None
    operation_task: GenerationTask | None = None
    scene_media_run_ids: tuple[Identifier, ...] | None = Field(default=None, min_length=1, max_length=3)
    scene_media_review_refs: tuple[ArtifactReference, ...] | None = Field(default=None, max_length=3)
    scene_media_pending_tasks: tuple[GenerationTask, ...] | None = Field(default=None, max_length=3)
    scene_media_goal_hash: Identifier | None = None
    media_batch_ref: ArtifactReference | None = None
    media_batch_opening_review_ref: ArtifactReference | None = None
    completed: tuple[Identifier, ...] = Field(default=(), max_length=16)

class FilmArtifact(RuntimeContract):
    owner: ClassVar[str]
    schema_version: str
    scope: RuntimeScope
    run_id: Identifier
    film_version: int = Field(ge=1)
    fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')
    @classmethod
    def seal(cls, **values: object) -> Self:
        candidate = cls.model_validate({**values, 'fingerprint': '0'*64}, context=_SEAL)
        body = candidate.model_dump(mode='json', by_alias=True, exclude={'fingerprint'})
        return cls.model_validate({**body, 'fingerprint': sha256_canonical(body)})
    @model_validator(mode='after')
    def sealed(self, info: ValidationInfo) -> Self:
        if self.scope.scene_id or self.scope.shot_id:
            raise ValueError('Film manifest requires Film scope')
        if info.context is not _SEAL and self.fingerprint != sha256_canonical(self.model_dump(mode='json', by_alias=True, exclude={'fingerprint'})):
            raise ValueError('Film manifest hash mismatch')
        return self
    def artifact_reference(self) -> ArtifactReference:
        return ArtifactReference(owner=self.owner, artifact_ref=self.owner+':'+self.fingerprint, version=1)

class FilmPlan(FilmArtifact):
    owner = 'film-plan'
    schema_version: Literal['film-plan-v1'] = 'film-plan-v1'
    source_ref: VersionRef
    canon_ref: ArtifactReference
    direction_ref: ArtifactReference
    unit_version_refs: tuple[tuple[VersionRef, ...], ...] = Field(max_length=12)
    graph: RoutePlan
    languages: LanguageMetadata

class FilmShotBinding(RuntimeContract):
    scene_id: Identifier
    shot_id: Identifier
    shot_ref: VersionRef
    package_ref: ArtifactReference
    candidate_ref: ArtifactReference
    media: MediaIdentity
    duration_ms: int = Field(gt=0)
    transition: Literal['cut'] = 'cut'

class FinalFilmCandidate(FilmArtifact):
    owner = 'final-film-candidate'
    schema_version: Literal['final-film-candidate-v1'] = 'final-film-candidate-v1'
    plan_ref: ArtifactReference
    shots: tuple[FilmShotBinding, ...] = Field(min_length=1, max_length=12)
    media: MediaIdentity
    canonical_media_ref: ArtifactReference | None = None
    subtitle_ref: ArtifactReference | None = None
    profile: DeliveryProfile
    duration_ms: int = Field(gt=0)

class FinalTechnicalQA(FilmArtifact):
    owner = 'final-technical-qa'
    schema_version: Literal['final-technical-qa-v1'] = 'final-technical-qa-v1'
    candidate_ref: ArtifactReference
    media_hash: str
    outcome: Literal['PASS', 'FAIL']
    checks: tuple[str, ...] = Field(max_length=16)
    failures: tuple[str, ...] = Field(default=(), max_length=16)

class FinalCreativeReview(FilmArtifact):
    owner = 'final-creative-review'
    schema_version: Literal['final-creative-review-v1'] = 'final-creative-review-v1'
    candidate_ref: ArtifactReference
    media_hash: str
    reviewer: Identifier
    qualification: Literal['OFFLINE_FIXTURE', 'HUMAN', 'QUALIFIED_REVIEWER']
    outcome: Literal['PASS', 'REVISE', 'CAPABILITY_ABSENT']
    observations: tuple[ReviewObservation, ...] = Field(default=(), max_length=16)
    affected_shots: tuple[Identifier, ...] = Field(default=(), max_length=12)
    @model_validator(mode='after')
    def revision(self) -> Self:
        if self.outcome == 'REVISE' and (not self.observations or not self.affected_shots):
            raise ValueError('Final revision needs exact owner and affected Shot scope')
        return self

class FinalDelivery(FilmArtifact):
    owner = 'final-delivery'
    schema_version: Literal['final-delivery-v1'] = 'final-delivery-v1'
    candidate_ref: ArtifactReference
    media: MediaIdentity
    canonical_media_ref: ArtifactReference | None = None
    subtitle_ref: ArtifactReference | None = None
    technical_ref: ArtifactReference
    creative_ref: ArtifactReference
    acceptance_ref: ArtifactReference
    source_ref: VersionRef
    rights_refs: tuple[ArtifactReference, ...] = Field(min_length=1, max_length=8)
    profile: DeliveryProfile

class FilmRevisionFeedback(FilmArtifact):
    owner = 'film-revision-feedback'
    schema_version: Literal['film-revision-feedback-v1'] = 'film-revision-feedback-v1'
    candidate_ref: ArtifactReference
    decision_or_review_ref: ArtifactReference
    requests: tuple[RevisionRequest, ...] = Field(min_length=1, max_length=12)

class FilmMediaBatch(FilmArtifact):
    """An authorized replacement production, retaining the preceding execution view."""
    owner = 'film-media-batch'
    schema_version: Literal['film-media-batch-v1'] = 'film-media-batch-v1'
    batch_id: Identifier
    authorization_ref: ArtifactReference
    opening_run_id: Identifier
    goal_hash: Identifier
    allow_unverified_audio: bool = False
    previous_checkpoint: FilmCheckpoint

FILM_TYPES: dict[str, type[FilmArtifact]] = {c.owner:c for c in (FilmPlan, FinalFilmCandidate, FinalTechnicalQA, FinalCreativeReview, FinalDelivery, FilmRevisionFeedback, FilmMediaBatch)}
