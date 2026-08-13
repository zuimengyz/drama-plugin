"""Read stable IDs after a real Drama Service restart."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from drama_plugin import DramaPlugin


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "drama-service-http.example.yaml"


async def run(ids: list[str]) -> None:
    if len(ids) != 5:
        raise SystemExit("usage: verify_drama_service_restart.py WORK SCRIPT EPISODE SCENE SHOT")
    required = (
        "DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN",
        "DRAMA_PLUGIN_SERVICE_ASSET_API_TOKEN",
        "DRAMA_PLUGIN_SERVICE_MEDIA_API_TOKEN",
    )
    if any(not os.environ.get(key, "").strip() for key in required):
        raise SystemExit("CONFIG: missing service token")
    async with DramaPlugin.load(ROOT, CONFIG) as plugin:
        work = await plugin.tools.invoke("work.get_work", work_id=ids[0])
        script = await plugin.tools.invoke("script.get_script", script_id=ids[1])
        episode = await plugin.tools.invoke("episode.get_episode", episode_id=ids[2])
        scene = await plugin.tools.invoke("scene.get_scene", scene_id=ids[3])
        shot = await plugin.tools.invoke("shot.get_shot", shot_id=ids[4])
        assert script.work_id == work.id
        assert episode.script_id == script.id
        assert scene.episode_id == episode.id
        assert shot.scene_id == scene.id
    print(json.dumps({"result": "PASS", "restartPersistence": ids}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:]))
