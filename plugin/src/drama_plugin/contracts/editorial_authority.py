"""Optional editorial authority facets; no second measured-media timeline."""
from __future__ import annotations
from typing import Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash
from drama_plugin.contracts.source_pin import SourcePin

class EditorialIntent(ContractModel):
    scene_id: Text
    director_intent_id: Text
    source_authority: tuple[SourcePin, ...] = Field(min_length=1)
    protected_priority_ids: tuple[Text, ...] = Field(min_length=1)
    may_compress: Text
    may_omit: Text
    cannot_reorder: tuple[Text, ...] = Field(min_length=1)

class CoverageUnit(ContractModel):
    key: Text
    scene_id: Text
    necessity: Literal['REQUIRED','OPTIONAL']
    evidence_function: Text
    simultaneous_duties: tuple[Text, ...] = Field(min_length=1)
    missing_consequence: Text
    source_authority: tuple[SourcePin, ...] = Field(min_length=1)
    activation_condition: Text | None = None
    @model_validator(mode='after')
    def optional_condition(self) -> Self:
        if self.necessity=='OPTIONAL' and not self.activation_condition:
            raise ValueError('Optional coverage needs an activation condition')
        return self

class EditorialHold(ContractModel):
    key: Text
    event_sequence: tuple[Text, ...] = Field(min_length=1)
    hold_until: Text
    premature_exit_risk: Text
    # Event order is semantic authority. Measured timing is future observation.
    continuous_perception_required: bool = True

class CutCondition(ContractModel):
    key: Text
    cut_allowed_when: tuple[Text, ...] = Field(min_length=1)
    cut_prohibited_when: tuple[Text, ...] = Field(min_length=1)
    hold: EditorialHold
    reaction_required_before_exit: Text
    spatial_reset_required: Text
    audio_continuity_required: Text

class CoverageRequirement(ContractModel):
    key: Text
    intent: EditorialIntent
    required_coverage: tuple[Text, ...] = Field(min_length=1)
    optional_coverage: tuple[Text, ...] = ()
    redundant_coverage: tuple[Text, ...] = Field(min_length=1)
    forbidden_substitute: tuple[Text, ...] = Field(min_length=1)
    protected_action: Text
    protected_reaction: Text
    reaction_class: Literal['REQUIRED_REACTION','OPTIONAL_REACTION','FORBIDDEN_PREMATURE_REACTION']
    spatial_requirement: Text
    audio_requirement: Text
    coverage_risk: Literal['LOW','MEDIUM','HIGH']
    risk_reason: Text
    minimum_coverage_count: int = Field(ge=1)
    cut: CutCondition
    music_policy: Literal['BLOCKED','OPTIONAL_CONDITIONAL','ALLOWED_CONDITIONAL']
    music_entry: Text
    music_exit: Text
    performance_source_refs: tuple[Text, ...] = Field(min_length=1)
    @model_validator(mode='after')
    def minimum_is_set_cardinality(self) -> Self:
        if len(set(self.required_coverage))!=len(self.required_coverage) or self.minimum_coverage_count!=len(self.required_coverage):
            raise ValueError('Minimum count is unique required evidence units, not generation tasks')
        return self

class EditorialTransition(ContractModel):
    key: Text
    from_scene: Text
    to_scene: Text
    types: tuple[Literal['HARD_CUT','VISUAL_BRIDGE','SOUND_BRIDGE','J_CUT','L_CUT','TIME_ELLIPSIS','LOCATION_RESET','DELAYED_CUT'], ...] = Field(min_length=1)
    reason: Text
    incoming_information: Text
    protected_outgoing_reaction: Text
    sound_carry: Text
    time_relation: Literal['CONTINUOUS','ELLIPSIS','PARALLEL']
    space_relation: Text
    false_continuity_risk: Text
    jl_permission: Literal['ALLOWED_WITH_CONDITIONS','BLOCKED','NOT_NEEDED']
    source_authority: tuple[SourcePin, ...] = Field(min_length=1)
    @model_validator(mode='after')
    def transition_semantics(self) -> Self:
        if self.from_scene==self.to_scene:raise ValueError('Scene adjacency requires different scenes')
        if self.jl_permission!='ALLOWED_WITH_CONDITIONS' and set(self.types)&{'J_CUT','L_CUT'}:
            raise ValueError('J/L transition lacks permission')
        if self.time_relation=='ELLIPSIS' and 'TIME_ELLIPSIS' not in self.types:
            raise ValueError('Ellipsis must be explicit')
        return self

