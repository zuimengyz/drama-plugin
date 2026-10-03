"""An independent single-host content-addressed Media Store and physical QA.

No media bytes, base64 or canonical locator enter ProductionLedger. Atomic
hard-link publication is idempotent across workers, including a crash between
blob retention and the operation checkpoint.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Literal

from drama_plugin.execution.contracts import MediaIdentity, ProbeObservation
from drama_plugin.execution.transport import CapabilityAbsent


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".retain-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != content:
                raise ValueError("Immutable Media/Replay identity conflict")
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


class LocalMediaStore:
    owner = "MEDIA_STORE"

    def __init__(self, directory: Path):
        if not directory.is_absolute():
            raise ValueError("Media Store requires a stable absolute root")
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)

    def retain(self, content: bytes, *, kind: Literal["VIDEO", "AUDIO"],
               mime: Literal["video/mp4", "audio/wav", "audio/mp4"], expected_hash: str | None = None) -> MediaIdentity:
        if not content:
            raise ValueError("Empty provider media")
        digest = hashlib.sha256(content).hexdigest()
        if expected_hash is not None and digest != expected_hash:
            raise ValueError("Provider media hash mismatch")
        identity = MediaIdentity(media_id="media:sha256:" + digest, content_hash=digest,
            kind=kind, mime=mime, byte_count=len(content))
        atomic_write(self.directory / digest, content)
        atomic_write(self.directory / (digest + ".json"), identity.model_dump_json(by_alias=True).encode())
        return identity

    def path(self, media: MediaIdentity) -> Path:
        media = MediaIdentity.model_validate(media.model_dump())
        path = self.directory / media.content_hash
        metadata = MediaIdentity.model_validate_json((self.directory / (media.content_hash + ".json")).read_bytes())
        if metadata != media or path.stat().st_size != media.byte_count:
            raise ValueError("Media Store identity/size mismatch")
        if hashlib.sha256(path.read_bytes()).hexdigest() != media.content_hash:
            raise ValueError("Retained media hash mismatch")
        return path


def probe(path: Path, *, decode: bool = True) -> ProbeObservation:
    if not shutil.which("ffprobe") or (decode and not shutil.which("ffmpeg")):
        raise CapabilityAbsent("MEDIA_PROBE_ABSENT")
    completed = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path)], capture_output=True, check=True, timeout=30)
    payload = json.loads(completed.stdout)
    streams = payload["streams"]
    video = next((s for s in streams if s["codec_type"] == "video"), None)
    audio = next((s for s in streams if s["codec_type"] == "audio"), None)
    observation = ProbeObservation(container=payload["format"]["format_name"],
        duration_ms=round(float(payload["format"]["duration"]) * 1000),
        width=video["width"] if video else None, height=video["height"] if video else None,
        video_codec=video["codec_name"] if video else None, audio_codec=audio["codec_name"] if audio else None)
    if decode:
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-err_detect", "explode",
            "-i", str(path), "-f", "null", "-"], capture_output=True, check=True, timeout=30)
    return observation


def probe_intake_bytes(content: bytes) -> ProbeObservation | None:
    """Probe staging before retention. Unreadable results remain QA evidence.

    Retaining corrupt bytes is quarantine evidence, not a usable production
    result. Technical QA records FAIL and no reviewed candidate can consume it.
    """
    with tempfile.TemporaryDirectory(prefix="target-intake-") as directory:
        staging = Path(directory) / "result"
        staging.write_bytes(content)
        try:
            return probe(staging)
        except (ValueError, KeyError, subprocess.SubprocessError):
            return None


def inspect(store: LocalMediaStore, media: MediaIdentity, *, duration_ms: int,
            tolerance_ms: int, audio_expected: bool, resolution: str | None = None,
            aspect_ratio: str | None = None) -> tuple[ProbeObservation | None, tuple[str, ...]]:
    failures: list[str] = []
    try:
        observation = probe(store.path(media))
    except CapabilityAbsent:
        raise
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return None, ("CORRUPT_OR_UNREADABLE_MEDIA",)
    if abs(observation.duration_ms - duration_ms) > tolerance_ms:
        failures.append("RESULT_DURATION_MISMATCH")
    if media.kind == "VIDEO" and (not observation.video_codec or not observation.width or not observation.height):
        failures.append("RESULT_VIDEO_MISSING")
    if media.kind == "AUDIO" and (not observation.audio_codec or observation.video_codec):
        failures.append("RESULT_AUDIO_INCOMPATIBLE")
    expected_container = "wav" if media.mime == "audio/wav" else "mp4"
    if expected_container not in observation.container.split(","):
        failures.append("RESULT_CONTAINER_MIME_MISMATCH")
    if audio_expected and not observation.audio_codec:
        failures.append("RESULT_AUDIO_MISSING")
    if media.kind == "VIDEO" and observation.width and observation.height:
        if resolution and min(observation.width, observation.height) != int(resolution.removesuffix("p")):
            failures.append("RESULT_RESOLUTION_MISMATCH")
        if aspect_ratio and aspect_ratio != "adaptive":
            w, h = map(int, aspect_ratio.split(":"))
            if abs(observation.width / observation.height - w / h) > 0.01:
                failures.append("RESULT_ASPECT_RATIO_MISMATCH")
    return observation, tuple(failures)
