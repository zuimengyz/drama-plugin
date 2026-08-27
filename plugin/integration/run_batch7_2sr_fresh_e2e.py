"""Fresh, Skill-planned Batch 7.2S-R candidate Audio E2E through formal MCP."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from drama_plugin.audio import (
    audio_input_fingerprint,
    pronunciation_fingerprint,
    provider_mapping_fingerprint,
    source_ref_for_review,
    text_hash,
    voice_profile_fingerprint,
)
from drama_plugin.audio.host_media import probe_media
from drama_plugin.contracts.audio import AudioReviewStatus, SpeechGenerationRequest
from drama_plugin.providers.speech.bailian_qwen import (
    bailian_qwen_voice_compatibility,
    compile_bailian_qwen_speech_payload,
    rank_bailian_qwen_voice_candidates,
)
from run_batch7_2r_preflight import write_json
from run_batch7_2r_real_e2e import sha256_file, validate_media


WORK_ID = "work_9cc5d11969a64f93bce4a544f349c793"
SCENE_ID = "scene_3ad95aa042e647d9a9be05a51dd8a009"
PLANNED_ORDER = (
    ("spoken-s1-wangsili-proposal", "wangsili", 1),
    ("spoken-s1-wangsili-proposal", "wangsili", 2),
    ("spoken-s1-geshuhan-refusal", "geshuhan", 1),
    ("spoken-s1-geshuhan-refusal", "geshuhan", 2),
)
STOP_CODES = {
    "AMBIGUOUS_RESULT",
    "TRANSIENT_RETRY_EXHAUSTED",
    "PROVIDER_REJECTED",
}


class E2EFailure(RuntimeError):
    pass


class ToolFailure(E2EFailure):
    def __init__(
        self, tool: str, code: str, diagnostics: dict[str, Any] | None = None
    ) -> None:
        super().__init__(f"{tool}:{code}")
        self.tool = tool
        self.code = code
        self.diagnostics = diagnostics or {}


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require_runtime(workspace: Path) -> tuple[str, int, Path]:
    if os.environ.get("REAL_TTS_E2E", "").strip().lower() not in {
        "1",
        "true",
        "yes",
    }:
        raise E2EFailure("REAL_TTS_E2E_GATE_DISABLED")
    if os.environ.get("DRAMA_PLUGIN_PROVIDER_SPEECH_MODE", "").strip().lower() != (
        "bailian_qwen"
    ):
        raise E2EFailure("ACTIVE_PROVIDER_NOT_BAILIAN_QWEN")
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        raise E2EFailure("DASHSCOPE_API_KEY_MISSING")
    retries = int(
        os.environ.get("DRAMA_PLUGIN_SERVICE_SPEECH_MAX_TRANSIENT_RETRIES", "2")
    )
    if retries not in {0, 1, 2}:
        raise E2EFailure("TRANSIENT_RETRY_BOUND_INVALID")
    output = Path(
        os.environ.get("DRAMA_PLUGIN_SERVICE_SPEECH_OUTPUT_DIRECTORY", "")
    ).expanduser()
    if not output.is_absolute():
        raise E2EFailure("SPEECH_OUTPUT_DIRECTORY_NOT_ABSOLUTE")
    expected = (workspace / "artifacts" / "batch7-2" / "review").resolve()
    if output.resolve() != expected:
        raise E2EFailure("SPEECH_OUTPUT_DIRECTORY_NOT_BATCH_REVIEW_ROOT")
    mcp_url = os.environ.get("DRAMA_MCP_URL", "http://127.0.0.1:8765/mcp")
    return mcp_url, retries, expected


async def call_tool(
    session: ClientSession, name: str, arguments: dict[str, Any]
) -> Any:
    result = await session.call_tool(name, arguments)
    payload: Any = result.structured_content
    if payload is None and result.content and result.content[0].type == "text":
        payload = json.loads(result.content[0].text)
    if result.is_error:
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        code = error.get("code", "UNKNOWN")
        allowed = {
            key: error[key]
            for key in (
                "httpStatus",
                "providerErrorCode",
                "providerErrorMessage",
                "providerRequestId",
                "rejectionReason",
            )
            if key in error
        }
        raise ToolFailure(name, str(code), allowed)
    if payload is None:
        raise E2EFailure(f"{name}:NO_JSON")
    return payload


def bind_candidate(
    request: SpeechGenerationRequest, rank: int
) -> tuple[SpeechGenerationRequest, list[dict[str, Any]]]:
    candidates = rank_bailian_qwen_voice_candidates(request, limit=3)
    candidate = candidates[rank - 1]
    profile = request.voice_profile.model_copy(
        update={"provider_mappings": [candidate]}
    )
    payload = request.model_dump(mode="json", by_alias=True)
    payload["voiceProfile"] = profile.model_dump(mode="json", by_alias=True)
    payload["providerMapping"] = candidate.model_dump(mode="json", by_alias=True)
    return (
        SpeechGenerationRequest.model_validate(payload),
        list(candidate.non_material_metadata["candidateRanking"]),
    )


def friendly_copy(
    item: dict[str, Any], workspace: Path, review_root: Path, slug: str, rank: int, run_id: str
) -> str:
    source = workspace / str(item["artifact"])
    suffix = source.suffix or ".audio"
    target = review_root / f"{slug}-candidate-{rank}-{run_id[:8]}{suffix}"
    shutil.copyfile(source, target)
    if sha256_file(target) != item["sha256"]:
        raise E2EFailure("FRIENDLY_REVIEW_COPY_HASH_MISMATCH")
    return str(target.relative_to(workspace))


async def import_resumable_audio(
    session: ClientSession,
    request: SpeechGenerationRequest,
    ranking: list[dict[str, Any]],
    provider_payload: dict[str, Any],
    source_path: Path,
) -> dict[str, Any]:
    """Finish Media import after a confirmed provider file survived locally."""

    mapping = request.provider_mapping
    if mapping is None:
        raise E2EFailure("CANDIDATE_MAPPING_MISSING")
    fingerprint = audio_input_fingerprint(request)
    prefix = f"speech-{fingerprint}-"
    if not source_path.name.startswith(prefix) or not source_path.suffix:
        raise E2EFailure("RESUME_AUDIO_IDENTITY_MISMATCH")
    attempt_id = source_path.name[len(prefix) : -len(source_path.suffix)]
    if not attempt_id or ":" in attempt_id:
        raise E2EFailure("RESUME_AUDIO_ATTEMPT_ID_INVALID")
    physical = probe_media(source_path)
    if not any(stream.get("codec_type") == "audio" for stream in physical.streams):
        raise E2EFailure("RESUME_AUDIO_STREAM_MISSING")
    content: dict[str, Any] = {
        "schemaVersion": "speech-clip-v1",
        "sceneId": request.scene_id,
        "spokenContentId": request.spoken_content_id,
        "speakerKey": request.speaker_key,
        "textHash": text_hash(request.exact_text),
        "voiceProfileFingerprint": voice_profile_fingerprint(request.voice_profile),
        "providerMappingFingerprint": provider_mapping_fingerprint(mapping),
        "pronunciationFingerprint": pronunciation_fingerprint(
            request.pronunciation_guidance
        ),
        "audioInputFingerprint": fingerprint,
        "provider": mapping.provider,
        "model": mapping.model,
        "actualDurationMs": physical.duration_ms,
        "reviewStatus": AudioReviewStatus.PENDING.value,
        "voiceBindingStatus": mapping.non_material_metadata.get(
            "voiceBindingStatus", "APPROVED"
        ),
        "exactTextInputVerified": True,
        "voiceCandidateRanking": ranking,
        "providerVoiceId": mapping.voice_id,
        "providerCallCount": 1,
        "providerRetryCount": 0,
        "providerDownloadCallCount": 1,
        "audioSha256": sha256_file(source_path),
        "providerRequestFingerprint": canonical_hash(provider_payload),
        "resumedAfterLocalImportRootMismatch": True,
    }
    imported = await call_tool(
        session,
        "media.import_media",
        {
            "work_id": request.work_id,
            "media_type": "AUDIO",
            "source_uri": source_path.resolve().as_uri(),
            "content": content,
            "purpose": "SPEECH_CLIP",
            "source_ref": source_ref_for_review(
                fingerprint, AudioReviewStatus.PENDING, attempt_id=attempt_id
            ),
            "duration_ms": physical.duration_ms,
        },
    )
    if not isinstance(imported, dict):
        raise E2EFailure("RESUME_MEDIA_IMPORT_RESPONSE_INVALID")
    return imported


async def run(args: argparse.Namespace) -> int:
    workspace = Path(__file__).resolve().parents[3]
    mcp_url, retry_limit, review_root = require_runtime(workspace)
    review_root.mkdir(parents=True, exist_ok=True)
    output_root = args.output_root.resolve()
    evidence_path = output_root / "evidence" / args.evidence_name
    request_path = output_root / "evidence" / "generation-request-7.2s-r-e2e.json"
    ranking_path = output_root / "evidence" / "voice-candidate-ranking-7.2s-r-e2e.json"
    source = json.loads(request_path.read_text(encoding="utf-8"))
    ranking_source = json.loads(ranking_path.read_text(encoding="utf-8"))
    requests = {
        item["spokenContentId"]: SpeechGenerationRequest.model_validate(item)
        for item in source["requests"]
    }
    expected_rankings = {
        item["spokenContentId"]: item["ranking"]
        for item in ranking_source["items"]
    }
    run_id = uuid.uuid4().hex
    planned_order = PLANNED_ORDER[
        args.start_index : args.start_index + args.max_items
    ]
    evidence: dict[str, Any] = {
        "schemaVersion": "batch-7.2s-r-e2e-real-generation-v1",
        "status": "IN_PROGRESS",
        "freshE2E": True,
        "e2eRunId": run_id,
        "historicalAmbiguousRetry": False,
        "historicalRejectedRetry": False,
        "runPurpose": args.run_purpose,
        "plannedAudioItems": len(planned_order),
        "providerSubmissionAttempts": 0,
        "confirmedProviderCalls": 0,
        "safeTransientRetries": 0,
        "ambiguousItems": 0,
        "providerRejectedItems": 0,
        "transientRetryExhaustedItems": 0,
        "openAiRealCalls": 0,
        "safeTransientRetryLimitPerItem": retry_limit,
        "items": [],
        "secretsRecorded": False,
        "signedUrlsRecorded": False,
    }
    write_json(evidence_path, evidence)

    try:
        async with streamable_http_client(mcp_url) as streams:
            async with ClientSession(*streams[:2]) as session:
                initialized = await session.initialize()
                if initialized.server_info.name != "drama-mcp-service":
                    raise E2EFailure("MCP_SERVER_IDENTITY_INVALID")
                scene = await call_tool(
                    session, "scene.get_scene", {"scene_id": SCENE_ID}
                )
                canonical_dialogue = {
                    item["id"]: item["text"]
                    for item in scene.get("content", {}).get("spokenContent", [])
                }

                for dialogue_id, slug, rank in planned_order:
                    request = requests[dialogue_id]
                    if canonical_dialogue.get(dialogue_id) != request.exact_text:
                        raise E2EFailure(f"EXACT_DIALOGUE_MISMATCH:{dialogue_id}")
                    bound, ranking = bind_candidate(request, rank)
                    if ranking != expected_rankings[dialogue_id]:
                        raise E2EFailure(f"CANDIDATE_RANKING_CHANGED:{dialogue_id}")
                    mapping = bound.provider_mapping
                    if mapping is None:
                        raise E2EFailure("CANDIDATE_MAPPING_MISSING")
                    compatibility = bailian_qwen_voice_compatibility(
                        mapping.model, mapping.voice_id
                    )
                    if compatibility != "COMPATIBLE":
                        raise E2EFailure(
                            f"VOICE_MODEL_COMPATIBILITY_{compatibility}:"
                            f"{mapping.model}:{mapping.voice_id}"
                        )
                    operation_material = {
                        "schemaVersion": "fresh-e2e-operation-v1",
                        "e2eRunId": run_id,
                        "spokenContentId": dialogue_id,
                        "candidateRank": rank,
                        "audioInputFingerprint": audio_input_fingerprint(bound),
                    }
                    operation_fingerprint = canonical_hash(operation_material)
                    request_payload = bound.model_dump(mode="json", by_alias=True)
                    provider_payload = compile_bailian_qwen_speech_payload(bound)
                    provider_input = provider_payload["input"]
                    instruction = str(provider_input.get("instructions", ""))
                    semantic_source = {
                        "voiceProfile": request_payload["voiceProfile"],
                        "sceneState": request_payload.get("sceneState"),
                        "performanceIntent": request_payload.get(
                            "performanceIntent"
                        ),
                    }
                    request_payload["nonMaterialMetadata"] = {
                        **request_payload.get("nonMaterialMetadata", {}),
                        "freshE2E": True,
                        "historicalAmbiguousRetry": False,
                        "historicalRejectedRetry": False,
                        "runPurpose": args.run_purpose,
                        "e2eRunId": run_id,
                        "candidateRank": rank,
                        "freshOperationFingerprint": operation_fingerprint,
                    }
                    item_evidence: dict[str, Any] = {
                        "spokenContentId": dialogue_id,
                        "speakerKey": bound.speaker_key,
                        "candidateRank": rank,
                        "providerVoiceId": mapping.voice_id,
                        "voiceModelCompatibility": compatibility,
                        "freshOperationFingerprint": operation_fingerprint,
                        "audioInputFingerprint": audio_input_fingerprint(bound),
                        "freshE2E": True,
                        "historicalAmbiguousRetry": False,
                        "historicalRejectedRetry": False,
                        "exactTextInputVerified": True,
                        "model": mapping.model,
                        "textCharacters": len(bound.exact_text),
                        "textUtf8Bytes": len(bound.exact_text.encode("utf-8")),
                        "instructionCharacters": len(instruction),
                        "instructionUtf8Bytes": len(instruction.encode("utf-8")),
                        "payloadFieldNames": sorted(provider_payload),
                        "providerInputFieldNames": sorted(provider_input),
                        "semanticSourceHash": canonical_hash(semantic_source),
                        "compiledInstructionHash": hashlib.sha256(
                            instruction.encode("utf-8")
                        ).hexdigest(),
                        "resultClassification": "SUBMITTING",
                    }
                    evidence["items"].append(item_evidence)
                    write_json(evidence_path, evidence)
                    try:
                        if args.resume_local_audio is not None:
                            generated = await import_resumable_audio(
                                session,
                                bound,
                                ranking,
                                provider_payload,
                                args.resume_local_audio,
                            )
                            item_evidence["resumedProviderSubmission"] = True
                        else:
                            evidence["providerSubmissionAttempts"] += 1
                            write_json(evidence_path, evidence)
                            generated = await call_tool(
                                session,
                                "production.generate_audio",
                                {"request": request_payload},
                            )
                    except ToolFailure as exc:
                        item_evidence["resultClassification"] = exc.code
                        if exc.diagnostics:
                            item_evidence["rejectionDiagnostics"] = exc.diagnostics
                        if exc.code == "AMBIGUOUS_RESULT":
                            evidence["ambiguousItems"] += 1
                        elif exc.code == "PROVIDER_REJECTED":
                            evidence["providerRejectedItems"] += 1
                            # A deterministic provider rejection confirms that the
                            # request reached the provider, even though no Audio was
                            # created and no success metadata is available.
                            evidence["confirmedProviderCalls"] += 1
                        elif exc.code == "TRANSIENT_RETRY_EXHAUSTED":
                            evidence["transientRetryExhaustedItems"] += 1
                        evidence["status"] = (
                            "AMBIGUOUS" if exc.code == "AMBIGUOUS_RESULT" else "STOPPED"
                        )
                        evidence["stopCode"] = exc.code
                        write_json(evidence_path, evidence)
                        if (
                            exc.code == "PROVIDER_REJECTED"
                            and exc.diagnostics.get("rejectionReason")
                            == "VOICE_MODEL_INCOMPATIBLE"
                        ):
                            evidence["status"] = "IN_PROGRESS"
                            evidence.pop("stopCode", None)
                            write_json(evidence_path, evidence)
                            continue
                        raise

                    fetched = await call_tool(
                        session,
                        "media.get_media",
                        {"media_id": generated["id"]},
                    )
                    if fetched.get("id") != generated.get("id"):
                        raise E2EFailure("MEDIA_GET_ID_MISMATCH")
                    source_ref = fetched.get("sourceRef")
                    listed = await call_tool(
                        session,
                        "media.list_media",
                        {
                            "media_type": "AUDIO",
                            "work_id": WORK_ID,
                            "purpose": "SPEECH_CLIP",
                            "source_ref": source_ref,
                        },
                    )
                    if len(listed) != 1 or listed[0].get("id") != fetched["id"]:
                        raise E2EFailure("MEDIA_LIST_ATTEMPT_IDENTITY_MISMATCH")
                    validated = await validate_media(
                        session, fetched, review_root, workspace
                    )
                    if validated.get("reviewStatus") != "PENDING":
                        raise E2EFailure("FRESH_CANDIDATE_NOT_PENDING")
                    content = fetched.get("content", {})
                    if content.get("voiceBindingStatus") != "PENDING":
                        raise E2EFailure("VOICE_BINDING_NOT_PENDING")
                    friendly = friendly_copy(
                        validated, workspace, review_root, slug, rank, run_id
                    )
                    item_evidence.update(validated)
                    item_evidence.update(
                        {
                            "reviewArtifact": friendly,
                            "sourceRef": source_ref,
                            "resultClassification": "PASS_PENDING_USER_REVIEW",
                            "mediaGet": "PASS",
                            "mediaList": "PASS",
                            "mediaResolveDownload": "PASS",
                            "currentEnvironmentStorage": "PASS",
                            "voiceBinding": "PENDING",
                            "providerRequestFingerprint": content.get(
                                "providerRequestFingerprint"
                            ),
                        }
                    )
                    evidence["confirmedProviderCalls"] += int(
                        validated.get("providerCallCount") or 0
                    )
                    evidence["safeTransientRetries"] += int(
                        validated.get("providerRetryCount") or 0
                    )
                    write_json(evidence_path, evidence)

        evidence["status"] = (
            "DIAGNOSTIC_PROBE_SUCCESS"
            if args.run_purpose == "DIAGNOSTIC_PROBE_1"
            else "READY_FOR_USER_AUDIO_REVIEW"
        )
        evidence["realAudioCreated"] = True
        evidence["audioTechnicalValidation"] = "PASS"
        evidence["freshAudioMediaCreated"] = True
        evidence["currentEnvironmentMediaRoundtrip"] = "PASS"
        evidence["voiceBinding"] = "PENDING"
        evidence["userAudioReview"] = "PENDING"
        evidence["audioApproved"] = "NOT_SET"
        evidence["oldEnvironmentMediaRequired"] = False
        evidence["comfyUiCalls"] = 0
        evidence["batch73"] = "NOT_STARTED"
        write_json(evidence_path, evidence)
        print(
            json.dumps(
                {
                    "status": evidence["status"],
                    "e2eRunId": run_id,
                    "providerSubmissionAttempts": evidence[
                        "providerSubmissionAttempts"
                    ],
                    "confirmedProviderCalls": evidence[
                        "confirmedProviderCalls"
                    ],
                    "safeTransientRetries": evidence["safeTransientRetries"],
                    "items": [
                        {
                            "spokenContentId": item["spokenContentId"],
                            "candidateRank": item["candidateRank"],
                            "providerVoiceId": item["providerVoiceId"],
                            "mediaId": item.get("mediaId"),
                            "reviewArtifact": item.get("reviewArtifact"),
                            "durationMs": item.get("durationMs"),
                            "codec": item.get("codec"),
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
    except ToolFailure as exc:
        print(
            json.dumps(
                {
                    "status": evidence["status"],
                    "stopCode": exc.code,
                    "providerSubmissionAttempts": evidence[
                        "providerSubmissionAttempts"
                    ],
                    "confirmedProviderCalls": evidence[
                        "confirmedProviderCalls"
                    ],
                    "batch73": "NOT_STARTED",
                },
                ensure_ascii=False,
            )
        )
        return 2
    except Exception as exc:
        # streamable_http_client may wrap the already-recorded ToolFailure in an
        # ExceptionGroup while closing its task group. Preserve the exact paid-call
        # classification written at the call boundary.
        if evidence.get("status") not in {"AMBIGUOUS", "STOPPED"}:
            evidence["status"] = "FAILED"
            evidence["stopCode"] = type(exc).__name__
        write_json(evidence_path, evidence)
        print(
            json.dumps(
                {
                    "status": evidence["status"],
                    "stopCode": evidence["stopCode"],
                    "providerSubmissionAttempts": evidence[
                        "providerSubmissionAttempts"
                    ],
                    "batch73": "NOT_STARTED",
                },
                ensure_ascii=False,
            )
        )
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "artifacts" / "batch7-2",
    )
    parser.add_argument("--start-index", type=int, default=0, choices=range(4))
    parser.add_argument("--max-items", type=int, default=4, choices=range(1, 5))
    parser.add_argument(
        "--run-purpose",
        choices=("DIAGNOSTIC_PROBE_1", "AUDITION_RESUME"),
        default="AUDITION_RESUME",
    )
    parser.add_argument(
        "--evidence-name",
        default="real-generation-evidence-7.2s-r-e2e.json",
    )
    parser.add_argument("--resume-local-audio", type=Path)
    args = parser.parse_args()
    if Path(args.evidence_name).name != args.evidence_name:
        parser.error("--evidence-name must be a filename")
    if args.start_index + args.max_items > len(PLANNED_ORDER):
        parser.error("selected planned items exceed the fixed candidate plan")
    if args.resume_local_audio is not None and args.max_items != 1:
        parser.error("--resume-local-audio requires --max-items 1")
    return args


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
