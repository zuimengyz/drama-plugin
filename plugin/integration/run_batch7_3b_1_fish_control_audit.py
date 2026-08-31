"""Run the bounded Fish S2-Pro control-surface audit for Batch 7.3B.1."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import wave
from array import array
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from drama_plugin.audio.intelligibility import intelligibility_qc
from drama_plugin.config import load_config
from drama_plugin.contracts import RoleDubbingQcPolicy
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.providers.speech.fish_audio import (
    FISH_TTS_MODEL,
    FishAudioHttpClient,
    compile_fish_tts_payload,
)


WORK_ID = "work_9cc5d11969a64f93bce4a544f349c793"
SPEAKER_KEY = "speaker:geshuhan"
SPOKEN_CONTENT_ID = "spoken-7-3b-consequence"
CANONICAL_TEXT = "你可知道后果？"
BASELINE_MEDIA = {
    "A": "media_a25dd7a0b7ef47adb4998f1c93ad44d3",
    "B0": "media_e0b7568bef8d494382ee7c9e4b911156",
    "C": "media_1794a591609f4983b2dab68b05e49222",
}
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
SILENCE_THRESHOLD_DBFS = -45.0


@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    groups: tuple[str, ...]
    speed: float
    volume: float
    rendered_text: str
    render_strategy: str


EXPERIMENTS = (
    Experiment("speed-low", ("speed",), 0.6, 0.0, CANONICAL_TEXT, "CANONICAL"),
    Experiment(
        "control-baseline",
        ("speed", "volume"),
        1.0,
        0.0,
        CANONICAL_TEXT,
        "CANONICAL",
    ),
    Experiment("speed-high", ("speed",), 1.6, 0.0, CANONICAL_TEXT, "CANONICAL"),
    Experiment("volume-low", ("volume",), 1.0, -12.0, CANONICAL_TEXT, "CANONICAL"),
    Experiment("volume-high", ("volume",), 1.0, 6.0, CANONICAL_TEXT, "CANONICAL"),
    Experiment(
        "case-b-punctuation",
        ("text-rendering",),
        1.0,
        -2.0,
        "你……可知道后果？",
        "PUNCTUATION",
    ),
    Experiment(
        "case-b-s2-markers",
        ("text-rendering",),
        1.0,
        -2.0,
        "[curious]你可知道[break][emphasis]后果？",
        "S2_OFFICIAL_MARKERS",
    ),
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def same_service_origin(expected: SplitResult, actual: SplitResult) -> bool:
    same_host = actual.hostname == expected.hostname or {
        actual.hostname,
        expected.hostname,
    } <= LOOPBACK_HOSTS
    return (
        actual.scheme == expected.scheme
        and actual.port == expected.port
        and same_host
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def probe_wav(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        declared_frame_count = source.getnframes()
        raw = source.readframes(declared_frame_count)
    if channels != 1 or sample_width != 2 or sample_rate <= 0:
        raise RuntimeError("Fish audit output must be non-empty 16-bit mono PCM WAV")
    samples = array("h")
    samples.frombytes(raw)
    if not samples:
        raise RuntimeError("Fish audit output contains no PCM samples")
    maximum = max(abs(value) for value in samples)
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    threshold = round(32768 * 10 ** (SILENCE_THRESHOLD_DBFS / 20))
    active = [index for index, value in enumerate(samples) if abs(value) >= threshold]
    if not active:
        raise RuntimeError("Fish audit output has no speech above the silence threshold")
    leading_ms = round(active[0] * 1000 / sample_rate)
    trailing_ms = round((len(samples) - 1 - active[-1]) * 1000 / sample_rate)
    active_ms = round((active[-1] - active[0] + 1) * 1000 / sample_rate)
    actual_frame_count = len(samples) // channels
    duration_ms = round(actual_frame_count * 1000 / sample_rate)
    return {
        "format": "WAV_PCM_S16LE",
        "sampleRate": sample_rate,
        "channels": channels,
        "durationMs": duration_ms,
        "speechActiveDurationMs": active_ms,
        "leadingSilenceMs": leading_ms,
        "trailingSilenceMs": trailing_ms,
        "rmsDbfs": round(20 * math.log10(rms / 32768), 3) if rms else -120.0,
        "peakDbfs": round(20 * math.log10(maximum / 32768), 3)
        if maximum
        else -120.0,
        "decodePlayable": True,
    }


async def call_tool(
    session: ClientSession, name: str, arguments: dict[str, Any]
) -> Any:
    result = await session.call_tool(name, arguments)
    payload: Any = result.structured_content
    if payload is None and result.content and result.content[0].type == "text":
        payload = json.loads(result.content[0].text)
    if result.is_error:
        raise RuntimeError(f"{name} failed safely: {payload}")
    return payload


def work_voice_id(work: dict[str, Any]) -> str:
    matches = [
        item
        for item in work.get("content", {}).get("voiceProfiles", [])
        if item.get("speakerKey") == SPEAKER_KEY and item.get("voiceId")
    ]
    if len(matches) != 1:
        raise RuntimeError("Batch 7.3B.1 requires one existing stable Work Voice")
    return str(matches[0]["voiceId"])


def fish_reference_id(voice: dict[str, Any]) -> str:
    matches = [
        item
        for item in voice.get("content", {}).get("providerMappings", [])
        if item.get("provider") == "fish"
        and item.get("model") == FISH_TTS_MODEL
        and item.get("status") == "ACTIVE"
        and item.get("providerVoiceId")
    ]
    if len(matches) != 1:
        raise RuntimeError("Batch 7.3B.1 requires one active Fish S2-Pro mapping")
    return str(matches[0]["providerVoiceId"])


async def download_media(
    session: ClientSession,
    *,
    media: dict[str, Any],
    destination: Path,
    drama_service_base_url: str,
) -> dict[str, Any]:
    resolved = await call_tool(
        session, "media.resolve_media", {"media_id": media["id"]}
    )
    expected = urlsplit(drama_service_base_url)
    actual = urlsplit(str(resolved["url"]))
    if not same_service_origin(expected, actual):
        raise RuntimeError("media.resolve_media returned a non-Drama-Service URL")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(str(resolved["url"]))
        response.raise_for_status()
        content = response.content
    digest = sha256_bytes(content)
    if digest != media["contentHash"]:
        raise RuntimeError("service-mediated Media content hash mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return {
        "contentHash": digest,
        "sizeBytes": len(content),
        "urlOwner": "DRAMA_SERVICE",
    }


async def obtain_experiment_media(
    session: ClientSession,
    fish: FishAudioHttpClient,
    *,
    experiment: Experiment,
    reference_id: str,
    voice_id: str,
    baseline_content: dict[str, Any],
    review_root: Path,
    source_root: Path,
    drama_service_base_url: str,
) -> tuple[dict[str, Any], str]:
    payload = compile_fish_tts_payload(
        exact_text=CANONICAL_TEXT,
        rendered_text=(
            experiment.rendered_text
            if experiment.rendered_text != CANONICAL_TEXT
            else None
        ),
        reference_id=reference_id,
        mode="directed",
        speed=experiment.speed,
        volume=experiment.volume,
    )
    request_fingerprint = sha256_canonical(payload)
    legacy_source_ref = (
        f"batch7-3b-1:{experiment.experiment_id}:{request_fingerprint}"
    )
    legacy = await call_tool(
        session,
        "media.list_media",
        {
            "work_id": WORK_ID,
            "media_type": "AUDIO",
            "purpose": "FISH_CONTROL_AUDIT",
            "source_ref": legacy_source_ref,
        },
    )
    if len(legacy) > 1:
        raise RuntimeError("legacy Fish control audit sourceRef is not unique")
    if legacy:
        legacy_media = await call_tool(
            session, "media.get_media", {"media_id": legacy[0]["id"]}
        )
        await call_tool(
            session,
            "media.save_media",
            {
                "media_id": legacy_media["id"],
                "purpose": "FISH_CONTROL_AUDIT_DEBUG",
                "content": {
                    **legacy_media["content"],
                    "reviewStatus": "DEBUG",
                    "supersededReason": "STREAMING_WAV_HEADER_DURATION_PLACEHOLDER",
                },
            },
        )
    source_ref = (
        f"batch7-3b-1-pcm-v2:{experiment.experiment_id}:{request_fingerprint}"
    )
    existing = await call_tool(
        session,
        "media.list_media",
        {
            "work_id": WORK_ID,
            "media_type": "AUDIO",
            "purpose": "FISH_CONTROL_AUDIT",
            "source_ref": source_ref,
        },
    )
    if len(existing) > 1:
        raise RuntimeError("Fish control audit sourceRef is not unique")
    output = review_root / f"{experiment.experiment_id}.wav"
    if existing:
        media = await call_tool(
            session, "media.get_media", {"media_id": existing[0]["id"]}
        )
        await download_media(
            session,
            media=media,
            destination=output,
            drama_service_base_url=drama_service_base_url,
        )
        return media, "REUSED"

    output.parent.mkdir(parents=True, exist_ok=True)
    source_output = source_root / f"{experiment.experiment_id}.wav"
    source_output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        audio = output.read_bytes()
        source_output.write_bytes(audio)
        generation_state = "RECOVERED_WITHOUT_PROVIDER_CALL"
    else:
        audio, _ = await fish.synthesize(payload)
        source_output.write_bytes(audio)
        generation_state = "NEW"
    technical = probe_wav(source_output)
    asr_evidence: dict[str, Any] | None = None
    if "text-rendering" in experiment.groups:
        asr = await fish.transcribe(source_output)
        asr_evidence = dump_contract(
            intelligibility_qc(
                canonical_text=CANONICAL_TEXT,
                transcript=asr.text,
                proper_nouns=[],
                policy=RoleDubbingQcPolicy(),
            )
        )
        if asr_evidence["status"] != "PASS":
            raise RuntimeError("Fish rendered-text candidate failed intelligibility QC")
    rendered_fingerprint = hashlib.sha256(
        experiment.rendered_text.encode("utf-8")
    ).hexdigest()
    media = await call_tool(
        session,
        "media.import_media",
        {
            "work_id": WORK_ID,
            "media_type": "AUDIO",
            "source_uri": source_output.resolve().as_uri(),
            "purpose": "FISH_CONTROL_AUDIT",
            "source_ref": source_ref,
            "duration_ms": technical["durationMs"],
            "content": {
                "schemaVersion": "fish-control-audit-v1",
                "batch": "7.3B.1",
                "experimentId": experiment.experiment_id,
                "canonicalSpokenContentId": SPOKEN_CONTENT_ID,
                "canonicalTextHash": hashlib.sha256(
                    CANONICAL_TEXT.encode("utf-8")
                ).hexdigest(),
                "renderStrategy": experiment.render_strategy,
                "renderedText": experiment.rendered_text,
                "renderedTextFingerprint": rendered_fingerprint,
                "dpdFingerprint": baseline_content["dpdFingerprint"],
                "audioProjectionFingerprint": baseline_content[
                    "audioProjectionFingerprint"
                ],
                "providerRequestFingerprint": request_fingerprint,
                "safeProviderControls": {
                    "model": FISH_TTS_MODEL,
                    "speed": experiment.speed,
                    "volume": experiment.volume,
                    "normalize": True,
                    "normalizeLoudness": True,
                },
                "voiceId": voice_id,
                "technicalQc": technical,
                "intelligibilityQc": asr_evidence,
                "reviewStatus": "PENDING",
            },
        },
    )
    integrity = await download_media(
        session,
        media=media,
        destination=output,
        drama_service_base_url=drama_service_base_url,
    )
    if integrity["contentHash"] != sha256_bytes(audio):
        raise RuntimeError("persisted Fish audit audio differs from provider result")
    return media, generation_state


def control_conclusions(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {item["experimentId"]: item for item in items}
    low_speed = by_id["speed-low"]["technicalQc"]["speechActiveDurationMs"]
    baseline_speed = by_id["control-baseline"]["technicalQc"][
        "speechActiveDurationMs"
    ]
    high_speed = by_id["speed-high"]["technicalQc"]["speechActiveDurationMs"]
    speed_pass = low_speed > baseline_speed > high_speed and low_speed / high_speed >= 1.2
    low_volume = by_id["volume-low"]["technicalQc"]["rmsDbfs"]
    baseline_volume = by_id["control-baseline"]["technicalQc"]["rmsDbfs"]
    high_volume = by_id["volume-high"]["technicalQc"]["rmsDbfs"]
    volume_pass = (
        low_volume < baseline_volume < high_volume
        and high_volume - low_volume >= 3.0
    )
    text_items = [item for item in items if "text-rendering" in item["groups"]]
    text_pass = all(
        item["intelligibilityQc"] is not None
        and item["intelligibilityQc"]["status"] == "PASS"
        for item in text_items
    )
    return {
        "speed": {
            "status": "PASS" if speed_pass else "FAIL",
            "activeDurationOrderMs": [low_speed, baseline_speed, high_speed],
            "conclusion": (
                "prosody.speed materially changes S2-Pro speech-active duration"
                if speed_pass
                else "prosody.speed did not produce the required monotonic duration effect"
            ),
        },
        "volume": {
            "status": "PASS" if volume_pass else "FAIL",
            "rmsOrderDbfs": [low_volume, baseline_volume, high_volume],
            "conclusion": (
                "prosody.volume materially changes output RMS with normalize_loudness enabled"
                if volume_pass
                else "normalize_loudness or model behavior prevented a reliable monotonic RMS effect"
            ),
        },
        "textRendering": {
            "status": "LIMITED" if text_pass else "FAIL",
            "conclusion": (
                "official S2 rendered text preserves intelligibility; artistic improvement awaits listening"
                if text_pass
                else "rendered text failed technical or intelligibility validation"
            ),
        },
    }


async def run(*, evidence_path: Path) -> None:
    workspace = Path(__file__).resolve().parents[3]
    review_root = workspace / "artifacts/batch7-3b-1/review"
    config = load_config(os.environ.get("DRAMA_PLUGIN_CONFIG"))
    role = config.services.role_dubbing
    if role.api_key is None:
        raise RuntimeError("Fish Audio credential is missing")
    if not role.output_directory:
        raise RuntimeError("Role Dubbing output directory is missing")
    source_root = Path(role.output_directory).resolve() / "batch7-3b-1"
    mcp_url = os.environ.get("DRAMA_MCP_URL", "http://127.0.0.1:8765/mcp")
    service_url = config.services.media.base_url
    if not service_url:
        raise RuntimeError("Drama Service media base URL is missing")
    generated_count = 0
    items: list[dict[str, Any]] = []
    async with streamable_http_client(mcp_url) as streams:
        async with ClientSession(*streams[:2]) as session:
            initialized = await session.initialize()
            tools = {item.name for item in (await session.list_tools()).tools}
            required = {
                "work.get_work",
                "voice.get_voice",
                "media.get_media",
                "media.list_media",
                "media.import_media",
                "media.resolve_media",
                "media.save_media",
            }
            if not required <= tools:
                raise RuntimeError("dynamic MCP projection is incomplete")
            work = await call_tool(session, "work.get_work", {"work_id": WORK_ID})
            voice_id = work_voice_id(work)
            voice = await call_tool(session, "voice.get_voice", {"voice_id": voice_id})
            reference_id = fish_reference_id(voice)
            baseline_b = await call_tool(
                session, "media.get_media", {"media_id": BASELINE_MEDIA["B0"]}
            )
            baseline_content = baseline_b["content"]
            if (
                baseline_content.get("voiceId") != voice_id
                or baseline_content.get("spokenContentId") != SPOKEN_CONTENT_ID
            ):
                raise RuntimeError("Batch 7.3B Case B baseline identity changed")
            baseline_integrity = await download_media(
                session,
                media=baseline_b,
                destination=workspace / "artifacts/batch7-3b/review/case-b.wav",
                drama_service_base_url=service_url,
            )
            baselines: dict[str, Any] = {"B0": baseline_integrity}
            for label in ("A", "C"):
                media = await call_tool(
                    session, "media.get_media", {"media_id": BASELINE_MEDIA[label]}
                )
                baselines[label] = await download_media(
                    session,
                    media=media,
                    destination=workspace
                    / f"artifacts/batch7-3b/review/case-{label.lower()}.wav",
                    drama_service_base_url=service_url,
                )

            async with FishAudioHttpClient(
                role.api_key.get_secret_value(),
                base_url=role.base_url,
                timeout_seconds=role.timeout_seconds,
                max_transient_retries=role.max_transient_retries,
            ) as fish:
                for experiment in EXPERIMENTS:
                    media, generation_state = await obtain_experiment_media(
                        session,
                        fish,
                        experiment=experiment,
                        reference_id=reference_id,
                        voice_id=voice_id,
                        baseline_content=baseline_content,
                        review_root=review_root,
                        source_root=source_root,
                        drama_service_base_url=service_url,
                    )
                    generated_count += int(generation_state == "NEW")
                    output = review_root / f"{experiment.experiment_id}.wav"
                    content = media["content"]
                    technical = probe_wav(output)
                    if technical != content["technicalQc"]:
                        raise RuntimeError("replayed technical QC differs from persisted evidence")
                    items.append(
                        {
                            "experimentId": experiment.experiment_id,
                            "groups": list(experiment.groups),
                            "canonicalSpokenContentId": SPOKEN_CONTENT_ID,
                            "dpdFingerprint": baseline_content["dpdFingerprint"],
                            "audioProjectionFingerprint": baseline_content[
                                "audioProjectionFingerprint"
                            ],
                            "renderStrategy": experiment.render_strategy,
                            "renderedText": experiment.rendered_text,
                            "renderedTextFingerprint": content[
                                "renderedTextFingerprint"
                            ],
                            "safeProviderControls": content["safeProviderControls"],
                            "providerRequestFingerprint": content[
                                "providerRequestFingerprint"
                            ],
                            "mediaId": media["id"],
                            "contentHash": media["contentHash"],
                            "technicalQc": technical,
                            "intelligibilityQc": content.get("intelligibilityQc"),
                            "reviewFile": str(output),
                            "generationState": generation_state,
                        }
                    )

    conclusions = control_conclusions(items)
    evidence = {
        "schemaVersion": "batch7-3b-1-fish-control-audit-v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "status": (
            "PASS"
            if conclusions["speed"]["status"] == "PASS"
            and conclusions["volume"]["status"] == "PASS"
            and conclusions["textRendering"]["status"] != "FAIL"
            else "NEEDS_REVIEW"
        ),
        "provider": "Fish Audio",
        "providerModel": FISH_TTS_MODEL,
        "protocolVersion": initialized.protocol_version,
        "workId": WORK_ID,
        "speakerKey": SPEAKER_KEY,
        "voiceId": voice_id,
        "canonicalSpokenContentId": SPOKEN_CONTENT_ID,
        "canonicalTextHash": hashlib.sha256(CANONICAL_TEXT.encode("utf-8")).hexdigest(),
        "baselineMedia": BASELINE_MEDIA,
        "baselineIntegrity": baselines,
        "primaryGenerationCalls": len(items),
        "newGenerationsThisRun": generated_count,
        "items": items,
        "conclusions": conclusions,
        "gates": {
            "sameCanonicalText": True,
            "sameSpeaker": True,
            "sameVoice": True,
            "sameProviderModel": True,
            "noVoiceDesign": True,
            "noCreateModel": True,
            "serviceMediatedPersistence": True,
            "dpdFrozen": True,
            "audioPerformanceBriefFrozen": True,
            "phraseSegmentationPerformed": False,
            "artisticReviewPending": True,
        },
    }
    write_json(evidence_path, evidence)
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "generated": generated_count,
                "speed": conclusions["speed"]["status"],
                "volume": conclusions["volume"]["status"],
                "textRendering": conclusions["textRendering"]["status"],
                "B1": next(
                    item["mediaId"]
                    for item in items
                    if item["experimentId"] == "case-b-punctuation"
                ),
                "B2": next(
                    item["mediaId"]
                    for item in items
                    if item["experimentId"] == "case-b-s2-markers"
                ),
                "evidence": str(evidence_path),
            },
            ensure_ascii=False,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    asyncio.run(run(evidence_path=args.evidence.resolve()))


if __name__ == "__main__":
    main()
