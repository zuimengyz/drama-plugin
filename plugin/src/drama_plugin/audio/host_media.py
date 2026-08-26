from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from drama_plugin.contracts.media import MediaType


class AvAssemblyCapabilityMissing(RuntimeError):
    pass


@dataclass(frozen=True)
class MediaProbe:
    duration_ms: int
    streams: tuple[dict[str, Any], ...]
    implementation: str
    version: str


def validate_media_mime(media_type: MediaType, purpose: str | None, mime_type: str) -> None:
    if media_type is MediaType.AUDIO and not mime_type.startswith("audio/"):
        raise ValueError("AUDIO media requires an audio/* MIME type")
    if purpose == "FINAL_AV" and (
        media_type is not MediaType.VIDEO or not mime_type.startswith("video/")
    ):
        raise ValueError("FINAL_AV requires VIDEO media with a video/* MIME type")


def _version(binary: str) -> str:
    completed = subprocess.run(
        [binary, "-version"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.splitlines()[0]


def capability_report() -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    return {
        "status": "READY" if ffmpeg and ffprobe else "AV_ASSEMBLY_CAPABILITY_MISSING",
        "ffmpeg": {"path": ffmpeg, "version": _version(ffmpeg)} if ffmpeg else None,
        "ffprobe": {"path": ffprobe, "version": _version(ffprobe)} if ffprobe else None,
    }


def probe_wav_duration_ms(path: Path | str) -> int:
    with wave.open(str(path), "rb") as fixture:
        frames = fixture.getnframes()
        rate = fixture.getframerate()
    if frames <= 0 or rate <= 0:
        raise ValueError("WAV has no measurable positive duration")
    return round(frames * 1000 / rate)


def probe_media(path: Path | str) -> MediaProbe:
    binary = shutil.which("ffprobe")
    if binary is None:
        raise AvAssemblyCapabilityMissing("AV_ASSEMBLY_CAPABILITY_MISSING: ffprobe not found")
    completed = subprocess.run(
        [
            binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,duration,channels,sample_rate",
            "-of",
            "json",
            str(Path(path)),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    duration_ms = round(float(payload["format"]["duration"]) * 1000)
    if duration_ms <= 0:
        raise ValueError("probed duration must be positive")
    return MediaProbe(
        duration_ms=duration_ms,
        streams=tuple(payload.get("streams", [])),
        implementation="ffprobe",
        version=_version(binary),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mux_video_and_audio(
    source_video: Path | str,
    audio: Path | str,
    output: Path | str,
) -> dict[str, Any]:
    source_path = Path(source_video).resolve()
    audio_path = Path(audio).resolve()
    output_path = Path(output).resolve()
    if output_path in (source_path, audio_path):
        raise ValueError("mux output must be a new path; source inputs are immutable")
    binary = shutil.which("ffmpeg")
    if binary is None:
        raise AvAssemblyCapabilityMissing("AV_ASSEMBLY_CAPABILITY_MISSING: ffmpeg not found")
    source_hash = _sha256(source_path)
    settings = [
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        "-movflags",
        "+faststart",
    ]
    subprocess.run(
        [binary, "-nostdin", "-y", "-i", str(source_path), "-i", str(audio_path), *settings, str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    if _sha256(source_path) != source_hash:
        raise RuntimeError("source video changed during mux")
    result_probe = probe_media(output_path)
    stream_types = {stream.get("codec_type") for stream in result_probe.streams}
    if not {"video", "audio"}.issubset(stream_types):
        raise RuntimeError("mux output must contain video and audio streams")
    return {
        "implementation": "ffmpeg",
        "version": _version(binary),
        "settings": settings,
        "durationMs": result_probe.duration_ms,
        "sourceVideoHash": source_hash,
        "audioHash": _sha256(audio_path),
        "outputHash": _sha256(output_path),
        "sourceVideoImmutable": True,
    }
