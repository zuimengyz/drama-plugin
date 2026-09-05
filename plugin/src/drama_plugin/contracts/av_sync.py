from __future__ import annotations

from typing import Annotated, Literal, Mapping, Sequence

from pydantic import Field, StringConstraints, model_validator

from drama_plugin.contracts.base import ContractModel, dump_contract, sha256_canonical


NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Fingerprint = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
PositiveMs = Annotated[int, Field(gt=0)]
NonNegativeMs = Annotated[int, Field(ge=0)]

TimingAuthority = Literal[
    "EXPLICIT_PRODUCTION_ANCHOR",
    "OBSERVED_MOUTH_ACTIVITY",
    "AUDIO_DRIVEN_ALIGNMENT",
    "USER_REVIEW",
    "USER_REVIEW_ANCHOR",
    "NONE",
]
LipSyncPolicy = Literal[
    "NOT_REQUIRED",
    "MOUTH_ONLY_DERIVATIVE",
    "AUDIO_DRIVEN_RETARGET",
    "OBSERVED_ALIGNMENT",
    "NOT_APPLIED_FOR_LOW_VISIBILITY",
    "UNSUPPORTED",
    "BLOCKED",
]


class AVSyncPlan(ContractModel):
    """Provider-neutral placement decision for one frozen Video and D1 pair."""

    schema_version: Literal["av-sync-plan-v1"] = "av-sync-plan-v1"
    shot_id: NonBlankText
    spoken_content_id: NonBlankText
    speaker_key: NonBlankText
    video_media_id: NonBlankText
    video_content_hash: Fingerprint
    video_duration_ms: PositiveMs
    dialogue_media_id: NonBlankText
    dialogue_content_hash: Fingerprint
    dialogue_duration_ms: PositiveMs
    timing_authority: TimingAuthority
    dialogue_start_ms: NonNegativeMs | None = None
    dialogue_end_ms: PositiveMs | None = None
    lip_sync_policy: LipSyncPolicy
    alignment_confidence: Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    fingerprint: Fingerprint

    @model_validator(mode="after")
    def validate_timing_and_fingerprint(self) -> "AVSyncPlan":
        has_start = self.dialogue_start_ms is not None
        has_end = self.dialogue_end_ms is not None
        if has_start != has_end:
            raise ValueError("dialogueStartMs and dialogueEndMs must be supplied together")
        if self.timing_authority == "NONE":
            if has_start or has_end:
                raise ValueError("timingAuthority=NONE cannot carry fabricated dialogue timing")
            if self.alignment_confidence != "UNKNOWN":
                raise ValueError("timingAuthority=NONE requires UNKNOWN confidence")
        elif not has_start:
            raise ValueError("a material timing authority requires a complete dialogue window")

        if has_start and has_end:
            assert self.dialogue_start_ms is not None
            assert self.dialogue_end_ms is not None
            if self.dialogue_end_ms <= self.dialogue_start_ms:
                raise ValueError("dialogueEndMs must be greater than dialogueStartMs")
            if self.dialogue_end_ms > self.video_duration_ms:
                raise ValueError("dialogue window exceeds video duration")
            if self.dialogue_end_ms - self.dialogue_start_ms != self.dialogue_duration_ms:
                raise ValueError("dialogue window must preserve the frozen D1 duration")

        if (
            self.lip_sync_policy == "OBSERVED_ALIGNMENT"
            and self.timing_authority != "OBSERVED_MOUTH_ACTIVITY"
        ):
            raise ValueError("observed alignment requires observed mouth timing authority")
        if (
            self.lip_sync_policy == "AUDIO_DRIVEN_RETARGET"
            and self.timing_authority != "AUDIO_DRIVEN_ALIGNMENT"
        ):
            raise ValueError("audio-driven retarget requires audio-driven timing authority")
        if self.lip_sync_policy == "MOUTH_ONLY_DERIVATIVE" and self.timing_authority not in (
            "USER_REVIEW", "USER_REVIEW_ANCHOR", "EXPLICIT_PRODUCTION_ANCHOR"
        ):
            raise ValueError("mouth-only derivative preserves a reviewed or explicit production window")
        expected = sha256_canonical(dump_contract(self, exclude={"fingerprint"}))
        if self.fingerprint != expected:
            raise ValueError("AV Sync fingerprint is invalid")
        return self


