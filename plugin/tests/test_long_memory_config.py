from drama_plugin.config.loader import _environment_overrides
from drama_plugin.long_memory.client import DramaArchiveClient


def test_shared_service_connection_keeps_legacy_overrides_and_production_routes() -> None:
    old = {"DRAMA_PLUGIN_SERVICE_MEMORY_BASE_URL":"http://memory.invalid",
           "DRAMA_PLUGIN_SERVICE_MEDIA_BASE_URL":"http://media.invalid",
           "DRAMA_PLUGIN_SERVICE_PRODUCTION_BASE_URL":"http://production.invalid",
           "DRAMA_PLUGIN_SERVICE_RESEARCH_BASE_URL":"http://research.invalid",
           "DRAMA_PLUGIN_VIDEO_MODEL_PREFERRED":"seedance-2-fast",
           "DRAMA_PLUGIN_TEXT_COMPOSITION_BASE_URL":"https://api.deepseek.com"}
    before = _environment_overrides(old)
    after = _environment_overrides({**old,"DRAMA_SERVICE_BASE_URL":"http://shared.invalid","DRAMA_SERVICE_API_TOKEN":"test-token"})
    assert after["services"]["memory"]["base_url"] == before["services"]["memory"]["base_url"]
    assert after["services"]["media"]["base_url"] == before["services"]["media"]["base_url"]
    assert after["services"]["asset"]["base_url"] == "http://shared.invalid"
    assert after["services"]["production"] == before["services"]["production"]
    assert after["services"]["research"] == before["services"]["research"]
    assert after["text_composition"] == before["text_composition"]
    assert after["video_route_policy"] == before["video_route_policy"]


def test_explicit_blank_legacy_key_does_not_fall_back_to_shared_secret() -> None:
    result = _environment_overrides({"DRAMA_SERVICE_API_TOKEN":"test-token","DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN":""})
    assert result["services"]["memory"]["api_token"] is None
    assert result["services"]["asset"]["api_token"] == "test-token"
    assert DramaArchiveClient.from_environment({"DRAMA_SERVICE_BASE_URL":"http://shared.invalid",
        "DRAMA_SERVICE_API_TOKEN":"test-token","DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN":""}) is None


async def test_archive_client_uses_the_same_explicit_domain_precedence() -> None:
    client=DramaArchiveClient.from_environment({"DRAMA_SERVICE_BASE_URL":"http://shared.invalid","DRAMA_SERVICE_API_TOKEN":"shared-test",
        "DRAMA_PLUGIN_SERVICE_MEMORY_BASE_URL":"http://specific.invalid","DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN":"specific-test",
        "DRAMA_PLUGIN_SERVICE_MEMORY_TIMEOUT_SECONDS":"17"})
    assert client is not None
    assert str(client._http.base_url).rstrip("/")=="http://specific.invalid"
    assert client._http.headers["Authorization"]=="Bearer specific-test"
    assert client._http.timeout.read==17
    await client.aclose()
