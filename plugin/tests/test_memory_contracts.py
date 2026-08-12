import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest

from drama_plugin.config import ServiceConfig
from drama_plugin.contracts import AssetType, MediaType
from drama_plugin.providers.http import HttpAssetProvider, HttpMediaProvider, HttpMemoryProvider, HttpProviderClient
from drama_plugin.providers.mock import MockAssetProvider, MockDramaData, MockMediaProvider, MockMemoryProvider

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_mock_save_is_full_replacement_and_preserves_stable_identity() -> None:
    data = MockDramaData()
    memory = MockMemoryProvider(data)
    asset = MockAssetProvider(data)
    media = MockMediaProvider(data)

    script = await memory.save_script("script-1", "修订剧本", {"main_line": "完整新状态"})
    episode = await memory.save_episode("episode-1", 2, "修订分集", {"hook": "新钩子"})
    scene = await memory.save_scene("scene-1", 4, "修订场景", {"characters": ["狄仁杰"]}, "神都·新书房")
    shot = await memory.save_shot("shot-1", "4-03", {"duration_seconds": 5.0}, "抬眼特写", "CLOSE_UP")
    revised_asset = await asset.save_asset("asset-di", "狄仁杰主角色卡", {"visual_identity": "完整新状态"}, reference_media_ids=["media-di"])
    revised_media = await media.save_media("media-di", {"width": 2048}, "MASTER_CHARACTER_CARD")

    assert script.work_id == "work-1"
    assert episode.script_id == "script-1"
    assert scene.episode_id == "episode-1"
    assert shot.scene_id == "scene-1"
    assert (revised_asset.work_id, revised_asset.asset_type) == ("work-1", AssetType.CHARACTER)
    assert (revised_media.work_id, revised_media.source_ref) == ("work-1", "mock:media:di-renjie")
    assert script.content == {"main_line": "完整新状态"}
    assert revised_media.content == {"width": 2048}


@pytest.mark.asyncio
async def test_mock_create_accepts_complete_envelope_and_object_content() -> None:
    data = MockDramaData()
    memory = MockMemoryProvider(data)
    asset = MockAssetProvider(data)
    media = MockMediaProvider(data)

    work = await memory.create_work("新作品", {"premise": "完整初始事实"}, "说明")
    script = await memory.create_script(work.id, "新剧本", {"structure": ["开端", "转折"]})
    episode = await memory.create_episode(script.id, 3, "宫门夜变", {"hook": "宫门将闭"})
    scene = await memory.create_scene(episode.id, 4, "府邸书房", {"characters": ["张柬之"]}, "洛阳·张府")
    shot = await memory.create_shot(scene.id, "4-03", {"framing": "MCU"}, "抬眼特写", "CLOSE_UP")
    created_asset = await asset.create_asset(work.id, AssetType.MASTER_CHARACTER_CARD, "太平公主", {"visual_identity": "正式角色卡"}, scene_id=scene.id)
    created_media = await media.create_media(work.id, MediaType.IMAGE, "opaque:host:media:1", {"semantic_labels": ["太平公主"]}, asset_id=created_asset.id, purpose="MASTER_CHARACTER_CARD")

    assert (episode.episode_no, scene.order, shot.shot_no) == (3, 4, "4-03")
    assert created_asset.content["visual_identity"] == "正式角色卡"
    assert created_media.source_ref == "opaque:host:media:1"


