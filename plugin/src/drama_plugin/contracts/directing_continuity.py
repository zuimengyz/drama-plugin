"""Optional work-authored intent, spatial and readiness declarations.

Structural validation only: no production, observation, editing or phase executor.
"""
from __future__ import annotations

from typing import Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text
from drama_plugin.contracts.sequence import SourcePin


class PrioritizedIntent(ContractModel):
    intent_id: Text
    intent: Text
    priority: Literal['P0', 'P1', 'P2', 'P3']
    reason: Text


class DirectorIntentPriority(ContractModel):
    work_scope: Text
    intent_group_id: Text
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    intent_priority: tuple[PrioritizedIntent, ...] = Field(min_length=1)
    protected_intent: tuple[Text, ...] = Field(min_length=1)
    degradable_intent: tuple[Text, ...]
    protect_first: tuple[Text, ...] = Field(min_length=1)
    sacrifice_first: tuple[Text, ...]
    sacrifice_before: tuple[tuple[Text, Text], ...]
    never_sacrifice_for: tuple[tuple[Text, Text], ...]
    allowed_substitution: Text
    unresolved_conflict_policy: Literal['STOP_AND_REPORT_CONFLICT']

    @model_validator(mode='after')
    def coherent_order(self) -> Self:
        levels = {x.intent_id: int(x.priority[1]) for x in self.intent_priority}
        if len(levels) != len(self.intent_priority):
            raise ValueError('Intent IDs must be unique')
        protected, degradable = set(self.protected_intent), set(self.degradable_intent)
        for values in (self.protected_intent, self.degradable_intent, self.protect_first, self.sacrifice_first):
            if len(values) != len(set(values)) or not set(values) <= levels.keys():
                raise ValueError('Unknown or duplicate intent reference')
        if protected & degradable or protected | degradable != levels.keys():
            raise ValueError('Declare each intent as protected or degradable')
        if any(levels[x] == 0 for x in degradable):
            raise ValueError('Inviolable intent cannot be degraded')
        if set(self.protect_first) != protected or set(self.sacrifice_first) != degradable:
            raise ValueError('Orders must enumerate the declared sets')
        if [levels[x] for x in self.protect_first] != sorted(levels[x] for x in protected):
            raise ValueError('Protect higher priority first')
        if [levels[x] for x in self.sacrifice_first] != sorted((levels[x] for x in degradable), reverse=True):
            raise ValueError('Sacrifice lower priority first')
        edges: dict[str, set[str]] = {x: set() for x in levels}
        for first, second in self.sacrifice_before:
            if first not in degradable or second not in levels or first == second or levels[first] < levels[second]:
                raise ValueError('Invalid sacrifice relation')
            edges[first].add(second)
            if second in degradable and self.sacrifice_first.index(first) >= self.sacrifice_first.index(second):
                raise ValueError('Sacrifice relation contradicts declared order')
        for protected_id, benefit in self.never_sacrifice_for:
            if protected_id not in levels or benefit not in levels or protected_id == benefit:
                raise ValueError('Invalid non-sacrifice reference')
            if benefit in edges[protected_id]:
                raise ValueError('Contradictory sacrifice prohibition')
        visiting: set[str] = set()
        done: set[str] = set()
        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError('Cyclic sacrifice relations')
            if node in done:
                return
            visiting.add(node)
            for other in edges[node]:
                visit(other)
            visiting.remove(node)
            done.add(node)
        for node in levels:
            visit(node)
        return self


class SpatialContinuity(ContractModel):
    work_scope: Text
    scope_id: Text
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    primary_axis: Text
    screen_direction: Text
    entry_direction: Text
    exit_direction: Text
    subject_relation: Text
    axis_mode: Literal['STABLE', 'MOTIVATED_AXIS_CROSS', 'RESET']
    allow_axis_cross: bool
    axis_cross_reason: Text
    axis_cross_condition: Text
    reorientation_required: bool
    reorientation_anchor: Text

    @model_validator(mode='after')
    def crossing_requires_reorientation(self) -> Self:
        if self.allow_axis_cross and not self.reorientation_required:
            raise ValueError('Permitted crossing requires reorientation')
        if self.axis_mode == 'MOTIVATED_AXIS_CROSS' and not self.allow_axis_cross:
            raise ValueError('Motivated crossing must be allowed explicitly')
        if self.axis_mode == 'RESET' and not self.reorientation_required:
            raise ValueError('Reset requires a reorientation anchor')
        return self


class ReadinessRequirement(ContractModel):
    requirement_id: Text
    category: Literal['AUTHORITY', 'BINDING', 'RUNTIME', 'INSTALLATION']
    required_state: Text
    current_state: Text
    assessment: Literal['MET', 'UNMET', 'UNKNOWN']
    blocking: bool
    evidence_refs: tuple[SourcePin, ...]
    reason: Text

    @model_validator(mode='after')
    def met_requires_evidence(self) -> Self:
        if self.assessment == 'MET' and (self.current_state != self.required_state or not self.evidence_refs):
            raise ValueError('Met requirement needs matching state and evidence')
        return self


class PhaseReadiness(ContractModel):
    """Declared evidence, not authenticated approval or permission to advance."""
    work_scope: Text
    target_phase: Text
    requirements: tuple[ReadinessRequirement, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def unique_requirements(self) -> Self:
        ids = [r.requirement_id for r in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate readiness requirement')
        return self

    result: Literal['READY', 'READY_WITH_NON_BLOCKING_GAPS', 'BLOCKED']

    @model_validator(mode='after')
    def result_matches_requirements(self) -> Self:
        gaps = [r for r in self.requirements if r.assessment != 'MET']
        expected = ('BLOCKED' if any(r.blocking for r in gaps) else
                    'READY_WITH_NON_BLOCKING_GAPS' if gaps else 'READY')
        if self.result != expected:
            raise ValueError('Readiness result contradicts declared requirements')
        return self
