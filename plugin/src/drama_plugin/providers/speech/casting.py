from __future__ import annotations

from dataclasses import dataclass

from drama_plugin.contracts.audio import CreativeVoiceProfile


@dataclass(frozen=True)
class VoiceCandidate:
    voice_id: str
    presentations: frozenset[str]
    semantic_vector: dict[str, float]


@dataclass(frozen=True)
class RankedVoiceCandidate:
    voice_id: str
    score: float
    compared_dimensions: tuple[str, ...]


_PROFILE_FIELDS = (
    "vocal_age",
    "vocal_weight",
    "resonance_depth",
    "timbre_brightness",
    "articulation_firmness",
    "phrase_attack",
    "baseline_pace",
    "baseline_energy",
    "breath_support",
    "command_presence",
    "gravitas",
    "controlled_power",
    "sentence_finality",
    "emotional_containment",
)
_FIELD_WEIGHTS = {field: 1.0 for field in _PROFILE_FIELDS}
_FIELD_WEIGHTS["vocal_age"] = 0.35


def _semantic_value(field: str, raw: str | None) -> float | None:
    if raw is None:
        return None
    value = raw.strip().upper().replace("-", "_").replace(" ", "_")
    if not value or value == "UNKNOWN":
        return None
    direct = {
        "VERY_LOW": 0.0,
        "LOW": 0.15,
        "LOW_TO_MEDIUM": 0.35,
        "MEDIUM_LOW": 0.35,
        "MEDIUM": 0.5,
        "MODERATE": 0.5,
        "MEDIUM_HIGH": 0.7,
        "MEDIUM_TO_HIGH": 0.7,
        "HIGH": 0.85,
        "VERY_HIGH": 1.0,
        "EXTREME": 1.0,
    }
    if value in direct:
        return direct[value]
    # Preserve an explicit ordinal while allowing an attached neutral qualifier,
    # for example HIGH_WITHOUT_LOUDNESS_REQUIREMENT.  The qualifier is evidence
    # for review; the adapter ranks only the leading provider-neutral magnitude.
    for prefix, score in (
        ("VERY_HIGH_", 1.0),
        ("MEDIUM_HIGH_", 0.7),
        ("MODERATE_", 0.5),
        ("MEDIUM_", 0.5),
        ("LOW_", 0.15),
        ("HIGH_", 0.85),
    ):
        if value.startswith(prefix):
            return score
    field_values = {
        "vocal_age": {
            "CHILD": 0.0,
            "ADOLESCENT": 0.15,
            "YOUNG_ADULT": 0.3,
            "ADULT": 0.5,
            "MATURE_ADULT": 0.65,
            "OLDER_ADULT": 0.85,
            "ELDER": 1.0,
        },
        "timbre_brightness": {"DARK": 0.15, "NEUTRAL": 0.5, "BRIGHT": 0.85},
        "resonance_depth": {"SHALLOW": 0.15, "MEDIUM": 0.5, "DEEP": 0.85},
        "baseline_pace": {"SLOW": 0.15, "MEDIUM": 0.5, "FAST": 0.85},
        "phrase_attack": {"SOFT": 0.15, "NEUTRAL": 0.5, "FIRM": 0.85},
        "articulation_firmness": {
            "SOFT": 0.15,
            "NEUTRAL": 0.5,
            "FIRM": 0.85,
        },
    }
    known = field_values.get(field, {}).get(value)
    if known is not None:
        return known

    # Backward-compatible parsing for pre-7.2S-R profiles. New Skill output uses
    # the canonical values above, so this is not an interpretation layer.
    normalized = raw.lower()
    if field == "vocal_age":
        if any(term in normalized for term in ("elder", "older", "aged", "年长", "老年")):
            return 0.9
        if any(term in normalized for term in ("mature", "middle-aged", "中年", "成熟")):
            return 0.65
        if any(term in normalized for term in ("young", "青年", "年轻")):
            return 0.3
    if field in {"resonance_depth", "timbre_brightness"}:
        if any(term in normalized for term in ("deep", "dark", "low", "深", "暗", "低")):
            return 0.15 if field == "timbre_brightness" else 0.85
        if any(term in normalized for term in ("bright", "high", "明亮", "高")):
            return 0.85 if field == "timbre_brightness" else 0.15
    return None


def profile_semantic_vector(profile: CreativeVoiceProfile) -> dict[str, float]:
    result: dict[str, float] = {}
    for field in _PROFILE_FIELDS:
        parsed = _semantic_value(field, getattr(profile, field))
        if parsed is not None:
            result[field] = parsed
    return result


def _presentation_filter(profile: CreativeVoiceProfile) -> str | None:
    presentation = (profile.gender_presentation or "").lower()
    if any(term in presentation for term in ("masculine", "male", "男")):
        return "masculine"
    if any(term in presentation for term in ("feminine", "female", "女")):
        return "feminine"
    return None


def rank_voice_candidates(
    profile: CreativeVoiceProfile,
    candidates: tuple[VoiceCandidate, ...],
    *,
    limit: int = 3,
) -> list[RankedVoiceCandidate]:
    if not 1 <= limit <= 3:
        raise ValueError("voice candidate ranking limit must be between 1 and 3")
    presentation = _presentation_filter(profile)
    compatible = [
        candidate
        for candidate in candidates
        if presentation is None or presentation in candidate.presentations
    ]
    if not compatible:
        compatible = list(candidates)
    profile_vector = profile_semantic_vector(profile)

    ranked: list[RankedVoiceCandidate] = []
    for candidate in compatible:
        common = tuple(
            sorted(set(profile_vector).intersection(candidate.semantic_vector))
        )
        if common:
            total_weight = sum(_FIELD_WEIGHTS[field] for field in common)
            distance = sum(
                abs(profile_vector[field] - candidate.semantic_vector[field])
                * _FIELD_WEIGHTS[field]
                for field in common
            ) / total_weight
            score = round(max(0.0, 100.0 * (1.0 - distance)), 3)
        else:
            score = 0.0
        ranked.append(
            RankedVoiceCandidate(
                voice_id=candidate.voice_id,
                score=score,
                compared_dimensions=common,
            )
        )
    ranked.sort(key=lambda item: (-item.score, item.voice_id))
    return ranked[:limit]
