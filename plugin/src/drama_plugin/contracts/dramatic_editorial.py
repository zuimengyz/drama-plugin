"""Story/coverage/edit sidecars; plans never write Canon or render Media."""
from __future__ import annotations
from typing import Annotated, Literal, Self, Any
from pydantic import Field, model_validator, model_serializer, SerializerFunctionWrapHandler
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash
from drama_plugin.contracts.production_design import HistoricalCanonPolicy
Seconds = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class PressureRelease(ContractModel):
    starting_pressure: Text
    pressure_escalation: Text
    turn: Text
    release_point: Text | None = None
    withheld_release_reason: Text | None = None
    aftermath: Text

    @model_validator(mode='after')
    def release_or_hold(self) -> Self:
        if not self.release_point and not self.withheld_release_reason:
            raise ValueError('Account for release or purposeful withheld release')
        return self


class DramaticPeak(ContractModel):
    key: Text
    scene_ids: tuple[Text, ...] = Field(min_length=1)
    level: Literal['MICRO','SCENE','EPISODE']
    type: Text
    setup: Text
    pressure: Text
    trigger: Text
    escalation: Text | None = None
    payoff: Text
    aftermath: Text
    character_change: Text
    visual_opportunity: Text | None = None
    sound_opportunity: Text | None = None


class HeroMoment(ContractModel):
    character: Text
    action: Text
    earned_by: tuple[Text, ...] = Field(min_length=1)
    cost_or_irreversibility: Text
    changes_space_or_others: Text
    canon_refs: tuple[Text, ...] = Field(min_length=1)


class SetPiece(ContractModel):
    key: Text
    scene_ids: tuple[Text, ...] = Field(min_length=1)
    memorable_because: Text
    pressure_ladder: tuple[Text, ...] = Field(min_length=2)
    first_reveal: Text
    payoff: Text
    irreversible_action: Text
    aftermath: Text
    hero_moment: HeroMoment | None = None
    historical_constraints: HistoricalCanonPolicy = Field(default_factory=HistoricalCanonPolicy)


class DramaticPeakMap(ContractModel):
    schema_version: Literal['dramatic-peak-map-v1'] = 'dramatic-peak-map-v1'
    scope_id: Text
    source_fingerprint: Hash
    revision: Text
    mode: Literal['CURRENT','RECOMMENDED']
    peaks: tuple[DramaticPeak, ...] = ()
    set_pieces: tuple[SetPiece, ...] = ()
    dynamic_range: Text
    memory_review: Text
    strongest_excerpt: Text | None = None
    delete_strongest_test: Text
    historical_constraints: HistoricalCanonPolicy = Field(default_factory=HistoricalCanonPolicy)

    @model_validator(mode='after')
    def unique_peaks(self) -> Self:
        if len({p.key for p in self.peaks})!=len(self.peaks):
            raise ValueError('Duplicate peak')
        return self


class VisualInformationBeat(ContractModel):
    key: Text
    information: Text
    focus: Text
    change: Text


class CutMotivation(ContractModel):
    from_beat: Text
    to_beat: Text
    reason: Text
    new_information_or_relation: Text

    @model_validator(mode='after')
    def changes_attention(self) -> Self:
        if self.from_beat==self.to_beat:raise ValueError('Cut must change the information beat')
        return self


class SingleTakeFeasibility(ContractModel):
    verdict: Literal['YES','NO','CONDITIONAL']
    rationale: Text
    attention_transitions: tuple[Text, ...]
    staging_solution: Text | None = None
    alternative: Text | None = None

    @model_validator(mode='after')
    def executable_judgment(self) -> Self:
        if self.verdict in {'YES','CONDITIONAL'} and not self.staging_solution:
            raise ValueError('Single take needs staging, not model length')
        if self.verdict in {'NO','CONDITIONAL'} and not self.alternative:
            raise ValueError('Single take rejection/condition needs alternative coverage')
        return self


class CoverageShot(ContractModel):
    key: Text
    beat_ids: tuple[Text, ...] = Field(min_length=1)
    duration: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    duration_basis: Literal['DRAMATIC_INFORMATION','MEASURED_PERFORMANCE']
    duration_reason: Text
    purpose: Literal['SETUP','ESCALATION','HERO','REACTION','PAYOFF','AFTERMATH','DETAIL','ESTABLISHING','DIALOGUE']
    visual_power_reason: Text | None = None
    attention_changes: Annotated[int, Field(ge=0)] = 0
    single_take: SingleTakeFeasibility | None = None
    hold_reason: Text | None = None

    @model_validator(mode='after')
    def duration_and_power(self) -> Self:
        if self.duration>=10 and self.attention_changes>=2 and self.single_take is None:
            raise ValueError('Long multi-focus Shot requires SingleTakeFeasibility')
        if self.purpose=='HERO' and not self.visual_power_reason:
            raise ValueError('HeroShot requires earned visual power')
        return self


class ReactionLink(ContractModel):
    actor: Text
    observed_action: Text
    responds_to: Text
    changes: Text


