import httpx
import pytest

from drama_plugin.config import ServiceConfig
from drama_plugin.exceptions import RemoteServiceError
from drama_plugin.providers.http import HttpProviderClient
from drama_plugin.providers.mock import MockAssetProvider, MockDramaData, MockProjectProvider


@pytest.mark.asyncio
async def test_mock_providers_return_coherent_data() -> None:
    data = MockDramaData()
    project = MockProjectProvider(data)
    asset = MockAssetProvider(data)
    shot = await project.get_shot("shot-1")
    hierarchy = await asset.resolve_asset_hierarchy(scene_id=shot.scene_id, shot_id=shot.id)
    character_asset = next(item for item in hierarchy.effective if item.entity_id == "character-di")
    assert character_asset.effective_asset.id == "asset-di-shot"


@pytest.mark.asyncio
async def test_http_non_2xx_becomes_domain_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(503, json={"error": "offline"}))
    async with httpx.AsyncClient(base_url="https://service.invalid", transport=transport) as client:
        provider = HttpProviderClient(ServiceConfig(base_url="https://service.invalid", operations={"get_project": "/project"}), client)
        with pytest.raises(RemoteServiceError, match="503"):
            await provider.request("get_project")
