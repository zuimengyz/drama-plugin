from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from drama_plugin.contracts.base import ContractModel, dump_contract, sha256_canonical
from drama_plugin.contracts.dialogue_timing import (
    DialogueTimingPlan, Fingerprint, NonBlank, NonNegativeMs, PositiveMs,
)


CandidateCause = Literal[
    "MISSING_REALIZED_TURN_AUDIO", "STALE_REALIZED_TURN_AUDIO",
    "DURATION_ESTIMATE_DRIFT", "SHOT_DURATION", "SHOT_SEGMENTATION_REVIEW",
    "TIMING_OBSERVABILITY",
]
AudioDiagnostic = Literal[
    "NO_CURRENT_FINAL_AUDIO", "CURRENT_REQUEST_MISSING", "AUDIO_LINEAGE_MISMATCH",
    "AUDIO_REVIEW_INVALID", "AUDIO_TECHNICAL_REVIEW_FAILED", "AUDIO_REVIEW_PENDING",
    "AMBIGUOUS_CURRENT_AUDIO",
]


class ReconciledDialogueTurn(ContractModel):
    """Nested evidence/placement detail, never a separate persisted entity."""

    spoken_content_id: NonBlank
    speaker_key: NonBlank
    sequence: Annotated[int, Field(strict=True, gt=0)]
    audio_status: Literal["PRESENT", "MISSING", "STALE"]
    audio_media_id: NonBlank | None
    audio_content_hash: Fingerprint | None
    audio_review_status: Literal["PASS", "PENDING"] | None
    actual_duration_ms: PositiveMs | None
    duration_authority: Literal["ACTUAL_AUDIO", "PLANNING_ESTIMATE"]
    duration_delta_ms: Annotated[int, Field(strict=True)] | None
    audio_evidence_fingerprint: Fingerprint
    rejected_audio_ids: tuple[NonBlank, ...]
    audio_diagnostics: tuple[AudioDiagnostic, ...]
    proposed_start_ms: NonNegativeMs | None
    proposed_end_ms: PositiveMs | None

    @model_validator(mode="after")
    def validate_actual_evidence(self) -> ReconciledDialogueTurn:
        actual = (self.audio_media_id, self.audio_content_hash, self.audio_review_status,
                  self.actual_duration_ms, self.duration_delta_ms)
        present = self.audio_status == "PRESENT"
        if (present and any(v is None for v in actual)) or (
            not present and any(v is not None for v in actual)
        ):
            raise ValueError("ACTUAL_AUDIO_AUTHORITY_MISMATCH")
        if self.duration_authority != ("ACTUAL_AUDIO" if present else "PLANNING_ESTIMATE"):
            raise ValueError("DURATION_AUTHORITY_MISMATCH")
        if (self.proposed_start_ms is None) != (self.proposed_end_ms is None):
            raise ValueError("INCOMPLETE_PROPOSED_WINDOW")
        if self.proposed_start_ms is not None:
            assert self.proposed_end_ms is not None
            if self.proposed_end_ms <= self.proposed_start_ms:
                raise ValueError("INVALID_PROPOSED_WINDOW")
        return self


