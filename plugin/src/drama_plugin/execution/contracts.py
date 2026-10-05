"""Target execution evidence. No creative authorship, Canon adoption or final delivery."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Self

from pydantic import Field, StrictInt, model_validator

from drama_plugin.contracts.creative_asset import Hash
from drama_plugin.generation.contracts import DerivedArtifact, ExecutionProfile
from drama_plugin.runtime.contracts import ExtendedRuntimeContract
from drama_plugin.production.contracts import SourceReference
from drama_plugin.runtime.contracts import ArtifactReference, Identifier, RuntimeContract, RuntimeScope

Milliseconds = Annotated[StrictInt, Field(ge=0, le=3_600_000)]


class OperationState(str, Enum):
    RESERVED = "RESERVED"
    SUBMITTING = "SUBMITTING"
    RUNNING = "RUNNING"
    UNKNOWN = "UNKNOWN"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class Authorization(RuntimeContract):
    approval_ref: ArtifactReference
    authorized: bool
    budget_microunits: Annotated[StrictInt, Field(ge=0)]
    estimated_cost_microunits: Annotated[StrictInt, Field(ge=0)]
    execution_mode: Literal["OFFLINE_ONLY", "CONTROLLED_LIVE"] = "OFFLINE_ONLY"


class ExecutionArtifact(DerivedArtifact):
    scope: RuntimeScope
    run_id: Identifier

    @model_validator(mode="after")
    def shot_scope(self) -> Self:
        if not self.scope.scene_id or not self.scope.shot_id:
            raise ValueError("Target execution must bind an exact Shot")
        return self


class ExecutionOperation(ExecutionArtifact):
    owner = "execution-operation"
    preparation_ref: ArtifactReference
    final_prompt_ref: ArtifactReference
    audio_plan_ref: ArtifactReference
    reference_bindings: tuple[SourceReference, ...] = Field(default=(), max_length=16)
    model: Identifier
    route: Identifier
    authorization: Authorization

    @model_validator(mode="after")
    def owners(self) -> Self:
        for ref, owner in ((self.preparation_ref, "generation-preparation"),
                           (self.final_prompt_ref, "final-prompt"), (self.audio_plan_ref, "audio-plan")):
            if ref.owner != owner or ref.version != 1:
                raise ValueError("Operation requires exact approved execution refs")
        return self


class ProviderAttempt(ExecutionArtifact):
    extension_fields = ("previous_attempt_ref", "approval_ref")
    owner = "provider-attempt"
    operation_ref: ArtifactReference
    provider: Identifier
    request_fingerprint: Hash
    # An attempt is reserved before sending, so it is also the stable query key.
    client_identity: Hash
    ordinal: Annotated[StrictInt, Field(ge=1, le=2)] = 1
    previous_attempt_ref: ArtifactReference | None = None
    approval_ref: ArtifactReference | None = None

    @model_validator(mode="after")
    def supplemental_identity(self) -> Self:
        if (self.ordinal == 2) != (self.previous_attempt_ref is not None and self.approval_ref is not None):
            raise ValueError("Supplemental attempt requires prior attempt and fresh cost receipt")
        return self


class RequestReference(ExtendedRuntimeContract):
    extension_fields = ("kind",)
    binding_ref: SourceReference
    media_id: Identifier
    content_hash: Hash
    role: Literal["FIRST_FRAME", "LAST_FRAME", "REFERENCE"]
    kind: Literal["image", "video", "audio"] | None = None


class ProviderRequest(ExtendedRuntimeContract):
    extension_fields = ("profile", "return_last_frame")
    operation_ref: ArtifactReference | None = None
    model: Identifier
    input_mode: Literal["text_to_video", "reference", "image_to_video", "first_last_frame"]
    prompt_text: str = Field(min_length=1, max_length=20000)
    duration_ms: Annotated[StrictInt, Field(gt=0, le=3_600_000)]
    native_audio: Literal["OPTIONAL", "REQUIRED", "DISABLED"]
    references: tuple[RequestReference, ...] = Field(default=(), max_length=16)
    profile: ExecutionProfile | None = None
    return_last_frame: Literal[True] | None = None


class ProviderResult(RuntimeContract):
    result_id: Identifier
    kind: Literal["VIDEO", "AUDIO"] = "VIDEO"
    mime: Literal["video/mp4", "audio/wav", "audio/mp4"] = "video/mp4"
    # Retrieval information is receipt evidence, never a canonical media identity.
    locator: str = Field(min_length=1, max_length=2048)
    expected_hash: Hash | None = None


class ProviderReceipt(ExecutionArtifact):
    extension_fields = ("query_code", "http_status", "query_retryable", "usage", "last_frame_url")
    owner = "provider-receipt"
    operation_ref: ArtifactReference
    attempt_ref: ArtifactReference
    provider: Identifier
    client_identity: Hash
    request_fingerprint: Hash
    remote_identity: Identifier
    state: Literal["RUNNING", "SUCCEEDED", "FAILED"]
    result: ProviderResult | None = None
    failure_code: Identifier | None = None
    # Read/reconciliation diagnostics, never vendor text, headers or result URLs.
    query_code: Identifier | None = None
    http_status: Annotated[StrictInt, Field(ge=100, le=599)] | None = None
    query_retryable: bool | None = None
    usage: dict[str, int | float | str] | None = None
    last_frame_url: str | None = Field(default=None, min_length=1, max_length=2048)

    @model_validator(mode="after")
    def receipt_shape(self) -> Self:
        if (self.state == "SUCCEEDED") != (self.result is not None):
            raise ValueError("Successful receipt needs its exact provider result")
        if (self.state == "FAILED") != (self.failure_code is not None):
            raise ValueError("Only a definite provider failure has a failure code")
        return self


class MediaIdentity(RuntimeContract):
    media_id: Identifier
    content_hash: Hash
    kind: Literal["VIDEO", "AUDIO", "IMAGE"]
    mime: Literal["video/mp4", "audio/wav", "audio/mp4", "image/jpeg"]
    byte_count: Annotated[StrictInt, Field(gt=0)]

    @model_validator(mode="after")
    def stable_id(self) -> Self:
        if self.media_id != "media:sha256:" + self.content_hash:
            raise ValueError("Media identity must be content addressed")
        if not self.mime.startswith({"VIDEO":"video/", "AUDIO":"audio/", "IMAGE":"image/"}[self.kind]):
            raise ValueError("Media kind/MIME mismatch")
        return self


class MediaBinding(ExecutionArtifact):
    extension_fields = ("canonical_media_ref",)
    owner = "media-binding"
    operation_ref: ArtifactReference
    attempt_ref: ArtifactReference
    receipt_ref: ArtifactReference
    provider_result_id: Identifier
    media: MediaIdentity
    final_prompt_ref: ArtifactReference
    reference_bindings: tuple[SourceReference, ...] = Field(default=(), max_length=16)
    parent_media: tuple[MediaIdentity, ...] = Field(default=(), max_length=64)
    canonical_media_ref: ArtifactReference | None = None


class ContinuationFrame(ExecutionArtifact):
    """Provider-returned last JPEG, retained unchanged beneath its source operation."""
    owner = "continuation-frame"
    predecessor_media_ref: ArtifactReference
    receipt_ref: ArtifactReference
    media: MediaIdentity
    width: int = Field(gt=0)
    height: int = Field(gt=0)

    @model_validator(mode="after")
    def frame_shape(self) -> Self:
        if self.predecessor_media_ref.owner != "media-binding" or self.media.kind != "IMAGE":
            raise ValueError("PROVIDER_ENDPOINT_FRAME_REQUIRED")
        return self


class ProbeObservation(ExtendedRuntimeContract):
    extension_fields = ('video_duration_ms','audio_duration_ms')
    video_duration_ms: int | None = Field(default=None,gt=0)
    audio_duration_ms: int | None = Field(default=None,gt=0)
    container: Identifier
    duration_ms: Annotated[StrictInt, Field(gt=0, le=3_600_000)]
    width: Annotated[StrictInt, Field(gt=0)] | None = None
    height: Annotated[StrictInt, Field(gt=0)] | None = None
    video_codec: Identifier | None = None
    audio_codec: Identifier | None = None


class TechnicalMediaReview(ExecutionArtifact):
    extension_fields = ('supersedes_ref',)
    supersedes_ref: ArtifactReference | None = None
    owner = "technical-media-review"
    operation_ref: ArtifactReference
    attempt_ref: ArtifactReference
    media: MediaIdentity
    policy_version: Literal["technical-media-v1", "technical-media-stream-duration-v2"] = "technical-media-v1"
    outcome: Literal["PASS", "FAIL"]
    observation: ProbeObservation | None = None
    findings: tuple[Identifier, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def technical_evidence(self) -> Self:
        if self.outcome == "PASS" and (self.observation is None or self.findings):
            raise ValueError("Technical pass requires observations and no failures")
        if self.outcome == "FAIL" and not self.findings:
            raise ValueError("Technical failure requires a finding")
        return self


class ReviewObservation(ExtendedRuntimeContract):
    extension_fields = ('verified_spoken_ids',)
    code: Identifier
    owner: Identifier
    finding: str = Field(min_length=1, max_length=1000)
    required_revision: str | None = Field(default=None, min_length=1, max_length=1000)
    verified_spoken_ids: tuple[Identifier, ...] | None = Field(default=None, min_length=1, max_length=16)

    @model_validator(mode='after')
    def speech_observation(self) -> Self:
        if (self.verified_spoken_ids is not None) != (self.code == 'SPOKEN_CONTENT_COVERAGE_VERIFIED'):
            raise ValueError('Exact observed speech coverage requires its named observation')
        return self


class CreativeMediaReview(ExecutionArtifact):
    extension_fields = ("canonical_media_ref", "preparation_ref", "review_context_hash")
    owner = "creative-media-review"
    operation_ref: ArtifactReference
    attempt_ref: ArtifactReference
    media: MediaIdentity
    reviewer: Identifier
    policy_version: Identifier
    outcome: Literal["PASS", "REVISE", "CAPABILITY_ABSENT"]
    observations: tuple[ReviewObservation, ...] = Field(default=(), max_length=16)
    adoption_recommendation: Literal["CANDIDATE_ONLY", "REVISION_REQUIRED", "UNASSESSED"]
    canonical_media_ref: ArtifactReference | None = None
    preparation_ref: ArtifactReference | None = None
    review_context_hash: Hash | None = None

    @model_validator(mode="after")
    def revision_owner(self) -> Self:
        recommendation = {"PASS": "CANDIDATE_ONLY", "REVISE": "REVISION_REQUIRED",
                          "CAPABILITY_ABSENT": "UNASSESSED"}[self.outcome]
        if self.adoption_recommendation != recommendation:
            raise ValueError("Review recommendation disagrees with its observations")
        if self.outcome == "REVISE" and not any(o.required_revision for o in self.observations):
            raise ValueError("Revision needs an explicit finding, revision and owner")
        return self


class AudioPlacement(RuntimeContract):
    event_id: Identifier
    source_ref: SourceReference
    media: MediaIdentity
    start_ms: Milliseconds
    gain_db: float = Field(ge=-60, le=12, allow_inf_nan=False)
    fade_out_window_ms: tuple[Milliseconds, Milliseconds] | None = None

    @model_validator(mode="after")
    def fade_window(self) -> Self:
        if self.fade_out_window_ms is not None and not self.start_ms <= self.fade_out_window_ms[0] < self.fade_out_window_ms[1]:
            raise ValueError("Approved fade must be a positive placement window")
        return self


class FinishingRecipe(ExecutionArtifact):
    owner = "finishing-recipe"
    preparation_ref: ArtifactReference
    audio_plan_ref: ArtifactReference
    approval_ref: ArtifactReference
    native_policy: Literal["PRESERVE", "REPLACE", "MIX"]
    native_gain_db: float = Field(default=0, ge=-60, le=12, allow_inf_nan=False)
    placements: tuple[AudioPlacement, ...] = Field(default=(), max_length=64)
    # Nonverbatim beds bind the plan's exact authored references too.
    bed_refs: tuple[SourceReference, ...] = Field(default=(), max_length=48)
    bed_placements: tuple[AudioPlacement, ...] = Field(default=(), max_length=48)
    duration_tolerance_ms: Milliseconds = 100

    @model_validator(mode="after")
    def approved_recipe(self) -> Self:
        if self.preparation_ref.owner != "generation-preparation" or self.audio_plan_ref.owner != "audio-plan":
            raise ValueError("Recipe must pin preparation and AudioExecutionPlan")
        if len({p.event_id for p in self.placements}) != len(self.placements):
            raise ValueError("Duplicate speech placement")
        if self.native_policy == "PRESERVE" and (self.placements or self.bed_placements):
            raise ValueError("PRESERVE cannot also add external speech/beds")
        if len(self.bed_refs) != len(self.bed_placements):
            raise ValueError("Each bed needs its exact authored source")
        return self


class AudioTiming(RuntimeContract):
    event_id: Identifier
    source_ref: SourceReference
    start_ms: Milliseconds
    end_ms: Milliseconds
    layer: Literal["PRIMARY", "SECONDARY", "BACKGROUND"]
    spoken_content_id: Identifier | None = None


class AudioExecution(ExecutionArtifact):
    owner = "audio-execution"
    operation_ref: ArtifactReference
    attempt_ref: ArtifactReference
    audio_plan_ref: ArtifactReference
    recipe_ref: ArtifactReference
    media: MediaIdentity
    parent_media: tuple[MediaIdentity, ...] = Field(min_length=1, max_length=128)
    timings: tuple[AudioTiming, ...] = Field(default=(), max_length=64)
    subtitle_status: Literal["UNTIMED", "TIMED_PREPARATION"] = "UNTIMED"
    render_authorized: Literal[False] = False


class AVDerivative(ExecutionArtifact):
    owner = "av-derivative"
    operation_ref: ArtifactReference
    attempt_ref: ArtifactReference
    recipe_ref: ArtifactReference
    audio_execution_ref: ArtifactReference
    media: MediaIdentity
    parent_media: tuple[MediaIdentity, ...] = Field(min_length=2, max_length=2)


class ReviewedAVCandidate(ExecutionArtifact):
    owner = "reviewed-av-candidate"
    operation_ref: ArtifactReference
    attempt_ref: ArtifactReference
    video_binding_ref: ArtifactReference
    video_technical_ref: ArtifactReference
    video_creative_ref: ArtifactReference
    audio_execution_ref: ArtifactReference
    audio_technical_ref: ArtifactReference
    av_derivative_ref: ArtifactReference
    av_technical_ref: ArtifactReference
    av_creative_ref: ArtifactReference
    media: MediaIdentity
    readiness: Literal["REVIEWED_AV_CANDIDATE"] = "REVIEWED_AV_CANDIDATE"
    canon_adopted: Literal[False] = False
    final_delivery: Literal[False] = False


class ExecutionInput(ExtendedRuntimeContract):
    extension_fields = ("recipe_ref",)
    preparation_ref: ArtifactReference
    authorization: Authorization
    recipe_ref: ArtifactReference | None = None
    route: Identifier


class AttemptHistory(RuntimeContract):
    attempt_ref: ArtifactReference
    state: OperationState
    receipt_ref: ArtifactReference | None = None
    query_last_code: Identifier | None = None
    reserved_cost_microunits: Annotated[StrictInt, Field(gt=0)]


class OperationProgress(ExtendedRuntimeContract):
    extension_fields = ("attempt_history", "unknown_lookup_attempts", "unknown_lookup_last_code", 'video_technical_repair_ref')
    video_technical_repair_ref: ArtifactReference | None = None
    attempt_history: tuple[AttemptHistory, ...] | None = Field(default=None, max_length=1)
    unknown_lookup_attempts: Annotated[StrictInt, Field(ge=0, le=4)] | None = None
    unknown_lookup_last_code: Identifier | None = None
    video_ref: ArtifactReference | None = None
    video_technical_ref: ArtifactReference | None = None
    video_creative_ref: ArtifactReference | None = None
    audio_ref: ArtifactReference | None = None
    audio_technical_ref: ArtifactReference | None = None
    av_ref: ArtifactReference | None = None
    av_technical_ref: ArtifactReference | None = None
    av_creative_ref: ArtifactReference | None = None
    candidate_ref: ArtifactReference | None = None
    intake_attempts: Annotated[StrictInt, Field(ge=0, le=3)] = 0
    intake_media: MediaIdentity | None = None
    intake_last_code: Identifier | None = None
    query_attempts: Annotated[StrictInt, Field(ge=0, le=60)] = 0
    query_started_at_ms: Annotated[StrictInt, Field(ge=0)] | None = None
    query_last_code: Identifier | None = None
    media_last_code: Identifier | None = None

    @property
    def current_video_technical_ref(self) -> ArtifactReference | None:
        return self.video_technical_repair_ref or self.video_technical_ref


EXECUTION_TYPES: dict[str, type[ExecutionArtifact]] = {model.owner: model for model in (
    ExecutionOperation, ProviderAttempt, ProviderReceipt, MediaBinding, ContinuationFrame, TechnicalMediaReview,
    CreativeMediaReview, FinishingRecipe, AudioExecution, AVDerivative, ReviewedAVCandidate,
)}
