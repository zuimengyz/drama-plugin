"""Explicit real-process Drama Plugin -> Drama Service E2E.

Prerequisites: a running Drama Service, a MySQL-backed local profile, and the
three API token environment variables. This file is intentionally outside the
normal pytest suite.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

from drama_plugin import DramaPlugin
from drama_plugin.contracts import AssetType, MediaType
from drama_plugin.exceptions import ConfigurationError, RemoteServiceError


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "drama-service-http.example.yaml"
TOKEN_KEYS = (
    "DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN",
    "DRAMA_PLUGIN_SERVICE_ASSET_API_TOKEN",
    "DRAMA_PLUGIN_SERVICE_MEDIA_API_TOKEN",
)


def _public(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, list):
        return [_public(item) for item in value]
    return value


async def _invoke(plugin: DramaPlugin, code: str, **arguments: Any) -> Any:
    return await plugin.tools.invoke(code, **arguments)


async def run() -> None:
    if any(not os.environ.get(key, "").strip() for key in TOKEN_KEYS):
        raise SystemExit("CONFIG: set all three DRAMA_PLUGIN_SERVICE_*_API_TOKEN values")

    family = os.environ.get("DRAMA_E2E_PREFIX_FAMILY", "E2E_B02_")
    if family not in {"E2E_B02_", "E2E_B021_"}:
        raise SystemExit("CONFIG: unsupported E2E prefix family")
    suffix = uuid.uuid4().hex[:10]
    prefix = f"{family}{suffix}"
    source_ref = f"{family.rstrip('_')}:{suffix}:standard-face"
    smoke: set[str] = set()

    async with DramaPlugin.load(ROOT, CONFIG) as plugin:
        async def call(code: str, **arguments: Any) -> Any:
            result = await _invoke(plugin, code, **arguments)
            smoke.add(code)
            return result

        # E2E-001 and the complete Work -> Shot tree.
        work = await call("work.create_work", title=f"{prefix}_神龙政变", description=f"{prefix}_候选", content={"theme": prefix})
        script = await call("script.create_script", work_id=work.id, title=f"{prefix}_剧本", content={"format": "short"})
        episode = await call("episode.create_episode", script_id=script.id, episode_no=1, title=f"{prefix}_第一集", content={"arc": prefix})
        scene = await call("scene.create_scene", episode_id=episode.id, order=3, title=f"{prefix}_张柬之书房", location=f"{prefix}_洛阳", content={"character": "张柬之"})
        shot = await call("shot.create_shot", scene_id=scene.id, shot_no="3A", title=f"{prefix}_密议特写", shot_type="CU", content={"character": "张柬之"})

        # All get/list/search query paths.
        assert (await call("work.get_work", work_id=work.id)).id == work.id
        assert (await call("script.get_script", script_id=script.id)).work_id == work.id
        assert (await call("episode.get_episode", episode_id=episode.id)).script_id == script.id
        before_scene = await call("scene.get_scene", scene_id=scene.id)
        assert (await call("shot.get_shot", shot_id=shot.id)).scene_id == scene.id
        assert [item.id for item in await call("work.list_works")] and work.id in [item.id for item in await call("work.search_works", query=prefix)]
        assert script.id in [item.id for item in await call("script.list_scripts", work_id=work.id)]
        assert episode.id in [item.id for item in await call("episode.list_episodes", script_id=script.id, episode_no=1, title="第一集")]
        assert scene.id in [item.id for item in await call("scene.list_scenes", episode_id=episode.id, order=3, location="洛阳", character="张柬之")]
        assert scene.id in [item.id for item in await call("scene.search_scenes", query="书房", episode_id=episode.id)]
        assert shot.id in [item.id for item in await call("shot.list_shots", scene_id=scene.id, shot_no="3A", shot_type="CU", character="张柬之")]
        assert shot.id in [item.id for item in await call("shot.search_shots", query="密议", scene_id=scene.id)]

        # Exercise every save. Stable parent IDs must remain unchanged.
        work = await call("work.save_work", work_id=work.id, title=f"{prefix}_神龙政变修订", description=f"{prefix}_候选", content={"revision": 2})
        script = await call("script.save_script", script_id=script.id, title=f"{prefix}_剧本修订", content={"revision": 2})
        episode = await call("episode.save_episode", episode_id=episode.id, episode_no=1, title=f"{prefix}_第一集修订", content={"revision": 2})
        scene = await call("scene.save_scene", scene_id=scene.id, order=3, title=f"{prefix}_书房修订", location=f"{prefix}_洛阳", content={"revision": 2})
        shot = await call("shot.save_shot", shot_id=shot.id, shot_no="3A", title=f"{prefix}_密议修订", shot_type="CU", content={"revision": 2})
        assert scene.episode_id == before_scene.episode_id

        # Asset A1 -> Media M1 -> Asset A2 semantic reference.
        a1 = await call("asset.create_asset", work_id=work.id, asset_type=AssetType.STANDARD_FACE, name=f"{prefix}_A1标准脸", content={"identity": prefix})
        m1 = await call("media.create_media", work_id=work.id, asset_id=a1.id, media_type=MediaType.IMAGE, source_ref=source_ref, content={"kind": "face"})
        a2 = await call("asset.create_asset", work_id=work.id, asset_type=AssetType.MASTER_CHARACTER_CARD, name=f"{prefix}_A2人物卡", reference_media_ids=[m1.id], content={"identity": prefix})
        assert (await call("asset.get_asset", asset_id=a2.id)).reference_media_ids == [m1.id]
        assert (await call("media.get_media", media_id=m1.id)).asset_id == a1.id != a2.id
        assert a2.id in [item.id for item in await call("asset.list_assets", asset_type=AssetType.MASTER_CHARACTER_CARD)]
        assert a2.id in [item.id for item in await call("asset.search_assets", query=prefix, asset_type=AssetType.MASTER_CHARACTER_CARD)]
        assert m1.id in [item.id for item in await call("media.list_media", media_type=MediaType.IMAGE)]
        a2 = await call("asset.save_asset", asset_id=a2.id, name=f"{prefix}_A2人物卡修订", reference_media_ids=[m1.id], content={"revision": 2})
        m1 = await call("media.save_media", media_id=m1.id, purpose="REFERENCE", content={"revision": 2})

        # Same immutable identity and source_ref is idempotent.
        retry = await call("media.create_media", work_id=work.id, asset_id=a1.id, media_type=MediaType.IMAGE, source_ref=source_ref, content={"ignored_on_retry": True})
        assert retry.id == m1.id

        # BUSINESS: NOT_FOUND and CONFLICT remain distinguishable at Plugin boundary.
        try:
            await _invoke(plugin, "scene.save_scene", scene_id=f"scene_missing_{suffix}", order=1, title="missing", content={})
            raise AssertionError("missing scene unexpectedly saved")
        except RemoteServiceError as exc:
            assert (exc.status_code, exc.error_code) == (404, "NOT_FOUND")
        other = await call("work.create_work", title=f"{prefix}_冲突作品", content={"test": True})
        try:
            await _invoke(plugin, "media.create_media", work_id=other.id, asset_id=None, shot_id=None, media_type=MediaType.IMAGE, purpose=None, source_ref=source_ref, content={})
            raise AssertionError("conflicting source_ref unexpectedly accepted")
        except RemoteServiceError as exc:
            assert (exc.status_code, exc.error_code) == (409, "CONFLICT")

        expected = {
            tool.code for tool in plugin.tools.list()
            if tool.domain in {"work", "script", "episode", "scene", "shot", "asset", "media"}
        }
        assert smoke == expected, f"HTTP_MAPPING: missing smoke operations {sorted(expected - smoke)}"

    # E2E-002: wrong token reaches the real Java process and is AUTH/401.
    correct = {key: os.environ[key] for key in TOKEN_KEYS}
    try:
        for key in TOKEN_KEYS:
            os.environ[key] = "E2E_B02_WRONG_SECRET"
        async with DramaPlugin.load(ROOT, CONFIG) as wrong_plugin:
            try:
                await _invoke(wrong_plugin, "work.list_works")
                raise AssertionError("wrong secret unexpectedly accepted")
            except RemoteServiceError as exc:
                assert exc.status_code == 401
    finally:
        os.environ.update(correct)

    # E2E-003: missing token is CONFIG failure, never a Mock fallback.
    try:
        for key in TOKEN_KEYS:
            os.environ.pop(key, None)
        try:
            DramaPlugin.load(ROOT, CONFIG)
            raise AssertionError("missing secret unexpectedly initialized")
        except ConfigurationError as exc:
            assert "api_token" in str(exc)
    finally:
        os.environ.update(correct)

    # E2E-018: default config remains Mock/local.
    async with DramaPlugin.load(ROOT) as mock_plugin:
        assert (await _invoke(mock_plugin, "work.get_work", work_id="work-1")).id == "work-1"

    print(json.dumps({
        "result": "PASS",
        "prefix": prefix,
        "smokeOperations": len(smoke),
        "ids": {"workId": work.id, "scriptId": script.id, "episodeId": episode.id, "sceneId": scene.id, "shotId": shot.id, "assetA1Id": a1.id, "mediaM1Id": m1.id, "assetA2Id": a2.id},
        "referenceIndependence": {"assetA2ReferenceMediaIds": a2.reference_media_ids, "mediaM1AssetId": m1.asset_id},
        "sourceRefIdempotentMediaId": retry.id,
        "secrets": "REDACTED",
    }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run())
