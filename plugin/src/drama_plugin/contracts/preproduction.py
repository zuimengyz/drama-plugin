"""Source-bound preproduction sidecars; no business entities or approval authority.

Readiness belongs to incubation; film/scene design to production-design;
lighting to cinematic-direction; the Director packet indexes, never copies them.
"""
from __future__ import annotations
from typing import Any, Literal, Self
from pydantic import Field, model_validator, model_serializer, SerializerFunctionWrapHandler
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text
from drama_plugin.contracts.sequence import SourcePin
from drama_plugin.contracts.production_design import HistoricalCanonPolicy, CharacterState, LocationDesignSpec
from drama_plugin.contracts.visual_route import VisualRoute
from drama_plugin.contracts.location_design import LocationDesignRef, SceneLocationBinding
from drama_plugin.contracts.director import DirectorRuntimeEstimate

READINESS_DIMENSIONS = frozenset({
    'historical_causality', 'narrative_spine', 'protagonist_decision_arc', 'character_arc',
    'human_stakes', 'emotional_counterline', 'internal_external_conflict', 'scene_variety',
    'scene_necessity', 'setup_payoff', 'dialogue', 'literary_opportunity', 'action_drama_balance',
    'climax_architecture', 'ending_weight', 'audience_knowledge'})


class ReadinessFinding(ContractModel):
    dimension: Text
    verdict: Literal['PASS', 'NOTE', 'MAJOR', 'UNKNOWN', 'NA']
    evidence: tuple[Text, ...] = Field(min_length=1)
    reason: Text
    revision_scope: Text | None = None

    @model_validator(mode='after')
    def actionable(self) -> Self:
        if self.verdict in {'MAJOR', 'UNKNOWN'} and not self.revision_scope:
            raise ValueError('Unresolved readiness needs an upstream repair scope')
        return self


class DramaticAffordance(ContractModel):
    opportunity: Text
    source_refs: tuple[Text, ...] = Field(min_length=1)
    evidence_limit: Text
    thematic_relevance: Text
    decision: Literal['INCLUDE', 'EXCLUDE_WITH_REASON', 'UNRESOLVED']
    reason: Text
    significant: bool = True


class ScreenplayReadinessReview(ContractModel):
    scope_id: Text
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    revision: Text
    findings: tuple[ReadinessFinding, ...] = Field(min_length=1)
    human_stakes_carrier: Text | None = None
    emotional_counterline: Text | None = None
    repeated_scene_pattern: Text | None = None
    pattern_dramatic_progression: Text | None = None
    affordances: tuple[DramaticAffordance, ...] = ()
    affordance_audit: Text
    historical: bool = True

    @model_validator(mode='after')
    def full_review(self) -> Self:
        keys = [f.dimension for f in self.findings]
        if len(set(keys)) != len(keys) or set(keys) != READINESS_DIMENSIONS:
            raise ValueError('Readiness must address each dimension exactly once; never average scores')
        if len({p.key for p in self.source_pins}) != len(self.source_pins):
            raise ValueError('Duplicate readiness source')
        return self


class StylizationReview(ContractModel):
    route: VisualRoute
    canon: HistoricalCanonPolicy
    hard_invariants: tuple[Text, ...] = Field(min_length=1)
    soft_realization: tuple[Text, ...] = Field(min_length=1)
    expression_freedom: tuple[Text, ...] = Field(min_length=1)
    quality_evidence: dict[str, Text] = Field(min_length=1)
    violations: tuple[Text, ...] = ()
    review_basis: Literal['TEXT_DESIGN_ONLY'] = 'TEXT_DESIGN_ONLY'
    cg_policy_applied: bool

    @model_validator(mode='after')
    def route_isolation(self) -> Self:
        if self.cg_policy_applied != (self.route == 'stylized_cinematic_cg'):
            raise ValueError('CG stylization policy must not leak into live action')
        required = {'hierarchy', 'material_coherence', 'depth', 'character_distinction',
                    'lighting_compatibility', 'composition', 'readability'}
        if set(self.quality_evidence) != required:
            raise ValueError('Cinematic quality requires evidence in every dimension')
        return self


class ColorKey(ContractModel):
    scene_id: Text
    hue_family: Text
    warm_cool: Text
    saturation: Text
    value: Text
    contrast: Text
    character_separation: Text
    dramatic_function: Text
    continuity_in: Text
    continuity_out: Text


