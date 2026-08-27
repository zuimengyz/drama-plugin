from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from drama_plugin.config import ServiceConfig
from drama_plugin.contracts.voice import VoiceContent, VoiceSourceType, VoiceStatus
from drama_plugin.providers.http import HttpMemoryProvider, HttpProviderClient, HttpVoiceProvider


def voice_payload(version: int = 1) -> dict[str, object]:
    return {
        "id": "voice-1", "name": "Stable Voice", "sourceType": "DESIGNED",
        "status": "ACTIVE", "storageType": "S3", "bucketName": "bucket",
        "objectKey": "voices/voice-1/master.wav", "mimeType": "audio/wav",
        "fileSize": 4, "durationMs": 1000, "contentHash": "hash",
        "content": {"schemaVersion": "voice-v1", "creativeCastingProfile": {},
                    "sourceProvenance": {}, "providerMappings": []},
        "version": version, "createdAt": None, "updatedAt": None,
    }


@pytest.mark.asyncio
async def test_voice_http_import_get_search_update_and_resolve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    master = tmp_path / "master.wav"; master.write_bytes(b"RIFF")
    monkeypatch.setenv("DRAMA_PLUGIN_MEDIA_IMPORT_ALLOWED_ROOTS", str(tmp_path))
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/voice/import":
            assert b'name="metadata"' in request.content
            assert b'"source_type":"DESIGNED"' in request.content
            assert b'name="file"' in request.content and b"RIFF" in request.content
            return httpx.Response(200, json=voice_payload())
        if request.url.path == "/voice/get":
            assert request.url.params["voice_id"] == "voice-1"
            return httpx.Response(200, json=voice_payload())
        if request.url.path == "/voice/search":
            assert request.url.params["status"] == "ACTIVE"
            return httpx.Response(200, json=[voice_payload()])
        if request.url.path == "/voice/update":
            payload = __import__("json").loads(request.content)
            assert payload["expected_version"] == 1
            return httpx.Response(200, json=voice_payload(version=2))
        assert request.url.path == "/voice/resolve"
        return httpx.Response(200, json={"voiceId": "voice-1",
            "url": "https://signed.invalid/master", "expiresAt": datetime.now(UTC).isoformat(),
            "mimeType": "audio/wav", "sizeBytes": 4, "contentHash": "hash"})

    config = ServiceConfig(base_url="https://unit.invalid", api_token="secret", operations={
        "import_voice": "/voice/import", "get_voice": "/voice/get",
        "search_voices": "/voice/search", "update_voice": "/voice/update",
        "resolve_voice": "/voice/resolve",
    })
    async with httpx.AsyncClient(base_url=config.base_url, transport=httpx.MockTransport(handler),
                                 headers={"Authorization": "Bearer secret"}) as raw:
        provider = HttpVoiceProvider(HttpProviderClient(config, raw))
        content = VoiceContent(creative_casting_profile={}, source_provenance={})
        imported = await provider.import_voice("Stable Voice", VoiceSourceType.DESIGNED,
                                               master.as_uri(), 1000, content)
        assert imported.id == "voice-1"
        assert (await provider.get_voice("voice-1")).content_hash == "hash"
        assert len(await provider.search_voices(status=VoiceStatus.ACTIVE)) == 1
        assert (await provider.update_voice("voice-1", content, 1)).version == 2
        assert (await provider.resolve_voice("voice-1")).content_hash == "hash"
    assert calls == ["/voice/import", "/voice/get", "/voice/search", "/voice/update", "/voice/resolve"]


@pytest.mark.asyncio
async def test_work_voice_binding_uses_versioned_service_operation() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        assert payload == {"work_id": "work-1", "speaker_key": "speaker:a",
                           "voice_id": "voice-1", "expected_version": 7}
        return httpx.Response(200, json={"id": "work-1", "title": "Work",
            "description": None, "content": {"voiceProfiles": [{"speakerKey": "speaker:a",
            "voiceId": "voice-1"}]}, "version": 8})

    config = ServiceConfig(base_url="https://unit.invalid", operations={"bind_work_voice": "/work/bind"})
    async with httpx.AsyncClient(base_url=config.base_url, transport=httpx.MockTransport(handler)) as raw:
        provider = HttpMemoryProvider(HttpProviderClient(config, raw))
        bound = await provider.bind_work_voice("work-1", "speaker:a", "voice-1", 7)
    assert bound.version == 8
