from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from drama_plugin.contracts.base import ContractModel


NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PerformanceLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DPDLayerState(ContractModel):
    """Sparse inheritable direction values; missing and null both inherit."""

    objective: NonBlankText | None = None
    interaction_target: NonBlankText | None = None
    tactic: NonBlankText | None = None
    authority_position: NonBlankText | None = None
    relationship_stance: NonBlankText | None = None
    internal_activation: PerformanceLevel | None = None
    external_control: PerformanceLevel | None = None
    public_private_context: NonBlankText | None = None
    subtext: NonBlankText | None = None
    performance_boundaries: tuple[NonBlankText, ...] | None = None

    @model_validator(mode="after")
    def reject_empty_patch(self) -> "DPDLayerState":
        if not self.model_fields_set:
            raise ValueError("DPD layer state must set at least one field")
        return self


class SceneDPD(ContractModel):
    schema_version: Literal["dpd-v1"] = "dpd-v1"
    scope: Literal["SCENE"] = "SCENE"
    scene_id: NonBlankText
    source_fingerprint: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    dramatic_purpose: NonBlankText
    conflict_condition: NonBlankText
    power_structure: NonBlankText
    emotional_climate: NonBlankText | None = None
    urgency_context: NonBlankText | None = None
    information_asymmetry: NonBlankText | None = None
    social_constraints: tuple[NonBlankText, ...] = ()
    direction: DPDLayerState

    @model_validator(mode="after")
    def require_scene_context(self) -> "SceneDPD":
        if self.direction.public_private_context is None:
            raise ValueError("Scene DPD requires publicPrivateContext")
        return self


class BeatDPD(ContractModel):
    schema_version: Literal["dpd-v1"] = "dpd-v1"
    scope: Literal["BEAT"] = "BEAT"
    scene_id: NonBlankText
    beat_id: NonBlankText
    actor: NonBlankText
    obstacle: NonBlankText
    transition_trigger: NonBlankText
    direction: DPDLayerState


class LineDPD(ContractModel):
    schema_version: Literal["dpd-v1"] = "dpd-v1"
    scope: Literal["LINE"] = "LINE"
    scene_id: NonBlankText
    beat_id: NonBlankText
    spoken_content_id: NonBlankText
    speaker: NonBlankText
    dramatic_action: NonBlankText
    observable_intent: NonBlankText
    continuity: NonBlankText
    change_from_previous: NonBlankText
    direction: DPDLayerState | None = None


class EffectiveDPD(ContractModel):
    schema_version: Literal["dpd-effective-v1"] = "dpd-effective-v1"
    scene_id: NonBlankText
    beat_id: NonBlankText
    spoken_content_id: NonBlankText
    actor: NonBlankText
    speaker: NonBlankText
    dramatic_purpose: NonBlankText
    conflict_condition: NonBlankText
    power_structure: NonBlankText
    emotional_climate: NonBlankText | None = None
    urgency_context: NonBlankText | None = None
    information_asymmetry: NonBlankText | None = None
    social_constraints: tuple[NonBlankText, ...] = ()
    objective: NonBlankText
    interaction_target: NonBlankText
    tactic: NonBlankText
    authority_position: NonBlankText
    relationship_stance: NonBlankText
    internal_activation: PerformanceLevel
    external_control: PerformanceLevel
    public_private_context: NonBlankText
    subtext: NonBlankText | None = None
    performance_boundaries: tuple[NonBlankText, ...] = ()
    obstacle: NonBlankText
    transition_trigger: NonBlankText
    dramatic_action: NonBlankText
    observable_intent: NonBlankText
    continuity: NonBlankText
    change_from_previous: NonBlankText


class DPDSnapshot(ContractModel):
    schema_version: Literal["dpd-snapshot-v1"] = "dpd-snapshot-v1"
    scene: SceneDPD
    beat: BeatDPD
    line: LineDPD
    effective: EffectiveDPD
    fingerprint: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
