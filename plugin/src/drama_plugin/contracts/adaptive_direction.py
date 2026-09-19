"""Source-bound evidence and bounded adaptive review facets, not a director state machine."""
from __future__ import annotations
from typing import Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash
from drama_plugin.contracts.source_pin import SourcePin

Domain = Literal['STORY','PERFORMANCE','BLOCKING','CAMERA','SPATIAL','ACTION','CONTINUITY','PROP','COSTUME','ENVIRONMENT','BACKGROUND','SOUND','MUSIC','EDITORIAL','AESTHETIC','PROVIDER_TECHNICAL']
FactDomain = Literal['visible_subjects','actions','action_order','spatial_relations','prop_relations','body_state','gaze','timing','audio_events','environmental_events','technical_artifacts']
DecisionKind = Literal['KEEP','KEEP_SURPRISE','ADAPT_DOWNSTREAM','EDITORIAL_FIX','LOCAL_REPAIR','TARGETED_PICKUP','TARGETED_RETAKE','ROUTE_CHANGE','UPSTREAM_REWRITE','REJECT']

class ObservedMaterialEvidence(ContractModel):
    key: Text
    basis: Literal['STRUCTURED_FIXTURE','OBSERVED_MEDIA']
    media_ref: Text
    media_hash: Hash
    shot_ref: Text
    scene_id: Text
    coverage_refs: tuple[Text, ...] = Field(min_length=1)
    director_intent_refs: tuple[Text, ...] = Field(min_length=1)
    start: float = Field(ge=0,allow_inf_nan=False)
    end: float = Field(gt=0,allow_inf_nan=False)
    facts: dict[FactDomain, tuple[Text, ...]] = Field(default_factory=dict)
    uncertain_observations: tuple[Text, ...] = ()
    observation_confidence: Literal['HIGH','MEDIUM','LOW']
    observer_type: Literal['HUMAN','VERIFIED_MULTIMODAL_RUNTIME','TECHNICAL_RUNTIME','STRUCTURED_FIXTURE']
    method: Literal['NORMAL_AV','NORMAL_VIDEO','TEMPORAL_VISUAL','AUDIO','FRAMES','TECHNICAL','STRUCTURED_FIXTURE']
    evidence_refs: tuple[SourcePin, ...] = Field(min_length=1)
    fact_review_ref: SourcePin | None = None
    @model_validator(mode='after')
    def facts_not_taste(self) -> Self:
        if self.end<=self.start:raise ValueError('Invalid observed range')
        if not self.facts and not self.uncertain_observations:raise ValueError('Declare facts or uncertainty')
        if self.basis=='STRUCTURED_FIXTURE' and (self.observer_type!='STRUCTURED_FIXTURE' or self.method!='STRUCTURED_FIXTURE'):raise ValueError('Fixture cannot claim playback')
        if self.basis=='OBSERVED_MEDIA' and (self.observer_type=='STRUCTURED_FIXTURE' or self.method=='STRUCTURED_FIXTURE' or not self.fact_review_ref):raise ValueError('Live facts require factuality review and real method')
        domains=set(self.facts)
        if (self.observer_type=='TECHNICAL_RUNTIME' or self.method=='TECHNICAL') and domains-{'technical_artifacts'}:raise ValueError('Technical metadata is not semantic observation')
        if self.method in ('FRAMES','NORMAL_VIDEO','TEMPORAL_VISUAL') and 'audio_events' in domains:raise ValueError('Silent evidence cannot establish sound')
        if self.method=='FRAMES' and domains&{'action_order','timing'}:raise ValueError('Stills cannot establish temporal order')
        if self.method=='AUDIO' and domains-{'audio_events','timing','technical_artifacts'}:raise ValueError('Audio cannot establish visible actions')
        # Catch obvious category mistakes, not a claim to understand arbitrary prose.
        for values in self.facts.values():
            if any(x.strip().lower() in {'演得很差','表演很差','他看起来很绝望','bad acting','looks beautiful','更高级'} for x in values):raise ValueError('Evaluation belongs to JUDGED')
        return self


