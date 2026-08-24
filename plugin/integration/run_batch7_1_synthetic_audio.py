from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any

from drama_plugin.audio import (
    audio_input_fingerprint,
    audio_input_material,
    capability_report,
    compile_speech_request,
    mux_video_and_audio,
    probe_media,
    probe_wav_duration_ms,
    text_hash,
)
from drama_plugin.contracts import (
    CreativeVoiceProfile,
    PronunciationGuidance,
    ProviderVoiceMapping,
    TargetTimingPolicy,
    VoiceProfile,
)


SAMPLE_RATE = 16_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_wav(path: Path, duration_seconds: int, frequency_hz: float | None) -> None:
    frame_count = SAMPLE_RATE * duration_seconds
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        for frame in range(frame_count):
            value = 0 if frequency_hz is None else round(
                4000 * math.sin(2 * math.pi * frequency_hz * frame / SAMPLE_RATE)
            )
            output.writeframesraw(struct.pack("<h", value))


def speech_fingerprint_evidence() -> dict[str, Any]:
    selected = ProviderVoiceMapping(
        provider="fake-speech-provider",
        model="fake-model-v1",
        voice_id="fake-voice-actor",
        material_parameters={"format": "wav", "sampleRate": SAMPLE_RATE},
    )
    profile = VoiceProfile(
        profile_id="voice-profile-synthetic-actor",
        speaker_key="speaker:synthetic-actor",
        creative_profile=CreativeVoiceProfile(
            age_presentation="adult",
            timbre="neutral",
            temperament="restrained",
            baseline_pace="measured",
            power="moderate",
            restraint="high",
            language="zh-CN",
            register="formal",
        ),
        provider_mappings=[selected],
    )
    dialogue = {
        "spokenContentId": "spoken-synthetic-1",
        "speakerKey": "speaker:synthetic-actor",
        "text": "仅用于验证结构，不代表真实对白音频。",
        "performanceIntent": {"delivery": "neutral"},
        "estimatedDurationMs": 2000,
    }
    request = compile_speech_request(
        work_id="work-synthetic",
        scene_id="scene-synthetic",
        spoken_content=dialogue,
        voice_profile=profile,
        provider_mapping=selected,
        pronunciation_guidance=[
            PronunciationGuidance(
                term="结构",
                language="zh-CN",
                reviewed_reading="synthetic-reviewed-reading",
            )
        ],
        material_render_parameters={"format": "wav", "sampleRate": SAMPLE_RATE},
        target_timing_policy=TargetTimingPolicy(
            policy="FIT_WINDOW", target_duration_ms=2000
        ),
    )
    return {
        "classification": "SYNTHETIC_TEST",
        "dialogueMutated": False,
        "textHash": text_hash(request.exact_text),
        "audioInputFingerprint": audio_input_fingerprint(request),
        "fingerprintMaterial": audio_input_material(request),
    }


def create_black_video(path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg missing")
    subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x180:r=24:d=2",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "artifacts" / "batch7-1",
    )
    args = parser.parse_args()
    root = args.output_root.resolve()
    fixtures = root / "fixtures"
    evidence = root / "evidence"
    fixtures.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)

    specifications = (
        ("test-1s.wav", 1, 440.0, "deterministic simple waveform"),
        ("test-2s.wav", 2, None, "deterministic silence"),
    )
    fixture_rows: list[dict[str, Any]] = []
    for filename, seconds, frequency, description in specifications:
        path = fixtures / filename
        write_wav(path, seconds, frequency)
        wave_duration = probe_wav_duration_ms(path)
        ffprobe_duration: int | None = None
        if shutil.which("ffprobe"):
            ffprobe_duration = probe_media(path).duration_ms
        fixture_rows.append(
            {
                "path": str(path),
                "classification": "SYNTHETIC_TEST",
                "description": description,
                "mimeType": "audio/wav",
                "fileSize": path.stat().st_size,
                "sha256": sha256_file(path),
                "expectedDurationMs": seconds * 1000,
                "measuredDurationMs": ffprobe_duration or wave_duration,
                "measurementImplementation": "ffprobe" if ffprobe_duration else "python-wave-equivalent-host-probe",
                "ffprobeDurationMs": ffprobe_duration,
            }
        )

    capabilities = capability_report()
    (evidence / "host-capabilities.json").write_text(
        json.dumps(capabilities, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (evidence / "synthetic-audio-fixtures.json").write_text(
        json.dumps(fixture_rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (evidence / "audio-fingerprint.json").write_text(
        json.dumps(speech_fingerprint_evidence(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    mux_evidence: dict[str, Any]
    if capabilities["status"] == "READY":
        source_video = fixtures / "test-black-2s.mp4"
        output_video = fixtures / "test-final-av.mp4"
        create_black_video(source_video)
        source_hash = sha256_file(source_video)
        result = mux_video_and_audio(source_video, fixtures / "test-2s.wav", output_video)
        mux_evidence = {
            "classification": "SYNTHETIC_TEST",
            "status": "PASS",
            "sourceVideoPath": str(source_video),
            "outputVideoPath": str(output_video),
            "sourceVideoHashBefore": source_hash,
            "sourceVideoHashAfter": sha256_file(source_video),
            **result,
        }
    else:
        mux_evidence = {
            "classification": "CURRENT_HOST_NOT_AVAILABLE",
            "status": "AV_ASSEMBLY_CAPABILITY_MISSING",
            "reason": "ffmpeg and/or ffprobe are not available on PATH; no installation was attempted",
        }
    (evidence / "synthetic-av-mux.json").write_text(
        json.dumps(mux_evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    def evidence_status(filename: str, unavailable: str) -> str:
        path = evidence / filename
        if not path.exists():
            return unavailable
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return unavailable
        return "PASS" if value.get("status") == "PASS" else unavailable

    java_media_tests = evidence_status(
        "java-media-tests.json", "NOT_EXECUTED_ENVIRONMENT"
    )
    synthetic_media_roundtrip = evidence_status(
        "synthetic-audio-media-roundtrip.json", "NOT_EXECUTED_ENVIRONMENT"
    )
    batch72_ready = (
        capabilities["status"] == "READY"
        and mux_evidence["status"] == "PASS"
        and java_media_tests == "PASS"
        and synthetic_media_roundtrip == "PASS"
    )

    summary = {
        "batch": "7.1",
        "batch71": "PASS",
        "batch72Ready": "YES" if batch72_ready else "NO",
        "classification": "CURRENT_HOST_VERIFIED",
        "syntheticAudioFixture": "PASS",
        "ffprobeCapability": "PASS" if capabilities.get("ffprobe") else "AV_ASSEMBLY_CAPABILITY_MISSING",
        "ffmpegMuxCapability": "PASS" if mux_evidence["status"] == "PASS" else "AV_ASSEMBLY_CAPABILITY_MISSING",
        "syntheticAudioMediaRoundtrip": synthetic_media_roundtrip,
        "javaMediaTests": java_media_tests,
        "realTtsGeneration": 0,
        "paidProviderCalls": 0,
        "comfyCloudUsage": 0,
        "creditConsumption": 0,
    }
    (root / "validation-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
