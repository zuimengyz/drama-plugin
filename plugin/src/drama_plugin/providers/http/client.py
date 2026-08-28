from __future__ import annotations

import json as json_module
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import urljoin, urlsplit

import httpx

from drama_plugin.config import ServiceConfig
from drama_plugin.exceptions import ConfigurationError, RemoteServiceError


_JAVA_ERROR_CODES = {
    40001: "INVALID_ARGUMENT",
    40100: "UNAUTHORIZED",
    40400: "NOT_FOUND",
    40900: "CONFLICT",
    50000: "INTERNAL_ERROR",
    42201: "IMPORT_SOURCE_UNREADABLE",
    42202: "STORAGE_ERROR",
    42203: "UNRESOLVABLE_MEDIA",
    42204: "CONTENT_HASH_MISMATCH",
    40901: "OBJECT_CONFLICT",
}


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
            error_code: str | None = None
            try:
                payload = exc.response.json()
                if isinstance(payload, dict):
                    raw_code = payload.get("code")
                    if isinstance(raw_code, str):
                        error_code = raw_code
                    elif isinstance(raw_code, int):
                        error_code = _JAVA_ERROR_CODES.get(raw_code)
            except ValueError:
                pass
            raise RemoteServiceError(
                f"Remote operation {operation} returned HTTP {exc.response.status_code}",
                status_code=exc.response.status_code,
                error_code=error_code,
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise RemoteServiceError(f"Remote operation {operation} failed") from exc

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def download_service_content(self, url: str, destination: Path) -> None:
        target = urljoin(self.config.base_url.rstrip("/") + "/", url)
        if self._origin(target) != self._origin(self.config.base_url):
            raise RemoteServiceError("Drama Service returned content outside its own HTTP origin",
                                     error_code="UNRESOLVABLE_MEDIA")
        try:
            async with self.client.stream("GET", target) as response:
                response.raise_for_status()
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("wb") as output:
                    async for chunk in response.aiter_bytes():
                        output.write(chunk)
        except httpx.HTTPStatusError as exc:
            raise RemoteServiceError(
                f"Drama Service content delivery returned HTTP {exc.response.status_code}",
                status_code=exc.response.status_code,
                error_code="MEDIA_UNAVAILABLE",
            ) from exc
        except httpx.HTTPError as exc:
            raise RemoteServiceError("Drama Service content delivery failed",
                                     error_code="MEDIA_UNAVAILABLE") from exc

    @staticmethod
    def _origin(url: str) -> tuple[str, str, int | None]:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        port = parsed.port if parsed.port is not None else {"http": 80, "https": 443}.get(scheme)
        return scheme, (parsed.hostname or "").lower(), port

    async def multipart_request(self, operation: str, *, metadata: dict[str, Any], stream: BinaryIO, filename: str, content_type: str) -> Any:
        path = self.config.operations.get(operation)
        if not path:
            raise ConfigurationError(f"No HTTP endpoint configured for operation: {operation}")
        try:
            response = await self.client.post(path, files={
                "metadata": (None, json_module.dumps(metadata, separators=(",", ":")), "application/json"),
                "file": (filename, stream, content_type),
            })
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            error_code: str | None = None
            try:
                payload = exc.response.json()
                raw_code = payload.get("code") if isinstance(payload, dict) else None
                error_code = raw_code if isinstance(raw_code, str) else _JAVA_ERROR_CODES.get(raw_code) if isinstance(raw_code, int) else None
            except ValueError:
                pass
            raise RemoteServiceError(f"Remote operation {operation} returned HTTP {exc.response.status_code}", status_code=exc.response.status_code, error_code=error_code) from exc
        except (httpx.HTTPError, ValueError, OSError) as exc:
            raise RemoteServiceError(f"Remote operation {operation} failed") from exc
