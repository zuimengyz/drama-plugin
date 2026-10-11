"""Shared synchronous image submission; callers own reservation and review.

Extracted from the retained Ark host. This primitive never reads a Work, starts a
Run, grants spending or registers an Asset. A retained receipt never repeats POST.
"""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
from typing import Any, cast
import httpx
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.providers.ark_image import credential, ENDPOINT, validate_binding
from drama_plugin.providers.video.diagnostics import seedance_error
from drama_plugin.config.production_routes import require_image


def retained_receipt(cache: Path, work_id: str, attempt: dict[str, Any]) -> dict[str, Any] | None:
    path = cache / (attempt['attempt_id'] + '.json')
    if not path.exists():
        return None
    receipt = json.loads(path.read_text())
    if (receipt['attempt_id'] != attempt['attempt_id'] or receipt['work_id'] != work_id
            or receipt['request_fingerprint'] != sha256_canonical(attempt['request'])):
        raise ValueError('ARK_IMAGE_RECOVERY_IDENTITY_MISMATCH')
    if receipt.get('output_hash'):
        data = Path(receipt['output_path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != receipt['output_hash']:
            raise ValueError('ARK_IMAGE_RECOVERY_HASH_MISMATCH')
    return cast(dict[str, Any], receipt)


def parse_output(response: httpx.Response, secret: str) -> tuple[bytes, dict[str, Any]]:
    diagnostic = seedance_error(response, secret)
    body = response.json()
    rows = body.get('data', []) if isinstance(body, dict) else []
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict) or not rows[0].get('b64_json'):
        raise ValueError('ARK_IMAGE_RESULT_REQUIRES_RECOVERY')
    data = base64.b64decode(rows[0]['b64_json'], validate=True)
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('ARK_IMAGE_RESULT_MIME_MISMATCH')
    if not diagnostic.get('request_id'):
        raise ValueError('ARK_IMAGE_RESPONSE_ID_MISSING')
    return data, dict(task_id=diagnostic['request_id'], output_hash=hashlib.sha256(data).hexdigest(),
        output_bytes=len(data), mime_type='image/png', created=body.get('created'), usage=body.get('usage'))


async def submit_reserved(work_id: str, attempt: dict[str, Any], frame: dict[str, Any],
                          cache: Path, *, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """Exactly one POST after the caller durably claims the uncertainty boundary."""
    require_image('ark', frame['template']['model'])
    value = attempt.get('execution_binding')
    validate_binding(frame, value)
    assert value is not None
    if attempt['request'] != frame['request']:
        raise ValueError('ARK_IMAGE_RESERVED_REQUEST_CHANGED')
    if recovered := retained_receipt(cache, work_id, attempt):
        return recovered
    if not attempt.get('submission_started') or attempt.get('job_id'):
        raise ValueError('ARK_IMAGE_DISPATCH_CLAIM_REQUIRED')
    config = credential()
    assert config.api_key is not None
    secret = config.api_key.get_secret_value()
    cache.mkdir(parents=True, exist_ok=True)
    active = client or httpx.AsyncClient(timeout=300, follow_redirects=False)
    try:
        response = await active.post(config.base_url + ENDPOINT,
            headers={'Authorization': 'Bearer ' + secret}, json=attempt['request']['body'])
    finally:
        if client is None:
            await active.aclose()
    receipt = dict(attempt_id=attempt['attempt_id'], work_id=work_id,
        request_fingerprint=sha256_canonical(attempt['request']),
        credential_source='DRAMA_VIDEO_SEEDANCE_API_KEY', provider='ark',
        model=frame['template']['model'], endpoint=config.base_url+ENDPOINT,
        diagnostics=seedance_error(response, secret))
    if response.status_code != 200:
        receipt.update(status='NOT_CREATED' if 400 <= response.status_code < 500 else 'UNKNOWN')
    else:
        data, output = parse_output(response, secret)
        destination = cache / (attempt['attempt_id'] + '.png')
        from drama_plugin.execution.media import atomic_write
        atomic_write(destination, data)
        receipt.update(status='COMPLETED', output_path=str(destination), **output)
        correlation = {key: value[key] for key in ('execution', 'endpoint_fingerprint', 'provider_schema_fingerprint', 'operation')}
        correlation.update(attempt_id=attempt['attempt_id'], task_id=receipt['task_id'],
            request_fingerprint=receipt['request_fingerprint'])
        receipt['correlation'] = correlation
    path = cache / (attempt['attempt_id'] + '.json')
    from drama_plugin.execution.media import atomic_write
    atomic_write(path, (json.dumps(receipt, indent=2)+'\n').encode())
    return receipt
