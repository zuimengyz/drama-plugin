from __future__ import annotations

from drama_plugin.contracts.context import ContextBuildRequest, DramaContextPatch, DramaRunContext
from drama_plugin.providers.base import ContextProvider


class ContextBuilder:
    """Stable facade for full and incremental Drama model context projection."""

    def __init__(self, provider: ContextProvider) -> None:
        self.provider = provider

    async def build(self, request: ContextBuildRequest) -> DramaRunContext:
        return await self.provider.build_context(request)

    async def refresh(self, request: ContextBuildRequest, current: DramaRunContext) -> DramaContextPatch:
        return await self.provider.refresh_context(request, current)
