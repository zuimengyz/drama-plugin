"""Reserved synchronous Ark still execution; durable bytes precede state completion."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import httpx
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.hosts.route_production import operate
from drama_plugin.providers.ark_image import validate_binding
from drama_plugin.visual.ark_submission import retained_receipt, submit_reserved
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
        if receipt := retained_receipt(self.cache, work_id, attempt):
            return receipt  # Existing caller recovers persistence; never repeat POST.
        if attempt['status'] != 'RESERVED' or attempt.get('job_id'):
            raise ValueError('RECOVER_EXISTING_ARK_IMAGE_ATTEMPT')
        await operate(self.memory, work_id, 'begin-submission', {'attempt_id': attempt_id},
                      approved_interpretation_refs=approved_interpretation_refs)
        # Retained test/remote adapters need not mutate the in-memory snapshot.
        receipt = await submit_reserved(work_id, {**attempt, 'submission_started': True},
            frame, self.cache, client=self.client)
        if receipt['status'] == 'NOT_CREATED':
            await operate(self.memory, work_id, 'result', dict(attempt_id=attempt_id,
                status='NOT_CREATED', job_id=None, evidence=json.dumps(receipt['diagnostics'])))
        elif receipt['status'] == 'COMPLETED':
            await operate(self.memory, work_id, 'result', dict(attempt_id=attempt_id, status='COMPLETED',
                job_id=receipt['task_id'], output_hash=receipt['output_hash'],
                evidence='Ark official image HTTP 200; original PNG retained',
                execution_receipt=receipt['correlation']))
        return receipt
