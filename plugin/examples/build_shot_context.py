from __future__ import annotations

import asyncio
from pathlib import Path

from drama_plugin import ContextBuildRequest, DramaPlugin
from drama_plugin.contracts import ContextPurpose, ContextScope


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    plugin = DramaPlugin.load(root)
    skill = plugin.skills.get("shot-production")
    context = await plugin.context.build(
        ContextBuildRequest(
            scope=ContextScope.SHOT,
            resource_id="shot-1",
            purpose=ContextPurpose.SHOT_PRODUCTION,
            options={"selectedAssetIds": ["asset-di", "asset-study"]},
        )
    )

    print("Loaded Plugin:", plugin.manifest.name, plugin.manifest.version)
    print("Loaded Skill:", skill.code)
    print()
    print("Context Scope:", context.scope.value)
    print("Shot:", context.shot.title if context.shot else "-")
    print("Scene:", context.scene.title if context.scene else "-")
    print("Work:", context.work.title if context.work else "-")
    print("Selected Assets:", ", ".join(context.selected_asset_ids) or "- none")


if __name__ == "__main__":
    asyncio.run(main())
