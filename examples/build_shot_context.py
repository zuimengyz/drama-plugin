from __future__ import annotations

import asyncio
from pathlib import Path

from drama_plugin import ContextBuildRequest, DramaPlugin
from drama_plugin.contracts import ContextPurpose, ContextScope


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    plugin = DramaPlugin.load(root)
    skill = plugin.skills.get("shot-generation")
    context = await plugin.context.build(
        ContextBuildRequest(
            scope=ContextScope.SHOT,
            resource_id="shot-1",
            purpose=ContextPurpose.SHOT_VIDEO_GENERATION,
        )
    )

    print("Loaded Plugin:", plugin.manifest.name, plugin.manifest.version)
    print("Loaded Skill:", skill.code)
    print()
    print("Context Scope:", context.scope.value)
    print("Shot:", context.shot.description if context.shot else "-")
    print()
    print("Characters:")
    for character in context.entities.characters:
        print(f"- {character.name}: {character.description}")
    print()
    print("Effective Assets:")
    for resolved in context.assets.effective:
        print(f"- {resolved.entity_type}/{resolved.entity_id}: {resolved.effective_asset.name}")
    print()
    print("Generation State:")
    state = context.generation.state
    print(f"- {state.status.value}: {state.message}" if state else "- none")


if __name__ == "__main__":
    asyncio.run(main())
