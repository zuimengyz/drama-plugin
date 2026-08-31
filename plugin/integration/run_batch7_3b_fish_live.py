"""Run the bounded three-case DPD Audio Projection comparison through Fish Audio."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit

import httpx
import yaml
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from drama_plugin.audio import compile_projected_speech_request
from drama_plugin.contracts import (
    BeatDPD,
    CreativeVoiceProfile,
    LineDPD,
    RoleDubbingRequest,
    SceneDPD,
    TargetTimingPolicy,
    VoiceProfile,
)
from drama_plugin.contracts.base import dump_contract
from drama_plugin.dpd import compose_dpd
from run_fish_role_dubbing_validation import load_frozen_voice_profiles


DEFAULT_WORK_ID = "work_9cc5d11969a64f93bce4a544f349c793"
DEFAULT_EPISODE_ID = "episode_c33021fe53ba4af08cd8b98113184dd2"
DEFAULT_SPEAKER_KEY = "speaker:geshuhan"
SCENE_TITLE = "Batch 7.3B DPD Audio Projection 对照场景"
SPOKEN_ID = "spoken-7-3b-consequence"
EXACT_TEXT = "你可知道后果？"
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


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
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


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


async def ensure_scene(
    session: ClientSession,
    *,
    episode_id: str,
    speaker_key: str,
) -> dict[str, Any]:
    candidates = await call_tool(
        session,
        "scene.search_scenes",
        {"query": SCENE_TITLE, "episode_id": episode_id},
    )
    exact = [item for item in candidates if item.get("title") == SCENE_TITLE]
    if len(exact) > 1:
        raise RuntimeError("multiple Batch 7.3B comparison Scenes exist")
    if exact:
        scene = await call_tool(
            session, "scene.get_scene", {"scene_id": exact[0]["id"]}
        )
    else:
        scene = await call_tool(
            session,
            "scene.create_scene",
            {
                "episode_id": episode_id,
                "order": 730,
                "title": SCENE_TITLE,
                "location": "对照验证空间",
                "content": {
                    "purpose": "Hold exact text and speaker constant for a three-context DPD audio comparison.",
                    "narrativeInputState": "The listener has not acknowledged the consequence.",
                    "requiredTransition": "The question forces the consequence into the interaction.",
                    "narrativeOutputState": "The listener must respond to the stated risk.",
                    "spokenContent": [
                        {
                            "id": SPOKEN_ID,
                            "kind": "DIALOGUE",
                            "speakerKey": speaker_key,
                            "text": EXACT_TEXT,
                            "intent": "Make the listener confront the consequence.",
                            "mustKeep": True,
                            "performanceIntent": "Compatibility-only; DPD Audio Projection is authoritative.",
                            "provenance": {"relation": "FUNCTIONAL"},
                            "estimatedDurationMs": 1500,
                        }
                    ],
                },
            },
        )
    items = scene.get("content", {}).get("spokenContent", [])
    matches = [item for item in items if item.get("id") == SPOKEN_ID]
    if len(matches) != 1:
        raise RuntimeError("comparison Scene canonical SpokenContent is missing")
    item = matches[0]
    if item.get("speakerKey") != speaker_key or item.get("text") != EXACT_TEXT:
        raise RuntimeError("comparison Scene canonical SpokenContent changed")
    return scene


def work_voice_id(work: dict[str, Any], speaker_key: str) -> str:
    matches = [
        item
        for item in work.get("content", {}).get("voiceProfiles", [])
        if item.get("speakerKey") == speaker_key and item.get("voiceId")
    ]
    if len(matches) != 1:
        raise RuntimeError("stable Work Voice binding is required for the projected path")
    return str(matches[0]["voiceId"])


def build_requests(
    *,
    workspace: Path,
    scene_id: str,
    work_id: str,
    speaker_key: str,
    voice_id: str,
) -> list[tuple[str, RoleDubbingRequest]]:
    fixture = yaml.safe_load(
        (
            workspace
            / "drama-plugin/plugin/tests/fixtures/dpd-core-v1.yaml"
        ).read_text(encoding="utf-8")
    )
    creative = load_frozen_voice_profiles(workspace)[speaker_key]
    profile = VoiceProfile(
        profile_id=f"profile:{speaker_key}:batch7-3b",
        speaker_key=speaker_key,
        creative_profile=CreativeVoiceProfile.model_validate(creative),
    )
    spoken_content = {"id": SPOKEN_ID, "speakerKey": speaker_key, "text": EXACT_TEXT}
    values: list[tuple[str, RoleDubbingRequest]] = []
    for label, raw_case in zip(("A", "B", "C"), fixture["cases"], strict=True):
        case = deepcopy(raw_case)
        scene_payload = case["scene"]
        beat_payload = case["beat"]
        line_payload = case["line"]
        scene_payload["sceneId"] = scene_id
        beat_payload["sceneId"] = scene_id
        beat_payload["actor"] = speaker_key
        line_payload.update(
            {
                "sceneId": scene_id,
                "beatId": beat_payload["beatId"],
                "spokenContentId": SPOKEN_ID,
                "speaker": speaker_key,
            }
        )
        snapshot = compose_dpd(
            SceneDPD.model_validate(scene_payload),
            BeatDPD.model_validate(beat_payload),
            LineDPD.model_validate(line_payload),
        )
        speech = compile_projected_speech_request(
            work_id=work_id,
            dpd_snapshot=snapshot,
            spoken_content=spoken_content,
            voice_profile=profile,
            voice_identity_ref=voice_id,
            timing_policy=TargetTimingPolicy(policy="NATURAL"),
            non_material_metadata={"batch": "7.3B", "case": label},
        )
        values.append((label, RoleDubbingRequest(speech_request=speech)))
    return values


async def download_and_verify(
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
        audio = response.content
    digest = sha256_bytes(audio)
    if digest != media["contentHash"]:
        raise RuntimeError("downloaded Audio content hash mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(audio)
    return {
        "contentHash": digest,
        "sizeBytes": len(audio),
        "urlOwner": "DRAMA_SERVICE",
        "reviewFile": str(destination),
    }


async def preflight_voice_storage(
    session: ClientSession,
    *,
    voice_id: str,
    drama_service_base_url: str,
) -> dict[str, Any]:
    """Prove service-mediated Voice storage access before any paid Fish call."""
    voice = await call_tool(session, "voice.get_voice", {"voice_id": voice_id})
    resolved = await call_tool(
        session, "voice.resolve_voice", {"voice_id": voice_id}
    )
    expected = urlsplit(drama_service_base_url)
    actual = urlsplit(str(resolved["url"]))
    if not same_service_origin(expected, actual):
        actual_origin = f"{actual.scheme}://{actual.hostname}:{actual.port}"
        expected_origin = f"{expected.scheme}://{expected.hostname}:{expected.port}"
        raise RuntimeError(
            "voice.resolve_voice returned an unexpected URL owner: "
            f"expected={expected_origin} actual={actual_origin}"
        )
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(str(resolved["url"]))
        response.raise_for_status()
        master = response.content
    digest = sha256_bytes(master)
    if digest != voice["contentHash"]:
        raise RuntimeError("Voice Master content hash mismatch")
    return {
        "status": "PASS",
        "contentHash": digest,
        "sizeBytes": len(master),
        "urlOwner": "DRAMA_SERVICE",
    }


async def run(
    *,
    mcp_url: str,
    drama_service_base_url: str,
    work_id: str,
    episode_id: str,
    speaker_key: str,
    evidence_path: Path,
) -> None:
    workspace = Path(__file__).resolve().parents[3]
    review_root = workspace / "artifacts/batch7-3b/review"
    results: list[dict[str, Any]] = []
    async with streamable_http_client(mcp_url) as streams:
        async with ClientSession(*streams[:2]) as session:
            initialized = await session.initialize()
            tools = {item.name for item in (await session.list_tools()).tools}
            required = {
                "work.get_work",
                "voice.get_voice",
                "voice.resolve_voice",
                "scene.search_scenes",
                "scene.get_scene",
                "scene.create_scene",
                "production.generate_role_dubbing",
                "media.get_media",
                "media.resolve_media",
            }
            if not required <= tools:
                raise RuntimeError("dynamic MCP projection is incomplete")
            work = await call_tool(session, "work.get_work", {"work_id": work_id})
            voice_id = work_voice_id(work, speaker_key)
            voice_storage_preflight = await preflight_voice_storage(
                session,
                voice_id=voice_id,
                drama_service_base_url=drama_service_base_url,
            )
            scene = await ensure_scene(
                session, episode_id=episode_id, speaker_key=speaker_key
            )
            requests = build_requests(
                workspace=workspace,
                scene_id=scene["id"],
                work_id=work_id,
                speaker_key=speaker_key,
                voice_id=voice_id,
            )
            common_text_hashes = {
                item.speech_request.audio_performance_brief.text_fingerprint
                for _, item in requests
                if item.speech_request.audio_performance_brief is not None
            }
            common_voice_hashes = {
                item.speech_request.audio_performance_brief.voice_profile_fingerprint
                for _, item in requests
                if item.speech_request.audio_performance_brief is not None
            }
            if len(common_text_hashes) != 1 or len(common_voice_hashes) != 1:
                raise RuntimeError("comparison controls are not constant")

            for label, request in requests:
                speech = request.speech_request
                brief = speech.audio_performance_brief
                if brief is None:
                    raise RuntimeError("projected request omitted AudioPerformanceBrief")
                result = await call_tool(
                    session,
                    "production.generate_role_dubbing",
                    {"request": dump_contract(request)},
                )
                if result["voiceId"] != voice_id:
                    raise RuntimeError("Voice identity changed across comparison cases")
                if result["voiceDesignCalls"] or result["createModelCalls"]:
                    raise RuntimeError("projected path unexpectedly changed Voice/Casting")
                media = await call_tool(
                    session, "media.get_media", {"media_id": result["audioMediaId"]}
                )
                content = media["content"]
                if content.get("performanceAuthority") != "DPD_AUDIO_PROJECTION":
                    raise RuntimeError("new performance authority was not preserved")
                if content.get("audioProjectionFingerprint") != brief.fingerprint:
                    raise RuntimeError("Audio Projection lineage mismatch")
                physical = await download_and_verify(
                    session,
                    media=media,
                    destination=review_root / f"case-{label.lower()}.wav",
                    drama_service_base_url=drama_service_base_url,
                )
                capability = content["fishCapabilityMapping"]
                results.append(
                    {
                        "case": label,
                        "dpdFingerprint": brief.dpd_fingerprint,
                        "audioProjectionFingerprint": brief.fingerprint,
                        "providerRequestFingerprint": content["providerRequestFingerprint"],
                        "audioBrief": {
                            "pace": brief.pace,
                            "rhythm": brief.rhythm,
                            "intensity": brief.intensity,
                            "pauseStrategy": brief.pause_strategy,
                            "articulation": brief.articulation,
                            "sentenceEnding": brief.sentence_ending,
                            "control": brief.control,
                            "paceTendency": brief.pace_tendency.value,
                            "volumeTendency": brief.volume_tendency.value,
                        },
                        "fishCapabilityMapping": {
                            "schemaVersion": capability["schemaVersion"],
                            "speed": capability["speed"],
                            "volume": capability["volume"],
                            "capabilities": capability["capabilities"],
                        },
                        "voiceId": voice_id,
                        "audioMediaId": media["id"],
                        "durationMs": media["durationMs"],
                        "technicalReviewStatus": content["technicalReviewStatus"],
                        "artisticReviewStatus": content["reviewStatus"],
                        "intelligibilityQc": result["intelligibilityQc"],
                        "physical": physical,
                    }
                )

    evidence = {
        "schemaVersion": "batch7-3b-fish-live-v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "PASS",
        "provider": "Fish Audio",
        "providerModel": "s2-pro",
        "protocolVersion": initialized.protocol_version,
        "workId": work_id,
        "episodeId": episode_id,
        "sceneId": scene["id"],
        "speakerKey": speaker_key,
        "spokenContentId": SPOKEN_ID,
        "exactTextHash": next(iter(common_text_hashes)),
        "voiceProfileFingerprint": next(iter(common_voice_hashes)),
        "voiceId": voice_id,
        "voiceStoragePreflight": voice_storage_preflight,
        "items": results,
        "gates": {
            "sameText": True,
            "sameSpeaker": True,
            "sameVoice": True,
            "sameProvider": True,
            "dpdOnlyPrimaryVariable": True,
            "legacyAuthorityAbsent": True,
            "serviceMediatedContent": True,
            "technicalQcPassed": True,
            "artisticReviewPending": True,
            "visualNotStarted": True,
        },
    }
    write_json(evidence_path, evidence)
    print(
        json.dumps(
            {
                "status": "PASS",
                "items": [
                    {
                        "case": item["case"],
                        "audioMediaId": item["audioMediaId"],
                        "reviewFile": item["physical"]["reviewFile"],
                    }
                    for item in results
                ],
                "evidence": str(evidence_path),
            },
            ensure_ascii=False,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mcp-url", default="http://127.0.0.1:8765/mcp")
    parser.add_argument("--drama-service-base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--work-id", default=DEFAULT_WORK_ID)
    parser.add_argument("--episode-id", default=DEFAULT_EPISODE_ID)
    parser.add_argument("--speaker-key", default=DEFAULT_SPEAKER_KEY)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(
        run(
            mcp_url=args.mcp_url,
            drama_service_base_url=args.drama_service_base_url,
            work_id=args.work_id,
            episode_id=args.episode_id,
            speaker_key=args.speaker_key,
            evidence_path=args.evidence.resolve(),
        )
    )


if __name__ == "__main__":
    main()
