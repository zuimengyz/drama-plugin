"""Opt-in work-owned directing facets; no renderer, editorial or review executor.

Stored through existing local artifact refs / DirectorWorkspace.intent_refs.
These contracts validate design structure, never formal Book readiness or taste.
"""
from __future__ import annotations

from typing import Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text
from drama_plugin.contracts.sequence import SourcePin


class FilmGrammarRule(ContractModel):
    rule_id: Text
    domain: Text
    narrative_reason: Text
    applies_when: Text
    execution: Text
    exception: Text
    exit_condition: Text


class GrammarState(ContractModel):
    scope_id: Text
    perceptual_owner: Text
    narrative_change: Text
    rule_ids: tuple[Text, ...] = Field(min_length=1)
    realization: Text


class AestheticRule(ContractModel):
    rule_id: Text
    stance: Literal['PREFER', 'REJECT', 'CONTEXT_DEPENDENT']
    criterion: Text
    reason: Text
    succeeds_when: Text
    fails_when: Text


class WorkDirectingAuthority(ContractModel):
    """A referenced design sidecar, not another Work or a second screenplay."""
    schema_version: Literal['work-directing-authority-v1'] = 'work-directing-authority-v1'
    work_scope: Text
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    grammar_rules: tuple[FilmGrammarRule, ...] = Field(min_length=1)
    evolution: tuple[GrammarState, ...] = Field(min_length=1)
    aesthetic_rules: tuple[AestheticRule, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def bindings(self) -> Self:
        for values in ([p.key for p in self.source_pins],
                       [r.rule_id for r in self.grammar_rules],
                       [r.rule_id for r in self.aesthetic_rules],
                       [s.scope_id for s in self.evolution]):
            if len(values) != len(set(values)):
                raise ValueError('Duplicate directing authority binding')
        rules = {r.rule_id for r in self.grammar_rules}
        if any(not set(s.rule_ids) <= rules for s in self.evolution):
            raise ValueError('Unknown grammar rule in evolution')
        return self


class EditorialIntentHandoff(ContractModel):
    """Intent only. It does not create coverage, an edit or an executable timeline."""
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    director_intent: Text
    shot_group_intent: Text
    protected_hold: Text
    cut_condition: Text
    coverage_requirement: Text
    continuity_requirement: Text
    sound_bridge_intent: Text
    optional_insert: tuple[Text, ...] = ()


class AdaptiveIntentHandoff(ContractModel):
    """Future comparison input; no observation, disposition or repair behavior."""
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    intended_result: Text
    must_preserve: tuple[Text, ...] = Field(min_length=1)
    acceptable_variation: tuple[Text, ...]
    forbidden_drift: tuple[Text, ...] = Field(min_length=1)
    aesthetic_constitution_refs: tuple[SourcePin, ...] = Field(min_length=1)
    performance_intent: Text
    camera_intent: Text


class AestheticPairwiseReviewContract(ContractModel):
    """Future evidence payload, referenced by existing feedback; not a review entity.

    No current consumer selects, adopts, observes or repairs candidate media.
    A future owner must verify original evidence, scope, source freshness and human
    review separately; construction never constitutes artistic approval.
    """
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    constitution_ref: SourcePin
    candidate_a: SourcePin
    candidate_b: SourcePin
    evidence_refs: tuple[SourcePin, ...] = ()
    technical_difference: Text
    performance_difference: Text
    camera_difference: Text
    aesthetic_difference: Text
    constitution_alignment_a: dict[Text, Literal['ALIGNED', 'CONFLICT', 'UNKNOWN']]
    constitution_alignment_b: dict[Text, Literal['ALIGNED', 'CONFLICT', 'UNKNOWN']]
    artificiality_risk: Text
    overstatement_risk: Text
    generic_beauty_risk: Text
    preferred_candidate: Literal['A', 'B', 'NEITHER', 'UNDETERMINED']
    reason: Text
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    human_review_required: bool

    @model_validator(mode='after')
    def evidence_boundary(self) -> Self:
        if self.candidate_a == self.candidate_b:
            raise ValueError('Pairwise comparison needs distinct candidates')
        if self.preferred_candidate != 'UNDETERMINED' and not self.evidence_refs:
            raise ValueError('Preference requires evidence references')
        if not self.constitution_alignment_a or self.constitution_alignment_a.keys() != self.constitution_alignment_b.keys():
            raise ValueError('Compare the same nonempty constitution criteria')
        return self
