"""Reusable environments owned by production-design, with bounded scene deltas."""
from __future__ import annotations
from typing import Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.contracts.character_evidence import EvidenceStatus, ScopedHistoricalEvidence


class LocationDesign(ContractModel):
    schema_version: Literal['location-design-v2'] = 'location-design-v2'
    id: Text
    name: Text
    revision: Text
    location_type: Text
    scene_refs: tuple[Text, ...] = Field(min_length=1)
    parent_location_id: Text | None = None
    historical_basis: tuple[ScopedHistoricalEvidence, ...] = Field(min_length=1)
    evidence_status: EvidenceStatus
    uncertainties: tuple[Text, ...]
    dramatic_function: Text
    macro_geography: Text
    terrain: Text
    ground_condition: Text
    architecture_or_structures: Text
    fortification_or_boundary: Text
    zone_layout: dict[str, Text] = Field(min_length=1)
    landmarks: dict[str, Text] = Field(min_length=1)
    entrances: tuple[Text, ...]
    exits: tuple[Text, ...]
    movement_routes: dict[str, tuple[Text, ...]] = Field(min_length=1)
    line_of_sight: tuple[Text, ...] = Field(min_length=1)
    scale_and_density: Text
    human_activity: Text
    military_logistics_if_applicable: Text | None = None
    materials: tuple[Text, ...] = Field(min_length=1)
    surface_texture: Text
    prop_families: tuple[Text, ...]
    time_of_day: Text
    weather: Text
    light_sources: tuple[Text, ...] = Field(min_length=1)
    lighting_behavior: Text
    color_environment: Text
    camera_affordances: tuple[Text, ...] = Field(min_length=1)
    blocking_affordances: tuple[Text, ...] = Field(min_length=1)
    action_constraints: tuple[Text, ...] = Field(min_length=1)
    acoustic_character: Text
    sound_sources: tuple[Text, ...]
    continuity_anchors: tuple[Text, ...] = Field(min_length=1)
    phase_ii_visual_requirements: tuple[Text, ...] = Field(min_length=1)
    forbidden_assumptions: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def navigable(self) -> Self:
        if len(set(self.scene_refs)) != len(self.scene_refs):
            raise ValueError('Duplicate location scene reference')
        if self.parent_location_id == self.id:
            raise ValueError('Location cannot be its own parent')
        zones = set(self.zone_layout)
        referenced = set(self.entrances) | set(self.exits)
        for route in self.movement_routes.values():
            if len(route) < 2:
                raise ValueError('Movement route needs at least two zones')
            referenced.update(route)
        if not referenced <= zones:
            raise ValueError('Environment route/entrance/exit refers to an unknown zone')
        if self.evidence_status == 'DOCUMENTED' and not any(b.evidence_status == 'DOCUMENTED' for b in self.historical_basis):
            raise ValueError('Documented environment requires documented basis')
        return self


class LocationDesignRef(ContractModel):
    location_id: Text
    artifact_ref: SourcePin


class SceneLocationOverride(ContractModel):
    """Transient state only. Geography/layout require a new base revision."""
    time_of_day: Text | None = None
    weather: Text | None = None
    light_sources: tuple[Text, ...] | None = None
    population_change: Text | None = None
    ground_change: Text | None = None
    damage_change: Text | None = None
    temporary_obstacles: tuple[Text, ...] | None = None
    change_reason: Text
    continuity_note: Text


class SceneLocationBinding(ContractModel):
    location_ref: LocationDesignRef
    local_override: SceneLocationOverride | None = None
