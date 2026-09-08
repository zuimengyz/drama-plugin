"""Finish an existing paid visual attempt through the formal Media tools."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from drama_plugin.hosts.mcp_media import McpMediaSession
from drama_plugin.media_delivery import MediaIdentity, complete_retained_media
from drama_plugin.contracts.media import MediaType


async def complete_attempt(state: dict[str, Any], *, attempt_id: str, mcp_config: str,
                           source_path: str, cache: str, work_id: str, shot_id: str,
                           media_id: str | None = None) -> dict[str, Any]:
    attempt = next(a for a in state['attempts'] if a['attempt_id'] == attempt_id)
    if attempt['status'] != 'COMPLETED' or any(attempt.get('technical', {}).get('checks', {}).get(k) != 'PASS' for k in ('integrity','linkage')):
        raise ValueError('TECHNICAL_PROVIDER_OUTPUT_REQUIRED')
    decision = state['frames'][attempt['shot_id']]
    r = decision.get('requirements', decision['spec'])
    if r.get('work_id') not in (None, work_id) or (decision.get('schema') == 'video-decision-v1' and r['shot_id'] != shot_id):
        raise ValueError('OUTPUT_BUSINESS_SCOPE_MISMATCH')
    kind = MediaType(attempt.get('media_kind', 'IMAGE'))
    source_ref = f"{state.get('stage', {}).get('id', state['plan_fingerprint'])}:{attempt['shot_id']}:{attempt_id}"
    expected = MediaIdentity(work_id, kind, source_ref, attempt['output_hash'], shot_id=shot_id,
        purpose='VIDEO_CANDIDATE' if kind == MediaType.VIDEO else 'VIDEO_INPUT', media_id=media_id)
    content = {'providerJobId':attempt['job_id'], 'attemptId':attempt_id,
        'requestFingerprint':attempt['request_fingerprint'], 'inputMediaIds':[i['media_id'] for i in r.get('inputs',[])],
        'retention':'CANDIDATE','technicalReviewStatus':attempt.get('technical_status','PENDING'),'reviewStatus':attempt.get('content_status','PENDING_REVIEW'),
        'userAdoption':attempt.get('user_adoption','PENDING')}
    async with McpMediaSession(Path(mcp_config)) as session:
        receipt = await complete_retained_media(session.media,session.memory,session.asset,expected,
            source=Path(source_path),content=content,cache=Path(cache),target_id=attempt['shot_id'],
            content_review=attempt.get('content_status','PENDING_REVIEW'),
            user_adoption=attempt.get('user_adoption','PENDING'),
            duration_ms=round(float(attempt['technical']['probe'].get('format', {}).get('duration', 0))*1000) or None)
        receipt['toolCalls'] = list(session.calls)
    attempt.update(persistence_status='VERIFIED', delivery_status=receipt['deliveryStatus'], delivery=receipt)
    return receipt
