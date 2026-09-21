"""Reusable design intent, separate from identity references and transient state."""
from __future__ import annotations
from typing import Annotated, Any, Literal, Self
from pydantic import Field, model_validator, model_serializer, SerializerFunctionWrapHandler
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.visual_medium import VisualMediumIntent
from drama_plugin.contracts.character_evidence import CharacterEvidence
from drama_plugin.contracts.location_design import LocationDesign
from drama_plugin.contracts.creative_asset import Text, Hash, Provenance, PatternValidation


class CanonBasis(ContractModel):
    source_ref: Text
    claim: Text
    classification: Literal['CANON', 'DOCUMENTED', 'INFERENCE', 'DESIGN_CHOICE', 'OPTIONAL_DESIGN_HYPOTHESIS']
    limitation: Text | None = None


class HistoricalCanonPolicy(ContractModel):
    historical: bool = False
    source_canon: tuple[CanonBasis, ...] = ()
    constraints: tuple[Text, ...] = ()

    @model_validator(mode='after')
    def supported_history(self) -> Self:
        if self.historical and (not self.constraints or not any(b.classification in {'CANON','DOCUMENTED'} for b in self.source_canon)):
            raise ValueError('Historical design requires evidence and constraints')
        return self


class VisualAuthority(ContractModel):
    silhouette_authority: Text
    body_scale: Text | None = None
    camera_privilege: Text | None = None
    costume_hierarchy: Text
    blocking_hierarchy: Text
    posture: Text | None = None
    movement_economy: Text | None = None
    others_reaction: Text | None = None
    visual_contrast: Text | None = None
    first_glance_importance: Text


class FirstAppearanceContract(ContractModel):
    silhouette: Text
    visual_hierarchy: Text
    costume_hierarchy: Text
    blocking: Text
    camera_privilege: Text
    lighting_privilege: Text
    surrounding_reaction: Text
    first_readable_action: Text
    first_readable_attitude: Text
    name_caption_requirement: Literal['NONE','OPTIONAL','REQUIRED'] = 'NONE'
    hidden_identity_reason: Text | None = None
    distinct_from_extras: bool = True

    @model_validator(mode='after')
    def readable_without_caption(self) -> Self:
        if not self.distinct_from_extras and not self.hidden_identity_reason:
            raise ValueError('Equal visual hierarchy needs a story reason to conceal identity')
        return self


class BodyDesign(ContractModel):
    stature: Text | None = None
    proportion: Text | None = None
    shoulder_width: Text | None = None
    physical_presence: Text | None = None
    movement_quality: Text | None = None


class FaceDesign(ContractModel):
    shape: Text | None = None
    bone_structure: Text | None = None
    brow: Text | None = None
    cheekbone: Text | None = None
    jaw: Text | None = None
    eye_character: Text | None = None
    skin_character: Text | None = None


