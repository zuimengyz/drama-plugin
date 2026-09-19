"""Provider-neutral audio observation boundary; no story or expected-answer input."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from drama_plugin.contracts.adaptive_direction import AudioSemanticObservation


@dataclass(frozen=True)
class AudioSemanticInput:
    audio_path: Path
    source_media_hash: str
    source_audio_hash: str
    source_start: float
    source_end: float
    media_duration: float


@dataclass(frozen=True)
class AudioSemanticResult:
    observation: AudioSemanticObservation | None
    receipt: dict[str, Any]
    raw_text: str
    status: str


class AudioSemanticProvider(Protocol):
    async def observe_audio(self, source: AudioSemanticInput) -> AudioSemanticResult: ...
    async def aclose(self) -> None: ...