class FilmProductionDesign(ContractModel):
    location_design_refs: tuple[LocationDesignRef, ...] | None = None
    character_visual_refs: tuple[SourcePin, ...] | None = None
    character_coverage_ref: SourcePin | None = None

    @model_serializer(mode='wrap')
    def preserve_legacy_wire(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        for field in ('location_design_refs', 'character_visual_refs', 'character_coverage_ref'):
            if getattr(self, field) is None:
                data.pop(field, None)
                alias = type(self).model_fields[field].alias
                if alias is not None:
                    data.pop(alias, None)
        return data

    scope_id: Text
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    intent_ref: SourcePin
    route: VisualRoute
    visual_bible_ref: SourcePin
    stylization: StylizationReview
    style_position: Text
    environment_architecture: Text
    materials: Text
    costume_armor: Text
    props: Text
    crowd_army: Text
    weather: Text
    daytime_strategy: Text
    dirt_damage: Text
    motifs: Text
    visual_hierarchy: Text
    color_script: tuple[ColorKey, ...] = Field(min_length=1)
    costume_bible_refs: tuple[SourcePin, ...] = Field(min_length=1)
    prop_design_refs: tuple[SourcePin, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def coherent_route(self) -> Self:
        if self.location_design_refs is not None:
            if not self.location_design_refs or len({r.location_id for r in self.location_design_refs}) != len(self.location_design_refs) or len({r.artifact_ref.key for r in self.location_design_refs}) != len(self.location_design_refs):
                raise ValueError('Film requires unique nonempty reusable location references')
        if self.character_visual_refs is not None and (not self.character_visual_refs or len({r.key for r in self.character_visual_refs}) != len(self.character_visual_refs)):
            raise ValueError('Film requires unique nonempty character references')
        if (self.character_visual_refs is None) != (self.character_coverage_ref is None):
            raise ValueError('Character evidence opt-in requires both character inventory and coverage review')
        if self.route != self.stylization.route:
            raise ValueError('Style review belongs to another route')
        if len({c.scene_id for c in self.color_script}) != len(self.color_script):
            raise ValueError('Duplicate scene color key')
        return self


class CostumeBible(ContractModel):
    character_identity: Text
    visual_spec_ref: SourcePin
    status_class: Text
    faction: Text
    silhouette: Text
    layers: Text
    armor: Text
    materials: Text
    colors: Text
    ornament: Text
    hero_support_hierarchy: Text
    historical_plausibility: Text
    stylization_boundary: Text
    occupation_movement_wear: Text


class CostumeState(CharacterState):
    """Refines the existing transient CharacterState, never the stable costume."""
    bible_ref: SourcePin
    previous_state_ref: SourcePin | None = None
    costume: Text
    armor: Text
    equipment: tuple[Text, ...]
    dirt: Text
    dust: Text
    water: Text
    sweat: Text
    damage: Text
    missing_equipment: tuple[Text, ...] = ()
    blood: Text
    continuity_in: Text
    continuity_out: Text
    change_causes: dict[str, Text] = Field(default_factory=dict)


class PropDesign(ContractModel):
    key: Text
    category: Literal['HERO', 'FUNCTIONAL', 'ENVIRONMENT', 'HISTORICAL']
    function: Text
    relationship: Text
    material: Text
    scale: Text
    wear: Text
    interaction: Text
    continuity: Text
    historical_basis: Text


class SceneProductionDesignPacket(ContractModel):
    scene_id: Text
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    film_design_ref: SourcePin
    location: LocationDesignSpec | None = None
    environment_refs: tuple[SceneLocationBinding, ...] | None = None
    geography_terrain: Text
    zones: dict[str, Text] = Field(min_length=1)
    paths: dict[str, tuple[Text, Text]] = Field(min_length=1)
    entrances_exits: tuple[Text, ...] = Field(min_length=1)
    power_center: Text
    key_props: dict[str, Text] = Field(min_length=1)
    character_start_end: dict[str, tuple[Text, Text]] = Field(min_length=1)
    crowd_density: Text
    weather_atmosphere: Text
    daytime: Text
    material_priority: Text
    color_key: ColorKey
    practical_sources: dict[str, Text] = Field(min_length=1)
    camera_zones: tuple[Text, ...] = Field(min_length=1)
    sound_zones: dict[str, Text] = Field(min_length=1)
    continuity_previous: Text
    continuity_next: Text
    costume_state_refs: tuple[SourcePin, ...] = Field(min_length=1)
    visual_development_brief: Text

    @model_serializer(mode='wrap')
    def preserve_legacy_wire(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if self.environment_refs is None:
            data.pop('environment_refs', None)
            data.pop('environmentRefs', None)
        if self.location is None:
            data.pop('location', None)
        return data

    @model_validator(mode='after')
    def usable_layout(self) -> Self:
        if (self.location is None) == (self.environment_refs is None):
            raise ValueError('Scene requires either legacy location or reusable environment references')
        if self.environment_refs is not None and (not self.environment_refs or len({r.location_ref.location_id for r in self.environment_refs}) != len(self.environment_refs)):
            raise ValueError('Scene requires unique nonempty environment references')
        referenced = set(self.entrances_exits) | set(self.camera_zones) | {self.power_center}
        referenced |= {z for path in self.paths.values() for z in path}
        referenced |= {z for pair in self.character_start_end.values() for z in pair}
        referenced |= set(self.key_props.values()) | set(self.sound_zones) | set(self.practical_sources.values())
        if not referenced <= set(self.zones):
            raise ValueError('Layout contains an unknown zone')
        if self.color_key.scene_id != self.scene_id:
            raise ValueError('Color key belongs to another scene')
        return self


class LightingScript(ContractModel):
    scene_id: Text
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    scene_design_ref: SourcePin
    intent: Text
    motivated_sources: tuple[Text, ...] = Field(min_length=1)
    key_direction: Text
    fill: Text
    contrast: Text
    value_hierarchy: Text
    character_readability: Text
    background_separation: Text
    practicals: Text
    atmosphere: Text
    daytime_logic: Text
    color_relationship: Text
    continuity_in: Text
    continuity_out: Text
    cg_risks: Text | None = None
    camera_philosophy: Text
    dominant_scale: Text
    height_logic: Text
    lens_family: Text
    movement: Text
    depth: Text
    axis: Text
    hero_restraint: Text
    environment_framing: Text


class DepartmentEntry(ContractModel):
    department: Literal['film_design', 'scene_design', 'costume', 'lighting', 'performance', 'coverage', 'sound']
    scope_id: Text
    owner: Literal['production-design', 'cinematic-direction', 'dramatic-performance-direction', 'shot-design']
    artifact_ref: SourcePin
    intent_ref: SourcePin
    summary: Text


class DepartmentConflict(ContractModel):
    code: Text
    subject_refs: tuple[SourcePin, ...] = Field(min_length=2)
    evidence: Text
    repair_owner: Literal['production-design', 'cinematic-direction', 'dramatic-performance-direction', 'shot-design', 'cinematic-screenplay-incubation', 'music-direction', 'director']
    severity: Literal['MAJOR', 'NOTE'] = 'MAJOR'
    resolved_by: SourcePin | None = None


class DirectorDepartmentPacket(ContractModel):
    expected_runtime: DirectorRuntimeEstimate | None = None
    scope_id: Text
    scene_ids: tuple[Text, ...] = Field(min_length=1)
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    route_ref: SourcePin
    intent_ref: SourcePin
    readiness_ref: SourcePin
    entries: tuple[DepartmentEntry, ...]
    conflicts: tuple[DepartmentConflict, ...] = ()
    sequence_transition_refs: tuple[SourcePin, ...] = ()
    self_review_ref: SourcePin | None = None
    mode: Literal['DESIGN_ONLY'] = 'DESIGN_ONLY'

    @model_validator(mode='after')
    def no_parallel_truth(self) -> Self:
        keys = [(e.department, e.scope_id) for e in self.entries]
        if len(set(keys)) != len(keys) or len(set(self.scene_ids)) != len(self.scene_ids):
            raise ValueError('Duplicate department or scene')
        owners = {'film_design': 'production-design', 'scene_design': 'production-design',
                  'costume': 'production-design', 'lighting': 'cinematic-direction',
                  'performance': 'dramatic-performance-direction', 'coverage': 'shot-design',
                  'sound': 'cinematic-direction'}
        for e in self.entries:
            if e.owner != owners[e.department] or e.intent_ref != self.intent_ref:
                raise ValueError('Department ownership or Director intent mismatch')
            if e.scope_id != (self.scope_id if e.department == 'film_design' else e.scope_id) or (
                e.department != 'film_design' and e.scope_id not in self.scene_ids):
                raise ValueError('Department scope mismatch')
        return self
