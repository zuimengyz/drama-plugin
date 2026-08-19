from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit

import httpx
import pytest

from drama_plugin.config import ServiceConfig
from drama_plugin.contracts import MediaType
from drama_plugin.exceptions import MediaImportSourceError
from drama_plugin.providers.http import HttpMediaProvider, HttpProviderClient
from drama_plugin.providers.http.media_source import (
    _file_uri_path,
    _is_path_allowed,
    local_media_path,
    open_media_source,
    reject_unsafe_remote,
    stream_remote_source,
)
from drama_plugin.providers.mock import MockDramaData, MockMediaProvider


def test_local_file_security(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    source = allowed / "fixture.png"
    source.write_bytes(b"png")
    assert local_media_path(source.as_uri(), (allowed.resolve(),)) == source.resolve()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    with pytest.raises(MediaImportSourceError) as invalid:
        local_media_path(outside.as_uri(), (allowed.resolve(),))
    assert invalid.value.error_code == "INVALID_ARGUMENT"
    link = allowed / "escape.png"
    link.symlink_to(outside)
    with pytest.raises(MediaImportSourceError) as escaped:
        local_media_path(link.as_uri(), (allowed.resolve(),))
    assert escaped.value.error_code == "INVALID_ARGUMENT"
    with pytest.raises(MediaImportSourceError) as missing:
        local_media_path((allowed / "missing.png").as_uri(), (allowed.resolve(),))
    assert missing.value.error_code == "IMPORT_SOURCE_UNREADABLE"


def test_windows_file_uri_preserves_drive_absolute_path() -> None:
    path = _file_uri_path(urlsplit("file:///D:/home/AI/test.png").path, windows=True)
    assert path == PureWindowsPath(r"D:\home\AI\test.png")
    assert path.is_absolute()


def test_windows_allowed_root_security() -> None:
    root = PureWindowsPath(r"D:\home\AI")
    assert _is_path_allowed(PureWindowsPath(r"D:\home\AI\test.png"), (root,))
    assert not _is_path_allowed(PureWindowsPath(r"D:\other\test.png"), (root,))
    assert not _is_path_allowed(PureWindowsPath(r"D:\home\AI-evil\test.png"), (root,))


@pytest.mark.parametrize(
    ("uri_path", "expected"),
    [
        ("/Users/test/AI/test.png", PurePosixPath("/Users/test/AI/test.png")),
        ("/home/test/AI/test.png", PurePosixPath("/home/test/AI/test.png")),
    ],
)
def test_posix_file_uri_path_regression(uri_path: str, expected: PurePosixPath) -> None:
    assert _file_uri_path(uri_path, windows=False) == expected


def test_windows_file_uri_decodes_encoded_path() -> None:
    uri_path = urlsplit("file:///D:/home/My%20Files/test.png").path
    assert _file_uri_path(uri_path, windows=True) == PureWindowsPath(r"D:\home\My Files\test.png")


def test_remote_rejects_credentials_and_local_network(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MediaImportSourceError):
        reject_unsafe_remote("https://user:secret@example.com/a.png")
    monkeypatch.setattr("socket.getaddrinfo", lambda *args: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(MediaImportSourceError) as local:
        reject_unsafe_remote("https://example.test/a.png")
    assert local.value.error_code == "INVALID_ARGUMENT"


@pytest.mark.asyncio
async def test_remote_source_success_and_redirect() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": "/fixture.png"})
        return httpx.Response(200, headers={"content-type": "image/png; charset=binary"}, content=b"png")

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond), follow_redirects=True, max_redirects=3) as client:
        async with stream_remote_source("https://media.example/redirect", client) as source:
            assert source.filename == "fixture.png"
            assert source.content_type == "image/png"
            assert source.stream.read() == b"png"


@pytest.mark.asyncio
async def test_remote_redirect_is_revalidated() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(302, headers={"location": "https://127.0.0.1/private"}))
    seen: list[str] = []

    def validate(url: str) -> None:
        seen.append(url)
        if "127.0.0.1" in url:
            raise MediaImportSourceError("disallowed", error_code="INVALID_ARGUMENT")

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(MediaImportSourceError) as captured:
            async with stream_remote_source("https://media.example/redirect", client, validate):
                pass
    assert captured.value.error_code == "INVALID_ARGUMENT"
    assert seen == ["https://media.example/redirect", "https://127.0.0.1/private"]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["status", "timeout"])
