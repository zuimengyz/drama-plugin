"""One film-score sidecar. All other classes here are nested values, not entities."""
from __future__ import annotations
import re
from typing import Literal, Self
from pydantic import Field, model_validator, field_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, MusicRights
from drama_plugin.contracts.sequence import SourcePin

SourceStrategy=Literal['NO_SCORE','ORIGINAL_AI','ORIGINAL_HUMAN','OWNED_EXISTING','LICENSED_LIBRARY','PUBLIC_DOMAIN_COMPOSITION_WITH_CLEARED_RECORDING','TEMP_REFERENCE']

class ScorePalette(ContractModel):
    timbre: Text
    density: Text
    rhythm: Text
    texture: Text
    historical_flavor_boundary: Text
    modern_cinematic_boundary: Text

class ScoreMotif(ContractModel):
    motif_id: Text
    dramatic_function: Text
    identity: Text
    development: Text
    payoff_or_withholding: Text
    context_refs: tuple[Text,...] = ()

class MusicGenerationRequirements(ContractModel):
    """Nested requirements / CapabilityRequest payload only. Never a provider request."""
    cue_ref: Text
    duration_range: tuple[float,float]
    dramatic_function: Text
    energy_arc: tuple[Text,...] = Field(min_length=2)
    motif_refs: tuple[Text,...] = ()
    timbre: Text
    rhythm: Text
    instrumental_policy: Literal['INSTRUMENTAL','EXPLICIT_VOCAL_APPROVAL'] = 'INSTRUMENTAL'
    vocal_policy: Literal['PROHIBITED','DIRECTOR_AND_MUSIC_APPROVED'] = 'PROHIBITED'
    reference_refs: tuple[SourcePin,...] = ()
    continuation: Text
    revision_requirement: Text
    stem_requirement: Literal['REQUIRED','NOT_REQUIRED_WITH_REASON'] = 'REQUIRED'
    stem_reason: Text
    lossless_requirement: Literal[True] = True
    commercial_rights_requirement: Literal[True] = True
    editability: Text
    content_kind: Literal['FILM_SCORE'] = 'FILM_SCORE'

    @model_validator(mode='after')
    def ranges(self) -> Self:
        import math
        a,b=self.duration_range
        if not all(math.isfinite(x) for x in (a,b)) or not 0<a<=b:raise ValueError('APPROXIMATE_DURATION_RANGE_REQUIRED')
        if (self.instrumental_policy=='INSTRUMENTAL') != (self.vocal_policy=='PROHIBITED'):raise ValueError('SCORE_VOCAL_POLICY_CONFLICT')
        return self

class MusicYieldEvent(ContractModel):
    """Nested dramatic event, not a measured edit point or independent contract."""
    source_ref: SourcePin
    trigger: Text
    action: Literal['ENTER','BUILD','HOLD','THIN','DUCK','DROP','STOP','RETURN','DO_NOT_RETURN']
    primary_sound: Text
    reason: Text

    @field_validator('trigger')
    @classmethod
    def event_not_time(cls, value: str) -> str:
        if re.fullmatch(r'[\d\s:.,]+(?:s|sec|秒)?', value):
            raise ValueError('SOURCE_EVENT_REQUIRED_NOT_TIMESTAMP')
        return value

class MusicYieldPolicy(ContractModel):
    """Nested MusicCue value. Priority protection does not mean automatic muting."""
    yield_to_dialogue: Literal[True] = True
    yield_to_physical_impact: Literal[True] = True
    yield_to_native_breath: Literal[True] = True
    yield_to_partner_response: Literal[True] = True
    yield_to_diegetic_music: Literal[True] = True
    events: tuple[MusicYieldEvent, ...] = Field(min_length=2)
    protected_no_score_refs: tuple[SourcePin, ...] = ()
    reentry_policy: Literal['DO_NOT_RETURN','REVIEW_REQUIRED','SOURCE_EVENT']

    @model_validator(mode='after')
    def transitions(self) -> Self:
        actions=[e.action for e in self.events]
        if actions[0]!='ENTER' or not any(a in {'DROP','STOP'} for a in actions):
            raise ValueError('ENTRY_AND_EXIT_EVENTS_REQUIRED')
        if 'RETURN' in actions and self.reentry_policy!='SOURCE_EVENT':
            raise ValueError('NO_AUTOMATIC_SCORE_RETURN')
        if self.reentry_policy=='SOURCE_EVENT' and 'RETURN' not in actions:
            raise ValueError('REENTRY_EVENT_REQUIRED')
        active=False
        for action in actions:
            if action in {'ENTER','RETURN'}:
                if active:
                    raise ValueError('SCORE_ENTRY_WHILE_ACTIVE')
                active=True
            elif action in {'DROP','STOP'}:
                active=False
            elif action=='DO_NOT_RETURN':
                if active:raise ValueError('SCORE_MUST_EXIT_BEFORE_NO_RETURN')
            elif not active:
                raise ValueError('SCORE_DEVELOPMENT_REQUIRES_ENTRY_OR_RETURN')
        if active:raise ValueError('SCORE_MUST_END_WITH_EXIT')
        protected={p.key for p in self.protected_no_score_refs}
        if any(e.source_ref.key in protected and e.action not in {'DROP','STOP','DO_NOT_RETURN'} for e in self.events):
            raise ValueError('PROTECTED_SILENCE_CANNOT_BE_SCORED')
        return self

