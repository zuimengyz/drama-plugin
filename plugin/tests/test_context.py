from pathlib import Path

import pytest

from drama_plugin import ContextBuildRequest, DramaPlugin
from drama_plugin.contracts import ContextPurpose, ContextScope
from drama_plugin.providers.mock import MockMemoryProvider

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_build_shot_context_contains_minimal_persistent_chain() -> None:
    plugin = DramaPlugin.load(ROOT)
    request = ContextBuildRequest(scope=ContextScope.SHOT, resource_id="shot-1", purpose=ContextPurpose.SHOT_PRODUCTION, options={"selectedAssetIds": ["asset-di"]})
    context = await plugin.context.build(request)
    assert context.version == 1
    assert context.work and context.work.id == "work-1"
    assert context.script and context.script.work_id == context.work.id
    assert context.episode and context.episode.script_id == context.script.id
    assert context.scene and context.scene.episode_id == context.episode.id
    assert context.shot and context.shot.scene_id == context.scene.id
    assert context.selected_asset_ids == ["asset-di"]
    assert not hasattr(context, "generation")


@pytest.mark.asyncio
async def test_refresh_patch_uses_canonical_aliases() -> None:
    plugin = DramaPlugin.load(ROOT)
    request = ContextBuildRequest(scope=ContextScope.SHOT, resource_id="shot-1", purpose=ContextPurpose.SHOT_DESIGN)
    context = await plugin.context.build(request)
    memory = plugin.providers.memory
    assert isinstance(memory, MockMemoryProvider)
    memory.data.shot = memory.data.shot.model_copy(update={"duration_seconds": 5.0})
    patch = await plugin.context.refresh(request, context)
    wire = patch.model_dump(mode="json", by_alias=True)
    assert wire["changes"][0]["path"] == "/shot"
    assert "durationSeconds" in str(wire)
    assert "duration_seconds" not in str(wire)


@pytest.mark.asyncio
async def test_build_scene_context_does_not_load_assets_or_media() -> None:
    plugin = DramaPlugin.load(ROOT)
    context = await plugin.context.build(ContextBuildRequest(scope=ContextScope.SCENE, resource_id="scene-1", purpose=ContextPurpose.SCENE_DEVELOPMENT))
    assert context.scene and context.scene.heading.startswith("内景")
    assert context.shot is None
    assert context.asset is None
    assert context.media is None
