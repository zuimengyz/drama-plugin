"""Network-denied dispatch/recovery faults; no production records or model calls."""
import json
import socket

import httpx
import pytest
from pydantic import SecretStr
from types import SimpleNamespace

from drama_plugin.config import ServiceConfig
from drama_plugin.execution.contracts import (
    OperationProgress, OperationState, ProviderAttempt, ProviderReceipt,
)
from drama_plugin.execution.live_transport import TargetHttpTransport
from drama_plugin.execution.transport import RecoveryIdentityUnavailable
from drama_plugin.exceptions import RemoteServiceError
from drama_plugin.generation.contracts import ExecutionDiagnostic
from drama_plugin.persistence.stores import DurableGenerationArtifactStore
from drama_plugin.providers.http.client import HttpProviderClient
from drama_plugin.providers.video.adapters import SeedanceProvider
from drama_plugin.providers.video.registry import ProviderSettings
from drama_plugin.runtime.contracts import CapabilityInput
from test_live_qualification import http_prepared, video


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No real network or production API allowed')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)


async def rig(tmp_path, monkeypatch, video, handler):
    # Use the native fixture's complete immutable owner lineage.
    p, op, request, _ = await http_prepared(tmp_path, monkeypatch, video)
    adapter = SeedanceProvider(op.model, ProviderSettings(api_key=SecretStr('offline-secret'),
        base_url='https://ark.cn-beijing.volces.com/api/v3'), resolve=None,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    transport = TargetHttpTransport(adapter, tmp_path/'receipts', ledger=p.ledger, qualification_only=True)
    owner = p.execution
    owner.transports['seedance'] = transport
    monkeypatch.setattr(owner, '_approved', lambda _: (op, request, None))
    monkeypatch.setattr(owner, '_govern', lambda inputs, codes, *args, **kwargs:
        SimpleNamespace(artifact_refs=()) if codes else None)
    inputs = CapabilityInput(run_id=op.run_id, operation_id='fixture-execute', scope=op.scope)
    return owner, transport, op, request, inputs


def detail(owner, op):
    cp = owner.store.checkpoint(op.artifact_reference())
    return DurableGenerationArtifactStore(owner.store.ledger).diagnostics(cp.progress.last_failure_ref)[0].failure_details


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['read_timeout', 'wire_write', 'preflight', 'post_timeout', 'http500', 'http400', 'invalid_ack'])
async def test_dispatch_stage_classifies_and_retains_cause(tmp_path, monkeypatch, video, mode):
    calls, reads = [], []
    def handle(req):
        calls.append(req)
        if mode == 'post_timeout':
            raise httpx.ReadTimeout('offline-secret https://signed.invalid/private', request=req)
        status = {'http500':500, 'http400':400}.get(mode, 200)
        return httpx.Response(status, headers={'x-request-id':'fixture-request-id'},
            json={'error':{'code':'FixtureError', 'message':'offline-secret'}, 'status':'running'})
    owner, transport, op, request, inputs = await rig(tmp_path, monkeypatch, video, handle)
    if mode == 'read_timeout':
        def local_get(req):
            reads.append(req)
            raise httpx.ReadTimeout('offline-secret', request=req)
        local = HttpProviderClient(ServiceConfig(base_url='http://local.invalid',
            operations={'get_media':'/media'}), httpx.AsyncClient(base_url='http://local.invalid',
                transport=httpx.MockTransport(local_get)))
        async def materialize(*args, **kwargs):
            await local.request('get_media')
        monkeypatch.setattr(transport, 'materialize_reference_payload', materialize)
    elif mode == 'wire_write':
        def broken_write(*args):
            raise OSError('private filesystem details')
        monkeypatch.setattr('drama_plugin.execution.live_transport.atomic_write', broken_write)
    elif mode == 'preflight':
        def broken_grant(*args):
            raise ValueError('private authorization details')
        monkeypatch.setattr(transport, '_grant', broken_grant)
    result = await owner.execute(inputs)
    assert result.code in {None, 'REFERENCE_INPUT_UNAVAILABLE', 'PRE_SUBMISSION_FAILED', 'HTTP_400',
        'UNKNOWN_SUBMISSION_RECOVERY_PENDING', 'PROVIDER_QUERY_PENDING'}, result
    cp = owner.store.checkpoint(op.artifact_reference())
    d = detail(owner, op)
    before = mode in {'read_timeout','wire_write','preflight'}
    assert cp.state == (OperationState.FAILED if before or mode == 'http400' else OperationState.UNKNOWN)
    assert len(calls) == (0 if before else 1)
    assert d.request_started is (not before)
    assert d.traceback_frames
    assert 'offline-secret' not in d.model_dump_json()
    assert 'private' not in d.model_dump_json()
    if mode == 'read_timeout':
        assert len(reads) == 2
        assert d.stage == 'REFERENCE_MATERIALIZATION'
        assert d.exception_types == ('RemoteServiceError', 'ReadTimeout')
        assert cp.progress.query_last_code == 'REFERENCE_INPUT_UNAVAILABLE'
        assert not list(transport.root.glob('*.wire.json'))
    if mode == 'post_timeout':
        assert d.exception_types == ('PossiblySubmitted', 'ReadTimeout')
    if mode in {'http400','http500'}:
        assert d.http_status == int(mode[4:])
        assert d.request_id == 'fixture-request-id' and d.official_error_code == 'FixtureError'
    await owner.execute(inputs)
    assert len(calls) == (0 if before else 1)  # Neither failure class re-posts.
    if cp.state == OperationState.UNKNOWN:
        assert owner.store.checkpoint(op.artifact_reference()).progress.unknown_lookup_last_code == 'PROVIDER_TASK_ID_REQUIRED'
    await transport.adapter.client.aclose()
    if mode == 'read_timeout':
        await local.client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['parse_ack', 'save_receipt'])
