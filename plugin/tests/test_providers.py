import httpx
import pytest

from drama_plugin.config import ServiceConfig
from drama_plugin.contracts import AssetType, MediaType
from drama_plugin.exceptions import RemoteServiceError
from drama_plugin.providers.http import HttpProviderClient
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
        with pytest.raises(RemoteServiceError, match="503"):
            await provider.request("get_work")
