from __future__ import annotations

from typing import Any

import httpx

from drama_plugin.config import ServiceConfig
from drama_plugin.exceptions import ConfigurationError, RemoteServiceError


class HttpProviderClient:
    """Shared HTTP transport. Operation paths are supplied entirely by configuration."""

    def __init__(self, config: ServiceConfig, client: httpx.AsyncClient | None = None) -> None:
        self.config = config
        headers = {"Authorization": f"Bearer {config.api_token}"} if config.api_token else None
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(base_url=config.base_url, timeout=config.timeout_seconds, headers=headers)

    async def request(self, operation: str, *, method: str = "GET", params: dict[str, Any] | None = None, json: Any = None) -> Any:
        path = self.config.operations.get(operation)
        if not path:
            raise ConfigurationError(f"No HTTP endpoint configured for operation: {operation}")
        try:
            response = await self.client.request(method, path, params=params, json=json)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise RemoteServiceError(f"Remote operation {operation} returned HTTP {exc.response.status_code}") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise RemoteServiceError(f"Remote operation {operation} failed") from exc

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()
