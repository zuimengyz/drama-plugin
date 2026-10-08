"""Language metadata sidecars preserve the frozen source/work originals."""
from typing import Any, Literal
from pydantic import Field, model_serializer
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text,Hash
from drama_plugin.config.language import LanguageTag

class SourceLanguageMetadata(ContractModel):
    artifact_id: Text
    artifact_hash: Hash
    artifact_language: LanguageTag | None = None
    original_artifact_id: Text
    original_work_languages: tuple[LanguageTag,...] = ()
    evidence_ref: Text
    evidence_hash: Hash
    evidence_selector: Text
    assertion_basis: Literal['SOURCE_METADATA','VERIFIED_PROVENANCE','USER_CONFIRMATION']
    asserted_by: Text

class SubtitlePolicy(ContractModel):
    enabled: bool
    languages: tuple[LanguageTag,...] = ()

class ProductionLanguageProfile(ContractModel):
    work_id: Text
    source_original_language: LanguageTag | None
    source_language_metadata: SourceLanguageMetadata
    spoken_language_policy: Literal['source_original','explicit']
    resolved_production_language: LanguageTag
    creative_review_language: LanguageTag
    subtitles: SubtitlePolicy
    configuration_sources: dict[str,Text]
    warnings: tuple[Text,...] = ()

class SemanticDialogueIntent(ContractModel):
    line_id: Text
    character_id: Text
    scene_id: Text
    beat_id: Text
    review_text: Text
    semantic_intent: Text
    language_register: Text = Field(alias="register")
    relationship_context: Text
    period: Text
    screenplay_hash: Hash
    character_dramaturgy_hash: Hash
    source_refs: tuple[Text,...] = Field(min_length=1)
    adaptation_refs: tuple[Text,...] = Field(min_length=1)
    original_dialogue: tuple[Text,...] = ()
    review_status: Literal['CANDIDATE','APPROVED','UPSTREAM_LOCALIZATION_CONFLICT']
    approval_ref: Text | None = None

class ProductionDialogueLine(ContractModel):
    authority: Literal['dialogue-design:production-language-adaptation']='dialogue-design:production-language-adaptation'
    purpose: Literal['TECHNICAL_FIXTURE','PRODUCTION']
    line_id: Text
    character_id: Text
    scene_id: Text
    beat_id: Text
    source_language: LanguageTag | None
    production_language: LanguageTag
    review_text: Text
    production_text: Text
    semantic_intent: Text
    language_register: Text = Field(alias="register")
    relationship_context: Text
    source_refs: tuple[Text,...] = Field(min_length=1)
    adaptation_refs: tuple[Text,...] = Field(min_length=1)
    semantic_intent_hash: Hash
    language_profile_hash: Hash
    original_dialogue_consulted: tuple[Text,...] = ()
    localization_reason: Text
    review_status: Literal['CANDIDATE','APPROVED','UPSTREAM_LOCALIZATION_CONFLICT']
    review_subject_hash: Hash
    reviewer: Text | None = None
    approval_ref: Text | None = None

class SubtitleCue(ContractModel):
    cue_id: Text
    scene_id: Text
    dialogue_line_id: Text | None = None
    narration_cue_id: Text | None = None
    source_text_language: LanguageTag
    target_language: LanguageTag
    subtitle_text: Text
    semantic_intent_ref: Hash
    speaker_ref: Text
    production_line_hash: Hash
    timing_status: Literal['UNTIMED']='UNTIMED'
    localization_status: Literal['CANDIDATE','APPROVED','UPSTREAM_LOCALIZATION_CONFLICT']='CANDIDATE'
    localization_reason: Text

class SubtitleTrack(ContractModel):
    authority: Literal['subtitle-localization']='subtitle-localization'
    track_id: Text
    work_id: Text
    track_language: LanguageTag
    language_profile_hash: Hash
    cues: tuple[SubtitleCue,...]
    purpose: Literal['TECHNICAL_FIXTURE','PRODUCTION']
    delivery_boundary: Literal['POST_PRODUCTION_OR_PLAYER']='POST_PRODUCTION_OR_PLAYER'

class ObservedSubtitleTiming(ContractModel):
    """Measured speech in a selected native source; canon is intent, not evidence."""
    source_media_hash: Hash
    observation_ref: Text
    observation_hash: Hash
    transcribed_text: Text
    source_start: float = Field(ge=0, allow_inf_nan=False)
    source_end: float = Field(gt=0, allow_inf_nan=False)
    edit_offset: float = Field(ge=0, allow_inf_nan=False)
    uncertainty: str = ''

class SubtitleTextBasis(ContractModel):
    """Subtitle wording provenance, independently of observed speech verification."""
    kind: Literal['ASR','SCRIPT','MIXED']
    source_text: Text
    script_ref: Text
    script_line_hash: Hash
    script_range: tuple[int,int]
    script_fragment: str = Field(min_length=1)
    evidence_refs: tuple[Text,...] = ()


class ReviewSubtitleCue(SubtitleCue):
    """Review-only subtype preserves the historical untimed contract and hashes."""
    timing_status: Literal['OBSERVED_CANDIDATE']='OBSERVED_CANDIDATE'
    observed_timing: ObservedSubtitleTiming
    text_basis: SubtitleTextBasis | None = None
    display_source_end: float | None = Field(default=None,ge=0,allow_inf_nan=False)
    timing_basis: Literal['SENTENCE_ESTIMATE','SPEECH_WINDOW_SENTENCE_SPLIT'] | None = None

    @model_serializer(mode='wrap')
    def preserve_historical_cues(self, handler):
        result=handler(self)
        if self.text_basis is None:
            result.pop('textBasis',None);result.pop('text_basis',None)
        if self.display_source_end is None:
            result.pop('displaySourceEnd',None);result.pop('display_source_end',None)
        if self.timing_basis is None:
            result.pop('timingBasis',None);result.pop('timing_basis',None)
        return result

class ReviewSubtitleTrack(SubtitleTrack):
    cues: tuple[ReviewSubtitleCue,...] = Field(min_length=1)
    edit_media_hash: Hash
    edit_duration: float = Field(gt=0, allow_inf_nan=False)
    review_status: Literal['CANDIDATE']='CANDIDATE'

class SpeechLanguageAuthorization(ContractModel):
    profile: ProductionLanguageProfile
    intent: SemanticDialogueIntent
    line: ProductionDialogueLine
