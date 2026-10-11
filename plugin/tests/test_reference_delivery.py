"""Original-byte, expiry and account boundaries before any paid POST."""
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from types import SimpleNamespace
import json
import httpx
from pydantic import SecretStr
import pytest

from drama_plugin.contracts.media import Media, MediaResolveResult
from drama_plugin.execution.contracts import MediaIdentity, ProviderReceipt
from drama_plugin.execution.reference_delivery import managed_original_url, verify_origin
from drama_plugin.execution.transport import DefinitelyNotSubmitted
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope

DATA = b'unchanged-original-provider-video'
SCOPE = RuntimeScope(work_id='W', scene_id='S', shot_id='shot')
IDENTITY = MediaIdentity(media_id='media:sha256:'+sha256(DATA).hexdigest(), content_hash=sha256(DATA).hexdigest(), kind='VIDEO',
                         mime='video/mp4', byte_count=len(DATA))


class Store:
    def __init__(self):
        self.count = 0
        self.record = Media(id='M', work_id='W', shot_id='shot', media_type='VIDEO', source_ref='owned:task',
            mime_type='video/mp4', file_size=len(DATA), content_hash=IDENTITY.content_hash)
        self.host = 'private-store.example.com'
        self.scheme = 'https'
        self.ttl = 900
    async def get_media(self, _): return self.record
    async def resolve_media(self, _, *, provider_delivery=False):
        assert provider_delivery
        self.count += 1
        return MediaResolveResult(media_id='M', url=f'{self.scheme}://{self.host}/bucket/original?signature={self.count}',
            expires_at=datetime.now(timezone.utc)+timedelta(seconds=self.ttl), mime_type='video/mp4', size_bytes=len(DATA))


async def test_each_dispatch_resolves_fresh_original_without_auth_or_transform():
    store, calls = Store(), []
    def handle(request):
        calls.append(request)
        assert request.method == 'GET'
        assert 'authorization' not in request.headers and 'x-drama-tool-secret' not in request.headers
        return httpx.Response(200, content=DATA, headers={'Content-Type':'video/mp4'})
    async with httpx.AsyncClient(headers={'Authorization':'Bearer API-secret'}, transport=httpx.MockTransport(handle)) as client:
        first = await managed_original_url(store, client, IDENTITY, SCOPE, media_id='M')
        second = await managed_original_url(store, client, IDENTITY, SCOPE, media_id='M')
    assert first != second and store.count == 2 and len(calls) == 2
    assert store.record.content_hash == IDENTITY.content_hash


