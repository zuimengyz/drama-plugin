"""Provider-neutral, source-pinned professional department artifacts.

These envelopes reuse the existing immutable Host artifact store; they are not
new Java entities and never contain an executable production job.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text
from drama_plugin.contracts.source_pin import SourcePin

ArtifactStatus = Literal['DRAFT', 'READY_FOR_REVIEW', 'APPROVED', 'NOT_REQUIRED']


class DepartmentDefinition(ContractModel):
    department_id: Text
    name: Text
    capability_type: Literal['SKILL', 'MODULE', 'VALIDATOR', 'AGGREGATOR']
    authority_scope: tuple[Text, ...]
    input_contract: Text = 'CreativeBible dependencies and pinned canonical sources'
    output_contract: Text
    depends_on: tuple[Text, ...] = ()
    consumed_by: tuple[Text, ...] = ()
    can_create: tuple[Text, ...]
    can_modify: tuple[Text, ...]
    cannot_modify: tuple[Text, ...]
    validator: Text = 'professional.validate_bible'
    version: Text = '1.0'
    skill_code: Text | None = None
    rationale: Text


class CreativeRecord(ContractModel):
    id: Text
    scope_refs: tuple[Text, ...] = Field(min_length=1)
    values: dict[str, Any]
    provenance: Literal['MIGRATED_FROM_R1', 'NEW_PROFESSIONAL_ELABORATION']
    source_refs: tuple[SourcePin, ...] = Field(min_length=1)
    status: Literal['DECIDED', 'UNRESOLVED', 'NOT_REQUIRED'] = 'DECIDED'
    limitations: tuple[Text, ...] = ()

    @model_validator(mode='after')
    def honest_record(self) -> Self:
        if not self.values:
            raise ValueError('EMPTY_PROFESSIONAL_RECORD')
        if self.status != 'DECIDED' and not self.limitations:
            raise ValueError('UNRESOLVED_OR_UNUSED_RECORD_REQUIRES_REASON')
        return self


class CreativeBible(ContractModel):
    schema_version: Literal['creative-bible-v1'] = 'creative-bible-v1'
    id: Text
    type: Text
    version: int = Field(default=1, ge=1)
    work_ref: Text
    script_ref: Text | None = None
    episode_ref: Text | None = None
    scene_refs: tuple[Text, ...] = ()
    shot_refs: tuple[Text, ...] = ()
    source_refs: tuple[SourcePin, ...] = Field(min_length=1)
    depends_on: tuple[SourcePin, ...] = ()
    status: ArtifactStatus = 'DRAFT'
    created_by_capability: Text
    approved_by: tuple[Text, ...] = ()
    approval_refs: tuple[SourcePin, ...] = ()
    content: tuple[CreativeRecord, ...] = ()
    continuity_refs: tuple[SourcePin, ...] = ()
    created_at: datetime
    updated_at: datetime
    not_required_reason: Text | None = None

    @model_validator(mode='after')
    def coherent(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError('INVALID_ARTIFACT_TIME')
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError('ARTIFACT_TIMESTAMPS_REQUIRE_TIMEZONE')
        if self.status == 'APPROVED' and (not self.approved_by or not self.approval_refs):
            raise ValueError('APPROVAL_IDENTITY_REQUIRED')
        if self.status != 'APPROVED' and (self.approved_by or self.approval_refs):
            raise ValueError('APPROVAL_ONLY_FOR_APPROVED_ARTIFACT')
        if self.status == 'NOT_REQUIRED':
            if not self.not_required_reason or any(r.status != 'NOT_REQUIRED' for r in self.content):
                raise ValueError('NOT_REQUIRED_NEEDS_REASON_AND_NO_ACTIVE_DESIGN')
        elif not self.content:
            raise ValueError('BIBLE_REQUIRES_PROFESSIONAL_CONTENT')
        if self.status == 'APPROVED' and any(r.status == 'UNRESOLVED' for r in self.content):
            raise ValueError('UNRESOLVED_DESIGN_NOT_READY')
        if len({r.id for r in self.content}) != len(self.content):
            raise ValueError('DUPLICATE_RECORD_ID')
        for refs in (self.source_refs, self.depends_on, self.continuity_refs):
            if len({r.key for r in refs}) != len(refs):
                raise ValueError('DUPLICATE_ARTIFACT_REFERENCE')
        return self


class SceneAssembly(ContractModel):
    schema_version: Literal['scene-assembly-v1'] = 'scene-assembly-v1'
    scene_id: Text
    work_ref: Text
    source_ref: SourcePin
    dramaturgy_ref: SourcePin
    characters: tuple[Text, ...]
    character_state_refs: tuple[SourcePin, ...] = ()
    environment_ref: SourcePin
    dialogue_refs: tuple[SourcePin, ...]
    department_refs: dict[str, SourcePin]


class ShotAssembly(ContractModel):
    schema_version: Literal['shot-assembly-v1'] = 'shot-assembly-v1'
    shot_id: Text
    scene_ref: Text
    work_ref: Text
    source_ref: SourcePin
    dramatic_purpose: Text
    subjects: tuple[Text, ...]
    start_state: Text
    end_state: Text
    department_refs: dict[str, SourcePin]
    generation_clip_refs: tuple[SourcePin, ...] = ()


class DirectorPackage(ContractModel):
    schema_version: Literal['director-package-v1'] = 'director-package-v1'
    id: Text
    version: int = Field(default=1, ge=1)
    work_ref: Text
    script_ref: Text | None = None
    episode_ref: Text | None = None
    source_refs: tuple[SourcePin, ...] = Field(min_length=1)
    bible_refs: dict[str, SourcePin]
    scene_assembly_refs: tuple[SourcePin, ...]
    shot_assembly_refs: tuple[SourcePin, ...]
    status: ArtifactStatus = 'READY_FOR_REVIEW'
    approved_by: tuple[Text, ...] = ()
    approval_refs: tuple[SourcePin, ...] = ()
    created_at: datetime
    updated_at: datetime

    @model_validator(mode='after')
    def approval(self) -> Self:
        if (self.status == 'APPROVED') != bool(self.approved_by and self.approval_refs):
            raise ValueError('PACKAGE_APPROVAL_IDENTITY_MISMATCH')
        if self.status != 'APPROVED' and (self.approved_by or self.approval_refs):
            raise ValueError('PACKAGE_APPROVAL_ONLY_FOR_APPROVED_STATUS')
        if self.updated_at < self.created_at or self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError('INVALID_PACKAGE_TIMESTAMPS')
        return self


class ContinuityState(ContractModel):
    entity: Text
    domain: Text
    property: Text
    state: Text | dict[str, Any]
    effective_from: Text
    effective_until: Text | None = None
    effective_from_event: Text | None = None
    effective_until_event: Text | None = None
    effective_from_phase: Literal['BEFORE', 'AFTER', 'INCLUSIVE'] | None = None
    effective_until_phase: Literal['BEFORE', 'AFTER', 'INCLUSIVE'] | None = None
    effective_until_shot_ref: Text | None = None
    changed_by: SourcePin
    scene_ref: Text
    shot_ref: Text | None = None
    predecessor: Text | None = None
    restored: bool = False
    restoration_ref: SourcePin | None = None
    owner_record_id: Text
    owner_state_path: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def restoration(self) -> Self:
        if not self.state:
            raise ValueError('CONTINUITY_STATE_CANNOT_BE_EMPTY')
        if self.restored and (not self.predecessor or not self.restoration_ref or not self.owner_record_id or not self.owner_state_path):
            raise ValueError('CONTINUITY_RESTORATION_REQUIRES_OWNED_EVIDENCE')
        if not self.restored and self.restoration_ref:
            raise ValueError('RESTORATION_REF_WITHOUT_RESTORATION')
        return self


class EntityIdentity(ContractModel):
    entity_id: Text
    name: Text
    entity_type: Text
    historical_status: Literal['DOCUMENTED', 'PLAUSIBLE_INFERENCE', 'DRAMATIC_RECONSTRUCTION', 'UNRESOLVED', 'EXCLUDED_WITH_REASON']
    identity_kind: Literal['HISTORICAL_PERSON', 'ORIGINAL', 'COMPOSITE', 'PLACE', 'ARMY', 'ANIMAL', 'OBJECT', 'TITLE', 'UNRESOLVED']
    historical_identity_ref: Text | None = None
    evidence_refs: tuple[SourcePin, ...]
    distinct_from: tuple[Text, ...] = ()

    @model_validator(mode='after')
    def identity_boundary(self) -> Self:
        if self.identity_kind in ('ORIGINAL', 'COMPOSITE') and (
            self.historical_identity_ref or self.historical_status == 'DOCUMENTED'
        ):
            raise ValueError('FICTIONAL_IDENTITY_CANNOT_RESOLVE_TO_HISTORICAL_PERSON')
        if self.historical_status == 'DOCUMENTED' and not self.evidence_refs:
            raise ValueError('DOCUMENTED_IDENTITY_REQUIRES_EVIDENCE')
        if self.historical_identity_ref in self.distinct_from:
            raise ValueError('EXCLUDED_IDENTITY_MATCH')
        return self
