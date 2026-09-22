"""Creative-source IR. SOURCE, interpretation and adaptation have distinct owners.

Rights assertions are supplied evidence, never a legal inference from author dates.
No provider controls or generated screenplay text belong to this upstream contract.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal
from pydantic import Field
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash
from drama_plugin.contracts.source_pin import SourcePin

CreativeSourceType = Literal['HISTORICAL', 'LITERARY']
Origin = Literal['SOURCE_FACT', 'INTERPRETATION', 'ADAPTATION_INVENTION']
Operation = Literal['KEEP', 'MERGE', 'COMPRESS', 'REMOVE', 'REORDER', 'EXTERNALIZE', 'ADD', 'ADAPT_DIALOGUE', 'SIMPLIFY']
Stage = Literal['literary-source-analysis', 'philosophical-core', 'literary-adaptation', 'literature-to-cinema', 'character-dramaturgy']
Channel = Literal['CHARACTER_CHOICE', 'ACTION', 'CONSEQUENCE', 'PERFORMANCE', 'SPATIAL_RELATION', 'OBJECT_MOTIF', 'VISUAL_COMPOSITION', 'SOUND', 'SILENCE', 'DIALOGUE', 'EXPLICIT_EXPLANATION', 'REACTION', 'BLOCKING', 'GAZE', 'TIMING', 'ENVIRONMENT', 'OFFSCREEN_SOUND', 'MONTAGE', 'SCENE_TRANSITION', 'VOICE_OVER']


class RightsAssertion(ContractModel):
    status: Literal['PUBLIC_DOMAIN', 'LICENSED', 'USER_OWNED', 'UNKNOWN', 'RESTRICTED']
    jurisdictions: tuple[Text, ...] = ()
    evidence: tuple[Text, ...] = ()
    asserted_by: Text | None = None
    basis: Literal['USER_CONFIRMATION', 'VERIFIED_EXTERNAL_INFORMATION', 'LICENSE_METADATA', 'PROVENANCE_RECORD'] | None = None
    # Exact declared uses; no scope is inherited from an original or another edition.
    permitted_uses: tuple[Literal['ADAPTATION', 'COMMERCIAL_PRODUCTION'], ...] = ()
    license_scope: Text | None = None


class SourceArtifact(ContractModel):
    id: Text
    title: Text
    kind: Literal['ORIGINAL_TEXT', 'TRANSLATION', 'EDITION', 'ADAPTATION', 'FILM_REFERENCE', 'AUDIO_SOURCE']
    role: Literal['SOURCE_OF_TRUTH', 'NON_COPYING_REFERENCE']
    provenance: Text
    text: Text
    text_sha256: Hash
    rights: RightsAssertion
    derived_from: Text | None = None


class SourceAnchor(ContractModel):
    id: Text
    artifact_id: Text
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: Text


class SourceUnit(ContractModel):
    id: Text
    kind: Literal['CHARACTER', 'RELATIONSHIP', 'EVENT', 'POV', 'CHRONOLOGY', 'NARRATOR', 'SETTING', 'OBJECT', 'MOTIF', 'IMAGE', 'INTERNAL_STATE', 'ARC', 'CONFLICT', 'SCENE', 'STRUCTURE']
    origin: Literal['SOURCE_FACT', 'INTERPRETATION']
    statement: Text
    anchor_ids: tuple[Text, ...] = Field(min_length=1)
    supports: tuple[Text, ...] = ()
    character_ids: tuple[Text, ...] = ()


class LiteraryAnalysis(ContractModel):
    authority: Literal['literary-source-analysis'] = 'literary-source-analysis'
    units: tuple[SourceUnit, ...] = Field(min_length=1)
    event_order: tuple[Text, ...]
    chronology: Text
    narrative_pov: Text
    narrator: Text
    narrative_structure: Text
    # Categories absent in a tiny text may be N/A with a reason, never invented to fill slots.
    absent_categories: dict[str, Text] = Field(default_factory=dict)


class PhilosophicalCore(ContractModel):
    authority: Literal['philosophical-core'] = 'philosophical-core'
    origin: Literal['INTERPRETATION'] = 'INTERPRETATION'
    source_unit_ids: tuple[Text, ...] = Field(min_length=1)
    question: Text
    conflict: Text
    value_poles: tuple[Text, ...] = Field(min_length=2)
    character_choice: Text
    consequence: Text
    ambiguity: Text


class Preservation(ContractModel):
    must_keep: tuple[Text, ...] = Field(min_length=1)
    core_relationships: tuple[Text, ...]
    core_events: tuple[Text, ...]
    character_arc: Text
    theme_conflict: Text
    narrative_identity: Text


class AdaptationDecision(ContractModel):
    id: Text
    origin: Literal['ADAPTATION_INVENTION'] = 'ADAPTATION_INVENTION'
    operation: Operation
    source_unit_ids: tuple[Text, ...] = Field(min_length=1)
    reason: Text
    narrative_effect: Text
    expression: Text


class AdaptationContract(ContractModel):
    authority: Literal['literary-adaptation'] = 'literary-adaptation'
    preserved: Preservation
    permitted_changes: tuple[Operation, ...]
    decisions: tuple[AdaptationDecision, ...] = Field(min_length=1)


class CompressionMapping(ContractModel):
    decision_id: Text
    destination_ids: tuple[Text, ...] = ()


class DramaticCompression(ContractModel):
    authority: Literal['literary-adaptation'] = 'literary-adaptation'
    mappings: tuple[CompressionMapping, ...] = Field(min_length=1)


class ExplicitnessException(ContractModel):
    basis: Literal['SOURCE_CONTAINS', 'CHARACTER_REQUIRES', 'DRAMATIC_STRUCTURE_REQUIRES']
    reason: Text
    source_unit_ids: tuple[Text, ...] = Field(min_length=1)
    director_decision: Text


class CinemaExpression(ContractModel):
    id: Text
    decision_id: Text
    destination_id: Text
    channels: tuple[Channel, ...] = Field(min_length=1)
    shootable_expression: Text
    choice_action_consequence: Text
    # Semantic review evidence, not a keyword ban or a classifier claiming artistic truth.
    nonverbal_alternative: Text
    explicitness_exception: ExplicitnessException | None = None


class CinemaTranslation(ContractModel):
    authority: Literal['literature-to-cinema'] = 'literature-to-cinema'
    expressions: tuple[CinemaExpression, ...] = Field(min_length=1)


class CharacterArcState(ContractModel):
    character_id: Text
    arc_stage: Text
    adaptation_decision_id: Text | None = None
    source_unit_ids: tuple[Text, ...] = Field(min_length=1)
    origin: Origin
    narrative_state: Text
    emotional_state: Text
    belief_state: Text
    behavioral_state: Text
    relationship_state: Text
    performance_implication: Text
    visual_continuity_boundary: Text


class CharacterArc(ContractModel):
    authority: Literal['character-dramaturgy'] = 'character-dramaturgy'
    states: tuple[CharacterArcState, ...] = Field(min_length=1)


class StageReview(ContractModel):
    authority: Stage
    subject_hash: Hash
    status: Literal['APPROVED', 'REVISE']
    reviewer: Text
    evidence: Text


class LiteraryPackage(ContractModel):
    source_type: Literal['LITERARY'] = 'LITERARY'
    id: Text
    artifacts: tuple[SourceArtifact, ...] = Field(min_length=1)
    source_artifact_id: Text
    anchors: tuple[SourceAnchor, ...] = Field(min_length=1)
    analysis: LiteraryAnalysis
    philosophical_core: PhilosophicalCore
    adaptation: AdaptationContract
    compression: DramaticCompression
    cinema: CinemaTranslation
    character_arc: CharacterArc
    reviews: tuple[StageReview, ...] = Field(min_length=5)


class HistoricalPackage(ContractModel):
    source_type: Literal['HISTORICAL'] = 'HISTORICAL'
    id: Text
    # Existing Work domain content and Dramatic Bible remain intact.
    work_content: dict[str, Any]
    incubation_bible: dict[str, Any]


CreativeSource = Annotated[HistoricalPackage | LiteraryPackage, Field(discriminator='source_type')]


class CompileSourceRequest(ContractModel):
    source: CreativeSource
    jurisdiction: Text
    intended_use: Literal['STUDY', 'ADAPTATION', 'COMMERCIAL_PRODUCTION'] = 'STUDY'


class RightsGate(ContractModel):
    authorized: bool
    jurisdiction: Text
    intended_use: Literal['STUDY', 'ADAPTATION', 'COMMERCIAL_PRODUCTION']
    reasons: tuple[Text, ...]
    artifact_ids: tuple[Text, ...]


class SourceMapEntry(ContractModel):
    target: Text
    origin: Origin
    layer: Literal['SOURCE_FACT', 'INTERPRETATION', 'ADAPTATION_CONTRACT', 'DRAMATIC_COMPRESSION', 'LITERATURE_TO_CINEMA', 'CHARACTER_ARC', 'DIRECTOR_DECISION']
    owner: Text
    source_ref: SourcePin
    source_path: Text
    anchor_ids: tuple[Text, ...]
    decision_id: Text | None = None


class ScreenplayInput(ContractModel):
    schema_version: Literal['screenplay-input-v1'] = 'screenplay-input-v1'
    source_type: CreativeSourceType
    package_ref: SourcePin
    pipeline: tuple[Text, ...]
    resolved_input: dict[str, Any]
    source_map: tuple[SourceMapEntry, ...]
    rights_gate: RightsGate | None = None
    # Consumer may only project this package. Upstream revision invalidates this input.
    upstream_revision_required_for_change: Literal[True] = True
