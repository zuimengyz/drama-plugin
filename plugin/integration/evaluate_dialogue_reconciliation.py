"""Offline Phase A replay. No generation, acceptance, AVSync updates or mux."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from drama_plugin.contracts import (
    DialogueTimingPlan, DPDSnapshot, Media, RealizedPerformanceSnapshot,
    Scene, Shot, SpeechGenerationRequest, Voice, Work,
)
from drama_plugin.contracts.base import dump_contract
from drama_plugin.dialogue_timing import TransitionIntent
from drama_plugin.dialogue_reconciliation import reconcile_dialogue_timing


def load_inputs(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    planning = json.loads((path.parent / fixture["planningFixture"]).read_text(encoding="utf-8"))
    loaded: dict[str, Any] = {
        "plan": DialogueTimingPlan.model_validate(fixture["sourcePlan"]),
        "scene": Scene.model_validate(planning["scene"]), "shot": Shot.model_validate(planning["shot"]),
        "work": Work.model_validate(fixture["work"]),
        "dpd_by_spoken_content": {k: DPDSnapshot.model_validate(v) for k, v in planning["dpdBySpokenContent"].items()},
        "intents": {k: TransitionIntent.model_validate(v) for k, v in planning["intents"].items()},
        "video": Media.model_validate(fixture["video"]),
        "realized": RealizedPerformanceSnapshot.model_validate(fixture["realized"]),
        "accepted_realized_fingerprint": fixture["acceptedRealizedFingerprint"],
        "observed_speaker_key": fixture["observedSpeakerKey"],
        "voices": {k: Voice.model_validate(v) for k, v in fixture["voices"].items()},
        "current_audio_requests": {k: SpeechGenerationRequest.model_validate(v) for k, v in fixture["currentAudioRequests"].items()},
        "audio_candidates": [Media.model_validate(v) for v in fixture["audioCandidates"]],
    }
    if "audioDpdBySpokenContent" in fixture:
        loaded["audio_dpd_by_spoken_content"] = {
            k: DPDSnapshot.model_validate(v) for k, v in fixture["audioDpdBySpokenContent"].items()
        }
    if "audioRealizedBySpokenContent" in fixture:
        loaded["audio_realized_by_spoken_content"] = {
            k: RealizedPerformanceSnapshot.model_validate(v)
            for k, v in fixture["audioRealizedBySpokenContent"].items()
        }
    if "audioSourceVideosBySpokenContent" in fixture:
        loaded["audio_source_videos_by_spoken_content"] = {
            k: Media.model_validate(v) for k, v in fixture["audioSourceVideosBySpokenContent"].items()
        }
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--historical-comparison", type=Path)
    args = parser.parse_args()
    result = reconcile_dialogue_timing(**load_inputs(args.fixture))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "dialogue-timing-reconciliation.json").write_text(
        json.dumps(dump_contract(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    summary = {
        "turnAudio": {t.spoken_content_id: t.audio_status for t in result.turns},
        "fullDialogueCoverage": result.full_dialogue_coverage,
        "fullRealizedFeasibility": result.physical_feasibility,
        "hybridFeasibility": result.hybrid_feasibility,
        "artisticCompatibility": result.artistic_compatibility,
        "requiredMinimumMs": result.required_minimum_duration_ms,
        "actualVideoMs": result.video_duration_ms, "slackMs": result.slack_ms, "overflowMs": result.overflow_ms,
        "candidateCauses": list(result.candidate_causes),
        "proposalStatus": result.recommended_placement_status, "userTimingReview": result.user_timing_review,
        "fingerprint": result.fingerprint,
    }
    # Only after result creation: historical anchors are never reconcile inputs.
    if args.historical_comparison:
        old = json.loads(args.historical_comparison.read_text(encoding="utf-8"))
        if old["shotId"] != result.shot_id:
            raise ValueError("historical comparison Shot mismatch")
        index = next(i for i, t in enumerate(result.turns) if t.spoken_content_id == old["spokenContentId"])
        summary["comparison"] = {
            "oldUserAnchorMs": old["previousUserStartMs"],
            "plannedStartMs": result.source_plan.turns[index].planned_start_ms,
            "proposedStartMs": result.turns[index].proposed_start_ms,
        }
    (args.output / "evaluation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
