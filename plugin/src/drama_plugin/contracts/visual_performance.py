from __future__ import annotations

from typing import Annotated, Literal, Any

from pydantic import Field, StringConstraints, model_validator, model_serializer, SerializerFunctionWrapHandler

from drama_plugin.contracts.base import ContractModel


NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Fingerprint = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonNegativeMs = Annotated[int, Field(ge=0)]
PositiveMs = Annotated[int, Field(gt=0)]
TimeWindowMs = tuple[NonNegativeMs, NonNegativeMs]
ObservedLevel = Literal["LOW", "MEDIUM", "HIGH", "UNKNOWN"]


class DialoguePerformancePhase(ContractModel):
    """Nested visual-brief value, not a timeline or independently stored contract."""

    order: Annotated[int, Field(strict=True, gt=0)]
    active_speaker: NonBlankText | None
    listener: NonBlankText
    dramatic_action: NonBlankText
    visible_performance_focus: NonBlankText
    transition_purpose: NonBlankText
    relative_timing_range: tuple[Annotated[float, Field(ge=0, le=1)], Annotated[float, Field(ge=0, le=1)]]

    @model_validator(mode="after")
    def validate_phase(self) -> "DialoguePerformancePhase":
        if self.active_speaker == self.listener:
            raise ValueError("ACTIVE_SPEAKER_CANNOT_BE_LISTENER")
        if self.relative_timing_range[0] >= self.relative_timing_range[1]:
            raise ValueError("INVALID_RELATIVE_PHASE_RANGE")
        return self


class VisualPerformanceBrief(ContractModel):
    """Provider-neutral visible performance direction projected from one DPD line."""

    schema_version: Literal["visual-performance-brief-v1"] = (
        "visual-performance-brief-v1"
    )
    dpd_fingerprint: Fingerprint
    scene_id: NonBlankText
    shot_id: NonBlankText
    shot_fingerprint: Fingerprint
    primary_character_key: NonBlankText
    character_visual_identity_fingerprint: Fingerprint
    scene_visual_identity_fingerprint: Fingerprint
    body_activity: NonBlankText
    head_behavior: NonBlankText
    gaze_behavior: NonBlankText
    facial_tension: NonBlankText
    gesture_policy: NonBlankText
    interaction_orientation: NonBlankText
    pre_speech_behavior: NonBlankText
    visible_control: NonBlankText
    performance_boundaries: tuple[NonBlankText, ...] = ()
    execution_timing_fingerprint: Fingerprint | None = None
    dialogue_timing_plan_fingerprint: Fingerprint | None = None
    dialogue_source_fingerprint: Fingerprint | None = None
    dialogue_performance_phases: tuple[DialoguePerformancePhase, ...] = ()
    fingerprint: Fingerprint

    @model_serializer(mode="wrap")
    def serialize_material(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        if self.execution_timing_fingerprint is None:
            result.pop("executionTimingFingerprint", None)
            result.pop("execution_timing_fingerprint", None)
        return result

    @model_validator(mode="after")
    def validate_dialogue_phases(self) -> "VisualPerformanceBrief":
        phases = self.dialogue_performance_phases
        if bool(phases) != bool(self.dialogue_timing_plan_fingerprint and self.dialogue_source_fingerprint):
            raise ValueError("DIALOGUE_PHASES_REQUIRE_SOURCE_LINEAGE")
        if not phases and (self.dialogue_timing_plan_fingerprint or self.dialogue_source_fingerprint):
            raise ValueError("DIALOGUE_PHASES_REQUIRED")
        if phases:
            if [p.order for p in phases] != list(range(1, len(phases) + 1)):
                raise ValueError("DIALOGUE_PHASE_ORDER_REQUIRED")
            if phases[0].relative_timing_range[0] != 0 or phases[-1].relative_timing_range[1] != 1:
                raise ValueError("DIALOGUE_PHASE_COVERAGE_REQUIRED")
            if any(a.relative_timing_range[1] != b.relative_timing_range[0] for a, b in zip(phases, phases[1:])):
                raise ValueError("DIALOGUE_PHASE_GAP_OR_OVERLAP")
        return self


class RealizedPerformanceSnapshot(ContractModel):
    """Accepted, observable facts from an existing video; never intended psychology."""

    schema_version: Literal["realized-performance-snapshot-v1"] = (
        "realized-performance-snapshot-v1"
    )
    observed_speaker_key: NonBlankText | None = None
    video_media_id: NonBlankText
    video_content_hash: Fingerprint
    shot_id: NonBlankText
    video_duration_ms: PositiveMs
    shot_scale: NonBlankText
    speaker_screen_presence: NonBlankText
    speaker_orientation: NonBlankText
    gaze_direction: NonBlankText
    head_motion: NonBlankText
    body_motion: NonBlankText
    visible_activation: ObservedLevel
    facial_tension: ObservedLevel
    expression_change: Literal["PRESENT", "ABSENT", "UNKNOWN"]
    gesture_activity: NonBlankText
    interaction_distance: NonBlankText
    pre_speech_action: NonBlankText
    mouth_activity: Literal["PRESENT", "ABSENT", "UNKNOWN"]
    post_speech_action: NonBlankText
    speaker_visible_start_ms: NonNegativeMs | None = None
    pre_speech_motion_window_ms: TimeWindowMs | None = None
    mouth_activity_windows_ms: tuple[TimeWindowMs, ...] = ()
    major_head_motion_windows_ms: tuple[TimeWindowMs, ...] = ()
    major_gesture_windows_ms: tuple[TimeWindowMs, ...] = ()
    visible_pause_windows_ms: tuple[TimeWindowMs, ...] = ()
    post_speech_hold_ms: NonNegativeMs | None = None
    observation_method: Literal["CONTROLLED_FRAME_SAMPLING"] = (
        "CONTROLLED_FRAME_SAMPLING"
    )
    fingerprint: Fingerprint

    @model_validator(mode="after")
    def validate_observed_timing(self) -> "RealizedPerformanceSnapshot":
        if (
            self.speaker_visible_start_ms is not None
            and self.speaker_visible_start_ms > self.video_duration_ms
        ):
            raise ValueError("speaker visible start is outside video duration")
        if (
            self.post_speech_hold_ms is not None
            and self.post_speech_hold_ms > self.video_duration_ms
        ):
            raise ValueError("post-speech hold exceeds video duration")

        windows: tuple[TimeWindowMs, ...] = (
            (() if self.pre_speech_motion_window_ms is None else (self.pre_speech_motion_window_ms,))
            + self.mouth_activity_windows_ms
            + self.major_head_motion_windows_ms
            + self.major_gesture_windows_ms
            + self.visible_pause_windows_ms
        )
        for start_ms, end_ms in windows:
            if end_ms < start_ms:
                raise ValueError("observed activity window ends before it starts")
            if end_ms > self.video_duration_ms:
                raise ValueError("observed activity window is outside video duration")
        if self.mouth_activity == "PRESENT" and not self.mouth_activity_windows_ms:
            raise ValueError("present mouth activity requires at least one observed window")
        if self.mouth_activity != "PRESENT" and self.mouth_activity_windows_ms:
            raise ValueError("mouth activity windows require mouthActivity=PRESENT")
        return self