async def test_existing_public_http_store_is_not_replaced_with_an_invented_https_alias():
    store = Store()
    store.scheme, store.host = 'http', '120.48.43.132'
    def handle(request):
        assert str(request.url).startswith('http://120.48.43.132/')
        assert 'authorization' not in request.headers
        return httpx.Response(200, content=DATA, headers={'Content-Type':'video/mp4'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await managed_original_url(store, client, IDENTITY, SCOPE, media_id='M')
    assert result.startswith('http://120.48.43.132/')


@pytest.mark.parametrize('failure', ['wrong-bytes','wrong-mime','wrong-owner','expired','localhost','redirect','oversize'])
async def test_invalid_delivery_fails_before_post(failure):
    store, calls = Store(), []
    if failure == 'wrong-owner': store.record = store.record.model_copy(update={'work_id':'other'})
    if failure == 'expired': store.ttl = 10
    if failure == 'localhost': store.host = 'localhost'
    def handle(request):
        calls.append(request)
        assert request.method == 'GET'
        return httpx.Response(302 if failure == 'redirect' else 200,
            content=b'changed' if failure == 'wrong-bytes' else DATA+b'x' if failure == 'oversize' else DATA,
            headers={'Content-Type':'image/jpeg' if failure == 'wrong-mime' else 'video/mp4',
                     'Location':'https://somewhere.example.com/changed'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(DefinitelyNotSubmitted):
            await managed_original_url(store, client, IDENTITY, SCOPE, media_id='M')
    assert not any(r.method == 'POST' for r in calls)


def provenance_fixture(age=2, key='current-account-key'):
    generated = datetime.now(timezone.utc)-timedelta(days=age)
    calls = []
    async def get_task(task):
        calls.append(task)
        # A poisoned/expired locator is deliberately irrelevant to delivery.
        return task.model_copy(update={'status':'SUCCEEDED','completed_at':generated,
            'output_url':'https://expired.invalid/old?X-Tos-Date=20000101T000000Z&X-Tos-Expires=1'})
    adapter = SimpleNamespace(settings=SimpleNamespace(api_key=SecretStr(key)), get_task=get_task)
    origin = SimpleNamespace(model='seedance-2-fast', artifact_reference=lambda: ArtifactReference(
        owner='execution-operation', artifact_ref='source', version=1))
    receipt = SimpleNamespace(provider='seedance',remote_identity='original-task',source_generated_at=None,
                              source_account_fingerprint=None)
    attempt = SimpleNamespace(client_identity='a'*64,request_fingerprint='b'*64)
    return adapter,origin,receipt,attempt,calls


async def test_legacy_origin_authenticates_exact_task_and_retains_proof_without_old_url(tmp_path):
    a,o,r,t,calls = provenance_fixture()
    await verify_origin(a,tmp_path,o,r,t,IDENTITY.content_hash)
    await verify_origin(a,tmp_path,o,r,t,IDENTITY.content_hash)
    assert len(calls) == 1 and calls[0].provider_task_id == r.remote_identity
    proof = json.loads(next(tmp_path.glob('*.reference-origin.json')).read_text())
    assert 'expired.invalid' not in str(proof) and 'current-account-key' not in str(proof)
    assert r.source_generated_at is None  # Historical receipt stays unchanged.


async def test_storage_url_cannot_renew_30_day_trust(tmp_path):
    a,o,r,t,calls = provenance_fixture(age=31)
    with pytest.raises(DefinitelyNotSubmitted, match='REFERENCE_TRUST_EXPIRED'):
        await verify_origin(a,tmp_path,o,r,t,IDENTITY.content_hash)
    assert len(calls) == 1 and not list(tmp_path.iterdir())


async def test_changed_credential_requires_official_ownership_check(tmp_path):
    a,o,r,t,calls = provenance_fixture()
    await verify_origin(a,tmp_path,o,r,t,IDENTITY.content_hash)
    a.settings.api_key = SecretStr('different-account-key')
    async def inaccessible(task): return task.model_copy(update={'status':'UNKNOWN'})
    a.get_task = inaccessible
    with pytest.raises(DefinitelyNotSubmitted, match='REFERENCE_ACCOUNT_UNVERIFIED'):
        await verify_origin(a,tmp_path,o,r,t,IDENTITY.content_hash)


def test_absent_new_provenance_fields_preserve_historical_receipt_serialization():
    raw = dict(scope=SCOPE.model_dump(mode='json', by_alias=True), runId='run',
        sourcePackageRef={'owner':'production-package','artifactRef':'P','version':1},
        operationRef={'owner':'execution-operation','artifactRef':'O','version':1},
        attemptRef={'owner':'provider-attempt','artifactRef':'A','version':1}, provider='seedance',
        clientIdentity='a'*64, requestFingerprint='b'*64, remoteIdentity='task', state='SUCCEEDED',
        result={'resultId':'task','locator':'https://expired.invalid/video'})
    receipt = ProviderReceipt.seal(**raw)
    retained = receipt.model_dump(mode='json', by_alias=True)
    assert 'sourceGeneratedAt' not in retained and 'sourceAccountFingerprint' not in retained
    assert ProviderReceipt.model_validate(retained).artifact_reference() == receipt.artifact_reference()