class EditorialAuthority(ContractModel):
    schema_version: Literal['editorial-authority-v1']='editorial-authority-v1'
    work_id: Text
    scene_order: tuple[Text, ...] = Field(min_length=1)
    source_authority: tuple[SourcePin, ...] = Field(min_length=1)
    coverage_units: tuple[CoverageUnit, ...] = Field(min_length=1)
    requirements: tuple[CoverageRequirement, ...] = Field(min_length=1)
    transitions: tuple[EditorialTransition, ...] = ()
    @model_validator(mode='after')
    def scope_and_economy(self) -> Self:
        scenes=set(self.scene_order);units={u.key:u for u in self.coverage_units}
        if len(scenes)!=len(self.scene_order) or len(units)!=len(self.coverage_units):raise ValueError('Duplicate identity')
        if len({r.key for r in self.requirements})!=len(self.requirements):raise ValueError('Duplicate requirement')
        if len({r.intent.director_intent_id for r in self.requirements})!=len(self.requirements):raise ValueError('Duplicate director intent')
        used=set()
        for r in self.requirements:
            if r.intent.scene_id not in scenes:raise ValueError('Unknown scene')
            for keys,kind in [(r.required_coverage,'REQUIRED'),(r.optional_coverage,'OPTIONAL')]:
                for key in keys:
                    if key not in units or units[key].scene_id!=r.intent.scene_id or units[key].necessity!=kind:raise ValueError('Invalid coverage reference')
                    used.add(key)
        if used!=set(units):raise ValueError('Unused coverage inflates budget')
        if {(t.from_scene,t.to_scene) for t in self.transitions}!=set(zip(self.scene_order,self.scene_order[1:])) or len(self.transitions)!=max(0,len(scenes)-1):
            raise ValueError('Every scene adjacency needs one transition')
        return self

RepairKind=Literal['TRIM_FIX','INSERT_FIX','REACTION_FIX','SOUND_BRIDGE_FIX','AMBIENCE_FIX','MUSIC_HANDOFF_FIX','SPEED_FIX','CROP_FIX','PICKUP_REQUIRED','RETAKE_REQUIRED_UPSTREAM']
class EditorialRepair(ContractModel):
    kind: RepairKind
    scope: Text
    preserves: tuple[Text, ...] = Field(min_length=1)
    evidence_ref: Text
    upstream_decision_required: bool = False
    @model_validator(mode='after')
    def upstream_owner(self) -> Self:
        if self.kind=='RETAKE_REQUIRED_UPSTREAM' and not self.upstream_decision_required:raise ValueError('Retake is an upstream decision')
        return self

class UsableRange(ContractModel):
    start: float = Field(ge=0,allow_inf_nan=False)
    end: float = Field(gt=0,allow_inf_nan=False)
    functions: tuple[Text, ...] = Field(min_length=1)
    @model_validator(mode='after')
    def range_order(self) -> Self:
        if self.end<=self.start:raise ValueError('Invalid usable range')
        return self

