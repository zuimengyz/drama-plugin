from __future__ import annotations

import ipaddress
import mimetypes
import os
import socket
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable
from urllib.parse import unquote, urlsplit

import httpx

from drama_plugin.exceptions import MediaImportSourceError


@dataclass
class OpenMediaSource:
    stream: BinaryIO
    filename: str
    content_type: str


def allowed_media_roots(environment: dict[str, str] | None = None) -> tuple[Path, ...]:
    source = environment if environment is not None else os.environ
    raw = source.get("DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS", "")
    return tuple(Path(item).expanduser().resolve() for item in raw.split(os.pathsep) if item.strip())


def local_media_path(source_uri: str, roots: tuple[Path, ...] | None = None) -> Path:
    parsed = urlsplit(source_uri)
    if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"} or parsed.query or parsed.fragment:
        raise MediaImportSourceError("Only canonical local file URIs are supported", error_code="INVALID_ARGUMENT")
    allowed = roots if roots is not None else allowed_media_roots()
    if not allowed:
        raise MediaImportSourceError("Local media import has no configured allowed roots", error_code="INVALID_ARGUMENT")
    path = Path(unquote(parsed.path)).resolve(strict=False)
    if not any(path.is_relative_to(root) for root in allowed):
        raise MediaImportSourceError("Local media source is outside allowed roots", error_code="INVALID_ARGUMENT")
    if not path.exists():
        raise MediaImportSourceError("Local media source does not exist", error_code="IMPORT_SOURCE_UNREADABLE")
    if not path.is_file() or not os.access(path, os.R_OK):
        raise MediaImportSourceError("Local media source is not a readable regular file", error_code="IMPORT_SOURCE_UNREADABLE")
    return path


def reject_unsafe_remote(source_uri: str) -> None:
    parsed = urlsplit(source_uri)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise MediaImportSourceError("Only credential-free https media sources are supported", error_code="INVALID_ARGUMENT")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except socket.gaierror as exc:
        raise MediaImportSourceError("Remote media source cannot be resolved", error_code="IMPORT_SOURCE_UNREADABLE") from exc
    for address in addresses:
        value = ipaddress.ip_address(address)
        if value.is_private or value.is_loopback or value.is_link_local or value.is_multicast or value.is_reserved or value.is_unspecified:
            raise MediaImportSourceError("Remote media source resolves to a disallowed network", error_code="INVALID_ARGUMENT")


@asynccontextmanager
async def stream_remote_source(
    source_uri: str,
    client: httpx.AsyncClient,
    validate_url: Callable[[str], None] | None = None,
) -> AsyncIterator[OpenMediaSource]:
    try:
        current_url = source_uri
        for redirect_count in range(4):
            if validate_url is not None:
                validate_url(current_url)
            async with client.stream("GET", current_url, follow_redirects=False) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location or redirect_count == 3:
                        raise MediaImportSourceError(
                            "Remote media source has an invalid redirect",
                            error_code="IMPORT_SOURCE_UNREADABLE",
                        )
                    current_url = str(response.url.join(location))
                    continue
                response.raise_for_status()
                filename = Path(unquote(urlsplit(str(response.url)).path)).name or "remote-media"
                content_type = response.headers.get("content-type", "application/octet-stream").split(";", 1)[0]
                with tempfile.TemporaryFile("w+b") as stream:
                    async for chunk in response.aiter_bytes():
                        stream.write(chunk)
                    stream.seek(0)
                    yield OpenMediaSource(stream, filename, content_type)
                    return
    except MediaImportSourceError:
        raise
    except (httpx.HTTPError, OSError) as exc:
        raise MediaImportSourceError("Remote media source cannot be read", error_code="IMPORT_SOURCE_UNREADABLE") from exc


@asynccontextmanager
async def open_media_source(source_uri: str) -> AsyncIterator[OpenMediaSource]:
    parsed = urlsplit(source_uri)
    if parsed.scheme == "file":
        path = local_media_path(source_uri)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as stream:
            yield OpenMediaSource(stream, path.name, content_type)
        return
    if parsed.scheme != "https":
        raise MediaImportSourceError("Media source scheme is not supported", error_code="INVALID_ARGUMENT")
    timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with stream_remote_source(source_uri, client, reject_unsafe_remote) as source:
            yield source
