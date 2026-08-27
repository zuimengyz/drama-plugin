from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integration"))

from run_fish_role_dubbing_validation import (  # noqa: E402
    build_voice_casting_brief,
    candidate_casting_score,
    parse_references,
)


def test_no_local_reference_selects_voice_design_for_both_roles() -> None:
    args = argparse.Namespace(
        reference_manifest=None,
        speaker_key=None,
        reference_audio=None,
        dialogue_id=None,
    )
    specs = parse_references(args)
    assert [item.speaker_key for item in specs] == [
        "speaker:wangsili",
        "speaker:geshuhan",
    ]
    assert all(item.reference_audio is None for item in specs)


def test_casting_brief_uses_only_supported_stable_non_unknown_fields() -> None:
    profile: dict[str, Any] = {
        "language": "zh-CN",
        "baselinePace": "MODERATE",
        "articulationFirmness": "FIRM",
        "phraseAttack": "DIRECT_REQUEST",
        "commandPresence": "MEDIUM_EXECUTION_CAPABLE",
        "sentenceFinality": "OPEN_FOR_SUPERIOR_DECISION",
        "vocalAge": None,
        "vocalWeight": "UNKNOWN",
        "sceneState": "MUST_NOT_BE_USED",
        "performanceIntent": "MUST_NOT_BE_USED",
        "characterName": "MUST_NOT_BE_USED",
    }
    brief = build_voice_casting_brief(profile)
    assert brief["profileSource"] == "EXISTING_FROZEN_VOICE_PROFILE"
    assert "vocalAge" in brief["excludedUnknownFields"]
    assert "vocalWeight" in brief["excludedUnknownFields"]
    serialized = str(brief)
    assert "MUST_NOT_BE_USED" not in serialized
    assert "characterName" not in serialized


def test_casting_score_is_identity_invariant_and_excludes_unknown_dimensions() -> None:
    candidate = {
        "durationMs": 3000,
        "previewText": "此事若行，我便是反臣。不可。",
        "intelligibilityQc": {
            "cer": 0.0,
            "status": "PASS",
            "missingCharacters": [],
            "extraCharacters": [],
            "properNounMismatches": [],
            "repetitions": [],
        },
        "signalAnalysis": {
            "tailToOverallRmsRatio": 0.5,
            "crestFactorDb": 12.0,
            "lowPassToSignalRmsRatio": 0.55,
            "differenceToSignalRmsRatio": 0.65,
            "envelopeVariation": 0.3,
            "zeroCrossingRate": 0.08,
            "obviousClipping": False,
        },
    }
    profile = {
        "baselinePace": "MODERATE_DELIBERATE",
        "sentenceFinality": "HIGH",
        "controlledPower": "HIGH_WITHOUT_LOUDNESS_REQUIREMENT",
        "vocalAge": None,
    }
    first = candidate_casting_score(candidate=candidate, creative_profile=profile)
    second = candidate_casting_score(
        candidate=candidate,
        creative_profile={
            **profile,
            "speakerKey": "different-identity-must-not-matter",
            "sceneState": "different-scene-must-not-matter",
        },
    )
    assert first == second
    assert first["eligible"] is True
    assert first["selectionDimensions"]["vocalAge"] == "EXCLUDED_UNKNOWN"


def test_candidate_missing_a_short_final_clause_is_not_casting_eligible() -> None:
    candidate = {
        "durationMs": 3000,
        "previewText": "此事若行，我便是反臣。不可。",
        "intelligibilityQc": {
            "cer": 2 / 11,
            "status": "FAIL",
            "missingCharacters": ["不", "可"],
            "extraCharacters": [],
            "properNounMismatches": [],
            "repetitions": [],
        },
        "signalAnalysis": {
            "tailToOverallRmsRatio": 0.5,
            "crestFactorDb": 12.0,
            "lowPassToSignalRmsRatio": 0.55,
            "differenceToSignalRmsRatio": 0.65,
            "envelopeVariation": 0.3,
            "zeroCrossingRate": 0.08,
            "obviousClipping": False,
        },
    }
    score = candidate_casting_score(
        candidate=candidate,
        creative_profile={
            "baselinePace": "MODERATE_DELIBERATE",
            "sentenceFinality": "HIGH",
            "controlledPower": "HIGH_WITHOUT_LOUDNESS_REQUIREMENT",
        },
    )
    assert score["eligible"] is False
    assert score["candidateQcStatus"] == "FAIL"
    assert score["score"] == 0.0


def test_repaired_casting_uses_acoustic_dimensions_after_technical_qc() -> None:
    candidate = {
        "durationMs": 3200,
        "previewText": "此事若行，我便是反臣。不可。",
        "intelligibilityQc": {
            "cer": 0.0,
            "status": "PASS",
            "missingCharacters": [],
            "extraCharacters": [],
            "properNounMismatches": [],
            "repetitions": [],
        },
        "signalAnalysis": {
            "tailToOverallRmsRatio": 0.5,
            "crestFactorDb": 12.0,
            "lowPassToSignalRmsRatio": 0.62,
            "differenceToSignalRmsRatio": 0.5,
            "envelopeVariation": 0.35,
            "zeroCrossingRate": 0.07,
            "obviousClipping": False,
        },
    }
    score = candidate_casting_score(
        candidate=candidate,
        creative_profile={
            "baselinePace": "MODERATE_DELIBERATE",
            "sentenceFinality": "HIGH",
            "vocalAge": "LATE_MIDDLE_ADULT",
            "vocalWeight": "MEDIUM_HEAVY",
            "resonance": "DEEP",
            "brightness": "SLIGHTLY_DARK",
            "texture": "DRY_AGE_TEXTURED",
            "roughness": "LOW_MEDIUM",
            "breathiness": "LOW",
        },
    )
    assert score["technicalQc"]["status"] == "PASS"
    assert score["voiceFit"]["status"] == "PASS"
    assert isinstance(score["selectionDimensions"]["vocalAge"], dict)
    assert score["selectionDimensions"]["vocalAge"]["confidence"] == (
        "LOW_ACOUSTIC_PROXY"
    )
