import httpx
import pytest

from drama_plugin.config import ServiceConfig
from drama_plugin.contracts import AssetType, MediaType
from drama_plugin.exceptions import RemoteServiceError
from drama_plugin.providers.http import HttpMemoryProvider, HttpProviderClient
from drama_plugin.providers.mock import MockAssetProvider, MockDramaData, MockMemoryProvider, MockProductionProvider


@pytest.mark.asyncio
async def test_mock_memory_asset_and_production_are_coherent() -> None:
    data = MockDramaData()
    memory = MockMemoryProvider(data)
    asset = MockAssetProvider(data)
    production = MockProductionProvider(data)
    shot = await memory.get_shot("shot-1")
    assert shot.scene_id == "scene-1"
    assert (await asset.search_assets("狄仁杰", AssetType.CHARACTER))[0].id == "asset-di"
    media = await production.generate_image("标准人物正视图", ["asset-di"])
    assert media.media_type is MediaType.IMAGE


@pytest.mark.asyncio
async def test_mock_memory_can_recover_context_without_stable_ids() -> None:
    memory = MockMemoryProvider(MockDramaData())
    work = (await memory.search_works("神都"))[0]
    script = (await memory.list_scripts(work.id))[0]
    episode = (await memory.list_episodes(script.id, episode_no=1))[0]
    scene = (await memory.search_scenes("残缺密诏", episode_id=episode.id))[0]
    shot = (await memory.search_shots("闪电", scene_id=scene.id))[0]
    assert (work.id, script.id, episode.id, scene.id, shot.id) == ("work-1", "script-1", "episode-1", "scene-1", "shot-1")


@pytest.mark.asyncio
async def test_http_non_2xx_becomes_domain_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(503, json={"error": "offline"}))
    async with httpx.AsyncClient(base_url="https://service.invalid", transport=transport) as client:
        provider = HttpProviderClient(ServiceConfig(base_url="https://service.invalid", operations={"get_work": "/work"}), client)
        with pytest.raises(RemoteServiceError, match="503") as captured:
            await provider.request("get_work")
        assert captured.value.status_code == 503


@pytest.mark.asyncio
async def test_http_preserves_remote_status_and_safe_error_code() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(409, json={"code": "CONFLICT", "message": "safe"}))
    async with httpx.AsyncClient(base_url="https://service.invalid", transport=transport) as client:
        provider = HttpProviderClient(ServiceConfig(base_url="https://service.invalid", operations={"create_media": "/media"}), client)
        with pytest.raises(RemoteServiceError) as captured:
            await provider.request("create_media", method="POST", json={})
    assert captured.value.status_code == 409
    assert captured.value.error_code == "CONFLICT"
    assert "safe" not in str(captured.value)


@pytest.mark.asyncio
async def test_http_maps_java_numeric_error_code() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(404, json={"code": 40400, "message": "not exposed"}))
    async with httpx.AsyncClient(base_url="https://service.invalid", transport=transport) as client:
        provider = HttpProviderClient(ServiceConfig(base_url="https://service.invalid", operations={"get_scene": "/scene"}), client)
        with pytest.raises(RemoteServiceError) as captured:
            await provider.request("get_scene")
    assert captured.value.status_code == 404
    assert captured.value.error_code == "NOT_FOUND"
    assert "not exposed" not in str(captured.value)


@pytest.mark.asyncio
async def test_http_uses_bearer_token_and_joins_relative_path_without_leaking_secret() -> None:
    seen: list[httpx.Request] = []
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})
    config = ServiceConfig(
        base_url="http://127.0.0.1:8080",
        api_token="test-secret-must-not-leak",
        operations={"probe": "/api/tool/probe"},
    )
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url=config.base_url, headers={"Authorization": f"Bearer {config.api_token}"}, transport=transport) as client:
        provider = HttpProviderClient(config, client)
        assert await provider.request("probe") == {"ok": True}
    assert str(seen[0].url) == "http://127.0.0.1:8080/api/tool/probe"
    assert seen[0].headers["Authorization"] == "Bearer test-secret-must-not-leak"
    assert "test-secret-must-not-leak" not in repr(config)


@pytest.mark.asyncio
async def test_http_list_shots_omits_absent_filters_and_returns_all_scene_shots() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[
            {"id": "shot-1", "sceneId": "scene-1", "shotNo": "1", "content": {}},
            {"id": "shot-2", "sceneId": "scene-1", "shotNo": "2", "content": {}},
        ])

    config = ServiceConfig(
        base_url="http://127.0.0.1:8080",
        operations={"list_shots": "/api/tool/shot/list"},
    )
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url=config.base_url, transport=transport) as client:
        provider = HttpMemoryProvider(HttpProviderClient(config, client))
        shots = await provider.list_shots("scene-1")

    assert [shot.id for shot in shots] == ["shot-1", "shot-2"]
    assert dict(seen[0].url.params) == {"scene_id": "scene-1"}
