from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def request_bytes(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"{method} {urllib.parse.urlsplit(url).path} returned HTTP {exc.code}"
        ) from exc


def request_json(
    base_url: str,
    path: str,
    *,
    headers: dict[str, str],
    method: str = "GET",
    query: dict[str, str] | None = None,
    value: Any = None,
) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    request_headers = dict(headers)
    body = None
    if value is not None:
        body = json.dumps(value, separators=(",", ":")).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    payload, _ = request_bytes(
        url, method=method, headers=request_headers, body=body
    )
    return json.loads(payload)


def multipart_body(metadata: dict[str, Any], wav: Path) -> tuple[bytes, str]:
    boundary = f"batch71-{uuid.uuid4().hex}"
    delimiter = f"--{boundary}\r\n".encode("ascii")
    body = bytearray()
    body.extend(delimiter)
    body.extend(b'Content-Disposition: form-data; name="metadata"\r\n')
    body.extend(b"Content-Type: application/json\r\n\r\n")
    body.extend(json.dumps(metadata, separators=(",", ":")).encode("utf-8"))
    body.extend(b"\r\n")
    body.extend(delimiter)
    body.extend(
        f'Content-Disposition: form-data; name="file"; filename="{wav.name}"\r\n'.encode(
            "utf-8"
        )
    )
    body.extend(b"Content-Type: audio/wav\r\n\r\n")
    body.extend(wav.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("ascii"))
    return bytes(body), boundary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--secret-config", type=Path)
    args = parser.parse_args()

    token = os.environ.get("DRAMA_TOOL_SECRET", "")
    if not token and args.secret_config:
        match = re.search(
            r"^\s*secret:\s*\$\{DRAMA_TOOL_SECRET:([^}]*)\}\s*$",
            args.secret_config.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        token = match.group(1) if match else ""
    if not token:
        raise RuntimeError(
            "DRAMA_TOOL_SECRET must be set or available through --secret-config"
        )

    wav = args.wav.resolve()
    local_hash = sha256_file(wav)
    title_suffix = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    headers = {"Authorization": f"Bearer {token}"}

    work = request_json(
        args.base_url,
        "/api/tool/work/create",
        headers=headers,
        method="POST",
        value={
            "title": f"Batch 7.1 synthetic audio round-trip {title_suffix}",
            "description": "Deterministic synthetic fixture; no real TTS or paid provider",
            "content": {
                "batch": "7.1",
                "classification": "SYNTHETIC_TEST",
            },
        },
    )
    work_id = work["id"]
    fingerprint_material = {
        "schemaVersion": "audio-input-v1",
        "workId": work_id,
        "fixtureSha256": local_hash,
        "fixtureDurationMs": 1000,
        "classification": "SYNTHETIC_TEST",
    }
    fingerprint = canonical_hash(fingerprint_material)
    source_ref = f"audio-input:{fingerprint}"
    content = {
        "classification": "SYNTHETIC_TEST",
        "reviewStatus": "PASS",
        "audioInputFingerprint": fingerprint,
        "dialogueMutated": False,
        "generationMode": "DETERMINISTIC_FIXTURE",
        "realTtsGeneration": 0,
        "paidProviderCalls": 0,
    }
    metadata = {
        "work_id": work_id,
        "media_type": "AUDIO",
        "purpose": "SPEECH_CLIP",
        "source_ref": source_ref,
        "duration_ms": 1000,
        "content": content,
    }
    body, boundary = multipart_body(metadata, wav)
    import_headers = {
        **headers,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    payload, _ = request_bytes(
        f"{args.base_url.rstrip('/')}/api/tool/media/import",
        method="POST",
        headers=import_headers,
        body=body,
    )
    imported = json.loads(payload)

    media_id = imported["id"]
    fetched = request_json(
        args.base_url,
        "/api/tool/media/get",
        headers=headers,
        query={"media_id": media_id},
    )
    listed = request_json(
        args.base_url,
        "/api/tool/media/list",
        headers=headers,
        query={
            "media_type": "AUDIO",
            "work_id": work_id,
            "purpose": "SPEECH_CLIP",
            "source_ref": source_ref,
        },
    )
    resolved = request_json(
        args.base_url,
        "/api/tool/media/resolve",
        headers=headers,
        query={"media_id": media_id},
    )

    downloaded, _ = request_bytes(resolved["url"])
    downloaded_hash = hashlib.sha256(downloaded).hexdigest()

    checks = {
        "mediaIdStableAcrossImportAndGet": fetched.get("id") == media_id,
        "filteredListReturnedExactlyOne": len(listed) == 1,
        "filteredListMediaIdMatches": len(listed) == 1
        and listed[0].get("id") == media_id,
        "sourceRefMatches": fetched.get("sourceRef") == source_ref,
        "durationMsMatches": fetched.get("durationMs") == 1000,
        "mimeTypeMatches": fetched.get("mimeType") == "audio/wav",
        "fileSizeMatches": fetched.get("fileSize") == wav.stat().st_size,
        "storedContentHashMatchesLocal": fetched.get("contentHash") == local_hash,
        "resolvedMimeTypeMatches": resolved.get("mimeType") == "audio/wav",
        "resolvedSizeMatches": resolved.get("sizeBytes") == wav.stat().st_size,
        "downloadedHashMatchesLocal": downloaded_hash == local_hash,
    }
    if not all(checks.values()):
        failed = ", ".join(name for name, passed in checks.items() if not passed)
        raise AssertionError(f"synthetic media round-trip checks failed: {failed}")

    evidence = {
        "batch": "7.1",
        "classification": "SYNTHETIC_TEST",
        "status": "PASS",
        "workId": work_id,
        "mediaId": media_id,
        "sourceRef": source_ref,
        "audioInputFingerprint": fingerprint,
        "durationMs": fetched["durationMs"],
        "mimeType": fetched["mimeType"],
        "fileSize": fetched["fileSize"],
        "localSha256": local_hash,
        "storedContentHash": fetched["contentHash"],
        "downloadedSha256": downloaded_hash,
        "checks": checks,
        "secretsOrSignedUrlsRecorded": False,
        "realTtsGeneration": 0,
        "paidProviderCalls": 0,
        "comfyCloudUsage": 0,
        "creditConsumption": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "checks": checks}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