class MusicCue(ContractModel):
    cue_id: Text
    scene_ids: tuple[Text,...] = Field(min_length=1)
    content_kind: Literal['FILM_SCORE'] = 'FILM_SCORE'
    narrative_function: Text
    emotional_direction: Literal['PROPULSION','JOY','NEUTRAL_TEXTURE','MOURNING']
    performance_relation: Literal['ADD_INFORMATION','SUPPORT_ACTION','SUPPORT_EARNED_RELEASE','DUPLICATE_EMOTION','PREMATURE_FORESHADOWING']
    audience_effect: Text
    entry_trigger: Text
    exit_trigger: Text
    energy_arc: tuple[Text,...] = Field(min_length=2)
    motif_refs: tuple[Text,...] = ()
    timbre_palette: Text
    rhythmic_function: Text
    yield_policy: MusicYieldPolicy | None = None
    dialogue_priority: Literal['PROTECT'] = 'PROTECT'
    dialogue_windows: tuple[Text,...] = Field(min_length=1)
    native_audio_priority: Literal['PROTECT'] = 'PROTECT'
    sfx_priority: Literal['PROTECT'] = 'PROTECT'
    silence_before: Text
    silence_after: Text
    sync_points: tuple[Text,...] = ()
    binding_refs: tuple[SourcePin,...] = ()
    source_strategy: SourceStrategy
    rights_requirement: Text
    rights: MusicRights = Field(default_factory=MusicRights)
    do_not: tuple[Text,...] = Field(min_length=1)
    status: Literal['PROPOSED','DESIGN_REVIEWED'] = 'PROPOSED'
    generation_requirements: MusicGenerationRequirements | None = None
    vocal_approval_refs: dict[Literal['director','music-direction'],SourcePin] = Field(default_factory=dict)
    context_refs: tuple[Text,...] = ()

    @field_validator('narrative_function')
    @classmethod
    def not_emotion_label(cls, value: str) -> str:
        if value.strip().lower() in {'epic','sad','heroic','悲壮','史诗','热血','中国风','古风'}:raise ValueError('EMOTION_LABEL_IS_NOT_DRAMATIC_FUNCTION')
        return value

    @model_validator(mode='after')
    def execution_boundary(self) -> Self:
        if self.source_strategy=='NO_SCORE':raise ValueError('NO_SCORE_IS_A_SCENE_DECISION_NOT_A_GENERATION_CUE')
        if self.source_strategy=='ORIGINAL_AI' and not self.generation_requirements:raise ValueError('ORIGINAL_AI_REQUIRES_GENERATION_REQUIREMENTS')
        if self.generation_requirements:
            r=self.generation_requirements
            if (r.cue_ref!=self.cue_id or r.dramatic_function!=self.narrative_function or r.energy_arc!=self.energy_arc or r.motif_refs!=self.motif_refs or r.timbre!=self.timbre_palette or r.rhythm!=self.rhythmic_function):raise ValueError('COMPOSER_REQUIREMENTS_CUE_MISMATCH')
            if r.vocal_policy!='PROHIBITED' and set(self.vocal_approval_refs)!={'director','music-direction'}:raise ValueError('EXPLICIT_SCORE_VOCAL_APPROVAL_REQUIRED')
        return self

