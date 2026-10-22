"""Expired locators do not change the bytes/authority of retained official tails."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from types import SimpleNamespace as NS

import httpx
import pytest
from pydantic import SecretStr

from drama_plugin.execution.contracts import RequestReference
from drama_plugin.execution.live_transport import TargetHttpTransport
from drama_plugin.execution.media import LocalMediaStore
from drama_plugin.execution.store import ExecutionStore
from drama_plugin.execution.transport import CapabilityAbsent, DefinitelyNotSubmitted
from drama_plugin.production.contracts import SourceReference
from drama_plugin.production.references import ReferenceExecutionBinding
from drama_plugin.providers.video.image_delivery import decode_image_url
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', [None, 'changed_bytes', 'expired_trust', 'wrong_model', 'wrong_input_hash'])
async def test_exact_official_tail_uses_verified_local_original(tmp_path, monkeypatch, fault):
    scope = RuntimeScope(work_id='fixture-work', scene_id='fixture-scene', shot_id='fixture-shot')
    media_store = LocalMediaStore(tmp_path / 'media')
    data = b'\xff\xd8\xff' + b'synthetic-retained-tail'
    media = media_store.retain(data, kind='IMAGE', mime='image/jpeg')
    authority = SourceReference(owner='professional', artifact_ref='fixture-reference-owner',
        version=1, fingerprint='1' * 64, path=('content', 'use'))
    frame_ref = ArtifactReference(owner='continuation-frame', artifact_ref='fixture-frame', version=1)
    binding = ReferenceExecutionBinding(binding_id='fixture-picture', version=1, scope=scope,
        media=dict(media_id=media.media_id, version='1', content_hash=media.content_hash,
            kind='image', semantics=('style',), width=640, height=480, review_ref='fixture-review'),
        duties=(dict(role='LOOK', necessity='REQUIRED', subject='fixture-shot', purpose='Light only'),),
        role='REFERENCE', authorization_scope='ADOPTED_PRODUCTION_INPUT', authority_refs=(authority,),
        picture_frame_ref=frame_ref)
    ref = binding.source().reference()
    ledger = NS(path=tmp_path/'ledger.sqlite3', get_artifact=lambda *args: (binding.model_dump(), scope, ref.fingerprint))
    origin = NS(model='seedance-2-standard')
    source = NS(scope=scope, operation_ref='op', attempt_ref='attempt', media=NS(content_hash='2' * 64))
    receipt = NS(provider='seedance', source_account_fingerprint=sha256(b'fixture-key').hexdigest(),
        source_generated_at=datetime.now(timezone.utc) - timedelta(days=31 if fault == 'expired_trust' else 2),
        last_frame_url='https://expired.example/tail?X-Tos-Date=20000101T000000Z&X-Tos-Expires=60')
    monkeypatch.setattr('drama_plugin.generation.operation.continuation_frame',
        lambda *args, **kwargs: (NS(media=media), source, receipt, None))
    monkeypatch.setattr(ExecutionStore, 'get', lambda self, ref, kind: origin if ref == 'op' else NS())
    calls = []
    def no_http(request):
        calls.append(request.method)
        raise AssertionError('Retained original delivery must not use expired URL or create a task')
    async with httpx.AsyncClient(transport=httpx.MockTransport(no_http)) as client:
        adapter = NS(provider='seedance', client=client, settings=NS(api_key=SecretStr('fixture-key')))
        transport = TargetHttpTransport(adapter, tmp_path / 'receipts', ledger=ledger, retained_media=media_store)
        reference = RequestReference(binding_ref=ref, media_id=media.media_id,
            content_hash='0' * 64 if fault == 'wrong_input_hash' else media.content_hash,
            role='REFERENCE', kind='image')
        if fault == 'changed_bytes':
            (media_store.directory / media.content_hash).write_bytes(b'\xff\xd8\xffchanged')
        operation = NS(scope=scope, model='wrong-model' if fault == 'wrong_model' else origin.model)
        if fault:
            with pytest.raises((ValueError, CapabilityAbsent, DefinitelyNotSubmitted)):
                await transport.reference_url(reference, operation)
        else:
            delivered = await transport.reference_url(reference, operation)
            assert decode_image_url(delivered) == data
            assert sha256(decode_image_url(delivered)).hexdigest() == reference.content_hash
        assert not calls
