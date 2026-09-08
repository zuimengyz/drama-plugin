"""Read-only projection of the existing Work stage into the supplied audit view."""
from __future__ import annotations
from typing import Any
from drama_plugin.contracts.base import sha256_canonical


def project(work: dict[str, Any]) -> dict[str, Any]:
    content = work['content']; route = content['productionRoute']
    if route['work_id'] != work['id']:
        raise ValueError('AUDIT_WORK_SCOPE_MISMATCH')
    stage = content.get('productionStage') or {'attempts': []}
    attempts: dict[str, dict[str, Any]] = {}; jobs: dict[str, str] = {}
    for a in stage['attempts']:
        # A reserved but never dispatched request is not a real submission event.
        if a['status'] == 'RESERVED' and not (a.get('submitted_at') or a.get('job_id')):
            continue
        key = a.get('call_id', a['attempt_id'])
        if key in attempts and attempts[key] != a:
            raise ValueError('CONFLICTING_DUPLICATE_CALL')
        if a.get('job_id') and a['job_id'] in jobs and jobs[a['job_id']] != key:
            raise ValueError('PROVIDER_JOB_COUNTED_TWICE')
        attempts[key] = a
        if a.get('job_id'): jobs[a['job_id']] = key
    ids = [i['target_id'] for i in route['inputs']] + route['video_targets']
    if any(a['shot_id'] not in ids for a in attempts.values()):
        raise ValueError('AUDIT_CALL_OUTSIDE_ROUTE')
    calls = []; usage = []; adopted: dict[str, list[tuple[float, float]]] = {}
    for key, a in attempts.items():
        created = bool(a.get('job_id'))
        status = '已创建' if created else '确认未创建' if a['status'] == 'NOT_CREATED' else '结果不明'
        settled = a.get('credits') is not None and bool(a.get('billing_event_id'))
        probe = a.get('technical', {}).get('probe', {})
        duration = probe.get('duration', probe.get('format', {}).get('duration')) if a.get('media_kind') == 'VIDEO' else None
        if duration is not None: duration = float(duration)
        seconds = None
        if a.get('user_adoption') == 'USER_SELECTED' and a.get('adopted_intervals'):
            digest = a['output_hash']; old = adopted.get(digest, [])
            def length(ranges: list[tuple[float, float]]) -> float:
                total = 0.0; end = 0.0
                for start, stop in sorted(ranges):
                    if not (0 <= start < stop and duration is not None and stop <= duration):
                        raise ValueError('INVALID_ADOPTED_INTERVAL')
                    total += max(0, stop - max(start, end)); end = max(end, stop)
                return total
            new = old + [tuple(x) for x in a['adopted_intervals']]
            seconds = length(new) - length(old); adopted[digest] = new
        evidence = {'stage': route['stage_id'], 'review': a.get('review_status'),
                    'reviewCategories': [f['category'] for f in a.get('review', {}).get('findings', [])],
                    'billingEvent': a.get('billing_event_id'), 'outputHash': a.get('output_hash'),
                    'providerUsageIsSettlement': False}
        reason = {'INITIAL':'首次生成','CONTENT_REWORK':'内容返工','TECHNICAL_RETRY':'技术重试'}.get(a.get('call_reason','INITIAL'),'首次生成')
        calls.append([key,a.get('submitted_at'),a['shot_id'],reason,status,'已结算' if settled else '未知/未结算',
                      'Comfy积分',a.get('credits') if settled else None,None,duration,seconds,
                      a.get('retry_evidence') or a.get('content_observation'),a.get('job_id'),a.get('delivery',{}).get('mediaId', a.get('media_id')),str(evidence)])
        observed = a.get('provider_usage', {})
        usage.append([observed.get('credits'), a.get('reserved_credits'), observed.get('event_id')])
    targets = []
    for target in ids:
        duty = next((i for i in route['inputs'] if i['target_id'] == target), None)
        related = [a for a in attempts.values() if a['shot_id'] == target]
        first = next((a for a in related if a.get('job_id')), None)
        review = None if first is None else ('通过' if first.get('review_status','').startswith('PASS') else '失败' if first.get('review_status') == 'FAIL' else '待审')
        selected = [a for a in related if a.get('user_adoption') == 'USER_SELECTED']
        intent = (duty['specification'] if duty else route['requirements'].get('shotIntents',{}).get(target, target+'；按正式镜头动作要求验收'))
        targets.append([target,'镜头帧' if duty else '视频',intent,
                        route['route_id'],'有限试产',review,'用户采用' if selected else None,
                        first.get('review',{}).get('evidence') if first else None])
    return {'schema':'v207-audit-view-v1','workId':work['id'],'title':work['title'],
            'source':'work.get_work.content.productionStage','sourceFingerprint':sha256_canonical(stage),
            'targets':targets,'calls':calls,'usage':usage,
            'authorization':stage.get('stage',{}).get('authorization_ref'), 'pause':stage.get('pause')}