@pytest.mark.asyncio
async def test_http_create_and_save_bindings_send_snake_case_contracts() -> None:
    captured: dict[str, dict[str, Any]] = {}
    responses: dict[str, dict[str, Any]] = {
        "create_work": {"id": "work-new", "title": "W", "content": {}},
        "save_work": {"id": "work-1", "title": "W", "content": {}},
        "create_script": {"id": "script-new", "work_id": "work-1", "title": "S", "content": {}},
        "save_script": {"id": "script-1", "work_id": "work-1", "title": "S", "content": {}},
        "create_episode": {"id": "episode-new", "script_id": "script-1", "episode_no": 3, "title": "E", "content": {}},
        "save_episode": {"id": "episode-1", "script_id": "script-1", "episode_no": 3, "title": "E", "content": {}},
        "create_scene": {"id": "scene-new", "episode_id": "episode-1", "order": 4, "title": "C", "content": {}},
        "save_scene": {"id": "scene-1", "episode_id": "episode-1", "order": 4, "title": "C", "content": {}},
        "create_shot": {"id": "shot-new", "scene_id": "scene-1", "shot_no": "4-03", "content": {}},
        "save_shot": {"id": "shot-1", "scene_id": "scene-1", "shot_no": "4-03", "content": {}},
        "create_asset": {"id": "asset-new", "work_id": "work-1", "asset_type": "PROP", "name": "A", "content": {}},
        "save_asset": {"id": "asset-1", "work_id": "work-1", "asset_type": "PROP", "name": "A", "content": {}},
        "create_media": {"id": "media-new", "work_id": "work-1", "media_type": "IMAGE", "source_ref": "opaque:1", "content": {}},
        "save_media": {"id": "media-1", "work_id": "work-1", "media_type": "IMAGE", "source_ref": "opaque:1", "content": {}},
    }

    def respond(request: httpx.Request) -> httpx.Response:
        operation = request.url.path.removeprefix("/")
        captured[operation] = json.loads(request.content)
        return httpx.Response(200, json=responses[operation])

    operations = {name: f"/{name}" for name in responses}
    async with httpx.AsyncClient(base_url="https://service.invalid", transport=httpx.MockTransport(respond)) as client:
        http = HttpProviderClient(ServiceConfig(base_url="https://service.invalid", operations=operations), client)
        memory = HttpMemoryProvider(http)
        asset = HttpAssetProvider(http)
        media = HttpMediaProvider(http)
        await memory.create_work("W", {})
        await memory.save_work("work-1", "W", {})
        await memory.create_script("work-1", "S", {})
        await memory.save_script("script-1", "S", {})
        await memory.create_episode("script-1", 3, "E", {})
        await memory.save_episode("episode-1", 3, "E", {})
        await memory.create_scene("episode-1", 4, "C", {})
        await memory.save_scene("scene-1", 4, "C", {})
        await memory.create_shot("scene-1", "4-03", {})
        await memory.save_shot("shot-1", "4-03", {})
        await asset.create_asset("work-1", AssetType.PROP, "A", {})
        await asset.save_asset("asset-1", "A", {})
        await media.create_media("work-1", MediaType.IMAGE, "opaque:1", {})
        await media.save_media("media-1", {})

    assert set(captured) == set(responses)
    assert captured["create_episode"]["episode_no"] == 3
    assert captured["create_shot"]["shot_no"] == "4-03"
    assert captured["create_media"]["source_ref"] == "opaque:1"
    assert "work_id" not in captured["save_script"]
    assert "scene_id" not in captured["save_shot"]
    assert "source_ref" not in captured["save_media"]
    assert not any(any(char.isupper() for char in key) for body in captured.values() for key in body)


def test_mysql_schema_freezes_exactly_seven_memory_tables() -> None:
    sql = (ROOT / "docs" / "schema" / "drama-memory-mysql.sql").read_text(encoding="utf-8")
    tables = re.findall(r"CREATE TABLE\s+(drama_\w+)", sql, flags=re.IGNORECASE)
    assert tables == [
        "drama_work",
        "drama_script",
        "drama_episode",
        "drama_scene",
        "drama_shot",
        "drama_asset",
        "drama_media",
    ]
    assert sql.count("content JSON NOT NULL") == 7
    assert len(re.findall(r"^    id VARCHAR\(64\) NOT NULL,$", sql, flags=re.MULTILINE)) == 7
    assert sql.count("version BIGINT UNSIGNED NOT NULL DEFAULT 1") == 7
    assert sql.count("created_at DATETIME(3) NOT NULL") == 7
    assert sql.count("updated_at DATETIME(3) NOT NULL") == 7
    assert "reference_media_ids JSON NOT NULL" in sql
    assert all(f"{field} VARCHAR(64)" in sql for field in ("work_id", "episode_id", "scene_id", "shot_id"))
    assert "BLOB" not in sql.upper()
    assert "FOREIGN KEY" not in sql.upper()
    assert not re.search(r"CREATE TABLE\s+\w*(binding|workflow|generation|entity)", sql, flags=re.IGNORECASE)