class AudioSemanticEvent(ContractModel):
    """Timed audio facet; unreviewed provider claims are not adopted facts."""
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(ge=0, allow_inf_nan=False)
    description: Text
    speaker_hint: str = Field(default='UNKNOWN', pattern=r'^(speaker_[1-9][0-9]*|UNKNOWN)$')
    confidence: Literal['HIGH','MEDIUM','LOW','UNKNOWN']
    uncertainty: str

    @model_validator(mode='after')
    def range_order(self) -> Self:
        if self.end < self.start:
            raise ValueError('Audio event end precedes start')
        return self


class AudioSemanticObservation(ContractModel):
    """Generic audio facet of material observation, locally validated."""
    speech_events: tuple[AudioSemanticEvent, ...]
    performance_sound_events: tuple[AudioSemanticEvent, ...]
    environment_events: tuple[AudioSemanticEvent, ...]
    other_sound_events: tuple[AudioSemanticEvent, ...]
    subjective_audio_changes: tuple[AudioSemanticEvent, ...]
    uncertain_observations: tuple[Text, ...]

    def timed_events(self) -> list[tuple[str, AudioSemanticEvent]]:
        return [(layer, event) for layer, events in (
            ('SPEECH', self.speech_events), ('PERFORMANCE_SOUND', self.performance_sound_events),
            ('ENVIRONMENT_AMBIENCE', self.environment_events), ('OTHER_SOUND_EVENT', self.other_sound_events),
            ('SUBJECTIVE_AUDIO_CHANGE', self.subjective_audio_changes)) for event in events]

class DeviationAssessment(ContractModel):
    key: Text
    domain: Domain
    classification: Literal['MATCH','ACCEPTABLE_VARIATION','MATERIAL_DEVIATION','POSITIVE_SURPRISE_CANDIDATE','OBSERVATION_UNCERTAIN']
    intended_refs: tuple[SourcePin, ...] = Field(min_length=1)
    observed_evidence_refs: tuple[Text, ...] = Field(min_length=1)
    difference: Text
    judged_consequence: Text
    affected_priority_ids: tuple[Text, ...] = Field(min_length=1)
    priority_impact: Literal['NONE','P0','P1','P2','P3']
    @model_validator(mode='after')
    def meaningful_classification(self) -> Self:
        if self.classification in ('MATCH','ACCEPTABLE_VARIATION') and self.priority_impact in ('P0','P1'):raise ValueError('Protected loss is material, not acceptable')
        return self

class PerformanceRedirection(ContractModel):
    subject: Text
    intended_behavior: Text
    observed_evidence_refs: tuple[Text, ...] = Field(min_length=1)
    performance_deviation_ref: Text
    preserve: tuple[Text, ...] = Field(min_length=1)
    change: tuple[Text, ...] = Field(min_length=1)
    minimal_correction: Text
    next_take_instruction: Text
    scope: Text
    confidence: Literal['HIGH','MEDIUM','LOW']
    authority_refs: tuple[SourcePin, ...] = Field(min_length=1)
    @model_validator(mode='after')
    def delta_only(self) -> Self:
        if set(self.preserve)&set(self.change):raise ValueError('Preserve and change must be separable')
        if self.next_take_instruction.strip() in ('更克制一点','更有层次','更悲伤','更电影','更高级'):raise ValueError('Instruction needs an observable action delta')
        return self

class SurpriseAssessment(ContractModel):
    expected: Text
    unexpected_evidence_refs: tuple[Text, ...] = Field(min_length=1)
    why_potentially_better: Text
    added_character_or_action_value: Text
    checks: dict[Literal['historical_provenance','character_arc','priority','performance','film_grammar','editorial','continuity_prop','continuity_costume','continuity_injury','continuity_position','continuity_knowledge','continuity_relationship','runtime','music_sound'],Literal['PASS','FAIL','UNKNOWN']]
    check_reasons: dict[Text,Text]
    @model_validator(mode='after')
    def full_review(self) -> Self:
        required={'historical_provenance','character_arc','priority','performance','film_grammar','editorial','continuity_prop','continuity_costume','continuity_injury','continuity_position','continuity_knowledge','continuity_relationship','runtime','music_sound'}
        if set(self.checks)!=required or set(self.check_reasons)!=required:raise ValueError('Surprise review needs every boundary and its reason')
        return self

