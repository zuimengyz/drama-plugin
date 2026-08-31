from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, model_validator

from drama_plugin.contracts.base import ContractModel, dump_contract, sha256_canonical
from drama_plugin.contracts.audio_projection import AudioPerformanceBrief
from drama_plugin.contracts.video_conditioned_audio import VideoConditionedAudioProjection


class ProviderMappingStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    APPROVED = "APPROVED"
    RETIRED = "RETIRED"


class VoiceUseCase(StrEnum):
    """Stable casting context; never a Scene or line-performance instruction."""

    CHARACTER_DIALOGUE = "CHARACTER_DIALOGUE"
    NARRATION = "NARRATION"


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


class CreativeCastingDimension(ContractModel):
    """One auditable artistic voice decision, explicitly not a historical fact."""

    value: str
    confidence: EvidenceConfidence = EvidenceConfidence.MEDIUM
    basis_refs: list[str] = Field(default_factory=list)


class CreativeVoiceCastingProfile(ContractModel):
    """Transient provider-neutral bridge from character evidence to casting."""

    schema_version: Literal["creative-voice-casting-v1"] = (
        "creative-voice-casting-v1"
    )
    source_profile_id: str
    voice_use_case: VoiceUseCase = VoiceUseCase.CHARACTER_DIALOGUE
    dimensions: dict[str, CreativeCastingDimension]
    historical_fact_refs: list[str] = Field(default_factory=list)
    creative_decision_basis: list[str] = Field(default_factory=list)
    semantic_invariants: list[str] = Field(
        default_factory=lambda: [
            "older life stage != simply lower pitch",
            "stable character casting != current scene performance",
        ]
    )


class VoiceDesignApproval(ContractModel):
    """Explicit human approval of one hash-addressed recovered design candidate."""

    schema_version: Literal["voice-design-approval-v1"] = "voice-design-approval-v1"
    design_request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_index: int = Field(ge=0)
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_artifact_id: str = Field(min_length=1)
    approval_source: Literal["USER"] = "USER"


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
    creative_casting_profile: CreativeVoiceCastingProfile | None = None
    provider_mapping: ProviderVoiceMapping | None = None
    pronunciation_guidance: list[PronunciationGuidance] = Field(default_factory=list)
    scene_state: SceneState | None = None
    performance_intent: dict[str, Any] = Field(default_factory=dict)
    audio_performance_brief: AudioPerformanceBrief | None = None
    video_conditioned_projection: VideoConditionedAudioProjection | None = None
    material_render_parameters: dict[str, Any] = Field(default_factory=dict)
    target_timing_policy: TargetTimingPolicy
    non_material_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_voice_resolution(self) -> "SpeechGenerationRequest":
        if self.video_conditioned_projection is not None:
            final = self.video_conditioned_projection
            if self.audio_performance_brief != final.final_audio_performance_brief:
                raise ValueError("final Audio brief must match video-conditioned projection")
            timing = self.target_timing_policy
            if (timing.policy != "NATURAL" or timing.target_duration_ms is not None
                    or timing.allow_rate_adjustment or timing.constraints):
                raise ValueError("guessed mouth timing and forced video duration are prohibited")
            if self.material_render_parameters != {"performanceRendering": "BRIEF_CUES_V1"}:
                raise ValueError("video conditioning requires Brief-derived execution only")
        if self.voice_profile.speaker_key != self.speaker_key:
            raise ValueError("voice profile speakerKey must match request speakerKey")
        if self.audio_performance_brief is not None:
            brief = self.audio_performance_brief
            if self.performance_intent or self.scene_state is not None:
                raise ValueError("DPD Audio Projection cannot be combined with legacy performance authority")
            if {"speed", "volume"} & self.material_render_parameters.keys():
                raise ValueError("DPD Audio Projection cannot be overridden by manual Fish prosody")
            if (
                brief.scene_id != self.scene_id
                or brief.spoken_content_id != self.spoken_content_id
                or brief.speaker_key != self.speaker_key
            ):
                raise ValueError("Audio Projection identity must match speech request")
            if brief.voice_profile_id != self.voice_profile.profile_id:
                raise ValueError("Audio Projection Voice Profile must match speech request")
            if brief.text_fingerprint != hashlib.sha256(self.exact_text.encode("utf-8")).hexdigest():
                raise ValueError("Audio Projection text fingerprint must match exact text")
            expected_voice_fingerprint = sha256_canonical(
                {
                    "schemaVersion": "voice-creative-profile-v1",
                    "speakerKey": self.voice_profile.speaker_key,
                    "creativeProfile": dump_contract(self.voice_profile.creative_profile),
                }
            )
            if brief.voice_profile_fingerprint != expected_voice_fingerprint:
                raise ValueError("Audio Projection Voice Profile fingerprint must match speech request")
            expected_projection_fingerprint = sha256_canonical(
                dump_contract(brief, exclude={"fingerprint"})
            )
            if brief.fingerprint != expected_projection_fingerprint:
                raise ValueError("Audio Projection fingerprint is invalid")
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


class IntelligibilityQcStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class IntelligibilityQc(ContractModel):
    status: IntelligibilityQcStatus
    cer: float = Field(ge=0)
    normalized_transcript: str
    missing: list[str] = Field(default_factory=list)
    extra: list[str] = Field(default_factory=list)
    repetition: list[str] = Field(default_factory=list)
    proper_noun_findings: list[str] = Field(default_factory=list)
    same_vendor_as_tts: bool = True


class RoleDubbingQcPolicy(ContractModel):
    max_cer: float = Field(default=0.2, ge=0, le=1)
    require_no_missing: bool = True
    require_no_extra: bool = True
    require_no_repetition: bool = True
    require_proper_nouns: bool = True


class RoleDubbingRequest(ContractModel):
    schema_version: Literal["role-dubbing-v1"] = "role-dubbing-v1"
    speech_request: SpeechGenerationRequest
    qc_policy: RoleDubbingQcPolicy = Field(default_factory=RoleDubbingQcPolicy)
    voice_design_approval: VoiceDesignApproval | None = None


class RoleDubbingResult(ContractModel):
    audio_media_id: str
    voice_id: str
    duration_ms: int = Field(gt=0)
    intelligibility_qc: IntelligibilityQc
    lifecycle_branch: Literal["EXISTING_MAPPING", "MATERIALIZED_MAPPING", "NEW_VOICE"]
    voice_design_calls: int = Field(ge=0)
    create_model_calls: int = Field(ge=0)


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