class ShotTransition(ContractModel):
    """Intended continuity; finishing owns the actual measured-media cut."""
    from_shot: Text
    to_shot: Text
    end_state: Text
    opening_state: Text
    cut_trigger: Text
    transition_type: Text
    screen_direction: Text
    axis: Text
    eyeline: Text
    motion_continuity: Text
    composition_relation: Text
    sound_carry: Literal['carry', 'cut', 'fade', 'prelap', 'offscreen continuation']
    sound_intent: Text
    time_relation: Literal['continuous', 'compressed continuous', 'explicit ellipsis', 'new time', 'parallel']
    space_relation: Text
    why_this_cut_exists: Text

    @model_validator(mode='after')
    def different_shots(self) -> Self:
        if self.from_shot == self.to_shot:
            raise ValueError('Transition requires two different views')
        return self


class EditorialRhythmPlan(ContractModel):
    schema_version: Literal['editorial-rhythm-v1'] = 'editorial-rhythm-v1'
    scene_ids: tuple[Text, ...] = Field(min_length=1)
    source_fingerprint: Hash
    revision: Text
    information_beats: tuple[VisualInformationBeat, ...] = Field(min_length=1)
    coverage: tuple[CoverageShot, ...] = Field(min_length=1)
    cuts: tuple[CutMotivation, ...] = ()
    reaction_chain: tuple[ReactionLink, ...] = ()
    transitions: tuple[ShotTransition, ...] = ()
    transition_omission_reason: Text | None = None
    establishing_need: Text
    rhythm_acceleration: Text | None = None
    rhythm_deceleration: Text | None = None
    visual_contrast_rhythm: Text
    set_piece_coverage: dict[Literal['setup','escalation','hero','reaction','payoff','aftermath'], tuple[Text, ...]] | None = None

    @model_serializer(mode='wrap')
    def compatible_dump(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = dict(handler(self))
        if not self.transitions:
            data.pop('transitions', None)
        if self.transition_omission_reason is None:
            data.pop('transitionOmissionReason', None)
            data.pop('transition_omission_reason', None)
        return data

    @model_validator(mode='after')
    def coverage_links(self) -> Self:
        beats={b.key for b in self.information_beats};shots={s.key for s in self.coverage}
        if len(beats)!=len(self.information_beats) or len(shots)!=len(self.coverage):raise ValueError('Duplicate coverage key')
        if any(not set(s.beat_ids)<=beats for s in self.coverage):raise ValueError('Unknown visual information beat')
        if beats != {b for s in self.coverage for b in s.beat_ids}:raise ValueError('Uncovered information beat')
        if any(c.from_beat not in beats or c.to_beat not in beats for c in self.cuts):raise ValueError('Unknown cut beat')
        if self.set_piece_coverage is not None:
            required={'setup','escalation','reaction','payoff','aftermath'}
            # Hero emphasis is optional, including for a political or civilian set piece.
            if not required <= set(self.set_piece_coverage) or any(not ids or not set(ids)<=shots for ids in self.set_piece_coverage.values()):
                raise ValueError('Set piece needs complete, existing coverage roles')
        pairs = [(t.from_shot, t.to_shot) for t in self.transitions]
        if len(set(pairs)) != len(pairs) or any(a not in shots or b not in shots for a,b in pairs):
            raise ValueError('Duplicate or unknown transition shot')
        return self


class EditSource(ContractModel):
    media_id: Text
    content_hash: Hash
    duration: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    performance_review: Text


class PictureEdit(ContractModel):
    source_media: Text
    source_in: Seconds
    source_out: Seconds
    cut_reason: Text
    reaction_hold: Text | None = None
    match_action: Text | None = None
    audio_carry: Text
    pace_function: Text

    @model_validator(mode='after')
    def positive_range(self) -> Self:
        if self.source_out<=self.source_in:raise ValueError('sourceOut must exceed sourceIn')
        return self


class PictureEditPlan(ContractModel):
    schema_version: Literal['picture-edit-v1'] = 'picture-edit-v1'
    revision: Text
    source_canon_fingerprint: Hash
    status: Literal['DRAFT','REVIEWED'] = 'DRAFT'
    sources: tuple[EditSource, ...] = Field(min_length=1)
    picture_edit: tuple[PictureEdit, ...] = Field(min_length=1)
    audio_review: Literal['UNKNOWN','PASS','FAIL'] = 'UNKNOWN'
    protected_dialogue_review: Text

    @model_validator(mode='after')
    def source_ranges(self) -> Self:
        sources={s.media_id:s for s in self.sources}
        if len(sources)!=len(self.sources):raise ValueError('Duplicate edit source')
        if any(e.source_media not in sources or e.source_out>sources[e.source_media].duration for e in self.picture_edit):
            raise ValueError('Source range outside measured Media')
        if self.status=='REVIEWED' and self.audio_review!='PASS':
            raise ValueError('Reviewed picture trim requires protected dialogue/audio review')
        return self
