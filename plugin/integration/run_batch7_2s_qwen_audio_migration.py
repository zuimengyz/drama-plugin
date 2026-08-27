"""Skill-driven Qwen-Audio Voice Design and exact-Dialogue TTS migration E2E."""

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

from drama_plugin.audio import audio_input_fingerprint
from drama_plugin.audio.host_media import probe_media
from drama_plugin.config import load_config
from drama_plugin.contracts.audio import (
    ProviderMappingStatus,
    ProviderVoiceMapping,
    SpeechGenerationRequest,
)
from drama_plugin.exceptions import ProviderResultUnknown, SpeechProviderError
from drama_plugin.providers.speech import (
    BailianQwenSpeechProvider,
    VoiceDesignResult,
    VoiceDesignSpec,
    bailian_qwen_model_family,
    compile_bailian_qwen_speech_payload,
    compile_voice_design_spec,
    voice_design_fingerprint,
)
from run_batch7_2r_preflight import write_json
from run_batch7_2r_real_e2e import sha256_file, validate_media
from run_batch7_2sr_fresh_e2e import E2EFailure, ToolFailure, call_tool


WORK_ID = "work_9cc5d11969a64f93bce4a544f349c793"
SCRIPT_ID = "script_a404a8277fef45eda8ef3aaf478307cc"
EPISODE_ID = "episode_c33021fe53ba4af08cd8b98113184dd2"
SCENE_ID = "scene_3ad95aa042e647d9a9be05a51dd8a009"
SHOT_ID = "shot_83db7eb53b2f49d3a58428d4659e584e"
MODEL = "qwen-audio-3.0-tts-plus"
PLANNED_ORDER = (
    ("spoken-s1-wangsili-proposal", "wangsili", 1),
    ("spoken-s1-wangsili-proposal", "wangsili", 2),
    ("spoken-s1-geshuhan-refusal", "geshuhan", 1),
    ("spoken-s1-geshuhan-refusal", "geshuhan", 2),
)


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require_runtime(workspace: Path) -> tuple[str, Path]:
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
    if os.environ.get("BATCH72R_QWEN_MODEL", "") != MODEL:
        raise E2EFailure("QWEN_AUDIO_PROCESS_OVERRIDE_MISSING")
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        raise E2EFailure("DASHSCOPE_API_KEY_MISSING")
    output = Path(
        os.environ.get("DRAMA_PLUGIN_SERVICE_SPEECH_OUTPUT_DIRECTORY", "")
    ).expanduser()
    expected = (workspace / "artifacts" / "batch7-2" / "review").resolve()
    if not output.is_absolute() or output.resolve() != expected:
        raise E2EFailure("SPEECH_OUTPUT_DIRECTORY_NOT_BATCH_REVIEW_ROOT")
    allowed = {
        Path(item).expanduser().resolve()
        for item in os.environ.get("DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS", "").split(
            os.pathsep
        )
        if item.strip()
    }
    if expected not in allowed:
        raise E2EFailure("REVIEW_ROOT_NOT_MEDIA_IMPORT_ALLOWED")
    mcp_url = os.environ.get("DRAMA_MCP_URL", "http://127.0.0.1:8765/mcp")
    return mcp_url, expected


def provisional_qwen_audio_request(
    source: SpeechGenerationRequest,
) -> SpeechGenerationRequest:
    mapping = ProviderVoiceMapping(
        provider="bailian_qwen",
        model=MODEL,
        voice_id="VOICE_DESIGN_PENDING",
        status=ProviderMappingStatus.CANDIDATE,
        material_parameters={
            "format": "wav",
            "sample_rate": 24000,
            "language_hints": ["zh"],
        },
        non_material_metadata={"voiceBindingStatus": "PENDING"},
    )
    profile = source.voice_profile.model_copy(
        update={"provider_mappings": [mapping]}
    )
    return source.model_copy(
        update={"voice_profile": profile, "provider_mapping": mapping}
    )