class EditorialUsability(ContractModel):
    """FilmReview facet, never a substitute for normal-speed AV evidence."""
    asset_ref: Text
    media_hash: Hash
    scene_id: Text
    director_intent_ids: tuple[Text, ...] = Field(min_length=1)
    usable_ranges: tuple[UsableRange, ...] = ()
    covered_requirements: tuple[Text, ...] = ()
    missing_requirements: tuple[Text, ...] = ()
    continuity_status: Literal['PASS','FAIL','UNKNOWN']
    axis_status: Literal['PASS','FAIL','UNKNOWN']
    performance_status: Literal['PASS','FAIL','UNKNOWN']
    audio_status: Literal['PASS','FAIL','UNKNOWN']
    editorial_usability: Literal['USABLE_FULL','USABLE_PARTIAL','EDITORIAL_REPAIRABLE','NEEDS_PICKUP','UNUSABLE']
    repair_options: tuple[EditorialRepair, ...] = ()
    pickup_requirements: tuple[Text, ...] = ()
    evidence_refs: tuple[Text, ...] = Field(min_length=1)
    basis: Literal['SYNTHETIC_FIXTURE','OBSERVED_MEDIA']
    outside_approved_intent: bool = False
    @model_validator(mode='after')
    def no_fictional_pass(self) -> Self:
        if set(self.covered_requirements)&set(self.missing_requirements):raise ValueError('Covered and missing overlap')
        if self.editorial_usability=='USABLE_FULL' and (self.missing_requirements or not self.covered_requirements or not self.usable_ranges or any(v!='PASS' for v in [self.continuity_status,self.axis_status,self.performance_status,self.audio_status])):
            raise ValueError('Full usability needs ranges, coverage and known passing domains')
        if self.editorial_usability=='EDITORIAL_REPAIRABLE' and not self.repair_options:raise ValueError('Repairable needs bounded repair')
        if self.editorial_usability=='NEEDS_PICKUP' and not self.pickup_requirements:raise ValueError('Pickup needs a missing function')
        return self


class CompressionCandidate(ContractModel):
    what_is_removed: Text
    why_redundant: Text
    surviving_director_intent_ids: tuple[Text, ...] = Field(min_length=1)
    priority_impact: Literal['NONE','P0','P1','P2','P3']
    disposition: Literal['COMPRESSION_CANDIDATE','UPSTREAM_AUTHORITY_REQUIRED']
    @model_validator(mode='after')
    def no_hidden_loss(self) -> Self:
        if self.priority_impact!='NONE' and self.disposition!='UPSTREAM_AUTHORITY_REQUIRED':
            raise ValueError('Compression may not hide protected intent loss')
        return self

class EditorialPass(ContractModel):
    stage: Literal['ASSEMBLY','ROUGH','FINE']
    source_authority: tuple[SourcePin, ...] = Field(min_length=1)
    entry_requirements: tuple[Text, ...] = Field(min_length=1)
    exit_requirements: tuple[Text, ...] = Field(min_length=1)
    compression_candidates: tuple[CompressionCandidate, ...] = ()
    picture_edit_plan_ref: Text | None = None
    media_state: Literal['DESIGN_ONLY','MEASURED_CANDIDATE','REVIEWED_MEDIA'] = 'DESIGN_ONLY'
    @model_validator(mode='after')
    def measured_reference(self) -> Self:
        if self.media_state!='DESIGN_ONLY' and not self.picture_edit_plan_ref:
            raise ValueError('Measured pass must reuse existing PictureEditPlan')
        return self

class EditorialDecision(ContractModel):
    """Evidence attached to an existing PictureEditPlan edit index, not a timeline."""
    edit_index: int = Field(ge=0)
    scene_id: Text
    director_intent_id: Text
    coverage_requirement_id: Text
    cut_condition_id: Text
    source_authority: tuple[SourcePin, ...] = Field(min_length=1)
    completed_events: tuple[Text, ...]
    reaction_complete: bool | None = None
    spatial_ready: bool | None = None
    audio_ready: bool | None = None
    priority_impact: Literal['NONE','P0','P1','P2','P3']='NONE'
    p2_grammar_equivalent: bool | None = None
    evidence_refs: tuple[Text, ...] = Field(min_length=1)
