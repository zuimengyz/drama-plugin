"""Small adapter-side safeguards. No workflow discovery or speaker guessing."""
from __future__ import annotations

from typing import Any, Mapping

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.media import Media, MediaType


def prepare_speaker_operation(
    *, video: Media, audio: Media, speaker_key: str, start_ms: int, end_ms: int,
    capability: Mapping[str, Any], selection: Mapping[str, Any],
) -> dict[str, Any]:
    if (capability.get("explicitSpeakerSelection") is not True
            or not capability.get("evidenceRef") or not capability.get("workflowId")
            or not capability.get("selectionParameter")
            or capability["selectionParameter"] not in selection):
        raise ValueError("LIP_SYNC_CAPABILITY_BLOCKED")
    if (selection.get("speakerKey") != speaker_key or not selection.get("identityEvidence")
            or selection.get("videoHash") != video.content_hash):
        raise ValueError("LIP_SYNC_SPEAKER_IDENTITY_UNVERIFIED")
    if (video.media_type != MediaType.VIDEO or audio.media_type != MediaType.AUDIO
            or audio.work_id != video.work_id or audio.content.get("speakerKey") != speaker_key
            or video.duration_ms is None or not video.content_hash or not audio.content_hash
            or not 0 <= start_ms < end_ms <= video.duration_ms or end_ms - start_ms != audio.duration_ms):
        raise ValueError("LIP_SYNC_WINDOW_OR_AUDIO_MISMATCH")
    material = {"sourceVideoHash": video.content_hash, "audioHash": audio.content_hash,
                "speakerKey": speaker_key, "startMs": start_ms, "endMs": end_ms,
                "workflowId": capability["workflowId"], "selection": dict(selection),
                "capabilityEvidence": capability["evidenceRef"], "audioChangesAllowed": False,
                "timingChangesAllowed": False}
    return {**material, "fingerprint": sha256_canonical(material)}


def validate_lip_derivative(
    *, operation: Mapping[str, Any], derivative_video_hash: str,
    source_duration_ms: int, derivative_duration_ms: int, audio_hash: str,
    qc: Mapping[str, Any],
) -> dict[str, Any]:
    if operation.get("fingerprint") != sha256_canonical({k:v for k,v in operation.items() if k != "fingerprint"}):
        raise ValueError("STALE_LIP_OPERATION")
    if (source_duration_ms != derivative_duration_ms or audio_hash != operation["audioHash"]
            or derivative_video_hash == operation["sourceVideoHash"] or len(derivative_video_hash) != 64):
        raise ValueError("LIP_SYNC_AUDIO_TIMING_OR_OUTPUT_CHANGED")
    required = ("activeSpeakerMouth", "nonSpeakerMouthSafety", "identityPreservation", "eyes",
                "beard", "skin", "costume", "background", "camera", "temporalContinuity")
    if any(qc.get(k) != "PASS" for k in required) or not qc.get("observationEvidence"):
        raise ValueError("LIP_SYNC_DERIVATIVE_QC_FAILED")
    material = {"sourceVideoHash":operation["sourceVideoHash"], "derivativeVideoHash":derivative_video_hash,
                "lipOperationFingerprint":operation["fingerprint"], "audioHash":audio_hash,
                "durationMs":derivative_duration_ms, "qc":dict(qc), "newObservationRequired":True}
    return {**material,"fingerprint":sha256_canonical(material)}