async def test_retained_exact_ack_recovers_after_partial_local_failure(tmp_path, monkeypatch, video, fault):
    calls = []
    def handle(req):
        calls.append(req)
        if req.method == 'POST':
            return httpx.Response(200, json={'id':'exact-task', 'status':'running'})
        assert req.url.path.endswith('/tasks/exact-task')
        return httpx.Response(200, json={'id':'exact-task', 'status':'succeeded',
            'content':{'video_url':'https://output.invalid/result.mp4'}})
    owner, transport, op, request, inputs = await rig(tmp_path, monkeypatch, video, handle)
    original_normalize = transport.adapter.normalize
    if fault == 'parse_ack':
        def bad_parse(raw, task):
            raise ValueError('optional ACK field is malformed')
        monkeypatch.setattr(transport.adapter, 'normalize', bad_parse)
    else:
        from drama_plugin.execution.media import atomic_write
        def failed_final_receipt(path, content):
            if path.name.endswith(('.ack.json', '.wire.json')):
                return atomic_write(path, content)
            raise OSError('fixture final receipt write failed')
        monkeypatch.setattr('drama_plugin.execution.live_transport.atomic_write', failed_final_receipt)
    await owner.execute(inputs)
    cp = owner.store.checkpoint(op.artifact_reference())
    assert cp.state == OperationState.UNKNOWN
    assert list(transport.root.glob('*.ack.json'))
    monkeypatch.setattr(transport.adapter, 'normalize', original_normalize)
    await owner.execute(inputs)
    cp = owner.store.checkpoint(op.artifact_reference())
    assert cp.state == OperationState.SUCCEEDED
    assert owner.store.get(cp.receipt_ref, ProviderReceipt).remote_identity == 'exact-task'
    assert [r.method for r in calls] == ['POST', 'GET']
    assert json.loads(calls[0].content)['content'][0]['text'] == request.prompt_text
    await transport.adapter.client.aclose()


@pytest.mark.asyncio
async def test_no_ack_does_not_match_unsent_local_fields_or_search_nearby_jobs(tmp_path, monkeypatch, video):
    def forbidden(_):
        raise AssertionError('No provider list lookup can establish local identity')
    owner, transport, op, request, inputs = await rig(tmp_path, monkeypatch, video, forbidden)
    cp = owner.reserve(inputs)
    attempt = owner.store.get(cp.attempt_ref, ProviderAttempt)
    with pytest.raises(RecoveryIdentityUnavailable, match='PROVIDER_TASK_ID_REQUIRED'):
        await transport.recover_unknown(op, attempt)
    assert not list(transport.root.iterdir())
    await transport.adapter.client.aclose()


