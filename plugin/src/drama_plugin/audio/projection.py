from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from drama_plugin.audio.foundation import text_hash, voice_profile_fingerprint
from drama_plugin.contracts.audio import (
    PronunciationGuidance,
    SpeechGenerationRequest,
    TargetTimingPolicy,
    VoiceProfile,
)
from drama_plugin.contracts.audio_projection import (
    AudioPerformanceBrief,
    PhraseDeliverySpan,
    PaceTendency,
    VolumeTendency,
)
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import DPDSnapshot, PerformanceLevel


class AudioProjectionError(ValueError):
    pass


def _spoken_identity(spoken_content: Mapping[str, Any]) -> tuple[str, str, str]:
    canonical_id = spoken_content.get("id")
    compatibility_id = spoken_content.get("spokenContentId")
    if canonical_id and compatibility_id and canonical_id != compatibility_id:
        raise AudioProjectionError("spokenContent identity aliases conflict")
    spoken_id = str(canonical_id or compatibility_id or "").strip()
    speaker_key = str(spoken_content.get("speakerKey", "")).strip()
    exact_text = str(spoken_content.get("text", ""))
    if not spoken_id or not speaker_key or not exact_text.strip():
        raise AudioProjectionError("canonical SpokenContent id, speakerKey and text are required")
    return spoken_id, speaker_key, exact_text


def _authority_band(snapshot: DPDSnapshot) -> str:
    effective = snapshot.effective
    # authorityPosition describes the current speaker's authority. Relationship,
    # tactic and action may name the interaction target (for example, a
    # subordinate addressing a commander) and must not be reclassified as the
    # speaker's own authority.
    material = effective.authority_position.casefold()
    groups = {
        "DOMINANT": ("dominant", "superior", "coercive", "command"),
        "EQUAL": ("equal", "peer", "probe", "reciprocal"),
        "SUBORDINATE": ("subordinate", "deferential", "remonstrance"),
    }
    matches = [name for name, terms in groups.items() if any(term in material for term in terms)]
    if len(matches) != 1:
        raise AudioProjectionError("AUDIO_DIRECTION_INSUFFICIENT: authority/relationship is ambiguous")
    return matches[0]


def _performance_language(snapshot: DPDSnapshot) -> dict[str, object]:
    effective = snapshot.effective
    activation = effective.internal_activation
    control = effective.external_control
    authority = _authority_band(snapshot)

    if activation is PerformanceLevel.HIGH and control is PerformanceLevel.HIGH:
        pace = "measured and restrained despite high internal pressure"
        intensity = "compressed high intensity without emotional spill"
        control_text = "maintain high external control while preserving internal pressure"
    elif activation is PerformanceLevel.MEDIUM and control is PerformanceLevel.HIGH:
        pace = "measured and responsive, leaving room to observe the listener"
        intensity = "contained medium intensity with attentive variation"
        control_text = "maintain high external control without sounding predetermined"
    elif activation is PerformanceLevel.HIGH and control is PerformanceLevel.LOW:
        pace = "accelerated in short phrases with unstable recovery"
        intensity = "open high intensity with audible variation"
        control_text = "allow pressure to escape without losing intelligibility"
    else:
        pace = "natural and deliberate"
        intensity = "proportionate intensity without exaggeration"
        control_text = f"balance {activation.value.lower()} activation with {control.value.lower()} control"

    if authority == "DOMINANT":
        pace_tendency = PaceTendency.SLOWER
        volume_tendency = VolumeTendency.NEUTRAL
        rhythm = "apply deliberate pressure and leave consequence-bearing words room to land"
        pause = "use short tactical pauses before the consequence or demanded response"
        articulation = "firm and explicit, never substituting loudness for authority"
        ending = "close as a warning that expects compliance"
    elif authority == "EQUAL":
        pace_tendency = PaceTendency.NEUTRAL
        volume_tendency = VolumeTendency.LOWER
        rhythm = "stay responsive and leave perceptible room to read the listener's reaction"
        pause = "use brief evaluative pauses that preserve uncertainty"
        articulation = "clear but non-commanding, with pressure kept below accusation"
        ending = "remain observant and slightly open rather than final"
    else:
        pace_tendency = PaceTendency.SLOWER
        volume_tendency = VolumeTendency.LOWER
        rhythm = "shape the warning indirectly so caution remains inside formal deference"
        pause = "use brief cautionary pauses before the implied consequence"
        articulation = "precise and careful without acquiring a superior's command weight"
        ending = "leave the decision with the superior while making the risk audible"

    return {
        "pace": pace,
        "pace_tendency": pace_tendency,
        "rhythm": rhythm,
        "intensity": intensity,
        "volume_tendency": volume_tendency,
        "pause_strategy": pause,
        "articulation": articulation,
        "sentence_ending": ending,
        "control": control_text,
    }


def _brief_material(brief: AudioPerformanceBrief) -> dict[str, Any]:
    return dump_contract(brief, exclude={"fingerprint"})


