from __future__ import annotations

from pathlib import Path
from typing import Literal, TypeAlias

from drama_plugin.config.models import SpeechServiceConfig
from drama_plugin.exceptions import ConfigurationError
from drama_plugin.providers.speech.bailian_qwen import BailianQwenSpeechProvider
from drama_plugin.providers.speech.openai import OpenAiSpeechProvider


SpeechProviderMode: TypeAlias = Literal["openai", "bailian_qwen"]
ResolvedSpeechProvider: TypeAlias = OpenAiSpeechProvider | BailianQwenSpeechProvider


def resolve_speech_provider(
    mode: SpeechProviderMode,
    config: SpeechServiceConfig,
    output_directory: Path,
) -> ResolvedSpeechProvider:
    """Select one configured provider. Resolution never performs fallback."""

    if not str(output_directory).strip():
        raise ConfigurationError("Speech provider requires an output directory")
    if mode == "openai":
        if config.api_key is None or not config.api_key.get_secret_value().strip():
            raise ConfigurationError("OpenAI speech provider credential is missing")
        return OpenAiSpeechProvider(config, output_directory)
    if mode == "bailian_qwen":
        if (
            config.dashscope_api_key is None
            or not config.dashscope_api_key.get_secret_value().strip()
        ):
            raise ConfigurationError("Bailian Qwen speech provider credential is missing")
        return BailianQwenSpeechProvider(config, output_directory)
    raise ConfigurationError(f"Unsupported speech provider mode: {mode}")
