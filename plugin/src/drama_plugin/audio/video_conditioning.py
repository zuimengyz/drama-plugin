from __future__ import annotations

from typing import Any, Mapping

from drama_plugin.audio.foundation import voice_profile_fingerprint
from drama_plugin.audio.projection import project_audio_performance, fingerprint_audio_projection
from drama_plugin.contracts.audio import SpeechGenerationRequest
from drama_plugin.contracts.audio_projection import AudioPerformanceBrief
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import DPDSnapshot, PerformanceLevel
from drama_plugin.contracts.media import Media, MediaType
from drama_plugin.contracts.video_conditioned_audio import VideoConditionedAudioProjection
from drama_plugin.contracts.visual_performance import RealizedPerformanceSnapshot
from drama_plugin.dpd import compose_dpd
from drama_plugin.visual import fingerprint_realized_performance


def condition_audio_on_video(
    *,
    base_request: SpeechGenerationRequest,
    dpd_snapshot: DPDSnapshot,
    realized_snapshot: RealizedPerformanceSnapshot,
    video_media: Media,
    shot_id: str,
    shot_scene_id: str,
    shot_spoken_content_ids: tuple[str, ...],
    canonical_spoken_content: Mapping[str, Any],
    observed_speaker_key: str,
    bound_voice_id: str,
    voice_content_hash: str,
    accepted_realized_fingerprint: str,
) -> SpeechGenerationRequest:
    """Condition execution on accepted pixels while preserving dramatic/text/voice authority."""
    if dpd_snapshot is None or realized_snapshot is None:
        raise ValueError("DPDSnapshot and RealizedPerformanceSnapshot are required")
    if base_request.video_conditioned_projection is not None:
        raise ValueError("base request is already video-conditioned")
    if base_request.material_render_parameters not in (
        {}, {"performanceRendering": "BRIEF_CUES_V1"}, {"performanceRendering": "PHRASE_CUES_V1"}
    ):
        raise ValueError("unsupported base rendering parameters; no silent overwrite")
    dpd = compose_dpd(dpd_snapshot.scene, dpd_snapshot.beat, dpd_snapshot.line)
    if dpd != dpd_snapshot:
        raise ValueError("DPDSnapshot fingerprint/effective facts are stale")
    realized = RealizedPerformanceSnapshot.model_validate(dump_contract(realized_snapshot))
    if not (
        realized.fingerprint == fingerprint_realized_performance(realized)
        == accepted_realized_fingerprint
    ):
        raise ValueError("stale realized fingerprint")
    if (video_media.media_type is not MediaType.VIDEO
            or video_media.id != realized.video_media_id
            or video_media.content_hash != realized.video_content_hash):
        raise ValueError("snapshot/video identity or hash mismatch")
    if (shot_id != realized.shot_id or video_media.shot_id != shot_id
            or video_media.work_id != base_request.work_id):
        raise ValueError("Shot/Video ownership mismatch")
    if shot_scene_id != dpd.effective.scene_id or shot_scene_id != base_request.scene_id:
        raise ValueError("Scene mismatch")
    if (base_request.speaker_key != observed_speaker_key
            or dpd.effective.actor != observed_speaker_key
            or dpd.effective.speaker != observed_speaker_key):
        raise ValueError("observed speaker mismatch")
    if base_request.spoken_content_id not in shot_spoken_content_ids:
        raise ValueError("SpokenContent binding mismatch")
    if canonical_spoken_content.get("text") != base_request.exact_text:
        raise ValueError("canonical SpokenContent text mismatch")
    timing = base_request.target_timing_policy
    if (timing.policy != "NATURAL" or timing.target_duration_ms is not None
            or timing.allow_rate_adjustment or timing.constraints):
        raise ValueError("natural delivery required; guessed mouth timing is prohibited")
    if base_request.performance_intent or base_request.scene_state is not None:
        raise ValueError("legacy performance authority conflict")
    base = project_audio_performance(
        dpd_snapshot=dpd, spoken_content=canonical_spoken_content,
        voice_profile=base_request.voice_profile, voice_identity_ref=bound_voice_id,
        timing_policy=timing,
    )
    authored = base_request.audio_performance_brief
    if authored is not None and authored.phrase_delivery_spans:
        SpeechGenerationRequest.model_validate(dump_contract(base_request))
        if (authored.dpd_fingerprint != dpd.fingerprint or authored.voice_identity_ref != bound_voice_id
                or authored.fingerprint != fingerprint_audio_projection(authored)):
            raise ValueError("authored base projection binding mismatch")
        base = authored
    if realized.observed_speaker_key not in (None, observed_speaker_key):
        raise ValueError("RP observed speaker mismatch")
    if base != base_request.audio_performance_brief:
        raise ValueError("base projection, SpokenContent or Voice binding mismatch")
    if len(voice_content_hash) != 64 or any(c not in "0123456789abcdef" for c in voice_content_hash):
        raise ValueError("Voice master content hash required")

    high_control = dpd.effective.external_control is PerformanceLevel.HIGH
    pressure = dpd.effective.internal_activation is PerformanceLevel.HIGH
    tension = realized.facial_tension == "HIGH"
    changing = realized.expression_change == "PRESENT" or bool(realized.major_head_motion_windows_ms)
    # No gaze-down -> emotion/volume or head-speed -> speech-speed shortcuts.
    updates: dict[str, Any] = {
        "pace": base.pace + " Use natural dialogue duration, never fill the video duration.",
        "control": (
            "contained interpersonal delivery, keeping pressure under audible control"
            if high_control else "responsive interpersonal delivery with intelligible variation"
        ),
        "intensity": (
            "internally tense without raised volume"
            if pressure and tension else "proportionate pressure without exaggerated projection"
        ),
        "rhythm": (
            "responsive short-clause variation without automatic acceleration"
            if realized.visible_activation == "HIGH"
            else "direct opening, measured progression, clear interpersonal ending"
        ),
        "pause_strategy": (
            "a small clause-boundary turn, then recover direct address; no timed pause"
            if changing else "natural clause pauses without adding a visual-event pause"
        ),
        "sentence_ending": f"recover clear finality while carrying the action: {dpd.effective.dramatic_action}",
    }
    if base.phrase_delivery_spans:
        # Preserve approved interpersonal/phrase/ending directions. An observed
        # motion is evidence for review, never a mandatory vocal reinterpretation.
        updates = {}
    material = {**base.model_dump(mode="json", exclude={"fingerprint"}), **updates}
    final_brief = AudioPerformanceBrief.model_validate({**material, "fingerprint": "0" * 64})
    final_brief = final_brief.model_copy(update={
        "fingerprint": sha256_canonical(dump_contract(final_brief, exclude={"fingerprint"}))
    })
    wrapper_material = {
        "schemaVersion": "video-conditioned-audio-v1",
        "baseAudioProjectionFingerprint": base.fingerprint,
        "realizedPerformanceFingerprint": realized.fingerprint,
        "videoMediaId": video_media.id,
        "videoContentHash": realized.video_content_hash,
        "shotId": shot_id,
        "voiceMaterialFingerprint": sha256_canonical({
            "voiceId": bound_voice_id, "masterHash": voice_content_hash,
            "voiceProfileFingerprint": voice_profile_fingerprint(base_request.voice_profile),
        }),
        "finalAudioPerformanceBrief": dump_contract(final_brief),
    }
    wrapper = VideoConditionedAudioProjection.model_validate({
        **wrapper_material, "fingerprint": sha256_canonical(wrapper_material)
    })
    payload = dump_contract(base_request)
    payload.update({"audioPerformanceBrief": dump_contract(final_brief),
                    "videoConditionedProjection": dump_contract(wrapper),
                    "materialRenderParameters": {"performanceRendering": "PHRASE_CUES_V1" if base.phrase_delivery_spans else "BRIEF_CUES_V1"}})
    return SpeechGenerationRequest.model_validate(payload)
