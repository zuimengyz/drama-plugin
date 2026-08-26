from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, model_validator

from drama_plugin.contracts.base import ContractModel


class ProviderMappingStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    APPROVED = "APPROVED"
    RETIRED = "RETIRED"


class EvidenceConfidence(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CharacterDimension(ContractModel):
    value: str = "UNKNOWN"
    confidence: EvidenceConfidence = EvidenceConfidence.LOW
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unknown(self) -> "CharacterDimension":
        if self.value == "UNKNOWN" and self.confidence is not EvidenceConfidence.LOW:
            raise ValueError("UNKNOWN character dimensions must have LOW confidence")
        return self


class CharacterUnderstanding(ContractModel):
    schema_version: Literal["character-understanding-v1"] = (
        "character-understanding-v1"
    )
    understanding_id: str
    speaker_key: str
    identity_and_life_stage: dict[str, CharacterDimension] = Field(
        default_factory=dict
    )
    experience_structure: dict[str, CharacterDimension] = Field(
        default_factory=dict
    )
    decision_style: dict[str, CharacterDimension] = Field(default_factory=dict)
    emotional_regulation: dict[str, CharacterDimension] = Field(
        default_factory=dict
    )
    interaction_style: dict[str, CharacterDimension] = Field(
        default_factory=dict
    )
    authority_and_responsibility: dict[str, CharacterDimension] = Field(
        default_factory=dict
    )
    communication_style: dict[str, CharacterDimension] = Field(
        default_factory=dict
    )
    physical_baseline: dict[str, CharacterDimension] = Field(default_factory=dict)
    presentation_modes: dict[str, CharacterDimension] = Field(default_factory=dict)
    alignment_and_constraints: dict[str, CharacterDimension] = Field(
        default_factory=dict
    )
    unknown_fields: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class SceneState(ContractModel):
    schema_version: Literal["scene-state-v1"] = "scene-state-v1"
    spoken_content_id: str | None = None
    speaker_key: str | None = None
    current_emotion: CharacterDimension | None = None
    emotion_cause: CharacterDimension | None = None
    internal_activation: CharacterDimension | None = None
    external_expressiveness: CharacterDimension | None = None
    urgency: CharacterDimension | None = None
    stress_level: CharacterDimension | None = None
    interaction_target: CharacterDimension | None = None
    speaker_objective: CharacterDimension | None = None
    subtext: CharacterDimension | None = None
    restraint: CharacterDimension | None = None
    physical_condition: CharacterDimension | None = None
    presentation_mode: CharacterDimension | None = None
    unknown_fields: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class CreativeVoiceProfile(ContractModel):
    # Pre-7.2S callers populate these broad fields.  They remain serialized for
    # backward compatibility, while new planning can leave them UNKNOWN and use
    # the more precise provider-neutral dimensions below.
    age_presentation: str = "UNKNOWN"
    gender_presentation: str | None = None
    timbre: str = "UNKNOWN"
    temperament: str = "UNKNOWN"
    baseline_pace: str = "UNKNOWN"
    power: str = "UNKNOWN"
    restraint: str = "UNKNOWN"
    language: str = "zh-CN"
    language_register: str | None = Field(default=None, alias="register")
    resonance: str | None = None
    texture: str | None = None
    authority: str | None = None
    articulation: str | None = None
    energy: str | None = None
    vocal_age: str | None = None
    vocal_weight: str | None = None
    resonance_depth: str | None = None
    timbre_brightness: str | None = None
    articulation_firmness: str | None = None
    phrase_attack: str | None = None
    baseline_energy: str | None = None
    breath_support: str | None = None
    command_presence: str | None = None
    gravitas: str | None = None
    controlled_power: str | None = None
    sentence_finality: str | None = None
    emotional_containment: str | None = None
    consistency_notes: list[str] = Field(default_factory=list)


class ProviderVoiceMapping(ContractModel):
    provider: str
    model: str
    voice_id: str
    status: ProviderMappingStatus = ProviderMappingStatus.APPROVED
    material_parameters: dict[str, Any] = Field(default_factory=dict)
    non_material_metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceProfile(ContractModel):
    profile_id: str
    speaker_key: str
    creative_profile: CreativeVoiceProfile
    character_understanding: CharacterUnderstanding | None = None
    provider_mappings: list[ProviderVoiceMapping] = Field(default_factory=list)
    display_name: str | None = None
    non_material_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_understanding_scope(self) -> "VoiceProfile":
        if (
            self.character_understanding is not None
            and self.character_understanding.speaker_key != self.speaker_key
        ):
            raise ValueError("character understanding speakerKey must match voice profile")
        return self


class PronunciationGuidance(ContractModel):
    term: str
    language: str
    reviewed_reading: str
    speaker_key: str | None = None
    notes: str | None = None


class TargetTimingPolicy(ContractModel):
    policy: Literal["NATURAL", "FIT_WINDOW", "FIXED_WINDOW"]
    target_duration_ms: int | None = Field(default=None, gt=0)
    allow_rate_adjustment: bool = False
    constraints: dict[str, Any] = Field(default_factory=dict)


class SpeechGenerationRequest(ContractModel):
    schema_version: Literal["speech-generation-v1"] = "speech-generation-v1"
    work_id: str
    scene_id: str
    spoken_content_id: str
    exact_text: str = Field(min_length=1)
    speaker_key: str
    voice_profile: VoiceProfile
    provider_mapping: ProviderVoiceMapping | None = None
    pronunciation_guidance: list[PronunciationGuidance] = Field(default_factory=list)
    scene_state: SceneState | None = None
    performance_intent: dict[str, Any] = Field(default_factory=dict)
    material_render_parameters: dict[str, Any] = Field(default_factory=dict)
    target_timing_policy: TargetTimingPolicy
    non_material_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_voice_resolution(self) -> "SpeechGenerationRequest":
        if self.voice_profile.speaker_key != self.speaker_key:
            raise ValueError("voice profile speakerKey must match request speakerKey")
        if self.provider_mapping is None:
            return self
        if self.provider_mapping.status is ProviderMappingStatus.RETIRED:
            raise ValueError("provider mapping must not be RETIRED")
        mapping_identity = (
            self.provider_mapping.provider,
            self.provider_mapping.model,
            self.provider_mapping.voice_id,
        )
        available = {
            (mapping.provider, mapping.model, mapping.voice_id)
            for mapping in self.voice_profile.provider_mappings
        }
        if mapping_identity not in available:
            raise ValueError("provider mapping must belong to the resolved voice profile")
        if any(
            item.speaker_key not in (None, self.speaker_key)
            for item in self.pronunciation_guidance
        ):
            raise ValueError("pronunciation guidance is scoped to another speaker")
        return self


class SpeechGenerationResult(ContractModel):
    source_uri: str
    mime_type: str
    provider_duration_ms: int | None = Field(default=None, gt=0)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class AudioReviewStatus(StrEnum):
    PASS = "PASS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    DEBUG = "DEBUG"


class AvTimelineItem(ContractModel):
    spoken_content_id: str
    audio_media_id: str
    start_ms: int = Field(ge=0)
    source_in_ms: int = Field(ge=0)
    source_out_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_slice(self) -> "AvTimelineItem":
        if self.source_out_ms <= self.source_in_ms:
            raise ValueError("sourceOutMs must be greater than sourceInMs")
        return self


class AvAssemblyManifest(ContractModel):
    schema_version: Literal["av-assembly-v1"] = "av-assembly-v1"
    source_video_media_id: str
    audio_mix_media_id: str | None = None
    speech_clip_media_ids: list[str] = Field(default_factory=list)
    timeline: list[AvTimelineItem]

    @model_validator(mode="after")
    def validate_audio_inputs(self) -> "AvAssemblyManifest":
        if self.audio_mix_media_id is None and not self.speech_clip_media_ids:
            raise ValueError("assembly requires an audio mix or speech clips")
        known = set(self.speech_clip_media_ids)
        if self.audio_mix_media_id is None and any(
            item.audio_media_id not in known for item in self.timeline
        ):
            raise ValueError("timeline audioMediaId must reference a declared speech clip")
        return self


class FinalAvFingerprintInput(ContractModel):
    schema_version: Literal["final-av-fingerprint-v1"] = "final-av-fingerprint-v1"
    manifest: AvAssemblyManifest
    source_video_content_hash: str
    audio_content_hashes: dict[str, str]
    mux_implementation: str
    mux_version: str
    mux_settings: dict[str, Any]