@pytest.mark.asyncio
async def test_ack_from_another_attempt_is_rejected_before_query(tmp_path, monkeypatch, video):
    calls = []
    owner, transport, op, request, inputs = await rig(tmp_path, monkeypatch, video,
        lambda req: calls.append(req) or httpx.Response(200, json={'id':'one-task','status':'running'}))
    await owner.execute(inputs)
    cp = owner.store.checkpoint(op.artifact_reference())
    attempt = owner.store.get(cp.attempt_ref, ProviderAttempt)
    original = ProviderReceipt.model_validate_json((transport.root/(attempt.client_identity+'.ack.json')).read_bytes())
    changed = ProviderReceipt.seal(**{**original.model_dump(exclude={'fingerprint'}), 'client_identity':'a'*64})
    transport._path(attempt).unlink()
    (transport.root/(attempt.client_identity+'.ack.json')).write_text(changed.model_dump_json())
    with pytest.raises(ValueError, match='PROVIDER_RECEIPT_IDENTITY_MISMATCH'):
        await transport.recover_unknown(op, attempt)
    assert len(calls) == 1
    await transport.adapter.client.aclose()


@pytest.mark.asyncio
async def test_query_mismatch_retains_both_failure_records_and_never_resubmits(tmp_path, monkeypatch, video):
    calls = []
    def handle(req):
        calls.append(req)
        if req.method == 'POST':
            return httpx.Response(200, json={'id':'exact-task', 'status':'running'})
        assert req.url.path.endswith('/tasks/exact-task')
        return httpx.Response(200, json={'id':'wrong-task' if len(calls)==2 else 'exact-task',
            'status':'succeeded', 'content':{'video_url':'https://output.invalid/video.mp4'}})
    owner, transport, op, request, inputs = await rig(tmp_path, monkeypatch, video, handle)
    normalize = transport.adapter.normalize
    def broken_ack(raw, task):
        raise ValueError('fixture parse failure')
    monkeypatch.setattr(transport.adapter, 'normalize', broken_ack)
    await owner.execute(inputs)
    first = owner.store.checkpoint(op.artifact_reference()).progress.last_failure_ref
    first_body = owner.store.ledger.get_artifact('execution-diagnostic', first)
    monkeypatch.setattr(transport.adapter, 'normalize', normalize)
    await owner.execute(inputs)
    second = owner.store.checkpoint(op.artifact_reference())
    assert second.state == OperationState.UNKNOWN
    assert second.progress.last_failure_ref != first
    assert 'PROVIDER_TASK_ID_CHANGED' in detail(owner, op).error_codes
    assert owner.store.ledger.get_artifact('execution-diagnostic', first) == first_body
    await owner.execute(inputs)
    assert owner.store.checkpoint(op.artifact_reference()).state == OperationState.SUCCEEDED
    assert [r.method for r in calls] == ['POST', 'GET', 'GET']
    await transport.adapter.client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('operation,method,status,expected', [
    ('get_media','GET',503,2), ('get_asset','GET',500,2), ('resolve_media','GET',504,2),
    ('get_media','GET',404,1), ('get_media','GET',403,1), ('get_media','POST',503,1),
    ('import_media','POST',503,1), ('create_task','POST',503,1), ('get_work','GET',503,1),
])
async def test_only_transient_input_reads_retry_once(operation, method, status, expected):
    calls = []
    def handle(req):
        calls.append(req)
        return httpx.Response(status if len(calls)==1 else 200, json={'ok':True})
    async with httpx.AsyncClient(base_url='http://local.invalid', transport=httpx.MockTransport(handle)) as client:
        provider = HttpProviderClient(ServiceConfig(base_url='http://local.invalid', operations={operation:'/fixture'}), client)
        if expected == 1:
            with pytest.raises(RemoteServiceError):
                await provider.request(operation, method=method)
        else:
            assert await provider.request(operation, method=method) == {'ok':True}
    assert len(calls) == expected


def test_old_progress_and_diagnostic_serialize_without_new_empty_fields():
    assert 'lastFailureRef' not in OperationProgress().model_dump(mode='json', by_alias=True)
    d = ExecutionDiagnostic(code='OLD_CODE', owner='target-execution', domain='REFERENCE')
    assert 'failureDetails' not in d.model_dump(mode='json', by_alias=True)
