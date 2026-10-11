"""Late-bound delivery of an unchanged managed original, beneath the input seal.

Storage credentials and signing stay in the Media service. An expiring vendor
result URL is provenance only, never a durable reference or a trust renewal.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import json
import httpx

from drama_plugin.contracts.base import canonical_json, sha256_canonical
from drama_plugin.contracts.video import ProviderTask
from drama_plugin.execution.media import atomic_write
from drama_plugin.execution.transport import DefinitelyNotSubmitted
from drama_plugin.exceptions import RemoteServiceError
from drama_plugin.providers.video.base import SafeProviderError
from drama_plugin.providers.video.image_delivery import external_https


def credential_fingerprint(adapter) -> str:
    key = adapter.settings.api_key
    if not key:
        raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED')
    return sha256(key.get_secret_value().encode()).hexdigest()


def require_trusted_time(generated: datetime) -> None:
    now = datetime.now(timezone.utc)
    if not generated.tzinfo or generated > now or generated < datetime(2026, 3, 11, tzinfo=timezone.utc):
        raise DefinitelyNotSubmitted('REFERENCE_PROVENANCE_UNVERIFIED')
    if now >= generated + timedelta(days=30):
        raise DefinitelyNotSubmitted('REFERENCE_TRUST_EXPIRED')


async def verify_origin(adapter, root: Path, origin, receipt, attempt, content_hash: str) -> None:
    """Authenticate historical ownership once; retain immutable task evidence.

    No numeric account identity is inferred. A changed credential requires the
    exact official task to be accessible again; Provider moderation is final.
    """
    account = credential_fingerprint(adapter)
    if receipt.source_account_fingerprint == account and receipt.source_generated_at is not None:
        require_trusted_time(receipt.source_generated_at)
        return
    identity = {'operationRef': origin.artifact_reference().model_dump(mode='json', by_alias=True),
                'provider': receipt.provider, 'model': origin.model, 'taskId': receipt.remote_identity,
                'contentHash': content_hash, 'credentialFingerprint': account}
    path = root / (sha256_canonical(identity) + '.reference-origin.json')
    if path.exists():
        proof = json.loads(path.read_bytes())
        if proof.get('identity') != identity or proof.get('status') != 'SUCCEEDED':
            raise DefinitelyNotSubmitted('REFERENCE_PROVENANCE_CONFLICT')
        generated = datetime.fromisoformat(proof['generatedAt'])
    else:
        try:
            task = await adapter.get_task(ProviderTask(provider=receipt.provider, model=origin.model,
                provider_task_id=receipt.remote_identity, client_request_id=attempt.client_identity,
                request_fingerprint=attempt.request_fingerprint, status='RUNNING'))
        except (SafeProviderError, httpx.HTTPError):
            raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED') from None
        if task.status != 'SUCCEEDED' or task.provider_task_id != receipt.remote_identity:
            raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED')
        generated = task.completed_at or task.created_at
        if generated is None:
            raise DefinitelyNotSubmitted('REFERENCE_PROVENANCE_UNVERIFIED')
        require_trusted_time(generated)
        # Do not change the old terminal receipt or persist its expired locator again.
        atomic_write(path, canonical_json({'identity': identity, 'status': 'SUCCEEDED',
            'generatedAt': generated.isoformat(), 'evidence': 'AUTHENTICATED_EXACT_OFFICIAL_TASK'}).encode())
    require_trusted_time(generated)


async def managed_original_url(provider, client: httpx.AsyncClient, identity, scope, *, media_id: str) -> str:
    if provider is None:
        raise DefinitelyNotSubmitted('REFERENCE_PUBLIC_DELIVERY_UNCONFIGURED')
    media = await provider.get_media(media_id)
    if (media.id, media.work_id, media.shot_id, media.content_hash, media.file_size, media.mime_type,
            media.media_type.value) != (media_id, scope.work_id, scope.shot_id, identity.content_hash,
            identity.byte_count, identity.mime, identity.kind):
        raise DefinitelyNotSubmitted('REFERENCE_MANAGED_ORIGINAL_MISMATCH')
    # Called for every actual dispatch; the URL is never cached into a package.
    try:
        delivery = await provider.resolve_media(media_id, provider_delivery=True)
    except RemoteServiceError as exc:
        code = ('REFERENCE_PUBLIC_DELIVERY_UNCONFIGURED' if exc.error_code == 'UNRESOLVABLE_MEDIA'
                else 'REFERENCE_DELIVERY_UNAVAILABLE')
        raise DefinitelyNotSubmitted(code) from None
    now = datetime.now(timezone.utc)
    if (delivery.media_id != media_id or delivery.size_bytes != identity.byte_count
            or delivery.mime_type != identity.mime or not delivery.expires_at.tzinfo
            or delivery.expires_at <= now + timedelta(minutes=2)):
        raise DefinitelyNotSubmitted('REFERENCE_DELIVERY_INVALID_OR_EXPIRED')
    url = urlsplit(delivery.url)
    # Reuse the configured store's public protocol. Generation API auth stays
    # on HTTPS; a bare object GET carries no API or storage credentials.
    if url.scheme not in ('http','https') or not external_https(urlunsplit(url._replace(scheme='https'))):
        raise DefinitelyNotSubmitted('REFERENCE_PUBLIC_DELIVERY_UNCONFIGURED')
    digest, size = sha256(), 0
    try:
        # Bare request: neither Provider API auth nor Media service auth reaches storage.
        request = httpx.Request('GET', delivery.url)
        response = await client.send(request, auth=None, follow_redirects=False, stream=True)
        try:
            response.raise_for_status()
            if response.headers.get('content-type', '').split(';', 1)[0] != identity.mime:
                raise DefinitelyNotSubmitted('REFERENCE_ORIGINAL_MIME_MISMATCH')
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > min(identity.byte_count, 256 * 1024 * 1024):
                    raise DefinitelyNotSubmitted('REFERENCE_ORIGINAL_BYTES_MISMATCH')
                digest.update(chunk)
        finally:
            await response.aclose()
    except httpx.HTTPError:
        raise DefinitelyNotSubmitted('REFERENCE_DELIVERY_UNREACHABLE') from None
    if size != identity.byte_count or digest.hexdigest() != identity.content_hash:
        raise DefinitelyNotSubmitted('REFERENCE_ORIGINAL_BYTES_MISMATCH')
    if delivery.expires_at <= datetime.now(timezone.utc) + timedelta(minutes=2):
        raise DefinitelyNotSubmitted('REFERENCE_DELIVERY_INVALID_OR_EXPIRED')
    return delivery.url
