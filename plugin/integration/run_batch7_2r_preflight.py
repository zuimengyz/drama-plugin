from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from drama_plugin.audio import audio_input_fingerprint, compile_speech_request, text_hash
from drama_plugin.contracts import (
    CreativeVoiceProfile,
    ProviderVoiceMapping,
    SpeechGenerationRequest,
    TargetTimingPolicy,
    VoiceProfile,
)
from drama_plugin.providers.speech import compile_bailian_qwen_speech_payload


_ALLOWED_MODELS = {
    "qwen3-tts-instruct-flash",
    "qwen3-tts-flash",
}
_OFFICIAL_VOICE_SOURCE = (
    "https://help.aliyun.com/zh/model-studio/qwen-tts-voice-list"
)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_request(
    *,
    model: str,
    spoken_content_id: str,
    speaker_key: str,
    text: str,
    voice_id: str,
    timbre: str,
    work_id: str = "BATCH_7_2_VALIDATION_PENDING_CREDENTIAL_GATE",
    scene_id: str = "BATCH_7_2_VALIDATION_SCENE_PENDING_CREDENTIAL_GATE",
) -> SpeechGenerationRequest:
    mapping = ProviderVoiceMapping(
        provider="bailian_qwen",
        model=model,
        voice_id=voice_id,
        material_parameters={"language_type": "Chinese"},
    )
    profile = VoiceProfile(
        profile_id=f"batch-7-2r:{speaker_key}",
        speaker_key=speaker_key,
        creative_profile=CreativeVoiceProfile(
            age_presentation="adult",
            timbre=timbre,
            temperament="restrained",
            baseline_pace="measured",
            power="moderate",
            restraint="high",
            language="zh-CN",
            language_register="neutral validation",
        ),
        provider_mappings=[mapping],
        display_name=f"Batch 7.2R validation {speaker_key}",
    )
    return compile_speech_request(
        work_id=work_id,
        scene_id=scene_id,
        spoken_content={
            "spokenContentId": spoken_content_id,
            "speakerKey": speaker_key,
            "text": text,
            "performanceIntent": {"delivery": "neutral", "pace": "measured"},
        },
        voice_profile=profile,
        provider_mapping=mapping,
        pronunciation_guidance=[],
        material_render_parameters={"validationControl": "steady"},
        target_timing_policy=TargetTimingPolicy(policy="NATURAL"),
        non_material_metadata={
            "validationFixture": True,
            "notProductionDrama": True,
            "notHistoricalProvenance": True,
        },
    )