def fingerprint_audio_projection(brief: AudioPerformanceBrief) -> str:
    return sha256_canonical(_brief_material(brief))


def project_audio_performance(
    *,
    dpd_snapshot: DPDSnapshot,
    spoken_content: Mapping[str, Any],
    voice_profile: VoiceProfile,
    voice_identity_ref: str,
    timing_policy: TargetTimingPolicy,
    phrase_delivery_spans: Sequence[PhraseDeliverySpan] = (),
) -> AudioPerformanceBrief:
    if dpd_snapshot is None:
        raise AudioProjectionError("DPDSnapshot is required")
    spoken_id, speaker_key, exact_text = _spoken_identity(spoken_content)
    if dpd_snapshot.line.spoken_content_id != spoken_id:
        raise AudioProjectionError("DPD and SpokenContent identity mismatch")
    if dpd_snapshot.line.speaker != speaker_key:
        raise AudioProjectionError("DPD and SpokenContent speaker mismatch")
    if voice_profile.speaker_key != speaker_key:
        raise AudioProjectionError("Voice Profile and SpokenContent speaker mismatch")
    if voice_profile.creative_profile.baseline_pace in (None, "UNKNOWN"):
        raise AudioProjectionError("Voice Profile baseline pace is required")
    if not voice_identity_ref.strip():
        raise AudioProjectionError("stable Voice or Casting identity reference is required")

    direction = _performance_language(dpd_snapshot)
    if phrase_delivery_spans:
        effective = dpd_snapshot.effective
        direction.update({
            "control": f"Address {effective.interaction_target} in the live scene: {effective.dramatic_action}. No audience address.",
            "rhythm": "Each clause advances the action toward the listener, with responsive phrasing.",
            "pause_strategy": "Brief clause turns with continuous supported breath; no broadcast cadence.",
            "articulation": f"Relationship: {effective.relationship_stance}. Position: {effective.authority_position}.",
            "sentence_ending": phrase_delivery_spans[-1].delivery,
            "pace_tendency": PaceTendency.NEUTRAL,
        })
        if any(span.end_char > len(exact_text) for span in phrase_delivery_spans):
            raise AudioProjectionError("phrase span exceeds canonical text")
    pace = f"From the {voice_profile.creative_profile.baseline_pace} voice baseline, {direction['pace']}."
    if timing_policy.policy != "NATURAL":
        pace += " Fit the approved timing window without sacrificing exact text or intelligibility."
    material: dict[str, Any] = {
        "schemaVersion": "audio-projection-v1",
        "dpdFingerprint": dpd_snapshot.fingerprint,
        "sceneId": dpd_snapshot.effective.scene_id,
        "spokenContentId": spoken_id,
        "speakerKey": speaker_key,
        "textFingerprint": text_hash(exact_text),
        "voiceProfileId": voice_profile.profile_id,
        "voiceProfileFingerprint": voice_profile_fingerprint(voice_profile),
        "voiceIdentityRef": voice_identity_ref,
        "timingContextFingerprint": sha256_canonical(dump_contract(timing_policy)),
        **direction,
        "pace": pace,
        "performanceBoundaries": dpd_snapshot.effective.performance_boundaries,
        "phraseDeliverySpans": [dump_contract(span) for span in phrase_delivery_spans],
    }
    provisional = AudioPerformanceBrief.model_validate(
        {**material, "fingerprint": "0" * 64}
    )
    return provisional.model_copy(
        update={"fingerprint": sha256_canonical(_brief_material(provisional))}
    )


def compile_projected_speech_request(
    *,
    work_id: str,
    dpd_snapshot: DPDSnapshot,
    spoken_content: Mapping[str, Any],
    voice_profile: VoiceProfile,
    voice_identity_ref: str,
    timing_policy: TargetTimingPolicy,
    phrase_delivery_spans: Sequence[PhraseDeliverySpan] = (),
    pronunciation_guidance: list[PronunciationGuidance] | None = None,
    non_material_metadata: Mapping[str, Any] | None = None,
) -> SpeechGenerationRequest:
    spoken_id, speaker_key, exact_text = _spoken_identity(spoken_content)
    brief = project_audio_performance(
        dpd_snapshot=dpd_snapshot,
        spoken_content=spoken_content,
        voice_profile=voice_profile,
        voice_identity_ref=voice_identity_ref,
        timing_policy=timing_policy,
        phrase_delivery_spans=phrase_delivery_spans,
    )
    return SpeechGenerationRequest(
        work_id=work_id,
        scene_id=dpd_snapshot.effective.scene_id,
        spoken_content_id=spoken_id,
        exact_text=exact_text,
        speaker_key=speaker_key,
        voice_profile=voice_profile.model_copy(deep=True),
        pronunciation_guidance=deepcopy(pronunciation_guidance or []),
        audio_performance_brief=brief,
        target_timing_policy=timing_policy.model_copy(deep=True),
        non_material_metadata=deepcopy(dict(non_material_metadata or {})),
    )
