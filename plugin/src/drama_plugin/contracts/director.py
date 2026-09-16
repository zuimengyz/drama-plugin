"""Three opt-in Director envelopes. Specialized content remains at its original owner."""
from __future__ import annotations

from typing import Literal, Self
from pydantic import ConfigDict, Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text
from drama_plugin.contracts.sequence import SourcePin


class DirectorWorkspace(ContractModel):
    model_config = ConfigDict(frozen=True)
    schema_version: Literal['director-workspace-v1'] = 'director-workspace-v1'
    workspace_id: Text
    scope_id: Text
    branch_id: Text
    parent_ref: SourcePin | None = None
    revision: int = Field(default=0, ge=0, strict=True)
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    route_ref: SourcePin | None = None
    intent_refs: tuple[SourcePin, ...] = ()  # PLANNED; never a second intent body
    checkpoint: Literal['READY', 'DISPATCHED', 'REVIEW_PENDING', 'REVISION_PENDING', 'WAITING_APPROVAL'] = 'READY'
    request_ref: SourcePin | None = None
    feedback_ref: SourcePin | None = None  # OBSERVED; not adopted
    review_ref: SourcePin | None = None
    adopted_head: SourcePin | None = None  # Only a reviewed Bible presentation receipt
    stale_keys: tuple[Text, ...] = ()

    @model_validator(mode='after')
    def coherent_index(self) -> Self:
        if len({p.key for p in self.source_pins}) != len(self.source_pins):
            raise ValueError('Duplicate source pin')
        if self.checkpoint != 'READY' and not self.request_ref:
            raise ValueError('Checkpoint requires request reference')
        if self.feedback_ref and not self.request_ref:
            raise ValueError('Observation requires request')
        if self.checkpoint == 'REVIEW_PENDING' and not self.feedback_ref:
            raise ValueError('Review requires observation')
        return self


class CapabilityRequest(ContractModel):
    model_config = ConfigDict(frozen=True)
    schema_version: Literal['capability-request-v1'] = 'capability-request-v1'
    request_id: Text
    revision: int = Field(default=0, ge=0, strict=True)
    workspace_id: Text
    branch_id: Text
    scope_id: Text
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    route_ref: SourcePin | None = None
    intent_refs: tuple[SourcePin, ...] = Field(min_length=1)
    capability: Text
    task: Text
    result_kind: Literal['DESIGN_ONLY', 'MEDIA']
    must_preserve: tuple[Text, ...]
    prohibitions: tuple[Text, ...]
    priority: Literal['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    required_evidence: tuple[Text, ...] = Field(min_length=1)
    approval_refs: tuple[SourcePin, ...] = ()
    requirement_refs: tuple[SourcePin, ...] = ()
    supersedes: SourcePin | None = None

    @model_validator(mode='after')
    def unique_bindings(self) -> Self:
        for pins in (self.source_pins, self.intent_refs, self.approval_refs, self.requirement_refs):
            if len({p.key for p in pins}) != len(pins):
                raise ValueError('Duplicate request binding')
        if len(set(self.required_evidence)) != len(self.required_evidence):
            raise ValueError('Duplicate evidence obligation')
        return self


class CapabilityFeedback(ContractModel):
    model_config = ConfigDict(frozen=True)
    schema_version: Literal['capability-feedback-v1'] = 'capability-feedback-v1'
    revision: int = Field(default=0, ge=0, strict=True)
    request_ref: SourcePin
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    result_refs: tuple[SourcePin, ...] = ()
    evidence_refs: tuple[SourcePin, ...] = ()
    execution: Literal['COMPLETED', 'FAILED', 'UNKNOWN'] = 'UNKNOWN'
    feasibility: Literal['SUPPORTED', 'SUPPORTED_WITH_CONSTRAINTS', 'UNKNOWN', 'UNSUPPORTED_CURRENTLY', 'REQUIRES_DECOMPOSITION'] = 'UNKNOWN'
    conditions: tuple[Literal['REQUIRES_HIGHER_COST', 'REQUIRES_USER_APPROVAL', 'INSUFFICIENT_EVIDENCE'], ...] = ()
    fulfilled: tuple[Text, ...] = ()
    unmet: tuple[Text, ...] = ()
    limitations: tuple[Text, ...] = ()
    unknowns: tuple[Text, ...] = ()
    assumptions: tuple[Text, ...] = ()
    production_risks: tuple[Text, ...] = ()
    next_responsibility: Text

    @model_validator(mode='after')
    def honest_completion(self) -> Self:
        if self.execution == 'COMPLETED' and not self.result_refs:
            raise ValueError('Completed execution needs a retained result')
        if set(self.fulfilled) & set(self.unmet):
            raise ValueError('Requirement cannot be both fulfilled and unmet')
        return self
