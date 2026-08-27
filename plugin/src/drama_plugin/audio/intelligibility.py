from __future__ import annotations

import math
import re
import unicodedata
import wave
from array import array
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from drama_plugin.contracts.audio import (
    CreativeVoiceCastingProfile,
    IntelligibilityQc,
    IntelligibilityQcStatus,
    RoleDubbingQcPolicy,
)


def normalize_transcript(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_value in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_value in enumerate(right, start=1):
            current.append(min(current[-1] + 1, previous[right_index] + 1,
                               previous[right_index - 1] + (left_value != right_value)))
        previous = current
    return previous[-1]


def intelligibility_qc(
    *, canonical_text: str, transcript: str, proper_nouns: list[str], policy: RoleDubbingQcPolicy
) -> IntelligibilityQc:
    canonical = normalize_transcript(canonical_text)
    observed = normalize_transcript(transcript)
    matcher = SequenceMatcher(a=canonical, b=observed, autojunk=False)
    missing: list[str] = []
    extra: list[str] = []
    for operation, left_start, left_end, right_start, right_end in matcher.get_opcodes():
        if operation in {"delete", "replace"} and left_start != left_end:
            missing.append(canonical[left_start:left_end])
        if operation in {"insert", "replace"} and right_start != right_end:
            extra.append(observed[right_start:right_end])
    repetitions = [value for value in extra if value and value in canonical]
    proper_findings = [term for term in proper_nouns
                       if normalize_transcript(term) in canonical and normalize_transcript(term) not in observed]
    cer = _edit_distance(canonical, observed) / max(1, len(canonical))
    passed = (
        cer <= policy.max_cer
        and (not policy.require_no_missing or not missing)
        and (not policy.require_no_extra or not extra)
        and (not policy.require_no_repetition or not repetitions)
        and (not policy.require_proper_nouns or not proper_findings)
    )
    return IntelligibilityQc(
        status=IntelligibilityQcStatus.PASS if passed else IntelligibilityQcStatus.FAIL,
        cer=cer,
        normalized_transcript=observed,
        missing=missing,
        extra=extra,
        repetition=repetitions,
        proper_noun_findings=proper_findings,
        same_vendor_as_tts=True,
    )


def analyze_pcm_wav(path: Path) -> dict[str, float | bool]:
    try:
        with wave.open(str(path), "rb") as source:
            if source.getsampwidth() != 2 or source.getnchannels() != 1:
                raise ValueError("Voice candidate must be 16-bit mono WAV")
            sample_rate = source.getframerate()
            samples = array("h", source.readframes(source.getnframes()))
    except (wave.Error, EOFError) as exc:
        raise ValueError("Voice candidate is not valid PCM WAV") from exc
    if not samples or sample_rate <= 0:
        raise ValueError("Voice candidate contains no samples")
    values = [float(value) for value in samples]
    peak = max(abs(value) for value in values)
    rms = math.sqrt(sum(value * value for value in values) / len(values))
    clipped = sum(1 for value in values if abs(value) >= 32760)
    tail = values[-max(1, round(sample_rate * 0.2)):]
    tail_rms = math.sqrt(sum(value * value for value in tail) / len(tail))
    zero_crossings = sum(1 for left, right in zip(values, values[1:])
                         if (left < 0 <= right) or (left >= 0 > right))
    difference_rms = math.sqrt(sum((right - left) ** 2 for left, right in zip(values, values[1:]))
                               / max(1, len(values) - 1))
    alpha = 1.0 - math.exp(-2.0 * math.pi * 500.0 / sample_rate)
    low_pass = 0.0
    low_energy = 0.0
    for sample in values:
        low_pass += alpha * (sample - low_pass)
        low_energy += low_pass * low_pass
    window_size = max(1, round(sample_rate * 0.05))
    window_rms = [math.sqrt(sum(value * value for value in window) / len(window))
                  for start in range(0, len(values), window_size)
                  if (window := values[start:start + window_size])]
    envelope_mean = sum(window_rms) / len(window_rms)
    envelope_variation = (math.sqrt(sum((value - envelope_mean) ** 2 for value in window_rms)
                                    / len(window_rms)) / envelope_mean) if envelope_mean else 0.0
    return {
        "crestFactorDb": 20 * math.log10(peak / rms) if peak and rms else 0.0,
        "tailToOverallRmsRatio": tail_rms / rms if rms else 0.0,
        "zeroCrossingRate": zero_crossings / max(1, len(values) - 1),
        "differenceToSignalRmsRatio": difference_rms / rms if rms else 0.0,
        "lowPassToSignalRmsRatio": math.sqrt(low_energy / len(values)) / rms if rms else 0.0,
        "envelopeVariation": envelope_variation,
        "obviousClipping": clipped / len(values) > 0.001,
    }


def creative_fit_score(
    *, evidence: dict[str, Any], profile: CreativeVoiceCastingProfile, duration_ms: int,
    reference_text: str,
) -> tuple[float, dict[str, Any]]:
    def clamp(value: float) -> float:
        return max(0.0, min(1.0, value))
    targets = {name: item.value for name, item in profile.dimensions.items()}
    cps = len(normalize_transcript(reference_text)) / max(0.001, duration_ms / 1000)
    pace_midpoint = 4.0 if "DELIBERATE" in targets.get("baselinePace", "") else 5.25
    dimensions: dict[str, Any] = {
        "baselinePace": clamp(1.0 - abs(cps - pace_midpoint) / pace_midpoint),
        "sentenceEnding": clamp(float(evidence["tailToOverallRmsRatio"]) / 0.45),
        "controlledPower": clamp(1.0 - abs(float(evidence["crestFactorDb"]) - 12.0) / 12.0),
    }
    low = clamp((float(evidence["lowPassToSignalRmsRatio"]) - 0.2) / 0.65)
    brightness = clamp(float(evidence["differenceToSignalRmsRatio"]) / 1.4)
    texture = clamp(float(evidence["envelopeVariation"]) * 0.75
                    + float(evidence["zeroCrossingRate"]) * 3.0)
    observations = {
        "vocalAge": clamp((low * 2 + (1 - brightness) + texture) / 4),
        "vocalWeight": low, "resonance": low, "brightness": brightness,
        "texture": texture, "roughness": texture,
        "breathiness": clamp(brightness * 0.55 + float(evidence["zeroCrossingRate"]) * 2.0),
    }
    target_values = {
        "vocalAge": {"MATURE_ADULT": 0.55, "LATE_MIDDLE_ADULT": 0.72},
        "vocalWeight": {"MEDIUM": 0.5, "MEDIUM_HEAVY": 0.7},
        "resonance": {"BALANCED": 0.5, "DEEP": 0.72},
        "brightness": {"NEUTRAL": 0.5, "SLIGHTLY_DARK": 0.35},
        "texture": {"CLEAN_SUBTLE_GRAIN": 0.32, "DRY_AGE_TEXTURED": 0.62},
        "roughness": {"LOW": 0.25, "LOW_MEDIUM": 0.45},
        "breathiness": {"LOW": 0.25},
    }
    for name, observed in observations.items():
        target = target_values[name].get(targets.get(name, ""))
        if target is not None:
            dimensions[name] = {"observed": observed, "target": target,
                                "match": clamp(1.0 - abs(observed - target)),
                                "confidence": "LOW_ACOUSTIC_PROXY"}
    numeric = [float(value) for value in dimensions.values() if isinstance(value, float)]
    numeric.extend(float(value["match"]) for value in dimensions.values() if isinstance(value, dict))
    return sum(numeric) / len(numeric), dimensions