class DialogueTimingReconciliation(ContractModel):
    """Phase A feasibility and recommendation, with an immutable source-plan copy.

    Embedding the existing plan allows standalone validation of all coverage,
    protected holds and deltas without defining another planning policy/schema.
    Current-source replay is additionally required before reusing this artifact.
    """

    schema_version: Literal["dialogue-timing-reconciliation-v1"] = "dialogue-timing-reconciliation-v1"
    source_plan: DialogueTimingPlan
    source_dialogue_timing_plan_fingerprint: Fingerprint
    scene_id: NonBlank
    shot_id: NonBlank
    video_media_id: NonBlank
    video_content_hash: Fingerprint
    video_duration_ms: PositiveMs
    realized_performance_fingerprint: Fingerprint
    observed_speaker_key: NonBlank
    mouth_activity: Literal["PRESENT", "ABSENT", "UNKNOWN"]
    visible_action_windows_ms: dict[
        Literal["HEAD_MOTION", "GESTURE", "VISIBLE_PAUSE"],
        tuple[tuple[NonNegativeMs, NonNegativeMs], ...],
    ]
    reconciliation_policy: Literal["VIDEO_DELTA_THEN_POST_SURPLUS_V1", "PARTICIPATION_CONSTRAINED_V1"]
    current_inputs_fingerprint: Fingerprint
    turns: Annotated[tuple[ReconciledDialogueTurn, ...], Field(min_length=1)]
    full_dialogue_coverage: Literal["COMPLETE", "INCOMPLETE"]
    evidence_mode: Literal["REALIZED", "HYBRID", "PLANNING_ONLY"]
    physical_feasibility: Literal["FEASIBLE", "CONFLICT", "EVIDENCE_LIMITED"]
    hybrid_feasibility: Literal["FEASIBLE", "CONFLICT", "NOT_NEEDED"]
    artistic_compatibility: Literal["SUPPORTED", "QUESTIONABLE", "CONFLICTING", "UNKNOWN"]
    recommended_placement_status: Literal["PROPOSED", "CONDITIONAL_HYBRID", "BLOCKED"]
    actual_video_delta_ms: Annotated[int, Field(strict=True)]
    flexible_post_slack_ms: NonNegativeMs
    consumed_video_delta_ms: NonNegativeMs
    consumed_post_slack_ms: NonNegativeMs
    required_minimum_duration_ms: PositiveMs
    full_realized_required_minimum_ms: PositiveMs | None
    overflow_ms: NonNegativeMs
    slack_ms: NonNegativeMs
    proposed_post_hold_ms: PositiveMs | None
    candidate_causes: tuple[CandidateCause, ...]
    diagnostics: tuple[Literal[
        "TIMING_CONFLICT", "HYBRID_EVIDENCE_ONLY", "NO_ACTUAL_AUDIO",
        "REACTION_COMPRESSION_REQUIRED_TO_FIT", "VISIBLE_ACTION_WINDOW_REVIEW",
        "ARTISTIC_TIMING_REVIEW_REQUIRED", "ON_SCREEN_MOUTH_ACTIVITY_ABSENT",
        "VISIBLE_COVERAGE_CONFLICT",
    ], ...]
    user_timing_review: Literal["REQUIRED", "NOT_READY"]
    fingerprint: Fingerprint

    @model_validator(mode="after")
    def validate_feasibility_before_placement(self) -> DialogueTimingReconciliation:
        plan = DialogueTimingPlan.model_validate(dump_contract(self.source_plan))
        if self.source_dialogue_timing_plan_fingerprint != plan.fingerprint:
            raise ValueError("SOURCE_PLAN_FINGERPRINT_MISMATCH")
        if self.scene_id != plan.scene_id or self.shot_id != plan.shot_id:
            raise ValueError("SOURCE_PLAN_IDENTITY_MISMATCH")
        if len(self.turns) != len(plan.turns):
            raise ValueError("FULL_SHOT_TURN_COVERAGE_REQUIRED")
        used: list[int] = []
        for actual, planned in zip(self.turns, plan.turns):
            if (actual.spoken_content_id, actual.speaker_key, actual.sequence) != (
                planned.spoken_content_id, planned.speaker_key, planned.sequence,
            ):
                raise ValueError("TURN_IDENTITY_OR_ORDER_MISMATCH")
            duration = actual.actual_duration_ms
            if duration is not None and actual.duration_delta_ms != duration - planned.planned_duration_ms:
                raise ValueError("DURATION_DELTA_MISMATCH")
            used.append(duration if duration is not None else planned.planned_duration_ms)
        count = sum(turn.audio_status == "PRESENT" for turn in self.turns)
        complete = count == len(self.turns)
        if self.full_dialogue_coverage != ("COMPLETE" if complete else "INCOMPLETE"):
            raise ValueError("FULL_REALIZED_COVERAGE_MISMATCH")
        mode = "REALIZED" if complete else "HYBRID" if count else "PLANNING_ONLY"
        if self.evidence_mode != mode:
            raise ValueError("HYBRID_EVIDENCE_MUST_BE_EXPLICIT")
        minimum = plan.pre_dialogue_hold_ms + sum(used) + sum(
            turn.transition_hold_ms for turn in plan.turns
        ) + plan.minimum_post_dialogue_hold_ms
        fits = minimum <= self.video_duration_ms
        feasibility = "FEASIBLE" if fits else "CONFLICT"
        if self.physical_feasibility != (feasibility if complete else "EVIDENCE_LIMITED"):
            raise ValueError("FULL_REALIZED_FEASIBILITY_REQUIRES_COMPLETE_EVIDENCE")
        if self.hybrid_feasibility != ("NOT_NEEDED" if complete else feasibility):
            raise ValueError("HYBRID_FEASIBILITY_MISMATCH")
        if (self.required_minimum_duration_ms != minimum
                or self.full_realized_required_minimum_ms != (minimum if complete else None)
                or self.overflow_ms != max(minimum - self.video_duration_ms, 0)
                or self.slack_ms != max(self.video_duration_ms - minimum, 0)):
            raise ValueError("PHYSICAL_BUDGET_MISMATCH")
        delta = self.video_duration_ms - plan.planned_duration_ms
        drift = sum(used) - sum(t.planned_duration_ms for t in plan.turns)
        flexible = plan.post_dialogue_hold_ms - plan.minimum_post_dialogue_hold_ms
        if (self.actual_video_delta_ms != delta or self.flexible_post_slack_ms != flexible
                or self.consumed_video_delta_ms != min(max(delta, 0), max(drift, 0))
                or self.consumed_post_slack_ms != min(flexible, max(drift - delta, 0))):
            raise ValueError("SLACK_REALLOCATION_MISMATCH")
        can_propose = fits and count > 0 and self.artistic_compatibility != "CONFLICTING"
        status = ("PROPOSED" if complete else "CONDITIONAL_HYBRID") if can_propose else "BLOCKED"
        if self.recommended_placement_status != status:
            raise ValueError("FEASIBILITY_GATE_BEFORE_PLACEMENT")
        cursor = plan.pre_dialogue_hold_ms
        for actual, planned, duration in zip(self.turns, plan.turns, used):
            cursor += planned.transition_hold_ms
            if can_propose:
                if self.reconciliation_policy == "PARTICIPATION_CONSTRAINED_V1":
                    if (actual.proposed_start_ms is None or actual.proposed_start_ms < cursor
                            or actual.proposed_end_ms != actual.proposed_start_ms + duration):
                        raise ValueError("PROTECTED_REACTION_OR_COMPLETE_AUDIO_VIOLATION")
                    cursor = actual.proposed_start_ms
                elif actual.proposed_start_ms != cursor or actual.proposed_end_ms != cursor + duration:
                    raise ValueError("PROTECTED_REACTION_OR_COMPLETE_AUDIO_VIOLATION")
            elif actual.proposed_start_ms is not None or actual.proposed_end_ms is not None:
                raise ValueError("BLOCKED_PLACEMENT_MUST_BE_NULL")
            cursor += duration
        if can_propose and self.video_duration_ms - cursor < plan.minimum_post_dialogue_hold_ms:
            raise ValueError("MINIMUM_POST_HOLD_VIOLATION")
        if self.proposed_post_hold_ms != (self.video_duration_ms - cursor if can_propose else None):
            raise ValueError("MINIMUM_POST_HOLD_VIOLATION")
        if self.user_timing_review != ("REQUIRED" if can_propose else "NOT_READY"):
            raise ValueError("USER_TIMING_REVIEW_REQUIRED")
        if self.reconciliation_policy == "VIDEO_DELTA_THEN_POST_SURPLUS_V1" and self.mouth_activity == "UNKNOWN" and self.artistic_compatibility == "SUPPORTED":
            raise ValueError("MOUTH_UNKNOWN_CANNOT_PROVE_ARTISTIC_SUPPORT")
        for windows in self.visible_action_windows_ms.values():
            if any(end < start or end > self.video_duration_ms for start, end in windows):
                raise ValueError("INVALID_VISIBLE_ACTION_WINDOW")
        if self.fingerprint != sha256_canonical(dump_contract(self, exclude={"fingerprint"})):
            raise ValueError("RECONCILIATION_FINGERPRINT_INVALID")
        return self
