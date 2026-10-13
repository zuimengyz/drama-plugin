"""Actual image-dispatch receipt identity; offline HTTP only, no Provider calls."""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json

import httpx
import pytest

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.providers.ark_image import binding
from drama_plugin.visual.ark_submission import submit_reserved
from test_fixed_production_routes import ark_frame


KEY = 'OFFLINE_IMAGE_KEY_AT_DISPATCH'
OTHER_KEY = 'OFFLINE_CHANGED_IMAGE_KEY'
PNG = b'\x89PNG\r\n\x1a\nfixture-only'


def reserved(tmp_path, monkeypatch):
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY', KEY)
    frame = ark_frame(tmp_path)
    now = datetime.now(timezone.utc)
    evidence = dict(source='OFFLINE_RECEIPT_FIXTURE', verified=True,
        checked_at=now.isoformat(), expires_at=(now + timedelta(minutes=5)).isoformat())
    attempt = dict(attempt_id='fixture-dispatch', request=frame['request'],
        submission_started=True, job_id=None, execution_binding=binding(frame, evidence))
    return frame, attempt


def response_for(status):
    if status == 200:
        return httpx.Response(status, headers={'x-request-id': 'fixture-created'},
            json={'created': 123, 'data': [{'b64_json': base64.b64encode(PNG).decode()}]})
    return httpx.Response(status, headers={'x-request-id': 'fixture-rejected'},
        json={'error': {'code': 'OfflineError', 'message': 'api_key=' + KEY}})


@pytest.mark.parametrize('http_status,expected',
    [(200, 'COMPLETED'), (400, 'NOT_CREATED'), (503, 'UNKNOWN')])
async def test_real_dispatch_retains_nonsecret_credential_for_each_http_outcome(
        tmp_path, monkeypatch, http_status, expected):
    frame, attempt = reserved(tmp_path, monkeypatch)
    calls = []

    def handle(request):
        calls.append(request)
        assert request.headers['Authorization'] == 'Bearer ' + KEY
        assert json.loads(request.content) == frame['request']['body']
        return response_for(http_status)

    cache = tmp_path / 'receipts'
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await submit_reserved('fixture-work', attempt, frame, cache, client=client)
    assert result['status'] == expected
    assert result['credential_source'] == 'DRAMA_VIDEO_SEEDANCE_API_KEY'
    assert result['credential_fingerprint'] == hashlib.sha256(KEY.encode()).hexdigest()
    assert result['request_fingerprint'] == sha256_canonical(frame['request'])
    retained = (cache / 'fixture-dispatch.json').read_text()
    assert json.loads(retained) == result
    assert KEY not in retained and 'Authorization' not in retained
    assert len(calls) == 1
    if http_status == 200:
        assert (cache / 'fixture-dispatch.png').read_bytes() == PNG
        assert result['correlation']['task_id'] == 'fixture-created'
    else:
        assert not list(cache.glob('*.png'))


async def test_credential_capture_uses_dispatch_key_even_if_environment_changes_during_http(
        tmp_path, monkeypatch):
    frame, attempt = reserved(tmp_path, monkeypatch)

    def handle(request):
        assert request.headers['Authorization'] == 'Bearer ' + KEY
        monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY', OTHER_KEY)
        return response_for(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        receipt = await submit_reserved('fixture-work', attempt, frame,
            tmp_path / 'receipts', client=client)
    assert receipt['credential_fingerprint'] == hashlib.sha256(KEY.encode()).hexdigest()
    assert receipt['credential_fingerprint'] != hashlib.sha256(OTHER_KEY.encode()).hexdigest()
    assert OTHER_KEY not in json.dumps(receipt)


@pytest.mark.parametrize('has_historical_fingerprint', [False, True])
async def test_retained_receipt_replay_never_backfills_or_rewrites_with_current_key(
        tmp_path, monkeypatch, has_historical_fingerprint):
    frame, attempt = reserved(tmp_path, monkeypatch)
    cache = tmp_path / 'receipts'
    cache.mkdir()
    legacy = dict(attempt_id=attempt['attempt_id'], work_id='fixture-work',
        request_fingerprint=sha256_canonical(attempt['request']), status='UNKNOWN',
        credential_source='DRAMA_VIDEO_SEEDANCE_API_KEY', provider='ark')
    if has_historical_fingerprint:
        legacy['credential_fingerprint'] = hashlib.sha256(KEY.encode()).hexdigest()
    path = cache / 'fixture-dispatch.json'
    original = (json.dumps(legacy, indent=4) + '\n').encode()
    path.write_bytes(original)
    monkeypatch.setenv('DRAMA_VIDEO_SEEDANCE_API_KEY', OTHER_KEY)

    def forbidden_post(request):
        raise AssertionError('Receipt replay must never create a second paid request')

    async with httpx.AsyncClient(transport=httpx.MockTransport(forbidden_post)) as client:
        replay = await submit_reserved('fixture-work', attempt, frame, cache, client=client)
    assert replay == legacy
    assert path.read_bytes() == original
    assert ('credential_fingerprint' in replay) == has_historical_fingerprint
