from pathlib import Path

import yaml

from drama_plugin import DramaPlugin
from drama_plugin.config import load_config


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "drama-service-http.example.yaml"
SERVICE_MAPPING = ROOT.parents[1] / "drama-service" / "docs" / "plugin-http-operations.yaml"

POST_OPERATIONS = {
    "create_work", "save_work", "create_script", "save_script",
    "create_episode", "save_episode", "create_scene", "save_scene",
    "create_shot", "save_shot", "create_asset", "save_asset",
    "create_media", "save_media",
}


def _configured_operations() -> dict[str, str]:
    payload = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for domain in ("memory", "asset", "media"):
        result.update(payload["services"][domain]["operations"])
    return result


def test_32_memory_operations_match_service_mapping_when_sibling_is_available() -> None:
    configured = _configured_operations()
    assert len(configured) == 32
    plugin = DramaPlugin.load(ROOT)
    expected_codes = {
        tool.code for tool in plugin.tools.list()
        if tool.domain in {"work", "script", "episode", "scene", "shot", "asset", "media"}
    }
    assert {code.split(".", 1)[1] for code in expected_codes} == set(configured)
    assert all(path.startswith("/api/tool/") and not path.startswith("http") for path in configured.values())
    assert len(POST_OPERATIONS) == 14
    if SERVICE_MAPPING.exists():
        service_operations = yaml.safe_load(SERVICE_MAPPING.read_text(encoding="utf-8"))["operations"]
        assert configured == service_operations


def test_real_http_example_routes_only_memory_asset_media_to_java() -> None:
    config = load_config(CONFIG, {
        "DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN": "test-only",
        "DRAMA_PLUGIN_SERVICE_ASSET_API_TOKEN": "test-only",
        "DRAMA_PLUGIN_SERVICE_MEDIA_API_TOKEN": "test-only",
    })
    assert config.providers.memory.mode == "http"
    assert config.providers.asset.mode == "http"
    assert config.providers.media.mode == "http"
    assert config.providers.research.mode == "mock"
    assert config.providers.production.mode == "mock"
    assert config.providers.context.mode == "local"
