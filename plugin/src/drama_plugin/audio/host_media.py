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
from drama_plugin.contracts.audio import AvAssemblyManifest


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
        declared_frames = fixture.getnframes()
        rate = fixture.getframerate()
        frame_size = fixture.getnchannels() * fixture.getsampwidth()
        raw = fixture.readframes(declared_frames)
    frames = len(raw) // frame_size if frame_size > 0 else 0
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


def assemble_reviewed_native_mix(
    source_video: Path | str, output_audio: Path | str, *,
    strategy: dict[str, Any], placements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Local complete mix before V1 mux. No provider calls or automatic source policy.

    PCM outside declared edits/placements remains identical to the decoded source.
    Pending preservation is allowed; destructive windows require a reviewed finding.
    This helper does not separate voices, infer clean ambience, or accept performances.
    """
    from array import array
    import math
    import tempfile

    source = Path(source_video).resolve()
    output = Path(output_audio).resolve()
    inputs = [source, *(Path(item["path"]).resolve() for item in placements)]
    if output in inputs or output.exists():
        raise ValueError("mix output must be a new path; inputs are immutable")
    mode = strategy.get("mode")
    if mode not in {"PRESERVE", "MIX", "LOCAL_REPLACE"}:
        raise ValueError("explicit native source strategy required; no automatic mute")
    if not strategy.get("evidenceRef"):
        raise ValueError("source strategy requires review evidence")
    if mode == "PRESERVE" and placements:
        raise ValueError("preserved native dialogue cannot also receive TTS")
    windows = strategy.get("replaceWindows", [])
    if windows and (mode != "LOCAL_REPLACE" or strategy.get("reviewStatus") != "PASS"):
        raise ValueError("local replacement requires reviewed, localized findings")
    binary = shutil.which("ffmpeg")
    if binary is None:
        raise AvAssemblyCapabilityMissing("AV_ASSEMBLY_CAPABILITY_MISSING")
    before = {str(path): _sha256(path) for path in inputs}
    duration = probe_media(source).duration_ms
    rate, channels = 48000, 2
    length = round(duration * rate / 1000) * channels

    def decode(path: Path, target: Path) -> array[int]:
        subprocess.run([binary, "-nostdin", "-v", "error", "-i", str(path),
                        "-map", "0:a:0", "-ar", str(rate), "-ac", str(channels),
                        "-f", "s16le", str(target)], check=True, capture_output=True)
        data: array[int] = array("h")
        data.frombytes(target.read_bytes())
        return data

    with tempfile.TemporaryDirectory(prefix="drama-native-mix-") as directory:
        temp = Path(directory)
        native = decode(source, temp / "native.pcm")
        native = native[:length]
        native.extend([0] * (length - len(native)))
        mixed = [float(sample) for sample in native]
        declared: list[tuple[float, float]] = []
        for window in windows:
            start, end = float(window["startMs"]), float(window["endMs"])
            if not 0 <= start < end <= duration or not window.get("finding"):
                raise ValueError("replacement window requires bounded finding")
            if any(start < b and end > a for a, b in declared):
                raise ValueError("replacement windows overlap")
            # Explicit silence is only a local candidate operation. No fake separation.
            lo, hi = round(start * rate / 1000) * channels, round(end * rate / 1000) * channels
            mixed[lo:hi] = [0.0] * (hi - lo)
            declared.append((start, end))
        line_ids: set[str] = set()
        hashes: set[str] = set()
        native_lines = set(strategy.get("nativeLineIds", []))
        placement_records = []
        for index, item in enumerate(placements):
            path = Path(item["path"]).resolve()
            digest = before[str(path)]
            line_id = str(item["sourceLineId"])
            if (line_id in line_ids or line_id in native_lines or digest in hashes
                    or digest == before[str(source)]):
                raise ValueError("duplicate dialogue or native bed")
            if item.get("kind") != "DIALOGUE" or not item.get("performanceFingerprint"):
                raise ValueError("placement must bind one active performance; no extra ambience bed")
            line_ids.add(line_id)
            hashes.add(digest)
            speech = decode(path, temp / f"speech-{index}.pcm")
            start = float(item["startMs"])
            end = start + len(speech) / channels / rate * 1000
            if not math.isfinite(start) or start < 0 or end > duration:
                raise ValueError("complete target speech does not fit; truncation is prohibited")
            for region in strategy.get("dialogueRegions", []):
                if start < region["endMs"] and end > region["startMs"]:
                    if region["kind"] in {"DIALOGUE", "UNCERTAIN_DIALOGUE"} and not any(
                        a <= region["startMs"] and b >= region["endMs"] for a, b in declared
                    ):
                        raise ValueError("native dialogue conflict must be removed, not ducked")
            gain_db = float(item.get("gainDb", 0))
            if not math.isfinite(gain_db):
                raise ValueError("gain must be finite")
            gain = 10 ** (gain_db / 20)
            offset = round(start * rate / 1000) * channels
            for position, sample in enumerate(speech):
                mixed[offset + position] += sample * gain
            placement_records.append({**item, "path": str(path), "audioHash": digest,
                                      "endMs": end, "measuredDurationMs": end - start})
        peak = max(abs(sample) for sample in mixed)
        if peak > 32767:
            raise ValueError("mix clips; review local levels instead of automatic normalization")
        pcm: array[int] = array("h", (round(sample) for sample in mixed))
        with wave.open(str(output), "wb") as wav:
            wav.setparams((channels, 2, rate, 0, "NONE", "not compressed"))
            wav.writeframes(pcm.tobytes())
    if any(_sha256(Path(path)) != digest for path, digest in before.items()):
        raise RuntimeError("audio source changed during mix")
    material = {"implementation": "host-native-mix-v1", "ffmpegVersion": _version(binary),
                "sourceVideoHash": before[str(source)], "strategy": strategy,
                "placements": placement_records, "sampleRate": rate, "channels": channels,
                "durationMs": duration, "audioHash": _sha256(output), "sourceInputsImmutable": True}
    from drama_plugin.contracts.base import sha256_canonical
    # Location and review prose are evidence, not acoustic cache dependencies.
    fingerprint_material = {
        **material,
        "strategy": {key: strategy.get(key) for key in
                     ("mode", "replaceWindows", "nativeLineIds", "dialogueRegions")},
        "placements": [{key: value for key, value in item.items() if key != "path"}
                       for item in placement_records],
    }
    material["mixFingerprint"] = sha256_canonical(fingerprint_material)
    return material


def assemble_av(
    source_video: Path | str, *, manifest: "AvAssemblyManifest",
    source_video_hash: str, audio_mix: Path | str | None = None,
    audio_mix_hash: str | None = None, output: Path | str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Consume the caller's chosen source before any optional audio processing.

    An empty external-audio manifest is a completed reuse operation: return the
    original file, without generating a new Media, mix, or MP4. An explicit mix
    retains V1 replacement semantics. This is physical assembly, not artistic QC.
    """
    from drama_plugin.contracts.base import dump_contract, sha256_canonical

    source = Path(source_video).resolve()
    if _sha256(source) != source_video_hash:
        raise ValueError("selected source video hash mismatch; do not choose another take")
    probe = probe_media(source)
    kinds = {stream.get("codec_type") for stream in probe.streams}
    if "video" not in kinds:
        raise ValueError("selected source must contain video")
    native = manifest.audio_mix_media_id is None and not manifest.speech_clip_media_ids
    inputs = {"manifest": dump_contract(manifest), "sourceVideoHash": source_video_hash}
    if native:
        if manifest.timeline or audio_mix is not None or audio_mix_hash is not None:
            raise ValueError("source AV reuse cannot also add external dialogue or a mix")
        return {
            "operation": "REUSE_SOURCE_AV", "status": "READY", "path": str(source),
            "videoSourcePath": str(source),
            "audioSourcePath": str(source) if "audio" in kinds else None,
            "sourceVideoMediaId": manifest.source_video_media_id,
            "sourceVideoHash": source_video_hash, "durationMs": probe.duration_ms,
            "assemblyFingerprint": sha256_canonical(inputs),
            "audioProcessing": [], "createdMedia": False, "dryRun": dry_run,
            "independentArtisticReview": "NOT_VERIFIED",
        }
    if manifest.audio_mix_media_id is None or audio_mix is None or audio_mix_hash is None:
        raise ValueError("external audio assembly requires a declared complete mix and hash")
    mix = Path(audio_mix).resolve()
    if _sha256(mix) != audio_mix_hash:
        raise ValueError("selected mix hash mismatch")
    if "audio" not in {stream.get("codec_type") for stream in probe_media(mix).streams}:
        raise ValueError("selected mix must contain audio")
    if output is None:
        raise ValueError("explicit replacement requires a new output path")
    if Path(output).resolve() in (source, mix):
        raise ValueError("output must be a new path")
    material = {**inputs, "audioMixHash": audio_mix_hash}
    result = {
        "operation": "REPLACE_WITH_COMPLETE_MIX", "path": str(Path(output).resolve()),
        "assemblyFingerprint": sha256_canonical(material), "dryRun": dry_run,
        "independentArtisticReview": "NOT_VERIFIED",
    }
    if dry_run:
        return {**result, "status": "READY_FOR_EXPLICIT_ASSEMBLY", "createdMedia": False}
    return {**result, "status": "ASSEMBLED", "mux": mux_video_and_audio(source, mix, output)}
