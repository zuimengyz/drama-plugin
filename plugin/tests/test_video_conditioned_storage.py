from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integration"))
from run_batch7_3d_fish_live import verified_object, cloud_configuration_gate


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["media", "voice"])
async def test_metadata_with_missing_cloud_object_requires_reconciliation(kind):
    metadata = {"id": "stable-1", "contentHash": "a"*64, "fileSize": 3}
    calls = []

    async def invoke(name, arguments):
        calls.append(name)
        return {"url": "https://service.invalid/content", "contentHash": "a"*64}

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404))) as client:
        with pytest.raises(RuntimeError, match="STORAGE_MIGRATION_RECONCILIATION_REQUIRED"):
            await verified_object(invoke=invoke, client=client, kind=kind, metadata=metadata, service_url="https://service.invalid")
    assert calls == [f"{kind}.resolve_{kind}"]


@pytest.mark.asyncio
async def test_restore_trusted_same_hash_only_through_service(tmp_path):
    data = b"trusted video bytes"
    digest = hashlib.sha256(data).hexdigest()
    metadata = {"id": "stable-video", "contentHash": digest, "fileSize": len(data)}
    artifact = tmp_path / "trusted.mp4"
    artifact.write_bytes(data)
    restored = False
    calls = []

    async def invoke(name, arguments):
        nonlocal restored
        calls.append((name, arguments))
        if name == "media.restore_media_object":
            assert arguments == {"media_id": "stable-video", "source_uri": artifact.as_uri()}
            restored = True
            return {"mediaId": "stable-video", "contentHash": digest}
        return {"url": "https://service.invalid/content"}

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:
        httpx.Response(200, content=data) if restored else httpx.Response(404))) as client:
        value = await verified_object(invoke=invoke, client=client, kind="media", metadata=metadata,
            service_url="https://service.invalid", trusted_restore=artifact)
    assert value["restoredSameIdentity"] is True
    assert value["id"] == "stable-video" and value["contentHash"] == digest
    assert [name for name, _ in calls] == ["media.resolve_media", "media.restore_media_object", "media.resolve_media"]


@pytest.mark.asyncio
async def test_wrong_restore_hash_and_direct_storage_url_are_rejected(tmp_path):
    artifact = tmp_path / "untrusted.mp4"
    artifact.write_bytes(b"wrong")
    metadata = {"id": "stable", "contentHash": "a"*64, "fileSize": 3}
    url = "https://service.invalid/content"
    calls = []

    async def invoke(name, arguments):
        calls.append(name)
        return {"url": url}

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404))) as client:
        with pytest.raises(RuntimeError, match="untrusted restore hash"):
            await verified_object(invoke=invoke, client=client, kind="media", metadata=metadata,
                service_url="https://service.invalid", trusted_restore=artifact)
        url = "https://storage.invalid/bucket/object"
        with pytest.raises(RuntimeError, match="STORAGE_OWNER_MISMATCH"):
            await verified_object(invoke=invoke, client=client, kind="media", metadata=metadata, service_url="https://service.invalid")
    assert "media.restore_media_object" not in calls


def test_cloud_gate_rejects_duplicate_local_endpoint_without_leaking_values(tmp_path):
    workspace = Path(__file__).resolve().parents[3]
    (tmp_path / "mcp-host.env").write_text("DRAMA_MCP_PORT=8765\n")
    (tmp_path / "drama-plugin.env").write_text("FISH_AUDIO_API_KEY=not-real\n")
    (tmp_path / "drama-service.env").write_text("DRAMA_MEDIA_STORAGE_ENDPOINT=https://private-cloud.invalid\nDRAMA_MEDIA_STORAGE_ENDPOINT=http://localhost:9000\nDRAMA_MEDIA_STORAGE_SECRET_KEY=never-show-this\n")
    result = cloud_configuration_gate(workspace, tmp_path)
    assert result["status"] == "RECONCILIATION_REQUIRED"
    assert result["endpointClasses"] == ["NON_LOCAL", "LOCAL"]
    assert "never-show-this" not in str(result) and "private-cloud" not in str(result)
