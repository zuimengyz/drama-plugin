from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from drama_plugin.contracts.base import ContractModel, dump_contract, sha256_canonical


NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Fingerprint = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
PositiveMs = Annotated[int, Field(strict=True, gt=0)]
NonNegativeMs = Annotated[int, Field(strict=True, ge=0)]
Transition = Literal[
    "OPENING", "IMMEDIATE_RESPONSE", "SHORT_REACTION", "DELIBERATE_REACTION"
]


class DialogueTurnTiming(ContractModel):
    """One whole canonical spoken item; no text, actual media or mouth timing."""

    spoken_content_id: NonBlank
    speaker_key: NonBlank
    sequence: Annotated[int, Field(strict=True, gt=0)]
    spoken_content_fingerprint: Fingerprint
    dpd_fingerprint: Fingerprint
    intent_context_fingerprint: Fingerprint
    duration_authority: Literal["SCENE_PLANNING_ESTIMATE"] = "SCENE_PLANNING_ESTIMATE"
    planned_start_ms: NonNegativeMs
    planned_duration_ms: PositiveMs
    planned_end_ms: PositiveMs
    transition_from_previous: Transition
    transition_hold_ms: NonNegativeMs
    transition_reason: NonBlank

    @model_validator(mode="after")
    def validate_window(self) -> DialogueTurnTiming:
        if self.planned_end_ms != self.planned_start_ms + self.planned_duration_ms:
            raise ValueError("INVALID_TURN_WINDOW: end must equal start + estimate")
        if self.sequence == 1:
            if self.transition_from_previous not in ("OPENING", "IMMEDIATE_RESPONSE"):
                raise ValueError("INVALID_OPENING_TRANSITION")
            if self.transition_hold_ms != 0:
                raise ValueError("opening hold belongs to preDialogueHoldMs")
        elif self.transition_from_previous == "OPENING":
            raise ValueError("OPENING is only valid for the first turn")
        elif self.transition_hold_ms == 0:
            raise ValueError("minimum inter-turn separation is required")
        return self


class DialogueTimingPlan(ContractModel):
    """Planned timing only. CONFLICT windows describe demand, not accepted placement."""

    schema_version: Literal["dialogue-timing-plan-v1"] = "dialogue-timing-plan-v1"
    scene_id: NonBlank
    shot_id: NonBlank
    shot_fingerprint: Fingerprint
    source_fingerprint: Fingerprint
    policy_version: NonBlank
    policy_fingerprint: Fingerprint
    target_shot_duration_ms: PositiveMs | None
    turns: Annotated[tuple[DialogueTurnTiming, ...], Field(min_length=1)]
    pre_dialogue_hold_ms: NonNegativeMs
    minimum_post_dialogue_hold_ms: PositiveMs
    post_dialogue_hold_ms: PositiveMs
    recommended_minimum_shot_duration_ms: PositiveMs
    planned_duration_ms: PositiveMs
    status: Literal["PLANNED", "CONFLICT"]
    diagnostic: Literal["TIMING_CONFLICT"] | None
    fingerprint: Fingerprint

    @model_validator(mode="after")
    def validate_budget_and_fingerprint(self) -> DialogueTimingPlan:
        sequences = [turn.sequence for turn in self.turns]
        if len(set(sequences)) != len(sequences):
            raise ValueError("DUPLICATE_SEQUENCE")
        if sequences != list(range(1, len(self.turns) + 1)):
            raise ValueError("DIALOGUE_ORDER_REQUIRED: contiguous ordered sequence required")
        ids = [turn.spoken_content_id for turn in self.turns]
        if len(set(ids)) != len(ids):
            raise ValueError("DUPLICATE_SPOKEN_CONTENT")
        if any(turn.intent_context_fingerprint != self.source_fingerprint for turn in self.turns):
            raise ValueError("INTENT_CONTEXT_MISMATCH")
        first = self.turns[0]
        if first.planned_start_ms != self.pre_dialogue_hold_ms:
            raise ValueError("PRE_DIALOGUE_HOLD_MISMATCH")
        if (first.transition_from_previous == "IMMEDIATE_RESPONSE") != (
            self.pre_dialogue_hold_ms == 0
        ):
            raise ValueError("zero opening requires explicit immediate intent")
        for previous, current in zip(self.turns, self.turns[1:]):
            if current.planned_start_ms < previous.planned_end_ms:
                raise ValueError("OVERLAPPING_DIALOGUE_NOT_SUPPORTED")
            if current.planned_start_ms != previous.planned_end_ms + current.transition_hold_ms:
                raise ValueError("TRANSITION_HOLD_MISMATCH")
        end = self.turns[-1].planned_end_ms
        minimum = end + self.minimum_post_dialogue_hold_ms
        if self.recommended_minimum_shot_duration_ms != minimum:
            raise ValueError("MINIMUM_DURATION_MISMATCH")
        target = self.target_shot_duration_ms
        conflict = target is not None and minimum > target
        if self.status != ("CONFLICT" if conflict else "PLANNED"):
            raise ValueError("TIMING_CONFLICT: status must reflect the Shot budget")
        if self.diagnostic != ("TIMING_CONFLICT" if conflict else None):
            raise ValueError("TIMING_DIAGNOSTIC_MISMATCH")
        if self.planned_duration_ms != max(minimum, target or 0):
            raise ValueError("SHOT_DURATION_MISMATCH")
        if self.post_dialogue_hold_ms != self.planned_duration_ms - end:
            raise ValueError("POST_DIALOGUE_HOLD_MISMATCH")
        expected = sha256_canonical(dump_contract(self, exclude={"fingerprint"}))
        if self.fingerprint != expected:
            raise ValueError("DIALOGUE_TIMING_FINGERPRINT_INVALID")
        return self