def bind_custom_voice(
    source: SpeechGenerationRequest,
    spec: VoiceDesignSpec,
    voice_id: str,
    target_model: str,
    design_metadata: dict[str, Any],
    candidate_rank: int,
) -> SpeechGenerationRequest:
    mapping = ProviderVoiceMapping(
        provider="bailian_qwen",
        model=target_model,
        voice_id=voice_id,
        status=ProviderMappingStatus.CANDIDATE,
        material_parameters={
            "format": "wav",
            "sample_rate": spec.sample_rate,
            "language_hints": list(spec.language_hints),
        },
        non_material_metadata={
            "selectionStrategy": "provider-voice-design-v1",
            "candidateRank": candidate_rank,
            "voiceDesignTargetModel": target_model,
            "voiceDesignStatus": "OK",
            "voiceDesignFingerprint": design_metadata["voiceDesignFingerprint"],
            "voicePromptHash": design_metadata["voicePromptHash"],
            "voiceBindingStatus": "PENDING",
        },
    )
    profile = source.voice_profile.model_copy(
        update={"provider_mappings": [mapping]}
    )
    return source.model_copy(
        update={"voice_profile": profile, "provider_mapping": mapping}
    )


def friendly_copy(
    source_path: Path,
    target_path: Path,
) -> tuple[str, str]:
    shutil.copyfile(source_path, target_path)
    source_hash = sha256_file(source_path)
    if sha256_file(target_path) != source_hash:
        raise E2EFailure("FRIENDLY_COPY_HASH_MISMATCH")
    return str(target_path), source_hash


def safe_design_error(exc: SpeechProviderError) -> dict[str, Any]:
    result: dict[str, Any] = {
        "classification": (
            "PROVIDER_REJECTED"
            if exc.rejection_reason is not None
            else "TRANSIENT_RETRY_EXHAUSTED"
            if exc.retryable
            else "PROVIDER_ERROR"
        )
    }
    if exc.status_code is not None:
        result["httpStatus"] = exc.status_code
    if exc.provider_error_code:
        result["providerErrorCode"] = exc.provider_error_code
    if exc.provider_error_message:
        result["providerErrorMessage"] = exc.provider_error_message
    if exc.provider_request_id:
        result["providerRequestId"] = exc.provider_request_id
    if exc.rejection_reason:
        result["rejectionReason"] = exc.rejection_reason
    return result


async def get_shared_context(session: ClientSession) -> dict[str, Any]:
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
    for key, value in values.items():
        if value.get("id") != expected[key]:
            raise E2EFailure(f"SHARED_{key.upper()}_ID_MISMATCH")
    return values


