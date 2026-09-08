"""Media completion through the installed tool contracts, using configured MCP.

Only this adapter owns protocol/temporary delivery URLs. It has no generator.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit
import httpx
from drama_plugin.contracts.media import Media, MediaType, MediaResolveResult, MediaRestoreResult
from drama_plugin.exceptions import RemoteServiceError
from drama_plugin.providers.http.client import HttpProviderClient
from drama_plugin.providers.http.providers import HttpMemoryProvider, HttpAssetProvider, HttpMediaProvider


class McpMediaSession:
    def __init__(self, config_path: Path) -> None:
        config = json.loads(config_path.read_text())
        self.url = config['mcpServers']['drama-tools']['url']
        self.client = httpx.AsyncClient(timeout=60, follow_redirects=False)
        self.headers = {'Accept': 'application/json, text/event-stream'}
        self.sequence = 0
        self.names: set[str] = set()
        self.calls: list[str] = []
        self.memory = HttpMemoryProvider(cast(HttpProviderClient, self))
        self.asset = HttpAssetProvider(cast(HttpProviderClient, self))
        self.media = McpMediaProvider(self)

    @staticmethod
    def parse(response: httpx.Response) -> dict[str, Any]:
        response.raise_for_status()
        body = (json.loads(next(s[6:] for s in response.text.splitlines() if s.startswith('data: ')))
                if 'text/event-stream' in response.headers.get('content-type', '') else response.json())
        if 'error' in body:
            raise RemoteServiceError('MCP protocol request failed')
        return cast(dict[str, Any], body)

    async def __aenter__(self) -> McpMediaSession:
        response = await self.client.post(self.url, headers=self.headers, json={'jsonrpc':'2.0','id':0,
            'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},
            'clientInfo':{'name':'drama-media-completion','version':'1'}}})
        body = self.parse(response)
        self.headers['MCP-Protocol-Version'] = body['result']['protocolVersion']
        if response.headers.get('mcp-session-id'):
            self.headers['Mcp-Session-Id'] = response.headers['mcp-session-id']
        await self.client.post(self.url, headers=self.headers,
            json={'jsonrpc':'2.0','method':'notifications/initialized'})
        schema = await self.rpc('tools/list', {})
        self.names = {item['name'] for item in schema['tools']}
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.client.aclose()

    async def rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.sequence += 1
        response = await self.client.post(self.url, headers=self.headers,
            json={'jsonrpc':'2.0','id':self.sequence,'method':method,'params':params})
        return cast(dict[str, Any], self.parse(response)['result'])

    async def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self.names:
            raise RemoteServiceError(f'Required tool unavailable: {name}')
        self.calls.append(name)
        result = await self.rpc('tools/call', {'name':name,'arguments':arguments})
        if result.get('isError'):
            # Never echo full remote errors that may contain a signed URL.
            payload = result.get('structuredContent') or json.loads(result['content'][0]['text'])
            code = payload.get('error', {}).get('code')
            raise RemoteServiceError(f'Formal tool {name} failed; recover persistence without regeneration', error_code=code)
        return result.get('structuredContent') or json.loads(result['content'][0]['text'])

    async def request(self, operation: str, *, method: str = 'GET', params: dict[str, Any] | None = None,
                      json: Any = None) -> Any:
        domain = operation.split('_', 1)[1].rstrip('s')
        return await self.call(f'{domain}.{operation}', json if json is not None else (params or {}))


class McpMediaProvider(HttpMediaProvider):
    def __init__(self, session: McpMediaSession) -> None:
        super().__init__(cast(HttpProviderClient, session))
        self.session = session

    async def import_media(self, work_id: str, media_type: MediaType, source_uri: str, content: dict[str, Any],
                           asset_id: str | None = None, shot_id: str | None = None, purpose: str | None = None,
                           source_ref: str | None = None, duration_ms: int | None = None) -> Media:
        return Media.model_validate(await self.session.call('media.import_media', dict(work_id=work_id,
            media_type=media_type.value, source_uri=source_uri, content=content, asset_id=asset_id,
            shot_id=shot_id, purpose=purpose, source_ref=source_ref, duration_ms=duration_ms)))

    async def download_media(self, media_id: str, destination: Path) -> MediaResolveResult:
        resolved = await self.resolve_media(media_id)
        parsed = urlsplit(resolved.url)
        if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
            raise RemoteServiceError('Invalid formal delivery URL')
        # URL is obtained only from the authenticated formal resolve tool. No arbitrary
        # source URL or redirect is accepted, and no tool credentials are forwarded.
        async with self.session.client.stream('GET', resolved.url) as response:
            response.raise_for_status()
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('wb') as output:
                async for chunk in response.aiter_bytes():
                    output.write(chunk)
        return resolved

    async def restore_media_object(self, media_id: str, source_uri: str) -> MediaRestoreResult:
        return MediaRestoreResult.model_validate(await self.session.call('media.restore_media_object',
            {'media_id':media_id,'source_uri':source_uri}))