class AcousticMixPlan(ContractModel):
    """Provider-neutral acoustic bindings and conservative mix intent for one Shot."""

    schema_version: Literal["acoustic-mix-plan-v1"] = "acoustic-mix-plan-v1"
    work_id: NonBlankText
    scene_id: NonBlankText
    shot_id: NonBlankText
    dialogue_media_id: NonBlankText
    dialogue_content_hash: Fingerprint
    dialogue_perspective: Literal[
        "CLOSE_CONVERSATIONAL", "MID_DISTANCE", "DISTANT", "UNKNOWN"
    ]
    ambience_bindings: dict[NonBlankText, Fingerprint] = Field(default_factory=dict)
    sfx_bindings: dict[NonBlankText, Fingerprint] = Field(default_factory=dict)
    spatial_treatment: Literal["NONE", "SUBTLE_INTERIOR_REFLECTION"] = "NONE"
    dialogue_gain_db: float = Field(default=0.0, ge=-12.0, le=6.0)
    ambience_gain_db: float | None = Field(default=None, ge=-60.0, le=0.0)
    sfx_gain_db: float | None = Field(default=None, ge=-60.0, le=0.0)
    music_policy: Literal["NONE"] = "NONE"
    fingerprint: Fingerprint

    @model_validator(mode="after")
    def validate_bindings_and_fingerprint(self) -> "AcousticMixPlan":
        overlap = set(self.ambience_bindings) & set(self.sfx_bindings)
        if overlap:
            raise ValueError("one Media cannot be both ambience and SFX")
        if not self.ambience_bindings and self.ambience_gain_db is not None:
            raise ValueError("ambience gain requires a bound ambience Media")
        if self.ambience_bindings and self.ambience_gain_db is None:
            raise ValueError("bound ambience Media requires an ambience gain")
        if not self.sfx_bindings and self.sfx_gain_db is not None:
            raise ValueError("SFX gain requires a bound SFX Media")
        if self.sfx_bindings and self.sfx_gain_db is None:
            raise ValueError("bound SFX Media requires an SFX gain")
        expected = sha256_canonical(dump_contract(self, exclude={"fingerprint"}))
        if self.fingerprint != expected:
            raise ValueError("Acoustic Mix fingerprint is invalid")
        return self


def build_av_sync_plan(
    *,
    shot_id: str,
    spoken_content_id: str,
    speaker_key: str,
    video_media_id: str,
    video_content_hash: str,
    video_duration_ms: int,
    dialogue_media_id: str,
    dialogue_content_hash: str,
    dialogue_duration_ms: int,
    timing_authority: TimingAuthority,
    dialogue_start_ms: int | None,
    dialogue_end_ms: int | None,
    lip_sync_policy: LipSyncPolicy,
    alignment_confidence: Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"],
) -> AVSyncPlan:
    payload: dict[str, object] = {
        "schemaVersion": "av-sync-plan-v1",
        "shotId": shot_id,
        "spokenContentId": spoken_content_id,
        "speakerKey": speaker_key,
        "videoMediaId": video_media_id,
        "videoContentHash": video_content_hash,
        "videoDurationMs": video_duration_ms,
        "dialogueMediaId": dialogue_media_id,
        "dialogueContentHash": dialogue_content_hash,
        "dialogueDurationMs": dialogue_duration_ms,
        "timingAuthority": timing_authority,
        "dialogueStartMs": dialogue_start_ms,
        "dialogueEndMs": dialogue_end_ms,
        "lipSyncPolicy": lip_sync_policy,
        "alignmentConfidence": alignment_confidence,
    }
    payload["fingerprint"] = sha256_canonical(payload)
    return AVSyncPlan.model_validate(payload)


