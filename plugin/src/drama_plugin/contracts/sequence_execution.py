"""Executable detail attached to existing Sequence receivers and Bible indexes."""
from __future__ import annotations
from typing import Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text


class AcceptanceCriterion(ContractModel):
    key: Text
    observation: Text
    result: Literal['PASS', 'PARTIAL', 'FAIL', 'UNKNOWN'] = 'UNKNOWN'
    evidence_ref: Text | None = None

    @model_validator(mode='after')
    def observed(self) -> Self:
        if self.result != 'UNKNOWN' and not self.evidence_ref:
            raise ValueError('Observed acceptance verdict requires evidence')
        return self


class ReferenceDuty(ContractModel):
    key: Text
    role: Literal['CHARACTER', 'COSTUME', 'FACTION', 'LOCATION', 'PROP', 'MOUNT', 'LIVING_ASSET']
    requirement: Literal['REQUIRED', 'OPTIONAL', 'NOT_APPLICABLE']
    freeze_entry_key: Text | None = None
    reason: Text

    @model_validator(mode='after')
    def traced(self) -> Self:
        if self.requirement == 'REQUIRED' and not self.freeze_entry_key:
            raise ValueError('Required duty must trace to freeze entry')
        return self


class MountInteraction(ContractModel):
    identity: Text
    scale: Text
    appearance: Text
    tack_bridle_saddle: Text
    rider_relationship: Text
    orientation: Text
    gait: Text
    rider_contact: Text
    terrain_contact: Text
    other_mount_contact: Text
    mud: Text
    sweat: Text
    injury: Text
    equipment: Text


class ActionChoreographyBeat(ContractModel):
    key: Text
    actor: Text
    target: Text
    approach_direction: Text
    body_orientation: Text
    mount_orientation: Text | None = None
    weapon_state: Text
    contact: Text
    force_motion_direction: Text
    target_reaction: Text
    mount_reaction: Text | None = None
    spatial_result: Text
    follower_opportunity: Text
    continuity_consequence: Text

    @model_validator(mode='after')
    def mount_consequence(self) -> Self:
        if bool(self.mount_orientation) != bool(self.mount_reaction):
            raise ValueError('Mounted action needs orientation and reaction together')
        return self


class AudioBridgeObligation(ContractModel):
    dialogue_carry: Text
    native_action_carry: Text
    ambience_continuity: Text
    intentional_silence: Text
    audio_cut: Text
    jl_carry_candidate: Text
    execution_status: Literal['PENDING_FINISHING'] = 'PENDING_FINISHING'
    reference_audio_evidence: Literal['UNKNOWN'] = 'UNKNOWN'


class ProductionClip(ContractModel):
    purpose: Text
    visual_information_beat: Text
    blocking: Text
    choreography: tuple[ActionChoreographyBeat, ...] = Field(min_length=1)
    camera: Text
    # These are Bible keys. Formal Asset/Media IDs are obtained through the seal.
    asset_refs: tuple[Text, ...] = Field(min_length=1)
    reference_duties: tuple[ReferenceDuty, ...] = Field(min_length=1)
    audio_bridge: AudioBridgeObligation
    edit_boundary: Text
    generation_group: Text
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = Field(min_length=1)
    fallback_plan: Text

    @model_validator(mode='after')
    def unique_duties(self) -> Self:
        if len({d.key for d in self.reference_duties}) != len(self.reference_duties):
            raise ValueError('Duplicate reference duty')
        return self
