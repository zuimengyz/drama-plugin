"""Narration strategy and scene direction, never audio/provider execution."""
from typing import Any, Literal
from pydantic import Field
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash
from drama_plugin.contracts.creative_source import LiteraryPackage

NarrationType = Literal['AUTHORIAL_NARRATION', 'CHARACTER_VOICE_OVER', 'INTERNAL_MONOLOGUE', 'EXPOSITORY_NARRATION']
NarrationMode = Literal['NONE', 'AUTHORIAL_NARRATION', 'CHARACTER_VOICE_OVER', 'INTERNAL_MONOLOGUE', 'EXPOSITORY_NARRATION']
NarrationLayer = Literal['SOURCE_NARRATOR_FUNCTION', 'ADAPTED_SOURCE_NARRATOR', 'CHARACTER_THOUGHT_SOURCE', 'ADAPTATION_NARRATION_INVENTION']

class NarrationBible(ContractModel):
    authority: Literal['narration-line'] = 'narration-line'
    narration_mode: NarrationMode
    narrator_identity: Text
    narrative_distance: Text
    knowledge_scope: Text
    temporal_position: Text
    tone: Text
    irony_level: Text
    language_density: Text
    rhythm: Text
    allowed_functions: tuple[Text, ...] = Field(min_length=1)
    forbidden_functions: tuple[Text, ...] = Field(min_length=1)
    relationship_to_character_pov: Text
    silence_policy: Text
    theme_explicitness_boundary: Text
    source_policy: Text

class NarrationPerformanceIntent(ContractModel):
    narrative_distance: Text
    delivery_restraint: Text
    irony: Text
    certainty: Text
    tempo: Text
    pause_behavior: Text
    emotional_temperature: Text

class ThemeExplicitnessReview(ContractModel):
    disposition: Literal['FUNCTION_ONLY', 'SOURCE_SUPPORTED_EXCEPTION', 'HUMAN_CONFLICT']
    reason: Text
    source_explicit_support: tuple[Text, ...] = ()
    # This is a supplied specialist judgment, not a classifier result.
    reviewer: Text

class NarrationCue(ContractModel):
    cue_id: Text
    scene_id: Text
    beat_id: Text
    narration_type: NarrationType
    text: Text
    source_layer: NarrationLayer
    source_anchor_ids: tuple[Text, ...] = Field(min_length=1)
    source_unit_ids: tuple[Text, ...] = Field(min_length=1)
    literary_function: Text
    cinematic_function: Text
    why_narration_is_needed: Text
    why_action_or_silence_is_insufficient: Text
    placement: Text
    relationship_to_dialogue: Text
    relationship_to_performance: Text
    theme_explicitness_review: ThemeExplicitnessReview
    source_map_refs: tuple[Text, ...] = Field(min_length=1)
    adaptation_decision_id: Text
    director_reason: Text
    upstream_change_request_id: Text | None = None
    performance_intent: NarrationPerformanceIntent

class SceneNarrationPolicy(ContractModel):
    scene_id: Text
    beat_ids: tuple[Text, ...] = Field(min_length=1)
    policy: Literal['NARRATION', 'SILENCE']
    reason: Text
    cue_ids: tuple[Text, ...] = ()

class UpstreamChangeRequest(ContractModel):
    id: Text
    status: Literal['USER_APPROVAL_PENDING'] = 'USER_APPROVAL_PENDING'
    target_authority: Literal['literary-adaptation', 'literature-to-cinema', 'character-dramaturgy']
    current_value: Text
    problem: Text
    source_evidence: tuple[Text, ...] = Field(min_length=1)
    proposed_change: Text
    downstream_impact: Text

class CandidateReview(ContractModel):
    subject_hash: Hash
    reviewer: Text
    evidence: Text
    status: Literal['REVIEWED_CANDIDATE', 'HUMAN_CONFLICT']
    user_approval: Literal[False] = False

class NarrationPlan(ContractModel):
    id: Text
    bible: NarrationBible
    cues: tuple[NarrationCue, ...] = ()
    scenes: tuple[SceneNarrationPolicy, ...] = Field(min_length=1)
    upstream_change_requests: tuple[UpstreamChangeRequest, ...] = ()
    review: CandidateReview

class NarrationContext(ContractModel):
    # Replay these originals. No rights reauthoring or new source acquisition.
    package: LiteraryPackage
    screenplay: dict[str, Any]
    character_dramaturgy: dict[str, Any]

class CharacterStateRef(ContractModel):
    character_id: Text
    arc_stage: Text

class DirectorScenePlan(ContractModel):
    scene_id: Text
    title: Text
    beat_ids: tuple[Text, ...] = Field(min_length=1)
    dramatic_purpose: Text
    audience_knowledge: Text
    audience_misunderstanding_risk: Text
    character_states: tuple[CharacterStateRef, ...] = Field(min_length=1)
    relationship_state: Text
    performance_intent: Text
    blocking_intent: Text
    spatial_dramaturgy: Text
    visual_attention: Text
    narration_policy: Literal['NARRATION', 'SILENCE']
    narration_cue_ids: tuple[Text, ...] = ()
    sound_intent: Text
    silence_intent: Text
    rhythm_tempo: Text
    humor_absurdity_function: Text
    transition_in: Text
    transition_out: Text
    must_preserve: tuple[Text, ...] = Field(min_length=1)
    must_not: tuple[Text, ...] = Field(min_length=1)
    continuity_requirement: Text
    specialized_asset_handoff: Text
    performance_handoff: Text
    cinematography_handoff: Text
    sound_handoff: Text
    music_handoff: Text
    music_policy: Literal['MUSIC_ALLOWED', 'MUSIC_AVOID', 'MUSIC_MUST_YIELD_TO_DIALOGUE', 'MUSIC_MUST_YIELD_TO_NARRATION']
    shot_design_handoff: Text
    source_map_refs: tuple[Text, ...] = Field(min_length=1)

class FullDirectorScreenplay(ContractModel):
    authority: Literal['director'] = 'director'
    id: Text
    narration_plan_hash: Hash
    screenplay_hash: Hash
    character_dramaturgy_hash: Hash
    scenes: tuple[DirectorScenePlan, ...] = Field(min_length=1)
    review: CandidateReview
    status: Literal['USER_APPROVAL_PENDING'] = 'USER_APPROVAL_PENDING'
    p2_authorized: Literal[False] = False
