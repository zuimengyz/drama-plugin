"""Nested source locators and review receipts, not another Scene/Beat canon.

Scene owns carrier order and actual events. DPD owns expectations/interpretation.
No mapper invents an event, objective, response, dialogue or approval.
"""
from __future__ import annotations

from typing import Literal
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash


class SourceCarrier(ContractModel):
    # action:<start>:<end> in screenplayAction, or spoken:<canonical line id>.
    ref: Text
    text_hash: Hash
    actor: Text | None = None
    target: Text | None = None
    role: Literal['STIMULUS', 'ACTION', 'RESPONSE', 'REACTION', 'TRIGGER', 'AFTERMATH', 'SILENCE', 'ENVIRONMENT']
    cause_ref: Text | None = None
    important: bool = False
    silence_function: Literal['REFUSAL', 'WAITING', 'PROCESSING', 'INTERRUPTION', 'UNFINISHED', 'NO_OPPORTUNITY', 'ENVIRONMENTAL'] | None = None


class InteractionTrace(ContractModel):
    action_ref: Text
    response_ref: Text
    next_action_ref: Text | None = None
    strategy_change: bool = False
    relationship_change: Text | None = None


class InformationRelease(ContractModel):
    carrier_ref: Text
    parts: tuple[Text, ...] = Field(min_length=1)
    audience: bool
    characters: tuple[Text, ...] = ()
    after_response_ref: Text | None = None


class InformationTrace(ContractModel):
    information_ref: Text
    # Source-owner's semantic partition; no NLP inference or arbitrary word count.
    parts: dict[Text, Text] = Field(min_length=1)
    releases: tuple[InformationRelease, ...] = ()
    not_before: Text | None = None
    needed_by: Text | None = None
    needed_by_subjects: tuple[Text, ...] = ()  # canonical actors or AUDIENCE
    prior_knowledge: dict[Text, tuple[Text, ...]] = Field(default_factory=dict)
    direct_statement_reason: Text | None = None


class SceneDramaturgy(ContractModel):
    """Approved annotation in existing Scene.content, with no new beat identities."""
    owner: Literal['scene-development'] = 'scene-development'
    source_body_hash: Hash  # Scene excluding this facet, avoiding self-hashing.
    carriers: tuple[SourceCarrier, ...] = Field(min_length=1)
    interactions: tuple[InteractionTrace, ...] = ()
    information: tuple[InformationTrace, ...] = ()
    entry_state: dict[Text, Text] = Field(min_length=1)
    exit_state: dict[Text, Text] = Field(min_length=1)
    state_evidence: tuple[Text, ...] = Field(min_length=1)
    suspension_reason: Text | None = None


class ResponseInterpretation(ContractModel):
    """Nested only in BeatDPD, referencing Scene's actual response."""
    action_ref: Text
    response_ref: Text
    expected_response: Text
    interpretation: Text
    transition_reason: Text | None = None
    next_beat_id: Text | None = None


ReviewAxis = Literal['ACTION_RESPONSE_CHAIN', 'STRATEGY_CHANGE', 'INFORMATION_RELEASE',
                     'LISTENER_CAUSALITY', 'SILENCE_FUNCTION', 'ENTRY_EXIT_DELTA']


class DramaturgyFinding(ContractModel):
    axis: ReviewAxis
    scope: Text  # SCENE, information ref or a carrier ref
    status: Literal['PASS', 'CONCERN', 'UNRESOLVED']
    finding: Text
    reason: Text
    evidence_refs: tuple[Text, ...] = Field(min_length=1)
    repair_owner: Literal['scene-development', 'dramatic-performance-direction', 'director', 'literary-adaptation']


class DramaturgyReview(ContractModel):
    subject_hash: Hash  # current Scene + DPD fingerprints; no review in source canon
    author: Text
    reviewer: Text
    basis: Literal['SELF_AUDIT', 'PARTIALLY_ISOLATED_REVIEW', 'INDEPENDENT_REVIEW']
    isolation_evidence: Text
    inputs_received: tuple[Text, ...] = Field(min_length=1)
    findings: tuple[DramaturgyFinding, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def honest_independence(self) -> DramaturgyReview:
        if self.basis == 'INDEPENDENT_REVIEW' and self.author == self.reviewer:
            raise ValueError('INDEPENDENT_REVIEW_REQUIRES_DISTINCT_READER')
        return self


class DirectionDensity(ContractModel):
    """Evidence for existing STANDARD/EXPANDED; not an artistic score."""
    dramatic_salience: bool
    ambiguity: bool
    relationship_turn: bool
    performance_risk: bool
    misreading_risk: bool
    reason: Text
    source_refs: tuple[Text, ...] = Field(min_length=1)

    @property
    def expanded(self) -> bool:
        return any((self.dramatic_salience, self.ambiguity, self.relationship_turn,
                    self.performance_risk, self.misreading_risk))
