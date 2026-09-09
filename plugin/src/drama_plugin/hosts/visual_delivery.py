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
    decision = attempt.get('frame_snapshot', state['frames'][attempt['shot_id']])
    r = decision.get('requirements', decision['spec'])
    if r.get('work_id') not in (None, work_id) or (decision.get('schema') == 'video-decision-v1' and r['shot_id'] != shot_id):
        raise ValueError('OUTPUT_BUSINESS_SCOPE_MISMATCH')
    kind = MediaType(attempt.get('media_kind', 'IMAGE'))
    source_ref = f"{state.get('stage', {}).get('id', state['plan_fingerprint'])}:{attempt['shot_id']}:{attempt_id}"
    expected = MediaIdentity(work_id, kind, source_ref, attempt['output_hash'], shot_id=shot_id,
        purpose='VIDEO_CANDIDATE' if kind == MediaType.VIDEO else 'VIDEO_INPUT', media_id=media_id)
    content = {'providerJobId':attempt['job_id'], 'attemptId':attempt_id,
        'requestFingerprint':attempt['request_fingerprint'],
        'inputMediaIds': ([r['edit_source']['media_id']] if r.get('edit_source')
                          else [i['media_id'] for i in r.get('inputs',[])]),
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


async def sync_review(state: dict[str, Any], *, attempt_id: str, mcp_config: str) -> dict[str, Any]:
    """Project the effective review to existing Media/Shot without adopting bytes."""
    from drama_plugin.visual.production import current_review
    from drama_plugin.contracts.base import sha256_canonical
    a = next(a for a in state['attempts'] if a['attempt_id'] == attempt_id)
    review = current_review(a); fingerprint = sha256_canonical(review)
    async with McpMediaSession(Path(mcp_config)) as s:
        m = await s.media.get_media(a['delivery']['mediaId'])
        if m.work_id != state['production_route']['work_id'] or m.content_hash != a['output_hash'] or not m.shot_id:
            raise ValueError('REVIEW_MEDIA_OWNERSHIP_MISMATCH')
        content = dict(m.content)
        content.setdefault('originalReviewStatus', content.get('reviewStatus'))
        content.update(reviewStatus=a['review_status'], currentReview=review, currentReviewHash=fingerprint)
        await s.media.save_media(m.id, content, m.purpose)
        shot = await s.memory.get_shot(m.shot_id)
        body = dict(shot.content); bindings = [dict(b) for b in body.get('mediaBindings', [])]
        matches = [b for b in bindings if b.get('mediaId') == m.id and b.get('contentHash') == m.content_hash]
        if len(matches) != 1:
            raise ValueError('REVIEW_BINDING_MISMATCH')
        b = matches[0]; b.setdefault('originalContentReview', b.get('contentReview'))
        b.update(contentReview=a['review_status'], currentReviewHash=fingerprint)
        body['mediaBindings'] = bindings
        await s.memory.save_shot(shot.id, shot.shot_no, body, shot.title, shot.shot_type)
        fresh = await s.media.get_media(m.id); updated = await s.memory.get_shot(shot.id)
        if fresh.content != content or updated.content != body:
            raise ValueError('REVIEW_PROJECTION_NOT_VERIFIED')
    return {'mediaId':m.id,'review':a['review_status'],'reviewHash':fingerprint,'userAdoption':a.get('user_adoption','PENDING')}
