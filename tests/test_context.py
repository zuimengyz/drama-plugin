from pathlib import Path

import pytest

from drama_plugin import ContextBuildRequest, DramaPlugin
from drama_plugin.contracts import ContextPurpose, ContextScope, GenerationStatus
from drama_plugin.providers.mock import MockGenerationProvider


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_build_shot_context_and_refresh_version() -> None:
    plugin = DramaPlugin.load(ROOT)
    request = ContextBuildRequest(scope=ContextScope.SHOT, resource_id="shot-1", purpose=ContextPurpose.SHOT_VIDEO_GENERATION)
    context = await plugin.context.build(request)
    assert context.version == 1
    assert context.shot and context.shot.id == "shot-1"
    assert context.entities.characters[0].name == "狄仁杰"
    assert context.assets.effective[0].effective_asset.id
    assert context.generation.state is not None
    patch = await plugin.context.refresh(request, context)
    assert patch.context_id == context.context_id
    assert patch.base_version == 1
    assert patch.new_version == 2


@pytest.mark.asyncio
async def test_refresh_patch_uses_canonical_aliases_recursively() -> None:
    plugin = DramaPlugin.load(ROOT)
    request = ContextBuildRequest(
        scope=ContextScope.SHOT,
        resource_id="shot-1",
        purpose=ContextPurpose.SHOT_VIDEO_GENERATION,
    )
    context = await plugin.context.build(request)
    generation = plugin.providers.generation
    assert isinstance(generation, MockGenerationProvider)
    generation.data.generation_state = generation.data.generation_state.model_copy(
        update={"status": GenerationStatus.RUNNING, "progress": 0.5}
    )
    patch = await plugin.context.refresh(request, context)
    wire = patch.model_dump(mode="json", by_alias=True)
    serialized = str(wire)
    assert wire["changes"][0]["path"] == "/generation"
    assert "planId" in serialized
    assert "generationTarget" in serialized
    assert "workflowCode" in serialized
    assert "plan_id" not in serialized
    assert "generation_target" not in serialized
    assert "workflow_code" not in serialized


@pytest.mark.asyncio
async def test_build_scene_context() -> None:
    plugin = DramaPlugin.load(ROOT)
    context = await plugin.context.build(ContextBuildRequest(scope=ContextScope.SCENE, resource_id="scene-1", purpose=ContextPurpose.CONTINUITY_REVIEW))
    assert context.scene and context.scene.heading.startswith("内景")
    assert context.shot is None
    assert context.assets.scene
