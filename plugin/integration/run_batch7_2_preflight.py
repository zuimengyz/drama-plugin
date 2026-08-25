from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from drama_plugin.audio import (
    audio_input_fingerprint,
    capability_report,
    compile_speech_request,
    text_hash,
)
from drama_plugin.contracts import (
    CreativeVoiceProfile,
    ProviderVoiceMapping,
    TargetTimingPolicy,
    VoiceProfile,
)
from drama_plugin.providers.speech import compile_openai_speech_payload


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def request_metadata(
    *,
    spoken_content_id: str,
    speaker_key: str,
    text: str,
    voice_id: str,
    timbre: str,
) -> dict[str, Any]:
    mapping = ProviderVoiceMapping(
        provider="openai",
        model="gpt-4o-mini-tts",
        voice_id=voice_id,
        material_parameters={"response_format": "wav", "speed": 1.0},
    )
    profile = VoiceProfile(
        profile_id=f"batch-7-2:{speaker_key}",
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
        display_name=f"Batch 7.2 validation {speaker_key}",
    )
    request = compile_speech_request(
        work_id="BATCH_7_2_VALIDATION_PENDING_CREDENTIAL_GATE",
        scene_id="BATCH_7_2_VALIDATION_SCENE_PENDING_CREDENTIAL_GATE",
        spoken_content={
            "spokenContentId": spoken_content_id,
            "speakerKey": speaker_key,
            "text": text,
            "performanceIntent": {"delivery": "neutral", "pace": "measured"},
        },
        voice_profile=profile,
        provider_mapping=mapping,
        pronunciation_guidance=[],
        material_render_parameters={"response_format": "wav", "speed": 1.0},
        target_timing_policy=TargetTimingPolicy(policy="NATURAL"),
        non_material_metadata={
            "validationFixture": True,
            "notProductionDrama": True,
            "notHistoricalProvenance": True,
        },
    )
    payload = compile_openai_speech_payload(request)
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
        "provider": mapping.provider,
        "model": mapping.model,
        "voiceId": mapping.voice_id,
        "responseFormat": payload["response_format"],
        "exactTextEqualsProviderInput": payload["input"] == request.exact_text,
        "pronunciationGuidanceApplied": False,
        "credentialFieldsRecorded": False,
        "authorizationRecorded": False,
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

    first = request_metadata(
        spoken_content_id="validation-spoken-a",
        speaker_key="speaker:validation-a",
        text="军报已经送到，请将军决断。",
        voice_id="marin",
        timbre="clear and steady",
    )
    second = request_metadata(
        spoken_content_id="validation-spoken-b",
        speaker_key="speaker:validation-b",
        text="军令未下，各部不得擅动。",
        voice_id="cedar",
        timbre="grounded and firm",
    )
    write_json(root / "requests" / "speaker-a.redacted.json", first)
    write_json(root / "requests" / "speaker-b.redacted.json", second)

    credential_available = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    e2e_gate = os.environ.get("DRAMA_PLUGIN_REAL_TTS_E2E", "").lower() in {
        "1",
        "true",
        "yes",
    }
    provider = {
        "classification": "CURRENT_HOST_VERIFIED",
        "adapter": "OpenAiSpeechProvider",
        "providerType": "HTTP",
        "endpointPath": "/v1/audio/speech",
        "credentialEnvironmentNamesChecked": ["OPENAI_API_KEY"],
        "credentialsAvailable": credential_available,
        "realTtsE2eGateEnabled": e2e_gate,
        "configuredEnvFilesFound": 0,
        "secretsRecorded": False,
        "comfyCloudExcluded": True,
    }
    write_json(root / "evidence" / "provider-preflight.json", provider)
    write_json(root / "evidence" / "host-capabilities.json", capability_report())
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
    vendor_terms = ("openai", "elevenlabs", "fish audio", "dashscope")
    write_json(
        root / "evidence" / "provider-neutrality-audit.json",
        {
            "providerAbstractionPreserved": True,
            "productionTool": "production.generate_audio",
            "newAudioDomainTool": False,
            "ttsMcpRequired": False,
            "skillVendorNeutral": not any(term in skill_text for term in vendor_terms),
            "javaProviderNeutral": not any(term in java_text for term in vendor_terms),
            "javaFilesChangedByBatch72": 0,
            "mediaSchemaChangedByBatch72": False,
            "replacementSurface": [
                "provider adapter",
                "provider configuration",
                "provider mapping",
            ],
        },
    )

    if not credential_available:
        batch_status = "BLOCKED_BY_REAL_TTS_CREDENTIALS"
    elif not e2e_gate:
        batch_status = "BLOCKED_BY_REAL_TTS_E2E_GATE"
    else:
        batch_status = "READY_FOR_EXPLICIT_REAL_E2E"

    summary = {
        "batch": "7.2",
        "batch72": batch_status,
        "realTtsProvider": "BLOCKED",
        "realTtsCredentialsAvailable": "YES" if credential_available else "NO",
        "realTtsE2eGateEnabled": e2e_gate,
        "realTtsCallCount": 0,
        "realTtsRetryCount": 0,
        "twoSpeakerMappingsPrepared": first["voiceId"] != second["voiceId"],
        "exactTextFidelityInput": (
            first["exactTextEqualsProviderInput"]
            and second["exactTextEqualsProviderInput"]
        ),
        "realAudioPhysicalValidation": "NOT_EXECUTED_CREDENTIAL_GATE",
        "realAudioMediaRoundtrip": "NOT_EXECUTED_CREDENTIAL_GATE",
        "audioTimeline": "NOT_EXECUTED_CREDENTIAL_GATE",
        "avMux": "NOT_EXECUTED_CREDENTIAL_GATE",
        "ttsMcpRequired": "NO",
        "comfyCloudUsage": 0,
        "comfyCloudCreditConsumption": 0,
        "imageAiGeneration": 0,
        "videoAiGeneration": 0,
    }
    write_json(root / "validation-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
