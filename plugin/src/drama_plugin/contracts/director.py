"""Three opt-in Director envelopes. Specialized content remains at its original owner."""
from __future__ import annotations

from typing import Literal, Self, Any
from pydantic import ConfigDict, Field, model_validator, model_serializer, SerializerFunctionWrapHandler
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text
from drama_plugin.contracts.sequence import SourcePin


class SceneRuntimeBudget(ContractModel):
    """Nested creative estimate. Narrative categories partition time; score overlaps."""
    scene_id: Text
    sequence_id: Text
    act_id: Text
    source_ref: SourcePin
    purpose: Text
    dialogue_seconds: float = Field(ge=0, allow_inf_nan=False)
    action_seconds: float = Field(ge=0, allow_inf_nan=False)
    silent_performance_seconds: float = Field(ge=0, allow_inf_nan=False)
    transition_seconds: float = Field(ge=0, allow_inf_nan=False)
    expected_seconds: float = Field(gt=0, allow_inf_nan=False)
    expected_range_seconds: tuple[float, float]
    music_bearing_seconds: float = Field(ge=0, allow_inf_nan=False)
    intentional_no_music_seconds: float = Field(ge=0, allow_inf_nan=False)
    music_undecided_seconds: float = Field(ge=0, allow_inf_nan=False)
    estimate_basis: Text

    @model_validator(mode='after')
    def accounting(self) -> Self:
        import math
        lo,hi=self.expected_range_seconds
        if not all(math.isfinite(v) for v in (lo,hi)) or not 0<lo<=self.expected_seconds<=hi:
            raise ValueError('RUNTIME_RANGE_INVALID')
        narrative=self.dialogue_seconds+self.action_seconds+self.silent_performance_seconds+self.transition_seconds
        music=self.music_bearing_seconds+self.intentional_no_music_seconds+self.music_undecided_seconds
        if not math.isclose(narrative,self.expected_seconds,abs_tol=.01) or not math.isclose(music,self.expected_seconds,abs_tol=.01):
            raise ValueError('RUNTIME_PARTITIONS_MUST_BALANCE_MUSIC_IS_OVERLAY')
        return self


class DirectorRuntimeEstimate(ContractModel):
    """Nested Director/Book facet, not another persisted screenplay or media timeline."""
    basis: Literal['CREATIVE_ESTIMATE'] = 'CREATIVE_ESTIMATE'
    target_seconds: float = Field(gt=0, allow_inf_nan=False)
    expected_range_seconds: tuple[float, float]
    scene_budgets: tuple[SceneRuntimeBudget, ...] = Field(min_length=1)
    uncertainty: Text

    @model_validator(mode='after')
    def totals(self) -> Self:
        import math
        ids=[r.scene_id for r in self.scene_budgets]
        if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_RUNTIME_SCENE')
        total=sum(r.expected_seconds for r in self.scene_budgets)
        lo=sum(r.expected_range_seconds[0] for r in self.scene_budgets)
        hi=sum(r.expected_range_seconds[1] for r in self.scene_budgets)
        if not math.isclose(total,self.target_seconds,abs_tol=.01) or any(not math.isfinite(a) or not math.isclose(a,b,abs_tol=.01) for a,b in zip(self.expected_range_seconds,(lo,hi))):
            raise ValueError('RUNTIME_TOTAL_MISMATCH')
        sequence_acts: dict[str,str]={}
        for row in self.scene_budgets:
            if row.sequence_id in sequence_acts and sequence_acts[row.sequence_id]!=row.act_id:raise ValueError('SEQUENCE_CROSSES_RUNTIME_ACT')
            sequence_acts[row.sequence_id]=row.act_id
        return self


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
    preproduction_required: bool = False
    readiness_ref: SourcePin | None = None
    expected_runtime: DirectorRuntimeEstimate | None = None

    @model_serializer(mode='wrap')
    def legacy_dump(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = dict(handler(self))
        if not self.preproduction_required:
            data.pop('preproductionRequired', None); data.pop('preproduction_required', None)
        if self.readiness_ref is None:
            data.pop('readinessRef', None); data.pop('readiness_ref', None)
        if self.expected_runtime is None:
            data.pop('expectedRuntime', None); data.pop('expected_runtime', None)
        return data

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
