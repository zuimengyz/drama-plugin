from __future__ import annotations

from collections.abc import Mapping

from drama_plugin.contracts.audio import (
    CreativeCastingDimension,
    CreativeVoiceCastingProfile,
    VoiceProfile,
)


STABLE_VOICE_FIELD_MAP = {
    "vocalAge": "vocal_age",
    "vocalWeight": "vocal_weight",
    "resonance": "resonance_depth",
    "brightness": "timbre_brightness",
    "texture": "texture",
    "articulation": "articulation_firmness",
    "baselinePace": "baseline_pace",
    "controlledPower": "controlled_power",
    "sentenceFinality": "sentence_finality",
    "language": "language",
    "register": "language_register",
}

FISH_DIMENSION_PHRASES = {
    ("vocalAge", "MATURE_ADULT"): "a mature adult vocal age",
    ("vocalAge", "LATE_MIDDLE_ADULT"): (
        "a late-middle-adult age impression expressed through texture, resonance, "
        "breath support, articulation, and phrase shape rather than a pitch shortcut"
    ),
    ("vocalWeight", "MEDIUM"): "medium vocal weight",
    ("vocalWeight", "MEDIUM_HEAVY"): "medium-heavy vocal weight",
    ("register", "MID"): "a natural middle register",
    ("register", "LOW_MIDDLE"): "a natural low-middle register without forced bass",
    ("resonance", "BALANCED"): "balanced resonance",
    ("resonance", "DEEP"): "deep but unforced resonance",
    ("brightness", "NEUTRAL"): "neutral timbre brightness",
    ("brightness", "SLIGHTLY_DARK"): "a slightly dark timbre",
    ("texture", "CLEAN_SUBTLE_GRAIN"): "a clean texture with subtle grain",
    ("texture", "DRY_AGE_TEXTURED"): "a dry, lightly age-textured voice",
    ("roughness", "LOW"): "low roughness",
    ("roughness", "LOW_MEDIUM"): "low-to-medium natural roughness",
    ("breathiness", "LOW"): "low breathiness with supported breath",
    ("articulation", "FIRM"): "firm articulation",
    ("baselinePace", "MODERATE"): "moderate baseline pace",
    ("baselinePace", "MODERATE_DELIBERATE"): "moderately deliberate baseline pace",
    ("controlledPower", "MEDIUM_CONTROLLED"): "medium controlled power",
    ("controlledPower", "HIGH_WITHOUT_LOUDNESS_REQUIREMENT"): (
        "strong controlled power without requiring loudness"
    ),
    ("sentenceFinality", "MODERATE_REQUEST_REMAINS_OPEN"): (
        "request endings that leave final authority with the listener"
    ),
    ("sentenceFinality", "OPEN_FOR_SUPERIOR_DECISION"): (
        "request endings that leave final authority with the listener"
    ),
    ("sentenceFinality", "HIGH"): "decisive high-finality sentence endings",
    ("language", "zh-CN"): "Mandarin Chinese voice",
}


def project_creative_voice_casting_profile(
    voice_profile: VoiceProfile,
    *,
    artistic_decisions: Mapping[str, CreativeCastingDimension],
    historical_fact_refs: list[str] | None = None,
    creative_decision_basis: list[str] | None = None,
) -> CreativeVoiceCastingProfile:
    """Merge supported stable profile values with separately labelled art decisions.

    The function deliberately has no speaker-name input and never reads SceneState or
    PerformanceIntent. Unknown stable acoustic fields may be filled only by explicit
    CREATIVE_VOICE_DECISION values supplied by the planning layer.
    """

    dimensions = dict(artistic_decisions)
    stable = voice_profile.creative_profile
    for target, source in STABLE_VOICE_FIELD_MAP.items():
        value = getattr(stable, source)
        if value in (None, "UNKNOWN") or target in dimensions:
            continue
        dimensions[target] = CreativeCastingDimension(
            value=str(value),
            basis_refs=[f"VoiceProfile.creativeProfile.{source}"],
        )
    return CreativeVoiceCastingProfile(
        source_profile_id=voice_profile.profile_id,
        dimensions=dimensions,
        historical_fact_refs=historical_fact_refs or [],
        creative_decision_basis=creative_decision_basis or [],
    )


def compile_fish_creative_casting_brief(
    profile: CreativeVoiceCastingProfile,
) -> dict[str, object]:
    """Compile a short Fish acoustic brief without identity or scene semantics."""

    source_values = {
        name: dimension.value for name, dimension in profile.dimensions.items()
    }
    phrases = [
        FISH_DIMENSION_PHRASES[(name, value)]
        for name, value in source_values.items()
        if (name, value) in FISH_DIMENSION_PHRASES
    ]
    if not phrases:
        raise ValueError("creative casting profile has no Fish-supported dimensions")
    return {
        "profileSource": profile.schema_version,
        "sourceValues": source_values,
        "instruction": ", ".join(dict.fromkeys(phrases))
        + ". Keep the base voice natural, clear, and controlled.",
    }
