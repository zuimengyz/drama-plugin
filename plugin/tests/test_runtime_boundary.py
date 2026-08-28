from __future__ import annotations

from pathlib import Path

from drama_plugin.config import load_config
from drama_plugin.plugin import DramaPlugin


def test_plugin_composition_and_fish_role_dubbing_config_need_no_storage_env() -> None:
    environment = {
        "DRAMA_PLUGIN_PROVIDER_MEMORY_MODE": "mock",
        "DRAMA_PLUGIN_PROVIDER_ASSET_MODE": "mock",
        "DRAMA_PLUGIN_PROVIDER_RESEARCH_MODE": "mock",
        "DRAMA_PLUGIN_PROVIDER_PRODUCTION_MODE": "mock",
        "DRAMA_PLUGIN_PROVIDER_MEDIA_MODE": "mock",
        "DRAMA_PLUGIN_PROVIDER_CONTEXT_MODE": "local",
        "DRAMA_PLUGIN_PROVIDER_VOICE_MODE": "mock",
        "FISH_AUDIO_API_KEY": "offline-test-key",
        "FISH_TTS_MODEL": "s2-pro",
        "DRAMA_PLUGIN_ROLE_DUBBING_OUTPUT_DIRECTORY": "/tmp/drama-runtime-boundary-test",
    }
    assert not any(name.startswith(("DB_", "MYSQL_", "MINIO_", "S3_", "DRAMA_MEDIA_STORAGE_"))
                   for name in environment)
    config = load_config(environment=environment)
    providers, clients = DramaPlugin._initialize_providers(config)
    assert providers.voice is not None and providers.role_dubbing is not None
    assert clients == []


def test_plugin_active_source_has_no_database_or_storage_configuration_reads() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src" / "drama_plugin"
    source = "\n".join(path.read_text(encoding="utf-8") for path in source_root.rglob("*.py"))
    for forbidden in ("MINIO_", "MYSQL_", "S3_ENDPOINT", "S3_ACCESS", "S3_SECRET",
                      "DRAMA_MEDIA_STORAGE_", "DB_HOST", "DB_PASSWORD"):
        assert forbidden not in source
