"""Reserved synchronous Ark still execution; durable bytes precede state completion."""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
from typing import Any
import httpx
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.hosts.route_production import operate
from drama_plugin.providers.ark_image import credential, ENDPOINT, validate_binding
from drama_plugin.providers.video.diagnostics import seedance_error
from drama_plugin.config.production_routes import require_image
from drama_plugin.visual.history import attempt_frame


class ArkImageHost:
    lifecycle = "LEGACY_RECOVERY_ONLY"
    def __init__(self, memory: Any, cache: Path, *, client: httpx.AsyncClient | None = None):
        self.memory, self.cache, self.client = memory, cache, client

    async def submit(self, work_id: str, attempt_id: str, *,
                     approved_interpretation_refs: tuple[SourcePin, ...] = ()) -> dict[str, Any]:
        work = await self.memory.get_work(work_id)
        state = work.content['productionStage']
        attempt = next(a for a in state['attempts'] if a['attempt_id'] == attempt_id)
        frame = attempt_frame(state, attempt)
        require_image('ark', frame['template']['model'])
        value = attempt.get('execution_binding')
        validate_binding(frame, value)
        if attempt['request'] != frame['request']:
            raise ValueError('ARK_IMAGE_RESERVED_REQUEST_CHANGED')
        self.cache.mkdir(parents=True, exist_ok=True)
        receipt_path = self.cache / (attempt_id + '.json')
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            if (receipt['attempt_id'] != attempt_id or receipt['work_id'] != work_id
                    or receipt['request_fingerprint'] != sha256_canonical(attempt['request'])):
                raise ValueError('ARK_IMAGE_RECOVERY_IDENTITY_MISMATCH')
            if receipt.get('output_hash'):
                data = Path(receipt['output_path']).read_bytes()
                if hashlib.sha256(data).hexdigest() != receipt['output_hash']:
                    raise ValueError('ARK_IMAGE_RECOVERY_HASH_MISMATCH')
            return receipt  # Caller recovers state/persistence; never repeat POST.
        if attempt['status'] != 'RESERVED' or attempt.get('job_id'):
            raise ValueError('RECOVER_EXISTING_ARK_IMAGE_ATTEMPT')
        config = credential()
        assert config.api_key is not None
        secret = config.api_key.get_secret_value()
        await operate(self.memory, work_id, 'begin-submission', {'attempt_id': attempt_id},
                      approved_interpretation_refs=approved_interpretation_refs)
        client = self.client or httpx.AsyncClient(timeout=300, follow_redirects=False)
        try:
            response = await client.post(config.base_url + ENDPOINT,
                headers={'Authorization': 'Bearer ' + secret}, json=attempt['request']['body'])
        finally:
            if self.client is None:
                await client.aclose()
        diagnostic = seedance_error(response, secret)
        receipt = dict(attempt_id=attempt_id, work_id=work_id,
            request_fingerprint=sha256_canonical(attempt['request']),
            credential_source='DRAMA_VIDEO_SEEDANCE_API_KEY', provider='ark',
            model=frame['template']['model'], endpoint=config.base_url+ENDPOINT,
            diagnostics=diagnostic)
        if response.status_code != 200:
            receipt.update(status='NOT_CREATED' if 400 <= response.status_code < 500 else 'UNKNOWN')
            receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
            if receipt['status'] == 'NOT_CREATED':
                await operate(self.memory, work_id, 'result', dict(attempt_id=attempt_id,
                    status='NOT_CREATED', job_id=None, evidence=json.dumps(diagnostic)))
            return receipt
        body = response.json()
        rows = body.get('data', [])
        if len(rows) != 1 or not rows[0].get('b64_json'):
            raise ValueError('ARK_IMAGE_RESULT_REQUIRES_RECOVERY')
        data = base64.b64decode(rows[0]['b64_json'], validate=True)
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('ARK_IMAGE_RESULT_MIME_MISMATCH')
        task_id = diagnostic.get('request_id')
        if not task_id:
            raise ValueError('ARK_IMAGE_RESPONSE_ID_MISSING')
        output = self.cache / (attempt_id + '.png')
        output.write_bytes(data)
        receipt.update(status='COMPLETED', task_id=task_id, output_path=str(output),
                       output_hash=hashlib.sha256(data).hexdigest(), output_bytes=len(data),
                       mime_type='image/png', created=body.get('created'), usage=body.get('usage'))
        assert value is not None
        correlation = {key: value[key] for key in ('execution', 'endpoint_fingerprint', 'provider_schema_fingerprint', 'operation')}
        correlation.update(attempt_id=attempt_id, task_id=task_id,
                           request_fingerprint=receipt['request_fingerprint'])
        receipt['correlation'] = correlation
        receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
        await operate(self.memory, work_id, 'result', dict(attempt_id=attempt_id, status='COMPLETED',
            job_id=task_id, output_hash=receipt['output_hash'], evidence='Ark official image HTTP 200; original PNG retained',
            execution_receipt=correlation))
        return receipt
