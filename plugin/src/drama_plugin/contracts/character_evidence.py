"""Explicit identity and scene evidence; labels never perform entity matching."""
from __future__ import annotations
from typing import Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text

EvidenceStatus = Literal['DOCUMENTED', 'PLAUSIBLE_INFERENCE', 'DRAMATIC_RECONSTRUCTION', 'UNRESOLVED']


class ScopedHistoricalEvidence(ContractModel):
    source_ref: Text
    claim: Text
    scope: Literal['IDENTITY', 'SCENE_PLACEMENT', 'ACTION', 'DESIGN']
    evidence_status: EvidenceStatus
    scene_ref: Text | None = None
    limitation: Text

    @model_validator(mode='after')
    def scoped(self) -> Self:
        if self.scope in {'SCENE_PLACEMENT', 'ACTION'} and not self.scene_ref:
            raise ValueError('Scene evidence requires an exact scene reference')
        return self


class CharacterScenePlacement(ContractModel):
    scene_id: Text
    evidence_status: EvidenceStatus
    source_basis: tuple[ScopedHistoricalEvidence, ...] = ()
    fictionalization_boundary: Text

    @model_validator(mode='after')
    def placement_evidence(self) -> Self:
        if any(b.scene_ref != self.scene_id or b.scope != 'SCENE_PLACEMENT' for b in self.source_basis):
            raise ValueError('Placement evidence must address this exact scene placement')
        if self.evidence_status == 'DOCUMENTED' and not any(b.evidence_status == 'DOCUMENTED' for b in self.source_basis):
            raise ValueError('Documented placement requires scene-specific documented evidence')
        return self


class CharacterEvidence(ContractModel):
    historical_status: EvidenceStatus
    identity_kind: Literal['HISTORICAL_PERSON', 'ORIGINAL', 'COMPOSITE', 'UNRESOLVED']
    source_basis: tuple[ScopedHistoricalEvidence, ...] = ()
    dramatic_function: tuple[Text, ...] = Field(min_length=1)
    historical_authority: bool
    fictionalization_boundary: Text
    scene_refs: tuple[Text, ...] = Field(min_length=1)
    scene_placements: tuple[CharacterScenePlacement, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def explicit_identity_and_placement(self) -> Self:
        if len(set(self.scene_refs)) != len(self.scene_refs) or {p.scene_id for p in self.scene_placements} != set(self.scene_refs) or len(self.scene_placements) != len(self.scene_refs):
            raise ValueError('Each character scene needs one explicit placement assessment')
        if self.historical_status == 'DOCUMENTED' and self.identity_kind != 'HISTORICAL_PERSON':
            raise ValueError('Documented identity must explicitly be a historical person')
        if self.historical_status == 'DOCUMENTED' and not any(b.scope == 'IDENTITY' and b.evidence_status == 'DOCUMENTED' for b in self.source_basis):
            raise ValueError('Documented identity requires identity evidence')
        fictional = self.identity_kind in {'ORIGINAL', 'COMPOSITE'}
        if fictional and self.historical_status != 'DRAMATIC_RECONSTRUCTION':
            raise ValueError('Original/composite identity remains dramatic reconstruction')
        if self.historical_status == 'DRAMATIC_RECONSTRUCTION' and (self.historical_authority or self.identity_kind == 'HISTORICAL_PERSON'):
            raise ValueError('Reconstruction identity cannot acquire historical authority')
        if self.historical_authority and self.historical_status != 'DOCUMENTED':
            raise ValueError('Historical authority requires documented identity')
        if fictional and (any(p.evidence_status == 'DOCUMENTED' for p in self.scene_placements) or any(b.scope == 'IDENTITY' and b.evidence_status == 'DOCUMENTED' for b in self.source_basis)):
            raise ValueError('Fictional identity cannot claim documented identity or placement')
        return self


class DocumentedSceneActor(ContractModel):
    character_identity: Text
    scene_id: Text
    historical_action: Text
    source_basis: tuple[ScopedHistoricalEvidence, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def documented_actor(self) -> Self:
        if not any(b.scene_ref == self.scene_id and b.scope in {'SCENE_PLACEMENT', 'ACTION'} and b.evidence_status == 'DOCUMENTED' for b in self.source_basis):
            raise ValueError('Coverage actor requires documented evidence for this scene')
        return self


class CharacterCoverageDecision(ContractModel):
    character_identity: Text
    scene_id: Text
    decision: Literal['INCLUDE', 'EXCLUDE_WITH_REASON', 'UNRESOLVED']
    reason: Text


class CharacterCoverageReview(ContractModel):
    scene_refs: tuple[Text, ...] = Field(min_length=1)
    documented_scene_actors: tuple[DocumentedSceneActor, ...]
    decisions: tuple[CharacterCoverageDecision, ...]
    inventory_basis: Text

    @model_validator(mode='after')
    def evaluates_evidence_not_headcount(self) -> Self:
        actors = [(a.character_identity, a.scene_id) for a in self.documented_scene_actors]
        decisions = [(d.character_identity, d.scene_id) for d in self.decisions]
        if len(set(actors)) != len(actors) or len(set(decisions)) != len(decisions) or set(actors) != set(decisions):
            raise ValueError('Every documented scene actor needs exactly one coverage decision')
        if not {s for _, s in actors} <= set(self.scene_refs):
            raise ValueError('Coverage actor lies outside reviewed scenes')
        return self