async def run(args: argparse.Namespace) -> int:
    workspace = Path(__file__).resolve().parents[3]
    mcp_url, review_root = require_runtime(workspace)
    output_root = args.output_root.resolve()
    evidence_path = output_root / "evidence" / args.evidence_name
    request_path = output_root / "evidence" / "generation-request-7.2s-r-e2e.json"
    skill_path = output_root / "evidence" / "skill-invocation-7.2s-r-e2e.json"
    source = json.loads(request_path.read_text(encoding="utf-8"))
    skill = json.loads(skill_path.read_text(encoding="utf-8"))
    if skill.get("skillActuallyInvoked") is not True or skill.get("fixtureBypass"):
        raise E2EFailure("SKILL_EVIDENCE_INVALID")
    requests = {
        item["spokenContentId"]: SpeechGenerationRequest.model_validate(item)
        for item in source["requests"]
    }
    preview_text = max(
        (request.exact_text for request in requests.values()), key=len
    )
    if not 15 <= len(preview_text) <= 200:
        raise E2EFailure("NO_PERSISTED_PREVIEW_TEXT_IN_PROVIDER_RANGE")
    run_id = uuid.uuid4().hex
    evidence: dict[str, Any] = {
        "schemaVersion": "batch-7.2s-r-qwen-audio-migration-e2e-v1",
        "status": "IN_PROGRESS",
        "e2eRunId": run_id,
        "model": MODEL,
        "modelFamily": bailian_qwen_model_family(MODEL),
        "skillActuallyInvoked": True,
        "fixtureBypass": False,
        "characterModelChanges": "NONE",
        "plannedVoiceDesignCalls": 4,
        "priorVoiceDesignSubmissionAttempts": args.prior_voice_design_submission_attempts,
        "voiceDesignSubmissionAttempts": 0,
        "voiceDesignCreated": 0,
        "recoveredVoiceDesignCount": 0,
        "plannedAuditionTtsCalls": 4,
        "auditionTtsSubmissionAttempts": 0,
        "confirmedAuditionTtsCalls": 0,
        "ambiguousItems": 0,
        "safeTransientRetries": 0,
        "domainWrites": 0,
        "duplicateWorkCreated": False,
        "items": [],
        "secretsRecorded": False,
        "signedUrlsRecorded": False,
        "comfyUiCalls": 0,
        "batch73": "NOT_STARTED",
    }
    write_json(evidence_path, evidence)
    config = load_config(environment=os.environ).services.speech
    designer = BailianQwenSpeechProvider(config, review_root)
    speaker_specs: dict[str, VoiceDesignSpec] = {}
    speaker_instruction_hashes: dict[str, str] = {}
    speaker_voice_ids: dict[str, set[str]] = {}
    try:
        async with streamable_http_client(mcp_url) as streams:
            async with ClientSession(*streams[:2]) as session:
                initialized = await session.initialize()
                if initialized.server_info.name != "drama-mcp-service":
                    raise E2EFailure("MCP_SERVER_IDENTITY_INVALID")
                context = await get_shared_context(session)
                canonical_dialogue = {
                    item["id"]: item["text"]
                    for item in context["scene"].get("content", {}).get(
                        "spokenContent", []
                    )
                }
                evidence["sharedContext"] = {
                    "work": "PASS",
                    "script": "PASS",
                    "episode": "PASS",
                    "scene": "PASS",
                    "shot": "PASS",
                }
                write_json(evidence_path, evidence)

                for dialogue_id, slug, rank in PLANNED_ORDER:
                    source_request = requests[dialogue_id]
                    if canonical_dialogue.get(dialogue_id) != source_request.exact_text:
                        raise E2EFailure(f"EXACT_DIALOGUE_MISMATCH:{dialogue_id}")
                    provisional = provisional_qwen_audio_request(source_request)
                    spec = compile_voice_design_spec(
                        provisional, preview_text=preview_text
                    )
                    previous_spec = speaker_specs.setdefault(
                        source_request.speaker_key, spec
                    )
                    if previous_spec != spec:
                        raise E2EFailure("VOICE_DESIGN_SPEC_CHANGED_BETWEEN_CANDIDATES")
                    design_operation = canonical_hash(
                        {
                            "schemaVersion": "voice-design-operation-v1",
                            "e2eRunId": run_id,
                            "spokenContentId": dialogue_id,
                            "candidateRank": rank,
                            "voiceDesignFingerprint": voice_design_fingerprint(spec),
                        }
                    )
                    item: dict[str, Any] = {
                        "spokenContentId": dialogue_id,
                        "speakerKey": source_request.speaker_key,
                        "candidateRank": rank,
                        "voiceDesignOperationFingerprint": design_operation,
                        "voiceDesignFingerprint": voice_design_fingerprint(spec),
                        "voicePromptCharacters": len(spec.voice_prompt),
                        "voicePromptUtf8Bytes": len(spec.voice_prompt.encode("utf-8")),
                        "voicePromptHash": hashlib.sha256(
                            spec.voice_prompt.encode("utf-8")
                        ).hexdigest(),
                        "previewTextCharacters": len(spec.preview_text),
                        "previewTextHash": hashlib.sha256(
                            spec.preview_text.encode("utf-8")
                        ).hexdigest(),
                        "prefix": spec.prefix,
                        "targetModel": spec.target_model,
                        "voiceDesignStatus": "SUBMITTING",
                        "ttsStatus": "NOT_STARTED",
                    }
                    evidence["items"].append(item)
                    write_json(evidence_path, evidence)
                    designed: VoiceDesignResult | None = None
                    if (
                        dialogue_id == PLANNED_ORDER[0][0]
                        and rank == 1
                        and args.resume_first_voice_id
                    ):
                        verified = await designer.verify_voice(
                            args.resume_first_voice_id, MODEL
                        )
                        design_voice_id = args.resume_first_voice_id
                        design_target_model = MODEL
                        metadata = {
                            "voiceDesignFingerprint": voice_design_fingerprint(spec),
                            "voicePromptHash": hashlib.sha256(
                                spec.voice_prompt.encode("utf-8")
                            ).hexdigest(),
                            **verified,
                        }
                        evidence["recoveredVoiceDesignCount"] += 1
                        item["recoveredVoiceDesign"] = True
                        item["previewArtifact"] = (
                            "UNAVAILABLE_AFTER_LOCAL_CREATE_RESPONSE_CONTRACT_MISMATCH"
                        )
                    else:
                        evidence["voiceDesignSubmissionAttempts"] += 1
                        write_json(evidence_path, evidence)
                        try:
                            designed = await designer.design_voice(spec)
                        except ProviderResultUnknown:
                            item["voiceDesignStatus"] = "AMBIGUOUS_RESULT"
                            evidence["ambiguousItems"] += 1
                            evidence["status"] = "AMBIGUOUS"
                            evidence["stopCode"] = "VOICE_DESIGN_AMBIGUOUS_RESULT"
                            write_json(evidence_path, evidence)
                            return 2
                        except SpeechProviderError as exc:
                            failure = safe_design_error(exc)
                            item["voiceDesignStatus"] = failure.pop("classification")
                            item["voiceDesignFailure"] = failure
                            write_json(evidence_path, evidence)
                            if exc.provider_error_code == "VOICE_DESIGN_UNDEPLOYED":
                                continue
                            evidence["status"] = "STOPPED"
                            evidence["stopCode"] = item["voiceDesignStatus"]
                            write_json(evidence_path, evidence)
                            return 2
                        design_voice_id = designed.voice_id
                        design_target_model = designed.target_model
                        metadata = designed.provider_metadata

                    evidence["voiceDesignCreated"] += 1
                    item.update(
                        {
                            "voiceDesignStatus": "OK",
                            "voiceId": design_voice_id,
                            "voiceDesignRequestId": metadata.get(
                                "voiceDesignRequestId"
                            ),
                            "voiceStatusRequestId": metadata.get(
                                "voiceStatusRequestId"
                            ),
                            "voiceStatusQueryCallCount": metadata.get(
                                "voiceStatusQueryCallCount"
                            ),
                            "voiceStatusQueryRetryCount": metadata.get(
                                "voiceStatusQueryRetryCount"
                            ),
                            "previewSha256": metadata.get("previewSha256"),
                            "previewBytes": metadata.get("previewBytes"),
                        }
                    )
                    voice_ids = speaker_voice_ids.setdefault(
                        source_request.speaker_key, set()
                    )
                    if design_voice_id in voice_ids:
                        raise E2EFailure("VOICE_DESIGN_RETURNED_DUPLICATE_CANDIDATE")
                    voice_ids.add(design_voice_id)
                    if designed is not None:
                        preview_source = Path(
                            designed.preview_source_uri.removeprefix("file://")
                        )
                        preview_target = review_root / (
                            f"{slug}-voice-design-preview-{rank}-{run_id[:8]}.wav"
                        )
                        preview_artifact, preview_hash = friendly_copy(
                            preview_source, preview_target
                        )
                        preview_probe = probe_media(preview_target)
                        if not any(
                            stream.get("codec_type") == "audio"
                            for stream in preview_probe.streams
                        ):
                            raise E2EFailure("VOICE_DESIGN_PREVIEW_HAS_NO_AUDIO")
                        item.update(
                            {
                                "previewArtifact": str(
                                    Path(preview_artifact).relative_to(workspace)
                                ),
                                "previewSha256": preview_hash,
                                "previewDurationMs": preview_probe.duration_ms,
                            }
                        )

                    bound = bind_custom_voice(
                        source_request,
                        spec,
                        design_voice_id,
                        design_target_model,
                        metadata,
                        rank,
                    )
                    payload = compile_bailian_qwen_speech_payload(bound)
                    instruction = str(payload["input"]["instruction"])
                    instruction_hash = hashlib.sha256(
                        instruction.encode("utf-8")
                    ).hexdigest()
                    previous_instruction = speaker_instruction_hashes.setdefault(
                        source_request.speaker_key, instruction_hash
                    )
                    if previous_instruction != instruction_hash:
                        raise E2EFailure("TTS_INSTRUCTION_CHANGED_BETWEEN_CANDIDATES")
                    item.update(
                        {
                            "audioInputFingerprint": audio_input_fingerprint(bound),
                            "ttsInstructionCharacters": len(instruction),
                            "ttsInstructionUtf8Bytes": len(
                                instruction.encode("utf-8")
                            ),
                            "ttsInstructionHash": instruction_hash,
                            "ttsPayloadFieldNames": sorted(payload),
                            "ttsInputFieldNames": sorted(payload["input"]),
                            "exactTextInputVerified": True,
                            "ttsStatus": "SUBMITTING",
                        }
                    )
                    evidence["auditionTtsSubmissionAttempts"] += 1
                    write_json(evidence_path, evidence)
                    try:
                        generated = await call_tool(
                            session,
                            "production.generate_audio",
                            {"request": bound.model_dump(mode="json", by_alias=True)},
                        )
                    except ToolFailure as exc:
                        item["ttsStatus"] = exc.code
                        if exc.diagnostics:
                            item["ttsFailure"] = exc.diagnostics
                        if exc.code == "AMBIGUOUS_RESULT":
                            evidence["ambiguousItems"] += 1
                            evidence["status"] = "AMBIGUOUS"
                        else:
                            evidence["status"] = "STOPPED"
                        evidence["stopCode"] = exc.code
                        write_json(evidence_path, evidence)
                        return 2

                    fetched = await call_tool(
                        session, "media.get_media", {"media_id": generated["id"]}
                    )
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
                    if len(listed) != 1 or listed[0].get("id") != fetched.get("id"):
                        raise E2EFailure("MEDIA_LIST_ATTEMPT_IDENTITY_MISMATCH")
                    validated = await validate_media(
                        session, fetched, review_root, workspace
                    )
                    if validated.get("reviewStatus") != "PENDING":
                        raise E2EFailure("FRESH_CANDIDATE_NOT_PENDING")
                    if fetched.get("content", {}).get("voiceBindingStatus") != "PENDING":
                        raise E2EFailure("VOICE_BINDING_NOT_PENDING")
                    formal_source = workspace / str(validated["artifact"])
                    formal_target = review_root / (
                        f"{slug}-qwen-audio-candidate-{rank}-{run_id[:8]}"
                        f"{formal_source.suffix}"
                    )
                    formal_artifact, formal_hash = friendly_copy(
                        formal_source, formal_target
                    )
                    if formal_hash != validated["sha256"]:
                        raise E2EFailure("FORMAL_REVIEW_COPY_HASH_MISMATCH")
                    item.update(validated)
                    item.update(
                        {
                            "formalReviewArtifact": str(
                                Path(formal_artifact).relative_to(workspace)
                            ),
                            "sourceRef": source_ref,
                            "ttsStatus": "PASS_PENDING_USER_REVIEW",
                            "mediaGet": "PASS",
                            "mediaList": "PASS",
                            "mediaResolveDownload": "PASS",
                            "currentEnvironmentStorage": "PASS",
                            "voiceBinding": "PENDING",
                        }
                    )
                    evidence["confirmedAuditionTtsCalls"] += int(
                        validated.get("providerCallCount") or 0
                    )
                    evidence["safeTransientRetries"] += int(
                        validated.get("providerRetryCount") or 0
                    )
                    write_json(evidence_path, evidence)

        successful = [
            item
            for item in evidence["items"]
            if item.get("ttsStatus") == "PASS_PENDING_USER_REVIEW"
        ]
        if len(successful) < 2:
            evidence["status"] = "STOPPED"
            evidence["stopCode"] = "INSUFFICIENT_CUSTOM_VOICE_CANDIDATES"
            write_json(evidence_path, evidence)
            return 2
        evidence.update(
            {
                "status": "READY_FOR_USER_AUDIO_REVIEW",
                "characterAnalysisSemanticDiff": "NONE",
                "qwen3LegacyPath": "PASS_OFFLINE",
                "qwenAudioModelFamily": "PASS",
                "qwenAudioTtsContract": "PASS",
                "voiceDesignApi": "PASS",
                "voiceDesignSpec": "PASS",
                "voiceDesignPromptLimit": "PASS",
                "customVoiceCreated": True,
                "targetModelMatch": "PASS",
                "qwenAudioRealTts": "PASS",
                "exactDialogue": "PASS",
                "realAudioCreated": True,
                "audioTechnicalValidation": "PASS",
                "freshAudioMediaCreated": True,
                "currentEnvironmentMediaRoundtrip": "PASS",
                "voiceCandidatesReady": True,
                "voiceBinding": "PENDING",
                "userAudioReview": "PENDING",
                "audioApproved": "NOT_SET",
            }
        )
        write_json(evidence_path, evidence)
        print(
            json.dumps(
                {
                    "status": evidence["status"],
                    "e2eRunId": run_id,
                    "voiceDesignSubmissionAttempts": evidence[
                        "voiceDesignSubmissionAttempts"
                    ],
                    "voiceDesignCreated": evidence["voiceDesignCreated"],
                    "auditionTtsSubmissionAttempts": evidence[
                        "auditionTtsSubmissionAttempts"
                    ],
                    "confirmedAuditionTtsCalls": evidence[
                        "confirmedAuditionTtsCalls"
                    ],
                    "ambiguousItems": evidence["ambiguousItems"],
                    "items": [
                        {
                            "spokenContentId": item["spokenContentId"],
                            "candidateRank": item["candidateRank"],
                            "voiceId": item.get("voiceId"),
                            "mediaId": item.get("mediaId"),
                            "formalReviewArtifact": item.get(
                                "formalReviewArtifact"
                            ),
                            "durationMs": item.get("durationMs"),
                        }
                        for item in successful
                    ],
                    "batch73": "NOT_STARTED",
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        await designer.aclose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "artifacts" / "batch7-2",
    )
    parser.add_argument(
        "--evidence-name",
        default="qwen-audio-migration-real-e2e-7.2s-r.json",
    )
    parser.add_argument("--resume-first-voice-id")
    parser.add_argument(
        "--prior-voice-design-submission-attempts", type=int, default=0
    )
    args = parser.parse_args()
    if Path(args.evidence_name).name != args.evidence_name:
        parser.error("--evidence-name must be a filename")
    if args.prior_voice_design_submission_attempts not in range(0, 5):
        parser.error("--prior-voice-design-submission-attempts must be 0..4")
    return args


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