async def test_remote_source_failures_are_unreadable(failure: str) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(MediaImportSourceError) as captured:
            async with stream_remote_source("https://media.example/missing.png", client):
                pass
    assert captured.value.error_code == "IMPORT_SOURCE_UNREADABLE"


@pytest.mark.asyncio
async def test_http_media_import_uses_multipart_file_stream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "fixture.png"
    source.write_bytes(b"streamed-png")
    monkeypatch.setenv("DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS", str(tmp_path))
    seen: dict[str, object] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        seen["content_type"] = request.headers["content-type"]
        seen["body"] = request.content
        return httpx.Response(200, json={"id":"media-imported","workId":"work-1","mediaType":"IMAGE","sourceRef":"opaque","content":{}})

    config = ServiceConfig(base_url="https://service.invalid", operations={"import_media": "/import"})
    async with httpx.AsyncClient(base_url=config.base_url, transport=httpx.MockTransport(respond)) as client:
        media = HttpMediaProvider(HttpProviderClient(config, client))
        result = await media.import_media("work-1", MediaType.IMAGE, source.as_uri(), {})
    assert result.id == "media-imported"
    assert str(seen["content_type"]).startswith("multipart/form-data; boundary=")
    assert b"streamed-png" in seen["body"]
    assert b'filename="fixture.png"' in seen["body"]


@pytest.mark.asyncio
async def test_resolve_parses_camel_case_result() -> None:
    payload = {"mediaId":"media-1","url":"https://storage.invalid/signed","expiresAt":"2026-08-13T10:00:00Z","mimeType":"image/png","sizeBytes":3}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    config = ServiceConfig(base_url="https://service.invalid", operations={"resolve_media": "/resolve"})
    async with httpx.AsyncClient(base_url=config.base_url, transport=transport) as client:
        result = await HttpMediaProvider(HttpProviderClient(config, client)).resolve_media("media-1")
    assert result.media_id == "media-1" and result.size_bytes == 3


@pytest.mark.asyncio
async def test_restore_uses_allowed_local_file_and_parses_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "fixture.png"
    source.write_bytes(b"stable-png")
    monkeypatch.setenv("DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS", str(tmp_path))

    def respond(request: httpx.Request) -> httpx.Response:
        assert b'"media_id":"media-1"' in request.content
        assert b"stable-png" in request.content
        return httpx.Response(200, json={"mediaId":"media-1","status":"RESTORED","contentHash":"abc","mimeType":"image/png","sizeBytes":10})

    config = ServiceConfig(base_url="https://service.invalid", operations={"restore_media_object": "/restore"})
    async with httpx.AsyncClient(base_url=config.base_url, transport=httpx.MockTransport(respond)) as client:
        result = await HttpMediaProvider(HttpProviderClient(config, client)).restore_media_object("media-1", source.as_uri())
    assert result.media_id == "media-1" and result.status.value == "RESTORED"


@pytest.mark.asyncio
async def test_restore_rejects_source_outside_allowed_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    monkeypatch.setenv("DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS", str(allowed))
    provider = HttpMediaProvider(HttpProviderClient(ServiceConfig(base_url="https://service.invalid", operations={"restore_media_object":"/restore"})))
    with pytest.raises(MediaImportSourceError) as captured:
        await provider.restore_media_object("media-1", outside.as_uri())
    assert captured.value.error_code == "INVALID_ARGUMENT"
    await provider.http.aclose()


@pytest.mark.asyncio
async def test_mock_import_and_resolve_are_offline() -> None:
    provider = MockMediaProvider(MockDramaData())
    imported = await provider.import_media("work-1", MediaType.IMAGE, "file:///not/read/by/mock.png", {"fixture": True})
    resolved = await provider.resolve_media(imported.id)
    assert imported.source_ref != "file:///not/read/by/mock.png"
    assert resolved.media_id == imported.id
    restored = await provider.restore_media_object(imported.id, "file:///not/read/by/mock.png")
    assert restored.media_id == imported.id and restored.status.value == "ALREADY_PRESENT"


@pytest.mark.asyncio
async def test_unsupported_source_scheme_is_invalid() -> None:
    with pytest.raises(MediaImportSourceError) as captured:
        async with open_media_source("data:image/png;base64,AAAA"):
            pass
    assert captured.value.error_code == "INVALID_ARGUMENT"
