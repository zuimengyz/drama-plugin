import asyncio
import base64
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_URL = "http://127.0.0.1:8765/mcp"


def result_payload(result):
    if result.structured_content is not None:
        return result.structured_content
    for item in result.content:
        text = getattr(item, "text", None)
        if text:
            return json.loads(text)
    return None


async def main() -> None:
    mode = sys.argv[1]
    async with streamable_http_client(MCP_URL) as streams:
        async with ClientSession(*streams[:2]) as session:
            await session.initialize()
            if mode == "list":
                result = await session.list_tools()
                payload = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema,
                    }
                    for tool in result.tools
                ]
            elif mode in {"call", "call64"}:
                tool_name = sys.argv[2]
                encoded = sys.argv[3]
                if mode == "call64":
                    encoded = base64.b64decode(encoded).decode("utf-8")
                arguments = json.loads(encoded)
                result = await session.call_tool(tool_name, arguments)
                payload = {
                    "isError": result.is_error,
                    "structuredContent": result.structured_content,
                    "content": [
                        item.model_dump(mode="json") if hasattr(item, "model_dump") else str(item)
                        for item in result.content
                    ],
                }
            elif mode == "resolve-check":
                media_id = sys.argv[2]
                artifact_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None
                media_result = await session.call_tool("media.get_media", {"media_id": media_id})
                media = result_payload(media_result)
                resolve_result = await session.call_tool("media.resolve_media", {"media_id": media_id})
                resolved = result_payload(resolve_result)
                expected_hash = (media.get("content") or {}).get("contentHash")
                payload = {
                    "mediaId": media_id,
                    "metadata": "EXISTS" if not media_result.is_error else "FAIL",
                    "mimeType": resolved.get("mimeType") if resolved else None,
                    "sizeBytes": resolved.get("sizeBytes") if resolved else None,
                    "metadataContentHash": expected_hash,
                    "currentHostResolve": "FAIL",
                    "resolvedSha256": None,
                    "metadataHashEquality": "NOT_RUN",
                    "artifactPath": str(artifact_path) if artifact_path else None,
                    "artifactSha256": None,
                    "artifactHashEquality": "NOT_RUN",
                }
                if artifact_path and artifact_path.is_file():
                    artifact_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
                    payload["artifactSha256"] = artifact_hash
                    payload["artifactHashEquality"] = "PASS" if artifact_hash == expected_hash else "FAIL"
                if not resolve_result.is_error and resolved and resolved.get("url"):
                    try:
                        with urllib.request.urlopen(resolved["url"], timeout=15) as response:
                            data = response.read()
                        resolved_hash = hashlib.sha256(data).hexdigest()
                        payload["currentHostResolve"] = "PASS"
                        payload["resolvedSha256"] = resolved_hash
                        payload["metadataHashEquality"] = "PASS" if resolved_hash == expected_hash else "FAIL"
                    except Exception as exc:
                        payload["resolveError"] = f"{type(exc).__name__}: {exc}"
            else:
                raise SystemExit(f"unknown mode: {mode}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
