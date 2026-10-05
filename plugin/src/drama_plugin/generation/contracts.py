"""Bounded execution contracts; audio references exact dialogue, never owns its text."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, ClassVar, Literal, Self

from pydantic import Field, StrictInt, StringConstraints, ValidationInfo, model_validator

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.creative_asset import Hash
from drama_plugin.production.contracts import DomainReference, SourceDomain, SourceReference
from drama_plugin.runtime.contracts import ArtifactReference, Identifier, RuntimeContract, RuntimeScope
from drama_plugin.runtime.contracts import ExtendedRuntimeContract, RecoveryClass
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.contracts import VersionRef

Text = Annotated[str, StringConstraints(min_length=1, max_length=3000)]
_SEAL_CONTEXT = object()


class DerivedArtifact(ExtendedRuntimeContract):
    creative_authority: ClassVar[bool] = False
    owner: ClassVar[str]
    source_package_ref: ArtifactReference
    fingerprint: Hash

    @classmethod
    def seal(cls, **values: object) -> Self:
        # Hash the validated content, including defaults; no clock/random/host data.
        candidate = cls.model_validate({**values, "fingerprint": "0" * 64}, context=_SEAL_CONTEXT)
        content = candidate.model_dump(mode="json", by_alias=True, exclude={"fingerprint"})
        return cls.model_validate({**content, "fingerprint": sha256_canonical(content)})

    @model_validator(mode="after")
    def content_hash(self, info: ValidationInfo) -> Self:
        if self.source_package_ref.owner != "production-package":
            raise ValueError("Execution artifacts require ProductionPackageRef")
        if info.context is _SEAL_CONTEXT:
            return self
        content = self.model_dump(mode="json", by_alias=True, exclude={"fingerprint"})
        if self.fingerprint != sha256_canonical(content):
            raise ValueError("Derived artifact fingerprint mismatch")
        return self

    def artifact_reference(self) -> ArtifactReference:
        return ArtifactReference(owner=self.owner, artifact_ref=self.owner + ":" + self.fingerprint, version=1)


class OperationSelection(RuntimeContract):
    """A bounded production selection, never a new creative version."""
    beat_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=16)
    action_refs: tuple[SourceReference, ...] = Field(min_length=1, max_length=16)
    spoken_ids: tuple[Identifier, ...] = Field(default=(), max_length=16)
    start_ref: SourceReference
    end_ref: SourceReference
    fact_refs: tuple[DomainReference, ...] = Field(min_length=1, max_length=128)
    reference_disposition: tuple[tuple[Identifier, Literal["INPUT", "OUT_OF_UNIT", "TECHNICAL_RISK_ACCEPTED", "OPTIONAL_OMITTED"]], ...] = Field(max_length=16)
    scope_decision_ref: ArtifactReference | None = None

    def terms_hash(self, package_ref: ArtifactReference) -> str:
        return sha256_canonical([package_ref.model_dump(mode="json",by_alias=True), self.model_dump(mode="json", by_alias=True, exclude={"scope_decision_ref"})])


class ExecutionProfile(RuntimeContract):
    provider: Identifier
    model: Identifier
    vendor_model_id: Identifier
    mode: Literal["text_to_video", "reference", "image_to_video", "first_last_frame"]
    requested_duration_ms: Annotated[StrictInt, Field(gt=0, le=3_600_000)]
    resolution: Literal["480p", "720p", "1080p"]
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "9:21", "adaptive"]
    native_audio: bool
    catalog_fingerprint: Hash
    policy_fingerprint: Hash
    paid_references: Literal[0] = 0
    paid_retries: Literal[0] = 0
    max_paid_operations: Literal[1] = 1


class OwnerBindings(RuntimeContract):
    adopted_refs: tuple[VersionRef, ...] = Field(min_length=5, max_length=32)
    dpd_pin: SourcePin
    performance_scope_pin: SourcePin
    # A silent Shot has BeatDPD coverage and no invented LineDPD.
    snapshot_pins: tuple[SourcePin, ...] = Field(default=(), max_length=16)
    rights_pin: SourcePin
    rights_request_ref: ArtifactReference
    rights_decision_ref: ArtifactReference
    adoption_decision_ref: ArtifactReference


class ContinuationInput(ExtendedRuntimeContract):
    """Physical predecessor and consumed context; never an approved screenplay rewrite."""
    predecessor_media_ref: ArtifactReference
    frame_ref: ArtifactReference
    global_reference_ref: SourceReference
    context_fact_refs: tuple[DomainReference, ...] = Field(default=(), max_length=128)
    output_mode: Literal["NEW_SEGMENT"] = "NEW_SEGMENT"
    extension_fields = ('allow_unverified_audio',)
    allow_unverified_audio: Literal[True] | None = None


class GenerationTask(ExtendedRuntimeContract):
    extension_fields = ("unit", "profile", "owners", "execution_reference_refs", "continuation", "return_last_frame")
    kind: Literal["VIDEO"] = "VIDEO"
    target_model: Identifier = "seedance-2-standard"
    input_mode: Literal["text_to_video", "reference", "image_to_video", "first_last_frame"] = "text_to_video"
    native_audio: Literal["OPTIONAL", "REQUIRED", "DISABLED"] = "OPTIONAL"
    tts_required: bool = False
    unit: OperationSelection | None = None
    profile: ExecutionProfile | None = None
    owners: OwnerBindings | None = None
    execution_reference_refs: tuple[SourceReference, ...] | None = Field(default=None, min_length=1, max_length=16)
    continuation: ContinuationInput | None = None
    return_last_frame: Literal[True] | None = None

    @model_validator(mode="after")
    def operation_boundary(self) -> Self:
        if self.continuation and (not self.unit or self.input_mode != "image_to_video"
                or self.return_last_frame is not True or len(self.execution_reference_refs or ()) != 1):
            raise ValueError("EXACT_CONTINUATION_FIRST_FRAME_REQUIRED")
        if any((self.unit, self.profile, self.owners)) and not all((self.unit, self.profile, self.owners)):
            raise ValueError("Operation selection/profile/owner refs must be fixed together")
        if self.profile and (self.target_model != self.profile.model or self.input_mode != self.profile.mode
                or self.native_audio == "DISABLED" and self.profile.native_audio
                or self.native_audio == "REQUIRED" and not self.profile.native_audio):
            raise ValueError("Task/profile conflict")
        if self.profile and self.unit and self.unit.spoken_ids and not self.profile.native_audio:
            raise ValueError("REQUEST_UNSUPPORTED_REQUIRED_SPEECH")
        return self

    @property
    def resolved_native_audio_policy(self) -> Literal["REQUIRED", "DISABLED", "OPTIONAL"]:
        if self.profile is not None:
            return "REQUIRED" if self.profile.native_audio else "DISABLED"
        return self.native_audio


class Obligation(str, Enum):
    EXECUTION_REQUIRED = "EXECUTION_REQUIRED"
    QUALITY_SUPPORTING = "QUALITY_SUPPORTING"


class ExecutableFact(RuntimeContract):
    fact_id: Identifier
    domain: SourceDomain
    slot: Identifier
    text: Text
    source_ref: SourceReference
    obligation: Obligation
    subject_id: Identifier | None = None


class PromptIR(DerivedArtifact):
    owner = "prompt-ir"
    schema_version: Literal["target-prompt-ir-v1"] = "target-prompt-ir-v1"
    scope: RuntimeScope
    duration_ms: Annotated[StrictInt, Field(gt=0, le=3_600_000)]
    facts: tuple[ExecutableFact, ...] = Field(min_length=1, max_length=128)
    execution_reference_refs: tuple[SourceReference, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def unique_facts(self) -> Self:
        if self.scope.scene_id is None or self.scope.shot_id is None:
            raise ValueError("PromptIR must describe one Shot")
        if len({f.fact_id for f in self.facts}) != len(self.facts):
            raise ValueError("Duplicate execution obligation")
        if self.source_package_ref.owner != "production-package":
            raise ValueError("PromptIR requires ProductionPackageRef")
        return self


class CoverageStatus(str, Enum):
    TEXT_COVERED = "TEXT_COVERED"
    REFERENCE_COVERED = "REFERENCE_COVERED"
    INTERNAL_ONLY = "INTERNAL_ONLY"
    OPTIONAL_OMITTED = "OPTIONAL_OMITTED"
    UNRESOLVED = "UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    OUT_OF_UNIT = "OUT_OF_UNIT"


class CoverageEntry(RuntimeContract):
    fact_id: Identifier
    domain: SourceDomain
    source_ref: SourceReference
    obligation: Obligation
    status: CoverageStatus
    span: tuple[Annotated[StrictInt, Field(ge=0)], Annotated[StrictInt, Field(ge=0)]] | None = None
    input_ref: ArtifactReference | None = None

    @model_validator(mode="after")
    def coverage_evidence(self) -> Self:
        if self.span is not None and self.span[0] >= self.span[1]:
            raise ValueError("Coverage span must be positive")
        if self.status == CoverageStatus.TEXT_COVERED and self.span is None:
            raise ValueError("Text coverage requires its final Prompt span")
        if self.status == CoverageStatus.REFERENCE_COVERED and self.input_ref is None:
            raise ValueError("Reference coverage requires an executable input reference")
        if self.status not in {CoverageStatus.TEXT_COVERED, CoverageStatus.REFERENCE_COVERED} and self.span is not None:
            raise ValueError("Omitted/internal obligations cannot claim final text coverage")
        return self


class PromptCoverage(DerivedArtifact):
    owner = "prompt-coverage"
    entries: tuple[CoverageEntry, ...] = Field(max_length=192)


class FinalPromptArtifact(DerivedArtifact):
    extension_fields = ("task_fingerprint",)
    owner = "final-prompt"
    task_fingerprint: Hash | None = None
    task: GenerationTask
    model_family: Identifier
    generator_policy_fingerprint: Hash
    prompt_text: Annotated[str, StringConstraints(min_length=1, max_length=20000)]
    prompt_ir_fingerprint: Hash
    coverage_ref: ArtifactReference
    execution_reference_refs: tuple[SourceReference, ...] = Field(default=(), max_length=16)

    def matches_task(self, task: GenerationTask) -> bool:
        if self.task_fingerprint is None:
            return self.task == task  # Immutable historical envelopes remain readable.
        return self.task_fingerprint == sha256_canonical(task) and self.task == GenerationTask.model_validate(
            task.model_dump(exclude={"unit", "profile", "owners", "continuation"}))

    @model_validator(mode="after")
    def coverage_owner(self) -> Self:
        if self.coverage_ref.owner != "prompt-coverage":
            raise ValueError("FinalPrompt requires the Target coverage reference")
        return self


class SpeechLayer(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    BACKGROUND = "BACKGROUND"


class Intelligibility(str, Enum):
    MUST_UNDERSTAND = "MUST_UNDERSTAND"
    BRIEFLY_CLEAR = "BRIEFLY_CLEAR"
    TEXTURE = "TEXTURE"


class TemporalRelation(str, Enum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    OVERLAP = "OVERLAP"
    INTERRUPT = "INTERRUPT"
    CONTINUE_UNDER = "CONTINUE_UNDER"
    FADE_BEHIND = "FADE_BEHIND"


class SpeechEvent(RuntimeContract):
    event_id: Identifier
    source_ref: SourceReference
    spoken_content_id: Identifier | None = None
    speaker_ref: ArtifactReference | None = None
    layer: SpeechLayer
    intelligibility: Intelligibility
    mix_priority: Annotated[StrictInt, Field(ge=0, le=3)]
    execution_ref: SourceReference
    language: Identifier | None = None
    language_ref: SourceReference | None = None
    delivery_refs: tuple[SourceReference, ...] = Field(default=(), max_length=8)
    window_ms: tuple[Annotated[StrictInt, Field(ge=0)], Annotated[StrictInt, Field(gt=0)]] | None = None

    @model_validator(mode="after")
    def exact_or_texture(self) -> Self:
        if (self.language is None) != (self.language_ref is None):
            raise ValueError("Speech language must retain its declared source")
        if self.spoken_content_id is not None:
            if self.source_ref.owner != "scene" or self.speaker_ref is None:
                raise ValueError("Exact speech requires Scene dialogue and speaker references")
        elif self.layer != SpeechLayer.BACKGROUND or self.source_ref.owner != "professional":
            raise ValueError("Nonverbatim vocals require an authored background texture")
        if self.window_ms and self.window_ms[0] >= self.window_ms[1]:
            raise ValueError("Speech window must be positive")
        return self


class SpeechRelation(RuntimeContract):
    event_id: Identifier
    target_event_id: Identifier
    relation: TemporalRelation
    source_ref: SourceReference
    # Interrupting the mix does not silently cut words. Truncation needs its Canon version.
    interruption_ref: SourceReference | None = None
    ends_target_speech: bool = False

    @model_validator(mode="after")
    def authorized_interruption(self) -> Self:
        if self.event_id == self.target_event_id:
            raise ValueError("Speech relation cannot target itself")
        if self.ends_target_speech and (self.relation != TemporalRelation.INTERRUPT or
                                       self.interruption_ref is None or self.interruption_ref.owner != "scene"):
            raise ValueError("Cutting exact speech requires an approved canonical interruption reference")
        return self


class AudioExecutionPlan(DerivedArtifact):
    owner = "audio-plan"
    schema_version: Literal["audio-execution-plan-v1"] = "audio-execution-plan-v1"
    scope: RuntimeScope
    duration_ms: Annotated[StrictInt, Field(gt=0, le=3_600_000)]
    speech_events: tuple[SpeechEvent, ...] = Field(default=(), max_length=64)
    relations: tuple[SpeechRelation, ...] = Field(default=(), max_length=128)
    ambience_refs: tuple[SourceReference, ...] = Field(default=(), max_length=16)
    foley_refs: tuple[SourceReference, ...] = Field(default=(), max_length=16)
    music_refs: tuple[SourceReference, ...] = Field(default=(), max_length=16)
    silence_refs: tuple[SourceReference, ...] = Field(default=(), max_length=16)
    mix_intent_refs: tuple[SourceReference, ...] = Field(default=(), max_length=16)
    native_audio_policy: Literal["OPTIONAL", "REQUIRED", "DISABLED"]
    source_roles: tuple[Literal["NATIVE_VIDEO_AUDIO", "TTS", "AMBIENCE", "FOLEY", "MUSIC"], ...]
    native_audio_is_final_mix: Literal[False] = False

    @model_validator(mode="after")
    def graph(self) -> Self:
        if self.scope.scene_id is None or self.scope.shot_id is None:
            raise ValueError("AudioExecutionPlan must describe one Shot")
        events = {event.event_id: event for event in self.speech_events}
        if len(events) != len(self.speech_events):
            raise ValueError("Duplicate speech event identity")
        if any(e.spoken_content_id and e.source_ref.artifact_ref != self.scope.scene_id for e in events.values()):
            raise ValueError("Exact speech belongs to another Scene")
        edges: set[tuple[str, str, TemporalRelation]] = set()
        precedes: dict[str, set[str]] = {key: set() for key in events}
        for relation in self.relations:
            relation_key = (relation.event_id, relation.target_event_id, relation.relation)
            if relation_key in edges or relation.event_id not in events or relation.target_event_id not in events:
                raise ValueError("Duplicate or dangling speech relation")
            edges.add(relation_key)
            a, b = events[relation.event_id].window_ms, events[relation.target_event_id].window_ms
            if relation.relation in {TemporalRelation.BEFORE, TemporalRelation.AFTER}:
                first, second = (relation.event_id, relation.target_event_id) if relation.relation == TemporalRelation.BEFORE else (relation.target_event_id, relation.event_id)
                precedes[first].add(second)
                if a and b and ((relation.relation == TemporalRelation.BEFORE and a[1] > b[0]) or
                                (relation.relation == TemporalRelation.AFTER and b[1] > a[0])):
                    raise ValueError("Speech windows contradict order")
            elif a and b and max(a[0], b[0]) >= min(a[1], b[1]):
                raise ValueError("Concurrent speech needs a shared time interval")
            if relation.relation == TemporalRelation.INTERRUPT and a and b and not b[0] < a[0] < b[1]:
                raise ValueError("Interrupting speech must enter while the target is speaking")
            if relation.ends_target_speech and relation.interruption_ref != events[relation.target_event_id].source_ref:
                raise ValueError("Interruption must bind the selected canonical target version")
        visited: set[str] = set()
        def visit(key: str, trail: set[str]) -> None:
            if key in trail:
                raise ValueError("Cyclic speech precedence")
            if key in visited:
                return
            for next_key in precedes[key]:
                visit(next_key, trail | {key})
            visited.add(key)
        for key in events:
            visit(key, set())
        def before(first: str, second: str) -> bool:
            pending, seen = [first], set()
            while pending:
                key = pending.pop()
                if key == second:
                    return True
                if key not in seen:
                    seen.add(key)
                    pending.extend(precedes[key])
            return False
        for relation in self.relations:
            if relation.relation not in {TemporalRelation.BEFORE, TemporalRelation.AFTER} and (
                before(relation.event_id, relation.target_event_id) or before(relation.target_event_id, relation.event_id)):
                raise ValueError("Concurrent speech contradicts authored precedence")
        if any(event.window_ms and event.window_ms[1] > self.duration_ms for event in events.values()):
            raise ValueError("Speech window exceeds Shot")
        return self


class ExecutionDiagnostic(ExtendedRuntimeContract):
    extension_fields = ("recovery_class", "external_ref")
    code: Identifier
    owner: Identifier
    domain: SourceDomain
    source_ref: SourceReference | None = None
    required: bool = False
    recovery_class: RecoveryClass | None = None
    external_ref: ArtifactReference | None = None


class GenerationPreparation(DerivedArtifact):
    owner = "generation-preparation"
    task: GenerationTask
    final_prompt_ref: ArtifactReference
    audio_plan_ref: ArtifactReference
    readiness: Literal["READY_FOR_PROVIDER"] = "READY_FOR_PROVIDER"
    provider_submission_allowed: Literal[False] = False

    @model_validator(mode="after")
    def execution_owners(self) -> Self:
        if self.final_prompt_ref.owner != "final-prompt" or self.audio_plan_ref.owner != "audio-plan":
            raise ValueError("Preparation requires authoritative FinalPrompt and AudioPlan references")
        return self


class GenerationInput(RuntimeContract):
    task: GenerationTask = GenerationTask()
    cached_preparation_ref: ArtifactReference | None = None