class CharacterVisualSpec(ContractModel):
    schema_version: Literal['character-visual-v1'] = 'character-visual-v1'
    evidence: CharacterEvidence | None = None

    @model_serializer(mode='wrap')
    def preserve_legacy_wire(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if self.evidence is None:
            data.pop('evidence', None)
        return data

    character_identity: Text
    revision: Text
    dramatic_role: Text
    core_character: bool = False
    visual_objective: Text
    age_impression: Text | None = None
    body: BodyDesign = Field(default_factory=BodyDesign)
    silhouette: Text
    face: FaceDesign = Field(default_factory=FaceDesign)
    hair: Text | None = None
    beard: Text | None = None
    posture: Text | None = None
    screen_presence: Text | None = None
    costume_authority: Text | None = None
    status_signals: tuple[Text, ...] = ()
    first_appearance: FirstAppearanceContract | None = None
    visual_authority: VisualAuthority | None = None
    avoid: tuple[Text, ...] = ()
    historical_constraints: HistoricalCanonPolicy = Field(default_factory=HistoricalCanonPolicy)

    @model_validator(mode='after')
    def core_authority(self) -> Self:
        if self.core_character and (not self.visual_authority or not self.first_appearance):
            raise ValueError('Core character requires authority and first appearance design')
        return self


class CharacterState(ContractModel):
    character_identity: Text
    scene_or_shot_id: Text
    changes: tuple[Text, ...] = Field(min_length=1)


class CastingTestConditions(ContractModel):
    """Shared casting test setup, independent of a candidate's face variation."""
    background: Text
    lighting: Text
    camera: Text
    framing: Text
    orientation: Text
    posture: Text
    clothing: Text
    armor: Literal['NONE'] = 'NONE'
    additional_people: Literal[0] = 0


class CastingReconciliation(ContractModel):
    """Explicit user-directed search-space correction, not a formal asset edit."""
    request_ref: Text
    population_direction: Text
    apparent_age_min: int = Field(ge=18, le=100)
    apparent_age_max: int = Field(ge=18, le=100)
    hair: Text
    beard: Text
    face: tuple[Text, ...] = Field(min_length=1)
    body: tuple[Text, ...] = Field(min_length=1)
    authority: Text
    avoid: tuple[Text, ...] = Field(min_length=1)
    original_fictional_face: Literal[True] = True
    old_face_authority: Literal[False] = False
    old_body_authority: Literal[False] = False

    @model_validator(mode='after')
    def age_interval(self) -> Self:
        if self.apparent_age_min > self.apparent_age_max:
            raise ValueError('Invalid casting age interval')
        return self


class CastingBrief(ContractModel):
    """Provider-neutral candidate proposal. Cannot authorize formal promotion."""
    candidate_id: Text
    visual_medium_intent: VisualMediumIntent | None = None
    source_content: ProductionDesignContent
    source_fingerprint: Hash
    reconciliation: CastingReconciliation
    conditions: CastingTestConditions
    variation: Text
    status: Literal['PENDING_USER_REVIEW'] = 'PENDING_USER_REVIEW'
    formal_promotion_allowed: Literal[False] = False


class FactionRank(ContractModel):
    role: Text
    silhouette: Text
    materials: Text
    wear: Text
    layering: Text | None = None
    headwear: Text | None = None
    armor_construction: Text | None = None
    weapon_family: Text | None = None
    rank_signals: Text
    color_distribution: Text | None = None


class FactionVisualSystem(ContractModel):
    schema_version: Literal['faction-visual-v1'] = 'faction-visual-v1'
    faction: Text
    revision: Text
    shared_language: Text
    ranks: tuple[FactionRank, ...] = Field(min_length=1)
    contrasts_with_other_factions: tuple[Text, ...] = ()
    historical_constraints: HistoricalCanonPolicy = Field(default_factory=HistoricalCanonPolicy)

    @model_validator(mode='after')
    def real_hierarchy(self) -> Self:
        if len({r.role for r in self.ranks}) != len(self.ranks):
            raise ValueError('Duplicate faction role')
        if len(self.ranks)>1 and len({(r.silhouette,r.rank_signals) for r in self.ranks})==1:
            raise ValueError('Same costume with different faces is not rank hierarchy')
        return self


class LocationDesignSpec(ContractModel):
    schema_version: Literal['location-design-v1'] = 'location-design-v1'
    location: Text
    revision: Text
    space_purpose: Text
    spatial_hierarchy: Text
    entrance_exit: Text
    major_anchors: tuple[Text, ...] = Field(min_length=1)
    materials: Text
    wear_state: Text
    storytelling_state: Text
    population_state: Text | None = None
    weather_influence: Text | None = None
    light_sources: tuple[Text, ...] = ()
    foreground: Text
    midground: Text
    background: Text
    historical_constraints: HistoricalCanonPolicy = Field(default_factory=HistoricalCanonPolicy)


class VisualMotifSpec(ContractModel):
    schema_version: Literal['visual-motif-v1'] = 'visual-motif-v1'
    motif: Text
    revision: Text
    physical_form: Text
    serves: Literal['CHARACTER','THEME','PLOT','MEMORY']
    narrative_function: Text
    recurrence_change: Text
    avoid_decoration: Text
    historical_constraints: HistoricalCanonPolicy = Field(default_factory=HistoricalCanonPolicy)


DesignSpec = CharacterVisualSpec | FactionVisualSystem | LocationDesignSpec | LocationDesign | VisualMotifSpec


class ProductionDesignContent(ContractModel):
    creative_kind: Literal['CHARACTER_VISUAL_SPEC','FACTION_VISUAL_SYSTEM','LOCATION_DESIGN','VISUAL_MOTIF']
    semantic_key: Annotated[str, Field(pattern=r'^production-design/[a-z0-9/-]+$')]
    title: Text
    usage_mode: Literal['CANDIDATE','APPROVED_DESIGN'] = 'CANDIDATE'
    spec: DesignSpec
    provenance: Provenance
    validation: PatternValidation
    approval_evidence: Text | None = None
    stable_reuse_reason: Text

    @model_validator(mode='after')
    def typed_candidate(self) -> Self:
        expected={CharacterVisualSpec:'CHARACTER_VISUAL_SPEC',FactionVisualSystem:'FACTION_VISUAL_SYSTEM',LocationDesignSpec:'LOCATION_DESIGN',LocationDesign:'LOCATION_DESIGN',VisualMotifSpec:'VISUAL_MOTIF'}
        if expected[type(self.spec)]!=self.creative_kind:
            raise ValueError('Design kind differs from typed spec')
        if self.usage_mode=='APPROVED_DESIGN' and not self.approval_evidence:
            raise ValueError('Candidate cannot replace design without approval evidence')
        return self