def build_acoustic_mix_plan(
    *,
    work_id: str,
    scene_id: str,
    shot_id: str,
    dialogue_media_id: str,
    dialogue_content_hash: str,
    dialogue_perspective: Literal[
        "CLOSE_CONVERSATIONAL", "MID_DISTANCE", "DISTANT", "UNKNOWN"
    ],
    ambience_bindings: Mapping[str, str] | None = None,
    sfx_bindings: Mapping[str, str] | None = None,
    spatial_treatment: Literal["NONE", "SUBTLE_INTERIOR_REFLECTION"] = "NONE",
    dialogue_gain_db: float = 0.0,
    ambience_gain_db: float | None = None,
    sfx_gain_db: float | None = None,
    ambience_scope: Mapping[str, tuple[str, str]] | None = None,
    sfx_scope: Mapping[str, tuple[str, str]] | None = None,
) -> AcousticMixPlan:
    """Validate optional (workId, sceneId) ownership before freezing bindings."""

    for label, scopes in (("ambience", ambience_scope), ("SFX", sfx_scope)):
        for media_id, scope in (scopes or {}).items():
            if scope != (work_id, scene_id):
                raise ValueError(f"{label} Media {media_id} belongs to another Work/Scene")
    payload: dict[str, object] = {
        "schemaVersion": "acoustic-mix-plan-v1",
        "workId": work_id,
        "sceneId": scene_id,
        "shotId": shot_id,
        "dialogueMediaId": dialogue_media_id,
        "dialogueContentHash": dialogue_content_hash,
        "dialoguePerspective": dialogue_perspective,
        "ambienceBindings": dict(ambience_bindings or {}),
        "sfxBindings": dict(sfx_bindings or {}),
        "spatialTreatment": spatial_treatment,
        "dialogueGainDb": float(dialogue_gain_db),
        "ambienceGainDb": (
            None if ambience_gain_db is None else float(ambience_gain_db)
        ),
        "sfxGainDb": None if sfx_gain_db is None else float(sfx_gain_db),
        "musicPolicy": "NONE",
    }
    payload["fingerprint"] = sha256_canonical(payload)
    return AcousticMixPlan.model_validate(payload)


def final_shot_fingerprint(
    *,
    sync_plan: AVSyncPlan,
    mix_plan: AcousticMixPlan,
    ambience_content_hashes: Sequence[str] = (),
    sfx_content_hashes: Sequence[str] = (),
    assembly_schema_version: str = "final-shot-assembly-v1",
) -> str:
    """Freeze final lineage only when dialogue placement is actually resolved."""

    if sync_plan.dialogue_start_ms is None or sync_plan.dialogue_end_ms is None:
        raise ValueError("Final Shot fingerprint requires resolved dialogue placement")
    if sync_plan.dialogue_media_id != mix_plan.dialogue_media_id:
        raise ValueError("AV Sync and Acoustic Mix plans reference different D1 Media")
    if sync_plan.dialogue_content_hash != mix_plan.dialogue_content_hash:
        raise ValueError("AV Sync and Acoustic Mix plans reference different D1 hashes")
    if sync_plan.shot_id != mix_plan.shot_id:
        raise ValueError("AV Sync and Acoustic Mix plans reference different Shots")
    expected_ambience = sorted(mix_plan.ambience_bindings.values())
    expected_sfx = sorted(mix_plan.sfx_bindings.values())
    if sorted(ambience_content_hashes) != expected_ambience:
        raise ValueError("Final Shot ambience hashes do not match Acoustic Mix plan")
    if sorted(sfx_content_hashes) != expected_sfx:
        raise ValueError("Final Shot SFX hashes do not match Acoustic Mix plan")
    return sha256_canonical(
        {
            "schemaVersion": assembly_schema_version,
            "videoContentHash": sync_plan.video_content_hash,
            "dialogueContentHash": sync_plan.dialogue_content_hash,
            "avSyncPlanFingerprint": sync_plan.fingerprint,
            "acousticMixPlanFingerprint": mix_plan.fingerprint,
            "ambienceContentHashes": expected_ambience,
            "sfxContentHashes": expected_sfx,
        }
    )