class SceneMusicDecision(ContractModel):
    scene_id: Text
    decision: Literal['NO_SCORE','NO_SCORE_MUST_PRESERVE','SCORE_PRESENT','SCORE_REQUIRED','SCORE_OPTIONAL','DIEGETIC_ONLY','TRANSITION_ONLY']
    rationale: Text
    score_function: Text
    entry_trigger: Text
    exit_trigger: Text
    performance_alignment: Text
    performance_intent_ref: SourcePin
    dialogue_native_priority: Text
    source_strategy: SourceStrategy
    cue_refs: tuple[Text,...] = ()
    do_not: tuple[Text,...] = Field(min_length=1)
    context_refs: tuple[Text,...] = ()
    @model_validator(mode='after')
    def conscious_silence(self) -> Self:
        silent=self.decision in ('NO_SCORE','NO_SCORE_MUST_PRESERVE','DIEGETIC_ONLY')
        if silent and (self.cue_refs or self.source_strategy!='NO_SCORE'):raise ValueError('SILENCE_CANNOT_CONTAIN_SCORE_CUES')
        if not silent and (not self.cue_refs or self.source_strategy=='NO_SCORE'):raise ValueError('SCORE_DECISION_REQUIRES_CUE')
        return self

class FilmScorePlan(ContractModel):
    schema_version: Literal['film-score-plan-v1'] = 'film-score-plan-v1'
    scope_id: Text
    source_kind: Literal['FORMAL','PROPOSAL_ONLY','DESIGN_FIXTURE_ONLY']
    source_pins: tuple[SourcePin,...] = Field(min_length=1)
    film_intent_ref: SourcePin
    stage: Literal['DRAMATIC_SCORE_DESIGN','CUE_DESIGN'] = 'DRAMATIC_SCORE_DESIGN'
    scene_ids: tuple[Text,...] = Field(min_length=1)
    score_thesis: Text
    score_world: Text
    score_palette: ScorePalette
    motifs: tuple[ScoreMotif,...] = ()
    character_theme_policy: Text = 'NO_CHARACTER_THEME unless dramatically necessary'
    silence_policy: Text
    diegetic_boundary: Text
    score_dynamic_range: Text
    scene_music_decisions: tuple[SceneMusicDecision,...]
    music_cues: tuple[MusicCue,...] = ()
    source_strategy_policy: Text
    rights_policy: Text
    excluded_performance_refs: tuple[Text,...] = ()
    unresolved_questions: tuple[Text,...] = ()
    review_status: Literal['DRAFT','DESIGN_REVIEWED'] = 'DRAFT'

    @model_validator(mode='after')
    def graph_and_stage(self) -> Self:
        scenes=set(self.scene_ids);decisions=[d.scene_id for d in self.scene_music_decisions]
        if len(scenes)!=len(self.scene_ids) or len(decisions)!=len(set(decisions)) or set(decisions)!=scenes:raise ValueError('ALL_SCENES_REQUIRE_MUSIC_REVIEW')
        cues={c.cue_id:c for c in self.music_cues};motifs={m.motif_id for m in self.motifs}
        if len(cues)!=len(self.music_cues) or len(motifs)!=len(self.motifs):raise ValueError('DUPLICATE_SCORE_IDENTITY')
        referenced=set()
        for d in self.scene_music_decisions:
            for ref in d.cue_refs:
                if ref not in cues or d.scene_id not in cues[ref].scene_ids or d.source_strategy!=cues[ref].source_strategy:raise ValueError('SCENE_CUE_SOURCE_BINDING_MISMATCH')
                referenced.add(ref)
        if referenced!=set(cues):raise ValueError('UNREVIEWED_MUSIC_CUE')
        for c in self.music_cues:
            if not set(c.scene_ids)<=scenes or not set(c.motif_refs)<=motifs:raise ValueError('FOREIGN_SCENE_OR_MOTIF')
            if (c.cue_id in self.excluded_performance_refs or set(c.context_refs)&set(self.excluded_performance_refs) or any(p.key in self.excluded_performance_refs for p in (*c.binding_refs,*(c.generation_requirements.reference_refs if c.generation_requirements else ())))):raise ValueError('HISTORICAL_VERSE_NOT_FILM_SCORE')
            if self.stage=='CUE_DESIGN' and not c.binding_refs:raise ValueError('CUE_REQUIRES_SHOT_BEAT_CUT_BINDING')
            for trigger in (c.entry_trigger,c.exit_trigger):
                if re.fullmatch(r'[\d\s:.,]+(?:s|sec|秒)?',trigger):raise ValueError('DRAMATIC_TRIGGER_REQUIRED_NOT_EXACT_TIMELINE')
        return self
