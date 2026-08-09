from pathlib import Path

import pytest

from drama_plugin.config import load_config


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_default_config_is_mock() -> None:
    config = load_config(environment={})
    assert config.providers.project.mode == "mock"
    assert config.providers.context.mode == "local"


def test_none_environment_reads_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRAMA_PLUGIN_PROVIDER_PROJECT_MODE", "http")
    assert load_config(environment=None).providers.project.mode == "http"


def test_empty_environment_isolated_from_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRAMA_PLUGIN_PROVIDER_PROJECT_MODE", "http")
    assert load_config(environment={}).providers.project.mode == "mock"


def test_yaml_config_and_environment_override() -> None:
    config = load_config(FIXTURES / "config.yaml", {
        "DRAMA_PLUGIN_PROVIDER_PROJECT_MODE": "http",
        "DRAMA_PLUGIN_SERVICE_PROJECT_BASE_URL": "https://env.invalid",
        "DRAMA_PLUGIN_SERVICE_PROJECT_API_TOKEN": "test-only-secret",
    })
    assert config.providers.project.mode == "http"
    assert config.services.project.base_url == "https://env.invalid"
    assert config.services.project.api_token == "test-only-secret"
