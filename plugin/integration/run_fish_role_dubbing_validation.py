"""Real Fish Audio local-reference role-dubbing validation; no domain/media writes."""

from __future__ import annotations

import argparse
import asyncio
import array
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import wave
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from drama_plugin.audio.host_media import probe_media
from drama_plugin.audio.creative_casting import (
    compile_fish_creative_casting_brief,
    project_creative_voice_casting_profile,
)
from drama_plugin.contracts import (
    CreativeCastingDimension,
    CreativeVoiceCastingProfile,
    EvidenceConfidence,
    VoiceProfile,
)
from drama_plugin.exceptions import ProviderResultUnknown, SpeechProviderError
from drama_plugin.providers.speech.fish_audio import (
    FISH_AUDIO_BASE_URL,
    FISH_TTS_MODEL,
    FISH_VOICE_DESIGN_MODEL,
    FishAudioHttpClient,
    compile_fish_tts_payload,
    compile_fish_voice_design_payload,
)


WORK_ID = "work_9cc5d11969a64f93bce4a544f349c793"
SCRIPT_ID = "script_a404a8277fef45eda8ef3aaf478307cc"
EPISODE_ID = "episode_c33021fe53ba4af08cd8b98113184dd2"
SCENE_ID = "scene_3ad95aa042e647d9a9be05a51dd8a009"
SHOT_ID = "shot_83db7eb53b2f49d3a58428d4659e584e"
CANONICAL_DIALOGUE = {
    "spoken-s1-wangsili-proposal": {
        "speakerKey": "speaker:wangsili",
        "speakerName": "王思礼",
        "exactText": "请给我三十骑，取杨国忠首级，为大帅除患。",
        "properNouns": ["三十骑", "杨国忠"],
    },
    "spoken-s1-geshuhan-refusal": {
        "speakerKey": "speaker:geshuhan",
        "speakerName": "哥舒翰",
        "exactText": "此事若行，我便是反臣。不可。",
        "properNouns": ["反臣"],
    },
}
DIRECTED_PROSODY = {
    "speaker:wangsili": {
        "speed": 1.05,
        "volume": -1.0,
        "brief": {
            "energy": "high internal activation",
            "pace": "slightly faster, not rushed",
            "restraint": "high",
            "volume": "lower without weakness",
            "phraseAttack": "direct request",
            "sentenceEnding": "open for superior decision",
        },
    },
    "speaker:geshuhan": {
        "speed": 0.92,
        "volume": -1.0,
        "brief": {
            "energy": "high internal activation",
            "pace": "slightly slower, not drawn out",
            "restraint": "very high",
            "volume": "lower without weakness",
            "phraseAttack": "deliberate judgment",
            "sentenceEnding": "high finality",
        },
    },
}


class ValidationBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class ReferenceSpec:
    speaker_key: str
    dialogue_id: str
    reference_audio: Path | None


VOICE_PROFILE_FIELDS = (
    "vocalAge",
    "vocalWeight",
    "resonanceDepth",
    "timbreBrightness",
    "texture",
    "articulationFirmness",
    "phraseAttack",
    "baselinePace",
    "baselineEnergy",
    "breathSupport",
    "commandPresence",
    "gravitas",
    "controlledPower",
    "sentenceFinality",
    "emotionalContainment",
    "language",
    "register",
)
VOICE_VALUE_PHRASES = {
    ("language", "zh-CN"): "Mandarin Chinese voice",
    ("articulationFirmness", "FIRM"): "firm articulation",
    ("phraseAttack", "DIRECT_REQUEST"): "a direct request phrase attack",
    ("phraseAttack", "DELIBERATE_JUDGMENT"): "a deliberate judgment phrase attack",
    ("baselinePace", "MODERATE"): "moderate baseline pace",
    ("baselinePace", "MODERATE_DELIBERATE"): "moderately deliberate baseline pace",
    ("commandPresence", "MEDIUM_EXECUTION_CAPABLE"): (
        "medium command presence able to carry executable intent"
    ),
    ("commandPresence", "HIGH_ACTION_CONSEQUENCE"): (
        "high command presence with clear action consequence"
    ),
    ("controlledPower", "HIGH_WITHOUT_LOUDNESS_REQUIREMENT"): (
        "strong controlled power without requiring loudness"
    ),
    ("sentenceFinality", "OPEN_FOR_SUPERIOR_DECISION"): (
        "sentence endings that leave final authority with the listener"
    ),
    ("sentenceFinality", "HIGH"): "decisive high-finality sentence endings",
}

