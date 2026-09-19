"""Provider-neutral realization of existing editorial evidence identities."""
from __future__ import annotations
from typing import Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash
from drama_plugin.contracts.source_pin import SourcePin

ProductionFormalizationState = Literal['NOT_FORMALIZED','READY_FOR_SHOT_DESIGN','FORMALIZED','BLOCKED_BY_AUTHORITY','BLOCKED_BY_PROVIDER_UNKNOWN']

class CoverageRealizationPolicy(ContractModel):
    realization_mode: Literal['SINGLE_MATERIAL_PREFERRED','MULTI_MATERIAL_ALLOWED','MULTI_MATERIAL_REQUIRED','UNRESOLVED']
    split_policy: Literal['FREE','CONTINUITY_GUARDED','PROTECTED_SEQUENCE','NO_INTERNAL_SPLIT']
    merge_policy: Literal['MAY_SHARE_WITH_OTHER_COVERAGE','DEDICATED_EVIDENCE_REQUIRED','SHARED_WITH_EXPLICIT_REFS']
    continuity_keys: dict[Text, Text] = Field(default_factory=dict)
    required_temporal_order: tuple[Text, ...] = ()
    required_shared_state: dict[Text, Text] = Field(default_factory=dict)
    production_risk: Literal['LOW','MEDIUM','HIGH']
    rationale: Text
    split_boundary_rule: Text
    @model_validator(mode='after')
    def meaningful_split(self) -> Self:
        if self.split_policy in ('PROTECTED_SEQUENCE','NO_INTERNAL_SPLIT') and not self.required_temporal_order:
            raise ValueError('Protected sequence needs approved ordered events')
        if self.split_policy!='FREE' and not self.continuity_keys:
            raise ValueError('Guarded split needs actual continuity keys')
        if self.realization_mode=='MULTI_MATERIAL_REQUIRED' and self.split_policy=='NO_INTERNAL_SPLIT':
            raise ValueError('Required internal decomposition conflicts with indivisible evidence')
        return self

class CoverageDependency(ContractModel):
    key: Text
    coverage_unit_id: Text
    target_coverage_unit_id: Text
    relation: Literal['depends_on','must_precede','must_follow','may_share_material_with','must_not_share_material_with','requires_same_axis_state_as','requires_same_continuity_state_as']
    scope: Text
    reason: Text
    source_authority: tuple[SourcePin, ...] = Field(min_length=1)
    @model_validator(mode='after')
    def not_self(self) -> Self:
        if self.coverage_unit_id==self.target_coverage_unit_id:raise ValueError('Self dependency')
        return self

class CoverageRealizationPlan(ContractModel):
    coverage_unit_id: Text
    scene_id: Text
    director_intent_refs: tuple[Text, ...] = Field(min_length=1)
    source_fingerprint: Hash
    source_authority: tuple[SourcePin, ...] = Field(min_length=1)
    coverage_type: Literal['REQUIRED','OPTIONAL']
    policy: CoverageRealizationPolicy
    planned_shot_refs: tuple[Text, ...] = ()
    planned_shot_group_refs: tuple[Text, ...] = ()
    dependency_refs: tuple[Text, ...] = ()
    formalization_state: ProductionFormalizationState = 'NOT_FORMALIZED'
    formalization_reason: Text
    optional_activation_evidence: tuple[SourcePin, ...] = ()
    @model_validator(mode='after')
    def formal_identity(self) -> Self:
        for refs in (self.director_intent_refs,self.planned_shot_refs,self.planned_shot_group_refs,self.dependency_refs):
            if len(set(refs))!=len(refs):raise ValueError('Duplicate realization reference')
        if self.formalization_state=='FORMALIZED' and not self.planned_shot_refs:
            raise ValueError('Formalized must resolve actual canonical Shots, including group members')
        if self.coverage_type=='OPTIONAL' and self.formalization_state in ('READY_FOR_SHOT_DESIGN','FORMALIZED') and not self.optional_activation_evidence:
            raise ValueError('Optional coverage requires source-bound activation evidence')
        if self.policy.realization_mode=='UNRESOLVED' and self.formalization_state in ('READY_FOR_SHOT_DESIGN','FORMALIZED'):
            raise ValueError('Unknown feasibility is not formal readiness')
        return self
