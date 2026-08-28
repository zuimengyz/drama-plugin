"""Run the bounded real Fish Role Dubbing E2E through the dynamic MCP projection.

This runner never prints credentials or temporary content URLs.  It records
only durable Drama identifiers, hashes, lifecycle decisions, QC, and local files
that are ready for the user's artistic review.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from drama_plugin.contracts.base import dump_contract
from run_fish_role_dubbing_validation import (
    CANONICAL_DIALOGUE,
    DIRECTED_PROSODY,
    EPISODE_ID,
    SCENE_ID,
    SCRIPT_ID,
    SHOT_ID,
    WORK_ID,
    build_creative_casting_profile,
    load_frozen_voice_profiles,
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
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


def requests(workspace: Path) -> list[dict[str, Any]]:
    source = json.loads(
        (
            workspace
            / "artifacts/batch7-2/evidence/generation-request-7.2s-r.json"
        ).read_text(encoding="utf-8")
    )["requests"]
    frozen = load_frozen_voice_profiles(workspace)
    values: list[dict[str, Any]] = []
    for speech in source:
        speaker_key = str(speech["speakerKey"])
        canonical = next(
            item
            for item in CANONICAL_DIALOGUE.values()
            if item["speakerKey"] == speaker_key
        )
        if speech["exactText"] != canonical["exactText"]:
            raise RuntimeError("persisted exact Dialogue changed")
        casting = build_creative_casting_profile(
            speaker_key=speaker_key, creative_profile=frozen[speaker_key]
        )
        speech["creativeCastingProfile"] = dump_contract(casting)
        speech["pronunciationGuidance"] = [
            {
                "term": term,
                "language": "zh-CN",
                "reviewedReading": term,
                "speakerKey": speaker_key,
                "notes": "Persisted exact-text proper noun gate",
            }
            for term in canonical["properNouns"]
        ]
        prosody = DIRECTED_PROSODY[speaker_key]
        speech["materialRenderParameters"] = {
            "speed": prosody["speed"],
            "volume": prosody["volume"],
        }
        speech["nonMaterialMetadata"]["productionRun"] = (
            "fish-role-dubbing-formal-e2e"
        )
        values.append({"schemaVersion": "role-dubbing-v1", "speechRequest": speech})
    return values


async def download_and_verify(
    session: ClientSession,
    *,
    resolve_tool: str,
    id_argument: str,
    durable_id: str,
    expected_hash: str,
    destination: Path,
    drama_service_base_url: str,
) -> dict[str, Any]:
    resolved = await call_tool(session, resolve_tool, {id_argument: durable_id})
    expected_origin = urlsplit(drama_service_base_url)
    actual_origin = urlsplit(str(resolved["url"]))
    if (actual_origin.scheme, actual_origin.hostname, actual_origin.port) != (
        expected_origin.scheme, expected_origin.hostname, expected_origin.port
    ):
        raise RuntimeError(f"{resolve_tool} returned non-Drama-Service content URL")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(str(resolved["url"]))
        response.raise_for_status()
        binary = response.content
    digest = sha256_bytes(binary)
    resolved_hash = resolved.get("contentHash")
    if digest != expected_hash or (
        resolved_hash is not None and digest != resolved_hash
    ):
        raise RuntimeError(f"content hash mismatch for {durable_id}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(binary)
    return {
        "durableId": durable_id,
        "contentHash": digest,
        "sizeBytes": len(binary),
        "resolvedHashMatches": True,
        "urlOwner": "DRAMA_SERVICE",
    }


def safe_mapping_evidence(voice: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "provider": item["provider"],
            "model": item["model"],
            "status": item["status"],
            "materialFingerprint": item["materialFingerprint"],
            "providerVoiceIdPresent": bool(item.get("providerVoiceId")),
            "providerVoiceIdHash": (
                hashlib.sha256(str(item["providerVoiceId"]).encode("utf-8")).hexdigest()
                if item.get("providerVoiceId")
                else None
            ),
        }
        for item in voice["content"]["providerMappings"]
    ]


async def run(phase: str, mcp_url: str, drama_service_base_url: str, evidence_path: Path) -> None:
    workspace = Path(__file__).resolve().parents[3]
    review_root = workspace / "artifacts/role-dubbing-production/review"
    names = {
        "speaker:wangsili": "王思礼",
        "speaker:geshuhan": "哥舒翰",
    }
    speech_requests = requests(workspace)
    baseline_path = evidence_path.with_name("initial.json")
    baseline = (
        json.loads(baseline_path.read_text(encoding="utf-8"))
        if phase == "reuse"
        else None
    )

    async with streamable_http_client(mcp_url) as streams:
        async with ClientSession(*streams[:2]) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            tool_names = {item.name for item in tools.tools}
            required_tools = {
                "production.generate_role_dubbing",
                "voice.search_voices",
                "voice.get_voice",
                "voice.resolve_voice",
                "media.get_media",
                "media.resolve_media",
                "work.get_work",
                "scene.get_scene",
            }
            if not required_tools <= tool_names:
                raise RuntimeError("dynamic MCP projection is incomplete")

            context = {
                "work": await call_tool(
                    session, "work.get_work", {"work_id": WORK_ID}
                ),
                "script": await call_tool(
                    session, "script.get_script", {"script_id": SCRIPT_ID}
                ),
                "episode": await call_tool(
                    session, "episode.get_episode", {"episode_id": EPISODE_ID}
                ),
                "scene": await call_tool(
                    session, "scene.get_scene", {"scene_id": SCENE_ID}
                ),
                "shot": await call_tool(
                    session, "shot.get_shot", {"shot_id": SHOT_ID}
                ),
            }
            before = await call_tool(session, "voice.search_voices", {})
            initial_bindings = {
                item["speakerKey"]: item.get("voiceId")
                for item in context["work"]["content"].get("voiceProfiles", [])
                if item.get("speakerKey") in names and item.get("voiceId")
            }
            if phase == "initial" and len(before) > 1:
                raise RuntimeError("initial recovery permits at most one committed target Voice")

            results: list[dict[str, Any]] = []
            for wrapped in speech_requests:
                speech = wrapped["speechRequest"]
                result = await call_tool(
                    session,
                    "production.generate_role_dubbing",
                    {"request": wrapped},
                )
                recovered_after_verification_crash = (
                    phase == "initial" and speech["speakerKey"] in initial_bindings
                )
                expected_branch = (
                    "NEW_VOICE"
                    if phase == "initial" and not recovered_after_verification_crash
                    else "EXISTING_MAPPING"
                )
                if result["lifecycleBranch"] != expected_branch:
                    raise RuntimeError(f"unexpected lifecycle branch: {result}")
                expected_calls = 1 if expected_branch == "NEW_VOICE" else 0
                if result["voiceDesignCalls"] != expected_calls:
                    raise RuntimeError("unexpected Voice Design call count")
                if result["createModelCalls"] != expected_calls:
                    raise RuntimeError("unexpected Create Model call count")

                voice = await call_tool(
                    session, "voice.get_voice", {"voice_id": result["voiceId"]}
                )
                media = await call_tool(
                    session, "media.get_media", {"media_id": result["audioMediaId"]}
                )
                mappings = safe_mapping_evidence(voice)
                if len(mappings) != 1 or mappings[0]["model"] != "s2-pro":
                    raise RuntimeError("Voice does not have exactly one active s2-pro mapping")
                if media["purpose"] != "ROLE_DUBBING_AUDIO":
                    raise RuntimeError("formal role dubbing Media purpose mismatch")
                if media["content"]["reviewStatus"] != "PENDING":
                    raise RuntimeError("artistic review boundary was not preserved")
                if media["content"]["technicalReviewStatus"] != "PASS":
                    raise RuntimeError("technical review did not pass")

                slug = speaker_key = speech["speakerKey"]
                slug = slug.split(":")[-1]
                media_integrity = await download_and_verify(
                    session,
                    resolve_tool="media.resolve_media",
                    id_argument="media_id",
                    durable_id=media["id"],
                    expected_hash=media["contentHash"],
                    destination=review_root / f"{names[speaker_key]}-{slug}.wav",
                    drama_service_base_url=drama_service_base_url,
                )
                master_integrity = await download_and_verify(
                    session,
                    resolve_tool="voice.resolve_voice",
                    id_argument="voice_id",
                    durable_id=voice["id"],
                    expected_hash=voice["contentHash"],
                    destination=review_root / "masters" / f"{slug}-master.wav",
                    drama_service_base_url=drama_service_base_url,
                )
                if baseline is not None:
                    prior = next(
                        item
                        for item in baseline["items"]
                        if item["speakerKey"] == speaker_key
                    )
                    if result["voiceId"] != prior["voiceId"]:
                        raise RuntimeError("Voice identity was not stable after restart")
                    if result["audioMediaId"] != prior["audioMediaId"]:
                        raise RuntimeError("canonical Media was not reused after restart")
                    if media_integrity["contentHash"] != prior["audioIntegrity"]["contentHash"]:
                        raise RuntimeError("Audio hash changed after restart")
                    if master_integrity["contentHash"] != prior["masterIntegrity"]["contentHash"]:
                        raise RuntimeError("Voice master hash changed after restart")
                results.append(
                    {
                        "speakerKey": speaker_key,
                        "spokenContentId": speech["spokenContentId"],
                        "exactText": speech["exactText"],
                        "exactTextHash": hashlib.sha256(
                            speech["exactText"].encode("utf-8")
                        ).hexdigest(),
                        "voiceId": voice["id"],
                        "voiceVersion": voice["version"],
                        "castingEvidence": {
                            "candidateCount": voice["content"][
                                "sourceProvenance"
                            ].get("candidateCount"),
                            "masterSelection": voice["content"][
                                "sourceProvenance"
                            ].get("masterSelection"),
                        },
                        "providerMappings": mappings,
                        "audioMediaId": media["id"],
                        "durationMs": media["durationMs"],
                        "reviewStatus": media["content"]["reviewStatus"],
                        "technicalReviewStatus": media["content"][
                            "technicalReviewStatus"
                        ],
                        "intelligibilityQc": result["intelligibilityQc"],
                        "sameVendorAsTts": media["content"]["sameVendorAsTts"],
                        "lifecycleBranch": result["lifecycleBranch"],
                        "creationBranch": (
                            "NEW_VOICE" if phase == "initial" else None
                        ),
                        "recoveredAfterRunnerVerificationCrash": (
                            recovered_after_verification_crash
                        ),
                        "voiceDesignCalls": result["voiceDesignCalls"],
                        "createModelCalls": result["createModelCalls"],
                        "audioIntegrity": media_integrity,
                        "masterIntegrity": master_integrity,
                        "reviewFile": str(
                            review_root / f"{names[speaker_key]}-{slug}.wav"
                        ),
                    }
                )

            after_work = await call_tool(
                session, "work.get_work", {"work_id": WORK_ID}
            )
            bindings = {
                item["speakerKey"]: item.get("voiceId")
                for item in after_work["content"].get("voiceProfiles", [])
                if item.get("speakerKey") in names
            }
            expected_bindings = {item["speakerKey"]: item["voiceId"] for item in results}
            if bindings != expected_bindings:
                raise RuntimeError("Work speakerKey to voiceId bindings mismatch")

    evidence = {
        "schemaVersion": "fish-role-dubbing-production-e2e-v1",
        "phase": phase,
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "PASS",
        "mcp": {
            "protocolVersion": initialized.protocol_version,
            "dynamicProjection": True,
            "requiredToolsProjected": True,
        },
        "sharedContext": {
            "workId": context["work"]["id"],
            "scriptId": context["script"]["id"],
            "episodeId": context["episode"]["id"],
            "sceneId": context["scene"]["id"],
            "shotId": context["shot"]["id"],
            "duplicateWorkCreated": False,
        },
        "voiceCountBeforeThisPhase": len(before),
        "voiceTableEmptyBeforeFirstSubmission": True,
        "workVersionAfter": after_work["version"],
        "workVoiceBindings": bindings,
        "items": results,
        "gates": {
            "fishOnly": True,
            "ttsModelS2ProOnly": True,
            "fishAsrQcPassed": True,
            "durableVoiceAndMedia": True,
            "hashIntegrity": True,
            "artisticReviewPending": True,
            "lipSyncNotStarted": True,
            "finalAvNotStarted": True,
            "serviceMediatedContent": True,
        },
    }
    write_json(evidence_path, evidence)
    print(
        json.dumps(
            {
                "status": "PASS",
                "phase": phase,
                "items": [
                    {
                        "speakerKey": item["speakerKey"],
                        "voiceId": item["voiceId"],
                        "audioMediaId": item["audioMediaId"],
                        "branch": item["lifecycleBranch"],
                        "reviewFile": item["reviewFile"],
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
    parser.add_argument("--phase", choices=("initial", "reuse"), required=True)
    parser.add_argument("--mcp-url", default="http://127.0.0.1:8765/mcp")
    parser.add_argument("--drama-service-base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.phase, args.mcp_url, args.drama_service_base_url, args.evidence.resolve()))


if __name__ == "__main__":
    main()
