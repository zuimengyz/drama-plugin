from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx


class ArchiveUnavailable(RuntimeError):
    """Synchronization remains pending; this is never a production decision."""


class DramaArchiveClient:
    """Thin, optional service client. Cannot call a model, advance a Run or adopt media."""

    def __init__(self, base_url: str, token: str, *, timeout: float = 30,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._http = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout,
            headers={"Authorization": "Bearer " + token}, transport=transport, trust_env=False)

    @classmethod
    def from_environment(cls, values: Mapping[str, str]) -> DramaArchiveClient | None:
        base = values.get("DRAMA_PLUGIN_SERVICE_MEMORY_BASE_URL", values.get("DRAMA_SERVICE_BASE_URL", "")).strip()
        token = values.get("DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN", values.get("DRAMA_SERVICE_API_TOKEN", "")).strip()
        if not base or not token:
            return None
        return cls(base, token, timeout=float(values.get("DRAMA_PLUGIN_SERVICE_MEMORY_TIMEOUT_SECONDS", values.get("DRAMA_SERVICE_TIMEOUT_SECONDS", "30"))))

    async def request(self, path: str, *, method: str = "GET", params: dict[str, Any] | None = None,
                      body: Any = None) -> Any:
        allowed = {"GET": {"tools", "query", "context", "history", "status", "character-assets"},
                   "POST": {"ingest", "checkpoint"}}
        routes = {"/api/tool/archive/" + suffix for suffix in allowed.get(method, set())}
        if path not in routes:
            raise ValueError("Archive client cannot access production endpoints")
        try:
            response = await self._http.request(method, path, params=params, json=body)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise ArchiveUnavailable("Archive service unavailable; source execution state is unchanged") from None

    async def tools(self) -> list[dict[str, Any]]:
        value = await self.request("/api/tool/archive/tools")
        if not isinstance(value, list):
            raise ArchiveUnavailable("Archive discovery returned an incompatible contract")
        return value

    async def ingest(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        result = await self.request("/api/tool/archive/ingest", method="POST", body={"records": records})
        if not isinstance(result, dict) or result.get("inserted", 0) + result.get("repeated", 0) != len(records):
            raise ArchiveUnavailable("Archive acknowledgement does not cover the batch")
        return result

    async def aclose(self) -> None:
        await self._http.aclose()
