"""Immutable production sidecars; no persistence entity or approval authority."""
from __future__ import annotations
from typing import Literal, Self
from pydantic import ConfigDict, Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Hash, Text


class FrozenContract(ContractModel):
    model_config = ConfigDict(frozen=True)


class CinematicStylizationPolicy(FrozenContract):
    historical_plausibility: Text
    screen_idealization: Text
    realism: Text
    leading_character_attractiveness: Text
    age_treatment: Text
    body_idealization: Text
    beauty_direction: Text
    forbidden_drifts: tuple[Text, ...] = Field(min_length=1)


class FreezeEntry(FrozenContract):
    role: Literal['CHARACTER', 'COSTUME', 'FACTION', 'LOCATION', 'PROP', 'MOUNT', 'LIVING_ASSET']
    semantic_key: Text
    requirement: Literal['REQUIRED', 'OPTIONAL']
    requires_visual_media: bool
    asset_id: Text | None = None
    media_id: Text | None = None
    media_content_hash: Hash | None = None
    content_fingerprint: Hash | None = None
    approval_status: Literal['USER_APPROVED', 'CANDIDATE', 'PENDING_USER_REVIEW', 'PROJECT_DERIVED', 'REJECTED', 'UNKNOWN']
    approval_evidence: Text | None = None
    reference_duty: Text
    scope: Text
    revision: Text
    source_lineage: tuple[Text, ...] = Field(min_length=1)


class ProductionDesignFreeze(FrozenContract):
    schema_version: Literal['production-design-freeze-v1'] = 'production-design-freeze-v1'
    snapshot_id: Text
    scope: Text
    revision: Text
    stylization: CinematicStylizationPolicy
    entries: tuple[FreezeEntry, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def identities(self) -> Self:
        keys = [e.semantic_key for e in self.entries]
        if len(keys) != len(set(keys)) or any(e.scope != self.scope for e in self.entries):
            raise ValueError('Duplicate or wrong-scope freeze entry')
        return self


class FreezeReference(FrozenContract):
    snapshot_id: Text
    fingerprint: Hash
