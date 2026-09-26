"""Opt-in evidence facet on existing Cinematic Intent items, never Source Canon.

Meaning stays in the intent's existing `meaning` field. Source facts are pointers;
professional implementation stays in its owner's existing artifact.
"""
from __future__ import annotations
from typing import Literal, Self
from pydantic import Field, model_validator
from .base import ContractModel
from .creative_asset import Text, Hash
from .creative_source import StageReview
from .source_pin import SourcePin


class InterpretationScope(ContractModel):
    kind: Literal['WHOLE_WORK', 'CHARACTER_ARC', 'RELATIONSHIP', 'MOVEMENT', 'SCENE', 'MOTIF']
    refs: tuple[Text, ...] = Field(min_length=1)


class SourceObservation(ContractModel):
    id: Text
    version: int = Field(ge=1)
    observation: Text
    scope: InterpretationScope
    anchor_ids: tuple[Text, ...] = Field(min_length=1)


class InterpretationEvidence(ContractModel):
    id: Text
    anchor_ids: tuple[Text, ...] = Field(min_length=1)
    basis: Literal['DIRECT_TEXT', 'RECURRENCE', 'STRUCTURAL_ECHO', 'CHARACTER_BEHAVIOR', 'INDIRECT']
    strength: Literal['STRONG', 'LIMITED']
    reason: Text


class CounterAssessment(ContractModel):
    evidence_id: Text
    effect: Literal['LIMITS_SCOPE', 'CONTRADICTS', 'ALTERNATIVE']
    reason: Text


class InterpretiveImplication(ContractModel):
    id: Text
    department: Text
    scope: InterpretationScope
    form: Literal['QUESTION', 'OBLIGATION']
    question: Text
    limitations: tuple[Text, ...] = Field(min_length=1)
    boundary_review: Literal['UNREVIEWED', 'QUESTIONS_ONLY', 'HOW_LEAK']
    # Explicit owner-original links distinguish phase state from objective world.
    character_state_ref: Text | None = None  # character_id:arc_stage in source package
    world_fact_refs: tuple[Text, ...] = ()
    music_policy: Literal['OPEN', 'YIELD', 'DO_NOT_SCORE'] = 'OPEN'


class MotifOccurrence(ContractModel):
    id: Text
    anchor_ids: tuple[Text, ...] = Field(min_length=1)
    scope: InterpretationScope
    local_function: Text
    evolution: Literal['RETAIN', 'EXPAND', 'RECONTEXTUALIZE', 'CONTRAST', 'OPEN']
    related_interpretation_ids: tuple[Text, ...] = Field(min_length=1)


class InterpretationFacet(ContractModel):
    schema_version: Literal['interpretation-facet-v1'] = 'interpretation-facet-v1'
    version: int = Field(ge=1)
    work_ref: Text
    branch_id: Text
    scope: InterpretationScope
    layer: Literal['INTERPRETIVE_HYPOTHESIS', 'WORKING_INTERPRETATION']
    status: Literal['WORKING', 'OPEN', 'MULTI_VALENT', 'CONTESTED', 'REJECTED', 'UNSUPPORTED']
    section: Literal['Core Interpretive Spine', 'Character State Arc', 'Primary Relationship Axis',
                     'Major Motifs', 'Reality / Dream Relation', 'World Relation',
                     'Do-Not-Interpret-As', 'Open / Contested Questions']
    source_ref: SourcePin
    thesis_refs: tuple[SourcePin, ...] = ()
    fact_refs: tuple[Text, ...] = ()
    observations: tuple[SourceObservation, ...] = Field(min_length=1)
    supporting: tuple[InterpretationEvidence, ...] = ()
    counter_evidence: tuple[InterpretationEvidence, ...] = ()
    counter_search: Literal['COUNTER_EVIDENCE_FOUND', 'NO_COUNTER_EVIDENCE_FOUND_IN_REVIEWED_SCOPE']
    reviewed_anchor_ids: tuple[Text, ...] = Field(min_length=1)
    counter_assessments: tuple[CounterAssessment, ...] = ()
    limitations: tuple[Text, ...] = Field(min_length=1)
    confidence: Literal['HIGH', 'MEDIUM', 'LOW', 'CONTESTED']
    confidence_reason: Text
    group_id: Text | None = None
    conflicts_with: tuple[Text, ...] = ()
    negative_boundaries: tuple[Text, ...] = ()
    occurrences: tuple[MotifOccurrence, ...] = ()
    implications: tuple[InterpretiveImplication, ...] = ()
    canon_consistency: Literal['UNREVIEWED', 'PRESERVED', 'CONCERN']
    review_basis: Literal['SELF_AUDIT', 'PROFESSIONAL_REVIEW', 'INDEPENDENT_REVIEW']
    evidence_review: StageReview | None = None

    @model_validator(mode='after')
    def explicit_evidence(self) -> Self:
        if bool(self.counter_evidence) != (self.counter_search == 'COUNTER_EVIDENCE_FOUND'):
            raise ValueError('COUNTER_EVIDENCE_SEARCH_MUST_BE_EXPLICIT')
        for values in (self.observations, self.supporting + self.counter_evidence, self.implications, self.occurrences):
            ids=[x.id for x in values]
            if len(ids)!=len(set(ids)): raise ValueError('DUPLICATE_INTERPRETATION_LOCAL_ID')
        if {a.evidence_id for a in self.counter_assessments} != {e.id for e in self.counter_evidence} or len(self.counter_assessments)!=len(self.counter_evidence):
            raise ValueError('COUNTER_EVIDENCE_ASSESSMENT_REQUIRED')
        return self


class InterpretationApproval(ContractModel):
    """Typed specialization of the existing PROFESSIONAL_CREATIVE_APPROVAL receipt.

    Its ref must additionally be supplied by the Host's approved_refs authority,
    as with Director dispatch. A JSON actor label alone is not authentication.
    """
    kind: Literal['PROFESSIONAL_CREATIVE_APPROVAL'] = 'PROFESSIONAL_CREATIVE_APPROVAL'
    subject_id: Text
    subject_fingerprint: Hash
    work_ref: Text
    branch_id: Text
    approved_by: tuple[Text, ...] = Field(min_length=1)
    actor_type: Literal['USER']
    decision: Literal['APPROVE', 'REJECT', 'REVOKE']
    mode: Literal['APPROVED_FOR_THIS_ADAPTATION', 'PRESERVE_AMBIGUITY']
    scope: InterpretationScope
    evidence_fingerprint: Hash
    version: int = Field(ge=1)


class InterpretationUse(ContractModel):
    interpretation_ref: SourcePin
    approval_ref: SourcePin
    implication_id: Text
    scope: InterpretationScope
    decision_fingerprint: Hash  # professional record values, not a copied decision
    disposition: Literal['CONSISTENT', 'DRIFT', 'INDEPENDENT_SOURCE', 'UNREVIEWED']
    reviewer: Text
    reason: Text
    independent_source_refs: tuple[SourcePin, ...] = ()