class AdaptiveDownstreamImpact(ContractModel):
    overlay_id: Text
    base_authority: tuple[SourcePin, ...] = Field(min_length=1)
    parent_revision_ref: SourcePin
    affected: dict[Literal['scenes','coverage','shots','cut_conditions','performance','continuity','runtime','music','sound','film_grammar','historical_claims'],tuple[Text,...]]
    dispositions: dict[Text,Text]
    future_only: bool = True
    preserved_media_refs: tuple[Text, ...] = Field(min_length=1)
    proposed_changes: tuple[Text, ...] = ()
    @model_validator(mode='after')
    def complete_impact(self) -> Self:
        required={'scenes','coverage','shots','cut_conditions','performance','continuity','runtime','music','sound','film_grammar','historical_claims'}
        if set(self.affected)!=required or set(self.dispositions)!=required:raise ValueError('All downstream dimensions need explicit assessment, including no change')
        if self.overlay_id==self.parent_revision_ref.key:raise ValueError('Overlay cannot overwrite its base')
        return self

class AdaptiveDecision(ContractModel):
    key: Text
    media_ref: Text
    evidence_refs: tuple[Text, ...] = Field(min_length=1)
    deviations: tuple[DeviationAssessment, ...] = Field(min_length=1)
    decision: DecisionKind
    what_worked: tuple[Text, ...] = Field(min_length=1)
    what_failed: tuple[Text, ...]
    what_is_preserved: tuple[Text, ...] = Field(min_length=1)
    what_changes: tuple[Text, ...]
    lower_cost_options: dict[Literal['KEEP','EDITORIAL_FIX','LOCAL_REPAIR','TARGETED_PICKUP','TARGETED_RETAKE','ROUTE_CHANGE','UPSTREAM_REWRITE'],Text] = Field(default_factory=dict)
    why_editing_is_not_enough: Text | None = None
    why_retake_is_necessary: Text | None = None
    why_no_usable_fragment: Text | None = None
    artistic_judgment: dict[Text,Text] = Field(min_length=1)
    editorial_usability_ref: Text
    performance_redirection: PerformanceRedirection | None = None
    surprise: SurpriseAssessment | None = None
    downstream_impact: AdaptiveDownstreamImpact | None = None
    authority_refs: tuple[SourcePin, ...] = Field(min_length=1)
    model_selection_ref: SourcePin | None = None
    retained_surprise_ref: SourcePin | None = None
    human_review_ref: SourcePin | None = None
    grammar_equivalence_reason: Text | None = None
    next_action: Text
    @model_validator(mode='after')
    def explicit_reasoning(self) -> Self:
        order=['KEEP','EDITORIAL_FIX','LOCAL_REPAIR','TARGETED_PICKUP','TARGETED_RETAKE','ROUTE_CHANGE','UPSTREAM_REWRITE','REJECT']
        if self.decision in order[1:]:
            required=set(order[:order.index(self.decision)])
            if not required<=set(self.lower_cost_options):raise ValueError('Explain why lower-cost options do not suffice')
        if self.decision in ('TARGETED_PICKUP','TARGETED_RETAKE','ROUTE_CHANGE','UPSTREAM_REWRITE','REJECT') and not self.why_editing_is_not_enough:raise ValueError('Editing sufficiency must be considered')
        if self.decision=='TARGETED_RETAKE' and not self.why_retake_is_necessary:raise ValueError('Retake requires exact irreparable intent loss')
        if self.decision=='REJECT' and not self.why_no_usable_fragment:raise ValueError('Reject needs fragment preservation assessment')
        if self.decision in ('KEEP_SURPRISE','ADAPT_DOWNSTREAM') and (not self.surprise or not self.downstream_impact):raise ValueError('Surprise/adaptation needs complete surprise and impact reviews')
        return self
