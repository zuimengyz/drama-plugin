"""Credential-gated Batch 7.2R real two-speaker TTS through the formal MCP chain."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from drama_plugin.audio import audio_input_fingerprint
from drama_plugin.audio.host_media import probe_media
from run_batch7_2r_preflight import build_request, write_json


FIXTURES = (
    {
        "key": "speakerA",
        "spoken_content_id": "validation-spoken-a",
        "speaker_key": "speaker:validation-a",
        "text": "军报已经送到，请将军决断。",
        "voice_id": "Cherry",
        "timbre": "clear and steady",
    },
    {
        "key": "speakerB",
        "spoken_content_id": "validation-spoken-b",
        "speaker_key": "speaker:validation-b",
        "text": "军令未下，各部不得擅动。",
        "voice_id": "Ethan",
        "timbre": "grounded and warm",
    },
)


class E2EFailure(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_artifact(path: Path, workspace: Path) -> str:
    return str(path.resolve().relative_to(workspace.resolve()))


def require_runtime() -> tuple[str, str, int]:
    if os.environ.get("REAL_TTS_E2E", "").strip().lower() not in {
        "1",
        "true",
        "yes",
    }:
        raise E2EFailure("REAL_TTS_E2E_GATE_DISABLED")
    if os.environ.get("DRAMA_PLUGIN_PROVIDER_SPEECH_MODE", "").strip() != (
        "bailian_qwen"
    ):
        raise E2EFailure("ACTIVE_PROVIDER_NOT_BAILIAN_QWEN")
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        raise E2EFailure("DASHSCOPE_API_KEY_MISSING")
    model = os.environ.get("BATCH72R_QWEN_MODEL", "qwen3-tts-instruct-flash")
    if model not in {"qwen3-tts-instruct-flash", "qwen3-tts-flash"}:
        raise E2EFailure("QWEN_MODEL_NOT_EXPLICITLY_ALLOWED")
    retries = int(
        os.environ.get("DRAMA_PLUGIN_SERVICE_SPEECH_MAX_TRANSIENT_RETRIES", "2")
    )
    if retries not in {0, 1, 2}:
        raise E2EFailure("TRANSIENT_RETRY_BOUND_INVALID")
    return os.environ.get("DRAMA_MCP_URL", "http://127.0.0.1:8765/mcp"), model, retries


async def call_tool(
    session: ClientSession,
    name: str,
    arguments: dict[str, Any],
) -> Any:
    result = await session.call_tool(name, arguments)
    if result.is_error:
        payload = result.structured_content or {}
        code = payload.get("error", {}).get("code", "UNKNOWN")
        raise E2EFailure(f"MCP_TOOL_FAILED:{name}:{code}")
    if result.structured_content is not None:
        return result.structured_content
    if not result.content or result.content[0].type != "text":
        raise E2EFailure(f"MCP_TOOL_RETURNED_NO_JSON:{name}")
    return json.loads(result.content[0].text)


async def ensure_fixture_hierarchy(
    session: ClientSession,
    model: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    templates = [
        build_request(model=model, **{key: value for key, value in fixture.items() if key != "key"})
        for fixture in FIXTURES
    ]
    works = await call_tool(
        session,
        "work.search_works",
        {"query": "Batch 7.2R Qwen two-speaker validation"},
    )
    work = next(
        (
            item
            for item in works
            if item.get("content", {}).get("batch72RValidationFixture") is True
        ),
        None,
    )
    if work is None:
        work = await call_tool(
            session,
            "work.create_work",
            {
                "title": "Batch 7.2R Qwen two-speaker validation",
                "description": "Non-production validation fixture for user audio review.",
                "content": {
                    "batch72RValidationFixture": True,
                    "classification": "TTS_VALIDATION_FIXTURE",
                    "voiceProfiles": [
                        request.voice_profile.model_dump(mode="json", by_alias=True)
                        for request in templates
                    ],
                },
            },
        )

    scripts = await call_tool(
        session, "script.list_scripts", {"work_id": work["id"]}
    )
    script = next(
        (
            item
            for item in scripts
            if item.get("content", {}).get("batch72RValidationFixture") is True
        ),
        None,
    )
    if script is None:
        script = await call_tool(
            session,
            "script.create_script",
            {
                "work_id": work["id"],
                "title": "Batch 7.2R validation script",
                "content": {"batch72RValidationFixture": True},
            },
        )

    episodes = await call_tool(
        session, "episode.list_episodes", {"script_id": script["id"]}
    )
    episode = next(
        (
            item
            for item in episodes
            if item.get("content", {}).get("batch72RValidationFixture") is True
        ),
        None,
    )
    if episode is None:
        episode = await call_tool(
            session,
            "episode.create_episode",
            {
                "script_id": script["id"],
                "episode_no": 1,
                "title": "Batch 7.2R validation episode",
                "content": {"batch72RValidationFixture": True},
            },
        )

    scenes = await call_tool(
        session, "scene.list_scenes", {"episode_id": episode["id"]}
    )
    scene = next(
        (
            item
            for item in scenes
            if item.get("content", {}).get("batch72RValidationFixture") is True
        ),
        None,
    )
    if scene is None:
        scene = await call_tool(
            session,
            "scene.create_scene",
            {
                "episode_id": episode["id"],
                "order": 1,
                "title": "Batch 7.2R two-speaker validation scene",
                "location": "Validation fixture",
                "content": {
                    "batch72RValidationFixture": True,
                    "spokenContent": [
                        {
                            "spokenContentId": fixture["spoken_content_id"],
                            "speakerKey": fixture["speaker_key"],
                            "text": fixture["text"],
                            "performanceIntent": {
                                "delivery": "neutral",
                                "pace": "measured",
                            },
                        }
                        for fixture in FIXTURES
                    ],
                },
            },
        )
    return work, scene


async def find_existing_attempt(
    session: ClientSession,
    work_id: str,
    fingerprint: str,
) -> dict[str, Any] | None:
    media = await call_tool(
        session,
        "media.list_media",
        {"media_type": "AUDIO", "work_id": work_id, "purpose": "SPEECH_CLIP"},
    )
    matches = [
        item
        for item in media
        if item.get("content", {}).get("audioInputFingerprint") == fingerprint
        and item.get("content", {}).get("reviewStatus") in {"PENDING", "PASS"}
    ]
    if len(matches) > 1:
        raise E2EFailure("MULTIPLE_EXISTING_AUDIO_ATTEMPTS_NEED_REVIEW")
    return matches[0] if matches else None


async def validate_media(
    session: ClientSession,
    media: dict[str, Any],
    review_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    content = media.get("content", {})
    expected_hash = content.get("audioSha256") or media.get("contentHash")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise E2EFailure("AUDIO_HASH_MISSING")
    resolved = await call_tool(
        session, "media.resolve_media", {"media_id": media["id"]}
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(resolved["url"])
            response.raise_for_status()
            downloaded = response.content
    except httpx.HTTPError as exc:
        raise E2EFailure("MEDIA_RESOLVE_DOWNLOAD_FAILED") from exc
    downloaded_hash = sha256_bytes(downloaded)

    local_path = next(
        (
            path
            for path in review_root.iterdir()
            if path.is_file() and sha256_file(path) == expected_hash
        ),
        None,
    )
    if local_path is None:
        extension = {
            "audio/wav": ".wav",
            "audio/mpeg": ".mp3",
            "audio/aac": ".aac",
            "audio/flac": ".flac",
            "audio/ogg": ".ogg",
        }.get(str(media.get("mimeType")), ".audio")
        local_path = review_root / f"recovered-{media['id']}{extension}"
        local_path.write_bytes(downloaded)

    local_hash = sha256_file(local_path)
    stored_hash = media.get("contentHash")
    if not (local_hash == downloaded_hash == expected_hash == stored_hash):
        raise E2EFailure("AUDIO_HASH_EQUALITY_FAILED")
    if local_path.stat().st_size <= 0 or int(media.get("fileSize") or 0) <= 0:
        raise E2EFailure("AUDIO_FILE_EMPTY")

    probe = probe_media(local_path)
    audio_stream = next(
        (item for item in probe.streams if item.get("codec_type") == "audio"), None
    )
    if audio_stream is None or probe.duration_ms <= 0:
        raise E2EFailure("AUDIO_PHYSICAL_VALIDATION_FAILED")
    if int(media.get("durationMs") or 0) != probe.duration_ms:
        raise E2EFailure("AUDIO_DURATION_MISMATCH")
    if not str(media.get("mimeType", "")).startswith("audio/"):
        raise E2EFailure("AUDIO_MIME_INVALID")

    return {
        "mediaId": media["id"],
        "artifact": relative_artifact(local_path, workspace),
        "fileSize": local_path.stat().st_size,
        "mimeType": media["mimeType"],
        "durationMs": probe.duration_ms,
        "codec": audio_stream.get("codec_name"),
        "sampleRate": audio_stream.get("sample_rate"),
        "channels": audio_stream.get("channels"),
        "sha256": local_hash,
        "hashEquality": True,
        "provider": content.get("provider"),
        "model": content.get("model"),
        "providerVoiceId": content.get("providerVoiceId"),
        "providerJobId": content.get("providerJobId"),
        "providerAudioId": content.get("providerAudioId"),
        "providerCallCount": content.get("providerCallCount"),
        "providerRetryCount": content.get("providerRetryCount"),
        "providerDownloadCallCount": content.get("providerDownloadCallCount"),
        "reviewStatus": content.get("reviewStatus"),
    }


async def run(args: argparse.Namespace) -> int:
    mcp_url, model, retry_bound = require_runtime()
    workspace = Path(__file__).resolve().parents[3]
    output_root = args.output_root.resolve()
    review_root = output_root / "review"
    evidence_path = output_root / "evidence" / "real-qwen-tts-e2e-7.2r.json"
    review_root.mkdir(parents=True, exist_ok=True)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, Any] = {
        "batch": "7.2R",
        "classification": "CURRENT_HOST_REAL_PROVIDER_E2E",
        "status": "IN_PROGRESS",
        "provider": "bailian_qwen",
        "model": model,
        "primaryGenerationLimit": 2,
        "primaryGenerationAttempts": 0,
        "safeTransientRetryLimitPerItem": retry_bound,
        "providerCalls": 0,
        "safeTransientRetries": 0,
        "ambiguousAttempts": 0,
        "openAiRealCalls": 0,
        "secretsRecorded": False,
        "providerResultUrlsRecorded": False,
        "items": [],
    }
    write_json(evidence_path, evidence)

    try:
        async with streamable_http_client(mcp_url) as streams:
            async with ClientSession(*streams[:2]) as session:
                initialized = await session.initialize()
                listed = await session.list_tools()
                names = {tool.name for tool in listed.tools}
                if initialized.server_info.name != "drama-mcp-service":
                    raise E2EFailure("MCP_SERVER_IDENTITY_INVALID")
                if "production.generate_audio" not in names:
                    raise E2EFailure("MCP_AUDIO_TOOL_MISSING")
                work, scene = await ensure_fixture_hierarchy(session, model)
                evidence["workId"] = work["id"]
                evidence["sceneId"] = scene["id"]
                evidence["mcpToolCount"] = len(names)

                for fixture in FIXTURES:
                    request = build_request(
                        model=model,
                        work_id=work["id"],
                        scene_id=scene["id"],
                        **{key: value for key, value in fixture.items() if key != "key"},
                    )
                    fingerprint = audio_input_fingerprint(request)
                    media = await find_existing_attempt(
                        session, work["id"], fingerprint
                    )
                    reused = media is not None
                    if media is None:
                        if evidence["primaryGenerationAttempts"] >= 2:
                            raise E2EFailure("PRIMARY_GENERATION_LIMIT_REACHED")
                        evidence["primaryGenerationAttempts"] += 1
                        write_json(evidence_path, evidence)
                        media = await call_tool(
                            session,
                            "production.generate_audio",
                            {
                                "request": request.model_dump(
                                    mode="json", by_alias=True
                                )
                            },
                        )
                    item = await validate_media(
                        session, media, review_root, workspace
                    )
                    item.update(
                        {
                            "fixture": fixture["key"],
                            "spokenContentId": fixture["spoken_content_id"],
                            "speakerKey": fixture["speaker_key"],
                            "audioInputFingerprint": fingerprint,
                            "existingAttemptReused": reused,
                            "exactTextInputVerified": media.get("content", {}).get(
                                "exactTextInputVerified"
                            ),
                        }
                    )
                    evidence["items"].append(item)
                    evidence["providerCalls"] += int(
                        item.get("providerCallCount") or 0
                    )
                    evidence["safeTransientRetries"] += int(
                        item.get("providerRetryCount") or 0
                    )
                    write_json(evidence_path, evidence)

        evidence["status"] = "READY_FOR_USER_AUDIO_REVIEW"
        evidence["technicalValidation"] = "PASS"
        evidence["userAudioReview"] = "PENDING"
        evidence["batch73"] = "NOT_STARTED"
        write_json(evidence_path, evidence)

        summary_path = output_root / "validation-summary-7.2r.json"
        summary = (
            json.loads(summary_path.read_text(encoding="utf-8"))
            if summary_path.is_file()
            else {}
        )
        summary.update(
            {
                "batch": "7.2R",
                "batch72R": "READY_FOR_USER_AUDIO_REVIEW",
                "activeProvider": "bailian_qwen",
                "dashscopeCredentialAvailable": True,
                "realTtsE2eEnabled": True,
                "qwenRealTtsCallCount": evidence["providerCalls"],
                "qwenRealTtsRetryCount": evidence["safeTransientRetries"],
                "openAiRealTtsCallCount": 0,
                "bailianQwenProvider": "PASS_REAL",
                "exactTextInput": "PASS_REAL",
                "audioInputFingerprintA": evidence["items"][0][
                    "audioInputFingerprint"
                ],
                "audioInputFingerprintB": evidence["items"][1][
                    "audioInputFingerprint"
                ],
                "realSpeechA": "PASS",
                "realSpeechB": "PASS",
                "actualDurationA": evidence["items"][0]["durationMs"],
                "actualDurationB": evidence["items"][1]["durationMs"],
                "realAudioMediaRoundtrip": "PASS",
                "hashEquality": "PASS",
                "audioTechnicalValidation": "PASS",
                "audioTimeline": "NOT_STARTED_USER_AUDIO_REVIEW_BOUNDARY",
                "avPreview": "NOT_STARTED_USER_AUDIO_REVIEW_BOUNDARY",
                "sourceVideoImmutable": "NOT_APPLICABLE_AUDIO_REVIEW_BOUNDARY",
                "userAudioReview": "PENDING",
                "batch73": "NOT_STARTED",
            }
        )
        write_json(summary_path, summary)
        print(
            json.dumps(
                {
                    "status": evidence["status"],
                    "provider": evidence["provider"],
                    "primaryGenerationAttempts": evidence[
                        "primaryGenerationAttempts"
                    ],
                    "providerCalls": evidence["providerCalls"],
                    "safeTransientRetries": evidence["safeTransientRetries"],
                    "ambiguousAttempts": evidence["ambiguousAttempts"],
                    "items": [
                        {
                            "artifact": item["artifact"],
                            "mediaId": item["mediaId"],
                            "durationMs": item["durationMs"],
                            "codec": item["codec"],
                        }
                        for item in evidence["items"]
                    ],
                    "userAudioReview": "PENDING",
                    "batch73": "NOT_STARTED",
                },
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:
        if evidence["primaryGenerationAttempts"] > len(evidence["items"]):
            evidence["ambiguousAttempts"] = 1
            evidence["status"] = "AMBIGUOUS_NEEDS_REVIEW"
        else:
            evidence["status"] = "FAILED_BEFORE_NEW_PROVIDER_SUBMISSION"
        evidence["failureCode"] = (
            str(exc) if isinstance(exc, E2EFailure) else type(exc).__name__
        )
        evidence["userAudioReview"] = "NOT_READY"
        evidence["batch73"] = "NOT_STARTED"
        write_json(evidence_path, evidence)
        print(
            json.dumps(
                {
                    "status": evidence["status"],
                    "failureCode": evidence["failureCode"],
                    "primaryGenerationAttempts": evidence[
                        "primaryGenerationAttempts"
                    ],
                    "ambiguousAttempts": evidence["ambiguousAttempts"],
                    "batch73": "NOT_STARTED",
                },
                ensure_ascii=False,
            )
        )
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "artifacts" / "batch7-2",
    )
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