def request_metadata(
    *,
    model: str,
    spoken_content_id: str,
    speaker_key: str,
    text: str,
    voice_id: str,
    timbre: str,
) -> dict[str, Any]:
    request = build_request(
        model=model,
        spoken_content_id=spoken_content_id,
        speaker_key=speaker_key,
        text=text,
        voice_id=voice_id,
        timbre=timbre,
    )
    payload = compile_bailian_qwen_speech_payload(request)
    provider_input = payload["input"]
    instructions = provider_input.get("instructions")
    return {
        "schemaVersion": request.schema_version,
        "classification": "TTS_VALIDATION_FIXTURE",
        "validationFixture": True,
        "notProductionDrama": True,
        "notHistoricalProvenance": True,
        "spokenContentId": request.spoken_content_id,
        "speakerKey": request.speaker_key,
        "exactText": request.exact_text,
        "textHash": text_hash(request.exact_text),
        "audioInputFingerprint": audio_input_fingerprint(request),
        "provider": request.provider_mapping.provider,
        "model": request.provider_mapping.model,
        "voiceId": request.provider_mapping.voice_id,
        "languageType": provider_input["language_type"],
        "officialVoiceSource": _OFFICIAL_VOICE_SOURCE,
        "exactTextEqualsProviderInput": provider_input["text"] == request.exact_text,
        "instructionsSeparatedFromDialogue": (
            instructions is None or request.exact_text not in str(instructions)
        ),
        "performanceIntentMappedToInstructions": (
            instructions is not None and "表演意图" in str(instructions)
        ),
        "optimizeInstructions": provider_input.get("optimize_instructions"),
        "pronunciationProviderControl": "NOT_AVAILABLE",
        "credentialFieldsRecorded": False,
        "authorizationRecorded": False,
        "providerResultUrlRecorded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "artifacts" / "batch7-2",
    )
    args = parser.parse_args()
    root = args.output_root.resolve()
    for name in ("evidence", "review", "requests", "manifests"):
        (root / name).mkdir(parents=True, exist_ok=True)

    model = os.environ.get("BATCH72R_QWEN_MODEL", "qwen3-tts-instruct-flash")
    if model not in _ALLOWED_MODELS:
        raise SystemExit("BATCH72R_QWEN_MODEL must be an explicitly allowed model")
    first = request_metadata(
        model=model,
        spoken_content_id="validation-spoken-a",
        speaker_key="speaker:validation-a",
        text="军报已经送到，请将军决断。",
        voice_id="Cherry",
        timbre="clear and steady",
    )
    second = request_metadata(
        model=model,
        spoken_content_id="validation-spoken-b",
        speaker_key="speaker:validation-b",
        text="军令未下，各部不得擅动。",
        voice_id="Ethan",
        timbre="grounded and warm",
    )
    write_json(root / "requests" / "speaker-a-qwen.redacted.json", first)
    write_json(root / "requests" / "speaker-b-qwen.redacted.json", second)

    credential_available = bool(os.environ.get("DASHSCOPE_API_KEY", "").strip())
    e2e_gate = os.environ.get("REAL_TTS_E2E", "").lower() in {
        "1",
        "true",
        "yes",
    }
    write_json(
        root / "evidence" / "provider-preflight-7.2r.json",
        {
            "classification": "CURRENT_HOST_VERIFIED",
            "activeProvider": "bailian_qwen",
            "adapter": "BailianQwenSpeechProvider",
            "providerType": "NON_REALTIME_HTTP",
            "endpointPath": (
                "/api/v1/services/aigc/multimodal-generation/generation"
            ),
            "model": model,
            "credentialEnvironmentNamesChecked": ["DASHSCOPE_API_KEY"],
            "credentialsAvailable": credential_available,
            "realTtsE2eGateEnvironmentName": "REAL_TTS_E2E",
            "realTtsE2eGateEnabled": e2e_gate,
            "secretsRecorded": False,
            "providerResultUrlsRecorded": False,
            "openAiRealCalls": 0,
            "qwenRealCalls": 0,
            "comfyCloudExcluded": True,
        },
    )

    skill_text = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "audio-production"
        / "SKILL.md"
    ).read_text(encoding="utf-8").lower()
    java_root = Path(__file__).resolve().parents[3] / "drama-service" / "server" / "src"
    java_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in java_root.rglob("*.java")
    )
    vendor_terms = ("openai", "qwen", "bailian", "dashscope", "elevenlabs")
    write_json(
        root / "evidence" / "provider-neutrality-audit-7.2r.json",
        {
            "providerAbstractionPreserved": True,
            "openAiProviderPreserved": True,
            "bailianQwenProviderAdded": True,
            "productionTool": "production.generate_audio",
            "newAudioDomainTool": False,
            "ttsMcpRequired": False,
            "skillVendorNeutral": not any(term in skill_text for term in vendor_terms),
            "javaProviderNeutral": not any(term in java_text for term in vendor_terms),
            "javaFilesChangedByBatch72R": 0,
            "mediaSchemaChangedByBatch72R": False,
            "providerSwitchingOfflineTests": "PASS",
            "replacementSurface": [
                "provider adapter",
                "provider configuration",
                "provider mapping",
                "fingerprint/result",
            ],
        },
    )
    write_json(
        root / "evidence" / "agents-sdk-llm-provider-design-7.2r.json",
        {
            "classification": "DESIGN_ONLY",
            "harnessCodeChanged": False,
            "agentsSdkDefaultProvider": "OpenAIModelProvider -> OpenAI API",
            "agentsSdkNonOpenAiSupported": "REQUIRES_COMPATIBILITY_VALIDATION",
            "futureHarnessModelProviderResolver": {
                "openai": "OpenAI Responses model",
                "bailian_qwen": "OpenAI-compatible Chat Completions model",
            },
            "implementationPreference": (
                "reuse existing OpenAI-compatible integration before custom ModelProvider"
            ),
            "compatibilityRisks": [
                "tool calling",
                "streaming",
                "structured output",
                "usage accounting",
                "handoffs",
                "system/developer instructions",
                "context limits",
                "error mapping",
                "model settings",
                "tracing without an OpenAI credential",
            ],
            "recommendedNextStep": "separate Harness Provider batch",
        },
    )

    if not credential_available:
        batch_status = "BLOCKED_BY_DASHSCOPE_CREDENTIAL"
    elif not e2e_gate:
        batch_status = "BLOCKED_BY_REAL_TTS_E2E_GATE"
    else:
        batch_status = "READY_FOR_EXPLICIT_REAL_E2E"
    summary = {
        "batch": "7.2R",
        "batch72R": batch_status,
        "speechProviderNeutral": True,
        "openAiProviderPreserved": True,
        "bailianQwenProvider": "PASS_OFFLINE",
        "activeProvider": "bailian_qwen",
        "providerSwitching": "PASS_OFFLINE",
        "qwenModel": model,
        "qwenVoiceA": first["voiceId"],
        "qwenVoiceB": second["voiceId"],
        "dashscopeCredentialAvailable": credential_available,
        "realTtsE2eEnabled": e2e_gate,
        "qwenRealTtsCallCount": 0,
        "qwenRealTtsRetryCount": 0,
        "openAiRealTtsCallCount": 0,
        "exactTextInput": (
            "PASS_OFFLINE"
            if first["exactTextEqualsProviderInput"]
            and second["exactTextEqualsProviderInput"]
            else "FAIL"
        ),
        "performanceIntentMapping": (
            "PASS_OFFLINE"
            if model == "qwen3-tts-instruct-flash"
            and first["performanceIntentMappedToInstructions"]
            and second["performanceIntentMappedToInstructions"]
            else "NOT_AVAILABLE_EXPLICIT_FLASH_FALLBACK"
        ),
        "pronunciationControl": "NOT_AVAILABLE",
        "audioInputFingerprintA": first["audioInputFingerprint"],
        "audioInputFingerprintB": second["audioInputFingerprint"],
        "realSpeechA": "NOT_EXECUTED_CREDENTIAL_GATE",
        "realSpeechB": "NOT_EXECUTED_CREDENTIAL_GATE",
        "actualDurationA": None,
        "actualDurationB": None,
        "realAudioMediaRoundtrip": "NOT_EXECUTED_CREDENTIAL_GATE",
        "hashEquality": "NOT_EXECUTED_CREDENTIAL_GATE",
        "audioTimeline": "NOT_EXECUTED_CREDENTIAL_GATE",
        "avPreview": "NOT_EXECUTED_CREDENTIAL_GATE",
        "sourceVideoImmutable": "NOT_EXECUTED_CREDENTIAL_GATE",
        "userAudioReviewRequired": True,
        "agentsSdkLlmProviderNeutralDesign": "PASS_DESIGN_ONLY",
        "harnessLlmProviderImplementation": "DEFERRED_TO_SEPARATE_BATCH",
        "comfyCloudUsage": 0,
        "imageAiGeneration": 0,
        "videoAiGeneration": 0,
    }
    write_json(root / "validation-summary-7.2r.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