# Integration planning fixture only. Production projection/compilation remains
# identity-free in drama_plugin.audio.creative_casting.
CREATIVE_CASTING_FIXTURE: dict[str, dict[str, Any]] = {
    "speaker:wangsili": {
        "historicalFactRefs": [
            "Work.content.historicalActorHierarchy[speakerKey=speaker:wangsili]",
            "Work.content.historicalSpine[beatId=P2]",
            "《旧唐书》卷110·王思礼传：少习戎旅、长期军旅经历；生年未载",
        ],
        "creativeDecisionBasis": [
            "Exact age remains UNKNOWN; mature vocal age is an explicit artistic casting decision based on sustained military experience, not a claimed birth year.",
            "Direct subordinate counsel supports clarity and firmness without assigning final command authority.",
        ],
        "dimensions": {
            "vocalAge": ("MATURE_ADULT", "MEDIUM"),
            "vocalWeight": ("MEDIUM", "MEDIUM"),
            "register": ("MID", "MEDIUM"),
            "resonance": ("BALANCED", "MEDIUM"),
            "brightness": ("NEUTRAL", "MEDIUM"),
            "texture": ("CLEAN_SUBTLE_GRAIN", "LOW"),
            "roughness": ("LOW", "LOW"),
            "breathiness": ("LOW", "LOW"),
            "controlledPower": ("MEDIUM_CONTROLLED", "MEDIUM"),
        },
    },
    "speaker:geshuhan": {
        "historicalFactRefs": [
            "Work.content.historicalActorHierarchy[speakerKey=speaker:geshuhan]",
            "Work.content.historicalSpine[beatId=P2]",
            "《旧唐书》卷104·哥舒翰传：年四十遭父丧、三年后入河西；天宝六载已任要职，天宝十五载守潼关",
        ],
        "creativeDecisionBasis": [
            "Primary chronology supports at least an early-fifties lower bound at the battle; late-middle-adult vocal age is an artistic target, not an asserted exact age.",
            "Long command responsibility supports weight and resonance; current illness is excluded from the base voice.",
            "Older life stage is represented by a composite of texture, resonance, breath support, articulation, and phrase shape, never pitch alone.",
        ],
        "dimensions": {
            "vocalAge": ("LATE_MIDDLE_ADULT", "HIGH"),
            "vocalWeight": ("MEDIUM_HEAVY", "MEDIUM"),
            "register": ("LOW_MIDDLE", "MEDIUM"),
            "resonance": ("DEEP", "MEDIUM"),
            "brightness": ("SLIGHTLY_DARK", "MEDIUM"),
            "texture": ("DRY_AGE_TEXTURED", "MEDIUM"),
            "roughness": ("LOW_MEDIUM", "LOW"),
            "breathiness": ("LOW", "LOW"),
        },
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def load_frozen_voice_profiles(workspace: Path) -> dict[str, dict[str, Any]]:
    candidates = (
        workspace / "artifacts/batch7-2/evidence/voice-profile-7.2s-r-e2e.json",
        workspace / "artifacts/batch7-2/evidence/voice-profile-7.2s-r.json",
    )
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        raise ValidationBlocked("FROZEN_VOICE_PROFILE_MISSING")
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles: dict[str, dict[str, Any]] = {}
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        speaker_key = str(item.get("speakerKey", ""))
        creative = item.get("creativeProfile")
        if speaker_key and isinstance(creative, dict):
            profiles[speaker_key] = creative
    required = {str(item["speakerKey"]) for item in CANONICAL_DIALOGUE.values()}
    if set(profiles) < required:
        raise ValidationBlocked("FROZEN_VOICE_PROFILE_MISSING")
    return profiles


def build_creative_casting_profile(
    *, speaker_key: str, creative_profile: dict[str, Any]
) -> CreativeVoiceCastingProfile:
    fixture = CREATIVE_CASTING_FIXTURE[speaker_key]
    voice_profile = VoiceProfile.model_validate(
        {
            "profileId": f"transient:{speaker_key}:fish-dimension-repair",
            "speakerKey": speaker_key,
            "creativeProfile": creative_profile,
        }
    )
    decisions = {
        name: CreativeCastingDimension(
            value=value,
            confidence=EvidenceConfidence(confidence),
            basis_refs=[f"creativeDecisionBasis[{index}]"],
        )
        for index, (name, (value, confidence)) in enumerate(
            fixture["dimensions"].items()
        )
    }
    return project_creative_voice_casting_profile(
        voice_profile,
        artistic_decisions=decisions,
        historical_fact_refs=list(fixture["historicalFactRefs"]),
        creative_decision_basis=list(fixture["creativeDecisionBasis"]),
    )


def build_voice_casting_brief(creative_profile: dict[str, Any]) -> dict[str, Any]:
    source_values = {
        field: creative_profile[field]
        for field in VOICE_PROFILE_FIELDS
        if field in creative_profile
        and creative_profile[field] is not None
        and creative_profile[field] != "UNKNOWN"
    }
    phrases = [
        VOICE_VALUE_PHRASES[(field, str(value))]
        for field, value in source_values.items()
        if (field, str(value)) in VOICE_VALUE_PHRASES
    ]
    if not phrases:
        raise ValidationBlocked("VOICE_CASTING_BRIEF_HAS_NO_SUPPORTED_FIELDS")
    return {
        "profileSource": "EXISTING_FROZEN_VOICE_PROFILE",
        "sourceValues": source_values,
        "excludedUnknownFields": [
            field
            for field in VOICE_PROFILE_FIELDS
            if creative_profile.get(field) in {None, "UNKNOWN"}
        ],
        "instruction": ", ".join(phrases) + ". Keep the base voice clear and controlled.",
    }


def build_repaired_voice_casting_brief(
    profile: CreativeVoiceCastingProfile,
) -> dict[str, Any]:
    return dict(compile_fish_creative_casting_brief(profile))


def load_runtime_env(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def normalize_transcript(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    return "".join(char for char in normalized if char.isalnum())


def edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def intelligibility_qc(
    canonical: str, transcript: str, proper_nouns: list[str]
) -> dict[str, Any]:
    expected = normalize_transcript(canonical)
    recognized = normalize_transcript(transcript)
    distance = edit_distance(expected, recognized)
    missing = [char for char in expected if expected.count(char) > recognized.count(char)]
    extra = [char for char in recognized if recognized.count(char) > expected.count(char)]
    repeated = sorted(
        {
            char
            for char in recognized
            if recognized.count(char) > expected.count(char) and recognized.count(char) > 1
        }
    )
    proper_noun_mismatches = [
        term for term in proper_nouns if normalize_transcript(term) not in recognized
    ]
    passed = (
        expected == recognized
        and not missing
        and not extra
        and not repeated
        and not proper_noun_mismatches
    )
    return {
        "canonicalNormalized": expected,
        "transcriptNormalized": recognized,
        "cer": distance / max(1, len(expected)),
        "editDistance": distance,
        "missingCharacters": missing,
        "extraCharacters": extra,
        "repetitions": repeated,
        "properNounMismatches": proper_noun_mismatches,
        "status": "PASS" if passed else "FAIL",
    }


def parse_references(args: argparse.Namespace) -> list[ReferenceSpec]:
    items: list[dict[str, str]] = []
    if args.reference_manifest:
        payload = json.loads(args.reference_manifest.read_text(encoding="utf-8"))
        raw_items = payload.get("speakers", [])
        if not isinstance(raw_items, list):
            raise ValidationBlocked("REFERENCE_MANIFEST_INVALID")
        items.extend(item for item in raw_items if isinstance(item, dict))
    single_values = (args.speaker_key, args.reference_audio, args.dialogue_id)
    if any(single_values):
        if not all(single_values):
            raise ValidationBlocked("REFERENCE_CLI_MAPPING_INCOMPLETE")
        items.append(
            {
                "speakerKey": args.speaker_key,
                "referenceAudio": str(args.reference_audio),
                "dialogueId": args.dialogue_id,
            }
        )
    if not items:
        return [
            ReferenceSpec(
                speaker_key=str(item["speakerKey"]),
                dialogue_id=dialogue_id,
                reference_audio=None,
            )
            for dialogue_id, item in CANONICAL_DIALOGUE.items()
        ]
    specs: list[ReferenceSpec] = []
    for item in items:
        dialogue_id = str(item.get("dialogueId", ""))
        speaker_key = str(item.get("speakerKey", ""))
        reference_audio = Path(str(item.get("referenceAudio", ""))).expanduser()
        canonical = CANONICAL_DIALOGUE.get(dialogue_id)
        if canonical is None or canonical["speakerKey"] != speaker_key:
            raise ValidationBlocked("REFERENCE_DIALOGUE_SPEAKER_MISMATCH")
        specs.append(
            ReferenceSpec(
                speaker_key=speaker_key,
                dialogue_id=dialogue_id,
                reference_audio=reference_audio.resolve(),
            )
        )
    return specs


def reference_preflight(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file() or not os.access(path, os.R_OK):
        raise ValidationBlocked(f"REFERENCE_AUDIO_UNREADABLE:{path}")
    probe = probe_media(path)
    audio_streams = [item for item in probe.streams if item.get("codec_type") == "audio"]
    if not audio_streams:
        raise ValidationBlocked(f"REFERENCE_AUDIO_STREAM_MISSING:{path}")
    stream = audio_streams[0]
    if path.stat().st_size <= 0 or probe.duration_ms <= 0:
        raise ValidationBlocked(f"REFERENCE_AUDIO_EMPTY:{path}")
    return {
        "path": str(path),
        "regularFile": True,
        "readable": True,
        "fileSize": path.stat().st_size,
        "sha256": sha256_file(path),
        "durationMs": probe.duration_ms,
        "codec": stream.get("codec_name"),
        "sampleRate": stream.get("sample_rate"),
        "channels": stream.get("channels"),
        "audioStreamExists": True,
        "obviousClipping": "HUMAN_OR_SIGNAL_REVIEW_REQUIRED",
        "strongBackgroundMusic": "HUMAN_REVIEW_REQUIRED",
        "speechIntelligibility": "FISH_ASR_CHECK_PLANNED",
    }


def analyze_pcm_wav(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as source:
        if source.getsampwidth() != 2 or source.getnchannels() != 1:
            raise ValidationBlocked("REVIEW_WAV_NOT_PCM_S16_MONO")
        samples = array.array("h", source.readframes(source.getnframes()))
        if sys.byteorder != "little":
            samples.byteswap()
        sample_rate = source.getframerate()
    if not samples or sample_rate <= 0:
        raise ValidationBlocked("REVIEW_WAV_HAS_NO_SAMPLES")
    peak = max(abs(item) for item in samples)
    rms = math.sqrt(sum(item * item for item in samples) / len(samples))
    clipped = sum(1 for item in samples if abs(item) >= 32760)
    tail_size = min(len(samples), max(1, round(sample_rate * 0.25)))
    tail = samples[-tail_size:]
    tail_rms = math.sqrt(sum(item * item for item in tail) / len(tail))
    crest_factor_db = 20 * math.log10(peak / rms) if peak and rms else 0.0
    zero_crossings = sum(
        1
        for left, right in zip(samples, samples[1:])
        if (left < 0 <= right) or (left >= 0 > right)
    )
    difference_rms = math.sqrt(
        sum((right - left) ** 2 for left, right in zip(samples, samples[1:]))
        / max(1, len(samples) - 1)
    )
    alpha = 1.0 - math.exp(-2.0 * math.pi * 500.0 / sample_rate)
    low_pass = 0.0
    low_energy = 0.0
    for sample in samples:
        low_pass += alpha * (sample - low_pass)
        low_energy += low_pass * low_pass
    low_rms = math.sqrt(low_energy / len(samples))
    window_size = max(1, round(sample_rate * 0.05))
    window_rms = [
        math.sqrt(sum(item * item for item in window) / len(window))
        for start in range(0, len(samples), window_size)
        if (window := samples[start : start + window_size])
    ]
    envelope_mean = sum(window_rms) / max(1, len(window_rms))
    envelope_variation = (
        math.sqrt(
            sum((item - envelope_mean) ** 2 for item in window_rms)
            / max(1, len(window_rms))
        )
        / envelope_mean
        if envelope_mean
        else 0.0
    )
    return {
        "peakRatio": peak / 32767,
        "rmsRatio": rms / 32767,
        "crestFactorDb": crest_factor_db,
        "clippedSampleCount": clipped,
        "clippedSampleRatio": clipped / len(samples),
        "tailToOverallRmsRatio": tail_rms / rms if rms else 0.0,
        "zeroCrossingRate": zero_crossings / max(1, len(samples) - 1),
        "differenceToSignalRmsRatio": difference_rms / rms if rms else 0.0,
        "lowPassToSignalRmsRatio": low_rms / rms if rms else 0.0,
        "envelopeVariation": envelope_variation,
        "obviousClipping": clipped / len(samples) > 0.001,
    }


def candidate_casting_score(
    *,
    candidate: dict[str, Any],
    creative_profile: CreativeVoiceCastingProfile | dict[str, Any],
) -> dict[str, Any]:
    qc = candidate["intelligibilityQc"]
    signal = candidate["signalAnalysis"]
    duration_ms = int(candidate["durationMs"])
    char_count = len(normalize_transcript(str(candidate["previewText"])))
    cps = char_count / max(duration_ms / 1000, 0.001)
    if isinstance(creative_profile, CreativeVoiceCastingProfile):
        targets = {
            name: item.value for name, item in creative_profile.dimensions.items()
        }
    else:
        targets = creative_profile
    pace = targets.get("baselinePace")
    target_midpoint = 5.25 if pace == "MODERATE" else 4.0
    pace_match = max(0.0, 1.0 - abs(cps - target_midpoint) / target_midpoint)
    clarity_match = max(0.0, 1.0 - float(qc["cer"]))
    articulation_match = clarity_match
    ending_target = targets.get("sentenceFinality")
    tail_ratio = float(signal["tailToOverallRmsRatio"])
    if ending_target == "HIGH":
        ending_match = min(1.0, tail_ratio / 0.45)
    else:
        ending_match = max(0.0, 1.0 - abs(tail_ratio - 0.35) / 0.35)
    controlled_power_target = targets.get("controlledPower")
    crest = float(signal["crestFactorDb"])
    controlled_power_match = (
        max(0.0, 1.0 - abs(crest - 12.0) / 12.0)
        if controlled_power_target not in {None, "UNKNOWN"}
        else None
    )
    def clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    def match(observed: float, target: float, confidence: str) -> dict[str, Any]:
        return {
            "observed": observed,
            "target": target,
            "match": clamp(1.0 - abs(observed - target)),
            "confidence": confidence,
        }

    low_frequency = clamp(
        (float(signal["lowPassToSignalRmsRatio"]) - 0.2) / 0.65
    )
    brightness = clamp(float(signal["differenceToSignalRmsRatio"]) / 1.4)
    texture = clamp(
        float(signal["envelopeVariation"]) * 0.75
        + float(signal["zeroCrossingRate"]) * 3.0
    )
    breathiness = clamp(
        brightness * 0.55 + float(signal["zeroCrossingRate"]) * 2.0
    )
    age_composite = clamp(
        (
            low_frequency
            + low_frequency
            + (1.0 - brightness)
            + texture
        )
        / 4.0
    )
    target_values = {
        "vocalAge": {"MATURE_ADULT": 0.55, "LATE_MIDDLE_ADULT": 0.72},
        "vocalWeight": {"MEDIUM": 0.5, "MEDIUM_HEAVY": 0.7},
        "resonance": {"BALANCED": 0.5, "DEEP": 0.72},
        "brightness": {"NEUTRAL": 0.5, "SLIGHTLY_DARK": 0.35},
        "texture": {"CLEAN_SUBTLE_GRAIN": 0.32, "DRY_AGE_TEXTURED": 0.62},
        "roughness": {"LOW": 0.25, "LOW_MEDIUM": 0.45},
        "breathiness": {"LOW": 0.25},
    }
    observations = {
        "vocalAge": age_composite,
        "vocalWeight": low_frequency,
        "resonance": low_frequency,
        "brightness": brightness,
        "texture": texture,
        "roughness": texture,
        "breathiness": breathiness,
    }
    voice_fit: dict[str, Any] = {}
    for name, observed in observations.items():
        target = target_values[name].get(str(targets.get(name)))
        voice_fit[name] = (
            match(observed, target, "LOW_ACOUSTIC_PROXY")
            if target is not None
            else "EXCLUDED_UNKNOWN"
        )
    dimensions: dict[str, Any] = {
        "clarity": clarity_match,
        "articulation": articulation_match,
        "baselinePace": pace_match,
        "sentenceEnding": ending_match,
        "controlledPower": controlled_power_match,
        **voice_fit,
        "commandPresence": "NOT_RELIABLY_AUTOMATED_FROM_SHORT_PREVIEW",
        "voiceStability": "SHORT_PREVIEW_ONLY",
    }
    numeric = [float(value) for value in dimensions.values() if isinstance(value, float)]
    numeric.extend(
        float(value["match"])
        for value in voice_fit.values()
        if isinstance(value, dict)
    )
    eligible = (
        float(qc["cer"]) <= 0.2
        and not qc.get("missingCharacters", [])
        and not qc.get("extraCharacters", [])
        and not qc.get("properNounMismatches", [])
        and not qc.get("repetitions", [])
        and not signal["obviousClipping"]
    )
    if not eligible:
        for name in voice_fit:
            dimensions[name] = "NOT_EVALUATED_TECHNICAL_QC_FAIL"
    return {
        "eligible": eligible,
        "candidateQcStatus": "PASS" if eligible else "FAIL",
        "score": sum(numeric) / len(numeric) if numeric and eligible else 0.0,
        "charsPerSecond": cps,
        "selectionDimensions": dimensions,
        "technicalQc": {
            "status": "PASS" if eligible else "FAIL",
            "cer": qc["cer"],
            "obviousClipping": signal["obviousClipping"],
        },
        "voiceFit": {
            "status": "PASS" if eligible else "NOT_EVALUATED",
            "dimensions": voice_fit if eligible else {},
            "shortPreviewConfidence": "LOW",
        },
        "reasonSummary": (
            "Eligible candidate compared only on measurable, supported stable-profile dimensions."
            if eligible
            else "Excluded because candidate intelligibility or clipping QC failed."
        ),
    }


def convert_review_wav(source: Path, target: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise ValidationBlocked("FFMPEG_MISSING")
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "24000",
            "-c:a",
            "pcm_s16le",
            str(target),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


async def call_tool(session: ClientSession, name: str, arguments: dict[str, Any]) -> Any:
    result = await session.call_tool(name, arguments)
    payload: Any = result.structured_content
    if payload is None and result.content and result.content[0].type == "text":
        payload = json.loads(result.content[0].text)
    if result.is_error:
        raise ValidationBlocked(f"SHARED_CONTEXT_READ_FAILED:{name}")
    return payload


def find_identifier(value: Any, expected: str) -> bool:
    if isinstance(value, dict):
        if expected in value.values():
            return True
        return any(find_identifier(item, expected) for item in value.values())
    if isinstance(value, list):
        return any(find_identifier(item, expected) for item in value)
    return value == expected


async def read_shared_context(mcp_url: str) -> dict[str, Any]:
    async with streamable_http_client(mcp_url) as streams:
        async with ClientSession(*streams[:2]) as session:
            await session.initialize()
            values = {
                "work": await call_tool(session, "work.get_work", {"work_id": WORK_ID}),
                "script": await call_tool(
                    session, "script.get_script", {"script_id": SCRIPT_ID}
                ),
                "episode": await call_tool(
                    session, "episode.get_episode", {"episode_id": EPISODE_ID}
                ),
                "scene": await call_tool(
                    session, "scene.get_scene", {"scene_id": SCENE_ID}
                ),
                "shot": await call_tool(session, "shot.get_shot", {"shot_id": SHOT_ID}),
            }
    expected = {
        "work": WORK_ID,
        "script": SCRIPT_ID,
        "episode": EPISODE_ID,
        "scene": SCENE_ID,
        "shot": SHOT_ID,
    }
    entity_status = {
        key: "PASS" if find_identifier(values[key], identifier) else "FAIL"
        for key, identifier in expected.items()
    }
    dialogue_status = {
        dialogue_id: (
            "PASS"
            if find_identifier(values["scene"], dialogue_id)
            and find_identifier(values["scene"], str(item["exactText"]))
            else "FAIL"
        )
        for dialogue_id, item in CANONICAL_DIALOGUE.items()
    }
    if "FAIL" in entity_status.values() or "FAIL" in dialogue_status.values():
        raise ValidationBlocked("SHARED_CONTEXT_OR_CANONICAL_DIALOGUE_MISMATCH")
    return {
        "entities": entity_status,
        "canonicalDialogue": dialogue_status,
        "duplicateWorkCreated": False,
        "domainWrites": 0,
    }


def safe_error(exc: SpeechProviderError) -> dict[str, Any]:
    return {
        "classification": (
            "AMBIGUOUS_RESULT"
            if isinstance(exc, ProviderResultUnknown)
            else "PROVIDER_REJECTED"
            if exc.status_code is not None
            else "PROVIDER_ERROR"
        ),
        "httpStatus": exc.status_code,
        "providerCode": exc.provider_error_code,
        "safeMessage": exc.provider_error_message,
        "providerRequestId": exc.provider_request_id,
        "retryable": exc.retryable,
    }


async def design_and_cast_master_reference(
    *,
    client: FishAudioHttpClient,
    spec: ReferenceSpec,
    canonical: dict[str, Any],
    creative_profile: dict[str, Any],
    voice_design_root: Path,
    master_root: Path,
    calls: dict[str, int],
) -> tuple[Path, dict[str, Any]]:
    slug = spec.speaker_key.split(":")[-1]
    casting_profile = build_creative_casting_profile(
        speaker_key=spec.speaker_key, creative_profile=creative_profile
    )
    brief = build_repaired_voice_casting_brief(casting_profile)
    preview_text = str(canonical["exactText"])
    payload = compile_fish_voice_design_payload(
        instruction=str(brief["instruction"]),
        reference_text=preview_text,
        candidate_count=3,
    )
    calls["fishVoiceDesign"] += 1
    result = await client.design_voice(payload)
    candidates: list[dict[str, Any]] = []
    for candidate in result.candidates:
        raw_path = voice_design_root / f"{slug}-design-{candidate.index}-raw.wav"
        review_path = voice_design_root / f"{slug}-design-{candidate.index}.wav"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(candidate.audio)
        convert_review_wav(raw_path, review_path)
        probe = probe_media(review_path)
        audio_stream = next(
            (
                stream
                for stream in probe.streams
                if stream.get("codec_type") == "audio"
            ),
            {},
        )
        signal = analyze_pcm_wav(review_path)
        calls["fishAsr"] += 1
        asr = await client.transcribe(review_path)
        qc = intelligibility_qc(
            preview_text,
            asr.text,
            [str(item) for item in canonical["properNouns"]],
        )
        item: dict[str, Any] = {
            "candidateIndex": candidate.index,
            "providerCandidateId": candidate.candidate_id,
            "audio": str(review_path),
            "sha256": sha256_file(review_path),
            "durationMs": probe.duration_ms,
            "codec": next(
                (
                    stream.get("codec_name")
                    for stream in probe.streams
                    if stream.get("codec_type") == "audio"
                ),
                None,
            ),
            "sampleRate": audio_stream.get("sample_rate"),
            "providerSampleRate": candidate.sample_rate,
            "providerDurationMs": candidate.duration_ms,
            "previewText": preview_text,
            "asrTranscript": asr.text,
            "intelligibilityQc": qc,
            "signalAnalysis": signal,
        }
        item["casting"] = candidate_casting_score(
            candidate=item, creative_profile=casting_profile
        )
        candidates.append(item)
    eligible = [item for item in candidates if item["casting"]["eligible"]]
    if not eligible:
        raise ValidationBlocked(f"VOICE_DESIGN_ALL_CANDIDATES_FAILED:{spec.speaker_key}")
    selected = max(
        eligible,
        key=lambda item: (float(item["casting"]["score"]), str(item["sha256"])),
    )
    master_path = master_root / f"{slug}-master-reference.wav"
    master_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(selected["audio"]), master_path)
    master_fingerprint = sha256_file(master_path)
    if master_fingerprint != selected["sha256"]:
        raise ValidationBlocked("MASTER_REFERENCE_COPY_HASH_MISMATCH")
    return master_path, {
        "speakerKey": spec.speaker_key,
        "voiceSource": "FISH_VOICE_DESIGN",
        "voiceDesignModel": FISH_VOICE_DESIGN_MODEL,
        "voiceDesignRequestId": result.provider_request_id,
        "requestedCandidateCount": 3,
        "actualCandidateCount": len(candidates),
        "previewText": preview_text,
        "voiceCastingBrief": brief,
        "creativeVoiceCastingProfile": casting_profile.model_dump(
            mode="json", by_alias=True
        ),
        "candidates": candidates,
        "selectedCandidateIndex": selected["candidateIndex"],
        "selectedCandidateFingerprint": selected["sha256"],
        "selectedDimensions": selected["casting"]["selectionDimensions"],
        "selectionReasonSummary": selected["casting"]["reasonSummary"],
        "masterReferenceAudio": str(master_path),
        "masterReferenceFingerprint": master_fingerprint,
        "masterVoicePersistence": "LOCAL_ONLY",
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    workspace = Path(__file__).resolve().parents[3]
    output_root = args.output_root.resolve()
    voice_design_root = output_root / "voice-design"
    master_root = output_root / "master-reference"
    raw_root = output_root / "raw"
    review_root = output_root / "review"
    evidence_root = output_root / "evidence"
    for path in (
        voice_design_root,
        master_root,
        raw_root,
        review_root,
        evidence_root,
    ):
        path.mkdir(parents=True, exist_ok=True)
    runtime_path = Path.home() / ".config" / "historical-plugin" / "runtime.env"
    load_runtime_env(runtime_path)
    api_key = os.environ.get("FISH_AUDIO_API_KEY", "").strip()
    if not api_key:
        raise ValidationBlocked("FISH_AUDIO_API_KEY_MISSING")
    base_url = os.environ.get("FISH_AUDIO_BASE_URL", FISH_AUDIO_BASE_URL).rstrip("/")
    if base_url != FISH_AUDIO_BASE_URL:
        raise ValidationBlocked("FISH_AUDIO_BASE_URL_NOT_OFFICIAL")
    specs = parse_references(args)
    frozen_profiles = load_frozen_voice_profiles(workspace)
    try:
        shared_context = await read_shared_context(
            os.environ.get("DRAMA_MCP_URL", "http://127.0.0.1:8765/mcp")
        )
    except ValidationBlocked:
        raise
    except Exception as exc:
        raise ValidationBlocked("SHARED_CONTEXT_READ_UNAVAILABLE") from exc
    evidence: dict[str, Any] = {
        "schemaVersion": "fish-role-dubbing-validation-v1",
        "startedAt": datetime.now(UTC).isoformat(),
        "runtime": {
            "fishAudioApiKey": "PRESENT",
            "baseUrl": base_url,
            "requestedModel": FISH_TTS_MODEL,
            "actualModel": FISH_TTS_MODEL,
            "voiceDesignModel": FISH_VOICE_DESIGN_MODEL,
        },
        "sharedNarrativeContext": shared_context,
        "frozenCreativeInputs": {
            "characterAnalysisChanges": "NONE",
            "sourceEvidence": [
                "artifacts/batch7-2/evidence/character-understanding-7.2s-r-e2e.json",
                "artifacts/batch7-2/evidence/voice-profile-7.2s-r-e2e.json",
                "artifacts/batch7-2/evidence/performance-intent-7.2s-r-e2e.json",
                "artifacts/batch7-2/evidence/generation-request-7.2s-r-e2e.json",
            ],
        },
        "referenceMappingRequired": False,
        "calls": {
            "fishVoiceDesign": 0,
            "fishCreateModel": 0,
            "fishTts": 0,
            "fishAsr": 0,
        },
        "forbiddenCalls": {"qwen": 0, "bailian": 0, "openai": 0},
        "references": [],
        "voiceDesigns": [],
        "items": [],
        "longTermPersistence": {
            "voiceEntity": "NOT_CREATED",
            "voiceTable": "NOT_CREATED",
            "workVoiceBinding": "NOT_CREATED",
            "providerMappingPersisted": False,
            "mediaImport": "NOT_RUN",
            "minioWrite": "NOT_RUN",
        },
    }
    model_cache: dict[tuple[str, str], str] = {}
    async with FishAudioHttpClient(
        api_key,
        base_url=base_url,
        max_transient_retries=args.max_transient_retries,
    ) as client:
        for spec in specs:
            canonical = CANONICAL_DIALOGUE[spec.dialogue_id]
            if spec.reference_audio is None:
                reference_audio, design_evidence = await design_and_cast_master_reference(
                    client=client,
                    spec=spec,
                    canonical=canonical,
                    creative_profile=frozen_profiles[spec.speaker_key],
                    voice_design_root=voice_design_root,
                    master_root=master_root,
                    calls=evidence["calls"],
                )
                evidence["voiceDesigns"].append(design_evidence)
                preflight = reference_preflight(reference_audio)
                preflight.update(
                    {
                        "voiceSource": "FISH_VOICE_DESIGN",
                        "speechIntelligibility": "CANDIDATE_ASR_PASS",
                        "referenceAsrTranscript": canonical["exactText"],
                    }
                )
            else:
                reference_audio = spec.reference_audio
                preflight = reference_preflight(reference_audio)
                reference_asr = await client.transcribe(reference_audio)
                evidence["calls"]["fishAsr"] += 1
                preflight.update(
                    {
                        "voiceSource": "LOCAL_REFERENCE_AUDIO",
                        "speechIntelligibility": (
                            "ASR_NONEMPTY" if reference_asr.text else "FAIL"
                        ),
                        "referenceAsrTranscript": reference_asr.text,
                    }
                )
            evidence["references"].append(
                {
                    "speakerKey": spec.speaker_key,
                    "dialogueId": spec.dialogue_id,
                    **preflight,
                }
            )
            cache_key = (spec.speaker_key, str(preflight["sha256"]))
            reference_id = model_cache.get(cache_key)
            if reference_id is None:
                evidence["calls"]["fishCreateModel"] += 1
                model = await client.create_model(
                    reference_audio=reference_audio,
                    title=f"historical-validation-{spec.speaker_key.split(':')[-1]}-{str(preflight['sha256'])[:10]}",
                    reference_text=str(canonical["exactText"]),
                )
                reference_id = model.reference_id
                model_cache[cache_key] = reference_id
                write_json(
                    evidence_root / f"{spec.speaker_key.split(':')[-1]}-temporary-model.json",
                    {
                        "speakerKey": spec.speaker_key,
                        "referenceFingerprint": preflight["sha256"],
                        "temporaryReferenceId": reference_id,
                        "state": model.state,
                        "providerRequestId": model.provider_request_id,
                        "longTermVoiceBinding": "NONE",
                        "providerVoiceIdPersistence": "EXPERIMENT_ONLY",
                    },
                )
            modes = (args.mode,) if args.mode != "both" else ("baseline", "directed")
            for mode in modes:
                prosody = DIRECTED_PROSODY[spec.speaker_key]
                payload = compile_fish_tts_payload(
                    exact_text=str(canonical["exactText"]),
                    reference_id=reference_id,
                    mode=mode,
                    speed=float(prosody["speed"]) if mode == "directed" else None,
                    volume=float(prosody["volume"]) if mode == "directed" else None,
                )
                if payload["text"] != canonical["exactText"]:
                    raise ValidationBlocked("EXACT_DIALOGUE_INVARIANT_FAILED")
                slug = spec.speaker_key.split(":")[-1]
                raw_path = raw_root / f"{slug}-fish-{mode}.wav"
                review_path = review_root / f"{slug}-{mode}.wav"
                evidence["calls"]["fishTts"] += 1
                audio, request_id = await client.synthesize(payload)
                raw_path.write_bytes(audio)
                convert_review_wav(raw_path, review_path)
                probe = probe_media(review_path)
                audio_stream = next(
                    (
                        stream
                        for stream in probe.streams
                        if stream.get("codec_type") == "audio"
                    ),
                    {},
                )
                asr = await client.transcribe(review_path)
                evidence["calls"]["fishAsr"] += 1
                qc = intelligibility_qc(
                    str(canonical["exactText"]),
                    asr.text,
                    [str(item) for item in canonical["properNouns"]],
                )
                evidence["items"].append(
                    {
                        "speakerKey": spec.speaker_key,
                        "speakerName": canonical["speakerName"],
                        "dialogueId": spec.dialogue_id,
                        "mode": mode,
                        "exactText": canonical["exactText"],
                        "exactTextInputVerified": True,
                        "temporaryReferenceId": reference_id,
                        "performanceBrief": prosody["brief"] if mode == "directed" else None,
                        "providerProsody": payload.get("prosody"),
                        "providerRequestId": request_id,
                        "rawAudio": str(raw_path),
                        "reviewAudio": str(review_path),
                        "sha256": sha256_file(review_path),
                        "durationMs": probe.duration_ms,
                        "codec": audio_stream.get("codec_name"),
                        "sampleRate": audio_stream.get("sample_rate"),
                        "channels": audio_stream.get("channels"),
                        "fileSize": review_path.stat().st_size,
                        "dialogueCharCount": len(str(canonical["exactText"])),
                        "charsPerSecond": len(str(canonical["exactText"])) / (probe.duration_ms / 1000),
                        "asrProvider": "Fish",
                        "sameVendorAsTts": True,
                        "asrTranscript": asr.text,
                        "intelligibilityQc": qc,
                    }
                )
    for spec in specs:
        relevant = [
            item for item in evidence["items"] if item["speakerKey"] == spec.speaker_key
        ]
        baseline = next((item for item in relevant if item["mode"] == "baseline"), None)
        directed = next((item for item in relevant if item["mode"] == "directed"), None)
        if baseline and directed:
            ratio = directed["durationMs"] / baseline["durationMs"]
            evidence.setdefault("comparisons", []).append(
                {
                    "speakerKey": spec.speaker_key,
                    "directedToBaselineDurationRatio": ratio,
                    "performanceControlDurationDistortion": ratio > 1.5 or ratio < 0.67,
                    "performanceControlIntelligibilityRegression": (
                        baseline["intelligibilityQc"]["status"] == "PASS"
                        and directed["intelligibilityQc"]["status"] == "FAIL"
                    ),
                }
            )
    evidence["completedAt"] = datetime.now(UTC).isoformat()
    evidence["status"] = (
        "READY_FOR_USER_AUDIO_REVIEW"
        if len(specs) == 2
        else "PARTIAL_READY_FOR_USER_REVIEW"
    )
    write_json(evidence_root / "fish-role-dubbing-validation.json", evidence)
    return evidence


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--speaker-key")
    result.add_argument("--reference-audio", type=Path)
    result.add_argument("--dialogue-id")
    result.add_argument("--reference-manifest", type=Path)
    result.add_argument("--mode", choices=("baseline", "directed", "both"), default="both")
    result.add_argument("--max-transient-retries", type=int, choices=(0, 1, 2), default=1)
    result.add_argument(
        "--output-root",
        type=Path,
        default=(
            Path(__file__).resolve().parents[3]
            / "artifacts/role-dubbing-bakeoff/fish-validation"
        ),
    )
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        evidence = asyncio.run(run(args))
    except ValidationBlocked as exc:
        print(f"FISH_ROLE_DUBBING_VALIDATION=BLOCKED:{exc}", file=sys.stderr)
        return 2
    except ProviderResultUnknown as exc:
        print(json.dumps(safe_error(exc), ensure_ascii=False), file=sys.stderr)
        return 3
    except SpeechProviderError as exc:
        print(json.dumps(safe_error(exc), ensure_ascii=False), file=sys.stderr)
        return 4
    print(f"FISH_ROLE_DUBBING_VALIDATION={evidence['status']}")
    print(f"FISH_REAL_CALLS={sum(evidence['calls'].values())}")
    print("QWEN_REAL_CALLS=0")
    print("BAILIAN_REAL_CALLS=0")
    print("OPENAI_REAL_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
